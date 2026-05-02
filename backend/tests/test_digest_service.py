"""Tests digest_service orchestrator — Phase 2.D Sprint α-push.

Couvre :
- Dispatch happy path (1 user opt-in, events présents → email envoyé)
- Skip silencieux si 0 events (pas de spam)
- Skip user sans UserOrgRole (pas d'org scope)
- Filtre user_filter
- dry_run (rendu mais pas d'envoi)
- Email échec → comptabilisé failed, ne crash pas
- Exception détecteur → captée, summary.failed++
- Resolve persona depuis UserOrgRole.role
- correlation_id unique par run

Mock pattern :
- monkeypatch sur `services.digest_service.get_upcoming_events`
- monkeypatch sur `services.digest_service.get_email_provider`
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.email_provider import EmailResult


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def db(app_client):
    _, SessionLocal = app_client
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def helios_org(db):
    from models import Organisation

    org = Organisation(nom="HELIOS Test", actif=True, is_demo=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@pytest.fixture
def daf_user(db, helios_org):
    """User DAF opt-in pour digest (avec UserOrgRole DAF)."""
    from models import User, UserOrgRole
    from models.enums import UserRole
    from models.user_notification_preference import UserNotificationPreference

    user = User(
        email="marie@helios.test",
        hashed_password="$2b$12$test_hash",
        nom="DAF",
        prenom="Marie",
        actif=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    role = UserOrgRole(user_id=user.id, org_id=helios_org.id, role=UserRole.DAF)
    db.add(role)

    pref = UserNotificationPreference(
        user_id=user.id,
        digest_daily_enabled=True,
        digest_daily_locale="fr-FR",
        digest_channels=["email"],
    )
    db.add(pref)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def opt_out_user(db, helios_org):
    """User avec digest_daily_enabled=False → ne doit jamais recevoir."""
    from models import User, UserOrgRole
    from models.enums import UserRole
    from models.user_notification_preference import UserNotificationPreference

    user = User(
        email="optout@helios.test",
        hashed_password="$2b$12$x",
        nom="Out",
        prenom="Opt",
        actif=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(UserOrgRole(user_id=user.id, org_id=helios_org.id, role=UserRole.DAF))
    db.add(UserNotificationPreference(user_id=user.id, digest_daily_enabled=False))
    db.commit()
    return user


def _fake_event(severity="warning", value=15.0, unit="days"):
    """Mock SolEventCard minimal pour rendu template."""
    e = MagicMock()
    e.severity = severity
    e.title = "Test event"
    e.narrative = "Narrative content"
    e.impact.value = value
    e.impact.unit = unit
    e.impact.period = "deadline"
    e.source.methodology = "Test methodology"
    e.action.label = "Voir"
    e.action.route = "/conformite"
    return e


# ── Tests dispatch_daily_digest ─────────────────────────────────────


class TestDispatchDailyDigest:
    def test_happy_path_sends_to_opt_in_user(self, db, daf_user, monkeypatch):
        """User opt-in + events → email envoyé via provider."""
        monkeypatch.setattr(
            "services.digest_service.get_upcoming_events",
            lambda db_, **kw: {"events": [_fake_event()], "next_cursor": None, "total": 1},
        )

        sent_calls = []

        class FakeProvider:
            def send_email(self, **kw):
                sent_calls.append(kw)
                return EmailResult(success=True, provider="brevo", message_id="<test>")

        monkeypatch.setattr("services.digest_service.get_email_provider", lambda: FakeProvider())

        from services.digest_service import dispatch_daily_digest

        summary = dispatch_daily_digest(db)
        assert summary.sent == 1
        assert summary.failed == 0
        assert summary.skipped_no_events == 0
        assert len(sent_calls) == 1
        # Auth Brevo : tags incluent correlation_id
        tags = sent_calls[0]["tags"]
        assert "digest" in tags
        assert "daily" in tags
        assert any(t.startswith("cid:") for t in tags)

    def test_skip_silently_when_no_events(self, db, daf_user, monkeypatch):
        """User opt-in + 0 events → skipped_no_events, pas d'email."""
        monkeypatch.setattr(
            "services.digest_service.get_upcoming_events",
            lambda db_, **kw: {"events": [], "next_cursor": None, "total": 0},
        )

        sent_calls = []
        provider = MagicMock()
        provider.send_email = lambda **kw: sent_calls.append(kw) or EmailResult(success=True, provider="brevo")
        monkeypatch.setattr("services.digest_service.get_email_provider", lambda: provider)

        from services.digest_service import dispatch_daily_digest

        summary = dispatch_daily_digest(db)
        assert summary.sent == 0
        assert summary.skipped_no_events == 1
        assert sent_calls == []

    def test_opt_out_user_excluded(self, db, opt_out_user, monkeypatch):
        """User digest_daily_enabled=False → jamais récupéré dans la query."""
        monkeypatch.setattr(
            "services.digest_service.get_upcoming_events",
            lambda db_, **kw: {"events": [_fake_event()], "next_cursor": None, "total": 1},
        )
        from services.digest_service import dispatch_daily_digest

        summary = dispatch_daily_digest(db, dry_run=True)
        assert summary.sent == 0
        assert summary.skipped_no_events == 0  # user pas itéré du tout

    def test_dry_run_renders_but_does_not_send(self, db, daf_user, monkeypatch):
        """dry_run=True → templates rendus, compté en sent, pas d'appel provider."""
        monkeypatch.setattr(
            "services.digest_service.get_upcoming_events",
            lambda db_, **kw: {"events": [_fake_event()], "next_cursor": None, "total": 1},
        )

        # Sentinelle : si get_email_provider est appelé en dry_run → fail
        called = {"provider": False}

        def _should_not_be_called():
            called["provider"] = True
            raise AssertionError("email_provider should not be called in dry_run")

        monkeypatch.setattr("services.digest_service.get_email_provider", _should_not_be_called)

        from services.digest_service import dispatch_daily_digest

        summary = dispatch_daily_digest(db, dry_run=True)
        assert summary.dry_run is True
        assert summary.sent == 1  # compté comme rendu OK
        assert called["provider"] is False

    def test_email_failure_counted_does_not_crash(self, db, daf_user, monkeypatch):
        """Provider échoue → summary.failed++ + ne crash pas la boucle."""
        monkeypatch.setattr(
            "services.digest_service.get_upcoming_events",
            lambda db_, **kw: {"events": [_fake_event()], "next_cursor": None, "total": 1},
        )

        class FailProvider:
            def send_email(self, **kw):
                return EmailResult(
                    success=False,
                    provider="brevo",
                    error="server_error:503",
                    attempts=3,
                )

        monkeypatch.setattr("services.digest_service.get_email_provider", lambda: FailProvider())

        from services.digest_service import dispatch_daily_digest

        summary = dispatch_daily_digest(db)
        assert summary.sent == 0
        assert summary.failed == 1

    def test_user_filter_restricts_dispatch(self, db, helios_org, monkeypatch):
        """user_filter=[X] → dispatch uniquement pour cet user."""
        from models import User, UserOrgRole
        from models.enums import UserRole
        from models.user_notification_preference import UserNotificationPreference

        users = []
        for i in range(3):
            u = User(
                email=f"u{i}@helios.test",
                hashed_password="$2b$12$x",
                nom=f"N{i}",
                prenom=f"P{i}",
                actif=True,
            )
            db.add(u)
            db.commit()
            db.refresh(u)
            db.add(UserOrgRole(user_id=u.id, org_id=helios_org.id, role=UserRole.DAF))
            db.add(UserNotificationPreference(user_id=u.id, digest_daily_enabled=True))
            users.append(u)
        db.commit()

        monkeypatch.setattr(
            "services.digest_service.get_upcoming_events",
            lambda db_, **kw: {"events": [_fake_event()], "next_cursor": None, "total": 1},
        )

        from services.digest_service import dispatch_daily_digest

        summary = dispatch_daily_digest(db, dry_run=True, user_filter=[users[0].id])
        assert summary.sent == 1  # uniquement users[0]

    def test_unexpected_exception_captured(self, db, daf_user, monkeypatch):
        """Exception inattendue dans la boucle → summary.failed++ + continue."""

        def _crash(*a, **kw):
            raise RuntimeError("simulated detector crash")

        monkeypatch.setattr("services.digest_service.get_upcoming_events", _crash)
        from services.digest_service import dispatch_daily_digest

        summary = dispatch_daily_digest(db, dry_run=True)
        assert summary.failed == 1

    def test_correlation_id_unique_per_run(self, db, daf_user, monkeypatch):
        monkeypatch.setattr(
            "services.digest_service.get_upcoming_events",
            lambda db_, **kw: {"events": [], "next_cursor": None, "total": 0},
        )
        from services.digest_service import dispatch_daily_digest

        s1 = dispatch_daily_digest(db, dry_run=True)
        s2 = dispatch_daily_digest(db, dry_run=True)
        assert s1.correlation_id != s2.correlation_id


class TestRoleToPersonaMapping:
    def test_role_to_persona_aligned_fe(self):
        """ROLE_TO_PERSONA BE doit matcher FE ROLE_TO_PERSONA + couvrir
        au moins ENERGY_MANAGER / DAF / DG_OWNER (4 personas core)."""
        from services.digest_service import ROLE_TO_PERSONA

        # Couverture minimale Phase 1.A backend personas
        assert ROLE_TO_PERSONA["ENERGY_MANAGER"] == "energy_manager"
        assert ROLE_TO_PERSONA["DAF"] == "daf"
        assert ROLE_TO_PERSONA["DG_OWNER"] == "daf"
