"""
PROMEOS - Routes Pilotage des usages.

Endpoints :
    - /flex-ready-signals/{site_id} : 5 donnees standardisees NF EN IEC 62746-4
      (conformite technique, cf. flex_ready.py).
    - /roi-flex-ready/{site_id}     : gain annuel estime EUR (business case CFO,
      cf. roi_flex_ready.py).
    - /radar-prix-negatifs          : fenetres probables prix negatifs J+7.

Reference : Barometre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026).
"""

from __future__ import annotations

import logging
import os
from typing import Any, List, Optional
from zoneinfo import ZoneInfo

_TZ_PARIS = ZoneInfo("Europe/Paris")

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth


def _is_demo_mode() -> bool:
    """Vrai si `PROMEOS_DEMO_MODE=true` — gate explicite pour fallback DEMO."""
    return os.environ.get("PROMEOS_DEMO_MODE", "false").lower() == "true"


from services.pilotage.flex_ready import (
    FlexReadySignalsResponse,
    PrixSource,
    build_flex_ready_signals,
)
from services.pilotage.portefeuille_scoring import compute_portefeuille_scoring
from services.pilotage.radar_prix_negatifs import predict_negative_windows
from services.pilotage.roi_flex_ready import compute_roi_flex_ready


router = APIRouter(prefix="/api/pilotage", tags=["Pilotage"])


# ---------------------------------------------------------------------------
# DEMO_SITES : fiches hardcodees pour la demo Flex Ready (R).
# Chaque fiche porte les 4 donnees statiques du standard (puissance max, prix
# tarif, puissance souscrite, vecteur energetique). Le 5e signal (empreinte
# carbone) vient de config/emission_factors.py. Le 1er signal (horloge) est
# genere au moment de l'appel.
# ---------------------------------------------------------------------------
DEMO_SITES: dict[str, dict[str, Any]] = {
    "retail-001": {
        "nom": "Hypermarche Montreuil",
        "puissance_max_instantanee_kw": 180.0,
        "prix_eur_kwh": 0.185,
        "puissance_souscrite_kva": 250,
        "energy_vector": "ELEC",
        "archetype_code": "COMMERCE_ALIMENTAIRE",
        "puissance_pilotable_kw": 220.0,
        "surface_m2": 2500.0,
    },
    "bureau-001": {
        "nom": "Bureau Haussmann",
        "puissance_max_instantanee_kw": 95.0,
        "prix_eur_kwh": 0.172,
        "puissance_souscrite_kva": 144,
        "energy_vector": "ELEC",
        "archetype_code": "BUREAU_STANDARD",
        "puissance_pilotable_kw": 120.0,
        "surface_m2": 1800.0,
    },
    "entrepot-001": {
        "nom": "Entrepot Rungis",
        "puissance_max_instantanee_kw": 320.0,
        "prix_eur_kwh": 0.158,
        "puissance_souscrite_kva": 400,
        "energy_vector": "ELEC",
        "archetype_code": "LOGISTIQUE_FRIGO",
        "puissance_pilotable_kw": 85.0,
        "surface_m2": 6000.0,
    },
}


# ---------------------------------------------------------------------------
# ROI Flex Ready (R) -- schemas de reponse (Piste 2 V1 innovation).
# ---------------------------------------------------------------------------
class RoiFlexReadyComposantes(BaseModel):
    """Les 3 composantes additives du gain annuel Flex Ready (R)."""

    evitement_pointe_eur: float = Field(..., description="Gain evitement pointe EUR/an")
    decalage_nebco_eur: float = Field(..., description="Valorisation decalage NEBCO EUR/an")
    cee_bacs_eur: float = Field(..., description="CEE BAT-TH-116 (GTB/BACS) EUR")


class RoiFlexReadyResponse(BaseModel):
    """Payload ROI Flex Ready (R) : gain annuel estime + hypotheses explicites."""

    site_id: str = Field(..., description="Identifiant canonique du site")
    archetype: str = Field(..., description="Archetype finalement utilise (fallback si inconnu)")
    gain_annuel_total_eur: float = Field(..., description="Gain annuel total estime (EUR)")
    composantes: RoiFlexReadyComposantes = Field(..., description="Detail des 3 composantes")
    hypotheses: dict = Field(
        ...,
        description=(
            "Parametres MVP utilises (explainability). Inclut la sous-cle "
            "'parametres_sources' : trace ParameterStore par parametre "
            "(code, value, source, source_ref, valid_from, unite, scope)."
        ),
    )
    confiance: str = Field(..., description="Niveau de confiance : 'indicative' en MVP")
    source: str = Field(..., description="Citation courte des sources de calibrage")


def _build_demo_site_ctx(site_id: str) -> dict[str, Any]:
    """
    Retourne la fiche DEMO_SITES pour `site_id`.
    Leve HTTP 404 si le site n'est pas dans la liste demo.
    """
    ctx = DEMO_SITES.get(site_id)
    if ctx is None:
        raise HTTPException(
            status_code=404,
            detail=f"Site demo inconnu : '{site_id}'. Sites disponibles : {sorted(DEMO_SITES.keys())}",
        )
    return ctx


def _scoped_site_query(db: Session, auth: Optional[AuthContext]):
    """
    Query de base `Site actif` + defense-in-depth org_id si auth present.

    Hors auth (DEMO_MODE), aucune restriction -- le filtre d'actif suffit.
    Retourne un Query[Site] que les callers affinent avec `.filter(Site.id == ...)`
    ou `.filter(Site.id.in_(...))`.

    Le 404 retourne sur lookup vide evite de distinguer "site inexistant" et
    "site hors scope" -- choix delibere anti-enumeration (vs monitoring.py 403).
    """
    from models import EntiteJuridique, Portefeuille, Site

    query = db.query(Site).filter(Site.actif == True)  # noqa: E712
    if auth is not None and getattr(auth, "org_id", None):
        query = (
            query.join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
            .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
            .filter(EntiteJuridique.organisation_id == auth.org_id)
        )
    return query


def _resolve_db_site(db: Session, site_id: str, auth: Optional[AuthContext]):
    """
    Cœur commun des `_load_*_ctx` : numerique -> Site.id scope, alpha -> None.

    Retourne `(site, None)` si site reel trouve, `(None, demo_ctx)` si cle DEMO_SITES,
    leve HTTP 404 si Site.id numerique inexistant / hors scope.

    Permet aux callers d'enrichir le contexte selon leurs besoins (roi, flex-ready...).
    """
    if not site_id.isdigit():
        return None, _build_demo_site_ctx(site_id)

    from models import Site

    site_pk = int(site_id)
    site = _scoped_site_query(db, auth).filter(Site.id == site_pk).first()
    if site is None:
        raise HTTPException(
            status_code=404,
            detail=f"Site introuvable ou hors scope : id={site_pk}",
        )
    return site, None


def _load_site_ctx(
    db: Session,
    site_id: str,
    auth: Optional[AuthContext],
) -> dict[str, Any]:
    """
    Resout `site_id` en fiche pour `compute_roi_flex_ready` :
        - Si `site_id` est numerique -> lookup Site.id en DB (scope via auth.org_id).
        - Sinon -> fallback DEMO_SITES (404 si cle inconnue).

    Un site sans `archetype_code` renseigne tombe sur le fallback
    BUREAU_STANDARD cote compute_roi_flex_ready (explainability preservee).
    """
    site, demo_ctx = _resolve_db_site(db, site_id, auth)
    if demo_ctx is not None:
        return demo_ctx

    return {
        "nom": site.nom,
        "puissance_max_instantanee_kw": float(site.puissance_pilotable_kw or 0.0),
        "surface_m2": float(site.surface_m2 or 0.0),
        "archetype_code": site.archetype_code,
    }


# Tarif de base fallback : source unique dans `services.pilotage.constants`
# (evite le drift avec `flex_ready._TARIF_BASE_FALLBACK_EUR_KWH`).
from services.pilotage.constants import TARIF_BASE_FALLBACK_EUR_KWH as _TARIF_BASE_FALLBACK_EUR_KWH


def _load_flex_ready_ctx(
    db: Session,
    site_id: str,
    auth: Optional[AuthContext],
) -> dict[str, Any]:
    """
    Resout `site_id` en fiche pour `build_flex_ready_signals`.

    Pattern Option C (cf. `_load_site_ctx` pour roi-flex-ready) :
        - `site_id` numerique  -> lookup Site.id en DB (scope via auth.org_id)
          + recuperation d'un DeliveryPoint actif (puissance_souscrite_kva)
          + dernier EnergyContract elec actif (prix_eur_kwh).
        - `site_id` alphanumerique -> fallback DEMO_SITES (4 signaux hardcodes).

    Fallbacks gracieux pour Site reel :
        - Pas de contrat elec rattache      -> prix = _TARIF_BASE_FALLBACK_EUR_KWH,
                                                trace `prix_source="site_sans_contrat_fallback"`.
        - Pas de DeliveryPoint / puissance  -> 0 kVA + warning logue
                                                (pas de crash, trace operateur).
        - Pas de puissance_pilotable_kw     -> 0 kW (cohesion avec roi-flex-ready).
    """
    site, demo_ctx = _resolve_db_site(db, site_id, auth)
    if demo_ctx is not None:
        return demo_ctx

    from models.patrimoine import DeliveryPoint

    # --- puissance_souscrite_kva : premier DeliveryPoint elec avec la valeur ---
    dp = (
        db.query(DeliveryPoint)
        .filter(
            DeliveryPoint.site_id == site.id,
            DeliveryPoint.puissance_souscrite_kva.isnot(None),
        )
        .order_by(DeliveryPoint.id.asc())
        .first()
    )
    if dp is not None and dp.puissance_souscrite_kva is not None:
        puissance_souscrite_kva = int(dp.puissance_souscrite_kva)
    else:
        puissance_souscrite_kva = 0
        logger.warning(
            "flex_ready: Site.id=%s sans DeliveryPoint.puissance_souscrite_kva -> 0 kVA sentinel (conformite degradee)",
            site.id,
        )

    # --- prix_eur_kwh : EnergyContract elec ACTIF (non resilie) le plus recent ---
    # Filtre end_date : None (ouvert) OU dans le futur. Evite qu'un contrat
    # resilie recemment batte un contrat actif plus ancien sur l'ordre start_date.
    try:
        from sqlalchemy import or_
        from datetime import datetime as _dt

        from models.billing_models import EnergyContract
        from models.enums import BillingEnergyType

        today_paris = _dt.now(_TZ_PARIS).date()
        contract = (
            db.query(EnergyContract)
            .filter(
                EnergyContract.site_id == site.id,
                EnergyContract.energy_type == BillingEnergyType.ELEC,
                or_(EnergyContract.end_date.is_(None), EnergyContract.end_date >= today_paris),
            )
            .order_by(EnergyContract.start_date.desc().nullslast(), EnergyContract.id.desc())
            .first()
        )
    except ImportError:
        contract = None

    prix_eur_kwh: float
    prix_source: str
    if contract is not None:
        # Priorite : price_hp_eur_kwh > price_base_eur_kwh > price_ref_eur_per_kwh
        candidate = (
            getattr(contract, "price_hp_eur_kwh", None)
            or getattr(contract, "price_base_eur_kwh", None)
            or getattr(contract, "price_ref_eur_per_kwh", None)
        )
        if candidate is not None and float(candidate) > 0:
            prix_eur_kwh = float(candidate)
            prix_source = PrixSource.CONTRAT_FOURNISSEUR.value
        else:
            prix_eur_kwh = _TARIF_BASE_FALLBACK_EUR_KWH
            prix_source = PrixSource.SITE_SANS_CONTRAT_FALLBACK.value
    else:
        prix_eur_kwh = _TARIF_BASE_FALLBACK_EUR_KWH
        prix_source = PrixSource.SITE_SANS_CONTRAT_FALLBACK.value

    return {
        "nom": site.nom,
        "puissance_max_instantanee_kw": float(site.puissance_pilotable_kw or 0.0),
        "prix_eur_kwh": prix_eur_kwh,
        "prix_source": prix_source,
        "puissance_souscrite_kva": puissance_souscrite_kva,
        "energy_vector": "ELEC",
        "surface_m2": float(site.surface_m2 or 0.0),
        "archetype_code": site.archetype_code,
    }


# ---------------------------------------------------------------------------
# Radar prix negatifs J+7 -- schemas de reponse.
# ---------------------------------------------------------------------------
class FenetrePrediteModel(BaseModel):
    """Fenetre favorable probable predite (cote client : wording doctrine)."""

    datetime_debut: str = Field(..., description="ISO 8601 Europe/Paris aware")
    datetime_fin: str = Field(..., description="ISO 8601 Europe/Paris aware")
    probabilite: float = Field(..., ge=0.0, le=1.0, description="Probabilite [0,1]")
    prix_estime_min_eur_mwh: float = Field(..., description="Mediane des prix negatifs observes sur jours semblables")
    usages_recommandes: List[str] = Field(
        ..., description="Usages flexibles conseilles (ecs, ve_recharge, pre_charge_froid)"
    )
    base_historique_jours: int = Field(
        ..., ge=0, description="Nb de jours historiques semblables ayant servi a la prediction"
    )


class RadarPrixNegatifsResponse(BaseModel):
    """Reponse endpoint /radar-prix-negatifs (wording cote client = 'favorable probable')."""

    fenetres_predites: List[FenetrePrediteModel]
    horizon_jours: int = Field(..., ge=1, le=14)
    source: str = Field("historique_entsoe_90j", description="Source des donnees d'entree")
    confiance: str = Field("indicative", description="Niveau de confiance du signal")


@router.get("/radar-prix-negatifs", response_model=RadarPrixNegatifsResponse)
def radar_prix_negatifs(
    horizon_days: int = Query(7, ge=1, le=14, description="Horizon de prediction (1..14 jours)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
) -> RadarPrixNegatifsResponse:
    """
    Radar prix negatifs J+7 (Piste 1 V1 innovation).

    Predit les fenetres probables de prix spot negatifs pour les jours a venir,
    a partir de l'historique MktPrice day-ahead FR (90 derniers jours).
    Approche MVP heuristique -- pas de ML :
        1. Analyse creneaux 10h-17h des 90 derniers jours.
        2. Pour chaque jour cible J+1..J+horizon, on compare aux jours de semaine
           semblables du meme mois.
        3. Si > 30 % des creneaux semblables ont ete negatifs => fenetre predite.

    Fallback gracieux :
        - < 30 jours d'historique => liste vide.
        - Aucune recurrence detectee => liste vide.

    Wording doctrine : cote front, ces fenetres sont presentees comme
    "Fenetres favorables probables" (pas "prix negatifs").
    """
    fenetres = predict_negative_windows(horizon_days=horizon_days, db=db)
    return RadarPrixNegatifsResponse(
        fenetres_predites=fenetres,
        horizon_jours=horizon_days,
        source="historique_entsoe_90j",
        confiance="indicative",
    )


# ---------------------------------------------------------------------------
# Scoring portefeuille multi-sites -- schemas de reponse (Piste 3 V1)
# ---------------------------------------------------------------------------
class PortefeuilleSiteRanked(BaseModel):
    """Ligne de classement Top-N d'un site dans le portefeuille."""

    site_id: str = Field(..., description="Identifiant canonique du site")
    archetype: Optional[str] = Field(None, description="Code archetype ou None si inconnu")
    score: float = Field(..., ge=0.0, le=100.0, description="Score potentiel pilotable 0-100")
    gain_annuel_eur: float = Field(..., ge=0.0, description="Gain annuel estime (EUR)")
    rang: int = Field(..., ge=1, description="Rang dans le classement (1 = meilleur)")


class PortefeuilleHeatmapEntry(BaseModel):
    """Agregat par archetype : nb_sites, gain total, score moyen."""

    nb_sites: int = Field(..., ge=0)
    gain_total_eur: float = Field(..., ge=0.0)
    score_moyen: float = Field(..., ge=0.0, le=100.0)


class PortefeuilleScoringResponse(BaseModel):
    """Reponse endpoint /portefeuille-scoring (Piste 3 V1)."""

    nb_sites_total: int = Field(..., ge=0)
    gain_annuel_portefeuille_eur: float = Field(..., ge=0.0)
    top_10: List[PortefeuilleSiteRanked]
    heatmap_archetype: dict[str, PortefeuilleHeatmapEntry]
    source: str = Field(..., description="Source du calibrage")


def _demo_sites_as_portfolio() -> list[dict[str, Any]]:
    """Transforme DEMO_SITES en liste prete pour compute_portefeuille_scoring."""
    return [
        {
            "site_id": site_id,
            "archetype_code": ctx.get("archetype_code"),
            "puissance_pilotable_kw": ctx.get("puissance_pilotable_kw", 0.0),
        }
        for site_id, ctx in DEMO_SITES.items()
    ]


def _org_sites_as_portfolio(db: Session, auth: AuthContext) -> list[dict[str, Any]]:
    """
    Liste les sites actifs scopes par AuthContext.site_ids + org pour le scoring.

    Defense-in-depth via `_scoped_site_query` (join Portefeuille -> EntiteJuridique).
    Lit `archetype_code` + `puissance_pilotable_kw` directement depuis Site.
    Sites non seedes -> None/0, scoring retombe sur fallback 50 + gain 0.
    """
    from models import Site

    site_ids = getattr(auth, "site_ids", None) or []
    if not site_ids:
        return []
    rows = _scoped_site_query(db, auth).filter(Site.id.in_(site_ids)).all()
    return [
        {
            "site_id": str(site.id),
            "archetype_code": site.archetype_code,
            "puissance_pilotable_kw": float(site.puissance_pilotable_kw or 0.0),
        }
        for site in rows
    ]


@router.get("/portefeuille-scoring", response_model=PortefeuilleScoringResponse)
def portefeuille_scoring(
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
) -> PortefeuilleScoringResponse:
    """
    Classement par potentiel de pilotage d'un portefeuille multi-sites.

    Retourne :
        - nb_sites_total                : cardinal du portefeuille
        - gain_annuel_portefeuille_eur  : somme des gains annuels estimes
        - top_10                        : Top-10 trie par score decroissant
        - heatmap_archetype             : agregat par archetype (nb, gain, score moyen)

    En prod (auth.org_id present), iterer sur les sites actifs de l'organisation
    courante -- avec fallback sentinel tant que les champs archetype /
    puissance_pilotable_kw ne sont pas encore portes par le modele Site.
    Si l'org ne porte aucun site (pilote pre-seed), le payload est vide --
    on ne pollue pas l'ecran d'un utilisateur authentifie avec des donnees DEMO.

    En DEMO_MODE uniquement (PROMEOS_DEMO_MODE=true ou auth absent), retombe sur
    les 3 sites de DEMO_SITES pour garantir un payload non-vide exploitable
    par le front de demonstration.

    Source : Barometre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026).
    """
    if auth is not None and getattr(auth, "org_id", None):
        sites = _org_sites_as_portfolio(db, auth)
        # Org authentifiee sans site utile : retourner payload vide plutot
        # que polluer l'ecran avec des donnees DEMO. Fallback DEMO reserve
        # au mode demonstration explicite.
        if not sites and _is_demo_mode():
            sites = _demo_sites_as_portfolio()
    else:
        # Pas d'auth : mode DEMO (front public ou dev local)
        sites = _demo_sites_as_portfolio()

    result = compute_portefeuille_scoring(sites)
    return PortefeuilleScoringResponse(**result)


@router.get("/flex-ready-signals/{site_id}", response_model=FlexReadySignalsResponse)
def flex_ready_signals(
    site_id: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
) -> FlexReadySignalsResponse:
    """
    Expose les 5 signaux standardises Flex Ready (R) conformes NF EN IEC 62746-4.

    Les 5 donnees echangees entre gestion technique du bâtiment et acteurs
    de pilotage (Baromètre Flex 2026) :
        1. Horloge (pas 15 min min, bidirectionnel)
        2. Puissance max instantanée (kW)
        3. Prix unitaire (EUR/kWh) — signal temps réel ou tarif contractuel
        4. Puissance souscrite (kVA)
        5. Empreinte carbone (kgCO2e/kWh) — source ADEME V23.6

    Accepte deux formes de `site_id` (pattern Option C, cf. /roi-flex-ready) :
        - Numerique (ex. `42`) : Site.id reel, lookup DB avec scope org.
          Puissance souscrite depuis DeliveryPoint, prix depuis EnergyContract
          actif (fallback tarif de base si contrat absent, avec trace
          `prix_source="site_sans_contrat_fallback"`).
        - Alphanumerique (ex. `retail-001`) : cle DEMO_SITES (catalogue demo).

    404 si le site est introuvable ou hors scope.
    Auth optionnelle (DEMO_MODE tolere).
    """
    ctx = _load_flex_ready_ctx(db=db, site_id=site_id, auth=auth)
    return build_flex_ready_signals(site_id=site_id, demo_site=ctx, db=db)


@router.get("/roi-flex-ready/{site_id}", response_model=RoiFlexReadyResponse)
def roi_flex_ready(
    site_id: str,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
) -> RoiFlexReadyResponse:
    """
    Expose le business case chiffre Flex Ready (R) : gain annuel estime (EUR).

    Complete la conformite technique NF EN IEC 62746-4 (voir
    /flex-ready-signals) avec la seule question que les CFOs lisent :
    "Combien ce site gagne-t-il par an a etre Flex Ready (R) + pilote ?"

    Trois composantes additives :
        1. Gain evitement pointe        -- kW pilotable x h pointe evitees x spread
        2. Valorisation decalage NEBCO  -- kW decalable x 200 h/an x 60 EUR/MWh
        3. CEE BAT-TH-116 (GTB/BACS)    -- surface m2 x 3,5 EUR/m2

    Wording doctrine : "gain annuel estime" cote client. Confiance "indicative"
    en MVP. Hypotheses toujours exposees dans la payload (explainability).

    Sources :
        - Barometre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026)
        - Fiche CEE BAT-TH-116 (systeme GTB / BACS)

    Accepte deux formes de `site_id` :
        - Numerique (ex. `42`) : Site.id reel, lookup DB avec scope org via
          la chaine Portefeuille -> EntiteJuridique -> Organisation.
        - Alphanumerique (ex. `retail-001`) : cle DEMO_SITES (catalogue demo).

    404 si le site est introuvable ou hors scope.
    Archetype non renseigne cote prod -> fallback BUREAU_STANDARD (cf.
    compute_roi_flex_ready), avec hypotheses exposees dans la payload.

    Auth optionnelle (DEMO_MODE tolere).
    """
    ctx = _load_site_ctx(db=db, site_id=site_id, auth=auth)
    return compute_roi_flex_ready(
        site_id=site_id,
        demo_site=ctx,
        archetype_code=ctx.get("archetype_code"),
    )


# ---------------------------------------------------------------------------
# Simulation NEBCO -- schemas de reponse (Vague 2 piste 4).
# ---------------------------------------------------------------------------
class NebcoSimulationComposantes(BaseModel):
    """Detail du gain simule : spread brut, compensation fournisseur, net encaisse."""

    gain_spread_eur: float = Field(..., description="Gain brut depuis spread prix marche")
    compensation_fournisseur_eur: float = Field(
        ..., description="Compensation versee au fournisseur historique (~30% MVP)"
    )
    net_eur: float = Field(..., description="Gain net reellement encaisse = spread - compensation")


class NebcoSimulationResponse(BaseModel):
    """Resultat de rejeu NEBCO sur CDC historique du site (Vague 2 piste 4)."""

    site_id: str
    periode_debut: str = Field(..., description="ISO date debut")
    periode_fin: str = Field(..., description="ISO date fin")
    gain_simule_eur: float = Field(..., description="Gain net simule EUR (arrondi)")
    kwh_decales_total: float = Field(..., description="Volume kWh theoriquement decalable sur la periode")
    n_fenetres_favorables: int = Field(..., ge=0)
    spread_moyen_eur_mwh: float = Field(..., description="Ecart moyen prix SENSIBLE vs FAVORABLE observe")
    composantes: NebcoSimulationComposantes
    hypotheses: dict = Field(
        ...,
        description=("Parametres MVP utilises (taux decalable archetype, compensation ratio, sources)"),
    )
    confiance: str = Field(..., description="'indicative' en MVP")
    source: str


@router.get("/nebco-simulation/{site_id}", response_model=NebcoSimulationResponse)
def nebco_simulation(
    site_id: str,
    period_days: int = Query(30, ge=7, le=90, description="Periode de rejeu (jours, 7-90)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
) -> NebcoSimulationResponse:
    """
    Rejoue les N derniers jours de CDC du site et estime le gain NEBCO
    qu'il aurait obtenu en decalant ses usages flexibles vers les fenetres
    favorables detectees.

    Differenciant demo : "voici les X EUR que vous auriez gagnes le mois
    dernier" -- preuve chiffree sans engagement agregateur.

    Accepte `site_id` numerique (Site.id scope org via `_scoped_site_query`)
    OU cle DEMO_SITES. Les cles DEMO n'ont pas de CDC historique seedee
    exploitable pour une simulation credible -> 404 explicite (wording doctrine :
    pas de donnees = pas de simulation chiffree).

    404 si le site est introuvable, hors scope, ou cle DEMO_SITES sans CDC.
    422 si `period_days` hors [7, 90] (Pydantic Query validation).
    Auth optionnelle (DEMO_MODE tolere).
    """
    site, demo_ctx = _resolve_db_site(db, site_id, auth)

    if demo_ctx is not None:
        # Cle DEMO_SITES : pas de CDC historique seedee -> 404 explicite.
        # Wording doctrine : pas de donnees = pas de simulation credible.
        raise HTTPException(
            status_code=404,
            detail=(
                f"Simulation NEBCO DEMO non disponible pour '{site_id}' "
                "(pas de CDC historique seedee) -- utiliser un Site reel seede."
            ),
        )

    # Site reel : appel service (interface stable, cf. agent A).
    from services.pilotage.nebco_simulation import simulate_nebco_gain

    result = simulate_nebco_gain(site=site, db=db, period_days=period_days)
    return NebcoSimulationResponse(**result)
