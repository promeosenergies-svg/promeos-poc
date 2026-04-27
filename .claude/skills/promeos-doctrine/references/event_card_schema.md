## 10. Modèle d'événement énergétique

Le produit vivant repose sur un moteur d'événements.

```ts
type SolEventCard = {
  id: string;
  event_type:
    | "consumption_drift"
    | "billing_anomaly"
    | "compliance_deadline"
    | "contract_renewal"
    | "market_window"
    | "data_quality_issue"
    | "flex_opportunity"
    | "asset_registry_issue"
    | "action_overdue";

  severity: "info" | "watch" | "warning" | "critical";
  title: string;
  narrative: string;

  impact: {
    value: number | null;
    unit: "€" | "kWh" | "MWh" | "kW" | "kVA" | "kgCO2e" | "days" | "%";
    period: "day" | "week" | "month" | "year" | "contract" | "deadline";
  };

  source: {
    system: "Enedis" | "GRDF" | "invoice" | "GTB" | "IoT" | "RegOps" | "EPEX" | "manual" | "benchmark";
    last_updated_at: string;
    confidence: "high" | "medium" | "low";
  };

  action: {
    label: string;
    route: string;
    owner_role?: "DAF" | "Energy Manager" | "Site Manager" | "Admin" | "Operator";
  };

  linked_assets: {
    org_id: string;
    portfolio_id?: string;
    site_ids?: string[];
    building_ids?: string[];
    meter_ids?: string[];
    invoice_ids?: string[];
    contract_ids?: string[];
  };
};
```

Un événement PROMEOS est valide seulement s'il répond :

- quel fait l'a déclenché ?
- quel périmètre est concerné ?
- quel impact est estimé ?
- quelle action est possible ?
- quelle source le prouve ?
- quel niveau de confiance est associé ?

---

