"""
PROMEOS KB - Fill missing excerpt_short on items/ sources
Best-effort placeholder generator pour les `sources[*].excerpt_short` manquants.

Stratégie : si la source n'a pas d'excerpt_short, on inscrit la première phrase
non triviale du `summary` de l'item (tronquée à ~180 caractères) avec le
préfixe `[auto-fill]`. Marqueur visible pour révision humaine ultérieure
(remplacer par une citation littérale de la source quand disponible).

Audit 2026-05-20 : 17/39 items avaient au moins une source sans excerpt_short.

Usage :
    python backend/scripts/kb_fill_excerpts.py             # dry-run
    python backend/scripts/kb_fill_excerpts.py --apply
"""

import argparse
import re
import sys
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
ITEMS_DIR = PROJECT_ROOT / "docs" / "kb" / "items"

EXCERPT_MAX = 180
AUTOFILL_PREFIX = "[auto-fill] "


def build_excerpt(item: dict) -> str:
    """Derive excerpt from the item's summary (first sentence, ~180 chars)."""
    summary = (item.get("summary") or "").strip().replace("\n", " ")
    # First sentence (up to . ! ? followed by space, fallback = whole summary)
    m = re.search(r"^(.+?[\.!?])(\s|$)", summary)
    text = m.group(1) if m else summary
    if len(text) > EXCERPT_MAX:
        text = text[: EXCERPT_MAX - 1].rstrip() + "…"
    text = text.replace('"', "'").replace("\\", "/")
    return AUTOFILL_PREFIX + text


def find_source_block_ranges(lines: list[str]) -> tuple[int, list[tuple[int, int]]] | None:
    """
    Locate the `sources:` block and return (sources_line_idx, [(start, end), ...])
    where each (start, end) frames one source list item (`  - doc_id:` block).
    """
    sources_line = None
    for i, line in enumerate(lines):
        if re.match(r"^sources:\s*$", line):
            sources_line = i
            break
    if sources_line is None:
        return None

    starts: list[int] = []
    section_end = len(lines)
    for j in range(sources_line + 1, len(lines)):
        stripped = lines[j].rstrip("\n")
        if not stripped.strip():
            continue
        # New top-level field (col 0 non-space) → end of sources block
        if not stripped.startswith(" "):
            section_end = j
            break
        if stripped.startswith("  - "):
            starts.append(j)

    if not starts:
        return None

    ranges: list[tuple[int, int]] = []
    for k, s in enumerate(starts):
        e = starts[k + 1] if k + 1 < len(starts) else section_end
        ranges.append((s, e))
    return sources_line, ranges


def patch_file(path: Path, apply: bool) -> int:
    raw = path.read_text(encoding="utf-8")
    item = yaml.safe_load(raw)
    if not isinstance(item, dict):
        return 0
    sources = item.get("sources") or []
    missing_idx = [i for i, s in enumerate(sources) if not s.get("excerpt_short")]
    if not missing_idx:
        return 0

    lines = raw.splitlines(keepends=True)
    info = find_source_block_ranges(lines)
    if info is None:
        return 0
    _, ranges = info

    excerpt = build_excerpt(item)
    insert_line = f'    excerpt_short: "{excerpt}"\n'

    # Insert from end to start to preserve indices
    for idx in sorted(missing_idx, reverse=True):
        start, end = ranges[idx]
        # Skip trailing blank lines inside the block
        insert_at = end
        while insert_at > start + 1 and not lines[insert_at - 1].strip():
            insert_at -= 1
        lines.insert(insert_at, insert_line)

    if apply:
        path.write_text("".join(lines), encoding="utf-8")
    return len(missing_idx)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    files = sorted(ITEMS_DIR.glob("**/*.yaml"))
    print(f"[INFO] Scanning {len(files)} items/ files")

    total = 0
    touched_files = 0
    for p in files:
        n = patch_file(p, args.apply)
        if n:
            total += n
            touched_files += 1
            tag = "PATCH" if args.apply else "WOULD-PATCH"
            print(f"  {tag:11s} +{n} {p.relative_to(PROJECT_ROOT)}")

    mode = "applied" if args.apply else "dry-run"
    print(f"\n[REPORT] {mode}: {total} excerpts added across {touched_files} files")
    if not args.apply:
        print("[DRY-RUN] Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
