"""
PROMEOS — Sprint C-2 Phase 2 : Tests site_portefeuille_service + endpoint.

Vérifie :
- transfer_site_to_portefeuille : création entry history + close previous + update FK
- Invariant cross-EJ : CrossEjTransferError levé
- get_site_history : ordre desc
- get_portefeuille_at_date : analyse rétrospective
- Audit log automatique via log_patrimoine_change (Phase 1.3)
- Résilience : échec audit log ne bloque pas la bascule
- Endpoint org-scopé (site source + portefeuille cible)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def db_session():
    """Session DB SQLAlchemy avec rollback en fin de test."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def two_portefeuilles_same_ej(db_session, request):
    """Crée 2 portefeuilles dans la MÊME EJ avec noms uniques par test.

    Noms uniques évitent UNIQUE constraint (entite_juridique_id, nom) quand un
    test précédent a commit() les fixtures.
    """
    import uuid

    from models import EntiteJuridique, Organisation, Portefeuille

    suffix = uuid.uuid4().hex[:8]

    # Trouver une EJ existante (HELIOS) ou en créer une de test
    ej = db_session.query(EntiteJuridique).first()
    if not ej:
        org = Organisation(nom=f"Test Org Phase2 {suffix}", siren=f"99900{suffix[:4]}")
        db_session.add(org)
        db_session.flush()
        ej = EntiteJuridique(
            nom=f"Test EJ Phase2 {suffix}",
            siren=f"99900{suffix[:4]}",
            organisation_id=org.id,
        )
        db_session.add(ej)
        db_session.flush()

    pf_source = Portefeuille(
        nom=f"PF_TEST_SOURCE_PHASE2_{suffix}",
        entite_juridique_id=ej.id,
    )
    pf_target = Portefeuille(
        nom=f"PF_TEST_TARGET_PHASE2_{suffix}",
        entite_juridique_id=ej.id,
    )
    db_session.add_all([pf_source, pf_target])
    db_session.flush()
    return pf_source, pf_target, ej


@pytest.fixture
def site_in_pf_source(db_session, two_portefeuilles_same_ej):
    """Crée un site test dans pf_source (pour bascule vers pf_target)."""
    from models import Site

    pf_source, _, _ = two_portefeuilles_same_ej
    site = Site(
        nom="Site Test Phase 2",
        type="bureau",
        portefeuille_id=pf_source.id,
        actif=True,
    )
    db_session.add(site)
    db_session.flush()
    return site


# ─── transfer_site_to_portefeuille ──────────────────────────────────────────


def test_transfer_creates_history_entry(db_session, site_in_pf_source, two_portefeuilles_same_ej):
    """Bascule réussie crée 1 entrée history avec valid_from=now et valid_to=None."""
    from services.site_portefeuille_service import transfer_site_to_portefeuille

    _, pf_target, _ = two_portefeuilles_same_ej

    entry = transfer_site_to_portefeuille(
        db_session,
        site_id=site_in_pf_source.id,
        new_portefeuille_id=pf_target.id,
        raison="Test transfer",
    )

    assert entry.id is not None
    assert entry.site_id == site_in_pf_source.id
    assert entry.portefeuille_id == pf_target.id
    assert entry.valid_to is None
    assert entry.raison == "Test transfer"


def test_transfer_updates_site_portefeuille_id(db_session, site_in_pf_source, two_portefeuilles_same_ej):
    """Site.portefeuille_id mis à jour après bascule."""
    from services.site_portefeuille_service import transfer_site_to_portefeuille

    _, pf_target, _ = two_portefeuilles_same_ej
    transfer_site_to_portefeuille(
        db_session,
        site_id=site_in_pf_source.id,
        new_portefeuille_id=pf_target.id,
    )
    db_session.flush()
    assert site_in_pf_source.portefeuille_id == pf_target.id


def test_transfer_closes_previous_entry(db_session, site_in_pf_source, two_portefeuilles_same_ej):
    """Si une entry history courante existe, valid_to est fermé à la date de bascule."""
    from datetime import datetime, timedelta

    from models.site_portefeuille_history import SitePortefeuilleHistory
    from services.site_portefeuille_service import transfer_site_to_portefeuille

    pf_source, pf_target, _ = two_portefeuilles_same_ej

    # Créer manuellement une entry précédente
    earlier_entry = SitePortefeuilleHistory(
        site_id=site_in_pf_source.id,
        portefeuille_id=pf_source.id,
        valid_from=datetime.utcnow() - timedelta(days=30),
        valid_to=None,
    )
    db_session.add(earlier_entry)
    db_session.flush()

    # Bascule → l'entry earlier doit être fermée
    transfer_site_to_portefeuille(
        db_session,
        site_id=site_in_pf_source.id,
        new_portefeuille_id=pf_target.id,
    )
    db_session.flush()

    db_session.refresh(earlier_entry)
    assert earlier_entry.valid_to is not None


def test_transfer_cross_ej_rejected(db_session):
    """Bascule vers un Portefeuille d'une autre EJ → CrossEjTransferError."""
    import uuid

    from models import EntiteJuridique, Organisation, Portefeuille, Site
    from services.site_portefeuille_service import (
        CrossEjTransferError,
        transfer_site_to_portefeuille,
    )

    suffix = uuid.uuid4().hex[:8]
    siren_a = f"88800{suffix[:4]}"
    siren_b = f"88800{suffix[4:8]}"

    org_a = Organisation(nom=f"Org A {suffix}", siren=siren_a)
    org_b = Organisation(nom=f"Org B {suffix}", siren=siren_b)
    db_session.add_all([org_a, org_b])
    db_session.flush()

    ej_a = EntiteJuridique(nom=f"EJ A {suffix}", siren=siren_a, organisation_id=org_a.id)
    ej_b = EntiteJuridique(nom=f"EJ B {suffix}", siren=siren_b, organisation_id=org_b.id)
    db_session.add_all([ej_a, ej_b])
    db_session.flush()

    pf_a = Portefeuille(nom=f"PF A {suffix}", entite_juridique_id=ej_a.id)
    pf_b = Portefeuille(nom=f"PF B {suffix}", entite_juridique_id=ej_b.id)
    db_session.add_all([pf_a, pf_b])
    db_session.flush()

    site = Site(nom=f"Site Cross-EJ Test {suffix}", type="bureau", portefeuille_id=pf_a.id, actif=True)
    db_session.add(site)
    db_session.flush()

    with pytest.raises(CrossEjTransferError):
        transfer_site_to_portefeuille(db_session, site_id=site.id, new_portefeuille_id=pf_b.id)


def test_transfer_portefeuille_not_found(db_session, site_in_pf_source):
    """Portefeuille cible inexistant → PortefeuilleNotFoundError."""
    from services.site_portefeuille_service import (
        PortefeuilleNotFoundError,
        transfer_site_to_portefeuille,
    )

    with pytest.raises(PortefeuilleNotFoundError):
        transfer_site_to_portefeuille(db_session, site_id=site_in_pf_source.id, new_portefeuille_id=9_999_999)


def test_transfer_site_not_found(db_session):
    """Site inexistant → SiteNotFoundError."""
    from services.site_portefeuille_service import (
        SiteNotFoundError,
        transfer_site_to_portefeuille,
    )

    with pytest.raises(SiteNotFoundError):
        transfer_site_to_portefeuille(db_session, site_id=9_999_999, new_portefeuille_id=1)


def test_transfer_creates_audit_log(db_session, site_in_pf_source, two_portefeuilles_same_ej):
    """Bascule déclenche log_patrimoine_change avec action='site.transfer_portefeuille'."""
    from services.audit_log_service import query_audit_trail
    from services.site_portefeuille_service import transfer_site_to_portefeuille

    _, pf_target, _ = two_portefeuilles_same_ej
    org_id = 999_100  # org isolée test

    transfer_site_to_portefeuille(
        db_session,
        site_id=site_in_pf_source.id,
        new_portefeuille_id=pf_target.id,
        org_id=org_id,
        raison="Test audit",
    )
    db_session.commit()

    logs = query_audit_trail(db_session, org_id=org_id, action="site.transfer_portefeuille")
    assert len(logs) >= 1
    log = logs[0]
    assert log.field_modified == "portefeuille_id"


def test_transfer_audit_log_failure_does_not_break_transfer(db_session, site_in_pf_source, two_portefeuilles_same_ej):
    """Si log_patrimoine_change raise, la bascule réussit quand même (résilience)."""
    from services.site_portefeuille_service import transfer_site_to_portefeuille

    _, pf_target, _ = two_portefeuilles_same_ej

    with patch(
        "services.audit_log_service.log_patrimoine_change",
        side_effect=RuntimeError("simulated audit failure"),
    ):
        # Ne doit PAS lever l'exception — bascule doit aboutir
        entry = transfer_site_to_portefeuille(
            db_session,
            site_id=site_in_pf_source.id,
            new_portefeuille_id=pf_target.id,
        )

    assert entry.id is not None
    assert entry.portefeuille_id == pf_target.id


# ─── get_site_history ───────────────────────────────────────────────────────


def test_get_site_history_orders_desc(db_session, site_in_pf_source, two_portefeuilles_same_ej):
    """get_site_history retourne l'historique trié par valid_from desc."""
    from services.site_portefeuille_service import (
        get_site_history,
        transfer_site_to_portefeuille,
    )

    pf_source, pf_target, _ = two_portefeuilles_same_ej

    # Bascule 1 : pf_source → pf_target
    transfer_site_to_portefeuille(db_session, site_id=site_in_pf_source.id, new_portefeuille_id=pf_target.id)
    db_session.flush()

    # Bascule 2 : pf_target → pf_source (retour)
    transfer_site_to_portefeuille(db_session, site_id=site_in_pf_source.id, new_portefeuille_id=pf_source.id)
    db_session.flush()

    history = get_site_history(db_session, site_in_pf_source.id)
    assert len(history) >= 2
    # Le plus récent (pf_source) en premier
    assert history[0].portefeuille_id == pf_source.id
    assert history[1].portefeuille_id == pf_target.id


# ─── get_portefeuille_at_date ───────────────────────────────────────────────


def test_get_portefeuille_at_date_returns_correct(db_session, site_in_pf_source, two_portefeuilles_same_ej):
    """Retourne le portefeuille auquel le site appartenait à une date donnée."""
    from services.site_portefeuille_service import (
        get_portefeuille_at_date,
        transfer_site_to_portefeuille,
    )

    pf_source, pf_target, _ = two_portefeuilles_same_ej

    # Bascule maintenant
    transfer_site_to_portefeuille(db_session, site_id=site_in_pf_source.id, new_portefeuille_id=pf_target.id)
    db_session.flush()

    # Maintenant : pf_target
    now = datetime.utcnow()
    pf_now = get_portefeuille_at_date(db_session, site_in_pf_source.id, now + timedelta(seconds=1))
    assert pf_now is not None
    assert pf_now.id == pf_target.id


# ─── Endpoint /api/v1/sites/{id}/portefeuille ───────────────────────────────


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


def test_endpoint_404_for_unknown_site(client):
    """PATCH endpoint pour site inexistant → 404."""
    r = client.patch("/api/v1/sites/9999999/portefeuille", json={"new_portefeuille_id": 1})
    assert r.status_code == 404


def test_endpoint_history_404_for_unknown_site(client):
    """GET history pour site inexistant → 404."""
    r = client.get("/api/v1/sites/9999999/portefeuille-history")
    assert r.status_code == 404


def test_history_table_indexes_present():
    """Vérifie présence des 2 index attendus sur site_portefeuille_history."""
    from sqlalchemy import text

    from database import SessionLocal

    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='site_portefeuille_history'")
        )
        idx_names = {row[0] for row in result}
        assert "ix_sph_site_id_valid_from" in idx_names
        assert "ix_sph_portefeuille_id_valid_from" in idx_names
    finally:
        db.close()
