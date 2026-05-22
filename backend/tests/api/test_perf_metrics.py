"""M2-6.A.3 — Tests middleware perf_metrics + endpoints /health/metrics + /health/alerts.

Couverture (10 tests) :

Utilities (3) :
- normalize_path : UUID, numeric id, static path inchangé

Store thread-safety + rolling window (3) :
- Concurrent writes (5 threads × 100 entries → 100 retenues à maxlen=100)
- Rolling window cap maxlen
- Snapshot retourne copie indépendante (mutation post-snapshot OK)

Endpoints (4) :
- /health/metrics requires admin (403 non-admin)
- /health/metrics retourne structure attendue + tracking item /v4
- /health excludes /health/* du tracking lui-même
- /health/alerts force breach latency → alerte présente
"""

import threading
import time

from middleware.perf_metrics import (
    MAX_ENTRIES_PER_ENDPOINT,
    MetricEntry,
    PerfMetricsStore,
    get_store,
    normalize_path,
)


# ═══════════════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════════════


class TestNormalizePath:
    def test_normalizes_uuid_to_placeholder(self):
        path = "/api/v4/items/abc12345-1234-1234-1234-123456789abc"
        assert normalize_path(path) == "/api/v4/items/{id}"

    def test_normalizes_numeric_id_mid_path(self):
        assert normalize_path("/api/admin/users/42/purge") == "/api/admin/users/{id}/purge"

    def test_static_paths_unchanged(self):
        assert normalize_path("/api/v4/action-center/items") == "/api/v4/action-center/items"
        assert normalize_path("/health/metrics") == "/health/metrics"


# ═══════════════════════════════════════════════════════════════════════
# Store thread-safety + rolling window
# ═══════════════════════════════════════════════════════════════════════


class TestStoreThreadSafety:
    def test_concurrent_writes_no_race_caps_at_max_entries(self):
        """5 threads × 100 writes sur même clé → 100 retenues (maxlen=100)."""
        store = PerfMetricsStore(max_entries=100)

        def add_entries(n: int):
            for _ in range(n):
                store.add(
                    "GET /test",
                    MetricEntry(
                        timestamp=time.time(),
                        latency_ms=10.0,
                        payload_bytes=1024,
                        status_code=200,
                        method="GET",
                    ),
                )

        threads = [threading.Thread(target=add_entries, args=(100,)) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        snapshot = store.snapshot()
        assert len(snapshot["GET /test"]) == 100  # cap maxlen, pas 500

    def test_rolling_window_keeps_most_recent(self):
        """deque maxlen évince les plus anciennes, garde les plus récentes."""
        store = PerfMetricsStore(max_entries=10)
        for i in range(50):
            store.add(
                "GET /x",
                MetricEntry(
                    timestamp=time.time(),
                    latency_ms=float(i),
                    payload_bytes=0,
                    status_code=200,
                    method="GET",
                ),
            )
        snapshot = store.snapshot()
        assert len(snapshot["GET /x"]) == 10
        # Les 10 dernières (40..49) restent
        assert snapshot["GET /x"][-1].latency_ms == 49.0
        assert snapshot["GET /x"][0].latency_ms == 40.0

    def test_snapshot_is_independent_copy(self):
        """Mutation du store après snapshot ne change pas la copie."""
        store = PerfMetricsStore(max_entries=100)
        entry = MetricEntry(timestamp=time.time(), latency_ms=1.0, payload_bytes=0, status_code=200, method="GET")
        store.add("GET /a", entry)
        snap = store.snapshot()
        assert len(snap["GET /a"]) == 1

        store.add("GET /a", entry)  # mutation après snap
        assert len(snap["GET /a"]) == 1  # snap inchangé
        assert len(store.snapshot()["GET /a"]) == 2


# ═══════════════════════════════════════════════════════════════════════
# Endpoints /health/metrics + /health/alerts (via app_client)
# ═══════════════════════════════════════════════════════════════════════


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestMetricsEndpoint:
    def test_metrics_requires_admin(self, app_client, user_token):
        """user_token (energy_manager) → 403."""
        client, _ = app_client
        get_store().clear()
        r = client.get("/health/metrics", headers=_h(user_token))
        assert r.status_code == 403

    def test_metrics_returns_structured_data_and_tracks_v4_route(self, app_client, admin_token):
        """Hits /api/v4/action-center/items → la route apparaît dans /health/metrics."""
        client, _ = app_client
        get_store().clear()

        # Génère 3 requests sur la route V4 (status code peu importe — 200 ou 401, le
        # tracking se fait peu importe le résultat tant que la requête passe le middleware).
        for _ in range(3):
            client.get("/api/v4/action-center/items", headers=_h(admin_token))

        r = client.get("/health/metrics", headers=_h(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert "endpoints" in data
        assert "window_minutes" in data
        assert data["window_minutes"] == 15
        assert "captured_at" in data

        tracked_endpoints = [e["endpoint"] for e in data["endpoints"]]
        assert any("/api/v4/action-center/items" in ep for ep in tracked_endpoints), (
            f"Route V4 absente du tracking. Tracked: {tracked_endpoints}"
        )

    def test_health_endpoints_excluded_from_tracking(self, app_client, admin_token):
        """Anti-récursion : /health/metrics + /health/alerts ne se trackent pas eux-mêmes."""
        client, _ = app_client
        get_store().clear()

        # Hit /health/metrics plusieurs fois
        for _ in range(3):
            client.get("/health/metrics", headers=_h(admin_token))
        # Hit /health/alerts aussi
        client.get("/health/alerts", headers=_h(admin_token))

        # Lecture finale du store
        snapshot = get_store().snapshot()
        for key in snapshot:
            assert "/health" not in key, f"/health/* leak: {key}"


class TestAlertsEndpoint:
    def test_alerts_requires_admin(self, app_client, user_token):
        client, _ = app_client
        get_store().clear()
        r = client.get("/health/alerts", headers=_h(user_token))
        assert r.status_code == 403

    def test_alerts_lists_latency_breach_when_p95_exceeds_budget(self, app_client, admin_token):
        """Inject entries lentes → /health/alerts liste un latency_p95 breach."""
        client, _ = app_client
        store = get_store()
        store.clear()

        # 20 entries à 10s chacune → P95 = 10000ms > budget 500ms
        for _ in range(20):
            store.add(
                "GET /api/test-slow",
                MetricEntry(
                    timestamp=time.time(),
                    latency_ms=10_000.0,
                    payload_bytes=1024,
                    status_code=200,
                    method="GET",
                ),
            )

        r = client.get("/health/alerts", headers=_h(admin_token))
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data
        assert "budgets" in data
        assert data["budgets"]["latency_p95_budget_ms"] == 500.0

        latency_alerts = [a for a in data["alerts"] if a["type"] == "latency_p95"]
        assert len(latency_alerts) >= 1
        breach = next(a for a in latency_alerts if a["endpoint"] == "GET /api/test-slow")
        assert breach["threshold"] == 500.0
        assert breach["actual"] >= 500.0  # P95 ≥ budget pour déclencher
        assert breach["actual"] == 10_000.0  # toutes les latencies identiques

    def test_alerts_empty_when_within_budget(self, app_client, admin_token):
        """Entries rapides (≤ budget) → pas d'alerte latency_p95 pour cet endpoint."""
        client, _ = app_client
        store = get_store()
        store.clear()

        for _ in range(20):
            store.add(
                "GET /api/test-fast",
                MetricEntry(
                    timestamp=time.time(),
                    latency_ms=42.0,  # bien sous 500ms
                    payload_bytes=512,
                    status_code=200,
                    method="GET",
                ),
            )

        r = client.get("/health/alerts", headers=_h(admin_token))
        data = r.json()
        # Aucune alerte pour cet endpoint spécifique
        endpoint_alerts = [a for a in data["alerts"] if a["endpoint"] == "GET /api/test-fast"]
        assert endpoint_alerts == []


# Sanity check : la constante exportée est cohérente avec sa value attendue
def test_max_entries_constant_is_1000():
    assert MAX_ENTRIES_PER_ENDPOINT == 1000
