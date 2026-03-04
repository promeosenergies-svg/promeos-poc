"""
PROMEOS - Tests Sprint V5.0: ROI Summary + Realized Gain
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
    Base,
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    ActionItem,
    ActionSourceType,
    ActionStatus,
    ActionEvent,
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
    db.commit()
    return org, site


def _add_action(
    db,
    org,
    site,
    estimated=0,
    realized=0,
    source_type=ActionSourceType.MANUAL,
    status=ActionStatus.OPEN,
    category=None,
    idx=0,
):
    item = ActionItem(
        org_id=org.id,
        site_id=site.id,
        source_type=source_type,
        source_id=f"roi_{idx}",
        source_key=f"key_{idx}",
        title=f"Action ROI {idx}",
        priority=3,
        status=status,
        estimated_gain_eur=estimated if estimated else None,
        realized_gain_eur=realized if realized else None,
        category=category,
    )
    db.add(item)
    db.flush()
    return item


class TestROISummary:
    def test_roi_summary_empty(self, db, client):
        """ROI summary with no actions returns zeros."""
        org, site = _create_org_site(db)
        resp = client.get("/api/actions/roi_summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_estimated_eur"] == 0.0
        assert data["total_realized_eur"] == 0.0
        assert data["roi_ratio"] == 0.0
        assert data["actions_with_realized"] == 0

    def test_roi_estimated_only(self, db, client):
        """Estimated gains with no realized -> ratio 0."""
        org, site = _create_org_site(db)
        _add_action(db, org, site, estimated=10000, idx=0)
        _add_action(db, org, site, estimated=5000, idx=1)
        db.commit()

        resp = client.get("/api/actions/roi_summary")
        data = resp.json()
        assert data["total_estimated_eur"] == 15000.0
        assert data["total_realized_eur"] == 0.0
        assert data["roi_ratio"] == 0.0
        assert data["actions_with_realized"] == 0

    def test_roi_with_realized(self, db, client):
        """Estimated + realized -> correct ratio."""
        org, site = _create_org_site(db)
        _add_action(db, org, site, estimated=10000, realized=7000, idx=0)
        _add_action(db, org, site, estimated=5000, realized=3000, idx=1)
        db.commit()

        resp = client.get("/api/actions/roi_summary")
        data = resp.json()
        assert data["total_estimated_eur"] == 15000.0
        assert data["total_realized_eur"] == 10000.0
        assert data["roi_ratio"] == pytest.approx(0.6667, abs=0.001)
        assert data["actions_with_realized"] == 2
        assert len(data["top_roi_actions"]) == 2

    def test_false_positive_excluded(self, db, client):
        """false_positive actions are excluded from ROI totals."""
        org, site = _create_org_site(db)
        _add_action(db, org, site, estimated=10000, realized=5000, idx=0)
        _add_action(db, org, site, estimated=8000, realized=4000, status=ActionStatus.FALSE_POSITIVE, idx=1)
        db.commit()

        resp = client.get("/api/actions/roi_summary")
        data = resp.json()
        assert data["total_estimated_eur"] == 10000.0
        assert data["total_realized_eur"] == 5000.0

    def test_by_source_breakdown(self, db, client):
        """by_source breakdown is correct."""
        org, site = _create_org_site(db)
        _add_action(db, org, site, estimated=5000, source_type=ActionSourceType.MANUAL, idx=0)
        _add_action(db, org, site, estimated=3000, source_type=ActionSourceType.INSIGHT, idx=1)
        db.commit()

        resp = client.get("/api/actions/roi_summary")
        data = resp.json()
        assert "manual" in data["by_source"]
        assert "insight" in data["by_source"]
        assert data["by_source"]["manual"]["estimated"] == 5000.0
        assert data["by_source"]["insight"]["estimated"] == 3000.0

    def test_patch_realized_creates_event(self, db, client):
        """PATCH realized_gain_eur creates a 'realized_updated' event."""
        org, site = _create_org_site(db)
        item = _add_action(db, org, site, estimated=10000, idx=0)
        db.commit()

        resp = client.patch(
            f"/api/actions/{item.id}",
            json={
                "realized_gain_eur": 7500.0,
                "realized_at": "2026-06-15",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["realized_gain_eur"] == 7500.0
        assert resp.json()["realized_at"] == "2026-06-15"

        # Check event
        events_resp = client.get(f"/api/actions/{item.id}/events")
        events = events_resp.json()
        realized_events = [e for e in events if e["event_type"] == "realized_updated"]
        assert len(realized_events) == 1
        assert realized_events[0]["new_value"] == "7500.0"
