"""
PROMEOS — Tests BACS Regulatory Engine complet.
Eligibilite, exigences fonctionnelles, exploitation, inspection, preuves, statut final.
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


def _system(db, asset_id, kw, sys_type=CvcSystemType.HEATING, cls=None, verified=False):
    s = BacsCvcSystem(
        asset_id=asset_id,
        system_type=sys_type,
        architecture=CvcArchitecture.CASCADE,
        units_json=json.dumps([{"label": "U", "kw": kw}]),
        putile_kw_computed=kw,
        system_class=cls,
        system_class_source="declaratif" if cls else None,
        system_class_verified=verified,
    )
    db.add(s)
    db.flush()
    return s


def _full_setup(db, asset_id, kw=200):
    """Setup complet : systeme + exigences + exploitation + inspection + preuves."""
    _system(db, asset_id, kw, cls="A", verified=True)
    # Exigences fonctionnelles toutes OK
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
    # Exploitation
    exp = BacsExploitationStatus(
        asset_id=asset_id,
        written_procedures="ok",
        operator_trained=True,
        control_points_defined=True,
        repair_process_defined=True,
        training_date=date(2024, 1, 1),
    )
    db.add(exp)
    # Inspection
    insp = BacsInspection(
        asset_id=asset_id,
        inspection_date=date(2024, 6, 1),
        due_next_date=date(2029, 6, 1),
        status=InspectionStatus.COMPLETED,
        critical_findings_count=0,
        report_compliant=True,
    )
    db.add(insp)
    # Preuves
    for doc_type in ["attestation_bacs", "rapport_inspection", "consignes", "formation"]:
        db.add(BacsProofDocument(asset_id=asset_id, document_type=doc_type, actor="test"))
    db.flush()


# ── Eligibilite ──────────────────────────────────────────────────────


class TestEligibility:
    def test_above_290_tier1(self, db, asset):
        _system(db, asset.id, 300)
        result = evaluate_full_bacs(db, asset.id)
        assert result["eligibility"]["in_scope"] is True
        assert result["eligibility"]["tier"] == "TIER1_290"

    def test_between_70_290_tier2(self, db, asset):
        _system(db, asset.id, 150)
        result = evaluate_full_bacs(db, asset.id)
        assert result["eligibility"]["tier"] == "TIER2_70"

    def test_below_70_not_applicable(self, db, asset):
        _system(db, asset.id, 50)
        result = evaluate_full_bacs(db, asset.id)
        assert result["final_status"] == "not_applicable"

    def test_renewal_detected(self, db, asset):
        asset.renewal_events_json = json.dumps([{"date": "2024-01-15", "system": "heating", "kw": 200}])
        db.flush()
        _system(db, asset.id, 200)
        result = evaluate_full_bacs(db, asset.id)
        assert result["eligibility"]["renewal"] is True


# ── Exigences fonctionnelles ─────────────────────────────────────────


class TestFunctionalRequirements:
    def test_all_not_demonstrated_by_default(self, db, asset):
        _system(db, asset.id, 200)
        result = evaluate_full_bacs(db, asset.id)
        assert result["functional_requirements"]["coverage_pct"] == 0
        assert result["functional_requirements"]["all_demonstrated"] is False

    def test_missing_zones_blocks(self, db, asset):
        _system(db, asset.id, 200)
        req = BacsFunctionalRequirement(asset_id=asset.id, functional_zones="absent")
        db.add(req)
        db.flush()
        result = evaluate_full_bacs(db, asset.id)
        zones = result["functional_requirements"]["requirements"]["functional_zones"]
        assert zones["status"] == "absent"

    def test_all_ok_passes(self, db, asset):
        _full_setup(db, asset.id)
        result = evaluate_full_bacs(db, asset.id)
        assert result["functional_requirements"]["all_demonstrated"] is True
        assert result["functional_requirements"]["coverage_pct"] == 100


# ── Exploitation ─────────────────────────────────────────────────────


class TestExploitation:
    def test_absent_consignes_blocks(self, db, asset):
        _system(db, asset.id, 200)
        exp = BacsExploitationStatus(asset_id=asset.id, written_procedures="absent")
        db.add(exp)
        db.flush()
        result = evaluate_full_bacs(db, asset.id)
        assert any("consignes" in b.lower() for b in result["exploitation"]["blockers"])

    def test_no_training_blocks(self, db, asset):
        _system(db, asset.id, 200)
        exp = BacsExploitationStatus(asset_id=asset.id, written_procedures="ok", operator_trained=False)
        db.add(exp)
        db.flush()
        result = evaluate_full_bacs(db, asset.id)
        assert any("formation" in b.lower() for b in result["exploitation"]["blockers"])


# ── Inspection ───────────────────────────────────────────────────────


class TestInspection:
    def test_overdue_blocks(self, db, asset):
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
        assert any("retard" in b.lower() for b in result["inspection"]["blockers"])

    def test_non_compliant_report_blocks(self, db, asset):
        _system(db, asset.id, 200)
        i = BacsInspection(
            asset_id=asset.id,
            inspection_date=date(2024, 6, 1),
            due_next_date=date(2029, 6, 1),
            status=InspectionStatus.COMPLETED,
            report_compliant=False,
            critical_findings_count=0,
        )
        db.add(i)
        db.flush()
        result = evaluate_full_bacs(db, asset.id)
        assert any("non conforme" in b.lower() for b in result["inspection"]["blockers"])


# ── Preuves ──────────────────────────────────────────────────────────


class TestProofs:
    def test_missing_proofs_blocks(self, db, asset):
        _system(db, asset.id, 200)
        result = evaluate_full_bacs(db, asset.id)
        assert len(result["proofs"]["missing_types"]) > 0


# ── Statut final ─────────────────────────────────────────────────────


class TestFinalStatus:
    def test_never_compliant(self, db, asset):
        """is_compliant_claim_allowed est TOUJOURS False — par design."""
        _full_setup(db, asset.id)
        result = evaluate_full_bacs(db, asset.id)
        assert result["is_compliant_claim_allowed"] is False  # JAMAIS

    def test_ready_for_review_when_complete(self, db, asset):
        _full_setup(db, asset.id)
        result = evaluate_full_bacs(db, asset.id)
        assert result["final_status"] == "ready_for_internal_review"
        assert len(result["blockers"]) == 0

    def test_review_required_when_functional_missing(self, db, asset):
        _system(db, asset.id, 200, cls="A", verified=True)
        # Pas d'exigences fonctionnelles
        result = evaluate_full_bacs(db, asset.id)
        assert result["final_status"] == "review_required"
        assert any("exigence" in b.lower() or "fonctionnelle" in b.lower() for b in result["blockers"])
