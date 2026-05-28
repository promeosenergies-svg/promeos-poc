"""S2 simplicité (2026-05-28) — Tests endpoint POST /api/v4/action-center/
items/upsert-by-external-ref.

Couvre les 3 scénarios cardinaux de la doctrine S2 + IDOR cross-org :
- Signature inédite → 201 + item créé avec external_ref + source_url persistés.
- Signature connue, item non clos → 200 + même item id (pas de doublon).
- Signature connue, item CLOSED → 409 EXTERNAL_REF_CLOSED (pas de
  résurrection).
- Cross-org → la même external_ref dans une autre org ne collisionne pas
  (indexed UNIQUE PARTIEL `(organisation_id, external_ref)`).

Discipline : `extra=forbid` côté schema → un champ inconnu retourne 422.
`organisation_id` JAMAIS dans le body (forcé par le repo).
"""

import uuid

import pytest

ITEMS = "/api/v4/action-center/items"
UPSERT = f"{ITEMS}/upsert-by-external-ref"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _payload(external_ref: str, title: str = "Décret Tertiaire — site 42") -> dict:
    return {
        "kind": "action",
        "title": title,
        "description": "Échéance OPERAT 30/09/2026. Référence 2020 manquante.",
        "domain": "conformite",
        "external_ref": external_ref,
        "source_url": "/conformite?regulation=dt&site=42",
    }


class TestUpsertByExternalRef:
    # ── Auth / RBAC ───────────────────────────────────────────────────

    def test_no_token_401_or_403(self, client):
        r = client.post(UPSERT, json=_payload("conformite:DT_OPERAT:1"))
        assert r.status_code in (401, 403)

    def test_viewer_forbidden_403(self, client, viewer_token):
        r = client.post(UPSERT, headers=_h(viewer_token), json=_payload("conformite:DT_OPERAT:2"))
        assert r.status_code == 403

    # ── Scénario 1 — signature inédite : CREATE 201 ──────────────────

    def test_create_when_external_ref_unknown(self, client, user_token):
        ext = f"conformite:DT_OPERAT:{uuid.uuid4().hex[:8]}"
        r = client.post(UPSERT, headers=_h(user_token), json=_payload(ext))
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["external_ref"] == ext
        assert body["source_url"] == "/conformite?regulation=dt&site=42"
        assert body["domain"] == "conformite"
        assert body["kind"] == "action"
        assert body["lifecycle_state"] == "new"
        assert body["score_stale"] is True
        # priority_* posée en placeholder server-set, jamais saisie user
        assert body["priority_bracket"] in ("P0", "P1", "P2", "P3")

    # ── Scénario 2 — signature connue, non close : RETURN EXISTING 200 ─

    def test_re_upsert_returns_existing_200_same_id(self, client, user_token):
        ext = f"conformite:BACS_RULE:{uuid.uuid4().hex[:8]}"
        first = client.post(UPSERT, headers=_h(user_token), json=_payload(ext))
        assert first.status_code == 201
        first_id = first.json()["id"]

        second = client.post(UPSERT, headers=_h(user_token), json=_payload(ext))
        assert second.status_code == 200, second.text
        assert second.json()["id"] == first_id

        # Un 3ᵉ re-clic : toujours le même id, jamais de doublon.
        third = client.post(UPSERT, headers=_h(user_token), json=_payload(ext))
        assert third.status_code == 200
        assert third.json()["id"] == first_id

    # ── Scénario 3 — signature connue, item CLOSED : 409 ─────────────

    def test_closed_item_is_not_resurrected_409(self, client, user_token):
        ext = f"conformite:APER_RULE:{uuid.uuid4().hex[:8]}"
        first = client.post(UPSERT, headers=_h(user_token), json=_payload(ext))
        assert first.status_code == 201
        item_id = first.json()["id"]

        # Clôt l'item via le endpoint lifecycle officiel.
        # IL10 : closure_reason requise SSI new_state == closed.
        # On utilise `dismissed` — `resolved` exigerait une preuve vérifiée
        # côté items domain=conformite (CLOSURE_REQUIRES_EVIDENCE), pas
        # pertinent ici puisqu'on teste l'effet de la clôture sur l'upsert.
        close = client.patch(
            f"{ITEMS}/{item_id}/lifecycle",
            headers=_h(user_token),
            json={"new_state": "closed", "closure_reason": "dismissed"},
        )
        assert close.status_code == 200, close.text

        # Re-upsert sur la même signature : la doctrine S2 interdit la résurrection.
        replay = client.post(UPSERT, headers=_h(user_token), json=_payload(ext))
        assert replay.status_code == 409, replay.text
        detail = replay.json()["detail"]
        assert detail["code"] == "EXTERNAL_REF_CLOSED"
        # Hint doit guider vers la stratégie de suffixe `:reopened:<iso-date>`.
        assert "reopened" in detail["hint"]

    # ── IDOR cross-org : même external_ref OK dans une autre org ─────

    def test_same_external_ref_different_org_is_fine(self, client, user_token_org_1, user_token_org_2):
        ext = f"conformite:SHARED_RULE:{uuid.uuid4().hex[:8]}"
        r1 = client.post(UPSERT, headers=_h(user_token_org_1), json=_payload(ext))
        assert r1.status_code == 201
        r2 = client.post(UPSERT, headers=_h(user_token_org_2), json=_payload(ext))
        # Même signature, autre org → CREATE séparé (UNIQUE PARTIEL par org).
        assert r2.status_code == 201
        assert r1.json()["id"] != r2.json()["id"]
        assert r1.json()["organisation_id"] != r2.json()["organisation_id"]

    # ── Validation schema strict ─────────────────────────────────────

    def test_extra_field_rejected_422(self, client, user_token):
        bad = _payload("conformite:X:1")
        bad["organisation_id"] = 999  # jamais accepté en body
        r = client.post(UPSERT, headers=_h(user_token), json=bad)
        assert r.status_code == 422

    def test_missing_external_ref_rejected_422(self, client, user_token):
        bad = _payload("conformite:X:1")
        del bad["external_ref"]
        r = client.post(UPSERT, headers=_h(user_token), json=bad)
        assert r.status_code == 422

    def test_missing_source_url_rejected_422(self, client, user_token):
        bad = _payload("conformite:X:1")
        del bad["source_url"]
        r = client.post(UPSERT, headers=_h(user_token), json=bad)
        assert r.status_code == 422
