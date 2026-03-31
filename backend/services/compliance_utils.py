"""
PROMEOS — Fonctions utilitaires conformité (extraites de compliance_engine.py)

Fonctions pures de calcul : statuts, risque financier, actions recommandées,
deadlines BACS. Aucune dépendance DB.
"""

from datetime import date
from typing import List, Optional

from models import Obligation, Evidence, StatutConformite, TypeObligation, TypeEvidence, StatutEvidence
from config.emission_factors import (
    BASE_PENALTY_EURO,
    A_RISQUE_PENALTY_EURO,
    BACS_SEUIL_HAUT,
    BACS_SEUIL_BAS,
)

# Status severity ranking for "worst status" logic
_STATUS_SEVERITY = {
    StatutConformite.CONFORME: 0,
    StatutConformite.DEROGATION: 1,
    StatutConformite.A_RISQUE: 2,
    StatutConformite.NON_CONFORME: 3,
}

BACS_DEADLINE_290 = date(2025, 1, 1)
BACS_DEADLINE_70 = date(2030, 1, 1)

# Action text templates ordered by priority (highest first)
_ACTION_TEMPLATES = [
    (TypeObligation.BACS, StatutConformite.NON_CONFORME, "Installer GTB/GTC conforme (BACS obligatoire)"),
    (TypeObligation.DECRET_TERTIAIRE, StatutConformite.NON_CONFORME, "Audit decret tertiaire - trajectoire 2030 KO"),
    (TypeObligation.BACS, StatutConformite.A_RISQUE, "Planifier mise en conformite BACS avant echeance"),
    (TypeObligation.DECRET_TERTIAIRE, StatutConformite.A_RISQUE, "Verifier trajectoire decret tertiaire"),
]


def worst_status(obligations: List[Obligation]) -> Optional[StatutConformite]:
    """Return the worst (most severe) status from a list of obligations."""
    if not obligations:
        return None
    return max(obligations, key=lambda o: _STATUS_SEVERITY[o.statut]).statut


def _worst_from_statuts(statuts: List[StatutConformite]) -> Optional[StatutConformite]:
    """Return the worst status from a plain list of StatutConformite values."""
    if not statuts:
        return None
    return max(statuts, key=lambda s: _STATUS_SEVERITY[s])


def average_avancement(obligations: List[Obligation]) -> float:
    """Return the average avancement_pct across obligations."""
    if not obligations:
        return 0.0
    return round(sum(o.avancement_pct for o in obligations) / len(obligations), 1)


def compute_risque_financier(obligations: List[Obligation]) -> float:
    """Calculate financial risk: NON_CONFORME = 100% penalty, A_RISQUE = 50% penalty."""
    non_conforme_count = sum(1 for o in obligations if o.statut == StatutConformite.NON_CONFORME)
    a_risque_count = sum(1 for o in obligations if o.statut == StatutConformite.A_RISQUE)
    return round(BASE_PENALTY_EURO * non_conforme_count + A_RISQUE_PENALTY_EURO * a_risque_count, 2)


def compute_action_recommandee(obligations: List[Obligation]) -> Optional[str]:
    """Return the highest-priority recommended action."""
    for ob_type, ob_statut, action_text in _ACTION_TEMPLATES:
        for o in obligations:
            if o.type == ob_type and o.statut == ob_statut:
                return action_text
    return None


def bacs_deadline_for_power(cvc_power_kw: float) -> Optional[date]:
    """Return the BACS regulatory deadline based on CVC power.

    >290 kW -> 2025-01-01
    >70 kW  -> 2030-01-01
    <=70 kW -> None (not concerned)
    """
    if cvc_power_kw > BACS_SEUIL_HAUT:
        return BACS_DEADLINE_290
    if cvc_power_kw > BACS_SEUIL_BAS:
        return BACS_DEADLINE_70
    return None


def compute_bacs_statut(
    evidences: List[Evidence],
    echeance: date,
    today: Optional[date] = None,
) -> StatutConformite:
    """
    Compute BACS obligation statut from evidences and deadline.

    Priority:
    1. Valid DEROGATION_BACS evidence  -> DEROGATION
    2. Valid ATTESTATION_BACS evidence -> CONFORME
    3. Deadline passed (today > echeance) -> NON_CONFORME
    4. Otherwise -> A_RISQUE
    """
    if today is None:
        today = date.today()

    bacs_evidences = [e for e in evidences if e.type in (TypeEvidence.ATTESTATION_BACS, TypeEvidence.DEROGATION_BACS)]

    has_valid_derogation = any(
        e.type == TypeEvidence.DEROGATION_BACS and e.statut == StatutEvidence.VALIDE for e in bacs_evidences
    )
    if has_valid_derogation:
        return StatutConformite.DEROGATION

    has_valid_attestation = any(
        e.type == TypeEvidence.ATTESTATION_BACS and e.statut == StatutEvidence.VALIDE for e in bacs_evidences
    )
    if has_valid_attestation:
        return StatutConformite.CONFORME

    if today > echeance:
        return StatutConformite.NON_CONFORME

    return StatutConformite.A_RISQUE
