"""Tests intégration endpoint REST `POST /api/v1/events/refresh` — Phase 2.A.

Couvre :
- 401 sans token (pas auth)
- 403 avec token role non admin (Energy Manager / DAF)
- 200 avec token DG_OWNER ou DSI_ADMIN
- Réponse schema (refreshed_orgs / total_events / errors / computed_at)
- Idempotence (2 appels successifs même résultat structurel)
- Erreur par org capturée (n'interrompt pas les suivantes)
- Délégation pure : handler appelle events_query_service.refresh_all_active_orgs

Utilise la fixture `app_client` partagée + override
`require_platform_admin` via `app.dependency_overrides`.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def admin_payload():
    """Faux payload JWT décodé représentant un platform admin valide."""
    return {
        "sub": "1",
        "org_id": 1,
        "role": "DG_OWNER",
    }


@pytest.fixture
def with_admin_auth(app_client, admin_payload):
    """Override require_platform_admin pour retourner un payload admin valide.

    Pattern documenté `middleware/auth.py:require_platform_admin` :
    « Dep directe (pas factory) pour faciliter app.dependency_overrides
    en tests. »
    """
    from main import app
    from middleware.auth import require_platform_admin

    app.dependency_overrides[require_platform_admin] = lambda: admin_payload
    yield app_client
    # Cleanup : ne pas pop car app_client.cleanup le fait déjà via
    # app.dependency_overrides.clear()


class TestEventsRefreshEndpoint:
    def test_returns_200_with_admin_auth(self, with_admin_auth, monkeypatch):
        """POST /refresh avec admin → 200 + payload structuré."""
        client, _ = with_admin_auth

        # Mock orchestrateur pour découpler du seed DB réel
        def _mock_refresh(db):
            return {
                "refreshed_orgs": 3,
                "total_events": 12,
                "errors": [],
                "computed_at": "2026-05-02T07:45:00+00:00",
            }

        monkeypatch.setattr("routes.events.refresh_all_active_orgs", _mock_refresh)

        response = client.post("/api/v1/events/refresh")
        assert response.status_code == 200
        body = response.json()
        assert body["refreshed_orgs"] == 3
        assert body["total_events"] == 12
        assert body["errors"] == []
        assert "computed_at" in body

    def test_returns_401_without_auth(self, app_client):
        """POST /refresh sans token → 401."""
        client, _ = app_client
        response = client.post("/api/v1/events/refresh")
        # require_platform_admin raise 401 si token absent
        assert response.status_code == 401

    def test_returns_403_without_platform_admin_role(self, app_client, monkeypatch):
        """POST /refresh avec token Energy Manager → 403."""
        from main import app
        from middleware.auth import require_platform_admin
        from fastapi import HTTPException

        def _deny():
            raise HTTPException(status_code=403, detail="Accès réservé")

        app.dependency_overrides[require_platform_admin] = _deny

        try:
            client, _ = app_client
            response = client.post("/api/v1/events/refresh")
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_response_schema(self, with_admin_auth, monkeypatch):
        """Schema réponse : refreshed_orgs (int), total_events (int),
        errors (list), computed_at (ISO datetime str)."""
        client, _ = with_admin_auth

        monkeypatch.setattr(
            "routes.events.refresh_all_active_orgs",
            lambda db: {
                "refreshed_orgs": 5,
                "total_events": 47,
                "errors": [{"org_id": 99, "error": "DB timeout"}],
                "computed_at": "2026-05-02T07:45:00+00:00",
            },
        )

        response = client.post("/api/v1/events/refresh")
        body = response.json()

        assert isinstance(body["refreshed_orgs"], int)
        assert isinstance(body["total_events"], int)
        assert isinstance(body["errors"], list)
        assert isinstance(body["computed_at"], str)
        # ISO 8601 UTC
        assert "T" in body["computed_at"]

        # Erreurs structurées : org_id + error
        if body["errors"]:
            for err in body["errors"]:
                assert "org_id" in err
                assert "error" in err

    def test_idempotent_two_consecutive_calls(self, with_admin_auth, monkeypatch):
        """Deux appels consécutifs → même structure de réponse.

        compute_events est stateless → pas d'effet de bord cumulatif.
        Le total_events peut différer si l'horloge avance entre les 2
        appels (ex: deadline qui passe), mais structure reste cohérente.
        """
        client, _ = with_admin_auth

        call_count = {"n": 0}

        def _mock(db):
            call_count["n"] += 1
            return {
                "refreshed_orgs": 2,
                "total_events": 8,
                "errors": [],
                "computed_at": "2026-05-02T07:45:00+00:00",
            }

        monkeypatch.setattr("routes.events.refresh_all_active_orgs", _mock)

        r1 = client.post("/api/v1/events/refresh")
        r2 = client.post("/api/v1/events/refresh")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert call_count["n"] == 2  # 2 invocations distinctes
        # Même schéma de réponse
        assert set(r1.json().keys()) == set(r2.json().keys())

    def test_handler_delegates_to_query_service(self):
        """SG comportemental : handler appelle refresh_all_active_orgs.

        Couvre par inspection que la délégation reste pure (cohérent
        SG_EVENTS_02 pour /upcoming).
        """
        import inspect

        from routes.events import refresh_events_endpoint

        body = inspect.getsource(refresh_events_endpoint)
        assert "refresh_all_active_orgs(db)" in body, (
            "Handler doit déléguer à events_query_service.refresh_all_active_orgs"
        )
        # Pas de SQL inline dans le handler
        forbidden = ("db.query(", ".filter(", ".all()", ".first()")
        for token in forbidden:
            assert token not in body, f"Handler refresh contient un appel SQL inline interdit : {token!r}"

    def test_endpoint_in_openapi(self, app_client):
        """OpenAPI doit lister POST /api/v1/events/refresh."""
        client, _ = app_client
        spec = client.get("/openapi.json").json()
        assert "/api/v1/events/refresh" in spec["paths"]
        assert "post" in spec["paths"]["/api/v1/events/refresh"]


class TestRefreshAllActiveOrgs:
    """Tests unitaires de l'orchestrateur (couche query)."""

    def test_returns_dict_with_expected_keys(self, app_client):
        """refresh_all_active_orgs retourne dict avec 4 clés."""
        from services.events_query_service import refresh_all_active_orgs

        _, SessionLocal = app_client
        db = SessionLocal()
        try:
            result = refresh_all_active_orgs(db)
            assert set(result.keys()) == {
                "refreshed_orgs",
                "total_events",
                "errors",
                "computed_at",
            }
        finally:
            db.close()

    def test_no_active_org_returns_zero(self, app_client):
        """DB sans org active → refreshed_orgs=0, total_events=0, errors=[]."""
        from services.events_query_service import refresh_all_active_orgs

        _, SessionLocal = app_client
        db = SessionLocal()
        try:
            # DB SQLite mémoire fraîche, aucune org seedée
            result = refresh_all_active_orgs(db)
            assert result["refreshed_orgs"] == 0
            assert result["total_events"] == 0
            assert result["errors"] == []
        finally:
            db.close()

    def test_org_error_captured_does_not_propagate(self, app_client, monkeypatch):
        """Une org qui fait crash compute_events → erreur captée,
        autres orgs continuent."""
        from models import Organisation
        from services.events_query_service import refresh_all_active_orgs

        _, SessionLocal = app_client
        db = SessionLocal()
        try:
            # Seed 2 orgs actives
            db.add(Organisation(nom="Org OK", actif=True))
            db.add(Organisation(nom="Org Crash", actif=True))
            db.commit()
            crash_org_id = db.query(Organisation).filter(Organisation.nom == "Org Crash").one().id

            def _selective_crash(db_arg, org_id):
                if org_id == crash_org_id:
                    raise RuntimeError("simulated detector failure")
                return []  # autre org : 0 events mais pas d'erreur

            monkeypatch.setattr("services.events_query_service.compute_events", _selective_crash)

            result = refresh_all_active_orgs(db)

            # 1 org OK, 1 org en erreur
            assert result["refreshed_orgs"] == 1
            assert len(result["errors"]) == 1
            assert result["errors"][0]["org_id"] == crash_org_id
            assert "simulated detector failure" in result["errors"][0]["error"]
        finally:
            db.close()
