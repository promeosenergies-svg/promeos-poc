"""
Boundaries Sol V1 : détection des questions hors scope + réponses cadrées.

Sol V1 est spécialisé énergie + réglementation FR. Pour toute autre
demande (conseil financier, juridique, personnel…) → refus explicite avec
remediation humaine.

Utilisé par Phase 4 route `/api/sol/ask` (Mode 2 conversation) pour
filtrer les questions avant d'appeler l'engine ou le LLM.
"""

from __future__ import annotations

import re
from typing import Pattern

from .voice import render_template


# ─────────────────────────────────────────────────────────────────────────────
# Patterns de détection (case-insensitive)
# ─────────────────────────────────────────────────────────────────────────────


# Chaque tuple : (pattern compilé, reason_code)
_PATTERNS: list[tuple[Pattern[str], str]] = [
    # Conseil financier / investissement
    (
        re.compile(
            r"\b(acheter|vendre|investir|trader|crypto|bitcoin|bourse|action|dividende|placement|"
            r"stratégie.*d.?achat)\b",
            re.IGNORECASE,
        ),
        "financial_advice",
    ),
    # Conseil juridique explicite
    (
        re.compile(
            r"(valide\s+juridiquement|ester\s+en\s+justice|contrat.*est.*valable|"
            r"responsabilité.*juridique|mon\s+juriste|c.?est\s+l[ée]gal)",
            re.IGNORECASE,
        ),
        "legal_advice",
    ),
    # Personnel / hors produit
    (
        re.compile(
            r"(comment\s+(vas[- ]tu|ça\s+va)|tu\s+as\s+bien\s+dormi|raconte[- ]moi|"
            r"quel\s+âge\s+as[- ]tu|t[ue][s]?\s+une\s+ia|es[- ]tu\s+humain)",
            re.IGNORECASE,
        ),
        "personal",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# API publique
# ─────────────────────────────────────────────────────────────────────────────


def is_out_of_scope(question_fr: str) -> tuple[bool, str | None]:
    """
    Détecte si une question utilisateur sort du scope Sol énergie + réglementation.

    Retourne :
    - `(True, reason_code)` si hors scope → appelant doit afficher
      `boundary_response(reason_code)` au lieu d'appeler l'engine/LLM
    - `(False, None)` si dans scope → poursuivre traitement normal

    `reason_code` ∈ {financial_advice, legal_advice, personal}.

    Conçu conservateur : faux positifs acceptables (meilleure UX de dire
    "je peux comparer les scénarios…" que de donner un conseil
    financier par erreur).
    """
    if not question_fr or not question_fr.strip():
        return (False, None)

    for pattern, reason_code in _PATTERNS:
        if pattern.search(question_fr):
            return (True, reason_code)

    return (False, None)


def boundary_response(reason_code: str) -> str:
    """
    Retourne la réponse Sol FR cadrée pour un reason_code donné.

    Chaque réponse est issue de `SOL_VOICE_TEMPLATES_V1` via
    `render_template(("boundary", reason_code))` — passe donc par
    `frenchifier()` automatiquement.

    Lève KeyError si reason_code inconnu (force un fix explicit dans
    le template store plutôt qu'un fallback silencieux).
    """
    return render_template(("boundary", reason_code), {})


__all__ = [
    "is_out_of_scope",
    "boundary_response",
]
