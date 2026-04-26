"""Provenance service — envelope SCM (Source · Confiance · Mis à jour).

Doctrine §5 grammaire éditoriale Sol :
    [FOOTER : SOURCE · CONFIANCE · MIS À JOUR]

Chaque endpoint REST des 7 piliers retourne `provenance` avec :
  - source : nom court du référentiel (RegOps, ADEME V23.6, EPEX, Enedis…)
  - confidence : high (calcul backend sourcé) | medium (estimation modélisée) | low (heuristique)
  - updated_at : ISO8601 timestamp dernière mise à jour
  - methodology_url : lien doc/méthodologie (optionnel)

Cf. ADR-001 grammaire Sol industrialisée — Sprint 1.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ProvenanceConfidence(str, Enum):
    """Niveaux de confiance déterministes (cf ADR-001).

    HIGH   — calcul backend sourcé sur référentiel (RegOps, ADEME V23.6,
             EPEX, Enedis SGE, JORF) avec données réelles ingérées.
    MEDIUM — estimation modélisée (modèle interne PROMEOS, archetype
             ADEME ODP, fallback contextualisé).
    LOW    — heuristique fallback faute de données suffisantes
             (couverture EMS <30%, archetype non-résolu, etc.).
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class Provenance:
    """Envelope SCM standard pour endpoints Sol.

    Frozen pour empêcher toute mutation post-build (immutabilité requise
    pour cohérence pages multi-onglets et cache frontend).
    """

    source: str
    confidence: ProvenanceConfidence = ProvenanceConfidence.MEDIUM
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    methodology_url: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # Sérialiser enum en valeur string lisible frontend
        d["confidence"] = self.confidence.value
        return d


def build_provenance(
    source: str,
    *,
    confidence: ProvenanceConfidence | str = ProvenanceConfidence.MEDIUM,
    updated_at: Optional[datetime] = None,
    methodology_url: Optional[str] = None,
) -> Provenance:
    """Helper factory pour construire une Provenance avec defaults sains.

    Accepte `confidence` comme enum ou string ("high"/"medium"/"low").
    `updated_at` peut être un datetime — converti en ISO8601 UTC.
    """
    if isinstance(confidence, str):
        confidence = ProvenanceConfidence(confidence)

    if updated_at is None:
        updated_at_iso = datetime.now(timezone.utc).isoformat()
    elif isinstance(updated_at, datetime):
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        updated_at_iso = updated_at.isoformat()
    else:
        updated_at_iso = str(updated_at)

    return Provenance(
        source=source,
        confidence=confidence,
        updated_at=updated_at_iso,
        methodology_url=methodology_url,
    )


def with_provenance(payload: dict, provenance: Provenance) -> dict:
    """Wrappe `payload` dans une envelope `{ data, provenance }`.

    Convention API Sol Sprint 1+ : tous les endpoints
    `/api/pages/{page_key}/briefing` et descendants retournent
    cette structure standardisée.

    Exemple :
        return with_provenance(
            payload={"narrative": "...", "kpis": [...], "week_cards": [...]},
            provenance=build_provenance("RegOps + ADEME V23.6", confidence="high"),
        )
    """
    return {"data": payload, "provenance": provenance.to_dict()}
