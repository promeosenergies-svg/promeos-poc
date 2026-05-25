"""
PROMEOS KB - Add `naf: [multi]` baseline tag on items/

Phase 1 NAF activation : pose une valeur de taxonomie sur tous les items/
qui ont actuellement un tag `naf` absent ou vide. La valeur `multi` signifie
"applies to multiple NAF codes" (taxonomy.yaml) et reflète honnêtement le
fait que la majorité des règles/connaissances PROMEOS s'appliquent par
segment×asset×reg et non par code NAF spécifique.

Phase 2 (à venir) : refinement manuel sur les items où une NAF spécifique
fait sens (ex. archetypes sectoriels), via croisement avec `naf_to_usage.csv`
le moment venu.

Audit 2026-05-20 : NAF à 0% partout (items + drafts).

Usage :
    python backend/scripts/kb_tag_naf_multi.py             # dry-run
    python backend/scripts/kb_tag_naf_multi.py --apply
"""

import argparse
import re
import sys
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
ITEMS_DIR = PROJECT_ROOT / "docs" / "kb" / "items"


def needs_fix(item: dict) -> bool:
    tags = item.get("tags") or {}
    return not tags.get("naf")  # absent OR empty list


def find_tags_block_end(lines: list[str]) -> int | None:
    """Return the line index immediately AFTER the last line of `tags:` block."""
    tags_start = None
    for i, line in enumerate(lines):
        if re.match(r"^tags:\s*$", line):
            tags_start = i
            break
    if tags_start is None:
        return None
    end = len(lines)
    for j in range(tags_start + 1, len(lines)):
        line = lines[j]
        if not line.strip():
            continue
        if not line.startswith(" "):
            end = j
            break
        end = j + 1
    return end


def patch_file(path: Path, apply: bool) -> bool:
    raw = path.read_text(encoding="utf-8")
    item = yaml.safe_load(raw)
    if not isinstance(item, dict) or not needs_fix(item):
        return False

    lines = raw.splitlines(keepends=True)

    # Case A : `naf:` present but empty → replace `naf: []` or `naf:` (no items) by `naf:\n    - multi`
    naf_line_idx = None
    for i, line in enumerate(lines):
        if re.match(r"^  naf:\s*(\[\s*\])?\s*$", line):
            naf_line_idx = i
            break

    if naf_line_idx is not None:
        lines[naf_line_idx] = "  naf:\n"
        lines.insert(naf_line_idx + 1, "    - multi\n")
    else:
        # Case B : no `naf:` key at all → append at end of tags: block
        end = find_tags_block_end(lines)
        if end is None:
            return False
        # Insert `  naf:\n    - multi\n` right before the next top-level field
        # but after the last non-empty line of the tags block
        insert_at = end
        while insert_at > 0 and not lines[insert_at - 1].strip():
            insert_at -= 1
        lines.insert(insert_at, "  naf:\n")
        lines.insert(insert_at + 1, "    - multi\n")

    if apply:
        path.write_text("".join(lines), encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    files = sorted(ITEMS_DIR.glob("**/*.yaml"))
    print(f"[INFO] Scanning {len(files)} items/ files")

    patched = 0
    for p in files:
        if patch_file(p, args.apply):
            patched += 1
            tag = "PATCH" if args.apply else "WOULD-PATCH"
            print(f"  {tag:11s} {p.relative_to(PROJECT_ROOT)}")

    mode = "applied" if args.apply else "dry-run"
    print(f"\n[REPORT] {mode}: {patched}/{len(files)} files tagged naf=[multi]")
    if not args.apply:
        print("[DRY-RUN] Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
