"""
PROMEOS — Tests hardening OPERAT : archivage, certification, actor, meteo.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Organisation, TertiaireEfa, TertiaireEfaConsumption
from models.operat_export_manifest import OperatExportManifest
from services.weather_provider import get_dju_for_year
from services.actor_resolver import resolve_actor


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool
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
    e = TertiaireEfa(org_id=org.id, nom="EFA Hardening")
    db.add(e)
    db.flush()
    return e


class TestManifestRetention:
    def test_manifest_has_retention_date(self, db, org, efa):
        from routes.operat import _build_manifest

        m = _build_manifest(db, org.id, 2025, "csv\n", "test.csv")
        assert m.retention_until is not None
        assert m.retention_until > datetime.now(timezone.utc)

    def test_retention_is_5_years(self, db, org, efa):
        from routes.operat import _build_manifest

        m = _build_manifest(db, org.id, 2025, "csv\n", "test.csv")
        delta = m.retention_until - m.generated_at
        assert delta.days >= 1825 - 2  # ~5 years with tolerance

    def test_archive_status_active_by_default(self, db, org, efa):
        from routes.operat import _build_manifest

        m = _build_manifest(db, org.id, 2025, "csv\n", "test.csv")
        assert m.archive_status == "active"


class TestManifestCertification:
    def test_promeos_version_present(self, db, org, efa):
        from routes.operat import _build_manifest

        m = _build_manifest(db, org.id, 2025, "csv\n", "test.csv")
        assert m.promeos_version == "2.0"

    def test_manifest_dict_includes_hardening_fields(self, db, org, efa):
        from routes.operat import _build_manifest, _manifest_to_dict

        m = _build_manifest(db, org.id, 2025, "csv\n", "test.csv")
        d = _manifest_to_dict(m)
        assert "retention_until" in d
        assert "archive_status" in d
        assert "promeos_version" in d
        assert d["archive_status"] == "active"


class TestActorPropagation:
    def test_actor_propagated_to_manifest(self, db, org, efa):
        from routes.operat import _build_manifest

        m = _build_manifest(db, org.id, 2025, "csv\n", "test.csv", actor="user@test.com")
        assert m.actor == "user@test.com"

    def test_actor_fallback_not_empty(self, db, org, efa):
        from routes.operat import _build_manifest

        m = _build_manifest(db, org.id, 2025, "csv\n", "test.csv", actor=None)
        assert m.actor != ""
        assert m.actor == "system"


class TestWeatherQualification:
    def test_weather_source_qualification_in_result(self):
        result = get_dju_for_year("75001", 2025)
        assert result.provider in ("promeos_reference_table", "manual")
        assert result.source_ref is not None
        assert result.retrieved_at is not None

    def test_manual_override_always_low_confidence(self):
        result = get_dju_for_year("75001", 2025, dju_heating_override=1800)
        assert result.confidence == "low"
        assert result.source_verified is False
        assert len(result.warnings) > 0

    def test_auto_source_has_source_ref(self):
        result = get_dju_for_year("44000", 2025)
        assert "RT2012" in result.source_ref
        assert result.source_verified is True
