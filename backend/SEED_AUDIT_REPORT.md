# SEED AUDIT REPORT — HELIOS

**Date** : 2026-04-04 19:51
**Pack** : helios  **Size** : S
**DB** : `backend/data/promeos.db`

## Résumé

| Statut | Count |
|--------|-------|
| ✅ OK | 28 |
| ⚠️ Partiel | 0 |
| ❌ Vide/Manquant | 0 |
| **Total** | **28** |

## Détail par module

| # | Module | Statut | Détail |
|---|--------|--------|--------|
| 1 | Patrimoine | ✅ | sites=5 batiments=13 compteurs=8 meters=21 delivery_points=8 |
| 2 | Consommation | ✅ | meter_readings=962009 frequencies=['MONTHLY', 'DAILY', 'HOURLY', 'MIN_15'] |
| 3 | Puissance | ✅ | power_readings=21600 power_contracts=5 |
| 4 | Facturation | ✅ | invoices=36 lines=216 insights=61 contracts=13 sites_covered=5 |
| 5 | Contrats V2 | ✅ | annexes=6 pricing=12 events=5 |
| 6 | Shadow Billing | ✅ | billing_insights=61 statuses=['OPEN', 'ACK', 'RESOLVED', 'FALSE_POSITIVE'] |
| 7 | Conformité DT | ✅ | efas=10 efa_buildings=13 efa_consumption=25 targets=728 |
| 8 | BACS | ✅ | assets=5 systems=9 assessments=5 inspections=4 |
| 9 | APER | ✅ | sites_eligible_aper=4 (parking>=1500 ou roof>=500) |
| 10 | Audit Énergétique/SMÉ | ✅ | audit_energetique=1 |
| 11 | RegOps Scoring | ✅ | reg_assessments=5 |
| 12 | Compliance Findings | ✅ | findings=15 statuses=['OPEN', 'RESOLVED', 'ACK'] severities=['critical', 'low', 'medium', 'high'] regulations=['aper', 'bacs', 'decret_tertiaire_operat'] |
| 13 | Actions | ✅ | actions=42 source_types=['BILLING', 'COMPLIANCE', 'CONSUMPTION', 'COPILOT', 'INSIGHT', 'MANUAL', 'PURCHASE'] statuses=['OPEN', 'DONE', 'IN_PROGRESS', 'FALSE_POSITIVE'] |
| 14 | Achat Énergie | ✅ | assumptions=5 results=15 sites_covered=5 |
| 15 | Monitoring | ✅ | snapshots=30 alerts=5 sites_covered=5 |
| 16 | Usages & Horaires | ✅ | schedules=5 usages=47 |
| 17 | Usages (drill-down) | ✅ | usages=47 sites_via_batiment=5 |
| 18 | Flex Scores | ✅ | usages=47 power_readings=21600 flex_assets=0 (computed dynamically) |
| 19 | Energy Signature | ✅ | meter_readings=962009 weather_cache=3650 (computed dynamically) |
| 20 | KB | ✅ | archetypes=11 rules=15 recommendations=10 versions=1 |
| 21 | Market Prices | ✅ | market_prices=0 mkt_prices=1101 regulated_tariffs=41 |
| 22 | Notifications | ✅ | events=22 batches=1 |
| 23 | DataPoints | ✅ | data_points=17 |
| 24 | RegSourceEvents | ✅ | reg_source_events=6 |
| 25 | Evidence / Preuves | ✅ | evidences=25 sites_covered=5 |
| 26 | Site Intelligence | ✅ | recommendations=169 anomalies=90 (computed dynamically) |
| 27 | Cockpit | ✅ | Deps: sites=5 invoices=36 findings=15 actions=42 |
| 28 | DT Progress | ✅ | efa_consumption=25 targets=728 |
