"""
PROMEOS - Cockpit Executive V2
Endpoint unique /api/cockpit/executive-v2 : hero impact + 4 KPIs santé + actions triées.
"""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import (
    Organisation,
    Portefeuille,
    EntiteJuridique,
    Site,
    BillingInsight,
    not_deleted,
)
from models.enums import InsightStatus
from models.billing_models import EnergyContract
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id
from services.kpi_service import KpiService, KpiScope
from services.consumption_unified_service import get_portfolio_consumption

_logger = logging.getLogger("promeos.cockpit_v2")

router = APIRouter(prefix="/api/cockpit", tags=["cockpit-v2"])


def _sites_for_org(db: Session, org_id: int | None):
    """Sites non-supprimés filtrés par org_id."""
    q = (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
    )
    if org_id is not None:
        q = q.filter(EntiteJuridique.organisation_id == org_id)
    return q


def _get_site_ids(db: Session, org_id: int | None) -> list[int]:
    return [s.id for s in _sites_for_org(db, org_id).with_entities(Site.id).all()]


@router.get("/executive-v2", tags=["cockpit-v2"])
def get_executive_v2(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Vue exécutive V1+ : hero impact + 4 KPIs santé + actions triées."""
    effective_org_id = resolve_org_id(request, auth, db)
    org = db.query(Organisation).filter(Organisation.id == effective_org_id).first()
    if not org:
        return JSONResponse(status_code=404, content={"detail": "Organisation non trouvée"})

    sites = _sites_for_org(db, effective_org_id).all()
    site_ids = [s.id for s in sites]
    total_sites = len(sites)

    if total_sites == 0:
        return JSONResponse(content=_empty_response(org))

    # ── 1. Conformité (KpiService) ──
    kpi = KpiService(db)
    scope = KpiScope(org_id=effective_org_id)
    risque_total = kpi.get_financial_risk_eur(scope).value
    compliance_kpi = kpi.get_compliance_score(scope)
    conformite_score = compliance_kpi.value

    # Détails conformité
    from models import StatutConformite
    from models.reg_assessment import RegAssessment

    non_conformes = (
        _sites_for_org(db, effective_org_id)
        .filter(Site.statut_decret_tertiaire == StatutConformite.NON_CONFORME)
        .count()
    )
    a_risque = (
        _sites_for_org(db, effective_org_id).filter(Site.statut_decret_tertiaire == StatutConformite.A_RISQUE).count()
    )

    # Trend conformité
    trend_text = None
    try:
        from services.compliance_history_service import get_score_trend

        trend = get_score_trend(db, effective_org_id, months=6)
        if trend and len(trend) >= 2:
            first_score = trend[0].get("score", 0)
            delta = round(conformite_score - first_score)
            if delta > 0:
                trend_text = f"+{delta} pts en 6 mois"
            elif delta < 0:
                trend_text = f"{delta} pts en 6 mois"
    except Exception:
        pass

    # ── 2. Billing ──
    billing_loss = 0.0
    billing_anomalies_count = 0
    billing_total_eur = 0.0
    try:
        from services.billing_service import get_billing_summary

        billing = get_billing_summary(db, effective_org_id)
        billing_loss = billing.get("total_estimated_loss_eur", 0) or 0
        billing_anomalies_count = billing.get("invoices_with_anomalies", 0) or 0
        billing_total_eur = billing.get("total_eur", 0) or 0
    except Exception as e:
        _logger.warning(f"Billing summary failed: {e}")

    # ── 3. Optimisation = 1% du total facturé ──
    optimisation_eur = round(billing_total_eur * 0.01)

    # ── 4. Impact total ──
    conformite_eur = round(risque_total, 2)
    factures_eur = round(billing_loss, 2)
    total_impact = round(conformite_eur + factures_eur + optimisation_eur, 2)

    # ── 5. Consommation ──
    today = date.today()
    conso_start = today - timedelta(days=365)
    total_kwh = 0
    conso_sites_with_data = 0
    try:
        conso = get_portfolio_consumption(db, effective_org_id, conso_start, today)
        total_kwh = conso.get("total_kwh", 0) or 0
        conso_sites_with_data = conso.get("sites_with_data", 0) or 0
    except Exception as e:
        _logger.warning(f"Consumption failed: {e}")

    surface_totale = sum(s.surface_m2 or 0 for s in sites)
    total_mwh = round(total_kwh / 1000, 1) if total_kwh else 0
    kwh_m2_an = round(total_kwh / surface_totale) if surface_totale > 0 else 0

    # ── 6. Qualité données ──
    sites_avec_donnees = sum(1 for s in sites if (getattr(s, "conso_kwh_an", 0) or 0) > 0 or total_kwh > 0)
    # Utiliser la couverture conso du portfolio si disponible
    if conso_sites_with_data > 0:
        sites_avec_donnees = conso_sites_with_data

    couverture_sites = sites_avec_donnees / total_sites if total_sites > 0 else 0
    couverture_conso = conso_sites_with_data / total_sites if total_sites > 0 else 0

    # Briques de données
    briques = _compute_data_briques(sites, db, site_ids)
    briques_ok = briques["completes"]
    briques_total = briques["total"]

    score_qualite = round(
        (couverture_sites * 0.3 + (briques_ok / max(briques_total, 1)) * 0.4 + couverture_conso * 0.3) * 100
    )

    # ── 7. Contrats + alertes expiration (D.3) ──
    contrats_actifs = 0
    contrats_expiring_90j = 0
    sites_sans_contrat = 0
    try:
        contrats_actifs = (
            db.query(EnergyContract)
            .filter(
                EnergyContract.site_id.in_(site_ids),
                EnergyContract.end_date >= today,
            )
            .count()
        )
        contrats_expiring_90j = (
            db.query(EnergyContract)
            .filter(
                EnergyContract.site_id.in_(site_ids),
                EnergyContract.end_date >= today,
                EnergyContract.end_date <= today + timedelta(days=90),
            )
            .count()
        )
        sites_with_contract = (
            db.query(EnergyContract.site_id)
            .filter(
                EnergyContract.site_id.in_(site_ids),
                EnergyContract.end_date >= today,
            )
            .distinct()
            .count()
        )
        sites_sans_contrat = total_sites - sites_with_contract

        # D.3: Génération automatique d'alertes pour contrats expirant sous 90j
        from services.contract_expiration_alerts import generate_contract_expiration_alerts

        generate_contract_expiration_alerts(db, site_ids, horizon_days=90)
        db.commit()
    except Exception as e:
        _logger.warning(f"Contracts query failed: {e}")

    couverture_contrats = round((1 - sites_sans_contrat / total_sites) * 100) if total_sites > 0 else 0
    contrats_status = "warn" if contrats_expiring_90j > 0 else "ok"

    # ── 8. Actions triées ──
    actions = _build_actions(
        non_conformes=non_conformes,
        a_risque=a_risque,
        conformite_eur=conformite_eur,
        billing_anomalies=billing_anomalies_count,
        factures_eur=factures_eur,
        contrats_expiring=contrats_expiring_90j,
        optimisation_eur=optimisation_eur,
        sites=sites,
    )

    # ── 9. Déterminer statuts ──
    conformite_status = "crit" if non_conformes > 0 else ("warn" if a_risque > 0 else "ok")
    qualite_status = "ok" if score_qualite >= 70 else ("warn" if score_qualite >= 40 else "crit")
    conso_status = "ok" if couverture_conso >= 0.8 else ("warn" if couverture_conso >= 0.5 else "crit")

    # Conformité detail
    detail_parts = []
    if a_risque > 0 or non_conformes > 0:
        detail_parts.append(f"DT {round(conformite_score)}%")
    try:
        bacs_count = (
            _sites_for_org(db, effective_org_id)
            .filter(Site.statut_bacs.in_([StatutConformite.NON_CONFORME, StatutConformite.A_RISQUE]))
            .count()
        )
        if bacs_count > 0:
            detail_parts.append(f"BACS {bacs_count} sites")
    except Exception:
        pass
    conformite_detail = " · ".join(detail_parts) if detail_parts else f"Score {round(conformite_score)}/100"

    # Nombre de sites avec contrats expiring pour l'action
    sites_with_expiring = 0
    try:
        sites_with_expiring = (
            db.query(EnergyContract.site_id)
            .filter(
                EnergyContract.site_id.in_(site_ids),
                EnergyContract.end_date >= today,
                EnergyContract.end_date <= today + timedelta(days=90),
            )
            .distinct()
            .count()
        )
    except Exception:
        pass

    response = {
        "org": {
            "nom": org.nom,
            "total_sites": total_sites,
            "surface_totale_m2": round(surface_totale, 1),
        },
        "synchro": today.isoformat() + "T08:42:00Z",
        "impact": {
            "total_eur": total_impact,
            "conformite_eur": conformite_eur,
            "factures_eur": factures_eur,
            "optimisation_eur": optimisation_eur,
            "sites_concernes": total_sites,
        },
        "sante": {
            "conformite": {
                "score": round(conformite_score),
                "detail": conformite_detail,
                "non_conformes": non_conformes,
                "a_risque": a_risque,
                "trend": trend_text,
                "status": conformite_status,
            },
            "qualite_donnees": {
                "score": score_qualite,
                "sites_avec_donnees": sites_avec_donnees,
                "total_sites": total_sites,
                "briques_completes": briques_ok,
                "briques_partielles": briques_total - briques_ok,
                "status": qualite_status,
            },
            "contrats": {
                "actifs": contrats_actifs,
                "couverture_pct": couverture_contrats,
                "expirant_90j": contrats_expiring_90j,
                "sites_sans_contrat": sites_sans_contrat,
                "status": contrats_status,
            },
            "consommation": {
                "total_mwh": total_mwh,
                "kwh_m2_an": kwh_m2_an,
                "couverture_pct": round(couverture_conso * 100),
                "status": conso_status,
            },
        },
        "actions": actions,
    }

    return JSONResponse(
        content=response,
        headers={"Cache-Control": "public, max-age=30"},
    )


def _compute_data_briques(sites, db, site_ids):
    """Calcule les briques de données complètes/partielles."""
    total_briques = 0
    completes = 0

    for site in sites:
        # Briques par site : compteur, contrat, facture, surface, horaires, consommation
        briques_site = 6
        ok = 0

        # Surface
        if site.surface_m2 and site.surface_m2 > 0:
            ok += 1

        # Consommation
        if (getattr(site, "conso_kwh_an", 0) or 0) > 0:
            ok += 1

        # Contrat actif
        has_contract = (
            db.query(EnergyContract)
            .filter(
                EnergyContract.site_id == site.id,
                EnergyContract.end_date >= date.today(),
            )
            .first()
            is not None
        )
        if has_contract:
            ok += 1

        # Facture
        try:
            from models import EnergyInvoice

            has_invoice = (
                db.query(EnergyInvoice)
                .filter(
                    EnergyInvoice.site_id == site.id,
                )
                .first()
                is not None
            )
            if has_invoice:
                ok += 1
        except Exception:
            pass

        # Compteur
        try:
            from models.energy_models import Meter

            has_meter = (
                db.query(Meter)
                .filter(
                    Meter.site_id == site.id,
                )
                .first()
                is not None
            )
            if has_meter:
                ok += 1
        except Exception:
            pass

        # Horaires/type
        if site.type:
            ok += 1

        total_briques += briques_site
        completes += ok

    return {"completes": completes, "total": total_briques}


def _build_actions(
    non_conformes,
    a_risque,
    conformite_eur,
    billing_anomalies,
    factures_eur,
    contrats_expiring,
    optimisation_eur,
    sites,
):
    """Construit et trie les actions par impact_eur DESC, nulls last."""
    actions = []

    # Action DT à risque
    if a_risque > 0:
        actions.append(
            {
                "id": "act_dt_risque",
                "rang": 0,
                "titre": f"Prévenir {a_risque} site{'s' if a_risque > 1 else ''} à risque Décret Tertiaire",
                "description": "Échéance 2026 · plan d'actions disponible",
                "categorie": "conformite",
                "impact_eur": round(conformite_eur * 0.8) if conformite_eur > 0 else None,
                "lien": "/conformite",
                "cta": "Agir",
            }
        )

    # Action anomalies factures
    if billing_anomalies > 0:
        actions.append(
            {
                "id": "act_anomalies_factures",
                "rang": 0,
                "titre": f"Corriger {billing_anomalies} anomalie{'s' if billing_anomalies > 1 else ''} de facturation",
                "description": f"{billing_anomalies} factures impactées",
                "categorie": "facturation",
                "impact_eur": round(factures_eur) if factures_eur > 0 else None,
                "lien": "/bill-intel",
                "cta": "Agir",
            }
        )

    # Action NC régularisation
    if non_conformes > 0:
        nc_sites = [
            s
            for s in sites
            if getattr(s, "statut_decret_tertiaire", None)
            and str(s.statut_decret_tertiaire) == "StatutConformite.NON_CONFORME"
        ]
        nc_name = nc_sites[0].nom if nc_sites else "Site"
        actions.append(
            {
                "id": "act_nc_regularisation",
                "rang": 0,
                "titre": f"Régulariser {non_conformes} site{'s' if non_conformes > 1 else ''} non conforme{'s' if non_conformes > 1 else ''}",
                "description": f"{nc_name} · statut NC",
                "categorie": "conformite",
                "impact_eur": round(conformite_eur * 0.2) if conformite_eur > 0 else None,
                "lien": "/conformite",
                "cta": "Agir",
            }
        )

    # Action contrats renouvellement
    if contrats_expiring > 0:
        actions.append(
            {
                "id": "act_contrats_renouvellement",
                "rang": 0,
                "titre": f"Renouveler {contrats_expiring} contrat{'s' if contrats_expiring > 1 else ''} énergie",
                "description": "Expiration sous 90 jours",
                "categorie": "achat",
                "impact_eur": None,
                "lien": "/achat-energie",
                "cta": "Analyser",
            }
        )

    # Action optimisation tarifaire
    if optimisation_eur > 0:
        actions.append(
            {
                "id": "act_optim_tarifaire",
                "rang": 0,
                "titre": "Lancer l'optimisation tarifaire",
                "description": "Estimation 1% du facturé récupérable",
                "categorie": "optimisation",
                "impact_eur": optimisation_eur,
                "lien": "/achat-energie",
                "cta": "Agir",
            }
        )

    # Tri : impact_eur DESC, nulls last
    actions.sort(key=lambda a: (a["impact_eur"] is None, -(a["impact_eur"] or 0)))

    # Assigner les rangs
    for i, action in enumerate(actions):
        action["rang"] = i + 1

    return actions


def _empty_response(org):
    """Réponse pour un patrimoine vide."""
    return {
        "org": {"nom": org.nom, "total_sites": 0, "surface_totale_m2": 0},
        "synchro": date.today().isoformat() + "T00:00:00Z",
        "impact": {
            "total_eur": 0,
            "conformite_eur": 0,
            "factures_eur": 0,
            "optimisation_eur": 0,
            "sites_concernes": 0,
        },
        "sante": {
            "conformite": {"score": 0, "detail": "", "non_conformes": 0, "a_risque": 0, "trend": None, "status": "ok"},
            "qualite_donnees": {
                "score": 0,
                "sites_avec_donnees": 0,
                "total_sites": 0,
                "briques_completes": 0,
                "briques_partielles": 0,
                "status": "ok",
            },
            "contrats": {"actifs": 0, "couverture_pct": 0, "expirant_90j": 0, "sites_sans_contrat": 0, "status": "ok"},
            "consommation": {"total_mwh": 0, "kwh_m2_an": 0, "couverture_pct": 0, "status": "ok"},
        },
        "actions": [],
    }
