"""
PROMEOS V50 — Tests: Proof Catalog V2 + Template Generation

Tests:
  1) GET /proofs/catalog returns enriched catalog
  2) GET /proofs/issue-mapping returns full mapping
  3) GET /issues/{code}/proofs returns proof details
  4) GET /issues/UNKNOWN/proofs returns graceful fallback
  5) POST /efa/{id}/proofs/templates creates draft docs
  6) Template dedup: second call skips existing
  7) Unknown proof type returns error entry
  8) 404 for nonexistent EFA
  9) Source guards on proof_catalog.py + proof_templates.py
"""
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine
from models.base import Base
Base.metadata.create_all(bind=engine)


# ── Catalog endpoints ────────────────────────────────────────────────────────

class TestProofCatalogV2:
    """GET /api/tertiaire/proofs/catalog (V50)."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from fastapi.testclient import TestClient
        self.client = TestClient(app)

    def test_catalog_returns_200(self):
        resp = self.client.get("/api/tertiaire/proofs/catalog")
        assert resp.status_code == 200

    def test_catalog_has_proof_types(self):
        data = self.client.get("/api/tertiaire/proofs/catalog").json()
        assert "proof_types" in data
        assert data["total"] >= 6

    def test_catalog_proof_type_shape(self):
        data = self.client.get("/api/tertiaire/proofs/catalog").json()
        for key, pt in data["proof_types"].items():
            assert "proof_type" in pt
            assert "title_fr" in pt
            assert "description_fr" in pt
            assert "examples_fr" in pt
            assert isinstance(pt["examples_fr"], list)
            assert "template_kind" in pt

    def test_catalog_version(self):
        data = self.client.get("/api/tertiaire/proofs/catalog").json()
        assert data["version"] == "v50"


class TestIssueMappingV2:
    """GET /api/tertiaire/proofs/issue-mapping (V50)."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from fastapi.testclient import TestClient
        self.client = TestClient(app)

    def test_mapping_returns_200(self):
        resp = self.client.get("/api/tertiaire/proofs/issue-mapping")
        assert resp.status_code == 200

    def test_mapping_has_issue_mapping(self):
        data = self.client.get("/api/tertiaire/proofs/issue-mapping").json()
        assert "issue_mapping" in data
        assert data["total"] >= 8

    def test_mapping_entry_shape(self):
        data = self.client.get("/api/tertiaire/proofs/issue-mapping").json()
        for code, entry in data["issue_mapping"].items():
            assert "proof_types" in entry
            assert "rationale_fr" in entry
            assert "confidence" in entry
            assert entry["confidence"] in ("high", "medium", "low")


class TestIssueProofsEndpoint:
    """GET /api/tertiaire/issues/{code}/proofs (V50)."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from fastapi.testclient import TestClient
        self.client = TestClient(app)

    def test_known_issue_returns_proof_types(self):
        resp = self.client.get("/api/tertiaire/issues/TERTIAIRE_MISSING_SURFACE/proofs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["proof_types"] == ["preuve_surface_usage"]
        assert data["confidence"] == "high"
        assert len(data["details"]) == 1
        assert data["details"][0]["proof_type"] == "preuve_surface_usage"

    def test_unknown_issue_returns_low_confidence(self):
        resp = self.client.get("/api/tertiaire/issues/UNKNOWN_CODE/proofs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["proof_types"] == []
        assert data["confidence"] == "low"

    def test_multi_proof_issue(self):
        resp = self.client.get("/api/tertiaire/issues/TERTIAIRE_SURFACE_COHERENCE/proofs")
        data = resp.json()
        assert len(data["proof_types"]) == 2
        assert "justificatif_exemption" in data["proof_types"]
        assert "preuve_surface_usage" in data["proof_types"]


# ── Template generation ──────────────────────────────────────────────────────

class TestTemplateGeneration:
    """POST /api/tertiaire/efa/{id}/proofs/templates (V50)."""

    _counter = 0

    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from fastapi.testclient import TestClient
        self.client = TestClient(app)
        TestTemplateGeneration._counter += 1

    def _create_efa(self, suffix=""):
        tag = f"v50_{TestTemplateGeneration._counter}_{suffix}"
        resp = self.client.post("/api/tertiaire/efa", json={
            "org_id": 1,
            "nom": f"V50 Test {tag}",
            "role_assujetti": "proprietaire",
        })
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_template_creation_returns_200(self):
        efa_id = self._create_efa("create")
        resp = self.client.post(
            f"/api/tertiaire/efa/{efa_id}/proofs/templates?year=2024",
            json={
                "issue_code": "TERTIAIRE_MISSING_SURFACE",
                "proof_types": ["preuve_surface_usage"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_created"] == 1
        assert data["total_skipped"] == 0
        assert data["created"][0]["proof_type"] == "preuve_surface_usage"
        assert data["created"][0]["status"] == "draft"

    def test_template_dedup(self):
        efa_id = self._create_efa("dedup")
        url = f"/api/tertiaire/efa/{efa_id}/proofs/templates?year=2024"
        body = {
            "issue_code": "TERTIAIRE_MISSING_SURFACE",
            "proof_types": ["preuve_surface_usage"],
        }
        # First call: create
        r1 = self.client.post(url, json=body)
        assert r1.json()["total_created"] == 1
        # Second call: skip
        r2 = self.client.post(url, json=body)
        assert r2.json()["total_created"] == 0
        assert r2.json()["total_skipped"] == 1

    def test_template_unknown_proof_type(self):
        efa_id = self._create_efa("unknown")
        resp = self.client.post(
            f"/api/tertiaire/efa/{efa_id}/proofs/templates?year=2024",
            json={
                "issue_code": "TEST",
                "proof_types": ["nonexistent_type"],
            },
        )
        data = resp.json()
        assert data["total_created"] == 0
        assert len(data["errors"]) == 1

    def test_template_multi_types(self):
        efa_id = self._create_efa("multi")
        resp = self.client.post(
            f"/api/tertiaire/efa/{efa_id}/proofs/templates?year=2024",
            json={
                "issue_code": "TERTIAIRE_SURFACE_COHERENCE",
                "proof_types": ["justificatif_exemption", "preuve_surface_usage"],
            },
        )
        data = resp.json()
        assert data["total_created"] == 2

    def test_template_404_for_missing_efa(self):
        resp = self.client.post(
            "/api/tertiaire/efa/999999/proofs/templates?year=2024",
            json={
                "issue_code": "TEST",
                "proof_types": ["preuve_surface_usage"],
            },
        )
        assert resp.status_code == 404

    def test_template_doc_id_format(self):
        efa_id = self._create_efa("docid")
        resp = self.client.post(
            f"/api/tertiaire/efa/{efa_id}/proofs/templates?year=2024",
            json={
                "issue_code": "TERTIAIRE_MISSING_SURFACE",
                "proof_types": ["preuve_surface_usage"],
            },
        )
        data = resp.json()
        doc_id = data["created"][0]["doc_id"]
        assert doc_id == f"operat_template:{efa_id}:2024:preuve_surface_usage"


# ── OpenAPI ──────────────────────────────────────────────────────────────────

class TestOpenAPIV50:
    """Verify V50 endpoints appear in OpenAPI spec."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from fastapi.testclient import TestClient
        self.client = TestClient(app)

    def test_openapi_has_proofs_catalog(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        assert "/api/tertiaire/proofs/catalog" in paths

    def test_openapi_has_issue_mapping(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        assert "/api/tertiaire/proofs/issue-mapping" in paths

    def test_openapi_has_issue_proofs(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        assert "/api/tertiaire/issues/{issue_code}/proofs" in paths

    def test_openapi_has_proof_templates(self):
        paths = self.client.get("/openapi.json").json()["paths"]
        # Check for the templates endpoint pattern
        template_paths = [p for p in paths if "proofs/templates" in p]
        assert len(template_paths) >= 1


# ── Source guards ────────────────────────────────────────────────────────────

class TestSourceGuardsV50:
    """Source code guards for V50 files."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        base = Path(__file__).resolve().parent.parent
        self.catalog_code = (base / "services" / "tertiaire_proof_catalog.py").read_text(encoding="utf-8")
        self.template_code = (base / "services" / "tertiaire_proof_templates.py").read_text(encoding="utf-8")
        self.route_code = (base / "routes" / "tertiaire.py").read_text(encoding="utf-8")

    def test_catalog_has_proof_types(self):
        assert "PROOF_TYPES" in self.catalog_code

    def test_catalog_has_issue_proof_mapping(self):
        assert "ISSUE_PROOF_MAPPING" in self.catalog_code

    def test_catalog_has_get_proof_types(self):
        assert "def get_proof_types" in self.catalog_code

    def test_catalog_has_get_issue_proof_mapping(self):
        assert "def get_issue_proof_mapping" in self.catalog_code

    def test_catalog_has_get_proofs_for_issue(self):
        assert "def get_proofs_for_issue" in self.catalog_code

    def test_catalog_has_confidence_levels(self):
        assert '"high"' in self.catalog_code
        assert '"medium"' in self.catalog_code

    def test_template_has_render_template_md(self):
        assert "def render_template_md" in self.template_code

    def test_template_has_generate_proof_templates(self):
        assert "def generate_proof_templates" in self.template_code

    def test_template_uses_kb_store(self):
        assert "KBStore" in self.template_code
        assert "upsert_doc" in self.template_code

    def test_template_has_dedup_logic(self):
        assert "get_doc" in self.template_code

    def test_template_supports_action_link(self):
        assert "link_doc_to_action" in self.template_code
        assert "action_id" in self.template_code

    def test_route_imports_v50_catalog(self):
        assert "from services.tertiaire_proof_catalog import" in self.route_code

    def test_route_imports_v50_templates(self):
        assert "from services.tertiaire_proof_templates import" in self.route_code
        assert "generate_proof_templates" in self.route_code

    def test_route_has_catalog_endpoint(self):
        assert "proofs/catalog" in self.route_code

    def test_route_has_issue_mapping_endpoint(self):
        assert "proofs/issue-mapping" in self.route_code

    def test_route_has_templates_endpoint(self):
        assert "proofs/templates" in self.route_code
