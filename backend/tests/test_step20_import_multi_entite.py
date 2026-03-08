"""
Step 20 — O5 : Import multi-entité dans le template
Tests unitaires pour les colonnes, mapping, staging, quality gate, et activation.
"""

import pytest


# ============================================================
# Template columns
# ============================================================


class TestTemplateColumns:
    """Test that new columns are present in CANONICAL_COLUMNS."""

    def test_has_siren_entite(self):
        from services.import_mapping import CANONICAL_COLUMNS

        keys = [c["key"] for c in CANONICAL_COLUMNS]
        assert "siren_entite" in keys

    def test_has_nom_entite(self):
        from services.import_mapping import CANONICAL_COLUMNS

        keys = [c["key"] for c in CANONICAL_COLUMNS]
        assert "nom_entite" in keys

    def test_has_portefeuille(self):
        from services.import_mapping import CANONICAL_COLUMNS

        keys = [c["key"] for c in CANONICAL_COLUMNS]
        assert "portefeuille" in keys

    def test_has_batiment_nom(self):
        from services.import_mapping import CANONICAL_COLUMNS

        keys = [c["key"] for c in CANONICAL_COLUMNS]
        assert "batiment_nom" in keys

    def test_has_batiment_surface_m2(self):
        from services.import_mapping import CANONICAL_COLUMNS

        keys = [c["key"] for c in CANONICAL_COLUMNS]
        assert "batiment_surface_m2" in keys

    def test_has_batiment_annee_construction(self):
        from services.import_mapping import CANONICAL_COLUMNS

        keys = [c["key"] for c in CANONICAL_COLUMNS]
        assert "batiment_annee_construction" in keys

    def test_has_batiment_cvc_power_kw(self):
        from services.import_mapping import CANONICAL_COLUMNS

        keys = [c["key"] for c in CANONICAL_COLUMNS]
        assert "batiment_cvc_power_kw" in keys

    def test_new_columns_not_required(self):
        from services.import_mapping import CANONICAL_COLUMNS

        new_keys = {
            "siren_entite",
            "nom_entite",
            "portefeuille",
            "batiment_nom",
            "batiment_surface_m2",
            "batiment_annee_construction",
            "batiment_cvc_power_kw",
        }
        for col in CANONICAL_COLUMNS:
            if col["key"] in new_keys:
                assert not col["required"], f"{col['key']} should not be required"

    def test_total_columns_count(self):
        from services.import_mapping import CANONICAL_COLUMNS

        # 14 original + 7 new = 21
        assert len(CANONICAL_COLUMNS) == 21


# ============================================================
# Synonym mapping
# ============================================================


class TestSynonyms:
    """Test synonym resolution for new columns."""

    def test_siren_filiale_maps(self):
        from services.import_mapping import normalize_column_name

        assert normalize_column_name("siren_filiale") == "siren_entite"

    def test_entity_siren_maps(self):
        from services.import_mapping import normalize_column_name

        assert normalize_column_name("entity_siren") == "siren_entite"

    def test_filiale_maps(self):
        from services.import_mapping import normalize_column_name

        assert normalize_column_name("filiale") == "nom_entite"

    def test_portfolio_maps(self):
        from services.import_mapping import normalize_column_name

        assert normalize_column_name("portfolio") == "portefeuille"

    def test_building_name_maps(self):
        from services.import_mapping import normalize_column_name

        assert normalize_column_name("building_name") == "batiment_nom"

    def test_building_surface_maps(self):
        from services.import_mapping import normalize_column_name

        assert normalize_column_name("building_surface") == "batiment_surface_m2"

    def test_year_built_maps(self):
        from services.import_mapping import normalize_column_name

        assert normalize_column_name("year_built") == "batiment_annee_construction"

    def test_hvac_power_maps(self):
        from services.import_mapping import normalize_column_name

        assert normalize_column_name("hvac_power") == "batiment_cvc_power_kw"


# ============================================================
# Canonical column keys
# ============================================================


class TestCanonicalColumnKeys:
    """Test CANONICAL_COLUMN_KEYS has new entries."""

    def test_siren_entite_in_keys(self):
        from services.import_mapping import CANONICAL_COLUMN_KEYS

        assert "siren_entite" in CANONICAL_COLUMN_KEYS

    def test_batiment_nom_in_keys(self):
        from services.import_mapping import CANONICAL_COLUMN_KEYS

        assert "batiment_nom" in CANONICAL_COLUMN_KEYS


# ============================================================
# StagingSite model columns
# ============================================================


class TestStagingSiteModel:
    """Test that StagingSite has the new columns."""

    def test_has_siren_entite(self):
        from models.patrimoine import StagingSite

        assert hasattr(StagingSite, "siren_entite")

    def test_has_nom_entite(self):
        from models.patrimoine import StagingSite

        assert hasattr(StagingSite, "nom_entite")

    def test_has_portefeuille_nom(self):
        from models.patrimoine import StagingSite

        assert hasattr(StagingSite, "portefeuille_nom")

    def test_has_batiment_nom(self):
        from models.patrimoine import StagingSite

        assert hasattr(StagingSite, "batiment_nom")

    def test_has_batiment_surface_m2(self):
        from models.patrimoine import StagingSite

        assert hasattr(StagingSite, "batiment_surface_m2")

    def test_has_batiment_annee_construction(self):
        from models.patrimoine import StagingSite

        assert hasattr(StagingSite, "batiment_annee_construction")

    def test_has_batiment_cvc_power_kw(self):
        from models.patrimoine import StagingSite

        assert hasattr(StagingSite, "batiment_cvc_power_kw")


# ============================================================
# Quality gate rules
# ============================================================


class TestQualityRules:
    """Test new quality gate rules exist."""

    def test_invalid_siren_entite_rule_exists(self):
        from services.quality_rules import QUALITY_RULES

        ids = [r["id"] for r in QUALITY_RULES]
        assert "invalid_siren_entite" in ids

    def test_orphan_portefeuille_rule_exists(self):
        from services.quality_rules import QUALITY_RULES

        ids = [r["id"] for r in QUALITY_RULES]
        assert "orphan_portefeuille" in ids

    def test_batiment_sans_surface_rule_exists(self):
        from services.quality_rules import QUALITY_RULES

        ids = [r["id"] for r in QUALITY_RULES]
        assert "batiment_sans_surface" in ids

    def test_quality_rules_total(self):
        from services.quality_rules import QUALITY_RULES

        # 11 original + 3 new = 14
        assert len(QUALITY_RULES) == 14


# ============================================================
# CSV template generation
# ============================================================


class TestCSVTemplate:
    """Test CSV template includes new columns."""

    def test_csv_template_has_siren_entite(self):
        from services.import_mapping import generate_csv_template

        template = generate_csv_template().decode("utf-8-sig")
        assert "siren_entite" in template

    def test_csv_template_has_batiment_nom(self):
        from services.import_mapping import generate_csv_template

        template = generate_csv_template().decode("utf-8-sig")
        assert "batiment_nom" in template


# ============================================================
# Backward compatibility
# ============================================================


class TestBackwardCompat:
    """Test that old columns still work."""

    def test_old_columns_still_present(self):
        from services.import_mapping import CANONICAL_COLUMNS

        keys = [c["key"] for c in CANONICAL_COLUMNS]
        for old_key in [
            "nom",
            "adresse",
            "code_postal",
            "ville",
            "surface_m2",
            "type",
            "naf_code",
            "siren",
            "siret",
            "energy_type",
            "delivery_code",
            "numero_serie",
            "type_compteur",
            "puissance_kw",
        ]:
            assert old_key in keys, f"Missing old column: {old_key}"

    def test_nom_still_required(self):
        from services.import_mapping import CANONICAL_COLUMNS

        nom_col = [c for c in CANONICAL_COLUMNS if c["key"] == "nom"][0]
        assert nom_col["required"] is True

    def test_map_headers_ignores_unknown(self):
        from services.import_mapping import map_headers

        mapping, warnings = map_headers(["nom", "unknown_col"])
        assert "nom" in mapping.values()
        assert len(warnings) == 1
