"""Tests chargement tarifs reglementes YAML -> DB."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from services.market_tariff_loader import load_tariffs_from_yaml, get_current_tariff
from models.market_models import TariffType, TariffComponent, RegulatedTariff


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


class TestTariffLoader:

    def test_load_yaml_inserts_tariffs(self, db_session):
        result = load_tariffs_from_yaml(db_session)
        assert result["inserted"] > 0
        assert result["version"] == "2026-02"

    def test_load_yaml_idempotent(self, db_session):
        r1 = load_tariffs_from_yaml(db_session)
        r2 = load_tariffs_from_yaml(db_session)
        assert r2["inserted"] == 0
        assert r2["skipped"] == r1["inserted"]

    def test_cspe_c4_value_correct(self, db_session):
        load_tariffs_from_yaml(db_session)
        tariff = get_current_tariff(
            db_session, TariffType.CSPE, TariffComponent.CSPE_C4
        )
        assert tariff is not None
        assert tariff.value == 26.58
        assert tariff.unit == "EUR_MWH"

    def test_vnu_seuil_bas_correct(self, db_session):
        load_tariffs_from_yaml(db_session)
        tariff = get_current_tariff(
            db_session, TariffType.VNU, TariffComponent.VNU_SEUIL_BAS
        )
        assert tariff is not None
        assert tariff.value == 78.0

    def test_capacity_price_2026(self, db_session):
        load_tariffs_from_yaml(db_session)
        tariff = get_current_tariff(
            db_session, TariffType.CAPACITY, TariffComponent.CAPACITY_PRICE_MW
        )
        assert tariff is not None
        assert tariff.value == 98.6

    def test_versioning_no_update(self, db_session):
        """Verifie que le loader n'UPDATE jamais -- insert-only."""
        load_tariffs_from_yaml(db_session)
        count_before = db_session.query(RegulatedTariff).count()
        # Re-charger ne doit rien changer
        load_tariffs_from_yaml(db_session)
        count_after = db_session.query(RegulatedTariff).count()
        assert count_after == count_before
