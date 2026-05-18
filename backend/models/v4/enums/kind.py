"""Kind enum — doctrine v0.3 §3.1 + ADR-025 §4.1 + L7 §3.8.

🛡️ D1 CARDINAL : 7 valeurs (PAS 3) — strict whitelist `chk_kind` CHECK constraint.

Quasi-immuable post-création (doctrine v0.3 §3.3) : modification autorisée
UNIQUEMENT via endpoint admin `PATCH /items/{id}/correct-kind` avec :
- Justification ≥ 20 chars
- Trace `action_event_log` event_type=`kind_corrected` (compliance 5y)
- Notification owner précédent

Détermine : rendu UX (Q7-A) + CTA primaire + filtres possibles.
"""

from enum import Enum


class Kind(str, Enum):
    """7 valeurs intrinsèques V4 (single-table inheritance discriminant Q1-A)."""

    ANOMALY = "anomaly"  # Écart constaté · détection auto/manuelle · CTA "Investiguer"
    ACTION = "action"  # Tâche d'exécution opérationnelle · CTA "Planifier" / "Démarrer"
    DECISION = "decision"  # Choix à arbitrer · options listées · CTA "Arbitrer"
    SIGNAL = "signal"  # Détection auto faible/moyenne confiance · CTA "Qualifier"
    EVIDENCE_REQUEST = "evidence_request"  # Demande de pièce justificative · CTA "Ajouter preuve"
    DEADLINE = "deadline"  # Obligation à échéance fixe · CTA "Préparer"
    RECOMMENDATION = "recommendation"  # Opportunité non obligatoire · CTA "Adopter" / "Refuser"

    @classmethod
    def values(cls) -> list[str]:
        """Liste des 7 valeurs string (utile pour CHECK constraint + tests)."""
        return [k.value for k in cls]

    @classmethod
    def fr_badge(cls, kind: "Kind") -> str:
        """Badge UI mode standard FR (doctrine v0.3 §7.1 + L7 §10.3)."""
        return {
            cls.ANOMALY: "ANOMALIE",
            cls.ACTION: "ACTION",
            cls.DECISION: "DÉCISION",
            cls.SIGNAL: "SIGNAL",
            cls.EVIDENCE_REQUEST: "PREUVE",
            cls.DEADLINE: "ÉCHÉANCE",
            cls.RECOMMENDATION: "RECO",
        }[kind]
