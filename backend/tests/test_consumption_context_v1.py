"""
PROMEOS — Consumption Context V1 — Security & Error-handling tests
Tests added by V1 audit fixes:
  1. Multi-tenant isolation on /portfolio/summary
  2. get_activity_context returns HTTPException (not dict) on 404
  3. Archetype lookup error is logged, not silenced
  4. Portfolio uses proper join chain (not Site.org_id)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta, timezone
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
    Meter,
    MeterReading,
    TypeSite,
)
from models.energy_models import FrequencyType, EnergyVector
from database import get_db
from main import app


# ═══════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════


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


def _h(org_id: int) -> dict:
    """Header helper for X-Org-Id scoping."""
    return {"X-Org-Id": str(org_id)}


def _create_org_with_site(db, name="Alpha", ville="Paris"):
    """Create a complete org hierarchy: Org → EJ → Portefeuille → Site."""
    org = Organisation(nom=f"Org {name}", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom=f"EJ {name}", siren=f"1{name[:8]:0<8}")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom=f"PF {name}")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom=f"Site {name}",
        type=TypeSite.BUREAU,
        adresse=f"1 rue {name}",
        code_postal="75001",
        ville=ville,
        surface_m2=1000,
        actif=True,
    )
    db.add(site)
    db.flush()
    return org, site


def _add_meter_readings(db, site, days=7, hourly_kwh=10.0):
    """Add a meter with hourly readings for the given site."""
    import uuid

    meter = Meter(
        site_id=site.id,
        meter_id=f"PRM-{uuid.uuid4().hex[:8]}",
        name=f"Meter {site.nom}",
        energy_vector=EnergyVector.ELECTRICITY,
        is_active=True,
    )
    db.add(meter)
    db.flush()
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    t = start
    while t < now:
        db.add(
            MeterReading(
                meter_id=meter.id,
                timestamp=t,
                value_kwh=hourly_kwh,
                frequency=FrequencyType.HOURLY,
            )
        )
        t += timedelta(hours=1)
    db.flush()
    return meter


# ═══════════════════════════════════════════════
# A. Multi-tenant isolation: portfolio/summary
# ═══════════════════════════════════════════════


class TestPortfolioMultiTenant:
    """Portfolio endpoint must only return sites belonging to the requested org."""

    def test_portfolio_scoped_to_org_alpha(self, client, db):
        """Org Alpha sees only its own site in portfolio summary."""
        org_a, site_a = _create_org_with_site(db, "Alpha")
        org_b, site_b = _create_org_with_site(db, "Bravo")
        db.commit()

        resp = client.get("/api/consumption-context/portfolio/summary?days=7", headers=_h(org_a.id))
        assert resp.status_code == 200
        data = resp.json()
        site_ids = [s["site_id"] for s in data["sites"]]
        assert site_a.id in site_ids
        assert site_b.id not in site_ids

    def test_portfolio_scoped_to_org_bravo(self, client, db):
        """Org Bravo sees only its own site in portfolio summary."""
        org_a, site_a = _create_org_with_site(db, "Alpha")
        org_b, site_b = _create_org_with_site(db, "Bravo")
        db.commit()

        resp = client.get("/api/consumption-context/portfolio/summary?days=7", headers=_h(org_b.id))
        assert resp.status_code == 200
        data = resp.json()
        site_ids = [s["site_id"] for s in data["sites"]]
        assert site_b.id in site_ids
        assert site_a.id not in site_ids

    def test_portfolio_nonexistent_org_empty(self, client, db):
        """Non-existent org_id → empty result (0 sites), not crash."""
        _create_org_with_site(db, "Alpha")
        db.commit()

        resp = client.get("/api/consumption-context/portfolio/summary?days=7", headers=_h(999999))
        assert resp.status_code == 200
        data = resp.json()
        assert data["sites_count"] == 0
        assert data["sites"] == []

    def test_portfolio_uses_site_nom_not_name(self, client, db):
        """Portfolio rows must use site.nom (not site.name which doesn't exist)."""
        org_a, site_a = _create_org_with_site(db, "TestNom")
        db.commit()

        resp = client.get("/api/consumption-context/portfolio/summary?days=7", headers=_h(org_a.id))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sites"]) == 1
        assert data["sites"][0]["site_name"] == "Site TestNom"


# ═══════════════════════════════════════════════
# B. Activity context: HTTPException instead of dict error
# ═══════════════════════════════════════════════


class TestActivityContextErrors:
    """get_activity_context must raise HTTPException, not return dict."""

    def test_activity_404_on_missing_site(self, client, db):
        """Non-existent site_id → 404 HTTP error."""
        db.commit()
        resp = client.get("/api/consumption-context/site/999999/activity")
        assert resp.status_code == 404

    def test_activity_happy_path(self, client, db):
        """Valid site → 200 with schedule data."""
        _, site = _create_org_with_site(db, "Happy")
        db.commit()
        resp = client.get(f"/api/consumption-context/site/{site.id}/activity")
        assert resp.status_code == 200
        data = resp.json()
        assert "schedule" in data
        assert "error" not in data


# ═══════════════════════════════════════════════
# C. Source guards: no bare except, proper error handling
# ═══════════════════════════════════════════════


class TestSourceGuards:
    """Verify error-handling patterns in service code."""

    def test_no_bare_except_in_service(self):
        """consumption_context_service.py must not have bare 'except Exception:' blocks."""
        import re

        service_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services", "consumption_context_service.py"
        )
        code = open(service_path).read()
        # Should NOT match bare "except Exception:" with only pass/continue/return None
        bare_excepts = re.findall(r"except\s+Exception\s*:\s*\n\s*(pass|continue)\s*$", code, re.MULTILINE)
        assert len(bare_excepts) == 0, f"Found {len(bare_excepts)} bare except Exception blocks"

    def test_no_dict_error_return_in_service(self):
        """Service functions must not return dict errors — they should raise."""
        service_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services", "consumption_context_service.py"
        )
        code = open(service_path).read()
        assert 'return {"error":' not in code, "Service must not return dict errors"

    def test_logger_exists_in_service(self):
        """Service must use structured logging."""
        service_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services", "consumption_context_service.py"
        )
        code = open(service_path).read()
        assert "logger = logging.getLogger" in code

    def test_portfolio_uses_join_not_org_id(self):
        """Portfolio query must use EntiteJuridique join, not Site.org_id."""
        service_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services", "consumption_context_service.py"
        )
        code = open(service_path).read()
        assert "Site.org_id" not in code, "Site model has no org_id — must use join"
        assert "EntiteJuridique.organisation_id == org_id" in code
