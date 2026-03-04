"""
PROMEOS - Tests for GET /api/ems/usage_suggest endpoint
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, SiteOperatingSchedule, KBArchetype, KBMappingCode, TypeSite
from models.kb_models import KBConfidence, KBStatus
from database import get_db
from main import app


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
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_site(db, naf_code=None, site_type=TypeSite.BUREAU):
    site = Site(nom="Test Site", type=site_type, actif=True, naf_code=naf_code)
    db.add(site)
    db.flush()
    return site


def _make_archetype(db, code="BUREAU_STANDARD", title="Bureau standard"):
    arch = KBArchetype(
        code=code,
        title=title,
        description="test",
        confidence=KBConfidence.HIGH,
        status=KBStatus.VALIDATED,
    )
    db.add(arch)
    db.flush()
    return arch


class TestUsageSuggest:
    def test_suggest_with_naf(self, client, db_session):
        """Site with NAF code mapped to archetype → source='naf', confidence='high'."""
        arch = _make_archetype(db_session, "BUREAU_STANDARD", "Bureau standard")
        db_session.add(
            KBMappingCode(
                naf_code="70.10Z",
                archetype_id=arch.id,
                confidence=KBConfidence.HIGH,
                priority=1,
            )
        )
        site = _make_site(db_session, naf_code="70.10Z")
        db_session.commit()

        r = client.get("/api/ems/usage_suggest", params={"site_id": site.id})
        assert r.status_code == 200
        data = r.json()
        assert data["archetype_code"] == "BUREAU_STANDARD"
        assert data["archetype_source"] == "naf"
        assert data["confidence"] == "high"
        assert "70.10Z" in data["reasons"][0]

    def test_suggest_without_naf_uses_type(self, client, db_session):
        """Site without NAF code falls back to site type."""
        site = _make_site(db_session, naf_code=None, site_type=TypeSite.BUREAU)
        db_session.commit()

        r = client.get("/api/ems/usage_suggest", params={"site_id": site.id})
        assert r.status_code == 200
        data = r.json()
        assert data["archetype_code"] == "BUREAU_STANDARD"
        assert data["archetype_source"] == "type_fallback"
        assert data["confidence"] == "medium"

    def test_suggest_schedule_for_school(self, client, db_session):
        """School site → has_vacation=True, weekday schedule."""
        site = _make_site(db_session, site_type=TypeSite.ENSEIGNEMENT)
        db_session.commit()

        r = client.get("/api/ems/usage_suggest", params={"site_id": site.id})
        assert r.status_code == 200
        data = r.json()
        assert data["has_vacation"] is True
        assert data["schedule_suggested"]["open_days"] == "0,1,2,3,4"
        assert data["schedule_suggested"]["is_24_7"] is False

    def test_suggest_returns_current_schedule(self, client, db_session):
        """If site has an existing schedule, it's returned in schedule_current."""
        site = _make_site(db_session)
        db_session.add(
            SiteOperatingSchedule(
                site_id=site.id,
                open_days="0,1,2,3,4",
                open_time="09:00",
                close_time="18:00",
                is_24_7=False,
            )
        )
        db_session.commit()

        r = client.get("/api/ems/usage_suggest", params={"site_id": site.id})
        assert r.status_code == 200
        data = r.json()
        assert data["schedule_current"] is not None
        assert data["schedule_current"]["open_time"] == "09:00"

    def test_suggest_unknown_site_404(self, client, db_session):
        """Nonexistent site returns 404."""
        r = client.get("/api/ems/usage_suggest", params={"site_id": 99999})
        assert r.status_code == 404

    def test_suggest_hotel_is_24_7(self, client, db_session):
        """Hotel site → schedule suggests 24/7."""
        site = _make_site(db_session, site_type=TypeSite.HOTEL)
        db_session.commit()

        r = client.get("/api/ems/usage_suggest", params={"site_id": site.id})
        assert r.status_code == 200
        data = r.json()
        assert data["schedule_suggested"]["is_24_7"] is True
