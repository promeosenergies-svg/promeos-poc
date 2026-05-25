"""
PROMEOS KB - Fix Lifecycle Status on items/
Adds or corrects `status: validated` on YAML items living in docs/kb/items/.

Background: 74 % of items/ lacked the `status` field (audit 2026-05-20).
README rule: "Items in items/ folder MUST have status=validated".

Usage:
    python backend/scripts/kb_fix_status.py             # dry-run
    python backend/scripts/kb_fix_status.py --apply     # write changes
"""

import argparse
import sys
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
ITEMS_DIR = PROJECT_ROOT / "docs" / "kb" / "items"


def needs_fix(item: dict) -> bool:
    """True if `status` is missing or differs from 'validated'."""
    return item.get("status") != "validated"


def insert_status_line(lines: list[str]) -> tuple[list[str], str]:
    """
    Insert or replace a top-level `status: validated` line.
    Anchors AFTER the top-level `confidence:` line (lifecycle cluster).
    Returns (new_lines, action) where action is 'added' | 'replaced' | 'skipped'.
    """
    # Replace if status already exists at column 0
    for i, line in enumerate(lines):
        if line.startswith("status:"):
            new = line.split(":", 1)[0] + ': "validated"\n'
            if line == new:
                return lines, "skipped"
            lines[i] = new
            return lines, "replaced"

    # Else insert after first top-level `confidence:` line
    for i, line in enumerate(lines):
        if line.startswith("confidence:"):
            lines.insert(i + 1, 'status: "validated"\n')
            return lines, "added"

    # Fallback: append before final newline
    insert_at = len(lines)
    lines.insert(insert_at, '\nstatus: "validated"\n')
    return lines, "added"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    args = parser.parse_args()

    yaml_files = sorted(ITEMS_DIR.glob("**/*.yaml"))
    print(f"[INFO] Scanning {len(yaml_files)} items/ files")

    fixes: list[tuple[Path, str]] = []
    errors: list[tuple[Path, str]] = []

    for path in yaml_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            item = yaml.safe_load(raw)
        except Exception as e:
            errors.append((path, f"parse error: {e}"))
            continue

        if not isinstance(item, dict):
            errors.append((path, "not a dict at root"))
            continue

        if not needs_fix(item):
            continue

        lines = raw.splitlines(keepends=True)
        new_lines, action = insert_status_line(lines)
        if action == "skipped":
            continue
        fixes.append((path, action))

        if args.apply:
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

    rel = lambda p: p.relative_to(PROJECT_ROOT)
    print(f"\n[REPORT] {len(fixes)} files need fix:")
    for path, action in fixes:
        print(f"  {action:9s} {rel(path)}")
    if errors:
        print(f"\n[ERRORS] {len(errors)}:")
        for path, msg in errors:
            print(f"  {rel(path)} :: {msg}")

    if not args.apply:
        print("\n[DRY-RUN] Re-run with --apply to write changes.")
    else:
        print(f"\n[OK] {len(fixes)} files patched.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
