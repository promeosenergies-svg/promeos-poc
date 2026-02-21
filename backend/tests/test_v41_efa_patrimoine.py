"""
PROMEOS V41 — Tests: EFA <-> Patrimoine building link
Zero duplication : le wizard selectionne des batiments existants.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure all tables exist (sites, batiments, etc.) for catalog tests
from database import engine
from models.base import Base
Base.metadata.create_all(bind=engine)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Catalog endpoint
# ══════════════════════════════════════════════════════════════════════════════

class TestCatalogEndpoint:
    """GET /api/tertiaire/catalog returns sites + buildings."""

    def test_catalog_returns_200(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/tertiaire/catalog")
        assert resp.status_code == 200
        data = resp.json()
        assert "sites" in data
        assert "total_buildings" in data

    def test_catalog_sites_have_batiments_shape(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/tertiaire/catalog")
        data = resp.json()
        for site in data["sites"]:
            assert "site_id" in site
            assert "site_nom" in site
            assert "batiments" in site
            for bat in site["batiments"]:
                assert "id" in bat
                assert "nom" in bat
                assert "surface_m2" in bat


# ══════════════════════════════════════════════════════════════════════════════
# 2. Create EFA with buildings — backward compat + validation
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateEfaWithBuildings:
    """POST /api/tertiaire/efa with buildings[] creates associations atomically."""

    def test_create_efa_without_buildings_backward_compat(self):
        """Old payload (no buildings) still returns 201."""
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/api/tertiaire/efa", json={
            "org_id": 1,
            "nom": "V41 backward compat",
        })
        assert resp.status_code == 201
        assert resp.json()["nom"] == "V41 backward compat"

    def test_create_efa_with_invalid_building_returns_404(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/api/tertiaire/efa", json={
            "org_id": 1,
            "nom": "V41 invalid building",
            "buildings": [{"building_id": 999999, "usage_label": "Bureaux"}],
        })
        assert resp.status_code == 404
        assert "introuvable" in resp.json()["detail"].lower()

    def test_create_efa_with_buildings_snapshots_surface(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        # First check if catalog has buildings
        cat = client.get("/api/tertiaire/catalog").json()
        all_bats = [
            bat
            for site in cat["sites"]
            for bat in site["batiments"]
        ]
        if not all_bats:
            pytest.skip("No buildings in patrimoine for test org")

        bat = all_bats[0]
        resp = client.post("/api/tertiaire/efa", json={
            "org_id": 1,
            "nom": "V41 linked EFA",
            "buildings": [{"building_id": bat["id"], "usage_label": "Bureaux"}],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "buildings" in data
        assert len(data["buildings"]) == 1
        assert data["buildings"][0]["building_id"] == bat["id"]
        assert data["buildings"][0]["surface_m2"] == bat["surface_m2"]
        assert data["buildings"][0]["usage_label"] == "Bureaux"


# ══════════════════════════════════════════════════════════════════════════════
# 3. OpenAPI / Swagger
# ══════════════════════════════════════════════════════════════════════════════

class TestOpenAPICatalog:
    """Verify /api/tertiaire/catalog appears in OpenAPI schema."""

    def test_openapi_contains_catalog(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/api/tertiaire/catalog" in paths


# ══════════════════════════════════════════════════════════════════════════════
# 4. Source guards — schema shapes
# ══════════════════════════════════════════════════════════════════════════════

class TestSourceGuardsV41:
    """Verify tertiaire.py contains V41 code."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        src_path = Path(__file__).resolve().parent.parent / "routes" / "tertiaire.py"
        self.code = src_path.read_text(encoding="utf-8")

    def test_building_with_usage_schema_exists(self):
        assert "class BuildingWithUsage" in self.code

    def test_buildings_field_optional_in_schema(self):
        assert "Optional[List[BuildingWithUsage]]" in self.code

    def test_snapshot_surface_from_patrimoine(self):
        assert "bat.surface_m2" in self.code

    def test_catalog_endpoint_exists(self):
        assert "def building_catalog" in self.code

    def test_building_validation_404(self):
        assert "introuvable" in self.code
