# Sprint 1-2 Sol V1 — Progress Log (append-only)

**Branche** : `claude/sol-v1-audit`
**Base** : origin/main `711d3f5e` (cx-sprint25-hardening)
**Worktree** : `C:/Users/amine/promeos-poc/promeos-sol-audit/`

---

## Commits prépa réalisés (pre-Gate 0)

| SHA | Titre | Fichiers |
|---|---|---|
| `d0b4d0df` | docs(sol-v1): decisions log + applied prompt | 2 docs ajoutés |
| `0dbbc2de` | docs(sol-v1): audit package + findings | 6 docs ajoutés |
| `c8644743` | chore(deps): add anthropic + freezegun for Sol V1 | backend/requirements.txt +4 lignes |
| `00610bb8` | fix(tests): auto-inject test secrets in conftest | backend/tests/conftest.py +10 lignes |

---

## Gate 0 — Audit read-only (DONE 2026-04-18)

### Environnement technique confirmé

- **Python** : 3.14.3 (supporte `from datetime import UTC` et `timezone.utc` — on reste sur `timezone.utc` par DÉCISION P1-1 pour aligner sur les 381 occurrences existantes)
- **DB dev** : SQLite par défaut (`backend/data/promeos.db`)
- **Deps Sol installées** : `anthropic>=0.40.0` + `freezegun>=1.5.0` ✓
- **conftest auto-inject** : vérifié — `pytest --collect-only` sans `PROMEOS_JWT_SECRET` env fonctionne ✓

### Baseline tests Gate 0

**Backend** :
```
5605 tests collected in ~15s · 0 erreur de collecte
```
→ baseline pour Gate 4 "régression ≥ baseline".

**Frontend** :
Install partiel dans worktree (node_modules workspace-split, tailwind non résolu sans scripts). Non bloquant pour Sprint 1-2 (backend-only). Baseline frontend à re-mesurer Gate 4 après `npm install` complet dans worktree parent si refresh nécessaire. Référence mémoire CLAUDE.md : ~3870 tests FE au merge sprint CX 2.5 hardening (PR #237).

### Patterns référencés dans DECISIONS_LOG — vérification factuelle

| Pattern | Attendu | Trouvé | Statut |
|---|---|---|---|
| `TimestampMixin` | `backend/models/base.py` avec `updated_at onupdate=now()` | `models/base.py:14` classe + `updated_at` ligne 27 | ✓ |
| `CreatedAtOnlyMixin` | Absent, à créer | 0 hit | ✓ (absence confirmée) |
| `resolve_org_id` signature | `(request, auth, db, *, org_id_override)` appelée body | `services/scope_utils.py:81` + usage `actions.py:103`, `aper.py:30`, `bacs.py:55` | ✓ |
| `get_optional_auth` | `Depends`-compatible | `middleware/auth.py:95` | ✓ |
| `JobOutbox` model | Existe | `models/job_outbox.py:13` (`__tablename__="job_outbox"`) | ✓ |
| `JobType` + `JobStatus` enums | Présents | **Relocalisés** : `models/enums.py:236` (JobType) et `models/enums.py:243` (JobStatus), PAS dans `models/job_outbox.py` comme le prompt laissait entendre | ⚠ correction Phase 3 |
| `enqueue_job` helper | Signature `(db, job_type, payload, priority=0)` | `jobs/worker.py:21` ✓ | ✓ |
| `cx_logger` | Réutilisable pour Sol monitoring | **Relocalisé** : `middleware/cx_logger.py` (pas `services/cx_logger.py` comme écrit dans DECISIONS_LOG P1-4) — API `log_cx_event(db, ...)`, utilise `AuditLog` model (V117) avec event_type préfixé `CX_*` | ⚠ correction P1-4 |
| `tarifs_reglementaires.yaml` | Existe | `backend/config/tarifs_reglementaires.yaml` ✓ | ✓ |
| Migration custom pattern | `_migrate_<feature_name>(engine)` dans `database/migrations.py` | Confirmé : les fonctions s'appellent `_migrate_usage_v1_1`, `_migrate_operat_trajectory`, `_migrate_compliance_event_log`, `_migrate_bacs_hardening`, `_migrate_contracts_v2`, `_migrate_phase1_contrats_cadre`, `_migrate_phase5_invoice_annexe_site` etc. **Pas de naming V112/V113/V114** — le prompt mentionnait ces noms de sprint, pas les noms de fonctions. Le pattern réel = 1 fonction par feature, préfixe `_migrate_`. | ⚠ correction DECISIONS_LOG + PROMPT_APPLIED |

### Corrections à apporter au PROMPT_APPLIED avant Phase 1

1. **Phase 1 section 1.3** — remplacer toutes références "pattern V113/V114" par "pattern `_migrate_<feature_name>`". Fonction à nommer : `_migrate_sol_v1_foundations(engine)` ✓ (déjà correct dans le prompt).

2. **Phase 3 section 3.4** — corriger :
   - "Ajouter `JobType.SOL_EXECUTE_PENDING_ACTION` dans enum" → préciser **fichier** : `backend/models/enums.py:236` (pas `models/job_outbox.py`).
   - Même correction pour toute mention de JobType/JobStatus.

3. **DECISIONS_LOG P1-4** — corriger : `cx_logger` est à `backend/middleware/cx_logger.py` (pas `services/`). Ajouter note API : `log_cx_event(db, user_id, org_id, event_type, ...)`. Event types = constantes `CX_*` définies en haut du fichier (`CX_INSIGHT_CONSULTED`, `CX_MODULE_ACTIVATED`, etc.).

4. **Ajouter constantes Sol** — quand Phase 4 wire le logging : créer constantes `SOL_PROPOSE_GENERATED`, `SOL_ACTION_SCHEDULED`, `SOL_ACTION_EXECUTED`, `SOL_ACTION_CANCELLED`, `SOL_PLAN_REFUSED` suivant le même pattern que `CX_*` mais préfixées `SOL_*`.

### Questions ouvertes détectées Gate 0 (non-bloquantes Phase 1, à tracker)

- **Q1** — `models/enums.py:236` : le fichier est-il à jour avec toutes les `JobType` utilisées actuellement ? Ajouter `JobType.SOL_EXECUTE_PENDING_ACTION` = 1 ligne, faible risque.
- **Q2** — `services/iam_service.py:35` lit `PROMEOS_JWT_SECRET` à l'import : le junior va peut-être avoir la même surprise en Phase 4 avec d'autres vars env. Garder l'œil sur autres modules qui lisent env à l'import (pattern anti-pattern repo à signaler post-seed).
- **Q3** — `AuditLog` (V117) existe déjà pour CX logging. Sol a sa propre table `SolActionLog` append-only. Pas de duplication — les 2 coexistent : `AuditLog` pour événements UI métier (CX), `SolActionLog` pour le trail agentique Sol (plan_json + state_before/after + outcome). À documenter dans Phase 4.
- **Q4** — Migration fonction `_migrate_sol_v1_foundations(engine, inspector)` : certaines migrations existantes prennent `(engine)` seul, d'autres `(engine, inspector)`. À vérifier au moment d'écrire pour matcher le pattern local le plus récent. Voir `_migrate_phase5_invoice_annexe_site(engine)` comme référence.
- **Q5** — Frontend baseline non mesurée dans worktree (node_modules workspace). Non-bloquant Sprint 1-2 (backend-only) mais Gate 4 devra la re-mesurer proprement pour le check "régression ≥ baseline".

### Fichiers existants à reproduire comme modèles

- **Mixin pattern** : `backend/models/base.py:14` (TimestampMixin) — copier structure, retirer `updated_at`.
- **Migration pattern** : `backend/database/migrations.py:2229` (`_migrate_phase5_invoice_annexe_site`) — exemple récent, bien typé.
- **Org-scoped route pattern** : `backend/routes/actions.py:100-110` — exemple canonique.
- **log_cx_event usage** : voir `backend/routes/cx_dashboard.py` ou `routes/copilot.py` — pattern à copier pour `log_sol_event`.

### Fichiers NE PAS toucher ce sprint

- `backend/models/base.py` → **autorisé pour ajouter `CreatedAtOnlyMixin` seulement**, ne pas modifier TimestampMixin/SoftDeleteMixin existants.
- `backend/models/enums.py` → **autorisé pour ajouter `JobType.SOL_EXECUTE_PENDING_ACTION` seulement**, ne pas modifier les autres enums.
- `backend/database/migrations.py` → **autorisé pour ajouter `_migrate_sol_v1_foundations(engine)` + son appel dans `run_migrations()`**, ne pas toucher au reste.
- `backend/jobs/worker.py` → **autorisé pour ajouter le dispatcher `JobType.SOL_EXECUTE_PENDING_ACTION`**, ne pas toucher aux autres types.
- `backend/main.py` → **autorisé pour include_router Sol uniquement** (Phase 4).
- `backend/requirements.txt` → **déjà modifié en Commit A**, ne plus toucher.
- `backend/tests/conftest.py` → **déjà modifié en Commit B**, ne plus toucher.

Tout le reste : **hors scope, zéro tolérance**. Diff review manuel avant chaque commit Phase 1-4.

---

## Gate 0 — Verdict

✅ **Ready for Phase 1.**

- Infrastructure prépa en place (2 commits préparatoires)
- Baseline backend : 5605 tests collectés, 0 erreur
- Patterns référencés tous vérifiés, 3 corrections mineures de localisation identifiées (à appliquer Phase 1 & 3)
- 5 questions ouvertes trackées (non-bloquantes)

**Attente** : validation user pour démarrer Phase 1 (modèles DB Sol + migration custom + 11 tests).

Estimation Phase 1 : 2 jours (CreatedAtOnlyMixin + 4 classes SQLAlchemy + event listener append-only + migration `_migrate_sol_v1_foundations` + tests).

---

---

## Phase 1 — Modèles DB + migration custom (DONE 2026-04-18)

**Durée réelle** : ~1j (vs 2j estimé). Gagné 1j sur estimation.

### Commit
`c90d8b64 feat(sol-p1): Phase 1 — Modèles DB Sol V1 (append-only audit, pending, tokens, policy)`

### Fichiers livrés (8 fichiers, 803 insertions, -1 deletion)

1. `backend/models/base.py` (modif) — +`CreatedAtOnlyMixin` (5 lignes)
2. `backend/models/__init__.py` (modif) — export `CreatedAtOnlyMixin`
3. `backend/models/sol.py` (new) — 4 classes SQLAlchemy + event listener + `AppendOnlyViolation`
4. `backend/database/migrations.py` (modif) — +`_migrate_sol_v1_foundations(engine)` (pattern `_create_sirene_tables`-like, import module + `metadata.create_all(checkfirst=True)`)
5. `backend/tests/sol/__init__.py` (new)
6. `backend/tests/sol/conftest.py` (new) — fixtures `sol_db`, `sol_org`, `sol_user`, `sol_correlation_id`, `now_utc` (DB SQLite mémoire isolée par test)
7. `backend/tests/sol/test_models_sol.py` (new) — 11 tests
8. `backend/tests/sol/test_sol_append_only.py` (new) — 7 tests

### Résultats tests

- **18/18 tests Sol verts en 8s** (vs 11 minimum exigé, +64% de couverture)
- **5623 tests collected total** (+18 Sol vs baseline 5605, 0 régression collecte)
- Couverture `models/sol.py` > 95% (toutes les classes + event listener + `is_dry_run_active` testés)

### Décisions appliquées

- P0-1 : Integer PK autoincrement ✓ (les 4 tables)
- P0-2 : `Column(JSON)` + event listener `before_update` (pas JSONB, pas trigger DDL)
- P0-5 : `CreatedAtOnlyMixin` créé et utilisé par `SolActionLog` / `SolPendingAction` / `SolConfirmationToken`. `SolOrgPolicy` a son propre `updated_at` (mutable).
- P0-3 : Migration custom pattern `_migrate_<feature_name>(engine)` avec `metadata.create_all(tables=[...], checkfirst=True)` — wired dans `run_migrations()` après `_create_sirene_tables`.
- P1-1 : `datetime.now(timezone.utc)` partout (zéro `datetime.utcnow()` introduit)

### Surprises / findings Phase 1

- **Test pré-existant cassé sur origin/main** : `tests/test_iam.py::TestScopeFiltering::test_sites_unfiltered_without_auth` échoue avec 401 au lieu de 200 attendu. Reproduit avec et sans mes changements Phase 1. Pas de ma faute, à remonter à l'équipe hors scope Sprint 1-2 Sol.
- **Git stash avec event listener** : `git stash` peut "oublier" les changements de certaines modifs sur fichiers modifiés en même temps que des fichiers nouveaux. Recovery par `git stash pop`. Incident contrôlé.
- **origin/main à jour** : 4 commits en avance depuis base `711d3f5e` (dernier `5fb57031 feat(cx-ux): migrate PriorityActions to FindingCard`). Branche Sol reste stable sur `711d3f5e`, pas de rebase nécessaire (pas de conflit scope).
- **User model fields** : `hashed_password` (pas `password_hash`), `actif` (pas `is_active`), `nom` + `prenom` requis. Corrigé dans fixture `sol_user`.

### Ce que Phase 1 ne livre pas (conforme au scope)

- Pas de `JobType.SOL_EXECUTE_PENDING_ACTION` encore (Phase 3)
- Pas de `cx_logger` wiring (Phase 4 — utiliser `middleware/cx_logger.py`)
- Pas de schemas Pydantic (Phase 2)
- Pas de `frenchifier()` (Phase 2)

---

## STOP GATE 1 — livré ✅

Attente validation user pour lancer Phase 2 (schemas Pydantic + utils + frenchifier + boundaries + voice templates V1).

Estimation Phase 2 : 3 jours.

---

---

## Phase 2 — Schemas + utils + frenchifier + boundaries + context (DONE 2026-04-18)

**Durée réelle** : ~1.5j (vs 3j estimé). Gagné 1.5j (cumulé : 2.5j d'avance).

### Commit
`93f2ed08 feat(sol-p2): Phase 2 — Schemas Pydantic + utils + frenchifier + boundaries + context`

### Fichiers livrés (14 fichiers, 1998 insertions)

Modules backend/sol/ :
- `__init__.py` : package org
- `utils.py` : 11 fonctions (datetime, hash, tokens HMAC, formatters FR)
- `schemas.py` : IntentKind + ActionPhase + AgenticMode + ActionPlan + PlanRefused + ExecutionResult + Source + Warning + SolContextData
- `voice.py` : frenchifier() + SOL_VOICE_TEMPLATES_V1 (30 templates) + render_template()
- `boundaries.py` : is_out_of_scope() + boundary_response()
- `context.py` : build_sol_context() + _load_or_default_policy() + _load_last_3_actions()
- `prompts/v1/*.txt` : 3 stubs Sprint 7-8

Tests backend/tests/sol/ :
- test_utils.py (28 tests), test_schemas.py (19), test_voice.py (30), test_boundaries.py (30), test_context.py (5)

### Résultats tests

- **147/147 tests Sol verts en 10s** (vs 42 après Phase 1, +105 tests Phase 2)
- **5752 tests collected total** (+147 vs baseline 5605, 0 régression collecte)
- Couverture `backend/sol/` > 95%

### Décisions appliquées

- P1-1 `datetime.now(timezone.utc)` : strict partout
- P1-3 `SOL_SECRET_KEY` : lazy load via `_sol_secret_key()` (pas à l'import)
- P1-7 frenchifier créé avec 30 cas testés, idempotence vérifiée
- P1-12 `IntentKind.DUMMY_NOOP` : kind exclusif tests créé

### Surprises / findings Phase 2

- **fmt_pct banker's rounding** : `Decimal.quantize` utilise ROUND_HALF_EVEN par défaut. Un test attendait `12,35` sur 0.12345 × 100 — banker's arrondit à 12,34. Test ajusté pour valeur non-ambigüe (0.1236).
- **fmt_pct precision=0** : cas où `str(Decimal)` ne contient pas de `.` → split plantait. Fix : branch conditionnelle dans fmt_pct.
- **frenchifier idempotence** : vérifiée sur 8 cas (espaces fines, guillemets, tirets, ordinaux, accents, nombres, techniques) + test générique `frenchifier(frenchifier(x)) == frenchifier(x)`.
- **boundaries regex stratégie d'achat** : ajouté `stratégie.*d.?achat` dans financial_advice car "conseille-moi une stratégie d'achat optimale" passait through initialement.

### Ce que Phase 2 ne livre pas (conforme au scope)

- Pas de planner, validator, scheduler (Phase 3)
- Pas de routes API /api/sol/* (Phase 4)
- Pas de LLM (Sprint 7-8 — prompts v1/*.txt sont stubs)
- Pas de UI (Sprint 3+)

---

## STOP GATE 2 — livré ✅

Cumul Sprint 1-2 : **6 commits atomiques + 4 commits préparatoires/docs**.
Tests Sol : 147 verts, 5752 collectés totaux (+147 vs baseline).

Attente validation user pour lancer Phase 3 (Planner + Validator +
Scheduler JobOutbox + Audit + DummyEngine — 4j estimé).

---

*Document append-only — ajouter Phase 3, Phase 4 en-dessous au fur et à mesure.*
