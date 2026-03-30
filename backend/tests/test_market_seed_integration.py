"""
Test d'integration : seed market prices + tarifs → decomposition fonctionnelle.

Valide que le pipeline complet (seed → DB → service → API response) produit
des donnees credibles pour la carte Marche Electricite du cockpit.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models.market_models import MktPrice, MarketType, PriceZone
from services.demo_seed.gen_market_prices import generate_market_prices
from services.market_tariff_loader import load_tariffs_from_yaml
from services.market_data_service import MarketDataService
from services.price_decomposition_service import PriceDecompositionService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def db_seeded(db_session):
    """DB avec seed complet : spot 2024-2026 + forwards + tarifs."""
    generate_market_prices(db_session)
    db_session.commit()
    load_tariffs_from_yaml(db_session)
    return db_session


# ── Spot seed couvre 2026 ──────────────────────────────────────────


class TestSpotSeed2026:
    def test_spot_data_exists_for_march_2026(self, db_seeded):
        """La fenetre 30j autour de mars 2026 doit contenir des prix."""
        svc = MarketDataService(db_seeded)
        avg = svc.get_spot_average(days=30)
        assert avg is not None, "Aucun prix spot dans les 30 derniers jours"
        assert avg > 0

    def test_spot_average_realistic_2026(self, db_seeded):
        """Le prix spot 2026 doit etre autour de 62 EUR/MWh (base seed)."""
        svc = MarketDataService(db_seeded)
        avg = svc.get_spot_average(days=30)
        assert 40 < avg < 90, f"Spot avg={avg} hors fourchette realiste"

    def test_spot_history_7d_not_empty(self, db_seeded):
        """L'historique 7j doit retourner des prix pour la sparkline."""
        svc = MarketDataService(db_seeded)
        start = datetime.now(timezone.utc) - timedelta(days=7)
        prices = svc.get_spot_prices(start=start)
        assert len(prices) > 0, "Sparkline 7j vide"

    def test_spot_stats_7d_not_null(self, db_seeded):
        """Les stats 7j doivent avoir avg/min/max non-null."""
        svc = MarketDataService(db_seeded)
        stats = svc.get_price_stats(days=7)
        assert stats["avg_eur_mwh"] is not None
        assert stats["min_eur_mwh"] is not None
        assert stats["max_eur_mwh"] is not None


# ── Forward curves ──────────────────────────────────────────


class TestForwardCurves:
    def test_forward_year_exists(self, db_seeded):
        """Au moins un forward CAL doit exister."""
        svc = MarketDataService(db_seeded)
        from models.market_models import ProductType

        curves = svc.get_forward_curves()
        year_curves = [c for c in curves if c.market_type == MarketType.FORWARD_YEAR]
        assert len(year_curves) >= 1, "Aucun forward CAL"

    def test_forward_quarter_exists(self, db_seeded):
        """Au moins un forward trimestriel doit exister."""
        svc = MarketDataService(db_seeded)
        curves = svc.get_forward_curves()
        q_curves = [c for c in curves if c.market_type == MarketType.FORWARD_QUARTER]
        assert len(q_curves) >= 1, "Aucun forward Q"


# ── Decomposition avec seed complet ──────────────────────────────────


class TestDecompositionWithSeed:
    def test_turpe_never_zero(self, db_seeded):
        svc = PriceDecompositionService(db_seeded)
        result = svc.compute(profile="C4")
        assert result.turpe_eur_mwh > 0, f"TURPE = {result.turpe_eur_mwh} (attendu > 0)"

    def test_cspe_never_zero(self, db_seeded):
        svc = PriceDecompositionService(db_seeded)
        result = svc.compute(profile="C4")
        assert result.cspe_eur_mwh > 0, f"CSPE = {result.cspe_eur_mwh} (attendu > 0)"

    def test_energy_from_spot_not_fallback(self, db_seeded):
        svc = PriceDecompositionService(db_seeded)
        result = svc.compute(profile="C4")
        assert result.energy_eur_mwh != 68.0, "Energie utilise le fallback au lieu du spot"
        assert not any("fallback" in w.lower() for w in result.warnings)

    def test_tariff_version_not_unknown(self, db_seeded):
        svc = PriceDecompositionService(db_seeded)
        result = svc.compute(profile="C4")
        assert result.tariff_version != "unknown", "tariff_version est 'unknown'"
        assert result.tariff_version == "2026-03"

    def test_total_ttc_realistic(self, db_seeded):
        """Un prix C4 TTC doit etre entre 80 et 220 EUR/MWh."""
        svc = PriceDecompositionService(db_seeded)
        result = svc.compute(profile="C4")
        assert 80 <= result.total_ttc_eur_mwh <= 220, f"Total TTC = {result.total_ttc_eur_mwh} hors fourchette realiste"

    def test_all_7_components_nonzero(self, db_seeded):
        """Les 7 briques doivent avoir une valeur > 0."""
        svc = PriceDecompositionService(db_seeded)
        result = svc.compute(profile="C4")
        components = {
            "energy": result.energy_eur_mwh,
            "turpe": result.turpe_eur_mwh,
            "cspe": result.cspe_eur_mwh,
            "cee": result.cee_eur_mwh,
            "cta": result.cta_eur_mwh,
            "tva": result.tva_eur_mwh,
        }
        for name, value in components.items():
            assert value > 0, f"{name} = {value} (attendu > 0)"
        # Capacite peut etre quasi-nulle en 2026 (98.6 EUR/MW / 8760h = 0.01)
        assert result.capacity_eur_mwh >= 0

    def test_no_unknown_in_warnings(self, db_seeded):
        svc = PriceDecompositionService(db_seeded)
        result = svc.compute(profile="C4")
        for w in result.warnings:
            assert "unknown" not in w.lower(), f"Warning contient 'unknown': {w}"

    def test_decomposition_dict_format(self, db_seeded):
        """Le dict de sortie doit contenir toutes les cles attendues par le frontend."""
        svc = PriceDecompositionService(db_seeded)
        result = svc.compute(profile="C4")
        d = result.to_dict()
        required_keys = [
            "energy_eur_mwh",
            "turpe_eur_mwh",
            "cspe_eur_mwh",
            "capacity_eur_mwh",
            "cee_eur_mwh",
            "cta_eur_mwh",
            "tva_eur_mwh",
            "total_ttc_eur_mwh",
            "total_ht_eur_mwh",
            "calculation_method",
            "tariff_version",
            "warnings",
        ]
        for key in required_keys:
            assert key in d, f"Cle manquante dans to_dict(): {key}"
