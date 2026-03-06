"""
Step 18 — M2 : Référentiel TURPE/taxes YAML
Tests unitaires pour le loader, les helpers, et la route.
"""

import pytest


# ============================================================
# YAML loading
# ============================================================

class TestYAMLLoad:
    """Test that YAML referentiel loads correctly."""

    def test_load_tarifs(self):
        from config.tarif_loader import load_tarifs
        tarifs = load_tarifs()
        assert isinstance(tarifs, dict)
        assert "version" in tarifs

    def test_version_format(self):
        from config.tarif_loader import get_tarif_version
        version = get_tarif_version()
        assert version == "2025-02-01"

    def test_reload_tarifs(self):
        from config.tarif_loader import reload_tarifs
        tarifs = reload_tarifs()
        assert "turpe" in tarifs


# ============================================================
# TURPE helpers
# ============================================================

class TestTURPE:
    """Test TURPE segment helpers."""

    def test_c5_bt_energie(self):
        from config.tarif_loader import get_turpe_moyen_kwh
        assert get_turpe_moyen_kwh("C5_BT") == 0.0453

    def test_c4_bt_energie(self):
        from config.tarif_loader import get_turpe_moyen_kwh
        assert get_turpe_moyen_kwh("C4_BT") == 0.0390

    def test_c3_hta_energie(self):
        from config.tarif_loader import get_turpe_moyen_kwh
        assert get_turpe_moyen_kwh("C3_HTA") == 0.0260

    def test_c5_bt_gestion(self):
        from config.tarif_loader import get_turpe_gestion_mois
        assert get_turpe_gestion_mois("C5_BT") == 18.48

    def test_unknown_segment_raises(self):
        from config.tarif_loader import get_turpe_moyen_kwh
        with pytest.raises(KeyError, match="TURPE segment inconnu"):
            get_turpe_moyen_kwh("C99_UNKNOWN")

    def test_segment_has_label(self):
        from config.tarif_loader import get_turpe_segment
        seg = get_turpe_segment("C5_BT")
        assert "label" in seg
        assert "C5" in seg["label"]


# ============================================================
# Accise helpers
# ============================================================

class TestAccise:
    """Test accise rate helpers."""

    def test_accise_elec(self):
        from config.tarif_loader import get_accise_kwh
        assert get_accise_kwh("elec") == 0.02250

    def test_accise_gaz(self):
        from config.tarif_loader import get_accise_kwh
        assert get_accise_kwh("gaz") == 0.01637

    def test_accise_unknown_raises(self):
        from config.tarif_loader import get_accise_kwh
        with pytest.raises(ValueError):
            get_accise_kwh("hydro")


# ============================================================
# CTA / TVA / prix reference
# ============================================================

class TestOtherHelpers:
    """Test CTA, TVA, and price reference helpers."""

    def test_cta_elec(self):
        from config.tarif_loader import get_cta_taux
        assert get_cta_taux("elec") == 27.04

    def test_cta_gaz(self):
        from config.tarif_loader import get_cta_taux
        assert get_cta_taux("gaz") == 20.80

    def test_tva_normale(self):
        from config.tarif_loader import get_tva_normale
        assert get_tva_normale() == 0.20

    def test_tva_reduite(self):
        from config.tarif_loader import get_tva_reduite
        assert get_tva_reduite() == 0.055

    def test_prix_reference_elec(self):
        from config.tarif_loader import get_prix_reference
        assert get_prix_reference("elec") == 0.068

    def test_prix_reference_gaz(self):
        from config.tarif_loader import get_prix_reference
        assert get_prix_reference("gaz") == 0.045

    def test_ticgn(self):
        from config.tarif_loader import get_ticgn_kwh
        assert get_ticgn_kwh() == 0.01637

    def test_atrd(self):
        from config.tarif_loader import get_atrd_kwh
        assert get_atrd_kwh() == 0.025

    def test_atrt(self):
        from config.tarif_loader import get_atrt_kwh
        assert get_atrt_kwh() == 0.012


# ============================================================
# Summary / route structure
# ============================================================

class TestTarifSummary:
    """Test the summary used by the API endpoint."""

    def test_summary_has_version(self):
        from config.tarif_loader import get_tarif_summary
        s = get_tarif_summary()
        assert s["version"] == "2025-02-01"

    def test_summary_has_turpe_segments(self):
        from config.tarif_loader import get_tarif_summary
        s = get_tarif_summary()
        assert "C5_BT" in s["turpe"]
        assert "C4_BT" in s["turpe"]
        assert "C3_HTA" in s["turpe"]

    def test_summary_has_accise(self):
        from config.tarif_loader import get_tarif_summary
        s = get_tarif_summary()
        assert s["accise_elec"]["rate_eur_kwh"] == 0.02250

    def test_summary_has_tva(self):
        from config.tarif_loader import get_tarif_summary
        s = get_tarif_summary()
        assert s["tva_normale"] == 0.20
        assert s["tva_reduite"] == 0.055


# ============================================================
# Route file guard
# ============================================================

class TestReferentielRoute:
    """Test that referentiel route exists."""

    def test_route_importable(self):
        from routes.referentiel import router
        assert router.prefix == "/api/referentiel"

    def test_route_has_tarifs_endpoint(self):
        from routes.referentiel import router
        paths = [r.path for r in router.routes]
        assert any("tarifs" in p for p in paths)


# ============================================================
# Shadow V2 uses YAML fallback
# ============================================================

class TestShadowV2YAMLIntegration:
    """Test that shadow_v2 _FALLBACK loads from YAML."""

    def test_fallback_dict_loaded(self):
        from services.billing_shadow_v2 import _FALLBACK
        assert _FALLBACK["TURPE_ENERGIE_C5_BT"] == 0.0453
        assert _FALLBACK["DEFAULT_PRICE_ELEC"] == 0.068

    def test_fallback_has_all_keys(self):
        from services.billing_shadow_v2 import _FALLBACK
        expected_keys = [
            "TURPE_ENERGIE_C5_BT", "TURPE_GESTION_C5_BT",
            "ATRD_GAZ", "ATRT_GAZ",
            "ACCISE_ELEC", "ACCISE_GAZ",
            "TVA_NORMALE", "TVA_REDUITE",
            "DEFAULT_PRICE_ELEC", "DEFAULT_PRICE_GAZ",
        ]
        for k in expected_keys:
            assert k in _FALLBACK, f"Missing key: {k}"
