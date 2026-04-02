"""
Service DJU (Degrés-Jours Unifiés) via Open-Meteo API.

Open-Meteo : gratuit, sans clé API, 10k req/jour.
- Forecast API : 7 derniers jours + 7 prochains
- Archive API : historique depuis 1940

Méthode COSTIC (standard français tertiaire) :
  DJU_chauffage(jour) = max(0, 18 - T_moy)
  DJU_clim(jour) = max(0, T_moy - 18)

Base de référence : 18°C.

Fallback synthétique : si Open-Meteo inaccessible (réseau container),
génère un profil sinusoïdal type Paris (~2400 DJU chauf/an).
"""

import math
import os
import logging
from datetime import date, timedelta

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
DJU_BASE_TEMP = 18.0  # °C — standard COSTIC France
TIMEOUT = 10

DEMO_MODE = os.environ.get("PROMEOS_DEMO_MODE", "false").lower() == "true"


# ── Coordonnées par défaut pour les grandes villes françaises ──────────────

CITY_COORDS: dict[str, tuple[float, float]] = {
    "75": (48.8566, 2.3522),  # Paris
    "69": (45.7640, 4.8357),  # Lyon
    "13": (43.2965, 5.3698),  # Marseille
    "06": (43.7102, 7.2620),  # Nice
    "31": (43.6047, 1.4442),  # Toulouse
    "33": (44.8378, -0.5792),  # Bordeaux
    "67": (48.5734, 7.7521),  # Strasbourg
    "59": (50.6292, 3.0573),  # Lille
    "44": (47.2184, -1.5536),  # Nantes
    "34": (43.6108, 3.8767),  # Montpellier
}


def get_site_coordinates(site) -> tuple[float, float] | None:
    """
    Récupère les coordonnées GPS d'un site.
    Cascade : lat/lon en DB → code postal → None.
    """
    lat = getattr(site, "latitude", None)
    lon = getattr(site, "longitude", None)

    if lat is not None and lon is not None:
        return (float(lat), float(lon))

    # Fallback code postal
    cp = getattr(site, "code_postal", None) or ""
    dept = cp[:2] if len(cp) >= 2 else ""
    if dept in CITY_COORDS:
        return CITY_COORDS[dept]

    return None


# ── API Open-Meteo ─────────────────────────────────────────────────────────


def get_daily_temperatures(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
    synthetic_fallback: bool | None = None,
) -> list[dict]:
    """
    Récupère les températures moyennes quotidiennes depuis Open-Meteo.
    Retourne : [{"date": "2025-01-15", "temp_mean": 5.2}, ...]
    Retourne liste vide si API indisponible et pas de fallback.
    """
    if not latitude or not longitude:
        return []

    if synthetic_fallback is None:
        synthetic_fallback = DEMO_MODE

    try:
        today = date.today()
        results = []

        # Archive (si start_date < today - 7 jours)
        archive_end = min(end_date, today - timedelta(days=8))
        if start_date <= archive_end:
            archive_data = _fetch_open_meteo(OPEN_METEO_ARCHIVE, latitude, longitude, start_date, archive_end)
            results.extend(archive_data)

        # Forecast (7 derniers jours + futur)
        forecast_start = max(start_date, today - timedelta(days=7))
        if forecast_start <= end_date:
            forecast_data = _fetch_open_meteo(
                OPEN_METEO_FORECAST,
                latitude,
                longitude,
                forecast_start,
                min(end_date, today),
            )
            results.extend(forecast_data)

        if results:
            return results

    except Exception as e:
        logger.warning(f"Open-Meteo unavailable: {e}")

    # Fallback synthétique
    if synthetic_fallback:
        logger.info("Utilisation du profil température synthétique (démo)")
        return _generate_synthetic_temperatures(latitude, start_date, end_date)

    return []


def _fetch_open_meteo(
    base_url: str,
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> list[dict]:
    """Appel Open-Meteo et parse la réponse."""
    resp = httpx.get(
        base_url,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": "temperature_2m_mean",
            "timezone": "Europe/Paris",
        },
        timeout=TIMEOUT,
    )

    if resp.status_code != 200:
        return []

    data = resp.json()
    dates = data.get("daily", {}).get("time", [])
    temps = data.get("daily", {}).get("temperature_2m_mean", [])

    return [{"date": d, "temp_mean": t} for d, t in zip(dates, temps) if t is not None]


# ── Profil synthétique ─────────────────────────────────────────────────────


def _generate_synthetic_temperatures(
    latitude: float,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """
    Génère un profil température sinusoïdal réaliste.
    T_moy(jour) = T_annuelle_moy + amplitude × sin(2π × (jour_année - 100) / 365)

    Calibré pour la France métropolitaine :
    - Paris (48.8°N) : moy 12°C, amplitude 9°C → 3°C janv, 21°C juil
    - Marseille (43.3°N) : moy 15°C, amplitude 8°C → 7°C janv, 23°C juil
    """
    # Ajuster selon la latitude (plus au sud = plus chaud, moins d'amplitude)
    t_mean_annual = 12.0 + (48.8 - latitude) * 0.5  # ~12°C à Paris, ~15°C à Marseille
    amplitude = 9.0 - (48.8 - latitude) * 0.2  # ~9°C à Paris, ~8°C à Marseille

    results = []
    current = start_date
    while current <= end_date:
        day_of_year = current.timetuple().tm_yday
        # Sinusoïde : minimum ~15 janvier (jour 15), maximum ~15 juillet (jour 196)
        t = t_mean_annual + amplitude * math.sin(2 * math.pi * (day_of_year - 100) / 365)
        # Ajout bruit léger déterministe (basé sur le jour)
        noise = math.sin(day_of_year * 7.3) * 1.5
        results.append(
            {
                "date": current.isoformat(),
                "temp_mean": round(t + noise, 1),
            }
        )
        current += timedelta(days=1)

    return results


# ── Calcul DJU ─────────────────────────────────────────────────────────────


def compute_dju(temperatures: list[dict]) -> list[dict]:
    """
    Calcule les DJU chauffage et climatisation depuis les températures.
    Méthode COSTIC : base 18°C.
    """
    return [
        {
            **t,
            "dju_chauf": round(max(0, DJU_BASE_TEMP - t["temp_mean"]), 2),
            "dju_clim": round(max(0, t["temp_mean"] - DJU_BASE_TEMP), 2),
        }
        for t in temperatures
    ]
