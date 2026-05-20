"""M2-5.10.D — Tests de GET /api/v4/action-center/pilotage/file-prioritaire.

Couverture :
- Auth : 401 sans token, 200 VIEWER/USER/ADMIN
- Filtres cardinaux : seulement P0/P1, exclut closed
- Tri : priority_score DESC, tie-break created_at ASC
- Limit : défaut 5, max 20 (422 si > 20)
- Empty : aucun P0/P1 actif → items=[]
- Org-scoping : items d'une autre org jamais retournés
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from models.v4.action_center_items import ActionCenterItem

URL = "/api/v4/action-center/pilotage/file-prioritaire"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _add_item(
    session_local,
    *,
    org_id: int = 1,
    priority_bracket: str = "P0",
    priority_score: float = 90.0,
    lifecycle_state: str = "new",
    title: str = "T",
    created_at=None,
    closed_at=None,
    closure_reason=None,
):
    db = session_local()
    try:
        item = ActionCenterItem(
            id=uuid4(),
            organisation_id=org_id,
            kind="anomaly",
            title=title,
            priority_bracket=priority_bracket,
            priority_score=priority_score,
            lifecycle_state=lifecycle_state,
        )
        if created_at:
            item.created_at = created_at
        if closed_at:
            item.closed_at = closed_at
            item.closure_reason = closure_reason or "resolved"
        db.add(item)
        db.commit()
    finally:
        db.close()


class TestPilotageAuth:
    def test_no_token_returns_401_or_403(self, client):
        r = client.get(URL)
        assert r.status_code in (401, 403)

    def test_viewer_can_read(self, client, viewer_token):
        r = client.get(URL, headers=_h(viewer_token))
        assert r.status_code == 200

    def test_cross_org_user_never_sees_other_org_items(self, app_client, user_token_org_2):
        """M2-5.11.B — IDOR cross-org sur la file prioritaire.

        Items P0/P1 actifs de l'org 1 → user_token_org_2 voit `items=[]`
        (org-scoping fail-closed via `_apply_scope`, IS3 anti-leak).
        Pas de 403 — la file existe pour l'org 2, juste vide.
        """
        client, session_local = app_client
        _add_item(
            session_local,
            org_id=1,
            priority_bracket="P0",
            priority_score=95.0,
            title="Org-1 vedette",
        )
        r = client.get(URL, headers=_h(user_token_org_2))
        assert r.status_code == 200
        assert r.json()["items"] == []


class TestPilotageFilters:
    def test_excludes_closed_items(self, app_client, user_token):
        client, session_local = app_client
        # P0 actif → inclus
        _add_item(session_local, priority_bracket="P0", priority_score=92.0)
        # P0 closed → exclu
        _add_item(
            session_local,
            priority_bracket="P0",
            priority_score=88.0,
            lifecycle_state="closed",
            closed_at=datetime.now(timezone.utc),
        )

        r = client.get(URL, headers=_h(user_token))
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["priority_score"] == 92.0

    def test_excludes_p2_and_p3(self, app_client, user_token):
        client, session_local = app_client
        _add_item(session_local, priority_bracket="P0", priority_score=85.0)
        _add_item(session_local, priority_bracket="P1", priority_score=75.0)
        _add_item(session_local, priority_bracket="P2", priority_score=55.0)
        _add_item(session_local, priority_bracket="P3", priority_score=25.0)

        r = client.get(URL, headers=_h(user_token))
        items = r.json()["items"]
        # Seuls P0+P1 sont retournés (2 items).
        assert len(items) == 2
        brackets = {it["priority_bracket"] for it in items}
        assert brackets == {"P0", "P1"}

    def test_orders_by_priority_score_desc(self, app_client, user_token):
        client, session_local = app_client
        _add_item(session_local, priority_score=70.0, priority_bracket="P1", title="A")
        _add_item(session_local, priority_score=92.0, priority_bracket="P0", title="B")
        _add_item(session_local, priority_score=85.0, priority_bracket="P0", title="C")

        r = client.get(URL, headers=_h(user_token))
        items = r.json()["items"]
        scores = [it["priority_score"] for it in items]
        assert scores == sorted(scores, reverse=True)
        assert scores == [92.0, 85.0, 70.0]


class TestPilotageLimit:
    def test_default_limit_is_5(self, app_client, user_token):
        client, session_local = app_client
        # 7 items P0/P1 actifs.
        for i in range(7):
            _add_item(session_local, priority_score=80.0 + i, priority_bracket="P0")

        r = client.get(URL, headers=_h(user_token))
        assert r.status_code == 200
        body = r.json()
        assert body["limit"] == 5
        assert len(body["items"]) == 5

    def test_custom_limit_respected(self, app_client, user_token):
        client, session_local = app_client
        for i in range(7):
            _add_item(session_local, priority_score=80.0 + i, priority_bracket="P0")

        r = client.get(URL, headers=_h(user_token), params={"limit": 3})
        assert r.status_code == 200
        assert len(r.json()["items"]) == 3

    def test_limit_over_20_returns_422(self, client, user_token):
        r = client.get(URL, headers=_h(user_token), params={"limit": 50})
        assert r.status_code == 422


class TestPilotageEmpty:
    def test_no_p0_p1_returns_empty(self, app_client, user_token):
        client, session_local = app_client
        _add_item(session_local, priority_bracket="P2", priority_score=55.0)
        r = client.get(URL, headers=_h(user_token))
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_no_items_at_all_returns_empty(self, client, user_token):
        r = client.get(URL, headers=_h(user_token))
        assert r.status_code == 200
        body = r.json()
        assert body["items"] == []
        assert body["limit"] == 5


class TestPilotageTieBreak:
    def test_tie_break_by_created_at_asc(self, app_client, user_token):
        """À score égal, l'item le plus ancien remonte (anti-FIFO inversé)."""
        client, session_local = app_client
        now = datetime.now(timezone.utc)
        _add_item(
            session_local,
            priority_bracket="P0",
            priority_score=90.0,
            title="younger",
            created_at=now,
        )
        _add_item(
            session_local,
            priority_bracket="P0",
            priority_score=90.0,
            title="older",
            created_at=now - timedelta(days=10),
        )

        r = client.get(URL, headers=_h(user_token))
        items = r.json()["items"]
        assert len(items) == 2
        assert items[0]["title"] == "older"
        assert items[1]["title"] == "younger"
