"""
PROMEOS — Tests intégration endpoint /api/bill-intelligence/anomalies (Sprint C-5 Phase 5.5 fix B4).

Anti-régression cardinal post-audit test-engineer Sprint C-5 :
- Org-scoping vérifié REST (org A ne voit pas anomalies org B)
- Filtres query params (code / severity / resolved) couverts
- Contrat JSON réponse figé

Comble le gap B4 identifié audit Phase 5.5 : endpoint exposé Sprint C-5 Phase 5.1 sans test
intégration → org-scoping non vérifié REST.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _seed_org_with_anomaly(db, siren_suffix, code="R19", severity="warning"):
    """Helper : Org → EJ → Pf → Site → EnergyInvoice → BillAnomaly."""
    from models import (
        BillAnomaly,
        BillingInvoiceStatus,
        EnergyInvoice,
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )

    org = Organisation(nom=f"Org{siren_suffix}", siren=f"60000000{siren_suffix}")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom=f"EJ{siren_suffix}", siren=f"60000000{siren_suffix}", organisation_id=org.id)
    db.add(ej)
    db.flush()
    pf = Portefeuille(nom=f"PF{siren_suffix}", entite_juridique_id=ej.id)
    db.add(pf)
    db.flush()
    site = Site(nom=f"S{siren_suffix}", type=TypeSite.BUREAU, actif=True, portefeuille_id=pf.id)
    db.add(site)
    db.flush()

    invoice = EnergyInvoice(
        site_id=site.id,
        invoice_number=f"INV-{siren_suffix}",
        period_start=datetime(2026, 4, 1, tzinfo=timezone.utc).date(),
        period_end=datetime(2026, 4, 30, tzinfo=timezone.utc).date(),
        total_eur=1500.0,
        energy_kwh=10000,
        status=BillingInvoiceStatus.IMPORTED,
    )
    db.add(invoice)
    db.flush()

    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code=code,
        severity=severity,
        threshold_value=0.01,
        actual_value=12.5,
        details_json={"vnu_total_eur": 12.5, "explanation": "test fixture"},
    )
    db.add(anomaly)
    db.commit()
    return org.id, anomaly.id


def test_endpoint_lists_anomalies_for_scoped_org(app_client):
    """B4-1 : GET /api/bill-intelligence/anomalies retourne les anomalies de l'org scopée."""
    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_a_id, _ = _seed_org_with_anomaly(db, "1")
    finally:
        db.close()

    resp = client.get("/api/bill-intelligence/anomalies", headers={"X-Org-Id": str(org_a_id)})
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "anomalies" in data
    assert data["count"] == 1
    assert data["anomalies"][0]["code"] == "R19"
    assert data["anomalies"][0]["severity"] == "warning"


def test_endpoint_org_scoping_isolates_orgs(app_client):
    """B4-2 CARDINAL : org A ne voit PAS les anomalies de l'org B (anti-IDOR cross-tenant)."""
    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_a_id, _ = _seed_org_with_anomaly(db, "2", code="R19")
        org_b_id, _ = _seed_org_with_anomaly(db, "3", code="R20")
    finally:
        db.close()

    resp_a = client.get("/api/bill-intelligence/anomalies", headers={"X-Org-Id": str(org_a_id)})
    assert resp_a.status_code == 200
    codes_a = {a["code"] for a in resp_a.json()["anomalies"]}
    assert codes_a == {"R19"}, f"Org A doit voir uniquement R19, vu : {codes_a}"

    resp_b = client.get("/api/bill-intelligence/anomalies", headers={"X-Org-Id": str(org_b_id)})
    assert resp_b.status_code == 200
    codes_b = {a["code"] for a in resp_b.json()["anomalies"]}
    assert codes_b == {"R20"}, f"Org B doit voir uniquement R20, vu : {codes_b}"


def test_endpoint_filter_by_code(app_client):
    """B4-3 : filtre query param `code` retourne uniquement les anomalies du code demandé."""
    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_id, _ = _seed_org_with_anomaly(db, "4", code="R19")
        from models import BillAnomaly, EnergyInvoice

        invoice = db.query(EnergyInvoice).first()
        anomaly_r20 = BillAnomaly(
            invoice_id=invoice.id,
            code="R20",
            severity="critical",
            actual_value=15.0,
        )
        db.add(anomaly_r20)
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/bill-intelligence/anomalies?code=R20", headers={"X-Org-Id": str(org_id)})
    assert resp.status_code == 200
    data = resp.json()
    assert all(a["code"] == "R20" for a in data["anomalies"])
    assert len(data["anomalies"]) == 1


def test_endpoint_filter_by_severity_and_resolved(app_client):
    """B4-4 : filtres `severity` + `resolved` cumulables, contrat JSON cardinal."""
    client, SessionLocal = app_client

    db = SessionLocal()
    try:
        org_id, anomaly_id = _seed_org_with_anomaly(db, "5", severity="critical")
        from models import BillAnomaly

        anomaly = db.query(BillAnomaly).get(anomaly_id)
        anomaly.resolved_at = datetime.now(timezone.utc)
        anomaly.resolution_note = "Fournisseur a corrigé"
        db.commit()
    finally:
        db.close()

    resp_resolved = client.get("/api/bill-intelligence/anomalies?resolved=true", headers={"X-Org-Id": str(org_id)})
    assert resp_resolved.status_code == 200
    assert resp_resolved.json()["count"] == 1
    assert resp_resolved.json()["anomalies"][0]["resolved_at"] is not None

    resp_open = client.get("/api/bill-intelligence/anomalies?resolved=false", headers={"X-Org-Id": str(org_id)})
    assert resp_open.status_code == 200
    assert resp_open.json()["count"] == 0

    resp_sev = client.get("/api/bill-intelligence/anomalies?severity=critical", headers={"X-Org-Id": str(org_id)})
    assert resp_sev.status_code == 200
    assert resp_sev.json()["count"] == 1

    anomaly_payload = resp_sev.json()["anomalies"][0]
    expected_keys = {
        "id",
        "invoice_id",
        "code",
        "severity",
        "detected_at",
        "resolved_at",
        "resolution_note",
        "threshold_value",
        "actual_value",
        "details",
    }
    assert set(anomaly_payload.keys()) == expected_keys
