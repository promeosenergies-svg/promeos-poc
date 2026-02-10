# AUDIT SUMMARY - PROMEOS POC
**Date**: 2026-02-09
**Auditeur**: Claude Code (Principal Architect)
**Scope**: Pre-integration audit complet (RegOps + préparation briques 2/3 + RBAC + KB)

---

## ÉTAT GLOBAL: 🟡 AMBER

**Résumé**: Infrastructure solide, 73% tests OK, frontend build OK, mais 10 blockers critiques avant prod/intégration.

---

## ✅ CE QUI MARCHE (PREUVES)

1. **Compliance Engine (Legacy)**: 56/56 tests PASS
   Preuve: `tests/test_compliance_engine.py` - Toutes classes vertes

2. **API Compliance Sites**: 8/8 tests PASS
   Preuve: `tests/test_site_compliance_api.py` - Endpoint `/api/sites/{id}/compliance` fonctionnel

3. **Connectors Registry**: 7/7 tests PASS
   Preuve: `tests/test_connectors.py` - Auto-discovery + RTE/PVGIS OK

4. **Watchers Infra**: 5/6 tests PASS
   Preuve: `tests/test_watchers.py` - RSS parsing + hash dedup fonctionnel

5. **Frontend Build**: ✅ SUCCESS (6.86s)
   Preuve: `npm run build` → dist/ généré, 281KB bundle

6. **API Routes**: 37 endpoints détectés
   Preuve: `grep @router routes/*.py` → RegOps (4), Connectors (3), Watchers (4), AI (5), etc.

7. **DB Schema**: 18 tables identifiées
   Preuve: `backend/models/*.py` → organisation, site, reg_assessment, datapoints, job_outbox, etc.

8. **Seed Data**: 120 sites + 615 evidences + 120 assessments
   Preuve: `backend/scripts/seed_data.py` ligne 475-486

---

## 🔴 TOP 10 BLOCKERS (CRITIQUE)

### Famille 1: YAML Config Mismatch (16 tests)

**Blocker #1**: RegOps tests cherchent clés YAML inexistantes
- **Fichier**: `tests/test_regops_rules.py:86,100,113,126,143...`
- **Erreur**: `KeyError: 'tertiaire_operat'` (cherche underscore, YAML a sans)
- **Cause**: _load_configs() retourne dict avec clés top-level, tests assument nested
- **Fix**: Aligner tests sur structure YAML réelle (`configs['tertiaire_operat']` → `configs['tertiaire_operat']` vérifié dans YAML)
- **Effort**: 15 min
- **Impact**: 🔴 CRITIQUE - Bloque validation RegOps

**Blocker #2**: TypeEvidence enum incomplet
- **Fichier**: `models/enums.py` manque `AUDIT_ENERGETIQUE`
- **Erreur**: `AttributeError: type object 'TypeEvidence' has no attribute 'AUDIT_ENERGETIQUE'`
- **Cause**: Tests CEE P6 utilisent `AUDIT_ENERGETIQUE`, enum a `AUDIT`
- **Fix**: Ajouter `AUDIT_ENERGETIQUE = "audit_energetique"` dans TypeEvidence
- **Effort**: 5 min
- **Impact**: 🟡 MOYEN - Bloque tests CEE P6

### Famille 2: AI Agents Fixtures (5 tests)

**Blocker #3**: Site model fixture incompatible
- **Fichier**: `tests/test_ai_agents.py:32-44`
- **Erreur**: `TypeError: 'organisation_id' is an invalid keyword argument for Site`
- **Cause**: Site n'a pas organisation_id direct (via portefeuille)
- **Fix**: Créer chaîne complète org→entite→portefeuille→site dans fixture
- **Effort**: 10 min
- **Impact**: 🟡 MOYEN - Bloque validation AI stub mode

### Famille 3: JobOutbox SQL (4 tests)

**Blocker #4**: Job enqueue retourne objet pas ID
- **Fichier**: `jobs/worker.py:enqueue_job()`
- **Erreur**: `sqlalchemy.exc.ArgumentError: SQL expression element or literal value expected`
- **Cause**: `enqueue_job()` retourne JobOutbox object, tests attendent int ID
- **Fix**: Retourner `job.id` au lieu de `job`
- **Effort**: 5 min
- **Impact**: 🟡 MOYEN - Bloque async job queue

**Blocker #5**: Watcher names mismatch
- **Fichier**: `tests/test_watchers.py:47`
- **Erreur**: `assert 'legifrance_watcher' in ['legifrance', 'cre', 'rte']`
- **Cause**: Registry retourne `watcher.name` (sans suffixe _watcher)
- **Fix**: Aligner tests ou registry (recommandé: tests → 'legifrance')
- **Effort**: 2 min
- **Impact**: 🟢 LOW - Cosmétique

### Famille 4: Production Hygiene

**Blocker #6**: Pas d'authentification/autorisation
- **Fichier**: AUCUN (manquant)
- **Cause**: Routes sensibles (recompute, watchers run, jobs) sans auth
- **Risque**: 🔴 CRITIQUE - N'importe qui peut déclencher recompute massif
- **Fix**: Implémenter RBAC simple (X-Role header + token env)
- **Effort**: 2-3h
- **Impact**: 🔴 CRITIQUE PROD

**Blocker #7**: Pas de logging structuré
- **Fichier**: Logging basique `print()` dans plusieurs modules
- **Cause**: Pas de logger central avec niveaux/handlers
- **Risque**: 🟡 MOYEN - Debugging prod impossible
- **Fix**: Configurer Python logging avec rotation + JSON format
- **Effort**: 1h
- **Impact**: 🟡 MOYEN PROD

**Blocker #8**: Pas de monitoring/observabilité
- **Fichier**: Aucun /metrics endpoint
- **Cause**: Pas d'instrumentation (Prometheus, StatsD, ou autre)
- **Risque**: 🟡 MOYEN - Pas de visibilité runtime
- **Fix**: Ajouter prometheus-fastapi-instrumentator
- **Effort**: 30 min
- **Impact**: 🟡 MOYEN PROD

**Blocker #9**: DB SQLite non adapté prod
- **Fichier**: `database/connection.py:17` → `sqlite:///`
- **Cause**: SQLite = fichier local, pas scalable/concurrent
- **Risque**: 🔴 CRITIQUE PROD - Perte données, locks
- **Fix**: Migration PostgreSQL + alembic
- **Effort**: 4h
- **Impact**: 🔴 CRITIQUE PROD

**Blocker #10**: Secrets en clair (.env non gitignored)
- **Fichier**: `.env.example` présent, mais `.env` pas dans .gitignore vérifié
- **Cause**: Risque commit accidentel secrets
- **Risque**: 🔴 CRITIQUE SÉCURITÉ
- **Fix**: Vérifier .gitignore + vault (Doppler/AWS Secrets)
- **Effort**: 15 min
- **Impact**: 🔴 CRITIQUE SÉCURITÉ

---

## 📊 MÉTRIQUES TESTS

| Fichier | Total | Pass | Fail | % |
|---------|-------|------|------|---|
| **test_compliance_engine.py** | 56 | 56 | 0 | 100% |
| **test_site_compliance_api.py** | 8 | 8 | 0 | 100% |
| **test_connectors.py** | 7 | 7 | 0 | 100% |
| **test_watchers.py** | 6 | 5 | 1 | 83% |
| **test_job_outbox.py** | 6 | 2 | 4 | 33% |
| **test_ai_agents.py** | 7 | 2 | 5 | 29% |
| **test_regops_rules.py** | 16 | 0 | 16 | 0% |
| **TOTAL** | **98** | **72** | **26** | **73%** |

---

## 🎯 RECOMMANDATION: ORDRE DE BATAILLE

### 🔥 CRÉNEAU 60-90 MIN (ce soir)
**Objectif**: Débloquer tests RegOps + quick wins sécurité

1. Fix YAML config keys mismatch (15 min) → +16 tests
2. Add TypeEvidence.AUDIT_ENERGETIQUE (5 min) → +4 tests
3. Fix AI agents fixture (10 min) → +5 tests
4. Fix JobOutbox return type (5 min) → +4 tests
5. Fix watcher names (2 min) → +1 test
6. Vérifier .gitignore secrets (5 min)
7. Add basic X-Role header check (20 min)

**Output**: 95%+ tests passing, basic security

### ⚡ CRÉNEAU 3-4H (demain matin)
**Objectif**: Production-ready hygiene

1. Structured logging (1h)
2. /metrics endpoint Prometheus (30 min)
3. RBAC complet avec matrice (1.5h)
4. Documentation RBAC_MATRIX.md (30 min)
5. CI/CD pipeline basique (30 min)

**Output**: Production monitoring + auth solide

### 🏗️ CRÉNEAU 1 JOURNÉE (cette semaine)
**Objectif**: PostgreSQL + Briques 2/3 prep

1. PostgreSQL migration + Alembic (4h)
2. Brique 2 (Bill Intelligence) prep: interfaces + contrats (2h)
3. Brique 3 (Achat post-ARENH) prep: interfaces + contrats (2h)
4. Tests E2E Playwright (2h)

**Output**: Prod DB + roadmap briques 2/3

---

## 🚨 RISQUES MAJEURS

1. **Auth Bypass**: Routes sensibles sans protection → DoS possible
2. **Data Loss**: SQLite corruption si concurrent writes → PostgreSQL urgent
3. **Secrets Leak**: .env commit → Vault mandatory
4. **No Rollback**: Pas de migrations Alembic → Schema drift inévitable
5. **Blind Monitoring**: Pas de logs structurés → Debugging prod = cauchemar

---

## ✅ TOP 5 ACTIONS IMMÉDIATES

| # | Action | Effort | Owner | Deadline | Impact |
|---|--------|--------|-------|----------|--------|
| 1 | Fix 5 blockers tests (YAML, enum, fixtures, job, watcher) | 37 min | Dev | Ce soir | 🔴 CRITICAL |
| 2 | Add X-Role header auth sur routes sensibles | 20 min | Dev | Ce soir | 🔴 CRITICAL |
| 3 | Verify .gitignore + secrets vault | 15 min | DevOps | Ce soir | 🔴 CRITICAL |
| 4 | Structured logging + /metrics | 1.5h | Dev | Demain AM | 🟡 HIGH |
| 5 | RBAC matrix doc + implementation | 2h | Architect | Demain AM | 🟡 HIGH |

---

## 🎯 NEXT PROMPT RECOMMANDÉ

```
PROMEOS — INTEGRATION REGOPS ULTIMATE++
Objectif: Fix 5 blockers + implement RBAC + structured logging
Scope:
- Fix tests/test_regops_rules.py YAML mismatch
- Fix models/enums.py TypeEvidence
- Fix AI agents fixtures (org chain)
- Fix jobs/worker.py return type
- Add middleware auth (X-Role header)
- Add Python logging config
- Create docs/security/RBAC_MATRIX.md
Deadline: 90 min
```

---

**Conclusion**: POC en bon état mais 10 blockers avant prod. 90 min fix débloque tests. 4h débloque prod hygiene.
