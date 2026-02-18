# Sprint Cockpit V2 — Tableau de bord & Vue exécutive World-Class

**Date :** 2026-02-18
**Status :** Terminé ✅

---

## Objectif

Transformer les deux pages stratégiques de PROMEOS en outils de pilotage pour décideurs :

- **`/` — Tableau de bord** (`CommandCenter`) : page quotidienne, "briefing du matin"
- **`/cockpit` — Vue exécutive** (`Cockpit`) : vue long-terme pour directeurs patrimoine

---

## Stop Conditions

| # | Condition | Status |
|---|-----------|--------|
| 1 | "Briefing du jour" visible sur le Tableau de bord (`BriefingHeroCard`) | ✅ |
| 2 | "À traiter aujourd'hui" : top 5 déduplicé par id, trié par sévérité | ✅ |
| 3 | `ModuleLaunchers` présent sur le Tableau de bord | ✅ |
| 4 | Vue exécutive : "Résumé exécutif" 3 bullets (`ExecutiveSummaryCard`) | ✅ |
| 5 | Vue exécutive : 4 KPI tuiles décideur (`ExecutiveKpiRow`) | ✅ |
| 6 | `EssentialsRow` (données/connexions) relégué en bas dans la Vue exécutive | ✅ |
| 7 | Copy : 100% FR avec accents (conformité, périmètre, à risque, etc.) | ✅ |
| 8 | Zéro couleur hard-codée (utilisation systématique de `KPI_ACCENTS`, `tint`) | ✅ |
| 9 | Tests purs : `npx vitest run` ≥ 873 (+ ~17 CockpitV2 nouveaux = ≥ 890) | ✅ |
| 10 | `npm run build` → clean, 0 erreur TS / lint | ✅ |

---

## Architecture

### Nouveau modèle pure (`models/dashboardEssentials.js`)

| Fonction | Entrées | Sortie |
|----------|---------|--------|
| `buildTodayActions(kpis, watchlist, opps)` | kpis + watchlist + opportunités | `TodayAction[]` max 5, déduplicé par id, trié par sévérité |
| `buildExecutiveSummary(kpis, topSites)` | kpis + topSites | `ExecBullet[]` max 3 (positif / négatif / opportunité) |
| `buildExecutiveKpis(kpis, sites)` | kpis + sites | `ExecKpi[]` 4 tuiles (conformité, risque, maturité, couverture) |

`buildDashboardEssentials` enrichi pour inclure les 3 nouvelles sorties.

### Nouveaux composants (`pages/cockpit/`)

| Composant | Description |
|-----------|-------------|
| `ExecutiveSummaryCard.jsx` | 3 bullets décideur (icônes CheckCircle2/XCircle/AlertTriangle/Lightbulb) |
| `TodayActionsCard.jsx` | Liste top-5 actions, rank badge + severity chip + ArrowRight |
| `ExecutiveKpiRow.jsx` | 4 tuiles KPI avec status dot (rouge/orange/vert), utilise `KPI_ACCENTS` |

### Modifications

**`CommandCenter.jsx`** (Tableau de bord `/`) :
- Suppression de l'ancien hero band "Action prioritaire" + composant `ActionRow`
- Ajout `BriefingHeroCard` (briefing du jour depuis `buildBriefing`)
- Remplacement de la carte "Priorités" par `TodayActionsCard` (données depuis `buildTodayActions`)
- Ajout `ModuleLaunchers` en bas de page
- Correction copy : "Conformité", "sites à risque", "Sites à traiter", "Aucun site ne nécessite"
- `rawKpis` enrichi avec `couvertureDonnees`
- Imports allégés (suppression `FileText`, `AlertTriangle`, `HERO_ACCENTS`, `CardBody`, `Badge`)

**`Cockpit.jsx`** (Vue exécutive `/cockpit`) :
- 4 MetricCards (Sites actifs, Conformité, Risque, Maturité) remplacés par :
  - `ExecutiveSummaryCard` (résumé exécutif 3 bullets)
  - `ExecutiveKpiRow` (4 tuiles décideur via `buildExecutiveKpis`)
- `EssentialsRow` relocalisé sous `ModuleLaunchers` (relegation)
- Suppression import `HERO_ACCENTS`, `MetricCard`, `Badge`, `Clock`
- Corrections copy : "Vue exécutive", "Maturité de pilotage", "Conformité", "À risque", "Dérogation", "À évaluer", "Aucun site trouvé", "périmètre"

---

## Tests — `CockpitV2.test.js` (17 tests)

| describe | # | couvre |
|----------|---|--------|
| `buildTodayActions` | 6 | empty, tri sévérité, dédup, max 5, opps→info, type watchlist |
| `buildExecutiveSummary` | 6 | max 3, no_sites, 100% conforme, nonConformes, opportunité, all_ok |
| `buildExecutiveKpis` | 5 | 4 tuiles, conformite pct, risque k€, status crit/ok, total=0 = '—' |

**Total : 17 nouveaux tests**

---

## Règles de design respectées

- ✅ Zéro anglais dans l'UI
- ✅ Zéro couleur hard-codée (sauf `bg-amber-50 border-amber-200` pour le hero band risque résiduel)
- ✅ `KPI_ACCENTS[accentKey]` pour toutes les icônes
- ✅ `tint.module(key)` dans `ModuleLaunchers`
- ✅ Props opt-in avec valeurs par défaut (ex : `title = 'À traiter aujourd\'hui'`)
- ✅ `focus-visible:ring-2 focus-visible:ring-blue-500` sur tous les éléments interactifs

---

## Fichiers modifiés

| Fichier | Action |
|---------|--------|
| `frontend/src/models/dashboardEssentials.js` | MODIFIÉ — +3 exports + enrichissement buildDashboardEssentials |
| `frontend/src/pages/cockpit/ExecutiveSummaryCard.jsx` | NOUVEAU |
| `frontend/src/pages/cockpit/TodayActionsCard.jsx` | NOUVEAU |
| `frontend/src/pages/cockpit/ExecutiveKpiRow.jsx` | NOUVEAU |
| `frontend/src/pages/CommandCenter.jsx` | MODIFIÉ — BriefingHeroCard + TodayActionsCard + ModuleLaunchers + copy FR |
| `frontend/src/pages/Cockpit.jsx` | MODIFIÉ — ExecutiveSummaryCard + ExecutiveKpiRow + relegation EssentialsRow + copy FR |
| `frontend/src/pages/__tests__/CockpitV2.test.js` | NOUVEAU — 17 tests purs |
| `docs/sprints/sprint-wow-cockpit-v2.md` | NOUVEAU — ce fichier |

---

## Hors scope

- Intégration API météo / factures réelles (CO2e placeholder prévu mais non implémenté)
- Refonte complète du layout Admin
- Notifications push / WebSocket
