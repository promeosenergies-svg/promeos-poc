"""
Validator Sol V1 — validation d'un ActionPlan avant exécution.

Exceptions typées levées par `validate_plan_for_execution()` :
- InvalidToken : token HMAC invalide, expiré ou consumed
- PlanAltered : plan_hash du token ≠ hash du plan actuel (tampering)
- DryRunBlocked : org_policy.dry_run_until dans le futur
- DualValidationMissing : requires_dual_validation + seuil €, 2e validation manquante
- ConfidenceTooLow : plan.confidence < org_policy.confidence_threshold

Utilisé par route `/api/sol/confirm` Phase 4.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from models.sol import SolConfirmationToken

from .schemas import ActionPlan, SolContextData
from .utils import hash_inputs, now_utc, verify_confirmation_token


# ─────────────────────────────────────────────────────────────────────────────
# Exceptions typées
# ─────────────────────────────────────────────────────────────────────────────


class SolValidationError(Exception):
    """Classe parent pour toutes les erreurs de validation Sol."""

    reason_code: str = "validation_failed"


class InvalidToken(SolValidationError):
    """Token HMAC invalide, expiré ou déjà consommé."""

    reason_code = "invalid_token"


class PlanAltered(SolValidationError):
    """plan_hash encodé dans le token ne matche plus le plan courant."""

    reason_code = "plan_altered"


class DryRunBlocked(SolValidationError):
    """L'organisation est en dry-run mode, exécution bloquée."""

    reason_code = "dry_run_active"


class DualValidationMissing(SolValidationError):
    """requires_dual_validation=True et 2e validation absente."""

    reason_code = "dual_validation_missing"


class ConfidenceTooLow(SolValidationError):
    """plan.confidence < org_policy.confidence_threshold."""

    reason_code = "confidence_too_low"


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────


def _plan_hash(plan: ActionPlan) -> str:
    """Hash canonique d'un plan pour comparaison détection altération."""
    return hash_inputs(
        plan.correlation_id,
        plan.intent.value,
        plan.title_fr,
        plan.summary_fr,
        plan.preview_payload,
        plan.inputs_hash,
        float(plan.confidence),
    )


def validate_plan_for_execution(
    db: Session,
    ctx: SolContextData,
    plan: ActionPlan,
    confirmation_token: str,
    *,
    second_validator_user_id: int | None = None,
) -> None:
    """
    Valide qu'un plan peut être exécuté / schedulé.

    Args:
        db: Session pour lookup SolConfirmationToken DB.
        ctx: SolContextData courant (org_policy).
        plan: ActionPlan retourné par /preview (à confirmer).
        confirmation_token: token HMAC émis au /preview.
        second_validator_user_id: pour dual validation (2 users distincts).

    Raises:
        InvalidToken, PlanAltered, DryRunBlocked, DualValidationMissing,
        ConfidenceTooLow — selon la règle violée. Aucune exception levée
        si tout est OK (retourne None).
    """
    expected_plan_hash = _plan_hash(plan)

    # 1. HMAC verification (structurel — correlation + plan_hash + signature)
    hmac_valid, token_user_id = verify_confirmation_token(
        confirmation_token, plan.correlation_id, expected_plan_hash
    )
    if not hmac_valid:
        raise InvalidToken(
            "Confirmation token invalide, expiré côté HMAC, ou plan altéré. "
            "Relancez la prévisualisation."
        )

    # 2. DB lookup token : consumed ? expiré ?
    token_row = (
        db.query(SolConfirmationToken)
        .filter(SolConfirmationToken.token == confirmation_token)
        .one_or_none()
    )
    if token_row is None:
        raise InvalidToken("Token inconnu en base.")
    if token_row.consumed:
        raise InvalidToken("Token déjà consommé — une confirmation a déjà eu lieu.")

    # Expires_at : SQLite peut retourner naive datetime, normaliser
    expires_at = token_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now_utc():
        raise InvalidToken("Token expiré (> 5 minutes). Relancez la prévisualisation.")

    # 3. plan_hash DB doit matcher plan_hash calculé
    if token_row.plan_hash != expected_plan_hash:
        raise PlanAltered(
            "Le plan a été modifié depuis la prévisualisation. "
            "Relancez /preview pour obtenir un nouveau token."
        )

    # 4. Org_id cohérence
    if token_row.org_id != ctx.org_id:
        raise InvalidToken("Token n'appartient pas à cette organisation.")

    # 5. Confidence threshold
    confidence_threshold = _as_decimal(ctx.org_policy.get("confidence_threshold", 0.85))
    plan_confidence = Decimal(str(plan.confidence))
    if plan_confidence < confidence_threshold:
        raise ConfidenceTooLow(
            f"Confiance du plan ({plan_confidence}) inférieure au seuil "
            f"de l'organisation ({confidence_threshold})."
        )

    # 6. Dry-run mode
    dry_run_until = _parse_maybe_datetime(ctx.org_policy.get("dry_run_until"))
    if dry_run_until is not None and dry_run_until > now_utc():
        raise DryRunBlocked(
            f"Mode dry-run actif jusqu'à {dry_run_until.isoformat()}. "
            f"L'exécution réelle est bloquée — prévisualisation uniquement."
        )

    # 7. Dual validation (seuil € + 2 users distincts)
    if plan.requires_dual_validation:
        threshold_eur = ctx.org_policy.get("dual_validation_threshold")
        plan_value = plan.estimated_value_eur
        if plan_value is not None and threshold_eur is not None:
            if plan_value >= float(threshold_eur):
                if second_validator_user_id is None:
                    raise DualValidationMissing(
                        f"Plan au-dessus du seuil de double validation "
                        f"({threshold_eur} €). 2e validateur requis."
                    )
                if second_validator_user_id == token_row.user_id:
                    raise DualValidationMissing(
                        "Double validation requiert 2 utilisateurs distincts. "
                        "Le validateur actuel est identique au primaire."
                    )

    # Tout est OK — caller peut procéder au scheduling


def _as_decimal(v: Any) -> Decimal:
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _parse_maybe_datetime(v: Any) -> datetime | None:
    """Parse v en datetime tz-aware, ou None si impossible."""
    if v is None:
        return None
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            dt = datetime.fromisoformat(v)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


__all__ = [
    "SolValidationError",
    "InvalidToken",
    "PlanAltered",
    "DryRunBlocked",
    "DualValidationMissing",
    "ConfidenceTooLow",
    "validate_plan_for_execution",
]
