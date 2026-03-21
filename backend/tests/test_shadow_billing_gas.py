"""
Tests shadow billing gaz (V110).
Vérifie la reconstitution déterministe des composantes gaz :
fourniture, ATRD (abo+var), ATRT, CTA, TICGN.
"""

import pytest
from datetime import date
from services.billing_engine import build_invoice_reconstitution
from services.billing_engine.types import ReconstitutionStatus, InvoiceType


class TestGasReconstitution:
    """Reconstitution gaz déterministe."""

    def test_basic_gas_reconstitution(self):
        """50 MWh gaz octobre 2025 → statut RECONSTITUTED."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 50_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
        )
        assert r.status == ReconstitutionStatus.RECONSTITUTED
        assert r.energy_type == "GAZ"
        assert r.total_ht > 0
        assert r.total_ttc > r.total_ht

    def test_gas_supply_component(self):
        """Fourniture = kWh × prix."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 10_000},
            supply_prices_by_period={"BASE": 0.08},
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
        )
        supply = next(c for c in r.components if c.code == "supply_base")
        assert supply.amount_ht == pytest.approx(800.0, abs=0.01)  # 10000 × 0.08

    def test_gas_ticgn(self):
        """TICGN = kWh × 0.01639 EUR/kWh (taux fév. 2026)."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 100_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
        )
        ticgn = next(c for c in r.components if c.code == "ticgn")
        assert ticgn.amount_ht == pytest.approx(1639.0, abs=0.01)  # 100000 × 0.01639

    def test_gas_atrd_tier_selection(self):
        """Tranche ATRD sélectionnée en fonction de la conso annuelle estimée."""
        # Petit consommateur → T1 (< 6 MWh/an)
        r_small = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 400},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 3, 1),
            period_end=date(2025, 3, 31),
        )
        assert any("T1" in a for a in r_small.assumptions)

        # Gros consommateur → T3 (> 300 MWh/an)
        r_big = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 100_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 3, 1),
            period_end=date(2025, 3, 31),
        )
        assert any("T3" in a for a in r_big.assumptions)

    def test_gas_advance_invoice_readonly(self):
        """Facture d'acompte gaz → READ_ONLY."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 10_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
            invoice_type=InvoiceType.ADVANCE,
        )
        assert r.status == ReconstitutionStatus.READ_ONLY

    def test_gas_all_components_present(self):
        """Les 6 composantes gaz sont présentes (sans abonnement fournisseur)."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 50_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
        )
        codes = {c.code for c in r.components}
        assert "supply_base" in codes
        assert "atrd_abo" in codes
        assert "atrd_var" in codes
        assert "atrt" in codes
        assert "cta_gaz" in codes
        assert "ticgn" in codes

    def test_gas_with_fixed_fee(self):
        """Abonnement fournisseur ajouté si > 0."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 10_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
            fixed_fee_eur_month=15.0,
        )
        codes = {c.code for c in r.components}
        assert "abo_fournisseur" in codes

    def test_gas_tva_split(self):
        """TVA 5.5% sur fixe (ATRD abo, CTA, abo fournisseur), 20% sur variable."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 50_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
        )
        for c in r.components:
            if c.code in ("atrd_abo", "cta_gaz", "abo_fournisseur"):
                assert c.tva_rate == pytest.approx(0.055), f"{c.code} should be 5.5% TVA"
            else:
                assert c.tva_rate == pytest.approx(0.20), f"{c.code} should be 20% TVA"

    def test_elec_still_works(self):
        """L'élec C5 fonctionne toujours après ajout gaz."""
        from services.billing_engine.types import TariffOption

        r = build_invoice_reconstitution(
            energy_type="ELEC",
            subscribed_power_kva=6.0,
            tariff_option=TariffOption.BASE,
            kwh_by_period={"BASE": 5_000},
            supply_prices_by_period={"BASE": 0.15},
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
        )
        assert r.status == ReconstitutionStatus.RECONSTITUTED
        assert r.energy_type == "ELEC"
