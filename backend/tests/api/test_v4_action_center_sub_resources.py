"""M2-4.3 — Tests des endpoints lecture sous-ressources /items/{item_id}/*.

4 sous-ressources : events · evidences · blockers · links.

Couverture par sous-ressource :
- Auth : 401/403 sans token, 200 VIEWER/USER/ADMIN
- Parent IDOR : item inexistant → 404, item cross-org → 404
- Résultat vide : item sans sous-ressource → items=[] total=0
- Pagination : plafond limit (>200 → 422)
- Tri : DESC sur la colonne datetime métier
- Sécurité (evidences) : storage_uri / validation_payload jamais exposés

Fixtures : `client`, `seeded_item`, `seeded_item_with_subs` (conftest api),
tokens JWT (conftest api). DB in-memory SQLite isolée (`app_client`).
"""

import uuid

import pytest

ITEMS = "/api/v4/action-center/items"
SUBS = ["events", "evidences", "blockers", "links"]

# Colonne datetime de tri exposée dans la réponse, par sous-ressource.
SORT_FIELD = {
    "events": "occurred_at",
    "evidences": "uploaded_at",
    "blockers": "added_at",
    "links": "created_at",
}
# Nombre d'éléments seedés par `seeded_item_with_subs`, par sous-ressource.
SEEDED_COUNT = {"events": 3, "evidences": 3, "blockers": 2, "links": 2}


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ════════════════════════════════════════════════════════════════════
# Tests communs aux 4 sous-ressources (paramétrés)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("sub", SUBS)
class TestSubResourceCommon:
    def test_no_token_returns_401_or_403(self, client, seeded_item, sub):
        r = client.get(f"{ITEMS}/{seeded_item}/{sub}")
        assert r.status_code in (401, 403)

    def test_viewer_can_list(self, client, viewer_token, seeded_item, sub):
        r = client.get(f"{ITEMS}/{seeded_item}/{sub}", headers=_h(viewer_token))
        assert r.status_code == 200
        body = r.json()
        assert "items" in body and "total" in body

    def test_nonexistent_item_returns_404(self, client, user_token, sub):
        r = client.get(f"{ITEMS}/{uuid.uuid4()}/{sub}", headers=_h(user_token))
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "ITEM_NOT_FOUND"

    def test_cross_org_item_returns_404(self, client, user_token_org_2, seeded_item, sub):
        """🛡️ seeded_item est org 1 ; un token org 2 → 404 (pas de leak d'existence)."""
        r = client.get(f"{ITEMS}/{seeded_item}/{sub}", headers=_h(user_token_org_2))
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "ITEM_NOT_FOUND"

    def test_empty_result_shape(self, client, user_token, seeded_item, sub):
        body = client.get(f"{ITEMS}/{seeded_item}/{sub}", headers=_h(user_token)).json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["offset"] == 0
        assert body["limit"] == 50

    def test_limit_max_enforced(self, client, user_token, seeded_item, sub):
        r = client.get(f"{ITEMS}/{seeded_item}/{sub}?limit=999", headers=_h(user_token))
        assert r.status_code == 422


# ════════════════════════════════════════════════════════════════════
# Tri DESC + comptage (sous-ressource seedée)
# ════════════════════════════════════════════════════════════════════


@pytest.mark.parametrize("sub", SUBS)
def test_sort_desc_and_count(client, user_token, seeded_item_with_subs, sub):
    """Liste triée DESC sur la colonne datetime métier + comptage attendu."""
    body = client.get(f"{ITEMS}/{seeded_item_with_subs}/{sub}", headers=_h(user_token)).json()
    items = body["items"]
    assert len(items) == SEEDED_COUNT[sub]
    assert body["total"] == SEEDED_COUNT[sub]
    timestamps = [i[SORT_FIELD[sub]] for i in items]
    assert timestamps == sorted(timestamps, reverse=True)


# ════════════════════════════════════════════════════════════════════
# Sécurité — evidences : storage_uri jamais exposé
# ════════════════════════════════════════════════════════════════════


def test_evidences_never_expose_storage_uri(client, user_token, seeded_item_with_subs):
    """🛡️ storage_uri / validation_payload absents du payload evidences (anti-leak)."""
    body = client.get(f"{ITEMS}/{seeded_item_with_subs}/evidences", headers=_h(user_token)).json()
    assert len(body["items"]) == 3
    for evidence in body["items"]:
        assert "storage_uri" not in evidence
        assert "validation_payload" not in evidence
        # download_endpoint omis tant que l'endpoint n'existe pas (M2-4.4+)
        assert "download_endpoint" not in evidence


# ════════════════════════════════════════════════════════════════════
# Pagination — offset/limit effectifs
# ════════════════════════════════════════════════════════════════════


def test_pagination_offset_limit_applied(client, user_token, seeded_item_with_subs):
    """events seedés=3 ; limit=2 → 2 items ; offset=2 → 1 item ; total=3 constant."""
    page1 = client.get(f"{ITEMS}/{seeded_item_with_subs}/events?offset=0&limit=2", headers=_h(user_token)).json()
    page2 = client.get(f"{ITEMS}/{seeded_item_with_subs}/events?offset=2&limit=2", headers=_h(user_token)).json()
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 1
    assert page1["total"] == page2["total"] == 3
