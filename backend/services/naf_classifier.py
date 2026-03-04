"""
PROMEOS - Classification automatique NAF → TypeSite
Mapping des codes NAF (nomenclature INSEE) vers les segments B2B PROMEOS.
"""

from models.enums import TypeSite


# Mapping prefix NAF (2 premiers chiffres) → TypeSite
# Source: nomenclature NAF rev. 2 (INSEE)
_NAF_PREFIX_MAP = {
    # Industrie manufacturiere (10-33)
    **{str(i).zfill(2): TypeSite.USINE for i in range(10, 34)},
    # Construction (41-43)
    **{str(i).zfill(2): TypeSite.USINE for i in range(41, 44)},
    # Commerce de gros (45-46)
    "45": TypeSite.ENTREPOT,
    "46": TypeSite.ENTREPOT,
    # Commerce de detail (47)
    "47": TypeSite.COMMERCE,
    # Transport et entreposage (49-53)
    **{str(i).zfill(2): TypeSite.ENTREPOT for i in range(49, 54)},
    # Hebergement / restauration (55-56)
    "55": TypeSite.HOTEL,
    "56": TypeSite.HOTEL,
    # Information et communication (58-63)
    **{str(i).zfill(2): TypeSite.BUREAU for i in range(58, 64)},
    # Finance et assurance (64-66)
    **{str(i).zfill(2): TypeSite.BUREAU for i in range(64, 67)},
    # Activites immobilieres (68) → copropriete par defaut
    "68": TypeSite.COPROPRIETE,
    # Services aux entreprises (69-82)
    **{str(i).zfill(2): TypeSite.BUREAU for i in range(69, 83)},
    # Administration publique (84)
    "84": TypeSite.COLLECTIVITE,
    # Enseignement (85)
    "85": TypeSite.ENSEIGNEMENT,
    # Sante humaine et action sociale (86-88)
    **{str(i).zfill(2): TypeSite.SANTE for i in range(86, 89)},
    # Logement social / bailleurs → mapping specifique sur sous-codes
    # (gere via override dans classify_naf)
}

# Sous-codes NAF specifiques pour affiner le mapping
_NAF_SPECIFIC_MAP = {
    "68.20A": TypeSite.LOGEMENT_SOCIAL,  # Location de logements (bailleurs sociaux)
    "68.20B": TypeSite.COPROPRIETE,  # Location de terrains et autres biens immo
    "68.31Z": TypeSite.COPROPRIETE,  # Agences immobilieres
    "68.32A": TypeSite.COPROPRIETE,  # Administration d'immeubles et syndics
    "68.32B": TypeSite.COPROPRIETE,  # Supports juridiques de programmes
}


def classify_naf(naf_code: str) -> TypeSite:
    """Classifie un code NAF vers un TypeSite PROMEOS.

    Args:
        naf_code: Code NAF 5 caracteres (ex: "47.11A", "68.20A", "84.11Z").
                  Accepte aussi le format sans point (ex: "4711A").

    Returns:
        TypeSite correspondant. Defaut: BUREAU si code inconnu.
    """
    if not naf_code or not isinstance(naf_code, str):
        return TypeSite.BUREAU

    # Normaliser: retirer les espaces et mettre en majuscules
    code = naf_code.strip().upper()

    # Verifier d'abord les sous-codes specifiques (ex: "68.20A")
    if code in _NAF_SPECIFIC_MAP:
        return _NAF_SPECIFIC_MAP[code]

    # Format sans point (ex: "4711A" → "47")
    code_clean = code.replace(".", "")
    if len(code_clean) >= 2:
        prefix = code_clean[:2]
        if prefix in _NAF_PREFIX_MAP:
            return _NAF_PREFIX_MAP[prefix]

    return TypeSite.BUREAU
