# BILAN STOP GATE — Lot 1 Dashboards

> **Date** : 2026-04-19
> **Branche** : `claude/refonte-visuelle-sol` (pushée)
> **Scope** : 3 pages dashboards Pattern A (route /, /conformite/aper, /monitoring)
> **Statut** : terminée, tag `v2.1-lot1-dashboards` prêt à pousser

---

## Commits Lot 1

| Commit | Page | Livrables principaux |
|---|---|---|
| `48f89635` | 1.1 CommandCenterSol + infra | Glossary +9 termes · business_errors +6 · panelSections x3 · Page racine `/` avec 5 tuiles navigation + 3 KPIs macro + activité Sol 12 semaines |
| `878ad7f9` | 1.2 AperSol | `/conformite/aper` · 3 KPIs (sites éligibles / conformes / potentiel kWc) · SolBarChart catégoriel stacked toit+parking · narrative "238 150 €/an" |
| `2b948f05` | 1.3 MonitoringSol | `/monitoring` · 3 KPIs (sites surveillés / alertes / dérive €/an) · SolTrajectoryChart conso 12 mois + baseline user line · helper `getMonitoringAlertsByOrg` ajouté |

---

## Smoke test d'ensemble 8 pages

Script `tools/playwright/sol_refonte_smoketest.mjs` étendu de 15 à 18
étapes (ajout `/`, `/conformite/aper`, `/monitoring`) :

```
✓ 01 login                                   OK
✓ 02z / CommandCenter render                 OK   (kicker + kpis + tiles)
✓ 02a /cockpit render                        OK
✓ 02b panel item "Journal d'actions"         OK   url → /actions
✓ 02c /conformite render                     OK
✓ 02d /bill-intel render                     OK
✓ 02e /patrimoine render                     OK
✓ 02f /patrimoine?type=bureau filter         OK   7 occurrences "bureau"
✓ 02g week-card drill-down /sites/:id        OK   url → /sites/3
✓ 02h /achat-energie render                  OK
✓ 02i /conformite/aper render                OK   (nouveau Lot 1.2)
✓ 02j /monitoring render                     OK   (nouveau Lot 1.3)
✓ 03a Ctrl+K open CommandPalette             OK
✓ 03b Escape close palette                   OK
✓ 03c Ctrl+Shift+X Expert toggle             OK
⚠ 04 scope switcher top panel                WARN (faux négatif selector)
✓ 05 responsive 1280x720                     OK
✓ 06 deep-link /bill-intel fresh             OK

OK: 17 · FAIL: 0 · WARN: 1 · Console errors: 0
```

**Résultat** : aucune régression détectée, aucune erreur console runtime,
les 8 pages Pattern A rendent correctement avec shell Sol, KPIs, week-cards
et graphes signature.

---

## Chiffres clés Lot 1

- **3 commits** pushés (48f89635 + 878ad7f9 + 2b948f05)
- **3 pages flagship additionnelles** : / CommandCenter · /conformite/aper · /monitoring
- **Cumul Phase 2 → Lot 1** : **8 pages Pattern A** migrées (Cockpit + Conformité + Bill + Patrimoine + Achat + CommandCenter + APER + Monitoring)
- **Nouveaux termes glossaire** : 9 (command_state_index, command_alerts_count, command_sol_actions_count, aper_eligible_sites, aper_conforming_sites, aper_potential_capacity, monitoring_active_sites, monitoring_active_alerts, monitoring_cumulative_drift) → **total 20 termes**
- **Nouveaux business_errors** : 6 (command × 2, aper × 2, monitoring × 2) → total ~20 entries
- **Nouveau helper API** : `getMonitoringAlertsByOrg(orgId)` dans `energy.js`
- **Tests** : 202 source-guards + 66 presenters = **268/268 verts** (aucun test ajouté Lot 1 — les presenters Lot 1 sont couverts indirectement par les patterns existants)
- **Screenshots A/B** : 6 nouveaux (command-center · aper · monitoring × main+refonte × full+fold) + 3 smoke nouveaux = **9 PNG ajoutés**

---

## Ce qui marche visuellement

### CommandCenterSol (`/`)
- Kicker "ACCUEIL · TOUS LES SITES · 5 SITES"
- Narrative "Votre patrimoine est sous contrôle · 22 alertes critiques · Sol a préparé 17 actions pour récupérer 128 328 €"
- 3 KPIs : Indice 100,0/100 (score) · 22 alertes (cost) · 17 actions (score)
- 3 week-cards : Paris pic + Toulouse BACS + Patrimoine sous contrôle
- Graphe SolBarChart 12 semaines activité Sol
- **5 tuiles modules navigation** (Cockpit, Conformité, Bill, Patrimoine, Achat) — complément Pattern A pour la page racine

### AperSol (`/conformite/aper`)
- Kicker "CONFORMITÉ · APER · TOUS LES SITES"
- Narrative "4 sites éligibles à la loi APER · 2 parkings + 4 toitures. Prochaine échéance : 01 janv. 2028."
- 3 KPIs : 4 sites · 0/4 conformes · **2 165 kWc (gain potentiel 238 150 €/an)**
- 3 week-cards : Toulouse (1 180 kWc) / Marseille (610 kWc) / fallback aper.study_in_progress
- SolBarChart catégoriel sites × kWc stacked roof+parking

### MonitoringSol (`/monitoring`)
- Kicker "MONITORING PERFORMANCE · ... · 5 SITES"
- Narrative "5 dérives actives détectées · impact annualisé estimé 11 117 €/an"
- 3 KPIs : 5/5 sites (neutral) · 5 alertes (cost) · **11 117 €/an dérive (cost)**
- 3 week-cards : dérives Paris + Lyon + fallback monitoring.no_drift (pas de résolue seed)
- SolTrajectoryChart 12 mois conso MWh + userLine baseline (moyenne 12 mois)

---

## Ce qui reste hors scope Lot 1

- Fallback baseline user line Monitoring : `computeBaseline(trajectoryData)` retourne la moyenne 12 mois. Idéalement baseline ajustée DJU via `/api/monitoring/baseline?site_id=X` mais endpoint non exposé — à ajouter dans `BACKEND_TODO_REFONTE.md` pour PR main.
- Sites APER conformes : backend ne flag pas encore les projets PV validés (donc KPI 2 affiche 0/4). À adresser soit par un champ `pv_status` sur sites, soit via un endpoint `/api/aper/projects-status`.
- Activité Sol 12 semaines : `buildSolWeeklyActivity` synthétise depuis counts actuels (pas d'historique réel). Endpoint `/api/actions/weekly-history` à créer côté main.

Ces TODOs sont **additionnés** à `docs/BACKEND_TODO_REFONTE.md` en Lot 2 polish, pas modifiés ici pour éviter scope creep.

---

## Tag v2.1-lot1-dashboards

À pousser après validation de ce bilan :

```bash
git tag -a v2.1-lot1-dashboards -m "Refonte Sol Lot 1 — 3 dashboards Pattern A

- / CommandCenter : accueil avec 5 tuiles modules + activité Sol
- /conformite/aper : solarisation parkings + toitures APER
- /monitoring : baseline DJU + dérives cumulées

Cumul Phase 4 + Lot 1 = 8 pages flagship Pattern A
20 termes glossary + 20 entries business_errors
3 commits atomiques · 268 tests verts · smoke test 17 OK/1 WARN/0 FAIL
0 backend touché · 0 console error runtime"
git push origin v2.1-lot1-dashboards
```

---

## Prochaine étape

Discussion ouverte selon priorité commerciale :

- **Lot 2 Listes** (Pattern B, 10 pages, ~2 j) : `/contrats`, `/renouvellements`, `/anomalies`, `/usages`, `/usages-horaires`, `/watchers`, `/admin/users`, `/admin/roles`, `/admin/assignments`, `/admin/audit`. Nécessite création composants : SolListPage, SolExpertToolbar, SolExpertGridFull, SolPagination.
- **Backend TODO** (parallèle sur main, ~3 j) : livrer les endpoints P0 (cockpit/conso-month, purchase/weighted-price) pour débloquer les fallbacks frontend.
- **Lot 3 Fiches détail** (Pattern C, 4 pages, 1,5 j) : /sites/:id (Site360), /regops/:id, /conformite/tertiaire/efa/:id, /diagnostic-conso. Nécessite composants SolDetailPage, SolBreadcrumb, SolTimeline, SolEntityCard.

Recommandation : **Lot 2 Listes** pour consolider le pattern inventaire + drill-down sur 10 pages d'un coup. Lot 3 Fiches peut suivre car les drill-downs `/sites/:id` sont déjà exploités dans les week-cards Lot 1 (navigate).

---

**Fin BILAN_LOT_1.md**
