"""Data provenance service — Source · Confiance · Mis à jour envelope.

ADR-001 grammaire Sol industrialisée : tout endpoint REST des 7 piliers
retourne `provenance: { source, confidence, updated_at, methodology_url }`
en plus de son payload `data`.
"""

from .provenance_service import (
    Provenance,
    ProvenanceConfidence,
    build_provenance,
    with_provenance,
)

__all__ = [
    "Provenance",
    "ProvenanceConfidence",
    "build_provenance",
    "with_provenance",
]
