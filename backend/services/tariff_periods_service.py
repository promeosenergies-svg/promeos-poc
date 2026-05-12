"""
PROMEOS — services/tariff_periods_service.py (ADR-022 F.18).

Service de résolution des plages tarifaires HP/HC actives pour un scope.

Source de vérité ordonnée :
  1. EnergyContract.metadata_json['tariff_periods'] (paramétrage onboarding)
  2. Fallback TURPE 6 standard : HC = 0h-7h + 22h-23h, HP = 8h-21h
     (cf CRE délibération TURPE 6 + skill `promeos-energy-fundamentals`)

Le service expose deux fonctions :
  - get_active_hp_hc_zones(db, org_id) → dict avec hc_hours, hp_hours, hc_zones
  - classify_hour_tariff(hour, hp_hc_zones) → 'HP' | 'HC' selon zone

F.18 cible la doctrine ADR-022 §Chart line — plages HP/HC :
"ContractEnergy.tariff_periods (matrice §4.4.G #G-22) OU fallback TURPE 6
config/tarifs_reglementaires.yaml". Ce service implémente cette résolution.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from models import EnergyContract, Site
from models.billing_models import BillingEnergyType
from services.scope_utils import sites_for_org_query

logger = logging.getLogger(__name__)


# ── Plages TURPE 6 standard (fallback) ──────────────────────────────────────
# Référence : CRE Délibération 2025-15 du 23/01/2025, TURPE 6 en vigueur.
# Plages "tarif vert/jaune" pour C2-C5. La nuit (22h-6h ou 0h-7h selon ELD)
# + jours fériés sont HC. On retient ici une plage simple "0h-7h + 22h-23h"
# qui couvre la majorité des contrats tertiaires C5.
TURPE_6_DEFAULT_HC_HOURS: set[int] = set(range(0, 8)) | {22, 23}  # 0-7h + 22-23h
TURPE_6_DEFAULT_HP_HOURS: set[int] = set(range(8, 22))  # 8h-21h

# Format hc_zones (pour ChartFrameLine.jsx renderer) :
# liste de {from_h: int, to_h: int} — intervalles inclusifs
TURPE_6_DEFAULT_HC_ZONES: list[dict] = [
    {"from_h": 0, "to_h": 7},
    {"from_h": 22, "to_h": 23},
]


# ── API publique ─────────────────────────────────────────────────────────────


def get_active_hp_hc_zones(
    db: Session,
    org_id: Optional[int],
    energy_type: BillingEnergyType = BillingEnergyType.ELEC,
) -> dict:
    """Résout les plages HP/HC actives pour le scope.

    Stratégie :
      1. Cherche un EnergyContract électricité actif sur les sites du scope
         avec un `metadata_json['tariff_periods']` peuplé.
      2. Si trouvé, parse et retourne ces plages.
      3. Sinon, fallback TURPE 6 standard.

    Returns:
        {
            "hc_hours": set[int],   # heures classées HC
            "hp_hours": set[int],   # heures classées HP
            "hc_zones": list[dict], # intervalles {from_h, to_h} pour renderer
            "source": "contract" | "turpe_6_default",
            "contract_id": int | None,
        }
    """
    # Trouve un contrat actif électricité sur le scope avec tariff_periods.
    site_ids = [s.id for s in sites_for_org_query(db, org_id).with_entities(Site.id).all()]
    if site_ids:
        contracts = (
            db.query(EnergyContract)
            .filter(
                EnergyContract.site_id.in_(site_ids),
                EnergyContract.energy_type == energy_type,
                EnergyContract.metadata_json.isnot(None),
            )
            .all()
        )
        for contract in contracts:
            parsed = _parse_tariff_periods(contract.metadata_json)
            if parsed:
                hc_zones, hc_hours, hp_hours = parsed
                return {
                    "hc_hours": hc_hours,
                    "hp_hours": hp_hours,
                    "hc_zones": hc_zones,
                    "source": "contract",
                    "contract_id": contract.id,
                }

    # Fallback TURPE 6 standard.
    return {
        "hc_hours": TURPE_6_DEFAULT_HC_HOURS,
        "hp_hours": TURPE_6_DEFAULT_HP_HOURS,
        "hc_zones": TURPE_6_DEFAULT_HC_ZONES,
        "source": "turpe_6_default",
        "contract_id": None,
    }


def classify_hour_tariff(hour: int, zones: dict) -> str:
    """Classe une heure en 'HP' ou 'HC' selon les zones actives.

    Args:
        hour : 0-23
        zones : dict retourné par get_active_hp_hc_zones (clés hc_hours/hp_hours)

    Returns:
        'HC' si l'heure est en heures creuses, 'HP' sinon.
    """
    if hour in zones.get("hc_hours", set()):
        return "HC"
    return "HP"


# ── Parser interne ──────────────────────────────────────────────────────────


def _parse_tariff_periods(metadata_json_raw: Optional[str]) -> Optional[tuple]:
    """Parse EnergyContract.metadata_json pour extraire les tariff_periods.

    Format attendu (à seeder Phase 4 patrimoine matrice §4.4.G #G-22) :
        {
            "tariff_periods": {
                "hc_zones": [
                    {"from_h": 0, "to_h": 7},
                    {"from_h": 22, "to_h": 23}
                ]
            }
        }

    Returns:
        Tuple (hc_zones, hc_hours, hp_hours) si parsable, None sinon.
    """
    if not metadata_json_raw:
        return None
    try:
        meta = json.loads(metadata_json_raw)
    except (json.JSONDecodeError, TypeError):
        logger.debug("tariff_periods_service: metadata_json non parsable")
        return None

    periods = meta.get("tariff_periods") if isinstance(meta, dict) else None
    if not isinstance(periods, dict):
        return None

    hc_zones_raw = periods.get("hc_zones")
    if not isinstance(hc_zones_raw, list) or not hc_zones_raw:
        return None

    # Validation des zones + dérive hc_hours / hp_hours.
    hc_hours: set[int] = set()
    cleaned_zones: list[dict] = []
    for z in hc_zones_raw:
        if not isinstance(z, dict):
            continue
        from_h = z.get("from_h")
        to_h = z.get("to_h")
        if not isinstance(from_h, int) or not isinstance(to_h, int):
            continue
        if not (0 <= from_h <= 23) or not (0 <= to_h <= 23) or from_h > to_h:
            continue
        for h in range(from_h, to_h + 1):
            hc_hours.add(h)
        cleaned_zones.append({"from_h": from_h, "to_h": to_h})

    if not hc_hours:
        return None

    hp_hours = set(range(24)) - hc_hours
    return (cleaned_zones, hc_hours, hp_hours)
