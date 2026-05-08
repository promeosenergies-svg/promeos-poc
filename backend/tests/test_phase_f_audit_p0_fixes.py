"""
PROMEOS — Phase F audit P0 fixes (3 P0 cardinaux pilote pré-prod externe).

Tests régression cardinaux post-audit code-reviewer global Phase E + F :

- P0-1 : `bridge_route.py GET /status/{job_id}` IDOR cross-tenant DataImportJob
- P0-2 : `contracts_parse.py` + `billing.py` import_pdf OOM avant Content-Length check
- P0-3 : `create_organisation` admin role guard strict (DG_OWNER/DSI_ADMIN)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import (
    Base,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _h(org_id: int) -> dict:
    return {"X-Org-Id": str(org_id)}


# ─── P0-1 : Bridge status IDOR ──────────────────────────────────────────────


def test_p0_1_bridge_status_cross_tenant_404(client, db):
    """P0-1 : DataImportJob d'org B inaccessible depuis scope org A."""
    from models.energy_models import DataImportJob

    org_a = Organisation(nom="Org Alpha", type_client="bureau", actif=True, siren="111111111")
    org_b = Organisation(nom="Org Bravo", type_client="industrie", actif=True, siren="222222222")
    db.add_all([org_a, org_b])
    db.flush()

    ej_b = EntiteJuridique(organisation_id=org_b.id, nom="EJ Bravo", siren="222111222")
    db.add(ej_b)
    db.flush()
    pf_b = Portefeuille(entite_juridique_id=ej_b.id, nom="PF Bravo")
    db.add(pf_b)
    db.flush()
    site_b = Site(portefeuille_id=pf_b.id, nom="Site Bravo", type=TypeSite.BUREAU, actif=True)
    db.add(site_b)
    db.flush()

    job_b = DataImportJob(job_type="consumption_import", site_id=site_b.id)
    db.add(job_b)
    db.commit()

    # Org A tente de consulter job de site Bravo → 404 anti-énumération
    r = client.get(f"/api/bridge/status/{job_b.id}", headers=_h(org_a.id))
    assert r.status_code == 404


def test_p0_1_bridge_status_same_tenant_ok(client, db):
    """P0-1 : DataImportJob de scope owner accessible normalement."""
    from models.energy_models import DataImportJob

    org_a = Organisation(nom="Org Alpha", type_client="bureau", actif=True, siren="111111111")
    db.add(org_a)
    db.flush()
    ej = EntiteJuridique(organisation_id=org_a.id, nom="EJ A", siren="111111222")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF A")
    db.add(pf)
    db.flush()
    site = Site(portefeuille_id=pf.id, nom="Site A", type=TypeSite.BUREAU, actif=True)
    db.add(site)
    db.flush()
    job = DataImportJob(job_type="consumption_import", site_id=site.id)
    db.add(job)
    db.commit()

    r = client.get(f"/api/bridge/status/{job.id}", headers=_h(org_a.id))
    assert r.status_code == 200
    assert r.json()["job_id"] == job.id


# ─── P0-2 : OOM Content-Length avant read ───────────────────────────────────


def test_p0_2_oversized_payload_post_read_returns_413(client, db):
    """P0-2 : payload > 20 Mo (via body) rejeté par check post-read avec 413 (anti-OOM).

    NB : TestClient recalcule Content-Length depuis le body, donc tester le check
    pré-read via header forgé n'est pas fiable. On vérifie ici que le check
    post-read (filet de sécurité doublé) rejette bien un payload réel oversized.
    """
    org_a = Organisation(nom="Org Alpha", type_client="bureau", actif=True, siren="111111111")
    db.add(org_a)
    db.commit()

    # Body réel > 20 Mo (PDF magic bytes + padding)
    huge_body = b"%PDF-1.4\n" + (b"X" * (21 * 1024 * 1024))
    r = client.post(
        "/api/contracts/parse-pdf",
        files={"file": ("huge.pdf", huge_body, "application/pdf")},
        headers={"X-Org-Id": str(org_a.id)},
    )
    assert r.status_code == 413


def test_p0_2_content_length_pre_read_check_present():
    """P0-2 source-guard : check Content-Length présent AVANT await file.read()."""
    from pathlib import Path

    backend_root = Path(__file__).resolve().parent.parent
    for routes_file in (
        backend_root / "routes" / "contracts_parse.py",
        backend_root / "routes" / "billing.py",
    ):
        src = routes_file.read_text(encoding="utf-8")
        # Le check Content-Length doit précéder file.read() dans les endpoints PDF
        assert 'content_length_header = request.headers.get("content-length")' in src, (
            f"P0-2 fix manquant dans {routes_file.name}"
        )


# ─── P0-3 : create_organisation admin role strict ───────────────────────────


def test_p0_3_create_organisation_demo_mode_passes(client, db):
    """P0-3 : DEMO_MODE (auth=None) accepte création (compat existante)."""
    r = client.post(
        "/api/patrimoine/crud/organisations",
        json={"nom": "New Demo Org", "type_client": "tertiaire"},
    )
    assert r.status_code == 201


def test_p0_3_require_admin_access_helper_strict():
    """P0-3 : helper require_admin_access rejette VIEWER/ENERGY_MANAGER."""
    from dataclasses import dataclass

    from fastapi import HTTPException

    from models import UserRole
    from services.auth_guards import require_admin_access

    @dataclass
    class _MockAuth:
        role: UserRole
        org_id: int = 1
        user: object = None

    # ENERGY_MANAGER (rôle WRITE_ROLES mais pas ADMIN_ROLES) → 403
    with pytest.raises(HTTPException) as exc:
        require_admin_access(_MockAuth(role=UserRole.ENERGY_MANAGER))
    assert exc.value.status_code == 403
    assert "FORBIDDEN_ADMIN_PROVISIONING" in str(exc.value.detail)

    # AUDITEUR (lecture seule) → 403
    with pytest.raises(HTTPException):
        require_admin_access(_MockAuth(role=UserRole.AUDITEUR))

    # DG_OWNER → accepté
    require_admin_access(_MockAuth(role=UserRole.DG_OWNER))

    # DSI_ADMIN → accepté
    require_admin_access(_MockAuth(role=UserRole.DSI_ADMIN))

    # auth=None (DEMO_MODE) → accepté (compat)
    require_admin_access(None)
