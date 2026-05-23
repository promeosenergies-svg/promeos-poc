"""
PROMEOS — P0-C 2026-05-23 : test règle anomalie `_rule_delivery_point_without_contract`.

Vérifie que `compute_site_anomalies` détecte les points de livraison actifs
sans contrat énergie rattaché (sévérité HIGH).
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (  # noqa: E402
    Base,
    EnergyContract,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)
from models.enums import (  # noqa: E402
    BillingEnergyType,
    DeliveryPointEnergyType,
    DeliveryPointStatus,
)
from models.patrimoine import ContractDeliveryPoint, DeliveryPoint  # noqa: E402
from services.patrimoine_anomalies import compute_site_anomalies  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _seed_site(db, *, surface=1000):
    org = Organisation(nom="Org A", siren="111111111", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="111111111")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site Anomaly",
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        surface_m2=surface,
        actif=True,
    )
    db.add(site)
    db.commit()
    return site


def test_active_dp_without_contract_raises_high_anomaly(db):
    """DP actif sans contrat → 1 anomalie DELIVERY_POINT_WITHOUT_CONTRACT HIGH."""
    site = _seed_site(db)
    db.add(
        DeliveryPoint(
            site_id=site.id,
            code="14000000000001",
            energy_type=DeliveryPointEnergyType.ELEC,
            status=DeliveryPointStatus.ACTIVE,
        )
    )
    db.commit()

    result = compute_site_anomalies(site.id, db)
    coverage_anomalies = [a for a in result["anomalies"] if a["code"] == "DELIVERY_POINT_WITHOUT_CONTRACT"]
    assert len(coverage_anomalies) == 1
    assert coverage_anomalies[0]["severity"] == "HIGH"
    assert "Point de livraison" in coverage_anomalies[0]["title_fr"]
    assert "Rattacher un contrat" == coverage_anomalies[0]["cta"]["label"]


def test_active_dp_with_active_contract_no_anomaly(db):
    """DP actif couvert par contrat actif → pas d'anomalie DELIVERY_POINT_WITHOUT_CONTRACT."""
    site = _seed_site(db)
    dp = DeliveryPoint(
        site_id=site.id,
        code="14000000000002",
        energy_type=DeliveryPointEnergyType.ELEC,
        status=DeliveryPointStatus.ACTIVE,
    )
    db.add(dp)
    db.flush()
    today = date.today()
    ct = EnergyContract(
        site_id=site.id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF",
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=365),
    )
    db.add(ct)
    db.flush()
    db.add(ContractDeliveryPoint(contract_id=ct.id, delivery_point_id=dp.id))
    db.commit()

    result = compute_site_anomalies(site.id, db)
    coverage_anomalies = [a for a in result["anomalies"] if a["code"] == "DELIVERY_POINT_WITHOUT_CONTRACT"]
    assert coverage_anomalies == []


def test_two_uncovered_dps_two_anomalies(db):
    """2 DP actifs sans contrat → 2 anomalies (une par DP)."""
    site = _seed_site(db)
    db.add(
        DeliveryPoint(
            site_id=site.id,
            code="14000000000003",
            energy_type=DeliveryPointEnergyType.ELEC,
            status=DeliveryPointStatus.ACTIVE,
        )
    )
    db.add(
        DeliveryPoint(
            site_id=site.id,
            code="14000000000004",
            energy_type=DeliveryPointEnergyType.GAZ,
            status=DeliveryPointStatus.ACTIVE,
        )
    )
    db.commit()

    result = compute_site_anomalies(site.id, db)
    coverage_anomalies = [a for a in result["anomalies"] if a["code"] == "DELIVERY_POINT_WITHOUT_CONTRACT"]
    assert len(coverage_anomalies) == 2


def test_inactive_dp_does_not_raise_anomaly(db):
    """DP inactif (statut INACTIVE) → ne déclenche pas l'anomalie (seuls les actifs comptent)."""
    site = _seed_site(db)
    db.add(
        DeliveryPoint(
            site_id=site.id,
            code="14000000000005",
            energy_type=DeliveryPointEnergyType.ELEC,
            status=DeliveryPointStatus.INACTIVE,
        )
    )
    db.commit()

    result = compute_site_anomalies(site.id, db)
    coverage_anomalies = [a for a in result["anomalies"] if a["code"] == "DELIVERY_POINT_WITHOUT_CONTRACT"]
    assert coverage_anomalies == []


def test_archived_site_does_not_raise_anomaly(db):
    """Site archivé (actif=False) → règle skip (orphan rule s'en charge)."""
    site = _seed_site(db)
    db.add(
        DeliveryPoint(
            site_id=site.id,
            code="14000000000006",
            energy_type=DeliveryPointEnergyType.ELEC,
            status=DeliveryPointStatus.ACTIVE,
        )
    )
    site.actif = False
    db.commit()

    result = compute_site_anomalies(site.id, db)
    coverage_anomalies = [a for a in result["anomalies"] if a["code"] == "DELIVERY_POINT_WITHOUT_CONTRACT"]
    assert coverage_anomalies == []
