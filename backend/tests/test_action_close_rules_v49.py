"""
PROMEOS V49 — Tests: Action Close Rules (OPERAT enforcement)

Tests:
  1) close rules service: is_operat_action, check_closable
  2) PATCH endpoint blocks OPERAT close without proof/justification
  3) PATCH endpoint allows close with justification >= 10 chars
  4) PATCH endpoint allows close for non-OPERAT actions
  5) closeability endpoint returns correct shape
  6) Source guards on action_close_rules.py
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine
from models.base import Base

Base.metadata.create_all(bind=engine)

# V49: ensure closure_justification column exists (additive migration)
from sqlalchemy import inspect as sa_inspect, text as sa_text

_insp = sa_inspect(engine)
if _insp.has_table("action_items"):
    _existing = {c["name"] for c in _insp.get_columns("action_items")}
    if "closure_justification" not in _existing:
        with engine.begin() as _conn:
            _conn.execute(sa_text('ALTER TABLE "action_items" ADD COLUMN "closure_justification" TEXT'))


# ── Service unit tests ───────────────────────────────────────────────────────


class TestIsOperatAction:
    """Unit tests for is_operat_action helper."""

    def test_operat_action_detected(self):
        from services.action_close_rules import is_operat_action

        class FakeAction:
            source_type = type("E", (), {"value": "insight"})()
            source_id = "operat:42:2024:missing_proof"

        FakeAction.source_type = type("E", (str,), {"value": "insight"})("insight")

        assert is_operat_action(FakeAction()) is True

    def test_non_operat_action(self):
        from services.action_close_rules import is_operat_action

        class FakeAction:
            pass

        a = FakeAction()
        a.source_type = type("E", (str,), {"value": "compliance"})("compliance")
        a.source_id = "rule_123"
        assert is_operat_action(a) is False

    def test_none_action(self):
        from services.action_close_rules import is_operat_action

        assert is_operat_action(None) is False


# ── Endpoint integration tests ───────────────────────────────────────────────


class TestPatchCloseRules:
    """PATCH /api/actions/{id} — V49 close rules enforcement."""

    _counter = 0

    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from fastapi.testclient import TestClient

        self.client = TestClient(app)
        TestPatchCloseRules._counter += 1
        # Ensure DemoState has a valid org (action creation requires org_id)
        from services.demo_state import DemoState

        if not DemoState.get_demo_org_id():
            from database import SessionLocal
            from models import Organisation

            db = SessionLocal()
            try:
                org = db.query(Organisation).first()
                if not org:
                    org = Organisation(
                        nom="V49 Test Org", type_client="tertiaire", actif=True, siren="999999999", is_demo=True
                    )
                    db.add(org)
                    db.commit()
                DemoState.set_demo_org(org_id=org.id, org_nom=org.nom)
            finally:
                db.close()

    def _create_operat_action(self, suffix=""):
        """Create a fresh OPERAT action via POST."""
        tag = f"{TestPatchCloseRules._counter}_{suffix}"
        resp = self.client.post(
            "/api/actions",
            json={
                "title": f"V49 OPERAT test {tag}",
                "source_type": "insight",
                "source_id": f"operat:99:2024:v49_test_{tag}",
                "idempotency_key": f"v49_operat_{tag}",
            },
        )
        assert resp.status_code == 200
        return resp.json()["id"]

    def _create_manual_action(self, suffix=""):
        """Create a fresh manual action via POST."""
        tag = f"{TestPatchCloseRules._counter}_{suffix}"
        resp = self.client.post(
            "/api/actions",
            json={
                "title": f"V49 manual test {tag}",
                "source_type": "manual",
                "idempotency_key": f"v49_manual_{tag}",
            },
        )
        assert resp.status_code == 200
        return resp.json()["id"]

    def test_operat_close_blocked_without_proof_or_justification(self):
        """OPERAT action → done without proof/justification → HTTP 400."""
        aid = self._create_operat_action("blocked")
        resp = self.client.patch(f"/api/actions/{aid}", json={"status": "done"})
        assert resp.status_code == 400
        body = resp.json()
        # Support both old format {"detail": "..."} and new format {"code": "...", "message": "..."}
        detail_str = str(body.get("message", body.get("detail", ""))).lower()
        assert "preuve" in detail_str or "justification" in detail_str

    def test_operat_close_allowed_with_justification(self):
        """OPERAT action → done with justification >= 10 chars → HTTP 200."""
        aid = self._create_operat_action("with_justif")
        resp = self.client.patch(
            f"/api/actions/{aid}",
            json={"status": "done", "closure_justification": "Action non applicable, hors perimetre decret."},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"
        assert resp.json()["closure_justification"] is not None

    def test_operat_close_blocked_with_short_justification(self):
        """OPERAT action → done with justification < 10 chars → HTTP 400."""
        aid = self._create_operat_action("short_justif")
        resp = self.client.patch(f"/api/actions/{aid}", json={"status": "done", "closure_justification": "ok"})
        assert resp.status_code == 400

    def test_manual_close_always_allowed(self):
        """Non-OPERAT action → done without proof → allowed."""
        aid = self._create_manual_action("close")
        resp = self.client.patch(f"/api/actions/{aid}", json={"status": "done"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "done"

    def test_operat_status_change_non_done_allowed(self):
        """OPERAT action → in_progress → allowed (not done)."""
        aid = self._create_operat_action("in_progress")
        resp = self.client.patch(f"/api/actions/{aid}", json={"status": "in_progress"})
        assert resp.status_code == 200


# ── Closeability endpoint ────────────────────────────────────────────────────


class TestCloseabilityEndpoint:
    """GET /api/actions/{id}/closeability"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from main import app
        from fastapi.testclient import TestClient

        self.client = TestClient(app)
        # Ensure DemoState has a valid org
        from services.demo_state import DemoState

        if not DemoState.get_demo_org_id():
            from database import SessionLocal
            from models import Organisation

            db = SessionLocal()
            try:
                org = db.query(Organisation).first()
                if not org:
                    org = Organisation(
                        nom="V49 Test Org", type_client="tertiaire", actif=True, siren="999999999", is_demo=True
                    )
                    db.add(org)
                    db.commit()
                DemoState.set_demo_org(org_id=org.id, org_nom=org.nom)
            finally:
                db.close()

    def test_closeability_returns_shape(self):
        """Closeability endpoint returns expected fields."""
        import time

        tag = f"closeability_{int(time.time() * 1000)}"
        resp = self.client.post(
            "/api/actions",
            json={
                "title": "V49 closeability test",
                "source_type": "insight",
                "source_id": f"operat:99:2024:{tag}",
                "idempotency_key": f"v49_{tag}",
            },
        )
        aid = resp.json()["id"]

        resp = self.client.get(f"/api/actions/{aid}/closeability")
        assert resp.status_code == 200
        data = resp.json()
        assert "closable" in data
        assert "is_operat" in data
        assert "has_valid_proof" in data
        assert "has_justification" in data

    def test_closeability_404(self):
        resp = self.client.get("/api/actions/999999/closeability")
        assert resp.status_code == 404


# ── Source guards ────────────────────────────────────────────────────────────


class TestSourceGuardsV49:
    """Source code guards for V49 files."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        base = Path(__file__).resolve().parent.parent
        self.rules_code = (base / "services" / "action_close_rules.py").read_text(encoding="utf-8")
        self.route_code = (base / "routes" / "actions.py").read_text(encoding="utf-8")
        self.model_code = (base / "models" / "action_item.py").read_text(encoding="utf-8")

    def test_action_close_rules_has_is_operat(self):
        assert "def is_operat_action" in self.rules_code

    def test_action_close_rules_has_check_closable(self):
        assert "def check_closable" in self.rules_code

    def test_action_close_rules_checks_valid_proofs(self):
        assert "validated" in self.rules_code
        assert "decisional" in self.rules_code

    def test_action_close_rules_checks_justification_length(self):
        assert "10" in self.rules_code

    def test_route_imports_close_rules(self):
        assert "from services.action_close_rules import" in self.route_code

    def test_route_enforces_close_on_done(self):
        assert "check_closable" in self.route_code
        assert "is_operat_action" in self.route_code

    def test_route_has_closeability_endpoint(self):
        assert "closeability" in self.route_code
        assert "get_action_closeability" in self.route_code

    def test_model_has_closure_justification(self):
        assert "closure_justification" in self.model_code

    def test_route_serializes_closure_justification(self):
        assert "closure_justification" in self.route_code
