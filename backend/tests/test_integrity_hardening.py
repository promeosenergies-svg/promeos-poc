"""
PROMEOS — Tests integrity hardening : reevaluation, coherence, recalcul CVC.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, Batiment, TertiaireEfa
from models.bacs_models import BacsAsset, BacsCvcSystem, BacsAssessment
from models.tertiaire import TertiaireEfaBuilding
from models.enums import CvcSystemType, CvcArchitecture
from services.patrimoine_conformite_sync import (
    reevaluate_on_usage_change,
    run_coherence_check,
    auto_recompute_bacs,
)


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
def setup(db):
    org = Organisation(nom="O", type_client="tertiaire", actif=True, siren="123456789")
    db.add(org)
    db.flush()
    site = Site(nom="S", type="bureau", actif=True, surface_m2=1000)
    db.add(site)
    db.flush()
    bat = Batiment(site_id=site.id, nom="B", surface_m2=1000)
    db.add(bat)
    db.flush()
    efa = TertiaireEfa(org_id=org.id, site_id=site.id, nom="EFA", trajectory_status="on_track")
    db.add(efa)
    db.flush()
    eb = TertiaireEfaBuilding(efa_id=efa.id, building_id=bat.id, surface_m2=1000, usage_label="Bureaux")
    db.add(eb)
    db.flush()
    asset = BacsAsset(site_id=site.id, is_tertiary_non_residential=True, bacs_scope_status="ready_for_internal_review")
    db.add(asset)
    db.flush()
    return {"org": org, "site": site, "bat": bat, "efa": efa, "eb": eb, "asset": asset}


# ── Reevaluation usage ───────────────────────────────────────────────


class TestReevaluation:
    def test_usage_change_flags_efa(self, db, setup):
        """Changement usage → EFA trajectory_status = review_required."""
        result = reevaluate_on_usage_change(db, setup["site"].id)
        db.flush()
        db.refresh(setup["efa"])
        assert setup["efa"].trajectory_status == "review_required"
        assert result["efa_flagged"] == 1

    def test_usage_change_flags_bacs(self, db, setup):
        """Changement usage → BACS scope_status = review_required."""
        result = reevaluate_on_usage_change(db, setup["site"].id)
        db.flush()
        db.refresh(setup["asset"])
        assert setup["asset"].bacs_scope_status == "review_required"
        assert result["bacs_flagged"] == 1

    def test_not_applicable_not_flagged(self, db, setup):
        """BacsAsset not_applicable ne doit pas etre flag."""
        setup["asset"].bacs_scope_status = "not_applicable"
        db.flush()
        result = reevaluate_on_usage_change(db, setup["site"].id)
        db.refresh(setup["asset"])
        assert setup["asset"].bacs_scope_status == "not_applicable"
        assert result["bacs_flagged"] == 0


# ── Job coherence ────────────────────────────────────────────────────


class TestCoherence:
    def test_clean_state_with_assessment(self, db, setup):
        """Etat propre avec assessment recent → status = clean."""
        from datetime import datetime, timezone

        # Ajouter un assessment recent pour eviter BACS stale
        a = BacsAssessment(asset_id=setup["asset"].id, assessed_at=datetime.now(timezone.utc), is_obligated=False)
        db.add(a)
        db.flush()
        result = run_coherence_check(db)
        assert result["status"] == "clean"
        assert result["total_issues"] == 0

    def test_detects_surface_desync(self, db, setup):
        """Surface divergente → detectee."""
        setup["bat"].surface_m2 = 1500  # Diverge avec EfaBuilding (1000)
        db.flush()
        result = run_coherence_check(db)
        assert len(result["surface_desyncs"]) >= 1
        assert result["status"] == "issues_detected"

    def test_detects_orphan_in_coherence(self, db, setup):
        """Site archive → orphelin detecte dans coherence."""
        setup["site"].soft_delete()
        db.flush()
        result = run_coherence_check(db)
        assert result["total_issues"] >= 1


# ── Recalcul BACS sur CVC ───────────────────────────────────────────


class TestAutoRecompute:
    def test_recompute_returns_true_if_asset_exists(self, db, setup):
        """auto_recompute_bacs retourne True si asset existe."""
        # Ajouter un systeme CVC pour que le moteur ait quelque chose a evaluer
        s = BacsCvcSystem(
            asset_id=setup["asset"].id,
            system_type=CvcSystemType.HEATING,
            architecture=CvcArchitecture.CASCADE,
            units_json=json.dumps([{"label": "U", "kw": 200}]),
            putile_kw_computed=200,
        )
        db.add(s)
        db.flush()
        result = auto_recompute_bacs(db, setup["site"].id)
        assert result is True

    def test_recompute_returns_false_if_no_asset(self, db):
        """auto_recompute_bacs retourne False si pas d'asset."""
        org = Organisation(nom="O2", type_client="tertiaire", actif=True, siren="987654321")
        db.add(org)
        db.flush()
        site = Site(nom="S2", type="bureau", actif=True)
        db.add(site)
        db.flush()
        result = auto_recompute_bacs(db, site.id)
        assert result is False
