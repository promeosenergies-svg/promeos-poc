"""PROMEOS — Enedis SGE domain enums.

Shared vocabulary across all sub-features (SF1 decrypt, SF2 CDC, SF3 index).
"""

from enum import Enum


class FluxType(str, Enum):
    """Type de flux SGE Enedis, identifié à partir du nom de fichier."""

    R4H = "R4H"  # CDC publiee hebdomadairement (C1-C4)
    R4M = "R4M"  # CDC publiee mensuellement (C1-C4)
    R4Q = "R4Q"  # CDC publiee quotidiennement (C1-C4)
    R171 = "R171"  # CDC journalière par PRM (C1-C4)
    R50 = "R50"  # Index mensuel (C5)
    R151 = "R151"  # Relevés trimestriels (C5)
    R172 = "R172"  # Réconciliation — binaire, hors scope parsing
    X14 = "X14"  # Hors scope
    HDM = "HDM"  # CSV chiffré PGP, hors scope
    R63 = "R63"  # Courbe de charge ponctuelle R6X/M023
    R64 = "R64"  # Index ponctuel R6X/M023
    C68 = "C68"  # Informations techniques et contractuelles
    R63A = "R63A"  # R6X recurrent — hors scope SF5
    R63B = "R63B"  # R6X recurrent — hors scope SF5
    R64A = "R64A"  # R6X recurrent — hors scope SF5
    R64B = "R64B"  # R6X recurrent — hors scope SF5
    R65 = "R65"  # R6X adjacent — hors scope SF5
    R66 = "R66"  # R6X adjacent — hors scope SF5
    R66B = "R66B"  # R6X adjacent — hors scope SF5
    R67 = "R67"  # R6X adjacent — hors scope SF5
    CR_M023 = "CR_M023"  # Compte rendu M023 — reconnu mais non parse
    UNKNOWN = "UNKNOWN"


class FluxStatus(str, Enum):
    """Statut de traitement d'un fichier flux Enedis."""

    RECEIVED = "received"
    PARSED = "parsed"
    ERROR = "error"
    SKIPPED = "skipped"
    NEEDS_REVIEW = "needs_review"
    PERMANENTLY_FAILED = "permanently_failed"


class IngestionRunStatus(str, Enum):
    """Statut d'execution d'un run d'ingestion."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
