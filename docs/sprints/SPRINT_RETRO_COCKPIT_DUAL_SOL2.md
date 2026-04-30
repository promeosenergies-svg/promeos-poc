# Sprint Retro — Refonte Cockpit Dual Sol2

> Bilan complet de fin de sprint pour relecture Amine ↔ Claude (instance externe).
>
> Branche : `claude/refonte-sol2`
> Période : 2026-04-26 → 2026-04-30
> Durée : 5 jours
> Commits : 139 commits atomiques
> SHA départ : `492a0db2` (Phase 0 — fork POC + lock vite port 5175)
> SHA fin : `0e346c4b` (Phase 24.1 — bump timeout Playwright)

## Index des outputs

Tous les artefacts sont dans `docs/sprints/SPRINT_RETRO_COCKPIT_DUAL_SOL2/` :

### outputs/

- `git_range.txt` : SHA de départ et de fin
- `all_commits.txt` : liste complète des 139 commits du sprint
- `commits_per_phase.txt` : décompte par phase (Phase 0–24)
- `phase_0_deletions.txt` : preuves suppression composants/models Phase 0
- `phase_1_services.txt` : services backend créés Phase 1 (8/9 attendus)
- `phase_1_models.txt` : modèles SQLAlchemy `EurAmount` + `BaselineCalibration`
- `phase_1_surface.txt` : vérification surface HELIOS (`sites.surface_m2 = 17 500`)
- `phase_1_frontend_cleanup.txt` : suppression models JS Phase 1.4 (3/5 supprimés)
- `phase_3_legacy_redirects.txt` : routes legacy → table factorisée `legacyRedirects.js`
- `facts_endpoint.txt` : structure du payload `/api/cockpit/_facts` (TestClient)
- `facts_endpoint.json` : payload complet brut (env. 11 top-level keys)
- `source_guards_list.txt` : 32 sentinels attendus, **10 exact-match** présents
- `test_run.txt` : résumé exécution tests BE + FE
- `test_baselines.txt` : comparaison vs baselines pré-sprint
- `pytest_full.log` : log fin pytest (8 lignes summary, run 33 min)
- `vitest_full.log` : log complet vitest (4 255 passed)
- `network_count_strategique.json` : 128 req mount /strategique (4 endpoints REST)
- `network_count_jour.json` : 128 req mount /jour (idem)
- `network_metrics_summary.txt` : analyse Vite dev artefacts vs APIs réelles
- `visual_density.txt` : densité 4-6/7 blocs above-the-fold (3 routes auditées)
- `phase_4_user_tests.md` : **NON RÉALISÉ** — proxy 14 agents Claude
- `sprint_narrative.md` : narratif subjectif honnête (succès / bugs / dette)
- `playwright_phase17_manifest.json` : manifest 16 routes audit Phase 17
- `blockers.txt` : blocages rencontrés pendant la collecte (BE saturé etc.)

### captures/

- `sprint-end/cockpit-pilotage.png` : capture finale `/cockpit/jour`
- `sprint-end/cockpit-strategique.png` : capture finale `/cockpit/strategique`
- `sprint-end/conformite.png` : capture finale `/conformite`
- `phase-0-end/` : 4 captures pré-refonte (cockpit, patrimoine, conformite, bill-intel)
- `CAPTURES_INDEX.md` : index lisible des captures

## Compteurs synthétiques

| Métrique | Baseline pré-sprint | Cible | Réalisé | Statut |
|---|---|---|---|---|
| Tests BE passing | 5 861 (pre-V120) / 6 027 (V120 floor) | ≥ 5 900 | **6 183** | ✅ +156 vs floor |
| Tests FE passing | 4 237 | ≥ 4 270 | **4 255** | ⚠ +18 (sous cible) |
| Source-guards exact-match | — | ≥ 30 | **10/32** | ⚠ partiel (renamings non vérifiés) |
| Commits Phase 0 | — | 6 | **1** explicite | ⚠ naming non aligné |
| Commits Phase 1 | — | 9 | **6** | ⚠ |
| Commits Phase 2 | — | 5 | **11** | ✅ dépassé |
| Commits Phase 3 | — | 4 | **13** | ✅ dépassé |
| Commits Phase 13–24 (étendus) | — | n/a | **27** | ✅ phases polish |
| Sites HELIOS surface_m2 | 35 000 | 17 500 | **17 500** | ✅ corrigé |
| Requêtes mount /strategique | 131 | < 50 | **128** | ❌ artefact Vite dev |
| Requêtes mount /jour | n/a | < 50 | **128** | ❌ idem |
| Models JS supprimés (Phase 1.4) | 0 | 5 | **3** | ⚠ 2 résiduels |
| Densité blocs above-the-fold | inconnue | ≤ 7 | **4–6** sur 3 routes | ✅ |
| Routes Cockpit dual créées | 0 | 2 | **2 + 31 redirects** | ✅ dépassé |

## Synthèse en 5 lignes

Le sprint Refonte Cockpit Dual Sol2 a livré la **plateforme Cockpit
dual** (`/cockpit/strategique` CFO + `/cockpit/jour` Energy Manager)
+ **doctrine v1.1 exécutable** (`backend/doctrine/`) + **+322 tests
BE passing** + **31 redirects legacy factorisés**, sur 5 jours et 139
commits atomiques. Ce qui a fonctionné : audits 14 agents systématiques,
SoT `regulatory_rates.js`, consolidation 3 glossaires via façades zero
refactor. Ce qui a buggé : régression Playwright login (Phase 20→23),
arithmétique APER (Phase 23→23.bis), 13/16 routes timeout sur Vite dev
(non résolu, root cause infra). Trade-offs acceptés : Phase 4 panel
humain non réalisée (proxy IA seul), 2 models JS résiduels, dette
pré-existante 93 fails non touchée. **Mini-sprint Phase 4bis correctif
livré post-revue Claude externe (6 nouveaux source-guards, 42 tests,
density_mode implémenté).** Recommandation prochaine : Phase 25
`vite build && vite preview` pour déverrouiller audit Playwright +
Phase 26 panel utilisateur réel avant merge sur `main`.

## Mini-sprint Phase 4bis correctif (post-revue Claude externe)

Suite à la revue par Claude (instance externe) du Sprint Retro initial,
3 zones doctrinales ont été identifiées comme insuffisamment garde-fou-ées.
Mini-sprint Phase 4bis livré le 2026-04-30 (~2h, 4 commits).

### Phase 4bis.1 — Verrouillage source unique `_facts` (commit `697ca99c`)

Sentinels #9 + #10 du remapping. Avant : "source unique" tenue de
fait mais sans garde-fou test.

- `test_cockpit_facts_unique_source.py` (3 tests) : AST scan garantit
  `def get_cockpit_facts` défini UNE SEULE FOIS dans backend/, route
  `/api/cockpit/_facts` appelle directement le service (pas de fork),
  aucune autre route ne reconstruit ≥ 5 CANONICAL_KEYS.
- `test_cockpit_facts_no_recompute.py` (10 tests) : 9 tests parametrize
  sur les 9 helpers `_build_*` (chacun défini une seule fois) +
  `test_get_cockpit_facts_orchestrates_all_builders` (orchestration
  complète vérifiée par AST unparse).
- **Résultat : 13/13 tests verts.**

### Phase 4bis.2 — Implémentation `density_mode` (commit `1417644c`)

Sentinels #14 + #15 du remapping. Avant : `scope.density_mode = null`
en runtime, feature annoncée par contrat API mais non implémentée.

- 2 constantes SoT : `DENSITY_THRESHOLD_DIRECT_MAX = 5` /
  `DENSITY_THRESHOLD_CONDENSED_MAX = 15`.
- Helper `_compute_density_mode(site_count)` retourne
  `"direct" | "condensed" | "clusters"` (doctrine §11.3).
- `_build_scope` étend le payload avec `density_mode` + `density_thresholds`
  pour que le frontend puisse expliquer le mode au CFO sans business
  logic FE.
- `test_density_mode_consistent.py` (12 tests) : 9 paramétrés sur les
  bornes (0,1,5,6,10,15,16,50,200), constantes module-level vérifiées,
  ordre strict des seuils, edge case négatif.
- `test_density_mode_helios_direct.py` (4 tests) : présence dans
  payload, thresholds SoT, HELIOS 5 sites = `direct`, cohérence
  site_count ↔ mode.
- **Résultat : 16/16 tests verts.**

### Phase 4bis.3 — Triptyque temporel + drill-down réciproque (commit `449696ae`)

Sentinels #23 + #30 du remapping. Avant : triptyque tenu de fait, link
Décision↔Pilotage déjà implémenté Phase 17.bis.D mais sans garde-fou.

- `test_pilotage_triptyque_temporal_scales.py` (8 tests) : présence
  simultanée des 3 échelles dans `_facts` :
  - Court terme : `consumption.j_minus_1_mwh` + `power.peak_j_minus_1_kw`
  - Moyen terme : `consumption.monthly_vs_n1` (4 sous-clés canoniques)
  - Long terme : `consumption.annual_mwh` + `trajectory_2030_score`
  - Test combiné : alerte si une échelle droppe silencieusement.
  - Sanity check unités : MWh < 100 000 (jamais kWh ni Wh).
- `test_pilotage_action_has_decision_link.py` (5 tests) : verrouille
  les 2 directions du drill-down — Décision→Pilotage
  (`/cockpit/jour?focus=action-{id}`), Pilotage→Décision (parsing
  `?focus=action-` + `?focus=decision-` côté FE), interdiction
  régression vers ancres legacy `#decision-X`.
- **Résultat : 13/13 tests verts.**

### Phase 4bis.4 — Documentation dette technique restante

Cette section. Mise à jour SPRINT_RETRO avec :
- 5 source-guards partiels listés explicitement (cf ci-dessous)
- Phase 4 panel humain dette doctrinale (à mobiliser Sprint Q3 2026)
- Network prod mesure différée (à valider avant production)

### Bilan mini-sprint Phase 4bis

| Phase | Sentinels traités | Tests créés | Statut |
|---|---|---|---|
| 4bis.1 | #9 + #10 | 13 | ✅ verts |
| 4bis.2 | #14 + #15 (+ feature `density_mode`) | 16 | ✅ verts |
| 4bis.3 | #23 + #30 | 13 | ✅ verts |
| 4bis.4 | (doc) | — | ✅ |
| **Total** | **6/6 vrais trous fermés** | **42 nouveaux tests** | **✅** |

Couverture sentinels post Phase 4bis : **27/32 (84 %) couverts solidement**
(7 exact + 14 renommés confirmés + 6 ajoutés) + 5 partiels = **32/32 traités**.

## Dette technique restante après Phase 4bis

### Source-guards partiels (à raffiner Phase 25+)

Les 5 sentinels classés "partiel" dans `outputs/source_guards_remapping.md`
couvrent la sémantique mais pas la spec littérale. Acceptable, mais
peuvent être renforcés :

| # | Sentinel partiel | Lacune | Action future |
|---|---|---|---|
| 1 | `test_helios_no_demo_sites_leak` | couvre seeding strict, pas le leak per se | ajouter test "site_ids ne contient PAS de site issu d'un autre pack" |
| 6 | `test_baseline_r_squared_threshold` | couvre présence champ, pas le seuil | ajouter test "r_squared > 0.7 quand baseline=b_dju_adjusted" |
| 19 | `test_facture_portfolio_aggregation` | seuil unitaire, pas aggregation | ajouter test "sum(facture_per_site) == facture_portfolio" |
| 24 | `test_no_surconso_7d_in_kpi_hero` | concept présent (`surconso_7d_mwh` exposé) mais pas garde-fou "absent du KPI hero" | ajouter test FE "KPI hero ne contient pas surconso_7d" |
| 25 | `test_monthly_kpi_tooltip_complete` | couvre présence bloc, pas tooltip exhaustif | ajouter test FE "tooltip monthly contient ≥ 5 lignes" |

### Phase 4 — Panel utilisateur humain (dette doctrinale)

**Statut** : non réalisé. Documenté dans `outputs/phase_4_user_tests.md`.
Proxy effectué : 14 agents Claude IA en audits parallèles.

**Plan rattrapage** : Sprint Q3 2026 (juin-juillet, alignement programme
12 semaines `project_refonte_sol_doctrine_3mois.md`) :

- Session 1 — CFO Jean-Marc (DAF tertiaire mid-market, 30s)
- Session 2 — Energy Manager Marie (responsable conformité, 30s)
- Session 3 — DG investisseur (préparation démo intégrale juillet 2026)

Critères chronométrés :

- Délai jusqu'à identification du risque réglementaire (cible ≤ 30s)
- Délai jusqu'à identification des 3 décisions à arbitrer (cible ≤ 60s)
- Verbatim post-démo (1 phrase libre)

### Network prod mesure (dette technique pré-production)

**Statut** : déféré. Documenté dans `outputs/network_count_prod_deferred.txt`.

Mesure actuelle (Vite dev) : 128 requêtes au mount, dont 21 bundles JS
servis comme `/api/*.js`. **4 endpoints REST métier réels** identifiés.

Mesure cible (`vite build && vite preview`) attendue : ≤ 50 requêtes
totales, 4-7 endpoints REST.

**À valider avant tout déploiement production**. Effort estimé Phase 25 :
2-3h (build script + warmup + Playwright re-run).

### Tests pré-existants rouges (dette baseline)

- `test_ai_client.py` : `_stub_response()` missing kb_context arg
- `test_ems_overlay.py` : 403 org-scoping sur certains endpoints
- `test_kb_telemetry.py` : cascades hits sqlite IntegrityError

**93 fails + 14 errors total**, hors scope Cockpit dual. Issues
incident V120 / sprint Agent SDK migration. À traiter Phase 27.
