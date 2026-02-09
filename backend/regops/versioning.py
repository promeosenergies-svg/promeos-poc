"""
PROMEOS RegOps - Versioning (hash computation for cache invalidation)
"""
import hashlib
import json


def compute_deterministic_version(regs_config: dict, rules_module_hashes: dict) -> str:
    """
    Hash des configs YAML + hashes des modules de regles.
    Permet de detecter les changements dans la logique deterministe.
    """
    combined = {
        "regs": regs_config,
        "rules": rules_module_hashes,
    }
    content = json.dumps(combined, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def compute_data_version(site, obligations: list, evidences: list) -> str:
    """
    Fingerprint des donnees critiques du site.
    Permet de detecter les changements dans les inputs.
    """
    data = {
        "site_id": site.id,
        "tertiaire_area_m2": site.tertiaire_area_m2,
        "parking_area_m2": site.parking_area_m2,
        "roof_area_m2": site.roof_area_m2,
        "operat_status": str(site.operat_status) if site.operat_status else None,
        "annual_kwh_total": site.annual_kwh_total,
        "obligations_count": len(obligations),
        "evidences_count": len(evidences),
    }
    content = json.dumps(data, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]
