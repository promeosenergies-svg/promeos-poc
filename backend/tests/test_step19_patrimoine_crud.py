"""
Step 19 — O3 : CRUD Organisation / Entité / Portefeuille / Site
Tests unitaires pour schemas, route, et intégration.
"""

import pytest


# ============================================================
# Pydantic Schemas
# ============================================================

class TestSchemas:
    """Test Pydantic schemas validation."""

    def test_organisation_create_valid(self):
        from schemas.patrimoine_crud import OrganisationCreate
        o = OrganisationCreate(nom="Test Corp", type_client="tertiaire", siren="123456789")
        assert o.nom == "Test Corp"
        assert o.siren == "123456789"

    def test_organisation_create_siren_strip(self):
        from schemas.patrimoine_crud import OrganisationCreate
        o = OrganisationCreate(nom="Test", siren="123 456 789")
        assert o.siren == "123456789"

    def test_organisation_create_bad_siren(self):
        from schemas.patrimoine_crud import OrganisationCreate
        with pytest.raises(Exception):
            OrganisationCreate(nom="Test", siren="1234")

    def test_organisation_create_no_siren(self):
        from schemas.patrimoine_crud import OrganisationCreate
        o = OrganisationCreate(nom="Test")
        assert o.siren is None

    def test_entite_create_valid(self):
        from schemas.patrimoine_crud import EntiteJuridiqueCreate
        e = EntiteJuridiqueCreate(
            organisation_id=1, nom="Filiale A", siren="987654321",
            siret="98765432100012", naf_code="70.10"
        )
        assert e.siren == "987654321"
        assert e.siret == "98765432100012"

    def test_entite_create_bad_siren(self):
        from schemas.patrimoine_crud import EntiteJuridiqueCreate
        with pytest.raises(Exception):
            EntiteJuridiqueCreate(organisation_id=1, nom="Bad", siren="abc")

    def test_entite_create_bad_siret(self):
        from schemas.patrimoine_crud import EntiteJuridiqueCreate
        with pytest.raises(Exception):
            EntiteJuridiqueCreate(organisation_id=1, nom="Bad", siren="123456789", siret="123")

    def test_portefeuille_create_valid(self):
        from schemas.patrimoine_crud import PortefeuilleCreate
        p = PortefeuilleCreate(entite_juridique_id=1, nom="Retail IDF")
        assert p.nom == "Retail IDF"

    def test_site_create_valid(self):
        from schemas.patrimoine_crud import SiteCreate
        s = SiteCreate(portefeuille_id=1, nom="Bureau Paris", type="bureau")
        assert s.type == "bureau"

    def test_site_create_surface_negative(self):
        from schemas.patrimoine_crud import SiteCreate
        with pytest.raises(Exception):
            SiteCreate(portefeuille_id=1, nom="Bad", type="bureau", surface_m2=-100)

    def test_organisation_update_partial(self):
        from schemas.patrimoine_crud import OrganisationUpdate
        u = OrganisationUpdate(nom="New Name")
        dump = u.model_dump(exclude_unset=True)
        assert "nom" in dump
        assert "type_client" not in dump

    def test_site_update_partial(self):
        from schemas.patrimoine_crud import SiteUpdate
        u = SiteUpdate(ville="Lyon")
        dump = u.model_dump(exclude_unset=True)
        assert dump == {"ville": "Lyon"}


# ============================================================
# Route file guard
# ============================================================

class TestRouteCrud:
    """Test that CRUD route exists and has expected structure."""

    def test_route_importable(self):
        from routes.patrimoine_crud import router
        assert router.prefix == "/api/patrimoine/crud"

    def test_route_has_organisations(self):
        from routes.patrimoine_crud import router
        paths = [r.path for r in router.routes]
        assert any("organisations" in p for p in paths)

    def test_route_has_entites(self):
        from routes.patrimoine_crud import router
        paths = [r.path for r in router.routes]
        assert any("entites" in p for p in paths)

    def test_route_has_portefeuilles(self):
        from routes.patrimoine_crud import router
        paths = [r.path for r in router.routes]
        assert any("portefeuilles" in p for p in paths)

    def test_route_has_sites(self):
        from routes.patrimoine_crud import router
        paths = [r.path for r in router.routes]
        assert any("sites" in p for p in paths)

    def test_route_registered_in_init(self):
        from routes import patrimoine_crud_router
        assert patrimoine_crud_router.prefix == "/api/patrimoine/crud"


# ============================================================
# Endpoint method coverage
# ============================================================

class TestEndpointMethods:
    """Verify CRUD methods (GET/POST/PATCH/DELETE) are registered."""

    def _find_method(self, path_suffix: str, method: str) -> bool:
        from routes.patrimoine_crud import router
        for route in router.routes:
            path = getattr(route, "path", "")
            if path.endswith(path_suffix):
                if method in getattr(route, "methods", set()):
                    return True
        return False

    def test_organisations_get(self):
        assert self._find_method("/organisations", "GET")

    def test_organisations_post(self):
        assert self._find_method("/organisations", "POST")

    def test_organisations_patch(self):
        assert self._find_method("/organisations/{org_id}", "PATCH")

    def test_organisations_delete(self):
        assert self._find_method("/organisations/{org_id}", "DELETE")

    def test_entites_post(self):
        assert self._find_method("/entites", "POST")

    def test_portefeuilles_post(self):
        assert self._find_method("/portefeuilles", "POST")

    def test_sites_post(self):
        assert self._find_method("/sites", "POST")

    def test_sites_patch(self):
        assert self._find_method("/sites/{site_id}", "PATCH")

    def test_sites_delete(self):
        assert self._find_method("/sites/{site_id}", "DELETE")
