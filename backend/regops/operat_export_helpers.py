"""
PROMEOS RegOps — OPERAT export helpers (Sprint C-8 Phase 8.1, ADR-020 Option C hybride).

Cardinal post-Phase 7.1 (`s_ce_m2` colonne ajoutée Site) :
- `tertiaire_area_m2` reste **dénominateur scoring** intensity_kwh_m2 (cohérent OPERAT déclaratif ADEME)
- `s_ce_m2` est utilisé pour **export OPERAT v2** (Arrêté 10/04/2020 art. 2-j NOR LOGL2005904A)

Helper `resolve_surface_for_operat_export()` priorise `s_ce_m2` quand non-NULL,
fallback `tertiaire_area_m2` (rétro-compat absolue Phase C+).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.site import Site


# Source légale de la définition Surface CE
_OPERAT_V2_SURFACE_CE_REFERENCE = "Surface CE — Arrêté 10/04/2020 art. 2-j (NOR LOGL2005904A)"
_OPERAT_LEGACY_SURFACE_REFERENCE = "Surface tertiaire assujettie (legacy fallback)"


def resolve_surface_for_operat_export(site: "Site") -> tuple[float, str]:
    """Résout la surface à utiliser pour export OPERAT v2 selon ADR-020 Option C hybride.

    Priorité :
      1. `site.s_ce_m2` si renseigné → Surface CE post-Arrêté 10/04/2020 art. 2-j
      2. `site.tertiaire_area_m2` fallback → Surface tertiaire assujettie (legacy MVP Phase C-)
      3. 0.0 fallback ultime (déclaration incomplète, sera signalé qa)

    Args:
        site: instance Site avec colonnes `s_ce_m2`, `tertiaire_area_m2` (Phase 7.1).

    Returns:
        Tuple (surface_m2, label_source) — label utilisé pour traçabilité export OPERAT v2.

    CARDINAL : utilisé UNIQUEMENT pour export déclaration OPERAT v2.
    Le scoring intensity_kwh_m2 (DT/BACS/APER) continue d'utiliser `tertiaire_area_m2`
    via `regops/rules/dpe_tertiaire.py:67` (statu quo Phase C+ ADR-020).
    """
    s_ce = getattr(site, "s_ce_m2", None)
    if s_ce is not None and s_ce > 0:
        return (float(s_ce), _OPERAT_V2_SURFACE_CE_REFERENCE)

    tert = getattr(site, "tertiaire_area_m2", None)
    if tert is not None and tert > 0:
        return (float(tert), _OPERAT_LEGACY_SURFACE_REFERENCE)

    return (0.0, "Surface non renseignée — déclaration incomplète")


def is_operat_v2_ready(site: "Site") -> bool:
    """True si le site est prêt pour export OPERAT v2 (s_ce_m2 renseigné explicitement)."""
    return getattr(site, "s_ce_m2", None) is not None and site.s_ce_m2 > 0
