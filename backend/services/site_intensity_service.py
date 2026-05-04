"""Service calcul intensité énergétique site (matrice v1 §4.4.F #56).

Sprint C-2 Phase 4.2 — comble GAP audit Phase B R7 (calcul kWh/m² inline FE).

Doctrine PROMEOS — 2 intensités persistées par site :
- intensity_kwh_m2_total      = annual_kwh_total / surface_m2          (UI legacy)
- intensity_kwh_m2_tertiaire  = annual_kwh_total / tertiaire_area_m2   (doctrine OPERAT/DT)

Garde-fous :
- Aucune intensity n'est calculée si annual_kwh_total est None ou 0
  (pas de données de consommation).
- Aucune intensity n'est calculée si la surface correspondante est None ou 0
  (division par zéro évitée → retourne None, pas NaN, pas Infinity).
- Anti-cycle : intensity n'est PAS source de cascade vers compliance_score.
  Cascade unidirectionnelle (annual_kwh_total / surface_m2 / tertiaire_area_m2
  → intensity_*).

API publique :
- compute_site_intensities(site)   → dict {intensity_kwh_m2_total, intensity_kwh_m2_tertiaire}
- persist_site_intensities(db, site) → écrit sur Site et flush (caller commit)
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session


_logger = logging.getLogger(__name__)


def _safe_intensity(annual_kwh: Optional[float], surface: Optional[float]) -> Optional[float]:
    """Retourne `annual_kwh / surface` arrondi 2 décimales, ou None si pas calculable.

    Cas null-safe :
    - annual_kwh None ou ≤ 0       → None
    - surface None ou ≤ 0          → None (évite division par zéro)
    - tout autre cas               → round(annual_kwh / surface, 2)
    """
    if annual_kwh is None or annual_kwh <= 0:
        return None
    if surface is None or surface <= 0:
        return None
    return round(annual_kwh / surface, 2)


def compute_site_intensities(site) -> dict:
    """Calcule les 2 intensités énergétiques d'un site (sans persistance).

    Args:
        site: instance ORM Site (ou MagicMock pour tests unit).

    Returns:
        dict avec 2 clés :
        - "intensity_kwh_m2_total"     : Optional[float] arrondi 2 décimales
        - "intensity_kwh_m2_tertiaire" : Optional[float] arrondi 2 décimales

        None pour chaque clé si données incomplètes (cf. _safe_intensity).

    Source : matrice v1 §4.4.F #56 + doctrine PROMEOS Sprint C-2 Phase 4.2.
    """
    annual_kwh = getattr(site, "annual_kwh_total", None)
    surface_total = getattr(site, "surface_m2", None)
    surface_tertiaire = getattr(site, "tertiaire_area_m2", None)

    return {
        "intensity_kwh_m2_total": _safe_intensity(annual_kwh, surface_total),
        "intensity_kwh_m2_tertiaire": _safe_intensity(annual_kwh, surface_tertiaire),
    }


def persist_site_intensities(db: Session, site) -> dict:
    """Calcule et persiste les 2 intensités sur le Site (flush, pas de commit).

    Args:
        db: session SQLAlchemy
        site: instance Site

    Returns:
        dict des 2 intensités calculées (cf. compute_site_intensities).

    Note : caller doit `db.commit()` ou laisser cascade_recompute_service le faire.
    """
    intensities = compute_site_intensities(site)
    site.intensity_kwh_m2_total = intensities["intensity_kwh_m2_total"]
    site.intensity_kwh_m2_tertiaire = intensities["intensity_kwh_m2_tertiaire"]
    db.flush()
    return intensities
