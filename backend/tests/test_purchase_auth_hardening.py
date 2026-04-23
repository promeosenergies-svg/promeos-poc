"""
PROMEOS — Sprint P1 Achats: Security hardening tests.

Covers:
  1) PATCH /results/{id}/accept requires auth (401 when AUTH required)
  2) POST /seed-demo requires admin + DEMO_SEED_ENABLED (403 / 403)
  3) POST /seed-wow-happy requires admin + DEMO_SEED_ENABLED
  4) POST /seed-wow-dirty requires admin + DEMO_SEED_ENABLED
  5) Seed endpoints return 403 when DEMO_SEED_ENABLED=false
  6) datetime.now(timezone.utc) removed from purchase-related modules
"""

import sys
import os
import inspect

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch
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
    PurchaseAssumptionSet,
    PurchaseScenarioResult,
    PurchaseStrategy,
    PurchaseRecoStatus,
    BillingEnergyType,
    TypeSite,
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


def _create_org_site(db):
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="Test Corp", siren="123456789")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="Default", description="Test PF")
    db.add(pf)
    db.flush()
    site = Site(
        nom="Site A",
        type=TypeSite.BUREAU,
        adresse="1 rue Test",
        code_postal="75001",
        ville="Paris",
        surface_m2=2000,
        portefeuille_id=pf.id,
    )
    db.add(site)
    db.flush()
    return org, site


def _create_result(db, site):
    assumption = PurchaseAssumptionSet(
        site_id=site.id,
        energy_type=BillingEnergyType.ELEC,
        volume_kwh_an=500000,
    )
    db.add(assumption)
    db.flush()
    result = PurchaseScenarioResult(
        assumption_set_id=assumption.id,
        strategy=PurchaseStrategy.FIXE,
        price_eur_per_kwh=0.189,
        total_annual_eur=94500,
        risk_score=15,
        is_recommended=True,
        reco_status=PurchaseRecoStatus.DRAFT,
    )
    db.add(result)
    db.commit()
    return result


# ========================================
# Auth on PATCH /accept
# ========================================


class TestAcceptAuthGuard:
    """PATCH /results/{id}/accept now requires auth (same guard as other endpoints)."""

    def test_accept_has_auth_dependency(self):
        """accept_result endpoint declares get_optional_auth dependency."""
        import routes.purchase as mod

        src = inspect.getsource(mod.accept_result)
        assert "get_optional_auth" in src

    def test_accept_works_in_demo_mode(self, client, db_session):
        """Accept still works in demo mode (auth=None is tolerated)."""
        _, site = _create_org_site(db_session)
        result = _create_result(db_session, site)
        resp = client.patch(f"/api/purchase/results/{result.id}/accept")
        assert resp.status_code == 200
        assert resp.json()["reco_status"] == "accepted"

    @patch("middleware.auth.DEMO_MODE", False)
    def test_accept_401_without_token_when_auth_required(self, client, db_session):
        """Without token and DEMO_MODE=false, returns 401."""
        _, site = _create_org_site(db_session)
        result = _create_result(db_session, site)
        resp = client.patch(f"/api/purchase/results/{result.id}/accept")
        assert resp.status_code == 401


# ========================================
# Auth + DEMO_SEED_ENABLED on seed endpoints
# ========================================


class TestSeedEndpointGuards:
    """POST /seed-* endpoints require admin role + DEMO_SEED_ENABLED=true."""

    def test_seed_demo_has_require_admin(self):
        """seed_demo endpoint declares require_admin dependency."""
        import routes.purchase as mod

        src = inspect.getsource(mod.seed_demo)
        assert "require_admin" in src

    def test_seed_wow_happy_has_require_admin(self):
        """seed_wow_happy_endpoint declares require_admin dependency."""
        import routes.purchase as mod

        src = inspect.getsource(mod.seed_wow_happy_endpoint)
        assert "require_admin" in src

    def test_seed_wow_dirty_has_require_admin(self):
        """seed_wow_dirty_endpoint declares require_admin dependency."""
        import routes.purchase as mod

        src = inspect.getsource(mod.seed_wow_dirty_endpoint)
        assert "require_admin" in src

    @patch("routes.purchase.DEMO_SEED_ENABLED", False)
    def test_seed_demo_403_when_disabled(self, client, db_session):
        """seed-demo returns 403 when DEMO_SEED_ENABLED=false."""
        _create_org_site(db_session)
        resp = client.post("/api/purchase/seed-demo")
        assert resp.status_code == 403
        body = resp.json()
        assert "DEMO_SEED_ENABLED" in (body.get("message") or str(body.get("detail") or ""))

    @patch("routes.purchase.DEMO_SEED_ENABLED", False)
    def test_seed_wow_happy_403_when_disabled(self, client, db_session):
        """seed-wow-happy returns 403 when DEMO_SEED_ENABLED=false."""
        resp = client.post("/api/purchase/seed-wow-happy")
        assert resp.status_code == 403

    @patch("routes.purchase.DEMO_SEED_ENABLED", False)
    def test_seed_wow_dirty_403_when_disabled(self, client, db_session):
        """seed-wow-dirty returns 403 when DEMO_SEED_ENABLED=false."""
        resp = client.post("/api/purchase/seed-wow-dirty")
        assert resp.status_code == 403

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_demo_works_when_enabled_demo_mode(self, client, db_session):
        """seed-demo works when DEMO_SEED_ENABLED=true (in demo mode, admin is lenient)."""
        org, site = _create_org_site(db_session)
        site_b = Site(
            nom="Site B",
            type=TypeSite.ENTREPOT,
            adresse="2 rue Test",
            code_postal="69001",
            ville="Lyon",
            surface_m2=5000,
            portefeuille_id=site.portefeuille_id,
        )
        db_session.add(site_b)
        db_session.commit()
        resp = client.post("/api/purchase/seed-demo")
        assert resp.status_code == 200

    @patch("routes.purchase.DEMO_SEED_ENABLED", True)
    def test_seed_wow_happy_works_when_enabled(self, client, db_session):
        """seed-wow-happy works when DEMO_SEED_ENABLED=true."""
        resp = client.post("/api/purchase/seed-wow-happy")
        assert resp.status_code == 200

    def test_demo_seed_enabled_default_is_false(self):
        """DEMO_SEED_ENABLED defaults to false (secure-by-default)."""
        import routes.purchase as mod

        src = inspect.getsource(mod)
        assert 'get("DEMO_SEED_ENABLED", "false")' in src


# ========================================
# datetime.now(timezone.utc) removal verification
# ========================================


class TestDatetimeCompat:
    """datetime.now(timezone.utc) must be replaced with datetime.now(timezone.utc) in purchase modules."""

    def test_purchase_route_no_utcnow(self):
        import routes.purchase as mod

        src = inspect.getsource(mod)
        assert "utcnow()" not in src

    def test_purchase_service_no_utcnow(self):
        import services.purchase_service as mod

        src = inspect.getsource(mod)
        assert "utcnow()" not in src

    def test_purchase_seed_no_utcnow(self):
        import services.purchase_seed as mod

        src = inspect.getsource(mod)
        assert "utcnow()" not in src

    def test_purchase_seed_wow_no_utcnow(self):
        import services.purchase_seed_wow as mod

        src = inspect.getsource(mod)
        assert "utcnow()" not in src

    def test_energy_route_no_utcnow(self):
        import routes.energy as mod

        src = inspect.getsource(mod)
        assert "utcnow()" not in src
