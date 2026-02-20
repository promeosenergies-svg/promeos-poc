"""
PROMEOS — Multi-Org Isolation Tests (Phase A1 Security Patch)
Proves: no cross-org data leakage via patrimoine routes.

Setup: 2 orgs (Alpha, Bravo), each with EJ → Portfolio → Sites.
Every test uses X-Org-Id headers to simulate org context.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Organisation, EntiteJuridique, Portefeuille,
    Site, Compteur, EnergyContract,
    StagingBatch, StagingSite, StagingCompteur,
    StagingStatus, ImportSourceType,
    TypeSite, TypeCompteur, EnergyVector, BillingEnergyType,
)
from database import get_db
from main import app
from services.patrimoine_service import (
    create_staging_batch, run_quality_gate, activate_batch,
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


def _create_two_orgs(db):
    """Create 2 complete org hierarchies: Alpha and Bravo."""
    # Org Alpha
    org_a = Organisation(nom="Org Alpha", type_client="bureau", actif=True, siren="111111111")
    db.add(org_a)
    db.flush()
    ej_a = EntiteJuridique(organisation_id=org_a.id, nom="EJ Alpha", siren="111111111")
    db.add(ej_a)
    db.flush()
    pf_a = Portefeuille(entite_juridique_id=ej_a.id, nom="PF Alpha")
    db.add(pf_a)
    db.flush()
    site_a = Site(
        portefeuille_id=pf_a.id, nom="Site Alpha", type=TypeSite.BUREAU,
        adresse="10 rue Alpha", code_postal="75001", ville="Paris",
        surface_m2=1000, actif=True,
    )
    db.add(site_a)
    db.flush()
    cpt_a = Compteur(
        site_id=site_a.id, type=TypeCompteur.ELECTRICITE,
        numero_serie="CPT-ALPHA-001", meter_id="11111111111111",
        energy_vector=EnergyVector.ELECTRICITY, actif=True,
    )
    db.add(cpt_a)
    db.flush()

    # Org Bravo
    org_b = Organisation(nom="Org Bravo", type_client="industrie", actif=True, siren="222222222")
    db.add(org_b)
    db.flush()
    ej_b = EntiteJuridique(organisation_id=org_b.id, nom="EJ Bravo", siren="222222222")
    db.add(ej_b)
    db.flush()
    pf_b = Portefeuille(entite_juridique_id=ej_b.id, nom="PF Bravo")
    db.add(pf_b)
    db.flush()
    site_b = Site(
        portefeuille_id=pf_b.id, nom="Site Bravo", type=TypeSite.BUREAU,
        adresse="20 rue Bravo", code_postal="69001", ville="Lyon",
        surface_m2=800, actif=True,
    )
    db.add(site_b)
    db.flush()
    cpt_b = Compteur(
        site_id=site_b.id, type=TypeCompteur.GAZ,
        numero_serie="CPT-BRAVO-001", meter_id="22222222222222",
        energy_vector=EnergyVector.GAS, actif=True,
    )
    db.add(cpt_b)
    db.flush()

    db.commit()
    return {
        "org_a": org_a, "ej_a": ej_a, "pf_a": pf_a, "site_a": site_a, "cpt_a": cpt_a,
        "org_b": org_b, "ej_b": ej_b, "pf_b": pf_b, "site_b": site_b, "cpt_b": cpt_b,
    }


def _headers(org_id: int) -> dict:
    """Build X-Org-Id header for a given org."""
    return {"X-Org-Id": str(org_id)}


def _create_batch_for_org(db, org_id):
    """Create a staging batch with 1 site, assigned to the given org."""
    batch = create_staging_batch(
        db, org_id=org_id, user_id=None,
        source_type=ImportSourceType.CSV, mode="import",
    )
    ss = StagingSite(
        batch_id=batch.id, row_number=2, nom="Staged Site",
        adresse="1 rue Test", code_postal="75001", ville="Paris",
        surface_m2=500,
    )
    db.add(ss)
    db.flush()
    sc = StagingCompteur(
        batch_id=batch.id, staging_site_id=ss.id,
        numero_serie="PRM-TEST-001", meter_id="99999999999999",
        type_compteur="electricite", puissance_kw=36,
    )
    db.add(sc)
    db.flush()
    return batch


# ========================================
# Test 1: Import — batch gets correct org_id
# ========================================

class TestImportIsolation:
    def test_import_assigns_correct_org(self, client, db):
        """Import via org Alpha header → batch.org_id == Alpha."""
        data = _create_two_orgs(db)
        csv_content = "nom,adresse,code_postal,ville\nNew Site,5 rue Test,75001,Paris\n"
        resp = client.post(
            "/api/patrimoine/staging/import",
            files={"file": ("test.csv", csv_content.encode(), "text/csv")},
            params={"mode": "express"},
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 200
        batch_id = resp.json()["batch_id"]
        batch = db.query(StagingBatch).get(batch_id)
        assert batch.org_id == data["org_a"].id

    def test_import_cross_org_batch_not_reused(self, client, db):
        """Same file imported by org A then org B → 2 separate batches."""
        data = _create_two_orgs(db)
        csv = "nom,adresse,code_postal,ville\nSite X,1 rue X,75001,Paris\n"

        r1 = client.post(
            "/api/patrimoine/staging/import",
            files={"file": ("test.csv", csv.encode(), "text/csv")},
            headers=_headers(data["org_a"].id),
        )
        r2 = client.post(
            "/api/patrimoine/staging/import",
            files={"file": ("test.csv", csv.encode(), "text/csv")},
            headers=_headers(data["org_b"].id),
        )
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Different batches (content_hash dedup is per-org now)
        assert r1.json()["batch_id"] != r2.json()["batch_id"]


# ========================================
# Test 2: Activation — cross-org denied
# ========================================

class TestActivationIsolation:
    def test_activate_own_batch_own_portfolio(self, client, db):
        """Org A activates its own batch into its own portfolio → 200."""
        data = _create_two_orgs(db)
        batch = _create_batch_for_org(db, data["org_a"].id)
        run_quality_gate(db, batch.id)
        db.commit()

        resp = client.post(
            f"/api/patrimoine/staging/{batch.id}/activate",
            json={"portefeuille_id": data["pf_a"].id},
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 200
        assert resp.json()["sites_created"] >= 1

    def test_activate_cross_org_batch_denied(self, client, db):
        """Org B tries to activate Org A's batch → 403."""
        data = _create_two_orgs(db)
        batch = _create_batch_for_org(db, data["org_a"].id)
        run_quality_gate(db, batch.id)
        db.commit()

        resp = client.post(
            f"/api/patrimoine/staging/{batch.id}/activate",
            json={"portefeuille_id": data["pf_b"].id},
            headers=_headers(data["org_b"].id),
        )
        assert resp.status_code == 403

    def test_activate_into_foreign_portfolio_denied(self, client, db):
        """Org A activates its batch into Org B's portfolio → 403."""
        data = _create_two_orgs(db)
        batch = _create_batch_for_org(db, data["org_a"].id)
        run_quality_gate(db, batch.id)
        db.commit()

        resp = client.post(
            f"/api/patrimoine/staging/{batch.id}/activate",
            json={"portefeuille_id": data["pf_b"].id},
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403


# ========================================
# Test 3: List endpoints — isolation
# ========================================

class TestListIsolation:
    def test_list_sites_isolated(self, client, db):
        """Org A sees only its sites, not Org B's."""
        data = _create_two_orgs(db)
        resp = client.get(
            "/api/patrimoine/sites",
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 200
        sites = resp.json()["sites"]
        site_names = [s["nom"] for s in sites]
        assert "Site Alpha" in site_names
        assert "Site Bravo" not in site_names

    def test_list_sites_org_b(self, client, db):
        """Org B sees only its sites."""
        data = _create_two_orgs(db)
        resp = client.get(
            "/api/patrimoine/sites",
            headers=_headers(data["org_b"].id),
        )
        assert resp.status_code == 200
        sites = resp.json()["sites"]
        site_names = [s["nom"] for s in sites]
        assert "Site Bravo" in site_names
        assert "Site Alpha" not in site_names

    def test_list_compteurs_isolated(self, client, db):
        """Org A sees only its compteurs."""
        data = _create_two_orgs(db)
        resp = client.get(
            "/api/patrimoine/compteurs",
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 200
        compteurs = resp.json()["compteurs"]
        nums = [c["numero_serie"] for c in compteurs]
        assert "CPT-ALPHA-001" in nums
        assert "CPT-BRAVO-001" not in nums

    def test_list_contracts_isolated(self, client, db):
        """Org A sees only its contracts."""
        data = _create_two_orgs(db)
        # Create contracts for each org
        ct_a = EnergyContract(
            site_id=data["site_a"].id, energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
        )
        ct_b = EnergyContract(
            site_id=data["site_b"].id, energy_type=BillingEnergyType.GAZ,
            supplier_name="Engie",
        )
        db.add_all([ct_a, ct_b])
        db.commit()

        resp = client.get(
            "/api/patrimoine/contracts",
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 200
        contracts = resp.json()["contracts"]
        suppliers = [c["supplier_name"] for c in contracts]
        assert "EDF" in suppliers
        assert "Engie" not in suppliers


# ========================================
# Test 4: Update — cross-org denied
# ========================================

class TestUpdateIsolation:
    def test_update_own_site(self, client, db):
        """Org A can update its own site."""
        data = _create_two_orgs(db)
        resp = client.patch(
            f"/api/patrimoine/sites/{data['site_a'].id}",
            json={"nom": "Site Alpha Renamed"},
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 200
        assert resp.json()["nom"] == "Site Alpha Renamed"

    def test_update_other_org_site_denied(self, client, db):
        """Org A tries to update Org B's site → 403."""
        data = _create_two_orgs(db)
        resp = client.patch(
            f"/api/patrimoine/sites/{data['site_b'].id}",
            json={"nom": "Hacked"},
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403

    def test_update_other_org_compteur_denied(self, client, db):
        """Org A tries to update Org B's compteur → 403."""
        data = _create_two_orgs(db)
        resp = client.patch(
            f"/api/patrimoine/compteurs/{data['cpt_b'].id}",
            json={"numero_serie": "HACKED-001"},
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403

    def test_move_compteur_cross_org_denied(self, client, db):
        """Org A tries to move Org B's compteur → 403."""
        data = _create_two_orgs(db)
        resp = client.post(
            f"/api/patrimoine/compteurs/{data['cpt_b'].id}/move",
            json={"target_site_id": data["site_a"].id},
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403


# ========================================
# Test 5: Delete / Archive — cross-org denied
# ========================================

class TestDeleteIsolation:
    def test_archive_own_site(self, client, db):
        """Org A can archive its own site."""
        data = _create_two_orgs(db)
        resp = client.post(
            f"/api/patrimoine/sites/{data['site_a'].id}/archive",
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 200

    def test_archive_other_org_site_denied(self, client, db):
        """Org A tries to archive Org B's site → 403."""
        data = _create_two_orgs(db)
        resp = client.post(
            f"/api/patrimoine/sites/{data['site_b'].id}/archive",
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403

    def test_delete_other_org_contract_denied(self, client, db):
        """Org A tries to delete Org B's contract → 403."""
        data = _create_two_orgs(db)
        ct_b = EnergyContract(
            site_id=data["site_b"].id, energy_type=BillingEnergyType.ELEC,
            supplier_name="Engie",
        )
        db.add(ct_b)
        db.commit()

        resp = client.delete(
            f"/api/patrimoine/contracts/{ct_b.id}",
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403

    def test_detach_other_org_compteur_denied(self, client, db):
        """Org A tries to detach Org B's compteur → 403."""
        data = _create_two_orgs(db)
        resp = client.post(
            f"/api/patrimoine/compteurs/{data['cpt_b'].id}/detach",
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403

    def test_abandon_other_org_batch_denied(self, client, db):
        """Org A tries to abandon Org B's batch → 403."""
        data = _create_two_orgs(db)
        batch_b = _create_batch_for_org(db, data["org_b"].id)
        db.commit()

        resp = client.delete(
            f"/api/patrimoine/staging/{batch_b.id}",
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403


# ========================================
# Test 6: Merge — cross-org denied
# ========================================

class TestMergeIsolation:
    def test_merge_own_sites(self, client, db):
        """Org A can merge two of its own sites."""
        data = _create_two_orgs(db)
        # Create a second site for Alpha
        site_a2 = Site(
            portefeuille_id=data["pf_a"].id, nom="Site Alpha 2",
            type=TypeSite.BUREAU, surface_m2=500, actif=True,
        )
        db.add(site_a2)
        db.commit()

        resp = client.post(
            "/api/patrimoine/sites/merge",
            json={"source_site_id": site_a2.id, "target_site_id": data["site_a"].id},
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 200

    def test_merge_cross_org_denied(self, client, db):
        """Org A tries to merge Org B's site into its own → 403."""
        data = _create_two_orgs(db)
        resp = client.post(
            "/api/patrimoine/sites/merge",
            json={"source_site_id": data["site_b"].id, "target_site_id": data["site_a"].id},
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403


# ========================================
# Test 7: Batch operations — cross-org denied
# ========================================

class TestBatchIsolation:
    def test_batch_summary_cross_org_denied(self, client, db):
        """Org A tries to read Org B's batch summary → 403."""
        data = _create_two_orgs(db)
        batch_b = _create_batch_for_org(db, data["org_b"].id)
        db.commit()

        resp = client.get(
            f"/api/patrimoine/staging/{batch_b.id}/summary",
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403

    def test_batch_rows_cross_org_denied(self, client, db):
        """Org A tries to read Org B's batch rows → 403."""
        data = _create_two_orgs(db)
        batch_b = _create_batch_for_org(db, data["org_b"].id)
        db.commit()

        resp = client.get(
            f"/api/patrimoine/staging/{batch_b.id}/rows",
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403

    def test_batch_validate_cross_org_denied(self, client, db):
        """Org A tries to validate Org B's batch → 403."""
        data = _create_two_orgs(db)
        batch_b = _create_batch_for_org(db, data["org_b"].id)
        db.commit()

        resp = client.post(
            f"/api/patrimoine/staging/{batch_b.id}/validate",
            headers=_headers(data["org_a"].id),
        )
        assert resp.status_code == 403
