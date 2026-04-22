"""Tests E2E du pipeline de promotion avec DB raw et DB produit séparées."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import data_ingestion.enedis.models  # noqa: F401
import data_staging.models  # noqa: F401
import models  # noqa: F401
from data_ingestion.enedis.migrations import run_flux_data_migrations
from data_ingestion.enedis.models import EnedisFluxFile, EnedisFluxMesureR4x
from data_staging.bridge import invalidate_promoted_cache
from data_staging.engine import run_promotion
from data_staging.models import MeterLoadCurve, PromotionRun, UnmatchedPrm
from models.base import Base
from models.energy_models import Meter
from models.enums import DeliveryPointEnergyType, EnergyVector, TypeSite
from models.patrimoine import DeliveryPoint
from models.site import Site


@pytest.fixture
def e2e_dbs():
    """Create one main DB and one raw flux DB for each test."""
    main_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    raw_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=main_engine)
    run_flux_data_migrations(raw_engine)

    MainSession = sessionmaker(bind=main_engine)
    RawSession = sessionmaker(bind=raw_engine)
    main_db = MainSession()
    raw_db = RawSession()
    invalidate_promoted_cache()

    try:
        yield main_db, raw_db, raw_engine
    finally:
        main_db.close()
        raw_db.close()
        invalidate_promoted_cache()


def _seed_site(db: Session, suffix: str) -> Site:
    site = Site(
        nom=f"E2E Site {suffix}",
        type=TypeSite.BUREAU,
        actif=True,
    )
    db.add(site)
    db.flush()
    return site


def _seed_meter_with_prm(db: Session, prm_code: str, site_id: int) -> int:
    dp = DeliveryPoint(code=prm_code, site_id=site_id, energy_type=DeliveryPointEnergyType.ELEC)
    db.add(dp)
    db.flush()

    meter = Meter(
        meter_id=prm_code,
        name=f"E2E meter {prm_code}",
        energy_vector=EnergyVector.ELECTRICITY,
        site_id=site_id,
        delivery_point_id=dp.id,
        is_active=True,
        subscribed_power_kva=100,
    )
    db.add(meter)
    db.flush()
    return meter.id


def _seed_flux_file(db: Session, flux_type: str = "R4H") -> int:
    now = datetime.now().astimezone()
    ff = EnedisFluxFile(
        filename=f"e2e_test_{flux_type}_{now.strftime('%H%M%S%f')}.zip",
        file_hash=f"e2e_hash_{flux_type}_{now.timestamp()}",
        flux_type=flux_type,
        status="parsed",
        measures_count=0,
        version=1,
    )
    db.add(ff)
    db.flush()
    return ff.id


def _seed_r4x_measures(db: Session, flux_file_id: int, prm_code: str, count: int = 10, base_power_kw: float = 50.0):
    base_ts = datetime(2025, 6, 15, 10, 0, 0)
    for i in range(count):
        ts = base_ts + timedelta(minutes=10 * i)
        db.add(
            EnedisFluxMesureR4x(
                flux_file_id=flux_file_id,
                flux_type="R4H",
                point_id=prm_code,
                grandeur_physique="EA",
                grandeur_metier="CONS",
                unite_mesure="kW",
                granularite="10",
                horodatage=ts.isoformat(),
                valeur_point=str(base_power_kw + i),
                statut_point="R",
            )
        )
    db.flush()


class TestE2ESF5Pipeline:
    """Validation complète raw DB -> promotion -> bridge."""

    def test_full_chain_unmatched_prm(self, e2e_dbs):
        main_db, raw_db, _raw_engine = e2e_dbs
        flux_file_id = _seed_flux_file(raw_db, "R4H")
        _seed_r4x_measures(raw_db, flux_file_id, "99999999999001", count=5)
        raw_db.commit()

        run = run_promotion(main_db, mode="full", triggered_by="e2e_test", flux_db=raw_db)

        assert run.status == "completed"
        assert run.prms_total == 1
        assert run.prms_unmatched == 1
        assert run.rows_load_curve == 0

        backlog = main_db.query(UnmatchedPrm).filter(UnmatchedPrm.point_id == "99999999999001").first()
        assert backlog is not None
        assert backlog.block_reason == "no_delivery_point"

    def test_full_chain_matched_and_promoted_cross_db(self, e2e_dbs):
        main_db, raw_db, raw_engine = e2e_dbs
        site = _seed_site(main_db, "matched")
        prm = "99999999999002"
        meter_id = _seed_meter_with_prm(main_db, prm, site.id)
        main_db.commit()

        flux_file_id = _seed_flux_file(raw_db, "R4H")
        _seed_r4x_measures(raw_db, flux_file_id, prm, count=12, base_power_kw=75.0)
        raw_db.commit()

        run = run_promotion(main_db, mode="full", triggered_by="e2e_test", flux_db=raw_db)

        assert run.status == "completed"
        assert run.prms_matched == 1
        assert run.rows_load_curve == 12

        promoted_rows = main_db.query(MeterLoadCurve).filter(MeterLoadCurve.meter_id == meter_id).all()
        assert len(promoted_rows) == 12
        assert all(r.quality_score == 1.0 for r in promoted_rows)
        assert all(r.is_estimated is False for r in promoted_rows)
        assert any((r.active_power_kw or 0) >= 75.0 for r in promoted_rows)

        raw_tables = set(inspect(raw_engine).get_table_names())
        assert "meter_load_curve" not in raw_tables
        assert raw_db.query(EnedisFluxMesureR4x).count() == 12
        assert main_db.query(PromotionRun).count() == 1

    def test_bridge_switches_to_promoted_after_promotion(self, e2e_dbs):
        main_db, raw_db, _raw_engine = e2e_dbs
        site = _seed_site(main_db, "bridge")
        prm = "99999999999003"
        meter_id = _seed_meter_with_prm(main_db, prm, site.id)
        main_db.commit()

        flux_file_id = _seed_flux_file(raw_db, "R4H")
        base_ts = datetime(2025, 1, 1, 0, 0, 0)
        for day in range(7):
            for hour in range(24):
                ts = base_ts + timedelta(days=day, hours=hour)
                raw_db.add(
                    EnedisFluxMesureR4x(
                        flux_file_id=flux_file_id,
                        flux_type="R4H",
                        point_id=prm,
                        grandeur_physique="EA",
                        grandeur_metier="CONS",
                        unite_mesure="kW",
                        granularite="10",
                        horodatage=ts.isoformat(),
                        valeur_point="100",
                        statut_point="R",
                    )
                )
        raw_db.commit()

        run = run_promotion(main_db, mode="full", triggered_by="e2e_test", flux_db=raw_db)
        assert run.rows_load_curve == 168

        from data_staging.bridge import get_readings

        readings, source = get_readings(main_db, [meter_id], datetime(2025, 1, 1), datetime(2025, 1, 7, 23, 59))

        assert source == "promoted"
        assert len(readings) == 168
        assert abs(readings[0].value_kwh - 16.67) < 0.1

    def test_promoted_cache_invalidation_after_run(self, e2e_dbs):
        main_db, raw_db, _raw_engine = e2e_dbs
        from data_staging import bridge as bridge_mod

        bridge_mod._promoted_available = False
        bridge_mod._promoted_checked_at = 999999999.0

        site = _seed_site(main_db, "cache")
        prm = "99999999999004"
        _seed_meter_with_prm(main_db, prm, site.id)
        main_db.commit()

        flux_file_id = _seed_flux_file(raw_db, "R4H")
        _seed_r4x_measures(raw_db, flux_file_id, prm, count=5)
        raw_db.commit()

        run_promotion(main_db, mode="full", triggered_by="e2e_test", flux_db=raw_db)

        assert bridge_mod._promoted_available is None
        assert bridge_mod._promoted_checked_at == 0.0

    def test_incremental_mode_respects_flux_high_water_mark(self, e2e_dbs):
        main_db, raw_db, _raw_engine = e2e_dbs
        site = _seed_site(main_db, "incremental")
        prm = "99999999999005"
        _seed_meter_with_prm(main_db, prm, site.id)
        main_db.commit()

        flux1 = _seed_flux_file(raw_db, "R4H")
        _seed_r4x_measures(raw_db, flux1, prm, count=5)
        raw_db.commit()

        run1 = run_promotion(main_db, mode="incremental", triggered_by="e2e_test", flux_db=raw_db)
        assert run1.rows_load_curve == 5

        run2 = run_promotion(main_db, mode="incremental", triggered_by="e2e_test", flux_db=raw_db)
        assert run2.rows_load_curve == 0

        flux2 = _seed_flux_file(raw_db, "R4H")
        for i in range(3):
            ts = datetime(2025, 7, 15, 10, i * 10)
            raw_db.add(
                EnedisFluxMesureR4x(
                    flux_file_id=flux2,
                    flux_type="R4H",
                    point_id=prm,
                    grandeur_physique="EA",
                    grandeur_metier="CONS",
                    unite_mesure="kW",
                    granularite="10",
                    horodatage=ts.isoformat(),
                    valeur_point="80",
                    statut_point="R",
                )
            )
        raw_db.commit()

        run3 = run_promotion(main_db, mode="incremental", triggered_by="e2e_test", flux_db=raw_db)
        assert run3.rows_load_curve == 3
