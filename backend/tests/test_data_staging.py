"""Tests pour le pipeline de promotion SF5."""

from datetime import datetime

from data_staging.quality import quality_r4x, quality_r50, quality_r171, quality_r151_pmax
from data_staging.prm_matcher import PrmMatchResult
from utils.parsing import parse_iso_datetime as _parse_iso, parse_date as _parse_date, safe_float as _safe_float
from data_staging.promoters import (
    promote_r4x_row,
    promote_r50_row,
    promote_r171_row,
    promote_r151_row,
)
from data_staging.bridge import ReadingRow
from data_staging.models import MeterLoadCurve, MeterEnergyIndex, MeterPowerPeak


# ── Tests Quality Mapping ─────────────────────────────────────────────────


class TestQualityR4x:
    def test_reel(self):
        assert quality_r4x("R") == (1.00, False)

    def test_corrige(self):
        assert quality_r4x("C") == (0.95, False)

    def test_estime(self):
        assert quality_r4x("E") == (0.60, True)

    def test_reconstitue(self):
        assert quality_r4x("H") == (0.80, True)

    def test_coupure(self):
        for code in ("S", "T", "F", "G"):
            assert quality_r4x(code) == (0.90, False)

    def test_unknown(self):
        assert quality_r4x(None) == (0.50, True)
        assert quality_r4x("Z") == (0.50, True)


class TestQualityR50:
    def test_ok(self):
        assert quality_r50("0") == (1.00, False)

    def test_caution(self):
        assert quality_r50("1") == (0.70, False)

    def test_unknown(self):
        assert quality_r50(None) == (0.50, True)


class TestQualityDefaults:
    def test_r171(self):
        assert quality_r171() == (0.90, False)

    def test_r151_pmax(self):
        assert quality_r151_pmax() == (0.90, False)


# ── Tests Parsing Helpers ─────────────────────────────────────────────────


class TestParseHelpers:
    def test_parse_iso_basic(self):
        dt = _parse_iso("2025-06-15T10:30:00")
        assert dt == datetime(2025, 6, 15, 10, 30)

    def test_parse_iso_with_tz(self):
        dt = _parse_iso("2025-06-15T10:30:00+02:00")
        assert dt is not None
        assert dt.tzinfo is None  # Stocké en naive UTC

    def test_parse_iso_with_z(self):
        dt = _parse_iso("2025-06-15T10:30:00Z")
        assert dt == datetime(2025, 6, 15, 10, 30)

    def test_parse_iso_none(self):
        assert _parse_iso(None) is None
        assert _parse_iso("") is None

    def test_parse_date(self):
        d = _parse_date("2025-06-15")
        assert d.year == 2025 and d.month == 6 and d.day == 15

    def test_parse_date_from_datetime(self):
        d = _parse_date("2025-06-15T10:30:00+02:00")
        assert d.year == 2025 and d.month == 6 and d.day == 15

    def test_safe_float(self):
        assert _safe_float("123.45") == 123.45
        assert _safe_float(None) is None
        assert _safe_float("abc") is None
        assert _safe_float("0") == 0.0


# ── Tests PRM Matcher ─────────────────────────────────────────────────────


class TestPrmMatchResult:
    def test_matched(self):
        r = PrmMatchResult(meter_id=42)
        assert r.matched is True
        assert r.meter_id == 42
        assert r.block_reason is None

    def test_unmatched(self):
        r = PrmMatchResult(block_reason="no_delivery_point")
        assert r.matched is False
        assert r.meter_id is None

    def test_invalid_prm(self):
        from data_staging.prm_matcher import resolve_prm
        from unittest.mock import MagicMock

        db = MagicMock()
        result = resolve_prm(db, "123")  # Too short
        assert not result.matched
        assert result.block_reason == "invalid_prm_format"


# ── Tests Promoters (mock staging rows) ───────────────────────────────────


class _MockRow:
    """Row mock flexible."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestPromoteR4x:
    def test_basic_ea(self):
        row = _MockRow(
            horodatage="2025-06-15T10:00:00",
            valeur_point="150.5",
            statut_point="R",
            granularite="10",
            grandeur_physique="EA",
            flux_type="R4H",
        )
        result = promote_r4x_row(row, meter_id=1, run_id=1)
        assert isinstance(result, MeterLoadCurve)
        assert result.active_power_kw == 150.5
        assert result.pas_minutes == 10
        assert result.quality_score == 1.0
        assert result.is_estimated is False

    def test_reactive_inductive(self):
        row = _MockRow(
            horodatage="2025-06-15T10:00:00",
            valeur_point="30.0",
            statut_point="C",
            granularite="10",
            grandeur_physique="ERI",
            flux_type="R4M",
        )
        result = promote_r4x_row(row, meter_id=1, run_id=1)
        assert result.reactive_inductive_kvar == 30.0
        assert result.quality_score == 0.95

    def test_null_value_returns_none(self):
        row = _MockRow(
            horodatage="2025-06-15T10:00:00",
            valeur_point=None,
            statut_point="R",
            granularite="10",
            grandeur_physique="EA",
            flux_type="R4H",
        )
        assert promote_r4x_row(row, meter_id=1, run_id=1) is None


class TestPromoteR50:
    def test_timestamp_shift_and_w_to_kw(self):
        """R50 : horodatage = fin intervalle → soustrait 30min. W → kW."""
        row = _MockRow(
            horodatage="2025-06-15T11:00:00",  # Fin d'intervalle
            valeur="5000",  # 5000 W
            indice_vraisemblance="0",
        )
        result = promote_r50_row(row, meter_id=1, run_id=1)
        assert isinstance(result, MeterLoadCurve)
        assert result.timestamp == datetime(2025, 6, 15, 10, 30)  # Début = 10:30
        assert result.active_power_kw == 5.0  # 5000W → 5kW
        assert result.pas_minutes == 30
        assert result.quality_score == 1.0

    def test_null_value(self):
        row = _MockRow(horodatage="2025-06-15T11:00:00", valeur=None, indice_vraisemblance="0")
        assert promote_r50_row(row, meter_id=1, run_id=1) is None


class TestPromoteR171:
    def test_ea_wh_promoted(self):
        row = _MockRow(
            grandeur_physique="EA",
            unite="Wh",
            valeur="123456",
            date_fin="2025-06-15",
            type_calendrier="D",
            code_classe_temporelle="HPE",
            libelle_classe_temporelle="Heures Pleines Été",
        )
        result = promote_r171_row(row, meter_id=1, run_id=1)
        assert isinstance(result, MeterEnergyIndex)
        assert result.value_wh == 123456.0
        assert result.tariff_grid == "CT_DIST"
        assert result.tariff_class_code == "HPE"

    def test_non_ea_stays_in_staging(self):
        row = _MockRow(
            grandeur_physique="PMA",
            unite="W",
            valeur="100",
            date_fin="2025-06-15",
            type_calendrier="D",
            code_classe_temporelle="HPE",
            libelle_classe_temporelle="",
        )
        assert promote_r171_row(row, meter_id=1, run_id=1) is None


class TestPromoteR151:
    def test_pmax(self):
        row = _MockRow(
            type_donnee="PMAX",
            valeur="15000",
            date_releve="2025-06-15",
            id_classe_temporelle=None,
        )
        result = promote_r151_row(row, meter_id=1, run_id=1)
        assert isinstance(result, MeterPowerPeak)
        assert result.value_va == 15000.0

    def test_ct_dist(self):
        row = _MockRow(
            type_donnee="CT_DIST",
            valeur="789000",
            date_releve="2025-06-15",
            id_classe_temporelle="HCB",
            libelle_classe_temporelle="Heures Creuses Bleu",
        )
        result = promote_r151_row(row, meter_id=1, run_id=1)
        assert isinstance(result, MeterEnergyIndex)
        assert result.tariff_grid == "CT_DIST"
        assert result.tariff_class_code == "HCB"

    def test_unknown_type(self):
        row = _MockRow(
            type_donnee="UNKNOWN",
            valeur="100",
            date_releve="2025-06-15",
            id_classe_temporelle=None,
        )
        assert promote_r151_row(row, meter_id=1, run_id=1) is None


# ── Tests Bridge kW→kWh conversion (régression P0) ───────────────────────


class TestBridgeKwhConversion:
    """Régression : la conversion kW → kWh dans le bridge doit utiliser pas_minutes."""

    def test_30min_pas(self):
        """10 kW sur 30 min = 5 kWh."""
        from unittest.mock import patch, MagicMock

        mock_row = (datetime(2025, 6, 15, 10, 0), 10.0, 1.0, 30)  # ts, kW, quality, pas_minutes
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_row]

        db = MagicMock()
        db.query.return_value = mock_query

        from data_staging.bridge import _query_promoted

        with patch("data_staging.bridge._is_promoted_available", return_value=True):
            results = _query_promoted(db, [1], datetime(2025, 1, 1), None)

        assert len(results) == 1
        assert results[0].value_kwh == 5.0  # 10 kW × 0.5h = 5 kWh

    def test_10min_pas(self):
        """10 kW sur 10 min = 1.667 kWh."""
        from unittest.mock import MagicMock

        mock_row = (datetime(2025, 6, 15, 10, 0), 10.0, 1.0, 10)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_row]

        db = MagicMock()
        db.query.return_value = mock_query

        from data_staging.bridge import _query_promoted

        results = _query_promoted(db, [1], datetime(2025, 1, 1), None)

        assert len(results) == 1
        assert abs(results[0].value_kwh - 1.6667) < 0.01  # 10 × (10/60)

    def test_zero_power_preserved(self):
        """0 kW doit donner 0 kWh, pas être filtré."""
        from unittest.mock import MagicMock

        mock_row = (datetime(2025, 6, 15, 2, 0), 0.0, 1.0, 30)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_row]

        db = MagicMock()
        db.query.return_value = mock_query

        from data_staging.bridge import _query_promoted

        results = _query_promoted(db, [1], datetime(2025, 1, 1), None)

        assert len(results) == 1
        assert results[0].value_kwh == 0.0  # Zéro préservé

    def test_null_power_treated_as_zero(self):
        """NULL kW → 0 kWh (pas d'erreur)."""
        from unittest.mock import MagicMock

        mock_row = (datetime(2025, 6, 15, 2, 0), None, 1.0, 30)
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [mock_row]

        db = MagicMock()
        db.query.return_value = mock_query

        from data_staging.bridge import _query_promoted

        results = _query_promoted(db, [1], datetime(2025, 1, 1), None)

        assert len(results) == 1
        assert results[0].value_kwh == 0.0


# ── Tests Shared Utils ───────────────────────────────────────────────────


class TestSharedUtils:
    """Vérifie que utils.parsing est la source unique."""

    def test_safe_float_nan(self):
        assert _safe_float(float("nan")) is None

    def test_safe_float_string(self):
        assert _safe_float("42.5") == 42.5

    def test_parse_date_datetime_string(self):
        d = _parse_date("2025-06-15T10:30:00+02:00")
        assert d.year == 2025 and d.month == 6 and d.day == 15

    def test_parse_iso_strips_tz(self):
        dt = _parse_iso("2025-06-15T10:30:00+02:00")
        assert dt.tzinfo is None
