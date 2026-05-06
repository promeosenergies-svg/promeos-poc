"""
PROMEOS — Tests Org/DP consentement_by + cgu_version (Sprint C-5 Phase 5.3, ADR-007 ext).

Couverture cardinal :
- CRUD Org : 4 cols audit RGPD (consentement_{dataconnect|grdf}_{by|cgu_version})
- CRUD DP : 4 cols local audit RGPD (consentement_{dataconnect|grdf}_local_{by|cgu_version})
- ondelete=SET NULL : suppression user (RGPD droit oubli) préserve l'historique
- Helper get_effective_consent_with_audit : 3 scopes (local / global / none)
- Sérialisation dict complet (active + by_user_id + cgu_version + at + scope)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def db_session():
    """In-memory SQLite avec schema déployé pour tests audit RGPD."""
    from models import Base

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Activer ondelete=SET NULL côté SQLite (foreign_keys=ON requis)
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.execute(text("PRAGMA foreign_keys=ON"))
    yield session
    session.close()


def _seed_user(db, email="alice@test.io"):
    from models import User

    user = User(
        email=email,
        hashed_password="hashed",
        nom="Test",
        prenom="Alice",
        actif=True,
    )
    db.add(user)
    db.commit()
    return user


def _seed_full_hierarchy(db):
    """Crée Org → EJ → Pf → Site → DP."""
    from models import (
        DeliveryPoint,
        DeliveryPointEnergyType,
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )

    org = Organisation(nom="O", siren="500000001")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom="EJ", siren="500000001", organisation_id=org.id)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom="PF", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    site = Site(nom="S", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
    db.add(site)
    db.flush()
    dp = DeliveryPoint(
        code="12345678901234",
        site_id=site.id,
        energy_type=DeliveryPointEnergyType.ELEC,
        grd_code="ENEDIS",
    )
    db.add(dp)
    db.commit()
    return org, ej, pf, site, dp


# ─── CRUD Org : 4 cols audit RGPD ───────────────────────────────────────────


def test_org_consentement_by_default_null(db_session):
    """Defaults : 4 cols audit RGPD = NULL si pas explicitement set."""
    from models import Organisation

    org = Organisation(nom="OrgDefaults", siren="500000002")
    db_session.add(org)
    db_session.commit()

    assert org.consentement_dataconnect_by is None
    assert org.consentement_dataconnect_cgu_version is None
    assert org.consentement_grdf_by is None
    assert org.consentement_grdf_cgu_version is None


def test_org_consentement_dataconnect_by_set_user_id(db_session):
    """Set consentement_dataconnect_by + cgu_version : valeurs persistées."""
    from models import Organisation

    user = _seed_user(db_session, email="bob@test.io")
    org = Organisation(
        nom="OrgConsented",
        siren="500000003",
        consentement_dataconnect_global=True,
        consentement_dataconnect_at=datetime.now(timezone.utc),
        consentement_dataconnect_by=user.id,
        consentement_dataconnect_cgu_version="1.0",
    )
    db_session.add(org)
    db_session.commit()

    db_session.refresh(org)
    assert org.consentement_dataconnect_global is True
    assert org.consentement_dataconnect_by == user.id
    assert org.consentement_dataconnect_cgu_version == "1.0"


def test_org_consentement_grdf_independent_from_dataconnect(db_session):
    """Indépendance des 2 types (dataconnect / grdf) : chaque col distincte."""
    from models import Organisation

    alice = _seed_user(db_session, email="alice@test.io")
    bob = _seed_user(db_session, email="bob@test.io")
    org = Organisation(
        nom="OrgMixed",
        siren="500000004",
        consentement_dataconnect_by=alice.id,
        consentement_dataconnect_cgu_version="1.0",
        consentement_grdf_by=bob.id,
        consentement_grdf_cgu_version="2.1.0",
    )
    db_session.add(org)
    db_session.commit()

    db_session.refresh(org)
    assert org.consentement_dataconnect_by == alice.id
    assert org.consentement_grdf_by == bob.id
    assert org.consentement_dataconnect_cgu_version != org.consentement_grdf_cgu_version


# ─── CRUD DP : 4 cols local audit RGPD ──────────────────────────────────────


def test_dp_consentement_local_by_default_null(db_session):
    """DP defaults : 4 cols local audit RGPD = NULL."""
    _, _, _, _, dp = _seed_full_hierarchy(db_session)

    assert dp.consentement_dataconnect_local_by is None
    assert dp.consentement_dataconnect_local_cgu_version is None
    assert dp.consentement_grdf_local_by is None
    assert dp.consentement_grdf_local_cgu_version is None


def test_dp_consentement_local_overrides_org(db_session):
    """DP override local audit RGPD persisté indépendamment de l'Org."""
    org, _, _, _, dp = _seed_full_hierarchy(db_session)
    user = _seed_user(db_session, email="carol@test.io")

    # Org a son propre consentement (cgu 1.0, byUser X)
    org.consentement_dataconnect_global = True
    org.consentement_dataconnect_cgu_version = "1.0"

    # DP override : cgu 2.0 distinct, byUser Y
    dp.consentement_dataconnect_local = False
    dp.consentement_dataconnect_local_at = datetime.now(timezone.utc)
    dp.consentement_dataconnect_local_by = user.id
    dp.consentement_dataconnect_local_cgu_version = "2.0"

    db_session.commit()
    db_session.refresh(dp)

    assert dp.consentement_dataconnect_local is False
    assert dp.consentement_dataconnect_local_by == user.id
    assert dp.consentement_dataconnect_local_cgu_version == "2.0"


# ─── ondelete=SET NULL : RGPD droit oubli ──────────────────────────────────


def test_user_delete_sets_org_consentement_by_to_null(db_session):
    """Suppression user (RGPD droit oubli) : consentement_*_by → NULL, historique préservé."""
    from models import Organisation

    user = _seed_user(db_session, email="todelete@test.io")
    org = Organisation(
        nom="OrgUserDeleted",
        siren="500000005",
        consentement_dataconnect_by=user.id,
        consentement_dataconnect_cgu_version="1.0",
    )
    db_session.add(org)
    db_session.commit()

    user_id = user.id
    db_session.delete(user)
    db_session.commit()
    db_session.refresh(org)

    # by → NULL (FK SET NULL), mais cgu_version préservé (historique)
    assert org.consentement_dataconnect_by is None
    assert org.consentement_dataconnect_cgu_version == "1.0"
    # Vérifier user effectivement supprimé
    from models import User

    assert db_session.query(User).filter(User.id == user_id).first() is None


def test_user_delete_sets_dp_local_consentement_by_to_null(db_session):
    """Suppression user : DP consentement_local_by → NULL, override préservé."""
    _, _, _, _, dp = _seed_full_hierarchy(db_session)
    user = _seed_user(db_session, email="grdfto@test.io")

    dp.consentement_grdf_local = True
    dp.consentement_grdf_local_by = user.id
    dp.consentement_grdf_local_cgu_version = "3.0"
    db_session.commit()

    db_session.delete(user)
    db_session.commit()
    db_session.refresh(dp)

    assert dp.consentement_grdf_local_by is None
    assert dp.consentement_grdf_local is True  # valeur préservée
    assert dp.consentement_grdf_local_cgu_version == "3.0"  # cgu préservée


# ─── Helper get_effective_consent_with_audit ────────────────────────────────


def test_get_effective_consent_with_audit_local_scope_returns_all_fields(db_session):
    """Scope local : helper retourne dict complet avec by + cgu_version + at."""
    from services.consent_service import get_effective_consent_with_audit

    org, _, _, _, dp = _seed_full_hierarchy(db_session)
    user = _seed_user(db_session, email="dave@test.io")
    dp.consentement_dataconnect_local = True
    dp.consentement_dataconnect_local_at = datetime(2026, 5, 6, 10, 0, tzinfo=timezone.utc)
    dp.consentement_dataconnect_local_by = user.id
    dp.consentement_dataconnect_local_cgu_version = "2.0"
    db_session.commit()

    result = get_effective_consent_with_audit(dp, "dataconnect")

    assert result["active"] is True
    assert result["scope"] == "local"
    assert result["by_user_id"] == user.id
    assert result["cgu_version"] == "2.0"
    assert result["at"] is not None


def test_get_effective_consent_with_audit_global_scope_fallback(db_session):
    """Scope global : DP._local NULL → fallback Org._global avec audit complet."""
    from services.consent_service import get_effective_consent_with_audit

    org, _, _, _, dp = _seed_full_hierarchy(db_session)
    user = _seed_user(db_session, email="erin@test.io")
    org.consentement_grdf_global = True
    org.consentement_grdf_at = datetime(2026, 5, 1, 9, 0, tzinfo=timezone.utc)
    org.consentement_grdf_by = user.id
    org.consentement_grdf_cgu_version = "1.5"
    db_session.commit()

    result = get_effective_consent_with_audit(dp, "grdf")

    assert result["active"] is True
    assert result["scope"] == "global"
    assert result["by_user_id"] == user.id
    assert result["cgu_version"] == "1.5"


def test_get_effective_consent_with_audit_none_scope_when_both_null(db_session):
    """Scope none : ni DP._local ni Org._global → tous champs null."""
    from services.consent_service import get_effective_consent_with_audit

    _, _, _, _, dp = _seed_full_hierarchy(db_session)

    result = get_effective_consent_with_audit(dp, "dataconnect")

    assert result["active"] is None
    assert result["scope"] == "none"
    assert result["by_user_id"] is None
    assert result["cgu_version"] is None
    assert result["at"] is None


def test_get_effective_consent_with_audit_invalid_type_raises(db_session):
    """type_ invalide → ValueError."""
    from services.consent_service import get_effective_consent_with_audit

    _, _, _, _, dp = _seed_full_hierarchy(db_session)

    with pytest.raises(ValueError, match="type_ inconnu"):
        get_effective_consent_with_audit(dp, "invalid_type")


def test_get_effective_consent_with_audit_local_priority_over_global(db_session):
    """DP._local prime sur Org._global même si valeurs distinctes (ADR-007 override)."""
    from services.consent_service import get_effective_consent_with_audit

    org, _, _, _, dp = _seed_full_hierarchy(db_session)
    alice = _seed_user(db_session, email="alice2@test.io")
    bob = _seed_user(db_session, email="bob2@test.io")

    # Org dit YES, DP override NO
    org.consentement_dataconnect_global = True
    org.consentement_dataconnect_by = alice.id
    org.consentement_dataconnect_cgu_version = "org-cgu"

    dp.consentement_dataconnect_local = False
    dp.consentement_dataconnect_local_by = bob.id
    dp.consentement_dataconnect_local_cgu_version = "dp-cgu"
    db_session.commit()

    result = get_effective_consent_with_audit(dp, "dataconnect")

    # Local prime
    assert result["active"] is False
    assert result["scope"] == "local"
    assert result["by_user_id"] == bob.id
    assert result["cgu_version"] == "dp-cgu"


# ─── Sérialisation dict complet ─────────────────────────────────────────────


def test_audit_dict_keys_stable_for_serialization(db_session):
    """Helper retourne TOUJOURS les 5 mêmes clés (contrat sérialisation API)."""
    from services.consent_service import get_effective_consent_with_audit

    _, _, _, _, dp = _seed_full_hierarchy(db_session)

    result = get_effective_consent_with_audit(dp, "dataconnect")
    expected_keys = {"active", "by_user_id", "cgu_version", "at", "scope"}
    assert set(result.keys()) == expected_keys, f"Keys instables : {set(result.keys()) ^ expected_keys}"
