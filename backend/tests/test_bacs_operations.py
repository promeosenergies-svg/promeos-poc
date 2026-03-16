"""
PROMEOS — Tests BACS Operations : remediation, alertes, workflow.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation
from models.bacs_models import BacsAsset, BacsCvcSystem, BacsInspection
from models.bacs_regulatory import BacsFunctionalRequirement, BacsExploitationStatus, BacsProofDocument
from models.enums import CvcSystemType, CvcArchitecture, InspectionStatus
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
    return a


def _system(db, asset_id, kw):
    s = BacsCvcSystem(
        asset_id=asset_id,
        system_type=CvcSystemType.HEATING,
        architecture=CvcArchitecture.CASCADE,
        units_json=json.dumps([{"label": "U", "kw": kw}]),
        putile_kw_computed=kw,
    )
    db.add(s)
    db.flush()


class TestRemediation:
    def test_remediation_for_missing_functional(self, db, asset):
        """Exigences manquantes => remediation avec cause + action."""
        _system(db, asset.id, 200)
        result = evaluate_full_bacs(db, asset.id)
        assert len(result["remediation"]) > 0
        causes = [r["cause"] for r in result["remediation"]]
        assert any("R.175-3" in c or "fonctionnelle" in c for c in causes)

    def test_remediation_for_missing_consignes(self, db, asset):
        """Consignes absentes => remediation specifique."""
        _system(db, asset.id, 200)
        exp = BacsExploitationStatus(asset_id=asset.id, written_procedures="absent")
        db.add(exp)
        db.flush()
        result = evaluate_full_bacs(db, asset.id)
        causes = [r["cause"] for r in result["remediation"]]
        assert any("consignes" in c.lower() for c in causes)

    def test_remediation_for_no_inspection(self, db, asset):
        """Inspection absente => remediation critique."""
        _system(db, asset.id, 200)
        result = evaluate_full_bacs(db, asset.id)
        priorities = [r["priority"] for r in result["remediation"]]
        assert "critical" in priorities or "high" in priorities

    def test_remediation_for_missing_proofs(self, db, asset):
        """Preuves manquantes => remediation avec details."""
        _system(db, asset.id, 200)
        result = evaluate_full_bacs(db, asset.id)
        proof_rems = [r for r in result["remediation"] if "preuve" in r["cause"].lower()]
        assert len(proof_rems) > 0

    def test_remediation_ordered_by_priority(self, db, asset):
        """Remediation ordonnee par priorite (critical > high > medium)."""
        _system(db, asset.id, 200)
        result = evaluate_full_bacs(db, asset.id)
        priorities = [r["priority"] for r in result["remediation"]]
        priority_order = {"critical": 0, "high": 1, "medium": 2}
        for i in range(len(priorities) - 1):
            assert priority_order.get(priorities[i], 3) <= priority_order.get(priorities[i + 1], 3)


class TestAlerts:
    def test_overdue_inspection_alert(self, db, asset):
        """Inspection en retard => blocker visible."""
        _system(db, asset.id, 200)
        i = BacsInspection(
            asset_id=asset.id,
            inspection_date=date(2018, 1, 1),
            due_next_date=date(2023, 1, 1),
            status=InspectionStatus.COMPLETED,
            critical_findings_count=0,
        )
        db.add(i)
        db.flush()
        result = evaluate_full_bacs(db, asset.id)
        assert any("retard" in b.lower() for b in result["blockers"])
        assert result["final_status"] == "review_required"

    def test_missing_training_alert(self, db, asset):
        """Formation absente => blocker dans exploitation."""
        _system(db, asset.id, 200)
        exp = BacsExploitationStatus(
            asset_id=asset.id,
            written_procedures="ok",
            operator_trained=False,
        )
        db.add(exp)
        db.flush()
        result = evaluate_full_bacs(db, asset.id)
        assert any("formation" in b.lower() for b in result["blockers"])


class TestWorkflow:
    def test_critical_finding_impacts_final(self, db, asset):
        """Finding critique dans inspection => review_required."""
        _system(db, asset.id, 200)
        # Setup complet SAUF inspection avec finding critique
        req = BacsFunctionalRequirement(asset_id=asset.id)
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
            asset_id=asset.id,
            written_procedures="ok",
            operator_trained=True,
            control_points_defined=True,
            repair_process_defined=True,
        )
        db.add(exp)
        i = BacsInspection(
            asset_id=asset.id,
            inspection_date=date(2024, 6, 1),
            due_next_date=date(2029, 6, 1),
            status=InspectionStatus.COMPLETED,
            critical_findings_count=2,
            report_compliant=True,
        )
        db.add(i)
        for doc_type in ["attestation_bacs", "rapport_inspection", "consignes", "formation"]:
            db.add(BacsProofDocument(asset_id=asset.id, document_type=doc_type, actor="test"))
        db.flush()
        result = evaluate_full_bacs(db, asset.id)
        assert result["final_status"] == "review_required"
        assert any("critique" in b.lower() for b in result["blockers"])
