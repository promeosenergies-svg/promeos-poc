"""
PROMEOS - Tests for BACS Ops Monitoring
6 tests covering KPIs, consumption linkage, and API endpoint.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from models import (
    Base, Site, TypeSite,
    BacsAsset, BacsCvcSystem, BacsAssessment, BacsInspection,
    CvcSystemType, CvcArchitecture, BacsTriggerReason, InspectionStatus,
    ConsumptionInsight,
)
from services.bacs_ops_monitor import (
    compute_bacs_ops_kpis, link_consumption_findings, get_bacs_ops_panel,
)
from services.bacs_engine import evaluate_bacs


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed(db, cvc_kw=300, deadline=None, inspection_date=None):
    site = Site(id=1, nom="Test", type=TypeSite.BUREAU)
    db.add(site)
    db.flush()
    asset = BacsAsset(site_id=1, is_tertiary_non_residential=True, pc_date=date(2000, 1, 1))
    db.add(asset)
    db.flush()
    sys = BacsCvcSystem(
        asset_id=asset.id,
        system_type=CvcSystemType.HEATING,
        architecture=CvcArchitecture.CASCADE,
        units_json=json.dumps([{"label": "PAC", "kw": cvc_kw}]),
    )
    db.add(sys)
    db.flush()
    # Evaluate to create assessment
    evaluate_bacs(db, 1)
    if inspection_date:
        insp = BacsInspection(
            asset_id=asset.id,
            inspection_date=inspection_date,
            status=InspectionStatus.COMPLETED,
            report_ref="RPT-001",
        )
        db.add(insp)
        db.flush()
    return site, asset


class TestBacsOpsKpis:

    def test_kpis_with_deadline(self, db):
        _seed(db, cvc_kw=450)
        kpis = compute_bacs_ops_kpis(db, 1)
        assert kpis["is_obligated"] is True
        assert kpis["compliance_delay_days"] is not None

    def test_kpis_inspection_countdown(self, db):
        _seed(db, cvc_kw=450, inspection_date=date(2023, 1, 1))
        kpis = compute_bacs_ops_kpis(db, 1)
        assert kpis["inspection_countdown_days"] is not None

    def test_kpis_no_asset(self, db):
        site = Site(id=1, nom="Empty", type=TypeSite.BUREAU)
        db.add(site)
        db.flush()
        kpis = compute_bacs_ops_kpis(db, 1)
        assert "error" in kpis


class TestConsumptionLinkage:

    def test_link_hors_horaires(self, db):
        _seed(db, cvc_kw=300)
        ins = ConsumptionInsight(site_id=1, type="hors_horaires", severity="high", message="58% hors horaires")
        db.add(ins)
        db.flush()
        findings = link_consumption_findings(db, 1)
        assert len(findings) >= 1
        hh = [f for f in findings if "hors_horaires" in (f.get("type") or "")]
        assert len(hh) >= 1
        assert hh[0]["bacs_context"] is not None

    def test_link_derive(self, db):
        _seed(db, cvc_kw=300)
        ins = ConsumptionInsight(site_id=1, type="derive", severity="medium", message="Derive +8%")
        db.add(ins)
        db.flush()
        findings = link_consumption_findings(db, 1)
        derive = [f for f in findings if "derive" in (f.get("type") or "")]
        assert derive[0]["bacs_context"] is not None


class TestBacsOpsPanel:

    def test_full_panel(self, db):
        _seed(db, cvc_kw=450)
        panel = get_bacs_ops_panel(db, 1)
        assert "kpis" in panel
        assert "consumption_findings" in panel
        assert "monthly_consumption" in panel
        assert "hourly_heatmap" in panel
        assert "cvc_alerts_stub" in panel
        assert len(panel["cvc_alerts_stub"]) == 3


class TestBacsOpsApi:

    def test_ops_endpoint(self):
        from main import app
        from database import get_db

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        def _override():
            try:
                yield session
            finally:
                pass

        app.dependency_overrides[get_db] = _override
        client = TestClient(app)

        # Create site + asset
        site = Site(nom="OpsTest", type=TypeSite.BUREAU)
        session.add(site)
        session.flush()
        asset = BacsAsset(site_id=site.id, is_tertiary_non_residential=True, pc_date=date(2000, 1, 1))
        session.add(asset)
        session.flush()
        sys = BacsCvcSystem(
            asset_id=asset.id,
            system_type=CvcSystemType.HEATING,
            architecture=CvcArchitecture.CASCADE,
            units_json=json.dumps([{"kw": 300}]),
        )
        session.add(sys)
        session.flush()
        evaluate_bacs(session, site.id)

        r = client.get(f"/api/regops/bacs/site/{site.id}/ops")
        assert r.status_code == 200
        data = r.json()
        assert "kpis" in data

        app.dependency_overrides.clear()
        session.close()
