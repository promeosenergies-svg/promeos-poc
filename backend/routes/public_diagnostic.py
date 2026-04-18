"""PROMEOS — Diagnostic public (P2 wedge Sirene).

Endpoint **sans authentification**, conçu pour être intégré sur :
- promeos.io (landing acquisition)
- partenaires (CCI, Medef, agences immo pro, comptables)
- emails / slides commerciaux

Flow :
  1. Input : SIREN (9 chiffres)
  2. Backend : lookup local → si absent, hydrate via API gouv (live)
  3. Compute : lead_score (segment/priorité — sans MRR pour éviter info leak)
  4. Output : carte pédagogique "coût d'inaction compliance" + pré-qualification

Différenciateur : premier diagnostic freemium B2B énergie France (intégration
Sirene + scoring + CBAM + compliance) en 1 appel, sans compte utilisateur.

**Opt-in production** : le router n'est enregistré dans `main.py` que si
`PROMEOS_ENABLE_PUBLIC_DIAGNOSTIC=true` (pas par défaut, pour éviter
exposition accidentelle avant rate limiting en place). Ajouter `slowapi`
throttle `/api/public/*` (10/min/IP) avant tout déploiement public réel.

Sources :
- `services/lead_score.py` — compute lead score (V116)
- `services/sirene_hydrate.py` — hydratation live API gouv (V117)
- `services/billing_engine/bricks/cbam.py` — exposition CBAM (P3)
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from database import get_db
from models.sirene import SireneEtablissement, SireneUniteLegale
from services.lead_score import compute_lead_score_from_loaded

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public", tags=["Public Diagnostic — Wedge Sirene"])


class LeadScoreSummary(BaseModel):
    """Résumé lead score pour carte publique (sans MRR pour éviter info leak
    vers les concurrents via énumération SIREN).
    """

    model_config = ConfigDict(extra="forbid")

    segment: str = Field(..., description="TPE / PME / ETI / GE")
    priority: str = Field(..., description="A (chaud) / B (tiède) / C (froid)")
    naf_value_tier: str = Field(..., description="high / medium / low")
    drivers: list[str] = Field(default_factory=list)


class CompliancePreview(BaseModel):
    """Estimation des obligations compliance — sensibilisation CFO."""

    model_config = ConfigDict(extra="forbid")

    decret_tertiaire_applicable: bool = Field(
        ..., description="Décret tertiaire potentiellement applicable (surface ≥ 1 000 m²)"
    )
    bacs_applicable: bool = Field(..., description="Décret BACS potentiellement applicable (puissance froide ≥ 70 kW)")
    cbam_potentiel: bool = Field(
        ..., description="Exposition CBAM potentielle (secteur NAF à forte importation hors UE)"
    )
    estimated_annual_exposure_eur: float = Field(
        ...,
        description=(
            "Coût d'inaction annuel estimé (ordre de grandeur pédagogique, MVP "
            "indicatif — pas un engagement commercial)."
        ),
    )
    note: str


class PublicDiagnosticResponse(BaseModel):
    """Carte de diagnostic public — consommable par widget embeddable."""

    model_config = ConfigDict(extra="forbid")

    siren: str
    denomination: str
    categorie_insee: Optional[str] = None
    naf_code: Optional[str] = None
    naf_label: Optional[str] = None
    n_etablissements_actifs: int
    lead_score: LeadScoreSummary
    compliance_preview: CompliancePreview
    source: str = Field(..., description="Citation courte des sources")


# ─────────────────────────────────────────────────────────────────────
# Logique métier : compliance preview heuristique
# ─────────────────────────────────────────────────────────────────────


# NAF codes à forte exposition CBAM (imports hors UE de biens couverts).
# Heuristique conservatrice — si le NAF correspond, on flag potentiel.
# Source : Règlement UE 2023/956 scopes × correspondance NAF FR.
CBAM_EXPOSED_NAF_PREFIXES = frozenset(
    [
        "24.",  # Métallurgie (acier, aluminium)
        "23.",  # Autres produits minéraux non métalliques (ciment)
        "20.15",  # Fabrication de produits azotés et engrais
        "20.1",  # Industrie chimique de base (hydrogène)
    ]
)

# Ordres de grandeur "coût inaction" par segment (EUR/an, MVP indicatif).
# Calibré sur les amendes potentielles décret tertiaire + BACS + CBAM.
INACTION_COST_BY_SEGMENT_EUR = {
    "TPE": 2_500,
    "PME": 12_000,
    "ETI": 45_000,
    "GE": 150_000,
}


def _preview_compliance(ul, segment: str) -> CompliancePreview:
    """Heuristique compliance : pas de DB, juste des règles métier."""
    naf = (ul.activite_principale or "").strip()
    cbam_potentiel = any(naf.startswith(p) for p in CBAM_EXPOSED_NAF_PREFIXES)

    # Décret tertiaire : très probable pour PME/ETI/GE multi-sites.
    # Sans surface locale on ne peut pas être précis — hypothèse conservatrice.
    decret_tertiaire_applicable = segment in ("PME", "ETI", "GE")

    # BACS : probable pour tertiaire avec froid (commerce, bureaux > seuil).
    # Même logique conservatrice.
    bacs_applicable = segment in ("PME", "ETI", "GE")

    exposure = float(INACTION_COST_BY_SEGMENT_EUR.get(segment, 2_500))
    if cbam_potentiel:
        # Secteurs CBAM = exposition +50% (import hors UE = coût additionnel).
        exposure *= 1.5

    note = (
        "Estimation ordre de grandeur MVP — sensibilisation CFO uniquement. "
        "Un diagnostic précis nécessite surface, puissance souscrite et "
        "volumes d'import réels (cockpit PROMEOS complet)."
    )

    return CompliancePreview(
        decret_tertiaire_applicable=decret_tertiaire_applicable,
        bacs_applicable=bacs_applicable,
        cbam_potentiel=cbam_potentiel,
        estimated_annual_exposure_eur=round(exposure, 2),
        note=note,
    )


# ─────────────────────────────────────────────────────────────────────
# Endpoint public
# ─────────────────────────────────────────────────────────────────────


@router.get("/diagnostic/{siren}", response_model=PublicDiagnosticResponse)
def get_public_diagnostic(
    siren: str,
    db: Session = Depends(get_db),
) -> PublicDiagnosticResponse:
    """Diagnostic public freemium (sans auth) pour widget embeddable.

    Retourne une carte pédagogique à partir d'un SIREN :
    pré-qualification lead (segment/MRR/priorité), preview compliance
    (décret tertiaire, BACS, CBAM potentiel), coût d'inaction estimé.

    Wedge acquisition : « entrez un SIREN, voyez votre coût d'inaction
    compliance en 30 s ». Partenaires cibles : CCI, Medef, agences immo
    pro, experts-comptables, directions achats / énergie ETI.

    **Scope** : lecture locale du référentiel Sirene. Si le SIREN n'est
    pas hydraté, l'endpoint hydrate live via API gouv (transparent).
    """
    siren = (siren or "").strip()
    if not siren.isdigit() or len(siren) != 9:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_SIREN",
                "message": "Le SIREN doit être composé de 9 chiffres.",
            },
        )

    # Lookup local → si absent, tentative hydratation live API gouv avec
    # rollback défensif si hydrate_siren_from_api insère partiellement puis
    # échoue (évite session pollution entre requêtes).
    ul = db.query(SireneUniteLegale).filter(SireneUniteLegale.siren == siren).first()
    if ul is None:
        try:
            from services.sirene_hydrate import hydrate_siren_from_api

            hydrate_siren_from_api(db, siren)
            db.commit()
            ul = db.query(SireneUniteLegale).filter(SireneUniteLegale.siren == siren).first()
        except (httpx.HTTPError, IOError, ValueError, SQLAlchemyError) as exc:
            db.rollback()
            logger.warning("public_diagnostic: hydrate failed for %s: %s", siren, exc)

    if ul is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SIREN_NOT_FOUND",
                "message": (
                    f"SIREN {siren} introuvable — vérifiez la saisie ou essayez à nouveau dans quelques minutes."
                ),
            },
        )

    n_etabs = (
        db.query(SireneEtablissement)
        .filter(
            SireneEtablissement.siren == siren,
            SireneEtablissement.etat_administratif == "A",
        )
        .count()
    )

    score_raw = compute_lead_score_from_loaded(ul, n_etabs)
    lead_score = LeadScoreSummary(
        segment=str(score_raw["segment"]),
        priority=str(score_raw["priority"]),
        naf_value_tier=str(score_raw["naf_value_tier"]),
        drivers=score_raw.get("drivers", []),
    )
    compliance_preview = _preview_compliance(ul, lead_score.segment)

    return PublicDiagnosticResponse(
        siren=siren,
        denomination=ul.denomination or ul.denomination_usuelle_1 or siren,
        categorie_insee=ul.categorie_entreprise,
        naf_code=ul.activite_principale,
        naf_label=getattr(ul, "activite_principale_libelle", None),
        n_etablissements_actifs=n_etabs,
        lead_score=lead_score,
        compliance_preview=compliance_preview,
        source=(
            "Sirene INSEE (data.gouv.fr) + lead scoring PROMEOS + décrets "
            "tertiaire/BACS + Règlement UE 2023/956 CBAM — MVP indicatif."
        ),
    )
