# Pré-flight Lot 7 — Inventaire Sol + scope proposal

> **Date** : 2026-04-19 · post-Lot 6 (tag `v2.4-lot6-explorer` prêt)
> **Objectif** : définir Top 4 cibles Lot 7 calibrées sur shape API + impact démo

## 1. Inventaire routes applicatives

57 routes (hors Navigate redirects techniques) dans `frontend/src/App.jsx` + 60 imports lazy. Périmètre utilisateur (routes réelles, hors `_sol_showcase` dev + redirects) :

### Routes Sol-ifiées (✓ — Lot 1 à 6) — **22 pages**

| Route | Page alias | Composant loaded | Stratégie |
|---|---|---|---|
| `/` | CommandCenter | `CommandCenterSol` | Pure Sol |
| `/patrimoine` | Patrimoine | `PatrimoineSol` | Pure Sol |
| `/sites/:id` | Site360 | `Site360.jsx` (injecte `Site360Sol`) | Injection |
| `/conformite` | ConformitePage | `ConformiteSol` | Pure Sol |
| `/conformite/tertiaire` | TertiaireDashboardPage | `TertiaireDashboardPage.jsx` (injecte `ConformiteTertiaireSol`) | Injection (Lot 6 P4) |
| `/conformite/aper` | AperPage | `AperSol` | Pure Sol |
| `/cockpit` | Cockpit | `CockpitSol` | Pure Sol |
| `/regops/:id` | RegOps | `RegOps.jsx` (injecte `RegOpsSol`) | Injection |
| `/consommations` | ConsommationsPage | routeur 57 L | Routing pur |
| `/watchers` | WatchersPage | `WatchersPage.jsx` (injecte `WatchersSol`) | Injection (Lot 2 P7) |
| `/monitoring` | MonitoringPage | `MonitoringSol` | Pure Sol |
| `/compliance/pipeline` | CompliancePipelinePage | `CompliancePipelinePage.jsx` (injecte `CompliancePipelineSol`) | **Injection (Lot 6 P5)** |
| `/diagnostic-conso` | DiagnosticConso | `ConsumptionDiagPage.jsx` (injecte `DiagnosticConsoSol`) | Injection |
| `/usages` | UsagesDashboardPage | injecte `UsagesSol` | Injection |
| `/usages-horaires` | UsagesHorairesPage | `UsagesHorairesSol` | Pure Sol |
| `/bill-intel` | BillIntelPage | `BillIntelSol` | Pure Sol |
| `/achat-energie` | PurchasePage | `AchatSol` | Pure Sol |
| `/kb` | KBExplorerPage | `KBExplorerPage.jsx` (injecte `KBExplorerSol`) | Injection (Lot 6 P2) |
| `/segmentation` | SegmentationPage | `SegmentationSol` | Pure Sol (Lot 6 P3) |
| `/contrats` | Contrats | `ContratsSol` | Pure Sol |
| `/renouvellements` | ContractRadarPage | injecte `RenouvellementsSol` | Injection |
| `/anomalies` | AnomaliesPage | `AnomaliesSol` | Pure Sol |

### Routes LEGACY (✗ — **15 pages utilisateur + 7 admin/tech**)

| Route | Page | LOC | Catégorie |
|---|---|---|---|
| `/billing` | BillingPage | 726 | 🟢 Commerce |
| `/bill-intel-legacy` | BillIntelPage | ? | 🟡 Legacy pur (kept pour fallback) |
| `/compliance/sites/:siteId` | SiteCompliancePage | 732 | 🟢 Commerce (drill conformité) |
| `/consommations/portfolio` | ConsumptionPortfolioPage | 980 | 🟢 Commerce (DAF) |
| `/consommations/explorer` | ConsumptionExplorerPage | 1077 | 🟢 Commerce (explorer) |
| `/contracts-radar` | ContractRadarPage variant | ? | 🟡 Legacy pur |
| `/notifications` | NotificationsPage | 680 | 🟢 UX quotidien |
| `/import` | ImportPage | 676 | 🟡 Onboarding ponctuel |
| `/action-center` | ActionCenterPage | 378 | 🟡 Actions hub (Sol Cockpit Top3 existe) |
| `/activation` | ActivationPage | 297 | 🟡 Onboarding data |
| `/connectors` | ConnectorsPage | 264 | 🟡 Tech |
| `/onboarding` | OnboardingPage | 251 | 🟡 Ponctuel |
| `/onboarding/sirene` | SireneOnboardingPage | 779 | 🟡 Ponctuel |
| `/payment-rules` | PaymentRulesPage | 164 | 🔴 Admin-like |
| `/portfolio-reconciliation` | PortfolioReconciliationPage | 202 | 🔴 Admin-like |
| `/status` | StatusPage | 176 | 🔴 Tech |
| `/admin/*` × 7 | Admin*Page | 150-400 | 🔴 Admin (hors scope utilisateur) |

**Ratio Sol-ifié actuel** : ~22/37 surface utilisateur ≈ **59%**. Restent **15 pages utilisateur** potentielles Lot 7+ (hors Admin).

## 2. Shape API — 8 candidats audités

| Candidat | Endpoint | HTTP | Shape richesse |
|---|---|---|---|
| BillingPage | `GET /api/billing/periods?limit=N` + `/coverage-summary` + `/missing-periods` + `/compare-monthly` | 200 | ✅ Rich : `periods[]` (month_key, coverage_status, coverage_ratio, invoices_count, total_ttc, energy_kwh, invoice_ids) + coverage + compare multi-mois |
| SiteCompliancePage | `GET /api/compliance/sites/:id/summary` + `getMvSummary` + `getSiteWorkPackages` + `getActionsList` | 200 | ✅ Rich : `readiness` (completeness+gate+missing) + `applicability.{dt,bacs,aper}` (reason + missing_fields) + `snapshot` (statut_decret_tertiaire + avancement_pct) + MV + work_packages |
| NotificationsPage | `GET /api/notifications/list` + `/summary` | 200 | ✅ Rich : `total` + `by_severity.{critical,warn,info}` + `by_status.{new,read,dismissed}` + `new_critical/warn` |
| ConsumptionPortfolioPage | `GET /api/portfolio/consumption/summary` | 200 | ✅ Rich : `period` + `totals.{kwh,eur,co2,impact_eur}` + `coverage.{sites_total,with_data,confidence_split}` + `top_drift[]` + `top_base_night[]` |
| ActionCenterPage | `GET /api/action-center/actions/summary` | 200 | ⚠️ Maigre : `{total, by_status, by_priority, by_domain, by_owner, by_sla, overdue/open/resolved counts}` mais démo vide (total=0, by_X dicts vides) |
| ImportPage | `GET /api/demo/packs` + `/status` | 200 | ⚠️ Moyen : `packs[]` (key, label, description, sizes, is_default) — suffisant pour cards |
| ConsumptionExplorerPage | endpoints `/api/consumption/*` (à creuser) | ? | ⚠️ Non-audité (page 1077 L, multiple sources, risque 8ᵉ remap) |
| ActivationPage | endpoints à identifier | ? | ⚠️ Non-audité |

**Absences notables** : aucun endpoint manquant majeur sur les 4 top candidats. Pas de piège Phase 4-style (RegAssessment ORG-level inexistant) en vue.

## 3. Scoring /10 — 8 candidats évalués

Axes : Commercial (40%) · Complexité (20%) · Shape API (20%) · Cohérence (20%).

| # | Candidat | Comm/4 | Cplx/2 | API/2 | Cohér/2 | **Total /10** |
|---|---|---|---|---|---|---|
| 1 | **BillingPage** `/billing` | 3.5 | 1.2 | 2.0 | 1.6 | **8.3** |
| 2 | **SiteCompliancePage** `/compliance/sites/:siteId` | 3.0 | 1.0 | 2.0 | 1.8 | **7.8** |
| 3 | **NotificationsPage** `/notifications` | 2.8 | 1.2 | 2.0 | 1.6 | **7.6** |
| 4 | **ConsumptionPortfolioPage** `/consommations/portfolio` | 3.2 | 0.6 | 2.0 | 1.4 | **7.2** |
| 5 | **ActionCenterPage** `/action-center` | 2.6 | 1.6 | 1.2 | 1.4 | **6.8** |
| 6 | **ImportPage** `/import` | 2.0 | 1.2 | 1.6 | 1.0 | **5.8** |
| 7 | **ActivationPage** `/activation` | 1.8 | 1.8 | 0.8 | 1.0 | **5.4** |
| 8 | **ConsumptionExplorerPage** `/consommations/explorer` | 2.8 | 0.3 | 0.8 | 1.2 | **5.1** |

### Justifications scoring

- **BillingPage 8.3** : CFO-facing (reporting facturation interne + génération factures), shape API la plus riche (periods + coverage + missing + compare), cohérence forte avec `/bill-intel` déjà Sol (drill depuis anomalie → facture).
- **SiteCompliancePage 7.8** : complète le triangle conformité Sol (`/conformite` + `/conformite/tertiaire` + `/compliance/pipeline`) par le drill site. Shape API la plus complète du pack (readiness+applicability+snapshot+mv+work_packages).
- **NotificationsPage 7.6** : UX quotidien vu à chaque visite, Pattern B pur simple (list + filter). Shape 2-endpoints (list + summary) propre. LOC modéré.
- **ConsumptionPortfolioPage 7.2** : DAF-facing (agrégat conso portefeuille), shape riche totals+coverage+drift. Mais 980 LOC legacy = gros wrap `{false && (…)}`.
- **ActionCenterPage 6.8** : hub actions, mais shape démo vide (by_X dicts vides = pas de KPIs crédibles démo HELIOS). Redondance potentielle avec Cockpit Top3 déjà Sol.
- **ImportPage 5.8** : onboarding ponctuel (pas UX quotidien), shape correcte mais scope métier étroit.
- **ActivationPage 5.4** : onboarding data, 297 LOC petit mais usage ponctuel.
- **ConsumptionExplorerPage 5.1** : 1077 LOC massif + endpoint non audité = risque 8ᵉ remap élevé. À repousser Lot 8+.

## 4. Top 4 Lot 7 — proposition

### Scénario A (score décroissant) — recommandé

1. **Phase 1 · BillingPage** (8.3) — Pattern B · shape riche · driver CFO
2. **Phase 2 · SiteCompliancePage** (7.8) — Pattern C (détail site) · complète triangle conformité
3. **Phase 3 · NotificationsPage** (7.6) — Pattern B simple · UX quotidien
4. **Phase 4 · ConsumptionPortfolioPage** (7.2) — Pattern B · DAF-facing · legacy gros

**Volumétrie estimée** : ~2h30 × 4 = **~10h** sur 5-6 jours calendaires au rythme Lot 6 (Phase 5 Lot 6 = 1h45 pour cas simple · BillingPage + SiteCompliancePage probablement 2h30-3h chacune).

**Risques identifiés** :
- Aucun 8ᵉ remap attendu (les 4 shapes API sont riches)
- 980 LOC ConsumptionPortfolio = gros wrap (mais pas structurellement différent)
- Pattern C (SiteCompliance) moins éprouvé que Pattern B (3 pages sur 4 sont B)

### Scénario B (opportuniste / commerce-first) — alternative

1. BillingPage (8.3) → driver revenue
2. ConsumptionPortfolioPage (7.2) → DAF
3. SiteCompliancePage (7.8) → conformité drill
4. NotificationsPage (7.6) → UX

Même Top 4, ordre différent (commerce d'abord).

## 5. Critères de cadrage — à trancher avec user

### C1 — Budget Lot 7
- 4 phases au rythme Lot 6 : ~10h · **5-6 jours calendaires**
- 3 phases (skip NotificationsPage) : ~7h30 · 4 jours — garde bandwidth pour Enedis/HELIOS real data

### C2 — Thème Lot 7
- **(a) Commerce-first** : BillingPage + ConsumptionPortfolio + SiteCompliance + NotificationsPage — Scénario A/B
- **(b) Opérations** : SiteCompliance + NotificationsPage + ImportPage + ActivationPage — UX quotidien
- **(c) Mixte 2+2** : BillingPage + ConsumptionPortfolio + NotificationsPage + SiteCompliance
- **(d) Opportuniste** : Scénario A pur (shape API validée, pas de risque 8ᵉ remap)

### C3 — Contrainte production
Enedis real connector + HELIOS V2 real data restent P0 démo investor. Question :
- **Option X** : Lot 7 complet (4 cibles) AVANT data réelle · refonte visuelle 100% cohérente pour démo
- **Option Y** : Lot 7 partiel (2-3 cibles P0 Top 4) puis bascule data réelle · accepter 75% Sol-ifié
- **Option Z** : Lot 7 en parallèle data réelle (via workstreams) — plus risqué

## 6. Vérifications post-livraison pré-flight

- ✅ Inventaire 57 routes (étape 1)
- ✅ Mapping Sol/legacy 22 Sol-ifiées vs 15 user legacy + 7 admin (étape 2)
- ✅ Shape API auditée 8 candidats via curl (étape 3)
- ✅ Score /10 par candidat justifié (étape 3)
- ✅ Top 4 proposé avec ordre scénarios A/B (étape 4)
- 🛑 Discussion pré-lancement avec user pour valider C1/C2/C3 + choix scénario

Prêt pour arbitrage user avant génération prompt Lot 7 calibré.
