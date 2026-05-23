"""
PROMEOS — P0-C 2026-05-23 : tests `contract_coverage_service`.

Vérifie les 5 status cardinaux + ready_for_billing/purchase + actions FR +
isolation multi-org + libellés "Point de livraison <énergie> — PRM/PDL/PCE".
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
from services.contract_coverage_service import (  # noqa: E402
    COVERAGE_CONTRAT_EXPIRE,
    COVERAGE_CONTRAT_INCOHERENT,
    COVERAGE_CONTRAT_MANQUANT,
    COVERAGE_CONTRAT_PARTIEL,
    COVERAGE_CONTRAT_RATTACHE,
    compute_site_contract_coverage,
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


def _make_site(db, *, siren="111111111", site_nom="Site Cov"):
    org = Organisation(nom="Org Cov", siren=siren, type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren=siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom=site_nom,
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        surface_m2=1000,
        actif=True,
    )
    db.add(site)
    db.flush()
    return org, site


def _make_dp(db, site, *, code, energy: DeliveryPointEnergyType, status=DeliveryPointStatus.ACTIVE):
    dp = DeliveryPoint(site_id=site.id, code=code, energy_type=energy, status=status)
    db.add(dp)
    db.flush()
    return dp


def _make_contract(
    db,
    site,
    *,
    energy: BillingEnergyType,
    supplier="EDF",
    start: date | None = None,
    end: date | None = None,
    dps=None,
):
    today = date.today()
    ct = EnergyContract(
        site_id=site.id,
        energy_type=energy,
        supplier_name=supplier,
        start_date=start or (today - timedelta(days=30)),
        end_date=end or (today + timedelta(days=365)),
    )
    db.add(ct)
    db.flush()
    for dp in dps or []:
        link = ContractDeliveryPoint(contract_id=ct.id, delivery_point_id=dp.id)
        db.add(link)
    db.flush()
    db.refresh(ct)
    return ct


# ─── 1. contrat_rattache — couverture parfaite ──────────────────────────────


def test_two_dp_two_contracts_coverage_complete(db):
    """Site avec 2 DP actifs + 2 contrats actifs couvrant → contrat_rattache."""
    org, site = _make_site(db)
    dp_elec = _make_dp(db, site, code="14111111111111", energy=DeliveryPointEnergyType.ELEC)
    dp_gaz = _make_dp(db, site, code="14222222222222", energy=DeliveryPointEnergyType.GAZ)
    _make_contract(db, site, energy=BillingEnergyType.ELEC, dps=[dp_elec])
    _make_contract(db, site, energy=BillingEnergyType.GAZ, dps=[dp_gaz])
    db.commit()

    cov = compute_site_contract_coverage(db, site_id=site.id, org_id=org.id)
    assert cov.status == COVERAGE_CONTRAT_RATTACHE
    assert cov.ready_for_billing is True
    assert cov.ready_for_purchase is True
    assert len(cov.delivery_points_active) == 2
    assert len(cov.contracts_active) == 2
    assert cov.uncovered_delivery_points == []
    assert cov.actions == []


# ─── 2. contrat_partiel — un PCE actif sans contrat ─────────────────────────


def test_partial_coverage_missing_gas_contract(db):
    """Site avec 2 DP (élec + gaz) mais contrat seulement sur l'élec → contrat_partiel."""
    org, site = _make_site(db)
    dp_elec = _make_dp(db, site, code="14111111111111", energy=DeliveryPointEnergyType.ELEC)
    dp_gaz = _make_dp(db, site, code="14222222222222", energy=DeliveryPointEnergyType.GAZ)
    _make_contract(db, site, energy=BillingEnergyType.ELEC, dps=[dp_elec])
    db.commit()

    cov = compute_site_contract_coverage(db, site_id=site.id, org_id=org.id)
    assert cov.status == COVERAGE_CONTRAT_PARTIEL
    assert cov.ready_for_billing is False
    assert len(cov.uncovered_delivery_points) == 1
    assert cov.uncovered_delivery_points[0].id == dp_gaz.id
    # Action FR cardinale
    assert any(a.code == "ATTACH_CONTRACT" for a in cov.actions)
    assert any("Rattacher un contrat" in a.label_fr for a in cov.actions)


# ─── 3. contrat_manquant — aucun contrat actif ──────────────────────────────


def test_no_contract_at_all(db):
    """Site avec DP actif et aucun contrat → contrat_manquant."""
    org, site = _make_site(db)
    _make_dp(db, site, code="14111111111111", energy=DeliveryPointEnergyType.ELEC)
    db.commit()

    cov = compute_site_contract_coverage(db, site_id=site.id, org_id=org.id)
    assert cov.status == COVERAGE_CONTRAT_MANQUANT
    assert cov.ready_for_billing is False


# ─── 4. contrat_expire — tous les contrats expirés ──────────────────────────


def test_all_contracts_expired(db):
    """Site avec DP actif et seulement des contrats expirés → contrat_expire."""
    org, site = _make_site(db)
    dp = _make_dp(db, site, code="14111111111111", energy=DeliveryPointEnergyType.ELEC)
    today = date.today()
    _make_contract(
        db,
        site,
        energy=BillingEnergyType.ELEC,
        start=today - timedelta(days=400),
        end=today - timedelta(days=30),
        dps=[dp],
    )
    db.commit()

    cov = compute_site_contract_coverage(db, site_id=site.id, org_id=org.id)
    assert cov.status == COVERAGE_CONTRAT_EXPIRE
    assert cov.ready_for_billing is False
    assert len(cov.expired_contracts) == 1
    assert any(a.code == "RENEW_CONTRACT" for a in cov.actions)


# ─── 5. contrat_incoherent — mismatch énergie ───────────────────────────────


def test_energy_mismatch_elec_contract_on_gas_dp(db):
    """Contrat électricité rattaché à PCE gaz → contrat_incoherent."""
    org, site = _make_site(db)
    dp_gaz = _make_dp(db, site, code="14222222222222", energy=DeliveryPointEnergyType.GAZ)
    _make_contract(db, site, energy=BillingEnergyType.ELEC, dps=[dp_gaz])
    db.commit()

    cov = compute_site_contract_coverage(db, site_id=site.id, org_id=org.id)
    assert cov.status == COVERAGE_CONTRAT_INCOHERENT
    assert cov.ready_for_billing is False
    assert len(cov.energy_mismatches) == 1
    assert any(a.code == "FIX_ENERGY_MISMATCH" for a in cov.actions)


# ─── 6. contrat_incoherent — contrat lié à un DP hors site ─────────────────


def test_contract_linked_to_foreign_delivery_point(db):
    """Contrat du site liant un DP qui n'appartient pas au site → contrat_incoherent."""
    org, site_a = _make_site(db, siren="111111111", site_nom="Site A")
    _, site_b = _make_site(db, siren="222222222", site_nom="Site B")
    dp_b = _make_dp(db, site_b, code="14333333333333", energy=DeliveryPointEnergyType.ELEC)
    _make_dp(db, site_a, code="14111111111111", energy=DeliveryPointEnergyType.ELEC)
    # Contrat du site A rattaché au DP du site B (anomalie)
    _make_contract(db, site_a, energy=BillingEnergyType.ELEC, dps=[dp_b])
    db.commit()

    cov = compute_site_contract_coverage(db, site_id=site_a.id, org_id=org.id)
    assert cov.status == COVERAGE_CONTRAT_INCOHERENT
    assert len(cov.foreign_delivery_point_links) == 1
    assert any(a.code == "DETACH_FOREIGN_DP" for a in cov.actions)


# ─── 7. Multi-org : impossible de voir le contrat d'une autre organisation ─


def test_multi_org_isolation(db):
    """Le calcul ne retourne que les contrats du site_id (donc de l'org propriétaire)."""
    org_a, site_a = _make_site(db, siren="111111111", site_nom="Site Org A")
    _, site_b = _make_site(db, siren="222222222", site_nom="Site Org B")
    dp_a = _make_dp(db, site_a, code="14111111111111", energy=DeliveryPointEnergyType.ELEC)
    dp_b = _make_dp(db, site_b, code="14222222222222", energy=DeliveryPointEnergyType.ELEC)
    _make_contract(db, site_a, energy=BillingEnergyType.ELEC, supplier="EDF A", dps=[dp_a])
    _make_contract(db, site_b, energy=BillingEnergyType.ELEC, supplier="EDF B", dps=[dp_b])
    db.commit()

    cov_a = compute_site_contract_coverage(db, site_id=site_a.id, org_id=org_a.id)
    cov_b = compute_site_contract_coverage(db, site_id=site_b.id, org_id=999)
    assert len(cov_a.contracts_active) == 1
    assert cov_a.contracts_active[0].supplier_name == "EDF A"
    assert len(cov_b.contracts_active) == 1
    assert cov_b.contracts_active[0].supplier_name == "EDF B"
    # Aucun mélange de contrats cross-sites
    a_dp_ids = {d.id for d in cov_a.delivery_points_active}
    assert dp_b.id not in a_dp_ids


# ─── 8. Libellés FR P0-C "Point de livraison <énergie> — PRM/PDL/PCE" ──────


def test_delivery_point_label_french_elec(db):
    """Libellé canonique élec : 'Point de livraison électricité — PRM/PDL <code>'."""
    org, site = _make_site(db)
    _make_dp(db, site, code="14010101010101", energy=DeliveryPointEnergyType.ELEC)
    db.commit()
    cov = compute_site_contract_coverage(db, site_id=site.id, org_id=org.id)
    assert len(cov.delivery_points_active) == 1
    assert cov.delivery_points_active[0].label_fr == "Point de livraison électricité — PRM/PDL 14010101010101"


def test_delivery_point_label_french_gas(db):
    """Libellé canonique gaz : 'Point de livraison gaz — PCE <code>'."""
    org, site = _make_site(db)
    _make_dp(db, site, code="GI222222", energy=DeliveryPointEnergyType.GAZ)
    db.commit()
    cov = compute_site_contract_coverage(db, site_id=site.id, org_id=org.id)
    assert cov.delivery_points_active[0].label_fr == "Point de livraison gaz — PCE GI222222"


# ─── 9. Site inexistant → status manquant, listes vides ─────────────────────


def test_unknown_site_returns_empty_coverage(db):
    """Site_id inexistant → status contrat_manquant + ready=False."""
    cov = compute_site_contract_coverage(db, site_id=9999, org_id=1)
    assert cov.status == COVERAGE_CONTRAT_MANQUANT
    assert cov.ready_for_billing is False
    assert cov.delivery_points_active == []
    assert cov.contracts_active == []


# ─── 10. Site sans DP du tout → contrat_rattache (rien à couvrir) ──────────


def test_site_without_delivery_points(db):
    """Site sans aucun DP → contrat_rattache (vacuously true) mais ready_for_purchase=False."""
    org, site = _make_site(db)
    db.commit()
    cov = compute_site_contract_coverage(db, site_id=site.id, org_id=org.id)
    assert cov.status == COVERAGE_CONTRAT_RATTACHE
    assert cov.ready_for_purchase is False  # pas de DP = pas de purchase


# ─── 11. to_dict() sérialisable JSON ─────────────────────────────────────────


def test_to_dict_serializable(db):
    """La sortie to_dict doit être sérialisable JSON (clés FR + status)."""
    import json

    org, site = _make_site(db)
    dp = _make_dp(db, site, code="14111111111111", energy=DeliveryPointEnergyType.ELEC)
    _make_contract(db, site, energy=BillingEnergyType.ELEC, dps=[dp])
    db.commit()
    cov = compute_site_contract_coverage(db, site_id=site.id, org_id=org.id)
    payload = cov.to_dict()
    json_str = json.dumps(payload)
    parsed = json.loads(json_str)
    assert parsed["status"] in {
        "contrat_rattache",
        "contrat_partiel",
        "contrat_manquant",
        "contrat_expire",
        "contrat_incoherent",
    }
    assert "delivery_points_active" in parsed
    assert "contracts_active" in parsed
    assert "ready_for_billing" in parsed
    assert "actions" in parsed
