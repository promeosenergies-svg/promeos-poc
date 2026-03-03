"""
test_contract_radar_v99.py — V99 Contract Renewal Radar tests
Tests: radar service, purchase scenarios service, endpoints.
"""
import pytest
import inspect
from datetime import date, timedelta

from services.contract_radar_service import (
    compute_contract_radar,
    _compute_urgency,
    _compute_status,
    _sort_key,
    INDEXATION_LABELS,
)
from services.purchase_scenarios_service import (
    compute_purchase_scenarios,
    SCENARIO_TEMPLATES,
    _estimate_annual_volume,
)


# ── A. Urgency mapping ────────────────────────────────────────────────

class TestComputeUrgency:
    """V99: urgency color logic."""

    def test_expired_is_red(self):
        assert _compute_urgency(-5, -95) == "red"

    def test_past_notice_is_red(self):
        assert _compute_urgency(30, -10) == "red"

    def test_notice_within_30_is_orange(self):
        assert _compute_urgency(60, 20) == "orange"

    def test_notice_within_60_is_yellow(self):
        assert _compute_urgency(100, 45) == "yellow"

    def test_end_within_90_is_green(self):
        assert _compute_urgency(80, 70) == "green"

    def test_far_future_is_gray(self):
        assert _compute_urgency(200, 150) == "gray"

    def test_none_days_to_end_is_gray(self):
        assert _compute_urgency(None, None) == "gray"


# ── B. Contract status logic ──────────────────────────────────────────

class TestComputeStatus:
    """V99: status from end_date."""
    today = date.today()

    def test_none_end_date_is_active(self):
        assert _compute_status(None, self.today) == "active"

    def test_past_date_is_expired(self):
        assert _compute_status(self.today - timedelta(days=5), self.today) == "expired"

    def test_within_90_is_expiring(self):
        assert _compute_status(self.today + timedelta(days=30), self.today) == "expiring"

    def test_far_future_is_active(self):
        assert _compute_status(self.today + timedelta(days=200), self.today) == "active"


# ── C. Sort key logic ────────────────────────────────────────────────

class TestSortKey:
    """V99: expired → expiring → active ordering."""

    def test_expired_before_expiring(self):
        expired = {"contract_status": "expired", "days_to_end": -5}
        expiring = {"contract_status": "expiring", "days_to_end": 30}
        assert _sort_key(expired) < _sort_key(expiring)

    def test_expiring_before_active(self):
        expiring = {"contract_status": "expiring", "days_to_end": 30}
        active = {"contract_status": "active", "days_to_end": 200}
        assert _sort_key(expiring) < _sort_key(active)

    def test_none_days_sorts_last(self):
        with_days = {"contract_status": "active", "days_to_end": 100}
        no_days = {"contract_status": "active", "days_to_end": None}
        assert _sort_key(with_days) < _sort_key(no_days)


# ── D. Indexation labels ──────────────────────────────────────────────

class TestIndexationLabels:
    """V99: indexation label lookup."""

    def test_fixe(self):
        assert INDEXATION_LABELS["fixe"] == "Prix fixe"

    def test_indexe(self):
        assert INDEXATION_LABELS["indexe"] == "Indexé marché"

    def test_spot(self):
        assert INDEXATION_LABELS["spot"] == "Spot"

    def test_hybride(self):
        assert INDEXATION_LABELS["hybride"] == "Hybride"


# ── E. Scenario templates ────────────────────────────────────────────

class TestScenarioTemplates:
    """V99: scenario template constants."""

    def test_has_three_scenarios(self):
        assert set(SCENARIO_TEMPLATES.keys()) == {"A", "B", "C"}

    def test_each_has_required_fields(self):
        required = {"label", "description", "risk_level", "avantages", "inconvenients", "action_templates", "price_factor"}
        for sid, tpl in SCENARIO_TEMPLATES.items():
            for field in required:
                assert field in tpl, f"Scenario {sid} missing {field}"

    def test_risk_levels(self):
        assert SCENARIO_TEMPLATES["A"]["risk_level"] == "faible"
        assert SCENARIO_TEMPLATES["B"]["risk_level"] == "modéré"
        assert SCENARIO_TEMPLATES["C"]["risk_level"] == "élevé"

    def test_price_factors_order(self):
        """A > B > C in price factor (fixe costs more)."""
        assert SCENARIO_TEMPLATES["A"]["price_factor"] > SCENARIO_TEMPLATES["B"]["price_factor"]
        assert SCENARIO_TEMPLATES["B"]["price_factor"] > SCENARIO_TEMPLATES["C"]["price_factor"]

    def test_action_templates_are_lists(self):
        for sid, tpl in SCENARIO_TEMPLATES.items():
            assert isinstance(tpl["action_templates"], list)
            assert len(tpl["action_templates"]) >= 3, f"Scenario {sid} should have 3+ action templates"


# ── F. compute_contract_radar signature ───────────────────────────────

class TestRadarServiceSignature:
    """V99: radar service interface."""

    def test_compute_contract_radar_params(self):
        sig = inspect.signature(compute_contract_radar)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "org_id" in params
        assert "portfolio_id" in params
        assert "horizon_days" in params

    def test_horizon_default_is_90(self):
        sig = inspect.signature(compute_contract_radar)
        assert sig.parameters["horizon_days"].default == 90


# ── G. compute_purchase_scenarios signature ───────────────────────────

class TestScenariosServiceSignature:
    """V99: scenarios service interface."""

    def test_compute_purchase_scenarios_params(self):
        sig = inspect.signature(compute_purchase_scenarios)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "contract_id" in params

    def test_estimate_annual_volume_exists(self):
        sig = inspect.signature(_estimate_annual_volume)
        params = list(sig.parameters.keys())
        assert "db" in params
        assert "site_id" in params


# ── H. Routes source guards ──────────────────────────────────────────

class TestContractRadarRoutes:
    """V99: route file has expected endpoints."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        import pathlib
        self.src = (pathlib.Path(__file__).parent.parent / "routes" / "contracts_radar.py").read_text(encoding="utf-8")

    def test_has_radar_endpoint(self):
        assert "/radar" in self.src

    def test_has_purchase_scenarios_endpoint(self):
        assert "purchase-scenarios" in self.src

    def test_has_actions_from_scenario_endpoint(self):
        assert "actions/from-scenario" in self.src

    def test_has_scenario_summary_endpoint(self):
        assert "scenario-summary" in self.src

    def test_has_scenario_action_create_schema(self):
        assert "ScenarioActionCreate" in self.src

    def test_has_idempotency_key(self):
        assert "idempotency_key" in self.src

    def test_has_action_source_purchase(self):
        assert "ActionSourceType.PURCHASE" in self.src
