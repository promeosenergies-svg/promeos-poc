"""
PROMEOS — Billing Explainability (Phase 2 ELEC)
Identifie les top contributeurs à l'écart TTC et génère des explications FR.
"""

_LABELS = {
    "fourniture": "Fourniture d'énergie",
    "reseau": "Réseau (TURPE)",
    "taxes": "Accise",
    "abonnement": "Abonnement & gestion",
}

_EXPLANATIONS = {
    "fourniture": lambda m, d: (
        f"Prix fourniture facturé supérieur à l'attendu ({m.get('price_ref', '?')} €/kWh)"
        if d > 0
        else f"Prix fourniture facturé inférieur à l'attendu ({m.get('price_ref', '?')} €/kWh)"
    ),
    "reseau": lambda m, d: (
        "Coût réseau supérieur au TURPE attendu" if d > 0 else "Coût réseau inférieur au TURPE attendu"
    ),
    "taxes": lambda m, d: (
        "Accise facturée supérieure au taux catalogue" if d > 0 else "Accise facturée inférieure au taux catalogue"
    ),
    "abonnement": lambda m, d: (
        "Abonnement/gestion supérieur à l'attendu" if d > 0 else "Abonnement/gestion inférieur à l'attendu"
    ),
}


def compute_contributors(metrics: dict) -> list:
    """
    Top 3 contributeurs à l'écart TTC, triés par |delta| décroissant.

    Lit delta_fourniture, delta_reseau, delta_taxes depuis metrics.
    Calcule delta_abonnement = delta_ttc - (fourniture + reseau + taxes).

    Returns:
        list[dict] avec code, label, delta_eur, pct_of_total, explanation_fr
    """
    delta_ttc = metrics.get("delta_ttc", 0)
    if delta_ttc == 0:
        return []

    components = [
        ("fourniture", metrics.get("delta_fourniture", 0)),
        ("reseau", metrics.get("delta_reseau", 0)),
        ("taxes", metrics.get("delta_taxes", 0)),
    ]
    # Abonnement delta = residual
    known_sum = sum(d for _, d in components)
    delta_abo = round(delta_ttc - known_sum, 2)
    if abs(delta_abo) > 0.01:
        components.append(("abonnement", delta_abo))

    # Filter non-zero, sort by |delta| desc, take top 3
    contributors = []
    for code, delta in sorted(components, key=lambda x: abs(x[1]), reverse=True):
        if abs(delta) < 0.01:
            continue
        pct = round(delta / delta_ttc * 100, 1) if delta_ttc else 0
        explanation_fn = _EXPLANATIONS.get(code)
        contributors.append({
            "code": code,
            "label": _LABELS.get(code, code),
            "delta_eur": round(delta, 2),
            "pct_of_total": pct,
            "explanation_fr": explanation_fn(metrics, delta) if explanation_fn else "",
        })
        if len(contributors) >= 3:
            break

    return contributors
