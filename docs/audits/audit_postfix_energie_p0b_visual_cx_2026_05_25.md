# Audit postfix — Énergie P0b Visual CX Credibility (2026-05-27)

**Branche** : `claude/energie-p0b-visual-cx-credibility`
**Base** : `claude/refonte-sol2` après merge PR #314 (squash `2bd20ba6`)
**Verdict** : 🟢 **GO MERGE** — 7 chantiers P0b clos. Playwright réel HELIOS confirme **0 console error** sur les 5 pages touchées (avant : 7 warnings `duplicate key` sur `/usages`). Tests : BE 83 verts + FE 74 verts.

---

## 1 — Livrables par chantier

### C1 — Score Monitoring borné [0, 100]

**Fichiers** : [`backend/services/electric_monitoring/monitoring_orchestrator.py:250-279`](backend/services/electric_monitoring/monitoring_orchestrator.py#L250) + [`backend/routes/monitoring.py`](backend/routes/monitoring.py)

- `_persist_snapshot()` : helper `_clamp_score()` posé sur `data_quality_score` + `risk_power_score` avant insertion DB.
- `routes/monitoring.py` : helper module-level `_clamp_monitoring_score()` + appliqué sur 5 callsites (snapshot principal `194-195`, compare `308-309`, list `403-404`). Defense-in-depth pour les snapshots legacy.
- Tests dédiés : [`backend/tests/test_monitoring_score_clamp_p0b.py`](backend/tests/test_monitoring_score_clamp_p0b.py) (5/5) : 108→100, négatif→0, in-range préservé, None préservé, string invalide→0.

### C2 — Breadcrumb « Portefeuille »

**Fichier** : [`frontend/src/layout/Breadcrumb.jsx:30-35`](frontend/src/layout/Breadcrumb.jsx#L30)

- `portfolio: 'Regroupement'` → `portfolio: 'Portefeuille'`. Alignement rail (« Portefeuille » dans `ConsommationsPage` tabs) + breadcrumb + H1 (`ConsumptionPortfolioPage` rend déjà « Portefeuille Consommation »).

### C3 — Diagnostic EmptyState 3 variantes

**Fichier** : [`frontend/src/pages/ConsumptionDiagPage.jsx:1092-1134, 1136-1167`](frontend/src/pages/ConsumptionDiagPage.jsx#L1092)

- **Cas 1** (jamais analysé) — `!summary` → EmptyState wording legacy « Aucun gisement détecté » + 2 CTAs (jeu d'essai + lancer diagnostic).
- **Cas 2** (analysé sans anomalie) — `summary && total_insights === 0` → EmptyState « Aucune anomalie détectée sur la période » + CTA primaire « Relancer l'analyse » (`data-testid=diagnostic-empty-cta`).
- **Cas 3** (données insuffisantes) — `filteredInsights.every(i => i.type === 'data_gap')` → banner inline jaune `data-testid=diagnostic-data-gap-banner` au-dessus du DiagHeader : « Données insuffisantes : les écarts détectés concernent uniquement des lacunes de données. Complétez la collecte (compteurs, CDC) pour permettre un diagnostic réel. »

### C4 — `/usages` duplicate keys

**Fichier** : [`frontend/src/components/usages/HeatmapCard.jsx:50-55, 105-111`](frontend/src/components/usages/HeatmapCard.jsx#L50)

- Root cause : 2 rangées (header + footer ADEME) itéraient `usages.map((u) => <div key={u}/>)` dans le **même parent grid** → React voit `key=u1, u2, u3, u4` deux fois dans le même scope → 7 warnings « duplicate key » (7 = 4 emojis dupliqués au tour 1 + 3 au tour 2 selon le re-render).
- Fix : préfixes `key={`head-${u}`}` (rangée header) + `key={`ademe-${u}`}` (rangée footer Réf. ADEME).
- **Playwright HELIOS** : `/usages` post-fix = **0 console error** (avant : 7 warnings).

### C5 — Emojis UI corporate

**Fichiers** : [`frontend/src/pages/UsagesDashboardPage.jsx`](frontend/src/pages/UsagesDashboardPage.jsx) + [`frontend/src/components/usages/TabBar.jsx`](frontend/src/components/usages/TabBar.jsx) + [`frontend/src/pages/ConsumptionDiagPage.jsx`](frontend/src/pages/ConsumptionDiagPage.jsx)

| Emoji | Remplacé par lucide-react |
|---|---|
| 📈 Évolution | `TrendingUp` |
| 📊 Baseline | `BarChart2` |
| 🔌 Comptage | `Plug` |
| 📊 Excel | `FileSpreadsheet` |
| 🖨 PDF | `Printer` |
| LEVER_ICONS `🌡️ 🔌 ❄️ ⚡` | `Thermometer / Plug / Snowflake / Zap` |

`TabBar` enrichi avec support de `tabs[].icon` (rétro-compat : sans icône, rendu identique).

### C6 — Memobox retiré du wrapper Consommations

**Fichier** : [`frontend/src/pages/ConsommationsPage.jsx:11-21`](frontend/src/pages/ConsommationsPage.jsx#L11)

- Tab `{ to: '/kb', label: 'Memobox', icon: Database }` retiré. Le wrapper Consommations a maintenant 3 tabs (Portefeuille / Explorer / Import). Import `Database` retiré du `import { … } from 'lucide-react'`.
- `/kb` reste accessible via module admin NavRegistry + deep-link bookmark + ⌘K search.

### C7 — Sidebar Administration mode normal

**Fichier** : [`frontend/src/layout/NavRegistry.js:1025-1031`](frontend/src/layout/NavRegistry.js#L1025) (déjà conforme)

- Vérification source-guard G7 : `getOrderedModules(role, isExpert)` n'ajoute le module admin que si `isExpert` (`if (isExpert && byKey.admin) ordered.push(byKey.admin)`).
- `NAV_MODULES.admin` reste `expertOnly: true`. **Aucun fix code nécessaire** — comportement déjà correct ; ajout de 2 source-guards G7 pour verrouiller la spec.

---

## 2 — Source-guards anti-régression

Fichier : [`backend/tests/source_guards/test_energie_p0b_visual_cx_source_guards.py`](backend/tests/source_guards/test_energie_p0b_visual_cx_source_guards.py) (9 tests, 196 lignes)

| Test | Vérification |
|---|---|
| `test_g1_monitoring_orchestrator_clamps_score` | Helper `_clamp_score` présent dans orchestrator |
| `test_g1_monitoring_route_clamps_score` | `_clamp_monitoring_score` présent + ≥ 5 callsites |
| `test_g2_breadcrumb_portfolio_label_is_portefeuille` | « Portefeuille » présent + « Regroupement » absent |
| `test_g3_diagnostic_emptystate_2_variants_plus_data_gap_banner` | Wording « Aucune anomalie détectée » + CTA « Relancer l'analyse » + testid `diagnostic-data-gap-banner` |
| `test_g4_heatmap_card_no_duplicate_usage_keys` | Préfixes `head-` + `ademe-` dans HeatmapCard |
| `test_g5_no_corporate_emoji_in_energie_pages` | 📈 📊 🔌 🖨 absents (hors commentaires) |
| `test_g6_consommations_wrapper_no_memobox_tab` | `to: '/kb'` absent + label `Memobox` absent |
| `test_g7_admin_module_hidden_when_not_expert` | `if (isExpert && byKey.admin)` présent |
| `test_g7_admin_module_expert_only` | `expertOnly: true` sur module admin |

---

## 3 — Smoke live HELIOS (BE git_sha=`2bd20ba6`)

```
GET /api/monitoring/snapshots          → 200 (vide sur HELIOS, normal pas de snapshot run)
GET /api/cockpit/pilotage              → 410 ✅ (non-régression P0a)
GET /api/consumption/insights          → 200 ✅
GET /api/cockpit/jour + strategique    → 200 ✅
GET /api/v4/action-center/items        → 200 ✅
```

## 4 — Playwright réel HELIOS (node + playwright 1.59.1 headless chromium 1440×900)

```
Login demo → 5 pages touchées par P0b :
  /consommations/portfolio  → 0 console error
  /monitoring               → 0 console error
  /usages                   → 0 console error  ← avant P0b : 7 warnings duplicate-key
  /diagnostic-conso         → 0 console error
  /flex                     → 0 console error  ← hidden page accessible deep-link OK

Console errors total : 0
Network 4xx/5xx total: 0
Duplicate-key warnings: 0 ← brief C4 résolu
410 Gone appelés     : 0
Navigations /anomalies: 0 (anti-régression #311)
```

---

## 5 — Tests anti-régression cumulatifs

| Suite | Résultat |
|---|---|
| BE `tests/test_monitoring_score_clamp_p0b.py` | **5/5 ✅** (nouveau) |
| BE `tests/source_guards/test_energie_p0b_visual_cx_source_guards.py` (G1-G7) | **9/9 ✅** (nouveau) |
| BE source-guards `-k "cockpit or billing or energie"` (cumulatif post-P0b) | **78 verts ✅** |
| FE `pages/cockpit/__tests__/` + `pages/action-center-v4/components/drawer/__tests__/` + `__tests__/ux-hardening.test.js` | **74/74 ✅** |
| **Total** | **78 BE + 74 FE = 152 tests verts** |

---

## 6 — Critères d'acceptation brief (11/11 ✅)

| # | Critère | État |
|---|---|---|
| 1 | Score Monitoring toujours 0–100 | ✅ BE clamp orchestrator + endpoint + 5 tests |
| 2 | Breadcrumb Portefeuille cohérent | ✅ Breadcrumb.jsx + G2 |
| 3 | Diagnostic a un EmptyState clair | ✅ 2 EmptyState variantes (cas 1, 2) + banner data_gap (cas 3) |
| 4 | /usages sans duplicate key warning | ✅ Playwright HELIOS = 0 warning (avant 7) |
| 5 | Aucun emoji dans labels énergie | ✅ G5 source-guard + remplacement lucide |
| 6 | Memobox retiré de Consommations | ✅ wrapper 3 tabs (Portefeuille/Explorer/Import) |
| 7 | Administration cachée en mode normal | ✅ G7 vérifie `getOrderedModules` gate `isExpert` |
| 8 | Aucun nouveau menu | ✅ pas de nouvel item NAV_SECTIONS |
| 9 | Aucun écran fantôme | ✅ aucune page créée |
| 10 | Tests verts | ✅ 152 BE+FE verts |
| 11 | Audit livré | ✅ ce document |

---

## 7 — Décisions clés

1. **C1 BE clamp double-couche** : `_persist_snapshot()` (orchestrator) corrige les nouveaux snapshots ; `_clamp_monitoring_score()` (route) corrige defense-in-depth la lecture des snapshots legacy déjà persistés avec score 108. Pattern conforme « jamais faire confiance à la donnée legacy ».
2. **C2 single source of truth breadcrumb** : Breadcrumb.jsx contient un override `portfolio:` qui surchargeait `ALL_NAV_ITEMS` (qui rend « Portefeuille » via NavRegistry). Fix : aligner l'override sur le rail.
3. **C3 3 variantes EmptyState** : 2 EmptyState (cas 1 = jamais analysé / cas 2 = analysé sans anomalie) + 1 banner inline (cas 3 = data_gap). Pas de 4e variante car le composant principal continue à rendre les insights non-data_gap normalement.
4. **C4 préfixes keys** : pattern stable (`head-${u}`, `ademe-${u}`) plutôt qu'un refactor des 3 rangées en sous-composants — minimum diff, max impact (0 → 0 warning).
5. **C5 LEVER_ICONS** : passé d'emoji strings vers icônes-component pour cohérence avec le reste du projet (lucide-react est déjà la convention). Rendu : `<Icon size={16}/>` au lieu de `<span>{emoji}</span>`.
6. **C6 plutôt que move** : on retire Memobox du wrapper Consommations sans le déplacer ailleurs — `/kb` est déjà accessible via le module admin (NavRegistry) qui est gated `expertOnly`. Cohérent avec C7.
7. **C7 verification sans fix** : la spec était déjà respectée ; on ajoute juste 2 source-guards pour verrouiller (un futur dev qui retire le `if (isExpert && …)` casserait le test).
8. **Pas de refactor Sol** : brief explicite « Ne pas lancer une refonte Sol complète. Corriger uniquement les irritants P0 visibles ». Tous les changements sont chirurgicaux.

---

## 8 — Dette résiduelle

Aucune nouvelle dette créée. Dette pré-existante héritée (audit menu Énergie #313 P1-P2) inchangée :
- P1-1 renommer « Répartition par usage » → « Usages énergétiques »
- P1-2 fusionner `/usages-horaires` dans `/usages`
- P1-3 audit IS11 `/api/energie/import/jobs` sans scope
- L8 Mois 5 cutover legacy pages (CockpitPilotage.jsx, etc.)

---

## Verdict

🟢 **GO MERGE** — 7 chantiers P0b clos sans nouveau menu, sans écran fantôme, sans réintroduire `/cockpit/pilotage` ni `/usage-steering`, sans réintroduire Flex en sidebar. Le DAF voit désormais :
- des scores Monitoring crédibles (0-100),
- un breadcrumb cohérent (« Portefeuille »),
- un Diagnostic qui distingue 3 états (vide / sans anomalie / données insuffisantes),
- une page Usages sans warning React,
- des onglets sans emoji corporate,
- un wrapper Consommations propre (3 tabs cohérentes),
- une sidebar mode normal sans Administration.

Le sprint suivant (Usage Steering = 4e tab `pilotage` dans `/usages`) peut démarrer sur cette base saine.
