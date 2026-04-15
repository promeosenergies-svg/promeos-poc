# ADDENDUM STRATÉGIQUE — Registre Patrimonial & Contractuel

**Date** : 2026-03-11
**Référence** : Corrige et complète `AUDIT_PATRIMOINE_ULTRA_SEVERE.md`
**Requalification cible** : "Patrimoine / Sites / Bâtiments" → **"Registre patrimonial & contractuel"**

---

## 1. FAITS

### 1.1 Ce que l'audit initial voit bien

| Point | Verdict audit | Confirmé |
|-------|--------------|----------|
| Route morte SiteDetail.jsx → 404 | 🔴 P0 | ✅ Vrai — 553 lignes de code mort |
| Score conformité incohérent Site360 vs SiteCompliancePage | 🔴 P0 | ✅ Vrai |
| Onglets Consommation/Conformité vides dans Site360 | 🔴 P1 | ✅ Vrai |
| Bâtiment = modèle maigre (5 colonnes, aucune page) | 🔴 Critique | ✅ Vrai — modèle a en réalité 6 colonnes (nom, surface_m2, annee_construction, cvc_power_kw, site_id, timestamps) mais reste faible |
| Pas de KPI portfolio agrégé en header | ⚠️ Majeur | ✅ Vrai |
| Pas de breadcrumb | ⚠️ Majeur | ✅ Vrai |
| Staging pipeline = dead code côté UI | 🔴 Critique | ✅ Vrai |

### 1.2 Ce que l'audit initial sous-estime

| Point audit | Ce qu'il dit | Réalité |
|-------------|-------------|---------|
| **"Portefeuille → Site = N-N jamais exposé"** | Lien N-N via `portefeuille_site` | **FAUX.** La relation est **1-to-many** : `Site.portefeuille_id` (FK). Le lien N-N `portefeuille_site` évoqué dans l'audit n'est pas le mécanisme actif. La hiérarchie est propre : EJ → Portefeuille → Site. |
| **"EntiteJuridique déconnectée"** | "Pas de lien direct EJ → Site, passe par l'org" | **SOUS-ESTIMÉ.** Le lien est EJ → Portefeuille → Site (1-to-many chaîné). C'est fonctionnel. Le vrai manque est qu'il n'y a pas de lien direct EJ → Site pour les cas de rattachement hors portefeuille. |
| **"DeliveryPoint = doublon PDL"** | Compteur a `pdl`, DP redonde l'info | **FAUX.** DP est l'entité **moderne** (PRM/PCE 14 digits, statut, audit trail import). `Compteur.meter_id` est le champ **legacy**. `Compteur.delivery_point_id` (FK) pointe vers DP. Le design est correct : DP = point réseau, Compteur = appareil physique. |
| **Score global 3.7/10** | Module "Insuffisant" | **Trop sévère** si on inclut le périmètre contractuel et la réconciliation. Le socle data est solide. Le problème est la couche UI/intégration, pas le modèle. Score corrigé : **4.8/10** (modèle solide, surface lacunaire). |

### 1.3 Ce que l'audit initial oublie complètement

| Angle mort | Impact | Détail réel du codebase |
|------------|--------|------------------------|
| **EnergyContract — modèle complet** | 🔴 MAJEUR | Le modèle `EnergyContract` existe (16 colonnes) avec : `supplier_name`, `start_date`, `end_date`, `price_ref_eur_per_kwh`, `fixed_fee_eur_per_month`, `notice_period_days`, `auto_renew`, `offer_indexation` (FIXE/INDEXE/SPOT/HYBRIDE), `price_granularity`, `renewal_alert_days`, `contract_status` (ACTIVE/EXPIRING/EXPIRED). **L'audit ne mentionne jamais le contrat.** |
| **Contract Radar (V99)** | 🔴 MAJEUR | Page `ContractRadarPage.jsx` fonctionnelle : vue portefeuille des échéances, urgency color-coded, filtres horizon (30/60/90/180/365j). **L'audit ignore cette feature.** |
| **Purchase Scenarios (V99)** | 🔴 MAJEUR | Service `purchase_scenarios_service.py` : 3 scénarios d'achat (A=conservateur/fixe, B=modéré/indexé, C=agressif/spot) avec avantages, inconvénients, estimation coût. Drawer + modal résumé imprimable. **L'audit ignore cette feature.** |
| **PaymentRule (V96)** | ⚠️ IMPORTANT | Modèle 3 niveaux (PORTEFEUILLE/SITE/CONTRAT) avec `invoice_entity_id`, `payer_entity_id`, `cost_center`. Résolution en cascade. **L'audit ignore ce modèle.** |
| **Reconciliation Service** | ⚠️ IMPORTANT | Service 6 checks (delivery_points, active_contract, recent_invoices, period_coherence, energy_type_match, payment_rule). Score 0-100. Endpoint fix 1-click (V97). **L'audit ignore ce service.** |
| **SIREN/SIRET complets** | ⚠️ IMPORTANT | Organisation.siren, EntiteJuridique.siren (UNIQUE) + siret + naf_code + region_code + insee_code. Seed peuple 3 EJ avec vrais SIREN/SIRET/NAF. **L'audit dit "déconnectée" — c'est faux.** |
| **OrgEntiteLink / PortfolioEntiteLink** | ℹ️ Mineur | Tables N-N optionnelles avec rôle (propriétaire/gestionnaire/locataire), dates, confidence. Existent mais non utilisées en UI. |
| **ContractIndexation enum** | ℹ️ Mineur | FIXE, INDEXE, SPOT, HYBRIDE — déjà modélisé et affiché en badge dans le Radar. |

---

## 2. HYPOTHÈSES

### 2.1 Hypothèses retenues pour le plan 30 jours

| # | Hypothèse | Justification |
|---|-----------|---------------|
| H1 | **Le contrat énergie est un objet de premier rang** au même titre que le site | Un DG/DAF voit d'abord ses engagements contractuels (combien je paie, quand ça expire, quel fournisseur). Le patrimoine physique (m², bâtiments) est secondaire. |
| H2 | **Le lien Contrat ↔ PDL est le chaînon manquant** | Aujourd'hui un contrat est lié à un Site. En réalité un contrat couvre N points de livraison (PDL/PCE). Un site peut avoir un contrat ELEC et un contrat GAZ couvrant des PDL différents. Le modèle actuel est correct à 80% (1 contrat = 1 site + 1 energy_type) mais ne modélise pas explicitement quels PDL sont couverts. |
| H3 | **Le modèle Org → EJ → Portefeuille → Site est bon** | La chaîne 1-to-many est propre. Le vrai problème n'est pas le modèle mais l'absence de visibilité UI de cette hiérarchie (pas de page EJ, pas de vue "sites par EJ", pas de drill-down). |
| H4 | **Le Contrat Radar est la feature la plus sous-exploitée** | Elle existe, fonctionne, mais est isolée dans sa page. Elle devrait alimenter : le dashboard, les alertes, le Site360, le dossier opposable. |
| H5 | **Pas de refonte de modèle nécessaire** | Le modèle backend est solide (EnergyContract 16 cols, DeliveryPoint moderne, PaymentRule 3 niveaux, Reconciliation 6 checks). Le travail est d'ajouter 4-5 colonnes manquantes et de brancher l'UI. |
| H6 | **Le bâtiment reste secondaire à 30 jours** | En B2B énergie, le DG ne gère pas ses bâtiments dans l'outil énergie. Il gère ses sites, ses contrats, ses compteurs. Le bâtiment est un nice-to-have pour la conformité DPE tertiaire (décret BACS). |

### 2.2 Hypothèses écartées

| Hypothèse écartée | Pourquoi |
|-------------------|----------|
| "Refaire le modèle de données" | Le modèle est bon. On enrichit, on ne refait pas. |
| "Ajouter un contrat multi-sites" | Trop complexe à 30j. Le pattern 1 contrat = 1 site + 1 energy_type fonctionne. Cas multi-sites = duplication de contrat avec même référence fournisseur. |
| "Digital twin / fiche bâtiment enrichie" | Hors scope B2B énergie. À traiter quand le décret BACS l'exigera. |
| "Page dédiée Entité Juridique" | La hiérarchie EJ fonctionne via le ScopeSwitcher. Une page dédiée n'apporte pas de valeur immédiate. |

---

## 3. DÉCISIONS

### D1 — Requalification de la brique

**Ancien nom** : "Patrimoine / Sites / Bâtiments"
**Nouveau nom** : **"Registre patrimonial & contractuel"**

**Périmètre cible** :

| Objet | Rang | Rôle |
|-------|------|------|
| Organisation | Racine | Groupe client multi-entités |
| Entité Juridique | 1er rang | Personne morale (SIREN unique), porteur des obligations légales |
| Portefeuille | Regroupement | Regroupement métier libre (par usage, région, entité) |
| Site | 1er rang | Lieu physique de consommation, unité de facturation |
| Bâtiment | 2ème rang | Sous-division physique du site (DPE, surface, équipements) |
| Point de livraison (DP) | 1er rang | Point réseau (PRM ELEC / PCE GAZ), objet de raccordement |
| Compteur | 2ème rang | Appareil physique de mesure, rattaché au DP |
| **Contrat énergie** | **1er rang** | Engagement fournisseur avec prix, échéances, conditions — **le chaînon central** |

### D2 — Corrections du diagnostic

| Axe audit | Score initial | Score corrigé | Justification |
|-----------|--------------|---------------|---------------|
| 1. Hiérarchie & modèle | 3/10 | **5/10** | Hiérarchie 1-to-many propre, contrat modélisé (16 cols), DeliveryPoint moderne, PaymentRule 3 niveaux. Manque : lien contrat ↔ DP, champs contrat (signature, conditions). |
| 2. Complétude données | 3/10 | **4/10** | Seed peuple SIREN/SIRET/NAF, contrats avec prix/indexation/préavis. Manque : complétude UI visible. |
| 8. Intégration cross-modules | 5/10 | **6/10** | Reconciliation 6 checks, Radar alimenté par contrats, Scenarios liés aux actions. Manque : Radar non visible dans dashboard/Site360. |
| 10. Potentiel domination | 4/10 | **5/10** | Radar + Scenarios + Reconciliation = base solide. Manque : exploitation cross-brique. |
| **GLOBAL** | **3.7/10** | **4.8/10** | Le modèle est plus solide que diagnostiqué. Le déficit est UI/intégration. |

### D3 — Champs à ajouter au contrat

| Champ | Type | Justification | Priorité |
|-------|------|---------------|----------|
| `reference_fournisseur` | String(100) | N° de contrat chez le fournisseur — clé de réconciliation | 🔴 P0 |
| `date_signature` | Date | Opposabilité juridique — quand le contrat a été signé | ⚠️ P1 |
| `conditions_particulieres` | Text | Notes libres : clauses spéciales, dérogations | ⚠️ P1 |
| `document_url` | String(500) | Lien vers le scan/PDF du contrat signé | ⚠️ P2 |

### D4 — Lien Contrat ↔ Points de livraison

**État actuel** : Contrat → Site (1-to-many via site_id). Le contrat ne dit pas quels PDL il couvre.

**Cible** : Table de liaison `contract_delivery_points` (N-N) :

```
contract_delivery_points
├── contract_id (FK → energy_contracts)
├── delivery_point_id (FK → delivery_points)
└── created_at
```

**Pourquoi** : Un contrat ELEC couvre les PRM X, Y, Z du site. Si le site a 5 PRM dont 2 hors contrat, il faut le savoir pour la réconciliation et le shadow billing.

**Impact** : Enrichit la reconciliation (check "tous les DP sont couverts"), le shadow billing (prix contractuel par DP), et le dossier (opposabilité par PDL).

### D5 — Le Contrat Radar doit irriguer le reste

| Consommateur | Aujourd'hui | Cible 30j |
|-------------|-------------|-----------|
| Dashboard | Rien | Widget "3 contrats expirant sous 90j" |
| Site360 onglet Résumé | SiteContractsSummary (mini-fiche) | Ajouter urgency badge + lien vers Radar |
| Alertes / Notifications | Rien | Notification "Contrat X expire dans 30j, préavis dans 15j" |
| BillIntel | Shadow billing utilise prix contrat | Afficher source prix ("Contrat #42 — 0.185 €/kWh") dans le drawer |
| Dossier opposable | Rien | Section "Engagements contractuels" avec dates + prix + échéances |

---

## 4. MODÈLE CIBLE

### 4.1 Hiérarchie complète

```
Organisation (siren, type_client)
│
├── EntiteJuridique (siren UNIQUE, siret, naf_code, region_code, insee_code)
│   │
│   ├── Portefeuille (nom, description)
│   │   │
│   │   └── Site (nom, type, siret, surface_m2, adresse, GPS)
│   │       │
│   │       ├── Batiment (nom, surface_m2, annee_construction, cvc_power_kw)
│   │       │
│   │       ├── DeliveryPoint (code PRM/PCE 14 digits, energy_type, status)
│   │       │   └── Compteur (numero_serie, puissance_souscrite_kw, energy_vector)
│   │       │
│   │       ├── EnergyContract ★ OBJET 1ER RANG
│   │       │   ├── supplier_name, energy_type
│   │       │   ├── reference_fournisseur ← NOUVEAU
│   │       │   ├── date_signature ← NOUVEAU
│   │       │   ├── start_date, end_date
│   │       │   ├── notice_period_days, auto_renew
│   │       │   ├── price_ref_eur_per_kwh, fixed_fee_eur_per_month
│   │       │   ├── offer_indexation (FIXE/INDEXE/SPOT/HYBRIDE)
│   │       │   ├── price_granularity, renewal_alert_days
│   │       │   ├── contract_status (ACTIVE/EXPIRING/EXPIRED)
│   │       │   ├── conditions_particulieres ← NOUVEAU
│   │       │   ├── document_url ← NOUVEAU
│   │       │   │
│   │       │   ├── N-N → DeliveryPoint (via contract_delivery_points) ← NOUVEAU
│   │       │   ├── 1-N → EnergyInvoice (factures rattachées)
│   │       │   └── PaymentRule (payer_entity, cost_center)
│   │       │
│   │       ├── EnergyInvoice (facture fournisseur)
│   │       └── Reconciliation (3-way check : DP + Contrat + Facture)
│   │
│   └── PaymentRule (cascade : Portefeuille → Site → Contrat)
│
├── OrgEntiteLink (N-N optionnel, rôle, dates)
└── PortfolioEntiteLink (N-N optionnel, rôle)
```

### 4.2 Différences vs état actuel

| Élément | État actuel | Cible | Effort |
|---------|------------|-------|--------|
| Lien Contrat → DP | Inexistant (contrat lié au site uniquement) | Table N-N `contract_delivery_points` | 0.5j |
| `reference_fournisseur` sur contrat | Absent | String(100), nullable | 0.25j |
| `date_signature` sur contrat | Absent | Date, nullable | 0.25j |
| `conditions_particulieres` | Absent | Text, nullable | 0.25j |
| `document_url` | Absent | String(500), nullable | 0.25j |
| Hiérarchie Org → EJ → PF → Site | ✅ Déjà correct | Pas de changement | 0 |
| DeliveryPoint moderne | ✅ Déjà correct | Pas de changement | 0 |
| EnergyContract 16 cols | ✅ Déjà riche | +4 colonnes | 0.5j |
| PaymentRule 3 niveaux | ✅ Déjà correct | Pas de changement | 0 |
| Reconciliation 6 checks | ✅ Déjà correct | Enrichir avec check DP-couvert-par-contrat | 0.5j |

**Effort modèle total : 2.5 jours** — c'est un enrichissement, pas une refonte.

---

## 5. PLAN 30 JOURS

### Bloc 0 — Modèle métier cible (Jours 1-3)

> Poser le socle data avant de toucher l'UI.

| # | Action | Effort | Fichiers |
|---|--------|--------|----------|
| 0.1 | **Ajouter 4 colonnes à EnergyContract** : `reference_fournisseur`, `date_signature`, `conditions_particulieres`, `document_url` | 0.5j | `models/billing_models.py`, migration |
| 0.2 | **Créer table `contract_delivery_points`** (N-N contrat ↔ DP) | 0.5j | `models/billing_models.py` ou `models/patrimoine.py`, migration |
| 0.3 | **Enrichir seed** : peupler les 4 nouveaux champs contrat + rattacher DP aux contrats | 0.5j | `demo_seed/gen_billing.py`, `demo_seed/gen_master.py` |
| 0.4 | **Enrichir reconciliation** : nouveau check "DP couvert par contrat actif" | 0.5j | `services/reconciliation_service.py` |
| 0.5 | **Exposer les nouveaux champs** dans les endpoints CRUD contrat + serializer | 0.5j | `routes/patrimoine.py`, schemas |
| 0.6 | **Tests Bloc 0** | 0.5j | `tests/test_contract_model_enrichment.py` |

**Livrable Bloc 0** : Modèle enrichi, seed à jour, reconciliation augmentée, tests green.

### Bloc 1 — Fixes P0 visibles (Jours 4-7)

> Éliminer les bugs qui détruisent la crédibilité.

| # | Action | Effort | Fichiers |
|---|--------|--------|----------|
| 1.1 | **Supprimer SiteDetail.jsx** + route morte | 0.25j | `SiteDetail.jsx`, router |
| 1.2 | **Unifier score conformité** : un seul calcul côté backend, consommé par Site360 ET SiteCompliancePage | 1j | `Site360.jsx`, `SiteCompliancePage.jsx`, endpoint backend |
| 1.3 | **Brancher onglet Consommation Site360** sur données réelles | 1j | `Site360.jsx`, endpoint conso |
| 1.4 | **Brancher onglet Conformité Site360** sur obligations réelles | 0.75j | `Site360.jsx`, endpoint obligations |
| 1.5 | **Breadcrumb Site360** : Patrimoine > [Portefeuille] > [Site] > [Onglet] | 0.5j | `Site360.jsx`, composant Breadcrumb |
| 1.6 | **Tests Bloc 1** (source-guard + Playwright) | 0.5j | Tests frontend |

**Livrable Bloc 1** : Zéro bug visible, navigation cohérente, onglets peuplés.

### Bloc 2 — Registre contractuel (Jours 8-15)

> Le contrat devient un citoyen de premier rang dans toute l'app.

| # | Action | Effort | Fichiers |
|---|--------|--------|----------|
| 2.1 | **Onglet Contrats enrichi dans Site360** : afficher les 4 nouveaux champs (ref fournisseur, date signature, conditions, lien document), urgency badge, lien Radar | 1.5j | `SiteContractsSummary.jsx`, `Site360.jsx` |
| 2.2 | **Vue contrats dans Patrimoine.jsx** : nouvelle vue "Contrats" (4ème vue après Table/Heatmap/Map) — tableau des contrats du portefeuille avec filtres fournisseur/énergie/statut/échéance | 2j | `Patrimoine.jsx`, nouveau composant `PatrimoineContractsView.jsx` |
| 2.3 | **Formulaire création/édition contrat** enrichi : tous les champs y compris ref fournisseur, date signature, sélection des DP couverts, conditions, upload doc | 1.5j | Nouveau composant `ContractForm.jsx`, routes existantes |
| 2.4 | **Widget dashboard "Contrats à renouveler"** : top 3 contrats expirant, lien vers Radar | 1j | `DashboardPage.jsx`, endpoint existant `/api/contracts/radar` |
| 2.5 | **Notification contrat** : alerte quand un contrat entre dans la fenêtre de préavis | 1j | Backend notification service, frontend NotificationCenter |
| 2.6 | **Tests Bloc 2** | 1j | Tests backend + frontend |

**Livrable Bloc 2** : Le contrat est visible partout : Site360, Patrimoine, Dashboard, Notifications.

### Bloc 3 — Complétude & readiness (Jours 16-22)

> Rendre les données exploitables et visibles.

| # | Action | Effort | Fichiers |
|---|--------|--------|----------|
| 3.1 | **KPIs agrégés header Patrimoine** : nb sites, surface totale, conso totale, coût annuel, nb contrats actifs, nb contrats expirant | 1.5j | `Patrimoine.jsx`, endpoint `/api/patrimoine/kpis` |
| 3.2 | **Score de complétude par site** : % remplissage champs critiques (surface, compteur, contrat, DP, facture récente). Badge dans tableau + Site360 | 1.5j | Backend service, `Patrimoine.jsx` |
| 3.3 | **Reconciliation visible dans Site360** : afficher le score reconciliation (6 checks) dans l'onglet Résumé avec bouton "Corriger" (1-click fix V97) | 1j | `Site360.jsx`, endpoints existants |
| 3.4 | **Source prix dans BillIntel drawer** : quand le shadow billing utilise un prix contrat, afficher "Contrat #42 — EDF — 0.185 €/kWh" | 0.5j | `InsightDrawer.jsx`, `billing_shadow_v2.py` |
| 3.5 | **Export CSV patrimoine** : export tableau courant (sites ou contrats) | 0.5j | `Patrimoine.jsx` |
| 3.6 | **Tests Bloc 3** | 1j | Tests backend + frontend |

**Livrable Bloc 3** : Données visibles, complétude mesurée, reconciliation accessible, export fonctionnel.

### Bloc 4 — Cross-briques (Jours 23-27)

> Connecter le registre au reste de PROMEOS.

| # | Action | Effort | Fichiers |
|---|--------|--------|----------|
| 4.1 | **Dossier opposable enrichi** : section "Engagements contractuels" dans DossierPrintView (contrat actif, prix, échéance, PDL couverts) | 1j | `DossierPrintView.jsx` |
| 4.2 | **Lien Patrimoine → BillIntel** : depuis Site360, bouton "Voir les anomalies billing" filtre BillIntel sur le site | 0.5j | `Site360.jsx`, `BillIntelPage.jsx` |
| 4.3 | **Lien Patrimoine → Radar** : depuis la vue Contrats de Patrimoine.jsx, bouton "Voir le Radar" pré-filtré | 0.5j | `Patrimoine.jsx`, `ContractRadarPage.jsx` |
| 4.4 | **Radar enrichi** : afficher les DP couverts par chaque contrat, le score reconciliation, la ref fournisseur | 1j | `ContractRadarPage.jsx`, endpoint enrichi |
| 4.5 | **Tests Bloc 4** | 1j | Tests frontend |

**Livrable Bloc 4** : Navigation cross-briques fluide, dossier opposable complet.

### Bloc 5 — Polish (Jours 28-30)

> Buffer + finition.

| # | Action | Effort | Fichiers |
|---|--------|--------|----------|
| 5.1 | **Buffer de sécurité** (glissements des blocs précédents) | 1j | — |
| 5.2 | **Smoke test complet** : 12 parcours critiques avec Playwright | 1j | `audit-agent.mjs` |
| 5.3 | **Nettoyage** : supprimer code mort restant, tables fantômes (Usage si pas planifiée) | 0.5j | Divers |
| 5.4 | **Documentation** : mettre à jour le README avec l'architecture registre | 0.5j | `README.md` |

---

## 5.1 CALENDRIER SYNTHÉTIQUE

```
Semaine 1  (J1-J5)   │ Bloc 0 (modèle)   │ Bloc 1a (P0 fixes)
Semaine 2  (J6-J10)  │ Bloc 1b (P0 fixes) │ Bloc 2a (contrats UI)
Semaine 3  (J11-J15) │ Bloc 2b (contrats)  │ Bloc 2c (dashboard/notif)
Semaine 4  (J16-J22) │ Bloc 3 (complétude) │
Semaine 5  (J23-J27) │ Bloc 4 (cross)      │
Semaine 6  (J28-J30) │ Bloc 5 (polish)     │
```

### Gates

| Gate | Jour | Critère | Bloquant |
|------|------|---------|----------|
| G0 | J3 | Modèle enrichi + tests green + seed OK | Oui — rien ne peut commencer sans le modèle |
| G1 | J7 | Zéro bug P0 visible, Site360 cohérent | Oui — crédibilité minimum |
| G2 | J15 | Vue contrats + formulaire + dashboard widget + notification | Oui — la valeur métier est là |
| G3 | J22 | KPIs, complétude, reconciliation visible, export | Non — nice-to-have si G2 est solide |
| G4 | J30 | Cross-briques + smoke test | Non — peut glisser à J35 si nécessaire |

---

## 6. TOP 5 ACTIONS

| Rang | Action | Bloc | Effort | Pourquoi d'abord |
|------|--------|------|--------|------------------|
| **1** | **Enrichir le modèle EnergyContract** (+4 cols + table N-N contrat↔DP) | 0 | 1.5j | **Tout en dépend.** Sans `reference_fournisseur` et lien DP, impossible de faire un registre contractuel crédible. Le modèle drive l'UI, pas l'inverse. |
| **2** | **Supprimer code mort + unifier score conformité** | 1 | 1.25j | **Crédibilité.** Un prospect qui voit un 404 ou un score incohérent arrête la démo. Coût bas, impact immédiat. |
| **3** | **Brancher les onglets vides de Site360** (Conso + Conformité) | 1 | 1.75j | **Produit fini vs prototype.** Les données existent déjà en base. C'est du branchement, pas du développement. |
| **4** | **Vue "Contrats" dans Patrimoine + formulaire enrichi** | 2 | 3.5j | **La feature qui repositionne le produit.** Le DG/DAF ne vient pas voir des bâtiments. Il vient voir combien il paie, à qui, jusqu'à quand, et s'il doit renégocier. |
| **5** | **KPIs agrégés header Patrimoine + widget dashboard "Contrats expirant"** | 2+3 | 2.5j | **Valeur visible en 2 secondes.** Le header KPI dit "vous avez 5 sites, 12 400 m², 3 contrats expirant". Le widget dashboard dit "action requise". |

**Effort total Top 5 : ~10.5 jours**
**Impact : Le module passe de 4.8/10 à ~7/10** — seuil de crédibilité B2B.

---

## ANNEXE — Matrice de traçabilité audit → addendum

| Point audit initial | Statut addendum |
|--------------------|-----------------|
| Route morte SiteDetail.jsx | ✅ Maintenu → Bloc 1.1 |
| Score conformité incohérent | ✅ Maintenu → Bloc 1.2 |
| Onglets vides Site360 | ✅ Maintenu → Bloc 1.3/1.4 |
| Breadcrumb absent | ✅ Maintenu → Bloc 1.5 |
| KPIs agrégés absents | ✅ Maintenu → Bloc 3.1 |
| Bâtiment = coquille vide | ⏸️ Reporté — secondaire en B2B énergie à 30j |
| "Portefeuille N-N" | ❌ Corrigé — c'est 1-to-many, pas N-N |
| "EJ déconnectée" | ❌ Corrigé — chaîne EJ→PF→Site fonctionne |
| "DeliveryPoint doublon" | ❌ Corrigé — DP est l'entité moderne, Compteur.meter_id est legacy |
| "Score 3.7/10" | ❌ Corrigé → 4.8/10 (modèle sous-estimé) |
| Contrat énergie | 🆕 Ajouté — angle mort majeur de l'audit |
| Contract Radar | 🆕 Ajouté — feature existante ignorée |
| Purchase Scenarios | 🆕 Ajouté — feature existante ignorée |
| PaymentRule | 🆕 Ajouté — modèle existant ignoré |
| Reconciliation Service | 🆕 Ajouté — service existant ignoré |
| Registre contractuel (vue + formulaire) | 🆕 Ajouté — le vrai différenciant B2B |
