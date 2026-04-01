"""
Site Intelligence endpoint — KB-driven anomalies, recommendations, archetype for a site.
Single source of truth for Site360 intelligence panel.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH
from services.billing_service import get_reference_price
from models import Site, Meter
from models.energy_models import UsageProfile, Anomaly, Recommendation, RecommendationStatus
from models.kb_models import KBArchetype

router = APIRouter(prefix="/api/sites", tags=["site-intelligence"])


def _deduplicate_recommendations(recos: list[dict]) -> list[dict]:
    """
    Déduplique les recos par recommendation_code.
    Si une reco apparaît N fois (par compteur), on fusionne :
    savings agrégés, count, max ICE conservé.
    """
    seen = {}
    for r in recos:
        key = r.get("recommendation_code") or r.get("title", "unknown")
        if key in seen:
            existing = seen[key]
            existing["estimated_savings_eur_year"] = (existing.get("estimated_savings_eur_year") or 0) + (
                r.get("estimated_savings_eur_year") or 0
            )
            existing["estimated_savings_kwh_year"] = (existing.get("estimated_savings_kwh_year") or 0) + (
                r.get("estimated_savings_kwh_year") or 0
            )
            existing["count"] = existing.get("count", 1) + 1
            if (r.get("ice_score") or 0) > (existing.get("ice_score") or 0):
                existing["ice_score"] = r["ice_score"]
        else:
            seen[key] = {**r, "count": 1}
    result = list(seen.values())
    result.sort(key=lambda x: x.get("ice_score") or 0, reverse=True)
    return result


def _fill_missing_eur_savings(recos: list[dict], price_eur_kwh: float = DEFAULT_PRICE_ELEC_EUR_KWH) -> None:
    """Estimate EUR savings from kWh when EUR is missing or zero.
    price_eur_kwh should be the site's reference price (all-in B2B tariff)."""
    for r in recos:
        if not r.get("estimated_savings_eur_year") and r.get("estimated_savings_kwh_year"):
            r["estimated_savings_eur_year"] = round(r["estimated_savings_kwh_year"] * price_eur_kwh)


@router.get("/{site_id}/intelligence")
def get_site_intelligence(site_id: int, db: Session = Depends(get_db)):
    """Return full KB intelligence for a site: archetype, anomalies, recommendations, summary."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")

    org_id = _resolve_org_id(db, site)

    meters = db.query(Meter).filter(Meter.site_id == site_id).all()
    if not meters:
        return {
            "site_id": site_id,
            "site_name": site.nom,
            "org_id": org_id,
            "archetype": None,
            "anomalies": [],
            "recommendations": [],
            "summary": _empty_summary(),
            "status": "no_meters",
        }

    site_price, _price_src = get_reference_price(db, site_id)

    meter_ids = [m.id for m in meters]

    # --- Archetype (best profile) ---
    profile = (
        db.query(UsageProfile)
        .filter(UsageProfile.meter_id.in_(meter_ids))
        .order_by(UsageProfile.archetype_match_score.desc().nullslast())
        .first()
    )

    archetype_data = None
    if profile and profile.archetype_code:
        kb_arch = db.query(KBArchetype).filter(KBArchetype.code == profile.archetype_code).first()
        archetype_data = {
            "code": profile.archetype_code,
            "match_score": round(profile.archetype_match_score or 0, 2),
            "title": kb_arch.title if kb_arch else profile.archetype_code,
            "kwh_m2_range": {
                "min": kb_arch.kwh_m2_min,
                "max": kb_arch.kwh_m2_max,
                "avg": kb_arch.kwh_m2_avg,
            }
            if kb_arch
            else None,
        }

    # --- Anomalies KB (active) ---
    # Join avec Meter pour récupérer energy_vector
    meter_map = {m.id: m for m in meters}
    anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.meter_id.in_(meter_ids), Anomaly.is_active == True)
        .order_by(Anomaly.severity.desc(), Anomaly.confidence.desc())
        .all()
    )

    anomalies_data = []
    for a in anomalies:
        title = a.title
        # Enrichir le titre benchmark/ratio_m2 avec le vecteur énergie
        meter = meter_map.get(a.meter_id)
        code_upper = (a.anomaly_code or "").upper()
        if meter and ("BENCHMARK" in code_upper or "RATIO_M2" in code_upper):
            vec = meter.energy_vector.value if hasattr(meter.energy_vector, "value") else str(meter.energy_vector)
            vec_label = {"electricity": "élec", "gas": "gaz"}.get(vec, vec)
            if vec_label and vec_label.lower() not in title.lower():
                title = f"{title} ({vec_label})"
        anomalies_data.append(
            {
                "id": a.id,
                "anomaly_code": a.anomaly_code,
                "title": title,
                "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
                "confidence": round(a.confidence, 2) if a.confidence else 0,
                "deviation_pct": round(a.deviation_pct, 1) if a.deviation_pct else None,
                "measured_value": a.measured_value,
                "threshold_value": a.threshold_value,
            }
        )

    # --- Recommendations (non-dismissed, by ICE) ---
    recos = (
        db.query(Recommendation)
        .filter(
            Recommendation.meter_id.in_(meter_ids),
            Recommendation.status != RecommendationStatus.DISMISSED,
        )
        .order_by(Recommendation.ice_score.desc().nullslast())
        .all()
    )

    recos_raw = [
        {
            "id": r.id,
            "recommendation_code": r.recommendation_code,
            "title": r.title,
            "estimated_savings_pct": r.estimated_savings_pct,
            "estimated_savings_kwh_year": r.estimated_savings_kwh_year,
            "estimated_savings_eur_year": r.estimated_savings_eur_year,
            "ice_score": round(r.ice_score, 3) if r.ice_score else None,
            "impact_score": r.impact_score,
            "confidence_score": r.confidence_score,
            "ease_score": r.ease_score,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
        }
        for r in recos
    ]
    recos_data = _deduplicate_recommendations(recos_raw)

    _fill_missing_eur_savings(recos_data, site_price)

    # --- Summary ---
    severity_counts = {}
    for a in anomalies:
        sev = a.severity.value if hasattr(a.severity, "value") else str(a.severity)
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    total_savings_kwh = sum(r.get("estimated_savings_kwh_year") or 0 for r in recos_data)
    total_savings_eur = sum(r.get("estimated_savings_eur_year") or 0 for r in recos_data)

    return {
        "site_id": site_id,
        "site_name": site.nom,
        "org_id": org_id,
        "archetype": archetype_data,
        "anomalies": anomalies_data,
        "recommendations": recos_data,
        "summary": {
            "total_anomalies": len(anomalies),
            "severity_breakdown": severity_counts,
            "total_recommendations": len(recos_data),
            "potential_savings_kwh_year": round(total_savings_kwh),
            "potential_savings_eur_year": round(total_savings_eur),
        },
        "status": "analyzed" if profile else "pending_analysis",
    }


def _fallback_reco(label: str, detail: str):
    return {"available": False, "label": label, "detail": detail, "source": "fallback"}


@router.get("/{site_id}/top-recommendation")
def get_top_recommendation(site_id: int, db: Session = Depends(get_db)):
    """Top reco KB pour un site. Utilisée par la fiche site."""
    try:
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            raise HTTPException(status_code=404, detail=f"Site {site_id} not found")

        meters = db.query(Meter).filter(Meter.site_id == site_id).all()
        if not meters:
            return _fallback_reco("Aucun compteur associé", "Ajoutez des compteurs pour activer l'analyse KB.")

        site_price, _ = get_reference_price(db, site_id)
        meter_ids = [m.id for m in meters]
        recos = (
            db.query(Recommendation)
            .filter(
                Recommendation.meter_id.in_(meter_ids),
                Recommendation.status != RecommendationStatus.DISMISSED,
            )
            .order_by(Recommendation.ice_score.desc().nullslast())
            .all()
        )

        recos_data = [
            {
                "recommendation_code": r.recommendation_code,
                "title": r.title,
                "description": r.description,
                "estimated_savings_eur_year": r.estimated_savings_eur_year,
                "estimated_savings_kwh_year": r.estimated_savings_kwh_year,
                "ice_score": round(r.ice_score, 3) if r.ice_score else None,
            }
            for r in recos
        ]
        deduped = _deduplicate_recommendations(recos_data)

        _fill_missing_eur_savings(deduped, site_price)

        if not deduped:
            return _fallback_reco(
                "Aucune recommandation disponible",
                "Complétez le profil énergétique pour recevoir des recommandations personnalisées.",
            )

        top = deduped[0]
        total_savings_eur = sum(r.get("estimated_savings_eur_year") or 0 for r in deduped)
        return {
            "available": True,
            "code": top.get("recommendation_code"),
            "label": top.get("title", "Recommandation"),
            "detail": top.get("description", ""),
            "ice_score": top.get("ice_score"),
            "savings_eur": top.get("estimated_savings_eur_year"),
            "savings_kwh": top.get("estimated_savings_kwh_year"),
            "total_savings_eur": round(total_savings_eur),
            "source": "kb",
            "total_recos": len(deduped),
        }
    except HTTPException:
        raise
    except Exception:
        logging.getLogger(__name__).warning("top-recommendation unavailable for site %s", site_id)
        return _fallback_reco("Analyse en cours", "Le moteur d'intelligence n'a pas encore analysé ce site.")


def _resolve_org_id(db, site):
    """Resolve org_id via site → portefeuille → entite_juridique → organisation."""
    if hasattr(site, "org_id") and site.org_id:
        return site.org_id
    if site.portefeuille_id:
        from models import Portefeuille, EntiteJuridique

        pf = db.query(Portefeuille).filter(Portefeuille.id == site.portefeuille_id).first()
        if pf and hasattr(pf, "entite_juridique_id") and pf.entite_juridique_id:
            ej = db.query(EntiteJuridique).filter(EntiteJuridique.id == pf.entite_juridique_id).first()
            if ej:
                return getattr(ej, "organisation_id", None)
    return None


def _empty_summary():
    return {
        "total_anomalies": 0,
        "severity_breakdown": {},
        "total_recommendations": 0,
        "potential_savings_kwh_year": 0,
        "potential_savings_eur_year": 0,
    }
