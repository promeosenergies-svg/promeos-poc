"""Tests du seed V4 minimal — Sprint M2-4.1.bis.

Couvre : idempotence stricte (C1), FK `organisation_id` ON DELETE RESTRICT
effective, PRAGMA foreign_keys de production (C2), intégration repo org-scopée.

Fixture `v4_session` (conftest voisin) : SQLite in-memory, 8 tables V4 + stub
`organisations` seedé (org id=1). `foreign_keys=ON`.
"""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from middleware.org_context import reset_org_context, set_org_context
from models.v4.action_center_items import ActionCenterItem
from repositories.base_v4 import BaseRepositoryV4
from seeds.v4_seed import SeedError, SeedReport, seed_v4_minimal
from seeds.v4_seed_constants import SEED_ACTION_SPECS, SEED_ORG_ID, seed_item_uuid


def _count_items(db) -> int:
    return db.scalar(select(func.count()).select_from(ActionCenterItem))


# ─────────────────────────────────────────────────────────────────────
# 1. Idempotence — cœur du sprint (C1)
# ─────────────────────────────────────────────────────────────────────


def test_seed_creates_items_first_run(v4_session):
    """Premier run : 3 action_center_items créés, 0 ignoré."""
    report = seed_v4_minimal(v4_session, org_id=SEED_ORG_ID)
    assert isinstance(report, SeedReport)
    assert report.items_created == 3
    assert report.items_skipped == 0
    assert _count_items(v4_session) == 3


def test_seed_idempotent_second_run(v4_session):
    """Deuxième run consécutif : 0 créé, 3 ignorés, COUNT inchangé (idempotence C1)."""
    seed_v4_minimal(v4_session, org_id=SEED_ORG_ID)
    report2 = seed_v4_minimal(v4_session, org_id=SEED_ORG_ID)
    assert report2.items_created == 0
    assert report2.items_skipped == 3
    assert _count_items(v4_session) == 3, "idempotence : aucun doublon au 2e run"


def test_seed_action_pk_deterministic(v4_session):
    """PK UUID5 déterministe : les IDs en DB == UUID5 des slugs (base de l'idempotence)."""
    seed_v4_minimal(v4_session, org_id=SEED_ORG_ID)
    expected_ids = {seed_item_uuid(spec["slug"]) for spec in SEED_ACTION_SPECS}
    db_ids = set(v4_session.scalars(select(ActionCenterItem.id)).all())
    assert db_ids == expected_ids


# ─────────────────────────────────────────────────────────────────────
# 2. Garde-fous : org absente + closure consistency
# ─────────────────────────────────────────────────────────────────────


def test_seed_missing_org_raises_seederror(v4_session):
    """org_id inexistant → SeedError (le seed ne crée pas d'organisation, D5)."""
    with pytest.raises(SeedError, match="introuvable"):
        seed_v4_minimal(v4_session, org_id=999_999)
    assert _count_items(v4_session) == 0, "aucun item inséré si l'org est absente"


def test_seeded_closed_item_satisfies_closure_consistency(v4_session):
    """🛡️ IL10 : l'item 'closed' porte closed_at + closure_reason (chk_closure_consistency)."""
    seed_v4_minimal(v4_session, org_id=SEED_ORG_ID)
    closed = v4_session.get(ActionCenterItem, seed_item_uuid("resolu"))
    assert closed.lifecycle_state == "closed"
    assert closed.closed_at is not None
    assert closed.closure_reason == "resolved"


# ─────────────────────────────────────────────────────────────────────
# 3. FK RESTRICT effective + PRAGMA (C2 / D6)
# ─────────────────────────────────────────────────────────────────────


def test_fk_restrict_blocks_org_deletion_with_actions(v4_session):
    """🛡️ FK organisation_id ON DELETE RESTRICT : supprimer l'org seedée → IntegrityError.

    `match` épingle la violation FK (RESTRICT immédiat SQLite) — le DELETE lui-même
    lève, pas un effet de bord plus loin.
    """
    seed_v4_minimal(v4_session, org_id=SEED_ORG_ID)
    with pytest.raises(IntegrityError, match="(?i)foreign key"):
        v4_session.execute(text("DELETE FROM organisations WHERE id = :id"), {"id": SEED_ORG_ID})
    v4_session.rollback()
    # L'org et les items survivent au DELETE refusé.
    assert _count_items(v4_session) == 3


def test_production_engine_enforces_foreign_keys():
    """Non-régression C2 : l'engine de production applique PRAGMA foreign_keys=ON.

    Garde-fou contre une suppression du listener `_set_sqlite_pragma`
    (`database/connection.py`) — sans lui, ON DELETE RESTRICT serait inopérant.
    """
    from database.connection import engine

    if engine.dialect.name != "sqlite":
        pytest.skip("PRAGMA foreign_keys spécifique SQLite (PostgreSQL enforce nativement)")
    with engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


# ─────────────────────────────────────────────────────────────────────
# 4. Intégration repo org-scopée (remplace l'e2e HTTP — endpoints V4 = M2-4.2+)
# ─────────────────────────────────────────────────────────────────────


def test_seeded_items_visible_through_v4_repo(v4_session):
    """Les items seedés sont lisibles via BaseRepositoryV4, et UNIQUEMENT dans leur org.

    Remplace le test e2e HTTP §4.3 (les endpoints V4 n'existent pas avant M2-4.2).
    Prouve la chaîne seed → contexte org → repo org-scopé.
    """
    seed_v4_minimal(v4_session, org_id=SEED_ORG_ID)

    class ActionCenterItemRepo(BaseRepositoryV4[ActionCenterItem]):
        model = ActionCenterItem

    repo = ActionCenterItemRepo(v4_session)

    token = set_org_context(SEED_ORG_ID)
    try:
        items = repo.list_all()
    finally:
        reset_org_context(token)
    assert len(items) == 3
    assert all(it.organisation_id == SEED_ORG_ID for it in items)

    # Org-scoping : un autre contexte org ne voit aucun item seedé.
    token_other = set_org_context(424242)
    try:
        assert repo.list_all() == []
    finally:
        reset_org_context(token_other)
