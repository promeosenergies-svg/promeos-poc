"""
Tests KPIs Contrats V2 : prix moyen pondere par volume.
Source poids : profils Enedis C5/C4 (HP=62%, HC=38%, HPH=25%, etc.)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    EnergyContract,
    BillingEnergyType,
    ContractStatus,
    ContractIndexation,
    TariffOptionEnum,
)
from models.contract_v2_models import ContractAnnexe, ContractPricing, VolumeCommitment
from services.contract_v2_service import compute_cadre_kpis, PERIOD_WEIGHTS


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


@pytest.fixture
def setup(db):
    from models.enums import TypeSite

    org = Organisation(nom="TestOrg", siren="111222333", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="TestEJ", siren="999888777")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF1")
    db.add(pf)
    db.flush()
    s1 = Site(portefeuille_id=pf.id, nom="Site A", type=TypeSite.BUREAU, actif=True)
    db.add(s1)
    db.flush()
    db.commit()
    return {"org": org, "ej": ej, "site": s1}


def _make_cadre_with_pricing(db, setup, pricing_lines, volume_kwh=None, **cadre_overrides):
    """Helper : cadre + annexe + pricing lines + volume optionnel."""
    defaults = dict(
        site_id=setup["site"].id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="Test",
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=335),
        notice_period_days=90,
        is_cadre=True,
        contract_type="UNIQUE",
        entite_juridique_id=setup["ej"].id,
    )
    defaults.update(cadre_overrides)
    cadre = EnergyContract(**defaults)
    db.add(cadre)
    db.flush()

    for pc, price in pricing_lines:
        db.add(
            ContractPricing(
                contract_id=cadre.id,
                period_code=pc,
                season="ANNUEL",
                unit_price_eur_kwh=price,
            )
        )

    a = ContractAnnexe(
        contrat_cadre_id=cadre.id,
        site_id=setup["site"].id,
        annexe_ref="ANX-1",
        status=ContractStatus.ACTIVE,
    )
    db.add(a)
    db.flush()

    if volume_kwh:
        db.add(VolumeCommitment(annexe_id=a.id, annual_kwh=volume_kwh))

    db.commit()
    return cadre


# ============================================================
# Prix moyen pondere
# ============================================================


class TestPrixMoyenPondere:
    def test_hphc_weighted_avg(self, db, setup):
        """HP=0.12, HC=0.08 -> avg pondere = (0.12*0.62 + 0.08*0.38) / 1.0 = 0.1048."""
        cadre = _make_cadre_with_pricing(db, setup, pricing_lines=[("HP", 0.12), ("HC", 0.08)], volume_kwh=100000)
        kpis = compute_cadre_kpis(db, cadre)
        expected = (0.12 * 0.62 + 0.08 * 0.38) / (0.62 + 0.38)
        assert abs(kpis["avg_price_eur_mwh"] - expected * 1000) < 0.1

    def test_base_single_price(self, db, setup):
        """BASE=0.10 -> avg = 0.10 (poids 100%)."""
        cadre = _make_cadre_with_pricing(db, setup, pricing_lines=[("BASE", 0.10)], volume_kwh=50000)
        kpis = compute_cadre_kpis(db, cadre)
        assert abs(kpis["avg_price_eur_mwh"] - 100.0) < 0.1

    def test_4postes_weighted(self, db, setup):
        """HPH=0.15, HCH=0.10, HPB=0.12, HCB=0.08 -> avg pondere."""
        cadre = _make_cadre_with_pricing(
            db, setup, pricing_lines=[("HPH", 0.15), ("HCH", 0.10), ("HPB", 0.12), ("HCB", 0.08)], volume_kwh=200000
        )
        kpis = compute_cadre_kpis(db, cadre)
        w = PERIOD_WEIGHTS
        expected = 0.15 * w["HPH"] + 0.10 * w["HCH"] + 0.12 * w["HPB"] + 0.08 * w["HCB"]
        expected /= w["HPH"] + w["HCH"] + w["HPB"] + w["HCB"]
        assert abs(kpis["avg_price_eur_mwh"] - expected * 1000) < 0.1

    def test_5postes_avec_pointe(self, db, setup):
        """HPH+HCH+HPB+HCB+POINTE -> poids pointe = 2%."""
        cadre = _make_cadre_with_pricing(
            db,
            setup,
            pricing_lines=[("HPH", 0.18), ("HCH", 0.12), ("HPB", 0.14), ("HCB", 0.09), ("POINTE", 0.35)],
            volume_kwh=500000,
        )
        kpis = compute_cadre_kpis(db, cadre)
        w = PERIOD_WEIGHTS
        num = 0.18 * w["HPH"] + 0.12 * w["HCH"] + 0.14 * w["HPB"] + 0.09 * w["HCB"] + 0.35 * w["POINTE"]
        den = w["HPH"] + w["HCH"] + w["HPB"] + w["HCB"] + w["POINTE"]
        expected = num / den
        assert abs(kpis["avg_price_eur_mwh"] - expected * 1000) < 0.1

    def test_budget_uses_weighted_price(self, db, setup):
        """Budget = prix_pondere * volume (pas prix arithmetique)."""
        cadre = _make_cadre_with_pricing(db, setup, pricing_lines=[("HP", 0.12), ("HC", 0.08)], volume_kwh=100000)
        kpis = compute_cadre_kpis(db, cadre)
        avg_eur_kwh = kpis["avg_price_eur_mwh"] / 1000
        expected_budget = avg_eur_kwh * 100000
        assert abs(kpis["budget_eur"] - expected_budget) < 1

    def test_no_pricing_zero(self, db, setup):
        """Pas de pricing -> avg = 0, budget = 0."""
        cadre = _make_cadre_with_pricing(db, setup, pricing_lines=[], volume_kwh=100000)
        kpis = compute_cadre_kpis(db, cadre)
        assert kpis["avg_price_eur_mwh"] == 0
        assert kpis["budget_eur"] == 0

    def test_fallback_annual_consumption(self, db, setup):
        """Si pas de volume_commitment -> utilise cadre.annual_consumption_kwh."""
        cadre = _make_cadre_with_pricing(
            db, setup, pricing_lines=[("BASE", 0.10)], volume_kwh=None, annual_consumption_kwh=200000
        )
        kpis = compute_cadre_kpis(db, cadre)
        assert kpis["total_volume_mwh"] == 200.0
