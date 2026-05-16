"""M2-3.C — Tests BaseRepositoryV4 : fail-closed + isolation org-scoping.

Sprint M2-3 commit M2-3.C.

Couvre :
- TestFailClosed (3) : list/get/create hors contexte → NoOrgContextError
- TestOrgIsolation (6) : create force scope, list filtre, get/update/delete
  bloquent cross-org, update ne change pas le scope
- TestExtensionHook (2) : _scope_column override + _apply_scope override-able
- TestRepoConstruction (1) : ValueError si 'model' absent

Total : 12 tests (cible prompt ~10).

Architecture test : `FakeEntity` SQLAlchemy in-memory SQLite (organisation_id
String — cohérent V4 models qui stockent UUID-as-string en SQLite). Le contexte
org est set DIRECTEMENT via set_org_context() — pas de JWT (cf. dette JWT/UUID
documentée dans org_context.py : la chaîne réelle JWT→repo = Sprint M2-4).
"""

import pytest
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from middleware.org_context import (
    NoOrgContextError,
    reset_org_context,
    set_org_context,
)
from repositories.base_v4 import BaseRepositoryV4, OrgScopeViolation

# Base de test isolée (ne pollue pas models.base.Base)
_TestBase = declarative_base()


class FakeEntity(_TestBase):
    """Model de test minimal avec organisation_id (cohérent V4 models)."""

    __tablename__ = "fake_entity_test_m2_3_c"
    id = Column(Integer, primary_key=True)
    organisation_id = Column(String, nullable=False, index=True)
    name = Column(String)


class FakeTenantEntity(_TestBase):
    """Model de test avec colonne org nommée différemment (test _scope_column)."""

    __tablename__ = "fake_tenant_entity_test_m2_3_c"
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
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
    """Contexte org 'org-a' (reset auto en fin de test)."""
    token = set_org_context("org-a")
    yield "org-a"
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
        obj = repo.create(name="foo", organisation_id="org-malicious")
        assert obj.organisation_id == "org-a", (
            "create() doit forcer organisation_id depuis le contexte (defense in depth)"
        )

    def test_list_all_filters_by_current_org(self, db_session, org_a):
        """list_all() ne retourne QUE les rows de l'org courante."""
        repo = FakeRepo(db_session)
        repo.create(name="from-a-1")
        repo.create(name="from-a-2")
        # Bascule contexte org-b et seed
        token_b = set_org_context("org-b")
        try:
            repo.create(name="from-b-1")
        finally:
            reset_org_context(token_b)
        # Retour contexte org-a (fixture)
        results = repo.list_all()
        assert len(results) == 2
        assert all(r.organisation_id == "org-a" for r in results)

    def test_get_blocks_cross_org_access(self, db_session, org_a):
        """get() d'un objet d'une autre org → None (IDOR bloqué, anti-énumération)."""
        repo = FakeRepo(db_session)
        obj_a = repo.create(name="from-a")
        a_id = obj_a.id
        # Bascule org-b
        token_b = set_org_context("org-b")
        try:
            assert repo.get(a_id) is None, "get() cross-org doit retourner None"
        finally:
            reset_org_context(token_b)

    def test_update_blocks_cross_org_write(self, db_session, org_a):
        """update() d'un objet d'une autre org → OrgScopeViolation."""
        repo = FakeRepo(db_session)
        obj_a = repo.create(name="from-a")
        token_b = set_org_context("org-b")
        try:
            with pytest.raises(OrgScopeViolation):
                repo.update(obj_a, name="hijacked")
        finally:
            reset_org_context(token_b)

    def test_update_cannot_change_org_id(self, db_session, org_a):
        """update() ne peut JAMAIS changer organisation_id (objet ne migre pas d'org)."""
        repo = FakeRepo(db_session)
        obj_a = repo.create(name="from-a")
        repo.update(obj_a, organisation_id="org-malicious", name="renamed")
        assert obj_a.organisation_id == "org-a", "organisation_id inchangé"
        assert obj_a.name == "renamed", "les autres champs sont bien mis à jour"

    def test_delete_blocks_cross_org(self, db_session, org_a):
        """delete() d'un objet d'une autre org → OrgScopeViolation."""
        repo = FakeRepo(db_session)
        obj_a = repo.create(name="from-a")
        token_b = set_org_context("org-b")
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
        assert obj.tenant_id == "org-a"
        # list_all() filtre bien sur tenant_id
        results = repo.list_all()
        assert len(results) == 1
        assert results[0].tenant_id == "org-a"

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
# 4. Construction — 1 test
# ═════════════════════════════════════════════════════════════════════


class TestRepoConstruction:
    """Garde-fou construction : un repo sans 'model' échoue au boot."""

    def test_repo_without_model_attr_raises(self, db_session):
        """BaseRepositoryV4 sous-classé sans 'model' → ValueError (fail-fast)."""

        class BrokenRepo(BaseRepositoryV4):
            pass  # pas de `model`

        with pytest.raises(ValueError, match="must define a 'model'"):
            BrokenRepo(db_session)
