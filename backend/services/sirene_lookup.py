"""
PROMEOS — Lookup SIRET via recherche-entreprises.api.gouv.fr (gratuit, sans clé).
Non bloquant si API down → retourne None.
"""

import logging
from typing import Optional

import httpx

from services.naf_classifier import classify_naf

logger = logging.getLogger(__name__)

_API_BASE = "https://recherche-entreprises.api.gouv.fr/search"
_TIMEOUT = 5.0  # secondes


def lookup_siret(siret: str) -> Optional[dict]:
    """
    Recherche un établissement par SIRET via l'API publique.
    Retourne un dict enrichi ou None si indisponible.
    """
    siret = (siret or "").strip().replace(" ", "")
    if len(siret) != 14 or not siret.isdigit():
        return None

    try:
        resp = httpx.get(
            _API_BASE,
            params={"q": siret, "per_page": 1},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning("SIRENE lookup failed for %s: %s", siret, e)
        return None

    results = data.get("results", [])
    if not results:
        return None

    ent = results[0]
    siren = ent.get("siren", siret[:9])
    nom = ent.get("nom_complet") or ent.get("nom_raison_sociale") or ""
    naf_code = ent.get("activite_principale") or ""
    naf_label = ent.get("libelle_activite_principale") or ""

    # Chercher l'établissement correspondant au SIRET
    adresse = ""
    code_postal = ""
    ville = ""
    for etab in ent.get("matching_etablissements", []) or []:
        if etab.get("siret") == siret:
            adr = etab.get("adresse") or ""
            adresse = adr
            # Tenter d'extraire CP et ville depuis le champ commune
            code_postal = etab.get("code_postal") or ""
            ville = etab.get("libelle_commune") or ""
            break

    # Si pas trouvé dans matching, fallback sur siege
    if not ville:
        siege = ent.get("siege", {})
        adresse = siege.get("adresse") or adresse
        code_postal = siege.get("code_postal") or code_postal
        ville = siege.get("libelle_commune") or ville

    # Archetype via NAF classifier
    archetype = None
    if naf_code:
        try:
            archetype = classify_naf(naf_code).value
        except Exception:
            pass

    return {
        "siret": siret,
        "siren": siren,
        "nom": nom,
        "naf_code": naf_code,
        "naf_label": naf_label,
        "adresse": adresse,
        "code_postal": code_postal,
        "ville": ville,
        "archetype": archetype,
    }
