# QA Checklist — Sprint V22 "Consommations Expert : Analyse & Insights"

**Date:** 2026-02-18
**Stop Conditions:** All items must pass before sprint close.

---

## Phase 0 — Audit recap

| Item | Status | Note |
|------|--------|------|
| Signature + Météo tabs wired | ✅ Déjà câblé | TAB_CONFIG lignes 62-63, panels lignes 1371-1375 |
| InsightsPanel (nouveau) | ✅ V22-A | `consumption/InsightsPanel.jsx` + 'insights' dans TAB_CONFIG |
| normalizeId | ✅ Clean | `helpers.js:15`, re-export `ConsumptionDiagPage.jsx:76` |
| Backend `_meta()` enrichi | ✅ V22-B | `sampling_minutes`, `available_granularities`, `valid_count` |
| Granularité data-driven | ✅ V22-B | `getAvailableGranularities(days, samplingMinutes)` intersection |

---

## Stop Condition 1 — Électricité

- [ ] `/consommations/explorer` → sélectionner un site → courbe visible
- [ ] `?debug=1` → `validCount > 50`
- [ ] Granularité "Auto" sélectionnée par défaut
- [ ] Aucune spinner infini (status ≠ loading après 10s)

---

## Stop Condition 2 — Gaz

- [ ] Basculer l'énergie sur "Gaz" → si pas de données : onglet Gaz visible
- [ ] Dans l'onglet Gaz (Expert mode) : CTA "Générer conso démo Gaz" visible quand no data
- [ ] Cliquer le CTA → spinner → rechargement automatique → courbe > 50 pts
- [ ] `?debug=1` → `energy_vector=gas`, `validCount > 50`, `granularity=daily`
- [ ] Profil saisonnier visible (hiver = pic, été = creux)

---

## Stop Condition 3 — Onglets Explorer

### Onglet Consommation
- [ ] Courbe visible en mode Expert (même comportement qu'en mode Classic)
- [ ] Granularité selon pills sélectionnées

### Onglet Insights (NOUVEAU — V22-A)
- [ ] Onglet "Insights" visible dans la tab bar Expert
- [ ] Icône Lightbulb (ampoule) visible
- [ ] 6 KPI-cards affichées : Total consommé, Moyenne/jour, Pic P95, Talon P05, Facteur de charge, Anomalies
- [ ] Barre de charge visible en bas
- [ ] Si anomalies > 0 : badge orange "N anomalies détectées" en haut à droite
- [ ] État vide si pas de données : "Données insuffisantes pour l'analyse"
- [ ] Skeleton pendant le chargement

### Onglet Signature
- [ ] Heatmap 7 rangées (Lun–Dim) × 24 colonnes (0h–23h) visible
- [ ] Gradient de couleur (bleu→rouge ou autre)
- [ ] État vide si données < 48 pts : "Données insuffisantes pour la signature"

### Onglet Météo
- [ ] Graphe double axe Y : consommation (Area) + température synthétique (Line tiretée)
- [ ] Badge DJU avec valeur numérique > 0
- [ ] Badge corrélation entre -1 et 1

---

## Stop Condition 4 — Granularité data-driven (V22-B)

- [ ] Après chargement d'un site avec données horaires (sampling_minutes=60) :
  - pills "Auto", "1 h", "1 j", "Mois" visibles
  - pill "30 min" **absente** (non disponible, fréquence réelle = 60 min)
- [ ] Après chargement d'un site avec données journalières (sampling_minutes=1440) :
  - pills "Auto", "1 j", "Mois" visibles
  - pills "30 min" et "1 h" **absentes**
- [ ] Si samplingMinutes non disponible (null) : filtrage période-only (backward compat)
- [ ] Sélectionner "1 j" → chart re-fetch avec granularity=daily

---

## Stop Condition 5 — Aucune régression

- [ ] `npx vitest run` → ≥ 854 tests verts (+ ~18 V22 nouveaux = ≥ 872 attendus)
- [ ] `npm run build` → clean, 0 erreur TS / lint
- [ ] Classic mode : pas de régression sur les fonctionnalités existantes
- [ ] Diagnostic page : scope filtre correctement (normalizeId OK)

---

## Tests purs (V22-C)

Fichier : `src/pages/__tests__/V22ConsommationsExpert.test.js`

| describe | # tests | covers |
|----------|---------|--------|
| extractValues | 4 | null/NaN filter, multi-series |
| percentile | 5 | P0/P50/P100/empty/P95 |
| computeInsightKpis | 5 | empty, uniform, varied, spike anomaly, no anomaly |
| getAvailableGranularities samplingMinutes | 5 | backward compat, daily data, hourly data, 30min data, auto always |

**Total : 19 nouveaux tests**

---

## Debug Checklist

Pour vérifier les métadonnées V22-B dans le debug panel (`?debug=1`) :

```
meta.sampling_minutes  → 60 pour données horaires, 1440 pour journalières
meta.available_granularities  → liste des granularités disponibles
meta.valid_count  → nombre de points non-null
```

---

## Notes de déploiement

- Backend : `backend/services/ems/timeseries_service.py` — `_meta()` étendu (non-breaking : champs optionnels)
- Backend : `backend/routes/ems.py` — `TimeseriesMeta` Pydantic (champs `Optional`)
- Frontend : `consumption/InsightsPanel.jsx` — NOUVEAU
- Frontend : `ConsumptionExplorerPage.jsx` — ajout import + TAB_CONFIG + panel routing
- Frontend : `consumption/helpers.js` — `getAvailableGranularities(days, samplingMinutes)`
- Frontend : `consumption/StickyFilterBar.jsx` — prop `samplingMinutes`
- Frontend : `consumption/TimeseriesPanel.jsx` — prop `onMeta` + `useEffect`
