# Patrimoine — Chaine de Valeur

## Hierarchie des donnees

```
Organisation
  └─ EntiteJuridique (siren, siret, naf_code)
       └─ Portefeuille
            └─ Site (nom, type, ville, surface_m2, tertiaire_area_m2, actif)
                 ├─ Batiment (surface_m2, annee_construction, cvc_power_kw)
                 ├─ Compteur (type: elec/gaz/eau, numero_serie)
                 ├─ Meter (meter_id PRM/PCE, energy_vector, subscribed_power_kva)
                 └─ DeliveryPoint (code, energy_type, status)
```

## Modules consommateurs (tous en lecture seule sur Patrimoine)

### Consommation
- **Lien** : `Meter.site_id` → Site, `MeterReading.meter_id` → Meter
- **Granularite** : 15min, 30min, horaire, journalier, mensuel
- **Import** : via `DataImportJob` (CSV/JSON, SHA-256 dedup)

### Facturation (Bill Intelligence)
- **Lien** : `EnergyContract.site_id` → Site, `EnergyInvoice.site_id` → Site
- **Structure** : Invoice → InvoiceLine → ConceptAllocation
- **Anomalies** : `BillingInsight` (overcharge, price_drift, duplicate, etc.)

### Conformite
- **Lien** : `Obligation.site_id` → Site, `ComplianceFinding.site_id` → Site
- **Reglementations** : BACS, Decret Tertiaire, APER
- **Preuves** : `Evidence.site_id` → Site

### Tertiaire / OPERAT
- **Lien** : `TertiaireEfa.site_id` → Site, `TertiaireEfaBuilding.building_id` → Batiment
- **Wizard** : selectionne des batiments existants via `GET /api/tertiaire/catalog`
- **Si 0 batiment** : CTA "Completer le patrimoine" + deep-link `/patrimoine`

### Actions
- **Lien** : `ActionItem.site_id` → Site (nullable pour actions org-level)
- **Sources** : compliance, consumption, billing, purchase, lever_engine
- **Dedup** : `idempotency_key` unique

### Achats
- **Lien** : `PurchaseAssumptionSet.site_id` → Site
- **Scenarios** : FIXE, INDEXE, SPOT par site

### Monitoring
- **Lien** : `MonitoringSnapshot.site_id` → Site, `MonitoringAlert.site_id` → Site
- **KPIs** : pmax, load_factor, peak_to_average, data_quality_score

### KB / Memobox
- **Lien indirect** : Site.naf_code → KBMappingCode → KBArchetype
- **Preuves OPERAT** : `TertiaireProofArtifact.efa_id` → TertiaireEfa → Site

## Verification : zero orphan creation

| Module | Cree des sites/batiments ? | Methode |
|--------|---------------------------|---------|
| Consommation | NON | Lecture Meter.site_id |
| Facturation | NON | Lecture EnergyContract.site_id |
| Conformite | NON | Lecture Obligation.site_id |
| Tertiaire | NON | Lecture TertiaireEfaBuilding.building_id |
| Actions | NON | Lecture ActionItem.site_id |
| Achats | NON | Lecture PurchaseAssumptionSet.site_id |
| Monitoring | NON | Lecture MonitoringSnapshot.site_id |

**Conclusion** : tous les modules consomment le patrimoine en lecture seule. Aucun ne recree de site ou batiment.
