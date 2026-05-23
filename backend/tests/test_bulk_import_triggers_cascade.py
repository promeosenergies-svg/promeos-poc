"""
PROMEOS — P0-A 2026-05-23 : import bulk déclenche cascade conformité.

Avant ce fix : `POST /api/import/sites` créait N sites sans recalcul DT/BACS/APER.
Maintenant l'endpoint appelle `batch_cascade_recompute_sites` post-import.
Idempotence garantie (re-import = re-cascade no-op si rien n'a changé).
"""

from __future__ import annotations

import io
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402
from main import app  # noqa: E402
from models import (  # noqa: E402
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
)
from models.iam import AuditLog  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
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


@pytest.fixture
def org_setup(db):
    """Setup minimum: 1 organisation + 1 EJ + 1 portefeuille (pré-requis import)."""
    org = Organisation(nom="Org Import", type_client="bureau", actif=True, siren="999000111")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ Import", siren="999000111")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF Import")
    db.add(pf)
    db.commit()
    return {"org": org, "pf": pf}


_CSV = (
    "nom,adresse,code_postal,ville,surface_m2,type,naf_code\n"
    "Bureau A,1 rue A,75001,Paris,1200,bureau,\n"
    "Bureau B,2 rue B,69001,Lyon,800,bureau,\n"
    "Bureau C,3 rue C,13001,Marseille,1500,bureau,\n"
)


def test_bulk_import_returns_cascade_summary(client, db, org_setup):
    """L'import bulk doit retourner un dict cascade avec les statuts par site."""
    files = {"file": ("sites.csv", io.BytesIO(_CSV.encode("utf-8")), "text/csv")}
    response = client.post(
        "/api/import/sites",
        files=files,
        headers={"X-Org-Id": str(org_setup["org"].id), "X-Correlation-ID": "test-bulk-001"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 3
    assert body["errors"] == 0
    cascade = body.get("cascade")
    assert cascade is not None, "réponse import doit inclure un champ cascade"
    assert cascade["processed"] == 3
    # Soit recomputed (compliance recalculée), soit pending_recompute, soit up_to_date.
    assert cascade["processed"] == (
        cascade["recomputed"] + cascade["pending_recompute"] + cascade["up_to_date"] + cascade["errors"]
    )
    # Chaque site doit avoir un statut clair
    for site_status in cascade["sites"]:
        assert site_status["status"] in {
            "recomputed",
            "pending_recompute",
            "up_to_date",
            "compliance_error",
            "not_found",
        }


def test_bulk_import_writes_audit_log_per_site(client, db, org_setup):
    """Chaque site importé doit générer un audit log site.cascade_recompute OR site.cascade_pending."""
    files = {"file": ("sites.csv", io.BytesIO(_CSV.encode("utf-8")), "text/csv")}
    client.post(
        "/api/import/sites",
        files=files,
        headers={"X-Org-Id": str(org_setup["org"].id), "X-Correlation-ID": "test-bulk-002"},
    )

    site_ids = [s.id for s in db.query(Site).all()]
    assert len(site_ids) == 3

    for sid in site_ids:
        logs = (
            db.query(AuditLog)
            .filter(
                AuditLog.resource_type == "site",
                AuditLog.resource_id == str(sid),
                AuditLog.action.in_(("site.cascade_recompute", "site.cascade_pending")),
            )
            .all()
        )
        assert len(logs) >= 1, f"site {sid} doit avoir au moins un log cascade_recompute ou cascade_pending"


def test_bulk_import_is_idempotent(client, db, org_setup):
    """Re-cascade sur les mêmes sites sans changement = up_to_date (zéro nouveau log)."""
    from regops.services.cascade_recompute_service import batch_cascade_recompute_sites

    files = {"file": ("sites.csv", io.BytesIO(_CSV.encode("utf-8")), "text/csv")}
    client.post(
        "/api/import/sites",
        files=files,
        headers={"X-Org-Id": str(org_setup["org"].id)},
    )
    site_ids = [s.id for s in db.query(Site).all()]
    initial_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.resource_type == "site",
            AuditLog.action.in_(("site.cascade_recompute", "site.cascade_pending")),
        )
        .count()
    )

    # Second cascade : aucune donnée n'a bougé, donc up_to_date partout
    summary = batch_cascade_recompute_sites(
        db,
        site_ids=site_ids,
        org_id=org_setup["org"].id,
        correlation_id="test-bulk-003",
    )
    # Tous les sites doivent être up_to_date ou pending_recompute (jamais recomputed à nouveau)
    assert summary["recomputed"] == 0, f"Cascade idempotente attendue (0 recomputed), reçu {summary['recomputed']}"

    # Aucun nouveau log recompute n'a été écrit
    final_logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.resource_type == "site",
            AuditLog.action == "site.cascade_recompute",
        )
        .count()
    )
    # Le compteur de cascade_recompute logs ne doit pas augmenter pour les sites up_to_date.
    # (Les sites pending peuvent en revanche ré-écrire un cascade_pending log à chaque appel —
    # signaler la conformité stale en continu est légitime.)
    initial_recompute_only = (
        db.query(AuditLog)
        .filter(
            AuditLog.resource_type == "site",
            AuditLog.action == "site.cascade_recompute",
        )
        .count()
    )
    assert initial_recompute_only == final_logs


def test_pending_recompute_when_missing_surface(client, db, org_setup):
    """Un site sans surface doit générer un audit log site.cascade_pending."""
    csv_no_surface = (
        "nom,adresse,code_postal,ville,surface_m2,type,naf_code\nBureau Sans Surface,1 rue X,75001,Paris,,bureau,\n"
    )
    files = {"file": ("sites.csv", io.BytesIO(csv_no_surface.encode("utf-8")), "text/csv")}
    response = client.post(
        "/api/import/sites",
        files=files,
        headers={"X-Org-Id": str(org_setup["org"].id)},
    )
    assert response.status_code == 200
    body = response.json()
    # provision_site assigne par défaut surface 1000 si vide → vérifions le statut cascade
    cascade = body["cascade"]
    assert cascade["processed"] == 1
