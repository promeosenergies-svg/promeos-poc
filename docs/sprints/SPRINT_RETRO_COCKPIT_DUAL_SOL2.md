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
pré-existante 93 fails non touchée. Recommandation prochaine : Phase 25
`vite build && vite preview` pour déverrouiller audit Playwright +
Phase 26 panel utilisateur réel avant merge sur `main`.
