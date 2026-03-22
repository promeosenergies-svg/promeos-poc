"""
PROMEOS — Tests workflow derogation BACS (Art. R.175-6).
Boucle : creation → soumission → approbation/rejet → expiration/reouverture.
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
from models.bacs_models import BacsAsset, BacsCvcSystem
from models.bacs_regulatory import BacsExemption
from models.enums import CvcSystemType, CvcArchitecture, BacsExemptionType, BacsExemptionStatus


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


class TestExemptionCreation:
    def test_create_tri_exemption(self, db, asset):
        ex = BacsExemption(
            asset_id=asset.id,
            exemption_type=BacsExemptionType.TRI_NON_VIABLE.value,
            status=BacsExemptionStatus.DRAFT.value,
            motif_detaille="TRI de 12.5 ans depasse le seuil de 10 ans",
            tri_annees=12.5,
            cout_installation_eur=45000.0,
            economies_annuelles_eur=3600.0,
        )
        db.add(ex)
        db.flush()
        assert ex.id is not None
        assert ex.status == "draft"
        assert ex.exemption_type == "tri_non_viable"
        assert ex.tri_annees == 12.5

    def test_create_impossibilite_technique(self, db, asset):
        ex = BacsExemption(
            asset_id=asset.id,
            exemption_type=BacsExemptionType.IMPOSSIBILITE_TECHNIQUE.value,
            status="draft",
            motif_detaille="Architecture CVC incompatible avec systeme GTB",
        )
        db.add(ex)
        db.flush()
        assert ex.exemption_type == "impossibilite_technique"

    def test_create_patrimoine_historique(self, db, asset):
        ex = BacsExemption(
            asset_id=asset.id,
            exemption_type=BacsExemptionType.PATRIMOINE_HISTORIQUE.value,
            status="draft",
            motif_detaille="Batiment classe monument historique (ref. MH-12345)",
        )
        db.add(ex)
        db.flush()
        assert ex.exemption_type == "patrimoine_historique"

    def test_create_mise_en_vente(self, db, asset):
        ex = BacsExemption(
            asset_id=asset.id,
            exemption_type=BacsExemptionType.MISE_EN_VENTE.value,
            status="draft",
            motif_detaille="Batiment en vente, cession prevue Q2 2025",
        )
        db.add(ex)
        db.flush()
        assert ex.exemption_type == "mise_en_vente"


class TestExemptionWorkflow:
    def _make_draft(self, db, asset):
        ex = BacsExemption(
            asset_id=asset.id,
            exemption_type="tri_non_viable",
            status="draft",
            motif_detaille="TRI 14 ans",
            tri_annees=14.0,
        )
        db.add(ex)
        db.flush()
        return ex

    def test_draft_to_submitted(self, db, asset):
        ex = self._make_draft(db, asset)
        ex.status = "submitted"
        ex.date_demande = date.today()
        db.flush()
        assert ex.status == "submitted"
        assert ex.date_demande is not None

    def test_submitted_to_approved(self, db, asset):
        ex = self._make_draft(db, asset)
        ex.status = "submitted"
        ex.date_demande = date.today()
        db.flush()

        # Approbation
        ex.status = "approved"
        ex.date_decision = date.today()
        ex.date_expiration = date(2030, 12, 31)
        ex.decision_reference = "AP-2024-001"
        ex.decision_conditions = "Renouveler l'etude TRI sous 5 ans"
        db.flush()

        assert ex.status == "approved"
        assert ex.decision_reference == "AP-2024-001"
        assert ex.date_expiration == date(2030, 12, 31)

    def test_submitted_to_rejected(self, db, asset):
        ex = self._make_draft(db, asset)
        ex.status = "submitted"
        db.flush()

        ex.status = "rejected"
        ex.date_decision = date.today()
        ex.decision_conditions = "TRI insuffisamment documente"
        db.flush()

        assert ex.status == "rejected"

    def test_approved_to_expired(self, db, asset):
        ex = self._make_draft(db, asset)
        ex.status = "approved"
        ex.date_expiration = date(2024, 1, 1)  # deja expire
        db.flush()

        ex.status = "expired"
        db.flush()
        assert ex.status == "expired"

    def test_rejected_reopened_to_draft(self, db, asset):
        """Apres rejet, on peut reouvrir en brouillon pour corriger."""
        ex = self._make_draft(db, asset)
        ex.status = "rejected"
        db.flush()

        ex.status = "draft"
        db.flush()
        assert ex.status == "draft"

    def test_expired_reopened_for_renewal(self, db, asset):
        """Apres expiration, on peut reouvrir pour renouvellement."""
        ex = self._make_draft(db, asset)
        ex.status = "approved"
        ex.date_expiration = date(2024, 1, 1)
        db.flush()

        ex.status = "expired"
        db.flush()

        ex.status = "draft"
        ex.renouvellement_prevu = True
        db.flush()
        assert ex.status == "draft"
        assert ex.renouvellement_prevu is True


class TestExemptionValidTransitions:
    """Verifie les transitions valides du workflow."""

    def test_valid_transitions_map(self):
        from routes.bacs import VALID_TRANSITIONS

        assert "submitted" in VALID_TRANSITIONS["draft"]
        assert "approved" in VALID_TRANSITIONS["submitted"]
        assert "rejected" in VALID_TRANSITIONS["submitted"]
        assert "expired" in VALID_TRANSITIONS["approved"]
        assert "draft" in VALID_TRANSITIONS["rejected"]
        assert "draft" in VALID_TRANSITIONS["expired"]

    def test_cannot_skip_submit(self):
        from routes.bacs import VALID_TRANSITIONS

        assert "approved" not in VALID_TRANSITIONS["draft"]
        assert "rejected" not in VALID_TRANSITIONS["draft"]

    def test_cannot_approve_after_reject(self):
        from routes.bacs import VALID_TRANSITIONS

        assert "approved" not in VALID_TRANSITIONS["rejected"]


class TestExemptionDocuments:
    def test_documents_json_storage(self, db, asset):
        docs = [
            {"type": "etude_tri", "ref": "DOC-001"},
            {"type": "courrier_prefet", "ref": "DOC-002"},
        ]
        ex = BacsExemption(
            asset_id=asset.id,
            exemption_type="tri_non_viable",
            status="draft",
            motif_detaille="TRI > 10 ans",
            tri_annees=12.0,
            documents_json=json.dumps(docs),
        )
        db.add(ex)
        db.flush()

        loaded_docs = json.loads(ex.documents_json)
        assert len(loaded_docs) == 2
        assert loaded_docs[0]["type"] == "etude_tri"

    def test_file_ref_attachment(self, db, asset):
        ex = BacsExemption(
            asset_id=asset.id,
            exemption_type="patrimoine_historique",
            status="draft",
            motif_detaille="Monument historique",
            file_ref="uploads/bacs/mh_certificat_12345.pdf",
        )
        db.add(ex)
        db.flush()
        assert ex.file_ref == "uploads/bacs/mh_certificat_12345.pdf"


class TestExemptionEdgeCases:
    def test_multiple_exemptions_per_asset(self, db, asset):
        """Un actif peut avoir plusieurs derogations (historique)."""
        for i in range(3):
            db.add(
                BacsExemption(
                    asset_id=asset.id,
                    exemption_type="tri_non_viable",
                    status="expired" if i < 2 else "draft",
                    motif_detaille=f"Derogation #{i + 1}",
                    tri_annees=11.0 + i,
                )
            )
        db.flush()

        count = db.query(BacsExemption).filter(BacsExemption.asset_id == asset.id).count()
        assert count == 3

        active = (
            db.query(BacsExemption).filter(BacsExemption.asset_id == asset.id, BacsExemption.status == "draft").count()
        )
        assert active == 1

    def test_exemption_never_auto_approved(self, db, asset):
        """Une derogation ne doit JAMAIS etre approuvee automatiquement."""
        ex = BacsExemption(
            asset_id=asset.id,
            exemption_type="tri_non_viable",
            status="draft",
            motif_detaille="TRI 15 ans",
            tri_annees=15.0,
        )
        db.add(ex)
        db.flush()

        # Meme avec un TRI > 10 ans, le statut reste draft
        assert ex.status == "draft"
        assert ex.status != "approved"
