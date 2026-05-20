"""M2-5.11.C — Tests de GET /api/v4/action-center/summary.

Couverture :
- Auth : 401/403 sans token, 200 VIEWER/USER/ADMIN
- Empty : aucun item → 5 compteurs = 0
- count_p0 / count_p1 : actifs uniquement (exclut closed), bracket strict
- count_without_owner : owner_id NULL + actif
- count_at_risk : item actif + ≥ 1 blocker non-résolu (resolved_at NULL)
  · blocker résolu n'incrémente pas
  · multiples blockers non-résolus ne dédoublonnent pas (1 item = 1 count)
- count_secured : item actif + ≥ 1 evidence verified_at NOT NULL
- Org-scoping : items / blockers / evidences d'une autre org jamais comptés
"""

from datetime import UTC, datetime
from uuid import uuid4

from models.v4.action_blockers import ActionBlocker
from models.v4.action_center_items import ActionCenterItem
from models.v4.evidences import Evidence

URL = "/api/v4/action-center/summary"


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
    owner_id=None,
    closed_at=None,
    closure_reason=None,
):
    item_id = uuid4()
    db = session_local()
    try:
        item = ActionCenterItem(
            id=item_id,
            organisation_id=org_id,
            kind="anomaly",
            title=title,
            priority_bracket=priority_bracket,
            priority_score=priority_score,
            lifecycle_state=lifecycle_state,
            owner_id=owner_id,
        )
        if closed_at:
            item.closed_at = closed_at
            item.closure_reason = closure_reason or "resolved"
        db.add(item)
        db.commit()
    finally:
        db.close()
    return item_id


def _add_blocker(session_local, *, item_id, org_id: int = 1, resolved: bool = False):
    db = session_local()
    try:
        b = ActionBlocker(
            id=uuid4(),
            organisation_id=org_id,
            item_id=item_id,
            blocker_type="waiting_evidence",
        )
        if resolved:
            b.resolved_at = datetime.now(UTC)
        db.add(b)
        db.commit()
    finally:
        db.close()


def _add_evidence(session_local, *, item_id, org_id: int = 1, verified: bool = False):
    """Crée une Evidence minimale (champs requis identiques au conftest V4)."""
    db = session_local()
    try:
        e = Evidence(
            id=uuid4(),
            organisation_id=org_id,
            action_item_id=item_id,
            mime_type="application/pdf",
            file_size_bytes=1024,
            storage_uri="fs://test/summary.pdf",
            original_filename="summary.pdf",
            uploaded_by=uuid4(),
        )
        if verified:
            e.verified_at = datetime.now(UTC)
            e.verified_by = uuid4()
        db.add(e)
        db.commit()
    finally:
        db.close()


class TestSummaryAuth:
    def test_no_token_returns_401_or_403(self, client):
        r = client.get(URL)
        assert r.status_code in (401, 403)

    def test_viewer_can_read(self, client, viewer_token):
        r = client.get(URL, headers=_h(viewer_token))
        assert r.status_code == 200
        body = r.json()
        # Shape canonique : 5 compteurs entiers ≥ 0.
        assert set(body.keys()) == {
            "count_p0",
            "count_p1",
            "count_without_owner",
            "count_at_risk",
            "count_secured",
        }
        for k, v in body.items():
            assert isinstance(v, int) and v >= 0, f"{k}={v}"


class TestSummaryEmpty:
    def test_no_items_returns_all_zeros(self, client, user_token):
        r = client.get(URL, headers=_h(user_token))
        assert r.status_code == 200
        body = r.json()
        assert body == {
            "count_p0": 0,
            "count_p1": 0,
            "count_without_owner": 0,
            "count_at_risk": 0,
            "count_secured": 0,
        }


class TestSummaryPriorityCounts:
    def test_count_p0_active_only(self, app_client, user_token):
        client, session_local = app_client
        # 1 P0 actif → count
        _add_item(session_local, priority_bracket="P0", lifecycle_state="new", title="P0 actif")
        # 1 P0 closed → exclu
        _add_item(
            session_local,
            priority_bracket="P0",
            lifecycle_state="closed",
            title="P0 fermé",
            closed_at=datetime.now(UTC),
        )
        body = client.get(URL, headers=_h(user_token)).json()
        assert body["count_p0"] == 1
        assert body["count_p1"] == 0

    def test_count_p1_separate_from_p0(self, app_client, user_token):
        client, session_local = app_client
        _add_item(session_local, priority_bracket="P0", priority_score=85.0)
        _add_item(session_local, priority_bracket="P1", priority_score=70.0)
        _add_item(session_local, priority_bracket="P1", priority_score=65.0)
        body = client.get(URL, headers=_h(user_token)).json()
        assert body["count_p0"] == 1
        assert body["count_p1"] == 2

    def test_p2_p3_not_counted_in_p0_p1(self, app_client, user_token):
        client, session_local = app_client
        _add_item(session_local, priority_bracket="P2", priority_score=50.0)
        _add_item(session_local, priority_bracket="P3", priority_score=20.0)
        body = client.get(URL, headers=_h(user_token)).json()
        assert body["count_p0"] == 0
        assert body["count_p1"] == 0


class TestSummaryWithoutOwner:
    def test_count_without_owner_active_only(self, app_client, user_token):
        client, session_local = app_client
        _add_item(session_local, owner_id=None, title="orphelin actif")
        _add_item(session_local, owner_id=uuid4(), title="assigné actif")
        _add_item(
            session_local,
            owner_id=None,
            title="orphelin fermé",
            lifecycle_state="closed",
            closed_at=datetime.now(UTC),
        )
        body = client.get(URL, headers=_h(user_token)).json()
        # Seul l'orphelin actif compte.
        assert body["count_without_owner"] == 1


class TestSummaryAtRisk:
    def test_item_with_unresolved_blocker_is_at_risk(self, app_client, user_token):
        client, session_local = app_client
        item_id = _add_item(session_local, title="bloqué")
        _add_blocker(session_local, item_id=item_id, resolved=False)
        body = client.get(URL, headers=_h(user_token)).json()
        assert body["count_at_risk"] == 1

    def test_item_with_only_resolved_blocker_not_at_risk(self, app_client, user_token):
        client, session_local = app_client
        item_id = _add_item(session_local, title="résolu")
        _add_blocker(session_local, item_id=item_id, resolved=True)
        body = client.get(URL, headers=_h(user_token)).json()
        assert body["count_at_risk"] == 0

    def test_multiple_unresolved_blockers_count_item_once(self, app_client, user_token):
        client, session_local = app_client
        item_id = _add_item(session_local)
        _add_blocker(session_local, item_id=item_id, resolved=False)
        _add_blocker(session_local, item_id=item_id, resolved=False)
        _add_blocker(session_local, item_id=item_id, resolved=False)
        body = client.get(URL, headers=_h(user_token)).json()
        # Sous-requête EXISTS → 1 item = 1 count, peu importe le nombre de blockers.
        assert body["count_at_risk"] == 1

    def test_closed_item_with_blocker_not_at_risk(self, app_client, user_token):
        client, session_local = app_client
        item_id = _add_item(session_local, lifecycle_state="closed", closed_at=datetime.now(UTC))
        _add_blocker(session_local, item_id=item_id, resolved=False)
        body = client.get(URL, headers=_h(user_token)).json()
        # Item fermé n'est jamais "at_risk", même si blocker laissé orphelin.
        assert body["count_at_risk"] == 0


class TestSummarySecured:
    def test_item_with_verified_evidence_is_secured(self, app_client, user_token):
        client, session_local = app_client
        item_id = _add_item(session_local, title="prouvé")
        _add_evidence(session_local, item_id=item_id, verified=True)
        body = client.get(URL, headers=_h(user_token)).json()
        assert body["count_secured"] == 1

    def test_item_with_unverified_evidence_not_secured(self, app_client, user_token):
        client, session_local = app_client
        item_id = _add_item(session_local, title="uploadé non vérifié")
        _add_evidence(session_local, item_id=item_id, verified=False)
        body = client.get(URL, headers=_h(user_token)).json()
        assert body["count_secured"] == 0

    def test_closed_item_not_secured(self, app_client, user_token):
        client, session_local = app_client
        item_id = _add_item(session_local, lifecycle_state="closed", closed_at=datetime.now(UTC))
        _add_evidence(session_local, item_id=item_id, verified=True)
        body = client.get(URL, headers=_h(user_token)).json()
        # Item fermé n'est jamais "secured" — la NarrativeBar mesure l'actif.
        assert body["count_secured"] == 0


class TestSummaryOrgScoping:
    def test_cross_org_items_blockers_evidences_never_counted(self, app_client, user_token_org_2):
        """M2-5.11.C — IDOR cross-org sur les 5 compteurs.

        Items + blockers + evidences org 1 → user_token_org_2 voit tout à 0
        (fail-closed via `_apply_scope` IS3 et filtre `organisation_id` sur
        les sous-requêtes EXISTS).
        """
        client, session_local = app_client
        # Org 1 : 1 P0 actif + 1 blocker non-résolu + 1 evidence vérifiée.
        item_id = _add_item(session_local, org_id=1, priority_bracket="P0", title="org-1")
        _add_blocker(session_local, item_id=item_id, org_id=1, resolved=False)
        _add_evidence(session_local, item_id=item_id, org_id=1, verified=True)
        # Org 2 lit son /summary : tout doit être à 0.
        body = client.get(URL, headers=_h(user_token_org_2)).json()
        assert body == {
            "count_p0": 0,
            "count_p1": 0,
            "count_without_owner": 0,
            "count_at_risk": 0,
            "count_secured": 0,
        }
