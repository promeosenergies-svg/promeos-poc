"""
PROMEOS — Tests resolve_pricing() cascade — 7 tests.
Couvre les 3 niveaux: override annexe > cadre structured > fallback flat.
Phase 6 CONTRATS-V2 QA.
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
from services.contrat_coherence import resolve_pricing


# ── Fixtures ──────────────────────────────────────────────────────


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
    s = Site(portefeuille_id=pf.id, nom="Site A", type=TypeSite.BUREAU, actif=True)
    db.add(s)
    db.flush()
    db.commit()
    return {"org": org, "ej": ej, "site": s}


def _make_cadre(db, setup, **overrides):
    defaults = dict(
        site_id=setup["site"].id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF Entreprises",
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=335),
        notice_period_days=90,
        is_cadre=True,
        contract_type="CADRE",
        entite_juridique_id=setup["ej"].id,
    )
    defaults.update(overrides)
    cadre = EnergyContract(**defaults)
    db.add(cadre)
    db.flush()
    return cadre


def _make_annexe(db, cadre_id, site_id, **overrides):
    defaults = dict(
        contrat_cadre_id=cadre_id,
        site_id=site_id,
        annexe_ref=f"ANX-{site_id}",
        status=ContractStatus.ACTIVE,
    )
    defaults.update(overrides)
    a = ContractAnnexe(**defaults)
    db.add(a)
    db.flush()
    return a


# ============================================================
# Cascade Level 1 — Override annexe
# ============================================================


class TestOverridePricing:
    def test_override_returns_annexe_pricing(self, db, setup):
        """has_price_override=True + pricing_overrides → source='override'."""
        c = _make_cadre(db, setup)
        a = _make_annexe(db, c.id, setup["site"].id, has_price_override=True)
        db.add(ContractPricing(annexe_id=a.id, period_code="BASE", season="ANNUEL", unit_price_eur_kwh=0.14))
        db.commit()
        result = resolve_pricing(db, a)
        assert len(result) == 1
        assert result[0]["source"] == "override"
        assert result[0]["unit_price_eur_kwh"] == 0.14
        assert result[0]["period_code"] == "BASE"

    def test_override_multi_period(self, db, setup):
        """Override avec HP+HC retourne 2 lignes source='override'."""
        c = _make_cadre(db, setup)
        a = _make_annexe(db, c.id, setup["site"].id, has_price_override=True)
        db.add(ContractPricing(annexe_id=a.id, period_code="HP", season="ANNUEL", unit_price_eur_kwh=0.16))
        db.add(ContractPricing(annexe_id=a.id, period_code="HC", season="ANNUEL", unit_price_eur_kwh=0.12))
        db.commit()
        result = resolve_pricing(db, a)
        assert len(result) == 2
        assert all(p["source"] == "override" for p in result)
        codes = {p["period_code"] for p in result}
        assert codes == {"HP", "HC"}


# ============================================================
# Cascade Level 2 — Heritage cadre (grille structuree)
# ============================================================


class TestCadrePricingInheritance:
    def test_cadre_structured_grid(self, db, setup):
        """Annexe sans override → herite grille ContractPricing du cadre, source='cadre'."""
        c = _make_cadre(db, setup)
        db.add(ContractPricing(contract_id=c.id, period_code="HP", season="ANNUEL", unit_price_eur_kwh=0.168))
        db.add(ContractPricing(contract_id=c.id, period_code="HC", season="ANNUEL", unit_price_eur_kwh=0.122))
        a = _make_annexe(db, c.id, setup["site"].id, has_price_override=False)
        db.commit()
        result = resolve_pricing(db, a)
        assert len(result) == 2
        assert all(p["source"] == "cadre" for p in result)
        hp = next(p for p in result if p["period_code"] == "HP")
        assert hp["unit_price_eur_kwh"] == 0.168

    def test_override_beats_cadre_grid(self, db, setup):
        """Override prend priorite meme si cadre a une grille structuree."""
        c = _make_cadre(db, setup)
        db.add(ContractPricing(contract_id=c.id, period_code="HP", season="ANNUEL", unit_price_eur_kwh=0.168))
        db.add(ContractPricing(contract_id=c.id, period_code="HC", season="ANNUEL", unit_price_eur_kwh=0.122))
        a = _make_annexe(db, c.id, setup["site"].id, has_price_override=True)
        db.add(ContractPricing(annexe_id=a.id, period_code="BASE", season="ANNUEL", unit_price_eur_kwh=0.14))
        db.commit()
        result = resolve_pricing(db, a)
        assert len(result) == 1
        assert result[0]["source"] == "override"
        assert result[0]["period_code"] == "BASE"


# ============================================================
# Cascade Level 3 — Fallback colonnes plates
# ============================================================


class TestFallbackFlat:
    def test_fallback_flat_columns(self, db, setup):
        """Pas de ContractPricing → fallback sur colonnes plates du cadre (price_base/hp/hc)."""
        c = _make_cadre(
            db,
            setup,
            price_base_eur_kwh=0.142,
            price_hp_eur_kwh=0.158,
            price_hc_eur_kwh=0.118,
        )
        a = _make_annexe(db, c.id, setup["site"].id, has_price_override=False)
        db.commit()
        result = resolve_pricing(db, a)
        assert len(result) >= 2
        assert all(p["source"] == "cadre" for p in result)
        codes = {p["period_code"] for p in result}
        assert "HP" in codes or "BASE" in codes


# ============================================================
# Edge: aucun prix
# ============================================================


class TestNoPricing:
    def test_empty_when_no_pricing_anywhere(self, db, setup):
        """Ni override ni cadre ni colonnes plates → liste vide."""
        c = _make_cadre(db, setup)
        a = _make_annexe(db, c.id, setup["site"].id, has_price_override=False)
        db.commit()
        result = resolve_pricing(db, a)
        assert result == []

    def test_override_flag_true_but_no_lines(self, db, setup):
        """has_price_override=True mais aucune ligne → fallback sur cadre."""
        c = _make_cadre(db, setup)
        db.add(ContractPricing(contract_id=c.id, period_code="HP", season="ANNUEL", unit_price_eur_kwh=0.168))
        a = _make_annexe(db, c.id, setup["site"].id, has_price_override=True)
        db.commit()
        result = resolve_pricing(db, a)
        # Override flag is True but no override lines → falls through to cadre
        assert len(result) >= 1
        assert all(p["source"] == "cadre" for p in result)
