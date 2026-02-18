# Sprint WOW Phase 7.0 — Dashboard "Essentiels Patrimoine"

## Objectif

Transformer le Cockpit.jsx d'une vue "propre mais creuse" en un hub actionnable qui oriente l'utilisateur vers les bons modules et signale les alertes critiques.

---

## Avant / Après

### Avant (Phase 6)
```
Cockpit
├── [KPI Grid] Sites / Conformité / Risque / Maturité
├── [Hero Band] Plan d'action (conditionnel)
├── [Single site] Quick insights (1 site uniquement)
├── [Portfolio Tabs]
└── [Sites Table]
```

### Après (Phase 7.0)
```
Cockpit
├── [KPI Grid] Sites / Conformité / Risque / Maturité (inchangé)
│
├── ── WOW Phase 7.0 ──────────────────────────────
├── [ConsistencyBanner] ← Alerte data incohérente (conditionnel)
├── [EssentialsRow] 4 mini cards: Santé data / Conso / Patrimoine / Maturité
├── [WatchlistCard] "À surveiller" — max 5 items, severity-sorted
├── [OpportunitiesCard] 3 reco cards (Expert only)
├── [TopSitesCard] Worst 5 / Best 5 (portfolio only, collapsed)
├── [ModuleLaunchers] 5 tuiles de navigation module
│
├── [Hero Band] Plan d'action (conditionnel, inchangé)
├── [Single site] Quick insights (inchangé)
├── [Portfolio Tabs] (inchangé)
└── [Sites Table] (inchangé)
```

---

## Fichiers créés/modifiés

| Fichier | Action | Rôle |
|---------|--------|------|
| `src/models/dashboardEssentials.js` | Nouveau | Couche model pure: buildWatchlist, checkConsistency, buildTopSites, buildOpportunities |
| `src/pages/cockpit/EssentialsRow.jsx` | Nouveau | 4 mini MetricCards compacts |
| `src/pages/cockpit/WatchlistCard.jsx` | Nouveau | Feed "À surveiller" |
| `src/pages/cockpit/OpportunitiesCard.jsx` | Nouveau | 3 reco cards Expert |
| `src/pages/cockpit/TopSitesCard.jsx` | Nouveau | Worst 5 / Best 5 (pliable) |
| `src/pages/cockpit/ModuleLaunchers.jsx` | Nouveau | Tuiles navigation modules |
| `src/pages/Cockpit.jsx` | Modifié | Intégration des nouvelles sections |
| `src/pages/__tests__/DashboardEssentials.test.js` | Nouveau | 14 tests purs (vitest) |
| `docs/sprint-wow-phase7-dashboard-essentials.md` | Nouveau | Ce document |

---

## Couche Model — `dashboardEssentials.js`

Fonctions pures exportées (aucun import React, testables en isolation) :

### `buildWatchlist(kpis, sites) → WatchItem[]`

Génère jusqu'à 5 éléments triés par sévérité (critical → info) :

| # | Condition | Sévérité | Path | CTA |
|---|-----------|----------|------|-----|
| 1 | `kpis.nonConformes > 0` | `critical` | `/conformite` | Voir conformité |
| 2 | `kpis.aRisque > 0` | `high` | `/actions` | Plan d'action |
| 3 | sites sans `conso_kwh_an` | `warn` | `/consommations/import` | Importer |
| 4 | `couvertureDonnees < 50 && total >= 3` (si pas de #3) | `medium` | `/consommations/import` | Compléter |

→ État vide = "Tout va bien ✓"

### `checkConsistency(kpis) → { ok, issues }`

| Code | Condition |
|------|-----------|
| `all_conformes_low_data` | `conformeRate === 100% && couvertureDonnees < 30 && total > 0` |
| `no_data_coverage` | `couvertureDonnees === 0 && total > 0` |

### `buildTopSites(sites) → { worst, best }`

- **worst 5** : `statut_conformite !== 'conforme'`, triés par `risque_eur DESC`
- **best 5** : `statut_conformite === 'conforme'`, triés par `conso_kwh_an ASC`

### `buildOpportunities(kpis, sites, { isExpert }) → Opportunity[]`

Retourne `[]` quand `!isExpert`. Max 3 items :

| # | Condition | Label |
|---|-----------|-------|
| 1 | `couvertureDonnees < 80` | Compléter les données (X% couvert) |
| 2 | `nonConformes > 0` | Réduire le risque Décret (N sites en retard) |
| 3 | `risqueTotal > 10000` | Optimiser les abonnements (Xk EUR) |

---

## Règles de design

1. **Aucune couleur hard-codée** dans les nouveaux composants :
   - Icônes/fonds → `tint.module(key).softBg()` + `tint.module(key).icon()`
   - Accents KPI → `KPI_ACCENTS[accentKey].iconBg` / `.iconText`
   - Dots sévérité → `SEVERITY_TINT[severity].dot`
   - Bordures → `tint.module('analyse').raw().activeBorder`

2. **Aucun anglais dans l'UI** : tous les labels, CTAs et messages en français.

3. **Accessibilité** : tous les éléments interactifs ont `focus-visible:ring-2 focus-visible:ring-blue-500`.

4. **Noms de sites tronqués** : `className="truncate"` + `title={site.nom}`.

5. **Progressive disclosure** : TopSitesCard plié par défaut (bouton "Analyse détaillée ▾/▴").

---

## Divulgation progressive

| Section | Visibilité |
|---------|------------|
| EssentialsRow | Toujours visible |
| WatchlistCard | Toujours visible |
| ModuleLaunchers | Toujours visible |
| OpportunitiesCard | Expert uniquement, max 3 cards compactes |
| TopSitesCard | Mode portfolio uniquement (`!isSingleSite`), plié par défaut |
| ConsistencyBanner | Conditionnel — `!consistency.ok` |

---

## Tests — `DashboardEssentials.test.js`

14 tests purs en 4 blocs `describe` :

```
describe('buildWatchlist') [4 tests]
  ✓ nonConformes=3 → severity=critical, path=/conformite
  ✓ sites sans conso → severity=warn, path=/consommations/import
  ✓ all conformes + all have conso → returns []
  ✓ 6 conditions → capped at 5 items

describe('checkConsistency') [3 tests]
  ✓ conformeRate=100%, couvertureDonnees=10% → !ok, all_conformes_low_data
  ✓ couvertureDonnees=0, total=5 → !ok, no_data_coverage
  ✓ healthy state → ok=true, issues=[]

describe('buildTopSites') [4 tests]
  ✓ worst 5 sorted by risque_eur DESC
  ✓ best 5 conformes only
  ✓ empty sites → both arrays empty
  ✓ only 2 non-conformes → worst has length 2

describe('buildOpportunities') [3 tests]
  ✓ isExpert=false → []
  ✓ isExpert=true + couvertureDonnees<80 → complete_data opportunity
  ✓ all 3 conditions → capped at 3
```

---

## Vérification

```bash
# Tests
npx vitest run    # ≥ 818 tests verts

# Build
npm run build     # 0 erreur, 0 warning

# QA manuel
# 1. /cockpit → EssentialsRow visible sous les KPIs existants
# 2. "À surveiller" : items présents si nonConformes > 0
# 3. "À surveiller" : "Tout va bien ✓" si tout est conforme + données présentes
# 4. Expert ON → OpportunitiesCard visible
# 5. Single site → TopSitesCard masqué, ModuleLaunchers visible
# 6. ConsistencyBanner si couvertureDonnees=0 && total>0
# 7. ModuleLaunchers : Marché/Admin masqués en mode non-Expert
# 8. Clic tuile module → navigation correcte
# 9. grep "bg-blue-500\|bg-red-500\|bg-green-500" src/pages/cockpit/*.jsx → 0 résultat
```

---

## Non dans le périmètre

- Nouveaux endpoints backend
- Modification du KPI grid existant (MetricCards conservées à l'identique)
- Modification de ConsumptionExplorer, ConformitePage ou autres pages
- Temps réel WebSocket, graphiques complexes, changements d'auth multi-tenant
