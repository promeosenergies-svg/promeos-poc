"""
PROMEOS — Tests cardinaux Phase 7.7 Sprint C-7 Lot D — Bill Intelligence endpoint polish.

Couvre 3 P2 dettes Sprint C-7 :
- D-Sprint-C7-BillAnomaly-Endpoint-Enum-Validation-001 P2 — Literal["R19","R20"] query params
- D-Sprint-C7-BillAnomaly-Endpoint-Pagination-001 P2 — limit/offset + period_start/end
- D-Sprint-C7-BillIntelligence-KPI-Aggregate-001 P2 — kpi_total_economie_potentielle_eur
"""

from __future__ import annotations


def _seed_org_with_anomaly(db, code="R19", actual_value=10.0, siren_suffix="77001"):
    """Helper : crée Org + EJ + PF + Site + Invoice + Anomaly."""
    from datetime import date

    from models import (
        BillAnomaly,
        EnergyInvoice,
        EntiteJuridique,
        Organisation,
        Portefeuille,
        Site,
        TypeSite,
    )

    org = Organisation(nom=f"OrgPhase77LotD_{siren_suffix}", siren=f"998{siren_suffix}")
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom=f"EJ{siren_suffix}", siren=f"998{siren_suffix}", organisation_id=org.id)
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
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
    )
    db.add(invoice)
    db.flush()
    anomaly = BillAnomaly(
        invoice_id=invoice.id,
        code=code,
        severity="warning",
        threshold_value=0.01,
        actual_value=actual_value,
    )
    db.add(anomaly)
    db.commit()
    return org.id, anomaly.id


def test_phase77_lot_d_endpoint_rejects_invalid_code_with_422(app_client):
    """Phase 7.7 Lot D : code='R99' (hors Literal) → 422 (vs 200 silencieux avant)."""
    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org_with_anomaly(db, siren_suffix="77001")
    finally:
        db.close()

    resp = client.get(
        "/api/bill-intelligence/anomalies?code=R99",
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 422, (
        f"Phase 7.7 Lot D BLOQUANT : code='R99' devrait retourner 422 (Literal validation), got {resp.status_code}"
    )


def test_phase77_lot_d_endpoint_rejects_invalid_severity_with_422(app_client):
    """Phase 7.7 Lot D : severity='URGENT' (hors Literal) → 422."""
    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org_with_anomaly(db, siren_suffix="77002")
    finally:
        db.close()

    resp = client.get(
        "/api/bill-intelligence/anomalies?severity=URGENT",
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 422


def test_phase77_lot_d_endpoint_returns_kpi_total_economie_aggregate(app_client):
    """Phase 7.7 Lot D : KPI `kpi_total_economie_potentielle_eur` = SUM(actual_value) R19."""
    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org_with_anomaly(db, code="R19", actual_value=42.50, siren_suffix="77003")
    finally:
        db.close()

    resp = client.get(
        "/api/bill-intelligence/anomalies",
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "kpi_total_economie_potentielle_eur" in body
    assert body["kpi_total_economie_potentielle_eur"] == 42.50


def test_phase77_lot_d_endpoint_supports_limit_offset_pagination(app_client):
    """Phase 7.7 Lot D : pagination limit=1 + offset=0 retourne 1 anomalie + total_count."""
    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org_with_anomaly(db, siren_suffix="77004")
        # Ajouter 2e anomalie même org (mais invoice différente pour respecter UNIQUE)
        from datetime import date

        from models import BillAnomaly, EnergyInvoice, Site

        site = db.query(Site).filter(Site.nom == "S77004").first()
        invoice2 = EnergyInvoice(
            site_id=site.id,
            invoice_number="INV-77004-2",
            period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28),
        )
        db.add(invoice2)
        db.flush()
        db.add(BillAnomaly(invoice_id=invoice2.id, code="R20", severity="critical", actual_value=15.0))
        db.commit()
    finally:
        db.close()

    resp = client.get(
        "/api/bill-intelligence/anomalies?limit=1&offset=0",
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["total_count"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 0


def test_phase77_lot_d_endpoint_filters_by_period_start_end(app_client):
    """Phase 7.7 Lot D : filtres period_start + period_end limitent résultats date."""
    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org_with_anomaly(db, siren_suffix="77005")
    finally:
        db.close()

    # Invoice période = 2026-01-01 / 2026-01-31 → filtre 2026-02-01+ doit retourner 0
    resp = client.get(
        "/api/bill-intelligence/anomalies?period_start=2026-02-01",
        headers={"X-Org-Id": str(org_id)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["total_count"] == 0


def test_phase77_lot_d_endpoint_accepts_valid_code_r19_r20(app_client):
    """Phase 7.7 Lot D : codes Literal valides R19 + R20 acceptés (200)."""
    client, SessionLocal = app_client
    db = SessionLocal()
    try:
        org_id, _ = _seed_org_with_anomaly(db, code="R19", siren_suffix="77006")
    finally:
        db.close()

    for code in ("R19", "R20"):
        resp = client.get(
            f"/api/bill-intelligence/anomalies?code={code}",
            headers={"X-Org-Id": str(org_id)},
        )
        assert resp.status_code == 200
