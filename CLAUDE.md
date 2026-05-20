# CLAUDE.md — Contexte PROMEOS pour Claude Code

Ce fichier est chargé automatiquement à chaque session Claude Code.

## Skill PROMEOS obligatoire

Lis `SKILL.md` à la racine AVANT toute action sur ce repo. Toutes les règles non-négociables y sont encodées. Skills détaillés dans `.claude/skills/`.

## Positionnement cardinal — Vision Consolidée v1.3 (08/05/2026 nuit tardive)

PROMEOS = **système de contrôle énergétique B2B des patrimoines multi-sites** / *"tour de contrôle énergétique du client B2B"*. 5 verbes cardinaux : **centraliser, fiabiliser, comparer, auditer, piloter**. Wedge : **facture + conformité + consommation**. **Pricing 3 tiers** : Control Lite 6,9 k€/an (1-10 sites, 1 module) / Control 19,9 k€/an (5-15 sites, full socle) / Control Plus 19,9 k€ + 850 €/site/an (16+ sites). 4 extensions modulaires (Purchase / Compliance+ avec eIDAS / ACC PMO client / Flex Advisory M&V only). **3 verticales prioritaires Y1-Y2** : tertiaire multi-sites + bailleurs + retail. Pas un hub Zapier, pas un fournisseur, pas un courtier, pas un agrégateur, pas une PMO ACC, pas un EMS vertical. Promesse finale : *"Comprendre. Décider. Agir. Prouver."* Doctrine complète : `project_promeos_vision_consolidee_v1_3_2026_05_08.md`. Tout choix produit/archi/GTM/pricing doit s'y conformer.

## Centre d'Action V4 — refonte Mois 1-6 (lancée 13/05/2026)

- **Doctrine source** : [`docs/doctrine/doctrine_v4_classement_priorisation.md`](docs/doctrine/doctrine_v4_classement_priorisation.md) (**v0.3** · avenant 2026-05-14 Q37-A+ closure_reasons révisés · cf. §11 historique versions)
- **North star UX** : [`docs/maquettes/centre_action_v4/`](docs/maquettes/centre_action_v4/) (5 HTML figées — voir README index)
- **L1 audit décisionnel** : [`docs/dev/L1_audit_centre_action_v4_decisional.md`](docs/dev/L1_audit_centre_action_v4_decisional.md) (86 verdicts binaires)
- **ADR-025 Architecture V4** : [`docs/dev/L2_ADR-025_architecture_v4.md`](docs/dev/L2_ADR-025_architecture_v4.md) (status: **Accepted** · 8 tables · 20 indexes · 100 tests)
- **ADR-026 Migration data legacy → V4** : [`docs/dev/L3_ADR-026_migration_data.md`](docs/dev/L3_ADR-026_migration_data.md) (status: **Accepted** · manuel de bascule sécurisé · 9 invariants I1-I9 · 7 arbitrages Q19-Q25 · 6 scripts · cutover Mois 4 + STOP GATE J+14)
- **ADR-027 Sécurité org-scoping V4** : [`docs/dev/L4_ADR-027_securite_org_scoping.md`](docs/dev/L4_ADR-027_securite_org_scoping.md) (status: **Accepted** · manuel défensif · 11 invariants IS1-IS11 · 7 arbitrages Q26-Q32 · 8 menaces M1-M8 · IDOR matrix 288 cellules · 50 SG CI custom · CI gate Bandit+Semgrep+gitleaks+pip-audit · risque P0 sécu mitigé)
- **ADR-028 Lifecycle states V4** : [`docs/dev/L5_ADR-028_lifecycle_states.md`](docs/dev/L5_ADR-028_lifecycle_states.md) (status: **Accepted** · manuel comportement item · 11 invariants IL1-IL11 · 7 arbitrages Q33-Q39 · state machine 5 états × 10 transitions strictes · 6 closure_reasons révisés (`merged_duplicate` + `resolved_via_recurrence`) · 56 tests planifiés · **avenant doctrinal v0.2 → v0.3 inclus dans ce commit**)
- **ADR-029 Evidence + audit trail V4** : [`docs/dev/L6_ADR-029_evidence_audit_trail.md`](docs/dev/L6_ADR-029_evidence_audit_trail.md) (status: **Accepted** · manuel des preuves et de la traçabilité · 9 invariants IE1-IE9 · 7 arbitrages Q40-Q46 · 16 event_types × 3 catégories rétention RGPD · 16 schemas Pydantic v1 · 8 articles CNIL référencés · 40+ tests planifiés · **dernier ADR Mois 1 — clôture trilogie data**)
- **L7 Data Dictionary V4** : [`docs/dev/L7_data_dictionary_v4.md`](docs/dev/L7_data_dictionary_v4.md) (status: **Accepted** · manuel de référence unique pour tout dev Mois 2+ · compilation pure des 5 ADR + doctrine v0.3 + L1 · 70 termes glossaire · 8 tables V4 + 20 indexes · 9 enums Python · 16 schemas Pydantic v1 · 49 invariants quick-reference (9 Q + 9 I + 11 IS + 11 IL + 9 IE) · 8 cardinaux Amine 🛡️ · 41 paires FR/EN · ~574 tests planifiés cumulés · auto-éval 40/30)
- **L8 Plan suppression legacy Mois 5** : [`docs/dev/L8_plan_suppression_legacy.md`](docs/dev/L8_plan_suppression_legacy.md) (status: **Accepted** · procédure opérationnelle step-by-step à exécuter Mois 5 J+14 minimum · 18 tables legacy à DROP · ~1 667 LoC FE mortes · 9 models + 20 services + 51 endpoints backend · 173 rows data préservées Mois 4 J0 · 12 mois rétention RGPD CNIL · STOP GATE 8 critères binaires obligatoires · auto-éval 27/18 · ⚠️ irréversible après exécution)
- **L9 Mois 2 backend pilot manual** : [`docs/dev/L9_mois2_backend_pilotage.md`](docs/dev/L9_mois2_backend_pilotage.md) (status: **Accepted** · **DERNIER LIVRABLE MOIS 1** · synthèse finale Mois 1 (9 livrables + 49 invariants + 46 arbitrages + 11 cardinaux non-rejouables) + sprint plan Mois 2 (8 sprints sur 4 semaines M2-1→M2-8) + 50 source-guards activation progressive + pyramide tests 100 min/574 cible + DoD binaire 20 critères go/no-go cutover Mois 4 + transition pratiques Mois 1 docs → Mois 2 code · auto-éval 22/20)
- **🎯 MOIS 1 DOCS ONLY — COMPLET 10/10** ✅ (doctrine v0.3 + L1 + ADR-025 + ADR-026 + ADR-027 + ADR-028 + ADR-029 + L7 + L8 + L9). **Mois 2 backend READY TO START** : Sprint M2-1 Foundation infra J+1 à J+3 après merge `claude/refonte-sol2` → `main`.
- **Arbitrages doctrinaux Q1-Q9** : Q1-A · Q2-α · Q3-C · Q4-A · Q5-B · Q6-A · Q7-A · Q8-C · Q9-B
- **Arbitrages techniques Q10-Q18 (ADR-025)** : Q10-A_refined · Q11-A · Q12-A · Q13-B · Q14-A · Q15-C · Q16-A · Q17-C_refined · Q18-C_refined
- **Arbitrages techniques Q19-Q25 (ADR-026)** : Q19-C · Q20-A · Q21-A · Q22-A · Q23-A · Q24-A · Q25-A + garde-fou cardinal **I9 backup hors Git · receipt sanitizé**
- **Arbitrages techniques Q26-Q32 (ADR-027)** : Q26-C · Q27-B+ · Q28-D · Q29-D · Q30-A+ · Q31-B+ · Q32-B + garde-fou cardinal **IS11 pattern repository org-scopé obligatoire** (4 lignes de défense empilées : middleware + décorateur + repository + source-guards CI)
- **Arbitrages techniques Q33-Q39 (ADR-028)** : Q33-B · Q34-A · Q35-A · Q36-C+ · Q37-A+ · Q38-B · Q39-B + garde-fous cardinaux **IL4 expired interdit P0/P1 conformité** · **IL5 merged_duplicate ≠ resolved_via_recurrence (Q9-B)** · **IL7 auto-close P0/P1 exige preuve ou justification**
- **Arbitrages techniques Q40-Q46 (ADR-029)** : Q40-D · Q41-D · Q42-C+ · Q43-A+ · Q44-A+ · Q45-B · Q46-B+ + garde-fou cardinal **IE9 validation MIME par magic bytes** (anti-spoofing — 4 lignes de défense empilées : libmagic + whitelist + log mismatch + double-check signatures hardcodées) · IE4 matrice rétention RGPD alignée doctrine v0.3 (`merged_duplicate` 3 ans ≠ `resolved_via_recurrence` 5 ans) · IE5 purge triple garde-fou (feature flag + dry-run + trace `security_audit_log`)
- **2 axes orthogonaux** : `kind` (7 valeurs intrinsèques) ≠ `priority` (calcul dérivé P0-P3 + 6 règles modulation R1-R6)
- **Cardinaux data à migrer** : **173 rows** (`action_items` 35 + `bill_anomaly` 52 + `anomaly` KB 86) · 15 autres tables vides Sprint 13 dette pure
- **Mois 1 série ADR complète (5/5)** : ADR-025 + ADR-026 + ADR-027 + ADR-028 + ADR-029 + 1 avenant doctrinal v0.3 · prochaines étapes L7 Data Dictionary V4 + glossaire · L8 Plan suppression legacy Mois 5 · L9 Prompt Mois 2 backend
- **Mois 2** : backend cible socle (8 tables V4 + services PriorityScoring/Lifecycle/Impact)
- **Mois 4** : cutover sec V4 (Q13-B) — feature flag global · backup triple artefact J-1 (binaire + SQL + JSON + checksums SHA256) · STOP GATE J+14 manuel
- **Backup DB + export JSON/CSV obligatoire** hors Git avant suppression (Q2-α non négociable · receipt sanitizé in Git si commité)
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
5. Baseline tests jamais régresser (FE ≥ 4 751 baseline M2-5.0, BE ≥ 843, cf. workflow pre-merge)
6. `consumption_unified_service.py` = SoT consommation
7. `utils/naf_resolver.py:resolve_naf_code()` = canonical NAF
8. Branche `claude/*` — jamais commit direct main
9. Commit + push + draft PR immédiat (pas d'accumulation)
10. Hooks et scripts d'audit : TOUJOURS utiliser `$CLAUDE_PROJECT_DIR` pour chemins, jamais relatifs (cwd peut varier). Leçon Phase 4 deadlock.

## Workflow méthodologique

Phase 0 read-only (grep/find/cat) → STOP gate → phases numérotées → DoD → atomic commit → source-guard test. Zero modif sans bilan Phase 0 valide. Méthodes détaillées : [`docs/dev/methode_audit_avant_fix.md`](docs/dev/methode_audit_avant_fix.md) (audit avant fix) · [`docs/dev/methode_walkthrough_navigateur.md`](docs/dev/methode_walkthrough_navigateur.md) (walkthrough routing/auth).

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
3. Tests FE ≥ 4 751, BE ≥ 843, zéro régression
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
