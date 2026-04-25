"""Sprint CX P1 residual : wiring invalidate_membership_cache sur CRUD UserOrgRole.

Vérifie que les mutations UserOrgRole (via service layer + routes admin) purgent
bien le cache membership. Avant ce wiring, un user retiré d'une org continuait à
logger des events pendant ≤ 5 min (TTL _MEMBERSHIP_CACHE).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Organisation
from models.iam import User, UserOrgRole, UserRole
from services.iam_service import assign_role, remove_role
from middleware.cx_logger import (
    _MEMBERSHIP_CACHE,
    _is_member_cached,
    invalidate_membership_cache,
)


pytestmark = pytest.mark.fast


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    invalidate_membership_cache()  # Isole le cache entre tests (module-level)
    yield session
    invalidate_membership_cache()
    session.close()


def _seed_user_and_org(db, user_id: int, org_id: int) -> None:
    user = User(
        id=user_id,
        email=f"u{user_id}@test.io",
        hashed_password="x",
        nom=f"U{user_id}",
        prenom=f"F{user_id}",
    )
    org = Organisation(id=org_id, nom=f"Org{org_id}")
    db.add_all([user, org])
    db.flush()


# ============================================================
# assign_role invalide le cache
# ============================================================


def test_assign_role_invalidates_cache(db_session):
    """Après assign_role, le cache pour (user_id, org_id) doit être vide
    → prochain _is_member_cached re-query la DB et retourne True."""
    _seed_user_and_org(db_session, user_id=1, org_id=1)

    # Peuple le cache avec une valeur False (pas de membership encore)
    assert _is_member_cached(db_session, 1, 1) is False
    assert (1, 1) in _MEMBERSHIP_CACHE
    assert _MEMBERSHIP_CACHE[(1, 1)][0] is False

    # Crée le role via le service
    assign_role(db_session, user_id=1, org_id=1, role=UserRole.DG_OWNER)
    db_session.flush()

    # Le cache doit avoir été purgé
    assert (1, 1) not in _MEMBERSHIP_CACHE

    # Prochain check → re-query DB → True
    assert _is_member_cached(db_session, 1, 1) is True


# ============================================================
# remove_role invalide le cache
# ============================================================


def test_remove_role_invalidates_cache(db_session):
    """Après remove_role, le cache doit être purgé → prochain check renvoie False
    (et non la valeur mise en cache pré-révocation)."""
    _seed_user_and_org(db_session, user_id=2, org_id=2)

    # Seed 2 DG_OWNER pour éviter last-owner protection
    assign_role(db_session, user_id=2, org_id=2, role=UserRole.DG_OWNER)
    # 2e DG_OWNER en DB direct (pour ne pas polluer le cache avec une 2e entrée)
    other_user = User(id=22, email="u22@test.io", hashed_password="x", nom="U22", prenom="F22")
    db_session.add(other_user)
    db_session.flush()
    other_uor = UserOrgRole(user_id=22, org_id=2, role=UserRole.DG_OWNER)
    db_session.add(other_uor)
    db_session.flush()

    # Peuple le cache (True)
    assert _is_member_cached(db_session, 2, 2) is True
    assert _MEMBERSHIP_CACHE[(2, 2)][0] is True

    # Retire le role
    ok = remove_role(db_session, user_id=2, org_id=2)
    assert ok is True

    # Cache doit être purgé
    assert (2, 2) not in _MEMBERSHIP_CACHE

    # Prochain check → re-query DB → False
    assert _is_member_cached(db_session, 2, 2) is False


def test_remove_role_not_found_does_not_crash(db_session):
    """Si remove_role échoue (user pas membre), pas d'erreur sur l'invalidate."""
    _seed_user_and_org(db_session, user_id=3, org_id=3)
    # Pas de UserOrgRole → remove_role retourne False sans toucher le cache
    ok = remove_role(db_session, user_id=3, org_id=3)
    assert ok is False


# ============================================================
# Cache purge spécifique à la paire, pas global
# ============================================================


def test_assign_role_only_invalidates_matching_pair(db_session):
    """L'invalidation doit cibler (user_id, org_id) uniquement — les autres
    entrées restent intactes."""
    _seed_user_and_org(db_session, user_id=4, org_id=4)
    _seed_user_and_org(db_session, user_id=5, org_id=5)

    # Peuple cache pour 2 paires distinctes
    assert _is_member_cached(db_session, 4, 4) is False
    assert _is_member_cached(db_session, 5, 5) is False
    assert (4, 4) in _MEMBERSHIP_CACHE
    assert (5, 5) in _MEMBERSHIP_CACHE

    # Mutation sur (4, 4) uniquement
    assign_role(db_session, user_id=4, org_id=4, role=UserRole.DG_OWNER)

    # (4, 4) purgé, (5, 5) intact
    assert (4, 4) not in _MEMBERSHIP_CACHE
    assert (5, 5) in _MEMBERSHIP_CACHE


# ============================================================
# Cache vraiment vidé — pas juste refresh avec valeur stale
# ============================================================


def test_cache_invalidation_forces_db_requery(db_session):
    """Prouve que l'invalidation supprime l'entrée du dict (pas juste refresh
    la valeur). On vérifie en inspectant _MEMBERSHIP_CACHE directement."""
    _seed_user_and_org(db_session, user_id=6, org_id=6)
    assign_role(db_session, user_id=6, org_id=6, role=UserRole.DG_OWNER)

    # Cache miss → fill
    assert _is_member_cached(db_session, 6, 6) is True
    assert (6, 6) in _MEMBERSHIP_CACHE

    # Invalidation explicite (simule ce que font assign_role/remove_role)
    invalidate_membership_cache(user_id=6, org_id=6)

    # L'entrée doit avoir disparu du dict (pas rester avec expires_at=now)
    assert (6, 6) not in _MEMBERSHIP_CACHE
