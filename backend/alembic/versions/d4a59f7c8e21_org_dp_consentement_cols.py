"""org_dp_consentement_cols

Revision ID: d4a59f7c8e21
Revises: 2e78ecc6040c
Create Date: 2026-05-05

Sprint C-4 Phase 4.4 — Création des colonnes consentement RGPD (DataConnect Enedis +
ADICT GRDF) sur tables `organisations` et `delivery_points`. Implémentation ADR-007
(modèle RGPD consentement DataConnect+GRDF).

Pré-requis cardinal Phase 4.5 cascade vivante : la cascade
`Organisation.consentement_*_global` → DPs élec/gaz nécessite ces 8 colonnes
(D-Sprint-C3-Cascade-Consentement-Activation-001 successeur).

Périmètre Phase 4.4 (MVP cardinal — 8 cols total, +at uniquement) :
- organisations +4 cols :
  * consentement_dataconnect_global (Boolean nullable)
  * consentement_dataconnect_at (DateTime timezone-aware nullable)
  * consentement_grdf_global (Boolean nullable)
  * consentement_grdf_at (DateTime timezone-aware nullable)
- delivery_points +4 cols (override local possible vs global Org, ADR-007) :
  * consentement_dataconnect_local (Boolean nullable)
  * consentement_dataconnect_local_at (DateTime timezone-aware nullable)
  * consentement_grdf_local (Boolean nullable)
  * consentement_grdf_local_at (DateTime timezone-aware nullable)
- 1 index sur delivery_points.consentement_dataconnect_local (filtres fréquents
  cascade vivante Phase 4.5)

Champs ADR-007 reportés Sprint C-5+ (audit trail RGPD avancé) :
- consentement_*_by (FK users) — délégation security-auditor
- consentement_*_cgu_version (String) — versioning CGU explicite

Note : autogenerate Alembic a initialement produit ~17 op.drop_table() sur
des tables Enedis legacy + IAM (annotator_profiles, enedis_flux_mesure_r151,
unmatched_prm, etc.). Ces drops ont été RETIRÉS manuellement — pattern
identique aux migrations Sprint C-1/C-2/C-3 :
- c8f1246522f9 (Sprint C-1 Phase 3)
- f415992b3d25 (Sprint C-2 Phase 1.2)
- fcf1be2a087d (Sprint C-2 Phase 2)
- c2c806d24cd9 (Sprint C-2 Phase 4.2)
- 2e78ecc6040c (Sprint C-2 Phase 5.3)

7e épisode de discipline anti-DROP : backup `.original-autogenerate` conservé.
Cf. tracker dette D-Enedis-Legacy-001 (P2 Sprint C-7+).

Cette migration ne contient QUE :
- 8 op.add_column() (4 organisations + 4 delivery_points)
- 1 op.create_index() (delivery_points.consentement_dataconnect_local)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4a59f7c8e21"
down_revision: Union[str, None] = "2e78ecc6040c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add consentement RGPD columns to organisations + delivery_points."""

    # ─── Organisation +4 cols ──────────────────────────────────────────────
    op.add_column(
        "organisations",
        sa.Column(
            "consentement_dataconnect_global",
            sa.Boolean(),
            nullable=True,
            comment="Consentement DataConnect (Enedis) global org-level (ADR-007 Sprint C-4)",
        ),
    )
    op.add_column(
        "organisations",
        sa.Column(
            "consentement_dataconnect_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp dernier changement consentement DataConnect (RGPD audit trail)",
        ),
    )
    op.add_column(
        "organisations",
        sa.Column(
            "consentement_grdf_global",
            sa.Boolean(),
            nullable=True,
            comment="Consentement GRDF ADICT global org-level (court-circuit ELD locales préservé)",
        ),
    )
    op.add_column(
        "organisations",
        sa.Column(
            "consentement_grdf_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp dernier changement consentement GRDF (RGPD audit trail)",
        ),
    )

    # ─── DeliveryPoint +4 cols (override local) ────────────────────────────
    op.add_column(
        "delivery_points",
        sa.Column(
            "consentement_dataconnect_local",
            sa.Boolean(),
            nullable=True,
            comment="Override local DataConnect par PRM (Phase 4.5 cascade ADR-007)",
        ),
    )
    op.add_column(
        "delivery_points",
        sa.Column(
            "consentement_dataconnect_local_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp override local DataConnect (RGPD audit)",
        ),
    )
    op.add_column(
        "delivery_points",
        sa.Column(
            "consentement_grdf_local",
            sa.Boolean(),
            nullable=True,
            comment="Override local GRDF par PCE (cascade Phase 4.5 — uniquement grd_code=GRDF)",
        ),
    )
    op.add_column(
        "delivery_points",
        sa.Column(
            "consentement_grdf_local_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp override local GRDF (RGPD audit)",
        ),
    )

    # ─── Index pour cascade Phase 4.5 (filtres fréquents) ───────────────────
    op.create_index(
        "ix_delivery_points_consentement_dataconnect_local",
        "delivery_points",
        ["consentement_dataconnect_local"],
        unique=False,
    )


def downgrade() -> None:
    """Defensive downgrade (NE PAS exécuter en prod — discipline anti-DROP Phase C).

    Présent uniquement pour cohérence Alembic. Doctrine PROMEOS : les colonnes
    consentement RGPD sont RGPD-protégées, leur drop nécessite procédure dédiée
    avec délégation security-auditor + sauvegarde audit trail conforme CNIL.
    """
    op.drop_index("ix_delivery_points_consentement_dataconnect_local", "delivery_points")
    op.drop_column("delivery_points", "consentement_grdf_local_at")
    op.drop_column("delivery_points", "consentement_grdf_local")
    op.drop_column("delivery_points", "consentement_dataconnect_local_at")
    op.drop_column("delivery_points", "consentement_dataconnect_local")
    op.drop_column("organisations", "consentement_grdf_at")
    op.drop_column("organisations", "consentement_grdf_global")
    op.drop_column("organisations", "consentement_dataconnect_at")
    op.drop_column("organisations", "consentement_dataconnect_global")
