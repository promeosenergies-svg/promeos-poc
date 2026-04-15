# DATABASE MAP - PROMEOS POC

**Date**: 2026-02-13
**Engine**: SQLite (dev) - `backend/data/promeos.db`
**ORM**: SQLAlchemy 2.x
**Total Tables**: 62

---

## Schema hierarchique

```
Organisation (organisations)
  |-- EntiteJuridique (entites_juridiques) [1:N]
  |     |-- OrgEntiteLink (org_entite_links)
  |     |-- Portefeuille (portefeuilles) [1:N]
  |           |-- PortfolioEntiteLink (portfolio_entite_links)
  |           |-- Site (sites) [1:N]  <-- CORE
  |                 |-- Batiment (batiments) [1:N]
  |                 |-- Compteur (compteurs) [1:N]
  |                 |     |-- Consommation (consommations) [1:N]
  |                 |-- Usage (usages) [1:N]
  |                 |-- Obligation (obligations) [1:N]
  |                 |-- Evidence (evidences) [1:N]
  |                 |-- Alerte (alertes) [1:N]
  |                 |-- DataPoint (datapoints) [1:N]
  |                 |-- RegAssessment (reg_assessments) [1:1 cached]
  |                 |-- ComplianceFinding (compliance_findings) [1:N]
  |                 |-- SegmentationProfile (segmentation_profiles) [1:1]
  |                 |-- SiteOperatingSchedule (site_operating_schedules) [1:1]
  |                 |-- SiteTariffProfile (site_tariff_profiles) [1:1]
  |                 |-- ConsumptionInsight (consumption_insights) [1:N]
  |                 |-- IntakeSession (intake_sessions) [1:N]
  |
  |-- User (users) [1:N]
  |     |-- UserOrgRole (user_org_roles) [1:N]
  |           |-- UserScope (user_scopes) [1:N]
  |
  |-- AuditLog (audit_logs) [1:N]
  |
  |-- EnergyContract (energy_contracts) [1:N]
  |     |-- EnergyInvoice (energy_invoices) [1:N]
  |           |-- EnergyInvoiceLine (energy_invoice_lines) [1:N]
  |           |-- BillingInsight (billing_insights) [1:N]
  |
  |-- BillingImportBatch (billing_import_batches)
  |-- PurchaseAssumptionSet (purchase_assumption_sets)
  |-- PurchasePreference (purchase_preferences)
  |-- PurchaseScenarioResult (purchase_scenario_results)
  |-- ActionItem (action_items) [cross-briques]
  |-- ActionSyncBatch (action_sync_batches)
  |-- NotificationEvent (notification_events) [cross-briques]
  |-- NotificationBatch (notification_batches)
  |-- NotificationPreference (notification_preferences)

Tables independantes:
  |-- RegSourceEvent (reg_source_events)     # Veille reglementaire (RSS)
  |-- AiInsight (ai_insights)                # AI agent outputs
  |-- JobOutbox (job_outbox)                 # Async job queue
  |-- ComplianceRunBatch (compliance_run_batches)

Knowledge Base (sub-app):
  |-- KBVersion (kb_version)
  |-- KBArchetype (kb_archetype)
  |-- KBMappingCode (kb_mapping_code)
  |-- KBAnomalyRule (kb_anomaly_rule)
  |-- KBRecommendation (kb_recommendation)
  |-- KBTaxonomy (kb_taxonomy)

Energy sub-domain:
  |-- Meter (meter)
  |-- MeterReading (meter_reading)
  |-- DataImportJob (data_import_job)
  |-- UsageProfile (usage_profile)
  |-- Anomaly (anomaly)
  |-- Recommendation (recommendation)
  |-- MonitoringSnapshot (monitoring_snapshot)
  |-- MonitoringAlert (monitoring_alert)

Patrimoine DIAMANT (staging):
  |-- StagingBatch (staging_batches)
  |-- StagingSite (staging_sites)
  |-- StagingCompteur (staging_compteurs)
  |-- QualityFinding (quality_findings)

Smart Intake:
  |-- IntakeSession (intake_sessions)
  |-- IntakeAnswer (intake_answers)
  |-- IntakeFieldOverride (intake_field_overrides)
```

---

## Tables par fichier model

| # | Fichier | Tables | Noms de table |
|---|---------|--------|---------------|
| 1 | organisation.py | 1 | organisations |
| 2 | entite_juridique.py | 1 | entites_juridiques |
| 3 | portefeuille.py | 1 | portefeuilles |
| 4 | site.py | 1 | sites |
| 5 | batiment.py | 1 | batiments |
| 6 | compteur.py | 1 | compteurs |
| 7 | consommation.py | 1 | consommations |
| 8 | usage.py | 1 | usages |
| 9 | conformite.py | 1 | obligations |
| 10 | evidence.py | 1 | evidences |
| 11 | alerte.py | 1 | alertes |
| 12 | datapoint.py | 1 | datapoints |
| 13 | reg_assessment.py | 1 | reg_assessments |
| 14 | reg_source_event.py | 1 | reg_source_events |
| 15 | ai_insight.py | 1 | ai_insights |
| 16 | job_outbox.py | 1 | job_outbox |
| 17 | segmentation.py | 1 | segmentation_profiles |
| 18 | compliance_finding.py | 1 | compliance_findings |
| 19 | compliance_run_batch.py | 1 | compliance_run_batches |
| 20 | site_operating_schedule.py | 1 | site_operating_schedules |
| 21 | site_tariff_profile.py | 1 | site_tariff_profiles |
| 22 | consumption_insight.py | 1 | consumption_insights |
| 23 | iam.py | 4 | users, user_org_roles, user_scopes, audit_logs |
| 24 | billing_models.py | 5 | energy_contracts, energy_invoices, energy_invoice_lines, billing_insights, billing_import_batches |
| 25 | purchase_models.py | 3 | purchase_assumption_sets, purchase_preferences, purchase_scenario_results |
| 26 | action_item.py | 2 | action_items, action_sync_batches |
| 27 | notification.py | 3 | notification_events, notification_batches, notification_preferences |
| 28 | kb_models.py | 6 | kb_version, kb_archetype, kb_mapping_code, kb_anomaly_rule, kb_recommendation, kb_taxonomy |
| 29 | energy_models.py | 8 | meter, meter_reading, data_import_job, usage_profile, anomaly, recommendation, monitoring_snapshot, monitoring_alert |
| 30 | patrimoine.py | 6 | org_entite_links, portfolio_entite_links, staging_batches, staging_sites, staging_compteurs, quality_findings |
| 31 | intake.py | 3 | intake_sessions, intake_answers, intake_field_overrides |

**Total**: 31 fichiers model, 62 tables

---

## Enums (36 enums dans enums.py)

| Categorie | Enums |
|-----------|-------|
| Sites & Assets | TypeSite (11 vals), TypeCompteur (3), SeveriteAlerte (3), TypeUsage (7) |
| Conformite | StatutConformite (4), TypeObligation (3), TypeEvidence (8), StatutEvidence (4) |
| RegOps | ParkingType (5), OperatStatus (5), EnergyVector (4), SourceType (4), JobType (4), JobStatus (4), RegStatus (6), Severity (4), Confidence (3), InsightType (5), RegulationType (4), Typologie (11) |
| Bill Intelligence | BillingEnergyType (2), InvoiceLineType (4), BillingInvoiceStatus (5), InsightStatus (4) |
| Achat Energie | PurchaseStrategy (3), PurchaseRecoStatus (3) |
| Actions Hub | ActionSourceType (4), ActionStatus (5) |
| Notifications | NotificationSeverity (3), NotificationStatus (3), NotificationSourceType (5) |
| IAM | UserRole (11), ScopeLevel (3), PermissionAction (6) |
| Patrimoine | StagingStatus (4), ImportSourceType (6), QualityRuleSeverity (3) |
| Smart Intake | IntakeSessionStatus (4), IntakeMode (4), IntakeSource (5) |

---

## Table Site (table principale - 30+ colonnes)

La table `sites` est la table centrale avec les champs reglementaires:

| Colonne | Type | Usage reglementaire |
|---------|------|---------------------|
| surface_m2 | Float | Base: surface totale |
| tertiaire_area_m2 | Float | Decret Tertiaire: seuil 1000m2 |
| parking_area_m2 | Float | APER: seuil parking |
| roof_area_m2 | Float | APER: seuil toiture |
| parking_type | Enum(ParkingType) | APER: type parking |
| operat_status | Enum(OperatStatus) | Decret Tertiaire: declaration |
| annual_kwh_total | Float | Decret Tertiaire: conso annuelle |
| is_multi_occupied | Boolean | Decret Tertiaire: multi-occupant |
| naf_code | String(5) | Classification NAF |
| siret | String(14) | Identification |

Batiment `cvc_power_kw` (Float) --> BACS: seuil 290kW
