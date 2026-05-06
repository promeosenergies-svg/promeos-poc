"""Audit log service — SoT pour traçabilité actions patrimoine + cascade.

Sprint C-2 Phase 1 — comble GAP audit Phase B R9 (audit_log_service dédié).

Source : matrice v1 §6.10 + audit Phase B R9.

API publique :
- log_patrimoine_change : audit modification champ patrimoine (PATCH events)
- log_cascade : audit cascade recompute (Phase 6 Sprint C-1)
- query_audit_trail : récupération audit trail org-scopée

Modèle : iam.AuditLog étendu (Phase 1.2 — 6 colonnes nullable backward compat).
Toute écriture passe par ce service (source-guard active dans
backend/tests/source_guards/test_audit_log_no_direct_writes_source_guards.py).

Allowlist legacy 7 callsites (cf. D-Phase1-Audit-Log-Legacy-Callsites-001) :
- middleware/cx_logger.py (CX events)
- services/intake_service.py
- services/operat_export_service.py
- services/copilot_engine.py
- services/iam_service.py
- (NB : routes/patrimoine/sites.py:508,554 ont été MIGRÉS vers ce service Phase 1.2)
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Any, Callable, Optional, Union

from sqlalchemy.orm import Session

from models.iam import AuditLog


_logger = logging.getLogger(__name__)


def _serialize_value(value: Any) -> Optional[str]:
    """Sérialise une valeur en JSON pour stockage dans old_value/new_value.

    Retourne None si value est None.
    Utilise default=str pour gérer datetime/date/Decimal automatiquement.
    """
    if value is None:
        return None
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def log_patrimoine_change(
    db: Session,
    *,
    user_id: Optional[int],
    org_id: Optional[int],
    entity_type: str,
    entity_id: int,
    action: str,
    field_modified: Optional[str] = None,
    old_value: Any = None,
    new_value: Any = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    detail: Optional[dict] = None,
) -> AuditLog:
    """Audit log modification champ patrimoine (PATCH events sur Site/Batiment/etc.).

    Args:
        db: session SQLAlchemy
        user_id: utilisateur déclencheur (None si système/cron)
        org_id: organisation propriétaire (scoping multi-tenant)
        entity_type: ex "site", "batiment", "compteur"
        entity_id: identifiant de l'entité modifiée
        action: ex "patrimoine.update", "site.update", "site.archive"
        field_modified: nom du champ modifié (optionnel si modification multi-champs)
        old_value, new_value: valeurs avant/après (sérialisés JSON automatiquement)
        correlation_id: identifiant de corrélation cross-services
        ip_address, user_agent: traçabilité HTTP
        detail: dict additionnel sérialisé dans detail_json

    Returns:
        AuditLog instance (id populé via flush, pas commit — caller décide).

    Note : ne fait pas de commit. Le caller est responsable du commit.
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=entity_type,
        resource_id=str(entity_id),
        detail_json=json.dumps(detail, default=str, ensure_ascii=False) if detail else None,
        ip_address=ip_address,
        # Sprint C-2 Phase 1 — extension
        correlation_id=correlation_id,
        org_id=org_id,
        field_modified=field_modified,
        old_value=_serialize_value(old_value),
        new_value=_serialize_value(new_value),
        user_agent=user_agent,
    )
    db.add(log)
    db.flush()
    return log


def log_cascade(
    db: Session,
    *,
    user_id: Optional[int],
    org_id: Optional[int],
    cascade_result,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """Audit log cascade recompute (Phase 6 Sprint C-1).

    Args:
        cascade_result: instance CascadeResult de cascade_recompute_service.
            Sérialisé en payload structuré dans detail_json :
            {type, trigger_field, old_value_serialized, new_value_serialized,
             actions[], errors_count, successes_count, persisted}

    Returns:
        AuditLog instance.

    Convention payload detail_json :
    - `type`: "cascade_recompute"
    - `trigger_field`: champ amont qui a déclenché la cascade
    - `actions`: liste des recalculs cascadants (output_field, new_value, error)
    - `errors_count` / `successes_count` : agrégats
    - `persisted`: True si cascade en mode persist=True, False si dry-run
    """
    payload = {
        "type": "cascade_recompute",
        "trigger_field": cascade_result.field_modified,
        "old_value_serialized": str(cascade_result.old_value) if cascade_result.old_value is not None else None,
        "new_value_serialized": str(cascade_result.new_value) if cascade_result.new_value is not None else None,
        "actions": [
            {
                "output_field": a.output_field,
                "new_value": str(a.new_value) if a.new_value is not None else None,
                "error": a.error,
            }
            for a in cascade_result.actions
        ],
        "errors_count": sum(1 for a in cascade_result.actions if a.error),
        "successes_count": sum(1 for a in cascade_result.actions if not a.error),
        "persisted": cascade_result.persisted,
    }

    log = AuditLog(
        user_id=user_id,
        action="cascade.recompute",
        resource_type=cascade_result.entity_type,
        resource_id=str(cascade_result.entity_id) if cascade_result.entity_id is not None else None,
        detail_json=json.dumps(payload, default=str, ensure_ascii=False),
        ip_address=ip_address,
        # Sprint C-2 Phase 1 — extension
        correlation_id=correlation_id,
        org_id=org_id,
        field_modified=cascade_result.field_modified,
        old_value=_serialize_value(cascade_result.old_value),
        new_value=_serialize_value(cascade_result.new_value),
        user_agent=user_agent,
    )
    db.add(log)
    db.flush()
    return log


# ─── Sprint C-7 Phase 7.4 — RGPD consent_change helper (clôture pattern doctrinal 5/5) ───


def log_consent_change(
    db: Session,
    *,
    user_id: Optional[int],
    org_id: int,
    target_type: str,
    target_id: int,
    field: str,
    old_value: Any,
    new_value: Any,
    cgu_version: Optional[str],
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Sprint C-7 Phase 7.4 — Helper RGPD `rgpd.consent_change` event AuditLog.

    Clôture pattern doctrinal "Déclaration sans enforcement runtime" 5/5 cardinal Phase C+ :

    - ADR-007 RGPD a déclaré audit trail (Sprint C-3)
    - Phase 5.3 a livré champs audit trail (`_by` + `_cgu_version`)
    - Phase 5.6 F1 a fixé enforcement FK runtime (PRAGMA foreign_keys=ON)
    - Phase 5.8 G1 a wiré cascade Org consent CASCADE_MAP runtime
    - Phase 5.8 G3 a fixé BillAnomaly UNIQUE constraint
    - Phase 7.2 a fixé DEMO_MODE bypass scope_utils
    - **Phase 7.4 (cette phase)** wire l'event AuditLog runtime → CLÔTURE pattern doctrinal

    Args:
        target_type: "organisation" | "delivery_point" (cf. ADR-007 Option B archi-helios)
        target_id: ID Organisation ou DeliveryPoint
        field: ex "consentement_dataconnect_global", "consentement_grdf_local"
        old_value, new_value: valeurs avant/après (None autorisé pour première mise à jour)
        cgu_version: version CGU acceptée (CNIL article 7 — preuve d'origine forte)

    CNIL article 7 : preuve d'origine forte = qui (user_id) + quand (created_at) +
    valeur (old/new_value) + CGU (cgu_version) + scope (target_type=organisation|delivery_point).

    Note : ne fait pas de commit. Le caller est responsable du commit (cohérent
    pattern `log_patrimoine_change` Sprint C-2 P1.3).
    """
    detail = {
        "type": "rgpd.consent_change",
        "field": field,
        "cgu_version": cgu_version,
        "rgpd_article": "Article 7 RGPD - preuve d'origine du consentement",
    }
    log = AuditLog(
        user_id=user_id,
        action="rgpd.consent_change",
        resource_type=target_type,
        resource_id=str(target_id),
        detail_json=json.dumps(detail, default=str, ensure_ascii=False),
        ip_address=ip_address,
        correlation_id=correlation_id,
        org_id=org_id,
        field_modified=field,
        old_value=_serialize_value(old_value),
        new_value=_serialize_value(new_value),
    )
    db.add(log)
    db.flush()
    return log


def log_consent_changes_batch(
    db: Session,
    *,
    user_id: Optional[int],
    org_id: int,
    target_type: str,
    target_id: int,
    changes: list[dict],
    cgu_version: Optional[str],
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> list[AuditLog]:
    """Sprint C-7 Phase 7.4 + 7.8 — Variant batch PATCH multi-champs avec commit immédiat.

    Sprint C-7 Phase 7.8 fix critique D-Audit-Phase7-Audit-Rollback-Loss-004 :
    `db.commit()` IMMÉDIAT après ajout des events — termine la transaction caller →
    audit persisté avant tout rollback ultérieur (cascade error / commit final échoué).

    Anti-CWE-778 (perte audit CNIL sur rollback). Le caller continue avec une nouvelle
    transaction implicite ouverte au prochain query/mutation.

    Args:
        changes: [{"field": "consentement_dataconnect_global", "old": True, "new": False}, ...]

    Returns:
        Liste des AuditLog créés (1 par change). Persistés DB avant retour.

    CNIL article 5(2) accountability : preuve d'origine forte garantie même en cas de
    rollback métier (rgpd_consent.py:cascade_recompute_on_change échec, etc.).
    """
    events = []
    for change in changes:
        events.append(
            log_consent_change(
                db=db,
                user_id=user_id,
                org_id=org_id,
                target_type=target_type,
                target_id=target_id,
                field=change["field"],
                old_value=change.get("old"),
                new_value=change.get("new"),
                cgu_version=cgu_version,
                correlation_id=correlation_id,
                ip_address=ip_address,
            )
        )
    # Sprint C-7 Phase 7.8 — commit immédiat anti-rollback caller ultérieur (CNIL preuve d'origine)
    db.commit()
    return events


# ─── Sprint C-7 Phase 7.5 — External Connectors audit trail (ADR-018, CNIL preuve d'extraction) ───

# Sentinelles de redaction — case-insensitive
_SENSITIVE_KEY_PATTERNS = (
    "authorization",
    "bearer",
    "client_secret",
    "secret",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "code_verifier",
    "code_challenge",
    "password",
    "passwd",
)

# Champs identifiants à hasher (PRM/PCE/SIREN/SIRET) plutôt que redact
_HASH_KEY_PATTERNS = (
    "prm",
    "pce",
    "siren",
    "siret",
    "usage_point_id",
    "code",  # code OAuth2 d'autorisation
)

_REDACTED = "<redacted>"


def _is_sensitive_key(key: str) -> bool:
    """True si la clé contient un pattern sensible (case-insensitive)."""
    lk = (key or "").lower()
    return any(p in lk for p in _SENSITIVE_KEY_PATTERNS)


def _is_hash_key(key: str) -> bool:
    """True si la clé contient un identifiant à hasher (PRM/PCE/SIREN/...)."""
    lk = (key or "").lower()
    return any(p == lk or p in lk for p in _HASH_KEY_PATTERNS)


def _short_hash(value: Any) -> str:
    """Hash sha256[:16] d'une valeur arbitraire — preuve de présence sans exposition."""
    if value is None:
        return ""
    try:
        s = value if isinstance(value, str) else json.dumps(value, default=str, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        s = str(value)
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:16]


def _sanitize_kwargs(kwargs: dict) -> dict:
    """Sérialise kwargs en dict sanitisé (secrets redacted, identifiants hashés).

    - Authorization/Bearer/client_secret/token → "<redacted>"
    - PRM/PCE/SIREN/SIRET/usage_point_id/code → sha256[:16]
    - Session SQLAlchemy → omis (non sérialisable, pas pertinent audit)
    - dict imbriqué → sanitisé récursivement
    """
    out: dict = {}
    for k, v in kwargs.items():
        if v is None:
            out[k] = None
            continue
        # Skip Session SQLAlchemy
        if isinstance(v, Session):
            continue
        if _is_sensitive_key(k):
            out[k] = _REDACTED
        elif _is_hash_key(k):
            out[k] = f"sha256:{_short_hash(v)}"
        elif isinstance(v, dict):
            out[k] = _sanitize_kwargs(v)
        elif isinstance(v, (list, tuple)):
            out[k] = [_sanitize_kwargs({"_": item})["_"] if isinstance(item, dict) else _safe_repr(item) for item in v]
        else:
            out[k] = _safe_repr(v)
    return out


def _safe_repr(v: Any) -> Any:
    """Représentation safe d'une valeur scalaire pour audit detail_json."""
    if isinstance(v, (str, int, float, bool)):
        # Tronque strings longues (anti-leak réponses verbeuses)
        if isinstance(v, str) and len(v) > 200:
            return v[:200] + "...[truncated]"
        return v
    return str(v)[:200]


def _record_external_api_event(
    *,
    provider: str,
    endpoint: str,
    method: str,
    success: bool,
    duration_ms: int,
    status_code: Optional[int] = None,
    error_class: Optional[str] = None,
    error_message: Optional[str] = None,
    request_hash: Optional[str] = None,
    response_hash: Optional[str] = None,
    args_summary: Optional[dict] = None,
    org_id: Optional[int] = None,
    user_id: Optional[int] = None,
    correlation_id: Optional[str] = None,
) -> Optional[AuditLog]:
    """Persiste un AuditLog `connector.api_call` dans une session dédiée.

    Découple la transaction d'audit de celle du caller (cohérent ADR-018) :
    une exception lors du logging ne doit pas casser le caller.
    """
    payload = {
        "type": "connector.api_call",
        "provider": provider,
        "endpoint": endpoint,
        "method": method.upper(),
        "success": success,
        "duration_ms": duration_ms,
        "status_code": status_code,
        "error_class": error_class,
        "error_message": error_message,
        "request_hash": request_hash,
        "response_hash": response_hash,
        "args_summary": args_summary or {},
        "rgpd_article": (
            "Article 5(2) RGPD - principe accountability + Article 30 - registre des activités de traitement"
        ),
    }

    # Session dédiée (découplée transaction caller)
    from database import SessionLocal

    audit_db = SessionLocal()
    try:
        log = AuditLog(
            user_id=user_id,
            action="connector.api_call",
            resource_type=provider,
            resource_id=endpoint,
            detail_json=json.dumps(payload, default=str, ensure_ascii=False),
            correlation_id=correlation_id,
            org_id=org_id,
        )
        audit_db.add(log)
        audit_db.commit()
        audit_db.refresh(log)
        return log
    except Exception as exc:  # noqa: BLE001 — résilience audit
        _logger.warning(
            "external_api_audit_log_failed provider=%s endpoint=%s err=%s",
            provider,
            endpoint,
            type(exc).__name__,
        )
        audit_db.rollback()
        return None
    finally:
        audit_db.close()


def audit_external_api_call(
    provider: str,
    endpoint: Union[str, Callable[..., str]],
    method: str = "GET",
):
    """Décorateur ADR-018 — audit trail external API calls (CNIL preuve d'extraction).

    Wrap une méthode connecteur (sync, instance ou module) pour produire un AuditLog
    `connector.api_call` à chaque invocation. Sanitisation automatique :
    - Authorization/Bearer/client_secret/token/code_verifier → `<redacted>`
    - PRM/PCE/SIREN/SIRET/usage_point_id/code → `sha256:<short_hash>`

    Args:
        provider: identifiant connecteur, ex "enedis_dataconnect", "grdf_adict", "sirene"
        endpoint: chemin endpoint statique OU callable(*args, **kwargs) → str
        method: HTTP verb par défaut "GET" (utilisé en payload, pas runtime)

    Behavior:
        - Mesure duration_ms (perf_counter)
        - Sur succès : log success=True, response_hash si dict
        - Sur exception : log success=False, error_class, error_message[:200], puis raise
        - L'audit utilise une session DÉDIÉE — n'affecte pas la transaction caller

    CNIL article 5(2) RGPD (principe accountability) + article 30 (registre des activités) :
    preuve d'extraction = qui (user_id si dispo) + quand (created_at) + où (provider + endpoint) +
    quoi (request_hash + response_hash) + résultat (success/error).

    Sprint C-7 Phase 7.8 fix D-Audit-Phase7-RGPD-Article-Inadequate-005 : Article 6 RGPD
    (bases légales du traitement) substitué par Article 5(2) (accountability) + Article 30
    (registre des traitements). Article 6 = licéité du traitement, NON traçabilité technique.

    Note CNIL Phase 7.5 : ce wiring clôt le dernier P0 résiduel Sprint C-7
    (D-Sprint-C7-External-Connectors-Audit-Trail-001) — pré-pilote-ready.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Résolution endpoint (statique ou dynamique)
            try:
                ep = endpoint(*args, **kwargs) if callable(endpoint) else endpoint
            except Exception:  # noqa: BLE001
                ep = str(endpoint)

            # Sanitize args/kwargs (skip self pour méthodes d'instance)
            sanitized_kwargs = _sanitize_kwargs(kwargs)
            sanitized_positional = [
                _safe_repr(a) if not isinstance(a, (Session,)) else None
                for a in args[1:]  # skip self / first arg
            ]
            args_summary = {
                "kwargs": sanitized_kwargs,
                "positional_count": len(args[1:]),
            }
            request_hash = _short_hash({"args": sanitized_positional, "kwargs": sanitized_kwargs})

            # Extraction org_id/user_id/correlation_id si présents en kwargs
            org_id = kwargs.get("org_id") if isinstance(kwargs.get("org_id"), int) else None
            user_id = kwargs.get("user_id") if isinstance(kwargs.get("user_id"), int) else None
            correlation_id = kwargs.get("correlation_id") if isinstance(kwargs.get("correlation_id"), str) else None

            t0 = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.perf_counter() - t0) * 1000)
                response_hash = _short_hash(result) if result is not None else None
                _record_external_api_event(
                    provider=provider,
                    endpoint=ep,
                    method=method,
                    success=True,
                    duration_ms=duration_ms,
                    status_code=None,
                    request_hash=request_hash,
                    response_hash=response_hash,
                    args_summary=args_summary,
                    org_id=org_id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                )
                return result
            except Exception as exc:
                duration_ms = int((time.perf_counter() - t0) * 1000)
                _record_external_api_event(
                    provider=provider,
                    endpoint=ep,
                    method=method,
                    success=False,
                    duration_ms=duration_ms,
                    error_class=type(exc).__name__,
                    error_message=str(exc)[:200],
                    request_hash=request_hash,
                    args_summary=args_summary,
                    org_id=org_id,
                    user_id=user_id,
                    correlation_id=correlation_id,
                )
                raise

        return wrapper

    return decorator


def query_audit_trail(
    db: Session,
    *,
    org_id: int,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    action: Optional[str] = None,
    correlation_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 100,
) -> list[AuditLog]:
    """Récupère l'audit trail filtré et org-scopé.

    Args:
        org_id: OBLIGATOIRE — sécurité multi-tenant. Une org ne peut voir que ses
            propres logs.
        entity_type, entity_id, action, correlation_id: filtres optionnels.
        since, until: bornes temporelles created_at.
        limit: pagination (défaut 100, ordre desc created_at).

    Returns:
        list[AuditLog] triée par created_at desc.

    ⚠️ Sécurité : org_id est OBLIGATOIRE pour cette query. Pas de fallback "all orgs".
    """
    q = db.query(AuditLog).filter(AuditLog.org_id == org_id)

    if entity_type:
        q = q.filter(AuditLog.resource_type == entity_type)
    if entity_id is not None:
        q = q.filter(AuditLog.resource_id == str(entity_id))
    if action:
        q = q.filter(AuditLog.action == action)
    if correlation_id:
        q = q.filter(AuditLog.correlation_id == correlation_id)
    if since:
        q = q.filter(AuditLog.created_at >= since)
    if until:
        q = q.filter(AuditLog.created_at <= until)

    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()
