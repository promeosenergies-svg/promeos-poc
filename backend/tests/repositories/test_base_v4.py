"""M2-3.C / M2-4.1 — Tests BaseRepositoryV4 : fail-closed + isolation org-scoping.

Sprint M2-3 commit M2-3.C ; étendu Sprint M2-4.1 (chaîne réelle JWT → repo).

Couvre :
- TestFailClosed (3) : list/get/create hors contexte → NoOrgContextError
- TestOrgIsolation (6) : create force scope, list filtre, get/update/delete
  bloquent cross-org, update ne change pas le scope
- TestExtensionHook (2) : _scope_column override + _apply_scope override-able
- TestRepoConstruction (1) : ValueError si 'model' absent
- TestRealJwtPath (1) : chaîne réelle JWT → populate_org_context → current_org_id()
  (M2-4.1 — valide que ADR-009 Option D résout la dette JWT/UUID de M2-3.C)

Total : 13 tests.

Architecture test : `FakeEntity` SQLAlchemy in-memory SQLite (organisation_id
Integer — cohérent V4 models post-M2-4.1, ADR-009 Option D : Integer FK partagé
legacy↔V4). L'isolation org est testée via set_org_context() direct ;
TestRealJwtPath exerce en plus la dependency de prod `populate_org_context`
avec un JWT signé (la chaîne JWT → repo, désormais bouclée).
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from middleware.org_context import (
    NoOrgContextError,
    current_org_id,
    populate_org_context,
    reset_org_context,
    set_org_context,
)
from repositories.base_v4 import BaseRepositoryV4, OrgScopeViolation
from services.iam_service import create_access_token

# Base de test isolée (ne pollue pas models.base.Base)
_TestBase = declarative_base()


class FakeEntity(_TestBase):
    """Model de test minimal avec organisation_id Integer (cohérent V4 models post-M2-4.1)."""

    __tablename__ = "fake_entity_test_m2_3_c"
    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, nullable=False, index=True)  # M2-4.1 : Integer (was String/UUID)
    name = Column(String)


class FakeTenantEntity(_TestBase):
    """Model de test avec colonne org nommée différemment (test _scope_column)."""

    __tablename__ = "fake_tenant_entity_test_m2_3_c"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, nullable=False, index=True)  # M2-4.1 : Integer
    name = Column(String)


class FakeRepo(BaseRepositoryV4[FakeEntity]):
    """Repo concret de test — scope_column défaut 'organisation_id'."""

    model = FakeEntity


class FakeTenantRepo(BaseRepositoryV4[FakeTenantEntity]):
    """Repo concret de test — _scope_column overridé 'tenant_id' (cas simple)."""

    model = FakeTenantEntity
    _scope_column = "tenant_id"


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def db_session():
    """Session SQLAlchemy in-memory SQLite avec les 2 tables de test."""
    engine = create_engine("sqlite:///:memory:", future=True)
    _TestBase.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    session = SessionLocal()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def org_a():
    """Contexte org 1 (reset auto en fin de test). M2-4.1 : int (was 'org-a' str)."""
    token = set_org_context(1)
    yield 1
    reset_org_context(token)


# ═════════════════════════════════════════════════════════════════════
# 1. Fail-closed — 3 tests cardinaux
# ═════════════════════════════════════════════════════════════════════


class TestFailClosed:
    """🛡️ Sans contexte org → exception immédiate (pas de fuite silencieuse)."""

    def test_list_all_without_context_raises(self, db_session):
        """list_all() hors contexte → NoOrgContextError."""
        repo = FakeRepo(db_session)
        with pytest.raises(NoOrgContextError):
            repo.list_all()

    def test_get_without_context_raises(self, db_session):
        """get() hors contexte → NoOrgContextError."""
        repo = FakeRepo(db_session)
        with pytest.raises(NoOrgContextError):
            repo.get(1)

    def test_create_without_context_raises(self, db_session):
        """create() hors contexte → NoOrgContextError."""
        repo = FakeRepo(db_session)
        with pytest.raises(NoOrgContextError):
            repo.create(name="foo")


# ═════════════════════════════════════════════════════════════════════
# 2. Org isolation — 6 tests
# ═════════════════════════════════════════════════════════════════════


class TestOrgIsolation:
    """🛡️ Isolation org : impossible d'accéder aux données d'un autre tenant."""

    def test_create_force_sets_org_id_from_context(self, db_session, org_a):
        """create() FORCE organisation_id = contexte, même si caller en passe un autre."""
        repo = FakeRepo(db_session)
        obj = repo.create(name="foo", organisation_id=999)
        assert obj.organisation_id == 1, "create() doit forcer organisation_id depuis le contexte (defense in depth)"

    def test_list_all_filters_by_current_org(self, db_session, org_a):
        """list_all() ne retourne QUE les rows de l'org courante."""
        repo = FakeRepo(db_session)
        repo.create(name="from-a-1")
        repo.create(name="from-a-2")
        # Bascule contexte org 2 et seed
        token_b = set_org_context(2)
        try:
            repo.create(name="from-b-1")
        finally:
            reset_org_context(token_b)
        # Retour contexte org 1 (fixture)
        results = repo.list_all()
        assert len(results) == 2
        assert all(r.organisation_id == 1 for r in results)

    def test_get_blocks_cross_org_access(self, db_session, org_a):
        """get() d'un objet d'une autre org → None (IDOR bloqué, anti-énumération)."""
        repo = FakeRepo(db_session)
        obj_a = repo.create(name="from-a")
        a_id = obj_a.id
        # Bascule org 2
        token_b = set_org_context(2)
        try:
            assert repo.get(a_id) is None, "get() cross-org doit retourner None"
        finally:
            reset_org_context(token_b)

    def test_update_blocks_cross_org_write(self, db_session, org_a):
        """update() d'un objet d'une autre org → OrgScopeViolation."""
        repo = FakeRepo(db_session)
        obj_a = repo.create(name="from-a")
        token_b = set_org_context(2)
        try:
            with pytest.raises(OrgScopeViolation):
                repo.update(obj_a, name="hijacked")
        finally:
            reset_org_context(token_b)

    def test_update_cannot_change_org_id(self, db_session, org_a):
        """update() ne peut JAMAIS changer organisation_id (objet ne migre pas d'org)."""
        repo = FakeRepo(db_session)
        obj_a = repo.create(name="from-a")
        repo.update(obj_a, organisation_id=999, name="renamed")
        assert obj_a.organisation_id == 1, "organisation_id inchangé"
        assert obj_a.name == "renamed", "les autres champs sont bien mis à jour"

    def test_delete_blocks_cross_org(self, db_session, org_a):
        """delete() d'un objet d'une autre org → OrgScopeViolation."""
        repo = FakeRepo(db_session)
        obj_a = repo.create(name="from-a")
        token_b = set_org_context(2)
        try:
            with pytest.raises(OrgScopeViolation):
                repo.delete(obj_a)
        finally:
            reset_org_context(token_b)


# ═════════════════════════════════════════════════════════════════════
# 3. Extension hook — 2 tests (guardrail user : extension hiérarchique)
# ═════════════════════════════════════════════════════════════════════


class TestExtensionHook:
    """Porte d'extension : _scope_column override + _apply_scope override-able."""

    def test_scope_column_override_simple_case(self, db_session, org_a):
        """_scope_column override → repo filtre sur 'tenant_id' au lieu de 'organisation_id'."""
        repo = FakeTenantRepo(db_session)
        obj = repo.create(name="tenant-scoped")
        # create() a forcé tenant_id depuis le contexte
        assert obj.tenant_id == 1
        # list_all() filtre bien sur tenant_id
        results = repo.list_all()
        assert len(results) == 1
        assert results[0].tenant_id == 1

    def test_apply_scope_is_overridable_for_hierarchy(self, db_session, org_a):
        """_apply_scope() est override-able : une sous-classe peut ajouter un filtre.

        Simule une future SiteScopedRepositoryV4 qui restreint à un sous-ensemble.
        Vérifie que super()._apply_scope() reste appelable (extension, pas réécriture).
        """
        captured = {}

        class HierarchicalRepo(BaseRepositoryV4[FakeEntity]):
            model = FakeEntity

            def _apply_scope(self, stmt):
                # Extension : org filter d'abord (base), puis filtre supplémentaire
                stmt = super()._apply_scope(stmt)
                captured["super_called"] = True
                # Ici une vraie sous-classe ajouterait .where(site_id.in_(...))
                return stmt.where(FakeEntity.name != "hidden")

        repo = HierarchicalRepo(db_session)
        repo.create(name="visible")
        repo.create(name="hidden")
        results = repo.list_all()
        assert captured.get("super_called") is True, "super()._apply_scope() doit rester appelable (OCP — extension)"
        names = {r.name for r in results}
        assert names == {"visible"}, "le filtre hiérarchique custom s'applique en plus de l'org"


# ═════════════════════════════════════════════════════════════════════
# 4. Real JWT path — 1 test d'intégration (M2-4.1 · dette M2-3.C résolue)
# ═════════════════════════════════════════════════════════════════════


class TestRealJwtPath:
    """🔗 M2-4.1 — la chaîne réelle JWT → populate_org_context → current_org_id() boucle.

    M2-3.C testait l'org-scoping via `set_org_context()` direct : le JWT legacy
    portait `org_id: int` mais les 8 models V4 utilisaient `organisation_id` UUID,
    donc la chaîne JWT → repo ne bouclait pas (dette documentée org_context.py).
    ADR-009 Option D (M2-4.1) migre les V4 vers `organisation_id` Integer FK
    partagé legacy↔V4 — le JWT alimente désormais le ContextVar sans mapping.
    Ce test valide ce câblage de bout en bout sur la VRAIE dependency de prod
    `populate_org_context` (montée dans une mini-app FastAPI isolée).
    """

    def test_real_jwt_path_populates_org_context(self):
        """JWT signé (org_id=42) → populate_org_context → current_org_id() == 42 (int)."""
        app = FastAPI()

        @app.get("/v4/whoami")
        async def whoami(_ctx=Depends(populate_org_context)):
            org_id = current_org_id()
            return {"org_id": org_id, "type": type(org_id).__name__}

        client = TestClient(app)
        token = create_access_token(user_id=1, org_id=42, role="dg_owner")
        response = client.get("/v4/whoami", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["org_id"] == 42, "le claim JWT `org_id` doit alimenter le ContextVar"
        assert isinstance(body["org_id"], int) and body["org_id"] > 0
        assert body["type"] == "int", (
            "ADR-009 Option D : le ContextVar V4 porte un int (Integer FK partagé "
            "legacy↔V4), pas un str/UUID — sinon la dette JWT/UUID M2-3.C subsiste"
        )


# ═════════════════════════════════════════════════════════════════════
# 5. Construction — 1 test
# ═════════════════════════════════════════════════════════════════════


class TestRepoConstruction:
    """Garde-fou construction : un repo sans 'model' échoue au boot."""

    def test_repo_without_model_attr_raises(self, db_session):
        """BaseRepositoryV4 sous-classé sans 'model' → ValueError (fail-fast)."""

        class BrokenRepo(BaseRepositoryV4):
            pass  # pas de `model`

        with pytest.raises(ValueError, match="must define a 'model'"):
            BrokenRepo(db_session)
