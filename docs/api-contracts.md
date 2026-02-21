# Contrats API PROMEOS

> Reference -- endpoints patrimoine, consommation, reglementation, monitoring, EMS.
> Base URL : `http://localhost:8000`

---

## Conventions communes

### Authentification

- Header : `Authorization: Bearer <token>`
- 401 si token absent/expire, 403 si permissions insuffisantes
- Mode demo : auth optionnelle (endpoints fonctionnent sans token)

### Pagination

- `?skip=0&limit=50` (defaut 50, max 200)
- Patrimoine staging : `?page=1&page_size=50`
- Response : `{ items: [...], total: int }`

### Scope

- `org_id` via query param ou header `X-Org-Id`
- `site_id` pour filtrer par site
- Priorite : auth token > X-Org-Id header > DemoState > dernier org

### Headers de reponse

- `X-Request-Id` : identifiant unique de la requete
- `X-Response-Time` : temps de traitement (ms)

### Erreurs

- `{ "detail": "message" }` avec code HTTP
- 422 pour validation Pydantic, 404 pour resource introuvable, 409 pour doublon

---

## 1. Patrimoine

Prefix : `/api/patrimoine` -- Import pipeline, quality gate, CRUD sites/compteurs/contrats.

### Import Template

#### GET /api/patrimoine/import/template

Telecharge le template officiel d'import.

- Query : `format` (str, opt, `xlsx` | `csv`, defaut `xlsx`)
- Response : fichier binaire (CSV ou XLSX)
- Codes : 200, 500

#### GET /api/patrimoine/import/template/columns

Liste les colonnes canoniques avec metadonnees.

- Response : `{ columns: [...], delimiter: ";", encoding: "utf-8", notes: [...] }`

### Staging Pipeline

#### POST /api/patrimoine/staging/import

Import CSV/Excel vers le pipeline staging.

- Body : `multipart/form-data` -- `file` (required)
- Query : `mode` (str, opt, `express` | `import` | `assiste` | `demo`, defaut `import`)
- Response : `{ batch_id: int, duplicate: bool, sites_count: int, compteurs_count: int, mapping?: {...} }`
- Codes : 200, 400, 409 (doublon hash)

#### POST /api/patrimoine/staging/import-invoices

Import sites/compteurs depuis metadonnees factures.

- Body : `{ invoices: [...] }`
- Response : `{ batch_id: int, sites_count: int, compteurs_count: int }`

#### GET /api/patrimoine/staging/{batch_id}/summary

Resume statistique d'un batch staging.

- Path : `batch_id` (int, required)
- Response : `{ total_sites, total_compteurs, status_counts, ... }`
- Codes : 200, 404

#### GET /api/patrimoine/staging/{batch_id}/rows

Liste les lignes staging avec pagination et recherche.

- Path : `batch_id` (int)
- Query : `status` (opt, `ok` | `error` | `skipped`), `q` (str, opt), `page` (int, defaut 1), `page_size` (int, defaut 50, max 200)
- Response : `{ total, page, page_size, rows: [{ id, nom, adresse, compteurs: [...], issues_count, ... }] }`

#### GET /api/patrimoine/staging/{batch_id}/issues

Liste les findings qualite d'un batch.

- Query : `severity` (opt, `blocking` | `critical` | `warning` | `info`), `resolved` (bool, opt)
- Response : `{ total, issues: [{ id, rule_id, severity, evidence, suggested_action, resolved }] }`

#### POST /api/patrimoine/staging/{batch_id}/validate

Execute le quality gate sur un batch.

- Response : `{ findings: [...], blocking_count: int, can_activate: bool }`

#### PUT /api/patrimoine/staging/{batch_id}/fix

Applique une correction unitaire.

- Body : `{ fix_type: str, params: dict }`
- Response : `{ applied: bool, ... }`

#### PUT /api/patrimoine/staging/{batch_id}/fix/bulk

Applique plusieurs corrections en une transaction.

- Body : `{ fixes: [{ fix_type: str, params: dict }] }`
- Response : `{ applied: int, total: int, results: [...] }`

#### POST /api/patrimoine/staging/{batch_id}/autofix

Auto-corrections safe (trim, pad CP, normalize types, skip orphans).

- Response : `{ fixes_applied: int, detail: str }`

#### DELETE /api/patrimoine/staging/{batch_id}

Abandonne un batch staging.

- Codes : 200, 404

#### POST /api/patrimoine/staging/{batch_id}/activate

Active un batch valide -- cree les entites reelles.

- Body : `{ portefeuille_id: int }`
- Response : `{ sites_created, compteurs_created, ... }`
- Codes : 200, 400 (blocking findings), 404

#### GET /api/patrimoine/staging/{batch_id}/result

Resultat post-activation d'un batch.

- Response : `{ batch_id, status, mode, activation: { sites_created, compteurs_created, ... }, stats }`

#### GET /api/patrimoine/staging/{batch_id}/export/report.csv

Export CSV du rapport d'import (lignes + issues + statut).

- Response : fichier CSV

#### POST /api/patrimoine/mapping/preview

Preview du mapping colonnes CSV/Excel.

- Body : `{ headers: [str] }`
- Response : `{ mapping, warnings, unmapped }`

### Sites CRUD (Patrimoine)

#### GET /api/patrimoine/sites

Liste les sites avec filtres.

- Query : `portefeuille_id` (int, opt), `actif` (bool, opt), `ville` (str, opt), `type_site` (str, opt), `search` (str, opt), `skip` (int, 0), `limit` (int, 100)
- Response : `{ total: int, sites: [{ id, nom, type, adresse, ville, surface_m2, siret, actif, ... }] }`

#### GET /api/patrimoine/sites/{site_id}

Detail d'un site avec compteurs et contrats count.

- Response : `{ id, nom, type, ..., compteurs_count, contracts_count }`

#### PATCH /api/patrimoine/sites/{site_id}

Mise a jour partielle d'un site.

- Body : `{ nom?, adresse?, code_postal?, ville?, surface_m2?, type?, ... }`
- Response : `{ updated: [str], ...site }`

#### POST /api/patrimoine/sites/{site_id}/archive

Soft-delete (actif=false).

- Response : `{ detail, site_id }`

#### POST /api/patrimoine/sites/{site_id}/restore

Restaurer un site archive.

- Response : `{ detail, site_id }`

#### POST /api/patrimoine/sites/merge

Fusionne source dans cible : transfert compteurs + contrats, archive source.

- Body : `{ source_site_id: int, target_site_id: int }`
- Response : `{ detail, compteurs_moved, contracts_moved, source_archived }`

#### GET /api/patrimoine/sites/{site_id}/delivery-points

Points de livraison actifs (PRM/PCE) d'un site.

- Response : `[{ id, code, energy_type, status, compteurs_count }]`

### Compteurs (Patrimoine)

#### GET /api/patrimoine/compteurs

Liste avec filtres.

- Query : `site_id` (int, opt), `actif` (bool, opt), `skip`, `limit`
- Response : `{ total, compteurs: [{ id, site_id, type, numero_serie, meter_id, puissance_souscrite_kw }] }`

#### PATCH /api/patrimoine/compteurs/{compteur_id}

Mise a jour partielle.

- Body : `{ numero_serie?, meter_id?, puissance_souscrite_kw?, type? }`

#### POST /api/patrimoine/compteurs/{compteur_id}/move

Deplace un compteur vers un autre site.

- Body : `{ target_site_id: int }`

#### POST /api/patrimoine/compteurs/{compteur_id}/detach

Desactive un compteur (soft detach).

### Contrats Energie (Patrimoine)

#### GET /api/patrimoine/contracts

Liste des contrats energie.

- Query : `site_id` (int, opt), `energy_type` (str, opt), `skip`, `limit`
- Response : `{ total, contracts: [{ id, site_id, energy_type, supplier_name, start_date, end_date, price_ref_eur_per_kwh }] }`

#### POST /api/patrimoine/contracts

Cree un contrat.

- Body : `{ site_id, energy_type, supplier_name, start_date?, end_date?, price_ref_eur_per_kwh?, notice_period_days?, auto_renew? }`

#### PATCH /api/patrimoine/contracts/{contract_id}

Mise a jour partielle.

- Body : `{ supplier_name?, start_date?, end_date?, price_ref_eur_per_kwh?, auto_renew? }`

#### DELETE /api/patrimoine/contracts/{contract_id}

Supprime un contrat.

### Sync & Demo (Patrimoine)

#### POST /api/patrimoine/{portfolio_id}/sync

Sync incremental : compare fichier vs portefeuille existant.

- Body : `multipart/form-data` -- `file`
- Query : `dry_run` (bool, defaut true)
- Response : `{ adds, updates, removes, applied: bool }`

#### POST /api/patrimoine/demo/load

Charge les donnees demo patrimoine.

---

## 2. Sites

Prefix : `/api/sites` -- CRUD sites avec conformite et guardrails.

#### POST /api/sites

Cree un site avec auto-provision (batiment + obligations + compliance).

- Body : `{ nom: str, type?, naf_code?, adresse?, code_postal?, ville?, surface_m2? }`
- Response : `{ id, nom, type, findings_count, batiments_count, obligations_count }`

#### GET /api/sites

Liste sites avec pagination et filtres. Scope : org_id ou X-Org-Id header.

- Query : `skip`, `limit`, `org_id` (int, opt), `ville` (str, opt), `type` (str, opt)
- Response : `{ total, sites: [SiteResponse] }`

#### GET /api/sites/{site_id}

Detail d'un site.

- Response : SiteResponse (id, nom, type, adresse, statut_decret_tertiaire, statut_bacs, risque_financier_euro, ...)

#### GET /api/sites/{site_id}/stats

Statistiques du site (compteurs, alertes, consommation mois).

- Response : `{ nb_compteurs, nb_alertes_actives, consommation_totale_mois, cout_total_mois }`

#### GET /api/sites/{site_id}/compliance

Conformite detaillee : obligations, evidences, explications, actions.

- Response : `{ site, batiments, obligations, evidences, explanations: [...], actions: [...] }`

#### GET /api/sites/{site_id}/guardrails

Regles de validation (guardrails) pour un site.

#### GET /api/sites/{site_id}/flex/mini

Potentiel flexibilite : score 0-100 + top 3 leviers.

- Query : `start` (str, opt, YYYY-MM-DD), `end` (str, opt)
- Response : `{ score, levers: [...], justification }`

---

## 3. Compteurs

Prefix : `/api/compteurs`

#### POST /api/compteurs

Cree un compteur.

- Body : `{ site_id: int, type: str (electricite|gaz|eau), numero_serie?, puissance_souscrite_kw? }`
- Codes : 200, 400, 404

#### GET /api/compteurs

Liste avec filtres.

- Query : `site_id` (int, opt), `type` (str, opt)
- Response : `[CompteurResponse]`

#### GET /api/compteurs/{compteur_id}

Detail d'un compteur.

---

## 4. Consommations

Prefix : `/api/consommations`

#### GET /api/consommations

Liste les consommations.

- Query : `compteur_id` (int, opt), `limit` (int, defaut 100, max 1000)
- Response : `[{ id, compteur_id, timestamp, valeur, unite, cout_euro }]`

---

## 5. Alertes

Prefix : `/api/alertes`

#### GET /api/alertes

Liste les alertes avec filtres.

- Query : `site_id` (int, opt), `severite` (str, opt), `resolue` (bool, opt), `limit` (int, defaut 50, max 200)
- Response : `{ total, alertes: [AlerteResponse] }`

#### GET /api/alertes/{alerte_id}

Detail d'une alerte.

#### PATCH /api/alertes/{alerte_id}/resolve

Marque une alerte comme resolue.

- Response : `{ message: "Alerte resolue avec succes" }`

---

## 6. Cockpit

Prefix : `/api`

#### GET /api/cockpit

KPIs executifs org-level. Scope : auth > X-Org-Id > DemoState.

- Response : `{ organisation: { nom, type_client }, stats: { total_sites, sites_actifs, avancement_decret_pct, risque_financier_euro, alertes_actives }, echeance_prochaine }`

#### GET /api/portefeuilles

Liste des portefeuilles avec stats. Scope : X-Org-Id header.

- Response : `{ portefeuilles: [{ id, nom, description, nb_sites }], total }`

---

## 7. Compliance

Prefix : `/api/compliance`

#### POST /api/compliance/recompute

Recalcule les snapshots conformite.

- Query : `scope` (str, required, `org` | `portfolio` | `site`), `id` (int, required)
- Response : `{ status: "ok", scope, ... }`

#### GET /api/compliance/summary

Resume agrege des findings.

- Query : `org_id`, `entity_id`, `site_id` (tous opt, priorite : site > entity > org)
- Response : `{ total_sites, sites_ok, sites_nok, pct_ok, findings_by_regulation, top_actions }`

#### GET /api/compliance/sites

Findings par site avec filtres.

- Query : `org_id`, `entity_id`, `site_id`, `regulation`, `status`, `severity` (tous opt)
- Response : `[{ site_id, site_nom, findings: [...] }]`

#### GET /api/compliance/bundle

Bundle single-request : summary + sites.

- Query : `org_id`, `entity_id`, `site_id`, `portefeuille_id`, `regulation`, `status`, `severity`
- Response : `{ summary, sites, empty_reason }`

#### POST /api/compliance/recompute-rules

Evalue toutes les regles YAML pour tous les sites d'une org.

- Query : `org_id` (int, opt)
- Response : `{ status: "ok", findings_count, sites_evaluated }`

#### GET /api/compliance/rules

Liste les rule packs charges (audit/transparence).

- Response : `[{ regulation, label, version, description, rules_count, rules: [...] }]`

#### GET /api/compliance/findings

Liste des findings avec workflow. Filtres : regulation, status, severity, insight_status.

- Query : `org_id`, `regulation`, `status`, `severity`, `insight_status` (opt, `open` | `in_progress` | `resolved` | `wont_fix`)
- Response : `[{ id, site_id, site_nom, regulation, rule_id, status, severity, deadline, insight_status, owner, notes }]`

#### GET /api/compliance/findings/{finding_id}

Detail finding avec champs audit (inputs, params, evidence, engine_version).

#### PATCH /api/compliance/findings/{finding_id}

Update workflow finding.

- Body : `{ status?, owner?, notes? }`
- Response : `{ status: "updated", finding_id, insight_status, owner, notes }`

#### GET /api/compliance/batches

Historique des runs compliance.

- Query : `org_id` (int, opt)
- Response : `[{ id, org_id, triggered_by, started_at, completed_at, sites_count, findings_count }]`

---

## 8. RegOps

Prefix : `/api/regops`

#### GET /api/regops/site/{site_id}

Evaluation RegOps complete (fresh compute).

- Response : `{ site_id, global_status, compliance_score, next_deadline, findings: [...], actions: [...], missing_data }`

#### GET /api/regops/site/{site_id}/cached

Assessment en cache (rapide).

- Response : `{ site_id, global_status, compliance_score, computed_at, is_stale }`

#### POST /api/regops/recompute

Trigger recompute.

- Query : `scope` (str, `site` | `all`), `site_id` (int, opt)
- Response : `{ recomputed: int }`

#### GET /api/regops/score_explain

Breakdown detaille du score compliance.

- Query : `scope_type` (str, `site`), `scope_id` (int, required)
- Response : `{ score, confidence_score, penalties: [...], suppressed_penalties, dq_summary, how_to_improve }`

#### GET /api/regops/data_quality

Data quality gate : coverage, confidence, champs manquants par reglementation.

- Query : `scope_type`, `scope_id`
- Response : `{ coverage_pct, confidence_score, gate_status, missing_critical, missing_optional, per_regulation }`

#### GET /api/regops/data_quality/specs

Specifications DQ par reglementation (pour UI).

#### GET /api/regops/dashboard

KPIs org-level RegOps.

- Response : `{ total_sites, sites_compliant, sites_at_risk, sites_non_compliant, avg_compliance_score }`

---

## 9. BACS Expert

Prefix : `/api/regops/bacs`

#### GET /api/regops/bacs/site/{site_id}

Assessment BACS complet : asset + systemes CVC + assessment + inspections + DQ.

- Response : `{ site_id, configured, asset, systems: [...], assessment, inspections: [...], data_quality }`

#### POST /api/regops/bacs/recompute/{site_id}

Recalcule l'assessment BACS, persiste le resultat.

#### GET /api/regops/bacs/score_explain/{site_id}

Putile steps + seuil + TRI + penalties breakdown.

#### GET /api/regops/bacs/data_quality/{site_id}

DQ gate BACS : `BLOCKED` | `WARNING` | `OK`.

#### POST /api/regops/bacs/asset

Cree un BacsAsset pour un site.

- Query : `site_id` (int), `is_tertiary` (bool, defaut true), `pc_date` (str, opt)
- Codes : 200, 404, 409

#### POST /api/regops/bacs/asset/{asset_id}/system

Ajoute un systeme CVC a un asset.

- Query : `system_type` (str), `architecture` (str), `units_json` (str, defaut `[]`)

#### PUT /api/regops/bacs/system/{system_id}

Met a jour un systeme CVC.

- Query : `units_json` (str, opt), `architecture` (str, opt)

#### DELETE /api/regops/bacs/system/{system_id}

Supprime un systeme CVC.

#### GET /api/regops/bacs/site/{site_id}/ops

Panel monitoring operationnel BACS : KPIs, liens conso, heatmap.

#### POST /api/regops/bacs/seed_demo

Seed 10 assets BACS demo avec configs CVC variees.

---

## 10. Monitoring

Prefix : `/api/monitoring`

#### GET /api/monitoring/kpis

KPIs monitoring pour un site/compteur.

- Query : `site_id` (int, required), `meter_id` (int, opt)
- Response : `{ snapshot_id, site_id, period, kpis, data_quality_score, risk_power_score, climate, schedule, impact, emissions }`

#### GET /api/monitoring/kpis/compare

Comparaison KPIs : periode precedente, N-1 ou custom.

- Query : `site_id` (required), `mode` (`previous` | `n-1` | `custom`), `custom_start`, `custom_end`, `meter_id`
- Response : `{ compare: { snapshot_id, period, kpis, impact }, mode, reason }`

#### POST /api/monitoring/run

Execute le pipeline monitoring complet pour un site.

- Body : `{ site_id: int, meter_id?: int, days?: int (90), interval_minutes?: int (60) }`

#### GET /api/monitoring/snapshots

Liste des snapshots monitoring.

- Query : `site_id`, `meter_id` (opt), `limit` (int, defaut 20, max 100)
- Response : `[{ id, site_id, meter_id, period, data_quality_score, risk_power_score, created_at }]`

#### GET /api/monitoring/alerts

Alertes monitoring avec filtres.

- Query : `site_id`, `status` (opt, `open` | `acknowledged` | `resolved`), `severity` (opt), `limit` (defaut 50, max 200)
- Response : `[{ id, alert_type, severity, explanation, recommended_action, estimated_impact_kwh, estimated_impact_eur, status }]`

#### POST /api/monitoring/alerts/{alert_id}/ack

Acquitte une alerte ouverte.

- Body : `{ acknowledged_by: str }`

#### POST /api/monitoring/alerts/{alert_id}/resolve

Resout une alerte.

- Body : `{ resolved_by: str, resolution_note?: str }`

#### GET /api/monitoring/emissions

Resume emissions CO2e pour un site.

- Query : `site_id` (required), `meter_id` (opt)

#### GET /api/monitoring/emission-factors

Liste les facteurs d'emission disponibles.

- Query : `energy_type` (opt), `region` (opt)

#### POST /api/monitoring/emission-factors/seed

Seed facteur d'emission FR par defaut.

#### POST /api/monitoring/demo/generate

Genere des donnees monitoring demo (pattern profile + meteo + anomalies).

- Body : `{ site_id: int, days?: int (90), profile?: str ("office"|"hotel"|"retail"|"warehouse"|"school"|"hospital") }`

---

## 11. Energy

Prefix : `/api/energy`

#### POST /api/energy/meters

Cree un compteur energie (Meter).

- Body : `{ meter_id: str, name: str, site_id: int, energy_vector?: str, subscribed_power_kva?, tariff_type? }`
- Codes : 200, 404, 409

#### GET /api/energy/meters

Liste des Meters. Filtre par site.

- Query : `site_id` (int, opt)
- Response : `[{ id, meter_id, name, site_id, energy_vector, readings_count }]`

#### POST /api/energy/import/upload

Upload fichier consommation (CSV/XLSX/JSON).

- Body : `multipart/form-data` -- `file`
- Query : `meter_id` (str, required), `frequency` (`15min` | `30min` | `hourly` | `daily` | `monthly`)
- Response : `{ status, job_id, rows_imported, rows_skipped, rows_errored, date_range }`

#### GET /api/energy/import/jobs

Liste des jobs d'import.

- Query : `meter_id` (str, opt)
- Response : `[ImportJobResponse]`

#### POST /api/energy/analysis/run

Lance l'analyse KB-driven sur un compteur.

- Query : `meter_id` (str, required)

#### GET /api/energy/analysis/summary

Resume de la derniere analyse.

- Query : `meter_id` (str, required)
- Response : `{ meter_id, site_name, period, archetype_code, kwh_total, anomalies_count, recommendations_count, top_anomalies, top_recommendations }`

#### POST /api/energy/demo/generate

Genere des donnees conso synthetiques.

- Body : `{ site_id: int, meter_name?: str, days?: int (365), archetype?: str }`

---

## 12. EMS Explorer

Prefix : `/api/ems`

#### GET /api/ems/health

Health check du module EMS.

#### GET /api/ems/timeseries

Timeseries consommation multi-site.

- Query : `site_ids` (str, required, comma-sep), `date_from` (str, required, ISO), `date_to` (str, required), `granularity` (`auto` | `15min` | `hourly` | `daily` | `weekly` | `monthly`), `mode` (`aggregate` | `overlay` | `stack` | `split`), `metric` (`kwh`), `meter_ids` (opt), `energy_vector` (opt)
- Response : `{ series: [{ key, label, data: [{ t, v, quality }] }], meta: { granularity, n_points, n_meters }, availability }`

#### GET /api/ems/timeseries/suggest

Suggere la granularite optimale.

- Query : `date_from`, `date_to`
- Response : `{ granularity: str }`

#### GET /api/ems/weather

Donnees meteo pour un ou plusieurs sites.

- Query : `site_id` (int, opt), `site_ids` (str, opt, comma-sep), `date_from`, `date_to`
- Response : `{ site_id, days: [{ date, temp_avg_c, temp_min_c, temp_max_c }] }`

#### GET /api/ems/usage_suggest

Suggestion archetype + horaires pour un site.

- Query : `site_id` (int, required)
- Response : `{ archetype_code, archetype_label, confidence, schedule_current, schedule_suggested }`

#### GET /api/ems/benchmark

Benchmark KPIs vs peers du meme archetype.

- Query : `site_id` (int, required)
- Response : `{ peer_count, benchmarks: { pbase_kw, off_hours_ratio, ... }, insufficient }`

#### GET /api/ems/schedule_suggest

Suggestion horaires depuis donnees conso reelles.

- Query : `site_id` (required), `days` (int, 7-365, defaut 90)

#### POST /api/ems/signature/run

Signature energetique (conso vs temperature).

- Query : `site_id`, `date_from`, `date_to`, `meter_ids` (opt)
- Response : `{ scatter, fit_line, slope, intercept, r2, base_temp }`

#### POST /api/ems/signature/portfolio

Signature energetique sur portefeuille agrege.

- Query : `site_ids` (comma-sep), `date_from`, `date_to`

### Saved Views

#### GET /api/ems/views

Liste des vues sauvegardees.

- Query : `user_id` (int, opt)

#### POST /api/ems/views

Cree une vue.

- Query : `name` (str), `config_json` (str), `user_id` (opt)
- Codes : 201

#### GET /api/ems/views/{view_id}

Detail d'une vue.

#### PUT /api/ems/views/{view_id}

Met a jour une vue.

- Query : `name` (opt), `config_json` (opt)

#### DELETE /api/ems/views/{view_id}

Supprime une vue.

### Collections (Paniers de sites)

#### GET /api/ems/collections

Liste des collections.

#### POST /api/ems/collections

Cree une collection.

- Query : `name`, `site_ids` (comma-sep), `scope_type` (defaut `custom`), `is_favorite` (bool)
- Codes : 201

#### PUT /api/ems/collections/{col_id}

Met a jour une collection.

#### DELETE /api/ems/collections/{col_id}

Supprime une collection.

### Demo EMS

#### POST /api/ems/demo/generate

Genere des donnees demo multi-site realistes.

- Query : `portfolio_size` (int, 12), `days` (int, 365), `seed` (int, 123), `force` (bool, false)

#### POST /api/ems/demo/generate_timeseries

Genere timeseries demo pour un site specifique.

- Query : `site_id` (required), `days` (7-365), `anomaly` (bool, true), `energy_vector` (`electricity` | `gas`)

#### POST /api/ems/demo/purge

Supprime toutes les donnees demo EMS.

---

## 13. Auth (IAM)

Prefix : `/api/auth`

#### POST /api/auth/login

Authentification email + password.

- Body : `{ email: str, password: str }`
- Response : `{ access_token, token_type, user: { id, email, nom, prenom }, org, role, orgs, scopes, permissions }`
- Codes : 200, 401, 403

#### POST /api/auth/refresh

Renouvelle le JWT.

- Header : `Authorization: Bearer <token>`
- Response : `{ access_token, token_type }`

#### GET /api/auth/me

Profil utilisateur courant + role + scopes + permissions.

- Response : meme structure que login

#### POST /api/auth/logout

Logout (invalidation cote client, log serveur).

- Response : `{ status: "ok" }`

#### PUT /api/auth/password

Change le mot de passe.

- Body : `{ current_password: str, new_password: str }`
- Response : `{ status: "updated" }`
- Codes : 200, 400, 401

#### POST /api/auth/switch-org

Change le contexte org, retourne un nouveau JWT.

- Body : `{ org_id: int }`
- Response : meme structure que login

#### POST /api/auth/impersonate

Impersonation (demo mode ou admin).

- Body : `{ email: str }`
- Response : meme structure que login
- Codes : 200, 401, 403, 404

#### GET /api/auth/audit

Liste les logs d'audit (admin only).

- Query : `limit` (int, 50, max 200), `offset` (int, 0), `action` (str, opt), `user_id` (int, opt), `resource_type` (str, opt)
- Response : `{ total, entries: [{ id, user_id, user_name, action, resource_type, created_at }] }`

#### POST /api/auth/reset-demo

Reset demo (delegue a /api/demo/reset-pack + IAM).

---

## 14. Admin Users (IAM)

Prefix : `/api/admin` -- Toutes les routes necessitent permission `admin`.

#### GET /api/admin/users

Liste des utilisateurs de l'org courante.

#### POST /api/admin/users

Cree un utilisateur + role + scopes.

- Body : `{ email, password, nom, prenom, role: str, scopes?: [{ level, id, expires_at? }] }`

#### GET /api/admin/users/{user_id}

Detail utilisateur.

#### PATCH /api/admin/users/{user_id}

Modifie les champs utilisateur.

- Body : `{ nom?, prenom?, email?, actif? }`

#### PUT /api/admin/users/{user_id}/role

Change le role.

- Body : `{ role: str }`
- Protection : dernier DG_OWNER ne peut pas etre demote.

#### PUT /api/admin/users/{user_id}/scopes

Remplace les scopes (supprime existants + cree nouveaux).

- Body : `{ scopes: [{ level, id, expires_at? }] }`

#### DELETE /api/admin/users/{user_id}

Soft delete (actif=false). Protection dernier DG_OWNER.

#### GET /api/admin/roles

Liste tous les roles avec matrice de permissions.

#### GET /api/admin/users/{user_id}/effective-access

Sites accessibles par un utilisateur (resolus depuis scopes).

- Response : `{ user_id, role, permissions, scopes: [...], sites: [{ id, nom, type }], total_sites }`

---

## 15. Demo

Prefix : `/api/demo`

#### POST /api/demo/enable

Active le mode demo.

#### POST /api/demo/disable

Desactive le mode demo.

#### GET /api/demo/status

Statut du mode demo.

#### GET /api/demo/packs

Liste des packs demo disponibles.

#### POST /api/demo/seed-pack

Seed complet par pack (casino, tertiaire).

- Body : `{ pack: str ("casino"), size: str ("S"), rng_seed?: int, reset?: bool, days?: int (90) }`

#### GET /api/demo/status-pack

Status detaille : comptage par table + org/site courants.

#### GET /api/demo/manifest

Source de verite : org, portefeuilles, sites, compteurs.

- Response : `{ org_id, org_nom, pack, size, portefeuilles: [...], total_sites, total_compteurs, all_site_ids }`

#### POST /api/demo/reset-pack

Reset des donnees demo.

- Body : `{ mode: str ("soft"|"hard"), confirm?: bool }`
- Note : hard reset necessite `confirm: true`

#### POST /api/demo/seed

Seed legacy (3 sites demo).

#### GET /api/demo/templates

Liste des profils demo disponibles.

#### GET /api/demo/templates/{template_id}

Detail d'un profil demo.

---

## 16. Transversal

### Health

#### GET /

Page d'accueil API.

- Response : `{ message, version, sites, docs, health }`

#### GET /health

Health check basique.

- Response : `{ status: "healthy", message, version }`

#### GET /api/health

Health check avance avec git SHA et versions moteurs.

- Response : `{ ok: true, version, git_sha, time, engine_versions: { compliance, bacs } }`

### Dev Tools

Prefix : `/api/dev`

#### POST /api/dev/reset_db

Backup + recreate schema + reseed demo. Developpement uniquement.

- Response : `{ status, backup_path, schema, seed }`
