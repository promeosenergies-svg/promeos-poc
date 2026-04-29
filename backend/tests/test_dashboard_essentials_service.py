"""
Source-guard Phase 1.4.d — service dashboard_essentials (migration JS → Python).

Sprint refonte cockpit dual sol2 (29/04/2026) — étape 1.4.d : verrouille
le contrat du service Python qui remplace
`frontend/src/models/dashboardEssentials.js` (717 lignes).

Le JS frontend reste temporairement en place (stratégie SoT d'abord).
Migration des 4 pages importeuses différée à Phase 1.4.d.bis.

Tests adaptés des cas couverts par les tests JS historiques :
    - DashboardEssentials.test.js
    - healthState.test.js
    - DashboardV2.test.js
    - CockpitV2.test.js (cas health)
    - chipFilterHealthFix.test.js (cas edge health)

CLAUDE.md règle d'or #1 : zero business logic frontend. Ce service
porte désormais la logique des essentiels dashboard côté backend.
"""

import pytest
from services.dashboard_essentials_service import (
    # Constantes
    COVERAGE_OPPORTUNITY,
    COVERAGE_SUSPICIOUS,
    COVERAGE_WARN,
    CONFORMITY_POSITIVE,
    CONFORMITY_WARN,
    COMPLIANCE_SCORE_OK,
    COMPLIANCE_SCORE_WARN,
    MATURITY_CRIT,
    MATURITY_WARN,
    RISK_THRESHOLDS_ORG_WARN,
    SEVERITY_RANK,
    # Dataclasses
    ConsistencyResult,
    DashboardEssentials,
    HealthState,
    TopSites,
    WatchItem,
    # Fonctions
    build_briefing,
    build_dashboard_essentials,
    build_executive_kpis,
    build_executive_summary,
    build_opportunities,
    build_today_actions,
    build_top_sites,
    build_watchlist,
    check_consistency,
    compute_health_state,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def make_kpis(**overrides):
    """KPIs de base pour les tests — 10 sites, 7 conformes."""
    base = {
        "total": 10,
        "conformes": 7,
        "nonConformes": 2,
        "aRisque": 1,
        "risqueTotal": 30_000,
        "couvertureDonnees": 70,
        "compliance_score": 72.0,
    }
    base.update(overrides)
    return base


def make_site(
    id=1,
    nom="Site A",
    ville="Paris",
    statut="conforme",
    risque_eur=0,
    conso_kwh_an=100_000,
):
    return {
        "id": id,
        "nom": nom,
        "ville": ville,
        "statut_conformite": statut,
        "risque_eur": risque_eur,
        "conso_kwh_an": conso_kwh_an,
    }


def make_sites_mixed():
    """Jeu de sites mélangés conforme/non_conforme/a_risque."""
    return [
        make_site(1, "Site A", "Paris", "conforme", 0, 100_000),
        make_site(2, "Site B", "Lyon", "non_conforme", 20_000, 80_000),
        make_site(3, "Site C", "Marseille", "a_risque", 5_000, 60_000),
        make_site(4, "Site D", "Lille", "conforme", 0, 40_000),
        make_site(5, "Site E", "Nantes", "non_conforme", 15_000, 0),
    ]


# ── build_watchlist ───────────────────────────────────────────────────────────


class TestBuildWatchlist:
    def test_empty_kpis_returns_empty(self):
        result = build_watchlist(make_kpis(nonConformes=0, aRisque=0, couvertureDonnees=90))
        assert result == []

    def test_non_conformes_is_critical(self):
        items = build_watchlist(make_kpis(nonConformes=3, aRisque=0))
        assert any(w.id == "non_conformes" and w.severity == "critical" for w in items)

    def test_a_risque_is_high(self):
        items = build_watchlist(make_kpis(nonConformes=0, aRisque=2))
        assert any(w.id == "a_risque" and w.severity == "high" for w in items)

    def test_sites_without_data_is_warn(self):
        sites = [make_site(1, conso_kwh_an=0)]
        items = build_watchlist(make_kpis(nonConformes=0, aRisque=0, total=1), sites)
        assert any(w.id == "no_conso_data" and w.severity == "warn" for w in items)

    def test_low_coverage_is_medium(self):
        # total >= 3, couverture < COVERAGE_WARN, pas de sites sans données
        sites = [make_site(i, conso_kwh_an=100) for i in range(5)]
        kpis = make_kpis(nonConformes=0, aRisque=0, total=5, couvertureDonnees=30)
        items = build_watchlist(kpis, sites)
        assert any(w.id == "low_coverage" and w.severity == "medium" for w in items)

    def test_sorted_critical_before_high(self):
        items = build_watchlist(make_kpis(nonConformes=1, aRisque=1))
        severities = [w.severity for w in items]
        assert severities[0] == "critical"

    def test_max_5_items(self):
        sites = [make_site(i, conso_kwh_an=0) for i in range(10)]
        kpis = make_kpis(nonConformes=3, aRisque=3, couvertureDonnees=10, total=10)
        items = build_watchlist(kpis, sites)
        assert len(items) <= 5

    def test_camel_case_legacy_keys(self):
        """Accepte nonConformes / aRisque (clés camelCase legacy)."""
        kpis = {"nonConformes": 1, "aRisque": 1, "couvertureDonnees": 90, "total": 5}
        items = build_watchlist(kpis)
        ids = [w.id for w in items]
        assert "non_conformes" in ids
        assert "a_risque" in ids

    def test_to_dict_contract(self):
        items = build_watchlist(make_kpis(nonConformes=1))
        d = items[0].to_dict()
        assert set(d.keys()) == {"id", "label", "severity", "path", "cta"}

    def test_singular_label_when_nc_equals_1(self):
        items = build_watchlist(make_kpis(nonConformes=1, aRisque=0))
        nc_item = next(w for w in items if w.id == "non_conformes")
        assert "1 site non conforme" in nc_item.label
        assert "sites" not in nc_item.label

    def test_plural_label_when_nc_gt_1(self):
        items = build_watchlist(make_kpis(nonConformes=3, aRisque=0))
        nc_item = next(w for w in items if w.id == "non_conformes")
        assert "sites" in nc_item.label


# ── check_consistency ─────────────────────────────────────────────────────────


class TestCheckConsistency:
    def test_ok_when_no_issues(self):
        result = check_consistency(make_kpis(couvertureDonnees=70))
        assert result.ok is True
        assert result.issues == []

    def test_all_conformes_low_data_suspicious(self):
        kpis = {"total": 5, "conformes": 5, "nonConformes": 0, "couvertureDonnees": 20}
        result = check_consistency(kpis)
        assert not result.ok
        assert any(i.code == "all_conformes_low_data" for i in result.issues)

    def test_no_data_coverage_issue(self):
        kpis = {"total": 3, "conformes": 1, "nonConformes": 1, "couvertureDonnees": 0}
        result = check_consistency(kpis)
        assert not result.ok
        assert any(i.code == "no_data_coverage" for i in result.issues)

    def test_no_issues_when_total_zero(self):
        result = check_consistency({"total": 0, "conformes": 0, "couvertureDonnees": 0})
        assert result.ok is True

    def test_to_dict_contract(self):
        kpis = {"total": 3, "conformes": 3, "nonConformes": 0, "couvertureDonnees": 10}
        d = check_consistency(kpis).to_dict()
        assert "ok" in d
        assert "issues" in d


# ── build_top_sites ───────────────────────────────────────────────────────────


class TestBuildTopSites:
    def test_empty_sites_returns_empty(self):
        result = build_top_sites([])
        assert result.worst == []
        assert result.best == []

    def test_worst_sorted_by_risque_desc(self):
        sites = [
            make_site(1, statut="non_conforme", risque_eur=5_000),
            make_site(2, statut="non_conforme", risque_eur=20_000),
            make_site(3, statut="non_conforme", risque_eur=1_000),
        ]
        result = build_top_sites(sites)
        assert result.worst[0].risque_eur == 20_000
        assert result.worst[1].risque_eur == 5_000

    def test_best_sorted_by_conso_asc(self):
        sites = [
            make_site(1, statut="conforme", conso_kwh_an=50_000),
            make_site(2, statut="conforme", conso_kwh_an=10_000),
            make_site(3, statut="conforme", conso_kwh_an=30_000),
        ]
        result = build_top_sites(sites)
        assert result.best[0].conso_kwh_an == 10_000

    def test_conformes_in_best_only(self):
        sites = make_sites_mixed()
        result = build_top_sites(sites)
        for s in result.best:
            assert s.statut_conformite == "conforme"

    def test_non_conformes_in_worst(self):
        sites = make_sites_mixed()
        result = build_top_sites(sites)
        for s in result.worst:
            assert s.statut_conformite != "conforme"

    def test_max_5_worst(self):
        sites = [make_site(i, statut="non_conforme", risque_eur=i * 1000) for i in range(10)]
        result = build_top_sites(sites)
        assert len(result.worst) <= 5

    def test_to_dict_contract(self):
        sites = make_sites_mixed()
        d = build_top_sites(sites).to_dict()
        assert "worst" in d and "best" in d
        if d["worst"]:
            assert "risque_eur" in d["worst"][0]


# ── build_opportunities ───────────────────────────────────────────────────────


class TestBuildOpportunities:
    def test_returns_empty_when_not_expert(self):
        result = build_opportunities(make_kpis(), is_expert=False)
        assert result == []

    def test_complete_data_opportunity_when_low_coverage(self):
        kpis = make_kpis(couvertureDonnees=50, total=10, nonConformes=0, risqueTotal=0)
        result = build_opportunities(kpis, is_expert=True)
        assert any(o.id == "complete_data" for o in result)

    def test_reduce_risk_when_non_conformes(self):
        kpis = make_kpis(nonConformes=2, is_expert=True)
        result = build_opportunities(kpis, is_expert=True)
        assert any(o.id == "reduce_risk" for o in result)

    def test_optimize_subscriptions_when_high_risk(self):
        kpis = make_kpis(risqueTotal=RISK_THRESHOLDS_ORG_WARN + 1, nonConformes=0)
        result = build_opportunities(kpis, is_expert=True)
        assert any(o.id == "optimize_subscriptions" for o in result)

    def test_max_3_items(self):
        kpis = make_kpis(couvertureDonnees=50, nonConformes=2, risqueTotal=20_000)
        result = build_opportunities(kpis, is_expert=True)
        assert len(result) <= 3

    def test_to_dict_contract(self):
        kpis = make_kpis(nonConformes=1)
        items = build_opportunities(kpis, is_expert=True)
        if items:
            d = items[0].to_dict()
            assert set(d.keys()) == {"id", "label", "sub", "path", "cta"}


# ── build_briefing ────────────────────────────────────────────────────────────


class TestBuildBriefing:
    def test_empty_kpis_no_alerts_returns_empty(self):
        kpis = {"total": 5, "nonConformes": 0, "aRisque": 0, "couvertureDonnees": 90, "conformes": 5}
        result = build_briefing(kpis)
        assert result == []

    def test_non_conformes_gives_critical(self):
        items = build_briefing(make_kpis(nonConformes=2))
        assert any(b.id == "non_conformes" and b.severity == "critical" for b in items)

    def test_a_risque_gives_high(self):
        items = build_briefing(make_kpis(nonConformes=0, aRisque=1))
        assert any(b.id == "a_risque" and b.severity == "high" for b in items)

    def test_few_alerts_gives_warn(self):
        items = build_briefing(make_kpis(nonConformes=0, aRisque=0), alerts_count=3)
        assert any(b.id == "alertes_actives" and b.severity == "warn" for b in items)

    def test_many_alerts_gives_high(self):
        items = build_briefing(make_kpis(nonConformes=0, aRisque=0), alerts_count=6)
        assert any(b.id == "alertes_actives" and b.severity == "high" for b in items)

    def test_low_coverage_gives_warn(self):
        kpis = make_kpis(nonConformes=0, aRisque=0, couvertureDonnees=50, total=10)
        items = build_briefing(kpis)
        assert any(b.id == "coverage" and b.severity == "warn" for b in items)

    def test_max_3_items(self):
        items = build_briefing(
            make_kpis(nonConformes=2, aRisque=2, couvertureDonnees=10),
            alerts_count=5,
        )
        assert len(items) <= 3


# ── build_today_actions ───────────────────────────────────────────────────────


class TestBuildTodayActions:
    def test_empty_inputs_returns_empty(self):
        result = build_today_actions(make_kpis(), [], [])
        assert result == []

    def test_watchlist_items_come_first(self):
        watchlist = [
            WatchItem("nc", "NC label", "critical", "/conformite", "Voir"),
        ]
        from services.dashboard_essentials_service import Opportunity

        opps = [Opportunity("opp1", "Opport", "sub", "/path", "Cta")]
        items = build_today_actions(make_kpis(), watchlist, opps)
        assert items[0].type == "watchlist"

    def test_no_duplicates(self):
        watchlist = [WatchItem("nc", "NC", "critical", "/conformite", "Voir")]
        # simuler même id dans opportunities
        from services.dashboard_essentials_service import Opportunity

        opps = [Opportunity("nc", "NC opp", "sub", "/path", "Cta")]
        items = build_today_actions(make_kpis(), watchlist, opps)
        ids = [i.id for i in items]
        assert len(ids) == len(set(ids))

    def test_max_5_items(self):
        watchlist = [WatchItem(f"w{i}", f"label {i}", "warn", "/path", "CTA") for i in range(8)]
        items = build_today_actions(make_kpis(), watchlist, [])
        assert len(items) <= 5

    def test_sorted_by_severity(self):
        watchlist = [
            WatchItem("warn_item", "warn", "warn", "/path", "CTA"),
            WatchItem("crit_item", "crit", "critical", "/path", "CTA"),
        ]
        items = build_today_actions(make_kpis(), watchlist, [])
        assert items[0].severity == "critical"

    def test_to_dict_contract(self):
        watchlist = [WatchItem("nc", "NC", "critical", "/conformite", "Voir")]
        items = build_today_actions(make_kpis(), watchlist)
        d = items[0].to_dict()
        assert set(d.keys()) == {"id", "label", "severity", "path", "cta", "type"}


# ── build_executive_summary ───────────────────────────────────────────────────


class TestBuildExecutiveSummary:
    def test_no_sites_returns_warn_bullet(self):
        bullets = build_executive_summary(make_kpis(total=0))
        assert any(b.id == "no_sites" and b.type == "warn" for b in bullets)

    def test_all_conformes_gives_positive(self):
        kpis = make_kpis(
            total=5,
            conformes=5,
            nonConformes=0,
            aRisque=0,
            compliance_score=90.0,
            couvertureDonnees=90,
        )
        bullets = build_executive_summary(kpis)
        assert any(b.type == "positive" for b in bullets)

    def test_non_conformes_gives_negative_bullet(self):
        bullets = build_executive_summary(make_kpis(nonConformes=2))
        assert any(b.id == "non_conformes_exec" and b.type == "negative" for b in bullets)

    def test_a_risque_gives_warn_bullet(self):
        bullets = build_executive_summary(make_kpis(nonConformes=0, aRisque=2, compliance_score=60.0))
        assert any(b.id == "a_risque_exec" and b.type == "warn" for b in bullets)

    def test_coverage_opportunity_bullet(self):
        kpis = make_kpis(
            nonConformes=0,
            aRisque=0,
            couvertureDonnees=50,
            total=10,
            risqueTotal=0,
            compliance_score=90.0,
        )
        bullets = build_executive_summary(kpis)
        assert any(b.id == "coverage_exec" and b.type == "opportunity" for b in bullets)

    def test_max_3_bullets(self):
        bullets = build_executive_summary(make_kpis())
        assert len(bullets) <= 3

    def test_to_dict_contract(self):
        bullets = build_executive_summary(make_kpis())
        if bullets:
            d = bullets[0].to_dict()
            assert "id" in d and "type" in d and "label" in d

    def test_mono_site_special_case(self):
        kpis = {
            "total": 1,
            "conformes": 0,
            "nonConformes": 1,
            "aRisque": 0,
            "risqueTotal": 5000,
            "couvertureDonnees": 100,
            "compliance_score": 30.0,
        }
        bullets = build_executive_summary(kpis)
        # Doit avoir un bullet adapté au mono-site
        assert any(b.id == "conforme_partial" for b in bullets)


# ── build_executive_kpis ──────────────────────────────────────────────────────


class TestBuildExecutiveKpis:
    def test_returns_4_kpis(self):
        kpis = build_executive_kpis(make_kpis())
        assert len(kpis) == 4

    def test_kpi_ids(self):
        kpis = build_executive_kpis(make_kpis())
        ids = [k.id for k in kpis]
        assert ids == ["conformite", "risque", "maturite", "couverture"]

    def test_empty_portfolio_returns_dashes(self):
        kpis = build_executive_kpis(make_kpis(total=0))
        assert all(k.value == "—" for k in kpis)

    def test_conformite_status_crit_when_score_low(self):
        kpis = build_executive_kpis(make_kpis(compliance_score=30.0, total=5))
        conf_kpi = next(k for k in kpis if k.id == "conformite")
        assert conf_kpi.status == "crit"

    def test_conformite_status_warn_when_score_medium(self):
        kpis = build_executive_kpis(make_kpis(compliance_score=65.0, total=5))
        conf_kpi = next(k for k in kpis if k.id == "conformite")
        assert conf_kpi.status == "warn"

    def test_conformite_status_ok_when_score_high(self):
        kpis = build_executive_kpis(make_kpis(compliance_score=85.0, total=5))
        conf_kpi = next(k for k in kpis if k.id == "conformite")
        assert conf_kpi.status == "ok"

    def test_couverture_crit_when_zero(self):
        kpis = build_executive_kpis(make_kpis(couvertureDonnees=0, total=5))
        cov_kpi = next(k for k in kpis if k.id == "couverture")
        assert cov_kpi.status == "crit"

    def test_risque_value_formatted_in_keur(self):
        kpis = build_executive_kpis(make_kpis(risqueTotal=45_000))
        risque_kpi = next(k for k in kpis if k.id == "risque")
        assert "k€" in risque_kpi.value
        assert "45" in risque_kpi.value

    def test_to_dict_camel_case_keys(self):
        kpis = build_executive_kpis(make_kpis())
        d = kpis[0].to_dict()
        assert "accentKey" in d
        assert "rawValue" in d
        assert "subShort" in d
        assert "messageCtx" in d


# ── compute_health_state ──────────────────────────────────────────────────────


class TestComputeHealthState:
    def test_green_when_no_issues(self):
        kpis = make_kpis(nonConformes=0, aRisque=0, conformes=5, total=5)
        hs = compute_health_state(kpis, watchlist=[], consistency=ConsistencyResult(ok=True))
        assert hs.level == "GREEN"
        assert hs.title == "Tout est sous contrôle"

    def test_red_when_non_conformes(self):
        kpis = make_kpis(nonConformes=2)
        watchlist = [WatchItem("nc", "NC", "critical", "/conformite", "Voir")]
        hs = compute_health_state(kpis, watchlist=watchlist)
        assert hs.level == "RED"

    def test_amber_when_a_risque_only(self):
        kpis = make_kpis(nonConformes=0, aRisque=1)
        watchlist = [WatchItem("ar", "AR", "high", "/actions", "Plan")]
        hs = compute_health_state(kpis, watchlist=watchlist)
        assert hs.level == "AMBER"

    def test_amber_when_alerts(self):
        kpis = make_kpis(nonConformes=0, aRisque=0, conformes=5, total=5)
        hs = compute_health_state(kpis, alerts_count=3)
        assert hs.level == "AMBER"

    def test_red_cta_to_conformite(self):
        kpis = make_kpis(nonConformes=1)
        watchlist = [WatchItem("nc", "NC", "critical", "/conformite", "Voir")]
        hs = compute_health_state(kpis, watchlist=watchlist)
        assert hs.primary_cta.to == "/conformite"

    def test_amber_cta_to_actions(self):
        kpis = make_kpis(nonConformes=0, aRisque=1)
        watchlist = [WatchItem("ar", "AR", "high", "/actions", "Plan")]
        hs = compute_health_state(kpis, watchlist=watchlist)
        assert hs.primary_cta.to == "/actions"

    def test_green_cta_to_explorer(self):
        kpis = make_kpis(nonConformes=0, aRisque=0, conformes=5, total=5)
        hs = compute_health_state(kpis)
        assert hs.primary_cta.to == "/consommations/explorer"

    def test_secondary_cta_when_many_reasons(self):
        watchlist = [WatchItem(f"w{i}", f"label {i}", "warn", "/path", "CTA") for i in range(5)]
        kpis = make_kpis(nonConformes=0, aRisque=0, conformes=5, total=5)
        hs = compute_health_state(kpis, watchlist=watchlist)
        # all_reason_count > 3 → secondary_cta present
        assert hs.secondary_cta is not None
        assert "/anomalies" in hs.secondary_cta.to

    def test_no_secondary_cta_when_few_reasons(self):
        kpis = make_kpis(nonConformes=0, aRisque=1, total=5)
        watchlist = [WatchItem("ar", "AR", "high", "/actions", "Plan")]
        hs = compute_health_state(kpis, watchlist=watchlist)
        # Only 1 reason (warn from a_risque) — but has_warn via aRisque >0
        assert hs.secondary_cta is None

    def test_consistency_issue_adds_reason(self):
        from services.dashboard_essentials_service import ConsistencyIssue

        kpis = make_kpis(nonConformes=0, aRisque=0, conformes=5, total=5)
        cons = ConsistencyResult(ok=False, issues=[ConsistencyIssue(code="no_data_coverage", label="Pas de données")])
        hs = compute_health_state(kpis, consistency=cons)
        assert hs.level in ("AMBER", "RED")

    def test_conformite_unknown_reason_when_no_statuts(self):
        # Sites présents mais conformes=0, nc=0, ar=0 → "conformité non évaluée"
        kpis = {"total": 3, "conformes": 0, "nonConformes": 0, "aRisque": 0, "risqueTotal": 0, "couvertureDonnees": 80}
        hs = compute_health_state(kpis)
        assert any(r.id == "conformite-unknown" for r in hs.reasons)

    def test_reasons_capped_at_3(self):
        watchlist = [WatchItem(f"w{i}", f"label {i}", "warn", "/path", "CTA") for i in range(6)]
        kpis = make_kpis(nonConformes=0, aRisque=0, conformes=5, total=5)
        hs = compute_health_state(kpis, watchlist=watchlist)
        assert len(hs.reasons) <= 3

    def test_to_dict_contract(self):
        kpis = make_kpis()
        hs = compute_health_state(kpis)
        d = hs.to_dict()
        required = {"level", "title", "subtitle", "reasons", "allReasonCount", "primaryCta"}
        assert required.issubset(d.keys())


# ── build_dashboard_essentials ────────────────────────────────────────────────


class TestBuildDashboardEssentials:
    def test_returns_dashboard_essentials_instance(self):
        result = build_dashboard_essentials(make_sites_mixed())
        assert isinstance(result, DashboardEssentials)

    def test_kpis_computed_correctly(self):
        sites = [
            make_site(1, statut="conforme"),
            make_site(2, statut="non_conforme"),
            make_site(3, statut="a_risque"),
        ]
        result = build_dashboard_essentials(sites)
        assert result.kpis["total"] == 3
        assert result.kpis["conformes"] == 1
        assert result.kpis["nonConformes"] == 1
        assert result.kpis["aRisque"] == 1

    def test_empty_sites(self):
        result = build_dashboard_essentials([])
        assert result.kpis["total"] == 0
        assert result.watchlist == []
        assert result.briefing == []

    def test_couverture_donnees_computed(self):
        sites = [
            make_site(1, conso_kwh_an=100_000),
            make_site(2, conso_kwh_an=0),
            make_site(3, conso_kwh_an=50_000),
            make_site(4, conso_kwh_an=0),
        ]
        result = build_dashboard_essentials(sites)
        # 2/4 = 50%
        assert result.kpis["couvertureDonnees"] == 50

    def test_to_dict_has_all_keys(self):
        result = build_dashboard_essentials(make_sites_mixed())
        d = result.to_dict()
        required = {
            "kpis",
            "watchlist",
            "briefing",
            "topSites",
            "opportunities",
            "todayActions",
            "executiveSummary",
            "executiveKpis",
            "consistency",
            "healthState",
        }
        assert required.issubset(d.keys())

    def test_is_expert_false_returns_no_opportunities(self):
        result = build_dashboard_essentials(make_sites_mixed(), is_expert=False)
        assert result.opportunities == []

    def test_is_expert_true_may_return_opportunities(self):
        sites = [make_site(i, statut="non_conforme", risque_eur=5_000) for i in range(5)]
        result = build_dashboard_essentials(sites, is_expert=True)
        # Avec nc présents et risque, des opportunities doivent apparaître
        assert len(result.opportunities) > 0

    def test_health_state_present(self):
        result = build_dashboard_essentials(make_sites_mixed())
        assert isinstance(result.health_state, HealthState)
        assert result.health_state.level in ("GREEN", "AMBER", "RED")

    def test_top_sites_present(self):
        result = build_dashboard_essentials(make_sites_mixed())
        assert isinstance(result.top_sites, TopSites)

    def test_executive_kpis_count(self):
        result = build_dashboard_essentials(make_sites_mixed())
        assert len(result.executive_kpis) == 4

    def test_all_sites_conforme_green_health(self):
        sites = [make_site(i, statut="conforme", conso_kwh_an=50_000) for i in range(5)]
        result = build_dashboard_essentials(sites)
        # Pas de NC ni AR → GREEN ou AMBER (si couverture basse) mais pas RED
        assert result.health_state.level != "RED"

    def test_alerts_count_propagated(self):
        sites = make_sites_mixed()
        result_no_alerts = build_dashboard_essentials(sites, alerts_count=0)
        result_alerts = build_dashboard_essentials(sites, alerts_count=10)
        # Avec alertes, le level ne devrait pas être GREEN (sauf déjà RED)
        if result_no_alerts.health_state.level == "GREEN":
            assert result_alerts.health_state.level in ("AMBER", "RED")


# ── Constantes canoniques ─────────────────────────────────────────────────────


class TestCanonicalConstants:
    """Vérifie que les constantes portées depuis JS sont correctes."""

    def test_risk_thresholds(self):
        assert RISK_THRESHOLDS_ORG_WARN == 10_000

    def test_coverage_thresholds(self):
        assert COVERAGE_SUSPICIOUS == 30
        assert COVERAGE_WARN == 50
        assert COVERAGE_OPPORTUNITY == 80

    def test_conformity_thresholds(self):
        assert CONFORMITY_POSITIVE == 80
        assert CONFORMITY_WARN == 50

    def test_maturity_thresholds(self):
        assert MATURITY_CRIT == 40
        assert MATURITY_WARN == 70

    def test_compliance_score_thresholds(self):
        assert COMPLIANCE_SCORE_OK == 80
        assert COMPLIANCE_SCORE_WARN == 50

    def test_severity_rank_order(self):
        assert SEVERITY_RANK["critical"] < SEVERITY_RANK["high"]
        assert SEVERITY_RANK["high"] < SEVERITY_RANK["warn"]
        assert SEVERITY_RANK["warn"] < SEVERITY_RANK["medium"]
        assert SEVERITY_RANK["medium"] < SEVERITY_RANK["info"]
