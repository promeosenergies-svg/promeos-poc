"""
PROMEOS — Tests audit-trail + qualification source conformite.
Covers: ComplianceEventLog, source reliability, fallback warnings.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Organisation, TertiaireEfa, TertiaireEfaConsumption
from models.compliance_event_log import ComplianceEventLog
from services.operat_trajectory import (
    declare_consumption,
    validate_trajectory,
    get_proof_events,
    _reliability_for_source,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def efa(db):
    org = Organisation(nom="TestOrg", type_client="tertiaire", actif=True, siren="123456789")
    db.add(org)
    db.flush()
    e = TertiaireEfa(org_id=org.id, nom="EFA Audit Test")
    db.add(e)
    db.flush()
    return e


# ── Audit trail ──────────────────────────────────────────────────────


class TestEventLog:
    def test_create_generates_event(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True, source="factures")
        events = db.query(ComplianceEventLog).filter(ComplianceEventLog.entity_type == "TertiaireEfaConsumption").all()
        assert len(events) >= 1
        assert events[0].action == "create"
        assert events[0].actor == "system"

    def test_update_generates_event(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, source="factures")
        declare_consumption(db, efa.id, year=2019, kwh_total=510000, source="factures")
        events = db.query(ComplianceEventLog).filter(ComplianceEventLog.entity_type == "TertiaireEfaConsumption").all()
        actions = [e.action for e in events]
        assert "create" in actions
        assert "update" in actions

    def test_trajectory_compute_generates_event(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=300000)
        validate_trajectory(db, efa.id, 2025)
        events = (
            db.query(ComplianceEventLog)
            .filter(
                ComplianceEventLog.entity_type == "TertiaireEfa",
                ComplianceEventLog.action == "trajectory_compute",
            )
            .all()
        )
        assert len(events) >= 1

    def test_proof_events_returns_events(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        events = get_proof_events(db, efa.id)
        assert len(events) >= 1
        assert events[0]["entity_type"] == "TertiaireEfaConsumption"


# ── Qualification source ─────────────────────────────────────────────


class TestSourceReliability:
    def test_import_invoice_is_high(self):
        assert _reliability_for_source("import_invoice") == "high"

    def test_factures_is_high(self):
        assert _reliability_for_source("factures") == "high"

    def test_declared_manual_is_medium(self):
        assert _reliability_for_source("declared_manual") == "medium"

    def test_site_fallback_is_low(self):
        assert _reliability_for_source("site_fallback") == "low"

    def test_none_is_unverified(self):
        assert _reliability_for_source(None) == "unverified"

    def test_unknown_string_is_unverified(self):
        assert _reliability_for_source("random_garbage") == "unverified"

    def test_fallback_never_high(self):
        """Fallback sources must NEVER be classified as high reliability."""
        for src in ["site_fallback", "inferred", "estimation", "seed"]:
            rel = _reliability_for_source(src)
            assert rel != "high", f"Source '{src}' should not be 'high' but got '{rel}'"


# ── Warnings fallback ────────────────────────────────────────────────


class TestFallbackWarnings:
    def test_low_reliability_baseline_generates_warning(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True, source="site_fallback")
        declare_consumption(db, efa.id, year=2025, kwh_total=300000, source="factures")
        result = validate_trajectory(db, efa.id, 2025)
        assert any("fiabilite" in w.lower() or "low" in w.lower() for w in result.get("evidence_warnings", []))

    def test_high_reliability_no_evidence_warning(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True, source="factures")
        declare_consumption(db, efa.id, year=2025, kwh_total=300000, source="import_invoice")
        result = validate_trajectory(db, efa.id, 2025)
        assert result["evidence_warnings"] == []

    def test_validate_returns_reliability(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True, source="factures")
        declare_consumption(db, efa.id, year=2025, kwh_total=300000, source="declared_manual")
        result = validate_trajectory(db, efa.id, 2025)
        assert result["baseline"]["reliability"] == "high"
        assert result["current"]["reliability"] == "medium"
