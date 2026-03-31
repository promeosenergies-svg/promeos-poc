"""
PROMEOS - V69 CEE Pipeline + M&V Tests
Tests: create_cee_dossier, kanban step advance, mv_summary, work packages.
"""

import json
import os
import pytest
from datetime import date
from unittest.mock import MagicMock, patch, PropertyMock

from models import (
    Site,
    Batiment,
    Obligation,
    Evidence,
    ActionItem,
    TypeObligation,
    StatutConformite,
    TypeEvidence,
    StatutEvidence,
    TypeSite,
    ActionSourceType,
    ActionStatus,
)
from models.cee_models import WorkPackage, CeeDossier, CeeDossierEvidence
from models.enums import WorkPackageSize, CeeDossierStep, CeeStatus, MVAlertType
from services.cee_service import (
    create_cee_dossier,
    advance_cee_step,
    compute_mv_summary,
    get_site_work_packages,
    _CEE_EVIDENCE_TEMPLATE,
)


# ── Helpers ──────────────────────────────────────────────────


def _make_site(**kwargs):
    defaults = dict(
        id=1,
        nom="Bureau Test",
        type=TypeSite.BUREAU,
        tertiaire_area_m2=1500,
        annual_kwh_total=120000,
        operat_status="submitted",
        parking_area_m2=2000,
        roof_area_m2=800,
        parking_type=None,
        is_multi_occupied=False,
        naf_code=None,
        surface_m2=None,
        statut_decret_tertiaire=StatutConformite.A_RISQUE,
        statut_bacs=StatutConformite.A_RISQUE,
        avancement_decret_pct=0.0,
        anomalie_facture=False,
        action_recommandee=None,
        risque_financier_euro=0.0,
        last_energy_update_at=None,
        portefeuille_id=1,
    )
    defaults.update(kwargs)
    site = MagicMock(spec=Site)
    for k, v in defaults.items():
        setattr(site, k, v)
    return site


def _make_work_package(id=1, site_id=1, **kwargs):
    defaults = dict(
        label="Isolation combles",
        size=WorkPackageSize.M,
        capex_eur=25000,
        savings_eur_year=5000,
        payback_years=5.0,
        complexity="medium",
        cee_status=CeeStatus.A_QUALIFIER,
        description=None,
        created_at=None,
    )
    defaults.update(kwargs)
    wp = MagicMock(spec=WorkPackage)
    wp.id = id
    wp.site_id = site_id
    for k, v in defaults.items():
        setattr(wp, k, v)
    return wp


def _make_obligation(site_id=1, type_=TypeObligation.BACS, statut=StatutConformite.A_RISQUE, echeance=None):
    o = MagicMock(spec=Obligation)
    o.site_id = site_id
    o.type = type_
    o.statut = statut
    o.echeance = echeance
    return o


# ═══════════════════════════════════════════════
# Test: CEE Evidence Template
# ═══════════════════════════════════════════════


class TestCeeEvidenceTemplate:
    def test_template_has_7_items(self):
        """CEE dossier requires 7 evidence pieces."""
        assert len(_CEE_EVIDENCE_TEMPLATE) == 7

    def test_template_keys_complete(self):
        """Each template item has type_key, label, step."""
        for tmpl in _CEE_EVIDENCE_TEMPLATE:
            assert "type_key" in tmpl
            assert "label" in tmpl
            assert "step" in tmpl

    def test_template_types_unique(self):
        """All type_keys are unique."""
        keys = [t["type_key"] for t in _CEE_EVIDENCE_TEMPLATE]
        assert len(keys) == len(set(keys))

    def test_all_steps_covered(self):
        """Template covers all kanban steps except engagement (action only)."""
        steps_in_template = {t["step"].value for t in _CEE_EVIDENCE_TEMPLATE}
        # devis, travaux, pv_photos, mv, versement are covered
        assert "devis" in steps_in_template
        assert "pv_photos" in steps_in_template
        assert "mv" in steps_in_template


# ═══════════════════════════════════════════════
# Test: create_cee_dossier
# ═══════════════════════════════════════════════


class TestCreateCeeDossier:
    def test_rejects_missing_work_package(self):
        """create_cee_dossier raises ValueError for unknown WP."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="WorkPackage.*not found"):
            create_cee_dossier(db, site_id=1, work_package_id=999)

    def test_rejects_wrong_site(self):
        """WP belonging to different site raises ValueError."""
        db = MagicMock()
        wp = _make_work_package(id=1, site_id=99)
        db.query.return_value.filter.return_value.first.return_value = wp
        with pytest.raises(ValueError, match="does not belong"):
            create_cee_dossier(db, site_id=1, work_package_id=1)

    def test_rejects_duplicate_dossier(self):
        """Cannot create second dossier for same WP."""
        db = MagicMock()
        wp = _make_work_package(id=1, site_id=1)
        site = _make_site()
        existing = MagicMock(spec=CeeDossier)

        # First query → WorkPackage, second → Site, third → existing dossier
        call_count = [0]

        def mock_first():
            call_count[0] += 1
            if call_count[0] == 1:
                return wp
            elif call_count[0] == 2:
                return site
            else:
                return existing

        db.query.return_value.filter.return_value.first.side_effect = mock_first

        with pytest.raises(ValueError, match="already exists"):
            create_cee_dossier(db, site_id=1, work_package_id=1)


# ═══════════════════════════════════════════════
# Test: advance_cee_step
# ═══════════════════════════════════════════════


class TestAdvanceCeeStep:
    def test_rejects_missing_dossier(self):
        """advance_cee_step raises ValueError for unknown dossier."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with pytest.raises(ValueError, match="CeeDossier.*not found"):
            advance_cee_step(db, dossier_id=999, new_step="travaux")

    def test_rejects_invalid_step(self):
        """Invalid step value raises ValueError."""
        db = MagicMock()
        dossier = MagicMock(spec=CeeDossier)
        dossier.id = 1
        dossier.current_step = CeeDossierStep.DEVIS
        dossier.action_ids_json = "[]"
        db.query.return_value.filter.return_value.first.return_value = dossier
        with pytest.raises(ValueError, match="Invalid CEE step"):
            advance_cee_step(db, dossier_id=1, new_step="invalid_step")

    def test_valid_advance_updates_step(self):
        """Valid advance changes current_step."""
        db = MagicMock()
        dossier = MagicMock(spec=CeeDossier)
        dossier.id = 1
        dossier.current_step = CeeDossierStep.DEVIS
        dossier.action_ids_json = "[]"
        db.query.return_value.filter.return_value.first.return_value = dossier

        result = advance_cee_step(db, dossier_id=1, new_step="engagement")
        assert result["old_step"] == "devis"
        assert result["new_step"] == "engagement"


# ═══════════════════════════════════════════════
# Test: compute_mv_summary
# ═══════════════════════════════════════════════


class TestMvSummary:
    def test_returns_baseline_from_site(self):
        """M&V baseline uses site.annual_kwh_total / 12."""
        db = MagicMock()
        site = _make_site(annual_kwh_total=120000)
        db.query.return_value.filter.return_value.first.return_value = site
        # Mock consumption query
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        # Mock obligations
        db.query.return_value.filter.return_value.all.return_value = []

        result = compute_mv_summary(db, site_id=1)
        assert result["baseline_kwh_month"] == 10000.0  # 120000/12
        assert result["site_id"] == 1

    def test_data_missing_alert(self):
        """Alert triggered when <3 recent data points."""
        db = MagicMock()
        site = _make_site(annual_kwh_total=120000)
        db.query.return_value.filter.return_value.first.return_value = site
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        db.query.return_value.filter.return_value.all.return_value = []

        result = compute_mv_summary(db, site_id=1)
        alert_types = [a["type"] for a in result["alerts"]]
        assert "data_missing" in alert_types

    def test_deadline_alert(self):
        """Alert when obligation deadline is within 90 days."""
        from models import Site

        db = MagicMock()
        site = _make_site(annual_kwh_total=120000)

        mock_site_query = MagicMock()
        mock_site_query.filter.return_value.first.return_value = site

        obl = _make_obligation(
            echeance=date(2026, 4, 1),
            statut=StatutConformite.A_RISQUE,
        )
        mock_obl_query = MagicMock()
        mock_obl_query.filter.return_value.all.return_value = [obl]

        # Dispatch par modèle — Meter/MeterReading peuvent échouer silencieusement,
        # seuls Site et Obligation comptent pour ce test.
        def mock_query(model):
            if model is Site:
                return mock_site_query
            if model is Obligation:
                return mock_obl_query
            return MagicMock()

        db.query.side_effect = mock_query

        result = compute_mv_summary(db, site_id=1)
        alert_types = [a["type"] for a in result["alerts"]]
        assert "deadline_approaching" in alert_types
        # data_missing aussi présent car aucun relevé récent dans ce test
        assert "data_missing" in alert_types


# ═══════════════════════════════════════════════
# Test: Enum values
# ═══════════════════════════════════════════════


class TestV69Enums:
    def test_work_package_sizes(self):
        assert WorkPackageSize.S.value == "S"
        assert WorkPackageSize.M.value == "M"
        assert WorkPackageSize.L.value == "L"

    def test_cee_dossier_steps(self):
        steps = [s.value for s in CeeDossierStep]
        assert steps == ["devis", "engagement", "travaux", "pv_photos", "mv", "versement"]

    def test_cee_status(self):
        assert CeeStatus.A_QUALIFIER.value == "a_qualifier"
        assert CeeStatus.OK.value == "ok"
        assert CeeStatus.NON.value == "non"

    def test_mv_alert_types(self):
        assert MVAlertType.BASELINE_DRIFT.value == "baseline_drift"
        assert MVAlertType.DEADLINE_APPROACHING.value == "deadline_approaching"
        assert MVAlertType.DATA_MISSING.value == "data_missing"


# ═══════════════════════════════════════════════
# Test: Model structure
# ═══════════════════════════════════════════════


class TestV69Models:
    def test_work_package_table(self):
        assert WorkPackage.__tablename__ == "work_packages"

    def test_cee_dossier_table(self):
        assert CeeDossier.__tablename__ == "cee_dossiers"

    def test_cee_dossier_evidence_table(self):
        assert CeeDossierEvidence.__tablename__ == "cee_dossier_evidences"

    def test_work_package_has_site_fk(self):
        cols = {c.name for c in WorkPackage.__table__.columns}
        assert "site_id" in cols
        assert "label" in cols
        assert "size" in cols
        assert "capex_eur" in cols

    def test_cee_dossier_has_required_columns(self):
        cols = {c.name for c in CeeDossier.__table__.columns}
        assert "work_package_id" in cols
        assert "site_id" in cols
        assert "current_step" in cols
        assert "action_ids_json" in cols

    def test_cee_evidence_has_required_columns(self):
        cols = {c.name for c in CeeDossierEvidence.__table__.columns}
        assert "dossier_id" in cols
        assert "site_id" in cols
        assert "type_key" in cols
        assert "statut" in cols
        assert "evidence_id" in cols
