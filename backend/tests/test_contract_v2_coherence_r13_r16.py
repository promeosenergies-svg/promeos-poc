"""
Tests unitaires R13-R16 — Coherence contrats V2.
Sources : TURPE 7 CRE 2025-78, grille Enedis, pratiques marche B2B France.
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
from models.contract_v2_models import ContractAnnexe, ContractPricing
from services.contract_v2_service import coherence_check


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
    """Org + EJ + 2 sites minimaux."""
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
    s2 = Site(portefeuille_id=pf.id, nom="Site B", type=TypeSite.BUREAU, actif=True)
    db.add_all([s1, s2])
    db.flush()
    db.commit()
    return {"org": org, "ej": ej, "sites": [s1, s2]}


def _make_cadre(db, setup, **overrides):
    """Helper : cree un cadre + 1 annexe."""
    defaults = dict(
        site_id=setup["sites"][0].id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="Test Supplier",
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
# R13 — Segment / Puissance souscrite incoherent
# ============================================================


class TestR13SegmentPuissance:
    def test_c5_over_36kva_error(self, db, setup):
        """C5 avec PS > 36 kVA -> ERROR."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C5", subscribed_power_kva=42.0)
        db.commit()
        results = coherence_check(db, c.id)
        r13 = [r for r in results if r["rule_id"] == "R13"]
        assert len(r13) == 1
        assert r13[0]["level"] == "error"

    def test_c5_at_36kva_ok(self, db, setup):
        """C5 avec PS = 36 kVA -> pas de R13."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C5", subscribed_power_kva=36.0)
        db.commit()
        results = coherence_check(db, c.id)
        r13 = [r for r in results if r["rule_id"] == "R13"]
        assert len(r13) == 0

    def test_c4_over_250kva_warning(self, db, setup):
        """C4 avec PS > 250 kVA -> WARNING."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C4", subscribed_power_kva=300.0)
        db.commit()
        results = coherence_check(db, c.id)
        r13 = [r for r in results if r["rule_id"] == "R13"]
        assert len(r13) == 1
        assert r13[0]["level"] == "warning"

    def test_c4_at_100kva_ok(self, db, setup):
        """C4 avec PS = 100 kVA -> pas de R13."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C4", subscribed_power_kva=100.0)
        db.commit()
        results = coherence_check(db, c.id)
        r13 = [r for r in results if r["rule_id"] == "R13"]
        assert len(r13) == 0

    def test_no_segment_skip(self, db, setup):
        """Pas de segment -> R13 non evaluee."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, subscribed_power_kva=500.0)
        db.commit()
        results = coherence_check(db, c.id)
        r13 = [r for r in results if r["rule_id"] == "R13"]
        assert len(r13) == 0

    def test_c4_under_37kva_warning(self, db, setup):
        """C4 avec PS = 30 kVA -> WARNING (PS trop basse pour C4)."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C4", subscribed_power_kva=30.0)
        db.commit()
        results = coherence_check(db, c.id)
        r13 = [r for r in results if r["rule_id"] == "R13"]
        assert len(r13) == 1
        assert r13[0]["level"] == "warning"

    def test_no_power_skip(self, db, setup):
        """Pas de PS -> R13 non evaluee."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C5")
        db.commit()
        results = coherence_check(db, c.id)
        r13 = [r for r in results if r["rule_id"] == "R13"]
        assert len(r13) == 0


# ============================================================
# R14 — Option tarifaire / segment incompatible
# ============================================================


class TestR14OptionSegment:
    def test_cu4_on_c5_error(self, db, setup):
        """CU4 est C4, pas C5 -> ERROR."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C5", tariff_option=TariffOptionEnum.CU4)
        db.commit()
        results = coherence_check(db, c.id)
        r14 = [r for r in results if r["rule_id"] == "R14"]
        assert len(r14) == 1
        assert r14[0]["level"] == "error"

    def test_cu4_on_c4_ok(self, db, setup):
        """CU4 sur C4 -> pas de R14."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C4", tariff_option=TariffOptionEnum.CU4)
        db.commit()
        results = coherence_check(db, c.id)
        r14 = [r for r in results if r["rule_id"] == "R14"]
        assert len(r14) == 0

    def test_hphc_on_c5_ok(self, db, setup):
        """HP/HC sur C5 -> pas de R14."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C5", tariff_option=TariffOptionEnum.HP_HC)
        db.commit()
        results = coherence_check(db, c.id)
        r14 = [r for r in results if r["rule_id"] == "R14"]
        assert len(r14) == 0

    def test_base_on_c4_error(self, db, setup):
        """BASE est C5 uniquement -> ERROR sur C4."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C4", tariff_option=TariffOptionEnum.BASE)
        db.commit()
        results = coherence_check(db, c.id)
        r14 = [r for r in results if r["rule_id"] == "R14"]
        assert len(r14) == 1
        assert r14[0]["level"] == "error"

    def test_lu_on_c4_ok(self, db, setup):
        """LU sur C4 -> pas de R14."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C4", tariff_option=TariffOptionEnum.LU)
        db.commit()
        results = coherence_check(db, c.id)
        r14 = [r for r in results if r["rule_id"] == "R14"]
        assert len(r14) == 0

    def test_no_option_skip(self, db, setup):
        """Pas d'option tarifaire -> R14 non evaluee."""
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C4")
        db.commit()
        results = coherence_check(db, c.id)
        r14 = [r for r in results if r["rule_id"] == "R14"]
        assert len(r14) == 0


# ============================================================
# R15 — Duree / modele prix incoherent
# ============================================================


class TestR15DureePrix:
    def test_spot_36_months_warning(self, db, setup):
        """Contrat SPOT de 36 mois -> WARNING."""
        c = _make_cadre(
            db,
            setup,
            offer_indexation=ContractIndexation.INDEXE_SPOT,
            start_date=date(2025, 1, 1),
            end_date=date(2028, 1, 1),
        )
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = coherence_check(db, c.id)
        r15 = [r for r in results if r["rule_id"] == "R15"]
        assert len(r15) == 1
        assert r15[0]["level"] == "warning"

    def test_spot_12_months_ok(self, db, setup):
        """Contrat SPOT de 12 mois -> pas de R15."""
        c = _make_cadre(
            db,
            setup,
            offer_indexation=ContractIndexation.INDEXE_SPOT,
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1),
        )
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = coherence_check(db, c.id)
        r15 = [r for r in results if r["rule_id"] == "R15"]
        assert len(r15) == 0

    def test_fixe_48_months_ok(self, db, setup):
        """Contrat FIXE de 48 mois -> pas de R15."""
        c = _make_cadre(
            db, setup, offer_indexation=ContractIndexation.FIXE, start_date=date(2025, 1, 1), end_date=date(2029, 1, 1)
        )
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = coherence_check(db, c.id)
        r15 = [r for r in results if r["rule_id"] == "R15"]
        assert len(r15) == 0

    def test_fixe_2_months_info(self, db, setup):
        """Contrat FIXE de 2 mois -> INFO."""
        c = _make_cadre(
            db, setup, offer_indexation=ContractIndexation.FIXE, start_date=date(2025, 1, 1), end_date=date(2025, 3, 1)
        )
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = coherence_check(db, c.id)
        r15 = [r for r in results if r["rule_id"] == "R15"]
        assert len(r15) == 1
        assert r15[0]["level"] == "info"


# ============================================================
# R16 — Option tarifaire elec sur contrat gaz
# ============================================================


class TestR16OptionElecSurGaz:
    def test_hphc_on_gaz_warning(self, db, setup):
        """HP/HC sur contrat gaz -> WARNING."""
        c = _make_cadre(db, setup, energy_type=BillingEnergyType.GAZ)
        _make_annexe(db, c.id, setup["sites"][0].id, tariff_option=TariffOptionEnum.HP_HC)
        db.commit()
        results = coherence_check(db, c.id)
        r16 = [r for r in results if r["rule_id"] == "R16"]
        assert len(r16) == 1
        assert r16[0]["level"] == "warning"

    def test_hphc_on_elec_ok(self, db, setup):
        """HP/HC sur contrat elec -> pas de R16."""
        c = _make_cadre(db, setup, energy_type=BillingEnergyType.ELEC)
        _make_annexe(db, c.id, setup["sites"][0].id, tariff_option=TariffOptionEnum.HP_HC)
        db.commit()
        results = coherence_check(db, c.id)
        r16 = [r for r in results if r["rule_id"] == "R16"]
        assert len(r16) == 0

    def test_cu4_on_gaz_warning(self, db, setup):
        """CU4 (TURPE C4) sur contrat gaz -> WARNING."""
        c = _make_cadre(db, setup, energy_type=BillingEnergyType.GAZ)
        _make_annexe(db, c.id, setup["sites"][0].id, tariff_option=TariffOptionEnum.CU4)
        db.commit()
        results = coherence_check(db, c.id)
        r16 = [r for r in results if r["rule_id"] == "R16"]
        assert len(r16) == 1

    def test_no_option_on_gaz_ok(self, db, setup):
        """Pas d'option sur contrat gaz -> pas de R16."""
        c = _make_cadre(db, setup, energy_type=BillingEnergyType.GAZ)
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = coherence_check(db, c.id)
        r16 = [r for r in results if r["rule_id"] == "R16"]
        assert len(r16) == 0
