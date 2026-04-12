"""Tests E2E du pipeline SF5 : staging → promote → bridge → service.

Valide la chaîne complète avec des données seed :
1. Créer un site + DeliveryPoint + Meter
2. Insérer des EnedisFluxMesureR4x en staging
3. Lancer run_promotion()
4. Vérifier que meter_load_curve contient les données converties
5. Vérifier que le bridge retourne data_source="promoted"
6. Vérifier que les services (load_profile) utilisent les données promues
"""

import pytest
from datetime import datetime, date, timezone, timedelta
from sqlalchemy.orm import Session

from database import SessionLocal, engine
from database.migrations import run_migrations
from data_ingestion.enedis.models import EnedisFluxFile, EnedisFluxMesureR4x
from data_staging.models import MeterLoadCurve, PromotionRun, UnmatchedPrm
from data_staging.engine import run_promotion
from data_staging.bridge import invalidate_promoted_cache, _is_promoted_available


@pytest.fixture
def e2e_db():
    """Session DB avec migrations appliquées, isolée par test."""
    run_migrations(engine)
    db = SessionLocal()
    # Nettoyer d'un test précédent
    db.query(MeterLoadCurve).delete()
    db.query(EnedisFluxMesureR4x).delete()
    db.query(EnedisFluxFile).filter(EnedisFluxFile.filename.like("e2e_test_%")).delete()
    db.query(PromotionRun).filter(PromotionRun.triggered_by == "e2e_test").delete()
    db.query(UnmatchedPrm).filter(UnmatchedPrm.point_id.like("99999%")).delete()
    db.commit()
    invalidate_promoted_cache()
    yield db
    # Cleanup
    db.query(MeterLoadCurve).delete()
    db.query(EnedisFluxMesureR4x).delete()
    db.query(EnedisFluxFile).filter(EnedisFluxFile.filename.like("e2e_test_%")).delete()
    db.query(PromotionRun).filter(PromotionRun.triggered_by == "e2e_test").delete()
    db.query(UnmatchedPrm).filter(UnmatchedPrm.point_id.like("99999%")).delete()
    db.commit()
    db.close()
    invalidate_promoted_cache()


def _seed_meter_with_prm(db: Session, prm_code: str, site_id: int = 1) -> int:
    """Crée DeliveryPoint + Meter pour un PRM donné. Retourne meter.id."""
    from models.patrimoine import DeliveryPoint
    from models.energy_models import Meter

    from models.enums import DeliveryPointEnergyType

    dp = db.query(DeliveryPoint).filter(DeliveryPoint.code == prm_code).first()
    if not dp:
        dp = DeliveryPoint(code=prm_code, site_id=site_id, energy_type=DeliveryPointEnergyType.ELEC)
        db.add(dp)
        db.flush()

    meter = db.query(Meter).filter(Meter.delivery_point_id == dp.id).first()
    if not meter:
        meter = Meter(
            meter_id=prm_code,
            name=f"E2E test {prm_code}",
            energy_vector="ELECTRICITY",
            site_id=site_id,
            delivery_point_id=dp.id,
            is_active=True,
            subscribed_power_kva=100,
        )
        db.add(meter)
        db.flush()

    return meter.id


def _seed_flux_file(db: Session, flux_type: str = "R4H") -> int:
    """Crée un EnedisFluxFile factice."""
    ff = EnedisFluxFile(
        filename=f"e2e_test_{flux_type}_{datetime.now(timezone.utc).strftime('%H%M%S%f')}.zip",
        file_hash=f"e2e_hash_{flux_type}_{datetime.now(timezone.utc).timestamp()}",
        flux_type=flux_type,
        status="parsed",
        measures_count=0,
        version=1,
    )
    db.add(ff)
    db.flush()
    return ff.id


def _seed_r4x_measures(db: Session, flux_file_id: int, prm_code: str, count: int = 10, base_power_kw: float = 50.0):
    """Seed N mesures R4x de 10 min pour un PRM."""
    base_ts = datetime(2025, 6, 15, 10, 0, 0)
    for i in range(count):
        ts = base_ts + timedelta(minutes=10 * i)
        m = EnedisFluxMesureR4x(
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
        db.add(m)
    db.flush()


# ── Tests E2E ────────────────────────────────────────────────────────────


class TestE2ESF5Pipeline:
    """Validation complète staging → promotion → bridge."""

    def test_full_chain_unmatched_prm(self, e2e_db):
        """PRM sans DeliveryPoint → va dans unmatched_prm."""
        db = e2e_db
        flux_file_id = _seed_flux_file(db, "R4H")
        _seed_r4x_measures(db, flux_file_id, "99999999999001", count=5)
        db.commit()

        run = run_promotion(db, mode="full", triggered_by="e2e_test")

        assert run.status == "completed"
        assert run.prms_total >= 1
        assert run.prms_unmatched >= 1
        assert run.rows_load_curve == 0  # Aucune row promue (PRM bloqué)

        # Vérifier que le PRM est dans le backlog
        backlog = db.query(UnmatchedPrm).filter(UnmatchedPrm.point_id == "99999999999001").first()
        assert backlog is not None
        assert backlog.block_reason == "no_delivery_point"

    def test_full_chain_matched_and_promoted(self, e2e_db):
        """PRM avec Meter → promotion réussie vers meter_load_curve."""
        db = e2e_db
        # Trouver un site existant
        from models.site import Site

        site = db.query(Site).first()
        assert site is not None, "Demo seed must provide at least one site"

        prm = "99999999999002"
        meter_id = _seed_meter_with_prm(db, prm, site_id=site.id)

        flux_file_id = _seed_flux_file(db, "R4H")
        _seed_r4x_measures(db, flux_file_id, prm, count=12, base_power_kw=75.0)
        db.commit()

        # Promotion
        run = run_promotion(db, mode="full", triggered_by="e2e_test")

        assert run.status == "completed"
        assert run.prms_matched >= 1
        assert run.rows_load_curve >= 12

        # Vérifier que les données sont dans meter_load_curve
        promoted_rows = db.query(MeterLoadCurve).filter(MeterLoadCurve.meter_id == meter_id).all()
        assert len(promoted_rows) == 12
        # Vérifier qualité (statut_point="R" → quality=1.0)
        assert all(r.quality_score == 1.0 for r in promoted_rows)
        assert all(r.is_estimated is False for r in promoted_rows)
        # Vérifier unité : active_power_kw (pas converti en Wh)
        assert all(r.active_power_kw is not None for r in promoted_rows)
        assert any(r.active_power_kw >= 75.0 for r in promoted_rows)

    def test_bridge_switches_to_promoted_after_promotion(self, e2e_db):
        """Après promotion, le bridge doit retourner data_source='promoted'."""
        db = e2e_db
        from models.site import Site

        site = db.query(Site).first()

        prm = "99999999999003"
        meter_id = _seed_meter_with_prm(db, prm, site_id=site.id)

        flux_file_id = _seed_flux_file(db, "R4H")
        # Seed 30 jours × 24h × 6 points/h = beaucoup de points
        # Simplification : 1 point par heure sur 7 jours
        base_ts = datetime(2025, 1, 1, 0, 0, 0)
        for day in range(7):
            for hour in range(24):
                ts = base_ts + timedelta(days=day, hours=hour)
                db.add(
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
        db.commit()

        run = run_promotion(db, mode="full", triggered_by="e2e_test")
        assert run.rows_load_curve >= 168  # 7 × 24

        # Test direct du bridge (pas via service, pour isoler)
        # Période ciblée pour avoir 100% coverage des données seedées
        from data_staging.bridge import get_readings

        readings, source = get_readings(db, [meter_id], datetime(2025, 1, 1), datetime(2025, 1, 7, 23, 59))

        assert source == "promoted", f"Expected promoted, got {source}"
        assert len(readings) >= 168
        # Conversion kW → kWh : 100 kW × (10/60) = 16.67 kWh par pas de 10min
        assert abs(readings[0].value_kwh - 16.67) < 0.1

    def test_promoted_cache_invalidation_after_run(self, e2e_db):
        """Le cache _is_promoted_available doit être invalidé après un run."""
        db = e2e_db
        invalidate_promoted_cache()

        # Avant : vérifier que _is_promoted_available met en cache
        from data_staging import bridge as bridge_mod

        bridge_mod._promoted_available = False
        bridge_mod._promoted_checked_at = 999999999.0  # Far future

        # Seed + run
        from models.site import Site

        site = db.query(Site).first()
        prm = "99999999999004"
        _seed_meter_with_prm(db, prm, site_id=site.id)
        flux_file_id = _seed_flux_file(db, "R4H")
        _seed_r4x_measures(db, flux_file_id, prm, count=5)
        db.commit()

        run_promotion(db, mode="full", triggered_by="e2e_test")

        # Après : le cache doit avoir été invalidé
        assert bridge_mod._promoted_available is None
        assert bridge_mod._promoted_checked_at == 0.0

    def test_incremental_mode_respects_high_water_mark(self, e2e_db):
        """Mode incremental ne retraite pas les rows déjà vues."""
        db = e2e_db
        from models.site import Site

        site = db.query(Site).first()

        prm = "99999999999005"
        _seed_meter_with_prm(db, prm, site_id=site.id)

        # Premier lot
        flux1 = _seed_flux_file(db, "R4H")
        _seed_r4x_measures(db, flux1, prm, count=5)
        db.commit()

        run1 = run_promotion(db, mode="incremental", triggered_by="e2e_test")
        rows_run1 = run1.rows_load_curve

        # Deuxième run sans nouvelles données → 0 rows promues
        run2 = run_promotion(db, mode="incremental", triggered_by="e2e_test")
        assert run2.rows_load_curve == 0

        # Ajouter de nouvelles mesures
        flux2 = _seed_flux_file(db, "R4H")
        for i in range(3):
            ts = datetime(2025, 7, 15, 10, i * 10)
            db.add(
                EnedisFluxMesureR4x(
                    flux_file_id=flux2,
                    flux_type="R4H",
                    point_id=prm,
                    grandeur_physique="EA",
                    granularite="10",
                    horodatage=ts.isoformat(),
                    valeur_point="80",
                    statut_point="R",
                )
            )
        db.commit()

        # Troisième run → 3 nouvelles rows
        run3 = run_promotion(db, mode="incremental", triggered_by="e2e_test")
        assert run3.rows_load_curve == 3
