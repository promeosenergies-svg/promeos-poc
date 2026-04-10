"""
PROMEOS — Tests data model Vague 2 (ATRD gaz détaillé).

Verrouille :
- Enums AtrdOption / GasProfileGrdf
- Colonnes gaz sur DeliveryPoint (atrd_option, car_kwh, cja_mwh_per_day, gas_profile, cjn_mwh_per_day)
- Seed vague2 : dérivation depuis CAR + fallback T2 + idempotence
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models.enums import (
    AtrdOption,
    DeliveryPointEnergyType,
    GasProfileGrdf,
)
from models.patrimoine import DeliveryPoint
from models.site import Site
from services.billing_engine.vague2_seed import seed_vague2


# ── Enums ─────────────────────────────────────────────────────────────────


class TestAtrdEnums:
    def test_atrd_option_values(self):
        assert AtrdOption.T1.value == "T1"
        assert AtrdOption.T2.value == "T2"
        assert AtrdOption.T3.value == "T3"
        assert AtrdOption.T4.value == "T4"
        assert AtrdOption.TP.value == "TP"

    def test_gas_profile_grdf_values(self):
        for p in ("BASE", "B0", "B1", "B2I", "MODULANT"):
            assert GasProfileGrdf(p).value == p


# ── DeliveryPoint nouvelles colonnes ─────────────────────────────────────


@pytest.fixture
def db_session():
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
def db_with_gas_pdls(db_session: Session):
    """Site + 1 PDL élec + 3 PDLs gaz (sans atrd_option)."""
    site = Site(nom="TestSite", type="bureau", surface_m2=1000)
    db_session.add(site)
    db_session.flush()

    pdl_elec = DeliveryPoint(
        code="30000000000001",
        energy_type=DeliveryPointEnergyType.ELEC,
        site_id=site.id,
    )
    pdl_gaz_t1 = DeliveryPoint(
        code="70000000000001",
        energy_type=DeliveryPointEnergyType.GAZ,
        site_id=site.id,
        car_kwh=5_000.0,  # < 6000 → T1
    )
    pdl_gaz_t2 = DeliveryPoint(
        code="70000000000002",
        energy_type=DeliveryPointEnergyType.GAZ,
        site_id=site.id,
        car_kwh=150_000.0,  # 6k-300k → T2
    )
    pdl_gaz_no_car = DeliveryPoint(
        code="70000000000003",
        energy_type=DeliveryPointEnergyType.GAZ,
        site_id=site.id,
        # pas de CAR → fallback T2
    )
    db_session.add_all([pdl_elec, pdl_gaz_t1, pdl_gaz_t2, pdl_gaz_no_car])
    db_session.commit()
    return db_session, site, pdl_elec, pdl_gaz_t1, pdl_gaz_t2, pdl_gaz_no_car


class TestDeliveryPointGasColumns:
    def test_has_atrd_option_column(self, db_with_gas_pdls):
        db, _, _, pdl_t1, _, _ = db_with_gas_pdls
        pdl_t1.atrd_option = AtrdOption.T1
        db.commit()
        assert pdl_t1.atrd_option == AtrdOption.T1

    def test_has_car_kwh(self, db_with_gas_pdls):
        _, _, _, pdl_t1, pdl_t2, _ = db_with_gas_pdls
        assert pdl_t1.car_kwh == 5_000.0
        assert pdl_t2.car_kwh == 150_000.0

    def test_has_capacity_columns(self, db_with_gas_pdls):
        db, _, _, _, _, pdl_no_car = db_with_gas_pdls
        pdl_no_car.cjn_mwh_per_day = 12.5
        pdl_no_car.cja_mwh_per_day = 15.0
        db.commit()
        assert pdl_no_car.cjn_mwh_per_day == 12.5
        assert pdl_no_car.cja_mwh_per_day == 15.0

    def test_has_gas_profile(self, db_with_gas_pdls):
        db, _, _, _, pdl_t2, _ = db_with_gas_pdls
        pdl_t2.gas_profile = GasProfileGrdf.B1
        db.commit()
        assert pdl_t2.gas_profile == GasProfileGrdf.B1


# ── Seed Vague 2 ──────────────────────────────────────────────────────────


class TestSeedVague2:
    def test_seed_derives_t1_from_small_car(self, db_with_gas_pdls):
        db, _, _, pdl_t1, _, _ = db_with_gas_pdls
        summary = seed_vague2(db)
        db.refresh(pdl_t1)
        assert pdl_t1.atrd_option == AtrdOption.T1
        assert summary.atrd_option_set == 3  # T1 + T2 + fallback

    def test_seed_derives_t2_from_medium_car(self, db_with_gas_pdls):
        db, _, _, _, pdl_t2, _ = db_with_gas_pdls
        seed_vague2(db)
        db.refresh(pdl_t2)
        assert pdl_t2.atrd_option == AtrdOption.T2

    def test_seed_fallback_t2_when_no_car(self, db_with_gas_pdls):
        db, _, _, _, _, pdl_no_car = db_with_gas_pdls
        seed_vague2(db)
        db.refresh(pdl_no_car)
        assert pdl_no_car.atrd_option == AtrdOption.T2

    def test_seed_skips_elec_pdls(self, db_with_gas_pdls):
        db, _, pdl_elec, _, _, _ = db_with_gas_pdls
        summary = seed_vague2(db)
        db.refresh(pdl_elec)
        assert pdl_elec.atrd_option is None
        assert summary.skipped_non_gas == 1

    def test_seed_idempotent(self, db_with_gas_pdls):
        db, _, _, _, _, _ = db_with_gas_pdls
        first = seed_vague2(db)
        second = seed_vague2(db)
        assert first.atrd_option_set == 3
        assert second.atrd_option_set == 0
        assert second.skipped_already_populated == 3

    def test_seed_preserves_explicit_option(self, db_session: Session):
        """Un PDL déjà configuré explicitement n'est pas écrasé par le seed."""
        site = Site(nom="S", type="bureau", surface_m2=500)
        db_session.add(site)
        db_session.flush()
        pdl = DeliveryPoint(
            code="70000000000099",
            energy_type=DeliveryPointEnergyType.GAZ,
            site_id=site.id,
            car_kwh=5_000.0,  # dériverait T1
            atrd_option=AtrdOption.T3,  # mais déjà fixé à T3
        )
        db_session.add(pdl)
        db_session.commit()

        seed_vague2(db_session)
        db_session.refresh(pdl)
        assert pdl.atrd_option == AtrdOption.T3  # préservé
