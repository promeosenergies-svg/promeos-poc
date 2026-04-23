"""
PROMEOS - Tests Onboarding B2B
Tests complets: API endpoints, classification NAF, auto-provisioning.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Batiment,
    Obligation,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    TypeSite,
    TypeObligation,
    StatutConformite,
)
from database import get_db
from main import app
from services.naf_classifier import classify_naf
from services.onboarding_service import (
    estimate_cvc_power,
    is_tertiaire,
    create_organisation_full,
    create_site_from_data,
    provision_site,
)


# ========================================
# Fixtures
# ========================================


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
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ========================================
# T2 — Classification NAF
# ========================================


class TestNafClassifier:
    """Test classify_naf() pour chaque segment B2B."""

    def test_industrie_manufacturiere(self):
        assert classify_naf("10.12A") == TypeSite.USINE

    def test_construction(self):
        assert classify_naf("41.20A") == TypeSite.USINE

    def test_commerce_gros(self):
        assert classify_naf("46.11Z") == TypeSite.ENTREPOT

    def test_commerce_detail(self):
        assert classify_naf("47.11A") == TypeSite.COMMERCE

    def test_transport_entreposage(self):
        assert classify_naf("52.10A") == TypeSite.ENTREPOT

    def test_hotel_hebergement(self):
        assert classify_naf("55.10Z") == TypeSite.HOTEL

    def test_restauration(self):
        assert classify_naf("56.10A") == TypeSite.HOTEL

    def test_info_communication(self):
        assert classify_naf("62.01Z") == TypeSite.BUREAU

    def test_finance(self):
        assert classify_naf("64.11Z") == TypeSite.BUREAU

    def test_immobilier_generique(self):
        assert classify_naf("68.10Z") == TypeSite.COPROPRIETE

    def test_immobilier_bailleur_social(self):
        assert classify_naf("68.20A") == TypeSite.LOGEMENT_SOCIAL

    def test_immobilier_syndic(self):
        assert classify_naf("68.32A") == TypeSite.COPROPRIETE

    def test_services_entreprises(self):
        assert classify_naf("70.10Z") == TypeSite.BUREAU

    def test_administration_publique(self):
        assert classify_naf("84.11Z") == TypeSite.COLLECTIVITE

    def test_enseignement(self):
        assert classify_naf("85.10Z") == TypeSite.ENSEIGNEMENT

    def test_sante(self):
        assert classify_naf("86.10Z") == TypeSite.SANTE

    def test_action_sociale(self):
        assert classify_naf("87.10A") == TypeSite.SANTE

    def test_code_inconnu_default_bureau(self):
        assert classify_naf("99.99Z") == TypeSite.BUREAU

    def test_none_returns_bureau(self):
        assert classify_naf(None) == TypeSite.BUREAU

    def test_empty_string_returns_bureau(self):
        assert classify_naf("") == TypeSite.BUREAU

    def test_format_sans_point(self):
        assert classify_naf("4711A") == TypeSite.COMMERCE


# ========================================
# T4 — Service onboarding (unit)
# ========================================


class TestOnboardingService:
    """Tests unitaires pour onboarding_service.py"""

    def test_is_tertiaire_bureau(self):
        assert is_tertiaire(TypeSite.BUREAU) is True

    def test_is_tertiaire_usine(self):
        assert is_tertiaire(TypeSite.USINE) is False

    def test_is_tertiaire_copropriete(self):
        assert is_tertiaire(TypeSite.COPROPRIETE) is False

    def test_is_tertiaire_hotel(self):
        assert is_tertiaire(TypeSite.HOTEL) is True

    def test_estimate_cvc_power_positive(self):
        power = estimate_cvc_power(TypeSite.BUREAU, 2000)
        assert power > 0
        # 40-70 W/m2 * 2000 m2 / 1000 = 80-140 kW
        assert 60 <= power <= 160

    def test_create_org_full(self, db_session):
        result = create_organisation_full(
            db=db_session,
            org_nom="Test Corp",
            org_siren="123456789",
            org_type_client="bureau",
            portefeuilles_data=[{"nom": "PF1"}, {"nom": "PF2"}],
        )
        db_session.commit()
        assert result["organisation_id"] is not None
        assert result["entite_juridique_id"] is not None
        assert len(result["portefeuille_ids"]) == 2

    def test_create_org_full_default_portefeuille(self, db_session):
        result = create_organisation_full(
            db=db_session,
            org_nom="Mono PF Corp",
            org_siren="",
            org_type_client="tertiaire",
            portefeuilles_data=[],
        )
        db_session.commit()
        assert len(result["portefeuille_ids"]) == 1
        pf = db_session.get(Portefeuille, result["default_portefeuille_id"])
        assert pf.nom == "Principal"

    def test_create_site_from_data_with_type(self, db_session):
        result = create_organisation_full(
            db=db_session,
            org_nom="Org",
            org_siren="",
            org_type_client="bureau",
            portefeuilles_data=[],
        )
        site = create_site_from_data(
            db=db_session,
            portefeuille_id=result["default_portefeuille_id"],
            nom="Bureau Paris",
            type_site="bureau",
            surface_m2=1500,
        )
        db_session.commit()
        assert site.type == TypeSite.BUREAU
        assert site.surface_m2 == 1500

    def test_create_site_from_data_naf_auto(self, db_session):
        result = create_organisation_full(
            db=db_session,
            org_nom="Org",
            org_siren="",
            org_type_client="bureau",
            portefeuilles_data=[],
        )
        site = create_site_from_data(
            db=db_session,
            portefeuille_id=result["default_portefeuille_id"],
            nom="Hotel Nice",
            type_site=None,
            naf_code="55.10Z",
        )
        db_session.commit()
        assert site.type == TypeSite.HOTEL

    def test_provision_site_creates_batiment(self, db_session):
        result = create_organisation_full(
            db=db_session,
            org_nom="Org",
            org_siren="",
            org_type_client="bureau",
            portefeuilles_data=[],
        )
        site = create_site_from_data(
            db=db_session,
            portefeuille_id=result["default_portefeuille_id"],
            nom="Bureau Lyon",
            type_site="bureau",
            surface_m2=2000,
        )
        prov = provision_site(db_session, site)
        db_session.commit()

        assert prov["batiment_id"] is not None
        assert prov["cvc_power_kw"] > 0
        bat = db_session.query(Batiment).filter_by(site_id=site.id).first()
        assert bat is not None
        assert bat.nom == site.nom

    def test_provision_site_tertiaire_gt1000_creates_decret(self, db_session):
        result = create_organisation_full(
            db=db_session,
            org_nom="Org",
            org_siren="",
            org_type_client="bureau",
            portefeuilles_data=[],
        )
        site = create_site_from_data(
            db=db_session,
            portefeuille_id=result["default_portefeuille_id"],
            nom="Bureau Grand",
            type_site="bureau",
            surface_m2=2000,
        )
        prov = provision_site(db_session, site)
        db_session.commit()

        obls = db_session.query(Obligation).filter_by(site_id=site.id).all()
        types = [o.type for o in obls]
        assert TypeObligation.DECRET_TERTIAIRE in types

    def test_provision_site_small_no_decret(self, db_session):
        result = create_organisation_full(
            db=db_session,
            org_nom="Org",
            org_siren="",
            org_type_client="bureau",
            portefeuilles_data=[],
        )
        site = create_site_from_data(
            db=db_session,
            portefeuille_id=result["default_portefeuille_id"],
            nom="Petit Bureau",
            type_site="bureau",
            surface_m2=500,
        )
        prov = provision_site(db_session, site)
        db_session.commit()

        obls = (
            db_session.query(Obligation)
            .filter_by(
                site_id=site.id,
                type=TypeObligation.DECRET_TERTIAIRE,
            )
            .all()
        )
        assert len(obls) == 0


# ========================================
# T3 — API Onboarding (integration)
# ========================================


class TestOnboardingAPI:
    """Tests integration sur les 3 endpoints /api/onboarding."""

    def test_create_org_complete(self, client):
        r = client.post(
            "/api/onboarding",
            json={
                "organisation": {"nom": "Nexity", "siren": "444346795", "type_client": "copropriete"},
                "portefeuilles": [{"nom": "IDF"}, {"nom": "PACA"}],
                "sites": [
                    {
                        "nom": "Residence Les Lilas",
                        "type": "copropriete",
                        "adresse": "12 rue des Lilas",
                        "code_postal": "75020",
                        "ville": "Paris",
                        "surface_m2": 3500,
                    }
                ],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["organisation_id"] is not None
        assert data["sites_created"] == 1
        assert len(data["portefeuille_ids"]) == 2

    def test_create_org_sans_sites(self, client):
        r = client.post(
            "/api/onboarding",
            json={
                "organisation": {"nom": "Org Vide"},
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["sites_created"] == 0
        assert data["organisation_id"] is not None

    def test_409_if_org_already_exists(self, client):
        # Premier appel: OK
        client.post(
            "/api/onboarding",
            json={
                "organisation": {"nom": "Premiere Org"},
            },
        )
        # Deuxieme appel: 409
        r = client.post(
            "/api/onboarding",
            json={
                "organisation": {"nom": "Deuxieme Org"},
            },
        )
        assert r.status_code == 409
        body = r.json()
        msg = body.get("message") or body.get("detail") or ""
        if isinstance(msg, dict):
            msg = msg.get("message", "")
        assert "existe deja" in msg

    def test_status_before_onboarding(self, client):
        r = client.get("/api/onboarding/status")
        assert r.status_code == 200
        data = r.json()
        assert data["has_organisation"] is False
        assert data["onboarding_complete"] is False
        assert data["total_sites"] == 0

    def test_status_after_onboarding(self, client):
        client.post(
            "/api/onboarding",
            json={
                "organisation": {"nom": "Ma Corp"},
                "sites": [{"nom": "Site 1", "type": "bureau"}],
            },
        )
        r = client.get("/api/onboarding/status")
        data = r.json()
        assert data["has_organisation"] is True
        assert data["organisation_nom"] == "Ma Corp"
        assert data["total_sites"] == 1
        assert data["onboarding_complete"] is True

    def test_import_csv_basic(self, client):
        # D'abord creer une org
        client.post(
            "/api/onboarding",
            json={
                "organisation": {"nom": "CSV Corp"},
            },
        )
        # Puis importer un CSV
        csv_content = (
            "nom,adresse,code_postal,ville,surface_m2,type,naf_code\n"
            "Bureau Paris,10 rue de la Paix,75002,Paris,1200,bureau,\n"
            "Entrepot Lyon,Zone Indus,69001,Lyon,5000,entrepot,\n"
            "Hotel Nice,Promenade,06000,Nice,800,,55.10Z\n"
        )
        r = client.post(
            "/api/onboarding/import-csv",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["imported"] == 3
        assert data["errors"] == 0

    def test_import_csv_naf_auto_classification(self, client):
        client.post(
            "/api/onboarding",
            json={
                "organisation": {"nom": "NAF Corp"},
            },
        )
        csv_content = (
            "nom,adresse,code_postal,ville,surface_m2,type,naf_code\n"
            "Mairie Brest,,29200,Brest,2000,,84.11Z\n"
            "Ecole Rennes,,35000,Rennes,1500,,85.10Z\n"
        )
        r = client.post(
            "/api/onboarding/import-csv",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        data = r.json()
        assert data["imported"] == 2
        # Verifier les types auto-classifies
        site_types = [s["type"] for s in data["sites"]]
        assert "collectivite" in site_types
        assert "enseignement" in site_types

    def test_import_csv_semicolon_delimiter(self, client):
        client.post(
            "/api/onboarding",
            json={
                "organisation": {"nom": "Semicolon Corp"},
            },
        )
        csv_content = (
            "nom;adresse;code_postal;ville;surface_m2;type;naf_code\n"
            "Bureau Marseille;La Canebiere;13001;Marseille;900;bureau;\n"
        )
        r = client.post(
            "/api/onboarding/import-csv",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        data = r.json()
        assert data["imported"] == 1

    def test_import_csv_with_errors(self, client):
        client.post(
            "/api/onboarding",
            json={
                "organisation": {"nom": "Error Corp"},
            },
        )
        csv_content = (
            "nom,adresse,code_postal,ville,surface_m2,type,naf_code\n"
            ",rue vide,,Paris,1000,bureau,\n"
            "Bon Site,rue OK,75001,Paris,500,bureau,\n"
        )
        r = client.post(
            "/api/onboarding/import-csv",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        data = r.json()
        assert data["imported"] == 1
        assert data["errors"] == 1
        assert data["error_details"][0]["row"] == 2

    def test_import_csv_requires_org(self, client):
        csv_content = "nom,type\nTest,bureau\n"
        r = client.post(
            "/api/onboarding/import-csv",
            files={"file": ("sites.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        )
        # V57: resolve_org_id returns 403 when no org resolvable
        assert r.status_code in (400, 403)
