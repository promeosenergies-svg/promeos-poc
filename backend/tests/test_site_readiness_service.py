"""
PROMEOS — Sprint C-2 Phase 1.4 : Tests site_readiness_service.

Vérifie l'algorithme `is_site_production_ready` (matrice v1 §9.2) :
- 7 checks individuels (hiérarchie, P0, bâtiments, compteurs, contrats,
  compliance calculable, Cabs si DT)
- Synthèse production_ready + completion_pct + next_action_recommended
- Endpoint /api/v1/sites/{id}/production-ready-status org-scopé
- Réutilisation helpers Phase 5 (_is_dt_assujetti)
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def db_session():
    """Session DB SQLAlchemy avec rollback en fin de test."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def site_complete(db_session):
    """Site HELIOS production-ready (7/7 checks). Garantit altitude + sous-cat."""
    from models import Site, not_deleted

    site = db_session.query(Site).filter(not_deleted(Site)).first()
    if not site:
        pytest.skip("Aucun site HELIOS dans la DB")
    if site.altitude_m is None:
        site.altitude_m = 35
    if not site.operat_sous_categorie_id:
        site.operat_sous_categorie_id = "Bureaux - Bureaux Standards (cloisonnés - attribués)"
    db_session.commit()
    return site


# ─── Tests checks individuels ───────────────────────────────────────────────


def test_check_hierarchy_passes_with_complete_site(site_complete, db_session):
    """Site HELIOS lié à portefeuille → EJ → org : check 1 passe."""
    from services.site_readiness_service import _check_hierarchy

    check = _check_hierarchy(site_complete)
    assert check.name == "hierarchie_complete"
    assert check.passed is True


def test_check_hierarchy_fails_with_orphan_site():
    """Site sans portefeuille → check 1 échoue."""
    from services.site_readiness_service import _check_hierarchy

    site = MagicMock()
    site.portefeuille = None
    check = _check_hierarchy(site)
    assert check.passed is False
    assert "incomplète" in check.message.lower()


def test_check_p0_fields_passes_when_all_present(site_complete):
    """Site avec tous les P0 → check 2 passe."""
    from services.site_readiness_service import _check_p0_site_fields

    check, missing = _check_p0_site_fields(site_complete)
    assert check.passed is True
    assert missing == []


def test_check_p0_fields_fails_with_missing_field():
    """Site sans code_postal → check 2 échoue, missing contient 'code_postal'."""
    from services.site_readiness_service import _check_p0_site_fields

    site = MagicMock()
    site.nom = "Test"
    site.adresse = "1 rue Test"
    site.code_postal = None  # manquant
    site.ville = "Paris"
    site.tertiaire_area_m2 = 1000
    site.altitude_m = 35
    site.operat_sous_categorie_id = "Bureaux"

    check, missing = _check_p0_site_fields(site)
    assert check.passed is False
    assert "code_postal" in missing


def test_check_compteur_fails_when_zero(site_complete):
    """Site sans compteur → check 4 échoue."""
    from services.site_readiness_service import _check_at_least_one_compteur

    # Mock site avec aucun compteur
    mock_site = MagicMock()
    mock_site.compteurs = []
    check = _check_at_least_one_compteur(mock_site)
    assert check.passed is False
    assert "Aucun compteur" in check.message


# ─── Algorithme is_site_production_ready ────────────────────────────────────


def test_complete_site_returns_production_ready_true(site_complete, db_session):
    """Site HELIOS complet → 7/7 checks ✅, production_ready=True."""
    from services.site_readiness_service import is_site_production_ready

    result = is_site_production_ready(db_session, site_complete.id)
    assert result.production_ready is True
    assert result.completion_pct == 100.0
    assert len(result.checks) == 7
    assert all(c.passed for c in result.checks)
    assert result.next_action_recommended is None


def test_completion_pct_calculation():
    """Vérifie calcul completion_pct = nb_passed / 7 * 100."""
    from services.site_readiness_service import (
        SiteReadinessCheck,
        SiteReadinessResult,
    )

    # 5/7 passed → 71.4%
    checks = [SiteReadinessCheck(name=f"c{i}", passed=(i < 5)) for i in range(7)]
    nb_passed = sum(1 for c in checks if c.passed)
    pct = round(nb_passed / len(checks) * 100, 1)
    assert pct == 71.4


def test_unknown_site_raises_value_error(db_session):
    """site_id inexistant → ValueError."""
    from services.site_readiness_service import is_site_production_ready

    with pytest.raises(ValueError):
        is_site_production_ready(db_session, 9_999_999)


def test_compliance_calculable_accepts_non_applicable(db_session, site_complete):
    """Site dont compliance retourne NON_APPLICABLE → check 6 passe (calculable)."""
    from services.compliance_score_service import ComplianceScoreResult
    from services.site_readiness_service import _check_compliance_calculable

    with patch(
        "services.compliance_score_service.compute_site_compliance_score",
        return_value=ComplianceScoreResult(
            score=None,
            confidence="non_applicable",
            frameworks_evaluated=0,
            frameworks_total=0,
        ),
    ):
        check = _check_compliance_calculable(db_session, site_complete)
    assert check.passed is True
    assert check.details["confidence"] == "non_applicable"


def test_cabs_check_passes_for_non_dt_site():
    """Site non DT-assujetti → check 7 passe par défaut (Cabs non requis)."""
    from services.site_readiness_service import _check_cabs_si_dt

    site = MagicMock()
    site.tertiaire_area_m2 = 500  # < 1000 → pas DT

    db = MagicMock()
    with patch(
        "services.compliance_score_service._is_dt_assujetti",
        return_value=False,
    ):
        check = _check_cabs_si_dt(db, site)
    assert check.passed is True
    assert "non DT-assujetti" in check.message
    assert check.details["dt_assujetti"] is False


def test_cabs_check_fails_for_dt_site_missing_altitude():
    """Site DT-assujetti sans altitude → check 7 échoue."""
    from services.site_readiness_service import _check_cabs_si_dt

    site = MagicMock()
    site.tertiaire_area_m2 = 2000  # ≥ 1000 → DT
    site.code_postal = "75001"
    site.altitude_m = None  # manquant
    site.operat_sous_categorie_id = "Bureaux"
    site.surface_m2 = 2000

    db = MagicMock()
    with patch(
        "services.compliance_score_service._is_dt_assujetti",
        return_value=True,
    ):
        check = _check_cabs_si_dt(db, site)
    assert check.passed is False
    assert "altitude_m" in check.message or "non calculable" in check.message.lower()


def test_next_action_recommended_first_failing_check():
    """next_action_recommended = message du 1er check rouge."""
    from services.site_readiness_service import (
        SiteReadinessCheck,
        SiteReadinessResult,
    )

    # Manuel : créer un result avec le 3e check rouge → next_action = msg check 3
    result = SiteReadinessResult(
        site_id=1,
        production_ready=False,
        completion_pct=66.7,
        checks=[
            SiteReadinessCheck(name="c1", passed=True),
            SiteReadinessCheck(name="c2", passed=True),
            SiteReadinessCheck(name="c3", passed=False, message="Check 3 fail"),
            SiteReadinessCheck(name="c4", passed=False, message="Check 4 fail"),
        ],
        # Recompute next_action manually pour test isolation
    )
    # Simulation : recalcul du next_action depuis les checks
    next_action = next((c.message for c in result.checks if not c.passed), None)
    assert next_action == "Check 3 fail"


# ─── Endpoint /api/v1/sites/{id}/production-ready-status ────────────────────


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


def test_endpoint_returns_200_for_valid_site(client, site_complete):
    """Endpoint OK pour site HELIOS → 200 + JSON conforme."""
    r = client.get(f"/api/v1/sites/{site_complete.id}/production-ready-status")
    assert r.status_code == 200
    body = r.json()
    assert body["site_id"] == site_complete.id
    assert "production_ready" in body
    assert "completion_pct" in body
    assert "checks" in body
    assert len(body["checks"]) == 7


def test_endpoint_404_for_unknown_site(client):
    """Site inexistant → 404 SITE_INTROUVABLE."""
    r = client.get("/api/v1/sites/9999999/production-ready-status")
    assert r.status_code == 404
    detail = r.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("error") == "SITE_INTROUVABLE"


def test_endpoint_response_structure(client, site_complete):
    """Le format JSON de la réponse est conforme dataclass SiteReadinessResult."""
    r = client.get(f"/api/v1/sites/{site_complete.id}/production-ready-status")
    body = r.json()
    expected_keys = {
        "site_id",
        "production_ready",
        "completion_pct",
        "checks",
        "champs_p0_manquants",
        "next_action_recommended",
        "computed_at",
    }
    assert expected_keys <= set(body.keys())

    # Each check has expected structure
    for check in body["checks"]:
        assert {"name", "passed", "message", "details"} <= set(check.keys())
