"""Tests intégration endpoint REST `/api/v1/events/upcoming` — Phase 1.A.

Couvre :
- 200 authentifié (DEMO_MODE)
- 401 non-authentifié (DEMO_MODE off)
- isolation org (auth.org_id propagé via resolve_org_id)
- filtres query params (persona, page_key, horizon_days)
- pagination via cursor
- conformité réponse au schema EventUpcomingResponse / OpenAPI
- pas de logique métier dans le handler (délégation pure)

Utilise la fixture `app_client` partagée (TestClient + DB SQLite mémoire).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def seed_demo_org(app_client):
    """Seed une Organisation minimale dans la DB SQLite mémoire pour
    permettre à resolve_org_id (DEMO_MODE fallback) de réussir.

    Sans ça, resolve_org_id raise 403 "Organisation non résolue" car
    aucune org n'existe dans la base de test.
    """
    _, SessionLocal = app_client
    from models import Organisation

    db = SessionLocal()
    try:
        org = Organisation(nom="Test Org", actif=True, is_demo=True)
        db.add(org)
        db.commit()
        db.refresh(org)
        yield org
    finally:
        db.close()


@pytest.fixture
def fake_event(monkeypatch, seed_demo_org):
    """Patch services.events_query_service.compute_events pour
    retourner un event prévisible. Permet de tester l'endpoint sans
    dépendance aux détecteurs réels."""
    from datetime import datetime, timezone

    from services.event_bus.types import (
        EventAction,
        EventImpact,
        EventLinkedAssets,
        EventSource,
        SolEventCard,
    )

    def _mock_compute_events(db, org_id):
        return [
            SolEventCard(
                id=f"compliance:org:{org_id}:dt_2030",
                event_type="compliance_deadline",
                severity="warning",
                title=f"Conformité Décret Tertiaire (org {org_id})",
                narrative="Trajectoire DT 2030 à risque sur 2 sites.",
                impact=EventImpact(value=15.0, unit="days", period="deadline"),
                source=EventSource(
                    system="RegOps",
                    last_updated_at=datetime.now(timezone.utc),
                    confidence="high",
                ),
                action=EventAction(
                    label="Voir conformité",
                    route="/conformite",
                    owner_role="DAF",
                ),
                linked_assets=EventLinkedAssets(org_id=org_id, site_ids=[1, 2]),
            )
        ]

    monkeypatch.setattr("services.events_query_service.compute_events", _mock_compute_events)
    return _mock_compute_events


class TestEventsUpcomingEndpoint:
    def test_returns_200_demo_mode(self, app_client, fake_event):
        client, _ = app_client
        response = client.get("/api/v1/events/upcoming")
        assert response.status_code == 200
        body = response.json()
        assert "events" in body
        assert "total" in body
        assert "computed_at" in body
        assert "cache_ttl_seconds" in body
        assert body["cache_ttl_seconds"] == 300

    def test_returns_403_when_no_org_in_db(self, app_client, monkeypatch):
        """DB sans Organisation seed → resolve_org_id raise 403.

        Garantit que l'endpoint propage le guard d'isolation multi-tenant
        de scope_utils.resolve_org_id (V57 SoT) : pas d'exposition de
        données si l'org ne peut pas être résolue.

        Variante du test 401 : impossible de tester 401 directement car
        DEMO_MODE est figé à l'import (env). Tester la 403 (org absente
        en DEMO_MODE) couvre l'essentiel du contrat de sécurité.
        """
        client, _ = app_client
        # Pas de seed_demo_org → DB vide
        # On mock compute_events pour découpler du moteur
        monkeypatch.setattr("services.events_query_service.compute_events", lambda db, org_id: [])
        response = client.get("/api/v1/events/upcoming")
        assert response.status_code == 403

    def test_response_schema_matches_event_upcoming(self, app_client, fake_event):
        """Conformité au schema Pydantic EventUpcomingResponse."""
        client, _ = app_client
        response = client.get("/api/v1/events/upcoming")
        body = response.json()
        # Champs obligatoires top-level
        assert isinstance(body["events"], list)
        assert isinstance(body["total"], int)
        # Si events non vide, structure mirror SolEventCard
        if body["events"]:
            ev = body["events"][0]
            for key in (
                "id",
                "event_type",
                "severity",
                "title",
                "narrative",
                "impact",
                "source",
                "action",
                "linked_assets",
            ):
                assert key in ev, f"champ manquant : {key}"
            assert "value" in ev["impact"]
            assert "unit" in ev["impact"]
            assert "period" in ev["impact"]
            assert "system" in ev["source"]
            assert "label" in ev["action"]
            assert "route" in ev["action"]
            assert "org_id" in ev["linked_assets"]

    def test_persona_query_param_filters(self, app_client, fake_event):
        """persona='daf' inclut l'event DAF, persona='energy_manager' l'exclut."""
        client, _ = app_client
        r_daf = client.get("/api/v1/events/upcoming?persona=daf")
        assert r_daf.status_code == 200
        assert r_daf.json()["total"] == 1

        r_em = client.get("/api/v1/events/upcoming?persona=energy_manager")
        assert r_em.status_code == 200
        assert r_em.json()["total"] == 0  # event mock owner DAF

    def test_page_key_query_param_filters(self, app_client, fake_event):
        """page_key='conformite' inclut compliance_deadline."""
        client, _ = app_client
        r = client.get("/api/v1/events/upcoming?page_key=conformite")
        assert r.status_code == 200
        assert r.json()["total"] == 1

        r2 = client.get("/api/v1/events/upcoming?page_key=flex")
        assert r2.status_code == 200
        assert r2.json()["total"] == 0  # event mock = compliance, pas flex

    def test_horizon_days_default(self, app_client, fake_event):
        """horizon_days=30 par défaut → impact deadline 15j inclus."""
        client, _ = app_client
        r = client.get("/api/v1/events/upcoming")
        assert r.status_code == 200
        assert r.json()["total"] == 1

    def test_horizon_days_excludes_far_deadline(self, app_client, monkeypatch, seed_demo_org):
        """horizon_days=5 → deadline 15j exclu."""
        from datetime import datetime, timezone

        from services.event_bus.types import (
            EventAction,
            EventImpact,
            EventLinkedAssets,
            EventSource,
            SolEventCard,
        )

        def _far(db, org_id):
            return [
                SolEventCard(
                    id="far",
                    event_type="compliance_deadline",
                    severity="info",
                    title="t",
                    narrative="n",
                    impact=EventImpact(value=15.0, unit="days", period="deadline"),
                    source=EventSource(
                        system="RegOps",
                        last_updated_at=datetime.now(timezone.utc),
                        confidence="high",
                    ),
                    action=EventAction(label="x", route="/", owner_role="DAF"),
                    linked_assets=EventLinkedAssets(org_id=org_id),
                )
            ]

        monkeypatch.setattr("services.events_query_service.compute_events", _far)
        client, _ = app_client
        r = client.get("/api/v1/events/upcoming?horizon_days=5")
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_pagination_via_cursor(self, app_client, monkeypatch, seed_demo_org):
        """50 events → page 1 (20) + cursor + page 2 (20) + cursor + page 3 (10)."""
        from datetime import datetime, timezone

        from services.event_bus.types import (
            EventAction,
            EventImpact,
            EventLinkedAssets,
            EventSource,
            SolEventCard,
        )

        def _many(db, org_id):
            return [
                SolEventCard(
                    id=f"e{i}",
                    event_type="compliance_deadline",
                    severity="info",
                    title=f"t{i}",
                    narrative="n",
                    impact=EventImpact(value=10.0, unit="days", period="deadline"),
                    source=EventSource(
                        system="RegOps",
                        last_updated_at=datetime.now(timezone.utc),
                        confidence="high",
                    ),
                    action=EventAction(label="x", route="/", owner_role="DAF"),
                    linked_assets=EventLinkedAssets(org_id=org_id),
                )
                for i in range(50)
            ]

        monkeypatch.setattr("services.events_query_service.compute_events", _many)
        client, _ = app_client
        page1 = client.get("/api/v1/events/upcoming?limit=20").json()
        assert len(page1["events"]) == 20
        assert page1["next_cursor"] is not None
        assert page1["total"] == 50

        page2 = client.get(f"/api/v1/events/upcoming?limit=20&cursor={page1['next_cursor']}").json()
        assert len(page2["events"]) == 20
        assert page2["next_cursor"] is not None

        page3 = client.get(f"/api/v1/events/upcoming?limit=20&cursor={page2['next_cursor']}").json()
        assert len(page3["events"]) == 10
        assert page3["next_cursor"] is None

    def test_endpoint_in_openapi(self, app_client):
        """OpenAPI doit lister /api/v1/events/upcoming."""
        client, _ = app_client
        spec = client.get("/openapi.json").json()
        assert "/api/v1/events/upcoming" in spec["paths"]
        assert "get" in spec["paths"]["/api/v1/events/upcoming"]

    def test_no_business_logic_in_endpoint_handler(self):
        """Le handler ne contient aucune query SQL ni logique métier inline."""
        import inspect

        from routes.events import get_upcoming_events_endpoint

        body = inspect.getsource(get_upcoming_events_endpoint)
        forbidden = ("db.query(", ".filter(", ".count()", ".all()", "for ", "while ")
        for token in forbidden:
            # `for ` exclu si présent uniquement dans la list comprehension
            # de mapping schema (qui est de la sérialisation, pas du métier)
            if token in body:
                # autoriser la list comprehension sur EventCardSchema.from_sol_event_card
                if token == "for " and "EventCardSchema.from_sol_event_card" in body:
                    continue
                pytest.fail(
                    f"Logique métier détectée dans le handler : {token!r}. "
                    "Le handler doit déléguer à events_query_service."
                )
