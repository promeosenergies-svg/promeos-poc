"""
PROMEOS - Detection d'archetype d'usage pilotage.

Resolution en cascade (ordre de priorite) :
    1. Site.archetype_code direct (Option C wiring prod)
    2. NAF du site (via utils/naf_resolver) mappe sur les 8 archetypes pilotage
       (constants.NAF_PREFIX_TO_PILOTAGE_ARCHETYPE)
    3. Signaux conso (horaires_ouverture, continu_24_7, talon_froid) -- fallback
       pur heuristique, utilise uniquement pour un compteur inconnu sans NAF
    4. BUREAU_STANDARD (fallback median tertiaire avec warning log)

Le resolveur generique multi-usage (flex, compliance, etc.) reste
`services.flex.archetype_resolver`. Ce module est specialise pour les 8
segments Barometre Flex 2026 consommes par le scoring/roi pilotage.

Le calibrage quantitatif (taux decalable, plages de pointe officielles) vit
dans `services.pilotage.constants.ARCHETYPE_CALIBRATION_2024` et est consomme
par `score_potential.compute_potential_score`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from services.pilotage.constants import (
    ARCHETYPE_CALIBRATION_2024,
    ARCHETYPE_RULES,
    archetype_from_naf,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from models import Site

logger = logging.getLogger(__name__)

_DEFAULT_ARCHETYPE = "BUREAU_STANDARD"


def resolve_pilotage_archetype(
    site: "Site",
    db: "Session",
    *,
    signals: Optional[dict] = None,
) -> str:
    """
    Resout l'archetype pilotage d'un site en cascade.

    Args:
        site: instance Site (avec `archetype_code`, `naf_code`, `portefeuille_id`).
        db: session DB (pour lookup EntiteJuridique.naf_code via portefeuille).
        signals: optionnel, dict {horaires_ouverture, continu_24_7, talon_froid}
                 -- utilise uniquement en fallback 3 quand site.archetype_code et
                 NAF sont absents.

    Returns:
        Code canonique parmi les 8 archetypes `ARCHETYPE_CALIBRATION_2024`.
    """
    # 1. Override direct (Option C)
    if getattr(site, "archetype_code", None) and site.archetype_code in ARCHETYPE_CALIBRATION_2024:
        return site.archetype_code

    # 2. NAF (en cascade Site -> EntiteJuridique via utils/naf_resolver)
    from utils.naf_resolver import resolve_naf_code

    naf = resolve_naf_code(site, db)
    from_naf = archetype_from_naf(naf)
    if from_naf:
        return from_naf

    # 3. Heuristique signaux conso (quand aucun NAF disponible)
    if signals:
        heuristique = detect_archetype(
            horaires_ouverture=signals.get("horaires_ouverture"),
            continu_24_7=bool(signals.get("continu_24_7")),
            talon_froid=bool(signals.get("talon_froid")),
        )
        if heuristique:
            return heuristique

    # 4. Fallback mediane tertiaire avec warning trace audit
    logger.warning(
        "pilotage.archetype fallback %s for site_id=%s nom=%r naf=%s",
        _DEFAULT_ARCHETYPE,
        getattr(site, "id", "?"),
        getattr(site, "nom", "?"),
        naf,
    )
    return _DEFAULT_ARCHETYPE


def detect_archetype(
    horaires_ouverture: Optional[tuple[int, int]] = None,
    continu_24_7: bool = False,
    talon_froid: bool = False,
) -> str:
    """
    Classifie un site a partir de signaux conso observes.

    Fallback pur heuristique utilise uniquement quand aucun NAF/archetype_code
    n'est disponible. L'heuristique precedente 'continu_24_7 sans talon froid
    -> HOTELLERIE' a ete retiree (biais vers hotellerie quand en realite sante
    /collectivite/datacenter sont aussi 24/7).

    Args:
        horaires_ouverture: (h_debut, h_fin) detecte sur la semaine type
        continu_24_7: True si la conso ne retombe jamais sur un niveau nuit
        talon_froid: True si un talon eleve (>40% mediane) est continu

    Returns:
        Code canonique parmi les 8 archetypes pilotage, ou BUREAU_STANDARD.
    """
    # Signal fort : froid continu 24/7 => logistique frigorifique
    if continu_24_7 and talon_froid:
        return "LOGISTIQUE_FRIGO"

    # Journee typique et talon froid => commerce alimentaire
    if talon_froid:
        return "COMMERCE_ALIMENTAIRE"

    # Classification par plage horaire
    if horaires_ouverture:
        h_debut, h_fin = horaires_ouverture
        if h_debut <= 8 and h_fin <= 18:
            return "ENSEIGNEMENT"
        if h_debut >= 10 and h_fin >= 19:
            return "COMMERCE_SPECIALISE"
        if h_debut <= 7 and h_fin >= 18:
            return "INDUSTRIE_LEGERE"

    # Note : continu_24_7 sans talon froid n'est PLUS mappe sur HOTELLERIE.
    # Ce cas merite un NAF ou un override site.archetype_code explicite --
    # on retombe sur BUREAU_STANDARD (fallback median) par defense.
    return _DEFAULT_ARCHETYPE


def get_rule(archetype_code: str) -> Optional[dict]:
    """Retourne la regle ARCHETYPE_RULES pour un code, ou None."""
    return ARCHETYPE_RULES.get(archetype_code)
