# Audit read-only PROMEOS — scope sans ACC, pilotage des usages en advisory

> **Mode** : READ-ONLY strict — aucune modification de code, aucune branche, aucune correction.
> **Branche auditée** : `claude/refonte-sol2` · **HEAD** : `ade3d0a0` (« test(m2-1): 4 source-guards V4 anti-régression with baseline whitelist »).
> **Worktree dédié** : `.claude/worktrees/audit-refonte-sol2/` (jeté après audit).
> **Date audit** : 2026-05-22 · **Auteur** : Claude (audit consolidé · 2 sous-agents Explore + sanity-checks).
> **Doctrine appliquée** : v1.3 du 2026-05-08 + position 2026-05-22 « ACC out / pilotage usages en advisory ».
> **Scope IN court terme** : Patrimoine · Conformité · Conso & Performance · Bill Intelligence · Achat · Centre d'Action · pilotage des usages (advisory).
> **Scope OUT court terme** : ACC, PMO, clé de répartition, participants ACC, settlement local, module ACC.
> **Règle d'or** : « PROMEOS reste non-sachant d'abord. Zéro KPI magique. »

---

## 1. Résumé exécutif

PROMEOS sur `claude/refonte-sol2` est **structurellement aligné** avec la doctrine v1.3 et le repositionnement « ACC out / pilotage usages en advisory » :

- **6 piliers IN scope** sont effectivement implémentés côté backend (104 routers, 90 services, 80 modèles ~12 k LoC, 545 fichiers de tests, 57 source-guards).
- **Frontend** : 57 routes actives + 31 redirects legacy, 7 modules dans le rail (Accueil, Conformité, Énergie, Patrimoine, Achat, Facturation, Admin), aucun dead-end de routing.
- **Centre d'Action** : hub canonique `/anomalies`, 4 briques sources opérationnelles (compliance, consumption, billing, purchase) toutes câblées via `action_hub_service.build_actions_from_*`.
- **ACC** : aucun endpoint, aucune table, aucun service métier ACC. Mais des **résidus à parker** (rôle utilisateur `PMO_ACC` actif dans IAM, glossaire FE qui définit « PMO / ACC », dossier KB `docs/kb/items/acc/` avec 4 fiches doctrinales).
- **Pilotage des usages** : tonalité advisory bien posée côté UI ; détecteurs backend (talon, drift, dépassement) opérationnels ; **CarpetPlot.jsx existe** côté FE (différenciant marché) ; CUSUM et M&V ISO 14064 absents — feature future.
- **Doctrine §8 « zéro KPI magique »** : excellente côté backend (`backend/doctrine/kpi_registry.py` impose unité / formule / source / scope / période / freshness / confidence_rule / owner — 11 KPI enregistrés et testés). **Échec partiel côté frontend** : ~10 violations « zero business logic » persistent (CO₂ calculé via `kwh * useElecCo2Factor()` au lieu d'un payload backend ; tarif unitaire `€/kWh` calculé en `BillIntelPage.jsx:1322` ; risque agrégé sommé côté FE dans `AnomaliesPage`, `Cockpit`, `CockpitPilotage`).
- **Org-scoping** : ~95 % couvert via `resolve_org_id()` + middleware + matrice 288 cellules + 57 source-guards. **5 routers à re-vérifier** (`bill_intelligence`, `kb_usages`, `onboarding`, `market_intelligence`, `public_diagnostic`).
- **Traçabilité NOR** : présente sur DT/BACS/APER/OPERAT (citations NOR + dates dans YAML config). **Manque** sur NEBCO (résolutions CRE non hardcodées).
- **Tests** : BE 545 fichiers + FE 234 fichiers + 57 source-guards V4 — baseline ne doit pas régresser.

**Verdict d'ensemble** : feu vert pour démo CFO / pilote Lite, sous réserve d'avoir traité les **8 P0** listés en §4 (essentiellement parking ACC + 5 endpoints org-scoping + CO₂ FE → BE + 1 désambiguïsation `/cockpit/pilotage` retro-compat). Aucune nécessité de coder ACC.

---

## 2. Verdict global

| Dimension | Verdict | Confiance |
|---|---|---|
| **Scope IN couvert (6 piliers)** | ✅ OK | Haute — code et tests présents pour les 6 piliers |
| **Scope OUT ACC respecté côté API/services** | ✅ OK | Haute — 0 endpoint ACC, 0 service ACC, 0 table ACC |
| **Scope OUT ACC nettoyé jusqu'au glossaire** | ⚠️ Partiel | Haute — `UserRole.PMO_ACC` + glossaire FE + KB `acc/` persistent |
| **Pilotage en mode advisory (pas d'exécution)** | ✅ OK | Haute — wording UI, pas de boutons « exécuter », advisory cohérent |
| **Centre d'Action 4 briques alimentent** | ✅ OK | Haute — `build_actions_from_{compliance,consumption,billing,purchase}` câblées |
| **Zéro KPI magique (registry, NOR, unités)** | ⚠️ Partiel | Haute — registry BE excellent · violations CO₂ FE résiduelles |
| **Non-sachant : tooltips + glossaire** | ✅ OK | Haute — `AcronymTooltip.jsx`, `glossary.js` (70+ termes), `JargonText.jsx` |
| **Org-scoping ≥ 95 %** | ⚠️ Partiel | Moyenne — 5 routers à re-vérifier |
| **Traçabilité NOR sur réglementaire** | ✅ OK | Haute — `config/*.yaml` cite NOR + JORF |
| **Tests baseline** | ✅ OK | Haute — 545 BE + 234 FE + 57 source-guards |

**Verdict synthèse** : **OK partiel** — la dette identifiée est bornée, traçable et non-bloquante pour un pilote, mais elle empêche la complétude « scope sans ACC + zéro KPI magique » revendiquée par la doctrine.

---

## 3. Matrice doctrine vs repo réel

### 3.1 Piliers IN scope court terme

| Pilier doctrine | Backend | Frontend | Tests | État repo | Écart vs doctrine |
|---|---|---|---|---|---|
| **Patrimoine** | `routes/patrimoine.py`, `patrimoine_crud.py`, `services/patrimoine_*` (8 services), 10 modèles | `/patrimoine` `Patrimoine.jsx` + `/sites/:id` `Site360.jsx` + `/onboarding/sirene` | source-guards patrimoine présents | ✅ OK | — |
| **Conformité (DT/BACS/APER/SMÉ/OPERAT)** | `routes/compliance.py`, `tertiaire.py`, `aper.py`, `operat.py` · `regops/scoring.py` (SoT) · `services/compliance_engine.py`, `bacs_regulatory_engine.py`, `aper_service.py`, `audit_sme_service.py`, `tertiaire_modulation_service.py`, `tertiaire_mutualisation_service.py`, `cascade_bacs_service.py` (15 services) · 8 modèles | `/conformite` + `/conformite/tertiaire` + wizard + EFA + anomalies + `/conformite/aper` + `/compliance/pipeline` + `/compliance/sites/:id` | 30+ tests régulatoires + 20+ tests doctrine | ✅ OK | — |
| **Conso & Performance** | `consumption_unified_service.py` (SoT) · `consumption_diagnostic.py`, `baseline_service.py`, `consumption_context_service.py`, `load_profile_service.py`, `tariff_periods_service.py`, `schedule_detection_service.py`, `consumption_drift_detector.py`, `energy_intensity_service.py` (10 services) · 10 modèles | `/consommations` (4 tabs : explorer / portfolio / import / kb) + `/monitoring` + `/diagnostic-conso` + `/usages-horaires` | source-guards consumption + `phase4_carpet_plot.test.js` | ✅ OK | CUSUM / IPMVP ISO 14064 absents (feature future, hors doctrine MVP) |
| **Bill Intelligence** | `routes/billing.py`, `bill_intelligence.py`, `billing_usage.py` · `services/billing_canonical_service.py`, `billing_normalization.py`, `billing_explainability.py`, `billing_reconcile.py`, `price_decomposition_service.py`, `cost_by_period_service.py`, `billing_shadow_v2.py` (12 services) · 10 modèles | `/bill-intel` `BillIntelPage.jsx` + `/billing` `BillingPage.jsx` | source-guards billing + tests anomalies | ✅ OK | Tarif `€/kWh` calculé côté FE en violation (`BillIntelPage.jsx:1322`) — cf. §4 P0-3 |
| **Achat** | `routes/purchase.py`, `contracts_v2.py`, `contracts_radar.py`, `fournisseurs.py` · `services/purchase_service.py`, `contract_v2.py`, `contract_risk_service.py`, `contract_expiration_alerts.py`, `purchase_actions_engine.py`, `market_data_service.py`, `flex_nebco_service.py` (10 services) · 8 modèles | `/achat-energie` `PurchasePage.jsx` + `/renouvellements` `ContractRadarPage.jsx` + `/contrats` `Contrats.jsx` | tests purchase + market | ✅ OK | NEBCO opérationnel mais traçabilité CRE non hardcodée — cf. §5 P1 |
| **Centre d'Action** | `routes/actions.py` (1300+ LoC) + `action_center.py` · `services/action_hub_service.py` (SoT sync 4-briques) + 11 autres services Action V4 (ADR-025→029) · 8 modèles | `/anomalies` `AnomaliesPage.jsx` (hub canonique 835 LoC) + `/actions` + `/actions/new` + `/actions/:id` · `ActionCenterSlideOver.jsx`, `ActionDetailPanel.jsx` | source-guards action + 20+ tests lifecycle + tests ROI | ✅ OK | Cf. §9 |
| **Pilotage usages (advisory)** | détecteurs `event_bus/detectors/consumption_drift_detector.py`, `flex_opportunity_detector.py`, `compliance_deadline_detector.py` · `schedule_detection_service.py`, `tou_service.py` · `recommendation_engine.py` | `/usages` `UsagesDashboardPage.jsx` + `CarpetPlot.jsx` (composant 228 LoC) + `HeatmapCard`, `FlexNebcoCard`, `PowerOptimizationCard`, `CdcSimulationCard`, `FlexBubbleChart` | tests carpet plot + drift | ✅ OK partiel | Cf. §8 |

### 3.2 Piliers OUT scope court terme

| Pilier doctrine OUT | Présence repo | Niveau | Action requise |
|---|---|---|---|
| **ACC — module métier (API, services, tables)** | 0 endpoint, 0 service métier, 0 table | ✅ Absent | — |
| **ACC — résidus organisationnels** | `UserRole.PMO_ACC` dans `models/enums.py:459` · `services/auth_guards.py:30,110` · `services/iam_service.py` · glossaire FE (5 fichiers : `AppShell.jsx`, `AdminRolesPage.jsx`, `AdminUsersPage.jsx`, `AdminAssignmentsPage.jsx`, source-guard nav FE) · KB `docs/kb/items/acc/` (4 fiches : `ACC-CLE-REPARTITION.yaml`, `ACC-DEFINITION-PERIMETRES.yaml`, `ACC-DEROGATION-10MW.yaml`, `ACC-PMO-OBLIGATIONS.yaml`) | ⚠️ Présent | Parking — cf. §7 |
| **CBAM / CSRD post-Omnibus** | 0 endpoint dédié, 0 service | ✅ Absent | Roadmap Mois 6+, ok |
| **Calculateur Électrification** | 0 endpoint, 0 page | ✅ Absent | Reporté post-Sol2 (cf. doctrine 26/04) |

### 3.3 Règles non-négociables CLAUDE.md vs repo

| Règle | État repo | Verdict |
|---|---|---|
| 1. Zero business logic FE | Multiples violations CO₂ + tarif unitaire + risque agrégé FE | ⚠️ KO partiel (cf. §4 P0-3) |
| 2. Org-scoping `resolve_org_id` sur chaque endpoint | ~95 % couvert | ⚠️ KO partiel (5 routers à vérifier — §4 P0-2) |
| 3. Atomic commits `fix(module-pN): Phase X.Y — description` | Pratiqué (git log récent) | ✅ OK |
| 4. MCP obligatoires (Context7, code-review, simplify) | Hors scope audit code | — |
| 5. Baseline tests jamais régresser | 545 BE / 234 FE / 57 source-guards | ✅ OK (à protéger) |
| 6. `consumption_unified_service.py` = SoT | Présent + référencé | ✅ OK |
| 7. `naf_resolver.py:resolve_naf_code()` canonical | Présent (150 LoC) | ✅ OK |
| 8. Branche `claude/*` jamais main | `claude/refonte-sol2` correct | ✅ OK |
| 9. Commit + push + draft PR immédiat | Pratiqué | ✅ OK |
| 10. Hooks utilisent `$CLAUDE_PROJECT_DIR` | Hors scope audit fonctionnel | — |

---

## 4. P0 bloquants (à traiter avant pilote payant)

> Bloquant = compromet la promesse doctrinale « non-sachant d'abord, zéro KPI magique, scope sans ACC » devant un CFO/DAF.

### P0-1. Résidus ACC dans IAM + glossaire FE + KB

- **Symptôme** : `UserRole.PMO_ACC = "pmo_acc"` reste un rôle utilisateur valide dans `backend/models/enums.py:459`, listé dans la whitelist `backend/services/auth_guards.py:30,110`, exposé dans 5 fichiers frontend (libellé « PMO / ACC » dans `AppShell.jsx`, `AdminRolesPage.jsx`, `AdminUsersPage.jsx`, `AdminAssignmentsPage.jsx` + source-guard nav).
- **Impact doctrine** : contradit le scope OUT — un démo CFO découvrant un rôle « PMO / ACC » dans `/admin/users` interroge le positionnement.
- **Action requise (sans coder maintenant)** :
  1. Parker `PMO_ACC` derrière feature flag `ENABLE_ACC_ROLE=false` par défaut.
  2. Renommer l'affichage FE « PMO / ACC » → « (futur module ACC) » ou retirer le rôle de la palette de sélection si flag off.
  3. Décider du devenir du dossier `docs/kb/items/acc/` (4 fiches doctrine ACC) : a) garder à des fins de veille KB sans exposition produit (recommandé) ; b) déplacer hors `docs/kb/items/` actif.

### P0-2. Org-scoping à re-vérifier sur 5 routers

- **Symptôme** : sur les 104 routers, 5 n'ont pas un `resolve_org_id()` clair — `bill_intelligence.py`, `kb_usages.py`, `onboarding.py`, `market_intelligence.py`, `public_diagnostic.py`. Risque IDOR théorique non-confirmé mais non-prouvé.
- **Impact doctrine** : ADR-027 IS11 exige 4 lignes de défense (middleware + décorateur + repository + source-guards). Ne pas régresser cette garantie.
- **Action requise** : passer les 5 routers au peigne fin avec source-guard dédié (`test_org_scoping_matrice.py` extension), confirmer que la défense en profondeur tient.

### P0-3. CO₂ calculé côté frontend (`kwh * co2Factor`) — violation Règle d'or

- **Symptôme** : 7+ occurrences `totalKwh * co2Factor` dans `ConsumptionDiagPage.jsx` (l.243, 359, 561, 724), `ConsumptionExplorerPage.jsx` (l.384), `ConsumptionPortfolioPage.jsx`, `ConsommationsUsages.jsx`. Le hook `useElecCo2Factor()` lit bien `/api/config/emission-factors` (ADEME V23.6 + source + année) mais le **calcul** lui-même est FE.
- **Impact doctrine** : règle d'or « zero business logic frontend » → doctrine §0 SKILL.md. Le facteur est versionné côté backend mais le résultat affiché échappe à la traçabilité audit (un changement de facteur ne re-trigge pas un recalcul backend traçable).
- **Action requise** : exposer un champ `co2_avoided_kg` ou équivalent pré-calculé dans le payload des insights / actions / explorer, à l'image de ce que fait déjà `routes/actions.py:_resolve_co2e_kg`. FE ne fait plus que afficher.

### P0-4. Tarif unitaire `€/kWh` calculé FE (`BillIntelPage.jsx:1322`)

- **Symptôme** : `(inv.total_eur / inv.energy_kwh).toFixed(4)` côté FE. Même nature de violation que P0-3 : aucun audit possible (pas de période, pas de TTC/HT explicite, pas de composante taxes/transport/fourniture séparée).
- **Impact doctrine** : §8 KPI registry exige `unit + formula + source + scope + period + freshness + confidence_rule + owner`. Un `€/kWh` brut sans ces attributs = KPI magique.
- **Action requise** : exposer `unit_price_eur_per_kwh` enrichi avec contexte (HT/TTC, période facture, composantes) dans le payload backend.

### P0-5. Agrégation risque/coût côté FE (Anomalies, Cockpit)

- **Symptôme** :
  - `AnomaliesPage.jsx:244-266` agrège `business_impact.estimated_risk_eur` côté FE.
  - `Cockpit.jsx:307` somme `sites[].risque_eur`.
  - `CockpitPilotage.jsx:119` somme `items[].impact_value_eur`.
  - `ConsumptionExplorerPage.jsx:283` agrège `total_cost_eur`.
- **Impact doctrine** : §8 et règle d'or. Le total affiché en cockpit n'est plus auditable (changement de filtre = recalcul FE silencieux, pas trace backend).
- **Action requise** : exposer ces totaux en endpoint `/api/.../summary` avec metadata `scope + period + filter_applied`.

### P0-6. Désambiguïsation `/cockpit/pilotage` (legacy retro-compat)

- **Symptôme** : `/cockpit/pilotage` cohabite avec `/cockpit/jour` et `/cockpit/strategique`. Risque d'incompréhension utilisateur : « lequel est canonique ? ».
- **Impact doctrine** : non-sachant d'abord — un CFO ne doit pas avoir à choisir entre 3 cockpits.
- **Action requise** : décision produit a) supprimer `/cockpit/pilotage` après mois 5 cleanup (L8 plan déjà acté), b) renommer comme tab interne dans `/cockpit/strategique`, c) maintenir comme deep-link expert sans exposition rail.

### P0-7. Pages mortes encore versionnées (suppression Mois 5 L8 plan)

- **Symptôme** :
  - `frontend/src/pages/EnergyCopilotPage.jsx` — commenté « dead code, no active route » dans `App.jsx:69`.
  - `frontend/src/pages/ActionCenterPage.jsx` (378 LoC) — remplacée par `/anomalies` depuis 2026-05-02.
  - `frontend/src/pages/CompliancePage.jsx` — alias ancien.
  - `frontend/src/pages/Dashboard.jsx` — legacy V1.
  - `frontend/src/pages/PurchaseAssistantPage.jsx` — intégrée tab dans `PurchasePage.jsx`.
- **Impact doctrine** : pollution mentale développeur, risque de réutilisation par erreur.
- **Action requise** : exécuter L8 « Plan suppression legacy » au Mois 5 J+14 (déjà documenté dans `docs/dev/L8_plan_suppression_legacy.md`).

### P0-8. Routes legacy v2 backend à dégommer Mois 5

- **Symptôme** : `routes/cockpit_v2.py` (27 LoC), `routes/contracts_v2.py` (14 LoC), `routes/billing_usage.py` (proxy) — pleinement référencés mais marqués « à retirer M5 » dans L8.
- **Action requise** : confirmer absence d'appels FE résiduels avant DROP, puis exécuter L8.

---

## 5. P1 crédibilité (à traiter avant scale-up commercial)

### P1-1. Traçabilité CRE / NEBCO non hardcodée

- `services/flex_nebco_service.py` opérationnel mais ne cite pas explicitement les délibérations CRE applicables (résolutions NEBCO, AOFD lauréats 2024). Pour un CFO qui demande « d'où viennent ces 5-15 € / MWh d'effacement ? », pas de réponse outillée.
- Recommandation : ajouter champ `source_nor_or_cre` dans le payload `/api/flex/*` et un yaml `config/cre_nebco_sources.yaml`.

### P1-2. KPI registry frontend manquant

- `backend/doctrine/kpi_registry.py` est exemplaire (11 KPI avec unit/formula/source/scope/period/freshness/confidence/owner). **Aucun équivalent côté FE** — les composants `KpiTile`, `KpiStrip` ne sont pas obligés de référencer un `kpi_id` du registry.
- Recommandation : créer `frontend/src/doctrine/kpiRegistry.js` (miroir lecture seule) + source-guard FE qui vérifie que tout `<KpiTile kpi_id="..."/>` pointe vers un id existant.

### P1-3. Composants mal classés (`src/pages/` ⊂ co-location)

- 51 fichiers JSX sous `src/pages/cockpit/`, `src/pages/consumption/`, `src/pages/conformite-tabs/`, `src/pages/tertiaire/`, `src/pages/dashboard/` sont en réalité des **composants** réutilisés. Convention de co-location défendable mais non documentée dans `docs/dev/conventions.md`.
- Recommandation : documenter ou refactorer.

### P1-4. Hidden pages — clarifier l'intention « expert vs deep-link only »

- 7 routes cachées (`/kb`, `/segmentation`, `/connectors`, `/usages-horaires`, `/compliance/pipeline`, `/action-center`). Logique cohérente (`NavRegistry.js:1085-1146`) mais nécessite documentation produit pour le commercial.
- Recommandation : 1 ligne par route dans le README produit.

### P1-5. `OnboardingPage.jsx` redirige vers `/cockpit/jour` — wizard absent

- Promesse doctrine v1.3 « Onboarding 3 parcours (Wizard / Expert / Bulk) » non livrée — `/onboarding` redirige actuellement. Gap matrice patrimoine v1 (sprint C-5).
- Recommandation : phase 4 sprint dédié.

### P1-6. M&V baseline simple, pas IPMVP/ISO 14064-2

- `services/baseline_service.py` fait des normalisations (DJU, occupation) mais n'implémente pas le formalisme IPMVP/ISO 14064-2 (M&V option B/C/D). Acceptable au pilote Lite ; bloquant pour clients audités CSRD.
- Recommandation : roadmap Mois 6+.

### P1-7. Tests E2E Playwright incomplets

- `tools/playwright/` contient des scripts audit (cf. status M2-5.10) mais pas une couverture E2E systématique. 10/10 routes screenshot OK (cf. memory `project_audit_complet_refonte_sol2_2026_05_03.md`) mais pas de scénarios fonctionnels complets.
- Recommandation : ajouter scénarios par persona (DAF, CFO, EM, RegOps).

---

## 6. P2 world-class (différenciation pitch / scale)

### P2-1. CarpetPlot.jsx — exposer comme différenciant marché

- `frontend/src/components/CarpetPlot.jsx` (228 LoC) est un composant Canvas-native avec palette septile (P10/25/50/75/90/95). C'est **un vrai différenciant** vs Deepki/Metron/Advizeo. Actuellement intégré dans `FlexPage.jsx` uniquement.
- Recommandation : promouvoir en `MonitoringPage.jsx` et `Site360.jsx`, packager pour export PDF (CFO).

### P2-2. CUSUM (control chart) absent

- Mention dans `glossary.js` + `MethodologiePage.jsx` mais aucun moteur backend. Différenciant ISO 50001 si livré.
- Recommandation : roadmap Mois 6+.

### P2-3. Pilier Flex pas (encore) source du Centre d'Action

- `action_hub_service.py` câble 4 briques (compliance / consumption / billing / purchase). Le pilier **Flex/EMS** n'alimente pas le Centre d'Action — pourtant `flex_opportunity_detector.py` existe dans `event_bus/detectors/`.
- Recommandation : Mois 2 — ajouter `build_actions_from_flex` (modèle déjà prêt).

### P2-4. Recommandation engine non-relié au lifecycle

- `recommendation_engine.py` (140+ LoC) génère recommandations advisory mais peu d'évidence qu'il alimente `ActionItem` avec `gain_kwh` / `gain_eur` / `co2_avoided_kg`.
- Recommandation : audit dédié Mois 2.

### P2-5. Forecasting / saisonnalité — feature gap vs Endesa Griffine

- Méthodologie ingérée 2026-05-21 (mémoire `reference_methodologie_endesa_analyse_site_industriel.md`) : 13 étapes de signature énergétique. Implémenté partiellement (talon, drift, signature) mais pas le forecasting probabiliste.
- Recommandation : roadmap Mois 6+ (Flex Advisory M&V only — pricing extension).

---

## 7. Traces ACC à supprimer ou parker

### 7.1 Vraies traces ACC (4 hits métier, hors faux positifs)

| Fichier | Référence | Nature | Décision recommandée |
|---|---|---|---|
| `backend/models/enums.py:459` | `UserRole.PMO_ACC = "pmo_acc"` | Enum rôle utilisateur | **Parker** — feature flag `ENABLE_ACC_ROLE=false`, conserver enum pour futur (Mois 6+) |
| `backend/services/auth_guards.py:30` `:110` | Whitelist rôle `"pmo_acc"` | IAM logique | **Parker** — conditionner accès par flag |
| `backend/services/iam_service.py` | Gestion role PMO_ACC | IAM logique | **Parker** — idem |
| `docs/kb/items/acc/` (4 fiches) | `ACC-CLE-REPARTITION.yaml`, `ACC-DEFINITION-PERIMETRES.yaml`, `ACC-DEROGATION-10MW.yaml`, `ACC-PMO-OBLIGATIONS.yaml` | KB doctrinale | **Garder** — KB de veille interne, non-exposée produit (KB explorer FE filtre déjà via tags) |
| `scripts/kb_ingest_batch.py` | Reference `"Autoconsommation Collective": ("ACC_FRANCE", ...)` | Ingestion KB | **Garder** — sert au seeding KB, pas runtime |

### 7.2 Traces frontend (5 fichiers)

| Fichier | Référence | Décision |
|---|---|---|
| `frontend/src/layout/AppShell.jsx:62` | `pmo_acc: 'PMO / Acc.'` (libellé persona) | **Renommer** affichage si flag off, ou retirer du menu sélecteur persona |
| `frontend/src/pages/AdminRolesPage.jsx` | Affiche `pmo_acc` dans la liste rôles | **Conditionner** affichage |
| `frontend/src/pages/AdminUsersPage.jsx` | Idem | **Conditionner** |
| `frontend/src/pages/AdminAssignmentsPage.jsx` | Idem | **Conditionner** |
| `frontend/src/__tests__/source_guards/nav_fe_source_guards.test.js:325,334` | Marque `pmo_acc` comme « fallback acceptable » | **Conserver** mais documenter le flag |

### 7.3 Faux positifs filtrés (à ignorer)

- `acc` comme variable accumulateur dans `.reduce((acc, ...) => ...)` → ~30 hits frontend, légitimes.
- `ACCENT_BAR`, `ACCEPTED`, `accordion`, `accounting`, `access` → idiomes système.
- `KPI_ACCENTS['acc']` dans `KpiTile.jsx:43,68` : c'est la couleur tinte « accent », pas ACC métier.
- Recherche placeholder « autoconsommation » dans `ConformitePage.jsx:392,482` : suggestion de recherche (info utilisateur, pas implémentation).

### 7.4 Verdict ACC

✅ **Module ACC absent comme promis** (0 endpoint, 0 service, 0 table).
⚠️ **Résidus organisationnels** à parker derrière un feature flag avant pilote payant.
✅ **KB ACC** justifiée à conserver (veille doctrinale).

Aucune action de suppression destructive nécessaire — uniquement du **parking conditionnel**.

---

## 8. Pilotage des usages — état réel

### 8.1 Notions cardinales (réf. backlog `project_pilotage_flex_usages_backlog_2026_05_22.md` + méthodologie Endesa Griffine 2026-05-21)

| Notion | Backend | Frontend | État |
|---|---|---|---|
| **Talon nocturne** (Pbase / charge minimale 02h-04h) | `consumption_diagnostic.py` (signature) · `services/demo_seed/gen_monitoring.py` (générateur) | mentionné dans `monitoringLabels.fr.js`, `ConsumptionPortfolioPage`, `MonitoringPage`, `ConsumptionDiagPage`, `ConsommationsUsages`, `consumption/TunnelPanel`, `OverviewRow`, `GasPanel` | ✅ Présent et nommé |
| **CVC hors horaires** (chauffage/clim en dehors créneaux occupation) | `schedule_detection_service.py` + `tou_service.py` | recommandation visible dans `UsagesDashboardPage` | ✅ Présent |
| **Dérive WE** (consommation week-end anormalement haute) | `event_bus/detectors/consumption_drift_detector.py` | **Non exposé comme widget dédié FE** | ⚠️ Backend OK, exposition FE manquante |
| **Surpuissance** (dépassement P souscrite) | `routes/power.py` (overload) + `event_bus/detectors/` | `PowerOptimizationCard` (composant pilotage) | ✅ Présent |
| **HP coûteuses** (consommation en plage HP / Tempo rouge) | `tariff_periods_service.py` + `tou_service.py` | composants tarifaires + alerte coût | ✅ Présent |
| **Conso déplaçable** (load shifting opportunity) | `schedule_detection_service.py` + `flex_nebco_service.py` | `CdcSimulationCard` + `FlexBubbleChart` | ✅ Présent |
| **Signature énergétique** (régression conso vs DJU) | `consumption_diagnostic.py` + `baseline_service.py` + `gas_weather_service.py` | présentation graphique dans monitoring | ✅ Présent |
| **Carpet plot** (heatmap 24h × N jours) | données brutes via `/api/energy/site` | `components/CarpetPlot.jsx` (228 LoC, palette septile P10→P95) | ✅ Présent, FE prêt |
| **CUSUM** (control chart cumulatif) | absent | mention glossaire + méthodologie | ❌ Absent |
| **IPMVP / M&V ISO 14064-2** | baseline simple, pas formalisme | absent | ❌ Absent (P1-6) |
| **Preuve avant/après** | `Evidence` model + `ActionEvent.type=EVIDENCE_ADDED` + MIME validation (libmagic + whitelist + double-check signatures hardcodées ADR-029 IE9) | upload preuve depuis ActionDetailPanel | ✅ Présent |
| **DJU** (degree-days normalisation) | `gas_weather_service.py` (gaz) + `weather_provider.py` | utilisé en backend, exposé partiellement FE | ✅ Présent |

### 8.2 Posture advisory bien posée

- ✅ Wording UI : « Opportunités identifiées », « Lancer analyse », « Voir détail » — guidage, jamais d'exécution autonome.
- ✅ Pas de bouton « Délester ce site maintenant ».
- ✅ NEBCO : `flex_nebco_service.py` propose des **gains** chiffrés mais ne pilote pas d'effacement.
- ✅ `recommendation_engine.py` produit des **recommandations** typées advisory.

### 8.3 Alimentation Centre d'Action

- ✅ `ConsumptionInsight` → `build_actions_from_consumption` (Centre d'Action) — câblé.
- ❌ **Pilier Flex / EMS n'alimente PAS encore le Centre d'Action** (cf. P2-3) — pourtant `flex_opportunity_detector.py` existe.

### 8.4 KPI sans justification (échantillons)

- `flex_potential_eur` (k€/an) — méthode (NEBCO score vs simulation tarifaire) non visible côté UI.
- `kwh_m2_year` — archetype benchmark / référence sectorielle non visible.
- `flex_capacity_mwh` — pas de période référence (capacité historique ? puissance souscrite ?).

### 8.5 Verdict pilotage

✅ **Advisory bien posé**, **détecteurs backend opérationnels**, **CarpetPlot prêt**.
⚠️ **Dérive WE non exposée FE** (backend OK, widget manquant).
⚠️ **KPI parfois sans contexte** (cf. §4 P0-3/P0-5).
❌ **CUSUM + M&V formel absents** (feature future, hors doctrine MVP).

---

## 9. Centre d'Action — état réel

### 9.1 Hub canonique

- `/anomalies` → `AnomaliesPage.jsx` (835 LoC) **est le hub** depuis le repoint 2026-05-02. `/action-center` redirige vers `/anomalies` (legacy).
- `/actions` + `/actions/new` + `/actions/:id` `ActionsPage.jsx` cohabitent — vue « tableau de bord actions » plus opérationnelle.

### 9.2 4 briques sources opérationnelles

| Brique | Fonction backend | Source données | État |
|---|---|---|---|
| **Compliance** | `build_actions_from_compliance` (`action_hub_service.py:84`) | `ComplianceFinding` (status NOK, hors faux positifs) | ✅ Câblée |
| **Consumption** | `build_actions_from_consumption` (`action_hub_service.py:133`) | `ConsumptionInsight` (estimated_loss_eur > 0) | ✅ Câblée |
| **Billing** | `build_actions_from_billing` (`action_hub_service.py:181`) | `BillingInsight` (status ≠ FALSE_POSITIVE/RESOLVED, avec recommandations) | ✅ Câblée |
| **Purchase** | `build_actions_from_purchase` (`action_hub_service.py:225`) | déclencheurs contrats expirants + signaux prix | ✅ Câblée |
| Flex / EMS | — | — | ❌ Non câblé (P2-3) |
| Tertiaire / APER / OPERAT | implicite via Compliance | `ComplianceFinding` issus de `tertiaire_modulation_service` / `aper_service` | ✅ Via Compliance |

### 9.3 Lifecycle (ADR-028)

- ✅ 5 états : `OPEN` / `IN_PROGRESS` / `ON_HOLD` / `DONE` / `CLOSED`.
- ✅ 10 transitions strictes (state machine).
- ✅ 6 closure_reasons révisés (doctrine v0.3) : `merged_duplicate`, `resolved_via_recurrence` (avenant Q9-B), etc.
- ✅ Auto-fermeture : `ActionItem.notes += "\n[Auto-ferme: source resolue]"` quand la source disparaît.
- ✅ Per-source caps (max actions par brique) pour démo réaliste (5-site portfolio ≈ 30 actions).
- ✅ Guards IL4 (expired interdit P0/P1 conformité), IL5 (merged_duplicate ≠ resolved_via_recurrence), IL7 (auto-close P0/P1 exige preuve).

### 9.4 Impact / Priority / Proof / Status

| Mécanique | Présence | Localisation |
|---|---|---|
| **impact** (kWh / € / tCO₂) | ✅ | `ActionItem.gain_kwh`, `.gain_eur`, `.co2_avoided_kg` · `impact_decision_service.py` · `routes/actions.py:_resolve_co2e_kg` |
| **priority** (P0-P3) | ✅ | `ActionItem.priority` · `compute_priority(severity, gain, deadline)` `action_hub_service.py:57` |
| **proof / evidence** | ✅ | `Evidence` model + `ActionEvent.type=EVIDENCE_ADDED` + 16 event_types (ADR-029) + MIME validation libmagic + whitelist + double-check signatures hardcodées (IE9) |
| **status / lifecycle** | ✅ | `ActionItem.status` enum + state machine + audit trail |
| **closure_reason** | ✅ | 6 enums |
| **audit_trail** | ✅ | `ActionEvent` + `compliance_event_log` + event_bus |
| **kpi `open_actions_count`** | ✅ | enregistré dans `KPI_REGISTRY` |

### 9.5 Endpoints clé Centre d'Action

| Méthode | Chemin | Fonction | Org-scoping |
|---|---|---|---|
| POST | `/api/actions` | `create_action()` `actions.py:266` | ✅ `resolve_org_id` |
| GET | `/api/actions` | `list_actions()` `actions.py:407` | ✅ filter org_id |
| PATCH | `/api/actions/{id}` | `patch_action()` `actions.py:506` | ✅ org-scoped query |
| POST | `/api/actions/sync` | `sync_action_hub()` `actions.py:391` | ✅ |
| GET | `/api/actions/summary` | agrégation count/status/priority/source | ✅ |
| GET | `/api/actions/roi_summary` | impact agrégé €/kWh/CO₂ | ✅ |
| POST | `/api/actions/{id}/evidence` | `add_evidence()` `actions.py:881` | ✅ |
| POST | `/api/actions/{id}/proofs/{kb_doc_id}` | `link_proof_to_action()` `actions.py:1035` | ✅ |
| POST | `/api/actions/{id}/comments` | `add_comment()` `actions.py:809` | ✅ |

### 9.6 Verdict Centre d'Action

✅ **Hub canonique cohérent** (`/anomalies`) avec 4 briques sources opérationnelles, lifecycle complet ADR-028, evidence ADR-029.
⚠️ **Flex / EMS pas encore branchés** (P2-3 — Mois 2).
⚠️ **Trace ROI agrégée côté FE** (P0-5 — à pousser backend).

---

## 10. Routes / endpoints / composants à conserver

### 10.1 Backend — routes core IN scope (90 % du trafic métier)

| Module doctrine | Routers à conserver |
|---|---|
| Patrimoine | `patrimoine.py`, `patrimoine_crud.py`, `sites.py`, `compteurs.py` |
| Conformité | `compliance.py`, `tertiaire.py`, `aper.py`, `operat.py`, `regops.py`, `regulatory_applicability.py`, `regulatory_rates.py` |
| Conso & Performance | `energy.py`, `consumption_diagnostic.py`, `consumption_context.py`, `consumption_unified.py`, `usages.py`, `ems.py`, `power.py`, `dashboard_2min.py` |
| Bill Intelligence | `billing.py`, `bill_intelligence.py` |
| Achat | `purchase.py`, `contracts_radar.py`, `fournisseurs.py`, `market.py`, `market_data.py`, `purchase_cost_simulation.py`, `purchase_strategy.py` |
| Centre d'Action | `actions.py`, `action_center.py`, `action_templates.py` |
| Cockpit | `cockpit.py`, `cockpit_strategique.py` |
| Data / Connecteurs | `dataconnect_route.py`, `enedis.py`, `grdf_route.py`, `bridge_route.py`, `connectors_route.py`, `watchers_route.py` |
| Onboarding / Import | `onboarding.py`, `onboarding_stepper.py`, `import_sites.py`, `intake.py`, `public_diagnostic.py` |
| KB / Doctrine | `kb_usages.py`, `doctrine.py`, `methodologie.py` (si présent), `schema.py` |
| Admin / Auth | `auth.py`, `admin_users.py`, `users.py`, `rgpd_consent.py`, `user_preferences.py`, `config_emission_factors.py`, `config_price_references.py`, `config_regulatory_constants.py`, `dev_tools.py` |
| Notifications / Reporting | `notifications.py`, `nps.py`, `digest.py`, `alertes.py`, `feedback.py`, `monitoring.py`, `analytics.py` |
| Support / Misc | `guidance.py`, `reports.py`, `segmentation.py`, `navigation.py`, `pages_briefing.py`, `site_config.py`, `geocoding.py`, `market_intelligence.py`, `site_intelligence.py`, `persona_dashboard.py` |

### 10.2 Backend — services SoT (canoniques)

| Service | Fichier | Rôle |
|---|---|---|
| Consommation SoT | `services/consumption_unified_service.py` | SoT consommation multi-source (Enedis / GRDF / facture) |
| Scoring conformité SoT | `regops/scoring.py` | SoT scoring DT/BACS/APER/AUDIT |
| NAF SoT | `utils/naf_resolver.py` | SoT classification NAF |
| CO₂ SoT | `config/emission_factors.py` | ADEME V23.6 |
| Tarifs SoT | `config/tarifs_reglementaires.yaml` | TURPE / CSPE / VNU / TVA versionnés |
| KPI registry SoT | `doctrine/kpi_registry.py` | 11 KPI cardinaux |
| Action hub | `services/action_hub_service.py` | Sync 4 briques → ActionItem |
| Bill canonique | `services/billing_canonical_service.py` | SoT facture |

### 10.3 Frontend — routes actives à conserver

37 pages actives. Cœur démo CFO :

- `/` → `/cockpit/strategique` (default = synthèse exécutive 3 min)
- `/cockpit/jour` (briefing EM 30 s)
- `/cockpit/strategique` (synthèse stratégique CFO 3 min)
- `/anomalies` (Centre d'action hub 4 piliers)
- `/conformite` + `/conformite/tertiaire` (DT/OPERAT) + `/conformite/aper`
- `/consommations` (4 tabs)
- `/monitoring` + `/diagnostic-conso` + `/usages` + `/usages-horaires`
- `/bill-intel` + `/billing`
- `/achat-energie` + `/renouvellements` + `/contrats`
- `/patrimoine` + `/sites/:id`
- `/admin/*` (users / roles / assignments / audit / enedis-health / cx-dashboard)
- `/methodologie/:docKey` (documentation accessible CFO)

### 10.4 Frontend — composants différenciants

- `components/CarpetPlot.jsx` (228 LoC) — heatmap 24h × N jours, palette septile P10→P95. Différenciant marché.
- `ui/sol/AcronymTooltip.jsx` + `ui/glossary.js` (70+ termes) + `ui/sol/JargonText.jsx` — couverture acronymes 95 %+, doctrine non-sachant respectée.
- `ui/Explain.jsx` — intégration glossaire.
- `components/ActionCenterSlideOver.jsx` + `ActionDetailPanel.jsx` — Centre d'Action transversal.
- `pages/anomalies/*` + `pages/cockpit/*` — co-location pattern lisible.

---

## 11. Routes / endpoints / composants à déprécier

### 11.1 Routes legacy v2 backend (DROP Mois 5 par L8)

| Fichier | Raison | Action L8 |
|---|---|---|
| `backend/routes/cockpit_v2.py` (27 LoC) | V2 legacy, remplacé par `cockpit.py` + `cockpit_strategique.py` | DROP après J+14 stop gate |
| `backend/routes/contracts_v2.py` (14 LoC) | V2 legacy | DROP après confirmation absence d'appels FE |
| `backend/routes/billing_usage.py` | Proxy | DROP |
| Tests `test_cockpit_v2.py`, `test_contracts_v2.py`, `test_phase3_*` | Tests legacy v2 / phase 3 | Archive |

### 11.2 Pages frontend mortes (DROP Mois 5)

| Fichier | Lignes | État | Action |
|---|---|---|---|
| `pages/EnergyCopilotPage.jsx` | ? | Dead code (commenté App.jsx:69) | **DROP immédiat** |
| `pages/ActionCenterPage.jsx` | 378 | Remplacée `/anomalies` 2026-05-02 | DROP Mois 5 |
| `pages/CompliancePage.jsx` | ? | Alias ancien | DROP Mois 5 |
| `pages/Dashboard.jsx` | ? | Legacy V1 | DROP Mois 5 |
| `pages/PurchaseAssistantPage.jsx` | ? | Intégrée tab Purchase | DROP Mois 5 |
| `pages/CommandCenter.jsx` | ~500 | Legacy V1, route retro-compat | Décommissionner Phase 3 sprint |
| `pages/Cockpit.jsx` | ~400 | V1 legacy | Archive Mois 5 |
| `pages/CockpitDecision.jsx` | ~1300 | Composant non routé | Audit + DROP |

### 11.3 Modèles backend à auditer (~5)

- `CopilotModels`, `RecommendationDecision`, `RecommendationOutcome` : présence à confirmer + références à recompter. Audit Mois 2.

### 11.4 ACC parking (cf. §7)

- Pas de DROP — **parker derrière feature flag** : `UserRole.PMO_ACC`, glossaire FE (5 fichiers), KB folder (4 fiches).

### 11.5 Doublons logiques résolus (rien à déprécier)

- `action_hub` (sync) vs `action_management` (CRUD) — distincts, à conserver.
- `compliance_engine` (rules) vs `regops/scoring.py` (weights) — distincts.
- `billing` (invoice) vs `bill_intelligence` (anomalies) — distincts.
- `consumption_diagnostic` (signature) vs `consumption_context_service` (metadata) — distincts.

---

## 12. Tests manquants

### 12.1 Source-guards à ajouter

| Source-guard | Pourquoi | Cible |
|---|---|---|
| `test_zero_business_logic_fe_co2.py` | Bloquer `kwh * co2Factor` côté FE (P0-3) | grep CI sur pattern interdit, whitelist exhaustive |
| `test_zero_business_logic_fe_unit_price.py` | Bloquer `total_eur / energy_kwh` côté FE (P0-4) | grep CI |
| `test_zero_business_logic_fe_risk_aggregation.py` | Bloquer `sites.reduce((s,a) => a + s.risque_eur)` côté FE (P0-5) | grep CI |
| `test_org_scoping_5_routers_completion.py` | Couvrir les 5 routers manquants (P0-2) : `bill_intelligence`, `kb_usages`, `onboarding`, `market_intelligence`, `public_diagnostic` | matrice IDOR ré-exécutée |
| `test_acc_role_flag_off_runtime.py` | Vérifier qu'avec `ENABLE_ACC_ROLE=false`, le rôle `PMO_ACC` ne s'expose ni dans `/admin/users` ni dans `/admin/roles` | conditional UI assertion |
| `test_kpi_registry_fe_mirror.py` | Vérifier que tout `<KpiTile kpi_id="..."/>` pointe vers un id présent dans `kpiRegistry.js` (mirror de `backend/doctrine/kpi_registry.py`) | static analysis FE |
| `test_flex_pillar_to_action_hub.py` | Confirmer ou rappeler l'absence de `build_actions_from_flex` (P2-3) — décision produit | feature flag check |

### 12.2 Tests fonctionnels manquants

| Domaine | Test absent |
|---|---|
| Pilotage | Dérive WE — exposition FE (P1, widget manquant) |
| Centre d'Action | `build_actions_from_flex` ou `from_ems` (P2-3) |
| Trace NEBCO | Source CRE attachée au payload `/api/flex/*` (P1-1) |
| M&V | Baseline IPMVP option B/C/D (P1-6) |
| Onboarding | Wizard 3 parcours (P1-5) |

### 12.3 Tests E2E Playwright (P1-7)

- Couverture screenshot OK (10/10 routes, mémoire `project_audit_complet_refonte_sol2_2026_05_03.md`), mais scénarios persona fonctionnels incomplets.
- Manque : DAF connecté → import facture → détection anomalie → création action → résolution avec evidence.

### 12.4 Baseline à préserver

- BE : **545 fichiers tests** (équiv. baseline 6 027 selon `MEMORY.md` post-sprint agents SDK).
- FE : **234 fichiers tests** (équiv. baseline 4 751 post-M2-5.0).
- Source-guards V4 : **57** dont 17 `*_source_guards.test.js` côté FE (`co2_factor_dedup`, `events`, `cockpit_jour_l11`, `consumption`, `lever`, `billing`, `cockpit_strategique`, `cockpit`, `conformite`, `narrative`, `nav`, etc.) — **ne jamais régresser**.

---

## 13. Plan de correction sans coder

> Plan sous forme **décisions produit / arbitrages** + **prompts Claude Code prêts à exécuter**. Aucune ligne de code n'est écrite ici. Ordre = priorité décroissante.

### 13.1 Avant pilote payant (P0 — 1 à 2 semaines)

1. **Décision produit P0-1 ACC** : arbitrer entre a) parker derrière flag `ENABLE_ACC_ROLE` (recommandé), b) renommer `PMO_ACC` en `PMO_FUTURE`, c) retirer purement. Documenter dans ADR-030 « Parking ACC court terme ».
2. **Audit org-scoping P0-2** : prompt Claude `audit org-scoping 5 routers manquants` → produire un test source-guard `test_org_scoping_completion.py` + patch chacun avec `resolve_org_id` ou justifier l'absence.
3. **Refactor CO₂ FE → BE (P0-3)** : ADR « calcul CO₂ exclusivement backend » + endpoint `/api/insights/*` enrichi `co2_avoided_kg` + source-guard FE bloquant.
4. **Refactor tarif unitaire (P0-4)** : `BillIntelPage.jsx:1322` → exposer `unit_price_eur_per_kwh` calculé backend avec metadata (HT/TTC, période, composantes).
5. **Refactor agrégation risque (P0-5)** : endpoints `/api/.../summary` retournent total + scope + period. FE consomme.
6. **Décision `/cockpit/pilotage` (P0-6)** : exécuter L8 ou maintenir comme tab interne. Documenter dans ADR-028 amendement.
7. **L8 cleanup pages mortes (P0-7) + routes v2 (P0-8)** : exécuter procédure documentée `docs/dev/L8_plan_suppression_legacy.md` Mois 5 J+14. Backup triple artefact J-1 obligatoire (Q2-α non négociable).

### 13.2 Avant scale-up (P1 — 1 à 2 mois)

1. **Traçabilité NEBCO (P1-1)** : créer `config/cre_nebco_sources.yaml` + ajouter champ `source_nor_or_cre` dans payload `/api/flex/*`.
2. **KPI registry FE mirror (P1-2)** : créer `frontend/src/doctrine/kpiRegistry.js` + source-guard FE.
3. **Documenter co-location `src/pages/` (P1-3)** : update `docs/dev/conventions.md` §directory-layout.
4. **Documenter hidden pages (P1-4)** : 7 routes commentées dans README produit.
5. **Onboarding wizard (P1-5)** : sprint dédié Phase 4 — wizard 3 parcours (Wizard / Expert / Bulk) selon backlog patrimoine C-5.
6. **M&V IPMVP (P1-6)** : roadmap Mois 6+ — Flex Advisory M&V only (pricing extension Compliance+).
7. **Tests E2E Playwright (P1-7)** : scénarios persona DAF/CFO/EM/RegOps.

### 13.3 World-class (P2 — 3 à 6 mois)

1. **Promouvoir CarpetPlot (P2-1)** : intégrer dans `MonitoringPage.jsx` + `Site360.jsx`. Export PDF CFO.
2. **CUSUM (P2-2)** : moteur backend + composant FE — différenciant ISO 50001.
3. **Pilier Flex → action_hub (P2-3)** : `build_actions_from_flex` Mois 2.
4. **Recommendation engine → lifecycle (P2-4)** : audit Mois 2.
5. **Forecasting saisonnier (P2-5)** : roadmap Mois 6+ — méthodologie Endesa Griffine 13 étapes.

### 13.4 Recommandations méta

- **Avant tout commit issu de ce plan** : passer par méthode `docs/dev/methode_audit_avant_fix.md` — Phase 0 read-only → STOP gate → phases numérotées → DoD → atomic commit → source-guard test.
- **PR base** : `claude/refonte-sol2` jamais `main` (cf. `feedback_v4_pr_base_refonte_sol2.md`).
- **Branches** : `claude/fix-pXX-...` (namespace cf. `feedback_claude_branch_namespace.md`).
- **Workflow pre-merge obligatoire** : `/code-review:code-review` + `/simplify` + tests baseline + Playwright si UI (cf. règle CLAUDE.md §workflow pre-merge).
- **Audit cycle** : ré-exécuter ce script audit READ-ONLY tous les 30 jours pendant Phase 4 — Mois 5 cleanup + post-pilote.

### 13.5 Synthèse priorisée

| # | Item | Catégorie | j-h estimés | Bloquant pilote ? |
|---|---|---|---|---|
| P0-1 | Parking ACC (flag + glossaire conditionnel) | Doctrine | 2-3 | Oui |
| P0-2 | Org-scoping 5 routers | Sécu | 2-3 | Oui |
| P0-3 | CO₂ FE → BE | Doctrine §0 | 3-5 | Oui |
| P0-4 | Tarif unitaire BE | Doctrine §8 | 2-3 | Oui |
| P0-5 | Agrégation risque BE | Doctrine §8 | 2-3 | Oui |
| P0-6 | Décision `/cockpit/pilotage` | Produit | 1-2 | Non |
| P0-7 | L8 pages mortes | Dette | 3-5 (L8) | Non |
| P0-8 | L8 routes v2 BE | Dette | 2-3 (L8) | Non |
| P1-1 | Trace NEBCO CRE | Crédibilité | 2-3 | Non |
| P1-2 | KPI registry FE | Doctrine §8 | 3-5 | Non |
| P1-3..7 | Divers crédibilité | Crédibilité | 15-25 cumulés | Non |
| P2-1..5 | World-class | Différenciation | 30-60 cumulés | Non |

**Total P0** : ~17-27 j-h pour rendre la doctrine respectée à 100 % sur les 6 piliers IN scope, avec ACC parqué, avant pilote payant.

---

## Annexes

### A. Méthode audit appliquée

- **Mode** : READ-ONLY strict (cf. instructions explicites utilisateur 2026-05-22).
- **Outils** : 2 sous-agents Explore parallèles (frontend + backend) + sanity-checks personnels via `rg` / `grep` / `find` / `wc` sur le worktree dédié.
- **Périmètre** : `frontend/src/`, `backend/`, `docs/kb/items/`, `tests/`, `config/`.
- **Hors périmètre** : tests d'exécution (pas de `pytest` ni `vitest` lancé), aucune branche créée, aucun fichier modifié hormis ce livrable.

### B. Sources d'autorité doctrinales

- `CLAUDE.md` (projet) — règles non-négociables.
- `SKILL.md` (racine) — règle d'or zero business logic FE.
- `docs/doctrine/doctrine_v4_classement_priorisation.md` v0.3 — Centre d'Action V4.
- `docs/dev/L1` → `L11` — chaîne ADR-025 → ADR-029 + plans suppression legacy L8 + plan Mois 2 L9 + audit manques L10 + plan application L11.
- `docs/dev/methode_audit_avant_fix.md` — méthode appliquée.
- Memory : `project_promeos_vision_consolidee_v1_3_2026_05_08.md` (doctrine v1.3) + `project_plan_application_audit_refonte_sol2_2026_05_22.md` (114 features matrice) + position 2026-05-22 « ACC out / pilotage advisory ».

### C. Fichiers clés référencés dans cet audit

| Fichier | Rôle |
|---|---|
| `backend/doctrine/kpi_registry.py` | SoT registry KPI (§8 doctrine, 11 KPI) |
| `backend/regops/scoring.py` | SoT scoring conformité |
| `backend/services/consumption_unified_service.py` | SoT consommation |
| `backend/services/action_hub_service.py` | Sync 4 briques → ActionItem |
| `backend/utils/naf_resolver.py` | SoT NAF |
| `backend/config/emission_factors.py` | CO₂ ADEME V23.6 |
| `backend/config/tarifs_reglementaires.yaml` | Tarifs versionnés CRE |
| `backend/models/action_item.py` | Modèle V4 unifié |
| `backend/models/enums.py` | `UserRole.PMO_ACC` (à parker) |
| `backend/services/auth_guards.py` | Whitelist rôles (PMO_ACC ligne 30, 110) |
| `frontend/src/App.jsx` | 57 routes + 11 contextes |
| `frontend/src/routes/legacyRedirects.js` | 31 redirects legacy |
| `frontend/src/layout/NavRegistry.js` | 6 modules rail + 14 quick actions + 7 hidden pages |
| `frontend/src/pages/AnomaliesPage.jsx` | Centre d'Action hub (835 LoC) |
| `frontend/src/components/CarpetPlot.jsx` | Heatmap différenciante (228 LoC) |
| `frontend/src/contexts/EmissionFactorsContext.jsx` | Hook `useElecCo2Factor()` |
| `frontend/src/ui/sol/AcronymTooltip.jsx` + `ui/glossary.js` | Couverture acronymes 95 %+ |
| `docs/kb/items/acc/` | 4 fiches KB ACC (à conserver, non-exposées produit) |

### D. Chiffres synthétiques

| Métrique | Valeur |
|---|---|
| Routers backend | 104 |
| Services backend | ~90 |
| Modèles backend | ~80 (100 % `org_id` ou inférable) |
| Routes frontend actives | 57 |
| Redirects legacy | 31 |
| Pages racine `src/pages/` | 57 (37 actives, 20 orphelines) |
| Composants `src/components/` + `src/pages/*/` | ~270 |
| Tests backend (fichiers) | 545 |
| Tests frontend (fichiers `.test.*`) | 234 |
| Source-guards V4 | 57 |
| Modules rail frontend | 7 (Accueil, Conformité, Énergie, Patrimoine, Achat, Facturation, Admin) |
| Quick actions | 14 |
| Hidden pages | 7 |
| Org-scoping couverture | ~95 % (5 routers à re-vérifier) |
| KPI registry | 11 KPI cardinaux |
| ACC endpoints | 0 |
| ACC services métier | 0 |
| ACC tables | 0 |
| Résidus ACC organisationnels | 1 enum + 5 fichiers FE + 4 fiches KB |

### E. Glossaire d'audit

- **ACC** : Autoconsommation Collective — opération multi-participants partageant une production locale (cadre Code énergie + Décret 2017-676 et suivants).
- **PMO** : Personne Morale Organisatrice — entité juridique organisatrice d'une ACC.
- **Clé de répartition** : règle de répartition de l'énergie autoproduite entre participants ACC (statique / dynamique / sur mesure).
- **Settlement local** : processus de réconciliation conso/prod intra-ACC, géré par GRD.
- **Scope IN** : ce que PROMEOS livre court terme (5 piliers + Centre d'Action + pilotage advisory).
- **Scope OUT** : ce que PROMEOS ne livre pas court terme (ACC, PMO, settlement, etc.).
- **Advisory** : posture produit non-prescriptive — PROMEOS conseille, n'exécute pas (pas de delestage automatique, pas d'achat automatique).
- **KPI magique** : KPI affiché sans unité, période, périmètre, source, formule traçable — proscrit par doctrine §8.

---

**Fin audit READ-ONLY** — branche `claude/refonte-sol2` @ `ade3d0a0` — 2026-05-22.

> Aucun fichier n'a été modifié pendant cet audit hormis ce livrable. Aucune branche créée. Aucun endpoint ACC créé. Aucun menu ACC ajouté. Worktree `audit-refonte-sol2` jeté après lecture.
