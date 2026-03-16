"""
PROMEOS — Tests gouvernance statut final trajectoire OPERAT.
Covers: arbitrage final_status, modes, major_warnings, baseline policy.
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
from services.operat_trajectory import declare_consumption, validate_trajectory
from services.operat_normalization import normalize_consumption


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
    e = TertiaireEfa(org_id=org.id, nom="EFA Decision Test")
    db.add(e)
    db.flush()
    return e


def _conso(db, efa_id, year):
    return (
        db.query(TertiaireEfaConsumption)
        .filter(TertiaireEfaConsumption.efa_id == efa_id, TertiaireEfaConsumption.year == year)
        .first()
    )


class TestFinalStatusGovernance:
    def test_raw_only_when_no_normalization(self, db, efa):
        """Sans normalisation → final_status = raw, mode = raw_only."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        result = validate_trajectory(db, efa.id, 2025)
        assert result["final_status_mode"] == "raw_only"
        assert result["final_status"] == result["raw_status"]

    def test_normalized_authoritative_when_verified_high(self, db, efa):
        """Normalisation high + source verifiee → normalized_authoritative."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        # Normaliser avec source verifiee et ecart faible
        c = _conso(db, efa.id, 2025)
        normalize_consumption(db, c.id, dju_heating=2000, dju_reference=2050, weather_data_source="meteo_france")
        result = validate_trajectory(db, efa.id, 2025)
        assert result["final_status_mode"] == "mixed_basis_warning"  # baseline non normalisee
        assert result["normalization"]["source_verified"] is True

    def test_review_required_when_low_confidence(self, db, efa):
        """Normalisation low confidence → review_required."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        c = _conso(db, efa.id, 2025)
        normalize_consumption(db, c.id, dju_heating=2000, dju_reference=2500, weather_data_source="meteo_france")
        result = validate_trajectory(db, efa.id, 2025)
        assert result["final_status"] == "review_required"
        assert any("faible" in w.lower() for w in result["major_warnings"])

    def test_review_required_when_manual_source(self, db, efa):
        """Source meteo manuelle → review_required."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        c = _conso(db, efa.id, 2025)
        normalize_consumption(db, c.id, dju_heating=2000, dju_reference=2050, weather_data_source="manual")
        result = validate_trajectory(db, efa.id, 2025)
        assert result["final_status"] == "review_required"
        assert any("non verifiee" in w.lower() or "manuelle" in w.lower() for w in result["major_warnings"])

    def test_mixed_basis_when_baseline_not_normalized(self, db, efa):
        """Baseline non normalisee + current normalisee → mixed_basis_warning."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        c = _conso(db, efa.id, 2025)
        normalize_consumption(db, c.id, dju_heating=2000, dju_reference=2050, weather_data_source="meteo_france")
        result = validate_trajectory(db, efa.id, 2025)
        assert "mixed_basis" in result["final_status_mode"]
        assert any("mixte" in w.lower() for w in result["major_warnings"])

    def test_major_warnings_in_raw_only(self, db, efa):
        """Mode raw_only → major warning sur donnees brutes."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        result = validate_trajectory(db, efa.id, 2025)
        assert any("brutes" in w.lower() for w in result["major_warnings"])


class TestNormalizationAuditTrail:
    def test_normalize_creates_event(self, db, efa):
        """Normalisation cree un event log."""
        declare_consumption(db, efa.id, year=2025, kwh_total=300000)
        c = _conso(db, efa.id, 2025)
        normalize_consumption(db, c.id, dju_heating=2000, dju_reference=2200)
        events = db.query(ComplianceEventLog).filter(ComplianceEventLog.action == "normalize").all()
        assert len(events) >= 1
        assert events[0].actor != ""


class TestWeatherSourceVerification:
    def test_meteo_france_is_verified(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        c = _conso(db, efa.id, 2025)
        normalize_consumption(db, c.id, dju_heating=2000, dju_reference=2050, weather_data_source="meteo_france")
        result = validate_trajectory(db, efa.id, 2025)
        assert result["normalization"]["source_verified"] is True

    def test_manual_is_not_verified(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        c = _conso(db, efa.id, 2025)
        normalize_consumption(db, c.id, dju_heating=2000, dju_reference=2050, weather_data_source="manual")
        result = validate_trajectory(db, efa.id, 2025)
        assert result["normalization"]["source_verified"] is False
