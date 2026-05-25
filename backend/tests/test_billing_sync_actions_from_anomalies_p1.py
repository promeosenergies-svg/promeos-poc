"""
PROMEOS — Bill Intelligence P1 C4 (2026-05-24) :
`POST /api/billing/sync-actions-from-anomalies` — ferme la boucle
anomalie facture → ActionCenterItem (litige).

Vérifie :
- Création nominale : anomalies valorisables → ActionCenterItem créé
- Replay idempotent : 2 appels → 0 doublon
- Anomalie informative (is_monetizable=False) → SKIP
- Anomalie résolue (resolved_at NOT NULL) → SKIP
- Item clos par utilisateur → SKIP, jamais re-créé
- Sans JWT/X-Org-Id → 401 NO_ORG_CONTEXT FR
- Idempotency-Key UUID v4 valide accepté
- Idempotency-Key non-UUID → 400 FR
"""

from __future__ import annotations

import os
import sys
import uuid
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
from models.v4.action_center_items import ActionCenterItem  # noqa: E402
from models.v4.enums import Domain, Kind, LifecycleState  # noqa: E402


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


def _seed_org_with_anomalies(
    db,
    *,
    n_monetizable: int = 2,
    n_informative: int = 1,
    n_resolved: int = 1,
):
    """Crée 1 org + N anomalies sur des factures distinctes."""
    org = Organisation(nom="Org C4", siren="444444444", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="444444444")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site C4",
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        actif=True,
    )
    db.add(site)
    db.flush()

    anomalies_created = []
    counter = [0]

    def _add_anomaly(**kwargs):
        counter[0] += 1
        invoice = EnergyInvoice(
            site_id=site.id,
            invoice_number=f"INV-{counter[0]:03d}",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            issue_date=date(2026, 5, 5),
            total_eur=1000.0,
            energy_kwh=5000,
            source="manual",
        )
        db.add(invoice)
        db.flush()
        defaults = {
            "code": "R19",
            "severity": "warning",
            "actual_value": Decimal("42.50"),
            "is_monetizable": True,
        }
        defaults.update(kwargs)
        anomaly = BillAnomaly(invoice_id=invoice.id, **defaults)
        db.add(anomaly)
        db.flush()
        anomalies_created.append(anomaly)
        return anomaly

    for _ in range(n_monetizable):
        _add_anomaly()
    for _ in range(n_informative):
        _add_anomaly(
            code="R017",
            severity="info",
            actual_value=None,
            is_monetizable=False,
            non_monetizable_reason="PDL manquant — non chiffrable",
        )
    for _ in range(n_resolved):
        _add_anomaly(resolved_at=datetime.now(timezone.utc))

    db.commit()
    return org, anomalies_created


# ─── Création nominale ─────────────────────────────────────────────────


def test_sync_creates_actions_for_monetizable_open_anomalies(client, db):
    """Anomalies valorisables ouvertes → ActionCenterItem créés."""
    org, _ = _seed_org_with_anomalies(db, n_monetizable=3, n_informative=1, n_resolved=1)
    response = client.post(
        "/api/billing/sync-actions-from-anomalies",
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"]["created"] == 3
    assert body["summary"]["skipped_non_actionable"] == 1
    assert body["summary"]["skipped_resolved_anomaly"] == 1

    # Vérif DB
    items = (
        db.query(ActionCenterItem)
        .filter(
            ActionCenterItem.organisation_id == org.id,
            ActionCenterItem.domain == Domain.FACTURATION.value,
            ActionCenterItem.kind == Kind.ANOMALY.value,
        )
        .all()
    )
    assert len(items) == 3
    # Titres déterministes
    for item in items:
        assert item.title.startswith("Litige facture — anomalie #")
        assert "EXTERNAL_REF: billing_anomaly:" in (item.description or "")


# ─── Idempotence ──────────────────────────────────────────────────────


def test_sync_replay_does_not_duplicate(client, db):
    """2e appel sans changement → 0 doublon (skipped_existing)."""
    org, _ = _seed_org_with_anomalies(db, n_monetizable=2, n_informative=0, n_resolved=0)
    r1 = client.post(
        "/api/billing/sync-actions-from-anomalies",
        headers={"X-Org-Id": str(org.id)},
    )
    assert r1.status_code == 200
    assert r1.json()["summary"]["created"] == 2
    count_after_1 = db.query(ActionCenterItem).count()

    r2 = client.post(
        "/api/billing/sync-actions-from-anomalies",
        headers={"X-Org-Id": str(org.id)},
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["summary"]["created"] == 0
    assert body2["summary"]["skipped_existing"] == 2
    count_after_2 = db.query(ActionCenterItem).count()
    assert count_after_2 == count_after_1


# ─── Item clos jamais re-créé ─────────────────────────────────────────


def test_closed_item_not_recreated(client, db):
    """L'utilisateur a clos un item → 2e sync ne le re-crée pas."""
    from models.v4.enums import ClosureReason

    org, _ = _seed_org_with_anomalies(db, n_monetizable=1, n_informative=0, n_resolved=0)
    r1 = client.post(
        "/api/billing/sync-actions-from-anomalies",
        headers={"X-Org-Id": str(org.id)},
    )
    item_id = r1.json()["created"][0]["id"]

    # Clôture manuelle
    item = db.query(ActionCenterItem).filter_by(id=uuid.UUID(item_id)).first()
    item.lifecycle_state = LifecycleState.CLOSED.value
    item.closed_at = datetime.now(timezone.utc)
    item.closure_reason = ClosureReason.RESOLVED.value
    db.commit()

    count_before = db.query(ActionCenterItem).count()
    r2 = client.post(
        "/api/billing/sync-actions-from-anomalies",
        headers={"X-Org-Id": str(org.id)},
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["summary"]["skipped_resolved_user"] >= 1
    assert db.query(ActionCenterItem).count() == count_before


# ─── Idempotency-Key ───────────────────────────────────────────────────


def test_idempotency_key_valid_uuid_accepted(client, db):
    """UUID v4 valide → 200."""
    org, _ = _seed_org_with_anomalies(db, n_monetizable=1, n_informative=0, n_resolved=0)
    response = client.post(
        "/api/billing/sync-actions-from-anomalies",
        params={"idempotency_key": str(uuid.uuid4())},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 200


def test_idempotency_key_invalid_returns_400(client, db):
    """Non-UUID → 400 + code FR."""
    org, _ = _seed_org_with_anomalies(db, n_monetizable=1, n_informative=0, n_resolved=0)
    response = client.post(
        "/api/billing/sync-actions-from-anomalies",
        params={"idempotency_key": "not-a-uuid"},
        headers={"X-Org-Id": str(org.id)},
    )
    assert response.status_code == 400
    detail = response.json().get("detail") or {}
    assert detail.get("code") == "IDEMPOTENCY_KEY_INVALID"
    assert "UUID" in detail.get("message", "")


# ─── No org context ───────────────────────────────────────────────────


def test_sync_without_org_context_returns_401_fr(client, db, monkeypatch):
    """Sans JWT/X-Org-Id + DEMO_MODE off → 401 NO_ORG_CONTEXT FR."""
    import services.scope_utils as scope_utils

    monkeypatch.setattr(scope_utils, "DEMO_MODE", False, raising=True)

    response = client.post("/api/billing/sync-actions-from-anomalies")
    assert response.status_code == 401, response.text
    detail = response.json().get("detail") or {}
    assert detail.get("code") == "NO_ORG_CONTEXT"
    assert "organisation" in detail.get("message", "").lower()
