"""
PROMEOS — Tests normalisation climatique OPERAT.
Covers: DJU ratio, absence meteo, conservation brute, confidence, warnings.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Organisation, TertiaireEfa, TertiaireEfaConsumption
from services.operat_normalization import normalize_consumption, get_normalization_history
from services.operat_trajectory import declare_consumption, validate_trajectory


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
    e = TertiaireEfa(org_id=org.id, nom="EFA Norm Test")
    db.add(e)
    db.flush()
    return e


class TestNormalizeConsumption:
    def test_dju_ratio_correct(self, db, efa):
        """DJU observe 2000, reference 2200 → conso normalisee = brute * 1.1"""
        declare_consumption(db, efa.id, year=2025, kwh_total=300000, source="factures")
        conso = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == efa.id, TertiaireEfaConsumption.year == 2025)
            .first()
        )

        result = normalize_consumption(db, conso.id, dju_heating=2000, dju_reference=2200)
        assert result["normalized_kwh"] == 330000  # 300000 * 2200/2000
        assert result["method"] == "dju_ratio"
        assert result["raw_kwh"] == 300000

    def test_raw_never_overwritten(self, db, efa):
        """La valeur brute kwh_total ne doit JAMAIS etre modifiee."""
        declare_consumption(db, efa.id, year=2025, kwh_total=300000)
        conso = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == efa.id, TertiaireEfaConsumption.year == 2025)
            .first()
        )

        normalize_consumption(db, conso.id, dju_heating=2000, dju_reference=2200)
        db.refresh(conso)
        assert conso.kwh_total == 300000  # brute intacte
        assert conso.normalized_kwh_total == 330000  # normalisee a cote

    def test_no_normalization_if_no_dju(self, db, efa):
        """Sans DJU, pas de normalisation — warning explicite."""
        declare_consumption(db, efa.id, year=2025, kwh_total=300000)
        conso = db.query(TertiaireEfaConsumption).filter(TertiaireEfaConsumption.efa_id == efa.id).first()

        result = normalize_consumption(db, conso.id, dju_heating=None, dju_reference=None)
        assert result["normalized_kwh"] is None
        assert result["method"] == "none"
        assert any("insuffisantes" in w for w in result["warnings"])

    def test_confidence_high_small_ecart(self, db, efa):
        """Ecart DJU <= 5% → confiance high."""
        declare_consumption(db, efa.id, year=2025, kwh_total=300000)
        conso = db.query(TertiaireEfaConsumption).filter(TertiaireEfaConsumption.efa_id == efa.id).first()

        result = normalize_consumption(db, conso.id, dju_heating=2000, dju_reference=2050)
        assert result["confidence"] == "high"

    def test_confidence_low_big_ecart(self, db, efa):
        """Ecart DJU > 15% → confiance low + warning."""
        declare_consumption(db, efa.id, year=2025, kwh_total=300000)
        conso = db.query(TertiaireEfaConsumption).filter(TertiaireEfaConsumption.efa_id == efa.id).first()

        result = normalize_consumption(db, conso.id, dju_heating=2000, dju_reference=2500)
        assert result["confidence"] == "low"
        assert any("verifier" in w for w in result["warnings"])


class TestTrajectoryWithNormalization:
    def test_trajectory_shows_both_raw_and_normalized(self, db, efa):
        """Trajectoire retourne brute et normalisee quand disponible."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=320000)

        # Normaliser la conso 2025
        conso = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == efa.id, TertiaireEfaConsumption.year == 2025)
            .first()
        )
        normalize_consumption(db, conso.id, dju_heating=2000, dju_reference=2200)

        result = validate_trajectory(db, efa.id, 2025)
        assert result["current"]["kwh"] == 320000  # brute
        assert result["current"]["normalized_kwh"] == 352000  # 320000 * 1.1
        assert result["normalization"]["applied"] is True
        assert result["raw_status"] is not None
        assert result["normalized_status"] is not None

    def test_trajectory_warning_when_not_normalized(self, db, efa):
        """Si pas normalise, warning explicite."""
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=280000)

        result = validate_trajectory(db, efa.id, 2025)
        assert result["normalization"]["applied"] is False
        assert any("brutes non normalisees" in w for w in result["warnings"])


class TestNormalizationHistory:
    def test_history_returns_all_years(self, db, efa):
        declare_consumption(db, efa.id, year=2019, kwh_total=500000, is_reference=True)
        declare_consumption(db, efa.id, year=2025, kwh_total=300000)

        conso = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == efa.id, TertiaireEfaConsumption.year == 2025)
            .first()
        )
        normalize_consumption(db, conso.id, dju_heating=2000, dju_reference=2200)

        history = get_normalization_history(db, efa.id)
        assert len(history) == 2
        norm_2025 = next(h for h in history if h["year"] == 2025)
        assert norm_2025["is_normalized"] is True
        assert norm_2025["normalized_kwh"] == 330000
