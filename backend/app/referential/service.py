"""
PROMEOS Referentiel — Service layer for Bill Intelligence integration.
Provides source traceability for tariff/tax calculations.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

INDICES_DIR = Path(__file__).resolve().parent / "indices"
SNAPSHOTS_DIR = Path(__file__).resolve().parent / "snapshots"


def get_sources_for_calc(tags: list[str]) -> list[dict]:
    """
    Return sources matching any of the given tags.
    Used by bill calculation to identify which regulatory sources apply.

    Returns list of dicts with:
    - source_id
    - url
    - sha256_raw (latest snapshot)
    - snapshot_date
    - authority
    - regulation
    """
    manifest_path = INDICES_DIR / "sources_manifest.json"
    if not manifest_path.exists():
        return []

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = []

    for source_id, data in manifest.get("sources", {}).items():
        source_tags = set(data.get("tags", []))
        if source_tags.intersection(tags):
            latest = data.get("latest", {})
            results.append({
                "source_id": source_id,
                "url": data.get("url"),
                "sha256_raw": latest.get("sha256_raw"),
                "snapshot_date": latest.get("date"),
                "authority": data.get("authority"),
                "regulation": data.get("regulation"),
                "ref": f"{source_id}@{latest.get('sha256_raw', 'unknown')[:12]}",
            })

    return results


def build_calc_trace(calc_id: str, tags: list[str], amount: float,
                     details: Optional[dict] = None) -> dict:
    """
    Build an audit trace for a tariff/tax calculation.
    Links the calculated amount to its regulatory sources.

    Returns a calc_trace dict ready for storage/logging.
    """
    sources = get_sources_for_calc(tags)
    manifest_path = INDICES_DIR / "sources_manifest.json"

    manifest_version = None
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_version = manifest.get("generated_at")

    return {
        "calc_id": calc_id,
        "calculated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "amount": amount,
        "tags_queried": tags,
        "sources_used": [s["ref"] for s in sources],
        "sources_detail": sources,
        "manifest_version": manifest_version,
        "details": details,
    }


def get_manifest_stats() -> dict:
    """Return summary stats from the manifest."""
    manifest_path = INDICES_DIR / "sources_manifest.json"
    if not manifest_path.exists():
        return {"status": "no_manifest"}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return manifest.get("stats", {})
