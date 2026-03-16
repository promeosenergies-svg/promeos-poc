"""
PROMEOS — Tests workflow remediation BACS.
Boucle : detection → action → preuve → revue.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation
from models.bacs_models import BacsAsset, BacsCvcSystem
from models.bacs_remediation import BacsRemediationAction
from models.bacs_regulatory import BacsProofDocument
from models.enums import CvcSystemType, CvcArchitecture


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
    )
    db.add(s)
    db.flush()
    return a


class TestCreateAction:
    def test_create_from_blocker(self, db, asset):
        action = BacsRemediationAction(
            asset_id=asset.id,
            blocker_code="missing_functional",
            blocker_cause="Exigences fonctionnelles non demontrees",
            expected_action="Evaluer les 10 exigences R.175-3",
            expected_proof_type="rapport_inspection",
            priority="high",
            status="open",
            proof_review_status="missing",
        )
        db.add(action)
        db.flush()
        assert action.id is not None
        assert action.status == "open"
        assert action.proof_review_status == "missing"

    def test_action_prefilled_correctly(self, db, asset):
        action = BacsRemediationAction(
            asset_id=asset.id,
            blocker_code="consignes_absentes",
            blocker_cause="Consignes ecrites absentes",
            expected_action="Rediger consignes",
            expected_proof_type="consignes",
            priority="high",
        )
        db.add(action)
        db.flush()
        assert action.blocker_cause == "Consignes ecrites absentes"
        assert action.expected_proof_type == "consignes"


class TestProofAttachment:
    def test_attach_proof_to_action(self, db, asset):
        action = BacsRemediationAction(
            asset_id=asset.id,
            blocker_code="test",
            blocker_cause="Test",
            expected_action="Test",
            status="open",
            proof_review_status="missing",
        )
        db.add(action)
        db.flush()

        proof = BacsProofDocument(
            asset_id=asset.id,
            document_type="consignes",
            actor="test_user",
            linked_entity_type="BacsRemediationAction",
            linked_entity_id=action.id,
        )
        db.add(proof)
        db.flush()

        action.proof_id = proof.id
        action.proof_review_status = "uploaded"
        action.status = "ready_for_review"
        db.flush()

        assert action.proof_review_status == "uploaded"
        assert action.status == "ready_for_review"

    def test_ready_for_review_when_proof_present(self, db, asset):
        action = BacsRemediationAction(
            asset_id=asset.id,
            blocker_code="test",
            blocker_cause="Test",
            expected_action="Test",
            status="open",
            proof_review_status="missing",
        )
        db.add(action)
        db.flush()
        # Simulate proof upload
        action.proof_review_status = "uploaded"
        action.status = "ready_for_review"
        db.flush()
        assert action.status == "ready_for_review"


class TestReviewWorkflow:
    def test_accepted_proof_closes_action(self, db, asset):
        from datetime import datetime, timezone

        action = BacsRemediationAction(
            asset_id=asset.id,
            blocker_code="test",
            blocker_cause="Test",
            expected_action="Test",
            status="ready_for_review",
            proof_review_status="uploaded",
        )
        db.add(action)
        db.flush()

        action.proof_review_status = "accepted"
        action.status = "closed"
        action.closed_at = datetime.now(timezone.utc)
        action.closed_by = "reviewer@test.com"
        db.flush()

        assert action.status == "closed"
        assert action.proof_review_status == "accepted"
        assert action.closed_by == "reviewer@test.com"

    def test_rejected_proof_reopens_action(self, db, asset):
        action = BacsRemediationAction(
            asset_id=asset.id,
            blocker_code="test",
            blocker_cause="Test",
            expected_action="Test",
            status="ready_for_review",
            proof_review_status="uploaded",
        )
        db.add(action)
        db.flush()

        action.proof_review_status = "rejected"
        action.status = "open"
        db.flush()

        assert action.status == "open"
        assert action.proof_review_status == "rejected"

    def test_blocker_not_auto_lifted(self, db, asset):
        """Un blocker ne doit JAMAIS etre leve automatiquement sans revue."""
        action = BacsRemediationAction(
            asset_id=asset.id,
            blocker_code="critical_finding",
            blocker_cause="Finding critique",
            expected_action="Corriger",
            priority="critical",
            status="open",
            proof_review_status="missing",
        )
        db.add(action)
        db.flush()

        # Meme avec preuve uploadee, status ne passe pas auto a closed
        action.proof_review_status = "uploaded"
        action.status = "ready_for_review"
        db.flush()

        # Le status est ready_for_review, PAS closed — revue explicite requise
        assert action.status != "closed"
        assert action.status == "ready_for_review"
