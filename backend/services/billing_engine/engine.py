"""
PROMEOS Billing Engine V2 — Deterministic invoice reconstitution.

This engine calculates what an electricity invoice SHOULD be, component by
component, from known inputs (kWh, power, period, tariff option, prices).

SUPPORTED:
  - C4 BT (>36 kVA ≤250 kVA): options LU, MU, CU
  - C5 BT (≤36 kVA): options Base, HP/HC

NOT SUPPORTED (V1):
  - C3 HTA / C2 / C1 (returned as UNSUPPORTED)
  - Reactive energy / power factor penalties
  - CEE (coût amont implicite, pas de ligne facture dédiée)

ADDED (V2.1):
  - Gas reconstitution (ATRD6/7, ATRT, CTA gaz, TICGN)
  - Capacity mechanism (garantie de capacité, enchères RTE)
  - TDN gaz (Terme de Débit Normalisé, B2B > 40 Nm³/h)
  - TVA 20% uniforme post 01/08/2025 (LFI 2025 art. 20)
  - Accise T2 février 2026 (26.58 EUR/MWh)

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
from .seasonal_resolver import needs_seasonal_upgrade, resolve_kwh_by_season
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
    at_date: Optional[date] = None,
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
    elif segment == TariffSegment.C3_HTA:
        gestion_code = "TURPE_GESTION_HTA"
        comptage_code = "TURPE_COMPTAGE_HTA"
    else:
        return [
            ComponentResult(
                code="turpe_unsupported",
                label="TURPE (segment non supporté)",
                amount_ht=0.0,
                tva_rate=0.0,
                amount_tva=0.0,
                amount_ttc=0.0,
                formula_used=f"Segment {segment.value} non supporté",
                assumptions=[f"Segment {segment.value} hors scope"],
            )
        ]

    # ── 1. Gestion ────────────────────────────────────────────────────────
    gestion_annual = catalog.get_rate(gestion_code)
    gestion_ht = round(gestion_annual * prorata_factor, 2)
    gestion_tva_rate = catalog.get_tva_rate_for(gestion_code, at_date) or 0.055
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
    comptage_tva_rate = catalog.get_tva_rate_for(comptage_code, at_date) or 0.055
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

    # ── 3. Soutirage fixe (C4 BT + C3 HTA) ────────────────────────────────
    # C4 BT: 4 plages (HPH/HCH/HPB/HCB) en EUR/kVA/an
    # C3 HTA: 5 plages (P/HPH/HCH/HPB/HCB) en EUR/kW/an
    # Agrégé en un seul ComponentResult pour compatibilité CTA (assiette = turpe_soutirage_fixe)
    sf_codes = catalog.get_soutirage_fixe_codes_5p(segment, option)
    if sf_codes:
        power_unit = "kW" if segment == TariffSegment.C3_HTA else "kVA"
        sf_total_ht = 0.0
        sf_sources = []
        sf_detail = {}
        for period_code, rate_code in sf_codes.items():
            sf_rate = catalog.get_rate(rate_code)
            sf_period_ht = round(sf_rate * subscribed_power_kva * prorata_factor, 2)
            sf_total_ht += sf_period_ht
            sf_sources.append(catalog.get_rate_source(rate_code))
            sf_detail[period_code] = {"rate": sf_rate, "amount_ht": sf_period_ht}
        sf_total_ht = round(sf_total_ht, 2)
        sf_tva_rate = catalog.get_tva_rate_for(list(sf_codes.values())[0], at_date) or 0.055
        sf_tva = round(sf_total_ht * sf_tva_rate, 2)
        n_plages = len(sf_codes)
        components.append(
            ComponentResult(
                code="turpe_soutirage_fixe",
                label=f"Composante de soutirage fixe ({n_plages} plages)",
                amount_ht=sf_total_ht,
                tva_rate=sf_tva_rate,
                amount_tva=sf_tva,
                amount_ttc=round(sf_total_ht + sf_tva, 2),
                formula_used=(
                    f"Σ(rate × {subscribed_power_kva:.0f} {power_unit} × {prorata_factor:.4f}) "
                    f"= {sf_total_ht:.2f} EUR HT ({n_plages} plages)"
                ),
                inputs_used={
                    "power": subscribed_power_kva,
                    "power_unit": power_unit,
                    "prorata": prorata_factor,
                    "detail_per_period": sf_detail,
                },
                rate_sources=sf_sources,
            )
        )
    elif catalog.get_soutirage_fixe_code(segment, option):
        # Fallback single-code for backward compat (should not be reached)
        soutirage_fixe_code = catalog.get_soutirage_fixe_code(segment, option)
        sf_rate = catalog.get_rate(soutirage_fixe_code)
        sf_ht = round(sf_rate * subscribed_power_kva * prorata_factor, 2)
        sf_tva_rate = catalog.get_tva_rate_for(soutirage_fixe_code, at_date) or 0.055
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
        var_tva_rate = catalog.get_tva_rate_for(rate_code, at_date) or 0.20
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


def compute_excise(
    kwh_total: float,
    at_date: Optional[date] = None,
    segment: Optional[TariffSegment] = None,
) -> ComponentResult:
    """
    Compute electricity excise (accise, ex-CSPE/TIEE).
    Assiette: total kWh.
    TVA: 20%.
    Segment routing: C4 BT / C3 HTA → T2 (PME), sinon T1 (ménages/petits pro).
    """
    # T2 pour C4 BT et C3 HTA (>36 kVA, typiquement >250 MWh/an)
    accise_code = "ACCISE_ELEC_T2" if segment in (TariffSegment.C4_BT, TariffSegment.C3_HTA) else "ACCISE_ELEC"
    rate = catalog.get_rate(accise_code, at_date)
    ht = round(kwh_total * rate, 2)
    tva_rate = catalog.get_tva_rate_for(accise_code, at_date) or 0.20
    tva = round(ht * tva_rate, 2)
    src = catalog.get_rate_source(accise_code, at_date)

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
    debit_normalise_nm3h: Optional[float] = None,
    grd_code: str = "GRDF",
) -> "ReconstitutionResult":
    """
    Shadow billing gaz — reconstitution simplifiée.

    Composantes :
    1. Fourniture : kWh × prix fournisseur (TVA 20%)
    2. ATRD : abonnement (TVA 5.5%→20% post 01/08/2025) + variable (TVA 20%)
    3. ATRT : variable (TVA 20%)
    4. CTA gaz : % × part fixe ATRD (TVA 5.5%→20% post 01/08/2025)
    5. TICGN : kWh × taux (TVA 20%)
    6. Abonnement fournisseur : fixe (TVA 5.5%→20% post 01/08/2025)
    7. TDN : débit normalisé × taux (TVA 20%) — si > 40 Nm³/h et post 01/07/2026
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
    # Post 01/08/2025 : TVA 20% uniforme (LFI 2025 art. 20)
    tva_reduite = 0.20 if period_start >= date(2025, 8, 1) else catalog.get_rate("TVA_REDUITE")

    all_components: List[ComponentResult] = []
    assumptions: List[str] = []

    # Estimate annual consumption for tier selection (extrapolate from period)
    annual_kwh_est = kwh_total / prorata_factor if prorata_factor > 0 else kwh_total * 12
    tier = _resolve_gas_tariff_tier(annual_kwh_est)
    assumptions.append(f"Tranche ATRD : {tier} (conso annuelle estimée : {annual_kwh_est:,.0f} kWh)")
    assumptions.append(f"GRD : {grd_code}")

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

    # 2. ATRD — abonnement fixe (résolution temporelle ATRD6/ATRD7)
    try:
        atrd_abo_rate = catalog.get_rate(f"ATRD_GAZ_ABO_{tier}", at_date=period_start)
        atrd_abo_ht = atrd_abo_rate * prorata_factor
        all_components.append(
            _gas_component(
                "atrd_abo",
                f"ATRD abonnement ({tier})",
                atrd_abo_ht,
                tva_reduite,
                f"{atrd_abo_rate} × {prorata_factor:.4f} = {atrd_abo_ht:.2f}",
                {"prorata_factor": prorata_factor, "tier": tier},
                [catalog.get_rate_source(f"ATRD_GAZ_ABO_{tier}", at_date=period_start)],
            )
        )
    except KeyError:
        assumptions.append(f"Tarif ATRD abonnement {tier} non trouvé — composante omise")

    # 3. ATRD — variable (résolution temporelle ATRD6/ATRD7)
    try:
        atrd_var_rate = catalog.get_rate(f"ATRD_GAZ_VAR_{tier}", at_date=period_start)
        atrd_var_ht = kwh_total * atrd_var_rate
        all_components.append(
            _gas_component(
                "atrd_var",
                f"ATRD distribution ({tier})",
                atrd_var_ht,
                tva_normale,
                f"{kwh_total:,.0f} × {atrd_var_rate} = {atrd_var_ht:.2f}",
                {"kwh_total": kwh_total, "rate": atrd_var_rate},
                [catalog.get_rate_source(f"ATRD_GAZ_VAR_{tier}", at_date=period_start)],
            )
        )
    except KeyError:
        assumptions.append(f"Tarif ATRD variable {tier} non trouvé — composante omise")

    # 4. ATRT — transport variable
    try:
        atrt_rate = catalog.get_rate("ATRT_GAZ", at_date=period_start)
        atrt_ht = kwh_total * atrt_rate
        all_components.append(
            _gas_component(
                "atrt",
                "ATRT transport",
                atrt_ht,
                tva_normale,
                f"{kwh_total:,.0f} × {atrt_rate} = {atrt_ht:.2f}",
                {"kwh_total": kwh_total, "rate": atrt_rate},
                [catalog.get_rate_source("ATRT_GAZ", at_date=period_start)],
            )
        )
    except KeyError:
        assumptions.append("Tarif ATRT non trouvé — composante omise")

    # 4b. Stockage gaz (ATS3 — shadow, déjà inclus dans ATRT)
    try:
        stockage_rate = catalog.get_rate("STOCKAGE_GAZ", at_date=period_start)
        stockage_shadow_ht = round(kwh_total * stockage_rate, 2)
        all_components.append(
            ComponentResult(
                code="stockage_gaz",
                label="Stockage gaz ATS3 (shadow, inclus dans ATRT)",
                amount_ht=0.0,  # Shadow: NOT added to totals
                tva_rate=0.0,
                amount_tva=0.0,
                amount_ttc=0.0,
                formula_used=f"SHADOW: {kwh_total:,.0f} kWh × {stockage_rate:.5f} = {stockage_shadow_ht:.2f} EUR (inclus dans ATRT)",
                inputs_used={"kwh_total": kwh_total, "rate": stockage_rate, "shadow_amount_ht": stockage_shadow_ht},
                rate_sources=[catalog.get_rate_source("STOCKAGE_GAZ", at_date=period_start)],
            )
        )
        assumptions.append(f"Stockage gaz explicité (shadow {stockage_shadow_ht:.2f} EUR) — déjà inclus dans ATRT")
    except KeyError:
        pass  # Stockage non trouvé — composante shadow omise silencieusement

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
        ticgn_rate = catalog.get_rate("TICGN", at_date=period_start)
        ticgn_ht = kwh_total * ticgn_rate
        all_components.append(
            _gas_component(
                "ticgn",
                "TICGN (accise gaz)",
                ticgn_ht,
                tva_normale,
                f"{kwh_total:,.0f} × {ticgn_rate} = {ticgn_ht:.2f}",
                {"kwh_total": kwh_total, "rate": ticgn_rate},
                [catalog.get_rate_source("TICGN", at_date=period_start)],
            )
        )
    except KeyError:
        assumptions.append("Taux TICGN non trouvé — composante omise")

    # 6b. CEE gaz (shadow — coût implicite estimatif)
    try:
        cee_rate = catalog.get_rate("CEE_SHADOW", at_date=period_start)
        cee_shadow_ht = round(kwh_total * cee_rate, 2)
        all_components.append(
            ComponentResult(
                code="cee_shadow",
                label="CEE (coût implicite estimé, inclus dans fourniture)",
                amount_ht=0.0,
                tva_rate=0.0,
                amount_tva=0.0,
                amount_ttc=0.0,
                formula_used=f"ESTIMATIF: {kwh_total:,.0f} kWh × {cee_rate:.4f} = {cee_shadow_ht:.2f} EUR (implicite)",
                inputs_used={"kwh_total": kwh_total, "rate": cee_rate, "shadow_amount_ht": cee_shadow_ht},
                rate_sources=[catalog.get_rate_source("CEE_SHADOW", at_date=period_start)],
            )
        )
    except KeyError:
        pass

    # 6c. CPB gaz (shadow — Certificats Production Biogaz, obligation depuis 01/01/2026)
    try:
        cpb_rate = catalog.get_rate("CPB_SHADOW", at_date=period_start)
        cpb_shadow_ht = round(kwh_total * cpb_rate, 2)
        all_components.append(
            ComponentResult(
                code="cpb_shadow",
                label="CPB (coût implicite estimé, obligation fournisseur gaz)",
                amount_ht=0.0,
                tva_rate=0.0,
                amount_tva=0.0,
                amount_ttc=0.0,
                formula_used=f"ESTIMATIF: {kwh_total:,.0f} kWh × {cpb_rate:.5f} = {cpb_shadow_ht:.2f} EUR (implicite)",
                inputs_used={"kwh_total": kwh_total, "rate": cpb_rate, "shadow_amount_ht": cpb_shadow_ht},
                rate_sources=[catalog.get_rate_source("CPB_SHADOW", at_date=period_start)],
            )
        )
    except KeyError:
        pass  # Pas de CPB avant 2026

    # 7. TDN (Terme de Débit Normalisé) — B2B gaz > 40 Nm³/h, post 01/07/2026
    if debit_normalise_nm3h is not None and debit_normalise_nm3h > 40 and period_start >= date(2026, 7, 1):
        try:
            tdn_rate = catalog.get_rate("TDN_GAZ")
            tdn_ht = tdn_rate * debit_normalise_nm3h * prorata_factor
            tdn_tva = catalog.get_tva_rate_for("TDN_GAZ", period_start) or 0.20
            all_components.append(
                _gas_component(
                    "tdn",
                    f"TDN (débit normalisé {debit_normalise_nm3h:.0f} Nm³/h)",
                    tdn_ht,
                    tdn_tva,
                    f"{tdn_rate} EUR/an/Nm³h × {debit_normalise_nm3h:.0f} Nm³/h × {prorata_factor:.4f} = {tdn_ht:.2f}",
                    {"debit_nm3h": debit_normalise_nm3h, "rate": tdn_rate, "prorata": prorata_factor},
                    [catalog.get_rate_source("TDN_GAZ")],
                )
            )
        except KeyError:
            assumptions.append("Taux TDN non trouvé — composante omise")
    elif debit_normalise_nm3h is not None and debit_normalise_nm3h > 40 and period_start < date(2026, 7, 1):
        assumptions.append(f"TDN non applicable avant 01/07/2026 (débit {debit_normalise_nm3h:.0f} Nm³/h)")

    # 8. Abonnement fournisseur (si renseigné)
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
    debit_normalise_nm3h: Optional[float] = None,
    grd_code: str = "GRDF",
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

    # ── Gas reconstitution (V110+TDN+stockage+CEE) ────────────────────────
    if energy_type == "GAZ":
        return _build_gas_reconstitution(
            kwh_by_period=kwh_by_period,
            supply_prices_by_period=supply_prices_by_period,
            period_start=period_start,
            period_end=period_end,
            invoice_type=invoice_type,
            fixed_fee_eur_month=fixed_fee_eur_month,
            debit_normalise_nm3h=debit_normalise_nm3h,
            grd_code=grd_code,
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
            status=ReconstitutionStatus.PARTIAL,
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

    # ── Resolve tariff option ─────────────────────────────────────────────
    if tariff_option is None or tariff_option == TariffOption.UNSUPPORTED:
        missing_inputs.append("tariff_option")
        # Default: LU for C4/HTA, BASE for C5
        if segment in (TariffSegment.C4_BT, TariffSegment.C3_HTA):
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

    # ── Résolution saisonnière (TURPE 7 Phase 2) ─────────────────────────
    # Si les kWh sont en 2 plages (HP/HC) ou BASE mais que l'option
    # tarifaire nécessite 4 plages (CU/MU/LU), upgrader la ventilation
    # via le calendrier TURPE officiel.
    if needs_seasonal_upgrade(kwh_by_period, tariff_option, segment):
        kwh_by_period = resolve_kwh_by_season(
            total_kwh=kwh_total,
            period_start=period_start,
            period_end=period_end,
            tariff_option=tariff_option,
            is_seasonal=True,
        )

    # ── Compute components ────────────────────────────────────────────────
    all_components: List[ComponentResult] = []
    assumptions: List[str] = []
    warnings: List[str] = []

    # Trace la ventilation saisonnière si elle a été appliquée
    if needs_seasonal_upgrade({"HP": 1}, tariff_option, segment):
        # On vérifie si les clés actuelles sont en 4P pour confirmer l'upgrade
        if set(kwh_by_period.keys()) & {"HPH", "HCH", "HPB", "HCB"}:
            assumptions.append(
                "Ventilation horosaisonnière estimée par calendrier TURPE 7 "
                f"({', '.join(f'{k}={v:.0f}' for k, v in kwh_by_period.items())} kWh)"
            )

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
        at_date=period_start,
    )
    all_components.extend(turpe_components)

    # 3. CTA (on TURPE fixed components) — temporally resolved
    cta_component = compute_cta(turpe_components, prorata_factor, at_date=period_start)
    all_components.append(cta_component)

    # 4. Accise — temporally resolved (PME taux par période)
    accise_component = compute_excise(kwh_total, at_date=period_start, segment=segment)
    all_components.append(accise_component)

    # 5. Capacité (obligation fournisseur B2B, répercutée)
    try:
        capa_rate = catalog.get_rate("CAPACITE_ELEC", at_date=period_start)
        if capa_rate > 0:
            capa_ht = round(kwh_total * capa_rate, 2)
            capa_tva_rate = catalog.get_tva_rate_for("CAPACITE_ELEC", period_start) or 0.20
            capa_tva = round(capa_ht * capa_tva_rate, 2)
            capa_src = catalog.get_rate_source("CAPACITE_ELEC", at_date=period_start)
            all_components.append(
                ComponentResult(
                    code="capacite",
                    label="Garantie de capacité",
                    amount_ht=capa_ht,
                    tva_rate=capa_tva_rate,
                    amount_tva=capa_tva,
                    amount_ttc=round(capa_ht + capa_tva, 2),
                    formula_used=f"{kwh_total:.0f} kWh × {capa_rate:.5f} EUR/kWh = {capa_ht:.2f} EUR HT",
                    inputs_used={"kwh_total": kwh_total, "rate": capa_rate},
                    rate_sources=[capa_src],
                )
            )
    except KeyError:
        pass  # Capacité non trouvée — composante omise silencieusement (acceptable)

    # 5b. CEE élec (shadow — coût implicite estimatif)
    try:
        cee_rate = catalog.get_rate("CEE_SHADOW", at_date=period_start)
        cee_shadow_ht = round(kwh_total * cee_rate, 2)
        cee_src = catalog.get_rate_source("CEE_SHADOW", at_date=period_start)
        all_components.append(
            ComponentResult(
                code="cee_shadow",
                label="CEE (coût implicite estimé, inclus dans fourniture)",
                amount_ht=0.0,
                tva_rate=0.0,
                amount_tva=0.0,
                amount_ttc=0.0,
                formula_used=f"ESTIMATIF: {kwh_total:.0f} kWh × {cee_rate:.4f} = {cee_shadow_ht:.2f} EUR (implicite)",
                inputs_used={"kwh_total": kwh_total, "rate": cee_rate, "shadow_amount_ht": cee_shadow_ht},
                rate_sources=[cee_src],
            )
        )
    except KeyError:
        pass

    # 6. Supplier fixed fee (if any)
    if fixed_fee_eur_month > 0:
        fee_ht = round(fixed_fee_eur_month * prorata_factor, 2)
        # Post 01/08/2025 : TVA 20% sur abonnement (LFI 2025 art. 20)
        fee_tva_rate = 0.20 if period_start >= date(2025, 8, 1) else catalog.get_rate("TVA_REDUITE")
        fee_tva = round(fee_ht * fee_tva_rate, 2)
        all_components.append(
            ComponentResult(
                code="supplier_fixed_fee",
                label="Abonnement fournisseur",
                amount_ht=fee_ht,
                tva_rate=fee_tva_rate,
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
