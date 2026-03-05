"""
PROMEOS - V68 Compliance Pipeline Tests
Tests: readiness gate, applicability, scores, deadlines, data trust, snapshots.
"""

import json
import os
import pytest
from datetime import date
from unittest.mock import MagicMock

from models import (
    Site,
    Batiment,
    Obligation,
    Evidence,
    ComplianceFinding,
    TypeObligation,
    StatutConformite,
    TypeEvidence,
    StatutEvidence,
    TypeSite,
    InsightStatus,
)
from services.compliance_engine import (
    compute_readiness,
    compute_applicability,
    compute_scores,
    compute_deadlines,
    compute_data_trust,
    compute_site_compliance_summary,
    compute_portfolio_compliance_summary,
)

SNAPSHOTS_DIR = os.path.join(os.path.dirname(__file__), "snapshots")
os.makedirs(SNAPSHOTS_DIR, exist_ok=True)


# ── Helpers ──────────────────────────────────────────────────


def _make_site(**kwargs):
    defaults = dict(
        id=1,
        nom="Bureau Test",
        type=TypeSite.BUREAU,
        tertiaire_area_m2=None,
        roof_area_m2=None,
        parking_area_m2=None,
        parking_type=None,
        operat_status=None,
        annual_kwh_total=None,
        is_multi_occupied=False,
        naf_code=None,
        surface_m2=None,
        statut_decret_tertiaire=StatutConformite.A_RISQUE,
        statut_bacs=StatutConformite.A_RISQUE,
        avancement_decret_pct=0.0,
        anomalie_facture=False,
        action_recommandee=None,
        risque_financier_euro=0.0,
        last_energy_update_at=None,
    )
    defaults.update(kwargs)
    site = MagicMock(spec=Site)
    for k, v in defaults.items():
        setattr(site, k, v)
    # Remove spec attributes that don't exist
    site._cvc_kw = kwargs.get("_cvc_kw", None)
    return site


def _make_batiment(site_id=1, cvc_power_kw=None):
    b = MagicMock(spec=Batiment)
    b.site_id = site_id
    b.cvc_power_kw = cvc_power_kw
    return b


def _make_obligation(
    site_id=1,
    type_=TypeObligation.BACS,
    statut=StatutConformite.A_RISQUE,
    echeance=None,
    avancement_pct=50.0,
    description="",
):
    o = MagicMock(spec=Obligation)
    o.site_id = site_id
    o.type = type_
    o.statut = statut
    o.echeance = echeance
    o.avancement_pct = avancement_pct
    o.description = description
    return o


def _make_evidence(site_id=1, type_=TypeEvidence.AUDIT, statut=StatutEvidence.VALIDE):
    e = MagicMock(spec=Evidence)
    e.site_id = site_id
    e.type = type_
    e.statut = statut
    return e


def _make_finding(
    site_id=1, regulation="bacs", status="NOK", severity="high", deadline=None, evidence="test", rule_id="TEST"
):
    f = MagicMock(spec=ComplianceFinding)
    f.site_id = site_id
    f.regulation = regulation
    f.status = status
    f.severity = severity
    f.deadline = deadline
    f.evidence = evidence
    f.rule_id = rule_id
    return f


# ═══════════════════════════════════════════════
# Test: compute_readiness
# ═══════════════════════════════════════════════


class TestReadiness:
    def test_blocking_missing_surface(self):
        """Site without tertiaire_area_m2 → BLOCKED gate."""
        site = _make_site()
        result = compute_readiness(site, [], [])
        assert result["gate_status"] == "BLOCKED"
        blocking_fields = [m["field"] for m in result["missing"] if m["level"] == "blocking"]
        assert "tertiaire_area_m2" in blocking_fields

    def test_all_filled_ok(self):
        """Site with all fields filled → OK gate."""
        site = _make_site(
            tertiaire_area_m2=1500,
            operat_status="submitted",
            annual_kwh_total=100000,
            parking_area_m2=2000,
            roof_area_m2=800,
            parking_type="outdoor",
            is_multi_occupied=True,
            naf_code="7022Z",
            surface_m2=3000,
        )
        bats = [_make_batiment(cvc_power_kw=300)]
        evs = [
            _make_evidence(type_=TypeEvidence.ATTESTATION_BACS),
            _make_evidence(type_=TypeEvidence.DEROGATION_BACS),
        ]
        result = compute_readiness(site, bats, evs)
        assert result["gate_status"] == "OK"
        assert result["completeness_pct"] == 100.0

    def test_warning_when_optional_missing(self):
        """All blocking filled but recommended missing → WARNING."""
        site = _make_site(
            tertiaire_area_m2=1500,
            operat_status="submitted",
            annual_kwh_total=100000,
            parking_area_m2=2000,
            roof_area_m2=800,
        )
        bats = [_make_batiment(cvc_power_kw=300)]
        result = compute_readiness(site, bats, [])
        assert result["gate_status"] == "WARNING"

    def test_cta_links_present(self):
        """Each missing field has a cta_target and cta_label."""
        site = _make_site()
        result = compute_readiness(site, [], [])
        for m in result["missing"]:
            assert "cta_target" in m
            assert "cta_label" in m
            assert m["cta_target"] in ("patrimoine", "consommation", "conformite", "billing")


# ═══════════════════════════════════════════════
# Test: compute_applicability
# ═══════════════════════════════════════════════


class TestApplicability:
    def test_uncertain_when_missing_cvc_power(self):
        """No CVC power → bacs applicability = None (uncertain)."""
        site = _make_site()
        result = compute_applicability(site, [])
        assert result["bacs"]["applicable"] is None
        assert "cvc_power_kw" in result["bacs"]["missing_fields"]

    def test_applicable_tertiaire_1500(self):
        site = _make_site(tertiaire_area_m2=1500)
        result = compute_applicability(site, [])
        assert result["tertiaire_operat"]["applicable"] is True

    def test_not_applicable_tertiaire_500(self):
        site = _make_site(tertiaire_area_m2=500)
        result = compute_applicability(site, [])
        assert result["tertiaire_operat"]["applicable"] is False

    def test_bacs_applicable_300kw(self):
        site = _make_site()
        bats = [_make_batiment(cvc_power_kw=300)]
        result = compute_applicability(site, bats)
        assert result["bacs"]["applicable"] is True

    def test_aper_applicable_large_parking(self):
        site = _make_site(parking_area_m2=2000, roof_area_m2=100)
        result = compute_applicability(site, [])
        assert result["aper"]["applicable"] is True


# ═══════════════════════════════════════════════
# Test: compute_scores
# ═══════════════════════════════════════════════


class TestScores:
    def test_no_risk_when_conforme(self):
        obs = [_make_obligation(statut=StatutConformite.CONFORME)]
        result = compute_scores(obs, [])
        assert result["reg_risk"] == 0
        assert result["financial_opportunity_eur"] == 0

    def test_high_risk_nok(self):
        obs = [_make_obligation(statut=StatutConformite.NON_CONFORME)]
        findings = [_make_finding(status="NOK")]
        result = compute_scores(obs, findings)
        assert result["reg_risk"] >= 30
        assert result["financial_opportunity_eur"] == 7500.0

    def test_a_risque_half_penalty(self):
        """A_RISQUE = 50% penalty (3750€)."""
        obs = [_make_obligation(statut=StatutConformite.A_RISQUE)]
        result = compute_scores(obs, [])
        assert result["financial_opportunity_eur"] == 3750.0

    def test_mixed_nok_and_a_risque(self):
        """2 NON_CONFORME + 1 A_RISQUE = 2*7500 + 1*3750 = 18750€."""
        obs = [
            _make_obligation(statut=StatutConformite.NON_CONFORME),
            _make_obligation(statut=StatutConformite.NON_CONFORME),
            _make_obligation(statut=StatutConformite.A_RISQUE),
        ]
        result = compute_scores(obs, [])
        assert result["financial_opportunity_eur"] == 18750.0

    def test_compliance_score_higher_is_better(self):
        """compliance_score = 100 - compliance_risk_score (higher=better)."""
        obs_conforme = [_make_obligation(statut=StatutConformite.CONFORME)]
        result_ok = compute_scores(obs_conforme, [])
        assert result_ok["compliance_score"] == 100
        assert result_ok["compliance_risk_score"] == 0

        obs_nok = [_make_obligation(statut=StatutConformite.NON_CONFORME)]
        result_bad = compute_scores(obs_nok, [])
        assert result_bad["compliance_score"] < 100  # worse than conforme
        assert result_bad["compliance_score"] == 100 - result_bad["compliance_risk_score"]
        assert result_bad["compliance_risk_score"] >= 30


# ═══════════════════════════════════════════════
# Test: compute_deadlines
# ═══════════════════════════════════════════════


class TestDeadlines:
    def test_sort_30_90_180(self):
        """Deadlines are bucketed into 30/90/180 day windows."""
        today = date(2026, 1, 1)
        obs = [
            _make_obligation(echeance=date(2026, 1, 15), statut=StatutConformite.A_RISQUE, description="14 days"),
            _make_obligation(echeance=date(2026, 3, 15), statut=StatutConformite.NON_CONFORME, description="73 days"),
            _make_obligation(echeance=date(2026, 6, 1), statut=StatutConformite.A_RISQUE, description="151 days"),
        ]
        result = compute_deadlines(obs, [], today)
        assert len(result["d30"]) == 1
        assert len(result["d90"]) == 1
        assert len(result["d180"]) == 1

    def test_conforme_obligations_excluded(self):
        """Conforme obligations don't appear in deadlines."""
        today = date(2026, 1, 1)
        obs = [_make_obligation(echeance=date(2026, 1, 15), statut=StatutConformite.CONFORME)]
        result = compute_deadlines(obs, [], today)
        assert len(result["d30"]) == 0

    def test_findings_included(self):
        """NOK findings with deadlines appear in deadline buckets."""
        today = date(2026, 1, 1)
        findings = [_make_finding(deadline=date(2026, 2, 1), status="NOK")]
        result = compute_deadlines([], findings, today)
        assert len(result["d90"]) == 1


# ═══════════════════════════════════════════════
# Test: compute_data_trust
# ═══════════════════════════════════════════════


class TestDataTrust:
    def test_stub_when_no_billing(self):
        """When BillingInsight table doesn't exist, return 100 trust."""
        site = _make_site()
        db = MagicMock()
        db.query.side_effect = Exception("no such table")
        result = compute_data_trust(site, db)
        assert result["trust_score"] == 100
        assert "billing_not_available" in result["reasons"]

    def test_perfect_trust_no_anomalies(self):
        site = _make_site()
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []
        result = compute_data_trust(site, db)
        assert result["trust_score"] == 100


# ═══════════════════════════════════════════════
# Snapshot: Portfolio_Min (4 sites)
# ═══════════════════════════════════════════════

PORTFOLIO_MIN_SNAPSHOT_FILE = os.path.join(SNAPSHOTS_DIR, "portfolio_min_v68.json")


class TestPortfolioMinFixture:
    """Validate readiness computations for a minimal 4-site portfolio."""

    @pytest.fixture
    def four_sites(self):
        return [
            _make_site(
                id=1,
                nom="Bureau Paris",
                tertiaire_area_m2=1500,
                annual_kwh_total=120000,
                operat_status="submitted",
                parking_area_m2=2000,
                roof_area_m2=800,
            ),
            _make_site(id=2, nom="Entrepot Lyon", tertiaire_area_m2=None, parking_area_m2=500, roof_area_m2=200),
            _make_site(id=3, nom="Agence Nantes", tertiaire_area_m2=800, parking_area_m2=100, roof_area_m2=100),
            _make_site(
                id=4,
                nom="Usine Bordeaux",
                tertiaire_area_m2=3000,
                annual_kwh_total=500000,
                operat_status="in_progress",
                parking_area_m2=3000,
                roof_area_m2=1500,
            ),
        ]

    def test_portfolio_readiness_distribution(self, four_sites):
        """Portfolio of 4 sites: verify gate distribution."""
        gates = []
        for s in four_sites:
            r = compute_readiness(s, [], [])
            gates.append(r["gate_status"])

        # Site 1: has critical fields for tertiaire → maybe WARNING (missing bacs etc)
        # Site 2: missing tertiaire_area_m2 → BLOCKED
        # Site 3: has tertiaire but <1000, missing others → BLOCKED
        # Site 4: most filled → WARNING or OK
        assert "BLOCKED" in gates, f"Expected at least one BLOCKED site, got: {gates}"

    def test_snapshot_stability(self, four_sites):
        """Generate and compare golden snapshot."""
        results = []
        for s in four_sites:
            r = compute_readiness(s, [], [])
            a = compute_applicability(s, [])
            results.append(
                {
                    "site_id": s.id,
                    "site_nom": s.nom,
                    "readiness": r,
                    "applicability": a,
                }
            )

        snapshot = {"version": "v68", "sites": results}

        if not os.path.exists(PORTFOLIO_MIN_SNAPSHOT_FILE):
            with open(PORTFOLIO_MIN_SNAPSHOT_FILE, "w") as f:
                json.dump(snapshot, f, indent=2, default=str)
            pytest.skip("Golden snapshot created — rerun to validate")
        else:
            with open(PORTFOLIO_MIN_SNAPSHOT_FILE) as f:
                expected = json.load(f)
            assert snapshot == expected, "Snapshot mismatch! Delete snapshot to regenerate."
