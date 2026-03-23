"""
Tests unitaires — Résolveur saisonnière kWh TURPE 7.

Couverture:
  1. Passthrough (BASE, HP/HC déjà OK)
  2. Upgrade 2P → 4P (HP/HC → HPH/HCH/HPB/HCB)
  3. Ratios saisonniers (mois hiver, mois été, période à cheval)
  4. Conservation de la somme kWh
  5. Intégration avec le billing engine

Sources vérifiées :
  - CRE TURPE 7 délibération n°2025-78
  - CRE délibération n°2026-33 du 4 février 2026
"""

import pytest
from datetime import date

from services.billing_engine.seasonal_resolver import (
    needs_seasonal_upgrade,
    resolve_kwh_by_season,
    compute_seasonal_ratios,
    _apply_ratios,
)
from services.billing_engine.types import TariffOption, TariffSegment


# ═══════════════════════════════════════════════════════════════════════════════
# 1. NEEDS_SEASONAL_UPGRADE
# ═══════════════════════════════════════════════════════════════════════════════


class TestNeedsSeasonalUpgrade:
    def test_base_no_upgrade(self):
        """Option BASE ne nécessite jamais d'upgrade."""
        assert needs_seasonal_upgrade({"BASE": 10000}, TariffOption.BASE, TariffSegment.C5_BT) is False

    def test_hp_hc_no_upgrade(self):
        """Option HP_HC simple ne nécessite pas d'upgrade."""
        assert needs_seasonal_upgrade({"HP": 6500, "HC": 3500}, TariffOption.HP_HC, TariffSegment.C5_BT) is False

    def test_cu_with_hp_hc_needs_upgrade(self):
        """Option CU avec données HP/HC → upgrade nécessaire."""
        assert needs_seasonal_upgrade({"HP": 6500, "HC": 3500}, TariffOption.CU, TariffSegment.C4_BT) is True

    def test_lu_with_base_needs_upgrade(self):
        """Option LU avec données BASE → upgrade nécessaire."""
        assert needs_seasonal_upgrade({"BASE": 10000}, TariffOption.LU, TariffSegment.C4_BT) is True

    def test_mu_with_4p_no_upgrade(self):
        """Option MU avec données déjà en 4P → pas d'upgrade."""
        assert (
            needs_seasonal_upgrade(
                {"HPH": 3000, "HCH": 1500, "HPB": 3800, "HCB": 1700}, TariffOption.MU, TariffSegment.C4_BT
            )
            is False
        )

    def test_cu_c5_with_hp_hc_needs_upgrade(self):
        """Option CU (CU4 C5) avec HP/HC → upgrade."""
        assert needs_seasonal_upgrade({"HP": 6500, "HC": 3500}, TariffOption.CU, TariffSegment.C5_BT) is True


# ═══════════════════════════════════════════════════════════════════════════════
# 2. RESOLVE_KWH_BY_SEASON — PASSTHROUGH
# ═══════════════════════════════════════════════════════════════════════════════


class TestResolvePassthrough:
    def test_base_passthrough(self):
        """Option BASE → retourne {'BASE': total}."""
        result = resolve_kwh_by_season(
            total_kwh=10000,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 2, 1),
            tariff_option=TariffOption.BASE,
        )
        assert result == {"BASE": 10000}

    def test_hp_hc_non_seasonal(self):
        """Option HP_HC non saisonnalisé → résolution 2 plages."""
        result = resolve_kwh_by_season(
            total_kwh=10000,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 2, 1),
            tariff_option=TariffOption.HP_HC,
            is_seasonal=False,
        )
        assert set(result.keys()) == {"HP", "HC"}
        assert sum(result.values()) == pytest.approx(10000, abs=1)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. RESOLVE_KWH_BY_SEASON — 4 PLAGES
# ═══════════════════════════════════════════════════════════════════════════════


class TestResolve4Plages:
    def test_cu_january_4p(self):
        """CU en janvier → HPH + HCH uniquement (100% hiver)."""
        result = resolve_kwh_by_season(
            total_kwh=10000,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 2, 1),
            tariff_option=TariffOption.CU,
        )
        assert set(result.keys()) == {"HPH", "HCH", "HPB", "HCB"}
        assert result["HPB"] == 0.0
        assert result["HCB"] == 0.0
        assert result["HPH"] > 0
        assert result["HCH"] > 0
        assert sum(result.values()) == pytest.approx(10000, abs=1)

    def test_lu_july_4p(self):
        """LU en juillet → HPB + HCB uniquement (100% été)."""
        result = resolve_kwh_by_season(
            total_kwh=12000,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 8, 1),
            tariff_option=TariffOption.LU,
        )
        assert result["HPH"] == 0.0
        assert result["HCH"] == 0.0
        assert result["HPB"] > 0
        assert result["HCB"] > 0
        assert sum(result.values()) == pytest.approx(12000, abs=1)

    def test_mu_november_4p(self):
        """MU en novembre → 100% hiver (nov = saison haute)."""
        result = resolve_kwh_by_season(
            total_kwh=8000,
            period_start=date(2026, 11, 1),
            period_end=date(2026, 12, 1),
            tariff_option=TariffOption.MU,
        )
        assert result["HPB"] == 0.0
        assert result["HCB"] == 0.0
        assert sum(result.values()) == pytest.approx(8000, abs=1)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CONSERVATION DE LA SOMME
# ═══════════════════════════════════════════════════════════════════════════════


class TestSumPreservation:
    def test_kwh_sum_preserved_january(self):
        """sum(kWh par plage) == total kWh (janvier)."""
        result = resolve_kwh_by_season(
            total_kwh=15000,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 2, 1),
            tariff_option=TariffOption.CU,
        )
        assert sum(result.values()) == pytest.approx(15000, abs=1)

    def test_kwh_sum_preserved_july(self):
        """sum(kWh par plage) == total kWh (juillet)."""
        result = resolve_kwh_by_season(
            total_kwh=20000,
            period_start=date(2026, 7, 1),
            period_end=date(2026, 8, 1),
            tariff_option=TariffOption.LU,
        )
        assert sum(result.values()) == pytest.approx(20000, abs=1)

    def test_kwh_sum_preserved_cross_season(self):
        """sum(kWh) préservée sur période à cheval hiver/été (mars→avril)."""
        result = resolve_kwh_by_season(
            total_kwh=10000,
            period_start=date(2026, 3, 15),
            period_end=date(2026, 4, 15),
            tariff_option=TariffOption.MU,
        )
        assert sum(result.values()) == pytest.approx(10000, abs=1)
        # Période à cheval → les 4 plages doivent être > 0
        assert result["HPH"] > 0
        assert result["HCH"] > 0
        assert result["HPB"] > 0
        assert result["HCB"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 5. RATIOS SAISONNIERS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSeasonalRatios:
    def test_ratios_sum_to_one(self):
        """Ratios saisonniers somment toujours à 1.0."""
        ratios = compute_seasonal_ratios(date(2026, 1, 1), date(2026, 2, 1))
        assert sum(ratios.values()) == pytest.approx(1.0, abs=0.001)

    def test_ratios_january_hiver_only(self):
        """Janvier = 100% hiver → HPB/HCB = 0."""
        ratios = compute_seasonal_ratios(date(2026, 1, 1), date(2026, 2, 1))
        assert ratios["HPB"] == pytest.approx(0.0)
        assert ratios["HCB"] == pytest.approx(0.0)

    def test_ratios_july_ete_only(self):
        """Juillet = 100% été → HPH/HCH = 0."""
        ratios = compute_seasonal_ratios(date(2026, 7, 1), date(2026, 8, 1))
        assert ratios["HPH"] == pytest.approx(0.0)
        assert ratios["HCH"] == pytest.approx(0.0)

    def test_ratios_cross_season(self):
        """Mars→avril = période à cheval → 4 ratios > 0."""
        ratios = compute_seasonal_ratios(date(2026, 3, 15), date(2026, 4, 15))
        assert ratios["HPH"] > 0
        assert ratios["HCH"] > 0
        assert ratios["HPB"] > 0
        assert ratios["HCB"] > 0

    def test_ratios_legacy_2p(self):
        """Mode non saisonnalisé → 2 plages HP/HC."""
        ratios = compute_seasonal_ratios(date(2026, 1, 1), date(2026, 2, 1), is_seasonal=False)
        assert set(ratios.keys()) == {"HP", "HC"}
        assert sum(ratios.values()) == pytest.approx(1.0, abs=0.001)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. APPLY_RATIOS
# ═══════════════════════════════════════════════════════════════════════════════


class TestApplyRatios:
    def test_simple_ratios(self):
        """Application de ratios simples."""
        result = _apply_ratios(10000, {"A": 0.6, "B": 0.4})
        assert sum(result.values()) == pytest.approx(10000, abs=1)

    def test_empty_ratios(self):
        """Ratios vides → fallback BASE."""
        result = _apply_ratios(5000, {})
        assert result == {"BASE": 5000}

    def test_sum_preserved_with_rounding(self):
        """La somme est préservée malgré les arrondis."""
        result = _apply_ratios(10000, {"HPH": 0.333, "HCH": 0.167, "HPB": 0.333, "HCB": 0.167})
        assert sum(result.values()) == pytest.approx(10000, abs=1)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. INTÉGRATION BILLING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class TestBillingEngineIntegration:
    """Tests d'intégration : le billing engine utilise la résolution saisonnière."""

    def test_c4_lu_january_produces_4p_components(self):
        """C4 LU en janvier avec HP/HC → reconstitution avec 4 plages."""
        from services.billing_engine.engine import build_invoice_reconstitution

        result = build_invoice_reconstitution(
            energy_type="ELEC",
            subscribed_power_kva=108.0,
            tariff_option=TariffOption.LU,
            kwh_by_period={"HP": 9000, "HC": 3000},
            supply_prices_by_period={"HPH": 0.095, "HCH": 0.075, "HPB": 0.085, "HCB": 0.065},
            period_start=date(2026, 1, 1),
            period_end=date(2026, 2, 1),
        )
        # Devrait avoir des composantes TURPE soutirage en HPH/HCH (janvier = hiver)
        turpe_var_codes = [c.code for c in result.components if c.code.startswith("turpe_soutirage_")]
        assert "turpe_soutirage_hph" in turpe_var_codes
        assert "turpe_soutirage_hch" in turpe_var_codes

    def test_c5_cu4_june_produces_4p_components(self):
        """C5 CU (CU4) en juin avec BASE → reconstitution avec 4 plages été."""
        from services.billing_engine.engine import build_invoice_reconstitution

        result = build_invoice_reconstitution(
            energy_type="ELEC",
            subscribed_power_kva=12.0,
            tariff_option=TariffOption.CU,
            kwh_by_period={"BASE": 5000},
            supply_prices_by_period={"HPH": 0.095, "HCH": 0.075, "HPB": 0.085, "HCB": 0.065},
            period_start=date(2026, 6, 1),
            period_end=date(2026, 7, 1),
        )
        turpe_var_codes = [c.code for c in result.components if c.code.startswith("turpe_soutirage_")]
        assert "turpe_soutirage_hpb" in turpe_var_codes
        assert "turpe_soutirage_hcb" in turpe_var_codes

    def test_c5_hphc_remains_2p(self):
        """C5 HP_HC reste en 2 plages (pas d'upgrade)."""
        from services.billing_engine.engine import build_invoice_reconstitution

        result = build_invoice_reconstitution(
            energy_type="ELEC",
            subscribed_power_kva=6.0,
            tariff_option=TariffOption.HP_HC,
            kwh_by_period={"HP": 3500, "HC": 1500},
            supply_prices_by_period={"HP": 0.1841, "HC": 0.1210},
            period_start=date(2026, 1, 1),
            period_end=date(2026, 2, 1),
        )
        turpe_var_codes = [c.code for c in result.components if c.code.startswith("turpe_soutirage_")]
        assert "turpe_soutirage_hp" in turpe_var_codes
        assert "turpe_soutirage_hc" in turpe_var_codes
        assert "turpe_soutirage_hph" not in turpe_var_codes
