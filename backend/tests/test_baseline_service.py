"""
PROMEOS — Tests Phase 1.2 : baseline_service 3 méthodes A/B/C (Décisions B+D §0.D).

Source-guards :
  - test_baseline_method_documented : chaque retour expose method/calibration_date/confidence
  - test_no_baseline_computation_in_frontend : grep cockpit pages → 0 baseline=

Couverture service :
  - TestBaselineMethod        : 3 valeurs canoniques de l'enum
  - TestGetBaselineA          : site vide, happy path, seuils confidence
  - TestGetBaselineB          : fallback si <90 jours, fallback si calib absente, r²<0.7
  - TestGetBaselineC          : calibration enregistrée, fallback agrégation, site vide

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.2
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base
from models.baseline_calibration import BaselineCalibration, BaselineMethod
from models.energy_models import Meter, MeterReading, FrequencyType
from models.enums import EnergyVector
from services.baseline_service import (
    get_baseline_a,
    get_baseline_b,
    get_baseline_c,
)
from doctrine.constants import DT_REF_YEAR_DEFAULT

# ─── Fixtures ────────────────────────────────────────────────────────────────

_SITE_ID = 9001  # site fictif utilisé par tous les tests


@pytest.fixture(scope="module")
def engine():
    """Base SQLite en mémoire, tables créées une seule fois."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(engine):
    """Session isolée avec rollback automatique après chaque test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def _make_meter(db, site_id: int = _SITE_ID, meter_uid: str = "TEST-METER-001") -> Meter:
    meter = Meter(
        meter_id=meter_uid,
        name=f"Meter {meter_uid}",
        energy_vector=EnergyVector.ELECTRICITY,
        site_id=site_id,
    )
    db.add(meter)
    db.flush()
    return meter


def _add_readings(db, meter: Meter, start_date: date, n_days: int, value_kwh: float = 100.0):
    """Ajoute n_days relevés journaliers à partir de start_date."""
    for i in range(n_days):
        ts = datetime.combine(start_date + timedelta(days=i), datetime.min.time())
        reading = MeterReading(
            meter_id=meter.id,
            timestamp=ts,
            frequency=FrequencyType.DAILY,
            value_kwh=value_kwh,
        )
        db.add(reading)
    db.flush()


# ─── TestBaselineMethod ──────────────────────────────────────────────────────


class TestBaselineMethod:
    def test_a_historical_value(self):
        assert BaselineMethod.A_HISTORICAL.value == "a_historical"

    def test_b_dju_adjusted_value(self):
        assert BaselineMethod.B_DJU_ADJUSTED.value == "b_dju_adjusted"

    def test_c_regulatory_dt_value(self):
        assert BaselineMethod.C_REGULATORY_DT.value == "c_regulatory_dt"


# ─── TestGetBaselineA ────────────────────────────────────────────────────────


class TestGetBaselineA:
    def test_empty_site_returns_zero_faible(self, db):
        """Site sans compteur → value_kwh=0, confidence='faible', data_points=0."""
        result = get_baseline_a(db, site_id=99999, target_date=date(2026, 4, 28))
        assert result["value_kwh"] == 0.0
        assert result["confidence"] == "faible"
        assert result["data_points"] == 0
        assert result["method"] == "a_historical"

    def test_returns_canonical_fields(self, db):
        """Happy path : tous les champs canoniques sont présents."""
        meter = _make_meter(db)
        today = date.today()
        _add_readings(db, meter, today - timedelta(weeks=10), n_days=28, value_kwh=80.0)

        result = get_baseline_a(db, site_id=_SITE_ID, target_date=today)
        assert "value_kwh" in result
        assert "calibration_date" in result
        assert "confidence" in result
        assert "method" in result
        assert "data_points" in result
        assert result["method"] == "a_historical"

    def test_confidence_haute_with_4_matching_weekdays(self, db):
        """4 mêmes jours de semaine dans la fenêtre → confidence='haute'."""
        meter = _make_meter(db)
        target = date(2026, 4, 28)  # mardi
        # Ajouter 4 mardis dans les 12 dernières semaines
        for week in range(4, 8):
            ts = datetime.combine(target - timedelta(weeks=week), datetime.min.time())
            db.add(
                MeterReading(
                    meter_id=meter.id,
                    timestamp=ts,
                    frequency=FrequencyType.DAILY,
                    value_kwh=100.0,
                )
            )
        db.flush()

        result = get_baseline_a(db, site_id=_SITE_ID, target_date=target)
        assert result["confidence"] == "haute"
        assert result["data_points"] >= 4

    def test_confidence_moyenne_with_2_matching_weekdays(self, db):
        """2 mêmes jours de semaine → confidence='moyenne'."""
        meter = _make_meter(db)
        target = date(2026, 4, 29)  # mercredi
        for week in range(5, 7):
            ts = datetime.combine(target - timedelta(weeks=week), datetime.min.time())
            db.add(
                MeterReading(
                    meter_id=meter.id,
                    timestamp=ts,
                    frequency=FrequencyType.DAILY,
                    value_kwh=90.0,
                )
            )
        db.flush()

        result = get_baseline_a(db, site_id=_SITE_ID, target_date=target)
        assert result["confidence"] == "moyenne"
        assert result["data_points"] == 2

    def test_confidence_faible_with_1_matching_weekday(self, db):
        """1 seul même jour de semaine → confidence='faible'."""
        meter = _make_meter(db)
        target = date(2026, 4, 30)  # jeudi
        ts = datetime.combine(target - timedelta(weeks=6), datetime.min.time())
        db.add(
            MeterReading(
                meter_id=meter.id,
                timestamp=ts,
                frequency=FrequencyType.DAILY,
                value_kwh=75.0,
            )
        )
        db.flush()

        result = get_baseline_a(db, site_id=_SITE_ID, target_date=target)
        assert result["confidence"] == "faible"
        assert result["data_points"] == 1


# ─── TestGetBaselineB ────────────────────────────────────────────────────────


class TestGetBaselineB:
    def test_fallback_a_when_less_than_90_days_data(self, db):
        """< 90 jours de données → fallback A (method=a_historical)."""
        meter = _make_meter(db)
        # Seulement 10 relevés récents
        _add_readings(db, meter, date.today() - timedelta(days=10), n_days=10, value_kwh=50.0)

        result = get_baseline_b(db, site_id=_SITE_ID, target_date=date.today(), dju=5.0)
        assert result["method"] == "a_historical"

    def test_fallback_a_when_no_calibration_stored(self, db):
        """≥ 90 jours data mais aucune calibration B → fallback A."""
        meter = _make_meter(db)
        _add_readings(db, meter, date.today() - timedelta(days=89), n_days=90, value_kwh=60.0)
        # Aucune BaselineCalibration en DB

        result = get_baseline_b(db, site_id=_SITE_ID, target_date=date.today(), dju=8.0)
        assert result["method"] == "a_historical"

    def test_confidence_faible_when_r2_below_threshold(self, db):
        """r² < 0.7 → confidence='faible' mais méthode B retournée."""
        meter = _make_meter(db)
        # 90 relevés dans les 89 derniers jours (tous dans la fenêtre 90j)
        _add_readings(db, meter, date.today() - timedelta(days=89), n_days=90, value_kwh=70.0)

        calib = BaselineCalibration(
            site_id=_SITE_ID,
            method=BaselineMethod.B_DJU_ADJUSTED.value,
            calibration_date=datetime.utcnow(),
            coefficient_a=2.5,
            coefficient_b=50.0,
            r_squared=0.45,  # < 0.7
            data_points=100,
            confidence="faible",
        )
        db.add(calib)
        db.flush()

        result = get_baseline_b(db, site_id=_SITE_ID, target_date=date.today(), dju=10.0)
        assert result["method"] == "b_dju_adjusted"
        assert result["confidence"] == "faible"
        assert result["r_squared"] == pytest.approx(0.45)

    def test_happy_path_r2_high(self, db):
        """r² ≥ 0.85 → confidence='haute', valeur E = a×DJU + b."""
        meter = _make_meter(db)
        _add_readings(db, meter, date.today() - timedelta(days=89), n_days=90, value_kwh=80.0)

        calib = BaselineCalibration(
            site_id=_SITE_ID,
            method=BaselineMethod.B_DJU_ADJUSTED.value,
            calibration_date=datetime.utcnow(),
            coefficient_a=3.0,
            coefficient_b=100.0,
            r_squared=0.92,  # ≥ 0.85
            data_points=100,
            confidence="haute",
        )
        db.add(calib)
        db.flush()

        dju = 20.0
        result = get_baseline_b(db, site_id=_SITE_ID, target_date=date.today(), dju=dju)
        assert result["method"] == "b_dju_adjusted"
        assert result["confidence"] == "haute"
        assert result["value_kwh"] == pytest.approx(3.0 * dju + 100.0, rel=1e-3)
        assert result["a"] == pytest.approx(3.0)
        assert result["b"] == pytest.approx(100.0)

    def test_returns_canonical_fields(self, db):
        """Contrat de retour : tous les champs canoniques présents."""
        result = get_baseline_b(db, site_id=99998, target_date=date.today(), dju=5.0)
        assert "value_kwh" in result
        assert "calibration_date" in result
        assert "confidence" in result
        assert "method" in result
        assert "r_squared" in result
        assert "a" in result
        assert "b" in result


# ─── TestGetBaselineC ────────────────────────────────────────────────────────


class TestGetBaselineC:
    def test_calibration_recorded_returns_haute(self, db):
        """Calibration C enregistrée → confidence='haute', valeur depuis coefficient_a."""
        calib = BaselineCalibration(
            site_id=_SITE_ID,
            method=BaselineMethod.C_REGULATORY_DT.value,
            calibration_date=datetime.utcnow(),
            coefficient_a=450000.0,  # conso annuelle kWh
            ref_year=DT_REF_YEAR_DEFAULT,
            data_points=365,
            confidence="haute",
        )
        db.add(calib)
        db.flush()

        result = get_baseline_c(db, site_id=_SITE_ID, year=DT_REF_YEAR_DEFAULT)
        assert result["confidence"] == "haute"
        assert result["value_kwh_year"] == pytest.approx(450000.0)
        assert result["ref_year"] == DT_REF_YEAR_DEFAULT
        assert result["method"] == "c_regulatory_dt"

    def test_fallback_aggregation_when_no_calibration(self, db):
        """Pas de calibration C → agrégation MeterReading, confidence='moyenne'."""
        meter = _make_meter(db)
        # 10 relevés dans l'année de référence
        for day in range(10):
            ts = datetime(DT_REF_YEAR_DEFAULT, 6, 1) + timedelta(days=day)
            db.add(
                MeterReading(
                    meter_id=meter.id,
                    timestamp=ts,
                    frequency=FrequencyType.DAILY,
                    value_kwh=200.0,
                )
            )
        db.flush()

        result = get_baseline_c(db, site_id=_SITE_ID, year=DT_REF_YEAR_DEFAULT)
        assert result["confidence"] == "moyenne"
        assert result["value_kwh_year"] == pytest.approx(2000.0)  # 10 × 200
        assert result["method"] == "c_regulatory_dt"

    def test_empty_site_returns_zero_faible(self, db):
        """Site sans compteur → value_kwh_year=0, confidence='faible'."""
        result = get_baseline_c(db, site_id=99997, year=DT_REF_YEAR_DEFAULT)
        assert result["value_kwh_year"] == 0.0
        assert result["confidence"] == "faible"
        assert result["method"] == "c_regulatory_dt"

    def test_returns_canonical_fields(self, db):
        """Contrat de retour : tous les champs canoniques présents."""
        result = get_baseline_c(db, site_id=99996, year=DT_REF_YEAR_DEFAULT)
        assert "value_kwh_year" in result
        assert "ref_year" in result
        assert "method" in result
        assert "calibration_date" in result
        assert "confidence" in result


# ─── Source-guards §2.B ──────────────────────────────────────────────────────


class TestSourceGuards:
    def test_baseline_method_documented(self, db):
        """Source-guard : chaque retour expose method/calibration_date/confidence."""
        canonical_fields = {"method", "calibration_date", "confidence"}

        result_a = get_baseline_a(db, site_id=99990, target_date=date.today())
        assert canonical_fields.issubset(set(result_a.keys())), (
            f"get_baseline_a missing fields: {canonical_fields - set(result_a.keys())}"
        )

        result_b = get_baseline_b(db, site_id=99990, target_date=date.today(), dju=5.0)
        assert canonical_fields.issubset(set(result_b.keys())), (
            f"get_baseline_b missing fields: {canonical_fields - set(result_b.keys())}"
        )

        result_c = get_baseline_c(db, site_id=99990, year=DT_REF_YEAR_DEFAULT)
        # Méthode C retourne value_kwh_year (pas value_kwh) mais mêmes champs méta
        meta_fields = {"method", "calibration_date", "confidence"}
        assert meta_fields.issubset(set(result_c.keys())), (
            f"get_baseline_c missing fields: {meta_fields - set(result_c.keys())}"
        )

    def test_no_baseline_computation_in_frontend(self):
        """Source-guard statique : aucun calcul baseline dans les pages cockpit frontend."""
        cockpit_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "pages" / "cockpit"
        if not cockpit_dir.exists():
            pytest.skip(f"Dossier {cockpit_dir} absent — test non applicable")

        violations = []
        for jsx_file in cockpit_dir.glob("*.jsx"):
            content = jsx_file.read_text(encoding="utf-8", errors="ignore")
            # Détecter affectation ou calcul baseline dans le code JSX
            import re

            # Pattern : baseline suivi d'un opérateur assignation ou calcul
            if re.search(r"baseline\s*[+\-*/=]", content, re.IGNORECASE):
                # Exclure les lignes qui sont uniquement des passages de props ou import
                lines = content.splitlines()
                for i, line in enumerate(lines, 1):
                    stripped = line.strip()
                    # Ignorer les commentaires
                    if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                        continue
                    if re.search(r"baseline\s*[+\-*/=]", stripped, re.IGNORECASE):
                        violations.append(f"{jsx_file.name}:{i}: {stripped[:80]}")

        assert violations == [], (
            "Business logic baseline détectée dans le frontend cockpit — viole §0.D :\n" + "\n".join(violations)
        )

    def test_dt_ref_year_from_constants(self):
        """Source-guard : DT_REF_YEAR_DEFAULT utilisé dans get_baseline_c (pas hardcodé)."""
        import inspect
        from services import baseline_service

        source = inspect.getsource(baseline_service)
        # Le fichier ne doit pas contenir 2020 en tant que literal dans la signature par défaut
        # mais uniquement via la constante importée
        assert "DT_REF_YEAR_DEFAULT" in source, (
            "get_baseline_c doit utiliser DT_REF_YEAR_DEFAULT (doctrine §0.D : no hardcoded constants)"
        )
        # Vérifier que la constante est bien importée
        assert (
            "from backend.doctrine.constants import DT_REF_YEAR_DEFAULT" in source
            or "from doctrine.constants import DT_REF_YEAR_DEFAULT" in source
        ), "DT_REF_YEAR_DEFAULT doit être importé depuis doctrine.constants"
