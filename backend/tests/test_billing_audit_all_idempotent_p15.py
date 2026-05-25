"""
PROMEOS — Bill Intelligence P1.5 C2 (2026-05-24) :
`POST /api/billing/audit-all` est désormais **idempotent**.

Doctrine : "Un audit-all doit être idempotent. Relancer un audit sur des
factures déjà auditées ne doit jamais produire un 500."

Cause racine P1 (D-P2-001) : tous les détecteurs R19-R31 dans
`anomaly_detector.py::detect_anomalies_for_invoice` faisaient `db.add(rN)`
aveuglément → violation `UniqueConstraint(invoice_id, code)` au re-run
→ HTTP 500 `IntegrityError`.

Fix : helper `_upsert_anomaly` qui :
- crée si absent
- update champs métier si ouverte
- skip si résolue (resolved_at NOT NULL)

Vérifie :
- 1er run audit-all → 200, anomalies créées
- 2e run audit-all → 200, 0 doublon, anomalies mises à jour
- Violation unique simulée (force add brut) → l'upsert convertit en update
- Anomalie résolue par opérateur préservée (resolved_at + resolution_note intacts)
- Sans org/JWT → 401 NO_ORG_CONTEXT (préservation P1 C3)
- message_fr présent et cohérent
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402
from main import app  # noqa: E402
from models import Base, EntiteJuridique, Organisation, Portefeuille, Site, TypeSite  # noqa: E402
from models.bill_anomaly import BillAnomaly  # noqa: E402
from models.billing_models import EnergyInvoice  # noqa: E402
from services.bill_intelligence.anomaly_detector import _upsert_anomaly  # noqa: E402


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


def _seed_org_with_invoice(db):
    """Crée 1 org + 1 site + 1 facture pour tests d'audit."""
    org = Organisation(nom="Org P1.5", siren="555555555", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="555555555")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site P1.5",
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
        invoice_number="INV-P15-001",
        period_start=date(2026, 4, 1),
        period_end=date(2026, 4, 30),
        issue_date=date(2026, 5, 5),
        total_eur=1000.0,
        energy_kwh=5000,
        source="manual",
    )
    db.add(invoice)
    db.commit()
    return org, site, invoice


# ─── 1. Unit test du helper _upsert_anomaly ────────────────────────────


def test_upsert_creates_when_absent(db):
    """_upsert_anomaly insère si aucune anomalie pour (invoice, code)."""
    _, _, invoice = _seed_org_with_invoice(db)
    new_anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="warning",
        actual_value=Decimal("42.50"),
        details_json={"vnu_total_eur": 42.50},
    )
    status, persisted = _upsert_anomaly(db, new_anomaly)
    db.commit()
    assert status == "created"
    assert persisted.id is not None
    assert db.query(BillAnomaly).count() == 1


def test_upsert_updates_when_open(db):
    """_upsert_anomaly met à jour les champs métier si anomalie ouverte existe."""
    _, _, invoice = _seed_org_with_invoice(db)
    first = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="warning",
        actual_value=Decimal("42.50"),
        details_json={"vnu_total_eur": 42.50},
    )
    _upsert_anomaly(db, first)
    db.commit()
    original_id = first.id

    # Nouvelle détection avec des valeurs différentes
    refreshed = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="critical",  # severity bump
        actual_value=Decimal("99.99"),  # montant nouveau
        details_json={"vnu_total_eur": 99.99, "lines_count": 5},
    )
    status, persisted = _upsert_anomaly(db, refreshed)
    db.commit()

    assert status == "updated"
    assert persisted.id == original_id, "L'id doit être préservé sur update"
    assert persisted.severity == "critical"
    assert persisted.actual_value == Decimal("99.9900")
    assert (persisted.details_json or {}).get("lines_count") == 5
    # Toujours 1 ligne en DB (pas de duplication)
    assert db.query(BillAnomaly).count() == 1


def test_upsert_skips_when_resolved(db):
    """_upsert_anomaly respecte la résolution opérateur (skipped_resolved)."""
    _, _, invoice = _seed_org_with_invoice(db)
    first = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="warning",
        actual_value=Decimal("42.50"),
        details_json={},
    )
    _upsert_anomaly(db, first)
    db.commit()

    # L'opérateur clôt l'anomalie
    first.resolved_at = datetime.now(timezone.utc)
    first.resolution_note = "Vérifié auprès du fournisseur — facturation OK."
    db.commit()
    original_note = first.resolution_note

    # Nouvelle détection → doit être SKIP (respect résolution)
    re_detected = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="critical",
        actual_value=Decimal("999.0"),
        details_json={},
    )
    status, persisted = _upsert_anomaly(db, re_detected)
    db.commit()

    assert status == "skipped_resolved"
    assert persisted.resolution_note == original_note, "Note opérateur doit être préservée"
    assert persisted.severity == "warning", "Severity ouvert ≠ severity re-détectée (preservation)"
    # Pas de nouvelle ligne
    assert db.query(BillAnomaly).count() == 1


# ─── 2. Integration test audit-all via TestClient ──────────────────────


def test_audit_all_first_run_returns_200(client, db):
    """1er run audit-all sur DB vide → 200, message FR."""
    org, _, _ = _seed_org_with_invoice(db)
    response = client.post(
        "/api/billing/audit-all",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["audited"] >= 1
    assert "message_fr" in body
    assert "Audit terminé" in body["message_fr"]
    assert "facture" in body["message_fr"]


def test_audit_all_second_run_is_idempotent_no_500(client, db):
    """2e run audit-all → 200, 0 doublon (cardinal P1.5 doctrine)."""
    org, _, _ = _seed_org_with_invoice(db)

    r1 = client.post(
        "/api/billing/audit-all",
        headers={"X-Org-Id": str(org.id)},
    )
    assert r1.status_code == 200
    count_after_1 = db.query(BillAnomaly).count()

    # 2e run — doit être 200, et le compte d'anomalies en DB ne doit PAS augmenter
    r2 = client.post(
        "/api/billing/audit-all",
        headers={"X-Org-Id": str(org.id)},
    )
    assert r2.status_code == 200, f"REGRESSION P1.5 : audit-all renvoie {r2.status_code} sur 2e run"
    count_after_2 = db.query(BillAnomaly).count()
    assert count_after_2 == count_after_1, f"Doublons créés : {count_after_1} → {count_after_2}"

    # Le 2e run ne doit créer que des updates / skips, jamais de created
    body2 = r2.json()
    assert body2["bill_anomalies_created"] == 0, "2e run ne doit créer aucune anomalie"


def test_audit_all_simulated_unique_violation_does_not_crash(client, db):
    """Anomalie pré-existante en DB (simule re-run après crash) → audit-all OK."""
    org, _, invoice = _seed_org_with_invoice(db)

    # Pre-injecte une anomalie pour simuler un état post-crash
    pre_existing = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="info",
        actual_value=Decimal("10.0"),
        details_json={"injected_pre": True},
    )
    db.add(pre_existing)
    db.commit()

    response = client.post(
        "/api/billing/audit-all",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    # Une seule anomalie R19 en DB (pas de doublon)
    r19_count = db.query(BillAnomaly).filter(BillAnomaly.code == "R19").count()
    assert r19_count == 1


def test_audit_all_preserves_resolved_anomalies(client, db):
    """Anomalie résolue par opérateur → SKIP au re-run, note préservée."""
    org, _, invoice = _seed_org_with_invoice(db)

    # 1) opérateur a résolu une anomalie R19 il y a quelques jours
    resolved = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="warning",
        actual_value=Decimal("42.50"),
        details_json={"manual": True},
        resolved_at=datetime.now(timezone.utc),
        resolution_note="Confirmé OK auprès du fournisseur le 2026-05-20.",
    )
    db.add(resolved)
    db.commit()
    original_note = resolved.resolution_note

    # 2) re-run audit-all
    response = client.post(
        "/api/billing/audit-all",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200

    # 3) la note opérateur doit être intacte
    db.refresh(resolved)
    assert resolved.resolution_note == original_note
    assert resolved.resolved_at is not None


def test_audit_all_without_org_context_returns_401_fr(client, db, monkeypatch):
    """Préservation P1 C3 : sans JWT/X-Org-Id + DEMO_MODE off → 401 NO_ORG_CONTEXT FR."""
    import services.scope_utils as scope_utils

    monkeypatch.setattr(scope_utils, "DEMO_MODE", False, raising=True)

    response = client.post("/api/billing/audit-all")
    assert response.status_code == 401, response.text
    detail = response.json().get("detail") or {}
    assert detail.get("code") == "NO_ORG_CONTEXT"
    assert "organisation" in (detail.get("message") or "").lower()


# ─── 3. Sync actions reste idempotente après le fix ────────────────────


def test_sync_actions_from_anomalies_still_idempotent(client, db):
    """Régression P1 C4 : sync-actions reste idempotente après le fix C2 P1.5."""
    org, _, invoice = _seed_org_with_invoice(db)

    # 1) audit-all crée des anomalies
    client.post("/api/billing/audit-all", headers={"X-Org-Id": str(org.id)})

    # 2) 1er sync actions
    r1 = client.post(
        "/api/billing/sync-actions-from-anomalies",
        headers={"X-Org-Id": str(org.id)},
    )
    assert r1.status_code == 200
    summary1 = r1.json()["summary"]

    # 3) 2e sync actions → 0 doublon
    r2 = client.post(
        "/api/billing/sync-actions-from-anomalies",
        headers={"X-Org-Id": str(org.id)},
    )
    assert r2.status_code == 200
    summary2 = r2.json()["summary"]
    assert summary2["created"] == 0, "2e sync ne doit créer aucune action"
    # Tous les items précédemment créés sont skipped_existing
    assert summary2["skipped_existing"] == summary1["created"]


# ─── 4. Message FR ──────────────────────────────────────────────────────


def test_audit_all_message_fr_format(client, db):
    """message_fr suit la doctrine : 'Audit terminé : X factures analysées...'."""
    org, _, _ = _seed_org_with_invoice(db)
    r1 = client.post("/api/billing/audit-all", headers={"X-Org-Id": str(org.id)})
    body1 = r1.json()
    assert body1["message_fr"].startswith("Audit terminé :")
    # Accord singulier/pluriel
    assert "facture" in body1["message_fr"]
    assert "analysée" in body1["message_fr"]

    r2 = client.post("/api/billing/audit-all", headers={"X-Org-Id": str(org.id)})
    body2 = r2.json()
    # 2e run : sur 0 anomalie créée → "0 anomalie créée" (sans 's')
    assert "0 anomalie créée" in body2["message_fr"]
