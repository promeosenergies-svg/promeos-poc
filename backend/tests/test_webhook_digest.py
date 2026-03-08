"""
Tests — Webhook + Digest service (Playbook 2.4).
"""

import json
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.fast

from models.base import Base
from models import (
    Organisation,
    NotificationEvent,
    NotificationSeverity,
    NotificationStatus,
    NotificationSourceType,
    WebhookSubscription,
    DigestPreference,
)


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organisation(id=1, nom="Test Org", siren="123456789", type_client="tertiaire")
    session.add(org)
    session.flush()

    # Add some notification events
    for i in range(3):
        ev = NotificationEvent(
            org_id=1,
            source_type=NotificationSourceType.BILLING,
            source_id=f"inv_{i}",
            source_key=f"key_{i}",
            severity=NotificationSeverity.CRITICAL if i == 0 else NotificationSeverity.WARN,
            title=f"Alert {i}",
            message=f"Detail {i}",
            estimated_impact_eur=1000.0 * (i + 1),
            status=NotificationStatus.NEW,
        )
        session.add(ev)

    session.commit()
    yield session
    session.close()
    engine.dispose()


class TestWebhookModel:
    def test_create_webhook(self, db):
        sub = WebhookSubscription(
            org_id=1,
            url="https://example.com/hook",
            secret="test_secret",
            active=True,
        )
        db.add(sub)
        db.commit()

        loaded = db.query(WebhookSubscription).filter(WebhookSubscription.org_id == 1).first()
        assert loaded is not None
        assert loaded.url == "https://example.com/hook"
        assert loaded.active is True
        assert loaded.failure_count == 0

    def test_events_filter_json(self, db):
        sub = WebhookSubscription(
            org_id=1,
            url="https://example.com/hook",
            events_filter=json.dumps(["billing", "compliance"]),
        )
        db.add(sub)
        db.commit()

        loaded = db.query(WebhookSubscription).first()
        filters = json.loads(loaded.events_filter)
        assert "billing" in filters
        assert "compliance" in filters


class TestDigestModel:
    def test_create_digest_pref(self, db):
        pref = DigestPreference(
            org_id=1,
            enabled=True,
            frequency="daily",
            recipient_emails="test@example.com,admin@example.com",
        )
        db.add(pref)
        db.commit()

        loaded = db.query(DigestPreference).filter(DigestPreference.org_id == 1).first()
        assert loaded.enabled is True
        assert loaded.frequency == "daily"
        assert "test@example.com" in loaded.recipient_emails


class TestBuildDigest:
    def test_digest_returns_none_when_disabled(self, db):
        from services.webhook_service import build_digest

        result = build_digest(db, org_id=1)
        assert result is None  # No DigestPreference exists

    def test_digest_returns_summary(self, db):
        from services.webhook_service import build_digest

        pref = DigestPreference(org_id=1, enabled=True, frequency="daily")
        db.add(pref)
        db.commit()

        result = build_digest(db, org_id=1)
        assert result is not None
        assert result["summary"]["total"] == 3
        assert result["summary"]["critical"] == 1
        assert result["summary"]["warn"] == 2
        assert result["summary"]["total_impact_eur"] == 6000.0

    def test_digest_marks_last_sent(self, db):
        from services.webhook_service import build_digest

        pref = DigestPreference(org_id=1, enabled=True, frequency="daily")
        db.add(pref)
        db.commit()

        build_digest(db, org_id=1)
        db.refresh(pref)
        assert pref.last_sent_at is not None

    def test_digest_second_call_empty(self, db):
        from services.webhook_service import build_digest

        pref = DigestPreference(org_id=1, enabled=True, frequency="daily")
        db.add(pref)
        db.commit()

        build_digest(db, org_id=1)  # First: returns events
        result = build_digest(db, org_id=1)  # Second: no new events
        assert result is None


class TestDispatchWebhooks:
    def test_no_subs_returns_zero(self, db):
        from services.webhook_service import dispatch_webhooks

        events = db.query(NotificationEvent).all()
        result = dispatch_webhooks(db, org_id=1, events=events)
        assert result["dispatched"] == 0
        assert result["skipped"] == 0

    def test_inactive_sub_skipped(self, db):
        from services.webhook_service import dispatch_webhooks

        sub = WebhookSubscription(
            org_id=1,
            url="https://example.com/hook",
            active=False,
        )
        db.add(sub)
        db.commit()

        events = db.query(NotificationEvent).all()
        result = dispatch_webhooks(db, org_id=1, events=events)
        assert result["dispatched"] == 0

    def test_event_to_dict_structure(self, db):
        from services.webhook_service import _event_to_dict

        event = db.query(NotificationEvent).first()
        d = _event_to_dict(event)
        assert "id" in d
        assert "title" in d
        assert "severity" in d
        assert "source_type" in d
        assert "estimated_impact_eur" in d
