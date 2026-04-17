"""
PROMEOS — Alert to Action mapper (CX Gap #5)

Mappe chaque type d'alerte Tier-1 vers un template d'action suggéré.
Utilise les 20 ActionTemplates V113 existants — ne crée pas de nouveaux templates.
"""

from typing import Optional

# Mapping alert_type → template_key + category + default_impact_source
# Les template_key réfèrent aux ActionTemplates V113 existants.
ALERT_TO_TEMPLATE_MAP = {
    # Monitoring alerts (12 Tier-1 du PowerEngine / DataQualityEngine)
    "BASE_NUIT_ELEVEE": {
        "template_key": "programmation-horaire",
        "category": "optimisation",
        "impact_hint_eur": "savings_annual",
    },
    "WEEKEND_ANORMAL": {
        "template_key": "programmation-horaire",
        "category": "optimisation",
        "impact_hint_eur": "savings_annual",
    },
    "DERIVE_TALON": {
        "template_key": "audit-energetique",
        "category": "audit",
        "impact_hint_eur": "savings_annual",
    },
    "PIC_ANORMAL": {
        "template_key": "optimisation-puissance",
        "category": "puissance",
        "impact_hint_eur": "penalty_avoided",
    },
    "P95_HAUSSE": {
        "template_key": "optimisation-puissance",
        "category": "puissance",
        "impact_hint_eur": "penalty_avoided",
    },
    "DEPASSEMENT_PUISSANCE": {
        "template_key": "optimisation-puissance",
        "category": "puissance",
        "impact_hint_eur": "penalty_avoided",
    },
    "RUPTURE_PROFIL": {
        "template_key": "audit-energetique",
        "category": "audit",
        "impact_hint_eur": "savings_annual",
    },
    "HORS_HORAIRES": {
        "template_key": "programmation-horaire",
        "category": "optimisation",
        "impact_hint_eur": "savings_annual",
    },
    "COURBE_PLATE": {
        "template_key": "audit-energetique",
        "category": "audit",
        "impact_hint_eur": "savings_annual",
    },
    "DONNEES_MANQUANTES": {
        "template_key": "import-donnees-manquantes",
        "category": "data_quality",
        "impact_hint_eur": None,
    },
    "DOUBLONS_DST": {
        "template_key": "import-donnees-manquantes",
        "category": "data_quality",
        "impact_hint_eur": None,
    },
    "SENSIBILITE_CLIMATIQUE": {
        "template_key": "audit-energetique",
        "category": "audit",
        "impact_hint_eur": "savings_annual",
    },
    "VALEURS_NEGATIVES": {
        "template_key": "import-donnees-manquantes",
        "category": "data_quality",
        "impact_hint_eur": None,
    },
    # Compliance alerts
    "DT_A_RISQUE": {
        "template_key": "audit-conformite-dt",
        "category": "conformite",
        "impact_hint_eur": "penalty_avoided",
    },
    "BACS_MISSING": {
        "template_key": "installation-bacs",
        "category": "conformite",
        "impact_hint_eur": "penalty_avoided",
    },
    # Market alerts
    "CONTRACT_EXPIRY": {
        "template_key": "renouvellement-contrat",
        "category": "achat",
        "impact_hint_eur": "savings_annual",
    },
}


def get_suggested_action(alert_type: str, alert_context: Optional[dict] = None) -> Optional[dict]:
    """
    Retourne le template et l'impact suggérés pour un type d'alerte.

    Args:
        alert_type: type d'alerte (ex: "BASE_NUIT_ELEVEE")
        alert_context: contexte libre (site_id, estimated_penalty_eur, ...)

    Returns:
        {template_key, category, estimated_impact_eur, pre_filled_context} ou None
    """
    mapping = ALERT_TO_TEMPLATE_MAP.get(alert_type)
    if not mapping:
        return None

    ctx = alert_context or {}
    impact_eur = None
    if mapping["impact_hint_eur"] == "penalty_avoided":
        impact_eur = ctx.get("estimated_penalty_eur")
    elif mapping["impact_hint_eur"] == "savings_annual":
        impact_eur = ctx.get("estimated_savings_eur")

    return {
        "template_key": mapping["template_key"],
        "category": mapping["category"],
        "estimated_impact_eur": impact_eur,
        "pre_filled_context": ctx,
    }


def is_alert_actionable(alert_type: str) -> bool:
    """Retourne True si un template d'action existe pour ce type d'alerte."""
    return alert_type in ALERT_TO_TEMPLATE_MAP
