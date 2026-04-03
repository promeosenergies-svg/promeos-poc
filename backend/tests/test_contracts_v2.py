"""
PROMEOS — Tests Contrats V2 (Cadre + Annexes)
25 tests: modele, heritage, status, coherence, KPIs, API.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
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
    ContractEvent,
)
from database import get_db


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def db():
    """In-memory SQLite session with all tables."""
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
def org_hierarchy(db):
    """Create org → EJ → portefeuille → 3 sites."""
    org = Organisation(nom="TestOrg", siren="123456789", actif=True)
    db.add(org)
    db.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="TestEJ", siren="987654321")
    db.add(ej)
    db.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="TestPF")
    db.add(pf)
    db.flush()

    sites = []
    from models.enums import TypeSite

    for name in ["Paris Bureaux", "Lyon Bureaux", "Toulouse Entrepot"]:
        s = Site(portefeuille_id=pf.id, nom=name, type=TypeSite.BUREAU, actif=True)
        db.add(s)
        db.flush()
        sites.append(s)

    db.commit()
    return {"org": org, "ej": ej, "pf": pf, "sites": sites}


@pytest.fixture
def cadre_with_annexes(db, org_hierarchy):
    """Create a cadre + 2 annexes + pricing + volume."""
    sites = org_hierarchy["sites"]
    ej = org_hierarchy["ej"]

    cadre = EnergyContract(
        site_id=sites[0].id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF Entreprises",
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=60),
        reference_fournisseur="CADRE-TEST-001",
        auto_renew=False,
        notice_period_days=90,
        offer_indexation=ContractIndexation.FIXE,
        contract_status=ContractStatus.EXPIRING,
        is_cadre=True,
        contract_type="CADRE",
        entite_juridique_id=ej.id,
        notice_period_months=3,
    )
    db.add(cadre)
    db.flush()

    # Pricing cadre
    for pc, price in [("HP", 0.168), ("HC", 0.122)]:
        db.add(
            ContractPricing(
                contract_id=cadre.id,
                period_code=pc,
                season="ANNUEL",
                unit_price_eur_kwh=price,
            )
        )
    db.add(
        ContractPricing(
            contract_id=cadre.id,
            period_code="BASE",
            season="ANNUEL",
            subscription_eur_month=145.80,
        )
    )

    # Annexe 1 (herite)
    a1 = ContractAnnexe(
        contrat_cadre_id=cadre.id,
        site_id=sites[0].id,
        annexe_ref="ANX-001",
        tariff_option=TariffOptionEnum.HP_HC,
        subscribed_power_kva=108,
        has_price_override=False,
        status=ContractStatus.ACTIVE,
    )
    db.add(a1)
    db.flush()
    db.add(
        VolumeCommitment(
            annexe_id=a1.id,
            annual_kwh=850000,
            tolerance_pct_up=10,
            tolerance_pct_down=10,
        )
    )

    # Annexe 2 (override)
    a2 = ContractAnnexe(
        contrat_cadre_id=cadre.id,
        site_id=sites[1].id,
        annexe_ref="ANX-002",
        tariff_option=TariffOptionEnum.BASE,
        subscribed_power_kva=60,
        has_price_override=True,
        override_pricing_model="FIXE",
        status=ContractStatus.ACTIVE,
    )
    db.add(a2)
    db.flush()
    db.add(
        ContractPricing(
            annexe_id=a2.id,
            period_code="BASE",
            season="ANNUEL",
            unit_price_eur_kwh=0.138,
        )
    )

    db.commit()
    return {"cadre": cadre, "a1": a1, "a2": a2}


@pytest.fixture
def isolated_client(db, org_hierarchy):
    """TestClient with isolated DB."""

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── Modele ────────────────────────────────────────────────────────


class TestModel:
    def test_cadre_creation_with_annexes(self, db, cadre_with_annexes):
        cadre = cadre_with_annexes["cadre"]
        assert cadre.is_cadre is True
        assert cadre.contract_type == "CADRE"
        assert len(cadre.annexes) == 2

    def test_annexe_unique_per_cadre_site(self, db, cadre_with_annexes):
        """Cannot create 2 annexes for same cadre+site."""
        cadre = cadre_with_annexes["cadre"]
        sites = db.query(Site).all()
        dup = ContractAnnexe(
            contrat_cadre_id=cadre.id,
            site_id=sites[0].id,
            annexe_ref="DUP",
        )
        db.add(dup)
        with pytest.raises(Exception):
            db.flush()
        db.rollback()

    def test_pricing_check_constraint(self, db, cadre_with_annexes):
        """Pricing must have exactly one parent (contract or annexe)."""
        p = ContractPricing(period_code="BASE", season="ANNUEL", unit_price_eur_kwh=0.1)
        db.add(p)
        with pytest.raises(Exception):
            db.flush()
        db.rollback()

    def test_volume_per_annexe(self, db, cadre_with_annexes):
        a1 = cadre_with_annexes["a1"]
        assert a1.volume_commitment is not None
        assert a1.volume_commitment.annual_kwh == 850000


# ── Heritage ──────────────────────────────────────────────────────


class TestHeritage:
    def test_resolve_pricing_inherited(self, db, cadre_with_annexes):
        from services.contract_v2_service import resolve_pricing

        a1 = cadre_with_annexes["a1"]
        pricing = resolve_pricing(db, a1)
        assert len(pricing) >= 2
        assert all(p["source"] == "cadre" for p in pricing)

    def test_resolve_pricing_override(self, db, cadre_with_annexes):
        from services.contract_v2_service import resolve_pricing

        a2 = cadre_with_annexes["a2"]
        pricing = resolve_pricing(db, a2)
        assert len(pricing) == 1
        assert pricing[0]["source"] == "override"
        assert pricing[0]["unit_price_eur_kwh"] == 0.138

    def test_resolve_dates_inherited(self, db, cadre_with_annexes):
        from services.contract_v2_service import resolve_dates

        a1 = cadre_with_annexes["a1"]
        dates = resolve_dates(a1)
        cadre = cadre_with_annexes["cadre"]
        assert dates["start_date"] == cadre.start_date
        assert dates["end_date"] == cadre.end_date

    def test_resolve_dates_override(self, db, cadre_with_annexes):
        from services.contract_v2_service import resolve_dates

        a2 = cadre_with_annexes["a2"]
        a2.start_date_override = date(2025, 1, 1)
        a2.end_date_override = date(2027, 12, 31)
        db.flush()
        dates = resolve_dates(a2)
        assert dates["start_date"] == date(2025, 1, 1)
        assert dates["end_date"] == date(2027, 12, 31)


# ── Status Engine ─────────────────────────────────────────────────


class TestStatus:
    def test_status_active(self):
        from services.contract_v2_service import compute_status

        class FakeContract:
            start_date = date.today() - timedelta(days=100)
            end_date = date.today() + timedelta(days=200)

        assert compute_status(FakeContract()) == ContractStatus.ACTIVE

    def test_status_expiring(self):
        from services.contract_v2_service import compute_status

        class FakeContract:
            start_date = date.today() - timedelta(days=100)
            end_date = date.today() + timedelta(days=60)

        assert compute_status(FakeContract()) == ContractStatus.EXPIRING

    def test_status_expired(self):
        from services.contract_v2_service import compute_status

        class FakeContract:
            start_date = date.today() - timedelta(days=400)
            end_date = date.today() - timedelta(days=10)

        assert compute_status(FakeContract()) == ContractStatus.EXPIRED

    def test_status_draft(self):
        from services.contract_v2_service import compute_status

        class FakeContract:
            start_date = None
            end_date = None

        assert compute_status(FakeContract()) == ContractStatus.DRAFT


# ── Coherence ─────────────────────────────────────────────────────


class TestCoherence:
    def test_coherence_cadre_sans_annexe(self, db, org_hierarchy):
        from services.contract_v2_service import coherence_check

        sites = org_hierarchy["sites"]
        cadre = EnergyContract(
            site_id=sites[0].id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Test",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            is_cadre=True,
            contract_type="CADRE",
        )
        db.add(cadre)
        db.flush()
        results = coherence_check(db, cadre.id)
        r1 = [r for r in results if r["rule_id"] == "R1"]
        assert len(r1) == 1
        assert r1[0]["level"] == "warning"

    def test_coherence_override_sans_pricing(self, db, org_hierarchy):
        from services.contract_v2_service import coherence_check

        sites = org_hierarchy["sites"]
        cadre = EnergyContract(
            site_id=sites[0].id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Test",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            is_cadre=True,
            contract_type="CADRE",
        )
        db.add(cadre)
        db.flush()
        a = ContractAnnexe(
            contrat_cadre_id=cadre.id,
            site_id=sites[0].id,
            has_price_override=True,
            status=ContractStatus.ACTIVE,
        )
        db.add(a)
        db.flush()
        results = coherence_check(db, cadre.id)
        r11 = [r for r in results if r["rule_id"] == "R11"]
        assert len(r11) == 1
        assert r11[0]["level"] == "error"

    def test_coherence_prix_anormal(self, db, org_hierarchy):
        from services.contract_v2_service import coherence_check

        sites = org_hierarchy["sites"]
        cadre = EnergyContract(
            site_id=sites[0].id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Test",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            is_cadre=True,
            contract_type="CADRE",
        )
        db.add(cadre)
        db.flush()
        db.add(
            ContractAnnexe(
                contrat_cadre_id=cadre.id,
                site_id=sites[0].id,
                status=ContractStatus.ACTIVE,
            )
        )
        db.add(
            ContractPricing(
                contract_id=cadre.id,
                period_code="HP",
                season="ANNUEL",
                unit_price_eur_kwh=0.50,
            )
        )
        db.flush()
        results = coherence_check(db, cadre.id)
        r9 = [r for r in results if r["rule_id"] == "R9"]
        assert len(r9) >= 1

    def test_coherence_dates_incoherentes(self, db, org_hierarchy):
        from services.contract_v2_service import coherence_check

        sites = org_hierarchy["sites"]
        cadre = EnergyContract(
            site_id=sites[0].id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="Test",
            start_date=date(2026, 12, 31),
            end_date=date(2025, 1, 1),
            is_cadre=True,
            contract_type="CADRE",
        )
        db.add(cadre)
        db.flush()
        db.add(
            ContractAnnexe(
                contrat_cadre_id=cadre.id,
                site_id=sites[0].id,
                status=ContractStatus.ACTIVE,
            )
        )
        db.flush()
        results = coherence_check(db, cadre.id)
        r8 = [r for r in results if r["rule_id"] == "R8"]
        assert len(r8) == 1
        assert r8[0]["level"] == "error"


# ── KPIs ──────────────────────────────────────────────────────────


class TestKPIs:
    def test_cadre_kpis(self, db, cadre_with_annexes):
        from services.contract_v2_service import compute_cadre_kpis

        cadre = cadre_with_annexes["cadre"]
        kpis = compute_cadre_kpis(db, cadre)
        assert kpis["nb_annexes"] == 2
        assert kpis["avg_price_eur_mwh"] > 0
        assert kpis["total_volume_mwh"] > 0

    def test_portfolio_kpis(self, db, org_hierarchy, cadre_with_annexes):
        from services.contract_v2_service import compute_portfolio_kpis

        org = org_hierarchy["org"]
        kpis = compute_portfolio_kpis(db, org.id)
        assert kpis["total_cadres"] >= 1


# ── API ───────────────────────────────────────────────────────────


class TestAPI:
    def test_suppliers_200(self, isolated_client):
        r = isolated_client.get("/api/contracts/v2/cadres/suppliers")
        assert r.status_code == 200
        data = r.json()
        assert "suppliers" in data
        assert len(data["suppliers"]) >= 10

    def test_list_cadres_200(self, isolated_client):
        r = isolated_client.get("/api/contracts/v2/cadres")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_cadre_201(self, isolated_client, org_hierarchy):
        sites = org_hierarchy["sites"]
        payload = {
            "supplier_name": "EDF Entreprises",
            "energy_type": "elec",
            "start_date": "2026-01-01",
            "end_date": "2028-12-31",
            "annexes": [{"site_id": sites[0].id}],
        }
        r = isolated_client.post("/api/contracts/v2/cadres", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["supplier_name"] == "EDF Entreprises"
        assert data["nb_annexes"] == 1

    def test_import_template(self, isolated_client):
        r = isolated_client.get("/api/contracts/v2/import/template")
        assert r.status_code == 200
        assert "supplier" in r.text
