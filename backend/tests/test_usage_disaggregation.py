"""
Tests du moteur de decomposition CDC -> usages.
Couvre : 3 couches (thermique + temporel + archetype), fallback, endpoint API.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock
from dataclasses import dataclass


# === Tests helpers pures ===


class TestHelpersPurs:
    def test_median_impaire(self):
        from services.analytics.usage_disaggregation import _median

        assert _median([1, 3, 5, 7, 9]) == 5

    def test_median_paire(self):
        from services.analytics.usage_disaggregation import _median

        assert _median([1, 3, 5, 7]) == 4.0

    def test_median_vide(self):
        from services.analytics.usage_disaggregation import _median

        assert _median([]) == 0

    def test_mean_basique(self):
        from services.analytics.usage_disaggregation import _mean

        assert _mean([10, 20, 30]) == 20.0

    def test_normalize_to_total(self):
        from services.analytics.usage_disaggregation import _normalize_to_total

        usages = {"A": 30.0, "B": 70.0}
        result = _normalize_to_total(usages, 200.0)
        assert abs(sum(result.values()) - 200.0) < 1.0


# === Tests Couche 3 : repartition par archetype ===


class TestArchetypeSplits:
    def test_split_baseload_bureau(self):
        from services.analytics.usage_disaggregation import _split_baseload_by_archetype

        result = _split_baseload_by_archetype(10000.0, "BUREAU_STANDARD")
        assert "IT_BUREAUTIQUE" in result
        assert "SECURITE_VEILLE" in result
        assert abs(sum(result.values()) - 10000.0) < 1.0

    def test_split_baseload_commerce_alimentaire(self):
        from services.analytics.usage_disaggregation import _split_baseload_by_archetype

        result = _split_baseload_by_archetype(5000.0, "COMMERCE_ALIMENTAIRE")
        assert result["FROID_COMMERCIAL"] >= 3000.0  # 70%
        assert abs(sum(result.values()) - 5000.0) < 1.0

    def test_split_business_increment_bureau(self):
        from services.analytics.usage_disaggregation import _split_business_increment

        result = _split_business_increment(8000.0, "BUREAU_STANDARD")
        assert "ECLAIRAGE" in result
        assert result["ECLAIRAGE"] >= 4000.0  # 55%

    def test_split_business_increment_industrie(self):
        from services.analytics.usage_disaggregation import _split_business_increment

        result = _split_business_increment(10000.0, "INDUSTRIE_LEGERE")
        assert "PROCESS_BATCH" in result
        assert result["PROCESS_BATCH"] >= 4500.0  # 50%

    def test_split_baseload_default_fallback(self):
        from services.analytics.usage_disaggregation import _split_baseload_by_archetype

        result = _split_baseload_by_archetype(1000.0, "ARCHETYPE_INCONNU")
        assert len(result) > 0  # DEFAULT utilise
        assert abs(sum(result.values()) - 1000.0) < 1.0

    def test_15_archetypes_couverts_baseload(self):
        from services.analytics.usage_disaggregation import _BASELOAD_SPLIT
        from services.flex.flexibility_scoring_engine import ARCHETYPE_TO_USAGES

        for code in ARCHETYPE_TO_USAGES:
            assert code in _BASELOAD_SPLIT, f"{code} absent de _BASELOAD_SPLIT"

    def test_15_archetypes_couverts_business(self):
        from services.analytics.usage_disaggregation import _BUSINESS_INCREMENT_SPLIT
        from services.flex.flexibility_scoring_engine import ARCHETYPE_TO_USAGES

        for code in ARCHETYPE_TO_USAGES:
            assert code in _BUSINESS_INCREMENT_SPLIT, f"{code} absent de _BUSINESS_INCREMENT_SPLIT"


# === Tests extraction temporelle ===


class TestExtractionTemporelle:
    def _make_readings(self, n_days=30, base_kw=20.0, biz_kw=60.0, night_kw=15.0):
        """Genere des readings synthetiques realistes."""
        readings = []
        start = datetime(2025, 1, 1)
        for day in range(n_days):
            for half_hour in range(48):
                ts = start + timedelta(days=day, minutes=half_hour * 30)
                h = ts.hour
                dow = ts.weekday()
                if 2 <= h < 5:
                    kw = night_kw
                elif dow < 5 and 8 <= h < 19:
                    kw = biz_kw
                else:
                    kw = base_kw
                r = MagicMock()
                r.ts_debut = ts
                r.P_active_kw = kw
                r.pas_minutes = 30
                readings.append(r)
        return readings

    def test_extraction_detecte_baseload(self):
        from services.analytics.usage_disaggregation import _extract_temporal

        readings = self._make_readings(n_days=60, base_kw=20, biz_kw=60, night_kw=12)
        total_kwh = sum(r.P_active_kw * 0.5 for r in readings)

        baseload_kwh, biz_kwh, profile = _extract_temporal(
            readings,
            {"open_time": "08:00", "close_time": "19:00", "open_days": "0,1,2,3,4"},
            total_kwh,
            0,
        )
        assert baseload_kwh > 0
        assert profile["baseload_kw"] >= 10  # ~12 kW
        assert profile["baseload_kw"] <= 15
        assert profile["biz_mean_kw"] >= 50  # ~60 kW

    def test_extraction_increment_business_positif(self):
        from services.analytics.usage_disaggregation import _extract_temporal

        readings = self._make_readings(n_days=60, base_kw=10, biz_kw=80, night_kw=8)
        total_kwh = sum(r.P_active_kw * 0.5 for r in readings)

        baseload_kwh, biz_kwh, _ = _extract_temporal(
            readings,
            {"open_time": "08:00", "close_time": "19:00", "open_days": "0,1,2,3,4"},
            total_kwh,
            0,
        )
        assert biz_kwh > 0


# === Tests fallback archetype-only ===


class TestFallbackArchetypeOnly:
    def test_fallback_sans_cdc_retourne_usages(self):
        from services.analytics.usage_disaggregation import _fallback_archetype_only

        site = MagicMock()
        site.annual_kwh_total = 100000.0

        result = _fallback_archetype_only(1, "BUREAU_STANDARD", date(2025, 1, 1), date(2025, 12, 31), site, 0)
        assert result.method == "archetype_only"
        assert result.confidence_global == "low"
        assert len(result.usages) > 0
        total_pct = sum(u.pct for u in result.usages)
        assert 90 <= total_pct <= 110  # environ 100% avec arrondis

    def test_fallback_sans_conso_retourne_vide(self):
        from services.analytics.usage_disaggregation import _fallback_archetype_only

        site = MagicMock()
        site.annual_kwh_total = None

        result = _fallback_archetype_only(1, "BUREAU_STANDARD", date(2025, 1, 1), date(2025, 12, 31), site, 0)
        assert result.method == "no_data"
        assert len(result.usages) == 0


# === Tests normalisation codes JSON ===


class TestNormalisationCodes:
    def test_hvac_vers_cvc_hvac(self):
        from services.analytics.usage_disaggregation import _normalize_usage_code

        assert _normalize_usage_code("HVAC") == "CVC_HVAC"

    def test_eclairage_majuscule(self):
        from services.analytics.usage_disaggregation import _normalize_usage_code

        assert _normalize_usage_code("Eclairage") == "ECLAIRAGE"

    def test_code_inconnu_passthrough(self):
        from services.analytics.usage_disaggregation import _normalize_usage_code

        assert _normalize_usage_code("UNKNOWN") == "UNKNOWN"


# === Tests endpoint API ===


class TestEndpointAPI:
    def test_site_inexistant_404(self, app_client):
        client, _ = app_client
        resp = client.get("/api/analytics/sites/99999/usage-breakdown")
        assert resp.status_code == 404

    def test_site_sans_cdc_retourne_fallback(self, app_client):
        """Site cree sans meter ni CDC -> fallback archetype-only."""
        client, SessionLocal = app_client
        from models.site import Site
        from models.enums import TypeSite

        db = SessionLocal()
        try:
            site = Site(
                nom="Bureau Test Disagg",
                type=TypeSite.BUREAU,
                naf_code="6820A",
                actif=True,
                annual_kwh_total=150000.0,
            )
            db.add(site)
            db.commit()
            db.refresh(site)
            site_id = site.id
        finally:
            db.close()

        resp = client.get(f"/api/analytics/sites/{site_id}/usage-breakdown")
        assert resp.status_code == 200
        data = resp.json()
        assert data["method"] in ("archetype_only", "no_data", "3_layer_decomposition")
        assert "usages" in data
        assert "archetype_code" in data

    def test_endpoint_param_days(self, app_client):
        """Le parametre days est accepte."""
        client, _ = app_client
        resp = client.get("/api/analytics/sites/99999/usage-breakdown?days=90")
        assert resp.status_code == 404  # site inexistant mais param accepte
