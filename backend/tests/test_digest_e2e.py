"""Tests E2E refresh → dispatch — Phase 2.E Sprint α-push (clôture).

Pattern monkeypatch maison (Q5 audit Phase 0.bis arbitré) :
- `FakeBrevoProvider` capture in-memory (zero new dep, pas httpx_mock)
- Patch sur `services.digest_service.get_email_provider` (namespace
  consommateur, pas `services.email_provider` directement — symbole
  re-importé)
- `compute_events` mocké pour découpler du seed DB (events prévisibles)
- `require_platform_admin` overridé pour bypass auth strict en test

8 scenarios couvrent l'intégration complète Phase 2.A→2.D :
  E1 — Happy path : refresh + dispatch envoie email à user opt-in
  E2 — Opt-out : user digest_daily_enabled=False → 0 envoi
  E3 — No events : user opt-in mais 0 events → skipped_no_events
  E4 — Email provider failure : Brevo down → failed, no crash
  E5 — Multi-user même org : 2 users opt-in → 2 emails distincts
  E6 — Dry run : dispatch dry_run=True → templates rendus, 0 envoi
  E7 — Cross-org isolation : user A org A, user B org B → emails distincts
  E8 — Cat A/B real flow : impact € avec methodology → "Source : ..."
       rendu, sans methodology → "à préciser"

Performance cible : < 10s pour 8 scenarios via TestClient SQLite mémoire.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.email_provider import EmailResult


# ── FakeBrevoProvider + fixtures monkeypatch ────────────────────────


@dataclass
class CapturedEmail:
    """In-memory capture d'un email envoyé via FakeBrevoProvider."""

    to: str
    subject: str
    html_body: str
    text_body: Optional[str] = None
    to_name: Optional[str] = None
    tags: tuple = field(default_factory=tuple)


class FakeBrevoProvider:
    """Stub Brevo qui capture sans appeler httpx. Q5 audit Phase 0.bis."""

    name = "fake"

    def __init__(self, captured: list, simulate_failure: bool = False) -> None:
        self.captured = captured
        self.simulate_failure = simulate_failure

    def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        to_name: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> EmailResult:
        if self.simulate_failure:
            return EmailResult(
                success=False,
                provider=self.name,
                error="server_error:503",
                attempts=3,
                tags=tuple(tags or []),
            )
        self.captured.append(
            CapturedEmail(
                to=to,
                to_name=to_name,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                tags=tuple(tags or []),
            )
        )
        return EmailResult(
            success=True,
            provider=self.name,
            message_id=f"fake-{len(self.captured)}",
            latency_ms=1.0,
            attempts=1,
            tags=tuple(tags or []),
        )


@pytest.fixture
def captured_emails(monkeypatch):
    """Patch get_email_provider dans le namespace consommateur (digest_service)."""
    captured: list = []
    fake = FakeBrevoProvider(captured)
    monkeypatch.setattr("services.digest_service.get_email_provider", lambda: fake)
    return captured


@pytest.fixture
def failing_email_provider(monkeypatch):
    """Provider qui retourne success=False (silent fail Brevo down)."""
    captured: list = []
    fake = FakeBrevoProvider(captured, simulate_failure=True)
    monkeypatch.setattr("services.digest_service.get_email_provider", lambda: fake)
    return captured


@pytest.fixture
def admin_auth(app_client):
    """Override require_platform_admin pour endpoints admin (refresh + dispatch)."""
    from main import app
    from middleware.auth import require_platform_admin

    app.dependency_overrides[require_platform_admin] = lambda: {
        "sub": "1",
        "org_id": 1,
        "role": "DG_OWNER",
    }
    yield app_client


# ── Builders fixtures multi-user (LOCAL — pas conftest global) ──────


def _make_org(db, nom="HELIOS Test"):
    """Crée une org et retourne un SimpleNamespace détaché (id, nom).

    Pattern : éviter DetachedInstanceError après db.close() en retournant
    un objet pur Python (pas l'instance SQLAlchemy lazy-load).
    """
    from types import SimpleNamespace

    from models import Organisation

    org = Organisation(nom=nom, actif=True, is_demo=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    return SimpleNamespace(id=org.id, nom=org.nom)


def _make_user(db, email, prenom, nom, role_name, org_id, opt_in=True):
    """Crée user + UserOrgRole + UserNotificationPreference."""
    from models import User, UserOrgRole
    from models.enums import UserRole
    from models.user_notification_preference import UserNotificationPreference

    user = User(
        email=email,
        hashed_password="$2b$12$test_hash",
        nom=nom,
        prenom=prenom,
        actif=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(
        UserOrgRole(
            user_id=user.id,
            org_id=org_id,
            role=UserRole[role_name],
        )
    )
    db.add(
        UserNotificationPreference(
            user_id=user.id,
            digest_daily_enabled=opt_in,
            digest_daily_locale="fr-FR",
            digest_channels=["email"],
        )
    )
    db.commit()
    db.refresh(user)
    return user


def _mock_compute_events(monkeypatch, events_by_org: dict):
    """Patch compute_events pour retourner events prévisibles par org_id.

    `events_by_org` est un dict {org_id: [events]}. Les events sont des
    SolEventCard mocks avec champs minimaux pour rendu template.
    """

    def _fake(db, org_id):
        return events_by_org.get(org_id, [])

    monkeypatch.setattr("services.events_query_service.compute_events", _fake)


def _fake_event(
    severity="warning",
    title="Test Event",
    narrative="Narrative",
    impact_value=5.0,  # ≤ DIGEST_HORIZON_DAYS=7 pour passer le filtre temporel
    impact_unit="days",
    impact_period="deadline",
    methodology=None,
    owner_role="DAF",
):
    """Construit un SolEventCard frozen dataclass pour mocks."""
    from services.event_bus.types import (
        EventAction,
        EventImpact,
        EventLinkedAssets,
        EventSource,
        SolEventCard,
    )

    return SolEventCard(
        id=f"test:{title}",
        event_type="compliance_deadline",
        severity=severity,  # type: ignore[arg-type]
        title=title,
        narrative=narrative,
        impact=EventImpact(
            value=impact_value,
            unit=impact_unit,  # type: ignore[arg-type]
            period=impact_period,  # type: ignore[arg-type]
        ),
        source=EventSource(
            system="RegOps",
            last_updated_at=datetime.now(timezone.utc),
            confidence="high",
            methodology=methodology,
        ),
        action=EventAction(
            label="Voir",
            route="/conformite",
            owner_role=owner_role,
        ),
        linked_assets=EventLinkedAssets(org_id=1),
    )


# ── 8 scenarios E2E ─────────────────────────────────────────────────


class TestDigestE2E:
    # E1 — Happy path
    def test_e1_refresh_then_dispatch_sends_email_to_opted_in_user(self, admin_auth, captured_emails, monkeypatch):
        """Refresh + dispatch → 1 email envoyé au user opt-in."""
        client, SessionLocal = admin_auth
        db = SessionLocal()
        try:
            org = _make_org(db, nom="HELIOS")
            org_id = org.id  # extract scalar before close
            _make_user(db, "marie@helios.io", "Marie", "DAF", "DAF", org_id)
        finally:
            db.close()

        _mock_compute_events(
            monkeypatch,
            {
                org_id: [
                    _fake_event(
                        severity="warning",
                        title="Conformité DT à risque",
                        impact_value=15000.0,
                        impact_unit="€",
                        impact_period="year",
                        methodology="DT_PENALTY_EUR=7500/site × 2 sites",
                    )
                ]
            },
        )

        # Step 1 : refresh
        r1 = client.post("/api/v1/events/refresh")
        assert r1.status_code == 200
        assert r1.json()["refreshed_orgs"] == 1

        # Step 2 : dispatch
        r2 = client.post("/api/v1/digest/dispatch", json={})
        assert r2.status_code == 200
        summary = r2.json()
        assert summary["sent"] == 1
        assert summary["failed"] == 0
        assert summary["skipped_no_events"] == 0

        # Assertions email capturé
        assert len(captured_emails) == 1
        captured = captured_emails[0]
        assert captured.to == "marie@helios.io"
        assert "Marie" in (captured.to_name or "")
        assert "PROMEOS" in captured.subject
        assert "Bonjour Marie" in captured.html_body
        assert "Conformité DT à risque" in captured.html_body
        assert captured.text_body and "PROMEOS" in captured.text_body
        # Tags inclus
        assert "digest" in captured.tags
        assert "daily" in captured.tags

    # E2 — Opt-out
    def test_e2_opt_out_user_receives_no_email(self, admin_auth, captured_emails, monkeypatch):
        """User digest_daily_enabled=False → 0 envoi."""
        client, SessionLocal = admin_auth
        db = SessionLocal()
        try:
            org = _make_org(db)
            _make_user(
                db,
                "optout@test.io",
                "Opt",
                "Out",
                "DAF",
                org.id,
                opt_in=False,  # explicitly disabled
            )
        finally:
            db.close()

        _mock_compute_events(monkeypatch, {org.id: [_fake_event()]})

        r = client.post("/api/v1/digest/dispatch", json={})
        assert r.status_code == 200
        summary = r.json()
        assert summary["sent"] == 0
        assert len(captured_emails) == 0

    # E3 — No events
    def test_e3_user_opt_in_but_no_events_skipped_silently(self, admin_auth, captured_emails, monkeypatch):
        """User opt-in mais 0 events détectés → skipped_no_events, pas d'email."""
        client, SessionLocal = admin_auth
        db = SessionLocal()
        try:
            org = _make_org(db)
            _make_user(db, "noevents@test.io", "No", "Events", "DAF", org.id)
        finally:
            db.close()

        # Aucun event pour cet org
        _mock_compute_events(monkeypatch, {})

        r = client.post("/api/v1/digest/dispatch", json={})
        assert r.status_code == 200
        summary = r.json()
        assert summary["sent"] == 0
        assert summary["skipped_no_events"] == 1
        assert summary["failed"] == 0
        assert len(captured_emails) == 0

    # E4 — Email provider failure
    def test_e4_email_provider_failure_counted_no_crash(self, admin_auth, failing_email_provider, monkeypatch):
        """Brevo down → summary.failed=1, ne crash pas la boucle."""
        client, SessionLocal = admin_auth
        db = SessionLocal()
        try:
            org = _make_org(db)
            _make_user(db, "marie@test.io", "Marie", "DAF", "DAF", org.id)
        finally:
            db.close()

        _mock_compute_events(monkeypatch, {org.id: [_fake_event()]})

        r = client.post("/api/v1/digest/dispatch", json={})
        assert r.status_code == 200
        summary = r.json()
        assert summary["sent"] == 0
        assert summary["failed"] == 1
        # Pas de crash 500, endpoint répond 200 avec compteur d'erreur
        assert len(failing_email_provider) == 0  # FakeBrevoProvider ne capture pas en simulate_failure

    # E5 — Multi-user même org
    def test_e5_multi_user_same_org_each_receives_distinct_email(self, admin_auth, captured_emails, monkeypatch):
        """2 users opt-in dans la même org → 2 emails distincts."""
        client, SessionLocal = admin_auth
        db = SessionLocal()
        try:
            org = _make_org(db)
            _make_user(db, "marie@helios.io", "Marie", "DAF", "DAF", org.id)
            _make_user(
                db,
                "paul@helios.io",
                "Paul",
                "EM",
                "ENERGY_MANAGER",
                org.id,
            )
        finally:
            db.close()

        # 2 events distincts pour matcher les 2 personas (DAF + Energy Manager)
        _mock_compute_events(
            monkeypatch,
            {
                org.id: [
                    _fake_event(title="DAF event", owner_role="DAF"),
                    _fake_event(title="EM event", owner_role="Energy Manager"),
                ]
            },
        )

        r = client.post("/api/v1/digest/dispatch", json={})
        assert r.status_code == 200
        assert r.json()["sent"] == 2
        assert len(captured_emails) == 2

        recipients = {e.to for e in captured_emails}
        assert recipients == {"marie@helios.io", "paul@helios.io"}

        # Personalisation prenom respectée
        marie_email = next(e for e in captured_emails if e.to == "marie@helios.io")
        paul_email = next(e for e in captured_emails if e.to == "paul@helios.io")
        assert "Bonjour Marie" in marie_email.html_body
        assert "Bonjour Paul" in paul_email.html_body

    # E6 — Dry run
    def test_e6_dry_run_renders_templates_no_email_sent(self, admin_auth, captured_emails, monkeypatch):
        """dispatch dry_run=True → templates rendus, 0 capture."""
        client, SessionLocal = admin_auth
        db = SessionLocal()
        try:
            org = _make_org(db)
            _make_user(db, "marie@test.io", "Marie", "DAF", "DAF", org.id)
        finally:
            db.close()

        _mock_compute_events(monkeypatch, {org.id: [_fake_event()]})

        r = client.post("/api/v1/digest/dispatch", json={"dry_run": True})
        assert r.status_code == 200
        summary = r.json()
        assert summary["dry_run"] is True
        assert summary["sent"] == 1  # rendu compté comme sent
        # Mais aucun email réellement capturé (provider non appelé)
        assert len(captured_emails) == 0

    # E7 — Cross-org isolation
    def test_e7_cross_org_isolation_each_user_sees_only_own_org_events(self, admin_auth, captured_emails, monkeypatch):
        """User A org A, user B org B → emails contiennent events de leur
        propre org uniquement."""
        client, SessionLocal = admin_auth
        db = SessionLocal()
        try:
            org_a = _make_org(db, nom="Org A")
            org_b = _make_org(db, nom="Org B")
            _make_user(db, "alice@a.io", "Alice", "A", "DAF", org_a.id)
            _make_user(db, "bob@b.io", "Bob", "B", "DAF", org_b.id)
        finally:
            db.close()

        _mock_compute_events(
            monkeypatch,
            {
                org_a.id: [_fake_event(title="Event spécifique Alice (org A)")],
                org_b.id: [_fake_event(title="Event spécifique Bob (org B)")],
            },
        )

        r = client.post("/api/v1/digest/dispatch", json={})
        assert r.status_code == 200
        assert r.json()["sent"] == 2

        alice_email = next(e for e in captured_emails if e.to == "alice@a.io")
        bob_email = next(e for e in captured_emails if e.to == "bob@b.io")

        # Alice voit son event, pas celui de Bob
        assert "Alice" in alice_email.html_body
        assert "Bob" not in alice_email.html_body
        # Bob voit son event, pas celui d'Alice
        assert "Bob" in bob_email.html_body
        assert "Alice" not in bob_email.html_body

    # E8 — Cat A/B real flow
    def test_e8_cat_a_b_traceability_in_real_html_render(self, admin_auth, captured_emails, monkeypatch):
        """Cat A : impact € + methodology → 'Source :' rendu.
        Cat B : impact € sans methodology → 'à préciser' fallback."""
        client, SessionLocal = admin_auth
        db = SessionLocal()
        try:
            org = _make_org(db)
            _make_user(db, "marie@test.io", "Marie", "DAF", "DAF", org.id)
        finally:
            db.close()

        _mock_compute_events(
            monkeypatch,
            {
                org.id: [
                    _fake_event(
                        title="Cat A event",
                        impact_value=15000.0,
                        impact_unit="€",
                        impact_period="year",
                        methodology="DT_PENALTY_EUR=7500/site × 2 sites (Décret 2019-771)",
                    ),
                    _fake_event(
                        title="Cat B event",
                        impact_value=20000.0,
                        impact_unit="€",
                        impact_period="year",
                        methodology=None,  # pas de provenance
                    ),
                ]
            },
        )

        r = client.post("/api/v1/digest/dispatch", json={})
        assert r.status_code == 200
        assert len(captured_emails) == 1
        html = captured_emails[0].html_body

        # Cat A : event avec methodology → Source rendue
        assert "Cat A event" in html
        assert "Source : DT_PENALTY_EUR=7500" in html or "Source : DT_PENALTY_EUR" in html
        # Format compact FR (espace insécable séparateur milliers — Jinja2 trim_blocks
        # peut affecter mais le 1 5 0 0 0 est dans une seule ligne)
        assert "15 000" in html or "15000" in html

        # Cat B : event sans methodology → fallback
        assert "Cat B event" in html
        assert "à préciser" in html
        # Pas de "20 000" rendu (sans Source, on n'expose pas le chiffre)
        # NOTE : le template fallback ne rend PAS le value, juste "à préciser"
