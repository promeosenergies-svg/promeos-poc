# AUDIT SEVERE — MODULE PATRIMOINE PROMEOS

> Audit produit senior · 2026-03-15 · Scope : Patrimoine comme fondation des 4 briques (Conformite, Achat, Facturation, Pilotage)

---

## 1. VERDICT

**Le module Patrimoine est une fondation solide mais perfectible.** L'architecture hierarchique (Org → EJ → Portefeuille → Site → Batiment → Compteur) est bien pensee pour le B2B France energie. Le pipeline d'import staging (DRAFT → QA → Activate) est mature. Les anomalies patrimoine avec scoring de risque reglementaire/financier sont un vrai differenciateur.

**Points forts majeurs :** pipeline d'ingestion multi-etape, quality gate 11 regles deterministes, heatmap risque quantile, virtual scroll 1000+ sites, URL-synced filters, cross-brick integration propre via ScopeContext + `site_id`.

**Points critiques :** soft-delete incoherent (actif vs deleted_at), activation batch sans rollback transactionnel, race condition meter_id, validation SIREN/SIRET incomplete cote frontend, XSS potentiel popup map.

**Note globale : 7.5/10** — Production-ready pour un POC avance, mais necessite 5-6 corrections ciblees avant scaling client.

---

## 2. SCORECARD

| Axe | Note | Commentaire |
|-----|------|-------------|
| **Modele de donnees** | 8/10 | Hierarchie complete, lineage, soft-delete. Manque coherence soft-delete |
| **Creation/CRUD** | 7/10 | Wizard 7 etapes bien guide. Validation SIREN frontend incomplete |
| **Import** | 8.5/10 | Pipeline staging exemplaire. 165 synonymes. 11 regles QA. Pas de streaming CSV |
| **B2B France** | 8/10 | SIREN/SIRET/PRM/PCE/NAF/INSEE bien modelises. NAF validator manquant |
| **Cross-brick** | 9/10 | Toutes les briques dependent de site_id. Routes helpers propres. 0 lien casse |
| **UX/UI** | 8/10 | Heatmap, health bar, virtual scroll, URL filters. Erreurs silencieuses meters |
| **Simplicite** | 7/10 | 1800 lignes Patrimoine.jsx = complexite concentree mais maitrisee |
| **Robustesse** | 6.5/10 | Race condition meter_id, batch activate sans rollback, CSV en memoire |
| **Performance** | 8/10 | Virtual scroll, lazy loading, cache 5min. Pas de pagination backend listes |
| **Extensibilite future** | 8/10 | Modele ouvert pour ACC/IoT/multi-energie. Enums extensibles |

---

## 3. FAITS TERRAIN (observes dans le code + screenshots)

| # | Fait | Source |
|---|------|--------|
| F1 | 5 sites actifs, 3 EJ, 3 PF, 11 batiments, 9 contrats | Screenshot KPI bar |
| F2 | Risque global 400 k€, 40% sains, 2 NC, 2 a risque | Screenshot health bar |
| F3 | Top sites risque : Hotel Nice 166k€, Siege Paris 148k€, Bureau Lyon 54k€ | Screenshot heatmap |
| F4 | Framework dominant : Decret Tertiaire (7), Facturation (8) | Screenshot badges |
| F5 | 0 Points de livraison actifs (KPI) → anomalie systemique | Screenshot KPI "PDL: 0" |
| F6 | Completude 88% — bon mais pas excellent | Screenshot bottom bar |
| F7 | Wizard import 6 etapes : Mode → Import → Apercu → Corrections → Validation → Resultat | Screenshot wizard |
| F8 | Wizard creation 7 etapes : Org → EJ → PF → Site → Batiments → Compteurs → Recap | Screenshot wizard create |
| F9 | Heatmap utilise quantiles (p40/p80) pour coloration risque | Code PatrimoineRiskDistributionBar |
| F10 | 11 regles qualite staging + 8 regles anomalies live = 19 controles patrimoine total | Code quality_rules.py + patrimoine_anomalies.py |

---

## 4. HYPOTHESES PRODUIT VALIDEES / INVALIDEES

| Hypothese | Statut | Evidence |
|-----------|--------|----------|
| "Le patrimoine est le socle de toutes les briques" | **VALIDE** | Toutes les briques (Conformite, Achat, Facturation, Pilotage) requierent `site_id` du patrimoine |
| "L'import CSV suffit pour l'onboarding client" | **PARTIELLEMENT** | Pipeline mature mais pas de streaming (50 MB limit), pas de parsing Excel natif |
| "Le quality gate bloque les donnees invalides" | **VALIDE** | 11 regles, BLOCKING empeche activation, score qualite deterministe |
| "Le modele supporte le multi-entite" | **VALIDE** | N-N via OrgEntiteLink avec roles (proprietaire/gestionnaire/locataire) |
| "Les anomalies sont actionnables" | **VALIDE** | Chaque anomalie a un `cta` (call-to-action) avec navigation |
| "Le modele est pret pour l'ACC" | **NON TESTE** (hors scope) | Architecture ouverte, mais pas de modele ACC existant |

---

## 5. AUDIT DETAILLE PAR AXE

### Axe 1 — Creation de site

**Wizard SiteCreationWizard (7 etapes)** : bien structure, flow Org → EJ → PF → Site → Batiments → Compteurs → Recap. Steps 5 et 6 optionnels = bon UX pour onboarding minimal.

**Problemes :**
- SIREN/SIRET : validation regex `^\d{9}$` cote frontend, mais **pas de checksum Luhn** (le backend le fait, pas le front → erreur tardive)
- Creation inline d'Organisation/EJ dans le wizard sans confirmation → risque de doublons
- Pas de geocoding automatique a la saisie d'adresse

**Verdict :** 7/10 — Fonctionnel, mais validation frontend insuffisante.

### Axe 2 — Import

**Pipeline staging exemplaire** : 6 etapes, 165 synonymes colonnes, auto-detection delimiteur/encoding, quality gate 11 regles, corrections (merge/skip/remap/update), activation avec audit trail.

**Problemes :**
- CSV charge entierement en memoire (50 MB limit, pas de streaming)
- Pas de deduplication par nom de site intra-batch
- Activation batch sans transaction rollback → etat incoherent si erreur partielle
- Mode Demo saute directement a step 5 (flow inconsistant)

**Verdict :** 8.5/10 — Le meilleur axe du module.

### Axe 3 — Modele de donnees

**Hierarchie complete et coherente :**

```
Organisation (SIREN, type_client)
  → EntiteJuridique (SIREN/SIRET, NAF, role N-N)
    → Portefeuille (groupement decisionnel)
      → Site (core, 40+ champs, compliance scores)
        → Batiment (surface, annee, CVC)
          → Usage (type, famille, surface, significance)
        → Compteur (PRM/PCE, energy_vector)
        → DeliveryPoint (PRM/PCE autonome)
        → Contract (fournisseur, dates, N-N DP)
```

**Problemes :**
- **Soft-delete incoherent** : Organisation utilise `actif=False`, EntiteJuridique utilise `deleted_at`, Site utilise `actif=False` → queries cassees quand on melange
- `compliance_score_breakdown_json` stocke en String (pas JSON type) → pas de query possible
- Dual PRM/PCE : `Compteur.meter_id` ET `DeliveryPoint.code` → risque d'incoherence, migration path flou
- `annual_kwh_total` nullable sans SLA de refresh → rapports stales
- Pas de `TypeBatiment` enum (residentiel/bureau/retail/industriel)

**Verdict :** 8/10 — Solide, manque de coherence sur les patterns.

### Axe 4 — B2B France

**Bien couvert :** SIREN (9 digits + Luhn backend), SIRET (14 digits + Luhn), PRM/PCE (14 digits), NAF, INSEE, code postal (5 digits, departement valide), TypeSite adapte (magasin, bureau, copropriete, logement social, collectivite, hotel, sante, enseignement).

**Manques :**
- Pas de validateur NAF (`is_valid_naf_code()` absent systeme-wide)
- SIRET nullable sur EntiteJuridique (devrait etre requis pour facturation France)
- Code postal rejette 00000 (CEDEX edge case)
- Pas d'inference TypeSite depuis code NAF (mentionne en commentaire mais pas implemente)

**Verdict :** 8/10 — Bon cadre reglementaire, quelques trous.

### Axe 5 — Cross-brick (fondation)

**Excellent** : Patrimoine = couche fondationnelle. Toutes les briques utilisent `site_id` :
- **Conformite** : `ComplianceFinding.site_id`, statut conformite sur Site, pipeline obligations
- **Achat** : scenarios par site, estimation volume depuis compteurs, contrats energie
- **Facturation** : factures par site, reconciliation, payment rules
- **Pilotage** : KPIs agreges depuis sites (nb actifs, NC, risque total)

Route helpers (`toPatrimoine()`, `toConsoExplorer()`, `toBillIntel()`) + ScopeContext = navigation cross-brick propre. **0 lien casse detecte.**

**Verdict :** 9/10 — Point le plus fort du module.

### Axe 6 — UX/UI

**Points forts visibles (screenshots) :**
- Health bar avec risque global, % sains, trend (stable/↑/↓)
- Heatmap sites avec quantiles couleur, filtres framework/severite/recherche
- KPIs bottom bar (Sites actifs, PDL, Contrats, Expirants, NC, Completude)
- Wizard import avec stepper visuel clair, 4 modes bien differencies

**Problemes :**
- Erreurs silencieuses sur ajout sous-compteur (`catch(() => {})`)
- XSS potentiel dans popup carte (inline HTML onclick)
- Pas de skeleton loading sur PatrimoineHealthCard
- Fichier max 10 Mo affiche mais pas verifie cote client

**Verdict :** 8/10 — UX soignee, quelques trous de robustesse.

### Axe 7 — Simplicite vs complexite

`Patrimoine.jsx` = **1800+ lignes** = fichier le plus gros du frontend. Concentre : table virtuelle, heatmap, drawers, filtres URL, vues multiples (table/map/expiring/PDL/contracts), bulk actions, favoris. C'est un **"God component"** maitrise mais a risque de dette technique.

**Verdict :** 7/10 — Fonctionne mais un refactor en sous-composants serait benefique.

### Axe 8 — Robustesse

**Problemes critiques :**
1. **Race condition meter_id** : `random PRM` en concurrent cree des doublons (TOCTOU)
2. **Batch activate sans rollback** : erreur partielle → sites crees + compteurs manquants → etat zombie
3. **CSV 50 MB en memoire** : OOM sur gros fichiers client
4. **Contract overlap TOCTOU** : check au POST, pas protege en concurrent
5. **Pas de rate limiting** sur endpoints batch

**Verdict :** 6.5/10 — Le point le plus faible. Correction prioritaire avant scaling.

### Axe 9 — Performance

**Points forts :** virtual scroll @tanstack/react-virtual (52px rows, overscan 10), cache 5min portfolio summary, lazy loading modals, code splitting.

**Problemes :**
- Pas de pagination backend sur `GET /patrimoine/crud/sites` et `GET /patrimoine/crud/organisations`
- Heatmap fetch anomalies pour 10 sites a chaque changement de scope (pas de memoization)
- KPIs pas cachees (recalcul a chaque requete)

**Verdict :** 8/10 — Bon pour le POC, optimisation necessaire pour 500+ sites.

### Axe 10 — Extensibilite future (ACC / IoT / multi-energie)

> **Note : L'ACC n'est pas dans le POC. Verification uniquement que le modele ne bloque pas une extension future.**

Le modele Patrimoine **ne bloque pas** une extension ACC :
- `EnergyVector` enum (electricity/gas/heat/water/other) → extensible pour biomasse, H2, etc.
- `TypeUsage` structure en familles (thermique/eclairage/process/mobilite) → extensible
- `DeliveryPoint` autonome (separe de Compteur) → pret pour IoT/GTB
- `DataSourceType` inclut deja `gtb_api` → pret pour connecteurs temps reel
- `UsageBaseline` avec `confidence` et `data_source` → pret pour sous-comptage virtuel
- Pas de couplage dur entre modele patrimoine et reglementation specifique

**Seul frein potentiel :** `TypeSite` enum fige en base → ajouter un nouveau type necessite migration DB. Recommandation : prevoir un type "autre" avec champ libre (deja present implicitement).

**Verdict :** 8/10 — Modele ouvert, pas de blocage structurel.

---

## 6. ERREURS ET BUGS DETECTES

| # | Severite | Description | Fichier | Impact |
|---|----------|-------------|---------|--------|
| E1 | **CRITIQUE** | `activate_batch()` pas de rollback transactionnel | patrimoine_service.py | Etat zombie si erreur partielle |
| E2 | **CRITIQUE** | Race condition random `meter_id` | compteurs.py routes | Doublons PRM en concurrent |
| E3 | **HAUTE** | Soft-delete incoherent (actif vs deleted_at) | organisation.py vs site.py vs batiment.py | Queries cassees |
| E4 | **HAUTE** | 0 Points de livraison (screenshot KPI) | Seed/data | Anomalies METER_NO_DELIVERY_POINT systemiques |
| E5 | **MOYENNE** | XSS popup carte via site.nom | SitesMap.jsx | Injection si nom malveillant |
| E6 | **MOYENNE** | Erreurs silencieuses sous-compteur | Patrimoine.jsx (SiteMetersTab) | Utilisateur ne sait pas que l'action a echoue |
| E7 | **BASSE** | SIREN checksum pas verifie cote front | SiteCreationWizard.jsx | Erreur tardive au backend |
| E8 | **BASSE** | File size "max 10 Mo" pas verifie client | PatrimoineWizard.jsx | Upload inutile puis erreur |

---

## 7. MODELE CIBLE (recommandations)

### Corrections immediates (Sprint 1, 3 jours)

1. **Standardiser soft-delete** → tout sur `SoftDeleteMixin` (deleted_at), supprimer `actif` boolean
2. **Transaction rollback activate_batch** → wrapper dans `db.begin()` / `db.rollback()`
3. **Meter ID unique via sequence DB** → remplacer random par compteur auto-incremente
4. **Toast erreur sous-compteur** → remplacer `catch(() => {})` par `catch((e) => toast(...))`
5. **Sanitize popup map** → utiliser API MapLibre Popup au lieu d'inline HTML

### Ameliorations structurantes (Sprint 2, 5 jours)

6. **Pagination backend** → ajouter `skip/limit` sur tous les endpoints liste
7. **Validation SIREN/SIRET frontend** → implementer checksum Luhn cote SiteCreationWizard
8. **Streaming CSV** → traitement ligne par ligne pour fichiers > 5 MB
9. **Deduplication batch** → unique(batch_id, nom) sur StagingSite
10. **File size check client** → verifier `file.size < 10 * 1024 * 1024` avant upload

---

## 8. PARCOURS CIBLE UTILISATEUR

### Parcours "Onboarding client 100 sites"

```
1. Admin importe CSV 100 sites → Wizard Import (mode Complet)
2. Quality gate detecte 12 issues → Corrections step (autofix + manuels)
3. Score qualite 82% "Bon" → Activation autorisee
4. 100 sites crees + batiments + compteurs provisionnes
5. Anomalies patrimoine calculees automatiquement → Heatmap visible
6. Compliance engine tourne → Statuts conformite attribues
7. Navigation vers Achat/Facturation/Conformite avec contexte site
```

### Parcours "Gestionnaire quotidien"

```
1. Ouvre /patrimoine → voit Heatmap top risques
2. Clique tile site rouge → Drawer anomalies
3. Voit "Ecart surface 15%" → CTA "Corriger" → edite surface batiment
4. Revient heatmap → site passe en orange
5. Filtre "Expirant < 90j" → voit 4 contrats → navigue vers Achat
```

---

## 9. GAP ANALYSIS (Etat actuel vs cible)

| Dimension | Actuel | Cible | Gap |
|-----------|--------|-------|-----|
| Soft-delete | Mixte (actif + deleted_at) | Unifie SoftDeleteMixin | **MOYEN** |
| Transaction batch | Pas de rollback | Atomique | **CRITIQUE** |
| Pagination backend | Absente sur CRUD | skip/limit partout | **MOYEN** |
| Validation front | Regex longueur seulement | Luhn + format + feedback | **FAIBLE** |
| CSV streaming | 50 MB en memoire | Streaming chunks | **MOYEN** |
| PDL provisionnes | 0 en demo (screenshot) | Auto-creation depuis PRM compteur | **HAUTE** |
| Export bulk | Absent | CSV/XLSX de sites filtres | **FAIBLE** |
| NAF validator | Absent | Referentiel INSEE | **FAIBLE** |
| Audit log corrections | Absent | Qui a corrige quoi/quand | **MOYEN** |
| TypeBatiment enum | Absent | residentiel/bureau/retail/industriel | **FAIBLE** |

---

## 10. PLAN 30 JOURS

| Semaine | Actions | Objectif |
|---------|---------|----------|
| **S1** (J1-J5) | E1: rollback activate_batch, E2: fix meter_id race, E3: unifier soft-delete, E6: toast erreurs | **0 bug critique** |
| **S2** (J6-J12) | Pagination backend, validation SIREN front, sanitize map popup, file size check | **Robustesse** |
| **S3** (J13-J19) | Auto-creation DeliveryPoints depuis PRM compteur, audit log corrections, CSV streaming | **Donnees completes** |
| **S4** (J20-J30) | Export bulk CSV, tests E2E patrimoine, refactor Patrimoine.jsx (< 800 lignes), doc API OpenAPI | **Qualite prod** |

---

## 11. TOP 5 ACTIONS PRIORITAIRES

| # | Action | Impact | Effort | Pourquoi |
|---|--------|--------|--------|----------|
| **1** | **Transaction rollback sur activate_batch** | CRITIQUE | 2h | Un echec partiel cree des sites zombies sans compteurs — corruption silencieuse de donnees |
| **2** | **Unifier soft-delete (SoftDeleteMixin partout)** | HAUTE | 4h | Les queries melangent `actif=False` et `deleted_at IS NULL` → donnees fantomes dans les rapports |
| **3** | **Fix race condition meter_id** | HAUTE | 1h | Deux imports simultanes creent le meme PRM → contrainte unique violee en prod |
| **4** | **Auto-creer DeliveryPoints depuis PRM compteur** | HAUTE | 3h | KPI "0 PDL" visible en screenshot → anomalie METER_NO_DELIVERY_POINT sur 100% des compteurs |
| **5** | **Remplacer catch vide par toast erreur (SiteMetersTab)** | MOYENNE | 30min | L'utilisateur ajoute un sous-compteur, ca echoue, aucun feedback → frustration garantie |

---

## ANNEXE — DETAILS TECHNIQUES

### A. Modele de donnees complet

```
Organisation (nom, type_client, siren, actif, is_demo)
  │
  ├─ OrgEntiteLink (N-N, role: proprietaire/gestionnaire/locataire)
  │   └─ EntiteJuridique (siren, siret, naf_code, region_code, insee_code)
  │
  └─ Portefeuille (nom, description)
      │
      └─ Site (40+ champs)
          ├─ Identity: nom, type (TypeSite enum)
          ├─ Location: adresse, code_postal, ville, region, lat/lon
          ├─ Physical: surface_m2, nombre_employes
          ├─ Regulatory: siret, naf_code, tertiaire_area_m2, operat_status
          ├─ Compliance: statut_decret_tertiaire, compliance_score_composite
          ├─ Energy: annual_kwh_total, last_energy_update_at
          ├─ Lineage: data_source, imported_at, imported_by, is_demo
          │
          ├─ Batiment (nom, surface_m2, annee_construction, cvc_power_kw)
          │   └─ Usage (type, famille, label, surface_m2, pct_of_total)
          │       └─ UsageBaseline (kwh_total, kwh_m2_year, confidence)
          │
          ├─ Compteur (numero_serie, type, energy_vector, puissance_kw)
          │   └─ Consommation (readings)
          │
          ├─ DeliveryPoint (code PRM/PCE, energy_type, status)
          │   └─ ContractDeliveryPoint (N-N)
          │
          └─ Contract (fournisseur, start_date, end_date, energy_type)
```

### B. Pipeline staging

```
StagingBatch (DRAFT → VALIDATED → APPLIED | ABANDONED)
  ├─ StagingSite (24 colonnes canoniques, 165 synonymes)
  ├─ StagingCompteur (PRM/PCE, type, puissance)
  └─ QualityFinding (11 regles, severity, evidence, resolution)
      │
      └─ ActivationLog (audit trail: sites_created, compteurs_created, hash)
```

### C. Regles qualite (19 total)

**Staging (11 regles) :**
1. dup_site_address (WARNING)
2. dup_meter (BLOCKING)
3. orphan_meter (BLOCKING)
4. invalid_siren (BLOCKING)
5. invalid_siret (BLOCKING)
6. invalid_postal_code (BLOCKING)
7. invalid_type_site (BLOCKING)
8. missing_nom_site (BLOCKING)
9. missing_surface (WARNING)
10. mismatch_surface (WARNING, tolerance 5%)
11. contract_overlap (BLOCKING)

**Live anomalies (8 regles) :**
1. SURFACE_MISSING (HIGH)
2. SURFACE_MISMATCH (MEDIUM)
3. BUILDING_MISSING (MEDIUM)
4. BUILDING_USAGE_MISSING (MEDIUM)
5. METER_NO_DELIVERY_POINT (HIGH)
6. CONTRACT_DATE_INVALID (MEDIUM)
7. CONTRACT_OVERLAP_SITE (HIGH)
8. ORPHANS_DETECTED (LOW)

### D. Enums patrimoine

- **TypeSite** : magasin, usine, bureau, entrepot, commerce, copropriete, logement_social, collectivite, hotel, sante, enseignement
- **TypeCompteur** : electricite, gaz, eau
- **TypeUsage** : 14 types + 3 legacy aliases, 6 familles
- **EnergyVector** : electricity, gas, heat, water, other
- **StatutConformite** : conforme, derogation, a_risque, non_conforme
- **StagingStatus** : DRAFT, VALIDATED, APPLIED, ABANDONED
- **QualityRuleSeverity** : CRITICAL, BLOCKING, WARNING, INFO

---

*Audit genere le 2026-03-15 par PROMEOS Audit Agent*
*Module : Patrimoine (backend + frontend)*
*Fichiers examines : 50+ (models, routes, schemas, services, components, pages)*
*Issues detectees : 34 backend + 17 frontend = 51 total*
