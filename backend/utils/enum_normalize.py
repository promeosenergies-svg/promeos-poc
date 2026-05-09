"""
PROMEOS — Helper SoT cardinal : normalisation Enum SQLAlchemy / String column / None.

Phase L2.1 — extraction du helper anciennement dupliqué dans :
- `services/bill_intelligence/anomaly_detector.py:_normalize_enum_value` (Phase K2)
- `routes/cockpit.py:_statut_dt_value` (legacy)
- `routes/cockpit.py:1466` inline (cockpit_decisions_top3)

Pattern Pilier 13 ADR-016 (SoT cross-services centralisé) : tous les services
qui doivent comparer une valeur de colonne stockée parfois comme Enum SQLAlchemy
(ex: `Site.statut_decret_tertiaire`) parfois comme String (ex: `DeliveryPoint.
accise_categorie_elec` declared as String(30) avec validator Enum) utilisent
ce helper unique.
"""

from __future__ import annotations

from typing import Optional


def normalize_enum_value(raw) -> Optional[str]:
    """Normalise un Enum SQLAlchemy ou colonne String en valeur string canonique.

    Gère 3 cas cardinal :
    - `Enum.value` (instance Enum SQLAlchemy) → renvoie `.value`
    - String raw (column String avec validator Enum) → renvoie tel quel
    - None / vide → renvoie None

    Args:
        raw: Enum instance, str, None, ou autre valeur

    Returns:
        str canonique (ex: "PME", "MENAGES_ASSIMILES", "CONFORME") ou None

    Examples:
        >>> from models.enums import AcciseCategorieElec
        >>> normalize_enum_value(AcciseCategorieElec.PME)
        'PME'
        >>> normalize_enum_value("PME")
        'PME'
        >>> normalize_enum_value(None)
        None
    """
    if raw is None:
        return None
    return raw.value if hasattr(raw, "value") else str(raw)
