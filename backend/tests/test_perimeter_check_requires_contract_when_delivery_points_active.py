"""
PROMEOS — P0-C 2026-05-23 : renforcement `perimeter_check.check_perimeter`.

Vérifie qu'une facture sans `contract_id` ne peut pas être considérée fiable
si le site a au moins un point de livraison actif. Avant ce fix, le contract
check était conditionnel (`if contract_id`) et silencieusement contourné.

Message FR canonique : "Impossible de fiabiliser cette facture : aucun
contrat n'est rattaché au point de livraison."
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
from services.perimeter_check import (  # noqa: E402
    ERROR_CODE_MISSING_CONTRACT,
    ERROR_MESSAGE_MISSING_CONTRACT_FR,
    check_perimeter,
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
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def _seed_site(db, *, with_active_dp=True, with_contract=False):
    org = Organisation(nom="Org P", siren="111111111", type_client="bureau", actif=True)
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
        nom="Site Perim",
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        surface_m2=1000,
        actif=True,
    )
    db.add(site)
    db.flush()
    dp = None
    if with_active_dp:
        dp = DeliveryPoint(
            site_id=site.id,
            code="14000000000010",
            energy_type=DeliveryPointEnergyType.ELEC,
            status=DeliveryPointStatus.ACTIVE,
        )
        db.add(dp)
        db.flush()
    ct = None
    if with_contract:
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
        if dp:
            db.add(ContractDeliveryPoint(contract_id=ct.id, delivery_point_id=dp.id))
    db.commit()
    return site, dp, ct


def test_no_contract_id_with_active_dp_is_blocking(db):
    """Site avec DP actif et facture sans contract_id → blocking + error_code + message FR."""
    site, _, _ = _seed_site(db, with_active_dp=True, with_contract=False)
    result = check_perimeter(db, site_id=site.id, contract_id=None)
    assert result["consistent"] is False
    assert result["blocking"] is True
    assert result["error_code"] == ERROR_CODE_MISSING_CONTRACT
    assert ERROR_MESSAGE_MISSING_CONTRACT_FR in result["warnings"]


def test_no_contract_id_without_active_dp_is_tolerated(db):
    """Site sans DP actif et facture sans contract_id → tolérée (rien à fiabiliser côté DP)."""
    site, _, _ = _seed_site(db, with_active_dp=False, with_contract=False)
    result = check_perimeter(db, site_id=site.id, contract_id=None)
    assert result["consistent"] is True
    assert result["blocking"] is False
    assert result["error_code"] is None


def test_contract_id_provided_for_site_with_active_dp_passes(db):
    """Site avec DP actif et facture avec contract_id valide → OK."""
    site, _, ct = _seed_site(db, with_active_dp=True, with_contract=True)
    result = check_perimeter(db, site_id=site.id, contract_id=ct.id)
    assert result["consistent"] is True
    assert result["error_code"] is None
    assert result["contract_exists"] is True
    assert result["contract_matches_site"] is True


def test_inexistent_contract_id_still_returns_consistent_false(db):
    """Si on fournit un contract_id qui n'existe pas → consistent=False (comportement existant)."""
    site, _, _ = _seed_site(db, with_active_dp=True, with_contract=False)
    result = check_perimeter(db, site_id=site.id, contract_id=99999)
    assert result["consistent"] is False
    assert "Contrat inexistant" in result["warnings"]


def test_inexistent_site_returns_consistent_false(db):
    """Site_id inconnu → consistent=False."""
    result = check_perimeter(db, site_id=99999, contract_id=None)
    assert result["consistent"] is False
    assert result["site_exists"] is False


def test_french_error_message_explicit(db):
    """Le message d'erreur P0-C est en FR et explicite (anti-jargon)."""
    site, _, _ = _seed_site(db, with_active_dp=True, with_contract=False)
    result = check_perimeter(db, site_id=site.id, contract_id=None)
    msg = " ".join(result["warnings"])
    assert "fiabiliser" in msg
    assert "contrat" in msg.lower()
    assert "point de livraison" in msg.lower()
    # Pas d'anglais résiduel
    for english_word in ("delivery", "contract", "missing", "billing"):
        assert english_word.lower() not in msg.lower()
