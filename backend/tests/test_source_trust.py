"""
PROMEOS — Tests source trust : meteo, actor, baseline policy.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Organisation, TertiaireEfa, TertiaireEfaConsumption
from services.operat_trajectory import declare_consumption, validate_trajectory
from services.operat_normalization import normalize_consumption
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
def efa(db):
    org = Organisation(nom="TestOrg", type_client="tertiaire", actif=True, siren="123456789")
    db.add(org)
    db.flush()
    e = TertiaireEfa(org_id=org.id, nom="EFA Trust Test")
    db.add(e)
    db.flush()
    return e


# ── Weather Provider ─────────────────────────────────────────────────


class TestWeatherProvider:
    def test_auto_source_is_verified(self):
        result = get_dju_for_year("75001", 2025)
        assert result.source_verified is True
        assert result.provider == "promeos_reference_table"
        assert result.climate_zone in ("H1", "H2", "H3")

    def test_manual_override_not_verified(self):
        result = get_dju_for_year("75001", 2025, dju_heating_override=1800)
        assert result.source_verified is False
        assert result.provider == "manual"
        assert result.confidence == "low"

    def test_zone_detection_paris(self):
        result = get_dju_for_year("75001", 2025)
        assert result.climate_zone == "H1"

    def test_zone_detection_marseille(self):
        result = get_dju_for_year("13001", 2025)
        assert result.climate_zone == "H3"

    def test_zone_detection_nantes(self):
        result = get_dju_for_year("44000", 2025)
        assert result.climate_zone == "H2"

    def test_dju_reference_positive(self):
        result = get_dju_for_year("75001", 2025)
        assert result.dju_reference > 0
        assert result.dju_heating > 0


# ── Actor Resolver ───────────────────────────────────────────────────


class TestActorResolver:
    def test_never_empty(self):
        assert resolve_actor() != ""
        assert resolve_actor(fallback=None) != ""

    def test_fallback_manual_unknown(self):
        assert resolve_actor() == "manual_unknown"

    def test_auth_email_priority(self):
        class FakeAuth:
            email = "user@test.com"
            user_id = 42

        assert resolve_actor(FakeAuth()) == "user@test.com"

    def test_auth_user_id_if_no_email(self):
        class FakeAuth:
            email = None
            user_id = 42

        assert resolve_actor(FakeAuth()) == "user_42"

    def test_header_actor(self):
        class FakeRequest:
            headers = {"X-Actor": "api_bot"}

        assert resolve_actor(request=FakeRequest()) == "api_bot"


# ── Baseline Policy ─────────────────────────────────────────────────


class TestBaselinePolicy:
    def test_baseline_raw_only_status(self, db, efa):
        """Baseline non normalisee → raw_only."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        result = validate_trajectory(db, efa.id, 2025)
        assert result["baseline_normalization_status"] == "raw_only"
        assert result["baseline"]["normalization_status"] == "raw_only"

    def test_baseline_normalized_status(self, db, efa):
        """Baseline normalisee → normalized."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        c = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == efa.id, TertiaireEfaConsumption.year == 2019)
            .first()
        )
        normalize_consumption(db, c.id, dju_heating=2000, dju_reference=2200, weather_data_source="meteo_france")
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        result = validate_trajectory(db, efa.id, 2025)
        assert result["baseline_normalization_status"] == "normalized"

    def test_no_optimistic_final_when_baseline_raw(self, db, efa):
        """Pas de final_status optimiste si baseline brute + current normalisee."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        c = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == efa.id, TertiaireEfaConsumption.year == 2025)
            .first()
        )
        normalize_consumption(db, c.id, dju_heating=2000, dju_reference=2050, weather_data_source="meteo_france")
        result = validate_trajectory(db, efa.id, 2025)
        # Baseline non normalisee → ne peut pas etre normalized_authoritative
        assert result["final_status_mode"] != "normalized_authoritative"
        assert any("mixte" in w.lower() for w in result["major_warnings"])

    def test_weather_provider_in_response(self, db, efa):
        """Le provider meteo est expose dans la reponse."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)
        c = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == efa.id, TertiaireEfaConsumption.year == 2025)
            .first()
        )
        normalize_consumption(
            db, c.id, dju_heating=2000, dju_reference=2200, weather_data_source="promeos_reference_table"
        )
        result = validate_trajectory(db, efa.id, 2025)
        assert result["weather_provider"] == "promeos_reference_table"
