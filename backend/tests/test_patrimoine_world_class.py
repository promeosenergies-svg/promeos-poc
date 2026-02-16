"""
PROMEOS - Tests Patrimoine WORLD CLASS
Tests for: import_mapping, QA scoring thresholds, CRUD Sites/Compteurs/Contrats.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Site, Organisation, EntiteJuridique, Portefeuille, Compteur,
    EnergyContract, TypeSite, TypeCompteur, EnergyVector, BillingEnergyType,
    StagingBatch, StagingSite, StagingCompteur, QualityFinding,
    StagingStatus, ImportSourceType, QualityRuleSeverity,
)
from database import get_db
from main import app
from services.import_mapping import (
    normalize_header, normalize_headers, normalize_type_site,
    normalize_type_compteur, get_mapping_report,
)
from services.patrimoine_service import (
    create_staging_batch, import_csv_to_staging,
    get_staging_summary, compute_quality_grade,
    QA_THRESHOLD_EXCELLENT, QA_THRESHOLD_BON, QA_THRESHOLD_MOYEN,
)


# ========================================
# Fixtures
# ========================================

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
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_org(db):
    org = Organisation(nom="WC Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ WC", siren="999888777")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF WC")
    db.add(pf)
    db.flush()
    return org, ej, pf


def _create_site(db, pf, nom="Site Test", ville="Paris", cp="75001"):
    site = Site(
        nom=nom, type=TypeSite.BUREAU,
        adresse="1 rue Test", code_postal=cp, ville=ville,
        surface_m2=1500, portefeuille_id=pf.id, actif=True,
    )
    db.add(site)
    db.flush()
    return site


def _create_compteur(db, site, num="CPT-001"):
    c = Compteur(
        site_id=site.id, type=TypeCompteur.ELECTRICITE,
        numero_serie=num, meter_id="12345678901234",
        energy_vector=EnergyVector.ELECTRICITY, actif=True,
    )
    db.add(c)
    db.flush()
    return c


def _create_contract(db, site, supplier="EDF"):
    ct = EnergyContract(
        site_id=site.id, energy_type=BillingEnergyType.ELEC,
        supplier_name=supplier, price_ref_eur_per_kwh=0.18,
        notice_period_days=90,
    )
    db.add(ct)
    db.flush()
    return ct


# ========================================
# TestImportMapping (10 tests)
# ========================================

class TestImportMapping:
    def test_normalize_header_basic(self):
        assert normalize_header("nom") == "nom"
        assert normalize_header("NOM") == "nom"
        assert normalize_header("  Nom  ") == "nom"

    def test_normalize_header_fr_synonyms(self):
        assert normalize_header("adresse_postale") == "adresse"
        assert normalize_header("cp") == "code_postal"
        assert normalize_header("commune") == "ville"
        assert normalize_header("superficie") == "surface_m2"
        assert normalize_header("categorie") == "type"

    def test_normalize_header_en_synonyms(self):
        assert normalize_header("name") == "nom"
        assert normalize_header("address") == "adresse"
        assert normalize_header("city") == "ville"
        assert normalize_header("zip_code") == "code_postal"
        assert normalize_header("area_m2") == "surface_m2"

    def test_normalize_header_meter(self):
        assert normalize_header("prm") == "meter_id"
        assert normalize_header("pdl") == "meter_id"
        assert normalize_header("pce") == "meter_id"
        assert normalize_header("point_de_livraison") == "meter_id"
        assert normalize_header("serial_number") == "numero_serie"

    def test_normalize_header_unknown(self):
        assert normalize_header("foobar_xyz") is None
        assert normalize_header("") is None

    def test_normalize_headers_batch(self):
        mapping, unmapped = normalize_headers(["nom", "cp", "ville", "random_col"])
        assert mapping == {"nom": "nom", "cp": "code_postal", "ville": "ville"}
        assert unmapped == ["random_col"]

    def test_normalize_type_site(self):
        assert normalize_type_site("bureau") == "bureau"
        assert normalize_type_site("bureaux") == "bureau"
        assert normalize_type_site("office") == "bureau"
        assert normalize_type_site("Magasin") == "magasin"
        assert normalize_type_site("logistique") == "entrepot"
        assert normalize_type_site("ehpad") == "sante"
        assert normalize_type_site("ecole") == "enseignement"
        assert normalize_type_site("copro") == "copropriete"

    def test_normalize_type_compteur(self):
        assert normalize_type_compteur("elec") == "electricite"
        assert normalize_type_compteur("electricity") == "electricite"
        assert normalize_type_compteur("gas") == "gaz"
        assert normalize_type_compteur("water") == "eau"

    def test_mapping_report_valid(self):
        report = get_mapping_report(["nom", "adresse", "code postal", "ville", "superficie"])
        assert report["is_valid"] is True
        assert len(report["missing_required"]) == 0
        assert report["coverage_pct"] == 100.0

    def test_mapping_report_missing_required(self):
        report = get_mapping_report(["adresse", "ville", "random"])
        assert report["is_valid"] is False
        assert "nom" in report["missing_required"]
        assert "random" in report["unmapped"]


# ========================================
# TestImportWithFRHeaders (3 tests)
# ========================================

class TestImportWithFRHeaders:
    def test_csv_with_fr_synonyms(self, db):
        batch = create_staging_batch(
            db, org_id=None, user_id=None,
            source_type=ImportSourceType.CSV, mode="import",
        )
        csv_content = (
            "name,address,cp,commune,superficie,categorie,serial_number,fluide,puissance\n"
            "Bureau Lyon,10 rue Garibaldi,69003,Lyon,1800,bureaux,PRM-FR-001,elec,60\n"
        ).encode("utf-8")
        result = import_csv_to_staging(db, batch.id, csv_content)
        assert result["sites_count"] == 1
        assert result["compteurs_count"] == 1

        # Verify normalized values
        ss = db.query(StagingSite).filter(StagingSite.batch_id == batch.id).first()
        assert ss.nom == "Bureau Lyon"
        assert ss.code_postal == "69003"
        assert ss.ville == "Lyon"
        assert ss.surface_m2 == 1800.0
        assert ss.type_site == "bureau"  # "bureaux" → "bureau"

    def test_csv_with_semicolon_delimiter(self, db):
        batch = create_staging_batch(
            db, org_id=None, user_id=None,
            source_type=ImportSourceType.CSV, mode="import",
        )
        csv_content = (
            "nom;adresse;code_postal;ville\n"
            "Hotel Nice;Promenade;06000;Nice\n"
        ).encode("utf-8")
        result = import_csv_to_staging(db, batch.id, csv_content)
        assert result["sites_count"] == 1

    def test_csv_with_mixed_case_headers(self, db):
        batch = create_staging_batch(
            db, org_id=None, user_id=None,
            source_type=ImportSourceType.CSV, mode="import",
        )
        csv_content = (
            "NOM,ADRESSE,CODE_POSTAL,VILLE,SURFACE_M2\n"
            "Entrepot Lille,Zone Ind,59000,Lille,4500\n"
        ).encode("utf-8")
        result = import_csv_to_staging(db, batch.id, csv_content)
        assert result["sites_count"] == 1


# ========================================
# TestQAScoring (6 tests)
# ========================================

class TestQAScoring:
    def test_grade_excellent(self):
        g = compute_quality_grade(90.0)
        assert g["grade"] == "excellent"
        assert g["color"] == "green"
        assert g["gap"] == 0.0

    def test_grade_bon(self):
        g = compute_quality_grade(75.0)
        assert g["grade"] == "bon"
        assert g["color"] == "amber"
        assert g["gap"] == 10.0  # 85 - 75

    def test_grade_moyen(self):
        g = compute_quality_grade(55.0)
        assert g["grade"] == "moyen"
        assert g["color"] == "orange"
        assert g["gap"] == 15.0  # 70 - 55

    def test_grade_insuffisant(self):
        g = compute_quality_grade(30.0)
        assert g["grade"] == "insuffisant"
        assert g["color"] == "red"
        assert g["gap"] == 20.0  # 50 - 30

    def test_thresholds_constants(self):
        assert QA_THRESHOLD_EXCELLENT == 85
        assert QA_THRESHOLD_BON == 70
        assert QA_THRESHOLD_MOYEN == 50

    def test_summary_includes_grade(self, db):
        batch = create_staging_batch(
            db, org_id=None, user_id=None,
            source_type=ImportSourceType.CSV, mode="import",
        )
        # Add 2 clean sites (no findings)
        for i in range(2):
            ss = StagingSite(batch_id=batch.id, row_number=i+1, nom=f"Site {i}",
                            adresse=f"{i} rue", code_postal="75001", ville="Paris")
            db.add(ss)
        db.flush()

        summary = get_staging_summary(db, batch.id)
        assert "quality_grade" in summary
        assert summary["quality_grade"]["grade"] == "excellent"
        assert summary["quality_score"] == 100.0
        assert summary["can_auto_activate"] is True


# ========================================
# TestSiteCRUD (8 tests)
# ========================================

class TestSiteCRUD:
    def test_list_sites(self, client, db):
        org, _, pf = _create_org(db)
        _create_site(db, pf, "Paris HQ")
        _create_site(db, pf, "Lyon Office", "Lyon", "69001")
        db.commit()

        resp = client.get("/api/patrimoine/sites")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_list_sites_filter_ville(self, client, db):
        org, _, pf = _create_org(db)
        _create_site(db, pf, "Paris HQ")
        _create_site(db, pf, "Lyon Office", "Lyon", "69001")
        db.commit()

        resp = client.get("/api/patrimoine/sites", params={"ville": "Lyon"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_get_site_detail(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        _create_compteur(db, site)
        _create_contract(db, site)
        db.commit()

        resp = client.get(f"/api/patrimoine/sites/{site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["nom"] == "Site Test"
        assert data["compteurs_count"] == 1
        assert data["contracts_count"] == 1

    def test_update_site(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        db.commit()

        resp = client.patch(f"/api/patrimoine/sites/{site.id}", json={"nom": "Site Renomme", "ville": "Marseille"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["nom"] == "Site Renomme"
        assert data["ville"] == "Marseille"
        assert "nom" in data["updated"]

    def test_archive_and_restore(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        db.commit()

        # Archive
        resp = client.post(f"/api/patrimoine/sites/{site.id}/archive")
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Site archive"

        # Verify archived
        resp = client.get(f"/api/patrimoine/sites/{site.id}")
        assert resp.json()["actif"] is False

        # Restore
        resp = client.post(f"/api/patrimoine/sites/{site.id}/restore")
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Site restaure"

    def test_merge_sites(self, client, db):
        org, _, pf = _create_org(db)
        source = _create_site(db, pf, "Source")
        target = _create_site(db, pf, "Target")
        _create_compteur(db, source, "CPT-SRC")
        _create_contract(db, source, "Engie")
        db.commit()

        resp = client.post("/api/patrimoine/sites/merge", json={
            "source_site_id": source.id,
            "target_site_id": target.id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["compteurs_moved"] == 1
        assert data["contracts_moved"] == 1
        assert data["source_archived"] is True

    def test_merge_self_rejected(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        db.commit()

        resp = client.post("/api/patrimoine/sites/merge", json={
            "source_site_id": site.id,
            "target_site_id": site.id,
        })
        assert resp.status_code == 400

    def test_site_not_found(self, client, db):
        resp = client.get("/api/patrimoine/sites/99999")
        assert resp.status_code == 404


# ========================================
# TestCompteurOps (4 tests)
# ========================================

class TestCompteurOps:
    def test_list_compteurs(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        _create_compteur(db, site)
        db.commit()

        resp = client.get("/api/patrimoine/compteurs", params={"site_id": site.id})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_move_compteur(self, client, db):
        org, _, pf = _create_org(db)
        site1 = _create_site(db, pf, "Site A")
        site2 = _create_site(db, pf, "Site B")
        c = _create_compteur(db, site1)
        db.commit()

        resp = client.post(f"/api/patrimoine/compteurs/{c.id}/move", json={"target_site_id": site2.id})
        assert resp.status_code == 200
        assert resp.json()["site_id"] == site2.id

    def test_detach_compteur(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        c = _create_compteur(db, site)
        db.commit()

        resp = client.post(f"/api/patrimoine/compteurs/{c.id}/detach")
        assert resp.status_code == 200
        assert resp.json()["actif"] is False

    def test_update_compteur(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        c = _create_compteur(db, site)
        db.commit()

        resp = client.patch(f"/api/patrimoine/compteurs/{c.id}", json={"puissance_souscrite_kw": 100})
        assert resp.status_code == 200
        assert resp.json()["puissance_souscrite_kw"] == 100


# ========================================
# TestContractCRUD (5 tests)
# ========================================

class TestContractCRUD:
    def test_create_contract(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        db.commit()

        resp = client.post("/api/patrimoine/contracts", json={
            "site_id": site.id,
            "energy_type": "elec",
            "supplier_name": "EDF Pro",
            "price_ref_eur_per_kwh": 0.165,
            "start_date": "2025-01-01",
            "end_date": "2027-12-31",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["supplier_name"] == "EDF Pro"
        assert data["price_ref_eur_per_kwh"] == 0.165
        assert data["start_date"] == "2025-01-01"

    def test_list_contracts(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        _create_contract(db, site, "EDF")
        _create_contract(db, site, "Engie")
        db.commit()

        resp = client.get("/api/patrimoine/contracts", params={"site_id": site.id})
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_update_contract(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        ct = _create_contract(db, site)
        db.commit()

        resp = client.patch(f"/api/patrimoine/contracts/{ct.id}", json={
            "supplier_name": "TotalEnergies",
            "price_ref_eur_per_kwh": 0.195,
        })
        assert resp.status_code == 200
        assert resp.json()["supplier_name"] == "TotalEnergies"

    def test_delete_contract(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        ct = _create_contract(db, site)
        db.commit()

        resp = client.delete(f"/api/patrimoine/contracts/{ct.id}")
        assert resp.status_code == 200
        assert "supprime" in resp.json()["detail"]

        # Verify deleted
        resp2 = client.get("/api/patrimoine/contracts", params={"site_id": site.id})
        assert resp2.json()["total"] == 0

    def test_create_contract_invalid_energy(self, client, db):
        org, _, pf = _create_org(db)
        site = _create_site(db, pf)
        db.commit()

        resp = client.post("/api/patrimoine/contracts", json={
            "site_id": site.id,
            "energy_type": "nuclear",
            "supplier_name": "X",
        })
        assert resp.status_code == 400


# ========================================
# TestMappingPreviewEndpoint (2 tests)
# ========================================

class TestMappingPreviewEndpoint:
    def test_mapping_preview(self, client):
        resp = client.post("/api/patrimoine/mapping/preview", json={
            "headers": ["nom", "adresse", "cp", "commune", "superficie"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is True
        assert data["coverage_pct"] == 100.0

    def test_mapping_preview_missing_nom(self, client):
        resp = client.post("/api/patrimoine/mapping/preview", json={
            "headers": ["adresse", "ville", "inconnu"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid"] is False
        assert "nom" in data["missing_required"]
