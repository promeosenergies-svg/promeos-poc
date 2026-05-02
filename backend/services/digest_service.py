"""Digest service — orchestrateur dispatch matinal Sprint α-push Phase 2.D.

Combine les 3 briques précédentes :
- Phase 1.A `events_query_service.get_upcoming_events` (filtre persona + horizon)
- Phase 2.B `email_provider` Brevo httpx (silent fail + retry)
- Phase 2.C `user_notification_preferences` (opt-in)

Flow par user opted-in :
1. Résoudre persona depuis `UserOrgRole.role` (premier rôle org)
2. Get upcoming events (horizon=7 jours, limit=10)
3. Skip silencieux si 0 events (ne spam pas les boites)
4. Render template Jinja2 (HTML + text fallback)
5. Send via email_provider (silent fail — log + continue)

Anti-leak PII strict :
- Logs : tags + status + classe d'erreur, **JAMAIS** email/prenom/nom
- Templates : pas d'identifiants techniques (event.id, source.system,
  internal counters)

Cat A/B traçabilité : impact € avec source.methodology visible OU
fallback "à préciser" dans le template (cf. digest_daily.html.j2).

Idempotence : NON garantie MVP. 1 appel = 1 envoi. Re-jouer dispatch
re-envoie. Phase 3+ : table `digest_dispatches(user_id, date)` pour
dedup.

Réf : docs/audits/sprint_alpha_push_phase0_audit_20260502.md (§plan 2.D),
docs/adr/ADR-006-coexistence-notification-service-event-bus.md.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from models.iam import User, UserOrgRole
from models.user_notification_preference import UserNotificationPreference
from services.email_provider import EmailResult, get_email_provider
from services.events_query_service import get_upcoming_events

logger = logging.getLogger(__name__)


# ── Configuration ──────────────────────────────────────────────────


DIGEST_HORIZON_DAYS = 7
DIGEST_EVENTS_LIMIT = 10
DEFAULT_APP_BASE_URL = "https://app.promeos.io"

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"

# Mapping role BE → persona endpoint (cohérent FE useEvents.js Phase 1.C
# + events_query_service.PERSONA_TO_OWNER_ROLES Phase 1.A).
# Les roles non listés → persona=None (no filter, tous events bruts).
ROLE_TO_PERSONA: dict[str, str] = {
    "ENERGY_MANAGER": "energy_manager",
    "RESP_SITE": "energy_manager",  # Site Manager → même filtre Energy Manager
    "DAF": "daf",
    "DG_OWNER": "daf",  # DG owner = décideur financier
    "DSI_ADMIN": "admin",
}


# ── Result dataclass ───────────────────────────────────────────────


@dataclass
class DigestRunSummary:
    """Compteurs run dispatch — mirror schema Pydantic schemas/digest.py."""

    sent: int = 0
    skipped_no_opt_in: int = 0
    skipped_no_events: int = 0
    failed: int = 0
    dry_run: bool = False
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


# ── Jinja2 environment (singleton lazy) ─────────────────────────────


_env: Optional[Environment] = None


def _get_jinja_env() -> Environment:
    """Singleton Jinja2 environment — autoescape HTML/J2."""
    global _env
    if _env is None:
        _env = Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html", "j2"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    return _env


# ── Public API ──────────────────────────────────────────────────────


def dispatch_daily_digest(
    db: Session,
    dry_run: bool = False,
    user_filter: Optional[list[int]] = None,
) -> DigestRunSummary:
    """Dispatch digest matinal aux users opt-in avec events.

    Parameters
    ----------
    db : Session
    dry_run : bool
        Si True, rend les templates et compte les destinataires SANS
        appeler email_provider. Sample HTML/text disponibles dans les
        logs DEBUG.
    user_filter : Optional[list[int]]
        Si fourni, restreint à ces user_ids (test/replay).

    Returns
    -------
    DigestRunSummary
        Compteurs propres + correlation_id pour cross-log.
    """
    summary = DigestRunSummary(dry_run=dry_run)
    cid = summary.correlation_id

    users = _query_opted_in_users(db, user_filter)
    logger.info("digest.dispatch start cid=%s users=%d dry_run=%s", cid, len(users), dry_run)

    app_base_url = os.environ.get("PROMEOS_APP_BASE_URL", DEFAULT_APP_BASE_URL)
    date_fr = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    provider = None  # lazy init si non dry_run

    for user in users:
        try:
            org_id, persona = _resolve_org_and_persona(user)
            if org_id is None:
                # User sans UserOrgRole — pas de scope org. Pas une erreur.
                logger.warning("digest.dispatch user_no_org cid=%s user_id=%d", cid, user.id)
                summary.skipped_no_events += 1
                continue

            events_response = get_upcoming_events(
                db,
                org_id=org_id,
                persona=persona,
                horizon_days=DIGEST_HORIZON_DAYS,
                limit=DIGEST_EVENTS_LIMIT,
            )
            events = events_response["events"]
            events_serialized = [_event_to_template_dict(e) for e in events]

            if not events_serialized:
                summary.skipped_no_events += 1
                continue

            html_body, text_body = _render_digest_templates(
                user=user,
                events=events_serialized,
                date_fr=date_fr,
                app_base_url=app_base_url,
            )

            if dry_run:
                summary.sent += 1
                logger.info(
                    "digest.dispatch dry_run rendered cid=%s user_id=%d events=%d",
                    cid,
                    user.id,
                    len(events_serialized),
                )
                continue

            if provider is None:
                provider = get_email_provider()

            result = provider.send_email(
                to=user.email,
                to_name=f"{user.prenom} {user.nom}".strip(),
                subject=_build_subject(events_serialized),
                html_body=html_body,
                text_body=text_body,
                tags=["digest", "daily", f"cid:{cid}"],
            )

            _record_send_result(summary, result, cid, user.id)

        except Exception as exc:  # noqa: BLE001 — silent fail anti-crash
            summary.failed += 1
            logger.error(
                "digest.dispatch unexpected_error cid=%s user_id=%d err=%s",
                cid,
                user.id,
                type(exc).__name__,
            )

    logger.info(
        "digest.dispatch end cid=%s sent=%d skipped_no_events=%d failed=%d dry_run=%s",
        cid,
        summary.sent,
        summary.skipped_no_events,
        summary.failed,
        dry_run,
    )
    return summary


# ── Helpers internes ────────────────────────────────────────────────


def _query_opted_in_users(db: Session, user_filter: Optional[list[int]]) -> list[User]:
    """Users actifs avec digest_daily_enabled=True."""
    q = (
        db.query(User)
        .join(UserNotificationPreference, UserNotificationPreference.user_id == User.id)
        .filter(User.actif.is_(True))
        .filter(UserNotificationPreference.digest_daily_enabled.is_(True))
    )
    if user_filter:
        q = q.filter(User.id.in_(user_filter))
    return q.all()


def _resolve_org_and_persona(user: User) -> tuple[Optional[int], Optional[str]]:
    """Résout (org_id, persona) depuis user.org_roles[0].

    User sans UserOrgRole → (None, None). Le caller skip ces users.
    """
    if not user.org_roles:
        return None, None
    first_role = user.org_roles[0]
    persona = ROLE_TO_PERSONA.get(first_role.role.name)  # role.name = enum key
    return first_role.org_id, persona


def _event_to_template_dict(event) -> dict:
    """Sérialise SolEventCard → dict pour rendu Jinja2.

    Pas de PII technique exposée (event.id, source.last_updated_at en
    string brute). Garde les champs métier nécessaires au template.
    """
    return {
        "severity": event.severity,
        "title": event.title,
        "narrative": event.narrative,
        "impact": {
            "value": event.impact.value,
            "unit": event.impact.unit,
            "period": event.impact.period,
        },
        "source": {
            "methodology": event.source.methodology,
        },
        "action": {
            "label": event.action.label,
            "route": event.action.route,
        },
    }


def _render_digest_templates(
    user: User,
    events: list[dict],
    date_fr: str,
    app_base_url: str,
) -> tuple[str, str]:
    """Render HTML + text. Pas d'exception silencieuse — si template KO,
    laisse remonter l'erreur (caller capture en summary.failed)."""
    env = _get_jinja_env()
    ctx = {
        "user": {"prenom": user.prenom},
        "events": events,
        "date_fr": date_fr,
        "app_base_url": app_base_url,
    }
    html_tmpl = env.get_template("digest_daily.html.j2")
    text_tmpl = env.get_template("digest_daily.txt.j2")
    return html_tmpl.render(**ctx), text_tmpl.render(**ctx)


def _build_subject(events: list[dict]) -> str:
    n = len(events)
    return f"PROMEOS — {n} signal{'s' if n > 1 else ''} aujourd'hui"


def _record_send_result(
    summary: DigestRunSummary,
    result: EmailResult,
    cid: str,
    user_id: int,
) -> None:
    if result.success:
        summary.sent += 1
        logger.info(
            "digest.dispatch sent cid=%s user_id=%d attempts=%d latency_ms=%.1f",
            cid,
            user_id,
            result.attempts,
            result.latency_ms,
        )
    else:
        summary.failed += 1
        logger.warning(
            "digest.dispatch failed cid=%s user_id=%d attempts=%d error=%s",
            cid,
            user_id,
            result.attempts,
            result.error,
        )
