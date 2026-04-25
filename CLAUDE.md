# CLAUDE.md — Contexte PROMEOS pour Claude Code

Ce fichier est chargé automatiquement à chaque session Claude Code.

## Skill PROMEOS obligatoire

Lis `SKILL.md` à la racine AVANT toute action sur ce repo. Toutes les règles non-négociables y sont encodées. Skills détaillés dans `.claude/skills/`.

## Sources veille canoniques (regle obligatoire 24/04/2026)

AVANT toute recherche externe (web, wiki, autre) sur un sujet energie /
reglementaire / marche / facture, consulter d'abord le catalogue de sources
canoniques :

- Catalogue : `~/.claude/projects/-Users-amine-projects-promeos-poc/memory/reference_sources_veille_kb.md`
  (28 entrees : CRE, RTE, Enedis, GRDF, NaTran, Terega, Legifrance, ADEME,
  MNE, France Renov, MTE/DGEC, Commission UE, EEX + presse + observatoires)
- Doctrine d'usage + triage par cas d'usage : `~/.claude/projects/-Users-amine-projects-promeos-poc/memory/feedback_kb_sources_systematic.md`

Pour tout subagent (Agent tool) en domaine energie/regulation, inclure dans
le prompt : *"Consulte le catalogue de sources canoniques PROMEOS avant
toute recherche externe."*

Decouverte d'une nouvelle source utile -> l'ajouter immediatement au catalogue.

## Workframe & boundaries

Lire et appliquer `docs/dev/workframe-contract.md`. Matériel personnel jamais dans le repo — il vit dans `../workspace/personal/<person>/` hors boundary git. Pas de `docs/drafts/` ni `docs/notes/` — utiliser Draft PRs GitHub.

## Stack technique

- Backend : Python 3.11 / FastAPI / SQLAlchemy / SQLite (PostgreSQL-ready)
- Frontend : React 18 / Vite / Tailwind CSS v4 / Recharts / Lucide React
- Tests : pytest (BE) / Vitest (FE) / Playwright (E2E)
- Port backend : **8001** (pas 8000 ni 8080) · Port frontend : **5173** (proxy → 8001)

## Règle d'or — ZERO calcul métier frontend

Le frontend est affichage uniquement. Calculs métier (CO₂, scoring, forecasting) côté backend, exposés via REST, consommés en Context/hook. Voir SKILL.md.

## Agents Claude Code (délégation via Task tool)

Routage obligatoire pour les 11 agents de `.claude/agents/*.md` :

- **Architecture / ADR / cross-pillar** → `architect-helios`
- **Code FastAPI + React (post-ADR)** → `implementer`
- **Revue PR / anti-patterns / duplication** → `code-reviewer` (avant commit)
- **Tests pytest / Vitest / Playwright** → `test-engineer`
- **Baseline / DoD / STOP gate / release** → `qa-guardian` (fin de phase)
- **OPERAT / BACS / APER / TURPE 7 / CRE / CBAM / VNU / capacité** → `regulatory-expert`
- **Shadow billing / accises / CTA / TURPE / anomalies** → `bill-intelligence`
- **Carpet plot / CUSUM / DJU / signature / forecasting / flex (NEBCO/AOFD)** → `ems-expert`
- **Enedis / SGE / GRDF / R6X / CDC / PHOTO D020** → `data-connector`
- **Org-scoping / RGPD / PII / secrets / CVE** → `security-auditor`
- **Génération prompts Claude Code** → `prompt-architect`

Les 5 agents Python `backend/ai_layer/agents/` sont runtime API production, **distincts** des 11 AgentDefinitions ci-dessus (usage interactif).

## Règles non-négociables

1. Zero business logic in frontend
2. Org-scoping obligatoire sur chaque endpoint via `resolve_org_id`
3. Atomic commits : `fix(module-pN): Phase X.Y — description`
4. MCP obligatoires : Context7, code-review, simplify
5. Baseline tests jamais régresser (FE ≥ 3 783, BE ≥ 843, cf. workflow pre-merge)
6. `consumption_unified_service.py` = SoT consommation
7. `utils/naf_resolver.py:resolve_naf_code()` = canonical NAF
8. Branche `claude/*` — jamais commit direct main
9. Commit + push + draft PR immédiat (pas d'accumulation)
10. Hooks et scripts d'audit : TOUJOURS utiliser `$CLAUDE_PROJECT_DIR` pour chemins, jamais relatifs (cwd peut varier). Leçon Phase 4 deadlock.

## Workflow méthodologique

Phase 0 read-only (grep/find/cat) → STOP gate → phases numérotées → DoD → atomic commit → source-guard test. Zero modif sans bilan Phase 0 valide.

## Fichiers critiques (audit avant modification)

- `backend/regops/scoring.py` — SoT scoring conformité
- `backend/services/consumption_unified_service.py` — SoT consommation
- `backend/config/emission_factors.py` — constantes CO₂ canoniques
- `backend/config/tarifs_reglementaires.yaml` — tarifs versionnés (ParameterStore)
- `backend/utils/naf_resolver.py` — résolution NAF
- `backend/services/demo_seed/orchestrator.py` — seed orchestration
- `backend/services/compliance_score_service.py` — scoring conformité

## Commandes de référence

```bash
cd backend && python main.py                                # → :8001
cd backend && python -m pytest tests/ -v --tb=short         # tests BE
cd frontend && npm run dev                                   # → :5173
cd frontend && npx vitest run                                # tests FE
cd backend && python -m pytest tests/source_guards/ -v       # source-guards
cd backend && python -m services.demo_seed --pack helios --size S --reset
npm run dev:full                                             # full stack
```

## Workflow obligatoire pre-merge

1. `/code-review:code-review` — bugs, sécu, qualité
2. `/simplify` — refactoring, clarté
3. Tests FE ≥ 3 783, BE ≥ 843, zéro régression
4. Playwright audit screenshots si modification UI

## Architecture hiérarchique

Organisation → EntitéJuridique → Portefeuille → Site → Bâtiment → Compteur → DeliveryPoint

## Skills partagées canoniques (`.claude/skills/`)

Skills PROMEOS auto-chargées par les 11 agents :

- `emission_factors` — CO₂ ADEME V23.6 (wrapper de `config/emission_factors.py`)
- `regops_constants` — seuils BACS/APER/AUDIT, jalons DT, sanctions
- `regulatory_calendar` — deadlines 2026-2050 (OPERAT, Audit SMÉ, Capacité 11/2026, CBAM…)
- `helios_architecture` — 6 pillars + 3-layers agents + SoT canoniques
- `tariff_constants` — **Phase 3B** (bloqué par followup `tarifs_sot_consolidation.md`)

Plus 11 skills domaine (`promeos-*`, `energy-*`) et 4 skills vendor dans `.claude/skills/`.
