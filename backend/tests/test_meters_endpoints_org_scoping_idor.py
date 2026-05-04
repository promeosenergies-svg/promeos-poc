"""
PROMEOS — Mini-sprint sécurité IDOR meters (CWE-639) — fix 2026-05-04.

Vérifie que les 3 endpoints meter du module patrimoine sont org-scopés :
- POST   /api/patrimoine/meters/{meter_id}/sub-meters
- DELETE /api/patrimoine/meters/{meter_id}/sub-meters/{sub_id}
- GET    /api/patrimoine/meters/{meter_id}/breakdown

Avant le fix : aucun appel à `_get_org_id` + `_load_meter_with_org_check` →
attaquant authentifié dans org A pouvait deviner meter_id de org B et
créer/supprimer/lire les compteurs (IDOR Authorization Bypass Through
User-Controlled Key).

Après le fix : `_load_meter_with_org_check` retourne 404 fail-closed si
meter_id ∉ org courante (pas d'enumeration des meter_id valides).

Couverture :
- 3 tests cross-org → 404 (un par endpoint)
- 3 tests own-org → succès non-régression (un par endpoint)
"""

from __future__ import annotations

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


@pytest.fixture
def foreign_meter_id():
    """Crée un Meter dans une org SÉPARÉE de la demo HELIOS courante.

    Le meter_id retourné doit être inaccessible depuis l'org HELIOS
    (résolue par DEMO_MODE / DemoState). Restauré en teardown via
    soft-delete + commit.
    """
    from database import SessionLocal
    from models import EntiteJuridique, Organisation, Portefeuille, Site
    from models.energy_models import EnergyVector, Meter

    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    created_ids: dict = {}

    try:
        org = Organisation(nom=f"Foreign Org IDOR {suffix}", siren=f"77700{suffix[:4]}")
        db.add(org)
        db.flush()
        created_ids["org"] = org.id

        ej = EntiteJuridique(
            nom=f"Foreign EJ IDOR {suffix}",
            siren=f"77700{suffix[:4]}",
            organisation_id=org.id,
        )
        db.add(ej)
        db.flush()
        created_ids["ej"] = ej.id

        pf = Portefeuille(nom=f"Foreign PF IDOR {suffix}", entite_juridique_id=ej.id)
        db.add(pf)
        db.flush()
        created_ids["pf"] = pf.id

        site = Site(nom=f"Foreign Site IDOR {suffix}", type="bureau", portefeuille_id=pf.id, actif=True)
        db.add(site)
        db.flush()
        created_ids["site"] = site.id

        meter = Meter(
            site_id=site.id,
            meter_id=f"FOREIGN-METER-{suffix}",
            name=f"Foreign Principal {suffix}",
            energy_vector=EnergyVector.ELECTRICITY,
            type_compteur="electricite",
            is_active=True,
        )
        db.add(meter)
        db.flush()
        created_ids["meter"] = meter.id

        db.commit()
        yield meter.id
    finally:
        # Cleanup ordre inverse : meter → site → pf → ej → org
        try:
            for cls, key in [
                (Meter, "meter"),
                (Site, "site"),
                (Portefeuille, "pf"),
                (EntiteJuridique, "ej"),
                (Organisation, "org"),
            ]:
                if key in created_ids:
                    obj = db.query(cls).filter(cls.id == created_ids[key]).first()
                    if obj:
                        db.delete(obj)
            db.commit()
        except Exception:
            db.rollback()
        db.close()


@pytest.fixture
def own_meter_id():
    """Récupère un Meter EXISTANT dans l'org HELIOS courante (demo seed)."""
    from database import SessionLocal
    from models.energy_models import Meter

    db = SessionLocal()
    try:
        meter = db.query(Meter).filter(Meter.is_active.is_(True), Meter.parent_meter_id.is_(None)).first()
        if not meter:
            pytest.skip("Aucun Meter actif (seed HELIOS)")
        yield meter.id
    finally:
        db.close()


# ─── 3 tests cross-org → 404 (IDOR mitigé) ──────────────────────────────────


def test_post_sub_meter_cross_org_returns_404(client, foreign_meter_id):
    """POST sur meter d'une autre org → 404 (avant fix : 201 + crash potentiel)."""
    resp = client.post(
        f"/api/patrimoine/meters/{foreign_meter_id}/sub-meters",
        json={"name": "IDOR attack attempt", "meter_id": "ATTACK-001"},
    )
    assert resp.status_code == 404, (
        f"IDOR non bloqué : POST cross-org renvoie {resp.status_code} au lieu de 404. Body: {resp.text}"
    )


def test_delete_sub_meter_cross_org_returns_404(client, foreign_meter_id):
    """DELETE sur meter d'une autre org → 404 (le sub_id n'a pas d'importance ici)."""
    resp = client.delete(
        f"/api/patrimoine/meters/{foreign_meter_id}/sub-meters/9999999",
    )
    assert resp.status_code == 404, (
        f"IDOR non bloqué : DELETE cross-org renvoie {resp.status_code} au lieu de 404. Body: {resp.text}"
    )


def test_get_meter_breakdown_cross_org_returns_404(client, foreign_meter_id):
    """GET breakdown sur meter d'une autre org → 404 (évite fuite données comptage)."""
    resp = client.get(f"/api/patrimoine/meters/{foreign_meter_id}/breakdown")
    assert resp.status_code == 404, (
        f"IDOR non bloqué : GET cross-org renvoie {resp.status_code} au lieu de 404. Body: {resp.text}"
    )


# ─── 3 tests own-org → succès non-régression ─────────────────────────────────


def test_get_meter_breakdown_own_org_succeeds(client, own_meter_id):
    """GET breakdown sur meter own-org → 200 (anti-régression)."""
    resp = client.get(f"/api/patrimoine/meters/{own_meter_id}/breakdown")
    assert resp.status_code == 200, f"GET own-org devrait réussir, code={resp.status_code} body={resp.text}"


def test_post_sub_meter_own_org_succeeds(client, own_meter_id):
    """POST sub-meter sur meter own-org → 201 (anti-régression).

    Cleanup : le sub-meter créé est désactivé via DELETE pour ne pas polluer
    la seed des tests suivants.
    """
    suffix = uuid.uuid4().hex[:6]
    resp = client.post(
        f"/api/patrimoine/meters/{own_meter_id}/sub-meters",
        json={"name": f"Test Phase IDOR {suffix}", "meter_id": f"SUB-IDOR-{suffix}"},
    )
    assert resp.status_code == 201, f"POST own-org devrait réussir, code={resp.status_code} body={resp.text}"
    sub_id = resp.json().get("id")
    if sub_id:
        # Cleanup
        client.delete(f"/api/patrimoine/meters/{own_meter_id}/sub-meters/{sub_id}")


def test_delete_sub_meter_own_org_succeeds(client, own_meter_id):
    """DELETE sub-meter own-org → 200 (anti-régression).

    Crée un sub-meter d'abord puis le supprime. Vérifie que le 200 est bien
    le code retour (pas un 404 cross-org).
    """
    suffix = uuid.uuid4().hex[:6]
    create_resp = client.post(
        f"/api/patrimoine/meters/{own_meter_id}/sub-meters",
        json={"name": f"Sub IDOR delete {suffix}", "meter_id": f"SUB-DEL-{suffix}"},
    )
    assert create_resp.status_code == 201, f"Setup failed : {create_resp.text}"
    sub_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/patrimoine/meters/{own_meter_id}/sub-meters/{sub_id}")
    assert del_resp.status_code == 200, (
        f"DELETE own-org devrait réussir, code={del_resp.status_code} body={del_resp.text}"
    )
