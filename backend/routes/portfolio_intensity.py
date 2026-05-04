"""
PROMEOS — Endpoint GET /api/portfolio/intensity (Sprint C-3 Phase 3.4).

Agrégat intensité énergétique portefeuille / organisation, calculé depuis
`Site.annual_kwh_total` (snapshot patrimoine) — distinct de `/api/energy/intensity`
qui calcule depuis Meter readings (réel mesuré).

Clôture la dette `D-Phase4-3-Portfolio-Intensity-Backend-001` (Sprint C-3) :
Patrimoine.jsx L825-830 KpiStripItem global "Consommation kWh/m² moy." pourra
désormais consommer cet endpoint (rolling Sprint C-3 Phase 3.5+ ou C-4 selon scope).

Org-scopé strict :
- Sans portefeuille_id : agrégation tous portefeuilles de l'organisation.
- Avec portefeuille_id : vérification ownership (404 si hors org).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from routes.patrimoine._helpers import _check_portfolio_belongs_to_org, _get_org_id
from services.portfolio_intensity_service import compute_portfolio_intensity


router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


@router.get("/intensity")
def get_portfolio_intensity_endpoint(
    request: Request,
    portefeuille_id: Optional[int] = Query(
        None,
        description="Filtre optionnel sur 1 portefeuille spécifique. Sans filtre = tous portefeuilles de l'org.",
    ),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
) -> dict:
    """Intensité énergétique agrégée du portefeuille / organisation.

    Calcul : `Σ(Site.annual_kwh_total) / Σ(Site.surface_m2)` org-scopé
    (ratio des sommes, NON moyenne arithmétique des ratios).

    Sans `portefeuille_id` → agrégation tous portefeuilles de l'organisation.
    Avec `portefeuille_id` → vérification ownership (404 si hors org).

    Source kWh : `Site.annual_kwh_total` en **énergie finale PCI** uniquement
    (cf. source-guard `test_annual_kwh_total_kwhef_pci_source_guards.py`).

    Cohabitation `/api/energy/intensity` (existant) :
    - `/api/energy/intensity` : calcul depuis Meter readings (réel mesuré).
    - `/api/portfolio/intensity` (ce endpoint) : depuis Site.annual_kwh_total
      (snapshot patrimoine, agrégat rapide pour Cockpit/Patrimoine KPIs).
    """
    org_id = _get_org_id(request, auth, db)

    # Sécurité : si portefeuille_id fourni, vérifier ownership avant calcul
    if portefeuille_id is not None:
        _check_portfolio_belongs_to_org(db, portefeuille_id, org_id)

    return compute_portfolio_intensity(db, org_id, portefeuille_id)
