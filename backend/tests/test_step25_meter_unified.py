"""
Step 25 — Unification Compteur → Meter
Tests pour le modèle Meter enrichi et le service unifié.
"""

import pytest
from sqlalchemy import inspect
from database import engine, SessionLocal
from models.energy_models import Meter
from models.enums import EnergyVector
from services.meter_unified_service import get_site_meters, _infer_type, _type_to_vector


# ── A. Meter model columns ─────────────────────────────────────────────────


class TestMeterModel:
    """Verify Meter has the new unified columns."""

    def test_meter_has_numero_serie(self):
        assert hasattr(Meter, "numero_serie")

    def test_meter_has_type_compteur(self):
        assert hasattr(Meter, "type_compteur")

    def test_meter_has_marque(self):
        assert hasattr(Meter, "marque")

    def test_meter_has_modele(self):
        assert hasattr(Meter, "modele")

    def test_meter_has_parent_meter_id(self):
        assert hasattr(Meter, "parent_meter_id")

    def test_meter_has_delivery_point_id(self):
        assert hasattr(Meter, "delivery_point_id")

    def test_meter_has_date_derniere_releve(self):
        assert hasattr(Meter, "date_derniere_releve")

    def test_meter_has_sub_meters_relationship(self):
        assert hasattr(Meter, "sub_meters")

    def test_meter_new_columns_nullable(self):
        """All new columns accept NULL."""
        insp = inspect(engine)
        if not insp.has_table("meter"):
            pytest.skip("meter table not found")
        cols = {c["name"]: c for c in insp.get_columns("meter")}
        for col_name in (
            "numero_serie",
            "type_compteur",
            "marque",
            "modele",
            "date_derniere_releve",
            "delivery_point_id",
            "parent_meter_id",
        ):
            if col_name in cols:
                assert cols[col_name]["nullable"], f"{col_name} should be nullable"

    def test_parent_meter_id_nullable(self):
        """Meter sans parent → parent_meter_id=null."""
        insp = inspect(engine)
        if not insp.has_table("meter"):
            pytest.skip("meter table not found")
        cols = {c["name"]: c for c in insp.get_columns("meter")}
        assert cols.get("parent_meter_id", {}).get("nullable", True)


# ── B. Unified service helpers ──────────────────────────────────────────────


class TestHelpers:
    def test_infer_type_elec(self):
        assert _infer_type(EnergyVector.ELECTRICITY) == "electricite"

    def test_infer_type_gaz(self):
        assert _infer_type(EnergyVector.GAS) == "gaz"

    def test_infer_type_other(self):
        assert _infer_type(EnergyVector.OTHER) == "eau"

    def test_infer_type_none(self):
        assert _infer_type(None) is None

    def test_type_to_vector_elec(self):
        assert _type_to_vector("electricite") == "electricity"

    def test_type_to_vector_gaz(self):
        assert _type_to_vector("gaz") == "gas"

    def test_type_to_vector_none(self):
        assert _type_to_vector(None) is None


# ── C. Service integration (requires seeded DB) ────────────────────────────


class TestUnifiedService:
    def test_get_site_meters_returns_list(self):
        db = SessionLocal()
        try:
            # Use site_id=1 (should exist after seed)
            result = get_site_meters(db, 1)
            assert isinstance(result, list)
        finally:
            db.close()

    def test_get_site_meters_has_source_field(self):
        db = SessionLocal()
        try:
            result = get_site_meters(db, 1)
            if result:
                assert "source" in result[0]
                assert result[0]["source"] in ("meter", "compteur_legacy")
        finally:
            db.close()

    def test_get_site_meters_nonexistent_site(self):
        db = SessionLocal()
        try:
            result = get_site_meters(db, 999999)
            assert result == []
        finally:
            db.close()

    def test_seed_helios_meters_exist(self):
        """After seed, sites should have meters."""
        db = SessionLocal()
        try:
            from models import Site

            sites = db.query(Site).limit(5).all()
            has_meters = False
            for s in sites:
                meters = get_site_meters(db, s.id)
                if meters:
                    has_meters = True
                    break
            assert has_meters, "At least one seeded site should have meters"
        finally:
            db.close()


# ── D. Source guard — file structure ────────────────────────────────────────


class TestSourceGuard:
    def _read(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def test_meter_unified_service_exists(self):
        src = self._read("services/meter_unified_service.py")
        assert "get_site_meters" in src

    def test_meter_model_has_parent_meter_id(self):
        src = self._read("models/energy_models.py")
        assert "parent_meter_id" in src

    def test_meter_model_has_delivery_point_id(self):
        src = self._read("models/energy_models.py")
        assert "delivery_point_id" in src

    def test_patrimoine_routes_import_unified(self):
        src = self._read("routes/patrimoine.py")
        assert "meter_unified_service" in src or "get_site_meters" in src

    def test_patrimoine_routes_has_meters_endpoint(self):
        src = self._read("routes/patrimoine.py")
        assert "/meters" in src

    def test_activation_creates_meter(self):
        src = self._read("services/patrimoine_service.py")
        assert "Meter(" in src

    def test_migration_has_meter_unified_columns(self):
        src = self._read("database/migrations.py")
        assert "_add_meter_unified_columns" in src
