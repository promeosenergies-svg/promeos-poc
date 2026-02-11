"""
PROMEOS — Bill Intelligence Seed Demo
3 good invoices + 2 bad (anomalous) invoices.
"""
from datetime import date
from sqlalchemy.orm import Session

from models import (
    Site, EnergyContract, EnergyInvoice, EnergyInvoiceLine,
    BillingEnergyType, InvoiceLineType, BillingInvoiceStatus,
)


def seed_billing_demo(db: Session) -> dict:
    """
    Seed 2 contracts + 5 invoices (3 clean, 2 anomalous) for existing sites.
    Returns summary.
    """
    # Get first 3 sites
    sites = db.query(Site).limit(3).all()
    if len(sites) < 2:
        return {"error": "Need at least 2 sites to seed billing demo"}

    site_a = sites[0]  # Main site
    site_b = sites[1]  # Secondary site

    # ── Contract 1: elec for site_a ──
    contract_elec = EnergyContract(
        site_id=site_a.id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF Entreprises",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        price_ref_eur_per_kwh=0.18,
        fixed_fee_eur_per_month=45.0,
    )
    db.add(contract_elec)

    # ── Contract 2: gaz for site_b ──
    contract_gaz = EnergyContract(
        site_id=site_b.id,
        energy_type=BillingEnergyType.GAZ,
        supplier_name="Engie Pro",
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
        price_ref_eur_per_kwh=0.09,
        fixed_fee_eur_per_month=30.0,
    )
    db.add(contract_gaz)
    db.flush()

    invoices_created = []

    # ── Invoice 1: GOOD — site_a elec jan 2025 ──
    inv1 = EnergyInvoice(
        site_id=site_a.id,
        contract_id=contract_elec.id,
        invoice_number="EDF-2025-001",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        issue_date=date(2025, 2, 5),
        total_eur=1620.00,
        energy_kwh=9000,
        status=BillingInvoiceStatus.IMPORTED,
        source="seed",
    )
    db.add(inv1)
    db.flush()
    # Lines
    for lt, label, qty, unit, up, amt in [
        (InvoiceLineType.ENERGY, "Consommation HP", 5400, "kWh", 0.20, 1080.00),
        (InvoiceLineType.ENERGY, "Consommation HC", 3600, "kWh", 0.14, 504.00),
        (InvoiceLineType.TAX, "CSPE + ACCISE", None, None, None, 36.00),
    ]:
        db.add(EnergyInvoiceLine(
            invoice_id=inv1.id, line_type=lt, label=label,
            qty=qty, unit=unit, unit_price=up, amount_eur=amt,
        ))
    invoices_created.append(inv1)

    # ── Invoice 2: GOOD — site_a elec feb 2025 ──
    inv2 = EnergyInvoice(
        site_id=site_a.id,
        contract_id=contract_elec.id,
        invoice_number="EDF-2025-002",
        period_start=date(2025, 2, 1),
        period_end=date(2025, 2, 28),
        issue_date=date(2025, 3, 5),
        total_eur=1530.00,
        energy_kwh=8500,
        status=BillingInvoiceStatus.IMPORTED,
        source="seed",
    )
    db.add(inv2)
    db.flush()
    for lt, label, qty, unit, up, amt in [
        (InvoiceLineType.ENERGY, "Consommation HP", 5100, "kWh", 0.20, 1020.00),
        (InvoiceLineType.ENERGY, "Consommation HC", 3400, "kWh", 0.14, 476.00),
        (InvoiceLineType.TAX, "CSPE + ACCISE", None, None, None, 34.00),
    ]:
        db.add(EnergyInvoiceLine(
            invoice_id=inv2.id, line_type=lt, label=label,
            qty=qty, unit=unit, unit_price=up, amount_eur=amt,
        ))
    invoices_created.append(inv2)

    # ── Invoice 3: GOOD — site_b gaz jan 2025 ──
    inv3 = EnergyInvoice(
        site_id=site_b.id,
        contract_id=contract_gaz.id,
        invoice_number="ENGIE-2025-001",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        issue_date=date(2025, 2, 10),
        total_eur=540.00,
        energy_kwh=6000,
        status=BillingInvoiceStatus.IMPORTED,
        source="seed",
    )
    db.add(inv3)
    db.flush()
    for lt, label, qty, unit, up, amt in [
        (InvoiceLineType.ENERGY, "Terme variable gaz", 6000, "kWh", 0.08, 480.00),
        (InvoiceLineType.NETWORK, "Abonnement distribution", 1, "mois", 30.0, 30.00),
        (InvoiceLineType.TAX, "TICGN", None, None, None, 30.00),
    ]:
        db.add(EnergyInvoiceLine(
            invoice_id=inv3.id, line_type=lt, label=label,
            qty=qty, unit=unit, unit_price=up, amount_eur=amt,
        ))
    invoices_created.append(inv3)

    # ── Invoice 4: BAD — site_a elec overcharge (shadow gap > 20%) ──
    inv4 = EnergyInvoice(
        site_id=site_a.id,
        contract_id=contract_elec.id,
        invoice_number="EDF-2025-003",
        period_start=date(2025, 3, 1),
        period_end=date(2025, 3, 31),
        issue_date=date(2025, 4, 5),
        total_eur=2800.00,  # Should be ~1620 for 9000 kWh → overcharge
        energy_kwh=9000,
        status=BillingInvoiceStatus.IMPORTED,
        source="seed",
    )
    db.add(inv4)
    db.flush()
    # Lines don't match total (lines_sum_mismatch)
    for lt, label, qty, unit, up, amt in [
        (InvoiceLineType.ENERGY, "Consommation HP", 5400, "kWh", 0.20, 1080.00),
        (InvoiceLineType.ENERGY, "Consommation HC", 3600, "kWh", 0.14, 504.00),
        (InvoiceLineType.OTHER, "Frais supplementaires", None, None, None, 800.00),
        (InvoiceLineType.TAX, "CSPE + ACCISE", None, None, None, 36.00),
    ]:
        db.add(EnergyInvoiceLine(
            invoice_id=inv4.id, line_type=lt, label=label,
            qty=qty, unit=unit, unit_price=up, amount_eur=amt,
        ))
    invoices_created.append(inv4)

    # ── Invoice 5: BAD — site_b gaz consumption spike + period too long ──
    inv5 = EnergyInvoice(
        site_id=site_b.id,
        contract_id=contract_gaz.id,
        invoice_number="ENGIE-2025-002",
        period_start=date(2025, 2, 1),
        period_end=date(2025, 5, 30),  # 119 days — period_too_long
        issue_date=date(2025, 6, 10),
        total_eur=2700.00,
        energy_kwh=30000,  # 5x normal → consumption_spike
        status=BillingInvoiceStatus.IMPORTED,
        source="seed",
    )
    db.add(inv5)
    db.flush()
    for lt, label, qty, unit, up, amt in [
        (InvoiceLineType.ENERGY, "Terme variable gaz", 30000, "kWh", 0.08, 2400.00),
        (InvoiceLineType.NETWORK, "Abonnement distribution", 4, "mois", 30.0, 120.00),
        (InvoiceLineType.TAX, "TICGN", None, None, None, 180.00),
    ]:
        db.add(EnergyInvoiceLine(
            invoice_id=inv5.id, line_type=lt, label=label,
            qty=qty, unit=unit, unit_price=up, amount_eur=amt,
        ))
    invoices_created.append(inv5)

    db.commit()

    return {
        "contracts_created": 2,
        "invoices_created": len(invoices_created),
        "good_invoices": 3,
        "bad_invoices": 2,
        "sites_used": [site_a.id, site_b.id],
    }
