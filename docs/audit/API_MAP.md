# API MAP - PROMEOS POC

**Date**: 2026-02-13
**Total Endpoints**: ~196 (30 routers + 2 app-level + sub-apps kb/bill)

---

## Vue d'ensemble par router

| # | Prefix | Tag | Fichier | Endpoints | Auth |
|---|--------|-----|---------|-----------|------|
| 1 | `/api/auth` | Auth | auth.py | 9 | Public (login) + JWT |
| 2 | `/api/admin` | Admin Users | admin_users.py | 9 | JWT + admin |
| 3 | `/api/billing` | Bill Intelligence V2 | billing.py | 15 | JWT |
| 4 | `/api/purchase` | Achat Energie | purchase.py | 14 | JWT |
| 5 | `/api/kb` | Knowledge Base | kb_usages.py | 9 | JWT |
| 6 | `/api/compliance` | Compliance | compliance.py | 8 | JWT |
| 7 | `/api/intake` | Smart Intake | intake.py | 8 | JWT |
| 8 | `/api/energy` | Energy | energy.py | 7 | JWT |
| 9 | `/api/notifications` | Notifications | notifications.py | 7 | JWT |
| 10 | `/api/sites` | Sites | sites.py | 6 | JWT |
| 11 | `/api/actions` | Actions | actions.py | 6 | JWT |
| 12 | `/api/demo` | Demo Mode | demo.py | 6 | JWT |
| 13 | `/api/monitoring` | Monitoring | monitoring.py | 6 | JWT |
| 14 | `/api/ai` | AI Agents | ai_route.py | 5 | JWT |
| 15 | `/api/site` | Site Config | site_config.py | 4 | JWT |
| 16 | `/api/regops` | RegOps | regops.py | 4 | JWT |
| 17 | `/api/watchers` | Watchers | watchers_route.py | 4 | JWT |
| 18 | `/api/consumption` | Consumption Diagnostic | consumption_diagnostic.py | 4 | JWT |
| 19 | `/api/patrimoine` | Patrimoine | patrimoine.py | 9 | JWT |
| 20 | `/api/connectors` | Connectors | connectors_route.py | 3 | JWT |
| 21 | `/api/compteurs` | Compteurs | compteurs.py | 3 | JWT |
| 22 | `/api/alertes` | Alertes | alertes.py | 3 | JWT |
| 23 | `/api/segmentation` | Segmentation | segmentation.py | 3 | JWT |
| 24 | `/api/onboarding` | Onboarding | onboarding.py | 3 | JWT |
| 25 | `/api` | Cockpit | cockpit.py | 2 | JWT |
| 26 | `/api/guidance` | Guidance | guidance.py | 2 | JWT |
| 27 | `/api/import` | Import | import_sites.py | 2 | JWT |
| 28 | `/api/reports` | Reports | reports.py | 2 | JWT |
| 29 | `/api/dashboard` | Dashboard 2min | dashboard_2min.py | 1 | JWT |
| 30 | `/api/consommations` | Consommations | consommations.py | 1 | JWT |
| - | `/` | App | main.py | 2 | Public |
| - | `/api/kb/*` | KB (sub-app) | app/kb/router.py | 16 | JWT |
| - | `/api/bill/*` | Bill (sub-app) | app/bill_intelligence/router.py | 13 | JWT |

---

## Endpoints detailles par prefixe

### `/api/auth` - Auth (9 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Login (email + password) -> JWT token |
| POST | `/api/auth/refresh` | Refresh JWT token |
| GET | `/api/auth/me` | Current user info |
| POST | `/api/auth/logout` | Logout (invalidate token) |
| PUT | `/api/auth/password` | Change password |
| POST | `/api/auth/switch-org` | Switch organisation context |
| POST | `/api/auth/impersonate` | Impersonate another user (admin) |
| POST | `/api/auth/reset-demo` | Reset demo data |
| GET | `/api/auth/audit` | Get audit log entries |

### `/api/admin` - Admin Users (9 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/users` | List all users |
| POST | `/api/admin/users` | Create new user |
| GET | `/api/admin/users/{user_id}` | Get user detail |
| PATCH | `/api/admin/users/{user_id}` | Update user |
| PUT | `/api/admin/users/{user_id}/role` | Assign role to user |
| PUT | `/api/admin/users/{user_id}/scopes` | Assign scopes to user |
| DELETE | `/api/admin/users/{user_id}` | Delete user |
| GET | `/api/admin/roles` | List available roles + permissions |
| GET | `/api/admin/users/{user_id}/effective-access` | Get effective access for user |

### `/api/billing` - Bill Intelligence V2 (15 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/billing/contracts` | Create energy contract |
| GET | `/api/billing/contracts` | List contracts |
| POST | `/api/billing/import-csv` | Import invoices from CSV |
| GET | `/api/billing/import/batches` | List import batches |
| POST | `/api/billing/invoices` | Create invoice manually |
| POST | `/api/billing/audit/{invoice_id}` | Audit single invoice |
| POST | `/api/billing/audit-all` | Audit all invoices |
| GET | `/api/billing/summary` | Billing summary KPIs |
| GET | `/api/billing/insights` | List billing anomaly insights |
| PATCH | `/api/billing/insights/{insight_id}` | Update insight status |
| POST | `/api/billing/insights/{insight_id}/resolve` | Resolve insight |
| GET | `/api/billing/invoices` | List invoices with filters |
| GET | `/api/billing/site/{site_id}` | Billing summary for site |
| GET | `/api/billing/rules` | List audit rules |
| POST | `/api/billing/seed-demo` | Seed demo billing data |

### `/api/purchase` - Achat Energie (14 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/purchase/estimate/{site_id}` | Price estimate for site |
| GET | `/api/purchase/assumptions/{site_id}` | Get assumptions |
| PUT | `/api/purchase/assumptions/{site_id}` | Update assumptions |
| GET | `/api/purchase/preferences` | Get purchase preferences |
| PUT | `/api/purchase/preferences` | Update purchase preferences |
| GET | `/api/purchase/renewals` | List contract renewals |
| GET | `/api/purchase/actions` | List purchase actions |
| POST | `/api/purchase/compute` | Compute scenarios (all sites) |
| POST | `/api/purchase/compute/{site_id}` | Compute scenarios (single site) |
| GET | `/api/purchase/results` | Get scenario results |
| GET | `/api/purchase/results/{site_id}` | Get results for site |
| GET | `/api/purchase/history/{site_id}` | Get purchase history |
| PATCH | `/api/purchase/results/{result_id}/accept` | Accept scenario result |
| POST | `/api/purchase/seed-demo` | Seed demo data |

### `/api/compliance` - Compliance (8 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/compliance/recompute` | Recompute compliance for all sites |
| GET | `/api/compliance/summary` | Compliance summary KPIs |
| GET | `/api/compliance/sites` | List sites with compliance status |
| POST | `/api/compliance/recompute-rules` | Recompute from YAML rules |
| GET | `/api/compliance/rules` | List compliance rules |
| GET | `/api/compliance/findings` | List compliance findings |
| PATCH | `/api/compliance/findings/{finding_id}` | Update finding status |
| GET | `/api/compliance/batches` | List compliance run batches |

### `/api/intake` - Smart Intake (8 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/intake/{site_id}/questions` | Generate intake questions for site |
| POST | `/api/intake/{site_id}/answers` | Submit answer |
| POST | `/api/intake/{site_id}/apply-suggestions` | Apply prefilled suggestions |
| POST | `/api/intake/{site_id}/demo-autofill` | Demo autofill all fields |
| POST | `/api/intake/{site_id}/complete` | Apply + complete session |
| GET | `/api/intake/session/{session_id}` | Get session detail |
| POST | `/api/intake/bulk` | Bulk override for scope |
| DELETE | `/api/intake/demo/purge` | Purge demo sessions |

### `/api/patrimoine` - Patrimoine DIAMANT (9 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/patrimoine/staging/import` | Import CSV to staging |
| POST | `/api/patrimoine/staging/import-invoices` | Import invoices to staging |
| GET | `/api/patrimoine/staging/{batch_id}/summary` | Staging batch summary |
| POST | `/api/patrimoine/staging/{batch_id}/validate` | Validate staging batch |
| PUT | `/api/patrimoine/staging/{batch_id}/fix` | Fix staging issues |
| DELETE | `/api/patrimoine/staging/{batch_id}` | Abandon staging batch |
| POST | `/api/patrimoine/staging/{batch_id}/activate` | Activate (create final entities) |
| POST | `/api/patrimoine/{portfolio_id}/sync` | Incremental sync |
| POST | `/api/patrimoine/demo/load` | Load demo patrimoine |

### `/api/sites` - Sites (6 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/sites` | Create site |
| GET | `/api/sites` | List sites |
| GET | `/api/sites/{site_id}` | Get site detail |
| GET | `/api/sites/{site_id}/stats` | Site stats |
| GET | `/api/sites/{site_id}/compliance` | Site compliance |
| GET | `/api/sites/{site_id}/guardrails` | Site guardrails |

### `/api/energy` - Energy (7 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/energy/meters` | Create meter |
| GET | `/api/energy/meters` | List meters |
| POST | `/api/energy/import/upload` | Upload meter data |
| GET | `/api/energy/import/jobs` | List import jobs |
| POST | `/api/energy/analysis/run` | Run energy analysis |
| GET | `/api/energy/analysis/summary` | Analysis summary |
| POST | `/api/energy/demo/generate` | Generate demo data |

### `/api/monitoring` - Monitoring (6 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/monitoring/kpis` | Monitoring KPIs |
| POST | `/api/monitoring/run` | Run monitoring cycle |
| GET | `/api/monitoring/snapshots` | List snapshots |
| GET | `/api/monitoring/alerts` | List alerts |
| POST | `/api/monitoring/alerts/{alert_id}/ack` | Acknowledge alert |
| POST | `/api/monitoring/alerts/{alert_id}/resolve` | Resolve alert |

### `/api/notifications` - Notifications (7 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/notifications/sync` | Sync notifications |
| GET | `/api/notifications/list` | List notifications |
| GET | `/api/notifications/summary` | Summary counts |
| PATCH | `/api/notifications/{event_id}` | Update notification |
| GET | `/api/notifications/preferences` | Get preferences |
| PUT | `/api/notifications/preferences` | Update preferences |
| GET | `/api/notifications/batches` | List notification batches |

### `/api/actions` - Actions Hub (6 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/actions/sync` | Sync actions from briques |
| GET | `/api/actions/list` | List all actions |
| GET | `/api/actions/summary` | Actions summary |
| PATCH | `/api/actions/{action_id}` | Update action status |
| GET | `/api/actions/batches` | List sync batches |
| GET | `/api/actions/export.csv` | Export actions CSV |

### `/api/kb` - Knowledge Base (9 endpoints)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/kb/archetypes` | List archetypes |
| GET | `/api/kb/archetypes/{code}` | Get archetype |
| GET | `/api/kb/archetypes/by-naf/{naf_code}` | Get archetype by NAF |
| GET | `/api/kb/rules` | List anomaly rules |
| GET | `/api/kb/recommendations` | List recommendations |
| GET | `/api/kb/search` | Search KB |
| GET | `/api/kb/provenance/{item_type}/{code}` | Get provenance |
| GET | `/api/kb/stats` | KB statistics |
| POST | `/api/kb/reload` | Reload KB from files |

### Autres prefixes (endpoints restants)

| Method | Path | Prefix | Description |
|--------|------|--------|-------------|
| GET | `/api/regops/site/{site_id}` | regops | Fresh evaluation |
| GET | `/api/regops/site/{site_id}/cached` | regops | Cached evaluation |
| POST | `/api/regops/recompute` | regops | Trigger recompute |
| GET | `/api/regops/dashboard` | regops | RegOps dashboard |
| GET | `/api/ai/site/{site_id}/explain` | ai | AI explanation |
| GET | `/api/ai/site/{site_id}/recommend` | ai | AI recommendations |
| GET | `/api/ai/site/{site_id}/data-quality` | ai | AI data quality |
| GET | `/api/ai/org/brief` | ai | AI exec brief |
| GET | `/api/ai/insights` | ai | List AI insights |
| GET | `/api/site/{site_id}/schedule` | site_config | Get schedule |
| PUT | `/api/site/{site_id}/schedule` | site_config | Update schedule |
| GET | `/api/site/{site_id}/tariff` | site_config | Get tariff |
| PUT | `/api/site/{site_id}/tariff` | site_config | Update tariff |
| GET | `/api/connectors/list` | connectors | List connectors |
| POST | `/api/connectors/{name}/test` | connectors | Test connector |
| POST | `/api/connectors/{name}/sync` | connectors | Sync connector |
| GET | `/api/watchers/list` | watchers | List watchers |
| POST | `/api/watchers/{name}/run` | watchers | Run watcher |
| GET | `/api/watchers/events` | watchers | List events |
| PATCH | `/api/watchers/events/{event_id}/review` | watchers | Review event |
| GET | `/api/consumption/insights` | consumption | List insights |
| GET | `/api/consumption/site/{site_id}` | consumption | Site diagnostic |
| POST | `/api/consumption/diagnose` | consumption | Run diagnostic |
| POST | `/api/consumption/seed-demo` | consumption | Seed demo data |
| GET | `/api/segmentation/questions` | segmentation | Questions |
| POST | `/api/segmentation/answers` | segmentation | Submit answers |
| GET | `/api/segmentation/profile` | segmentation | Get profile |
| POST | `/api/onboarding` | onboarding | Create org+sites |
| POST | `/api/onboarding/import-csv` | onboarding | Import from CSV |
| GET | `/api/onboarding/status` | onboarding | Onboarding status |
| GET | `/api/cockpit` | cockpit | Cockpit KPIs |
| GET | `/api/portefeuilles` | cockpit | List portefeuilles |
| GET | `/api/dashboard/2min` | dashboard | Dashboard 2 minutes |
| GET | `/api/guidance/action-plan` | guidance | Suggested actions |
| GET | `/api/guidance/readiness` | guidance | Readiness score |
| GET | `/api/import/template` | import | CSV template |
| POST | `/api/import/sites` | import | Import CSV |
| POST | `/api/demo/enable` | demo | Enable demo |
| POST | `/api/demo/disable` | demo | Disable demo |
| GET | `/api/demo/status` | demo | Demo status |
| POST | `/api/demo/seed` | demo | Seed demo data |
| GET | `/api/demo/templates` | demo | List templates |
| GET | `/api/demo/templates/{template_id}` | demo | Get template |
| GET | `/api/alertes` | alertes | List alertes |
| GET | `/api/alertes/{alerte_id}` | alertes | Get alerte |
| PATCH | `/api/alertes/{alerte_id}/resolve` | alertes | Resolve alerte |
| POST | `/api/compteurs` | compteurs | Create compteur |
| GET | `/api/compteurs` | compteurs | List compteurs |
| GET | `/api/compteurs/{compteur_id}` | compteurs | Get compteur |
| GET | `/api/consommations` | consommations | List consommations |
| GET | `/api/reports/audit.json` | reports | Audit report JSON |
| GET | `/api/reports/audit.pdf` | reports | Audit report PDF |
| GET | `/` | app | Root (health info) |
| GET | `/health` | app | Health check |
