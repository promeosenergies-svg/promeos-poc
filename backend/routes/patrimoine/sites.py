"""
PROMEOS - Patrimoine Sites routes.
Site CRUD, KPIs, anomalies, snapshot, completeness, delivery_points, meters.
"""

import csv
import io
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from database import get_db
from models import (
    EntiteJuridique,
    Portefeuille,
    Site,
    DeliveryPoint,
    not_deleted,
    Compteur,
    TypeSite,
    EnergyContract,
    StatutConformite,
    Batiment,
)
from middleware.auth import get_optional_auth, get_portfolio_optional_auth, AuthContext
from services.error_catalog import business_error

from routes.patrimoine._helpers import (
    _get_org_id,
    _check_portfolio_belongs_to_org,
    _load_site_with_org_check,
    _serialize_site,
    _build_sites_query,
    _worst_compliance_status,
    _compute_site_completeness,
    SiteUpdateRequest,
    SiteMergeRequest,
    SubMeterCreateRequest,
    SiteAnomaliesResponse,
    UnifiedAnomaliesResponse,
    OrgAnomaliesResponse,
    PortfolioSummaryResponse,
    PatrimoineKpisResponse,
    DeliveryPointItemResponse,
    CompletenessResponse,
    SiteMetersResponse,
)

router = APIRouter(tags=["Patrimoine"])

_SORT_WHITELIST = {"nom", "ville", "surface_m2", "risque_financier_euro", "type", "created_at"}


# ========================================
# Delivery Points
# ========================================


@router.get("/sites/{site_id}/delivery-points", response_model=List[DeliveryPointItemResponse])
def site_delivery_points(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List active delivery points (PRM/PCE) for a site."""
    org_id = _get_org_id(request, auth, db)
    site = _load_site_with_org_check(db, site_id, org_id)

    dps = (
        not_deleted(db.query(DeliveryPoint), DeliveryPoint)
        .filter(
            DeliveryPoint.site_id == site_id,
        )
        .all()
    )

    return [
        {
            "id": dp.id,
            "code": dp.code,
            "energy_type": dp.energy_type.value if dp.energy_type else None,
            "status": dp.status.value if dp.status else None,
            "compteurs_count": len(dp.compteurs) if dp.compteurs else 0,
            "data_source": dp.data_source,
            "created_at": dp.created_at.isoformat() if dp.created_at else None,
        }
        for dp in dps
    ]


# ========================================
# KPIs (server-side aggregation)
# ========================================


@router.get("/kpis", response_model=PatrimoineKpisResponse)
def patrimoine_kpis(
    request: Request,
    site_id: Optional[int] = Query(None, description="Filter KPIs to a single site"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Unified KPIs for the patrimoine page — legacy + V-registre fields."""
    org_id = _get_org_id(request, auth, db)

    base_q = (
        db.query(Site)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .filter(not_deleted(Site))
    )

    if site_id is not None:
        base_q = base_q.filter(Site.id == site_id)

    result = base_q.with_entities(
        func.count(Site.id).label("total"),
        func.count(case((Site.statut_decret_tertiaire == StatutConformite.CONFORME, 1))).label("conformes"),
        func.count(case((Site.statut_decret_tertiaire == StatutConformite.A_RISQUE, 1))).label("a_risque"),
        func.count(case((Site.statut_decret_tertiaire == StatutConformite.NON_CONFORME, 1))).label("non_conformes"),
        func.coalesce(func.sum(Site.risque_financier_euro), 0).label("total_risque"),
        func.coalesce(func.sum(Site.surface_m2), 0).label("total_surface"),
        func.count(case((Site.anomalie_facture == True, 1))).label("total_anomalies"),
    ).one()

    # V-registre enrichment
    sites = base_q.all()
    site_ids = [s.id for s in sites]
    today = date.today()

    # EJ and PF counts — scoped to the actual sites in view
    pf_ids = set(s.portefeuille_id for s in sites if s.portefeuille_id)
    ej_ids = set()
    for s in sites:
        if s.portefeuille and s.portefeuille.entite_juridique_id:
            ej_ids.add(s.portefeuille.entite_juridique_id)
    nb_ej = (
        len(ej_ids)
        if site_id is not None
        else db.query(EntiteJuridique)
        .filter(
            EntiteJuridique.organisation_id == org_id,
            not_deleted(EntiteJuridique),
        )
        .count()
    )
    nb_pf = (
        len(pf_ids)
        if site_id is not None
        else (
            db.query(Portefeuille)
            .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
            .filter(EntiteJuridique.organisation_id == org_id, not_deleted(Portefeuille))
            .count()
        )
    )

    nb_batiments = db.query(Batiment).filter(Batiment.site_id.in_(site_ids)).count() if site_ids else 0

    nb_dp = (
        db.query(DeliveryPoint)
        .filter(
            DeliveryPoint.site_id.in_(site_ids),
            not_deleted(DeliveryPoint),
        )
        .count()
        if site_ids
        else 0
    )

    contracts_q = (
        db.query(EnergyContract).filter(EnergyContract.site_id.in_(site_ids))
        if site_ids
        else db.query(EnergyContract).filter(False)
    )
    nb_contrats = contracts_q.count()
    nb_contrats_actifs = contracts_q.filter(
        (EnergyContract.end_date >= today) | (EnergyContract.end_date.is_(None)),
        (EnergyContract.start_date <= today) | (EnergyContract.start_date.is_(None)),
    ).count()
    nb_contrats_expiring = contracts_q.filter(
        EnergyContract.end_date >= today,
        EnergyContract.end_date <= today + timedelta(days=90),
    ).count()

    completeness_scores = []
    for s in sites:
        score = _compute_site_completeness(db, s, site_ids)
        completeness_scores.append(score["score"])
    avg_completeness = round(sum(completeness_scores) / len(completeness_scores)) if completeness_scores else 0

    return {
        # Legacy fields (used by existing KPI cards)
        "total": result.total,
        "conformes": result.conformes,
        "aRisque": result.a_risque,
        "nonConformes": result.non_conformes,
        "totalRisque": round(float(result.total_risque), 2),
        "totalSurface": round(float(result.total_surface), 2),
        "totalAnomalies": result.total_anomalies,
        # V-registre fields
        "nb_organisations": 1,
        "nb_entites_juridiques": nb_ej,
        "nb_portefeuilles": nb_pf,
        "nb_sites": len(sites),
        "nb_batiments": nb_batiments,
        "nb_delivery_points": nb_dp,
        "nb_contrats": nb_contrats,
        "nb_contrats_actifs": nb_contrats_actifs,
        "nb_contrats_expiring_90j": nb_contrats_expiring,
        "surface_totale_m2": round(float(result.total_surface), 2),
        "completude_moyenne_pct": avg_completeness,
    }


# ========================================
# Site CRUD (WORLD CLASS)
# ========================================


@router.get("/sites")
def list_sites(
    request: Request,
    portefeuille_id: Optional[int] = None,
    actif: Optional[bool] = None,
    ville: Optional[str] = None,
    type_site: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(25, ge=1, le=200, description="Items per page"),
    sort_by: Optional[str] = Query(None, description="Sort column"),
    sort_dir: Optional[str] = Query("asc", description="Sort direction: asc or desc"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List sites with filters, pagination, and sorting — scoped to org."""
    org_id = _get_org_id(request, auth, db)
    q = _build_sites_query(db, org_id, portefeuille_id, actif, ville, type_site, search)

    # Sort
    if sort_by and sort_by in _SORT_WHITELIST:
        col = getattr(Site, sort_by, None)
        if col is not None:
            q = q.order_by(col.desc() if sort_dir == "desc" else col.asc())

    total = q.count()

    # Use page/page_size if page > 1, otherwise fall back to skip/limit for backward compat
    if page > 1 or page_size != 25:
        offset = (page - 1) * page_size
        sites = q.offset(offset).limit(page_size).all()
    else:
        sites = q.offset(skip).limit(limit).all()

    return {
        "total": total,
        "sites": [_serialize_site(s) for s in sites],
        "page": page,
        "page_size": page_size,
    }


@router.get("/sites/export.csv")
def export_sites_csv(
    request: Request,
    portefeuille_id: Optional[int] = None,
    actif: Optional[bool] = None,
    ville: Optional[str] = None,
    type_site: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Export filtered sites as CSV (streaming, UTF-8-sig BOM for French Excel)."""
    org_id = _get_org_id(request, auth, db)
    q = _build_sites_query(db, org_id, portefeuille_id, actif, ville, type_site, search)
    sites = q.all()

    headers = [
        "id",
        "nom",
        "type",
        "adresse",
        "code_postal",
        "ville",
        "region",
        "surface_m2",
        "nombre_employes",
        "siret",
        "actif",
        "risque_financier_euro",
        "statut_conformite",
        "anomalie_facture",
        "conso_kwh_an",
        "portefeuille_id",
    ]

    def iter_csv():
        yield "\ufeff"  # BOM for Excel
        out = io.StringIO()
        w = csv.writer(out, delimiter=";")
        w.writerow(headers)
        yield out.getvalue()
        for site in sites:
            out = io.StringIO()
            w = csv.writer(out, delimiter=";")
            w.writerow(
                [
                    site.id,
                    site.nom,
                    site.type.value if site.type else "",
                    site.adresse or "",
                    site.code_postal or "",
                    site.ville or "",
                    site.region or "",
                    site.surface_m2 or "",
                    site.nombre_employes or "",
                    site.siret or "",
                    site.actif,
                    site.risque_financier_euro or 0,
                    (
                        _worst_compliance_status(site.statut_decret_tertiaire, site.statut_bacs).value
                        if _worst_compliance_status(site.statut_decret_tertiaire, site.statut_bacs)
                        else ""
                    ),
                    site.anomalie_facture or False,
                    site.annual_kwh_total or "",
                    site.portefeuille_id or "",
                ]
            )
            yield out.getvalue()

    filename = f"patrimoine_sites_{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter_csv(),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sites/{site_id}")
def get_site_detail(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Get a site with compteurs, contracts count, and consumption source."""
    from services.meter_unified_service import get_site_meters

    org_id = _get_org_id(request, auth, db)
    site = _load_site_with_org_check(db, site_id, org_id)
    unified_meters = get_site_meters(db, site_id)
    compteurs_count = len(unified_meters)
    contracts_count = db.query(EnergyContract).filter(EnergyContract.site_id == site_id).count()

    # A.1: Consumption source info
    consumption_source = None
    try:
        from services.consumption_unified_service import get_consumption_summary
        from datetime import timedelta

        today = date.today()
        conso = get_consumption_summary(db, site_id, today - timedelta(days=365), today)
        consumption_source = conso["source_used"]
    except Exception:
        pass

    return {
        **_serialize_site(site),
        "compteurs_count": compteurs_count,
        "contracts_count": contracts_count,
        "consumption_source": consumption_source,
    }


@router.get("/sites/{site_id}/meters", response_model=SiteMetersResponse)
def list_site_meters_unified(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste unifiée des compteurs d'un site (Meter + Compteur legacy)."""
    from services.meter_unified_service import get_site_meters

    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)
    return {"meters": get_site_meters(db, site_id)}


@router.get("/sites/{site_id}/meters/tree")
def list_site_meters_tree(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Arbre compteurs avec sous-compteurs (1 niveau)."""
    from services.meter_unified_service import get_site_meters_tree

    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)
    return {"meters": get_site_meters_tree(db, site_id)}


@router.post("/meters/{meter_id}/sub-meters", status_code=201)
def create_sub_meter_endpoint(
    meter_id: int,
    body: SubMeterCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Crée un sous-compteur rattaché à un compteur principal."""
    from services.meter_unified_service import create_sub_meter

    try:
        result = create_sub_meter(db, meter_id, body.model_dump(exclude_unset=True))
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/meters/{meter_id}/sub-meters/{sub_id}")
def delete_sub_meter_endpoint(
    meter_id: int,
    sub_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Supprime un sous-compteur."""
    from services.meter_unified_service import delete_sub_meter

    if not delete_sub_meter(db, meter_id, sub_id):
        raise HTTPException(status_code=404, detail="Sous-compteur non trouvé ou mauvais parent")
    db.commit()
    return {"detail": f"Sous-compteur {sub_id} supprimé"}


@router.get("/meters/{meter_id}/breakdown")
def meter_breakdown_endpoint(
    meter_id: int,
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Breakdown principal vs sous-compteurs."""
    from services.meter_unified_service import get_meter_breakdown
    from datetime import datetime as dt

    df = dt.fromisoformat(date_from) if date_from else None
    dto = dt.fromisoformat(date_to) if date_to else None
    return get_meter_breakdown(db, meter_id, df, dto)


@router.patch("/sites/{site_id}")
def update_site(
    site_id: int,
    request: Request,
    body: SiteUpdateRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Update a site (partial update). V110: audit trail before/after."""
    import json as _json
    from models.iam import AuditLog

    org_id = _get_org_id(request, auth, db)
    site = _load_site_with_org_check(db, site_id, org_id)

    changes = body.model_dump(exclude_unset=True)
    before = {}
    for field in changes:
        val = getattr(site, field, None)
        before[field] = val.value if hasattr(val, "value") else val

    updated_fields = []
    for field, value in changes.items():
        if field == "type" and value is not None:
            try:
                value = TypeSite(value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Type invalide: {value}")
        setattr(site, field, value)
        updated_fields.append(field)

    after = {}
    for field in changes:
        val = getattr(site, field, None)
        after[field] = val.value if hasattr(val, "value") else val

    diff = {k: {"before": before.get(k), "after": after[k]} for k in after if before.get(k) != after[k]}
    if diff:
        db.add(
            AuditLog(
                user_id=auth.user_id if auth else None,
                action="site.update",
                resource_type="site",
                resource_id=str(site_id),
                detail_json=_json.dumps(diff, default=str, ensure_ascii=False),
                ip_address=request.client.host if request.client else None,
            )
        )

    db.commit()

    # Propagation conformite si champs critiques modifies
    from services.patrimoine_conformite_sync import flag_efa_desync_on_surface_change, reevaluate_on_usage_change

    if "surface_m2" in updated_fields:
        flag_efa_desync_on_surface_change(db, site_id)
    if any(f in updated_fields for f in ("type", "naf_code")):
        reevaluate_on_usage_change(db, site_id)
    if any(f in updated_fields for f in ("surface_m2", "type", "naf_code")):
        db.commit()

    return {"updated": updated_fields, **_serialize_site(site)}


@router.post("/sites/{site_id}/archive")
def archive_site(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Soft-delete a site. V110: audit trail."""
    from models.iam import AuditLog

    org_id = _get_org_id(request, auth, db)
    site = _load_site_with_org_check(db, site_id, org_id)
    if site.is_deleted:
        return {"detail": "Site deja archive", "site_id": site_id}
    site.soft_delete()

    # Cascade conformite
    from services.patrimoine_conformite_sync import cascade_site_archive

    cascade_result = cascade_site_archive(db, site_id)
    db.add(
        AuditLog(
            user_id=auth.user_id if auth else None,
            action="site.archive",
            resource_type="site",
            resource_id=str(site_id),
            detail_json=f'{{"nom": "{site.nom}"}}',
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    return {"detail": "Site archive", "site_id": site_id, "cascade": cascade_result}


@router.post("/sites/{site_id}/restore")
def restore_site(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Restore an archived site."""
    org_id = _get_org_id(request, auth, db)
    site = _load_site_with_org_check(db, site_id, org_id)
    if not site.is_deleted:
        return {"detail": "Site deja actif", "site_id": site_id}
    site.restore()
    db.commit()
    return {"detail": "Site restaure", "site_id": site_id}


@router.post("/sites/merge")
def merge_sites(
    request: Request,
    body: SiteMergeRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Merge source site into target: transfer compteurs+contracts, archive source."""
    org_id = _get_org_id(request, auth, db)
    source = _load_site_with_org_check(db, body.source_site_id, org_id)
    target = _load_site_with_org_check(db, body.target_site_id, org_id)
    if source.id == target.id:
        raise HTTPException(status_code=400, detail="Source et cible identiques")

    # Transfer compteurs
    compteurs_moved = (
        db.query(Compteur)
        .filter(Compteur.site_id == source.id)
        .update({"site_id": target.id}, synchronize_session="fetch")
    )
    # Transfer contracts
    contracts_moved = (
        db.query(EnergyContract)
        .filter(EnergyContract.site_id == source.id)
        .update({"site_id": target.id}, synchronize_session="fetch")
    )
    # Archive source
    source.soft_delete()
    db.commit()

    return {
        "detail": f"Site {source.id} fusionne dans {target.id}",
        "compteurs_moved": compteurs_moved,
        "contracts_moved": contracts_moved,
        "source_archived": True,
    }


# ========================================
# Snapshot & Anomalies (V58 → V59)
# ========================================


@router.get("/sites/{site_id}/snapshot")
def get_site_snapshot_endpoint(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Snapshot canonique d'un site : surface SoT, bâtiments, compteurs,
    points de livraison, contrats.  Scoped org — zéro N+1.
    """
    from services.patrimoine_snapshot import get_site_snapshot

    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)  # 404/403 si hors périmètre
    snapshot = get_site_snapshot(site_id, org_id, db)
    if snapshot is None:
        raise HTTPException(**business_error("SITE_NOT_FOUND", site_id=site_id))
    return snapshot


@router.get("/sites/{site_id}/anomalies", response_model=SiteAnomaliesResponse)
def get_site_anomalies_endpoint(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Anomalies de données patrimoine pour un site (8 règles P0).
    V59 : enrichies avec regulatory_impact, business_impact, priority_score.
    Triées par priority_score DESC.
    """
    from services.patrimoine_anomalies import compute_site_anomalies
    from services.patrimoine_impact import enrich_anomalies_with_impact
    from services.patrimoine_snapshot import get_site_snapshot
    from config.patrimoine_assumptions import DEFAULT_ASSUMPTIONS

    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)

    result = compute_site_anomalies(site_id, db)
    # Snapshot optionnel pour améliorer SURFACE_MISMATCH (usage-aware)
    snapshot = get_site_snapshot(site_id, org_id, db) or {}
    enriched = enrich_anomalies_with_impact(result["anomalies"], snapshot, DEFAULT_ASSUMPTIONS)
    total_risk_eur = sum((a.get("business_impact") or {}).get("estimated_risk_eur") or 0.0 for a in enriched)
    return {
        **result,
        "anomalies": enriched,
        "total_estimated_risk_eur": round(total_risk_eur, 0),
        "assumptions_used": DEFAULT_ASSUMPTIONS.to_dict(),
    }


def _normalize_kb_severity(raw: str) -> str:
    """Normalise la sévérité KB vers l'échelle patrimoine."""
    mapping = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "warning": "medium",
        "low": "low",
        "info": "low",
    }
    return mapping.get(raw.lower() if raw else "", "medium")


@router.get("/sites/{site_id}/anomalies-unified", response_model=UnifiedAnomaliesResponse)
def get_unified_anomalies(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Anomalies unifiées : patrimoine (intégrité données) + KB analytique (conso).
    Graceful degradation : si KB indisponible, retourne patrimoine seul.
    """
    import logging

    from services.patrimoine_anomalies import compute_site_anomalies
    from services.patrimoine_impact import enrich_anomalies_with_impact
    from services.patrimoine_snapshot import get_site_snapshot
    from config.patrimoine_assumptions import DEFAULT_ASSUMPTIONS

    org_id = _get_org_id(request, auth, db)
    _load_site_with_org_check(db, site_id, org_id)

    # 1. Anomalies patrimoine (toujours disponibles)
    pat_result = compute_site_anomalies(site_id, db)
    snapshot = get_site_snapshot(site_id, org_id, db) or {}
    enriched = enrich_anomalies_with_impact(pat_result["anomalies"], snapshot, DEFAULT_ASSUMPTIONS)

    unified = []
    for a in enriched:
        unified.append(
            {
                "source": "patrimoine",
                "code": a["code"],
                "severity": a["severity"].lower(),
                "title_fr": a["title_fr"],
                "detail_fr": a.get("detail_fr"),
                "evidence": a.get("evidence"),
                "cta": a.get("cta"),
                "fix_hint_fr": a.get("fix_hint_fr"),
                "regulatory_impact": a.get("regulatory_impact"),
                "business_impact": a.get("business_impact"),
                "priority_score": a.get("priority_score"),
            }
        )

    # 2. Anomalies KB analytiques (graceful degradation)
    kb_anomalies = []
    try:
        from models.energy_models import Anomaly as KBAnomaly, Meter

        meter_ids_subq = db.query(Meter.id).filter(Meter.site_id == site_id)
        kb_rows = (
            db.query(KBAnomaly)
            .filter(
                KBAnomaly.meter_id.in_(meter_ids_subq),
                KBAnomaly.is_active == True,  # noqa: E712
            )
            .all()
        )
        if kb_rows:
            for a in kb_rows:
                sev = a.severity.value if hasattr(a.severity, "value") else str(a.severity)
                kb_anomalies.append(
                    {
                        "source": "analytique",
                        "code": a.anomaly_code,
                        "severity": _normalize_kb_severity(sev),
                        "title_fr": a.title or a.anomaly_code,
                        "detail_fr": a.description,
                        "confidence": round(a.confidence, 2) if a.confidence else None,
                        "deviation_pct": round(a.deviation_pct, 1) if a.deviation_pct else None,
                        "measured_value": a.measured_value,
                        "threshold_value": a.threshold_value,
                    }
                )
    except Exception:
        logging.getLogger(__name__).warning("KB anomalies indisponibles pour site %s, patrimoine seul", site_id)

    _SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    # Dédupliquer anomalies KB par code (même anomalie sur N compteurs → 1 seule)
    kb_deduped = {}
    for a in kb_anomalies:
        key = a["code"]
        if key in kb_deduped:
            existing = kb_deduped[key]
            existing["meter_count"] = existing.get("meter_count", 1) + 1
            if abs(a.get("deviation_pct") or 0) > abs(existing.get("deviation_pct") or 0):
                existing["deviation_pct"] = a["deviation_pct"]
                existing["measured_value"] = a["measured_value"]
            if _SEV_ORDER.get(a["severity"], 9) < _SEV_ORDER.get(existing["severity"], 9):
                existing["severity"] = a["severity"]
        else:
            kb_deduped[key] = {**a, "meter_count": 1}
    unified.extend(kb_deduped.values())
    unified.sort(
        key=lambda x: (
            _SEV_ORDER.get(x.get("severity", "low"), 99),
            -(x.get("priority_score") or 0),
        )
    )

    return {
        "site_id": site_id,
        "anomalies": unified,
        "total": len(unified),
        "patrimoine_count": len(enriched),
        "analytique_count": len(kb_deduped),
        "completude_score": pat_result.get("completude_score"),
        "computed_at": datetime.now(timezone.utc).isoformat() + "Z",
    }


@router.get("/anomalies/batch")
def get_anomalies_batch(
    request: Request,
    site_ids: str = Query(..., description="Comma-separated site IDs, max 50"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Anomalies batch : retourne anomalies + score + risque pour N sites en un appel.
    V110 : remplace N appels /sites/{id}/anomalies depuis le frontend heatmap.
    """
    from services.patrimoine_anomalies import compute_site_anomalies
    from services.patrimoine_impact import enrich_anomalies_with_impact
    from config.patrimoine_assumptions import DEFAULT_ASSUMPTIONS

    org_id = _get_org_id(request, auth, db)
    ids = [int(x) for x in site_ids.split(",") if x.strip().isdigit()][:50]
    if not ids:
        return {}

    # Charger tous les sites de l'org en un seul query pour éviter N queries
    org_sites = (
        db.query(Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id, Site.id.in_(ids), not_deleted(Site))
        .all()
    )
    site_map = {s.id: s for s in org_sites}

    results = {}
    for sid in ids:
        if sid not in site_map:
            continue
        result = compute_site_anomalies(sid, db)
        enriched = enrich_anomalies_with_impact(result["anomalies"], {}, DEFAULT_ASSUMPTIONS)
        total_risk = sum((a.get("business_impact") or {}).get("estimated_risk_eur") or 0.0 for a in enriched)
        results[str(sid)] = {
            "completude_score": result.get("completude_score", 0),
            "nb_anomalies": result.get("nb_anomalies", 0),
            "total_estimated_risk_eur": round(total_risk, 0),
            "top_severity": enriched[0]["severity"] if enriched else None,
            "top_anomalies": [
                {"code": a["code"], "severity": a["severity"], "title_fr": a.get("title_fr", "")} for a in enriched[:3]
            ],
        }
    return results


@router.get("/anomalies", response_model=OrgAnomaliesResponse)
def list_org_anomalies(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Filtre sites avec score ≤ min_score"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Liste paginée des sites de l'org avec leurs anomalies patrimoine (V59).
    Chaque anomalie enrichie : regulatory_impact, business_impact, priority_score.
    Triée par completude_score ASC (plus dégradés en premier).
    """
    from services.patrimoine_anomalies import compute_site_anomalies
    from services.patrimoine_impact import enrich_anomalies_with_impact
    from config.patrimoine_assumptions import DEFAULT_ASSUMPTIONS
    from sqlalchemy.orm import joinedload

    org_id = _get_org_id(request, auth, db)

    sites_q = (
        db.query(Site)
        .options(
            joinedload(Site.batiments),
            joinedload(Site.delivery_points),
        )
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .filter(Site.actif.is_(True))
        .order_by(Site.id)
    )
    all_sites = sites_q.all()

    results = []
    for site in all_sites:
        data = compute_site_anomalies(site.id, db)
        if min_score is not None and data["completude_score"] > min_score:
            continue
        enriched = enrich_anomalies_with_impact(data["anomalies"], None, DEFAULT_ASSUMPTIONS)
        total_risk_eur = sum((a.get("business_impact") or {}).get("estimated_risk_eur") or 0.0 for a in enriched)
        top_priority = enriched[0]["priority_score"] if enriched else None
        results.append(
            {
                "site_id": site.id,
                "nom": site.nom,
                "completude_score": data["completude_score"],
                "nb_anomalies": data["nb_anomalies"],
                "top_severity": enriched[0]["severity"] if enriched else None,
                "top_priority_score": top_priority,
                "total_estimated_risk_eur": round(total_risk_eur, 0),
                "anomalies": enriched,
            }
        )

    # Tri : scores les plus bas en premier (les plus à risque)
    results.sort(key=lambda r: r["completude_score"])

    total = len(results)
    offset = (page - 1) * page_size
    page_items = results[offset : offset + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "sites": page_items,
    }


@router.get("/assumptions")
def get_patrimoine_assumptions():
    """
    Retourne les hypothèses de calcul d'impact en lecture seule (V59).
    Permet au frontend d'afficher la transparence des estimations.
    """
    from config.patrimoine_assumptions import DEFAULT_ASSUMPTIONS

    return DEFAULT_ASSUMPTIONS.to_dict()


@router.get("/portfolio-summary", response_model=PortfolioSummaryResponse)
def get_portfolio_summary(
    request: Request,
    portefeuille_id: Optional[int] = Query(None, description="Filtre par portefeuille"),
    site_id: Optional[int] = Query(None, description="Filtre par site unique"),
    top_n: int = Query(default=3, ge=1, le=10, description="Nombre de top sites retournés"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_portfolio_optional_auth),
):
    """
    Agrégation portfolio patrimoine : risque global, framework breakdown, top sites (V60).

    - Multi-org safe : scoped via org_id + filtres optionnels portefeuille/site.
    - Zéro N+1 côté query SQL — enrichissement impact fait en mémoire via enrich_anomalies_with_impact().
    - Cas critique : org vide ou scope vide → tout à 0, listes vides, pas de crash.
    - top_n (1..10, défaut 3) : contrôle la taille de top_sites.
    - Gracieux : si org non résolue (no auth, no demo) → 200 empty (jamais de 401/403).
    """
    from services.patrimoine_anomalies import compute_site_anomalies
    from services.patrimoine_impact import enrich_anomalies_with_impact
    from config.patrimoine_assumptions import DEFAULT_ASSUMPTIONS
    from services.patrimoine_portfolio_cache import get_prev_snapshot, set_snapshot

    # Résolution org_id gracieuse : si non résolu → 200 vide (pas de 401/403)
    # Évite le bandeau d'erreur frontend quand l'auth n'est pas encore établie.
    try:
        org_id = _get_org_id(request, auth, db)
    except HTTPException:
        # Org non résolue : pas d'auth, pas de DemoState, pas d'org active en DB.
        # Retourner une réponse vide valide plutôt qu'une erreur 401/403.
        from datetime import datetime as _dt, timezone as _tz

        return {
            "scope": {"org_id": None, "portefeuille_id": portefeuille_id, "site_id": site_id},
            "total_estimated_risk_eur": 0.0,
            "sites_count": 0,
            "sites_at_risk": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "sites_health": {"healthy": 0, "warning": 0, "critical": 0, "healthy_pct": 0.0},
            "framework_breakdown": [],
            "top_sites": [],
            "trend": None,
            "computed_at": _dt.now(_tz.utc).isoformat(),
        }

    _SEV_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}

    # Build sites query — même chaîne de jointures que list_org_anomalies
    sites_q = (
        db.query(Site)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .filter(Site.actif.is_(True))
        .order_by(Site.id)
    )
    if portefeuille_id is not None:
        sites_q = sites_q.filter(Site.portefeuille_id == portefeuille_id)
    if site_id is not None:
        sites_q = sites_q.filter(Site.id == site_id)

    all_sites = sites_q.all()

    _HEALTH_HEALTHY = 85
    _HEALTH_WARNING = 50

    # Scope vide → tout à 0
    if not all_sites:
        computed_at_empty = datetime.now(timezone.utc).isoformat() + "Z"
        # Trend V62 : scope vide → on ne met pas en cache (pas de data utile)
        empty_resp = {
            "scope": {"org_id": org_id, "portefeuille_id": portefeuille_id, "site_id": site_id},
            "total_estimated_risk_eur": 0.0,
            "sites_count": 0,
            "sites_at_risk": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "sites_health": {"healthy": 0, "warning": 0, "critical": 0, "healthy_pct": 0.0},
            "framework_breakdown": [],
            "top_sites": [],
            "trend": None,
            "computed_at": computed_at_empty,
        }
        return empty_resp

    # Agrégation
    total_risk = 0.0
    sites_at_risk: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    sites_health: Dict[str, Any] = {"healthy": 0, "warning": 0, "critical": 0}
    framework_totals: Dict[str, Dict] = {}
    site_summaries = []

    for site in all_sites:
        data = compute_site_anomalies(site.id, db)
        enriched = enrich_anomalies_with_impact(data["anomalies"], None, DEFAULT_ASSUMPTIONS)

        site_risk = sum((a.get("business_impact") or {}).get("estimated_risk_eur") or 0.0 for a in enriched)
        total_risk += site_risk

        # Pire sévérité du site → bucket sites_at_risk
        if enriched:
            worst_sev = max(
                (a["severity"] for a in enriched),
                key=lambda s: _SEV_ORDER.get(s, 0),
            ).lower()
            if worst_sev in sites_at_risk:
                sites_at_risk[worst_sev] += 1

        # V2 — santé alignée sur statut_conformite + risque (cohérent avec la table)
        sc = getattr(site, "statut_conformite", None) or "a_evaluer"
        if sc in ("a_risque", "non_conforme") or site_risk > 0:
            sites_health["critical"] += 1
        else:
            sites_health["healthy"] += 1

        # Breakdown par framework réglementaire
        for a in enriched:
            fw = (a.get("regulatory_impact") or {}).get("framework", "NONE")
            if fw == "NONE":
                continue
            risk_a = (a.get("business_impact") or {}).get("estimated_risk_eur") or 0.0
            if fw not in framework_totals:
                framework_totals[fw] = {"risk_eur": 0.0, "anomalies_count": 0}
            framework_totals[fw]["risk_eur"] += risk_a
            framework_totals[fw]["anomalies_count"] += 1

        # Framework dominant du site (depuis l'anomalie top priority)
        top_fw: Optional[str] = None
        if enriched:
            ri = enriched[0].get("regulatory_impact") or {}
            fw0 = ri.get("framework", "NONE")
            top_fw = fw0 if fw0 != "NONE" else None

        site_summaries.append(
            {
                "site_id": site.id,
                "site_nom": site.nom,
                "risk_eur": round(site_risk, 0),
                "anomalies_count": data["nb_anomalies"],
                "top_framework": top_fw,
            }
        )

    # healthy_pct final
    n_total = len(all_sites)
    sites_health["healthy_pct"] = round(sites_health["healthy"] / n_total * 100, 1) if n_total else 0.0

    # Top N sites par risk_eur DESC
    site_summaries.sort(key=lambda s: s["risk_eur"], reverse=True)
    top_sites = site_summaries[:top_n]

    # Framework breakdown trié par risk_eur DESC
    framework_breakdown = [
        {
            "framework": fw,
            "risk_eur": round(v["risk_eur"], 0),
            "anomalies_count": v["anomalies_count"],
        }
        for fw, v in sorted(framework_totals.items(), key=lambda x: x[1]["risk_eur"], reverse=True)
    ]

    computed_at = datetime.now(timezone.utc).isoformat() + "Z"
    total_risk_rounded = round(total_risk, 0)

    # V62 — Trend réel via snapshot in-memory par org_id
    # On ne cache que lorsque le scope est global (pas de filtre site/portefeuille)
    # pour éviter de polluer la baseline avec une vue partielle.
    _EPS = 1.0  # €  — seuil anti-bruit
    trend_payload: Optional[Dict[str, Any]] = None

    if portefeuille_id is None and site_id is None:
        prev = get_prev_snapshot(org_id)
        if prev is not None:
            delta_risk = total_risk_rounded - prev["total_estimated_risk_eur"]
            delta_sites = n_total - prev["sites_count"]
            if delta_risk > _EPS:
                direction = "up"
            elif delta_risk < -_EPS:
                direction = "down"
            else:
                direction = "stable"
            trend_payload = {
                "risk_eur_delta": round(delta_risk, 0),
                "sites_count_delta": delta_sites,
                "direction": direction,
                "vs_computed_at": prev["computed_at"],
            }
        # Mettre à jour le snapshot courant APRÈS avoir lu le précédent
        set_snapshot(
            org_id,
            {
                "computed_at": computed_at,
                "total_estimated_risk_eur": total_risk_rounded,
                "sites_count": n_total,
            },
        )

    return {
        "scope": {"org_id": org_id, "portefeuille_id": portefeuille_id, "site_id": site_id},
        "total_estimated_risk_eur": total_risk_rounded,
        "sites_count": n_total,
        "sites_at_risk": sites_at_risk,
        "sites_health": sites_health,
        "framework_breakdown": framework_breakdown,
        "top_sites": top_sites,
        "trend": trend_payload,
        "computed_at": computed_at,
    }


# ========================================
# V-registre: Completude site
# ========================================


@router.get("/sites/{site_id}/completeness", response_model=CompletenessResponse)
def get_site_completeness(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Score de completude d'un site du registre patrimonial."""
    org_id = _get_org_id(request, auth, db)
    site = _load_site_with_org_check(db, site_id, org_id)
    return _compute_site_completeness(db, site, [site_id])


# ── SIRENE Lookup ────────────────────────────────────────────────────────


@router.get("/lookup-siret/{siret}")
def lookup_siret_endpoint(
    siret: str,
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Lookup SIRET via recherche-entreprises.api.gouv.fr (gratuit, sans clé)."""
    from services.sirene_lookup import lookup_siret

    # Validate format before any processing
    clean = siret.strip().replace(" ", "")
    if len(clean) != 14 or not clean.isdigit():
        return {"found": False, "siret": clean, "error": "Format SIRET invalide (14 chiffres)"}

    result = lookup_siret(clean)
    if not result:
        return {"found": False, "siret": clean}
    return {"found": True, **result}


# ── Scope Tree ───────────────────────────────────────────────────────────


@router.get("/scope-tree")
def get_scope_tree(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Arbre hiérarchique Org → Entités → Portefeuilles → Sites pour le scope switcher."""
    org_id = _get_org_id(request, auth, db)

    entites = (
        db.query(EntiteJuridique)
        .filter(EntiteJuridique.organisation_id == org_id, not_deleted(EntiteJuridique))
        .order_by(EntiteJuridique.nom)
        .all()
    )

    tree = []
    for ej in entites:
        pfs = (
            db.query(Portefeuille)
            .filter(Portefeuille.entite_juridique_id == ej.id, not_deleted(Portefeuille))
            .order_by(Portefeuille.nom)
            .all()
        )
        pf_list = []
        for pf in pfs:
            sites = db.query(Site).filter(Site.portefeuille_id == pf.id, not_deleted(Site)).order_by(Site.nom).all()
            pf_list.append(
                {
                    "id": pf.id,
                    "nom": pf.nom,
                    "sites": [{"id": s.id, "nom": s.nom} for s in sites],
                }
            )
        tree.append(
            {
                "id": ej.id,
                "nom": ej.nom,
                "siren": ej.siren,
                "portefeuilles": pf_list,
            }
        )

    return {"org_id": org_id, "entites": tree}
