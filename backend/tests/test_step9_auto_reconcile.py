"""
PROMEOS — Step 9: Auto-reconciliation compteur/facture a l'import
Verifie que auto_reconcile_after_import fonctionne correctement,
et que les 3 endpoints + reconcile-all sont branches.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── A. Source structure — billing_reconcile.py ────────────────────────────────


class TestBillingReconcileSource:
    """Tests source-guard sur billing_reconcile.py."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        path = os.path.join(os.path.dirname(__file__), "..", "services", "billing_reconcile.py")
        self.source = open(path).read()

    def test_function_exists(self):
        assert "def auto_reconcile_after_import" in self.source

    def test_calls_reconcile_metered_billed(self):
        assert "reconcile_metered_billed" in self.source

    def test_creates_billing_insight(self):
        assert "BillingInsight" in self.source

    def test_type_reconciliation_mismatch(self):
        assert '"reconciliation_mismatch"' in self.source

    def test_severity_high_threshold(self):
        # high si > 20%
        assert "20" in self.source
        assert '"high"' in self.source

    def test_severity_medium(self):
        assert '"medium"' in self.source

    def test_idempotent_check(self):
        # Verifie qu'on cherche un insight existant avant d'en creer un
        assert "existing" in self.source
        assert "already_exists" in self.source

    def test_try_except_safety(self):
        # L'import ne doit jamais echouer a cause du rapprochement
        assert "try:" in self.source
        assert "except Exception" in self.source

    def test_returns_status(self):
        assert '"status"' in self.source
        assert '"mismatch_created"' in self.source
        assert '"aligned"' in self.source
        assert '"insufficient_data"' in self.source

    def test_message_in_french(self):
        assert "Ecart de" in self.source
        assert "compteur" in self.source
        assert "facture" in self.source


# ── B. Wiring — billing routes ───────────────────────────────────────────────


class TestBillingRoutesWiring:
    """Verifie que les 3 endpoints + reconcile-all sont branches."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        path = os.path.join(os.path.dirname(__file__), "..", "routes", "billing.py")
        self.source = open(path).read()

    def test_import_auto_reconcile(self):
        assert "from services.billing_reconcile import auto_reconcile_after_import" in self.source

    def test_csv_import_calls_reconcile(self):
        # Between import-csv endpoint and its return
        csv_section = self.source.split("def import_invoices_csv")[1].split("def ")[0]
        assert "auto_reconcile_after_import" in csv_section

    def test_pdf_import_calls_reconcile(self):
        pdf_section = self.source.split("def import_invoice_pdf")[1].split("def ")[0]
        assert "auto_reconcile_after_import" in pdf_section

    def test_audit_all_calls_reconcile(self):
        audit_section = self.source.split("def audit_all_invoices")[1].split("def ")[0]
        assert "auto_reconcile_after_import" in audit_section

    def test_reconcile_all_endpoint_exists(self):
        assert "def reconcile_all_sites" in self.source
        assert '"/reconcile-all"' in self.source

    def test_reconcile_all_uses_auto_reconcile(self):
        reconcile_section = self.source.split("def reconcile_all_sites")[1].split("def ")[0]
        assert "auto_reconcile_after_import" in reconcile_section

    def test_reconcile_all_has_months_param(self):
        assert "months" in self.source.split("def reconcile_all_sites")[1].split("def ")[0]

    def test_csv_returns_reconciliation(self):
        csv_section = self.source.split("def import_invoices_csv")[1].split("def ")[0]
        assert '"reconciliation"' in csv_section

    def test_pdf_returns_reconciliation(self):
        pdf_section = self.source.split("def import_invoice_pdf")[1].split("def ")[0]
        assert '"reconciliation"' in pdf_section

    def test_audit_all_returns_reconciliation(self):
        audit_section = self.source.split("def audit_all_invoices")[1].split("def ")[0]
        assert '"reconciliation"' in audit_section


# ── C. Function importable ───────────────────────────────────────────────────


class TestFunctionImportable:
    """Verifie que la fonction est importable."""

    def test_import_auto_reconcile(self):
        from services.billing_reconcile import auto_reconcile_after_import

        assert callable(auto_reconcile_after_import)

    def test_handles_none_period(self):
        from services.billing_reconcile import auto_reconcile_after_import

        result = auto_reconcile_after_import(None, 1, None, None)
        assert result is None
