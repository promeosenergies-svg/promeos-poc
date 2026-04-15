"""
PROMEOS — Mapping des rule_ids entre les deux évaluateurs conformité.

★ Contexte — deux moteurs en parallèle (sprint V115 step 5) ★

PROMEOS dispose actuellement de DEUX évaluateurs conformité qui couvrent les
mêmes réglementations (DT, BACS, APER) avec des sémantiques divergentes :

  1. services.compliance_rules — produit `ComplianceFinding` ORM rows.
     YAML : backend/rules/decret_*_v1.yaml (packs versionnés).
     Rule IDs : DT_SCOPE, DT_OPERAT, BACS_POWER, BACS_ATTESTATION, APER_*...
     Consommé par : /api/compliance/bundle (cockpit workflow OPS).

  2. regops.engine — produit `Finding` dataclass → JSON dans RegAssessment.
     YAML : backend/regops/config/regs.yaml (référentiel centralisé).
     Rule IDs : SCOPE_UNKNOWN, OPERAT_NOT_STARTED, TRAJECTORY_*, BACS_V2_*...
     Consommé par : /api/regops/site/{id} et compliance_score_service (score A.2).

Cette divergence est un risque de dérive (un moteur devient NON_COMPLIANT alors
que l'autre reste COMPLIANT sur les mêmes données). Le sprint V115 pose les
fondations d'une fusion future :
  - Step 4 : seuils BACS unifiés via YAML partagé.
  - Step 5 (ce fichier) : mapping canonique + test de cohérence cross-moteur.

Ce module fournit :
  - CANONICAL_REGULATIONS : l'ensemble des régulations suivies.
  - RULE_ID_TO_REGULATION : lookup rule_id → regulation (couvre les 2 moteurs).
  - categorize_finding_status : convertit un statut rule_id vers une granularité
    commune {OK, ISSUE, UNKNOWN, OUT_OF_SCOPE} pour comparer les deux moteurs.

Objectif long terme (hors V115) : supprimer compliance_rules._eval_* et faire
pointer compliance_rules.evaluate_site vers regops.engine.evaluate_site avec
un adaptateur ComplianceFinding. Voir TODO dans compliance_rules.py.
"""

from __future__ import annotations


CANONICAL_REGULATIONS = frozenset(
    {
        "decret_tertiaire",
        "bacs",
        "aper",
        "dpe_tertiaire",
    }
)


# ── Lookup rule_id → regulation canonique ──────────────────────────────────
#
# Couvre les rule_ids des DEUX évaluateurs. Les rule_ids qui n'apparaissent
# que dans un seul évaluateur sont tolérés (asymétrie acceptée) tant qu'ils
# sont catégorisés par régulation.

RULE_ID_TO_REGULATION: dict[str, str] = {
    # ── Décret Tertiaire ────────────────────────────────────────────────────
    # compliance_rules pack
    "DT_SCOPE": "decret_tertiaire",
    "DT_OPERAT": "decret_tertiaire",
    "DT_TRAJECTORY_2030": "decret_tertiaire",
    "DT_TRAJECTORY_2040": "decret_tertiaire",
    "DT_ENERGY_DATA": "decret_tertiaire",
    # regops
    "SCOPE_UNKNOWN": "decret_tertiaire",
    "OUT_OF_SCOPE": "decret_tertiaire",  # ambiguïté : aussi utilisé par bacs — cf. resolve helper
    "OPERAT_NOT_STARTED": "decret_tertiaire",
    "TRAJECTORY_ON_TRACK": "decret_tertiaire",
    "TRAJECTORY_OFF_TRACK": "decret_tertiaire",
    "TRAJECTORY_NOT_EVALUABLE": "decret_tertiaire",
    "ENERGY_DATA_MISSING": "decret_tertiaire",
    "MULTI_OCCUPIED_GOVERNANCE": "decret_tertiaire",
    # ── BACS ────────────────────────────────────────────────────────────────
    # compliance_rules pack
    "BACS_POWER": "bacs",
    "BACS_HIGH_DEADLINE": "bacs",
    "BACS_LOW_DEADLINE": "bacs",
    "BACS_ATTESTATION": "bacs",
    "BACS_DEROGATION": "bacs",
    # regops + bacs_engine
    "CVC_POWER_UNKNOWN": "bacs",
    "BACS_NOT_INSTALLED": "bacs",
    "BACS_V2_OUT_OF_SCOPE": "bacs",
    "BACS_V2_OBLIGATION": "bacs",
    "BACS_V2_CLASS_INSUFFICIENT": "bacs",
    "BACS_V2_TRI_EXEMPTION": "bacs",
    "BACS_V2_TRI_NO_EXEMPTION": "bacs",
    "BACS_V2_INSPECTION_OVERDUE": "bacs",
    "BACS_V2_FULL": "bacs",
    # ── APER ────────────────────────────────────────────────────────────────
    # compliance_rules pack
    "APER_PARKING": "aper",
    "APER_TOITURE": "aper",
    "APER_PARKING_TYPE": "aper",
    # regops
    "PARKING_LARGE_APER": "aper",
    "PARKING_MEDIUM_APER": "aper",
    "PARKING_NOT_OUTDOOR": "aper",
    "ROOF_APER": "aper",
    # ── DPE Tertiaire (regops only — pas de pack compliance_rules) ──────────
    "DPE_SCOPE_UNKNOWN": "dpe_tertiaire",
    "DPE_OUT_OF_SCOPE": "dpe_tertiaire",
    "DPE_REALIZATION_MISSING": "dpe_tertiaire",
    "DPE_EXPIRED": "dpe_tertiaire",
    "DPE_COMPLIANT": "dpe_tertiaire",
}


# Statuts normalisés pour comparaison cross-moteur
STATUS_OK = "OK"
STATUS_ISSUE = "ISSUE"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_OUT_OF_SCOPE = "OUT_OF_SCOPE"


_COMPLIANCE_RULES_STATUS = {
    "OK": STATUS_OK,
    "COMPLIANT": STATUS_OK,
    "NOK": STATUS_ISSUE,
    "NON_COMPLIANT": STATUS_ISSUE,
    "AT_RISK": STATUS_ISSUE,
    "EXEMPTION_POSSIBLE": STATUS_ISSUE,
    "UNKNOWN": STATUS_UNKNOWN,
    "OUT_OF_SCOPE": STATUS_OUT_OF_SCOPE,
}


def categorize_finding_status(raw_status: str | None) -> str:
    """Normalise le statut brut d'un finding vers la granularité cross-moteur.

    Les deux moteurs utilisent des vocabulaires différents (NOK vs AT_RISK,
    COMPLIANT vs OK). Cette fonction produit 4 catégories communes pour que
    le test de cohérence puisse comparer les deux sans biais de vocabulaire.
    """
    if raw_status is None:
        return STATUS_UNKNOWN
    return _COMPLIANCE_RULES_STATUS.get(str(raw_status).upper(), STATUS_UNKNOWN)


def regulation_worst_status(rule_id_status_pairs: list[tuple[str, str]]) -> dict[str, str]:
    """Retourne le pire statut par régulation à partir d'une liste (rule_id, status).

    Règle d'agrégation : ISSUE > UNKNOWN > OUT_OF_SCOPE > OK.
    Les rule_ids non mappés sont ignorés (avec un warning implicite).
    """
    severity = {STATUS_ISSUE: 3, STATUS_UNKNOWN: 2, STATUS_OUT_OF_SCOPE: 1, STATUS_OK: 0}
    worst: dict[str, str] = {}
    for rule_id, raw_status in rule_id_status_pairs:
        reg = RULE_ID_TO_REGULATION.get(rule_id)
        if reg is None:
            continue
        normalized = categorize_finding_status(raw_status)
        current = worst.get(reg)
        if current is None or severity[normalized] > severity[current]:
            worst[reg] = normalized
    return worst
