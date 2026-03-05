"""
PROMEOS — Webhook dispatch + digest service (Playbook 2.4).
Delivers notification events to external webhook subscribers.
"""

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from models import (
    WebhookSubscription,
    DigestPreference,
    NotificationEvent,
    NotificationSeverity,
    NotificationStatus,
)

_logger = logging.getLogger("promeos.webhook")

MAX_FAILURES = 5  # Disable webhook after N consecutive failures
WEBHOOK_TIMEOUT = 10  # seconds


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """HMAC-SHA256 signature for webhook payload."""
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


def _event_to_dict(event: NotificationEvent) -> dict:
    return {
        "id": event.id,
        "org_id": event.org_id,
        "site_id": event.site_id,
        "source_type": event.source_type.value if event.source_type else None,
        "severity": event.severity.value if event.severity else None,
        "title": event.title,
        "message": event.message,
        "estimated_impact_eur": event.estimated_impact_eur,
        "due_date": event.due_date.isoformat() if event.due_date else None,
        "deeplink_path": event.deeplink_path,
        "status": event.status.value if event.status else None,
    }


def dispatch_webhooks(
    db: Session,
    org_id: int,
    events: list[NotificationEvent],
    trigger: str = "sync",
) -> dict:
    """
    POST notification events to all active webhook subscriptions for this org.
    Returns summary: {dispatched, failed, skipped}.
    """
    subs = (
        db.query(WebhookSubscription)
        .filter(
            WebhookSubscription.org_id == org_id,
            WebhookSubscription.active == True,
            WebhookSubscription.failure_count < MAX_FAILURES,
        )
        .all()
    )

    if not subs or not events:
        return {"dispatched": 0, "failed": 0, "skipped": 0}

    events_data = [_event_to_dict(e) for e in events]
    summary = {"dispatched": 0, "failed": 0, "skipped": 0}

    for sub in subs:
        # Filter by events_filter if set
        if sub.events_filter:
            try:
                allowed = json.loads(sub.events_filter)
                events_data_filtered = [
                    e for e in events_data if e["source_type"] in allowed
                ]
            except (json.JSONDecodeError, TypeError):
                events_data_filtered = events_data
        else:
            events_data_filtered = events_data

        if not events_data_filtered:
            summary["skipped"] += 1
            continue

        payload = json.dumps({
            "event": "notifications.sync",
            "trigger": trigger,
            "org_id": org_id,
            "count": len(events_data_filtered),
            "events": events_data_filtered,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }).encode()

        headers = {"Content-Type": "application/json"}
        if sub.secret:
            headers["X-Promeos-Signature"] = _sign_payload(payload, sub.secret)

        try:
            resp = httpx.post(
                sub.url,
                content=payload,
                headers=headers,
                timeout=WEBHOOK_TIMEOUT,
            )
            if resp.status_code < 400:
                sub.failure_count = 0
                sub.last_triggered_at = datetime.now(timezone.utc)
                summary["dispatched"] += 1
                _logger.info("Webhook %d dispatched to %s (status=%d)", sub.id, sub.url, resp.status_code)
            else:
                sub.failure_count += 1
                summary["failed"] += 1
                _logger.warning("Webhook %d failed: %s returned %d", sub.id, sub.url, resp.status_code)
        except Exception as exc:
            sub.failure_count += 1
            summary["failed"] += 1
            _logger.error("Webhook %d error: %s — %s", sub.id, sub.url, exc)

        if sub.failure_count >= MAX_FAILURES:
            sub.active = False
            _logger.warning("Webhook %d disabled after %d failures", sub.id, MAX_FAILURES)

    db.commit()
    return summary


def build_digest(db: Session, org_id: int) -> Optional[dict]:
    """
    Build a digest summary of NEW notifications since last digest.
    Returns None if no new alerts, or a dict with summary + events list.
    """
    pref = db.query(DigestPreference).filter(
        DigestPreference.org_id == org_id,
        DigestPreference.enabled == True,
    ).first()

    if not pref:
        return None

    q = db.query(NotificationEvent).filter(
        NotificationEvent.org_id == org_id,
        NotificationEvent.status == NotificationStatus.NEW,
    )
    if pref.last_sent_at:
        q = q.filter(NotificationEvent.created_at > pref.last_sent_at)

    events = q.order_by(NotificationEvent.created_at.desc()).limit(50).all()

    if not events:
        return None

    critical = sum(1 for e in events if e.severity == NotificationSeverity.CRITICAL)
    warn = sum(1 for e in events if e.severity == NotificationSeverity.WARN)
    info = sum(1 for e in events if e.severity == NotificationSeverity.INFO)

    total_impact = sum(e.estimated_impact_eur or 0 for e in events)

    digest = {
        "org_id": org_id,
        "frequency": pref.frequency,
        "recipient_emails": [e.strip() for e in (pref.recipient_emails or "").split(",") if e.strip()],
        "summary": {
            "total": len(events),
            "critical": critical,
            "warn": warn,
            "info": info,
            "total_impact_eur": round(total_impact, 2),
        },
        "events": [_event_to_dict(e) for e in events[:10]],  # Top 10
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Mark digest as sent
    pref.last_sent_at = datetime.now(timezone.utc)
    db.commit()

    return digest
