"""
PROMEOS — Tests trajectoire OPERAT (Decret Tertiaire)
Covers: modele consommation, calcul trajectoire, garde-fous.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Organisation, TertiaireEfa, TertiaireEfaConsumption
from services.operat_trajectory import (
    declare_consumption,
    validate_trajectory,
    get_consumption_history,
    get_efa_baseline_kwh,
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
    e = TertiaireEfa(org_id=org.id, nom="EFA Test")
    db.add(e)
    db.flush()
    return e


# ── Declaration consommation ─────────────────────────────────────────


class TestDeclareConsumption:
    def test_declare_reference_year(self, db, efa):
        result = declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True, source="factures")
        assert result["kwh_total"] == 500000
        assert result["is_reference"] is True

        # EFA cache mis a jour
        db.refresh(efa)
        assert efa.reference_year == 2019
        assert efa.reference_year_kwh == 500000

    def test_declare_current_year(self, db, efa):
        result = declare_consumption(db, efa.id, year=2025, kwh_total=320000)
        assert result["kwh_total"] == 320000
        assert result["is_reference"] is False

    def test_refuse_two_reference_years(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        with pytest.raises(ValueError, match="annee de reference existe"):
            declare_consumption(db, efa.id, year=2020, kwh_total=480000, is_reference=True)

    def test_update_same_year(self, db, efa):
        declare_consumption(db, efa.id, year=2025, kwh_total=300000)
        declare_consumption(db, efa.id, year=2025, kwh_total=310000)
        history = get_consumption_history(db, efa.id)
        assert len(history) == 1
        assert history[0]["kwh_total"] == 310000

    def test_refuse_negative_kwh(self, db, efa):
        with pytest.raises(ValueError, match="negatif"):
            declare_consumption(db, efa.id, year=2025, kwh_total=-100)

    def test_refuse_invalid_year(self, db, efa):
        with pytest.raises(ValueError, match="hors plage"):
            declare_consumption(db, efa.id, year=1900, kwh_total=100000)


# ── Validation trajectoire ───────────────────────────────────────────


class TestValidateTrajectory:
    def test_not_evaluable_without_baseline(self, db, efa):
        result = validate_trajectory(db, efa.id, 2025)
        assert result["status"] == "not_evaluable"
        assert "reference_year_consumption" in result["missing_fields"]

    def test_not_evaluable_without_current(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        result = validate_trajectory(db, efa.id, 2025)
        assert result["status"] == "not_evaluable"
        assert result["baseline"]["kwh"] == 500000
        assert result["current"]["kwh"] is None

    def test_on_track(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)  # < 300000 (60%)
        result = validate_trajectory(db, efa.id, 2025)
        assert result["status"] == "on_track"
        assert result["applicable_target_kwh"] == 300000  # 500000 * 0.60
        assert result["raw_delta_kwh"] < 0

    def test_off_track(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=350000)  # > 300000 (60%)
        result = validate_trajectory(db, efa.id, 2025)
        assert result["status"] == "off_track"
        assert result["raw_delta_kwh"] == 50000
        assert result["raw_delta_percent"] > 0

    def test_targets_2030_2040_2050(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=1000000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=700000)
        result = validate_trajectory(db, efa.id, 2025)
        assert result["targets"]["2030"] == 600000
        assert result["targets"]["2040"] == 500000
        assert result["targets"]["2050"] == 400000

    def test_applicable_target_year_2045(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=1000000, is_reference=True)
        declare_consumption(db, efa.id, year=2045, kwh_total=450000)
        result = validate_trajectory(db, efa.id, 2045)
        assert result["applicable_target_year"] == 2040
        assert result["applicable_target_kwh"] == 500000

    def test_warning_non_normalized(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=300000)
        result = validate_trajectory(db, efa.id, 2025)
        assert any("non normalisees" in w for w in result["warnings"])
        assert result["is_normalized"] is False


# ── Helpers ──────────────────────────────────────────────────────────


class TestHelpers:
    def test_baseline_kwh_none_if_absent(self, db, efa):
        assert get_efa_baseline_kwh(db, efa.id) is None

    def test_baseline_kwh_returns_value(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        assert get_efa_baseline_kwh(db, efa.id) == 500000

    def test_history_ordered_by_year(self, db, efa):
        declare_consumption(db, efa.id, year=2025, kwh_total=300000)
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2022, kwh_total=400000)
        history = get_consumption_history(db, efa.id)
        years = [h["year"] for h in history]
        assert years == [2019, 2022, 2025]
