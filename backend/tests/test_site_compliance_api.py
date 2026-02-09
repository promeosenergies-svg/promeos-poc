"""
PROMEOS - Contract tests for GET /api/sites/{id}/compliance
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
    Base, Site, Obligation, Organisation, EntiteJuridique, Portefeuille,
    Evidence, StatutConformite, TypeObligation, TypeSite,
    TypeEvidence, StatutEvidence,
)
from database import get_db
from main import app


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
    Session = sessionmaker(bind=engine)
    session = Session()
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


def _seed(db):
    org = Organisation(nom="Test Org", type_client="retail", actif=True)
    db.add(org)
    db.commit()
    db.refresh(org)

    entite = EntiteJuridique(organisation_id=org.id, nom="SAS", siren="123456789")
    db.add(entite)
    db.commit()
    db.refresh(entite)

    pf = Portefeuille(entite_juridique_id=entite.id, nom="PF", description="Test")
    db.add(pf)
    db.commit()
    db.refresh(pf)

    site = Site(
        nom="Site Test", type=TypeSite.MAGASIN, portefeuille_id=pf.id,
        surface_m2=2000, actif=True,
    )
    db.add(site)
    db.commit()
    db.refresh(site)

    ob1 = Obligation(
        site_id=site.id, type=TypeObligation.DECRET_TERTIAIRE,
        statut=StatutConformite.NON_CONFORME, avancement_pct=25.0,
        echeance=date(2030, 12, 31),
    )
    ob2 = Obligation(
        site_id=site.id, type=TypeObligation.BACS,
        statut=StatutConformite.CONFORME, avancement_pct=100.0,
        echeance=date(2025, 1, 1),
    )
    ev1 = Evidence(
        site_id=site.id, type=TypeEvidence.AUDIT,
        statut=StatutEvidence.VALIDE, note="Audit OK",
    )
    ev2 = Evidence(
        site_id=site.id, type=TypeEvidence.RAPPORT,
        statut=StatutEvidence.MANQUANT, note="Rapport annuel - Document non fourni",
    )
    db.add_all([ob1, ob2, ev1, ev2])
    db.commit()

    # Recompute snapshot so site fields are set
    from services.compliance_engine import recompute_site
    recompute_site(db, site.id)

    return site


# ========================================
# Contract tests
# ========================================

class TestSiteComplianceEndpoint:
    def test_returns_200_with_correct_shape(self, client, db_session):
        site = _seed(db_session)
        resp = client.get(f"/api/sites/{site.id}/compliance")
        assert resp.status_code == 200

        data = resp.json()
        # Top-level keys
        assert set(data.keys()) == {"site", "batiments", "obligations", "evidences", "explanations", "actions"}

        # Site object has expected fields
        assert data["site"]["id"] == site.id
        assert data["site"]["nom"] == "Site Test"
        assert "statut_decret_tertiaire" in data["site"]
        assert "risque_financier_euro" in data["site"]

    def test_obligations_list(self, client, db_session):
        site = _seed(db_session)
        data = client.get(f"/api/sites/{site.id}/compliance").json()

        assert len(data["obligations"]) == 2
        types = {o["type"] for o in data["obligations"]}
        assert types == {"decret_tertiaire", "bacs"}

        for ob in data["obligations"]:
            assert "id" in ob
            assert "statut" in ob
            assert "avancement_pct" in ob

    def test_evidences_list(self, client, db_session):
        site = _seed(db_session)
        data = client.get(f"/api/sites/{site.id}/compliance").json()

        assert len(data["evidences"]) == 2
        statuses = {e["statut"] for e in data["evidences"]}
        assert "valide" in statuses
        assert "manquant" in statuses

        for ev in data["evidences"]:
            assert "id" in ev
            assert "type" in ev
            assert "note" in ev

    def test_explanations_contain_why(self, client, db_session):
        site = _seed(db_session)
        data = client.get(f"/api/sites/{site.id}/compliance").json()

        assert len(data["explanations"]) >= 2
        for exp in data["explanations"]:
            assert "label" in exp
            assert "statut" in exp
            assert "why" in exp
            assert len(exp["why"]) > 0

    def test_explanations_include_evidence_gaps(self, client, db_session):
        site = _seed(db_session)
        data = client.get(f"/api/sites/{site.id}/compliance").json()

        labels = [e["label"] for e in data["explanations"]]
        assert "Preuves manquantes" in labels

    def test_actions_list(self, client, db_session):
        site = _seed(db_session)
        data = client.get(f"/api/sites/{site.id}/compliance").json()

        assert len(data["actions"]) >= 1
        # Decret tertiaire is NON_CONFORME -> action expected
        assert any("decret tertiaire" in a.lower() for a in data["actions"])
        # Evidence manquante -> action expected
        assert any("preuve" in a.lower() for a in data["actions"])

    def test_404_for_unknown_site(self, client, db_session):
        resp = client.get("/api/sites/9999/compliance")
        assert resp.status_code == 404

    def test_empty_obligations_and_evidences(self, client, db_session):
        """Site with no obligations and no evidences returns defaults."""
        org = Organisation(nom="Org2", type_client="retail", actif=True)
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)

        ej = EntiteJuridique(organisation_id=org.id, nom="EJ2", siren="999999999")
        db_session.add(ej)
        db_session.commit()
        db_session.refresh(ej)

        pf = Portefeuille(entite_juridique_id=ej.id, nom="PF2", description="x")
        db_session.add(pf)
        db_session.commit()
        db_session.refresh(pf)

        site = Site(nom="Empty", type=TypeSite.BUREAU, portefeuille_id=pf.id, surface_m2=500, actif=True)
        db_session.add(site)
        db_session.commit()
        db_session.refresh(site)

        data = client.get(f"/api/sites/{site.id}/compliance").json()
        assert data["obligations"] == []
        assert data["evidences"] == []
        assert data["explanations"] == []
        assert data["actions"] == []
