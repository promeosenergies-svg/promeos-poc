"""
Service de prevision energetique J+1 a J+7.

Methode : signature thermique (IPMVP-like) + temperature prevue + ajustement occupation.

Pipeline :
1. Charger la signature thermique du site (run_signature sur 365j passes)
2. Charger les temperatures prevues J+1 a J+7 (Open-Meteo forecast)
3. Calculer : forecast(j) = base_kwh + a_heating*max(0, Tb-T(j)) + b_cooling*max(0, T(j)-Tc)
4. Ajuster par facteur jour ouvré / weekend / férié
5. Retourner prevision + intervalle de confiance

Sources :
- IPMVP option D (methode signature inverse)
- ISO 52000 (signature energetique)
- Open-Meteo Forecast API (7 jours gratuit)
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class DayForecast:
    date: str
    predicted_kwh: float
    temperature_forecast: float
    is_business_day: bool
    confidence_low: float
    confidence_high: float


@dataclass
class ForecastResult:
    site_id: int
    site_nom: str
    archetype_code: str
    forecast_days: list[DayForecast]
    total_kwh_7d: float
    avg_kwh_day: float
    signature: Optional[dict] = None
    method: str = "thermal_signature_forecast"
    confidence_global: str = "medium"
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


# Facteurs d'ajustement jour ouvré vs weekend
WEEKEND_FACTOR = {
    "BUREAU_STANDARD": 0.25,
    "ENSEIGNEMENT": 0.15,
    "ENSEIGNEMENT_SUP": 0.40,
    "HOTEL_HEBERGEMENT": 0.85,
    "COMMERCE_ALIMENTAIRE": 0.90,
    "RESTAURANT": 0.70,
    "SANTE": 0.95,
    "DATA_CENTER": 1.0,
    "INDUSTRIE_LEGERE": 0.30,
    "INDUSTRIE_LOURDE": 0.50,
    "LOGISTIQUE_SEC": 0.20,
    "LOGISTIQUE_FRIGO": 0.85,
    "SPORT_LOISIR": 0.60,
    "COLLECTIVITE": 0.20,
    "COPROPRIETE": 0.80,
    "DEFAULT": 0.40,
}

# Jours feries France 2026 (fixes + Paques/Ascension/Pentecote)
JOURS_FERIES_2026 = {
    date(2026, 1, 1),
    date(2026, 4, 6),
    date(2026, 4, 7),  # Nouvel An, Lundi Paques
    date(2026, 5, 1),
    date(2026, 5, 8),
    date(2026, 5, 14),  # 1er Mai, Victoire, Ascension
    date(2026, 5, 25),  # Lundi Pentecote
    date(2026, 7, 14),
    date(2026, 8, 15),  # 14 Juillet, Assomption
    date(2026, 11, 1),
    date(2026, 11, 11),
    date(2026, 12, 25),  # Toussaint, Armistice, Noel
}


def forecast_site(
    db: Session,
    site_id: int,
    horizon_days: int = 7,
) -> ForecastResult:
    """
    Prevision energetique J+1 a J+horizon pour un site.

    Pipeline :
    1. Signature thermique (365j passes)
    2. Temperature prevue (Open-Meteo)
    3. Forecast = base + DJU chaud/froid + ajustement occupation
    """
    from models.site import Site
    from models.energy_models import Meter
    from services.flex.archetype_resolver import resolve_archetype

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} non trouve")

    meter = db.query(Meter).filter(Meter.site_id == site_id, Meter.is_active == True).first()
    archetype = resolve_archetype(db, site, meter)

    # 1. Signature thermique
    sig = _get_or_compute_signature(db, site, meter)
    if not sig or sig.get("error"):
        return _fallback_forecast(site_id, site.nom, archetype, horizon_days)

    # 2. Temperatures prevues
    lat = site.latitude or 48.8566
    lon = site.longitude or 2.3522
    forecast_temps = _get_forecast_temperatures(lat, lon, horizon_days)
    if not forecast_temps:
        return _fallback_forecast(site_id, site.nom, archetype, horizon_days, sig)

    # 3. Calcul prevision par jour
    base = sig.get("base_kwh", 0)
    a_heat = sig.get("a_heating", 0) or 0
    b_cool = sig.get("b_cooling", 0) or 0
    tb = sig.get("Tb", 15.0) or 15.0
    tc = sig.get("Tc", 22.0) or 22.0
    r2 = sig.get("r_squared", 0) or sig.get("r2", 0) or 0

    # Residual std pour intervalle de confiance (~15% si R2 bon, ~30% sinon)
    residual_pct = 0.12 if r2 > 0.7 else 0.20 if r2 > 0.4 else 0.30

    weekend_factor = WEEKEND_FACTOR.get(archetype, WEEKEND_FACTOR["DEFAULT"])
    today = date.today()

    forecasts = []
    for d in range(1, horizon_days + 1):
        forecast_date = today + timedelta(days=d)
        temp = forecast_temps.get(forecast_date.isoformat())
        if temp is None:
            continue

        # Modele thermique
        heating = max(0, tb - temp)
        cooling = max(0, temp - tc)
        kwh_base = base + a_heat * heating + b_cool * cooling

        # Ajustement occupation
        is_biz = _is_business_day(forecast_date)
        if not is_biz:
            kwh_adjusted = kwh_base * weekend_factor
        else:
            kwh_adjusted = kwh_base

        # Intervalle de confiance
        margin = kwh_adjusted * residual_pct
        confidence_low = max(0, kwh_adjusted - margin)
        confidence_high = kwh_adjusted + margin

        forecasts.append(
            DayForecast(
                date=forecast_date.isoformat(),
                predicted_kwh=round(kwh_adjusted, 1),
                temperature_forecast=round(temp, 1),
                is_business_day=is_biz,
                confidence_low=round(confidence_low, 1),
                confidence_high=round(confidence_high, 1),
            )
        )

    total_7d = sum(f.predicted_kwh for f in forecasts)
    avg_day = total_7d / max(len(forecasts), 1)

    confidence = "high" if r2 > 0.6 else "medium" if r2 > 0.3 else "low"

    return ForecastResult(
        site_id=site_id,
        site_nom=site.nom,
        archetype_code=archetype,
        forecast_days=forecasts,
        total_kwh_7d=round(total_7d, 1),
        avg_kwh_day=round(avg_day, 1),
        signature={
            "base_kwh": round(base, 1),
            "a_heating": round(a_heat, 2),
            "b_cooling": round(b_cool, 2),
            "Tb": tb,
            "Tc": tc,
            "r2": round(r2, 3),
        },
        confidence_global=confidence,
    )


# === Helpers ===


def _get_or_compute_signature(db: Session, site, meter) -> Optional[dict]:
    """Calcule ou recupere la signature thermique."""
    if not meter:
        return None
    try:
        from models.power import PowerReading
        from services.weather_dju_service import get_daily_temperatures
        from services.ems.signature_service import run_signature

        today = date.today()
        start = today - timedelta(days=365)

        # Lectures CDC 365j
        readings = (
            db.query(PowerReading)
            .filter(
                PowerReading.meter_id == meter.id,
                PowerReading.sens == "CONS",
                PowerReading.ts_debut >= datetime.combine(start, datetime.min.time()),
                PowerReading.ts_debut < datetime.combine(today, datetime.min.time()),
            )
            .all()
        )
        if len(readings) < 30 * 48:
            return None

        # Agreger en kWh journalier
        daily_kwh_map: dict[str, float] = defaultdict(float)
        for r in readings:
            d = r.ts_debut.strftime("%Y-%m-%d")
            pas_h = (r.pas_minutes or 30) / 60.0
            daily_kwh_map[d] += (r.P_active_kw or 0) * pas_h

        # Temperatures
        lat = site.latitude or 48.8566
        lon = site.longitude or 2.3522
        temps = get_daily_temperatures(lat, lon, start, today)
        if not temps or len(temps) < 30:
            return None

        temp_by_date = {t["date"]: t["temp_mean"] for t in temps}
        common = sorted(set(daily_kwh_map.keys()) & set(temp_by_date.keys()))
        if len(common) < 30:
            return None

        daily_kwh = [daily_kwh_map[d] for d in common]
        daily_temp = [temp_by_date[d] for d in common]

        return run_signature(daily_kwh, daily_temp)

    except Exception as exc:
        logger.debug("signature compute failed: %s", exc)
        return None


def _get_forecast_temperatures(lat: float, lon: float, horizon_days: int) -> dict[str, float]:
    """Recupere les temperatures prevues J+1 a J+horizon via Open-Meteo."""
    try:
        from services.weather_dju_service import get_daily_temperatures

        today = date.today()
        end = today + timedelta(days=horizon_days)
        temps = get_daily_temperatures(lat, lon, today, end)
        if not temps:
            return {}
        return {t["date"]: t["temp_mean"] for t in temps}

    except Exception as exc:
        logger.debug("forecast temperatures failed: %s", exc)
        return {}


def _is_business_day(d: date) -> bool:
    """Jour ouvre en France (hors weekends et feries)."""
    if d.weekday() >= 5:
        return False
    if d in JOURS_FERIES_2026:
        return False
    return True


def _fallback_forecast(
    site_id: int,
    site_nom: str,
    archetype: str,
    horizon_days: int,
    sig: Optional[dict] = None,
) -> ForecastResult:
    """Fallback quand pas de signature ou pas de meteo prevue."""
    return ForecastResult(
        site_id=site_id,
        site_nom=site_nom,
        archetype_code=archetype,
        forecast_days=[],
        total_kwh_7d=0,
        avg_kwh_day=0,
        signature=sig,
        method="no_data",
        confidence_global="none",
    )
