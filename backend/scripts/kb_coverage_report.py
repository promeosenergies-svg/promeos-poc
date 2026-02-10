"""
PROMEOS KB - Coverage Report
Compares actual KB items against required coverage matrix.
Identifies gaps ("angles morts") and generates a report.

Usage:
    python backend/scripts/kb_coverage_report.py
    python backend/scripts/kb_coverage_report.py --output docs/kb/_meta/coverage_report.md
    python backend/scripts/kb_coverage_report.py --include-drafts
"""
import sys
import csv
import yaml
from pathlib import Path
from collections import defaultdict
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).parent.parent.parent

ITEMS_DIR = PROJECT_ROOT / "docs" / "kb" / "items"
DRAFTS_DIR = PROJECT_ROOT / "docs" / "kb" / "drafts"
COVERAGE_CSV = PROJECT_ROOT / "docs" / "kb" / "_meta" / "coverage.csv"


def load_coverage_matrix():
    """Load required coverage from CSV"""
    requirements = []
    with open(COVERAGE_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            requirements.append({
                "domain": row["domain"],
                "segment": row["segment"],
                "type": row["type"],
                "required_min": int(row["required_min_items"]),
                "description": row["description"]
            })
    return requirements


def load_kb_items(include_drafts=False):
    """Load all KB items and index by domain/segment/type"""
    items = []

    # Items (validated)
    for yaml_file in ITEMS_DIR.glob("**/*.yaml"):
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                item = yaml.safe_load(f)
            item["_source"] = "items"
            item["_file"] = str(yaml_file.relative_to(PROJECT_ROOT))
            items.append(item)
        except Exception as e:
            print(f"[WARN] Cannot load {yaml_file.name}: {e}")

    # Drafts
    if include_drafts and DRAFTS_DIR.exists():
        for yaml_file in DRAFTS_DIR.glob("**/*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    item = yaml.safe_load(f)
                item["_source"] = "drafts"
                item["_file"] = str(yaml_file.relative_to(PROJECT_ROOT))
                items.append(item)
            except Exception as e:
                print(f"[WARN] Cannot load draft {yaml_file.name}: {e}")

    return items


def match_items_to_requirements(items, requirements):
    """Match KB items against coverage requirements"""
    results = []

    for req in requirements:
        matching = []
        for item in items:
            # Match domain
            if item.get("domain") != req["domain"]:
                continue
            # Match type
            if item.get("type") != req["type"]:
                continue
            # Match segment (item must have this segment in tags)
            tags = item.get("tags", {})
            segments = tags.get("segment", [])
            if isinstance(segments, str):
                segments = [segments]
            if req["segment"] not in segments:
                continue

            matching.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "confidence": item.get("confidence"),
                "status": item.get("status", "validated"),
                "source": item.get("_source")
            })

        # Coverage status
        validated_count = sum(1 for m in matching if m["status"] == "validated")
        draft_count = sum(1 for m in matching if m["status"] == "draft")
        total = len(matching)
        required = req["required_min"]

        if validated_count >= required:
            coverage_status = "COVERED"
        elif total >= required:
            coverage_status = "PARTIAL"  # Has items but some are drafts
        elif total > 0:
            coverage_status = "INSUFFICIENT"
        else:
            coverage_status = "MISSING"

        results.append({
            **req,
            "matching_items": matching,
            "validated_count": validated_count,
            "draft_count": draft_count,
            "total_count": total,
            "coverage_status": coverage_status
        })

    return results


def generate_report(results, include_drafts=False):
    """Generate markdown coverage report"""
    lines = []
    lines.append(f"# KB Coverage Report")
    lines.append(f"Generated: {date.today()}")
    lines.append(f"Include drafts: {include_drafts}")
    lines.append("")

    # Summary
    total_req = len(results)
    covered = sum(1 for r in results if r["coverage_status"] == "COVERED")
    partial = sum(1 for r in results if r["coverage_status"] == "PARTIAL")
    insufficient = sum(1 for r in results if r["coverage_status"] == "INSUFFICIENT")
    missing = sum(1 for r in results if r["coverage_status"] == "MISSING")

    coverage_pct = (covered / total_req * 100) if total_req > 0 else 0

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total requirements | {total_req} |")
    lines.append(f"| COVERED | {covered} |")
    lines.append(f"| PARTIAL (has drafts) | {partial} |")
    lines.append(f"| INSUFFICIENT | {insufficient} |")
    lines.append(f"| MISSING (angle mort) | {missing} |")
    lines.append(f"| Coverage % | {coverage_pct:.0f}% |")
    lines.append("")

    # Detail by domain
    domains = sorted(set(r["domain"] for r in results))
    for domain in domains:
        lines.append(f"## {domain.upper()}")
        lines.append("")
        lines.append(f"| Segment | Type | Required | Validated | Drafts | Status | Description |")
        lines.append(f"|---------|------|----------|-----------|--------|--------|-------------|")

        domain_results = [r for r in results if r["domain"] == domain]
        for r in domain_results:
            status_badge = {
                "COVERED": "[OK]",
                "PARTIAL": "[PARTIAL]",
                "INSUFFICIENT": "[LOW]",
                "MISSING": "[MISSING]"
            }.get(r["coverage_status"], "?")

            lines.append(
                f"| {r['segment']} | {r['type']} | {r['required_min']} "
                f"| {r['validated_count']} | {r['draft_count']} "
                f"| {status_badge} | {r['description']} |"
            )

        lines.append("")

    # Missing items detail
    missing_results = [r for r in results if r["coverage_status"] in ("MISSING", "INSUFFICIENT")]
    if missing_results:
        lines.append("## Angles Morts (Gaps)")
        lines.append("")
        for r in missing_results:
            gap = r["required_min"] - r["validated_count"]
            lines.append(f"- **{r['domain']}/{r['segment']}/{r['type']}**: "
                        f"need {gap} more validated items ({r['description']})")
        lines.append("")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="KB coverage report")
    parser.add_argument("--output", help="Output markdown file path")
    parser.add_argument("--include-drafts", action="store_true",
                        help="Include draft items in coverage count")
    args = parser.parse_args()

    if not COVERAGE_CSV.exists():
        print(f"[ERROR] Coverage matrix not found: {COVERAGE_CSV}")
        sys.exit(1)

    # Load data
    requirements = load_coverage_matrix()
    items = load_kb_items(include_drafts=args.include_drafts)

    print(f"[INFO] Loaded {len(requirements)} requirements, {len(items)} KB items")

    # Analyze
    results = match_items_to_requirements(items, requirements)

    # Generate report
    report = generate_report(results, include_drafts=args.include_drafts)

    # Output
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"[OK] Report written to {output_path}")
    else:
        print(report)

    # Exit code based on coverage
    covered = sum(1 for r in results if r["coverage_status"] == "COVERED")
    if covered < len(results):
        missing = sum(1 for r in results if r["coverage_status"] == "MISSING")
        print(f"\n[WARN] {missing} missing, {len(results) - covered} not fully covered")
        sys.exit(0)  # Non-blocking — just a warning
    else:
        print(f"\n[OK] Full coverage!")
        sys.exit(0)


if __name__ == "__main__":
    main()
