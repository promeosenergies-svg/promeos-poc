"""M2-6.A.2 — Tests du service + endpoint purge PII RGPD article 17.

Couverture (15 tests) :

Service `purge_user` (12 tests) :
- Hard-clear User PII (email/nom/prenom/actif=False)
- User.id préservé pour FK historiques
- Hard-delete UserOrgRole (relation)
- Anonymisation snapshots event_log.actor_name + action_center_items.owner_display_name
- Création purge_log + SHA256 hash (CNIL article 30)
- purge_log ne contient pas d'email/nom en clair
- Idempotency 409
- Whitelist .demo → 422
- 404 unknown user
- dry_run no side-effects
- `_hash_user_id` SHA256 hex 64 chars
- `_actor_uuid_for_user_id` déterministe (cohérent route V4 action_center)

Endpoint `POST /api/admin/users/{user_id}/purge` (3 tests) :
- Non-admin (energy_manager) → 403
- reason min_length validation → 422
- Extra field forbidden → 422

Pattern : `app_client` fixture racine (in-memory SQLite, DEMO_MODE=true) +
`admin_token` (role dg_owner = platform admin, passe `require_platform_admin`).
"""

import json
import uuid

import bcrypt
import pytest

from models.iam import User, UserOrgRole
from models.v4.action_center_items import ActionCenterItem
from models.v4.action_event_log import ActionEventLog
from models.v4.purge_log import PurgeLog
from services.v4.pii_purge import (
    ANONYMIZED_NAME,
    PIIPurgeError,
    _actor_uuid_for_user_id,
    _hash_user_id,
    purge_user,
)

PURGE_PATH = "/api/admin/users/{user_id}/purge"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_user(
    session_local,
    *,
    user_id: int = 42,
    email: str = "target@example.com",
    nom: str = "Target",
    prenom: str = "User",
    org_id: int = 1,
    with_role: bool = True,
) -> int:
    """Seed un user + son UserOrgRole. Renvoie user.id."""
    from models.enums import UserRole

    db = session_local()
    try:
        u = User(
            id=user_id,
            email=email,
            hashed_password=bcrypt.hashpw(b"irrelevant", bcrypt.gensalt()).decode(),
            nom=nom,
            prenom=prenom,
            actif=True,
        )
        db.add(u)
        db.flush()
        if with_role:
            db.add(
                UserOrgRole(
                    user_id=u.id,
                    org_id=org_id,
                    role=UserRole.ENERGY_MANAGER,
                )
            )
        db.commit()
        return u.id
    finally:
        db.close()


def _seed_v4_traces(session_local, *, user_id: int, org_id: int = 1) -> dict:
    """Seed 1 ActionCenterItem (owner) + 1 ActionEventLog (actor) liés au user.
    Retourne {'item_id': UUID, 'event_id': UUID}."""
    actor_uuid = _actor_uuid_for_user_id(user_id)
    item_id = uuid.uuid4()
    event_id = uuid.uuid4()
    db = session_local()
    try:
        db.add(
            ActionCenterItem(
                id=item_id,
                organisation_id=org_id,
                kind="anomaly",
                title="Item pour test purge",
                priority_bracket="P2",
                priority_score=50.0,
                lifecycle_state="new",
                owner_id=actor_uuid,
                owner_display_name="Target User",
            )
        )
        db.add(
            ActionEventLog(
                id=event_id,
                organisation_id=org_id,
                action_item_id=item_id,
                event_type="created",
                actor_type="user",
                actor_id=actor_uuid,
                actor_name="Target User",
                actor_role="energy_manager",
                event_payload={"src": "test"},
                correlation_id=uuid.uuid4(),
            )
        )
        db.commit()
        return {"item_id": item_id, "event_id": event_id}
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════
# Tests utilitaires (pas de DB)
# ═══════════════════════════════════════════════════════════════════════


class TestUtilities:
    def test_hash_user_id_returns_sha256_hex_64_chars(self):
        h = _hash_user_id(42)
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_actor_uuid_is_deterministic_and_matches_v4_route_pattern(self):
        """Le UUID5 généré DOIT correspondre EXACTEMENT à `routes/v4/action_center._actor_uuid`.
        Sinon la purge n'anonymisera pas les bons events."""
        u1 = _actor_uuid_for_user_id(42)
        u2 = _actor_uuid_for_user_id(42)
        assert u1 == u2  # déterministe

        # Reproduit le calcul de routes/v4/action_center.py ligne 510-516
        namespace = uuid.uuid5(uuid.NAMESPACE_URL, "promeos:v4:actor")
        expected = uuid.uuid5(namespace, "42")
        assert u1 == expected


# ═══════════════════════════════════════════════════════════════════════
# Tests service purge_user
# ═══════════════════════════════════════════════════════════════════════


class TestPurgeService:
    def test_purge_hard_clears_user_pii_fields(self, app_client):
        _, session_local = app_client
        user_id = _seed_user(session_local)
        db = session_local()
        try:
            purge_user(db, user_id, purged_by_admin_id=1, reason="Demande RGPD art. 17")
            db.expire_all()
            u = db.query(User).filter(User.id == user_id).first()
            assert u.email.startswith("purged_")
            assert u.email.endswith("@purged.local")
            assert u.nom == ANONYMIZED_NAME
            assert u.prenom == ""
            assert u.actif is False
        finally:
            db.close()

    def test_purge_preserves_user_id_for_fk_historiques(self, app_client):
        _, session_local = app_client
        user_id = _seed_user(session_local)
        db = session_local()
        try:
            purge_user(db, user_id, purged_by_admin_id=1, reason="Test FK preservation")
            u = db.query(User).filter(User.id == user_id).first()
            assert u is not None  # l'id reste, juste PII clearée
            assert u.id == user_id
        finally:
            db.close()

    def test_purge_hard_deletes_user_org_roles(self, app_client):
        _, session_local = app_client
        user_id = _seed_user(session_local, with_role=True)
        db = session_local()
        try:
            assert db.query(UserOrgRole).filter_by(user_id=user_id).count() == 1
            report = purge_user(db, user_id, purged_by_admin_id=1, reason="Test del UOR")
            assert report.user_org_roles_deleted == 1
            assert db.query(UserOrgRole).filter_by(user_id=user_id).count() == 0
        finally:
            db.close()

    def test_purge_anonymizes_event_log_actor_name(self, app_client):
        _, session_local = app_client
        user_id = _seed_user(session_local)
        traces = _seed_v4_traces(session_local, user_id=user_id)
        db = session_local()
        try:
            report = purge_user(db, user_id, purged_by_admin_id=1, reason="Test event log")
            assert report.event_logs_anonymized == 1

            db.expire_all()
            evt = db.query(ActionEventLog).filter_by(id=traces["event_id"]).first()
            assert evt.actor_name == ANONYMIZED_NAME
            # actor_id volontairement NON touché (UUID5 opaque) — vérifié explicitement
            assert evt.actor_id == _actor_uuid_for_user_id(user_id)
            # actor_type reste 'user' (CheckConstraint chk_actor_consistency intact)
            assert evt.actor_type == "user"
        finally:
            db.close()

    def test_purge_anonymizes_action_items_owner_display_name(self, app_client):
        _, session_local = app_client
        user_id = _seed_user(session_local)
        traces = _seed_v4_traces(session_local, user_id=user_id)
        db = session_local()
        try:
            report = purge_user(db, user_id, purged_by_admin_id=1, reason="Test items owner")
            assert report.action_items_owner_anonymized == 1

            db.expire_all()
            item = db.query(ActionCenterItem).filter_by(id=traces["item_id"]).first()
            assert item.owner_display_name == ANONYMIZED_NAME
            # owner_id UUID5 opaque, volontairement non touché
            assert item.owner_id == _actor_uuid_for_user_id(user_id)
        finally:
            db.close()

    def test_purge_creates_purge_log_entry_for_cnil_article_30(self, app_client):
        _, session_local = app_client
        user_id = _seed_user(session_local)
        db = session_local()
        try:
            report = purge_user(db, user_id, purged_by_admin_id=7, reason="Demande RGPD reçue 2026-05-22")
            log = db.query(PurgeLog).filter_by(id=report.purge_log_id).first()
            assert log is not None
            assert log.user_id_hash == _hash_user_id(user_id)
            assert log.purged_by_admin_id == 7
            assert log.reason == "Demande RGPD reçue 2026-05-22"
            assert log.dry_run is False
            # report_json contient bien les compteurs
            parsed = json.loads(log.report_json)
            assert parsed["user_pii_cleared"] is True
        finally:
            db.close()

    def test_purge_log_does_not_contain_email_or_user_id_in_clear(self, app_client):
        """Vérif sécurité : ni email ni user_id en clair dans purge_log."""
        _, session_local = app_client
        email = "secret_target@example.com"
        user_id = _seed_user(session_local, email=email)
        db = session_local()
        try:
            report = purge_user(db, user_id, purged_by_admin_id=1, reason="Confidentialité")
            log = db.query(PurgeLog).filter_by(id=report.purge_log_id).first()
            log_str = f"{log.user_id_hash}|{log.reason}|{log.report_json}|{log.purged_by_admin_id}"
            assert email not in log_str
            # user_id en clair ne doit pas figurer dans le hash (qui est SHA256 ≠ str(id))
            assert log.user_id_hash != str(user_id)
        finally:
            db.close()

    def test_purge_idempotent_returns_409_on_second_call(self, app_client):
        _, session_local = app_client
        user_id = _seed_user(session_local)
        db = session_local()
        try:
            purge_user(db, user_id, purged_by_admin_id=1, reason="Première purge")
            with pytest.raises(PIIPurgeError) as exc:
                purge_user(db, user_id, purged_by_admin_id=1, reason="Deuxième purge")
            assert exc.value.code == "USER_ALREADY_PURGED"
            assert exc.value.status_code == 409
        finally:
            db.close()

    def test_purge_demo_user_returns_422_protected(self, app_client):
        _, session_local = app_client
        user_id = _seed_user(session_local, email="marie.dupont@helios.demo")
        db = session_local()
        try:
            with pytest.raises(PIIPurgeError) as exc:
                purge_user(db, user_id, purged_by_admin_id=1, reason="Tentative démo")
            assert exc.value.code == "PROTECTED_DEMO_USER"
            assert exc.value.status_code == 422
            # User intact après tentative
            db.expire_all()
            u = db.query(User).filter_by(id=user_id).first()
            assert u.email == "marie.dupont@helios.demo"
        finally:
            db.close()

    def test_purge_unknown_user_returns_404(self, app_client):
        _, session_local = app_client
        db = session_local()
        try:
            with pytest.raises(PIIPurgeError) as exc:
                purge_user(db, 99999, purged_by_admin_id=1, reason="User inexistant")
            assert exc.value.code == "USER_NOT_FOUND"
            assert exc.value.status_code == 404
        finally:
            db.close()

    def test_purge_dry_run_no_side_effects(self, app_client):
        _, session_local = app_client
        user_id = _seed_user(session_local, email="dry@example.com")
        traces = _seed_v4_traces(session_local, user_id=user_id)
        db = session_local()
        try:
            log_count_before = db.query(PurgeLog).count()
            report = purge_user(db, user_id, purged_by_admin_id=1, reason="Dry run preview", dry_run=True)
            # Le report indique le travail qui SERAIT fait
            assert report.user_pii_cleared is True
            assert report.dry_run is True
            assert report.event_logs_anonymized == 1
            assert report.action_items_owner_anonymized == 1

            # Mais DB inchangée — rollback total
            db.expire_all()
            u = db.query(User).filter_by(id=user_id).first()
            assert u.email == "dry@example.com"
            assert u.nom == "Target"
            assert u.actif is True
            evt = db.query(ActionEventLog).filter_by(id=traces["event_id"]).first()
            assert evt.actor_name == "Target User"
            item = db.query(ActionCenterItem).filter_by(id=traces["item_id"]).first()
            assert item.owner_display_name == "Target User"
            # purge_log entry pas committée non plus (rollback la supprime)
            assert db.query(PurgeLog).count() == log_count_before
        finally:
            db.close()


# ═══════════════════════════════════════════════════════════════════════
# Tests endpoint HTTP
# ═══════════════════════════════════════════════════════════════════════


class TestPurgeEndpoint:
    def test_endpoint_non_admin_returns_403(self, app_client, user_token):
        client, session_local = app_client
        user_id = _seed_user(session_local)
        r = client.post(
            PURGE_PATH.format(user_id=user_id),
            headers=_h(user_token),  # energy_manager → pas platform admin
            json={"reason": "Tentative non-admin avec body valide"},
        )
        assert r.status_code == 403

    def test_endpoint_reason_too_short_returns_422(self, app_client, admin_token):
        client, session_local = app_client
        user_id = _seed_user(session_local)
        r = client.post(
            PURGE_PATH.format(user_id=user_id),
            headers=_h(admin_token),
            json={"reason": "court"},  # < 10 chars
        )
        assert r.status_code == 422

    def test_endpoint_extra_field_forbidden_returns_422(self, app_client, admin_token):
        client, session_local = app_client
        user_id = _seed_user(session_local)
        r = client.post(
            PURGE_PATH.format(user_id=user_id),
            headers=_h(admin_token),
            json={"reason": "Tentative champ inconnu", "rogue_field": "x"},
        )
        assert r.status_code == 422
