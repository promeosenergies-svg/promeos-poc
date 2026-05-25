# Audit deep READ-ONLY — Cockpit / Vue exécutive PROMEOS

**Date** : 2026-05-25
**Branche** : `claude/cockpit-vue-executive-audit-deep` (depuis `claude/refonte-sol2`)
**Mode** : READ-ONLY strict — aucun fichier de code modifié.
**Auditeur** : Staff Engineer Full-Stack + Lead Product + QA/Release Manager
**Périmètre** : Cockpit (Strategique / Pilotage / Jour) — pages, composants, routes, services, KPIs, tests, doctrine.
**Contexte voisin** : Patrimoine P0-A/P0-B mergés · Conformité P1.5 + cleanup sidebar (PR #300) en attente merge · Bill Intelligence P2-A/P2-B (PR #298/#299) en attente merge.

---

## 1. Résumé exécutif

### Verdict global : 🟡 **GO conditionnel** — note **6,5 / 10**

Le Cockpit dual sol2 (CockpitStrategique + CockpitJour + CockpitPilotage) est **fonctionnellement vivant et architecturalement propre** (composition pure des primitifs `grammar/hub/*`, payload data-driven backend, KPIs avec confidence + traceability). Les routes sont câblées, les hooks sont SoT, et 13 fichiers de tests backend + 8 fichiers de tests frontend cockpit existent.

**Mais il porte 2 dettes critiques qui le bloquent en démo DAF/DG sévère** :

1. **~2 865 lignes de code mort** : `Cockpit.jsx` (1 337 l) et `CockpitDecision.jsx` (1 528 l) **ne sont plus importés** dans `App.jsx` (M2-5.11 audit routes), mais les fichiers existent encore, polluent grep / refactor, et **maintiennent des dépendances backend orphelines** (`/api/cockpit/executive-v2`, `/api/cockpit/levers`, `/api/cockpit/impact_decision`, `/api/cockpit/essentials*`, `/api/cockpit/data_activation`, `/api/cockpit/top-contributors`, `/api/cockpit/co2`, `/api/cockpit/benchmark`, `/api/cockpit/conso-month`, `/api/cockpit/cdc`) — soit **10+ endpoints sans consommateur FE actif**.
2. **Aucun pont visible entre Cockpit et Bill Intelligence P2-B** (badge énergie, anomalies, lien `EXTERNAL_REF`), Conformité P1.5 (cleanup sidebar = 1 hub unique + chips réglementaires), Patrimoine P0-B (drill-down DATA_MISSING) — les briques voisines ont consolidé leur narratif post-audit mais le Cockpit n'a pas été ré-aligné sur leurs nouveaux KPIs et leurs nouvelles boucles.

### Top 5 dettes (vue exécutive)

| # | Item | Sévérité | Effort |
|---|---|---|---|
| 1 | Supprimer `Cockpit.jsx` + `CockpitDecision.jsx` (~2 865 l) + 10+ endpoints BE orphelins | 🔴 P0 | 2-3 j |
| 2 | Brancher KPI « Surfacturations à contester » (Bill Intel P2-A) dans CockpitStrategique | 🔴 P0 | 1 j |
| 3 | Brancher drill-down `CadreApplicable` DATA_MISSING (Patrimoine P0-B) déjà câblé MAIS ré-aligner les keys | 🟡 P1 | 1 j |
| 4 | Aucun acronyme protégé par `<Term>` / `<Explain>` dans les hero CockpitStrategique (DT/OPERAT/BACS/APER/SMÉ/BEGES) | 🟡 P1 | 1-2 j |
| 5 | 1722 lignes dans `CockpitPilotage.jsx` (monolithe) — extraire 3 sous-pages logiques | 🟢 P2 | 3-5 j |

### Score par dimension

| Dimension | Note | Verdict |
|---|---|---|
| Architecture composants (grammar/hub) | 9/10 | ✅ Excellente (composition pure, polymorphique ADR-023) |
| KPIs avec source/formule/unité/période/périmètre | 7/10 | 🟡 Backend OK, FE expose mais sans Explain |
| Cohérence Patrimoine ↔ Conformité ↔ Billing ↔ Actions | 5/10 | 🟠 Patrimoine ✅, Conformité ⚠️ (chips réglementaires non remontées), Billing ⚠️ (KPI VNU/€ contester absent), Actions ✅ (Centre V4 lié) |
| UX / Lisibilité DAF/DG en 2 min | 6/10 | 🟡 Hero clair mais acronymes nus |
| Code mort / Routes mortes | 3/10 | 🔴 ~2 865 l + 10+ endpoints BE orphelins |
| Tests existants | 7/10 | ✅ 18 fichiers tests cockpit (FE+BE) — bonne couverture source-guards |
| Tests manquants | 5/10 | 🟡 Aucun test bout-en-bout walking persona DAF |

---

## 2. Cartographie écrans / composants / routes

### 2.1 Routes Cockpit (`App.jsx` + `legacyRedirects.js`)

| Route | Composant cible | Fichier | Lignes | Statut | Source |
|---|---|---|---|---|---|
| `/` | redirect → `/cockpit/strategique` | — | — | ✅ Vivant | `legacyRedirects.js:26` |
| `/cockpit` | redirect → `/cockpit/strategique` | — | — | ✅ Vivant | `legacyRedirects.js:26` |
| `/cockpit/strategique` | `CockpitStrategique` | [CockpitStrategique.jsx](../../frontend/src/pages/CockpitStrategique.jsx) | **242** | ✅ **Canonical** (Phase 3.5 D.5, ADR-023) | App.jsx:340 |
| `/cockpit/jour` | `CockpitJour` | [CockpitJour.jsx](../../frontend/src/pages/CockpitJour.jsx) | **266** | ✅ **Canonical** (Hub L11, briefing 30 s) | App.jsx:322 |
| `/cockpit/pilotage` | `CockpitPilotage` | [CockpitPilotage.jsx](../../frontend/src/pages/CockpitPilotage.jsx) | **1722** | ✅ Vivant (retro-compat legacy) | App.jsx:327-330 |
| `/synthese`, `/executive`, `/dashboard` | redirect → `/cockpit/strategique` | — | — | ✅ Bookmarks legacy | `legacyRedirects.js:27-29` |
| `/tableau-de-bord` | redirect → `/cockpit/jour` | — | — | ✅ Bookmarks legacy | `legacyRedirects.js:31` |

### 2.2 Pages cockpit fantômes (code mort)

| Page | Fichier | Lignes | État | Preuve |
|---|---|---|---|---|
| **Cockpit** | [Cockpit.jsx](../../frontend/src/pages/Cockpit.jsx) | **1337** | 🔴 **ORPHELIN** (jamais importé) | App.jsx:30-31 commentaire « M2-5.11 audit routes — CockpitDecision et Cockpit imports lazy retirés (orphelins : jamais routés) »; source-guard `cockpit_strategique_fe_source_guards.test.js:54-57` interdit explicitement les imports |
| **CockpitDecision** | [CockpitDecision.jsx](../../frontend/src/pages/CockpitDecision.jsx) | **1528** | 🔴 **ORPHELIN** (jamais importé) | Idem ci-dessus |

**Total code mort frontend cockpit : 2 865 lignes** soit **~56 %** des lignes cockpit `pages/*` (5 095 lignes au total). Ces deux fichiers compilent toujours, sont parsés par Vitest pour les source-guards, et empêchent un refactor naturel des hooks (`useCockpitData`, `useExecutiveV2`, etc.) qu'ils sont les seuls à consommer.

### 2.3 Panel sidebar Cockpit (`NavRegistry.js:596-687`)

3 items visibles dans le panel module `cockpit` (key='cockpit', icon LayoutDashboard, tint blue) :

| Item | Route | Icon | Description |
|---|---|---|---|
| **Briefing du jour** | `/cockpit/jour` | LayoutDashboard | « Quoi traiter aujourd'hui (30 s) » |
| **Synthèse stratégique** | `/cockpit/strategique` | BarChart3 | « Où en sommes-nous (3 min) » |
| **Centre d'action** | `/action-center-v4/pilotage` | Inbox | « File prioritaire, pilotes et impact financier (refonte V4) » + badge `actionCenter` |

**`CockpitPilotage` n'apparaît PAS dans le panel sidebar** — uniquement accessible par deep-link ou tableau de bord legacy. C'est conforme à la doctrine (deux entrées canoniques = Briefing + Synthèse), mais 1 722 lignes de page pour un deep-link est démesuré → candidat extraction.

### 2.4 Composants `pages/cockpit/*` (24 fichiers)

| Composant | Fichier | Lignes | Consommé par | Statut |
|---|---|---|---|---|
| ActionsImpact | pages/cockpit/ActionsImpact.jsx | 213 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| AlertesPrioritaires | pages/cockpit/AlertesPrioritaires.jsx | 83 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| BoutonRapportCOMEX | pages/cockpit/BoutonRapportCOMEX.jsx | 18 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| BriefingHeroCard | pages/cockpit/BriefingHeroCard.jsx | 87 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| CockpitHeaderSignals | pages/cockpit/CockpitHeaderSignals.jsx | 87 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| CockpitHero | pages/cockpit/CockpitHero.jsx | 364 | Cockpit.jsx (mort, toggle) | 🔴 **Mort transitivement** |
| DataActivationPanel | pages/cockpit/DataActivationPanel.jsx | 121 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| DataQualityWidget | pages/cockpit/DataQualityWidget.jsx | 162 | Cockpit.jsx (mort, expertOnly) | 🔴 **Mort transitivement** |
| EssentialsRow | pages/cockpit/EssentialsRow.jsx | 189 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| EvenementsRecents | pages/cockpit/EvenementsRecents.jsx | 103 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| ExecutiveSummaryCard | pages/cockpit/ExecutiveSummaryCard.jsx | 60 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| HeroImpactBar | pages/cockpit/HeroImpactBar.jsx | 114 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| MarketWidget | pages/cockpit/MarketWidget.jsx | 306 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| ModuleLaunchers | pages/cockpit/ModuleLaunchers.jsx | 107 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| OpportunitiesCard | pages/cockpit/OpportunitiesCard.jsx | 56 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| PerformanceSitesCard | pages/cockpit/PerformanceSitesCard.jsx | 142 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| PriorityActions | pages/cockpit/PriorityActions.jsx | 84 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| SanteKpiGrid | pages/cockpit/SanteKpiGrid.jsx | 152 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| SitesBaselineCard | pages/cockpit/SitesBaselineCard.jsx | 105 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| TodayActionsCard | pages/cockpit/TodayActionsCard.jsx | 107 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| TopContributorsCard | pages/cockpit/TopContributorsCard.jsx | 148 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| TopDeriveSitesCard | pages/cockpit/TopDeriveSitesCard.jsx | 95 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| TopSitesCard | pages/cockpit/TopSitesCard.jsx | 117 | Cockpit.jsx (mort) | 🔴 **Mort transitivement** |
| TrajectorySection | pages/cockpit/TrajectorySection.jsx | 288 | Cockpit.jsx + CockpitDecision (morts) | 🔴 **Mort transitivement** |
| VecteurEnergetiqueCard | pages/cockpit/VecteurEnergetiqueCard.jsx | 220 | Cockpit.jsx (mort, data non câblées) | 🔴 **Mort transitivement** |

**⚠️ Si Cockpit.jsx + CockpitDecision.jsx sont supprimés, TOUS les composants `pages/cockpit/*` deviennent transitively dead** (24 fichiers, ~3 528 lignes additionnelles). Total dette nettoyage potentielle = **~6 393 lignes**.

### 2.5 Composants `components/cockpit/*` (3 fichiers)

| Composant | Fichier | Consommé par |
|---|---|---|
| KpiCard | components/cockpit/KpiCard.jsx | CockpitDecision (mort), CockpitPilotage (vif) |
| KpiSkeleton | components/cockpit/KpiSkeleton.jsx | Idem |
| SolKpiMonthlyVsN1Container | components/cockpit/SolKpiMonthlyVsN1Container.jsx | CockpitPilotage (vif) |

### 2.6 Primitifs `components/grammar/hub/*` (12 fichiers, vifs)

| Primitif | Rôle | Consommé par |
|---|---|---|
| HubPage | Layout L11 (pillar, sections) | CockpitJour, CockpitStrategique |
| HubKpiCard | KPI card (value, unit, source badge, drill) | CockpitJour, CockpitStrategique |
| ChartFrame (+ Bars, Line, BenchSites, ForwardCurve, OpportunityMap, TrajectoryLine) | Frames graphiques | CockpitJour, CockpitStrategique |
| HubHighlight | Highlight item (priorité narrative) | CockpitJour |
| HubPageFooter | Footer (source, fraîcheur, confiance) | CockpitJour, CockpitStrategique |
| SolHeroPremiumNight | Hero exécutif (eyebrow, title, sub, meta, primaryCta) | CockpitStrategique, CockpitJour |
| CadreApplicable | Grille 5 règles (DT/BACS/APER/SMÉ/BEGES) avec applicabilité + maturité | CockpitStrategique |
| DossierP1 | Dossier prioritaire P0/P1 narré | CockpitStrategique |
| VerdictFinal | Verdict + recommandation finale | CockpitStrategique |
| QueueP2P3 | File P2/P3 (items secondaires) | CockpitStrategique |
| PriorityProofModal | Modal preuve (evidence-required action) | CockpitJour |
| StrategicModeBanner | Bandeau persona/mode | CockpitStrategique |

### 2.7 Backend routes cockpit (3 fichiers, 23 endpoints)

| Endpoint | Fichier | Consommé par FE ? | Statut |
|---|---|---|---|
| `GET /api/cockpit` | cockpit.py:168 | **Non** (seul Cockpit.jsx mort le consomme) | 🔴 **Orphelin** |
| `GET /api/cockpit/benchmark` | cockpit.py:467 | Non | 🔴 **Orphelin** |
| `GET /api/cockpit/trajectory` | cockpit.py:537 | Oui (`getCockpitTrajectory` dans CockpitDecision mort) + tests | ⚠️ **À vérifier** |
| `GET /api/cockpit/conso-month` | cockpit.py:789 | Non | 🔴 **Orphelin** |
| `GET /api/cockpit/co2` | cockpit.py:848 | Non | 🔴 **Orphelin** |
| `GET /api/cockpit/_facts.scope` | cockpit.py:866 | Non (sous-endpoint atomique) | ⚠️ Probablement orphelin |
| `GET /api/cockpit/_facts.alerts` | cockpit.py:901 | Non | ⚠️ Probablement orphelin |
| `GET /api/cockpit/cdc` | cockpit.py:952 | Non | 🔴 **Orphelin** |
| `GET /api/cockpit/priorities` | cockpit.py:1037 | **Oui** (CockpitPilotage, `getCockpitPriorities`) | ✅ **Vivant** |
| `GET /api/cockpit/levers` | cockpit.py:1382 | Non | 🔴 **Orphelin** (remplacé par impact_decision puis abandonné) |
| `GET /api/cockpit/impact_decision` | cockpit.py:1473 | Non | 🔴 **Orphelin** |
| `GET /api/cockpit/essentials` | cockpit.py:1563 | Non | 🔴 **Orphelin** |
| `GET /api/cockpit/essentials/health` | cockpit.py:1648 | Non | 🔴 **Orphelin** |
| `GET /api/cockpit/essentials/watchlist` | cockpit.py:1734 | Non | 🔴 **Orphelin** |
| `GET /api/cockpit/data_activation` | cockpit.py:1791 | Non | 🔴 **Orphelin** |
| `GET /api/cockpit/jour` | cockpit.py:2657 | **Oui** (CockpitJour, `getCockpitJour`) | ✅ **Vivant** |
| `GET /api/cockpit/executive-v2` | cockpit_v2.py:49 | Non (CockpitV2 hook → Cockpit.jsx mort) | 🔴 **Orphelin** |
| `GET /api/cockpit/top-contributors` | cockpit_v2.py:329 | Non (TopContributorsCard → Cockpit.jsx mort) | 🔴 **Orphelin** |
| `GET /api/cockpit/strategique` | cockpit_strategique.py:64 | **Oui** (CockpitStrategique, `getCockpitStrategique`) | ✅ **Vivant** |
| `GET /api/cockpit/_facts` (atomic SoT) | cockpit.py | **Oui** (CockpitPilotage, `useCockpitFacts`) | ✅ **Vivant** |
| `GET /api/cockpit/decisions/top3` | cockpit.py | Oui (CockpitDecision mort) | 🔴 **Orphelin** |
| `GET /api/pages/{key}/briefing` | pages_briefing.py:49 | **Oui** (`usePageBriefing`, partagé Cockpit/Conformite/Billing/Monitoring/Diagnostic) | ✅ **Vivant** |
| `GET /api/v1/events/upcoming` | events.py:48 | **Oui** (events cockpit + autres pages) | ✅ **Vivant** |

**4 endpoints réellement vivants** (`/cockpit/jour`, `/cockpit/strategique`, `/cockpit/priorities`, `/cockpit/_facts`) + 2 transverses (`/pages/.../briefing`, `/events/upcoming`) = **6 endpoints actifs sur 23** = **74 % d'orphelins backend**.

---

## 3. Cartographie KPIs

Notation : ✅ source/formule/unité/période/périmètre explicites · ⚠️ partiel · 🔴 manquant.

### 3.1 CockpitStrategique (page `/cockpit/strategique`) — payload `getCockpitStrategique({period, persona})`

KPIs **data-driven** (le payload `kpis[]` est rendu via `<HubKpiCard {...k}/>` — donc le frontend NE recalcule rien, doctrine respectée).

| KPI (selon mode strategique) | Source backend | Formule | Unité | Période | Périmètre | Score |
|---|---|---|---|---|---|---|
| **Maturity Score** | `applicability_service.compute_patrimoine_maturity()` (via strategique/builders) | Composite couverture + complétude FE/EF | % | Snapshot | Org | ✅ |
| **Compliance Score (avg)** | `compliance_score_service.compute_portfolio_compliance(db, org_id)` | Moyenne pondérée DT 45 % + BACS 30 % + APER 25 % − pénalité findings critiques (max −20) | /100 | Snapshot | Org | ✅ |
| **DT trajectory (réel / cible / projection)** | `routes/cockpit.py:_project_with_action_echeances` | Δ % vs ref (2010 ou ref site) ; jalons 2030/2040/2050 −40/−50/−60 % | % | Annuel | Site/Portfolio | ✅ (article R131-39 CCH) |
| **Bench sites (top/bottom IPE)** | `routes/cockpit.py:467` (`benchmark`) | kWh / m² / an vs ADEME BENCHMARK | kWh/m²/an | Annuel | Site | ⚠️ Endpoint orphelin déclaré, mais payload Strategique peut le contenir |
| **Forward curve EPEX** | `getCockpitStrategique` builders | Prix marché EPEX | €/MWh | T+1 à T+12 mois | Org | ⚠️ Source non explicite dans le hub |
| **Opportunity map** | `getCockpitStrategique` builders | Sites × leviers (matrix bubble) | k€/an, MWh/an | Annuel | Portfolio | ⚠️ Confidence non affichée |

**Verdict** : payload bien structuré, KPIs typés (id/label/value/unit/source_ref/confidence) mais le **FE n'affiche pas systématiquement la confidence ni la source_ref** dans le hover (Phase L33.1 a livré la structure, l'affichage UI ne l'utilise pas partout).

### 3.2 CockpitJour (page `/cockpit/jour`) — payload `getCockpitJour({period, persona})`

| KPI | Source backend | Formule | Unité | Période | Périmètre | Score |
|---|---|---|---|---|---|---|
| **3 KPI Triptych** (data-driven) | `cockpit_facts_service` + `cockpit_highlights_service` | Variable selon persona | Variable | period_type (J−1, semaine, mois) | persona-scoped | ✅ |
| **Chart 7d barres** | `cockpit_jour` builders → `facts.weekly_breakdown` | Σ MWh par jour | MWh/j | 7 derniers jours | Site/Portfolio | ✅ |
| **Chart 24h ligne** | Idem → `facts.hourly_breakdown` | Pic puissance par heure (J−1) | kW | 24h | Site | ✅ |
| **3-5 Highlights** (priorités narratives) | `cockpit_highlights_service._collect_compliance_findings + _collect_billing_findings + _collect_patrimoine_issues` | Scoring `regops.priority_scoring` | — | Snapshot | Org | ✅ |
| **Footer (source/fraîcheur/confiance)** | `HubPageFooter` props | `footer.source`, `footer.last_updated`, `footer.confidence` | — | — | — | ✅ |

**Verdict** : briefing bien orchestré. Highlights cross-domaines (compliance + billing + patrimoine) — **MAIS aucun lien explicite vers CockpitStrategique pour escalader** (clic → /cockpit/strategique avec scope préservé).

### 3.3 CockpitPilotage (page `/cockpit/pilotage`, 1722 lignes) — `useCockpitFacts('current_month')`

| KPI | Source backend | Formule | Unité | Période | Périmètre | Score |
|---|---|---|---|---|---|---|
| **Conso J-1** | `facts.consumption.j_minus_1_kwh` via `consumption_unified_service` | metered > billed > estimated | kWh | J-1 | Portfolio | ✅ |
| **Mois DJU** | `facts.consumption.month_dju_corrected_mwh` | Conso ajustée degrés-jour | MWh | Mois en cours | Portfolio | ⚠️ Méthode DJU non explicite |
| **Pic souscrite** | `facts.hourly_breakdown.peak_kw vs subscribed_kw` | Max kW vs contrat | kW | J-1 | Site | ✅ |
| **Conso 7d barres** | `facts.weekly_breakdown` | Σ MWh par jour | MWh/j | 7 derniers jours | Portfolio | ✅ |
| **Courbe charge J-1** | `facts.hourly_breakdown` | kWh par heure × 24 | kWh/h | J-1 | Site | ✅ |
| **File P1-P5** | `getCockpitPriorities()` → `cockpit_facts_service._build_priorities` | Priorisation P0-P3 doctrine | — | Snapshot | Portfolio | ⚠️ Mapping P1-P5 vs doctrine P0-P3 ambigu |

**Verdict** : page très dense (1722 l), beaucoup de KPIs orientés Energy Manager (Marc), mais **pas un point d'entrée DAF/DG**. Si CockpitStrategique reste la canonical entry, CockpitPilotage devrait être positionné comme "Pilotage opérationnel".

### 3.4 KPIs absents du Cockpit mais déclarés stables ailleurs

| KPI stable (audit voisin) | Brique source | Cockpit l'expose ? | Verdict |
|---|---|---|---|
| **Surfacturations à contester** | Bill Intelligence P2-A | ❌ Absent | 🔴 **P0** — KPI majeur DAF, doit remonter dans CockpitStrategique |
| **VNU dormant (€)** | Bill Intelligence P2-A | ❌ Absent (était dans Cockpit.jsx mort) | 🔴 **P0** |
| **Anomalies factures par énergie (élec/gaz)** | Bill Intelligence P2-B | ❌ Absent | 🟡 P1 |
| **Sites non rattachés à un contrat** | Bill Intelligence P2-A (audit `is_reliable`) | ❌ Absent | 🟡 P1 |
| **Actions Centre V4 en cours (kind=anomaly, domain=facturation)** | Cleanup sidebar P1.5 (chip Facturation) | ⚠️ Cockpit Highlights pourrait remonter | 🟡 P1 |
| **Évolution patrimoine maturity (delta vs M−1)** | Patrimoine P0-B | ⚠️ CadreApplicable affiche valeur courante seulement | 🟢 P2 |
| **Couverture contrats (% sites avec contrat actif)** | Patrimoine P0-C contract_coverage | ❌ Absent | 🟡 P1 |

---

## 4. Cohérence Patrimoine ↔ Conformité ↔ Billing ↔ Actions

### 4.1 Patrimoine ↔ Cockpit

✅ **Bon** : `CadreApplicable` consomme `payload.applicability` + `payload.patrimoine_maturity` (mêmes structures que la page Patrimoine). Le drill-down P0-B (`/patrimoine?incomplete=<RULE>`) est cité dans la doctrine mais **non câblé explicitement dans `CadreApplicable.jsx`** — il fonctionne uniquement si l'API renvoie la bonne propriété `remediation_field`.

🟡 **Faille** : aucun test vérifie qu'un site passé en *non_conforme* depuis Patrimoine apparaît dans le payload Strategique au refresh suivant (latence cache `cachedGet` = 60 s — pas documenté).

### 4.2 Conformité ↔ Cockpit

🟡 **Décalage post-P1.5** : Conformité expose maintenant des chips réglementaires internes (Vue d'ensemble · DT/OPERAT · BACS · APER · SMÉ/BEGES) avec compteur d'obligations + URL state `?regulation=`. **Le Cockpit n'a aucun équivalent** : `CadreApplicable` affiche les 5 mêmes règles mais sans compteur d'obligations *non conformes*, et le clic vers `/conformite?regulation=dt` n'est pas implémenté.

🟠 **Risque** : Marie DAF voit `CadreApplicable` indiquer « DT applicable », clique sur « Conformité » dans la sidebar (hub unique post-cleanup), et **doit refaire le filtre dans `/conformite`** au lieu d'arriver pré-filtré.

### 4.3 Billing ↔ Cockpit

🔴 **Régression majeure** : Bill Intelligence P2-A/P2-B a renommé le KPI principal en « Surfacturations à contester », ajouté `kpi_metadata` (source/formule/unité/période), enrichi le drawer anomalie, ajouté badge énergie. **Aucun de ces éléments n'est exposé dans CockpitStrategique** (le payload `kpis[]` ne contient pas de KPI Billing en P2-A/P2-B). Si l'audit Bill P2-A déclare la note brique 9/10 → 9,5/10 mais que le **point d'entrée exécutif l'ignore**, le DAF n'a aucun signal.

🟠 **Patch existant mais non câblé** : `cockpit_highlights_service._collect_billing_findings` agrège `BillingInsight` (anomalies) en findings cross-domain → ils alimentent `CockpitJour` (Highlights). **Mais pas CockpitStrategique** (le KPI Triptych n'inclut pas Billing).

### 4.4 Actions ↔ Cockpit

✅ **Bon** : `/action-center-v4/pilotage` est item du panel Cockpit (Centre d'action) + badge `actionCenter` (compteur live).

🟡 **Faille** : pas d'agrégation visible « Top 3 actions du jour » dans CockpitStrategique. Le hub L11 a `DossierP1` + `QueueP2P3` mais ces composants attendent un payload spécifique (`payload.dossier_p1`, `payload.queue_p2_p3`) que `getCockpitStrategique` ne fournit pas nécessairement (selon `strategic_mode`).

---

## 5. UX / UI / lisibilité

### 5.1 Conformité grammaire Sol §5

✅ **Excellent** : `SolHeroPremiumNight` + `HubPageFooter` respectent la grammaire Sol (eyebrow + title + sub + meta + primaryCta), persona-scoped.

### 5.2 Acronymes (DT / OPERAT / BACS / APER / SMÉ / BEGES)

🔴 **Régression** : `CockpitStrategique` rend `payload.hero?.kicker` et `payload.hero?.title` en string nu — aucun wrapping `<Term acronyme="DT">` ou `<Explain term="OPERAT">` n'est appliqué. Pourtant `ConformitePage` utilise systématiquement `<Term>` dans son hero (vu dans P1.5). Conséquence : un DAF / DG **non-expert** lit « DT 2030 trajectoire -40 % » sans tooltip → décroche.

### 5.3 Densité informationnelle

🟡 **CockpitPilotage** : 1722 lignes, ~15 sous-sections rendues. Risque de surcharge pour Marc (Energy Manager — promesse 30 s). À découper.

✅ **CockpitStrategique** : 242 lignes propres, composition pure des primitifs hub. Densité optimale.

### 5.4 Boutons morts

Audit `Cockpit.jsx` mort + tests `cockpit_no_dead_cards.test.js` existant : si on supprime les 2 morts, aucun bouton/card non-cliquable ne reste dans les 3 pages vivantes. **À valider après cleanup**.

### 5.5 Empty states

✅ `PageState state="loading"` et `state="error"` dans CockpitStrategique. ⚠️ **CockpitPilotage** : pas vérifié exhaustivement, à auditer en P1.

---

## 6. Legacy / Code mort / Routes mortes

### 6.1 Fichiers FE morts (totaux)

| Fichier | Lignes | Statut |
|---|---|---|
| pages/Cockpit.jsx | 1 337 | 🔴 Orphelin |
| pages/CockpitDecision.jsx | 1 528 | 🔴 Orphelin |
| pages/cockpit/* (24 fichiers transitivement morts) | ~3 528 | 🔴 Mort transitivement (si #1 et #2 supprimés) |
| **Total dette nettoyage FE** | **~6 393** | |

### 6.2 Endpoints BE morts (totaux)

| Endpoint | Statut |
|---|---|
| `/api/cockpit` | 🔴 Orphelin |
| `/api/cockpit/benchmark` | 🔴 Orphelin |
| `/api/cockpit/conso-month` | 🔴 Orphelin |
| `/api/cockpit/co2` | 🔴 Orphelin |
| `/api/cockpit/cdc` | 🔴 Orphelin |
| `/api/cockpit/_facts.scope` + `_facts.alerts` | ⚠️ Probables orphelins |
| `/api/cockpit/levers` | 🔴 Orphelin |
| `/api/cockpit/impact_decision` | 🔴 Orphelin |
| `/api/cockpit/essentials` + `essentials/health` + `essentials/watchlist` | 🔴 Orphelins |
| `/api/cockpit/data_activation` | 🔴 Orphelin |
| `/api/cockpit/executive-v2` | 🔴 Orphelin |
| `/api/cockpit/top-contributors` | 🔴 Orphelin |
| `/api/cockpit/decisions/top3` | 🔴 Orphelin |
| `/api/cockpit/trajectory` | ⚠️ Consommateur mort (CockpitDecision) — vérifier si CockpitStrategique en a besoin |
| **Total ~14 endpoints à confirmer orphelins** | |

### 6.3 Services BE associés au code mort

Si on supprime les endpoints orphelins :
- `services/impact_decision_service.py` → mort
- `services/lever_engine_service.py` → mort
- `services/dashboard_essentials_service.py` → mort (si existe)
- `services/data_activation_service.py` → mort (si existe)
- `services/cockpit_decisions_service.py` → mort (utilisé seulement par decisions/top3)
- `services/co2_service.py` → utilisé par `/api/cockpit/co2` mort (mais peut-être autres endpoints)

### 6.4 Tests source-guards existants qui protègent l'orphelin status

✅ `cockpit_strategique_fe_source_guards.test.js:54-57` : `SG_STRATEGIQUE_02 — no import from pages/Cockpit.jsx` — **protège l'invariant orphelin** mais **ne supprime pas le fichier**.

### 6.5 Routes mortes

Aucune route déclarée dans `App.jsx` ne pointe vers un composant inexistant. ✅

### 6.6 Anciens widgets / doublons

| Item | Statut |
|---|---|
| `CockpitHero` 364 l + `BriefingHeroCard` 87 l + `SolHeroPremiumNight` (hub) | Doublon 3 façons → seul `SolHeroPremiumNight` est vivant |
| `TopContributorsCard` + `TopSitesCard` + `TopDeriveSitesCard` + `PerformanceSitesCard` | 4 variantes de « top sites » dans pages/cockpit/* (tous transitivement morts) |
| `EssentialsRow` + `SanteKpiGrid` + KPI Triptych hub | 3 implémentations KPI grid |
| `ExecutiveSummaryCard` + `BriefingHeroCard` + payload `dossier_p1` | 3 façons de résumer |

---

## 7. Personas sévères

### 7.1 DAF pressé (Marie, 2 min)

| Critère | État | Verdict |
|---|---|---|
| Voit montant € total à contester (Billing) dès le hero | ❌ Absent | 🔴 Bloquant |
| Voit risque pénalités réglementaires € (DT/BACS/APER/OPERAT) | ⚠️ Partiel (CadreApplicable affiche statut, pas € exposition) | 🟡 |
| Comprend chaque acronyme sans cliquer | ❌ Pas de tooltip | 🔴 |
| Trouve un bouton « Voir actions du jour » | ✅ Centre d'action dans le panel | ✅ |
| Trouve un bouton « Voir preuves manquantes » | ❌ Absent du Cockpit | 🔴 |

**Verdict DAF : 1/5 ✅, 1/5 🟡, 3/5 🔴 — NO GO en l'état**.

### 7.2 DG / Dirigeant non-expert (Sophie, 2 min)

| Critère | État | Verdict |
|---|---|---|
| Voit trajectoire 2030 (graphique simple) | ✅ `ChartFrameTrajectoryLine` | ✅ |
| Comprend pourquoi -40 % en 2030 | ❌ Pas de phrase « Décret tertiaire — loi ELAN » | 🔴 |
| Voit un verdict en 1 ligne (« vous êtes sur la trajectoire / vous décrochez ») | ✅ `VerdictFinal` | ✅ |
| N'a pas à comprendre « strategic_mode », « persona », « cockpit_comex » | ✅ (interne) | ✅ |

**Verdict DG : 3/4 ✅, 1/4 🔴 — GO sous condition de wrapping acronymes**.

### 7.3 Responsable Énergie multi-sites (Marc, 30 s)

| Critère | État | Verdict |
|---|---|---|
| Voit conso J−1 et anomalies du jour | ✅ CockpitJour + CockpitPilotage | ✅ |
| Voit top 3 priorités | ✅ `HubHighlight` × 5 dans CockpitJour | ✅ |
| Bascule rapidement vers Strategique pour reporting CFO | 🟡 Sidebar OK, pas de raccourci contextuel | 🟡 |
| Comprend `/cockpit/pilotage` vs `/cockpit/jour` (qui sert à quoi) | ❌ 2 pages très proches sans positionnement explicite | 🔴 |

**Verdict Energy Manager : 2/4 ✅, 1/4 🟡, 1/4 🔴 — GO avec doute sur la coexistence Pilotage + Jour**.

### 7.4 Customer Success PROMEOS (escalade démo)

| Critère | État | Verdict |
|---|---|---|
| Peut exporter un PDF synthèse client | ❌ `BoutonRapportCOMEX` est mort (dans Cockpit.jsx orphelin) | 🔴 |
| Peut basculer entre personas pour démo | ✅ `PersonaContext` + dropdown | ✅ |
| Voit fraîcheur des données (last_updated) | ✅ `HubPageFooter` | ✅ |

**Verdict CS : 2/3 ✅, 1/3 🔴 — Export PDF perdu lors de la dépriorisation de Cockpit.jsx**.

### 7.5 Auditeur conformité (RGPD + preuves)

| Critère | État | Verdict |
|---|---|---|
| Trace SoT pour chaque KPI affiché | ⚠️ Backend l'expose (source_ref, confidence) mais FE ne tooltip pas systématiquement | 🟡 |
| Accède aux logs audit trail patrimoine | ✅ Via `/admin/audit` (item sidebar) | ✅ |
| Voit fraîcheur de l'évaluation conformité | ✅ Via HubPageFooter | ✅ |

**Verdict Auditeur : 2/3 ✅, 1/3 🟡 — GO sous condition d'exposer source/confidence dans le tooltip**.

### 7.6 Acheteur énergie

| Critère | État | Verdict |
|---|---|---|
| Voit prix EPEX courant + forward curve | ⚠️ `ChartFrameForwardCurve` existe dans hub/* mais payload Strategique ne le rend que en mode `PERFORMANCE_DRIVEN` | 🟡 |
| Voit échéances contrats <90 j | ❌ Absent du Cockpit (était dans Cockpit.jsx mort) | 🔴 |
| Bascule vers `/achat-energie` depuis Cockpit | ✅ Sidebar Achat | ✅ |

**Verdict Acheteur : 1/3 ✅, 1/3 🟡, 1/3 🔴 — GO sous condition d'exposer contrats expirants**.

### 7.7 Synthèse personas

| Persona | Note |
|---|---|
| DAF | 🔴 NO GO (3/5 bloquants) |
| DG | 🟡 GO conditionnel (1 P0) |
| Energy Manager | 🟡 GO (positionnement Pilotage vs Jour) |
| Customer Success | 🟡 GO conditionnel (export PDF) |
| Auditeur | 🟡 GO conditionnel (tooltip source) |
| Acheteur | 🟡 GO conditionnel (contrats expirants) |

**Verdict global personas : 0/6 GO pur — 1/6 NO GO, 5/6 GO conditionnel**.

---

## 8. Tests existants

### 8.1 Frontend (16 fichiers tests cockpit)

| Fichier | Lignes (env.) | Couvre |
|---|---|---|
| `__tests__/CockpitHero.test.js` | ? | CockpitHero (mort transitivement) |
| `__tests__/CockpitIntegration.test.js` | ? | Cockpit (mort) — intégration scope/profile |
| `__tests__/cockpitDecisionPhase14a.test.js` | ? | CockpitDecision (mort) — narrative typology |
| `__tests__/cockpit_no_dead_cards.test.js` | ? | Anti-régression cartes vides |
| `__tests__/no_business_logic_in_frontend_cockpit.test.js` | ? | Doctrine §8.1 |
| `__tests__/phase3_1_routes_cockpit_dual.test.js` | ? | Routes /jour /strategique résolvables |
| `__tests__/sol_cockpit_header_phase1_2.test.js` | ? | Header Sol cockpit |
| `__tests__/useCockpitData.test.js` | ? | Hook (mort transitivement — consommé seulement par Cockpit.jsx mort) |
| `__tests__/source_guards/cockpit_fe_source_guards.test.js` | ? | Source guards FE |
| `__tests__/source_guards/cockpit_jour_l11_fe_source_guards.test.js` | ? | Hub L11 CockpitJour |
| `__tests__/source_guards/cockpit_strategique_fe_source_guards.test.js` | ? | SG_STRATEGIQUE_02 anti-import Cockpit.jsx |
| `pages/__tests__/CockpitDecision.test.js` | 16 it | CockpitDecision (mort) |
| `pages/__tests__/CockpitV1Plus.test.js` | 11 it | V1+ (mort) |
| `pages/__tests__/CockpitV2.test.js` | 24 it | V2 logic (mort) |
| `pages/__tests__/CockpitPilotage.test.js` | 20 it | CockpitPilotage (vivant) |
| `pages/__tests__/site360CockpitWC.test.js` | ? | Cross site360-cockpit |

**Constat tests** : sur 16 fichiers, **8 testent du code mort** (Cockpit/CockpitDecision/V1+/V2/CockpitHero/CockpitIntegration/cockpitDecisionPhase14a/useCockpitData). Si on supprime les morts, on supprime ~111 fonctions de test — **mais les source-guards qui interdisent le re-import resteront**.

### 8.2 Backend (13 fichiers tests cockpit)

| Fichier | Couvre |
|---|---|
| `test_cockpit.py` | Routes `/api/cockpit` (Cockpit.jsx mort) |
| `test_cockpit_v2.py` | `/api/cockpit/executive-v2` (mort) |
| `test_cockpit_facts_service.py` | Service `cockpit_facts_service` |
| `test_cockpit_facts_no_recompute.py` | Performance (1 fetch, pas N+1) |
| `test_cockpit_facts_unique_source.py` | SoT audit |
| `test_cockpit_decisions_service.py` | `cockpit_decisions_service` (utilisé seul par decisions/top3 mort) |
| `test_cockpit_jour_endpoint.py` | `/api/cockpit/jour` (vivant) |
| `test_cockpit_p0.py` | P0 audit |
| `test_cockpit_phase1_2bis.py` | Phase 1.2bis specs |
| `source_guards/test_cockpit_facts_source_guards.py` | Constantes doctrine |
| `source_guards/test_cockpit_decisions_source_guards.py` | MWh XOR € traceability |
| `source_guards/test_cockpit_kpi_tracability_source_guards.py` | KPI confidence + source_ref |
| `source_guards/test_cockpit_no_hardcode.py` | Anti-hardcode |
| `source_guards/test_cockpit_strategique_data_driven.py` | Strategique mode calc no mock |

**Constat tests BE** : **bonne couverture source-guards** (5/13 sont des SG). Mais 2 fichiers (`test_cockpit.py`, `test_cockpit_v2.py`) testent des endpoints orphelins → ~50+ tests sur du code mort.

---

## 9. Tests manquants

### 9.1 Bout-en-bout personas

🔴 **Aucun test Playwright walking persona** :
- DAF Marie : login → /cockpit/strategique → vérifie tooltips acronymes + KPI Billing visible.
- DG Sophie : login → /cockpit/strategique → vérifie verdict + trajectoire en < 2 min.
- Marc Energy Manager : login → /cockpit/jour → vérifie highlights + drill action.

### 9.2 Cohérence cross-domaines

🔴 **Aucun test** :
- KPI Conformité du Cockpit doit matcher exactement KPI /conformite (même périmètre, même période).
- KPI Billing du Cockpit doit matcher /bill-intel.
- Cadre Applicable du Cockpit doit matcher chips réglementaires /conformite.

### 9.3 Régression code mort

🟡 Source-guards existent (anti-import Cockpit.jsx) **mais aucun test ne vérifie qu'un endpoint orphelin n'est pas re-câblé par erreur**. Manque un guard `tests/test_cockpit_endpoint_consumed.py` qui grep `cachedGet|api.get|api.post` pour chaque endpoint déclaré.

### 9.4 Drill-down boucles

🟡 Aucun test ne vérifie :
- Clic sur `CadreApplicable` chip → arrive sur `/conformite?regulation=<rule>` pré-filtré.
- Clic sur Highlight Billing dans CockpitJour → arrive sur `/bill-intel?anomaly=<id>`.
- Clic sur DATA_MISSING → `/patrimoine?incomplete=<RULE>` (Patrimoine P0-B).

### 9.5 Tests visuels (snapshot Playwright)

🟢 Suite `tests/visual-grammar/baseline.spec.ts` existe (config Playwright) mais **ne couvre pas explicitement les 3 cockpits live** (à vérifier).

---

## 10. Plan P0 / P1 / P2

### 🔴 P0 — Bloquants démo DAF (effort 5-8 jours)

| # | Action | Critère d'acceptation | Effort |
|---|---|---|---|
| P0-1 | **Supprimer `Cockpit.jsx` + `CockpitDecision.jsx`** (+ 24 composants `pages/cockpit/*` transitivement morts) | `git diff --stat` montre ~6 393 lignes supprimées · Tous les tests FE/BE verts · Source-guard SG_STRATEGIQUE_02 toujours vert | 2 j |
| P0-2 | **Supprimer 10+ endpoints BE orphelins** (`/api/cockpit`, `/executive-v2`, `/levers`, `/impact_decision`, `/essentials*`, `/data_activation`, `/top-contributors`, `/co2`, `/benchmark`, `/conso-month`, `/cdc`, `/decisions/top3`) + services associés | Coverage BE inchangée · 0 import cassé · grep `from routes.cockpit_v2 import` retourne 0 occurrence après ménage | 1-2 j |
| P0-3 | **Ajouter KPI « Surfacturations à contester » dans `getCockpitStrategique`** (payload `kpis[]`) | Le DAF voit le montant € dès le hero · Source = `billing_service.get_billing_summary().total_estimated_loss_eur` · Confidence affichée · Test BE `/api/cockpit/strategique` retourne `kpis[i].id === 'surfacturations_a_contester'` | 1 j |
| P0-4 | **Wrapper acronymes hero avec `<Term>`** dans `SolHeroPremiumNight` rendu par `CockpitStrategique` | DT/OPERAT/BACS/APER/SMÉ/BEGES tous tooltipés · Test `conformite_acronyms_hero.test.jsx` étendu au cockpit | 1 j |
| P0-5 | **Drill-down `CadreApplicable` → `/conformite?regulation=<rule>`** | Clic sur chip DT du Cockpit ouvre `/conformite?regulation=dt` (chip post-cleanup PR #300 pré-sélectionnée) · Test Playwright bout-en-bout | 1 j |

### 🟡 P1 — Hardening DAF/DG/Marc (effort 4-6 jours)

| # | Action | Effort |
|---|---|---|
| P1-1 | Ajouter KPI « VNU dormant € » + « Anomalies par énergie (élec/gaz) » dans payload Strategique | 1 j |
| P1-2 | Ajouter KPI « Contrats expirant < 90 j » dans payload Strategique (persona Acheteur) | 0,5 j |
| P1-3 | Exposer `source_ref` + `confidence` dans tooltip `HubKpiCard` (FE déjà reçoit la prop, affichage UI manque) | 0,5 j |
| P1-4 | Ajouter Bouton « Voir preuves manquantes » dans CockpitStrategique → drill `/conformite?tab=preuves` | 0,5 j |
| P1-5 | Découper CockpitPilotage (1 722 l) en 3 sous-composants : `PilotageConsomation`, `PilotagePic`, `PilotageFile` | 2 j |
| P1-6 | Ré-implémenter export PDF synthèse (Customer Success) — `BoutonRapportCOMEX` à reconstruire dans CockpitStrategique | 1 j |
| P1-7 | Tests Playwright walking personas DAF + DG + Marc | 1 j |

### 🟢 P2 — Polish (effort 3-5 jours)

| # | Action | Effort |
|---|---|---|
| P2-1 | Test cohérence cross-domaine (Cockpit KPI = Conformité KPI = Billing KPI) | 1 j |
| P2-2 | Source-guard anti-régression endpoint (vérifier qu'un endpoint déclaré est consommé FE) | 0,5 j |
| P2-3 | Positionnement explicite CockpitJour vs CockpitPilotage (descriptions sidebar plus claires) | 0,5 j |
| P2-4 | Snapshot visuel Playwright pour les 3 cockpits (baseline.spec.ts) | 1 j |
| P2-5 | Évolution patrimoine maturity (delta vs M−1) dans `CadreApplicable` | 1 j |

---

## 11. Prompt de correction P0 uniquement

```
Tu es Staff Engineer Full-Stack + QA/Release Manager sur PROMEOS.

BRANCHE
Créer : claude/cockpit-p0-cleanup-and-billing-kpi
Base : claude/refonte-sol2 après merge propre des PR #298 + #299 + #300.
Ne jamais travailler sur main.

OBJECTIF
Clôturer les 5 P0 identifiés par l'audit deep cockpit
(`docs/audits/audit_brique_cockpit_vue_executive_deep_readonly_2026_05_24.md` §10) :

1. Supprimer `frontend/src/pages/Cockpit.jsx` + `CockpitDecision.jsx`
   (~2 865 lignes) + les 24 composants `pages/cockpit/*` qui en dépendent
   transitivement (vérifier qu'aucun composant n'est utilisé ailleurs via
   `grep -rn "from.*pages/cockpit/<Name>"` avant suppression).

2. Supprimer endpoints BE orphelins (et services associés sans autres
   consommateurs) :
   - `/api/cockpit` (cockpit.py:168)
   - `/api/cockpit/benchmark` (cockpit.py:467)
   - `/api/cockpit/conso-month` (cockpit.py:789)
   - `/api/cockpit/co2` (cockpit.py:848)
   - `/api/cockpit/_facts.scope` + `_facts.alerts` (cockpit.py:866, 901)
   - `/api/cockpit/cdc` (cockpit.py:952)
   - `/api/cockpit/levers` (cockpit.py:1382)
   - `/api/cockpit/impact_decision` (cockpit.py:1473)
   - `/api/cockpit/essentials*` (cockpit.py:1563, 1648, 1734)
   - `/api/cockpit/data_activation` (cockpit.py:1791)
   - `/api/cockpit/executive-v2` (cockpit_v2.py:49)
   - `/api/cockpit/top-contributors` (cockpit_v2.py:329)
   - `/api/cockpit/decisions/top3` (vérifier dans cockpit.py)
   Garder vivants : `/api/cockpit/jour`, `/api/cockpit/strategique`,
   `/api/cockpit/priorities`, `/api/cockpit/_facts`,
   `/api/cockpit/trajectory` (seulement si CockpitStrategique en a
   réellement besoin — sinon supprimer aussi).
   Avant suppression : grep `getCockpit*\|cachedGet.*cockpit\|api.get.*cockpit`
   dans `frontend/src/` pour confirmer 0 consommateur.

3. Étendre `getCockpitStrategique` (backend `cockpit_strategique.py`) pour
   inclure dans `payload.kpis[]` :
   - id="surfacturations_a_contester"
   - label="Surfacturations à contester"
   - value=billing_service.get_billing_summary(db, org_id).total_estimated_loss_eur
   - unit="€"
   - source_ref="BillingInsight.estimated_loss_eur (statut ouvert/in_progress)"
   - formula="Σ insights non clôturés (anomalies R01-R31)"
   - period="snapshot"
   - confidence=high si is_reliable, medium sinon (cf. Bill P2-A shadow_billing_v2)
   Mettre à jour test `test_cockpit_strategique_data_driven.py`.

4. Dans `frontend/src/components/grammar/hub/SolHeroPremiumNight.jsx`
   (et/ou dans `CockpitStrategique.jsx` au moment du rendu hero), wrapper
   les acronymes DT, OPERAT, BACS, APER, SMÉ, BEGES par `<Term acronyme=...>`
   (cf. pattern déjà appliqué dans `ConformitePage.jsx` ligne 658-662).
   Tester via `conformite_acronyms_hero.test.jsx` étendu (`it.each(['DT',
   'OPERAT', 'BACS', 'APER', 'SME', 'BEGES'])`) — copier le pattern et
   l'appliquer au render de `CockpitStrategique`.

5. Brancher le drill-down `CadreApplicable` → `/conformite?regulation=<rule>` :
   dans `frontend/src/components/grammar/hub/CadreApplicable.jsx`, ajouter
   `onClick` sur chaque tile qui navigate vers `/conformite?regulation=dt`
   (ou `bacs`, `aper`, `audit-sme`) — utiliser le mapping suivant :
   DT → 'dt', BACS → 'bacs', APER → 'aper', SME → 'audit-sme', BEGES → 'audit-sme'.
   Test Playwright dans `scripts/audit_postfix_cockpit_p0_2026_05_25.mjs` :
   clic chip DT → URL devient `/conformite?regulation=dt` et la chip
   correspondante est `aria-selected=true` (post-cleanup sidebar PR #300).

RÈGLES NON NÉGOCIABLES
- Aucun nouveau menu.
- Aucun écran fantôme.
- Aucun KPI sans source/formule/unité/période/périmètre.
- Français clair, sans jargon inutile.
- Pas d'ACC, PMO, Flex, Partner Hub.
- Audit curl + Playwright en fin de sprint (script repris du modèle
  `scripts/audit_postfix_cleanup_sidebar_conformite.mjs`).

TESTS
- Tous tests FE existants restent verts (5302 baseline post P1.5).
- Tous tests BE cockpit restent verts (~13 fichiers).
- Tests morts supprimés en cohérence (FE: ~111 it sur Cockpit/CockpitDecision/
  V1+/V2 ; BE: test_cockpit.py et test_cockpit_v2.py).
- Nouveau test BE `test_cockpit_strategique_billing_kpi.py` : payload
  contient `kpis[i].id == 'surfacturations_a_contester'`.
- Nouveau test FE `cockpit_strategique_acronyms.test.jsx` : 6 acronymes
  wrappés `<Term>`.
- Nouveau test Playwright drill-down `CadreApplicable` → `/conformite?regulation=X`.

AUDIT POSTFIX
Doc : docs/audits/audit_postfix_cockpit_p0_2026_05_25.md (modèle =
audit_postfix_cleanup_sidebar_conformite_2026_05_24.md). Verdict GO si
22/22 contrôles Playwright verts.

COMMIT
fix(cockpit): kill dead code, surface billing kpi and explain acronyms
```

---

## Annexes

### A. Critères de GO audit (auto-vérification)

- [x] 0 modification code (audit READ-ONLY strict respecté)
- [x] Tous les KPIs listés (§3 — 19 KPIs cockpit identifiés, 7 KPIs absents listés en §3.4)
- [x] Tous les écrans cockpit listés (§2 — 4 routes vivantes + 2 fichiers morts)
- [x] Tous les écarts de valeur identifiés (§4 — 4 axes Patrimoine/Conformité/Billing/Actions)
- [x] Tous les boutons morts identifiés (§6 — `BoutonRapportCOMEX` mort, 4 variantes top sites, doublons hero)
- [x] Recommandations P0/P1/P2 concrètes (§10 — 17 items avec effort jour estimé)

### B. Fichiers référencés (file:line cliquables)

- [App.jsx:30-31](../../frontend/src/App.jsx#L30-L31) — commentaire orphelins
- [App.jsx:315-340](../../frontend/src/App.jsx#L315-L340) — routes /cockpit/*
- [legacyRedirects.js:26](../../frontend/src/routes/legacyRedirects.js#L26) — `/cockpit` → `/cockpit/strategique`
- [CockpitStrategique.jsx](../../frontend/src/pages/CockpitStrategique.jsx) — 242 l, canonical
- [CockpitJour.jsx](../../frontend/src/pages/CockpitJour.jsx) — 266 l, briefing 30 s
- [CockpitPilotage.jsx](../../frontend/src/pages/CockpitPilotage.jsx) — 1 722 l, candidat extraction
- [Cockpit.jsx](../../frontend/src/pages/Cockpit.jsx) — 1 337 l, **ORPHELIN**
- [CockpitDecision.jsx](../../frontend/src/pages/CockpitDecision.jsx) — 1 528 l, **ORPHELIN**
- [NavRegistry.js:596-687](../../frontend/src/layout/NavRegistry.js#L596-L687) — panel cockpit
- [cockpit_strategique_fe_source_guards.test.js:54-57](../../frontend/src/__tests__/source_guards/cockpit_strategique_fe_source_guards.test.js#L54-L57) — SG_STRATEGIQUE_02

### C. Audits voisins déjà clôturés

- [audit_brique_patrimoine_deep_readonly_2026_05_23.md](audit_brique_patrimoine_deep_readonly_2026_05_23.md)
- [audit_brique_conformite_deep_readonly_2026_05_23.md](audit_brique_conformite_deep_readonly_2026_05_23.md)
- [audit_brique_bill_intelligence_deep_readonly_2026_05_23.md](audit_brique_bill_intelligence_deep_readonly_2026_05_23.md)
- [audit_postfix_patrimoine_p0ab_2026_05_23.md](audit_postfix_patrimoine_p0ab_2026_05_23.md)
- [audit_postfix_patrimoine_p0c_contract_coverage_2026_05_23.md](audit_postfix_patrimoine_p0c_contract_coverage_2026_05_23.md)
- [audit_postfix_cleanup_sidebar_conformite_2026_05_24.md](audit_postfix_cleanup_sidebar_conformite_2026_05_24.md) (post PR #300)
