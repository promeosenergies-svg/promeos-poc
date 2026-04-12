"""
PROMEOS - Analytics Routes
GET /api/analytics/sites/{site_id}/usage-breakdown    — decomposition CDC en usages (3 couches)
GET /api/analytics/sites/{site_id}/usage-anomalies    — anomalies par usage (contextualisees)
GET /api/analytics/sites/{site_id}/optimization-plan  — plan d'optimisation ROI chiffre (etage 3)
"""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/sites/{site_id}/usage-breakdown")
def get_site_usage_breakdown(
    site_id: int,
    days: int = Query(365, ge=30, le=730, description="Nombre de jours d'historique"),
    db: Session = Depends(get_db),
):
    """
    Decompose la courbe de charge du site en usages canoniques.

    3 couches de decomposition :
    1. Thermique (DJU) -> CVC_HVAC (confidence HIGH si R2 >= 0.6)
    2. Temporelle (occupation) -> baseload nuit, increment business hours
    3. Archetype (residuel) -> calibrage CEREN/ADEME

    Returns:
        {
            "site_id": 1,
            "total_kwh": 125000.0,
            "archetype_code": "BUREAU_STANDARD",
            "usages": [
                {"code": "CVC_HVAC", "kwh": 46250, "pct": 37.0, "method": "dju_regression", "confidence": "high"},
                {"code": "ECLAIRAGE", "kwh": 27500, "pct": 22.0, "method": "temporal_business", "confidence": "medium"},
                ...
            ],
            "thermal_signature": {"base_kwh": 250, "a_heating": 18.5, "r2": 0.78, ...},
            "temporal_profile": {"baseload_kw": 15.2, "biz_mean_kw": 42.5, ...},
            "confidence_global": "medium",
            "method": "3_layer_decomposition"
        }
    """
    from datetime import date, timedelta
    from services.analytics.usage_disaggregation import disaggregate_site

    date_fin = date.today()
    date_debut = date_fin - timedelta(days=days)

    try:
        result = disaggregate_site(db, site_id, date_debut, date_fin)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return asdict(result)


@router.get("/sites/{site_id}/usage-anomalies")
def get_site_usage_anomalies(
    site_id: int,
    days: int = Query(365, ge=30, le=730, description="Nombre de jours d'historique"),
    db: Session = Depends(get_db),
):
    """
    Detecte les anomalies par usage en croisant la decomposition CDC
    avec les seuils contextuels de l'archetype du site.

    6 detecteurs :
    1. CVC active la nuit (hors horaires d'occupation)
    2. Consommation weekend excessive
    3. Eclairage probablement actif la nuit
    4. CVC surdimensionnee (faible correlation DJU)
    5. ECS en heures de pointe au lieu de heures creuses
    6. Intensite energetique (kWh/m2) hors norme archetype

    Returns:
        {
            "site_id": 1,
            "archetype_code": "BUREAU_STANDARD",
            "n_anomalies": 3,
            "total_gain_eur_an": 8200,
            "anomalies": [
                {
                    "usage_code": "CVC_HVAC",
                    "anomaly_type": "CVC_NUIT_EXCESSIF",
                    "severity": "high",
                    "message": "CVC active la nuit : 35% du talon vs 20% attendu",
                    "gain_eur_an": 5400,
                    "action": "Programmer l'arret CVC..."
                },
                ...
            ]
        }
    """
    from datetime import date, timedelta
    from services.analytics.usage_anomaly_detector import detect_usage_anomalies

    date_fin = date.today()
    date_debut = date_fin - timedelta(days=days)

    try:
        result = detect_usage_anomalies(db, site_id, date_debut, date_fin)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return asdict(result)


@router.get("/sites/{site_id}/optimization-plan")
def get_site_optimization_plan(
    site_id: int,
    days: int = Query(365, ge=30, le=730),
    db: Session = Depends(get_db),
):
    """
    Plan d'optimisation par usage avec ROI chiffre (etage 3).

    Croise decomposition CDC (etage 1), anomalies (etage 2) et catalogue
    d'actions pour produire un plan trie par payback croissant (quick wins d'abord).
    """
    from datetime import date, timedelta
    from services.analytics.usage_optimization_engine import generate_optimization_plan

    date_fin = date.today()
    date_debut = date_fin - timedelta(days=days)

    try:
        result = generate_optimization_plan(db, site_id, date_debut, date_fin)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return asdict(result)
