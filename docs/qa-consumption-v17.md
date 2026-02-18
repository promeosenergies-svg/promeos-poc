# QA Checklist — Sprint V17 (Consumption Explorer World-Class)

## V17-A: Sélection de site fiable

- [ ] Page Explorer sans sites → EmptyState "Aucun site sélectionné" + bouton "Tout sélectionner" visible
- [ ] Clic "Tout sélectionner" → siteIds = tous les sites de l'org, courbes visibles
- [ ] Changer d'org (Casino → Tertiaire) via le header : picker se réinitialise aux sites Tertiaire (plus de sites Casino)
- [ ] Refresh F5 : sites dans URL correspondent à l'org courante (pas stale)
- [ ] N ≤ 5 sites dans l'org → auto-sélection de tous les sites au chargement
- [ ] N > 5 sites → auto-sélection du premier site uniquement
- [ ] selectedSiteId (scope) = "Bureau Paris #01" → site pré-sélectionné à l'ouverture de l'Explorer

## V17-B: Cohérence des IDs (normalizeId)

- [ ] scope.siteId numérique vs string (localStorage) : picker affiche le bon site sélectionné dans scopedSites
- [ ] Filtre Diagnostic avec selectedSiteId → seuls les insights du site s'affichent (normalizeId dans filteredInsights)
- [ ] URL `sites=1,2` → siteIds = [1, 2] (nombres, non strings)

## V17-C: Courbes — garantie de rendu

- [ ] 1 site avec data EMS → courbe visible (dates sur X, kWh sur Y)
- [ ] 2-3 sites, mode Superpose → 2-3 lignes colorées
- [ ] 2-3 sites, mode Empile → areas empilées
- [ ] 2-3 sites, mode Sépare → sous-graphiques individuels
- [ ] Site sans compteur → "Aucun compteur configuré" + CTA Connecter
- [ ] Site avec compteur, période sans données → "Pas de données" + CTA Étendre
- [ ] Erreur API → "Erreur de chargement" + bouton Réessayer
- [ ] ?debug=1 → panel terminal vert visible avec siteIds, orgId, scopeLabel, n_points

## V17-D: Régression

- [ ] `npx vitest run` → ≥ 745 tests verts, 0 rouge
- [ ] `npm run build` → clean, 0 erreur TypeScript/PropTypes
- [ ] Navigation Explorer → Diagnostic → Monitoring → Explorer : scope cohérent partout
- [ ] Seed Tertiaire S=10 → "SCI Les Terrasses · 10 sites" dans le topbar + picker
- [ ] Seed Casino S=36 → "Groupe Casino · 36 sites" dans le topbar + picker
- [ ] Rechargement F5 : scope conservé (localStorage), sites sélectionnés conservés si dans l'org
