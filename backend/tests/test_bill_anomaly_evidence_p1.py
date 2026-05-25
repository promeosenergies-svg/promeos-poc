"""
PROMEOS — Bill Intelligence P1 C2 (2026-05-24) : preuves anomalies.

Vérifie :
- Upload preuve (POST) avec multipart : OK + hash SHA-256 + storage fs://
- Liste preuves (GET) : org-scopée
- Download preuve (GET) : binaire + content-disposition + header hash
- Cross-org : 404 anti-énumération
- MIME non whitelisted : 415
- evidence_type invalide : 400
- Fichier vide : 400
- Fichier disparu : 404 EVIDENCE_FILE_MISSING
- Path traversal : 403
"""

from __future__ import annotations

import io
import os
import sys
from datetime import date
from decimal import Decimal

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
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)
from models.bill_anomaly import BillAnomaly  # noqa: E402
from models.bill_anomaly_evidence import BillAnomalyEvidence  # noqa: E402
from models.billing_models import EnergyInvoice  # noqa: E402


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
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed(db, org_id_override=None):
    org = Organisation(
        nom=f"Org C2 #{org_id_override or 'A'}",
        siren=f"{(org_id_override or 1):09d}",
        actif=True,
    )
    db.add(org)
    db.flush()
    if org_id_override:
        # Force the id (SQLite allows update on PK in some cases) — skip in this test setup
        pass
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren=org.siren)
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site C2",
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        actif=True,
    )
    db.add(site)
    db.flush()
    invoice = EnergyInvoice(
        site_id=site.id,
        invoice_number=f"INV-{org.id}",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        issue_date=date(2026, 5, 5),
        total_eur=1000.0,
        energy_kwh=5000,
        source="manual",
    )
    db.add(invoice)
    db.flush()
    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="warning",
        actual_value=Decimal("42.50"),
        details_json={"vnu_total_eur": 42.50},
    )
    db.add(anomaly)
    db.commit()
    return org, invoice, anomaly


# ─── Upload nominal ─────────────────────────────────────────────────────


def test_upload_evidence_pdf_returns_201_with_hash(client, db):
    """Upload PDF → 201 + hash SHA-256 + storage_uri masqué."""
    org, _, anomaly = _seed(db)
    pdf_bytes = b"%PDF-1.4\n%fake test content\n"
    response = client.post(
        f"/api/billing/anomalies/{anomaly.id}/evidences?evidence_type=invoice_pdf",
        files={"file": ("rapport.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["anomaly_id"] == anomaly.id
    assert body["filename"] == "rapport.pdf"
    assert body["mime_type"] == "application/pdf"
    assert len(body["file_hash_sha256"]) == 64
    # storage_uri ne doit JAMAIS être exposé en clair côté FE
    assert "storage_uri" not in body


# ─── Liste ──────────────────────────────────────────────────────────────


def test_list_evidences_org_scoped(client, db):
    """GET liste les preuves de l'org courante uniquement."""
    org, _, anomaly = _seed(db)
    pdf = b"%PDF content"
    client.post(
        f"/api/billing/anomalies/{anomaly.id}/evidences?evidence_type=invoice_pdf",
        files={"file": ("a.pdf", io.BytesIO(pdf), "application/pdf")},
        headers={"X-Org-Id": str(org.id)},
    )
    response = client.get(
        f"/api/billing/anomalies/{anomaly.id}/evidences",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["anomaly_id"] == anomaly.id
    assert body["count"] == 1
    assert body["has_pending_evidence"] is True
    assert body["evidences"][0]["filename"] == "a.pdf"


def test_anomaly_without_evidence_returns_zero(client, db):
    """Liste preuves d'une anomalie sans preuve uploadée → count=0, has_pending=False."""
    org, _, anomaly = _seed(db)
    response = client.get(
        f"/api/billing/anomalies/{anomaly.id}/evidences",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["has_pending_evidence"] is False


# ─── Download ───────────────────────────────────────────────────────────


def test_download_evidence_returns_binary_with_hash_header(client, db):
    """GET download → 200 + binaire + content-disposition + X-Evidence-Hash-Sha256."""
    org, _, anomaly = _seed(db)
    pdf = b"%PDF download content"
    up = client.post(
        f"/api/billing/anomalies/{anomaly.id}/evidences?evidence_type=invoice_pdf",
        files={"file": ("preuve.pdf", io.BytesIO(pdf), "application/pdf")},
        headers={"X-Org-Id": str(org.id)},
    )
    ev_id = up.json()["id"]
    expected_hash = up.json()["file_hash_sha256"]

    response = client.get(
        f"/api/billing/anomalies/{anomaly.id}/evidences/{ev_id}/download",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    assert response.content == pdf
    assert 'filename="preuve.pdf"' in response.headers.get("content-disposition", "")
    assert response.headers.get("x-evidence-hash-sha256") == expected_hash


# ─── Cross-org anti-énumération ─────────────────────────────────────────


def test_cross_org_upload_returns_404(client, db):
    """Org 2 tente d'uploader sur anomalie de org 1 → 404 anti-énumération."""
    org_a, _, anomaly = _seed(db)
    other_org = Organisation(nom="Org B", siren="222222222", actif=True)
    db.add(other_org)
    db.commit()

    response = client.post(
        f"/api/billing/anomalies/{anomaly.id}/evidences?evidence_type=invoice_pdf",
        files={"file": ("hack.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        headers={"X-Org-Id": str(other_org.id)},
    )
    assert response.status_code == 404
    assert (response.json().get("detail") or {}).get("code") == "BILL_ANOMALY_NOT_FOUND"


def test_cross_org_download_returns_404(client, db):
    """Org B tente de télécharger preuve de Org A → 404."""
    org_a, _, anomaly = _seed(db)
    up = client.post(
        f"/api/billing/anomalies/{anomaly.id}/evidences?evidence_type=invoice_pdf",
        files={"file": ("a.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        headers={"X-Org-Id": str(org_a.id)},
    )
    ev_id = up.json()["id"]

    other_org = Organisation(nom="Org B", siren="333333333", actif=True)
    db.add(other_org)
    db.commit()

    response = client.get(
        f"/api/billing/anomalies/{anomaly.id}/evidences/{ev_id}/download",
        headers={"X-Org-Id": str(other_org.id)},
    )
    assert response.status_code == 404


# ─── Validation MIME ────────────────────────────────────────────────────


def test_upload_unsupported_mime_returns_415(client, db):
    """text/html non whitelisté → 415 avec message FR."""
    org, _, anomaly = _seed(db)
    response = client.post(
        f"/api/billing/anomalies/{anomaly.id}/evidences?evidence_type=invoice_pdf",
        files={"file": ("hack.html", io.BytesIO(b"<html/>"), "text/html")},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 415
    detail = response.json().get("detail") or {}
    assert detail.get("code") == "EVIDENCE_MIME_NOT_ALLOWED"
    assert "PDF" in (detail.get("hint") or "")


def test_invalid_evidence_type_returns_400(client, db):
    """evidence_type hors whitelist → 400 avec liste autorisée."""
    org, _, anomaly = _seed(db)
    response = client.post(
        f"/api/billing/anomalies/{anomaly.id}/evidences?evidence_type=phishing",
        files={"file": ("a.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 400
    assert (response.json().get("detail") or {}).get("code") == "EVIDENCE_TYPE_INVALID"


def test_empty_file_returns_400(client, db):
    """Fichier vide → 400 EVIDENCE_EMPTY_FILE."""
    org, _, anomaly = _seed(db)
    response = client.post(
        f"/api/billing/anomalies/{anomaly.id}/evidences?evidence_type=invoice_pdf",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 400
    assert (response.json().get("detail") or {}).get("code") == "EVIDENCE_EMPTY_FILE"


# ─── Fichier disparu ────────────────────────────────────────────────────


def test_download_missing_file_returns_404(client, db):
    """Fichier supprimé du disque → 404 EVIDENCE_FILE_MISSING."""
    org, _, anomaly = _seed(db)
    up = client.post(
        f"/api/billing/anomalies/{anomaly.id}/evidences?evidence_type=invoice_pdf",
        files={"file": ("a.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
        headers={"X-Org-Id": str(org.id)},
    )
    ev_id = up.json()["id"]

    # Récupère le path et supprime le fichier physique
    e = db.query(BillAnomalyEvidence).filter_by(id=ev_id).first()
    fs_path = e.storage_uri[len("fs://") :]
    os.remove(fs_path)

    response = client.get(
        f"/api/billing/anomalies/{anomaly.id}/evidences/{ev_id}/download",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 404
    assert (response.json().get("detail") or {}).get("code") == "EVIDENCE_FILE_MISSING"


# ─── Path traversal ─────────────────────────────────────────────────────


def test_download_path_traversal_returns_403(client, db):
    """storage_uri avec '..' → 403 EVIDENCE_PATH_INVALID."""
    org, invoice, anomaly = _seed(db)
    # Création manuelle avec un storage_uri malveillant (ne passe pas par l'upload normal)
    e = BillAnomalyEvidence(
        anomaly_id=anomaly.id,
        org_id=org.id,
        invoice_id=invoice.id,
        evidence_type="invoice_pdf",
        filename="hack.pdf",
        mime_type="application/pdf",
        file_hash_sha256="0" * 64,
        storage_uri="fs:///tmp/../../etc/passwd",
        source="manual_upload",
    )
    db.add(e)
    db.commit()

    response = client.get(
        f"/api/billing/anomalies/{anomaly.id}/evidences/{e.id}/download",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 403
    assert (response.json().get("detail") or {}).get("code") == "EVIDENCE_PATH_INVALID"


# ─── S3 not supported ───────────────────────────────────────────────────


def test_download_s3_returns_501(client, db):
    """s3:// → 501 EVIDENCE_STORAGE_NOT_SUPPORTED documenté."""
    org, invoice, anomaly = _seed(db)
    e = BillAnomalyEvidence(
        anomaly_id=anomaly.id,
        org_id=org.id,
        invoice_id=invoice.id,
        evidence_type="invoice_pdf",
        filename="cloud.pdf",
        mime_type="application/pdf",
        file_hash_sha256="0" * 64,
        storage_uri="s3://bucket/evidences/cloud.pdf",
        source="manual_upload",
    )
    db.add(e)
    db.commit()

    response = client.get(
        f"/api/billing/anomalies/{anomaly.id}/evidences/{e.id}/download",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 501
    assert (response.json().get("detail") or {}).get("code") == "EVIDENCE_STORAGE_NOT_SUPPORTED"
