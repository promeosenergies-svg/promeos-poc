"""Check billing ↔ contract ↔ site consistency."""

from sqlalchemy.orm import Session
from models import Site, EnergyContract
from models.base import not_deleted


def check_perimeter(db: Session, site_id: int, contract_id: int = None, period_start=None, period_end=None) -> dict:
    """Verify billing perimeter consistency."""
    result = {
        "consistent": True,
        "site_exists": False,
        "contract_exists": None,
        "contract_matches_site": None,
        "contract_covers_period": None,
        "warnings": [],
    }

    # 1. Check site exists and is active
    site = db.query(Site).filter(Site.id == site_id, not_deleted(Site)).first()
    result["site_exists"] = site is not None
    if not site:
        result["consistent"] = False
        result["warnings"].append("Site inexistant ou archivé")
        return result

    # 2. Check contract if provided
    if contract_id:
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
            from datetime import date as date_type

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
