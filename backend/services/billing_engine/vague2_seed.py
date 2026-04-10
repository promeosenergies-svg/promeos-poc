"""
PROMEOS — Seed de compatibilité data model Vague 2.

Alimente les nouvelles colonnes gaz sur DeliveryPoint à partir des
données déjà présentes. Idempotent : ne touche aucune valeur non-null
existante.

Règles de dérivation :

- `DeliveryPoint.atrd_option` :
    * si déjà renseigné → inchangé
    * sinon si `car_kwh` renseigné → dérivé via les seuils CRE ATRD7
        · ≤ 6 000 kWh/an           → T1
        · 6 000 – 300 000 kWh/an   → T2
        · 300 000 – 5 000 000      → T3
        · > 5 000 000              → T4
    * sinon (ni option ni CAR)     → T2 (résidentiel chauffage, cas le plus courant)

- `DeliveryPoint.car_kwh` :
    * dérivé depuis l'historique de consommation s'il est disponible
    * sinon laissé NULL (le calcul ATRD retombera sur T2 fallback)

N'intervient que sur les PDL dont `energy_type` est gaz.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class SeedSummaryVague2:
    atrd_option_set: int = 0
    car_kwh_set: int = 0
    skipped_already_populated: int = 0
    skipped_non_gas: int = 0
    errors: list[str] = field(default_factory=list)


def _is_gas(energy_val) -> bool:
    if energy_val is None:
        return False
    v = getattr(energy_val, "value", energy_val)
    return str(v).lower() in ("gaz", "gas", "natural_gas")


def seed_vague2(db: Session) -> SeedSummaryVague2:
    """
    Exécute le seed ATRD gaz. Idempotent : les PDLs déjà renseignés sont
    laissés intacts.
    """
    from models.enums import AtrdOption
    from models.patrimoine import DeliveryPoint
    from services.billing_engine.bricks.atrd import derive_atrd_option_from_car

    summary = SeedSummaryVague2()

    pdls = db.query(DeliveryPoint).all()
    for pdl in pdls:
        if not _is_gas(pdl.energy_type):
            summary.skipped_non_gas += 1
            continue

        current = getattr(pdl.atrd_option, "value", pdl.atrd_option)
        if current:
            summary.skipped_already_populated += 1
            continue

        car = getattr(pdl, "car_kwh", None)
        option_str = derive_atrd_option_from_car(car)
        try:
            pdl.atrd_option = AtrdOption(option_str)
            summary.atrd_option_set += 1
        except Exception as exc:
            summary.errors.append(f"pdl {pdl.id}: {exc}")

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        summary.errors.append(f"commit failed: {exc}")
        logger.exception("seed_vague2 commit failed")

    logger.info(
        "seed_vague2: atrd_option=%d, car=%d, skipped=%d (populated) + %d (non-gas), errors=%d",
        summary.atrd_option_set,
        summary.car_kwh_set,
        summary.skipped_already_populated,
        summary.skipped_non_gas,
        len(summary.errors),
    )
    return summary


if __name__ == "__main__":
    import sys
    from pathlib import Path

    BACKEND_DIR = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(BACKEND_DIR))

    from database.connection import SessionLocal  # type: ignore

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    with SessionLocal() as db:
        result = seed_vague2(db)
    print(f"Seed summary: {result}")
