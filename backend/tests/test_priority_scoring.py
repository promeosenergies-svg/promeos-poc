"""
PROMEOS — Tests algo priorisation findings cockpit (ADR-022 F.22 v1 doctrine).

Couverture v1 doctrine :
  - Mappers severity/impact/deadline → G/I/D (0-5)
  - Formule G·wG + I·wI + D·wD par persona
  - 3 overrides (G=5, D=5+G≥3, I=5+G=0)
  - Tiering P1/P2/P3/NONE persona-dependent
  - rank_findings + top_n hub-aware
  - Departage catégorie HUB_CAT_ORDER
  - 4 scénarios HELIOS représentatifs
"""

from __future__ import annotations

from datetime import date

import pytest

from regops.priority_scoring import (
    Category,
    DOCTRINE_VERSION,
    Domain,
    Finding,
    HUB_CAT_ORDER,
    HubId,
    PERSONA_THRESHOLDS,
    PERSONA_WEIGHTS,
    Persona,
    Scope,
    Severity,
    Tier,
    compute_finding_priority,
    deadline_to_d,
    impact_eur_to_i,
    rank_findings,
    severity_to_g,
    top_n,
)


REF_DATE = date(2026, 5, 12)


def _f(**overrides) -> Finding:
    """Helper finding avec defaults sains."""
    base = dict(
        severity=Severity.MEDIUM,
        domain=Domain.ENERGY,
        scope_level=Scope.SITE,
    )
    base.update(overrides)
    return Finding(**base)


# ── Mappers severity / impact / deadline → G/I/D ─────────────────────────────


class TestMapperSeverityToG:
    def test_critical_g5(self):
        assert severity_to_g(Severity.CRITICAL) == 5

    def test_high_g4(self):
        assert severity_to_g(Severity.HIGH) == 4

    def test_medium_g3(self):
        assert severity_to_g(Severity.MEDIUM) == 3

    def test_low_g2(self):
        assert severity_to_g(Severity.LOW) == 2


class TestMapperImpactEurToI:
    def test_above_100k_i5(self):
        assert impact_eur_to_i(150_000) == 5

    def test_50k_to_100k_i4(self):
        assert impact_eur_to_i(60_000) == 4

    def test_10k_to_50k_i3(self):
        assert impact_eur_to_i(25_000) == 3

    def test_1k_to_10k_i2(self):
        assert impact_eur_to_i(3_800) == 2

    def test_below_1k_i1(self):
        assert impact_eur_to_i(500) == 1

    def test_none_i0(self):
        assert impact_eur_to_i(None) == 0

    def test_zero_i0(self):
        assert impact_eur_to_i(0) == 0


class TestMapperDeadlineToD:
    def test_30_days_d5(self):
        assert deadline_to_d(date(2026, 5, 30), today=REF_DATE) == 5

    def test_90_days_d4(self):
        assert deadline_to_d(date(2026, 7, 15), today=REF_DATE) == 4

    def test_1_year_d3(self):
        assert deadline_to_d(date(2026, 12, 31), today=REF_DATE) == 3

    def test_2_years_d2(self):
        assert deadline_to_d(date(2028, 5, 1), today=REF_DATE) == 2

    def test_far_future_d1(self):
        assert deadline_to_d(date(2030, 12, 31), today=REF_DATE) == 1

    def test_past_d5_urgence_max(self):
        assert deadline_to_d(date(2025, 12, 1), today=REF_DATE) == 5

    def test_none_d0(self):
        assert deadline_to_d(None, today=REF_DATE) == 0


# ── Formule scoring par persona ──────────────────────────────────────────────


class TestFormulaResponsableEnergie:
    """G·3 + I·2 + D·2 (max 35)."""

    def test_critical_finding_resp_energie(self):
        # CRITICAL(G=5) + impact 60k(I=4) + deadline 60d(D=4) → 5*3 + 4*2 + 4*2 = 31
        # Override OV1 (G=5): score ≥ 25 (déjà 31, no-op)
        f = _f(
            severity=Severity.CRITICAL,
            impact_eur_year=60_000,
            deadline_date=date(2026, 7, 5),  # 54 jours → D=4
        )
        score = compute_finding_priority(f, Persona.RESPONSABLE_ENERGIE, today=REF_DATE)
        assert score.breakdown == {
            "g": 5,
            "i": 4,
            "d": 4,
            "g_weighted": 15,
            "i_weighted": 8,
            "d_weighted": 8,
        }
        assert score.total == 31
        assert score.tier == Tier.P1


class TestFormulaDAF:
    """G·2 + I·3 + D·2 (max 35) — impact financier prime."""

    def test_post_arenh_passes_p1_for_daf(self):
        """Post-ARENH (G=1, I=4, D=4) chez DAF: 1·2 + 4·3 + 4·2 = 22 → P1 (≥22)."""
        f = _f(
            severity=Severity.LOW,
            impact_eur_year=60_000,  # I=4
            deadline_date=date(2026, 7, 15),  # ~64 jours → D=4
        )
        score = compute_finding_priority(f, Persona.DAF, today=REF_DATE)
        # severity LOW → G=2 par défaut (mapping)
        # 2*2 + 4*3 + 4*2 = 24
        assert score.total == 24
        assert score.tier == Tier.P1


class TestFormulaDGComex:
    """G·2 + I·3 + D·3 (max 40) — urgence + impact priment."""

    def test_dg_comex_more_p1_due_to_d3(self):
        # G=3, I=3, D=4 chez DG: 3·2 + 3·3 + 4·3 = 27 → P1 (≥24)
        f = _f(
            severity=Severity.MEDIUM,
            impact_eur_year=15_000,
            deadline_date=date(2026, 7, 15),
        )
        score = compute_finding_priority(f, Persona.DG_COMEX, today=REF_DATE)
        assert score.total == 27
        assert score.tier == Tier.P1


# ── Overrides cardinaux ──────────────────────────────────────────────────────


class TestOverride1GraviteLegale:
    """G=5 → score garanti ≥ 25 (override force P1)."""

    def test_g5_low_impact_forces_25(self):
        # G=5, I=0, D=0 chez Resp: brut = 15, override → 25 (P1)
        f = _f(severity=Severity.CRITICAL)
        score = compute_finding_priority(f, Persona.RESPONSABLE_ENERGIE, today=REF_DATE)
        assert score.total == 25
        assert "OV1_GRAVITE_LEGALE_ABSOLUE" in score.overrides_applied
        assert score.tier == Tier.P1

    def test_g5_high_no_override_when_score_already_above(self):
        # CRITICAL + impact 100k + deadline 30j: 5·3 + 5·2 + 5·2 = 35 (déjà ≥ 25)
        f = _f(
            severity=Severity.CRITICAL,
            impact_eur_year=120_000,
            deadline_date=date(2026, 5, 20),
        )
        score = compute_finding_priority(f, Persona.RESPONSABLE_ENERGIE, today=REF_DATE)
        assert score.total == 35
        # OV1 ne s'applique pas car score déjà au-dessus de 25
        assert "OV1_GRAVITE_LEGALE_ABSOLUE" not in score.overrides_applied


class TestOverride2UrgenceQualifiee:
    """D=5 AND G≥3 → score ≥ 22."""

    def test_d5_g3_forces_22(self):
        # G=3, I=0, D=5 chez Resp: brut = 3·3 + 0 + 5·2 = 19, override → 22
        f = _f(severity=Severity.MEDIUM, deadline_date=date(2026, 5, 20))
        score = compute_finding_priority(f, Persona.RESPONSABLE_ENERGIE, today=REF_DATE)
        assert score.total == 22
        assert "OV2_URGENCE_QUALIFIEE" in score.overrides_applied

    def test_d5_g2_no_override(self):
        # G=2, D=5 chez Resp: brut = 2·3 + 0 + 5·2 = 16, OV2 ne s'applique pas (G<3)
        f = _f(severity=Severity.LOW, deadline_date=date(2026, 5, 20))
        score = compute_finding_priority(f, Persona.RESPONSABLE_ENERGIE, today=REF_DATE)
        assert score.total == 16
        assert "OV2_URGENCE_QUALIFIEE" not in score.overrides_applied


class TestOverride3ImpactOrphelin:
    """I=5 AND G=0 → score ≤ 15."""

    def test_i5_g0_capped_at_15(self):
        # On force g=0 explicite + impact massif
        f = _f(
            severity=Severity.LOW,
            g=0,
            impact_eur_year=200_000,  # I=5
            deadline_date=date(2026, 5, 20),  # D=5
        )
        # Brut = 0 + 5·2 + 5·2 = 20, plafonné à 15
        score = compute_finding_priority(f, Persona.RESPONSABLE_ENERGIE, today=REF_DATE)
        assert score.total == 15
        assert "OV3_IMPACT_ORPHELIN" in score.overrides_applied


# ── Tiering persona-dependent ───────────────────────────────────────────────


class TestTieringPersonaDependent:
    def test_p1_thresholds_per_persona(self):
        assert PERSONA_THRESHOLDS[Persona.RESPONSABLE_ENERGIE].P1 == 25
        assert PERSONA_THRESHOLDS[Persona.DAF].P1 == 22
        assert PERSONA_THRESHOLDS[Persona.DG_COMEX].P1 == 24

    def test_p2_thresholds_per_persona(self):
        assert PERSONA_THRESHOLDS[Persona.RESPONSABLE_ENERGIE].P2 == 18
        assert PERSONA_THRESHOLDS[Persona.DAF].P2 == 16
        assert PERSONA_THRESHOLDS[Persona.DG_COMEX].P2 == 17

    def test_score_15_is_tier_p3_responsable(self):
        # P3 threshold Resp = 12, score 15 → P3
        f = _f(severity=Severity.MEDIUM, impact_eur_year=2_000)
        score = compute_finding_priority(f, Persona.RESPONSABLE_ENERGIE, today=REF_DATE)
        # G=3, I=2, D=0 → 9 + 4 + 0 = 13 → P3 (≥12)
        assert score.tier == Tier.P3

    def test_score_low_is_tier_none(self):
        # Score < seuil P3
        f = _f(severity=Severity.LOW)  # G=2
        score = compute_finding_priority(f, Persona.RESPONSABLE_ENERGIE, today=REF_DATE)
        # 2*3 + 0 + 0 = 6 → NONE (<12)
        assert score.total == 6
        assert score.tier == Tier.NONE


# ── HUB_CAT_ORDER ──────────────────────────────────────────────────────────


class TestHubCatOrder:
    def test_seven_hubs_defined(self):
        assert set(HUB_CAT_ORDER.keys()) == {
            HubId.COCKPIT_JOUR,
            HubId.COCKPIT_STRATEGIQUE,
            HubId.ENERGIE,
            HubId.CONFORMITE,
            HubId.FACTURES,
            HubId.ACHAT,
            HubId.PATRIMOINE,
        }

    def test_each_hub_has_5_unique_categories(self):
        for hub, cats in HUB_CAT_ORDER.items():
            assert len(cats) == 5, f"Hub {hub} doit avoir 5 catégories"
            assert len(set(cats)) == 5, f"Hub {hub} a des doublons"

    def test_cockpit_jour_starts_with_energie(self):
        assert HUB_CAT_ORDER[HubId.COCKPIT_JOUR][0] == Category.ENERGIE

    def test_cockpit_strategique_starts_with_strategique(self):
        assert HUB_CAT_ORDER[HubId.COCKPIT_STRATEGIQUE][0] == Category.STRATEGIQUE

    def test_conformite_starts_with_reglementaire(self):
        assert HUB_CAT_ORDER[HubId.CONFORMITE][0] == Category.REGLEMENTAIRE


# ── Personnas reorder le ranking ─────────────────────────────────────────────


class TestPersonaReorders:
    def test_daf_promotes_financial_finding(self):
        """Une finding à impact financier remonte chez DAF vs Resp Énergie."""
        # f1 : G=4 (HIGH), I=2, D=2 → Resp: 12+4+4=20, DAF: 8+6+4=18
        # f2 : G=2 (LOW), I=4, D=3 → Resp: 6+8+6=20, DAF: 4+12+6=22
        f1 = _f(severity=Severity.HIGH, impact_eur_year=3_000, deadline_date=date(2027, 5, 1))
        f2 = _f(severity=Severity.LOW, impact_eur_year=60_000, deadline_date=date(2026, 12, 1))
        resp = rank_findings([f1, f2], persona=Persona.RESPONSABLE_ENERGIE, today=REF_DATE)
        daf = rank_findings([f1, f2], persona=Persona.DAF, today=REF_DATE)
        # Chez DAF, f2 (impact 60k) doit remonter premier
        assert daf[0][0] is f2


# ── Top N ───────────────────────────────────────────────────────────────────


class TestTopN:
    def test_top_n_excludes_none_tier(self):
        f1 = _f(severity=Severity.LOW)  # tier NONE (6 pts)
        f2 = _f(severity=Severity.HIGH, impact_eur_year=15_000)  # P1+
        result = top_n([f1, f2], n=3, today=REF_DATE)
        assert len(result) == 1
        assert result[0][0] is f2

    def test_top_n_default_3(self):
        findings = [_f(severity=Severity.CRITICAL) for _ in range(5)]
        assert len(top_n(findings, today=REF_DATE)) == 3


# ── Doctrine version ────────────────────────────────────────────────────────


def test_doctrine_version_constant():
    assert DOCTRINE_VERSION == "priorisation_v1.0"
