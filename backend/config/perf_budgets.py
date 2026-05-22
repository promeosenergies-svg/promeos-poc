"""M2-6.A.3 — Budgets perf MV3 conservateurs (Q7).

Approche : commencer large pour MV3 (éviter faux-positifs alertes), serrer
post-pilote selon mesures réelles (cf. RUNBOOK_OBSERVABILITY.md procédure
ajustement). Override par endpoint possible si certains sont critiques
(e.g. `/v4/items` critique UX → budget P95 200ms post-pilote).

Constantes immuables — toute modif doit passer par PR + RUNBOOK update.
"""

# ── Budgets globaux MV3 ──────────────────────────────────────────────

# P95 latency par endpoint (ms). 500ms = seuil au-delà duquel un UX humain
# perçoit la latence comme un délai (Nielsen Norman Group). Conservateur :
# inclut tout l'overhead (auth + ORM + sérialisation + middleware chain).
LATENCY_P95_BUDGET_MS = 500

# Payload moyen par endpoint (kB). 200kB = limite raisonnable pour mobile 3G
# (TTI ~2s sur 100 kB/s). Couvre l'ensemble agrégat (list V4 items, summary).
PAYLOAD_AVG_BUDGET_KB = 200

# Error rate (status >= 500) sur fenêtre rolling 15min. 2% = seuil au-delà
# duquel on déclare une dégradation (vs simple bruit). À serrer post-pilote
# pour atteindre 0.1% (1 erreur sur 1000 requêtes).
ERROR_RATE_BUDGET = 0.02


# ── Overrides par endpoint (M3+ si besoin) ──────────────────────────
#
# Format : {endpoint_key: {'latency_p95_ms': X, 'payload_avg_kb': Y, 'error_rate': Z}}
# `endpoint_key` = "METHOD /path/normalisé" (cf. `middleware.perf_metrics.normalize_path`).
# Les overrides remplacent les budgets globaux pour le seul endpoint cible.
#
# Désactivé en MV3 (Q7 — pas d'optimisation prématurée). Activer post-pilote
# après collecte 7+ jours de mesures réelles.
ENDPOINT_OVERRIDES: dict[str, dict[str, float]] = {
    # Exemples à activer post-pilote (commentés) :
    # "GET /api/v4/action-center/items": {
    #     "latency_p95_ms": 200,   # critique UX pilote (liste principale)
    # },
    # "GET /api/v4/action-center/summary": {
    #     "latency_p95_ms": 150,   # NarrativeBar visible au-dessus du fold
    # },
}
