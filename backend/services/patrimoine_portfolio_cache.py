"""
patrimoine_portfolio_cache.py — Cache snapshot in-memory pour Portfolio Trend (V62)

Objectif : stocker le dernier snapshot calculé par org_id pour dériver un trend
  (delta risk_eur, delta sites_count, direction) au prochain appel.

Design :
  - Dictionnaire global protégé par threading.Lock() — safe FastAPI multi-worker
    (single process avec plusieurs threads : Uvicorn workers partagent ce module).
  - Snapshot minimal : { computed_at, total_estimated_risk_eur, sites_count }.
  - Isolé par org_id (int). Jamais mis en cache si org_id is None.
  - Pas de TTL : snapshot valide jusqu'au prochain appel ou reset explicite.
    Le cas "snapshot périmé" (ex : restart serveur) se traduit par trend=None
    lors du premier appel post-restart (comportement attendu et documenté).

API publique :
  get_prev_snapshot(org_id)   → dict | None
  set_snapshot(org_id, snap)  → None
  clear_snapshot(org_id)      → None
  clear_all()                 → None   (invalidation globale, ex : demo reset)
"""

from __future__ import annotations

import threading
from typing import Dict, Any, Optional

# ── État global ──────────────────────────────────────────────────────────────

_lock: threading.Lock = threading.Lock()

# { org_id: { "computed_at": str, "total_estimated_risk_eur": float, "sites_count": int } }
_cache: Dict[int, Dict[str, Any]] = {}


# ── API publique ──────────────────────────────────────────────────────────────


def get_prev_snapshot(org_id: int) -> Optional[Dict[str, Any]]:
    """Retourne le snapshot précédent pour l'org, ou None s'il n'existe pas."""
    if org_id is None:
        return None
    with _lock:
        return _cache.get(org_id)


def set_snapshot(org_id: int, snapshot: Dict[str, Any]) -> None:
    """Stocke un snapshot minimal pour l'org.

    snapshot attendu (sous-ensemble utilisé) :
      {
        "computed_at":               str   (ISO 8601),
        "total_estimated_risk_eur":  float,
        "sites_count":               int,
      }
    Tout champ supplémentaire est ignoré.
    """
    if org_id is None:
        return
    minimal = {
        "computed_at": snapshot.get("computed_at", ""),
        "total_estimated_risk_eur": float(snapshot.get("total_estimated_risk_eur", 0.0)),
        "sites_count": int(snapshot.get("sites_count", 0)),
    }
    with _lock:
        _cache[org_id] = minimal


def clear_snapshot(org_id: int) -> None:
    """Supprime le snapshot d'une org spécifique."""
    if org_id is None:
        return
    with _lock:
        _cache.pop(org_id, None)


def clear_all() -> None:
    """Vide tout le cache — typiquement appelé après un demo reset."""
    with _lock:
        _cache.clear()
