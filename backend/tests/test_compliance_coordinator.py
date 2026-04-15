"""
PROMEOS — Tests compliance_coordinator.py (Sprint QA XS)
Vérifie que recompute_site_full() appelle les 4 étapes attendues :
  1. compliance_engine.recompute_site()
  1b. dt_trajectory_service.update_site_avancement()
  2. regops.engine.evaluate_site() + persist_assessment()
  3. compliance_score_service.sync_site_unified_score()
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base


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
    yield session
    session.close()


class TestRecomputeSiteFull:
    """Vérifie que recompute_site_full orchestre correctement les 4 étapes."""

    @patch("services.compliance_coordinator.recompute_site")
    @patch("services.dt_trajectory_service.update_site_avancement")
    @patch("regops.engine.evaluate_site")
    @patch("regops.engine.persist_assessment")
    @patch("services.compliance_score_service.sync_site_unified_score")
    def test_all_4_steps_called(
        self, mock_sync, mock_persist, mock_evaluate, mock_avancement, mock_recompute, db_session
    ):
        """Les 4 étapes sont appelées dans l'ordre."""
        mock_recompute.return_value = {"statut_decret_tertiaire": "A_RISQUE"}
        mock_avancement.return_value = 35.0
        mock_summary = MagicMock()
        mock_summary.compliance_score = 72.0
        mock_evaluate.return_value = mock_summary
        mock_sync_result = MagicMock()
        mock_sync_result.score = 72.0
        mock_sync_result.confidence = "high"
        mock_sync.return_value = mock_sync_result

        from services.compliance_coordinator import recompute_site_full

        result = recompute_site_full(db_session, site_id=42)

        mock_recompute.assert_called_once_with(db_session, 42)
        mock_avancement.assert_called_once_with(db_session, 42)
        mock_evaluate.assert_called_once_with(db_session, 42)
        mock_persist.assert_called_once_with(db_session, mock_summary)
        mock_sync.assert_called_once_with(db_session, 42)

    @patch("services.compliance_coordinator.recompute_site")
    @patch("services.dt_trajectory_service.update_site_avancement")
    @patch("regops.engine.evaluate_site")
    @patch("regops.engine.persist_assessment")
    @patch("services.compliance_score_service.sync_site_unified_score")
    def test_avancement_updates_snapshot(
        self, mock_sync, mock_persist, mock_evaluate, mock_avancement, mock_recompute, db_session
    ):
        """L'avancement calculé est injecté dans le snapshot retourné."""
        mock_recompute.return_value = {"avancement_decret_pct": 0.0}
        mock_avancement.return_value = 42.5
        mock_evaluate.side_effect = Exception("RegOps unavailable")
        mock_sync.side_effect = Exception("Score unavailable")

        from services.compliance_coordinator import recompute_site_full

        result = recompute_site_full(db_session, site_id=1)

        assert result["avancement_decret_pct"] == 42.5

    @patch("services.compliance_coordinator.recompute_site")
    @patch("services.dt_trajectory_service.update_site_avancement")
    @patch("regops.engine.evaluate_site")
    @patch("regops.engine.persist_assessment")
    @patch("services.compliance_score_service.sync_site_unified_score")
    def test_step2_failure_does_not_block_step3(
        self, mock_sync, mock_persist, mock_evaluate, mock_avancement, mock_recompute, db_session
    ):
        """Une erreur en étape 2 ne bloque pas l'étape 3."""
        mock_recompute.return_value = {}
        mock_avancement.return_value = None
        mock_evaluate.side_effect = Exception("DB error")
        mock_sync_result = MagicMock()
        mock_sync_result.score = 50.0
        mock_sync_result.confidence = "low"
        mock_sync.return_value = mock_sync_result

        from services.compliance_coordinator import recompute_site_full

        result = recompute_site_full(db_session, site_id=1)

        mock_evaluate.assert_called_once()
        mock_persist.assert_not_called()
        mock_sync.assert_called_once()

    @patch("services.compliance_coordinator.recompute_site")
    @patch("services.dt_trajectory_service.update_site_avancement")
    @patch("regops.engine.evaluate_site")
    @patch("regops.engine.persist_assessment")
    @patch("services.compliance_score_service.sync_site_unified_score")
    def test_avancement_none_keeps_original_snapshot(
        self, mock_sync, mock_persist, mock_evaluate, mock_avancement, mock_recompute, db_session
    ):
        """Si avancement incalculable (None), le snapshot garde sa valeur originale."""
        mock_recompute.return_value = {"avancement_decret_pct": 15.0}
        mock_avancement.return_value = None
        mock_evaluate.side_effect = Exception("skip")
        mock_sync.side_effect = Exception("skip")

        from services.compliance_coordinator import recompute_site_full

        result = recompute_site_full(db_session, site_id=1)

        assert result["avancement_decret_pct"] == 15.0

    @patch("services.compliance_coordinator.recompute_site")
    @patch("services.dt_trajectory_service.update_site_avancement")
    @patch("regops.engine.evaluate_site")
    @patch("regops.engine.persist_assessment")
    @patch("services.compliance_score_service.sync_site_unified_score")
    def test_avancement_failure_graceful(
        self, mock_sync, mock_persist, mock_evaluate, mock_avancement, mock_recompute, db_session
    ):
        """Exception dans update_site_avancement ne bloque pas les étapes suivantes."""
        mock_recompute.return_value = {}
        mock_avancement.side_effect = Exception("trajectory crash")
        mock_summary = MagicMock()
        mock_summary.compliance_score = 60.0
        mock_evaluate.return_value = mock_summary
        mock_sync_result = MagicMock()
        mock_sync_result.score = 60.0
        mock_sync_result.confidence = "medium"
        mock_sync.return_value = mock_sync_result

        from services.compliance_coordinator import recompute_site_full

        result = recompute_site_full(db_session, site_id=1)

        mock_evaluate.assert_called_once()
        mock_sync.assert_called_once()


class TestBulkRecomputeFullChain:
    """V115 step 2 — bulk recompute (portfolio/org) doit propager RegOps + score A.2."""

    @patch("services.compliance_score_service.sync_site_unified_score")
    @patch("regops.engine.persist_assessment")
    @patch("regops.engine.evaluate_site")
    @patch("services.compliance_coordinator.compute_site_snapshot")
    def test_bulk_recompute_runs_regops_and_score_per_site(
        self, mock_snapshot, mock_evaluate, mock_persist, mock_sync, db_session
    ):
        """_bulk_recompute appelle RegOps + score sync pour chaque site."""
        from models import Site
        from services.compliance_coordinator import _bulk_recompute

        mock_snapshot.return_value = {}
        mock_summary = MagicMock(compliance_score=70.0)
        mock_evaluate.return_value = mock_summary
        mock_sync.return_value = MagicMock(score=70.0, confidence="high")

        sites = [
            Site(id=1, nom="A", type="bureau"),
            Site(id=2, nom="B", type="bureau"),
            Site(id=3, nom="C", type="bureau"),
        ]
        for s in sites:
            db_session.add(s)
        db_session.flush()

        _bulk_recompute(db_session, sites)

        assert mock_evaluate.call_count == 3
        assert mock_persist.call_count == 3
        assert mock_sync.call_count == 3

    @patch("services.compliance_score_service.sync_site_unified_score")
    @patch("regops.engine.persist_assessment")
    @patch("regops.engine.evaluate_site")
    @patch("services.compliance_coordinator.compute_site_snapshot")
    def test_bulk_regops_failure_does_not_block_other_sites(
        self, mock_snapshot, mock_evaluate, mock_persist, mock_sync, db_session
    ):
        """Échec RegOps sur 1 site ne bloque pas les autres ni le score sync."""
        from models import Site
        from services.compliance_coordinator import _bulk_recompute

        mock_snapshot.return_value = {}
        mock_evaluate.side_effect = [
            MagicMock(compliance_score=60.0),
            Exception("regops crash"),
            MagicMock(compliance_score=80.0),
        ]
        mock_sync.return_value = MagicMock(score=70.0, confidence="medium")

        sites = [
            Site(id=10, nom="X", type="bureau"),
            Site(id=11, nom="Y", type="bureau"),
            Site(id=12, nom="Z", type="bureau"),
        ]
        for s in sites:
            db_session.add(s)
        db_session.flush()

        _bulk_recompute(db_session, sites)

        assert mock_evaluate.call_count == 3
        assert mock_persist.call_count == 2  # un seul échec
        assert mock_sync.call_count == 3  # score sync tenté pour tous
