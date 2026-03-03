"""
test_contracts_v96.py — V96 Contract enrichment tests
"""
import pytest
from models import ContractIndexation, ContractStatus
from models.billing_models import EnergyContract


class TestContractV96Fields:
    """Verify EnergyContract V96 columns and serialization."""

    def test_offer_indexation_column(self):
        assert hasattr(EnergyContract, 'offer_indexation')

    def test_price_granularity_column(self):
        assert hasattr(EnergyContract, 'price_granularity')

    def test_renewal_alert_days_column(self):
        assert hasattr(EnergyContract, 'renewal_alert_days')

    def test_contract_status_column(self):
        assert hasattr(EnergyContract, 'contract_status')

    def test_contract_indexation_enum(self):
        assert ContractIndexation('fixe') == ContractIndexation.FIXE
        assert ContractIndexation('spot') == ContractIndexation.SPOT

    def test_contract_status_enum(self):
        assert ContractStatus('active') == ContractStatus.ACTIVE
        assert ContractStatus('expiring') == ContractStatus.EXPIRING

    def test_invalid_indexation_raises(self):
        with pytest.raises(ValueError):
            ContractIndexation('invalid')

    def test_serialize_contract_has_v96_fields(self):
        """_serialize_contract should include V96 fields."""
        import inspect
        from routes.patrimoine import _serialize_contract
        source = inspect.getsource(_serialize_contract)
        assert 'offer_indexation' in source
        assert 'contract_status' in source
        assert 'price_granularity' in source
        assert 'renewal_alert_days' in source

    def test_contract_create_schema_has_v96(self):
        """ContractCreateRequest should have V96 fields."""
        from routes.patrimoine import ContractCreateRequest
        fields = ContractCreateRequest.model_fields
        assert 'offer_indexation' in fields
        assert 'contract_status' in fields
        assert 'price_granularity' in fields
        assert 'renewal_alert_days' in fields

    def test_contract_update_schema_has_v96(self):
        """ContractUpdateRequest should have V96 fields."""
        from routes.patrimoine import ContractUpdateRequest
        fields = ContractUpdateRequest.model_fields
        assert 'offer_indexation' in fields
        assert 'contract_status' in fields
