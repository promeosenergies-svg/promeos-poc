"""
PROMEOS — Tests contrat_coherence.py
validate_contrat() 16 regles R1-R16 + resolve_pricing() cascade.
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
from models.contract_v2_models import (
    ContractAnnexe,
    ContractPricing,
    VolumeCommitment,
)
from services.contrat_coherence import validate_contrat, resolve_pricing


# ── Fixtures ──────────────────────────────────────────────────


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
    sites = []
    for name in ["Site A", "Site B", "Site C"]:
        s = Site(portefeuille_id=pf.id, nom=name, type=TypeSite.BUREAU, actif=True)
        db.add(s)
        db.flush()
        sites.append(s)
    db.commit()
    return {"org": org, "ej": ej, "sites": sites}


def _make_cadre(db, setup, **overrides):
    defaults = dict(
        site_id=setup["sites"][0].id,
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
# R1 — Dates obligatoires et coherentes
# ============================================================


class TestR1Dates:
    def test_missing_dates_error(self, db, setup):
        c = _make_cadre(db, setup, start_date=None, end_date=None)
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r1 = [r for r in results if r["rule_id"] == "R1"]
        assert len(r1) == 1
        assert r1[0]["level"] == "error"

    def test_end_before_start_error(self, db, setup):
        c = _make_cadre(db, setup, start_date=date(2027, 1, 1), end_date=date(2025, 1, 1))
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r1 = [r for r in results if r["rule_id"] == "R1"]
        assert len(r1) == 1
        assert r1[0]["level"] == "error"

    def test_valid_dates_ok(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r1 = [r for r in results if r["rule_id"] == "R1"]
        assert len(r1) == 0


# ============================================================
# R2 — Duree contractuelle
# ============================================================


class TestR2Duree:
    def test_spot_36_months_warning(self, db, setup):
        c = _make_cadre(
            db,
            setup,
            offer_indexation=ContractIndexation.INDEXE_SPOT,
            start_date=date(2025, 1, 1),
            end_date=date(2028, 1, 1),
        )
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r2 = [r for r in results if r["rule_id"] == "R2"]
        assert any(r["level"] == "warning" for r in r2)

    def test_fixe_2_months_info(self, db, setup):
        c = _make_cadre(
            db,
            setup,
            offer_indexation=ContractIndexation.FIXE,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 1),
        )
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r2 = [r for r in results if r["rule_id"] == "R2"]
        assert any(r["level"] == "info" for r in r2)

    def test_over_72_months_warning(self, db, setup):
        c = _make_cadre(
            db,
            setup,
            start_date=date(2020, 1, 1),
            end_date=date(2027, 6, 1),
        )
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r2 = [r for r in results if r["rule_id"] == "R2"]
        assert any("72 mois" in r["message"] for r in r2)

    def test_12_months_fixe_ok(self, db, setup):
        c = _make_cadre(
            db,
            setup,
            offer_indexation=ContractIndexation.FIXE,
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1),
        )
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r2 = [r for r in results if r["rule_id"] == "R2"]
        assert len(r2) == 0


# ============================================================
# R3 — Fournisseur CRE
# ============================================================


class TestR3Fournisseur:
    def test_unknown_supplier_info(self, db, setup):
        c = _make_cadre(db, setup, supplier_name="Fournisseur Inconnu SARL")
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r3 = [r for r in results if r["rule_id"] == "R3"]
        assert len(r3) == 1
        assert r3[0]["level"] == "info"

    def test_edf_ok(self, db, setup):
        c = _make_cadre(db, setup, supplier_name="EDF Entreprises")
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r3 = [r for r in results if r["rule_id"] == "R3"]
        assert len(r3) == 0

    def test_engie_ok(self, db, setup):
        c = _make_cadre(db, setup, supplier_name="Engie")
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r3 = [r for r in results if r["rule_id"] == "R3"]
        assert len(r3) == 0


# ============================================================
# R4 — Minimum 1 annexe
# ============================================================


class TestR4MinAnnexe:
    def test_cadre_sans_annexe_warning(self, db, setup):
        c = _make_cadre(db, setup)
        db.commit()
        results = validate_contrat(db, c.id)
        r4 = [r for r in results if r["rule_id"] == "R4"]
        assert len(r4) == 1
        assert r4[0]["level"] == "warning"

    def test_cadre_with_annexe_ok(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r4 = [r for r in results if r["rule_id"] == "R4"]
        assert len(r4) == 0


# ============================================================
# R7 — HP > HC
# ============================================================


class TestR7HpHc:
    def test_hp_less_than_hc_warning(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.add(ContractPricing(contract_id=c.id, period_code="HP", season="ANNUEL", unit_price_eur_kwh=0.10))
        db.add(ContractPricing(contract_id=c.id, period_code="HC", season="ANNUEL", unit_price_eur_kwh=0.15))
        db.commit()
        results = validate_contrat(db, c.id)
        r7 = [r for r in results if r["rule_id"] == "R7" and "HP" in r["message"] and "HC" in r["message"]]
        assert len(r7) == 1
        assert r7[0]["level"] == "warning"

    def test_hp_greater_than_hc_ok(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.add(ContractPricing(contract_id=c.id, period_code="HP", season="ANNUEL", unit_price_eur_kwh=0.18))
        db.add(ContractPricing(contract_id=c.id, period_code="HC", season="ANNUEL", unit_price_eur_kwh=0.12))
        db.commit()
        results = validate_contrat(db, c.id)
        r7 = [
            r for r in results if r["rule_id"] == "R7" and "HP" in r.get("message", "") and "HC" in r.get("message", "")
        ]
        assert len(r7) == 0


# ============================================================
# R9 — Energie / PRM / PCE
# ============================================================


class TestR9EnergiePrmPce:
    def test_annexe_sans_pdl_warning(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r9 = [r for r in results if r["rule_id"] == "R9"]
        assert any("sans PDL/PRM/PCE" in r["message"] for r in r9)


# ============================================================
# R10 — Puissance / segment
# ============================================================


class TestR10Puissance:
    def test_c5_over_36kva_error(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C5", subscribed_power_kva=42.0)
        db.commit()
        results = validate_contrat(db, c.id)
        r10 = [r for r in results if r["rule_id"] == "R10"]
        assert any(r["level"] == "error" for r in r10)

    def test_c5_at_36kva_ok(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C5", subscribed_power_kva=36.0)
        db.commit()
        results = validate_contrat(db, c.id)
        r10 = [r for r in results if r["rule_id"] == "R10" and "C5" in r["message"]]
        assert len(r10) == 0

    def test_c4_over_250kva_warning(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C4", subscribed_power_kva=300.0)
        db.commit()
        results = validate_contrat(db, c.id)
        r10 = [r for r in results if r["rule_id"] == "R10" and "C4" in r["message"]]
        assert len(r10) == 1
        assert r10[0]["level"] == "warning"

    def test_puissance_manquante_multi_postes(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, tariff_option=TariffOptionEnum.HP_HC)
        db.commit()
        results = validate_contrat(db, c.id)
        r10 = [r for r in results if r["rule_id"] == "R10" and "Puissance" in r["message"]]
        assert len(r10) >= 1


# ============================================================
# R11 — Plage dates annexe dans cadre
# ============================================================


class TestR11PlageDates:
    def test_annexe_debut_before_cadre(self, db, setup):
        c = _make_cadre(db, setup, start_date=date(2025, 1, 1), end_date=date(2027, 12, 31))
        _make_annexe(
            db,
            c.id,
            setup["sites"][0].id,
            start_date_override=date(2024, 6, 1),
        )
        db.commit()
        results = validate_contrat(db, c.id)
        r11 = [r for r in results if r["rule_id"] == "R11"]
        assert len(r11) >= 1

    def test_annexe_fin_after_cadre(self, db, setup):
        c = _make_cadre(db, setup, start_date=date(2025, 1, 1), end_date=date(2027, 12, 31))
        _make_annexe(
            db,
            c.id,
            setup["sites"][0].id,
            end_date_override=date(2028, 6, 1),
        )
        db.commit()
        results = validate_contrat(db, c.id)
        r11 = [r for r in results if r["rule_id"] == "R11"]
        assert len(r11) >= 1

    def test_annexe_within_cadre_ok(self, db, setup):
        c = _make_cadre(db, setup, start_date=date(2025, 1, 1), end_date=date(2027, 12, 31))
        _make_annexe(
            db,
            c.id,
            setup["sites"][0].id,
            start_date_override=date(2025, 6, 1),
            end_date_override=date(2027, 6, 1),
        )
        db.commit()
        results = validate_contrat(db, c.id)
        r11 = [r for r in results if r["rule_id"] == "R11"]
        assert len(r11) == 0


# ============================================================
# R12 — ARENH post-VNU
# ============================================================


class TestR12Arenh:
    def test_arenh_post_2025_via_reference_info(self, db, setup):
        """ARENH detected via indexation_reference field."""
        c = _make_cadre(
            db,
            setup,
            offer_indexation=ContractIndexation.INDEXE,
            start_date=date(2026, 1, 1),
            end_date=date(2028, 1, 1),
            indexation_reference="ARENH + spread",
        )
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r12 = [r for r in results if r["rule_id"] == "R12"]
        assert len(r12) == 1
        assert r12[0]["level"] == "info"

    def test_no_arenh_ok(self, db, setup):
        c = _make_cadre(
            db,
            setup,
            offer_indexation=ContractIndexation.FIXE,
            start_date=date(2026, 1, 1),
            end_date=date(2028, 1, 1),
        )
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r12 = [r for r in results if r["rule_id"] == "R12"]
        assert len(r12) == 0


# ============================================================
# R14 — Volume engage
# ============================================================


class TestR14Volume:
    def test_penalty_without_volume_warning(self, db, setup):
        c = _make_cadre(db, setup)
        a = _make_annexe(db, c.id, setup["sites"][0].id)
        db.add(
            VolumeCommitment(
                annexe_id=a.id,
                annual_kwh=0,
                penalty_eur_kwh_above=0.05,
            )
        )
        db.commit()
        results = validate_contrat(db, c.id)
        r14 = [r for r in results if r["rule_id"] == "R14"]
        assert any("negatif ou nul" in r["message"] or "Penalite" in r["message"] for r in r14)


# ============================================================
# R15 — Option tarifaire / segment
# ============================================================


class TestR15OptionSegment:
    def test_cu4_on_c5_error(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C5", tariff_option=TariffOptionEnum.CU4)
        db.commit()
        results = validate_contrat(db, c.id)
        r15 = [r for r in results if r["rule_id"] == "R15"]
        assert any(r["level"] == "error" for r in r15)

    def test_hphc_on_c5_ok(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, segment_enedis="C5", tariff_option=TariffOptionEnum.HP_HC)
        db.commit()
        results = validate_contrat(db, c.id)
        r15 = [r for r in results if r["rule_id"] == "R15" and "incompatible" in r["message"]]
        assert len(r15) == 0

    def test_gaz_with_elec_option_warning(self, db, setup):
        c = _make_cadre(db, setup, energy_type=BillingEnergyType.GAZ)
        _make_annexe(db, c.id, setup["sites"][0].id, tariff_option=TariffOptionEnum.HP_HC)
        db.commit()
        results = validate_contrat(db, c.id)
        r15 = [r for r in results if r["rule_id"] == "R15" and "gaz" in r["message"]]
        assert len(r15) >= 1


# ============================================================
# R16 — Expiration + override sans pricing + indexed sans grille
# ============================================================


class TestR16Expiration:
    def test_expired_warning(self, db, setup):
        c = _make_cadre(db, setup, contract_status=ContractStatus.EXPIRED)
        # Force status
        c.contract_status = ContractStatus.EXPIRED
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r16 = [r for r in results if r["rule_id"] == "R16"]
        assert any("expire" in r["message"].lower() for r in r16)

    def test_override_sans_pricing_error(self, db, setup):
        c = _make_cadre(db, setup)
        _make_annexe(db, c.id, setup["sites"][0].id, has_price_override=True)
        db.commit()
        results = validate_contrat(db, c.id)
        r16 = [r for r in results if r["rule_id"] == "R16" and "override" in r["message"]]
        assert len(r16) == 1
        assert r16[0]["level"] == "error"

    def test_indexed_sans_grille_error(self, db, setup):
        c = _make_cadre(db, setup, offer_indexation=ContractIndexation.INDEXE)
        _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        results = validate_contrat(db, c.id)
        r16 = [r for r in results if r["rule_id"] == "R16" and "indexe" in r["message"].lower()]
        assert len(r16) == 1
        assert r16[0]["level"] == "error"


# ============================================================
# resolve_pricing() cascade
# ============================================================


class TestResolvePricing:
    def test_override_source(self, db, setup):
        c = _make_cadre(db, setup)
        a = _make_annexe(db, c.id, setup["sites"][0].id, has_price_override=True)
        db.add(ContractPricing(annexe_id=a.id, period_code="BASE", season="ANNUEL", unit_price_eur_kwh=0.14))
        db.commit()
        pricing = resolve_pricing(db, a)
        assert len(pricing) == 1
        assert pricing[0]["source"] == "override"
        assert pricing[0]["unit_price_eur_kwh"] == 0.14

    def test_cadre_inheritance(self, db, setup):
        c = _make_cadre(db, setup)
        db.add(ContractPricing(contract_id=c.id, period_code="HP", season="ANNUEL", unit_price_eur_kwh=0.168))
        db.add(ContractPricing(contract_id=c.id, period_code="HC", season="ANNUEL", unit_price_eur_kwh=0.122))
        a = _make_annexe(db, c.id, setup["sites"][0].id, has_price_override=False)
        db.commit()
        pricing = resolve_pricing(db, a)
        assert len(pricing) == 2
        assert all(p["source"] == "cadre" for p in pricing)

    def test_empty_when_no_pricing(self, db, setup):
        c = _make_cadre(db, setup)
        a = _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        pricing = resolve_pricing(db, a)
        assert pricing == []

    def test_override_takes_priority(self, db, setup):
        """Override pricing beats cadre pricing even when cadre has pricing."""
        c = _make_cadre(db, setup)
        db.add(ContractPricing(contract_id=c.id, period_code="HP", season="ANNUEL", unit_price_eur_kwh=0.168))
        a = _make_annexe(db, c.id, setup["sites"][0].id, has_price_override=True)
        db.add(ContractPricing(annexe_id=a.id, period_code="BASE", season="ANNUEL", unit_price_eur_kwh=0.14))
        db.commit()
        pricing = resolve_pricing(db, a)
        assert len(pricing) == 1
        assert pricing[0]["source"] == "override"
        assert pricing[0]["period_code"] == "BASE"


# ============================================================
# Backward compatibility: import from contract_v2_service
# ============================================================


class TestBackwardCompat:
    def test_coherence_check_alias(self, db, setup):
        """coherence_check imported from contract_v2_service still works."""
        from services.contract_v2_service import coherence_check

        c = _make_cadre(db, setup)
        db.commit()
        results = coherence_check(db, c.id)
        assert isinstance(results, list)

    def test_resolve_pricing_alias(self, db, setup):
        """resolve_pricing imported from contract_v2_service still works."""
        from services.contract_v2_service import resolve_pricing as rp

        c = _make_cadre(db, setup)
        a = _make_annexe(db, c.id, setup["sites"][0].id)
        db.commit()
        result = rp(db, a)
        assert isinstance(result, list)
