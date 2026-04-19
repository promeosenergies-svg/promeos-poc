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

## Politique d'intégration

Quand l'un de ces endpoints est livré sur main :

1. **Swap** : remplacer le helper/fallback dans le `sol_presenters.js` concerné.
2. **Supprimer** le helper si plus jamais utilisé (dead code).
3. **Tester** que le rendu reste identique visuellement (A/B screenshot avec le helper Playwright existant).
4. **Pousser** sur `claude/refonte-visuelle-sol` dans un commit dédié `feat(refonte): swap <helper> → <endpoint>`.

Aucun backend touché dans la refonte tant que ces endpoints ne sont pas livrés — les fallbacks actuels suffisent pour la démo pilote et la validation visuelle.

---

## Mesure de l'effort

- **Backend** : ~2 jours pour les 4 endpoints P0 (cockpit/conso-month, purchase/weighted-price) + tests. Les P1 peuvent suivre en PRs séparés.
- **Frontend refonte** : ~1 heure par endpoint pour swap helper → API + test smoke.
- **Fix issue #257** : investigation ~1 jour (probablement un fix localisé dans `resolve_org_id` ou `log_cx_event`).

**Total estimé** : 3 jours backend + 4 heures swap frontend = 3,5 jours pour débloquer les KPIs en valeurs canoniques.

---

**Fin BACKEND_TODO_REFONTE.md**
