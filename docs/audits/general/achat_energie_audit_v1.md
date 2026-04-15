# AUDIT COMPLET — Brique "Achats Energie" (Front + Back + Data + UX)

**Date**: 2026-02-26
**Auditeur**: Claude Code (Opus 4.6)
**Branche**: `claude/audit-energy-purchasing-nmNdG`
**Perimetre**: PurchasePage, PurchaseAssistantPage, domaine `purchase/`, endpoints `/api/purchase/*`, modeles, seeds, navigation, UX

---

## 1. Resume executif (10 lignes)

La brique "Achats Energie" est **la plus ambitieuse du POC** avec 2 pages distinctes, 14 endpoints API, 3 tables SQL, un moteur front-end Monte Carlo (Brique 3), et des exports A4.

**Ce qui marche**: Le flow Simulation mono-site (choisir site → configurer → calculer → accepter) est fonctionnel bout-en-bout. Les 4 onglets (Simulation/Portefeuille/Echeances/Historique) sont branches. L'Assistant Achat (Brique 3, wizard 8 etapes) est complet en front-end avec un moteur de scoring, Monte Carlo et exports Note de Decision/Pack RFP. Les routes sont montees dans `main.py`. L'ErrorBoundary et le DebugDrawer sont en place.

**Ce qui casse**: (P0) L'`org_id` du portfolio est **hardcode a `1`** dans PurchasePage.jsx L234/L243. Les `?filter=renewal|missing` des deep-links Cockpit ne sont **pas lus** par PurchasePage (pas de `useSearchParams`). L'Assistant Achat (Brique 3) est un **moteur purement front-end** sans aucun appel API backend — les donnees demo sont hardcodees en JS, non liees au Patrimoine reel.

**Risque principal**: Un DAF/DG qui navigue vers Achats via le Cockpit tombera sur un filtre non applique. Le portfolio multi-site ne fonctionne que pour org_id=1. La Brique 3 (Assistant Achat) est un prototype autoportant deconnecte du reste du systeme.

---

## 2. Inventaire Front-end

### 2.1 Pages

| Route | Fichier | But | Module Nav | Expert Only |
|-------|---------|-----|------------|-------------|
| `/achat-energie` | `pages/PurchasePage.jsx` | Simulateur 4 onglets (Simulation / Portefeuille / Echeances / Historique) | marche | Oui |
| `/achat-assistant` | `pages/PurchaseAssistantPage.jsx` | Wizard 8 etapes post-ARENH (Brique 3) | marche | Oui |

### 2.2 Aliases de route (App.jsx L149-150)

| Alias | Redirige vers |
|-------|---------------|
| `/achats` | `/achat-energie` |
| `/purchase` | `/achat-energie` |

### 2.3 Composants enfants

| Composant | Fichier | Utilise par | But |
|-----------|---------|-------------|-----|
| `PurchaseErrorBoundary` | `components/PurchaseErrorBoundary.jsx` | PurchasePage | ErrorBoundary local avec retry |
| `PurchaseDebugDrawer` | `components/PurchaseDebugDrawer.jsx` | PurchasePage | Debug state (dev only) |
| `ExportNoteDecision` | `components/ExportNoteDecision.jsx` | PurchasePage (Simulation) | Export A4 Note de Decision (window.print) |
| `ExportPackRFP` | `components/ExportPackRFP.jsx` | PurchasePage (Portefeuille) | Export A4 Pack RFP (window.print) |
| `CoverageBar` | `components/CoverageBar.jsx` | Cockpit | Barre couverture contrats |
| `ScopeSummary` | `components/ScopeSummary.jsx` | Cockpit | Resume scope multi-site |
| `InsightDrawer` | `components/InsightDrawer.jsx` | Cockpit | Tiroir detail insight |
| `PerformanceSnapshot` | `components/PerformanceSnapshot.jsx` | Cockpit | Snapshot KPI |
| `ROISummaryBar` | `components/ROISummaryBar.jsx` | Cockpit | Barre ROI |

### 2.4 Domaine front-end (Brique 3)

| Fichier | But |
|---------|-----|
| `domain/purchase/index.js` | Barrel export (re-export tout) |
| `domain/purchase/types.js` | Enums: EnergyType, OfferStructure, ScenarioPreset, Persona, Confidence, ScoreLevel |
| `domain/purchase/assumptions.js` | DEFAULT_MARKET, SCENARIO_PRESETS, PERSONA_PROFILES, saisonnalite |
| `domain/purchase/engine.js` | Moteur principal: runEngine, memoisation, validation breakdown |
| `domain/purchase/risk.js` | Monte Carlo: monteCarloOffer, computeTco, cvar90, volatilityProxy |
| `domain/purchase/scoring.js` | scoreBudgetRisk, scoreTransparency, scoreContractRisk, scoreDataReadiness |
| `domain/purchase/recommend.js` | Recommandation multi-critere |
| `domain/purchase/scenarioLibrary.js` | Generateur trajectoires (PRNG deterministe) |
| `domain/purchase/rfp.js` | Generateurs: Note de Decision, Pack RFP, CSV comparatif |
| `domain/purchase/audit.js` | Piste d'audit in-memory (appendDecision, export JSONL) |
| `domain/purchase/demoData.js` | 2 orgs demo, 3 sites, 5 offres (4 propres + 1 dirty) |
| `domain/purchase/dataAdapter.js` | Bridge B1/B2 → domaine (fetchSites, fetchAnomalies, fallback demo) |

### 2.5 Modele de contrat

| Fichier | But |
|---------|-----|
| `models/purchaseSignalsContract.js` | Contract normalization pour signaux achat (renewals, couverture, manquants) |

### 2.6 Services API utilises (api.js L655-674)

| Fonction front | Methode | Route API |
|----------------|---------|-----------|
| `getPurchaseEstimate(siteId)` | GET | `/purchase/estimate/{siteId}` |
| `getPurchaseAssumptions(siteId)` | GET | `/purchase/assumptions/{siteId}` |
| `putPurchaseAssumptions(siteId, data)` | PUT | `/purchase/assumptions/{siteId}` |
| `getPurchasePreferences(params)` | GET | `/purchase/preferences` |
| `putPurchasePreferences(data)` | PUT | `/purchase/preferences` |
| `computePurchaseScenarios(siteId)` | POST | `/purchase/compute/{siteId}` |
| `getPurchaseResults(siteId)` | GET | `/purchase/results/{siteId}` |
| `acceptPurchaseResult(resultId)` | PATCH | `/purchase/results/{resultId}/accept` |
| `seedPurchaseDemo()` | POST | `/purchase/seed-demo` |
| `seedWowHappy()` | POST | `/purchase/seed-wow-happy` |
| `seedWowDirty()` | POST | `/purchase/seed-wow-dirty` |
| `computePortfolio(orgId)` | POST | `/purchase/compute?org_id=X&scope=org` |
| `getPortfolioResults(orgId)` | GET | `/purchase/results?org_id=X` |
| `getPurchaseRenewals(orgId)` | GET | `/purchase/renewals?org_id=X` |
| `getPurchaseHistory(siteId)` | GET | `/purchase/history/{siteId}` |
| `getPurchaseActions(orgId)` | GET | `/purchase/actions?org_id=X` |

### 2.7 Params URL attendus

| Page | Param | Source | Transmission |
|------|-------|--------|--------------|
| PurchasePage | `selectedSiteId` | ScopeContext (`scopedSites`) | State interne, auto-select premier site |
| PurchasePage | `org_id` pour portfolio | **Hardcode `1`** (L234, L243) | BUG P0 |
| PurchasePage | `?filter=renewal\|missing` | Deep-links Cockpit | **NON LU** — BUG P0 |
| PurchaseAssistantPage | aucun | Mode demo interne | Pas de param URL |

---

## 3. Inventaire Back-end

### 3.1 Router et montage

| Element | Fichier | Statut |
|---------|---------|--------|
| Router | `backend/routes/purchase.py` | `prefix="/api/purchase"`, tags=["Achat Energie"] |
| Import main.py | `main.py:26` | `purchase_router` importe |
| Montage main.py | `main.py:93` | `app.include_router(purchase_router)` — OK |
| Routes __init__.py | `routes/__init__.py` | `purchase_router` exporte — OK |

### 3.2 Endpoints (16 routes)

| # | Methode | Route | Fichier:Ligne | Inputs | Outputs | Headers | Auth |
|---|---------|-------|---------------|--------|---------|---------|------|
| 1 | GET | `/api/purchase/estimate/{site_id}` | purchase.py:60 | site_id (path) | `{volume_kwh_an, source, months_covered, profile_factor}` | X-Org-Id (via auth) | optional auth + check_site_access |
| 2 | GET | `/api/purchase/assumptions/{site_id}` | purchase.py:72 | site_id (path) | `{id, site_id, energy_type, volume_kwh_an, ...}` | idem | optional auth |
| 3 | PUT | `/api/purchase/assumptions/{site_id}` | purchase.py:106 | site_id (path), body: AssumptionSetIn | `{id, status}` | idem | optional auth |
| 4 | GET | `/api/purchase/preferences` | purchase.py:151 | org_id (query, opt) | `{id, org_id, risk_tolerance, budget_priority, green_preference}` | idem | optional auth |
| 5 | PUT | `/api/purchase/preferences` | purchase.py:181 | org_id (query, opt), body: PreferenceIn | `{id, status}` | idem | optional auth |
| 6 | GET | `/api/purchase/renewals` | purchase.py:224 | org_id (query, opt) | `{total, renewals: [...]}` | idem | optional auth |
| 7 | GET | `/api/purchase/actions` | purchase.py:293 | org_id (query, opt) | computed purchase actions | idem | optional auth |
| 8 | POST | `/api/purchase/compute` | purchase.py:307 | org_id (query, req), scope (query, default="org") | `{batch_id, org_id, portfolio, sites}` | idem | optional auth |
| 9 | POST | `/api/purchase/compute/{site_id}` | purchase.py:425 | site_id (path) | `{assumption_set_id, site_id, run_id, scenarios}` | idem | optional auth |
| 10 | GET | `/api/purchase/results` | purchase.py:531 | org_id (query, req) | `{org_id, portfolio, sites}` | idem | optional auth |
| 11 | GET | `/api/purchase/results/{site_id}` | purchase.py:613 | site_id (path) | `{assumption_set_id, site_id, run_id, scenarios}` | idem | optional auth |
| 12 | GET | `/api/purchase/history/{site_id}` | purchase.py:679 | site_id (path) | `{site_id, total_runs, runs}` | idem | optional auth |
| 13 | PATCH | `/api/purchase/results/{result_id}/accept` | purchase.py:742 | result_id (path) | `{id, reco_status}` | aucun | **AUCUN AUTH** — BUG P1 |
| 14 | POST | `/api/purchase/seed-demo` | purchase.py:757 | aucun | seed result | aucun | **AUCUN AUTH** |
| 15 | POST | `/api/purchase/seed-wow-happy` | purchase.py:766 | aucun | seed result | aucun | **AUCUN AUTH** |
| 16 | POST | `/api/purchase/seed-wow-dirty` | purchase.py:773 | aucun | seed result | aucun | **AUCUN AUTH** |

### 3.3 Modeles SQLAlchemy (3 tables)

| Table | Fichier | Colonnes cles | Relations |
|-------|---------|---------------|-----------|
| `purchase_assumption_sets` | `models/purchase_models.py:14` | id, site_id (FK sites), energy_type, volume_kwh_an, profile_factor, horizon_months, assumptions_json | site, scenario_results |
| `purchase_preferences` | `models/purchase_models.py:56` | id, org_id, risk_tolerance, budget_priority, green_preference | aucune FK |
| `purchase_scenario_results` | `models/purchase_models.py:83` | id, run_id, batch_id, inputs_hash, assumption_set_id (FK), strategy, price_eur_per_kwh, total_annual_eur, risk_score, savings_vs_current_pct, p10_eur, p90_eur, is_recommended, reco_status | assumption_set |

### 3.4 Enums (models/enums.py)

| Enum | Valeurs |
|------|---------|
| `PurchaseStrategy` | fixe, indexe, spot |
| `PurchaseRecoStatus` | draft, accepted, rejected |
| `BillingEnergyType` | elec, gaz (utilise pour energy_type) |

### 3.5 Services

| Service | Fichier | Fonctions |
|---------|---------|-----------|
| purchase_service | `services/purchase_service.py` | estimate_consumption, compute_profile_factor, compute_scenarios, recommend_scenario, get_org_site_ids, compute_inputs_hash, aggregate_portfolio_results |
| purchase_actions_engine | `services/purchase_actions_engine.py` | compute_purchase_actions (ephemere: renewal_urgent/soon/plan, strategy_switch, accept_reco) |
| purchase_seed | `services/purchase_seed.py` | seed_purchase_demo (2 sites x 3 scenarios) |
| purchase_seed_wow | `services/purchase_seed_wow.py` | seed_wow_happy (15 sites clean), seed_wow_dirty (15 sites edge-cases) |
| billing_service | `services/billing_service.py` | get_reference_price (utilise par compute_scenarios) |

### 3.6 Tests

| Fichier | Tests | Couverture |
|---------|-------|------------|
| `tests/test_purchase.py` | 25 tests (13 V1 + 12 V1.1) | Models, service, API, seed, portfolio, renewals, history, dashboard 2min |

---

## 4. Bugs & incoherences (priorise P0/P1)

### P0 — Bloquants pour demo

| # | Bug | Fichier:Ligne | Preuve | Reproduction |
|---|-----|---------------|--------|-------------|
| P0-1 | **org_id hardcode `1` dans Portfolio** | `PurchasePage.jsx:234` `computePortfolio(1)` et L243 `getPortfolioResults(1)` | L'org_id devrait venir du ScopeContext. Si l'org demo a un id != 1, le portfolio est vide. | Charger un dataset WOW (qui cree une org avec un id > 1) → cliquer "Calculer le portefeuille" → resultat vide car org_id=1. |
| P0-2 | **Deep-link `?filter=renewal\|missing` ignore** | `PurchasePage.jsx` (entier) | Aucun `useSearchParams` dans le composant. Les CTAs du Cockpit (`ImpactDecisionPanel.jsx:231,243`) et du modele lever (`leverEngineModel.js:152,163`) naviguent vers `/achat-energie?filter=renewal` mais le filtre n'est jamais lu. | Cliquer "Renouvellement" dans le Cockpit → PurchasePage s'ouvre sur l'onglet Simulation au lieu de l'onglet Echeances. |
| P0-3 | **Brique 3 (Assistant Achat) deconnectee du backend** | `PurchaseAssistantPage.jsx` (entier) | Zero appel API backend. Toutes les donnees viennent de `domain/purchase/demoData.js` (hardcode). Le `dataAdapter.js` existe mais n'est **pas utilise** par PurchaseAssistantPage — il fait ses propres calculs avec le moteur front-end. | Activer "mode reel" (decocher "Mode demo") → message "Connectez-vous a votre patrimoine" avec zero integration reelle. |

### P1 — Importants

| # | Bug | Fichier:Ligne | Preuve | Impact |
|---|-----|---------------|--------|--------|
| P1-1 | **PATCH `/results/{id}/accept` sans auth** | `purchase.py:742` | Pas de `auth: AuthContext = Depends(get_optional_auth)` ni `check_site_access`. N'importe qui peut accepter une recommandation. | Risque securite: un utilisateur non authentifie peut valider un scenario d'achat. |
| P1-2 | **3 endpoints seed sans auth** | `purchase.py:757,766,773` | `seed-demo`, `seed-wow-happy`, `seed-wow-dirty` n'ont aucune protection auth. | Risque demo: n'importe qui peut re-seeder la base en production. |
| P1-3 | **`datetime.utcnow()` deprece** | `purchase_models.py:46,80,147` et `purchase_service.py:28` | Python 3.12+ deprece `datetime.utcnow()` au profit de `datetime.now(UTC)`. | 54942 warnings si logging verbose. |
| P1-4 | **Energy Gate "elec only" incoherent** | `PurchasePage.jsx:349-357` affiche "Post-ARENH — elec uniquement" avec un Lock icon, mais le backend `purchase.py:111` rejette aussi le gaz. | Le front lock l'input mais ne valide pas cote client. Le demoData.js de Brique 3 inclut un site GAZ (Siege Paris 8e). | Confusion: un site GAZ dans l'Assistant Achat passe les calculs front-end mais echouerait cote backend. |
| P1-5 | **`toast()` sans `toast` dans la deps array du useCallback** | `PurchasePage.jsx:169` — `loadSiteData` utilise `toast` mais ne le met pas en dependance du `useCallback`. | Le `toast` capture une reference obsolete potentiellement (React StrictMode). | Minor: le toast pourrait ne pas fonctionner apres un re-render profond. |

### P1 — Incoherences structurelles

| # | Incoherence | Detail |
|---|-------------|--------|
| P1-6 | **2 systemes de simulation paralleles** | PurchasePage = backend (3 strategies fixe/indexe/spot, prix deterministes), PurchaseAssistantPage = front-end (Monte Carlo, 4 structures FIXE/INDEXE/SPOT/HYBRIDE, scoring multi-dimension). Aucun partage de code ou de donnees entre les deux. |
| P1-7 | **Portfolio PurchasePage vs Brique 3** | PurchasePage onglet Portefeuille appelle le backend. PurchaseAssistantPage Step 1 utilise ses propres demo orgs hardcodees. Zero synchronisation. |
| P1-8 | **`purchaseSignalsContract.js` utilise par Cockpit mais pas par PurchasePage** | Le model normalise les signaux d'achat pour le Cockpit mais PurchasePage n'en beneficie pas. |

---

## 5. Manques data (ce qui manque pour rendre la brique credible)

### 5.1 Donnees reelles manquantes

| Donnee | Source attendue | Etat actuel | Solution POC |
|--------|-----------------|-------------|--------------|
| **Prix marche temps reel** (EPEX Spot FR, forwards) | EPEX/EEX API ou RTE Transparency | **ABSENT** — prix de ref calcule via `get_reference_price()` (contrat > tarif > default 0.18) | Seed: table `market_prices` avec historique 12 mois EPEX Spot FR. Import CSV ou connecteur RTE. |
| **Forward curves** (CAL+1, CAL+2, CAL+3) | EEX API | **ABSENT** | Seed: courbe forward statique dans assumptions_json. |
| **TURPE / Acheminement detail** | Enedis Tarif ou CRE open data | **ABSENT** — Brique 3 utilise des % estimes (27% du TCO) | Seed: table referentielle TURPE avec postes (part fixe, soutirage HP/HC, depassement). Ou fichier YAML statique. |
| **ATRD / ATRT** (gaz) | GRDF/GRTgaz | **ABSENT** | Non prioritaire (Energy Gate elec-only). |
| **CSPE / Taxes reelles** | CRE open data | Hardcode 14% dans demoData.js | Seed: YAML referentiel `tarif_taxes.yaml` (doc existant dans docs/referential_tarifs_taxes.md). |
| **Profil de charge reel** (courbe horaire) | Enedis DataConnect ou import CSV | Fallback a un facteur de profil simple (0.85/1.0/1.25) | Deja couvert par la brique Conso (MeterReading). Bridge purchase_service ← MeterReading pour profil horaire. |
| **Contrats reels fournisseurs** | Import CSV ou saisie manuelle | Seed: 2 contrats (Site A EDF, Site B Engie) via `seed_purchase_demo` | Suffisant pour POC. |
| **Volumes conso mensuels** | Brique Conso (MeterReading) | Estimation annualisee dans `estimate_consumption()` avec fallback 500k kWh | OK pour POC mais a bridger avec la conso reelle. |

### 5.2 Donnees demo vs reelles

| Source | Statut | Fichier |
|--------|--------|---------|
| Seed purchase_seed.py | REEL (seede en DB) | `services/purchase_seed.py` — 2 sites x 3 scenarios |
| Seed purchase_seed_wow.py | REEL (seede en DB) | `services/purchase_seed_wow.py` — 15 sites x 3 scenarios |
| Demo Brique 3 front-end | HARDCODE JS | `domain/purchase/demoData.js` — 2 orgs, 3 sites, 5 offres |
| Prix de reference | FALLBACK | `billing_service.get_reference_price()` → contrat > tarif > default 0.18 EUR/kWh |

---

## 6. Check Routes & Boutons

### 6.1 Navigation (NavRegistry.js)

| Route | Label | Module | Keywords | Expert Only |
|-------|-------|--------|----------|-------------|
| `/achat-energie` | "Achats energie" | marche | achat, purchase, scenarios, strategie | Oui (module marche) |
| `/achat-assistant` | "Assistant Achat" | marche | assistant, wizard, rfp, arenh, corridor | Oui (module marche) |

**Constat**: Les deux pages sont dans le module "Marche" qui est `expertOnly: true`. Un DAF/DG en mode normal **ne voit pas les achats**. C'est coherent avec la progression graduelle (Cockpit → Operations → Analyse → Marche), mais c'est un point UX critique pour le public cible.

### 6.2 CTAs/Boutons dans PurchasePage

| CTA | Emplacement | Action | Route/API | Contexte transmis |
|-----|------------|--------|-----------|-------------------|
| Select site (dropdown) | Simulation, section 1 | Change `selectedSiteId` → recharge donnees | 4 API calls en parallele | site_id via state |
| "Sauvegarder" hypotheses | Simulation, section 2 | PUT assumptions | `/purchase/assumptions/{siteId}` | site_id + assumptions |
| "Sauvegarder" preferences | Simulation, section 3 | PUT preferences | `/purchase/preferences` | preferences (sans org_id) |
| "Calculer les scenarios" | Simulation, section 3 | PUT assumptions + PUT prefs + POST compute | 3 API calls sequentiels | site_id |
| "Accepter" | Resultat recommande | PATCH accept | `/purchase/results/{id}/accept` | result_id |
| "Exporter Note de Decision (A4)" | Apres resultats | Ouvre modal ExportNoteDecision | window.print() | scenarios, site_nom, volume |
| "Calculer le portefeuille" | Portefeuille | POST compute org | `/purchase/compute?org_id=1` | **org_id hardcode** |
| "Charger resultats existants" | Portefeuille | GET results org | `/purchase/results?org_id=1` | **org_id hardcode** |
| "15 sites (happy)" / "15 sites (dirty)" | Portefeuille | POST seed-wow | `/purchase/seed-wow-happy\|dirty` | aucun |
| "Exporter Pack RFP (A4)" | Portefeuille (apres resultats) | Ouvre modal ExportPackRFP | window.print() | portfolio + sites |

### 6.3 URLs hardcodees detectees

| Fichier | Ligne | URL hardcodee | Risque | Recommandation |
|---------|-------|---------------|--------|----------------|
| `leverEngineModel.js` | L152 | `'/achat-energie?filter=renewal'` | Filtre non lu par PurchasePage | Passer par route registry + useSearchParams |
| `leverEngineModel.js` | L163 | `'/achat-energie?filter=missing'` | idem | idem |
| `dataActivationModel.js` | L103 | `'/achat-energie'` | OK, route canonique | Acceptable si canonique |
| `Cockpit2MinPage.jsx` | L233 | `<Link to="/achat-energie">` | OK, route canonique | Acceptable |
| `ImpactDecisionPanel.jsx` | L231 | `navigate('/achat-energie?filter=renewal')` | Filtre non lu | Passer par route registry |
| `ImpactDecisionPanel.jsx` | L243 | `navigate('/achat-energie?filter=missing')` | idem | idem |
| `PurchasePage.jsx` | L234 | `computePortfolio(1)` | org_id=1 hardcode | Utiliser `effectiveOrgId` du ScopeContext |
| `PurchasePage.jsx` | L243 | `getPortfolioResults(1)` | org_id=1 hardcode | idem |

### 6.4 Coherence scope (bandeau global)

| Question | Reponse |
|----------|---------|
| PurchasePage respecte-t-il le scope site du header ? | **Partiellement**. Le dropdown site utilise `scopedSites` du ScopeContext. Mais l'onglet Portefeuille ignore le scope et utilise org_id=1. |
| PurchasePage explique-t-il si mono-site ou multi-sites ? | **Non**. L'onglet Simulation est mono-site, Portefeuille est multi-sites, mais aucune explication visible. |
| PurchaseAssistantPage respecte-t-il le scope ? | **Non**. Il utilise ses propres sites demo hardcodes, deconnecte du ScopeContext. |

---

## 7. UX "Grand Public" — Scorecard

### 7.1 Scorecard rapide (0-10)

| Critere | Score | Justification |
|---------|-------|---------------|
| **Clarte** | 6/10 | Labels FR corrects, mais confusion entre 2 pages (PurchasePage vs Assistant). Un DAF ne sait pas laquelle utiliser. |
| **Time-to-insight** | 5/10 | PurchasePage: 2 clics pour voir des resultats (select site + "Calculer"). Assistant: 5 clics (wizard 8 steps). Correct pour PurchasePage, long pour Assistant. |
| **Coherence scope** | 3/10 | org_id hardcode, filter params ignores, Brique 3 deconnectee du Patrimoine reel. |
| **Actionnabilite** | 7/10 | "Accepter" un scenario, exports A4, historique — clairs et actionables. |
| **Robustesse erreurs/empty** | 6/10 | Toast sur erreurs API, ErrorBoundary, empty states presents mais generiques ("Aucun historique"). |
| **TOTAL** | **5.4/10** | |

### 7.2 Top 10 frictions UX (sans coder)

| # | Friction | Page | Fix propose |
|---|---------|------|-------------|
| 1 | **2 pages Achat sans explication** — "Achats energie" vs "Assistant Achat": un DAF ne sait pas laquelle choisir | NavPanel | Ajouter une description inline ou merger en une seule page avec un switch "Simple / Expert" |
| 2 | **Module "Marche" expert-only** — un DAF/DG ne voit pas les achats en mode normal | NavRegistry | Rendre visible en mode normal avec un niveau simplifie (Echeances + Recommandation), expert = simulation complete |
| 3 | **Aucune explication de l'€/MWh** — les prix affiches n'expliquent pas d'ou ils viennent (ref_price, source, date) | PurchasePage, section resultats | Ajouter un tooltip "Prix de reference: 0.18 EUR/kWh (source: contrat EDF, maj: 15/02/2026)" |
| 4 | **Risk score sans benchmark** — "45/100" ne parle pas a un DG | PurchasePage, jauge risque | Ajouter un libelle contextuel: "Risque moyen — equivalent a l'exposition d'un contrat indexe classique" |
| 5 | **Empty state Portefeuille trop vague** — "Cliquez pour lancer l'analyse multi-site" sans explication | PurchasePage, onglet Portefeuille | Ajouter: "Ce module analyse tous vos sites et recommande une strategie d'achat par site. Prerequis: au moins 2 sites dans votre patrimoine." |
| 6 | **Pas de lien vers contrat source** — L'onglet Echeances montre le fournisseur mais ne lien pas vers la fiche contrat (billing) | PurchasePage, onglet Echeances | Ajouter un lien vers `/billing?contract_id=X` sur chaque ligne |
| 7 | **"Post-ARENH" jargon** — "Post-ARENH — elec uniquement" n'est pas comprehensible pour un DAF | PurchasePage, section Hypotheses | Remplacer par: "Marche libre electricite (fin de l'ARENH en 2025)" avec un tooltip explicatif |
| 8 | **Wizard Brique 3 trop long** — 8 etapes pour un DAF presse, pas de shortcut pour les experts | PurchaseAssistantPage | Ajouter un mode "Express" (3 etapes: portfolio + offres + resultats) avec valeurs par defaut |
| 9 | **"Courtier Opaque SARL" en demo** — l'offre intentionnellement "dirty" n'est pas signalee comme telle en mode demo | PurchaseAssistantPage | Ajouter un badge "Offre test (mauvaise)" ou un tooltip explicatif en mode demo |
| 10 | **Pas de notification de fin de calcul** — un portefeuille de 15 sites peut prendre quelques secondes sans feedback adequat | PurchasePage, Portefeuille | Ajouter une barre de progression ou un compteur "Site 5/15 calcule..." |

### 7.3 Empty states

| Situation | Page | Affichage actuel | Adequat ? |
|-----------|------|-----------------|-----------|
| Aucun site dans le scope | PurchasePage | Dropdown vide, pas de message | **Non** — ajouter "Aucun site disponible. Importez votre patrimoine." |
| Pas de resultats de simulation | PurchasePage, Simulation | Rien ne s'affiche | **Partiellement** — le skeleton loader s'affiche pendant loading, mais pas d'invite a calculer si jamais calcule |
| Portefeuille vide | PurchasePage, Portefeuille | "Cliquez pour lancer l'analyse multi-site" | **OK** mais sans contexte |
| Echeances vides | PurchasePage, Echeances | "Aucun contrat avec echeance a venir" | **OK** |
| Historique vide | PurchasePage, Historique | "Aucun historique de calcul pour ce site" | **OK** |
| Mode reel sans patrimoine | PurchaseAssistantPage, Step 1 | "Connectez-vous a votre patrimoine (Brique 1)" | **OK** mais pas de lien vers /patrimoine |
| Aucune offre saisie | PurchaseAssistantPage, Step 5 | Bouton disabled + texte demo | **OK** |

### 7.4 Explainability (d'ou viennent les chiffres)

| Indicateur affiche | Source reelle | Explique a l'utilisateur ? |
|-------------------|---------------|---------------------------|
| Volume estime (kWh/an) | MeterReading > Invoice > 500k default | **Oui** — source + mois couverts affiches |
| Profil de charge (facteur) | SiteOperatingSchedule (24/7=0.85, bureau=1.25) | **Partiellement** — affiche "Profil pointe/plat" mais pas la source |
| Prix EUR/kWh par scenario | ref_price x multiplicateur (1.05/0.95/0.88) | **Non** — ni le ref_price ni le multiplicateur ne sont visibles |
| Risk score (0-100) | Valeurs fixes (15/45/75) | **Non** — pas de methodologie visible |
| P10/P90 fourchette | Pourcentages fixes du total (70%-145%) | **Non** — pas d'explication de la methode |
| Savings vs current | (1 - scenario_total/current_total) x 100 | **Partiellement** — le % est affiche mais "prix actuel" n'est pas defini |
| TCO Brique 3 (EUR/MWh) | Monte Carlo 1000 iterations, PRNG deterministe | **Non** — "P50" mentionne mais pas les hypotheses |
| CVaR 90 | 10e percentile de la distribution Monte Carlo | **Non** — terme technique sans explication |

---

## 8. Robustesse / Erreurs / Observabilite

### 8.1 Gestion d'erreurs front-end

| Pattern | Fichier | Implementation |
|---------|---------|---------------|
| ErrorBoundary | `PurchaseErrorBoundary.jsx` | Capture exceptions React, affiche message + bouton retry. Console.error en dev. OK. |
| Toast sur erreur API | `PurchasePage.jsx` (7 catch blocks) | Tous les catch appellent `toast('Erreur...', 'error')`. OK. |
| DebugDrawer | `PurchaseDebugDrawer.jsx` | Visible uniquement en dev (`import.meta.env.DEV`). OK. |
| Console.error silencieux | PurchaseAssistantPage.jsx:224 | `toast('Erreur lors du calcul: ' + err.message)` — OK, pas de console.error silencieux. |

**Verdict**: Bonne couverture. Pas d'appel API silencieux detecte dans la brique achat.

### 8.2 Risques de 404/405

| Risque | Statut |
|--------|--------|
| Routes purchase non montees dans main.py | **OK** — `purchase_router` est importe et monte (main.py:26,93) |
| Collision de routes FastAPI (parameterless vs path-param) | **OK** — Le code commente (L218-220) indique que les routes sans parametre sont declarees AVANT les routes avec path-param. Ordre correct. |
| Endpoints renvoient HTML au lieu de JSON | **Faible risque** — Toutes les routes retournent des dicts Python (serialises en JSON par FastAPI). Pas de proxy reverse detecte dans le code. |

### 8.3 Verification de registration (routes/__init__.py)

La verification est faite dans `main.py:113-120` pour les routes billing critiques. **Pas de verification equivalente pour les routes purchase**. Recommandation: ajouter une verification au startup pour les routes purchase critiques aussi.

### 8.4 Observabilite

| Element | Statut |
|---------|--------|
| Logging structure | `services/json_logger.py` est setup dans main.py. Mais `purchase_service.py` et `purchase.py` n'utilisent **aucun logging**. Pas de `print()` non plus. |
| Request tracing | `RequestContextMiddleware` ajoute `X-Request-Id` et `X-Response-Time`. OK pour le purchase. |
| Metriques | Pas de metriques specifiques purchase (pas de compteur de calculs, pas de latence par scenario). |
| Audit trail backend | Pas de persistence des decisions dans le backend. Seul l'audit trail front-end Brique 3 (`audit.js`) est en memoire. |

---

## 9. Recommandations V2 (3 blocs max)

### Bloc 1: Unifier et connecter les 2 pages

**Probleme**: 2 pages paralleles (PurchasePage + PurchaseAssistantPage) avec zero partage de code ou de donnees.

**Recommandation**:
- Fusionner en une seule page `/achats` avec un switch "Quick" (3 clics, backend) / "Expert" (wizard complet, Monte Carlo)
- Le mode Quick reutilise le backend existant (14 endpoints)
- Le mode Expert appelle les memes endpoints + fait le Monte Carlo en front en complement
- Partager le `dataAdapter.js` pour alimenter les deux modes depuis le Patrimoine reel
- Supprimer les demo orgs hardcodees de `demoData.js` — utiliser le seed backend

### Bloc 2: Corriger les 3 P0 avant toute demo

| Action | Effort | Impact |
|--------|--------|--------|
| Remplacer `computePortfolio(1)` par `computePortfolio(effectiveOrgId)` | 5 min | Portfolio multi-site fonctionne pour toute org |
| Ajouter `useSearchParams` pour lire `?filter=renewal\|missing` et setter l'onglet actif | 15 min | Deep-links Cockpit → Achats fonctionnent |
| Connecter PurchaseAssistantPage au ScopeContext pour charger les sites reels | 2h | L'Assistant utilise le patrimoine reel |

### Bloc 3: Enrichir la data pour credibilite

| Action | Effort | Impact |
|--------|--------|--------|
| Seed table `market_prices` avec 12 mois EPEX Spot FR (CSV statique) | 1h | Le prix de reference n'est plus un fallback 0.18 |
| Integrer `referential_tarifs_taxes.md` existant dans un YAML referentiel | 2h | Le breakdown Brique 3 utilise des valeurs reelles (TURPE, CSPE, CTA) |
| Bridge `purchase_service.estimate_consumption` ← donnees conso reelles (quand disponibles) | 30 min | Deja fait via MeterReading/Invoice, OK |

---

## 10. Backlog ICE (10 items)

| # | Item | Impact (1-10) | Confiance (1-10) | Effort (j) | ICE Score |
|---|------|--------------|-------------------|-----------|-----------|
| 1 | Fix org_id hardcode dans PurchasePage (P0-1) | 10 | 10 | 0.1 | 1000 |
| 2 | Ajouter useSearchParams pour filter deep-links (P0-2) | 9 | 10 | 0.2 | 450 |
| 3 | Ajouter auth sur PATCH /accept et POST /seed-* (P1-1, P1-2) | 8 | 10 | 0.2 | 400 |
| 4 | Connecter Assistant Achat au ScopeContext (P0-3) | 9 | 7 | 1 | 63 |
| 5 | Seed table market_prices (12 mois EPEX Spot FR) | 7 | 9 | 0.5 | 126 |
| 6 | Ajouter tooltip explainability sur prix/risque | 6 | 9 | 0.5 | 108 |
| 7 | Rendre module "Marche" visible en mode normal (simplifie) | 8 | 7 | 1 | 56 |
| 8 | Fusionner PurchasePage + PurchaseAssistantPage | 8 | 6 | 3 | 16 |
| 9 | Bridge breakdown TURPE/CSPE vers referentiel YAML | 5 | 8 | 1 | 40 |
| 10 | Ajouter verification startup routes purchase (comme billing) | 4 | 10 | 0.1 | 400 |

---

## 11. Plan de tests smoke (5 scenarios)

### Scenario 1: Simulation mono-site bout-en-bout
1. Login → activer mode Expert → naviguer vers "Achats energie"
2. Selectionner un site dans le dropdown
3. Verifier que l'estimation conso et le profil s'affichent (section 1)
4. Modifier le volume (section 2) → "Sauvegarder"
5. Cliquer "Calculer les scenarios" → verifier 3 cartes (Fixe/Indexe/Spot)
6. Verifier qu'un scenario porte le badge "Recommande"
7. Cliquer "Accepter" → verifier le badge "Accepte"
8. **Expected**: flow complet sans erreur console, toast de succes

### Scenario 2: Portfolio multi-site
1. Seeder un dataset WOW (happy) via l'onglet Portefeuille
2. Cliquer "Calculer le portefeuille"
3. Verifier les 4 KPIs (sites, cout, risque, economies)
4. Verifier le tableau par site
5. Cliquer "Exporter Pack RFP" → verifier que la fenetre print s'ouvre
6. **Expected**: KPIs coherents, tableau complet, PDF A4 lisible

### Scenario 3: Deep-link Cockpit → Echeances
1. Depuis le Cockpit (Vue executive), cliquer sur un CTA "Renouvellement" (si affiche)
2. Verifier que PurchasePage s'ouvre sur l'onglet "Echeances"
3. Verifier que les contrats expirants sont affiches avec badges urgence
4. **Expected**: Actuellement echoue (P0-2). Apres fix: onglet Echeances pre-selectionne.

### Scenario 4: Assistant Achat (Brique 3) — Wizard complet
1. Naviguer vers "Assistant Achat"
2. Step 1: selectionner 2+ sites demo → Suivant
3. Step 2: verifier volumes agreges → Suivant
4. Step 3: choisir Persona "DAF" → Suivant
5. Step 4: garder defaults → Suivant
6. Step 5: verifier les 5 offres demo → Suivant
7. Step 6: verifier corridor Monte Carlo (P10/P50/P90)
8. Step 7: verifier scoring multi-dimension
9. Step 8: verifier recommandation + export Note de Decision
10. **Expected**: wizard complet, pas d'erreur, exports fonctionnels

### Scenario 5: Robustesse — site sans donnees
1. Creer un site vide (pas de compteur, pas de facture, pas de contrat)
2. Naviguer vers "Achats energie" → selectionner ce site
3. Verifier que l'estimation fallback (500k kWh) s'affiche
4. Cliquer "Calculer" → verifier que les scenarios utilisent le fallback
5. Aller sur l'onglet Echeances → verifier "Aucun contrat"
6. **Expected**: pas de crash, fallbacks appliques, messages empty state corrects

### Suggestions de tests automatises (sans les ecrire)

| # | Type | Cible | Assertion |
|---|------|-------|-----------|
| 1 | Unit (vitest) | `domain/purchase/engine.js:runEngine()` | 3 offres → 3 resultats, memoisation fonctionne, clear cache force recalcul |
| 2 | Unit (vitest) | `domain/purchase/scoring.js:scoreOffer()` | Offre "dirty" obtient un score inferieur a l'offre "fixe" |
| 3 | Unit (vitest) | `models/purchaseSignalsContract.js:normalizePurchaseSignals()` | Input null → EMPTY, input valide → signaux normalises |
| 4 | Integration (pytest) | POST `/api/purchase/compute/{site_id}` | Retourne 3 scenarios, 1 recommande, run_id UUID, persistance en DB |
| 5 | Integration (pytest) | GET `/api/purchase/renewals` avec auth → org_id auto-resolu | Retourne contrats filtres par org |
| 6 | E2E (playwright) | Scenario 1 complet (simulation mono-site) | Select site → Calculate → Accept → verify badges |
| 7 | E2E (playwright) | Deep-link `/achat-energie?filter=renewal` | Onglet Echeances pre-selectionne (apres fix P0-2) |
| 8 | Regression (vitest) | PurchasePage ne contient aucun `computePortfolio(1)` hardcode | `expect(source).not.toContain('computePortfolio(1)')` |
| 9 | Contract (pytest) | Tous les endpoints `/api/purchase/*` retournent du JSON (pas HTML) | `assert response.headers['content-type'].startswith('application/json')` |
| 10 | Smoke (pytest) | `GET /api/purchase/estimate/999999` → retourne fallback, pas 500 | `assert response.status_code == 200` |

---

## Annexe A: Arbre des fichiers de la brique Achat

```
backend/
  routes/purchase.py              # 16 endpoints, 778 lignes
  services/purchase_service.py    # 7 fonctions, 338 lignes
  services/purchase_actions_engine.py  # 1 fonction (compute_purchase_actions)
  services/purchase_seed.py       # seed_purchase_demo (2 sites)
  services/purchase_seed_wow.py   # seed_wow_happy + seed_wow_dirty (15 sites)
  models/purchase_models.py       # 3 tables, 151 lignes
  tests/test_purchase.py          # 25 tests

frontend/src/
  pages/PurchasePage.jsx                # 757 lignes, 4 onglets
  pages/PurchaseAssistantPage.jsx       # ~1400 lignes, wizard 8 steps
  domain/purchase/                       # 12 fichiers, ~2000 lignes total
    index.js, types.js, assumptions.js, engine.js, risk.js,
    scoring.js, recommend.js, scenarioLibrary.js, rfp.js,
    audit.js, demoData.js, dataAdapter.js
  domain/purchase/__tests__/engine.test.js
  components/PurchaseErrorBoundary.jsx
  components/PurchaseDebugDrawer.jsx
  components/ExportNoteDecision.jsx
  components/ExportPackRFP.jsx
  models/purchaseSignalsContract.js
  services/api.js (L655-674)            # 16 fonctions API purchase
```

## Annexe B: Dependances cross-briques

```
Achat Energie (Brique 2+3)
  ├── depends on: Patrimoine (sites, org, portefeuille) — OK via get_org_site_ids()
  ├── depends on: Billing (contrats, ref_price) — OK via billing_service.get_reference_price()
  ├── depends on: Conso (MeterReading, Invoice) — OK via estimate_consumption()
  ├── depends on: ScopeContext (orgId, siteId) — PARTIELLEMENT (P0-1)
  ├── feeds: Cockpit (purchaseSignalsContract) — OK
  ├── feeds: Dashboard 2min (achat block) — OK
  ├── feeds: Action Hub (purchase_actions_engine) — OK
  └── feeds: Audit Report PDF (section achat) — OK
```

---

**FIN DE L'AUDIT — Aucune modification du code applicatif effectuee.**
