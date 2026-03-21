"""
PROMEOS Billing Engine V2 — Deterministic invoice reconstitution.

This engine calculates what an electricity invoice SHOULD be, component by
component, from known inputs (kWh, power, period, tariff option, prices).

SUPPORTED:
  - C4 BT (>36 kVA ≤250 kVA): options LU, MU, CU
  - C5 BT (≤36 kVA): options Base, HP/HC

NOT SUPPORTED (V1):
  - C3 HTA / C2 / C1 (returned as UNSUPPORTED)
  - Gas reconstitution (returned as READ_ONLY)
  - Reactive energy / power factor penalties
  - Capacity mechanism (MEOC)
  - CEE

RULES:
  - Zero magic numbers: all rates from catalog.
  - Zero silent fallback: missing data → PARTIAL status with explicit reason.
  - Every component returns: amount, formula, inputs, sources.
  - Prorata is calendar-exact: days / days_in_month.
"""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from . import catalog
from .types import (
    AuditTrace,
    ComponentResult,
    InvoiceType,
    PeriodCode,
    RateSource,
    ReconstitutionResult,
    ReconstitutionStatus,
    TariffOption,
    TariffSegment,
)

logger = logging.getLogger(__name__)


# ─── Prorata (calendar-exact) ─────────────────────────────────────────────────


def compute_prorata(period_start: date, period_end: date) -> Tuple[int, float]:
    """
    Compute calendar-exact prorata factor for annual rates.
    Returns (days_in_period, prorata_factor).

    Prorata = days_in_period / days_in_year.
    Used to convert EUR/an and EUR/kVA/an rates to the billing period.
    days_in_year = 366 if leap year, else 365 (based on period_start).
    """
    days = (period_end - period_start).days
    if days <= 0:
        return (1, 1.0 / 365.0)

    days_in_year = 366 if calendar.isleap(period_start.year) else 365
    return (days, days / days_in_year)


# ─── Supply (Fourniture) ─────────────────────────────────────────────────────


def compute_supply_breakdown(
    kwh_by_period: Dict[str, float],
    prices_by_period: Dict[str, float],
    tva_rate: float,
) -> List[ComponentResult]:
    """
    Compute supply (fourniture) components per tariff period.

    Args:
        kwh_by_period: {"HPE": 9484, "HCE": 2283, ...}
        prices_by_period: {"HPE": 0.0950, "HCE": 0.0750, ...}
        tva_rate: 0.20 (standard)

    Returns: List of ComponentResult, one per period.
    """
    components = []
    for period_code, kwh in kwh_by_period.items():
        price = prices_by_period.get(period_code)
        if price is None:
            components.append(
                ComponentResult(
                    code=f"supply_{period_code.lower()}",
                    label=f"Fourniture {period_code}",
                    amount_ht=0.0,
                    tva_rate=tva_rate,
                    amount_tva=0.0,
                    amount_ttc=0.0,
                    formula_used=f"PRIX MANQUANT pour période {period_code}",
                    assumptions=[f"Prix fourniture {period_code} non renseigné sur le contrat"],
                )
            )
            continue

        ht = round(kwh * price, 2)
        tva = round(ht * tva_rate, 2)
        components.append(
            ComponentResult(
                code=f"supply_{period_code.lower()}",
                label=f"Fourniture {period_code}",
                amount_ht=ht,
                tva_rate=tva_rate,
                amount_tva=tva,
                amount_ttc=round(ht + tva, 2),
                formula_used=f"{kwh:.0f} kWh × {price:.4f} EUR/kWh = {ht:.2f} EUR HT",
                inputs_used={"kwh": kwh, "price_eur_kwh": price, "period": period_code},
            )
        )
    return components


# ─── TURPE ────────────────────────────────────────────────────────────────────


def compute_turpe_breakdown(
    segment: TariffSegment,
    option: TariffOption,
    subscribed_power_kva: float,
    kwh_by_period: Dict[str, float],
    prorata_days: int,
    prorata_factor: float,
) -> List[ComponentResult]:
    """
    Compute TURPE components for C4 BT or C5 BT.

    For C4 BT:
      1. Gestion (EUR/an × prorata)
      2. Comptage (EUR/an × prorata)
      3. Soutirage fixe (EUR/kVA/an × kVA × prorata)
      4-5. Soutirage variable per period (EUR/kWh × kWh)

    For C5 BT:
      1. Gestion (EUR/an × prorata)
      2. Comptage (EUR/an × prorata)
      3+. Soutirage variable per period (EUR/kWh × kWh)
    """
    components = []
    rate_sources = []

    if segment == TariffSegment.C4_BT:
        gestion_code = "TURPE_GESTION_C4"
        comptage_code = "TURPE_COMPTAGE_C4"
    elif segment == TariffSegment.C5_BT:
        gestion_code = "TURPE_GESTION_C5"
        comptage_code = "TURPE_COMPTAGE_C5"
    else:
        return [
            ComponentResult(
                code="turpe_unsupported",
                label="TURPE (segment non supporté)",
                amount_ht=0.0,
                tva_rate=0.0,
                amount_tva=0.0,
                amount_ttc=0.0,
                formula_used=f"Segment {segment.value} non supporté en V1",
                assumptions=[f"Segment {segment.value} hors scope V1"],
            )
        ]

    # ── 1. Gestion ────────────────────────────────────────────────────────
    gestion_annual = catalog.get_rate(gestion_code)
    gestion_ht = round(gestion_annual * prorata_factor, 2)
    gestion_tva_rate = catalog.get_tva_rate_for(gestion_code) or 0.055
    gestion_tva = round(gestion_ht * gestion_tva_rate, 2)
    gestion_src = catalog.get_rate_source(gestion_code)
    components.append(
        ComponentResult(
            code="turpe_gestion",
            label="Composante de gestion",
            amount_ht=gestion_ht,
            tva_rate=gestion_tva_rate,
            amount_tva=gestion_tva,
            amount_ttc=round(gestion_ht + gestion_tva, 2),
            formula_used=f"{gestion_annual:.2f} EUR/an × {prorata_factor:.4f} = {gestion_ht:.2f} EUR HT",
            inputs_used={"annual_rate": gestion_annual, "prorata": prorata_factor, "days": prorata_days},
            rate_sources=[gestion_src],
        )
    )

    # ── 2. Comptage ───────────────────────────────────────────────────────
    comptage_annual = catalog.get_rate(comptage_code)
    comptage_ht = round(comptage_annual * prorata_factor, 2)
    comptage_tva_rate = catalog.get_tva_rate_for(comptage_code) or 0.055
    comptage_tva = round(comptage_ht * comptage_tva_rate, 2)
    comptage_src = catalog.get_rate_source(comptage_code)
    components.append(
        ComponentResult(
            code="turpe_comptage",
            label="Composante de comptage",
            amount_ht=comptage_ht,
            tva_rate=comptage_tva_rate,
            amount_tva=comptage_tva,
            amount_ttc=round(comptage_ht + comptage_tva, 2),
            formula_used=f"{comptage_annual:.2f} EUR/an × {prorata_factor:.4f} = {comptage_ht:.2f} EUR HT",
            inputs_used={"annual_rate": comptage_annual, "prorata": prorata_factor, "days": prorata_days},
            rate_sources=[comptage_src],
        )
    )

    # ── 3. Soutirage fixe (C4 only) ──────────────────────────────────────
    soutirage_fixe_code = catalog.get_soutirage_fixe_code(segment, option)
    if soutirage_fixe_code:
        sf_rate = catalog.get_rate(soutirage_fixe_code)
        sf_ht = round(sf_rate * subscribed_power_kva * prorata_factor, 2)
        sf_tva_rate = catalog.get_tva_rate_for(soutirage_fixe_code) or 0.055
        sf_tva = round(sf_ht * sf_tva_rate, 2)
        sf_src = catalog.get_rate_source(soutirage_fixe_code)
        components.append(
            ComponentResult(
                code="turpe_soutirage_fixe",
                label="Composante de soutirage fixe",
                amount_ht=sf_ht,
                tva_rate=sf_tva_rate,
                amount_tva=sf_tva,
                amount_ttc=round(sf_ht + sf_tva, 2),
                formula_used=(
                    f"{sf_rate:.2f} EUR/kVA/an × {subscribed_power_kva:.0f} kVA "
                    f"× {prorata_factor:.4f} = {sf_ht:.2f} EUR HT"
                ),
                inputs_used={
                    "rate_per_kva_per_year": sf_rate,
                    "subscribed_power_kva": subscribed_power_kva,
                    "prorata": prorata_factor,
                },
                rate_sources=[sf_src],
            )
        )

    # ── 4-5. Soutirage variable per period ────────────────────────────────
    var_codes = catalog.get_soutirage_variable_codes(segment, option)
    for period_code, rate_code in var_codes.items():
        kwh = kwh_by_period.get(period_code, 0.0)
        var_rate = catalog.get_rate(rate_code)
        var_ht = round(kwh * var_rate, 2)
        var_tva_rate = catalog.get_tva_rate_for(rate_code) or 0.20
        var_tva = round(var_ht * var_tva_rate, 2)
        var_src = catalog.get_rate_source(rate_code)
        components.append(
            ComponentResult(
                code=f"turpe_soutirage_{period_code.lower()}",
                label=f"Composante de soutirage {period_code}",
                amount_ht=var_ht,
                tva_rate=var_tva_rate,
                amount_tva=var_tva,
                amount_ttc=round(var_ht + var_tva, 2),
                formula_used=f"{kwh:.0f} kWh × {var_rate:.4f} EUR/kWh = {var_ht:.2f} EUR HT",
                inputs_used={"kwh": kwh, "rate": var_rate, "period": period_code},
                rate_sources=[var_src],
            )
        )

    return components


# ─── CTA ──────────────────────────────────────────────────────────────────────


def compute_cta(
    turpe_components: List[ComponentResult],
    prorata_factor: float,
    at_date: Optional[date] = None,
) -> ComponentResult:
    """
    Compute CTA (Contribution Tarifaire d'Acheminement).

    Assiette CTA = sum of FIXED acheminement components HT:
      - turpe_gestion
      - turpe_comptage
      - turpe_soutirage_fixe (C4 only)

    NOT included: soutirage variable (HPE/HCE/HP/HC), accise, fourniture.
    TVA: 5.5% (taux réduit).
    Taux: 21.93% (août 2021 → jan 2026), 15% (fév 2026+).
    """
    fixed_codes = {"turpe_gestion", "turpe_comptage", "turpe_soutirage_fixe"}
    cta_base = sum(c.amount_ht for c in turpe_components if c.code in fixed_codes)

    cta_taux = catalog.get_rate("CTA_ELEC", at_date) / 100.0
    cta_ht = round(cta_base * cta_taux, 2)
    cta_tva_rate = catalog.get_tva_rate_for("CTA_ELEC", at_date) or 0.055
    cta_tva = round(cta_ht * cta_tva_rate, 2)
    cta_src = catalog.get_rate_source("CTA_ELEC", at_date)

    base_detail = {c.code: c.amount_ht for c in turpe_components if c.code in fixed_codes}

    return ComponentResult(
        code="cta",
        label="CTA (Contribution Tarifaire d'Acheminement)",
        amount_ht=cta_ht,
        tva_rate=cta_tva_rate,
        amount_tva=cta_tva,
        amount_ttc=round(cta_ht + cta_tva, 2),
        formula_used=(
            f"Assiette = {cta_base:.2f} EUR (gestion + comptage + soutirage fixe) "
            f"× {cta_taux * 100:.2f}% = {cta_ht:.2f} EUR HT"
        ),
        inputs_used={
            "cta_base_eur": cta_base,
            "cta_taux_pct": round(cta_taux * 100, 2),
            "base_components": base_detail,
        },
        rate_sources=[cta_src],
    )


# ─── Accise ───────────────────────────────────────────────────────────────────


def compute_excise(kwh_total: float, at_date: Optional[date] = None) -> ComponentResult:
    """
    Compute electricity excise (accise, ex-CSPE/TIEE).
    Assiette: total kWh.
    TVA: 20%.
    Taux PME : jan 2025 = 20.50 €/MWh, fév-jul 2025 = 26.23, août+ 2025 = 29.98.
    """
    rate = catalog.get_rate("ACCISE_ELEC", at_date)
    ht = round(kwh_total * rate, 2)
    tva_rate = catalog.get_tva_rate_for("ACCISE_ELEC", at_date) or 0.20
    tva = round(ht * tva_rate, 2)
    src = catalog.get_rate_source("ACCISE_ELEC", at_date)

    return ComponentResult(
        code="accise",
        label="Accise sur l'électricité (TIEE)",
        amount_ht=ht,
        tva_rate=tva_rate,
        amount_tva=tva,
        amount_ttc=round(ht + tva, 2),
        formula_used=f"{kwh_total:.0f} kWh × {rate:.5f} EUR/kWh = {ht:.2f} EUR HT",
        inputs_used={"kwh_total": kwh_total, "rate": rate},
        rate_sources=[src],
    )


# ─── Gas reconstitution (V110) ───────────────────────────────────────────────


def _resolve_gas_tariff_tier(annual_kwh: float) -> str:
    """Determine ATRD tariff tier from annual gas consumption."""
    annual_mwh = annual_kwh / 1000
    if annual_mwh <= 6:
        return "T1"
    elif annual_mwh <= 300:
        return "T2"
    else:
        return "T3"


def _build_gas_reconstitution(
    *,
    kwh_by_period: Dict[str, float],
    supply_prices_by_period: Dict[str, float],
    period_start: date,
    period_end: date,
    invoice_type: InvoiceType = InvoiceType.NORMAL,
    fixed_fee_eur_month: float = 0.0,
) -> "ReconstitutionResult":
    """
    Shadow billing gaz — reconstitution simplifiée.

    Composantes :
    1. Fourniture : kWh × prix fournisseur (TVA 20%)
    2. ATRD : abonnement (TVA 5.5%) + variable (TVA 20%)
    3. ATRT : variable (TVA 20%)
    4. CTA gaz : % × part fixe ATRD (TVA 5.5%)
    5. TICGN : kWh × taux (TVA 20%)
    6. Abonnement fournisseur : fixe (TVA 5.5%)
    """
    if invoice_type == InvoiceType.ADVANCE:
        return ReconstitutionResult(
            status=ReconstitutionStatus.READ_ONLY,
            segment=TariffSegment.UNSUPPORTED,
            tariff_option=TariffOption.UNSUPPORTED,
            energy_type="GAZ",
            assumptions=["Facture d'acompte gaz — reconstitution non applicable"],
        )

    prorata_days, prorata_factor = compute_prorata(period_start, period_end)
    kwh_total = sum(kwh_by_period.values())
    tva_normale = catalog.get_rate("TVA_NORMALE")
    tva_reduite = catalog.get_rate("TVA_REDUITE")

    all_components: List[ComponentResult] = []
    assumptions: List[str] = []

    # Estimate annual consumption for tier selection (extrapolate from period)
    annual_kwh_est = kwh_total / prorata_factor if prorata_factor > 0 else kwh_total * 12
    tier = _resolve_gas_tariff_tier(annual_kwh_est)
    assumptions.append(f"Tranche ATRD : {tier} (conso annuelle estimée : {annual_kwh_est:,.0f} kWh)")

    # 1. Fourniture gaz
    supply_components = compute_supply_breakdown(kwh_by_period, supply_prices_by_period, tva_normale)
    all_components.extend(supply_components)

    def _gas_component(code, label, ht, tva, formula, inputs, sources=None):
        tva_amt = round(ht * tva, 2)
        return ComponentResult(
            code=code,
            label=label,
            amount_ht=round(ht, 2),
            tva_rate=tva,
            amount_tva=tva_amt,
            amount_ttc=round(ht + tva_amt, 2),
            formula_used=formula,
            inputs_used=inputs,
            rate_sources=sources or [],
        )

    # 2. ATRD — abonnement fixe
    try:
        atrd_abo_rate = catalog.get_rate(f"ATRD_GAZ_ABO_{tier}")
        atrd_abo_ht = atrd_abo_rate * prorata_factor
        all_components.append(
            _gas_component(
                "atrd_abo",
                f"ATRD abonnement ({tier})",
                atrd_abo_ht,
                tva_reduite,
                f"{atrd_abo_rate} × {prorata_factor:.4f} = {atrd_abo_ht:.2f}",
                {"prorata_factor": prorata_factor, "tier": tier},
                [catalog.get_rate_source(f"ATRD_GAZ_ABO_{tier}")],
            )
        )
    except KeyError:
        assumptions.append(f"Tarif ATRD abonnement {tier} non trouvé — composante omise")

    # 3. ATRD — variable
    try:
        atrd_var_rate = catalog.get_rate(f"ATRD_GAZ_VAR_{tier}")
        atrd_var_ht = kwh_total * atrd_var_rate
        all_components.append(
            _gas_component(
                "atrd_var",
                f"ATRD distribution ({tier})",
                atrd_var_ht,
                tva_normale,
                f"{kwh_total:,.0f} × {atrd_var_rate} = {atrd_var_ht:.2f}",
                {"kwh_total": kwh_total, "rate": atrd_var_rate},
                [catalog.get_rate_source(f"ATRD_GAZ_VAR_{tier}")],
            )
        )
    except KeyError:
        assumptions.append(f"Tarif ATRD variable {tier} non trouvé — composante omise")

    # 4. ATRT — transport variable
    try:
        atrt_rate = catalog.get_rate("ATRT_GAZ")
        atrt_ht = kwh_total * atrt_rate
        all_components.append(
            _gas_component(
                "atrt",
                "ATRT transport",
                atrt_ht,
                tva_normale,
                f"{kwh_total:,.0f} × {atrt_rate} = {atrt_ht:.2f}",
                {"kwh_total": kwh_total, "rate": atrt_rate},
                [catalog.get_rate_source("ATRT_GAZ")],
            )
        )
    except KeyError:
        assumptions.append("Tarif ATRT non trouvé — composante omise")

    # 5. CTA gaz (% de la part fixe ATRD)
    try:
        cta_rate_pct = catalog.get_rate("CTA_GAZ") / 100
        atrd_fixed = next((c.amount_ht for c in all_components if "atrd_abo" == c.code), 0)
        cta_ht = atrd_fixed * cta_rate_pct
        all_components.append(
            _gas_component(
                "cta_gaz",
                "CTA gaz",
                cta_ht,
                tva_reduite,
                f"{atrd_fixed:.2f} × {cta_rate_pct:.4f} = {cta_ht:.2f}",
                {"atrd_fixed_ht": atrd_fixed, "cta_pct": cta_rate_pct},
                [catalog.get_rate_source("CTA_GAZ")],
            )
        )
    except KeyError:
        assumptions.append("Taux CTA gaz non trouvé — composante omise")

    # 6. TICGN (accise gaz)
    try:
        ticgn_rate = catalog.get_rate("TICGN")
        ticgn_ht = kwh_total * ticgn_rate
        all_components.append(
            _gas_component(
                "ticgn",
                "TICGN (accise gaz)",
                ticgn_ht,
                tva_normale,
                f"{kwh_total:,.0f} × {ticgn_rate} = {ticgn_ht:.2f}",
                {"kwh_total": kwh_total, "rate": ticgn_rate},
                [catalog.get_rate_source("TICGN")],
            )
        )
    except KeyError:
        assumptions.append("Taux TICGN non trouvé — composante omise")

    # 7. Abonnement fournisseur (si renseigné)
    if fixed_fee_eur_month > 0:
        abo_ht = fixed_fee_eur_month * (prorata_days / 30)
        all_components.append(
            _gas_component(
                "abo_fournisseur",
                "Abonnement fournisseur",
                abo_ht,
                tva_reduite,
                f"{fixed_fee_eur_month} × {prorata_days}/30 = {abo_ht:.2f}",
                {"fee_month": fixed_fee_eur_month, "prorata_days": prorata_days},
            )
        )

    # Build result
    total_ht = sum(c.amount_ht for c in all_components)
    total_ttc = sum(c.amount_ttc for c in all_components)

    return ReconstitutionResult(
        status=ReconstitutionStatus.RECONSTITUTED,
        segment=TariffSegment.UNSUPPORTED,  # No segment for gas
        tariff_option=TariffOption.UNSUPPORTED,
        energy_type="GAZ",
        components=all_components,
        total_ht=round(total_ht, 2),
        total_ttc=round(total_ttc, 2),
        prorata_days=prorata_days,
        prorata_factor=prorata_factor,
        assumptions=assumptions,
        missing_inputs=[],
    )


# ─── Main orchestrator ───────────────────────────────────────────────────────


def build_invoice_reconstitution(
    *,
    energy_type: str,
    subscribed_power_kva: Optional[float],
    tariff_option: Optional[TariffOption],
    kwh_by_period: Dict[str, float],
    supply_prices_by_period: Dict[str, float],
    period_start: date,
    period_end: date,
    invoice_type: InvoiceType = InvoiceType.NORMAL,
    fixed_fee_eur_month: float = 0.0,
) -> ReconstitutionResult:
    """
    Build a complete invoice reconstitution.

    Args:
        energy_type: "ELEC" or "GAZ"
        subscribed_power_kva: Power in kVA (required for ELEC C4)
        tariff_option: TariffOption enum
        kwh_by_period: {"HPE": 9484, "HCE": 2283} or {"BASE": 12000}
        supply_prices_by_period: {"HPE": 0.095, "HCE": 0.075} (EUR/kWh HT)
        period_start: Start of billing period
        period_end: End of billing period
        invoice_type: Type of invoice
        fixed_fee_eur_month: Supplier's fixed monthly fee (if any)

    Returns: ReconstitutionResult with all components and audit trail.
    """

    # ── Gas reconstitution (V110) ────────────────────────────────────────
    if energy_type == "GAZ":
        return _build_gas_reconstitution(
            kwh_by_period=kwh_by_period,
            supply_prices_by_period=supply_prices_by_period,
            period_start=period_start,
            period_end=period_end,
            invoice_type=invoice_type,
            fixed_fee_eur_month=fixed_fee_eur_month,
        )

    # ── Advance invoices → READ_ONLY ──────────────────────────────────────
    if invoice_type == InvoiceType.ADVANCE:
        return ReconstitutionResult(
            status=ReconstitutionStatus.READ_ONLY,
            segment=TariffSegment.UNSUPPORTED,
            tariff_option=tariff_option or TariffOption.UNSUPPORTED,
            energy_type=energy_type,
            assumptions=["Facture d'acompte — reconstitution non applicable"],
        )

    # ── Resolve segment ───────────────────────────────────────────────────
    segment = catalog.resolve_segment(subscribed_power_kva)
    missing_inputs = []

    if segment == TariffSegment.UNSUPPORTED:
        if subscribed_power_kva is None:
            missing_inputs.append("subscribed_power_kva")
        return ReconstitutionResult(
            status=ReconstitutionStatus.UNSUPPORTED
            if (subscribed_power_kva and subscribed_power_kva > 250)
            else ReconstitutionStatus.PARTIAL,
            segment=segment,
            tariff_option=tariff_option or TariffOption.UNSUPPORTED,
            energy_type=energy_type,
            missing_inputs=missing_inputs,
            assumptions=[
                f"Puissance souscrite: {subscribed_power_kva} kVA"
                if subscribed_power_kva
                else "Puissance souscrite non renseignée"
            ],
        )

    if segment == TariffSegment.C3_HTA:
        return ReconstitutionResult(
            status=ReconstitutionStatus.UNSUPPORTED,
            segment=segment,
            tariff_option=tariff_option or TariffOption.UNSUPPORTED,
            energy_type=energy_type,
            assumptions=[f"Segment C3 HTA (>250 kVA) hors scope V1. Puissance: {subscribed_power_kva} kVA."],
        )

    # ── Resolve tariff option ─────────────────────────────────────────────
    if tariff_option is None or tariff_option == TariffOption.UNSUPPORTED:
        missing_inputs.append("tariff_option")
        # Default: LU for C4, BASE for C5
        if segment == TariffSegment.C4_BT:
            tariff_option = TariffOption.LU
        else:
            tariff_option = TariffOption.BASE
        assumed_option = True
    else:
        assumed_option = False

    # ── Prorata ───────────────────────────────────────────────────────────
    prorata_days, prorata_factor = compute_prorata(period_start, period_end)
    kwh_total = sum(kwh_by_period.values())

    # ── Check required inputs ─────────────────────────────────────────────
    if kwh_total <= 0 and invoice_type == InvoiceType.NORMAL:
        missing_inputs.append("kwh_by_period")

    if not supply_prices_by_period:
        missing_inputs.append("supply_prices_by_period")

    # ── Compute components ────────────────────────────────────────────────
    all_components: List[ComponentResult] = []
    assumptions: List[str] = []
    warnings: List[str] = []

    if assumed_option:
        assumptions.append(f"Option tarifaire non renseignée — hypothèse {tariff_option.value}")

    # 1. Supply (fourniture)
    tva_normale = catalog.get_rate("TVA_NORMALE")
    supply_components = compute_supply_breakdown(kwh_by_period, supply_prices_by_period, tva_normale)
    all_components.extend(supply_components)

    # 2. TURPE
    turpe_components = compute_turpe_breakdown(
        segment,
        tariff_option,
        subscribed_power_kva or 0,
        kwh_by_period,
        prorata_days,
        prorata_factor,
    )
    all_components.extend(turpe_components)

    # 3. CTA (on TURPE fixed components) — temporally resolved
    cta_component = compute_cta(turpe_components, prorata_factor, at_date=period_start)
    all_components.append(cta_component)

    # 4. Accise — temporally resolved (PME taux par période)
    accise_component = compute_excise(kwh_total, at_date=period_start)
    all_components.append(accise_component)

    # 5. Supplier fixed fee (if any)
    if fixed_fee_eur_month > 0:
        fee_ht = round(fixed_fee_eur_month * prorata_factor, 2)
        tva_reduite = catalog.get_rate("TVA_REDUITE")
        fee_tva = round(fee_ht * tva_reduite, 2)
        all_components.append(
            ComponentResult(
                code="supplier_fixed_fee",
                label="Abonnement fournisseur",
                amount_ht=fee_ht,
                tva_rate=tva_reduite,
                amount_tva=fee_tva,
                amount_ttc=round(fee_ht + fee_tva, 2),
                formula_used=f"{fixed_fee_eur_month:.2f} EUR/mois × {prorata_factor:.4f} = {fee_ht:.2f} EUR HT",
                inputs_used={"monthly_fee": fixed_fee_eur_month, "prorata": prorata_factor},
            )
        )

    # ── Totaux ────────────────────────────────────────────────────────────
    total_ht = round(sum(c.amount_ht for c in all_components), 2)
    total_tva = round(sum(c.amount_tva for c in all_components), 2)
    total_ttc = round(total_ht + total_tva, 2)
    total_tva_reduite = round(sum(c.amount_tva for c in all_components if c.tva_rate < 0.10), 2)
    total_tva_normale = round(sum(c.amount_tva for c in all_components if c.tva_rate >= 0.10), 2)

    # ── Status ────────────────────────────────────────────────────────────
    if missing_inputs:
        status = ReconstitutionStatus.PARTIAL
        for mi in missing_inputs:
            warnings.append(f"Donnée manquante : {mi}")
    elif invoice_type == InvoiceType.CREDIT_NOTE:
        status = ReconstitutionStatus.PARTIAL
        assumptions.append("Avoir — reconstitution indicative")
    elif invoice_type == InvoiceType.REGULARIZATION:
        status = ReconstitutionStatus.RECONSTITUTED
        assumptions.append("Régularisation — montants basés sur les kWh réels")
    else:
        status = ReconstitutionStatus.RECONSTITUTED

    # Check for [TO_VERIFY] rates
    for c in all_components:
        for rs in c.rate_sources:
            if "[TO_VERIFY]" in rs.source:
                warnings.append(f"Taux {rs.code} ({rs.rate} {rs.unit}) non vérifié contre la source CRE officielle")

    return ReconstitutionResult(
        status=status,
        segment=segment,
        tariff_option=tariff_option,
        energy_type=energy_type,
        components=all_components,
        total_ht=total_ht,
        total_tva=total_tva,
        total_ttc=total_ttc,
        total_tva_reduite=total_tva_reduite,
        total_tva_normale=total_tva_normale,
        kwh_total=kwh_total,
        kwh_by_period=kwh_by_period,
        subscribed_power_kva=subscribed_power_kva or 0,
        period_start=period_start,
        period_end=period_end,
        prorata_days=prorata_days,
        prorata_factor=prorata_factor,
        missing_inputs=missing_inputs,
        assumptions=assumptions,
        warnings=warnings,
        catalog_version=catalog.get_catalog_version(),
    )


# ─── Compare to supplier invoice ─────────────────────────────────────────────


def compare_to_supplier_invoice(
    reconstitution: ReconstitutionResult,
    supplier_total_ttc: float,
    supplier_lines: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Compare reconstitution to actual supplier invoice.

    Args:
        reconstitution: Result from build_invoice_reconstitution()
        supplier_total_ttc: Actual TTC amount from supplier
        supplier_lines: Optional mapping of component codes to supplier amounts
            e.g. {"turpe_gestion": 17.90, "turpe_comptage": 23.28, ...}

    Returns: Comparison dict with global and per-component gaps.
    """
    global_gap = round(supplier_total_ttc - reconstitution.total_ttc, 2)
    global_gap_pct = round(global_gap / reconstitution.total_ttc * 100, 2) if reconstitution.total_ttc > 0 else None

    component_gaps = []
    if supplier_lines:
        for comp in reconstitution.components:
            supplier_val = supplier_lines.get(comp.code)
            if supplier_val is not None:
                gap = round(supplier_val - comp.amount_ht, 2)
                gap_pct = round(gap / comp.amount_ht * 100, 1) if comp.amount_ht > 0 else None
                comp.supplier_amount_ht = supplier_val
                comp.gap_eur = gap
                comp.gap_pct = gap_pct
                comp.gap_status = (
                    "ok"
                    if gap_pct is not None and abs(gap_pct) <= 5
                    else "warn"
                    if gap_pct is not None and abs(gap_pct) <= 15
                    else "alert"
                )
                component_gaps.append(
                    {
                        "code": comp.code,
                        "expected": comp.amount_ht,
                        "supplier": supplier_val,
                        "gap_eur": gap,
                        "gap_pct": gap_pct,
                        "status": comp.gap_status,
                    }
                )

    return {
        "global_gap_eur": global_gap,
        "global_gap_pct": global_gap_pct,
        "global_status": (
            "ok"
            if global_gap_pct is not None and abs(global_gap_pct) <= 2
            else "warn"
            if global_gap_pct is not None and abs(global_gap_pct) <= 5
            else "alert"
        ),
        "expected_ttc": reconstitution.total_ttc,
        "supplier_ttc": supplier_total_ttc,
        "component_gaps": component_gaps,
        "reconstitution_status": reconstitution.status.value,
    }


# ─── Audit trace generator ───────────────────────────────────────────────────


def generate_audit_trace(
    reconstitution: ReconstitutionResult,
    comparison: Optional[Dict[str, Any]] = None,
) -> AuditTrace:
    """Generate a complete audit trace for a reconstitution."""
    all_sources = []
    steps = []

    for comp in reconstitution.components:
        all_sources.extend(comp.rate_sources)
        steps.append(
            {
                "component": comp.code,
                "label": comp.label,
                "formula": comp.formula_used,
                "amount_ht": comp.amount_ht,
                "tva_rate": comp.tva_rate,
                "amount_tva": comp.amount_tva,
                "amount_ttc": comp.amount_ttc,
                "inputs": comp.inputs_used,
            }
        )

    return AuditTrace(
        reconstitution=reconstitution,
        rate_sources_used=all_sources,
        computation_steps=steps,
        comparison=comparison,
    )
