"""Persona context — Sprint Refonte Narrative dynamique Phase 4.1.

Mention persona italique (Option 1.C) : injecte une phrase courte adaptée
au rôle de l'utilisateur courant, en italique, sous le récit principal.

## Format cible (audit doctrine §11.3)

> *Pour Marie, DAF ETI tertiaire : exposition financière contenue 12,7 k€,
> trajectoire 2030 à -3,2 % vs cible.*

## Pourquoi par rôle ?

Doctrine §11.3 — chaque persona arbitre sur des indicateurs différents :
- **CFO** : P&L, exposition financière, ratio CAPEX/payback
- **DG** : trajectoire stratégique, score conformité global
- **Asset Manager** : performance asset (€/m², m² sous contrôle)
- **Property Manager** : opérationnel (échéances site, anomalies)
- **Energy Manager** : kWh/m², dérive vs baseline, leviers MWh/an
- **Director ERP** : service public + budget établissement
- **Owner Commerce** : économies directes €/mois, surcoût immédiat

Une phrase générique noierait le signal. Une phrase rôle-adaptée ouvre
la lecture par "ce qui parle à VOUS aujourd'hui".

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 4.1 + Option 1.C.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from doctrine.naf_to_typology import OrganizationTypology


class PersonaRole(str, Enum):
    """9 rôles persona canoniques (Phase 4.1 + Phase 4.bis3 corrections audit)."""

    DG = "dg"  # Directeur général
    CFO = "cfo"  # Directeur financier
    ASSET_MANAGER = "asset_manager"  # Asset Manager (immo investisseur)
    PROPERTY_MANAGER = "property_manager"  # Property Manager (gestion locative)
    ENERGY_MANAGER = "energy_manager"  # Responsable énergie/EM
    DIRECTOR_ERP = "director_erp"  # Directeur d'établissement public
    OWNER_COMMERCE = "owner_commerce"  # Propriétaire commerçant
    # Phase 4.bis3 corrections audit CX (gap stratégique roadmap)
    ENERGY_BUYER = "energy_buyer"  # Acheteur énergie (PR #239 post-ARENH)
    CSR_MANAGER = "csr_manager"  # Responsable RSE / CSRD (CBAM scope 1-2-3)


# Libellés FR courts à injecter dans la phrase persona.
PERSONA_ROLE_LABEL: dict[PersonaRole, str] = {
    PersonaRole.DG: "DG",
    PersonaRole.CFO: "DAF",
    PersonaRole.ASSET_MANAGER: "Asset Manager",
    PersonaRole.PROPERTY_MANAGER: "Property Manager",
    PersonaRole.ENERGY_MANAGER: "Energy Manager",
    PersonaRole.DIRECTOR_ERP: "directeur d'établissement",
    PersonaRole.OWNER_COMMERCE: "propriétaire",
    PersonaRole.ENERGY_BUYER: "acheteur énergie",
    PersonaRole.CSR_MANAGER: "responsable RSE",
}


# Mapping persona → focus métier (axes d'arbitrage prioritaires).
PERSONA_FOCUS: dict[PersonaRole, str] = {
    PersonaRole.CFO: "exposition financière + trajectoire",
    PersonaRole.DG: "stratégie + conformité globale",
    PersonaRole.ASSET_MANAGER: "performance asset (€/m²)",
    PersonaRole.PROPERTY_MANAGER: "opérationnel sites + échéances",
    PersonaRole.ENERGY_MANAGER: "leviers énergétiques MWh/an",
    PersonaRole.DIRECTOR_ERP: "service public + budget établissement",
    PersonaRole.OWNER_COMMERCE: "économies directes mensuelles",
    PersonaRole.ENERGY_BUYER: "prix moyen €/MWh + bande tolérance",
    PersonaRole.CSR_MANAGER: "tCO₂e scope 1-2-3 + reporting CSRD",
}


# Phase 7 correctif D — délégation au SoT canonique services/narrative/formatters.py
# Conserve l'alias _format_eur_short pour rétrocompat des tests.
from services.narrative.formatters import format_eur_short as _format_eur_short  # noqa: F401


def compute_persona_focus_text(
    role: PersonaRole,
    facts: dict,
    typology: OrganizationTypology,
) -> str:
    """Compute le texte focus chiffré adapté au rôle.

    Lit les faits canoniques (`facts`) et compose une phrase courte
    qui parle à l'arbitrage du rôle. Si les facts manquent, fallback
    sur le focus générique non-chiffré.

    Args:
        role: rôle persona (PersonaRole).
        facts: dict avec clés possibles `exposure_eur`, `compliance_score`,
            `levers_mwh_year`, `surcout_eur_mois`, etc.
        typology: typologie organisationnelle (Phase 1.2).

    Returns:
        Texte focus court (ex: "exposition 12,7 k€, trajectoire 78/100").
    """
    if role == PersonaRole.CFO:
        exposure = facts.get("exposure_eur")
        score = facts.get("compliance_score")
        if exposure is not None and score is not None:
            return f"exposition {_format_eur_short(exposure)}, trajectoire {score}/100"
        if exposure is not None:
            return f"exposition financière {_format_eur_short(exposure)}"
        return PERSONA_FOCUS[role]

    if role == PersonaRole.DG:
        score = facts.get("compliance_score")
        if score is not None:
            return f"trajectoire 2030 à {score}/100"
        return PERSONA_FOCUS[role]

    if role == PersonaRole.ENERGY_MANAGER:
        mwh = facts.get("levers_mwh_year")
        if mwh is not None:
            return f"potentiel {round(mwh)} MWh/an mobilisable"
        return PERSONA_FOCUS[role]

    if role == PersonaRole.OWNER_COMMERCE:
        # Commerce : on parle € direct, pas score abstrait
        surcout = facts.get("surcout_eur_mois")
        if surcout is not None:
            return f"surcoût mensuel {_format_eur_short(surcout)}"
        return PERSONA_FOCUS[role]

    if role == PersonaRole.DIRECTOR_ERP:
        score = facts.get("compliance_score")
        if score is not None:
            return f"conformité service public {score}/100"
        return PERSONA_FOCUS[role]

    if role == PersonaRole.ENERGY_BUYER:
        # Phase 4.bis3 audit gap stratégique : acheteur énergie post-ARENH
        # focus prix + bande tolérance contractuelle.
        prix_mwh = facts.get("avg_price_eur_mwh")
        if prix_mwh is not None:
            return f"prix moyen {round(prix_mwh)} €/MWh"
        return PERSONA_FOCUS[role]

    if role == PersonaRole.CSR_MANAGER:
        # Phase 4.bis3 audit gap stratégique : RSE / CBAM
        co2 = facts.get("emissions_tco2e")
        if co2 is not None:
            return f"émissions {round(co2)} tCO₂e (scope 1-2-3)"
        return PERSONA_FOCUS[role]

    # ASSET_MANAGER, PROPERTY_MANAGER : focus générique pour V1
    return PERSONA_FOCUS.get(role, "vue synthétique")


def _resolve_role_label(user_role: PersonaRole, typology: OrganizationTypology, naf_code: Optional[str]) -> str:
    """Résout le libellé rôle adapté à la typologie + NAF (Phase 4.bis3 audit CX).

    Pour OWNER_COMMERCE, "propriétaire" générique remplacé par le métier
    réel : "boulanger" (NAF 4724Z), "restaurateur" (5610A), "hôtelier" (5510Z).
    Tombe sur "propriétaire" si NAF absent ou typologie non-Commerce.
    """
    if user_role != PersonaRole.OWNER_COMMERCE:
        return PERSONA_ROLE_LABEL.get(user_role, "responsable")

    # OWNER_COMMERCE — métier réel via NAF
    from services.narrative.lexical_templates import get_activity_name

    activity = get_activity_name(naf_code, fallback="propriétaire")
    # Mapping court "boulangerie" → "boulanger" (forme persona)
    activity_to_persona = {
        "boulangerie": "boulanger",
        "boucherie": "boucher",
        "poissonnerie": "poissonnier",
        "primeur": "primeur",
        "épicerie": "épicier",
        "pharmacie": "pharmacien",
        "restaurant": "restaurateur",
        "hôtel": "hôtelier",
        "café-bar": "patron de café",
    }
    return activity_to_persona.get(activity, "propriétaire")


def compose_persona_mention(
    user_first_name: str,
    user_role: PersonaRole,
    facts: dict,
    typology: OrganizationTypology,
    naf_code: Optional[str] = None,
) -> str:
    """Compose la mention persona italique (Option 1.C).

    Format : "Pour {Prénom}, {rôle} : {focus chiffré}"

    Phase 4.bis3 : `naf_code` permet l'adaptation Commerce —
    "Hervé, propriétaire" → "Hervé, boulanger" si NAF 4724Z passé.

    Args:
        user_first_name: prénom utilisateur (ex: "Marie", "Jean-Marc").
        user_role: rôle PersonaRole.
        facts: faits canoniques (cf compute_persona_focus_text).
        typology: typologie organisationnelle.
        naf_code: code NAF (utile pour OWNER_COMMERCE — Phase 4.bis3).

    Returns:
        Phrase courte prête à wrapper en `<em>` dans le frontend.
        Ex: "Pour Marie, DAF : exposition 12,7 k€, trajectoire 78/100"
        Ex: "Pour Hervé, boulanger : surcoût mensuel 230 €"  (Phase 4.bis3)

    Examples:
        >>> compose_persona_mention(
        ...     "Marie", PersonaRole.CFO,
        ...     {"exposure_eur": 12700, "compliance_score": 78},
        ...     OrganizationTypology.GRAND_GROUPE,
        ... )
        'Pour Marie, DAF : exposition 12,7 k€, trajectoire 78/100'

        >>> compose_persona_mention(
        ...     "Hervé", PersonaRole.OWNER_COMMERCE,
        ...     {"surcout_eur_mois": 230},
        ...     OrganizationTypology.COMMERCE,
        ...     naf_code="4724Z",
        ... )
        'Pour Hervé, boulanger : surcoût mensuel 230 €'
    """
    focus_text = compute_persona_focus_text(user_role, facts, typology)
    role_label = _resolve_role_label(user_role, typology, naf_code)
    # Capitalisation préservée du prénom (peut contenir tiret/composé)
    return f"Pour {user_first_name}, {role_label} : {focus_text}"


__all__ = [
    "PersonaRole",
    "PERSONA_ROLE_LABEL",
    "PERSONA_FOCUS",
    "compute_persona_focus_text",
    "compose_persona_mention",
]
