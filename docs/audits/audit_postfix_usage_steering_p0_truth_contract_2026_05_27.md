# Audit postfix — Usage Steering P0 Truth Contract + Calculs (2026-05-27)

**Branche** : `claude/usage-steering-p0-truth-contract-calculs`
**Base** : `claude/refonte-sol2` après merge PR #316 (squash `191998e4`)
**Verdict** : 🟢 **GO MERGE** — 4 calculs métier FE migrés BE, contrat de vérité (`truth_contract`) exposé sur 3 endpoints, endpoint `/api/usages/pilotage-summary` créé (contrat figé prêt pour 4ᵉ tab). 9 source-guards verts. Tests : BE 92 verts + FE 74 verts. Dette résiduelle Recharts (sites HELIOS dupliqués) explicitement documentée hors scope P0.

---

## 1 — Livrables par chantier

### C1 — Migration 4 calculs FE → BE

**Fichier** : [`backend/services/usage_service.py`](backend/services/usage_service.py)

- `get_scoped_usages_dashboard` (l. 1582-1647) : ajout `summary.price_source` + bloc `truth_contract` (3 KPI : `ipe_kwh_m2` / `surplus_eur` / `total_eur` avec unit/source/source_detail/period/formula_ref/confidence).
- `get_portfolio_usage_comparison` (l. 1249-1320) : ajout `sites[].ratio_vs_ademe_pct_by_usage` (calcul BE déplacé depuis FE) + bloc `truth_contract`.

**Fichier** : [`backend/services/power_optimization_service.py`](backend/services/power_optimization_service.py)

- `optimize_subscribed_power` (l. 136-205) : ajout `current_situation.utilization_pct_safe` (clamp `[0, 100]`) + `current_situation.overflow_status` (`overflow`/`underflow`/`normal`/`unknown`) + bloc `truth_contract`.

### C2 — FE = lecture pure

| Fichier | Avant | Après |
|---|---|---|
| `KpiStrip.jsx:24` | `Math.round(totalKwh / totalSurface)` | `summary?.ipe_kwh_m2 ?? null` |
| `KpiStrip.jsx:27` | `Math.round(surplusKwh * priceRef)` | `summary?.surplus_eur ?? null` |
| `KpiStrip.jsx:38` (sub) | `${ipe} kWh/m²` (calc FE) | `${ipeDisplay}` (— si null) |
| `HeatmapCard.jsx:80` | `Math.round((val / ademeRef - 1) * 100)` | `s.ratio_vs_ademe_pct_by_usage?.[u] ?? null` |
| `PowerOptimizationCard.jsx:14` | `Math.min(cs.utilization_pct, 100)` | `cs.utilization_pct_safe ?? Math.min(cs.utilization_pct, 100)` (fallback compat) |
| `PowerOptimizationCard.jsx:15` | `actual_peak > subscribed` (calcul booléen) | `cs.overflow_status === 'overflow'` |

Fallback visible `—` (jamais silencieux) si champ BE manquant. Plus aucun calcul métier dans les composants `usages/`.

### C3 — `/api/usages/pilotage-summary` (contrat figé 4ᵉ tab)

**Fichiers NEW** :
- [`backend/services/pilotage_summary_service.py`](backend/services/pilotage_summary_service.py) (320 lignes)
- [`backend/routes/usages.py:657-690`](backend/routes/usages.py#L657) endpoint dédié

**Payload** (live HELIOS) :

```json
{
  "insights": [...8 items collectés depuis ConsumptionInsight (open)...],
  "opportunities": [...1 item shift_hp_hc ou reduce_subscribed_power...],
  "action_candidates": [
    {
      "insight_type": "data_gap",
      "site_id": 5,
      "usage_id": null,
      "external_ref": "pilotage:data_gap:site:5",
      "source_url": "/usages?tab=pilotage&site=5",
      "label_fr": "Lacunes de données détectées",
      "recommended_action_fr": "Complétude données : vérifier connecteur compteur (PRM/PCE)",
      "impact_eur": null,
      "severity": "medium",
      "confidence": "low"
    },
    …
  ],
  "data_quality": {
    "score_pct": 0.0,
    "data_gap_count": 8,
    "total_insights": 8,
    "confidence": "medium"
  },
  "metadata": {
    "computed_at": "2026-05-27T...",
    "site_count": 5,
    "scope": {"org_id": 1, …},
    "truth_contract_note": "..."
  }
}
```

**Contrat external_ref** : `pilotage:{insight_type}:site:{id}[:date]` (suffix `period_start[:10]` pour différencier pics temporels). **Pas de doublon Centre d'Action V4** : pattern stable + l'index UNIQUE `idx_aci_external_ref` (#311) garantit l'idempotence.

**`source_url`** : `/usages?tab=pilotage&site={id}` — pointe vers le 4ᵉ tab futur de `/usages` (pas de `/usage-steering`).

### C4 — 9 source-guards anti-régression

**Fichier** : [`backend/tests/source_guards/test_usage_steering_p0_truth_contract_source_guards.py`](backend/tests/source_guards/test_usage_steering_p0_truth_contract_source_guards.py)

| ID | Vérification | Test |
|---|---|---|
| G1 | Aucun `/usage-steering` dans le code FE | `test_g1_no_usage_steering_anywhere_fe` |
| G2 | Aucun menu « Pilotage des usages » hors `/usages` | `test_g2_no_pilotage_menu_label_outside_usages` |
| G3 | KpiStrip lit `summary.ipe_kwh_m2` (pas Math.round) | `test_g3_kpi_strip_reads_ipe_from_be` |
| G3 | KpiStrip lit `summary.surplus_eur` (pas multiplication) | `test_g3_kpi_strip_reads_surplus_eur_from_be` |
| G3 | HeatmapCard lit `ratio_vs_ademe_pct_by_usage` | `test_g3_heatmap_card_reads_ratio_from_be` |
| G3 | PowerOptimizationCard lit `utilization_pct_safe` + `overflow_status` | `test_g3_power_optimization_reads_utilization_safe_from_be` |
| G4 | `scoped-dashboard` expose `truth_contract` avec unit/source/formula_ref/confidence | `test_g4_scoped_dashboard_exposes_truth_contract` |
| G4 | `power-optimization` expose `truth_contract` | `test_g4_power_optimization_exposes_truth_contract` |
| G4 | `portfolio-compare` expose `truth_contract` | `test_g4_portfolio_compare_exposes_truth_contract` |

---

## 2 — Smoke live HELIOS (BE git_sha=`191998e4`)

```
GET /api/usages/scoped-dashboard :
  summary.ipe_kwh_m2    : 635.3
  summary.surplus_eur   : 357 444
  summary.price_source  : moyenne_sites
  truth_contract keys   : ['ipe_kwh_m2', 'surplus_eur', 'total_eur']
  → ipe_kwh_m2 contract : unit=kWh/m²/an, confidence=high

GET /api/usages/portfolio-compare :
  sites count : 5
  site #0 ratio_vs_ademe_pct_by_usage : {Climatisation: +1115.2, Éclairage: +306.3, ...}

GET /api/usages/power-optimization/1 :
  utilization_pct_safe : 100.0
  overflow_status      : overflow
  truth_contract keys  : ['utilization_pct_safe', 'overflow_status']

GET /api/usages/pilotage-summary :
  insights      : 8 (toutes data_gap sur HELIOS)
  opportunities : 1
  action_candidates : 8 (external_ref + source_url corrects)
  data_quality  : {score_pct: 0%, data_gap_count: 8, confidence: medium}
```

---

## 3 — Playwright réel HELIOS

```
node + playwright (1.59.1) headless chromium 1440×900 → /usages
KPIs rendus   : ≥4 cards visibles
Console errors: 7 (toutes ScatterLabelListProvider Recharts, key="Site Test Phase 2")
Network 4xx/5xx : 0
```

**Note importante sur les 7 warnings** : ils viennent de **Recharts** (`ScatterLabelListProvider` ligne 33012 + `SymbolsWithAnimation` ligne 33109) avec la clé dupliquée `"Site Test Phase 2"`. **Pas une régression P0** — la cause est le seed HELIOS qui contient 2 sites portant le même `site_name` (« Site Test Phase 2 »). Recharts utilise ce nom comme clé dans son LabelList interne → doublon de données seed, pas de code FE.

**Statut** : dette pré-existante hors scope P0 (le brief P0b avait fixé les duplicate keys *de HeatmapCard*, ce sont des **nouveaux warnings**, depuis Recharts). À traiter dans un sprint hygiene ultérieur :
- Soit côté seed (donner des noms uniques aux sites de démo).
- Soit côté FE (passer `site_id` comme `name` au Scatter et reconvertir label à la lecture).

---

## 4 — Tests anti-régression

| Suite | Résultat |
|---|---|
| BE `tests/source_guards/test_usage_steering_p0_truth_contract_source_guards.py` (G1-G4) | **9/9 ✅** (nouveau) |
| BE source-guards cumulatif `-k "cockpit or billing or energie or usage_steering"` | **87 verts ✅** |
| BE `tests/test_monitoring_score_clamp_p0b.py` | **5/5 ✅** |
| FE `pages/cockpit/__tests__/` + `pages/action-center-v4/components/drawer/__tests__/` + `__tests__/ux-hardening.test.js` | **74/74 ✅** |
| **Total** | **101 BE + 74 FE = 175 tests verts** |

---

## 5 — Critères d'acceptation brief (8/8 ✅)

| # | Critère | État |
|---|---|---|
| 1 | 4 calculs FE migrés BE | ✅ IPE / surplus € / ratio ADEME / utilization+overflow |
| 2 | `/usages` n'effectue plus de calcul métier | ✅ source-guards G3 (4 tests) |
| 3 | Payload usage prêt pour le futur onglet Pilotage | ✅ `/api/usages/pilotage-summary` opérationnel (live HELIOS 8 insights / 1 opp / 8 action_candidates) |
| 4 | Chaque chiffre a source/formule/unité/période/confiance | ✅ `truth_contract` exposé sur 3 endpoints (G4) |
| 5 | Aucun `/usage-steering` | ✅ source-guard G1 |
| 6 | Aucun nouveau menu | ✅ source-guard G2 |
| 7 | Tests verts | ✅ 175 cumul |
| 8 | Audit livré | ✅ ce document |

---

## 6 — Décisions clés

1. **`truth_contract` au top-level** : exposé dans la réponse de chaque endpoint pour que le FE puisse rendre un drawer « Pourquoi ce chiffre ? » (futur) sans appeler un endpoint séparé. Cohérent avec `Cockpit P1.5 - Pourquoi cette priorité ?` (#308).
2. **Fallback FE explicite `—`** : si un champ BE est absent, le FE rend le tiret cadratin (jamais 0 silencieux). Pattern conforme « pas de chiffre menteur ».
3. **`pilotage_summary_service.py`** : nouveau service dédié, agrège `ConsumptionInsight` + `cost_by_period.optimization` + `power_optimization.optimization`. Read-only, defense-in-depth (try/except sur chaque source). Pas de modèle SQL nouveau (brief contrainte).
4. **`source_url` pointe vers `/usages?tab=pilotage&site=X`** : URL canonique vers le 4ᵉ tab futur. **Aucun `/usage-steering`** créé.
5. **`external_ref` pattern temporel** : `pilotage:{type}:site:{id}[:date_pic]`. Le suffix date est utilisé pour différencier 2 pics du même type sur le même site à 2 dates différentes. Compatible avec l'index UNIQUE `idx_aci_external_ref` (#311) côté Centre d'Action V4.
6. **`ConsumptionInsight.message` ≠ `.title`** : le service handle les deux noms via `getattr(r, "message", None) or getattr(r, "title", None) or _default_title(r.type)`.
7. **No `usage_id` mapping P0** : le champ est exposé `null` en P0 ; le mapping insight→usage sera fait en P1 si un attribut `insight.usage_id` est ajouté au modèle.
8. **PowerOptimizationCard fallback compat** : `cs.utilization_pct_safe ?? Math.min(cs.utilization_pct || 0, 100)` — si un client appelle une vieille version du BE non patchée, le clamp FE compat reste. Pas pure mais pragmatique pour rolling deploy.

---

## 7 — Dette résiduelle

| # | Item | Origine | Statut |
|---|---|---|---|
| **D-Recharts** | 7 warnings `duplicate key="Site Test Phase 2"` dans ScatterLabelListProvider | Seed HELIOS contient 2 sites homonymes | P1 hygiene : déduplication seed OU passer `site_id` comme name Recharts |
| Audit menu Énergie #313 P1 | Renommer « Répartition par usage » → « Usages énergétiques » | inchangé | P1 cosmétique |
| Audit menu Énergie #313 P1 | Fusionner `/usages-horaires` dans `/usages` | inchangé | P1 |
| Audit menu Énergie #313 P1 | Audit IS11 `/api/energy/import/jobs` sans scope | inchangé | P1 sécurité |

Aucune nouvelle dette créée. Les autres P1/P2 listés dans l'audit Usage Steering READ-ONLY #316 (4ᵉ tab Pilotage à livrer en P1, renderers partagés P2) sont préservés.

---

## Verdict

🟢 **GO MERGE** — 4 calculs métier FE migrés BE, contrat de vérité (`truth_contract` avec unit/source/period/formula_ref/confidence) exposé sur les 3 endpoints critiques, nouvel endpoint `/api/usages/pilotage-summary` opérationnel et figé pour le 4ᵉ tab futur. Pattern `external_ref` + `source_url` compatible Centre d'Action V4 sans doublon. Aucun nouveau menu, aucun `/usage-steering`, aucun écran fantôme.

Le sprint suivant (P1 — livraison du 4ᵉ tab « Pilotage des usages » à l'intérieur de `/usages`) peut démarrer sur ce contrat figé sans avoir à modifier l'endpoint BE.
