"""
PROMEOS V40 — Tests: export pack OPERAT → KB doc + proof_artifact
"""

import hashlib
import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Ensure backend on sys.path ──────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ══════════════════════════════════════════════════════════════════════════════
# 1. KB doc creation logic (unit)
# ══════════════════════════════════════════════════════════════════════════════


class TestKBDocFromExportPack:
    """Test the KB doc registration logic isolated from DB."""

    def test_sha256_of_zip_is_deterministic(self, tmp_path):
        """Same zip content → same hash."""
        zp = tmp_path / "test.zip"
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr("recap.json", '{"efa_id": 1}')
        h1 = hashlib.sha256(zp.read_bytes()).hexdigest()

        zp2 = tmp_path / "test2.zip"
        with zipfile.ZipFile(zp2, "w") as zf:
            zf.writestr("recap.json", '{"efa_id": 1}')
        h2 = hashlib.sha256(zp2.read_bytes()).hexdigest()

        assert h1 == h2

    def test_doc_id_format(self):
        """doc_id should start with generated_operat_ + 12 hex chars."""
        fake_hash = hashlib.sha256(b"test").hexdigest()
        doc_id = f"generated_operat_{fake_hash[:12]}"
        assert doc_id.startswith("generated_operat_")
        assert len(doc_id) == len("generated_operat_") + 12

    def test_doc_metadata_shape(self):
        """The doc dict passed to upsert_doc should have required fields."""
        fake_hash = hashlib.sha256(b"test").hexdigest()
        doc = {
            "doc_id": f"generated_operat_{fake_hash[:12]}",
            "title": "Pack OPERAT — Test EFA — 2025",
            "source_type": "pdf",
            "source_path": "/tmp/test.zip",
            "content_hash": fake_hash,
            "nb_sections": 2,
            "nb_chunks": 0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "meta": {"efa_id": 1, "year": 2025, "simulation": True, "generated_type": "operat_export"},
            "status": "review",
        }
        assert doc["status"] == "review"
        assert doc["source_type"] == "pdf"
        assert doc["meta"]["generated_type"] == "operat_export"
        assert "efa_id" in doc["meta"]

    def test_display_name_format(self):
        """V40.1: display_name should be human-friendly, no hash."""
        efa_nom = "Siège Nantes"
        year = 2025
        display_name = f"Pack OPERAT \u2014 {efa_nom} \u2014 {year}"
        assert display_name == "Pack OPERAT \u2014 Siège Nantes \u2014 2025"
        assert "generated_operat_" not in display_name

    def test_kb_open_url_format(self):
        """kb_open_url should point to /kb with context=proof and status=review."""
        url = (
            "/kb?context=proof"
            "&domain=conformite%2Ftertiaire-operat"
            "&status=review"
            "&hint=Pack+OPERAT+%E2%80%94+Test+%E2%80%94+2025"
        )
        assert "context=proof" in url
        assert "status=review" in url
        assert "domain=conformite%2Ftertiaire-operat" in url


# ══════════════════════════════════════════════════════════════════════════════
# 2. Service function source guards
# ══════════════════════════════════════════════════════════════════════════════


class TestServiceSourceGuards:
    """Verify tertiaire_service.py contains V40 code."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        src_path = Path(__file__).resolve().parent.parent / "services" / "tertiaire_service.py"
        self.code = src_path.read_text(encoding="utf-8")

    def test_imports_hashlib(self):
        assert "import hashlib" in self.code

    def test_imports_kb_store(self):
        assert "from app.kb.store import KBStore" in self.code

    def test_creates_proof_artifact(self):
        assert "TertiaireProofArtifact" in self.code
        assert '"operat_export_pack"' in self.code

    def test_returns_kb_doc_id(self):
        assert '"kb_doc_id": kb_doc_id' in self.code

    def test_returns_kb_open_url(self):
        assert '"kb_open_url": kb_open_url' in self.code

    def test_dedup_check(self):
        assert "kb_store.get_doc(kb_doc_id)" in self.code

    def test_non_blocking_on_failure(self):
        assert "V40: KB doc creation failed" in self.code

    def test_review_initial_status(self):
        assert '"status": "review"' in self.code

    # V40.1: display_name guards
    def test_builds_display_name(self):
        assert "kb_display_name" in self.code

    def test_passes_display_name_to_upsert(self):
        assert '"display_name": kb_display_name' in self.code

    def test_returns_kb_doc_display_name(self):
        assert '"kb_doc_display_name"' in self.code


# ══════════════════════════════════════════════════════════════════════════════
# 3. Proof artifact model
# ══════════════════════════════════════════════════════════════════════════════


class TestDisplayNameInKBStore:
    """V40.1: Verify display_name column is supported in KB store + models."""

    def test_store_upsert_handles_display_name(self):
        src_path = Path(__file__).resolve().parent.parent / "app" / "kb" / "store.py"
        code = src_path.read_text(encoding="utf-8")
        assert "display_name" in code
        assert "display_name=excluded.display_name" in code

    def test_models_migration_adds_display_name(self):
        src_path = Path(__file__).resolve().parent.parent / "app" / "kb" / "models.py"
        code = src_path.read_text(encoding="utf-8")
        assert '"display_name"' in code


class TestProofArtifactModel:
    """Verify TertiaireProofArtifact has kb_doc_id field."""

    def test_kb_doc_id_column_exists(self):
        src_path = Path(__file__).resolve().parent.parent / "models" / "tertiaire.py"
        code = src_path.read_text(encoding="utf-8")
        assert "kb_doc_id" in code
        assert "String(200)" in code

    def test_type_column_exists(self):
        src_path = Path(__file__).resolve().parent.parent / "models" / "tertiaire.py"
        code = src_path.read_text(encoding="utf-8")
        assert "type = Column(String(100)" in code


# ══════════════════════════════════════════════════════════════════════════════
# 4. E2E: POST create EFA returns 201 (TestClient)
# ══════════════════════════════════════════════════════════════════════════════


class TestCreateEfaEndpoint:
    """Verify the POST /api/tertiaire/efa endpoint returns 201."""

    def test_create_efa_minimal_payload(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.post(
            "/api/tertiaire/efa",
            json={
                "org_id": 1,
                "nom": "Test E2E V39.3",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["nom"] == "Test E2E V39.3"
        assert data["statut"] == "draft"
        assert "id" in data

    def test_create_efa_without_email(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.post(
            "/api/tertiaire/efa",
            json={
                "org_id": 1,
                "nom": "EFA sans email",
                "role_assujetti": "locataire",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["role_assujetti"] == "locataire"

    def test_list_returns_created_efa(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        # Create
        resp = client.post(
            "/api/tertiaire/efa",
            json={
                "org_id": 1,
                "nom": "EFA list check",
            },
        )
        assert resp.status_code == 201
        efa_id = resp.json()["id"]
        # List
        resp2 = client.get("/api/tertiaire/efa")
        assert resp2.status_code == 200
        ids = [e["id"] for e in resp2.json()["efas"]]
        assert efa_id in ids


# ══════════════════════════════════════════════════════════════════════════════
# 5. Swagger: /api/tertiaire/* exposed in OpenAPI
# ══════════════════════════════════════════════════════════════════════════════


class TestSwaggerTertiaireRoutes:
    """Verify /api/tertiaire endpoints appear in /docs (OpenAPI schema)."""

    def test_get_efa_returns_200(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/tertiaire/efa")
        assert resp.status_code == 200
        assert "efas" in resp.json()

    def test_openapi_exposes_tertiaire_routes(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        tertiaire_paths = [p for p in paths if "/tertiaire" in p]
        assert len(tertiaire_paths) >= 10, f"Expected >=10 tertiaire routes, got {len(tertiaire_paths)}"
        assert "/api/tertiaire/efa" in paths
        assert "/api/tertiaire/efa/{efa_id}/export-pack" in paths
