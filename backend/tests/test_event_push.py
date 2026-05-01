"""Phase 2.1 — Source-guards push événementiel "+X vs S-1".

Vérifie l'**Option 3.C** (silence éditorial strict) :

1. Variation < 5 % en relatif → push silence (sauf si seuil absolu dépassé)
2. Variation ≥ 5 % en relatif → push actif
3. Variation absolue < 1 k€ → push silence (sauf si seuil relatif dépassé)
4. Format push clause cohérent par typologie

+ cas null-safe (previous=None/0, current=None).

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 2.1.
"""

from __future__ import annotations

import pytest

from doctrine.naf_to_typology import OrganizationTypology
from services.narrative.event_push import (
    PUSH_THRESHOLDS,
    format_push_clause,
    should_push_metric,
)


# ─── Tests should_push_metric — silence éditorial Option 3.C ────────────────


class TestShouldPushMetricSilence:
    """Source-guards : silence éditorial pour variations sous seuil."""

    def test_push_silence_below_5pct(self):
        """exposure_eur : variation 3 % et abs faible → silence."""
        # 100 000 → 103 000 = +3 % ET +3 000 €
        # rel < 5 % MAIS abs > 1 000 € → push
        assert should_push_metric("exposure_eur", 103_000, 100_000) is True

        # 100 000 → 100 800 = +0,8 % ET +800 €
        # rel < 5 % ET abs < 1 000 € → silence
        assert should_push_metric("exposure_eur", 100_800, 100_000) is False

        # 100 000 → 102 000 = +2 % ET +2 000 €
        # rel < 5 % MAIS abs > 1 000 € → push (un seuil dépassé suffit)
        assert should_push_metric("exposure_eur", 102_000, 100_000) is True

    def test_push_active_above_5pct(self):
        """exposure_eur : variation 18 % → push actif (rel franchit le seuil)."""
        assert should_push_metric("exposure_eur", 118_000, 100_000) is True

    def test_push_silence_below_1keur(self):
        """exposure_eur : variation < 1 k€ ET < 5 % → silence."""
        # 100 000 → 100 800 = +0,8 % ET +800 €
        assert should_push_metric("exposure_eur", 100_800, 100_000) is False

        # 50 000 → 50 700 = +1,4 % ET +700 €
        assert should_push_metric("exposure_eur", 50_700, 50_000) is False

    def test_push_potential_mwh_year_silence_under_5(self):
        """potential_mwh_year : silence si rel < 5 % ET abs < 5 MWh."""
        # 100 → 102 = +2 % ET +2 MWh
        assert should_push_metric("potential_mwh_year", 102, 100) is False
        # 100 → 110 = +10 % → push (rel franchit)
        assert should_push_metric("potential_mwh_year", 110, 100) is True
        # 100 → 104 = +4 % ET +4 MWh → silence
        assert should_push_metric("potential_mwh_year", 104, 100) is False
        # 100 → 106 = +6 % ET +6 MWh → push (les 2 franchis)
        assert should_push_metric("potential_mwh_year", 106, 100) is True

    def test_push_compliance_score_3pct_threshold(self):
        """compliance_score : seuil 3 % uniquement (pas de seuil absolu)."""
        # 70 → 72 = +2,86 % → silence (< 3 %)
        assert should_push_metric("compliance_score", 72, 70) is False
        # 70 → 73 = +4,29 % → push (> 3 %)
        assert should_push_metric("compliance_score", 73, 70) is True

    def test_push_sites_in_drift_absolute_only(self):
        """sites_in_drift : seuil absolu 1 site uniquement."""
        # 3 → 3 → silence (pas de variation)
        assert should_push_metric("sites_in_drift", 3, 3) is False
        # 3 → 4 = +1 → push (delta = abs threshold, strict comparaison)
        assert should_push_metric("sites_in_drift", 4, 3) is True
        # 3 → 5 = +2 → push
        assert should_push_metric("sites_in_drift", 5, 3) is True


class TestShouldPushMetricEdgeCases:
    """Source-guards null-safe : cas baseline manquante."""

    def test_push_silence_when_previous_none(self):
        """previous=None → silence (pas de baseline historique seedée)."""
        assert should_push_metric("exposure_eur", 100_000, None) is False

    def test_push_silence_when_previous_zero(self):
        """previous=0 → silence (division par zéro évitée)."""
        assert should_push_metric("exposure_eur", 100_000, 0) is False

    def test_push_silence_when_current_none(self):
        """current=None → silence (métrique indisponible)."""
        assert should_push_metric("exposure_eur", None, 100_000) is False

    def test_push_unknown_metric_uses_default_5pct(self):
        """Métrique non listée → seuil par défaut 5 %."""
        # +3 % → silence
        assert should_push_metric("metric_inconnue", 103, 100) is False
        # +10 % → push
        assert should_push_metric("metric_inconnue", 110, 100) is True

    def test_push_negative_variation(self):
        """Variation négative respecte les mêmes seuils (valeur absolue)."""
        # -10 % → push
        assert should_push_metric("exposure_eur", 90_000, 100_000) is True
        # -2 % et -2 k€ → push (abs > 1 k€)
        assert should_push_metric("exposure_eur", 98_000, 100_000) is True
        # -0,5 % et -500 € → silence
        assert should_push_metric("exposure_eur", 99_500, 100_000) is False


# ─── Tests format_push_clause — adaptation typologique ──────────────────────


class TestFormatPushClauseGrandGroupe:
    """Format CFO expert : 'vs semaine précédente'."""

    def test_format_grand_groupe_positive(self):
        result = format_push_clause("exposure_eur", 118_000, 100_000, OrganizationTypology.GRAND_GROUPE)
        assert result == "+ 18 % vs semaine précédente"

    def test_format_grand_groupe_negative(self):
        result = format_push_clause("exposure_eur", 90_000, 100_000, OrganizationTypology.GRAND_GROUPE)
        assert result == "− 10 % vs semaine précédente"


class TestFormatPushClauseCommerce:
    """Format commerçant pédagogique : 'vs la semaine dernière'."""

    def test_format_commerce_positive(self):
        result = format_push_clause("potential_mwh_year", 114, 100, OrganizationTypology.COMMERCE)
        assert result == "+ 14 % vs la semaine dernière"

    def test_format_commerce_uses_la_semaine_derniere(self):
        """COMMERCE doit utiliser 'la semaine dernière' (article + adjectif)."""
        result = format_push_clause("exposure_eur", 105, 100, OrganizationTypology.COMMERCE)
        assert "la semaine dernière" in result


class TestFormatPushClauseERP:
    """Format directeur pédagogique-pro : 'vs semaine dernière' (sans article)."""

    def test_format_erp_positive(self):
        result = format_push_clause("exposure_eur", 110_000, 100_000, OrganizationTypology.ERP)
        assert result == "+ 10 % vs semaine dernière"

    def test_format_erp_no_la_article(self):
        """ERP ne doit PAS utiliser 'la semaine dernière' (article)."""
        result = format_push_clause("exposure_eur", 110_000, 100_000, OrganizationTypology.ERP)
        assert "la semaine" not in result
        assert "semaine dernière" in result


class TestFormatPushClauseTypologyDifferentiation:
    """Source-guard : les 3 typologies produisent des clauses distinctes."""

    def test_push_format_grand_groupe_vs_commerce(self):
        """Format GG ≠ format Commerce (registre éditorial doit diverger)."""
        gg = format_push_clause("exposure_eur", 118_000, 100_000, OrganizationTypology.GRAND_GROUPE)
        commerce = format_push_clause("exposure_eur", 118_000, 100_000, OrganizationTypology.COMMERCE)
        assert gg != commerce, (
            f"Les formats GG et COMMERCE doivent diverger (registre éditorial différent), trouvé identique : {gg!r}"
        )

    def test_format_unknown_falls_back_grand_groupe(self):
        """UNKNOWN hérite GRAND_GROUPE (registre expert par défaut)."""
        unknown = format_push_clause("exposure_eur", 110_000, 100_000, OrganizationTypology.UNKNOWN)
        gg = format_push_clause("exposure_eur", 110_000, 100_000, OrganizationTypology.GRAND_GROUPE)
        assert unknown == gg


# ─── Tests structure thresholds ─────────────────────────────────────────────


class TestPushThresholdsStructure:
    """Source-guards : seuils canoniques exposés correctement."""

    def test_push_thresholds_has_4_canonical_metrics(self):
        """Les 4 métriques canoniques `weekly_deltas` ont un seuil défini."""
        canonical = {"exposure_eur", "potential_mwh_year", "compliance_score", "sites_in_drift"}
        assert canonical.issubset(set(PUSH_THRESHOLDS.keys())), (
            f"Métriques canoniques manquantes : {canonical - set(PUSH_THRESHOLDS.keys())}"
        )

    def test_push_thresholds_exposure_eur_is_5pct_1keur(self):
        """exposure_eur seuils : 5 % OU 1 000 € (Option 3.C doctrine §11.3)."""
        assert PUSH_THRESHOLDS["exposure_eur"] == (5.0, 1000.0)

    def test_push_thresholds_compliance_score_3pct(self):
        """compliance_score : 3 points relatifs, pas de seuil absolu."""
        assert PUSH_THRESHOLDS["compliance_score"] == (3.0, None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
