"""create_v4_tables

Sprint M2-2 · Mois 2 backend V4 — Schéma DB Centre d'Action V4.

Revision ID: m2s2v4
Revises: p37bilan
Create Date: 2026-05-15

Crée 8 tables V4 + leurs indexes + CHECK constraints (cohérent ADR-025 §4 +
ADR-029 §2-3 + L7 §2 + 5 décisions cardinales D1-D5 actées Phase 0 audit M2-2).

🛡️ CARDINAL Q13-B : MIGRATION ADDITIVE UNIQUEMENT.
Les 18 tables legacy restent INTACTES (Mois 2-3 coexistence Q13-B).
Le downgrade DROP uniquement les 8 tables V4 (legacy non touché).

Tables créées (ordre FK-aware) :
1. duplicate_groups          (Q9-B doublons)
2. recurrence_groups         (Q9-B récurrences ≠ doublons)
3. action_center_items       (cardinale single-table inheritance Q1-A)
4. action_event_log          (16 event_types CHECK · IE7 schema_version)
5. evidences                 (D2 ADR-029 §2.1 autoritatif · IE6 90j)
6. action_links              (FK item)
7. action_blockers           (FK item · 7 blocker_types)
8. action_scenarios          (D3 ADR-025 §4.3 enrichi + 2 indexes)

Indexes : 23 total (20 ADR-025 §4.2 canonical + 3 enrichissements M2-2 :
- idx_event_log_actor : RGPD art. 15 droit d'accès user
- idx_scenarios_item_recommended : D3 affichage scenarios recommandés
- idx_evidences_verified : job notifications evidence à expirer)

CHECK constraints cardinaux (cohérent décisions D1-D5) :
- 🛡️ chk_kind 7 valeurs (D1)
- chk_lifecycle_state 5 valeurs (IL2)
- chk_priority_bracket 4 valeurs
- 🛡️ chk_closure_consistency (IL10 cardinal)
- chk_closure_reason_valid (6 valeurs révisées doctrine v0.3)
- chk_event_type 16 valeurs (renommages ADR-029)
- chk_actor_consistency
- chk_evidence_size_max_10mb (Q45-B)
- chk_evidence_mime_whitelist (PDF/JPG/PNG)
- chk_evidence_verified_consistency (IE2)
- chk_evidence_expires_90d (IE6 · PG-only · service enforce SQLite)
- chk_blocker_type 7 valeurs
- chk_scenario_selection_consistency (D3)
- chk_duplicate_status 'suggested/merged/dismissed' (D4)
- chk_recurrence_status 'active/watching/closed'
- chk_recurrence_occurrence_count >= 1
- chk_score_range + chk_confidence_range
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic
revision = "m2s2v4"
down_revision = "p37bilan"
branch_labels = None
depends_on = None


def upgrade():
    # ─────────────────────────────────────────────────────────────────
    # 1. duplicate_groups (Q9-B doublons stricts · D4 status vocabulaire UX)
    # ─────────────────────────────────────────────────────────────────
    op.create_table(
        "duplicate_groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),  # IS1
        sa.Column("detection_method", sa.String(20), nullable=False),
        sa.Column("detection_signature", sa.Text, nullable=False),
        sa.Column("representative_item_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="suggested"),
        sa.Column(
            "suggested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", UUID(as_uuid=True)),
        sa.CheckConstraint(
            "status IN ('suggested', 'merged', 'dismissed')",
            name="chk_duplicate_status",
        ),
    )
    op.create_index(
        "idx_duplicate_groups_org_status",
        "duplicate_groups",
        ["organisation_id", "status"],
    )

    # ─────────────────────────────────────────────────────────────────
    # 2. recurrence_groups (Q9-B récurrences distinctes des doublons)
    # ─────────────────────────────────────────────────────────────────
    op.create_table(
        "recurrence_groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),  # IS1
        sa.Column("domain", sa.String(20), nullable=False),
        sa.Column("source_signature", sa.Text, nullable=False),
        sa.Column("scope_signature", sa.Text, nullable=False),
        sa.Column("site_id", UUID(as_uuid=True)),
        sa.Column("building_id", UUID(as_uuid=True)),
        sa.Column("meter_id", UUID(as_uuid=True)),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("occurrence_count", sa.Integer, nullable=False, server_default="1"),
        sa.Column("rolling_window_days", sa.Integer, nullable=False, server_default="90"),
        sa.Column("representative_item_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution_justification", sa.Text),  # IL7 cardinal Amine
        sa.CheckConstraint(
            "status IN ('active', 'watching', 'closed')",
            name="chk_recurrence_status",
        ),
        sa.CheckConstraint("occurrence_count >= 1", name="chk_recurrence_occurrence_count"),
    )
    op.create_index(
        "idx_recurrence_groups_org_signature",
        "recurrence_groups",
        ["organisation_id", "source_signature", "scope_signature"],
    )
    op.create_index(
        "idx_recurrence_groups_org_status",
        "recurrence_groups",
        ["organisation_id", "status", "last_seen_at"],
    )

    # ─────────────────────────────────────────────────────────────────
    # 3. action_center_items (cardinale single-table inheritance Q1-A · D1 7 kinds)
    # ─────────────────────────────────────────────────────────────────
    op.create_table(
        "action_center_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),  # IS1
        sa.Column("kind", sa.String(20), nullable=False),  # D1 : 7 valeurs
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("domain", sa.String(30)),  # D5 : pas de CHECK DB
        sa.Column("source_module", sa.String(40)),
        # Lifecycle (ADR-028)
        sa.Column("lifecycle_state", sa.String(20), nullable=False, server_default="new"),
        # Priority (ADR-022 + Q11-A JSONB)
        sa.Column("priority_bracket", sa.String(2), nullable=False),
        sa.Column("priority_score", sa.Float, nullable=False),
        sa.Column("priority_explanation", sa.JSON),
        sa.Column("score_version", sa.String(10), server_default="v1"),
        sa.Column("score_calculated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("score_stale", sa.Boolean, nullable=False, server_default=sa.text("false")),  # IL9
        # Owner
        sa.Column("owner_id", UUID(as_uuid=True)),
        sa.Column("owner_role", sa.String(40)),
        sa.Column("assigned_at", sa.DateTime(timezone=True)),
        # Dates métier
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("sla_due_date", sa.DateTime(timezone=True)),
        sa.Column("business_due_date", sa.DateTime(timezone=True)),
        # Closure (IL10 cardinal)
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("closure_reason", sa.String(40)),
        sa.Column("closure_payload", sa.JSON),
        # Impact
        sa.Column("impact_current_period_eur", sa.Numeric(12, 2)),
        sa.Column("impact_cumulative_eur", sa.Numeric(12, 2)),
        sa.Column("impact_dimension", sa.String(20)),
        sa.Column("impact_payload", sa.JSON),
        # Flags & Confiance (R3 + R5)
        sa.Column("next_best_action", sa.String(40)),
        sa.Column("confidence_score", sa.Numeric(3, 2)),
        sa.Column(
            "is_irreversible_action_disabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("is_escalated", sa.Boolean, nullable=False, server_default=sa.text("false")),
        # Refs faibles
        sa.Column("site_id", UUID(as_uuid=True)),
        sa.Column("building_id", UUID(as_uuid=True)),
        sa.Column("meter_id", UUID(as_uuid=True)),
        sa.Column("regulatory_rule_id", UUID(as_uuid=True)),  # R6 plancher P1
        # Refs groupes Q9-B (FK strict)
        sa.Column(
            "duplicate_group_id",
            UUID(as_uuid=True),
            sa.ForeignKey("duplicate_groups.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "recurrence_group_id",
            UUID(as_uuid=True),
            sa.ForeignKey("recurrence_groups.id", ondelete="SET NULL"),
        ),
        # Champs spécifiques par kind (D1 prévoit 7 kinds)
        sa.Column("anomaly_detector_id", sa.String(50)),
        sa.Column("decision_deadline", sa.DateTime(timezone=True)),
        sa.Column("recommendation_payback_years", sa.Numeric(4, 1)),
        sa.Column("deadline_authority", sa.String(50)),
        sa.Column("evidence_format_expected", sa.String(20)),
        sa.Column("signal_confidence_level", sa.String(10)),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # 🛡️ CHECK constraints (D1 + D2 + D3 + IL10)
        sa.CheckConstraint(
            "kind IN ('anomaly', 'action', 'decision', 'signal', 'evidence_request', 'deadline', 'recommendation')",
            name="chk_kind",
        ),
        sa.CheckConstraint(
            "lifecycle_state IN ('new', 'triaged', 'planned', 'in_progress', 'closed')",
            name="chk_lifecycle_state",
        ),
        sa.CheckConstraint(
            "priority_bracket IN ('P0', 'P1', 'P2', 'P3')",
            name="chk_priority_bracket",
        ),
        sa.CheckConstraint(
            "(lifecycle_state = 'closed' AND closed_at IS NOT NULL AND closure_reason IS NOT NULL)"
            " OR (lifecycle_state != 'closed' AND closed_at IS NULL)",
            name="chk_closure_consistency",
        ),
        sa.CheckConstraint(
            "closure_reason IS NULL OR closure_reason IN ("
            "'resolved', 'dismissed', 'not_applicable',"
            " 'merged_duplicate', 'resolved_via_recurrence', 'expired'"
            ")",
            name="chk_closure_reason_valid",
        ),
        sa.CheckConstraint(
            "priority_score >= 0 AND priority_score <= 100",
            name="chk_score_range",
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="chk_confidence_range",
        ),
    )
    # 8 indexes (cohérent ADR-025 §4.2)
    op.create_index(
        "idx_aci_priority_active",
        "action_center_items",
        ["organisation_id", "priority_score", "priority_bracket"],
        sqlite_where=sa.text("lifecycle_state != 'closed'"),
        postgresql_where=sa.text("lifecycle_state != 'closed'"),
    )
    op.create_index(
        "idx_aci_kind_domain",
        "action_center_items",
        ["organisation_id", "kind", "domain"],
    )
    op.create_index(
        "idx_aci_lifecycle",
        "action_center_items",
        ["organisation_id", "lifecycle_state", "sla_due_date"],
    )
    op.create_index(
        "idx_aci_stale",
        "action_center_items",
        ["organisation_id", "score_stale"],
        sqlite_where=sa.text("score_stale = 1"),
        postgresql_where=sa.text("score_stale = TRUE"),
    )
    op.create_index(
        "idx_aci_unassigned",
        "action_center_items",
        ["organisation_id", "priority_bracket"],
        sqlite_where=sa.text("owner_id IS NULL AND lifecycle_state != 'closed'"),
        postgresql_where=sa.text("owner_id IS NULL AND lifecycle_state != 'closed'"),
    )
    op.create_index(
        "idx_aci_recent_closed",
        "action_center_items",
        ["organisation_id", "closed_at"],
        sqlite_where=sa.text("lifecycle_state = 'closed'"),
        postgresql_where=sa.text("lifecycle_state = 'closed'"),
    )
    op.create_index(
        "idx_aci_site",
        "action_center_items",
        ["organisation_id", "site_id"],
        sqlite_where=sa.text("site_id IS NOT NULL"),
        postgresql_where=sa.text("site_id IS NOT NULL"),
    )
    op.create_index(
        "idx_aci_owner",
        "action_center_items",
        ["organisation_id", "owner_id", "lifecycle_state"],
        sqlite_where=sa.text("owner_id IS NOT NULL"),
        postgresql_where=sa.text("owner_id IS NOT NULL"),
    )

    # ─────────────────────────────────────────────────────────────────
    # 4. action_event_log (16 event_types CHECK · IE7 schema_version · IS9)
    # ─────────────────────────────────────────────────────────────────
    op.create_table(
        "action_event_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),  # IS1
        sa.Column(
            "action_item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("action_center_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True)),
        sa.Column("actor_name", sa.String(120)),
        sa.Column("actor_role", sa.String(20)),
        sa.Column("event_payload", sa.JSON, nullable=False),
        sa.Column("schema_version", sa.String(10), nullable=False, server_default="v1"),  # IE7
        sa.Column("correlation_id", UUID(as_uuid=True), nullable=False),  # IS9
        sa.Column("source_route", sa.String(120)),
        # 🛡️ 16 event_types CHECK (renommages ADR-029)
        sa.CheckConstraint(
            "event_type IN ("
            "'created', 'state_changed', 'owner_changed', 'priority_changed',"
            " 'blocker_added', 'blocker_removed',"
            " 'evidence_added', 'evidence_verified',"
            " 'closed_with_evidence', 'closed_via_merged_duplicate',"
            " 'closed_via_resolved_via_recurrence', 'reopened',"
            " 'bulk_updated', 'exported', 'kind_corrected', 'priority_recalculated'"
            ")",
            name="chk_event_type",
        ),
        sa.CheckConstraint(
            "(actor_type = 'system' AND actor_id IS NULL) OR (actor_type = 'user' AND actor_id IS NOT NULL)",
            name="chk_actor_consistency",
        ),
    )
    op.create_index(
        "idx_event_log_org_item",
        "action_event_log",
        ["organisation_id", "action_item_id", "occurred_at"],
    )
    op.create_index("idx_event_log_type", "action_event_log", ["event_type", "occurred_at"])
    op.create_index("idx_event_log_correlation", "action_event_log", ["correlation_id"])
    op.create_index(
        "idx_event_log_actor",
        "action_event_log",
        ["actor_id", "occurred_at"],
        sqlite_where=sa.text("actor_id IS NOT NULL"),
        postgresql_where=sa.text("actor_id IS NOT NULL"),
    )

    # ─────────────────────────────────────────────────────────────────
    # 5. evidences (D2 ADR-029 §2.1 autoritatif · IE6 90j · IE9 magic bytes service)
    # ─────────────────────────────────────────────────────────────────
    op.create_table(
        "action_evidences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),  # IS1
        sa.Column(
            "action_item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("action_center_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mime_type", sa.String(50), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("storage_uri", sa.Text, nullable=False),
        sa.Column("original_filename", sa.String(255)),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("verified_by", UUID(as_uuid=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("validation_payload", sa.JSON),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("uploaded_by", UUID(as_uuid=True), nullable=False),
        sa.Column("description", sa.Text),
        # Q45-B 10 MB
        sa.CheckConstraint(
            "file_size_bytes > 0 AND file_size_bytes <= 10485760",
            name="chk_evidence_size_max_10mb",
        ),
        # IE9 whitelist 3 MIMEs
        sa.CheckConstraint(
            "mime_type IN ('application/pdf', 'image/jpeg', 'image/png')",
            name="chk_evidence_mime_whitelist",
        ),
        # IE2 verified consistency (portable PG + SQLite)
        sa.CheckConstraint(
            "(verified_at IS NULL AND verified_by IS NULL AND expires_at IS NULL)"
            " OR (verified_at IS NOT NULL AND verified_by IS NOT NULL AND expires_at IS NOT NULL)",
            name="chk_evidence_verified_consistency",
        ),
        # IE6 90 jours : enforced côté service Python (Sprint M2-6 verify_evidence
        # endpoint). Pas de CHECK SQL portable — `INTERVAL '90 days'` est
        # PostgreSQL-only (SQLite échoue parsing). Le service backend.services.evidence
        # garantit `expires_at = verified_at + timedelta(days=90)` strict.
        # Test SG-7 vérifie que la documentation IE6 référence ce mécanisme.
    )
    op.create_index("idx_evidences_org_item", "action_evidences", ["organisation_id", "action_item_id"])
    op.create_index(
        "idx_evidences_verified",
        "action_evidences",
        ["verified_at"],
        sqlite_where=sa.text("verified_at IS NOT NULL"),
        postgresql_where=sa.text("verified_at IS NOT NULL"),
    )
    op.create_index(
        "idx_evidences_expiring",
        "action_evidences",
        ["expires_at"],
        sqlite_where=sa.text("expires_at IS NOT NULL"),
        postgresql_where=sa.text("expires_at IS NOT NULL"),
    )

    # ─────────────────────────────────────────────────────────────────
    # 6. action_links
    # ─────────────────────────────────────────────────────────────────
    op.create_table(
        "action_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),  # IS1
        sa.Column(
            "item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("action_center_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("link_type", sa.String(40), nullable=False),
        sa.Column("target_module", sa.String(40), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("relation", sa.String(40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_links_item", "action_links", ["item_id"])
    op.create_index(
        "idx_links_target",
        "action_links",
        ["target_module", "target_id", "relation"],
    )

    # ─────────────────────────────────────────────────────────────────
    # 7. action_blockers (7 blocker_types · index partiel actifs)
    # ─────────────────────────────────────────────────────────────────
    op.create_table(
        "action_blockers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),  # IS1
        sa.Column(
            "item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("action_center_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("blocker_type", sa.String(40), nullable=False),
        sa.Column("added_by", UUID(as_uuid=True)),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("justification", sa.Text),
        sa.Column("expected_resolution_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_by", UUID(as_uuid=True)),
        sa.CheckConstraint(
            "blocker_type IN ("
            "'waiting_evidence', 'waiting_budget', 'waiting_third_party',"
            " 'waiting_data', 'waiting_supplier',"
            " 'waiting_manager_validation', 'waiting_regulatory_confirmation'"
            ")",
            name="chk_blocker_type",
        ),
    )
    op.create_index(
        "idx_blocker_item_active",
        "action_blockers",
        ["item_id"],
        sqlite_where=sa.text("resolved_at IS NULL"),
        postgresql_where=sa.text("resolved_at IS NULL"),
    )

    # ─────────────────────────────────────────────────────────────────
    # 8. action_scenarios (D3 enrichi · 2 indexes · CHECK selection consistency)
    # ─────────────────────────────────────────────────────────────────
    op.create_table(
        "action_scenarios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation_id", UUID(as_uuid=True), nullable=False),  # IS1
        sa.Column(
            "item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("action_center_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scenario_tag", sa.String(20), nullable=False),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("capex_eur", sa.Numeric(12, 2)),
        sa.Column("gain_eur_per_year", sa.Numeric(12, 2)),
        sa.Column(
            "is_recommended",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("selected_at", sa.DateTime(timezone=True)),
        sa.Column("selected_by", UUID(as_uuid=True)),
        sa.Column("payload", sa.JSON),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "(selected_at IS NULL AND selected_by IS NULL) OR (selected_at IS NOT NULL AND selected_by IS NOT NULL)",
            name="chk_scenario_selection_consistency",
        ),
    )
    op.create_index(
        "idx_scenarios_item_order",
        "action_scenarios",
        ["organisation_id", "item_id", "display_order"],
    )
    op.create_index(
        "idx_scenarios_item_recommended",
        "action_scenarios",
        ["organisation_id", "item_id"],
        sqlite_where=sa.text("is_recommended = 1"),
        postgresql_where=sa.text("is_recommended = TRUE"),
    )


def downgrade():
    # Reversible : drop V4 tables (legacy 18 tables intactes — Q13-B inviolable).
    # Ordre inverse FK : tables filles d'abord, puis cardinale, puis groupes.
    op.drop_index("idx_scenarios_item_recommended", table_name="action_scenarios")
    op.drop_index("idx_scenarios_item_order", table_name="action_scenarios")
    op.drop_table("action_scenarios")

    op.drop_index("idx_blocker_item_active", table_name="action_blockers")
    op.drop_table("action_blockers")

    op.drop_index("idx_links_target", table_name="action_links")
    op.drop_index("idx_links_item", table_name="action_links")
    op.drop_table("action_links")

    op.drop_index("idx_evidences_expiring", table_name="action_evidences")
    op.drop_index("idx_evidences_verified", table_name="action_evidences")
    op.drop_index("idx_evidences_org_item", table_name="action_evidences")
    op.drop_table("action_evidences")

    op.drop_index("idx_event_log_actor", table_name="action_event_log")
    op.drop_index("idx_event_log_correlation", table_name="action_event_log")
    op.drop_index("idx_event_log_type", table_name="action_event_log")
    op.drop_index("idx_event_log_org_item", table_name="action_event_log")
    op.drop_table("action_event_log")

    op.drop_index("idx_aci_owner", table_name="action_center_items")
    op.drop_index("idx_aci_site", table_name="action_center_items")
    op.drop_index("idx_aci_recent_closed", table_name="action_center_items")
    op.drop_index("idx_aci_unassigned", table_name="action_center_items")
    op.drop_index("idx_aci_stale", table_name="action_center_items")
    op.drop_index("idx_aci_lifecycle", table_name="action_center_items")
    op.drop_index("idx_aci_kind_domain", table_name="action_center_items")
    op.drop_index("idx_aci_priority_active", table_name="action_center_items")
    op.drop_table("action_center_items")

    op.drop_index("idx_recurrence_groups_org_status", table_name="recurrence_groups")
    op.drop_index("idx_recurrence_groups_org_signature", table_name="recurrence_groups")
    op.drop_table("recurrence_groups")

    op.drop_index("idx_duplicate_groups_org_status", table_name="duplicate_groups")
    op.drop_table("duplicate_groups")
