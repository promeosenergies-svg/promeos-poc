"""
PROMEOS Watchers - Registry avec auto-discovery
"""

from typing import Dict, Optional
from .base import Watcher
from . import rss_watcher, legifrance_watcher, cre_watcher, rte_watcher


_WATCHERS: Dict[str, Watcher] = {}


def _register_all():
    """Auto-discovery de tous les watchers."""
    if _WATCHERS:
        return

    watchers = [
        legifrance_watcher.LegifranceWatcher(),
        cre_watcher.CREWatcher(),
        rte_watcher.RTEWatcher(),
    ]

    for watcher in watchers:
        _WATCHERS[watcher.name] = watcher


def list_watchers() -> list[dict]:
    """Liste tous les watchers disponibles."""
    _register_all()
    return [
        {
            "name": w.name,
            "description": w.description,
            "source_url": w.source_url,
        }
        for w in _WATCHERS.values()
    ]


def run_watcher(name: str, db) -> list:
    """Execute un watcher."""
    _register_all()
    watcher = _WATCHERS.get(name)
    if not watcher:
        raise ValueError(f"Watcher {name} not found")
    return watcher.check(db)
