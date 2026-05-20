"""ActionCenterItem — table cardinale V4 single-table inheritance Q1-A (ADR-025 §4.1).

🛡️ D1 CARDINAL : `chk_kind` whitelist 7 valeurs (PAS 3 — correction prompt M2-2).

Invariants applicables :
- IS1 : organisation_id NOT NULL + indexed sur tous les indexes
- IL1-IL11 : lifecycle (state machine via VALID_TRANSITIONS Sprint M2-5)
- IL10 : `chk_closure_consistency` lifecycle_state=closed ⇔ closed_at + closure_reason
- IL9 : score_stale=TRUE après chaque transition (Sprint M2-5)
- Q9-B : duplicate_group_id (FK) ≠ recurrence_group_id (FK) — tables séparées
- Q11-A : priority_explanation JSONB versionné (composantes R1-R6)
"""

from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from models.base import Base


class ActionCenterItem(Base):
    """Table cardinale V4 (single-table inheritance Q10-A)."""

    __tablename__ = "action_center_items"

    # ─── Identité ───
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organisation_id = Column(  # IS1 · M2-4.1 Path B : Integer FK partagé legacy↔V4 (ADR-009 Option D)
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ─── Single-table inheritance discriminant (Q1-A · D1 cardinal) ───
    kind = Column(String(20), nullable=False)  # 7 valeurs whitelist (Kind enum)

    # ─── Métadonnées ───
    title = Column(String(255), nullable=False)
    description = Column(Text)
    domain = Column(String(30))  # D5 : pas de CHECK DB (extensible Mois 6+)
    source_module = Column(String(40))

    # ─── Lifecycle (ADR-028) ───
    lifecycle_state = Column(String(20), nullable=False, server_default="new")

    # ─── Priority (ADR-022 + Q11-A JSONB) ───
    priority_bracket = Column(String(2), nullable=False)
    priority_score = Column(Float, nullable=False)
    priority_explanation = Column(JSON)  # JSONB en PG, JSON en SQLite (portable)
    score_version = Column(String(10), server_default="v1")
    score_calculated_at = Column(DateTime(timezone=True), server_default=func.now())
    score_stale = Column(Boolean, nullable=False, server_default=text("false"))  # IL9

    # ─── Owner ───
    owner_id = Column(UUID(as_uuid=True))
    owner_role = Column(String(40))
    # M2-5.11.E : snapshot du libellé pilote (rempli au PATCH /assign).
    # Pattern V4 « UUID isolé + snapshot label » identique à `actor_name`
    # sur action_event_log — évite une jointure runtime sur la table legacy
    # `users` (Integer id ≠ UUID owner_id).
    owner_display_name = Column(String(120))
    assigned_at = Column(DateTime(timezone=True))

    # ─── Dates métier ───
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    sla_due_date = Column(DateTime(timezone=True))
    business_due_date = Column(DateTime(timezone=True))

    # ─── Closure (cohérent doctrine v0.3 §7.1 + IL4 + IL5 + IL10) ───
    closed_at = Column(DateTime(timezone=True))
    closure_reason = Column(String(40))
    closure_payload = Column(JSON)

    # ─── Impact ───
    impact_current_period_eur = Column(Numeric(12, 2))
    impact_cumulative_eur = Column(Numeric(12, 2))
    impact_dimension = Column(String(20))
    impact_payload = Column(JSON)

    # ─── Flags & Confiance ───
    next_best_action = Column(String(40))
    confidence_score = Column(Numeric(3, 2))
    is_irreversible_action_disabled = Column(Boolean, nullable=False, server_default=text("false"))
    is_escalated = Column(Boolean, nullable=False, server_default=text("false"))

    # ─── Refs faibles ───
    site_id = Column(UUID(as_uuid=True))
    building_id = Column(UUID(as_uuid=True))
    meter_id = Column(UUID(as_uuid=True))
    regulatory_rule_id = Column(UUID(as_uuid=True))  # R6 plancher P1

    # ─── Refs groupes Q9-B (FK strict) ───
    duplicate_group_id = Column(UUID(as_uuid=True), ForeignKey("duplicate_groups.id", ondelete="SET NULL"))
    recurrence_group_id = Column(UUID(as_uuid=True), ForeignKey("recurrence_groups.id", ondelete="SET NULL"))

    # ─── Champs spécifiques par kind (D1 prévoit 7 kinds) ───
    anomaly_detector_id = Column(String(50))
    decision_deadline = Column(DateTime(timezone=True))
    recommendation_payback_years = Column(Numeric(4, 1))
    deadline_authority = Column(String(50))
    evidence_format_expected = Column(String(20))
    signal_confidence_level = Column(String(10))

    # ─── Idempotency (M2-4.2 — POST /items replay-safe) ───
    # idempotency_key : UUID v4 fourni par le client dans le header Idempotency-Key.
    # idempotency_payload_hash : SHA256 du body — détecte un rejeu de clé avec un
    # payload différent (→ 409). Index UNIQUE partiel par org (cf. __table_args__).
    idempotency_key = Column(String(36))
    idempotency_payload_hash = Column(String(64))

    # ─── Timestamps ───
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    @property
    def impact_at_risk_eur(self) -> float | None:
        """M2-5.11.D — Extrait la valeur €/12m du quadrant `at_risk` depuis
        `impact_payload` (JSON). Exposé via `ActionCenterItemResponse` pour
        permettre à l'UI (colonne € ItemsTable + libellé PriorityQueueCard)
        d'afficher « ce que le CFO risque de perdre » sans drill-down.

        Cohérent avec `impact_service.build_item_impact` : même clé
        `impact_payload['at_risk']['value_eur']`, mêmes coercions
        défensives (`None`, `""`, `"NaN"` → `None`).
        """
        raw = (self.impact_payload or {}).get("at_risk")
        if not isinstance(raw, dict):
            return None
        value = raw.get("value_eur")
        if value is None or value == "":
            return None
        try:
            f = float(value)
        except (TypeError, ValueError):
            return None
        # NaN guard (NaN != NaN) — cohérent _coerce_float impact_service.
        if f != f:
            return None
        return f

    __table_args__ = (
        # 🛡️ D1 CARDINAL : 7 valeurs strictes (PAS 3)
        CheckConstraint(
            "kind IN ('anomaly', 'action', 'decision', 'signal', 'evidence_request', 'deadline', 'recommendation')",
            name="chk_kind",
        ),
        # IL2 : 5 lifecycle_state strict (ADR-028 §6.1)
        CheckConstraint(
            "lifecycle_state IN ('new', 'triaged', 'planned', 'in_progress', 'closed')",
            name="chk_lifecycle_state",
        ),
        # ADR-022 : 4 priority_bracket
        CheckConstraint(
            "priority_bracket IN ('P0', 'P1', 'P2', 'P3')",
            name="chk_priority_bracket",
        ),
        # IL10 cardinal : closure consistency (ADR-025 §4.1)
        CheckConstraint(
            "(lifecycle_state = 'closed' AND closed_at IS NOT NULL AND closure_reason IS NOT NULL)"
            " OR (lifecycle_state != 'closed' AND closed_at IS NULL)",
            name="chk_closure_consistency",
        ),
        # closure_reason valid (cohérent doctrine v0.3 §7.1 — 6 valeurs révisées)
        CheckConstraint(
            "closure_reason IS NULL OR closure_reason IN ("
            "'resolved', 'dismissed', 'not_applicable', "
            "'merged_duplicate', 'resolved_via_recurrence', 'expired'"
            ")",
            name="chk_closure_reason_valid",
        ),
        # Score range
        CheckConstraint(
            "priority_score >= 0 AND priority_score <= 100",
            name="chk_score_range",
        ),
        # Confidence range (R5)
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="chk_confidence_range",
        ),
        # ─── Indexes (cohérent ADR-025 §4.2 — 8 indexes table cardinale) ───
        Index(
            "idx_aci_priority_active",
            "organisation_id",
            "priority_score",
            "priority_bracket",
            sqlite_where=text("lifecycle_state != 'closed'"),
            postgresql_where=text("lifecycle_state != 'closed'"),
        ),
        Index("idx_aci_kind_domain", "organisation_id", "kind", "domain"),
        Index("idx_aci_lifecycle", "organisation_id", "lifecycle_state", "sla_due_date"),
        Index(
            "idx_aci_stale",
            "organisation_id",
            "score_stale",
            sqlite_where=text("score_stale = 1"),
            postgresql_where=text("score_stale = TRUE"),
        ),
        Index(
            "idx_aci_unassigned",
            "organisation_id",
            "priority_bracket",
            sqlite_where=text("owner_id IS NULL AND lifecycle_state != 'closed'"),
            postgresql_where=text("owner_id IS NULL AND lifecycle_state != 'closed'"),
        ),
        Index(
            "idx_aci_recent_closed",
            "organisation_id",
            "closed_at",
            sqlite_where=text("lifecycle_state = 'closed'"),
            postgresql_where=text("lifecycle_state = 'closed'"),
        ),
        Index(
            "idx_aci_site",
            "organisation_id",
            "site_id",
            sqlite_where=text("site_id IS NOT NULL"),
            postgresql_where=text("site_id IS NOT NULL"),
        ),
        Index(
            "idx_aci_owner",
            "organisation_id",
            "owner_id",
            "lifecycle_state",
            sqlite_where=text("owner_id IS NOT NULL"),
            postgresql_where=text("owner_id IS NOT NULL"),
        ),
        # M2-4.2 : unicité de l'idempotency_key PAR organisation (deux orgs
        # peuvent réutiliser le même UUID sans conflit). Partiel : seules les
        # lignes avec une clé sont indexées.
        Index(
            "idx_aci_idempotency_key",
            "organisation_id",
            "idempotency_key",
            unique=True,
            sqlite_where=text("idempotency_key IS NOT NULL"),
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )
