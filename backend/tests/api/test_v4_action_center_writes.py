"""M2-4.4 — Tests des 7 endpoints write/admin du Centre d'Action V4.

PATCH item · PATCH lifecycle · POST evidence · PATCH verify · POST blocker ·
PATCH resolve · POST link. Couvre auth, IDOR parent, règles métier, events
d'audit service-generated, atomicité (modif + event = même transaction).

Fixtures : `client`, `seeded_item` (conftest api), tokens JWT. DB in-memory.
"""

import uuid

import pytest

ITEMS = "/api/v4/action-center/items"

# Magic bytes valides (cf. services/v4/file_validation.py).
_PDF = b"%PDF-1.4\n%%EOF\n"
_JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF test"
_PNG = b"\x89PNG\r\n\x1a\n test"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _evidence_storage(tmp_path, monkeypatch):
    """Isole le stockage des evidences dans un tmp dir (pas de pollution repo)."""
    monkeypatch.setenv("PROMEOS_EVIDENCE_STORAGE_PATH", str(tmp_path / "evidences"))


def _upload_evidence(client, token, item_id, content=_PDF, content_type="application/pdf"):
    """Helper : upload une evidence, retourne la réponse."""
    return client.post(
        f"{ITEMS}/{item_id}/evidences",
        headers=_h(token),
        files={"file": ("evidence.pdf", content, content_type)},
    )


def _add_blocker(client, token, item_id, blocker_type="waiting_evidence"):
    """Helper : crée un blocker, retourne la réponse."""
    return client.post(
        f"{ITEMS}/{item_id}/blockers",
        headers=_h(token),
        json={"blocker_type": blocker_type, "justification": "Motif de blocage test"},
    )


# ════════════════════════════════════════════════════════════════════
# PATCH /items/{id}
# ════════════════════════════════════════════════════════════════════


class TestUpdateItem:
    def test_no_token_401_or_403(self, client, seeded_item):
        r = client.patch(f"{ITEMS}/{seeded_item}", json={"title": "Nouveau titre"})
        assert r.status_code in (401, 403)

    def test_viewer_forbidden_403(self, client, viewer_token, seeded_item):
        r = client.patch(f"{ITEMS}/{seeded_item}", headers=_h(viewer_token), json={"title": "Nouveau titre"})
        assert r.status_code == 403

    def test_user_updates_title_200(self, client, user_token, seeded_item):
        r = client.patch(f"{ITEMS}/{seeded_item}", headers=_h(user_token), json={"title": "Titre mis à jour"})
        assert r.status_code == 200
        assert r.json()["title"] == "Titre mis à jour"

    def test_nonexistent_item_404(self, client, user_token):
        r = client.patch(f"{ITEMS}/{uuid.uuid4()}", headers=_h(user_token), json={"title": "Titre valide"})
        assert r.status_code == 404

    def test_cross_org_404(self, client, user_token_org_2, seeded_item):
        r = client.patch(f"{ITEMS}/{seeded_item}", headers=_h(user_token_org_2), json={"title": "Titre valide"})
        assert r.status_code == 404

    def test_immutable_field_kind_refused_422(self, client, user_token, seeded_item):
        """kind est hors périmètre (IS5) → extra='forbid' → 422."""
        r = client.patch(f"{ITEMS}/{seeded_item}", headers=_h(user_token), json={"kind": "decision"})
        assert r.status_code == 422

    def test_empty_payload_is_idempotent_200(self, client, user_token, seeded_item):
        r = client.patch(f"{ITEMS}/{seeded_item}", headers=_h(user_token), json={})
        assert r.status_code == 200
        assert r.json()["id"] == seeded_item


# ════════════════════════════════════════════════════════════════════
# PATCH /items/{id}/lifecycle
# ════════════════════════════════════════════════════════════════════


class TestLifecycle:
    def test_user_new_to_triaged_200(self, client, user_token, seeded_item):
        r = client.patch(
            f"{ITEMS}/{seeded_item}/lifecycle",
            headers=_h(user_token),
            json={"new_state": "triaged"},
        )
        assert r.status_code == 200
        assert r.json()["lifecycle_state"] == "triaged"

    def test_viewer_forbidden_403(self, client, viewer_token, seeded_item):
        r = client.patch(
            f"{ITEMS}/{seeded_item}/lifecycle",
            headers=_h(viewer_token),
            json={"new_state": "triaged"},
        )
        assert r.status_code == 403

    def test_new_to_closed_with_reason_200(self, client, user_token, seeded_item):
        r = client.patch(
            f"{ITEMS}/{seeded_item}/lifecycle",
            headers=_h(user_token),
            json={"new_state": "closed", "closure_reason": "resolved"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["lifecycle_state"] == "closed"

    def test_illegal_transition_422(self, client, user_token, seeded_item):
        """new → planned (saut) interdit."""
        r = client.patch(
            f"{ITEMS}/{seeded_item}/lifecycle",
            headers=_h(user_token),
            json={"new_state": "planned"},
        )
        assert r.status_code == 422
        assert r.json()["detail"]["code"] == "LIFECYCLE_TRANSITION_FORBIDDEN"

    def test_close_without_reason_422(self, client, user_token, seeded_item):
        r = client.patch(
            f"{ITEMS}/{seeded_item}/lifecycle",
            headers=_h(user_token),
            json={"new_state": "closed"},
        )
        assert r.status_code == 422
        assert r.json()["detail"]["code"] == "CLOSURE_REASON_REQUIRED"

    def test_system_only_closure_reason_422(self, client, user_token, seeded_item):
        """🛡️ merged_duplicate est system-only → refusé sur un PATCH user-driven."""
        r = client.patch(
            f"{ITEMS}/{seeded_item}/lifecycle",
            headers=_h(user_token),
            json={"new_state": "closed", "closure_reason": "merged_duplicate"},
        )
        assert r.status_code == 422
        assert r.json()["detail"]["code"] == "CLOSURE_REASON_SYSTEM_ONLY"

    def test_nonexistent_item_404(self, client, user_token):
        r = client.patch(
            f"{ITEMS}/{uuid.uuid4()}/lifecycle",
            headers=_h(user_token),
            json={"new_state": "triaged"},
        )
        assert r.status_code == 404

    def test_transition_writes_state_changed_event(self, client, user_token, seeded_item):
        """La transition écrit un event `state_changed` lisible via GET /events."""
        client.patch(
            f"{ITEMS}/{seeded_item}/lifecycle",
            headers=_h(user_token),
            json={"new_state": "triaged"},
        )
        events = client.get(f"{ITEMS}/{seeded_item}/events", headers=_h(user_token)).json()["items"]
        assert any(e["event_type"] == "state_changed" for e in events)


# ════════════════════════════════════════════════════════════════════
# POST /items/{id}/evidences
# ════════════════════════════════════════════════════════════════════


class TestUploadEvidence:
    def test_no_token_401_or_403(self, client, seeded_item):
        r = client.post(
            f"{ITEMS}/{seeded_item}/evidences",
            files={"file": ("ev.pdf", _PDF, "application/pdf")},
        )
        assert r.status_code in (401, 403)

    def test_viewer_forbidden_403(self, client, viewer_token, seeded_item):
        r = _upload_evidence(client, viewer_token, seeded_item)
        assert r.status_code == 403

    def test_user_uploads_pdf_201_no_storage_uri(self, client, user_token, seeded_item):
        r = _upload_evidence(client, user_token, seeded_item)
        assert r.status_code == 201
        body = r.json()
        assert body["mime_type"] == "application/pdf"
        assert "storage_uri" not in body  # 🛡️ jamais exposé

    def test_magic_bytes_mismatch_415(self, client, user_token, seeded_item):
        """PDF déclaré mais contenu JPEG → 415 MAGIC_BYTES_MISMATCH."""
        r = _upload_evidence(client, user_token, seeded_item, content=_JPG)
        assert r.status_code == 415
        assert r.json()["detail"]["code"] == "MAGIC_BYTES_MISMATCH"

    def test_unsupported_type_415(self, client, user_token, seeded_item):
        r = _upload_evidence(client, user_token, seeded_item, content=b"PK\x03\x04zip", content_type="application/zip")
        assert r.status_code == 415
        assert r.json()["detail"]["code"] == "UNSUPPORTED_MEDIA_TYPE"

    def test_oversize_413(self, client, user_token, seeded_item):
        big = b"%PDF-" + b"0" * (10 * 1024 * 1024)
        r = _upload_evidence(client, user_token, seeded_item, content=big)
        assert r.status_code == 413

    def test_filename_traversal_400(self, client, user_token, seeded_item):
        r = client.post(
            f"{ITEMS}/{seeded_item}/evidences",
            headers=_h(user_token),
            files={"file": ("../../etc/passwd", _PDF, "application/pdf")},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "INVALID_FILENAME"

    def test_nonexistent_item_404(self, client, user_token):
        r = _upload_evidence(client, user_token, str(uuid.uuid4()))
        assert r.status_code == 404

    def test_upload_writes_evidence_added_event(self, client, user_token, seeded_item):
        _upload_evidence(client, user_token, seeded_item, content=_PNG, content_type="image/png")
        events = client.get(f"{ITEMS}/{seeded_item}/events", headers=_h(user_token)).json()["items"]
        assert any(e["event_type"] == "evidence_added" for e in events)


# ════════════════════════════════════════════════════════════════════
# PATCH /evidences/{id}/verify
# ════════════════════════════════════════════════════════════════════


class TestVerifyEvidence:
    def test_verify_sets_verified_at_200(self, client, user_token, seeded_item):
        evidence_id = _upload_evidence(client, user_token, seeded_item).json()["id"]
        r = client.patch(f"/api/v4/action-center/evidences/{evidence_id}/verify", headers=_h(user_token), json={})
        assert r.status_code == 200
        body = r.json()
        assert body["verified_at"] is not None
        assert body["expires_at"] is not None  # défaut verified_at + 90j

    def test_custom_expires_at_honored(self, client, user_token, seeded_item):
        evidence_id = _upload_evidence(client, user_token, seeded_item).json()["id"]
        custom = "2027-01-01T00:00:00+00:00"
        r = client.patch(
            f"/api/v4/action-center/evidences/{evidence_id}/verify",
            headers=_h(user_token),
            json={"expires_at": custom},
        )
        assert r.status_code == 200
        assert r.json()["expires_at"].startswith("2027-01-01")

    def test_already_verified_409(self, client, user_token, seeded_item):
        evidence_id = _upload_evidence(client, user_token, seeded_item).json()["id"]
        url = f"/api/v4/action-center/evidences/{evidence_id}/verify"
        client.patch(url, headers=_h(user_token), json={})
        r2 = client.patch(url, headers=_h(user_token), json={})
        assert r2.status_code == 409
        detail = r2.json()["detail"]
        assert detail["code"] == "EVIDENCE_ALREADY_VERIFIED"
        # M2-5.9 — le 409 ne fuit aucun timestamp interne (CWE-209).
        assert "hint" not in detail
        assert "verified_at" not in str(detail)

    def test_nonexistent_evidence_404(self, client, user_token):
        r = client.patch(f"/api/v4/action-center/evidences/{uuid.uuid4()}/verify", headers=_h(user_token), json={})
        assert r.status_code == 404

    def test_cross_org_evidence_404(self, client, user_token, user_token_org_2, seeded_item):
        evidence_id = _upload_evidence(client, user_token, seeded_item).json()["id"]
        r = client.patch(
            f"/api/v4/action-center/evidences/{evidence_id}/verify",
            headers=_h(user_token_org_2),
            json={},
        )
        assert r.status_code == 404

    def test_viewer_forbidden_403(self, client, user_token, viewer_token, seeded_item):
        evidence_id = _upload_evidence(client, user_token, seeded_item).json()["id"]
        r = client.patch(f"/api/v4/action-center/evidences/{evidence_id}/verify", headers=_h(viewer_token), json={})
        assert r.status_code == 403

    def test_verify_writes_evidence_verified_event(self, client, user_token, seeded_item):
        evidence_id = _upload_evidence(client, user_token, seeded_item).json()["id"]
        client.patch(f"/api/v4/action-center/evidences/{evidence_id}/verify", headers=_h(user_token), json={})
        events = client.get(f"{ITEMS}/{seeded_item}/events", headers=_h(user_token)).json()["items"]
        assert any(e["event_type"] == "evidence_verified" for e in events)


# ════════════════════════════════════════════════════════════════════
# POST /items/{id}/blockers + PATCH /blockers/{id}/resolve
# ════════════════════════════════════════════════════════════════════


class TestBlockers:
    def test_add_blocker_user_201(self, client, user_token, seeded_item):
        r = _add_blocker(client, user_token, seeded_item)
        assert r.status_code == 201
        assert r.json()["blocker_type"] == "waiting_evidence"

    def test_add_blocker_viewer_403(self, client, viewer_token, seeded_item):
        r = _add_blocker(client, viewer_token, seeded_item)
        assert r.status_code == 403

    def test_add_blocker_invalid_type_422(self, client, user_token, seeded_item):
        r = client.post(
            f"{ITEMS}/{seeded_item}/blockers",
            headers=_h(user_token),
            json={"blocker_type": "waiting_unicorn", "justification": "Motif test"},
        )
        assert r.status_code == 422

    def test_add_blocker_nonexistent_item_404(self, client, user_token):
        r = _add_blocker(client, user_token, str(uuid.uuid4()))
        assert r.status_code == 404

    def test_resolve_blocker_200(self, client, user_token, seeded_item):
        blocker_id = _add_blocker(client, user_token, seeded_item).json()["id"]
        r = client.patch(f"/api/v4/action-center/blockers/{blocker_id}/resolve", headers=_h(user_token), json={})
        assert r.status_code == 200
        assert r.json()["resolved_at"] is not None

    def test_resolve_already_resolved_409(self, client, user_token, seeded_item):
        blocker_id = _add_blocker(client, user_token, seeded_item).json()["id"]
        url = f"/api/v4/action-center/blockers/{blocker_id}/resolve"
        client.patch(url, headers=_h(user_token), json={})
        r2 = client.patch(url, headers=_h(user_token), json={})
        assert r2.status_code == 409
        detail = r2.json()["detail"]
        assert detail["code"] == "BLOCKER_ALREADY_RESOLVED"
        # M2-5.9 — le 409 ne fuit aucun timestamp interne (CWE-209).
        assert "hint" not in detail
        assert "resolved_at" not in str(detail)

    def test_resolve_nonexistent_404(self, client, user_token):
        r = client.patch(f"/api/v4/action-center/blockers/{uuid.uuid4()}/resolve", headers=_h(user_token), json={})
        assert r.status_code == 404

    def test_resolve_cross_org_404(self, client, user_token, user_token_org_2, seeded_item):
        blocker_id = _add_blocker(client, user_token, seeded_item).json()["id"]
        r = client.patch(
            f"/api/v4/action-center/blockers/{blocker_id}/resolve",
            headers=_h(user_token_org_2),
            json={},
        )
        assert r.status_code == 404

    def test_blocker_lifecycle_writes_events(self, client, user_token, seeded_item):
        blocker_id = _add_blocker(client, user_token, seeded_item).json()["id"]
        client.patch(f"/api/v4/action-center/blockers/{blocker_id}/resolve", headers=_h(user_token), json={})
        types = {
            e["event_type"] for e in client.get(f"{ITEMS}/{seeded_item}/events", headers=_h(user_token)).json()["items"]
        }
        assert {"blocker_added", "blocker_removed"} <= types


# ════════════════════════════════════════════════════════════════════
# POST /items/{id}/links
# ════════════════════════════════════════════════════════════════════


class TestLinks:
    def _link_body(self, target_id, target_module="action_center_item"):
        return {
            "target_module": target_module,
            "target_id": str(target_id),
            "link_type": "references",
            "relation": "references",
        }

    def test_link_to_action_center_item_201(self, client, user_token, seeded_item):
        """Cible action_center_item existante (l'item lui-même) → 201."""
        r = client.post(f"{ITEMS}/{seeded_item}/links", headers=_h(user_token), json=self._link_body(seeded_item))
        assert r.status_code == 201
        assert r.json()["target_module"] == "action_center_item"

    def test_link_viewer_403(self, client, viewer_token, seeded_item):
        r = client.post(
            f"{ITEMS}/{seeded_item}/links",
            headers=_h(viewer_token),
            json=self._link_body(seeded_item),
        )
        assert r.status_code == 403

    def test_link_target_not_found_404(self, client, user_token, seeded_item):
        r = client.post(
            f"{ITEMS}/{seeded_item}/links",
            headers=_h(user_token),
            json=self._link_body(uuid.uuid4()),
        )
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "TARGET_NOT_FOUND"

    def test_link_deferred_module_501(self, client, user_token, seeded_item):
        """target_module=site → 501 (module différé M2-5)."""
        r = client.post(
            f"{ITEMS}/{seeded_item}/links",
            headers=_h(user_token),
            json=self._link_body(uuid.uuid4(), target_module="site"),
        )
        assert r.status_code == 501
        assert r.json()["detail"]["code"] == "TARGET_MODULE_NOT_IMPLEMENTED"

    def test_link_invalid_target_module_422(self, client, user_token, seeded_item):
        r = client.post(
            f"{ITEMS}/{seeded_item}/links",
            headers=_h(user_token),
            json=self._link_body(uuid.uuid4(), target_module="galaxy"),
        )
        assert r.status_code == 422

    def test_link_nonexistent_parent_404(self, client, user_token):
        r = client.post(
            f"{ITEMS}/{uuid.uuid4()}/links",
            headers=_h(user_token),
            json=self._link_body(uuid.uuid4()),
        )
        assert r.status_code == 404


# ════════════════════════════════════════════════════════════════════
# Atomicité — modif + event = même transaction
# ════════════════════════════════════════════════════════════════════


def test_event_failure_rolls_back_modification(client, user_token, seeded_item, monkeypatch):
    """🛡️ Si l'écriture de l'audit event échoue, la modif métier est rollback.

    On force ActionEventLogRepository.create à lever → le PATCH /lifecycle
    renvoie 500 → l'item ne doit PAS avoir changé d'état.
    """
    from repositories.action_event_log_repository import ActionEventLogRepository

    def _boom(*args, **kwargs):
        raise RuntimeError("forced audit event failure")

    monkeypatch.setattr(ActionEventLogRepository, "create", _boom)

    r = client.patch(f"{ITEMS}/{seeded_item}/lifecycle", headers=_h(user_token), json={"new_state": "triaged"})
    assert r.status_code == 500

    # L'item doit être resté à 'new' (transition rollback avec l'event échoué).
    monkeypatch.undo()
    item = client.get(f"{ITEMS}/{seeded_item}", headers=_h(user_token)).json()
    assert item["lifecycle_state"] == "new"
