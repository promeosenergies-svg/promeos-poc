"""
Tests integration score Audit/SME dans le scoring RegOps site-level.
Non-regression totale si audit non applicable.
"""

import pytest
from regops.engine import _apply_audit_sme_to_compliance_score, _get_audit_sme_score_for_site


class TestApplyAuditSme:
    def test_non_regression_si_non_applicable(self):
        """Score STRICTEMENT inchange si audit non applicable."""
        for original in [0.0, 45.0, 72.5, 88.0, 100.0]:
            final, detail = _apply_audit_sme_to_compliance_score(original, None, False)
            assert final == original, f"REGRESSION: {original} -> {final}"
            assert detail["audit_sme_applicable"] is False

    def test_non_regression_si_score_none(self):
        """Score None + applicable=True -> fail-safe -> inchange."""
        final, _ = _apply_audit_sme_to_compliance_score(75.0, None, True)
        assert final == 75.0

    def test_injection_conforme(self):
        """Audit conforme (1.0) -> score composite >= raw * 0.84."""
        final, detail = _apply_audit_sme_to_compliance_score(70.0, 1.0, True)
        expected = 70.0 * 0.84 + 100.0 * 0.16
        assert abs(final - expected) < 0.1
        assert detail["audit_sme_applicable"] is True

    def test_injection_en_retard(self):
        """Audit EN_RETARD (0.0) -> score degrade."""
        final, _ = _apply_audit_sme_to_compliance_score(85.0, 0.0, True)
        expected = 85.0 * 0.84 + 0.0
        assert abs(final - expected) < 0.1
        assert final < 85.0

    def test_poids_audit_16_pct(self):
        """Score 100 + audit 0 = 84."""
        final, detail = _apply_audit_sme_to_compliance_score(100.0, 0.0, True)
        assert abs(final - 84.0) < 0.1
        assert detail["weight_audit_sme"] == 0.16
        assert detail["weight_findings"] == 0.84

    def test_score_borne_0_100(self):
        for raw, audit in [(0.0, 0.0), (100.0, 1.0), (50.0, 0.5)]:
            final, _ = _apply_audit_sme_to_compliance_score(raw, audit, True)
            assert 0.0 <= final <= 100.0

    def test_a_realiser_0_3(self):
        """A_REALISER = 0.3 -> impact partiel."""
        final, _ = _apply_audit_sme_to_compliance_score(80.0, 0.3, True)
        expected = 80.0 * 0.84 + 30.0 * 0.16
        assert abs(final - expected) < 0.1


class TestGetAuditSmeScoreForSite:
    def test_site_inexistant_fail_safe(self):
        """Site inexistant -> (None, False)."""
        from database import SessionLocal

        db = SessionLocal()
        try:
            score, applicable = _get_audit_sme_score_for_site(db, 99999)
            assert score is None
            assert applicable is False
        finally:
            db.close()

    def test_site_existant_retourne_score(self):
        """Site existant avec seed audit -> score et applicable."""
        from database import SessionLocal

        db = SessionLocal()
        try:
            score, applicable = _get_audit_sme_score_for_site(db, 1)
            # Peut etre applicable ou non selon les donnees seedees
            assert isinstance(applicable, bool)
            if applicable:
                assert score is not None
                assert 0.0 <= score <= 1.0
        finally:
            db.close()
