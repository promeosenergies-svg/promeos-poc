"""
PROMEOS KB - Promote Item CLI
Move KB items from drafts/ -> items/ with confidence upgrade and validation.

Usage:
    python backend/scripts/kb_promote_item.py <item_file.yaml>
    python backend/scripts/kb_promote_item.py <item_file.yaml> --confidence medium
    python backend/scripts/kb_promote_item.py --batch docs/kb/drafts/usages/

Rules:
    - Draft items have status=draft, confidence=low
    - Promoted items get status=validated, confidence>=medium
    - Validation checks are run before promotion
    - File is moved from drafts/ to items/ (same subdomain folder)
    - If validation fails, promotion is REFUSED
"""

import sys
import shutil
import yaml
from pathlib import Path
from datetime import date

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).parent.parent.parent

ITEMS_DIR = PROJECT_ROOT / "docs" / "kb" / "items"
DRAFTS_DIR = PROJECT_ROOT / "docs" / "kb" / "drafts"

VALID_STATUSES = {"draft", "validated", "deprecated"}
VALID_CONFIDENCES = {"high", "medium", "low"}
REQUIRED_FIELDS = ["id", "type", "domain", "title", "summary", "tags", "sources", "updated_at", "confidence"]


def load_taxonomy():
    """Load taxonomy for validation"""
    taxonomy_path = PROJECT_ROOT / "docs" / "kb" / "_meta" / "taxonomy.yaml"
    if not taxonomy_path.exists():
        print(f"[WARN] Taxonomy not found at {taxonomy_path}, skipping tag validation")
        return None
    with open(taxonomy_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_for_promotion(item: dict, taxonomy: dict = None) -> list:
    """
    Validate item is ready for promotion to validated status.
    Returns list of errors (empty = valid).

    HARD RULES:
    - validated items MUST have confidence >= medium
    - validated items MUST have non-empty sources
    - validated items MUST have all required fields
    - validated items MUST have tags with at least 1 category
    """
    errors = []

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in item or item[field] is None:
            errors.append(f"Missing required field: {field}")

    # Confidence check: validated items cannot have confidence=low
    confidence = item.get("confidence", "low")
    if confidence == "low":
        errors.append("Cannot promote to validated with confidence=low (must be medium or high)")

    # Sources must be non-empty
    sources = item.get("sources", [])
    if not sources:
        errors.append("sources[] must not be empty for validated items")
    else:
        for i, src in enumerate(sources):
            if not src.get("doc_id") and not src.get("label"):
                errors.append(f"sources[{i}] must have at least doc_id or label")

    # Tags must have at least 1 category with values
    tags = item.get("tags", {})
    has_tags = False
    for category, values in tags.items():
        if values and (isinstance(values, list) and len(values) > 0):
            has_tags = True
            break
    if not has_tags:
        errors.append("tags must have at least one category with values")

    # Taxonomy validation (if available)
    if taxonomy:
        if item.get("type") not in taxonomy.get("types", []):
            errors.append(f"Invalid type '{item.get('type')}' (not in taxonomy)")
        if item.get("domain") not in taxonomy.get("domains", []):
            errors.append(f"Invalid domain '{item.get('domain')}' (not in taxonomy)")
        if confidence not in taxonomy.get("confidence", []):
            errors.append(f"Invalid confidence '{confidence}' (not in taxonomy)")

        # Validate individual tag values
        for category in ["energy", "segment", "asset", "reg", "granularity"]:
            if category in tags:
                values = tags[category] if isinstance(tags[category], list) else [tags[category]]
                for val in values:
                    if val and val not in taxonomy.get(category, []):
                        errors.append(f"Invalid tag {category}='{val}' (not in taxonomy)")

    return errors


def promote_item(yaml_path: Path, target_confidence: str = None, dry_run: bool = False) -> bool:
    """
    Promote a single KB item from draft to validated.
    Returns True if successful.
    """
    if not yaml_path.exists():
        print(f"[ERROR] File not found: {yaml_path}")
        return False

    # Load YAML
    with open(yaml_path, "r", encoding="utf-8") as f:
        item = yaml.safe_load(f)

    item_id = item.get("id", yaml_path.stem)
    current_status = item.get("status", "draft")
    current_confidence = item.get("confidence", "low")

    print(f"\n--- Promoting {item_id} ---")
    print(f"  Current: status={current_status}, confidence={current_confidence}")

    # If already validated, skip
    if current_status == "validated":
        print(f"  [SKIP] Already validated")
        return True

    # Upgrade confidence
    new_confidence = target_confidence or ("medium" if current_confidence == "low" else current_confidence)
    item["confidence"] = new_confidence
    item["status"] = "validated"
    item["updated_at"] = str(date.today())

    print(f"  Target:  status=validated, confidence={new_confidence}")

    # Validate
    taxonomy = load_taxonomy()
    errors = validate_for_promotion(item, taxonomy)

    if errors:
        print(f"  [REFUSED] Validation failed:")
        for err in errors:
            print(f"    - {err}")
        return False

    if dry_run:
        print(f"  [DRY RUN] Would promote {item_id}")
        return True

    # Determine target path
    domain = item.get("domain", "usages")
    target_dir = ITEMS_DIR / domain
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / yaml_path.name

    # Write updated YAML to items/
    with open(target_path, "w", encoding="utf-8") as f:
        yaml.dump(item, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # Remove from drafts/ if it was there
    if str(DRAFTS_DIR) in str(yaml_path.resolve()):
        yaml_path.unlink()
        print(f"  [MOVED] {yaml_path.name} -> items/{domain}/")
    else:
        print(f"  [SAVED] items/{domain}/{yaml_path.name}")

    print(f"  [OK] {item_id} promoted to validated (confidence={new_confidence})")
    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Promote KB items from draft to validated")
    parser.add_argument("path", help="YAML file or directory to promote")
    parser.add_argument(
        "--confidence",
        choices=["medium", "high"],
        default=None,
        help="Target confidence level (default: upgrade low->medium)",
    )
    parser.add_argument("--batch", action="store_true", help="Promote all YAML files in directory")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, don't move files")
    args = parser.parse_args()

    target = Path(args.path)

    if target.is_dir() or args.batch:
        # Batch mode
        if not target.is_dir():
            print(f"[ERROR] {target} is not a directory")
            sys.exit(1)

        yaml_files = list(target.glob("**/*.yaml"))
        print(f"[BATCH] Found {len(yaml_files)} YAML files in {target}")

        success = 0
        failed = 0
        skipped = 0

        for yf in sorted(yaml_files):
            result = promote_item(yf, target_confidence=args.confidence, dry_run=args.dry_run)
            if result:
                success += 1
            else:
                # Check if it was a skip (already validated)
                with open(yf, "r", encoding="utf-8") as f:
                    item = yaml.safe_load(f)
                if item.get("status") == "validated":
                    skipped += 1
                else:
                    failed += 1

        print(f"\n{'=' * 60}")
        print(f"Batch promotion complete:")
        print(f"  [OK]      {success} promoted")
        print(f"  [SKIP]    {skipped} already validated")
        print(f"  [REFUSED] {failed} failed validation")
        print(f"{'=' * 60}")

        if failed > 0:
            sys.exit(1)
    else:
        # Single file mode
        if not target.exists():
            print(f"[ERROR] File not found: {target}")
            sys.exit(1)

        result = promote_item(target, target_confidence=args.confidence, dry_run=args.dry_run)
        sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
