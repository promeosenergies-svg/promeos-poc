# Audit Sol V1 — Synthèse findings avant lancement sprint

**Date** : 2026-04-17
**Branche** : `claude/sol-v1-audit` (worktree `promeos-sol-audit/`, basé origin/main `711d3f5e`)
**Matériel audité** : 4 livrables fournis par Amine
- `SOL_V1_ARCHITECTURE.md` — architecture 14 sections (5 lois, 5 tables DB, 5 engines, LLM sandboxing, RGPD)
- `PROMPT_SOL_V1_SPRINT_1-2.md` — prompt 4 phases Gate 0→4, fondations 2 semaines
- `SOL_V1_VOICE_GUIDE.md` — guide éditorial 11 sections (8 règles, 50 situations types)
- `maquettes/cockpit-sol-v1.html` + `rapport-comex-sol-v1.html` (3 copies cockpit fournies — identiques, `_1` et `_2` = doublons inutiles)

**Méthode** : 3 agents SDK parallèles (architecture / prompt / voice+mockups) — chacun a lu les docs + inspecté le codebase PROMEOS réel.

---

## Verdict global

**Clarifications bloquantes avant Sprint 1.** L'architecture est saine dans son principe (5 lois, séparation moteur/planner/validator, audit append-only) mais contient **plusieurs hypothèses contredites par l'existant PROMEOS**. Le prompt Sprint 1-2 est sous-estimé d'environ **47%** en timing et contient 5 pièges bloquants pour un junior dev. Les maquettes sont **incompatibles** avec le design system V7 récemment mergé — à trancher.

**Aucun blocage majeur**, mais ~1 à 1.5 jour de cadrage/alignement avant de pouvoir ouvrir Sprint 1 avec confiance.

---

## P0 — Bloquants avant Sprint 1 (à trancher MAINTENANT)

### P0-1 · UUID vs autoincrement — convention contredite
**Finding** : 100% des tables PROMEOS utilisent `Column(Integer, primary_key=True, autoincrement=True)` (60+ modèles). Les 4 tables Sol proposées (`sol_action_log`, `sol_pending_action`, `sol_confirmation_token`, `sol_org_policy`) utilisent toutes **`UUID DEFAULT gen_random_uuid()`**.
**Impact** :
- `gen_random_uuid()` KO sur SQLite (DB dev par défaut, `database/connection.py:19`)
- FK `sol.org_id UUID` vers `organisations.id INT` → crash `run_migrations`
- Casse convention codebase (tests, seed, fixtures)

**Décision requise** :
- **(A)** Aligner Sol sur `Integer autoincrement` comme le reste (recommandé)
- **(B)** Utiliser `String(36)` + `uuid.uuid4()` portable Python (compromis)
- **(C)** Forcer migration Postgres obligatoire (lourd)

---

### P0-2 · JSONB + triggers SQL non portables
**Finding** : Architecture cite `JSONB` et `CREATE TRIGGER prevent_sol_log_update` en Postgres. SQLite ne supporte ni JSONB (just JSON), ni trigger syntax Postgres.
**Impact** : Tests CI tournent sur SQLite en mémoire (`pyproject.toml:71-81`). Trigger DDL Postgres = KO.
**Décision requise** :
- Remplacer JSONB par `JSON` générique SQLAlchemy (fonctionne sur les deux)
- Remplacer trigger DDL par `SQLAlchemy event listener @event.listens_for(mapper, 'before_update')` + contrainte applicative
- Accepter : event listener peut être contourné par raw SQL (vs trigger strict). Acceptable ou pas ?

---

### P0-3 · Alembic quasi-inexistant dans le repo
**Finding** : `backend/alembic/versions/` contient **une seule migration no-op baseline** (`2f83c6bebc57_initial_schema.py`). Le vrai système = **`backend/database/migrations.py`** (custom Python, 2200+ LOC, appelé `run_migrations(engine)` dans `main.py:239`). Les tables existantes naissent via `Base.metadata.create_all()`.
**Impact** : Le prompt Sprint 1 Phase 1 dit "écrire migration Alembic avec upgrade/downgrade". Un junior va créer une migration Alembic qui n'est ni lue ni jouée, OU va casser le boot s'il force `alembic upgrade head`.
**Décision requise** :
- **(A)** Sol est la 1ère migration Alembic "sérieuse" — on ouvre enfin ce chantier
- **(B)** Sol suit le pattern existant `database/migrations.py` custom (cohérence avec le repo)
- **(C)** Sol vit via `create_all` comme le reste + seed documenté (pragmatique V1)

---

### P0-4 · `resolve_org_id` n'est PAS un `Depends`
**Finding** : Prompt dit "Chaque route : `Depends(resolve_org_id)` — NON NÉGOCIABLE". Mais `services/scope_utils.py:81` définit `resolve_org_id(request, auth, db, *, org_id_override)` comme **fonction normale**, appelée dans le body des routes : `org_id = resolve_org_id(request, auth, db)`.
**Impact** : Junior va écrire `Depends(resolve_org_id)` → signature incompatible, crash au startup.
**Décision requise** : Corriger le prompt pour utiliser le pattern existant (appel dans body), OU créer un wrapper `depends_org_id()` réellement `Depends`-compatible.

---

### P0-5 · TimestampMixin incompatible append-only
**Finding** : `backend/models/base.py:14` → `TimestampMixin` inclut `updated_at` avec `onupdate=now()`. Un audit log append-only **ne peut pas avoir `updated_at`** (violation sémantique).
**Impact** : Prompt dit "réutiliser TimestampMixin" — contradictoire avec append-only.
**Décision requise** : Créer `CreatedAtOnlyMixin` dans `models/base.py` (override) ou ne pas hériter.

---

### P0-6 · Double Rail+Panel incompatible V7 récemment mergée
**Finding** : Maquette cockpit propose Rail (5 icônes glyphiques `◐ § ∿ € ⋯`) + Panel palette sable. V7 mergée (PRs #193→#213 d'après mémoire) a **6 modules lucide-react** (`LayoutDashboard`, `ShieldCheck`, `Zap`, `Building2`, `ShoppingCart`, `Settings`) avec tints `blue/emerald/indigo/ambre/violet/slate` Tailwind. Incompatible.
**Décision requise** :
- **(A)** Sol remplace V7 → refactor 3-4 semaines, régression sur 60+ pages
- **(B)** Sol garde V7 et ne change que style visuel (recommandé)
- **(C)** Sol vit isolé dans un wrapper `<SolSurface>` avec CSS scoping strict

---

### P0-7 · Design tokens incompatibles
**Finding** : Maquette utilise palette ivoire crème `#FAF6F0` + ink warm `#1C1B18` + calme `#2F6B5E`. Existant `frontend/src/ui/tokens.js` utilise `neutral.50→900` (gris froids Tailwind) + primary bleu `#3b82f6`. Les deux systèmes **ne peuvent pas coexister** sur même page.
**Décision requise** :
- **(A)** Migrer tout le DS (budget 3-4 semaines)
- **(B)** Namespace `sol.*` dans `tokens.js` + wrapper `.sol-surface` scoping strict
- **(C)** Aligner la maquette Sol sur le DS existant

---

### P0-8 · Fonts Fraunces + DM Sans + JetBrains Mono absents
**Finding** : `frontend/src/index.css:43-50` utilise `-apple-system, BlinkMacSystemFont...` (système). Aucun preconnect Google Fonts, aucun `@font-face`. Les 3 fonts custom Sol = **+300-500 ko**, shift layout FOUT, Fraunces opsz variable pèse lourd.
**Décision requise** : budget perf accepté ? Alternative : Fraunces uniquement sur `/cockpit/sol/*`, fallback Georgia ailleurs.

---

### P0-9 · `anthropic` SDK non installé
**Finding** : absent de `requirements.txt` et `requirements.lock.txt`. Pas bloquant Sprint 1-2 (pas de LLM) mais **doit être ajouté maintenant** pour préparer Sprint 7-8.

---

### P0-10 · Test baseline cassé
**Finding** : `python -m pytest --collect-only` échoue immédiatement avec `PROMEOS_JWT_SECRET environment variable is required`. Gate 4 exige "régression ≥ baseline" — sans baseline collectable, bloqué.
**Décision requise** : Fixer baseline via `conftest.py` ou `.env.test` documenté avant Sprint 1.

---

## P1 — Importants (à clarifier Gate 0)

### P1-1 · `datetime.now(UTC)` vs `datetime.now(timezone.utc)` (convention)
- Existant : 381 occurrences de `datetime.now(timezone.utc)` (convention repo)
- Prompt impose : `datetime.now(UTC)` (Python 3.11+, OK sur 3.14.3 installé)
- Dette existante : 38 occurrences de `datetime.utcnow()` dans 10 fichiers (iam, billing, energy, kb, purchase, job_outbox, reg_*)
- **Décision** : aligner Sol sur `timezone.utc` (convention) ou imposer `UTC` (moderne, mais introduit 2e convention)

### P1-2 · Scheduler — `JobOutbox` existe, APScheduler absent
- 0 hit `APScheduler` ou `BackgroundScheduler` dans le repo
- Pattern existant : `backend/jobs/worker.py` + `JobOutbox` table (outbox polling, pull-based `process_one`)
- Introduire APScheduler = **2 systèmes d'exécution différée concurrents** → risque désynchro + double-exécution
- **Recommandation forte** : réutiliser `JobOutbox` pour `execute_due_pending_actions`

### P1-3 · `SOL_SECRET_KEY` n'existe pas
- `.env.example` n'a que `PROMEOS_JWT_SECRET` et `SECRET_KEY`
- Prompt utilise `SOL_SECRET_KEY` pour HMAC tokens
- **Décision** : nouvelle var env, dérivée `PROMEOS_JWT_SECRET`, ou réutiliser `SECRET_KEY` ?

### P1-4 · Monitoring — Prometheus absent, `cx_logger` existe
- 0 hit `prometheus_client`
- Pattern existant : `cx_logger` (9 fichiers, voir `routes/cx_dashboard.py`, `routes/copilot.py`, `tests/test_cx_logger.py`)
- **Recommandation** : réutiliser `cx_logger` pour métriques Sol (`SOL_INTENT_CLASSIFIED`, `SOL_ACTION_SCHEDULED`, etc.)

### P1-5 · Timing sprint sous-estimé (+47%)
| Gate | Prompt | Révisé | Justification |
|---|---|---|---|
| Gate 0 audit | 0.5j | 0.5j | OK |
| Gate 1 models+migration+triggers | 1j | **2j** | Trigger SQLite event + Postgres + décision Alembic + tests append-only |
| Gate 2 schemas+utils+voice+boundaries | 2j | **3j** | 30 templates + frenchifier 20 cas + SolContext testable |
| Gate 3 planner+validator+scheduler+audit+dummy | 3j | **4j** | Scheduler Windows + cycle E2E + tous cas `InvalidToken/PlanAltered/DryRunBlocked` |
| Gate 4 routes+org-scoping+CSV+tests | 2j | **3j** | 10 endpoints, cross-tenant rigoureux, CSV anti-injection |
| **Total** | **~8.5j (2 sem)** | **~12.5j (2.5 sem)** | +47% |

Pour tenir 2 semaines strictes : descope CSV/PDF export audit Gate 4, réduire templates voice à 10 (pas 30).

### P1-6 · Règle R8 "zéro jargon Surface" violée dans maquettes
- Surface cockpit cite : `accise T1/T2`, `TURPE CMS`, `CTA coefficient`, `OID` (rapport p3), `PDL` (drawer), `M023` (source chip)
- Guide éditorial interdit explicitement
- **Décision** : maquettes à retoucher OU règle R8 à assouplir (ex: tooltips)

### P1-7 · Grammaire FR stricte — espaces fines U+202F absentes
- Maquette utilise `&nbsp;` (U+00A0) correctement pour milliers (`1 847,20 €`)
- **Aucune U+202F** (fine insécable) avant `: ; ! ? %` comme imposé par le guide
- Helper `frenchifier()` n'existe ni côté front (`utils/format.js`) ni côté back
- **Décision** : créer `frenchifier()` avant toute génération, imposer en CI

### P1-8 · Émojis dans drawer critique (violation R4)
- `cockpit-sol-v1.html:666-669` : 📎 × 4 (pièces jointes drawer contestation facture)
- Règle interdit émojis dans "messages critiques" — drawer contestation = critique
- **Décision** : remplacer par `<Paperclip/>` lucide-react

### P1-9 · Layer toggle Surface/Inspect/Expert — pattern à trancher
- Mockup toggle local (`classList.add('hidden')`)
- `ExpertModeContext` existe déjà (`frontend/src/contexts/ExpertModeContext.jsx`)
- Inspect a contexte (dossier anomalie F-2026-03-LYON) → pointe vers routes `/cockpit/inspect/:dossierId`
- **Décision** : state local vs routes vs ExpertModeContext existant ?

### P1-10 · Rétention 3 ans / anonymisation — hors scope Sprint 1-2
- Architecture cite anonymisation automatique après 3 ans (colonne `anonymized`)
- Prompt Sprint 1-2 ne prévoit pas le job cron
- **Décision** : in-scope Gate 3 ou reporté Sprint 3+ ?

### P1-11 · `SolContext.build()` classmethod non testable sans mock
- Prompt impose `SolContext.build(request, db, correlation_id)` depuis FastAPI Request
- Test unitaire = mock `Request` via `starlette.testclient` ou factory
- **Décision** : documenter pattern test ou junior invente

### P1-12 · DummyEngine — `IntentKind.CONSULTATIVE_ONLY` ou nouveau
- Prompt Phase 3 dit "DummyEngine.KIND = IntentKind.CONSULTATIVE_ONLY # ou nouveau kind DUMMY"
- Ambigu : si CONSULTATIVE_ONLY, DummyEngine entre en conflit avec engine réel du même kind plus tard
- **Recommandation** : créer `IntentKind.DUMMY_NOOP` exclusif tests

---

## P2 — Polish (peut se faire dans sprint)

- **P2-1** `reportlab>=4.1.0` déjà présent → export PDF audit sans nouvelle dep
- **P2-2** `freezegun` absent des deps → nécessaire pour tester scheduler deterministically sous Windows
- **P2-3** `Drawer` composant existe (`frontend/src/ui/Drawer.jsx`) avec Esc + tab trap → base pour `SolActionPreview`
- **P2-4** `FindingCard` existe (`frontend/src/ui/FindingCard.jsx`) → adapter pour `SolHero`
- **P2-5** `Table` existe (`frontend/src/ui/Table.jsx`) → réutiliser pour `SolJournal`
- **P2-6** Animations sans `prefers-reduced-motion` (pulse 3s cartouche) — wrapper en CSS
- **P2-7** Contrast ratio `--ink-400:#8F8A7E` sur `#FAF6F0` ≈ 3.1:1 → **fail WCAG AA** pour texte 13px (`.kpi-unit`)
- **P2-8** 3 HTML cockpit fournis = doublons exacts (`_1`, `_2` identiques au premier) — ne garder qu'une version
- **P2-9** i18n absent partout — dates `14 avril`, format `1 847,20 €`, 50 situations uniquement FR
- **P2-10** Scope creep Gate 4 stub `/api/sol/ask` et `/api/sol/headline` 501 — nécessite déjà route + schema request + test → effort non nul
- **P2-11** Chiffres maquettes (47 382 €, 1 847,20 €, 62/100, 4 200 €/an, 7 500 €/an) = fixtures. Shadow billing V113/V114 calcule déjà ATRD gaz, TURPE, CTA, accise T1/T2 mais **pas de service exposé** pour "liste anomalies détectées vs facture" → nouvel endpoint à créer Sprint 3

---

## Questions prioritaires pour le user (avant Sprint 1)

Ordre d'importance :

1. **P0-1 UUID vs int** → choix (A/B/C) ?
2. **P0-3 Alembic** → choix (A/B/C) ?
3. **P0-6 Rail+Panel V7** → choix (A/B/C) ? (bloquant pour Sprint 3+ UI)
4. **P0-7 Design tokens** → choix (A/B/C) ? (bloquant pour Sprint 3+ UI)
5. **P1-2 Scheduler** → APScheduler ou réutiliser JobOutbox (recommandation : JobOutbox) ?
6. **P1-3 SOL_SECRET_KEY** → nouvelle var ou dérivée ?
7. **P0-10 baseline tests cassée** → fixer avant sprint ?
8. **P1-5 timing** → 2 semaines strictes (descoping nécessaire) ou 2.5 semaines ?
9. **P1-10 rétention 3 ans** → in-scope Sprint 1-2 ou différé ?
10. **P1-6 Règle R8 jargon Surface** → maquettes à retoucher ou règle assouplie (tooltips) ?

---

## Recommandations pour le sprint

### Si go validation rapide (2-3 heures de clarifications)
1. Répondre aux 10 questions prioritaires ci-dessus
2. Fixer baseline tests (docker-compose ou `.env.test`)
3. Patcher le prompt Sprint 1-2 pour :
   - Corriger `resolve_org_id` pattern (body, pas Depends)
   - Remplacer UUID par `Integer autoincrement` (ou String(36))
   - Remplacer JSONB par `JSON`
   - Remplacer trigger DDL par event listener SQLAlchemy
   - Créer `CreatedAtOnlyMixin` (pas `TimestampMixin`)
   - Ajouter `freezegun`, `anthropic` aux deps Gate 1
   - Préciser scheduler = `JobOutbox` (pas APScheduler)
   - Aligner sur `datetime.now(timezone.utc)` (convention)
   - Décider Alembic strategy (A/B/C)
   - Timing révisé 2.5 semaines

### Si refactor prompt profond (1 journée)
Réécrire Phase 1 complètement pour coller au repo réel. Gate 0 audit devient : "lire ce findings doc + trancher les 10 Qs, pas besoin de réauditer".

---

## Ce que l'audit valide

- ✅ **Principe architectural** (5 lois, engines isolés, audit append-only, refus explicite, RGPD-aware)
- ✅ **Voice guide** (8 règles cohérentes, 50 situations bien documentées)
- ✅ **Maquettes éditorialement fidèles** aux règles R1-R4, R6-R7 (vouvoiement, phrases courtes, chiffre d'abord, toujours une issue)
- ✅ **Composants existants réutilisables** (Drawer, FindingCard, Table, reportlab, cx_logger, JobOutbox)
- ✅ **Pydantic v2 OK** (2.12.5 installé)
- ✅ **Python 3.14.3 OK** (support `from datetime import UTC`)
- ✅ **Infrastructure pure Sprint 1-2** (pas de LLM, pas d'UI) = bon choix

---

## Ce que l'audit ne couvre pas

- **LLM sandboxing** (Sprint 7-8) — audit séparé à faire avant
- **Engines métier** (Sprint 3-6) — chacun audité séparément au moment de son sprint
- **Tests frontend composants Sol** — attendent décision P0-6/P0-7 design system
- **Intégration CI/CD** — quality gate Sol à définir

---

**Livré par** : 3 agents SDK parallèles (architecture / prompt / voice+mockups), 440s total
**Fichiers clés cités** : ~40 chemins, tous vérifiés dans worktree `claude/sol-v1-audit` @ 711d3f5e
