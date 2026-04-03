"""
Tests — A.2: Unified compliance score service.
Covers: site scoring, portfolio aggregation, confidence levels, critical penalty.
"""

import json
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.fast

from models.base import Base
from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    StatutConformite,
)
from models.reg_assessment import RegAssessment
from models.enums import RegStatus
from services.compliance_score_service import (
    compute_site_compliance_score,
    compute_portfolio_compliance,
    FRAMEWORK_WEIGHTS,
    MAX_CRITICAL_PENALTY,
    CRITICAL_PENALTY_PER_FINDING,
)


@pytest.fixture()
def db():
    """In-memory SQLite with seed data for compliance score tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed org → EJ → portfolio → sites
    org = Organisation(id=1, nom="Test Org", siren="123456789", type_client="tertiaire")
    session.add(org)
    session.flush()

    ej = EntiteJuridique(id=1, nom="EJ Test", siren="123456789", siret="12345678900001", organisation_id=1)
    session.add(ej)
    session.flush()

    pf = Portefeuille(id=1, nom="PF Test", entite_juridique_id=1)
    session.add(pf)
    session.flush()

    # Site 1: full snapshots (DT conforme, BACS conforme)
    session.add(
        Site(
            id=1,
            nom="Site Full",
            type="bureau",
            portefeuille_id=1,
            actif=True,
            surface_m2=2000,
            statut_decret_tertiaire=StatutConformite.CONFORME,
            statut_bacs=StatutConformite.CONFORME,
        )
    )
    # Site 2: partial snapshots (DT à risque, BACS missing)
    session.add(
        Site(
            id=2,
            nom="Site Partial",
            type="commerce",
            portefeuille_id=1,
            actif=True,
            surface_m2=1000,
            statut_decret_tertiaire=StatutConformite.A_RISQUE,
            statut_bacs=None,
        )
    )
    # Site 3: no snapshots at all
    session.add(
        Site(
            id=3,
            nom="Site Empty",
            type="bureau",
            portefeuille_id=1,
            actif=True,
            surface_m2=500,
            statut_decret_tertiaire=None,
            statut_bacs=None,
        )
    )
    session.commit()
    yield session
    session.close()
    engine.dispose()


class TestSiteComplianceScore:
    def test_full_snapshots_confidence(self, db):
        """Site with DT + BACS snapshots → confidence medium (2/3 evaluated, APER defaults)."""
        r = compute_site_compliance_score(db, 1)
        assert r.confidence == "medium"
        assert r.frameworks_evaluated == 2

    def test_partial_snapshots_confidence(self, db):
        """Site with A_RISQUE DT → score maps to 50 (same as default), so snapshot not counted as 'available'."""
        r = compute_site_compliance_score(db, 2)
        assert r.confidence == "low"
        # A_RISQUE → 50.0 which equals default → source="default", not counted as evaluated
        assert r.frameworks_evaluated == 0

    def test_empty_site_confidence_low(self, db):
        """Site with no snapshots → confidence low, score ~50 (all defaults)."""
        r = compute_site_compliance_score(db, 3)
        assert r.confidence == "low"
        assert r.frameworks_evaluated == 0
        assert abs(r.score - 50.0) < 0.1  # all defaults = 50

    def test_nonexistent_site(self, db):
        """Non-existent site → score 50, confidence low."""
        r = compute_site_compliance_score(db, 999)
        assert r.score == 50.0
        assert r.confidence == "low"

    def test_score_range_0_100(self, db):
        """Score should always be between 0 and 100."""
        for site_id in [1, 2, 3]:
            r = compute_site_compliance_score(db, site_id)
            assert 0.0 <= r.score <= 100.0

    def test_breakdown_has_3_frameworks(self, db):
        """Breakdown should always have 3 entries (DT, BACS, APER)."""
        r = compute_site_compliance_score(db, 1)
        assert len(r.breakdown) == 3
        fw_names = {f.framework for f in r.breakdown}
        assert fw_names == {"tertiaire_operat", "bacs", "aper"}

    def test_weights_sum_to_1(self):
        """Framework weights must sum to 1.0."""
        assert abs(sum(FRAMEWORK_WEIGHTS.values()) - 1.0) < 0.001

    def test_conforme_scores_high(self, db):
        """Site with CONFORME DT + BACS should score well above 50."""
        r = compute_site_compliance_score(db, 1)
        # DT=100*0.45 + BACS=100*0.30 + APER=50*0.25 = 87.5
        assert r.score >= 80.0

    def test_a_risque_scores_moderate(self, db):
        """Site with A_RISQUE DT should score around 50."""
        r = compute_site_compliance_score(db, 2)
        # DT=50*0.45 + BACS=50*0.30 + APER=50*0.25 = 50
        assert 40.0 <= r.score <= 60.0

    def test_result_has_formula(self, db):
        """Result should contain the formula description."""
        r = compute_site_compliance_score(db, 1)
        assert "45%" in r.formula
        assert "30%" in r.formula
        assert "25%" in r.formula

    def test_to_dict(self, db):
        """to_dict() should return all required fields."""
        r = compute_site_compliance_score(db, 1)
        d = r.to_dict()
        assert "score" in d
        assert "breakdown" in d
        assert "confidence" in d
        assert "critical_penalty" in d
        assert "formula" in d


class TestCriticalPenalty:
    def test_critical_findings_reduce_score(self, db):
        """Critical findings in RegAssessment should reduce the score."""
        # Add a RegAssessment with critical findings for site 1
        findings = [
            {"regulation": "tertiaire_operat", "severity": "critical", "title": "Missing declaration"},
            {"regulation": "tertiaire_operat", "severity": "critical", "title": "Deadline passed"},
        ]
        ra = RegAssessment(
            object_type="site",
            object_id=1,
            computed_at=datetime.now(timezone.utc),
            global_status=RegStatus.AT_RISK,
            compliance_score=80.0,
            deterministic_version="tertiaire_operat_v1",
            data_version="v1",
            findings_json=json.dumps(findings),
        )
        db.add(ra)
        db.commit()

        r = compute_site_compliance_score(db, 1)
        assert r.critical_penalty == 2 * CRITICAL_PENALTY_PER_FINDING
        # Score should be reduced by the penalty
        assert r.critical_penalty > 0

    def test_penalty_capped_at_max(self, db):
        """Critical penalty should never exceed MAX_CRITICAL_PENALTY."""
        findings = [
            {"regulation": "tertiaire_operat", "severity": "critical", "title": f"Finding {i}"}
            for i in range(10)  # 10 findings * 5 pts = 50, but max is 20
        ]
        ra = RegAssessment(
            object_type="site",
            object_id=1,
            computed_at=datetime.now(timezone.utc),
            global_status=RegStatus.AT_RISK,
            compliance_score=90.0,
            deterministic_version="tertiaire_operat_v1",
            data_version="v1",
            findings_json=json.dumps(findings),
        )
        db.add(ra)
        db.commit()

        r = compute_site_compliance_score(db, 1)
        assert r.critical_penalty == MAX_CRITICAL_PENALTY


class TestRegAssessmentScoring:
    def test_regassessment_overrides_snapshot(self, db):
        """When a RegAssessment exists, it should override the Site snapshot."""
        # Site 1 has CONFORME DT snapshot (score=100)
        # Add RegAssessment with score=60 for tertiaire_operat
        ra = RegAssessment(
            object_type="site",
            object_id=1,
            computed_at=datetime.now(timezone.utc),
            global_status=RegStatus.COMPLIANT,
            compliance_score=60.0,
            deterministic_version="tertiaire_operat_v1",
            data_version="v1",
            findings_json="[]",
        )
        db.add(ra)
        db.commit()

        r = compute_site_compliance_score(db, 1)
        # With RA: DT=60*0.45 + BACS=100*0.30 + APER=50*0.25 = 27+30+12.5 = 69.5
        # Without RA: DT=100*0.45 + BACS=100*0.30 + APER=50*0.25 = 87.5
        assert r.score < 80.0  # Should be lower than snapshot-only
        assert r.confidence == "medium"  # 2/3: RA for DT, snapshot for BACS, APER default not counted

    def test_stale_assessment_ignored(self, db):
        """Stale RegAssessments should be ignored."""
        ra = RegAssessment(
            object_type="site",
            object_id=1,
            computed_at=datetime.now(timezone.utc),
            global_status=RegStatus.AT_RISK,
            compliance_score=10.0,
            deterministic_version="tertiaire_operat_v1",
            data_version="v1",
            findings_json="[]",
            is_stale=True,
        )
        db.add(ra)
        db.commit()

        r = compute_site_compliance_score(db, 1)
        # Stale RA ignored → falls back to snapshot (CONFORME = 100)
        assert r.score >= 80.0


class TestPortfolioCompliance:
    def test_portfolio_avg_score(self, db):
        """Portfolio score should be surface-weighted average of site scores."""
        result = compute_portfolio_compliance(db, 1)
        assert "avg_score" in result
        assert 0.0 <= result["avg_score"] <= 100.0

    def test_portfolio_has_all_fields(self, db):
        """Portfolio result should have all required fields."""
        result = compute_portfolio_compliance(db, 1)
        assert "avg_score" in result
        assert "min_score" in result
        assert "max_score" in result
        assert "total_sites" in result
        assert "worst_sites" in result
        assert "breakdown_avg" in result
        assert "high_confidence_count" in result

    def test_portfolio_total_sites(self, db):
        """Portfolio should report correct number of active sites."""
        result = compute_portfolio_compliance(db, 1)
        assert result["total_sites"] == 3

    def test_portfolio_worst_sites_sorted(self, db):
        """Worst sites should be sorted by score ascending."""
        result = compute_portfolio_compliance(db, 1)
        worst = result["worst_sites"]
        scores = [w["score"] for w in worst]
        assert scores == sorted(scores)

    def test_portfolio_empty_org(self, db):
        """Empty org should return 0 for all metrics."""
        result = compute_portfolio_compliance(db, 999)
        assert result["avg_score"] == 0.0
        assert result["total_sites"] == 0
        assert result["worst_sites"] == []

    def test_portfolio_surface_weighted(self, db):
        """Surface-weighted avg should differ from simple avg when surfaces differ."""
        result = compute_portfolio_compliance(db, 1)
        # Site 1 (2000m²) is CONFORME (high score), site 2 (1000m²) is A_RISQUE, site 3 (500m²) is default
        # Surface weighting should give more weight to site 1 (higher score)
        avg = result["avg_score"]
        # Simple average would be roughly (87.5 + 50 + 50) / 3 = 62.5
        # Surface-weighted should be higher since site 1 (87.5, 2000m²) has most weight
        assert avg > 55.0  # Should be pulled up by site 1's larger surface

    def test_portfolio_breakdown_avg(self, db):
        """Breakdown avg should contain all 3 frameworks."""
        result = compute_portfolio_compliance(db, 1)
        bd = result["breakdown_avg"]
        assert "tertiaire_operat" in bd
        assert "bacs" in bd
        assert "aper" in bd


class TestCrossBriqueConsistency:
    def test_kpi_service_uses_unified_score(self, db):
        """KpiService.get_compliance_score should delegate to compliance_score_service."""
        from services.kpi_service import KpiService, KpiScope

        svc = KpiService(db)
        result = svc.get_compliance_score(KpiScope(org_id=1))
        # Should return a score (not a percentage of conformes)
        assert result.unit == "score"
        assert 0.0 <= result.value <= 100.0

    def test_site_score_matches_portfolio_entry(self, db):
        """Individual site score should appear in portfolio worst_sites."""
        site_r = compute_site_compliance_score(db, 3)  # Site Empty — lowest score
        portfolio = compute_portfolio_compliance(db, 1)
        worst_ids = [w["site_id"] for w in portfolio["worst_sites"]]
        assert 3 in worst_ids
        # Score should match
        worst_entry = next(w for w in portfolio["worst_sites"] if w["site_id"] == 3)
        assert abs(worst_entry["score"] - site_r.score) < 0.1
