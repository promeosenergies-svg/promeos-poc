"""p0fix_action_center_external_ref — Action Center V4 P0 fix (2026-05-25).

Sprint Action Center V4 P0 sources/links/resilience/idempotence (audit deep
§5.3 + §6) : structurer la signature d'idempotence cross-brique pour
garantir zéro doublon DB sur les syncs Billing/Conformité (avant : title
matching applicatif vulnérable en race condition).

Changements (additifs uniquement, Q13-B compliant) :
  1. ALTER TABLE action_center_items ADD COLUMN external_ref VARCHAR(120) NULL.
  2. ALTER TABLE action_center_items ADD COLUMN source_url   VARCHAR(500) NULL.
  3. Backfill external_ref pour les items legacy billing : parse le pattern
     « EXTERNAL_REF: billing_anomaly:{N} » présent dans `description`, peuple
     la colonne, et pose `source_url='/bill-intel?anomaly={N}'`.
  4. Dedupe légère AVANT index UNIQUE : si plusieurs items partagent le
     même `(organisation_id, external_ref)`, on garde l'item ouvert le plus
     récent et on marque les autres `closure_reason='merged_duplicate'` avec
     `closed_at=now()`, `lifecycle_state='closed'` — préserve les clôtures
     utilisateur (jamais ressuscitées).
  5. CREATE UNIQUE INDEX idx_aci_external_ref (organisation_id, external_ref)
     WHERE external_ref IS NOT NULL.

Revision ID: p0fix_acref
Revises: m26b1impact
"""

import re
import sqlalchemy as sa
from alembic import op
from datetime import datetime, timezone


revision = "p0fix_acref"
down_revision = "m26b1impact"
branch_labels = None
depends_on = None


_BILLING_REF_RE = re.compile(r"EXTERNAL_REF:\s*billing_anomaly:(\d+)")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # 1-2. Add columns (nullable, additive only — pas de défaut bruyant).
    with op.batch_alter_table("action_center_items") as batch:
        batch.add_column(sa.Column("external_ref", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("source_url", sa.String(length=500), nullable=True))

    # 3. Backfill billing items legacy : parse `description` pour extraire
    #    l'id d'anomalie référencé, et peupler external_ref + source_url.
    items = bind.execute(
        sa.text(
            "SELECT id, description FROM action_center_items "
            "WHERE domain = 'facturation' AND external_ref IS NULL "
            "AND description LIKE '%EXTERNAL_REF: billing_anomaly:%'"
        )
    ).fetchall()
    for row in items:
        m = _BILLING_REF_RE.search(row.description or "")
        if not m:
            continue
        anomaly_id = m.group(1)
        bind.execute(
            sa.text("UPDATE action_center_items SET external_ref = :ref, source_url = :url WHERE id = :id"),
            {
                "ref": f"billing_anomaly:{anomaly_id}",
                "url": f"/bill-intel?anomaly={anomaly_id}",
                "id": row.id,
            },
        )

    # 4. Dedupe AVANT index UNIQUE. Stratégie (audit §5.3) :
    #    - identifier les groupes (organisation_id, external_ref) avec count > 1
    #    - garder l'item ouvert le plus récent (ou le plus récent tout court si tous fermés)
    #    - les autres : closure_reason='merged_duplicate' + closed_at=now()
    #      pour préserver les clôtures utilisateur existantes (jamais ressuscitées).
    dups = bind.execute(
        sa.text(
            "SELECT organisation_id, external_ref, COUNT(*) AS n "
            "FROM action_center_items "
            "WHERE external_ref IS NOT NULL "
            "GROUP BY organisation_id, external_ref HAVING COUNT(*) > 1"
        )
    ).fetchall()
    now_iso = datetime.now(timezone.utc).isoformat()
    for d in dups:
        rows = bind.execute(
            sa.text(
                "SELECT id, lifecycle_state, updated_at FROM action_center_items "
                "WHERE organisation_id = :org AND external_ref = :ref "
                "ORDER BY (lifecycle_state != 'closed') DESC, updated_at DESC, created_at DESC"
            ),
            {"org": d.organisation_id, "ref": d.external_ref},
        ).fetchall()
        # Garder le 1er (ouvert le + récent ou le + récent tout court),
        # marquer les autres merged_duplicate.
        for r in rows[1:]:
            if r.lifecycle_state != "closed":
                bind.execute(
                    sa.text(
                        "UPDATE action_center_items "
                        "SET lifecycle_state = 'closed', "
                        "    closed_at = :now, "
                        "    closure_reason = 'merged_duplicate' "
                        "WHERE id = :id"
                    ),
                    {"now": now_iso, "id": r.id},
                )

    # 5. Index UNIQUE partiel (cohérent ORM action_center_items.py idx_aci_external_ref).
    if dialect == "postgresql":
        op.execute(
            "CREATE UNIQUE INDEX idx_aci_external_ref ON action_center_items "
            "(organisation_id, external_ref) WHERE external_ref IS NOT NULL"
        )
    else:
        # SQLite : partial index syntax similaire.
        op.execute(
            "CREATE UNIQUE INDEX idx_aci_external_ref ON action_center_items "
            "(organisation_id, external_ref) WHERE external_ref IS NOT NULL"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_aci_external_ref")
    with op.batch_alter_table("action_center_items") as batch:
        batch.drop_column("source_url")
        batch.drop_column("external_ref")
