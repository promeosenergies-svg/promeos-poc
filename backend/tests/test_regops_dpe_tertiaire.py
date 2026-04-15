"""
PROMEOS — Tests moteur DPE Tertiaire (V115 step 3, décret 2024-1040).
"""

import os
import sys
from datetime import date, datetime, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from regops.rules import dpe_tertiaire


DEFAULT_CONFIG = {
    "scope_threshold_m2": 1000,
    "deadlines": {
        "erp_cat_1_2": "2025-01-01",
        "batiments_1000m2": "2026-01-01",
        "affichage_public": "2026-07-01",
    },
    "validite_annees": 10,
    "penalties": {
        "non_realisation": 1500,
        "non_realisation_pm": 7500,
        "non_affichage": 1500,
    },
}


def _site(**kwargs):
    return SimpleNamespace(id=1, tertiaire_area_m2=kwargs.get("tertiaire_area_m2", 2000))


def _evidence(type_name="ATTESTATION_DPE", statut="VALIDE", created_at=None):
    return SimpleNamespace(
        type=SimpleNamespace(__str__=lambda self: type_name, name=type_name),
        statut=SimpleNamespace(__str__=lambda self: statut, name=statut),
        created_at=created_at,
    )


class TestScope:
    def test_scope_unknown_surface(self):
        site = SimpleNamespace(id=1, tertiaire_area_m2=None)
        findings = dpe_tertiaire.evaluate(site, [], [], DEFAULT_CONFIG)
        assert len(findings) == 1
        assert findings[0].rule_id == "DPE_SCOPE_UNKNOWN"
        assert findings[0].status == "UNKNOWN"

    def test_out_of_scope_small_building(self):
        site = _site(tertiaire_area_m2=500)
        findings = dpe_tertiaire.evaluate(site, [], [], DEFAULT_CONFIG)
        assert len(findings) == 1
        assert findings[0].rule_id == "DPE_OUT_OF_SCOPE"
        assert findings[0].status == "OUT_OF_SCOPE"


class TestRealization:
    def test_missing_dpe_past_deadline_non_compliant(self):
        site = _site(tertiaire_area_m2=2000)
        findings = dpe_tertiaire.evaluate(site, [], [], DEFAULT_CONFIG)
        assert len(findings) == 1
        f = findings[0]
        assert f.rule_id == "DPE_REALIZATION_MISSING"
        # deadline 2026-01-01, today is 2026-04-15 per context → past deadline
        assert f.status == "NON_COMPLIANT"
        assert f.severity == "CRITICAL"
        assert f.estimated_penalty_eur == 7500.0

    def test_missing_dpe_before_deadline_at_risk(self):
        site = _site(tertiaire_area_m2=2000)
        config = {**DEFAULT_CONFIG, "deadlines": {"batiments_1000m2": "2030-01-01"}}
        findings = dpe_tertiaire.evaluate(site, [], [], config)
        f = findings[0]
        assert f.rule_id == "DPE_REALIZATION_MISSING"
        assert f.status == "AT_RISK"
        assert f.severity == "HIGH"

    def test_invalid_evidence_ignored(self):
        site = _site()
        invalid_ev = _evidence(statut="EN_ATTENTE")
        findings = dpe_tertiaire.evaluate(site, [], [invalid_ev], DEFAULT_CONFIG)
        assert findings[0].rule_id == "DPE_REALIZATION_MISSING"


class TestValidity:
    def test_valid_dpe_compliant(self):
        site = _site()
        ev = _evidence(created_at=datetime(2024, 1, 1))
        findings = dpe_tertiaire.evaluate(site, [], [ev], DEFAULT_CONFIG)
        assert len(findings) == 1
        assert findings[0].rule_id == "DPE_COMPLIANT"
        assert findings[0].status == "COMPLIANT"

    def test_expired_dpe_non_compliant(self):
        site = _site()
        ev = _evidence(created_at=datetime(2010, 1, 1))
        findings = dpe_tertiaire.evaluate(site, [], [ev], DEFAULT_CONFIG)
        assert len(findings) == 1
        assert findings[0].rule_id == "DPE_EXPIRED"
        assert findings[0].status == "NON_COMPLIANT"

    def test_most_recent_dpe_wins(self):
        site = _site()
        old = _evidence(created_at=datetime(2010, 1, 1))
        recent = _evidence(created_at=datetime(2024, 6, 1))
        findings = dpe_tertiaire.evaluate(site, [], [old, recent], DEFAULT_CONFIG)
        assert findings[0].rule_id == "DPE_COMPLIANT"
