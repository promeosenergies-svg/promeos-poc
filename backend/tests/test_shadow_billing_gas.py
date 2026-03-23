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
        """TICGN = kWh × taux temporel (jan 2025 → 0.01637 EUR/kWh)."""
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
        assert ticgn.amount_ht == pytest.approx(1637.0, abs=0.01)  # 100000 × 0.01637 (TICGN 2024)

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

    def test_gas_tva_split_post_august_2025(self):
        """Post 01/08/2025 : TVA 20% uniforme sur composantes réelles (LFI 2025 art. 20)."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 50_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
        )
        shadow_codes = {"stockage_gaz", "cee_shadow"}
        for c in r.components:
            if c.code not in shadow_codes:
                assert c.tva_rate == pytest.approx(0.20), f"{c.code} should be 20% TVA post 01/08/2025"

    def test_gas_tva_split_pre_august_2025(self):
        """Avant 01/08/2025 : TVA 5.5% sur fixe (ATRD abo, CTA), 20% sur variable."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 50_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
        )
        shadow_codes = {"stockage_gaz", "cee_shadow"}
        for c in r.components:
            if c.code in shadow_codes:
                continue  # shadow components have tva_rate=0
            if c.code in ("atrd_abo", "cta_gaz", "abo_fournisseur"):
                assert c.tva_rate == pytest.approx(0.055), f"{c.code} should be 5.5% TVA pre 01/08/2025"
            else:
                assert c.tva_rate == pytest.approx(0.20), f"{c.code} should be 20% TVA"

    def test_gas_atrd6_temporal_resolution(self):
        """Période avant 01/07/2024 → taux ATRD6 (délibération n°2023-123)."""
        # Facture gaz janvier 2024 → ATRD6 (T2 car ~50 MWh/an estimé)
        r_atrd6 = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 4_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
        )
        atrd_var_6 = next(c for c in r_atrd6.components if c.code == "atrd_var")
        # ATRD6 T2 variable = 0.00893 EUR/kWh → 4000 × 0.00893 = 35.72
        assert atrd_var_6.amount_ht == pytest.approx(4_000 * 0.00893, abs=0.02)

        atrd_abo_6 = next(c for c in r_atrd6.components if c.code == "atrd_abo")
        # Source doit mentionner ATRD 6
        assert any("ATRD 6" in s.source for s in atrd_abo_6.rate_sources)

        # Facture gaz octobre 2024 → ATRD7
        r_atrd7 = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 4_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2024, 10, 1),
            period_end=date(2024, 10, 31),
        )
        atrd_var_7 = next(c for c in r_atrd7.components if c.code == "atrd_var")
        # ATRD7 T2 variable = 0.01208 EUR/kWh → 4000 × 0.01208 = 48.32
        assert atrd_var_7.amount_ht == pytest.approx(4_000 * 0.01208, abs=0.02)

        # Les deux périodes doivent donner des taux différents
        assert atrd_var_6.amount_ht < atrd_var_7.amount_ht

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


class TestGasStockageShadow:
    """Tests stockage gaz (ATS3) — composante shadow pour traçabilité."""

    def test_gas_stockage_shadow_present(self):
        """Composante stockage_gaz existe dans la décomposition."""
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
        assert "stockage_gaz" in codes

    def test_gas_stockage_shadow_zero_ht(self):
        """Shadow : amount_ht = 0 (pas de double comptage)."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 50_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
        )
        stockage = next(c for c in r.components if c.code == "stockage_gaz")
        assert stockage.amount_ht == 0.0
        assert stockage.inputs_used["shadow_amount_ht"] > 0

    def test_gas_stockage_temporal_2025_2026(self):
        """Taux change au 01/04/2026 (ATS3 2026 = +20%)."""
        r_2025 = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 100_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
        )
        r_2026 = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 100_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2026, 6, 1),
            period_end=date(2026, 6, 30),
        )
        s_2025 = next(c for c in r_2025.components if c.code == "stockage_gaz")
        s_2026 = next(c for c in r_2026.components if c.code == "stockage_gaz")
        assert s_2026.inputs_used["shadow_amount_ht"] > s_2025.inputs_used["shadow_amount_ht"]


class TestGasCeeShadow:
    """CEE shadow gaz."""

    def test_cee_shadow_gaz_present(self):
        """CEE shadow existe dans la décomposition gaz."""
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
        assert "cee_shadow" in codes
        cee = next(c for c in r.components if c.code == "cee_shadow")
        assert cee.amount_ht == 0.0
        assert cee.inputs_used["shadow_amount_ht"] > 0


class TestGasGrdCode:
    """Péréquation gaz — paramètre grd_code."""

    def test_gas_grd_code_default(self):
        """Par défaut grd_code=GRDF, résultat identique."""
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
        assert any("GRDF" in a for a in r.assumptions)

    def test_gas_grd_code_traced(self):
        """GRD code ELD tracé dans assumptions."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 50_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
            grd_code="REGIE_STRASBOURG",
        )
        assert any("REGIE_STRASBOURG" in a for a in r.assumptions)


class TestGasAtrtTemporal:
    """ATRT gaz — résolution temporelle 2023 vs 2025."""

    def test_gas_atrt_2023(self):
        """Facture gaz 2023 : ATRT 2023 = 0.00240."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 50_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2023, 10, 1),
            period_end=date(2023, 10, 31),
        )
        atrt = next(c for c in r.components if c.code == "atrt")
        assert atrt.amount_ht == pytest.approx(50_000 * 0.00240, abs=0.5)

    def test_gas_atrt_2025(self):
        """Facture gaz post avr 2025 : ATRT 2025 = 0.00267."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 50_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 10, 1),
            period_end=date(2025, 10, 31),
        )
        atrt = next(c for c in r.components if c.code == "atrt")
        assert atrt.amount_ht == pytest.approx(50_000 * 0.00267, abs=0.5)


class TestGasTicgnTemporal:
    """TICGN gaz — résolution temporelle 2023/2024/2026."""

    def test_gas_ticgn_2023(self):
        """2023 : TICGN réduite 8.41 EUR/MWh (bouclier)."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 100_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2023, 6, 1),
            period_end=date(2023, 6, 30),
        )
        ticgn = next(c for c in r.components if c.code == "ticgn")
        assert ticgn.amount_ht == pytest.approx(100_000 * 0.00841, abs=0.5)

    def test_gas_ticgn_2024(self):
        """2024 : TICGN retour 16.37 EUR/MWh."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 100_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2024, 6, 1),
            period_end=date(2024, 6, 30),
        )
        ticgn = next(c for c in r.components if c.code == "ticgn")
        assert ticgn.amount_ht == pytest.approx(100_000 * 0.01637, abs=0.5)

    def test_gas_ticgn_2026(self):
        """Fév 2026+ : TICGN 16.39 EUR/MWh."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 100_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
        )
        ticgn = next(c for c in r.components if c.code == "ticgn")
        assert ticgn.amount_ht == pytest.approx(100_000 * 0.01639, abs=0.5)


class TestGasCpbShadow:
    """CPB gaz — shadow composante biogaz."""

    def test_cpb_shadow_present_post_2026(self):
        """CPB shadow présent pour factures post 01/01/2026."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 50_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
        )
        codes = {c.code for c in r.components}
        assert "cpb_shadow" in codes
        cpb = next(c for c in r.components if c.code == "cpb_shadow")
        assert cpb.amount_ht == 0.0
        assert cpb.inputs_used["shadow_amount_ht"] == pytest.approx(50_000 * 0.00035, abs=0.1)

    def test_cpb_shadow_absent_pre_2026(self):
        """Pas de CPB avant 2026."""
        r = build_invoice_reconstitution(
            energy_type="GAZ",
            subscribed_power_kva=None,
            tariff_option=None,
            kwh_by_period={"BASE": 50_000},
            supply_prices_by_period={"BASE": 0.09},
            period_start=date(2025, 6, 1),
            period_end=date(2025, 6, 30),
        )
        codes = {c.code for c in r.components}
        assert "cpb_shadow" not in codes
