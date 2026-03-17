"""Purchase perimeter validation — aligned with billing canonical."""

from sqlalchemy.orm import Session
from services.perimeter_check import check_perimeter
from schemas.contract_perimeter import ContractPerimeter


def validate_purchase_perimeter(
    db: Session, site_id: int, contract_id: int = None, period_start=None, period_end=None
) -> dict:
    """Validate that a purchase scenario references a valid billing perimeter.
    Reuses the same perimeter_check as billing to ensure consistency.
    """
    result = check_perimeter(db, site_id, contract_id, period_start, period_end)
    result["module"] = "purchase"

    # Additional purchase-specific checks
    if result["site_exists"] and contract_id and result.get("contract_exists"):
        if not result.get("contract_covers_period", True):
            result["warnings"].append("Scénario achat sur contrat expiré — vérifier la pertinence")

    return result
