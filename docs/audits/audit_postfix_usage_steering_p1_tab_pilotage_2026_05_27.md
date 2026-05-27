# Audit postfix — Usage Steering P1 — 4ᵉ onglet Pilotage des usages (2026-05-27)

**Branche** : `claude/usage-steering-p1-tab-pilotage`
**Base** : `claude/refonte-sol2` après merge PR #317 (squash `24a773da`)
**Verdict** : 🟢 **GO MERGE** — 4ᵉ onglet « Pilotage des usages » livré dans `/usages` (PAS de nouveau menu, PAS de `/usage-steering`). Live HELIOS : 5 action_candidates uniques (dédup BE) + 3 cards above-the-fold + sync idempotent vers Centre d'Action V4 + banner data-gap. Playwright `/usages?tab=pilotage` : **0 console error**, 0 network 4xx/5xx. Tests : BE 95 verts + FE 74 verts.

---

## 1 — Livrables par chantier

### Phase 0 — Audit court (avant code)

| Vérif | Statut |
|---|---|
| 0 `/usage-steering` FE | ✅ |
| 0 nouveau menu | ✅ |
| 0 calcul métier FE résiduel (post #317) | ✅ |
| `truth_contract` présent (usage_service + power_optimization_service) | ✅ |
| `external_ref` + `source_url` BE | ✅ |
| 0 « Flex Intelligence » côté client | ✅ (SolFlexTeaser orphelin, jamais importé) |
| 2 key={name} restants détectés (CdcSim + FlexBubble) | ⚠️ → C0 |

### C0 — Hygiène Recharts + suppression fallback Math.min

**Fichiers** : `frontend/src/components/usages/CdcSimulationCard.jsx` + `FlexBubbleChart.jsx` + `PowerOptimizationCard.jsx`

| Fichier | Avant | Après |
|---|---|---|
| `CdcSimulationCard.jsx:37` | `key={s.name}` | `key={s.id ?? \`strategy-${idx}-${s.name}\`}` |
| `FlexBubbleChart.jsx:96` | `key={entry.name}` | `key={entry.site_id ?? entry.id ?? \`bubble-${idx}-${entry.name}\`}` |
| `PowerOptimizationCard.jsx:20` | `cs.utilization_pct_safe ?? Math.min(cs.utilization_pct, 100)` | `cs.utilization_pct_safe ?? null` |
| `PowerOptimizationCard.jsx:22` | `cs.overflow_status \|\| (peak > kva)` | `cs.overflow_status ?? 'unknown'` |
| `PowerOptimizationCard.jsx:120` | `(100 - cs.utilization_pct).toFixed(0)` | `utilizationPct != null ? (100 - utilizationPct).toFixed(0) : '—'` |

### C1 — Onglet interne `pilotage` + URL state

**Fichier** : `frontend/src/pages/UsagesDashboardPage.jsx`

- `ALL_TABS` enrichi : `{ id: 'pilotage', label: 'Pilotage des usages', icon: Sliders }` (4ᵉ tab).
- `useSearchParams` : sync `?tab=pilotage` ↔ `activeTab`. Permet le deep-link depuis Centre d'Action V4 (`source_url = /usages?tab=pilotage&site={id}`).
- Helper `handleTabChange` met à jour l'URL (param `tab` retiré si timeline = défaut).
- **Aucun nouveau menu sidebar** (G2 source-guard verrouille).

### C2 — `PilotageTab.jsx` consomme `/api/usages/pilotage-summary`

**Fichier NEW** : `frontend/src/components/usages/PilotageTab.jsx` (273 lignes)

- Consomme `getPilotageSummary({entityId, portefeuilleId, siteId, archetypeCode})` (helper FE ajouté à `services/api/energy.js`).
- Rend 3 sections : header (« N signaux détectés ») / banner data-gap (si all data_gap) / 3 cards above-the-fold.
- Chaque `PilotageCard` affiche :
  - type d'insight (FR clair : `Consommation hors horaires` / `Talon de nuit/WE` / `Pic de puissance` / `Dérive de consommation` / `Lacune de données`)
  - site_id
  - impact € (lecture pure `action.impact_eur`, fallback `—` si null)
  - badge confiance (`Fiable` / `À confirmer` / `À fiabiliser`)
  - action recommandée FR
  - CTA primaire « Créer l'action »
  - lien secondaire « Voir la source » (vers `source_url`)
- Section `<details>` « Détails expert » expose : périmètre, computed_at, insights bruts, score qualité, truth_contract_note (mode expert §C4 brief).

### C3 — Création `ActionCenterItem` V4 (idempotent)

**Fichier BE** : `backend/routes/usages.py:692-833` — endpoint `POST /api/usages/pilotage/sync-action`

| Comportement | Résultat |
|---|---|
| Validation payload : `insight_type`, `site_id`, `external_ref` obligatoires | HTTP 422 sinon |
| Validation pattern `external_ref` commence par `pilotage:` (anti-collision billing/conformite) | HTTP 422 `EXTERNAL_REF_INVALID` |
| Lookup idempotent par `(org_id, external_ref)` indexed UNIQUE (#311) | 0 doublon DB |
| Si item existe et est `OPEN` | HTTP 200 `created=false` |
| Si item existe et est `CLOSED` | HTTP 409 `ACTION_CLOSED` — **jamais ressuscité** (brief C3) |
| Création nouvelle : `kind=recommendation`, `domain=optimisation`, `priority_bracket` par severity (P0-P3) | HTTP 201 |
| `ActionLink` peuplée (target_module=`energie`, uuid5 déterministe), relation `caused_by` | back-link drawer V4 |

**Smoke live HELIOS** : POST identique × 2 = 201 puis 200 même item_id ✅

### C4 — UX/UI

| Critère brief | Implémentation |
|---|---|
| 3 priorités maximum visibles above the fold | `top3 = allCandidates.slice(0, 3)` + footer « N autres signaux dans le Centre d'Action V4 » |
| EmptyState « Aucune dérive prioritaire détectée aujourd'hui. » | `testid=pilotage-tab-empty`, copy émeraude pastel |
| Data gap « Données à compléter pour fiabiliser le pilotage. » | `testid=pilotage-tab-data-gap`, banner amber inline si tous insights = `data_gap` |
| Mode expert : source/formule/période/confiance | `<details>` « Détails expert » expose 5 champs |
| Pas de jargon Flex / NEBCO / AOFD | G5 source-guard vérifie 0 occurrence |

### C5 — Tests + source-guards

| Suite | Résultat |
|---|---|
| BE `tests/test_pilotage_sync_action_p1.py` | **5/5 ✅** (idempotence, CLOSED non ressuscité, external_ref invalid 422, payload incomplet 422, refs distincts → items distincts) |
| BE `tests/source_guards/test_usage_steering_p1_tab_pilotage_source_guards.py` (G1-G7) | **8/8 ✅** |
| BE source-guards cumul `-k "cockpit or billing or energie or usage_steering"` | **95+ verts ✅** |
| FE non-régression `cockpit__tests__/` + `action-center-v4 drawer __tests__/` + `ux-hardening.test.js` | **74/74 ✅** |

#### Détail source-guards G1-G7

| ID | Vérification | Test |
|---|---|---|
| G1 | Aucun `/usage-steering` FE | `test_g1_no_usage_steering_anywhere_fe` |
| G2 | Aucun menu sidebar « Pilotage des usages » | `test_g2_no_pilotage_menu_in_nav_sections` |
| G3 | Aucun `key={X.name}` dans CdcSim + FlexBubble | `test_g3_no_name_only_keys_in_usages_components` |
| G4 | Aucun fallback `Math.min(cs.utilization_pct)` dans PowerOpt | `test_g4_no_math_min_fallback_in_power_optimization` |
| G5 | Aucun NEBCO / AOFD / « revenu flex » / « Flex Intelligence » dans PilotageTab | `test_g5_no_flex_revenue_jargon_in_pilotage_tab` |
| G6 | Onglet `pilotage` dans `ALL_TABS` + `useSearchParams` pour URL state | `test_g6_pilotage_tab_in_all_tabs` + `test_g6_pilotage_tab_uses_internal_url_state` |
| G7 | Endpoint POST sync-action : pattern strict + skip CLOSED + 409 | `test_g7_sync_action_endpoint_idempotent_pattern` |

---

## 2 — Curl smoke HELIOS (BE git_sha=`24a773da`)

```
GET /api/usages/pilotage-summary :
  action_candidates : 5 (dédup OK : True)
  - pilotage:data_gap:site:1   label=24 trou(s) de donnees…
  - pilotage:data_gap:site:2   …
  - pilotage:data_gap:site:3   …
  - pilotage:data_gap:site:4   …
  - pilotage:data_gap:site:5   …

POST /api/usages/pilotage/sync-action (1er run, pilotage:data_gap:site:5)
  → HTTP 201 created=true item_id=b5371767-... domain=optimisation

POST /api/usages/pilotage/sync-action (2e run, même external_ref)
  → HTTP 200 created=false item_id=b5371767-... (idempotent)
```

---

## 3 — Playwright réel HELIOS

```
node + playwright (1.59.1) headless chromium 1440×900
→ login demo → /usages?tab=pilotage
  Tab « Pilotage des usages » visible : true
  pilotage-tab visible                : true
  Cards article rendues               : 3 (brief : max 3) ✅
  data-gap banner                     : true (tous insights data_gap)
  Console errors                      : 0 ← brief « 0 console error »
  Console warnings                    : 4 (toutes React Router future flags, non bloquantes)
  Network 4xx/5xx                     : 0
```

Screenshot : `/tmp/pilotage_final.png` — 4 onglets visibles (Évolution / Baseline / Comptage / Pilotage des usages), 3 cards Lacune données avec impact `—` (None safe), badge « À fiabiliser », CTA « Créer l'action » + « Voir la source », banner amber « Données à compléter ».

---

## 4 — Vérification Action Center V4

| Vérification | Statut |
|---|---|
| POST sync-action crée un ActionCenterItem | ✅ (HTTP 201 + item_id retourné) |
| `domain=optimisation` (enum canonique cohérent doctrine §6.2) | ✅ |
| `kind=recommendation` | ✅ |
| `external_ref` unique par org (index UNIQUE `idx_aci_external_ref` #311) | ✅ |
| `source_url` pointe vers `/usages?tab=pilotage&site={id}` | ✅ (back-link drawer V4 LinksTab) |
| ActionLink peuplée (target_module=`energie`, target_id=uuid5 déterministe) | ✅ |
| Action CLOSED non ressuscitée | ✅ (test BE `test_closed_action_not_resurrected`) |

---

## 5 — Critères d'acceptation brief (12/12 ✅)

| # | Critère | État |
|---|---|---|
| 1 | 4ᵉ onglet visible dans `/usages` | ✅ Sliders icon, label « Pilotage des usages » |
| 2 | Aucun nouveau menu | ✅ G2 source-guard |
| 3 | Aucun `/usage-steering` | ✅ G1 source-guard |
| 4 | Aucun calcul métier FE | ✅ G3 + G4 source-guards (PowerOpt Math.min retiré, ratio ADEME / IPE / surplus lus BE) |
| 5 | Aucun warning Recharts | ✅ Playwright 0 dup-key (G3 source-guard CdcSim + FlexBubble keys composites) |
| 6 | 3 priorités maximum affichées | ✅ Playwright = 3 articles |
| 7 | EmptyState clair | ✅ `pilotage-tab-empty` + `pilotage-tab-data-gap` testids |
| 8 | Action candidate → Centre d'Action V4 | ✅ POST sync-action 201 sur HELIOS |
| 9 | `external_ref` stable | ✅ pattern `pilotage:{type}:site:{id}[:date]` + dédup BE + UNIQUE index DB |
| 10 | `source_url` stable | ✅ `/usages?tab=pilotage&site={id}` (cohérent avec URL deep-link) |
| 11 | Tests verts | ✅ 169 cumul (95 BE + 74 FE) |
| 12 | Audit livré | ✅ ce document |

---

## 6 — Décisions clés

1. **Dédup BE par `external_ref`** : `_build_action_candidates` agrège plusieurs insights de même type/site en 1 action_candidate (somme impact_eur, garde severity max + confidence min). Évite duplicate-key warnings côté FE + cohérent avec index UNIQUE Centre d'Action V4.
2. **`impact_eur=None` si 0** : conformément à « pas de chiffre menteur » — si la somme = 0, on retourne `null` et le FE affiche `—` au lieu de « 0 € » trompeur.
3. **`domain=optimisation`** : choix de l'enum Domain V4 le plus proche pour « pilotage des usages » (économies / optimisation énergétique). Pas de nouveau Domain ajouté (brief « pas de modèle SQL nouveau »).
4. **`kind=recommendation`** : cohérent avec la sémantique d'un insight de pilotage (suggestion d'action). `decision` est réservé aux décisions DAF, `action` aux tâches déjà actées.
5. **`useSearchParams` plutôt que `useState` seul** : permet le deep-link depuis Centre d'Action V4 (drawer LinksTab « Voir la source » → `/usages?tab=pilotage&site={id}`). Cohérent avec audit menu Énergie #313 §7.1 « 4ᵉ tab interne pas nouveau menu ».
6. **Vocabulaire client clair** : `INSIGHT_LABEL` mapping FR force le wording « Consommation hors horaires » / « Talon de nuit / week-end » / « Pic de puissance » / « Dérive de consommation » / « Lacune de données » au lieu des types techniques BE (`hors_horaires` / `base_load` / `pointe` / `derive` / `data_gap`). Brief « Français clair ».
7. **`<details>` expert** : 5 champs (périmètre, computed_at, total insights, score qualité, truth_contract_note) — pas un panel séparé pour préserver la simplicité visuelle.
8. **PowerOptCard sans fallback Math.min** : le BE garantit `utilization_pct_safe` post #317 ; sans champ → `null` → FE affiche `—`. Pattern strict « lecture pure ».

---

## 7 — Dette résiduelle

| # | Item | Statut |
|---|---|---|
| Hygiene seed HELIOS | 2 sites portent le même nom « Site Test Phase 2 » (origine warnings ScatterLabel pré-existants documentés #317) | P1 hygiene seed (non bloquant) |
| Audit menu Énergie #313 P1 | Renommer « Répartition par usage » → « Usages énergétiques » | inchangé, cosmétique |
| Audit menu Énergie #313 P1 | Fusionner `/usages-horaires` dans `/usages` | inchangé |
| Audit menu Énergie #313 P1 | Audit IS11 `/api/energy/import/jobs` sans scope | inchangé sécurité |

Aucune nouvelle dette créée. Les 7 console warnings Recharts pré-existants sur `/usages` (timeline scatter) restent dans le scope hygiene seed.

---

## Verdict

🟢 **GO MERGE** — 4ᵉ onglet « Pilotage des usages » livré dans `/usages` sans nouveau menu, sans `/usage-steering`, sans Flex visible client, sans calcul métier FE. Endpoint POST sync-action idempotent strict (HELIOS 201 → 200 sur rejeu). 3 cards above-the-fold avec EmptyState + banner data-gap + mode expert détails. Tests : 169 verts. Playwright : 0 console error, 0 network 4xx/5xx.

Le sprint suivant (P2 — renderers partagés `<Heatmap7x24/>` + `<ProfileChart/>` + fusion `/usages-horaires`) peut démarrer sur cette base saine.
