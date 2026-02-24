"""
PROMEOS — Bill Intelligence Seed Demo (V68)
36 mois (Jan 2023 – Déc 2025) × 2 sites (elec + gaz).
3 trous + 2 partiels + 3 anomalies contrôlées.
Idempotent via source tag "seed_36m".
"""
import calendar
from datetime import date
from sqlalchemy.orm import Session

from models import (
    Site, EnergyContract, EnergyInvoice, EnergyInvoiceLine,
    BillingEnergyType, InvoiceLineType, BillingInvoiceStatus,
)

# ── Constantes seed ──
SOURCE_TAG     = "seed_36m"
START_YEAR     = 2023
START_MONTH    = 1
MONTHS_COUNT   = 36   # Jan 2023 → Déc 2025
KWH_ELEC       = 9000
KWH_GAZ        = 6000
PRICE_REF_ELEC = 0.18   # EUR/kWh all-in (TTC / kWh dans ce modèle simplifié)
PRICE_REF_GAZ  = 0.09

# Montants ligne "normaux" pour 9000 kWh elec (total = 1620)
ELEC_ENERGY_AMT  = 1020.0   # fourniture
ELEC_NETWORK_AMT = 400.0    # réseau (attendu TURPE ≈ 407.70 → delta < 2%)
ELEC_TAX_AMT     = 200.0    # taxes (attendu CSPE ≈ 202.50 → delta < 1%)

# Montants ligne "normaux" pour 6000 kWh gaz (total = 540)
GAZ_ENERGY_AMT  = 192.0     # fourniture
GAZ_NETWORK_AMT = 220.0     # réseau (attendu ATRD+ATRT ≈ 222 → delta < 1%)
GAZ_TAX_AMT     = 128.0     # taxes (attendu TICGN ≈ 130.20 → delta < 2%)

# ── Trous contrôlés ──
GAPS_SITE_A = {
    (2023, 3): "missing",
    (2024, 9): "missing",
}
PARTIALS_SITE_A = {
    (2023, 6): 15,   # 15 jours → couverture partielle
    (2024, 1): 20,   # 20 jours/31 → couverture partielle
}
GAPS_SITE_B = {
    (2025, 2): "missing",
}

# ── Anomalies contrôlées ──
ANOMALY_SHADOW_GAP    = (2024, 7)   # R1 : total_eur = shadow × 1.45
ANOMALY_RESEAU_MISMATCH = (2024, 11)  # R13: NETWORK line = TURPE × 2.3
ANOMALY_TAXES_MISMATCH  = (2025, 1)   # R14: TAX line = CSPE × 1.08


def _iter_months(start_year: int, start_month: int, count: int):
    """Génère (year, month) pour `count` mois consécutifs."""
    y, m = start_year, start_month
    for _ in range(count):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def _add_elec_invoice(db: Session, site_id: int, contract_id: int, y: int, m: int) -> None:
    """Crée une facture elec pour le mois (y, m), avec anomalies contrôlées."""
    # Trou → skip
    if (y, m) in GAPS_SITE_A:
        return

    # Période
    days_in_month = calendar.monthrange(y, m)[1]
    period_start = date(y, m, 1)

    if (y, m) in PARTIALS_SITE_A:
        period_end = date(y, m, PARTIALS_SITE_A[(y, m)])
    else:
        period_end = date(y, m, days_in_month)

    issue_date = date(y, m + 1 if m < 12 else 1, 5)
    if m == 12:
        issue_date = date(y + 1, 1, 5)

    energy_line = ELEC_ENERGY_AMT
    network_line = ELEC_NETWORK_AMT
    tax_line = ELEC_TAX_AMT

    # Anomalie R13 : réseau × 2.3
    if (y, m) == ANOMALY_RESEAU_MISMATCH:
        network_line = round(9000 * 0.0453 * 2.3, 2)  # 937.71

    # Anomalie R14 : taxes × 1.08
    if (y, m) == ANOMALY_TAXES_MISMATCH:
        tax_line = round(9000 * 0.0225 * 1.08, 2)  # 218.70

    total_eur = round(energy_line + network_line + tax_line, 2)

    # Anomalie R1 : surcharge 45%
    if (y, m) == ANOMALY_SHADOW_GAP:
        total_eur = round(KWH_ELEC * PRICE_REF_ELEC * 1.45, 2)  # 2349.00
        energy_line = round(total_eur - network_line - tax_line, 2)

    inv = EnergyInvoice(
        site_id=site_id,
        contract_id=contract_id,
        invoice_number=f"EDF-{y}-{m:02d}",
        period_start=period_start,
        period_end=period_end,
        issue_date=issue_date,
        total_eur=total_eur,
        energy_kwh=KWH_ELEC,
        status=BillingInvoiceStatus.IMPORTED,
        source=SOURCE_TAG,
    )
    db.add(inv)
    db.flush()

    for lt, label, qty, unit, up, amt in [
        (InvoiceLineType.ENERGY,  "Consommation elec",  KWH_ELEC, "kWh", round(energy_line / KWH_ELEC, 4), energy_line),
        (InvoiceLineType.NETWORK, "Acheminement TURPE",     None,  None,  None, network_line),
        (InvoiceLineType.TAX,     "CSPE / Accise elec",     None,  None,  None, tax_line),
    ]:
        db.add(EnergyInvoiceLine(
            invoice_id=inv.id, line_type=lt, label=label,
            qty=qty, unit=unit, unit_price=up, amount_eur=amt,
        ))


def _add_gaz_invoice(db: Session, site_id: int, contract_id: int, y: int, m: int) -> None:
    """Crée une facture gaz pour le mois (y, m)."""
    if (y, m) in GAPS_SITE_B:
        return

    days_in_month = calendar.monthrange(y, m)[1]
    period_start = date(y, m, 1)
    period_end = date(y, m, days_in_month)
    issue_date = date(y, m + 1 if m < 12 else 1, 10)
    if m == 12:
        issue_date = date(y + 1, 1, 10)

    total_eur = round(GAZ_ENERGY_AMT + GAZ_NETWORK_AMT + GAZ_TAX_AMT, 2)

    inv = EnergyInvoice(
        site_id=site_id,
        contract_id=contract_id,
        invoice_number=f"ENGIE-{y}-{m:02d}",
        period_start=period_start,
        period_end=period_end,
        issue_date=issue_date,
        total_eur=total_eur,
        energy_kwh=KWH_GAZ,
        status=BillingInvoiceStatus.IMPORTED,
        source=SOURCE_TAG,
    )
    db.add(inv)
    db.flush()

    for lt, label, qty, unit, up, amt in [
        (InvoiceLineType.ENERGY,  "Terme variable gaz",    KWH_GAZ, "kWh", round(GAZ_ENERGY_AMT / KWH_GAZ, 4), GAZ_ENERGY_AMT),
        (InvoiceLineType.NETWORK, "Acheminement gaz (ATRD+ATRT)", None, None, None, GAZ_NETWORK_AMT),
        (InvoiceLineType.TAX,     "TICGN",                  None,  None,  None, GAZ_TAX_AMT),
    ]:
        db.add(EnergyInvoiceLine(
            invoice_id=inv.id, line_type=lt, label=label,
            qty=qty, unit=unit, unit_price=up, amount_eur=amt,
        ))


def seed_billing_demo(db: Session) -> dict:
    """
    Seed 36 mois (Jan 2023 – Déc 2025) × 2 sites (elec + gaz).
    Trous contrôlés : 2023-03, 2024-09 (site_a); 2025-02 (site_b).
    Partiels : 2023-06 (15j), 2024-01 (20j/31) sur site_a.
    Anomalies : 2024-07 R1 shadow_gap, 2024-11 R13 reseau, 2025-01 R14 taxes.
    Idempotent via source="seed_36m".
    """
    # Idempotency check
    existing = db.query(EnergyInvoice).filter(
        EnergyInvoice.source == SOURCE_TAG
    ).count()
    if existing > 0:
        return {"skipped": True, "reason": "already seeded (seed_36m)", "existing": existing}

    # Récupérer les 2 premiers sites
    sites = db.query(Site).limit(3).all()
    if len(sites) < 2:
        return {"error": "Need at least 2 sites to seed billing demo"}

    site_a = sites[0]
    site_b = sites[1]

    # ── Contrats ──
    contract_elec = EnergyContract(
        site_id=site_a.id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF ENR",
        start_date=date(2022, 12, 1),
        end_date=date(2026, 12, 31),
        price_ref_eur_per_kwh=PRICE_REF_ELEC,
        fixed_fee_eur_per_month=45.0,
    )
    db.add(contract_elec)

    contract_gaz = EnergyContract(
        site_id=site_b.id,
        energy_type=BillingEnergyType.GAZ,
        supplier_name="Engie Pro",
        start_date=date(2022, 12, 1),
        end_date=date(2025, 12, 31),
        price_ref_eur_per_kwh=PRICE_REF_GAZ,
        fixed_fee_eur_per_month=30.0,
    )
    db.add(contract_gaz)
    db.flush()

    # ── 36 mois site_a (elec) ──
    for y, m in _iter_months(START_YEAR, START_MONTH, MONTHS_COUNT):
        _add_elec_invoice(db, site_a.id, contract_elec.id, y, m)

    # ── 36 mois site_b (gaz) ──
    for y, m in _iter_months(START_YEAR, START_MONTH, MONTHS_COUNT):
        _add_gaz_invoice(db, site_b.id, contract_gaz.id, y, m)

    db.commit()

    # Compter
    n_elec = db.query(EnergyInvoice).filter(
        EnergyInvoice.site_id == site_a.id,
        EnergyInvoice.source == SOURCE_TAG,
    ).count()
    n_gaz = db.query(EnergyInvoice).filter(
        EnergyInvoice.site_id == site_b.id,
        EnergyInvoice.source == SOURCE_TAG,
    ).count()

    return {
        "contracts_created": 2,
        "invoices_created": n_elec + n_gaz,
        "elec_invoices": n_elec,
        "gaz_invoices": n_gaz,
        "sites_used": [site_a.id, site_b.id],
        "months_range": f"{START_YEAR}-{START_MONTH:02d} → 2025-12",
        "controlled_gaps": 3,
        "controlled_anomalies": 3,
    }
