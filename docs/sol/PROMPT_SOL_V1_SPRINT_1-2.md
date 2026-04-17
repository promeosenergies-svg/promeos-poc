# PROMPT_SOL_V1_SPRINT_1-2_FONDATIONS.md

**Destination** : Claude Code (Cursor / Terminal) avec MCP Context7 + code-review + simplify actifs.
**Sprint** : Sol V1 — Sprint 1-2 (2 semaines) — Fondations « Zéro Défaut ».
**Scope** : infrastructure agentique sans engine métier encore. Pas d'LLM. Pas d'UI finale. Tout est testé avant la suite.
**Stop gates** : 4 gates obligatoires avec bilan validable avant progression.

---

## Contexte PROMEOS

PROMEOS est un cockpit énergétique B2B France post-ARENH, scoré 6.5/10 (avril 2026). Stack : FastAPI + SQLAlchemy (backend, SQLite PostgreSQL-ready), React 18 + Vite + Tailwind v4 + Recharts (frontend). Test baseline actuel : ~3783 tests FE (Vitest), ~68+ tests BE (pytest). P0 sécurité multi-tenant en cours (org-scoping ~22 route files).

Sol V1 agentique est livré en 8 semaines. Ce sprint 1-2 pose les **fondations techniques invariantes** : les 5 lois (prévisualisation, réversibilité, moteurs déterministes, audit, refus explicite), sans aucun engine métier encore, sans LLM encore.

Doctrine de voix : **vouvoiement, pas de mascotte, grammaire française stricte**. Voir `docs/sol/voice_guide.md` (déjà rédigé, à lire avant toute rédaction de copy).

---

## Phase 0 — Audit read-only obligatoire (STOP GATE 0)

**Avant toute écriture de code**, produire le bilan suivant en markdown :

### 0.1 — Exploration repository
```bash
ls -la backend/
ls -la backend/models/
ls -la backend/routes/
ls -la backend/services/
ls -la frontend/src/
ls -la frontend/src/ui/
ls -la frontend/src/__tests__/
cat backend/main.py | head -80
cat backend/models/__init__.py 2>/dev/null || echo "no init"
grep -r "resolve_org_id" backend/routes/ | wc -l
grep -r "get_optional_auth" backend/ | wc -l
```

### 0.2 — État actuel à relever
- Nombre de routes actuelles dans `backend/routes/`
- Présence et état du pattern org-scoping
- Présence des helpers `not_deleted()`, `soft_delete()`
- Présence de tables UUID vs autoincrement int
- Présence d'un système de migrations (Alembic ou pas)
- État du TimestampMixin, SoftDeleteMixin
- Présence d'un logger structuré (`json_logger.py` ?)
- État du design system (`ui/tokens.js`, `ui/index.js`)
- Nombre de tests actuellement verts

### 0.3 — Dépendances manquantes à signaler
- `apscheduler` (scheduler) ou équivalent cron Python
- `pyhumps` ou util de frenchification
- `anthropic` SDK (pour plus tard mais à prévoir)
- `weasyprint` ou `puppeteer` (pour PDF plus tard mais à prévoir)

### 0.4 — Livrable Gate 0
Fichier `docs/sol/sprint_1_2_audit.md` qui répond :
- [ ] État des lieux complet
- [ ] Dépendances à ajouter listées (avec versions)
- [ ] Risques de régression identifiés
- [ ] Stratégie de migration DB proposée (SQLite dev, Postgres prod-ready)
- [ ] Estimation temps par phase

**STOP GATE 0** : produire ce bilan, s'arrêter, demander validation. Ne pas écrire de code.

---

## Phase 1 — Modèles DB + migrations (STOP GATE 1)

**Objectif** : créer les 4 tables core avec contraintes et triggers. Zéro logique métier encore.

### Fichiers
- `backend/models/sol.py` — 4 classes SQLAlchemy
- `backend/alembic/versions/{timestamp}_sol_v1_foundations.py`
- `backend/tests/sol/test_models_sol.py`

### Classes
- `SolActionLog` (append-only via trigger) — id UUID, org_id, user_id, correlation_id, intent_kind, action_phase, inputs_hash, plan_json, state_before/after, outcome_code/message, llm_calls, confidence, anonymized
- `SolPendingAction` — id, correlation_id (unique), org_id, user_id, intent_kind, plan_json, scheduled_for, cancellation_token (unique), status (waiting/executing/executed/cancelled)
- `SolConfirmationToken` — token (PK 64 char), correlation_id, plan_hash, user_id, org_id, expires_at (5 min TTL), consumed
- `SolOrgPolicy` — org_id (PK), agentic_mode (4 enum values), dry_run_until, dual_validation_threshold, confidence_threshold (default 0.85), grace_period_seconds (default 900), tone_preference (default vous)

### Mixins réutilisés
- `TimestampMixin` déjà présent → réutiliser
- Pas de SoftDeleteMixin pour Sol (append-only)

### Tests unitaires (>95% couverture)
- test_sol_action_log_append_only_trigger
- test_sol_action_log_json_serialization
- test_sol_pending_action_unique_correlation_id
- test_sol_confirmation_token_expiry
- test_sol_confirmation_token_single_use
- test_sol_org_policy_defaults
- test_sol_org_policy_dry_run_check
- test_sol_action_phase_enum_values

### Règles imposées
- Imports : `from models.sol import ...`
- Types : tout datetime en `datetime.now(UTC)` — pas de `datetime.utcnow()`
- UUIDs : `uuid.uuid4()` Python, `gen_random_uuid()` Postgres

### Livrables Gate 1
- backend/models/sol.py créé, 4 classes, docstrings claires
- Migration Alembic générée et testée (upgrade/downgrade OK)
- Trigger Postgres dans migration (avec équivalent SQLite via event)
- 8 tests minimum, tous verts
- Commit atomique : `feat(sol-p1): Phase 1 — Modèles DB Sol V1 (append-only audit log, pending actions, tokens, org policy)`

**STOP GATE 1** : bilan tests + migration + trigger validé. Demander validation avant Phase 2.

---

## Phase 2 — Schemas Pydantic + utilitaires Sol core (STOP GATE 2)

### Fichiers
- backend/sol/__init__.py
- backend/sol/schemas.py
- backend/sol/utils.py
- backend/sol/context.py
- backend/sol/boundaries.py
- backend/sol/voice.py
- backend/tests/sol/test_schemas.py
- backend/tests/sol/test_utils.py
- backend/tests/sol/test_voice.py
- backend/tests/sol/test_boundaries.py

### Schemas
- IntentKind (Enum, 5 V1 + CONSULTATIVE_ONLY)
- ActionPhase (Enum, 8 valeurs)
- ActionPlan (BaseModel validation stricte)
- PlanRefused (BaseModel)
- ExecutionResult (BaseModel)
- SolContext (BaseModel)
- Source (BaseModel)
- Warning (BaseModel)

### Utils
- now_utc(), hash_inputs(), generate_correlation_id()
- generate_cancellation_token(), generate_confirmation_token()
- verify_confirmation_token(), fmt_eur(), fmt_mwh(), fmt_pct()

### Frenchifier
- Fonction `frenchifier(text)` : espaces fines, insécables, guillemets chevrons, tirets cadratins, majuscules accentuées, ordinaux typographiques
- SOL_VOICE_TEMPLATES_V1 : 30 templates couvrant S01-S50 du voice guide
- `render_template(key, ctx)`

### Boundaries
- OUT_OF_SCOPE_PATTERNS (financial, legal, personal)
- is_out_of_scope() → (bool, reason_fr)
- BOUNDARY_RESPONSES par catégorie

### Context
- SolContext.build(request, db, correlation_id)

### Tests (>95% couverture)
- test_schemas.py : 8 tests min
- test_utils.py : 15 tests min (incluant vérif char codes 0x202F et 0x00A0)
- test_voice.py : 20 cas frenchifier
- test_boundaries.py : 15 questions test

### Livrables Gate 2
- Tests verts, couverture > 95%
- Aucun `datetime.utcnow()` introduit (grep check)
- Commit : `feat(sol-p2): Phase 2 — Schemas Pydantic + utils + frenchifier + boundaries`

**STOP GATE 2** : validation par bilan + git diff review.

---

## Phase 3 — Planner + Validator + Scheduler (STOP GATE 3)

### Fichiers
- backend/sol/planner.py
- backend/sol/validator.py
- backend/sol/scheduler.py
- backend/sol/audit.py
- backend/sol/engines/__init__.py
- backend/sol/engines/base.py
- backend/sol/engines/_dummy.py
- tests correspondants

### Base engine
```python
class SolEngine(ABC):
    KIND: IntentKind
    MIN_CONFIDENCE: float = 0.85
    GRACE_PERIOD_SECONDS: int = 900
    REVERSIBLE: bool = True

    @abstractmethod
    def dry_run(self, ctx, params) -> ActionPlan | PlanRefused: ...

    @abstractmethod
    def execute(self, ctx, plan, confirmation_token) -> ExecutionResult: ...

    def revert(self, ctx, log_entry, reason) -> ExecutionResult: raise NotReversibleError

ENGINE_REGISTRY: dict[IntentKind, SolEngine] = {}
def register_engine(engine): ...
```

### Planner
- propose_plan(ctx, intent, params) — dispatch engine, check policy, log append-only phase=proposed

### Validator
- validate_plan_for_execution(ctx, plan, token)
- Lève : InvalidToken, PlanAltered, DryRunBlocked, DualValidationMissing

### Scheduler
- schedule_pending_action(ctx, plan, confirmation_token)
- cancel_pending_action(cancellation_token, user_id=None) — accepte sans auth si token valide
- execute_due_pending_actions(db, now) — job périodique APScheduler

### Audit
- log_action(ctx, phase, plan_or_refusal, outcome)
- get_audit_trail(ctx, correlation_id)
- check_audit_integrity(db, window_hours=1)

### Tests critiques (30+ tests)
- test_propose_schedule_cancel_cycle (clé)
- Cycle complet propose → schedule → execute via DummyEngine

### Livrables Gate 3
- Commit : `feat(sol-p3): Phase 3 — Planner + Validator + Scheduler + Audit + DummyEngine`

**STOP GATE 3** : run tests + démo du cycle complet via script Python → validation.

---

## Phase 4 — Routes API + sécurité + monitoring (STOP GATE 4)

### Fichiers
- backend/routes/sol.py (propose, preview, confirm, cancel)
- backend/routes/sol_audit.py (audit trail, export)
- backend/routes/sol_policy.py (org policy management)
- backend/main.py (register routers)
- tests correspondants

### Routes
```
POST   /api/sol/propose       → ActionPlan | PlanRefused (201)
POST   /api/sol/preview       → ActionPlan complet (200)
POST   /api/sol/confirm       → 202 scheduled + pending_action_id
POST   /api/sol/cancel        → 200 cancelled
GET    /api/sol/pending       → list[SolPendingActionDTO]
GET    /api/sol/audit         → paginated list
GET    /api/sol/audit/export  → CSV ou PDF
GET    /api/sol/policy        → SolOrgPolicyDTO (admin only)
PUT    /api/sol/policy        → admin only
```

Stubs `501 Not Implemented Yet` pour `/ask` et `/headline` (Sprint 7-8).

### Règles routes
- `Depends(resolve_org_id)` + `Depends(get_optional_auth)` — NON NÉGOCIABLE
- Gestion erreur standardisée : `{code, message_fr, correlation_id, hint_fr}`
- Logs structurés via `json_logger`
- Pydantic `response_model` OBLIGATOIRE

### Tests org-scoping critique
- test_org_scoping_sol.py : chaque route testée cross-tenant
- Requête sans org_id → 401/403
- Requête org A ne peut PAS accéder org B
- correlation_id cross-org rejeté

### Livrables Gate 4
- Toutes routes avec org-scoping
- Tests routes + org-scoping verts (15+)
- Export CSV audit fonctionnel
- Tests total Sol : > 70, tous verts
- Régression : `pytest backend/` ≥ baseline
- Commit : `feat(sol-p4): Phase 4 — Routes API Sol V1 + org-scoping strict + audit/policy/pending`

**STOP GATE 4** : bilan complet Sprint 1-2 → validation avant Sprint 3.

---

## Règles non-négociables pour TOUT ce sprint

1. **Ne toucher QUE** `backend/models/sol.py`, `backend/sol/*`, `backend/routes/sol*`, `backend/tests/sol/*`. Zéro modif dans `routes/compliance.py`, `routes/ems.py`, etc.
2. **Chaque phase a un commit atomique**. Jamais de commit fourre-tout.
3. **`git status` clean avant chaque STOP GATE**.
4. **`datetime.utcnow()` interdit** — utiliser `datetime.now(UTC)` ou helper.
5. **Aucun hardcoding de chiffres réglementaires** — importer depuis `tarifs_reglementaires.yaml` ou `emission_factors.py`.
6. **Aucun LLM appelé** dans ce sprint. Tout déterministe. LLM arrive Sprint 7-8.
7. **Frenchifier appliqué sur toutes chaînes FR** — tests CI vérifient absence `"` droits dans templates.
8. **Couverture test > 95%** sur `backend/sol/`.
9. **MCP obligatoires** : Context7 avant pattern FastAPI/SQLAlchemy/Pydantic, code-review avant commit, simplify si fichier > 250 lignes.
10. **Si ambigu, poser question dans le bilan, ne pas inventer**. Pas de hardcoding "plausible".

---

## Definition of Done Sprint 1-2

- [ ] 4 STOP GATES passés avec bilans validés
- [ ] 4 commits atomiques propres
- [ ] 70+ tests Sol verts, couverture > 95%
- [ ] Régression globale : tests verts ≥ baseline
- [ ] Aucune modification hors scope Sol
- [ ] Documentation inline claire
- [ ] `backend/sol/` prêt pour Sprint 3 sans refactor

---

## Ce que Sprint 1-2 NE livre PAS

- Aucun engine métier réel (Sprint 3+)
- Pas de LLM (Sprint 7-8)
- Pas d'UI frontend Sol (Sprint 3+)
- Pas de voice layer ambient (Sprint 7-8)
- Pas de conversation Mode 2 (Sprint 7-8)
- Pas de mail réel envoyé (mock dev, vrai Sprint 3 avec Invoice Dispute)

Ce sprint est **infrastructure pure**. Succès = reste devient possible.

---

## Questions ouvertes à clarifier

- Choix scheduler : APScheduler vs Celery vs cron externe ?
- DB prod : SQLite V1 ou forcer Postgres ?
- Stockage plan_json volumineux (CSV OPERAT 50 ko) : JSONB OK ou S3 ?
- Rétention journal : 3 ans strict ou configurable par org ?
