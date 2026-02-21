# QA Checklist — Sprint V20 Consommations World-Class

## PHASE 0 : Debug mode
- [ ] Ouvrir `/consommations/explorer?debug=1` avec un site sélectionné
- [ ] Le debug panel affiche : `validCount > 0`, `zerosCount`, `nullsCount`, `effectiveValueKey = 'value'`
- [ ] `pointsCount = validCount` (mode agrégé : tous les points ont un `value`)
- [ ] `overlayValueKeys` = `(none — single series)` en mode agrégé

## PHASE 1 : La courbe doit s'afficher

- [ ] Sélectionner un site avec 90 jours de période
- [ ] Le chart Recharts rend avec des dates sur l'axe X et des kWh sur l'axe Y
- [ ] Le badge "N compteurs / M points / Source EMS" s'affiche au-dessus du chart
- [ ] Le message "0 points valides (min 2)" **n'apparaît JAMAIS** quand les données existent

## PHASE 2 : Les valeurs zéro sont valides

- [ ] Modifier un relevé à `value_kwh = 0` → la courbe montre un segment plat, **pas de trou**
- [ ] `validCount` dans le debug panel inclut les points à valeur 0

## PHASE 3 : Génération de démo

- [ ] Aucune donnée pour un site → bouton "Générer conso démo" apparaît (state empty)
- [ ] Même bouton dans l'état "Données insuffisantes" (< 2 points valides)
- [ ] Clic sur le bouton → POST `/api/ems/demo/generate_timeseries?site_id=X&days=90`
- [ ] Après génération, la courbe apparaît sans rechargement de page
- [ ] Le debug panel affiche `meter_id` commençant par "PRM-DEMO-"

## PHASE 4 : Régression

- [ ] `npx vitest run` → ≥ 803 tests verts (789 + 14 V20)
- [ ] `npm run build` → clean, 0 erreur
- [ ] Navigation Explorer → Diagnostic → Monitoring → Explorer : scope cohérent partout
- [ ] Changer d'énergie Électricité → Gaz → Électricité : reste sur l'onglet Timeseries
- [ ] URL avec `?days=30&unit=eur` → API reçoit `metric=kwh` (pas `metric=eur`)

## Checks rapides V19 (non-régression)

- [ ] Onglet par défaut = "Consommation" (Timeseries), pas "Tunnel"
- [ ] Chips de site toujours visibles même avec 0 ou 1 site
- [ ] Placeholder "Chargement…" pendant le chargement des sites
- [ ] Swagger `/api/ems/timeseries` → 200 retourne un schéma typé (pas `{}`)
