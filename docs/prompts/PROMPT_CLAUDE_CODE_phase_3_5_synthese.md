# PROMPT CLAUDE CODE — Phase 3.5 Refonte Synthèse stratégique

> **Usage** : ouvrir Claude Code sur la branche `claude/refonte-sol2`, copier-coller le bloc `## Prompt initial` ci-dessous, joindre les références citées, attendre le compte-rendu Phase 0 avant de valider la suite.
>
> **Branche** : `claude/refonte-sol2` (fork du POC, port frontend `:5175`, backend `:8001` partagé)
>
> **Modèle recommandé** : Opus 4.7 (1M context). Activer `/fast` uniquement si l'itération démo presse — sinon Opus pour la doctrine.

---

## Contexte chargé d'office

L'agent doit lire ces 4 documents en Phase 0 :

1. `docs/adr/ADR-023-synthese-strategique-data-driven.md` — architecture cible
2. `docs/adr/ADR-024-moteur-assujettissement.md` — moteur d'assujettissement réglementaire
3. `docs/doctrine/BRIEFING_BLUEPRINT_FOR_SYNTHESE_STRATEGIQUE.md` — pattern à dupliquer
4. `docs/sol/maquettes/synthese_v7.html`, `synthese_v8.html`, `catalogue_5_modes.html` — références visuelles

Charger également (skim, pas relecture intégrale) :

- `docs/adr/ADR-021-hub-page-grammar-l11.md` — Loi L11 hub page grammar
- `docs/adr/ADR-022-cockpit-data-sources.md` — doctrine SoT data
- `docs/vision/promeos_sol_doctrine.md` — Doctrine Sol v1.1
- `frontend/src/pages/CockpitJour.jsx` (commit `32916787` réf) — pattern frontend
- `backend/routes/cockpit.py` — pattern endpoint hub
- `backend/regops/priority_scoring.py` — moteur priorisation v1.0
- `backend/services/cockpit_highlights_service.py` — pattern aggregator

---

## MCPs à activer

- **`context7`** — pour toute requête FastAPI/SQLAlchemy/React doc
- **`code-review`** — avant chaque commit atomique
- **`simplify`** — après chaque vague d'implémentation

---

## Prompt initial (à coller)

```
Tu es Claude Code (Opus 4.7) sur la branche claude/refonte-sol2 du repo PROMEOS.

OBJECTIF DE SESSION : exécuter la Phase 3.5 = refonte data-driven de la page
Synthèse stratégique (/cockpit/strategique), sur le modèle de Briefing du Jour
livré commit 32916787.

LECTURES OBLIGATOIRES PHASE 0 (read-only, AVANT toute action) :
  1. SKILL.md (racine) + CLAUDE.md (racine)
  2. docs/adr/ADR-023-synthese-strategique-data-driven.md
  3. docs/adr/ADR-024-moteur-assujettissement.md
  4. docs/doctrine/BRIEFING_BLUEPRINT_FOR_SYNTHESE_STRATEGIQUE.md
  5. docs/sol/maquettes/synthese_v7.html (REGULATORY_DRIVEN)
  6. docs/sol/maquettes/synthese_v8.html (PERFORMANCE_DRIVEN)
  7. docs/sol/maquettes/catalogue_5_modes.html (matrice 5 modes)

LIVRABLES PHASE 0 (compte-rendu attendu, AVANT toute écriture) :
  A. Bilan ce que tu as compris : architecture, moteur d'assujettissement,
     5 modes, persona, doctrine.
  B. Dépendances déjà en place dans le repo (ce qui existe vs ce qu'il
     faut créer).
  C. Plan d'exécution Phase 3.5 en sous-phases atomiques numérotées,
     chacune avec : effort estimé, fichiers touchés, source-guard test
     associé, commit message prévisionnel.
  D. STOP-gate : 3 questions ouvertes (avec recommandation par défaut)
     que tu poses à Amine AVANT d'écrire la première ligne de code.

DOCTRINE NON-NÉGOCIABLE (rappel) :
  • Backend authoritative — zéro calcul métier frontend
  • Org-scoping obligatoire (resolve_org_id) sur l'endpoint orchestrateur
  • Atomic commits : feat(p3.5-X.Y): description courte
  • Branche claude/refonte-sol2, jamais main
  • Tests pyramide : source-guards → pytest unit → pytest integ → Playwright
  • Baseline FE 4 515 / BE 7 103 jamais régresser
  • Skill MCP context7 pour FastAPI/SQLAlchemy/React doc
  • /code-review et /simplify avant chaque commit

ROUTAGE D'AGENTS :
  • architect-helios : ADR-023/024 lecture, validation cross-pillar
  • implementer : code FastAPI + React après ADR validé
  • test-engineer : tests pyramide
  • code-reviewer : pre-commit (avec /code-review)
  • qa-guardian : fin de phase, DoD
  • regulatory-expert : règles DT/BACS/APER/SMÉ/BEGES catalogue

ATTENDS MA VALIDATION du compte-rendu Phase 0 avant de continuer.
```

---

## Plan détaillé Phase 3.5 (référence pour l'agent)

### Vague A — Moteur d'assujettissement (cf. ADR-024)

| # | Item | Fichier(s) | Test source-guard | Effort |
|---|---|---|---|---|
| A.1 | `RuleCode` + `ApplicabilityStatus` + `RuleApplicability` dataclass | `backend/regulatory/applicability_types.py` | `test_no_hardcoded_rule_status_outside_service` | 0.5 j/h |
| A.2 | 5 évaluateurs (DT, BACS, APER, SMÉ, BEGES) | `backend/regulatory/rules/{dt,bacs,aper,sme,beges}.py` | `test_every_rule_has_evaluator` | 2.5 j/h |
| A.3 | `rules_catalog.py` + dispatcher | `backend/regulatory/rules_catalog.py` | unit | 0.5 j/h |
| A.4 | `compute_applicability` + `compute_patrimoine_maturity` | `backend/services/regulatory_applicability_service.py` | unit | 1 j/h |
| A.5 | Endpoint `/api/regulatory/applicability` | `backend/routes/regulatory_applicability.py` | integ | 0.5 j/h |
| A.6 | Source-guards | `backend/tests/source_guards/test_applicability_engine.py` | self | 0.5 j/h |

**Commit** : `feat(p3.5-A): moteur assujettissement v1.0 (5 règles · ADR-024)`

### Vague B — Mode dispatcher

| # | Item | Fichier(s) | Effort |
|---|---|---|---|
| B.1 | `StrategicMode` enum + `ModeThresholds` dataclass | `backend/services/strategique/mode_thresholds.py` | 0.5 j/h |
| B.2 | `compute_strategic_mode` (4 gates + default) | `backend/services/strategique/mode_router.py` | 1 j/h |
| B.3 | Tests unit cascade (5 cases minimum) | `backend/tests/services/test_strategique_mode_router.py` | 1 j/h |

**Commit** : `feat(p3.5-B): compute_strategic_mode v1.0 (5 modes + cascade gates)`

### Vague C — Builders backend

| # | Item | Fichier(s) | Effort |
|---|---|---|---|
| C.1 | `StrategicModeBuilder` interface | `backend/services/strategique/builders/base.py` | 1 j/h |
| C.2 | `RegulatoryDrivenBuilder` (HELIOS) | `backend/services/strategique/builders/regulatory.py` | 3 j/h |
| C.3 | `PerformanceDrivenBuilder` (MERIDIAN) | `backend/services/strategique/builders/performance.py` | 2 j/h |
| C.4 | `DataInsufficientBuilder` (onboarding) | `backend/services/strategique/builders/data_insufficient.py` | 2 j/h |
| C.5 | `MODE_BUILDERS` dispatcher | `backend/services/strategique/builders/__init__.py` | 0.5 j/h |
| C.6 | Endpoint `/api/cockpit/strategique` | `backend/routes/cockpit_strategique.py` | 1.5 j/h |
| C.7 | Tests intégration (3 modes × 2 personas) | `backend/tests/integration/test_cockpit_strategique.py` | 2 j/h |
| C.8 | Source-guards (cf. ADR-023 §7) | `backend/tests/source_guards/test_strategique_data_driven.py` | 1 j/h |

**Commits** :
- `feat(p3.5-C.1): StrategicModeBuilder interface + dispatcher`
- `feat(p3.5-C.2): RegulatoryDrivenBuilder (HELIOS scenario)`
- `feat(p3.5-C.3): PerformanceDrivenBuilder (MERIDIAN scenario)`
- `feat(p3.5-C.4): DataInsufficientBuilder (onboarding scenario)`
- `feat(p3.5-C.5): endpoint GET /api/cockpit/strategique + tests integ`
- `test(p3.5-C.6): source-guards anti-régression strategique`

### Vague D — Frontend

| # | Item | Fichier(s) | Effort |
|---|---|---|---|
| D.1 | API client `getCockpitStrategique` | `frontend/src/api/cockpit.js` | 0.5 j/h |
| D.2 | `<StrategicModeBanner />` | `frontend/src/components/grammar/hub/StrategicModeBanner.jsx` | 0.5 j/h |
| D.3 | `<CadreApplicable />` | `frontend/src/components/grammar/hub/CadreApplicable.jsx` | 1 j/h |
| D.4 | `<VerdictFinal />` | `frontend/src/components/grammar/hub/VerdictFinal.jsx` | 0.5 j/h |
| D.5 | `<ChartFrameTrajectoryLine />` | `frontend/src/components/grammar/hub/charts/ChartFrameTrajectoryLine.jsx` | 1 j/h |
| D.6 | `<ChartFrameBenchSites />` | `frontend/src/components/grammar/hub/charts/ChartFrameBenchSites.jsx` | 1 j/h |
| D.7 | `<DossierP1 />` (réutilise primitifs Briefing) | `frontend/src/components/grammar/hub/DossierP1.jsx` | 1 j/h |
| D.8 | Page `CockpitStrategique.jsx` | `frontend/src/pages/CockpitStrategique.jsx` | 1.5 j/h |
| D.9 | Route `App.jsx` | `frontend/src/App.jsx` | 0.25 j/h |
| D.10 | Tests Vitest (modes × personas) | `frontend/tests/pages/CockpitStrategique.test.jsx` | 1 j/h |
| D.11 | Recapture Playwright (3 modes) | `frontend/tests/visual/cockpit-strategique.spec.ts` | 1 j/h |

**Commits** :
- `feat(p3.5-D.1): primitifs Sol — StrategicModeBanner + CadreApplicable + VerdictFinal`
- `feat(p3.5-D.2): chart primitives — TrajectoryLine + BenchSites`
- `feat(p3.5-D.3): page CockpitStrategique + dispatcher mode`
- `test(p3.5-D.4): Vitest CockpitStrategique + Playwright capture 3 modes`

### Vague E — DoD + bilan

| # | Item | Fichier | Effort |
|---|---|---|---|
| E.1 | Bilan baseline tests (FE/BE/source-guards) | terminal | 0.25 j/h |
| E.2 | DoD checklist par qa-guardian agent | conversation | 0.5 j/h |
| E.3 | Documentation `docs/dev/synthese_strategique_runbook.md` | doc | 0.5 j/h |
| E.4 | Push origin + draft PR | git | 0.25 j/h |

**Commit final** : `docs(p3.5-E): runbook Synthèse stratégique + DoD Phase 3.5`

**Total estimé Phase 3.5 (3 modes prioritaires) ≈ 27 j/h** sur 5-7 jours calendaires effectifs.

---

## DoD Phase 3.5 — checklist non-négociable

- [ ] Endpoint `GET /api/cockpit/strategique` répond 200 sur HELIOS et MERIDIAN
- [ ] `payload.strategic_mode` ∈ {regulatory_driven, performance_driven, data_insufficient}
- [ ] `payload.applicability` contient les 5 règles avec `reason_human` non vide
- [ ] `payload.kpis.length === 3` strictement
- [ ] `payload.charts.length === 2` strictement
- [ ] `payload.dossier_p1` complet (proof_pills, scenarios, timeline, why_promeos)
- [ ] `payload.verdict.{constraint,opportunity}` non vides
- [ ] `payload.footer.version_tags` inclut `Assujettissement v1.0`
- [ ] Page `/cockpit/strategique` rend 3 modes sans crash (Playwright capture commitée)
- [ ] Persona switch ne change PAS le mode (test E2E)
- [ ] Source-guards verts : `test_applicability_engine` + `test_strategique_data_driven`
- [ ] Baseline FE ≥ 4 515 + BE ≥ 7 103, **strictement non régressée**
- [ ] `/code-review` et `/simplify` exécutés avant commit final
- [ ] Draft PR pushée sur origin avec checklist DoD cochée dans le body

---

## Anti-patterns à refuser (rappel ADR-023 §6)

| AP | Description |
|---|---|
| AP-stratX1 | Trajectoire DT/BACS affichée si statut UNKNOWN ou DATA_MISSING |
| AP-stratX2 | `strategic_mode` hardcodé dans la route ou un builder |
| AP-stratX3 | Builder qui appelle la DB pour évaluer une règle (doit passer par service) |
| AP-stratX4 | Verdict final ("contrainte principale") en dur dans le frontend |
| AP-stratX5 | > 5 highlights ou < 3 dans la file P2/P3 |
| AP-stratX6 | KPI sans `trace` complète (source, formula, scope, freshness) |
| AP-stratX7 | Nom de site/portefeuille en dur dans un builder |
| AP-stratX8 | Workflow gouvernance sans owner + échéance + pièce + décision |

Si l'agent rencontre un de ces patterns dans le code existant qu'il s'apprête à toucher, il doit **le signaler dans son compte-rendu** plutôt que de l'effacer silencieusement.

---

## Sortie attendue de la session

À la clôture, l'agent doit produire :

1. **Bilan exécutif** : 5-10 lignes résumant ce qui est livré, ce qui reste, baseline atteinte
2. **PR draft URL** sur `origin/claude/refonte-sol2`
3. **Liste des screenshots Playwright** committées (3 modes × 1 viewport minimum)
4. **Checklist DoD complète** cochée
5. **Punchlist Phase 3.6** (2 modes restants : PROCUREMENT + OPPORTUNITY, 4 chart types restants)

---

## Notes de cadrage

- **Pas de calcul climate-driven, ETS2, CSRD** dans cette phase. Si l'envie est forte → ADR séparée + Phase 4+.
- **Pas de modification du moteur de priorisation** (`backend/regops/priority_scoring.py`). Il est consommé tel quel.
- **Pas de refonte de la page Briefing** dans cette phase. Le pattern est figé sur commit `32916787`.
- **Persona DG/COMEX par défaut** sur `/cockpit/strategique` (vs Responsable Énergie sur `/cockpit/jour`).
- **Période par défaut** = `month` (vs `week` sur Briefing).

---

**Auteur** : session Sol v1.1 du 13/05/2026 (Claude Code Opus 4.7).
**Suivi** : ce prompt est versionné `v1.0`. Toute modification → bump version + commit.
