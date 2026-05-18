"""Seed V4 minimal idempotent — Sprint M2-4.1.bis.

Seede `action_center_items` (3 items représentatifs, cf. `v4_seed_constants`)
rattachés à une organisation EXISTANTE.

Idempotence (D3) — chaque item porte une PK UUID5 déterministe ; un item déjà
présent est ignoré. C'est l'équivalent portable de `INSERT OR IGNORE` (sans SQL
dialecte-spécifique : fonctionne SQLite ET PostgreSQL) et il fournit un compte
exact créés/ignorés. Deux runs consécutifs ⇒ COUNT identique, 0 doublon (C1).

Org-scoping (D1/D5) — le seed NE crée PAS d'organisation. Il exige que l'org
cible existe (sinon `SeedError`) ; la FK `organisation_id` ON DELETE RESTRICT
interdit de toute façon un item orphelin. La création d'organisations
appartient au seed HELIOS legacy.

PRAGMA — `foreign_keys=ON` est garanti par `database/connection.py` pour toute
session de production ; aucune action requise côté seed (cf. contrainte C2).
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.organisation import Organisation
from models.v4.action_center_items import ActionCenterItem
from seeds.v4_seed_constants import SEED_ACTION_SPECS, SEED_ORG_ID, seed_item_uuid


class SeedError(RuntimeError):
    """Le seed V4 ne peut pas s'exécuter (organisation cible absente)."""


@dataclass
class SeedReport:
    """Résultat d'un run de seed V4."""

    org_id: int
    items_created: int
    items_skipped: int

    def __str__(self) -> str:
        return (
            f"seed V4 — org_id={self.org_id} · "
            f"items créés={self.items_created} · "
            f"ignorés (déjà présents)={self.items_skipped}"
        )


def _require_org(db: Session, org_id: int) -> None:
    """Vérifie que l'organisation cible existe. Lève `SeedError` sinon.

    Requête limitée à la colonne `id` → compatible aussi bien avec la table
    `organisations` réelle qu'avec un stub de test (id PK seul).
    """
    exists = db.scalar(select(Organisation.id).where(Organisation.id == org_id))
    if exists is None:
        raise SeedError(
            f"Organisation id={org_id} introuvable — le seed V4 ne crée pas "
            f"d'organisation. Lancer le seed HELIOS d'abord "
            f"(python -m services.demo_seed --pack helios --size S), "
            f"ou passer un org_id existant."
        )


def _seed_action_items(db: Session, org_id: int) -> tuple[int, int]:
    """Seede les action_center_items des specs. Idempotent (skip si PK présente).

    Returns:
        (créés, ignorés).
    """
    created = 0
    skipped = 0
    for spec in SEED_ACTION_SPECS:
        item_id = seed_item_uuid(spec["slug"])
        if db.get(ActionCenterItem, item_id) is not None:
            skipped += 1
            continue
        item = ActionCenterItem(
            id=item_id,
            organisation_id=org_id,
            kind=spec["kind"],
            title=spec["title"],
            lifecycle_state=spec["lifecycle_state"],
            priority_bracket=spec["priority_bracket"],
            priority_score=spec["priority_score"],
        )
        # IL10 (chk_closure_consistency) : lifecycle_state='closed' exige
        # closed_at ET closure_reason NOT NULL.
        if spec["lifecycle_state"] == "closed":
            item.closed_at = datetime.now(UTC)
            item.closure_reason = spec["closure_reason"]
        db.add(item)
        db.flush()  # flush par item : isole une éventuelle violation CHECK
        created += 1
    return created, skipped


def seed_v4_minimal(db: Session, *, org_id: int = SEED_ORG_ID, force: bool = False) -> SeedReport:
    """Seede les tables V4 minimales de façon idempotente.

    Args:
        db: session SQLAlchemy. `PRAGMA foreign_keys=ON` doit être actif (garanti
            par `database/connection.py` pour toute session de production).
        org_id: organisation cible (défaut `SEED_ORG_ID`=1, HELIOS). Doit exister.
        force: réservé M2-4.x — no-op aujourd'hui (idempotence stricte).

    Returns:
        SeedReport(org_id, items_created, items_skipped).

    Raises:
        SeedError: si l'organisation cible n'existe pas.
    """
    _ = force  # réservé futur — l'idempotence reste stricte en M2-4.1.bis
    _require_org(db, org_id)
    created, skipped = _seed_action_items(db, org_id)
    db.commit()
    return SeedReport(org_id=org_id, items_created=created, items_skipped=skipped)


def main() -> None:
    """Point d'entrée CLI : `python -m seeds.v4_seed [--org-id N]`.

    Utilise `SessionLocal` de production (`PRAGMA foreign_keys=ON` garanti).
    """
    import argparse
    import sys

    from database.connection import SessionLocal

    parser = argparse.ArgumentParser(
        prog="python -m seeds.v4_seed",
        description="Seed V4 minimal idempotent (action_center_items).",
    )
    parser.add_argument(
        "--org-id",
        type=int,
        default=SEED_ORG_ID,
        help=f"organisation cible (défaut {SEED_ORG_ID}, HELIOS). Doit exister.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        report = seed_v4_minimal(db, org_id=args.org_id)
    except SeedError as exc:
        print(f"ERREUR seed V4 : {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()
    print(report)


if __name__ == "__main__":
    main()
