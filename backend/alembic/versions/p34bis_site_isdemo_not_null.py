"""Phase 3.4-bis Correctif #4 — Site.is_demo NOT NULL DEFAULT FALSE (P0 audit Sprint F)

Risque production critique identifié audit Sprint F CS staff engineer :
le filtre F.4 `Site.is_demo == Organisation.is_demo` (commit ff2b3a4d)
applique une comparaison SQL. Si un site existe avec `is_demo=NULL`
(insertion directe SQL, fixture pytest sans valeur, import CSV onboarding
sans champ), alors `NULL == False` retourne `NULL` (≠ TRUE) → le site
est silencieusement filtré OUT du résultat.

Combiné aux 13 callsites cockpit.py + helpers `_sites_for_org` factorisés
post-Correctif #3, un site avec is_demo NULL = site invisible côté API.
Cockpit vide pour le premier pilote client réel = scénario inacceptable.

Cette migration :
  1. Backfill `is_demo = FALSE` pour tous les sites où `is_demo IS NULL`
     (production-safe : aucun site demo HELIOS n'a NULL — seuls les
     parasites de tests d'intégration peuvent en avoir).
  2. Ajoute la contrainte `NOT NULL DEFAULT FALSE` sur la colonne.

Pattern Phase D-4 anti-DROP discipline : aucune colonne supprimée,
opération idempotente (vérification existant + non-null).

Source : audit Sprint F CS verdict — "Si on déploie tel quel, le filtre
casse silencieusement la prod multi-tenant dès le premier client réel."

Revision ID: p34bisisd
Revises: l7r29idx
Create Date: 2026-05-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "p34bisisd"
down_revision: Union[str, Sequence[str], None] = "l7r29idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Phase 3.4-bis Correctif #4 — backfill + NOT NULL sur Site.is_demo."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"]: c for c in inspector.get_columns("sites")}

    if "is_demo" not in cols:
        # Colonne absente (cas improbable, model.site.py:278 la déclare) → skip
        return

    # 1. Backfill NULL → FALSE (idempotent, safe sur n'importe quelle DB).
    op.execute("UPDATE sites SET is_demo = 0 WHERE is_demo IS NULL")

    # 2. Ajout contrainte NOT NULL si pas déjà présente.
    if cols["is_demo"].get("nullable", True):
        with op.batch_alter_table("sites") as batch_op:
            batch_op.alter_column(
                "is_demo",
                existing_type=sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )


def downgrade() -> None:
    """Rollback : relâche la contrainte NOT NULL (mais conserve les valeurs FALSE backfillées).

    Note : un rollback complet impliquerait de restaurer les NULLs originaux,
    ce qui est impossible (information perdue par le backfill). On laisse les
    valeurs FALSE en place — la colonne redevient simplement nullable.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"]: c for c in inspector.get_columns("sites")}

    if "is_demo" not in cols:
        return

    if not cols["is_demo"].get("nullable", True):
        with op.batch_alter_table("sites") as batch_op:
            batch_op.alter_column(
                "is_demo",
                existing_type=sa.Boolean(),
                nullable=True,
            )
