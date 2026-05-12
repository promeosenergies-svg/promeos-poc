"""
PROMEOS — Tests algo priorisation findings cockpit (ADR-022 F.19a).

Couverture :
  - 1 test par dimension (severity, impact, urgency, scope, domain)
  - Tiering P1/P2/P3/NONE
  - 3 scénarios personas (Marie CFO / Yannick DG / Asset-Energy manager)
  - rank_findings + top_n contracts
"""

from __future__ import annotations

from datetime import date

import pytest

from regops.priority_scoring import (
    Domain,
    Finding,
    MAX_SCORE,
    Scope,
    Severity,
    Tier,
    compute_finding_priority,
    rank_findings,
    top_n,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


REF_DATE = date(2026, 5, 12)  # Date de référence pour tests urgency reproductibles


def _f(**overrides) -> Finding:
    """Helper finding minimaliste avec defaults sains."""
    base = dict(
        severity=Severity.MEDIUM,
        domain=Domain.ENERGY,
        scope_level=Scope.SITE,
    )
    base.update(overrides)
    return Finding(**base)


# ── 1 test par dimension ────────────────────────────────────────────────────


class TestSeverityDimension:
    def test_critical_max_60_pts(self):
        score = compute_finding_priority(_f(severity=Severity.CRITICAL), today=REF_DATE)
        assert score.breakdown["severity"] == 60

    def test_high_50_pts(self):
        score = compute_finding_priority(_f(severity=Severity.HIGH), today=REF_DATE)
        assert score.breakdown["severity"] == 50

    def test_medium_30_pts(self):
        score = compute_finding_priority(_f(severity=Severity.MEDIUM), today=REF_DATE)
        assert score.breakdown["severity"] == 30

    def test_low_10_pts(self):
        score = compute_finding_priority(_f(severity=Severity.LOW), today=REF_DATE)
        assert score.breakdown["severity"] == 10


class TestImpactDimension:
    def test_above_50k_max_40_pts(self):
        score = compute_finding_priority(_f(impact_eur_year=120_000), today=REF_DATE)
        assert score.breakdown["impact"] == 40

    def test_10k_to_50k_30_pts(self):
        score = compute_finding_priority(_f(impact_eur_year=25_000), today=REF_DATE)
        assert score.breakdown["impact"] == 30

    def test_1k_to_10k_20_pts(self):
        score = compute_finding_priority(_f(impact_eur_year=3_800), today=REF_DATE)
        assert score.breakdown["impact"] == 20

    def test_below_1k_zero_pts(self):
        score = compute_finding_priority(_f(impact_eur_year=500), today=REF_DATE)
        assert score.breakdown["impact"] == 0

    def test_none_zero_pts(self):
        score = compute_finding_priority(_f(impact_eur_year=None), today=REF_DATE)
        assert score.breakdown["impact"] == 0


class TestUrgencyDimension:
    def test_30_days_max_50_pts(self):
        deadline = date(2026, 5, 30)  # 18 jours
        score = compute_finding_priority(_f(deadline_date=deadline), today=REF_DATE)
        assert score.breakdown["urgency"] == 50

    def test_90_days_35_pts(self):
        deadline = date(2026, 7, 15)  # 64 jours
        score = compute_finding_priority(_f(deadline_date=deadline), today=REF_DATE)
        assert score.breakdown["urgency"] == 35

    def test_1_year_20_pts(self):
        deadline = date(2026, 12, 31)  # 233 jours
        score = compute_finding_priority(_f(deadline_date=deadline), today=REF_DATE)
        assert score.breakdown["urgency"] == 20

    def test_2_years_10_pts(self):
        deadline = date(2027, 11, 1)  # 538 jours
        score = compute_finding_priority(_f(deadline_date=deadline), today=REF_DATE)
        assert score.breakdown["urgency"] == 10

    def test_far_future_zero_pts(self):
        deadline = date(2030, 12, 31)  # Décret tertiaire jalon -40 % loin
        score = compute_finding_priority(_f(deadline_date=deadline), today=REF_DATE)
        assert score.breakdown["urgency"] == 0

    def test_past_deadline_max_pts(self):
        """Deadline passée → urgence max (sanction probable en cours)."""
        deadline = date(2025, 12, 1)
        score = compute_finding_priority(_f(deadline_date=deadline), today=REF_DATE)
        assert score.breakdown["urgency"] == 50

    def test_none_zero_pts(self):
        score = compute_finding_priority(_f(deadline_date=None), today=REF_DATE)
        assert score.breakdown["urgency"] == 0


class TestScopeDimension:
    def test_group_max_30_pts(self):
        score = compute_finding_priority(_f(scope_level=Scope.GROUP), today=REF_DATE)
        assert score.breakdown["scope"] == 30

    def test_portfolio_20_pts(self):
        score = compute_finding_priority(_f(scope_level=Scope.PORTFOLIO), today=REF_DATE)
        assert score.breakdown["scope"] == 20

    def test_site_10_pts(self):
        score = compute_finding_priority(_f(scope_level=Scope.SITE), today=REF_DATE)
        assert score.breakdown["scope"] == 10


class TestDomainDimension:
    def test_platform_health_first_doctrinal_priority(self):
        """Anti-pattern 'conclusions sur données pourries' → platform_health en tête."""
        score = compute_finding_priority(_f(domain=Domain.PLATFORM_HEALTH), today=REF_DATE)
        assert score.breakdown["domain"] == 20

    def test_compliance_18_pts(self):
        score = compute_finding_priority(_f(domain=Domain.COMPLIANCE), today=REF_DATE)
        assert score.breakdown["domain"] == 18

    def test_financial_15_pts(self):
        score = compute_finding_priority(_f(domain=Domain.FINANCIAL), today=REF_DATE)
        assert score.breakdown["domain"] == 15

    def test_energy_12_pts(self):
        score = compute_finding_priority(_f(domain=Domain.ENERGY), today=REF_DATE)
        assert score.breakdown["domain"] == 12

    def test_optimisation_8_pts(self):
        score = compute_finding_priority(_f(domain=Domain.OPTIMISATION), today=REF_DATE)
        assert score.breakdown["domain"] == 8


# ── Tiering ─────────────────────────────────────────────────────────────────


class TestTiering:
    def test_p1_score_above_130(self):
        # CRITICAL(60) + COMPLIANCE(18) + GROUP(30) + impact 50k(40) → 148 pts
        score = compute_finding_priority(
            _f(
                severity=Severity.CRITICAL,
                domain=Domain.COMPLIANCE,
                scope_level=Scope.GROUP,
                impact_eur_year=60_000,
            ),
            today=REF_DATE,
        )
        assert score.total >= 130
        assert score.tier == Tier.P1

    def test_p2_score_80_to_130(self):
        # HIGH(50) + ENERGY(12) + SITE(10) + impact 5k(20) = 92
        score = compute_finding_priority(
            _f(
                severity=Severity.HIGH,
                domain=Domain.ENERGY,
                scope_level=Scope.SITE,
                impact_eur_year=5_000,
            ),
            today=REF_DATE,
        )
        assert 80 <= score.total < 130
        assert score.tier == Tier.P2

    def test_p3_score_40_to_80(self):
        # MEDIUM(30) + OPTIMISATION(8) + SITE(10) = 48
        score = compute_finding_priority(
            _f(
                severity=Severity.MEDIUM,
                domain=Domain.OPTIMISATION,
                scope_level=Scope.SITE,
            ),
            today=REF_DATE,
        )
        assert 40 <= score.total < 80
        assert score.tier == Tier.P3

    def test_none_tier_below_40(self):
        # LOW(10) + OPTIMISATION(8) + SITE(10) = 28
        score = compute_finding_priority(
            _f(
                severity=Severity.LOW,
                domain=Domain.OPTIMISATION,
                scope_level=Scope.SITE,
            ),
            today=REF_DATE,
        )
        assert score.total < 40
        assert score.tier == Tier.NONE

    def test_max_score_capped_at_200(self):
        score = compute_finding_priority(
            _f(
                severity=Severity.CRITICAL,
                domain=Domain.PLATFORM_HEALTH,
                scope_level=Scope.GROUP,
                impact_eur_year=500_000,
                deadline_date=date(2026, 5, 13),  # demain
            ),
            today=REF_DATE,
        )
        assert score.total <= MAX_SCORE
        assert score.total == 60 + 40 + 50 + 30 + 20  # = 200


# ── Personas (ADR-022 §Personas mapping) ────────────────────────────────────


class TestPersonas:
    """Vérifie que le scoring privilégie les findings utiles aux 3 personas."""

    def test_marie_cfo_favored_by_financial_impact(self):
        """Marie (DAF/CFO) doit voir remonter les findings à impact € chiffré."""
        # Finding "Marie" : facture surfacturée 25 k€/an, sévérité HIGH
        marie = _f(
            severity=Severity.HIGH,
            domain=Domain.FINANCIAL,
            scope_level=Scope.PORTFOLIO,
            impact_eur_year=25_000,
        )
        # Finding générique sans impact financier
        generic = _f(severity=Severity.HIGH, scope_level=Scope.SITE)

        ranked = rank_findings([generic, marie], today=REF_DATE)
        assert ranked[0][0] is marie  # Marie's finding remonte première

    def test_yannick_dg_favored_by_group_scope_and_urgency(self):
        """Yannick (DG) doit voir remonter les findings groupe + urgentes."""
        # Finding "Yannick" : Décret tertiaire jalon 2030 sur tout le groupe
        yannick = _f(
            severity=Severity.HIGH,
            domain=Domain.COMPLIANCE,
            scope_level=Scope.GROUP,
            deadline_date=date(2026, 6, 30),  # 49 jours → 35 pts urgency
        )
        # Finding site unique sans urgence
        site_finding = _f(severity=Severity.HIGH, scope_level=Scope.SITE)

        ranked = rank_findings([site_finding, yannick], today=REF_DATE)
        assert ranked[0][0] is yannick

    def test_asset_manager_favored_by_platform_health_and_severity(self):
        """Asset/Energy manager doit voir remonter les findings data-quality critiques."""
        # Finding "Asset" : connecteur EMS down (platform_health critique)
        asset = _f(
            severity=Severity.CRITICAL,
            domain=Domain.PLATFORM_HEALTH,
            scope_level=Scope.PORTFOLIO,
        )
        # Finding optimisation low priority
        low = _f(severity=Severity.LOW, domain=Domain.OPTIMISATION)

        ranked = rank_findings([low, asset], today=REF_DATE)
        assert ranked[0][0] is asset

    def test_p1_must_satisfy_three_personas(self):
        """Test doctrinal ADR-022 : un P1 doit être justifiable pour les 3 personas."""
        # Finding "tri-persona" : DT jalon 2026 sur le groupe avec impact 50k€
        # → Marie (financial), Yannick (group + urgent), Asset (high severity)
        tri_persona = _f(
            severity=Severity.HIGH,  # asset manager
            domain=Domain.COMPLIANCE,
            scope_level=Scope.GROUP,  # Yannick DG
            impact_eur_year=60_000,  # Marie CFO
            deadline_date=date(2026, 11, 1),  # 173 jours → 20 pts urgency
        )
        score = compute_finding_priority(tri_persona, today=REF_DATE)
        # Score = HIGH(50) + COMPLIANCE(18) + GROUP(30) + impact(40) + urgency(20) = 158
        assert score.tier == Tier.P1


# ── Contracts API ───────────────────────────────────────────────────────────


class TestApiContracts:
    def test_rank_findings_returns_descending_order(self):
        f1 = _f(severity=Severity.LOW)
        f2 = _f(severity=Severity.CRITICAL)
        f3 = _f(severity=Severity.MEDIUM)
        ranked = rank_findings([f1, f2, f3], today=REF_DATE)
        assert ranked[0][0] is f2
        assert ranked[1][0] is f3
        assert ranked[2][0] is f1

    def test_top_n_filters_out_none_tier(self):
        # f1 score < 40 → NONE, f2 score P3 → kept
        f1 = _f(severity=Severity.LOW, domain=Domain.OPTIMISATION, scope_level=Scope.SITE)
        f2 = _f(severity=Severity.MEDIUM, domain=Domain.COMPLIANCE, scope_level=Scope.PORTFOLIO)
        result = top_n([f1, f2], n=3, today=REF_DATE)
        assert len(result) == 1
        assert result[0][0] is f2

    def test_top_n_default_3_for_cockpit(self):
        findings = [_f(severity=Severity.CRITICAL) for _ in range(5)]
        result = top_n(findings, today=REF_DATE)
        assert len(result) == 3

    def test_breakdown_traceability(self):
        """L'audit user doit pouvoir lire les 5 dimensions du score."""
        score = compute_finding_priority(_f(severity=Severity.CRITICAL, impact_eur_year=12_000), today=REF_DATE)
        assert set(score.breakdown.keys()) == {
            "severity",
            "impact",
            "urgency",
            "scope",
            "domain",
        }
        assert score.total == sum(score.breakdown.values())
