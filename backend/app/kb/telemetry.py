"""
PROMEOS KB - Telemetry (fire-and-forget)
Log every apply() call for coverage/usage metrics.
Schema: kb_apply_events (event_ts, domain, allow_drafts, applicable_count, missing_count, latency_ms, context_keys).
"""

import json
import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from .models import get_kb_db

logger = logging.getLogger(__name__)


def ensure_telemetry_schema() -> None:
    """Create kb_apply_events + kb_item_hits tables if missing. Idempotent."""
    db = get_kb_db()
    cursor = db.conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_apply_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_ts TEXT NOT NULL DEFAULT (datetime('now')),
            domain TEXT,
            allow_drafts INTEGER NOT NULL DEFAULT 0,
            applicable_count INTEGER NOT NULL,
            missing_count INTEGER NOT NULL,
            total_evaluated INTEGER NOT NULL,
            latency_ms REAL NOT NULL,
            context_keys_json TEXT NOT NULL,
            missing_fields_json TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_apply_events_ts ON kb_apply_events(event_ts)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_apply_events_domain ON kb_apply_events(domain)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_item_hits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            kb_item_id TEXT NOT NULL,
            domain TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES kb_apply_events(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_hits_item ON kb_item_hits(kb_item_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_hits_event ON kb_item_hits(event_id)")

    db.conn.commit()


@contextmanager
def measure_latency():
    """Yield a callable that returns elapsed ms since enter."""
    start = time.perf_counter()
    yield lambda: (time.perf_counter() - start) * 1000.0


def log_apply_event(
    *,
    domain: Optional[str],
    allow_drafts: bool,
    site_context: Dict[str, Any],
    result: Dict[str, Any],
    latency_ms: float,
) -> None:
    """Persist one apply() call. Fire-and-forget: exceptions swallowed."""
    try:
        db = get_kb_db()
        cursor = db.conn.cursor()

        stats = result.get("stats", {}) or {}
        applicable_items = result.get("applicable_items", []) or []
        missing_fields = result.get("missing_fields", []) or []

        cursor.execute(
            """
            INSERT INTO kb_apply_events (
                domain, allow_drafts, applicable_count, missing_count,
                total_evaluated, latency_ms, context_keys_json, missing_fields_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                domain,
                1 if allow_drafts else 0,
                len(applicable_items),
                len(missing_fields),
                stats.get("total_items_evaluated", 0),
                round(latency_ms, 3),
                json.dumps(sorted(site_context.keys())),
                json.dumps(missing_fields),
            ),
        )
        event_id = cursor.lastrowid

        hit_rows = [
            (event_id, item["kb_item_id"], item["domain"])
            for item in applicable_items
            if item.get("kb_item_id") and item.get("domain")
        ]
        if hit_rows:
            cursor.executemany(
                "INSERT INTO kb_item_hits (event_id, kb_item_id, domain) VALUES (?, ?, ?)",
                hit_rows,
            )

        db.conn.commit()
    except Exception:
        logger.debug("KB telemetry failed", exc_info=True)


def prune_old_events(retention_days: int = 90) -> int:
    """Delete kb_apply_events older than retention_days. Returns rows deleted.

    Call this via a cron/scheduled job. kb_item_hits rows cascade via FK.
    """
    db = get_kb_db()
    cursor = db.conn.cursor()
    cursor.execute(f"DELETE FROM kb_apply_events WHERE event_ts < datetime('now', '-{int(retention_days)} days')")
    deleted = cursor.rowcount
    db.conn.commit()
    return deleted


def get_metrics(since_days: int = 30) -> Dict[str, Any]:
    """Aggregate KB usage metrics over the last N days."""
    db = get_kb_db()
    cursor = db.conn.cursor()
    since_clause = f"datetime('now', '-{int(since_days)} days')"

    cursor.execute(f"SELECT COUNT(*) FROM kb_apply_events WHERE event_ts >= {since_clause}")
    total_calls = cursor.fetchone()[0]

    if total_calls == 0:
        return {
            "since_days": since_days,
            "total_calls": 0,
            "coverage": {"calls_with_matches": 0, "calls_without_matches": 0, "coverage_pct": 0.0},
            "latency_ms": {"avg": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0},
            "by_domain": [],
            "top_items": [],
            "top_missing_fields": [],
        }

    cursor.execute(
        f"""
        SELECT
            SUM(CASE WHEN applicable_count > 0 THEN 1 ELSE 0 END) AS with_matches,
            SUM(CASE WHEN applicable_count = 0 THEN 1 ELSE 0 END) AS without_matches
        FROM kb_apply_events WHERE event_ts >= {since_clause}
        """
    )
    with_matches, without_matches = cursor.fetchone()
    coverage_pct = (with_matches / total_calls * 100.0) if total_calls else 0.0

    cursor.execute(f"SELECT latency_ms FROM kb_apply_events WHERE event_ts >= {since_clause} ORDER BY latency_ms")
    latencies = [row[0] for row in cursor.fetchall()]

    def percentile(data: List[float], p: float) -> float:
        if not data:
            return 0.0
        k = (len(data) - 1) * p
        f = int(k)
        c = min(f + 1, len(data) - 1)
        return data[f] + (data[c] - data[f]) * (k - f)

    latency_stats = {
        "avg": sum(latencies) / len(latencies) if latencies else 0.0,
        "p50": percentile(latencies, 0.5),
        "p95": percentile(latencies, 0.95),
        "max": max(latencies) if latencies else 0.0,
    }

    cursor.execute(
        f"""
        SELECT domain, COUNT(*) AS n
        FROM kb_apply_events
        WHERE event_ts >= {since_clause} AND domain IS NOT NULL
        GROUP BY domain ORDER BY n DESC
        """
    )
    by_domain = [{"domain": r[0], "calls": r[1]} for r in cursor.fetchall()]

    cursor.execute(
        f"""
        SELECT h.kb_item_id, h.domain, COUNT(*) AS hits
        FROM kb_item_hits h
        JOIN kb_apply_events e ON e.id = h.event_id
        WHERE e.event_ts >= {since_clause}
        GROUP BY h.kb_item_id, h.domain
        ORDER BY hits DESC LIMIT 10
        """
    )
    top_items = [{"kb_item_id": r[0], "domain": r[1], "hits": r[2]} for r in cursor.fetchall()]

    cursor.execute(
        f"SELECT missing_fields_json FROM kb_apply_events WHERE event_ts >= {since_clause} AND missing_fields_json IS NOT NULL"
    )
    field_counter: Dict[str, int] = {}
    for (fields_json,) in cursor.fetchall():
        try:
            for field in json.loads(fields_json):
                field_counter[field] = field_counter.get(field, 0) + 1
        except (ValueError, TypeError):
            continue
    top_missing_fields = [
        {"field": f, "occurrences": n} for f, n in sorted(field_counter.items(), key=lambda x: x[1], reverse=True)[:10]
    ]

    return {
        "since_days": since_days,
        "total_calls": total_calls,
        "coverage": {
            "calls_with_matches": with_matches or 0,
            "calls_without_matches": without_matches or 0,
            "coverage_pct": round(coverage_pct, 2),
        },
        "latency_ms": {k: round(v, 3) for k, v in latency_stats.items()},
        "by_domain": by_domain,
        "top_items": top_items,
        "top_missing_fields": top_missing_fields,
    }
