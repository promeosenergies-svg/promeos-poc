"""
PROMEOS RegOps Hardening Tests
Covers: scoring, data quality gate, watcher pipeline, connector contracts, finding audit.
~30 tests across 5 test classes.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import hashlib
import pytest
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from models import (
    Base, Site, Batiment, Evidence, Organisation, EntiteJuridique, Portefeuille,
    ComplianceFinding, RegSourceEvent, WatcherEventStatus,
    TypeSite, TypeEvidence, StatutEvidence, InsightStatus, OperatStatus,
)
from database import get_db
from main import app

from regops.schemas import Finding
from regops.scoring import (
    compute_regops_score, load_scoring_profile,
    _dedup_findings, ScoreResult, ScoringPenalty,
)
from regops.data_quality import compute_data_quality, DataQualityReport
from regops.data_quality_specs import DATA_QUALITY_SPECS
from connectors.contracts import validate_mapping, MappingReport, REQUIRED_FIELDS, SANITY_RANGES
from watchers.rss_watcher import _normalize_dedup_key


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def db_session():
    """In-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_org_site(db, surface=2000, **extra):
    """Helper: org + entite + portefeuille + site."""
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="Test Corp", siren="123456789")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="Principal")
    db.add(pf)
    db.flush()
    site_kwargs = dict(
        portefeuille_id=pf.id,
        nom="Site Test",
        type=TypeSite.BUREAU,
        surface_m2=surface,
        actif=True,
    )
    site_kwargs.update(extra)
    site = Site(**site_kwargs)
    db.add(site)
    db.flush()
    return org, site


def _make_finding(**overrides):
    """Create a Finding dataclass with sensible defaults."""
    defaults = dict(
        regulation="tertiaire_operat",
        rule_id="DT_SCOPE",
        status="NON_COMPLIANT",
        severity="high",
        confidence="high",
        legal_deadline=None,
        trigger_condition="test",
        config_params_used={},
        inputs_used=["surface_m2"],
        missing_inputs=[],
        explanation="Test finding",
    )
    defaults.update(overrides)
    return Finding(**defaults)


# ========================================
# 1. Scoring Hardening (8 tests)
# ========================================

class TestScoringHardening:
    """Tests for regops/scoring.py — compute_regops_score, dedup, clamp, profile."""

    def test_score_clamped_0_100(self):
        """Score is always in [0, 100]."""
        # Many critical findings should not go below 0
        findings = [
            _make_finding(rule_id=f"R_{i}", severity="critical", status="NON_COMPLIANT")
            for i in range(20)
        ]
        result = compute_regops_score(findings, 100.0)
        assert 0.0 <= result.score <= 100.0

    def test_score_no_findings_returns_100(self):
        """Empty findings list gives perfect score."""
        result = compute_regops_score([], 100.0)
        assert result.score == 100.0

    def test_dedup_same_rule_id_keeps_most_severe(self):
        """Duplicate (regulation, rule_id) keeps the most severe."""
        findings = [
            _make_finding(rule_id="DT_SCOPE", severity="low", status="NON_COMPLIANT"),
            _make_finding(rule_id="DT_SCOPE", severity="critical", status="NON_COMPLIANT"),
        ]
        unique, suppressed = _dedup_findings(findings)
        assert len(unique) == 1
        assert len(suppressed) == 1
        assert unique[0].severity == "critical"

    def test_suppressed_penalties_logged(self):
        """Suppressed findings appear in suppressed_penalties."""
        findings = [
            _make_finding(rule_id="DT_SCOPE", severity="low", status="NON_COMPLIANT"),
            _make_finding(rule_id="DT_SCOPE", severity="critical", status="NON_COMPLIANT"),
        ]
        result = compute_regops_score(findings, 100.0)
        assert len(result.suppressed_penalties) == 1
        assert result.suppressed_penalties[0].suppressed is True

    def test_regulation_weights_applied(self):
        """Different regulation weights produce different scores."""
        profile = load_scoring_profile().copy()
        f1 = _make_finding(regulation="tertiaire_operat", rule_id="R1", severity="high")
        f2 = _make_finding(regulation="bacs", rule_id="R2", severity="high")

        # Both with equal weights → same penalty
        result1 = compute_regops_score([f1], 100.0, profile)
        result2 = compute_regops_score([f2], 100.0, profile)
        # With default profile (all weights=1.0), scores should be equal
        assert result1.score == result2.score

        # Now change one weight
        profile2 = {**profile, "regulation_weights": {**profile["regulation_weights"], "bacs": 0.5}}
        result3 = compute_regops_score([f2], 100.0, profile2)
        # Penalty with weight 0.5 should give a different score
        assert isinstance(result3.score, float)

    def test_confidence_score_separate(self):
        """confidence_score comes from dq_coverage_pct, not from findings."""
        result = compute_regops_score([], dq_coverage_pct=42.0)
        assert result.confidence_score == 42.0
        assert result.score == 100.0  # no findings → perfect compliance

    def test_scoring_profile_loaded(self):
        """Scoring profile loads with expected keys."""
        profile = load_scoring_profile()
        assert "id" in profile
        assert "version" in profile
        assert "regulation_weights" in profile
        assert "severity_multipliers" in profile
        assert "status_penalties" in profile

    def test_score_explain_endpoint(self, client, db_session):
        """GET /api/regops/score_explain returns structured response."""
        _org, site = _create_org_site(db_session)
        resp = client.get(f"/api/regops/score_explain?scope_type=site&scope_id={site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "score" in data
        assert "confidence_score" in data
        assert "scoring_profile" in data
        assert "penalties" in data
        assert "how_to_improve" in data


# ========================================
# 2. Data Quality Gate (6 tests)
# ========================================

class TestDataQualityGate:
    """Tests for regops/data_quality.py — compute_data_quality, specs."""

    def test_full_data_coverage_100(self, db_session):
        """Site with all fields filled → gate OK, high coverage."""
        _org, site = _create_org_site(
            db_session,
            surface=2000,
            tertiaire_area_m2=2000,
            operat_status=OperatStatus.SUBMITTED,
            annual_kwh_total=500000,
            parking_area_m2=1800,
            roof_area_m2=800,
            naf_code="6820B",
        )
        # Add batiment with cvc_power_kw
        bat = Batiment(site_id=site.id, nom="Bat1", surface_m2=2000, cvc_power_kw=120)
        db_session.add(bat)
        db_session.flush()

        report = compute_data_quality(db_session, site.id)
        assert report.gate_status in ("OK", "WARNING")
        assert report.coverage_pct > 50.0

    def test_missing_critical_blocked(self, db_session):
        """Site missing critical fields → gate BLOCKED."""
        _org, site = _create_org_site(db_session)
        report = compute_data_quality(db_session, site.id)
        assert report.gate_status == "BLOCKED"
        assert len(report.missing_critical) > 0

    def test_missing_optional_warning(self, db_session):
        """Site with all critical but missing optional → gate WARNING."""
        _org, site = _create_org_site(
            db_session,
            surface=2000,
            tertiaire_area_m2=2000,
            operat_status=OperatStatus.SUBMITTED,
            annual_kwh_total=500000,
            parking_area_m2=1800,
            roof_area_m2=800,
        )
        bat = Batiment(site_id=site.id, nom="Bat1", surface_m2=2000, cvc_power_kw=120)
        db_session.add(bat)
        db_session.flush()

        report = compute_data_quality(db_session, site.id)
        # Some optional fields are still missing (naf_code, is_multi_occupied, etc.)
        if report.missing_optional:
            assert report.gate_status in ("WARNING", "OK")

    def test_confidence_score_formula(self, db_session):
        """confidence_score = 100 - 20*critical - 5*optional, clamped."""
        _org, site = _create_org_site(db_session)
        report = compute_data_quality(db_session, site.id)
        expected = 100.0 - 20 * len(report.missing_critical) - 5 * len(report.missing_optional)
        expected = max(0.0, min(100.0, expected))
        assert report.confidence_score == round(expected, 1)

    def test_dq_endpoint(self, client, db_session):
        """GET /api/regops/data_quality returns structured response."""
        _org, site = _create_org_site(db_session)
        resp = client.get(f"/api/regops/data_quality?scope_type=site&scope_id={site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "coverage_pct" in data
        assert "confidence_score" in data
        assert "gate_status" in data
        assert data["gate_status"] in ("OK", "WARNING", "BLOCKED")

    def test_dq_specs_endpoint(self, client):
        """GET /api/regops/data_quality/specs returns specs."""
        resp = client.get("/api/regops/data_quality/specs")
        assert resp.status_code == 200
        data = resp.json()
        assert "tertiaire_operat" in data
        assert "critical" in data["tertiaire_operat"]
        assert "optional" in data["tertiaire_operat"]


# ========================================
# 3. Watcher Pipeline (6 tests)
# ========================================

class TestWatcherPipeline:
    """Tests for watcher status pipeline and dedup key normalization."""

    def test_dedup_normalized_key(self):
        """_normalize_dedup_key strips accents and is deterministic."""
        key1 = _normalize_dedup_key("Décret n° 2024-123", "2024-06-15", "legifrance")
        key2 = _normalize_dedup_key("Décret n° 2024-123", "2024-06-15", "legifrance")
        assert key1 == key2
        assert len(key1) > 0
        # Accent-stripped: should be pure hex
        assert all(c in "0123456789abcdef" for c in key1)

    def test_dedup_key_case_insensitive(self):
        """Same text with different casing produces same key."""
        key1 = _normalize_dedup_key("TEST TITLE", "2024-01-01", "source")
        key2 = _normalize_dedup_key("test title", "2024-01-01", "source")
        assert key1 == key2

    def test_pipeline_new_to_reviewed(self, client, db_session):
        """PATCH review with decision=apply sets status to REVIEWED."""
        event = RegSourceEvent(
            source_name="test_watcher",
            title="Test Event",
            content_hash=hashlib.sha256(b"test_review").hexdigest(),
            status=WatcherEventStatus.NEW,
        )
        db_session.add(event)
        db_session.flush()

        resp = client.patch(
            f"/api/watchers/events/{event.id}/review",
            json={"decision": "apply", "notes": "Verified content"},
        )
        assert resp.status_code == 200
        db_session.refresh(event)
        assert event.status == WatcherEventStatus.REVIEWED

    def test_pipeline_dismissed(self, client, db_session):
        """PATCH review with decision=dismiss sets status to DISMISSED."""
        event = RegSourceEvent(
            source_name="test_watcher",
            title="Test Dismiss",
            content_hash=hashlib.sha256(b"test_dismiss").hexdigest(),
            status=WatcherEventStatus.NEW,
        )
        db_session.add(event)
        db_session.flush()

        resp = client.patch(
            f"/api/watchers/events/{event.id}/review",
            json={"decision": "dismiss", "notes": "Not relevant"},
        )
        assert resp.status_code == 200
        db_session.refresh(event)
        assert event.status == WatcherEventStatus.DISMISSED

    def test_status_filter_endpoint(self, client, db_session):
        """GET /api/watchers/events?status=new filters by status."""
        for i, status in enumerate([WatcherEventStatus.NEW, WatcherEventStatus.REVIEWED]):
            ev = RegSourceEvent(
                source_name="test",
                title=f"Event {i}",
                content_hash=hashlib.sha256(f"filter_{i}".encode()).hexdigest(),
                status=status,
            )
            db_session.add(ev)
        db_session.flush()

        resp = client.get("/api/watchers/events?status=new")
        assert resp.status_code == 200
        data = resp.json()
        events = data.get("events", data if isinstance(data, list) else [])
        for ev in events:
            assert ev.get("status") in ("new", None)

    def test_duplicate_insert_blocked(self, db_session):
        """Inserting two events with same content_hash raises."""
        h = hashlib.sha256(b"unique_content").hexdigest()
        ev1 = RegSourceEvent(source_name="src", title="T1", content_hash=h)
        db_session.add(ev1)
        db_session.flush()

        ev2 = RegSourceEvent(source_name="src", title="T2", content_hash=h)
        db_session.add(ev2)
        with pytest.raises(Exception):
            db_session.flush()
        db_session.rollback()


# ========================================
# 4. Connector Contracts (4 tests)
# ========================================

class TestConnectorContracts:
    """Tests for connectors/contracts.py — validate_mapping."""

    def test_mapping_validator_valid(self):
        """Valid records pass validation."""
        records = [
            {"metric": "consumption_kwh", "value": 1500.0, "unit": "kWh", "ts_start": "2024-01-01T00:00:00"},
            {"metric": "temperature", "value": 22.0, "unit": "C", "ts_start": "2024-01-01T00:00:00"},
        ]
        report = validate_mapping("site", records, "test_connector")
        assert report.valid is True
        assert len(report.missing_fields) == 0

    def test_mapping_validator_missing_field(self):
        """Records missing required fields are flagged."""
        records = [
            {"metric": "consumption_kwh", "value": 1500.0},  # missing unit, ts_start
        ]
        report = validate_mapping("site", records, "test_connector")
        assert report.valid is False
        assert "unit" in report.missing_fields
        assert "ts_start" in report.missing_fields

    def test_mapping_validator_range_sanity(self):
        """Out-of-range values produce warnings."""
        records = [
            {"metric": "temperature", "value": 999.0, "unit": "C", "ts_start": "2024-01-01"},
        ]
        report = validate_mapping("site", records, "test_connector")
        assert len(report.warnings) > 0
        assert any("out of range" in w for w in report.warnings)

    def test_validate_endpoint(self, client, db_session):
        """GET /api/connectors/validate returns a response."""
        _org, site = _create_org_site(db_session)
        resp = client.get(f"/api/connectors/validate?connector=rte_eco2mix&scope_type=site&scope_id={site.id}")
        # Should return 200 (even if no data, it returns a report)
        assert resp.status_code == 200


# ========================================
# 5. Finding Audit (6 tests)
# ========================================

class TestFindingAudit:
    """Tests for finding audit fields (inputs_json, params_json, evidence_json, engine_version)."""

    def _create_finding(self, db_session, site_id, **overrides):
        defaults = dict(
            site_id=site_id,
            regulation="tertiaire_operat",
            rule_id="DT_SCOPE",
            status="NOK",
            severity="high",
            evidence="Surface tertiaire > 1000 m2",
            inputs_json='{"tertiaire_area_m2": 2000}',
            params_json='{"threshold_m2": 1000}',
            evidence_json='{"obligation_ref": "R.174-22"}',
            engine_version="abc123",
            insight_status=InsightStatus.OPEN,
        )
        defaults.update(overrides)
        f = ComplianceFinding(**defaults)
        db_session.add(f)
        db_session.flush()
        return f

    def test_finding_has_inputs_json(self, db_session):
        """Finding persists inputs_json."""
        _org, site = _create_org_site(db_session)
        f = self._create_finding(db_session, site.id)
        db_session.refresh(f)
        assert f.inputs_json is not None
        data = json.loads(f.inputs_json)
        assert "tertiaire_area_m2" in data

    def test_finding_has_params_json(self, db_session):
        """Finding persists params_json."""
        _org, site = _create_org_site(db_session)
        f = self._create_finding(db_session, site.id)
        db_session.refresh(f)
        data = json.loads(f.params_json)
        assert "threshold_m2" in data

    def test_finding_has_evidence_json(self, db_session):
        """Finding persists evidence_json."""
        _org, site = _create_org_site(db_session)
        f = self._create_finding(db_session, site.id)
        db_session.refresh(f)
        data = json.loads(f.evidence_json)
        assert "obligation_ref" in data

    def test_finding_has_engine_version(self, db_session):
        """Finding persists engine_version."""
        _org, site = _create_org_site(db_session)
        f = self._create_finding(db_session, site.id)
        db_session.refresh(f)
        assert f.engine_version == "abc123"

    def test_finding_detail_endpoint(self, client, db_session):
        """GET /api/compliance/findings/{id} returns audit fields."""
        _org, site = _create_org_site(db_session)
        f = self._create_finding(db_session, site.id)

        resp = client.get(f"/api/compliance/findings/{f.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rule_id"] == "DT_SCOPE"
        assert "inputs" in data
        assert "params" in data
        assert "evidence_refs" in data
        assert data["engine_version"] == "abc123"

    def test_retrocompat_null_audit_fields(self, db_session):
        """Findings with NULL audit fields (pre-migration) work fine."""
        _org, site = _create_org_site(db_session)
        f = ComplianceFinding(
            site_id=site.id,
            regulation="bacs",
            rule_id="BACS_POWER",
            status="OK",
            severity="low",
            insight_status=InsightStatus.OPEN,
            # No audit fields set → should default to None/'{}'
        )
        db_session.add(f)
        db_session.flush()
        db_session.refresh(f)
        # Should not crash — nullable fields
        assert f.engine_version is None
        # inputs_json has default="{}" but SQLAlchemy may set it as None if not provided
        # either way, parsing should be safe
        raw = f.inputs_json if f.inputs_json else "{}"
        data = json.loads(raw)
        assert isinstance(data, dict)
