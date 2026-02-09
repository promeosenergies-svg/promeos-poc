"""
PROMEOS RegOps - Completeness checks (required inputs gate)
"""


def check_required_inputs(site, batiments, reg_config: dict) -> list[str]:
    """
    Verifie la presence des champs requis pour une reglementation.
    Retourne la liste des champs manquants.
    """
    missing = []
    required = reg_config.get("required_inputs", [])

    for field_name in required:
        # Check site fields
        if hasattr(site, field_name):
            value = getattr(site, field_name)
            if value is None:
                missing.append(field_name)
        # Check batiment fields (aggregated)
        elif field_name == "cvc_power_kw":
            if not batiments or not any(b.cvc_power_kw for b in batiments):
                missing.append(field_name)
        else:
            missing.append(field_name)

    return missing
