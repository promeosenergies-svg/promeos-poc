"""
Generate 24-month demo invoice corpus for PROMEOS Bill Intelligence.
2 sites x 2 energies x 24 months = up to 96 invoices.
Site 1: EDF elec + Engie gaz
Site 2: TotalEnergies elec only (some months missing = gaps)
"""

import json
import os
import random
from datetime import date, timedelta
from calendar import monthrange

DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoices", "demo")

random.seed(42)  # Reproducible


def month_range(year: int, month: int):
    """Return (first_day, last_day) for a given year/month."""
    _, days = monthrange(year, month)
    return date(year, month, 1), date(year, month, days)


def generate_elec_invoice(
    site_id,
    supplier,
    pdl,
    contract,
    year,
    month,
    idx,
    puissance_kva=120,
    base_conso=18000,
    abo_price=145.92,
    introduce_error=False,
):
    """Generate a realistic electricity invoice."""
    p_start, p_end = month_range(year, month)
    inv_date = p_end + timedelta(days=15)
    due_date = inv_date + timedelta(days=30)

    # Seasonal variation on consumption
    season_factor = 1.0
    if month in (12, 1, 2):
        season_factor = 1.25
    elif month in (6, 7, 8):
        season_factor = 0.80
    elif month in (3, 4, 5, 9, 10, 11):
        season_factor = 1.0 + random.uniform(-0.05, 0.05)

    conso = int(base_conso * season_factor * random.uniform(0.95, 1.05))
    hp_ratio = random.uniform(0.55, 0.65)
    conso_hp = int(conso * hp_ratio)
    conso_hc = conso - conso_hp

    # Unit prices with slight yearly evolution
    year_offset = (year - 2023) * 0.005
    hp_price = round(0.0952 + year_offset + random.uniform(-0.002, 0.002), 4)
    hc_price = round(0.0741 + year_offset + random.uniform(-0.002, 0.002), 4)

    components = [
        {
            "component_type": "abonnement",
            "label": f"Abonnement Option Base C5 - {puissance_kva} kVA",
            "quantity": 1,
            "unit": "mois",
            "unit_price": abo_price,
            "amount_ht": abo_price,
            "tva_rate": 5.5 if not introduce_error else 20.0,
            "tva_amount": round(abo_price * (0.055 if not introduce_error else 0.20), 2),
        },
        {
            "component_type": "conso_hp",
            "label": "Energie heures pleines",
            "quantity": conso_hp,
            "unit": "kWh",
            "unit_price": hp_price,
            "amount_ht": round(conso_hp * hp_price, 2),
            "tva_rate": 20.0,
            "tva_amount": round(conso_hp * hp_price * 0.20, 2),
        },
        {
            "component_type": "conso_hc",
            "label": "Energie heures creuses",
            "quantity": conso_hc,
            "unit": "kWh",
            "unit_price": hc_price,
            "amount_ht": round(conso_hc * hc_price, 2),
            "tva_rate": 20.0,
            "tva_amount": round(conso_hc * hc_price * 0.20, 2),
        },
        {
            "component_type": "turpe_fixe",
            "label": "TURPE - Composante de gestion",
            "quantity": 1,
            "unit": "mois",
            "unit_price": 18.48,
            "amount_ht": 18.48,
            "tva_rate": 5.5,
            "tva_amount": round(18.48 * 0.055, 2),
        },
        {
            "component_type": "turpe_puissance",
            "label": "TURPE - Composante de soutirage fixe",
            "quantity": puissance_kva,
            "unit": "kVA",
            "unit_price": 4.56,
            "amount_ht": round(puissance_kva * 4.56, 2),
            "tva_rate": 20.0,
            "tva_amount": round(puissance_kva * 4.56 * 0.20, 2),
        },
        {
            "component_type": "cta",
            "label": "Contribution Tarifaire d'Acheminement",
            "quantity": 1,
            "unit": "forfait",
            "amount_ht": 63.36,
            "tva_rate": 5.5,
            "tva_amount": round(63.36 * 0.055, 2),
        },
        {
            "component_type": "accise",
            "label": "Accise sur l'electricite (ex-CSPE/TICFE)",
            "quantity": conso,
            "unit": "kWh",
            "unit_price": 0.02121,
            "amount_ht": round(conso * 0.02121, 2),
            "tva_rate": 20.0,
            "tva_amount": round(conso * 0.02121 * 0.20, 2),
        },
    ]

    # Sum HT (non-TVA components only)
    total_ht = round(sum(c["amount_ht"] for c in components), 2)
    total_tva = round(sum(c["tva_amount"] for c in components), 2)
    total_ttc = round(total_ht + total_tva, 2)

    # Add TVA recap lines
    tva_reduite_base = sum(c["amount_ht"] for c in components if c["tva_rate"] == 5.5)
    tva_normale_base = sum(c["amount_ht"] for c in components if c["tva_rate"] == 20.0)
    tva_reduite_amount = round(sum(c["tva_amount"] for c in components if c["tva_rate"] == 5.5), 2)
    tva_normale_amount = round(sum(c["tva_amount"] for c in components if c["tva_rate"] == 20.0), 2)

    components.append(
        {
            "component_type": "tva_reduite",
            "label": "TVA 5,5% (abonnement + CTA + TURPE gestion)",
            "amount_ht": round(tva_reduite_base, 2),
            "tva_rate": 5.5,
            "tva_amount": tva_reduite_amount,
        }
    )
    components.append(
        {
            "component_type": "tva_normale",
            "label": "TVA 20% (consommation + TURPE soutirage + accise)",
            "amount_ht": round(tva_normale_base, 2),
            "tva_rate": 20.0,
            "tva_amount": tva_normale_amount,
        }
    )

    invoice_id = f"DEMO-ELEC-{site_id:03d}-{year}{month:02d}"

    return {
        "invoice_id": invoice_id,
        "energy_type": "elec",
        "supplier": supplier,
        "contract_ref": contract,
        "pdl_pce": pdl,
        "site_id": site_id,
        "invoice_date": str(inv_date),
        "due_date": str(due_date),
        "period_start": str(p_start),
        "period_end": str(p_end),
        "total_ht": total_ht,
        "total_tva": total_tva,
        "total_ttc": total_ttc,
        "conso_kwh": conso,
        "puissance_souscrite_kva": puissance_kva,
        "source_format": "json",
        "components": components,
        "_demo_notes": f"Facture demo elec {supplier} site {site_id} - {year}/{month:02d}",
    }


def generate_gaz_invoice(site_id, supplier, pce, contract, year, month, idx, base_conso=25000, abo_price=38.50):
    """Generate a realistic gas invoice."""
    p_start, p_end = month_range(year, month)
    inv_date = p_end + timedelta(days=20)
    due_date = inv_date + timedelta(days=30)

    # Seasonal variation (gas heavier in winter)
    season_factor = 1.0
    if month in (12, 1, 2):
        season_factor = 1.8
    elif month in (6, 7, 8):
        season_factor = 0.3
    elif month in (3, 11):
        season_factor = 1.2
    elif month in (4, 5, 9, 10):
        season_factor = 0.7

    conso = int(base_conso * season_factor * random.uniform(0.92, 1.08))

    molecule_price = round(0.0385 + random.uniform(-0.003, 0.003), 4)

    components = [
        {
            "component_type": "abonnement",
            "label": "Abonnement distribution gaz T2",
            "quantity": 1,
            "unit": "mois",
            "unit_price": abo_price,
            "amount_ht": abo_price,
            "tva_rate": 5.5,
            "tva_amount": round(abo_price * 0.055, 2),
        },
        {
            "component_type": "terme_variable",
            "label": "Molecule gaz naturel",
            "quantity": conso,
            "unit": "kWh",
            "unit_price": molecule_price,
            "amount_ht": round(conso * molecule_price, 2),
            "tva_rate": 20.0,
            "tva_amount": round(conso * molecule_price * 0.20, 2),
        },
        {
            "component_type": "terme_fixe",
            "label": "ATRD7 - Part fixe distribution GRDF",
            "quantity": 1,
            "unit": "mois",
            "unit_price": 52.80,
            "amount_ht": 52.80,
            "tva_rate": 5.5,
            "tva_amount": round(52.80 * 0.055, 2),
        },
        {
            "component_type": "turpe_energie",
            "label": "ATRD7 - Part proportionnelle distribution",
            "quantity": conso,
            "unit": "kWh",
            "unit_price": 0.0062,
            "amount_ht": round(conso * 0.0062, 2),
            "tva_rate": 20.0,
            "tva_amount": round(conso * 0.0062 * 0.20, 2),
        },
        {
            "component_type": "cta",
            "label": "CTA (Contribution Tarifaire d'Acheminement)",
            "quantity": 1,
            "unit": "forfait",
            "amount_ht": 14.87,
            "tva_rate": 5.5,
            "tva_amount": round(14.87 * 0.055, 2),
        },
        {
            "component_type": "accise",
            "label": "Accise sur le gaz naturel (ex-TICGN)",
            "quantity": conso,
            "unit": "kWh",
            "unit_price": 0.008,
            "amount_ht": round(conso * 0.008, 2),
            "tva_rate": 20.0,
            "tva_amount": round(conso * 0.008 * 0.20, 2),
        },
    ]

    total_ht = round(sum(c["amount_ht"] for c in components), 2)
    total_tva = round(sum(c["tva_amount"] for c in components), 2)
    total_ttc = round(total_ht + total_tva, 2)

    # TVA recap
    tva_reduite_base = sum(c["amount_ht"] for c in components if c["tva_rate"] == 5.5)
    tva_normale_base = sum(c["amount_ht"] for c in components if c["tva_rate"] == 20.0)
    tva_reduite_amount = round(sum(c["tva_amount"] for c in components if c["tva_rate"] == 5.5), 2)
    tva_normale_amount = round(sum(c["tva_amount"] for c in components if c["tva_rate"] == 20.0), 2)

    components.append(
        {
            "component_type": "tva_reduite",
            "label": "TVA 5,5%",
            "amount_ht": round(tva_reduite_base, 2),
            "tva_rate": 5.5,
            "tva_amount": tva_reduite_amount,
        }
    )
    components.append(
        {
            "component_type": "tva_normale",
            "label": "TVA 20%",
            "amount_ht": round(tva_normale_base, 2),
            "tva_rate": 20.0,
            "tva_amount": tva_normale_amount,
        }
    )

    invoice_id = f"DEMO-GAZ-{site_id:03d}-{year}{month:02d}"

    return {
        "invoice_id": invoice_id,
        "energy_type": "gaz",
        "supplier": supplier,
        "contract_ref": contract,
        "pdl_pce": pce,
        "site_id": site_id,
        "invoice_date": str(inv_date),
        "due_date": str(due_date),
        "period_start": str(p_start),
        "period_end": str(p_end),
        "total_ht": total_ht,
        "total_tva": total_tva,
        "total_ttc": total_ttc,
        "conso_kwh": conso,
        "source_format": "json",
        "components": components,
        "_demo_notes": f"Facture demo gaz {supplier} site {site_id} - {year}/{month:02d}",
    }


def main():
    os.makedirs(DEMO_DIR, exist_ok=True)

    count = 0

    # Keep existing 3 hand-crafted invoices (they're already there)
    # Generate site 1: EDF elec + Engie gaz, 24 months (2023-01 to 2024-12)
    for year in (2023, 2024):
        for month in range(1, 13):
            idx = (year - 2023) * 12 + month

            # Elec site 1
            inv = generate_elec_invoice(
                site_id=1,
                supplier="EDF Entreprises",
                pdl="30001234567890",
                contract="CTR-EDF-DEMO-001",
                year=year,
                month=month,
                idx=idx,
            )
            fname = f"facture_elec_site1_{year}_{month:02d}.json"
            with open(os.path.join(DEMO_DIR, fname), "w", encoding="utf-8") as f:
                json.dump(inv, f, indent=2, ensure_ascii=False)
            count += 1

            # Gaz site 1
            inv = generate_gaz_invoice(
                site_id=1,
                supplier="Engie Entreprises",
                pce="GI000789012345",
                contract="CTR-ENGIE-DEMO-001",
                year=year,
                month=month,
                idx=idx,
            )
            fname = f"facture_gaz_site1_{year}_{month:02d}.json"
            with open(os.path.join(DEMO_DIR, fname), "w", encoding="utf-8") as f:
                json.dump(inv, f, indent=2, ensure_ascii=False)
            count += 1

    # Site 2: TotalEnergies elec only, with intentional gaps (missing months 4, 8, 11 each year)
    gap_months = {4, 8, 11}
    for year in (2023, 2024):
        for month in range(1, 13):
            if month in gap_months:
                continue  # Intentional gap
            idx = (year - 2023) * 12 + month

            # Introduce a TVA error on 2024-06
            error = year == 2024 and month == 6

            inv = generate_elec_invoice(
                site_id=2,
                supplier="TotalEnergies",
                pdl="30009876543210",
                contract="CTR-TE-DEMO-001",
                year=year,
                month=month,
                idx=idx,
                puissance_kva=80,
                base_conso=12000,
                abo_price=98.40,
                introduce_error=error,
            )
            fname = f"facture_elec_site2_{year}_{month:02d}.json"
            with open(os.path.join(DEMO_DIR, fname), "w", encoding="utf-8") as f:
                json.dump(inv, f, indent=2, ensure_ascii=False)
            count += 1

    print(f"Generated {count} demo invoices in {DEMO_DIR}")


if __name__ == "__main__":
    main()
