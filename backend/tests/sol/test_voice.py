"""Tests voice Sol V1 — frenchifier (grammaire FR) + templates V1."""

from __future__ import annotations

import pytest

from sol.voice import SOL_VOICE_TEMPLATES_V1, frenchifier, render_template


_NBSP = "\u00A0"
_NNBSP = "\u202F"
_EMDASH = "\u2014"
_ENDASH = "\u2013"


# ─────────────────────────────────────────────────────────────────────────────
# Frenchifier — purity & idempotence
# ─────────────────────────────────────────────────────────────────────────────


def test_frenchifier_empty_string():
    assert frenchifier("") == ""


def test_frenchifier_no_change_on_clean_text():
    text = "Bonjour, voici votre semaine."
    # Pas d'espace fine après bonjour, donc result = input
    assert frenchifier(text) == text


def test_frenchifier_idempotent_generic():
    for text in [
        "La confiance est à 85 %.",
        "Récupération : 1 847 €",
        "Mise en garde ! Attention ?",
        'Le message "bonjour" est bref.',
        "Incise -- avec tirets -- ici.",
        "Sur la période 2024-2026.",
        "Le 1er jour.",
        "Economie de temps.",
    ]:
        once = frenchifier(text)
        twice = frenchifier(once)
        assert once == twice, f"Not idempotent for: {text!r}"


# ─────────────────────────────────────────────────────────────────────────────
# Frenchifier — règles spécifiques
# ─────────────────────────────────────────────────────────────────────────────


def test_frenchifier_fine_space_before_colon():
    result = frenchifier("Écart : 4,27 €/MWh")
    assert _NNBSP + ":" in result


def test_frenchifier_fine_space_before_percent():
    result = frenchifier("Confiance à 94 %.")
    assert _NNBSP + "%" in result


def test_frenchifier_fine_space_before_euro():
    result = frenchifier("Montant : 1847 €.")
    # Après frenchifier : ":" et "€" doivent être précédés de U+202F
    assert _NNBSP + "€" in result


def test_frenchifier_fine_space_before_question_mark():
    result = frenchifier("Voulez-vous continuer ?")
    assert _NNBSP + "?" in result


def test_frenchifier_fine_space_before_exclamation():
    result = frenchifier("Validé !")
    assert _NNBSP + "!" in result


def test_frenchifier_fine_space_before_semicolon():
    result = frenchifier("D'abord ; ensuite.")
    assert _NNBSP + ";" in result


def test_frenchifier_replaces_straight_quotes_with_chevrons():
    result = frenchifier('Le terme "accise" s\'applique ici.')
    assert "«" in result and "»" in result
    assert '"' not in result


def test_frenchifier_chevrons_have_nbsp():
    result = frenchifier('Contestation "validée" le 14 avril.')
    # « U+00A0 validée U+00A0 »
    assert f"«{_NBSP}validée{_NBSP}»" in result


def test_frenchifier_replaces_double_dashes_with_emdash():
    result = frenchifier("Voici -- et c'est normal -- votre semaine.")
    assert _EMDASH in result
    assert "--" not in result


def test_frenchifier_date_range_with_endash():
    result = frenchifier("Période 2024-2026.")
    assert f"2024{_ENDASH}2026" in result


def test_frenchifier_date_range_does_not_modify_short_ids():
    # PDL-style refs, SIRET, etc. ne doivent pas être convertis
    result = frenchifier("PDL 14500-1234.")
    # "1234" n'a pas de 4 chiffres-4 chiffres pattern isolé, donc OK
    assert "14500-1234" in result


def test_frenchifier_ordinal_1er():
    assert "1ᵉʳ" in frenchifier("Le 1er jour du mois.")


def test_frenchifier_ordinal_numeric():
    assert "2ᵉ" in frenchifier("Notre 2eme expérience.")
    assert "3ᵉ" in frenchifier("Le 3ème trimestre.")


def test_frenchifier_accent_economie_at_start():
    assert frenchifier("Economie de 400 €.").startswith("Éco")


def test_frenchifier_accent_a_faire_at_start():
    assert frenchifier("A faire cette semaine.").startswith("À")


def test_frenchifier_does_not_modify_technical_sentinels():
    # TURPE, CTA, MWh ne doivent jamais être modifiés
    for term in ["TURPE", "CTA", "MWh", "kWh", "ENEDIS", "GRDF", "PDL", "TVA"]:
        text = f"Le {term} s'applique."
        result = frenchifier(text)
        assert term in result, f"{term} muté: {result}"


# ─────────────────────────────────────────────────────────────────────────────
# Templates V1
# ─────────────────────────────────────────────────────────────────────────────


def test_templates_v1_non_empty():
    assert len(SOL_VOICE_TEMPLATES_V1) >= 20  # au moins 20 templates


def test_render_template_substitutes_variables():
    out = render_template(("propose", "invoice_dispute"), {
        "site": "Lyon",
        "period": "mars",
        "anomaly_reason": "L'accise T1 a été appliquée au lieu de T2",
        "grace_hours": 24,
    })
    assert "Lyon" in out
    assert "mars" in out


def test_render_template_applies_frenchifier():
    out = render_template(("refuse", "confidence_low"), {
        "conf_pct": "78 %",
        "threshold_pct": "85 %",
    })
    # U+202F doit apparaître avant les %
    assert _NNBSP + "%" in out


def test_render_template_unknown_key_raises():
    with pytest.raises(KeyError, match="not found"):
        render_template(("unknown", "missing"), {})


def test_render_template_missing_var_preserves_placeholder():
    # _SafeDict __missing__ retourne "{key}"
    out = render_template(("propose", "invoice_dispute"), {"site": "Lyon"})
    # Les autres placeholders doivent rester visibles (pas crash silencieux)
    assert "{period}" in out or "period" in out


def test_all_boundary_templates_renderable():
    for code in ("financial_advice", "legal_advice", "personal"):
        out = render_template(("boundary", code), {})
        assert len(out) > 20
        # Chaque réponse boundary doit être vouvoyée
        assert " vous" in out.lower() or "Je " in out


def test_render_template_no_straight_quotes_in_rendered():
    # Le guide interdit guillemets droits en production
    for key, template in SOL_VOICE_TEMPLATES_V1.items():
        # Les templates peuvent contenir " uniquement pour l'interpolation
        # (format_map Python). En l'absence de variable, pas de " restant.
        if "{" not in template:
            assert '"' not in frenchifier(template), f"Template {key} has straight quotes"
