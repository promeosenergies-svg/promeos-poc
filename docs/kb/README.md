# PROMEOS KNOWLEDGE BASE - README

**Version**: 1.0
**Status**: 🟢 Core implemented, scripts + seed pending

---

## 🎯 OVERVIEW

The PROMEOS Knowledge Base is a **structured, queryable, deterministic system** for storing and applying regulatory, usage, and operational knowledge to site contexts.

**Core Principles**:
- ✅ **Zero hallucination**: No recommendations without structured KB items
- ✅ **Full traceability**: Every output includes sources + explanations
- ✅ **Offline-first**: No runtime dependencies on external services
- ✅ **Deterministic apply engine**: Null-safe evaluation with explicit logic
- ✅ **HTML ingestion**: Automatic conversion of documentation → YAML drafts

---

## 📁 STRUCTURE

```
docs/kb/
├── items/              # Validated KB items (YAML)
│   ├── reglementaire/
│   ├── usages/
│   ├── acc/
│   ├── facturation/
│   └── flex/
├── drafts/             # Auto-generated drafts (from HTML ingestion)
├── _meta/
│   ├── taxonomy.yaml   # Closed-list allowed values
│   └── schema_kbitem.yaml  # Canonical format reference

docs/sources/html/      # Ingested HTML docs
├── <doc_id>/
│   ├── raw/            # Original HTML + assets
│   ├── clean/          # clean.md
│   ├── chunks/         # chunks.json
│   └── meta.json

backend/app/kb/
├── models.py           # SQLite schema (kb_items, kb_fts, kb_docs, kb_chunks)
├── store.py            # CRUD operations
├── indexer.py          # FTS5 full-text search
├── service.py          # Apply engine (deterministic evaluation)
├── router.py           # FastAPI endpoints
└── ingest_html.py      # HTML → chunks → YAML drafts

backend/scripts/
├── kb_validate.py      # Validate YAML against taxonomy
├── kb_seed_import.py   # Import YAML → SQLite
├── kb_build_index.py   # Rebuild FTS5 index
└── kb_ingest_html.py   # Ingest HTML documentation
```

---

## 🚀 QUICK START

### 1. Initialize DB

```bash
cd backend
python -c "from app.kb.models import get_kb_db; db=get_kb_db(); print('✅ DB initialized')"
```

### 2. Ingest HTML Documentation

```bash
python backend/scripts/kb_ingest_html.py \
  --input path/to/doc.html \
  --doc-id DECRET-2020-887 \
  --title "Décret BACS"
```

**Output**:
- `docs/sources/html/DECRET-2020-887/` (raw, clean, chunks, meta)
- `docs/kb/drafts/DECRET-2020-887/` (auto-generated YAML drafts)

### 3. Review & Upgrade Drafts

Edit generated drafts in `docs/kb/drafts/`:
- Upgrade `confidence: "low"` → `"high"`
- Refine `tags` (must match taxonomy)
- Add `logic.when` conditions
- Add `logic.then.outputs` (actions)

### 4. Validate YAML

```bash
python backend/scripts/kb_validate.py
```

Checks:
- Required fields present
- Tags match taxonomy
- IDs unique
- Sources present

### 5. Import to DB

```bash
python backend/scripts/kb_seed_import.py --include-drafts
```

### 6. Build FTS5 Index

```bash
python backend/scripts/kb_build_index.py
```

### 7. Test API

```bash
# Start server
cd backend
python main.py

# Test endpoints
curl http://localhost:8000/api/kb/stats
curl http://localhost:8000/api/kb/items?domain=reglementaire

# Search
curl -X POST http://localhost:8000/api/kb/search \
  -H "Content-Type: application/json" \
  -d '{"q": "bacs", "limit": 5}'

# Apply
curl -X POST http://localhost:8000/api/kb/apply \
  -H "Content-Type: application/json" \
  -d '{"site_context": {"hvac_kw": 350, "building_type": "bureau"}}'
```

---

## 📊 API ENDPOINTS

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/kb/items` | List KB items (filter by domain/type) |
| GET | `/api/kb/items/{id}` | Get single KB item |
| POST | `/api/kb/search` | Full-text search (FTS5 + filters) |
| POST | `/api/kb/apply` | Apply KB to site_context (deterministic) |
| GET | `/api/kb/stats` | KB statistics |
| GET | `/api/kb/docs` | List ingested HTML docs |
| GET | `/api/kb/docs/{doc_id}` | Get doc metadata + chunks |

---

## 🧩 KB ITEM FORMAT (YAML)

See `docs/kb/_meta/schema_kbitem.yaml` for complete reference.

**Minimal Example**:

```yaml
id: "BACS-290KW"
type: "rule"
domain: "reglementaire"
title: "Obligation BACS >290 kW"
summary: "Installation GTB obligatoire avant 2025-01-01"

tags:
  energy: [elec]
  segment: [tertiaire_multisite]
  asset: [hvac]
  reg: [bacs]
  granularity: [event]

scope:
  building_type: ["bureau", "magasin"]
  hvac_kw_min: 290

content_md: |
  ## Décret 2020-887
  Installation d'un système BACS (GTB) classe B ou A obligatoire...

logic:
  when:
    all:
      - {field: "hvac_kw", op: ">=", value: 290}
      - {field: "building_type", op: "in", value: ["bureau", "magasin"]}
  then:
    outputs:
      - type: "obligation"
        label: "Installer GTB classe B ou A"
        deadline: "2025-01-01"
        severity: "critical"

sources:
  - doc_id: "DECRET-2020-887"
    label: "Décret n°2020-887"
    section: "Article 2"
    anchor: "#article-2"

updated_at: "2026-02-09"
confidence: "high"
priority: 1
```

---

## 🔍 APPLY ENGINE LOGIC

The **apply engine** (`service.py`) evaluates KB items deterministically:

1. **Load site_context** (e.g., `{hvac_kw: 350, building_type: "bureau"}`)
2. **Evaluate scope** (high-level filters)
3. **Evaluate logic.when** (detailed conditions, null-safe)
4. **Collect why** (which conditions matched)
5. **Extract actions** from `logic.then.outputs`
6. **Return**:
   ```json
   {
     "applicable_items": [
       {
         "kb_item_id": "BACS-290KW",
         "why": ["hvac_kw=350 >= 290", "building_type=bureau in scope"],
         "actions": [{"type": "obligation", "label": "Installer GTB", ...}],
         "sources": [...]
       }
     ],
     "missing_fields": [],
     "status": "ok"
   }
   ```

**Null-Safety**: If a required field is missing in `site_context`, condition = `false`, field added to `missing_fields[]`.

---

## 📦 TAXONOMY (CLOSED LISTS)

See `docs/kb/_meta/taxonomy.yaml`.

**Tag categories**:
- `types`: rule, knowledge, checklist, calc
- `domains`: reglementaire, usages, acc, facturation, flex
- `energy`: elec, gaz, multi
- `segment`: collectivite, bailleur, tertiaire_multisite, industrie, copro
- `asset`: hvac, froid, eclairage, air_comprime, irve, process, it, multi
- `reg`: decret_tertiaire, bacs, loi_aper, acc, turpe, taxes, cee, multi
- `granularity`: mensuel, journalier, 30min, 15min, 10min, event, multi
- `confidence`: high, medium, low

**Validation rejects any value not in taxonomy.**

---

## 🔧 REMAINING WORK (TODO)

### ✅ COMPLETED
- [x] KB directory structure
- [x] Taxonomy + schema definition
- [x] SQLite models (kb_items, kb_fts, kb_docs, kb_chunks)
- [x] Store (CRUD)
- [x] Indexer (FTS5)
- [x] Service (apply engine with null-safe logic)
- [x] FastAPI router (7 endpoints)
- [x] HTML ingestion pipeline (sanitize → chunk → drafts)
- [x] kb_ingest_html.py CLI

### ⏳ TODO (20-30min)
- [ ] **kb_validate.py** (validate YAML against taxonomy)
- [ ] **kb_seed_import.py** (import YAML → DB)
- [ ] **kb_build_index.py** (rebuild FTS5)
- [ ] **Seed pack** (20 YAML items: 8 reglementaire, 8 usages, 4 ACC)
- [ ] **Tests** (pytest for validation, search, apply, HTML ingestion)

---

## 🧪 TESTING

```bash
cd backend
pytest tests/test_kb.py -v
```

**Test coverage**:
- Taxonomy validation (reject unknown tags)
- Search (FTS5 returns results)
- Apply (site_context → applicable items)
- HTML ingestion (HTML → clean.md → chunks → drafts)

---

## 📚 EXAMPLES

### Example 1: Add a new KB item

1. Create `docs/kb/items/reglementaire/tertiaire_scope.yaml`
2. Fill with canonical format (see schema)
3. Validate: `python backend/scripts/kb_validate.py`
4. Import: `python backend/scripts/kb_seed_import.py`
5. Rebuild index: `python backend/scripts/kb_build_index.py`

### Example 2: Ingest HTML doc

```bash
python backend/scripts/kb_ingest_html.py \
  --input ~/Downloads/guide_tertiaire.html \
  --doc-id GUIDE-TERTIAIRE-2024 \
  --title "Guide pratique Décret Tertiaire"
```

Review drafts in `docs/kb/drafts/GUIDE-TERTIAIRE-2024/`, upgrade confidence, then import.

### Example 3: Query KB

```python
from app.kb.service import KBService

service = KBService()

# Apply to site
result = service.apply({
    "surface_m2": 1500,
    "hvac_kw": 350,
    "building_type": "bureau",
    "segment": "tertiaire_multisite"
})

# Print applicable items
for item in result["applicable_items"]:
    print(f"{item['title']}: {item['why']}")
    for action in item["actions"]:
        print(f"  → {action['label']}")
```

---

## 🛠️ TROUBLESHOOTING

### "No such table: kb_items"

**Fix**: Initialize DB
```bash
python -c "from app.kb.models import get_kb_db; get_kb_db()"
```

### "Tag 'foo' not in taxonomy"

**Fix**: Either:
1. Add tag to `docs/kb/_meta/taxonomy.yaml`
2. Or use existing taxonomy value

### "Search returns no results"

**Fix**: Rebuild FTS5 index
```bash
python backend/scripts/kb_build_index.py
```

### "HTML ingestion fails"

**Check**:
- Input file exists
- File is valid HTML (not binary/PDF)
- No encoding errors (use UTF-8)

---

## 🚀 NEXT STEPS

1. **Complete CLI scripts** (kb_validate.py, kb_seed_import.py, kb_build_index.py)
2. **Create seed pack** (20 realistic YAML items)
3. **Write tests** (pytest suite)
4. **Integration test** (full pipeline end-to-end)
5. **Production deployment** (see docs/deployment.md)

---

## 📞 SUPPORT

- Issues: https://github.com/promeosenergies/promeos-poc/issues
- Docs: `docs/kb/`
- API Docs: http://localhost:8000/docs (when server running)

---

**Status**: 🟡 Core functional, CLI + seed pending (80% complete)
