"""
PROMEOS — Routes API Usage V1.2
Endpoints pour la brique Usages Energetiques.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id, resolve_site_ids
from services.usage_service import (
    compute_usage_readiness,
    get_metering_plan,
    get_top_ues,
    get_usage_cost_breakdown,
    get_usages_dashboard,
    compute_baselines,
    get_usage_compliance,
    get_usage_billing_links,
    get_usage_timeline,
    get_portfolio_usage_comparison,
    get_meter_readings_preview,
    get_scoped_usages_dashboard,
    get_scoped_usage_timeline,
)
from models import Usage, UsageBaseline, USAGE_LABELS_FR, USAGE_FAMILY_MAP, TypeUsage, UsageFamily, DataSourceType
from schemas.usages_schemas import (
    ArchetypesResponse,
    UsageItemResponse,
    UsageTaxonomyResponse,
)

router = APIRouter(prefix="/api/usages", tags=["usages"])


def _check_site_org(db: Session, site_id: int, org_id: int):
    """Verify site belongs to org. Raises 404/403."""
    from models import Site, Portefeuille, EntiteJuridique

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(404, "Site non trouvé")
    if not site.portefeuille_id:
        raise HTTPException(403, "Site hors périmètre")
    pf = db.get(Portefeuille, site.portefeuille_id)
    if not pf:
        raise HTTPException(403, "Site hors périmètre")
    ej = db.get(EntiteJuridique, pf.entite_juridique_id)
    if not ej or ej.organisation_id != org_id:
        raise HTTPException(403, "Site hors périmètre")
    return site


# ── Dashboard scoped (multi-niveaux) ─────────────────────────────────────


@router.get("/scoped-dashboard")
def api_scoped_usages_dashboard(
    request: Request,
    entity_id: Optional[int] = Query(None),
    portefeuille_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    archetype_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Dashboard usages adaptatif : org → entité → portefeuille → site, filtrable par archétype."""
    org_id = resolve_org_id(request, auth, db)
    return get_scoped_usages_dashboard(
        db,
        org_id,
        entity_id=entity_id,
        portefeuille_id=portefeuille_id,
        site_id=site_id,
        archetype_code=archetype_code,
    )


@router.get("/scoped-timeline")
def api_scoped_usage_timeline(
    request: Request,
    entity_id: Optional[int] = Query(None),
    portefeuille_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    archetype_code: Optional[str] = Query(None),
    months: int = Query(12, ge=3, le=36),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Timeline usages agrégée par scope, filtrable par archétype."""
    org_id = resolve_org_id(request, auth, db)
    return get_scoped_usage_timeline(
        db,
        org_id,
        entity_id=entity_id,
        portefeuille_id=portefeuille_id,
        site_id=site_id,
        archetype_code=archetype_code,
        months=months,
    )


@router.get("/archetypes-in-scope", response_model=ArchetypesResponse)
def api_archetypes_in_scope(
    request: Request,
    entity_id: Optional[int] = Query(None),
    portefeuille_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Distribution des archétypes (TypeSite) dans le scope courant, pour les chips filtre."""
    from models.site import Site as SiteModel
    from services.scope_utils import resolve_site_ids as _resolve

    org_id = resolve_org_id(request, auth, db)
    site_ids = _resolve(db, org_id, entity_id=entity_id, portefeuille_id=portefeuille_id, site_id=site_id)
    if not site_ids:
        return {"archetypes": []}

    sites = db.query(SiteModel.type).filter(SiteModel.id.in_(site_ids)).all()
    counts = {}
    for (t,) in sites:
        label = t.value if hasattr(t, "value") else str(t)
        counts[label] = counts.get(label, 0) + 1

    archetypes = sorted(
        [{"code": k, "label": k.replace("_", " ").title(), "count": v} for k, v in counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )
    return {"archetypes": archetypes}


# ── Flex NEBCO + BACS↔Flex ────────────────────────────────────────────────


@router.get("/flex-potential/{site_id}")
def api_flex_potential(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Scoring flex NEBCO + lien BACS↔Flex pour un site."""
    from services.flex_nebco_service import compute_flex_nebco

    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return compute_flex_nebco(db, site_id)


@router.get("/flex-portfolio")
def api_flex_portfolio(
    request: Request,
    entity_id: Optional[int] = Query(None),
    portefeuille_id: Optional[int] = Query(None),
    archetype_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Agrège le potentiel flex de tous les sites du périmètre, filtrable par archétype."""
    from services.flex_nebco_service import compute_flex_portfolio

    org_id = resolve_org_id(request, auth, db)
    site_ids = resolve_site_ids(
        db, org_id, entity_id=entity_id, portefeuille_id=portefeuille_id, archetype_code=archetype_code
    )
    return compute_flex_portfolio(db, site_ids)


# ── Coût par période tarifaire × usage ───────────────────────────────────


@router.get("/cost-by-period/{site_id}")
def api_cost_by_period(
    site_id: int,
    request: Request,
    months: int = Query(12, ge=1, le=36),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Ventilation du coût par usage × période tarifaire TURPE 7 (HPH/HCH/HPB/HCB)."""
    from services.cost_by_period_service import get_cost_by_period

    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return get_cost_by_period(db, site_id, months)


# ── Dashboard agrege (legacy mono-site) ──────────────────────────────────


@router.get("/dashboard/{site_id}")
def api_usages_dashboard(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Endpoint principal de la page /usages : readiness + plan + UES + derives + cout."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return get_usages_dashboard(db, site_id)


# ── Readiness Score ───────────────────────────────────────────────────────


@router.get("/readiness/{site_id}")
def api_usage_readiness(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Score de readiness usage d'un site (/100)."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return compute_usage_readiness(db, site_id)


# ── Metering Plan ─────────────────────────────────────────────────────────


@router.get("/metering-plan/{site_id}")
def api_metering_plan(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Plan de comptage dynamique d'un site."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return get_metering_plan(db, site_id)


# ── Top UES ───────────────────────────────────────────────────────────────


@router.get("/top-ues/{site_id}")
def api_top_ues(
    site_id: int,
    request: Request,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Top usages energetiques significatifs, tries par kWh."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return get_top_ues(db, site_id, limit=limit)


# ── Cost Breakdown ────────────────────────────────────────────────────────


@router.get("/cost-breakdown/{site_id}")
def api_usage_cost_breakdown(
    site_id: int,
    request: Request,
    days: int = Query(365, ge=30, le=1095),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Ventilation du cout energetique par usage."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return get_usage_cost_breakdown(db, site_id, days=days)


# ── Taxonomie ─────────────────────────────────────────────────────────────


@router.get("/taxonomy", response_model=UsageTaxonomyResponse)
def api_usage_taxonomy():
    """Retourne la taxonomie des usages energetiques (familles + types + labels FR)."""
    families = {}
    for usage_type in TypeUsage:
        family = USAGE_FAMILY_MAP.get(usage_type, UsageFamily.AUXILIAIRES)
        if family.value not in families:
            families[family.value] = {"family": family.value, "usages": []}
        families[family.value]["usages"].append(
            {
                "type": usage_type.value,
                "label": USAGE_LABELS_FR.get(usage_type, usage_type.value),
                "is_legacy": usage_type in (TypeUsage.BUREAUX, TypeUsage.CVC, TypeUsage.FROID),
            }
        )
    return {
        "families": list(families.values()),
        "data_sources": [{"value": ds.value, "label": ds.value.replace("_", " ").title()} for ds in DataSourceType],
    }


# ── V1.2 — Baselines ─────────────────────────────────────────────────────


@router.get("/baselines/{site_id}")
def api_usage_baselines(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Baselines auto-calculees avec comparaison avant/apres."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return compute_baselines(db, site_id)


# ── V1.2 — Compliance par usage ──────────────────────────────────────────


@router.get("/compliance/{site_id}")
def api_usage_compliance(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Widget conformite par usage (BACS, DT, ISO 50001)."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return get_usage_compliance(db, site_id)


# ── V1.2 — Billing links ────────────────────────────────────────────────


@router.get("/billing-links/{site_id}")
def api_usage_billing_links(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liens usage → facture → contrat → achat."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return get_usage_billing_links(db, site_id)


# ── CRUD Usages (liste, create) ──────────────────────────────────────────


@router.get("/site/{site_id}", response_model=list[UsageItemResponse])
def api_list_usages(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les usages declares pour un site."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    usages = db.query(Usage).join(Usage.batiment).filter(Usage.batiment.has(site_id=site_id)).all()

    return [
        {
            "id": u.id,
            "batiment_id": u.batiment_id,
            "type": u.type.value,
            "label": u.label or USAGE_LABELS_FR.get(u.type, u.type.value),
            "family": USAGE_FAMILY_MAP.get(u.type, UsageFamily.AUXILIAIRES).value,
            "description": u.description,
            "surface_m2": u.surface_m2,
            "data_source": u.data_source.value if u.data_source else None,
            "is_significant": u.is_significant,
            "pct_of_total": u.pct_of_total,
        }
        for u in usages
    ]


# ── V2 — Timeline mensuelle ─────────────────────────────────────────────


@router.get("/timeline/{site_id}")
def api_usage_timeline(
    site_id: int,
    request: Request,
    months: int = Query(12, ge=3, le=36),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Consommation mensuelle par usage pour AreaChart empile."""
    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    return get_usage_timeline(db, site_id, months=months)


# ── V2 — Comparaison inter-sites ────────────────────────────────────────


@router.get("/portfolio-compare")
def api_portfolio_usage_comparison(
    request: Request,
    archetype_code: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Compare les IPE par usage pour tous les sites d'une organisation, filtrable par archétype."""
    org_id = resolve_org_id(request, auth, db)
    return get_portfolio_usage_comparison(db, org_id, archetype_code=archetype_code)


# ── V2 — Meter readings preview ─────────────────────────────────────────


@router.get("/meter-readings/{meter_id}")
def api_meter_readings_preview(
    meter_id: int,
    request: Request,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Releves recents d'un compteur pour mini-graphe inline."""
    from models.energy_models import Meter
    from models import Site, Portefeuille, EntiteJuridique

    org_id = resolve_org_id(request, auth, db)
    meter = (
        db.query(Meter)
        .join(Site, Meter.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(Meter.id == meter_id, EntiteJuridique.organisation_id == org_id)
        .first()
    )
    if not meter:
        raise HTTPException(404, "Compteur non trouvé")
    return get_meter_readings_preview(db, meter_id, days=days)


# ── Signature énergétique (corrélation DJU) ────────────────────────────────


@router.get("/energy-signature/{site_id}")
def api_energy_signature(
    site_id: int,
    request: Request,
    months: int = Query(12, ge=3, le=36),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Signature énergétique E = a × DJU + b.
    Retourne : baseload, thermosensibilité, R², benchmark, potentiel économie.
    """
    from services.energy_signature_service import compute_energy_signature

    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    result = compute_energy_signature(db, site_id, months)
    if result is None:
        raise HTTPException(404, "Site non trouvé")
    return result


# ── Signature avancée multi-modèles ──────────────────────────────────────


@router.get("/energy-signature/{site_id}/advanced")
def api_energy_signature_advanced(
    site_id: int,
    request: Request,
    months: int = Query(12, ge=3, le=36),
    model: str = Query("auto", pattern="^(auto|2p|3p_heat|3p_cool|4p|5p)$"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Signature énergétique avancée avec sélection de modèle 3P/4P/5P.
    Retourne : modèle piecewise (Tb, Tc), classification, benchmark.
    """
    from services.energy_signature_service import compute_energy_signature_advanced

    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    result = compute_energy_signature_advanced(db, site_id, months, model)
    if result is None or (isinstance(result, dict) and "error" in result):
        detail = result.get("error", "Site non trouvé") if isinstance(result, dict) else "Site non trouvé"
        raise HTTPException(404, detail)
    return result


# ── Profil de charge (baseload, LF, ratios, qualité) ────────────────────


@router.get("/load-profile/{site_id}")
def api_load_profile(
    site_id: int,
    request: Request,
    months: int = Query(12, ge=3, le=36),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Profil de charge complet : baseload P5, load factor, ratios nuit/jour
    et semaine/WE, variabilité, score qualité, profil horaire type.
    """
    from services.load_profile_service import compute_load_profile

    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    result = compute_load_profile(db, site_id, months)
    if result is None or (isinstance(result, dict) and "error" in result):
        detail = result.get("error", "Site non trouvé") if isinstance(result, dict) else "Site non trouvé"
        raise HTTPException(404, detail)
    return result


# ── Benchmark sectoriel Enedis Open Data ─────────────────────────────────


@router.get("/benchmark/{site_id}")
def api_benchmark(
    site_id: int,
    request: Request,
    months: int = Query(12, ge=3, le=36),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Benchmark sectoriel : compare le site aux agrégats Enedis Open Data
    par secteur d'activité (NAF) × plage de puissance × région.
    Retourne : score d'atypie, profil horaire comparé, disclaimer.
    """
    from services.enedis_benchmarks import compute_benchmark

    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    result = compute_benchmark(db, site_id, months)
    if result is None or (isinstance(result, dict) and "error" in result):
        detail = result.get("error", "Site non trouvé") if isinstance(result, dict) else "Site non trouvé"
        raise HTTPException(404, detail)
    return result


# ── Optimisation puissance souscrite ───────────────────────────────────────


@router.get("/power-optimization/{site_id}")
def api_power_optimization(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Analyse de la puissance souscrite et recommandation d'optimisation."""
    from services.power_optimization_service import optimize_subscribed_power

    org_id = resolve_org_id(request, auth, db)
    _check_site_org(db, site_id, org_id)
    result = optimize_subscribed_power(db, site_id)
    if result is None:
        raise HTTPException(404, "Site non trouvé")
    return result
