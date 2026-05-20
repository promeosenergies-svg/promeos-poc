"""M2-5.8.C — Tests du seed Use Case A (idempotence + garde organisation).

Tests d'intégration : `SessionLocal` réelle (même pattern que `test_demo_login.py`).
Le seed `seed_use_case_a_actions` n'avait aucun test dédié — comble la dette
relevée par l'audit M2-5 (qa-guardian).
"""

import pytest

from database import SessionLocal
from seeds.use_case_a_seed import USE_CASE_A_SPECS, seed_use_case_a_actions
from seeds.v4_seed import SeedError


def test_seed_use_case_a_is_idempotent():
    """Ré-exécution du seed → 0 action créée, toutes ignorées (PK UUID5 stables).

    Deux runs successifs : on vérifie le rapport du SECOND, indépendant de
    l'état de départ de la base.
    """
    db = SessionLocal()
    try:
        seed_use_case_a_actions(db)  # garantit l'état seedé
        report = seed_use_case_a_actions(db)  # second run
        assert report.actions_created == 0, "un 2e run ne doit créer aucune action"
        assert report.actions_skipped == len(USE_CASE_A_SPECS)
    finally:
        db.close()


def test_seed_use_case_a_raises_seederror_on_missing_org():
    """org_id inexistant → `SeedError` explicite (pas une IntegrityError nue)."""
    db = SessionLocal()
    try:
        with pytest.raises(SeedError):
            seed_use_case_a_actions(db, org_id=999_999)
    finally:
        db.close()
