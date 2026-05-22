"""M2-6.A.3 — Endpoints health metrics + alerts (admin uniquement).

Q10=A : `require_platform_admin` STRICT (DG_OWNER / DSI_ADMIN, no DEMO_MODE
bypass). Pas de tokens monitoring externes en MV3 — accès humain admin via
curl/Postman uniquement.

2 endpoints :
  - GET /health/metrics : snapshot stats par endpoint (P50/P95/P99 + payload + error rate)
  - GET /health/alerts  : SLO breaches actifs vs budgets MV3 (config/perf_budgets.py)

Pattern : pull (consultation manuelle ou cron externe), pas push. M3+
ajoutera webhook Slack/email sur breach actif >5min (cf. RUNBOOK §plan évolution).
"""

import statistics
import time

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from config.perf_budgets import (
    ERROR_RATE_BUDGET,
    LATENCY_P95_BUDGET_MS,
    PAYLOAD_AVG_BUDGET_KB,
)
from middleware.auth import require_platform_admin
from middleware.perf_metrics import WINDOW_MINUTES, MetricEntry, get_store

router = APIRouter(prefix="/health", tags=["Observability"])


# ── Schémas Pydantic ─────────────────────────────────────────────────


class EndpointMetrics(BaseModel):
    endpoint: str  # ex: "GET /api/v4/action-center/items"
    count: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    payload_avg_kb: float
    payload_max_kb: float
    error_rate: float  # 0.0 - 1.0
    last_15min_count: int


class MetricsResponse(BaseModel):
    endpoints: list[EndpointMetrics]
    window_minutes: int
    captured_at: float


class AlertEntry(BaseModel):
    endpoint: str
    type: str  # "latency_p95" | "payload_avg" | "error_rate"
    threshold: float
    actual: float
    since_ts: float  # timestamp de la première entry dans la fenêtre


class AlertsResponse(BaseModel):
    alerts: list[AlertEntry]
    budgets: dict[str, float]
    captured_at: float


# ── Calculs stats ────────────────────────────────────────────────────


def _percentile(sorted_values: list[float], p: float) -> float:
    """Interpolation linéaire (méthode 7 / numpy default).

    `sorted_values` DOIT être trié croissant. `p` ∈ [0, 1].
    """
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


def _compute_endpoint_metrics(key: str, entries: list[MetricEntry]) -> EndpointMetrics:
    """Calcule P50/P95/P99 + payload + error_rate pour 1 endpoint."""
    if not entries:
        return EndpointMetrics(
            endpoint=key,
            count=0,
            p50_ms=0.0,
            p95_ms=0.0,
            p99_ms=0.0,
            payload_avg_kb=0.0,
            payload_max_kb=0.0,
            error_rate=0.0,
            last_15min_count=0,
        )

    latencies = sorted(e.latency_ms for e in entries)
    payloads = [e.payload_bytes for e in entries]
    errors = sum(1 for e in entries if e.status_code >= 500)
    cutoff = time.time() - WINDOW_MINUTES * 60
    last_15min = sum(1 for e in entries if e.timestamp >= cutoff)

    return EndpointMetrics(
        endpoint=key,
        count=len(entries),
        p50_ms=round(_percentile(latencies, 0.50), 2),
        p95_ms=round(_percentile(latencies, 0.95), 2),
        p99_ms=round(_percentile(latencies, 0.99), 2),
        payload_avg_kb=round(statistics.mean(payloads) / 1024.0, 2),
        payload_max_kb=round(max(payloads) / 1024.0, 2),
        error_rate=round(errors / len(entries), 4),
        last_15min_count=last_15min,
    )


# ── Endpoints ────────────────────────────────────────────────────────


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(_admin=Depends(require_platform_admin)):
    """Snapshot des métriques performance backend.

    Réservé admin platform (Q10=A — pas de monitoring externe en MV3).
    Renvoie 1 entrée par couple `(method, path normalisé)` trié alphabétiquement.
    """
    snapshot = get_store().snapshot()
    endpoints = [_compute_endpoint_metrics(key, entries) for key, entries in sorted(snapshot.items())]
    return MetricsResponse(
        endpoints=endpoints,
        window_minutes=WINDOW_MINUTES,
        captured_at=time.time(),
    )


@router.get("/alerts", response_model=AlertsResponse)
def get_alerts(_admin=Depends(require_platform_admin)):
    """Liste des SLO breaches actifs vs budgets MV3.

    Réservé admin. Source de vérité Q8=A+B (pull, pas push).
    `since_ts` = timestamp de la première entry dans la fenêtre rolling — utile
    pour identifier le début de la dégradation côté logs serveur.
    """
    snapshot = get_store().snapshot()
    alerts: list[AlertEntry] = []

    for key, entries in snapshot.items():
        if not entries:
            continue
        m = _compute_endpoint_metrics(key, entries)
        since_ts = entries[0].timestamp  # première entry de la fenêtre rolling

        if m.p95_ms > LATENCY_P95_BUDGET_MS:
            alerts.append(
                AlertEntry(
                    endpoint=key,
                    type="latency_p95",
                    threshold=float(LATENCY_P95_BUDGET_MS),
                    actual=m.p95_ms,
                    since_ts=since_ts,
                )
            )
        if m.payload_avg_kb > PAYLOAD_AVG_BUDGET_KB:
            alerts.append(
                AlertEntry(
                    endpoint=key,
                    type="payload_avg",
                    threshold=float(PAYLOAD_AVG_BUDGET_KB),
                    actual=m.payload_avg_kb,
                    since_ts=since_ts,
                )
            )
        if m.error_rate > ERROR_RATE_BUDGET:
            alerts.append(
                AlertEntry(
                    endpoint=key,
                    type="error_rate",
                    threshold=ERROR_RATE_BUDGET,
                    actual=m.error_rate,
                    since_ts=since_ts,
                )
            )

    return AlertsResponse(
        alerts=alerts,
        budgets={
            "latency_p95_budget_ms": float(LATENCY_P95_BUDGET_MS),
            "payload_avg_budget_kb": float(PAYLOAD_AVG_BUDGET_KB),
            "error_rate_budget": ERROR_RATE_BUDGET,
        },
        captured_at=time.time(),
    )
