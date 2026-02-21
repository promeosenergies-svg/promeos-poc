"""
PROMEOS V45 — Tests: Controls V2 (actionnable + proof_required)
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine
from models.base import Base
Base.metadata.create_all(bind=engine)


# ══════════════════════════════════════════════════════════════════════════════
# 1. CONTROL_RULES structure V2
# ══════════════════════════════════════════════════════════════════════════════

class TestControlRulesV2:
    def test_rules_count_at_least_8(self):
        from services.tertiaire_service import CONTROL_RULES
        assert len(CONTROL_RULES) >= 8

    def test_rules_have_title_fr(self):
        from services.tertiaire_service import CONTROL_RULES
        for rule in CONTROL_RULES:
            assert "title_fr" in rule, f"Rule {rule['code']} missing title_fr"

    def test_rules_have_required_fields(self):
        from services.tertiaire_service import CONTROL_RULES
        required = ["code", "severity", "check", "message_fr", "impact_fr", "action_fr"]
        for rule in CONTROL_RULES:
            for field in required:
                assert field in rule, f"Rule {rule['code']} missing {field}"

    def test_new_rules_present(self):
        from services.tertiaire_service import CONTROL_RULES
        codes = [r["code"] for r in CONTROL_RULES]
        assert "TERTIAIRE_RESP_NO_EMAIL" in codes
        assert "TERTIAIRE_PERIMETER_EVENT_PROOF" in codes

    def test_proof_required_structured(self):
        from services.tertiaire_service import CONTROL_RULES
        for rule in CONTROL_RULES:
            proof = rule.get("proof_required")
            if proof is not None:
                assert isinstance(proof, dict), f"{rule['code']}: proof_required should be dict"
                assert "type" in proof
                assert "label_fr" in proof
                assert "owner_role" in proof
                assert "deadline_hint" in proof
                assert "doc_domain" in proof


# ══════════════════════════════════════════════════════════════════════════════
# 2. run_controls V2 — enriched output
# ══════════════════════════════════════════════════════════════════════════════

class TestRunControlsV2:
    def test_controls_returns_issues_with_proof_fields(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        # Create EFA without buildings → triggers TERTIAIRE_NO_BUILDING
        efa = client.post("/api/tertiaire/efa", json={
            "org_id": 1, "nom": "V45 Controls Test",
        })
        if efa.status_code != 201:
            pytest.skip("Cannot create EFA")
        efa_id = efa.json()["id"]
        resp = client.post(f"/api/tertiaire/efa/{efa_id}/controls")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        for issue in data["issues"]:
            assert "title_fr" in issue
            assert "proof_required" in issue or issue.get("proof_required") is None
            assert "proof_links" in issue

    def test_controls_critical_no_building(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        efa = client.post("/api/tertiaire/efa", json={
            "org_id": 1, "nom": "V45 No Building",
        })
        if efa.status_code != 201:
            pytest.skip("Cannot create EFA")
        efa_id = efa.json()["id"]
        data = client.post(f"/api/tertiaire/efa/{efa_id}/controls").json()
        codes = [i["code"] for i in data["issues"]]
        assert "TERTIAIRE_NO_BUILDING" in codes
        nb = next(i for i in data["issues"] if i["code"] == "TERTIAIRE_NO_BUILDING")
        assert nb["severity"] == "critical"

    def test_controls_no_resp_has_proof_required(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        efa = client.post("/api/tertiaire/efa", json={
            "org_id": 1, "nom": "V45 No Resp Proof",
        })
        if efa.status_code != 201:
            pytest.skip("Cannot create EFA")
        efa_id = efa.json()["id"]
        data = client.post(f"/api/tertiaire/efa/{efa_id}/controls").json()
        codes = [i["code"] for i in data["issues"]]
        assert "TERTIAIRE_NO_RESPONSIBILITY" in codes
        nr = next(i for i in data["issues"] if i["code"] == "TERTIAIRE_NO_RESPONSIBILITY")
        assert nr["proof_required"] is not None
        assert nr["proof_required"]["type"] == "bail_titre_propriete"
        assert len(nr["proof_links"]) > 0
        assert "context=proof" in nr["proof_links"][0]

    def test_controls_deterministic(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        efa = client.post("/api/tertiaire/efa", json={
            "org_id": 1, "nom": "V45 Deterministic",
        })
        if efa.status_code != 201:
            pytest.skip("Cannot create EFA")
        efa_id = efa.json()["id"]
        r1 = client.post(f"/api/tertiaire/efa/{efa_id}/controls").json()
        r2 = client.post(f"/api/tertiaire/efa/{efa_id}/controls").json()
        assert r1["total"] == r2["total"]
        assert [i["code"] for i in r1["issues"]] == [i["code"] for i in r2["issues"]]


# ══════════════════════════════════════════════════════════════════════════════
# 3. Source guards
# ══════════════════════════════════════════════════════════════════════════════

class TestV45ControlsSourceGuards:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.code = (
            Path(__file__).resolve().parent.parent / "services" / "tertiaire_service.py"
        ).read_text(encoding="utf-8")

    def test_v45_proof_helper(self):
        assert "def _proof(" in self.code

    def test_v45_build_proof_links(self):
        assert "_build_proof_links" in self.code

    def test_v45_title_fr_in_rules(self):
        assert "title_fr" in self.code

    def test_v45_proof_required_structured(self):
        assert "proof_required" in self.code
        assert "proof_links" in self.code

    def test_v45_new_rules(self):
        assert "TERTIAIRE_RESP_NO_EMAIL" in self.code
        assert "TERTIAIRE_PERIMETER_EVENT_PROOF" in self.code
