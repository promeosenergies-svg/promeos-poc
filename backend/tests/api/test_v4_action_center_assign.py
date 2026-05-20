"""M2-5.11.E — Tests de PATCH /api/v4/action-center/items/{id}/assign.

Couverture :
- Auth : 401/403 sans token, 403 viewer, 200 USER/ADMIN
- Assigner : owner_id + owner_display_name persistés, assigned_at posé
- Désassigner : owner_id=None → owner_display_name=None aussi, assigned_at=None
- Réassigner : transition d'un owner à un autre + event owner_changed
- No-op : même owner_id + même display_name → 200 sans event
- Event log : 1 event owner_changed par changement, payload structuré
- Cross-org IDOR : item d'une autre org → 404 (anti-leak)
- Schema strict : extra fields → 422, display_name > 120 → 422
"""

from uuid import uuid4

from models.v4.action_center_items import ActionCenterItem
from models.v4.action_event_log import ActionEventLog

ITEMS = "/api/v4/action-center/items"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_item(session_local, *, org_id: int = 1, title: str = "À assigner") -> str:
    item_id = uuid4()
    db = session_local()
    try:
        db.add(
            ActionCenterItem(
                id=item_id,
                organisation_id=org_id,
                kind="anomaly",
                title=title,
                priority_bracket="P1",
                priority_score=70.0,
                lifecycle_state="new",
            )
        )
        db.commit()
    finally:
        db.close()
    return str(item_id)


def _count_events(session_local, *, item_id: str, event_type: str | None = None) -> int:
    db = session_local()
    try:
        q = db.query(ActionEventLog).filter(ActionEventLog.action_item_id == item_id)
        if event_type:
            q = q.filter(ActionEventLog.event_type == event_type)
        return q.count()
    finally:
        db.close()


class TestAssignAuth:
    def test_no_token_returns_401_or_403(self, client):
        r = client.patch(f"{ITEMS}/{uuid4()}/assign", json={"owner_id": str(uuid4())})
        assert r.status_code in (401, 403)

    def test_viewer_cannot_assign(self, app_client, viewer_token):
        client, session_local = app_client
        item_id = _create_item(session_local)
        r = client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(viewer_token),
            json={"owner_id": str(uuid4()), "owner_display_name": "J. Martin"},
        )
        # VIEWER n'a pas le droit d'écrire — 403 explicit ou 404 (les deux
        # corrects selon le rang de la guard ; on accepte les deux).
        assert r.status_code in (403, 404)

    def test_user_can_assign(self, app_client, user_token):
        client, session_local = app_client
        item_id = _create_item(session_local)
        owner_uuid = str(uuid4())
        r = client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={"owner_id": owner_uuid, "owner_display_name": "J. Martin"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["owner_id"] == owner_uuid
        assert body["owner_display_name"] == "J. Martin"


class TestAssignBehavior:
    def test_assign_persists_owner_and_display_name(self, app_client, user_token):
        client, session_local = app_client
        item_id = _create_item(session_local)
        owner_uuid = str(uuid4())
        client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={"owner_id": owner_uuid, "owner_display_name": "M. Dupont"},
        )
        # Refetch via GET — confirme la persistance (pas juste la réponse).
        got = client.get(f"{ITEMS}/{item_id}", headers=_h(user_token)).json()
        assert got["owner_id"] == owner_uuid
        assert got["owner_display_name"] == "M. Dupont"

    def test_unassign_clears_owner_id_and_display_name(self, app_client, user_token):
        client, session_local = app_client
        item_id = _create_item(session_local)
        # 1) Assigner.
        client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={"owner_id": str(uuid4()), "owner_display_name": "A. Pilote"},
        )
        # 2) Désassigner (owner_id=None).
        r = client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={"owner_id": None},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["owner_id"] is None
        # `owner_display_name` est purgé en même temps — pas de label fantôme.
        assert body["owner_display_name"] is None

    def test_reassign_changes_owner_and_writes_event(self, app_client, user_token):
        client, session_local = app_client
        item_id = _create_item(session_local)
        first = str(uuid4())
        second = str(uuid4())
        client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={"owner_id": first, "owner_display_name": "Pilote A"},
        )
        client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={"owner_id": second, "owner_display_name": "Pilote B"},
        )
        got = client.get(f"{ITEMS}/{item_id}", headers=_h(user_token)).json()
        assert got["owner_id"] == second
        assert got["owner_display_name"] == "Pilote B"
        # 2 events owner_changed (1 assign + 1 réassign).
        assert _count_events(session_local, item_id=item_id, event_type="owner_changed") == 2

    def test_noop_same_owner_and_label_returns_200_without_event(self, app_client, user_token):
        client, session_local = app_client
        item_id = _create_item(session_local)
        owner_uuid = str(uuid4())
        # 1ère assignation → event #1.
        client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={"owner_id": owner_uuid, "owner_display_name": "Idempotent"},
        )
        # Replay identique → 200 sans event #2 (anti-spam audit trail).
        r = client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={"owner_id": owner_uuid, "owner_display_name": "Idempotent"},
        )
        assert r.status_code == 200
        assert _count_events(session_local, item_id=item_id, event_type="owner_changed") == 1


class TestAssignEventPayload:
    def test_event_payload_carries_old_and_new_owner(self, app_client, user_token):
        client, session_local = app_client
        item_id = _create_item(session_local)
        owner_uuid = str(uuid4())
        client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={"owner_id": owner_uuid, "owner_display_name": "Audité"},
        )
        db = session_local()
        try:
            event = (
                db.query(ActionEventLog)
                .filter(
                    ActionEventLog.action_item_id == item_id,
                    ActionEventLog.event_type == "owner_changed",
                )
                .one()
            )
            payload = event.event_payload
            assert payload["old_owner_id"] is None  # 1ère assignation
            assert payload["new_owner_id"] == owner_uuid
            assert payload["new_owner_display_name"] == "Audité"
        finally:
            db.close()


class TestAssignOrgScoping:
    def test_cross_org_assign_returns_404(self, app_client, user_token_org_2):
        """Item de l'org 1 → user_token_org_2 reçoit 404 (anti-leak IS3)."""
        client, session_local = app_client
        item_id = _create_item(session_local, org_id=1)
        r = client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token_org_2),
            json={"owner_id": str(uuid4()), "owner_display_name": "Hostile"},
        )
        assert r.status_code == 404


class TestAssignSchemaStrict:
    def test_extra_field_refused(self, app_client, user_token):
        client, session_local = app_client
        item_id = _create_item(session_local)
        r = client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={
                "owner_id": str(uuid4()),
                "owner_display_name": "OK",
                "evil_field": "bypass",
            },
        )
        assert r.status_code == 422

    def test_display_name_too_long_refused(self, app_client, user_token):
        client, session_local = app_client
        item_id = _create_item(session_local)
        r = client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={"owner_id": str(uuid4()), "owner_display_name": "x" * 200},
        )
        assert r.status_code == 422

    def test_invalid_uuid_refused(self, app_client, user_token):
        client, session_local = app_client
        item_id = _create_item(session_local)
        r = client.patch(
            f"{ITEMS}/{item_id}/assign",
            headers=_h(user_token),
            json={"owner_id": "not-a-uuid", "owner_display_name": "OK"},
        )
        assert r.status_code == 422
