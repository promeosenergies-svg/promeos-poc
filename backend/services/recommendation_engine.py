"""
Recommendation Engine — transforme les KPIs analytics en actions priorisées.

Parse les résultats de :
- load_profile_service (baseload, LF, ratios, qualité)
- energy_signature_service (signature 3P/4P/5P)
- enedis_benchmarks (score d'atypie)
- naf_estimator (comparaison site vs secteur)

Génère des objets Anomaly + Recommendation avec ICE scoring dans la DB.
"""

import logging
import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH
from models.energy_models import (
    Anomaly,
    Recommendation,
    Meter,
    AnomalySeverity,
    RecommendationStatus,
)

logger = logging.getLogger(__name__)


def _ice(impact: int, confidence: int, ease: int) -> float:
    """ICE score = moyenne géométrique (plus robuste que produit)."""
    return round((impact * confidence * ease) ** (1 / 3), 2)


# ── Rules metier : KPI → (Anomaly, Recommendation) ───────────────────────


def _rule_baseload_excessive(load_profile: dict, meter_id: int) -> tuple[dict, dict] | None:
    """Baseload > 60% du max → serveurs/veilles/éclairage permanent."""
    baseload = load_profile.get("baseload", {})
    verdict = baseload.get("verdict")
    pct = baseload.get("baseload_pct_of_mean", 0)
    p_moy = load_profile.get("power_stats", {}).get("p_mean_kwh", 0)

    if verdict != "eleve" or pct < 60:
        return None

    excess_kwh_year = round((pct - 40) / 100 * p_moy * 8760, 0)
    excess_eur_year = round(excess_kwh_year * DEFAULT_PRICE_ELEC_EUR_KWH, 0)

    anomaly = {
        "code": "ANOM_BASELOAD_ELEVE",
        "title": "Baseload excessive (talon de consommation anormal)",
        "explanation": (
            f"La consommation minimale nocturne/WE représente {pct}% de la moyenne, "
            f"indiquant un gaspillage probable (serveurs, éclairage permanent, veilles)."
        ),
        "severity": "high",
        "confidence": 0.85,
        "measured_value": pct,
        "threshold_value": 40.0,
        "deviation_pct": round((pct - 40), 1),
    }

    reco = {
        "code": "RECO_REDUIRE_BASELOAD",
        "title": "Éteindre les équipements hors occupation",
        "description": (
            "Identifier les équipements qui tournent la nuit et le week-end "
            "(serveurs, CVC mal programmé, éclairage, veilles). "
            "Mettre en place un pilotage horaire ou manuel."
        ),
        "impact_score": 9,
        "confidence_score": 8,
        "ease_score": 7,
        "estimated_savings_kwh": excess_kwh_year,
        "estimated_savings_eur": excess_eur_year,
        "estimated_savings_pct": round((pct - 40) / pct * 100, 1),
    }
    return anomaly, reco


def _rule_low_load_factor(load_profile: dict, meter_id: int) -> tuple[dict, dict] | None:
    """Load factor < 0.15 → puissance souscrite surdimensionnée."""
    lf = load_profile.get("load_factor", 0)
    if lf >= 0.15 or lf == 0:
        return None

    anomaly = {
        "code": "ANOM_LOAD_FACTOR_FAIBLE",
        "title": "Puissance souscrite potentiellement surdimensionnée",
        "explanation": (
            f"Facteur de charge {lf} très faible : la puissance max appelée est beaucoup "
            f"plus élevée que la moyenne. L'abonnement peut probablement être réduit."
        ),
        "severity": "medium",
        "confidence": 0.75,
        "measured_value": lf,
        "threshold_value": 0.15,
        "deviation_pct": round((0.15 - lf) / 0.15 * 100, 1),
    }

    reco = {
        "code": "RECO_OPTIMISER_PSOUS",
        "title": "Optimiser la puissance souscrite",
        "description": (
            "Analyser la monotone de charge pour déterminer la puissance souscrite "
            "optimale. Une réduction d'un palier TURPE peut économiser 10-20% sur "
            "l'abonnement annuel sans risquer les dépassements."
        ),
        "impact_score": 7,
        "confidence_score": 7,
        "ease_score": 9,  # Changement contractuel simple
        "estimated_savings_kwh": 0,  # Economie sur abonnement, pas sur conso
        "estimated_savings_eur": 500,  # Ordre de grandeur
        "estimated_savings_pct": 15.0,
    }
    return anomaly, reco


def _rule_night_day_ratio_high(load_profile: dict, meter_id: int) -> tuple[dict, dict] | None:
    """Ratio nuit/jour > 0.5 pour un tertiaire → activité nocturne anormale."""
    ratio = load_profile.get("ratios", {}).get("night_day", 0)
    if ratio < 0.5:
        return None

    anomaly = {
        "code": "ANOM_NUIT_JOUR_ELEVE",
        "title": "Consommation nocturne anormalement élevée",
        "explanation": (
            f"Ratio nuit/jour de {ratio} : plus de 50% de la consommation diurne "
            f"se poursuit la nuit. Pour un site tertiaire, c'est un indicateur fort "
            f"de gaspillage hors occupation."
        ),
        "severity": "high",
        "confidence": 0.80,
        "measured_value": ratio,
        "threshold_value": 0.5,
        "deviation_pct": round((ratio - 0.5) / 0.5 * 100, 1),
    }

    reco = {
        "code": "RECO_PILOTAGE_NOCTURNE",
        "title": "Programmer l'arrêt CVC/éclairage hors occupation",
        "description": (
            "Mettre en place un scénario GTB/horloge pour arrêter CVC, éclairage "
            "et équipements non critiques de 20h à 7h et les week-ends."
        ),
        "impact_score": 8,
        "confidence_score": 7,
        "ease_score": 6,  # Nécessite GTB ou horloges
        "estimated_savings_kwh": 5000,
        "estimated_savings_eur": 340,
        "estimated_savings_pct": 10.0,
    }
    return anomaly, reco


def _rule_thermosensitivity_high(signature: dict, meter_id: int) -> tuple[dict, dict] | None:
    """Part thermosensible > 40% → potentiel isolation élevé."""
    thermo = signature.get("thermosensitivity", {})
    part_pct = thermo.get("part_thermo_pct", 0)
    if part_pct < 40:
        return None

    classification = thermo.get("classification", "")
    if classification not in ("heating_dominant", "mixed"):
        return None

    anomaly = {
        "code": "ANOM_THERMOSENSIBILITE_ELEVEE",
        "title": "Forte dépendance chauffage électrique",
        "explanation": (
            f"Part thermosensible de {part_pct}% (hiver vs base). Le bâtiment est très "
            f"sensible à la météo, indiquant une isolation perfectible ou un chauffage "
            f"électrique dominant sans régulation."
        ),
        "severity": "medium",
        "confidence": 0.75,
        "measured_value": part_pct,
        "threshold_value": 40.0,
        "deviation_pct": round((part_pct - 40), 1),
    }

    reco = {
        "code": "RECO_ISOLATION_THERMIQUE",
        "title": "Audit énergétique ciblé + plan d'isolation",
        "description": (
            "La thermosensibilité élevée indique un potentiel d'économie via isolation "
            "(toiture, fenêtres, murs) et/ou régulation CVC (sondes, optimisation, PAC). "
            "Un audit énergétique ciblé permet de prioriser les travaux par ROI."
        ),
        "impact_score": 8,
        "confidence_score": 6,
        "ease_score": 4,  # Travaux lourds, capex
        "estimated_savings_kwh": 15000,
        "estimated_savings_eur": 1020,
        "estimated_savings_pct": 20.0,
    }
    return anomaly, reco


def _rule_atypicity_high(benchmark: dict, meter_id: int) -> tuple[dict, dict] | None:
    """Score d'atypie > 0.50 → profil très éloigné du secteur."""
    atyp = benchmark.get("atypicity", {})
    score = atyp.get("score")
    if score is None or score < 0.50:
        return None

    sector = benchmark.get("sector_enedis", "")
    site_stats = benchmark.get("site_stats", {})
    conso_spec = site_stats.get("conso_kwh_m2_year", 0)

    anomaly = {
        "code": "ANOM_ATYPIE_SECTEUR",
        "title": "Profil de charge atypique vs secteur",
        "explanation": (
            f"Score d'atypie {score} (très atypique) vs benchmark Enedis {sector}. "
            f"Consommation spécifique : {conso_spec} kWh/m²/an. "
            f"Le profil horaire diverge significativement de la moyenne sectorielle."
        ),
        "severity": "medium",
        "confidence": 0.70,
        "measured_value": score,
        "threshold_value": 0.30,
        "deviation_pct": round((score - 0.30) / 0.30 * 100, 1),
    }

    reco = {
        "code": "RECO_DIAGNOSTIC_ATYPIE",
        "title": "Diagnostic énergétique pour identifier la cause d'atypie",
        "description": (
            f"Le profil diverge fortement du segment {sector}. Causes possibles : "
            f"activité mixte sur un seul PDL, équipements spécifiques non-standards, "
            f"horaires atypiques, ou anomalie réelle. Un audit terrain est recommandé."
        ),
        "impact_score": 6,
        "confidence_score": 5,
        "ease_score": 7,
        "estimated_savings_kwh": 3000,
        "estimated_savings_eur": 205,
        "estimated_savings_pct": 5.0,
    }
    return anomaly, reco


def _rule_data_quality_low(load_profile: dict, meter_id: int) -> tuple[dict, dict] | None:
    """Score qualité < 0.80 → alerter sur fiabilité analyses."""
    quality = load_profile.get("data_quality", {})
    score = quality.get("score", 1.0)
    if score >= 0.80:
        return None

    details = quality.get("details", {})
    gaps = details.get("gaps", 0)

    anomaly = {
        "code": "ANOM_QUALITE_DONNEES",
        "title": "Qualité de données insuffisante pour analyses fiables",
        "explanation": (
            f"Score qualité {score} (seuil : 0.80). "
            f"{gaps} jours manquants, {details.get('outliers', 0)} valeurs aberrantes. "
            f"Les analyses ci-dessous sont à interpréter avec prudence."
        ),
        "severity": "low",
        "confidence": 0.95,
        "measured_value": score,
        "threshold_value": 0.80,
        "deviation_pct": round((0.80 - score) / 0.80 * 100, 1),
    }

    reco = {
        "code": "RECO_FIABILISER_COLLECTE",
        "title": "Activer courbes Linky + vérifier acquisition",
        "description": (
            "Activer l'enregistrement des courbes de charge Linky (inhibé par défaut), "
            "vérifier la connexion Data Connect et relancer une collecte complète pour "
            "disposer de données fiables pour les analyses."
        ),
        "impact_score": 3,  # Pas d'économie directe mais débloque les analyses
        "confidence_score": 10,
        "ease_score": 9,
        "estimated_savings_kwh": 0,
        "estimated_savings_eur": 0,
        "estimated_savings_pct": 0,
    }
    return anomaly, reco


# ── Rules orchestration ───────────────────────────────────────────────────


_RULES = [
    ("load_profile", _rule_baseload_excessive),
    ("load_profile", _rule_low_load_factor),
    ("load_profile", _rule_night_day_ratio_high),
    ("load_profile", _rule_data_quality_low),
    ("signature", _rule_thermosensitivity_high),
    ("benchmark", _rule_atypicity_high),
]


def generate_recommendations_for_site(db: Session, site_id: int, persist: bool = True) -> dict:
    """Analyse un site avec tous les services et génère des recommandations.

    Si persist=True, insère les Anomaly + Recommendation en DB.
    Retourne un dict avec les recommandations classées par ICE score.
    """
    from services.load_profile_service import compute_load_profile
    from services.energy_signature_service import compute_energy_signature_advanced
    from services.enedis_benchmarks import compute_benchmark

    # Trouver le compteur principal pour FK
    main_meter = db.query(Meter).filter(Meter.site_id == site_id, Meter.parent_meter_id.is_(None)).first()
    if not main_meter:
        return {"error": "Aucun compteur principal", "site_id": site_id}

    meter_id = main_meter.id

    # Collecter les analytics
    analytics = {}
    load_profile = compute_load_profile(db, site_id)
    if load_profile and "error" not in load_profile:
        analytics["load_profile"] = load_profile

    signature = compute_energy_signature_advanced(db, site_id)
    if signature and "error" not in signature:
        analytics["signature"] = signature

    benchmark = compute_benchmark(db, site_id)
    if benchmark and "error" not in benchmark:
        analytics["benchmark"] = benchmark

    if not analytics:
        return {"error": "Aucune analyse disponible", "site_id": site_id}

    # Appliquer les règles
    generated = []
    for source_key, rule_fn in _RULES:
        source_data = analytics.get(source_key)
        if not source_data:
            continue
        result = rule_fn(source_data, meter_id)
        if result:
            anomaly_dict, reco_dict = result
            reco_dict["ice_score"] = _ice(
                reco_dict["impact_score"],
                reco_dict["confidence_score"],
                reco_dict["ease_score"],
            )
            generated.append((anomaly_dict, reco_dict))

    # Trier par ICE score décroissant
    generated.sort(key=lambda x: x[1]["ice_score"], reverse=True)

    # Persister
    persisted = []
    if persist and generated:
        for rank, (anom_dict, reco_dict) in enumerate(generated, 1):
            # Désactiver les anomalies existantes du même code
            db.query(Anomaly).filter(
                Anomaly.meter_id == meter_id,
                Anomaly.anomaly_code == anom_dict["code"],
                Anomaly.is_active.is_(True),
            ).update({"is_active": False})

            anom = Anomaly(
                meter_id=meter_id,
                anomaly_code=anom_dict["code"],
                title=anom_dict["title"],
                description=anom_dict["explanation"],
                severity=AnomalySeverity(anom_dict["severity"]),
                confidence=anom_dict["confidence"],
                detected_at=datetime.now(timezone.utc),
                measured_value=anom_dict["measured_value"],
                threshold_value=anom_dict["threshold_value"],
                deviation_pct=anom_dict["deviation_pct"],
                is_active=True,
            )
            db.add(anom)
            db.flush()

            reco = Recommendation(
                meter_id=meter_id,
                recommendation_code=reco_dict["code"],
                title=reco_dict["title"],
                description=reco_dict["description"],
                triggered_by_anomaly_id=anom.id,
                impact_score=reco_dict["impact_score"],
                confidence_score=reco_dict["confidence_score"],
                ease_score=reco_dict["ease_score"],
                ice_score=reco_dict["ice_score"],
                priority_rank=rank,
                estimated_savings_kwh_year=reco_dict["estimated_savings_kwh"],
                estimated_savings_eur_year=reco_dict.get("estimated_savings_eur"),
                estimated_savings_pct=reco_dict["estimated_savings_pct"],
                status=RecommendationStatus.PENDING,
            )
            db.add(reco)
            db.flush()
            persisted.append(
                {
                    "anomaly_id": anom.id,
                    "recommendation_id": reco.id,
                    "code": reco_dict["code"],
                    "ice_score": reco_dict["ice_score"],
                }
            )

        db.commit()

    return {
        "site_id": site_id,
        "meter_id": meter_id,
        "n_recommendations": len(generated),
        "recommendations": [
            {
                "code": r["code"],
                "title": r["title"],
                "description": r["description"],
                "impact_score": r["impact_score"],
                "confidence_score": r["confidence_score"],
                "ease_score": r["ease_score"],
                "ice_score": r["ice_score"],
                "priority_rank": i + 1,
                "estimated_savings_kwh_year": r["estimated_savings_kwh"],
                "estimated_savings_eur_year": r.get("estimated_savings_eur", 0),
                "estimated_savings_pct": r["estimated_savings_pct"],
                "triggered_by": {
                    "code": a["code"],
                    "severity": a["severity"],
                    "explanation": a["explanation"],
                },
            }
            for i, (a, r) in enumerate(generated)
        ],
        "persisted": persisted,
    }
