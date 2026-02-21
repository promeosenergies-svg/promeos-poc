"""
PROMEOS - Tests Sprint V4.9: ImpactModel (resolve_price, compute_off_hours_eur, compute_power_overrun_eur)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, EntiteJuridique, Portefeuille, TypeSite
from models.billing_models import EnergyContract
from models.enums import BillingEnergyType
from models.site_tariff_profile import SiteTariffProfile
from services.impact_model import (
    resolve_price, compute_off_hours_eur, compute_power_overrun_eur,
    PriceInfo, DEFAULT_PRICE_EUR_KWH, TURPE_PENALTY_EUR_KVA_MONTH,
)


@pytest.fixture
def db():
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


def _create_site(db):
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="123456789")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="P1")
    db.add(pf)
    db.flush()
    site = Site(portefeuille_id=pf.id, nom="Site Test", type=TypeSite.BUREAU, surface_m2=1000, actif=True)
    db.add(site)
    db.flush()
    return site


# ========================================
# resolve_price
# ========================================

class TestResolvePrice:
    def test_default_demo_mode(self, db):
        """No contract, no tariff -> DEMO mode with default price."""
        site = _create_site(db)
        db.commit()

        info = resolve_price(db, site.id)
        assert info.mode == "DEMO"
        assert info.price_eur_kwh == DEFAULT_PRICE_EUR_KWH
        assert info.confidence == "low"

    def test_tariff_profile_mode(self, db):
        """SiteTariffProfile present -> TARIF mode."""
        site = _create_site(db)
        tariff = SiteTariffProfile(site_id=site.id, price_ref_eur_per_kwh=0.22)
        db.add(tariff)
        db.commit()

        info = resolve_price(db, site.id)
        assert info.mode == "TARIF"
        assert info.price_eur_kwh == 0.22
        assert info.confidence == "medium"

    def test_contract_mode(self, db):
        """EnergyContract with price -> CONTRAT mode (highest priority)."""
        site = _create_site(db)
        # Also add tariff to verify contract takes precedence
        tariff = SiteTariffProfile(site_id=site.id, price_ref_eur_per_kwh=0.22)
        db.add(tariff)
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 12, 31),
            price_ref_eur_per_kwh=0.15,
        )
        db.add(contract)
        db.commit()

        info = resolve_price(db, site.id)
        assert info.mode == "CONTRAT"
        assert info.price_eur_kwh == 0.15
        assert info.confidence == "high"
        assert "EDF" in info.source_label

    def test_contract_without_price_falls_to_tariff(self, db):
        """Contract with null price -> falls back to tariff."""
        site = _create_site(db)
        tariff = SiteTariffProfile(site_id=site.id, price_ref_eur_per_kwh=0.20)
        db.add(tariff)
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Engie",
            price_ref_eur_per_kwh=None,
        )
        db.add(contract)
        db.commit()

        info = resolve_price(db, site.id)
        assert info.mode == "TARIF"
        assert info.price_eur_kwh == 0.20


# ========================================
# compute_off_hours_eur
# ========================================

class TestOffHoursEur:
    def test_zero_kwh(self):
        """Zero off-hours -> 0 EUR."""
        price = PriceInfo(price_eur_kwh=0.18, mode="DEMO", source_label="test", confidence="low")
        result = compute_off_hours_eur(0, 90, price)
        assert result.eur_year == 0.0
        assert len(result.assumptions) > 0

    def test_annualization(self):
        """90-day observation annualized correctly."""
        price = PriceInfo(price_eur_kwh=0.20, mode="CONTRAT", source_label="EDF", confidence="high")
        result = compute_off_hours_eur(1000, 90, price, reduction_pct=1.0)
        # 1000 * (365/90) * 1.0 * 0.20 = 811.11
        expected = round(1000 * (365 / 90) * 1.0 * 0.20, 2)
        assert result.eur_year == expected
        assert result.mode == "CONTRAT"

    def test_reduction_50pct(self):
        """Default 50% reduction."""
        price = PriceInfo(price_eur_kwh=0.18, mode="DEMO", source_label="test", confidence="low")
        result = compute_off_hours_eur(1000, 365, price, reduction_pct=0.5)
        expected = round(1000 * 0.5 * 0.18, 2)
        assert result.eur_year == expected

    def test_mode_propagation(self):
        """Mode from PriceInfo propagates to result."""
        price = PriceInfo(price_eur_kwh=0.15, mode="CONTRAT", source_label="EDF", confidence="high")
        result = compute_off_hours_eur(500, 30, price)
        assert result.mode == "CONTRAT"
        assert result.confidence == "high"


# ========================================
# compute_power_overrun_eur
# ========================================

class TestPowerOverrunEur:
    def test_no_overrun(self):
        """P95 <= Psub -> 0 EUR."""
        price = PriceInfo(price_eur_kwh=0.18, mode="DEMO", source_label="test", confidence="low")
        result = compute_power_overrun_eur(100, 150, price)
        assert result.eur_year == 0.0

    def test_with_overrun(self):
        """P95 > Psub -> penalty = excess * 15.48 * 12."""
        price = PriceInfo(price_eur_kwh=0.18, mode="TARIF", source_label="test", confidence="medium")
        result = compute_power_overrun_eur(200, 150, price)
        expected = round(50 * TURPE_PENALTY_EUR_KVA_MONTH * 12, 2)
        assert result.eur_year == expected
        assert result.mode == "TARIF"

    def test_psub_none(self):
        """Psub unknown -> 0 EUR with low confidence."""
        price = PriceInfo(price_eur_kwh=0.18, mode="CONTRAT", source_label="test", confidence="high")
        result = compute_power_overrun_eur(200, None, price)
        assert result.eur_year == 0.0
        assert result.confidence == "low"

    def test_no_negative(self):
        """Result is never negative."""
        price = PriceInfo(price_eur_kwh=0.18, mode="DEMO", source_label="test", confidence="low")
        result = compute_power_overrun_eur(50, 200, price)
        assert result.eur_year >= 0.0

    def test_no_nan(self):
        """No NaN values in any result field."""
        price = PriceInfo(price_eur_kwh=0.18, mode="DEMO", source_label="test", confidence="low")
        for p95, psub in [(0, 0), (100, 100), (200, 150), (0, None)]:
            result = compute_power_overrun_eur(p95, psub, price)
            assert not math.isnan(result.eur_year)
            assert not math.isnan(result.price_eur_kwh)
