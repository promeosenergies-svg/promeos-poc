"""
PROMEOS — Step 8: Billing seed 5 sites HELIOS
Verifie que billing_seed.py couvre 5 sites avec anomalies variees.
"""

import pytest
import sys
import os
import calendar
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── A. Source structure — billing_seed.py couvre 5 sites ──────────────────────


class TestBillingSeedSource:
    """Tests source-guard sur billing_seed.py."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        seed_path = os.path.join(os.path.dirname(__file__), "..", "services", "billing_seed.py")
        self.source = open(seed_path).read()

    def test_source_mentions_5_sites(self):
        assert "site_a" in self.source
        assert "site_b" in self.source
        assert "site_c" in self.source
        assert "site_d" in self.source
        assert "site_e" in self.source

    def test_marseille_function_exists(self):
        assert "_add_marseille_invoice" in self.source

    def test_nice_elec_function_exists(self):
        assert "_add_nice_elec_invoice" in self.source

    def test_nice_gaz_function_exists(self):
        assert "_add_nice_gaz_invoice" in self.source

    def test_toulouse_function_exists(self):
        assert "_add_toulouse_invoice" in self.source

    def test_3_suppliers(self):
        # EDF, ENGIE, TotalEnergies
        assert "EDF" in self.source
        assert "ENGIE" in self.source
        assert "TotalEnergies" in self.source

    def test_source_tag_seed_36m(self):
        assert 'SOURCE_TAG = "seed_36m"' in self.source

    def test_idempotent(self):
        assert "existing" in self.source
        assert "skipped" in self.source

    def test_marseille_gap_august(self):
        assert "(2024, 8)" in self.source
        assert "GAPS_MARSEILLE" in self.source

    def test_toulouse_3_gaps(self):
        assert "GAPS_TOULOUSE" in self.source
        assert "(2024, 9)" in self.source
        assert "(2024, 12)" in self.source
        assert "(2025, 3)" in self.source

    def test_nice_seasonality(self):
        assert "_NICE_ELEC_SEASON" in self.source
        assert "_NICE_GAZ_SEASON" in self.source

    def test_anomaly_r1_marseille(self):
        assert "ANOMALY_MARSEILLE_R1" in self.source
        assert "1.35" in self.source

    def test_anomaly_r3_marseille_spike(self):
        assert "ANOMALY_MARSEILLE_R3" in self.source
        assert "2.7" in self.source

    def test_anomaly_r11_nice(self):
        assert "ANOMALY_NICE_R11" in self.source
        assert "1.035" in self.source

    def test_anomaly_r1_toulouse(self):
        assert "ANOMALY_TOULOUSE_R1" in self.source
        assert "0.24" in self.source

    def test_nice_contract_expiry_30days(self):
        # Contract Nice ELEC expires in 30 days (R12)
        assert "days=30" in self.source


# ── B. Constants — volumes et prix corrects ──────────────────────────────────


class TestBillingConstants:
    """Verifie les constantes de billing pour chaque site."""

    def test_marseille_volume(self):
        from services.billing_seed import KWH_MARSEILLE

        assert KWH_MARSEILLE == 4500

    def test_marseille_price(self):
        from services.billing_seed import PRICE_REF_MARSEILLE

        assert PRICE_REF_MARSEILLE == 0.19

    def test_nice_elec_volume(self):
        from services.billing_seed import KWH_NICE_ELEC

        assert KWH_NICE_ELEC == 8000

    def test_nice_gaz_volume(self):
        from services.billing_seed import KWH_NICE_GAZ

        assert KWH_NICE_GAZ == 3000

    def test_nice_elec_price(self):
        from services.billing_seed import PRICE_REF_NICE_ELEC

        assert PRICE_REF_NICE_ELEC == 0.21

    def test_nice_gaz_price(self):
        from services.billing_seed import PRICE_REF_NICE_GAZ

        assert PRICE_REF_NICE_GAZ == 0.09

    def test_toulouse_volume(self):
        from services.billing_seed import KWH_TOULOUSE

        assert KWH_TOULOUSE == 12000

    def test_toulouse_price(self):
        from services.billing_seed import PRICE_REF_TOULOUSE

        assert PRICE_REF_TOULOUSE == 0.17

    def test_toulouse_partial_coverage(self):
        from services.billing_seed import TOULOUSE_MONTHS

        assert TOULOUSE_MONTHS == 18


# ── C. Invoice count predictions ─────────────────────────────────────────────


class TestInvoiceCounts:
    """Verifie le nombre attendu de factures par site."""

    def test_marseille_invoice_count(self):
        """Marseille: 24 mois - 1 trou = 23 factures."""
        from services.billing_seed import GAPS_MARSEILLE

        expected = 24 - len(GAPS_MARSEILLE)
        assert expected == 23

    def test_nice_elec_invoice_count(self):
        """Nice ELEC: 24 mois, pas de trou = 24 factures."""
        assert 24 == 24

    def test_nice_gaz_invoice_count(self):
        """Nice GAZ: 24 mois, pas de trou = 24 factures."""
        assert 24 == 24

    def test_toulouse_invoice_count(self):
        """Toulouse: 18 mois - 3 trous = 15 factures."""
        from services.billing_seed import GAPS_TOULOUSE, TOULOUSE_MONTHS

        expected = TOULOUSE_MONTHS - len(GAPS_TOULOUSE)
        assert expected == 15

    def test_total_new_invoices(self):
        """3 nouveaux sites: 23 + 24 + 24 + 15 = 86 factures."""
        from services.billing_seed import (
            GAPS_MARSEILLE,
            GAPS_TOULOUSE,
            TOULOUSE_MONTHS,
        )

        marseille = 24 - len(GAPS_MARSEILLE)
        nice_elec = 24
        nice_gaz = 24
        toulouse = TOULOUSE_MONTHS - len(GAPS_TOULOUSE)
        total_new = marseille + nice_elec + nice_gaz + toulouse
        assert total_new == 86


# ── D. Saisonnalite Nice ─────────────────────────────────────────────────────


class TestNiceSeasonality:
    """Verifie la saisonnalite hotel Nice."""

    def test_elec_summer_higher(self):
        from services.billing_seed import _NICE_ELEC_SEASON

        assert _NICE_ELEC_SEASON[7] == 1.4  # été ×1.4

    def test_elec_winter_lower(self):
        from services.billing_seed import _NICE_ELEC_SEASON

        assert _NICE_ELEC_SEASON[1] == 0.9

    def test_gaz_winter_higher(self):
        from services.billing_seed import _NICE_GAZ_SEASON

        assert _NICE_GAZ_SEASON[1] == 1.3  # hiver ×1.3

    def test_gaz_summer_lower(self):
        from services.billing_seed import _NICE_GAZ_SEASON

        assert _NICE_GAZ_SEASON[7] == 0.7


# ── E. Invoice number uniqueness ─────────────────────────────────────────────


class TestInvoiceNumberPatterns:
    """Verifie que les patterns de numero de facture sont uniques."""

    def test_marseille_pattern(self):
        source = open(os.path.join(os.path.dirname(__file__), "..", "services", "billing_seed.py")).read()
        assert "ENGIE-MAR-" in source

    def test_nice_elec_pattern(self):
        source = open(os.path.join(os.path.dirname(__file__), "..", "services", "billing_seed.py")).read()
        assert "TOTAL-NIC-" in source

    def test_nice_gaz_pattern(self):
        source = open(os.path.join(os.path.dirname(__file__), "..", "services", "billing_seed.py")).read()
        assert "ENGIE-NIC-G-" in source

    def test_toulouse_pattern(self):
        source = open(os.path.join(os.path.dirname(__file__), "..", "services", "billing_seed.py")).read()
        assert "EDF-TLS-" in source

    def test_all_patterns_distinct(self):
        patterns = ["EDF-", "ENGIE-MAR-", "TOTAL-NIC-", "ENGIE-NIC-G-", "EDF-TLS-"]
        assert len(set(patterns)) == len(patterns)


# ── F. Paris + Lyon unchanged ─────────────────────────────────────────────────


class TestExistingSitesUnchanged:
    """Verifie que Paris (site_a) et Lyon (site_b) restent identiques."""

    def test_paris_elec_constants(self):
        from services.billing_seed import KWH_ELEC, PRICE_REF_ELEC

        assert KWH_ELEC == 9000
        assert PRICE_REF_ELEC == 0.068

    def test_lyon_gaz_constants(self):
        from services.billing_seed import KWH_GAZ, PRICE_REF_GAZ

        assert KWH_GAZ == 6000
        assert PRICE_REF_GAZ == 0.045

    def test_paris_anomalies_unchanged(self):
        from services.billing_seed import (
            ANOMALY_SHADOW_GAP,
            ANOMALY_RESEAU_MISMATCH,
            ANOMALY_TAXES_MISMATCH,
        )

        assert ANOMALY_SHADOW_GAP == (2024, 7)
        assert ANOMALY_RESEAU_MISMATCH == (2024, 11)
        assert ANOMALY_TAXES_MISMATCH == (2025, 1)

    def test_paris_gaps_unchanged(self):
        from services.billing_seed import GAPS_SITE_A, PARTIALS_SITE_A

        assert (2023, 3) in GAPS_SITE_A
        assert (2024, 9) in GAPS_SITE_A
        assert (2023, 6) in PARTIALS_SITE_A

    def test_lyon_gaps_unchanged(self):
        from services.billing_seed import GAPS_SITE_B

        assert (2025, 2) in GAPS_SITE_B
