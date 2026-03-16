"""
PROMEOS — Tests BACS Compliance Gate : statuts prudents, classe, inspections.
Jamais de faux "conforme".
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, Batiment
from models.bacs_models import BacsAsset, BacsCvcSystem, BacsInspection
from models.enums import CvcSystemType, CvcArchitecture, InspectionStatus
from services.bacs_compliance_gate import evaluate_bacs_status


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
    org = Organisation(nom="TestOrg", type_client="tertiaire", actif=True, siren="123456789")
    db.add(org)
    db.flush()
    site = Site(nom="Site BACS", type="bureau", actif=True)
    db.add(site)
    db.flush()
    a = BacsAsset(site_id=site.id, is_tertiary_non_residential=True)
    db.add(a)
    db.flush()
    return a


def _add_system(db, asset_id, system_type, kw, system_class=None, verified=False):
    import json

    s = BacsCvcSystem(
        asset_id=asset_id,
        system_type=system_type,
        architecture=CvcArchitecture.CASCADE,
        units_json=json.dumps([{"label": "Unit 1", "kw": kw}]),
        putile_kw_computed=kw,
        system_class=system_class,
        system_class_source="declaratif" if system_class else None,
        system_class_verified=verified,
    )
    db.add(s)
    db.flush()
    return s


def _add_inspection(db, asset_id, completed=True, critical_findings=0, system_class_observed=None):
    i = BacsInspection(
        asset_id=asset_id,
        inspection_date=date(2024, 6, 1) if completed else None,
        due_next_date=date(2029, 6, 1),
        status=InspectionStatus.COMPLETED if completed else InspectionStatus.SCHEDULED,
        findings_count=critical_findings,
        critical_findings_count=critical_findings,
        system_class_observed=system_class_observed,
    )
    db.add(i)
    db.flush()
    return i


class TestBacsNeverFalseConforme:
    def test_unknown_class_never_compliant(self, db, asset):
        """Classe inconnue => jamais conforme."""
        _add_system(db, asset.id, CvcSystemType.HEATING, 200, system_class=None)
        _add_inspection(db, asset.id)
        result = evaluate_bacs_status(db, asset.id)
        assert result["is_compliant_claim_allowed"] is False
        assert result["bacs_status"] in ("review_required", "in_scope_incomplete")
        assert any("classe" in w.lower() or "GTB" in w for w in result["major_warnings"])

    def test_class_c_never_compliant(self, db, asset):
        """Classe C => non conforme."""
        _add_system(db, asset.id, CvcSystemType.HEATING, 200, system_class="C")
        result = evaluate_bacs_status(db, asset.id)
        assert result["is_compliant_claim_allowed"] is False
        assert any("C ou D" in b for b in result["blockers"])

    def test_no_inspection_never_compliant(self, db, asset):
        """Sans inspection => pas de statut fort."""
        _add_system(db, asset.id, CvcSystemType.HEATING, 200, system_class="A", verified=True)
        result = evaluate_bacs_status(db, asset.id)
        assert result["is_compliant_claim_allowed"] is False
        assert any("inspection" in b.lower() for b in result["blockers"])

    def test_critical_finding_blocks(self, db, asset):
        """Finding critique => review_required."""
        _add_system(db, asset.id, CvcSystemType.HEATING, 200, system_class="A", verified=True)
        _add_inspection(db, asset.id, critical_findings=2)
        result = evaluate_bacs_status(db, asset.id)
        assert result["bacs_status"] == "review_required"
        assert result["is_compliant_claim_allowed"] is False


class TestBacsEligibility:
    def test_non_tertiary_not_applicable(self, db):
        """Batiment non tertiaire => not_applicable."""
        org = Organisation(nom="O", type_client="tertiaire", actif=True, siren="999999999")
        db.add(org)
        db.flush()
        site = Site(nom="S", type="bureau", actif=True)
        db.add(site)
        db.flush()
        a = BacsAsset(site_id=site.id, is_tertiary_non_residential=False)
        db.add(a)
        db.flush()
        result = evaluate_bacs_status(db, a.id)
        assert result["bacs_status"] == "not_applicable"

    def test_below_threshold_not_applicable(self, db, asset):
        """Putile < 70 kW => not_applicable."""
        _add_system(db, asset.id, CvcSystemType.HEATING, 50, system_class="A", verified=True)
        result = evaluate_bacs_status(db, asset.id)
        assert result["bacs_status"] == "not_applicable"

    def test_no_systems_potentially_in_scope(self, db, asset):
        """Pas de systeme CVC => potentially_in_scope."""
        result = evaluate_bacs_status(db, asset.id)
        assert result["bacs_status"] == "potentially_in_scope"


class TestBacsReadyForReview:
    def test_all_conditions_met(self, db, asset):
        """Classe A verifiee + inspection OK + pas de findings => ready_for_internal_review."""
        _add_system(db, asset.id, CvcSystemType.HEATING, 200, system_class="A", verified=True)
        _add_inspection(db, asset.id, critical_findings=0)
        result = evaluate_bacs_status(db, asset.id)
        assert result["bacs_status"] == "ready_for_internal_review"
        assert result["is_compliant_claim_allowed"] is True

    def test_class_b_also_ok(self, db, asset):
        """Classe B est conforme aussi."""
        _add_system(db, asset.id, CvcSystemType.COOLING, 150, system_class="B", verified=True)
        _add_inspection(db, asset.id)
        result = evaluate_bacs_status(db, asset.id)
        assert result["bacs_status"] == "ready_for_internal_review"


class TestBacsSourceTraceability:
    def test_unverified_class_generates_warning(self, db, asset):
        """Classe declarative non verifiee => warning."""
        _add_system(db, asset.id, CvcSystemType.HEATING, 200, system_class="A", verified=False)
        _add_inspection(db, asset.id)
        result = evaluate_bacs_status(db, asset.id)
        assert any("non verifiee" in w.lower() or "declaratif" in w.lower() for w in result["warnings"])

    def test_no_baseline_warning(self, db, asset):
        """Sans baseline performance => warning efficacite."""
        _add_system(db, asset.id, CvcSystemType.HEATING, 200, system_class="A", verified=True)
        _add_inspection(db, asset.id)
        result = evaluate_bacs_status(db, asset.id)
        assert any("baseline" in w.lower() or "efficacite" in w.lower() for w in result["warnings"])
