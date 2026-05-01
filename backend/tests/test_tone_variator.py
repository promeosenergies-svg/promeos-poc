"""Phase 4.2 — Source-guards variation tonale lexicale.

Vérifie :
1. Tone CRITICAL transforme "stable" / "patrimoine bien positionné" en
   "écart critique" / "patrimoine en écart critique"
2. Tone POSITIVE transforme "écart significatif" en "objectif sur la bonne voie"
3. Tone TENSION transforme "stable" en "sous vigilance"
4. Tone NEUTRAL n'a pas d'impact (identité)
5. Aucun `.lower()` casse les sigles (TURPE/OPERAT préservés)
6. Tone inconnu → body inchangé (fallback safe)

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 4.2.
"""

from __future__ import annotations

import pytest

from doctrine.naf_to_typology import OrganizationTypology
from services.narrative.tone_variator import (
    TONE_LEXICAL_VARIANTS,
    apply_tone_variation,
    get_tone_marker_count,
)


# ─── Tests transformations tonales ──────────────────────────────────────────


class TestApplyToneCritical:
    """Source-guards : tone CRITICAL → registre d'urgence."""

    def test_critical_replaces_stable_with_ecart(self):
        body = "Score 80/100, stable cette semaine."
        result = apply_tone_variation(body, "critical")
        assert "stable" not in result
        assert "écart significatif" in result

    def test_critical_replaces_patrimoine_positionne(self):
        # Narrative_generator emit en lowercase "patrimoine bien positionné"
        # (cf week_cards good_news cockpit_comex). Marker case-sensitive.
        body = "Score 80/100 — patrimoine bien positionné, trajectoire 2030."
        result = apply_tone_variation(body, "critical")
        assert "bien positionné" not in result
        assert "écart critique" in result

    def test_critical_replaces_codir_present_with_arbitrer_urgence(self):
        body = "Synthèse à présenter en l'état au prochain CODIR."
        result = apply_tone_variation(body, "critical")
        assert "à arbitrer en urgence" in result


class TestApplyTonePositive:
    """Source-guards : tone POSITIVE → registre confiant."""

    def test_positive_replaces_ecart_with_bonne_voie(self):
        body = "Score 76/100, écart significatif vs cible 2030."
        result = apply_tone_variation(body, "positive")
        assert "écart significatif" not in result
        assert "bonne voie" in result

    def test_positive_replaces_stable_with_favorable(self):
        body = "Trajectoire stable cette semaine."
        result = apply_tone_variation(body, "positive")
        assert "favorable" in result

    def test_positive_replaces_codir_with_valoriser(self):
        body = "Patrimoine à présenter en l'état au prochain CODIR."
        result = apply_tone_variation(body, "positive")
        assert "à valoriser" in result


class TestApplyToneTension:
    """Source-guards : tone TENSION → registre de vigilance."""

    def test_tension_replaces_stable_with_vigilance(self):
        body = "Score 70/100, stable."
        result = apply_tone_variation(body, "tension")
        assert "sous vigilance" in result

    def test_tension_replaces_codir_with_arbitrer(self):
        body = "Patrimoine à présenter en l'état au prochain CODIR."
        result = apply_tone_variation(body, "tension")
        assert "à arbitrer" in result


class TestApplyToneNeutral:
    """Source-guards : tone NEUTRAL = identité."""

    def test_neutral_does_not_modify(self):
        body = "Score 60/100, vue stable. Patrimoine bien positionné."
        result = apply_tone_variation(body, "neutral")
        assert result == body


# ─── Tests robustesse ───────────────────────────────────────────────────────


class TestRobustness:
    """Source-guards : robustesse aux entrées edge."""

    def test_unknown_tone_fallback_identity(self):
        body = "Score 80/100, stable."
        result = apply_tone_variation(body, "tone_inconnu_xyz")
        assert result == body  # fallback identité

    def test_empty_body(self):
        assert apply_tone_variation("", "critical") == ""

    def test_no_marker_present_returns_unchanged(self):
        """Si aucun marqueur connu présent, body reste inchangé."""
        body = "Anomalie TURPE 6 détectée sur PDL 14529."
        result = apply_tone_variation(body, "critical")
        assert result == body  # Aucun marqueur → identité

    def test_sigles_preserved_critical(self):
        """Aucun .lower() — sigles TURPE/OPERAT/CODIR préservés."""
        body = "TURPE et OPERAT inchangés cette semaine, stable."
        result = apply_tone_variation(body, "critical")
        assert "TURPE" in result  # sigle préservé
        assert "OPERAT" in result
        # Mais "stable" remplacé
        assert "stable" not in result

    def test_replacement_order_long_first(self):
        """'écart significatif' ne doit pas être avalé par remplacement de 'stable'."""
        # Si on remplace "stable" → X avant "écart significatif" → Y,
        # le résultat reste cohérent (les deux marqueurs cohabitent OK).
        body = "Vue stable. Mais écart significatif sur site 3."
        result = apply_tone_variation(body, "positive")
        # "stable" remplacé en "favorable", "écart significatif" remplacé
        # en "objectif sur la bonne voie"
        assert "favorable" in result
        assert "bonne voie" in result


# ─── Tests coverage ─────────────────────────────────────────────────────────


class TestCoverage:
    """Source-guards : couverture exhaustive des tones canoniques."""

    @pytest.mark.parametrize("tone", ["positive", "neutral", "tension", "critical"])
    def test_all_canonical_tones_in_variants(self, tone):
        """Les 4 tones NarrativeTone canoniques ont une entrée TONE_LEXICAL_VARIANTS."""
        assert tone in TONE_LEXICAL_VARIANTS

    def test_get_tone_marker_count_critical_has_markers(self):
        """CRITICAL a au moins 3 marqueurs (couverture minimale)."""
        assert get_tone_marker_count("critical") >= 3

    def test_neutral_has_zero_markers(self):
        """NEUTRAL est l'identité (0 marqueurs)."""
        assert get_tone_marker_count("neutral") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
