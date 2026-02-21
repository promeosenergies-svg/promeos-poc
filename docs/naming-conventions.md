# Conventions de nommage PROMEOS

> Reference -- regles de nommage validees sur le code existant.

## Backend (Python / FastAPI)

### Fichiers

- Models : `snake_case.py` (ex : `energy_models.py`, `consommation.py`, `billing_models.py`, `action_item.py`)
- Routes : `snake_case.py` (ex : `patrimoine.py`, `compliance.py`, `consumption_diagnostic.py`, `admin_users.py`)
- Services : `snake_case.py` (ex : `json_logger.py`, `billing_service.py`, `compliance_engine.py`, `iam_service.py`)

### Tables SQL

- Nom : `snake_case` pluriel (ex : `consommations`, `compteurs`, `alertes`, `sites`, `obligations`)
- Tables de liaison : `snake_case` pluriel avec suffixe `_links` (ex : `org_entite_links`, `portfolio_entite_links`)
- Tables staging : prefixe `staging_` (ex : `staging_batches`, `staging_sites`, `staging_compteurs`)
- Colonnes : `snake_case` (ex : `type_energie`, `date_debut`, `montant_ttc`, `surface_m2`, `code_postal`)

### Classes

- Models SQLAlchemy : `PascalCase` singulier (ex : `Consommation`, `Compteur`, `Site`, `Obligation`, `DeliveryPoint`)
- Mixins : `PascalCase` suffixe `Mixin` (ex : `TimestampMixin`, `SoftDeleteMixin`)
- Enums : `PascalCase` (ex : `TypeSite`, `StatutConformite`, `EnergyVector`, `ActionStatus`)
- Valeurs enum : `UPPER_SNAKE_CASE` pour la cle, `snake_case` pour la valeur string (ex : `ELECTRICITE = "electricite"`, `GAZ_NATUREL = "gaz"`, `NON_CONFORME = "non_conforme"`)

### Variables / fonctions

- `snake_case` (ex : `get_sites`, `create_consommation`, `soft_delete`, `not_deleted`)

---

## Frontend (React / JavaScript)

### Fichiers

- Composants : `PascalCase.jsx` (ex : `Dashboard.jsx`, `SitePicker.jsx`, `ROISummaryBar.jsx`, `ErrorBoundary.jsx`)
- Pages : `PascalCase.jsx` (ex : `CompliancePage.jsx`, `ConsumptionExplorerPage.jsx`, `Cockpit.jsx`)
- Hooks : `camelCase.js` prefixe `use` (ex : `useExplorerMotor.js`, `useExplorerPresets.js`, `useEmsTimeseries.js`)
- Services : `camelCase.js` (ex : `api.js`, `logger.js`, `tracker.js`)
- Utils : `camelCase.js` (ex : `format.js`, `navRecent.js`)
- Domain : `camelCase.js` dans `domain/<module>/` (ex : `domain/compliance/complianceLabels.fr.js`)
- UI tokens : `camelCase.js` dans `ui/` (ex : `ui/conventions.js`)
- Tests : `*.test.js` dans `__tests__/` (ex : `__tests__/logger.test.js`, `__tests__/api.test.js`)

### Variables / fonctions

- `camelCase` (ex : `getLastRequests`, `genRequestId`, `formatDate`, `fmtEur`, `isDemoPath`)

### Constantes

- `UPPER_SNAKE_CASE` (ex : `MAX_REQUESTS`, `LOG_LEVELS`, `API_BASE_URL`)
- Objets de config : `UPPER_SNAKE_CASE` (ex : `LAYOUT`, `TYPO`, `LABELS_FR`, `REG_LABELS`, `STATUT_LABELS`)

### CSS

- Tailwind utilities directement (pas de BEM, pas de CSS modules)
- Classes de design system centralisees dans `ui/conventions.js` (ex : `LAYOUT.page`, `TYPO.pageTitle`)

---

## Labels FR

### Source de verite

| Fichier | Contenu |
|---------|---------|
| `frontend/src/ui/conventions.js` | Design tokens (spacing, typo), labels generiques FR (`loading`, `noData`, `error`) |
| `frontend/src/domain/compliance/complianceLabels.fr.js` | Labels conformite, statuts, workflow, severite, regles metier FR |
| `frontend/src/utils/format.js` | Helpers formatage FR : `fmtEur`, `fmtArea`, `fmtKwh`, `fmtDateFR`, `formatPercentFR` |

### Energies

| Code backend | Label FR | Unite |
|---|---|---|
| `electricite` | Electricite | kWh |
| `gaz` | Gaz | kWh (PCS) |
| `eau` | Eau | m3 |
| `electricity` | Electricity (EnergyVector) | kWh |
| `gas` | Gas (EnergyVector) | kWh |
| `heat` | Chaleur reseau | kWh |

### Statuts conformite

| Code | Label FR |
|---|---|
| `conforme` | Conforme |
| `non_conforme` | Non conforme |
| `a_risque` | A risque |
| `derogation` | Derogation |
| `a_qualifier` | A qualifier |
| `hors_perimetre` | Hors perimetre |

### Severite

| Code | Label FR |
|---|---|
| `critical` | Critique |
| `high` | Elevee |
| `medium` | Moyenne |
| `low` | Faible |

### Workflow findings

| Code | Label FR |
|---|---|
| `open` | A traiter |
| `ack` | En cours |
| `resolved` | Resolu |
| `false_positive` | Faux positif |

### Unites standard

| Grandeur | Unite | Format affichage |
|---|---|---|
| Energie | kWh | `125k kWh` ou `1,2 GWh` (`fmtKwh`) |
| Surface | m2 | `11 562 m2` ou `11,6k m2` (`fmtArea`) |
| Cout | EUR | `24 k EUR` ou `1,2 M EUR` (`fmtEur`) |
| Pourcentage | % | `24 %` (`formatPercentFR`) |
| Date | - | `14 fev. 2026` (`fmtDateFR`) |

---

## Mapping backend -> frontend

| Backend (snake_case) | Frontend (camelCase) | Label FR |
|---|---|---|
| `site_id` | `siteId` | Site |
| `org_id` | `orgId` | Organisation |
| `compteur_id` | `compteurId` | Compteur |
| `type_site` | `typeSite` | Type de site |
| `surface_m2` | `surfaceM2` | Surface (m2) |
| `code_postal` | `codePostal` | Code postal |
| `nombre_employes` | `nombreEmployes` | Nombre d'employes |
| `statut_decret_tertiaire` | `statutDecretTertiaire` | Statut Decret Tertiaire |
| `avancement_decret_pct` | `avancementDecretPct` | Avancement (%) |
| `statut_bacs` | `statutBacs` | Statut BACS |
| `risque_financier_euro` | `risqueFinancierEuro` | Risque financier (EUR) |
| `anomalie_facture` | `anomalieFacture` | Anomalie facture |
| `action_recommandee` | `actionRecommandee` | Action recommandee |
| `puissance_souscrite_kw` | `puissanceSouscriteKw` | Puissance souscrite (kW) |
| `tertiaire_area_m2` | `tertiaireAreaM2` | Surface tertiaire (m2) |
| `parking_area_m2` | `parkingAreaM2` | Surface parking (m2) |
| `roof_area_m2` | `roofAreaM2` | Surface toiture (m2) |
| `energy_vector` | `energyVector` | Vecteur energetique |
| `data_source` | `dataSource` | Source de donnees |
| `data_source_ref` | `dataSourceRef` | Reference source |
| `created_at` | `createdAt` | Date de creation |
| `updated_at` | `updatedAt` | Date de modification |
| `deleted_at` | `deletedAt` | Date de suppression |
| `scope_type` | `scopeType` | Niveau de scope |
| `scope_id` | `scopeId` | ID du scope |

---

## Regles transversales

1. **Langue des colonnes SQL** : francais (`nom`, `adresse`, `ville`, `echeance`, `severite`) sauf termes techniques anglais standardises (`energy_vector`, `data_source`, `parking_type`).
2. **Langue des enums** : noms de classes en anglais PascalCase (`StatutConformite`, `TypeSite`), valeurs en francais snake_case (`"non_conforme"`, `"logement_social"`).
3. **API headers** : `X-Org-Id`, `X-Site-Id`, `X-Request-Id` (PascalCase avec prefixe `X-`).
4. **Token localStorage** : `promeos_token`.
5. **Locale** : `fr-FR` pour tous les formatages (nombres, dates, pourcentages).
6. **Mixins communs** : tout model herite de `TimestampMixin` (`created_at`, `updated_at`) ; les entites supprimables ajoutent `SoftDeleteMixin` (`deleted_at`, `deleted_by`, `delete_reason`).
