# Sprint 1-2 Sol V1 — Fondations (version APPLICABLE après décisions)

**Version** : v2 patchée post-audit (2026-04-17)
**Source** : `PROMPT_SOL_V1_SPRINT_1-2.md` (original Amine) + `DECISIONS_LOG.md` (décisions conjointes)
**Destinataire** : Claude Code (Cursor/Terminal) avec MCP Context7 + code-review + simplify actifs
**Durée révisée** : 2.5 semaines (12.5j dev) — vs 2 semaines annoncées (correction +47% réaliste)
**Stop gates** : 4 gates obligatoires avec bilan validable

---

## Décisions verrouillées (à appliquer, pas à rediscuter)

Lire `DECISIONS_LOG.md` pour le détail. Résumé actionnable :

| Thème | Décision | Impact pratique |
|---|---|---|
| **Primary keys** | `Integer autoincrement` (pas UUID) | `Column(Integer, primary_key=True, autoincrement=True)` sur les 4 tables Sol. `correlation_id` = `String(36)` tracking UUID Python, non-PK. |
| **Append-only** | `JSON` + SQLAlchemy event listener (pas JSONB + trigger) | `Column(JSON)` générique SQLAlchemy. `@event.listens_for(SolActionLog, 'before_update')` lève `AppendOnlyViolation`. |
| **Mixin créé** | `CreatedAtOnlyMixin` dans `models/base.py` | 5 lignes, `created_at` only, `datetime.now(timezone.utc)` default. Pas d'`updated_at`. |
| **Migration strategy** | Custom `database/migrations.py` V113-V114 pattern (pas Alembic) | Tables déclarées dans `models/sol.py` → `create_all` sur fresh DB + bloc idempotent `CREATE TABLE IF NOT EXISTS` dans `database/migrations.py`. |
| **org-scoping** | `resolve_org_id(request, auth, db)` appelé dans body (pas `Depends`) | Voir pattern `actions.py:103`, `aper.py:30`. |
| **Convention datetime** | `datetime.now(timezone.utc)` partout Sol | Aligner sur les 381 occurrences existantes. Pas de `from datetime import UTC`. |
| **Scheduler** | Réutiliser `JobOutbox` + `worker.py` (pas APScheduler) | `JobType.SOL_EXECUTE_PENDING_ACTION` + `enqueue_job(db, ...)`. |
| **Secret** | Nouvelle var env `SOL_SECRET_KEY` | Dans `.env.example` + `conftest.py` setdefault. |
| **Monitoring** | `cx_logger` pattern (pas Prometheus) | `logging.getLogger("promeos.sol")` + `extra={...}`. |
| **UI** | Hors scope Sprint 1-2 (fondations backend only) | Sprint 3+ : V7 Rail/Panel gardée, `sol.*` namespace tokens, fonts subset 200 ko. |

---

## Pré-requis avant Gate 0 (commits préparatoires séparés)

**Commit A** — `chore(deps): add anthropic + freezegun for Sol V1`
Fichier : `backend/requirements.txt`
```
anthropic>=0.40.0
freezegun>=1.5.0
```

**Commit B** — `fix(tests): auto-inject test secrets in conftest`
Fichier : `backend/tests/conftest.py` (en tête, avant tout import)
```python
import os
os.environ.setdefault("PROMEOS_JWT_SECRET", "test_only_not_for_production")
os.environ.setdefault("SECRET_KEY", "test_only_not_for_production")
os.environ.setdefault("SOL_SECRET_KEY", "test_only_not_for_production")
os.environ.setdefault("DEMO_MODE", "true")
```

Validation : `cd backend && python -m pytest --collect-only` doit retourner 0 erreur de collecte.

---

## Phase 0 — Audit read-only (STOP GATE 0)

**Durée estimée** : 0.5j

### 0.1 — Vérifier que les commits préparatoires sont mergés
```bash
grep -E "^anthropic|^freezegun" backend/requirements.txt
grep "PROMEOS_JWT_SECRET" backend/tests/conftest.py
cd backend && python -m pytest --collect-only 2>&1 | tail -5
```
Si échec, stopper et remonter.

### 0.2 — Établir baseline tests
```bash
cd backend && python -m pytest --collect-only -q 2>&1 | tail -3
cd frontend && npx vitest --run 2>&1 | tail -3
```
Noter le nombre exact de tests passants (sera la baseline de référence pour Gate 4 "régression ≥ baseline").

### 0.3 — Livrable Gate 0
Produire `docs/sol/sprint_1_2_progress.md` (append-only durant sprint) avec :
- Baseline tests backend : X tests, Y passing
- Baseline tests frontend : X tests, Y passing
- Confirmation des patterns référencés dans `DECISIONS_LOG.md` trouvés dans le repo (grep checks)
- Questions ouvertes détectées pendant l'exploration (aucune décision à prendre, juste flagger)

**STOP GATE 0** : présenter le bilan, attendre validation avant Phase 1.

---

## Phase 1 — Modèles DB + migration custom (STOP GATE 1)

**Durée estimée** : 2j

### Fichiers à créer
```
backend/models/sol.py                             # 4 classes SQLAlchemy
backend/models/base.py                            # AJOUTER CreatedAtOnlyMixin (ne pas recréer le fichier)
backend/database/migrations.py                    # AJOUTER bloc _migrate_sol_v1_foundations()
backend/tests/sol/__init__.py
backend/tests/sol/test_models_sol.py
backend/tests/sol/test_sol_append_only.py
```

### 1.1 — Ajouter `CreatedAtOnlyMixin` dans `models/base.py`
```python
class CreatedAtOnlyMixin:
    """Mixin pour tables append-only : created_at seul, pas d'updated_at."""
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```
Ne pas toucher `TimestampMixin` ni `SoftDeleteMixin` existants.

### 1.2 — `backend/models/sol.py` — 4 classes

**`SolActionLog`** (append-only)
- `id` Integer PK autoincrement
- `org_id` Integer FK → `organisations.id`
- `user_id` Integer FK → `users.id` (ou équivalent existant)
- `correlation_id` String(36) indexed (UUID Python)
- `intent_kind` String(64) — enum applicatif IntentKind
- `action_phase` String(32) — enum applicatif ActionPhase (8 valeurs)
- `inputs_hash` String(64) — SHA256
- `plan_json` Column(JSON) — pas JSONB
- `state_before` Column(JSON, nullable=True)
- `state_after` Column(JSON, nullable=True)
- `outcome_code` String(64, nullable=True)
- `outcome_message` Text(nullable=True)
- `llm_calls` Column(JSON, nullable=True, default=list)
- `confidence` Numeric(4, 2, nullable=True)
- `anonymized` Boolean default=False
- `anonymized_at` DateTime(timezone=True, nullable=True)
- Hérite `CreatedAtOnlyMixin` (pas `TimestampMixin`)
- Index : `(org_id, created_at DESC)`, `(correlation_id)`, `(user_id)`

**Event listener append-only** (dans `models/sol.py` au bas du fichier) :
```python
from sqlalchemy import event

class AppendOnlyViolation(Exception):
    """Levée quand un UPDATE est tenté sur une table append-only Sol."""

@event.listens_for(SolActionLog, 'before_update')
def _block_sol_action_log_update(mapper, connection, target):
    # Autoriser uniquement anonymization (change anonymized + anonymized_at)
    from sqlalchemy import inspect
    state = inspect(target)
    changed = {attr.key for attr in state.attrs if attr.history.has_changes()}
    if changed and not changed.issubset({'anonymized', 'anonymized_at'}):
        raise AppendOnlyViolation(
            f"SolActionLog is append-only. Attempted changes: {changed}"
        )
```

**`SolPendingAction`**
- `id` Integer PK autoincrement
- `correlation_id` String(36) UNIQUE indexed
- `org_id` Integer FK
- `user_id` Integer FK
- `intent_kind` String(64)
- `plan_json` Column(JSON)
- `scheduled_for` DateTime(timezone=True) indexed WHERE status='waiting'
- `cancellation_token` String(64) UNIQUE
- `status` String(32) default='waiting' — values: waiting/executing/executed/cancelled
- `executed_at` DateTime(timezone=True, nullable=True)
- `cancelled_at` DateTime(timezone=True, nullable=True)
- `cancelled_by` Integer FK → users.id (nullable=True)
- Hérite `CreatedAtOnlyMixin`

**`SolConfirmationToken`**
- `token` String(64) PK
- `correlation_id` String(36) UNIQUE
- `plan_hash` String(64)
- `user_id` Integer FK
- `org_id` Integer FK
- `expires_at` DateTime(timezone=True) — TTL 5 min à la création
- `consumed` Boolean default=False
- `consumed_at` DateTime(timezone=True, nullable=True)
- Hérite `CreatedAtOnlyMixin`

**`SolOrgPolicy`**
- `org_id` Integer PK FK → organisations.id
- `agentic_mode` String(40) default='preview_only' — enum : consultative_only/preview_only/full_agentic/full_agentic_with_dual_validation
- `dry_run_until` DateTime(timezone=True, nullable=True)
- `dual_validation_threshold` Numeric(12, 2, nullable=True)
- `confidence_threshold` Numeric(4, 2) default=0.85
- `grace_period_seconds` Integer default=900
- `tone_preference` String(8) default='vous'
- `updated_at` DateTime(timezone=True) onupdate=now

### 1.3 — Bloc migration dans `backend/database/migrations.py`

Ajouter fonction `_migrate_sol_v1_foundations(engine, inspector)` suivant exactement le pattern V113/V114. Exemple squelette :
```python
def _migrate_sol_v1_foundations(engine, inspector):
    """Sol V1 foundations: 4 append-only tables + org policy."""
    existing_tables = set(inspector.get_table_names())

    if 'sol_action_log' not in existing_tables:
        # create via raw SQL compatible SQLite+Postgres
        ...
    if 'sol_pending_action' not in existing_tables:
        ...
    # etc.
```
Puis appeler dans `run_migrations()` : `_migrate_sol_v1_foundations(engine, inspector)`.

**NB** : sur fresh DB, `Base.metadata.create_all()` crée les tables via les modèles SQLAlchemy. Le bloc migration sert uniquement aux installs existants.

### 1.4 — Tests (>95% couverture)

`test_models_sol.py` — 8 tests min :
- `test_sol_action_log_json_serialization` — plan_json/state_before/after round-trip
- `test_sol_pending_action_unique_correlation_id`
- `test_sol_confirmation_token_expiry_in_past_invalid`
- `test_sol_confirmation_token_consumed_rejected`
- `test_sol_org_policy_defaults` — 0.85 confidence, 900s grace, 'vous' tone, 'preview_only' mode
- `test_sol_org_policy_is_dry_run_active` — method sur modèle
- `test_sol_action_phase_enum_values` — 8 valeurs via `ActionPhase` Enum applicatif (Phase 2)
- `test_sol_tables_foreign_keys` — FK org_id vers organisations

`test_sol_append_only.py` — 3 tests min :
- `test_sol_action_log_update_blocked` — modifier outcome_code raise `AppendOnlyViolation`
- `test_sol_action_log_anonymization_allowed` — set anonymized=True + anonymized_at OK
- `test_sol_action_log_delete_allowed_but_logged` — DELETE autorisé (event listener on update only)

### 1.5 — Livrables Gate 1
- [ ] `backend/models/base.py` : `CreatedAtOnlyMixin` ajouté
- [ ] `backend/models/sol.py` : 4 classes + event listener
- [ ] `backend/database/migrations.py` : `_migrate_sol_v1_foundations` ajouté
- [ ] `backend/tests/sol/test_models_sol.py` + `test_sol_append_only.py` : 11+ tests verts
- [ ] `cd backend && python -m pytest tests/sol/ -v` : 100% green
- [ ] `cd backend && python -m pytest --collect-only` : tests totaux ≥ baseline Gate 0
- [ ] Commit atomique : `feat(sol-p1): Phase 1 — Modèles DB Sol V1 (append-only audit log, pending, tokens, org policy)`

**STOP GATE 1** : bilan → validation avant Phase 2.

---

## Phase 2 — Schemas Pydantic + utilitaires + frenchifier + boundaries (STOP GATE 2)

**Durée estimée** : 3j

### Fichiers à créer
```
backend/sol/__init__.py
backend/sol/schemas.py
backend/sol/utils.py
backend/sol/context.py
backend/sol/boundaries.py
backend/sol/voice.py
backend/sol/prompts/v1/classify_intent.txt      # stub vide, Sprint 7-8
backend/sol/prompts/v1/explain_plan.txt         # stub vide
backend/sol/prompts/v1/summarize_result.txt     # stub vide
backend/tests/sol/test_schemas.py
backend/tests/sol/test_utils.py
backend/tests/sol/test_voice.py
backend/tests/sol/test_boundaries.py
```

### 2.1 — `backend/sol/schemas.py`

- **`IntentKind`** (str, Enum) : INVOICE_DISPUTE, EXEC_REPORT, DT_ACTION_PLAN, AO_BUILDER, OPERAT_BUILDER, CONSULTATIVE_ONLY, **`DUMMY_NOOP`** (tests uniquement)
- **`ActionPhase`** (str, Enum) : PROPOSED, PREVIEWED, CONFIRMED, SCHEDULED, EXECUTED, CANCELLED, REVERTED, REFUSED
- **`Source`** (BaseModel) : kind, ref, freshness_hours: int, confidence: Optional[float]
- **`Warning`** (BaseModel) : code, message_fr
- **`ActionPlan`** (BaseModel, stricte) :
  - correlation_id: str (uuid4), intent: IntentKind, title_fr: str (5-120), summary_fr: str (10-500 + frenchified)
  - preview_payload: dict[str, Any]
  - inputs_hash: str (sha256 hex 64 chars)
  - confidence: float ∈ [0.0, 1.0]
  - grace_period_seconds: int ≥ 0
  - reversible: bool
  - requires_dual_validation: bool
  - estimated_value_eur: Optional[float]
  - estimated_time_saved_minutes: Optional[int]
  - sources: list[Source]
  - warnings: list[Warning]
- **`PlanRefused`** (BaseModel) : correlation_id, intent, reason_code, reason_fr (non-vide, frenchified), remediation_fr: Optional, missing_data: Optional[list[str]]
- **`ExecutionResult`** (BaseModel) : correlation_id, outcome_code, outcome_message_fr, state_before, state_after, reversal_instructions: Optional[dict]
- **`SolContext`** (BaseModel, arbitrary_types_allowed=True) : org_id: int, user_id: int, correlation_id: str, now: datetime, org_policy_dict: dict (DTO léger), scope_site_id: Optional[int], last_3_actions: list[dict]

### 2.2 — `backend/sol/utils.py`

```python
def now_utc() -> datetime:
    """datetime UTC-aware. Jamais utcnow()."""
    return datetime.now(timezone.utc)

def hash_inputs(*args) -> str:
    """SHA256 deterministic des inputs sérialisables JSON-canonical."""
    import hashlib, json
    payload = json.dumps(args, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

def generate_correlation_id() -> str:
    return str(uuid.uuid4())

def generate_cancellation_token() -> str:
    """32 bytes url-safe — lien one-click email annulation."""
    return secrets.token_urlsafe(32)

def generate_confirmation_token(correlation_id: str, plan_hash: str, user_id: int) -> str:
    """HMAC-SHA256 signé avec SOL_SECRET_KEY, encodage url-safe."""
    secret = os.environ["SOL_SECRET_KEY"].encode('utf-8')
    payload = f"{correlation_id}|{plan_hash}|{user_id}|{now_utc().isoformat()}".encode('utf-8')
    sig = hmac.new(secret, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"|" + sig).decode('ascii').rstrip('=')

def verify_confirmation_token(token: str, correlation_id: str, plan_hash: str) -> Tuple[bool, Optional[int]]:
    """Retourne (valid, user_id) ou (False, None)."""
    # decode + compare HMAC + vérifier correlation_id et plan_hash matchent

def fmt_eur(amount: float) -> str:
    """1847.2 → '1 847,20 €' avec U+00A0 milliers + U+202F fine avant €."""

def fmt_mwh(amount: float) -> str:
    """432.6 → '432,6 MWh' avec U+00A0 avant unité."""

def fmt_pct(ratio: float, precision: int = 1, signed: bool = True) -> str:
    """0.084 → '+8,4 %' (signed) ou '8,4 %'. Fine U+202F avant %."""
```

### 2.3 — `backend/sol/voice.py`

**`frenchifier(text: str) -> str`** — pure, idempotente. Règles :
- Espace ordinaire avant `:` `;` `!` `?` → remplacer par U+202F (fine insécable)
- Espace ordinaire avant `%` `€` `$` → U+202F
- Espaces entre chiffres milliers (`1847` → `1 847`) — seulement si nombre ≥ 1000 isolé
- `"..."` → `« ... »` avec U+00A0 après `«` et avant `»`
- `--` ou ` - ` entre deux mots → `—` (tiret cadratin U+2014)
- `2024-2026` dans contexte intervalle → `2024–2026` (tiret demi-cadratin U+2013) [heuristique : 4 chiffres + `-` + 4 chiffres]
- Ordinaux `1er`, `2eme`, `3ème` → `1ᵉʳ`, `2ᵉ`, `3ᵉ`
- Majuscules : `Economie` → `Économie`, `A faire` → `À faire` (dictionnaire statique de 30 mots FR courants)
- **NE PAS** modifier les mots techniques sentinelles : `TURPE`, `kWh`, `MWh`, `ARENH`, `CTA`, `TVA`, `CEE`, `ENEDIS`, `GRDF`, `PDL`, `PCE`, `TRVE`, `DJU`, `OID`

**`SOL_VOICE_TEMPLATES_V1`** (dict) : 30 templates min couvrant situations S01-S50 du voice guide. Clés `(voice_kind, situation_code)`, valeurs strings avec placeholders `{var}`.

**`render_template(key: tuple, ctx: dict) -> str`** — charge template, substitue vars (f-string safe), applique `frenchifier()`.

### 2.4 — `backend/sol/boundaries.py`

```python
OUT_OF_SCOPE_PATTERNS = [
    (r"(?i)\b(acheter|investir|trader|crypto|bourse)\b", "financial_advice"),
    (r"(?i)(valide juridiquement|ester en justice|contrat.*valable)", "legal_advice"),
    (r"(?i)(tu as bien dormi|ça va|raconte-moi)", "personal"),
]

def is_out_of_scope(question_fr: str) -> Tuple[bool, Optional[str]]:
    """Retourne (True, reason_code) ou (False, None)."""

BOUNDARY_RESPONSES = {
    "financial_advice": "Je peux comparer les scénarios...",
    "legal_advice": "Je peux vérifier la conformité technique...",
    "personal": "Je suis là pour les questions énergie et réglementation...",
}
```
Toutes les chaînes passées par `frenchifier()` à l'import.

### 2.5 — `backend/sol/context.py`

```python
@dataclass
class SolContextData:
    org_id: int
    user_id: int
    correlation_id: str
    now: datetime
    org_policy: dict  # DTO léger
    scope_site_id: Optional[int]
    last_3_actions: list[dict]

def build_sol_context(request, auth, db, correlation_id: Optional[str] = None) -> SolContextData:
    """Construit SolContextData depuis request FastAPI + auth + db."""
    org_id = resolve_org_id(request, auth, db)  # pattern body call
    # récupérer user_id de auth, org_policy via SolOrgPolicy, last_3_actions via SolActionLog
    ...
```

### 2.6 — Tests (>95% couverture)

- `test_schemas.py` : 8 tests — bornes ActionPlan (confidence 0-1, length title/summary), PlanRefused vide = invalid, ExecutionResult state_before/after JSON
- `test_utils.py` : 15 tests — hash_inputs idempotence, fmt_eur/mwh/pct (vérif char codes 0x202F fine + 0x00A0 milliers), tokens génération/verify (tampering détecté, expiry, wrong plan_hash)
- `test_voice.py` : 20 cas — frenchifier sur échantillon S01-S50, templates render avec substitution, idempotence (`frenchifier(frenchifier(x)) == frenchifier(x)`)
- `test_boundaries.py` : 15 questions test couvrant 3 patterns + cases edge (question neutre énergie passe through)

### 2.7 — Livrables Gate 2
- [ ] Tous fichiers créés
- [ ] `cd backend && python -m pytest tests/sol/ -v` : 58+ tests verts (11 P1 + 47 P2)
- [ ] Couverture `backend/sol/` > 95%
- [ ] Grep `datetime.utcnow` dans `backend/sol/` : 0 hit
- [ ] `.env.example` inclut `SOL_SECRET_KEY=change-me-in-production`
- [ ] Commit : `feat(sol-p2): Phase 2 — Schemas Pydantic + utils + frenchifier + boundaries + voice templates V1`

**STOP GATE 2** : validation bilan + git diff review.

---

## Phase 3 — Planner + Validator + Scheduler (JobOutbox-based) + Audit (STOP GATE 3)

**Durée estimée** : 4j

### Fichiers à créer
```
backend/sol/planner.py
backend/sol/validator.py
backend/sol/scheduler.py
backend/sol/audit.py
backend/sol/engines/__init__.py
backend/sol/engines/base.py
backend/sol/engines/_dummy.py             # DummyEngine, IntentKind.DUMMY_NOOP
backend/models/job_outbox.py              # MODIF : ajouter JobType.SOL_EXECUTE_PENDING_ACTION
backend/jobs/worker.py                    # MODIF : dispatch vers execute_sol_action
backend/tests/sol/test_planner.py
backend/tests/sol/test_validator.py
backend/tests/sol/test_scheduler.py
backend/tests/sol/test_audit.py
backend/tests/sol/test_engine_base.py
backend/tests/sol/test_sol_job_dispatch.py
```

### 3.1 — `backend/sol/engines/base.py`

Contrat abstrait + registry. Voir DECISIONS_LOG P1-12 : `DummyEngine.KIND = IntentKind.DUMMY_NOOP` (pas CONSULTATIVE_ONLY).

### 3.2 — `backend/sol/planner.py`

`propose_plan(ctx, intent, params)` : dispatch engine, check org_policy (`consultative_only` mode → refuse sauf CONSULTATIVE_ONLY), append-only log phase=PROPOSED.

### 3.3 — `backend/sol/validator.py`

`validate_plan_for_execution(ctx, plan, token)` avec exceptions : `InvalidToken`, `PlanAltered`, `DryRunBlocked`, `DualValidationMissing`. Semantique `dry_run_until` : **seule `execute` est bloquée**, `propose`/`preview` continuent de fonctionner.

### 3.4 — `backend/sol/scheduler.py`

**Réutilisation JobOutbox** (DÉCISION P1-2) :
```python
from models.job_outbox import JobType, JobStatus
from jobs.worker import enqueue_job

def schedule_pending_action(ctx, plan, confirmation_token) -> SolPendingAction:
    """
    1. Consomme le confirmation_token (consumed=True)
    2. Crée SolPendingAction (scheduled_for = now + grace_period)
    3. Enqueue JobOutbox (JobType.SOL_EXECUTE_PENDING_ACTION)
    4. Log phase=SCHEDULED
    5. Envoie email (mock en dev, MailerWorker plus tard)
    """
    enqueue_job(db, JobType.SOL_EXECUTE_PENDING_ACTION, {
        "correlation_id": ctx.correlation_id,
        "scheduled_for_iso": scheduled_for.isoformat(),
    }, priority=3)
```

**`JobType.SOL_EXECUTE_PENDING_ACTION`** — ajouter au enum existant dans `models/job_outbox.py`.

**Dispatcher worker** — modifier `backend/jobs/worker.py` `process_one()` pour dispatcher :
```python
if job.job_type == JobType.SOL_EXECUTE_PENDING_ACTION:
    from sol.scheduler import execute_due_sol_action
    payload = json.loads(job.payload_json)
    scheduled_for = datetime.fromisoformat(payload['scheduled_for_iso'])
    if datetime.now(timezone.utc) >= scheduled_for:
        execute_due_sol_action(db, payload['correlation_id'])
        job.status = JobStatus.DONE
    else:
        # re-queue — garder pending, ne pas marquer DONE
        return
```

`cancel_pending_action(cancellation_token, user_id=None)` : accepte sans auth si token valide (one-click email), log phase=CANCELLED, mark JobOutbox entry as SKIPPED.

### 3.5 — `backend/sol/audit.py`

- `log_action(ctx, phase, plan_or_refusal, outcome=None) -> SolActionLog` : INSERT append-only
- `get_audit_trail(ctx, correlation_id) -> list[SolActionLog]` : chain par correlation_id
- `check_audit_integrity(db, window_hours=1) -> list[str]` : job hourly (pas cron, lancé via JobOutbox ou script)

### 3.6 — Tests critiques (30+ tests)

**Test clé** : `test_propose_schedule_cancel_cycle` — cycle complet avec `DummyEngine`, 100% déterministe via `freezegun.freeze_time`.
Également `test_propose_schedule_execute_cycle` — cycle exécuté via worker manuel (pas cron).

Test org-scoping Phase 3 : engine registry safe cross-org (pas de leak plan_json d'une org vers une autre via correlation_id).

### 3.7 — Livrables Gate 3
- [ ] 30+ tests Sol verts, couverture `backend/sol/` > 95%
- [ ] Audit log append-only vérifié (11 tests Phase 1 + 3 nouveaux cycle)
- [ ] Cycle propose → schedule → cancel testé via DummyEngine
- [ ] Cycle propose → schedule → execute via worker testé (freezegun)
- [ ] Commit : `feat(sol-p3): Phase 3 — Planner + Validator + Scheduler (JobOutbox) + Audit + DummyEngine`

**STOP GATE 3** : démo script Python du cycle complet → validation.

---

## Phase 4 — Routes API + sécurité org-scoping + monitoring (STOP GATE 4)

**Durée estimée** : 3j

### Fichiers à créer/modifier
```
backend/routes/sol.py                             # propose, preview, confirm, cancel, pending
backend/routes/sol_audit.py                       # audit trail, export CSV
backend/routes/sol_policy.py                      # org policy (admin only)
backend/main.py                                   # MODIF : include_router Sol (autorisé)
backend/tests/sol/test_routes_sol.py
backend/tests/sol/test_routes_sol_audit.py
backend/tests/sol/test_routes_sol_policy.py
backend/tests/sol/test_org_scoping_sol.py
```

### 4.1 — Pattern de route (NON NÉGOCIABLE)

```python
@router.post("/api/sol/propose", response_model=Union[ActionPlan, PlanRefused], status_code=201)
async def propose(
    body: ProposeRequest,
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(request, auth, db)   # appel body, pas Depends
    ctx = build_sol_context(request, auth, db)
    result = propose_plan(ctx, body.intent, body.params)
    logger = logging.getLogger("promeos.sol")
    logger.info("sol_propose", extra={
        "correlation_id": ctx.correlation_id,
        "org_id": ctx.org_id,
        "intent": body.intent.value,
        "outcome": "plan_generated" if isinstance(result, ActionPlan) else "refused",
    })
    return result
```

### 4.2 — Endpoints (10 au total, dont 2 stubs 501)

```
POST   /api/sol/propose            → 201 ActionPlan | PlanRefused
POST   /api/sol/preview            → 200 ActionPlan complet
POST   /api/sol/confirm            → 202 {pending_action_id, scheduled_for}
POST   /api/sol/cancel             → 200 {cancelled_at}
GET    /api/sol/pending            → 200 list[SolPendingActionDTO]
GET    /api/sol/audit              → 200 paginated list
GET    /api/sol/audit/export       → 200 text/csv
GET    /api/sol/policy             → 200 SolOrgPolicyDTO (admin-only)
PUT    /api/sol/policy             → 200 SolOrgPolicyDTO (admin-only)
POST   /api/sol/ask                → 501 Not Implemented (Sprint 7-8 stub)
POST   /api/sol/headline           → 501 Not Implemented (Sprint 7-8 stub)
```

### 4.3 — Tests org-scoping CRITIQUE

`test_org_scoping_sol.py` — sur CHAQUE route :
- [ ] Requête sans org_id (DEMO_MODE=false) → 401
- [ ] Requête org A ne peut pas lire correlation_id org B → 404 ou 403
- [ ] PUT /policy avec user non-admin → 403

Ce fichier est bloquant : 1 fail = rejet du sprint.

### 4.4 — Livrables Gate 4
- [ ] 10 endpoints (8 fonctionnels + 2 stubs 501)
- [ ] 15+ tests routes, 100% verts
- [ ] Tests org-scoping cross-tenant : 9+ tests verts (1 par endpoint fonctionnel)
- [ ] Export CSV audit fonctionnel (testé format + anti-injection `=+-@` prefix)
- [ ] Tests total Sol : **70+** verts, couverture > 95%
- [ ] Régression : `pytest backend/` total ≥ baseline Gate 0
- [ ] Régression : `npx vitest` frontend intact (aucune modif frontend ce sprint)
- [ ] Commit : `feat(sol-p4): Phase 4 — Routes API Sol V1 + org-scoping + audit/policy/pending + CSV export`

**STOP GATE 4** : bilan complet Sprint 1-2 + check régression → validation → merge dans main (via PR GitHub standard).

---

## Règles non-négociables Sprint 1-2

1. **Scope fichiers** — toucher uniquement : `backend/models/sol.py`, `backend/models/base.py` (juste +CreatedAtOnlyMixin), `backend/database/migrations.py` (juste +_migrate_sol_v1_foundations), `backend/sol/**`, `backend/routes/sol*.py`, `backend/main.py` (juste +include_router), `backend/models/job_outbox.py` (+JobType.SOL_EXECUTE_PENDING_ACTION), `backend/jobs/worker.py` (+dispatcher Sol), `backend/tests/sol/**`, `backend/tests/conftest.py` (commit B préparatoire), `backend/requirements.txt` (commit A préparatoire), `.env.example` (+SOL_SECRET_KEY).
2. **Commits atomiques** — 1 par Phase + 2 préparatoires. Jamais de fourre-tout.
3. **`git status` clean avant chaque STOP GATE**.
4. **`datetime.now(timezone.utc)` uniquement** — pas `utcnow()`, pas `datetime.now(UTC)`.
5. **Aucun hardcoding chiffres réglementaires** — source = `backend/config/tarifs_reglementaires.yaml`.
6. **Aucun LLM appelé ce sprint** — `backend/sol/prompts/v1/*.txt` = stubs vides, remplis Sprint 7-8.
7. **`frenchifier()` appliqué sur toutes chaînes FR Sol** — grep CI vérifie : 0 `"..."` droit dans `SOL_VOICE_TEMPLATES_V1`.
8. **Couverture `backend/sol/` > 95%**. Check via `pytest --cov=sol`.
9. **MCP obligatoires** : Context7 avant pattern FastAPI/SQLAlchemy/Pydantic, `/code-review` avant chaque commit, `/simplify` si fichier > 250 lignes.
10. **Si ambigu, poser question dans bilan, ne pas inventer**. Zéro hardcoding "plausible".

---

## Definition of Done Sprint 1-2

- [ ] 2 commits préparatoires (deps + conftest) mergés
- [ ] 4 STOP GATES passés avec bilans validés
- [ ] 4 commits atomiques Phase 1-4 propres
- [ ] 70+ tests Sol verts, couverture > 95%
- [ ] Régression : tests verts ≥ baseline Gate 0 (backend + frontend)
- [ ] Aucune modification hors scope Sol (diff review manuel + CI guards)
- [ ] `backend/sol/` prêt pour Sprint 3 (première UI Sol + engine Invoice Dispute) sans refactor préalable
- [ ] `DECISIONS_LOG.md` reste source de vérité sur les choix pris

---

## Hors scope Sprint 1-2 (intentionnel)

- ❌ Aucun engine métier réel (Sprint 3-6)
- ❌ Pas de LLM Haiku appelé (Sprint 7-8)
- ❌ Pas d'UI frontend Sol (Sprint 3+)
- ❌ Pas de voice layer ambient (Sprint 7-8)
- ❌ Pas de conversation Mode 2 (Sprint 7-8)
- ❌ Pas de mail réel envoyé (mock en dev, vrai envoi Sprint 3)
- ❌ Pas de job anonymisation 3 ans (différé Sprint 3+, voir DECISIONS_LOG P1-10)
- ❌ Pas de PDF rapport comex (Sprint 5)

Ce sprint est **infrastructure backend pure**. Son succès = tout le reste devient possible.

---

## En cas de blocage

Si un point ne peut être résolu sans info supplémentaire :
1. Ne pas bloquer le reste du sprint
2. Créer un `TODO: blocker — [question précise]` dans le code
3. Lister les blockers dans le bilan du STOP GATE concerné
4. Continuer autres tâches de la phase

Questions déjà anticipées et tranchées dans `DECISIONS_LOG.md`. Si nouveau blocker apparaît, appliquer la même rigueur.
