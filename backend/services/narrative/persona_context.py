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
    """7 rôles persona canoniques (extensible V2)."""

    DG = "dg"  # Directeur général
    CFO = "cfo"  # Directeur financier
    ASSET_MANAGER = "asset_manager"  # Asset Manager (immo investisseur)
    PROPERTY_MANAGER = "property_manager"  # Property Manager (gestion locative)
    ENERGY_MANAGER = "energy_manager"  # Responsable énergie/EM
    DIRECTOR_ERP = "director_erp"  # Directeur d'établissement public
    OWNER_COMMERCE = "owner_commerce"  # Propriétaire commerçant


# Libellés FR courts à injecter dans la phrase persona.
# Ordre : féminin / masculin (le caller choisit selon prénom user).
PERSONA_ROLE_LABEL: dict[PersonaRole, str] = {
    PersonaRole.DG: "DG",
    PersonaRole.CFO: "DAF",
    PersonaRole.ASSET_MANAGER: "Asset Manager",
    PersonaRole.PROPERTY_MANAGER: "Property Manager",
    PersonaRole.ENERGY_MANAGER: "Energy Manager",
    PersonaRole.DIRECTOR_ERP: "directeur d'établissement",
    PersonaRole.OWNER_COMMERCE: "propriétaire",
}


# Mapping persona → focus métier (axes d'arbitrage prioritaires).
# Utilisé pour formuler la phrase persona en s'alignant sur ce qui
# importe pour ce rôle.
PERSONA_FOCUS: dict[PersonaRole, str] = {
    PersonaRole.CFO: "exposition financière + trajectoire",
    PersonaRole.DG: "stratégie + conformité globale",
    PersonaRole.ASSET_MANAGER: "performance asset (€/m²)",
    PersonaRole.PROPERTY_MANAGER: "opérationnel sites + échéances",
    PersonaRole.ENERGY_MANAGER: "leviers énergétiques MWh/an",
    PersonaRole.DIRECTOR_ERP: "service public + budget établissement",
    PersonaRole.OWNER_COMMERCE: "économies directes mensuelles",
}


def _format_eur_short(value: Optional[float]) -> str:
    """Formatage court € (k€, M€) pour mention persona inline.

    Examples:
        >>> _format_eur_short(12750)
        '12,7 k€'
        >>> _format_eur_short(1500000)
        '1,5 M€'
        >>> _format_eur_short(450)
        '450 €'
    """
    if value is None:
        return "—"
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f} M€".replace(".", ",")
    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f} k€".replace(".", ",")
    return f"{round(value)} €"


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

    # ASSET_MANAGER, PROPERTY_MANAGER : focus générique pour V1
    return PERSONA_FOCUS.get(role, "vue synthétique")


def compose_persona_mention(
    user_first_name: str,
    user_role: PersonaRole,
    facts: dict,
    typology: OrganizationTypology,
) -> str:
    """Compose la mention persona italique (Option 1.C).

    Format : "Pour {Prénom}, {rôle} : {focus chiffré}"

    Args:
        user_first_name: prénom utilisateur (ex: "Marie", "Jean-Marc").
        user_role: rôle PersonaRole.
        facts: faits canoniques (cf compute_persona_focus_text).
        typology: typologie organisationnelle.

    Returns:
        Phrase courte prête à wrapper en `<em>` dans le frontend.
        Ex: "Pour Marie, DAF : exposition 12,7 k€, trajectoire 78/100"

    Examples:
        >>> compose_persona_mention(
        ...     "Marie", PersonaRole.CFO,
        ...     {"exposure_eur": 12750, "compliance_score": 78},
        ...     OrganizationTypology.GRAND_GROUPE,
        ... )
        'Pour Marie, DAF : exposition 12,7 k€, trajectoire 78/100'
    """
    focus_text = compute_persona_focus_text(user_role, facts, typology)
    role_label = PERSONA_ROLE_LABEL.get(user_role, "responsable")
    # Capitalisation préservée du prénom (peut contenir tiret/composé)
    return f"Pour {user_first_name}, {role_label} : {focus_text}"


__all__ = [
    "PersonaRole",
    "PERSONA_ROLE_LABEL",
    "PERSONA_FOCUS",
    "compute_persona_focus_text",
    "compose_persona_mention",
]
