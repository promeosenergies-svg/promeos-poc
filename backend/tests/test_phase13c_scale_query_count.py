"""Phase 13.C — Test query count batch (avant/après N+1 fix).

Vérifie que `get_baselines_a_batch` exécute O(1) queries quel que soit
le nombre de sites passés (N=1, N=10, N=80) — preuve de non-régression
N+1 sur le hot path /_facts pour le persona Antoine 80 sites.

Avant Phase 13.C P0-1 :
  - get_baseline_a × N sites = 2N queries (meter_ids + readings par site)

Après :
  - get_baselines_a_batch × N sites = 1 query (JOIN Meter↔MeterReading)

Ce test garantit la non-régression future si quelqu'un re-introduisait
un loop Python avec get_baseline_a dans le hot path.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest


def _count_queries(query_log: list, kind: str = None) -> int:
    """Compte les queries SQL exécutées (toutes ou filtrées par kind)."""
    if kind is None:
        return len(query_log)
    return sum(1 for q in query_log if kind.lower() in q.lower())


@pytest.fixture
def event_log():
    """Capture chaque exécution SQL via SQLAlchemy event listeners."""
    from sqlalchemy import event
    from database import SessionLocal

    log: list[str] = []

    def receive(conn, cursor, statement, *args, **kwargs):
        log.append(statement)

    db = SessionLocal()
    engine = db.get_bind()
    event.listen(engine, "before_cursor_execute", receive)
    yield (db, log)
    event.remove(engine, "before_cursor_execute", receive)
    db.close()


class TestBaselineABatchQueryCount:
    """Non-régression query count pour get_baselines_a_batch."""

    def test_one_query_for_one_site(self, event_log):
        """Pour 1 site, le batch effectue exactement 1 query (JOIN)."""
        from services.baseline_service import get_baselines_a_batch

        db, log = event_log
        log.clear()

        # Test avec un site_id qui peut ou pas avoir des readings
        result = get_baselines_a_batch(db, [1], date(2026, 4, 27))

        # 1 query SELECT (JOIN Meter↔MeterReading)
        select_count = _count_queries(log, "SELECT")
        assert select_count == 1, f"Attendu 1 SELECT, observé {select_count}: {log}"
        assert isinstance(result, dict)
        assert 1 in result

    def test_one_query_for_ten_sites(self, event_log):
        """Pour 10 sites, le batch reste à 1 query (preuve O(1) vs N+1)."""
        from services.baseline_service import get_baselines_a_batch

        db, log = event_log
        log.clear()

        site_ids = list(range(1, 11))
        result = get_baselines_a_batch(db, site_ids, date(2026, 4, 27))

        select_count = _count_queries(log, "SELECT")
        assert select_count == 1, f"Attendu 1 SELECT pour 10 sites, observé {select_count}"
        assert len(result) == 10

    def test_one_query_for_eighty_sites(self, event_log):
        """Persona Antoine : 80 sites → toujours 1 SELECT (P0-1 véracité scale).

        Avant Phase 13.C P0-1 : 2 × 80 = 160 queries ; après : 1.
        """
        from services.baseline_service import get_baselines_a_batch

        db, log = event_log
        log.clear()

        site_ids = list(range(1, 81))
        result = get_baselines_a_batch(db, site_ids, date(2026, 4, 27))

        select_count = _count_queries(log, "SELECT")
        assert select_count == 1, (
            f"REGRESSION N+1 Phase 13.C : attendu 1 SELECT pour 80 sites, "
            f"observé {select_count}. Persona Antoine (80 sites) cassé."
        )
        # Tous les sites doivent être présents (même si certains n'ont pas de data)
        assert len(result) == 80

    def test_empty_site_ids_zero_queries(self, event_log):
        """Liste vide → court-circuit, zéro query SQL."""
        from services.baseline_service import get_baselines_a_batch

        db, log = event_log
        log.clear()

        result = get_baselines_a_batch(db, [], date(2026, 4, 27))

        select_count = _count_queries(log, "SELECT")
        assert select_count == 0, f"Liste vide doit court-circuiter, observé {select_count}"
        assert result == {}


class TestBaselineABatchSemantics:
    """Vérifie que la version batch retourne les mêmes valeurs que la version unitaire."""

    def test_batch_matches_unit_value(self, event_log):
        """get_baselines_a_batch[sid] == get_baseline_a(sid) pour chaque site testé.

        Garantit zéro divergence sémantique entre les deux APIs (sinon Phase
        13.C casserait la véracité au lieu de l'améliorer).
        """
        from services.baseline_service import get_baseline_a, get_baselines_a_batch

        db, _ = event_log
        target = date(2026, 4, 27)

        # Test sur sites 1, 2, 3 (5 sites HELIOS seedés)
        for sid in [1, 2, 3]:
            unit = get_baseline_a(db, sid, target)
            batch = get_baselines_a_batch(db, [sid], target)
            assert sid in batch, f"site {sid} absent du batch result"
            assert batch[sid]["value_kwh"] == pytest.approx(unit["value_kwh"], rel=1e-6), (
                f"Divergence batch vs unit pour site {sid} : "
                f"batch={batch[sid]['value_kwh']} vs unit={unit['value_kwh']}"
            )
            assert batch[sid]["data_points"] == unit["data_points"]
            assert batch[sid]["confidence"] == unit["confidence"]
