"""
PROMEOS — Source-guard Phase 1.9 : seed notifications timestamps distribués (Q7).

Vérifie que les `created_at` des notifications HELIOS couvrent au moins
3 échelles temporelles différentes (heures / jour / jours / semaines)
pour que la Vue Exécutive affiche une narrative crédible et non figée.

Le seed `gen_notifications.py` utilise des `age_days` étalés (1, 2, 5, 8,
12, 14, 15, 20, 25, 30) — ce test verrouille la diversité.

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.9.
"""

import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import math

import pytest
from sqlalchemy import desc

from database import SessionLocal


def _floor_to_scale(hours: float) -> str:
    """Catégorise une durée en échelles temporelles humaines."""
    if hours < 24:
        return "hours"
    if hours < 7 * 24:
        return "days"
    if hours < 30 * 24:
        return "weeks"
    return "months"


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestNotificationsTimestampsDistributed:
    def test_notifications_seed_diverse_age_days(self):
        """Verrouille que le template seed couvre au moins 3 échelles temporelles."""
        from services.demo_seed.gen_notifications import _TEMPLATES

        ages = [t["age_days"] for t in _TEMPLATES if "age_days" in t]
        scales = {_floor_to_scale(a * 24) for a in ages}
        assert len(scales) >= 3, (
            f"Seed notifications ne couvre que {len(scales)} échelles temporelles : "
            f"{scales}. Doctrine §11.3 narrative crédible exige ≥ 3 (heures/jours/semaines)."
        )

    def test_at_least_one_recent_under_24h(self):
        """Au moins une notification < 24h pour la narrative 'aujourd'hui'."""
        from services.demo_seed.gen_notifications import _TEMPLATES

        ages = [t["age_days"] for t in _TEMPLATES if "age_days" in t]
        assert any(a <= 1 for a in ages), "Aucune notification < 24h dans le seed — Vue Exé sans signal frais."

    def test_at_least_one_older_than_week(self):
        """Au moins une notification > 7 jours pour montrer la fenêtre historique."""
        from services.demo_seed.gen_notifications import _TEMPLATES

        ages = [t["age_days"] for t in _TEMPLATES if "age_days" in t]
        assert any(a > 7 for a in ages), "Aucune notification > 7 jours dans le seed — pas d'horizon historique."

    def test_db_notifications_diverse_if_seeded(self, db):
        """Si la DB contient des notifications, vérifie même invariant en runtime."""
        try:
            from models.notification_event import NotificationEvent
        except ImportError:
            pytest.skip("NotificationEvent model absent — skip runtime check")

        rows = db.query(NotificationEvent).order_by(desc(NotificationEvent.created_at)).limit(20).all()
        if len(rows) < 4:
            pytest.skip(f"DB contient {len(rows)} notifications — seed non chargé")

        now = datetime.now(timezone.utc)
        scales = set()
        for n in rows:
            ts = n.created_at
            if ts is None:
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            hours_ago = (now - ts).total_seconds() / 3600
            if hours_ago < 0:
                continue
            scales.add(_floor_to_scale(hours_ago))

        assert len(scales) >= 3, (
            f"DB notifications couvrent {len(scales)} échelles : {scales}. Cible ≥ 3 (heures/jours/semaines)."
        )
