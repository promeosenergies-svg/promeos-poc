"""
PROMEOS — Sprint C-2 Phase 3 : Tests wiring PATCH /api/patrimoine/sites/{id}
                                  → cascade_recompute_on_change(persist=True).

Vérifie que la route `update_site` :
- détecte les champs ∈ CASCADE_MAP_MVP_SPRINT_C1 et déclenche cascade_recompute
- propage correlation_id / ip / user_agent vers audit_log_service
- enrichit la réponse avec `cascade_results` (liste CascadeResult.to_dict())
- log_patrimoine_change basique pour les champs hors cascade_map
- 404/422 pour cas invalides
"""

from __future__ import annotations

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


@pytest.fixture
def site_for_patch():
    """Site HELIOS avec données OPERAT minimales pour cascade.

    Snapshot des valeurs avant le test → restaurées en teardown pour ne pas
    polluer la seed des tests suivants (cascade_recompute commit en interne).
    """
    from database import SessionLocal
    from models import Site, not_deleted

    db = SessionLocal()
    snapshot: dict = {}
    site_id: int | None = None
    try:
        site = db.query(Site).filter(not_deleted(Site)).first()
        if not site:
            pytest.skip("Aucun site HELIOS dans la DB")
        site_id = site.id

        # Patch champs minimaux pour cascade fonctionnelle
        if site.altitude_m is None:
            site.altitude_m = 35
        if not site.operat_sous_categorie_id:
            site.operat_sous_categorie_id = "Bureaux - Bureaux Standards (cloisonnés - attribués)"

        # Snapshot pour restoration
        snapshot = {
            "nom": site.nom,
            "code_postal": site.code_postal,
            "ville": site.ville,
            "tertiaire_area_m2": site.tertiaire_area_m2,
            "parking_area_m2": site.parking_area_m2,
            "roof_area_m2": site.roof_area_m2,
            "surface_m2": site.surface_m2,
        }
        db.commit()

        yield site_id, snapshot, db
    finally:
        # Restoration : recharger site depuis DB et restaurer
        if site_id is not None and snapshot:
            try:
                site = db.query(Site).filter(Site.id == site_id).first()
                if site:
                    for field, value in snapshot.items():
                        setattr(site, field, value)
                    db.commit()
            except Exception:
                db.rollback()
        db.close()


# ─── Test 1 : code_postal déclenche cascade complète ────────────────────────


def test_patch_code_postal_triggers_full_cascade(client, site_for_patch):
    """PATCH `code_postal` → cascade zone+palier+Cabs+compliance + audit log."""
    from database import SessionLocal
    from services.audit_log_service import query_audit_trail

    site_id, snapshot, _ = site_for_patch
    cid = f"test-patch-cp-{uuid.uuid4().hex[:8]}"
    new_cp = "13001" if snapshot["code_postal"] != "13001" else "75001"

    resp = client.patch(
        f"/api/patrimoine/sites/{site_id}",
        json={"code_postal": new_cp},
        headers={"X-Correlation-ID": cid},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Réponse contient cascade_results avec ≥ 1 entrée pour Site.code_postal
    assert "cascade_results" in body
    assert isinstance(body["cascade_results"], list)
    assert len(body["cascade_results"]) >= 1
    cascade = body["cascade_results"][0]
    assert cascade["field_modified"] == "Site.code_postal"
    assert cascade["persisted"] is True

    # Output fields attendus pour Site.code_postal
    output_fields = {a["output_field"] for a in cascade["actions"]}
    assert {
        "operat_zone_climatique",
        "operat_palier_altitude",
        "cabs_kwh_m2_an",
        "compliance_score",
    }.issubset(output_fields)

    # Audit log cascade.recompute créé avec ce correlation_id
    db2 = SessionLocal()
    try:
        # On ne connaît pas l'org_id résolu côté route, mais le correlation_id
        # est unique → on cherche dans toutes les orgs HELIOS connues
        from services.audit_log_service import AuditLog

        logs = db2.query(AuditLog).filter(AuditLog.correlation_id == cid, AuditLog.action == "cascade.recompute").all()
        assert len(logs) >= 1
        assert logs[0].field_modified == "Site.code_postal"
    finally:
        db2.close()


# ─── Test 2 : champ hors CASCADE_MAP → 0 cascade, audit basique ─────────────


def test_patch_field_outside_cascade_map_no_cascade(client, site_for_patch):
    """PATCH `nom` (hors CASCADE_MAP) → 0 cascade + audit log action='site.update'."""
    from database import SessionLocal
    from services.audit_log_service import AuditLog

    site_id, snapshot, _ = site_for_patch
    cid = f"test-patch-nom-{uuid.uuid4().hex[:8]}"
    new_nom = f"{snapshot['nom']}__test_phase3" if snapshot["nom"] else "Test Phase 3"

    resp = client.patch(
        f"/api/patrimoine/sites/{site_id}",
        json={"nom": new_nom},
        headers={"X-Correlation-ID": cid},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Pas de cascade (champ hors CASCADE_MAP)
    assert body["cascade_results"] == []

    # Audit log action='site.update' avec le correlation_id
    db2 = SessionLocal()
    try:
        logs = db2.query(AuditLog).filter(AuditLog.correlation_id == cid, AuditLog.action == "site.update").all()
        assert len(logs) >= 1
        assert "nom" in (logs[0].field_modified or "")
    finally:
        db2.close()


# ─── Test 3 : N champs cascade modifiés → N cascades distinctes ─────────────


def test_patch_multiple_cascade_fields_triggers_n_cascades(client, site_for_patch):
    """PATCH `code_postal` + `parking_area_m2` → 2 cascades distinctes dans la réponse."""
    site_id, snapshot, _ = site_for_patch
    cid = f"test-patch-multi-{uuid.uuid4().hex[:8]}"

    new_cp = "69001" if snapshot["code_postal"] != "69001" else "75001"
    new_parking = (snapshot["parking_area_m2"] or 0) + 12000

    resp = client.patch(
        f"/api/patrimoine/sites/{site_id}",
        json={"code_postal": new_cp, "parking_area_m2": new_parking},
        headers={"X-Correlation-ID": cid},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    fields_modified = {c["field_modified"] for c in body["cascade_results"]}
    assert "Site.code_postal" in fields_modified
    assert "Site.parking_area_m2" in fields_modified


# ─── Test 4 : aucun changement effectif → 0 cascade ─────────────────────────


def test_patch_no_change_no_cascade(client, site_for_patch):
    """PATCH avec valeur identique à l'actuelle → 0 cascade."""
    site_id, snapshot, _ = site_for_patch
    current_cp = snapshot["code_postal"] or "75001"

    # Si code_postal courant est None, on patch d'abord à une valeur connue
    if snapshot["code_postal"] is None:
        client.patch(f"/api/patrimoine/sites/{site_id}", json={"code_postal": "75001"})
        current_cp = "75001"

    cid = f"test-patch-noop-{uuid.uuid4().hex[:8]}"
    resp = client.patch(
        f"/api/patrimoine/sites/{site_id}",
        json={"code_postal": current_cp},
        headers={"X-Correlation-ID": cid},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Aucune cascade puisque diff vide pour ce champ
    assert body["cascade_results"] == []


# ─── Test 5 : org-scoping (site inexistant → 404) ───────────────────────────


def test_patch_org_scoping_returns_404_for_unknown_site(client):
    """PATCH d'un site inexistant → 404 (org-scoping fail-closed)."""
    resp = client.patch(
        "/api/patrimoine/sites/9999999",
        json={"code_postal": "13001"},
    )
    assert resp.status_code == 404


# ─── Test 6 : réponse contient cascade_results structurés ───────────────────


def test_patch_response_includes_cascade_results(client, site_for_patch):
    """Réponse PATCH contient la clé `cascade_results: list[dict]` (CascadeResult.to_dict)."""
    site_id, snapshot, _ = site_for_patch
    new_parking = (snapshot["parking_area_m2"] or 0) + 5000

    resp = client.patch(
        f"/api/patrimoine/sites/{site_id}",
        json={"parking_area_m2": new_parking},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "cascade_results" in body
    assert isinstance(body["cascade_results"], list)
    assert len(body["cascade_results"]) == 1
    cascade = body["cascade_results"][0]

    # Schéma CascadeResult.to_dict
    expected_keys = {
        "entity_type",
        "entity_id",
        "field_modified",
        "old_value",
        "new_value",
        "actions",
        "persisted",
        "computed_at",
        "errors_count",
        "successes_count",
    }
    assert expected_keys.issubset(set(cascade.keys()))
    assert cascade["entity_type"] == "Site"
    assert cascade["entity_id"] == site_id
    assert cascade["field_modified"] == "Site.parking_area_m2"


# ─── Test 7 : correlation_id propagé dans AuditLog ──────────────────────────


def test_patch_audit_log_correlation_id_propagated(client, site_for_patch):
    """X-Correlation-ID header → AuditLog.correlation_id pour cascade ET non-cascade."""
    from database import SessionLocal
    from services.audit_log_service import AuditLog

    site_id, snapshot, _ = site_for_patch
    cid = f"test-patch-cid-{uuid.uuid4().hex[:8]}"

    # Cascade field (parking) ET non-cascade field (nom) dans la même requête
    new_parking = (snapshot["parking_area_m2"] or 0) + 3000
    new_nom = f"{snapshot['nom'] or 'X'}__cid_test"

    resp = client.patch(
        f"/api/patrimoine/sites/{site_id}",
        json={"parking_area_m2": new_parking, "nom": new_nom},
        headers={"X-Correlation-ID": cid},
    )
    assert resp.status_code == 200, resp.text

    db2 = SessionLocal()
    try:
        logs = db2.query(AuditLog).filter(AuditLog.correlation_id == cid).all()
        actions = {l.action for l in logs}
        # Au moins le log cascade ET le log site.update
        assert "cascade.recompute" in actions
        assert "site.update" in actions
    finally:
        db2.close()


# ─── Test 8 : champ inconnu rejeté par Pydantic (extra='forbid') ────────────


def test_patch_invalid_field_rejected_by_pydantic(client, site_for_patch):
    """Body avec champ non déclaré dans SiteUpdateRequest → 422 (extra='forbid')."""
    site_id, _, _ = site_for_patch

    resp = client.patch(
        f"/api/patrimoine/sites/{site_id}",
        json={"hacked_field": "injection_attempt"},
    )
    assert resp.status_code == 422, resp.text
