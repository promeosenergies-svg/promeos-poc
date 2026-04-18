"""
PROMEOS — Modèles DB Sol V1 (agentic assistant).

4 tables append-only / statefuls pour l'infrastructure Sol :

1. `SolActionLog` — journal append-only de toutes les actions Sol.
   Modification interdite (event listener before_update), suppression
   interdite (event listener before_delete). Seule exception :
   anonymisation RGPD (champs `anonymized` + `anonymized_at`, rétention 3 ans).

2. `SolPendingAction` — queue des actions programmées (grace period L2).
   Immutable sauf transitions de statut légitimes (waiting → executing →
   executed | cancelled). Lookup via `correlation_id` ou
   `cancellation_token` (annulation one-click sans auth depuis email).

3. `SolConfirmationToken` — tokens HMAC de confirmation avant exécution
   (L1 prévisualisation intégrale). TTL 5 min, single-use.

4. `SolOrgPolicy` — politique agentique par organisation (modes,
   seuils, dry-run, préférences de ton).

Décisions appliquées : cf docs/sol/DECISIONS_LOG.md
- P0-1 : Integer PK autoincrement (pas UUID)
- P0-2 : Column(JSON) générique SQLAlchemy (pas JSONB)
- P0-5 : CreatedAtOnlyMixin pour append-only (pas TimestampMixin)
- P1-1 : datetime.now(timezone.utc) (pas UTC import)

Corrections audit (commit c90d8b64 → post-review) :
- P0-B : SolOrgPolicy.updated_at a server_default=func.now()
- P0-A : SolPendingAction a event listener whitelist transitions d'état
- P1-B : SolActionLog a event listener before_delete bloquant
- P1-A : SolActionLog anonymized/anonymized_at cohérence enforcée
- P2   : CheckConstraint confidence ∈ [0, 1] sur SolActionLog et SolOrgPolicy
"""

from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    event,
    func,
    inspect,
)

from .base import Base, CreatedAtOnlyMixin


class AppendOnlyViolation(Exception):
    """Levée quand un UPDATE / DELETE est tenté sur une table append-only Sol,
    ou quand un champ immuable d'une table partiellement mutable est modifié."""


# Fields de SolPendingAction qui PEUVENT changer (transitions d'état légitimes).
# Tout le reste est figé à la création.
_PENDING_ACTION_MUTABLE_FIELDS = frozenset(
    {"status", "executed_at", "cancelled_at", "cancelled_by"}
)

# Fields de SolActionLog autorisés à changer (anonymisation RGPD uniquement).
_ACTION_LOG_ANONYMIZATION_FIELDS = frozenset({"anonymized", "anonymized_at"})


# ─────────────────────────────────────────────────────────────────────────────
# 1. SolActionLog — journal append-only (5 lois / L4 Audit complet)
# ─────────────────────────────────────────────────────────────────────────────


class SolActionLog(Base, CreatedAtOnlyMixin):
    """
    Journal append-only de toutes les actions agentiques Sol.

    Couvre tout le cycle de vie d'une action via `correlation_id` :
    PROPOSED → PREVIEWED → CONFIRMED → SCHEDULED → EXECUTED
    (ou CANCELLED / REVERTED / REFUSED).

    L'immutabilité est garantie par deux event listeners :
    - `_block_sol_action_log_update` rejette UPDATE sauf anonymisation
      cohérente (anonymized + anonymized_at ensemble).
    - `_block_sol_action_log_delete` rejette tout DELETE (politique RGPD
      exige anonymisation par le job périodique, pas suppression).
    """

    __tablename__ = "sol_action_log"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Scoping multi-tenant + traçabilité utilisateur
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Correlation : relie toutes les phases d'une même action agentique
    correlation_id = Column(String(36), nullable=False, index=True)

    # Enums applicatifs (définis dans backend/sol/schemas.py Phase 2)
    intent_kind = Column(String(64), nullable=False)
    action_phase = Column(String(32), nullable=False)

    # Détection d'altération entre propose/preview/confirm
    inputs_hash = Column(String(64), nullable=False)

    # Payload complet de l'ActionPlan
    plan_json = Column(JSON, nullable=False)

    # Snapshots avant/après exécution (idempotence + reversal)
    state_before = Column(JSON, nullable=True)
    state_after = Column(JSON, nullable=True)

    # Issue de l'action
    outcome_code = Column(String(64), nullable=True)
    outcome_message = Column(Text, nullable=True)

    # Traces LLM (rôles strictement CLASSIFY/EXPLAIN/SUMMARIZE, Sprint 7-8)
    llm_calls = Column(JSON, nullable=True)

    # Confiance du calcul déterministe (seuil d'exécution L5) ∈ [0, 1]
    confidence = Column(Numeric(4, 2), nullable=True)

    # RGPD : anonymisation après 3 ans (job différé Sprint 3+, voir P1-10)
    anonymized = Column(Boolean, nullable=False, default=False)
    anonymized_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_sol_action_log_org_created", "org_id", "created_at"),
        # Confidence must be in [0, 1] when present (Postgres enforce, SQLite ignore)
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_sol_action_log_confidence_range",
        ),
    )


@event.listens_for(SolActionLog, "before_update")
def _block_sol_action_log_update(mapper, connection, target):  # noqa: ARG001
    """
    Bloque les UPDATE sur sol_action_log sauf anonymisation RGPD cohérente.

    Règles :
    - Aucun field changé → autorisé (idempotent no-op).
    - Uniquement fields ⊆ {anonymized, anonymized_at} → autorisé.
    - Toute autre combinaison → AppendOnlyViolation.
    - Cohérence anonymisation : si `anonymized` passe à True, alors
      `anonymized_at` doit être set dans la même transaction.

    Compensation SQLite : event listener SQLAlchemy suffit pour le code
    applicatif. Contournement par raw SQL reste possible — compensé par
    test CI grep "no raw UPDATE on sol_action_log" dans backend/.
    """
    state = inspect(target)
    changed = {attr.key for attr in state.attrs if attr.history.has_changes()}

    if not changed:
        return  # no-op UPDATE idempotent

    disallowed = changed - _ACTION_LOG_ANONYMIZATION_FIELDS
    if disallowed:
        raise AppendOnlyViolation(
            f"SolActionLog is append-only. Attempted changes on forbidden "
            f"fields: {sorted(disallowed)}"
        )

    # Cohérence anonymisation : anonymized=True ⇒ anonymized_at set
    anonymized_changed = "anonymized" in changed
    if anonymized_changed and target.anonymized is True and target.anonymized_at is None:
        raise AppendOnlyViolation(
            "SolActionLog anonymization inconsistent: anonymized=True requires "
            "anonymized_at set in the same transaction."
        )


@event.listens_for(SolActionLog, "before_delete")
def _block_sol_action_log_delete(mapper, connection, target):  # noqa: ARG001
    """
    Bloque DELETE sur sol_action_log.

    La politique RGPD (DECISIONS_LOG P1-10) exige anonymisation, pas
    suppression. Le job différé Sprint 3+ set `anonymized=True` +
    `anonymized_at` à la place d'un DELETE physique.

    Un DELETE accidentel (bug app, migration mal faite) doit échouer
    bruyamment pour préserver le trail d'audit.
    """
    raise AppendOnlyViolation(
        "SolActionLog DELETE forbidden. Use RGPD anonymization "
        "(set anonymized=True + anonymized_at) instead of physical delete."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 2. SolPendingAction — queue grace period (L2 Réversible ou différé)
# ─────────────────────────────────────────────────────────────────────────────


class SolPendingAction(Base, CreatedAtOnlyMixin):
    """
    Action agentique programmée, en attente d'exécution (grace period).

    Entre le `confirm` de l'utilisateur et l'exécution réelle par le
    worker, une ligne vit ici avec status='waiting'. Le worker
    (`backend/jobs/worker.py`, via JobOutbox — DÉCISION P1-2) picks
    les entrées où `scheduled_for <= now()` et status='waiting'.

    Annulation one-click sans auth : le `cancellation_token` (URL-safe
    32 bytes) peut être utilisé sans JWT — lien envoyé par email,
    "Annuler l'envoi" dans les 24h.

    Fields MUTABLES (transitions d'état légitimes) :
    - status, executed_at, cancelled_at, cancelled_by

    Tout le reste (correlation_id, org_id, user_id, intent_kind,
    plan_json, scheduled_for, cancellation_token, created_at) est
    immuable après insertion — enforcement via event listener.
    """

    __tablename__ = "sol_pending_action"

    id = Column(Integer, primary_key=True, autoincrement=True)

    correlation_id = Column(String(36), nullable=False, unique=True, index=True)

    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    intent_kind = Column(String(64), nullable=False)
    plan_json = Column(JSON, nullable=False)

    # Quand exécuter (created_at + grace_period_seconds)
    scheduled_for = Column(DateTime, nullable=False, index=True)

    # Token URL-safe pour annulation one-click depuis email
    cancellation_token = Column(String(64), nullable=False, unique=True)

    # waiting / executing / executed / cancelled
    status = Column(String(32), nullable=False, default="waiting")

    executed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    cancelled_by = Column(Integer, ForeignKey("users.id"), nullable=True)


@event.listens_for(SolPendingAction, "before_update")
def _block_sol_pending_action_update(mapper, connection, target):  # noqa: ARG001
    """
    Whitelist des fields mutables sur SolPendingAction.

    Seules les transitions d'état opérationnelles sont autorisées :
    status + timestamps (executed_at, cancelled_at, cancelled_by).

    Toute tentative de modifier le plan original (correlation_id,
    org_id, plan_json, scheduled_for, cancellation_token) lève
    AppendOnlyViolation — ces champs sont figés à la création.
    """
    state = inspect(target)
    changed = {attr.key for attr in state.attrs if attr.history.has_changes()}

    if not changed:
        return

    disallowed = changed - _PENDING_ACTION_MUTABLE_FIELDS
    if disallowed:
        raise AppendOnlyViolation(
            f"SolPendingAction has immutable fields. Attempted changes on "
            f"forbidden fields: {sorted(disallowed)}. Only status transitions "
            f"({sorted(_PENDING_ACTION_MUTABLE_FIELDS)}) are allowed."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. SolConfirmationToken — tokens HMAC preview→execute (L1 Prévisualisation)
# ─────────────────────────────────────────────────────────────────────────────


class SolConfirmationToken(Base, CreatedAtOnlyMixin):
    """
    Token HMAC-SHA256 signé avec SOL_SECRET_KEY, émis à la prévisualisation
    d'un plan et consommé au moment du confirm.

    Garanties :
    - TTL 5 minutes (expires_at) — au-delà, re-prévisualisation obligatoire.
    - Single-use (consumed=True après usage).
    - Lié à un `plan_hash` précis — si le plan change entre preview et
      confirm (altération ou race condition), le token est rejeté.
    """

    __tablename__ = "sol_confirmation_token"

    # Token = clé primaire (déterministe, pas d'auto-increment — lookup par token)
    token = Column(String(64), primary_key=True)

    correlation_id = Column(String(36), nullable=False, unique=True, index=True)

    # Hash du plan prévisualisé — détecte altération entre preview et confirm
    plan_hash = Column(String(64), nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)

    expires_at = Column(DateTime, nullable=False, index=True)
    consumed = Column(Boolean, nullable=False, default=False)
    consumed_at = Column(DateTime, nullable=True)


# ─────────────────────────────────────────────────────────────────────────────
# 4. SolOrgPolicy — gouvernance agentique par organisation
# ─────────────────────────────────────────────────────────────────────────────


class SolOrgPolicy(Base):
    """
    Politique agentique par organisation — gouvernance Sol.

    Valeurs :
    - agentic_mode :
        consultative_only              : Sol propose, n'exécute jamais
        preview_only                   : Sol propose + prévisualise, user exécute
        full_agentic                   : Sol exécute après grace period
        full_agentic_with_dual_validation : idem + 2 users requis au-delà de seuil

    - dry_run_until : si dans le futur, toute exécution est bloquée
      (propose/preview continuent) — sécurité migration pilote.

    - confidence_threshold : minimum pour que Sol valide une proposition
      automatique ∈ [0, 1]. Si < threshold → PlanRefused avec
      reason='confidence_low'.

    NB : `SolOrgPolicy` n'utilise PAS CreatedAtOnlyMixin car la politique
    évolue — `updated_at` est donc légitime (transitions de mode attendues).
    """

    __tablename__ = "sol_org_policy"

    org_id = Column(Integer, ForeignKey("organisations.id"), primary_key=True)

    agentic_mode = Column(
        String(40),
        nullable=False,
        default="preview_only",
    )

    dry_run_until = Column(DateTime, nullable=True)
    dual_validation_threshold = Column(Numeric(12, 2), nullable=True)

    confidence_threshold = Column(Numeric(4, 2), nullable=False, default=0.85)
    grace_period_seconds = Column(Integer, nullable=False, default=900)

    tone_preference = Column(String(8), nullable=False, default="vous")

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.current_timestamp(),  # fallback pour INSERT SQL brut
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "confidence_threshold >= 0 AND confidence_threshold <= 1",
            name="ck_sol_org_policy_confidence_range",
        ),
    )

    def is_dry_run_active(self, now: datetime) -> bool:
        """True si mode dry-run est actif à l'instant `now`."""
        if self.dry_run_until is None:
            return False
        dry_run_ref = self.dry_run_until
        # Normaliser si SQLite retourne naive datetime
        if dry_run_ref.tzinfo is None:
            dry_run_ref = dry_run_ref.replace(tzinfo=timezone.utc)
        now_ref = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
        return now_ref < dry_run_ref


# ─────────────────────────────────────────────────────────────────────────────
# Exports publics
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    "SolActionLog",
    "SolPendingAction",
    "SolConfirmationToken",
    "SolOrgPolicy",
    "AppendOnlyViolation",
]
