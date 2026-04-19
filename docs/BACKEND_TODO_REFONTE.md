# Backend TODO — Refonte Sol V1

> **Scope** : endpoints backend manquants détectés pendant la refonte Sol V1 (Phases 2 à 4.5). Chantier **séparé** à traiter sur `main` dans un PR dédié.
>
> **Règle** : la refonte Sol V1 ne modifie **aucun** backend. Chaque endpoint listé ici est actuellement contourné côté frontend par un fallback documenté dans les `sol_presenters.js` concernés.
>
> **Audience** : équipe backend + contributeur PR future.

---

## Tableau récapitulatif

| # | Endpoint | Priorité | Utilisé par | Fallback actuel |
|---|---|---|---|---|
| 1 | `GET /api/billing/compare-monthly?months=12` (existe, shape à enrichir) | **P0** | `BillIntelSol` KPI 1 delta vs mois précédent | `extractCurrentMonthTotals(compare)` pour derniers 2 mois, delta calculé frontend. OK. **Pas de TODO critique** — existant suffit. |
| 2 | `GET /api/cockpit/conso-month?scope` | **P0** | `CockpitSol` KPI 3 delta consommation N-1 | Pas de delta affiché (prop `consoDelta = null`). Fallback gracieux (SolKpiCard masque la pastille). |
| 3 | `GET /api/billing/recovery-ytd` | **P1** | `BillIntelSol` KPI 3 valeur exacte | `estimateRecoveredYtd(insights)` = Σ insights.insight_status='resolved'.estimated_loss_eur. Heuristique pragmatique ; endpoint dédié donnerait la valeur canonique (avoirs correctifs réels). |
| 4 | `GET /api/sites/history-n1?scope` | **P1** | `PatrimoineSol` SolBarChart previous year | Mock `current × 1.04` dans `adaptSitesToBarChart`. Visuellement OK mais pas exact. |
| 5 | `GET /api/purchase/weighted-price` | **P0** | `AchatSol` KPI 1 valeur exacte | `estimateWeightedPrice` = spot × 1.20 (heuristique markup B2B). Fait illusion mais pas précis par site. |
| 6 | `GET /api/market/history?months=12` | **P1** | `AchatSol` SolTrajectoryChart courbe marché | `synthesizeMarketTrend` interpole entre `spot_avg_12m_eur_mwh` et `spot_current_eur_mwh` avec oscillation sinusoïdale. Graphe visuellement correct mais pas historique réel. |
| 7 | `GET /api/purchase/scenarios` | **P1** | `AchatSol` KPI 3 count | Count hard-coded à 0 (`scenariosSummary.validatedCount = 0`). Interpretation affiche "Lancez l'assistant". |
| 8 | Fix `/api/cockpit` 500 runtime browser (**issue #257**) | **P2** | Tous les pages Cockpit | Fallbacks côté frontend : `cockpit.stats.compliance_score` remplacé par `trend[last].score` (59.4 vs 48.4), `conso_kwh_total` remplacé par `billing.total_kwh/1000` (1 268 MWh vs 2 757 MWh). UX non-cassée mais données proxy, pas canoniques. |
| 9 | `GET /api/monitoring/baseline?site_id=X` | **P1** | `MonitoringSol` SolTrajectoryChart userLine baseline ajustée DJU | `computeBaseline(trajectoryData)` = moyenne 12 mois simple, non ajustée DJU Météo-France. Baseline visuellement correcte mais biais saisonnier possible. |
| 10 | `GET /api/aper/projects-status` | **P1** | `AperSol` KPI 2 "sites conformes" | Count hard-coded à 0/4 (backend ne flag pas encore les projets PV validés). KPI visuellement présent mais sans progression réelle possible. |
| 11 | `GET /api/actions/weekly-history?weeks=12` | **P2** | `CommandCenterSol` SolBarChart activité Sol hebdomadaire | `buildSolWeeklyActivity` synthétise depuis counts actuels (extrapolation simple, pas d'historique réel). Graphe visuellement correct mais pas d'historique factuel. |

---

## Détails endpoint par endpoint

### 1. `GET /api/billing/compare-monthly?months=12` — **existant, shape suffit**

**Statut** : endpoint déjà exposé et consommé. Pas de TODO critique.

**Shape actuelle vérifiée** :
```json
{
  "current_year": 2026,
  "previous_year": 2025,
  "months": [
    {
      "month": 1,
      "label": "Janv",
      "current_eur": 37454.86,
      "previous_eur": null,
      "current_kwh": 141972.0,
      "previous_kwh": null,
      "delta_eur": null,
      "delta_pct": null
    }
  ]
}
```

**Amélioration possible (non-bloquante)** : remplir `previous_eur` pour les mois où l'historique N−1 est disponible → affichage des deltas inline pour 2026.

---

### 2. `GET /api/cockpit/conso-month?scope` — **P0 nouveau**

**Objectif** : exposer la consommation du mois courant + même mois année précédente pour le delta KPI Cockpit.

**Shape attendue** :
```json
{
  "current_month": "2026-04",
  "current_kwh": 230000,
  "previous_year_month": "2025-04",
  "previous_year_kwh": 215000,
  "delta_pct": 7.0,
  "sites_with_data": 5,
  "source": "metered"
}
```

**Intégration** : dans `useCockpitSolData`, ajouter `getCockpitConsoMonth().catch(() => null)` au `Promise.allSettled`. Dans `CockpitSol.jsx`, supprimer `consoDelta = null` et calculer via `computeDelta({ current: consoMonth.current_kwh, previous: consoMonth.previous_year_kwh, unit: '%' })`.

**Test** : `curl -s http://127.0.0.1:8001/api/cockpit/conso-month -H "X-Org-Id: 1"` → 200 avec shape conforme.

---

### 3. `GET /api/billing/recovery-ytd` — **P1 nouveau**

**Objectif** : remplacer l'heuristique frontend `estimateRecoveredYtd` par la source canonique (avoirs correctifs réellement reçus).

**Shape attendue** :
```json
{
  "ytd_recovered_eur": 12340.50,
  "contestations_validated": 7,
  "avg_delay_days": 45,
  "source": "contestation_tracker"
}
```

**Intégration** : dans `bill-intel/sol_presenters.js`, supprimer `estimateRecoveredYtd`, remplacer par lecture directe `billingRecovery.ytd_recovered_eur`.

---

### 4. `GET /api/sites/history-n1?scope` — **P1 nouveau**

**Objectif** : exposer la consommation année précédente pour chaque site, alimenter le `previous` de SolBarChart sur Patrimoine.

**Shape attendue** :
```json
[
  {
    "site_id": 1,
    "conso_kwh_an_n1": 650000,
    "year_n1": 2025,
    "completeness_pct": 100
  }
]
```

**Intégration** : dans `patrimoine/sol_presenters.js`, `adaptSitesToBarChart` lit `site.conso_kwh_an_n1` depuis cette API au lieu du mock `current × 1.04`.

---

### 5. `GET /api/purchase/weighted-price` — **P0 nouveau**

**Objectif** : calcul canonique du prix pondéré contracté (par volume réel des contrats actifs), plus fiable que `spot × 1.20`.

**Shape attendue** :
```json
{
  "weighted_eur_mwh": 68.5,
  "coverage_pct": 85,
  "energy_types": ["elec", "gaz"],
  "contracts_count": 9,
  "as_of": "2026-04-19"
}
```

**Intégration** : dans `achat/sol_presenters.js`, remplacer `estimateWeightedPrice` par lecture directe. Le `coverage_pct` permet d'avertir si portefeuille incomplet (< 80 % → message "Complétez vos contrats pour un prix pondéré fiable").

---

### 6. `GET /api/market/history?months=12` — **P1 nouveau**

**Objectif** : exposer l'historique spot EPEX réel 12 mois (moyenne mensuelle) pour SolTrajectoryChart AchatSol.

**Shape attendue** :
```json
{
  "months": [
    {
      "month": "2025-04",
      "spot_avg_eur_mwh": 52.3,
      "spot_min_eur_mwh": 31.5,
      "spot_max_eur_mwh": 88.7,
      "forward_y1_eur_mwh": 68.2
    }
  ],
  "source": "EPEX"
}
```

**Intégration** : dans `achat/sol_presenters.js`, remplacer `synthesizeMarketTrend` par mapping direct de `months[].spot_avg_eur_mwh`. Option : afficher aussi la courbe forward en overlay (deuxième <Line>).

---

### 7. `GET /api/purchase/scenarios` — **P1 nouveau**

**Objectif** : peupler le KPI 3 "Scénarios validés" avec données réelles + alimenter les week-cards AchatSol.

**Shape attendue** :
```json
[
  {
    "id": 42,
    "title": "Passage à contrat indexé Powernext",
    "status": "validated",
    "created_at": "2026-03-10",
    "validated_at": "2026-03-25",
    "savings_eur_year": 18200,
    "site_id": 3
  }
]
```

**Intégration** : dans `AchatSol.jsx`, remplacer `scenarios = []` par `getPurchaseScenarios({ org_id })`. Calculer `scenariosSummary.validatedCount = scenarios.filter(s => s.status === 'validated').length`, `potentialSavings = Σ(s.savings_eur_year)`. Week-cards alimentées automatiquement via `buildAchatWeekCards({ scenarios })`.

---

### 8. Fix `/api/cockpit` 500 runtime browser — **P2 (issue #257)**

**Objectif** : résoudre le 500 qui apparaît uniquement en runtime browser (pas en curl direct). Probablement un bug de résolution scope/auth dans la session authentifiée.

**Issue existante** : https://github.com/promeosenergies-svg/promeos-poc/issues/257

**Impact actuel** : masqué par fallbacks côté frontend (trend pour compliance_score, billing.total_kwh pour conso). Quand fix appliqué, supprimer les fallbacks dans `CockpitSol.jsx` (utiliser `cockpit.stats.compliance_score` et `cockpit.stats.conso_kwh_total` directement).

---

### 9. `GET /api/monitoring/baseline?site_id=X` — **P1 Lot 1**

**Objectif** : fournir la baseline mensuelle ajustée DJU Météo-France (correction saisonnière) pour la courbe conso MWh 12 mois dans MonitoringSol, en remplacement de la moyenne arithmétique brute.

**Shape attendue** :
```json
{
  "site_id": 3,
  "baseline_mwh_per_month": [142.3, 138.1, 125.6, 108.4, 98.2, 92.0, 88.7, 91.4, 102.8, 118.9, 131.2, 139.5],
  "method": "dju_adjusted",
  "dju_source": "Meteo-France",
  "reference_years": [2023, 2024]
}
```

**Intégration** : dans `monitoring/sol_presenters.js`, remplacer `computeBaseline(trajectoryData)` (moyenne 12 mois) par une lecture directe du tableau `baseline_mwh_per_month`. La prop `userLine` de `SolTrajectoryChart` devient un tableau aligné à `trajectoryData` au lieu d'un scalaire — alternative : passer via `userLineByIndex`.

**Notes** : idéalement baseline ajustée DJU pour éviter faux positifs saisonniers (dérive hiver/été masquant climato réelle). Endpoint peut accepter `scope=org_id` pour agrégat patrimoine.

---

### 10. `GET /api/aper/projects-status` — **P1 Lot 1**

**Objectif** : exposer le statut PV par site éligible APER pour débloquer le KPI 2 "sites conformes" d'AperSol (actuellement 0/4 en dur car backend ne flag pas encore les projets photovoltaïques validés).

**Shape attendue** :
```json
[
  {
    "site_id": 3,
    "pv_status": "validated",
    "capacity_kwc": 1180,
    "surface_type": "roof",
    "last_update": "2026-03-15",
    "deadline": "2028-01-01"
  }
]
```

Valeurs possibles de `pv_status` : `none` (aucun projet) · `study` (étude en cours) · `filed` (dossier déposé) · `validated` (projet validé/mise en service).

**Intégration** : dans `aper/sol_presenters.js`, nouveau helper `buildAperKpis({ sites, projectsStatus })` qui croise `sites_eligibles` avec `projectsStatus[].pv_status === 'validated'`. KPI 2 devient `${conforming}/${eligible}` avec narrative de progression (ex : "2/4 sites conformes, 2 dossiers déposés").

**Notes** : débloque la narrative de progression APER. Sans cet endpoint, un champ `pv_status` sur `sites` suffirait aussi (plus simple côté DB, moins flexible côté dossier).

---

### 11. `GET /api/actions/weekly-history?weeks=12` — **P2 Lot 1**

**Objectif** : exposer l'historique hebdomadaire réel des actions Sol (proposées/exécutées/validées) pour alimenter SolBarChart "Activité Sol 12 semaines" sur CommandCenterSol, en remplacement de la synthèse frontend extrapolée depuis les counts actuels.

**Shape attendue** :
```json
[
  {
    "week": "2026-W04",
    "proposed": 12,
    "executed": 8,
    "validated": 5
  }
]
```

**Intégration** : dans `command-center/sol_presenters.js`, remplacer `buildSolWeeklyActivity(counts)` (extrapolation) par un mapping direct des 12 semaines. SolBarChart conserve son shape stacked (proposed/executed/validated).

**Notes** : utile post-release Sol V1 backend agentique, quand l'historique weekly sera réellement tracé (actuellement seuls les counts instantanés existent). Ne bloque pas la démo Lot 1 (extrapolation est visuellement cohérente).

---

## Politique d'intégration

Quand l'un de ces endpoints est livré sur main :

1. **Swap** : remplacer le helper/fallback dans le `sol_presenters.js` concerné.
2. **Supprimer** le helper si plus jamais utilisé (dead code).
3. **Tester** que le rendu reste identique visuellement (A/B screenshot avec le helper Playwright existant).
4. **Pousser** sur `claude/refonte-visuelle-sol` dans un commit dédié `feat(refonte): swap <helper> → <endpoint>`.

Aucun backend touché dans la refonte tant que ces endpoints ne sont pas livrés — les fallbacks actuels suffisent pour la démo pilote et la validation visuelle.

---

## Mesure de l'effort

- **Backend** : ~2 jours pour les 2 endpoints P0 (cockpit/conso-month, purchase/weighted-price) + tests. Les P1 peuvent suivre en PRs séparés (recovery-ytd, sites/history-n1, market/history, purchase/scenarios, monitoring/baseline, aper/projects-status). P2 (weekly-history) différable post-release Sol V1 backend agentique.
- **Frontend refonte** : ~1 heure par endpoint pour swap helper → API + test smoke.
- **Fix issue #257** : investigation ~1 jour (probablement un fix localisé dans `resolve_org_id` ou `log_cx_event`).

**Total estimé** : 3,5 jours backend (2 P0 + 6 P1 + 1 P2) + 5,5 heures swap frontend = ~4 jours pour débloquer l'ensemble des KPIs en valeurs canoniques sur les 8 pages Pattern A.

---

## Traçabilité par phase

- **Entrées 1-8** : Phases 2 à 4.5 (refonte flagship — Cockpit, Conformité, Bill Intel, Patrimoine, Achat énergie).
- **Entrées 9-11** : Lot 1 Dashboards (CommandCenter /, APER, Monitoring).
- **Total** : 11 TODOs backend consolidés au tag `v2.1-lot1-dashboards`.

---

**Fin BACKEND_TODO_REFONTE.md**
