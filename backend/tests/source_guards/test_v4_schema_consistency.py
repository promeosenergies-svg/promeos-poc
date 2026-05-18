"""5 source-guards V4 supplémentaires (Sprint M2-2).

Source : L9 §2 Sprint M2-2 + ADR-027 §11 (50 SG progressifs cible fin Mois 2).

Anti-régression sur le schéma DB V4 (migration `m2s2v4_create_v4_tables.py` +
8 SQLAlchemy models v4/).

Path canonique CI : `backend/tests/source_guards/`
(cf. .github/workflows/source_guards.yml ligne 22).

Cumul SG fin M2-2 : 9 V4-spécifiques (4 M2-1 + 5 M2-2).
Cumul SG cible fin M2-8 : 50 V4-spécifiques (cardinaux progressifs L9 §3).
"""

import re
from pathlib import Path

# Repo root = .../promeos-poc/ (3 levels up from this file)
REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_PATH = REPO_ROOT / "backend" / "alembic" / "versions" / "m2s2v4_create_v4_tables.py"
EVIDENCES_MODEL_PATH = REPO_ROOT / "backend" / "models" / "v4" / "evidences.py"


def _read_migration() -> str:
    """Lit la migration M2-2 V4. Échec test si introuvable."""
    assert MIGRATION_PATH.exists(), (
        f"V4 migration not found at {MIGRATION_PATH}. "
        f"Sprint M2-2 commit 3/5 doit créer ce fichier (cf. L9 §2 Sprint M2-2)."
    )
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_sg_5_chk_closure_consistency_present():
    """SG-5 (🛡️ IL10 cardinal) : chk_closure_consistency dans migration V4.

    La formule cardinale (ADR-025 §4.1) : lifecycle_state=closed ⇔ closed_at +
    closure_reason NOT NULL. Empêche silently-broken closures (item closed
    sans trace).
    """
    migration = _read_migration()
    assert "chk_closure_consistency" in migration, (
        "SG-5 violation: missing CHECK constraint chk_closure_consistency. Cf. ADR-025 §4.1 + IL10 cardinal Amine."
    )
    # Vérifier la formule cardinale (cohérent ADR-025 §4.1 + IL10)
    assert "lifecycle_state = 'closed'" in migration and "closed_at IS NOT NULL" in migration, (
        "SG-5 violation: chk_closure_consistency formula incorrect. "
        "Expected: (lifecycle_state = 'closed' AND closed_at IS NOT NULL AND closure_reason IS NOT NULL)"
        " OR (lifecycle_state != 'closed' AND closed_at IS NULL)"
    )


def test_sg_6_chk_event_type_covers_16_values():
    """SG-6 (IE7 + critère d'attention #9) : chk_event_type couvre 16 valeurs ADR-029.

    Renommages aval acceptés vs ADR-025 §4.3 (15 → 16 valeurs alignées doctrine v0.3) :
    - assigned → owner_changed
    - merged → closed_via_merged_duplicate
    - closed → 3 variantes (with_evidence + via_merged_duplicate + via_resolved_via_recurrence)
    """
    migration = _read_migration()
    required_event_types = [
        # Business 3 ans (7)
        "created",
        "state_changed",
        "owner_changed",
        "priority_changed",
        "blocker_added",
        "blocker_removed",
        "closed_via_merged_duplicate",
        # Compliance 5 ans (6)
        "evidence_added",
        "evidence_verified",
        "closed_with_evidence",
        "closed_via_resolved_via_recurrence",
        "reopened",
        "kind_corrected",
        # System 1 an (3)
        "bulk_updated",
        "exported",
        "priority_recalculated",
    ]
    assert len(required_event_types) == 16, "SG-6 internal: required list must be 16"

    missing = [et for et in required_event_types if f"'{et}'" not in migration]
    assert not missing, (
        f"SG-6 violation: chk_event_type missing {len(missing)}/16 event_types: {missing}. "
        f"Cf. ADR-029 §6.1 + L7 §3.4 — extension aval ADR-025 §4.3 acceptée par convention."
    )


def test_sg_7_evidence_expires_90d_documented_or_check():
    """SG-7 (IE6 cardinal) : règle 90j documentée ET référencée service Sprint M2-6.

    Note : `INTERVAL '90 days'` est PostgreSQL-only. SQLite refuse parsing.
    Solution adoptée commit 3/5 : règle 90j enforced côté service Python
    (backend.services.evidence Sprint M2-6) — single source of truth.
    Ce SG vérifie que la documentation IE6 référence bien ce mécanisme.
    """
    assert EVIDENCES_MODEL_PATH.exists(), f"Model evidences.py not found at {EVIDENCES_MODEL_PATH}"
    model_content = EVIDENCES_MODEL_PATH.read_text(encoding="utf-8")

    # Règle 90j IE6 doit être documentée
    assert "90 jours" in model_content or "90 days" in model_content, (
        "SG-7 violation: IE6 (90 days expiration) not documented in model evidences.py."
    )
    # Référence cardinale au service Sprint M2-6 qui enforce la règle Python-side
    assert "verify_evidence" in model_content or "Sprint M2-6" in model_content, (
        "SG-7 violation: missing reference to Sprint M2-6 service that enforces 90d rule. "
        "Add reference to backend.services.evidence.verify_evidence() (Python single source of truth)."
    )


def test_sg_8_all_8_v4_tables_have_organisation_id():
    """SG-8 (🛡️ IS1 cardinal + critère d'attention #10) : 8 tables V4 ont organisation_id.

    IS1 = colonne par laquelle TOUTE requête SQL filtre. Présence sur TOUTES
    les 8 tables V4 obligatoire (sécurité org-scoping).
    """
    migration = _read_migration()
    v4_tables = [
        "duplicate_groups",
        "recurrence_groups",
        "action_center_items",
        "action_event_log",
        "action_evidences",  # collision evidences legacy → renommé V4 commit 3/5
        "action_links",
        "action_blockers",
        "action_scenarios",
    ]

    for table in v4_tables:
        # Trouver le bloc op.create_table pour cette table
        pattern = rf'op\.create_table\(\s*["\']({table})["\']'
        match = re.search(pattern, migration)
        assert match, f"SG-8 internal: table {table} not found in migration"

        # Trouver organisation_id dans le bloc (heuristique : 3000 chars suivants)
        block = migration[match.start() : match.start() + 3000]
        assert "organisation_id" in block, (
            f"SG-8 violation: missing 'organisation_id' column in V4 table {table}. "
            f"Cf. IS1 cardinal (ADR-027 §3.1) — colonne org-scoping obligatoire sur "
            f"TOUTES les 8 tables V4 pour pattern repository (IS11)."
        )


def test_sg_9_action_event_log_has_schema_version_and_correlation_id():
    """SG-9 (IE7 + IS9) : action_event_log a schema_version + correlation_id.

    - IE7 : schema_version VARCHAR(10) NOT NULL pour Pydantic versionning
    - IS9 : correlation_id UUID NOT NULL pour traçabilité cross-actions

    Sans ces deux colonnes, l'audit trail métier perd sa structure stable
    (évolution payloads + IDOR forensique).
    """
    migration = _read_migration()

    # Trouver bloc action_event_log
    pattern = r'op\.create_table\(\s*["\']action_event_log["\']'
    match = re.search(pattern, migration)
    assert match, "SG-9 internal: action_event_log table not found in migration"

    block = migration[match.start() : match.start() + 3000]

    # IE7 schema_version
    assert "schema_version" in block, (
        "SG-9 violation: missing schema_version column in action_event_log. "
        "Cf. IE7 cardinal — Pydantic schemas v1/v2 versionning, registry "
        "EVENT_PAYLOAD_SCHEMAS lookup (event_type, schema_version)."
    )
    # IS9 correlation_id
    assert "correlation_id" in block, (
        "SG-9 violation: missing correlation_id column in action_event_log. "
        "Cf. IS9 cardinal — UUID propagé pour traçabilité cross-actions "
        "(bulk_updated, retention.purge.completed, etc.)."
    )
