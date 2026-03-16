"""
PROMEOS — Tests BACS Hardening V1 : alertes, statut external review, preuve durcie.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation
from models.bacs_models import BacsAsset, BacsCvcSystem, BacsInspection
from models.bacs_regulatory import BacsFunctionalRequirement, BacsExploitationStatus, BacsProofDocument
from models.bacs_remediation import BacsRemediationAction
from models.enums import CvcSystemType, CvcArchitecture, InspectionStatus
from services.bacs_alerts import compute_bacs_alerts
from services.bacs_regulatory_engine import evaluate_full_bacs


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def asset(db):
    org = Organisation(nom="O", type_client="tertiaire", actif=True, siren="123456789")
    db.add(org)
    db.flush()
    site = Site(nom="S", type="bureau", actif=True)
    db.add(site)
    db.flush()
    a = BacsAsset(site_id=site.id, is_tertiary_non_residential=True)
    db.add(a)
    db.flush()
    s = BacsCvcSystem(
        asset_id=a.id,
        system_type=CvcSystemType.HEATING,
        architecture=CvcArchitecture.CASCADE,
        units_json=json.dumps([{"label": "U", "kw": 200}]),
        putile_kw_computed=200,
        system_class="A",
        system_class_verified=True,
    )
    db.add(s)
    db.flush()
    return a


def _full_setup(db, asset_id):
    req = BacsFunctionalRequirement(asset_id=asset_id)
    for f in [
        "continuous_monitoring",
        "hourly_timestep",
        "functional_zones",
        "monthly_retention_5y",
        "reference_values",
        "efficiency_loss_detection",
        "interoperability",
        "manual_override",
        "autonomous_management",
        "data_ownership",
    ]:
        setattr(req, f, "ok")
    db.add(req)
    exp = BacsExploitationStatus(
        asset_id=asset_id,
        written_procedures="ok",
        operator_trained=True,
        control_points_defined=True,
        repair_process_defined=True,
        training_date=date.today(),
    )
    db.add(exp)
    insp = BacsInspection(
        asset_id=asset_id,
        inspection_date=date.today(),
        due_next_date=date.today() + timedelta(days=5 * 365),
        status=InspectionStatus.COMPLETED,
        critical_findings_count=0,
        report_compliant=True,
    )
    db.add(insp)
    for doc_type in ["attestation_bacs", "rapport_inspection", "consignes", "formation"]:
        db.add(BacsProofDocument(asset_id=asset_id, document_type=doc_type, actor="test"))
    db.flush()


# ── Alertes ──────────────────────────────────────────────────────────


class TestAlerts:
    def test_inspection_overdue_alert(self, db, asset):
        BacsInspection(
            asset_id=asset.id,
            inspection_date=date(2018, 1, 1),
            due_next_date=date(2023, 1, 1),
            status=InspectionStatus.COMPLETED,
            critical_findings_count=0,
        )
        db.add(
            BacsInspection(
                asset_id=asset.id,
                inspection_date=date(2018, 1, 1),
                due_next_date=date(2023, 1, 1),
                status=InspectionStatus.COMPLETED,
                critical_findings_count=0,
            )
        )
        db.flush()
        alerts = compute_bacs_alerts(db, asset.id)
        overdue = [a for a in alerts if a["type"] == "inspection_overdue"]
        assert len(overdue) >= 1
        assert overdue[0]["severity"] == "critical"

    def test_proof_missing_alert(self, db, asset):
        alerts = compute_bacs_alerts(db, asset.id)
        missing = [a for a in alerts if a["type"] == "proof_missing"]
        assert len(missing) >= 1

    def test_proof_expired_alert(self, db, asset):
        db.add(
            BacsProofDocument(
                asset_id=asset.id,
                document_type="attestation_bacs",
                actor="test",
                valid_until=date.today() - timedelta(days=30),
            )
        )
        db.flush()
        alerts = compute_bacs_alerts(db, asset.id)
        expired = [a for a in alerts if a["type"] == "proof_expired"]
        assert len(expired) >= 1

    def test_action_overdue_alert(self, db, asset):
        db.add(
            BacsRemediationAction(
                asset_id=asset.id,
                blocker_code="test",
                blocker_cause="Test",
                expected_action="Test",
                status="open",
                due_at=date.today() - timedelta(days=10),
            )
        )
        db.flush()
        alerts = compute_bacs_alerts(db, asset.id)
        overdue = [a for a in alerts if a["type"] == "action_overdue"]
        assert len(overdue) >= 1

    def test_training_missing_alert(self, db, asset):
        db.add(BacsExploitationStatus(asset_id=asset.id, operator_trained=False))
        db.flush()
        alerts = compute_bacs_alerts(db, asset.id)
        training = [a for a in alerts if a["type"] == "training_missing"]
        assert len(training) >= 1

    def test_alerts_sorted_by_severity(self, db, asset):
        db.add(
            BacsInspection(
                asset_id=asset.id,
                inspection_date=date(2018, 1, 1),
                due_next_date=date(2023, 1, 1),
                status=InspectionStatus.COMPLETED,
                critical_findings_count=0,
            )
        )
        db.flush()
        alerts = compute_bacs_alerts(db, asset.id)
        if len(alerts) >= 2:
            sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            for i in range(len(alerts) - 1):
                assert sev_order.get(alerts[i]["severity"], 9) <= sev_order.get(alerts[i + 1]["severity"], 9)


# ── Statut ready_for_external_review ─────────────────────────────────


class TestExternalReview:
    def test_ready_for_external_when_complete_no_alerts(self, db, asset):
        """Setup complet + 0 alertes → is_ready_for_external_review = True."""
        _full_setup(db, asset.id)
        result = evaluate_full_bacs(db, asset.id)
        assert result["final_status"] == "ready_for_internal_review"
        assert result["is_ready_for_external_review"] is True

    def test_not_ready_if_alerts_present(self, db, asset):
        """Setup complet mais preuve expiree → is_ready_for_external_review = False."""
        _full_setup(db, asset.id)
        # Ajouter une preuve expiree
        db.add(
            BacsProofDocument(
                asset_id=asset.id,
                document_type="derogation_tri",
                actor="test",
                valid_until=date.today() - timedelta(days=1),
            )
        )
        db.flush()
        result = evaluate_full_bacs(db, asset.id)
        assert result["is_ready_for_external_review"] is False

    def test_never_compliant(self, db, asset):
        """is_compliant_claim_allowed est TOUJOURS False."""
        _full_setup(db, asset.id)
        result = evaluate_full_bacs(db, asset.id)
        assert result["is_compliant_claim_allowed"] is False

    def test_alerts_in_response(self, db, asset):
        """Les alertes sont incluses dans la reponse du moteur."""
        result = evaluate_full_bacs(db, asset.id)
        assert "alerts" in result
        assert "alerts_count" in result
        assert isinstance(result["alerts"], list)
