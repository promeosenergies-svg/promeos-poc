"""
PROMEOS - Tests for BACS Engine v2
25+ unit tests covering Putile, obligation, TRI, inspections, and full flow.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Batiment,
    TypeSite,
    BacsAsset,
    BacsCvcSystem,
    BacsAssessment,
    BacsInspection,
    CvcSystemType,
    CvcArchitecture,
    BacsTriggerReason,
    InspectionStatus,
)
from services.bacs_engine import (
    compute_putile,
    determine_obligation,
    compute_tri,
    compute_inspection_schedule,
    evaluate_bacs,
    evaluate_legacy,
    DEADLINE_290,
    DEADLINE_70,
    RENEWAL_CUTOFF,
    ENGINE_VERSION,
)


# ── Test DB fixture ──


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_system(asset_id=1, sys_type=CvcSystemType.HEATING, arch=CvcArchitecture.CASCADE, units=None, **kw):
    """Helper to create BacsCvcSystem with defaults."""
    if units is None:
        units = [{"label": "Unit 1", "kw": 150}]
    return BacsCvcSystem(
        asset_id=asset_id,
        system_type=sys_type,
        architecture=arch,
        units_json=json.dumps(units),
        **kw,
    )


def _make_inspection(asset_id=1, **kw):
    defaults = {
        "asset_id": asset_id,
        "inspection_date": date(2022, 6, 1),
        "due_next_date": date(2027, 6, 1),
        "status": InspectionStatus.COMPLETED,
    }
    defaults.update(kw)
    return BacsInspection(**defaults)


# ════════════════════════════════════════════
# Putile tests
# ════════════════════════════════════════════


class TestPutile:
    def test_cascade_heating_sums_units(self):
        systems = [_make_system(units=[{"label": "PAC 1", "kw": 150}, {"label": "PAC 2", "kw": 100}])]
        result = compute_putile(systems)
        assert result["putile_heating_kw"] == 250
        assert result["putile_kw"] == 250

    def test_independent_heating_takes_max(self):
        systems = [
            _make_system(
                arch=CvcArchitecture.INDEPENDENT,
                units=[{"label": "PAC 1", "kw": 150}, {"label": "PAC 2", "kw": 100}],
            )
        ]
        result = compute_putile(systems)
        assert result["putile_heating_kw"] == 150
        assert result["putile_kw"] == 150

    def test_network_cooling_sums(self):
        systems = [
            _make_system(
                sys_type=CvcSystemType.COOLING,
                arch=CvcArchitecture.NETWORK,
                units=[{"label": "Chiller 1", "kw": 80}, {"label": "Chiller 2", "kw": 60}],
            )
        ]
        result = compute_putile(systems)
        assert result["putile_cooling_kw"] == 140
        assert result["putile_kw"] == 140

    def test_mixed_heating_cooling_takes_max_channel(self):
        systems = [
            _make_system(
                sys_type=CvcSystemType.HEATING,
                arch=CvcArchitecture.CASCADE,
                units=[{"label": "Chaud", "kw": 200}],
            ),
            _make_system(
                sys_type=CvcSystemType.COOLING,
                arch=CvcArchitecture.CASCADE,
                units=[{"label": "Froid", "kw": 350}],
            ),
        ]
        result = compute_putile(systems)
        assert result["putile_heating_kw"] == 200
        assert result["putile_cooling_kw"] == 350
        assert result["putile_kw"] == 350

    def test_ventilation_ignored(self):
        systems = [
            _make_system(sys_type=CvcSystemType.VENTILATION, units=[{"kw": 500}]),
            _make_system(sys_type=CvcSystemType.HEATING, units=[{"kw": 100}]),
        ]
        result = compute_putile(systems)
        assert result["putile_kw"] == 100

    def test_empty_systems_returns_zero(self):
        result = compute_putile([])
        assert result["putile_kw"] == 0

    def test_trace_includes_all_steps(self):
        systems = [_make_system(units=[{"kw": 150}])]
        result = compute_putile(systems)
        assert len(result["trace"]) >= 3
        assert "Putile final" in result["trace"][-1]

    def test_invalid_units_json_handled(self):
        sys = BacsCvcSystem(
            asset_id=1,
            system_type=CvcSystemType.HEATING,
            architecture=CvcArchitecture.CASCADE,
            units_json="not-json",
        )
        result = compute_putile([sys])
        assert result["putile_kw"] == 0


# ════════════════════════════════════════════
# Obligation tests
# ════════════════════════════════════════════


class TestObligation:
    CONFIG = {"high_kw": 290, "low_kw": 70}

    def test_above_290kw_deadline_2025(self):
        result = determine_obligation(450, None, [], self.CONFIG)
        assert result["is_obligated"] is True
        assert result["threshold"] == 290
        assert result["deadline"] == DEADLINE_290
        assert result["trigger_reason"] == BacsTriggerReason.THRESHOLD_290

    def test_70_to_290kw_deadline_2030(self):
        result = determine_obligation(150, None, [], self.CONFIG)
        assert result["is_obligated"] is True
        assert result["threshold"] == 70
        assert result["deadline"] == DEADLINE_70
        assert result["trigger_reason"] == BacsTriggerReason.THRESHOLD_70

    def test_below_70kw_out_of_scope(self):
        result = determine_obligation(50, None, [], self.CONFIG)
        assert result["is_obligated"] is False
        assert result["trigger_reason"] is None

    def test_new_construction_post_2023_immediate(self):
        pc = date(2024, 3, 1)
        result = determine_obligation(100, pc, [], self.CONFIG)
        assert result["is_obligated"] is True
        assert result["trigger_reason"] == BacsTriggerReason.NEW_CONSTRUCTION
        assert result["deadline"] == pc

    def test_renewal_post_2023_triggers(self):
        events = [{"date": "2024-06-15", "system": "heating", "kw": 200}]
        result = determine_obligation(100, None, events, self.CONFIG)
        assert result["is_obligated"] is True
        assert result["trigger_reason"] == BacsTriggerReason.RENEWAL

    def test_renewal_pre_2023_no_trigger(self):
        events = [{"date": "2022-01-01", "system": "heating", "kw": 200}]
        result = determine_obligation(50, None, events, self.CONFIG)
        assert result["is_obligated"] is False


# ════════════════════════════════════════════
# TRI tests
# ════════════════════════════════════════════


class TestTRI:
    def test_above_10_years_exemption(self):
        ctx = {"cout_bacs_eur": 100000, "aides_pct": 0, "conso_kwh": 50000, "gain_pct": 10, "prix_kwh": 0.15}
        result = compute_tri(ctx)
        # TRI = 100000 / (50000*0.10*0.15) = 100000/750 ≈ 133.33
        assert result["tri_years"] > 10
        assert result["exemption_possible"] is True

    def test_below_10_years_no_exemption(self):
        ctx = {"cout_bacs_eur": 10000, "aides_pct": 0, "conso_kwh": 500000, "gain_pct": 15, "prix_kwh": 0.20}
        result = compute_tri(ctx)
        # TRI = 10000 / (500000*0.15*0.20) = 10000/15000 ≈ 0.67
        assert result["tri_years"] < 10
        assert result["exemption_possible"] is False

    def test_with_aides_reduces_cost(self):
        ctx = {"cout_bacs_eur": 100000, "aides_pct": 50, "conso_kwh": 50000, "gain_pct": 10, "prix_kwh": 0.15}
        result = compute_tri(ctx)
        # cout_net = 50000, TRI = 50000/750 ≈ 66.67
        assert result["tri_years"] < 100000 / (50000 * 0.10 * 0.15)
        assert result["tri_years"] > 0

    def test_missing_data_returns_none(self):
        result = compute_tri({})
        assert result["tri_years"] is None
        assert result["exemption_possible"] is None

    def test_zero_prix_returns_none(self):
        ctx = {"cout_bacs_eur": 100000, "aides_pct": 0, "conso_kwh": 50000, "gain_pct": 10, "prix_kwh": 0}
        result = compute_tri(ctx)
        assert result["tri_years"] is None


# ════════════════════════════════════════════
# Inspection schedule tests
# ════════════════════════════════════════════


class TestInspectionSchedule:
    def test_first_due_matches_deadline(self):
        deadline = date(2025, 1, 1)
        result = compute_inspection_schedule(deadline, [])
        assert result["next_due"] == deadline

    def test_5_year_periodicity(self):
        deadline = date(2025, 1, 1)
        insp = _make_inspection(inspection_date=date(2023, 6, 1))
        result = compute_inspection_schedule(deadline, [insp])
        expected = date(2023, 6, 1) + timedelta(days=5 * 365)
        assert result["next_due"] == expected

    def test_overdue_detection(self):
        deadline = date(2020, 1, 1)
        result = compute_inspection_schedule(deadline, [])
        assert result["is_overdue"] is True

    def test_no_deadline_no_inspection(self):
        result = compute_inspection_schedule(None, [])
        assert result["next_due"] is None
        assert result["is_overdue"] is False


# ════════════════════════════════════════════
# Full flow tests (with DB)
# ════════════════════════════════════════════


class TestEvaluateBacs:
    def _seed_site(self, db, cvc_kw=300, arch=CvcArchitecture.CASCADE, pc_date=None):
        site = Site(id=1, nom="Test Site", type=TypeSite.BUREAU)
        db.add(site)
        db.flush()
        asset = BacsAsset(site_id=1, is_tertiary_non_residential=True, pc_date=pc_date)
        db.add(asset)
        db.flush()
        sys = BacsCvcSystem(
            asset_id=asset.id,
            system_type=CvcSystemType.HEATING,
            architecture=arch,
            units_json=json.dumps([{"label": "PAC", "kw": cvc_kw}]),
        )
        db.add(sys)
        db.flush()
        return site, asset

    def test_full_flow_persists_assessment(self, db):
        self._seed_site(db, cvc_kw=450)
        result = evaluate_bacs(db, site_id=1)
        assert result is not None
        assert result.is_obligated is True
        assert result.threshold_applied == 290
        assert result.engine_version == ENGINE_VERSION
        # Check persisted
        stored = db.query(BacsAssessment).filter(BacsAssessment.asset_id == result.asset_id).first()
        assert stored.id == result.id

    def test_recompute_replaces(self, db):
        self._seed_site(db, cvc_kw=450)
        r1 = evaluate_bacs(db, site_id=1)
        ts1 = r1.assessed_at
        r2 = evaluate_bacs(db, site_id=1)
        count = db.query(BacsAssessment).filter(BacsAssessment.asset_id == r1.asset_id).count()
        assert count == 1
        assert r2.assessed_at >= ts1

    def test_out_of_scope(self, db):
        self._seed_site(db, cvc_kw=40)
        result = evaluate_bacs(db, site_id=1)
        assert result.is_obligated is False
        findings = json.loads(result.findings_json)
        assert findings[0]["rule_id"] == "BACS_V2_OUT_OF_SCOPE"

    def test_no_asset_returns_none(self, db):
        site = Site(id=1, nom="Test", type=TypeSite.BUREAU)
        db.add(site)
        db.flush()
        assert evaluate_bacs(db, site_id=1) is None

    def test_tri_exemption_in_findings(self, db):
        self._seed_site(db, cvc_kw=150)
        tri_ctx = {"cout_bacs_eur": 200000, "aides_pct": 0, "conso_kwh": 50000, "gain_pct": 10, "prix_kwh": 0.15}
        result = evaluate_bacs(db, site_id=1, tri_context=tri_ctx)
        assert result.tri_exemption_possible is True
        findings = json.loads(result.findings_json)
        rule_ids = [f["rule_id"] for f in findings]
        assert "BACS_V2_TRI_EXEMPTION" in rule_ids


# ════════════════════════════════════════════
# EN 15232 system class tests (PRO-7)
# ════════════════════════════════════════════


class TestEN15232SystemClass:
    """Verify EN 15232 class B minimum check in BACS findings and scoring."""

    def _seed_site_with_class(self, db, system_class, cvc_kw=300):
        site = Site(id=1, nom="Test Site", type=TypeSite.BUREAU)
        db.add(site)
        db.flush()
        asset = BacsAsset(site_id=1, is_tertiary_non_residential=True)
        db.add(asset)
        db.flush()
        sys = BacsCvcSystem(
            asset_id=asset.id,
            system_type=CvcSystemType.HEATING,
            architecture=CvcArchitecture.CASCADE,
            units_json=json.dumps([{"label": "PAC", "kw": cvc_kw}]),
            system_class=system_class,
        )
        db.add(sys)
        db.flush()
        return site, asset

    def test_class_d_marked_non_compliant(self, db):
        """A site with system_class=D must be NON_COMPLIANT."""
        self._seed_site_with_class(db, "D", cvc_kw=300)
        result = evaluate_bacs(db, site_id=1)
        findings = json.loads(result.findings_json)
        rule_ids = [f["rule_id"] for f in findings]
        assert "BACS_V2_CLASS_INSUFFICIENT" in rule_ids
        class_finding = [f for f in findings if f["rule_id"] == "BACS_V2_CLASS_INSUFFICIENT"][0]
        assert class_finding["status"] == "NON_COMPLIANT"
        assert class_finding["severity"] == "HIGH"

    def test_class_c_marked_non_compliant(self, db):
        """A site with system_class=C must be NON_COMPLIANT."""
        self._seed_site_with_class(db, "C", cvc_kw=300)
        result = evaluate_bacs(db, site_id=1)
        findings = json.loads(result.findings_json)
        rule_ids = [f["rule_id"] for f in findings]
        assert "BACS_V2_CLASS_INSUFFICIENT" in rule_ids

    def test_class_b_is_compliant(self, db):
        """A site with system_class=B must NOT produce a class finding."""
        self._seed_site_with_class(db, "B", cvc_kw=300)
        result = evaluate_bacs(db, site_id=1)
        findings = json.loads(result.findings_json)
        rule_ids = [f["rule_id"] for f in findings]
        assert "BACS_V2_CLASS_INSUFFICIENT" not in rule_ids

    def test_class_a_is_compliant(self, db):
        """A site with system_class=A must NOT produce a class finding."""
        self._seed_site_with_class(db, "A", cvc_kw=300)
        result = evaluate_bacs(db, site_id=1)
        findings = json.loads(result.findings_json)
        rule_ids = [f["rule_id"] for f in findings]
        assert "BACS_V2_CLASS_INSUFFICIENT" not in rule_ids

    def test_class_null_no_finding(self, db):
        """A site with system_class=None must NOT produce a class finding (unknown)."""
        self._seed_site_with_class(db, None, cvc_kw=300)
        result = evaluate_bacs(db, site_id=1)
        findings = json.loads(result.findings_json)
        rule_ids = [f["rule_id"] for f in findings]
        assert "BACS_V2_CLASS_INSUFFICIENT" not in rule_ids

    def test_class_d_caps_compliance_score(self, db):
        """A site with system_class=D must have compliance_score capped at 20."""
        self._seed_site_with_class(db, "D", cvc_kw=300)
        result = evaluate_bacs(db, site_id=1)
        assert result.compliance_score <= 20.0


# ════════════════════════════════════════════
# Legacy wrapper test
# ════════════════════════════════════════════


class TestLegacyWrapper:
    def test_returns_finding_list(self):
        bat = Batiment(id=1, site_id=1, nom="B1", surface_m2=500, cvc_power_kw=300)
        config = {"thresholds": {"high_kw": 290, "low_kw": 70}}
        findings = evaluate_legacy(None, [bat], [], config)
        assert len(findings) >= 1
        assert findings[0].regulation == "BACS"

    def test_no_cvc_returns_unknown(self):
        bat = Batiment(id=1, site_id=1, nom="B1", surface_m2=500, cvc_power_kw=None)
        findings = evaluate_legacy(None, [bat], [], {"thresholds": {}})
        assert findings[0].rule_id == "CVC_POWER_UNKNOWN"

    def test_below_threshold_out_of_scope(self):
        bat = Batiment(id=1, site_id=1, nom="B1", surface_m2=500, cvc_power_kw=50)
        findings = evaluate_legacy(None, [bat], [], {"thresholds": {"high_kw": 290, "low_kw": 70}})
        assert findings[0].rule_id == "OUT_OF_SCOPE"


# ════════════════════════════════════════════
# Data quality specs test
# ════════════════════════════════════════════


class TestDataQualitySpecs:
    def test_bacs_generic_gate_has_cvc_power(self):
        from regops.data_quality_specs import DATA_QUALITY_SPECS

        spec = DATA_QUALITY_SPECS["bacs"]
        assert "cvc_power_kw" in spec["critical"]

    def test_bacs_optional_preserved(self):
        from regops.data_quality_specs import DATA_QUALITY_SPECS

        spec = DATA_QUALITY_SPECS["bacs"]
        assert "has_bacs_attestation" in spec["optional"]

    def test_bacs_extended_fields_documented(self):
        """Extended BACS v2 fields are documented as comments in the spec."""
        import inspect
        from regops import data_quality_specs

        source = inspect.getsource(data_quality_specs)
        assert "critical_ext" in source
        assert "important_ext" in source
