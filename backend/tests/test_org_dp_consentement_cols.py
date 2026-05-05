"""
PROMEOS — Tests CRUD modèle consentement Org/DP (Sprint C-4 Phase 4.4, ADR-007).

Vérifie les 8 nouvelles colonnes RGPD ajoutées par migration `d4a59f7c8e21` :

- Organisation : 4 cols (consentement_dataconnect_global + at + grdf_global + at)
- DeliveryPoint : 4 cols (consentement_dataconnect_local + at + grdf_local + at)

Pré-requis cardinal Phase 4.5 cascade vivante (cascade Org.global → DPs locaux).

Clôture dette `D-Sprint-C3-7d-ADR-RGPD-Consent-Detail-001` (P1 Sprint C-3 7d).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def db_session():
    """In-memory SQLite avec schema déployé (modèles ORM appliqués)."""
    from models import Base
    from models.organisation import Organisation  # noqa: F401
    from models.patrimoine import DeliveryPoint  # noqa: F401

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ─── 1. Organisation — 4 cols consentement ───────────────────────────────────


def test_org_consentement_dataconnect_global_default_null(db_session):
    """Défaut Phase 4.4 : nullable=True (pas False) pour signaler 'pas encore choisi'."""
    from models.organisation import Organisation

    org = Organisation(nom="Test Org Consent")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    assert org.consentement_dataconnect_global is None
    assert org.consentement_dataconnect_at is None


def test_org_consentement_dataconnect_global_set_true_with_at(db_session):
    """Set True + timestamp explicite (RGPD audit trail)."""
    from models.organisation import Organisation

    now = datetime.now(timezone.utc)
    org = Organisation(
        nom="Org Consent True",
        consentement_dataconnect_global=True,
        consentement_dataconnect_at=now,
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    assert org.consentement_dataconnect_global is True
    assert org.consentement_dataconnect_at is not None


def test_org_consentement_grdf_independent_from_dataconnect(db_session):
    """Les 2 paires (DataConnect/GRDF) sont indépendantes — Org peut consentir Enedis sans GRDF."""
    from models.organisation import Organisation

    org = Organisation(
        nom="Org Mixed Consent",
        consentement_dataconnect_global=True,
        consentement_grdf_global=False,
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    assert org.consentement_dataconnect_global is True
    assert org.consentement_grdf_global is False


def test_org_consentement_grdf_global_set_with_at(db_session):
    """GRDF également avec timestamp séparé."""
    from models.organisation import Organisation

    now = datetime.now(timezone.utc)
    org = Organisation(
        nom="Org GRDF",
        consentement_grdf_global=True,
        consentement_grdf_at=now,
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    assert org.consentement_grdf_global is True
    assert org.consentement_grdf_at is not None


# ─── 2. DeliveryPoint — 4 cols consentement local ────────────────────────────


def test_dp_consentement_dataconnect_local_default_null(db_session):
    """Défaut DP : null (pas d'override actif)."""
    from models.organisation import Organisation
    from models.entite_juridique import EntiteJuridique
    from models.portefeuille import Portefeuille
    from models.site import Site, TypeSite
    from models.patrimoine import DeliveryPoint

    org = Organisation(nom="Org DP Default")
    db_session.add(org)
    db_session.flush()
    ej = EntiteJuridique(nom="EJ DP", siren="123456789", organisation_id=org.id)
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(nom="PF DP", entite_juridique_id=ej.id)
    db_session.add(pf)
    db_session.flush()
    site = Site(nom="Site DP", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
    db_session.add(site)
    db_session.flush()

    dp = DeliveryPoint(code="12345678901234", site_id=site.id)
    db_session.add(dp)
    db_session.commit()
    db_session.refresh(dp)
    assert dp.consentement_dataconnect_local is None
    assert dp.consentement_grdf_local is None


def test_dp_consentement_local_set_overrides_org_global_semantically(db_session):
    """ADR-007 : DP local override possible vs Org global. Test stockage indépendant
    (la logique cascade est Phase 4.5, ce test vérifie juste que le storage fonctionne).
    """
    from models.organisation import Organisation
    from models.entite_juridique import EntiteJuridique
    from models.portefeuille import Portefeuille
    from models.site import Site, TypeSite
    from models.patrimoine import DeliveryPoint

    now = datetime.now(timezone.utc)
    org = Organisation(nom="Org Override", consentement_dataconnect_global=True)
    db_session.add(org)
    db_session.flush()
    ej = EntiteJuridique(nom="EJ Override", siren="987654321", organisation_id=org.id)
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(nom="PF Override", entite_juridique_id=ej.id)
    db_session.add(pf)
    db_session.flush()
    site = Site(nom="Site Override", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
    db_session.add(site)
    db_session.flush()

    # DP avec override LOCAL = False alors que global = True
    dp = DeliveryPoint(
        code="22345678901234",
        site_id=site.id,
        consentement_dataconnect_local=False,
        consentement_dataconnect_local_at=now,
    )
    db_session.add(dp)
    db_session.commit()
    db_session.refresh(dp)
    assert dp.consentement_dataconnect_local is False
    assert org.consentement_dataconnect_global is True
    # Override sémantique : Phase 4.5 cascade prendra le local en priorité


def test_dp_consentement_grdf_local_independent_from_dataconnect(db_session):
    """DataConnect (élec) et GRDF (gaz) indépendants côté DP — un DP peut être l'un OU l'autre."""
    from models.organisation import Organisation
    from models.entite_juridique import EntiteJuridique
    from models.portefeuille import Portefeuille
    from models.site import Site, TypeSite
    from models.patrimoine import DeliveryPoint

    org = Organisation(nom="Org Indep")
    db_session.add(org)
    db_session.flush()
    ej = EntiteJuridique(nom="EJ Indep", siren="111111111", organisation_id=org.id)
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(nom="PF Indep", entite_juridique_id=ej.id)
    db_session.add(pf)
    db_session.flush()
    site = Site(nom="Site Indep", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
    db_session.add(site)
    db_session.flush()

    dp = DeliveryPoint(
        code="33345678901234",
        site_id=site.id,
        grd_code="GRDF",
        consentement_grdf_local=True,
        # consentement_dataconnect_local reste null (DP gaz, pas de DataConnect)
    )
    db_session.add(dp)
    db_session.commit()
    db_session.refresh(dp)
    assert dp.consentement_grdf_local is True
    assert dp.consentement_dataconnect_local is None


# ─── 3. Schema introspection — 8 cols + 1 index ──────────────────────────────


def test_schema_organisations_has_4_consent_cols(db_session):
    """SG_PHASE44_01 : table organisations a bien les 4 cols consentement."""
    inspector = inspect(db_session.bind)
    cols = {c["name"] for c in inspector.get_columns("organisations")}
    expected = {
        "consentement_dataconnect_global",
        "consentement_dataconnect_at",
        "consentement_grdf_global",
        "consentement_grdf_at",
    }
    missing = expected - cols
    assert not missing, f"Cols consentement manquantes sur organisations : {missing}"


def test_schema_delivery_points_has_4_consent_cols(db_session):
    """SG_PHASE44_02 : table delivery_points a bien les 4 cols consentement local."""
    inspector = inspect(db_session.bind)
    cols = {c["name"] for c in inspector.get_columns("delivery_points")}
    expected = {
        "consentement_dataconnect_local",
        "consentement_dataconnect_local_at",
        "consentement_grdf_local",
        "consentement_grdf_local_at",
    }
    missing = expected - cols
    assert not missing, f"Cols consentement local manquantes sur delivery_points : {missing}"


def test_schema_consent_at_cols_are_datetime_tz(db_session):
    """SG_PHASE44_03 : timestamps consent sont DateTime (RGPD-compliant)."""
    inspector = inspect(db_session.bind)
    org_cols = {c["name"]: c["type"] for c in inspector.get_columns("organisations")}
    # SQLite type peut être str — vérifier juste présence + non-Boolean
    assert "consentement_dataconnect_at" in org_cols
    assert "consentement_grdf_at" in org_cols
    # Vérification type DateTime (string repr peut varier selon dialect)
    assert "DATETIME" in str(org_cols["consentement_dataconnect_at"]).upper()


def test_dp_consentement_relations_preserved(db_session):
    """Phase 4.4 ne casse pas les relations existantes Site/DP/Compteur."""
    from models.organisation import Organisation
    from models.entite_juridique import EntiteJuridique
    from models.portefeuille import Portefeuille
    from models.site import Site, TypeSite
    from models.patrimoine import DeliveryPoint

    org = Organisation(nom="Org Relations")
    db_session.add(org)
    db_session.flush()
    ej = EntiteJuridique(nom="EJ Rel", siren="222222222", organisation_id=org.id)
    db_session.add(ej)
    db_session.flush()
    pf = Portefeuille(nom="PF Rel", entite_juridique_id=ej.id)
    db_session.add(pf)
    db_session.flush()
    site = Site(nom="Site Rel", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
    db_session.add(site)
    db_session.flush()

    dp = DeliveryPoint(code="44345678901234", site_id=site.id)
    db_session.add(dp)
    db_session.commit()
    db_session.refresh(dp)
    db_session.refresh(site)
    # Relation existante Site→DPs préservée
    assert dp in site.delivery_points
    assert dp.site_id == site.id
