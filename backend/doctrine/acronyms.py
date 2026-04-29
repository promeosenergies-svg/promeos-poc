"""PROMEOS — Dictionnaire acronymes → récit (Phase 1.8 / Q6).

Source unique de vérité backend pour la transformation des acronymes
réglementaires en récit lisible. Pendant Python du dictionnaire FE
`frontend/src/domain/acronymToNarrative.js` (Phase 1.1) — utilisé par
`narrative_generator.py` pour produire des titres/cards Vue Exécutive
sans acronymes bruts.

Doctrine §6.4 (et §6.3 anti-pattern « acronymes bruts en titres ») :
toute UI Cockpit/Conformité/Bill-Intel ne doit jamais exposer
DT/BACS/GTB/TURPE/APER/OPERAT/CDC/VNU/CBAM/ARENH en titre brut.
Soit transformer en récit (mode='narrative'), soit annoter inline
(mode='inline' = "Décret Tertiaire (DT)").

Source-guard : `test_acronyms_transformed_vue_executive`.

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.8.
"""

from __future__ import annotations

import re
from typing import Literal


ACRONYM_TO_NARRATIVE: dict[str, str] = {
    # Réglementation tertiaire
    "DT": "Décret Tertiaire",
    "BACS": "Décret BACS · pilotage CVC obligatoire",
    "GTB": "système de pilotage CVC",
    "APER": "obligation solaire parking",
    "OPERAT": "déclaration énergie tertiaire annuelle",
    # Tarifs réseau & marché
    "TURPE": "tarif d'acheminement réseau",
    "ARENH": "ancien tarif réglementé (fin du dispositif)",
    "VNU": "Versement Nucléaire Universel",
    "CBAM": "taxe carbone aux frontières",
    "CEE": "Certificat d'économie d'énergie",
    "EPEX": "bourse électricité spot",
    # Indicateur technique
    "CDC": "courbe de charge 30 min",
}


# Acronymes interdits en titres bruts (subset critique du dico).
# Source-guard : si un titre Vue Exécutive contient l'un de ces tokens
# en MAJUSCULE isolée, le test FAIL.
ACRONYMS_FORBIDDEN_IN_TITLES: frozenset[str] = frozenset({"DT", "BACS", "GTB", "TURPE", "APER", "VNU", "CBAM", "ARENH"})


_TransformMode = Literal["narrative", "inline"]


def transform_acronym(text: str, *, mode: _TransformMode = "narrative") -> str:
    """Transforme les acronymes bruts d'un texte selon doctrine §6.4.

    Args:
        text: chaîne pouvant contenir des acronymes (ex: "Le DT impose…")
        mode:
          - 'narrative' : remplace l'acronyme par son récit complet
            ("Le DT impose…" → "Le Décret Tertiaire impose…")
          - 'inline' : conserve l'acronyme en parenthèses après le récit
            la 1re occurrence ("Le Décret Tertiaire (DT) impose…")

    Returns:
        Texte transformé. Les acronymes inconnus sont laissés tels quels
        (no-op safe — pas d'exception).
    """
    if not text or not isinstance(text, str):
        return text

    # Trier par longueur décroissante pour matcher OPERAT avant DT
    keys_sorted = sorted(ACRONYM_TO_NARRATIVE.keys(), key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in keys_sorted) + r")\b")
    seen_inline: set[str] = set()

    def _replace(match: re.Match) -> str:
        acr = match.group(1)
        narrative = ACRONYM_TO_NARRATIVE.get(acr, acr)
        if mode == "narrative":
            return narrative
        # mode == 'inline'
        if acr in seen_inline:
            return acr  # 2e+ occurrence = acronyme nu (déjà glossé)
        seen_inline.add(acr)
        return f"{narrative} ({acr})"

    return pattern.sub(_replace, text)


def has_forbidden_acronym(title: str) -> str | None:
    """Détecte un acronyme interdit en titre brut.

    Returns:
        Le 1er acronyme interdit trouvé, ou None si titre OK.
    """
    if not title:
        return None
    for acr in ACRONYMS_FORBIDDEN_IN_TITLES:
        if re.search(rf"\b{re.escape(acr)}\b", title):
            return acr
    return None


__all__ = [
    "ACRONYM_TO_NARRATIVE",
    "ACRONYMS_FORBIDDEN_IN_TITLES",
    "transform_acronym",
    "has_forbidden_acronym",
]
