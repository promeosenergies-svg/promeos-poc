"""
test_compliance_contracts.py — Contrats de cohérence inter-composants.

Ces tests détectent les drifts entre :
- reconciliation_service (CHECK_TRANSLATION / _CHECK_PRIORITY)
- compliance_score_service (FRAMEWORK_WEIGHTS)
- patrimoine.py (_worst_compliance_status)
- regops rules (CEE P6 ≠ réglementation)

Chaque test doit rester vert quand on modifie un composant et oublie de mettre à jour l'autre.
"""

import pytest
from models import StatutConformite


# ─────────────────────────────────────────────────────────────
# A. reconciliation_service : CHECK_TRANSLATION ↔ _CHECK_PRIORITY
# ─────────────────────────────────────────────────────────────


class TestReconciliationConsistency:
    """Vérifie que _CHECK_PRIORITY est toujours en phase avec CHECK_TRANSLATION."""

    def test_all_translation_keys_in_priority(self):
        from services.reconciliation_service import CHECK_TRANSLATION, _CHECK_PRIORITY

        for check_id in CHECK_TRANSLATION:
            assert check_id in _CHECK_PRIORITY, (
                f"'{check_id}' présent dans CHECK_TRANSLATION mais absent de _CHECK_PRIORITY — "
                "ajouter l'entrée dans _CHECK_PRIORITY avec l'ordre correct."
            )

    def test_no_unknown_key_in_priority(self):
        from services.reconciliation_service import CHECK_TRANSLATION, _CHECK_PRIORITY

        for check_id in _CHECK_PRIORITY:
            assert check_id in CHECK_TRANSLATION, (
                f"'{check_id}' présent dans _CHECK_PRIORITY mais absent de CHECK_TRANSLATION — "
                "ajouter la traduction ou retirer l'entrée de _CHECK_PRIORITY."
            )

    def test_priority_and_translation_same_length(self):
        from services.reconciliation_service import CHECK_TRANSLATION, _CHECK_PRIORITY

        assert len(_CHECK_PRIORITY) == len(CHECK_TRANSLATION), (
            f"Taille diverge : _CHECK_PRIORITY={len(_CHECK_PRIORITY)}, CHECK_TRANSLATION={len(CHECK_TRANSLATION)}."
        )


# ─────────────────────────────────────────────────────────────
# B. compliance_score_service : poids DT + BACS + APER = 100%
# ─────────────────────────────────────────────────────────────


class TestFrameworkWeights:
    """Vérifie que les poids des frameworks sont cohérents."""

    def test_weights_sum_to_one(self):
        from services.compliance_score_service import FRAMEWORK_WEIGHTS

        total = sum(FRAMEWORK_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, (
            f"FRAMEWORK_WEIGHTS ne somment pas à 1.0 (total={total:.3f}). "
            "Vérifier regs.yaml > scoring > framework_weights."
        )

    def test_cee_not_in_framework_weights(self):
        from services.compliance_score_service import FRAMEWORK_WEIGHTS

        for key in FRAMEWORK_WEIGHTS:
            assert "cee" not in key.lower(), (
                f"'{key}' dans FRAMEWORK_WEIGHTS — le CEE est un dispositif de financement, "
                "pas une réglementation. Retirer du calcul de score."
            )

    def test_expected_frameworks_present(self):
        from services.compliance_score_service import FRAMEWORK_WEIGHTS

        expected = {"tertiaire_operat", "bacs", "aper"}
        assert set(FRAMEWORK_WEIGHTS.keys()) == expected, (
            f"Frameworks attendus : {expected}, trouvés : {set(FRAMEWORK_WEIGHTS.keys())}. "
            "Mettre à jour evidence.fixtures.js si le périmètre change."
        )


# ─────────────────────────────────────────────────────────────
# C. patrimoine : _worst_compliance_status
# ─────────────────────────────────────────────────────────────


class TestWorstComplianceStatus:
    """Vérifie que le statut global reflète le pire des frameworks."""

    @pytest.fixture
    def worst(self):
        from routes.patrimoine import _worst_compliance_status

        return _worst_compliance_status

    def test_non_conforme_wins_over_conforme(self, worst):
        result = worst(StatutConformite.NON_CONFORME, StatutConformite.CONFORME)
        assert result == StatutConformite.NON_CONFORME

    def test_non_conforme_wins_over_a_risque(self, worst):
        result = worst(StatutConformite.NON_CONFORME, StatutConformite.A_RISQUE)
        assert result == StatutConformite.NON_CONFORME

    def test_a_risque_wins_over_conforme(self, worst):
        result = worst(StatutConformite.A_RISQUE, StatutConformite.CONFORME)
        assert result == StatutConformite.A_RISQUE

    def test_all_conformes_returns_conforme(self, worst):
        result = worst(StatutConformite.CONFORME, StatutConformite.CONFORME)
        assert result == StatutConformite.CONFORME

    def test_none_values_ignored(self, worst):
        result = worst(None, StatutConformite.CONFORME, None)
        assert result == StatutConformite.CONFORME

    def test_all_none_returns_none(self, worst):
        result = worst(None, None)
        assert result is None

    def test_bacs_non_conforme_makes_site_non_conforme(self, worst):
        """Cas réel Paris : DT conforme, BACS non conforme → site non conforme."""
        result = worst(StatutConformite.CONFORME, StatutConformite.NON_CONFORME)
        assert result == StatutConformite.NON_CONFORME


# ─────────────────────────────────────────────────────────────
# D. regops/cee_p6 : hints seulement, pas de réglementation
# ─────────────────────────────────────────────────────────────


class TestCeeP6IsNotRegulation:
    """Vérifie que CEE P6 ne produit que des hints, jamais des findings réglementaires bloquants."""

    def test_cee_findings_have_no_blocking_severity(self):
        from regops.rules.cee_p6 import evaluate
        from tests.test_regops_rules import make_site, make_batiment

        site = make_site(surface_m2=6000)
        batiments = [make_batiment(cvc_power_kw=200.0, surface_m2=6000)]
        evidences = []
        config = {"enabled": True}

        findings = evaluate(site, batiments, evidences, config)
        for f in findings:
            severity = getattr(f, "severity", "")
            assert severity.upper() not in ("CRITICAL", "BLOCKING"), (
                f"CEE P6 finding avec severity '{severity}' — "
                "CEE est un dispositif de financement, ses findings ne peuvent pas être bloquants."
            )

    def test_cee_findings_are_incentive_category(self):
        from regops.rules.cee_p6 import evaluate
        from tests.test_regops_rules import make_site, make_batiment

        site = make_site(surface_m2=6000)
        batiments = [make_batiment(cvc_power_kw=200.0, surface_m2=6000)]
        findings = evaluate(site, batiments, [], {})
        for f in findings:
            category = getattr(f, "category", None)
            assert category == "incentive", (
                f"CEE P6 finding category='{category}' au lieu de 'incentive'. "
                "Le CEE est un dispositif financier, pas une obligation réglementaire."
            )
