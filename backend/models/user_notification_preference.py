"""UserNotificationPreference — préférences digest user-scoped (Phase 2.C).

Q2 audit Phase 0.bis arbitré : nouvelle table dédiée user-scoped (PK
user_id), distincte de :
- `notification_preferences` (org-scoped, V1 badges/snooze, cf. notification.py:156)
- `digest_preferences` (org-scoped, V2 digest org-level, cf. notification.py:end)

Cette table porte exclusivement le **opt-in user-level email digest**.
Pas de relation backref `User.notification_preferences` (éviter coupling
bidirectionnel — `user_notification_preference_service.py` est le seul
chemin canonique).

Schéma :
- user_id : FK users.id ON DELETE CASCADE, UNIQUE (1 ligne par user max)
- digest_daily_enabled : opt-in/opt-out digest matinal Brevo (Phase 2.D)
- digest_daily_locale : i18n future (Phase 3+) — défaut fr-FR
- digest_channels : JSON list, MVP ['email'], forward-compat SMS Phase 3
- created_at / updated_at : audit trail

Réf : docs/audits/sprint_alpha_push_phase0_audit_20260502.md (Q2),
docs/adr/ADR-006-coexistence-notification-service-event-bus.md.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String

from .base import Base


class UserNotificationPreference(Base):
    """Préférences notification niveau utilisateur (digest matinal opt-in)."""

    __tablename__ = "user_notification_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="User (1:1) — CASCADE delete avec users.id",
    )
    digest_daily_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="Opt-in digest matinal 7h45 (Phase 2.D dispatch)",
    )
    digest_daily_locale = Column(
        String(16),
        nullable=False,
        default="fr-FR",
        server_default="fr-FR",
        comment="i18n future — défaut fr-FR",
    )
    digest_channels = Column(
        JSON,
        nullable=False,
        default=lambda: ["email"],
        comment="Channels actifs — MVP ['email'], forward-compat SMS Phase 3",
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UserNotificationPreference user_id={self.user_id} digest_daily_enabled={self.digest_daily_enabled}>"
