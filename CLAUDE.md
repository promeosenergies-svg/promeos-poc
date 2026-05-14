# CLAUDE.md — Contexte PROMEOS pour Claude Code

Ce fichier est chargé automatiquement à chaque session Claude Code.

## Skill PROMEOS obligatoire

Lis `SKILL.md` à la racine AVANT toute action sur ce repo. Toutes les règles non-négociables y sont encodées. Skills détaillés dans `.claude/skills/`.

## Positionnement cardinal — Vision Consolidée v1.3 (08/05/2026 nuit tardive)

PROMEOS = **système de contrôle énergétique B2B des patrimoines multi-sites** / *"tour de contrôle énergétique du client B2B"*. 5 verbes cardinaux : **centraliser, fiabiliser, comparer, auditer, piloter**. Wedge : **facture + conformité + consommation**. **Pricing 3 tiers** : Control Lite 6,9 k€/an (1-10 sites, 1 module) / Control 19,9 k€/an (5-15 sites, full socle) / Control Plus 19,9 k€ + 850 €/site/an (16+ sites). 4 extensions modulaires (Purchase / Compliance+ avec eIDAS / ACC PMO client / Flex Advisory M&V only). **3 verticales prioritaires Y1-Y2** : tertiaire multi-sites + bailleurs + retail. Pas un hub Zapier, pas un fournisseur, pas un courtier, pas un agrégateur, pas une PMO ACC, pas un EMS vertical. Promesse finale : *"Comprendre. Décider. Agir. Prouver."* Doctrine complète : `project_promeos_vision_consolidee_v1_3_2026_05_08.md`. Tout choix produit/archi/GTM/pricing doit s'y conformer.

## Centre d'Action V4 — refonte Mois 1-6 (lancée 13/05/2026)

- **Doctrine source** : [`docs/doctrine/doctrine_v4_classement_priorisation.md`](docs/doctrine/doctrine_v4_classement_priorisation.md) (v0.2 — référence figée 6 mois)
- **North star UX** : [`docs/maquettes/centre_action_v4/`](docs/maquettes/centre_action_v4/) (M1-M5 figées — voir README index)
- **Arbitrages actés** : Q1-A (ActionCenterItem polymorphique) · Q2-α (table rase + backup obligatoire) · Q3-C (ADR-022 + extensions V4) · Q4-A (regulatory_applicability_service SoT) · Q5-B (job pull idempotent compliance) · Q6-A (Mois 1 docs only) · Q7-A (rendu strict par kind) · Q8-C (score persisté + invalidation event-driven) · Q9-B (duplicate_groups vs recurrence_groups séparés)
- **2 axes orthogonaux** : `kind` (7 valeurs intrinsèques) ≠ `priority` (calcul dérivé P0-P3 + 6 règles modulation R1-R6)
- **Mois 1** : docs only (L1 → L10), zéro code. STOP GATE Phase 0 → validation Amine → Phase 1 L1 décisionnel
- **Mois 2** : backend cible via ADR-025 → ADR-029 (architecture / migration / sécurité / lifecycle / evidence+audit trail)
- **Backup DB + export JSON/CSV des tables legacy `Action`/`Anomaly` OBLIGATOIRE** avant suppression (Q2-α non négociable)
- Audit legacy de référence : [`docs/audits/AUDIT_CENTRE_ACTION_2026_05_13.md`](docs/audits/AUDIT_CENTRE_ACTION_2026_05_13.md)

## Workframe & boundaries

Lire et appliquer `docs/dev/workframe-contract.md`. Matériel personnel jamais dans le repo — il vit dans `../workspace/personal/<person>/` hors boundary git. Pas de `docs/drafts/` ni `docs/notes/` — utiliser Draft PRs GitHub.

## Conventions de développement

Référence stable des conventions stack + paths canoniques + modèles Claude par défaut + filtres pytest : [`docs/dev/conventions.md`](docs/dev/conventions.md). À consulter avant tout sprint régulatoire ou refacto cross-modules.

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
