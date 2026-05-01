"""Mapping NAF → typologie organisationnelle PROMEOS Sol2 (5 typologies V2).

Sprint Refonte Narrative dynamique — Phase 1.1 (2026-05-01) + Phase 9.B
(2026-05-01 V2 ETI_TERTIAIRE).

5 typologies livrées :

- **GRAND_GROUPE** : groupe coté / foncière institutionnelle / holdings >
  30 sites tertiaires ou > 100k m². Audience CFO / DG / Asset Manager.
  Vocabulaire patrimoine / CODIR / Directeur Financier.

- **ETI_TERTIAIRE** (Phase 9.B) : ETI tertiaire midmarket 1-30 sites
  bureaux / ≤ 100k m². Audience DAF / DG opérationnel. Vocabulaire
  parc / comité de direction / DAF (sans CODIR ni patrimoine).
  Distinction GG vs ETI faite via `_typology_dominant_for_sites` selon
  seuils de taille (cf typology_resolver).

- **COMMERCE** : commerce indépendant ou multi-magasins (1-10 sites). Audience
  propriétaire / gérant. Vocabulaire métier-concret (boulangerie, magasin, four).
  Pas de CODIR ni patrimoine. Chiffrage en € directs (pas en MWh).

- **ERP** : établissement recevant du public (école, EHPAD, hôpital, mairie).
  Audience directeur / DG. Vocabulaire usagers / élèves / résidents. "Conseil
  d'administration" ou "comité de direction" (jamais CODIR).

- **UNKNOWN** : fallback NAF non couvert (industrie 1X-3X, agriculture 0X).

Le mapping NAF → typologie est dérivé du préfixe NAF (2 premiers chars).
GRAND_GROUPE et ETI_TERTIAIRE partagent les mêmes préfixes NAF (sièges
sociaux, foncières) — la distinction se fait par TAILLE (cf typology_resolver
`_apply_eti_threshold`).

Source : nomenclature NAF rév 2 INSEE 2008.
Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md` Phase 1.1 + 9.B.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class OrganizationTypology(str, Enum):
    """Typologie organisationnelle pour adaptation narrative.

    Phase 1.1 : 3 typologies MVP + UNKNOWN.
    Phase 9.B : ajout ETI_TERTIAIRE (sous-typologie GG raffinée par taille).

    UNKNOWN = fallback explicite (jamais erreur sur NAF inconnu).
    """

    GRAND_GROUPE = "grand_groupe_tertiaire"
    ETI_TERTIAIRE = "eti_tertiaire"
    COMMERCE = "commerce"
    ERP = "etablissement_recevant_public"
    UNKNOWN = "unknown"


# ─── Mapping NAF prefix (2 chars) → typologie ──────────────────────────────
# Source : nomenclature NAF rév 2 INSEE 2008.
# Le mapping doit rester exhaustif pour les divisions énergivores tertiaires
# (qui représentent 99 % du marché PROMEOS). Industries (1X-3X) et agriculture
# (0X) → UNKNOWN car hors cible MVP.

NAF_PREFIX_TO_TYPOLOGY: dict[str, OrganizationTypology] = {
    # ─── Grand groupe tertiaire (sièges + foncières + finance) ───────────
    "64": OrganizationTypology.GRAND_GROUPE,  # Activités services financiers (holdings)
    "65": OrganizationTypology.GRAND_GROUPE,  # Assurance
    "66": OrganizationTypology.GRAND_GROUPE,  # Activités auxiliaires services financiers
    "68": OrganizationTypology.GRAND_GROUPE,  # Activités immobilières (foncières)
    "69": OrganizationTypology.GRAND_GROUPE,  # Activités juridiques et comptables
    "70": OrganizationTypology.GRAND_GROUPE,  # Activités sièges sociaux
    "71": OrganizationTypology.GRAND_GROUPE,  # Activités d'architecture et d'ingénierie
    "73": OrganizationTypology.GRAND_GROUPE,  # Publicité et études de marché
    "74": OrganizationTypology.GRAND_GROUPE,  # Autres activités spécialisées
    "78": OrganizationTypology.GRAND_GROUPE,  # Activités liées à l'emploi
    # ─── Commerce (détail + gros + restauration + hébergement privé) ─────
    "45": OrganizationTypology.COMMERCE,  # Commerce automobile
    "46": OrganizationTypology.COMMERCE,  # Commerce de gros
    "47": OrganizationTypology.COMMERCE,  # Commerce de détail
    "55": OrganizationTypology.COMMERCE,  # Hébergement (hôtels privés)
    "56": OrganizationTypology.COMMERCE,  # Restauration
    "95": OrganizationTypology.COMMERCE,  # Réparation ordinateurs et biens
    "96": OrganizationTypology.COMMERCE,  # Autres services personnels (coiffure, pressing)
    # ─── ERP (établissements recevant du public) ─────────────────────────
    "84": OrganizationTypology.ERP,  # Administration publique
    "85": OrganizationTypology.ERP,  # Enseignement
    "86": OrganizationTypology.ERP,  # Santé humaine
    "87": OrganizationTypology.ERP,  # Hébergement médico-social (EHPAD)
    "88": OrganizationTypology.ERP,  # Action sociale sans hébergement
    "90": OrganizationTypology.ERP,  # Activités créatives, artistiques (théâtre, musée)
    "91": OrganizationTypology.ERP,  # Bibliothèques, archives, musées
    "93": OrganizationTypology.ERP,  # Activités sportives, récréatives
    "94": OrganizationTypology.ERP,  # Activités des organisations associatives
}


def resolve_typology(naf_code: Optional[str]) -> OrganizationTypology:
    """Résout typologie depuis code NAF (ex: '4724Z' → COMMERCE).

    Args:
        naf_code: code NAF de l'entité (Site / Org / EJ). Format INSEE
            standard : 4 chiffres + 1 lettre (ex: '8520Z'). Peut être None
            ou vide → UNKNOWN.

    Returns:
        `OrganizationTypology`. Jamais d'exception : si `naf_code` invalide
        ou non mappé, retourne `UNKNOWN` (la narrative aura un fallback).

    Examples:
        >>> resolve_typology("6420Z")  # holdings
        <OrganizationTypology.GRAND_GROUPE: 'grand_groupe_tertiaire'>
        >>> resolve_typology("4724Z")  # boulangerie
        <OrganizationTypology.COMMERCE: 'commerce'>
        >>> resolve_typology("8510Z")  # école primaire
        <OrganizationTypology.ERP: 'etablissement_recevant_public'>
        >>> resolve_typology(None)
        <OrganizationTypology.UNKNOWN: 'unknown'>
        >>> resolve_typology("ZZZZZ")  # NAF inconnu
        <OrganizationTypology.UNKNOWN: 'unknown'>
    """
    if not naf_code or len(naf_code) < 2:
        return OrganizationTypology.UNKNOWN
    prefix = naf_code[:2]
    return NAF_PREFIX_TO_TYPOLOGY.get(prefix, OrganizationTypology.UNKNOWN)


__all__ = [
    "OrganizationTypology",
    "NAF_PREFIX_TO_TYPOLOGY",
    "resolve_typology",
]
