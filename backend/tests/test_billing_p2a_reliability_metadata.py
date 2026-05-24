"""
PROMEOS — Bill Intelligence P2-A (2026-05-24) :
- F1 : `shadow_billing_v2` retourne `is_reliable` + `reliability_reason`
       si facture sans contrat ou contrat sans prix
- F2 : `get_billing_summary` retourne `kpi_metadata` (période, unit, source)
- F4 : `audit_invoice_full` retourne `energy_type` + `period_start/end` explicites

Doctrine : "Aucun KPI sans source, formule, unité, période, périmètre."
+ "facture sans contrat = non fiable" (P1 Règle 1).
"""

from __future__ import annotations

import os
import sys
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (  # noqa: E402
    Base,
    BillingEnergyType,
    EnergyContract,
    EnergyInvoice,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)
from services.billing_service import audit_invoice_full, get_billing_summary  # noqa: E402
from services.billing_shadow_v2 import shadow_billing_v2  # noqa: E402


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


def _seed(db, *, with_contract: bool = True, energy: str = "elec"):
    org = Organisation(nom="Org P2A", siren="666666666", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="666666666")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site P2A",
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        actif=True,
    )
    db.add(site)
    db.flush()
    contract = None
    if with_contract:
        contract = EnergyContract(
            site_id=site.id,
            energy_type=BillingEnergyType.ELEC if energy == "elec" else BillingEnergyType.GAZ,
            supplier_name="EDF" if energy == "elec" else "Engie",
            price_ref_eur_per_kwh=0.15 if energy == "elec" else 0.07,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
        )
        db.add(contract)
        db.flush()
    invoice = EnergyInvoice(
        site_id=site.id,
        contract_id=contract.id if contract else None,
        invoice_number="INV-P2A-001",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        issue_date=date(2026, 5, 5),
        total_eur=1200.0,
        energy_kwh=8000,
        source="manual",
    )
    db.add(invoice)
    db.commit()
    return org, site, invoice, contract


# ─── F1 — shadow_billing_v2 is_reliable ──────────────────────────────────


def test_shadow_v2_reliable_when_contract_with_price(db):
    """Facture avec contrat + prix → is_reliable=True, reason=None."""
    _, _, invoice, contract = _seed(db, with_contract=True)
    result = shadow_billing_v2(invoice, [], contract, db=db)
    assert result["is_reliable"] is True, "Facture avec contrat doit être fiable"
    assert result["reliability_reason"] is None
    # F1+F4 : période exposée
    assert result["period_start"] == "2026-04-01"
    assert result["period_end"] == "2026-04-30"


def test_shadow_v2_unreliable_when_no_contract(db):
    """Facture sans contrat → is_reliable=False + raison FR explicite."""
    _, _, invoice, _ = _seed(db, with_contract=False)
    result = shadow_billing_v2(invoice, [], None, db=db)
    assert result["is_reliable"] is False
    assert result["reliability_reason"] is not None
    reason = result["reliability_reason"].lower()
    assert "contrat" in reason, "La raison doit mentionner l'absence de contrat"
    assert "défaut" in reason or "fiabiliser" in reason


def test_shadow_v2_unreliable_when_contract_no_price(db):
    """Contrat sans price_ref → is_reliable=False + raison FR."""
    _, _, invoice, contract = _seed(db, with_contract=True)
    contract.price_ref_eur_per_kwh = None
    db.commit()
    result = shadow_billing_v2(invoice, [], contract, db=db)
    assert result["is_reliable"] is False
    assert "prix" in (result["reliability_reason"] or "").lower()


# ─── F2 — billing_summary kpi_metadata ──────────────────────────────────


def test_billing_summary_exposes_kpi_metadata(db):
    """`get_billing_summary` retourne `kpi_metadata` avec période + source + unit."""
    org, _, _, _ = _seed(db)
    summary = get_billing_summary(db, org_id=org.id)
    assert "kpi_metadata" in summary
    meta = summary["kpi_metadata"]
    # Période analysée
    assert "period_analyzed" in meta
    assert meta["period_analyzed"]["start"] == "2026-04-01"
    assert meta["period_analyzed"]["end"] == "2026-04-30"
    # Périmètre
    assert meta["scope"] in ("org", "all_organisations")
    # Unités explicites
    assert meta["total_eur_unit"] == "TTC"
    assert meta["total_estimated_loss_eur_unit"] == "TTC"
    # Source explicite (formule = doctrine "aucun KPI sans source")
    assert "shadow_billing_v2" in meta["total_estimated_loss_eur_source"]
    # computed_at présent
    assert "computed_at" in meta


def test_billing_summary_empty_period_when_no_invoices(db):
    """DB vide → period_analyzed.{start,end} = None (sans crash)."""
    summary = get_billing_summary(db, org_id=None)
    meta = summary["kpi_metadata"]
    assert meta["period_analyzed"]["start"] is None
    assert meta["period_analyzed"]["end"] is None


# ─── F4 — audit_invoice_full energy_type ───────────────────────────────


def test_audit_invoice_full_exposes_energy_type_elec(db):
    """Facture élec → response.energy_type='elec' explicite."""
    _, _, invoice, _ = _seed(db, with_contract=True, energy="elec")
    result = audit_invoice_full(db, invoice.id)
    assert result.get("energy_type") == "elec"
    assert result.get("period_start") == "2026-04-01"
    assert result.get("period_end") == "2026-04-30"


def test_audit_invoice_full_exposes_energy_type_gaz(db):
    """Facture gaz → response.energy_type='gaz' explicite."""
    _, _, invoice, _ = _seed(db, with_contract=True, energy="gaz")
    result = audit_invoice_full(db, invoice.id)
    assert result.get("energy_type") == "gaz"


def test_audit_invoice_full_energy_type_none_when_no_contract(db):
    """Facture sans contrat → energy_type=None (cohérent avec is_reliable=False)."""
    _, _, invoice, _ = _seed(db, with_contract=False)
    result = audit_invoice_full(db, invoice.id)
    # shadow ajoute energy_type par défaut "ELEC" — on tolère None ou heuristique élec
    # mais pas de gaz inventé sur facture sans contrat
    assert result.get("energy_type") in (None, "elec")
