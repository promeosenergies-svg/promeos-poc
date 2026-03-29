"""
PROMEOS — V99 Purchase Scenarios Service (Grand Public)

⚠️  DÉPRÉCIÉ — Ce service utilise des facteurs prix fixes (1.05/0.95/0.88).
    La source de vérité pour les scénarios achat est désormais :
      - purchase_service.py (4 stratégies market-based)
      - purchase_pricing.py (forward, spread, volatility)
    via POST /api/purchase/compute/{site_id}

    Ce service est conservé pour backward-compat (contracts_radar).
    NE PAS ajouter de nouvelles logiques ici.
"""

from sqlalchemy.orm import Session

from models import EnergyContract
from models.billing_models import EnergyInvoice


SCENARIO_TEMPLATES = {
    "A": {
        "id": "A",
        "label": "Renouveler à prix fixe",
        "description": "Vous bloquez un prix pour toute la durée du contrat. Pas de surprise sur votre facture.",
        "risk_level": "faible",
        "risk_label": "Risque faible",
        "prerequis": [
            "Contrat actuel arrivé à échéance ou bientôt",
            "Budget prévisible souhaité",
        ],
        "avantages": [
            "Prix stable et prévisible",
            "Budget maîtrisé sur la durée",
            "Simple à comprendre",
        ],
        "inconvenients": [
            "Pas de bénéfice si les prix du marché baissent",
            "Prix généralement plus élevé qu'un contrat indexé",
        ],
        "action_templates": [
            "Demander 3 devis fournisseurs en prix fixe",
            "Comparer les offres reçues avec le prix actuel",
            "Négocier la durée d'engagement (12, 24 ou 36 mois)",
            "Vérifier les clauses de résiliation anticipée",
            "Signer le contrat avant la date limite de préavis",
        ],
        "indexation_match": "fixe",
        "price_factor": 1.05,
    },
    "B": {
        "id": "B",
        "label": "Passer en indexé marché",
        "description": "Votre prix suit l'évolution du marché de gros. Vous payez le vrai prix du moment.",
        "risk_level": "modéré",
        "risk_label": "Risque modéré",
        "prerequis": [
            "Capacité à absorber des variations de facture",
            "Suivi régulier des prix de marché",
        ],
        "avantages": [
            "Prix en moyenne plus bas qu'un fixe",
            "Transparence sur la composition du prix",
            "Flexibilité pour changer de fournisseur",
        ],
        "inconvenients": [
            "Facture variable d'un mois à l'autre",
            "Risque de hausse en cas de tension sur le marché",
        ],
        "action_templates": [
            "Analyser la volatilité de vos factures sur 12 mois",
            "Demander des offres indexées à 2-3 fournisseurs",
            "Mettre en place un suivi mensuel des coûts",
            "Définir un seuil d'alerte prix avec PROMEOS",
            "Signer le contrat avant la date limite de préavis",
        ],
        "indexation_match": "indexe",
        "price_factor": 0.95,
    },
    "C": {
        "id": "C",
        "label": "Spot + pilotage actif",
        "description": "Vous achetez au prix du marché heure par heure, avec un pilotage actif de vos consommations.",
        "risk_level": "élevé",
        "risk_label": "Risque élevé",
        "prerequis": [
            "Compteur communicant (Linky ou télérelève)",
            "Capacité de pilotage ou décalage de charges",
            "Équipe ou prestataire pour le suivi quotidien",
        ],
        "avantages": [
            "Prix potentiellement le plus bas",
            "Valorisation de la flexibilité de consommation",
            "Économies significatives si pilotage efficace",
        ],
        "inconvenients": [
            "Complexité opérationnelle forte",
            "Risque de prix très élevés en pointe",
            "Nécessite un suivi quotidien",
        ],
        "action_templates": [
            "Vérifier la compatibilité de votre compteur",
            "Évaluer votre capacité de flexibilité (report de charge)",
            "Demander une offre spot auprès de 2 fournisseurs",
            "Mettre en place un tableau de bord de suivi horaire",
            "Signer le contrat avant la date limite de préavis",
        ],
        "indexation_match": "spot",
        "price_factor": 0.88,
    },
}

# Mapping: contract indexation → matching scenario ID
_INDEXATION_TO_SCENARIO = {
    "fixe": "A",
    "indexe": "B",
    "spot": "C",
    "hybride": "B",
}


def _estimate_annual_volume(db: Session, site_id: int) -> float | None:
    """Estimate annual kWh via unified consumption service (single source of truth)."""
    from datetime import date, timedelta
    from services.consumption_unified_service import get_consumption_summary

    one_year_ago = date.today() - timedelta(days=365)
    summary = get_consumption_summary(db, site_id, one_year_ago, date.today())
    kwh = summary.get("value_kwh", 0)
    return float(kwh) if kwh else None


def compute_purchase_scenarios(db: Session, contract_id: int) -> dict:
    """Compute 3 purchase scenarios for a contract."""
    ct = db.query(EnergyContract).filter(EnergyContract.id == contract_id).first()
    if not ct:
        return {"contract_id": contract_id, "contract_summary": {}, "scenarios": []}

    current_indexation = ct.offer_indexation.value if ct.offer_indexation else None
    current_scenario_id = _INDEXATION_TO_SCENARIO.get(current_indexation)
    price_ref = ct.price_ref_eur_per_kwh

    # Estimate annual volume for cost estimation
    annual_kwh = _estimate_annual_volume(db, ct.site_id)

    contract_summary = {
        "supplier_name": ct.supplier_name,
        "energy_type": ct.energy_type.value if ct.energy_type else None,
        "end_date": ct.end_date.isoformat() if ct.end_date else None,
        "current_indexation": current_indexation,
        "price_ref_eur_per_kwh": price_ref,
        "annual_kwh_estimate": annual_kwh,
    }

    scenarios = []
    for scenario_id in ("A", "B", "C"):
        tmpl = SCENARIO_TEMPLATES[scenario_id]
        is_current = scenario_id == current_scenario_id

        # Estimate annual cost if we have price and volume
        estimate_eur = None
        if price_ref and annual_kwh:
            estimate_eur = round(price_ref * tmpl["price_factor"] * annual_kwh, 0)

        scenarios.append(
            {
                "id": tmpl["id"],
                "label": tmpl["label"],
                "description": tmpl["description"],
                "risk_level": tmpl["risk_level"],
                "risk_label": tmpl["risk_label"],
                "prerequis": tmpl["prerequis"],
                "avantages": tmpl["avantages"],
                "inconvenients": tmpl["inconvenients"],
                "recommended_actions": tmpl["action_templates"],
                "estimate_eur": estimate_eur,
                "is_current": is_current,
            }
        )

    return {
        "contract_id": contract_id,
        "contract_summary": contract_summary,
        "scenarios": scenarios,
    }
