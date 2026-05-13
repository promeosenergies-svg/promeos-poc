"""PROMEOS — Whitelist des `reason_code` v1.0.

Référence : `docs/adr/ADR-024-moteur-assujettissement.md` §3 + §8 (source-guard).

Discipline : tout `RuleApplicability.reason_code` produit par un évaluateur doit
appartenir à `REASON_CODES`. La source-guard `test_reason_codes_whitelist`
(Vague A.7) verrouille cette contrainte.

Convention de nommage :
    "{RULE}.{STATUS_HINT}"      ex. "DT.APPLICABLE", "DT.SDP_LT_1000"
    "{RULE}.DATA_MISSING_{X}"   ex. "DT.DATA_MISSING_SURFACE"

Toute extension passe par :
  1. Ajout du code ici
  2. Mise à jour de l'évaluateur correspondant
  3. Mise à jour de `REASON_CODE_TO_HUMAN` (libellé FR humain par défaut)
"""

from __future__ import annotations

from typing import Final


# Codes par règle — extensibles uniquement via ADR

_DT_REASON_CODES: Final[frozenset[str]] = frozenset(
    {
        "DT.APPLICABLE",
        "DT.NOT_APPLICABLE.SDP_LT_1000",
        "DT.NOT_APPLICABLE.USAGE_NON_TERTIARY",
        "DT.UNKNOWN.USAGE_MIXTE",
        "DT.DATA_MISSING.SURFACE",
        "DT.DATA_MISSING.USAGE",
    }
)

_BACS_REASON_CODES: Final[frozenset[str]] = frozenset(
    {
        # Phase 3.8 P1-B (audit code-reviewer P3.7) — distinction Tier 1/Tier 2.
        # L'ancien code générique "BACS.APPLICABLE" a été retiré au profit de
        # ces deux codes plus précis (garde-fou bijection Vague QQ).
        "BACS.APPLICABLE.TIER1_EXPIRED",  # > 290 kW, deadline 2025 expirée
        "BACS.APPLICABLE.TIER2_UPCOMING",  # > 70 kW, deadline 2030
        "BACS.NOT_APPLICABLE.NO_SYSTEM_GT_THRESHOLD",
        "BACS.NOT_APPLICABLE.NO_BUILDINGS",
        "BACS.DATA_MISSING.CVC_POWER",
    }
)

_APER_REASON_CODES: Final[frozenset[str]] = frozenset(
    {
        "APER.APPLICABLE.PARKING",
        "APER.APPLICABLE.TOITURE",
        "APER.NOT_APPLICABLE.PARKING_LT_1500",
        "APER.NOT_APPLICABLE.NO_ELIGIBLE_AREA",
        "APER.DATA_MISSING.PARKING_AREA",
        "APER.DATA_MISSING.ROOF_AREA",
    }
)

_SME_REASON_CODES: Final[frozenset[str]] = frozenset(
    {
        "SME.APPLICABLE.EFFECTIF",
        "SME.APPLICABLE.CA_BILAN",
        "SME.APPLICABLE.CONSO_GT_THRESHOLD",
        "SME.NOT_APPLICABLE.PME",
        "SME.DATA_MISSING.EFFECTIF",
        "SME.DATA_MISSING.CA",
        "SME.DATA_MISSING.CONSO",
    }
)

_BEGES_REASON_CODES: Final[frozenset[str]] = frozenset(
    {
        "BEGES.APPLICABLE.EFFECTIF_METROPOLE",
        "BEGES.APPLICABLE.EFFECTIF_DOM",
        "BEGES.NOT_APPLICABLE.EFFECTIF_LT_250",
        "BEGES.DATA_MISSING.EFFECTIF",
    }
)


REASON_CODES: Final[frozenset[str]] = (
    _DT_REASON_CODES | _BACS_REASON_CODES | _APER_REASON_CODES | _SME_REASON_CODES | _BEGES_REASON_CODES
)


def is_valid_reason_code(code: str) -> bool:
    """Renvoie True si `code` appartient à la whitelist v1.0."""
    return code in REASON_CODES
