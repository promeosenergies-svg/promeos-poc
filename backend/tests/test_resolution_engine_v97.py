"""
test_resolution_engine_v97.py — V97 Resolution Engine tests
Tests fix_actions, fixer functions, audit trail, evidence pack.
"""
import pytest
import inspect
from services.reconciliation_service import (
    reconcile_site, reconcile_portfolio,
    fix_create_delivery_point, fix_extend_contract,
    fix_adjust_contract_dates, fix_align_energy_type,
    fix_create_payment_rule,
    get_fix_logs, get_evidence_pack,
    _log_fix,
)
from models import ReconciliationFixLog, ReconciliationStatus


class TestFixActionsPresent:
    """V97: Every check must have fix_actions[] key."""

    def test_reconcile_site_checks_have_fix_actions(self):
        source = inspect.getsource(reconcile_site)
        assert 'fix_actions' in source

    def test_fix_actions_for_has_delivery_points(self):
        source = inspect.getsource(reconcile_site)
        assert 'create_delivery_point' in source

    def test_fix_actions_for_has_active_contract(self):
        source = inspect.getsource(reconcile_site)
        assert 'extend_contract' in source
        assert 'create_contract' in source

    def test_fix_actions_for_period_coherence(self):
        source = inspect.getsource(reconcile_site)
        assert 'adjust_contract_dates' in source

    def test_fix_actions_for_energy_type_match(self):
        source = inspect.getsource(reconcile_site)
        assert 'align_energy_type' in source

    def test_fix_actions_for_has_payment_rule(self):
        source = inspect.getsource(reconcile_site)
        assert 'create_payment_rule' in source


class TestFixerFunctions:
    """V97: Fixer functions are callable with correct signatures."""

    def test_fix_create_delivery_point_callable(self):
        assert callable(fix_create_delivery_point)
        sig = inspect.signature(fix_create_delivery_point)
        assert 'site_id' in sig.parameters
        assert 'code' in sig.parameters

    def test_fix_extend_contract_callable(self):
        assert callable(fix_extend_contract)
        sig = inspect.signature(fix_extend_contract)
        assert 'site_id' in sig.parameters
        assert 'contract_id' in sig.parameters
        assert 'months' in sig.parameters

    def test_fix_adjust_contract_dates_callable(self):
        assert callable(fix_adjust_contract_dates)
        sig = inspect.signature(fix_adjust_contract_dates)
        assert 'site_id' in sig.parameters
        assert 'contract_id' in sig.parameters

    def test_fix_align_energy_type_callable(self):
        assert callable(fix_align_energy_type)
        sig = inspect.signature(fix_align_energy_type)
        assert 'site_id' in sig.parameters

    def test_fix_create_payment_rule_callable(self):
        assert callable(fix_create_payment_rule)
        sig = inspect.signature(fix_create_payment_rule)
        assert 'site_id' in sig.parameters
        assert 'invoice_entity_id' in sig.parameters


class TestAuditTrail:
    """V97: Audit trail model and functions."""

    def test_reconciliation_fix_log_model_exists(self):
        assert hasattr(ReconciliationFixLog, '__tablename__')
        assert ReconciliationFixLog.__tablename__ == 'reconciliation_fix_logs'

    def test_fix_log_has_site_id(self):
        assert hasattr(ReconciliationFixLog, 'site_id')

    def test_fix_log_has_check_id(self):
        assert hasattr(ReconciliationFixLog, 'check_id')

    def test_fix_log_has_action(self):
        assert hasattr(ReconciliationFixLog, 'action')

    def test_fix_log_has_status_before(self):
        assert hasattr(ReconciliationFixLog, 'status_before')

    def test_fix_log_has_status_after(self):
        assert hasattr(ReconciliationFixLog, 'status_after')

    def test_fix_log_has_detail_json(self):
        assert hasattr(ReconciliationFixLog, 'detail_json')

    def test_fix_log_has_applied_by(self):
        assert hasattr(ReconciliationFixLog, 'applied_by')

    def test_fix_log_has_applied_at(self):
        assert hasattr(ReconciliationFixLog, 'applied_at')

    def test_get_fix_logs_callable(self):
        assert callable(get_fix_logs)

    def test_log_fix_callable(self):
        assert callable(_log_fix)


class TestEvidencePack:
    """V97 Phase 4: Evidence pack generation."""

    def test_get_evidence_pack_callable(self):
        assert callable(get_evidence_pack)

    def test_get_evidence_pack_source_has_keys(self):
        source = inspect.getsource(get_evidence_pack)
        assert 'reconciliation' in source
        assert 'fix_history' in source
        assert 'summary' in source
        assert 'generated_at' in source


class TestFixEndpoints:
    """V97: Fixer endpoints exist in patrimoine routes."""

    def test_apply_reconciliation_fix_endpoint(self):
        from routes.patrimoine import apply_reconciliation_fix
        assert callable(apply_reconciliation_fix)

    def test_get_reconciliation_fix_history_endpoint(self):
        from routes.patrimoine import get_reconciliation_fix_history
        assert callable(get_reconciliation_fix_history)

    def test_get_reconciliation_evidence_endpoint(self):
        from routes.patrimoine import get_reconciliation_evidence
        assert callable(get_reconciliation_evidence)

    def test_get_reconciliation_evidence_csv_endpoint(self):
        from routes.patrimoine import get_reconciliation_evidence_csv
        assert callable(get_reconciliation_evidence_csv)

    def test_get_portfolio_evidence_csv_endpoint(self):
        from routes.patrimoine import get_portfolio_evidence_csv
        assert callable(get_portfolio_evidence_csv)


class TestReconciliationFixRequestSchema:
    """V97: ReconciliationFixRequest schema exists."""

    def test_schema_exists(self):
        from routes.patrimoine import ReconciliationFixRequest
        fields = ReconciliationFixRequest.model_fields
        assert 'action' in fields
        assert 'params' in fields


class TestMigration:
    """V97: Migration function exists."""

    def test_create_reconciliation_fix_logs_table_exists(self):
        from database.migrations import _create_reconciliation_fix_logs_table
        assert callable(_create_reconciliation_fix_logs_table)

    def test_run_migrations_calls_v97(self):
        source = inspect.getsource(__import__('database.migrations', fromlist=['run_migrations']).run_migrations)
        assert '_create_reconciliation_fix_logs_table' in source
