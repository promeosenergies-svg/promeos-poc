"""
SF5 — PRM Matcher : résout un PRM 14 chiffres vers un meter.id unique.

Règle D19 : exact-one-meter
- DeliveryPoint.code = PRM
- Meter.delivery_point_id FK, is_active=True, energy_vector='ELECTRICITY'
- Exactement 1 meter actif requis, sinon bloqué
"""

import logging

from sqlalchemy.orm import Session

from models.patrimoine import DeliveryPoint
from models.energy_models import Meter

logger = logging.getLogger(__name__)


class PrmMatchResult:
    """Résultat du matching PRM → meter_id."""

    __slots__ = ("meter_id", "block_reason")

    def __init__(self, meter_id: int | None = None, block_reason: str | None = None):
        self.meter_id = meter_id
        self.block_reason = block_reason

    @property
    def matched(self) -> bool:
        return self.meter_id is not None


def resolve_prm(db: Session, prm_code: str) -> PrmMatchResult:
    """Résout un PRM vers exactement un meter_id actif électricité.

    Retourne PrmMatchResult avec meter_id ou block_reason.
    """
    if not prm_code or len(prm_code.strip()) != 14:
        return PrmMatchResult(block_reason="invalid_prm_format")

    prm = prm_code.strip()

    # Étape 1 : trouver le DeliveryPoint
    dp = db.query(DeliveryPoint).filter(DeliveryPoint.code == prm).first()
    if not dp:
        return PrmMatchResult(block_reason="no_delivery_point")

    # Étape 2 : trouver les compteurs actifs électricité sur ce DP
    meters = (
        db.query(Meter)
        .filter(
            Meter.delivery_point_id == dp.id,
            Meter.is_active.is_(True),
        )
        .all()
    )

    # Filtrer sur energy_vector ELECTRICITY (attribut peut être enum ou string)
    elec_meters = []
    for m in meters:
        ev = getattr(m, "energy_vector", None)
        if ev is None:
            continue
        ev_str = ev.value if hasattr(ev, "value") else str(ev)
        if ev_str.upper() in ("ELECTRICITY", "ELEC", "ELECTRICITE"):
            elec_meters.append(m)

    if not elec_meters:
        return PrmMatchResult(block_reason="no_active_meter")

    if len(elec_meters) > 1:
        return PrmMatchResult(block_reason="multiple_active_meters")

    return PrmMatchResult(meter_id=elec_meters[0].id)
