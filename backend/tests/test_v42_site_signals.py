"""
PROMEOS V42 — Tests: Site Signals + Auto-qualification
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure all tables exist (sites, batiments, etc.) for signal tests
from database import engine
from models.base import Base

try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass


# ══════════════════════════════════════════════════════════════════════════════
# 1. Site Signals endpoint
# ══════════════════════════════════════════════════════════════════════════════


class TestSiteSignalsEndpoint:
    """GET /api/tertiaire/site-signals returns site qualification."""

    def test_site_signals_returns_200(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/tertiaire/site-signals")
        assert resp.status_code == 200
        data = resp.json()
        assert "sites" in data
        assert "total_sites" in data
        assert "counts" in data
        assert "uncovered_probable" in data
        assert "incomplete_data" in data

    def test_site_signals_shape(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        for site in data["sites"]:
            assert "site_id" in site
            assert "site_nom" in site
            assert "signal" in site
            assert site["signal"] in ("assujetti_probable", "a_verifier", "non_concerne")
            assert "is_covered" in site
            assert "data_complete" in site
            assert "surface_tertiaire_m2" in site
            assert "nb_batiments" in site

    def test_counts_sum_matches_total(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        total = sum(data["counts"].values())
        assert total == data["total_sites"]

    def test_uncovered_probable_lte_assujetti_probable(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/site-signals").json()
        assert data["uncovered_probable"] <= data["counts"]["assujetti_probable"]


# ══════════════════════════════════════════════════════════════════════════════
# 2. OpenAPI
# ══════════════════════════════════════════════════════════════════════════════


class TestOpenAPISignals:
    """Verify /api/tertiaire/site-signals appears in OpenAPI schema."""

    def test_openapi_contains_site_signals(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/api/tertiaire/site-signals" in paths

    def test_openapi_200_schema_is_object(self):
        """V50.1: OpenAPI 200 schema must be an object ref, not empty/string."""
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        oa = client.get("/openapi.json").json()
        path_info = oa["paths"]["/api/tertiaire/site-signals"]["get"]
        schema = path_info["responses"]["200"]["content"]["application/json"]["schema"]
        # Must have a $ref to a named model
        assert "$ref" in schema, "OpenAPI 200 schema should reference a model"
        ref = schema["$ref"]
        model_name = ref.split("/")[-1]
        model_def = oa["components"]["schemas"][model_name]
        assert model_def["type"] == "object"
        props = model_def.get("properties", {})
        assert "sites" in props
        assert "total_sites" in props
        assert "counts" in props

    def test_openapi_site_item_has_signal_field(self):
        """V50.1: site item in OpenAPI must expose 'signal' field."""
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        oa = client.get("/openapi.json").json()
        # Walk: SiteSignalsResponse → sites → items → SiteSignalItem
        ref = oa["paths"]["/api/tertiaire/site-signals"]["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        resp_model = oa["components"]["schemas"][ref.split("/")[-1]]
        sites_prop = resp_model["properties"]["sites"]
        item_ref = sites_prop["items"]["$ref"]
        item_model = oa["components"]["schemas"][item_ref.split("/")[-1]]
        assert "signal" in item_model["properties"]
        assert "site_id" in item_model["properties"]
        assert "is_covered" in item_model["properties"]


# ══════════════════════════════════════════════════════════════════════════════
# 3. Source guards
# ══════════════════════════════════════════════════════════════════════════════


class TestSourceGuardsV42:
    """Verify V42 code in route + service."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        self.route_code = (Path(__file__).resolve().parent.parent / "routes" / "tertiaire.py").read_text(
            encoding="utf-8"
        )
        self.service_code = (Path(__file__).resolve().parent.parent / "services" / "tertiaire_service.py").read_text(
            encoding="utf-8"
        )

    def test_compute_site_signals_exists(self):
        assert "def compute_site_signals" in self.service_code

    def test_heuristic_threshold_1000(self):
        assert "1000" in self.service_code
        assert "assujetti_probable" in self.service_code

    def test_signal_categories_exist(self):
        assert "a_verifier" in self.service_code
        assert "non_concerne" in self.service_code

    def test_route_imports_compute_site_signals(self):
        assert "compute_site_signals" in self.route_code

    def test_route_has_site_signals_endpoint(self):
        assert "site-signals" in self.route_code

    def test_service_imports_site_batiment(self):
        assert "Site, Batiment" in self.service_code

    def test_route_has_response_model(self):
        """V50.1: endpoint must declare response_model for proper OpenAPI."""
        assert "response_model=SiteSignalsResponse" in self.route_code

    def test_route_has_pydantic_models(self):
        """V50.1: Pydantic response models must be defined."""
        assert "class SiteSignalsResponse" in self.route_code
        assert "class SiteSignalItem" in self.route_code
        assert "class SiteSignalCounts" in self.route_code
