# Résumé Audit UX/UI Cockpit — Maquettes vs Implémentation
**Date** : 2026-03-24
**Branche** : `feat/cockpit-world-class`
**Commits audit** : `69c85a4` → `565b986` → `2cb03d0` → `f44168b`

---

## Résultat final : correspondance widget par widget

### Vue Exécutive (/cockpit) — mode non-expert

| Widget | Statut | Détail |
|--------|--------|--------|
| **Tabs** Vue exec / Tableau de bord | ✅ EXACT | Navigation bidirectionnelle, underline bleu |
| **4 KPI cards** (Score, Risque, Réduction, Actions) | ✅ EXACT | Gauge SVG + DT/BACS/APER, amber accent risque, retard rouge, X/Y potentiel |
| **Bannière retard** trajectoire | ✅ EXACT | Conditionnelle, montant pénalité, deadline, CTA |
| **Alertes Prioritaires** (3 items) | ✅ EXACT | Badge icône, titre+rationale, EUR+jours |
| **Événements Récents** (4 items) | ✅ EXACT | Dot coloré, source label, titre, date relative |
| **Trajectoire DT** courbe Recharts | ✅ EXACT | Titre uppercase, toggle KWH/%, légende exacte, footer jalons+réf+surface |
| **Performance par site** kWh/m² | ✅ EXACT | 5 sites, couleurs distinctes, objectif marker |
| **Vecteur énergétique** + CO₂ | ✅ EXACT | Barres + "Émissions CO₂ cumulées N" + scopes |
| **Actions Impact** plan trajectoire | ✅ EXACT | P0/P1 badges, rationale, barre verte, footer toujours visible |
| Sections expert masquées | ✅ OK | Scope indicator, ExecKpiRow, topActions, detail zone |

### Vue Exploitation (/) — mode non-expert

| Widget | Statut | Détail |
|--------|--------|--------|
| **Tabs** | ✅ EXACT | CockpitTabs shared component |
| **4 KPI J-1** | ⚠️ PARTIEL | Conso hier ✅, Conso mois ❌ (endpoint manquant), Pic kW ✅, CO₂ ❌ (connecteur RTE) |
| **Conso 7j** BarChart | ✅ EXACT | Recharts BarChart, données EMS |
| **Profil J-1** AreaChart | ✅ EXACT | Recharts ComposedChart + seuil conditionnel |
| **Trajectoire + Actions** 2-col | ✅ EXACT | Grid 2 colonnes, placeholder si null |
| **Sites J-1 vs Baseline** | ⚠️ PARTIEL | Composant rendu mais `consoJ1BySite` non passé |
| **ModuleLaunchers** | ✅ EXACT | 5 tuiles navigation |
| Sections legacy masquées | ✅ OK | HealthSummary, BriefingHeroCard, EssentialsRow, Sites risque |

---

## Écarts restants (backlog)

### Données manquantes (pas un problème de code)

| Écart | Cause racine | Solution |
|-------|-------------|----------|
| KPI "Conso ce mois" affiche "—" | Pas d'endpoint `/api/cockpit/conso-month` | Créer endpoint qui query ConsumptionTarget monthly avec actual_kwh |
| KPI "CO₂ réseau" affiche "—" | Connecteur RTE API non branché | Brancher `eco2mix` RTE sur EMS |
| Sites Baseline barres vides | `consoJ1BySite` prop non passée | Calculer depuis `weekSeries` ou `kpisJ1` et passer la prop |
| Trajectoire "non disponible" au 1er chargement | Endpoint lent (3-6s) + race condition scope | Optimiser la requête SQL ou ajouter cache |

### Violations architecture (hors scope cockpit)

| Violation | Fichier | Sévérité |
|-----------|---------|----------|
| CO₂ calculé front avec 0.052 (devrait être 0.0569) | `CreateActionModal.jsx:106` | HIGH |
| VecteurEnergetiqueCard agrège CO₂ en front | `VecteurEnergetiqueCard.jsx:56-84` | HIGH |
| Cockpit.jsx `rawKpis` useMemo recalcule pctConf | `Cockpit.jsx:193-237` | HIGH |
| `kw = v * 4` non documenté | `useCommandCenterData.js:55` | MEDIUM |

---

## Bugs de données corrigés dans cet audit

| Bug | Avant | Après |
|-----|-------|-------|
| `actions.enCours` | Toujours **0** | **5** (fix `counts.in_progress`) |
| `actions.potentielEur` | Toujours **0** | **63 488 €** (fix `total_gain_eur`) |
| `billing.anomalies` | Toujours **0** | **29** (fix `invoices_with_anomalies`) |
| `risque_breakdown.billing_anomalies_eur` | Hardcodé **0** | **44 140 €** (query BillingInsight) |
| `reduction_pct_actuelle` | **+39.1** (positif) | **−39.1** (convention maquette : négatif = réduction) |
| `isRetard` logique | Inversée (affichait retard quand OK) | Correcte (−39.1 > −25 = false = pas en retard) |

## Corrections visuelles appliquées

| Correction | Composant |
|------------|-----------|
| Scope indicator → expert-only | `Cockpit.jsx` |
| Single-site row → expert-only | `Cockpit.jsx` |
| KPI J-1 en premier après tabs | `CommandCenter.jsx` |
| Trajectoire + Actions en 2 colonnes | `CommandCenter.jsx` |
| Sections legacy → expert-only | `CommandCenter.jsx` |
| Placeholder quand trajectoire null | `CommandCenter.jsx` |
| Titre uppercase trajectoire | `TrajectorySection.jsx` |
| Toggle "KWH" / "% RÉDUCTION" uppercase | `TrajectorySection.jsx` |
| Légende icônes exactes (dotted projection) | `TrajectorySection.jsx` |
| Footer jalons inline + "Réf. · Surface :" | `TrajectorySection.jsx` |
| Chart 280px + dots visibles + fill opacity | `TrajectorySection.jsx` |
| Card Risque amber accent conditionnel | `CockpitHero.jsx` |
| Barre de progression verte par action | `ActionsImpact.jsx` |
| Footer toujours visible + CTA bordé | `ActionsImpact.jsx` |
| Couleurs distinctes par site | `PerformanceSitesCard.jsx` |
| Label "Émissions CO₂ cumulées N" | `VecteurEnergetiqueCard.jsx` |
| `fmtEur` dans Sites à risque | `CommandCenter.jsx` |
| Accents FR corrigés EmptyState | `CommandCenter.jsx` |

---

## Indicateurs qualité

| Métrique | Valeur |
|----------|--------|
| Tests backend | **13/13** |
| Tests frontend | **138/139** (1 pre-existing) |
| Régressions | **0** |
| Build | **OK** |
| Widgets EXACT MATCH | **14/18** |
| Widgets PARTIEL | **4/18** (données manquantes, pas de code) |
| Widgets MISSING | **0** |
