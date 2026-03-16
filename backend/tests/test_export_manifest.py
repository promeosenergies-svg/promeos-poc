"""
PROMEOS — Tests chaine de preuve export OPERAT.
Covers: manifest, checksum, event log, actor, warnings.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Organisation, TertiaireEfa, TertiaireEfaConsumption
from models.operat_export_manifest import OperatExportManifest
from models.compliance_event_log import ComplianceEventLog


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
def org(db):
    o = Organisation(nom="TestOrg", type_client="tertiaire", actif=True, siren="123456789")
    db.add(o)
    db.flush()
    return o


@pytest.fixture
def efa(db, org):
    e = TertiaireEfa(org_id=org.id, nom="EFA Export Test")
    db.add(e)
    db.flush()
    return e


def _add_conso(db, efa_id, year, kwh, is_ref=False, source="factures"):
    c = TertiaireEfaConsumption(
        efa_id=efa_id,
        year=year,
        kwh_total=kwh,
        is_reference=is_ref,
        source=source,
        reliability="high" if source in ("factures", "import_invoice") else "low",
    )
    db.add(c)
    db.flush()
    return c


class TestBuildManifest:
    def test_manifest_created_with_checksum(self, db, org, efa):
        from routes.operat import _build_manifest

        csv = "col1;col2\nval1;val2\n"
        m = _build_manifest(db, org.id, 2025, csv, "test.csv", actor="test_user")
        assert m.id is not None
        assert m.checksum_sha256 is not None
        assert len(m.checksum_sha256) == 64

    def test_manifest_actor_never_empty(self, db, org, efa):
        from routes.operat import _build_manifest

        csv = "col1\nval1\n"
        m = _build_manifest(db, org.id, 2025, csv, "test.csv", actor=None)
        assert m.actor == "system"
        assert m.actor != ""

    def test_manifest_captures_baseline(self, db, org, efa):
        from routes.operat import _build_manifest

        _add_conso(db, efa.id, 2019, 500000, is_ref=True, source="factures")
        _add_conso(db, efa.id, 2025, 300000, source="declared_manual")

        csv = "col1\nval1\n"
        m = _build_manifest(db, org.id, 2025, csv, "test.csv")
        assert m.baseline_year == 2019
        assert m.baseline_kwh == 500000
        assert m.baseline_source == "factures"
        assert m.baseline_reliability == "high"
        assert m.current_kwh == 300000

    def test_manifest_warnings_if_no_baseline(self, db, org, efa):
        from routes.operat import _build_manifest

        csv = "col1\nval1\n"
        m = _build_manifest(db, org.id, 2025, csv, "test.csv")
        import json

        warnings = json.loads(m.evidence_warnings_json) if m.evidence_warnings_json else []
        assert any("reference absente" in w.lower() for w in warnings)

    def test_manifest_warnings_if_low_reliability(self, db, org, efa):
        from routes.operat import _build_manifest

        _add_conso(db, efa.id, 2019, 500000, is_ref=True, source="site_fallback")
        csv = "col1\nval1\n"
        m = _build_manifest(db, org.id, 2025, csv, "test.csv")
        import json

        warnings = json.loads(m.evidence_warnings_json) if m.evidence_warnings_json else []
        assert any("low" in w.lower() or "fiabilite" in w.lower() for w in warnings)


class TestEventLogExport:
    def test_export_generates_event_log(self, db, org, efa):
        from routes.operat import _build_manifest

        csv = "col1\nval1\n"
        _build_manifest(db, org.id, 2025, csv, "test.csv", actor="test_user")
        events = (
            db.query(ComplianceEventLog)
            .filter(
                ComplianceEventLog.entity_type == "OperatExportManifest",
                ComplianceEventLog.action == "export_generate",
            )
            .all()
        )
        assert len(events) >= 1
        assert events[0].actor == "test_user"

    def test_different_content_different_checksum(self, db, org, efa):
        from routes.operat import _build_manifest

        m1 = _build_manifest(db, org.id, 2025, "content_A\n", "a.csv")
        m2 = _build_manifest(db, org.id, 2025, "content_B\n", "b.csv")
        assert m1.checksum_sha256 != m2.checksum_sha256


class TestManifestList:
    def test_list_returns_manifests(self, db, org, efa):
        from routes.operat import _build_manifest

        _build_manifest(db, org.id, 2025, "c1\n", "f1.csv")
        _build_manifest(db, org.id, 2024, "c2\n", "f2.csv")
        db.flush()

        rows = (
            db.query(OperatExportManifest)
            .filter(OperatExportManifest.org_id == org.id)
            .order_by(OperatExportManifest.generated_at.desc())
            .all()
        )
        assert len(rows) == 2
        assert rows[0].observation_year in (2024, 2025)
