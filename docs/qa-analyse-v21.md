# QA Checklist — Sprint V21 "Analyse World-Class"

## Phase 0: Audit technique

- [ ] `/consommations/explorer?debug=1` avec un site électricité → `validCount > 50`
- [ ] Granularité auto → badge montre la granularité effective (daily / hourly / etc.)
- [ ] `normalizeId` export visible dans ConsumptionDiagPage (pas de crash à l'import)

---

## Phase 1: Courbes électricité (stop-condition)

- [ ] Sélectionner un site → onglet "Consommation" → courbe visible avec dates sur l'axe X
- [ ] `?debug=1` → `validCount > 50`, `energy_vector: electricity`
- [ ] Mode agrégé + superposé → pas d'écran blanc

---

## Phase 2: Courbes gaz (stop-condition)

- [ ] Sélectionner "Gaz" dans le sélecteur d'énergie
- [ ] Onglet "Consommation" avec energy=gaz → si vide → bouton "Générer conso démo Gaz" visible
- [ ] Cliquer → spinner bref → courbe gaz apparaît avec pattern saisonnier
- [ ] `?debug=1` → `validCount > 50`, `energy_vector: gas`
- [ ] Onglet "Gaz" (GasPanel) → si vide → bouton "Générer conso démo Gaz" visible

---

## Phase 3: Signature (stop-condition)

- [ ] Onglet "Signature" accessible dans la barre d'onglets Expert
- [ ] Avec site ayant 90 jours de données électricité horaires → heatmap 7×24 visible
- [ ] Gradient de couleur visible (HP rouge / HC bleu, intensité = kWh moyen)
- [ ] Survol d'une cellule → tooltip avec jour + heure + kWh + HP/HC
- [ ] Sans données suffisantes (<48 points) → message "Données insuffisantes pour la signature"

---

## Phase 4: Météo (stop-condition)

- [ ] Onglet "Météo" accessible dans la barre d'onglets Expert
- [ ] Graphique ComposedChart : courbe de conso (violet, area) + courbe température (bleu, pointillé)
- [ ] Badge DJU affiche une valeur numérique > 0 (été : DJU faible, hiver : DJU élevé)
- [ ] Badge Corrélation affiche R entre -1 et 1 avec label (Forte/Modérée/Faible)
- [ ] Tooltip personnalisé au survol
- [ ] Sans données → message "Données de consommation manquantes"

---

## Phase 5: Granularité (stop-condition)

- [ ] Barre de filtres → pills "Auto / 30 min / 1 h / 1 j / Mois" visibles
- [ ] Période 90 jours → "30 min" absent, "1 j" et "Mois" disponibles
- [ ] Période 7 jours → "30 min" et "1 h" disponibles, "Mois" absent
- [ ] Sélectionner "1 h" → axe X du graphique passe aux heures (jan. 01 10:00 etc.)
- [ ] Sélectionner "Auto" → granularité revient à l'auto-suggestion
- [ ] Granularité pill active est visuellement distincte (fond blanc + ombre)

---

## Phase 6: Diagnostic scope (stop-condition)

- [ ] Page Diagnostic → sélectionner "Bureau Paris #01" dans la sidebar
- [ ] Seuls les insights de ce site s'affichent (badge "Vue filtrée" visible)
- [ ] Bannière ambrée si insights multi-sites dans la réponse API
- [ ] Pas de crash sur normalizeId
- [ ] Aucune erreur console sur l'import de normalizeId depuis ConsumptionDiagPage

---

## Phase 7: Régression

- [ ] `npx vitest run` → ≥ 836 tests verts (822 + 14), 0 rouge
- [ ] `npm run build` → 0 erreur, 0 warning
- [ ] Navigation Explorer → Diagnostic → Monitoring → Explorer : scope cohérent
- [ ] Tous les onglets existants (Tunnel, Objectifs, HP/HC) fonctionnent inchangés

---

## Fichiers modifiés (V21)

| Fichier | Sprint |
|---------|--------|
| `backend/services/consumption_diagnostic.py` | V21-B: `generate_demo_gas_consumption()` |
| `backend/routes/ems.py` | V21-B: paramètre `energy_vector` dans `/demo/generate_timeseries` |
| `frontend/src/pages/consumption/helpers.js` | V21-C: `getAvailableGranularities()` |
| `frontend/src/pages/consumption/useEmsTimeseries.js` | V21-C: `granularityOverride` prop |
| `frontend/src/pages/consumption/StickyFilterBar.jsx` | V21-C: pills granularité |
| `frontend/src/pages/ConsumptionExplorerPage.jsx` | V21-C/D/E/F: état + onglets + CTA |
| `frontend/src/pages/consumption/SignaturePanel.jsx` | V21-D: NOUVEAU |
| `frontend/src/pages/consumption/MeteoPanel.jsx` | V21-E: NOUVEAU |
| `frontend/src/pages/__tests__/V21AnalyseWorldClass.test.js` | V21-G: NOUVEAU (14 tests) |
| `docs/qa-analyse-v21.md` | Ce fichier |
