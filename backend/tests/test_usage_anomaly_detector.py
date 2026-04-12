"""
Tests du detecteur d'anomalies par usage.
Couvre : 6 detecteurs, seuils contextuels, endpoint API.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import MagicMock, patch
from datetime import date


class TestHelpers:
    def test_night_base_ratio_normal(self):
        from services.analytics.usage_anomaly_detector import _compute_night_base_ratio

        ratio = _compute_night_base_ratio({"baseload_kw": 10, "biz_mean_kw": 50})
        assert ratio == pytest.approx(0.2, abs=0.01)

    def test_night_base_ratio_zero_biz(self):
        from services.analytics.usage_anomaly_detector import _compute_night_base_ratio

        ratio = _compute_night_base_ratio({"baseload_kw": 10, "biz_mean_kw": 0})
        assert ratio == 0

    def test_weekend_ratio(self):
        from services.analytics.usage_anomaly_detector import _compute_weekend_ratio

        ratio = _compute_weekend_ratio({"off_mean_kw": 15, "biz_mean_kw": 50})
        assert ratio == pytest.approx(0.3, abs=0.01)

    def test_load_archetype_thresholds_bureau(self):
        from services.analytics.usage_anomaly_detector import _load_archetype_thresholds

        t = _load_archetype_thresholds("BUREAU_STANDARD")
        assert "ANOM_BASE_NUIT_ELEVEE" in t
        assert t["ANOM_BASE_NUIT_ELEVEE"] == pytest.approx(0.2, abs=0.01)

    def test_load_archetype_thresholds_commerce(self):
        from services.analytics.usage_anomaly_detector import _load_archetype_thresholds

        t = _load_archetype_thresholds("COMMERCE_ALIMENTAIRE")
        # Commerce alimentaire a un seuil nuit bien plus haut (froid 24/7)
        assert t["ANOM_BASE_NUIT_ELEVEE"] > 0.5


class TestDetecteurs:
    """Tests unitaires des detecteurs via mock de disaggregate_site."""

    def _mock_disagg(self, archetype, total_kwh, usages, temporal=None, thermal=None):
        from services.analytics.usage_disaggregation import DisaggregationResult, UsageShare

        return DisaggregationResult(
            site_id=1,
            period_start="2025-01-01",
            period_end="2025-12-31",
            total_kwh=total_kwh,
            archetype_code=archetype,
            usages=[
                UsageShare(
                    code=u["code"],
                    label=u.get("label", u["code"]),
                    kwh=u["kwh"],
                    pct=u["pct"],
                    method="test",
                    confidence="medium",
                )
                for u in usages
            ],
            thermal_signature=thermal,
            temporal_profile=temporal,
            n_readings=17520,
            confidence_global="medium",
        )

    @patch("services.analytics.usage_anomaly_detector._get_site_surface", return_value=None)
    @patch("services.analytics.usage_disaggregation.disaggregate_site")
    def test_cvc_nuit_excessif_bureau(self, mock_disagg, _mock_surface):
        """Bureau avec CVC nuit a 35% -> anomalie detectee."""
        from services.analytics.usage_anomaly_detector import detect_usage_anomalies

        mock_disagg.return_value = self._mock_disagg(
            "BUREAU_STANDARD",
            100000,
            [{"code": "CVC_HVAC", "kwh": 40000, "pct": 40}],
            temporal={
                "baseload_kw": 35,
                "biz_mean_kw": 100,
                "off_mean_kw": 20,
                "biz_increment_kw": 65,
                "n_night_readings": 500,
                "n_biz_readings": 2000,
            },
        )
        db = MagicMock()
        result = detect_usage_anomalies(db, 1)
        cvc_anom = [a for a in result.anomalies if a.anomaly_type == "CVC_NUIT_EXCESSIF"]
        assert len(cvc_anom) == 1
        assert cvc_anom[0].gain_eur_an > 0

    @patch("services.analytics.usage_anomaly_detector._get_site_surface", return_value=None)
    @patch("services.analytics.usage_disaggregation.disaggregate_site")
    def test_cvc_nuit_normal_commerce(self, mock_disagg, _):
        """Commerce alimentaire avec nuit a 60% -> PAS d'anomalie (froid 24/7 normal)."""
        from services.analytics.usage_anomaly_detector import detect_usage_anomalies

        mock_disagg.return_value = self._mock_disagg(
            "COMMERCE_ALIMENTAIRE",
            200000,
            [{"code": "FROID_COMMERCIAL", "kwh": 100000, "pct": 50}, {"code": "CVC_HVAC", "kwh": 40000, "pct": 20}],
            temporal={
                "baseload_kw": 60,
                "biz_mean_kw": 100,
                "off_mean_kw": 70,
                "biz_increment_kw": 40,
                "n_night_readings": 500,
                "n_biz_readings": 2000,
            },
        )
        db = MagicMock()
        result = detect_usage_anomalies(db, 1)
        cvc_anom = [a for a in result.anomalies if a.anomaly_type == "CVC_NUIT_EXCESSIF"]
        assert len(cvc_anom) == 0  # seuil commerce = 0.75, ratio 0.60 = OK

    @patch("services.analytics.usage_anomaly_detector._get_site_surface", return_value=None)
    @patch("services.analytics.usage_disaggregation.disaggregate_site")
    def test_eclairage_nuit_detecte(self, mock_disagg, _):
        """Eclairage > 10% + ratio nuit/jour > 30% -> anomalie eclairage."""
        from services.analytics.usage_anomaly_detector import detect_usage_anomalies

        mock_disagg.return_value = self._mock_disagg(
            "BUREAU_STANDARD",
            100000,
            [{"code": "CVC_HVAC", "kwh": 40000, "pct": 40}, {"code": "ECLAIRAGE", "kwh": 22000, "pct": 22}],
            temporal={
                "baseload_kw": 25,
                "biz_mean_kw": 60,
                "off_mean_kw": 15,
                "biz_increment_kw": 35,
                "n_night_readings": 500,
                "n_biz_readings": 2000,
            },
        )
        db = MagicMock()
        result = detect_usage_anomalies(db, 1)
        ecl_anom = [a for a in result.anomalies if a.anomaly_type == "ECLAIRAGE_NUIT"]
        assert len(ecl_anom) == 1

    @patch("services.analytics.usage_disaggregation.disaggregate_site")
    @patch("services.analytics.usage_anomaly_detector._get_site_surface")
    def test_intensite_energetique_elevee(self, mock_surface, mock_disagg):
        """Intensite 400 kWh/m2 vs seuil P90 300 -> anomalie."""
        from services.analytics.usage_anomaly_detector import detect_usage_anomalies

        mock_surface.return_value = 500.0  # 500 m2
        mock_disagg.return_value = self._mock_disagg(
            "BUREAU_STANDARD",
            200000,  # 400 kWh/m2
            [{"code": "CVC_HVAC", "kwh": 80000, "pct": 40}],
            temporal={
                "baseload_kw": 10,
                "biz_mean_kw": 60,
                "off_mean_kw": 8,
                "biz_increment_kw": 50,
                "n_night_readings": 500,
                "n_biz_readings": 2000,
            },
        )
        db = MagicMock()
        result = detect_usage_anomalies(db, 1)
        intensity_anom = [a for a in result.anomalies if a.anomaly_type == "INTENSITE_ENERGETIQUE_ELEVEE"]
        assert len(intensity_anom) == 1
        assert intensity_anom[0].gain_eur_an > 0

    @patch("services.analytics.usage_anomaly_detector._get_site_surface", return_value=None)
    @patch("services.analytics.usage_disaggregation.disaggregate_site")
    def test_anomalies_triees_par_gain(self, mock_disagg, _):
        """Les anomalies sont triees par gain EUR decroissant."""
        from services.analytics.usage_anomaly_detector import detect_usage_anomalies

        mock_disagg.return_value = self._mock_disagg(
            "BUREAU_STANDARD",
            100000,
            [{"code": "CVC_HVAC", "kwh": 40000, "pct": 40}, {"code": "ECLAIRAGE", "kwh": 22000, "pct": 22}],
            temporal={
                "baseload_kw": 35,
                "biz_mean_kw": 80,
                "off_mean_kw": 30,
                "biz_increment_kw": 45,
                "n_night_readings": 500,
                "n_biz_readings": 2000,
            },
        )
        db = MagicMock()
        result = detect_usage_anomalies(db, 1)
        if len(result.anomalies) >= 2:
            gains = [a.gain_eur_an for a in result.anomalies]
            assert gains == sorted(gains, reverse=True)


class TestEndpointAPI:
    def test_site_inexistant_404(self, app_client):
        client, _ = app_client
        resp = client.get("/api/analytics/sites/99999/usage-anomalies")
        assert resp.status_code == 404

    def test_site_sans_cdc(self, app_client):
        """Site sans CDC -> endpoint retourne 200 (meme si 0 anomalies)."""
        client, SessionLocal = app_client
        from models.site import Site
        from models.enums import TypeSite

        db = SessionLocal()
        try:
            site = Site(
                nom="Bureau Anomaly Test",
                type=TypeSite.BUREAU,
                naf_code="6820A",
                actif=True,
                annual_kwh_total=150000.0,
                surface_m2=600.0,
            )
            db.add(site)
            db.commit()
            db.refresh(site)
            site_id = site.id
        finally:
            db.close()

        resp = client.get(f"/api/analytics/sites/{site_id}/usage-anomalies")
        assert resp.status_code == 200
        data = resp.json()
        assert "anomalies" in data
        assert "total_gain_eur_an" in data
        assert data["archetype_code"] != ""
