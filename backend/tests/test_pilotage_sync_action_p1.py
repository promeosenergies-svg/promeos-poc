"""Tests Usage Steering P1 — endpoint POST /pilotage/sync-action.

Brief P1 C3 : idempotence stricte + clôture préservée + pattern external_ref.
"""

from __future__ import annotations

import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402
from models import EntiteJuridique, Organisation, Base  # noqa: E402
from main import app  # noqa: E402
from models.v4.action_center_items import ActionCenterItem  # noqa: E402
from models.v4.enums import LifecycleState  # noqa: E402


@pytest.fixture
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(db_engine):
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db_engine, db):
    SessionLocal = sessionmaker(bind=db_engine)

    def _get_test_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    org = Organisation(nom="P1 Org", siren="100000000", actif=True)
    db.add(org)
    db.flush()
    db.add(EntiteJuridique(organisation_id=org.id, nom="EJ", siren="100000000"))
    db.commit()

    app.dependency_overrides[get_db] = _get_test_db
    # Bypass auth via header X-Org-Id (resolve_org_id accepte ce fallback DEMO).
    yield TestClient(app, headers={"X-Org-Id": str(org.id)}), org.id
    app.dependency_overrides.clear()


def _candidate(insight_type="hors_horaires", site_id=42, suffix=""):
    ext_ref = f"pilotage:{insight_type}:site:{site_id}"
    if suffix:
        ext_ref += f":{suffix}"
    return {
        "insight_type": insight_type,
        "site_id": site_id,
        "external_ref": ext_ref,
        "source_url": f"/usages?tab=pilotage&site={site_id}",
        "label_fr": f"Test pilotage {insight_type}",
        "recommended_action_fr": "Action FR test",
        "severity": "high",
    }


class TestSyncActionEndpoint:
    def test_create_then_idempotent(self, client):
        c, _ = client
        payload = _candidate()
        # 1er run : created=true
        r1 = c.post("/api/usages/pilotage/sync-action", json=payload)
        assert r1.status_code == 201, r1.text
        d1 = r1.json()
        assert d1["created"] is True
        assert d1["external_ref"] == payload["external_ref"]
        assert d1["domain"] == "optimisation"
        # 2e run : created=false même item
        r2 = c.post("/api/usages/pilotage/sync-action", json=payload)
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["created"] is False
        assert d2["item_id"] == d1["item_id"]

    def test_closed_action_not_resurrected(self, client, db):
        c, org_id = client
        payload = _candidate(insight_type="base_load", site_id=99)
        r = c.post("/api/usages/pilotage/sync-action", json=payload)
        item_id_str = r.json()["item_id"]
        # Marque manuellement CLOSED (cast str→UUID pour SQLite)
        item_uuid = uuid.UUID(item_id_str)
        item = db.query(ActionCenterItem).filter(ActionCenterItem.id == item_uuid).one()
        from datetime import datetime, timezone

        item.lifecycle_state = LifecycleState.CLOSED.value
        item.closed_at = datetime.now(timezone.utc)
        item.closure_reason = "resolved"
        db.commit()
        # Re-sync : 409, item non ressuscité
        r2 = c.post("/api/usages/pilotage/sync-action", json=payload)
        assert r2.status_code == 409
        d = r2.json()
        assert d["code"] == "ACTION_CLOSED"
        assert d["lifecycle_state"] == "closed"

    def test_invalid_external_ref_rejected(self, client):
        c, _ = client
        bad = _candidate()
        bad["external_ref"] = "billing:anomaly:42"  # mauvais préfixe
        r = c.post("/api/usages/pilotage/sync-action", json=bad)
        assert r.status_code == 422
        assert r.json()["detail"]["code"] == "EXTERNAL_REF_INVALID"

    def test_incomplete_payload_rejected(self, client):
        c, _ = client
        r = c.post(
            "/api/usages/pilotage/sync-action",
            json={"insight_type": "pointe"},  # missing site_id + external_ref
        )
        assert r.status_code == 422
        assert r.json()["detail"]["code"] == "VALIDATION_ERROR"

    def test_distinct_external_refs_create_distinct_items(self, client):
        c, _ = client
        a = _candidate(insight_type="hors_horaires", site_id=1)
        b = _candidate(insight_type="hors_horaires", site_id=2)
        r1 = c.post("/api/usages/pilotage/sync-action", json=a)
        r2 = c.post("/api/usages/pilotage/sync-action", json=b)
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["item_id"] != r2.json()["item_id"]
