"""
PROMEOS V45 — Tests: Proof catalog + proofs status endpoint
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine
from models.base import Base

try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass


# ══════════════════════════════════════════════════════════════════════════════
# 1. PROOF_CATALOG — stable keys + structure
# ══════════════════════════════════════════════════════════════════════════════


class TestProofCatalog:
    """Proof catalog has expected structure and stable keys."""

    def test_catalog_has_required_types(self):
        from services.tertiaire_proofs import PROOF_CATALOG

        required = [
            "attestation_operat",
            "dossier_modulation",
            "justificatif_exemption",
            "justificatif_multi_occupation",
            "preuve_surface_usage",
            "bail_titre_propriete",
        ]
        for key in required:
            assert key in PROOF_CATALOG, f"Missing proof type: {key}"

    def test_catalog_entry_has_required_fields(self):
        from services.tertiaire_proofs import PROOF_CATALOG

        required_fields = ["type", "label_fr", "owner_role", "exemple_fichiers", "deadline_hint", "kb_domain"]
        for key, entry in PROOF_CATALOG.items():
            for field in required_fields:
                assert field in entry, f"{key} missing field: {field}"

    def test_catalog_kb_domain_is_tertiaire(self):
        from services.tertiaire_proofs import PROOF_CATALOG

        for key, entry in PROOF_CATALOG.items():
            assert entry["kb_domain"] == "conformite/tertiaire-operat", f"{key} has wrong kb_domain"

    def test_catalog_labels_are_french(self):
        from services.tertiaire_proofs import PROOF_CATALOG

        for key, entry in PROOF_CATALOG.items():
            assert len(entry["label_fr"]) > 5, f"{key} has too short label_fr"
            # Should contain French chars or words
            assert any(c in entry["label_fr"] for c in "éèêàùûîôç/ "), f"{key} label_fr may not be French"


# ══════════════════════════════════════════════════════════════════════════════
# 2. GET /proof-catalog endpoint
# ══════════════════════════════════════════════════════════════════════════════


class TestProofCatalogEndpoint:
    def test_endpoint_returns_catalog(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/tertiaire/proof-catalog")
        assert resp.status_code == 200
        data = resp.json()
        assert "proofs" in data
        assert "total" in data
        assert data["total"] >= 6

    def test_endpoint_entries_have_type(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        data = client.get("/api/tertiaire/proof-catalog").json()
        for proof in data["proofs"]:
            assert "type" in proof
            assert "label_fr" in proof


# ══════════════════════════════════════════════════════════════════════════════
# 3. GET /efa/{id}/proofs — proofs status counts
# ══════════════════════════════════════════════════════════════════════════════


class TestProofsStatusEndpoint:
    def test_proofs_status_for_nonexistent_efa(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/tertiaire/efa/99999/proofs")
        assert resp.status_code == 404

    def test_proofs_status_shape(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        # Create EFA first
        efa = client.post(
            "/api/tertiaire/efa",
            json={
                "org_id": 1,
                "nom": "V45 Proofs Test",
            },
        )
        if efa.status_code != 201:
            pytest.skip("Cannot create EFA")
        efa_id = efa.json()["id"]
        resp = client.get(f"/api/tertiaire/efa/{efa_id}/proofs")
        assert resp.status_code == 200
        data = resp.json()
        for key in [
            "expected",
            "expected_count",
            "deposited",
            "deposited_count",
            "validated",
            "validated_count",
            "missing",
            "missing_count",
            "coverage_pct",
        ]:
            assert key in data, f"Missing key: {key}"

    def test_proofs_baseline_has_expected(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        efa = client.post(
            "/api/tertiaire/efa",
            json={
                "org_id": 1,
                "nom": "V45 Expected Test",
            },
        )
        if efa.status_code != 201:
            pytest.skip("Cannot create EFA")
        efa_id = efa.json()["id"]
        data = client.get(f"/api/tertiaire/efa/{efa_id}/proofs").json()
        # Should expect at least attestation_operat + bail_titre_propriete
        assert data["expected_count"] >= 2
        types = [p["type"] for p in data["expected"]]
        assert "attestation_operat" in types
        assert "bail_titre_propriete" in types

    def test_proofs_no_deposits_initially(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        efa = client.post(
            "/api/tertiaire/efa",
            json={
                "org_id": 1,
                "nom": "V45 No Deposits",
            },
        )
        if efa.status_code != 201:
            pytest.skip("Cannot create EFA")
        efa_id = efa.json()["id"]
        data = client.get(f"/api/tertiaire/efa/{efa_id}/proofs").json()
        assert data["deposited_count"] == 0
        assert data["validated_count"] == 0
        assert data["missing_count"] == data["expected_count"]


# ══════════════════════════════════════════════════════════════════════════════
# 4. POST /efa/{id}/proofs/link
# ══════════════════════════════════════════════════════════════════════════════


class TestProofLinkEndpoint:
    def test_link_proof_creates_artifact(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        efa = client.post(
            "/api/tertiaire/efa",
            json={
                "org_id": 1,
                "nom": "V45 Link Test",
            },
        )
        if efa.status_code != 201:
            pytest.skip("Cannot create EFA")
        efa_id = efa.json()["id"]
        resp = client.post(
            f"/api/tertiaire/efa/{efa_id}/proofs/link",
            json={
                "kb_doc_id": "test_doc_v45_001",
                "proof_type": "attestation_operat",
                "year": 2024,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "linked"
        assert data["type"] == "attestation_operat"

    def test_link_proof_dedup(self):
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        efa = client.post(
            "/api/tertiaire/efa",
            json={
                "org_id": 1,
                "nom": "V45 Dedup Link",
            },
        )
        if efa.status_code != 201:
            pytest.skip("Cannot create EFA")
        efa_id = efa.json()["id"]
        body = {
            "kb_doc_id": "test_doc_v45_dedup",
            "proof_type": "attestation_operat",
        }
        client.post(f"/api/tertiaire/efa/{efa_id}/proofs/link", json=body)
        # Second link same doc → already_linked
        resp2 = client.post(f"/api/tertiaire/efa/{efa_id}/proofs/link", json=body)
        assert resp2.status_code == 201
        assert resp2.json()["status"] == "already_linked"


# ══════════════════════════════════════════════════════════════════════════════
# 5. Source guards
# ══════════════════════════════════════════════════════════════════════════════


class TestV45SourceGuards:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.proofs_code = (Path(__file__).resolve().parent.parent / "services" / "tertiaire_proofs.py").read_text(
            encoding="utf-8"
        )
        self.routes_code = (Path(__file__).resolve().parent.parent / "routes" / "tertiaire.py").read_text(
            encoding="utf-8"
        )

    def test_proof_catalog_in_proofs_service(self):
        assert "PROOF_CATALOG" in self.proofs_code

    def test_list_proofs_status_in_proofs_service(self):
        assert "list_proofs_status" in self.proofs_code

    def test_get_expected_proofs_in_proofs_service(self):
        assert "get_expected_proofs_for_efa" in self.proofs_code

    def test_proof_endpoints_in_routes(self):
        assert "proof-catalog" in self.routes_code
        assert "/proofs" in self.routes_code
        assert "proofs/link" in self.routes_code

    def test_v45_import_in_routes(self):
        assert "tertiaire_proofs" in self.routes_code
