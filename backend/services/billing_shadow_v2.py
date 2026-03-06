"""
PROMEOS — Shadow Billing V2 (V68 → V100 Catalog integration)
Décomposition 5 composantes : fourniture_ht, reseau_ht, taxes_ht, abonnement_ht, tva.
Taux depuis tax_catalog.json (avec fallback hardcodé).
TVA per-composante : 20 % énergie/réseau/taxes, 5.5 % abonnement.
Prorata jours : days_in_period / 30.
Comparaison vs lignes réelles → deltas pour R13/R14.
"""

import logging

logger = logging.getLogger(__name__)

# ── Backward-compatible module-level constants (V68 tests import these) ──
TURPE_EUR_KWH_ELEC = 0.0453
ATRD_EUR_KWH_GAZ = 0.025
ATRT_EUR_KWH_GAZ = 0.012
CSPE_EUR_KWH_ELEC = 0.0225
TICGN_EUR_KWH_GAZ = 0.01637
TVA_RATE_20 = 0.20

# ── Fallback from YAML referentiel (tarifs_reglementaires.yaml) ───────
def _load_fallback() -> dict:
    """Load fallback rates from YAML referentiel, with hardcoded last resort."""
    try:
        from config.tarif_loader import (
            get_turpe_moyen_kwh, get_turpe_gestion_mois,
            get_atrd_kwh, get_atrt_kwh,
            get_accise_kwh, get_tva_normale, get_tva_reduite,
            get_prix_reference,
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
            "DEFAULT_PRICE_ELEC": get_prix_reference("elec"),
            "DEFAULT_PRICE_GAZ": get_prix_reference("gaz"),
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
            "DEFAULT_PRICE_ELEC": 0.068,
            "DEFAULT_PRICE_GAZ": 0.045,
        }

_FALLBACK = _load_fallback()


def _safe_rate(code: str, at_date=None) -> float:
    """Get rate from tax catalog with hardcoded fallback."""
    try:
        from app.referential.tax_catalog_service import get_rate

        return get_rate(code, at_date)
    except Exception:
        return _FALLBACK.get(code, 0.0)


def _safe_trace(code: str, at_date=None) -> dict:
    """Get audit trace from catalog (returns {} on failure)."""
    try:
        from app.referential.tax_catalog_service import trace

        return trace(code, at_date)
    except Exception:
        return {}


def shadow_billing_v2(invoice, lines: list, contract) -> dict:
    """
    Calcule la facture attendue sur 5 composantes avec TVA per-composante.

    Components:
      fourniture_ht : kwh × price_ref                       (TVA 20 %)
      reseau_ht     : kwh × TURPE énergie                   (TVA 20 %)
      taxes_ht      : kwh × accise                           (TVA 20 %)
      abonnement_ht : (TURPE gestion + fixed_fee) × prorata  (TVA 5.5 %)

    Args:
        invoice:  EnergyInvoice (energy_kwh, total_eur, period_start, period_end)
        lines:    liste d'EnergyInvoiceLine (line_type, amount_eur)
        contract: EnergyContract ou None

    Returns:
        dict avec expected_* + actual_* + delta_* + components[] + totals{} + meta
    """
    kwh = invoice.energy_kwh or 0.0
    is_elec = (contract.energy_type.value == "elec") if contract else True

    # ── Reference price ──────────────────────────────────────────────
    has_contract_price = contract and contract.price_ref_eur_per_kwh
    price_ref = (
        contract.price_ref_eur_per_kwh
        if has_contract_price
        else _safe_rate("DEFAULT_PRICE_ELEC" if is_elec else "DEFAULT_PRICE_GAZ")
    )
    price_source = (
        f"contract:{contract.id}" if has_contract_price else "catalog_default"
    )

    # ── Prorata factor (days in period / 30) ─────────────────────────
    p_start = getattr(invoice, "period_start", None)
    p_end = getattr(invoice, "period_end", None)
    if p_start and p_end:
        days_in_period = max((p_end - p_start).days, 1)
    else:
        days_in_period = 30
    prorata_factor = days_in_period / 30.0

    # ── TVA rates ────────────────────────────────────────────────────
    tva_normal = _safe_rate("TVA_NORMALE")
    tva_reduit = _safe_rate("TVA_REDUITE")

    # ── Component rates from catalog ─────────────────────────────────
    if is_elec:
        turpe_energie = _safe_rate("TURPE_ENERGIE_C5_BT")
        turpe_gestion = _safe_rate("TURPE_GESTION_C5_BT")
        accise = _safe_rate("ACCISE_ELEC")
    else:
        turpe_energie = _safe_rate("ATRD_GAZ") + _safe_rate("ATRT_GAZ")
        turpe_gestion = 0.0  # Simplified for gas POC
        accise = _safe_rate("ACCISE_GAZ")

    # ── Expected HT components ───────────────────────────────────────
    exp_fourniture = kwh * price_ref
    exp_reseau = kwh * turpe_energie
    exp_taxes = kwh * accise

    # Abonnement: TURPE gestion (monthly, prorated) + contract fixed fee
    fixed_fee = getattr(contract, "fixed_fee_eur_per_month", None) or 0
    exp_abo = (turpe_gestion + fixed_fee) * prorata_factor

    # ── TVA per-component ────────────────────────────────────────────
    tva_fourniture = exp_fourniture * tva_normal
    tva_reseau = exp_reseau * tva_normal
    tva_taxes = exp_taxes * tva_normal
    tva_abo = exp_abo * tva_reduit

    exp_tva = tva_fourniture + tva_reseau + tva_taxes + tva_abo
    exp_ht = exp_fourniture + exp_reseau + exp_taxes + exp_abo
    exp_ttc = exp_ht + exp_tva

    # ── Actual (from invoice lines) ──────────────────────────────────
    act_fourniture = sum(l.amount_eur or 0 for l in lines if l.line_type.value == "energy")
    act_reseau = sum(l.amount_eur or 0 for l in lines if l.line_type.value == "network")
    act_taxes = sum(l.amount_eur or 0 for l in lines if l.line_type.value == "tax")
    act_ttc = invoice.total_eur or 0.0

    # ── Deltas ───────────────────────────────────────────────────────
    delta_fourniture = act_fourniture - exp_fourniture
    delta_reseau = act_reseau - exp_reseau
    delta_taxes = act_taxes - exp_taxes
    delta_ttc = act_ttc - exp_ttc
    delta_pct = (delta_ttc / exp_ttc * 100) if exp_ttc else 0.0

    # ── Structured breakdown ─────────────────────────────────────────
    components = [
        {
            "code": "fourniture",
            "label": "Fourniture d'énergie",
            "ht": round(exp_fourniture, 2),
            "tva_rate": tva_normal,
            "tva": round(tva_fourniture, 2),
            "ttc": round(exp_fourniture + tva_fourniture, 2),
            "qty": kwh,
            "unit_rate": round(price_ref, 4),
            "unit": "EUR/kWh",
            "source": price_source,
        },
        {
            "code": "reseau",
            "label": "Réseau (TURPE)" if is_elec else "Réseau (ATRD+ATRT)",
            "ht": round(exp_reseau, 2),
            "tva_rate": tva_normal,
            "tva": round(tva_reseau, 2),
            "ttc": round(exp_reseau + tva_reseau, 2),
            "qty": kwh,
            "unit_rate": round(turpe_energie, 4),
            "unit": "EUR/kWh",
        },
        {
            "code": "taxes",
            "label": "Accise électricité (TIEE)" if is_elec else "Accise gaz (TICGN)",
            "ht": round(exp_taxes, 2),
            "tva_rate": tva_normal,
            "tva": round(tva_taxes, 2),
            "ttc": round(exp_taxes + tva_taxes, 2),
            "qty": kwh,
            "unit_rate": round(accise, 4),
            "unit": "EUR/kWh",
        },
        {
            "code": "abonnement",
            "label": "Abonnement & gestion",
            "ht": round(exp_abo, 2),
            "tva_rate": tva_reduit,
            "tva": round(tva_abo, 2),
            "ttc": round(exp_abo + tva_abo, 2),
            "qty": round(prorata_factor, 4),
            "unit_rate": round(turpe_gestion + fixed_fee, 2),
            "unit": "EUR/mois",
        },
    ]

    totals = {
        "ht": round(exp_ht, 2),
        "tva": round(exp_tva, 2),
        "ttc": round(exp_ttc, 2),
    }

    # ── Catalog audit trace ────────────────────────────────────────────
    at_date = getattr(invoice, "period_start", None)
    catalog_trace = [
        _safe_trace("TURPE_ENERGIE_C5_BT" if is_elec else "ATRD_GAZ", at_date),
        _safe_trace("ACCISE_ELEC" if is_elec else "ACCISE_GAZ", at_date),
        _safe_trace("TVA_NORMALE", at_date),
        _safe_trace("TVA_REDUITE", at_date),
    ]
    if is_elec:
        catalog_trace.append(_safe_trace("TURPE_GESTION_C5_BT", at_date))
    # Filter out empty traces (catalog unavailable)
    catalog_trace = [t for t in catalog_trace if t]

    # ── Diagnostics ─────────────────────────────────────────────────
    has_lines = len(lines) > 0
    line_types = {l.line_type.value for l in lines} if has_lines else set()
    missing_fields = []
    if exp_reseau > 0 and act_reseau == 0 and "network" not in line_types:
        missing_fields.append("network_lines")
    if exp_taxes > 0 and act_taxes == 0 and "tax" not in line_types:
        missing_fields.append("tax_lines")
    if act_fourniture == 0 and "energy" not in line_types and has_lines:
        missing_fields.append("energy_lines")

    assumptions = []
    if has_contract_price:
        cid = getattr(contract, "id", "?")
        assumptions.append(f"Prix fourniture : contrat #{cid}")
    else:
        assumptions.append("Prix fourniture : catalogue POC (pas de contrat)")
    if is_elec:
        assumptions.append("Réseau : TURPE C5 BT (profil simplifié)")
    else:
        assumptions.append("Réseau : ATRD+ATRT (profil simplifié)")

    # Confidence: high if contract+lines, medium if one, low if neither
    if has_contract_price and has_lines and len(line_types) >= 2:
        confidence = "high"
    elif has_contract_price or (has_lines and len(line_types) >= 2):
        confidence = "medium"
    else:
        confidence = "low"

    diagnostics = {
        "missing_fields": missing_fields,
        "assumptions": assumptions,
        "confidence": confidence,
    }

    # ── Backward-compatible flat fields + structured breakdown ───────
    return {
        # Flat fields (backward compat for R13/R14)
        "expected_fourniture_ht": round(exp_fourniture, 2),
        "expected_reseau_ht": round(exp_reseau, 2),
        "expected_taxes_ht": round(exp_taxes, 2),
        "expected_abo_ht": round(exp_abo, 2),
        "expected_tva": round(exp_tva, 2),
        "expected_ttc": round(exp_ttc, 2),
        "actual_fourniture_ht": round(act_fourniture, 2),
        "actual_reseau_ht": round(act_reseau, 2),
        "actual_taxes_ht": round(act_taxes, 2),
        "actual_ttc": round(act_ttc, 2),
        "delta_fourniture": round(delta_fourniture, 2),
        "delta_reseau": round(delta_reseau, 2),
        "delta_taxes": round(delta_taxes, 2),
        "delta_ttc": round(delta_ttc, 2),
        "delta_pct": round(delta_pct, 2),
        # Meta
        "energy_type": "ELEC" if is_elec else "GAZ",
        "kwh": kwh,
        "price_ref": round(price_ref, 4),
        "prorata_factor": round(prorata_factor, 4),
        "days_in_period": days_in_period,
        "method": "shadow_v2_catalog",
        "price_source": price_source,
        # Structured (new)
        "components": components,
        "totals": totals,
        # Phase 2: audit trail + diagnostics
        "catalog_trace": catalog_trace,
        "diagnostics": diagnostics,
    }
