# Source guards CI — inventaire

> Liste consolidée des garde-fous mécaniques actifs sur la branche
> `claude/refonte-sol2` post Sprint Grammaire v1.2 Phase F.
> Maintenir à jour à chaque ajout de guard.

---

## Guards Vitest (frontend pure-grep)

| Guard | Fichier | Phase | Rôle |
|---|---|---|---|
| **SG_HUB_L11_01** | `frontend/src/__tests__/source_guards/cockpit_jour_l11_fe_source_guards.test.js` | Step 6 + F.1 + F.2 + F.3 + F.5 | Primitifs L11 requis (HubPage, SolHeroPremiumNight, ChartFrame, HubHighlight, HubPageFooter, HubKpiCard) importés depuis `components/grammar`. Plus : marqueurs `data-page` + `data-doctrine`, `useFilter()`, `getCockpitJour`, ChartFrame variants flexibles (≥1 enfant `<ChartFrame*>`), pas de `<svg>` inline, HubSkeleton/HubError conditionnels, AutoTerm import + usage. |
| **SG_HUB_L11_02** | idem | Step 6 | Marque PROMEOS toujours en majuscules sans accent (forbidden : Promeos, Proméos, promeos, proméos, ProMeos). |
| **SG_HUB_L11_03** | idem | Step 6 | Pas de formulation trompeuse hardcodée (100% sans contexte, Total ARR, garanti/garantie). |
| **Per-primitive source guards** | `frontend/src/components/grammar/hub/__tests__/*.test.js` | F.1 → F.5 | 9 fichiers : HubKpiCard, ChartFrameBars, ChartFrameLine, HubSkeleton, HubError, ChartFrame, HubHighlight, HubPage, HubPageFooter, SolHeroPremiumNight (data-* + JSDoc typedef + tokens-only + defensive null-render). |
| **Term + AutoTerm source guards** | `frontend/src/components/grammar/__tests__/Term.test.js` + `AutoTerm.test.js` | F.5 + F.6 | Term variants (inline-tooltip/short/narrative/preserve-text), AutoTerm tokenisation regex word-boundary + tri longueur décroissante + default `preserve-text`. |
| **Phase F.7 meta-guards** | `frontend/src/__tests__/source_guards/phase_f7_meta_guards.test.js` | F.7 | Valide existence + exécutabilité + comportement du Guard A (shell) + Hook B (Husky). 14 tests. |

---

## Guards shell (CI build + pre-commit local)

| Guard | Fichier | Phase | Rôle |
|---|---|---|---|
| **Guard A — kpi-not-inline-in-hub-pages** | `scripts/source_guards_design_system.sh` | **F.7** | Scan 12 pages-hub L11 (cockpit/jour + futurs energie/conformite/factures/achat/patrimoine + cockpit/strategique + cockpit/decision). Détecte (1) `className kpi-*` inline, (2) définition locale `function KpiTriptychCard/KpiCard/MetricCard/KpiBlock`. Exit 1 si violation. |

Exécution :

- Local : `bash scripts/source_guards_design_system.sh`
- Pre-commit : invoqué automatiquement par `.husky/pre-commit` après `lint-staged`.
- CI : à invoquer depuis `.github/workflows/*.yml` (TODO si pas encore en place).

---

## Hooks Husky (commit-time)

| Hook | Fichier | Phase | Rôle |
|---|---|---|---|
| **pre-commit** | `.husky/pre-commit` | (existant) + F.7 | Lance `lint-staged` (ruff + eslint + prettier) **puis** Guard A. |
| **Hook B — commit-msg** | `.husky/commit-msg` | **F.7** | Si message commence par `docs(...)`, refuse les commits dont staged contient des fichiers non-docs (`.jsx`, `.py`, `.js`, `.ts`, etc.). Cible la récidive de la contamination commit `3774d2c0` (16 fichiers WIP parallèle embarqués sous `docs(p3.4)`). Patterns autorisés : `docs/`, `*.md`, `*.mdx`, `*.yaml`, `*.yml`, `CLAUDE.md`, `README.md`. |

---

## Tests négatifs validés (smoke F.7)

| Scénario | Guard concerné | Résultat |
|---|---|---|
| Injection `function KpiTriptychCard()` dans CockpitJour.jsx | Guard A | **Exit 1 ✓** |
| Modif `.jsx` staged + commit-msg `docs(p3.4): test` | Hook B | **Exit 1 ✓** |
| État propre (post F.6) | Guard A | **Exit 0 ✓** |

---

## Backlog P2 (guards non-bloquants tracés `docs/debt/p2_backlog.md`)

- **P2-debt-BE-sites-isdemo-filter-other-endpoints** : appliquer le filtre `Site.is_demo == Organisation.is_demo` aux 4 helpers `_sites_for_org` clonés + 12 routes faisant `db.query(Site)` directs. Voir entrée dédiée.
- **P2-debt-BE-cockpit-jour-charts-series-hp-hc** : backend payload manque `series_hp` / `series_hc` (fallback synthétique `generateSyntheticHC()` en place).
