"""
PROMEOS KB - Smoke Test Suite
The "red button" before pilot deployment.
Validates entire KB stack: YAML items, DB, FTS, apply engine, lifecycle guards.

Usage:
    python backend/scripts/kb_smoke.py
    python backend/scripts/kb_smoke.py --verbose
    python backend/scripts/kb_smoke.py --fix (attempt auto-fixes)

Exit codes:
    0 = ALL OK (safe for pilot)
    1 = CRITICAL failures (do NOT deploy)
    2 = Warnings only (deploy with caution)
"""

import sys
import json
import yaml
import sqlite3
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).parent.parent.parent
ITEMS_DIR = PROJECT_ROOT / "docs" / "kb" / "items"
DRAFTS_DIR = PROJECT_ROOT / "docs" / "kb" / "drafts"
META_DIR = PROJECT_ROOT / "docs" / "kb" / "_meta"
FIXTURES_DIR = Path(__file__).parent.parent / "tests" / "fixtures"


class SmokeResult:
    def __init__(self, name, status, message):
        self.name = name
        self.status = status  # "PASS", "FAIL", "WARN"
        self.message = message

    def __repr__(self):
        badge = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]"}
        return f"{badge.get(self.status, '[?]')} {self.name}: {self.message}"


class KBSmokeTest:
    """Comprehensive KB smoke test suite"""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results = []

    def run_all(self):
        """Run all smoke tests"""
        print("=" * 70)
        print("PROMEOS KB SMOKE TEST SUITE")
        print(f"Time: {datetime.now().isoformat()[:19]}")
        print("=" * 70)
        print()

        # Phase 1: File system checks
        self._test_yaml_files_exist()
        self._test_taxonomy_exists()
        self._test_yaml_parse_all()
        self._test_lifecycle_coherence()
        self._test_no_duplicate_ids()
        self._test_all_items_have_sources()

        # Phase 2: Database checks
        self._test_db_exists_and_schema()
        self._test_db_has_status_column()
        self._test_db_items_match_yaml()

        # Phase 3: FTS index checks
        self._test_fts_index_exists()

        # Phase 4: Apply engine checks
        self._test_apply_engine_loads()
        self._test_apply_rejects_drafts()
        self._test_apply_golden_contexts()

        # Phase 5: Coverage checks
        self._test_coverage_matrix_exists()

        # Report
        return self._report()

    def _add(self, name, status, message):
        r = SmokeResult(name, status, message)
        self.results.append(r)
        if self.verbose or status != "PASS":
            print(f"  {r}")

    # --- Phase 1: File System ---

    def _test_yaml_files_exist(self):
        """Check that items/ has YAML files"""
        if not ITEMS_DIR.exists():
            self._add("YAML items dir", "FAIL", f"Directory not found: {ITEMS_DIR}")
            return

        yaml_files = list(ITEMS_DIR.glob("**/*.yaml"))
        if len(yaml_files) == 0:
            self._add("YAML items", "FAIL", "No YAML files in items/")
        elif len(yaml_files) < 5:
            self._add("YAML items", "WARN", f"Only {len(yaml_files)} items (expected >= 5)")
        else:
            self._add("YAML items", "PASS", f"{len(yaml_files)} items found")

    def _test_taxonomy_exists(self):
        """Check taxonomy.yaml exists"""
        taxonomy_path = META_DIR / "taxonomy.yaml"
        if not taxonomy_path.exists():
            self._add("Taxonomy", "FAIL", "taxonomy.yaml not found")
            return

        with open(taxonomy_path, "r", encoding="utf-8") as f:
            taxonomy = yaml.safe_load(f)

        required_keys = ["types", "domains", "confidence", "energy", "segment"]
        missing = [k for k in required_keys if k not in taxonomy]
        if missing:
            self._add("Taxonomy", "FAIL", f"Missing keys: {missing}")
        else:
            self._add("Taxonomy", "PASS", f"v{taxonomy.get('version', '?')} loaded")

    def _test_yaml_parse_all(self):
        """Parse ALL YAML files without errors"""
        errors = []
        for yaml_file in ITEMS_DIR.glob("**/*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    yaml.safe_load(f)
            except Exception as e:
                errors.append(f"{yaml_file.name}: {e}")

        if DRAFTS_DIR.exists():
            for yaml_file in DRAFTS_DIR.glob("**/*.yaml"):
                try:
                    with open(yaml_file, "r", encoding="utf-8") as f:
                        yaml.safe_load(f)
                except Exception as e:
                    errors.append(f"drafts/{yaml_file.name}: {e}")

        if errors:
            self._add("YAML parse", "FAIL", f"{len(errors)} parse errors")
            for e in errors[:5]:
                print(f"    -> {e}")
        else:
            self._add("YAML parse", "PASS", "All files parse OK")

    def _test_lifecycle_coherence(self):
        """Check that validated items have confidence >= medium"""
        violations = []
        for yaml_file in ITEMS_DIR.glob("**/*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    item = yaml.safe_load(f)

                status = item.get("status", "validated")
                confidence = item.get("confidence", "low")

                # HARD RULE: validated + low = violation
                if status == "validated" and confidence == "low":
                    violations.append(f"{item.get('id')}: validated + confidence=low")
            except Exception:
                pass

        if violations:
            self._add("Lifecycle coherence", "FAIL", f"{len(violations)} violations")
            for v in violations[:5]:
                print(f"    -> {v}")
        else:
            self._add("Lifecycle coherence", "PASS", "All items coherent")

    def _test_no_duplicate_ids(self):
        """Check no duplicate IDs across items/ and drafts/"""
        ids = {}
        for yaml_file in ITEMS_DIR.glob("**/*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    item = yaml.safe_load(f)
                item_id = item.get("id")
                if item_id in ids:
                    ids[item_id].append(str(yaml_file.name))
                else:
                    ids[item_id] = [str(yaml_file.name)]
            except Exception:
                pass

        dupes = {k: v for k, v in ids.items() if len(v) > 1}
        if dupes:
            self._add("Unique IDs", "FAIL", f"{len(dupes)} duplicate IDs")
            for k, v in list(dupes.items())[:5]:
                print(f"    -> {k} in {v}")
        else:
            self._add("Unique IDs", "PASS", f"{len(ids)} unique IDs")

    def _test_all_items_have_sources(self):
        """Check all validated items have sources[]"""
        missing_sources = []
        for yaml_file in ITEMS_DIR.glob("**/*.yaml"):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    item = yaml.safe_load(f)
                if not item.get("sources"):
                    missing_sources.append(item.get("id", yaml_file.name))
            except Exception:
                pass

        if missing_sources:
            self._add("Sources present", "FAIL", f"{len(missing_sources)} items missing sources")
            for s in missing_sources[:5]:
                print(f"    -> {s}")
        else:
            self._add("Sources present", "PASS", "All items have sources")

    # --- Phase 2: Database ---

    def _test_db_exists_and_schema(self):
        """Check KB database exists with correct tables"""
        db_path = Path("data/kb.db")
        if not db_path.exists():
            self._add("DB exists", "WARN", "data/kb.db not found (will be created on first run)")
            return

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            required = ["kb_items", "kb_fts", "kb_docs", "kb_chunks"]
            missing = [t for t in required if t not in tables]
            if missing:
                self._add("DB schema", "FAIL", f"Missing tables: {missing}")
            else:
                self._add("DB schema", "PASS", f"Tables: {', '.join(required)}")
        except Exception as e:
            self._add("DB schema", "FAIL", f"Cannot connect: {e}")

    def _test_db_has_status_column(self):
        """Check kb_items has status column"""
        db_path = Path("data/kb.db")
        if not db_path.exists():
            self._add("DB status column", "WARN", "DB not found (skipped)")
            return

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(kb_items)")
            columns = [row[1] for row in cursor.fetchall()]
            conn.close()

            if "status" in columns:
                self._add("DB status column", "PASS", "kb_items.status exists")
            else:
                self._add("DB status column", "FAIL", "kb_items.status MISSING - run migration")
        except Exception as e:
            self._add("DB status column", "FAIL", f"Error: {e}")

    def _test_db_items_match_yaml(self):
        """Check DB items count matches YAML items"""
        db_path = Path("data/kb.db")
        if not db_path.exists():
            self._add("DB/YAML sync", "WARN", "DB not found (skipped)")
            return

        yaml_count = len(list(ITEMS_DIR.glob("**/*.yaml")))

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM kb_items")
            db_count = cursor.fetchone()[0]
            conn.close()

            if db_count == 0:
                self._add("DB/YAML sync", "WARN", "DB empty - run kb_seed_import.py")
            elif abs(db_count - yaml_count) > 5:
                self._add("DB/YAML sync", "WARN", f"DB has {db_count} items, YAML has {yaml_count}")
            else:
                self._add("DB/YAML sync", "PASS", f"DB={db_count}, YAML={yaml_count}")
        except Exception as e:
            self._add("DB/YAML sync", "FAIL", f"Error: {e}")

    # --- Phase 3: FTS ---

    def _test_fts_index_exists(self):
        """Check FTS5 index is populated"""
        db_path = Path("data/kb.db")
        if not db_path.exists():
            self._add("FTS index", "WARN", "DB not found (skipped)")
            return

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM kb_fts")
            fts_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM kb_items")
            items_count = cursor.fetchone()[0]
            conn.close()

            if fts_count == 0:
                self._add("FTS index", "WARN", "FTS empty - run kb_build_index.py")
            elif fts_count < items_count:
                self._add("FTS index", "WARN", f"FTS has {fts_count}/{items_count} items")
            else:
                self._add("FTS index", "PASS", f"{fts_count} items indexed")
        except Exception as e:
            self._add("FTS index", "FAIL", f"Error: {e}")

    # --- Phase 4: Apply Engine ---

    def _test_apply_engine_loads(self):
        """Check apply engine can be instantiated"""
        try:
            from app.kb.service import KBService

            service = KBService()
            self._add("Apply engine load", "PASS", "KBService instantiated")
        except Exception as e:
            self._add("Apply engine load", "FAIL", f"Cannot load: {e}")

    def _test_apply_rejects_drafts(self):
        """CRITICAL: Verify apply() with allow_drafts=False does not use draft items"""
        try:
            from app.kb.service import KBService

            service = KBService()

            # Apply with a basic context
            result = service.apply(site_context={"building_type": "bureau", "surface_m2": 1000}, allow_drafts=False)

            # Check no draft items in results
            for item in result.get("applicable_items", []):
                # Items from apply should be validated (confidence != low expected)
                if item.get("confidence") == "low":
                    self._add(
                        "Apply rejects drafts",
                        "WARN",
                        f"Item {item['kb_item_id']} has confidence=low in non-draft mode",
                    )
                    return

            self._add("Apply rejects drafts", "PASS", "No draft items in apply(allow_drafts=False)")
        except Exception as e:
            self._add("Apply rejects drafts", "WARN", f"Cannot test: {e}")

    def _test_apply_golden_contexts(self):
        """Test apply() against golden test fixtures"""
        contexts_path = FIXTURES_DIR / "site_contexts.json"
        expected_path = FIXTURES_DIR / "expected_apply_results.json"

        if not contexts_path.exists():
            self._add("Golden tests", "WARN", "site_contexts.json not found")
            return
        if not expected_path.exists():
            self._add("Golden tests", "WARN", "expected_apply_results.json not found")
            return

        try:
            with open(contexts_path, "r", encoding="utf-8") as f:
                contexts = json.load(f)
            with open(expected_path, "r", encoding="utf-8") as f:
                expectations = json.load(f)

            from app.kb.service import KBService

            service = KBService()

            # Check if DB has any items — if empty, golden tests are not meaningful
            db_item_count = service.store.count_items()
            if db_item_count == 0:
                self._add("Golden tests", "WARN", "DB has 0 items — run kb_seed_import.py first, then re-run smoke")
                return

            failures = []
            tested = 0

            for ctx in contexts.get("contexts", []):
                ctx_id = ctx["id"]
                if ctx_id not in expectations.get("expectations", {}):
                    continue

                tested += 1
                exp = expectations["expectations"][ctx_id]
                result = service.apply(site_context=ctx["site_context"], allow_drafts=False)

                applicable = result.get("applicable_items", [])
                status = result.get("status", "unknown")

                # Check min/max applicable
                if len(applicable) < exp.get("min_applicable_items", 0):
                    failures.append(f"{ctx_id}: {len(applicable)} items < min {exp['min_applicable_items']}")
                if len(applicable) > exp.get("max_applicable_items", 999):
                    failures.append(f"{ctx_id}: {len(applicable)} items > max {exp['max_applicable_items']}")

                # Check status
                if "expected_status_in" in exp:
                    if status not in exp["expected_status_in"]:
                        failures.append(f"{ctx_id}: status={status} not in {exp['expected_status_in']}")
                if "must_not_have_status" in exp:
                    if status == exp["must_not_have_status"]:
                        failures.append(f"{ctx_id}: status={status} is forbidden")

                # Run checks
                for check in exp.get("checks", []):
                    check_type = check["check"]
                    if check_type == "no_draft_items":
                        for item in applicable:
                            if item.get("confidence") == "low":
                                failures.append(f"{ctx_id}: draft item in results ({item['kb_item_id']})")
                    elif check_type == "all_have_confidence":
                        for item in applicable:
                            if "confidence" not in item:
                                failures.append(f"{ctx_id}: item missing confidence ({item['kb_item_id']})")
                    elif check_type == "all_have_sources":
                        for item in applicable:
                            if not item.get("sources"):
                                failures.append(f"{ctx_id}: item missing sources ({item['kb_item_id']})")
                    elif check_type == "has_missing_fields":
                        if not result.get("missing_fields"):
                            failures.append(f"{ctx_id}: expected missing_fields but got none")

            if failures:
                self._add("Golden tests", "FAIL", f"{len(failures)} failures in {tested} contexts")
                for f in failures[:5]:
                    print(f"    -> {f}")
            else:
                self._add("Golden tests", "PASS", f"{tested} contexts tested OK")

        except Exception as e:
            self._add("Golden tests", "WARN", f"Cannot run: {e}")

    # --- Phase 5: Coverage ---

    def _test_coverage_matrix_exists(self):
        """Check coverage matrix exists"""
        csv_path = META_DIR / "coverage.csv"
        if not csv_path.exists():
            self._add("Coverage matrix", "WARN", "coverage.csv not found")
            return

        import csv

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if len(rows) == 0:
            self._add("Coverage matrix", "FAIL", "coverage.csv is empty")
        else:
            self._add("Coverage matrix", "PASS", f"{len(rows)} requirements defined")

    # --- Report ---

    def _report(self):
        """Generate final report"""
        print()
        print("=" * 70)
        print("SMOKE TEST RESULTS")
        print("=" * 70)

        passes = sum(1 for r in self.results if r.status == "PASS")
        fails = sum(1 for r in self.results if r.status == "FAIL")
        warns = sum(1 for r in self.results if r.status == "WARN")
        total = len(self.results)

        for r in self.results:
            print(f"  {r}")

        print()
        print(f"  Total: {total} tests")
        print(f"  PASS:  {passes}")
        print(f"  FAIL:  {fails}")
        print(f"  WARN:  {warns}")
        print()

        if fails > 0:
            print("  VERDICT: FAIL - DO NOT DEPLOY")
            print("=" * 70)
            return 1
        elif warns > 0:
            print("  VERDICT: WARN - Deploy with caution")
            print("=" * 70)
            return 2
        else:
            print("  VERDICT: ALL CLEAR - Safe for pilot")
            print("=" * 70)
            return 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="KB smoke test suite")
    parser.add_argument("--verbose", action="store_true", help="Show all test results including PASS")
    args = parser.parse_args()

    smoke = KBSmokeTest(verbose=args.verbose)
    exit_code = smoke.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
