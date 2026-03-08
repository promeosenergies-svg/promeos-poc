"""
PROMEOS — Bill Intelligence Seed Demo (V68 + B4)
36 mois (Jan 2023 – Déc 2025) × 5 sites.
Site A (Paris ELEC), Site B (Lyon GAZ), Site C (Marseille ELEC),
Site D (Nice ELEC+GAZ), Site E (Toulouse ELEC).
Trous + anomalies contrôlées par site.
Idempotent via source tag "seed_36m".
"""

import calendar
from datetime import date, timedelta
from sqlalchemy.orm import Session

from models import (
    Site,
    EnergyContract,
    EnergyInvoice,
    EnergyInvoiceLine,
    BillingEnergyType,
    InvoiceLineType,
    BillingInvoiceStatus,
)

# ── Constantes seed ──
SOURCE_TAG = "seed_36m"
START_YEAR = 2023
START_MONTH = 1
MONTHS_COUNT = 36  # Jan 2023 → Déc 2025
KWH_ELEC = 9000
KWH_GAZ = 6000
from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH, DEFAULT_PRICE_GAZ_EUR_KWH

PRICE_REF_ELEC = DEFAULT_PRICE_ELEC_EUR_KWH  # EUR/kWh all-in
PRICE_REF_GAZ = DEFAULT_PRICE_GAZ_EUR_KWH

# Montants ligne "normaux" pour 9000 kWh elec (total = 1620)
ELEC_ENERGY_AMT = 1020.0  # fourniture
ELEC_NETWORK_AMT = 400.0  # réseau (attendu TURPE ≈ 407.70 → delta < 2%)
ELEC_TAX_AMT = 200.0  # taxes (attendu CSPE ≈ 202.50 → delta < 1%)

# Montants ligne "normaux" pour 6000 kWh gaz (total = 540)
GAZ_ENERGY_AMT = 192.0  # fourniture
GAZ_NETWORK_AMT = 220.0  # réseau (attendu ATRD+ATRT ≈ 222 → delta < 1%)
GAZ_TAX_AMT = 128.0  # taxes (attendu TICGN ≈ 130.20 → delta < 2%)

# ── Trous contrôlés ──
GAPS_SITE_A = {
    (2023, 3): "missing",
    (2024, 9): "missing",
}
PARTIALS_SITE_A = {
    (2023, 6): 15,  # 15 jours → couverture partielle
    (2024, 1): 20,  # 20 jours/31 → couverture partielle
}
GAPS_SITE_B = {
    (2025, 2): "missing",
}

# ── Anomalies contrôlées ──
ANOMALY_SHADOW_GAP = (2024, 7)  # R1 : total_eur = shadow × 1.45
ANOMALY_RESEAU_MISMATCH = (2024, 11)  # R13: NETWORK line = TURPE × 2.3
ANOMALY_TAXES_MISMATCH = (2025, 1)  # R14: TAX line = CSPE × 1.08

# ── Site C (Marseille école ELEC) ──
KWH_MARSEILLE = 4500
PRICE_REF_MARSEILLE = 0.19
MARSEILLE_ENERGY_AMT = round(KWH_MARSEILLE * 0.1133, 2)  # 509.85 fourniture
MARSEILLE_NETWORK_AMT = round(KWH_MARSEILLE * 0.045, 2)  # 202.50 réseau
MARSEILLE_TAX_AMT = round(KWH_MARSEILLE * 0.0225, 2)  # 101.25 taxes
GAPS_MARSEILLE = {(2024, 8): "missing"}  # vacances scolaires
ANOMALY_MARSEILLE_R1 = (2025, 3)  # R1 : surfacturation 35%
ANOMALY_MARSEILLE_R3 = (2025, 10)  # R3 : spike ×2.7

# ── Site D (Nice hôtel ELEC + GAZ) ──
KWH_NICE_ELEC = 8000
KWH_NICE_GAZ = 3000
PRICE_REF_NICE_ELEC = 0.21
PRICE_REF_NICE_GAZ = 0.09
NICE_ELEC_ENERGY_AMT = round(KWH_NICE_ELEC * 0.14, 2)  # 1120.00
NICE_ELEC_NETWORK_AMT = round(KWH_NICE_ELEC * 0.045, 2)  # 360.00
NICE_ELEC_TAX_AMT = round(KWH_NICE_ELEC * 0.0225, 2)  # 180.00
NICE_GAZ_ENERGY_AMT = round(KWH_NICE_GAZ * 0.032, 2)  # 96.00
NICE_GAZ_NETWORK_AMT = round(KWH_NICE_GAZ * 0.037, 2)  # 111.00
NICE_GAZ_TAX_AMT = round(KWH_NICE_GAZ * 0.022, 2)  # 66.00
ANOMALY_NICE_R11 = (2025, 6)  # R11 : TTC ≠ HT + TVA (écart 3.5%)
# Saisonnalité hôtel : été ×1.4 elec (clim), hiver ×1.3 gaz (chauffage)
_NICE_ELEC_SEASON = {6: 1.4, 7: 1.4, 8: 1.4, 12: 0.9, 1: 0.9, 2: 0.9}
_NICE_GAZ_SEASON = {12: 1.3, 1: 1.3, 2: 1.3, 6: 0.7, 7: 0.7, 8: 0.7}

# ── Site E (Toulouse entrepôt ELEC) ──
KWH_TOULOUSE = 12000
PRICE_REF_TOULOUSE = 0.17
TOULOUSE_ENERGY_AMT = round(KWH_TOULOUSE * 0.1133, 2)  # 1359.60
TOULOUSE_NETWORK_AMT = round(KWH_TOULOUSE * 0.04, 2)  # 480.00
TOULOUSE_TAX_AMT = round(KWH_TOULOUSE * 0.0225, 2)  # 270.00
TOULOUSE_START_YEAR = 2024
TOULOUSE_START_MONTH = 7
TOULOUSE_MONTHS = 18  # Juil 2024 → Déc 2025 (couverture partielle)
GAPS_TOULOUSE = {(2024, 9): "missing", (2024, 12): "missing", (2025, 3): "missing"}
ANOMALY_TOULOUSE_R1 = (2025, 11)  # R1 : implied_price 0.24 vs ref 0.17 (écart 41%)


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
        (InvoiceLineType.ENERGY, "Consommation elec", KWH_ELEC, "kWh", round(energy_line / KWH_ELEC, 4), energy_line),
        (InvoiceLineType.NETWORK, "Acheminement TURPE", None, None, None, network_line),
        (InvoiceLineType.TAX, "CSPE / Accise elec", None, None, None, tax_line),
    ]:
        db.add(
            EnergyInvoiceLine(
                invoice_id=inv.id,
                line_type=lt,
                label=label,
                qty=qty,
                unit=unit,
                unit_price=up,
                amount_eur=amt,
            )
        )


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
        (
            InvoiceLineType.ENERGY,
            "Terme variable gaz",
            KWH_GAZ,
            "kWh",
            round(GAZ_ENERGY_AMT / KWH_GAZ, 4),
            GAZ_ENERGY_AMT,
        ),
        (InvoiceLineType.NETWORK, "Acheminement gaz (ATRD+ATRT)", None, None, None, GAZ_NETWORK_AMT),
        (InvoiceLineType.TAX, "TICGN", None, None, None, GAZ_TAX_AMT),
    ]:
        db.add(
            EnergyInvoiceLine(
                invoice_id=inv.id,
                line_type=lt,
                label=label,
                qty=qty,
                unit=unit,
                unit_price=up,
                amount_eur=amt,
            )
        )


def _add_marseille_invoice(db: Session, site_id: int, contract_id: int, y: int, m: int) -> None:
    """Crée une facture ELEC école Marseille pour le mois (y, m)."""
    if (y, m) in GAPS_MARSEILLE:
        return

    days_in_month = calendar.monthrange(y, m)[1]
    period_start = date(y, m, 1)
    period_end = date(y, m, days_in_month)
    issue_date = date(y + 1, 1, 5) if m == 12 else date(y, m + 1, 5)

    energy_kwh = KWH_MARSEILLE
    energy_line = MARSEILLE_ENERGY_AMT
    network_line = MARSEILLE_NETWORK_AMT
    tax_line = MARSEILLE_TAX_AMT

    # Anomalie R3 : spike ×2.7
    if (y, m) == ANOMALY_MARSEILLE_R3:
        energy_kwh = round(KWH_MARSEILLE * 2.7)  # 12150
        energy_line = round(energy_kwh * 0.1133, 2)
        network_line = round(energy_kwh * 0.045, 2)
        tax_line = round(energy_kwh * 0.0225, 2)

    total_eur = round(energy_line + network_line + tax_line, 2)

    # Anomalie R1 : surfacturation 35%
    if (y, m) == ANOMALY_MARSEILLE_R1:
        total_eur = round(KWH_MARSEILLE * PRICE_REF_MARSEILLE * 1.35, 2)
        energy_line = round(total_eur - network_line - tax_line, 2)

    inv = EnergyInvoice(
        site_id=site_id,
        contract_id=contract_id,
        invoice_number=f"ENGIE-MAR-{y}{m:02d}",
        period_start=period_start,
        period_end=period_end,
        issue_date=issue_date,
        total_eur=total_eur,
        energy_kwh=energy_kwh,
        status=BillingInvoiceStatus.IMPORTED,
        source=SOURCE_TAG,
    )
    db.add(inv)
    db.flush()

    for lt, label, qty, unit, up, amt in [
        (
            InvoiceLineType.ENERGY,
            "Consommation elec",
            energy_kwh,
            "kWh",
            round(energy_line / energy_kwh, 4),
            energy_line,
        ),
        (InvoiceLineType.NETWORK, "Acheminement TURPE", None, None, None, network_line),
        (InvoiceLineType.TAX, "CSPE / Accise elec", None, None, None, tax_line),
    ]:
        db.add(
            EnergyInvoiceLine(
                invoice_id=inv.id,
                line_type=lt,
                label=label,
                qty=qty,
                unit=unit,
                unit_price=up,
                amount_eur=amt,
            )
        )


def _add_nice_elec_invoice(db: Session, site_id: int, contract_id: int, y: int, m: int) -> None:
    """Crée une facture ELEC hôtel Nice pour le mois (y, m), avec saisonnalité."""
    days_in_month = calendar.monthrange(y, m)[1]
    period_start = date(y, m, 1)
    period_end = date(y, m, days_in_month)
    issue_date = date(y + 1, 1, 5) if m == 12 else date(y, m + 1, 5)

    season = _NICE_ELEC_SEASON.get(m, 1.0)
    energy_kwh = round(KWH_NICE_ELEC * season)
    energy_line = round(NICE_ELEC_ENERGY_AMT * season, 2)
    network_line = round(NICE_ELEC_NETWORK_AMT * season, 2)
    tax_line = round(NICE_ELEC_TAX_AMT * season, 2)

    total_eur = round(energy_line + network_line + tax_line, 2)

    # Anomalie R11 : TTC ≠ HT + TVA (écart 3.5%)
    if (y, m) == ANOMALY_NICE_R11:
        total_eur = round(total_eur * 1.035, 2)

    inv = EnergyInvoice(
        site_id=site_id,
        contract_id=contract_id,
        invoice_number=f"TOTAL-NIC-{y}{m:02d}",
        period_start=period_start,
        period_end=period_end,
        issue_date=issue_date,
        total_eur=total_eur,
        energy_kwh=energy_kwh,
        status=BillingInvoiceStatus.IMPORTED,
        source=SOURCE_TAG,
    )
    db.add(inv)
    db.flush()

    for lt, label, qty, unit, up, amt in [
        (
            InvoiceLineType.ENERGY,
            "Consommation elec",
            energy_kwh,
            "kWh",
            round(energy_line / energy_kwh, 4),
            energy_line,
        ),
        (InvoiceLineType.NETWORK, "Acheminement TURPE", None, None, None, network_line),
        (InvoiceLineType.TAX, "CSPE / Accise elec", None, None, None, tax_line),
    ]:
        db.add(
            EnergyInvoiceLine(
                invoice_id=inv.id,
                line_type=lt,
                label=label,
                qty=qty,
                unit=unit,
                unit_price=up,
                amount_eur=amt,
            )
        )


def _add_nice_gaz_invoice(db: Session, site_id: int, contract_id: int, y: int, m: int) -> None:
    """Crée une facture GAZ hôtel Nice pour le mois (y, m), avec saisonnalité."""
    days_in_month = calendar.monthrange(y, m)[1]
    period_start = date(y, m, 1)
    period_end = date(y, m, days_in_month)
    issue_date = date(y + 1, 1, 10) if m == 12 else date(y, m + 1, 10)

    season = _NICE_GAZ_SEASON.get(m, 1.0)
    energy_kwh = round(KWH_NICE_GAZ * season)
    energy_line = round(NICE_GAZ_ENERGY_AMT * season, 2)
    network_line = round(NICE_GAZ_NETWORK_AMT * season, 2)
    tax_line = round(NICE_GAZ_TAX_AMT * season, 2)

    total_eur = round(energy_line + network_line + tax_line, 2)

    inv = EnergyInvoice(
        site_id=site_id,
        contract_id=contract_id,
        invoice_number=f"ENGIE-NIC-G-{y}{m:02d}",
        period_start=period_start,
        period_end=period_end,
        issue_date=issue_date,
        total_eur=total_eur,
        energy_kwh=energy_kwh,
        status=BillingInvoiceStatus.IMPORTED,
        source=SOURCE_TAG,
    )
    db.add(inv)
    db.flush()

    for lt, label, qty, unit, up, amt in [
        (
            InvoiceLineType.ENERGY,
            "Terme variable gaz",
            energy_kwh,
            "kWh",
            round(energy_line / energy_kwh, 4),
            energy_line,
        ),
        (InvoiceLineType.NETWORK, "Acheminement gaz (ATRD+ATRT)", None, None, None, network_line),
        (InvoiceLineType.TAX, "TICGN", None, None, None, tax_line),
    ]:
        db.add(
            EnergyInvoiceLine(
                invoice_id=inv.id,
                line_type=lt,
                label=label,
                qty=qty,
                unit=unit,
                unit_price=up,
                amount_eur=amt,
            )
        )


def _add_toulouse_invoice(db: Session, site_id: int, contract_id: int, y: int, m: int) -> None:
    """Crée une facture ELEC entrepôt Toulouse pour le mois (y, m)."""
    if (y, m) in GAPS_TOULOUSE:
        return

    days_in_month = calendar.monthrange(y, m)[1]
    period_start = date(y, m, 1)
    period_end = date(y, m, days_in_month)
    issue_date = date(y + 1, 1, 5) if m == 12 else date(y, m + 1, 5)

    energy_kwh = KWH_TOULOUSE
    energy_line = TOULOUSE_ENERGY_AMT
    network_line = TOULOUSE_NETWORK_AMT
    tax_line = TOULOUSE_TAX_AMT

    total_eur = round(energy_line + network_line + tax_line, 2)

    # Anomalie R1 : implied_price 0.24 vs ref 0.17 (écart 41%)
    if (y, m) == ANOMALY_TOULOUSE_R1:
        total_eur = round(KWH_TOULOUSE * 0.24, 2)
        energy_line = round(total_eur - network_line - tax_line, 2)

    inv = EnergyInvoice(
        site_id=site_id,
        contract_id=contract_id,
        invoice_number=f"EDF-TLS-{y}{m:02d}",
        period_start=period_start,
        period_end=period_end,
        issue_date=issue_date,
        total_eur=total_eur,
        energy_kwh=energy_kwh,
        status=BillingInvoiceStatus.IMPORTED,
        source=SOURCE_TAG,
    )
    db.add(inv)
    db.flush()

    for lt, label, qty, unit, up, amt in [
        (
            InvoiceLineType.ENERGY,
            "Consommation elec",
            energy_kwh,
            "kWh",
            round(energy_line / energy_kwh, 4),
            energy_line,
        ),
        (InvoiceLineType.NETWORK, "Acheminement TURPE", None, None, None, network_line),
        (InvoiceLineType.TAX, "CSPE / Accise elec", None, None, None, tax_line),
    ]:
        db.add(
            EnergyInvoiceLine(
                invoice_id=inv.id,
                line_type=lt,
                label=label,
                qty=qty,
                unit=unit,
                unit_price=up,
                amount_eur=amt,
            )
        )


def seed_billing_demo(db: Session) -> dict:
    """
    Seed 36 mois × 5 sites HELIOS avec anomalies contrôlées.
    Site A (Paris ELEC), Site B (Lyon GAZ), Site C (Marseille ELEC),
    Site D (Nice ELEC+GAZ), Site E (Toulouse ELEC, 18 mois partiel).
    Idempotent via source="seed_36m".
    """
    # Idempotency check
    existing = db.query(EnergyInvoice).filter(EnergyInvoice.source == SOURCE_TAG).count()
    if existing > 0:
        return {"skipped": True, "reason": "already seeded (seed_36m)", "existing": existing}

    # Récupérer les 5 premiers sites
    sites = db.query(Site).limit(5).all()
    if len(sites) < 2:
        return {"error": "Need at least 2 sites to seed billing demo"}

    site_a = sites[0]
    site_b = sites[1]
    site_c = sites[2] if len(sites) > 2 else None  # Marseille
    site_d = sites[3] if len(sites) > 3 else None  # Nice
    site_e = sites[4] if len(sites) > 4 else None  # Toulouse

    contracts_created = 0

    # ── Contrats site_a (Paris ELEC) ──
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
    contracts_created += 1

    # ── Contrat site_b (Lyon GAZ) ──
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
    contracts_created += 1

    # ── Contrat site_c (Marseille ELEC) ──
    contract_marseille = None
    if site_c:
        contract_marseille = EnergyContract(
            site_id=site_c.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="ENGIE",
            start_date=date(2023, 6, 1),
            end_date=date(2026, 5, 31),
            price_ref_eur_per_kwh=PRICE_REF_MARSEILLE,
            fixed_fee_eur_per_month=40.0,
        )
        db.add(contract_marseille)
        contracts_created += 1

    # ── Contrats site_d (Nice ELEC + GAZ) ──
    contract_nice_elec = None
    contract_nice_gaz = None
    if site_d:
        contract_nice_elec = EnergyContract(
            site_id=site_d.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="TotalEnergies",
            start_date=date(2023, 1, 1),
            end_date=date.today() + timedelta(days=30),  # expire dans 30j → R12
            price_ref_eur_per_kwh=PRICE_REF_NICE_ELEC,
            fixed_fee_eur_per_month=75.0,
        )
        db.add(contract_nice_elec)
        contracts_created += 1

        contract_nice_gaz = EnergyContract(
            site_id=site_d.id,
            energy_type=BillingEnergyType.GAZ,
            supplier_name="ENGIE",
            start_date=date(2024, 1, 1),
            end_date=date(2027, 12, 31),
            price_ref_eur_per_kwh=PRICE_REF_NICE_GAZ,
            fixed_fee_eur_per_month=35.0,
        )
        db.add(contract_nice_gaz)
        contracts_created += 1

    # ── Contrat site_e (Toulouse ELEC) ──
    contract_toulouse = None
    if site_e:
        contract_toulouse = EnergyContract(
            site_id=site_e.id,
            energy_type=BillingEnergyType.ELEC,
            supplier_name="EDF",
            start_date=date(2024, 1, 1),
            end_date=date(2027, 12, 31),
            price_ref_eur_per_kwh=PRICE_REF_TOULOUSE,
            fixed_fee_eur_per_month=85.0,
        )
        db.add(contract_toulouse)
        contracts_created += 1

    db.flush()

    # ── 36 mois site_a (Paris ELEC) ──
    for y, m in _iter_months(START_YEAR, START_MONTH, MONTHS_COUNT):
        _add_elec_invoice(db, site_a.id, contract_elec.id, y, m)

    # ── 36 mois site_b (Lyon GAZ) ──
    for y, m in _iter_months(START_YEAR, START_MONTH, MONTHS_COUNT):
        _add_gaz_invoice(db, site_b.id, contract_gaz.id, y, m)

    # ── 24 mois site_c (Marseille ELEC, Jan 2024 — Déc 2025) ──
    if site_c and contract_marseille:
        for y, m in _iter_months(2024, 1, 24):
            _add_marseille_invoice(db, site_c.id, contract_marseille.id, y, m)

    # ── 24 mois site_d (Nice ELEC + GAZ, Jan 2024 — Déc 2025) ──
    if site_d and contract_nice_elec:
        for y, m in _iter_months(2024, 1, 24):
            _add_nice_elec_invoice(db, site_d.id, contract_nice_elec.id, y, m)
    if site_d and contract_nice_gaz:
        for y, m in _iter_months(2024, 1, 24):
            _add_nice_gaz_invoice(db, site_d.id, contract_nice_gaz.id, y, m)

    # ── 18 mois site_e (Toulouse ELEC, Juil 2024 — Déc 2025) ──
    if site_e and contract_toulouse:
        for y, m in _iter_months(TOULOUSE_START_YEAR, TOULOUSE_START_MONTH, TOULOUSE_MONTHS):
            _add_toulouse_invoice(db, site_e.id, contract_toulouse.id, y, m)

    db.commit()

    # Compter par site
    total = db.query(EnergyInvoice).filter(EnergyInvoice.source == SOURCE_TAG).count()
    sites_used = [site_a.id, site_b.id]
    if site_c:
        sites_used.append(site_c.id)
    if site_d:
        sites_used.append(site_d.id)
    if site_e:
        sites_used.append(site_e.id)

    return {
        "contracts_created": contracts_created,
        "invoices_created": total,
        "sites_used": sites_used,
        "sites_count": len(sites_used),
        "months_range": f"{START_YEAR}-{START_MONTH:02d} → 2025-12",
    }
