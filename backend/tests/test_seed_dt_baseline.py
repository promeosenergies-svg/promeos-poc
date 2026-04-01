"""
PROMEOS — Tests du seed DT baseline 2020-2023.
Couvre : baselines ADEME, derive, bruit, jalons DT, interpolation,
determinisme RNG, idempotence, monthly breakdown, gas scoping.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, EntiteJuridique, Portefeuille, TypeSite
from models.consumption_target import ConsumptionTarget
from services.demo_seed.gen_dt_baseline import (
    generate_dt_baseline,
    _interpolate_dt_reduction,
    _BASELINE_YEARS,
    _DT_MILESTONES,
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


def _seed_site(db, nom="Paris Test", type_site=TypeSite.BUREAU, surface=3500):
    org = Organisation(nom="DT Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ DT", siren="555666777")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF DT")
    db.add(pf)
    db.flush()
    site = Site(portefeuille_id=pf.id, nom=nom, type=type_site, surface_m2=surface, actif=True)
    db.add(site)
    db.flush()
    db.commit()
    return site


class TestDTBaseline:
    """Baselines ADEME et generation des records."""

    def test_generates_records_for_all_years(self, db):
        site = _seed_site(db)
        meta = {site.id: {"type_site": "bureau", "surface_m2": 3500}}
        generate_dt_baseline(db, [site], random.Random(42), site_meta=meta)
        db.commit()
        years = sorted(
            set(
                r.year
                for r in db.query(ConsumptionTarget)
                .filter(ConsumptionTarget.site_id == site.id, ConsumptionTarget.period == "yearly")
                .all()
            )
        )
        assert years == [2020, 2021, 2022, 2023]

    def test_baseline_2020_equals_ademe(self, db):
        site = _seed_site(db, surface=3500)
        meta = {site.id: {"type_site": "bureau", "surface_m2": 3500}}
        generate_dt_baseline(db, [site], random.Random(42), site_meta=meta)
        db.commit()
        rec = (
            db.query(ConsumptionTarget)
            .filter(
                ConsumptionTarget.site_id == site.id,
                ConsumptionTarget.period == "yearly",
                ConsumptionTarget.year == 2020,
                ConsumptionTarget.energy_type == "electricity",
            )
            .first()
        )
        # 2020 baseline: no noise, no drift → exact ADEME
        assert rec.actual_kwh == 595_000  # 170 × 3500
        assert rec.target_kwh == 595_000

    def test_drift_direction(self, db):
        site = _seed_site(db)
        meta = {site.id: {"type_site": "bureau", "surface_m2": 3500}}
        generate_dt_baseline(db, [site], random.Random(42), site_meta=meta)
        db.commit()
        records = {
            r.year: r.actual_kwh
            for r in db.query(ConsumptionTarget)
            .filter(
                ConsumptionTarget.site_id == site.id,
                ConsumptionTarget.period == "yearly",
                ConsumptionTarget.energy_type == "electricity",
            )
            .all()
        }
        assert records[2023] < records[2020]

    def test_drift_magnitude(self, db):
        site = _seed_site(db)
        meta = {site.id: {"type_site": "bureau", "surface_m2": 3500}}
        generate_dt_baseline(db, [site], random.Random(42), site_meta=meta)
        db.commit()
        records = {
            r.year: r.actual_kwh
            for r in db.query(ConsumptionTarget)
            .filter(
                ConsumptionTarget.site_id == site.id,
                ConsumptionTarget.period == "yearly",
                ConsumptionTarget.energy_type == "electricity",
            )
            .all()
        }
        # 2023 should be ~baseline × 0.955 (±3% noise)
        ratio = records[2023] / records[2020]
        assert 0.92 < ratio < 0.99, f"2023/2020 ratio = {ratio:.4f}"

    def test_deterministic_rng_42(self, db):
        site = _seed_site(db)
        meta = {site.id: {"type_site": "bureau", "surface_m2": 3500}}
        r1 = generate_dt_baseline(db, [site], random.Random(42), site_meta=meta)
        db.commit()
        vals1 = [
            r.actual_kwh
            for r in db.query(ConsumptionTarget)
            .filter(ConsumptionTarget.site_id == site.id, ConsumptionTarget.period == "yearly")
            .order_by(ConsumptionTarget.year)
            .all()
        ]
        # Clear and re-run
        db.query(ConsumptionTarget).filter(ConsumptionTarget.site_id == site.id).delete()
        db.commit()
        generate_dt_baseline(db, [site], random.Random(42), site_meta=meta)
        db.commit()
        vals2 = [
            r.actual_kwh
            for r in db.query(ConsumptionTarget)
            .filter(ConsumptionTarget.site_id == site.id, ConsumptionTarget.period == "yearly")
            .order_by(ConsumptionTarget.year)
            .all()
        ]
        assert vals1 == vals2

    def test_idempotent_skip(self, db):
        site = _seed_site(db)
        meta = {site.id: {"type_site": "bureau", "surface_m2": 3500}}
        r1 = generate_dt_baseline(db, [site], random.Random(42), site_meta=meta)
        db.commit()
        r2 = generate_dt_baseline(db, [site], random.Random(42), site_meta=meta)
        db.commit()
        assert r1["dt_baseline_count"] > 0
        assert r2["dt_baseline_count"] == 0

    def test_monthly_records_created(self, db):
        site = _seed_site(db)
        meta = {site.id: {"type_site": "bureau", "surface_m2": 3500}}
        generate_dt_baseline(db, [site], random.Random(42), site_meta=meta)
        db.commit()
        monthly = (
            db.query(ConsumptionTarget)
            .filter(
                ConsumptionTarget.site_id == site.id,
                ConsumptionTarget.period == "monthly",
                ConsumptionTarget.energy_type == "electricity",
            )
            .all()
        )
        # 4 years × 12 months = 48 monthly records for electricity
        assert len(monthly) == 48

    def test_monthly_sum_approx_yearly(self, db):
        site = _seed_site(db)
        meta = {site.id: {"type_site": "bureau", "surface_m2": 3500}}
        generate_dt_baseline(db, [site], random.Random(42), site_meta=meta)
        db.commit()
        yearly_rec = (
            db.query(ConsumptionTarget)
            .filter(
                ConsumptionTarget.site_id == site.id,
                ConsumptionTarget.period == "yearly",
                ConsumptionTarget.year == 2020,
                ConsumptionTarget.energy_type == "electricity",
            )
            .first()
        )
        monthly_sum = sum(
            r.target_kwh
            for r in db.query(ConsumptionTarget)
            .filter(
                ConsumptionTarget.site_id == site.id,
                ConsumptionTarget.period == "monthly",
                ConsumptionTarget.year == 2020,
                ConsumptionTarget.energy_type == "electricity",
            )
            .all()
        )
        # Monthly targets should approximately sum to yearly (rounding tolerance)
        assert abs(monthly_sum - yearly_rec.target_kwh) < yearly_rec.target_kwh * 0.02


class TestDTInterpolation:
    """Jalons DT et interpolation."""

    def test_2020_reduction_is_zero(self):
        assert _interpolate_dt_reduction(2020) == 0.0

    def test_2030_reduction_is_minus_40(self):
        assert abs(_interpolate_dt_reduction(2030) - (-0.40)) < 0.001

    def test_2025_interpolated(self):
        # 2025: 5/10 of the way from 0% to -40% = -20%
        assert abs(_interpolate_dt_reduction(2025) - (-0.20)) < 0.001

    def test_2040_reduction_is_minus_50(self):
        assert abs(_interpolate_dt_reduction(2040) - (-0.50)) < 0.001

    def test_2050_reduction_is_minus_60(self):
        assert abs(_interpolate_dt_reduction(2050) - (-0.60)) < 0.001

    def test_before_ref_year(self):
        assert _interpolate_dt_reduction(2019) == 0.0


class TestDTSourceGuards:
    """Constantes DT conformes au Decret n°2019-771."""

    def test_milestones_official(self):
        assert _DT_MILESTONES[2030] == -0.40
        assert _DT_MILESTONES[2040] == -0.50
        assert _DT_MILESTONES[2050] == -0.60

    def test_baseline_years_complete(self):
        assert _BASELINE_YEARS == [2020, 2021, 2022, 2023]
