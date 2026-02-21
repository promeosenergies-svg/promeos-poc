# Dictionnaire de donnees PROMEOS

> Reference automatique -- alignee sur les modeles SQLAlchemy du backend.
> Derniere mise a jour : V26

## Table des matieres

1. [Regles generales](#regles-generales)
2. [Enums](#enums)
3. [Core / Organisation](#core--organisation) -- `organisations`, `entites_juridiques`, `portefeuilles`
4. [Sites & Batiments](#sites--batiments) -- `sites`, `batiments`
5. [IAM](#iam) -- `users`, `user_org_roles`, `user_scopes`, `audit_logs`
6. [Patrimoine / Staging](#patrimoine--staging) -- liens N-N, staging pipeline, `delivery_points`
7. [Compteurs & Consommation](#compteurs--consommation) -- `compteurs`, `consommations`
8. [Conformite / Compliance](#conformite--compliance) -- `obligations`, `evidences`, `compliance_findings`, `compliance_run_batches`
9. [BACS Expert](#bacs-expert) -- `bacs_assets`, `bacs_cvc_systems`, `bacs_assessments`, `bacs_inspections`
10. [Bill Intelligence](#bill-intelligence) -- contrats, factures, insights facturation
11. [Achat Energie](#achat-energie) -- hypotheses, scenarios, preferences
12. [Energy Models / Analytics](#energy-models--analytics) -- `meter`, readings, anomalies, recommandations
13. [Monitoring / Alertes](#monitoring--alertes) -- snapshots, alertes monitoring, alertes legacy
14. [Consumption Insights & Targets](#consumption-insights--targets)
15. [Action Hub](#action-hub) -- `action_items`, events, commentaires, pieces
16. [Notifications](#notifications) -- events, batches, preferences
17. [RegOps / Infrastructure](#regops--infrastructure) -- assessments, jobs, datapoints, AI insights, watchers
18. [Segmentation](#segmentation)
19. [Smart Intake](#smart-intake)
20. [Knowledge Base](#knowledge-base)
21. [EMS Explorer](#ems-explorer) -- weather cache, saved views, collections
22. [Tarification](#tarification) -- TOU schedules, tariff calendars, site tariff profiles
23. [Decarbonation](#decarbonation) -- emission factors

---

## Regles generales

- **Hierarchie** : Organisation -> EntiteJuridique -> Portefeuille -> Site -> Batiment -> Zone
- **Scope** : `org_id` obligatoire sur la plupart des tables
- **Audit trail** : `created_at`, `updated_at` (automatiques via `TimestampMixin`)
- **Soft delete** : `deleted_at`, `deleted_by`, `delete_reason` (via `SoftDeleteMixin` sur les tables marquees)
- **Mixins** :
  - `TimestampMixin` : `created_at` (DateTime, NOT NULL, default utcnow), `updated_at` (DateTime, NOT NULL, default utcnow, onupdate utcnow)
  - `SoftDeleteMixin` : `deleted_at` (DateTime, nullable, indexed), `deleted_by` (String(200), nullable), `delete_reason` (String(500), nullable)

---

## Enums

### Sites & Assets

| Enum | Valeurs | Description |
| ------ | --------- | ------------- |
| `TypeSite` | magasin, usine, bureau, entrepot, commerce, copropriete, logement_social, collectivite, hotel, sante, enseignement | Types de sites B2B France |
| `TypeCompteur` | electricite, gaz, eau | Types de compteurs d'energie |
| `SeveriteAlerte` | info, warning, critical | Niveaux de severite des alertes |
| `TypeUsage` | bureaux, process, froid, cvc, eclairage, it, autres | Types d'usage energetique |

### Conformite

| Enum | Valeurs | Description |
| ------ | --------- | ------------- |
| `StatutConformite` | conforme, derogation, a_risque, non_conforme | Statut de conformite |
| `TypeObligation` | decret_tertiaire, bacs, aper | Types d'obligations reglementaires |
| `TypeEvidence` | audit, facture, certificat, rapport, photo, declaration, attestation_bacs, derogation_bacs | Types de preuves |
| `StatutEvidence` | valide, en_attente, manquant, expire | Statut de preuve |

### RegOps / Lifecycle

| Enum | Valeurs | Description |
| ------ | --------- | ------------- |
| `ParkingType` | outdoor, indoor, underground, silo, unknown | Type de parking |
| `OperatStatus` | not_started, in_progress, submitted, verified, unknown | Statut OPERAT |
| `EnergyVector` | electricity, gas, heat, other | Vecteur energetique |
| `SourceType` | manual, import, api, scrape | Source de donnee |
| `JobType` | recompute_assessment, sync_connector, run_watcher, run_ai_agent | Types de jobs async |
| `JobStatus` | pending, running, done, failed | Statut de job |
| `RegStatus` | compliant, at_risk, non_compliant, unknown, out_of_scope, exemption_possible | Statut reglementaire |
| `Severity` | low, medium, high, critical | Severite generique |
| `Confidence` | high, medium, low | Niveaux de confiance |
| `InsightType` | explain, suggest, change_impact, exec_brief, data_quality | Types d'insight IA |
| `RegulationType` | tertiaire_operat, bacs, aper, cee_p6 | Types de reglementation |
| `Typologie` | tertiaire_prive, tertiaire_public, industrie, commerce_retail, copropriete_syndic, bailleur_social, collectivite, hotellerie_restauration, sante_medico_social, enseignement, mixte | Segments client B2B |

### Enums Bill Intelligence

| Enum | Valeurs | Description |
| ------ | --------- | ------------- |
| `BillingEnergyType` | elec, gaz | Type d'energie facturation |
| `InvoiceLineType` | energy, network, tax, other | Type de ligne facture |
| `BillingInvoiceStatus` | imported, validated, audited, anomaly, archived | Statut facture |
| `InsightStatus` | open, ack, resolved, false_positive | Statut workflow insight |

### Enums Achat Energie

| Enum | Valeurs | Description |
| ------ | --------- | ------------- |
| `PurchaseStrategy` | fixe, indexe, spot | Strategie d'achat |
| `PurchaseRecoStatus` | draft, accepted, rejected | Statut recommandation achat |

### Enums Action Hub

| Enum | Valeurs | Description |
| ------ | --------- | ------------- |
| `ActionSourceType` | compliance, consumption, billing, purchase, insight, manual | Source de l'action |
| `ActionStatus` | open, in_progress, done, blocked, false_positive | Statut workflow action |

### Enums Notifications

| Enum | Valeurs | Description |
| ------ | --------- | ------------- |
| `NotificationSeverity` | info, warn, critical | Severite notification |
| `NotificationStatus` | new, read, dismissed | Statut lifecycle notification |
| `NotificationSourceType` | compliance, billing, purchase, consumption, action_hub | Source notification |

### Enums IAM

| Enum | Valeurs | Description |
| ------ | --------- | ------------- |
| `UserRole` | dg_owner, dsi_admin, daf, acheteur, resp_conformite, energy_manager, resp_immobilier, resp_site, prestataire, auditeur, pmo_acc | 11 roles metier PROMEOS |
| `ScopeLevel` | org, entite, site | Niveau de scope hierarchique |
| `PermissionAction` | view, edit, admin, export, sync, approve | Actions granulaires |

### Enums Patrimoine / Staging

| Enum | Valeurs | Description |
| ------ | --------- | ------------- |
| `StagingStatus` | draft, validated, applied, abandoned | Statut batch staging |
| `ImportSourceType` | excel, csv, invoice, manual, demo, api | Source d'import |
| `QualityRuleSeverity` | critical, blocking, warning, info | Severite finding qualite |
| `ActivationLogStatus` | started, success, failed, rolled_back | Statut activation batch |
| `DeliveryPointStatus` | active, inactive | Statut point de livraison |
| `DeliveryPointEnergyType` | elec, gaz | Type energie point de livraison |

### Enums Smart Intake

| Enum | Valeurs | Description |
| ------ | --------- | ------------- |
| `IntakeSessionStatus` | draft, in_progress, completed, abandoned | Statut session intake |
| `IntakeMode` | wizard, chat, bulk, demo | Mode d'intake |
| `IntakeSource` | user, import, system, system_demo, ai_prefill | Source reponse intake |
| `WatcherEventStatus` | new, reviewed, applied, dismissed | Statut evenement watcher |

### Enums BACS Expert

| Enum | Valeurs | Description |
| ------ | --------- | ------------- |
| `CvcSystemType` | heating, cooling, ventilation | Type systeme CVC |
| `CvcArchitecture` | cascade, network, independent | Architecture CVC |
| `BacsTriggerReason` | threshold_290, threshold_70, renewal, new_construction | Raison obligation BACS |
| `InspectionStatus` | scheduled, completed, overdue | Statut inspection quinquennale |

---

## Core / Organisation

### `organisations`

Mixins : TimestampMixin, SoftDeleteMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| nom | String | NOT NULL | -- | Nom de l'organisation |
| type_client | String | NULL | -- | Segment : retail, tertiaire, industrie |
| logo_url | String | NULL | -- | URL du logo |
| siren | String(9) | NULL | -- | Numero SIREN |
| actif | Boolean | NOT NULL | True | Organisation active |
| is_demo | Boolean | NOT NULL | False | Donnees de demonstration |

Relations : `entites_juridiques` (1-N -> EntiteJuridique)

### `entites_juridiques`

Mixins : TimestampMixin, SoftDeleteMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| organisation_id | Integer | NOT NULL | -- | FK -> organisations.id |
| nom | String | NOT NULL | -- | Nom de l'entite juridique |
| siren | String(9) | NOT NULL | -- | Numero SIREN (UNIQUE) |
| siret | String(14) | NULL | -- | Numero SIRET siege |
| naf_code | String(5) | NULL | -- | Code NAF principal |
| region_code | String(3) | NULL | -- | Code region |
| insee_code | String(5) | NULL | -- | Code INSEE siege |

Relations : `organisation` (N-1 -> Organisation), `portefeuilles` (1-N -> Portefeuille)

### `portefeuilles`

Mixins : TimestampMixin, SoftDeleteMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| entite_juridique_id | Integer | NOT NULL | -- | FK -> entites_juridiques.id |
| nom | String | NOT NULL | -- | Nom du portefeuille |
| description | String | NULL | -- | Description |

Relations : `entite_juridique` (N-1), `sites` (1-N -> Site, cascade delete)

---

## Sites & Batiments

### `sites`

Mixins : TimestampMixin, SoftDeleteMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| nom | String(200) | NOT NULL | -- | Nom du site (indexed) |
| type | Enum(TypeSite) | NOT NULL | -- | Type de site |
| adresse | String(300) | NULL | -- | Adresse postale |
| code_postal | String(10) | NULL | -- | Code postal (indexed) |
| ville | String(100) | NULL | -- | Ville (indexed) |
| region | String(100) | NULL | -- | Region |
| surface_m2 | Float | NULL | -- | Surface en m2 |
| nombre_employes | Integer | NULL | -- | Nombre d'employes |
| latitude | Float | NULL | -- | Latitude GPS |
| longitude | Float | NULL | -- | Longitude GPS |
| actif | Boolean | NOT NULL | True | Site actif |
| portefeuille_id | Integer | NULL | -- | FK -> portefeuilles.id (indexed) |
| statut_decret_tertiaire | Enum(StatutConformite) | NULL | A_RISQUE | Statut decret tertiaire |
| avancement_decret_pct | Float | NOT NULL | 0.0 | % avancement decret (0-100) |
| statut_bacs | Enum(StatutConformite) | NULL | A_RISQUE | Statut BACS |
| anomalie_facture | Boolean | NOT NULL | False | Anomalie facture detectee |
| action_recommandee | String | NULL | -- | Action recommandee |
| risque_financier_euro | Float | NOT NULL | 0.0 | Risque financier EUR |
| siret | String(14) | NULL | -- | SIRET du site |
| insee_code | String(5) | NULL | -- | Code INSEE commune |
| naf_code | String(5) | NULL | -- | Code NAF override |
| tertiaire_area_m2 | Float | NULL | -- | Surface tertiaire assujettie (m2) |
| roof_area_m2 | Float | NULL | -- | Surface toiture (m2) |
| parking_area_m2 | Float | NULL | -- | Surface parking (m2) |
| parking_type | Enum(ParkingType) | NULL | -- | Type de parking |
| is_multi_occupied | Boolean | NOT NULL | False | Site multi-occupant |
| operat_status | Enum(OperatStatus) | NULL | -- | Statut OPERAT |
| operat_last_submission_year | Integer | NULL | -- | Derniere annee declaration OPERAT |
| annual_kwh_total | Float | NULL | -- | Conso annuelle totale (kWh) |
| last_energy_update_at | DateTime | NULL | -- | Derniere MAJ donnees energie |
| is_demo | Boolean | NOT NULL | False | Donnees de demonstration |
| data_source | String(20) | NULL | -- | csv, manual, demo, api |
| data_source_ref | String(200) | NULL | -- | Batch ID / filename |
| imported_at | DateTime | NULL | -- | Date d'import |
| imported_by | Integer | NULL | -- | User ID importateur |

Relations : `compteurs` (1-N), `alertes` (1-N), `portefeuille` (N-1), `batiments` (1-N), `obligations` (1-N), `delivery_points` (1-N), `meters` (1-N)

### `batiments`

Mixins : TimestampMixin, SoftDeleteMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| nom | String | NOT NULL | -- | Nom du batiment |
| surface_m2 | Float | NOT NULL | -- | Surface en m2 |
| annee_construction | Integer | NULL | -- | Annee de construction |
| cvc_power_kw | Float | NULL | -- | Puissance CVC nominale (kW) |

Relations : `site` (N-1 -> Site), `usages` (1-N backref), `bacs_assets` (1-N backref)

---

## IAM

### `users`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| email | String(255) | NOT NULL | -- | Email (UNIQUE, indexed) |
| hashed_password | String(255) | NOT NULL | -- | Mot de passe hache |
| nom | String(100) | NOT NULL | -- | Nom de famille |
| prenom | String(100) | NOT NULL | -- | Prenom |
| actif | Boolean | NOT NULL | True | Compte actif |
| last_login | DateTime | NULL | -- | Derniere connexion |

Relations : `org_roles` (1-N -> UserOrgRole)

### `user_org_roles`

Mixins : TimestampMixin. Contrainte UNIQUE : (user_id, org_id)

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| user_id | Integer | NOT NULL | -- | FK -> users.id |
| org_id | Integer | NOT NULL | -- | FK -> organisations.id |
| role | Enum(UserRole) | NOT NULL | -- | Role metier PROMEOS |

Relations : `user` (N-1), `organisation` (N-1), `scopes` (1-N -> UserScope)

### `user_scopes`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| user_org_role_id | Integer | NOT NULL | -- | FK -> user_org_roles.id |
| scope_level | Enum(ScopeLevel) | NOT NULL | -- | Niveau : org, entite, site |
| scope_id | Integer | NOT NULL | -- | ID de l'objet scope |
| expires_at | DateTime | NULL | -- | Expiration du scope |
| created_at | DateTime | NOT NULL | utcnow | Date de creation |

Relations : `user_org_role` (N-1)

### `audit_logs`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| user_id | Integer | NULL | -- | FK -> users.id |
| action | String(50) | NOT NULL | -- | Action executee |
| resource_type | String(50) | NULL | -- | Type de ressource |
| resource_id | String(100) | NULL | -- | ID de la ressource |
| detail_json | Text | NULL | -- | Details (JSON) |
| ip_address | String(45) | NULL | -- | Adresse IP |
| created_at | DateTime | NOT NULL | utcnow | Date |

---

## Patrimoine / Staging

### `org_entite_links`

Mixins : TimestampMixin. Contrainte UNIQUE : (organisation_id, entite_juridique_id)

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| organisation_id | Integer | NOT NULL | -- | FK -> organisations.id |
| entite_juridique_id | Integer | NOT NULL | -- | FK -> entites_juridiques.id |
| role | String(50) | NULL | -- | proprietaire, gestionnaire, locataire |
| start_date | Date | NULL | -- | Date de debut |
| end_date | Date | NULL | -- | Date de fin |
| confidence | Float | NOT NULL | 1.0 | Confiance du lien 0-1 |
| source_ref | String(200) | NULL | -- | Reference source |

### `portfolio_entite_links`

Mixins : TimestampMixin. Contrainte UNIQUE : (portefeuille_id, entite_juridique_id)

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| portefeuille_id | Integer | NOT NULL | -- | FK -> portefeuilles.id |
| entite_juridique_id | Integer | NOT NULL | -- | FK -> entites_juridiques.id |
| role | String(50) | NULL | -- | Role du lien |

### `staging_batches`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| org_id | Integer | NULL | -- | FK -> organisations.id |
| user_id | Integer | NULL | -- | FK -> users.id |
| status | Enum(StagingStatus) | NOT NULL | DRAFT | Statut du batch |
| source_type | Enum(ImportSourceType) | NOT NULL | -- | Source d'import |
| filename | String(500) | NULL | -- | Nom du fichier |
| content_hash | String(64) | NULL | -- | Hash du contenu (indexed) |
| mode | String(20) | NULL | -- | express, import, assiste, demo |
| stats_json | Text | NULL | -- | Statistiques (JSON) |
| error_json | Text | NULL | -- | Erreurs (JSON) |

Relations : `sites` (1-N -> StagingSite), `compteurs` (1-N -> StagingCompteur), `findings` (1-N -> QualityFinding)

### `staging_sites`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| batch_id | Integer | NOT NULL | -- | FK -> staging_batches.id |
| row_number | Integer | NULL | -- | Ligne dans le fichier source |
| nom | String(200) | NOT NULL | -- | Nom du site |
| type_site | String(50) | NULL | -- | Type de site |
| adresse | String(300) | NULL | -- | Adresse |
| code_postal | String(10) | NULL | -- | Code postal |
| ville | String(100) | NULL | -- | Ville |
| surface_m2 | Float | NULL | -- | Surface m2 |
| siret | String(14) | NULL | -- | SIRET |
| naf_code | String(5) | NULL | -- | Code NAF |
| source_type | String(20) | NULL | -- | Source d'import |
| source_ref | String(200) | NULL | -- | Reference source |
| target_site_id | Integer | NULL | -- | Merge avec site existant |
| target_portefeuille_id | Integer | NULL | -- | Portefeuille cible |
| skip | Boolean | NOT NULL | False | Ignore par l'utilisateur |

### `staging_compteurs`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| batch_id | Integer | NOT NULL | -- | FK -> staging_batches.id |
| staging_site_id | Integer | NULL | -- | FK -> staging_sites.id |
| row_number | Integer | NULL | -- | Ligne fichier source |
| numero_serie | String(50) | NULL | -- | Numero de serie |
| meter_id | String(14) | NULL | -- | PRM/PDL/PCE |
| type_compteur | String(20) | NULL | -- | electricite, gaz, eau |
| puissance_kw | Float | NULL | -- | Puissance kW |
| target_site_id | Integer | NULL | -- | Site cible |
| target_compteur_id | Integer | NULL | -- | Merge avec compteur existant |
| skip | Boolean | NOT NULL | False | Ignore |

### `quality_findings`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| batch_id | Integer | NOT NULL | -- | FK -> staging_batches.id |
| rule_id | String(50) | NOT NULL | -- | Regle (dup_site, dup_meter, orphan_meter...) |
| severity | Enum(QualityRuleSeverity) | NOT NULL | -- | Severite |
| staging_site_id | Integer | NULL | -- | Site staging concerne |
| staging_compteur_id | Integer | NULL | -- | Compteur staging concerne |
| evidence_json | Text | NULL | -- | Evidence (JSON) |
| suggested_action | String(200) | NULL | -- | merge, skip, fix_address |
| resolved | Boolean | NOT NULL | False | Resolu |
| resolution | String(200) | NULL | -- | Description resolution |

### `activation_logs`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| batch_id | Integer | NOT NULL | -- | FK -> staging_batches.id |
| started_at | DateTime | NOT NULL | -- | Debut activation |
| completed_at | DateTime | NULL | -- | Fin activation |
| status | Enum(ActivationLogStatus) | NOT NULL | -- | Statut |
| error_message | Text | NULL | -- | Message d'erreur |
| sites_created | Integer | NOT NULL | 0 | Sites crees |
| compteurs_created | Integer | NOT NULL | 0 | Compteurs crees |
| activation_hash | String(64) | NULL | -- | Hash (indexed) |
| user_id | Integer | NULL | -- | Utilisateur |

### `delivery_points`

Mixins : TimestampMixin, SoftDeleteMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| code | String(14) | NOT NULL | -- | PRM ou PCE (14 digits, indexed) |
| energy_type | Enum(DeliveryPointEnergyType) | NULL | -- | elec (PRM) ou gaz (PCE) |
| site_id | Integer | NOT NULL | -- | FK -> sites.id |
| status | Enum(DeliveryPointStatus) | NOT NULL | ACTIVE | Statut |
| data_source | String(20) | NULL | -- | csv, manual, demo, api |
| data_source_ref | String(200) | NULL | -- | Batch ID / filename |
| imported_at | DateTime | NULL | -- | Date d'import |
| imported_by | Integer | NULL | -- | User ID importateur |

Relations : `site` (N-1 -> Site), `compteurs` (1-N -> Compteur)

---

## Compteurs & Consommation

### `compteurs`

Mixins : TimestampMixin, SoftDeleteMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| type | Enum(TypeCompteur) | NOT NULL | -- | Type de compteur |
| numero_serie | String(50) | NOT NULL | -- | Numero de serie (UNIQUE, indexed) |
| puissance_souscrite_kw | Float | NULL | -- | Puissance souscrite kW |
| meter_id | String(14) | NULL | -- | PRM/PDL/PCE (legacy) |
| energy_vector | Enum(EnergyVector) | NULL | -- | Vecteur energetique |
| actif | Boolean | NOT NULL | True | Compteur actif |
| delivery_point_id | Integer | NULL | -- | FK -> delivery_points.id (indexed) |
| data_source | String(20) | NULL | -- | csv, manual, demo, api |
| data_source_ref | String(200) | NULL | -- | Batch ID / filename |

Relations : `site` (N-1), `delivery_point` (N-1), `consommations` (1-N, dynamic)

### `consommations`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| compteur_id | Integer | NOT NULL | -- | FK -> compteurs.id (indexed) |
| timestamp | DateTime | NOT NULL | -- | Date/heure du releve (indexed) |
| valeur | Float | NOT NULL | -- | Valeur consommee (kWh, m3...) |
| cout_euro | Float | NULL | -- | Cout en euros |

Relations : `compteur` (N-1)

---

## Conformite / Compliance

### `obligations`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| type | Enum(TypeObligation) | NOT NULL | -- | Type d'obligation |
| description | String | NULL | -- | Description |
| echeance | Date | NULL | -- | Echeance reglementaire |
| statut | Enum(StatutConformite) | NOT NULL | A_RISQUE | Statut de conformite |
| avancement_pct | Float | NOT NULL | 0.0 | Avancement 0-100 |

Relations : `site` (N-1 -> Site)

### `evidences`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| type | Enum(TypeEvidence) | NOT NULL | -- | Type de preuve |
| statut | Enum(StatutEvidence) | NOT NULL | EN_ATTENTE | Statut |
| note | String | NULL | -- | Note |
| file_url | String | NULL | -- | URL du fichier |

Relations : `site` (N-1 backref)

### `usages`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| batiment_id | Integer | NOT NULL | -- | FK -> batiments.id |
| type | Enum(TypeUsage) | NOT NULL | -- | Type d'usage |
| description | String | NULL | -- | Description |

Relations : `batiment` (N-1 backref)

### `compliance_findings`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| regulation | String(50) | NOT NULL | -- | Pack reglementaire (indexed) |
| rule_id | String(100) | NOT NULL | -- | ID de la regle (DT_SCOPE, BACS_POWER...) |
| status | String(20) | NOT NULL | -- | OK, NOK, UNKNOWN, OUT_OF_SCOPE |
| severity | String(20) | NULL | -- | low, medium, high, critical |
| deadline | Date | NULL | -- | Echeance reglementaire |
| evidence | String(500) | NULL | -- | Explication humaine |
| recommended_actions_json | Text | NULL | -- | Actions recommandees (JSON) |
| insight_status | Enum(InsightStatus) | NOT NULL | OPEN | Statut workflow ops |
| owner | String(100) | NULL | -- | Responsable assigne |
| notes | Text | NULL | -- | Notes operateur |
| run_batch_id | Integer | NULL | -- | FK -> compliance_run_batches.id |
| inputs_json | Text | NULL | {} | Input data (JSON) |
| params_json | Text | NULL | {} | Params/seuils (JSON) |
| evidence_json | Text | NULL | {} | Evidence references (JSON) |
| engine_version | String(64) | NULL | -- | Version hash du moteur |

Relations : `site` (N-1 backref), `run_batch` (N-1 backref)

### `compliance_run_batches`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| org_id | Integer | NULL | -- | FK -> organisations.id |
| triggered_by | String(100) | NULL | -- | Declencheur : api, auto, manual |
| started_at | DateTime | NULL | -- | Debut du run |
| completed_at | DateTime | NULL | -- | Fin du run |
| sites_count | Integer | NOT NULL | 0 | Nombre de sites evalues |
| findings_count | Integer | NOT NULL | 0 | Findings totaux |
| nok_count | Integer | NOT NULL | 0 | Findings NOK |
| unknown_count | Integer | NOT NULL | 0 | Findings UNKNOWN |

Relations : `organisation` (N-1 backref), `findings` (1-N backref)

---

## BACS Expert

### `bacs_assets`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| building_id | Integer | NULL | -- | FK -> batiments.id (indexed) |
| is_tertiary_non_residential | Boolean | NOT NULL | True | Critere d'eligibilite |
| pc_date | Date | NULL | -- | Date du permis de construire |
| renewal_events_json | Text | NULL | [] | Evenements renouvellement (JSON) |
| responsible_party_json | Text | NULL | {} | Responsable (JSON) |

Relations : `site` (N-1 backref), `building` (N-1 backref), `cvc_systems` (1-N), `assessments` (1-N), `inspections` (1-N)

### `bacs_cvc_systems`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| asset_id | Integer | NOT NULL | -- | FK -> bacs_assets.id (CASCADE, indexed) |
| system_type | Enum(CvcSystemType) | NOT NULL | -- | heating, cooling, ventilation |
| architecture | Enum(CvcArchitecture) | NOT NULL | -- | cascade, network, independent |
| units_json | Text | NOT NULL | [] | Unites CVC (JSON) |
| putile_kw_computed | Float | NULL | -- | Puissance utile calculee kW |
| putile_calc_trace_json | Text | NULL | -- | Trace audit calcul (JSON) |
| inputs_json | Text | NULL | {} | Input data (JSON) |
| params_json | Text | NULL | {} | Params (JSON) |
| engine_version | String(64) | NULL | -- | Version moteur |

Relations : `asset` (N-1 -> BacsAsset)

### `bacs_assessments`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| asset_id | Integer | NOT NULL | -- | FK -> bacs_assets.id (CASCADE, indexed) |
| assessed_at | DateTime | NOT NULL | -- | Date/heure evaluation |
| threshold_applied | Integer | NULL | -- | Seuil: 70 ou 290 kW |
| is_obligated | Boolean | NOT NULL | False | Site assujetti au decret |
| deadline_date | Date | NULL | -- | Echeance reglementaire |
| trigger_reason | Enum(BacsTriggerReason) | NULL | -- | Raison declenchante |
| tri_exemption_possible | Boolean | NULL | -- | Exemption TRI > 10 ans |
| tri_years | Float | NULL | -- | TRI en annees |
| confidence_score | Float | NULL | -- | Score confiance 0-1 |
| compliance_score | Float | NULL | -- | Score conformite 0-100 |
| findings_json | Text | NULL | -- | Findings detailles (JSON) |
| rule_id | String(100) | NULL | -- | Rule ID (BACS_V2_*) |
| inputs_json | Text | NULL | {} | Input data (JSON) |
| params_json | Text | NULL | {} | Params (JSON) |
| evidence_json | Text | NULL | {} | Evidence references (JSON) |
| engine_version | String(64) | NULL | -- | Version moteur |

Relations : `asset` (N-1 -> BacsAsset)

### `bacs_inspections`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| asset_id | Integer | NOT NULL | -- | FK -> bacs_assets.id (CASCADE, indexed) |
| inspection_date | Date | NULL | -- | Date de l'inspection |
| due_next_date | Date | NULL | -- | Prochaine inspection (periodicite 5 ans) |
| report_ref | String(255) | NULL | -- | Reference du rapport |
| status | Enum(InspectionStatus) | NOT NULL | SCHEDULED | Statut |

Relations : `asset` (N-1 -> BacsAsset)

---

## Bill Intelligence

### `energy_contracts`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| energy_type | Enum(BillingEnergyType) | NOT NULL | -- | elec / gaz |
| supplier_name | String(200) | NOT NULL | -- | Nom fournisseur |
| start_date | Date | NULL | -- | Debut contrat |
| end_date | Date | NULL | -- | Fin contrat |
| price_ref_eur_per_kwh | Float | NULL | -- | Prix ref EUR HT/kWh |
| fixed_fee_eur_per_month | Float | NULL | -- | Abonnement mensuel EUR HT |
| metadata_json | Text | NULL | -- | Metadata libre (JSON) |
| notice_period_days | Integer | NOT NULL | 90 | Preavis resiliation (jours) |
| auto_renew | Boolean | NOT NULL | False | Reconduction tacite |

Relations : `site` (N-1 backref), `invoices` (1-N -> EnergyInvoice)

### `energy_invoices`

Mixins : TimestampMixin. Contrainte UNIQUE : (site_id, invoice_number, period_start, period_end)

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| contract_id | Integer | NULL | -- | FK -> energy_contracts.id (indexed) |
| invoice_number | String(100) | NOT NULL | -- | Numero facture (indexed) |
| period_start | Date | NULL | -- | Debut periode facturee |
| period_end | Date | NULL | -- | Fin periode facturee |
| issue_date | Date | NULL | -- | Date d'emission |
| total_eur | Float | NULL | -- | Montant total EUR TTC |
| energy_kwh | Float | NULL | -- | Consommation kWh |
| status | Enum(BillingInvoiceStatus) | NOT NULL | IMPORTED | Statut facture |
| source | String(50) | NULL | -- | Source : csv, json, pdf, manual |
| raw_json | Text | NULL | -- | Donnees brutes (JSON) |

Relations : `site` (N-1 backref), `contract` (N-1), `lines` (1-N -> EnergyInvoiceLine)

### `energy_invoice_lines`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| invoice_id | Integer | NOT NULL | -- | FK -> energy_invoices.id (indexed) |
| line_type | Enum(InvoiceLineType) | NOT NULL | -- | energy/network/tax/other |
| label | String(300) | NOT NULL | -- | Libelle |
| qty | Float | NULL | -- | Quantite |
| unit | String(20) | NULL | -- | Unite (kWh, kVA, mois...) |
| unit_price | Float | NULL | -- | Prix unitaire EUR |
| amount_eur | Float | NULL | -- | Montant EUR |
| meta_json | Text | NULL | -- | Metadata (JSON) |

Relations : `invoice` (N-1), `allocations` (1-N backref -> ConceptAllocation)

### `concept_allocations`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| invoice_line_id | Integer | NOT NULL | -- | FK -> energy_invoice_lines.id (indexed) |
| concept_id | String(50) | NOT NULL | -- | Concept (fourniture, acheminement, taxes...) (indexed) |
| confidence | Float | NOT NULL | 1.0 | Confiance allocation 0-1 |
| matched_rules_json | Text | NULL | -- | Regles d'allocation (JSON) |

Relations : `line` (N-1 backref)

### `billing_insights`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| invoice_id | Integer | NULL | -- | FK -> energy_invoices.id (indexed) |
| type | String(50) | NOT NULL | -- | Type d'insight (indexed) |
| severity | String(20) | NOT NULL | medium | low, medium, high, critical |
| message | String(500) | NOT NULL | -- | Description humaine |
| metrics_json | Text | NULL | -- | Metriques (JSON) |
| estimated_loss_eur | Float | NULL | -- | Perte estimee EUR |
| recommended_actions_json | Text | NULL | -- | Actions recommandees (JSON) |
| insight_status | Enum(InsightStatus) | NOT NULL | OPEN | Statut workflow |
| owner | String(100) | NULL | -- | Responsable assigne |
| notes | Text | NULL | -- | Notes operateur |

Relations : `site` (N-1 backref), `invoice` (N-1 backref)

### `billing_import_batches`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| org_id | Integer | NULL | -- | Organisation (indexed) |
| filename | String(500) | NULL | -- | Nom du fichier |
| content_hash | String(64) | NOT NULL | -- | SHA-256 contenu (indexed) |
| imported_at | DateTime | NOT NULL | utcnow | Date d'import |
| rows_total | Integer | NOT NULL | 0 | Total lignes |
| rows_inserted | Integer | NOT NULL | 0 | Lignes inserees |
| rows_skipped | Integer | NOT NULL | 0 | Lignes ignorees |
| errors_json | Text | NULL | -- | Erreurs (JSON) |

---

## Achat Energie

### `purchase_assumption_sets`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| energy_type | Enum(BillingEnergyType) | NOT NULL | ELEC | elec/gaz |
| volume_kwh_an | Float | NOT NULL | 0 | Conso annuelle estimee kWh |
| profile_factor | Float | NOT NULL | 1.0 | Facteur de profil P/Pmoy |
| horizon_months | Integer | NOT NULL | 24 | Duree contrat simule (mois) |
| assumptions_json | Text | NULL | -- | Hypotheses libres (JSON) |
| created_at | DateTime | NOT NULL | utcnow | Date creation |

Relations : `site` (N-1 backref), `scenario_results` (1-N)

### `purchase_preferences`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| org_id | Integer | NULL | -- | Organisation (indexed) |
| risk_tolerance | String(20) | NOT NULL | medium | low, medium, high |
| budget_priority | Float | NOT NULL | 0.5 | Poids prix vs risque (0-1) |
| green_preference | Boolean | NOT NULL | False | Preference offre verte |
| updated_at | DateTime | NOT NULL | utcnow | Derniere MAJ |

### `purchase_scenario_results`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| run_id | String(36) | NULL | -- | UUID du run (indexed) |
| batch_id | String(36) | NULL | -- | UUID batch portfolio (indexed) |
| inputs_hash | String(64) | NULL | -- | SHA-256 hypotheses |
| assumption_set_id | Integer | NOT NULL | -- | FK -> purchase_assumption_sets.id (indexed) |
| strategy | Enum(PurchaseStrategy) | NOT NULL | -- | fixe, indexe, spot |
| price_eur_per_kwh | Float | NOT NULL | -- | Prix moyen EUR HT/kWh |
| total_annual_eur | Float | NOT NULL | -- | Cout annuel EUR HT |
| risk_score | Float | NOT NULL | 50 | Score risque 0-100 |
| savings_vs_current_pct | Float | NULL | -- | Economies vs actuel (%) |
| p10_eur | Float | NULL | -- | Borne basse P10 EUR |
| p90_eur | Float | NULL | -- | Borne haute P90 EUR |
| detail_json | Text | NULL | -- | Breakdown mensuel (JSON) |
| is_recommended | Boolean | NOT NULL | False | Scenario recommande |
| reco_status | Enum(PurchaseRecoStatus) | NOT NULL | DRAFT | Statut recommandation |
| computed_at | DateTime | NOT NULL | utcnow | Date du calcul |

Relations : `assumption_set` (N-1)

---

## Energy Models / Analytics

### `meter`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| meter_id | String(50) | NOT NULL | -- | PRM/PDL (UNIQUE, indexed) |
| name | String(200) | NOT NULL | -- | Nom du compteur |
| energy_vector | Enum(EnergyVector) | NOT NULL | ELECTRICITY | Vecteur energetique |
| site_id | Integer | NOT NULL | -- | FK -> sites.id |
| subscribed_power_kva | Float | NULL | -- | Puissance souscrite kVA |
| tariff_type | String(50) | NULL | -- | Type tarif (C5, TURPE...) |
| installation_date | DateTime | NULL | -- | Date d'installation |
| is_active | Boolean | NOT NULL | True | Actif |
| notes | Text | NULL | -- | Notes |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| updated_at | DateTime | NOT NULL | utcnow | Derniere MAJ |

Relations : `site` (N-1), `readings` (1-N), `profiles` (1-N), `anomalies` (1-N), `recommendations` (1-N)

### `meter_reading`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| meter_id | Integer | NOT NULL | -- | FK -> meter.id (indexed) |
| timestamp | DateTime | NOT NULL | -- | Date/heure (indexed) |
| frequency | Enum(FrequencyType) | NOT NULL | HOURLY | Frequence |
| value_kwh | Float | NOT NULL | -- | Valeur kWh |
| is_estimated | Boolean | NOT NULL | False | Valeur estimee |
| quality_score | Float | NULL | -- | Score qualite 0-1 |
| import_job_id | Integer | NULL | -- | FK -> data_import_job.id |
| created_at | DateTime | NOT NULL | utcnow | Creation |

Enums locaux : `FrequencyType` (15min, 30min, hourly, daily, monthly)

### `data_import_job`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| job_type | String(50) | NOT NULL | consumption_import | Type de job |
| status | Enum(ImportStatus) | NOT NULL | PENDING | Statut |
| filename | String(500) | NULL | -- | Nom du fichier |
| file_format | String(20) | NULL | -- | csv, xlsx, json |
| file_size_bytes | Integer | NULL | -- | Taille fichier |
| file_hash | String(64) | NULL | -- | SHA256 dedup |
| site_id | Integer | NULL | -- | FK -> sites.id |
| meter_id | Integer | NULL | -- | FK -> meter.id |
| rows_total | Integer | NULL | -- | Total lignes |
| rows_imported | Integer | NULL | -- | Lignes importees |
| rows_skipped | Integer | NULL | -- | Lignes ignorees |
| rows_errored | Integer | NULL | -- | Lignes en erreur |
| date_start | DateTime | NULL | -- | Debut plage importee |
| date_end | DateTime | NULL | -- | Fin plage importee |
| error_message | Text | NULL | -- | Message d'erreur |
| error_details_json | JSON | NULL | -- | Erreurs detaillees (JSON) |
| created_by | String(200) | NULL | -- | Utilisateur/systeme |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| started_at | DateTime | NULL | -- | Debut traitement |
| completed_at | DateTime | NULL | -- | Fin traitement |

Enums locaux : `ImportStatus` (pending, processing, completed, failed, partially_completed)

### `usage_profile`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| meter_id | Integer | NOT NULL | -- | FK -> meter.id (indexed) |
| period_start | DateTime | NOT NULL | -- | Debut periode analyse |
| period_end | DateTime | NOT NULL | -- | Fin periode |
| archetype_id | Integer | NULL | -- | FK -> kb_archetype.id |
| archetype_code | String(100) | NULL | -- | Code archetype matche |
| archetype_match_score | Float | NULL | -- | Score match 0-1 |
| features_json | JSON | NULL | -- | Metriques calculees (JSON) |
| temporal_patterns_json | JSON | NULL | -- | Patterns temporels (JSON) |
| kb_version_id | Integer | NULL | -- | FK -> kb_version.id |
| analysis_version | String(50) | NULL | -- | Version engine analytics |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| updated_at | DateTime | NOT NULL | utcnow | Derniere MAJ |

### `anomaly`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| meter_id | Integer | NOT NULL | -- | FK -> meter.id (indexed) |
| anomaly_code | String(100) | NOT NULL | -- | Code anomalie (indexed) |
| title | String(200) | NOT NULL | -- | Titre |
| description | Text | NULL | -- | Description |
| severity | Enum(AnomalySeverity) | NOT NULL | MEDIUM | Severite |
| confidence | Float | NOT NULL | 0.8 | Confiance 0-1 |
| detected_at | DateTime | NOT NULL | utcnow | Date detection |
| period_start | DateTime | NULL | -- | Debut periode |
| period_end | DateTime | NULL | -- | Fin periode |
| measured_value | Float | NULL | -- | Valeur mesuree |
| threshold_value | Float | NULL | -- | Valeur seuil |
| deviation_pct | Float | NULL | -- | Ecart % |
| kb_rule_id | Integer | NULL | -- | FK -> kb_anomaly_rule.id |
| kb_version_id | Integer | NULL | -- | FK -> kb_version.id |
| explanation_json | JSON | NULL | -- | Explication detaillee (JSON) |
| is_active | Boolean | NOT NULL | True | Active |
| is_reviewed | Boolean | NOT NULL | False | Revue |
| reviewed_at | DateTime | NULL | -- | Date revue |
| reviewed_by | String(200) | NULL | -- | Revu par |
| review_note | Text | NULL | -- | Note de revue |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| updated_at | DateTime | NOT NULL | utcnow | Derniere MAJ |

Enums locaux : `AnomalySeverity` (low, medium, high, critical)

### `recommendation`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| meter_id | Integer | NOT NULL | -- | FK -> meter.id (indexed) |
| recommendation_code | String(100) | NOT NULL | -- | Code recommandation (indexed) |
| title | String(200) | NOT NULL | -- | Titre |
| description | Text | NULL | -- | Description |
| triggered_by_anomaly_id | Integer | NULL | -- | FK -> anomaly.id |
| estimated_savings_kwh_year | Float | NULL | -- | Economies kWh/an |
| estimated_savings_eur_year | Float | NULL | -- | Economies EUR/an |
| estimated_savings_pct | Float | NULL | -- | Economies % |
| impact_score | Integer | NULL | -- | ICE: Impact (1-10) |
| confidence_score | Integer | NULL | -- | ICE: Confiance (1-10) |
| ease_score | Integer | NULL | -- | ICE: Facilite (1-10) |
| ice_score | Float | NULL | -- | Score ICE calcule |
| priority_rank | Integer | NULL | -- | Rang de priorite |
| kb_recommendation_id | Integer | NULL | -- | FK -> kb_recommendation.id |
| kb_version_id | Integer | NULL | -- | FK -> kb_version.id |
| action_plan_json | JSON | NULL | -- | Plan d'action (JSON) |
| status | Enum(RecommendationStatus) | NOT NULL | PENDING | Statut lifecycle |
| is_reviewed | Boolean | NOT NULL | False | Revue |
| reviewed_at | DateTime | NULL | -- | Date revue |
| reviewed_by | String(200) | NULL | -- | Revu par |
| review_note | Text | NULL | -- | Note de revue |
| implementation_started_at | DateTime | NULL | -- | Debut implementation |
| implementation_completed_at | DateTime | NULL | -- | Fin implementation |
| actual_savings_kwh_year | Float | NULL | -- | Economies reelles kWh/an |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| updated_at | DateTime | NOT NULL | utcnow | Derniere MAJ |

Enums locaux : `RecommendationStatus` (pending, in_progress, completed, dismissed)

---

## Monitoring / Alertes

### `monitoring_snapshot`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| meter_id | Integer | NULL | -- | FK -> meter.id (indexed) |
| period_start | DateTime | NOT NULL | -- | Debut periode |
| period_end | DateTime | NOT NULL | -- | Fin periode |
| kpis_json | JSON | NULL | -- | KPIs: pmax, p95, load_factor... (JSON) |
| data_quality_score | Float | NULL | -- | Score qualite 0-100 |
| risk_power_score | Float | NULL | -- | Score risque puissance 0-100 |
| data_quality_details_json | JSON | NULL | -- | Details qualite (JSON) |
| risk_power_details_json | JSON | NULL | -- | Details risque (JSON) |
| engine_version | String(50) | NULL | -- | Version engine |
| created_at | DateTime | NOT NULL | utcnow | Creation |

### `monitoring_alert`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| meter_id | Integer | NULL | -- | FK -> meter.id (indexed) |
| alert_type | String(100) | NOT NULL | -- | Type d'alerte (indexed) |
| severity | Enum(AlertSeverity) | NOT NULL | WARNING | Severite |
| start_ts | DateTime | NULL | -- | Debut fenetre |
| end_ts | DateTime | NULL | -- | Fin fenetre |
| evidence_json | JSON | NULL | -- | Evidence (JSON) |
| explanation | Text | NOT NULL | -- | Explication |
| recommended_action | Text | NULL | -- | Action recommandee |
| estimated_impact_kwh | Float | NULL | -- | Impact kWh |
| estimated_impact_eur | Float | NULL | -- | Impact EUR |
| kb_link_json | JSON | NULL | -- | Lien KB (JSON) |
| status | Enum(AlertStatus) | NOT NULL | OPEN | Statut (indexed) |
| acknowledged_at | DateTime | NULL | -- | Date acquittement |
| acknowledged_by | String(200) | NULL | -- | Acquitte par |
| resolved_at | DateTime | NULL | -- | Date resolution |
| resolved_by | String(200) | NULL | -- | Resolu par |
| resolution_note | Text | NULL | -- | Note resolution |
| snapshot_id | Integer | NULL | -- | FK -> monitoring_snapshot.id |
| created_at | DateTime | NOT NULL | utcnow | Creation (indexed) |
| updated_at | DateTime | NOT NULL | utcnow | Derniere MAJ |

Enums locaux : `AlertStatus` (open, ack, resolved), `AlertSeverity` (info, warning, high, critical)

### `alertes` (legacy)

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| severite | Enum(SeveriteAlerte) | NOT NULL | -- | Severite (indexed) |
| titre | String(200) | NOT NULL | -- | Titre |
| description | Text | NULL | -- | Description detaillee |
| timestamp | DateTime | NOT NULL | -- | Date/heure (indexed) |
| resolue | Boolean | NOT NULL | False | Resolue |
| date_resolution | DateTime | NULL | -- | Date resolution |

Relations : `site` (N-1 -> Site)

---

## Consumption Insights & Targets

### `consumption_insights`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| meter_id | Integer | NULL | -- | FK -> meter.id (indexed) |
| type | String(50) | NOT NULL | -- | hors_horaires, base_load, pointe, derive, data_gap (indexed) |
| severity | String(20) | NOT NULL | medium | low, medium, high, critical |
| message | String(500) | NOT NULL | -- | Description humaine |
| metrics_json | Text | NULL | -- | Metriques (JSON) |
| estimated_loss_kwh | Float | NULL | -- | Perte estimee kWh/an |
| estimated_loss_eur | Float | NULL | -- | Perte estimee EUR/an |
| recommended_actions_json | Text | NULL | -- | Actions (JSON) |
| period_start | DateTime | NULL | -- | Debut periode |
| period_end | DateTime | NULL | -- | Fin periode |
| insight_status | Enum(InsightStatus) | NOT NULL | OPEN | Statut workflow |

Relations : `site` (N-1 backref)

### `consumption_targets`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| energy_type | String(20) | NOT NULL | electricity | electricity, gas |
| period | String(10) | NOT NULL | -- | monthly, yearly |
| year | Integer | NOT NULL | -- | Annee |
| month | Integer | NULL | -- | Mois 1-12 (NULL = yearly) |
| target_kwh | Float | NULL | -- | Objectif kWh |
| target_eur | Float | NULL | -- | Objectif EUR |
| target_co2e_kg | Float | NULL | -- | Objectif CO2e kg |
| actual_kwh | Float | NULL | -- | Reel kWh |
| actual_eur | Float | NULL | -- | Reel EUR |
| actual_co2e_kg | Float | NULL | -- | Reel CO2e kg |
| source | String(50) | NULL | manual | manual, import, forecast |
| notes | Text | NULL | -- | Notes |

---

## Action Hub

### `action_items`

Mixins : TimestampMixin. Contrainte UNIQUE : (org_id, source_type, source_id, source_key)

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| org_id | Integer | NOT NULL | -- | FK -> organisations.id (indexed) |
| site_id | Integer | NULL | -- | FK -> sites.id (indexed) |
| source_type | Enum(ActionSourceType) | NOT NULL | -- | Brique source (indexed) |
| source_id | String(100) | NOT NULL | -- | ID objet source |
| source_key | String(200) | NOT NULL | -- | Cle dedup intra-source |
| title | String(500) | NOT NULL | -- | Titre |
| rationale | Text | NULL | -- | Justification |
| priority | Integer | NOT NULL | 3 | Priorite 1 (critique) a 5 (faible) |
| severity | String(20) | NULL | -- | low, medium, high, critical |
| estimated_gain_eur | Float | NULL | -- | Gain estime EUR |
| due_date | Date | NULL | -- | Echeance |
| status | Enum(ActionStatus) | NOT NULL | OPEN | Statut workflow |
| owner | String(100) | NULL | -- | Responsable assigne |
| notes | Text | NULL | -- | Notes operateur |
| inputs_hash | String(64) | NULL | -- | SHA-256 contenu source |
| category | String(50) | NULL | -- | conformite, energie, maintenance, finance |
| description | Text | NULL | -- | Description detaillee |
| realized_gain_eur | Float | NULL | -- | Gain realise EUR |
| realized_at | Date | NULL | -- | Date constatation gain |
| closed_at | DateTime | NULL | -- | Date fermeture |
| idempotency_key | String(64) | NULL | -- | Cle idempotence (UNIQUE, indexed) |
| co2e_savings_est_kg | Float | NULL | -- | Economies CO2e estimees kg |

Relations : `organisation` (N-1 backref), `site` (N-1 backref), `events` (1-N backref), `comments` (1-N backref), `evidence_items` (1-N backref)

### `action_events`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| action_id | Integer | NOT NULL | -- | FK -> action_items.id (indexed) |
| event_type | String(50) | NOT NULL | -- | created, status_change, assigned, etc. |
| actor | String(200) | NULL | -- | Utilisateur declencheur |
| old_value | String(500) | NULL | -- | Ancienne valeur |
| new_value | String(500) | NULL | -- | Nouvelle valeur |
| metadata_json | Text | NULL | -- | Contexte additionnel (JSON) |

### `action_comments`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| action_id | Integer | NOT NULL | -- | FK -> action_items.id (indexed) |
| author | String(200) | NOT NULL | -- | Auteur |
| body | Text | NOT NULL | -- | Contenu |

### `action_evidence`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| action_id | Integer | NOT NULL | -- | FK -> action_items.id (indexed) |
| label | String(300) | NOT NULL | -- | Libelle de la piece |
| file_url | String(1000) | NULL | -- | URL / chemin reference |
| mime_type | String(100) | NULL | -- | Type MIME |
| uploaded_by | String(200) | NULL | -- | Utilisateur |

### `action_sync_batches`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| org_id | Integer | NULL | -- | FK -> organisations.id (indexed) |
| triggered_by | String(100) | NULL | -- | Declencheur : api, seed, auto |
| inputs_hash | String(64) | NULL | -- | Hash global idempotence |
| started_at | DateTime | NULL | -- | Debut |
| finished_at | DateTime | NULL | -- | Fin |
| created_count | Integer | NOT NULL | 0 | Actions creees |
| updated_count | Integer | NOT NULL | 0 | Actions mises a jour |
| skipped_count | Integer | NOT NULL | 0 | Actions ignorees |
| closed_count | Integer | NOT NULL | 0 | Actions auto-fermees |
| warnings_json | Text | NULL | -- | Warnings (JSON) |

---

## Notifications

### `notification_events`

Mixins : TimestampMixin. Contrainte UNIQUE : (org_id, source_type, source_id, source_key)

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| org_id | Integer | NOT NULL | -- | FK -> organisations.id (indexed) |
| site_id | Integer | NULL | -- | FK -> sites.id (indexed) |
| source_type | Enum(NotificationSourceType) | NOT NULL | -- | Brique source (indexed) |
| source_id | String(100) | NULL | -- | ID objet source |
| source_key | String(200) | NULL | -- | Cle dedup intra-source |
| severity | Enum(NotificationSeverity) | NOT NULL | -- | Severite (indexed) |
| title | String(500) | NOT NULL | -- | Titre |
| message | Text | NULL | -- | Description detaillee |
| due_date | Date | NULL | -- | Echeance |
| estimated_impact_eur | Float | NULL | -- | Impact financier EUR |
| deeplink_path | String(500) | NULL | -- | Chemin deep-link frontend |
| evidence_json | Text | NULL | -- | Inputs + seuils (JSON) |
| status | Enum(NotificationStatus) | NOT NULL | NEW | Statut lifecycle (indexed) |
| inputs_hash | String(64) | NULL | -- | SHA-256 dedup (indexed) |

### `notification_batches`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| org_id | Integer | NULL | -- | FK -> organisations.id (indexed) |
| triggered_by | String(100) | NULL | -- | Declencheur |
| inputs_hash | String(64) | NULL | -- | Hash global idempotence |
| started_at | DateTime | NULL | -- | Debut |
| finished_at | DateTime | NULL | -- | Fin |
| created_count | Integer | NOT NULL | 0 | Creees |
| updated_count | Integer | NOT NULL | 0 | Mises a jour |
| skipped_count | Integer | NOT NULL | 0 | Ignorees |
| warnings_json | Text | NULL | -- | Warnings (JSON) |

### `notification_preferences`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| org_id | Integer | NOT NULL | -- | FK -> organisations.id (UNIQUE, indexed, 1:1) |
| enable_badges | Boolean | NOT NULL | True | Afficher badges NEW |
| snooze_days | Integer | NOT NULL | 0 | Jours de snooze global |
| thresholds_json | Text | NULL | -- | Seuils (JSON) |

---

## RegOps / Infrastructure

### `reg_assessments`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| object_type | String(20) | NOT NULL | -- | Type d'objet (indexed) |
| object_id | Integer | NOT NULL | -- | ID objet (indexed) |
| computed_at | DateTime | NOT NULL | utcnow | Date de calcul |
| global_status | Enum(RegStatus) | NOT NULL | -- | Statut global |
| compliance_score | Float | NOT NULL | 0.0 | Score conformite |
| next_deadline | Date | NULL | -- | Prochaine echeance |
| findings_json | Text | NULL | -- | Findings (JSON) |
| top_actions_json | Text | NULL | -- | Actions top (JSON) |
| missing_data_json | Text | NULL | -- | Donnees manquantes (JSON) |
| deterministic_version | String(64) | NOT NULL | -- | Version deterministe |
| ai_version | String(64) | NULL | -- | Version IA |
| data_version | String(64) | NOT NULL | -- | Version donnees |
| is_stale | Boolean | NOT NULL | False | Cache perime |
| stale_reason | String(200) | NULL | -- | Raison perimee |

### `job_outbox`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| job_type | Enum(JobType) | NOT NULL | -- | Type de job (indexed) |
| payload_json | Text | NULL | -- | Payload (JSON) |
| priority | Integer | NOT NULL | 0 | Priorite |
| status | Enum(JobStatus) | NOT NULL | PENDING | Statut (indexed) |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| started_at | DateTime | NULL | -- | Debut |
| finished_at | DateTime | NULL | -- | Fin |
| error | Text | NULL | -- | Message d'erreur |

### `datapoints`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| object_type | String(20) | NOT NULL | -- | Type d'objet (indexed) |
| object_id | Integer | NOT NULL | -- | ID objet (indexed) |
| metric | String(50) | NOT NULL | -- | Metrique (indexed) |
| ts_start | DateTime | NOT NULL | -- | Debut periode |
| ts_end | DateTime | NOT NULL | -- | Fin periode |
| value | Float | NOT NULL | -- | Valeur |
| unit | String(20) | NOT NULL | -- | Unite |
| source_type | Enum(SourceType) | NOT NULL | -- | Source |
| source_name | String(50) | NOT NULL | -- | Nom source |
| quality_score | Float | NOT NULL | 1.0 | Score qualite |
| coverage_ratio | Float | NOT NULL | 1.0 | Ratio couverture |
| retrieved_at | DateTime | NOT NULL | -- | Date de recuperation |
| source_ref | String(500) | NULL | -- | Reference source |

### `ai_insights`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| object_type | String(20) | NOT NULL | -- | Type d'objet (indexed) |
| object_id | Integer | NOT NULL | -- | ID objet (indexed) |
| insight_type | Enum(InsightType) | NOT NULL | -- | Type d'insight (indexed) |
| content_json | Text | NOT NULL | -- | Contenu (JSON) |
| ai_version | String(64) | NOT NULL | -- | Version IA |
| sources_used_json | Text | NULL | -- | Sources utilisees (JSON) |

### `reg_source_events`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| source_name | String(50) | NOT NULL | -- | Nom source (indexed) |
| title | String(500) | NOT NULL | -- | Titre |
| url | String(1000) | NULL | -- | URL |
| content_hash | String(64) | NOT NULL | -- | Hash contenu (UNIQUE, indexed) |
| snippet | String(500) | NULL | -- | Extrait |
| tags | String(200) | NULL | -- | Tags |
| published_at | DateTime | NULL | -- | Date publication |
| retrieved_at | DateTime | NOT NULL | utcnow | Date recuperation |
| reviewed | Boolean | NOT NULL | False | Revu (legacy) |
| review_note | String(500) | NULL | -- | Note revue |
| status | Enum(WatcherEventStatus) | NULL | NEW | Statut pipeline |
| dedup_key | String(128) | NULL | -- | Cle dedup (UNIQUE, indexed) |
| diff_summary | Text | NULL | -- | Resume des differences |
| applied_at | DateTime | NULL | -- | Date d'application |
| reviewed_at | DateTime | NULL | -- | Date de revue |
| reviewed_by | String(100) | NULL | -- | Revu par |

---

## Segmentation

### `segmentation_profiles`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| organisation_id | Integer | NOT NULL | -- | FK -> organisations.id (UNIQUE, indexed, 1:1) |
| typologie | String(50) | NOT NULL | -- | Segment detecte (Typologie enum) |
| naf_code | String(10) | NULL | -- | Code NAF principal |
| confidence_score | Float | NOT NULL | 0.0 | Score confiance 0-100 |
| answers_json | Text | NULL | -- | Reponses questionnaire (JSON) |
| reasons_json | Text | NULL | -- | Raisons detection (JSON) |

Relations : `organisation` (1-1 backref)

---

## Smart Intake

### `intake_sessions`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NULL | -- | FK -> sites.id (indexed) |
| org_id | Integer | NULL | -- | FK -> organisations.id |
| scope_type | String(10) | NOT NULL | -- | site, entity, org |
| scope_id | Integer | NOT NULL | -- | ID du scope |
| status | Enum(IntakeSessionStatus) | NOT NULL | DRAFT | Statut session |
| mode | Enum(IntakeMode) | NOT NULL | WIZARD | Mode d'intake |
| user_id | Integer | NULL | -- | FK -> users.id |
| score_before | Float | NULL | -- | Score compliance avant |
| score_after | Float | NULL | -- | Score compliance apres |
| questions_count | Integer | NOT NULL | 0 | Nombre questions |
| answers_count | Integer | NOT NULL | 0 | Nombre reponses |
| started_at | DateTime | NULL | -- | Debut session |
| completed_at | DateTime | NULL | -- | Fin session |

### `intake_answers`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| session_id | Integer | NOT NULL | -- | FK -> intake_sessions.id (indexed) |
| field_path | String(100) | NOT NULL | -- | Chemin du champ (site.tertiaire_area_m2) |
| value_json | Text | NOT NULL | -- | Valeur reponse (JSON) |
| source | Enum(IntakeSource) | NOT NULL | USER | Source de la reponse |
| confidence | String(10) | NOT NULL | high | high, medium, low |
| previous_value_json | Text | NULL | -- | Valeur precedente (diff) |
| applied_at | DateTime | NULL | -- | Date d'ecriture au modele final |

### `intake_field_overrides`

Mixins : TimestampMixin. Contrainte UNIQUE : (scope_type, scope_id, field_path)

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| scope_type | String(10) | NOT NULL | -- | org, entity, site |
| scope_id | Integer | NOT NULL | -- | ID scope (indexed) |
| field_path | String(100) | NOT NULL | -- | Chemin du champ |
| value_json | Text | NOT NULL | -- | Valeur (JSON) |
| source | String(20) | NULL | -- | Source |
| created_by | Integer | NULL | -- | FK -> users.id |

---

## Knowledge Base

### `kb_version`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| doc_id | String(100) | NOT NULL | -- | ID document (UNIQUE, indexed) |
| version | String(20) | NOT NULL | -- | Version |
| date | String(10) | NOT NULL | -- | Date YYYY-MM-DD |
| source_path | String(500) | NOT NULL | -- | Chemin source |
| source_sha256 | String(64) | NOT NULL | -- | SHA256 (UNIQUE, indexed) |
| author | String(200) | NULL | -- | Auteur |
| description | Text | NULL | -- | Description |
| status | Enum(KBStatus) | NOT NULL | VALIDATED | Statut |
| is_active | Boolean | NOT NULL | True | Actif |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| updated_at | DateTime | NOT NULL | utcnow | MAJ |

Enums locaux : `KBStatus` (draft, validated, deprecated), `KBConfidence` (high, medium, low)

### `kb_archetype`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| code | String(100) | NOT NULL | -- | Code archetype (UNIQUE, indexed) |
| title | String(200) | NOT NULL | -- | Titre |
| description | Text | NULL | -- | Description |
| kwh_m2_min | Integer | NULL | -- | Conso min kWh/m2 |
| kwh_m2_max | Integer | NULL | -- | Conso max kWh/m2 |
| kwh_m2_avg | Integer | NULL | -- | Conso moy kWh/m2 |
| usage_breakdown_json | JSON | NULL | -- | Repartition usages (JSON) |
| temporal_signature_json | JSON | NULL | -- | Signature temporelle (JSON) |
| segment_tags | JSON | NULL | -- | Tags segments (JSON) |
| kb_item_id | String(200) | NULL | -- | Ref YAML item ID |
| kb_version_id | Integer | NULL | -- | FK -> kb_version.id |
| source_section | String(200) | NULL | -- | Section source |
| confidence | Enum(KBConfidence) | NOT NULL | MEDIUM | Confiance |
| status | Enum(KBStatus) | NOT NULL | VALIDATED | Statut |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| updated_at | DateTime | NOT NULL | utcnow | MAJ |

### `kb_mapping_code`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| naf_code | String(10) | NOT NULL | -- | Code NAF (indexed) |
| archetype_id | Integer | NOT NULL | -- | FK -> kb_archetype.id |
| confidence | Enum(KBConfidence) | NOT NULL | HIGH | Confiance |
| priority | Integer | NOT NULL | 1 | Priorite multi-match |
| kb_version_id | Integer | NULL | -- | FK -> kb_version.id |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| updated_at | DateTime | NOT NULL | utcnow | MAJ |

### `kb_anomaly_rule`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| code | String(100) | NOT NULL | -- | Code regle (UNIQUE, indexed) |
| title | String(200) | NOT NULL | -- | Titre |
| description | Text | NULL | -- | Description |
| rule_type | String(50) | NOT NULL | -- | base_nuit, weekend, puissance... |
| severity | String(20) | NOT NULL | medium | Severite |
| thresholds_json | JSON | NULL | -- | Seuils (JSON) |
| conditions_json | JSON | NULL | -- | Conditions KB (JSON) |
| archetype_codes | JSON | NULL | -- | Archetypes applicables (JSON) |
| kb_item_id | String(200) | NULL | -- | Ref YAML item ID |
| kb_version_id | Integer | NULL | -- | FK -> kb_version.id |
| source_section | String(200) | NULL | -- | Section source |
| confidence | Enum(KBConfidence) | NOT NULL | HIGH | Confiance |
| status | Enum(KBStatus) | NOT NULL | VALIDATED | Statut |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| updated_at | DateTime | NOT NULL | utcnow | MAJ |

### `kb_recommendation`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| code | String(100) | NOT NULL | -- | Code reco (UNIQUE, indexed) |
| title | String(200) | NOT NULL | -- | Titre |
| description | Text | NULL | -- | Description |
| action_type | String(50) | NOT NULL | -- | regulation, equipment, behavior... |
| target_asset | String(50) | NULL | -- | hvac, eclairage, froid... |
| savings_min_pct | Float | NULL | -- | Economies min % |
| savings_max_pct | Float | NULL | -- | Economies max % |
| impact_score | Integer | NULL | -- | ICE: Impact (1-10) |
| confidence_score | Integer | NULL | -- | ICE: Confiance (1-10) |
| ease_score | Integer | NULL | -- | ICE: Facilite (1-10) |
| ice_score | Float | NULL | -- | Score ICE calcule |
| implementation_steps_json | JSON | NULL | -- | Etapes (JSON) |
| prerequisites_json | JSON | NULL | -- | Prerequis (JSON) |
| archetype_codes | JSON | NULL | -- | Archetypes applicables (JSON) |
| anomaly_codes | JSON | NULL | -- | Anomalies declencheuses (JSON) |
| kb_item_id | String(200) | NULL | -- | Ref YAML item ID |
| kb_version_id | Integer | NULL | -- | FK -> kb_version.id |
| source_section | String(200) | NULL | -- | Section source |
| confidence | Enum(KBConfidence) | NOT NULL | MEDIUM | Confiance |
| status | Enum(KBStatus) | NOT NULL | VALIDATED | Statut |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| updated_at | DateTime | NOT NULL | utcnow | MAJ |

### `kb_taxonomy`

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| category | String(50) | NOT NULL | -- | type, domain, energy... (indexed) |
| value | String(100) | NOT NULL | -- | Valeur |
| label | String(200) | NULL | -- | Libelle |
| description | Text | NULL | -- | Description |
| parent_value | String(100) | NULL | -- | Parent (taxonomie arborescente) |
| is_active | Boolean | NOT NULL | True | Actif |
| created_at | DateTime | NOT NULL | utcnow | Creation |
| updated_at | DateTime | NOT NULL | utcnow | MAJ |

---

## EMS Explorer

### `ems_weather_cache`

Mixins : TimestampMixin. Index UNIQUE : (site_id, date)

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (indexed) |
| date | DateTime | NOT NULL | -- | Date (indexed) |
| temp_avg_c | Float | NOT NULL | -- | Temperature moyenne C |
| temp_min_c | Float | NULL | -- | Temperature min C |
| temp_max_c | Float | NULL | -- | Temperature max C |
| source | String(50) | NOT NULL | demo | Source meteo |

### `ems_saved_view`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| user_id | Integer | NULL | -- | Utilisateur (indexed) |
| name | String(200) | NOT NULL | -- | Nom de la vue |
| config_json | Text | NOT NULL | -- | Configuration (JSON) |

### `ems_collection`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| name | String(200) | NOT NULL | -- | Nom de la collection |
| scope_type | String(50) | NOT NULL | custom | portfolio, org, custom |
| site_ids_json | Text | NOT NULL | [] | IDs de sites (JSON) |
| is_favorite | Integer | NOT NULL | 0 | Favori (0/1) |

---

## Tarification

### `site_operating_schedules`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (UNIQUE, indexed, 1:1) |
| timezone | String(50) | NOT NULL | Europe/Paris | Fuseau horaire IANA |
| open_days | String(20) | NOT NULL | 0,1,2,3,4 | Jours ouverts (CSV, 0=lun) |
| open_time | String(5) | NOT NULL | 08:00 | Heure ouverture HH:MM |
| close_time | String(5) | NOT NULL | 19:00 | Heure fermeture HH:MM |
| is_24_7 | Boolean | NOT NULL | False | Fonctionnement 24/7 |
| exceptions_json | Text | NULL | -- | Jours feries (JSON) |

Relations : `site` (1-1 backref uselist=False)

### `site_tariff_profiles`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| site_id | Integer | NOT NULL | -- | FK -> sites.id (UNIQUE, indexed, 1:1) |
| price_ref_eur_per_kwh | Float | NOT NULL | 0.18 | Prix ref EUR HT/kWh |
| currency | String(3) | NOT NULL | EUR | Devise ISO 4217 |

Relations : `site` (1-1 backref uselist=False)

### `tou_schedules`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| meter_id | Integer | NULL | -- | FK -> meter.id (indexed) |
| site_id | Integer | NULL | -- | FK -> sites.id (indexed) |
| name | String(100) | NOT NULL | HC/HP Standard | Nom |
| effective_from | Date | NOT NULL | -- | Debut validite |
| effective_to | Date | NULL | -- | Fin validite (NULL = actif) |
| is_active | Boolean | NOT NULL | True | Actif |
| windows_json | Text | NOT NULL | -- | Fenetres HP/HC (JSON) |
| source | String(50) | NULL | manual | manual, turpe, enedis_sge, grdf |
| source_ref | String(200) | NULL | -- | Reference doc/API |
| price_hp_eur_kwh | Float | NULL | -- | Prix HP EUR/kWh |
| price_hc_eur_kwh | Float | NULL | -- | Prix HC EUR/kWh |

### `tariff_calendars`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| name | String(200) | NOT NULL | -- | Nom (ex: TURPE 6 HTA) |
| version | String(50) | NULL | -- | Version tag |
| effective_from | String(10) | NOT NULL | -- | Date debut ISO |
| effective_to | String(10) | NULL | -- | Date fin ISO ou null |
| region | String(100) | NULL | -- | Region ou national |
| ruleset_json | Text | NOT NULL | -- | Fenetres tarifaires (JSON) |
| is_active | Boolean | NOT NULL | True | Actif |
| source | String(100) | NULL | -- | CRE, manual, etc. |
| notes | Text | NULL | -- | Notes |

---

## Decarbonation

### `emission_factors`

Mixins : TimestampMixin

| Colonne | Type | Nullable | Default | Description |
| --------- | ------ | ---------- | --------- | ------------- |
| id | Integer | PK | auto | Identifiant |
| energy_type | String(50) | NOT NULL | -- | electricity, gas, heat, other (indexed) |
| region | String(100) | NOT NULL | FR | Region/pays |
| valid_from | Date | NULL | -- | Debut validite |
| valid_to | Date | NULL | -- | Fin validite |
| kgco2e_per_kwh | Float | NOT NULL | -- | Facteur kgCO2e/kWh |
| source_label | String(300) | NULL | -- | Source (ADEME, demo...) |
| quality | String(20) | NULL | demo | official, estimated, demo |
