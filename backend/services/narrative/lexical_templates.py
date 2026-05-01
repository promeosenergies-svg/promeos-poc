"""Templates lexicaux par typologie organisationnelle.

Sprint Refonte Narrative dynamique — Phase 1.3 (2026-05-01).

Fondation lexicale pour la composition de narratives adaptées par typologie.
Chaque typologie expose un dictionnaire de mots-clés (`scope_singular`,
`decision_body`, `owner_term`, etc.) que les builders narrative consomment.

## Doctrine §11.3 — règles éditoriales par typologie

| Typologie | scope | décision | owner | structurel | audience régul |
|---|---|---|---|---|---|
| GRAND_GROUPE | "votre patrimoine" | "comité de direction"/"CODIR" | "Asset Manager" | "portefeuille" | expert |
| COMMERCE | "votre {activity}" (boulangerie/magasin/etc.) | "vous-même en tant que propriétaire" | "propriétaire" | "activité" | pédagogique |
| ERP | "votre établissement" | "conseil d'administration"/"comité de direction" | "directeur/directrice" | "établissement" | pédagogique-pro |
| UNKNOWN (fallback) | hérite GRAND_GROUPE | hérite GG | hérite GG | hérite GG | expert |

## Anti-patterns interdits

Vérifiés par source-guards Phase 1.3 :

- ❌ "patrimoine" dans templates COMMERCE
- ❌ "CODIR" dans templates COMMERCE ou ERP (ERP utilise "comité de direction")
- ❌ "propriétaire" dans templates GRAND_GROUPE
- ❌ "élèves"/"résidents"/"usagers" dans templates GRAND_GROUPE ou COMMERCE

## V2 (Sprint Q3 2026)

Ajout des typologies PME_TERTIAIRE (préfixes 49-53) et INDUSTRIE
(préfixes 10-33). Templates dédiés à créer.

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 1.3 + maquettes `narrative-{grand-groupe,commerce,erp}.html`.
"""

from __future__ import annotations

from typing import Optional

from doctrine.naf_to_typology import OrganizationTypology

# ─── Templates lexicaux par typologie ──────────────────────────────────────


LEXICAL_TEMPLATES: dict[OrganizationTypology, dict[str, object]] = {
    OrganizationTypology.GRAND_GROUPE: {
        # Vocabulaire de scope (utilisé dans phrase 1 et phrases structurelles)
        "scope_singular": "votre patrimoine",
        "scope_plural": "vos sites",
        "scope_qualifier": "patrimonial",
        # Vocabulaire de décision (organe d'arbitrage)
        "decision_body": "comité de direction",
        "decision_short": "CODIR",
        # Vocabulaire d'owner (qui agit / qui décide opérationnellement)
        "owner_term": "Asset Manager",
        "owner_alt_term": "Property Manager",
        # Vocabulaire structurel (le "tout" qu'on évoque)
        "structural_term": "portefeuille",
        "structural_term_alt": "patrimoine",
        # Audience réglementaire (registre)
        "regulatory_audience": "expert",
        # Lecture cible (chronométrage doctrine §11.3)
        "avg_lecture_seconds": 180,  # 3 min CFO
        # Marqueurs d'amélioration / dégradation (usage tonale Phase 4)
        "improvement_term": "rattrapage",
        "degradation_term": "dérive",
    },
    OrganizationTypology.COMMERCE: {
        # NB : `scope_singular` contient `{activity}` à substituer par
        # `get_activity_name(naf_code)` (boulangerie, magasin, restaurant…)
        "scope_singular": "votre {activity}",
        "scope_plural": "vos {activity}s",
        "scope_qualifier": "métier",
        # Le commerçant arbitre seul — pas de CODIR ni de comité
        "decision_body": "vous-même en tant que propriétaire",
        "decision_short": "vous-même",
        "owner_term": "propriétaire",
        "owner_alt_term": "gérant",
        "structural_term": "activité",
        "structural_term_alt": "commerce",
        "regulatory_audience": "pédagogique",
        "avg_lecture_seconds": 60,  # 1 min commerçant
        "improvement_term": "économies",
        "degradation_term": "surcoût",
    },
    OrganizationTypology.ERP: {
        "scope_singular": "votre établissement",
        "scope_plural": "vos établissements",
        "scope_qualifier": "public",
        # ERP : "comité de direction" (ou "conseil d'administration"/"conseil de
        # surveillance" selon statut) — JAMAIS "CODIR" qui est purement privé/ETI
        "decision_body": "conseil d'administration",
        "decision_short": "comité de direction",
        "owner_term": "directeur",  # ou "directrice", à adapter au persona
        "owner_alt_term": "responsable d'établissement",
        "structural_term": "établissement",
        "structural_term_alt": "service public",
        "regulatory_audience": "pédagogique-pro",
        "avg_lecture_seconds": 120,  # 2 min directeur
        "improvement_term": "amélioration",
        "degradation_term": "dérive",
    },
    OrganizationTypology.UNKNOWN: {
        # Fallback : hérite GRAND_GROUPE (audience experte, registre neutre).
        # Si on tombe ici en prod, c'est qu'on a une org non mappée — la
        # narrative reste fonctionnelle mais générique.
        "scope_singular": "votre périmètre",
        "scope_plural": "vos sites",
        "scope_qualifier": "",
        "decision_body": "comité de direction",
        "decision_short": "comité",
        "owner_term": "responsable",
        "owner_alt_term": "responsable",
        "structural_term": "périmètre",
        "structural_term_alt": "scope",
        "regulatory_audience": "expert",
        "avg_lecture_seconds": 180,
        "improvement_term": "amélioration",
        "degradation_term": "dérive",
    },
}


def get_template(
    typology: OrganizationTypology,
    key: str,
    fallback: str = "",
) -> str:
    """Récupère un template lexical avec fallback safe.

    Args:
        typology: typologie cible (OrganizationTypology).
        key: clé du template (ex: "scope_singular", "decision_body").
        fallback: valeur retournée si la clé est absente du template
            de la typologie. Par défaut, chaîne vide.

    Returns:
        Le template (str) si trouvé, sinon le fallback. Pour
        `OrganizationTypology.UNKNOWN`, on tombe sur le template UNKNOWN
        (qui hérite des valeurs GRAND_GROUPE génériques).

    Examples:
        >>> get_template(OrganizationTypology.GRAND_GROUPE, "scope_singular")
        'votre patrimoine'
        >>> get_template(OrganizationTypology.COMMERCE, "decision_body")
        'vous-même en tant que propriétaire'
        >>> get_template(OrganizationTypology.ERP, "owner_term")
        'directeur'
        >>> get_template(OrganizationTypology.UNKNOWN, "scope_singular")
        'votre périmètre'
    """
    templates = LEXICAL_TEMPLATES.get(typology, LEXICAL_TEMPLATES[OrganizationTypology.UNKNOWN])
    value = templates.get(key, fallback)
    return str(value) if value is not None else fallback


# ─── NAF → activity name (Commerce uniquement) ─────────────────────────────


# Mapping NAF code complet (5 chars) → nom métier concret pour insertion dans
# le template `scope_singular = "votre {activity}"` du Commerce.
# Source : nomenclature NAF rév 2 INSEE 2008.
NAF_TO_ACTIVITY_NAME: dict[str, str] = {
    # Commerce de détail alimentaire (4724x-4729x)
    "4711A": "supérette",
    "4711B": "supérette",
    "4711C": "supérette",
    "4711D": "supérette",
    "4711E": "supermarché",
    "4711F": "hypermarché",
    "4719A": "magasin",  # grand magasin
    "4719B": "magasin",
    "4721Z": "primeur",  # fruits et légumes
    "4722Z": "boucherie",  # viandes
    "4723Z": "poissonnerie",
    "4724Z": "boulangerie",  # pains, pâtisseries, confiseries
    "4725Z": "cave",  # boissons
    "4726Z": "tabac-presse",
    "4729Z": "épicerie",
    # Commerce de détail non-alimentaire (475x-477x)
    "4730Z": "station-service",
    "4741Z": "magasin d'informatique",
    "4742Z": "magasin de téléphonie",
    "4751Z": "magasin de textiles",
    "4752Z": "magasin de bricolage",
    "4753Z": "magasin de revêtements",
    "4754Z": "magasin d'électroménager",
    "4759A": "magasin de meubles",
    "4761Z": "librairie",
    "4762Z": "magasin de presse",
    "4771Z": "magasin de vêtements",
    "4772A": "magasin de chaussures",
    "4772B": "maroquinerie",
    "4773Z": "pharmacie",
    "4774Z": "magasin d'optique",
    "4775Z": "parfumerie",
    "4778A": "magasin d'art",
    "4778B": "magasin de fleurs",
    "4778C": "magasin de souvenirs",
    "4781Z": "stand de marché",  # alimentaire
    "4782Z": "stand de marché",  # textiles
    "4789Z": "stand de marché",  # autres
    "4791A": "boutique en ligne",
    "4791B": "boutique en ligne",
    # Restauration / hébergement privé (55x-56x)
    "5510Z": "hôtel",
    "5520Z": "résidence de tourisme",
    "5530Z": "camping",
    "5610A": "restaurant",
    "5610B": "restaurant",  # restauration rapide
    "5610C": "restaurant",  # cafétéria
    "5621Z": "service traiteur",
    "5629A": "restauration collective",
    "5629B": "restauration collective",
    "5630Z": "café-bar",
}


def get_activity_name(naf_code: Optional[str], fallback: str = "magasin") -> str:
    """Retourne le nom métier concret pour un NAF (Commerce uniquement).

    Utilisé pour substituer le placeholder `{activity}` dans le template
    `scope_singular` de la typologie COMMERCE :
    `"votre {activity}"` → `"votre boulangerie"` (NAF 4724Z).

    Args:
        naf_code: code NAF complet (ex: "4724Z"). Peut être None.
        fallback: valeur par défaut si NAF inconnu (par défaut "magasin").

    Returns:
        Nom métier concret en français (str).

    Examples:
        >>> get_activity_name("4724Z")
        'boulangerie'
        >>> get_activity_name("5510Z")
        'hôtel'
        >>> get_activity_name(None)
        'magasin'
        >>> get_activity_name("ZZZZZ")
        'magasin'
    """
    if not naf_code:
        return fallback
    return NAF_TO_ACTIVITY_NAME.get(naf_code, fallback)


def render_scope_singular(typology: OrganizationTypology, naf_code: Optional[str] = None) -> str:
    """Rend le `scope_singular` avec interpolation `{activity}` pour Commerce.

    Pour COMMERCE : substitue `{activity}` par `get_activity_name(naf_code)`.
    Pour les autres typologies : retourne le template tel quel.

    Args:
        typology: typologie cible.
        naf_code: code NAF du site (utile uniquement pour COMMERCE).

    Returns:
        Scope singular interpolé (str).

    Examples:
        >>> render_scope_singular(OrganizationTypology.COMMERCE, "4724Z")
        'votre boulangerie'
        >>> render_scope_singular(OrganizationTypology.COMMERCE, "5510Z")
        'votre hôtel'
        >>> render_scope_singular(OrganizationTypology.GRAND_GROUPE, "6420Z")
        'votre patrimoine'
        >>> render_scope_singular(OrganizationTypology.ERP, "8510Z")
        'votre établissement'
    """
    template = get_template(typology, "scope_singular")
    if "{activity}" in template:
        activity = get_activity_name(naf_code)
        return template.replace("{activity}", activity)
    return template


__all__ = [
    "LEXICAL_TEMPLATES",
    "NAF_TO_ACTIVITY_NAME",
    "get_template",
    "get_activity_name",
    "render_scope_singular",
]
