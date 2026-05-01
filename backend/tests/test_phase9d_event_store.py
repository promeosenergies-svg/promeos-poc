"""Phase 9.D — Source-guards event store temporel.

Vérifie l'infrastructure de journal append-only des SolEventCard :

1. Modèle `EventHistorySnapshot` exposé + table créée par migration
2. `record_event_snapshot()` persiste un event avec timestamp + payload JSON
3. `compute_events_at_date()` filtre `recorded_at ≤ target_date`
4. Tri DESC par recorded_at (event le plus récent en 1er)
5. Limit anti-explosion (100 par défaut)
6. `purge_snapshots_before()` GC manuel V2

Audit final ticket BL-6 closé Phase 9.D MVP. Wiring automatique dans
`compute_events()` reste opt-in V2 selon panel Phase 5.

Ref : sprint narrative-sol2 Phase 9.D.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    EventHistorySnapshot,
    Organisation,
)
from services.event_bus.types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventSource,
    SolEventCard,
)
from services.narrative.event_history_service import (
    compute_events_at_date,
    purge_snapshots_before,
    record_event_snapshot,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def org(db_session):
    org = Organisation(nom="Test Org", type_client="bureau", actif=True)
    db_session.add(org)
    db_session.commit()
    return org


def _make_event(event_type: str, recorded_at: datetime, title: str = "Test"):
    return SolEventCard(
        id=f"{event_type}:{recorded_at.isoformat()}",
        event_type=event_type,
        severity="warning",
        title=title,
        narrative=f"Narrative {event_type}",
        impact=EventImpact(value=10.0, unit="%", period="week"),
        source=EventSource(
            system="RegOps",
            last_updated_at=recorded_at,
            confidence="high",
        ),
        action=EventAction(label="Voir", route="/test"),
        linked_assets=EventLinkedAssets(org_id=1, site_ids=[1]),
    )


# ─── record_event_snapshot ─────────────────────────────────────────────────


class TestRecordEventSnapshot:
    def test_record_persists_snapshot(self, db_session, org):
        event = _make_event("consumption_drift", datetime(2026, 5, 1, tzinfo=timezone.utc))
        snapshot = record_event_snapshot(db_session, org.id, event)
        db_session.commit()

        assert snapshot.id is not None
        assert snapshot.org_id == org.id
        assert snapshot.event_type == "consumption_drift"
        # SQLite drop tzinfo — comparer naive
        assert snapshot.recorded_at.replace(tzinfo=None) == datetime(2026, 5, 1)

    def test_record_serializes_payload_json(self, db_session, org):
        event = _make_event("billing_anomaly", datetime(2026, 5, 1, tzinfo=timezone.utc))
        snapshot = record_event_snapshot(db_session, org.id, event)
        db_session.commit()

        payload = json.loads(snapshot.payload_json)
        assert payload["event_type"] == "billing_anomaly"
        assert payload["severity"] == "warning"
        assert payload["title"] == "Test"

    def test_record_uses_event_source_last_updated_when_no_recorded_at(self, db_session, org):
        """Si recorded_at non fourni, utilise event.source.last_updated_at."""
        event_time = datetime(2026, 4, 15, 14, 30, tzinfo=timezone.utc)
        event = _make_event("consumption_drift", event_time)
        snapshot = record_event_snapshot(db_session, org.id, event)
        db_session.commit()

        # SQLite drop tzinfo — comparer naive
        assert snapshot.recorded_at.replace(tzinfo=None) == event_time.replace(tzinfo=None)

    def test_record_explicit_recorded_at_overrides_event_source(self, db_session, org):
        """recorded_at explicite override event.source.last_updated_at."""
        event_time = datetime(2026, 5, 1, tzinfo=timezone.utc)
        explicit_time = datetime(2026, 4, 1, tzinfo=timezone.utc)
        event = _make_event("consumption_drift", event_time)
        snapshot = record_event_snapshot(db_session, org.id, event, recorded_at=explicit_time)
        db_session.commit()

        assert snapshot.recorded_at.replace(tzinfo=None) == explicit_time.replace(tzinfo=None)


# ─── compute_events_at_date ────────────────────────────────────────────────


class TestComputeEventsAtDate:
    def test_filters_by_target_date(self, db_session, org):
        """Seuls les snapshots avec recorded_at ≤ target_date retournés."""
        # 3 events à des dates différentes
        for date_str in ("2026-04-01", "2026-04-15", "2026-05-01"):
            recorded = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            event = _make_event("consumption_drift", recorded, title=f"E{date_str}")
            record_event_snapshot(db_session, org.id, event)
        db_session.commit()

        target = datetime(2026, 4, 20, tzinfo=timezone.utc)
        result = compute_events_at_date(db_session, org.id, target)

        # Seulement les 2 events avant target_date
        assert len(result) == 2
        # Tri DESC : le plus récent (2026-04-15) en 1er
        assert result[0].recorded_at.date() == datetime(2026, 4, 15).date()

    def test_filters_by_org_id(self, db_session, org):
        """Org-scoping : ne retourne pas les snapshots d'autres orgs."""
        # Création autre org
        other_org = Organisation(nom="Other", type_client="bureau", actif=True)
        db_session.add(other_org)
        db_session.commit()

        # Event dans org cible
        event = _make_event("consumption_drift", datetime(2026, 5, 1, tzinfo=timezone.utc))
        record_event_snapshot(db_session, org.id, event)
        # Event dans autre org (même date)
        record_event_snapshot(db_session, other_org.id, event)
        db_session.commit()

        target = datetime(2026, 6, 1, tzinfo=timezone.utc)
        result_org = compute_events_at_date(db_session, org.id, target)
        result_other = compute_events_at_date(db_session, other_org.id, target)

        assert len(result_org) == 1
        assert len(result_other) == 1
        assert result_org[0].org_id != result_other[0].org_id

    def test_respects_limit(self, db_session, org):
        """Limit anti-explosion (défaut 100, paramétrable)."""
        # 5 events
        for i in range(5):
            event = _make_event(
                "consumption_drift",
                datetime(2026, 5, 1, tzinfo=timezone.utc) - timedelta(days=i),
                title=f"E{i}",
            )
            record_event_snapshot(db_session, org.id, event)
        db_session.commit()

        target = datetime(2026, 6, 1, tzinfo=timezone.utc)
        result = compute_events_at_date(db_session, org.id, target, limit=3)
        assert len(result) == 3

    def test_empty_when_no_snapshots_before_target(self, db_session, org):
        event = _make_event("consumption_drift", datetime(2026, 5, 1, tzinfo=timezone.utc))
        record_event_snapshot(db_session, org.id, event)
        db_session.commit()

        # Target avant le snapshot
        target = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = compute_events_at_date(db_session, org.id, target)
        assert result == []


# ─── purge_snapshots_before ────────────────────────────────────────────────


class TestPurgeSnapshotsBefore:
    def test_deletes_old_snapshots(self, db_session, org):
        """Supprime snapshots avec recorded_at < before_date."""
        for date_str in ("2026-01-01", "2026-04-01", "2026-05-01"):
            recorded = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            event = _make_event("consumption_drift", recorded, title=date_str)
            record_event_snapshot(db_session, org.id, event)
        db_session.commit()

        cutoff = datetime(2026, 4, 1, tzinfo=timezone.utc)
        deleted = purge_snapshots_before(db_session, cutoff)
        db_session.commit()

        # Seul le snapshot 2026-01-01 supprimé (< 2026-04-01)
        assert deleted == 1
        # 2 snapshots restants
        remaining = db_session.query(EventHistorySnapshot).filter(EventHistorySnapshot.org_id == org.id).count()
        assert remaining == 2

    def test_purge_per_org_isolates(self, db_session, org):
        """Purge avec org_id ne touche que cette org."""
        other = Organisation(nom="Other", type_client="bureau", actif=True)
        db_session.add(other)
        db_session.commit()

        old_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        event = _make_event("consumption_drift", old_time)
        record_event_snapshot(db_session, org.id, event)
        record_event_snapshot(db_session, other.id, event)
        db_session.commit()

        deleted = purge_snapshots_before(db_session, datetime(2026, 4, 1, tzinfo=timezone.utc), org_id=org.id)
        db_session.commit()

        assert deleted == 1
        # Autre org intacte
        other_count = db_session.query(EventHistorySnapshot).filter(EventHistorySnapshot.org_id == other.id).count()
        assert other_count == 1


# ─── Source-guard model exposé ─────────────────────────────────────────────


class TestModelExport:
    def test_event_history_snapshot_in_models_init(self):
        """Source-guard : EventHistorySnapshot est exposé via models/__init__."""
        from models import EventHistorySnapshot as ImportedModel

        assert ImportedModel is EventHistorySnapshot


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
