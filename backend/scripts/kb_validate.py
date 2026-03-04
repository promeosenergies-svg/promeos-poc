"""
PROMEOS KB - Validation CLI
Validate all YAML items against taxonomy and schema.
Includes lifecycle coherence checks (status vs confidence vs folder).

Usage:
    python backend/scripts/kb_validate.py
    python backend/scripts/kb_validate.py --strict
    python backend/scripts/kb_validate.py --include-drafts
    python backend/scripts/kb_validate.py --strict --include-drafts
"""

import sys
import yaml
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_taxonomy():
    """Load taxonomy"""
    taxonomy_path = Path("docs/kb/_meta/taxonomy.yaml")
    with open(taxonomy_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_item(item_path: Path, taxonomy: dict, strict: bool = False) -> list:
    """
    Validate single KB item, return list of errors.

    Lifecycle coherence checks (always active):
    - Validated items MUST have confidence >= medium
    - Validated items MUST have non-empty sources with doc_id or label
    - Items in items/ folder MUST have status=validated (strict mode)
    - Items in drafts/ folder MUST have status=draft (strict mode)
    """
    errors = []

    try:
        with open(item_path, "r", encoding="utf-8") as f:
            item = yaml.safe_load(f)

        # Required fields
        required = ["id", "type", "domain", "title", "summary", "tags", "sources", "updated_at", "confidence"]
        for field in required:
            if field not in item:
                errors.append(f"Missing required field: {field}")

        # Validate type
        if item.get("type") not in taxonomy["types"]:
            errors.append(f"Invalid type '{item.get('type')}' (allowed: {taxonomy['types']})")

        # Validate domain
        if item.get("domain") not in taxonomy["domains"]:
            errors.append(f"Invalid domain '{item.get('domain')}' (allowed: {taxonomy['domains']})")

        # Validate confidence
        confidence = item.get("confidence")
        if confidence not in taxonomy["confidence"]:
            errors.append(f"Invalid confidence '{confidence}' (allowed: {taxonomy['confidence']})")

        # Validate status field
        status = item.get("status", "validated")
        if status not in ("draft", "validated", "deprecated"):
            errors.append(f"Invalid status '{status}' (allowed: draft, validated, deprecated)")

        # Validate tags
        tags = item.get("tags", {})
        for category in ["energy", "segment", "asset", "reg", "granularity"]:
            if category in tags:
                values = tags[category] if isinstance(tags[category], list) else [tags[category]]
                for val in values:
                    if val and val not in taxonomy.get(category, []):
                        errors.append(f"Invalid tag {category}='{val}' (not in taxonomy)")

        # Validate sources not empty
        if not item.get("sources"):
            errors.append("sources[] must not be empty")

        # --- LIFECYCLE COHERENCE CHECKS ---

        # HARD RULE: validated items MUST have confidence >= medium
        if status == "validated" and confidence == "low":
            errors.append("LIFECYCLE: validated item cannot have confidence=low (must be medium or high)")

        # HARD RULE: validated items must have identifiable source provenance
        if status == "validated" and item.get("sources"):
            for i, src in enumerate(item["sources"]):
                if not src.get("doc_id") and not src.get("label"):
                    errors.append(f"LIFECYCLE: sources[{i}] must have doc_id or label for validated items")

        # Folder coherence (strict mode)
        if strict:
            path_str = str(item_path.resolve())
            if "/items/" in path_str or "\\items\\" in path_str:
                if status != "validated":
                    errors.append(f"LIFECYCLE: item in items/ folder must have status=validated (got {status})")
            elif "/drafts/" in path_str or "\\drafts\\" in path_str:
                if status != "draft":
                    errors.append(f"LIFECYCLE: item in drafts/ folder should have status=draft (got {status})")

            # Tags must have at least 1 category with values for validated items
            if status == "validated":
                has_tags = any(values and (isinstance(values, list) and len(values) > 0) for values in tags.values())
                if not has_tags:
                    errors.append("LIFECYCLE: validated item must have at least one tag category with values")

    except yaml.YAMLError as e:
        errors.append(f"YAML parse error: {e}")
    except Exception as e:
        errors.append(f"Unexpected error: {e}")

    return errors


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate KB YAML items")
    parser.add_argument(
        "--strict", action="store_true", help="Enable strict mode: lifecycle folder coherence + exit on first error"
    )
    parser.add_argument("--include-drafts", action="store_true", help="Also validate files in docs/kb/drafts/")
    args = parser.parse_args()

    # Load taxonomy
    taxonomy = load_taxonomy()
    print(f"[OK] Loaded taxonomy (v{taxonomy.get('version')})")

    # Find all YAML files
    items_dir = Path("docs/kb/items")
    yaml_files = list(items_dir.glob("**/*.yaml"))

    if args.include_drafts:
        drafts_dir = Path("docs/kb/drafts")
        if drafts_dir.exists():
            draft_files = list(drafts_dir.glob("**/*.yaml"))
            yaml_files.extend(draft_files)
            print(f"[INFO] Including {len(draft_files)} draft files")

    print(f"[INFO] Found {len(yaml_files)} YAML files to validate")

    # Validate
    all_errors = {}
    seen_ids = set()
    validated_count = 0
    draft_count = 0

    for yaml_file in yaml_files:
        try:
            rel_path = yaml_file.relative_to(Path.cwd())
        except ValueError:
            rel_path = yaml_file

        errors = validate_item(yaml_file, taxonomy, strict=args.strict)

        # Track status distribution
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                item = yaml.safe_load(f)
                item_status = item.get("status", "validated")
                if item_status == "validated":
                    validated_count += 1
                elif item_status == "draft":
                    draft_count += 1

                # Check ID uniqueness
                item_id = item.get("id")
                if item_id in seen_ids:
                    errors.append(f"Duplicate ID '{item_id}'")
                seen_ids.add(item_id)
        except Exception:
            pass

        if errors:
            all_errors[str(rel_path)] = errors
            if args.strict:
                print(f"[FAIL] {rel_path}")
                for err in errors:
                    print(f"   - {err}")
                sys.exit(1)

    # Report
    print(f"\n{'=' * 60}")
    print(f"KB Validation Report:")
    print(f"  Total files:     {len(yaml_files)}")
    print(f"  Validated items: {validated_count}")
    print(f"  Draft items:     {draft_count}")
    print(f"  Unique IDs:      {len(seen_ids)}")

    if all_errors:
        print(f"\n[FAIL] Validation failed ({len(all_errors)} files with errors):\n")
        for file, errors in all_errors.items():
            print(f"  {file}:")
            for err in errors:
                print(f"    - {err}")
        print(f"{'=' * 60}")
        sys.exit(1)
    else:
        print(f"\n[OK] All {len(yaml_files)} files valid!")
        print(f"{'=' * 60}")
        sys.exit(0)


if __name__ == "__main__":
    main()
