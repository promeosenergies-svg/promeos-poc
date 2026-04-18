"""Tests unitaires brique CBAM — P3 stratégique (audit CBAM intégré cockpit énergie)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date

import pytest

from services.billing_engine.bricks.cbam import (
    CBAM_SCOPES,
    DEFAULT_INTENSITIES,
    DEFAULT_RATE_EUR_PER_TCO2,
    compute_cbam,
)


AT_DATE = date(2026, 4, 18)


class TestCompteCbamSansImportations:
    def test_empty_dict_non_applicable(self):
        """Site sans imports → 0 EUR, applicable=False, note pédagogique."""
        result = compute_cbam({}, AT_DATE)
        assert result.total_cost_eur == 0.0
        assert result.total_co2_embedded_t == 0.0
        assert result.applicable is False
        assert result.breakdown == []
        assert "non applicable" in result.note.lower()

    def test_none_imports_non_applicable(self):
        """None imports (pas de configuration) → 0 EUR, applicable=False."""
        result = compute_cbam(None, AT_DATE)
        assert result.total_cost_eur == 0.0
        assert result.applicable is False

    def test_all_scopes_zero_non_applicable(self):
        """Tous les scopes à 0 tonne → non applicable."""
        imports = {s: 0.0 for s in CBAM_SCOPES}
        result = compute_cbam(imports, AT_DATE)
        assert result.total_cost_eur == 0.0
        assert result.applicable is False


class TestComputeCbamAvecImportations:
    def test_acier_100t_intensite_defaut(self):
        """100 t acier × 2.0 tCO2/t × 75.36 €/tCO2 = 15 072 €."""
        result = compute_cbam({"acier": 100.0}, AT_DATE)
        assert result.applicable is True
        assert len(result.breakdown) == 1
        bk = result.breakdown[0]
        assert bk.scope == "acier"
        assert bk.volume_t == 100.0
        assert bk.intensity_tco2_per_t == 2.0
        assert bk.co2_embedded_t == 200.0
        assert bk.cost_eur == pytest.approx(15072.0, rel=1e-3)
        assert bk.intensity_source == "default_ce"
        assert result.total_cost_eur == pytest.approx(15072.0, rel=1e-3)
        assert result.total_co2_embedded_t == 200.0
        assert result.rate_eur_per_tco2 == pytest.approx(75.36, rel=1e-3)

    def test_multi_scope_somme(self):
        """Imports mixtes → somme correcte par scope."""
        imports = {"acier": 50.0, "aluminium": 10.0, "ciment": 200.0}
        result = compute_cbam(imports, AT_DATE)
        assert len(result.breakdown) == 3
        scopes_rendus = {b.scope for b in result.breakdown}
        assert scopes_rendus == {"acier", "aluminium", "ciment"}
        # Somme = (50×2.0 + 10×16.5 + 200×0.66) × 75.36
        #       = (100 + 165 + 132) × 75.36 = 397 × 75.36
        expected = 397.0 * 75.36
        assert result.total_cost_eur == pytest.approx(expected, rel=1e-3)
        assert result.total_co2_embedded_t == pytest.approx(397.0, rel=1e-3)

    def test_intensite_site_specific_surcharge_defaut(self):
        """Intensité site-specific prioritaire sur défaut CE."""
        site_int = {"acier": 1.2}  # aciérie bas-carbone (EAF recyclage)
        result = compute_cbam({"acier": 100.0}, AT_DATE, site_specific_intensities=site_int)
        bk = result.breakdown[0]
        assert bk.intensity_tco2_per_t == 1.2
        assert bk.intensity_source == "site_specific"
        # 100 × 1.2 × 75.36 = 9 043.2 €
        assert result.total_cost_eur == pytest.approx(9043.2, rel=1e-3)

    def test_scope_inconnu_ignore_silencieux(self):
        """Scope hors CBAM_SCOPES → ignoré, n'affecte pas le total."""
        imports = {"acier": 10.0, "gaz_naturel": 500.0, "petrole": 1000.0}
        result = compute_cbam(imports, AT_DATE)
        assert len(result.breakdown) == 1
        assert result.breakdown[0].scope == "acier"

    def test_breakdown_audit_trail_complet(self):
        """Chaque scope breakdown expose volume, intensité, source, coût."""
        result = compute_cbam({"hydrogene": 20.0}, AT_DATE)
        bk = result.breakdown[0]
        assert bk.scope == "hydrogene"
        assert bk.volume_t == 20.0
        assert bk.intensity_tco2_per_t == DEFAULT_INTENSITIES["hydrogene"]
        assert bk.intensity_source == "default_ce"
        assert bk.co2_embedded_t == pytest.approx(200.0, rel=1e-3)
        # 200 × 75.36 = 15 072 €
        assert bk.cost_eur == pytest.approx(15072.0, rel=1e-3)


class TestComputeCbamParametres:
    def test_rate_lu_depuis_yaml(self):
        """Rate CBAM provient du YAML cbam_eu.rate_eur_per_t_co2."""
        result = compute_cbam({"acier": 1.0}, AT_DATE)
        # Le YAML ship avec 75.36 ; vérifier qu'on ne fallback pas silencieusement
        assert result.rate_eur_per_tco2 == pytest.approx(DEFAULT_RATE_EUR_PER_TCO2, rel=1e-3)

    def test_rate_at_date_tracable(self):
        """at_date passée est exposée dans rate_at_date pour audit."""
        custom_date = date(2027, 6, 15)
        result = compute_cbam({"acier": 1.0}, custom_date)
        assert result.rate_at_date == custom_date

    def test_note_applicable_resume(self):
        """Note pédagogique quand applicable expose tCO2 + rate + total."""
        result = compute_cbam({"acier": 50.0}, AT_DATE)
        assert result.applicable is True
        assert "tCO2" in result.note
        assert "75.36" in result.note or "75,36" in result.note


class TestCbamScopes:
    def test_cbam_scopes_canoniques_six(self):
        """Les 6 scopes CBAM du règlement 2023/956."""
        assert CBAM_SCOPES == frozenset(["acier", "ciment", "aluminium", "engrais", "hydrogene", "electricite"])

    def test_cbam_scopes_aligned_with_yaml(self):
        """Drift guard : CBAM_SCOPES Python == cbam_eu.scope YAML == DEFAULT_INTENSITIES keys.

        Si le YAML est mis à jour (ajout/retrait scope), le Python doit suivre —
        ce test catche une divergence au test run plutôt qu'en prod silencieuse.
        """
        from utils.parameter_store_base import load_yaml_section

        section = load_yaml_section("cbam_eu") or {}
        yaml_scopes = frozenset(section.get("scope", []))
        default_keys = frozenset(DEFAULT_INTENSITIES.keys())
        assert CBAM_SCOPES == yaml_scopes, (
            f"Drift CBAM_SCOPES Python vs YAML cbam_eu.scope : py={CBAM_SCOPES} yaml={yaml_scopes}"
        )
        assert CBAM_SCOPES == default_keys, (
            f"Drift CBAM_SCOPES vs DEFAULT_INTENSITIES keys : scopes={CBAM_SCOPES} defaults={default_keys}"
        )
