# Audit doctrine v2.0 « cockpit ouvert, interopérable, partenarial » — refonte-sol2

> **Mission** : auditer `claude/refonte-sol2` contre les **3 dimensions nouvelles** introduites par la note de vision v1.0 du 23/05/2026 (doctrine v2.0) :
> 1. **Plateforme ouverte API-first** — interopérabilité 6 couches.
> 2. **Partner Hub contextuel** — proposer le bon partenaire dans le contexte de l'action.
> 3. **Architecture connectable** — 9 environnements externes, 12 modules cœur, 23 tables data cible.
>
> **Date** : 2026-05-23 · **Mode** : READ-ONLY strict.
> **HEAD audité** : commit `ade3d0a0` (`claude/refonte-sol2`) · worktree dédié `.claude/worktrees/audit-cockpit-ouvert/`.
> **Doctrine source** : memory `project_promeos_vision_cockpit_patrimoine_ouvert_2026_05_23.md` (étend v1.3 du 08/05).
> **Périmètre exclu court terme** : ACC / PMO / clé de répartition (compat archi future, hors POC) · chaleur réseau urbain · vapeur process industriel.

## TL;DR

🎯 **Doctrine v2.0 portée à ~55 %** sur `claude/refonte-sol2`.

Les fondations API + webhooks + connecteurs sont **partielles** : `/api/v1/` prefix utilisé sur quelques routers (`navigation`, `doctrine`, `events`, `users`, `digest`) mais **majorité encore en `/api/` v0**. Les connecteurs sont **bien isolés** (`backend/connectors/` : 12 modules dont enedis_dataconnect, grdf_adict, entsoe, rte_eco2mix, meteofrance, pvgis), `event_bus/` existe avec `WebhookSubscription` model + endpoints `/webhooks` (GET/POST/DELETE).

**Partner Hub absent** : 0 modèle `Partner` / `PartnerPermission` / `PartnerActionProposal`. Endpoints `/api/v1/partner/*` absents. RBAC partenaire absent.

**5 statuts moteur réglementaire** : confirmé 4 statuts actuels (`APPLICABLE` / `NOT_APPLICABLE` / `UNKNOWN` / `DATA_MISSING`) — granularité « probablement_soumis / probablement_non_soumis » non implémentée.

**7 statuts data** par donnée (`reel/importe/calcule/estime/manquant/incoherent/obsolete`) : pas d'enum dédié, occurrences `estime` éparses, traçabilité partielle via `confidence_rule` du `kpi_registry`.

**Data Readiness Score multi-modules** : `readiness_score` existe pour Sirene, Reconciliation, Technical, Action, mais **pas un score canonique par pilier doctrinal** (Patrimoine / Conformité / Facture / Achat / Conso / Pilotage / Flex).

---

## 1. Architecture interopérabilité 6 couches

### 1.1 Couche 1 — Référentiel interne (vérité métier)

| Entité | Modèle | File | Verdict |
|---|---|---|---|
| Patrimoine (Org / EJ / Portefeuille / Site / Bâtiment / Compteur) | présent — cf. audit doctrine patrimoine §1.1 | `backend/models/{organisation,entite_juridique,portefeuille,site,batiment,compteur}.py` | ✅ |
| Contrats V2 | `ContractV2Models` + `ContractDeliveryPoint` N:N | `backend/models/contract_v2_models.py` | ✅ |
| Factures | `EnergyInvoice` + `EnergyInvoiceLine` | `backend/models/billing_models.py` | ✅ |
| Consommations | `Consommation` (CDC) + `ConsumptionInsight` | présent | ✅ |
| Équipements | `BacsCvcSystem` + équipement enum | présent | ✅ |
| Régulations | 5 évaluateurs ADR-024 | `backend/regulatory/rules/` | ✅ |
| Actions | `ActionItem` + state machine | `backend/models/action_item.py` | ✅ |
| Preuves | `Evidence` model ADR-029 + 16 event_types | présent | ✅ |
| **Partenaires** | `Partner` / `PartnerPermission` / `PartnerActionProposal` | — | ❌ **P0 cardinal v2.0** |
| **Connecteurs (méta)** | `Connector` / `ConnectorRun` / `ExternalMapping` | partiellement via `ConnectorToken` | 🟡 **P1** — table `connector_runs` absente |

### 1.2 Couche 2 — API stables versionnées

| API canon doctrine v2.0 | Route effective | Verdict |
|---|---|---|
| `/api/v1/organisations` | majorité `/api/...` sans v1 | 🟡 — versionning v1 partiel |
| `/api/v1/sites` | `routes/patrimoine.py` + `routes/sites.py` (legacy) | 🟡 |
| `/api/v1/buildings` | `routes/patrimoine_crud.py` (bâtiments) | 🟡 |
| `/api/v1/meters` | `routes/compteurs.py` | 🟡 |
| `/api/v1/contracts` | `routes/contracts_v2.py` + `contracts_radar.py` | 🟡 |
| `/api/v1/invoices` | `routes/billing.py` | 🟡 |
| `/api/v1/consumption` | `routes/consumption_unified.py` + `consumption_diagnostic.py` | 🟡 |
| `/api/v1/regulations` | `routes/regulatory_applicability.py` + `routes/regops.py` | 🟡 |
| `/api/v1/actions` | `routes/actions.py` + `action_center.py` | 🟡 |
| `/api/v1/evidences` | dans `routes/actions.py:881` (`add_evidence`) | 🟡 — pas d'endpoint dédié `/evidences` |
| `/api/v1/partners` | — | ❌ |
| `/api/v1/connectors` | — | ❌ |
| `/api/v1/webhooks` | `routes/webhooks.py` (GET/POST/DELETE l. 286-329) | ✅ |
| `/api/v1/navigation` | `routes/navigation.py:26` | ✅ |
| `/api/v1/doctrine` | `routes/doctrine.py:18` | ✅ |
| `/api/v1/events` | `routes/events.py:40` | ✅ |
| `/api/v1/users` | `routes/users.py:34` | ✅ |
| `/api/v1/digest` | `routes/digest.py:20` | ✅ |
| OpenAPI documentée | FastAPI auto-generation | 🟢 disponible par défaut, à exposer publiquement |

**Verdict** : ~5 routers ont migré vers `/api/v1/`. ~99 autres routers utilisent `/api/...` v0. **Migration v1 systématique = P1.**

### 1.3 Couche 3 — Connecteurs isolés

| Connecteur doctrine v2.0 | Code refonte-sol2 | File | Verdict |
|---|---|---|---|
| `enedis/` | `backend/connectors/enedis_dataconnect.py` + `enedis_opendata.py` + `enedis_dataconnect_errors.py` | présent | ✅ |
| `grdf/` | `backend/connectors/grdf_adict.py` + `grdf_errors.py` | présent | ✅ |
| `operat/` | — | — | ❌ **P0** (connecteur OPERAT manquant) |
| `supplier_generic/` | — | — | ❌ **P0** |
| `gtb_modbus/` | — | — | 🔵 P2 (Mois 6+) |
| `gtb_bacnet/` | — | — | 🔵 P2 |
| `mqtt_iot/` | — | — | 🔵 P2 |
| `erp_export/` | — | — | 🔵 P2 |
| `billing_platform/` | partial via `billing_normalization.py` | présent | 🟡 |
| `aggregator/` | — | — | 🔵 P2 (post agrégateur RTE) |
| `partner_sdk/` | — | — | ❌ **P1** |
| `rte_eco2mix/` (signaux marché) | `backend/connectors/rte_eco2mix.py` | ✅ | bonus doctrine |
| `entsoe/` (signaux EU) | `backend/connectors/entsoe_connector.py` | ✅ | bonus doctrine |
| `meteofrance/` (DJU) | `backend/connectors/meteofrance.py` | ✅ | bonus doctrine |
| `pvgis/` (PV potentiel APER) | `backend/connectors/pvgis.py` | ✅ | bonus doctrine |
| Registry connecteurs | `backend/connectors/registry.py` | ✅ | structure cohérente |
| Base abstraite | `backend/connectors/base.py` | ✅ | pattern factory + héritage |
| Contracts | `backend/connectors/contracts.py` | ✅ | types Python pour I/O |

**Verdict** : couche connecteurs **bien posée** (15 fichiers, factory pattern, registry, contracts typés) mais 7 connecteurs canon de la doctrine v2.0 manquent.

### 1.4 Couche 4 — Mapping & normalisation

| Item | Code | Verdict |
|---|---|---|
| Normalisation factures → `invoice_line.type` canonique | `billing_normalization.py` (150+ LoC) | ✅ |
| `external_mappings` table (lien external_id ↔ internal_id avec `confidence_score`) | — | ❌ **P1** — absent côté modèle |
| Mapping fournisseur → composante TURPE/ATRD/CTA | dans `billing_normalization` (statique) | 🟡 — pas de table dynamique versionnée |
| `confidence_score` exposé sur chaque mapping | `kpi_registry.confidence_rule` (haut niveau) | 🟡 — pas par ligne facture |

### 1.5 Couche 5 — Webhooks & événements

| Item | Code | Verdict |
|---|---|---|
| `event_bus/` (publication + detection) | `backend/services/event_bus/` (event_service, freshness, types, detectors) | ✅ |
| Modèle `WebhookSubscription` | `backend/models/*.py:179` | ✅ |
| Endpoints `/webhooks` (GET/POST/DELETE) | `backend/routes/webhooks.py:286,308,329` | ✅ |
| Event `event.site.created` | logs Phase 1.3 via `log_patrimoine_change` | ✅ |
| Event `event.meter.connected` | — | 🟡 à confirmer |
| Event `event.invoice.imported` | `BillingImportBatch` audit | ✅ |
| Event `event.invoice.anomaly_detected` | 🟢 bus prévu mais pipeline L17 wiring (P0 cardinal) | ⚠️ |
| Event `event.regulation.status_changed` | déclenchement post-`compute_applicability` | 🟡 à confirmer trigger automatique |
| Event `event.action.created` | `ActionEvent` model + 16 event_types ADR-029 | ✅ |
| Event `event.action.completed` | idem | ✅ |
| Event `event.contract.expiring` | `compliance_deadline_detector.py` + `contract_expiration_alerts.py` | ✅ |
| Event `event.partner.recommendation_ready` | — | ❌ **P1** |
| Event `event.flex.eligibility_changed` | `flex_opportunity_detector.py` | ✅ |
| Retry webhook en échec | `webhook_events.retries` champ | 🟢 à vérifier en source-guard |

**Verdict** : **couche événements ~75 %** — bien posée mais 2 events partenaires manquants + pipeline anomalies L17 cardinal.

### 1.6 Couche 6 — Portail partenaires

| Item | Code | Verdict |
|---|---|---|
| Espace partenaire dédié | — | ❌ **P0 v2.0** |
| Portefeuille autorisé par partenaire | — | ❌ |
| Permissions granulaires (8 niveaux) | — | ❌ |
| API credentials partenaire | — | ❌ |
| Webhooks dédiés par partenaire | — | ❌ |

**Verdict couche 6** : **0 %** — entièrement à construire.

### Synthèse Architecture interop

| Couche | Couverture | Verdict |
|---|---|---|
| 1. Référentiel interne | 90 % | ✅ — gap Partner / Connecteur méta |
| 2. API versionnées `/api/v1/` | 30 % | 🟡 — migration v1 systématique = P1 |
| 3. Connecteurs isolés | 65 % | 🟡 — 7 connecteurs canon manquent (OPERAT, supplier_generic, partner_sdk, GTB) |
| 4. Mapping & normalisation | 50 % | 🟡 — table `external_mappings` absente |
| 5. Webhooks & événements | 75 % | ✅ — pipeline L17 P0 + 2 events partenaires P1 |
| 6. Portail partenaires | 0 % | ❌ **P0 v2.0** |
| **Moyenne** | **~50 %** | — |

---

## 2. Partner Hub contextuel

### 2.1 Vision doctrine

> *« Le Partner Hub ne doit pas devenir un menu supplémentaire compliqué. Il doit apparaître dans le contexte de l'action. »*

Exemples canon :
- Anomalie facture → expert facture / courtier / fournisseur
- Site BACS probablement soumis → intégrateur GTB
- Dérive CVC → mainteneur ou audit technique
- Contrat à échéance → consultation fournisseurs
- Potentiel flexibilité → agrégateur
- Potentiel économie → société d'efficacité énergétique (SEE)
- Dossier CEE possible → opérateur CEE

### 2.2 État du code

| Item | Verdict | Détail |
|---|---|---|
| Modèle `Partner` (id, name, type, status, contact, api_enabled, certification_level) | ❌ | absent |
| Modèle `PartnerPermission` (partner_id, organisation_id, scope, data_access_level, expires_at, granted_by, granted_at, revoked_at) | ❌ | absent |
| Modèle `PartnerActionProposal` (partner_id, action_id, proposal_status, amount_estimated, gain_estimated, document_id) | ❌ | absent |
| Endpoint `GET /api/v1/partners` | ❌ | — |
| Endpoint `POST /api/v1/partners/invite` | ❌ | — |
| Endpoint `POST /api/v1/partners/{id}/permissions` | ❌ | — |
| Endpoint `POST /api/v1/actions/{id}/share-with-partner` | ❌ | — |
| Endpoint `GET /api/v1/partner/sites` (côté partenaire authentifié) | ❌ | — |
| Endpoint `POST /api/v1/partner/actions/{id}/proposal` | ❌ | — |
| Recommandation contextuelle « cette action nécessite un partenaire X » | — | ❌ **P1** — pas de service `recommend_partner_for_action(action, context)` |
| RBAC 8 niveaux d'accès | — | ❌ |
| Journal accès partenaire | `audit_log_service.py` existe — extensible | 🟡 à étendre |
| Consentement client explicite pour partage données | — | ❌ |
| Expiration et révocation accès | — | ❌ |
| Permissions par type partenaire (courtier / fournisseur / SEE / agrégateur / intégrateur GTB / auditeur) | — | ❌ |

### Synthèse Partner Hub

**0 %** — entièrement à construire. **P0 cardinal v2.0** si la promesse « cockpit ouvert partenarial » fait partie du pitch.

---

## 3. Connectors Hub

### 3.1 État du code

✅ **Bonne fondation** : `backend/connectors/` structuré comme un **registry/factory** avec :
- `base.py` (abstraction)
- `contracts.py` (types I/O typés Python)
- `registry.py` (dispatch)
- 12 connecteurs concrets (Enedis OpenData + DataConnect, GRDF ADICT, ENTSOE, RTE eCO2mix, MétéoFrance, PVGIS, etc.)
- Gestion erreurs dédiée (`enedis_dataconnect_errors.py`, `grdf_errors.py`)

### 3.2 Gaps identifiés vs doctrine v2.0

| Gap | Verdict | Priorité |
|---|---|---|
| Table `connectors` (id, type, provider, status, auth_type, last_sync_at, error_count, owner_org_id) | ❌ partiel via `ConnectorToken` | **P1** |
| Table `connector_runs` (started_at, ended_at, status, records_in, records_out, errors, correlation_id) | ❌ | **P1** — observabilité runs |
| Table `external_mappings` (external_object_type/id, internal_object_type/id, confidence_score) | ❌ | **P1** |
| Endpoint `GET /api/v1/connectors` | ❌ | **P1** |
| Endpoint `POST /api/v1/connectors/{id}/sync` (déclenchement manuel) | ❌ | **P1** |
| Endpoint `GET /api/v1/connectors/{id}/health` | ❌ | **P1** |
| Connecteur OPERAT (ADEME) | ❌ | **P0** — déjà identifié audit mapping §13.1 |
| Connecteur SDK partenaire générique (CSV/API) | ❌ | **P1** |
| Connecteur GTB générique (Modbus/BACnet/LonWorks/MQTT) | ❌ | **P1** (cf. audit mapping P1-8) |
| Sandbox + jeu de données démo SDK | — | 🔵 P2 |

---

## 4. 5 statuts moteur réglementaire — granularité v2.0

### 4.1 État actuel ADR-024 (4 statuts)

`backend/regulatory/applicability_types.py:37` :
```python
class ApplicabilityStatus(StrEnum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"
    DATA_MISSING = "data_missing"
```

### 4.2 Granularité v2.0 attendue (5 statuts)

```python
class ApplicabilityStatus(StrEnum):
    NOT_APPLICABLE = "not_applicable"          # données suffisantes, règle ne s'applique pas
    PROBABLY_NOT_APPLICABLE = "probably_not_applicable"  # NOUVEAU — faisceau d'indices "non" mais données partielles
    DATA_MISSING = "data_missing"              # champs cardinaux manquants
    PROBABLY_APPLICABLE = "probably_applicable"  # NOUVEAU — faisceau d'indices "oui" mais à confirmer
    APPLICABLE = "applicable"                  # données suffisantes, règle s'applique
```

| Item | Verdict | Détail |
|---|---|---|
| Mapping ADR-024 4 statuts → doctrine v2.0 5 statuts | ❌ | **P1** — granularité « probably_* » absente |
| UI `<CadreApplicable.jsx>` adapte le rendu pour 5 statuts | ❌ | **P1** — actuellement 4 statuts |
| Impact tests : 54 tests régulatoires existants à compléter avec cas `probably_*` | — | **P1** |
| Migration backward-compatible (legacy `UNKNOWN` → `PROBABLY_*` ?) | — | **P1** — décision de migration |

### Synthèse 5 statuts

**P1** — extension granulaire à introduire. Effort 3-5 j-h (refactor `ApplicabilityStatus` enum + UI + 54 tests + migration).

---

## 5. 7 statuts data — qualité de donnée explicite

### 5.1 Vision doctrine v2.0

Chaque donnée affichée doit porter un statut parmi 7 :
- `reel` — donnée mesurée / facturée
- `importe` — donnée importée d'une source tierce
- `calcule` — donnée dérivée d'autres données réelles
- `estime` — estimation avec hypothèse explicite
- `manquant` — absente
- `incoherent` — détectée comme incohérente
- `obsolete` — donnée datée vs période courante

### 5.2 État actuel

| Item | Verdict | Détail |
|---|---|---|
| Enum `DataStatus(StrEnum)` dans `backend/models/enums.py` ou `backend/doctrine/` | ❌ | **P0** — enum cardinal absent |
| Champ `data_status` sur entités cardinales (`Consommation`, `EnergyInvoice`, `Compteur`, `Site`) | ❌ | **P0** |
| `confidence_rule` dans `KPI_REGISTRY` | ✅ — par KPI mais pas par valeur affichée | 🟡 |
| Marquage `estime` quand fallback utilisé | présent ad-hoc (`pilotage/`, `radar_prix_negatifs`, `flex_nebco_service` avec `hypotheses`) | 🟡 — non standardisé |
| Marquage `incoherent` post-`reconcile_metered_billed()` (delta > 10 %) | logique présente mais pas tracée comme `data_status` | 🟡 |
| Marquage `obsolete` (ex. DJU année N-1 sur N) | — | ❌ |

### Synthèse 7 statuts data

**P0** cardinal — enum `DataStatus` + champ sur entités + propagation FE. Effort ~3-5 j-h.

---

## 6. Data Readiness Score multi-modules

### 6.1 Vision doctrine v2.0

7 scores indépendants — un par pilier :
- Patrimoine
- Conformité
- Facture
- Achat
- Consommation
- Pilotage usages
- Flexibilité

Chaque score affiche : OK ✅ / Manquant ❌ / Conclusion (« la trajectoire 2030 ne peut pas être fiabilisée tant que … »).

### 6.2 État actuel

| Pilier | Score actuel | Verdict |
|---|---|---|
| Patrimoine | `compute_patrimoine_maturity()` → float [0..1] | ✅ — ADR-024 maturity |
| Conformité | implicite via `compliance_score` (regops) — pondéré par règles applicables | 🟡 — pas un readiness pur (mélange data + résultat) |
| Facture | `readiness_score` Sirene + Reconciliation | 🟡 — pas score unique « Bill Intelligence » |
| Achat | — | ❌ **P1** |
| Consommation | `data_quality_score` (KPI registry) + `coverage_pct` | 🟡 — partiel |
| Pilotage | `flex_assessment.score` ou `roi_flex_ready` | 🟡 |
| Flexibilité | `flex_ready_score` (cf. `pilotage/flex_ready.py`) | 🟡 |
| Score unifié `data_readiness` exposé sur Cockpit | — | ❌ **P0** — pas de tuile Cockpit dédiée multi-pilier |

### Synthèse Data Readiness

**P1** — agréger les scores existants dans une vue unifiée Cockpit. Effort 3-5 j-h.

---

## 7. 5 niveaux maturité pilotage des usages

### 7.1 Vision doctrine v2.0

- Niveau 0 — Pas de données
- Niveau 1 — Données factures (tendances mensuelles)
- Niveau 2 — Courbes compteur (pics, talons, horaires)
- Niveau 3 — Données équipement / GTB (relier dérives ↔ équipement)
- Niveau 4 — Pilotage assisté (recos horaires/tarifaires)
- Niveau 5 — Pilotage automatisé (consignes vers GTB/EMS/IRVE)

### 7.2 État du code

| Niveau | Vérifié dans le code | Verdict |
|---|---|---|
| Niveau 0 — Pas de données | Recommandation données via `DATA_MISSING` ADR-024 | ✅ |
| Niveau 1 — Données factures | `billing_canonical_service` + `cost_by_period_service` + `monthly_comparison_service` | ✅ |
| Niveau 2 — Courbes compteur | `consumption_diagnostic.py` + `CarpetPlot.jsx` + `load_profile_service.py` | ✅ |
| Niveau 3 — Données équipement / GTB | `BacsCvcSystem` modèle ✅ ; **connecteur GTB générique absent** | 🟡 |
| Niveau 4 — Pilotage assisté | `recommendation_engine.py` + `consumption_diagnostic._actions_*()` | ✅ |
| Niveau 5 — Pilotage automatisé | aucun endpoint dispatch (mode advisory strict — cf. audit mapping §5.4) | ❌ **P2 hors scope MVP** (advisory only) |
| Service `compute_pilotage_maturity_level(site) → int 0-5` | — | ❌ **P1** — pas de calcul explicite |
| UI affichage niveau atteint par site | — | ❌ **P1** |

### Synthèse 5 niveaux pilotage

**P1** — formaliser le calcul et l'affichage par site. Effort 2-3 j-h.

---

## 8. 5 niveaux flexibilité progressive

### 8.1 Vision doctrine v2.0

- Niveau 1 — Implicite (HP/HC, heures solaires, signal spot)
- Niveau 2 — Opérationnelle interne (décalage usage, planning)
- Niveau 3 — Pilotée via GTB / systèmes locaux
- Niveau 4 — Valorisable via agrégateur (effacement, capacité)
- Niveau 5 — Orchestration multi-sites

### 8.2 État du code

| Niveau | Verdict | File |
|---|---|---|
| Niveau 1 — Implicite | `tariff_periods_service.py` + `tou_service.py` + spot detection `radar_prix_negatifs.py` | ✅ |
| Niveau 2 — Opérationnelle | `schedule_detection_service.py` + `power_optimization_service.py` | ✅ |
| Niveau 3 — GTB pilotée | enum `BacsCvcSystem` ✅ + **connecteur GTB manquant** | 🟡 |
| Niveau 4 — Agrégateur (NEBCO/AOFD) | `flex_nebco_service.py` + `flex_assessment_service.py` + `flex_mini.py` | ✅ — mode advisory |
| Niveau 5 — Orchestration multi-sites | `portefeuille_scoring.py` + agrégation portfolio | 🟡 — partiel |
| Service `compute_flex_progression_level(site) → int 1-5` | — | ❌ **P1** |
| UI roadmap progressive « vous êtes au niveau 2, ouvrez le niveau 3 » | — | ❌ **P1** |

### Synthèse 5 niveaux flex

**P1** — formaliser le calcul progressif. Effort 2-3 j-h.

---

## 9. 4 modes recommandation (consentement utilisateur)

### 9.1 Vision doctrine v2.0

- recommandation manuelle (utilisateur exécute)
- action semi-automatique validée par l'utilisateur
- action automatique avec règles validées
- action interdite (contrainte métier)

### 9.2 État du code

| Mode | Verdict | Détail |
|---|---|---|
| Recommandation manuelle | ✅ | mode par défaut Centre d'Action |
| Action semi-automatique validée | 🟢 à confirmer | présence partielle via `action_close_rules` + auto-fermeture sur source résolue |
| Action automatique avec règles | ❌ | hors scope MVP advisory |
| Action interdite (contrainte métier) | ❌ | pas de mécanisme dédié |
| Enum `RecommendationMode` | — | ❌ **P1** |
| Champ `recommended_mode` sur `ActionItem` | — | ❌ |
| Consentement signé pour modes 2/3 | — | ❌ |

### Synthèse 4 modes reco

**P1** — formaliser l'enum + champ sur ActionItem. Effort 2-3 j-h.

---

## 10. 12 modules cœur

| # | Module canon | Code refonte-sol2 | Verdict |
|---|---|---|---|
| 1 | Patrimoine | hiérarchie 8 niveaux modélisée | ✅ |
| 2 | Data Readiness | `compute_patrimoine_maturity()` + scores éparses | 🟡 |
| 3 | Conformité conditionnelle | ADR-024 + 5 évaluateurs + `<CadreApplicable />` | ✅ |
| 4 | Consommation / Performance | `consumption_unified_service` SoT | ✅ |
| 5 | Bill Intelligence | shadow billing + 13 règles R19-R31 + pipeline L17 wiring P0 | ⚠️ |
| 6 | Contract Intelligence | `contract_v2_service` + `contract_risk_service` + `contracts_radar` | ✅ |
| 7 | Purchase Strategy | `purchase/strategy_recommender.py` + `cost_simulator_2026.py` | ✅ |
| 8 | Usage Steering | `consumption_diagnostic` + `pilotage/*` | ✅ |
| 9 | Action Center | `action_hub_service` + lifecycle ADR-028 | ✅ |
| 10 | Evidence Center | `Evidence` model ADR-029 + 16 event_types | ✅ |
| 11 | **Partner Hub** | absent | ❌ **P0 v2.0** |
| 12 | **Connectors Hub** | `backend/connectors/` (15 fichiers) mais sans table méta | 🟡 |

**Verdict** : **10/12 modules présents** (83 %). Les 2 modules manquants sont **Partner Hub** (P0 cardinal v2.0) et **Connectors Hub** méta (P1).

---

## 11. Format erreur API standardisé (10 types)

### 11.1 Vision doctrine v2.0

```json
{
  "code": "MISSING_REQUIRED_DATA",
  "message": "La surface tertiaire est manquante pour déterminer l'assujettissement au Décret Tertiaire.",
  "hint": "Ajoutez la surface tertiaire du bâtiment ou importez un fichier patrimoine.",
  "correlation_id": "req_20260523_001",
  "blocking": true
}
```

### 11.2 État du code

| Code erreur canon | Présence partiel | Verdict |
|---|---|---|
| `MISSING_REQUIRED_DATA` | `DATA_MISSING` côté regulatory + `fix_hint_fr` | 🟡 — pas wrapper unifié |
| `INVALID_UNIT` | — | ❌ |
| `INCONSISTENT_PERIOD` | logique réconciliation existe | 🟡 |
| `CONNECTOR_AUTH_FAILED` | `enedis_dataconnect_errors.py` + `grdf_errors.py` | 🟢 par connecteur |
| `CONNECTOR_RATE_LIMIT` | rate limit GRDF (5 req/s) | 🟢 |
| `PARTNER_PERMISSION_DENIED` | — | ❌ (Partner Hub absent) |
| `REGULATION_RULE_VERSION_MISSING` | `RULES_VERSIONS` + source-guard `test_reason_codes_whitelist` | ✅ |
| `INVOICE_PARSE_FAILED` | parser PDF générique absent | ❌ |
| `CONTRACT_MISSING` | — | 🟡 |
| `METER_NOT_LINKED` | `compteur_meter_bridge.py` + `IDOR fix Phase C-7` | ✅ |
| `correlation_id` propagé partout | ✅ ADR-027 IS9 | ✅ |
| Wrapper `ErrorResponse` Pydantic | — | ❌ **P1** |
| Middleware `correlation_id_middleware.py` | structlog config | 🟢 partial |
| OpenAPI documente codes erreur | — | ❌ **P1** |

**Verdict** : **`correlation_id` ✅, `fix_hint_fr` ✅, mais wrapper unifié `ErrorResponse` absent**. Effort P1 ~2-3 j-h.

---

## 12. 23 tables data cible

| Table doctrine v2.0 | Code refonte-sol2 | Verdict |
|---|---|---|
| `organisations` | `Organisation` | ✅ |
| `legal_entities` | `EntiteJuridique` | ✅ |
| `portfolios` | `Portefeuille` | ✅ |
| `sites` | `Site` | ✅ |
| `buildings` | `Batiment` | ✅ |
| `meters` | `Compteur` | ✅ |
| `contracts` | `EnergyContract` + `ContractV2Models` | ✅ |
| `invoices` | `EnergyInvoice` | ✅ |
| `invoice_lines` | `EnergyInvoiceLine` | ✅ |
| `consumption_readings` | `Consommation` (CDC) | ✅ |
| `equipment` | `BacsCvcSystem` + autres | ✅ |
| `usage_profiles` | `UsageBreakdownSnapshot` | ✅ |
| `regulation_assessments` | `RegAssessment` + `RuleApplicability` | ✅ |
| `data_requirements` | reason_codes `DATA_MISSING.{FIELD}` mais pas table dédiée | 🟡 |
| `anomalies` | `BillingAnomaly` + `ComplianceFinding` + `ConsumptionInsight` | ✅ |
| `energy_opportunities` | `flex_opportunity_detector` + détecteurs | 🟡 — pas table unifiée |
| `actions` | `ActionItem` | ✅ |
| `evidences` | `Evidence` | ✅ |
| `partners` | — | ❌ **P0** |
| `partner_permissions` | — | ❌ **P0** |
| `connectors` | `ConnectorToken` partiel | 🟡 |
| `connector_runs` | — | ❌ **P1** |
| `webhook_events` | `WebhookSubscription` + event_bus | ✅ |
| `audit_logs` | `audit_log_service` + `compliance_event_log` | ✅ |
| Bonus : `external_mappings` | — | ❌ **P1** |
| Bonus : `partner_action_proposals` | — | ❌ **P0** |

**Verdict** : **18/23 tables présentes** (78 %). Gap : **6 tables Partner Hub + Connectors Hub méta + opportunités unifiées** (P0/P1).

---

## 13. Synthèse globale doctrine v2.0

### 13.1 Couverture par dimension

| Dimension nouvelle v2.0 | Couverture | Verdict |
|---|---|---|
| Architecture interopérabilité 6 couches | ~50 % | 🟡 |
| Partner Hub contextuel | 0 % | ❌ **P0** |
| Connectors Hub méta + 12 connecteurs canon | 65 % | 🟡 |
| 5 statuts moteur réglementaire | 4/5 | 🟡 P1 |
| 7 statuts data | 0/7 enum dédié | ❌ **P0** |
| Data Readiness Score multi-modules | 30 % | 🟡 P1 |
| 5 niveaux maturité pilotage | logique présente, formalisation absente | 🟡 P1 |
| 5 niveaux flexibilité progressive | logique présente, formalisation absente | 🟡 P1 |
| 4 modes recommandation | 1/4 | 🟡 P1 |
| 12 modules cœur | 10/12 (83 %) | ✅ |
| 10 types erreurs API standardisés | `correlation_id` ✅ + `hint` ✅ + wrapper ❌ | 🟡 P1 |
| 23 tables data cible | 18/23 (78 %) | 🟡 |
| **Moyenne pondérée** | **~55 %** | — |

### 13.2 Top 5 P0 doctrine v2.0 (cumul ~22-32 j-h)

| # | Item P0 | Effort | Justification |
|---|---|---|---|
| 1 | **Modèles Partner + PartnerPermission + PartnerActionProposal** + RBAC 8 niveaux + endpoints `/api/v1/partners` + `/api/v1/partner/*` (côté partenaire authentifié) | 8-12 j | Cardinal pour la promesse « cockpit ouvert partenarial » |
| 2 | **Enum `DataStatus`** (7 valeurs : reel/importe/calcule/estime/manquant/incoherent/obsolete) + propagation entités cardinales + FE markers | 3-5 j | Cardinal « ne jamais afficher une donnée estimée comme certaine » |
| 3 | **Connecteur OPERAT ADEME** (déjà identifié audit mapping) + connecteur **SDK partenaire générique** | 5-7 j | Centralisation + extensibilité |
| 4 | **Pipeline anomalies L17 wiring** (déjà identifié — répété ici car cardinal pour Bill Intelligence brique 5 doctrine v2.0) | 3-5 j | cf. audit mapping P0 #2 |
| 5 | **Tuile Cockpit Data Readiness multi-modules** (7 scores agrégés en vue unifiée) | 3-5 j | DoD v2.0 critère 4 « données manquantes expliquées » |

### 13.3 Top 7 P1 doctrine v2.0 (cumul ~25-37 j-h)

| # | Item P1 | Effort |
|---|---|---|
| 1 | Migration `/api/v1/` systématique sur ~99 routers + OpenAPI publiquement exposée | 5-8 j |
| 2 | Modèle `ApplicabilityStatus` granularité 5 statuts (+ `probably_*`) + extension UI `<CadreApplicable />` + 10 nouveaux tests par règle | 3-5 j |
| 3 | Tables `connectors` + `connector_runs` + `external_mappings` + endpoints `/api/v1/connectors` | 5-7 j |
| 4 | Wrapper `ErrorResponse` Pydantic + middleware correlation_id + middleware unifié error_handler + documentation OpenAPI codes erreur | 3-5 j |
| 5 | Service `compute_pilotage_maturity_level(site) → int 0-5` + `compute_flex_progression_level(site) → int 1-5` + UI affichage par site | 3-5 j |
| 6 | Enum `RecommendationMode` (4 valeurs) + champ sur ActionItem + workflow consentement signé | 2-3 j |
| 7 | Events partenaires : `event.partner.recommendation_ready` + `event.action.shared_with_partner` | 2-3 j |

### 13.4 P2 différenciation (~30-50 j-h)

- Marketplace dynamique partenaires avec scoring + rating client
- SDK partenaire (Postman, sandbox, OpenAPI, exemples, jeu démo)
- 9 connecteurs P2 (`gtb_modbus`, `gtb_bacnet`, `mqtt_iot`, `erp_export`, `aggregator`)
- Pilotage GTB semi-automatique (Niveau 5 du progression)
- Orchestration multi-sites flex (Niveau 5)
- Assistant énergétique contextuel (LLM léger sur les KPI/dérives/recos)
- Scoring partenaire continu

---

## 14. Recoupement avec les 4 audits précédents

| Audit | Sujet | Recoupement avec v2.0 |
|---|---|---|
| 1. `audit_readonly_promeos_scope_sans_acc_usage_steering.md` | Code seul, scope sans ACC | Couvre architecture mais pas Partner Hub explicite — **complété ici** |
| 2. `audit_docs_drive_promeos_sans_acc.md` | Extraction 6 docs Drive | Couvre exigences réglementaires/TURPE — **non-redondant avec v2.0** |
| 3. `audit_drive_vs_refonte_sol2_mapping.md` | Mapping bidirectionnel 5 verbes | Top 9 P0 = 50-74 j-h — **complémentaire** : ce nouvel audit ajoute ~22-32 j-h P0 spécifiques v2.0 (Partner Hub + DataStatus + Connectors méta + Data Readiness multi-modules) |
| 4. `audit_doctrine_patrimoine_declencheur_refonte_sol2.md` | Doctrine v1.3 patrimoine + QA + DoD | Couvre 5 verbes + workflow + QA — **v2.0 enrichit** avec interop + Partner Hub. Le service `levers_recommender` P0 reste cardinal commun. |

### Bilan effort consolidé (5 audits cumulés)

| Catégorie | Audit 4 (doctrine v1.3) | Audit 5 (doctrine v2.0) | **Total cumulé** |
|---|---|---|---|
| P0 (bloquant pilote) | ~56-78 j-h | **+22-32 j-h** | **~78-110 j-h** |
| P1 (crédibilité scale-up) | ~45-60 j-h | **+25-37 j-h** | **~70-97 j-h** |
| P2 (différenciation world-class) | ~30-50 j-h | **+30-50 j-h** | **~60-100 j-h** |
| **TOTAL** | ~131-188 j-h | **+77-119 j-h** | **~208-307 j-h** |

> ⚠️ Recoupement à éviter : les items en commun (pipeline L17, parser PDF contrat, CSRD, APIs SGE V25→V26.2) sont listés UNE seule fois côté audit 4. L'audit 5 ajoute uniquement ce qui est **spécifique à la dimension cockpit ouvert v2.0**.

---

## 15. Recommandations méthodologiques

### 15.1 Séquencement P0 doctrine v2.0

Sprint **M2-Δ-Partner-Hub** (~2-3 semaines, 8-12 j-h) :
1. ADR Partner Hub (3 modèles + RBAC 8 niveaux + endpoints partenaires authentifiés)
2. Modèles Pydantic + tables Alembic
3. Endpoints `/api/v1/partners` + `/api/v1/partner/*` (client + partenaire)
4. Source-guards permissions partenaires
5. Audit log accès partenaire (étendre `audit_log_service`)

Sprint **M2-Δ-Data-Status** (~3-5 j-h) :
1. Enum `DataStatus(StrEnum)` dans `backend/doctrine/`
2. Champ `data_status` sur entités cardinales
3. Propagation FE (`<DataStatusBadge />`)
4. Source-guard FE bloquant valeur sans `data_status`

Sprint **M2-Δ-Connectors-Meta** (~3-5 j-h) :
1. Tables `connectors` + `connector_runs` + `external_mappings`
2. Connecteur OPERAT (cf. audit mapping P0-4)
3. Endpoints `/api/v1/connectors`

### 15.2 Source-guards complémentaires v2.0

| Source-guard | Vérifie | Priorité |
|---|---|---|
| `test_partner_permission_required.py` | Endpoint `/api/v1/partner/*` exige `PartnerPermission` valide non expirée | P0 |
| `test_data_status_propagated.py` | KPI / facture / conso retournés portent un `data_status` ∈ 7 valeurs | P0 |
| `test_connector_runs_observability.py` | Chaque `connector.sync()` insère un `connector_run` avec `correlation_id` | P1 |
| `test_partner_audit_log.py` | Tout accès partenaire est journalisé dans `audit_log` | P0 |
| `test_api_v1_versioning.py` | Tous les routers utilisent `/api/v1/` prefix | P1 |
| `test_error_response_format.py` | Toutes les `HTTPException` retournent `{code, message, hint, correlation_id, blocking}` | P1 |
| `test_5_statuts_applicability.py` | `ApplicabilityStatus` contient les 5 valeurs canon | P1 |

### 15.3 Workflow

1. Audit READ-ONLY strict — aucun fichier modifié hormis ce livrable.
2. Pour chaque P0 : branche `claude/fix-vXX-...` distincte sur `claude/refonte-sol2`.
3. Phase 0 read-only → STOP gate → phases → DoD → atomic commit → source-guard test.
4. Workflow pre-merge : `/code-review:code-review` + `/simplify` + baseline FE ≥ 4 751 + BE ≥ 6 027.
5. Ré-exécuter cet audit tous les 30 jours.
6. **Toujours croiser les 5 audits** : code seul / Drive / mapping / doctrine v1.3 / **doctrine v2.0 (ce document)**.

---

## Annexes

### A. Synthèse en une phrase

> **PROMEOS sur `claude/refonte-sol2` porte ~55 % de la doctrine v2.0 « cockpit ouvert partenarial »** : fondations API + webhooks + connecteurs présentes, 18/23 tables data cible, 10/12 modules cœur, mais **Partner Hub à 0 %**, **enum `DataStatus` 7 valeurs absent**, **5e statut réglementaire `probably_*` non implémenté**, **Connectors Hub méta partiel**. ~22-32 j-h P0 supplémentaires pour atteindre 80 %.

### B. Score global combiné (5 audits cumulés)

| Doctrine | Couverture moyenne |
|---|---|
| v1.3 (5 verbes + patrimoine déclencheur + QA + DoD) | **~78 %** |
| v2.0 (interop + Partner Hub + 5/7 statuts + niveaux) | **~55 %** |
| **Synthèse pondérée** | **~70 %** |

✅ **Prêt pour démo CFO/DAF + pilote pré-prod**.
🟡 **Pas encore pour pilote payant Lite 6,9 k€** (gap Partner Hub + Pipeline L17 + 3 violations FE business logic + CACNC/CER).
🔵 **Loin de l'objectif Marketplace + SDK partenaires** (P2 ~30-50 j-h).

### C. Référentiel des 5 audits

1. `docs/audits/audit_readonly_promeos_scope_sans_acc_usage_steering.md` — code seul (22/05)
2. `docs/audits/audit_docs_drive_promeos_sans_acc.md` — extraction 6 docs Drive (22/05)
3. `docs/audits/audit_drive_vs_refonte_sol2_mapping.md` — mapping bidirectionnel par 5 verbes (23/05)
4. `docs/audits/audit_doctrine_patrimoine_declencheur_refonte_sol2.md` — doctrine v1.3 patrimoine + QA + DoD + promesse client (23/05)
5. **`docs/audits/audit_doctrine_cockpit_ouvert_refonte_sol2.md`** (ce document) — doctrine v2.0 cockpit ouvert + Partner Hub + interop 6 couches (23/05)

### D. Doctrine de référence

- Memory `project_promeos_vision_cockpit_patrimoine_ouvert_2026_05_23.md` (v2.0)
- Memory `project_promeos_vision_consolidee_v1_3_2026_05_08.md` (v1.3)
- `docs/adr/ADR-024-moteur-assujettissement.md` (Accepted 13/05/2026 — 5 évaluateurs, 4 statuts actuels)
- ADR Mois 1 : ADR-025→029 (architecture V4 Centre d'Action)
- `reference_patrimoine_parametrage_matrice_v1_2026_05_03.md` (~310 champs / 52 P0)

### E. Position ACC réaffirmée v2.0

> *« La vision actuelle peut rester sans ACC active dans le POC immédiat. En revanche, l'architecture doit être compatible avec une activation future : patrimoine + compteurs + courbes + contrats + partenaires + facturation + actions + preuves. »*

Confirme la position du 22/05/2026 (audit `audit_readonly_promeos_scope_sans_acc_usage_steering.md` §7.4) : ACC hors scope court terme, architecture data prête.

---

**Fin de l'audit cockpit ouvert v2.0** — branche `claude/refonte-sol2` @ `ade3d0a0` — 2026-05-23.
**Worktree** : `.claude/worktrees/audit-cockpit-ouvert/` (à nettoyer après lecture).
**Aucune modification de code n'a été effectuée pendant cet audit hormis ce livrable.**
