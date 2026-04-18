# SOL_WIREFRAME_SPEC.md

> **Source de vérité visuelle** : `docs/sol/maquettes/cockpit-sol-v1-adjusted-v2.html` (V2 raw, warm accents "journal en terrasse")
> **Branche** : `claude/refonte-visuelle-sol` — worktree `promeos-refonte` port 5174
> **Backend commun** : main canonical port 8001 (jamais modifié)
> **Main canonical UI** : port 5173 (continue pour comparaison A/B)

---

## 1. Résumé exécutif

Cette spec documente le **mapping 1:1** entre chaque zone de la maquette `cockpit-sol-v1-adjusted-v2.html` et :
- la donnée PROMEOS existante (API + hook + helper),
- le composant Sol cible (`frontend/src/ui/sol/*`),
- la transformation nécessaire (helper pur, mock, câblage Sol V1 différé).

**Règle d'or** : aucun nouvel endpoint backend. Toutes les données proviennent d'APIs **déjà opérationnelles sur main**. Les composants Sol sont de présentation pure.

**Gate 0** : ce document doit être validé par Amine avant Phase 1 (création des composants).

---

## 2. APIs PROMEOS disponibles (audit main)

### 2.1 Cockpit (`frontend/src/services/api/cockpit.js`)

Fonctions pertinentes pour la refonte :
- `getCockpit()` — `/cockpit` → synthèse portefeuille (KPIs conso, économies, tendances)
- `getCockpitTrajectory()` — `/cockpit/trajectory` → trajectoire DT (current -12.4 %, target -25 %)
- `getCockpitBenchmark()` — `/cockpit/benchmark`
- `getCockpitCo2()` — `/cockpit/co2`
- `getCockpitConsoMonth()` — `/cockpit/conso-month`
- `getNotificationsSummary(orgId, siteId)` — `/notifications/summary?type=alert`
- `getNotificationsList(params)` — `/notifications/list`
- `getValueSummary(orgId)` — `/value-counter/summary`
- `getPortfolioSummary(params)` — `/portfolio/summary`
- `getPortfolioSites(params)` — `/portfolio/sites`

### 2.2 Billing (`frontend/src/services/api/billing.js`)

- `getBillingSummary(params)` — `/billing/summary` → total mensuel, sites, deltas
- `getBillingInsights(params)` — insights détection anomalies
- `getInvoiceShadowBreakdown(invoiceId)` — ventilation canonique 6 composantes
- `getBillingCompareMonthly(params)` — comparatif mois M-1/M-12

### 2.3 Conformité (`frontend/src/services/api/conformite.js`)

- `getComplianceScoreTrend(params)` — `/compliance/score-trend` → `{ currentScore, previousScore, sitesByStatus }`
- `getComplianceTimeline()` — `/compliance/timeline` → événements validés / à venir
- `getComplianceSummary(params)` — `/compliance/summary`
- `getComplianceFindings(params)` — findings avec statut
- `getAuditSmeAssessment(orgId)` — audit énergétique

### 2.4 EMS / Énergie (`frontend/src/services/api/ems.js`)

- `getEmsTimeseries({ site_ids, date_from, date_to, granularity, mode, metric })` — courbe de charge
- `getEmsCdc(meterId, dateFrom, dateTo)` — courbe de charge classifiée TURPE (avec `slot` HPH/HCH/HPE/HCE/HP/HC)

### 2.5 Patrimoine (`frontend/src/services/api/patrimoine.js`)

- `getPatrimoineSites(params)` — liste sites avec surface, conso, compliance_score
- `getSiteDetail(siteId)` — fiche site complète

### 2.6 Achat (`frontend/src/services/api/purchase.js`)

- `getRadarEcheances()` — contrats à renouveler
- `getPurchaseScenarios(siteId)` — scénarios d'achat
- `getCostSimulator(params)` — simulation post-ARENH

### 2.7 Sol V1 (**différé Phase 4.6 post-merge**)

Quand `claude/sol-v1-audit` sera mergée vers main :
- `GET /api/sol/pending` — propositions d'actions en attente
- `GET /api/sol/audit` — journal actions Sol
- `POST /api/sol/schedule` — planifier action Sol
- Aujourd'hui : **mock `solProposal = null`** dans V2 (hero n'apparaît pas)

---

## 3. NavRegistry — 5 modules visibles + Admin (expertOnly)

Source : `frontend/src/layout/NavRegistry.js`

| Ordre | Key | Label | Tint V1 | Icon | expertOnly |
|---|---|---|---|---|---|
| 1 | `cockpit` | Accueil | blue | `LayoutDashboard` | ✗ |
| 2 | `conformite` | Conformité | emerald | `ShieldCheck` | ✗ |
| 3 | `energie` | Énergie | indigo | `Zap` | ✗ |
| 4 | `patrimoine` | Patrimoine | amber | `Building2` | ✗ |
| 5 | `achat` | Achat | violet | `ShoppingCart` | ✗ |
| 6 | `admin` | Administration | slate | `Settings` | ✓ |

**Pour SolRail** : les 5 premiers icons sont utilisés tel quel (re-stylisés V2 slate, pas les tints Tailwind V1). Admin reste conditionnel (expertOnly + DG_OWNER).

**Pour SolPanel** : `getSectionsForModule(moduleKey)` + `getVisibleItems(items, expertMode)` donnent les items du module actif. Le `label` du module courant devient le `panel-module`. Le `desc` devient le `panel-desc`.

**Ordre role-based** : `getOrderedModules(role, isExpert)` (ex. DG_OWNER : cockpit → achat → conformité → patrimoine → énergie). À respecter dans SolRail.

---

## 4. Mapping zone maquette ↔ donnée PROMEOS

### 4.1 Chrome global (toutes pages)

| Zone maquette | Source PROMEOS | Fichier cible | Transformation |
|---|---|---|---|
| `rail-logo` "P." (Fraunces) | Statique | `SolRail.jsx` | — |
| 5 `rail-icon` | `getOrderedModules(role, isExpert)` | `SolRail.jsx` | `modules.map(m => <m.icon/>)` |
| rail-icon active state | `useLocation().pathname` + `resolveModule()` | `SolRail.jsx` | Compare avec `m.key` |
| `panel-module` (titre) | `NAV_MODULES.find(m => m.key === moduleKey).label` | `SolPanel.jsx` | — |
| `panel-desc` | `NAV_MODULES.find(...).desc` + scope context | `SolPanel.jsx` | `buildPanelDesc(scope, date)` |
| `panel-section` | `getSectionsForModule(moduleKey)` | `SolPanel.jsx` | Filter via `getVisibleItems` |
| `panel-item` (label + desc) | Items de la section | `SolPanel.jsx` | `to`, `label`, `desc`, `icon` |
| `panel-item` badge "3" | `getNotificationsSummary(orgId)` | `SolPanel.jsx` | Per-item via `badgeKey` |
| `timerail-live-dot` + HP/HC | Heure courante + grille tarifaire | `SolTimerail.jsx` | Helper `getCurrentTariffPeriod()` |
| `timerail-week` | ISO week `dayjs().isoWeek()` | `SolTimerail.jsx` | Helper `buildWeekLabel()` |
| `timerail-traj` (-12,4 % / -25 %) | `getCockpitTrajectory()` ou `getComplianceScoreTrend()` | `SolTimerail.jsx` | `{ current, target }` |
| `timerail-sol-status` "3 actions en attente" | Mock en V2 | `SolTimerail.jsx` | Câblage Sol V1 Phase 4.6 |
| `sol-cartouche` (bas-droit fixed) | Mock `default` en V2 | `SolCartouche.jsx` | Câblage Sol V1 Phase 4.6 |

### 4.2 Cockpit (`/cockpit` → `CockpitSol.jsx`)

| Zone maquette | Source PROMEOS | Fichier cible | Transformation |
|---|---|---|---|
| `page-kicker` "Cockpit · semaine 16 · patrimoine HELIOS" | `useScope().orgName` + ISO week | `SolPageHeader.jsx` | Helper `buildKicker(scope)` |
| `page-title` "Bonjour — voici votre semaine" (DM Sans + em Fraunces) | Statique + greeting temporel | `SolPageHeader.jsx` | Helper `buildGreeting()` |
| `layer-toggle` Surface/Inspect/Expert | `useState('surface')` local | `SolLayerToggle.jsx` | — |
| `sol-headline` (phrase narrative) | `getBillingSummary` + `getComplianceScoreTrend` + alerts | `SolHeadline.jsx` | `buildCockpitNarrative(billing, compliance, alerts)` |
| `sol-subline` (sous-phrase) | `useScope` + schedule Sol | `SolSubline.jsx` | `buildCockpitSubNarrative(scope, schedule)` |
| `sol-hero` (conditionnel) | Mock `null` en V2 | `SolHero.jsx` | Hidden si `solProposal === null` |
| **KPI 1** "Facture énergie · mars" `47 382 €` | `getBillingSummary({ scope })` | `SolKpiCard.jsx` | `{ totalCost, previousCost, fournisseurCount }` |
| KPI 1 delta "+8,2 % vs fév" | `getBillingSummary` M-1 | Helper | `computeDelta(currentCost, previousCost)` |
| KPI 1 headline "Hausse tirée par Lyon et Nice" | Helper pur | Helper `interpretCost` | `interpretCost(billing, topDrivers)` |
| KPI 1 source chip "Factures fournisseur" | Statique | `SolSourceChip.jsx` | `kind="factures"` |
| **KPI 2** "Conformité DT" `62/100` | `getComplianceScoreTrend({ scope })` | `SolKpiCard.jsx` | `{ currentScore, previousScore }` |
| KPI 2 delta "-2 pts vs fév" | `getComplianceScoreTrend` | Helper | `computeDelta(currentScore, previousScore, 'pts')` |
| KPI 2 headline "en zone à risque" | Helper pur | Helper `interpretCompliance` | Seuils 60/75 → `{att, risk, ok}` |
| KPI 2 source chip "RegOps canonique" | Statique | `SolSourceChip.jsx` | `kind="regops"` |
| **KPI 3** "Consommation · patrimoine" `1 847 MWh` | `getCockpit()` | `SolKpiCard.jsx` | `{ totalConso, previousYearConso }` |
| KPI 3 delta "-4,1 % vs mars 2024" | `getCockpit` N-1 | Helper | `computeDelta(totalConso, previousYearConso)` |
| KPI 3 headline "baisse organique sites tertiaires" | Helper pur | Helper `interpretConso` | — |
| KPI 3 source chip "Enedis + Engie Solutions" | Meta API | `SolSourceChip.jsx` | `kind="enedis"` |
| **week-card 1** "À regarder" dérive | `getNotificationsSummary` filtré `type='derive'` | `SolWeekCard.jsx` | `slice(0, 1)` tag=`attention` |
| **week-card 2** "À faire" échéance | `getComplianceTimeline()` | `SolWeekCard.jsx` | `filter(e => e.dueDate > now).sort(asc)[0]` tag=`afaire` |
| **week-card 3** "Bonne nouvelle" validation | `getComplianceTimeline()` | `SolWeekCard.jsx` | `filter(e => e.status === 'validated').sort(desc)[0]` tag=`succes` |
| **courbe de charge** SVG 48 points | `getEmsTimeseries({ site_ids: criticalSiteId, granularity: '30min' })` | `SolLoadCurve.jsx` | Fallback mock 24 h si endpoint vide |
| courbe pic annoté "14h32" | Helper pur | Helper `findPeak(series)` | Max argmax |
| légende "85 % en HP" | Helper pur | Helper `computeHPShare(series, tariffGrid)` | — |
| bandes HP/HC (ReferenceArea) | Grille tarifaire statique | `SolLoadCurve.jsx` | Constantes `HP_HOURS = [6..22]` |

### 4.3 Conformité DT (`/conformite` → `ConformiteSol.jsx`)

| Zone maquette | Source PROMEOS | Fichier cible | Transformation |
|---|---|---|---|
| `page-kicker` "Conformité · décret tertiaire · HELIOS" | `useScope` + statique | `SolPageHeader.jsx` | `buildKicker('conformite')` |
| `page-title` "Conformité DT" + em "11 oct" | Deadline 11/10/2026 | `SolPageHeader.jsx` | Statique |
| `sol-headline` "Vous êtes à 62/100..." | `getComplianceScoreTrend` | Helper `buildConformiteNarrative` | — |
| `sol-subline` "Il reste N mois..." | Date deadline | Helper `buildConformiteSubNarrative(deadline)` | — |
| **KPI 1** Score global `62/100` | `getComplianceScoreTrend` | `SolKpiCard.jsx` | — |
| **KPI 2** Sites conformes `4/12` | `getComplianceSummary` | `SolKpiCard.jsx` | Count by status |
| **KPI 3** Réduction actuelle `-12,4 %` | `getComplianceScoreTrend` | `SolKpiCard.jsx` | — |
| Liste obligations (DT, BACS, APER, SMÉ) | `getComplianceFindings` + `getAuditSmeAssessment` | `ConformiteSol.jsx` | Grid 2 cols |
| Timeline échéances | `getComplianceTimeline()` | `SolWeekGrid.jsx` | Items triés par dueDate |

### 4.4 Bill Intelligence (`/bill-intel` → `BillIntelSol.jsx`)

| Zone maquette | Source PROMEOS | Fichier cible | Transformation |
|---|---|---|---|
| `page-kicker` "Facturation · mars 2026" | Month current | `SolPageHeader.jsx` | — |
| `page-title` "Anomalies factures" | Statique | — | — |
| `sol-headline` "47 382 €..." | `getBillingSummary` + `getBillingInsights` | Helper `buildBillNarrative` | — |
| **KPI 1** Total facturé `47 382 €` | `getBillingSummary` | `SolKpiCard.jsx` | — |
| **KPI 2** Anomalies détectées `N` | `getBillingInsights` | `SolKpiCard.jsx` | `insights.length` |
| **KPI 3** Économie potentielle `€` | `getBillingInsights` | `SolKpiCard.jsx` | Sum `potential_saving_eur` |
| Table anomalies (shadow breakdown) | `getInvoiceShadowBreakdown` | `SolExpertGrid.jsx` (mode Expert) | 6 composantes |
| Timeline factures | `getBillingCompareMonthly` | `SolLoadCurve.jsx` (adapté) | — |

### 4.5 Patrimoine (`/patrimoine` → `PatrimoineSol.jsx`)

| Zone maquette | Source PROMEOS | Fichier cible | Transformation |
|---|---|---|---|
| `page-kicker` "Patrimoine · HELIOS · 12 sites" | `useScope` + count | `SolPageHeader.jsx` | — |
| `page-title` "Vos sites" | Statique | — | — |
| `sol-headline` "12 sites, 48 230 m²..." | `getPortfolioSummary` | Helper `buildPatrimoineNarrative` | — |
| **KPI 1** Sites `12` | `getPortfolioSummary` | `SolKpiCard.jsx` | — |
| **KPI 2** Surface totale `48 230 m²` | `getPortfolioSummary` | `SolKpiCard.jsx` | — |
| **KPI 3** Conso /m² `142 kWh/m²` | `getPortfolioSummary` | `SolKpiCard.jsx` | — |
| Carte sites (liste) | `getPatrimoineSites()` | `SolExpertGrid.jsx` (Expert) ou `SolWeekGrid` (Surface) | — |

### 4.6 Achat énergie (`/achat-energie` → `AchatSol.jsx`)

| Zone maquette | Source PROMEOS | Fichier cible | Transformation |
|---|---|---|---|
| `page-kicker` "Achat énergie · 2026" | Statique | `SolPageHeader.jsx` | — |
| `page-title` "Arbitrage & renouvellements" | Statique | — | — |
| `sol-headline` "N contrats à renouveler" | `getRadarEcheances` | Helper | — |
| **KPI 1** Contrats à renouveler | `getRadarEcheances` | `SolKpiCard.jsx` | — |
| **KPI 2** Volume énergie à arbitrer | `getPurchaseScenarios` | `SolKpiCard.jsx` | — |
| **KPI 3** Économie potentielle | `getCostSimulator` | `SolKpiCard.jsx` | — |
| Scénarios post-ARENH | `getCostSimulator({ year })` | `SolWeekGrid.jsx` | — |

---

## 5. Helpers presenters (purs, pas de fetch)

Fichier cible : `frontend/src/pages/cockpit/sol_presenters.js` (déjà partiel, à enrichir)

### 5.1 Kicker / Greeting / Scope

```js
buildKicker(scope, route)        // "Cockpit · semaine 16 · patrimoine HELIOS"
buildGreeting(hour)              // "Bonjour" / "Bonsoir" selon heure
buildPanelDesc(scope, moduleKey) // "Votre cockpit énergétique, semaine du 14 avril"
buildWeekLabel(date)             // "Sem. 16 · avril"
```

### 5.2 Narratives (sol-headline + sol-subline)

```js
buildCockpitNarrative({ billing, compliance, alerts })
buildCockpitSubNarrative({ scope, schedule })
buildConformiteNarrative({ complianceTrend, findings })
buildConformiteSubNarrative({ deadline })
buildBillNarrative({ billingSummary, insights })
buildPatrimoineNarrative({ portfolioSummary })
buildAchatNarrative({ radar, scenarios })
```

### 5.3 Interpretations (KPI headlines)

```js
interpretCost({ totalCost, previousCost, topDrivers })
  // → "Hausse tirée par Lyon et Nice"
interpretCompliance({ currentScore, previousScore })
  // Seuils : score >= 75 → { kind: 'ok', text: 'conformité solide' }
  //          60 <= score < 75 → { kind: 'att', text: 'vigilance' }
  //          score < 60 → { kind: 'risk', text: 'en zone à risque' }
interpretConso({ totalConso, previousYearConso })
  // → "baisse organique sites tertiaires"
```

### 5.4 Week cards builders

```js
buildWeekCards({ notifications, timeline })
// Returns [{ kind: 'attention', title, body, footer }, ...]
```

### 5.5 Load curve helpers

```js
findPeak(series)                     // → { time: '14:00', kw: 118 }
computeHPShare(series, tariffGrid)   // → 0.85 → "85 %"
getCurrentTariffPeriod(date)         // → { period: 'HP', endsAt: '22h' }
```

### 5.6 Deltas & formatters

```js
computeDelta(current, previous, unit = '%')
  // → { value: 8.2, direction: 'up', formatted: '+8,2 %' }
formatFR(number, decimals = 0)
  // → "1 847" avec espaces fines U+202F
formatFREur(amount, decimals = 0)
  // → "47 382 €"
```

---

## 6. Mocks V2 (Sol V1 différé)

**Raison** : la branche `claude/sol-v1-audit` n'est pas mergée vers main. Pour éviter la friction inter-branches, V2 mock les données Sol côté frontend.

### 6.1 `solProposal`

```js
const solProposal = null; // → SolHero ne s'affiche pas
```

En Phase 4.6 (post-merge), remplacer par :
```js
const { data: solProposal } = useSolPending(scope);
```

### 6.2 `solStatus` (timerail)

```js
const solStatus = { state: 'veille', pending: 3 };
// → "Sol · en veille · 3 actions en attente"
```

### 6.3 `solCartoucheState`

```js
const [cartoucheState, setCartoucheState] = useState('default');
// 5 états : default | proposing | pending | executing | done
// En V2 : toujours 'default'
```

---

## 7. Composants Sol à créer (21 total)

### 7.1 Déjà existants (Sprint 2, à auditer/migrer)

1. `SolPageHeader.jsx` ✓ (existe, à valider styles V2)
2. `SolKpiCard.jsx` ✓ (existe, à valider props)
3. `SolHero.jsx` ✓ (existe, conditionnel)
4. `SolWeekCard.jsx` ✓ (existe, 3 tag kinds)
5. `SolSourceChip.jsx` ✓ (existe, mono 9.5 px)
6. `SolSectionHead.jsx` ✓ (existe, Fraunces + mono meta)
7. `SolLoadCurve.jsx` ✓ (existe, Recharts + HP/HC bands)
8. `SolTimerail.jsx` ✓ (existe, 4 zones)

### 7.2 Nouveaux Phase 1 (13)

9. `SolAppShell.jsx` — layout grid 56/240/1fr/36
10. `SolRail.jsx` — rail 56 px logo "P." + 5 icons NavRegistry
11. `SolPanel.jsx` — panel 240 px lit NAV_SECTIONS
12. `SolKpiRow.jsx` — grid 3 cols exactement
13. `SolWeekGrid.jsx` — grid 3 cols gap 12
14. `SolLayerToggle.jsx` — segmented Surface/Inspect/Expert
15. `SolCartouche.jsx` — bas-droit fixed 5 états
16. `SolDrawer.jsx` — wrapper ui/Drawer existant
17. `SolPendingBanner.jsx` — bannière envoi dans Xh
18. `SolInspectDoc.jsx` — prose éditoriale max-w 760
19. `SolExpertGrid.jsx` — table dense 6 cols sortable
20. `SolJournal.jsx` — journal append-only
21. `SolStatusPill.jsx` + `SolButton.jsx` + `SolHeadline.jsx` + `SolSubline.jsx`

### 7.3 Fichiers support

- `frontend/src/ui/sol/tokens.css` — CSS vars (imported once in `index.css`)
- `frontend/src/ui/sol/index.js` — barrel export
- `frontend/src/ui/sol/__tests__/sol_source_guard.test.js` — regex tests
- `frontend/src/ui/sol/__tests__/sol_components.test.jsx` — render tests

---

## 8. Endpoints **non utilisés** par la refonte

Pour clarté : ces endpoints existent sur main mais la refonte V2 ne les appelle pas en Phase 2-5.

- `/pilotage/*` (NEBCO, radar J+7) — reste accessible via `/pilotage` en mode V1
- `/flex/*` — Flex retiré WIP
- `/cbam/*` — nouveau P3, pas dans les 4 pages flagship
- `/public/diagnostic/*` — wedge freemium P2, hors scope refonte

---

## 9. Invariants de zéro régression

Avant chaque commit Phase 2-5 :

```bash
# 1. Zéro touch backend
git diff --name-only origin/main... | grep -E '^backend/' && echo 'REGRESSION' || echo 'OK'

# 2. Zéro modif NavRegistry (sauf lecture)
git diff origin/main... frontend/src/layout/NavRegistry.js && echo 'REGRESSION' || echo 'OK'

# 3. Zéro modif api/* (sauf ajouts nouveaux helpers)
git diff --stat origin/main... frontend/src/services/api/

# 4. Baseline tests verts
cd frontend && npx vitest run
```

**Source-guards Sol** (Phase 1) :
- Pas de `fetch(` / `axios.` dans `ui/sol/*`
- Pas de `useState` de données (seulement UI state)
- Pas de hex hardcodés (sauf `#FFFFFF`, `transparent`, `currentColor`)
- Tous les composants utilisent `var(--...)`

---

## 10. Timeline phases

| Phase | Durée | Output | Gate |
|---|---|---|---|
| **0** | 45 min | Ce document | ⟵ ici |
| **1** | 4-5 h | 21 composants + tokens + source-guards | Showcase `/_sol_showcase` screenshot |
| **2** | 4 h | `CockpitSol.jsx` branché API | Screenshot + comparaison 5173 vs 5174 |
| **3** | 1 h | `SolAppShell` remplace `AppShell` global | Toutes routes V1 fonctionnent |
| **4** | 10-12 h | 4 pages flagship (Conformité → Bill → Patrimoine → Achat) | Screenshot × 4 |
| **5** | 2 h | Frenchifier + build prod + tag `v2.0-refonte-sol` | Build clean, bundle <1 MB |
| **6** | Optionnel | Câblage Sol V1 APIs (hero + cartouche + pending banner) | Post-merge `claude/sol-v1-audit` |

---

## 11. Décisions de design figées (rappel)

1. **V2 raw** comme source (slate + warm accents), pas V2 polished (trop éditorial)
2. **Fraunces** seulement : rail-logo, sol-hero-title, drawer-title, preview-box courrier, prose Inspect
3. **DM Sans** partout ailleurs · **JetBrains Mono** tous chiffres/kickers/chips
4. **Google Fonts CDN** en V2 (self-hosting = V3)
5. **Composants V1 laissés en place** (pas de ménage parallèle)
6. **3 modes Surface/Inspect/Expert** : Cockpit seulement en Phase 2, autres pages en Phase 6
7. **Sol hero mocké `null`** en V2, câblage Phase 4.6

---

**Fin SOL_WIREFRAME_SPEC.md · Gate 0 · Attente validation Amine avant Phase 1.**
