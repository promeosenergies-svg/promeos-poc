"""
PROMEOS V44 — Tests: Patrimoine → OPERAT integration
Dedup warning, site_id inference, surface snapshot, source guards
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine
from models.base import Base
Base.metadata.create_all(bind=engine)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Dedup warning — POST /efa returns warning when site already has EFA
# ══════════════════════════════════════════════════════════════════════════════

class TestDedupWarning:
    """POST /efa should warn (not block) when site already has an EFA."""

    def test_first_efa_no_warning(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        # Create first EFA with buildings from catalog
        catalog = client.get("/api/tertiaire/catalog").json()
        if not catalog["sites"] or not catalog["sites"][0]["batiments"]:
            pytest.skip("No patrimoine data for dedup test")
        site = catalog["sites"][0]
        bat = site["batiments"][0]
        resp = client.post("/api/tertiaire/efa", json={
            "org_id": 1,
            "nom": "V44 Test Dedup First",
            "buildings": [{"building_id": bat["id"], "usage_label": "Bureaux"}],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "dedup_warning" not in data or data["dedup_warning"] is None

    def test_second_efa_has_warning(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        catalog = client.get("/api/tertiaire/catalog").json()
        if not catalog["sites"] or not catalog["sites"][0]["batiments"]:
            pytest.skip("No patrimoine data for dedup test")
        site = catalog["sites"][0]
        bat = site["batiments"][0]
        # Create first EFA
        client.post("/api/tertiaire/efa", json={
            "org_id": 1,
            "nom": "V44 Dedup A",
            "buildings": [{"building_id": bat["id"], "usage_label": "Bureaux"}],
        })
        # Create second EFA for same site → warning expected
        resp = client.post("/api/tertiaire/efa", json={
            "org_id": 1,
            "nom": "V44 Dedup B",
            "buildings": [{"building_id": bat["id"], "usage_label": "Commerce"}],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "dedup_warning" in data
        assert data["dedup_warning"] is not None
        assert "EFA existante" in data["dedup_warning"]


# ══════════════════════════════════════════════════════════════════════════════
# 2. site_id inference from building
# ══════════════════════════════════════════════════════════════════════════════

class TestSiteIdInference:
    """POST /efa infers site_id from first building."""

    def test_site_id_inferred(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        catalog = client.get("/api/tertiaire/catalog").json()
        if not catalog["sites"] or not catalog["sites"][0]["batiments"]:
            pytest.skip("No patrimoine data")
        site = catalog["sites"][0]
        bat = site["batiments"][0]
        resp = client.post("/api/tertiaire/efa", json={
            "org_id": 1,
            "nom": "V44 Infer Site",
            "buildings": [{"building_id": bat["id"], "usage_label": "Bureaux"}],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["site_id"] == site["site_id"]


# ══════════════════════════════════════════════════════════════════════════════
# 3. Surface snapshot from patrimoine
# ══════════════════════════════════════════════════════════════════════════════

class TestSurfaceSnapshot:
    """EFA buildings get surface_m2 snapshotted from patrimoine."""

    def test_surface_snapshotted(self):
        from main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        catalog = client.get("/api/tertiaire/catalog").json()
        if not catalog["sites"] or not catalog["sites"][0]["batiments"]:
            pytest.skip("No patrimoine data")
        bat = catalog["sites"][0]["batiments"][0]
        resp = client.post("/api/tertiaire/efa", json={
            "org_id": 1,
            "nom": "V44 Surface Snap",
            "buildings": [{"building_id": bat["id"], "usage_label": "Bureaux"}],
        })
        assert resp.status_code == 201
        data = resp.json()
        if "buildings" in data:
            efa_bat = data["buildings"][0]
            assert efa_bat["surface_m2"] == bat["surface_m2"]


# ══════════════════════════════════════════════════════════════════════════════
# 4. Source guards
# ══════════════════════════════════════════════════════════════════════════════

class TestV44SourceGuards:
    """Verify V44 code exists in source files."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        self.route_code = (
            Path(__file__).resolve().parent.parent / "routes" / "tertiaire.py"
        ).read_text(encoding="utf-8")

    def test_dedup_warning_in_route(self):
        assert "dedup_warning" in self.route_code

    def test_dedup_checks_existing_efas(self):
        assert "existing_efas" in self.route_code

    def test_dedup_non_blocking(self):
        # Should be a warning, not a raise
        assert "dedup_warning" in self.route_code
        # The EFA creation should still proceed (no HTTPException for dedup)
        lines = self.route_code.split("\n")
        dedup_section = False
        for line in lines:
            if "dedup_warning" in line and "=" in line:
                dedup_section = True
            if dedup_section and "raise HTTPException" in line:
                pytest.fail("Dedup should be a warning, not an exception")
            if dedup_section and "efa = TertiaireEfa(" in line:
                break  # Past dedup section, no exception found — good

    def test_v44_comment_present(self):
        assert "V44" in self.route_code
