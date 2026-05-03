"""PROMEOS — Codification doctrine traçabilité KPI (Vague 3B EPIC #274).

Règle cardinale 03/05/2026 :
    Chaque KPI exposé DOIT porter 3 attributs :
    1. `confidence`  — niveau de certitude (enum ci-dessous)
    2. `source_ref`  — référence réglementaire ou contractuelle (non-null sauf 'unavailable')
    3. `formula_text`— formule lisible par le CFO / DAF

Si aucune source n'est disponible → confidence='unavailable', valeur=None.
Jamais de valeur heuristique magique sans badge explicite.

Référence : Doctrine PROMEOS Sol §8 (info fiable), §13 (traçabilité KPI).
"""

from __future__ import annotations

from typing import Literal, Optional

# ─── Enum confidence ──────────────────────────────────────────────────────────

ConfidenceLevel = Literal[
    "calculated_regulatory",
    "calculated_contractual",
    "modeled_cee",
    "modeled_pre_audit",
    "unavailable",
]

CONFIDENCE_LEVELS: dict[str, str] = {
    "calculated_regulatory": "Calculé d'après source réglementaire",
    "calculated_contractual": "Calculé d'après contrat fournisseur",
    "modeled_cee": "Modélisé fiches CEE (à confirmer par audit énergétique réel)",
    "modeled_pre_audit": "Estimation pré-audit (heuristique sectorielle)",
    "unavailable": "Indisponible — connecter source ou lancer audit",
}

VALID_CONFIDENCE_LEVELS: frozenset[str] = frozenset(CONFIDENCE_LEVELS.keys())

# ─── Tooltip standard par niveau ─────────────────────────────────────────────

CONFIDENCE_TOOLTIP: dict[str, str] = {
    "calculated_regulatory": "Valeur calculée à partir d'une source réglementaire officielle.",
    "calculated_contractual": "Valeur calculée à partir du contrat fournisseur en vigueur.",
    "modeled_cee": ("Modélisé via fiches CEE (CEE BAT-TH-*, Code Énergie). À confirmer par un audit énergétique réel."),
    "modeled_pre_audit": (
        "Estimation heuristique sectorielle (pré-audit). Précision : ±30 %. Lancer un audit pour affiner."
    ),
    "unavailable": (
        "Données insuffisantes. Connecter votre compteur ou lancer un audit pour obtenir une valeur traçable."
    ),
}

# ─── Constructeur de KPI traçable ────────────────────────────────────────────


def make_traceable_kpi(
    value,
    confidence: ConfidenceLevel,
    source_ref: Optional[str],
    formula_text: str,
    fallback_reason: Optional[str] = None,
    unit: Optional[str] = None,
) -> dict:
    """Construit un dict KPI traçable conforme doctrine PROMEOS.

    Args:
        value         : valeur numérique ou None si indisponible
        confidence    : niveau de confiance (CONFIDENCE_LEVELS keys)
        source_ref    : référence réglementaire/contractuelle (None si unavailable)
        formula_text  : formule lisible CFO ("Σ gains × prix CRE / 1 000")
        fallback_reason: raison si value=None ("aucune_action_qualifiée", etc.)
        unit          : unité affichée ("MWh/an", "€/an", etc.)

    Returns:
        dict avec keys: value, confidence, source_ref, formula_text,
                        confidence_label, confidence_tooltip, fallback_reason, unit
    """
    if confidence not in VALID_CONFIDENCE_LEVELS:
        raise ValueError(f"confidence='{confidence}' invalide. Valeurs acceptées : {sorted(VALID_CONFIDENCE_LEVELS)}")
    if confidence != "unavailable" and source_ref is None:
        raise ValueError(
            "source_ref ne peut être None que si confidence='unavailable'. "
            "Fournir une référence réglementaire ou contractuelle."
        )
    return {
        "value": value,
        "confidence": confidence,
        "confidence_label": CONFIDENCE_LEVELS[confidence],
        "confidence_tooltip": CONFIDENCE_TOOLTIP[confidence],
        "source_ref": source_ref,
        "formula_text": formula_text,
        "fallback_reason": fallback_reason,
        "unit": unit,
    }


def unavailable_kpi(reason: str, formula_text: str = "", unit: Optional[str] = None) -> dict:
    """Retourne un KPI marqué 'unavailable' — valeur None, bouton audit affiché."""
    return make_traceable_kpi(
        value=None,
        confidence="unavailable",
        source_ref=None,
        formula_text=formula_text,
        fallback_reason=reason,
        unit=unit,
    )


__all__ = [
    "ConfidenceLevel",
    "CONFIDENCE_LEVELS",
    "VALID_CONFIDENCE_LEVELS",
    "CONFIDENCE_TOOLTIP",
    "make_traceable_kpi",
    "unavailable_kpi",
]
