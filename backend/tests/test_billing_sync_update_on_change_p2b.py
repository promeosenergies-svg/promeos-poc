"""
PROMEOS — Bill Intelligence P2-B C5 (2026-05-24) :
`POST /api/billing/sync-actions-from-anomalies` met à jour l'action existante
si le montant ou la description ont changé (sans dupliquer).

Doctrine : "Si une anomalie devient valorisable après update, l'action doit
être créée OU mise à jour (montant, description)."

Cas couverts :
- Anomalie non valorisable (is_monetizable=False) → SKIP (déjà P1 C4)
- Update vers valorisable → action créée (transition False→True)
- Double sync sans changement → 0 doublon (héritage idempotence P1)
- Montant change → action existante mise à jour (description rafraîchie)
- Severity bump → priority_bracket rafraîchi
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
from models.v4.action_center_items import ActionCenterItem  # noqa: E402
from models.v4.enums import Domain, Kind  # noqa: E402


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
    org = Organisation(nom="Org P2B", siren="777777777", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="777777777")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site P2B",
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
        invoice_number="INV-P2B-001",
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


# ─── 1. Informative reste ignorée ───────────────────────────────────────


def test_informative_anomaly_does_not_create_action(client, db):
    """Anomalie is_monetizable=False reste skip (régression P1 C4)."""
    org, _, invoice = _seed_org_with_invoice(db)
    db.add(
        BillAnomaly(
            invoice_id=invoice.id,
            code="R017",
            severity="info",
            is_monetizable=False,
            non_monetizable_reason="PDL manquant — non chiffrable.",
        )
    )
    db.commit()
    r = client.post(
        "/api/billing/sync-actions-from-anomalies",
        headers={"X-Org-Id": str(org.id)},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["created"] == 0
    assert body["summary"]["skipped_non_actionable"] == 1


# ─── 2. Transition non-valorisable → valorisable → action créée ─────────


def test_anomaly_becoming_monetizable_creates_action(client, db):
    """Après transition is_monetizable False→True, action créée au sync suivant."""
    org, _, invoice = _seed_org_with_invoice(db)
    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="warning",
        is_monetizable=False,
        non_monetizable_reason="En attente de vérification fournisseur.",
    )
    db.add(anomaly)
    db.commit()

    # 1er sync : skip (non valorisable)
    r1 = client.post(
        "/api/billing/sync-actions-from-anomalies",
        headers={"X-Org-Id": str(org.id)},
    )
    assert r1.json()["summary"]["created"] == 0

    # L'audit re-classifie : devient valorisable avec montant
    anomaly.is_monetizable = True
    anomaly.actual_value = Decimal("123.45")
    anomaly.non_monetizable_reason = None
    db.commit()

    # 2e sync : action créée
    r2 = client.post(
        "/api/billing/sync-actions-from-anomalies",
        headers={"X-Org-Id": str(org.id)},
    )
    body2 = r2.json()
    assert body2["summary"]["created"] == 1
    assert body2["summary"]["skipped_non_actionable"] == 0


# ─── 3. Idempotence (double sync sans changement) ──────────────────────


def test_double_sync_does_not_duplicate(client, db):
    """Régression P1 C4 : 2 syncs successifs → 1 seule action en DB."""
    org, _, invoice = _seed_org_with_invoice(db)
    db.add(
        BillAnomaly(
            invoice_id=invoice.id,
            code="R19",
            severity="warning",
            actual_value=Decimal("42.50"),
            details_json={"vnu_total_eur": 42.50},
        )
    )
    db.commit()

    r1 = client.post("/api/billing/sync-actions-from-anomalies", headers={"X-Org-Id": str(org.id)})
    n_after_1 = (
        db.query(ActionCenterItem)
        .filter(
            ActionCenterItem.domain == Domain.FACTURATION.value,
            ActionCenterItem.kind == Kind.ANOMALY.value,
        )
        .count()
    )

    r2 = client.post("/api/billing/sync-actions-from-anomalies", headers={"X-Org-Id": str(org.id)})
    n_after_2 = (
        db.query(ActionCenterItem)
        .filter(
            ActionCenterItem.domain == Domain.FACTURATION.value,
            ActionCenterItem.kind == Kind.ANOMALY.value,
        )
        .count()
    )

    assert r1.status_code == 200 and r2.status_code == 200
    assert n_after_2 == n_after_1, "2e sync ne doit pas dupliquer"


# ─── 4. Montant change → action existante rafraîchie ────────────────────


def test_amount_change_updates_existing_action(client, db):
    """Si le montant change entre 2 syncs, description + priorité rafraîchis."""
    org, _, invoice = _seed_org_with_invoice(db)
    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="warning",
        actual_value=Decimal("42.50"),
        details_json={"vnu_total_eur": 42.50},
    )
    db.add(anomaly)
    db.commit()

    # 1er sync
    r1 = client.post("/api/billing/sync-actions-from-anomalies", headers={"X-Org-Id": str(org.id)})
    assert r1.json()["summary"]["created"] == 1
    item = db.query(ActionCenterItem).filter(ActionCenterItem.domain == Domain.FACTURATION.value).first()
    original_id = item.id
    original_desc = item.description

    # Le montant augmente significativement + severity bump
    anomaly.actual_value = Decimal("999.00")
    anomaly.severity = "critical"
    db.commit()

    # 2e sync → action updated (pas dupliquée)
    r2 = client.post("/api/billing/sync-actions-from-anomalies", headers={"X-Org-Id": str(org.id)})
    body2 = r2.json()
    assert body2["summary"]["created"] == 0, "Pas de nouvelle action"
    assert body2["summary"]["updated"] >= 1, "Action existante mise à jour"

    # Vérif DB : même id, nouvelle description, priorité bump
    items = db.query(ActionCenterItem).filter(ActionCenterItem.domain == Domain.FACTURATION.value).all()
    assert len(items) == 1, "Toujours 1 seule action en DB"
    refreshed = items[0]
    assert refreshed.id == original_id
    assert refreshed.description != original_desc, "Description doit avoir changé"
    assert "999" in refreshed.description
    assert refreshed.priority_bracket == "P0", "severity=critical → P0"


# ─── 5. Sync update n'efface pas une action clôturée ───────────────────


def test_closed_action_not_revived_by_update(client, db):
    """Action clôturée par opérateur ne ressuscite jamais (même si montant change)."""
    from datetime import datetime as _dt
    from models.v4.enums import LifecycleState, ClosureReason

    org, _, invoice = _seed_org_with_invoice(db)
    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code="R19",
        severity="warning",
        actual_value=Decimal("100.0"),
        details_json={},
    )
    db.add(anomaly)
    db.commit()

    # Crée + clôt l'action
    client.post("/api/billing/sync-actions-from-anomalies", headers={"X-Org-Id": str(org.id)})
    item = db.query(ActionCenterItem).filter(ActionCenterItem.domain == Domain.FACTURATION.value).first()
    item.lifecycle_state = LifecycleState.CLOSED.value
    item.closed_at = _dt.now(timezone.utc)
    item.closure_reason = ClosureReason.RESOLVED.value
    db.commit()

    # Le montant change → on re-sync. L'item clos ne doit ni revivre ni être mis à jour.
    anomaly.actual_value = Decimal("999.0")
    db.commit()
    r = client.post("/api/billing/sync-actions-from-anomalies", headers={"X-Org-Id": str(org.id)})
    body = r.json()
    assert body["summary"]["created"] == 0
    assert body["summary"]["updated"] == 0
    assert body["summary"]["skipped_resolved_user"] >= 1

    refreshed = db.query(ActionCenterItem).filter_by(id=item.id).first()
    assert refreshed.lifecycle_state == LifecycleState.CLOSED.value
