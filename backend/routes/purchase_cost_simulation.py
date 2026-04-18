"""
PROMEOS — Purchase Cost Simulation Route (Sprint Achat post-ARENH MVP).

GET /api/purchase/cost-simulation/{site_id}?year=2026

Expose le simulateur de facture annuelle prévisionnelle post-ARENH décomposée
par composante réglementaire 2026+ :
    - fourniture (forward baseload × CDC annuel)
    - TURPE 7 (part fixe + variable)
    - VNU (dormant si prix < 78 EUR/MWh CRE, upside sinon)
    - mécanisme capacité RTE (enchères PL-4/PL-1 centralisées à partir de Nov 2026)
    - CBAM scope (non applicable à la conso élec directe — documenté)
    - taxes agrégées (accise + CTA + TVA)

Service délégué : `services.purchase.cost_simulator_2026.simulate_annual_cost_2026`.
Scope org : défense-in-depth via la chaîne Site → Portefeuille → EntiteJuridique
→ organisation_id (pattern hérité de `routes/pilotage._resolve_db_site`).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/purchase/cost-simulation", tags=["Achat Energie — Cost Simulator"])


# ───────────────────────── Pydantic schemas ─────────────────────────


class CostComposantes(BaseModel):
    """Décomposition des 6 composantes de la facture prévisionnelle post-ARENH."""

    fourniture_eur: float = Field(..., description="Fourniture énergie (forward baseload × CDC annuel)")
    turpe_eur: float = Field(..., description="TURPE 7 (part fixe + variable)")
    vnu_eur: float = Field(
        ...,
        description="Versement Nucléaire Universel — 0 si dormant (prix marché < 78 EUR/MWh CRE)",
    )
    capacite_eur: float = Field(..., description="Mécanisme capacité RTE centralisé (PL-4/PL-1 à partir du 01/11/2026)")
    cbam_scope: float = Field(..., description="Impact CBAM — 0 pour la conso élec directe (non applicable)")
    accise_cta_tva_eur: float = Field(..., description="Taxes agrégées (accise + CTA + TVA)")


class CostHypotheses(BaseModel):
    """Hypothèses MVP documentées (contrat stable côté frontend)."""

    prix_forward_y1_eur_mwh: float
    facteur_forme: float
    capacite_unitaire_eur_mwh: float
    capacite_source_ref: str
    vnu_statut: str = Field(..., description="'dormant' | 'actif'")
    vnu_seuil_active_eur_mwh: float
    vnu_source_ref: Optional[str] = None
    vnu_note: str
    vnu_risque_upside_eur_mwh: float
    archetype: str
    turpe_segment: str
    turpe_energie_eur_kwh: float
    turpe_gestion_eur_mois: float
    turpe_comptage_eur_an: float
    turpe_soutirage_eur_an: float
    p_souscrite_kva_estimee: float
    accise_code_resolu: str
    accise_eur_kwh: float
    cta_rate: float
    tva_rate: float
    baseline_2024_eur_mwh: float
    comparabilite_baseline: str
    annual_kwh_resolu: float
    cbam_note: str
    source_calibration: list[str]


class Baseline2024(BaseModel):
    """Estimation facture historique ARENH 2024 HT pour delta comparable."""

    fourniture_ht_eur: float
    prix_moyen_pondere_eur_mwh: float
    methode: str
    delta_fourniture_ht_pct: float


class CostSimulation2026Response(BaseModel):
    """Facture prévisionnelle annuelle post-ARENH — décomposition 6 composantes."""

    site_id: str = Field(..., description="Identifiant canonique du site")
    year: int = Field(..., ge=2026, le=2030)
    facture_totale_eur: float = Field(..., description="Somme des composantes arrondie")
    energie_annuelle_mwh: float = Field(..., description="Conso annuelle en MWh")
    composantes: CostComposantes
    hypotheses: CostHypotheses
    baseline_2024: Baseline2024
    delta_vs_2024_pct: float = Field(..., description="Variation % vs baseline 2024 HT énergie (comparable)")
    confiance: str = Field(..., description="'indicative' en MVP")
    source: str = Field(..., description="Citation courte sources réglementaires")


# ───────────────────────── Helper : scope org ─────────────────────────


def _resolve_site(db: Session, site_id: str, auth: Optional[AuthContext]) -> Any:
    """Résout un Site numérique via le helper pilotage `_scoped_site_query`.

    Les clés DEMO_SITES (non numériques) renvoient 404 explicite : le
    simulateur exige annual_kwh réel + archétype résolu.
    """
    if not site_id.isdigit():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Simulation cost 2026 non disponible pour '{site_id}' — cet endpoint "
                "exige un Site.id réel avec annual_kwh renseigné. Les clés DEMO_SITES "
                "ne sont pas supportées (pas de CDC historique suffisante)."
            ),
        )

    from models import Site
    from routes.pilotage import _scoped_site_query

    site_pk = int(site_id)
    site = _scoped_site_query(db, auth).filter(Site.id == site_pk).first()
    if site is None:
        raise HTTPException(
            status_code=404,
            detail=f"Site introuvable ou hors scope : id={site_pk}",
        )
    return site


# ───────────────────────── Endpoint ─────────────────────────


@router.get("/{site_id}", response_model=CostSimulation2026Response)
def get_cost_simulation_2026(
    site_id: str,
    year: int = Query(2026, ge=2026, le=2030, description="Année prévisionnelle (2026-2030)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
) -> CostSimulation2026Response:
    """
    Simule la facture annuelle prévisionnelle post-ARENH décomposée.

    Décompose en 6 composantes réglementaires 2026+ :
    **fourniture + TURPE 7 + VNU + capacité RTE + CBAM + taxes**.

    Retour JSON : `CostSimulation2026Response` avec trace des hypothèses MVP
    (prix forward Y+1, facteur de forme, VNU statut, sources). Confiance
    "indicative" — pas d'engagement commercial.

    **Scope** : Site.id numérique uniquement (pas de clé DEMO_SITES — le
    chiffrage dépend d'annual_kwh renseigné). 404 si introuvable ou hors
    scope org (anti-énumération).

    **Sources doctrine** :
      - Post-ARENH 01/01/2026 (Loi 2023-491 souveraineté énergétique,
        art. L. 336-1 Code énergie)
      - TURPE 7 CRE 2025-78 (01/08/2025, brochure Enedis p.13-14)
      - VNU Décret 2026-55 + CRE 2026-52 (tarif unitaire 2026 = 0 €/MWh ;
        seuils 78 / 110 €/MWh)
      - Capacité Décret 2025-1441 + Arrêté 18/03/2026 (mécanisme centralisé
        Y-4 / Y-1, démarrage 01/11/2026)
    """
    site = _resolve_site(db, site_id, auth)

    # Import tardif pour découpler l'import du module route du service
    # (évite crash au boot si le service a un ImportError amont).
    from services.purchase.cost_simulator_2026 import simulate_annual_cost_2026

    result = simulate_annual_cost_2026(site=site, db=db, year=year)
    return CostSimulation2026Response(**result)
