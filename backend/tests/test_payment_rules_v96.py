"""
test_payment_rules_v96.py — V96 Payment Rules model + hierarchy tests
"""

import pytest
from models import PaymentRule, PaymentRuleLevel, ContractIndexation, ContractStatus, ReconciliationStatus


class TestV96Enums:
    """Verify V96 enums exist and have correct values."""

    def test_payment_rule_level_values(self):
        assert PaymentRuleLevel.PORTEFEUILLE.value == "portefeuille"
        assert PaymentRuleLevel.SITE.value == "site"
        assert PaymentRuleLevel.CONTRAT.value == "contrat"

    def test_contract_indexation_values(self):
        assert ContractIndexation.FIXE.value == "fixe"
        assert ContractIndexation.INDEXE.value == "indexe"
        assert ContractIndexation.SPOT.value == "spot"
        assert ContractIndexation.HYBRIDE.value == "hybride"

    def test_contract_status_values(self):
        assert ContractStatus.ACTIVE.value == "active"
        assert ContractStatus.EXPIRING.value == "expiring"
        assert ContractStatus.EXPIRED.value == "expired"

    def test_reconciliation_status_values(self):
        assert ReconciliationStatus.OK.value == "ok"
        assert ReconciliationStatus.WARN.value == "warn"
        assert ReconciliationStatus.FAIL.value == "fail"


class TestPaymentRuleModel:
    """Verify PaymentRule model structure."""

    def test_tablename(self):
        assert PaymentRule.__tablename__ == "payment_rules"

    def test_has_level_column(self):
        assert hasattr(PaymentRule, "level")

    def test_has_portefeuille_id(self):
        assert hasattr(PaymentRule, "portefeuille_id")

    def test_has_site_id(self):
        assert hasattr(PaymentRule, "site_id")

    def test_has_contract_id(self):
        assert hasattr(PaymentRule, "contract_id")

    def test_has_invoice_entity_id(self):
        assert hasattr(PaymentRule, "invoice_entity_id")

    def test_has_payer_entity_id(self):
        assert hasattr(PaymentRule, "payer_entity_id")

    def test_has_cost_center(self):
        assert hasattr(PaymentRule, "cost_center")


class TestEnergyContractV96Columns:
    """Verify V96 columns added to EnergyContract."""

    def test_offer_indexation(self):
        from models.billing_models import EnergyContract

        assert hasattr(EnergyContract, "offer_indexation")

    def test_price_granularity(self):
        from models.billing_models import EnergyContract

        assert hasattr(EnergyContract, "price_granularity")

    def test_renewal_alert_days(self):
        from models.billing_models import EnergyContract

        assert hasattr(EnergyContract, "renewal_alert_days")

    def test_contract_status(self):
        from models.billing_models import EnergyContract

        assert hasattr(EnergyContract, "contract_status")


class TestMigrationFunctions:
    """Verify migration functions exist."""

    def test_create_payment_rules_table_exists(self):
        from database.migrations import _create_payment_rules_table

        assert callable(_create_payment_rules_table)

    def test_add_contract_v96_columns_exists(self):
        from database.migrations import _add_contract_v96_columns

        assert callable(_add_contract_v96_columns)

    def test_run_migrations_calls_v96(self):
        import inspect
        from database.migrations import run_migrations

        source = inspect.getsource(run_migrations)
        assert "_create_payment_rules_table" in source
        assert "_add_contract_v96_columns" in source
