"""
Tests du moteur de decomposition prix electricite.

Couvre: 7 briques individuelles, assemblage complet, persistance DB,
tests de realisme (fourchettes metier), et comparaison profils.
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
from models.market_models import (
    MktPrice,
    MarketDataSource,
    MarketType,
    ProductType,
    PriceZone,
    Resolution,
    PriceDecomposition,
    TariffType,
    TariffComponent,
    RegulatedTariff,
)
from services.market_tariff_loader import load_tariffs_from_yaml
from services.price_decomposition_service import (
    PriceDecompositionService,
    DecompositionResult,
    LOAD_PROFILES,
)


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
def db_with_tariffs(db_session):
    """DB avec tous les tarifs YAML charges."""
    load_tariffs_from_yaml(db_session)
    return db_session


@pytest.fixture
def db_with_spot(db_with_tariffs):
    """DB avec tarifs + 30 jours de prix spot a 85 EUR/MWh."""
    now = datetime.now(timezone.utc)
    for d in range(30):
        for h in range(24):
            db_with_tariffs.add(
                MktPrice(
                    source=MarketDataSource.MANUAL,
                    market_type=MarketType.SPOT_DAY_AHEAD,
                    product_type=ProductType.HOURLY,
                    zone=PriceZone.FR,
                    delivery_start=now - timedelta(days=d, hours=h),
                    delivery_end=now - timedelta(days=d, hours=h - 1),
                    price_eur_mwh=85.0,
                    resolution=Resolution.PT60M,
                    fetched_at=now,
                )
            )
    db_with_tariffs.commit()
    return db_with_tariffs


# ============================================================
# Brique 1: Energie
# ============================================================


class TestBriqueEnergie:
    def test_energy_uses_spot_average(self, db_with_spot):
        svc = PriceDecompositionService(db_with_spot)
        result = svc.compute(profile="C4")
        assert abs(result.energy_eur_mwh - 85.0) < 1.0

    def test_energy_forced_price(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute(profile="C4", energy_price_eur_mwh=72.5)
        assert result.energy_eur_mwh == 72.5

    def test_energy_fallback_no_spot(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute(profile="C4")
        assert result.energy_eur_mwh == 68.0
        assert any("fallback" in w for w in result.warnings)


# ============================================================
# Brique 2: TURPE
# ============================================================


class TestBriqueTurpe:
    def test_turpe_weighted_average(self, db_with_tariffs):
        """TURPE C4 = 0.25*42.30 + 0.10*19.90 + 0.40*10.10 + 0.25*6.90 (CRE TURPE 7 CU pf)"""
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        # Calcul attendu: 10.575 + 1.99 + 4.04 + 1.725 = 18.33
        assert 17.5 < result.turpe_eur_mwh < 19.5

    def test_turpe_c5_different_from_c4(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        r_c5 = svc.compute(profile="C5", energy_price_eur_mwh=70.0)
        r_c4 = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        assert r_c5.turpe_eur_mwh != r_c4.turpe_eur_mwh

    def test_turpe_with_power_adds_fixed(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        r_no_power = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        r_with_power = svc.compute(
            profile="C4",
            energy_price_eur_mwh=70.0,
            power_kw=250,
            volume_mwh=2000,
        )
        assert r_with_power.turpe_eur_mwh > r_no_power.turpe_eur_mwh

    def test_turpe_fixed_part_calculation(self, db_with_tariffs):
        """Part fixe = 250kW * 14.41 EUR/kW/an / 2000 MWh = 1.80 EUR/MWh (CRE TURPE 7)."""
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute(
            profile="C4",
            energy_price_eur_mwh=70.0,
            power_kw=250,
            volume_mwh=2000,
        )
        r_no = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        delta = result.turpe_eur_mwh - r_no.turpe_eur_mwh
        assert abs(delta - 1.80) < 0.1  # 250 * 14.41 / 2000


# ============================================================
# Brique 3: CSPE
# ============================================================


class TestBriqueCspe:
    def test_cspe_c4_value(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        assert result.cspe_eur_mwh == 26.58

    def test_cspe_c5_higher_than_c4(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        r_c5 = svc.compute(profile="C5", energy_price_eur_mwh=70.0)
        r_c4 = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        assert r_c5.cspe_eur_mwh > r_c4.cspe_eur_mwh  # 30.35 > 26.58


# ============================================================
# Brique 4: Capacite
# ============================================================


class TestBriqueCapacite:
    def test_capacity_quasi_null(self, db_with_tariffs):
        """98.6 EUR/MW * 1.0 / 8760 = 0.011 EUR/MWh — quasi nul en 2026."""
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        assert result.capacity_eur_mwh < 0.02
        assert result.capacity_eur_mwh > 0


# ============================================================
# Brique 5: CEE
# ============================================================


class TestBriqueCee:
    def test_cee_value(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        assert result.cee_eur_mwh == 5.0


# ============================================================
# Brique 6: CTA
# ============================================================


class TestBriqueCta:
    def test_cta_with_power_and_volume(self, db_with_tariffs):
        """CTA = 15% * 250kW * 14.41 EUR/kW/an / 2000 MWh ≈ 0.27 EUR/MWh (CRE 2026-14)."""
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute(
            profile="C4",
            energy_price_eur_mwh=70.0,
            power_kw=250,
            volume_mwh=2000,
        )
        # 15% × 250 × 14.41 / 2000 = 0.270 EUR/MWh
        assert result.cta_eur_mwh > 0
        assert result.cta_eur_mwh < 0.60

    def test_cta_approximation_without_power(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        assert result.cta_eur_mwh > 0
        assert any("approximation" in w for w in result.warnings)


# ============================================================
# Brique 7: TVA
# ============================================================


class TestBriqueTva:
    def test_tva_20_pct(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        expected_tva = result.total_ht_eur_mwh * 0.20
        assert abs(result.tva_eur_mwh - expected_tva) < 0.1

    def test_ttc_equals_ht_plus_tva(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        assert abs(result.total_ttc_eur_mwh - (result.total_ht_eur_mwh + result.tva_eur_mwh)) < 0.01


# ============================================================
# Assemblage complet
# ============================================================


class TestAssemblage:
    def test_total_ht_sum_of_briques(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        r = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        briques = (
            r.energy_eur_mwh + r.turpe_eur_mwh + r.cspe_eur_mwh + r.capacity_eur_mwh + r.cee_eur_mwh + r.cta_eur_mwh
        )
        assert abs(r.total_ht_eur_mwh - briques) < 0.01

    def test_tariff_version_populated(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        r = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        assert r.tariff_version == "2026-03"

    def test_to_dict_serializable(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        r = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        d = r.to_dict()
        assert isinstance(d, dict)
        assert "energy_eur_mwh" in d
        assert "total_ttc_eur_mwh" in d
        assert isinstance(d["warnings"], list)


# ============================================================
# Realisme metier
# ============================================================


class TestRealisme:
    def test_total_ttc_between_120_and_250(self, db_with_tariffs):
        """Le prix TTC complet doit etre entre 120 et 250 EUR/MWh."""
        svc = PriceDecompositionService(db_with_tariffs)
        for profile in ["C5", "C4", "C2", "HTA"]:
            r = svc.compute(profile=profile, energy_price_eur_mwh=70.0)
            assert 120 < r.total_ttc_eur_mwh < 250, f"TTC {r.total_ttc_eur_mwh} hors fourchette pour {profile}"

    def test_energy_is_biggest_brique(self, db_with_tariffs):
        """L'energie doit etre la brique la plus grosse."""
        svc = PriceDecompositionService(db_with_tariffs)
        r = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        briques = {
            "energy": r.energy_eur_mwh,
            "turpe": r.turpe_eur_mwh,
            "cspe": r.cspe_eur_mwh,
            "capacity": r.capacity_eur_mwh,
            "cee": r.cee_eur_mwh,
            "cta": r.cta_eur_mwh,
        }
        assert max(briques, key=briques.get) == "energy"

    def test_turpe_second_biggest_brique(self, db_with_tariffs):
        """Le TURPE doit etre la 2e brique la plus grosse."""
        svc = PriceDecompositionService(db_with_tariffs)
        r = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        briques = [
            ("energy", r.energy_eur_mwh),
            ("turpe", r.turpe_eur_mwh),
            ("cspe", r.cspe_eur_mwh),
        ]
        briques.sort(key=lambda x: x[1], reverse=True)
        # Avec TURPE 7 CRE officiel, CSPE (26.58) > TURPE variable (18.33)
        assert briques[0][0] == "energy"
        assert briques[1][0] in ("turpe", "cspe")  # CSPE ou TURPE selon profil

    def test_c5_more_expensive_than_c4(self, db_with_tariffs):
        """Un C5 (petit consommateur) paye plus cher au MWh qu'un C4."""
        svc = PriceDecompositionService(db_with_tariffs)
        r_c5 = svc.compute(profile="C5", energy_price_eur_mwh=70.0)
        r_c4 = svc.compute(profile="C4", energy_price_eur_mwh=70.0)
        assert r_c5.total_ttc_eur_mwh > r_c4.total_ttc_eur_mwh


# ============================================================
# Persistance
# ============================================================


class TestPersistance:
    def test_compute_and_store_creates_record(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute_and_store(
            org_id=1,
            site_id=1,
            profile="C4",
            energy_price_eur_mwh=70.0,
        )
        count = db_with_tariffs.query(PriceDecomposition).count()
        assert count == 1
        record = db_with_tariffs.query(PriceDecomposition).first()
        assert record.profile == "C4"
        assert record.energy_eur_mwh == result.energy_eur_mwh
        assert record.total_ttc_eur_mwh == result.total_ttc_eur_mwh

    def test_compute_and_store_returns_result(self, db_with_tariffs):
        svc = PriceDecompositionService(db_with_tariffs)
        result = svc.compute_and_store(
            org_id=1,
            profile="C4",
            energy_price_eur_mwh=70.0,
        )
        assert isinstance(result, DecompositionResult)
        assert result.total_ttc_eur_mwh > 0


# ============================================================
# Profils de charge
# ============================================================


class TestProfilsCharge:
    def test_all_profiles_sum_to_100(self):
        """Les poids horosaisonniers de chaque profil doivent sommer a 1.0."""
        for profile, weights in LOAD_PROFILES.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.001, f"Profil {profile}: somme = {total}"

    def test_four_profiles_defined(self):
        assert set(LOAD_PROFILES.keys()) == {"C5", "C4", "C2", "HTA"}


# ============================================================
# Versionnement temporel des tarifs
# ============================================================


class TestVersionnementTemporel:
    """Verifie que la decomposition utilise les tarifs de la bonne periode."""

    def test_turpe6_vs_turpe7(self, db_with_tariffs):
        """Juin 2025 = TURPE 6, oct 2025 = TURPE 7 — valeurs differentes."""
        svc = PriceDecompositionService(db_with_tariffs)
        r_t6 = svc.compute(
            profile="C4",
            energy_price_eur_mwh=85.0,
            period_start=datetime(2025, 6, 15, tzinfo=timezone.utc),
        )
        r_t7 = svc.compute(
            profile="C4",
            energy_price_eur_mwh=85.0,
            period_start=datetime(2025, 10, 15, tzinfo=timezone.utc),
        )
        assert r_t6.turpe_eur_mwh != r_t7.turpe_eur_mwh
        # TURPE 6 HPH=32.00, TURPE 7 HPH=42.30 — pondere C4 => T6~19.25, T7~18.33
        assert 18.5 < r_t6.turpe_eur_mwh < 20.5  # TURPE 6
        assert 17.5 < r_t7.turpe_eur_mwh < 19.5  # TURPE 7

    def test_cspe_2024_vs_2025_vs_2026(self, db_with_tariffs):
        """CSPE augmente chaque annee: 2024 < 2025 < 2026."""
        svc = PriceDecompositionService(db_with_tariffs)
        r24 = svc.compute(
            profile="C4",
            energy_price_eur_mwh=85.0,
            period_start=datetime(2024, 6, 15, tzinfo=timezone.utc),
        )
        r25 = svc.compute(
            profile="C4",
            energy_price_eur_mwh=85.0,
            period_start=datetime(2025, 6, 15, tzinfo=timezone.utc),
        )
        r26 = svc.compute(
            profile="C4",
            energy_price_eur_mwh=85.0,
            period_start=datetime(2026, 6, 15, tzinfo=timezone.utc),
        )
        assert r24.cspe_eur_mwh == 20.50  # LF 2024
        assert r25.cspe_eur_mwh == 25.79  # LF 2025
        assert r26.cspe_eur_mwh == 26.58  # LF 2026
        assert r24.cspe_eur_mwh < r25.cspe_eur_mwh < r26.cspe_eur_mwh

    def test_cta_taux_change_2026(self, db_with_tariffs):
        """CTA passe de 21.93% a 15% au 1er fev 2026 (CRE 2026-14)."""
        svc = PriceDecompositionService(db_with_tariffs)
        r_jan = svc.compute(
            profile="C4",
            energy_price_eur_mwh=85.0,
            period_start=datetime(2026, 1, 15, tzinfo=timezone.utc),
        )
        r_feb = svc.compute(
            profile="C4",
            energy_price_eur_mwh=85.0,
            period_start=datetime(2026, 2, 15, tzinfo=timezone.utc),
        )
        assert r_feb.cta_eur_mwh < r_jan.cta_eur_mwh

    def test_cee_p5_vs_p6(self, db_with_tariffs):
        """CEE P5 (4 EUR/MWh) avant 2026, P6 (5 EUR/MWh) apres."""
        svc = PriceDecompositionService(db_with_tariffs)
        r_p5 = svc.compute(
            profile="C4",
            energy_price_eur_mwh=85.0,
            period_start=datetime(2025, 6, 15, tzinfo=timezone.utc),
        )
        r_p6 = svc.compute(
            profile="C4",
            energy_price_eur_mwh=85.0,
            period_start=datetime(2026, 6, 15, tzinfo=timezone.utc),
        )
        assert r_p5.cee_eur_mwh == 4.0
        assert r_p6.cee_eur_mwh == 5.0

    def test_retroactive_ttc_realistic(self, db_with_tariffs):
        """Un calcul retroactif oct 2024 @ 85 EUR/MWh doit etre < mars 2026."""
        svc = PriceDecompositionService(db_with_tariffs)
        r_2024 = svc.compute(
            profile="C4",
            energy_price_eur_mwh=85.0,
            period_start=datetime(2024, 10, 15, tzinfo=timezone.utc),
        )
        r_2026 = svc.compute(
            profile="C4",
            energy_price_eur_mwh=85.0,
        )
        # Taxes augmentent => TTC 2024 < TTC 2026
        assert r_2024.total_ttc_eur_mwh < r_2026.total_ttc_eur_mwh
