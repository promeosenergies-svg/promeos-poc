"""M2-5.10.C — Service Impact financier par item V4.

Doctrine PROMEOS : zéro calcul métier frontend (cf. règle d'or CLAUDE.md).
Le frontend reçoit les 4 quadrants déjà mis en forme par cette couche service.

MV3 — l'engine de scoring économique (priority_explanation R1-R6 + modèle €)
n'est pas livré (sprint M3+). Ce service expose simplement les valeurs
existantes dans `ActionCenterItem.impact_payload` (JSONB) si présent.

Structure attendue dans `impact_payload` :
    {
        "estimated": {"value_eur": 49000, "detail": "...", "formula": "...", "source": "..."},
        "at_risk":   {"value_eur": 7500,  "detail": "...", "formula": "...", "source": "..."},
        "secured":   {"value_eur": null,  "detail": "...", "formula": null,  "source": null},
        "realized":  {"value_eur": null,  "detail": "...", "formula": null,  "source": null},
    }

Fallback : si `impact_payload` est `None` ou ne contient aucun champ
quadrant, on construit une réponse 4-quadrants à `None` + `has_data=False`
(l'UI affiche alors « Impact non encore calculé pour cet item »).

Aucun calcul dérivé MV3 — pas de fallback heuristique du type
« priority_bracket × X = € ». Doctrine v0.3 : un chiffre € sans source et
sans formule est un chiffre menteur (cardinal CFO).
"""

from typing import Any, Optional

from models.v4.action_center_items import ActionCenterItem
from schemas.v4.action_center import ImpactDimension, ItemImpactResponse

_QUADRANT_KEYS: tuple[str, ...] = ("estimated", "at_risk", "secured", "realized")


def _build_dimension(raw: Optional[dict[str, Any]]) -> ImpactDimension:
    """Construit une dimension depuis un dict brut JSONB ou retourne le neutre.

    Les champs absents sont posés à `None` — c'est cohérent avec la doctrine
    UI « — » plutôt que « 0 € » menteur.
    """
    if not isinstance(raw, dict):
        return ImpactDimension()
    return ImpactDimension(
        value_eur=_coerce_float(raw.get("value_eur")),
        detail=_coerce_str(raw.get("detail"), max_len=200),
        formula=_coerce_str(raw.get("formula"), max_len=200),
        source=_coerce_str(raw.get("source"), max_len=120),
    )


def _coerce_float(value: Any) -> Optional[float]:
    """Cast défensif : `None`, `""`, `nan` → `None`."""
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    # NaN check sans import math (NaN != NaN).
    if f != f:
        return None
    return f


def _coerce_str(value: Any, *, max_len: int) -> Optional[str]:
    """Cast défensif + troncature soft."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return s[:max_len]


def build_item_impact(item: ActionCenterItem) -> ItemImpactResponse:
    """Construit la réponse Impact 4 quadrants pour un item donné.

    Source unique : `item.impact_payload` (JSONB). Si absent, retourne
    4 dimensions vides + `has_data=False`. Aucun calcul dérivé MV3.

    Le `dominant_dimension` legacy est lu depuis `item.impact_dimension`
    (1 string) — sera décommissionné M3+ au profit du payload structuré.
    """
    payload: dict[str, Any] = item.impact_payload or {}

    # Construit chaque quadrant depuis la clé correspondante (ou neutre).
    dimensions: dict[str, ImpactDimension] = {key: _build_dimension(payload.get(key)) for key in _QUADRANT_KEYS}

    # `has_data` = au moins une valeur €. Permet à l'UI de choisir entre
    # rendu cards (avec « — » sur les quadrants vides) et empty state global.
    has_data = any(d.value_eur is not None for d in dimensions.values())

    return ItemImpactResponse(
        item_id=item.id,
        period="12m",  # cardinal maquette §8.5 : période d'évaluation 12 mois
        estimated=dimensions["estimated"],
        at_risk=dimensions["at_risk"],
        secured=dimensions["secured"],
        realized=dimensions["realized"],
        dominant_dimension=_coerce_str(item.impact_dimension, max_len=20),
        has_data=has_data,
    )
