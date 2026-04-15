# AUDIT ULTRA-SÉVÈRE — Patrimoine / Sites / Bâtiments

**Date** : 2026-03-11
**Auditeur** : Principal Product Architect + Staff Engineer + UX Auditor
**Périmètre** : Module Patrimoine complet (backend models, routes, frontend pages/components, seed data)
**Verdict global** : 🔴 **4.2 / 10** — Module fonctionnel en surface mais criblé d'incohérences, de routes mortes, de données fantômes et de lacunes UX majeures.

---

## 1. INVENTAIRE COMPLET

### 1.1 Modèles backend (15 tables)

| Table | Fichier | Colonnes clés | Relations |
|-------|---------|--------------|-----------|
| Organisation | `models/organisation.py` | id, name, siren, type_org | → EntiteJuridique, Portefeuille |
| EntiteJuridique | `models/organisation.py` | id, name, siret, org_id | → Organisation |
| Portefeuille | `models/organisation.py` | id, name, org_id | N-N → Site via `portefeuille_site` |
| Site | `models/site.py` | id, name, adresse, ville, surface_m2, nb_occupants, type_site, statut_conformite, latitude, longitude, ges_kg_co2, dpe_class… (40+ cols) | → Batiment, Compteur |
| Batiment | `models/site.py` | id, name, surface, nb_etages, annee_construction, site_id | → Site |
| Usage | `models/site.py` | id, label, batiment_id | → Batiment |
| Compteur | `models/compteur.py` | id, pdl, serial, energy_vector, site_id, batiment_id | → Site, Batiment, DeliveryPoint |
| DeliveryPoint | `models/compteur.py` | id, pdl, compteur_id | → Compteur |
| EnergyVector | `models/compteur.py` | enum (ELEC, GAZ, EAU, FIOUL…) | — |
| StagingBatch | staging pipeline | id, file_name, status, stats_json | → StagingSite |
| StagingSite | staging pipeline | id, batch_id, raw_json, matched_site_id | → StagingBatch |
| StagingCompteur | staging pipeline | id, batch_id, raw_json | → StagingBatch |
| QualityFinding | staging pipeline | id, staging_site_id, field, severity | — |
| ActivationLog | staging pipeline | id, staging_site_id, action | — |
| portefeuille_site | link table N-N | portefeuille_id, site_id | — |

### 1.2 Routes API (88+ endpoints)

| Fichier | Lignes | Endpoints | Thème |
|---------|--------|-----------|-------|
| `routes/patrimoine.py` | 2897 | ~60 | CRUD sites/bâtiments/compteurs, heatmap, stats, staging pipeline, compliance, analytics |
| `routes/patrimoine_crud.py` | 533 | 21 | CRUD organisations, entités juridiques, portefeuilles |
| `routes/sites.py` | 283 | 6 | Sites alternatifs (KPI, compliance, search) |
| `routes/import_sites.py` | 180 | 2 | Import CSV/Excel |

### 1.3 Frontend (16 fichiers)

**Pages (5)** :

| Fichier | Lignes | Rôle | Verdict |
|---------|--------|------|---------|
| `Patrimoine.jsx` | 1521 | Centre de commande portfolio (table/heatmap/map) | ⚠️ Monstre monolithique |
| `Site360.jsx` | 1340 | Détail site 6 onglets | 🔴 Onglets vides/incohérents |
| `SiteDetail.jsx` | 553 | Ancien détail site | 🔴 **ROUTE MORTE — 404** |
| `SiteCompliancePage.jsx` | 863 | Conformité par site | ⚠️ Scores contradictoires |
| (aucune page Bâtiment) | — | — | 🔴 **ABSENT** |

**Composants (11)** :

| Composant | Rôle | Verdict |
|-----------|------|---------|
| PatrimoineWizard | Wizard ajout site | ✅ Fonctionnel |
| PatrimoineHealthCard | Carte santé portfolio | ✅ OK |
| PatrimoineHeatmap | Heatmap risque/conso | ✅ Fonctionne visuellement |
| PatrimoinePortfolioHealthBar | Barre santé globale | ✅ OK |
| PatrimoineRiskDistributionBar | Distribution risque | ✅ OK |
| SiteCreationWizard | Wizard création site | ✅ Fonctionnel |
| SitePicker | Sélecteur site | ✅ OK |
| SitesMap | Carte Leaflet | ⚠️ Zoom/clusters basiques |
| SiteAnomalyPanel | Anomalies site | ✅ OK |
| SiteBillingMini | Mini facturation site | ✅ OK |
| SiteContractsSummary | Résumé contrats site | ✅ OK |

### 1.4 Seed data

| Élément | Quantité | Détail |
|---------|----------|--------|
| Sites | 5 | Paris bureau, Lyon bureau, Toulouse entrepôt, Nice hôtel, Marseille école |
| Bâtiments | 7 | 1-2 par site |
| Compteurs | 11 | ELEC + GAZ par site |
| Organisations | 1 | Demo Corp |
| Entités juridiques | 3 | |
| Portefeuilles | 3 | |

---

## 2. HIÉRARCHIE MÉTIER ACTUELLE

```
Organisation (Demo Corp)
├── EntiteJuridique (× 3)
│   └── (lien indirect via org_id)
├── Portefeuille (× 3)
│   └── N-N → Site
└── Site (× 5)
    ├── Batiment (× 1-2)
    │   └── Usage (× 0-1)
    └── Compteur (× 2-3)
        └── DeliveryPoint (× 0-1)
```

### Verdict hiérarchie : 🔴 3/10

| Problème | Sévérité | Détail |
|----------|----------|--------|
| Portefeuille → Site = N-N mais jamais exposé en UI | 🔴 Critique | Le lien N-N existe en DB mais l'UI ne permet pas d'affecter un site à plusieurs portefeuilles |
| Bâtiment = coquille vide | 🔴 Critique | Modèle avec 5 colonnes, aucun KPI rattaché, aucune page dédiée |
| Usage = fantôme | 🔴 Critique | Table existe, jamais peuplée par le seed, jamais affichée |
| DeliveryPoint = doublon PDL | ⚠️ Majeur | Compteur a déjà `pdl`, DeliveryPoint redonde l'info |
| EntiteJuridique déconnectée | ⚠️ Majeur | Pas de lien direct EntiteJuridique → Site (passe par l'org) |
| Pas de Zone/Région/Cluster | 🔴 Critique | Aucun regroupement géographique au-dessus du site |

---

## 3. AUDIT 10 AXES

### Axe 1 : Hiérarchie et modèle de données — 🔴 3/10

**Forces** : Structure multi-niveaux pensée (Org → EJ → Portefeuille → Site → Batiment → Compteur). Tables de liaison N-N présentes.

**Faiblesses critiques** :
- **Bâtiment = table morte** : 5 colonnes (name, surface, nb_etages, annee_construction), aucun rattachement conso/facture/DPE/équipement. Le DPE est sur le Site, pas sur le Bâtiment — absurde pour un multi-bâtiment.
- **Usage jamais implémenté** : Table existe, 0 données.
- **DeliveryPoint redondant** : Le PDL est déjà sur Compteur.
- **Pas de lien EJ → Site direct** : impossible de filtrer "les sites de l'entité juridique X" sans passer par l'org.
- **Pas d'historisation** : aucun `valid_from/valid_to` sur les attributs site (surface change ? occupants changent ? DPE évolue ?).

### Axe 2 : Complétude des données — 🔴 3/10

**Forces** : Le seed produit des données crédibles (adresses réelles, surfaces cohérentes, coordonnées GPS).

**Faiblesses critiques** :
- **40+ colonnes sur Site** mais 80% vides en seed et en usage réel : `parking_type`, `oper_status`, `heating_type`, `cooling_type`, `insulation_year`… jamais affichées, jamais requises.
- **Aucune validation de complétude** : pas de score de remplissage, pas d'indicateur "données manquantes".
- **Conso non rattachée aux compteurs en Site360** : l'onglet Consommation affiche "à venir" malgré des données seedées.
- **Pas de qualité de données visible** : le staging pipeline QualityFinding existe en backend mais n'est jamais surfacé en UI.

### Axe 3 : Lisibilité et UX — ⚠️ 5/10

**Forces** :
- Patrimoine.jsx offre 3 vues (table/heatmap/map) — concept solide.
- Filtres fonctionnels (énergie, type site, ville).
- Heatmap visuellement lisible.
- Design system cohérent (Tailwind + composants ui/).

**Faiblesses** :
- **1521 lignes monolithiques** dans Patrimoine.jsx — maintenance cauchemar.
- **Site360 = 1340 lignes** — même problème.
- **Onglets vides dans Site360** : Consommation → placeholder, Conformité → "0 obligations" alors que des données existent.
- **Pas de breadcrumb** : quand on est sur Site360, impossible de remonter au portefeuille ou à l'entité juridique.
- **Pas de recherche globale** patrimoine.
- **Colonnes non triables** dans la table patrimoine (seulement filtres).

### Axe 4 : KPIs et métriques — ⚠️ 4/10

**Forces** :
- Score conformité 0-100 affiché.
- GES kgCO2 affiché par site.
- DPE class affiché (A-G).
- Heatmap par conso/risque.

**Faiblesses** :
- **Aucun KPI portfolio agrégé** : pas de conso totale, pas de coût total, pas de surface totale, pas de kWh/m², pas de €/m².
- **Score conformité incohérent** : Site360 affiche "100/100 Conforme" mais SiteCompliancePage montre "BACS Non conforme, Risque 10" pour le même site. Les deux pages calculent le score différemment.
- **Pas de tendance** : aucun delta N-1, aucune flèche d'évolution.
- **Pas de benchmark** : aucune comparaison inter-sites, aucune référence ADEME/CEREN.
- **GES affiché mais pas calculé** : c'est une valeur seedée statique, pas un calcul dynamique à partir de la conso.

### Axe 5 : Navigation et parcours — 🔴 3/10

**Forces** :
- Navigation Patrimoine → Site360 fonctionne (clic sur ligne du tableau).
- Onglets dans Site360 (6 tabs).

**Faiblesses critiques** :
- **Route morte `/sites/detail/:id`** → 404. SiteDetail.jsx existe (553 lignes) mais la route est cassée ou supprimée. **Code mort en production.**
- **Pas de navigation Bâtiment** : impossible d'accéder à un bâtiment spécifique.
- **Pas de navigation Compteur → Consommation** : les compteurs sont listés mais ne sont pas cliquables.
- **Retour arrière = bouton browser** : pas de breadcrumb, pas de bouton "Retour au patrimoine".
- **Carte (SitesMap)** : clic sur un pin ne navigue nulle part.
- **Heatmap** : clic sur une cellule ne navigue nulle part.

### Axe 6 : Actionnabilité — 🔴 3/10

**Forces** :
- Wizard de création site existe (PatrimoineWizard + SiteCreationWizard).
- Import CSV/Excel disponible (2 endpoints).

**Faiblesses critiques** :
- **Pas d'action depuis le tableau** : pas de sélection multiple, pas d'actions bulk (affecter portefeuille, changer statut, exporter).
- **Pas d'export** : aucun bouton CSV/Excel/PDF depuis l'UI patrimoine.
- **Pas d'édition inline** : cliquer sur un site ouvre Site360 en lecture seule (pas d'édition rapide).
- **Staging pipeline = backend only** : le pipeline DIAMANT (staging → quality → activation) est implémenté en backend mais jamais surfacé en UI.
- **Pas d'alertes patrimoine** : aucune notification "DPE expiré", "compteur sans données", "site incomplet".

### Axe 7 : Performances et scalabilité — ⚠️ 5/10

**Forces** :
- SQLite OK pour le POC (5 sites).
- Pagination présente sur les endpoints backend.
- Heatmap render côté client = rapide.

**Faiblesses** :
- **Patrimoine.jsx charge TOUT en un appel** : `/api/patrimoine/sites` sans pagination côté UI.
- **Site360 fait 6+ appels API** au montage (un par onglet).
- **Carte charge tous les sites** (pas de clustering pour >100 sites).
- **Pas de cache** : chaque visite re-fetch tout.

### Axe 8 : Intégration cross-modules — ⚠️ 5/10

**Forces** :
- Site360 intègre Factures (SiteBillingMini), Contrats (SiteContractsSummary), Anomalies (SiteAnomalyPanel).
- Conformité par site accessible via onglet.
- ScopePicker utilise le patrimoine.

**Faiblesses** :
- **Consommation non intégrée** : onglet vide malgré données existantes.
- **Pas de lien Patrimoine → BillIntel** : impossible de voir les anomalies billing d'un site directement.
- **Pas de lien Patrimoine → Contrats** : pas de vue "contrats par portefeuille".
- **Actions créées depuis Conformité ne remontent pas dans Site360**.

### Axe 9 : Data readiness (production) — 🔴 2/10

**Forces** :
- Import CSV existe en backend.
- Staging pipeline DIAMANT conçu (5 tables).

**Faiblesses critiques** :
- **Staging pipeline = dead code** : endpoints existent mais aucune UI pour déclencher un import, voir les erreurs qualité, activer les sites.
- **Pas de connecteur API** : aucune intégration fournisseur (Enedis, GRDF).
- **Pas de validation métier** : un site peut avoir surface=0, nb_occupants=null, pas d'alerte.
- **Pas de dédoublonnage** : aucune détection de doublons à l'import.
- **Pas de géocodage** : les coordonnées GPS sont seedées manuellement.

### Axe 10 : Potentiel de domination — ⚠️ 4/10

**Forces** :
- Concept 3 vues (table/heatmap/map) = différenciant si bien exécuté.
- Hiérarchie multi-niveaux (Org → EJ → Portefeuille → Site → Bâtiment) = bon design de base.
- Staging pipeline DIAMANT = bonne vision.

**Faiblesses** :
- **Aucun feature "wow"** : pas de digital twin, pas de scoring automatique, pas de recommandation IA.
- **Pas de comparaison inter-sites** : le minimum pour un portfolio manager.
- **Pas de carte thermique bâtiment** (floor plan).
- **Pas de timeline patrimoine** (historique des changements).

---

## 4. TABLEAU DE SYNTHÈSE

| # | Axe | Score | Statut |
|---|-----|-------|--------|
| 1 | Hiérarchie & modèle de données | 3/10 | 🔴 Critique |
| 2 | Complétude des données | 3/10 | 🔴 Critique |
| 3 | Lisibilité & UX | 5/10 | ⚠️ Insuffisant |
| 4 | KPIs & métriques | 4/10 | 🔴 Faible |
| 5 | Navigation & parcours | 3/10 | 🔴 Critique |
| 6 | Actionnabilité | 3/10 | 🔴 Critique |
| 7 | Performances & scalabilité | 5/10 | ⚠️ Acceptable POC |
| 8 | Intégration cross-modules | 5/10 | ⚠️ Partielle |
| 9 | Data readiness (production) | 2/10 | 🔴 Bloquant |
| 10 | Potentiel de domination | 4/10 | 🔴 Faible |
| **GLOBAL** | | **3.7 / 10** | **🔴 Insuffisant** |

---

## 5. GAP ANALYSIS — ÉTAT ACTUEL vs WORLD CLASS

| Capacité | Actuel | Cible World Class | Gap |
|----------|--------|-------------------|-----|
| **Hiérarchie** | Org→Site→Batiment (linéaire) | Org→EJ→Portefeuille→Site→Batiment→Zone→Compteur + tags libres + regroupements dynamiques | 🔴 Énorme |
| **Fiche site** | 40 colonnes, 80% vides | Fiche structurée par section, score de complétude, historique, photos, documents | 🔴 Grand |
| **Fiche bâtiment** | 5 colonnes, aucune page | DPE rattaché, équipements, surfaces par usage, plans, certifications | 🔴 Énorme |
| **KPI portfolio** | Score conformité + GES statique | kWh/m², €/m², CO2/m², score global, tendances N-1, benchmark ADEME | 🔴 Grand |
| **Navigation** | Table → Site360 (one way) | Breadcrumb complet, drill-down carte → site → bâtiment → compteur, recherche globale | 🔴 Grand |
| **Carte** | Pins basiques | Clusters, heatmap overlay, clic → fiche rapide, rayon de recherche | ⚠️ Moyen |
| **Import** | CSV backend uniquement | Wizard UI multi-étapes, mapping colonnes, preview, validation, dédoublonnage, API Enedis/GRDF | 🔴 Énorme |
| **Export** | Aucun | CSV, Excel, PDF fiche site, PDF portfolio, API | 🔴 Grand |
| **Actions bulk** | Aucune | Sélection multiple, affectation portefeuille, changement statut, export sélection | 🔴 Grand |
| **Qualité données** | QualityFinding en DB (invisible) | Score de complétude par site, alertes données manquantes, suggestions auto | 🔴 Grand |
| **Benchmark** | Aucun | Comparaison inter-sites, référentiel ADEME/CEREN, positionnement DPE | 🔴 Grand |
| **Historique** | Aucun | Timeline patrimoine, audit trail modifications, versioning attributs | 🔴 Énorme |
| **Staging pipeline UI** | Dead code | Wizard import → review qualité → correction → activation → monitoring | 🔴 Énorme |

---

## 6. BUGS ET ANOMALIES CRITIQUES

| # | Bug | Sévérité | Fichier | Action |
|---|-----|----------|---------|--------|
| B1 | **Route morte `/sites/detail/:id` → 404** | 🔴 P0 | `SiteDetail.jsx` (553L de code mort) | Supprimer SiteDetail.jsx + route |
| B2 | **Score conformité incohérent** : Site360 "100/100" vs SiteCompliancePage "Risque 10, BACS Non conforme" | 🔴 P0 | `Site360.jsx` vs `SiteCompliancePage.jsx` | Unifier le calcul de score |
| B3 | **Site360 Conformité "0 obligations"** malgré données existantes | 🔴 P1 | `Site360.jsx` onglet Conformité | Fix appel API ou mapping données |
| B4 | **Site360 Consommation = placeholder vide** malgré données seedées | 🔴 P1 | `Site360.jsx` onglet Consommation | Implémenter le rattachement conso |
| B5 | **Usage table = fantôme** : jamais peuplée, jamais affichée | ⚠️ P2 | `models/site.py` | Soit implémenter, soit supprimer |
| B6 | **DeliveryPoint = doublon PDL** | ⚠️ P2 | `models/compteur.py` | Clarifier le rôle ou supprimer |
| B7 | **GES = valeur statique** : pas recalculé dynamiquement | ⚠️ P2 | Seed + Site model | Implémenter calcul GES = conso × facteur émission |

---

## 7. PLAN D'UPGRADE PRIORISÉ

### Niveau A — Hygiène immédiate (Sprint 1-2, 5 jours)

| # | Action | Impact | Effort | Fichiers |
|---|--------|--------|--------|----------|
| A1 | **Supprimer SiteDetail.jsx + route morte** | Propreté codebase | 0.5j | `SiteDetail.jsx`, router config |
| A2 | **Unifier score conformité** : un seul calcul utilisé par Site360 ET SiteCompliancePage | Fix bug P0 | 1j | `Site360.jsx`, `SiteCompliancePage.jsx`, endpoint backend |
| A3 | **Brancher onglet Consommation Site360** sur les données réelles | Fix bug P1 | 1.5j | `Site360.jsx`, endpoint `/api/patrimoine/sites/{id}/consumption` |
| A4 | **Brancher onglet Conformité Site360** sur les obligations réelles | Fix bug P1 | 1j | `Site360.jsx`, endpoint obligations |
| A5 | **Ajouter breadcrumb** dans Site360 (Patrimoine > Site > [Onglet]) | Navigation | 0.5j | `Site360.jsx`, nouveau composant `Breadcrumb.jsx` |
| A6 | **Supprimer/commenter table Usage** si pas de plan d'implémentation | Propreté | 0.5j | `models/site.py` |

### Niveau B — Fondations solides (Sprint 3-5, 10 jours)

| # | Action | Impact | Effort | Fichiers |
|---|--------|--------|--------|----------|
| B1 | **KPIs portfolio agrégés** : ajouter en-tête Patrimoine.jsx avec kWh total, €/m² moyen, surface totale, nb compteurs | Valeur immédiate | 2j | `Patrimoine.jsx`, nouvel endpoint `/api/patrimoine/kpis` |
| B2 | **Score de complétude par site** : calculer % de remplissage des champs critiques, afficher badge | Qualité data | 2j | Backend service + `Patrimoine.jsx` colonne |
| B3 | **Rattacher DPE au Bâtiment** (pas au Site) + enrichir modèle Bâtiment (surface_utile, certification, année_renovation) | Modèle correct | 2j | `models/site.py`, migration, `Site360.jsx` |
| B4 | **Page Bâtiment** : fiche bâtiment accessible depuis Site360, avec DPE, surface, équipements | Navigation complète | 2j | Nouveau `BatimentDetail.jsx`, route |
| B5 | **Export CSV/Excel** depuis tableau patrimoine (sélection ou tout) | Actionnabilité | 1j | `Patrimoine.jsx`, endpoint export |
| B6 | **Recherche globale patrimoine** : barre de recherche dans Patrimoine.jsx (nom, adresse, PDL) | UX | 1j | `Patrimoine.jsx`, endpoint search |

### Niveau C — Différenciation (Sprint 6-9, 15 jours)

| # | Action | Impact | Effort | Fichiers |
|---|--------|--------|--------|----------|
| C1 | **Staging pipeline UI** : Wizard import → preview → quality review → activation | Data readiness | 5j | Nouveau `ImportWizard.jsx`, 3-4 étapes |
| C2 | **Benchmark inter-sites** : comparaison kWh/m² entre sites du même type, référence ADEME | KPI différenciant | 3j | Backend benchmark service, widget Site360 |
| C3 | **Carte avancée** : clusters, heatmap overlay, popup fiche rapide au hover, drill-down | UX carte | 3j | `SitesMap.jsx` refactor |
| C4 | **Actions bulk** : sélection checkbox, affecter portefeuille, changer statut, exporter sélection | Productivité | 2j | `Patrimoine.jsx` |
| C5 | **Timeline patrimoine** : historique des modifications par site (audit trail) | Traçabilité | 2j | Backend audit_log table, widget Site360 |

### Niveau D — Domination (Sprint 10-12, 10 jours)

| # | Action | Impact | Effort | Fichiers |
|---|--------|--------|--------|----------|
| D1 | **Scoring IA patrimoine** : score composite risque × complétude × performance → priorisation automatique des sites à traiter | Wow factor | 3j | Backend ML service, widget dashboard |
| D2 | **Connecteurs API Enedis/GRDF** : import automatique des points de livraison | Data readiness prod | 3j | Backend connectors |
| D3 | **Digital twin simplifié** : vue bâtiment avec zones colorées par usage/conso | Différenciation visuelle | 2j | Nouveau composant SVG |
| D4 | **PDF fiche site** : export PDF professionnel avec KPIs, DPE, conso, contrats, conformité | Opposabilité | 2j | Backend WeasyPrint + template |

---

## 8. TOP 5 ACTIONS IMMÉDIATES

| Rang | Action | Pourquoi maintenant | Effort | ROI |
|------|--------|---------------------|--------|-----|
| **1** | 🔴 **Supprimer route morte SiteDetail.jsx** | Code mort = dette technique active, confus pour les devs | 2h | Très élevé |
| **2** | 🔴 **Unifier score conformité** (B2 audit → un seul calcul) | Bug visible utilisateur, détruit la confiance | 1j | Critique |
| **3** | 🔴 **Brancher onglet Consommation Site360** | Feature "vide" = impression de produit inachevé, les données EXISTENT déjà | 1.5j | Très élevé |
| **4** | ⚠️ **Ajouter KPIs agrégés en header Patrimoine** | C'est la première chose qu'un DG regarde : "combien de m², combien de kWh, combien de €" | 2j | Élevé |
| **5** | ⚠️ **Breadcrumb + retour arrière Site360** | Navigation minimale pour ne pas perdre l'utilisateur | 0.5j | Élevé |

**Effort total Top 5 : ~5 jours**
**Impact : Le module passe de 3.7/10 à ~5.5/10** — seuil minimum de crédibilité.

---

## 9. SPEC V1.1 — CIBLE SPRINT 1-5

### Patrimoine V1.1 = Actuel + Niveau A + Niveau B

**Score cible : 6.5/10** (de "Insuffisant" à "Correct")

**Ce que l'utilisateur verra** :
1. ✅ Tableau patrimoine avec **KPIs agrégés en header** (surface totale, conso totale, €/m² moyen)
2. ✅ **Score de complétude** par site (badge vert/orange/rouge)
3. ✅ **Breadcrumb** fonctionnel dans tout le parcours
4. ✅ **Site360 avec tous les onglets peuplés** (Conso, Conformité, Factures)
5. ✅ **Score conformité unifié** et cohérent partout
6. ✅ **Page Bâtiment** accessible avec DPE rattaché
7. ✅ **Export CSV** depuis le tableau
8. ✅ **Recherche** dans le patrimoine
9. ✅ **Zéro code mort** (SiteDetail supprimé, Usage clarifié)

**Ce qui reste hors scope V1.1** :
- Import wizard UI (Niveau C)
- Benchmark ADEME (Niveau C)
- Actions bulk (Niveau C)
- Scoring IA (Niveau D)
- Connecteurs Enedis/GRDF (Niveau D)

---

## 10. PROPOSITIONS UI/UX

### 10.1 Header KPI Portfolio (Niveau B1)

```
┌──────────────────────────────────────────────────────────────┐
│  PATRIMOINE                                                   │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ 5 sites │  │12 400 m²│  │ 847 MWh │  │ 142 €/m²│        │
│  │         │  │ Surface  │  │Conso/an │  │Coût/an  │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│  [Table] [Heatmap] [Carte]           🔍 Rechercher...       │
└──────────────────────────────────────────────────────────────┘
```

### 10.2 Breadcrumb Site360

```
Patrimoine > Paris — Siège Social > Résumé
                                     ^^^^^^ onglet actif
```

### 10.3 Badge complétude

```
Site: Paris — Siège Social
Complétude: ████████░░ 82%  ⚠ 3 champs manquants
```

### 10.4 Fiche Bâtiment

```
┌─────────────────────────────────────────┐
│ 🏢 Bâtiment A — Tour Principale        │
│                                          │
│ Surface: 2 400 m²  │ Étages: 8          │
│ Année: 2005        │ Rénovation: 2019   │
│ DPE: C (180 kWh/m²/an)                  │
│                                          │
│ Compteurs rattachés:                     │
│ ├ ELEC PDL 12345678901234  ⚡ 450 MWh/an│
│ └ GAZ  PCE 98765432109876  🔥 120 MWh/an│
│                                          │
│ [Voir consommation] [Voir factures]      │
└─────────────────────────────────────────┘
```

---

## CONCLUSION

Le module Patrimoine de PROMEOS est une **fondation structurellement correcte** (bon modèle de données de base, bonne vision 3 vues) mais **criblé de lacunes d'exécution** :

- **4 bugs P0/P1** dont une route morte et des onglets vides
- **Aucun KPI agrégé** pour le portfolio manager
- **Navigation unidirectionnelle** sans retour ni breadcrumb
- **Staging pipeline = dead code** — la feature d'import la plus critique n'est pas accessible
- **Bâtiment = entité fantôme** — 5 colonnes, 0 page, 0 KPI

Le plan d'upgrade en 4 niveaux (A→D) permet de passer de **3.7/10 à 6.5/10 en 5 sprints** (Niveaux A+B), puis de viser **8/10 en 4 sprints supplémentaires** (Niveau C), pour atteindre le **statut "best-in-class" en 12 sprints** (Niveau D).

**Priorité absolue** : Les 5 actions immédiates (5 jours) qui éliminent les bugs visibles et ajoutent les KPIs minimaux. Sans ça, aucun utilisateur ne prendra le module au sérieux.
