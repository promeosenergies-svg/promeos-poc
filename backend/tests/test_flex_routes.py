"""
PROMEOS — Tests routes Flex (assets CRUD, assessment, idempotence).
Sprint B : couverture des endpoints REST.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from models import Base, Organisation, EntiteJuridique, Portefeuille, Site
from database import get_db


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def db():
    """In-memory SQLite session."""
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
def org_with_site(db):
    """Cree org -> EJ -> portefeuille -> site."""
    from models.enums import TypeSite

    org = Organisation(nom="FlexOrg", siren="777888999", actif=True)
    db.add(org)
    db.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="FlexEJ", siren="111222333")
    db.add(ej)
    db.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="FlexPF")
    db.add(pf)
    db.flush()

    site = Site(portefeuille_id=pf.id, nom="Site Flex Test", type=TypeSite.BUREAU, actif=True)
    db.add(site)
    db.flush()

    db.commit()
    return {"org": org, "site": site, "pf": pf}


@pytest.fixture
def client(db, org_with_site):
    """TestClient avec DB isolee."""

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── Tests Assets List ─────────────────────────────────────────────


class TestFlexAssetsList:
    def test_list_assets_empty(self, client):
        """GET /flex/assets retourne liste vide."""
        r = client.get("/api/flex/assets")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 0
        assert data["assets"] == []

    def test_list_assets_filter_by_site(self, client, org_with_site):
        """GET /flex/assets?site_id=X retourne liste filtree."""
        site_id = org_with_site["site"].id
        r = client.get(f"/api/flex/assets?site_id={site_id}")
        assert r.status_code == 200
        assert r.json()["total"] == 0


# ── Tests Assets Create ───────────────────────────────────────────


class TestFlexAssetsCreate:
    def _asset_payload(self, site_id):
        return {
            "site_id": site_id,
            "asset_type": "hvac",
            "label": "CTA Principale",
            "power_kw": 45.0,
            "is_controllable": True,
            "control_method": "gtb",
            "confidence": "medium",
        }

    def test_create_asset_200(self, client, org_with_site):
        """POST /flex/assets cree un asset."""
        payload = self._asset_payload(org_with_site["site"].id)
        r = client.post("/api/flex/assets", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["label"] == "CTA Principale"
        assert data["asset_type"] == "hvac"
        assert data["power_kw"] == 45.0

    def test_create_asset_confidence_high_requires_source(self, client, org_with_site):
        """POST /flex/assets avec confidence=high sans data_source retourne 400."""
        payload = self._asset_payload(org_with_site["site"].id)
        payload["confidence"] = "high"
        payload.pop("control_method", None)
        r = client.post("/api/flex/assets", json=payload)
        assert r.status_code == 400

    def test_create_asset_then_list(self, client, org_with_site):
        """Create asset puis verifier qu'il apparait dans la liste."""
        site_id = org_with_site["site"].id
        payload = self._asset_payload(site_id)
        r = client.post("/api/flex/assets", json=payload)
        assert r.status_code == 200

        r2 = client.get(f"/api/flex/assets?site_id={site_id}")
        assert r2.status_code == 200
        assert r2.json()["total"] >= 1


# ── Tests Assets Update ───────────────────────────────────────────


class TestFlexAssetsUpdate:
    def test_update_asset_404(self, client):
        """PATCH /flex/assets/99999 retourne 404."""
        r = client.patch("/api/flex/assets/99999", json={"label": "Updated"})
        assert r.status_code == 404

    def test_update_asset_ok(self, client, org_with_site):
        """PATCH /flex/assets/{id} met a jour un champ."""
        # Create first
        payload = {
            "site_id": org_with_site["site"].id,
            "asset_type": "battery",
            "label": "Batterie Li-ion",
            "power_kw": 100,
            "energy_kwh": 400,
            "is_controllable": True,
        }
        r = client.post("/api/flex/assets", json=payload)
        assert r.status_code == 200
        asset_id = r.json()["id"]

        # Update
        r2 = client.patch(f"/api/flex/assets/{asset_id}", json={"label": "Batterie Li-ion v2"})
        assert r2.status_code == 200
        assert r2.json()["label"] == "Batterie Li-ion v2"


# ── Tests Assessment ──────────────────────────────────────────────


class TestFlexAssessment:
    def test_assessment_200(self, client, org_with_site):
        """GET /flex/assessment?site_id=X retourne 200."""
        site_id = org_with_site["site"].id
        r = client.get(f"/api/flex/assessment?site_id={site_id}")
        assert r.status_code == 200
        data = r.json()
        assert "flex_score" in data


# ── Tests Idempotence ────────────────────────────────────────────


class TestFlexIdempotence:
    def test_create_asset_idempotent(self, client, org_with_site):
        """Deux POST avec meme idempotency_key retournent le meme asset."""
        site_id = org_with_site["site"].id
        payload = {
            "site_id": site_id,
            "asset_type": "irve",
            "label": "Borne IRVE",
            "power_kw": 22,
            "is_controllable": False,
        }
        r1 = client.post("/api/flex/assets?idempotency_key=Borne+IRVE", json=payload)
        assert r1.status_code == 200

        r2 = client.post("/api/flex/assets?idempotency_key=Borne+IRVE", json=payload)
        assert r2.status_code == 200
        # Meme asset retourne
        assert r1.json()["id"] == r2.json()["id"]


# ── Tests Regulatory Opportunities ────────────────────────────────


class TestRegOpp:
    def test_list_reg_opp_empty(self, client):
        """GET /flex/regulatory-opportunities retourne liste vide."""
        r = client.get("/api/flex/regulatory-opportunities")
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_create_reg_opp(self, client, org_with_site):
        """POST /flex/regulatory-opportunities cree une opportunite."""
        payload = {
            "site_id": org_with_site["site"].id,
            "regulation": "cee",
            "eligible": True,
            "eligibility_reason": "Test CEE",
        }
        r = client.post("/api/flex/regulatory-opportunities", json=payload)
        assert r.status_code == 200
        assert r.json()["regulation"] == "cee"


# ── Tests Tariff Windows ─────────────────────────────────────────


class TestTariffWindows:
    def test_list_tariff_windows_empty(self, client):
        """GET /flex/tariff-windows retourne liste vide."""
        r = client.get("/api/flex/tariff-windows")
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_create_tariff_window(self, client):
        """POST /flex/tariff-windows cree une fenetre."""
        payload = {
            "name": "HC Nuit Hiver",
            "season": "hiver",
            "months": [1, 2, 3, 11, 12],
            "period_type": "HC_NUIT",
            "start_time": "22:00",
            "end_time": "06:00",
        }
        r = client.post("/api/flex/tariff-windows", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "HC Nuit Hiver"
        assert data["period_type"] == "HC_NUIT"


# ── Tests Portfolio ───────────────────────────────────────────────


class TestFlexPortfolio:
    def test_portfolio_200(self, client):
        """GET /flex/portfolio retourne 200."""
        r = client.get("/api/flex/portfolio")
        assert r.status_code == 200
        data = r.json()
        assert "total_sites" in data
        assert "rankings" in data
