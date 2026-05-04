"""
PROMEOS — Portfolio Intensity Service (Sprint C-3 Phase 3.4).

Agrégat patrimoine : `Σ(Site.annual_kwh_total) / Σ(Site.surface_m2)` org-scopé.

Doctrine PROMEOS :
- Le ratio des SOMMES (et NON la moyenne arithmétique des ratios sites).
- Mathématiquement correct pour un portefeuille pondéré par taille.
- Exemple : site A (100 kWh / 1 m²) + site B (1 kWh / 100 m²) :
  * Moyenne arithmétique = 50.5 kWh/m²       (FAUX — pondère pareil un site géant et un placard)
  * Σ/Σ = 101 / 101 = 1.0 kWh/m²              (CORRECT — pondéré par surface)

⚠️ Cohabitation avec `services/energy_intensity_service.get_portfolio_intensity` :
- `energy_intensity_service` calcule depuis **Meter readings** (réel mesuré, fiable).
- `portfolio_intensity_service` (ce module) calcule depuis **Site.annual_kwh_total**
  (snapshot patrimoine, simple, agrégat org/portef rapide).
Distinction sémantique pour 2 cas d'usage différents :
- Cockpit/RegOps précision réelle → energy_intensity_service
- Patrimoine.jsx KpiStripItem global rapide → portfolio_intensity_service (Phase 4.3 dette
  D-Phase4-3-Portfolio-Intensity-Backend-001 levée).

Convention kWhEF PCI :
- `Site.annual_kwh_total` est en kWh **énergie finale (EF) PCI** uniquement.
- Source-guard : `tests/source_guards/test_annual_kwh_total_kwhef_pci_source_guards.py`
  (D-Phase4-2-EnergieFinale-Source-Guard-001 levée).
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from models import EntiteJuridique, Portefeuille, Site, not_deleted


def compute_portfolio_intensity(
    db: Session,
    organisation_id: int,
    portefeuille_id: Optional[int] = None,
) -> dict:
    """Calcule l'intensité agrégée d'un portefeuille (ou de toute une organisation).

    Args:
        db: session SQLAlchemy
        organisation_id: org-scoping strict (filtre Site → Portefeuille → EJ → Org)
        portefeuille_id: filtre optionnel sur 1 portefeuille spécifique

    Returns:
        dict avec :
        - intensity_kwh_m2_total: float | None (Σ kWh / Σ surface_m2)
        - intensity_kwh_m2_tertiaire: float | None (Σ kWh / Σ tertiaire_area_m2)
        - sites_count: int (total sites du périmètre)
        - sites_with_data_count: int (sites ayant ≥ kWh > 0 ET surface > 0)
        - sum_annual_kwh: float | None (kWh EF PCI)
        - sum_surface_m2: float | None
        - sum_tertiaire_area_m2: float | None
        - scope: dict (organisation_id, portefeuille_id pour traçabilité)
    """
    q = (
        db.query(Site)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == organisation_id)
        .filter(not_deleted(Site))
    )
    if portefeuille_id is not None:
        q = q.filter(Site.portefeuille_id == portefeuille_id)

    sites = q.all()
    sites_count = len(sites)

    sum_annual_kwh = sum((s.annual_kwh_total or 0) for s in sites if s.annual_kwh_total and s.annual_kwh_total > 0)
    sum_surface_m2 = sum((s.surface_m2 or 0) for s in sites if s.surface_m2 and s.surface_m2 > 0)
    sum_tertiaire_area_m2 = sum(
        (getattr(s, "tertiaire_area_m2", None) or 0)
        for s in sites
        if getattr(s, "tertiaire_area_m2", None) and getattr(s, "tertiaire_area_m2", 0) > 0
    )

    sites_with_data_count = sum(
        1 for s in sites if (s.annual_kwh_total and s.annual_kwh_total > 0) and (s.surface_m2 and s.surface_m2 > 0)
    )

    intensity_total = round(sum_annual_kwh / sum_surface_m2, 2) if sum_annual_kwh > 0 and sum_surface_m2 > 0 else None
    intensity_tertiaire = (
        round(sum_annual_kwh / sum_tertiaire_area_m2, 2) if sum_annual_kwh > 0 and sum_tertiaire_area_m2 > 0 else None
    )

    return {
        "intensity_kwh_m2_total": intensity_total,
        "intensity_kwh_m2_tertiaire": intensity_tertiaire,
        "sites_count": sites_count,
        "sites_with_data_count": sites_with_data_count,
        "sum_annual_kwh": sum_annual_kwh if sum_annual_kwh > 0 else None,
        "sum_surface_m2": sum_surface_m2 if sum_surface_m2 > 0 else None,
        "sum_tertiaire_area_m2": (sum_tertiaire_area_m2 if sum_tertiaire_area_m2 > 0 else None),
        # Sprint C-3 Phase 3.7d audit follow-up — PROMEOS-SEC-2026-042 (CWE-200) :
        # `organisation_id` numérique auto-incrémenté retiré de la réponse publique.
        # Le scope inclut uniquement `portefeuille_id` (déjà fourni par le client).
        # L'org est implicite via le token / DEMO_MODE — pas d'amplification IDOR.
        "scope": {
            "portefeuille_id": portefeuille_id,
        },
    }
