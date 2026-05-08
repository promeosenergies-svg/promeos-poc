"""
PROMEOS — Phase F1.7 (ADR-F-01) : backfill idempotent supplier_name → fournisseur_id.

Script one-shot post-déploiement Phase F1 : pour chaque EnergyContract avec
`fournisseur_id IS NULL` et `supplier_name` matchant un canonique connu,
remplit la FK.

Idempotent : filtre `fournisseur_id IS NULL` côté requête.
Insensible à la casse + trim espaces.
Log warnings pour les supplier_name non mappés (action manuelle requise).

Usage :
    cd backend && venv/bin/python -m scripts.backfill_fournisseur_id
"""

from __future__ import annotations

import logging
import sys
from collections import Counter

from sqlalchemy.orm import Session

# Phase F2 P1 fix code-reviewer : SoT canonique partagée (anti-couplage script→service)
from config.fournisseur_mappings import (
    SUPPLIER_NAME_TO_CANONICAL,
    normalize_supplier_name,
)
from database import SessionLocal
from models.billing_models import EnergyContract
from models.fournisseur import Fournisseur


logger = logging.getLogger(__name__)


def backfill_fournisseur_id(db: Session) -> dict:
    """Backfill idempotent supplier_name → fournisseur_id (canoniques uniquement).

    Returns:
        dict: {"updated": N, "unmapped": [supplier_name1, ...], "total_contracts": N}
    """
    contracts = db.query(EnergyContract).filter(EnergyContract.fournisseur_id.is_(None)).all()

    # Charger les canoniques en mémoire (10 lignes)
    canoniques = {f.nom: f for f in db.query(Fournisseur).filter(Fournisseur.organisation_id.is_(None)).all()}

    updated = 0
    unmapped: Counter = Counter()

    for c in contracts:
        normalized = normalize_supplier_name(c.supplier_name)
        canonical_key = SUPPLIER_NAME_TO_CANONICAL.get(normalized)
        if not canonical_key:
            unmapped[c.supplier_name] += 1
            continue

        canonical_fournisseur = canoniques.get(canonical_key)
        if not canonical_fournisseur:
            logger.warning(
                "Backfill : canonique %r introuvable en DB (seed manquant ?)",
                canonical_key,
            )
            unmapped[c.supplier_name] += 1
            continue

        c.fournisseur_id = canonical_fournisseur.id
        updated += 1

    db.commit()

    return {
        "updated": updated,
        "unmapped": dict(unmapped),
        "total_contracts": len(contracts),
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    db = SessionLocal()
    try:
        result = backfill_fournisseur_id(db)
        print(f"Backfill terminé : {result['updated']} contrats mis à jour.")
        if result["unmapped"]:
            print("Supplier_name non mappés (action manuelle requise) :")
            for name, count in result["unmapped"].items():
                print(f"  - {name!r} × {count}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
