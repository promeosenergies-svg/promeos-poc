"""
PROMEOS — Billing Explainability (Phase 2 ELEC + Phase P1 C7 multi-énergie)
Identifie les top contributeurs à l'écart TTC et génère des explications FR
adaptées à l'énergie de la facture (électricité OU gaz).

Bug racine corrigé en Bill Intelligence P1 C7 (2026-05-24, signalé live par user) :
> Une facture GAZ s'auditait avec un label "Réseau (TURPE)" — doctrinalement
> impossible (TURPE = électricité uniquement, ATRD+ATRT = gaz). Le calcul
> sous-jacent était correct (`billing_shadow_v2.py:351` utilise bien
> `ATRD_GAZ + ATRT_GAZ` pour le gaz), mais le label final était hardcodé
> "TURPE" quelle que soit l'énergie. Conséquence : décrédibilisation totale
> du moteur de vérification auprès d'un DAF qui sait que ces deux mécanismes
> tarifaires sont disjoints.

Fix : `_LABELS` et `_EXPLANATIONS` sont désormais énergie-aware. La fonction
`compute_contributors(metrics)` lit `metrics["energy_type"]` (propagé par
`shadow_billing_v2.py`) et produit des labels corrects par énergie.
"""

# Labels énergie-aware (élec = TURPE, gaz = ATRD+ATRT)
_LABELS_ELEC = {
    "fourniture": "Fourniture d'énergie",
    "reseau": "Réseau (TURPE)",
    "taxes": "Accise (CSPE / TICFE)",
    "abonnement": "Abonnement & gestion",
}

_LABELS_GAZ = {
    "fourniture": "Fourniture de gaz",
    "reseau": "Acheminement (ATRD + ATRT)",
    "taxes": "Accise (TICGN)",
    "abonnement": "Abonnement & CTA",
}


def _labels_for_energy(energy_type: str | None) -> dict[str, str]:
    """Retourne le mapping de labels adapté à l'énergie de la facture."""
    if (energy_type or "").upper() in ("GAZ", "GAS", "GAZ_NATUREL"):
        return _LABELS_GAZ
    # Défaut élec (rétro-compat : avant P1 C7, tout était labellisé élec)
    return _LABELS_ELEC


def _explanation_reseau(energy_type: str | None, d: float) -> str:
    """Explication réseau adaptée à l'énergie (TURPE vs ATRD/ATRT)."""
    if (energy_type or "").upper() in ("GAZ", "GAS", "GAZ_NATUREL"):
        return (
            "Coût acheminement (ATRD+ATRT) supérieur au tarif attendu"
            if d > 0
            else "Coût acheminement (ATRD+ATRT) inférieur au tarif attendu"
        )
    return "Coût réseau supérieur au TURPE attendu" if d > 0 else "Coût réseau inférieur au TURPE attendu"


def _explanation_taxes(energy_type: str | None, d: float) -> str:
    """Explication taxes adaptée à l'énergie."""
    label = "TICGN" if (energy_type or "").upper() in ("GAZ", "GAS", "GAZ_NATUREL") else "CSPE/TICFE"
    return (
        f"Accise {label} facturée supérieure au taux catalogue"
        if d > 0
        else f"Accise {label} facturée inférieure au taux catalogue"
    )


def _explanation_fourniture(m: dict, d: float) -> str:
    energy = (m.get("energy_type") or "").upper()
    ref = m.get("price_ref", "?")
    label = "gaz" if energy in ("GAZ", "GAS", "GAZ_NATUREL") else "énergie"
    return (
        f"Prix fourniture {label} facturé supérieur à l'attendu ({ref} €/kWh)"
        if d > 0
        else f"Prix fourniture {label} facturé inférieur à l'attendu ({ref} €/kWh)"
    )


def _explanation_abonnement(d: float) -> str:
    return "Abonnement/gestion supérieur à l'attendu" if d > 0 else "Abonnement/gestion inférieur à l'attendu"


def compute_contributors(metrics: dict) -> list:
    """
    Top 3 contributeurs à l'écart TTC, triés par |delta| décroissant.

    Lit `delta_fourniture`, `delta_reseau`, `delta_taxes` depuis metrics ;
    calcule `delta_abonnement = delta_ttc - (fourniture + reseau + taxes)`.

    Bill Intelligence P1 C7 (2026-05-24) : lit `metrics["energy_type"]`
    pour produire des labels et explications énergie-adaptées (ATRD+ATRT
    pour gaz, TURPE pour élec, TICGN vs CSPE/TICFE pour accise).

    Returns:
        list[dict] avec code, label, delta_eur, pct_of_total, explanation_fr,
        energy_type (echo, pour debug/traçabilité)
    """
    delta_ttc = metrics.get("delta_ttc", 0)
    if delta_ttc == 0:
        return []

    energy_type = metrics.get("energy_type")
    labels = _labels_for_energy(energy_type)

    explanations = {
        "fourniture": lambda m, d: _explanation_fourniture(m, d),
        "reseau": lambda m, d: _explanation_reseau(energy_type, d),
        "taxes": lambda m, d: _explanation_taxes(energy_type, d),
        "abonnement": lambda m, d: _explanation_abonnement(d),
    }

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
        explanation_fn = explanations.get(code)
        contributors.append(
            {
                "code": code,
                "label": labels.get(code, code),
                "delta_eur": round(delta, 2),
                "pct_of_total": pct,
                "explanation_fr": explanation_fn(metrics, delta) if explanation_fn else "",
                "energy_type": energy_type,  # traçabilité (debug DAF)
            }
        )
        if len(contributors) >= 3:
            break

    return contributors
