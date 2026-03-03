"""
PROMEOS Referentiel — Source fetcher.
Downloads HTML sources, creates snapshots with metadata + hashes.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional

# Allow imports from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.referential.normalize_text import html_to_markdown, extract_title
from scripts.referential.extract_cre_metadata import extract_cre_metadata

USER_AGENT = "PROMEOS-POC/1.0 (referentiel-tarifs; contact@promeos.fr)"
MAX_RETRIES = 3
BACKOFF_BASE = 2.0
TIMEOUT_S = 30
RATE_LIMIT_S = 1.5  # seconds between requests to same domain

SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "referential" / "snapshots"


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _fetch_url(url: str) -> tuple[int, str, str]:
    """
    Fetch a URL with retries and backoff.
    Returns (http_status, content_type, body).
    Raises on final failure.
    """
    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Language": "fr-FR,fr;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")
                charset = "utf-8"
                if "charset=" in content_type:
                    charset = content_type.split("charset=")[-1].split(";")[0].strip()
                body = resp.read().decode(charset, errors="replace")
                return status, content_type, body
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** attempt
                print(f"    [RETRY {attempt}/{MAX_RETRIES}] {url} — {e} — waiting {wait:.0f}s")
                time.sleep(wait)
    raise last_error  # type: ignore


def fetch_source(source: dict, today: str, dry_run: bool = False) -> dict:
    """
    Fetch a single source. Returns a result dict with status info.
    If dry_run=True, validates config without downloading.
    """
    source_id = source["id"]
    url = source["url"]
    result = {
        "source_id": source_id,
        "url": url,
        "status": "pending",
        "error": None,
        "snapshot_path": None,
    }

    if dry_run:
        result["status"] = "dry_run_ok"
        return result

    try:
        http_status, content_type, body = _fetch_url(url)
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        return result

    if http_status != 200:
        result["status"] = "http_error"
        result["error"] = f"HTTP {http_status}"
        return result

    if "text/html" not in content_type.lower() and "text/plain" not in content_type.lower():
        # Some sites return application/xhtml+xml — that's fine
        if "xhtml" not in content_type.lower():
            result["status"] = "warning"
            result["error"] = f"Unexpected content-type: {content_type}"

    # Normalize to markdown
    md_content = html_to_markdown(body)
    title = extract_title(body)

    # Hashes
    sha256_raw = _sha256(body)
    sha256_md = _sha256(md_content)

    # CRE-specific metadata
    cre_meta = {}
    if source.get("authority") == "CRE":
        cre_meta = extract_cre_metadata(body)

    # Build metadata
    metadata = {
        "source_id": source_id,
        "url": url,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat() + "Z",
        "http_status": http_status,
        "content_type": content_type,
        "sha256_raw": sha256_raw,
        "sha256_md": sha256_md,
        "title": title,
        "authority": source.get("authority"),
        "category": source.get("category"),
        "energy": source.get("energy"),
        "regulation": source.get("regulation"),
        "tags": source.get("tags", []),
        "date_hint": source.get("date_hint"),
        "description": source.get("description"),
        "baseline": source.get("baseline", False),
        "raw_size_bytes": len(body.encode("utf-8")),
        "md_size_bytes": len(md_content.encode("utf-8")),
    }
    if cre_meta:
        metadata["cre_metadata"] = cre_meta

    # Write snapshot
    snapshot_dir = SNAPSHOTS_DIR / source_id / today
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    (snapshot_dir / "raw.html").write_text(body, encoding="utf-8")
    (snapshot_dir / "extracted.md").write_text(md_content, encoding="utf-8")
    (snapshot_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    result["status"] = "ok"
    result["snapshot_path"] = str(snapshot_dir)
    result["sha256_raw"] = sha256_raw
    return result


def fetch_all(sources: list[dict], since: Optional[str] = None, until: Optional[str] = None,
              dry_run: bool = False) -> list[dict]:
    """
    Fetch all sources. Filter by date window if provided.
    Rate-limits requests per domain.
    """
    today = date.today().isoformat()
    results = []
    last_domain: Optional[str] = None

    for i, source in enumerate(sources):
        source_id = source["id"]

        # Filter by date window
        date_hint = source.get("date_hint")
        is_baseline = source.get("baseline", False)
        if date_hint and since and not is_baseline:
            if date_hint < since:
                print(f"  [{i+1}/{len(sources)}] SKIP {source_id} (before window: {date_hint} < {since})")
                results.append({"source_id": source_id, "status": "skipped_before_window"})
                continue
        if date_hint and until:
            if date_hint > until:
                print(f"  [{i+1}/{len(sources)}] SKIP {source_id} (after window: {date_hint} > {until})")
                results.append({"source_id": source_id, "status": "skipped_after_window"})
                continue

        # Rate limit
        url = source["url"]
        domain = url.split("/")[2] if "/" in url else ""
        if not dry_run and last_domain and domain == last_domain:
            time.sleep(RATE_LIMIT_S)
        last_domain = domain

        print(f"  [{i+1}/{len(sources)}] {'DRY ' if dry_run else ''}FETCH {source_id}")
        result = fetch_source(source, today, dry_run=dry_run)
        results.append(result)

        if result["status"] == "ok":
            print(f"    OK — {result.get('sha256_raw', '')[:12]}...")
        elif result["status"] == "error":
            print(f"    ERROR — {result.get('error')}")
        elif result["status"] == "dry_run_ok":
            print(f"    DRY RUN OK")

    return results
