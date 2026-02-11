"""
PROMEOS Referentiel — Manifest builder.
Scans snapshots directory, builds sources_manifest.json + optional SQLite index.
"""
import json
import os
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Optional

SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "referential" / "snapshots"
INDICES_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "referential" / "indices"


def build_manifest(window_start: Optional[str] = None, window_end: Optional[str] = None) -> dict:
    """
    Scan all snapshot directories and build a manifest with:
    - latest snapshot per source_id
    - history of all snapshots
    - change detection (content_changed flag)
    - in_window_24m flag
    """
    manifest = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "window": {"start": window_start, "end": window_end},
        "sources": {},
        "stats": {
            "total_sources": 0,
            "total_snapshots": 0,
            "sources_with_changes": 0,
            "errors": 0,
        },
    }

    if not SNAPSHOTS_DIR.exists():
        return manifest

    # Scan source dirs
    for source_dir in sorted(SNAPSHOTS_DIR.iterdir()):
        if not source_dir.is_dir():
            continue
        source_id = source_dir.name

        # Collect all date-stamped snapshot dirs
        snapshot_dates = []
        for date_dir in sorted(source_dir.iterdir()):
            if not date_dir.is_dir():
                continue
            meta_path = date_dir / "metadata.json"
            if not meta_path.exists():
                continue
            snapshot_dates.append(date_dir.name)

        if not snapshot_dates:
            continue

        # Load metadata for each snapshot
        snapshots = []
        prev_hash: Optional[str] = None
        for snap_date in sorted(snapshot_dates):
            meta_path = source_dir / snap_date / "metadata.json"
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                manifest["stats"]["errors"] += 1
                continue

            current_hash = meta.get("sha256_raw", "")
            content_changed = prev_hash is not None and current_hash != prev_hash
            prev_hash = current_hash

            # Check if in 24m window
            doc_date = meta.get("date_mise_en_ligne") or meta.get("date_hint") or snap_date
            if isinstance(doc_date, dict):
                doc_date = snap_date
            in_window = True
            if window_start and doc_date < window_start:
                if not meta.get("baseline", False):
                    in_window = False
            if window_end and doc_date > window_end:
                in_window = False

            snapshots.append({
                "date": snap_date,
                "sha256_raw": current_hash,
                "sha256_md": meta.get("sha256_md", ""),
                "content_changed": content_changed,
                "in_window_24m": in_window,
                "title": meta.get("title"),
                "fetched_at": meta.get("fetched_at_utc"),
            })

        latest = snapshots[-1]
        has_changes = any(s["content_changed"] for s in snapshots)

        manifest["sources"][source_id] = {
            "latest": latest,
            "history": snapshots,
            "total_snapshots": len(snapshots),
            "has_content_changes": has_changes,
            "authority": _get_meta_field(source_dir, snapshots[-1]["date"], "authority"),
            "category": _get_meta_field(source_dir, snapshots[-1]["date"], "category"),
            "energy": _get_meta_field(source_dir, snapshots[-1]["date"], "energy"),
            "regulation": _get_meta_field(source_dir, snapshots[-1]["date"], "regulation"),
            "tags": _get_meta_field(source_dir, snapshots[-1]["date"], "tags") or [],
            "url": _get_meta_field(source_dir, snapshots[-1]["date"], "url"),
        }

        manifest["stats"]["total_sources"] += 1
        manifest["stats"]["total_snapshots"] += len(snapshots)
        if has_changes:
            manifest["stats"]["sources_with_changes"] += 1

    return manifest


def _get_meta_field(source_dir: Path, snap_date: str, field: str):
    """Read a field from a snapshot's metadata.json."""
    meta_path = source_dir / snap_date / "metadata.json"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return meta.get(field)
    except Exception:
        return None


def write_manifest(manifest: dict) -> Path:
    """Write manifest to indices/sources_manifest.json."""
    INDICES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = INDICES_DIR / "sources_manifest.json"
    out_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return out_path


def build_sqlite_index(manifest: dict) -> Path:
    """Build a SQLite index from the manifest for fast queries."""
    INDICES_DIR.mkdir(parents=True, exist_ok=True)
    db_path = INDICES_DIR / "sources_index.sqlite"

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS sources")
    cur.execute("DROP TABLE IF EXISTS snapshots")

    cur.execute("""
        CREATE TABLE sources (
            source_id TEXT PRIMARY KEY,
            url TEXT,
            authority TEXT,
            category TEXT,
            energy TEXT,
            regulation TEXT,
            tags TEXT,
            total_snapshots INTEGER,
            has_content_changes BOOLEAN,
            latest_sha256 TEXT,
            latest_date TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            sha256_raw TEXT,
            sha256_md TEXT,
            content_changed BOOLEAN,
            in_window_24m BOOLEAN,
            title TEXT,
            fetched_at TEXT,
            FOREIGN KEY (source_id) REFERENCES sources(source_id)
        )
    """)
    cur.execute("CREATE INDEX idx_snapshots_source ON snapshots(source_id)")
    cur.execute("CREATE INDEX idx_sources_tags ON sources(tags)")
    cur.execute("CREATE INDEX idx_sources_authority ON sources(authority)")

    for source_id, data in manifest.get("sources", {}).items():
        latest = data.get("latest", {})
        cur.execute("""
            INSERT INTO sources (source_id, url, authority, category, energy, regulation,
                                 tags, total_snapshots, has_content_changes, latest_sha256, latest_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source_id,
            data.get("url"),
            data.get("authority"),
            data.get("category"),
            data.get("energy"),
            data.get("regulation"),
            ",".join(data.get("tags", [])),
            data.get("total_snapshots", 0),
            data.get("has_content_changes", False),
            latest.get("sha256_raw"),
            latest.get("date"),
        ))

        for snap in data.get("history", []):
            cur.execute("""
                INSERT INTO snapshots (source_id, snapshot_date, sha256_raw, sha256_md,
                                       content_changed, in_window_24m, title, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                source_id,
                snap.get("date"),
                snap.get("sha256_raw"),
                snap.get("sha256_md"),
                snap.get("content_changed", False),
                snap.get("in_window_24m", True),
                snap.get("title"),
                snap.get("fetched_at"),
            ))

    conn.commit()
    conn.close()
    return db_path
