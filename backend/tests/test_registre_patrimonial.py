"""
PROMEOS — Tests Bloc 0: Registre patrimonial & contractuel
Vérifie le modèle enrichi, le seed, la réconciliation, et les KPIs.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import date, timedelta

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Batiment,
    DeliveryPoint,
    DeliveryPointEnergyType,
    EnergyContract,
    BillingEnergyType,
    ContractIndexation,
    ContractDeliveryPoint,
    TypeSite,
)


@pytest.fixture(scope="module")
def db():
    """In-memory SQLite for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def seed(db):
    """Seed minimal registre patrimonial & contractuel."""
    org = Organisation(nom="Test Corp", siren="111222333", actif=True)
    db.add(org)
    db.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="Test SAS", siren="111222333", siret="11122233300010")
    db.add(ej)
    db.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="Bureaux Test")
    db.add(pf)
    db.flush()

    site = Site(
        portefeuille_id=pf.id,
        nom="Site Paris Test",
        type=TypeSite.BUREAU,
        adresse="1 Rue Test",
        ville="Paris",
        code_postal="75001",
        surface_m2=2000,
        latitude=48.86,
        longitude=2.35,
        siret="11122233300010",
        actif=True,
    )
    db.add(site)
    db.flush()

    dp1 = DeliveryPoint(
        code="12345678901234", energy_type=DeliveryPointEnergyType.ELEC, site_id=site.id, data_source="demo"
    )
    dp2 = DeliveryPoint(
        code="98765432109876", energy_type=DeliveryPointEnergyType.GAZ, site_id=site.id, data_source="demo"
    )
    db.add_all([dp1, dp2])
    db.flush()

    ct = EnergyContract(
        site_id=site.id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF",
        start_date=date(2024, 1, 1),
        end_date=date.today() + timedelta(days=180),
        price_ref_eur_per_kwh=0.145,
        fixed_fee_eur_per_month=80,
        notice_period_days=90,
        auto_renew=True,
        offer_indexation=ContractIndexation.FIXE,
        # V-registre fields
        reference_fournisseur="EDF-2024-001E",
        date_signature=date(2023, 11, 15),
        conditions_particulieres="Clause de sortie anticipée à 6 mois",
        document_url="https://docs.example.com/contrat-edf-2024.pdf",
    )
    db.add(ct)
    db.flush()

    # Link DP to contract
    cdp = ContractDeliveryPoint(contract_id=ct.id, delivery_point_id=dp1.id)
    db.add(cdp)
    db.commit()

    return {"org": org, "ej": ej, "pf": pf, "site": site, "dp1": dp1, "dp2": dp2, "ct": ct}


# ========================================
# Tests: Modèle enrichi
# ========================================


class TestContractModel:
    def test_reference_fournisseur(self, db, seed):
        ct = db.query(EnergyContract).first()
        assert ct.reference_fournisseur == "EDF-2024-001E"

    def test_date_signature(self, db, seed):
        ct = db.query(EnergyContract).first()
        assert ct.date_signature == date(2023, 11, 15)

    def test_conditions_particulieres(self, db, seed):
        ct = db.query(EnergyContract).first()
        assert "Clause de sortie" in ct.conditions_particulieres

    def test_document_url(self, db, seed):
        ct = db.query(EnergyContract).first()
        assert ct.document_url.startswith("https://")


# ========================================
# Tests: Table N-N contract_delivery_points
# ========================================


class TestContractDeliveryPoints:
    def test_table_exists(self, db, seed):
        engine = db.get_bind()
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "contract_delivery_points" in tables

    def test_link_created(self, db, seed):
        links = db.query(ContractDeliveryPoint).all()
        assert len(links) >= 1

    def test_link_correct(self, db, seed):
        link = db.query(ContractDeliveryPoint).first()
        assert link.contract_id == seed["ct"].id
        assert link.delivery_point_id == seed["dp1"].id

    def test_contract_has_delivery_points(self, db, seed):
        ct = db.query(EnergyContract).first()
        assert len(ct.delivery_points) >= 1
        assert ct.delivery_points[0].code == "12345678901234"

    def test_dp_has_contracts(self, db, seed):
        dp = db.query(DeliveryPoint).filter_by(code="12345678901234").first()
        assert len(dp.contracts) >= 1
        assert dp.contracts[0].supplier_name == "EDF"


# ========================================
# Tests: Hiérarchie complète
# ========================================


class TestHierarchy:
    def test_org_to_ej(self, db, seed):
        org = seed["org"]
        assert len(org.entites_juridiques) == 1
        assert org.entites_juridiques[0].siren == "111222333"

    def test_ej_to_portefeuille(self, db, seed):
        ej = seed["ej"]
        assert len(ej.portefeuilles) == 1

    def test_portefeuille_to_site(self, db, seed):
        pf = seed["pf"]
        assert len(pf.sites) == 1

    def test_site_to_contract(self, db, seed):
        site = seed["site"]
        assert len(site.energy_contracts) >= 1

    def test_site_to_delivery_points(self, db, seed):
        site = seed["site"]
        assert len(site.delivery_points) == 2

    def test_full_chain(self, db, seed):
        """Org → EJ → PF → Site → DP → Contract : la chaine complete fonctionne."""
        org = seed["org"]
        ej = org.entites_juridiques[0]
        pf = ej.portefeuilles[0]
        site = pf.sites[0]
        dps = site.delivery_points
        contracts = site.energy_contracts
        assert site.nom == "Site Paris Test"
        assert len(dps) == 2
        assert len(contracts) >= 1
        # Contract linked to DP
        ct = contracts[0]
        assert len(ct.delivery_points) >= 1


# ========================================
# Tests: Complétude
# ========================================


class TestCompleteness:
    def test_completeness_function_exists(self, db, seed):
        """_compute_site_completeness is importable from routes."""
        # Import inline to avoid circular
        import importlib

        mod = importlib.import_module("routes.patrimoine")
        assert hasattr(mod, "_compute_site_completeness")

    def test_completeness_full_site(self, db, seed):
        from routes.patrimoine import _compute_site_completeness

        site = seed["site"]
        result = _compute_site_completeness(db, site, [site.id])
        assert result["score"] >= 80  # All fields filled
        assert result["level"] == "complet"
        assert len(result["missing"]) <= 2
