"""
Moteur de decomposition CDC -> usages.

Decompose la courbe de charge d'un site en usages canoniques via 3 couches :

  Couche 1 — Thermique (DJU)
    Regression E = base + a*DJU_chauf + b*DJU_clim → isole CVC_HVAC
    Reutilise services/ems/signature_service.run_signature()

  Couche 2 — Temporelle (occupation)
    Analyse CDC 30min × SiteOperatingSchedule → extrait :
    - Baseload nuit (2h-5h weekdays) = charges 24/7 (froid, IT, securite)
    - Increment business hours = eclairage + bureautique + occupation
    - Delta weekend vs semaine = charges occupation-dependantes

  Couche 3 — Archetype (residuel)
    Repartition du residu via usage_breakdown de archetypes_energy_v1.json
    calibre CEREN/ADEME (source sectorielle)

Sources :
  - ADEME "Chiffres cles du batiment energie climat"
  - CEREN "Donnees statistiques du tertiaire" (repartition par poste usage)
  - ISO 52000 (methode signature energetique)
  - ASHRAE Inverse Modeling Toolkit (regression change-point)
"""

import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Seuils temporels pour extraction baseload
NIGHT_START_HOUR = 2
NIGHT_END_HOUR = 5
MIN_READINGS_FOR_DISAGG = 30 * 48  # ~30 jours × 48 pas/jour (30 min)


@dataclass
class UsageShare:
    """Part d'un usage dans la consommation totale du site."""

    code: str
    label: str
    kwh: float
    pct: float
    method: str  # dju_regression | temporal_night_base | temporal_business | archetype_residual
    confidence: str  # high | medium | low


@dataclass
class DisaggregationResult:
    site_id: int
    period_start: str
    period_end: str
    total_kwh: float
    archetype_code: str
    usages: list[UsageShare]
    thermal_signature: Optional[dict] = None
    temporal_profile: Optional[dict] = None
    residual_kwh: float = 0.0
    residual_pct: float = 0.0
    n_readings: int = 0
    confidence_global: str = "low"
    method: str = "3_layer_decomposition"


# Labels par code usage
_USAGE_LABELS = {
    "CVC_HVAC": "CVC (chauffage/ventilation/climatisation)",
    "ECLAIRAGE": "Eclairage",
    "ECS": "Eau chaude sanitaire",
    "FROID_COMMERCIAL": "Froid commercial",
    "FROID_INDUSTRIEL": "Froid industriel",
    "IT_BUREAUTIQUE": "IT / bureautique",
    "IRVE": "Recharge VE",
    "AIR_COMPRIME": "Air comprime",
    "POMPES": "Pompes",
    "DATA_CENTER": "Salles informatiques",
    "PROCESS_BATCH": "Process batch",
    "SECURITE_VEILLE": "Securite / veille",
    "AUTRES": "Autres usages",
}


def disaggregate_site(
    db: Session,
    site_id: int,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
) -> DisaggregationResult:
    """
    Decompose la CDC d'un site en usages via 3 couches.

    Args:
        db: session SQLAlchemy
        site_id: ID du site
        date_debut/date_fin: periode (defaut : 365j glissants)

    Returns:
        DisaggregationResult avec la liste des usages detectes,
        leur part (kWh, %), la methode de detection et le niveau de confiance.
    """
    from models.site import Site
    from models.energy_models import Meter
    from services.flex.archetype_resolver import resolve_archetype

    if date_fin is None:
        date_fin = date.today()
    if date_debut is None:
        date_debut = date_fin - timedelta(days=365)

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} non trouve")

    meter = db.query(Meter).filter(Meter.site_id == site_id, Meter.is_active == True).first()
    archetype = resolve_archetype(db, site, meter)

    # Lire les PowerReadings 30min
    readings = _fetch_readings(db, meter, date_debut, date_fin) if meter else []
    n_readings = len(readings)

    if n_readings < MIN_READINGS_FOR_DISAGG:
        return _fallback_archetype_only(site_id, archetype, date_debut, date_fin, site, n_readings)

    total_kwh = _total_kwh(readings)
    if total_kwh <= 0:
        return _fallback_archetype_only(site_id, archetype, date_debut, date_fin, site, n_readings)

    usages: dict[str, float] = {}
    methods: dict[str, str] = {}
    confidences: dict[str, str] = {}
    thermal_sig = None
    temporal_prof = None

    # === COUCHE 1 : Thermique (DJU) ===
    cvc_kwh, sig = _extract_thermal(db, site, readings, date_debut, date_fin)
    thermal_sig = sig
    if cvc_kwh > 0:
        usages["CVC_HVAC"] = cvc_kwh
        methods["CVC_HVAC"] = "dju_regression"
        confidences["CVC_HVAC"] = "high" if sig and sig.get("r2", 0) >= 0.6 else "medium"

    # === COUCHE 2 : Temporelle (occupation) ===
    schedule = _fetch_schedule(db, site_id)
    baseload_kwh, business_increment_kwh, temporal = _extract_temporal(
        readings,
        schedule,
        total_kwh,
        cvc_kwh,
    )
    temporal_prof = temporal

    if baseload_kwh > 0:
        # Baseload nuit = froid + IT + securite/veille
        base_usages = _split_baseload_by_archetype(baseload_kwh, archetype)
        for code, kwh in base_usages.items():
            usages[code] = usages.get(code, 0) + kwh
            methods.setdefault(code, "temporal_night_base")
            confidences.setdefault(code, "medium")

    if business_increment_kwh > 0:
        # Business hours increment = eclairage + IT bureautique
        biz_usages = _split_business_increment(business_increment_kwh, archetype)
        for code, kwh in biz_usages.items():
            usages[code] = usages.get(code, 0) + kwh
            methods.setdefault(code, "temporal_business")
            confidences.setdefault(code, "medium")

    # === COUCHE 3 : Archetype residuel ===
    attributed_kwh = sum(usages.values())
    residual_kwh = max(0, total_kwh - attributed_kwh)

    if residual_kwh > total_kwh * 0.05:
        residual_usages = _split_residual_by_archetype(residual_kwh, archetype, set(usages.keys()))
        for code, kwh in residual_usages.items():
            usages[code] = usages.get(code, 0) + kwh
            methods.setdefault(code, "archetype_residual")
            confidences.setdefault(code, "low")
        residual_kwh = max(0, total_kwh - sum(usages.values()))

    # Normaliser pour que la somme = total_kwh exact
    usages = _normalize_to_total(usages, total_kwh)

    usage_list = [
        UsageShare(
            code=code,
            label=_USAGE_LABELS.get(code, code),
            kwh=round(kwh, 1),
            pct=round(kwh / total_kwh * 100, 1) if total_kwh > 0 else 0,
            method=methods.get(code, "archetype_residual"),
            confidence=confidences.get(code, "low"),
        )
        for code, kwh in sorted(usages.items(), key=lambda x: -x[1])
    ]

    n_high = sum(1 for u in usage_list if u.confidence == "high")
    n_medium = sum(1 for u in usage_list if u.confidence == "medium")
    if n_high >= 1 and n_medium >= 1:
        confidence_global = "medium"
    elif n_high >= 2:
        confidence_global = "high"
    else:
        confidence_global = "low"

    return DisaggregationResult(
        site_id=site_id,
        period_start=date_debut.isoformat(),
        period_end=date_fin.isoformat(),
        total_kwh=round(total_kwh, 1),
        archetype_code=archetype,
        usages=usage_list,
        thermal_signature=thermal_sig,
        temporal_profile=temporal_prof,
        residual_kwh=round(residual_kwh, 1),
        residual_pct=round(residual_kwh / total_kwh * 100, 1) if total_kwh > 0 else 0,
        n_readings=n_readings,
        confidence_global=confidence_global,
    )


# === Couche 1 : Extraction thermique ===


def _extract_thermal(
    db: Session,
    site,
    readings: list,
    date_debut: date,
    date_fin: date,
) -> tuple[float, Optional[dict]]:
    """Extrait la composante CVC via regression DJU."""
    try:
        from services.weather_dju_service import get_daily_temperatures
        from services.ems.signature_service import run_signature

        lat = site.latitude or 48.8566  # Paris fallback
        lon = site.longitude or 2.3522

        temps = get_daily_temperatures(lat, lon, date_debut, date_fin)
        if not temps or len(temps) < 30:
            return 0.0, None

        temp_by_date = {t["date"]: t["temp_mean"] for t in temps}

        # Agreger CDC 30min -> kWh journalier
        daily_kwh_map: dict[str, float] = defaultdict(float)
        for r in readings:
            d = r.ts_debut.strftime("%Y-%m-%d")
            pas_h = (r.pas_minutes or 30) / 60.0
            daily_kwh_map[d] += (r.P_active_kw or 0) * pas_h

        # Aligner dates communes
        common_dates = sorted(set(daily_kwh_map.keys()) & set(temp_by_date.keys()))
        if len(common_dates) < 30:
            return 0.0, None

        daily_kwh = [daily_kwh_map[d] for d in common_dates]
        daily_temp = [temp_by_date[d] for d in common_dates]

        sig = run_signature(daily_kwh, daily_temp)
        if sig.get("error"):
            return 0.0, sig

        # CVC = (total - base * n_jours) = composante thermosensible
        base_daily = sig.get("base_kwh", 0)
        total_all_days = sum(daily_kwh)
        base_all_days = base_daily * len(common_dates)
        cvc_kwh = max(0, total_all_days - base_all_days)

        return cvc_kwh, sig

    except Exception as exc:
        logger.debug("thermal extraction failed for site %s: %s", site.id, exc)
        return 0.0, None


# === Couche 2 : Extraction temporelle ===


def _extract_temporal(
    readings: list,
    schedule: Optional[dict],
    total_kwh: float,
    cvc_kwh_already: float,
) -> tuple[float, float, dict]:
    """
    Extrait le baseload nuit et l'increment business hours depuis la CDC.

    Returns:
        (baseload_kwh_annualise, business_increment_kwh, temporal_profile_dict)
    """
    open_hour = int((schedule or {}).get("open_time", "08:00").split(":")[0])
    close_hour = int((schedule or {}).get("close_time", "19:00").split(":")[0])
    open_days_str = (schedule or {}).get("open_days", "0,1,2,3,4")
    open_days = set(int(d) for d in open_days_str.split(",") if d.strip().isdigit())

    # Classifier chaque reading
    night_kw = []  # 2h-5h weekdays (baseload absolu)
    biz_kw = []  # heures ouvertes jours ouvres
    off_kw = []  # heures fermees (hors nuit profonde)

    for r in readings:
        h = r.ts_debut.hour
        dow = r.ts_debut.weekday()
        kw = r.P_active_kw or 0

        if NIGHT_START_HOUR <= h < NIGHT_END_HOUR and dow in open_days:
            night_kw.append(kw)
        elif dow in open_days and open_hour <= h < close_hour:
            biz_kw.append(kw)
        else:
            off_kw.append(kw)

    # Baseload = median de la nuit profonde (plus robuste que Q5)
    baseload_kw = _median(night_kw) if night_kw else 0
    biz_mean_kw = _mean(biz_kw) if biz_kw else 0
    off_mean_kw = _mean(off_kw) if off_kw else 0

    # Baseload annualise (kW * 8760h)
    baseload_kwh = baseload_kw * 8760 if baseload_kw > 0 else 0

    # Business increment = (mean biz - baseload) * heures ouvertes/an
    biz_hours_per_day = max(close_hour - open_hour, 1)
    biz_days_per_year = len(open_days) * 52
    biz_increment_kw = max(0, biz_mean_kw - baseload_kw)
    # Retrancher la CVC deja attribuee (couche 1)
    biz_hours_annual = biz_hours_per_day * biz_days_per_year
    business_increment_kwh = max(0, biz_increment_kw * biz_hours_annual - cvc_kwh_already * 0.3)

    # Eviter de depasser le total restant
    remaining = total_kwh - cvc_kwh_already
    baseload_kwh = min(baseload_kwh, remaining * 0.6)
    business_increment_kwh = min(business_increment_kwh, remaining - baseload_kwh)

    temporal = {
        "baseload_kw": round(baseload_kw, 1),
        "biz_mean_kw": round(biz_mean_kw, 1),
        "off_mean_kw": round(off_mean_kw, 1),
        "biz_increment_kw": round(biz_increment_kw, 1),
        "n_night_readings": len(night_kw),
        "n_biz_readings": len(biz_kw),
    }

    return round(baseload_kwh, 1), round(business_increment_kwh, 1), temporal


# === Couche 3 : Attribution residuelle par archetype ===

# Mapping archetype → repartition du baseload nuit
_BASELOAD_SPLIT = {
    "BUREAU_STANDARD": {"IT_BUREAUTIQUE": 0.50, "SECURITE_VEILLE": 0.30, "ECS": 0.20},
    "HOTEL_HEBERGEMENT": {"ECS": 0.40, "FROID_COMMERCIAL": 0.30, "SECURITE_VEILLE": 0.30},
    "COMMERCE_ALIMENTAIRE": {"FROID_COMMERCIAL": 0.70, "SECURITE_VEILLE": 0.20, "ECS": 0.10},
    "RESTAURANT": {"FROID_COMMERCIAL": 0.60, "ECS": 0.30, "SECURITE_VEILLE": 0.10},
    "LOGISTIQUE_FRIGO": {"FROID_INDUSTRIEL": 0.80, "SECURITE_VEILLE": 0.15, "ECS": 0.05},
    "DATA_CENTER": {"DATA_CENTER": 0.85, "SECURITE_VEILLE": 0.15},
    "INDUSTRIE_LEGERE": {"AIR_COMPRIME": 0.30, "POMPES": 0.30, "SECURITE_VEILLE": 0.25, "ECS": 0.15},
    "INDUSTRIE_LOURDE": {"POMPES": 0.35, "AIR_COMPRIME": 0.30, "SECURITE_VEILLE": 0.25, "ECS": 0.10},
    "SANTE": {"ECS": 0.40, "IT_BUREAUTIQUE": 0.30, "SECURITE_VEILLE": 0.30},
    "ENSEIGNEMENT": {"SECURITE_VEILLE": 0.40, "IT_BUREAUTIQUE": 0.30, "ECS": 0.30},
    "ENSEIGNEMENT_SUP": {"DATA_CENTER": 0.40, "IT_BUREAUTIQUE": 0.30, "ECS": 0.20, "SECURITE_VEILLE": 0.10},
    "LOGISTIQUE_SEC": {"SECURITE_VEILLE": 0.50, "AIR_COMPRIME": 0.30, "ECS": 0.20},
    "SPORT_LOISIR": {"ECS": 0.50, "POMPES": 0.30, "SECURITE_VEILLE": 0.20},
    "COLLECTIVITE": {"IT_BUREAUTIQUE": 0.40, "SECURITE_VEILLE": 0.30, "ECS": 0.30},
    "COPROPRIETE": {"ECS": 0.50, "SECURITE_VEILLE": 0.30, "ECLAIRAGE": 0.20},
    "DEFAULT": {"IT_BUREAUTIQUE": 0.40, "SECURITE_VEILLE": 0.30, "ECS": 0.30},
}

# Mapping archetype → repartition de l'increment business hours
_BUSINESS_INCREMENT_SPLIT = {
    "BUREAU_STANDARD": {"ECLAIRAGE": 0.55, "IT_BUREAUTIQUE": 0.35, "AUTRES": 0.10},
    "HOTEL_HEBERGEMENT": {"ECLAIRAGE": 0.45, "ECS": 0.30, "AUTRES": 0.25},
    "COMMERCE_ALIMENTAIRE": {"ECLAIRAGE": 0.60, "AUTRES": 0.40},
    "RESTAURANT": {"ECLAIRAGE": 0.40, "ECS": 0.35, "AUTRES": 0.25},
    "DATA_CENTER": {"DATA_CENTER": 0.70, "ECLAIRAGE": 0.20, "AUTRES": 0.10},
    "INDUSTRIE_LEGERE": {"PROCESS_BATCH": 0.50, "AIR_COMPRIME": 0.25, "ECLAIRAGE": 0.15, "AUTRES": 0.10},
    "INDUSTRIE_LOURDE": {"PROCESS_CONTINU": 0.60, "POMPES": 0.20, "ECLAIRAGE": 0.10, "AUTRES": 0.10},
    "SANTE": {"ECLAIRAGE": 0.40, "IT_BUREAUTIQUE": 0.30, "ECS": 0.20, "AUTRES": 0.10},
    "ENSEIGNEMENT": {"ECLAIRAGE": 0.55, "IT_BUREAUTIQUE": 0.30, "AUTRES": 0.15},
    "ENSEIGNEMENT_SUP": {"ECLAIRAGE": 0.40, "IT_BUREAUTIQUE": 0.30, "DATA_CENTER": 0.20, "AUTRES": 0.10},
    "LOGISTIQUE_SEC": {"ECLAIRAGE": 0.50, "AIR_COMPRIME": 0.30, "AUTRES": 0.20},
    "LOGISTIQUE_FRIGO": {"ECLAIRAGE": 0.30, "AUTRES": 0.70},
    "SPORT_LOISIR": {"ECLAIRAGE": 0.40, "POMPES": 0.30, "ECS": 0.20, "AUTRES": 0.10},
    "COLLECTIVITE": {"ECLAIRAGE": 0.50, "IT_BUREAUTIQUE": 0.30, "AUTRES": 0.20},
    "COPROPRIETE": {"ECLAIRAGE": 0.60, "AUTRES": 0.40},
    "DEFAULT": {"ECLAIRAGE": 0.50, "IT_BUREAUTIQUE": 0.30, "AUTRES": 0.20},
}

# Repartition du residu non explique par couche 1+2
_RESIDUAL_SPLIT = {
    "BUREAU_STANDARD": {"IRVE": 0.30, "AUTRES": 0.70},
    "HOTEL_HEBERGEMENT": {"IRVE": 0.20, "AUTRES": 0.80},
    "COMMERCE_ALIMENTAIRE": {"IRVE": 0.20, "AUTRES": 0.80},
    "DATA_CENTER": {"AUTRES": 1.0},
    "INDUSTRIE_LEGERE": {"POMPES": 0.40, "AUTRES": 0.60},
    "INDUSTRIE_LOURDE": {"AUTRES": 1.0},
    "DEFAULT": {"AUTRES": 1.0},
}


def _split_baseload_by_archetype(baseload_kwh: float, archetype: str) -> dict[str, float]:
    splits = _BASELOAD_SPLIT.get(archetype, _BASELOAD_SPLIT["DEFAULT"])
    return {code: round(baseload_kwh * pct, 1) for code, pct in splits.items()}


def _split_business_increment(increment_kwh: float, archetype: str) -> dict[str, float]:
    splits = _BUSINESS_INCREMENT_SPLIT.get(archetype, _BUSINESS_INCREMENT_SPLIT["DEFAULT"])
    return {code: round(increment_kwh * pct, 1) for code, pct in splits.items()}


def _split_residual_by_archetype(
    residual_kwh: float,
    archetype: str,
    already_attributed: set[str],
) -> dict[str, float]:
    splits = _RESIDUAL_SPLIT.get(archetype, _RESIDUAL_SPLIT["DEFAULT"])
    return {code: round(residual_kwh * pct, 1) for code, pct in splits.items()}


def _normalize_to_total(usages: dict[str, float], total_kwh: float) -> dict[str, float]:
    """Normalise pour que sum(usages) == total_kwh (evite les arrondis)."""
    current = sum(usages.values())
    if current <= 0 or total_kwh <= 0:
        return usages
    factor = total_kwh / current
    return {k: round(v * factor, 1) for k, v in usages.items()}


# === Helpers I/O ===


def _fetch_readings(db: Session, meter, date_debut: date, date_fin: date) -> list:
    from models.power import PowerReading

    return (
        db.query(PowerReading)
        .filter(
            PowerReading.meter_id == meter.id,
            PowerReading.sens == "CONS",
            PowerReading.ts_debut >= datetime.combine(date_debut, datetime.min.time()),
            PowerReading.ts_debut < datetime.combine(date_fin, datetime.min.time()),
        )
        .order_by(PowerReading.ts_debut)
        .all()
    )


def _fetch_schedule(db: Session, site_id: int) -> Optional[dict]:
    try:
        from models.site_operating_schedule import SiteOperatingSchedule

        sched = db.query(SiteOperatingSchedule).filter_by(site_id=site_id).first()
        if sched:
            return {
                "open_time": sched.open_time or "08:00",
                "close_time": sched.close_time or "19:00",
                "open_days": sched.open_days or "0,1,2,3,4",
                "is_24_7": sched.is_24_7 or False,
            }
    except Exception:
        pass
    return None


def _total_kwh(readings: list) -> float:
    return sum((r.P_active_kw or 0) * ((r.pas_minutes or 30) / 60.0) for r in readings)


def _median(values: list[float]) -> float:
    if not values:
        return 0
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n // 2 - 1] + s[n // 2]) / 2
    return s[n // 2]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0


def _fallback_archetype_only(
    site_id: int,
    archetype: str,
    date_debut: date,
    date_fin: date,
    site,
    n_readings: int,
) -> DisaggregationResult:
    """Fallback quand pas assez de CDC : estimation pure archetype."""
    total_kwh = getattr(site, "annual_kwh_total", None) or 0
    if total_kwh <= 0:
        return DisaggregationResult(
            site_id=site_id,
            period_start=date_debut.isoformat(),
            period_end=date_fin.isoformat(),
            total_kwh=0,
            archetype_code=archetype,
            usages=[],
            n_readings=n_readings,
            confidence_global="none",
            method="no_data",
        )

    # Charger breakdown JSON si disponible
    breakdown = _load_archetype_breakdown(archetype)
    usages = []
    for code, info in breakdown.items():
        avg_pct = (info.get("pct_min", 0) + info.get("pct_max", 0)) / 2
        kwh = round(total_kwh * avg_pct / 100, 1)
        usages.append(
            UsageShare(
                code=_normalize_usage_code(code),
                label=info.get("label", code),
                kwh=kwh,
                pct=round(avg_pct, 1),
                method="archetype_only",
                confidence="low",
            )
        )

    usages.sort(key=lambda u: -u.kwh)

    return DisaggregationResult(
        site_id=site_id,
        period_start=date_debut.isoformat(),
        period_end=date_fin.isoformat(),
        total_kwh=round(total_kwh, 1),
        archetype_code=archetype,
        usages=usages,
        n_readings=n_readings,
        confidence_global="low",
        method="archetype_only",
    )


def _load_archetype_breakdown(archetype_code: str) -> dict:
    """Charge le usage_breakdown depuis archetypes_energy_v1.json."""
    try:
        # __file__ = backend/services/analytics/usage_disaggregation.py -> 4 niveaux up = project root
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        path = os.path.join(base, "docs", "base_documentaire", "naf_archetype_mapping", "archetypes_energy_v1.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for arch in data.get("archetypes", []):
            if arch.get("code") == archetype_code:
                return arch.get("usage_breakdown", {})
    except Exception as exc:
        logger.debug("archetype breakdown load failed: %s", exc)
    return {}


# Normalisation des codes usage du JSON vers les codes canoniques flex
_JSON_TO_CANONICAL = {
    "HVAC": "CVC_HVAC",
    "Eclairage": "ECLAIRAGE",
    "IT": "IT_BUREAUTIQUE",
    "ECS": "ECS",
    "Autres": "AUTRES",
    "Froid": "FROID_COMMERCIAL",
    "Froid alimentaire": "FROID_COMMERCIAL",
    "Froid industriel": "FROID_INDUSTRIEL",
    "Processus": "PROCESS_BATCH",
    "Air comprime": "AIR_COMPRIME",
    "IRVE": "IRVE",
}


def _normalize_usage_code(code: str) -> str:
    return _JSON_TO_CANONICAL.get(code, code)
