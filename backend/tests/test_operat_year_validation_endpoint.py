"""Tests endpoint Conformite S1 — validation annee de reference OPERAT.

S1 #324 Chantier 2 (2026-05-27) — validation annee de reference via le
router `/api/tertiaire/efa/{efa_id}/consumption/declare`.

Couverture :
  T1. Annee de reference valide (2010-2022) -> 200.
  T2. Annee de reference trop ancienne (< 2010) -> 422 + message FR.
  T3. Annee de reference trop recente (> 2022) sans flag -> 422 + message FR.
  T4. Annee post-2022 avec is_first_full_year_of_operation=True -> 200.
  T5. Annee future avec is_first_full_year_of_operation=True -> 422.
  T6. Conso non-reference posterieure a 2022 -> 200 (plage large preservee).
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
def fresh_efa_id():
    """Cree une EFA jetable pour le test, supprime en teardown."""
    from database import SessionLocal
    from models.tertiaire import TertiaireEfa

    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    efa = TertiaireEfa(nom=f"EFA Test S1 {suffix}", org_id=1)
    try:
        db.add(efa)
        db.commit()
        yield efa.id
    finally:
        # Cleanup : conso d'abord (cascade pas force), puis EFA.
        from models.tertiaire import TertiaireEfaConsumption

        try:
            db.query(TertiaireEfaConsumption).filter_by(efa_id=efa.id).delete()
            obj = db.query(TertiaireEfa).filter_by(id=efa.id).first()
            if obj:
                db.delete(obj)
            db.commit()
        except Exception:
            db.rollback()
        db.close()


def test_t1_reference_year_valid_2019_succeeds(client, fresh_efa_id):
    resp = client.post(
        f"/api/tertiaire/efa/{fresh_efa_id}/consumption/declare",
        json={
            "year": 2019,
            "kwh_total": 500000,
            "is_reference": True,
            "source": "factures",
        },
    )
    assert resp.status_code == 200, f"Annee 2019 valide doit passer, got {resp.status_code} {resp.text[:300]}"


def test_t2_reference_year_too_old_rejected(client, fresh_efa_id):
    resp = client.post(
        f"/api/tertiaire/efa/{fresh_efa_id}/consumption/declare",
        json={
            "year": 2005,
            "kwh_total": 500000,
            "is_reference": True,
        },
    )
    assert resp.status_code == 422, (
        f"Annee 2005 trop ancienne doit etre rejetee (422), got {resp.status_code} {resp.text[:300]}"
    )
    body = resp.json()
    msg = (body.get("detail") or body.get("message") or "").lower()
    assert "periode autorisee" in msg or "période autorisée" in msg, (
        f"Message FR doit mentionner la periode autorisee. Got : {body}"
    )
    assert "2010" in msg and "2022" in msg, "Message FR doit citer les bornes 2010-2022."


def test_t3_reference_year_too_recent_rejected_without_flag(client, fresh_efa_id):
    resp = client.post(
        f"/api/tertiaire/efa/{fresh_efa_id}/consumption/declare",
        json={
            "year": 2024,
            "kwh_total": 500000,
            "is_reference": True,
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    msg = (body.get("detail") or body.get("message") or "").lower()
    assert "first_full_year" in msg or "1ere" in msg or "1ère" in msg or "premiere" in msg or "première" in msg, (
        f"Message FR doit guider vers le flag is_first_full_year_of_operation. Got : {body}"
    )


def test_t4_first_full_year_post_2022_accepted_with_flag(client, fresh_efa_id):
    resp = client.post(
        f"/api/tertiaire/efa/{fresh_efa_id}/consumption/declare",
        json={
            "year": 2024,
            "kwh_total": 500000,
            "is_reference": True,
            "is_first_full_year_of_operation": True,
            "source": "factures",
        },
    )
    assert resp.status_code == 200, (
        f"Annee 2024 avec is_first_full_year=True doit etre acceptee (cas batiment neuf), "
        f"got {resp.status_code} {resp.text[:300]}"
    )


def test_t5_future_year_rejected_even_with_flag(client, fresh_efa_id):
    from datetime import date

    future_year = date.today().year + 2
    resp = client.post(
        f"/api/tertiaire/efa/{fresh_efa_id}/consumption/declare",
        json={
            "year": future_year,
            "kwh_total": 500000,
            "is_reference": True,
            "is_first_full_year_of_operation": True,
        },
    )
    assert resp.status_code == 422, (
        f"Annee future doit etre rejetee meme avec is_first_full_year=True. Got {resp.status_code} {resp.text[:300]}"
    )


def test_t6_non_reference_year_after_2022_accepted(client, fresh_efa_id):
    """Conso non-reference peut etre post-2022 (suivi annuel)."""
    resp = client.post(
        f"/api/tertiaire/efa/{fresh_efa_id}/consumption/declare",
        json={
            "year": 2025,
            "kwh_total": 320000,
            "is_reference": False,
            "source": "factures",
        },
    )
    assert resp.status_code == 200, (
        f"Conso non-reference 2025 doit passer (suivi annuel OPERAT). Got {resp.status_code} {resp.text[:300]}"
    )
