# V66 — Billing Routing Map : Routes UI ↔ Endpoints API

> Date : 2026-02-23  |  Préfixe API : `/api/billing`

---

## Routes UI → Endpoints

| Route UI | Composant | Endpoint API | Méthode | Org scoped V66 |
|----------|-----------|-------------|---------|----------------|
| `/bill-intel` — liste factures | `BillIntelPage.jsx` | `/billing/invoices` | GET | ✓ |
| `/bill-intel` — anomalies insights | `BillIntelPage.jsx` | `/billing/insights` | GET | ✓ |
| `/bill-intel` — KPIs summary | `BillIntelPage.jsx` | `/billing/summary` | GET | ✓ |
| `/bill-intel` — import CSV | `BillIntelPage.jsx` | `/billing/import-csv` | POST | ✓ |
| `/bill-intel` — import PDF *(V66 NEW)* | `BillIntelPage.jsx` | `/billing/import-pdf` | POST | ✓ |
| `/bill-intel` — audit tout | `BillIntelPage.jsx` | `/billing/audit-all` | POST | ✓ |
| `/bill-intel` — audit facture | `BillIntelPage.jsx` | `/billing/audit/{id}` | POST | ✓ |
| `/bill-intel` — résoudre insight | `BillIntelPage.jsx` | `/billing/insights/{id}/resolve` | POST | ✓ |
| `/bill-intel` — "Créer action" CTA *(V66 NEW)* | `BillIntelPage.jsx` | `/actions` (source_type=manual) | POST | via auth |
| `/anomalies` — billing *(V66 NEW)* | `AnomaliesPage.jsx` | `/billing/anomalies-scoped` | GET | ✓ |
| Site360 onglet Factures | `SiteBillingMini.jsx` | `/billing/site/{siteId}` | GET | ✓ (site-level) |
| — | `BillIntelPage.jsx` | `/billing/contracts` | GET | ✓ |
| — | internal | `/billing/import/batches` | GET | ✓ |
| — | internal | `/billing/rules` | GET | static (no scope) |

---

## Endpoints par fichier backend

### `routes/billing.py`

```
POST   /api/billing/contracts            ← ContractCreate + org scope
GET    /api/billing/contracts            ← org scope (join chain)
POST   /api/billing/import-csv          ← org_id param → resolve_org_id
GET    /api/billing/import/batches      ← org scope
POST   /api/billing/invoices            ← site check via _org_sites_query
POST   /api/billing/audit/{invoice_id}  ← org check invoice ownership
POST   /api/billing/audit-all           ← org scope
GET    /api/billing/summary             ← org scope
GET    /api/billing/insights            ← org scope
PATCH  /api/billing/insights/{id}       ← org scope
POST   /api/billing/insights/{id}/resolve ← org scope
GET    /api/billing/invoices            ← org scope
GET    /api/billing/site/{site_id}      ← org scope
POST   /api/billing/import-pdf         ← V66 NEW — org scope + site check
GET    /api/billing/anomalies-scoped   ← V66 NEW — org scope
GET    /api/billing/rules              ← static, no scope
POST   /api/billing/seed-demo         ← admin, no scope
```

---

## Chaîne d'org scoping (modèles sans org_id direct)

```
EnergyInvoice.site_id
  → Site.portefeuille_id
    → Portefeuille.entite_juridique_id
      → EntiteJuridique.organisation_id  ← effectif org_id ici
```

**Helper** : `_org_sites_query(db, ModelClass, effective_org_id)` encapsule ce join.

---

## Wrappers frontend (api.js)

| Fonction | Endpoint | V66 Status |
|---------|---------|------------|
| `getBillingContracts()` | GET /billing/contracts | ✓ existant |
| `getBillingSummary()` | GET /billing/summary | ✓ existant |
| `getBillingInsights(params)` | GET /billing/insights | ✓ existant |
| `getBillingInvoices(params)` | GET /billing/invoices | ✓ existant |
| `getSiteBilling(siteId)` | GET /billing/site/{siteId} | ✓ existant |
| `importInvoicesCsv(file, orgId)` | POST /billing/import-csv | ✓ existant |
| `auditInvoice(id)` | POST /billing/audit/{id} | ✓ existant |
| `auditAllInvoices()` | POST /billing/audit-all | ✓ existant |
| `resolveInsight(id, notes)` | POST /billing/insights/{id}/resolve | ✓ existant |
| `patchInsight(id, data)` | PATCH /billing/insights/{id} | ✓ existant |
| `getImportBatches(orgId)` | GET /billing/import/batches | ✓ existant |
| `seedBillingDemo()` | POST /billing/seed-demo | ✓ existant |
| `importInvoicesPdf(siteId, file)` | POST /billing/import-pdf | **V66 NEW** |
| `createActionFromBillingInsight(id, title, siteId)` | POST /actions | **V66 NEW** |
| `getBillingAnomaliesScoped()` | GET /billing/anomalies-scoped | **V66 NEW** |
