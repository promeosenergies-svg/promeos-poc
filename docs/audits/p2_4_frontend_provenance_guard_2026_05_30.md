# Sprint Énergie P2.4 — Source-guard FE provenance visible (rapport)

**Date** : 2026-05-30
**Sprint** : P2.4 — Source-guard statique frontend Énergie provenance visible obligatoire
**Branche** : `claude/energie-p2-4-fe-provenance-guard` depuis `6fd30492`
**Périmètre** : backend (source-guard) + 1 correction frontend (FavorableHoursPanel)

## 1. Composants audités (15 composants `frontend/src/ui/energy/*.jsx`)

| Composant | Type | Props détectées | Provenance rendue | Statut |
|---|---|---|---|---|
| KpiCardWithProvenance.jsx | KPI card | provenance, value, label | `kpi-provenance-tooltip` + 5 axes canoniques | ✅ canonique |
| MonitoringSynthesisStrip.jsx | wrapper KPI | scope, period, compare | délègue à KpiCardWithProvenance ×10 | ✅ OK |
| LoadCurveChart.jsx | chart Recharts | series, display, granularity | provenance racine rendue par parent | ✅ whitelist (chart pur) |
| TopPeaksTable.jsx | placeholder | points (null actuellement) | API top_peaks pas encore exposé | ✅ whitelist (cible P3.x) |
| WeekProfileHeatmap.jsx | heatmap | matrix, provenance | `heatmap-provenance` | ✅ OK |
| CostVsContractCard.jsx | scénarios | scenarios, recommendation, activeContract | `scenario-provenance` (ScenarioProvenanceDot) | ✅ OK |
| PriceDecompositionTable.jsx | table prix | priceDecomposition | `price-component-provenance` | ✅ OK |
| ExposureScoreGauge.jsx | KPI gauge | score, state, provenance | `exposure-score-provenance` | ✅ OK |
| TopExpensiveHoursTable.jsx | table heures | topExpensiveHours | `top-hour-provenance` | ✅ OK |
| **FavorableHoursPanel.jsx** | **liste métier** | **favorableHours** | **❌ AVANT P2.4 : aucun marqueur** | **🔧 corrigé P2.4** |
| BaseloadComparisonCard.jsx | KPI baseload | baseloadComparison | `baseload-provenance` | ✅ OK |
| DisplacementSimulationCard.jsx | simulation | simulation | `simulation-provenance` (SimulationProvenanceDot) | ✅ OK |
| EnergyCrossLinks.jsx | navigation | links | non-KPI | ✅ whitelist |
| SiteRequiredState.jsx | EmptyState | title, text, ctaLabel | non-KPI | ✅ whitelist |
| EnergyFilterBar.jsx | filtre UI | filters | non-KPI | ✅ whitelist |

## 2. Composants couverts (12 sur 15)

**10 composants métier** avec marqueur provenance visible :
- KpiCardWithProvenance (canonique + 5 axes)
- MonitoringSynthesisStrip (délégation)
- WeekProfileHeatmap (`heatmap-provenance`)
- CostVsContractCard (`scenario-provenance` × 4 scénarios)
- PriceDecompositionTable (`price-component-provenance` par composante)
- ExposureScoreGauge (`exposure-score-provenance`)
- TopExpensiveHoursTable (`top-hour-provenance` par heure)
- BaseloadComparisonCard (`baseload-provenance`)
- DisplacementSimulationCard (`simulation-provenance`)
- FavorableHoursPanel (`favorable-hours-provenance` — **ajouté P2.4**)

**2 composants** délégant la provenance à un parent ou ayant une donnée non métier :
- LoadCurveChart (chart pur, provenance rendue par parent via KpiCardWithProvenance)
- TopPeaksTable (placeholder en attente API)

**3 composants non-métier** explicitement whitelistés :
- EnergyCrossLinks (navigation pure)
- SiteRequiredState (EmptyState métier)
- EnergyFilterBar (filtre UI)

## 3. Whitelist finale (5 entrées documentées)

`NON_METIER_WHITELIST` dans `backend/tests/source_guards/test_frontend_energy_provenance_visible_source_guard.py` :

| Fichier | Raison | Cible suppression |
|---|---|---|
| `EnergyCrossLinks.jsx` | Composant navigation pure (P1.S7 + P2.2), prop `links` non métier | Pas de dette |
| `EnergyFilterBar.jsx` | Composant filtre UI pur (P1.S3a), props filtres pilotent les requêtes API | Pas de dette |
| `SiteRequiredState.jsx` | EmptyState métier (P1.S6 fix UX), aucune donnée KPI | Pas de dette |
| `LoadCurveChart.jsx` | Chart Recharts pur (P1.S3a), provenance rendue par parent `LoadCurveTab` via KpiCardWithProvenance | Pas de dette frontend ; rendre provenance dans chart = redondance UX |
| `TopPeaksTable.jsx` | Placeholder « Top pics indisponible » (P1.S3a), API `top_peaks` pas encore exposé | Cible P3.x : extension API backend + ajout marqueur + retrait whitelist |

## 4. Corrections minimales (1 fichier)

### `frontend/src/ui/energy/FavorableHoursPanel.jsx`

**AVANT P2.4** : composant rendait les 3 groupes catégorisés (« prix bas » / « prix négatif » / « heure solaire ») avec leurs heures mais **aucun marqueur provenance** alors que chaque `EnergyFavorableHour` backend porte `provenance` (cf. P1.S6).

**P2.4 — correction minimale** (3 lignes ajoutées en pied de panel) :

```jsx
// Marqueur provenance visible (source-guard statique).
// Toutes les heures favorables partagent la même provenance backend.
const commonProvenance = favorableHours[0]?.provenance;
// ... (rendu groupes) ...
{commonProvenance?.service && (
  <p
    className="text-[9px] text-gray-400 font-mono italic"
    data-testid="favorable-hours-provenance"
    aria-label={`Provenance : ${commonProvenance.service}`}
  >
    Source : {commonProvenance.service}
  </p>
)}
```

**Impact visuel** : 1 ligne discrète en bas du panel, taille `text-[9px]`, gris clair italique, format `Source : market_exposure._compute_favorable_hours`. Conforme au brief P2.4 (« ajout invisible/inoffensif »).

**Aucun calcul métier** ajouté — lecture pure de la provenance backend depuis `favorableHours[0].provenance`.

## 5. Tests exécutés

| Suite | Résultat |
|---|---|
| `pytest tests/source_guards/test_frontend_energy_provenance_visible_source_guard.py -v` | **8/8 ✅** (nouveau) |
| `pytest tests/source_guards/ -k "frontend_no_business or energy_orchestration or market_price or cdc_timezone or frontend_energy_provenance"` | **66/66 ✅** (+8 vs P2.3) |
| `vitest src/__tests__/EnergyProvenanceCoverage.test.jsx` | **31/31 ✅** (+15 vs P1.S7 — section P2.4 ajoutée) |
| `vitest src/__tests__/` (full suite frontend) | **1951/1951 ✅** (+15 vs P2.3, 3 skipped) |
| `playwright p1_energy_final_smoke.spec.js` | **7/7 ✅** (8.3 s) — aucune régression sur 5 vues brique Énergie |

### Détails source-guard P2.4 (8 tests)

1. `test_energy_ui_directory_exists` — sanity check
2. `test_at_least_one_energy_component_present` — au moins 10 composants
3. `test_all_metier_components_render_provenance_marker` — règle principale (15 composants scannés)
4. `test_whitelist_entries_exist_on_disk` — pas d'entrée orpheline
5. `test_whitelist_entries_have_justification` — justification ≥ 50 chars
6. `test_whitelisted_components_explicitly_dont_accept_kpi_provenance` — cohérence whitelist
7. `test_canonical_kpi_card_with_provenance_renders_5_axes` — 5 axes canoniques (Source / Service / Formule / Période / Confiance)
8. `test_p2_4_corrected_favorable_hours_panel` — vérifie la correction P2.4 spécifique

## 6. Risques restants

| Risque | Sévérité | Mitigation |
|---|---|---|
| Détection prop métier basée sur regex de déstructuration — un composant peut accepter une prop sans utiliser le pattern reconnu | Faible | Whitelist explicite documentée + tests vitest complémentaires sur composants nommés |
| Faux négatif sur composant qui rend `data-testid` provenance dans un sous-composant non détecté par regex | Faible | Whitelist `LoadCurveChart` documente ce cas (provenance déléguée au parent) |
| Évolution future : nouveau composant Énergie créé sans provenance visible | Géré | Le guard scanne automatiquement tous les `*.jsx` de `ui/energy/` ; doit être à jour pour tout nouveau composant (CI feedback immédiat) |
| Whitelist `TopPeaksTable` dette résiduelle | Moyenne | Cible P3.x : extension API `/api/energy/loadcurve.top_peaks` puis ajout marqueur provenance + retrait whitelist |

## 7. Recommandation P2.5

**P2.5 — Audit bundle size brique Énergie** :
- 12 composants UI Énergie + 5 Tabs lazy-loaded
- Cible : ≤ 250 kB gzipped par route
- Mesurer : `frontend/src/pages/{MonitoringPage, consumption/LoadCurveTab, consumption/CostContractTab, consumption/MarketExposureTab, usages/WeekProfileTab}.jsx` après lazy load
- Outils suggérés : `vite-bundle-visualizer` + `source-map-explorer`
- Si dépassement : split + dynamic import des composants UI lourds (Recharts, Lucide-react)

**Prérequis P2.5 validés** :
- ✅ HELPER_WHITELIST FE à 2 entrées (P2.1)
- ✅ Cross-links transverses 5/5 vues (P2.2)
- ✅ MarketPrice legacy durcie (P2.3)
- ✅ Source-guard FE provenance visible (P2.4)

**Aucun blocant identifié** pour démarrer P2.5.

---

Rapport généré le 2026-05-30 dans le cadre du sprint P2.4.
