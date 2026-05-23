# Audit profond brique Patrimoine — refonte-sol2

> **Branche** : `claude/refonte-sol2` (SHA tip `ade3d0a0`)
> **Date** : 2026-05-23
> **Mode** : READ-ONLY strict — aucune modification de code
> **Périmètre** : Patrimoine uniquement. Bill Intelligence / Achat / Flex / Partner Hub / ACC ne sont touchés que pour vérifier leur dépendance au patrimoine.
> **Auteur** : Staff Engineer + QA/Release (audit IA, lecture exhaustive des fichiers cités)
> **Doctrine appliquée** : Patrimoine déclencheur + anti-legacy + 6 personas sévères.

Hypothèses cardinales :
- `routes/patrimoine.py` est vide ou résiduel ; le router actif est `routes/patrimoine/__init__.py` (package). À vérifier en supprimant un jour le fichier vide.
- Le SoT runtime consommation est `Meter.parent_meter_id` ; `Compteur` est SoT *onboarding/wizard*. Dualité documentée ADR-D-01 (`backend/services/compteur_meter_bridge.py:1-23`).
- Le frontend cible Sol2 (grammaire `grammar/hub/*`) ; les pages V2/V3/V4 résiduelles ne sont pas censées être wirées en prod.

---

## 1. Résumé exécutif

| Axe | Note | Verdict |
|---|---|---|
| Modèle de données | **7/10** | Hiérarchie correcte, FKs explicites, mais `Site.portefeuille_id` nullable → sites orphelins légaux. Champs OPERAT/APER/BACS/SMÉ/BEGES **présents** au bon niveau. |
| Unicité PRM/PCE | **8/10** | Unicité globale assurée via *partial unique index actif* (`DeliveryPoint.code`). Soft-delete recyclable testé (C60/C85). Risque résiduel : index créé hors SQLAlchemy (migration runtime). |
| Données manquantes | **6/10** | 9 codes `DATA_MISSING` whitelistés, `missing_inputs` exposé. Aucune route UI cliquable vers le champ → friction grave côté DAF/CS. |
| Onboarding | **3/10** | **5 entry-points** patrimoine concurrents (PatrimoineWizard, Sirene, SiteCreationWizard, QuickCreateSite, Drawer*). Pas de Wizard canonique. `OnboardingPage` MORT. Aucun "mode Expert" assumé. |
| Cohérence transverse | **6/10** | Patrimoine→conformité partiellement câblé (PATCH `patrimoine/sites/{id}` ok, PATCH `patrimoine_crud/sites/{id}` swallow exceptions, **import bulk sans cascade**). |
| Audit trail | **4/10** | `audit_log_service` complet. **5 endpoints CRUD** patrimoine mutent sans log_patrimoine_change (Org/EJ/PF/Site/Site.delete via crud). |
| API | **5/10** | 100 % `/api/` legacy ; doublons `routes/sites.py` (deprecated) ↔ `routes/patrimoine/sites.py` (premium) ↔ `routes/patrimoine_crud.py` (CRUD brut). Frontend appelle simultanément les 3. |
| UX/UI | **4/10** | Patrimoine.jsx solide mais 9 tabs sur Site360, jargon PRM/PCE non explicité, CadreApplicable display-only sans drill-down DATA_MISSING. |
| Tests | **6/10** | Excellent côté source-guards (≈48 guards) et unicité PRM/PCE. Manque : mutation→recompute applicability, facture sans compteur, multi-org matrix endpoints. |

**Note globale : 5,4 / 10. Verdict : partiel — bloquant en production pour un client B2B sévère.**

### 5 risques majeurs (P0)

1. **Patrimoine non-actionnable depuis le Cockpit** : `CadreApplicable.jsx:135` affiche *"Données manquantes · 4 sites"* sans drill-down ni CTA vers le champ. Le pacte produit "patrimoine déclencheur de tout" est cassé côté UI.
2. **5 parcours de création patrimoine concurrents** : `PatrimoineWizard` / `SireneOnboardingPage` / `SiteCreationWizard` / `QuickCreateSite` / `OnboardingPage` (morte). Aucun n'est canonique. Personas CS et Dirigeant PME perdus.
3. **CRUD patrimoine sans audit trail** : `routes/patrimoine_crud.py` mute Organisation/EntiteJuridique/Portefeuille/Site/Site.archive sans appeler `log_patrimoine_change` (seul `routes/patrimoine/sites.py` PATCH/archive est correctement câblé). Audit RGPD/conformité fragilisé.
4. **Bulk import sans cascade réglementaire** : `routes/import_sites.py` crée N sites sans déclencher `cascade_recompute_on_change` ni `compute_applicability` ; sites visibles, conformité stale.
5. **Doublon de référentiels Compteur ↔ Meter et routers /sites legacy + crud + premium** : la chaîne onboarding → runtime traverse 3 modèles et 3 routers ; bug surface garanti à moyen terme (ADR-D-01 explicite la dette).

---

## 2. Cartographie modèle data

| Entité | Fichier | Relations | Champs critiques | Gaps | Risque |
|---|---|---|---|---|---|
| `Organisation` | `backend/models/organisation.py:16-164` | 1-N `EntiteJuridique` (cascade delete) | `siren`, `type_client`, `secteur` (Typologie validator), `effectif_total`, `chiffre_affaires_eur`, `bilan_eur` (SMÉ b), `tva_intra` (validator FR), `pays` | Pas de `code_naf_principal` sur EJ (existe sur Org), mais cardinal SMÉ sur EJ — voir contrat sémantique L40-49 EJ | Confusion Org vs EJ pour SMÉ : `Organisation.chiffre_affaires_eur` = niveau groupe consolidé ≠ `EntiteJuridique.chiffre_affaires_eur` = signataire ; risque double comptage si non documenté UI. |
| `EntiteJuridique` | `backend/models/entite_juridique.py:18-153` | N-1 `Organisation`, 1-N `Portefeuille` (cascade delete) | `siren` UNIQUE, `siret`, `naf_code`, `consommation_annuelle_moyenne_3y_gwh` (déclencheur SMÉ DDADUE), `effectif_etp`, `chiffre_affaires_eur`, `iso_50001_actif` | Pas de N-N Org↔EJ direct sur le modèle "métier" — mais `OrgEntiteLink` (`patrimoine.py:45-74`) le fournit côté DIAMANT. Risque : 2 mappings concurrents (FK directe + N-N link table). | Moyen : la FK `EntiteJuridique.organisation_id` (L22) est nullable=False, le N-N link sert pour des cas atypiques (refactoring partiel). |
| `Portefeuille` | `backend/models/portefeuille.py:17-60` | N-1 `EntiteJuridique`, 1-N `Site` (cascade delete) | `responsable_id` (FK User, SET NULL), `actif`, `couleur_ui` (hex validator), `tags` JSON, `code_interne` | Aucun gap notable. UniqueConstraint manquant sur `(entite_juridique_id, nom)`. | Faible. |
| `Site` | `backend/models/site.py:24-388` | N-1 `Portefeuille` **(nullable !)**, 1-N `Batiment`, 1-N `Compteur`, 1-N `DeliveryPoint`, 1-N `Meter`, 1-N `Obligation`, 1-N `Alerte` | 3 surfaces distinctes (`surface_m2` SDP, `tertiaire_area_m2`, `s_ce_m2`), `parking_area_m2`/`roof_area_m2` (APER), `aper_*`, `operat_*` (15 champs), `bacs_assujetti`/`bacs_puissance_cvc_totale_kw` (cascade BACS), `mode_propriete` (EfaRole), `categorie_operat_principale` (OperatUsagePrincipalEnum), `consentement_site_overrides` JSON, `is_demo` NOT NULL. | **`portefeuille_id` nullable** (L61) → site orphelin légal. Aucun champ `organisation_id` direct (multi-org sécurisé via remontée portefeuille→EJ→Org). | **HAUT** — un site sans portefeuille n'a aucun ancrage org → bypass scope possible si un endpoint oublie `assert_org_owns_site`. |
| `Batiment` | `backend/models/batiment.py:17-211` | N-1 `Site` (NOT NULL, cascade delete via Site). UniqueConstraint `(site_id, nom)`. | `cvc_power_kw` (cascade BACS), `rnb_id`, `dpe_class` (validator), `dpe_score_kwhep_m2_an`, `categorie_operat_batiment` (validator + cross-FK avec `usage_batiment`), `usage_batiment` (UsageBatimentEnum 11 valeurs, contrainte PARKING/TECHNIQUE ⇒ categorie_operat_batiment NULL). | Pas de relation directe `Batiment ↔ Compteur` (uniquement via `Compteur.batiment_id` SET NULL). Bon. | Faible. |
| `Compteur` | `backend/models/compteur.py:12-141` | N-1 `Site` (NOT NULL), N-1 `DeliveryPoint` (SET NULL), N-1 `Batiment` (SET NULL), self-FK `sub_meter_of_id` (D6, anti-cycle validator). | `numero_serie` UNIQUE global, `type` (TypeCompteur), `meter_id` legacy (pas UNIQUE), `delivery_point_id`, `sub_meter_usage` (SubMeterUsageEnum), `batiment_id`. | **Dualité Compteur ↔ Meter** : le runtime conso passe par `Meter`, le wizard par `Compteur`. Bridge `compteur_meter_bridge.py:ensure_meter_pair`. Documenté ADR-D-01 mais reste une dette structurelle. | **MOYEN** — risque de divergence silencieuse Compteur/Meter (sous-meter créé via Compteur mais pas miroir Meter → pilotage CVC manquant). |
| `DeliveryPoint` | `backend/models/patrimoine.py:258-941` | N-1 `Site` (cascade delete), 1-N `Compteur`, N-N `EnergyContract` via `ContractDeliveryPoint` | `code` (PRM élec / PCE gaz, validator 3 formats `\d{14}|GI\d{6}|IR\d{4}`), `energy_type`, `grd_code` (cross-validator énergie), `pce_format` (cross-FK avec `code`), `categorie_turpe`/`domaine_tension` (cross-validator C61-63), `atrd_option` (gaz). | Pas de gap fonctionnel. **Index UNIQUE partial actif** (`uq_delivery_point_code_active`) créé via `database/migrations.py:_add_unique_delivery_point_code_index` — pas via SQLAlchemy. | **MOYEN** — un environnement où la migration n'a pas tourné laisse la porte ouverte à des doublons PRM/PCE. À assurer via test d'intégration sur migrations. |
| `EnergyContract` | `backend/models/billing_models.py:46-...` | N-1 `Site` (NOT NULL), N-1 `Fournisseur` (transitoire). | `site_id`, `energy_type`, `supplier_name` (DEPRECATED), `fournisseur_id` (FK). | Migration en cours `supplier_name` → `fournisseur_id` (ADR-F-01). | Faible. |
| `ContratCadre` | `backend/models/contract_v2_models.py:36+` | N-1 `Organisation`, optionnel N-1 `EntiteJuridique`, N `AnnexeSite`. | Multi-site cadre. | **Doublon de modèle** avec `EnergyContract` ; UI doit choisir lequel. | **MOYEN** — phase de transition longue. |

**Verdict modèle** : la hiérarchie est correcte et les FK explicites, mais 4 dettes structurelles persistent : (1) `Site.portefeuille_id` nullable, (2) Compteur/Meter duality, (3) EnergyContract/ContratCadre duality, (4) OrgEntiteLink N-N concurrent de la FK directe `EntiteJuridique.organisation_id`.

---

## 3. Cartographie API

> Notation source : `backend/routes/...`. Authz `OrgScope` = `resolve_org_id` + `assert_org_owns_*` (Phase E IDOR). Tous les endpoints sont préfixés `/api/` (pas `/api/v1/` sauf 5 routes hors patrimoine — users, digest, events, doctrine, navigation).

| Route | Méthode | Usage | Version | Authz | Side-effects | Tests | Gaps |
|---|---|---|---|---|---|---|---|
| `/api/sites` | GET, POST | **LEGACY** (deprecated explicite) | `/api/` | partial | aucun cascade | ✓ (legacy) | **À supprimer / rediriger.** Doublon avec `/api/patrimoine/sites`. |
| `/api/sites/quick-create` | POST | Création rapide site (1 form, 1 écran) | `/api/` | OrgScope auto | `provision_site` + `evaluate_site` legacy | ✓ | **DEPRECATED mais appelé activement par `QuickCreateSite.jsx`** → P0 nettoyage. |
| `/api/import/sites` | POST | Import CSV bulk | `/api/` | OrgScope | `create_site_from_data` + `provision_site` par ligne. **Aucun `cascade_recompute_on_change`**. | ✓ partiel | **P0** : conformité stale après import. |
| `/api/import/template` | GET | Renvoie colonnes CSV attendues | `/api/` | OrgScope | — | — | OK. |
| `/api/patrimoine/sites` | GET | Liste sites org-scope (premium) | `/api/` | OrgScope | — | ✓ | OK. |
| `/api/patrimoine/sites/{id}` | GET, PATCH, DELETE | Site premium (snapshot, completeness, anomalies, merge) | `/api/` | OrgScope | PATCH : `cascade_recompute_on_change(persist=True)` + `log_patrimoine_change` + `log_cascade`. DELETE : `cascade_site_archive` + log. | ✓ (`test_patch_sites_triggers_cascade.py`) | **Référence d'excellence** — ce pattern devrait s'appliquer aux 5 endpoints suivants. |
| `/api/patrimoine/sites/{id}/archive` | POST | Soft archive | `/api/` | OrgScope | `log_patrimoine_change` | ✓ | OK. |
| `/api/patrimoine/crud/organisations` | GET, POST | CRUD Org | `/api/` | OrgScope | POST: pas de log | ✓ | **No audit_log on POST**. |
| `/api/patrimoine/crud/organisations/{id}` | GET, PATCH, DELETE | CRUD Org détail | `/api/` | OrgScope | PATCH : cascade ssi consent fields (`consentement_dataconnect_global`/`grdf_global`) ; reste des champs setattr sans log (`patrimoine_crud.py:204-206`). DELETE : `soft_delete` sans log (L249-258). | ✓ | **P0** — mutations *non-consent* (raison sociale, NAF, CA, bilan, ISO 50001…) **non auditées**. |
| `/api/patrimoine/crud/entites` | GET, POST | CRUD EJ | `/api/` | OrgScope | — | ✓ | No log POST. |
| `/api/patrimoine/crud/entites/{id}` | GET, PATCH, DELETE | CRUD EJ | `/api/` | OrgScope | PATCH (`patrimoine_crud.py:333-349`) : setattr+commit, **no audit_log, no cascade**. | ✓ | **P0** — change de SIREN/SIRET → 0 trace. |
| `/api/patrimoine/crud/portefeuilles` | GET, POST | CRUD PF | `/api/` | OrgScope | — | ✓ | No log POST. |
| `/api/patrimoine/crud/portefeuilles/{id}` | GET, PATCH, DELETE | CRUD PF | `/api/` | OrgScope | PATCH (L439-455) : setattr+commit, **no audit_log**. | ✓ | **P0** — change de responsable/nom → 0 trace. |
| `/api/patrimoine/crud/sites` | POST | Crée site brut | `/api/` | OrgScope | `create_site` + `provision_site` ; pas de `log_patrimoine_change`. | ✓ | **P0** doublon avec `/api/patrimoine/sites` premium. |
| `/api/patrimoine/crud/sites/{id}` | GET, PATCH, DELETE | CRUD Site brut | `/api/` | OrgScope | PATCH (L568-619) : essaye `recompute_site_full` dans try/except qui **avale l'erreur** (warning seulement). DELETE : `soft_delete` sans log. | ✓ | **P0** : un recompute en échec → mutation persistée + conformité stale et silencieuse. |
| `/api/patrimoine/crud/batiments` | POST | Crée bâtiment | `/api/` | OrgScope | `recompute_site_bacs_aggregate` (cascade BACS Phase D-4). | ✓ | OK cascade ; **pas de log_patrimoine_change**. |
| `/api/patrimoine/crud/batiments/{id}` | PATCH, DELETE | CRUD bâtiment | `/api/` | OrgScope | Cascade BACS sur cvc_power_kw. | ✓ | Idem : cascade OK, audit log absent. |
| `/api/compteurs` | GET, POST | CRUD compteur | `/api/` | OrgScope partiel sur GET (filtré par site_id seulement) | POST : `ensure_delivery_points_for_site` post-commit. | ✓ partiel | **P1** — GET `/api/compteurs` sans site_id pourrait leaker. |
| `/api/regulatory/applicability` | GET | Évalue règles DT/BACS/APER/SMÉ/BEGES | `/api/` | OrgScope | Pure read. Retourne `[RuleApplicability]` avec `reason_code` + `missing_inputs`. | ✓ source-guards G1/G3/G5 | OK. Aucun `remediation_field` machine pour pointer vers champ UI. |
| `/api/v1/sites/{id}/cascade-impact` | GET | **Preview seulement** (`routes/cascade.py:86`) | `/api/v1/` | OrgScope | Dry-run | ✓ | UI peut induire en erreur (preview ≠ persist). |

**Versions API** : 100 % du patrimoine est en `/api/` (legacy non versionné) sauf cascade.py en `/api/v1/`. La cohabitation crée une asymétrie suspecte.

**Routes mortes / doublons à supprimer ou consolider** :
- `backend/routes/patrimoine.py` est résiduel : à supprimer si non importé (le router actif est `routes/patrimoine/__init__.py` package).
- `routes/sites.py` → marqué deprecated en interne mais activement appelé par `QuickCreateSite.jsx` (FE) → P0.
- `routes/patrimoine_crud.py` ET `routes/patrimoine/sites.py` exposent tous deux POST/PATCH site → le FE choisit selon le wizard. À unifier : un seul endpoint "premium" (avec log + cascade), `patrimoine_crud` rétrogradé en GET-only.

---

## 4. Cartographie Front

| Page / composant | Rôle | États UI | Gaps UX | Risque | Verdict |
|---|---|---|---|---|---|
| `OnboardingPage.jsx` | Page d'onboarding générique | n/a | **MORT** — `App.jsx:647-650` la redirige vers `/cockpit/jour`. Code commentaire : "test 2 doctrinal 'dirigeant non-sachant' en échec, score 1,5/10". | P0 confusion (CS / Atlas / Phase 4 ne savent pas où aller) | **Supprimer** ou marquer explicitement Phase 4 WIP. |
| `SireneOnboardingPage.jsx` | Sirène → patrimoine 3 steps | loading/error/success | Pas d'entry-point primaire (la page parent /onboarding est morte). `SurfaceCapture` arrive en step 2 mais devrait être central. | P1 | Garder + remettre en entry-point /onboarding. |
| `PatrimoineWizard.jsx` (1162 L) | Import CSV bulk 6 steps Express/Verification | empty/loading/error/partial | Aucun "mode Expert" (juste 2 modes ≈ identiques). Pas de mapping colonne custom. Aucune justification métier expliquée à l'utilisateur. | P1 | Garder, simplifier. |
| `SiteCreationWizard.jsx` | 7 étapes Org→EJ→PF→Site→Bât→Compteurs→Récap | loading/error | Doublon fonctionnel avec PatrimoineWizard. Cible cas "première installation" mais flou côté UI : qui choisit quoi entre les deux ? | P1 | Fusionner avec PatrimoineWizard ou rendre canonique. |
| `QuickCreateSite.jsx` | 1 form, 1 écran | loading/error | Appelle endpoint **deprecated** `/api/sites/quick-create`. | P0 | À recâbler sur `/api/patrimoine/crud/sites` ou supprimer. |
| `DrawerEditSite.jsx` | Édition site depuis table | loading/error | OK ergonomie. | P3 | Garder. |
| `DrawerAddCompteur.jsx` | Ajout compteur depuis SiteDrawer | loading/error | PRM/PCE jamais expliqué (pas de tooltip). | P1 jargon | Garder + tooltip. |
| `Patrimoine.jsx` (2331 L) | Table portefeuille risque-first, URL-sync, SiteDrawer tabbed | empty/loading/error/skeleton | Pas de colonne "Dernière MAJ donnée", pas d'indicateur "source", pas de bulk action exploité (checkbox rendus, jamais utilisés). | P1 | **Garder** + raffiner. Très bonne fondation. |
| `Site360.jsx` (~2200 L) | Fiche site 360, 8-9 tabs (Résumé/Conso/Analytics/Factures/Réconciliation/Conformité/Actions/Puissance) | loading/error | **Tab-spam**. Responsable GTB ne trouvera jamais "Puissance" (position 7/8). Delivery Points enterrés. Aucun tab Équipements. | P0 | **Refondre** : 5 tabs core + "Avancé" repli. |
| `CockpitStrategique.jsx` (242 L) | Hero + CadreApplicable + Kpis + Verdict | loading/error | KPIs non-cliquables, CadreApplicable affiche "Données manquantes · N sites" **sans drill-down ni CTA**. | P0 | **Refondre actions** : drill-down DATA_MISSING. |
| `CadreApplicable.jsx` (`grammar/hub/CadreApplicable.jsx`) | Grid 5 règles DT/BACS/APER/SMÉ/BEGES | display only | `onRuleClick` callback optionnel mais aucun parent ne l'implémente. Labels FR OK (`SolAcronym` global). | P0 | **Refondre** : drill-down obligatoire vers Patrimoine filtré. |
| `PatrimoineHealthCard.jsx` / `PatrimoineHeatmap.jsx` / `PatrimoinePortfolioHealthBar.jsx` / `PatrimoineRiskDistributionBar.jsx` | Visus V2 patrimoine | n/a | **Imports commentés** dans `Patrimoine.jsx:50-53` : "V2 — composants retirés du flow principal". | P2 dead code | **Supprimer** si pas réutilisés. |
| `patrimoine/SitesMap.jsx` | Carte des sites | empty/loading | OK. | — | Garder. |
| `OnboardingOverlay.jsx` | Hint overlay | n/a | À vérifier où il est monté. | — | À expertiser. |

**Verdict UX synthétique** :
- **5 entry-points de création patrimoine concurrents** (Sirene, Wizard CSV, Site Wizard 7-steps, QuickCreateSite, Drawer) sans hiérarchie claire — viole la doctrine "patrimoine déclencheur".
- **CadreApplicable display-only** = le pacte produit "données manquantes → action immédiate" est cassé.
- **Site360 tab-spam** = personas GTB et auditeur perdus.
- Anglais résiduel : aucun (✅). Jargon non-tooltippé : **PRM/PCE** systématiquement, **Cabs/Crelat/EFA** dans certaines cards.

---

## 5. Matrice champs patrimoine

| Champ | Niveau | Obligatoire | Utilisé par | Présent ? | Gap |
|---|---|---|---|---|---|
| `siren` | Organisation/EJ | P0 | Sirène lookup, SMÉ, audit trail | ✓ unique EJ | OK. |
| `siret` | EJ / Site / Bâtiment | P1 | Audit, OPERAT EFA | ✓ (3 niveaux, validators stricts) | Cohérence à monitorer (siret_site != siret_batiment voulu ?). |
| `effectif_total` | Organisation | P0 SMÉ/BEGES | rules sme.py, beges.py | ✓ | OK. |
| `chiffre_affaires_eur` | Organisation + EJ | P0 SMÉ | rules sme.py (lit `Organisation.chiffre_affaires_eur`) | ✓ | Contrat sémantique Org vs EJ documenté code commentaire — risque UI confondre. |
| `bilan_eur` | Organisation | P0 SMÉ (b) | rules sme.py | ✓ (`organisation.py:66-70`) | Champ ajouté Phase 3.7 ; vérifier que `SMEEvaluator` le lit (gap signalé subagent). |
| `consommation_annuelle_moyenne_3y_gwh` | EJ | P0 SMÉ DDADUE | rules sme.py | ✓ (`entite_juridique.py:33-37`) | Source : déclencheur Audit SMÉ 11/10/2026. |
| `iso_50001_actif` + `iso_50001_date_validite` | EJ | P1 SMÉ exemption | rules sme.py | ✓ (`entite_juridique.py:76-86`) | OK. |
| `nom` | Site | P0 | UI / table | ✓ | OK. |
| `type` (TypeSite) | Site | P0 | usage tertiaire, DT | ✓ | OK. |
| `adresse` + `code_postal` + `ville` + `region` | Site | P0 | Géoloc, zone climatique OPERAT | ✓ | OK. |
| `latitude`/`longitude` + `geocoding_*` | Site | P1 | SitesMap, BAN | ✓ | OK. |
| `surface_m2` (SDP) | Site | P0 | DT, intensité | ✓ | OK. |
| `tertiaire_area_m2` | Site | P0 DT | rules dt.py | ✓ | OK. |
| `s_ce_m2` (Surface CE OPERAT) | Site | P1 | OPERAT déclaratif | ✓ | OK. |
| `parking_area_m2` + `roof_area_m2` + `parking_type` | Site | P0 APER | rules aper.py | ✓ | OK. |
| `aper_assujetti`, `aper_categorie_taille`, `aper_deadline`, `parking_solar_pct_engaged`, `aper_exemption_motif` | Site | P1 | aper.py + UI | ✓ | OK. |
| `bacs_assujetti`, `bacs_puissance_cvc_totale_kw` | Site agrégat | P0 BACS | bacs.py + cascade Phase D-4 | ✓ | OK. |
| `cvc_power_kw` | Batiment | P0 BACS | rule bacs.py | ✓ | OK. |
| `operat_zone_climatique`, `operat_palier_altitude`, `altitude_m`, `operat_sous_categorie_id`, `operat_iiu_*`, `cabs_kwh_m2_an`, `crelat_kwh_m2_an`, `usage_principal`, `efa_id`, `annee_reference_operat`, `categorie_operat_principale`, `mode_propriete`, `methode_modulation_dt`, `dossier_modulation_id` | Site | P0 OPERAT/DT | rules dt.py + OperatValeursAbsoluesService | ✓ (15 champs présents) | OK. |
| `archetype_code` + `puissance_pilotable_kw` | Site | P1 Flex | flex services | ✓ | OK. |
| `cbam_imports_tonnes`, `cbam_intensities_tco2_per_t` | Site | P2 CBAM | billing/turpe | ✓ | OK. |
| `intensity_kwh_m2_total` + `intensity_kwh_m2_tertiaire` | Site (persisté) | P1 | UI Patrimoine.jsx | ✓ | OK. |
| `consentement_*_global` + `_at` + `_by` + `_cgu_version` | Organisation | P0 RGPD | DataConnect/GRDF | ✓ (Sprint C-4/5) | OK + cascade Phase 4.5. |
| `consentement_site_overrides` | Site | P1 RGPD cascade | Phase 4.5 | ✓ | OK. |
| `nom`, `surface_m2`, `cvc_power_kw`, `rnb_id`, `dpe_class`, `dpe_score_kwhep_m2_an`, `dpe_date_validite`, `annee_renovation_lourde`, `categorie_operat_batiment`, `usage_batiment`, `dpe_emissions_kgco2_m2`, `etage_count`, `efa_operat_id`, `parties_communes_pct`, `siret_batiment` | Batiment | P0/P1 | bacs.py, DT modulation, DPE alerts | ✓ | OK. |
| `numero_serie` (UNIQUE global), `type`, `puissance_souscrite_kw`, `meter_id` (legacy), `delivery_point_id`, `sub_meter_of_id`, `sub_meter_usage`, `batiment_id` | Compteur | P0 | UI compteurs, ensure_delivery_points_for_site | ✓ | Dualité Meter à monitorer. |
| `code` (PRM/PCE), `energy_type`, `grd_code`, `atrd_option`, `pce_format`, `code_fta`, `categorie_turpe`, `domaine_tension` | DeliveryPoint | P0 | facturation, TURPE | ✓ | Unicité partielle index actif. |

**Conclusion** : aucun gap critique de champ. Tous les déclencheurs DT/BACS/APER/SMÉ/BEGES ont leur champ patrimoine. Le seul risque structurel est sémantique : **Org vs EJ pour SMÉ** (CA + bilan en deux endroits).

---

## 6. Data Missing réglementaire

> Source : `backend/regulatory/reason_codes.py:25-86`. Whitelist verrouillée par `test_reason_codes_whitelist` (source-guard Vague A.7).

| Reason code | Champ attendu | UI de correction | Présent BE ? | Présent UI ? | Gap |
|---|---|---|---|---|---|
| `DT.DATA_MISSING.SURFACE` | `Site.tertiaire_area_m2` (fallback `surface_m2`) | DrawerEditSite section "Surfaces" | ✓ `missing_inputs=["site.tertiaire_area_m2"]` (`rules/dt.py:85-91`) | ❌ CadreApplicable affiche le compte mais ne navigue PAS vers DrawerEditSite | **P0** drill-down UI. |
| `DT.DATA_MISSING.USAGE` | `Site.usage_principal` | DrawerEditSite section "Usage" | ✓ | ❌ | **P0**. |
| `DT.UNKNOWN.USAGE_MIXTE` | Champ à qualifier manuellement | UI dédiée | ✓ | ❌ aucune UI | **P1** champ-réponse manquant. |
| `BACS.DATA_MISSING.CVC_POWER` | `Batiment.cvc_power_kw` (par bâtiment) | DrawerEditSite tab Bâtiments | ✓ `missing_inputs=["batiment.cvc_power_kw[{id}]"]` (`rules/bacs.py:77-89`) | ❌ | **P0**. |
| `APER.DATA_MISSING.PARKING_AREA` | `Site.parking_area_m2` | DrawerEditSite "Stationnement" | ✓ | ❌ | **P0**. |
| `APER.DATA_MISSING.ROOF_AREA` | `Site.roof_area_m2` | DrawerEditSite "Toiture" | ✓ | ❌ | **P0**. |
| `SME.DATA_MISSING.EFFECTIF` | `Organisation.effectif_total` | UI Organisation (non identifiée) | ✓ | ⚠️ aucune page "Organisation" claire dans le frontend | **P1** UI org-level absent. |
| `SME.DATA_MISSING.CA` | `Organisation.chiffre_affaires_eur` + `bilan_eur` | UI Organisation | ✓ | ⚠️ | **P1**. |
| `SME.DATA_MISSING.CONSO` | `AuditSME.conso_annuelle_moy_gwh` (et/ou `EntiteJuridique.consommation_annuelle_moyenne_3y_gwh`) | UI EJ/Audit | ✓ | ⚠️ | **P1**. |
| `BEGES.DATA_MISSING.EFFECTIF` | `Organisation.effectif_total` | UI Organisation | ✓ | ⚠️ | **P1**. |

**Synthèse** :
1. Le **backend expose correctement** `missing_inputs` (10 codes, whitelistés, testés source-guards G5).
2. L'**UI ne consomme pas** ce champ : `CadreApplicable.jsx:135-138` affiche un compteur de sites, sans drill-down ni callback de remédiation. **P0**.
3. Il manque une **page "Organisation/Entité juridique"** pour saisir les champs SMÉ/BEGES (effectif, CA, bilan, conso). Tous les wizards créent l'org en arrière-plan, sans surface pour l'éditer ensuite.
4. Aucun champ machine type `remediation_field: "site.tertiaire_area_m2"` enrichi dans la réponse API → le FE devrait soit mapper côté front, soit on enrichit `RuleApplicability.to_dict()` (P2).

---

## 7. Cohérence transverse

### 7.1 Patrimoine ↔ Conformité

- **PATCH `/api/patrimoine/sites/{id}`** : `cascade_recompute_on_change(persist=True)` + `log_patrimoine_change` + `log_cascade` (`routes/patrimoine/sites.py:494-620`). ✅ **OK premium**.
- **PATCH `/api/patrimoine/crud/sites/{id}`** : try/except `recompute_site_full` qui avale l'erreur (`patrimoine_crud.py:609-615`). ⚠️ **silencieux**.
- **Bulk import `/api/import/sites`** : `create_site_from_data` + `provision_site` ; **aucun cascade**. 🔴 **P0**.
- **PATCH/POST/DELETE `/api/patrimoine/crud/batiments`** : `recompute_site_bacs_aggregate` câblé (cascade BACS ADR-D-04). ✅.
- **`patrimoine_conformite_sync.py`** : `cascade_site_archive`, `flag_efa_desync_on_surface_change`, `reevaluate_on_usage_change` câblés depuis `patrimoine/sites.py` PATCH/archive.
- Aucune mutation ne déclenche un appel **direct** à `applicability_service.compute_applicability(persist=True)`. Le calcul d'assujettissement repose sur `compliance_rules` + `regops.engine` + `bacs_engine` historiques → **3 moteurs concurrents**.

### 7.2 Patrimoine ↔ Facture (Bill Intelligence)

- `perimeter_check.py:check_perimeter(db, site_id, contract_id, period_start, period_end)` vérifie site existe / contrat existe / contrat matche le site / période couverte. ✅ Solide.
- Appelé par `routes/billing.py` (validé via `git grep`). ✅.
- Champ `EnergyContract.site_id` NOT NULL → contrainte forte. Mais `ContratCadre` (multi-sites) coexiste → ambiguïté UI sur "contrat de quel site". ⚠️.
- Aucune route patrimoine ne vérifie qu'un site existe **avant** d'importer une facture côté staging — le check arrive seulement au moment d'ingestion via perimeter_check. Acceptable.

### 7.3 Patrimoine ↔ Contrat

- `EnergyContract.site_id` (FK NOT NULL). ✅.
- `ContractDeliveryPoint` (N-N) table de liaison. ✅.
- `ContratCadre` (v2) ajoute hiérarchie Org + EJ + multi-sites. **Doublon en cours de migration**.

### 7.4 Patrimoine ↔ Consommation

- `Compteur` (SoT onboarding) ↔ `Meter` (SoT runtime). Bridge `compteur_meter_bridge.py:ensure_meter_pair`. Documenté ADR-D-01.
- Risque : sous-compteur créé via Compteur self-FK (`sub_meter_of_id`) **sans** trigger automatique du miroir `Meter.parent_meter_id` (le bridge doit être appelé explicitement par les wizards). 🔴 **P1 dette**.

### 7.5 Patrimoine ↔ Achat

- `purchase_perimeter.py` (vu via grep) — non audité en profondeur car hors scope. À surveiller en couplage avec ContratCadre.

### 7.6 Patrimoine ↔ Actions / Preuves

- `Obligation` relation `Site.obligations` (cascade delete) (`site.py:330-334`). ✅ couplage présent.
- Pas d'objet "preuve" cardinal dans le modèle Site directement (existe ailleurs, hors périmètre patrimoine).

### 7.7 Doublons de référentiels

- `Compteur` vs `Meter` — explicite (ADR-D-01).
- `EnergyContract` vs `ContratCadre` — migration en cours.
- `EntiteJuridique.organisation_id` FK + `OrgEntiteLink` N-N — concurrent.
- `routes/sites.py` + `routes/patrimoine_crud.py` + `routes/patrimoine/sites.py` — 3 surfaces pour CRUD site.
- `OnboardingPage` + `SireneOnboardingPage` + `PatrimoineWizard` + `SiteCreationWizard` + `QuickCreateSite` + `DrawerEditSite` — 5+ surfaces patrimoine FE.

### 7.8 Logique métier côté FE

- `Patrimoine.jsx` formats k€/m² locaux mais source-guard `patrimoine_no_kwh_calc_fe_source_guards.test.js` interdit le calcul kWh côté FE. ✅ doctrine respectée.
- Néanmoins quelques formules d'agrégation `risque_eur` / "Maturité patrimoine %" sont calculées en JS (à vérifier).

---

## 8. Tests existants

### 8.1 Backend (≈230 tests patrimoine)

- **Unicité PRM/PCE** : `backend/tests/test_phase_d1b_validators_cross_fk.py:282-322` C60/C85 partial unique index + recyclage soft-delete. ✅.
- **DT/BACS/APER/SMÉ/BEGES rules** : `backend/tests/regulatory/test_rule_*.py` + `test_applicability_service.py` + `test_endpoint_applicability.py`. ✅.
- **Patrimoine anomalies** : `test_patrimoine_anomalies_v58.py` couvre BUILDING_MISSING, METER_NO_DELIVERY_POINT, CONTRACT_OVERLAP, surface_mismatch. ✅ partiel.
- **Cascade recompute** : `test_cascade_recompute_audit_log_wiring.py:30-57` + `test_patch_sites_triggers_cascade.py`. ✅.
- **BACS** : suite très complète (test_bacs_*.py — 11+ fichiers). ✅.
- **Idempotence import** : `test_patrimoine.py:TestStagingPipeline.test_activate_idempotent()`. ✅.
- **Multi-org isolation** : `test_patrimoine_portfolio_v60.py:336-346`. ✅ pour summary, ❌ matrix par endpoint manquant.
- **Site is_demo NOT NULL** : `test_site_isdemo_not_null.py`. ✅.

### 8.2 Source guards (~48 patrimoine-related)

- `test_applicability_engine_source_guards.py:G1/G3/G5` — reason codes whitelist + DATA_MISSING.missing_inputs non-vide.
- `test_audit_log_no_direct_writes_source_guards.py` — interdit `db.add(AuditLog(...))` hors `audit_log_service`.
- `test_compteur_meter_bridge_source_guards.py` — bridge invariant.
- `test_meter_endpoints_org_scoping_source_guards.py` — endpoints org-scoped.
- `test_routes_patrimoine_init_reexports_source_guards.py` — package patrimoine intègre toutes les routes attendues.
- `test_site_3_surfaces_structure_source_guards.py` — surface_m2/tertiaire_area_m2/s_ce_m2 distincts.
- `test_site_isdemo_not_null.py` — fuites is_demo bloquées.
- `test_site_portefeuille_no_direct_fk_modification_source_guards.py` — assignement direct interdit.
- `test_cascade_recompute_no_direct_field_modification_source_guards.py` — toute mutation passe par le service cascade.

### 8.3 Frontend (≈7 tests)

- `frontend/src/__tests__/patrimoine_v2.test.js`, `patrimoine_intensity_phase43.test.js`, `phase1_site360_nav_unified.test.js`, `nav_patrimoine_contextual.test.js`, `sirene_onboarding.test.js`, `patrimoineV63.portfoliofix.test.js`, `patrimoineV64.distribution.test.js`.
- Aucun e2e Playwright wirée du parcours onboarding complet (multiples capture scripts dans `tools/playwright/captures/`, pas de spec testée).

### 8.4 E2E

- `tools/playwright/captures/` contient screenshots historiques pour audits visuels. Pas de spec exécuté en CI sur l'onboarding.

---

## 9. Tests manquants

### P0 (bloquants)

| Test à créer | Niveau | Couvre |
|---|---|---|
| `test_facture_sans_compteur_refusee.py` | backend | Facture importée sans `Compteur` / `EnergyContract` / `period_start` → refus (HTTP 422 + reason). Aujourd'hui `staging` accepte. |
| `test_patrimoine_crud_audit_log_wiring.py` | backend source-guard | Chaque PATCH/DELETE de `routes/patrimoine_crud.py` appelle `log_patrimoine_change`. |
| `test_bulk_import_triggers_cascade.py` | backend | `/api/import/sites` déclenche `cascade_recompute_on_change` ou batch_recompute pour chaque site créé. |
| `test_quick_create_route_deprecated_unwired.py` | backend+frontend | `QuickCreateSite.jsx` n'appelle plus `/api/sites/quick-create`. |
| `test_data_missing_drill_down_e2e.spec.js` | playwright | Cliquer "Données manquantes · N sites" dans `CadreApplicable` → ouvre liste cliquable des sites avec champs concernés. |
| `test_patch_site_operat_triggers_applicability_refresh.py` | backend | PATCH `tertiaire_area_m2` → applicability recalculée et persistée (pas seulement `compliance_score`). |
| `test_org_endpoint_isolation_matrix.py` | backend | Matrix 8×N : pour chaque endpoint patrimoine, org A ne voit pas patrimoine org B (forme étendue de `test_v57_multiorg_isolation`). |

### P1 (crédibilité produit)

| Test | Niveau | Couvre |
|---|---|---|
| `test_building_without_meters.py` | backend | Bâtiment sans aucun compteur → anomalie ou warning + résolution path. |
| `test_compteur_to_meter_bridge_auto.py` | backend | Création de Compteur via wizard → Meter miroir présent. |
| `test_soft_delete_patrimoine_cascade.py` | backend | Soft-delete Site → Batiments + Compteurs + DeliveryPoints conservés ou archivés selon doctrine. |
| `test_onboarding_workflow_e2e.spec.js` | playwright | Flux complet PME : Sirène → SurfaceCapture → SiteCreationWizard → /patrimoine populé → /cockpit/strategique correct. |
| `test_data_missing_field_path_structure.py` | backend source-guard | Chaque `DATA_MISSING.*` expose un `missing_inputs` au format `models.field` (parsable côté UI). |

### P2 (différenciation)

| Test | Niveau | Couvre |
|---|---|---|
| `test_delivery_point_state_transitions.py` | backend | Lifecycle PRM/PCE (ACTIVE → ARCHIVED). |
| `test_incremental_csv_sync_dedupe_accuracy.py` | backend | Re-import partiel d'un CSV : dedupe par siret/nom CP, pas par count. |
| `test_cascade_resilience_audit_log_failure.py` | backend | (déjà partiel) audit_log fail ≠ rollback mutation. |
| `test_remediation_field_in_rule_applicability.py` | backend | `RuleApplicability.to_dict()` expose `remediation_field: "site.tertiaire_area_m2"` machine-readable. |

---

## 10. Plan de correction

### P0 — Bloquants production B2B (Sprint 1)

1. **Drill-down DATA_MISSING UI**
   - Backend : enrichir `RuleApplicability.to_dict()` (`backend/regulatory/applicability_types.py`) avec `remediation_field` + `affected_site_ids[]`.
   - Frontend : `CadreApplicable.jsx` — implémenter `onRuleClick` avec drawer "Sites incomplets" cliquables vers `DrawerEditSite`.
   - Test : Playwright `test_data_missing_drill_down_e2e.spec.js`.
2. **Audit log sur tout `routes/patrimoine_crud.py` PATCH/DELETE**
   - Appliquer le pattern de `routes/patrimoine/sites.py` (`log_patrimoine_change` post-flush, pré-commit) aux 6 endpoints PATCH/DELETE Org/EJ/PF/Site (CRUD) + bâtiments.
   - Source-guard : `test_patrimoine_crud_audit_log_wiring.py`.
3. **Cascade sur import bulk**
   - `routes/import_sites.py` : après chaque `create_site_from_data` + `provision_site`, appeler `cascade_recompute_on_change` ou un nouveau `batch_cascade_recompute_sites([ids])`.
   - Test : `test_bulk_import_triggers_cascade.py`.
4. **Supprimer ou rediriger les routes mortes / doublons**
   - `routes/patrimoine.py` (fichier résiduel) : supprimer ou ne pas l'importer.
   - `routes/sites.py` (`/api/sites`, `/api/sites/quick-create`) : déprécier hard (HTTP 410) et migrer `QuickCreateSite.jsx` vers `/api/patrimoine/crud/sites`.
   - Documenter le SoT : `routes/patrimoine/sites.py` premium est canonique.
5. **PATCH `/api/patrimoine/crud/sites/{id}` doit re-raise**
   - Supprimer le try/except qui avale l'erreur, ou faire un fallback queue async tracé.
6. **Consolider les 5 entry-points de création patrimoine FE**
   - Décision produit : SireneOnboardingPage = onboarding initial (Org→EJ→Site), PatrimoineWizard = import CSV bulk, DrawerEditSite = modification incrémentale. Supprimer `OnboardingPage`, `SiteCreationWizard`, `QuickCreateSite` (ou les rendre des sous-composants des 2 précédents).
7. **Refondre Site360 (9 tabs → 5 + Avancé)**
   - Tabs core : Résumé / Conso / Factures / Conformité / Actions. Avancé : Analytics, Puissance, Réconciliation.
   - Exposer DeliveryPoints dans Résumé.

### P1 — Crédibilité produit (Sprint 2)

1. UI "Organisation / Entité juridique" pour saisir effectif, CA, bilan, conso 3y (champs SMÉ/BEGES).
2. Justification métier visible à chaque champ wizard (tooltip "pourquoi PROMEOS demande cette donnée").
3. Tooltips PRM/PCE/EFA partout (`SolAcronym` étendu).
4. Mode Expert dans PatrimoineWizard : mapping colonnes custom, règles métier avancées.
5. Source de donnée (Enedis/GRDF/facture/manuel/demo) en colonne Patrimoine.jsx.
6. Bridge Compteur ↔ Meter automatique sur création (`ensure_meter_pair` appelé dans CRUD compteur POST + sub-meter).
7. Audit endpoint isolation matrix `test_org_endpoint_isolation_matrix.py`.

### P2 — Différenciation (Sprint 3)

1. Unifier `EnergyContract` et `ContratCadre` (ou définir clairement le contrat sémantique).
2. Unifier `EntiteJuridique.organisation_id` FK et `OrgEntiteLink` N-N.
3. Export PDF audit "Certificat conformité" + signature trail.
4. Bulk actions Patrimoine.jsx (checkboxes déjà rendus mais non exploités).
5. Versioning API : tout `/api/` patrimoine → `/api/v1/`.
6. Supprimer composants morts `PatrimoineHeatmap`/`PatrimoinePortfolioHealthBar`/`PatrimoineRiskDistributionBar` (imports commentés).

---

## 11. Prompt de correction suivant

Le prompt ci-dessous est prêt à coller dans une nouvelle session Claude Code. Il **ne traite que les P0 patrimoine**.

````
Tu es Staff Engineer + QA Release Manager sur PROMEOS.

OBJECTIF
Corriger uniquement les P0 patrimoine identifiés dans
`docs/audits/audit_brique_patrimoine_deep_readonly_2026_05_23.md`.

BRANCHE
- Repartir d'une branche fille `claude/patrimoine-p0-fix` depuis `claude/refonte-sol2`.
- Pas de refacto en dehors du périmètre P0.

PÉRIMÈTRE STRICT P0 (6 chantiers indépendants, 1 commit par chantier)

CHANTIER 1 — Drill-down DATA_MISSING UI
- Backend : enrichir `backend/regulatory/applicability_types.py` `RuleApplicability.to_dict()`
  avec un champ optionnel `affected_site_ids: list[int]` et `remediation_field: str | None`.
- Mettre à jour `backend/regulatory/rules/dt.py`, `bacs.py`, `aper.py`, `sme.py`, `beges.py`
  pour fournir le `remediation_field` (ex. "site.tertiaire_area_m2",
  "batiment.cvc_power_kw[{batiment_id}]", "organisation.effectif_total").
- Frontend : `frontend/src/components/grammar/hub/CadreApplicable.jsx`
  - Implémenter `onRuleClick` (callback parent obligatoire si DATA_MISSING).
  - `frontend/src/pages/CockpitStrategique.jsx` : ajouter drawer
    "Sites incomplets" avec liste cliquable → `navigate('/patrimoine?incomplete=DT')`.
- `frontend/src/pages/Patrimoine.jsx` : ajouter filtre URL `?incomplete=<RULE>`
  qui ne montre que les sites avec `missing_inputs` non-vide pour la règle.
- Tests :
  - backend : `backend/tests/test_remediation_field_in_rule_applicability.py`.
  - source-guard : étendre `test_applicability_engine_source_guards.py::G5`
    pour vérifier `remediation_field` non-null sur tous `DATA_MISSING.*`.
  - frontend : `frontend/src/components/grammar/hub/__tests__/CadreApplicable.test.js`
    teste que cliquer un tile data_missing déclenche `onRuleClick(rule)`.

CHANTIER 2 — Audit log sur tout `routes/patrimoine_crud.py`
- Pattern de référence : `backend/routes/patrimoine/sites.py:494-620`
  (capture old/new payload, post-flush pré-commit `log_patrimoine_change`).
- Appliquer aux 6 endpoints :
  - PATCH /organisations/{id}
  - PATCH /entites/{id}
  - PATCH /portefeuilles/{id}
  - PATCH /sites/{id}
  - DELETE /organisations/{id}, /entites/{id}, /portefeuilles/{id}, /sites/{id}
- Source-guard à créer :
  `backend/tests/source_guards/test_patrimoine_crud_audit_log_wiring_source_guards.py`
  qui parse l'AST et vérifie que chaque endpoint PATCH/DELETE de patrimoine_crud
  contient un appel à `log_patrimoine_change`.

CHANTIER 3 — Cascade sur bulk import
- `backend/routes/import_sites.py` : après le commit final, déclencher
  un `batch_cascade_recompute_sites(site_ids: list[int])` (à créer dans
  `regops/services/cascade_recompute_service.py`).
- Idempotent : si appelé deux fois, ne fait rien.
- Test : `backend/tests/test_bulk_import_triggers_cascade.py`
  charge 3 sites via CSV puis vérifie que `applicability` est persistée pour chacun.

CHANTIER 4 — Suppression / dépréciation des routes mortes
- `backend/routes/patrimoine.py` (vide) : supprimer le fichier.
  Confirmer dans `main.py` que seul `routes.patrimoine.__init__:router` est wired.
- `backend/routes/sites.py` (`/api/sites` + `/api/sites/quick-create`) :
  retourner HTTP 410 Gone avec message
  "Endpoint déprécié, utiliser /api/patrimoine/crud/sites".
- `frontend/src/components/QuickCreateSite.jsx` : recâbler sur
  `crudCreateSite` (qui pointe `/api/patrimoine/crud/sites`).
- Tests :
  - `backend/tests/test_legacy_sites_route_gone.py` (HTTP 410).
  - vitest QuickCreateSite : doit appeler `crudCreateSite`.

CHANTIER 5 — PATCH crud/sites doit re-raise
- `backend/routes/patrimoine_crud.py:609-615` : supprimer le try/except
  qui avale `recompute_site_full`. Si recompute échoue → 5xx OU appeler une
  queue async tracée (préférable : 5xx pour MVP).
- Test : `test_patch_crud_site_raises_on_recompute_failure.py`.

CHANTIER 6 — Site360 : 5 tabs core + "Avancé"
- `frontend/src/pages/Site360.jsx` :
  - Onglets visibles top-level : Résumé / Conso / Factures / Conformité / Actions.
  - Onglets dans accordion "Avancé" : Analytics / Puissance / Réconciliation.
  - Section "Delivery Points" déplacée dans le Résumé (visible direct).
- Test e2e : `tools/playwright/site360_tabs.spec.mjs`.

CONTRAINTES
- 1 commit par chantier (6 commits au total).
- Chaque commit ajoute son test associé. CI verte requise.
- Aucune modification hors P0 patrimoine.
- Format commit : `fix(patrimoine,P0): <chantier> — <description>`.
- Aucune dépendance ajoutée.

LIVRABLE
- 6 commits sur `claude/patrimoine-p0-fix`
- README du PR contenant : tableau P0 → fichier → test associé.
````

---

*Audit clôturé le 2026-05-23. Toutes les affirmations citent `file:ligne` quand applicable ; les chiffres de lignes peuvent dériver d'un commit à l'autre — référence verrouillée à `claude/refonte-sol2@ade3d0a0`.*

---

## 12. Correctifs P0-A réalisés (2026-05-23)

> **Branche** : `claude/patrimoine-p0a-clean-routes-audit-cascade`
> **Doctrine** : ne pas construire par-dessus du legacy. Relocaliser, ne pas dupliquer. Auditer toute mutation. Aucune erreur silencieuse.
> **Référence canonique post-fix** : [`docs/dev/patrimoine_routes_canonical.md`](../dev/patrimoine_routes_canonical.md)

### 12.1 Phase 1 — Routes legacy nettoyées

- `backend/routes/patrimoine.py` (0 octets — collision potentielle avec le package) **supprimé**.
- `POST /api/sites/quick-create` → **HTTP 410 Gone** + payload `{code: PATRIMOINE_ROUTE_GONE, message FR, replacement, doc}`.
- `POST /api/sites` → **HTTP 410**.
- `GET /api/sites` → **HTTP 410**.
- Endpoint canonique créé par **relocation** (pas de nouvelle route concurrente) : `POST /api/patrimoine/crud/sites/quick-create` dans `routes/patrimoine_crud.py` (auto-création hiérarchie Org/EJ/PF, anti-doublons, audit + cascade).
- Frontend `services/api/patrimoine.js` migré : `getSites`, `getSite`, `createSite`, `quickCreateSite` pointent désormais sur `/api/patrimoine/*`. `QuickCreateSite.jsx` inchangé (importe via le shim).

### 12.2 Phase 2 — Audit log sur toutes les mutations CRUD

Les **5 endpoints PATCH** + **5 endpoints DELETE** de `routes/patrimoine_crud.py` (Organisation, EntiteJuridique, Portefeuille, Site, Batiment) appellent désormais systématiquement `services.audit_log_service.log_patrimoine_change`.

Helpers ajoutés en haut du fichier :
- `_capture_before(entity, fields)` — snapshot des valeurs avant mutation.
- `_diff_after(entity, before)` — diff strict (ignore les champs non modifiés).
- `_audit_headers(request, auth)` — extrait `correlation_id`, `ip_address`, `user_agent`, `user_id`.

Actions canoniques : `<entity>.update` / `<entity>.archive` / `<entity>.delete` / `site.create`.

### 12.3 Phase 3 — Cascade après import bulk

Nouvelle fonction publique dans `regops/services/cascade_recompute_service.py` :

```python
batch_cascade_recompute_sites(db, *, site_ids, org_id, user_id=None,
                              correlation_id=None, ip_address=None, user_agent=None) -> dict
```

- **Idempotente** : compare le résultat calculé à la valeur stockée, ne persiste que si différent.
- **Statut explicite** : `recomputed` / `pending_recompute` (données amont manquantes) / `up_to_date` / `errors`.
- **Audit trail** : écrit `site.cascade_recompute` ou `site.cascade_pending` selon le cas.
- **Wirings** :
  - `routes/import_sites.py:import_sites_csv` — post-import bulk.
  - `routes/patrimoine_crud.py:quick_create_site_crud` — post quick-create.

### 12.4 Phase 4 — Plus d'erreur silencieuse sur PATCH /sites

`update_site_crud` (patrimoine_crud.py) : le `try/except` qui logait un `warning` sans re-raise a été remplacé par :
- `db.rollback()` ;
- `HTTPException(500, detail={code: PATRIMOINE_RECOMPUTE_FAILED, message FR, hint, correlation_id, blocking: true})`.

Source-guard AST `test_patrimoine_crud_audit_log_wiring_source_guards.py::test_no_swallow_recompute_in_crud_sites` verrouille la non-réintroduction du pattern.

### 12.5 Phase 5 — Tests

5 nouveaux fichiers, **24 tests, 24 verts** :

| Fichier | Tests |
|---|---|
| `tests/test_legacy_sites_route_gone.py` | 4 (3 endpoints × 410 + check message FR) |
| `tests/test_patrimoine_crud_audit_log_wiring.py` | 10 (5 PATCH + 4 DELETE + 1 no-op) |
| `tests/test_bulk_import_triggers_cascade.py` | 4 (cascade summary + audit + idempotence + missing surface) |
| `tests/test_patch_crud_site_raises_on_recompute_failure.py` | 3 (500 + rollback + champ non-conformité) |
| `tests/source_guards/test_patrimoine_crud_audit_log_wiring_source_guards.py` | 2 (AST log_patrimoine_change + AST no-swallow) |

**Non-régression** : 276 tests verts sur la suite patrimoine + cascade + regulatory + 41 source-guards. 2 baselines pré-existantes désélectionnées (`OrgEntiteLink.role="a"` et `CASCADE_MAP` set comparison) — ces 2 fails existent déjà sur `claude/refonte-sol2` sans rapport avec ce sprint.

### 12.6 Impact sur les 5 risques majeurs initiaux

| Risque P0 initial | Statut post-P0-A |
|---|---|
| 1. `CadreApplicable` DATA_MISSING non actionnable | ❌ **HORS scope P0-A** (FE/UI — Sprint P0-B) |
| 2. 5 entry-points création patrimoine concurrents | ⏳ **Partiel** — endpoint canonique BE unifié, FE wizards à consolider (Sprint P0-B) |
| 3. CRUD patrimoine sans audit trail | ✅ **CORRIGÉ** — 10 endpoints PATCH/DELETE wirés + source-guard AST |
| 4. Bulk import sans cascade | ✅ **CORRIGÉ** — `batch_cascade_recompute_sites` idempotent + audit |
| 5. Doublons référentiels Compteur/Meter + 3 routers /sites | ⏳ **Partiel** — `/api/sites` legacy en 410, routers Compteur/Meter inchangés (ADR-D-01 reste, hors scope P0-A) |

### 12.7 Critères d'acceptation P0-A — checklist

- [x] `POST /api/sites/quick-create` retourne 410.
- [x] Plus aucun appel front à `/api/sites/quick-create` (audit `frontend/src/services/api/patrimoine.js`).
- [x] PATCH/DELETE patrimoine_crud loggent les mutations (source-guard AST + 10 tests unitaires).
- [x] Import bulk déclenche cascade ou statut `pending_recompute` explicite (audit trail + 4 tests).
- [x] Échec recompute n'est plus silencieux (HTTP 500 + rollback + 3 tests).
- [x] Tests nouveaux verts (24/24).
- [x] Tests existants patrimoine/réglementaire verts (276 + 41 SG, 2 baselines pré-existantes désélectionnées).
- [x] Aucun nouvel écran.
- [x] Aucune route concurrente — relocation propre, pas de doublon.
- [x] Code mort supprimé (`backend/routes/patrimoine.py` 0 octets).

---

## 13. Correctifs P0-B réalisés (2026-05-23)

> **Branche** : `claude/patrimoine-p0b-actionnable-onboarding`
> **Doctrine** : rendre le patrimoine actionnable côté utilisateur, sans reconstruire par-dessus du legacy. Aucun nouvel écran. Aucune route concurrente. Tout texte en français clair, sans jargon non expliqué.

### 13.1 Chantier 1 — Audit log sur POST création (complète P0-A)

P0-A avait câblé PATCH/DELETE. P0-B complète avec les **4 POST manquants** dans `routes/patrimoine_crud.py` :

- `POST /api/patrimoine/crud/organisations` → audit `organisation.create`
- `POST /api/patrimoine/crud/entites` → audit `entite_juridique.create`
- `POST /api/patrimoine/crud/portefeuilles` → audit `portefeuille.create`
- `POST /api/patrimoine/crud/batiments` → audit `batiment.create`

(Les POST `/sites` et `/sites/quick-create` étaient déjà couverts par P0-A.)

**Pattern uniforme** : `log_patrimoine_change(action="<entity>.create", old_value=None, new_value=payload, correlation_id, ip, ua)`. **Source-guard AST** : `tests/source_guards/test_patrimoine_crud_post_audit_log_source_guards.py` verrouille la présence de l'appel sur chaque POST + interdit l'appel sur les GET.

**Résultat** : aucune création patrimoine silencieuse possible. Patrimoine = entièrement audité.

### 13.2 Chantier 2 — DATA_MISSING enrichi

Nouveau fichier `backend/regulatory/remediation.py` — SoT du mapping `reason_code` → instructions de remédiation FR (5 champs).

**`RuleApplicability.to_dict()` auto-enrichit** quand `status=DATA_MISSING` :

```json
{
  "status": "data_missing",
  "reason_code": "DT.DATA_MISSING.SURFACE",
  "remediation_field": "site.tertiaire_area_m2",
  "remediation_level": "site",
  "remediation_label_fr": "Surface tertiaire",
  "remediation_hint_fr": "Renseignez la surface tertiaire pour confirmer si le site est soumis au Décret Tertiaire.",
  "cta_label_fr": "Compléter la surface",
  "affected_site_ids": [42]
}
```

**9 codes DATA_MISSING** mappés (DT/BACS/APER/SMÉ/BEGES). Aucune rule à modifier — l'enrichissement est central.

**Source-guard** : `test_data_missing_remediation_source_guards.py` impose la bijection `reason_codes.REASON_CODES ↔ REASON_CODE_TO_REMEDIATION`. Toute ajout d'un nouveau code DATA_MISSING sans remediation FR fait échouer le build.

### 13.3 Chantier 3 — CadreApplicable interactif

`frontend/src/components/grammar/hub/CadreApplicable.jsx` refondu :

- **Tuile DATA_MISSING cliquable** (autres tuiles non-cliquables sauf si `onRuleClick` custom fourni).
- **Panneau interne `DataMissingPanel`** : titre règle, liste des sites concernés (label + champ FR + hint), bouton "Compléter dans Patrimoine".
- **Navigation** : `navigate('/patrimoine?incomplete=<RULE>')` via `useNavigate` (fallback `window.location` hors RouterProvider).
- Le label du CTA provient de `cta_label_fr` enrichi backend, sinon fallback "Compléter dans Patrimoine".

**Aucun changement** dans `CockpitStrategique.jsx` — le composant `CadreApplicable` est consommé tel quel, le comportement interactif s'active automatiquement.

### 13.4 Chantier 4 — Patrimoine filtré par donnée manquante

`pages/Patrimoine.jsx` comprend désormais `?incomplete=<RULE>` :

- **Bandeau FR** en haut de page : *"Sites à compléter pour le Décret Tertiaire — 4 sites"* + explication courte + bouton "Effacer le filtre".
- **Filtre table** : fetch `/api/regulatory/applicability`, extraction des `scope_id` avec `status=data_missing` pour la règle, restriction de la table à ces sites.
- Pour les données niveau organisation/EJ : bandeau affiche *"À compléter dans les informations de l'organisation (écran en préparation)"* — pas de filtre table.
- Composant extrait dans `components/patrimoine/IncompleteBanner.jsx` pour testabilité isolée.
- Service API ajouté : `getRegulatoryApplicability` dans `services/api/conformite.js`.

### 13.5 Chantier 5 — Onboarding consolidé (sans refonte)

`App.jsx` : **`/onboarding` redirige désormais vers `/onboarding/sirene`** (avant : impasse `/cockpit/jour`).

**Hiérarchie canonique des entry-points** (cf. `docs/dev/patrimoine_routes_canonical.md §9`) :

| Cas d'usage | Composant canonique |
|---|---|
| Création initiale | `SireneOnboardingPage` (route `/onboarding/sirene`) |
| Import bulk CSV | `PatrimoineWizard` (depuis Patrimoine) |
| Création manuelle | `QuickCreateSite` (drawer depuis Patrimoine) |
| Édition incrémentale | `DrawerEditSite` (clic ligne) |
| Détaillé 7 étapes | `SiteCreationWizard` (sous-composant interne de QuickCreate, plus d'entrée principale) |

**`OnboardingPage` neutralisé** : fichier conservé pour réutilisation Phase 4, aucune route active ne le rend. **Aucun nouvel écran d'aiguillage créé** — l'empty-state de Patrimoine (3 boutons "Depuis Sirene / Nouveau site manuel / Importer CSV") joue déjà ce rôle.

### 13.6 Tests P0-B

| Fichier | Tests |
|---|---|
| `tests/test_patrimoine_crud_create_audit_log.py` | 5 (4 POST + 1 GET sans audit) |
| `tests/source_guards/test_patrimoine_crud_post_audit_log_source_guards.py` | 2 (AST POST + AST GET-no-log) |
| `tests/test_regulatory_remediation_fields.py` | 22 (mapping + bijection + to_dict enrichi + zero pollution autres statuts + scopes) |
| `tests/source_guards/test_data_missing_remediation_source_guards.py` | 12 (bijection + structurel par code) |
| `frontend/src/components/grammar/hub/__tests__/CadreApplicable.test.jsx` | 6 (clickable / non-clickable / CTA navigation / callback / fermeture) |
| `frontend/src/components/patrimoine/__tests__/IncompleteBanner.test.jsx` | 7 (libellé FR / hint / org-level / clear / pluriel / 5 règles / no-anglais) |
| `frontend/src/__tests__/onboarding_entrypoints.test.jsx` | 6 (redirect / pas vers cockpit/jour / OnboardingPage neutralisé / SiteCreationWizard sous-composant) |

**Total P0-B : 60 tests verts** (41 BE + 19 FE). **Non-régression** : 288 tests patrimoine/regulatory baseline verts (mêmes 2 baselines pré-existantes désélectionnées).

### 13.7 Impact sur les 5 risques majeurs initiaux

| Risque P0 initial | Statut après P0-A + P0-B |
|---|---|
| 1. `CadreApplicable` DATA_MISSING non actionnable | ✅ **CORRIGÉ** — panneau interactif + navigation vers Patrimoine filtré |
| 2. 5 entry-points création patrimoine concurrents | ✅ **CORRIGÉ** — `/onboarding` canonisé sur Sirène, `SiteCreationWizard` rétrogradé en sous-composant, `OnboardingPage` neutralisé, hiérarchie documentée |
| 3. CRUD patrimoine sans audit trail | ✅ **CORRIGÉ** — POST + PATCH + DELETE tous wirés (15 endpoints), double source-guard AST (PATCH/DELETE en P0-A, POST en P0-B) |
| 4. Bulk import sans cascade | ✅ **CORRIGÉ** — `batch_cascade_recompute_sites` idempotent (P0-A) |
| 5. Doublons Compteur/Meter + 3 routers /sites | ⏳ **Partiel** — `/api/sites` legacy en 410 (P0-A), Compteur/Meter inchangé (ADR-D-01 hors P0) |

### 13.8 Critères d'acceptation P0-B — checklist

- [x] Tous les POST création patrimoine sont audités.
- [x] Aucun DATA_MISSING sans `remediation_field` (verrou source-guard).
- [x] `CadreApplicable` permet d'agir sur les données manquantes (panneau + CTA).
- [x] Patrimoine comprend `?incomplete=<RULE>` (bandeau + filtre).
- [x] `/onboarding` ne redirige plus vers `/cockpit/jour`.
- [x] Parcours onboarding limités à 3 entry-points canoniques explicables.
- [x] Aucun nouvel écran fantôme (composants créés : `IncompleteBanner.jsx` extrait + `remediation.py` SoT — pas d'écran).
- [x] Aucun nouvel endpoint concurrent (BE : aucun ajout d'endpoint, juste enrichissement de payload + audit + relocation).
- [x] Aucun jargon non expliqué dans les nouveaux textes FR (test pure-grep `IncompleteBanner.test.jsx` vérifie l'absence d'anglais résiduel).
- [x] Tests nouveaux verts (60/60).
- [x] Tests P0-A non régressés (24/24 toujours verts + 288 baseline).

