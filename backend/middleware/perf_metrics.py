"""M2-6.A.3 — Middleware capture latency + payload + error rate par endpoint.

Pattern hybride (Q6=C) :
  - In-memory rolling window (`deque` max 1000 entries par endpoint)
  - Thread-safe via `threading.Lock`
  - Excludes méta-endpoints (anti-récursion + anti-bruit) : `/health`, `/api/health`,
    `/docs`, `/openapi.json`, `/favicon.ico`
  - Path normalization UUID/numeric → `{id}` (groupement routes paramétrées)

Pas de dépendance Prometheus / StatsD / OpenTelemetry en MV3. Structure prête
pour migration M3+ (cf. RUNBOOK_OBSERVABILITY.md plan évolution).

Cardinal ordre middleware : à enregistrer **APRÈS** tous les autres dans
`main.py` (LIFO Starlette → wraps tout le pipeline, capture latency totale
y compris auth + ORM + sérialisation).
"""

from __future__ import annotations

import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# ── Configuration ───────────────────────────────────────────────────────

MAX_ENTRIES_PER_ENDPOINT = 1000
WINDOW_MINUTES = 15

# Préfixes à exclure du tracking (anti-récursion + anti-bruit méta).
# IMPORTANT : utiliser des chemins ≥ 2 segments OU paths exacts pour ne pas
# matcher accidentellement `/healthcheck` ou `/api/health-data` métier.
EXCLUDED_EXACT_PATHS = frozenset({"/health", "/api/health", "/", "/favicon.ico"})
EXCLUDED_PREFIXES = ("/health/", "/docs", "/openapi.json", "/redoc")

# Regex path normalization — figées en module-level (pas recompilées par requête)
_UUID_RE = re.compile(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
_NUMERIC_ID_RE = re.compile(r"/\d+(?=/|$)")


@dataclass
class MetricEntry:
    """Une mesure unitaire de requête HTTP."""

    timestamp: float  # `time.time()` UTC epoch — pour fenêtre rolling
    latency_ms: float  # `perf_counter` delta — monotone
    payload_bytes: int  # 0 si chunked / streaming (MV3 acceptable)
    status_code: int
    method: str


class PerfMetricsStore:
    """Store thread-safe : une `deque` par couple (method, normalized_path).

    `max_entries` cap par endpoint évite explosion mémoire sur trafic soutenu.
    Avec 100 endpoints × 1000 entries × ~80 bytes/entry ≈ 8 MB max.
    """

    def __init__(self, max_entries: int = MAX_ENTRIES_PER_ENDPOINT):
        self.max_entries = max_entries
        self.entries: dict[str, deque[MetricEntry]] = defaultdict(lambda: deque(maxlen=self.max_entries))
        self.lock = threading.Lock()

    def add(self, key: str, entry: MetricEntry) -> None:
        with self.lock:
            self.entries[key].append(entry)

    def snapshot(self) -> dict[str, list[MetricEntry]]:
        """Copy thread-safe pour calcul stats (évite mutation pendant lecture)."""
        with self.lock:
            return {k: list(v) for k, v in self.entries.items()}

    def clear(self) -> None:
        """Vide tout le store (tests + reset manuel admin)."""
        with self.lock:
            self.entries.clear()


# Singleton global — importé par les endpoints health
_store = PerfMetricsStore()


def get_store() -> PerfMetricsStore:
    """Accesseur public pour endpoints `/health/metrics` + `/health/alerts` + tests."""
    return _store


def normalize_path(path: str) -> str:
    """Normalise les paths pour grouper les routes paramétrées.

    Exemples :
      `/api/v4/items/abc12345-1234-1234-1234-123456789abc` → `/api/v4/items/{id}`
      `/api/admin/users/42/purge` → `/api/admin/users/{id}/purge`
      `/api/v4/items` → `/api/v4/items` (inchangé)
    """
    path = _UUID_RE.sub("/{id}", path)
    path = _NUMERIC_ID_RE.sub("/{id}", path)
    return path


def _should_exclude(path: str) -> bool:
    """True si le path doit être ignoré du tracking (méta-endpoint)."""
    if path in EXCLUDED_EXACT_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES)


class PerfMetricsMiddleware(BaseHTTPMiddleware):
    """Capture latency + payload + status code de chaque requête HTTP.

    Pattern : `time.perf_counter()` pour latency (monotone), `time.time()` pour
    timestamp epoch (fenêtre 15min). Ne jamais mélanger les deux horloges.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if _should_exclude(path):
            return await call_next(request)

        start = time.perf_counter()
        response: Optional[Response] = None
        status_code = 500  # default si exception non capturée par FastAPI

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            latency_ms = (time.perf_counter() - start) * 1000.0

            # Estimation payload size : content-length header si présent. Si
            # chunked / streaming, on enregistre 0 (acceptable MV3 — runbook
            # documente la limitation).
            payload_bytes = 0
            if response is not None:
                cl = response.headers.get("content-length")
                if cl and cl.isdigit():
                    payload_bytes = int(cl)

            entry = MetricEntry(
                timestamp=time.time(),
                latency_ms=latency_ms,
                payload_bytes=payload_bytes,
                status_code=status_code,
                method=request.method,
            )

            normalized = normalize_path(path)
            key = f"{request.method} {normalized}"
            _store.add(key, entry)
