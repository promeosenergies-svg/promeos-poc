# Sol V1 — Decisions log (pre-Sprint 1)

**Date** : 2026-04-17
**Contexte** : décisions prises en revue conjointe après audit 3 agents (voir `AUDIT_SOL_V1_FINDINGS.md`).
**Statut** : locked — la version applicable du prompt est `PROMPT_SOL_V1_SPRINT_1-2_APPLIED.md`. L'original `PROMPT_SOL_V1_SPRINT_1-2.md` reste comme référence.

---

## Bloc 1 — Data model (P0-1, P0-2, P0-5)

### P0-1 · Primary keys : `Integer autoincrement` (pas UUID)
**Décision** : option A.
**Raison** : 100% des 60+ modèles PROMEOS utilisent `Column(Integer, primary_key=True, autoincrement=True)`. FK `org_id UUID` vers `organisations.id INT` crasherait. `gen_random_uuid()` KO sur SQLite (DB dev par défaut). L'obfuscation UUID n'apporte rien pour un audit log interne : scope sécurité couvert par org_id.
**Impact** : les 4 tables Sol (`sol_action_log`, `sol_pending_action`, `sol_confirmation_token`, `sol_org_policy`) utilisent `Integer autoincrement`. `correlation_id` reste string UUID Python (non-PK, juste tracking).

### P0-2 · Append-only : `JSON` + SQLAlchemy event listener (pas JSONB + trigger)
**Décision** : option A.
**Raison** : CI tourne SQLite en mémoire. JSONB + `CREATE TRIGGER` Postgres-only = tests impossibles. Event listener `@event.listens_for(mapper, 'before_update')` fonctionne sur les 2 DB, lève `AppendOnlyViolation`.
**Trade-off assumé** : event listener contournable par raw SQL. Compensé par test CI "grep no raw UPDATE on sol_action_log in backend/".

### P0-5 · Mixin append-only : créer `CreatedAtOnlyMixin`
**Décision** : option A.
**Raison** : `TimestampMixin` existant inclut `updated_at` avec `onupdate=now()`. Incompatible sémantique avec append-only.
**Implémentation** : ajouter dans `backend/models/base.py` un nouveau mixin 5 lignes exposant uniquement `created_at` avec `default=lambda: datetime.now(timezone.utc)`. Réutilisable ailleurs (autres tables audit éventuelles).

---

## Bloc 2 — Migration strategy (P0-3)

### P0-3 · Pattern custom `database/migrations.py` V112-V114 (pas Alembic)
**Décision** : option B.
**Raison** : Alembic = no-op baseline dans le repo. La vraie source de vérité = `database/migrations.py` (2200 LOC, pattern éprouvé V112, V113, V114 — 645 tests verts sans régression). Ouvrir Alembic correctement = 1-2j sec + régénérer baseline. Pas le moment à 10 semaines de la seed.
**Implémentation** :
- Modèles Sol déclarés dans `backend/models/sol.py` → `Base.metadata.create_all()` les pose sur fresh DB
- Bloc idempotent dans `backend/database/migrations.py` : `CREATE TABLE IF NOT EXISTS sol_*` pour installs existants, style V113/V114
- Appelé automatiquement par `run_migrations(engine)` dans `main.py:239`
**Dette assumée** : ajouter au backlog tech debt post-seed "Migrer `database/migrations.py` vers Alembic + régénérer baseline" (budget 1 semaine T3 2026).

---

## Bloc 3 — API patterns (P0-4, P0-10)

### P0-4 · `resolve_org_id` appelé dans body (pas `Depends`)
**Décision** : option A.
**Raison** : signature actuelle `resolve_org_id(request, auth, db, *, org_id_override=None)` incompatible avec `Depends()` direct (FastAPI ne peut pas injecter `auth: Optional[AuthContext]` ni `db: Session` sans `Depends` explicite). Pattern existant confirmé dans `actions.py:103`, `aper.py:30,49`, `bacs.py:55`, `billing.py`, etc.
**Implémentation routes Sol** :
```python
@router.post("/api/sol/propose")
async def propose(
    body: ProposeRequest,
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    org_id = resolve_org_id(request, auth, db)
    # ... logic ...
```

### P0-10 · Fix conftest.py pour setdefault test secrets
**Décision** : option A.
**Raison** : `services/iam_service.py:35` lit `PROMEOS_JWT_SECRET` à l'import → `pytest --collect-only` plante. Bloquant Gate 4 "régression ≥ baseline".
**Implémentation** : commit pré-Sprint 1 séparé `fix(tests): auto-inject test secrets in conftest`. 10 lignes en tête de `backend/tests/conftest.py` :
```python
import os
os.environ.setdefault("PROMEOS_JWT_SECRET", "test_only_not_for_production")
os.environ.setdefault("SECRET_KEY", "test_only_not_for_production")
os.environ.setdefault("DEMO_MODE", "true")
# autres defaults utiles aux tests
```
**Bénéfice** : universel (pas Sol-spécifique), améliore DX de toute l'équipe.

---

## Bloc 4 — Design system / UI (P0-6, P0-7, P0-8) — **impact Sprint 3+**

**Cadrage stratégique** : Sol V1 = différenciant démo levée seed 30/06/2026. Le mockup éditorial (ivoire crème, Fraunces, palette calme) **est** l'arme de pitch. Runway 10 semaines ne permet pas refactor DS complet (3-4 sem). Donc **isolation contrôlée**, pas remplacement.

### P0-6 · Rail+Panel : garder V7, restyler dans `.sol-surface`
**Décision** : option B.
**Raison** : V7 = 11 PRs mergées (#193→#213), 6 modules lucide-react. Jeter = gâchis + régression 60+ pages.
**Implémentation** : la structure Rail+Panel reste intacte. Un wrapper `<SolSurface>` au niveau `<AppShell>` applique les styles Sol uniquement sur les routes cockpit Sol via classe CSS `.sol-surface`.

### P0-7 · Design tokens : namespace `sol.*` + `.sol-surface` scoping strict
**Décision** : option B.
**Raison** : migrer tout = 3-4 sem + casse `V24DesignSystem.test.js`. Aligner mockup sur Tailwind bleu = perdre wow factor.
**Implémentation** :
```js
// frontend/src/ui/tokens.js — ajout sans toucher à l'existant
export const solTokens = {
  bg: { canvas: '#FAF6F0', paper: '#FFFEFB', panel: '#F3ECE0' },
  ink: { 900: '#1C1B18', 700: '#3A3731', 500: '#6B665C', 400: '#8F8A7E' },
  accent: { calme: '#2F6B5E', attention: '#A06B1A', afaire: '#B8552E', succes: '#2E6B4A' },
  rule: '#D9D2C1',
};
```
CSS scoping strict : tous les sélecteurs Sol commencent par `.sol-surface`. Tokens PROMEOS existants intacts.

### P0-8 · Fonts : subset self-hosted, chargement global ~200 ko
**Décision** : option B.
**Raison** : chargement route-based cause FOUT cross-route. Chargement complet = 500-800 ko too much.
**Implémentation** :
- Fraunces 400/500 + italic, opsz statique 24pt → ~80 ko
- DM Sans 400/500/600 → ~70 ko
- JetBrains Mono 400/500 tabular-nums → ~45 ko
- **Total ~195 ko**, `font-display: swap`, self-hosted dans `frontend/public/fonts/` (pas Google Fonts EU tracking pour RGPD).

---

## Bloc 5 — Dépendances (P0-9)

### P0-9 · `anthropic` SDK + `freezegun` ajoutés maintenant
**Décision** : option A.
**Raison** : anthropic nécessaire Sprint 7-8, ajout anticipé évite prompt-pollution future. `freezegun` nécessaire pour tests scheduler Windows déterministes.
**Implémentation** : `requirements.txt` :
```
anthropic>=0.40.0
freezegun>=1.5.0
```
Commit pré-Sprint 1 séparé `chore(deps): add anthropic + freezegun for Sol V1`.

---

## Décisions P1

### P1-2 · Scheduler : réutiliser `JobOutbox` (pas APScheduler)
**Décision** : option A.
**Raison** : introduire APScheduler en parallèle du `JobOutbox` worker = 2 systèmes d'exécution différée concurrents, risque désynchro + double-exécution. Pattern existant `backend/jobs/worker.py` + `backend/models/job_outbox.py` fonctionne, éprouvé.
**Implémentation** :
- Ajouter `JobType.SOL_EXECUTE_PENDING_ACTION` dans enum
- `schedule_pending_action()` appelle `enqueue_job(db, JobType.SOL_EXECUTE_PENDING_ACTION, payload={correlation_id, scheduled_for_iso}, priority=3)`
- Worker `process_one` dispatche vers `execute_sol_action(correlation_id)` si `datetime.now(tz.utc) >= scheduled_for`, sinon re-queue
- Si `JobOutbox.scheduled_for` n'existe pas : ajouter la colonne via migration custom, ou stocker dans payload et gérer en applicatif

### P1-3 · `SOL_SECRET_KEY` : nouvelle var env dédiée
**Décision** : option A.
**Raison** : isolation cryptographique propre. Rotation HMAC Sol ne doit pas casser JWT auth.
**Implémentation** : `.env.example` +1 ligne `SOL_SECRET_KEY=change-me-in-production`. `backend/sol/utils.py` lit via `os.environ["SOL_SECRET_KEY"]`. `conftest.py` setdefault pour tests.

### P1-5 · Timing : 2.5 semaines full scope (pas descope)
**Décision** : option B.
**Raison** : Sol V1 = différenciant démo. Pas la peine de couper maintenant pour gagner 3 jours. Gate 4 garde CSV audit export + 30 templates voice V1.

### P1-10 · Rétention 3 ans / anonymisation : différée Sprint 3+
**Décision** : option B.
**Raison** : hors scope fondations Sprint 1-2. Infra en place (colonne `anonymized` + `anonymized_at` dans `sol_action_log` depuis Phase 1), mais job cron de production différé. RGPD compliance V1 beta acceptable sans job automatique — 3 ans = horizon long.
**Implémentation** : colonnes créées Phase 1. Job `anonymize_old_sol_logs(db)` à écrire en Sprint 3+ (~30 lignes). Tracé dans backlog Sol V2.

---

## Autres P1 non discutés (décisions appliquées par défaut dans prompt patché)

- **P1-1 datetime convention** : aligner sur `datetime.now(timezone.utc)` (convention existante, 381 occurrences). Ne PAS introduire `from datetime import UTC` (2e convention) dans le scope Sol. Les 38 violations `utcnow()` hors scope Sol restent dette différée.
- **P1-4 Monitoring** : réutiliser `cx_logger` pattern (9 fichiers existants), pas Prometheus. Log structuré via `logging.getLogger("promeos.sol")` + `extra={...}` dict.
- **P1-6 Règle R8 jargon Surface** : assouplir — les termes techniques (TURPE, CTA, accise T1/T2, OID, PDL, M023) **autorisés** en Surface mais **obligatoirement accompagnés d'un tooltip/glossaire**. Le guide éditorial est updated en conséquence.
- **P1-7 Grammaire FR U+202F** : `frenchifier()` créé Phase 2 Sprint 1-2 côté backend (`backend/sol/voice.py`), miroir frontend Sprint 3+ (`frontend/src/utils/frenchify.js`).
- **P1-8 Émojis drawer critique** : remplacer 📎 par `<Paperclip/>` lucide-react dans mockups — tracé comme rework Sprint 3 UI.
- **P1-9 Layer Surface/Inspect/Expert** : décision Sprint 3+ UI. Piste privilégiée : routes `/cockpit/sol/inspect/:dossierId` + `/cockpit/sol/expert` + context existant `ExpertModeContext`. Hors scope Sprint 1-2.
- **P1-11 SolContext.build() testable** : documenté dans prompt patché avec pattern `starlette.testclient.TestClient` + fixture `sol_ctx_factory`.
- **P1-12 DummyEngine kind** : créer `IntentKind.DUMMY_NOOP` exclusif tests (pas réutiliser CONSULTATIVE_ONLY).

---

## Recap deps à ajouter avant Sprint 1

Commits préparatoires (avant Phase 0 audit) :
1. `chore(deps): add anthropic + freezegun for Sol V1` — 2 lignes dans `requirements.txt`
2. `fix(tests): auto-inject test secrets in conftest` — 10 lignes dans `backend/tests/conftest.py`

Ensuite : Sprint 1-2 peut démarrer sur Gate 0 (audit read-only).

---

## Fichiers de référence (pour Sprint 1)

Patterns existants à **reproduire** :
- `backend/models/base.py` (mixins) — ajouter `CreatedAtOnlyMixin`
- `backend/middleware/auth.py:95` (`get_optional_auth`)
- `backend/services/scope_utils.py:81` (`resolve_org_id`, appel body)
- `backend/jobs/worker.py` + `backend/models/job_outbox.py` (scheduler pattern)
- `backend/database/migrations.py` pattern V113/V114 (migrations custom)
- `backend/routes/actions.py`, `aper.py`, `bacs.py` (exemples org-scoping)
- `backend/services/cx_logger.py` pattern monitoring
- `backend/services/json_logger.py` (format structure)

Patterns existants à **ne PAS reproduire** :
- `datetime.utcnow()` (38 violations héritées, ne pas propager)
- Column type UUID (1 modèle legacy, pas un pattern)

---

**Document figé. Les 15 décisions ci-dessus sont les données d'entrée du prompt applicable `PROMPT_SOL_V1_SPRINT_1-2_APPLIED.md`.**
