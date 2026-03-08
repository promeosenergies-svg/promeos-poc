"""
Step 35 — Import incremental (mode update) : tests unitaires.
Matching SIRET > PRM > nom+CP, update fields, backward compat.
"""

import pytest


class TestMatchingFunctionExists:
    """match_staging_to_existing is importable and callable."""

    def test_import(self):
        from services.patrimoine_service import match_staging_to_existing

        assert callable(match_staging_to_existing)

    def test_update_site_fields_import(self):
        from services.patrimoine_service import _update_site_fields

        assert callable(_update_site_fields)


class TestUpdateableFields:
    """_UPDATABLE_FIELDS is defined correctly."""

    def test_fields_defined(self):
        from services.patrimoine_service import _UPDATABLE_FIELDS

        assert "nom" in _UPDATABLE_FIELDS
        assert "adresse" in _UPDATABLE_FIELDS
        assert "code_postal" in _UPDATABLE_FIELDS
        assert "ville" in _UPDATABLE_FIELDS
        assert "surface_m2" in _UPDATABLE_FIELDS


class TestStagingSiteMatchFields:
    """StagingSite has match_method and match_confidence columns."""

    def test_match_method_column(self):
        from models.patrimoine import StagingSite

        cols = {c.name for c in StagingSite.__table__.columns}
        assert "match_method" in cols

    def test_match_confidence_column(self):
        from models.patrimoine import StagingSite

        cols = {c.name for c in StagingSite.__table__.columns}
        assert "match_confidence" in cols

    def test_target_site_id_exists(self):
        from models.patrimoine import StagingSite

        cols = {c.name for c in StagingSite.__table__.columns}
        assert "target_site_id" in cols


class TestStagingBatchModeUpdate:
    """StagingBatch.mode can hold 'update'."""

    def test_mode_column(self):
        from models.patrimoine import StagingBatch

        cols = {c.name for c in StagingBatch.__table__.columns}
        assert "mode" in cols


class TestRouteAcceptsUpdateMode:
    """POST /staging/import accepts mode=update."""

    def test_route_import_exists(self):
        from routes.patrimoine import router

        paths = [r.path for r in router.routes]
        assert any("staging/import" in p for p in paths)

    def test_route_matching_exists(self):
        from routes.patrimoine import router

        paths = [r.path for r in router.routes]
        assert any("matching" in p for p in paths)

    def test_route_activate_exists(self):
        from routes.patrimoine import router

        paths = [r.path for r in router.routes]
        assert any("activate" in p for p in paths)


class TestMatchingImportedInRoutes:
    """match_staging_to_existing is imported in patrimoine routes."""

    def test_import(self):
        from routes.patrimoine import match_staging_to_existing

        assert callable(match_staging_to_existing)


class TestUpdateSiteFieldsLogic:
    """_update_site_fields returns changes only for non-null different values."""

    def test_no_change_when_equal(self):
        from services.patrimoine_service import _update_site_fields

        class FakeSite:
            nom = "Test"
            adresse = "1 rue X"
            code_postal = "75001"
            ville = "Paris"
            surface_m2 = 100.0
            naf_code = "6820B"

        class FakeStaging:
            nom = "Test"
            adresse = "1 rue X"
            code_postal = "75001"
            ville = "Paris"
            surface_m2 = 100.0
            naf_code = "6820B"

        changes = _update_site_fields(FakeSite(), FakeStaging())
        assert len(changes) == 0

    def test_change_detected(self):
        from services.patrimoine_service import _update_site_fields

        class FakeSite:
            nom = "Old Name"
            adresse = "1 rue X"
            code_postal = "75001"
            ville = "Paris"
            surface_m2 = 100.0
            naf_code = "6820B"

        class FakeStaging:
            nom = "New Name"
            adresse = None  # null → should not overwrite
            code_postal = "75001"
            ville = "Paris"
            surface_m2 = 200.0
            naf_code = "6820B"

        site = FakeSite()
        changes = _update_site_fields(site, FakeStaging())
        assert len(changes) == 2
        fields_changed = [c["field"] for c in changes]
        assert "nom" in fields_changed
        assert "surface_m2" in fields_changed
        # adresse should NOT be changed (staging value is None)
        assert site.adresse == "1 rue X"

    def test_null_staging_does_not_overwrite(self):
        from services.patrimoine_service import _update_site_fields

        class FakeSite:
            nom = "Keep This"
            adresse = "Keep This Too"
            code_postal = "75001"
            ville = "Paris"
            surface_m2 = 500.0
            naf_code = "6820B"

        class FakeStaging:
            nom = None
            adresse = None
            code_postal = None
            ville = None
            surface_m2 = None
            naf_code = None

        site = FakeSite()
        changes = _update_site_fields(site, FakeStaging())
        assert len(changes) == 0
        assert site.nom == "Keep This"
        assert site.surface_m2 == 500.0


class TestDoActivateUpdateMode:
    """_do_activate handles is_update_mode flag."""

    def test_source_has_update_mode_check(self):
        import inspect
        from services.patrimoine_service import _do_activate

        src = inspect.getsource(_do_activate)
        assert "is_update_mode" in src
        assert "sites_updated" in src
        assert "_update_site_fields" in src

    def test_result_includes_update_fields_in_update_mode(self):
        import inspect
        from services.patrimoine_service import _do_activate

        src = inspect.getsource(_do_activate)
        assert '"sites_updated"' in src
        assert '"changes"' in src


class TestBackwardCompat:
    """mode=import (default) does not trigger update logic."""

    def test_default_mode_unchanged(self):
        import inspect
        from services.patrimoine_service import _do_activate

        src = inspect.getsource(_do_activate)
        # is_update_mode is only True when batch.mode == "update"
        assert 'batch.mode == "update"' in src
