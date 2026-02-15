"""
PROMEOS - Demo Seed: Billing Generator
Creates contracts, invoices, invoice lines, and billing insights.
"""
import json
import random
from datetime import date, datetime, timedelta

from models import (
    EnergyContract, EnergyInvoice, EnergyInvoiceLine, BillingInsight,
    BillingEnergyType, InvoiceLineType, BillingInvoiceStatus, InsightStatus,
)


_SUPPLIERS = ["EDF", "Engie", "TotalEnergies", "Eni", "Vattenfall"]


def generate_billing(db, org, sites: list, invoices_count: int,
                     rng: random.Random) -> dict:
    """Generate contracts + invoices + lines + insights."""
    contracts_created = 0
    invoices_created = 0
    lines_created = 0
    insights_created = 0

    # Create 1 contract per site (electricity)
    contract_map = {}  # site_id → contract
    for site in sites:
        supplier = _SUPPLIERS[rng.randint(0, len(_SUPPLIERS) - 1)]
        price = round(rng.uniform(0.10, 0.25), 4)
        contract = EnergyContract(
            site_id=site.id, energy_type=BillingEnergyType.ELEC,
            supplier_name=supplier,
            start_date=date(2024, 1, 1),
            end_date=date(2026, 12, 31),
            price_ref_eur_per_kwh=price,
            fixed_fee_eur_per_month=round(rng.uniform(20, 200), 2),
            notice_period_days=90, auto_renew=rng.choice([True, False]),
        )
        db.add(contract)
        db.flush()
        contract_map[site.id] = contract
        contracts_created += 1

    # Generate invoices — spread across sites
    sites_for_inv = rng.sample(sites, min(invoices_count, len(sites)))
    for inv_idx in range(invoices_count):
        site = sites_for_inv[inv_idx % len(sites_for_inv)]
        contract = contract_map.get(site.id)
        if not contract:
            continue

        # Period: rolling monthly invoices
        month_offset = inv_idx % 12
        period_start = date(2025, max(1, 12 - month_offset), 1)
        if period_start.month == 12:
            period_end = date(2026, 1, 1) - timedelta(days=1)
        else:
            period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)

        # Realistic energy
        annual = site.annual_kwh_total or 500000
        monthly_kwh = round(annual / 12 * rng.uniform(0.8, 1.2), 0)
        price = contract.price_ref_eur_per_kwh or 0.15
        energy_eur = round(monthly_kwh * price, 2)
        network_eur = round(monthly_kwh * rng.uniform(0.03, 0.06), 2)
        tax_eur = round((energy_eur + network_eur) * rng.uniform(0.15, 0.25), 2)
        total = round(energy_eur + network_eur + tax_eur + (contract.fixed_fee_eur_per_month or 0), 2)

        # Anomaly: 1 in 5 invoices has an overcharge
        is_anomaly = inv_idx % 5 == 3
        if is_anomaly:
            total = round(total * rng.uniform(1.15, 1.40), 2)

        invoice = EnergyInvoice(
            site_id=site.id, contract_id=contract.id,
            invoice_number=f"INV-{site.id:04d}-{period_start.strftime('%Y%m')}",
            period_start=period_start, period_end=period_end,
            issue_date=period_end + timedelta(days=rng.randint(5, 20)),
            total_eur=total, energy_kwh=monthly_kwh,
            status=BillingInvoiceStatus.ANOMALY if is_anomaly else BillingInvoiceStatus.VALIDATED,
            source="demo_seed",
        )
        db.add(invoice)
        db.flush()
        invoices_created += 1

        # Invoice lines
        for lt, label, amount in [
            (InvoiceLineType.ENERGY, "Fourniture electricite", energy_eur),
            (InvoiceLineType.NETWORK, "Acheminement (TURPE)", network_eur),
            (InvoiceLineType.TAX, "Taxes et contributions", tax_eur),
            (InvoiceLineType.OTHER, "Abonnement mensuel", contract.fixed_fee_eur_per_month or 0),
        ]:
            db.add(EnergyInvoiceLine(
                invoice_id=invoice.id, line_type=lt,
                label=label, amount_eur=amount,
                qty=monthly_kwh if lt == InvoiceLineType.ENERGY else None,
                unit="kWh" if lt == InvoiceLineType.ENERGY else None,
                unit_price=price if lt == InvoiceLineType.ENERGY else None,
            ))
            lines_created += 1

        # Billing insight for anomalous invoices
        if is_anomaly:
            db.add(BillingInsight(
                site_id=site.id, invoice_id=invoice.id,
                type="overcharge", severity="high",
                message=f"Surfacturation detectee sur la facture {invoice.invoice_number}: "
                        f"ecart de {((total / (energy_eur + network_eur + tax_eur + (contract.fixed_fee_eur_per_month or 0))) - 1) * 100:.0f}%.",
                estimated_loss_eur=round(total * 0.15, 2),
                insight_status=InsightStatus.OPEN,
            ))
            insights_created += 1

    db.flush()

    return {
        "contracts_count": contracts_created,
        "invoices_count": invoices_created,
        "lines_count": lines_created,
        "insights_count": insights_created,
    }
