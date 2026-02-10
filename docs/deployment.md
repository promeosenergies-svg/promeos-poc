# PROMEOS Deployment Guide

## Pre-Deployment Checklist

### 1. Run Smoke Tests (mandatory)
```bash
cd promeos-poc
python backend/scripts/kb_smoke.py --verbose
```
Expected: `VERDICT: ALL CLEAR - Safe for pilot`

If FAIL: fix issues before deployment. If WARN: review warnings and decide.

### 2. Validate KB Items
```bash
python backend/scripts/kb_validate.py --strict
```
Expected: `All N files valid!`

### 3. Run Test Suite
```bash
cd backend
python -m pytest tests/ -v --tb=short
```
Expected: All tests pass (40+ existing + new lifecycle tests).

### 4. Check Coverage Gaps
```bash
python backend/scripts/kb_coverage_report.py
```
Review MISSING items. These are "angles morts" — domains with no KB coverage.

---

## Deployment Steps

### Backend

```bash
# 1. Install dependencies
cd backend
pip install -r requirements.txt

# 2. Initialize database
python scripts/init_database.py

# 3. Import KB items to SQLite
python scripts/kb_seed_import.py --rebuild-index

# 4. Seed demo data
python scripts/seed_data.py

# 5. Run smoke test
python scripts/kb_smoke.py

# 6. Start server
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run build    # Production build
npm run dev      # Development server
```

---

## KB Lifecycle Operations

### Adding New Knowledge

1. **Ingest HTML source:**
   ```bash
   python backend/scripts/kb_ingest_html.py \
     --input path/to/document.html \
     --doc-id MY_DOC_v1 \
     --title "Document Title"
   ```
   This creates draft YAML files in `docs/kb/drafts/MY_DOC_v1/`.

2. **Review & edit drafts:**
   - Open each YAML in `docs/kb/drafts/`
   - Set proper tags (energy, segment, asset, reg, granularity)
   - Write scope and logic.when conditions
   - Upgrade confidence: low -> medium or high
   - Verify sources[] has doc_id and label

3. **Validate:**
   ```bash
   python backend/scripts/kb_validate.py --include-drafts --strict
   ```

4. **Promote to validated:**
   ```bash
   python backend/scripts/kb_promote_item.py docs/kb/drafts/MY_DOC_v1/item.yaml --confidence medium
   ```
   Or batch:
   ```bash
   python backend/scripts/kb_promote_item.py docs/kb/drafts/MY_DOC_v1/ --batch --confidence medium
   ```

5. **Import to database:**
   ```bash
   python backend/scripts/kb_seed_import.py --rebuild-index
   ```

6. **Verify:**
   ```bash
   python backend/scripts/kb_smoke.py
   ```

### Lifecycle Rules

| Status | Confidence | Location | Used in /apply? | Used in /search? |
|--------|-----------|----------|-----------------|------------------|
| draft | low | drafts/ | NO (blocked) | NO (by default) |
| draft | medium | drafts/ | NO (blocked) | YES (if include_drafts=true) |
| validated | medium | items/ | YES | YES |
| validated | high | items/ | YES | YES |
| deprecated | any | items/ | NO | NO |

**HARD RULE**: `validated` + `confidence=low` is FORBIDDEN. Validation will reject it.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | No | SQLAlchemy database URL (default: SQLite) |
| `AI_API_KEY` | No | AI provider API key (stub mode if missing) |
| `AI_MODEL` | No | AI model name (default: claude-sonnet) |
| `METEOFRANCE_API_KEY` | No | MeteoFrance API key (stub if missing) |
| `ENEDIS_CLIENT_ID` | No | Enedis DataConnect client ID |
| `ENEDIS_CLIENT_SECRET` | No | Enedis DataConnect client secret |

---

## Monitoring

### Health Check
```
GET /api/health
```

### KB Statistics
```
GET /api/kb/stats
```
Returns: total items, by domain, by type, by confidence, by status, FTS index stats.

### Apply Engine Test
```bash
curl -X POST http://localhost:8000/api/kb/apply \
  -H "Content-Type: application/json" \
  -d '{"site_context": {"building_type": "bureau", "surface_m2": 1200}, "allow_drafts": false}'
```

---

## Seed Packs

Seed packs provide versioned sets of KB items for reproducible deployments.

```bash
# List available packs
python backend/scripts/kb_seed_expand.py --list-packs

# Apply a pack (won't overwrite existing items)
python backend/scripts/kb_seed_expand.py --pack v1_base

# Dry run
python backend/scripts/kb_seed_expand.py --pack v1_base --dry-run
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "KB item not found" | Run `kb_seed_import.py --rebuild-index` |
| FTS search returns 0 | Run `kb_build_index.py` |
| "validated item with confidence=low" | Fix YAML or use `kb_promote_item.py` |
| Apply returns empty | Check site_context has required fields |
| DB schema mismatch | Delete `data/kb.db` and re-run `kb_seed_import.py` |
