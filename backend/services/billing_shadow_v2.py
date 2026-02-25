"""
PROMEOS — Shadow Billing V2 (V68)
Décomposition 4 composantes : fourniture_ht, reseau_ht, taxes_ht, tva.
Tarifs POC France 2025 simplifiés (constantes publiques).
Comparaison vs lignes réelles → deltas pour R13/R14.
"""

# ── Tarifs POC France 2025 (simplifiés, source CRE / DGFiP publique) ──
TURPE_EUR_KWH_ELEC = 0.0453    # C5 BT <= 36 kVA (grille TURPE 7)
ATRD_EUR_KWH_GAZ   = 0.025     # Distribution gaz (ATRD moyen)
ATRT_EUR_KWH_GAZ   = 0.012     # Transport gaz (ATRT moyen)
CSPE_EUR_KWH_ELEC  = 0.0225    # TIEE / Accise énergie électrique 2025
TICGN_EUR_KWH_GAZ  = 0.0217    # Accise gaz naturel (TICGN 2025)
TVA_RATE_20        = 0.20


def shadow_billing_v2(invoice, lines: list, contract) -> dict:
    """
    Calcule la facture attendue sur 4 composantes et les deltas vs facturé.

    Args:
        invoice: EnergyInvoice (energy_kwh, total_eur, ...)
        lines:   liste d'EnergyInvoiceLine (line_type, amount_eur)
        contract: EnergyContract ou None

    Returns:
        dict avec expected_* + actual_* + delta_* + meta (energy_type, kwh, method)
    """
    kwh = invoice.energy_kwh or 0.0
    is_elec = (contract.energy_type.value == "elec") if contract else True
    price_ref = (
        contract.price_ref_eur_per_kwh
        if (contract and contract.price_ref_eur_per_kwh)
        else (0.18 if is_elec else 0.09)
    )

    # ── Valeurs attendues (shadow) ──
    exp_fourniture = kwh * price_ref
    exp_reseau = kwh * (
        TURPE_EUR_KWH_ELEC if is_elec else ATRD_EUR_KWH_GAZ + ATRT_EUR_KWH_GAZ
    )
    exp_taxes = kwh * (CSPE_EUR_KWH_ELEC if is_elec else TICGN_EUR_KWH_GAZ)
    exp_tva   = (exp_fourniture + exp_reseau) * TVA_RATE_20
    exp_ttc   = exp_fourniture + exp_reseau + exp_taxes + exp_tva

    # ── Valeurs réelles (depuis lignes) ──
    act_fourniture = sum(
        l.amount_eur or 0 for l in lines if l.line_type.value == "energy"
    )
    act_reseau = sum(
        l.amount_eur or 0 for l in lines if l.line_type.value == "network"
    )
    act_taxes = sum(
        l.amount_eur or 0 for l in lines if l.line_type.value == "tax"
    )
    act_ttc = invoice.total_eur or 0.0

    # ── Deltas ──
    delta_fourniture = act_fourniture - exp_fourniture
    delta_reseau     = act_reseau - exp_reseau
    delta_taxes      = act_taxes - exp_taxes
    delta_ttc        = act_ttc - exp_ttc
    delta_pct        = (delta_ttc / exp_ttc * 100) if exp_ttc else 0.0

    return {
        "expected_fourniture_ht": round(exp_fourniture, 2),
        "expected_reseau_ht":     round(exp_reseau, 2),
        "expected_taxes_ht":      round(exp_taxes, 2),
        "expected_tva":           round(exp_tva, 2),
        "expected_ttc":           round(exp_ttc, 2),
        "actual_fourniture_ht":   round(act_fourniture, 2),
        "actual_reseau_ht":       round(act_reseau, 2),
        "actual_taxes_ht":        round(act_taxes, 2),
        "actual_ttc":             round(act_ttc, 2),
        "delta_fourniture":       round(delta_fourniture, 2),
        "delta_reseau":           round(delta_reseau, 2),
        "delta_taxes":            round(delta_taxes, 2),
        "delta_ttc":              round(delta_ttc, 2),
        "delta_pct":              round(delta_pct, 2),
        "energy_type":            "ELEC" if is_elec else "GAZ",
        "kwh":                    kwh,
        "price_ref":              round(price_ref, 4),
        "method":                 "shadow_v2_simplified",
    }
