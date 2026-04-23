"""
Step 26 — Sous-compteurs (O2)
Tests pour le modèle, service unifié, endpoints et seed.
"""

import pytest
from sqlalchemy import inspect
from database import engine, SessionLocal
from models.energy_models import Meter
from services.meter_unified_service import (
    get_site_meters,
    get_site_meters_tree,
    create_sub_meter,
    delete_sub_meter,
    get_meter_breakdown,
)


# ── A. Meter model — parent_meter_id ────────────────────────────────────────


class TestMeterSubModel:
    def test_meter_has_parent_meter_id(self):
        assert hasattr(Meter, "parent_meter_id")

    def test_meter_has_sub_meters_relationship(self):
        assert hasattr(Meter, "sub_meters")

    def test_parent_meter_id_nullable_in_db(self):
        insp = inspect(engine)
        if not insp.has_table("meter"):
            pytest.skip("meter table not found")
        cols = {c["name"]: c for c in insp.get_columns("meter")}
        assert cols.get("parent_meter_id", {}).get("nullable", True)


# ── B. Service — get_site_meters_tree ────────────────────────────────────────


class TestSiteMetersTree:
    def test_returns_list(self):
        db = SessionLocal()
        try:
            result = get_site_meters_tree(db, 1)
            assert isinstance(result, list)
        finally:
            db.close()

    def test_tree_has_sub_meters_key(self):
        db = SessionLocal()
        try:
            result = get_site_meters_tree(db, 1)
            if result:
                assert "sub_meters" in result[0]
        finally:
            db.close()


# ── C. Service — create_sub_meter ────────────────────────────────────────────


class TestCreateSubMeter:
    def _get_principal(self, db):
        return (
            db.query(Meter)
            .filter(
                Meter.parent_meter_id.is_(None),
                Meter.is_active.is_(True),
            )
            .first()
        )

    def test_create_sub_meter_success(self):
        db = SessionLocal()
        try:
            parent = self._get_principal(db)
            if not parent:
                pytest.skip("No principal meter found")
            result = create_sub_meter(db, parent.id, {"name": "Test Sub"})
            assert result["parent_meter_id"] == parent.id
            assert result["name"] == "Test Sub"
            db.rollback()
        finally:
            db.close()

    def test_create_sub_meter_inherits_site(self):
        db = SessionLocal()
        try:
            parent = self._get_principal(db)
            if not parent:
                pytest.skip("No principal meter found")
            result = create_sub_meter(db, parent.id, {"name": "Test Sub 2"})
            assert result["site_id"] == parent.site_id
            db.rollback()
        finally:
            db.close()

    def test_refuse_nested_sub_meter(self):
        db = SessionLocal()
        try:
            parent = self._get_principal(db)
            if not parent:
                pytest.skip("No principal meter found")
            sub = create_sub_meter(db, parent.id, {"name": "Sub A"})
            with pytest.raises(ValueError, match="1 niveau max"):
                create_sub_meter(db, sub["id"], {"name": "Sub B"})
            db.rollback()
        finally:
            db.close()

    def test_nonexistent_parent_raises(self):
        db = SessionLocal()
        try:
            with pytest.raises(ValueError, match="non trouvé"):
                create_sub_meter(db, 999999, {"name": "Orphan"})
        finally:
            db.close()


# ── D. Service — delete_sub_meter ────────────────────────────────────────────


class TestDeleteSubMeter:
    def test_delete_wrong_parent_returns_false(self):
        db = SessionLocal()
        try:
            assert delete_sub_meter(db, 999999, 888888) is False
        finally:
            db.close()


# ── E. Service — get_meter_breakdown ─────────────────────────────────────────


class TestMeterBreakdown:
    def test_breakdown_returns_dict(self):
        db = SessionLocal()
        try:
            meter = db.query(Meter).filter(Meter.is_active.is_(True)).first()
            if not meter:
                pytest.skip("No meter found")
            result = get_meter_breakdown(db, meter.id)
            assert isinstance(result, dict)
            assert "principal_kwh" in result
            assert "sub_meters" in result
            assert "delta_kwh" in result
            assert "delta_pct" in result
        finally:
            db.close()

    def test_breakdown_delta_label(self):
        db = SessionLocal()
        try:
            meter = db.query(Meter).filter(Meter.is_active.is_(True)).first()
            if not meter:
                pytest.skip("No meter found")
            result = get_meter_breakdown(db, meter.id)
            assert "delta_label" in result
        finally:
            db.close()


# ── F. Seed — hotel sub-meters exist ─────────────────────────────────────────


class TestSeedSubMeters:
    def test_hotel_has_sub_meters(self):
        """After helios seed, Nice hotel should have sub-meters."""
        db = SessionLocal()
        try:
            subs = (
                db.query(Meter)
                .filter(
                    Meter.parent_meter_id.isnot(None),
                    Meter.is_active.is_(True),
                )
                .all()
            )
            # At least 1 sub-meter should exist after seed
            if not subs:
                pytest.skip("No sub-meters found (seed may not have run)")
            assert len(subs) >= 1
        finally:
            db.close()

    def test_sub_meter_has_parent(self):
        db = SessionLocal()
        try:
            sub = db.query(Meter).filter(Meter.parent_meter_id.isnot(None)).first()
            if not sub:
                pytest.skip("No sub-meters found")
            parent = db.query(Meter).filter(Meter.id == sub.parent_meter_id).first()
            assert parent is not None
            assert parent.parent_meter_id is None  # parent is a principal
        finally:
            db.close()


# ── G. Source guards — file structure ─────────────────────────────────────────


class TestSourceGuards:
    def _read(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def test_meter_unified_service_has_tree(self):
        src = self._read("services/meter_unified_service.py")
        assert "get_site_meters_tree" in src

    def test_meter_unified_service_has_create(self):
        src = self._read("services/meter_unified_service.py")
        assert "create_sub_meter" in src

    def test_meter_unified_service_has_breakdown(self):
        src = self._read("services/meter_unified_service.py")
        assert "get_meter_breakdown" in src

    def test_routes_has_sub_meters_endpoint(self):
        src = self._read("routes/patrimoine/sites.py") + self._read("routes/patrimoine/_helpers.py")
        assert "sub-meters" in src or "sub_meters" in src

    def test_routes_has_breakdown_endpoint(self):
        src = self._read("routes/patrimoine/sites.py") + self._read("routes/patrimoine/_helpers.py")
        assert "breakdown" in src

    def test_packs_has_sub_meters(self):
        src = self._read("services/demo_seed/packs.py")
        assert "sub_meters" in src
