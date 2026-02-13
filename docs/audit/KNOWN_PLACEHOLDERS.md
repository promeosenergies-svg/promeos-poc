# KNOWN PLACEHOLDERS - PROMEOS POC

**Date**: 2026-02-13
**Scan**: Grep sur backend/ + frontend/src/ pour TODO, FIXME, HACK, stub, print, hardcoded secrets

---

## 1. TODO comments (4 occurrences)

| # | Fichier | Ligne | Contenu | Severite |
|---|---------|-------|---------|----------|
| 1 | `jobs/worker.py` | L106 | `# TODO: implement entity/org level recompute` | HIGH - Fonctionnel incomplet |
| 2 | `ai_layer/client.py` | L23 | `# TODO: Real API call (httpx POST to api.anthropic.com)` | HIGH - AI stub |
| 3 | `services/kb_service.py` | L100 | `'temporal_signature_json': None,  # TODO: Extract if available` | MEDIUM |
| 4 | `services/kb_service.py` | L215 | `'implementation_steps_json': None,  # TODO: Extract if available` | MEDIUM |

---

## 2. TabStub (frontend) - 3 onglets non branches

| # | Fichier | Ligne | Onglet | Message affiche |
|---|---------|-------|--------|-----------------|
| 1 | `pages/Site360.jsx` | L416 | Consommation | "Courbes de charge, historique et benchmark a venir." |
| 2 | `pages/Site360.jsx` | L417 | Factures | "Analyse factures, shadow billing et optimisation tarifaire a venir." |
| 3 | `pages/Site360.jsx` | L419 | Actions | "Plan d'action et suivi des recommandations a venir." |

Le composant `TabStub` est defini L128 de Site360.jsx. Il affiche un panneau vide avec "Bientot disponible".

**Fix**: Brancher sur les API existantes (`/api/consommations`, `/api/billing/site/{id}`, `/api/actions/list`).

---

## 3. Secrets hardcodes

| # | Fichier | Ligne | Secret | Risque | Fix |
|---|---------|-------|--------|--------|-----|
| 1 | `services/iam_service.py` | L24 | `JWT_SECRET = os.environ.get("PROMEOS_JWT_SECRET", "dev-secret-change-me-in-prod")` | CRITICAL - Fallback previsible | Crash si env var absente en prod |
| 2 | `scripts/seed_data.py` | L867 | `password="demo2024"` pour les 10 users seed | MEDIUM - Password identique | Variable env ou generation |
| 3 | `scripts/seed_data.py` | L892 | `print("Login demo: sophie@atlas.demo / demo2024")` | LOW - Log du password | Supprimer le print |

---

## 4. print() au lieu de logging (454 occurrences / 33 fichiers)

Les fichiers les plus concernes (hors scripts/):

| # | Fichier | Nombre de print() | Usage |
|---|---------|-------------------|-------|
| 1 | `services/kb_service.py` | 8 | Status ingest KB |
| 2 | `database/connection.py` | 1 | Path de la DB |
| 3 | `connectors/rte_eco2mix.py` | 1 | Status fetch |
| 4 | `connectors/pvgis.py` | 1 | Status fetch |
| 5 | `watchers/rss_watcher.py` | 1 | Status parse |
| 6 | `jobs/worker.py` | 1 | Job processing |
| 7 | `jobs/run.py` | 9 | Worker startup |
| 8 | `regops/engine.py` | 1 | Evaluation status |
| 9 | `app/kb/store.py` | 5 | KB operations |
| 10 | `app/kb/ingest_html.py` | 12 | HTML ingestion |
| 11 | `app/bill_intelligence/parsers/json_parser.py` | 1 | Parse status |

Scripts (attendu, pas un probleme):
- `scripts/seed_data.py`: 70 print()
- `scripts/referential/cli.py`: 65 print()
- `scripts/kb_*.py`: ~150 print() total

**Fix**: Remplacer par `import logging; logger = logging.getLogger(__name__)` dans les services/routes.

---

## 5. Demo / Mock references

| # | Fichier | Contenu | Impact |
|---|---------|---------|--------|
| 1 | `services/demo_state.py` | Demo mode global state (in-memory) | OK - Par design |
| 2 | `services/demo_templates.py` | Templates demo pour scenarios | OK - Par design |
| 3 | `routes/demo.py` | 6 endpoints demo (enable/disable/seed) | OK - Par design |
| 4 | `ai_layer/client.py` | Stub mode retourne mock responses | HIGH - Pas d'appel reel |
| 5 | `services/billing_seed.py` | Seed demo billing data | OK - Par design |
| 6 | `services/purchase_seed.py` | Seed demo purchase data | OK - Par design |

---

## 6. Briques stub / guidance (0 logique reelle)

| # | Fichier | Description | Fix |
|---|---------|-------------|-----|
| 1 | `routes/guidance.py` | 2 endpoints (action-plan, readiness) - logique minimale | Implementer avec compliance_engine |
| 2 | `ai_layer/client.py` | AI client retourne des mock responses | Implementer avec httpx + Anthropic API |
| 3 | `routes/reports.py` | audit.json/audit.pdf - JSON OK, PDF stub | Implementer PDF avec reportlab ou weasyprint |

---

## 7. Deprecation warnings (datetime.utcnow)

54942 warnings de deprecation `datetime.utcnow()` dans 12 fichiers.
Liste detaillee dans TEST_REPORT.md.

**Fix global** (15 min):
```python
# Avant:
from datetime import datetime
now = datetime.utcnow()

# Apres:
from datetime import datetime, UTC
now = datetime.now(UTC)
```

---

## 8. SQLAlchemy legacy warnings

Warnings `Query.get()` deprece (utiliser `Session.get()`) dans:

| Fichier | Occurrences |
|---------|-------------|
| `services/patrimoine_service.py` | L64, L222, L268, L489, L604, L689, L162 |

**Fix**: Remplacer `db.query(Model).get(id)` par `db.get(Model, id)`

---

## Resume des actions

| Categorie | Count | Severite | Effort |
|-----------|-------|----------|--------|
| TODO comments | 4 | HIGH (2), MEDIUM (2) | 2h |
| TabStub frontend | 3 | MEDIUM | 4h |
| Secrets hardcodes | 3 | CRITICAL (1), MEDIUM (1), LOW (1) | 30 min |
| print() -> logging | 454 | LOW (services), OK (scripts) | 2h |
| AI stub | 1 | HIGH | 2h |
| Guidance stub | 1 | LOW | 1h |
| Reports PDF stub | 1 | LOW | 2h |
| datetime.utcnow | 12 fichiers | LOW | 15 min |
| Query.get() legacy | 7 occurrences | LOW | 10 min |
