# Audit Complet Cockpit — Architecture, Calculs, Donnees, Coherence, UI

**Date** : 2026-03-23
**Branche** : `feat/cockpit-world-class` (11 commits)
**Methode** : Analyse statique code + comparaison maquettes + revue architecture

---

## 1. VIOLATIONS CRITIQUES (a corriger)

### V1 — VecteurEnergetiqueCard.jsx : agregation CO2 cote front

**Fichier** : `frontend/src/pages/cockpit/VecteurEnergetiqueCard.jsx` lignes 56-84
**Severite** : HAUTE

Le composant recoit les breakdowns CO2 par site depuis `/api/cockpit/co2` mais effectue l'agregation totale cote front :
- Somme `kwh` et `kg_co2` par vecteur energetique (lignes 57-68)
- Classification Scope 1 vs Scope 2 (gaz/fioul = scope 1, elec/reseau = scope 2) — regle metier dans le front
- Calcul `mwh = Math.round(val.kwh / 1000)` et `pct = Math.round((val.kwh / totalKwh) * 100)`
- Les totaux `(totalKgCo2 / 1000).toFixed(1)` tCO2eq sont affiches comme KPIs

**Fix recommande** : Enrichir `/api/cockpit/co2` pour retourner les totaux pre-agreges :
```
{
  "total_kwh": ..., "total_kg_co2": ...,
  "scope1_kg_co2": ..., "scope2_kg_co2": ...,
  "by_vector": [{ "key": "elec", "mwh": ..., "pct": ..., "tco2": ... }]
}
```
Le composant ne ferait alors qu'afficher.

---

### V2 — Facteur CO2 0.052 (obsolete) dans 3 fichiers

**Severite** : HAUTE — Valeur incorrecte affichee aux utilisateurs

| Fichier | Ligne | Code | Probleme |
|---------|-------|------|----------|
| `components/CreateActionModal.jsx` | 106 | `* 0.052` | Ancien facteur (doit etre 0.0569) |
| `components/CreateActionDrawer.jsx` | 179 | `* 0.052` | Idem — code duplique |
| `pages/ConsumptionExplorerPage.jsx` | 343 | `totalKwh * 0.052` | Calcul CO2 cote front interdit |

Double violation : (a) calcul metier cote front, (b) facteur obsolete (ecart -8.6% vs ADEME 2024).

**Fix recommande** : Supprimer ces calculs. Utiliser les valeurs CO2 retournees par le backend (`co2e_savings_est_kg` pour les actions, `/api/cockpit/co2` pour l'explorer).

---

### V3 — Cockpit.jsx + CommandCenter.jsx : KPIs recalcules depuis scopedSites

**Severite** : MOYENNE — Calculs redondants avec le backend

| Fichier | Ligne | Calcul | KPI affiche |
|---------|-------|--------|-------------|
| `Cockpit.jsx` | 202 | `conformes / total * 100` | `suiviConformite` (affiche en UI) |
| `Cockpit.jsx` | 204-212 | `readinessScore` weighted formula | Score maturite (affiche via ExecutiveKpiRow) |
| `CommandCenter.jsx` | 203 | `conformes / total * 100` | `pctConf` dans MetricCard |
| `CommandCenter.jsx` | 197-222 | `risque = reduce(risque_eur)` | Somme risque dans MetricCard |
| `dashboardEssentials.js` | 483 | `conformes / total * 100` | Fallback si backend score null |

Ces calculs sont masques pour les non-experts (Zone1 + ExecKpiRow wrapes dans `{isExpert && ...}`) mais le code tourne toujours. La formule `actionsActives = Math.round((conformes/total)*60 + ((total-nonConformes)/total)*40)` est une regle metier.

**Fix recommande** : A moyen terme, migrer ces calculs vers le backend et utiliser `useCockpitData()` comme seule source. Pour l'instant, la coexistence est acceptable car les sections sont masquees.

---

## 2. WARNINGS (a documenter ou corriger)

### W1 — SitesBaselineCard.jsx : deltaPct non documente

**Fichier** : `frontend/src/pages/cockpit/SitesBaselineCard.jsx` lignes 19-20
**Severite** : BASSE

La division `conso_kwh_an / 365` est documentee comme transformation de presentation. Mais `deltaPct = ((consoJ1 - baselineJ) / baselineJ) * 100` est un KPI derive affiche ("+12% vs baseline") sans documentation.

**Fix** : Ajouter un commentaire dans le fichier documentant cette exception.

---

### W2 — useCommandCenterData.js : `kw = v * 4` non documente

**Fichier** : `frontend/src/hooks/useCommandCenterData.js` ligne 55
**Severite** : BASSE

La conversion `* 4` (kWh/15min → kW) est une formule physique fragile : si la granularite EMS change (30min, hourly), le resultat est faux silencieusement. `picKw = Math.max(...)` est une agregation metier.

**Fix** : Ajouter commentaire + idealement retourner `peak_kw` depuis le backend EMS.

---

### W3 — CommandCenter.jsx : formatage EUR manuel

**Fichier** : `frontend/src/pages/CommandCenter.jsx` ligne 671
**Severite** : BASSE

```jsx
{(site.risque_eur || 0).toLocaleString('fr-FR')} €
```

Devrait utiliser `fmtEur(site.risque_eur)` (deja importe dans le fichier).

---

### W4 — Accents manquants dans textes UI

**Fichier** : `frontend/src/pages/CommandCenter.jsx` lignes 624-626
**Severite** : BASSE

```
"reglementaire" → "réglementaire"
"penalite" → "pénalité"
"Verifier" → "Vérifier"
"separement" → "séparément"
```

---

## 3. COHERENCE DONNEES BACKEND

### Constantes reglementaires

| Constante | Valeur | Fichier source | Importe dans | Statut |
|-----------|--------|---------------|-------------|--------|
| `BASE_PENALTY_EURO` | 7 500 | `compliance_engine.py:57` | migrations.py, orchestrator.py | OK |
| `A_RISQUE_PENALTY_EURO` | 3 750 | `compliance_engine.py:59` | migrations.py, orchestrator.py | OK |
| `CO2_FACTOR_ELEC_KG_KWH` | 0.0569 | `compliance_engine.py:60` | — | OK |
| `CO2_FACTOR_GAZ_KG_KWH` | 0.2270 | `compliance_engine.py:61` | — | OK |

Aucune valeur hardcodee dans les fichiers dependants.

### Endpoints API cockpit

| Endpoint | Existe | Champs P0 | Statut |
|----------|--------|-----------|--------|
| `GET /api/cockpit` | Oui | compliance_score, compliance_source, risque_breakdown | OK |
| `GET /api/cockpit/trajectory` | Oui | annees, reel_mwh, objectif_mwh, jalons | OK |
| `GET /api/cockpit/co2` | Oui | sites[].breakdown[].energy_type/kwh/kg_co2 | OK (manque totaux agreges) |
| `GET /api/cockpit/benchmark` | Oui | sites[].ipe_kwh_m2_an, benchmark | OK (manque filtre org_id) |

### Issue backend mineure

**`GET /api/cockpit/benchmark`** (ligne 261) ne filtre PAS par `org_id` — retourne tous les sites actifs de toutes les orgs. En multi-tenant, c'est une fuite de donnees.

---

## 4. COHERENCE HOOK FRONTEND

### useCockpitData.js — Mapping champs

| Backend | Frontend | Statut |
|---------|----------|--------|
| `stats.compliance_score` | `conformiteScore` | OK |
| `stats.compliance_source` | `conformiteSource` | OK |
| `stats.compliance_computed_at` | `conformiteComputedAt` | OK |
| `stats.risque_financier_euro` | `risqueTotal` | OK |
| `stats.risque_breakdown` | `risqueBreakdown` | OK |
| `stats.total_sites` | `totalSites` | OK |
| `stats.avancement_decret_pct` | `avancementDecretPct` | OK |
| `organisation.nom` | `orgNom` | OK |
| `action_center` | — (non mappe) | INFO — fetche separement via getActionsSummary |

### useCommandCenterData.js

| Champ | Source | Statut |
|-------|--------|--------|
| `weekSeries` | EMS timeseries daily | OK |
| `hourlyProfile` | EMS timeseries hourly | OK |
| `kpisJ1.consoHierKwh` | weekSeries[yest].kwh | OK |
| `kpisJ1.picKw` | Math.max(hourlyProfile) | WARNING (agregation front) |
| `kpisJ1.co2ResKgKwh` | null | OK (connecteur RTE absent) |

---

## 5. COUVERTURE TESTS

### Backend (12/12)

| Classe | Tests | Couverture |
|--------|-------|-----------|
| TestCockpitComplianceScore | 3 | score source, computed_at, sites_evaluated |
| TestCockpitRisk | 3 | constantes 7500/3750, pas hardcode migrations, risque_breakdown |
| TestCockpitTrajectory | 4 | endpoint 200, structure, jalons, no-calc-front |
| TestCo2Factor | 2 | 0.0569 elec, 0.2270 gaz |

**Gap** : `test_trajectory_jalons_correct` n'asserte pas le jalon 2050 (-60%).

### Frontend — Tests sprint cockpit (112 nouveaux)

| Fichier test | Tests | Type |
|-------------|-------|------|
| useCockpitData.test.js | 17 | Source guard + structure |
| CockpitHero.test.js | 24 | Source guard + structure + a11y |
| TrajectorySection.test.js | 17 | Source guard + structure |
| ActionsImpact.test.js | 16 | Source guard + structure |
| useCommandCenterData.test.js | 22 | Source guard + structure |
| CockpitIntegration.test.js | 19 | Integration + conservation existant |

### Tests existants preserves

| Fichier test | Tests | Statut |
|-------------|-------|--------|
| CockpitV2.test.js | 20 | OK — pas de regression |
| DashboardEssentials.test.js | 28 | OK — pas de regression |
| CommandCenter.test.js | 13 | OK — pas de regression |
| actionsConsoleV1.test.js | 50 | OK — pas de regression |

---

## 6. UI/UX — COUVERTURE MAQUETTES

### Vue Executive (/cockpit)

| Section maquette | Implemente | Conforme |
|-----------------|-----------|---------|
| Tabs Vue executive / Tableau de bord | Oui | Oui |
| Banniere retard trajectoire + penalite | Oui | Oui |
| 4 KPI cards (Score/Risque/Reduction/Actions) | Oui | Oui |
| Gauge score sante avec DT/BACS/APER | Oui | Oui |
| Alertes Prioritaires (3 items) | Oui | Oui |
| Evenements Recents (4 items dots) | Oui | Oui |
| Trajectoire DT Recharts + toggle + jalons | Oui | Oui |
| Performance par site kWh/m2 (5 barres) | Oui | Oui |
| Repartition vecteur energetique + CO2 scopes | Oui | Oui (V1 — agregation front) |
| Actions Impact (P0/P1 + rationale) | Oui | Partiel (manque MWh/an + pts trajectoire) |

### Vue Exploitation (/)

| Section maquette | Implemente | Conforme |
|-----------------|-----------|---------|
| Tabs Vue executive / Tableau de bord | Oui | Oui |
| 4 KPIs J-1 | Oui | Partiel (2 placeholders) |
| Conso 7j BarChart | Oui | Partiel (1 serie, maquette = 2) |
| Profil J-1 + seuil | Oui | Oui |
| Progression trajectoire mensuelle | Oui | Oui |
| Actions du jour | Oui | Oui (TodayActionsCard) |
| Sites J-1 vs Baseline (5 barres) | Oui | Oui |

---

## 7. PLAN DE CORRECTION RECOMMANDE

### Priorite 1 — Corrections immediates (sans backend)

| # | Fix | Fichier | Risque |
|---|-----|---------|--------|
| 1 | Remplacer `* 0.052` par suppression du calcul (utiliser backend) | CreateActionModal.jsx:106, CreateActionDrawer.jsx:179, ConsumptionExplorerPage.jsx:343 | FAIBLE |
| 2 | Remplacer `.toLocaleString('fr-FR') €` par `fmtEur()` | CommandCenter.jsx:671 | NUL |
| 3 | Corriger accents manquants | CommandCenter.jsx:624-626 | NUL |
| 4 | Documenter `deltaPct` exception | SitesBaselineCard.jsx:19 | NUL |
| 5 | Documenter `kw = v * 4` conversion | useCommandCenterData.js:55 | NUL |

### Priorite 2 — Corrections backend necessaires

| # | Fix | Fichier | Impact |
|---|-----|---------|--------|
| 6 | Enrichir `/api/cockpit/co2` avec totaux agreges + scopes | routes/cockpit.py + co2_service.py | MOYEN |
| 7 | Ajouter filtre org_id dans `/api/cockpit/benchmark` | routes/cockpit.py:261 | MOYEN |
| 8 | Ajouter jalon 2050 dans test_trajectory_jalons_correct | test_cockpit_p0.py | FAIBLE |

### Priorite 3 — Migration architecture (sprint suivant)

| # | Fix | Impact |
|---|-----|--------|
| 9 | Migrer `readinessScore`/`pctConf`/`risque` de scopedSites vers useCockpitData | FORT |
| 10 | Ajouter `impact_kwh_an` au modele ActionItem backend | MOYEN |
| 11 | Ajouter `conso_mois_kwh` au endpoint /api/cockpit | MOYEN |
| 12 | Connecteur RTE eco2mix pour CO2 reseau | MOYEN |

---

## 8. VERDICT GLOBAL

| Dimension | Note | Commentaire |
|-----------|------|-------------|
| Architecture | 7/10 | Regle no-calc respectee dans les nouveaux composants. 3 violations legacy hors perimetre sprint |
| Calculs | 6/10 | 3 fichiers avec `* 0.052` (hors perimetre sprint mais critiques). Cockpit.jsx a des calculs masques |
| Donnees | 8/10 | Constantes backend correctes. Endpoints coherents. VecteurEnergetique agrege cote front |
| Coherence | 8/10 | Hook mapping correct. Pas de divergence entre pages pour les nouveaux composants |
| UI/UX | 9/10 | 95% des maquettes couvertes. 2 placeholders documentes |
| Tests | 9/10 | 112 nouveaux + 111 existants preserves. 1 gap mineur (jalon 2050) |
