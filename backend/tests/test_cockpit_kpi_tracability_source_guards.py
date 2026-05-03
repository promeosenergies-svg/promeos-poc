"""PROMEOS — Source guards KPI traçabilité cockpit (Vague 3B EPIC #274).

Règle cardinale 03/05/2026 : chaque KPI exposé doit porter confidence + source_ref.

SG_TRACE_01 — doctrine/kpi_tracability.py existe et exporte CONFIDENCE_LEVELS
SG_TRACE_02 — CONFIDENCE_LEVELS contient les 5 niveaux obligatoires
SG_TRACE_03 — make_traceable_kpi rejette confidence invalide (ValueError)
SG_TRACE_04 — make_traceable_kpi rejette source_ref=None si confidence != 'unavailable'
SG_TRACE_05 — make_traceable_kpi retourne les 7 clés obligatoires
SG_TRACE_06 — unavailable_kpi retourne confidence='unavailable' et value=None
SG_TRACE_07 — potential_recoverable retourne leviers_kpi avec confidence + source_ref
SG_TRACE_08 — leviers_kpi.confidence est dans CONFIDENCE_LEVELS
SG_TRACE_09 — leviers_kpi.source_ref non-null si confidence != 'unavailable'
SG_TRACE_10 — get_cockpit_trajectory retourne projection_tracability avec confidence + source_ref

Ref : backend/doctrine/kpi_tracability.py + backend/services/cockpit_facts_service.py
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from doctrine.kpi_tracability import (
    CONFIDENCE_LEVELS,
    VALID_CONFIDENCE_LEVELS,
    make_traceable_kpi,
    unavailable_kpi,
)


# ─── SG_TRACE_01-02 — Module et enum ────────────────────────────────────────


class TestKpiTracabilityModule(unittest.TestCase):
    def test_sg_trace_01_module_importable(self):
        """SG_TRACE_01 : doctrine/kpi_tracability.py importable avec exports requis."""
        from doctrine import kpi_tracability  # noqa: F401

        assert hasattr(kpi_tracability, "CONFIDENCE_LEVELS")
        assert hasattr(kpi_tracability, "make_traceable_kpi")
        assert hasattr(kpi_tracability, "unavailable_kpi")

    def test_sg_trace_02_five_confidence_levels(self):
        """SG_TRACE_02 : les 5 niveaux de confiance obligatoires sont présents."""
        required = {
            "calculated_regulatory",
            "calculated_contractual",
            "modeled_cee",
            "modeled_pre_audit",
            "unavailable",
        }
        assert required.issubset(set(CONFIDENCE_LEVELS.keys())), (
            f"Niveaux manquants : {required - set(CONFIDENCE_LEVELS.keys())}"
        )


# ─── SG_TRACE_03-06 — make_traceable_kpi / unavailable_kpi ─────────────────


class TestMakeTraceableKpi(unittest.TestCase):
    def test_sg_trace_03_rejects_invalid_confidence(self):
        """SG_TRACE_03 : confidence invalide → ValueError."""
        with self.assertRaises(ValueError):
            make_traceable_kpi(
                value=42,
                confidence="random_invalid",  # type: ignore[arg-type]
                source_ref="Décret 2019-771",
                formula_text="test",
            )

    def test_sg_trace_04_rejects_null_source_ref_if_not_unavailable(self):
        """SG_TRACE_04 : source_ref=None interdit sauf confidence='unavailable'."""
        with self.assertRaises(ValueError):
            make_traceable_kpi(
                value=42,
                confidence="calculated_regulatory",
                source_ref=None,  # interdit ici
                formula_text="test",
            )

    def test_sg_trace_05_seven_required_keys(self):
        """SG_TRACE_05 : make_traceable_kpi retourne les 7 clés obligatoires."""
        result = make_traceable_kpi(
            value=17,
            confidence="modeled_cee",
            source_ref="CEE BAT-TH-116",
            formula_text="Σ gain CEE / 1 000 = 17 MWh/an",
            unit="MWh/an",
        )
        required_keys = {
            "value",
            "confidence",
            "source_ref",
            "formula_text",
            "confidence_label",
            "confidence_tooltip",
            "fallback_reason",
        }
        missing = required_keys - set(result.keys())
        assert not missing, f"Clés manquantes dans make_traceable_kpi : {missing}"

    def test_sg_trace_05_values_coherent(self):
        """SG_TRACE_05 : les valeurs du KPI traçable sont cohérentes."""
        result = make_traceable_kpi(
            value=25,
            confidence="calculated_regulatory",
            source_ref="Décret n°2019-771",
            formula_text="consommation réelle / référence",
            unit="%",
        )
        assert result["value"] == 25
        assert result["confidence"] == "calculated_regulatory"
        assert result["source_ref"] == "Décret n°2019-771"
        assert result["confidence_label"] == CONFIDENCE_LEVELS["calculated_regulatory"]
        assert result["unit"] == "%"

    def test_sg_trace_06_unavailable_kpi(self):
        """SG_TRACE_06 : unavailable_kpi retourne confidence='unavailable' et value=None."""
        result = unavailable_kpi(reason="aucune_action_qualifiee", unit="MWh/an")
        assert result["confidence"] == "unavailable"
        assert result["value"] is None
        assert result["source_ref"] is None
        assert result["fallback_reason"] == "aucune_action_qualifiee"


# ─── SG_TRACE_07-09 — potential_recoverable leviers_kpi ────────────────────


class TestPotentialRecoverableLeviers(unittest.TestCase):
    def _make_mock_db(self, sites=None, surface=None, analytics=None):
        """Construit un mock SQLAlchemy session minimal."""
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = sites or []
        db.query.return_value.filter.return_value.scalar.return_value = surface
        return db

    def test_sg_trace_07_potential_recoverable_has_leviers_kpi(self):
        """SG_TRACE_07 : _build_potential_recoverable retourne leviers_kpi."""
        from services.cockpit_facts_service import _build_potential_recoverable

        db = MagicMock()
        # Simuler aucun site → value_mwh=0 → unavailable
        db.query.return_value.filter.return_value.with_entities.return_value.all.return_value = []
        db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = []

        with patch("services.cockpit_facts_service.not_deleted", return_value=db.query.return_value):
            result = _build_potential_recoverable(db, org_id=1, site_ids=[])

        assert "leviers_kpi" in result, "leviers_kpi absent du résultat potential_recoverable"

    def test_sg_trace_08_leviers_kpi_confidence_valid(self):
        """SG_TRACE_08 : leviers_kpi.confidence est dans VALID_CONFIDENCE_LEVELS."""
        from services.cockpit_facts_service import _build_potential_recoverable

        db = MagicMock()
        with patch("services.cockpit_facts_service.not_deleted", return_value=db.query.return_value):
            result = _build_potential_recoverable(db, org_id=1, site_ids=[])

        kpi = result.get("leviers_kpi", {})
        assert kpi.get("confidence") in VALID_CONFIDENCE_LEVELS, (
            f"confidence='{kpi.get('confidence')}' invalide. Attendu : {sorted(VALID_CONFIDENCE_LEVELS)}"
        )

    def test_sg_trace_09_source_ref_not_null_if_not_unavailable(self):
        """SG_TRACE_09 : source_ref non-null si confidence != 'unavailable'."""
        from services.cockpit_facts_service import _build_potential_recoverable

        db = MagicMock()
        with patch("services.cockpit_facts_service.not_deleted", return_value=db.query.return_value):
            result = _build_potential_recoverable(db, org_id=1, site_ids=[])

        kpi = result.get("leviers_kpi", {})
        if kpi.get("confidence") != "unavailable":
            assert kpi.get("source_ref") is not None, "source_ref est None alors que confidence != 'unavailable'"


# ─── SG_TRACE_10 — projection_tracability trajectory ────────────────────────


class TestTrajectoryTracability(unittest.TestCase):
    def test_sg_trace_10_cockpit_facts_service_imports_tracability(self):
        """SG_TRACE_10 : cockpit_facts_service importe doctrine.kpi_tracability."""
        import importlib
        import importlib.util

        spec = importlib.util.find_spec("services.cockpit_facts_service")
        assert spec is not None, "cockpit_facts_service introuvable"

        # Lire le source pour vérifier l'import
        with open(spec.origin, encoding="utf-8") as fh:
            src = fh.read()

        assert "kpi_tracability" in src, "cockpit_facts_service n'importe pas doctrine.kpi_tracability"
        assert "make_traceable_kpi" in src, "cockpit_facts_service n'utilise pas make_traceable_kpi"

    def test_sg_trace_10_cockpit_route_has_projection_tracability(self):
        """SG_TRACE_10 : cockpit.py route trajectory expose projection_tracability."""
        import importlib.util

        spec = importlib.util.find_spec("routes.cockpit")
        if spec is None:
            # Chemin alternatif
            import os

            route_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "routes", "cockpit.py"
            )
        else:
            route_path = spec.origin

        with open(route_path, encoding="utf-8") as fh:
            src = fh.read()

        assert "projection_tracability" in src, (
            "routes/cockpit.py ne retourne pas projection_tracability (VEX-Q5 Vague 3B manquant)"
        )
        assert "confidence" in src, "routes/cockpit.py ne contient pas de champ confidence"


if __name__ == "__main__":
    unittest.main()
