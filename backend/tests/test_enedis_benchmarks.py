"""Tests pour le service de benchmark sectoriel Enedis Open Data."""

from datetime import datetime
from unittest.mock import patch, MagicMock

from services.enedis_benchmarks import (
    _compute_atypicity,
    _atypicity_label,
    _power_to_range,
    _TYPE_TO_ENEDIS_SECTOR,
)
from utils.parsing import parse_iso_datetime as _parse_dt, safe_float as _safe_float, safe_int as _safe_int


# ── Tests utilitaires ────────────────────────────────────────────────────


class TestParseHelpers:
    """Helpers de parsing ODS."""

    def test_parse_dt_iso(self):
        dt = _parse_dt("2025-01-15T10:30:00")
        assert dt == datetime(2025, 1, 15, 10, 30)

    def test_parse_dt_with_z(self):
        dt = _parse_dt("2025-01-15T10:30:00Z")
        assert dt == datetime(2025, 1, 15, 10, 30)

    def test_parse_dt_none(self):
        assert _parse_dt(None) is None
        assert _parse_dt("") is None

    def test_safe_float(self):
        assert _safe_float("123.45") == 123.45
        assert _safe_float(None) is None
        assert _safe_float("abc") is None

    def test_safe_int(self):
        assert _safe_int("42") == 42
        assert _safe_int("42.7") == 42
        assert _safe_int(None) is None


# ── Tests mapping ────────────────────────────────────────────────────────


class TestMappings:
    """Mappings archétype → secteur Enedis et puissance → plage."""

    def test_bureau_maps_to_tertiaire(self):
        assert _TYPE_TO_ENEDIS_SECTOR["bureau"] == "S3: Tertiaire"

    def test_usine_maps_to_industrie(self):
        assert _TYPE_TO_ENEDIS_SECTOR["usine"] == "S2: Industrie"

    def test_copropriete_maps_to_tertiaire(self):
        assert _TYPE_TO_ENEDIS_SECTOR["copropriete"] == "S3: Tertiaire"

    def test_power_range_50kva(self):
        assert _power_to_range(50) == "P1: ]36-120] kVA"

    def test_power_range_exactly_36(self):
        """36 kVA n'est PAS >36 kVA → None (convention Enedis ]36-120])."""
        assert _power_to_range(36) is None

    def test_power_range_none(self):
        assert _power_to_range(None) is None

    def test_power_range_200kva(self):
        assert _power_to_range(200) == "P2: ]120-250] kVA"

    def test_power_range_high(self):
        assert _power_to_range(3000) == "P6: > 2000 kVA"

    def test_power_range_120_is_P1(self):
        """120 kVA est dans ]36-120] → P1 (convention Enedis : borne haute incluse)."""
        assert _power_to_range(120) == "P1: ]36-120] kVA"

    def test_power_range_121_is_P2(self):
        """121 kVA est dans ]120-250] → P2."""
        assert _power_to_range(121) == "P2: ]120-250] kVA"

    def test_power_range_below_36(self):
        assert _power_to_range(20) is None


# ── Tests score d'atypie ─────────────────────────────────────────────────


class TestAtypicity:
    """Score d'atypie entre profil site et benchmark."""

    def test_identical_profiles(self):
        """Profils identiques → score ~0."""
        profile = {h: 10.0 + h * 0.5 for h in range(24)}
        score = _compute_atypicity(profile, profile)
        assert score < 0.01

    def test_proportional_profiles(self):
        """Profils proportionnels (même forme, volume différent) → score ~0."""
        site = {h: 20.0 + h * 1.0 for h in range(24)}
        bench = {h: 10.0 + h * 0.5 for h in range(24)}
        score = _compute_atypicity(site, bench)
        assert score < 0.01  # Mêmes formes normalisées

    def test_opposite_profiles(self):
        """Profils inversés → score élevé."""
        site = {h: 100 - h * 4 for h in range(24)}  # décroissant
        bench = {h: 10 + h * 4 for h in range(24)}  # croissant
        score = _compute_atypicity(site, bench)
        assert score > 0.3

    def test_flat_vs_peaked(self):
        """Profil plat vs profil avec pic → score modéré."""
        site = {h: 50.0 for h in range(24)}
        bench = {h: 10.0 if h < 8 or h > 18 else 100.0 for h in range(24)}
        score = _compute_atypicity(site, bench)
        assert 0.1 < score < 0.8

    def test_zero_mean_handling(self):
        """Profil à moyenne nulle → score 0.5 (fallback)."""
        site = {h: 0.0 for h in range(24)}
        bench = {h: 10.0 for h in range(24)}
        score = _compute_atypicity(site, bench)
        assert score == 0.5

    def test_atypicity_labels(self):
        assert _atypicity_label(0.05) == "typique"
        assert _atypicity_label(0.20) == "modere"
        assert _atypicity_label(0.40) == "atypique"
        assert _atypicity_label(0.70) == "tres_atypique"
        assert _atypicity_label(None) == "indisponible"


# ── Tests connector ODS (mock HTTP) ──────────────────────────────────────


class TestODSConnector:
    """Test du connector OpenData avec mock httpx."""

    def test_test_connection_success(self):
        """test_connection retourne ok quand API accessible."""
        from connectors.enedis_opendata import EnedisOpenDataConnector

        connector = EnedisOpenDataConnector()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("connectors.enedis_opendata.httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = MagicMock(
                return_value=MagicMock(get=MagicMock(return_value=mock_response))
            )
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            result = connector.test_connection()
            assert result["status"] == "ok"

    def test_build_date_filter(self):
        """Vérifie la construction du filtre where ODS."""
        from connectors.enedis_opendata import EnedisOpenDataConnector

        f = EnedisOpenDataConnector._build_date_filter("2025-01-01", "2025-06-30")
        assert "2025-01-01" in f
        assert "2025-06-30" in f
        assert "AND" in f

    def test_build_date_filter_empty(self):
        from connectors.enedis_opendata import EnedisOpenDataConnector

        f = EnedisOpenDataConnector._build_date_filter(None, None)
        assert f == ""
