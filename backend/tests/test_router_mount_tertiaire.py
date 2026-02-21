"""
PROMEOS V39.4 — Test bloquant : router Tertiaire/OPERAT monté dans app.

Empêche toute régression sur le montage du router.
Si ce test échoue → les endpoints /api/tertiaire/* ne sont plus exposés dans Swagger.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ══════════════════════════════════════════════════════════════════════════════
# 1. Import chain integrity
# ══════════════════════════════════════════════════════════════════════════════

class TestImportChain:
    """Verify the import chain: tertiaire.py → __init__.py → main.py."""

    def test_tertiaire_module_exports_router(self):
        from routes import tertiaire
        assert hasattr(tertiaire, "router"), "routes/tertiaire.py must export 'router'"

    def test_routes_init_exports_tertiaire_router(self):
        from routes import tertiaire_router
        assert tertiaire_router is not None

    def test_router_has_correct_prefix(self):
        from routes import tertiaire_router
        assert tertiaire_router.prefix == "/api/tertiaire"

    def test_router_has_routes(self):
        from routes import tertiaire_router
        assert len(tertiaire_router.routes) >= 10, (
            f"Expected >= 10 routes, got {len(tertiaire_router.routes)}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# 2. App mount — tertiaire routes reachable
# ══════════════════════════════════════════════════════════════════════════════

class TestAppMountTertiaire:
    """Verify /api/tertiaire/* endpoints are mounted and respond (not 404)."""

    def test_get_efa_list_returns_200(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/tertiaire/efa")
        assert resp.status_code == 200, (
            f"GET /api/tertiaire/efa returned {resp.status_code}, expected 200. "
            "Router not mounted?"
        )
        assert "efas" in resp.json()

    def test_post_efa_returns_201(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.post("/api/tertiaire/efa", json={
            "org_id": 1,
            "nom": "Test mount V39.4",
        })
        assert resp.status_code == 201, (
            f"POST /api/tertiaire/efa returned {resp.status_code}, expected 201"
        )

    def test_get_dashboard_returns_200(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/tertiaire/dashboard")
        assert resp.status_code == 200

    def test_get_issues_returns_200(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/api/tertiaire/issues")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# 3. OpenAPI / Swagger exposure
# ══════════════════════════════════════════════════════════════════════════════

class TestSwaggerExposure:
    """Verify /api/tertiaire/* appears in OpenAPI schema (/docs)."""

    def test_openapi_contains_tertiaire_efa(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/tertiaire/efa" in paths, (
            "'/api/tertiaire/efa' missing from OpenAPI schema — "
            "Swagger /docs will not show tertiaire routes"
        )

    def test_openapi_contains_export_pack(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/api/tertiaire/efa/{efa_id}/export-pack" in paths

    def test_openapi_tertiaire_count(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/openapi.json")
        paths = resp.json()["paths"]
        tertiaire = [p for p in paths if "/tertiaire" in p]
        assert len(tertiaire) >= 10, (
            f"Expected >= 10 tertiaire paths in OpenAPI, got {len(tertiaire)}"
        )

    def test_tertiaire_tag_exists(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/openapi.json")
        schema = resp.json()
        # Check at least one tertiaire path uses the tag
        efa_path = schema["paths"].get("/api/tertiaire/efa", {})
        get_op = efa_path.get("get", {})
        tags = get_op.get("tags", [])
        assert "Tertiaire / OPERAT" in tags, (
            f"Expected tag 'Tertiaire / OPERAT', got {tags}"
        )
