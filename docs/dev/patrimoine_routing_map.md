# Patrimoine — Routing Map

## Frontend Routes

| Route | Page | Lazy-load | Guard |
|-------|------|-----------|-------|
| `/patrimoine` | `Patrimoine.jsx` | `import('./pages/Patrimoine')` | NavRegistry (donnees, expertOnly) |
| `/sites/:id` | `Site360.jsx` | `import('./pages/Site360')` | — |
| `/sites-legacy/:id` | `SiteDetail.jsx` | `import('./pages/SiteDetail')` | — (legacy, preserved) |

## Backend API (`/api/patrimoine`)

### Staging Pipeline (DIAMANT)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/import/template` | Download CSV/XLSX import template |
| GET | `/import/template/columns` | List canonical columns + mappings |
| POST | `/staging/import` | Upload file, create staging batch |
| GET | `/staging/{batch_id}/summary` | Batch summary + quality score |
| GET | `/staging/{batch_id}/rows` | Paginated staging rows |
| GET | `/staging/{batch_id}/issues` | Quality findings |
| PUT | `/staging/{batch_id}/fix` | Apply single fix |
| PUT | `/staging/{batch_id}/fix/bulk` | Apply multiple fixes |
| POST | `/staging/{batch_id}/autofix` | Auto-fix all auto-fixable issues |
| POST | `/staging/{batch_id}/validate` | Run quality gate |
| POST | `/staging/{batch_id}/activate` | Activate batch into production |
| GET | `/staging/{batch_id}/result` | Activation result |
| POST | `/staging/{batch_id}/abandon` | Abandon batch |
| GET | `/staging/{batch_id}/export/report.csv` | Export quality report |

### Sites CRUD

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sites` | List sites (filterable) |
| GET | `/sites/export.csv` | Export sites CSV |
| GET | `/sites/{site_id}` | Site detail |
| PATCH | `/sites/{site_id}` | Update site fields |
| POST | `/sites/{site_id}/archive` | Soft-archive site |
| POST | `/sites/{site_id}/restore` | Restore archived site |
| POST | `/sites/merge` | Merge two sites |

### Compteurs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sites/{site_id}/compteurs` | List compteurs for site |
| PATCH | `/compteurs/{compteur_id}` | Update compteur |
| POST | `/compteurs/{compteur_id}/move` | Move compteur to another site |
| POST | `/compteurs/{compteur_id}/detach` | Detach compteur from site |

### Contrats

| Method | Path | Description |
|--------|------|-------------|
| GET | `/contracts` | List contracts (filterable) |
| POST | `/contracts` | Create contract |
| PATCH | `/contracts/{contract_id}` | Update contract |
| DELETE | `/contracts/{contract_id}` | Delete contract |

### Delivery Points

| Method | Path | Description |
|--------|------|-------------|
| GET | `/sites/{site_id}/delivery-points` | List PRM/PCE for site |

### KPIs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/kpis` | Aggregated patrimoine KPIs |

### Demo

| Method | Path | Description |
|--------|------|-------------|
| POST | `/demo/load` | Load demo patrimoine data |

## Cross-Module CTAs

```
CommandCenter ─── /patrimoine ──────────► Patrimoine.jsx
              └── /sites/{id} ─────────► Site360.jsx

Cockpit ────────── /sites/{id} ────────► Site360.jsx

ImpactDecisionPanel ── /patrimoine ────► Patrimoine.jsx

TertiaireDashboard ── /patrimoine ─────► Patrimoine.jsx

TertiaireWizard ── ?site_id={id} ──────► prefill buildings

Site360 ── back button ── /patrimoine ─► Patrimoine.jsx
```

## Frontend API Functions (35 exports)

### Staging
`stagingImport`, `stagingSummary`, `stagingRows`, `stagingIssues`, `stagingValidate`, `stagingFix`, `stagingAutofix`, `stagingActivate`, `stagingResult`, `stagingAbandon`, `stagingExportReport`

### Sites
`patrimoineSites`, `patrimoineSiteDetail`, `patrimoineSiteUpdate`, `patrimoineSiteArchive`, `patrimoineSiteRestore`, `patrimoineSiteMerge`, `patrimoineSitesExport`

### Compteurs
`patrimoineCompteurs`, `patrimoineCompteurUpdate`, `patrimoineCompteurMove`, `patrimoineCompteurDetach`

### Contrats
`patrimoineContracts`, `patrimoineContractCreate`, `patrimoineContractUpdate`, `patrimoineContractDelete`

### Autres
`patrimoineDeliveryPoints`, `patrimoineKpis`, `getImportTemplate`, `getImportTemplateColumns`, `loadPatrimoineDemo`
