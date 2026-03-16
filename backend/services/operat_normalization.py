"""
PROMEOS — Service normalisation climatique OPERAT

Methode DJU (Degres-Jours Unifies) :
  conso_normalisee = conso_brute * (DJU_reference / DJU_observe)

Si DJU absents : pas de normalisation, warning explicite.
La valeur brute n'est JAMAIS ecrasee.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import TertiaireEfaConsumption
from models.compliance_event_log import ComplianceEventLog

logger = logging.getLogger("promeos.operat.normalization")


def normalize_consumption(
    db: Session,
    consumption_id: int,
    dju_heating: Optional[float] = None,
    dju_cooling: Optional[float] = None,
    dju_reference: Optional[float] = None,
    weather_data_source: str = "manual",
) -> dict:
    """Normalise climatiquement une consommation EFA existante.

    Methode DJU : conso_norm = conso_brute * (DJU_ref / DJU_observe)
    Si DJU absents : retour sans normalisation avec warning.
    La valeur brute (kwh_total) n'est JAMAIS modifiee.
    """
    conso = db.query(TertiaireEfaConsumption).filter(TertiaireEfaConsumption.id == consumption_id).first()
    if not conso:
        raise ValueError(f"Consommation {consumption_id} introuvable")

    raw_kwh = conso.kwh_total
    warnings = []

    # Verifier disponibilite DJU
    dju_observe = dju_heating  # Simplification : on utilise les DJU chauffage comme proxy principal
    if dju_observe is None or dju_reference is None:
        # Pas de normalisation possible
        conso.is_normalized = False
        conso.normalization_method = "none"
        conso.normalization_confidence = "none"
        conso.normalized_kwh_total = None
        conso.dju_heating = dju_heating
        conso.dju_cooling = dju_cooling
        conso.dju_reference = dju_reference
        conso.weather_data_source = weather_data_source
        conso.normalized_at = datetime.now(timezone.utc)
        db.flush()

        warnings.append("Donnees meteo insuffisantes — normalisation impossible")
        return {
            "consumption_id": consumption_id,
            "raw_kwh": raw_kwh,
            "normalized_kwh": None,
            "delta_kwh": None,
            "delta_percent": None,
            "method": "none",
            "confidence": "none",
            "warnings": warnings,
        }

    if dju_observe <= 0:
        raise ValueError("DJU observe doit etre > 0")

    # Calcul normalisation DJU
    ratio = dju_reference / dju_observe
    normalized_kwh = round(raw_kwh * ratio)

    # Confiance basee sur l'ecart DJU
    ecart_pct = abs(ratio - 1.0) * 100
    if ecart_pct <= 5:
        confidence = "high"
    elif ecart_pct <= 15:
        confidence = "medium"
    else:
        confidence = "low"
        warnings.append(f"Ecart DJU important ({ecart_pct:.0f}%) — normalisation a verifier")

    # Persister
    conso.is_normalized = True
    conso.normalized_kwh_total = normalized_kwh
    conso.normalization_method = "dju_ratio"
    conso.normalization_confidence = confidence
    conso.dju_heating = dju_heating
    conso.dju_cooling = dju_cooling
    conso.dju_reference = dju_reference
    conso.weather_data_source = weather_data_source
    conso.normalized_at = datetime.now(timezone.utc)
    db.flush()

    # Audit-trail
    db.add(
        ComplianceEventLog(
            entity_type="TertiaireEfaConsumption",
            entity_id=conso.id,
            action="normalize",
            after_json=json.dumps(
                {
                    "raw_kwh": raw_kwh,
                    "normalized_kwh": normalized_kwh,
                    "method": "dju_ratio",
                    "confidence": confidence,
                    "dju_observe": dju_observe,
                    "dju_reference": dju_reference,
                    "weather_source": weather_data_source,
                }
            ),
            actor="system",
            source_context="api_normalize",
        )
    )
    db.flush()

    delta_kwh = normalized_kwh - raw_kwh
    delta_pct = round(delta_kwh / raw_kwh * 100, 1) if raw_kwh else 0

    return {
        "consumption_id": consumption_id,
        "raw_kwh": raw_kwh,
        "normalized_kwh": normalized_kwh,
        "delta_kwh": delta_kwh,
        "delta_percent": delta_pct,
        "method": "dju_ratio",
        "confidence": confidence,
        "dju_observe": dju_observe,
        "dju_reference": dju_reference,
        "ratio": round(ratio, 4),
        "warnings": warnings,
    }


def get_normalization_history(db: Session, efa_id: int) -> list:
    """Historique normalisation pour chaque annee d'une EFA."""
    rows = (
        db.query(TertiaireEfaConsumption)
        .filter(TertiaireEfaConsumption.efa_id == efa_id)
        .order_by(TertiaireEfaConsumption.year)
        .all()
    )
    return [
        {
            "year": r.year,
            "raw_kwh": r.kwh_total,
            "normalized_kwh": r.normalized_kwh_total,
            "is_normalized": r.is_normalized,
            "method": r.normalization_method,
            "confidence": r.normalization_confidence,
            "dju_heating": r.dju_heating,
            "dju_cooling": r.dju_cooling,
            "dju_reference": r.dju_reference,
            "weather_source": r.weather_data_source,
            "normalized_at": r.normalized_at.isoformat() if r.normalized_at else None,
        }
        for r in rows
    ]
