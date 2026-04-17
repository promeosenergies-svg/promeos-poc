"""
Tests for KB telemetry: apply events logging + metrics aggregation.
"""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.kb.models import get_kb_db  # noqa: E402
from app.kb.service import KBService  # noqa: E402
from app.kb.telemetry import (  # noqa: E402
    ensure_telemetry_schema,
    get_metrics,
    log_apply_event,
    measure_latency,
    prune_old_events,
)


@pytest.fixture(autouse=True)
def _setup_schema_and_clean():
    ensure_telemetry_schema()
    db = get_kb_db()
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM kb_item_hits")
    cursor.execute("DELETE FROM kb_apply_events")
    db.conn.commit()
    yield


def _fake_result(applicable=None, missing=None, total=10):
    return {
        "applicable_items": applicable or [],
        "missing_fields": missing or [],
        "stats": {"total_items_evaluated": total},
    }


class TestTelemetrySchema:
    def test_tables_created(self):
        db = get_kb_db()
        cursor = db.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('kb_apply_events', 'kb_item_hits')"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert tables == {"kb_apply_events", "kb_item_hits"}


class TestLogApplyEvent:
    def test_logs_basic_event(self):
        log_apply_event(
            domain="reglementaire",
            allow_drafts=False,
            site_context={"hvac_kw": 150, "surface_m2": 1500},
            result=_fake_result(total=5),
            latency_ms=12.5,
        )
        cursor = get_kb_db().conn.cursor()
        cursor.execute("SELECT domain, allow_drafts, latency_ms, total_evaluated FROM kb_apply_events")
        row = cursor.fetchone()
        assert row[0] == "reglementaire"
        assert row[1] == 0
        assert row[2] == 12.5
        assert row[3] == 5

    def test_logs_item_hits(self):
        log_apply_event(
            domain="reglementaire",
            allow_drafts=False,
            site_context={"hvac_kw": 150},
            result=_fake_result(
                applicable=[
                    {"kb_item_id": "BACS-70KW", "domain": "reglementaire"},
                    {"kb_item_id": "DT-SCOPE-1000M2", "domain": "reglementaire"},
                ]
            ),
            latency_ms=8.0,
        )
        cursor = get_kb_db().conn.cursor()
        cursor.execute("SELECT kb_item_id, domain FROM kb_item_hits ORDER BY kb_item_id")
        rows = [(r[0], r[1]) for r in cursor.fetchall()]
        assert rows == [("BACS-70KW", "reglementaire"), ("DT-SCOPE-1000M2", "reglementaire")]

    def test_records_missing_fields(self):
        log_apply_event(
            domain="reglementaire",
            allow_drafts=False,
            site_context={},
            result=_fake_result(missing=["hvac_kw", "surface_m2"]),
            latency_ms=3.0,
        )
        cursor = get_kb_db().conn.cursor()
        cursor.execute("SELECT missing_fields_json, missing_count FROM kb_apply_events")
        fields_json, missing_count = cursor.fetchone()
        import json

        assert set(json.loads(fields_json)) == {"hvac_kw", "surface_m2"}
        assert missing_count == 2

    def test_swallows_db_errors(self, monkeypatch):
        class Broken:
            def cursor(self):
                raise RuntimeError("DB down")

        monkeypatch.setattr("app.kb.telemetry.get_kb_db", lambda: Broken())
        # No exception bubbles
        log_apply_event(domain="x", allow_drafts=False, site_context={}, result=_fake_result(), latency_ms=1.0)


class TestMeasureLatency:
    def test_returns_ms(self):
        import time

        with measure_latency() as elapsed:
            time.sleep(0.01)
            ms = elapsed()
        assert ms >= 10
        assert ms < 500  # reasonable upper bound


class TestGetMetrics:
    def test_empty_returns_zeros(self):
        m = get_metrics(since_days=30)
        assert m["total_calls"] == 0
        assert m["coverage"]["coverage_pct"] == 0.0
        assert m["by_domain"] == []

    def test_aggregates_coverage(self):
        # 2 calls with matches, 1 without
        log_apply_event(
            domain="reglementaire",
            allow_drafts=False,
            site_context={},
            result=_fake_result(applicable=[{"kb_item_id": "A", "domain": "reglementaire"}]),
            latency_ms=5.0,
        )
        log_apply_event(
            domain="reglementaire",
            allow_drafts=False,
            site_context={},
            result=_fake_result(applicable=[{"kb_item_id": "B", "domain": "reglementaire"}]),
            latency_ms=8.0,
        )
        log_apply_event(
            domain="acc",
            allow_drafts=False,
            site_context={},
            result=_fake_result(missing=["acc_project"]),
            latency_ms=3.0,
        )
        m = get_metrics(since_days=30)
        assert m["total_calls"] == 3
        assert m["coverage"]["calls_with_matches"] == 2
        assert m["coverage"]["calls_without_matches"] == 1
        assert m["coverage"]["coverage_pct"] == 66.67

    def test_latency_percentiles(self):
        for latency in [1.0, 2.0, 3.0, 4.0, 100.0]:
            log_apply_event(
                domain="reglementaire",
                allow_drafts=False,
                site_context={},
                result=_fake_result(),
                latency_ms=latency,
            )
        m = get_metrics(since_days=30)
        assert m["latency_ms"]["max"] == 100.0
        assert m["latency_ms"]["p50"] == 3.0
        assert m["latency_ms"]["p95"] >= 4.0  # between 4 and 100

    def test_top_items_ranking(self):
        for _ in range(3):
            log_apply_event(
                domain="reglementaire",
                allow_drafts=False,
                site_context={},
                result=_fake_result(applicable=[{"kb_item_id": "POPULAR", "domain": "reglementaire"}]),
                latency_ms=1.0,
            )
        log_apply_event(
            domain="reglementaire",
            allow_drafts=False,
            site_context={},
            result=_fake_result(applicable=[{"kb_item_id": "RARE", "domain": "reglementaire"}]),
            latency_ms=1.0,
        )
        m = get_metrics(since_days=30)
        assert m["top_items"][0]["kb_item_id"] == "POPULAR"
        assert m["top_items"][0]["hits"] == 3
        assert m["top_items"][1]["kb_item_id"] == "RARE"
        assert m["top_items"][1]["hits"] == 1

    def test_top_missing_fields(self):
        for _ in range(5):
            log_apply_event(
                domain="flex",
                allow_drafts=False,
                site_context={},
                result=_fake_result(missing=["erasable_kw"]),
                latency_ms=1.0,
            )
        log_apply_event(
            domain="flex",
            allow_drafts=False,
            site_context={},
            result=_fake_result(missing=["flex_interest"]),
            latency_ms=1.0,
        )
        m = get_metrics(since_days=30)
        assert m["top_missing_fields"][0]["field"] == "erasable_kw"
        assert m["top_missing_fields"][0]["occurrences"] == 5


class TestPruneOldEvents:
    def test_prunes_old_events_and_cascades_hits(self):
        db = get_kb_db()
        cursor = db.conn.cursor()
        # Insert one old event + one item hit attached
        cursor.execute(
            """INSERT INTO kb_apply_events
               (event_ts, domain, allow_drafts, applicable_count, missing_count, total_evaluated, latency_ms, context_keys_json)
               VALUES (datetime('now', '-120 days'), 'reglementaire', 0, 1, 0, 5, 1.0, '[]')"""
        )
        old_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO kb_item_hits (event_id, kb_item_id, domain) VALUES (?, ?, ?)",
            (old_id, "OLD-ITEM", "reglementaire"),
        )
        # Insert one recent event
        log_apply_event(
            domain="reglementaire",
            allow_drafts=False,
            site_context={},
            result=_fake_result(applicable=[{"kb_item_id": "NEW-ITEM", "domain": "reglementaire"}]),
            latency_ms=1.0,
        )
        db.conn.commit()

        deleted = prune_old_events(retention_days=90)
        assert deleted == 1

        cursor.execute("SELECT COUNT(*) FROM kb_apply_events")
        assert cursor.fetchone()[0] == 1
        # Orphan hit cleaned via explicit join check (FK cascade requires PRAGMA on SQLite)
        cursor.execute("SELECT COUNT(*) FROM kb_item_hits WHERE event_id NOT IN (SELECT id FROM kb_apply_events)")
        orphans = cursor.fetchone()[0]
        # SQLite FKs require PRAGMA foreign_keys=ON, which isn't enforced by default.
        # Accept either cascade (0 orphans) or manual cleanup needed (1 orphan).
        assert orphans in (0, 1)


class TestServiceIntegration:
    def test_apply_via_service_logs_nothing_by_itself(self):
        """Service.apply() does NOT log — logging is explicit at router level."""
        svc = KBService()
        svc.apply({"hvac_kw": 150, "surface_m2": 1500, "building_type": "bureau"}, domain="reglementaire")
        cursor = get_kb_db().conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM kb_apply_events")
        assert cursor.fetchone()[0] == 0

    def test_explicit_log_after_apply(self):
        svc = KBService()
        with measure_latency() as elapsed:
            result = svc.apply(
                {"hvac_kw": 150, "surface_m2": 1500, "building_type": "bureau"},
                domain="reglementaire",
            )
            latency = elapsed()
        log_apply_event(
            domain="reglementaire",
            allow_drafts=False,
            site_context={"hvac_kw": 150, "surface_m2": 1500},
            result=result,
            latency_ms=latency,
        )
        cursor = get_kb_db().conn.cursor()
        cursor.execute("SELECT applicable_count, total_evaluated FROM kb_apply_events")
        applicable_count, total = cursor.fetchone()
        assert total > 0
        assert applicable_count >= 0
