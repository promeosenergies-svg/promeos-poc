#!/bin/bash
set -e
echo "=== Backend fast tests ==="
cd "$(dirname "$0")/../backend" && python -m pytest -m fast -x --tb=short
echo "=== Frontend tests ==="
cd "$(dirname "$0")/../frontend" && npx vitest run --reporter=dot
echo "=== Lint ==="
cd "$(dirname "$0")/../backend" && ruff check . --config pyproject.toml
cd "$(dirname "$0")/../frontend" && npx eslint src/ --max-warnings=1
echo "✅ Quick check passed"
