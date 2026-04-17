"""
PROMEOS - Detection d'archetype d'usage a partir de signaux consos.

Module leger : classifie un compteur inconnu en appliquant les regles
`ARCHETYPE_RULES` aux signatures observees (continuite 24h/24, talon froid,
plage ouverte). Le resolveur principal reste `services.flex.archetype_resolver`
(NAF + KB + UsageProfile) ; ce detecteur sert de fallback quand aucune des
trois sources n'est disponible.

Le calibrage quantitatif (taux decalable, plages de pointe officielles) vit
dans `services.pilotage.constants.ARCHETYPE_CALIBRATION_2024` et est consomme
par `score_potential.compute_potential_score`.
"""

from __future__ import annotations

from typing import Optional

from services.pilotage.constants import ARCHETYPE_RULES


def detect_archetype(
    horaires_ouverture: Optional[tuple[int, int]] = None,
    continu_24_7: bool = False,
    talon_froid: bool = False,
) -> str:
    """
    Retourne le code d'archetype le plus proche des signaux passes.

    Args:
        horaires_ouverture: (h_debut, h_fin) detecte sur la semaine type
        continu_24_7: True si la conso ne retombe jamais sur un niveau nuit
        talon_froid: True si un talon eleve (>40% mediane) est continu

    Returns:
        Code canonique (ex: "BUREAU_STANDARD", "LOGISTIQUE_FRIGO"), ou
        "BUREAU_STANDARD" par defaut si rien ne matche.
    """
    # Froid continu 24/7 -> logistique frigorifique (signal le plus net)
    if continu_24_7 and talon_froid:
        return "LOGISTIQUE_FRIGO"

    # 24/7 sans froid prononce -> sante ou hotellerie
    if continu_24_7:
        # Heuristique : sans talon froid, privilegier hotellerie (plus frequent
        # en base PROMEOS). La resolution fine se fait ensuite via NAF.
        return "HOTELLERIE"

    # Journee typique et talon froid -> commerce alimentaire
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

    return "BUREAU_STANDARD"


def get_rule(archetype_code: str) -> Optional[dict]:
    """Retourne la regle ARCHETYPE_RULES pour un code, ou None."""
    return ARCHETYPE_RULES.get(archetype_code)
