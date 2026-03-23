"""PROMEOS — Enedis SGE domain enums.

Shared vocabulary across all sub-features (SF1 decrypt, SF2 CDC, SF3 index).
"""

from enum import Enum


class FluxType(str, Enum):
    """Type de flux SGE Enedis, identifié à partir du nom de fichier."""

    R4H = "R4H"  # CDC horaire agrégée (C1-C4)
    R4M = "R4M"  # CDC mensuelle agrégée (C1-C4)
    R4Q = "R4Q"  # CDC trimestrielle agrégée (C1-C4)
    R171 = "R171"  # CDC journalière par PRM (C1-C4)
    R50 = "R50"  # Index mensuel (C5)
    R151 = "R151"  # Relevés trimestriels (C5)
    R172 = "R172"  # Réconciliation — binaire, hors scope parsing
    X14 = "X14"  # Hors scope
    HDM = "HDM"  # CSV chiffré PGP, hors scope
    UNKNOWN = "UNKNOWN"
