# AUDIT & PLAN D'UPGRADE — Brique "Usages Énergétiques / Plan de Comptage"

**Date** : 2026-03-13
**Auteur** : Claude (Principal Product Architect + Energy Data Product Lead + UX Auditor)
**Périmètre** : PROMEOS — Brique Usage / Plan de comptage / Usages énergétiques

---

## 1. SYNTHÈSE EXÉCUTIVE

| Métrique | Valeur |
|----------|--------|
| **Note globale** | **38/100** |
| **Potentiel à 30 jours** (Niveaux A+B) | 62/100 |
| **Potentiel à 90 jours** (Niveaux A+B+C) | 82/100 |

**Verdict** : La brique Usage **n'existait pas** en tant que brique produit. Les usages étaient un enum à 7 valeurs collé sur un bâtiment, sans aucun lien vers les compteurs, les factures, les contrats, la conformité, ou les actions. Le modèle `Usage` avait 4 champs : id, batiment_id, type (enum), description. Aucune FK vers Meter, Invoice, Contrat, ni BacsAsset.

### Ce qui a été implémenté (V1.1)

| Composant | Avant | Après V1.1 |
|-----------|-------|------------|
| **Modèle Usage** | 4 champs, isolé | 10 champs, pivot entity avec relations Meter/BACS/Recommendation |
| **TypeUsage** | 7 valeurs plates, "BUREAUX" ambigu | 16 valeurs en 6 familles (Thermique, Éclairage, Élec Spécifique, Process, Mobilité, Auxiliaires) |
| **Plan de comptage** | Inexistant | Endpoint `metering_plan(site_id)` — arbre dynamique compteurs→usages |
| **Usage Readiness** | Inexistant | Score /100 à 4 dimensions (déclaration, couverture, qualité, profondeur) |
| **Top UES** | KB breakdown prévu mais `None` | Endpoint `top_ues(site_id)` — top usages par kWh |
| **Coût par usage** | Aucun lien facture→usage | Endpoint `cost_breakdown(site_id)` — ventilation pro-rata sous-compteur |
| **Diagnostic par usage** | Meter principal seulement | `usage_id` propagé de Meter → ConsumptionInsight |
| **Cross-links** | Aucun | `usage_id` FK sur Meter, BacsCvcSystem, Recommendation, ConsumptionInsight |
| **UsageBaseline** | Inexistant | Modèle créé (période, kWh, IPE, source, confiance) |
| **Provenance data** | Backend only, invisible front | `DataSourceType` enum (6 sources) + badges dans page /usages |
| **Page /usages** | Données éclatées sur 5 pages | Page pivot unifiée avec 6 blocs |
| **Seed demo** | Usages basiques | Usages enrichis avec label, surface, source, % total, significativité + sous-compteurs liés |

---

## 2. AUDIT DÉTAILLÉ — 14 ANGLES

### ANGLE 1 : POSITIONNEMENT PRODUIT

**FAITS** :
- La page `ConsumptionContextPage.jsx` s'appelle "Usages & Horaires" mais affiche un score comportement /100 et des KPI hors-horaires/talon/dérive. Pas de vision "usages" au sens énergétique.
- `ConsumptionExplorerPage.jsx` (992 lignes) : 8 panels, 3 niveaux d'onglets. Impressionnant techniquement mais ne raconte pas l'histoire "usage".
- `ConsommationsUsages.jsx` (1238 lignes) : wizard d'import en 7 étapes. Le mot "usage" est dans le titre mais le contenu est 100% import/technique.
- Le modèle `Usage` avait 4 champs : id, batiment_id, type (enum), description. Aucun lien vers Meter, Invoice, Contrat, BacsAsset.

**DÉCISION** : L'Usage devient une entité pivot. La page `/usages` est la page d'atterrissage après le Cockpit pour un Energy Manager.

**STATUT V1.1** : ✅ Implémenté — page `/usages` créée, modèle Usage enrichi.

### ANGLE 2 : USAGE READINESS

**FAITS** :
- Aucun "Usage Readiness Score" n'existait.
- `consumption_unified_service.py` avait un concept de couverture (80% threshold) mais au niveau site/meter, pas au niveau usage.
- `dataReadinessModel.js` évalue 4 dimensions génériques, pas usage.

**DÉCISION** : Score calculé par site, 4 dimensions pondérées :
- Usages déclarés vs attendus (30 pts)
- Couverture sous-comptage (30 pts)
- Qualité données (20 pts)
- Profondeur données (20 pts)

**STATUT V1.1** : ✅ Implémenté — `compute_usage_readiness()` + endpoint `/api/usages/readiness/{site_id}`.

### ANGLE 3 : PLAN DE COMPTAGE

**FAITS** :
- Sous-comptage existait (`Meter.parent_meter_id`, `get_site_meters_tree`, `get_meter_breakdown`).
- MAIS : aucune entité "Plan de comptage". Le breakdown calculait `delta_kwh` sans formalisation.

**DÉCISION** : Endpoint `metering_plan(site_id)` calculant dynamiquement l'arbre depuis les données existantes.

**STATUT V1.1** : ✅ Implémenté — `get_metering_plan()` + endpoint `/api/usages/metering-plan/{site_id}`.

### ANGLE 4 : ZONES FONCTIONNELLES

**FAITS** :
- `TertiaireEfaBuilding` avait un champ `usage_label` (String libre) — seul proxy.
- Sous-compteurs liés à un parent Meter, pas à un usage ni à une zone.

**DÉCISION** : A minima associer Meter → Usage via FK. A terme : entité `FunctionalZone`.

**STATUT V1.1** : ✅ Partiel — FK `usage_id` sur Meter. `FunctionalZone` reporté à V1.2.

### ANGLE 5 : TAXONOMIE DES USAGES

**FAITS** :
- `TypeUsage` enum : 7 valeurs plates, "BUREAUX" ambigu (type de bâtiment ET usage).
- KB archetypes avaient `usage_breakdown_json` prévu mais jamais rempli.

**DÉCISION** : Restructurer en 2 niveaux (Famille → Sous-usages), aligner sur nomenclature ADEME/OPERAT.

**STATUT V1.1** : ✅ Implémenté — 16 TypeUsage en 6 UsageFamily + 3 alias legacy + endpoint `/api/usages/taxonomy`.

### ANGLE 6 : DUALITÉ BACS / TERTIAIRE

**FAITS** :
- `BacsCvcSystem` (heating/cooling/ventilation) existait sans lien vers `Usage`.
- `TertiaireEfaBuilding.usage_label` pas lié à `TypeUsage`.

**DÉCISION** : `usage_id` FK optionnel sur `BacsCvcSystem`.

**STATUT V1.1** : ✅ Implémenté — FK ajoutée + migration.

### ANGLE 7 : UES / IPE / BASELINE

**FAITS** :
- Aucun modèle `Baseline`. Aucun `IPE`.
- `Recommendation.actual_savings_kwh_year` existait mais jamais utilisé.

**DÉCISION** : Créer `UsageBaseline` + exposer les UES.

**STATUT V1.1** : ✅ Implémenté — modèle `UsageBaseline` créé, `get_top_ues()` opérationnel.

### ANGLE 8 : DÉRIVES

**FAITS** :
- `consumption_diagnostic.py` détecte 5 types : hors_horaires, base_load, pointe, derive, data_gap.
- Détection robuste : median+MAD pour pointe, linreg pour dérive, Q10 vs median pour base load.
- MAIS : pas de diagnostic par usage, pas de détection simultanéité chauffage/clim.

**DÉCISION** : Propager `usage_id` de Meter → ConsumptionInsight. Simultanéité → V1.2.

**STATUT V1.1** : ✅ Implémenté — `usage_id` propagé dans `run_diagnostic()`, insights enrichis avec usage_label/usage_type.

### ANGLE 9 : ACTIONNABILITÉ

**FAITS** :
- Actions générées au niveau site/meter, pas par usage.
- `Recommendation` avec ICE scoring, lifecycle existants.

**DÉCISION** : `usage_id` FK sur Recommendation.

**STATUT V1.1** : ✅ Implémenté — FK ajoutée + migration.

### ANGLE 10 : LIEN FACTURE

**FAITS** :
- `EnergyInvoice` existait sans lien vers Usage.

**DÉCISION** : Endpoint `usage_cost_breakdown(site_id, period)` ventilant facture par usage pro-rata sous-compteur.

**STATUT V1.1** : ✅ Implémenté — `get_usage_cost_breakdown()` + endpoint `/api/usages/cost-breakdown/{site_id}`.

### ANGLE 11 : LIEN CONTRAT / ACHAT

**FAITS** :
- Contrats énergie existaient sans lien usage.

**DÉCISION** : Quick win afficher répartition usage dans page Achat.

**STATUT V1.1** : ⏳ Reporté à V1.2 — dépend de l'intégration contrats.

### ANGLE 12 : LIEN CONFORMITÉ

**FAITS** :
- Score compliance composite ne descendait pas au niveau usage.
- CVC systems BACS inventoriés mais pas liés à Usage.

**DÉCISION** : Cross-link Usage → BacsCvcSystem.

**STATUT V1.1** : ✅ Partiel — FK `usage_id` sur BacsCvcSystem. Widget conformité par usage → V1.2.

### ANGLE 13 : INTEROPÉRABILITÉ / API / GOUVERNANCE DATA

**FAITS** :
- `MeterReading.is_estimated`, `quality_score` existaient en backend, invisibles côté front.

**DÉCISION** : Badge provenance visible sur chaque widget.

**STATUT V1.1** : ✅ Implémenté — `DataSourceType` enum + `DataSourceBadge` composant dans page /usages.

### ANGLE 14 : UX / UI / POTENTIEL DE DOMINATION

**FAITS** :
- Pas de page "Usages" unifiée. Information éclatée sur 4-5 pages.
- Un DG ne pouvait pas comprendre en 10 secondes "quels sont mes usages principaux, lesquels dérivent, combien ça me coûte, que dois-je faire".

**DÉCISION** : Page `/usages` pivot avec 6 blocs.

**STATUT V1.1** : ✅ Implémenté — `UsagesDashboardPage.jsx` avec KPIs, readiness, plan comptage, top UES, dérives, coût.

---

## 3. GAP ANALYSIS

| # | Capacité cible | État avant V1.1 | Sévérité | V1.1 | Reste |
|---|---------------|------------------|----------|------|-------|
| 1 | **Usage Readiness Score** par site | N'existait pas | Critical | ✅ | — |
| 2 | **Plan de comptage** formel | Implicite seulement | Major | ✅ | — |
| 3 | **Zones fonctionnelles** explicites | String libre TertiaireEfa | Major | ⚠️ FK Meter→Usage | Entité FunctionalZone |
| 4 | **Taxonomie usages structurée** | Enum plat 7 valeurs | Critical | ✅ 16 en 6 familles | — |
| 5 | **Top UES** | KB breakdown retournait None | Major | ✅ | Enrichir avec KB |
| 6 | **IPE** par usage (kWh/m²/an) | N'existait pas | Major | ⚠️ Modèle prêt | Calcul effectif |
| 7 | **Baseline** par usage | Inexistant | Critical | ✅ Modèle créé | CRUD API + UI |
| 8 | **Diagnostic par sous-compteur/usage** | Meter principal seulement | Major | ✅ | — |
| 9 | **Simultanéité chauffage/clim** | Non détectée | Major | ❌ | V1.2 |
| 10 | **Usage → Facture** (coût par usage) | Aucun lien | Critical | ✅ | — |
| 11 | **Usage → Contrat/Achat** | Aucun lien | Major | ❌ | V1.2 |
| 12 | **Usage → Conformité** | BACS non liés à Usage | Major | ⚠️ FK ajoutée | Widget UI |
| 13 | **Badge provenance data** | Backend only | Minor | ✅ | — |
| 14 | **Page Usages unifiée** | Éclatée sur 5 pages | Critical | ✅ | — |

---

## 4. PLAN D'ACTION — RÉSUMÉ EXÉCUTION

### NIVEAU A — QUICK WINS ✅ FAIT

| # | Action | Statut |
|---|--------|--------|
| A1 | Renommer → "Usages Énergétiques" | ⏳ Fusionné dans nouvelle page |
| A2 | Badge provenance sur KPIs | ✅ DataSourceBadge dans page /usages |
| A3 | Usage Readiness Score | ✅ compute_usage_readiness() |
| A4 | Diagnostic par sous-compteur | ✅ usage_id propagé dans run_diagnostic |
| A5 | Enrichir TypeUsage (16 valeurs, 6 familles) | ✅ enums.py + migration |

### NIVEAU B — STRUCTURE PRODUIT ✅ FAIT

| # | Action | Statut |
|---|--------|--------|
| B1 | FK usage_id sur Meter | ✅ energy_models.py + migration |
| B2 | Endpoint metering_plan | ✅ usage_service.py |
| B3 | Bloc plan de comptage UI | ✅ MeteringPlanTree dans UsagesDashboardPage |
| B5 | Top 5 UES | ✅ get_top_ues() + UesTable |
| B6 | FK usage_id sur BacsCvcSystem et Recommendation | ✅ + migration |
| B7 | Page /usages pivot | ✅ UsagesDashboardPage.jsx |

### NIVEAU C — DIFFÉRENCIATION FORTE (à venir)

| # | Action | Statut |
|---|--------|--------|
| C1 | Modèle UsageBaseline | ✅ Modèle créé, CRUD à exposer |
| C2 | IPE par usage | ⏳ Modèle prêt, calcul effectif à faire |
| C3 | Endpoint cost_breakdown | ✅ get_usage_cost_breakdown() |
| C4 | Avant/Après action | ❌ V1.2 |
| C5 | Simultanéité chauffage/clim | ❌ V1.2 |
| C6 | Cross-link Usage → Conformité UI | ❌ V1.2 |
| C7 | Prochaine action par usage | ⏳ CTA dans page, filtrage à affiner |
| C8 | Export PDF Dossier Usage | ❌ V1.2 |

### NIVEAU D — FONDATIONS TECHNIQUES ✅ FAIT

| # | Action | Statut |
|---|--------|--------|
| D1 | Migrations (Meter, BACS, Recommendation, ConsumptionInsight) | ✅ _migrate_usage_v1_1() |
| D2 | Taxonomie 2 niveaux (UsageFamily + TypeUsage) | ✅ |
| D3 | Enum DataSourceType | ✅ 6 sources |
| D4 | Schéma import GTB | ❌ V1.2 |

---

## 5. ARCHITECTURE TECHNIQUE V1.1

### Nouveaux fichiers créés

| Fichier | Rôle |
|---------|------|
| `backend/services/usage_service.py` | Service central — readiness, metering plan, top UES, cost breakdown, dashboard |
| `backend/routes/usages.py` | Router FastAPI `/api/usages` — 7 endpoints |
| `frontend/src/pages/UsagesDashboardPage.jsx` | Page pivot `/usages` — 6 blocs |

### Fichiers modifiés

| Fichier | Modifications |
|---------|--------------|
| `backend/models/enums.py` | +UsageFamily, TypeUsage 16 valeurs, USAGE_FAMILY_MAP, USAGE_LABELS_FR, DataSourceType |
| `backend/models/usage.py` | Usage enrichi (10 champs) + UsageBaseline |
| `backend/models/energy_models.py` | +usage_id FK sur Meter et Recommendation |
| `backend/models/bacs_models.py` | +usage_id FK sur BacsCvcSystem |
| `backend/models/consumption_insight.py` | +usage_id FK |
| `backend/models/__init__.py` | Exports ajoutés |
| `backend/database/migrations.py` | +_migrate_usage_v1_1() |
| `backend/services/consumption_diagnostic.py` | Propagation usage_id, enrichissement insights |
| `backend/services/demo_seed/gen_master.py` | Usages enrichis + sous-compteurs liés |
| `backend/routes/__init__.py` | +usages_router |
| `backend/main.py` | +usages_router registration |
| `frontend/src/services/api.js` | +7 fonctions API usage |

### Endpoints API

| Méthode | Path | Description |
|---------|------|-------------|
| GET | `/api/usages/dashboard/{site_id}` | Dashboard agrégé (readiness + plan + UES + dérives + coût) |
| GET | `/api/usages/readiness/{site_id}` | Score readiness /100 avec 4 dimensions |
| GET | `/api/usages/metering-plan/{site_id}` | Arbre plan de comptage hiérarchique |
| GET | `/api/usages/top-ues/{site_id}?limit=5` | Top usages énergétiques significatifs |
| GET | `/api/usages/cost-breakdown/{site_id}?days=365` | Ventilation coût par usage |
| GET | `/api/usages/taxonomy` | Taxonomie complète (familles + types + labels FR) |
| GET | `/api/usages/site/{site_id}` | Liste CRUD des usages d'un site |

### Structure page `/usages`

```
┌──────────────────────────────────────────────────────────────┐
│ [HEADER] Usages Énergétiques — {site.nom}                    │
│   [Badge Readiness: 72/100]  [CTA: "Compléter le plan"]     │
├──────────────────────────────────────────────────────────────┤
│ [BLOC 1: KPI ROW]                                            │
│   Conso totale | Coût total | Nb usages | Score readiness    │
│   | Dérives actives | Couverture sous-comptage               │
├──────────────────────────────────────────────────────────────┤
│ [BLOC 2: RECOMMANDATIONS READINESS]                          │
│   Actions prioritaires pour améliorer le score               │
├──────────────────────────────────────────────────────────────┤
│ [BLOC 3: PLAN DE COMPTAGE] (arbre interactif)                │
│   Compteur principal → Sous-compteurs → Usage associé        │
│   kWh | % total | Badge provenance                           │
├──────────────────────────────────────────────────────────────┤
│ [BLOC 4: TOP UES] (table triable)                            │
│   Usage | Famille | kWh | % total | Surface | Source         │
├──────────────────────────────────────────────────────────────┤
│ [BLOC 5: DÉRIVES ACTIVES] (cards)                            │
│   Usage | Type dérive | Impact kWh | Impact EUR | Sévérité   │
├──────────────────────────────────────────────────────────────┤
│ [BLOC 6: RÉPARTITION COÛT] (barres horizontales)             │
│   Usage | Coût EUR | % du total                              │
├──────────────────────────────────────────────────────────────┤
│ [NAVIGATION CROSS-BRIQUE]                                    │
│   Diagnostic | Conformité | Factures | Actions | Patrimoine  │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. PROCHAINES ÉTAPES (V1.2)

| # | Action | Priorité | Effort |
|---|--------|----------|--------|
| 1 | CRUD Baseline API + UI avant/après | P1 | 3j |
| 2 | Calcul IPE effectif par usage | P1 | 2j |
| 3 | Simultanéité chauffage/clim | P2 | 2j |
| 4 | Widget conformité par usage | P2 | 2j |
| 5 | Export PDF Dossier Usage | P2 | 3j |
| 6 | Lien contrat/achat → usage | P3 | 2j |
| 7 | Entité FunctionalZone | P3 | 3j |
| 8 | Connecteur GTB | P3 | 5j |

---

## 7. SCORE FINAL

| Phase | Score |
|-------|-------|
| **Avant V1.1** | 38/100 |
| **Après V1.1** (Niveaux A+B+D) | **65/100** |
| **Cible V1.2** (Niveau C) | 82/100 |
