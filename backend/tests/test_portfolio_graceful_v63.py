"""
test_portfolio_graceful_v63.py — V63 : Portfolio Summary gracieux (200 empty)

Couverture :
  - DB vide (aucune org active) + aucun header → 200 (pas 403/401)
  - DEMO_MODE=false + aucun token → 200 empty grâce à get_portfolio_optional_auth
    (AVANT le fix : FastAPI retournait 401 avant même d'entrer dans la route)
  - Header X-Org-Id valide + org + site → 200 avec sites_count ≥ 1
  - Header X-Org-Id invalide (non-entier) → 200 empty (pas 422/500)
  - Header X-Org-Id pointant une org inexistante → 200 empty (pas 404)
  - Champs structurels V61/V62 présents dans la réponse 200 vide
  - get_portfolio_optional_auth appelée directement : token=None → None (jamais 401)
  - Backward compat : computed_at, sites_health, framework_breakdown présents

Scénarios de régression :
  - L'endpoint /portfolio-summary retourne toujours 200, jamais 401 ou 403.
  - Les champs V61 (sites_health) et V62 (trend) sont présents même en réponse vide.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models import Organisation, EntiteJuridique, Portefeuille, Site, TypeSite
from database import get_db
from main import app


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_demo_state():
    """Nettoie DemoState avant chaque test pour éviter la pollution entre suites.
    DemoState est un singleton global — d'autres tests peuvent le peupler,
    ce qui altère resolve_org_id (fallback DEMO_MODE=true → demo org).
    """
    from services.demo_state import DemoState

    DemoState.clear_demo_org()
    yield
    DemoState.clear_demo_org()


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def _override():
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_org_with_site(db, nom="OrgGraceful"):
    """Crée une org complète (EJ → Portefeuille → Site) pour les tests data."""
    org = Organisation(nom=nom, actif=True)
    db.add(org)
    db.flush()
    siren = str(abs(hash(nom)) % 10**9).zfill(9)
    ej = EntiteJuridique(nom="EJ " + nom, organisation_id=org.id, siren=siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom="PF " + nom, entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    site = Site(
        nom="Site " + nom,
        type=TypeSite.BUREAU,
        surface_m2=1000.0,
        portefeuille_id=pf.id,
        actif=True,
    )
    db.add(site)
    db.commit()
    return org, pf, site


EXPECTED_FIELDS = (
    "scope",
    "total_estimated_risk_eur",
    "sites_count",
    "sites_at_risk",
    "sites_health",
    "framework_breakdown",
    "top_sites",
    "trend",
    "computed_at",
)


# ── Groupe 1 : DB vide — 200 empty ───────────────────────────────────────────


class TestPortfolioGracefulEmptyDB:
    """DB complètement vide (aucune org) → 200 vide, jamais 401/403."""

    def test_empty_db_no_header_status_200(self, client, db):
        """DB vide + aucun header → HTTP 200 (pas 403)."""
        resp = client.get("/api/patrimoine/portfolio-summary")
        assert resp.status_code == 200, f"Attendu 200 gracieux, obtenu {resp.status_code}: {resp.text}"

    def test_empty_db_sites_count_zero(self, client, db):
        """DB vide → sites_count = 0."""
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["sites_count"] == 0

    def test_empty_db_zero_risk(self, client, db):
        """DB vide → total_estimated_risk_eur = 0.0."""
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["total_estimated_risk_eur"] == 0.0

    def test_empty_db_all_fields_present(self, client, db):
        """Réponse 200 vide contient tous les champs structurels."""
        data = client.get("/api/patrimoine/portfolio-summary").json()
        for field in EXPECTED_FIELDS:
            assert field in data, f"Champ manquant dans réponse vide : {field}"

    def test_empty_db_sites_health_structure(self, client, db):
        """DB vide → sites_health a les 4 sous-champs à 0."""
        sh = client.get("/api/patrimoine/portfolio-summary").json()["sites_health"]
        assert sh["healthy"] == 0
        assert sh["warning"] == 0
        assert sh["critical"] == 0
        assert sh["healthy_pct"] == 0.0

    def test_empty_db_trend_is_none(self, client, db):
        """DB vide → trend est None."""
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["trend"] is None

    def test_empty_db_framework_breakdown_empty_list(self, client, db):
        """DB vide → framework_breakdown = []."""
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["framework_breakdown"] == []

    def test_empty_db_top_sites_empty_list(self, client, db):
        """DB vide → top_sites = []."""
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["top_sites"] == []

    def test_empty_db_scope_org_id_is_none(self, client, db):
        """DB vide → scope.org_id = None (org non résolue)."""
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["scope"]["org_id"] is None

    def test_empty_db_computed_at_is_string(self, client, db):
        """DB vide → computed_at est une chaîne ISO non vide."""
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert isinstance(data["computed_at"], str) and len(data["computed_at"]) > 0

    def test_empty_db_sites_at_risk_structure(self, client, db):
        """DB vide → sites_at_risk a les 4 niveaux à 0."""
        sar = client.get("/api/patrimoine/portfolio-summary").json()["sites_at_risk"]
        assert sar.get("critical", -1) == 0
        assert sar.get("high", -1) == 0
        assert sar.get("medium", -1) == 0
        assert sar.get("low", -1) == 0


# ── Groupe 2 : DEMO_MODE=false (scénario production) ─────────────────────────


class TestPortfolioGracefulDemoModeFalse:
    """
    Simule la production (DEMO_MODE=false).

    AVANT le fix V63 :
      - get_optional_auth levait HTTPException(401) côté FastAPI dependency
        → la route ne s'exécutait JAMAIS → 401 → bandeau d'erreur frontend.
    APRÈS le fix V63 :
      - get_portfolio_optional_auth (jamais de raise) → route s'exécute
      - _get_org_id échoue (DEMO_MODE=false, pas d'org) → try/except → 200 empty.
    """

    def test_demo_false_no_token_returns_200(self, client, db, monkeypatch):
        """DEMO_MODE=false + aucun token → 200 (pas 401)."""
        import services.scope_utils as _su

        monkeypatch.setattr(_su, "DEMO_MODE", False)
        resp = client.get("/api/patrimoine/portfolio-summary")
        assert resp.status_code == 200, (
            f"DEMO_MODE=false sans token devrait retourner 200 gracieux, obtenu {resp.status_code}: {resp.text}"
        )

    def test_demo_false_no_token_sites_count_zero(self, client, db, monkeypatch):
        """DEMO_MODE=false + aucun token → sites_count = 0."""
        import services.scope_utils as _su

        monkeypatch.setattr(_su, "DEMO_MODE", False)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert data["sites_count"] == 0

    def test_demo_false_no_token_all_fields_present(self, client, db, monkeypatch):
        """DEMO_MODE=false + aucun token → tous les champs structurels présents."""
        import services.scope_utils as _su

        monkeypatch.setattr(_su, "DEMO_MODE", False)
        data = client.get("/api/patrimoine/portfolio-summary").json()
        for field in EXPECTED_FIELDS:
            assert field in data, f"Champ manquant: {field}"

    def test_demo_false_with_valid_xorgid_returns_data(self, client, db, monkeypatch):
        """DEMO_MODE=false + X-Org-Id valide → 200 avec données réelles."""
        import services.scope_utils as _su

        monkeypatch.setattr(_su, "DEMO_MODE", False)
        org, _, _ = _make_org_with_site(db, "OrgDemoFalseData")
        resp = client.get(
            "/api/patrimoine/portfolio-summary",
            headers={"X-Org-Id": str(org.id)},
        )
        assert resp.status_code == 200
        assert resp.json()["sites_count"] >= 1

    def test_demo_false_invalid_xorgid_returns_200(self, client, db, monkeypatch):
        """DEMO_MODE=false + X-Org-Id non-entier → 200 empty (pas 422)."""
        import services.scope_utils as _su

        monkeypatch.setattr(_su, "DEMO_MODE", False)
        resp = client.get(
            "/api/patrimoine/portfolio-summary",
            headers={"X-Org-Id": "not-a-number"},
        )
        assert resp.status_code == 200
        assert resp.json()["sites_count"] == 0


# ── Groupe 3 : Header X-Org-Id valide ────────────────────────────────────────


class TestPortfolioGracefulWithOrgHeader:
    """Header X-Org-Id fourni → réponse avec données réelles."""

    def test_valid_xorgid_returns_sites_count(self, client, db):
        """X-Org-Id valide + 1 site → sites_count ≥ 1."""
        org, _, _ = _make_org_with_site(db, "OrgHeaderData")
        data = client.get(
            "/api/patrimoine/portfolio-summary",
            headers={"X-Org-Id": str(org.id)},
        ).json()
        assert data["sites_count"] >= 1

    def test_valid_xorgid_scope_matches(self, client, db):
        """X-Org-Id = org.id → scope.org_id = org.id dans la réponse."""
        org, _, _ = _make_org_with_site(db, "OrgScopeMatch")
        data = client.get(
            "/api/patrimoine/portfolio-summary",
            headers={"X-Org-Id": str(org.id)},
        ).json()
        assert data["scope"]["org_id"] == org.id

    def test_unknown_xorgid_returns_200_empty(self, client, db):
        """X-Org-Id pointant une org inexistante → 200 avec sites_count=0 (pas 404)."""
        resp = client.get(
            "/api/patrimoine/portfolio-summary",
            headers={"X-Org-Id": "999999"},
        )
        assert resp.status_code == 200
        assert resp.json()["sites_count"] == 0

    def test_invalid_xorgid_format_returns_200(self, client, db):
        """X-Org-Id='abc' (non-entier) → 200 empty (scope_utils ignore la valeur)."""
        resp = client.get(
            "/api/patrimoine/portfolio-summary",
            headers={"X-Org-Id": "abc"},
        )
        assert resp.status_code == 200
        # Pas de crash, sites_count = 0 (org non résolue ou org 0 introuvable)
        assert resp.json()["sites_count"] == 0


# ── Groupe 4 : Test unitaire get_portfolio_optional_auth ─────────────────────


class TestGetPortfolioOptionalAuthUnit:
    """
    Appel direct de get_portfolio_optional_auth — vérifie qu'elle ne lève JAMAIS.
    """

    def test_no_token_returns_none(self, db):
        """token=None → retourne None (JAMAIS HTTPException)."""
        from middleware.auth import get_portfolio_optional_auth

        result = get_portfolio_optional_auth(token=None, db=db)
        assert result is None

    def test_bad_token_returns_none(self, db):
        """Token invalide → retourne None (JAMAIS HTTPException)."""
        from middleware.auth import get_portfolio_optional_auth

        result = get_portfolio_optional_auth(token="garbage.token.value", db=db)
        assert result is None

    def test_no_raise_on_any_input(self, db):
        """Aucune exception ne doit remonter, quelle que soit l'entrée."""
        from middleware.auth import get_portfolio_optional_auth

        for bad_token in (None, "", "bad", "a.b.c", "Bearer xyz"):
            try:
                result = get_portfolio_optional_auth(token=bad_token, db=db)
                # Doit retourner None, pas lever
                assert result is None, f"Attendu None pour token={bad_token!r}"
            except Exception as exc:
                pytest.fail(f"get_portfolio_optional_auth a levé une exception pour token={bad_token!r} : {exc!r}")

    def test_function_exists_in_auth_module(self):
        """get_portfolio_optional_auth est bien exporté depuis middleware.auth."""
        import middleware.auth as _auth

        assert hasattr(_auth, "get_portfolio_optional_auth")
        assert callable(_auth.get_portfolio_optional_auth)


# ── Groupe 5 : Régression V61/V62 ─────────────────────────────────────────────


class TestPortfolioGracefulRegressionV61V62:
    """Vérifie que les champs V61/V62 sont présents même en réponse vide."""

    def test_sites_health_keys_in_empty_response(self, client, db):
        """sites_health avec 4 sous-clés dans réponse vide (V61 backward compat)."""
        sh = client.get("/api/patrimoine/portfolio-summary").json()["sites_health"]
        for key in ("healthy", "warning", "critical", "healthy_pct"):
            assert key in sh, f"Clé V61 manquante dans sites_health: {key}"

    def test_trend_key_present_in_empty_response(self, client, db):
        """trend présent dans réponse vide (V62 backward compat)."""
        data = client.get("/api/patrimoine/portfolio-summary").json()
        assert "trend" in data

    def test_scope_keys_in_empty_response(self, client, db):
        """scope avec org_id/portefeuille_id/site_id dans réponse vide."""
        scope = client.get("/api/patrimoine/portfolio-summary").json()["scope"]
        assert "org_id" in scope
        assert "portefeuille_id" in scope
        assert "site_id" in scope

    def test_no_401_regression(self, client, db):
        """L'endpoint ne doit JAMAIS retourner 401 (régression fix V63)."""
        for _ in range(3):
            resp = client.get("/api/patrimoine/portfolio-summary")
            assert resp.status_code != 401, "Régression V63 : l'endpoint a retourné 401"

    def test_no_403_regression(self, client, db):
        """L'endpoint ne doit JAMAIS retourner 403 (régression fix V63)."""
        for _ in range(3):
            resp = client.get("/api/patrimoine/portfolio-summary")
            assert resp.status_code != 403, "Régression V63 : l'endpoint a retourné 403"
