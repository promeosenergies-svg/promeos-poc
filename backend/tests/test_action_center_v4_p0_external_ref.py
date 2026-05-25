"""Tests Action Center V4 P0 fix (2026-05-25) — external_ref + ActionLink.

Couvre les 4 P0 audit deep (sprint claude/action-center-v4-p0-source-links-
resilience-idempotence) :

P0-1 testé dans test_cockpit_priorities_no_legacy_anomalies.py (séparé).
P0-2 testé côté FE (drawer not-found state, vitest).
P0-3 ici : index UNIQUE external_ref + idempotence sync billing.
P0-4 ici : ActionLink peuplée à la création + lookup par target_uuid.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (  # noqa: E402
    Base,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)
from models.v4.action_center_items import ActionCenterItem  # noqa: E402
from models.v4.action_links import ActionLink  # noqa: E402
from models.v4.enums import Domain, Kind, LifecycleState  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _seed_org(db):
    org = Organisation(nom="Org P0", siren="999999999", actif=True)
    db.add(org)
    db.flush()
    db.add(EntiteJuridique(organisation_id=org.id, nom="EJ", siren="999999999"))
    db.commit()
    return org


def _make_item(db, org_id, *, external_ref, lifecycle="new", title="Item"):
    item = ActionCenterItem(
        id=uuid.uuid4(),
        organisation_id=org_id,
        kind=Kind.ANOMALY.value,
        domain=Domain.FACTURATION.value,
        title=title,
        description="x",
        lifecycle_state=lifecycle,
        priority_bracket="P2",
        priority_score=50.0,
        external_ref=external_ref,
    )
    db.add(item)
    db.flush()
    return item


# ─── P0-3 : Index UNIQUE external_ref ──────────────────────────────────


class TestP03ExternalRefUnique:
    def test_index_unique_protege_doublons_meme_org(self, db):
        """2 items avec même (org_id, external_ref) → IntegrityError DB."""
        org = _seed_org(db)
        _make_item(db, org.id, external_ref="billing_anomaly:1")
        db.commit()
        with pytest.raises(IntegrityError):
            _make_item(db, org.id, external_ref="billing_anomaly:1")
            db.commit()
        db.rollback()

    def test_index_autorise_meme_ref_orgs_differentes(self, db):
        """external_ref est unique PAR org (deux orgs peuvent partager une ref)."""
        org1 = _seed_org(db)
        org1_id = org1.id
        db.add(Organisation(nom="Org2", siren="888888888", actif=True))
        db.commit()
        org2 = db.query(Organisation).filter_by(nom="Org2").one()
        _make_item(db, org1_id, external_ref="billing_anomaly:42")
        _make_item(db, org2.id, external_ref="billing_anomaly:42")
        db.commit()
        all_items = db.query(ActionCenterItem).filter_by(external_ref="billing_anomaly:42").all()
        assert len(all_items) == 2

    def test_index_autorise_null_external_ref(self, db):
        """L'index est partiel — plusieurs items sans external_ref OK."""
        org = _seed_org(db)
        for _ in range(3):
            _make_item(db, org.id, external_ref=None, title=f"item-{_}")
        db.commit()
        # Pas d'IntegrityError — N items avec external_ref=NULL coexistent.
        assert db.query(ActionCenterItem).filter_by(organisation_id=org.id, external_ref=None).count() == 3


# ─── P0-4 : ActionLink populated ────────────────────────────────────────


class TestP04ActionLink:
    def test_anomaly_target_uuid_deterministe(self):
        """Le UUID dérivé d'un anomaly_id integer est stable (idempotent)."""
        from routes.billing_sync import _anomaly_target_uuid

        u1 = _anomaly_target_uuid(42)
        u2 = _anomaly_target_uuid(42)
        u3 = _anomaly_target_uuid(43)
        assert u1 == u2, "même anomaly_id → même UUID (stable)"
        assert u1 != u3, "anomaly_id différent → UUID différent"

    def test_ensure_action_link_cree_si_absent(self, db):
        """_ensure_action_link insère un ActionLink si aucun n'existe."""
        org = _seed_org(db)
        item = _make_item(db, org.id, external_ref="billing_anomaly:7")
        db.commit()

        from routes.billing_sync import _ensure_action_link

        created = _ensure_action_link(db, org.id, item.id, anomaly_id=7)
        db.commit()
        assert created is True
        link = db.query(ActionLink).filter_by(organisation_id=org.id, item_id=item.id).one()
        assert link.target_module == "billing"
        assert link.relation == "caused_by"
        assert link.link_type == "source"

    def test_ensure_action_link_idempotent(self, db):
        """Appel répété ne crée pas de doublon ActionLink."""
        org = _seed_org(db)
        item = _make_item(db, org.id, external_ref="billing_anomaly:8")
        db.commit()

        from routes.billing_sync import _ensure_action_link

        assert _ensure_action_link(db, org.id, item.id, 8) is True
        db.commit()
        assert _ensure_action_link(db, org.id, item.id, 8) is False
        db.commit()
        assert db.query(ActionLink).filter_by(item_id=item.id).count() == 1, (
            "ActionLink ne doit jamais être dupliqué pour la même source"
        )


# ─── P0-3 + P0-4 : Helpers billing_sync ────────────────────────────────


class TestBillingSyncHelpers:
    def test_make_external_ref_pattern_stable(self):
        from routes.billing_sync import _make_external_ref

        class FakeAnomaly:
            id = 42

        assert _make_external_ref(FakeAnomaly()) == "billing_anomaly:42"

    def test_make_source_url_pointe_vers_bill_intel(self):
        from routes.billing_sync import _make_source_url

        class FakeAnomaly:
            id = 99

        url = _make_source_url(FakeAnomaly())
        assert url == "/bill-intel?anomaly=99"
        # Anti-régression : jamais /anomalies (page legacy gated OFF)
        assert "/anomalies" not in url
