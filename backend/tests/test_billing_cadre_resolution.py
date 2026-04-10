"""
PROMEOS — Phase 5 billing cascade + org scope tests.

Fixes from PR #190 audit :
  - `find_active_annexe` multi-tenant scope (org_id filter)
  - `_normalized_hp_hc_weights` guards operator typos (70+40 ≠ 100)
  - `_resolve_cadre_weighted_price` returns None on incomplete grids
    instead of silently picking the first price (pointe falsely used as base)
  - `get_reference_price` Priority 0 cascade (cadre annexe > legacy contract)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    BillingEnergyType,
    ContractIndexation,
    TariffOptionEnum,
)
from models.enums import TypeSite, ContractStatus
from models.contract_v2_models import ContratCadre, ContractAnnexe, ContractPricing
from services.billing_service import (
    _normalized_hp_hc_weights,
    _resolve_cadre_weighted_price,
    find_active_annexe,
    get_reference_price,
)


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


def _make_site(db, org_name, siren, site_name):
    org = Organisation(nom=org_name, siren=siren, actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom=f"EJ {org_name}", siren=siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom=f"PF {org_name}")
    db.add(pf)
    db.flush()
    site = Site(portefeuille_id=pf.id, nom=site_name, type=TypeSite.BUREAU, actif=True)
    db.add(site)
    db.flush()
    return org, site


def _make_cadre(db, org_id, ej_id, **overrides):
    defaults = dict(
        org_id=org_id,
        entite_juridique_id=ej_id,
        reference=f"CADRE-{org_id}-INT",
        fournisseur="EDF Entreprises",
        reference_fournisseur=f"REF-{org_id}",
        energie=BillingEnergyType.ELEC,
        date_debut=date(2025, 1, 1),
        date_fin=date(2025, 12, 31),
        type_prix=ContractIndexation.FIXE,
        statut=ContractStatus.ACTIVE,
        poids_hp=62.0,
        poids_hc=38.0,
    )
    defaults.update(overrides)
    cadre = ContratCadre(**defaults)
    db.add(cadre)
    db.flush()
    return cadre


def _make_annexe(db, cadre_id, site_id, with_hp_hc_pricing=True, with_base_pricing=False):
    annexe = ContractAnnexe(
        cadre_id=cadre_id,
        site_id=site_id,
        annexe_ref=f"ANX-{cadre_id}-{site_id}",
        tariff_option=TariffOptionEnum.HP_HC if with_hp_hc_pricing else TariffOptionEnum.BASE,
        has_price_override=True,
        status=ContractStatus.ACTIVE,
    )
    db.add(annexe)
    db.flush()
    if with_hp_hc_pricing:
        db.add(ContractPricing(annexe_id=annexe.id, period_code="HP", season="ANNUEL", unit_price_eur_kwh=0.160))
        db.add(ContractPricing(annexe_id=annexe.id, period_code="HC", season="ANNUEL", unit_price_eur_kwh=0.120))
    if with_base_pricing:
        db.add(ContractPricing(annexe_id=annexe.id, period_code="BASE", season="ANNUEL", unit_price_eur_kwh=0.140))
    db.commit()
    return annexe


# ── 1. HP/HC weights normalization ────────────────────────────────


class TestNormalizedWeights:
    def test_default_market_weights_62_38(self):
        class _Cadre:
            poids_hp = None
            poids_hc = None

        hp, hc = _normalized_hp_hc_weights(_Cadre())
        assert hp == pytest.approx(0.62)
        assert hc == pytest.approx(0.38)
        assert hp + hc == pytest.approx(1.0)

    def test_normalizes_operator_typo_70_plus_40(self):
        """Operator typo : 70+40=110 must normalize to 0.636/0.364, not inflate by 10%."""

        class _Cadre:
            poids_hp = 70.0
            poids_hc = 40.0

        hp, hc = _normalized_hp_hc_weights(_Cadre())
        assert hp + hc == pytest.approx(1.0)
        assert hp == pytest.approx(70.0 / 110.0)
        assert hc == pytest.approx(40.0 / 110.0)

    def test_handles_none_cadre(self):
        hp, hc = _normalized_hp_hc_weights(None)
        assert hp == pytest.approx(0.62)
        assert hc == pytest.approx(0.38)

    def test_zero_total_falls_back_to_default(self):
        class _Cadre:
            poids_hp = 0
            poids_hc = 0

        hp, hc = _normalized_hp_hc_weights(_Cadre())
        assert hp == pytest.approx(0.62)
        assert hc == pytest.approx(0.38)


# ── 2. _resolve_cadre_weighted_price ──────────────────────────────


class TestResolveCadreWeightedPrice:
    def test_base_price_returned_as_is(self, db):
        org, site = _make_site(db, "Org1", "111111111", "Site1")
        cadre = _make_cadre(db, org.id, 1)
        annexe = _make_annexe(db, cadre.id, site.id, with_hp_hc_pricing=False, with_base_pricing=True)

        result = _resolve_cadre_weighted_price(db, annexe)
        assert result is not None
        price, source = result
        assert price == pytest.approx(0.140)
        assert source == f"cadre_annexe:{annexe.id}"

    def test_hp_hc_weighted_average(self, db):
        """0.160 HP * 0.62 + 0.120 HC * 0.38 = 0.1448."""
        org, site = _make_site(db, "Org2", "222222222", "Site2")
        cadre = _make_cadre(db, org.id, 1)
        annexe = _make_annexe(db, cadre.id, site.id, with_hp_hc_pricing=True)

        result = _resolve_cadre_weighted_price(db, annexe)
        assert result is not None
        price, source = result
        expected = 0.160 * 0.62 + 0.120 * 0.38
        assert price == pytest.approx(expected, abs=1e-5)

    def test_incomplete_grid_returns_none(self, db):
        """Only HP available (no HC, no BASE) must return None, not an arbitrary price."""
        org, site = _make_site(db, "Org3", "333333333", "Site3")
        cadre = _make_cadre(db, org.id, 1)
        annexe = ContractAnnexe(
            cadre_id=cadre.id,
            site_id=site.id,
            annexe_ref="ANX-partial",
            has_price_override=True,
            status=ContractStatus.ACTIVE,
        )
        db.add(annexe)
        db.flush()
        db.add(ContractPricing(annexe_id=annexe.id, period_code="HP", season="ANNUEL", unit_price_eur_kwh=0.16))
        db.add(ContractPricing(annexe_id=annexe.id, period_code="P", season="ANNUEL", unit_price_eur_kwh=0.25))
        db.commit()

        result = _resolve_cadre_weighted_price(db, annexe)
        assert result is None, (
            "Incomplete grid must fall through to next priority source, "
            "not silently pick a pointe price as the reference."
        )


# ── 3. Multi-tenant org scope ─────────────────────────────────────


class TestOrgScopeIsolation:
    def test_find_active_annexe_respects_org_id(self, db):
        """Two cadres on the same site_id (different orgs) must not leak cross-tenant."""
        org_a, site_a = _make_site(db, "OrgA", "100000001", "SiteA")
        org_b, site_b = _make_site(db, "OrgB", "200000002", "SiteB")

        cadre_a = _make_cadre(db, org_a.id, 1, reference_fournisseur="REF-A")
        cadre_b = _make_cadre(db, org_b.id, 2, reference_fournisseur="REF-B")
        annexe_a = _make_annexe(db, cadre_a.id, site_a.id, with_base_pricing=True)
        annexe_b = _make_annexe(db, cadre_b.id, site_b.id, with_base_pricing=True)

        # Query with org_a scope must NOT return annexe_b
        found_for_a = find_active_annexe(db, site_a.id, "elec", date(2025, 6, 1), org_id=org_a.id)
        assert found_for_a is not None
        assert found_for_a.id == annexe_a.id

        # Query with org_b scope on site_a must return None (org_a owns that site)
        found_wrong_org = find_active_annexe(db, site_a.id, "elec", date(2025, 6, 1), org_id=org_b.id)
        assert found_wrong_org is None, "Annexe leaked across orgs — multi-tenant isolation broken"

    def test_get_reference_price_auto_resolves_org_id_from_site(self, db):
        """get_reference_price() derives org_id from the site without caller passing it."""
        org_a, site_a = _make_site(db, "OrgCheck", "300000003", "SiteCheck")
        cadre = _make_cadre(db, org_a.id, 1)
        _make_annexe(db, cadre.id, site_a.id, with_base_pricing=True)

        price, source = get_reference_price(db, site_a.id, "elec", date(2025, 6, 1), date(2025, 6, 30))
        assert price == pytest.approx(0.140)
        assert source.startswith("cadre_annexe:")
