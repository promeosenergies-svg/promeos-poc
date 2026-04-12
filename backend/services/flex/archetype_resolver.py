"""
Archetype resolver pour le moteur flex.

Reconcilie 3 sources de verite (UsageProfile observe, KB versionnee, NAF prefix statique)
et normalise tous les codes vers la taxonomie canonique `ARCHETYPE_TO_USAGES` du moteur flex.

Usage :
    from services.flex.archetype_resolver import (
        resolve_archetype,       # un seul site
        batch_resolve_archetypes, # N sites (evite N+1 KB)
        normalize_archetype,     # normalisation pure
    )
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from services.flex.flexibility_scoring_engine import ARCHETYPE_TO_USAGES

logger = logging.getLogger(__name__)


# KB (libelles sectoriels) -> flex engine (codes canoniques).
# La KB emploie "SANTE_HOPITAL", "DATACENTER", "HOTEL_STANDARD" ; le moteur flex
# emploie "SANTE", "DATA_CENTER", "HOTEL_HEBERGEMENT".
KB_TO_FLEX_ARCHETYPE: dict[str, str] = {
    "BUREAU_STANDARD": "BUREAU_STANDARD",
    "BUREAU_PERFORMANT": "BUREAU_STANDARD",
    "HOTEL_STANDARD": "HOTEL_HEBERGEMENT",
    "HOTEL_HEBERGEMENT": "HOTEL_HEBERGEMENT",
    "ENSEIGNEMENT": "ENSEIGNEMENT",
    "ENSEIGNEMENT_SUP": "ENSEIGNEMENT_SUP",
    "SANTE": "SANTE",
    "SANTE_HOPITAL": "SANTE",
    "COMMERCE_ALIMENTAIRE": "COMMERCE_ALIMENTAIRE",
    "RESTAURATION_SERVICE": "RESTAURANT",
    "RESTAURANT": "RESTAURANT",
    "LOGISTIQUE_ENTREPOT": "LOGISTIQUE_SEC",
    "LOGISTIQUE_SEC": "LOGISTIQUE_SEC",
    "LOGISTIQUE_FROID": "LOGISTIQUE_FRIGO",
    "LOGISTIQUE_FRIGO": "LOGISTIQUE_FRIGO",
    "INDUSTRIE_LEGERE": "INDUSTRIE_LEGERE",
    "INDUSTRIE_LOURDE": "INDUSTRIE_LOURDE",
    "DATACENTER": "DATA_CENTER",
    "DATA_CENTER": "DATA_CENTER",
    "COPROPRIETE": "COPROPRIETE",
    "SPORT_LOISIR": "SPORT_LOISIR",
    "SPORT_LOISIRS": "SPORT_LOISIR",
    "COLLECTIVITE": "COLLECTIVITE",
}

# Fallback NAF quand la KB n'a pas de mapping (dev/tests sans seed KB).
# 4 premiers chiffres du NAF -> archetype canonique flex.
NAF_PREFIX_TO_FLEX_ARCHETYPE: dict[str, str] = {
    "6820": "BUREAU_STANDARD",
    "7010": "BUREAU_STANDARD",
    "6910": "BUREAU_STANDARD",
    "5510": "HOTEL_HEBERGEMENT",
    "5520": "HOTEL_HEBERGEMENT",
    "8520": "ENSEIGNEMENT",
    "8531": "ENSEIGNEMENT",
    "8541": "ENSEIGNEMENT_SUP",
    "8542": "ENSEIGNEMENT_SUP",
    "8610": "SANTE",
    "8621": "SANTE",
    "5610": "RESTAURANT",
    "5630": "RESTAURANT",
    "4711": "COMMERCE_ALIMENTAIRE",
    "4721": "COMMERCE_ALIMENTAIRE",
    "5210": "LOGISTIQUE_SEC",
    "5229": "LOGISTIQUE_SEC",
    "1013": "LOGISTIQUE_FRIGO",
    "1052": "LOGISTIQUE_FRIGO",
    "6311": "DATA_CENTER",
    "2511": "INDUSTRIE_LEGERE",
    "2594": "INDUSTRIE_LEGERE",
    "2410": "INDUSTRIE_LOURDE",  # siderurgie
    "2351": "INDUSTRIE_LOURDE",  # fabrication ciment
    "2013": "INDUSTRIE_LOURDE",  # chimie de base
    "9311": "SPORT_LOISIR",
    "9313": "SPORT_LOISIR",
    "8411": "COLLECTIVITE",
    "8412": "COLLECTIVITE",
    "6832": "COPROPRIETE",
}


def normalize_archetype(code: Optional[str]) -> str:
    """Normalise un code archetype (KB ou libre) vers la taxonomie canonique flex."""
    if not code:
        return "DEFAULT"
    if code in ARCHETYPE_TO_USAGES:
        return code
    normalized = KB_TO_FLEX_ARCHETYPE.get(code)
    if normalized and normalized in ARCHETYPE_TO_USAGES:
        return normalized
    return "DEFAULT"


def _naf_prefix(naf_code: str) -> str:
    """Strip dots/spaces avant slice (format DD.DDC et DDDDC supportes)."""
    return naf_code.replace(".", "").replace(" ", "")[:4]


def _archetype_from_naf_static(naf_code: Optional[str]) -> Optional[str]:
    """Tier 3 : fallback NAF prefix hardcode (sans acces DB)."""
    if not naf_code:
        return None
    return NAF_PREFIX_TO_FLEX_ARCHETYPE.get(_naf_prefix(naf_code))


def resolve_archetype(db: Session, site, meter=None) -> str:
    """
    Resolution archetype pour un site, dans l'ordre :
    1. UsageProfile.archetype_code du compteur (donnee observee)
    2. KBMappingCode via NAF (referentiel versionne)
    3. NAF prefix hardcode (fallback dev/tests sans seed KB)
    4. DEFAULT (log WARNING)
    """
    from models.energy_models import Meter, UsageProfile

    # 1. UsageProfile
    try:
        if meter is None:
            meter = db.query(Meter).filter(Meter.site_id == site.id, Meter.is_active == True).first()
        if meter:
            profile = db.query(UsageProfile).filter(UsageProfile.meter_id == meter.id).first()
            if profile and profile.archetype_code:
                return normalize_archetype(profile.archetype_code)
    except Exception:
        pass

    # 2. KB service
    if site.naf_code:
        try:
            from services.kb_service import KBService

            kb_arch = KBService(db).get_archetype_by_naf(site.naf_code)
            if kb_arch and kb_arch.code:
                normalized = normalize_archetype(kb_arch.code)
                if normalized != "DEFAULT":
                    return normalized
        except Exception:
            pass

    # 3. NAF prefix statique
    static = _archetype_from_naf_static(site.naf_code)
    if static:
        return static

    # 4. Fallback
    logger.warning(
        "flex archetype fallback DEFAULT for site_id=%s nom=%r naf=%s",
        getattr(site, "id", "?"),
        getattr(site, "nom", "?"),
        getattr(site, "naf_code", None),
    )
    return "DEFAULT"


def batch_resolve_archetypes(
    db: Session,
    sites: list,
    meter_by_site: Optional[dict] = None,
    profile_by_meter: Optional[dict] = None,
) -> dict[int, str]:
    """
    Resolution archetype en batch pour N sites (evite le N+1 KBService).

    Args:
        sites: liste de Site
        meter_by_site: dict {site_id: Meter} pre-charge (optionnel)
        profile_by_meter: dict {meter_id: UsageProfile} pre-charge (optionnel)

    Returns:
        {site_id: archetype_code}
    """
    from models.kb_models import KBMappingCode

    meter_by_site = meter_by_site or {}
    profile_by_meter = profile_by_meter or {}

    # Batch KB : 1 requete pour tous les NAF distincts des sites
    naf_codes = list({s.naf_code for s in sites if s.naf_code})
    kb_naf_to_archetype: dict[str, str] = {}
    if naf_codes:
        try:
            mappings = (
                db.query(KBMappingCode)
                .options(joinedload(KBMappingCode.archetype))
                .filter(KBMappingCode.naf_code.in_(naf_codes))
                .order_by(KBMappingCode.priority.desc())
                .all()
            )
            for m in mappings:
                if m.naf_code not in kb_naf_to_archetype and m.archetype:
                    kb_naf_to_archetype[m.naf_code] = m.archetype.code
        except Exception:
            pass

    result: dict[int, str] = {}
    for site in sites:
        archetype = "DEFAULT"

        # 1. UsageProfile pre-charge
        meter = meter_by_site.get(site.id)
        if meter:
            up = profile_by_meter.get(meter.id)
            if up and up.archetype_code:
                archetype = normalize_archetype(up.archetype_code)

        # 2. KB batch
        if archetype == "DEFAULT" and site.naf_code:
            kb_code = kb_naf_to_archetype.get(site.naf_code)
            if kb_code:
                archetype = normalize_archetype(kb_code)

        # 3. NAF prefix statique
        if archetype == "DEFAULT":
            static = _archetype_from_naf_static(site.naf_code)
            if static:
                archetype = static

        # 4. Log fallback
        if archetype == "DEFAULT":
            logger.warning(
                "flex archetype fallback DEFAULT (batch) site_id=%s naf=%s",
                site.id,
                site.naf_code,
            )

        result[site.id] = archetype

    return result
