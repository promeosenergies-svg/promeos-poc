"""PROMEOS — Types canoniques du moteur d'assujettissement v1.0.

Référence : `docs/adr/ADR-024-moteur-assujettissement.md` §1.

Trois types figés :
    RuleCode             — enum des 5 règles cataloguées
    ApplicabilityStatus  — enum des 4 statuts cardinaux
    RuleApplicability    — dataclass immuable (frozen=True) avec traçabilité
                           complète (reason_human + reason_code + _audit)

L'immutabilité est imposée pour interdire les mutations downstream (un builder
ne doit jamais "corriger" un statut au vol). Toute modification passe par
recréation explicite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import Any


DOCTRINE_VERSION = "ADR-024-v1.0"


class RuleCode(StrEnum):
    """Codes des règles cataloguées v1.0 (cf. ADR-024 §4)."""

    DT = "DT"  # Décret tertiaire 2019-771
    BACS = "BACS"  # Décrets 2020-887 + 2025-1343
    APER = "APER"  # Loi 2023-175 art. 40 (parkings ≥ 1 500 m² + ombrières)
    SME = "SME"  # Audit énergétique obligatoire (Code énergie L233-1)
    BEGES = "BEGES"  # Bilan GES réglementaire (Grenelle 2 art. 75)


class ApplicabilityStatus(StrEnum):
    """Statut d'applicabilité d'une règle sur un scope donné.

    APPLICABLE      — la règle s'applique, action/trajectoire visible
    NOT_APPLICABLE  — la règle ne s'applique pas, masquée ou grisée
    UNKNOWN         — statut indéterminable, bandeau "à clarifier"
    DATA_MISSING    — champs patrimoine manquants, CTA "renseigner"
    """

    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"
    DATA_MISSING = "data_missing"


# Niveaux de scope canoniques (cf. ADR-024 §2 — site-scoped vs org-scoped)
SCOPE_LEVELS: frozenset[str] = frozenset({"site", "organisation", "portefeuille"})


@dataclass(frozen=True)
class RuleApplicability:
    """Verdict typé d'applicabilité d'une règle sur un scope donné.

    Champs cardinaux (ordre figé Phase 0 v1.0 Amine) :
        rule_code        — la règle évaluée (RuleCode)
        rule_version     — version normative de l'évaluateur (chaîne datée)
        scope_level      — "site" | "organisation" | "portefeuille"
        scope_id         — identifiant du scope (None si scope organisationnel implicite)
        scope_label      — libellé humain ("Site Toulouse Entrepôt", "Organisation HELIOS SAS")
        status           — ApplicabilityStatus
        reason_code      — code machine dans whitelist REASON_CODES (cf. source-guard A.7)
        reason_human     — phrase prête à afficher (i18n FR Phase 3.5)
        inputs_used      — dict des champs utilisés (ex: {"tertiaire_area_m2": 1820})
        missing_inputs   — list de noms de champs manquants si DATA_MISSING
        confidence       — float 0.0..1.0 (1.0 = certitude formelle)
        evidence_refs    — list de pointeurs (ex: ["NOR:TREL1908035D", "AuditSME#42"])
        next_review_date — prochaine échéance de réévaluation (révision normative)
        deadline         — échéance réglementaire si APPLICABLE (sinon None)
        _audit           — traçabilité doctrine_version + evaluated_at + evaluator
                           + evaluator_version + data_source

    Discipline immutabilité : `frozen=True`. Toute mutation lève
    `dataclasses.FrozenInstanceError`. Pour "corriger" un verdict, recréer.
    """

    rule_code: RuleCode
    rule_version: str
    scope_level: str
    scope_id: int | None
    scope_label: str
    status: ApplicabilityStatus
    reason_code: str
    reason_human: str
    inputs_used: dict[str, Any] = field(default_factory=dict)
    missing_inputs: list[str] = field(default_factory=list)
    confidence: float = 1.0
    evidence_refs: list[str] = field(default_factory=list)
    next_review_date: date | None = None
    deadline: date | None = None
    _audit: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.scope_level not in SCOPE_LEVELS:
            raise ValueError(f"scope_level invalide: {self.scope_level!r}. Attendu un de {sorted(SCOPE_LEVELS)}.")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence doit être dans [0.0, 1.0], reçu {self.confidence!r}.")
        if self.status == ApplicabilityStatus.DATA_MISSING and not self.missing_inputs:
            raise ValueError("DATA_MISSING exige missing_inputs non vide (cf. ADR-024 §8 source-guard).")
        required_audit_keys = {
            "doctrine_version",
            "evaluated_at",
            "evaluator",
            "evaluator_version",
            "data_source",
        }
        missing_audit = required_audit_keys - set(self._audit.keys())
        if missing_audit:
            raise ValueError(
                f"_audit incomplet: clés manquantes {sorted(missing_audit)}. Requises: {sorted(required_audit_keys)}."
            )

    def to_dict(self) -> dict[str, Any]:
        """Sérialisation JSON-ready pour le payload endpoint."""
        return {
            "rule_code": self.rule_code.value,
            "rule_version": self.rule_version,
            "scope_level": self.scope_level,
            "scope_id": self.scope_id,
            "scope_label": self.scope_label,
            "status": self.status.value,
            "reason_code": self.reason_code,
            "reason_human": self.reason_human,
            "inputs_used": dict(self.inputs_used),
            "missing_inputs": list(self.missing_inputs),
            "confidence": self.confidence,
            "evidence_refs": list(self.evidence_refs),
            "next_review_date": self.next_review_date.isoformat() if self.next_review_date else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "_audit": dict(self._audit),
        }
