"""
PROMEOS - Tests Sprint V5.0: Action Detail Models + GET Detail Endpoint
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
    Base, Site, Organisation, EntiteJuridique, Portefeuille,
    ActionItem, ActionSourceType, ActionStatus,
    ActionEvent, ActionComment, ActionEvidence,
    TypeSite,
)
from database import get_db
from main import app


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


def _create_org_site(db):
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="123456789")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="P1")
    db.add(pf)
    db.flush()
    site = Site(portefeuille_id=pf.id, nom="Site Test", type=TypeSite.BUREAU, surface_m2=1000, actif=True)
    db.add(site)
    db.flush()
    return org, site


def _create_action(db, org, site, title="Test Action"):
    item = ActionItem(
        org_id=org.id,
        site_id=site.id,
        source_type=ActionSourceType.MANUAL,
        source_id="test_1",
        source_key="key_1",
        title=title,
        priority=2,
        status=ActionStatus.OPEN,
    )
    db.add(item)
    db.flush()
    return item


# ========================================
# Model relationship tests
# ========================================

class TestActionDetailModels:
    def test_create_action_event(self, db):
        """ActionEvent persists and links to ActionItem."""
        org, site = _create_org_site(db)
        action = _create_action(db, org, site)
        event = ActionEvent(
            action_id=action.id,
            event_type="created",
            actor="system",
            new_value="open",
        )
        db.add(event)
        db.commit()

        assert event.id is not None
        assert event.action_id == action.id
        assert event.event_type == "created"
        assert event.actor == "system"
        # Verify relationship
        assert len(action.events) == 1
        assert action.events[0].event_type == "created"

    def test_create_action_comment(self, db):
        """ActionComment persists and links to ActionItem."""
        org, site = _create_org_site(db)
        action = _create_action(db, org, site)
        comment = ActionComment(
            action_id=action.id,
            author="J. Dupont",
            body="RDV planifie avec le prestataire.",
        )
        db.add(comment)
        db.commit()

        assert comment.id is not None
        assert comment.action_id == action.id
        assert comment.author == "J. Dupont"
        assert len(action.comments) == 1

    def test_create_action_evidence(self, db):
        """ActionEvidence persists and links to ActionItem."""
        org, site = _create_org_site(db)
        action = _create_action(db, org, site)
        evidence = ActionEvidence(
            action_id=action.id,
            label="Rapport audit energetique",
            file_url="https://docs.example.com/audit.pdf",
            mime_type="application/pdf",
            uploaded_by="A. Martin",
        )
        db.add(evidence)
        db.commit()

        assert evidence.id is not None
        assert evidence.label == "Rapport audit energetique"
        assert evidence.file_url == "https://docs.example.com/audit.pdf"
        assert len(action.evidence_items) == 1

    def test_new_columns_persist(self, db):
        """New V5.0 columns (category, description, realized_gain_eur, etc.) persist."""
        from datetime import date, datetime
        org, site = _create_org_site(db)
        item = ActionItem(
            org_id=org.id,
            site_id=site.id,
            source_type=ActionSourceType.MANUAL,
            source_id="test_2",
            source_key="key_2",
            title="Action with new fields",
            priority=3,
            status=ActionStatus.OPEN,
            category="energie",
            description="Description detaillee de l'action",
            realized_gain_eur=5000.0,
            realized_at=date(2026, 6, 15),
            closed_at=datetime(2026, 6, 15, 10, 0, 0),
            idempotency_key="idem_abc123",
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        assert item.category == "energie"
        assert item.description == "Description detaillee de l'action"
        assert item.realized_gain_eur == 5000.0
        assert item.realized_at == date(2026, 6, 15)
        assert item.closed_at is not None
        assert item.idempotency_key == "idem_abc123"

    def test_idempotency_key_unique(self, db):
        """idempotency_key unique constraint is enforced."""
        from sqlalchemy.exc import IntegrityError
        org, site = _create_org_site(db)

        item1 = ActionItem(
            org_id=org.id, site_id=site.id,
            source_type=ActionSourceType.MANUAL,
            source_id="a1", source_key="k1",
            title="Action 1", priority=3,
            status=ActionStatus.OPEN,
            idempotency_key="unique_key_1",
        )
        db.add(item1)
        db.commit()

        item2 = ActionItem(
            org_id=org.id, site_id=site.id,
            source_type=ActionSourceType.MANUAL,
            source_id="a2", source_key="k2",
            title="Action 2", priority=3,
            status=ActionStatus.OPEN,
            idempotency_key="unique_key_1",  # duplicate
        )
        db.add(item2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


# ========================================
# GET /api/actions/{action_id} endpoint tests
# ========================================

class TestGetActionDetail:
    def test_detail_returns_full_data(self, db, client):
        """GET /api/actions/{id} returns full detail with sub-resource counts."""
        org, site = _create_org_site(db)
        action = _create_action(db, org, site, title="Action detail test")
        # Add sub-resources
        db.add(ActionComment(action_id=action.id, author="Test", body="Comment 1"))
        db.add(ActionComment(action_id=action.id, author="Test", body="Comment 2"))
        db.add(ActionEvidence(action_id=action.id, label="Piece 1"))
        db.add(ActionEvent(action_id=action.id, event_type="created", actor="system"))
        db.commit()

        resp = client.get(f"/api/actions/{action.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == action.id
        assert data["title"] == "Action detail test"
        assert data["comments_count"] == 2
        assert data["evidence_count"] == 1
        assert data["events_count"] == 1
        # V5.0 fields present
        assert "category" in data
        assert "description" in data
        assert "realized_gain_eur" in data
        assert "realized_at" in data
        assert "closed_at" in data

    def test_detail_404_nonexistent(self, db, client):
        """GET /api/actions/99999 returns 404."""
        _create_org_site(db)
        db.commit()
        resp = client.get("/api/actions/99999")
        assert resp.status_code == 404

    def test_detail_zero_counts(self, db, client):
        """GET detail with no sub-resources returns zero counts."""
        org, site = _create_org_site(db)
        action = _create_action(db, org, site)
        db.commit()

        resp = client.get(f"/api/actions/{action.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["comments_count"] == 0
        assert data["evidence_count"] == 0
        assert data["events_count"] == 0
