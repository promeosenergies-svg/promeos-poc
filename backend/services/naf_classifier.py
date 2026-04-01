"""
PROMEOS - Classification automatique NAF → TypeSite
Cascade : KB (732 mappings) → fallback hardcodé (_NAF_PREFIX_MAP).
"""

import logging

from models.enums import TypeSite

logger = logging.getLogger(__name__)


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
}

# Sous-codes NAF specifiques pour affiner le mapping
_NAF_SPECIFIC_MAP = {
    "68.20A": TypeSite.LOGEMENT_SOCIAL,
    "68.20B": TypeSite.COPROPRIETE,
    "68.31Z": TypeSite.COPROPRIETE,
    "68.32A": TypeSite.COPROPRIETE,
    "68.32B": TypeSite.COPROPRIETE,
}

# KB archetype code → TypeSite (pour résoudre depuis KBArchetype)
_ARCHETYPE_TO_TYPE = {
    "BUREAU_STANDARD": TypeSite.BUREAU,
    "HOTEL_HEBERGEMENT": TypeSite.HOTEL,
    "ENSEIGNEMENT": TypeSite.ENSEIGNEMENT,
    "LOGISTIQUE_SEC": TypeSite.ENTREPOT,
    "LOGISTIQUE_FROID": TypeSite.ENTREPOT,
    "INDUSTRIE_LEGERE": TypeSite.USINE,
    "HOPITAL_STANDARD": TypeSite.SANTE,
    "COMMERCE_ALIMENTAIRE": TypeSite.COMMERCE,
    "COMMERCE_NON_ALIMENTAIRE": TypeSite.COMMERCE,
    "RESTAURATION_SERVICE": TypeSite.HOTEL,
    "ADMINISTRATION": TypeSite.COLLECTIVITE,
    "DATA_CENTER_IT": TypeSite.BUREAU,
    "SPORT_LOISIRS": TypeSite.BUREAU,
    "COPROPRIETE_LOGEMENT": TypeSite.COPROPRIETE,
    "AUTRE_TERTIAIRE": TypeSite.BUREAU,
}


def classify_naf(naf_code: str) -> TypeSite:
    """Classifie un code NAF vers un TypeSite PROMEOS.

    Cascade : KB (KBMappingCode) → sous-codes spécifiques → prefix map → BUREAU.
    """
    if not naf_code or not isinstance(naf_code, str):
        return TypeSite.BUREAU

    code = naf_code.strip().upper()

    # 1. Tenter la KB (source de vérité si disponible)
    kb_result = _lookup_kb(code)
    if kb_result:
        return kb_result

    # 2. Sous-codes spécifiques (ex: "68.20A")
    if code in _NAF_SPECIFIC_MAP:
        return _NAF_SPECIFIC_MAP[code]

    # 3. Prefix map (2 premiers chiffres)
    code_clean = code.replace(".", "")
    if len(code_clean) >= 2:
        prefix = code_clean[:2]
        if prefix in _NAF_PREFIX_MAP:
            return _NAF_PREFIX_MAP[prefix]

    return TypeSite.BUREAU


def _lookup_kb(naf_code: str) -> TypeSite | None:
    """Cherche le NAF dans KBMappingCode (DB). Retourne None si indisponible."""
    try:
        from database.connection import SessionLocal
        from models.kb_models import KBMappingCode, KBArchetype

        db = SessionLocal()
        try:
            mapping = db.query(KBMappingCode).filter(KBMappingCode.naf_code == naf_code).first()
            if not mapping:
                return None
            archetype = db.query(KBArchetype).filter(KBArchetype.id == mapping.archetype_id).first()
            if archetype and archetype.code in _ARCHETYPE_TO_TYPE:
                return _ARCHETYPE_TO_TYPE[archetype.code]
        finally:
            db.close()
    except Exception:
        pass  # DB non disponible → fallback hardcodé
    return None
