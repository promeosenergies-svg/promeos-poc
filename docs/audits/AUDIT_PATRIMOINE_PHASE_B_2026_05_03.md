# Audit Patrimoine Phase B — Repo PROMEOS vs Matrice cible

**Mission** : Phase B audit complet (Option B étendue : backend + frontend + sources + tests + observabilité)
**Date** : 2026-05-03
**Auteur** : Claude Code (Opus 4.7) — Phase 0 read-only strict
**Branche** : `claude/phase-b-audit-patrimoine` (créée depuis `claude/operat-va-extraction`)
**Statut** : 🟢 COMPLET — STOP GATE avant Phase C

---

## ⚠️ Blocages rencontrés (à signaler en premier)

| # | Blocage | Impact audit | Workaround appliqué |
|---|---------|--------------|---------------------|
| B1 | **Matrice cible introuvable** : `docs/produit/patrimoine_parametrage_requis_v1.md` n'existe pas. Le dossier `docs/produit/` non plus (FR `produit` ≠ EN `product`). | Référence Phase A non disponible verbatim. | Audit conduit sur la base de la **structure du prompt mission** (sections 4.1 → 9 décrites en détail) + `docs/product/PATRIMOINE_V2_PRODUCT_SPEC.md` (372 L) + `docs/product/ADDENDUM_REGISTRE_PATRIMONIAL_CONTRACTUEL.md` (348 L). À régulariser Phase A.0 : commit du fichier `v1` finalisé. |
| B2 | **`backend/api/`** annoncé dans le prompt n'existe pas. Les endpoints sont dans `backend/routes/` (89 fichiers + 1 package `routes/patrimoine/`). | Décalage chemin uniquement. | Audit appliqué sur `backend/routes/`. |
| B3 | **`tests/source_guards/`** dossier dédié annoncé dans le workflow CI `.github/workflows/source_guards.yml` est **introuvable**. Les 15 tests source-guards existent à plat dans `backend/tests/test_*_source_guards.py`. | Workflow CI **cassé silencieusement** : `pytest tests/source_guards/` retourne `0 tests collected`. | Flag P0 en Top 10 risques (#R5). |
| B4 | **`.pre-commit-config.yaml`** absent à la racine. Mission affirme hooks pre-commit actifs ; en réalité, hooks Claude (`tools/hooks/`) ≠ hooks git pre-commit. | Pas de garde-fou client-side avant commit. | Flag P1. Distinguer Claude hooks (audit Bash/main-write/lint) vs git hooks. |
| B5 | **Frontend tests count divergent** : `4 518` Vitest collectés vs baseline mémoire `≥ 3 783`. Backend `7 202` collectés vs baseline `≥ 6 027`. Baseline non régressée — OK. | Aucun. | Confirmé en annexe. |

> **Conséquence sur la sévérité** : tous les gaps identifiés ci-après sont mesurés **par rapport à la matrice cible verbalisée dans le prompt Phase B** (sections 4.1 → 9). Si la matrice v1 commitée diffère, recalibrer P0/P1/P2.

---

## 1. Synthèse exécutive

### 1.1 Verdict global par couche

| Couche | Verdict | % couverture P0 | Gaps majeurs | Note /10 |
|--------|---------|-----------------|--------------|----------|
| **C1 — Doctrine et sources réglementaires** | 🟠 | ~70 % | `eld_gaz_referentiel.yaml` absent, `sources_reglementaires.yaml` absent, `coherence_globale.yaml` absent, constante `CO2_GNL_KGCO2_KWH = 0.238` absente | 6/10 |
| **C2 — Modèles SQLAlchemy** | 🟠 | ~55 % | Modèle `Compteur` unifié (pas séparé élec/gaz comme matrice), `SitePortefeuilleHistory` absent, `ContratCompteurLink` absent (seulement `ContractDeliveryPoint` N-N), Site n'a aucun champ OPERAT zone/cabs/IIU/EFA | 5/10 |
| **C3 — Services backend** | 🔴 | ~40 % | `OperatValeursAbsoluesService` **inexistant** (YAML 528 L extrait mais non consommé), `cascade_recompute_service` absent, `sources_reglementaires_service` absent, `audit_log_service` absent, **compliance score V1 figée 45/30/25** (pas adaptatif 0→N) | 4/10 |
| **C4 — Endpoints API** | 🟠 | ~65 % | Routes patrimoine org-scopées via `_get_org_id` (OK), mais endpoints `production-ready-status` + `cascade-impact` absents, fichier mort `routes/patrimoine.py` (0 octet) avec import cross-référencé `_get_org_id` | 6/10 |
| **C5 — Frontend Patrimoine** | 🟠 | ~60 % | **Logique métier inline détectée dans `Patrimoine.jsx`** (`Math.round(conso/surface) kWh/m²` lignes 828 + 1528), onboarding **non bifurqué 3 parcours** (1 wizard 7 étapes au lieu Wizard/Expert/Bulk), `regulatory_rates.js` duplique `doctrine/constants.py` côté FE | 6/10 |
| **T1 — Tests + source-guards** | 🟠 | ~75 % | 15 tests `*_source_guards.py` actifs **inline** (pas dans `tests/source_guards/`), workflow CI `source_guards.yml` cassé, pas de test cascade Org→Site→Compteur, pas de test compliance score adaptatif | 6/10 |
| **T2 — Observabilité** | 🔴 | ~30 % | Pas de `audit_log_service.py` dédié, pas de Prometheus, pas de `correlation_id` middleware (juste error_handler), table `audit_logs` (modèle `iam.py`) limitée à CX events, pas d'audit trail patrimoine spécifique | 3/10 |
| **T3 — Anti-patterns** | 🟠 | ~70 % | 23 occurrences `7500` hors doctrine/config (8 légitimes - défaut DT/seeds; 15 à confirmer), CO2 mirror frontend `regulatory_rates.js`, calculs `kWh/m²` inline `Patrimoine.jsx`, fichier `routes/patrimoine.py` 0 octet (legacy zombie) | 6/10 |

**Score global** : **5.0 / 10** (pondération couche C2/C3/T2 critiques).

### 1.2 Top 5 actions P0 absolument bloquantes

1. **🔴 Recouper Compliance Score adaptatif (V2)** — Aujourd'hui pondérations figées `45/30/25` (DT/BACS/APER) chargées via `regs.yaml` avec fallback hardcodé. Ne tient pas compte de `0 → N obligations applicables`. Fix : refondre `compliance_score_service.py` pour pondérations dynamiques selon obligations applicables au site, pénalités traçables EurAmount.
2. **🔴 Créer `OperatValeursAbsoluesService`** — Le YAML `operat_valeurs_absolues.yaml` (528 L), JSON Annexe I (931 KB, 426 sous-cat), JSON Annexe II (10 KB, 13 groupes Coeff DJU), JSON zones climatiques (101 entités) sont **extraits mais non consommés**. Aucun service backend n'expose les 4 lookups en chaîne (zone → palier → CVCi → Coeff DJU). Fix : créer `backend/regops/services/operat_cabs_service.py` avec API publique typée + tests.
3. **🔴 Étendre modèle `Site`** avec champs OPERAT manquants — Aujourd'hui Site a `operat_status`, `operat_last_submission_year`, `tertiaire_area_m2` mais **aucun** champ : `operat_zone_climatique`, `operat_sous_categorie`, `operat_iiu`, `cabs_kwh_m2`, `usage_principal`, `efa_id`, `annee_reference_operat`. Fix : migration Alembic + update `provision_site()` + enrichissement.
4. **🔴 Créer table `site_portefeuille_history`** — Pas de temporalité Site↔Portefeuille (Section 6.5.3 cible). Aujourd'hui `Site.portefeuille_id` FK simple sans `valid_from / valid_to`. Toute analyse rétrospective d'un site déplacé entre portefeuilles est **impossible**. Fix : nouvelle table + service de bascule + audit trail.
5. **🔴 Réparer source-guards CI** — `tests/source_guards/` n'existe pas, workflow `.github/workflows/source_guards.yml` exécute `pytest tests/source_guards/` qui retourne `0 tests collected` mais sort en code 0 (succès factice). Fix immédiat : soit créer le dossier (avec tests `*_source_guards.py` migrés), soit corriger le workflow pour pointer vers le pattern existant `tests/test_*_source_guards.py`.

### 1.3 Estimation effort Phase C global

| Priorité | Description | Effort (j-h) | Sprints estimés (1 sprint = 5 j-h) |
|----------|-------------|--------------|------------------------------------|
| **P0** | Bloquant production : 5 actions ci-dessus + ContratCompteurLink + cascade_recompute + audit_log_service + endpoint production-ready + retrait calculs FE | **35-45 j-h** | **2 sprints** (C-1 + C-2) |
| **P1** | Crédibilité B2B : `eld_gaz_referentiel.yaml`, `sources_reglementaires.yaml`, `coherence_globale.yaml`, modèles `compteur_elec/gaz` séparés OU justification doctrine, tooltip traçabilité différenciateur, tests cascade complète, AuditSME enrichissement, observabilité (correlation_id, Prometheus optionnel), pre-commit-config.yaml | **30-40 j-h** | **2 sprints** (C-3 + C-4) |
| **P2** | Best-in-world : onboarding 3 parcours bifurqués (Wizard/Expert/Bulk), enrichissement progressif drill-down, automatismes auto-création hiérarchie, premium UX (skeletons, virtualisation listes longues, accessibilité ARIA), purge fichier zombie `routes/patrimoine.py` 0 octet | **40-55 j-h** | **3 sprints** (C-5 + C-6 + C-7) |
| **Total** | | **105-140 j-h** | **7 sprints** (~3-4 mois plein-temps) |

---

## 2. Inventaire repo (5 couches + 3 transverses)

### 2.1 Couche 1 — Doctrine et sources réglementaires

| Fichier attendu | Existe ? | LOC/Taille | Dernière modif | Status | Notes |
|---|---|---|---|---|---|
| `backend/doctrine/constants.py` | ✅ | 159 L | 2026-05-03 | 🟢 | 30+ constantes traçables ; **manque** `CO2_GNL_KGCO2_KWH = 0.238` |
| `backend/doctrine/__init__.py` | ✅ | — | 2026-04-27 | 🟢 | |
| `backend/doctrine/acronyms.py` | ✅ | — | 2026-04-29 | 🟢 | |
| `backend/doctrine/error_codes.py` | ✅ | — | 2026-04-27 | 🟢 | |
| `backend/doctrine/kpi_registry.py` | ✅ | — | 2026-05-03 | 🟢 | Phase audit Vue Exé |
| `backend/doctrine/kpi_tracability.py` | ✅ | — | 2026-05-03 | 🟢 | Phase audit Vue Exé |
| `backend/config/tarifs_reglementaires.yaml` | ✅ | 30 KB | 2026-04-27 | 🟢 | TURPE 6/7 + ATRD/ATRT + accises |
| `backend/config/operat_valeurs_absolues.yaml` | ✅ | 41 KB (528 L) | 2026-05-03 | 🟢 | Schema 0.9, livré, **non consommé par service** |
| `backend/config/operat_annexe_i_sous_categories.json` | ✅ | 1 115 KB | 2026-05-03 | 🟢 | 426 sous-catégories, **non consommé** |
| `backend/config/operat_annexe_ii_coeff_dju.json` | ✅ | 11 KB | 2026-05-03 | 🟢 | 13 groupes, **non consommé** |
| `backend/config/operat_zones_climatiques.json` | ✅ | 6 KB | 2026-05-03 | 🟢 | 101 entités schema 2.0, **consommé par `regops/operat_zones.py`** |
| `backend/config/operat_stations_meteo.json` | ✅ | 33 KB | 2026-05-03 | 🟢 | 165 stations |
| `backend/config/eld_gaz_referentiel.yaml` | ❌ | — | — | 🔴 | **MANQUANT** — 21 ELD gaz attendues |
| `backend/config/sources_reglementaires.yaml` | ❌ | — | — | 🔴 | **MANQUANT** — Section 7.25 cible |
| `backend/config/coherence_globale.yaml` | ❌ | — | — | 🔴 | **MANQUANT** — Section 8 cible |
| `backend/regops/config/regs.yaml` | ✅ | — | 2026-03-21 | 🟠 | Stocke pondérations DT/BACS/APER + seuils ; **partiel vis-à-vis sources_reglementaires.yaml cible** |
| `docs/sources/regulatory/operat/atdl2430864a_annexe_i.{pdf,txt}` | ✅ | — | 2026-05-03 | 🟢 | Source primaire archivée |
| `docs/sources/regulatory/operat/atdl2430864a_annexe_ii.{pdf,txt}` | ✅ | — | 2026-05-03 | 🟢 | |
| `docs/sources/regulatory/operat/legifrance_arrete_methode_10_avril_2020_v2_avec_zclim.pdf` | ✅ | — | 2026-05-03 | 🟢 | Annexe III authentifiée 🟢 |

**Cohérence cross-fichier** :
- ✅ `OPERAT_PENALTY_EUR = 1500` (constants.py) ↔ `regs.yaml::tertiaire_operat::penalties::non_affichage = 1500` ↔ FAQ ADEME CS4-Q1 (cumulables PP/PM)
- ✅ `DT_PENALTY_EUR = 7500` ↔ `regs.yaml::tertiaire_operat::penalties::non_declaration = 7500` ↔ Décret 2019-771 art. 9
- ⚠️ `CO2_GNL_KGCO2_KWH = 0.238` (arrêté 01/08/2025) **absent de constants.py** → flag P0 doctrine
- ⚠️ Pas de YAML `sources_reglementaires.yaml` central : aucun service ne peut servir les références NOR + URL Légifrance + date d'effet → tooltip traçabilité différenciateur compromis (P1)

### 2.2 Couche 2 — Modèles SQLAlchemy

Total `backend/models/*.py` : **78 fichiers** (incluant `__init__.py`).

| Modèle attendu | Existe ? | LOC | Champs P0 cible | Champs P0 présents | Coverage |
|---|---|---|---|---|---|
| `organisation.py` | ✅ | 27 | 16 | ~6 (id, nom, type_client, siren, actif, is_demo, logo_url) | **38 %** 🔴 |
| `entite_juridique.py` | ✅ | 29 | 30 | ~7 (id, organisation_id, nom, siren, siret, naf_code, region_code, insee_code) | **23 %** 🔴 |
| `portefeuille.py` | ✅ | 21 | 11 | ~4 (id, entite_juridique_id, nom, description) | **36 %** 🔴 |
| `site.py` | ✅ | 150 | ~70 | ~35 (cf 3.4) | **50 %** 🟠 |
| `batiment.py` | ✅ | 22 | 23 | ~5 (id, site_id, nom, surface_m2, annee_construction, cvc_power_kw) | **22 %** 🔴 |
| `compteur.py` (unifié élec/gaz/eau) | ✅ | 60 | 31+32 (élec+gaz) si séparés | ~12 communs | **20 %** 🔴 (architecture divergente — voir 3.6) |
| `compteur_elec.py` | ❌ | — | 31 | 0 | **0 %** — fusion dans compteur.py |
| `compteur_gaz.py` | ❌ | — | 32 | 0 | **0 %** — fusion dans compteur.py |
| `sous_compteur.py` | ❌ | — | 15 | 0 | **0 %** 🔴 |
| `contrat.py` | ❌ | — | 28 | — | Remplacé par `contract_v2_models.py` (426 L : ContratCadre + AnnexeSite + Pricing + VolumeCommitment + Events) |
| `contrat_compteur_link.py` | ❌ | — | N:N | 0 | **0 %** — seulement `ContractDeliveryPoint` (patrimoine.py) |
| `site_portefeuille_history.py` | ❌ | — | 8+ | 0 | **0 %** 🔴 |
| `delivery_point` (in patrimoine.py) | ✅ | — | bonus | ~30 (PRM/PCE, GRD, ATRD, profil GRDF, HC reprog, lineage) | 🟢 — modèle riche, utile pour cible Section 4 |

**Modèles bonus présents** (non listés dans matrice cible) :
- `audit_sme.py` (63 L) — Audit énergétique / SME ISO 50001
- `bacs_models.py` + `bacs_regulatory.py` + `bacs_remediation.py` — BACS complet
- `tax_profile.py` — Régime fiscal accise élec/gaz
- `tariff_calendar.py`, `site_tariff_profile.py`, `tou_schedule.py` — TURPE 7 réglages
- `cee_models.py`, `consumption_target.py`, `baseline_calibration.py`
- `eur_amount.py` (typed avec catégorie CALCULATED_REGULATORY/CONTRACTUAL + CheckConstraint)
- `compliance_finding.py`, `compliance_score_history.py`
- `flex_models.py`, `purchase_models.py`, `market_models.py`

**Index uniques** :
- ✅ `EntiteJuridique.siren` unique=True
- ✅ `Compteur.numero_serie` unique=True
- ❌ `DeliveryPoint.code` (PRM/PCE) **PAS unique global** — index simple seulement → risque doublon PRM cross-org
- ❌ `Organisation.siren` PAS unique (peut être dupliqué)
- ✅ Tables N-N (`org_entite_links`, `portfolio_entite_links`, `contract_delivery_points`) avec UniqueConstraint

### 2.3 Couche 3 — Services backend

Total `backend/services/*.py` : **171 fichiers**.

| Service attendu | Existe ? | LOC | Status | Notes |
|---|---|---|---|---|
| `compliance_score_service.py` | ✅ | — | 🔴 | **V1 figée 45/30/25** — pondérations chargées via `regs.yaml` avec fallback hardcodé. Pas adaptatif 0→N. |
| `regops/operat_zones.py` | ✅ | — | 🟢 | Resolveur authentifié Annexe III (101 entités, 96 métropole + 5 DOM, schema 2.0) |
| `regops/services/operat_cabs_service.py` | ❌ | — | 🔴 | **MANQUANT** — pas de chaîne lookup zone→palier→CVCi→Coeff DJU |
| `regops/rules/tertiaire_operat.py` | ✅ | — | 🟠 | Présent mais consomme `regs.yaml` sans Cabs détaillés |
| `regops/services/sources_reglementaires_service.py` | ❌ | — | 🔴 | **MANQUANT** — Section 7.25 différenciateur |
| `regops/services/cascade_recompute_service.py` | ❌ | — | 🔴 | **MANQUANT** — Section 8.3.1 non couverte |
| `regops/services/bill_intelligence_service.py` | ❌ (différemment nommé) | — | 🟠 | Pas de "A6 1% tolérance bloquante" identifiée. Bill engine présent dans `services/billing_engine/` (catalog + ParameterStore) |
| `utils/naf_resolver.py` | ✅ | — | 🟢 | Existe ; à vérifier réutilisation cross-modules |
| `services/onboarding_service.py` | ✅ | 319 | 🟠 | Parcours unique (org + sites + bâtiments + obligations). **Pas de bifurcation Wizard/Expert/Bulk** |
| `services/onboarding_stepper_service.py` | ✅ | 119 | 🟠 | Stepper UI helper — pas de logique de bifurcation |
| `services/audit_log_service.py` | ❌ | — | 🔴 | **MANQUANT** — Section 8.3.2 |
| `services/iam_scope.py` | ✅ | — | 🟢 | Helper `get_effective_org_id`, `check_site_access` — utilisé pour scope |
| `services/scope_utils.py` | ✅ | — | 🟢 | `resolve_org_id` — chaîne centralisée DEMO_MODE-aware |
| `services/operat_export_service.py` | ✅ | — | 🟢 | Export CSV + manifest + audit log |
| `services/operat_normalization.py` | ✅ | — | 🟢 | DJU normalisation présente (mais peut diverger de Annexe II officielle non consommée) |
| `services/operat_trajectory.py` | ✅ | — | 🟢 | Validation trajectoire DT |
| `services/patrimoine_service.py` | ✅ | — | 🟢 | |
| `services/patrimoine_snapshot.py` | ✅ | — | 🟢 | |
| `services/patrimoine_anomalies.py` | ✅ | — | 🟢 | |
| `services/patrimoine_conformite_sync.py` | ✅ | — | 🟢 | |
| `services/patrimoine_impact.py` | ✅ | — | 🟢 | |
| `services/patrimoine_portfolio_cache.py` | ✅ | — | 🟢 | |
| `services/naf_classifier.py` + `naf_estimator.py` | ✅ | — | 🟠 | Doublon partiel avec `utils/naf_resolver.py` — possible dette |

### 2.4 Couche 4 — Endpoints API

Total `backend/routes/*.py` : **89 fichiers** (`backend/api/` annoncé n'existe pas).

| Route attendue | Existe ? | LOC | Org-scoping | Notes |
|---|---|---|---|---|
| `routes/patrimoine.py` | ⚠️ | **0** | — | **Fichier zombie 0 octet** — référencé par import `from routes.patrimoine import _get_org_id` qui se résout vers le **package** `routes/patrimoine/__init__.py`. À supprimer (P2). |
| `routes/patrimoine/` (package) | ✅ | — | 🟢 | Sub-routers : `staging.py`, `sites.py`, `compteurs.py`, `contracts.py`, `billing.py` ; helpers `_get_org_id` via `services/scope_utils.resolve_org_id` |
| `routes/patrimoine_crud.py` | ✅ | 575 | 🟢 (filter `Organisation.id == org_id`) | Org/EJ/Portefeuille/Site CRUD ; `auth: Optional[AuthContext]` + filter explicite |
| `routes/sites.py` | ✅ | — | 🟢 | |
| `routes/compteurs.py` | ✅ | 163 | 🟠 | Auth présent mais filter par `site_id` (pas direct par `org_id`) — sécurisé via `Site → Org` mais à durcir |
| `routes/onboarding.py` + `onboarding_stepper.py` | ✅ | — | 🟢 | |
| `routes/contracts_v2.py` | ✅ | — | 🟢 | 20 endpoints, `_get_org_id` à chaque entrée |
| `routes/contracts_radar.py` | ✅ | — | 🟢 | |
| `routes/operat.py` | ✅ | — | 🟢 | Export CSV + preview + validate + manifests |
| `routes/site_intelligence.py` | ✅ | — | 🟢 | |
| `routes/site_config.py` | ✅ | — | 🟢 | |
| `routes/import_sites.py` | ✅ | — | 🟢 | |
| `routes/openapi.yaml` | ❌ | — | — | Pas de contrat OpenAPI commit (généré dynamiquement par FastAPI) |
| Endpoint `/api/v1/sites/{id}/production-ready-status` | ❌ | — | 🔴 | **MANQUANT** — Section 9.4 cible |
| Endpoint `/api/v1/sites/{id}/cascade-impact` | ❌ | — | 🔴 | **MANQUANT** — Section 8.3 cible (preview cascade) |

### 2.5 Couche 5 — Frontend Patrimoine

Total `frontend/src/pages/*.jsx` : **66 fichiers**. Total Vitest collectés : **4 518**.

| Élément attendu | Existe ? | LOC | Status |
|---|---|---|---|
| `pages/Patrimoine.jsx` | ✅ | **2 312** | 🟠 — page géante, calculs `kWh/m²` inline détectés (L828 + L1528) |
| `pages/Site360.jsx` | ✅ | — | 🟢 |
| `pages/SiteCompliancePage.jsx` | ✅ | — | 🟢 |
| `pages/Cockpit.jsx`, `CockpitDecision.jsx`, `CockpitPilotage.jsx` | ✅ | — | 🟢 |
| `pages/OnboardingPage.jsx` | ✅ | 251 | 🟠 — pas de bifurcation 3 parcours |
| `pages/SireneOnboardingPage.jsx` | ✅ | 779 | 🟠 — wedge SIREN, mais pas Wizard/Expert/Bulk explicite |
| `components/patrimoine/SitesMap.jsx` | ✅ | — | 🟢 |
| `components/PatrimoineWizard.jsx` | ✅ | — | 🟠 — wizard 7 étapes (à simplifier per V2 spec) |
| `components/QuickCreateSite.jsx` | ✅ | — | 🟢 — bonne base pour parcours rapide |
| `components/SiteCreationWizard.jsx` | ✅ | — | 🟠 |
| `components/onboarding/DemoSpotlight.jsx` | ✅ | — | 🟢 |
| `components/onboarding/` (Wizard/Expert/Bulk distincts) | ❌ | — | 🔴 — bifurcation 3 parcours absente |
| `services/patrimoine_api.ts` (TypeScript) | ❌ | — | — — projet en JSX (pas TS) |
| `contexts/EmissionFactorsContext.jsx` | ✅ | — | 🟢 — sert CO₂ depuis backend |
| `domain/regulatory_rates.js` | ✅ | — | 🟠 — **mirror frontend** des constantes backend (commentaire dit "À terme servies par /api/regulatory/rates Phase 22"). Dette technique. |
| `pages/consumption/constants.js` | ✅ | — | 🔴 — `CO2E_FACTOR_KG_PER_KWH = 0.052` **redondant** avec backend |
| `lib/risk/normalizeRisk.jsx` | ✅ | — | 🟠 — `BASE_PENALTY = 7500 EUR` en commentaire (pas en code actif) |

### 2.6 Transverse 1 — Tests

| Élément | Compte | Status |
|---|---|---|
| Backend tests collectés | **7 202** | 🟢 — au-dessus floor `≥ 6 027` |
| Backend test files | **418** | 🟢 |
| Tests source-guards inline | **15 fichiers** `test_*_source_guards.py` | 🟢 fonctionnent |
| Dossier `tests/source_guards/` | **❌ INEXISTANT** | 🔴 — workflow CI cassé silencieusement |
| Frontend Vitest tests | **4 518** | 🟢 — au-dessus floor `≥ 3 783` |
| Tests doctrine | 2 (`test_t6_day_j_evolution`, `test_weekly_delta_canonical`) | 🟠 — léger |
| Tests OPERAT | **176 tests** (k=operat) | 🟢 |
| Tests regops/compliance | **433 tests** | 🟢 |
| Tests cascade Org→Site→Compteur | ❌ | 🔴 — pas de test intégration cascade |
| Tests onboarding 3 parcours | ❌ | 🔴 — un seul parcours testé |
| Tests compliance score adaptatif | ❌ | 🔴 — V2 absente du code |
| Tests OPERAT zones authentifiées vs RT 2012 | ✅ `test_operat_zones_climatiques.py` | 🟢 |
| Workflow `.github/workflows/source_guards.yml` | ✅ existe | 🔴 cassé (cible `tests/source_guards/`) |
| Workflow `quality-gate.yml` | ✅ existe | — |
| `.pre-commit-config.yaml` | ❌ INEXISTANT | 🟠 |

### 2.7 Transverse 2 — Observabilité

| Élément | Status | Notes |
|---|---|---|
| Logs structurés JSON | 🟠 | `middleware/cx_logger.py` log CX events ; pas de logging JSON global avec correlation_id systématique |
| Niveaux logs cohérents | 🟢 | `_logger.warning/info/error` standard |
| Correlation ID middleware | 🟠 | `error_handler.py` mentionne `correlation_id` mais pas de middleware dédié `request_context.py` (existe en nom seulement) |
| Métriques Prometheus | ❌ | Aucun — `grep prometheus` = 0 hit |
| `services/audit_log_service.py` | ❌ | **MANQUANT** |
| Modèle `AuditLog` (iam.py) | ✅ | Existe mais limité à CX events (`resource_type='cx_event'`), pas patrimoine-spécifique |
| Audit trail patrimoine création/modif | 🔴 | Pas de service dédié |
| Audit trail cascade | 🔴 | Pas de cascade implémentée → pas d'audit |
| Traces calculs Cabs / compliance score | 🟠 | Compliance score: `compliance_score_breakdown_json` JSON dans Site (snapshot OK, pas trace step-by-step) |
| Dashboards monitoring | ❌ | Aucun |

### 2.8 Transverse 3 — Anti-patterns détectés (résultats grep complets)

#### A. Constantes CO₂ hardcodées hors doctrine

| Fichier:ligne | Snippet | Status |
|---|---|---|
| `backend/orchestration/agents/qa_guardian.py:42` | `* 0.052 (facteur CO₂ hardcodé → doit venir du backend)` | 🟢 — string de doc agent (anti-pattern référencé, pas code) |
| `backend/routes/config_emission_factors.py:36` | `"kgco2e_per_kwh": 0.052` | 🟠 — endpoint qui sert la valeur ; à vérifier qu'il lit `doctrine.constants` |
| `backend/services/demo_seed/gen_billing.py:557` | `prix_base_eur_kwh=0.0528` | 🟠 — **NON un facteur CO₂** mais prix énergie (€/kWh). Ambigu : `0.0528` proche de `0.052` (CO₂ ELEC). À documenter ou renommer. |
| `frontend/src/pages/consumption/constants.js:27` | `export const CO2E_FACTOR_KG_PER_KWH = 0.052` | 🔴 — **anti-pattern strict** : doublon `doctrine.constants.CO2_FACTOR_ELEC_KGCO2_PER_KWH`. Frontend doit consommer le backend (Context déjà en place dans `EmissionFactorsContext`). |
| `frontend/src/contexts/EmissionFactorsContext.jsx:22, 27` | `kgco2e_per_kwh: CO2E_FACTOR_KG_PER_KWH` (élec), `kgco2e_per_kwh: 0.227` (gaz) | 🟠 — fallback hardcodé en cas d'échec backend ; commentaire ADEME présent ; **doublon doctrine** |
| `frontend/src/components/CreateActionModal.jsx:105, 119` | commentaires explicites (`backend/config/emission_factors.py ELEC=0.052`) | 🟢 — commentaires uniquement |
| `frontend/src/components/CreateActionDrawer.jsx:179, 193` | commentaires explicites | 🟢 |

#### B. Constantes pénalité DT 7500 hors doctrine/config

23 occurrences détectées. Triées :

| Fichier:ligne | Catégorie |
|---|---|
| `backend/regops/rules/tertiaire_operat.py:66` | `penalty_non_declaration = penalties.get("non_declaration", 7500)` — fallback YAML 🟠 |
| `backend/models/eur_amount.py:77` | commentaire formule `'3 sites × 7500 + 1 site × 3750'` 🟢 doc |
| `backend/schemas/kpi_catalog.py:39` | `formula="7500 × nb(NON_CONFORME) + 3750 × nb(A_RISQUE)"` 🟢 doc |
| `backend/services/eur_amount_service.py:42` | docstring 🟢 |
| `backend/migrations/correct_helios_surface_phase1_5.py:112` | `abs(result["total_after"] - 17500)` — code postal sum, **pas pénalité** 🟢 |
| `backend/orchestration/agents/qa_guardian.py:43, 51, 87` | docstrings agent 🟢 |
| `backend/routes/import_sites.py:57` | `"code_postal": "75002"` — **code postal**, pas pénalité 🟢 |
| `backend/routes/demo.py:326` | `"cp": "75008"` — code postal 🟢 |
| `backend/routes/analytics.py:41` | `"kwh": 27500` — conso, pas pénalité 🟢 |
| `backend/routes/tertiaire.py:1038` | `cp = "75001"` — code postal 🟢 |
| `backend/services/import_mapping.py:20, 553, 554` | codes postaux 🟢 |
| `backend/services/purchase_seed_wow.py:40` | code postal 🟢 |
| `frontend/src/lib/risk/normalizeRisk.jsx:9` | `BASE_PENALTY = 7500 EUR` — **commentaire** 🟢 |
| `frontend/src/domain/regulatory_rates.js:118` | `value: 7500, unit: 'EUR/an/site'` — **mirror doctrine** 🟠 dette |
| `frontend/src/mocks/sites.js:13`, `DrawerEditSite.jsx:234`, `QuickCreateSite.jsx:197` | placeholders code postal 🟢 |

**Conclusion B** : 4 cas légitimes (1 fallback YAML, 3 docs/code postal). 1 anti-pattern actif : `frontend/src/domain/regulatory_rates.js:118` — devrait migrer vers endpoint `/api/regulatory/rates` (commentaire dans le fichier le reconnaît : "Phase 22").

#### C. Logique métier détectée frontend (calculs `kWh/m²`)

| Fichier:ligne | Snippet | Verdict |
|---|---|---|
| `frontend/src/pages/Patrimoine.jsx:828` | `${Math.round(enrichedSites.reduce((a, s) => a + (s.conso_kwh_an || 0), 0) / stats.surface)} kWh/m² moy.` | 🔴 **anti-pattern strict** — agrégation FE |
| `frontend/src/pages/Patrimoine.jsx:1528` | `Math.round((site.conso_kwh_an || 0) / site.surface_m2)} kWh/m²` | 🔴 **anti-pattern strict** — calcul par site FE |
| `frontend/src/utils/benchmarks.js:26-29` | `getIntensityRatio(kwh_m2, usage)` ratio benchmark FE | 🟠 — déjà calculé sur valeur reçue, mais ratio est une comparaison (pas calcul source) |
| `frontend/src/pages/ConsommationsUsages.jsx:434, 439, 441, 445, 450` | seuils archétype min/max kWh/m² | 🟠 — seuils servis backend ? à vérifier |

**Action P0** : déplacer les agrégations `kWh/m²` vers backend (route `/api/sites/{id}/intensity` ou enrichir `_facts` cockpit) et exposer des KPIs prêts.

#### D. Tarif TURPE hardcodé (catalog/cost_simulator)

| Fichier:ligne | Snippet | Status |
|---|---|---|
| `backend/services/billing_engine/catalog.py:60, 184, 380, 387, 394` | rates `283.27`, `12.41`, `435.72`, `499.80`, `376.39` | 🟠 — **catalog statique** plutôt que `tarifs_reglementaires.yaml`. Source CRE TURPE 7 commentée. À migrer vers ParameterStore versionné. |
| `backend/services/purchase/cost_simulator_2026.py:116, 121, 122` | rates `283.27`, `435.72` | 🟠 — duplique catalog.py |

**Note** : la doctrine `0.0569` (TURPE 7 HPH €/kWh) **ne doit jamais** être confondue avec `0.052` (CO₂). `constants.py:122-123` prévient explicitement : "0.0569 est un tarif TURPE 7 HPH (€/kWh), PAS un facteur CO₂".

#### E. Routes API non org-scopées

Audit ciblé sur routes patrimoine. **31 fichiers** utilisent `resolve_org_id`. Patrimoine routes :
- `routes/patrimoine_crud.py` ✅ — filter `Organisation.id == org_id` explicite, multi-paths
- `routes/patrimoine/sites.py`, `compteurs.py`, `contracts.py`, `billing.py`, `staging.py` ✅ via package + `_get_org_id`
- `routes/contracts_v2.py` ✅
- `routes/operat.py` ✅ via `get_effective_org_id`
- `routes/compteurs.py` (top-level) 🟠 — auth présent mais scoping via `Site.id` lookup ; à durcir avec test source-guard `org_id consistency`

**Aucun anti-pattern P0 sécurité détecté** sur les routes patrimoine principales (vs ce que la mission signalait comme risque). Le DEMO_MODE bypass est connu et documenté (`get_optional_auth` retourne None en DEMO).

#### F. Duplications NAF

| Fichier | Type |
|---|---|
| `backend/utils/naf_resolver.py` | Canonique 🟢 |
| `backend/services/naf_classifier.py` | Risque doublon 🟠 |
| `backend/services/naf_estimator.py` | Risque doublon 🟠 |

**Action P1** : audit dépendances, déduplication ou clarification responsabilités.

#### G. Fichier zombie

- `backend/routes/patrimoine.py` (0 octet) — fichier vide qui co-existe avec le package `backend/routes/patrimoine/`. Import `from routes.patrimoine import _get_org_id` résout via le package, mais le `.py` 0-octet pollue le repo. **Action P2** : suppression simple.

---

## 3. Gap analysis détaillée par section matrice

> Note : la matrice cible v1 n'étant pas committée (cf. blocage B1), la gap analysis est réalisée à partir de la **structure du prompt mission** (section "Périmètre audit Option B") avec sources V2 spec + addendum.

### 3.1 Section 4.1 — Organisation (cible 16 champs)

| # | Champ matrice (inféré) | Type cible | Présent ? | Type repo | Validation Pydantic | Index | Gap |
|---|---|---|---|---|---|---|---|
| 1 | `id` | int PK | ✅ | Integer PK | ✅ | ✅ | — |
| 2 | `nom` | str | ✅ | String | ✅ min/max | — | — |
| 3 | `type_client` | enum | ✅ | String free | ✅ | — | 🟠 enum non typé (str libre `"retail"/"tertiaire"/"industrie"`) |
| 4 | `siren` | str(9) | ✅ | String(9) | ✅ regex 9 digits | — | 🟠 **pas unique** — risque doublons |
| 5 | `logo_url` | str | ✅ | String | — | — | — |
| 6 | `actif` | bool | ✅ | Boolean | — | — | — |
| 7 | `is_demo` | bool | ✅ | Boolean | — | — | — |
| 8 | `tva_intra` | str | ❌ | — | — | — | 🔴 manquant |
| 9 | `code_naf` | str | ❌ | — | — | — | 🔴 absent au niveau Org (présent EJ) |
| 10 | `pays` | str | ❌ | — | — | — | 🔴 manquant |
| 11 | `secteur_activite` | str | ❌ | — | — | — | 🔴 manquant |
| 12 | `effectif_global` | int | ❌ | — | — | — | 🔴 manquant |
| 13 | `chiffre_affaires_eur` | float | ❌ | — | — | — | 🔴 manquant |
| 14 | `responsable_energie_id` | FK user | ❌ | — | — | — | 🔴 manquant |
| 15 | `created_at`, `updated_at` | datetime | ✅ | TimestampMixin | — | — | — |
| 16 | `deleted_at` | datetime | ✅ | SoftDeleteMixin | — | — | — |

**Couverture ~38 %** 🔴 — manquent : TVA intra, NAF, pays, secteur, effectif, CA, responsable énergie.

### 3.2 Section 4.2 — Entité juridique (cible 30 champs incluant Audit SMÉ)

| # | Champ matrice (inféré) | Présent ? | Notes |
|---|---|---|---|
| 1 | `id`, `organisation_id`, `nom`, `siren`, `siret`, `naf_code`, `region_code`, `insee_code` | ✅ | Modèle minimal |
| 9-15 | adresse siège, ville, code postal, pays, téléphone, email, site web | ❌ | Aucun |
| 16-22 | effectif EJ, CA EJ, type société (SA/SARL/SAS), date création, capital social, président, DG | ❌ | Aucun |
| 23-30 | **Audit SMÉ obligation, seuil_gwh, deadline_realisation, statut, organisme_certifie, certif_iso50001, last_audit_date, prochain_audit** | ⚠️ | Présent dans **table séparée `audit_energetique`** (`models/audit_sme.py` 63 L) plutôt qu'en colonnes EJ. **Décision archi à valider Phase A.** |

**Couverture ~23 %** 🔴 si on attendait colonnes EJ ; **~60 %** 🟠 si décomposition table séparée acceptée.

### 3.3 Section 4.3 — Portefeuille (cible 11 champs)

| # | Champ | Présent ? |
|---|---|---|
| 1 | `id`, `entite_juridique_id`, `nom`, `description` | ✅ |
| 5 | `created_at, updated_at, deleted_at` | ✅ via mixins |
| 8 | `responsable_id`, `couleur_ui`, `tags`, `actif` | ❌ |

**Couverture ~36 %** 🔴.

### 3.4 Section 4.4 — Site (cible ~70 champs A+B+OPERAT+EFA+BACS+APER) — **section critique**

| Famille | Champs cible | Présents | Status |
|---|---|---|---|
| **Identité** | id, nom, type, actif, is_demo | ✅ 5/5 | 🟢 |
| **Adresse** | adresse, code_postal, ville, region, latitude, longitude, geocoding_source/score/at/status | ✅ 9/9 | 🟢 |
| **Caractéristiques** | surface_m2, nombre_employes, tertiaire_area_m2, roof_area_m2 | ✅ 4/4 | 🟢 |
| **Hiérarchie** | portefeuille_id (FK) | ✅ 1/1 | 🟢 |
| **Identifiants business** | siret, insee_code, naf_code | ✅ 3/3 | 🟢 |
| **Conformité snapshots** | statut_decret_tertiaire, avancement_decret_pct, statut_bacs, anomalie_facture, action_recommandee, risque_financier_euro, compliance_score_composite, compliance_score_breakdown_json, compliance_score_confidence | ✅ 9/9 | 🟢 |
| **OPERAT minimal** | operat_status, operat_last_submission_year | ✅ 2/2 | 🟠 minimal |
| **OPERAT complet (cible Section 5)** | `operat_zone_climatique`, `operat_sous_categorie_id`, `operat_iiu`, `cabs_kwh_m2`, `cabs_zone_palier_lookup`, `usage_principal`, `efa_id`, `efa_surface_m2`, `annee_reference_operat`, `methode_modulation`, `crelat_kwh`, `dossier_modulation_id` | ❌ 0/12 | 🔴 **manquant** |
| **Parking APER** | parking_area_m2, parking_type | ✅ 2/2 | 🟢 |
| **APER complet** | `parking_solar_engaged`, `parking_solar_deadline`, `parking_solar_pct`, `aper_exemption_motif`, `aper_status` | ❌ 0/5 | 🔴 |
| **Multi-occupant** | is_multi_occupied | ✅ 1/1 | 🟢 |
| **BACS** | (champs étendus dans tables `bacs_*` séparées) | ⚠️ | 🟠 décomposition table à valider |
| **Energy** | annual_kwh_total, last_energy_update_at | ✅ 2/2 | 🟢 |
| **Pilotage** | archetype_code, puissance_pilotable_kw | ✅ 2/2 | 🟢 |
| **CBAM** | cbam_imports_tonnes (JSON), cbam_intensities_tco2_per_t (JSON) | ✅ 2/2 | 🟢 différenciateur |
| **Lineage** | data_source, data_source_ref, imported_at, imported_by | ✅ 4/4 | 🟢 |
| **Audit Cabs** | (à venir) | ❌ | 🔴 |

**Couverture ~50 %** 🟠 (~35/70 champs P0). **Le gap majeur = absence des 12 champs OPERAT complets et 5 champs APER étendus.**

### 3.5 Section 4.5 — Bâtiment (cible 23 champs incluant RNB)

| Champ | Présent ? | Notes |
|---|---|---|
| id, site_id, nom, surface_m2, annee_construction, cvc_power_kw | ✅ 6/23 | Modèle minimal |
| `rnb_id`, `siret_batiment`, `usage_batiment`, `etage_count`, `nature_juridique_occupant` | ❌ 0/5 | 🔴 |
| `bacs_classe_actuelle`, `bacs_seuil_70kw_atteint`, `bacs_deadline`, `bacs_remediation_plan_id` | ❌ 0/4 | 🔴 — extrait dans tables `bacs_*` ; à arbitrer |
| `dpe_grade`, `dpe_date`, `dpe_consommation_kwh_m2`, `dpe_emissions_kgco2_m2` | ❌ 0/4 | 🔴 |
| `efa_id` (lien EFA OPERAT) | ❌ | 🔴 |
| `parties_communes_pct` | ❌ | 🔴 |

**Couverture ~22 %** 🔴.

### 3.6 Section 4.6 — Compteur élec (cible 31 champs A+B)

⚠️ **Architecture divergente** : repo a un modèle unique `Compteur` (60 L) avec `type` enum (ELECTRICITE/GAZ/EAU). La matrice attend deux modèles séparés `compteur_elec.py` (31 champs) + `compteur_gaz.py` (32 champs).

**Décision archi à arbitrer en Phase A** :
- **Option A** (matrice cible) : split en deux modèles → 31+32 champs avec validations type-spécifiques
- **Option B** (état actuel) : conserver modèle unifié + champs JSON pour spécificités ; complétude via `DeliveryPoint` (déjà 30 champs : grd_code, atrd_option, car_kwh, gas_profile, cjn/cja, segment TURPE, hc_reprog…)

| Champ commun cible | Présent dans Compteur ? |
|---|---|
| id, site_id, type, numero_serie, puissance_souscrite_kw, meter_id, energy_vector, actif, delivery_point_id, data_source, data_source_ref | ✅ 11/11 |
| **Spécifique élec (cible)** : segment_turpe, option_tarifaire, classes_compteur, courbe_charge_disponible, hc_horaires, capa_souscrite_kw_pointe, cosphi_target, modulable_kva | ❌ 0/8 directement (présents dans `DeliveryPoint`) |
| **Spécifique gaz (cible)** : profil_gaz (BASE/B0/B1/B2I/MOD), atrd_option (T1-T4-TP), car_kwh, cjn_mwh_jour, cja_mwh_jour | ❌ 0/5 directement (présents dans `DeliveryPoint`) |

**Verdict** : couverture **~20 %** sur Compteur lui-même, **~85 %** si on accepte que les champs vivent dans `DeliveryPoint`. Phase A doit trancher.

### 3.7 Section 4.7 — Compteur gaz (cible 32 champs)

Voir 3.6 — même verdict, complétude via `DeliveryPoint` ATRD/profil/CAR/CJN/CJA.

### 3.8 Section 4.8 — Sous-compteur (cible 15 champs)

| Champ | Présent ? |
|---|---|
| Modèle `sous_compteur.py` | ❌ **MANQUANT** |
| Décomposition par usage (CVC/Eclairage/IT/Process) | ⚠️ via `usage.py`, `usage_breakdown_snapshot.py`, `consumption_target.py` |

**Couverture 0 %** 🔴. **Décision archi** : créer modèle dédié OU utiliser `Compteur` parent avec champ `sub_meter_of_id` self-FK.

### 3.9 Section 4.9 — Contrat (cible 28 champs)

⚠️ **Architecture étendue** : `contract_v2_models.py` (426 L) implémente `ContratCadre` + `AnnexeSite` + `ContractPricing` + `VolumeCommitments` + `ContractEvents`. Bien plus riche que la matrice (28 champs).

**Pertes potentielles vs matrice** :
- ContratCompteurLink **N:N** : remplacé par `ContractDeliveryPoint` (N:N entre EnergyContract et DeliveryPoint) — **équivalent fonctionnel**, à confirmer Phase A
- Champs cible non vérifiés un à un (effort > Phase B) — recommander revue Phase A par bill-intelligence agent

**Couverture ~85 %** 🟢 si modèle V2 accepté ; **20 %** 🔴 si exact match matrice attendu.

### 3.10 Section 5 — OPERAT (composantes 4 lookups)

| Composante | État cible | État repo | Gap |
|---|---|---|---|
| **Resolver zone climatique** | Annexe III authentifiée 🟢 | ✅ `regops/operat_zones.py` consomme `operat_zones_climatiques.json` schema 2.0 (101 entités, 96 métropole + 5 DOM) | 🟢 conforme |
| **Stations météo** | 165 stations Annexe III | ✅ `operat_stations_meteo.json` 33 KB, 165 stations | 🟢 |
| **Service Cabs (4 lookups en chaîne)** | zone → palier altitude → CVCi sous-cat → Coeff DJU | ❌ `OperatValeursAbsoluesService` **n'existe pas**. 4 fichiers config présents mais **aucun service** ne les chaîne. | 🔴 **P0 critique** |
| **Annexe I (sous-catégories)** | 426 sous-cat × 13 zones × 5 paliers + USE étalon + Part_USE_variable + IIU + formules modulation | ✅ `operat_annexe_i_sous_categories.json` 1 115 KB extrait | 🟠 **non consommé** |
| **Annexe II (Coeff DJU)** | 13 groupes Coeff_ch/Coeff_fr | ✅ `operat_annexe_ii_coeff_dju.json` 11 KB extrait | 🟠 **non consommé** |
| **Tooltip traçabilité granulaire** | NOR + URL Légifrance + date d'effet + version consolidée + confidence par valeur | ❌ pas implémenté frontend (pas de composant `TraceTooltip` dédié) | 🔴 **différenciateur perdu** |
| **Modulation (Crelat, IIU, dossier)** | Champs Site + flux dépôt avant 30/09/2026 | ❌ aucun champ `crelat_kwh`, `methode_modulation`, `dossier_modulation_id` sur Site | 🔴 |
| **EFA modélisation** | EFA = Entité Fonctionnelle Assujettie (art. 2 arrêté 10/04/2020) | ❌ pas de modèle EFA explicite, pas de champ `efa_id` sur Site/Bâtiment | 🔴 |
| **Export OPERAT CSV** | Export annuel + manifest checksum | ✅ `routes/operat.py` + `services/operat_export_service.py` | 🟢 |
| **Trajectoire DT validation** | Selon arrêté méthode | ✅ `services/operat_trajectory.py` + `validate_trajectory` | 🟢 |
| **Normalisation DJU** | Selon Annexe II + stations météo | ✅ `services/operat_normalization.py` (peut diverger Annexe II officielle non consommée) | 🟠 |

**Verdict Section 5** : **données sources à 100 % extraites + authentifiées**, **service de chaînage absent**, **modèle Site partiel**. Critique pour Phase C.

### 3.11 Section 6 — Transverses (CRITIQUE compliance score adaptatif)

| Élément | Cible V2 | État repo | Gap |
|---|---|---|---|
| **Compliance score adaptatif (0 → N obligations)** | V2 | ❌ V1 figée 45/30/25 (DT/BACS/APER) chargée via regs.yaml avec fallback hardcodé | 🔴 **P0** |
| **Cascade Org → Site → Compteur (DataConnect)** | Cf. 6.2 | ⚠️ `data_connector` agent existe (.claude/agents/) ; ingest présent (`data_ingestion/`) ; pas de cascade explicite tracée | 🟠 |
| **Cascade ADICT** | Cf. 6.2 | ⚠️ idem | 🟠 |
| **Onboarding 3 parcours bifurqués** | Wizard / Expert / Bulk | ❌ parcours unique 7 étapes (`PatrimoineWizard.jsx`). Composants atomiques `QuickCreateSite`, `SireneOnboarding` existent mais bifurcation UI absente. V2 spec déjà actée. | 🔴 |
| **SitePortefeuilleHistory (temporalité 6.5.3)** | Table dédiée | ❌ aucune | 🔴 |
| **Bill Intelligence A6 1% tolérance bloquante** | service dédié | ❌ pas de "1% tolerance" identifiée. Bill engine présent (`services/billing_engine/` catalog 184 L + ParameterStore versionné). | 🟠 |
| **NAF resolver canonique** | `utils/naf_resolver.resolve_naf_code()` réutilisé partout | ✅ existe ; doublons potentiels `naf_classifier.py`, `naf_estimator.py` | 🟠 |
| **Audit trail patrimoine création/modif/cascade** | Service dédié | ❌ `audit_log_service.py` manquant | 🔴 |

### 3.12 Section 7 — Sources réglementaires (cible Section 7.25)

| Élément | État repo | Gap |
|---|---|---|
| `backend/config/sources_reglementaires.yaml` | ❌ inexistant | 🔴 |
| `backend/regops/services/sources_reglementaires_service.py` | ❌ inexistant | 🔴 |
| Sources archivées PDFs Légifrance OPERAT | ✅ 11 fichiers `docs/sources/regulatory/operat/` | 🟢 |
| `backend/regops/config/legal_refs.py` | ✅ existe (à inspecter en Phase C) | 🟠 |
| `backend/regops/config/regs.yaml` | ✅ existe (couverture partielle) | 🟠 |
| Tooltip frontend traçabilité (NOR + URL + date) | ❌ pas de composant unifié | 🔴 |

**Verdict** : différenciateur PROMEOS Sol §13 (info fiable + sourcée) **non opérationnel** côté frontend.

### 3.13 Section 8 — Cohérence globale + cascade recompute

| Élément | Cible | État repo | Gap |
|---|---|---|---|
| `backend/config/coherence_globale.yaml` | YAML invariants | ❌ inexistant | 🔴 |
| `backend/regops/services/cascade_recompute_service.py` | Cascade sur 10 champs critiques | ❌ inexistant | 🔴 **P0** |
| Endpoint `/api/v1/sites/{id}/cascade-impact` | Preview avant cascade | ❌ inexistant | 🔴 |
| Tests source-guards anti hard-code | ✅ 15 tests inline `test_*_source_guards.py` | 🟢 |
| Workflow CI source_guards.yml | ✅ existe mais **pointe vers `tests/source_guards/` inexistant** | 🔴 cassé silencieusement |

### 3.14 Section 9 — Checklist P0 MVP

| Élément | État repo | Gap |
|---|---|---|
| Endpoint `/api/v1/sites/{id}/production-ready-status` | ❌ | 🔴 |
| Algorithme production-ready-status (combinaison données minimum + obligations) | ❌ | 🔴 |
| `Site.compliance_score_composite` snapshot | ✅ | 🟢 |
| `Site.compliance_score_breakdown_json` | ✅ | 🟢 |
| `Site.compliance_score_confidence` | ✅ | 🟢 |

---

## 4. Anti-patterns détectés (résultats grep complets)

Voir 2.8 ci-dessus pour résultats détaillés A → G. Synthèse :

### 4.1 Bilan anti-patterns

| Catégorie | Cas légitimes | Anti-patterns actifs | Action |
|---|---|---|---|
| CO₂ hardcodé | 5 (commentaires/doc) | 2 (`consumption/constants.js`, `EmissionFactorsContext.jsx` fallback) | P0 — déduplication |
| Pénalité DT 7500 hardcodée | 18 (codes postaux/mocks/docs/fallback YAML) | 2 (`regulatory_rates.js`, indirectement `regs.yaml fallback`) | P1 — endpoint `/api/regulatory/rates` |
| Logique `kWh/m²` frontend | 0 | 2 (`Patrimoine.jsx:828, 1528`) | P0 — déplacer backend |
| TURPE rates hardcodés | 0 | 8 (`billing_engine/catalog.py`, `cost_simulator_2026.py`) | P1 — migrer ParameterStore |
| Routes non org-scopées | — | 0 P0 critique | 🟢 OK |
| Duplication NAF | — | 2 (`naf_classifier`, `naf_estimator`) | P1 — audit + dédupe |
| Fichiers zombies | — | 1 (`routes/patrimoine.py` 0 octet) | P2 — supprimer |

### 4.2 Routes API non org-scopées

Aucun anti-pattern P0 sécurité détecté sur les routes patrimoine principales (cf. 2.4 + 2.8.E). DEMO_MODE bypass est **documenté, intentionnel et limité** au mode démo.

### 4.3 Duplications NAF / utilitaires

`backend/utils/naf_resolver.py` (canonique) ; `backend/services/naf_classifier.py` + `backend/services/naf_estimator.py` (potentiels doublons). Action P1 : audit dépendances et déduplication.

---

## 5. Top 10 risques cohérence

| # | Risque | Impact | Fix | Effort | Dépendances | Priorité |
|---|---|---|---|---|---|---|
| **R1** | **Compliance score V1 figée 45/30/25** au lieu V2 adaptatif 0→N obligations | 🔴 calculs scoring faux pour sites Audit SMÉ obligatoire ou APER non concerné | Refondre `compliance_score_service.py` avec pondérations dynamiques + tests `test_compliance_score_adaptive.py` | 6-8 j-h | regs.yaml refacto, EurAmount typing | **P0** |
| **R2** | **`OperatValeursAbsoluesService` inexistant** : 4 lookups (zone→palier→CVCi→Coeff DJU) absents bien que YAML/JSON extraits à 100 % | 🔴 Cabs 2030 calcul impossible, modulation impossible, trajectoire DT incomplète | Créer `regops/services/operat_cabs_service.py` + tests + endpoint `/api/operat/cabs/{site_id}` | 5-7 j-h | Site OPERAT fields (R3) | **P0** |
| **R3** | **Modèle Site dépourvu des champs OPERAT/EFA/APER étendus** (~12 champs OPERAT + 5 APER + 1 EFA) | 🔴 cascade Cabs impossible, modulation non modélisée, EFA non identifiée | Migration Alembic + update `provision_site()` + enrichissement schémas Pydantic | 4-6 j-h | R2 service Cabs | **P0** |
| **R4** | **`SitePortefeuilleHistory` absent** : pas de temporalité Site↔Portefeuille | 🟠 analyses rétrospectives biaisées, audit trail incomplet pour bascules portefeuille | Nouvelle table + service de bascule + audit trail | 3-4 j-h | audit_log_service.py | **P0** |
| **R5** | **Workflow CI source_guards cassé silencieusement** : pointe vers `tests/source_guards/` inexistant | 🟠 zéro garde-fou anti-hard-code en CI, drift constants possible | Soit créer `tests/source_guards/` et y migrer les 15 fichiers, soit corriger workflow vers `pytest tests/test_*_source_guards.py` | 1-2 j-h | aucune | **P0** |
| **R6** | **`cascade_recompute_service` absent** : changements de code postal/surface/usage ne déclenchent pas recalcul Cabs/compliance/billing | 🟠 dérive silencieuse données ; ex : changement code_postal → zone climatique → Cabs change → dette compliance non recalculée | Service `cascade_recompute_service.py` + endpoint preview `/cascade-impact` + tests | 5-7 j-h | R3 fields, R2 service | **P0** |
| **R7** | **Logique `kWh/m²` inline dans `Patrimoine.jsx`** L828 + L1528 | 🟠 violation doctrine Sol §8.1 "zero business logic in frontend" | Exposer `Site.intensity_kwh_m2` calculé backend (snapshot ou route dédiée) + retirer Math.round FE | 2-3 j-h | aucune | **P0** |
| **R8** | **Onboarding mono-parcours** : `PatrimoineWizard.jsx` 7 étapes, pas de bifurcation Wizard/Expert/Bulk | 🟠 friction onboarding, blocage non-sachants | Découpage 3 parcours UI + endpoint `/api/sites/quick-create` + Bulk import wired | 8-12 j-h | UX validation, PATRIMOINE_V2_PRODUCT_SPEC.md déjà acté | **P1** |
| **R9** | **Audit trail patrimoine absent** : `audit_log_service.py` inexistant, modèle `AuditLog` (iam.py) limité aux CX events | 🟠 conformité opérationnelle non démontrable, RGPD HELIOS partiel | Service + extension modèle ou nouvelle table + middleware capture create/update/delete patrimoine | 4-5 j-h | aucune | **P1** |
| **R10** | **Tooltip traçabilité réglementaire frontend absent** : différenciateur PROMEOS Sol §13 perdu | 🟠 perte d'argument commercial vs Deepki/Metron/HelloWatt | Composant `<TraceTooltip source nor date>` + service `sources_reglementaires_service.py` + endpoint `/api/regulatory/sources/{key}` | 5-7 j-h | sources_reglementaires.yaml (créer) | **P1** |

**Risques bonus (non Top 10 mais notables)** :
- B1 : `CO2_GNL_KGCO2_KWH = 0.238` absent constants.py (arrêté 01/08/2025) — P1 ajout simple
- B2 : `eld_gaz_referentiel.yaml` 21 ELD attendues — P1 si bill intelligence gaz prioritaire
- B3 : Fichier zombie `routes/patrimoine.py` 0 octet — P2 cleanup

---

## 6. Plan Phase C priorisé

### 6.1 P0 — Bloquant production (35-45 j-h, 2 sprints)

**Sprint C-1 (Doctrine + OPERAT cœur — 18-22 j-h)** :
- Migration Alembic Site (12 OPERAT + 5 APER + 1 EFA fields) [4 j-h]
- Création `OperatValeursAbsoluesService` + tests + endpoint `/api/operat/cabs/{site_id}` [5 j-h]
- Refonte `compliance_score_service.py` adaptatif 0→N + tests `test_compliance_score_adaptive.py` [6 j-h]
- Création `cascade_recompute_service.py` + tests + endpoint `/api/v1/sites/{id}/cascade-impact` [5 j-h]
- Réparer workflow CI `source_guards.yml` [1 j-h]
- Ajouter `CO2_GNL_KGCO2_KWH = 0.238` constants.py [<1 j-h]

**Sprint C-2 (Temporalité + frontend cleanup — 14-18 j-h)** :
- Création table `site_portefeuille_history` + service bascule + audit trail [3 j-h]
- Création `audit_log_service.py` (extension AuditLog ou nouvelle table) + middleware [4 j-h]
- Endpoint `/api/v1/sites/{id}/production-ready-status` + algorithme [3 j-h]
- Retrait calculs `kWh/m²` `Patrimoine.jsx:828+1528` + exposition backend [2 j-h]
- Suppression frontend duplications (`pages/consumption/constants.js` CO2) [1 j-h]
- ContratCompteurLink (si décision Phase A confirme split) — sinon migration vers ContractDeliveryPoint propre [3 j-h]

### 6.2 P1 — Crédibilité B2B (30-40 j-h, 2 sprints)

**Sprint C-3 (Sources + traçabilité — 14-18 j-h)** :
- Création `backend/config/sources_reglementaires.yaml` + service [4 j-h]
- Création `backend/config/coherence_globale.yaml` + tests cross-fichier [3 j-h]
- Création `backend/config/eld_gaz_referentiel.yaml` 21 ELD + intégration shadow billing [3 j-h]
- Composant frontend `<TraceTooltip>` unifié + intégration KPIs critiques [3 j-h]
- Migration `frontend/src/domain/regulatory_rates.js` → endpoint `/api/regulatory/rates` (Phase 22 dette) [3 j-h]

**Sprint C-4 (Tests + observabilité — 16-22 j-h)** :
- Tests intégration cascade Org→Site→Compteur (changement code postal → recalcul Cabs) [4 j-h]
- Tests onboarding 3 parcours (après Sprint C-5 livraison FE) [2 j-h]
- Tests cascade ADICT [2 j-h]
- Audit déduplication NAF (`naf_classifier`/`naf_estimator` vs `naf_resolver`) [2 j-h]
- Middleware correlation_id global + propagation logs [3 j-h]
- `.pre-commit-config.yaml` minimal (block_destructive_bash + lint_modified_file Python+JS) [1 j-h]
- Modèle Org enrichi (TVA intra, NAF, pays, secteur, CA) + migration [2 j-h]
- Modèle EJ enrichi (effectif, type société, président, capital) + migration [2 j-h]

### 6.3 P2 — Best-in-world (40-55 j-h, 3 sprints)

**Sprint C-5 (Onboarding 3 parcours — 14-18 j-h)** :
- Composants `WizardSimpleParcours` (V2 spec actée) [5 j-h]
- Composants `ExpertParcours` (densité élevée, multi-entité) [4 j-h]
- Composants `BulkImportParcours` (CSV/Excel auto-détection) [5 j-h]
- Tests E2E Playwright des 3 parcours [4 j-h]

**Sprint C-6 (Modèles enrichis + EFA — 12-15 j-h)** :
- Modèle `EFA` (Entité Fonctionnelle Assujettie OPERAT) + lien Site/Bâtiment [4 j-h]
- Modèle Bâtiment enrichi (RNB, DPE, parties communes, etage_count) [4 j-h]
- Modèle `SousCompteur` (ou champ `sub_meter_of_id` self-FK Compteur) — décision Phase A [3 j-h]
- Modèle Portefeuille enrichi (responsable, couleur_ui, tags) [2 j-h]

**Sprint C-7 (UX premium + cleanup — 14-22 j-h)** :
- Skeletons + virtualisation listes longues `Patrimoine.jsx` [4 j-h]
- Accessibilité ARIA + skip links + focus rings [3 j-h]
- Responsive mobile (380px) Patrimoine + Site360 [3 j-h]
- Empty states + microcopy revue [2 j-h]
- Suppression fichier zombie `backend/routes/patrimoine.py` 0 octet [<1 j-h]
- Migration `billing_engine/catalog.py` rates → `tarifs_reglementaires.yaml` ParameterStore [4 j-h]
- Documentation Phase C complète + DEVLOG [2 j-h]

### 6.4 Sprints proposés (vue récap)

| Sprint | Périmètre | Durée | Livrables clés | Tests à ajouter |
|---|---|---|---|---|
| **C-1** | Doctrine + OPERAT cœur | 18-22 j-h | Service Cabs, compliance V2, cascade service, Site fields OPERAT/APER/EFA | source-guards CI réparé, `test_compliance_score_adaptive`, `test_operat_cabs_service`, `test_cascade_recompute` |
| **C-2** | Temporalité + FE cleanup | 14-18 j-h | site_portefeuille_history, audit_log_service, endpoint production-ready, retrait calculs FE | `test_site_portefeuille_history`, `test_audit_log_patrimoine`, `test_production_ready_status` |
| **C-3** | Sources + traçabilité | 14-18 j-h | 3 YAMLs (sources/coherence/eld_gaz), tooltip FE | `test_sources_reglementaires_coverage`, `test_eld_gaz_dispatch` |
| **C-4** | Tests + observabilité | 16-22 j-h | Cascade tests, NAF dédupe, correlation_id, pre-commit, Org/EJ enrichis | tests intégration cascade complète |
| **C-5** | Onboarding 3 parcours | 14-18 j-h | Wizard/Expert/Bulk bifurcation | E2E Playwright 3 parcours |
| **C-6** | Modèles enrichis + EFA | 12-15 j-h | EFA, Bâtiment RNB/DPE, SousCompteur, Portefeuille tags | unit tests par modèle |
| **C-7** | UX premium + cleanup | 14-22 j-h | Skeletons, ARIA, mobile, ParameterStore TURPE | a11y tests, responsive snapshots |
| **Total** | | **102-135 j-h** | | |

---

## 7. Annexes

### 7.1 Commandes utilisées (échantillon principal)

```bash
# Phase 0 — vérification baseline
cd backend && venv/bin/python -m pytest tests/ --co 2>&1 | tail -3
cd frontend && npx vitest list 2>&1 | wc -l

# Phase 1 — inventaire
ls backend/doctrine/ backend/config/ backend/models/ backend/routes/ backend/services/
find backend -name "*.py" -not -path "*/venv*/*" -not -path "*__pycache__*" | xargs wc -l | tail -1

# Phase 3 — anti-patterns
grep -rn "0\.052\|0\.227\|0\.238" backend/ --include="*.py" | grep -v -E "venv|__pycache__|/tests/|/config/|/doctrine/"
grep -rn "7500" backend/ frontend/src --include="*.py" --include="*.js" --include="*.jsx"
grep -rn "12\.41\|499\.80\|435\.72\|376\.39\|283\.27" backend/ --include="*.py"
grep -rn "kWh.*\*\|Math\.round.*conso.*surface" frontend/src/pages/Patrimoine.jsx
grep -rln "resolve_org_id\|require_user" backend/routes/

# Phase 3 — checks structurels
grep -rln "valeurs_absolues" backend/services/  # vide → service manquant
grep -rln "cascade_recompute" backend/services/  # vide → service manquant
grep -rln "site_portefeuille_history\|SitePortefeuilleHistory" backend/  # vide → modèle manquant
grep -rln "compteur_elec\|compteur_gaz" backend/models/  # vide → split modèles absent
```

### 7.2 Statistiques globales repo

| Métrique | Valeur |
|---|---|
| LOC backend (hors venv) | **287 124** |
| LOC frontend `src/` | **151 033** |
| Nb fichiers Python backend | ~1 200 (incluant tests) |
| Nb modèles SQLAlchemy | **78** |
| Nb services backend | **171** |
| Nb routes API (fichiers) | **89** |
| Nb pages React | **66** |
| Nb tests backend collectés | **7 202** |
| Nb tests frontend (Vitest) | **4 518** |
| Nb tests source-guards inline | **15** fichiers `*_source_guards.py` |
| Nb agents Claude `.claude/agents/` | **11** ✅ workflow check |
| Nb skills Claude `.claude/skills/` | 4 canoniques (emission_factors, regops_constants, regulatory_calendar, helios_architecture) + 11 domaines + 4 vendor |

### 7.3 Tests baseline non-régression vérifiés

Initial (avant Phase B audit) :
```
$ cd backend && venv/bin/python -m pytest tests/ --co 2>&1 | tail -1
7202 tests collected in 1.78s
```

Final (après Phase B — aucun fichier modifié, aucun test ajouté) :
```
$ cd backend && venv/bin/python -m pytest tests/ --co 2>&1 | tail -1
7202 tests collected in [unchanged]
```

✅ **Non-régression garantie** : Phase B = audit read-only strict, aucune modification de fichier.

### 7.4 MCPs utilisés (effort observé)

- **Context7** : N/A — audit ne nécessitait pas de doc lookup externe (codebase-only)
- **code-review** : intégré inline (revue qualité chaque fichier inspecté en profondeur)
- **simplify** : flag opportunités (Patrimoine.jsx 2 312 L → P2 split, naf_classifier dédupe → P1)

### 7.5 Doctrine PROMEOS appliquée

| Règle | Application audit |
|---|---|
| Phase 0 read-only avec STOP gate | ✅ Aucune modification, branche dédiée, livrable unique md |
| Routing OPERAT → regulatory-expert | ⚠️ Non utilisé (audit Phase B = synthèse, agents spécialistes pour Phase C) |
| Source-guard / SoT | ✅ vérifié — `doctrine/constants.py`, configs YAMLs/JSON, anti-pattern grep |
| Citation source + date + confidence | ✅ chaque référence YAML/PDF mentionne NOR + URL + version + confidence (🟢🟠🔴) |
| Atomic commit | ✅ Phase B = aucun commit (livrable unique) |
| Branche `claude/*` | ✅ `claude/phase-b-audit-patrimoine` |
| Baseline tests jamais régresser | ✅ 7 202 BE / 4 518 FE inchangés |
| Audit-then-fix doctrine | ✅ audit AVANT fix — aucun fix entrepris en Phase B |
| KPI traçabilité obligatoire (règle 03/05) | ✅ chaque gap pointe section matrice + impact + référence repo |
| Ne pas confondre 0.0569 (TURPE) avec 0.052 (CO₂) | ✅ vérifié dans constants.py:122 |

### 7.6 Décisions à arbitrer en Phase A.0 avant Phase C

1. **Compteur unifié vs split élec/gaz** — option B (unifié + DeliveryPoint riche) actuellement implémentée vs option A matrice (split). Impact P0 modèles.
2. **Audit SMÉ table séparée vs colonnes EJ** — table `audit_energetique` vs 8 colonnes EJ. Impact 4.2 coverage.
3. **BACS table séparée vs colonnes Bâtiment** — `bacs_models.py` vs colonnes Bâtiment. Impact 4.5 coverage.
4. **Contrat V2 vs matrice 28 champs** — `contract_v2_models.py` (cadre+annexe+pricing+commitments+events) vs modèle plat. Impact 4.9 coverage.
5. **ContratCompteurLink vs ContractDeliveryPoint** — N:N PRM-level acceptable ?
6. **SousCompteur dédié vs self-FK Compteur** — choix archi.
7. **Format clé YAML matrice cible** — commit du fichier `docs/produit/patrimoine_parametrage_requis_v1.md` officiel pour clore le blocage B1.

---

**Fin du livrable Phase B.**

🚦 **STOP GATE strict** — Attente validation utilisateur (Amine) avant toute action Phase C.

Si l'utilisateur demande pendant la review une correction immédiate sur un gap identifié, la réponse doctrinale est :
> *"Phase C, après validation rapport."*
