# Runbook — Observabilité PROMEOS (M2-6.A.3)

> **Statut** : runbook ops. Sibling de `RUNBOOK_DEPLOY.md` et `RUNBOOK_RGPD_PURGE.md`.
> Établi M2-6.A.3 (perf budgets MV3).
>
> **Cible** : DevOps + admins plateforme. Console humaine via curl/Postman MV3.

## Origine

Sans observabilité runtime, impossible de détecter dégradation P95 latency
ou error rate spike chez pilote HELIOS / MERIDIAN. Les décisions d'optimisation
M3+ sont informées par mesures réelles (« mesurer avant d'optimiser »),
pas par intuition.

## Endpoints disponibles MV3

| Endpoint | Auth | Description |
|---|---|---|
| `GET /health/metrics` | `require_platform_admin` STRICT | Snapshot P50/P95/P99 + payload + error rate par endpoint |
| `GET /health/alerts` | `require_platform_admin` STRICT | SLO breaches actifs vs budgets MV3 |

### GET /health/metrics

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" https://api.promeos.io/health/metrics | jq
```

Réponse (extrait) :

```json
{
  "endpoints": [
    {
      "endpoint": "GET /api/v4/action-center/items",
      "count": 1234,
      "p50_ms": 45.2,
      "p95_ms": 187.5,
      "p99_ms": 312.0,
      "payload_avg_kb": 12.4,
      "payload_max_kb": 89.7,
      "error_rate": 0.001,
      "last_15min_count": 89
    }
  ],
  "window_minutes": 15,
  "captured_at": 1747915200.0
}
```

### GET /health/alerts

```bash
curl -H "Authorization: Bearer $ADMIN_TOKEN" https://api.promeos.io/health/alerts | jq '.alerts'
```

Réponse (extrait — endpoint en dépassement) :

```json
{
  "alerts": [
    {
      "endpoint": "GET /api/v4/action-center/items",
      "type": "latency_p95",
      "threshold": 500.0,
      "actual": 728.0,
      "since_ts": 1747914300.0
    }
  ],
  "budgets": {
    "latency_p95_budget_ms": 500.0,
    "payload_avg_budget_kb": 200.0,
    "error_rate_budget": 0.02
  },
  "captured_at": 1747915200.0
}
```

`since_ts` = timestamp de la **première entry** dans la fenêtre rolling — utile
pour cadrer la recherche dans les logs serveur autour du début de la dégradation.

## Budgets MV3 (conservateurs — Q7)

| Métrique | Seuil | Source |
|---|---|---|
| Latency P95 | < 500 ms (toutes routes) | Nielsen Norman threshold UX |
| Payload moyen | < 200 kB | 3G mobile (TTI ~2s à 100 kB/s) |
| Error rate 5xx | < 2 % rolling 15 min | Bruit acceptable MV3 |

**Volontairement larges en MV3** (éviter faux-positifs alertes). Post-pilote :
serrer selon mesures réelles (objectif probable P95 <200ms `/v4/items`,
<50kB payload moyen, <0.1% error rate).

## Architecture interne

```
Request HTTP
   ↓
PerfMetricsMiddleware (outermost wrap — capture latency totale)
   ↓
CORSMiddleware
   ↓
SecurityHeadersMiddleware
   ↓
RequestContextMiddleware
   ↓
Endpoint FastAPI (auth + ORM + sérialisation)
   ↓ (réponse remonte la chaîne)
PerfMetricsMiddleware enregistre l'entry dans PerfMetricsStore (thread-safe deque)
   ↓
PerfMetricsStore (in-memory, 1000 entries/endpoint max)
   ↓ (consultation)
GET /health/metrics → calcul P50/P95/P99
GET /health/alerts → comparaison vs budgets
```

**Exclusions** (anti-récursion + anti-bruit méta) :
- Paths exacts : `/`, `/health`, `/api/health`, `/favicon.ico`
- Prefixes : `/health/`, `/docs`, `/openapi.json`, `/redoc`

**Path normalization** : `/api/v4/items/<UUID>` → `/api/v4/items/{id}` (regrouper
les routes paramétrées dans le même bucket de stats).

## Procédure consultation runtime

### Console quotidienne (5 min)

```bash
ADMIN_TOKEN="<token DG_OWNER ou DSI_ADMIN>"
BACKEND_URL="https://api.promeos.io"

# 1. Top 10 endpoints par latency P95
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$BACKEND_URL/health/metrics" \
  | jq '.endpoints | sort_by(-.p95_ms) | .[0:10] | .[] | "\(.endpoint) | P95=\(.p95_ms)ms | count=\(.count)"'

# 2. Alertes actives
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" "$BACKEND_URL/health/alerts" \
  | jq '.alerts[] | "\(.type) | \(.endpoint) | \(.actual) > \(.threshold)"'
```

### Procédure ajustement budgets post-pilote

1. **Collecter 7+ jours de mesures** (consultation `/health/metrics` quotidienne, dump JSON archivé).
2. **Calculer percentiles réels par endpoint** (script Python ou jq).
3. **Définir budgets cibles** : `budget = P95_réel × 1.5` (marge 50 % anti-flap).
4. **Modifier** `backend/config/perf_budgets.py` (constantes globales ou `ENDPOINT_OVERRIDES`).
5. **Redéployer** + valider sur staging avant prod (smoke test).

## Procédure escalation incident

### Cas 1 — Latency P95 spike soudain

1. `GET /health/alerts` → identifier endpoint(s) affecté(s).
2. Logs serveur fenêtre `[since_ts, now]` (correlation_id propagé via `RequestContextMiddleware`).
3. Check DB load (slow queries via `pg_stat_statements` ou EXPLAIN ANALYZE).
4. Check infrastructure (CPU/RAM/réseau plateforme deploy).
5. Si rien → **rollback dernier deploy** (cf. `RUNBOOK_DEPLOY.md` procédure rollback).

### Cas 2 — Error rate > 2 % sur 15 min

1. Logs serveur immédiat (probable exception non gérée — niveau ERROR).
2. Identifier endpoint via `/health/alerts` (type `error_rate`).
3. Si erreur récente → rollback. Sinon hotfix + redeploy via Safety Gate (`docs/deploy/RUNBOOK_DEPLOY.md` Gate 1).

### Cas 3 — Payload moyen > 200 kB

1. Cause probable : pagination cassée (limit non appliquée) OU dataset gonflé.
2. Vérifier `/health/metrics` champ `count` — pic de trafic ? Cache miss ?
3. Si payload anormal sur un endpoint précis → audit dernière modif schéma de réponse.

## Limitations MV3 connues

- **Persistance metrics** : in-memory uniquement, **perdues au restart** backend. Acceptable MV3 (fenêtre 15 min). M3+ : Postgres TimescaleDB ou Prometheus exporter.
- **Tracking frontend** : différé M3 (Q9=A). Aucune mesure côté navigateur (TTI, LCP, INP).
- **Notifications** : pull uniquement (consultation endpoint). M3+ : webhook Slack / email sur breach actif > 5 min.
- **Pas de Prometheus / Grafana / Sentry** : dashboard visuel à monter post-pilote si scale.
- **`Content-Length` absent** sur chunked / streaming → `payload_bytes` enregistré à 0 (documenté, acceptable MV3).
- **Pas de tracing distribué** : OpenTelemetry à introduire si architecture microservices M3+.

## Plan évolution M3+

| Étape | Solution candidate | Trigger |
|---|---|---|
| Persistance metrics | Prometheus exporter (`prometheus-fastapi-instrumentator`) | Pilote scale > 1 instance |
| Tracking frontend | `PerformanceObserver` + endpoint `/health/frontend-metrics` | Q9 réouvert post-pilote |
| Notifications push | Webhook Slack sur `/health/alerts` non vide > 5 min | Pilote payant signé |
| Dashboard visuel | Grafana (sur Prometheus) ou Sentry Performance | > 5 endpoints critiques |
| Tracing distribué | OpenTelemetry + Jaeger | Architecture microservices |

## Doctrine référencée

- [`backend/middleware/perf_metrics.py`](../../backend/middleware/perf_metrics.py) — middleware + store
- [`backend/routes/health_metrics.py`](../../backend/routes/health_metrics.py) — endpoints admin
- [`backend/config/perf_budgets.py`](../../backend/config/perf_budgets.py) — constantes
- [`docs/dev/methode_self_review_pr.md`](../dev/methode_self_review_pr.md) — discipline cas trunk-based
- `docs/deploy/RUNBOOK_DEPLOY.md` — gates pré-deploy (Gate 1 DEMO_MODE / Gate 2 V4 flag / Gate 3 seed)
- `docs/deploy/RUNBOOK_RGPD_PURGE.md` — purge PII RGPD art. 17
