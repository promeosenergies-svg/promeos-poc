"""Phase 1.4 — Source-guards user typology_override.

Vérifie :
1. `user_preferences.typology_override` prioritaire sur scope auto-détecté
2. `typology_override = None` → auto-détection NAF reprend la main
3. Helpers `get_or_create_user_preference` / `get_user_typology_override`
4. `PUT /api/user/preferences/typology` avec UNKNOWN → 400
5. `PUT /api/user/preferences/typology` avec null → reset override
6. `GET /api/user/preferences/typology` retourne l'état courant

Décision Amine 2026-05-01 (Phase 1.4) — permettre à un CFO d'une org mixte
de figer une typologie pour ses narratives, sans modifier le NAF officiel
(qui reste source de vérité réglementaire).

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 1.4.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from doctrine.naf_to_typology import OrganizationTypology
from main import app
from middleware.auth import get_current_user
from models import (
    Base,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
    User,
    UserPreference,
)
from routes.user_preferences import (
    get_or_create_user_preference,
    get_user_typology_override,
)
from services.iam_service import hash_password
from services.narrative.typology_resolver import resolve_typology_for_scope


# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def helios_user(db_session):
    """User authentifié + org HELIOS-like (GRAND_GROUPE auto-détecté)."""
    org = Organisation(nom="HELIOS Test", type_client="bureau", actif=True)
    db_session.add(org)
    db_session.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="HELIOS EJ", siren="111111111")
    db_session.add(ej)
    db_session.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="HELIOS PF")
    db_session.add(pf)
    db_session.flush()

    # Site GRAND_GROUPE dominant — NAF 6820B (préfixe 68 → GRAND_GROUPE)
    site = Site(
        portefeuille_id=pf.id,
        nom="Siège Paris",
        type=TypeSite.BUREAU,
        naf_code="6820B",
        surface_m2=3500,
        actif=True,
    )
    db_session.add(site)

    user = User(
        email="cfo@helios.test",
        hashed_password=hash_password("test123"),
        nom="Test",
        prenom="CFO",
        actif=True,
    )
    db_session.add(user)
    db_session.commit()

    return user, org, site


@pytest.fixture
def client(db_session, helios_user):
    """TestClient avec auth override → user authentifié = helios_user."""
    user, _, _ = helios_user

    def _override_db():
        try:
            yield db_session
        finally:
            pass

    def _override_user():
        return user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    yield TestClient(app)
    app.dependency_overrides.clear()


# ─── Tests helpers ──────────────────────────────────────────────────────────


class TestUserPreferenceHelpers:
    """Source-guards helpers `get_or_create_user_preference` et `get_user_typology_override`."""

    def test_get_or_create_creates_when_missing(self, db_session, helios_user):
        user, _, _ = helios_user
        # Pas encore de préférence
        assert db_session.query(UserPreference).filter_by(user_id=user.id).count() == 0
        pref = get_or_create_user_preference(db_session, user.id)
        assert pref is not None
        assert pref.user_id == user.id
        assert pref.typology_override is None

    def test_get_or_create_returns_existing(self, db_session, helios_user):
        user, _, _ = helios_user
        pref1 = get_or_create_user_preference(db_session, user.id)
        pref1.typology_override = OrganizationTypology.COMMERCE
        db_session.commit()

        pref2 = get_or_create_user_preference(db_session, user.id)
        assert pref2.id == pref1.id
        assert pref2.typology_override == OrganizationTypology.COMMERCE

    def test_get_user_typology_override_none_when_no_pref(self, db_session, helios_user):
        user, _, _ = helios_user
        assert get_user_typology_override(db_session, user.id) is None

    def test_get_user_typology_override_returns_value(self, db_session, helios_user):
        user, _, _ = helios_user
        pref = get_or_create_user_preference(db_session, user.id)
        pref.typology_override = OrganizationTypology.ERP
        db_session.commit()
        assert get_user_typology_override(db_session, user.id) == OrganizationTypology.ERP


# ─── Tests typology_resolver respecte override ──────────────────────────────


class TestTypologyResolverRespectUserOverride:
    """Source-guard CARDINAL : user override > auto-détection scope."""

    def test_typology_user_override_priority(self, db_session, helios_user):
        """Si user a override = COMMERCE, scope org HELIOS retourne COMMERCE.

        Sans override, l'org HELIOS-test devrait retourner GRAND_GROUPE
        (Site Siège Paris NAF 6820B). Avec override = COMMERCE, on doit
        respecter la préférence user.
        """
        user, org, _ = helios_user

        # Sans override : auto-détection → GRAND_GROUPE
        result_no_override = resolve_typology_for_scope({"org_id": org.id}, db_session, user_id=user.id)
        assert result_no_override == OrganizationTypology.GRAND_GROUPE

        # Avec override : COMMERCE forcé
        pref = get_or_create_user_preference(db_session, user.id)
        pref.typology_override = OrganizationTypology.COMMERCE
        db_session.commit()

        result_with_override = resolve_typology_for_scope({"org_id": org.id}, db_session, user_id=user.id)
        assert result_with_override == OrganizationTypology.COMMERCE, (
            "Phase 1.4 : user typology_override doit avoir priorité absolue sur l'auto-détection NAF"
        )

    def test_typology_override_overrides_site_scope(self, db_session, helios_user):
        """Override user prioritaire même sur scope site_id (le plus spécifique)."""
        user, _, site = helios_user
        pref = get_or_create_user_preference(db_session, user.id)
        pref.typology_override = OrganizationTypology.ERP
        db_session.commit()

        result = resolve_typology_for_scope({"site_id": site.id}, db_session, user_id=user.id)
        assert result == OrganizationTypology.ERP

    def test_typology_no_user_id_skips_override(self, db_session, helios_user):
        """Si user_id non fourni, override ignoré → auto-détection scope."""
        user, org, _ = helios_user
        pref = get_or_create_user_preference(db_session, user.id)
        pref.typology_override = OrganizationTypology.COMMERCE
        db_session.commit()

        # Pas de user_id passé → override ignoré
        result = resolve_typology_for_scope({"org_id": org.id}, db_session)
        assert result == OrganizationTypology.GRAND_GROUPE

    def test_typology_override_none_falls_back_to_auto(self, db_session, helios_user):
        """`typology_override = None` → auto-détection NAF reprend la main."""
        user, org, _ = helios_user
        pref = get_or_create_user_preference(db_session, user.id)
        pref.typology_override = OrganizationTypology.COMMERCE
        db_session.commit()

        # Reset override
        pref.typology_override = None
        db_session.commit()

        result = resolve_typology_for_scope({"org_id": org.id}, db_session, user_id=user.id)
        assert result == OrganizationTypology.GRAND_GROUPE


# ─── Tests endpoints PUT/GET ────────────────────────────────────────────────


class TestUserPreferencesEndpoints:
    """Source-guards endpoints `/api/user/preferences/typology`."""

    def test_get_typology_preference_initial_none(self, client, helios_user):
        """GET initial → typology_override = null (pas encore de préférence)."""
        user, _, _ = helios_user
        response = client.get("/api/user/preferences/typology")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user.id
        assert data["typology_override"] is None

    def test_put_typology_set_commerce(self, client, helios_user):
        """PUT typology=commerce → override sauvegardé."""
        response = client.put(
            "/api/user/preferences/typology",
            json={"typology": "commerce"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["typology_override"] == "commerce"

    def test_put_typology_reset_with_null(self, client, helios_user):
        """PUT typology=null → reset override."""
        # Set d'abord
        client.put("/api/user/preferences/typology", json={"typology": "etablissement_recevant_public"})
        # Reset
        response = client.put("/api/user/preferences/typology", json={"typology": None})
        assert response.status_code == 200
        assert response.json()["typology_override"] is None

    def test_put_typology_unknown_rejected(self, client, helios_user):
        """PUT typology=unknown → 400 (UNKNOWN n'est pas une préférence valide)."""
        response = client.put(
            "/api/user/preferences/typology",
            json={"typology": "unknown"},
        )
        assert response.status_code == 400
        # PROMEOS APIError contract → champ "message" (cf schemas/error.py)
        assert "UNKNOWN" in response.json()["message"]

    def test_put_then_get_persists(self, client, helios_user):
        """PUT puis GET → l'override est persisté."""
        client.put("/api/user/preferences/typology", json={"typology": "grand_groupe_tertiaire"})
        response = client.get("/api/user/preferences/typology")
        assert response.json()["typology_override"] == "grand_groupe_tertiaire"

    def test_put_typology_invalid_value_422(self, client, helios_user):
        """PUT avec typology inconnue → 422 (validation Pydantic)."""
        response = client.put(
            "/api/user/preferences/typology",
            json={"typology": "valeur_inconnue_xyz"},
        )
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
