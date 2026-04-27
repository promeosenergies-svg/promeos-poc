## 8. Doctrine KPI

Aucun KPI PROMEOS ne peut exister sans fiche de définition.

### 8.1 Fiche KPI obligatoire

Chaque KPI doit documenter :

```yaml
kpi_id: annual_consumption_mwh
label: Consommation annuelle
unit: MWh
formula: sum(consumption_kwh) / 1000
source: consumption_unified_service
scope: site | portfolio | organization
period: rolling_12_months | calendar_year | contract_year
freshness: daily | monthly | on_import
confidence_rule: high_if_full_period_and_primary_source
owner: data_product
used_in:
  - cockpit
  - portfolio
  - site
  - conformity
  - bill_intelligence
```

### 8.2 KPIs prioritaires du cockpit

Le cockpit ne doit pas afficher 15 indicateurs. Les KPIs prioritaires sont :

1. consommation ;
2. coût ;
3. trajectoire / objectif ;
4. qualité data ;
5. actions ouvertes ;
6. risque conformité ;
7. anomalies facture ou dérives.

Les autres indicateurs doivent être accessibles en profondeur, pas en premier niveau.

---

