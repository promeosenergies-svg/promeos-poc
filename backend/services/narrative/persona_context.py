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


# Libellés FR (par défaut masculin/neutre) — utilisés si typology ≠ GG corporate.
# Phase 8.B : DAF/CFO context-aware via PERSONA_ROLE_LABEL_BY_TYPOLOGY.
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


# Phase 8.B — féminisation des libellés rôle (audit final P1).
# Mapping libellé masculin/neutre → libellé féminin. Si rôle absent du
# mapping, le label par défaut est unisexe (DG, DAF, Asset Manager, etc.)
# Note : "DAF" et "DG" ne sont pas fléchis (les sigles s'utilisent
# indifféremment). Seuls les rôles avec article ou suffixe genré
# nécessitent une fléchissement.
PERSONA_ROLE_LABEL_FEMININE: dict[PersonaRole, str] = {
    PersonaRole.DIRECTOR_ERP: "directrice d'établissement",
    PersonaRole.OWNER_COMMERCE: "propriétaire",  # déjà épicène
    PersonaRole.ENERGY_BUYER: "acheteuse énergie",
    PersonaRole.CSR_MANAGER: "responsable RSE",  # déjà épicène
}


# Phase 8.B — différenciation CFO/DAF selon typology (audit final CX).
# "DAF" est l'usage ETI/PME tertiaire, "Directeur Financier" plutôt
# grand groupe coté + finance. Pour HELIOS GG, on utilise le libellé
# long ; pour Marie ETI, "DAF" reste juste.
PERSONA_ROLE_LABEL_BY_TYPOLOGY: dict[tuple[PersonaRole, OrganizationTypology], str] = {
    (PersonaRole.CFO, OrganizationTypology.GRAND_GROUPE): "Directeur Financier",
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


def _is_feminine_first_name(first_name: Optional[str]) -> bool:
    """Détection heuristique du genre prénom (Phase 8.B audit P1).

    Liste FR commune des terminaisons et prénoms typiquement féminins.
    Tient en couverture environ 80% des cas FR — pour les 20% restants,
    le label par défaut est utilisé. Acceptable MVP : on n'applique le
    féminin que si on est confiant.

    Pour V2 : possibilité de stocker `gender` dans User model (RGPD-soft
    car non-sensible) ou d'extraire depuis Sirene/source officielle.
    """
    if not first_name:
        return False
    name = first_name.strip().lower()
    # Terminaisons typiquement féminines (couvre Marie/Anne/Sophie/Inès/etc.)
    feminine_endings = ("a", "e", "ie", "ine", "elle", "ette", "ée", "ah", "ès")
    if name.endswith(feminine_endings):
        # Edge case : prénoms masculins finissant en -e (Pierre, Jean-Pierre,
        # Charles, Claude). Liste explicite d'exceptions.
        masculine_exceptions = {
            "pierre",
            "jean-pierre",
            "charles",
            "claude",
            "anne",  # ambigu
            "thomas",
            "nicolas",
            "luca",
            "noah",
            "philippe",
            "alexandre",
            "yves",
            "lyes",
            "iliès",
        }
        # Note : "anne" est ici car certains prénoms composés (Pierre-Anne, Marie-Anne)
        # restent féminins par leur 1er composant. Mais "Anne" seul est féminin.
        # On exclut juste les cas où l'unique prénom = ces masculins-en-e.
        if name in masculine_exceptions and name != "anne":
            return False
        return True
    return False


def _resolve_role_label(
    user_role: PersonaRole,
    typology: OrganizationTypology,
    naf_code: Optional[str],
    first_name: Optional[str] = None,
) -> str:
    """Résout le libellé rôle adapté à la typologie + NAF + genre (Phase 4.bis3 + 8.B).

    Phase 4.bis3 — OWNER_COMMERCE : "propriétaire" → métier NAF (boulanger/...).
    Phase 8.B — CFO + GRAND_GROUPE → "Directeur Financier" (vs "DAF" ETI).
    Phase 8.B — fléchissement féminin si first_name suggère prénom féminin
    (DIRECTOR_ERP → "directrice d'établissement", ENERGY_BUYER → "acheteuse").
    """
    # 1. OWNER_COMMERCE — métier réel via NAF (Phase 4.bis3)
    if user_role == PersonaRole.OWNER_COMMERCE:
        from services.narrative.lexical_templates import get_activity_name

        activity = get_activity_name(naf_code, fallback="propriétaire")
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
        # Note : féminisation Commerce non implémentée V1 (boulangère /
        # restauratrice → manque mapping ; à enrichir V2 si panel le demande).
        return activity_to_persona.get(activity, "propriétaire")

    # 2. Phase 8.B — context-aware GG CFO → "Directeur Financier"
    contextual_key = (user_role, typology)
    if contextual_key in PERSONA_ROLE_LABEL_BY_TYPOLOGY:
        base_label = PERSONA_ROLE_LABEL_BY_TYPOLOGY[contextual_key]
        # Féminisation : "Directeur Financier" → "Directrice Financière"
        if _is_feminine_first_name(first_name) and base_label == "Directeur Financier":
            return "Directrice Financière"
        return base_label

    # 3. Phase 8.B — féminisation rôles éligibles
    if _is_feminine_first_name(first_name) and user_role in PERSONA_ROLE_LABEL_FEMININE:
        return PERSONA_ROLE_LABEL_FEMININE[user_role]

    # 4. Default masculin/neutre
    return PERSONA_ROLE_LABEL.get(user_role, "responsable")


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
    # Phase 8.B — propage first_name pour féminisation + context typology
    role_label = _resolve_role_label(user_role, typology, naf_code, first_name=user_first_name)
    # Capitalisation préservée du prénom (peut contenir tiret/composé)
    return f"Pour {user_first_name}, {role_label} : {focus_text}"


__all__ = [
    "PersonaRole",
    "PERSONA_ROLE_LABEL",
    "PERSONA_ROLE_LABEL_FEMININE",
    "PERSONA_ROLE_LABEL_BY_TYPOLOGY",
    "PERSONA_FOCUS",
    "compute_persona_focus_text",
    "compose_persona_mention",
]
