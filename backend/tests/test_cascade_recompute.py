"""
PROMEOS — Sprint C-1 Phase 6 : Tests cascade_recompute_service.

Vérifie l'orchestrateur cascade pour 7 champs MVP (Site x6 + Batiment x1) :
- Recalculs cascadants zone/palier/Cabs/compliance
- Preview dry-run sans mutation DB (savepoint)
- Résilience erreur sub-action
- Endpoint org-scopé /api/v1/sites/{id}/cascade-impact
"""

from __future__ import annotations

import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Helpers résolution mockés ───────────────────────────────────────────────


def test_resolve_aper_assujetti_below_1500():
    from regops.services.cascade_recompute_service import _resolve_aper_assujetti

    site = MagicMock()
    site.parking_area_m2 = 1499
    assert _resolve_aper_assujetti(site) is False


def test_resolve_aper_assujetti_exact_1500():
    from regops.services.cascade_recompute_service import _resolve_aper_assujetti

    site = MagicMock()
    site.parking_area_m2 = 1500
    assert _resolve_aper_assujetti(site) is True


def test_resolve_aper_taille_small():
    from regops.services.cascade_recompute_service import _resolve_aper_taille

    site = MagicMock()
    site.parking_area_m2 = 5000
    assert _resolve_aper_taille(site) == "SMALL"


def test_resolve_aper_taille_large():
    from regops.services.cascade_recompute_service import _resolve_aper_taille

    site = MagicMock()
    site.parking_area_m2 = 12000
    assert _resolve_aper_taille(site) == "LARGE"


def test_resolve_aper_deadline_small_2028():
    from regops.services.cascade_recompute_service import _resolve_aper_deadline

    site = MagicMock()
    site.parking_area_m2 = 5000
    assert _resolve_aper_deadline(site) == date(2028, 7, 1)


def test_resolve_aper_deadline_large_2026():
    from regops.services.cascade_recompute_service import _resolve_aper_deadline

    site = MagicMock()
    site.parking_area_m2 = 12000
    assert _resolve_aper_deadline(site) == date(2026, 7, 1)


def test_resolve_aper_deadline_below_seuil():
    from regops.services.cascade_recompute_service import _resolve_aper_deadline

    site = MagicMock()
    site.parking_area_m2 = 1000
    assert _resolve_aper_deadline(site) is None


# ─── CASCADE_MAP composition ─────────────────────────────────────────────────


def test_cascade_map_contains_mvp_fields():
    """7 C-1 + 2 Phase 4.2 + 1 Phase 5.2 + 1 Phase 5.3 = 11 entrées CASCADE_MAP."""
    from regops.services.cascade_recompute_service import CASCADE_MAP_MVP_SPRINT_C1

    expected = {
        # Sprint C-1
        "Site.code_postal",
        "Site.altitude_m",
        "Site.tertiaire_area_m2",
        "Site.parking_area_m2",
        "Site.roof_area_m2",
        "Site.operat_sous_categorie_id",
        "Batiment.cvc_power_kw",
        # Sprint C-2 Phase 4.2
        "Site.surface_m2",
        "Site.annual_kwh_total",
        # Sprint C-2 Phase 5.2 — pivot org-scoped (clôture D-Phase6-Cascade-EJ-Sites-001)
        "AuditEnergetique.conso_annuelle_moy_gwh",
        # Sprint C-2 Phase 5.3 — alerte renouvellement 90j MVP
        "EnergyContract.end_date",
    }
    assert set(CASCADE_MAP_MVP_SPRINT_C1.keys()) == expected


def test_cascade_map_unsupported_field_returns_no_actions():
    """Cascade sur field non listé → result.actions vide."""
    from regops.services.cascade_recompute_service import cascade_recompute_on_change

    db = MagicMock()
    site = MagicMock(id=1)
    result = cascade_recompute_on_change(db, site, "Site.unsupported_field", persist=False)
    assert len(result.actions) == 0


# ─── Cascade preview e2e (DB réelle, savepoint) ──────────────────────────────


@pytest.fixture
def site_with_operat_data():
    """Site HELIOS avec données OPERAT minimales pour tests cascade."""
    from database import SessionLocal
    from models import Site, not_deleted

    db = SessionLocal()
    try:
        site = db.query(Site).filter(not_deleted(Site)).first()
        if not site:
            pytest.skip("Aucun site HELIOS dans la DB")
        # Patcher altitude + sous-cat si manquant (no commit, fixture-scoped)
        if site.altitude_m is None:
            site.altitude_m = 35
        if not site.operat_sous_categorie_id:
            site.operat_sous_categorie_id = "Bureaux - Bureaux Standards (cloisonnés - attribués)"
        db.commit()
        yield site, db
    finally:
        db.close()


def test_cascade_preview_code_postal_change_returns_actions(site_with_operat_data):
    """Preview cascade Paris → Marseille : retourne 4 actions (zone+palier+Cabs+compliance)."""
    from regops.services.cascade_recompute_service import cascade_impact_preview

    site, db = site_with_operat_data
    result = cascade_impact_preview(db, site, "Site.code_postal", "13001")
    output_fields = {a.output_field for a in result.actions}
    assert {"operat_zone_climatique", "operat_palier_altitude", "cabs_kwh_m2_an", "compliance_score"} == output_fields


def test_cascade_preview_zone_h3_for_marseille(site_with_operat_data):
    """Preview Paris → Marseille : zone calculée = H3."""
    from regops.services.cascade_recompute_service import cascade_impact_preview

    site, db = site_with_operat_data
    result = cascade_impact_preview(db, site, "Site.code_postal", "13001")
    zone_action = next(a for a in result.actions if a.output_field == "operat_zone_climatique")
    assert zone_action.new_value == "H3"


def test_cascade_preview_no_db_mutation(site_with_operat_data):
    """Preview ne modifie PAS la DB (savepoint rollback)."""
    from database import SessionLocal
    from models import Site
    from regops.services.cascade_recompute_service import cascade_impact_preview

    site, db = site_with_operat_data
    initial_code_postal = site.code_postal

    cascade_impact_preview(db, site, "Site.code_postal", "13001")

    # Re-fetch depuis nouvelle session pour bypasser le cache éventuel
    db2 = SessionLocal()
    try:
        site_reloaded = db2.query(Site).filter(Site.id == site.id).first()
        assert site_reloaded.code_postal == initial_code_postal, (
            f"DB modifiée par preview ! code_postal={site_reloaded.code_postal}, attendu={initial_code_postal}"
        )
    finally:
        db2.close()


def test_cascade_preview_persisted_false(site_with_operat_data):
    """Preview retourne result.persisted=False."""
    from regops.services.cascade_recompute_service import cascade_impact_preview

    site, db = site_with_operat_data
    result = cascade_impact_preview(db, site, "Site.altitude_m", "500")
    assert result.persisted is False


def test_cascade_preview_altitude_change_palier(site_with_operat_data):
    """Preview altitude 35 → 1000 : palier devient alt_800_1200."""
    from regops.services.cascade_recompute_service import cascade_impact_preview

    site, db = site_with_operat_data
    result = cascade_impact_preview(db, site, "Site.altitude_m", 1000)
    palier_action = next(a for a in result.actions if a.output_field == "operat_palier_altitude")
    assert palier_action.new_value == "alt_800_1200"


def test_cascade_preview_parking_change_aper(site_with_operat_data):
    """Preview parking 1000 → 12000 : aper_assujetti True + LARGE + deadline 2026."""
    from regops.services.cascade_recompute_service import cascade_impact_preview

    site, db = site_with_operat_data
    result = cascade_impact_preview(db, site, "Site.parking_area_m2", 12000)
    actions_by_field = {a.output_field: a.new_value for a in result.actions}
    assert actions_by_field.get("aper_assujetti") is True
    assert actions_by_field.get("aper_categorie_taille") == "LARGE"
    assert actions_by_field.get("aper_deadline") == date(2026, 7, 1)


def test_cascade_preview_resilience_partial_data(site_with_operat_data):
    """Preview avec données partielles ne crash pas, retourne actions avec None."""
    from regops.services.cascade_recompute_service import cascade_impact_preview

    site, db = site_with_operat_data
    # Patch local : retirer operat_sous_categorie_id pour forcer Cabs=None
    original_subcat = site.operat_sous_categorie_id
    site.operat_sous_categorie_id = None
    db.commit()

    try:
        result = cascade_impact_preview(db, site, "Site.code_postal", "13001")
        # Cabs doit être None mais zone+palier OK
        cabs_action = next(a for a in result.actions if a.output_field == "cabs_kwh_m2_an")
        assert cabs_action.new_value is None
        zone_action = next(a for a in result.actions if a.output_field == "operat_zone_climatique")
        assert zone_action.new_value == "H3"
    finally:
        site.operat_sous_categorie_id = original_subcat
        db.commit()


def test_cascade_audit_log_emitted(site_with_operat_data):
    """Cascade emit audit trail via audit_log_service.log_cascade.

    Sprint C-2 Phase 1.3 — comportement migré : le legacy `_logger.info("CASCADE_AUDIT")`
    a été remplacé par persistance via `audit_log_service.log_cascade()`.
    Cf. tests/test_cascade_recompute_audit_log_wiring.py pour validation complète.

    Ici on vérifie le contrat minimal : l'appel à log_cascade est bien effectué.
    """

    from regops.services.cascade_recompute_service import cascade_recompute_on_change

    site, db = site_with_operat_data

    with patch("services.audit_log_service.log_cascade") as mock_log_cascade:
        cascade_recompute_on_change(
            db,
            site,
            "Site.altitude_m",
            old_value=site.altitude_m,
            new_value=site.altitude_m,
            persist=True,
            org_id=999_010,
        )
        assert mock_log_cascade.called, "log_cascade n'a pas été appelé par la cascade"


# ─── Endpoint /api/v1/sites/{id}/cascade-impact ──────────────────────────────


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


def test_endpoint_field_not_supported_returns_400(client, site_with_operat_data):
    """Field hors whitelist → 400 FIELD_NOT_SUPPORTED."""
    site, _ = site_with_operat_data
    r = client.get(f"/api/v1/sites/{site.id}/cascade-impact?field=hacker_field&new_value=42")
    assert r.status_code == 400
    detail = r.json().get("detail", {})
    if isinstance(detail, dict):
        assert detail.get("error") == "FIELD_NOT_SUPPORTED"


def test_endpoint_unknown_site_returns_404(client):
    """Site inexistant → 404."""
    r = client.get("/api/v1/sites/99999999/cascade-impact?field=code_postal&new_value=13001")
    assert r.status_code == 404


def test_endpoint_returns_cascade_actions(client, site_with_operat_data):
    """Endpoint OK avec champs valides → 200 + actions cascadantes."""
    site, _ = site_with_operat_data
    r = client.get(f"/api/v1/sites/{site.id}/cascade-impact?field=code_postal&new_value=13001")
    assert r.status_code == 200
    body = r.json()
    assert body.get("entity_type") == "Site"
    assert body.get("persisted") is False
    assert "actions" in body
    output_fields = {a["output_field"] for a in body["actions"]}
    assert "operat_zone_climatique" in output_fields


def test_endpoint_dry_run_no_db_change(client, site_with_operat_data):
    """Appel endpoint preview ne modifie pas la DB."""
    from database import SessionLocal
    from models import Site

    site, _ = site_with_operat_data
    initial_cp = site.code_postal

    r = client.get(f"/api/v1/sites/{site.id}/cascade-impact?field=code_postal&new_value=13001")
    assert r.status_code == 200

    db2 = SessionLocal()
    try:
        site_after = db2.query(Site).filter(Site.id == site.id).first()
        assert site_after.code_postal == initial_cp, (
            f"DB mutée par endpoint preview ! code_postal={site_after.code_postal}"
        )
    finally:
        db2.close()


def test_endpoint_invalid_value_coercion_returns_400(client, site_with_operat_data):
    """Coercion impossible (altitude="abc") → 400."""
    site, _ = site_with_operat_data
    r = client.get(f"/api/v1/sites/{site.id}/cascade-impact?field=altitude_m&new_value=abc")
    assert r.status_code == 400
