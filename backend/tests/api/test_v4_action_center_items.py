"""M2-4.2 — Tests endpoint template /api/v4/action-center/items.

Couvre :
- Auth : 401 sans token, 403 viewer→POST, 201 user→POST, 200 viewer→GET
- Pagination : offset/limit, plafond limit enforced
- Isolation org : cross-org → 404 (pas 403, pas de leak)
- Idempotency : rejeu → 200 même item, conflit → 409, clé invalide → 400
- Schema strict : champ inconnu → 422, organisation_id injecté → 422

Fixture `app_client` (conftest root) : TestClient + DB in-memory SQLite isolée,
`get_db` overridé. Tokens JWT : `tests/api/conftest.py`.
"""

import uuid

import pytest


@pytest.fixture
def client(app_client):
    """Déballe le TestClient du tuple (client, SessionLocal) de `app_client`."""
    return app_client[0]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _payload(title: str = "Action seed test", kind: str = "anomaly") -> dict:
    return {"kind": kind, "title": title}


ITEMS = "/api/v4/action-center/items"


# ════════════════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════════════════


class TestAuth:
    def test_post_unauthenticated_401(self, client):
        r = client.post(ITEMS, json=_payload())
        assert r.status_code in (401, 403)

    def test_get_unauthenticated_401(self, client):
        r = client.get(ITEMS)
        assert r.status_code in (401, 403)

    def test_post_viewer_role_403(self, client, viewer_token):
        r = client.post(ITEMS, headers=_h(viewer_token), json=_payload())
        assert r.status_code == 403
        assert r.json()["detail"]["code"] == "ROLE_FORBIDDEN"

    def test_post_user_role_201(self, client, user_token):
        r = client.post(ITEMS, headers=_h(user_token), json=_payload("Test action"))
        assert r.status_code == 201
        body = r.json()
        assert body["title"] == "Test action"
        assert body["kind"] == "anomaly"
        assert body["lifecycle_state"] == "new"

    def test_get_list_viewer_role_200(self, client, viewer_token):
        r = client.get(ITEMS, headers=_h(viewer_token))
        assert r.status_code == 200


# ════════════════════════════════════════════════════════════════════
# CRÉATION — defaults serveur
# ════════════════════════════════════════════════════════════════════


class TestCreateDefaults:
    def test_post_sets_placeholder_priority_and_stale(self, client, user_token):
        """priority dérivée (M2-5) → placeholder P2/50 + score_stale=True à la création."""
        r = client.post(ITEMS, headers=_h(user_token), json=_payload("Item priorité"))
        body = r.json()
        assert body["priority_bracket"] == "P2"
        assert body["priority_score"] == 50.0
        assert body["score_stale"] is True

    def test_get_by_id_same_org_200(self, client, user_token):
        created = client.post(ITEMS, headers=_h(user_token), json=_payload("À relire")).json()
        r = client.get(f"{ITEMS}/{created['id']}", headers=_h(user_token))
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]


# ════════════════════════════════════════════════════════════════════
# PAGINATION
# ════════════════════════════════════════════════════════════════════


class TestPagination:
    def test_default_pagination(self, client, viewer_token):
        body = client.get(ITEMS, headers=_h(viewer_token)).json()
        assert body["offset"] == 0
        assert body["limit"] == 50

    def test_custom_pagination(self, client, viewer_token):
        body = client.get(f"{ITEMS}?offset=10&limit=5", headers=_h(viewer_token)).json()
        assert body["offset"] == 10
        assert body["limit"] == 5
        assert len(body["items"]) <= 5

    def test_limit_max_enforced(self, client, viewer_token):
        r = client.get(f"{ITEMS}?limit=999", headers=_h(viewer_token))
        assert r.status_code == 422


# ════════════════════════════════════════════════════════════════════
# ISOLATION ORG
# ════════════════════════════════════════════════════════════════════


class TestOrgIsolation:
    def test_cross_org_get_returns_404(self, client, user_token_org_1, user_token_org_2):
        """🛡️ GET cross-org → 404 (pas 403 — pas de fuite d'existence)."""
        created = client.post(ITEMS, headers=_h(user_token_org_1), json=_payload("Org1 item")).json()
        r = client.get(f"{ITEMS}/{created['id']}", headers=_h(user_token_org_2))
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "ITEM_NOT_FOUND"

    def test_list_does_not_leak_cross_org(self, client, user_token_org_1, user_token_org_2):
        """🛡️ La liste d'une org ne contient jamais les items d'une autre."""
        client.post(ITEMS, headers=_h(user_token_org_1), json=_payload("Org1 secret"))
        body = client.get(ITEMS, headers=_h(user_token_org_2)).json()
        assert "Org1 secret" not in [i["title"] for i in body["items"]]


# ════════════════════════════════════════════════════════════════════
# IDEMPOTENCY
# ════════════════════════════════════════════════════════════════════


class TestIdempotency:
    def test_replay_same_payload_returns_same_item(self, client, user_token):
        key = str(uuid.uuid4())
        headers = {**_h(user_token), "Idempotency-Key": key}
        payload = _payload("Idempotent action")
        r1 = client.post(ITEMS, headers=headers, json=payload)
        r2 = client.post(ITEMS, headers=headers, json=payload)
        assert r1.status_code == 201
        assert r2.status_code == 200  # rejeu → 200, pas 201
        assert r1.json()["id"] == r2.json()["id"]

    def test_replay_different_payload_returns_409(self, client, user_token):
        key = str(uuid.uuid4())
        headers = {**_h(user_token), "Idempotency-Key": key}
        r1 = client.post(ITEMS, headers=headers, json=_payload("Original"))
        assert r1.status_code == 201
        r2 = client.post(ITEMS, headers=headers, json=_payload("Different"))
        assert r2.status_code == 409
        assert r2.json()["detail"]["code"] == "IDEMPOTENCY_CONFLICT"

    def test_invalid_idempotency_key_format_400(self, client, user_token):
        r = client.post(
            ITEMS,
            headers={**_h(user_token), "Idempotency-Key": "not-a-uuid"},
            json=_payload(),
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "IDEMPOTENCY_KEY_INVALID"

    def test_no_key_means_no_idempotency(self, client, user_token):
        """Sans Idempotency-Key, 2 POST identiques créent 2 items distincts."""
        r1 = client.post(ITEMS, headers=_h(user_token), json=_payload("Sans clé"))
        r2 = client.post(ITEMS, headers=_h(user_token), json=_payload("Sans clé"))
        assert r1.status_code == r2.status_code == 201
        assert r1.json()["id"] != r2.json()["id"]


# ════════════════════════════════════════════════════════════════════
# SCHEMA STRICT
# ════════════════════════════════════════════════════════════════════


class TestSchemaStrict:
    def test_extra_fields_refused(self, client, user_token):
        r = client.post(
            ITEMS,
            headers=_h(user_token),
            json={"kind": "anomaly", "title": "Titre valide", "evil_field": "bypass"},
        )
        assert r.status_code == 422

    def test_organisation_id_in_body_refused(self, client, user_token):
        """organisation_id dans le body → 422 (extra='forbid'). Le repo le force de toute façon."""
        r = client.post(
            ITEMS,
            headers=_h(user_token),
            json={"kind": "anomaly", "title": "Titre valide", "organisation_id": 999},
        )
        assert r.status_code == 422

    def test_missing_kind_refused(self, client, user_token):
        """kind est requis (discriminant single-table) → 422 si absent."""
        r = client.post(ITEMS, headers=_h(user_token), json={"title": "Sans kind"})
        assert r.status_code == 422
