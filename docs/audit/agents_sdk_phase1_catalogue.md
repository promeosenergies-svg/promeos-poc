# Phase 1 — Catalogue cible 11 agents Claude SDK PROMEOS

**Date** : 2026-04-24
**Branche** : `claude/agents-sdk-catalogue`
**Prérequis** : [Phase 0 report](agents_sdk_phase0_report.md) validé
**Status** : ✅ Spec finalisée — prêt pour Phase 2 (création fichiers `.claude/agents/*.md`)

---

## 1. Objet

Formaliser la spécification complète des **11 agents Claude SDK cibles** pour PROMEOS avec tous les attributs requis (name, description, model, tools, délégations, guardrails, critères éval) et documenter les arbitrages d'archive.

Chaque agent ici aura un fichier `.claude/agents/<name>.md` en Phase 2.

---

## 2. Catalogue 11 agents — spec complète

### Core Development (5 agents)

#### 2.1 `architect-helios`

| Attribut | Valeur |
|---|---|
| **Model** | `claude-opus-4-7` |
| **Tools** | `Read, Glob, Grep, Task` (pas de Write direct) |
| **Description** | Décisions architecturales, ADR, design modules EMS/RegOps/Bill/Achat, cohérence cross-pillar |
| **Quand invoquer** | ✅ "comment structurer X ?", nouveau module, refacto cross-module, ADR |
| **Ne PAS invoquer** | ❌ Implémentation code → `implementer`. ❌ Revue PR → `code-reviewer` |
| **Pillars owned** | Architecture transverse |
| **Skills chargées** | `helios_architecture` (à créer P3) |
| **Guardrails** | zero-business-logic-frontend · org-scoping mandatory · SoT `consumption_unified_service.py` |
| **Délègue à** | `implementer` (après validation) · `regulatory-expert` (si doute règle) · `security-auditor` (si P0 archi) |
| **Format sortie** | ADR numéroté (contexte, décision, conséquences) |
| **Éval criteria** | 5 golden tasks (new module, cross-pillar refacto, cross-org leak, DB migration, API contract change) |
| **Source prompt** | Nouveau — inspiré ex-CTO Paperclip |

#### 2.2 `implementer`

| Attribut | Valeur |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Tools** | `Read, Write, Edit, Glob, Grep, Bash` (scoped repo) |
| **Description** | Exécution code FastAPI + React suivant ADR d'`architect-helios` |
| **Quand invoquer** | ✅ Implémentation concrète post-ADR · nouvelles fonctions / endpoints |
| **Ne PAS invoquer** | ❌ Décision archi → `architect-helios`. ❌ Tests → `test-engineer` |
| **Pillars owned** | Cross (exécute sous ADR) |
| **Skills chargées** | `tariff_constants`, `emission_factors` (à créer P3) |
| **Guardrails** | Jamais de constantes hardcodées · toujours ParameterStore / YAML · atomic commits |
| **Délègue à** | `test-engineer` (après implémentation) · `code-reviewer` (avant commit) |
| **Format sortie** | Diff + résumé modifications + commit message proposé |
| **Éval criteria** | 5 golden tasks (new endpoint, refacto service, migration DB, fix bug, hook pre-commit) |
| **Source prompt** | Nouveau — inspiré ex-Lead Engineer Paperclip |

#### 2.3 `code-reviewer`

| Attribut | Valeur |
|---|---|
| **Model** | `claude-sonnet-4-6` (read-only) |
| **Tools** | `Read, Glob, Grep` uniquement |
| **Description** | Revue PR, conformité archi, détection anti-patterns, duplication |
| **Quand invoquer** | ✅ Avant chaque commit atomique · après chaque implémentation |
| **Ne PAS invoquer** | ❌ Security → `security-auditor`. ❌ Tests → `test-engineer` |
| **Pillars owned** | Qualité code transverse |
| **Skills chargées** | `code-review` MCP |
| **Guardrails** | Read-only strict · jamais Write/Edit |
| **Délègue à** | `architect-helios` (si violation archi) · `implementer` (si fix requis) |
| **Format sortie** | `{finding, severity, file:line, evidence, suggestion}` |
| **Éval criteria** | 5 golden tasks (duplication detect, anti-pattern FastAPI, anti-pattern React, secret leak, perf issue) |
| **Source prompt** | Nouveau |

#### 2.4 `test-engineer`

| Attribut | Valeur |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Tools** | `Read, Write, Edit, Bash` (scoped aux `tests/`, `__tests__/`) |
| **Description** | Création/maintenance pytest + Vitest, couverture, non-régression |
| **Quand invoquer** | ✅ Après chaque nouvelle fonction/endpoint · après fix bug · gap coverage |
| **Ne PAS invoquer** | ❌ Écriture code métier → `implementer` |
| **Pillars owned** | Qualité tests transverse |
| **Skills chargées** | `python-testing-patterns`, `webapp-testing` |
| **Guardrails** | Baseline 9 585 tests jamais régresser · tests intégration > mocks DB (doctrine user) |
| **Délègue à** | `qa-guardian` (vérification baseline) |
| **Format sortie** | Liste tests ajoutés + diff + count change |
| **Éval criteria** | 5 golden tasks (new endpoint test, bug regression, integration test, e2e Playwright, flaky fix) |
| **Source prompt** | Nouveau |

#### 2.5 `qa-guardian`

| Attribut | Valeur |
|---|---|
| **Model** | `claude-sonnet-4-6` (read-only) |
| **Tools** | `Read, Glob, Grep, Bash (readonly: pytest --collect-only, npm test -- --listTests, git status)` |
| **Description** | Vérification STOP gates, baseline tests, DoD, checklist release |
| **Quand invoquer** | ✅ Fin de phase · avant commit final · avant pilot push |
| **Ne PAS invoquer** | ❌ Fix tests → `test-engineer` |
| **Pillars owned** | Guardrails release |
| **Skills chargées** | `deploy-checklist` |
| **Guardrails** | Read-only strict · format `PASS` / `FAIL` + liste non satisfaits obligatoire |
| **Délègue à** | `test-engineer` (si test manquant) · `security-auditor` (si P0 sécu) |
| **Format sortie** | `{status: PASS\|FAIL, criteria_passed: [], criteria_failed: [], blockers: []}` |
| **Éval criteria** | 5 golden tasks (baseline check, DoD vérif, source-guards check, org-scoping check, seed integrity) |
| **Source prompt** | **Extract V120** `/tmp/v120_qa_guardian.py` (172 L) |

### Domain Expertise (4 agents)

#### 2.6 `regulatory-expert`

| Attribut | Valeur |
|---|---|
| **Model** | `claude-opus-4-7` |
| **Tools** | `Read, Grep, WebFetch (allow-list : legifrance.gouv.fr, cre.fr, ademe.fr, ecologie.gouv.fr)` |
| **Description** | OPERAT, BACS, APER, TURPE 7, CRE délibérations, Audit SMÉ, BEGES, CSRD, CEE |
| **Quand invoquer** | ✅ Question réglementaire · calcul scoring RegOps · vérif date/seuil · veille |
| **Ne PAS invoquer** | ❌ Impact shadow billing → `bill-intelligence`. ❌ Archi scoring → `architect-helios` |
| **Pillars owned** | RegOps |
| **Skills chargées** | `promeos-regulatory`, `regulatory_calendar`, `regops_constants` (2 dernières à créer P3) · `energy-france-veille` |
| **Guardrails** | Toujours citer source + date + confidence · jamais `validated` + `low_confidence` · dates absolues |
| **Délègue à** | `architect-helios` (si impact archi) · `bill-intelligence` (si impact facturation) |
| **Format sortie** | `{finding, source, date, confidence, regulatory_reference, applicability}` |
| **Éval criteria** | 5 golden tasks (OPERAT deadline, BACS seuil 2030, audit SMÉ applicabilité, TURPE 7 HPH calcul, BEGES sanction) |
| **Source prompt** | **Extract V120** `/tmp/v120_regulatory.py` (395 L) + 3 MCP tools YAML |

#### 2.7 `bill-intelligence`

| Attribut | Valeur |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Tools** | `Read, Write, Edit, Grep, Bash` (scoped `backend/bill/`, `backend/ai_layer/bill_*`) |
| **Description** | Shadow billing, TURPE 7, décomposition accises/CTA/CSPE, détection anomalies factures |
| **Quand invoquer** | ✅ Parsing facture · bill_anomaly_explainer · scénarios SPOT/TUNNEL · reclaim |
| **Ne PAS invoquer** | ❌ Règle legifrance → `regulatory-expert`. ❌ Connecteur data → `data-connector` |
| **Pillars owned** | Bill |
| **Skills chargées** | `promeos-billing`, `tariff_constants` (à créer P3 post-consolidation SoT) |
| **Guardrails** | Jamais hardcoder accises/TURPE · toujours ParameterStore · source-of-truth `catalog.py` OU YAML (à trancher P3 followup) |
| **Délègue à** | `regulatory-expert` (si doute règle) · `test-engineer` (si nouveau calcul) |
| **Format sortie** | `{line_item, computed_value, reference_value, variance, confidence, anomaly_type}` |
| **Éval criteria** | 5 golden tasks (TURPE 7 check, accise fév 2026, CTA récalc, TICGN deprecated detect, CSPE anomaly) |
| **Source prompt** | Nouveau |

#### 2.8 `ems-expert`

| Attribut | Valeur |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Tools** | `Read, Write, Edit, Grep, Bash` (scoped `backend/ems/`, `frontend/src/modules/ems/`) |
| **Description** | Carpet plot 24h×365j, décomposition baseload/DJU/occupation, CUSUM ISO 50001, signature énergétique, forecasting |
| **Quand invoquer** | ✅ Question EMS / diagnostic / consumption · OID benchmarking · analyse dérives |
| **Ne PAS invoquer** | ❌ Règle → `regulatory-expert`. ❌ Connecteur Enedis → `data-connector` |
| **Pillars owned** | EMS |
| **Skills chargées** | `promeos-energy-fundamentals`, `promeos-seed` |
| **Guardrails** | DJU méthode COSTIC base 18°C · baseload 15-40% tertiaire · jamais calc métier frontend |
| **Délègue à** | `data-connector` (si besoin CDC) · `bill-intelligence` (si impact coût) |
| **Format sortie** | `{kpi, value, unit, method, period, reference_benchmark, variance}` |
| **Éval criteria** | 5 golden tasks (carpet plot génération, CUSUM deriv detect, baseload split, OID bench, forecast 7j) |
| **Source prompt** | Nouveau — inspiré ex-Energy Analytics Paperclip |

#### 2.9 `data-connector`

| Attribut | Valeur |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Tools** | `Read, Write, Edit, Grep, Bash` (scoped `backend/enedis/`, `backend/connectors/`, `backend/services/gaz_*`) |
| **Description** | Enedis DataConnect OAuth2 / SGE SOAP / GRDF ADICT REST, parsers R6X, ingestion CDC 30min, PHOTO D020/SGE |
| **Quand invoquer** | ✅ Connecteur externe · parsing flux · OAuth refresh · rate limits |
| **Ne PAS invoquer** | ❌ Analyse conso → `ems-expert`. ❌ Règle SGE → `regulatory-expert` |
| **Pillars owned** | Ingestion |
| **Skills chargées** | `promeos-enedis` |
| **Guardrails** | Jamais PRM réel en repo public (RGPD HELIOS) · consentement RGPD obligatoire · rate limits documentés |
| **Délègue à** | `security-auditor` (si PII) · `ems-expert` (si analyse post-ingestion) |
| **Format sortie** | `{endpoint, method, payload_shape, rate_limit, error_handling, retry_policy}` |
| **Éval criteria** | 5 golden tasks (OAuth2 refresh, R6X parse, SGE SOAP fallback, PHOTO D020, consentement expiry) |
| **Source prompt** | Nouveau — inspiré ex-Data Infra Paperclip |

### Support / Process (2 agents)

#### 2.10 `security-auditor`

| Attribut | Valeur |
|---|---|
| **Model** | `claude-sonnet-4-6` (read-only) |
| **Tools** | `Read, Glob, Grep` uniquement |
| **Description** | Org-scoping check (22 routes P0), input validation, secrets, PII (RGPD HELIOS), source-guards KB |
| **Quand invoquer** | ✅ Avant pilot push · après nouveau endpoint · hebdomadaire scheduled |
| **Ne PAS invoquer** | ❌ Code review général → `code-reviewer`. ❌ Fix → `implementer` |
| **Pillars owned** | Sécurité transverse |
| **Skills chargées** | `security-scan`, `security-review` |
| **Guardrails** | Read-only strict · format severity CVE-like (Critical/High/Medium/Low) obligatoire |
| **Délègue à** | `implementer` (pour fix) · `architect-helios` (si refonte requise) |
| **Format sortie** | `{cve_like_id, severity, component, attack_vector, remediation, cwe}` |
| **Éval criteria** | 5 golden tasks (org-scope leak, SQL inject, XSS vector, secret commit, PII in logs) |
| **Source prompt** | Nouveau |

#### 2.11 `prompt-architect`

| Attribut | Valeur |
|---|---|
| **Model** | `claude-sonnet-4-6` |
| **Tools** | `Read, Write, Grep` (scoped `/docs/prompts/`, `/mnt/user-data/outputs/`) |
| **Description** | Génère les prompts Claude Code (Phase 0 → STOP gate → phases → DoD) avec MCP Context7/code-review/simplify |
| **Quand invoquer** | ✅ Demande explicite "génère un prompt pour X" |
| **Ne PAS invoquer** | ❌ Autres tâches (méta-agent uniquement) |
| **Pillars owned** | Méta |
| **Skills chargées** | `writing-plans`, `init` |
| **Guardrails** | Templates Phase 0 read-only + STOP gate + phases numérotées + DoD + source-guards obligatoires |
| **Délègue à** | — (terminal) |
| **Format sortie** | Prompt Claude Code complet Markdown |
| **Éval criteria** | 5 golden tasks (audit prompt, feature prompt, refacto prompt, migration prompt, debug prompt) |
| **Source prompt** | Nouveau |

---

## 3. Mapping pillars PROMEOS → owners

| Pillar | Owner principal | Backup |
|---|---|---|
| **Architecture** | `architect-helios` | — |
| **RegOps** | `regulatory-expert` | `architect-helios` (scoring) |
| **Bill** | `bill-intelligence` | `regulatory-expert` (règles) |
| **EMS** | `ems-expert` | `data-connector` (ingestion) |
| **Ingestion** | `data-connector` | — |
| **Achat** | `bill-intelligence` | `regulatory-expert` |
| **Sécurité** | `security-auditor` | `code-reviewer` |
| **Tests** | `test-engineer` | `qa-guardian` |
| **Release** | `qa-guardian` | `test-engineer` |
| **Méta** | `prompt-architect` | — |

**Zéro pillar sans owner clair** ✅ (critère DoD Phase 1 satisfait).

---

## 4. Décisions d'archive / fusion

### 4.1 Paperclip agents archivés

| Paperclip agent | Décision | Rationale |
|---|---|---|
| **CEO** | Archive | Pas de besoin dev direct |
| **Product Manager** | Archive | Pas de besoin dev direct |
| **UX Designer** | Archive | Non-exécutable en SDK texte (besoin Figma MCP séparé) |
| **DevOps Engineer** | Fusion `qa-guardian` | Overlap CI/tests/release |

### 4.2 V120 `lead.py` → **Archive** (arbitrage user 2026-04-24)

**Décision** : le pattern orchestrateur de `lead.py` V120 n'est **pas converti en agent dédié**. Le Task tool natif Claude Code + les règles de délégation du CLAUDE.md racine suffisent à dispatcher `architect-helios` → `implementer` → `code-reviewer` → `qa-guardian` sans wrapper explicite.

**Rationale** :
- `lead.py` est un pur orchestrateur (dispatche QA + Regulatory, consolide rapports)
- Pattern redondant avec le Task tool Claude Code (qui dispatch déjà vers sous-agents)
- Ajouterait un 12ème agent sans valeur incrémentale
- Préserve le catalogue à 11 agents (DoD Phase 1)

**Conséquence** :
- `/tmp/v120_lead.py` **non réutilisé** en Phase 2
- Si orchestration cross-phase nécessaire côté CI/CD, réinjecter via nouveau script `scripts/run_phase_orchestration.sh` appelant `architect-helios` + `qa-guardian` (hors catalogue agents)

### 4.3 `ai_layer/` existant — **Préserver**

Les 5 agents Python `backend/ai_layer/agents/` (regops_explainer, regops_recommender, data_quality_agent, reg_change_agent, exec_brief_agent) :
- **Ne migrent pas** vers `.claude/agents/`
- Restent en **runtime API Anthropic directe** (FastAPI-compatible)
- Le catalogue SDK est **additif**

---

## 5. Definition of Done — Phase 1

- [x] Catalogue 11 agents validé (section 2)
- [x] Chaque agent a : name, description, model, tools, délégation rules, guardrails, éval criteria (section 2.1-2.11)
- [x] Zéro overlap entre descriptions (vérifié via tableau pillars section 3)
- [x] Chaque pillar PROMEOS a owner clair (section 3)
- [x] Archives documentées avec rationale (section 4)
- [x] Arbitrage `lead.py` V120 = archive (section 4.2, user 2026-04-24)
- [x] 2 agents ont source prompt V120 à réutiliser : `qa-guardian`, `regulatory-expert`

---

## 6. Prochaine étape

**Phase 2** — création des 11 fichiers `.claude/agents/<name>.md` avec template complet (frontmatter + Rôle + Contexte + Quand m'invoquer + Format sortie + Guardrails + Délégations sortantes).

Atomic commit cible : `fix(agents-p2): Phase 2 — 11 AgentDefinitions .claude/agents/*.md`
