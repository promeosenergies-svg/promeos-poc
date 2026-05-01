"""Phase 7 correctif D — Source-guards formatters canoniques narrative.

Vérifie le SoT `services/narrative/formatters.py` :
1. format_eur_short — virgule FR, fallback `—`, zéro `0 €`
2. format_eur_thousand — espace milliers
3. format_pct_short — signe explicite + minus Unicode
4. persona_context._format_eur_short alias canonique (rétrocompat tests)
5. sentence_composer._format_eur_fr / _format_pct_fr aliases canoniques

Audit final 2026-05-01 P1 : doublon `_format_eur_short` / `_fmt_eur_short`
factorisé dans `formatters.py` SoT.
"""

from __future__ import annotations

import pytest

from services.narrative.formatters import (
    format_eur_short,
    format_eur_thousand,
    format_pct_short,
)


# ─── format_eur_short SoT canonique ────────────────────────────────────────


class TestFormatEurShort:
    """Source-guards SoT canonique €/k€/M€ FR."""

    def test_thousands_virgule_fr(self):
        assert format_eur_short(12700) == "12,7 k€"

    def test_millions_virgule_fr(self):
        assert format_eur_short(1_500_000) == "1,5 M€"

    def test_under_1k(self):
        assert format_eur_short(450) == "450 €"

    def test_zero_returns_zero_eur(self):
        """Phase 7 : zéro = montant nul, différent de None (donnée absente)."""
        assert format_eur_short(0) == "0 €"

    def test_none_returns_em_dash(self):
        """Phase 7 : None = donnée absente → tiret cadratin (signal explicite)."""
        assert format_eur_short(None) == "—"

    def test_negative_value(self):
        """Valeur négative gardée (signe minus standard)."""
        result = format_eur_short(-1500)
        assert "1,5 k€" in result or "k€" in result


class TestFormatEurThousand:
    def test_simple(self):
        assert format_eur_thousand(1234) == "1 234 €"

    def test_million(self):
        assert format_eur_thousand(1_234_567) == "1 234 567 €"


class TestFormatPctShort:
    def test_positive_with_explicit_sign(self):
        assert format_pct_short(14.3) == "+14 %"

    def test_negative_unicode_minus(self):
        """Phase 7 : − Unicode (pas hyphen ASCII)."""
        assert format_pct_short(-12.7) == "−13 %"

    def test_zero(self):
        assert format_pct_short(0) == "0 %"


# ─── Backward-compat aliases ───────────────────────────────────────────────


class TestPersonaContextAlias:
    """persona_context._format_eur_short doit pointer sur format_eur_short SoT."""

    def test_persona_context_alias_canonical(self):
        from services.narrative.persona_context import _format_eur_short

        assert _format_eur_short is format_eur_short


class TestSentenceComposerAliases:
    """sentence_composer aliases pointent sur SoT canonique."""

    def test_eur_fr_alias_canonical(self):
        from services.narrative.sentence_composer import _format_eur_fr

        assert _format_eur_fr is format_eur_thousand

    def test_pct_fr_alias_canonical(self):
        from services.narrative.sentence_composer import _format_pct_fr

        assert _format_pct_fr is format_pct_short


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
