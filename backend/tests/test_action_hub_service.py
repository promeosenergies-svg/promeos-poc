"""
PROMEOS — Tests action_hub_service.py (Sprint QA S)
Couvre les 4 builders + sync_actions dedup + capping.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import json
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    ComplianceFinding,
    BillingInsight,
    ActionItem,
    ActionSourceType,
    ActionStatus,
    InsightStatus,
    TypeSite,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organisation(nom="Hub Test Org", siren="111222333")
    session.add(org)
    session.flush()
    ej = EntiteJuridique(nom="Hub EJ", organisation_id=org.id, siren="444555666")
    session.add(ej)
    session.flush()
    pf = Portefeuille(nom="Hub PF", entite_juridique_id=ej.id)
    session.add(pf)
    session.flush()
    site = Site(nom="Hub Site", type=TypeSite.BUREAU, surface_m2=1500, portefeuille_id=pf.id, actif=True)
    session.add(site)
    session.flush()

    yield session
    session.close()


class TestBuildActionsFromCompliance:
    """Vérifie que les ComplianceFinding NOK génèrent des actions."""

    def test_nok_finding_generates_action(self, db_session):
        from services.action_hub_service import build_actions_from_compliance

        site = db_session.query(Site).first()
        org = db_session.query(Organisation).first()
        finding = ComplianceFinding(
            site_id=site.id,
            regulation="bacs",
            rule_id="BACS_POWER",
            status="NOK",
            severity="high",
            evidence="CVC > 290 kW sans GTB",
            insight_status=InsightStatus.OPEN,
        )
        db_session.add(finding)
        db_session.flush()

        actions = build_actions_from_compliance(db_session, org.id, [site.id])

        assert len(actions) >= 1
        assert actions[0]["source_type"] == ActionSourceType.COMPLIANCE
        assert actions[0]["severity"] == "high"
        assert actions[0]["site_id"] == site.id

    def test_false_positive_excluded(self, db_session):
        from services.action_hub_service import build_actions_from_compliance

        site = db_session.query(Site).first()
        org = db_session.query(Organisation).first()
        finding = ComplianceFinding(
            site_id=site.id,
            regulation="bacs",
            rule_id="BACS_TEST",
            status="NOK",
            severity="medium",
            insight_status=InsightStatus.FALSE_POSITIVE,
        )
        db_session.add(finding)
        db_session.flush()

        actions = build_actions_from_compliance(db_session, org.id, [site.id])

        assert len(actions) == 0

    def test_recommended_actions_json_parsed(self, db_session):
        from services.action_hub_service import build_actions_from_compliance

        site = db_session.query(Site).first()
        org = db_session.query(Organisation).first()
        finding = ComplianceFinding(
            site_id=site.id,
            regulation="tertiaire_operat",
            rule_id="DT_TRAJECTORY",
            status="NOK",
            severity="critical",
            evidence="Trajectoire DT insuffisante",
            recommended_actions_json=json.dumps(["Installer sous-compteurs", "Lancer audit"]),
            insight_status=InsightStatus.OPEN,
        )
        db_session.add(finding)
        db_session.flush()

        actions = build_actions_from_compliance(db_session, org.id, [site.id])

        assert len(actions) == 2
        titles = [a["title"] for a in actions]
        assert "Installer sous-compteurs" in titles
        assert "Lancer audit" in titles


class TestBuildActionsFromBilling:
    """Vérifie que les BillingInsight avec recommandations génèrent des actions."""

    def test_billing_insight_generates_action(self, db_session):
        from services.action_hub_service import build_actions_from_billing

        site = db_session.query(Site).first()
        org = db_session.query(Organisation).first()
        insight = BillingInsight(
            site_id=site.id,
            type="shadow_gap",
            severity="high",
            message="Ecart shadow billing 25%",
            estimated_loss_eur=1500.0,
            recommended_actions_json=json.dumps(["Vérifier le contrat"]),
            insight_status=InsightStatus.OPEN,
        )
        db_session.add(insight)
        db_session.flush()

        actions = build_actions_from_billing(db_session, org.id, [site.id])

        assert len(actions) == 1
        assert actions[0]["source_type"] == ActionSourceType.BILLING
        assert actions[0]["estimated_gain_eur"] == 1500.0

    def test_resolved_insight_excluded(self, db_session):
        """Les insights résolus ne génèrent pas d'actions."""
        from services.action_hub_service import build_actions_from_billing

        site = db_session.query(Site).first()
        org = db_session.query(Organisation).first()
        insight = BillingInsight(
            site_id=site.id,
            type="unit_price_high",
            severity="medium",
            message="Prix unitaire élevé",
            recommended_actions_json=json.dumps(["Renégocier"]),
            insight_status=InsightStatus.RESOLVED,
        )
        db_session.add(insight)
        db_session.flush()

        actions = build_actions_from_billing(db_session, org.id, [site.id])

        assert len(actions) == 0

    def test_no_reco_json_excluded(self, db_session):
        """Insight sans recommended_actions_json → pas d'action."""
        from services.action_hub_service import build_actions_from_billing

        site = db_session.query(Site).first()
        org = db_session.query(Organisation).first()
        insight = BillingInsight(
            site_id=site.id,
            type="duplicate_invoice",
            severity="low",
            message="Doublon facture",
            recommended_actions_json=None,
            insight_status=InsightStatus.OPEN,
        )
        db_session.add(insight)
        db_session.flush()

        actions = build_actions_from_billing(db_session, org.id, [site.id])

        assert len(actions) == 0


class TestSyncActionsDedup:
    """Vérifie l'idempotence de sync_actions."""

    def test_sync_creates_then_skips(self, db_session):
        from services.action_hub_service import sync_actions, build_actions_from_compliance

        site = db_session.query(Site).first()
        org = db_session.query(Organisation).first()
        finding = ComplianceFinding(
            site_id=site.id,
            regulation="bacs",
            rule_id="BACS_DEDUP",
            status="NOK",
            severity="high",
            evidence="Test dedup",
            insight_status=InsightStatus.OPEN,
        )
        db_session.add(finding)
        db_session.flush()

        # Premier sync → crée
        r1 = sync_actions(db_session, org.id, triggered_by="test")
        assert r1["created"] > 0

        # Deuxième sync → skip (idempotent)
        r2 = sync_actions(db_session, org.id, triggered_by="test")
        assert r2["created"] == 0
        assert r2["skipped"] > 0

    def test_sync_preserves_workflow_on_update(self, db_session):
        """Si le contenu change mais le status est modifié par l'utilisateur, le status est préservé."""
        from services.action_hub_service import sync_actions

        site = db_session.query(Site).first()
        org = db_session.query(Organisation).first()

        # Créer un finding → sync → action créée
        finding = ComplianceFinding(
            site_id=site.id,
            regulation="bacs",
            rule_id="BACS_WORKFLOW",
            status="NOK",
            severity="medium",
            evidence="Attestation manquante",
            insight_status=InsightStatus.OPEN,
        )
        db_session.add(finding)
        db_session.flush()
        sync_actions(db_session, org.id)

        # L'utilisateur change le status de l'action
        action = db_session.query(ActionItem).filter(ActionItem.source_type == ActionSourceType.COMPLIANCE).first()
        assert action is not None
        action.status = ActionStatus.IN_PROGRESS
        action.owner = "jean@promeos.io"
        db_session.flush()

        # Modifier le finding → re-sync
        finding.severity = "critical"
        finding.evidence = "Attestation manquante — deadline passée"
        db_session.flush()
        r = sync_actions(db_session, org.id)

        # L'action est mise à jour MAIS le status/owner sont préservés
        action_after = (
            db_session.query(ActionItem).filter(ActionItem.source_type == ActionSourceType.COMPLIANCE).first()
        )
        assert action_after.severity == "critical"  # Mis à jour
        assert action_after.status == ActionStatus.IN_PROGRESS  # Préservé
        assert action_after.owner == "jean@promeos.io"  # Préservé
