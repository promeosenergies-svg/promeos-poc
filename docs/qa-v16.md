# QA Checklist — Sprint V16 (Consommations World-Class)

## V16-A: Garantie anti-blank

### Explorer — 1 site avec données
- [ ] Aller sur `/consommations/explorer`
- [ ] Sélectionner un site avec des relevés EMS dans la barre de filtres
- [ ] **Attendu**: Courbe visible dans la zone chart (dates sur l'axe X, valeurs kWh)
- [ ] **Attendu**: Badge "N points · N compteurs · Granularité: Journalière · Source: EMS" au-dessus du chart

### Explorer — 1 site sans données
- [ ] Sélectionner un site sans relevés EMS
- [ ] **Attendu**: `EmptyByReason` visible dans une Card blanche (jamais une zone blanche)
- [ ] **Attendu**: Message clair + CTA contextuel (ex: "Importer des données")

### Explorer — aucun site sélectionné
- [ ] Vider le sélecteur de site
- [ ] **Attendu**: Message "Aucun site sélectionné" dans la Card (pas de zone blanche)

### Explorer — erreur API
- [ ] Couper le backend ou simuler une erreur (via ?debug=1 pour vérifier)
- [ ] **Attendu**: `ErrorState` visible avec message d'erreur lisible + bouton "Réessayer"

### Explorer — multi-sites (superpose/empile/sépare)
- [ ] Sélectionner 2–3 sites, mode Superpose
- [ ] **Attendu**: Courbes colorées par site, pas de zone blanche
- [ ] Empile: areas empilées
- [ ] Sépare: sous-graphiques individuels

---

## V16-B: EmptyByReason enrichi

- [ ] Site sans compteur: message "Aucun compteur configuré" + CTA "Connecter"
- [ ] Site avec compteur mais sans relevés: message "Peu de relevés importés" + CTA "Importer"
- [ ] API retourne `first_ts`/`last_ts`: dates affichées + CTA "Étendre à 12 mois"
- [ ] Clic "Étendre à 12 mois" → period passe à 365 jours

---

## V16-C: ChartFrame height guarantee

- [ ] En mode Classic: zone chart occupe toujours ≥ 360px de hauteur
- [ ] En mode Expert tab Consommation: même garantie
- [ ] En cas de loading: SkeletonCard visible dans la Card (pas de hauteur 0)

---

## V16-C: Debug panel (?debug=1)

- [ ] Aller sur `/consommations/explorer?debug=1`
- [ ] **Attendu**: Panel terminal vert visible en haut de la zone chart
- [ ] Section "Scope global": orgId, selectedSiteId, scopeLabel, sitesCount
- [ ] Section "Paramètres requête": siteIds, energyType, days, unit, mode
- [ ] Section "État série temporelle (EMS)": status, n_points, granularity
- [ ] Section "API debug": endpoint, responseMs, seriesCount, pointsCount, yMin, yMax
- [ ] "Copier diagnostic" → JSON copié dans le presse-papiers (inclut scope)
- [ ] Panel visible même en état EMPTY et ERROR

---

## V16-D: Cohérence périmètre (Diagnostic)

- [ ] Sélectionner "Bureau Paris #01" dans le header global
- [ ] Aller sur Diagnostic (`/consommations/analyse`)
- [ ] **Attendu**: Badge "Périmètre : Site : Bureau Paris #01 — Vue filtrée"
- [ ] **Attendu**: Insights affichés uniquement pour Bureau Paris #01
- [ ] **Attendu**: Bannière amber si le diagnostic couvre plusieurs sites mais vue filtrée
- [ ] Clic "Afficher tout le portefeuille" → sélection site réinitialisée

### Cohérence après changement de scope

- [ ] Changer d'org (ex: Casino → Tertiaire) via le header
- [ ] Naviguer sur Explorer → sites de Tertiaire dans le sélecteur
- [ ] Naviguer sur Diagnostic → insights de Tertiaire uniquement
- [ ] Naviguer sur Monitoring → site de Tertiaire dans le sélecteur
- [ ] **Attendu**: Aucune donnée de Casino ne s'affiche après changement

---

## V16-D: Cohérence périmètre (Explorer + Monitoring)

- [ ] Sélectionner un site spécifique
- [ ] Explorer: courbe du site sélectionné uniquement
- [ ] Monitoring: KPIs et alertes du site sélectionné uniquement
- [ ] Mode portfolio: tous les sites de l'org, agrégé

---

## Régression générale

- [ ] `npx vitest run` → ≥ 718 tests verts, 0 rouge
- [ ] `npm run build` → build propre, 0 erreur TypeScript/PropTypes
- [ ] Navigation complète sans erreur console critique
- [ ] Après seed Tertiaire S=10: "SCI Les Terrasses · 10 sites" partout
- [ ] Après seed Casino S=36: "Groupe Casino · 36 sites" partout
- [ ] Rechargement de page (F5): scope conservé (localStorage), courbe rechargée

---

## Matrice tests automatiques

| Test | Fichier | Couvre |
|------|---------|--------|
| normalizeId (6 tests) | V16BlankChart.test.js | V16-D type safety |
| filteredInsights (4 tests) | V16BlankChart.test.js | V16-D scope filter |
| computeSummaryFromInsights (3 tests) | V16BlankChart.test.js | V15-B + V16-D |
| MODE_MAP completeness (5 tests) | V16BlankChart.test.js | V16-A EMS modes |
| formatDate FR (4 tests) | V16BlankChart.test.js | V16-A date labels |
| TimeseriesPanel state machine (8 tests) | V16BlankChart.test.js | V16-A blank fix |
| hasMismatch logic (4 tests) | V16BlankChart.test.js | V16-D mismatch |
