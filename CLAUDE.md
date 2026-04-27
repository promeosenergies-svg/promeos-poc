# CLAUDE.md — Contexte PROMEOS pour Claude Code

Ce fichier est chargé automatiquement à chaque session Claude Code.

## 🎯 Doctrine cardinale (v1.1 — 2026-04-27)

**Source complète** : `docs/doctrine/doctrine_promeos_sol_v1_1.md` (881 lignes)
**Version exécutable** : `backend/doctrine/` (constants, kpi_registry, error_codes)
**Skill activable** : `.claude/skills/promeos-doctrine/SKILL.md`

### Les 10 règles non-négociables

1. **Tout est lié** — patrimoine → données → KPIs → alertes → actions → conformité → factures → achat. Aucune feature isolée.
2. **Non-sachants d'abord** — copy simple, profondeur via "voir le calcul". Jamais d'acronyme brut en titre.
3. **Zéro KPI magique** — tout KPI a fiche YAML (label, unit, formula, source, scope, period, confidence). Source : `backend/doctrine/kpi_registry.py`.
4. **Constantes inviolables** — CO₂ 0.052, primary energy 1.9, fallback prix 0.068, DT jalons -40/-50/-60 (PAS 2026), NEBCO 100kW, accise élec T1 30.85 / T2 26.58 €/MWh, accise gaz 10.73 €/MWh. Source unique : `backend/doctrine/constants.py`. Importer, jamais redéfinir.
5. **Statuts data obligatoires** — réel | estimé | incomplet | incohérent | en attente | démo. Aucun fallback silencieux.
6. **Zéro logique métier dans le frontend** — tout calcul (trajectoire, score, %, intensité kWh/m²) côté backend. Test source-guard : `tests/doctrine/test_no_frontend_business_logic.py`.
7. **Cohérence transverse** — mêmes valeurs entre cockpit, portfolio, site, conformité, billing, achat. Test : `tests/doctrine/test_cross_view_consistency.py`.
8. **Chaque chiffre a son unité** — kWh/MWh, kW/kVA, €/MWh, HT/TTC explicités. Période et source visibles.
9. **Erreurs API standard** — `{code, message, hint, correlation_id, scope}`. Source : `backend/doctrine/error_codes.py`.
10. **Org-scoping obligatoire** — tout endpoint applique `resolve_org_id`. Aucune fuite cross-org.

### Anti-patterns rejetés en PR

Page démarrant par tableau sans synthèse · KPI sans source · graphique sans période · bouton sans destination · route accessible uniquement par URL · ajout de menu au lieu d'améliorer le centre d'action · mock non signalé · règle réglementaire non versionnée · KPI calculé différemment selon la page · valeur estimée affichée comme certaine.

### Activation skill doctrine

Pour toute tâche touchant cockpit, KPI, UX cœur, conformité, billing, achat, scoring, événements ou tout écran user-facing : **lire `.claude/skills/promeos-doctrine/SKILL.md` AVANT d'écrire du code**.

### MCP obligatoires

Context7 · code-review · simplify · (futur) doctrine-check

### Convention commits

`feat(<scope>): Phase N — description` · `fix(p0): ...` · atomic per phase.

---

## Skill PROMEOS obligatoire

Lis `SKILL.md` à la racine AVANT toute action sur ce repo. Toutes les règles non-négociables y sont encodées. Skills détaillés dans `.claude/skills/`.

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
