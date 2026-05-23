"""Check billing ↔ contract ↔ site consistency.

P0-C 2026-05-23 — renforcement : une facture ne peut pas être considérée
fiable si aucun contrat n'est rattaché alors que le site a des points de
livraison actifs. Délègue à `contract_coverage_service` pour la détection.
"""

from datetime import date as date_type
from typing import Any, Optional

from sqlalchemy.orm import Session

from models import EnergyContract, Site
from models.base import not_deleted
from models.enums import DeliveryPointStatus
from models.patrimoine import DeliveryPoint


# Code d'erreur FR exposé côté API pour Bill Intelligence + UI.
ERROR_CODE_MISSING_CONTRACT = "BILLING_CONTRACT_REQUIRED"
ERROR_MESSAGE_MISSING_CONTRACT_FR = (
    "Impossible de fiabiliser cette facture : aucun contrat n'est rattaché au point de livraison."
)


def _site_has_active_delivery_points(db: Session, site_id: int) -> bool:
    """Vrai si le site a au moins un point de livraison actif (P0-C)."""
    return (
        not_deleted(db.query(DeliveryPoint), DeliveryPoint)
        .filter(
            DeliveryPoint.site_id == site_id,
            DeliveryPoint.status == DeliveryPointStatus.ACTIVE,
        )
        .first()
        is not None
    )


def check_perimeter(
    db: Session,
    site_id: int,
    contract_id: Optional[int] = None,
    period_start: Any = None,
    period_end: Any = None,
) -> dict:
    """Vérifie la cohérence facture ↔ contrat ↔ site.

    Retourne un dict avec `consistent`, les flags intermédiaires, et la liste
    `warnings`. P0-C — si `contract_id` est manquant alors que le site a des
    DP actifs, `consistent=False` + `error_code=BILLING_CONTRAT_REQUIRED`.
    """
    result: dict = {
        "consistent": True,
        "site_exists": False,
        "contract_exists": None,
        "contract_matches_site": None,
        "contract_covers_period": None,
        "warnings": [],
        "error_code": None,
        "blocking": False,
    }

    # 1. Site exists and active
    site = db.query(Site).filter(Site.id == site_id, not_deleted(Site)).first()
    result["site_exists"] = site is not None
    if not site:
        result["consistent"] = False
        result["warnings"].append("Site inexistant ou archivé")
        return result

    # P0-C — un site avec DP actifs DOIT avoir un contract_id fourni
    if not contract_id:
        if _site_has_active_delivery_points(db, site_id):
            result["consistent"] = False
            result["blocking"] = True
            result["error_code"] = ERROR_CODE_MISSING_CONTRACT
            result["warnings"].append(ERROR_MESSAGE_MISSING_CONTRACT_FR)
        return result

    # 2. Contract exists
    contract = db.query(EnergyContract).filter(EnergyContract.id == contract_id).first()
    result["contract_exists"] = contract is not None
    if not contract:
        result["consistent"] = False
        result["warnings"].append("Contrat inexistant")
        return result

    # 3. Contract matches site
    result["contract_matches_site"] = contract.site_id == site_id
    if not result["contract_matches_site"]:
        result["consistent"] = False
        result["warnings"].append(f"Contrat {contract_id} lié au site {contract.site_id}, pas au site {site_id}")

    # 4. Contract covers period
    if period_start and contract.end_date:
        if isinstance(period_start, str):
            period_start = date_type.fromisoformat(period_start)
        if isinstance(contract.end_date, str):
            contract.end_date = date_type.fromisoformat(contract.end_date)
        covers = contract.end_date >= period_start
        result["contract_covers_period"] = covers
        if not covers:
            result["warnings"].append("Contrat expiré avant le début de la période facturée")
            result["consistent"] = False

    return result
