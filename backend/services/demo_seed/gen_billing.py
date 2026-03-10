"""
PROMEOS - Demo Seed: Billing Generator
Creates contracts, invoices, invoice lines, and billing insights.
"""

import json
import random
from datetime import date, datetime, timedelta

from models import (
    EnergyContract,
    EnergyInvoice,
    EnergyInvoiceLine,
    BillingInsight,
    BillingEnergyType,
    InvoiceLineType,
    BillingInvoiceStatus,
    InsightStatus,
    ContractIndexation,
)


_SUPPLIERS = ["EDF", "Engie", "TotalEnergies", "Eni", "Vattenfall"]


def generate_billing(db, org, sites: list, invoices_count: int, rng: random.Random, pack_def: dict = None) -> dict:
    """Generate contracts + invoices + lines + insights."""
    contracts_created = 0
    invoices_created = 0
    lines_created = 0
    insights_created = 0

    _ENERGY_TYPE_MAP = {"elec": BillingEnergyType.ELEC, "gaz": BillingEnergyType.GAZ}

    contract_map = {}  # site_id → contract (first per site, for invoices)

    if pack_def and "contracts_spec" in pack_def:
        # ── Explicit contracts (helios) ──────────────────────────────
        _DYNAMIC_ENDS = {
            "EXPIRING_SOON": 60,
            "EXPIRING_30": 30,
            "EXPIRING_90": 90,
            "EXPIRING_180": 180,
        }
        _INDEXATION_MAP = {
            "fixe": ContractIndexation.FIXE,
            "indexe": ContractIndexation.INDEXE,
            "spot": ContractIndexation.SPOT,
            "hybride": ContractIndexation.HYBRIDE,
        }
        for c_spec in pack_def["contracts_spec"]:
            site = sites[c_spec["site_idx"]]
            end_str = c_spec["end"]
            if end_str in _DYNAMIC_ENDS:
                end_date_val = date.today() + timedelta(days=_DYNAMIC_ENDS[end_str])
            else:
                end_date_val = date.fromisoformat(end_str)

            strategy = c_spec.get("strategy", "fixe")
            contract = EnergyContract(
                site_id=site.id,
                energy_type=_ENERGY_TYPE_MAP.get(c_spec["type"], BillingEnergyType.ELEC),
                supplier_name=c_spec["supplier"],
                start_date=date.fromisoformat(c_spec["start"]),
                end_date=end_date_val,
                price_ref_eur_per_kwh=c_spec["price"],
                fixed_fee_eur_per_month=c_spec.get("fee", 50),
                notice_period_days=90,
                auto_renew=c_spec.get("auto_renew", False),
                offer_indexation=_INDEXATION_MAP.get(strategy),
                metadata_json=json.dumps({"strategy": strategy}),
            )
            db.add(contract)
            db.flush()
            # Keep first contract per site for invoice generation
            if site.id not in contract_map:
                contract_map[site.id] = contract
            contracts_created += 1
    else:
        # ── Randomized contracts (tertiaire) ────────────────
        for site in sites:
            supplier = _SUPPLIERS[rng.randint(0, len(_SUPPLIERS) - 1)]
            price = round(rng.uniform(0.10, 0.25), 4)
            contract = EnergyContract(
                site_id=site.id,
                energy_type=BillingEnergyType.ELEC,
                supplier_name=supplier,
                start_date=date(2024, 1, 1),
                end_date=date(2026, 12, 31),
                price_ref_eur_per_kwh=price,
                fixed_fee_eur_per_month=round(rng.uniform(20, 200), 2),
                notice_period_days=90,
                auto_renew=rng.choice([True, False]),
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

        inv_number = f"INV-{site.id:04d}-{period_start.strftime('%Y%m')}"

        # Skip if invoice already exists (avoid IntegrityError on re-seed)
        existing = (
            db.query(EnergyInvoice)
            .filter_by(site_id=site.id, invoice_number=inv_number, period_start=period_start, period_end=period_end)
            .first()
        )
        if existing:
            continue

        # Realistic energy — aligned with shadow billing rates to avoid false anomalies
        annual = site.annual_kwh_total or 500000
        monthly_kwh = round(annual / 12 * rng.uniform(0.8, 1.2), 0)
        price = contract.price_ref_eur_per_kwh or 0.15
        energy_eur = round(monthly_kwh * price, 2)
        # Use realistic TURPE/accise rates (aligned with shadow billing V2 expectations)
        turpe_rate = 0.0453  # TURPE C5 BT
        accise_rate = 0.0225  # Accise ELEC (TIEE)
        # Add small variance ±8% to look realistic without triggering 20% shadow_gap
        network_eur = round(monthly_kwh * turpe_rate * rng.uniform(0.92, 1.08), 2)
        tax_eur = round(monthly_kwh * accise_rate * rng.uniform(0.92, 1.08), 2)
        abo_eur = contract.fixed_fee_eur_per_month or 0
        # TTC = HT components + TVA (20% on energy/network/taxes, 5.5% on abonnement)
        ht = energy_eur + network_eur + tax_eur + abo_eur
        tva = round((energy_eur + network_eur + tax_eur) * 0.20 + abo_eur * 0.055, 2)
        total = round(ht + tva, 2)

        # Anomaly: 1 in 5 invoices — varied types
        is_anomaly = inv_idx % 5 == 3
        anomaly_type = None
        if is_anomaly:
            anomaly_type = rng.choice(["overcharge", "volume_spike", "network_drift", "tax_mismatch"])
            if anomaly_type == "overcharge":
                total = round(total * rng.uniform(1.25, 1.45), 2)
            elif anomaly_type == "volume_spike":
                total = round(total * rng.uniform(1.30, 1.55), 2)
            elif anomaly_type == "network_drift":
                network_eur = round(network_eur * rng.uniform(1.35, 1.65), 2)
                total = round(energy_eur + network_eur + tax_eur + abo_eur, 2)
            elif anomaly_type == "tax_mismatch":
                tax_eur = round(tax_eur * rng.uniform(1.30, 1.55), 2)
                total = round(energy_eur + network_eur + tax_eur + abo_eur, 2)

        invoice = EnergyInvoice(
            site_id=site.id,
            contract_id=contract.id,
            invoice_number=inv_number,
            period_start=period_start,
            period_end=period_end,
            issue_date=period_end + timedelta(days=rng.randint(5, 20)),
            total_eur=total,
            energy_kwh=monthly_kwh,
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
            db.add(
                EnergyInvoiceLine(
                    invoice_id=invoice.id,
                    line_type=lt,
                    label=label,
                    amount_eur=amount,
                    qty=monthly_kwh if lt == InvoiceLineType.ENERGY else None,
                    unit="kWh" if lt == InvoiceLineType.ENERGY else None,
                    unit_price=price if lt == InvoiceLineType.ENERGY else None,
                )
            )
            lines_created += 1

        # Billing insight for anomalous invoices — varied messages
        if is_anomaly and anomaly_type:
            _ANOMALY_TEMPLATES = {
                "overcharge": {
                    "type": "overcharge",
                    "severity": "high",
                    "msg": f"Surfacturation detectee sur {invoice.invoice_number}: montant TTC superieur de "
                    f"{rng.randint(15, 35)}% au prix contractuel.",
                },
                "volume_spike": {
                    "type": "volume_spike",
                    "severity": "medium",
                    "msg": f"Pic de consommation anormal sur {invoice.invoice_number}: volume facture "
                    f"{monthly_kwh:.0f} kWh vs moyenne attendue {annual / 12:.0f} kWh (+{rng.randint(20, 45)}%).",
                },
                "network_drift": {
                    "type": "network_drift",
                    "severity": "medium",
                    "msg": f"Derive reseau (TURPE) sur {invoice.invoice_number}: cout acheminement "
                    f"{network_eur:.0f} EUR, soit +{rng.randint(30, 55)}% vs reference tarifaire.",
                },
                "tax_mismatch": {
                    "type": "tax_mismatch",
                    "severity": "low",
                    "msg": f"Ecart taxes sur {invoice.invoice_number}: montant taxes {tax_eur:.0f} EUR "
                    f"ne correspond pas au taux applicable ({rng.choice(['accise', 'CTA', 'TVA'])} incorrect).",
                },
            }
            tpl = _ANOMALY_TEMPLATES[anomaly_type]
            db.add(
                BillingInsight(
                    site_id=site.id,
                    invoice_id=invoice.id,
                    type=tpl["type"],
                    severity=tpl["severity"],
                    message=tpl["msg"],
                    estimated_loss_eur=round(total * rng.uniform(0.05, 0.20), 2),
                    insight_status=InsightStatus.OPEN,
                )
            )
            insights_created += 1

    db.flush()

    return {
        "contracts_count": contracts_created,
        "invoices_count": invoices_created,
        "lines_count": lines_created,
        "insights_count": insights_created,
    }
