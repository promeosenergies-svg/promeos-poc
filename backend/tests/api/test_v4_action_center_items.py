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


# ════════════════════════════════════════════════════════════════════
# M2-5.11.D — impact_at_risk_eur exposé sur ActionCenterItemResponse
# ════════════════════════════════════════════════════════════════════
#
# Le champ est lu via la @property sur le model, qui extrait
# `impact_payload['at_risk']['value_eur']`. Permet à l'UI d'afficher le
# € dans ItemsTable + PriorityQueueCard sans appel /impact unitaire.


class TestImpactAtRiskEurExposed:
    def test_get_by_id_returns_null_when_no_impact_payload(self, client, user_token):
        """Item créé sans payload → impact_at_risk_eur = null."""
        created = client.post(ITEMS, headers=_h(user_token), json=_payload("sans impact")).json()
        body = client.get(f"{ITEMS}/{created['id']}", headers=_h(user_token)).json()
        assert "impact_at_risk_eur" in body
        assert body["impact_at_risk_eur"] is None

    def test_get_by_id_returns_value_when_payload_has_at_risk(
        self, app_client, user_token
    ):
        """Item avec `impact_payload.at_risk.value_eur` → exposé en float."""
        from models.v4.action_center_items import ActionCenterItem
        from uuid import uuid4

        client, session_local = app_client
        item_id = uuid4()
        db = session_local()
        try:
            db.add(
                ActionCenterItem(
                    id=item_id,
                    organisation_id=1,
                    kind="anomaly",
                    title="avec impact",
                    priority_bracket="P0",
                    priority_score=85.0,
                    lifecycle_state="new",
                    impact_payload={"at_risk": {"value_eur": 3400.0, "detail": "12m"}},
                )
            )
            db.commit()
        finally:
            db.close()
        body = client.get(f"{ITEMS}/{item_id}", headers=_h(user_token)).json()
        assert body["impact_at_risk_eur"] == 3400.0

    def test_get_by_id_returns_null_when_at_risk_value_missing(
        self, app_client, user_token
    ):
        """Payload présent mais sans `value_eur` → null (jamais 0 menteur)."""
        from models.v4.action_center_items import ActionCenterItem
        from uuid import uuid4

        client, session_local = app_client
        item_id = uuid4()
        db = session_local()
        try:
            db.add(
                ActionCenterItem(
                    id=item_id,
                    organisation_id=1,
                    kind="anomaly",
                    title="payload partiel",
                    priority_bracket="P2",
                    priority_score=50.0,
                    lifecycle_state="new",
                    impact_payload={"estimated": {"value_eur": 1000}},  # at_risk absent
                )
            )
            db.commit()
        finally:
            db.close()
        body = client.get(f"{ITEMS}/{item_id}", headers=_h(user_token)).json()
        assert body["impact_at_risk_eur"] is None

    def test_list_exposes_impact_at_risk_eur_per_item(self, app_client, user_token):
        """La liste paginée expose le champ sur chaque item — anti N+1."""
        from models.v4.action_center_items import ActionCenterItem
        from uuid import uuid4

        client, session_local = app_client
        db = session_local()
        try:
            db.add(
                ActionCenterItem(
                    id=uuid4(),
                    organisation_id=1,
                    kind="anomaly",
                    title="A — chiffré",
                    priority_bracket="P0",
                    priority_score=90.0,
                    lifecycle_state="new",
                    impact_payload={"at_risk": {"value_eur": 7500}},
                )
            )
            db.add(
                ActionCenterItem(
                    id=uuid4(),
                    organisation_id=1,
                    kind="action",
                    title="B — sans chiffre",
                    priority_bracket="P2",
                    priority_score=45.0,
                    lifecycle_state="new",
                    impact_payload=None,
                )
            )
            db.commit()
        finally:
            db.close()
        body = client.get(ITEMS, headers=_h(user_token)).json()
        values = {it["title"]: it.get("impact_at_risk_eur") for it in body["items"]}
        assert values["A — chiffré"] == 7500.0
        assert values["B — sans chiffre"] is None
