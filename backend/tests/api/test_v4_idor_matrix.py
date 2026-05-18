"""M2-4.5 — Matrice IDOR systémique cross-org (focus no-leak).

Vue TRANSVERSE de l'isolation org : prouve qu'elle est systématique, stable et
non-contournable. Ne duplique PAS les tests cross-org par endpoint déjà présents
dans test_v4_action_center_items/_sub_resources/_writes.py.

5 angles :
  1. Matrice cross-org systématique (test paramétré sur les endpoints {item_id})
  2. IDOR polymorphe profond sur POST /links
  3. No-leak via corps des réponses 404 (cross-org ≡ not-exists)
  4. No-leak via headers (correlation_id opaque)
  5. Isolation de la propagation des events
"""

import uuid

import pytest

BASE = "/api/v4/action-center"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ════════════════════════════════════════════════════════════════════
# ANGLE 1 — Matrice cross-org systématique
# ════════════════════════════════════════════════════════════════════
#
# Bodies VALIDES : seul le parent cross-org doit faire échouer la requête →
# 404 ITEM_NOT_FOUND. Un body invalide brouillerait la preuve (422 parasite).


def _link_body(target_id: str) -> dict:
    return {
        "target_module": "action_center_item",
        "target_id": target_id,
        "link_type": "references",
        "relation": "references",
    }


@pytest.mark.parametrize(
    "method,path_template,body",
    [
        ("GET", "{base}/items/{item_id}", None),
        ("GET", "{base}/items/{item_id}/events", None),
        ("GET", "{base}/items/{item_id}/evidences", None),
        ("GET", "{base}/items/{item_id}/blockers", None),
        ("GET", "{base}/items/{item_id}/links", None),
        ("PATCH", "{base}/items/{item_id}", {"title": "hijack attempt"}),
        ("PATCH", "{base}/items/{item_id}/lifecycle", {"new_state": "triaged"}),
        (
            "POST",
            "{base}/items/{item_id}/blockers",
            {"blocker_type": "waiting_data", "justification": "hijack attempt"},
        ),
        (
            "POST",
            "{base}/items/{item_id}/links",
            {
                "target_module": "action_center_item",
                "target_id": "00000000-0000-0000-0000-000000000000",
                "link_type": "references",
                "relation": "references",
            },
        ),
    ],
)
def test_cross_org_returns_404_systematic(client, user_token_org_2, seeded_item_org_1, method, path_template, body):
    """🛡️ User org 2 → item org 1 : 404 ITEM_NOT_FOUND sur les 9 endpoints {item_id}.

    Le fail-fast parent (`verify_parent_item_access` / `repo.get` org-scopé)
    s'exécute AVANT toute validation métier — aucune fuite d'existence.
    """
    path = path_template.format(base=BASE, item_id=seeded_item_org_1)
    r = client.request(method, path, headers=_h(user_token_org_2), json=body)
    assert r.status_code == 404, f"{method} {path} → {r.status_code} (attendu 404)"
    assert r.json()["detail"]["code"] == "ITEM_NOT_FOUND"


def test_cross_org_evidence_verify_returns_404(client, user_token_org_2, seeded_evidence_org_1):
    """Evidence org 1, user org 2 → 404 (path /evidences/{id}, hors paramétrage)."""
    r = client.patch(
        f"{BASE}/evidences/{seeded_evidence_org_1}/verify",
        headers=_h(user_token_org_2),
        json={"comment": "hijack"},
    )
    assert r.status_code == 404


def test_cross_org_blocker_resolve_returns_404(client, user_token_org_2, seeded_blocker_org_1):
    """Blocker org 1, user org 2 → 404 (path /blockers/{id}, hors paramétrage)."""
    r = client.patch(
        f"{BASE}/blockers/{seeded_blocker_org_1}/resolve",
        headers=_h(user_token_org_2),
        json={"resolution_comment": "hijack"},
    )
    assert r.status_code == 404


# ════════════════════════════════════════════════════════════════════
# ANGLE 2 — IDOR polymorphe profond sur POST /links
# ════════════════════════════════════════════════════════════════════


class TestPolymorphicIDORDeep:
    def test_target_in_other_org_returns_404(self, client, user_token_org_2, seeded_item_org_1, seeded_item_org_2):
        """User org 2 lie son item vers un item org 1 (target cross-org) → 404."""
        r = client.post(
            f"{BASE}/items/{seeded_item_org_2}/links",
            headers=_h(user_token_org_2),
            json=_link_body(seeded_item_org_1),
        )
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "TARGET_NOT_FOUND"

    def test_target_malformed_uuid_returns_422(self, client, user_token_org_1, seeded_item_org_1):
        r = client.post(
            f"{BASE}/items/{seeded_item_org_1}/links",
            headers=_h(user_token_org_1),
            json=_link_body("not-a-uuid"),
        )
        assert r.status_code == 422

    def test_target_random_uuid_returns_404(self, client, user_token_org_1, seeded_item_org_1):
        r = client.post(
            f"{BASE}/items/{seeded_item_org_1}/links",
            headers=_h(user_token_org_1),
            json=_link_body(str(uuid.uuid4())),
        )
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "TARGET_NOT_FOUND"

    def test_target_module_outside_enum_returns_422(self, client, user_token_org_1, seeded_item_org_1):
        body = _link_body(str(uuid.uuid4()))
        body["target_module"] = "evil_module"
        r = client.post(f"{BASE}/items/{seeded_item_org_1}/links", headers=_h(user_token_org_1), json=body)
        assert r.status_code == 422

    def test_parent_cross_org_fails_fast_before_target_verify(
        self, client, user_token_org_2, seeded_item_org_1, seeded_item_org_2
    ):
        """🛡️ Parent cross-org + target valide propre → 404 ITEM_NOT_FOUND.

        Le parent échoue AVANT `verify_link_target` — fail-fast, pas de fuite.
        """
        r = client.post(
            f"{BASE}/items/{seeded_item_org_1}/links",
            headers=_h(user_token_org_2),
            json=_link_body(seeded_item_org_2),
        )
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "ITEM_NOT_FOUND"

    @pytest.mark.parametrize(
        "deferred_module",
        ["site", "building", "meter", "invoice", "contract", "regulatory_obligation"],
    )
    def test_deferred_target_module_returns_501(self, client, user_token_org_1, seeded_item_org_1, deferred_module):
        """Les 6 modules différés → 501 NOT_IMPLEMENTED explicite."""
        body = _link_body(str(uuid.uuid4()))
        body["target_module"] = deferred_module
        r = client.post(f"{BASE}/items/{seeded_item_org_1}/links", headers=_h(user_token_org_1), json=body)
        assert r.status_code == 501
        assert r.json()["detail"]["code"] == "TARGET_MODULE_NOT_IMPLEMENTED"


# ════════════════════════════════════════════════════════════════════
# ANGLE 3 — No-leak via corps des réponses 404
# ════════════════════════════════════════════════════════════════════


class TestNoLeak404Bodies:
    _ORG_LEAK_WORDS = ["another org", "different org", "cross-org", "wrong org", "access denied", "forbidden"]

    def test_cross_org_404_indistinguishable_from_not_exists(self, client, user_token_org_2, seeded_item_org_1):
        """🛡️ 404 cross-org ≡ 404 not-exists : même code, même hint, pas de mot org."""
        r_cross = client.get(f"{BASE}/items/{seeded_item_org_1}", headers=_h(user_token_org_2))
        r_absent = client.get(f"{BASE}/items/{uuid.uuid4()}", headers=_h(user_token_org_2))

        assert r_cross.status_code == r_absent.status_code == 404
        assert r_cross.json()["detail"]["code"] == r_absent.json()["detail"]["code"]
        assert r_cross.json()["detail"]["hint"] == r_absent.json()["detail"]["hint"]

        message = r_cross.json()["detail"]["message"].lower()
        for word in self._ORG_LEAK_WORDS:
            assert word not in message, f"404 message leaks org info: {word!r}"

    def test_target_not_found_indistinguishable_origin(
        self, client, user_token_org_1, seeded_item_org_1, seeded_item_org_2
    ):
        """TARGET_NOT_FOUND : target cross-org ≡ target inexistant (même code)."""
        r_cross = client.post(
            f"{BASE}/items/{seeded_item_org_1}/links",
            headers=_h(user_token_org_1),
            json=_link_body(seeded_item_org_2),
        )
        r_absent = client.post(
            f"{BASE}/items/{seeded_item_org_1}/links",
            headers=_h(user_token_org_1),
            json=_link_body(str(uuid.uuid4())),
        )
        assert r_cross.status_code == r_absent.status_code == 404
        assert r_cross.json()["detail"]["code"] == r_absent.json()["detail"]["code"] == "TARGET_NOT_FOUND"


# ════════════════════════════════════════════════════════════════════
# ANGLE 4 — No-leak via headers / correlation_id
# ════════════════════════════════════════════════════════════════════


def test_correlation_id_does_not_leak_org_info(client, user_token_org_2, seeded_item_org_1):
    """🛡️ Le correlation_id d'une 404 cross-org est opaque (ni org_id ni item_id)."""
    r = client.get(f"{BASE}/items/{seeded_item_org_1}", headers=_h(user_token_org_2))
    assert r.status_code == 404

    correlation = r.headers.get("X-Correlation-ID") or r.json().get("correlation_id")
    if correlation:
        token = str(correlation).lower()
        assert "org" not in token
        assert seeded_item_org_1 not in token


# ════════════════════════════════════════════════════════════════════
# ANGLE 5 — Isolation de la propagation des events
# ════════════════════════════════════════════════════════════════════


class TestEventPropagationIsolation:
    def test_state_changed_event_not_visible_cross_org(
        self, client, user_token_org_1, user_token_org_2, seeded_item_org_1
    ):
        """Org 1 transitionne (event state_changed) ; org 2 ne voit pas les events."""
        assert (
            client.patch(
                f"{BASE}/items/{seeded_item_org_1}/lifecycle",
                headers=_h(user_token_org_1),
                json={"new_state": "triaged"},
            ).status_code
            == 200
        )
        # Org 1 voit bien l'event (sinon bug audit trail M2-4.4).
        org1_events = client.get(f"{BASE}/items/{seeded_item_org_1}/events", headers=_h(user_token_org_1)).json()
        assert org1_events["total"] >= 1
        # Org 2 → 404, aucun event n'est listé.
        r_org2 = client.get(f"{BASE}/items/{seeded_item_org_1}/events", headers=_h(user_token_org_2))
        assert r_org2.status_code == 404
        assert r_org2.json()["detail"]["code"] == "ITEM_NOT_FOUND"

    def test_blocker_added_event_not_visible_cross_org(
        self, client, user_token_org_1, user_token_org_2, seeded_item_org_1
    ):
        """Org 1 ajoute un blocker (event blocker_added) ; org 2 → 404 sur /events."""
        assert (
            client.post(
                f"{BASE}/items/{seeded_item_org_1}/blockers",
                headers=_h(user_token_org_1),
                json={"blocker_type": "waiting_data", "justification": "org 1 blocker"},
            ).status_code
            == 201
        )
        r_org2 = client.get(f"{BASE}/items/{seeded_item_org_1}/events", headers=_h(user_token_org_2))
        assert r_org2.status_code == 404

    def test_link_not_visible_cross_org(self, client, user_token_org_1, user_token_org_2, seeded_item_org_1):
        """Org 1 crée un lien (vers lui-même) ; org 2 → 404 sur /links."""
        assert (
            client.post(
                f"{BASE}/items/{seeded_item_org_1}/links",
                headers=_h(user_token_org_1),
                json=_link_body(seeded_item_org_1),
            ).status_code
            == 201
        )
        r_org2 = client.get(f"{BASE}/items/{seeded_item_org_1}/links", headers=_h(user_token_org_2))
        assert r_org2.status_code == 404
