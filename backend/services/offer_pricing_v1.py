"""
PROMEOS — Offer Pricing Engine V1 (Sprint V2)
Deterministic pricing with catalog-backed breakdown identical to shadow_v2 structure.
Components: fourniture / réseau / taxes-accises / abonnement, each with per-component TVA.
Replaces frontend hardcoded % splits with authoritative backend calculation.
"""

import logging
from datetime import date
from typing import Optional

from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH, DEFAULT_PRICE_GAZ_EUR_KWH

logger = logging.getLogger(__name__)

# ── Strategy multipliers (aligned with purchase_service.py) ──────────
STRATEGY_FACTORS = {
    "fixe": 1.05,
    "indexe": 0.95,
    "spot": 0.88,
    "hybride": 0.95,  # Default: same as indexed
}

# ── Default segment = C5 BT (< 36 kVA) ──────────────────────────────
DEFAULT_SEGMENT = "C5"


# ── Helpers ──────────────────────────────────────────────────────────


def convert_eur_mwh_to_eur_kwh(price_eur_per_mwh: float) -> float:
    """Convert €/MWh to €/kWh."""
    return price_eur_per_mwh / 1000.0


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division with zero guard."""
    if not denominator:
        return default
    return numerator / denominator


def _catalog_rate(code: str, at_date: Optional[date] = None) -> float:
    """Get rate from tax catalog with hardcoded fallback."""
    try:
        from app.referential.tax_catalog_service import get_rate

        return get_rate(code, at_date)
    except Exception:
        return _FALLBACK_RATES.get(code, 0.0)


def _catalog_trace(code: str, at_date: Optional[date] = None) -> dict:
    """Get audit trace from catalog (returns {} on failure)."""
    try:
        from app.referential.tax_catalog_service import trace

        return trace(code, at_date)
    except Exception:
        return {}


# Fallback rates — loaded from tarif_loader (YAML referentiel)
def _build_fallback_rates() -> dict:
    try:
        from config.tarif_loader import (
            get_turpe_moyen_kwh, get_turpe_gestion_mois,
            get_atrd_kwh, get_atrt_kwh,
            get_accise_kwh, get_tva_normale, get_tva_reduite,
        )
        return {
            "TURPE_ENERGIE_C5_BT": get_turpe_moyen_kwh("C5_BT"),
            "TURPE_GESTION_C5_BT": get_turpe_gestion_mois("C5_BT"),
            "ATRD_GAZ": get_atrd_kwh(),
            "ATRT_GAZ": get_atrt_kwh(),
            "ACCISE_ELEC": get_accise_kwh("elec"),
            "ACCISE_GAZ": get_accise_kwh("gaz"),
            "TVA_NORMALE": get_tva_normale(),
            "TVA_REDUITE": get_tva_reduite(),
            "DEFAULT_PRICE_ELEC": DEFAULT_PRICE_ELEC_EUR_KWH,
            "DEFAULT_PRICE_GAZ": DEFAULT_PRICE_GAZ_EUR_KWH,
        }
    except Exception:
        return {
            "TURPE_ENERGIE_C5_BT": 0.0453,
            "TURPE_GESTION_C5_BT": 18.48,
            "ATRD_GAZ": 0.025,
            "ATRT_GAZ": 0.012,
            "ACCISE_ELEC": 0.0225,
            "ACCISE_GAZ": 0.01637,
            "TVA_NORMALE": 0.20,
            "TVA_REDUITE": 0.055,
            "DEFAULT_PRICE_ELEC": DEFAULT_PRICE_ELEC_EUR_KWH,
            "DEFAULT_PRICE_GAZ": DEFAULT_PRICE_GAZ_EUR_KWH,
        }

_FALLBACK_RATES = _build_fallback_rates()


# ── Main engine ──────────────────────────────────────────────────────


def compute_offer_quote(
    strategy: str,
    energy_type: str = "elec",
    consumption_kwh: float = 0.0,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    price_ref_eur_per_kwh: Optional[float] = None,
    price_ref_eur_per_mwh: Optional[float] = None,
    fixed_fee_eur_per_month: float = 0.0,
    segment: str = DEFAULT_SEGMENT,
    invoice_date: Optional[date] = None,
) -> dict:
    """
    Compute a deterministic offer quote with structured breakdown.

    Args:
        strategy: "fixe" | "indexe" | "spot" | "hybride"
        energy_type: "elec" | "gaz"
        consumption_kwh: kWh for the period
        period_start/end: billing period (for prorata)
        price_ref_eur_per_kwh: reference price in €/kWh (priority)
        price_ref_eur_per_mwh: reference price in €/MWh (converted if kwh not set)
        fixed_fee_eur_per_month: monthly fixed fee from contract
        segment: tariff segment (C5 default)
        invoice_date: date for catalog rate lookup

    Returns:
        OfferQuoteResult: { components[], totals{}, meta{} }
    """
    strategy_lower = strategy.lower()
    is_elec = energy_type.lower() == "elec"
    kwh = max(consumption_kwh, 0.0)
    at_date = invoice_date or date.today()

    # ── Resolve reference price ──────────────────────────────────
    if price_ref_eur_per_kwh and price_ref_eur_per_kwh > 0:
        base_price = price_ref_eur_per_kwh
    elif price_ref_eur_per_mwh and price_ref_eur_per_mwh > 0:
        base_price = convert_eur_mwh_to_eur_kwh(price_ref_eur_per_mwh)
    else:
        base_price = _catalog_rate("DEFAULT_PRICE_ELEC" if is_elec else "DEFAULT_PRICE_GAZ", at_date)

    # Apply strategy factor
    factor = STRATEGY_FACTORS.get(strategy_lower, 1.0)
    offer_price = base_price * factor

    # ── Prorata factor ───────────────────────────────────────────
    if period_start and period_end:
        days_in_period = max((period_end - period_start).days, 1)
    else:
        days_in_period = 30
    prorata_factor = days_in_period / 30.0

    # ── TVA rates ────────────────────────────────────────────────
    tva_normal = _catalog_rate("TVA_NORMALE", at_date)
    tva_reduit = _catalog_rate("TVA_REDUITE", at_date)

    # ── Component rates from catalog ─────────────────────────────
    if is_elec:
        turpe_energie = _catalog_rate("TURPE_ENERGIE_C5_BT", at_date)
        turpe_gestion = _catalog_rate("TURPE_GESTION_C5_BT", at_date)
        accise = _catalog_rate("ACCISE_ELEC", at_date)
    else:
        turpe_energie = _catalog_rate("ATRD_GAZ", at_date) + _catalog_rate("ATRT_GAZ", at_date)
        turpe_gestion = 0.0
        accise = _catalog_rate("ACCISE_GAZ", at_date)

    # ── HT components ────────────────────────────────────────────
    ht_fourniture = kwh * offer_price
    ht_reseau = kwh * turpe_energie
    ht_taxes = kwh * accise
    ht_abo = (turpe_gestion + fixed_fee_eur_per_month) * prorata_factor

    # ── TVA per component ────────────────────────────────────────
    tva_fourniture = ht_fourniture * tva_normal
    tva_reseau = ht_reseau * tva_normal
    tva_taxes = ht_taxes * tva_normal
    tva_abo = ht_abo * tva_reduit

    total_ht = ht_fourniture + ht_reseau + ht_taxes + ht_abo
    total_tva = tva_fourniture + tva_reseau + tva_taxes + tva_abo
    total_ttc = total_ht + total_tva

    # ── Build structured result ──────────────────────────────────
    components = [
        {
            "code": "fourniture",
            "label": "Fourniture d'énergie",
            "ht": round(ht_fourniture, 2),
            "tva_rate": tva_normal,
            "tva": round(tva_fourniture, 2),
            "ttc": round(ht_fourniture + tva_fourniture, 2),
            "qty": kwh,
            "unit_rate": round(offer_price, 6),
            "unit": "EUR/kWh",
            "trace": _catalog_trace("DEFAULT_PRICE_ELEC" if is_elec else "DEFAULT_PRICE_GAZ", at_date)
            if not price_ref_eur_per_kwh
            else {"source": "contract_or_input"},
        },
        {
            "code": "reseau",
            "label": "Réseau (TURPE)" if is_elec else "Réseau (ATRD+ATRT)",
            "ht": round(ht_reseau, 2),
            "tva_rate": tva_normal,
            "tva": round(tva_reseau, 2),
            "ttc": round(ht_reseau + tva_reseau, 2),
            "qty": kwh,
            "unit_rate": round(turpe_energie, 6),
            "unit": "EUR/kWh",
            "trace": _catalog_trace("TURPE_ENERGIE_C5_BT" if is_elec else "ATRD_GAZ", at_date),
        },
        {
            "code": "taxes",
            "label": "Accise électricité (TIEE)" if is_elec else "Accise gaz (TICGN)",
            "ht": round(ht_taxes, 2),
            "tva_rate": tva_normal,
            "tva": round(tva_taxes, 2),
            "ttc": round(ht_taxes + tva_taxes, 2),
            "qty": kwh,
            "unit_rate": round(accise, 6),
            "unit": "EUR/kWh",
            "trace": _catalog_trace("ACCISE_ELEC" if is_elec else "ACCISE_GAZ", at_date),
        },
        {
            "code": "abonnement",
            "label": "Abonnement & gestion",
            "ht": round(ht_abo, 2),
            "tva_rate": tva_reduit,
            "tva": round(tva_abo, 2),
            "ttc": round(ht_abo + tva_abo, 2),
            "qty": round(prorata_factor, 4),
            "unit_rate": round(turpe_gestion + fixed_fee_eur_per_month, 2),
            "unit": "EUR/mois",
            "trace": _catalog_trace("TURPE_GESTION_C5_BT", at_date) if is_elec else {},
        },
    ]

    totals = {
        "ht": round(total_ht, 2),
        "tva": round(total_tva, 2),
        "ttc": round(total_ttc, 2),
    }

    meta = {
        "strategy": strategy_lower,
        "strategy_factor": factor,
        "energy_type": energy_type.upper(),
        "segment": segment,
        "base_price_eur_kwh": round(base_price, 6),
        "offer_price_eur_kwh": round(offer_price, 6),
        "consumption_kwh": kwh,
        "days_in_period": days_in_period,
        "prorata_factor": round(prorata_factor, 4),
        "fixed_fee_eur_per_month": fixed_fee_eur_per_month,
        "model_version": "offer_v1",
    }

    return {
        "components": components,
        "totals": totals,
        "meta": meta,
    }


def compute_multi_strategy_quotes(
    energy_type: str = "elec",
    consumption_kwh: float = 0.0,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    price_ref_eur_per_kwh: Optional[float] = None,
    fixed_fee_eur_per_month: float = 0.0,
    invoice_date: Optional[date] = None,
) -> dict:
    """
    Compute quotes for all strategies (FIXE/INDEXE/SPOT) in one call.
    Returns { strategies: { fixe: QuoteResult, indexe: ..., spot: ... }, comparison: {...} }
    """
    strategies = {}
    for strat in ["fixe", "indexe", "spot"]:
        strategies[strat] = compute_offer_quote(
            strategy=strat,
            energy_type=energy_type,
            consumption_kwh=consumption_kwh,
            period_start=period_start,
            period_end=period_end,
            price_ref_eur_per_kwh=price_ref_eur_per_kwh,
            fixed_fee_eur_per_month=fixed_fee_eur_per_month,
            invoice_date=invoice_date,
        )

    # Build comparison summary
    comparison = {}
    for strat, quote in strategies.items():
        comparison[strat] = {
            "ttc": quote["totals"]["ttc"],
            "ht": quote["totals"]["ht"],
            "strategy_factor": quote["meta"]["strategy_factor"],
            "offer_price_eur_kwh": quote["meta"]["offer_price_eur_kwh"],
        }

    return {
        "strategies": strategies,
        "comparison": comparison,
        "meta": {
            "energy_type": energy_type.upper(),
            "consumption_kwh": consumption_kwh,
            "model_version": "offer_v1",
        },
    }
