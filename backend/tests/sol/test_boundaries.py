"""Tests boundaries Sol V1 — out-of-scope detection + responses."""

from __future__ import annotations

import pytest

from sol.boundaries import boundary_response, is_out_of_scope


# ─────────────────────────────────────────────────────────────────────────────
# In-scope (doit retourner (False, None))
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "question",
    [
        "pourquoi ma facture Lyon est plus chère ce mois-ci ?",
        "quelle est la consommation du site Marseille ?",
        "combien vais-je payer de TURPE cette année ?",
        "peux-tu préparer ma déclaration OPERAT ?",
        "quel est mon score DT ?",
        "quand faut-il renouveler le contrat Nice ?",
        "montre-moi la courbe de charge de Paris",
        "qu'est-ce que la CTA ?",
        "",  # vide = in-scope (filter upstream)
        "   ",  # whitespace = in-scope
    ],
)
def test_in_scope_questions_not_flagged(question):
    flagged, reason = is_out_of_scope(question)
    assert flagged is False, f"Should NOT flag: {question}"
    assert reason is None


# ─────────────────────────────────────────────────────────────────────────────
# Financial advice
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "question",
    [
        "dois-je acheter en fixe ou en spot ?",
        "quand faut-il vendre ma PPA ?",
        "investir dans le solaire c'est rentable ?",
        "le bitcoin est en hausse, qu'en penses-tu ?",
        "conseille-moi une stratégie d'achat optimale",
    ],
)
def test_financial_advice_flagged(question):
    flagged, reason = is_out_of_scope(question)
    assert flagged is True
    assert reason == "financial_advice"


# ─────────────────────────────────────────────────────────────────────────────
# Legal advice
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "question",
    [
        "est-ce que ce contrat est valide juridiquement ?",
        "puis-je ester en justice contre mon fournisseur ?",
        "ce contrat est-il valable sans signature ?",
        "quelle est ma responsabilité juridique ?",
    ],
)
def test_legal_advice_flagged(question):
    flagged, reason = is_out_of_scope(question)
    assert flagged is True
    assert reason == "legal_advice"


# ─────────────────────────────────────────────────────────────────────────────
# Personal / hors produit
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "question",
    [
        "comment vas-tu ?",
        "comment ça va aujourd'hui ?",
        "tu as bien dormi ?",
        "raconte-moi une blague",
        "quel âge as-tu ?",
        "es-tu humain ?",
    ],
)
def test_personal_questions_flagged(question):
    flagged, reason = is_out_of_scope(question)
    assert flagged is True
    assert reason == "personal"


# ─────────────────────────────────────────────────────────────────────────────
# Boundary responses
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("reason_code", ["financial_advice", "legal_advice", "personal"])
def test_boundary_response_returns_string(reason_code):
    resp = boundary_response(reason_code)
    assert isinstance(resp, str)
    assert len(resp) > 30


def test_boundary_response_unknown_raises():
    with pytest.raises(KeyError):
        boundary_response("unknown_reason_code")


def test_boundary_response_applies_frenchifier():
    # Toutes les réponses boundaries passent par render_template → frenchifier
    # Elles doivent contenir vouvoiement / "je" (voice Sol)
    resp = boundary_response("financial_advice")
    assert "vous" in resp.lower() or "Je " in resp
