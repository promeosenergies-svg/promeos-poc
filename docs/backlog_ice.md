# PROMEOS - Backlog ICE

**Date**: 2026-02-11
**Methode**: ICE = Impact (1-10) x Confidence (1-10) x Ease (1-10) / 10
**Regle**: on fait le score ICE le plus haut en premier.

---

## Backlog actif (23 items)

| # | Item | I | C | E | ICE | Preuve attendue | Statut |
|---|------|---|---|---|-----|-----------------|--------|
| 1 | **Auth JWT + RBAC (3 roles)** | 10 | 9 | 7 | 63 | Login/logout fonctionnel, 118 endpoints proteges, 10 tests auth | TODO |
| 2 | **Dockerize backend + frontend** | 9 | 9 | 8 | 64.8 | `docker compose up` lance tout, CI-ready | TODO |
| 3 | **CI GitHub Actions** | 9 | 9 | 8 | 64.8 | PR = tests auto + build auto + badge green | TODO |
| 4 | **MAJ README avec etat reel** | 8 | 10 | 10 | 80 | README reflete 603 tests, 130 endpoints, 12 pages | TODO |
| 5 | **Corriger warnings utcnow()** | 6 | 10 | 9 | 54 | 0 DeprecationWarning dans pytest | TODO |
| 6 | **Indexes DB critiques** | 8 | 10 | 9 | 72 | 10 indexes sur FK + colonnes filtrees, queries <50ms | TODO |
| 7 | **Smoke test /health + API create** | 9 | 10 | 9 | 81 | 1 test ping /health, 1 test create Org/Site via API | SPRINT 0 |
| 8 | **Page /status frontend** | 7 | 10 | 9 | 63 | Page affichant version + statut backend + KPIs repo | SPRINT 0 |
| 9 | **Alembic migrations** | 8 | 8 | 6 | 38.4 | `alembic upgrade head` idempotent, migration initiale | TODO |
| 10 | **Rate limiting (slowapi)** | 7 | 9 | 8 | 50.4 | 100 req/min par IP, 429 au-dela | TODO |
| 11 | **Enrichir KB 12 -> 40 items** | 7 | 7 | 6 | 29.4 | 40 items valides, couverture 5 segments x 4 reglementations | TODO |
| 12 | **Connecteur Enedis sandbox** | 8 | 5 | 5 | 20 | OAuth flow, 1 releve importe en sandbox | TODO |
| 13 | **Shadow billing L2** | 7 | 7 | 5 | 24.5 | Optimisation tarifaire (meilleure option HP/HC vs Base) | TODO |
| 14 | **Notifications V2: email/webhook/digest** | 6 | 8 | 7 | 33.6 | Email sur alerte CRITICAL, webhook, digest periodique, SLA/escalation | TODO |
| 15 | **Export PDF rapport site** | 7 | 8 | 6 | 33.6 | PDF telechargeab avec conformite + conso + alertes | TODO |
| 16 | **PostgreSQL migration** | 9 | 7 | 4 | 25.2 | Meme 603 tests green sur Postgres, script migration | TODO |
| 17 | **Audit logging** | 6 | 8 | 7 | 33.6 | Table AuditLog, middleware, qui/quoi/quand | TODO |
| 18 | **Structured JSON logging** | 6 | 9 | 9 | 48.6 | Logs JSON parsables, correlation_id | TODO |
| 19 | **Activer IA Claude live** | 7 | 8 | 8 | 44.8 | 5 agents fonctionnels avec cle API, fallback stub | TODO |
| 20 | **Brique 3: Scenarios Achat** | 8 | 5 | 3 | 12 | Simulateur spot vs forward, 1 scenario demo | TODO |
| 21 | **Onboarding: import XLSX** | 6 | 8 | 6 | 28.8 | Upload Excel, parse avec openpyxl, meme pipeline que CSV | TODO |
| 22 | **Onboarding: geocodage auto** | 5 | 7 | 7 | 24.5 | Adresse -> lat/lon via API BAN (adresse.data.gouv.fr) | TODO |
| 23 | **Onboarding: enrichissement Pappers** | 5 | 6 | 5 | 15 | SIREN -> raison sociale, NAF, effectif via API Pappers | TODO |

---

## Items completes (reference)

| # | Item | ICE | Date | Commit |
|---|------|-----|------|--------|
| C1 | RegOps 4 reglementations | 90 | 2026-02-09 | 6ddf3ff |
| C2 | KB System 12 items + FTS5 | 72 | 2026-02-09 | 1602400 |
| C3 | 3 Couches Excellence | 64 | 2026-02-09 | 702a61b |
| C4 | Bill Intelligence complete | 72 | 2026-02-10 | e43ddaa |
| C5 | Referentiel Tarifs & Taxes | 56 | 2026-02-10 | 3ff603a |
| C6 | Electric Monitoring complet | 81 | 2026-02-11 | 4e53a6f |
| C7 | Onboarding B2B (wizard + API + NAF + CSV) | 85 | 2026-02-11 | - |
| C8 | Diagnostic Conso V1.1 (horaires, tarif, stats robustes, actions) | 72 | 2026-02-11 | - |
| C9 | Bill Intelligence V2 (models persistes, CSV import, shadow simplifie, 10 regles anomalies, frontend) | 72 | 2026-02-11 | - |
| C10 | Action Hub V1 (unified actions, sync 4 briques, export CSV, frontend) | 72 | 2026-02-11 | - |
| C11 | Audit Report PDF V1 (reportlab, 4 pages, 16 tests) | 56 | 2026-02-11 | - |
| C12 | Notifications & Alert Center V1 (5 briques, in-app, badges, 22 tests) | 48 | 2026-02-11 | - |

---

## Priorite recommandee (top 5 next)

1. **#7 Smoke test** (ICE 81) - Sprint 0, en cours
2. **#4 MAJ README** (ICE 80) - 30 min
3. **#6 Indexes DB** (ICE 72) - 1h
4. **#2 Docker** (ICE 64.8) - 2h
5. **#3 CI GitHub Actions** (ICE 64.8) - 2h
