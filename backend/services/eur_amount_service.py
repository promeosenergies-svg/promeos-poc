"""
PROMEOS — Service EurAmount typé (Cockpit Sol2 Phase 1.1).

Deux constructeurs canoniques selon la doctrine §0.D (Décision A) :
  - build_regulatory() : montant tracé à un article réglementaire
  - build_contractual() : montant tracé à un EnergyContract

La fonction to_dict_with_proof() sérialise pour l'API avec proof_url.

Règle d'or : aucune constante € hardcodée ici. Les valeurs numériques
viennent exclusivement des couches appelantes (tests, seed, endpoints).

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.1
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.billing_models import EnergyContract
from models.eur_amount import EurAmount, EurAmountCategory


def build_regulatory(
    db: Session,
    value_eur: float,
    regulatory_article: str,
    formula_text: str,
) -> EurAmount:
    """Construit et persiste un EurAmount de catégorie réglementaire.

    Utiliser pour tout montant calculé depuis un texte réglementaire :
    pénalités DT (Décret 2019-771), amendes BACS (Décret 2020-887),
    sanctions OPERAT, etc.

    Args:
        db: session SQLAlchemy active
        value_eur: montant brut en €
        regulatory_article: référence précise, ex "Décret 2019-771 art. 9"
        formula_text: formule lisible, ex "3 sites × 7500 + 1 site × 3750"

    Returns:
        EurAmount persisté (id assigné après flush)

    Raises:
        ValueError: si regulatory_article est vide
    """
    if not regulatory_article or not regulatory_article.strip():
        raise ValueError(
            "regulatory_article est obligatoire pour category=CALCULATED_REGULATORY (doctrine §0.D décision A)"
        )
    if not formula_text or not formula_text.strip():
        raise ValueError("formula_text est obligatoire — traçabilité du calcul")

    eur = EurAmount(
        value_eur=value_eur,
        category=EurAmountCategory.CALCULATED_REGULATORY,
        regulatory_article=regulatory_article.strip(),
        contract_id=None,
        formula_text=formula_text.strip(),
        computed_at=datetime.utcnow(),
    )
    db.add(eur)
    db.flush()
    return eur


def build_contractual(
    db: Session,
    value_eur: float,
    contract_id: int,
    formula_text: str,
) -> EurAmount:
    """Construit et persiste un EurAmount de catégorie contractuelle.

    Utiliser pour tout montant calculé depuis un EnergyContract :
    coût fourniture, abonnement, dépassement de puissance, etc.

    Args:
        db: session SQLAlchemy active
        value_eur: montant brut en €
        contract_id: identifiant EnergyContract.id (doit exister en DB)
        formula_text: formule lisible, ex "12 mois × 250 €/mois"

    Returns:
        EurAmount persisté (id assigné après flush)

    Raises:
        HTTPException 404: si contract_id introuvable en DB
        ValueError: si formula_text vide
    """
    if not formula_text or not formula_text.strip():
        raise ValueError("formula_text est obligatoire — traçabilité du calcul")

    contract = db.query(EnergyContract).filter(EnergyContract.id == contract_id).first()
    if contract is None:
        raise HTTPException(
            status_code=404,
            detail=f"EnergyContract id={contract_id} introuvable — "
            "impossible de créer un EurAmount contractuel sans contrat valide",
        )

    eur = EurAmount(
        value_eur=value_eur,
        category=EurAmountCategory.CALCULATED_CONTRACTUAL,
        regulatory_article=None,
        contract_id=contract_id,
        formula_text=formula_text.strip(),
        computed_at=datetime.utcnow(),
    )
    db.add(eur)
    db.flush()
    return eur


def to_dict_with_proof(eur_amount: EurAmount) -> dict:
    """Sérialise un EurAmount pour l'API avec champ proof_url.

    Le proof_url pointe vers l'endpoint GET /api/cockpit/eur_amount/{id}/proof
    qui retourne ce même dict — permettant aux clients de récupérer la preuve
    de traçabilité par lien direct (dashboard, export PDF, audit trail).

    Args:
        eur_amount: instance EurAmount chargée depuis la DB

    Returns:
        dict avec tous les champs + proof_url canonique
    """
    computed_at_str = (
        eur_amount.computed_at.isoformat()
        if isinstance(eur_amount.computed_at, datetime)
        else str(eur_amount.computed_at)
    )
    category_value = eur_amount.category.value if hasattr(eur_amount.category, "value") else str(eur_amount.category)
    return {
        "id": eur_amount.id,
        "value_eur": eur_amount.value_eur,
        "category": category_value,
        "regulatory_article": eur_amount.regulatory_article,
        "contract_id": eur_amount.contract_id,
        "formula_text": eur_amount.formula_text,
        "computed_at": computed_at_str,
        "proof_url": f"/api/cockpit/eur_amount/{eur_amount.id}/proof",
    }
