"""Tests pour weather_dju_service — DJU COSTIC + fallback synthétique."""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_dju_calculation():
    """DJU chauffage = max(0, 18 - T), clim = max(0, T - 18)."""
    from services.weather_dju_service import compute_dju

    temps = [
        {"date": "2025-01-15", "temp_mean": 5.0},
        {"date": "2025-07-15", "temp_mean": 28.0},
        {"date": "2025-04-15", "temp_mean": 18.0},
    ]
    result = compute_dju(temps)
    assert result[0]["dju_chauf"] == 13.0  # 18 - 5
    assert result[0]["dju_clim"] == 0
    assert result[1]["dju_chauf"] == 0
    assert result[1]["dju_clim"] == 10.0  # 28 - 18
    assert result[2]["dju_chauf"] == 0  # 18 - 18 = 0
    assert result[2]["dju_clim"] == 0


def test_city_coords_fallback():
    """Code postal → coordonnées Paris."""
    from services.weather_dju_service import get_site_coordinates

    class FakeSite:
        latitude = None
        longitude = None
        code_postal = "75001"

    coords = get_site_coordinates(FakeSite())
    assert coords is not None
    assert abs(coords[0] - 48.85) < 0.1  # Paris lat


def test_city_coords_from_db():
    """Coordonnées DB prioritaires sur code postal."""
    from services.weather_dju_service import get_site_coordinates

    class FakeSite:
        latitude = 43.60
        longitude = 1.44
        code_postal = "75001"

    coords = get_site_coordinates(FakeSite())
    assert coords == (43.60, 1.44)  # Toulouse, pas Paris


def test_city_coords_unknown_cp():
    """Code postal inconnu → None."""
    from services.weather_dju_service import get_site_coordinates

    class FakeSite:
        latitude = None
        longitude = None
        code_postal = "97400"  # La Réunion, pas dans CITY_COORDS

    assert get_site_coordinates(FakeSite()) is None


def test_synthetic_fallback():
    """Profil synthétique retourne 365 jours pour une année."""
    from services.weather_dju_service import _generate_synthetic_temperatures

    start = date(2025, 1, 1)
    end = date(2025, 12, 31)
    result = _generate_synthetic_temperatures(48.85, start, end)
    assert len(result) == 365

    # Vérifier que janvier est froid et juillet est chaud
    jan_temps = [r["temp_mean"] for r in result if r["date"].startswith("2025-01")]
    jul_temps = [r["temp_mean"] for r in result if r["date"].startswith("2025-07")]
    assert sum(jan_temps) / len(jan_temps) < 10  # moy janvier < 10°C
    assert sum(jul_temps) / len(jul_temps) > 18  # moy juillet > 18°C


def test_synthetic_dju_annual():
    """DJU annuels synthétiques Paris ≈ 2000-2800 (réf COSTIC ~2400)."""
    from services.weather_dju_service import _generate_synthetic_temperatures, compute_dju

    start = date(2025, 1, 1)
    end = date(2025, 12, 31)
    temps = _generate_synthetic_temperatures(48.85, start, end)
    djus = compute_dju(temps)

    annual_chauf = sum(d["dju_chauf"] for d in djus)
    assert 1800 < annual_chauf < 3000, f"DJU chauffage Paris = {annual_chauf}"


def test_get_daily_temperatures_synthetic():
    """get_daily_temperatures avec synthetic_fallback=True retourne des données."""
    from services.weather_dju_service import get_daily_temperatures

    start = date(2025, 1, 1)
    end = date(2025, 3, 31)
    result = get_daily_temperatures(48.85, 2.35, start, end, synthetic_fallback=True)
    assert len(result) >= 89  # ~90 jours
