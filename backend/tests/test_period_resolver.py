"""
Tests du résolveur unifié de période tarifaire (period_resolver).

Couverture :
  1. is_in_hc_window — fenêtres overnight, intra-journée, multiples, vides
  2. select_windows — saisonnalisation hiver/été, fallback
  3. resolve_period — avec TOUSchedule, sans DB, fallback turpe_calendar
  4. resolve_period_binary — wrapper HP/HC
  5. Scénarios reprogrammation HC (avant/après bascule)
  6. Intégration classify_period (wrapper backward-compatible)

Sources :
  - CRE TURPE 7 délibération n°2025-78
  - CRE délibération n°2026-33 (levée gel HC 11-14h hiver)
"""

import pytest
from datetime import datetime

from services.billing_engine.period_resolver import (
    is_in_hc_window,
    select_windows,
    resolve_period,
    resolve_period_binary,
    resolve_period_no_db,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. IS_IN_HC_WINDOW
# ═══════════════════════════════════════════════════════════════════════════════


class TestIsInHcWindow:
    """Tests fenêtres HC consommateur."""

    def test_overnight_before_midnight(self):
        """23h dans fenêtre HC 23:00-07:00 → True"""
        windows = [{"start": "23:00", "end": "07:00", "period": "HC"}]
        assert is_in_hc_window(23, 0, windows) is True

    def test_overnight_after_midnight(self):
        """03h dans fenêtre HC 23:00-07:00 → True"""
        windows = [{"start": "23:00", "end": "07:00", "period": "HC"}]
        assert is_in_hc_window(3, 0, windows) is True

    def test_overnight_outside(self):
        """10h hors fenêtre HC 23:00-07:00 → False"""
        windows = [{"start": "23:00", "end": "07:00", "period": "HC"}]
        assert is_in_hc_window(10, 0, windows) is False

    def test_overnight_boundary_start_inclusive(self):
        """23h00 dans fenêtre HC 23:00-07:00 → True (inclusive)"""
        windows = [{"start": "23:00", "end": "07:00", "period": "HC"}]
        assert is_in_hc_window(23, 0, windows) is True

    def test_overnight_boundary_end_exclusive(self):
        """07h00 hors fenêtre HC 23:00-07:00 → False (exclusive)"""
        windows = [{"start": "23:00", "end": "07:00", "period": "HC"}]
        assert is_in_hc_window(7, 0, windows) is False

    def test_daytime_window(self):
        """12h dans fenêtre HC 11:00-14:00 → True"""
        windows = [{"start": "11:00", "end": "14:00", "period": "HCB"}]
        assert is_in_hc_window(12, 0, windows) is True

    def test_daytime_boundary_start(self):
        """11h00 dans fenêtre HC 11:00-14:00 → True"""
        windows = [{"start": "11:00", "end": "14:00", "period": "HCB"}]
        assert is_in_hc_window(11, 0, windows) is True

    def test_daytime_boundary_end(self):
        """14h00 hors fenêtre HC 11:00-14:00 → False"""
        windows = [{"start": "11:00", "end": "14:00", "period": "HCB"}]
        assert is_in_hc_window(14, 0, windows) is False

    def test_multiple_windows(self):
        """Fenêtres combinées 23:00-07:00 + 11:00-14:00"""
        windows = [
            {"start": "23:00", "end": "07:00", "period": "HCH"},
            {"start": "11:00", "end": "14:00", "period": "HCH"},
        ]
        assert is_in_hc_window(2, 0, windows) is True  # nuit
        assert is_in_hc_window(12, 0, windows) is True  # méridienne
        assert is_in_hc_window(9, 0, windows) is False  # HP matin

    def test_empty_windows(self):
        """Pas de fenêtre HC → jamais HC"""
        assert is_in_hc_window(3, 0, []) is False

    def test_hp_windows_ignored(self):
        """Fenêtre HP (pas HC) → ignorée"""
        windows = [{"start": "06:00", "end": "22:00", "period": "HP"}]
        assert is_in_hc_window(10, 0, windows) is False

    def test_minute_precision(self):
        """23h30 dans fenêtre HC 23:30-07:00 → True"""
        windows = [{"start": "23:30", "end": "07:00", "period": "HC"}]
        assert is_in_hc_window(23, 30, windows) is True
        assert is_in_hc_window(23, 29, windows) is False


# ═══════════════════════════════════════════════════════════════════════════════
# 2. SELECT_WINDOWS
# ═══════════════════════════════════════════════════════════════════════════════


class TestSelectWindows:
    """Tests sélection saisonnière des fenêtres."""

    WINDOWS_HIVER = [{"start": "23:00", "end": "07:00", "period": "HCH"}]
    WINDOWS_ETE = [
        {"start": "01:00", "end": "06:00", "period": "HCB"},
        {"start": "12:00", "end": "15:00", "period": "HCB"},
    ]

    def test_non_seasonal_always_same(self):
        """Non-saisonnalisé → windows quel que soit le mois"""
        sched = {"windows": self.WINDOWS_HIVER, "windows_ete": self.WINDOWS_ETE, "is_seasonal": False}
        assert select_windows(sched, 1) == self.WINDOWS_HIVER
        assert select_windows(sched, 7) == self.WINDOWS_HIVER

    def test_seasonal_winter(self):
        """Saisonnalisé, janvier → windows (hiver)"""
        sched = {"windows": self.WINDOWS_HIVER, "windows_ete": self.WINDOWS_ETE, "is_seasonal": True}
        assert select_windows(sched, 1) == self.WINDOWS_HIVER
        assert select_windows(sched, 11) == self.WINDOWS_HIVER
        assert select_windows(sched, 3) == self.WINDOWS_HIVER

    def test_seasonal_summer(self):
        """Saisonnalisé, juillet → windows_ete"""
        sched = {"windows": self.WINDOWS_HIVER, "windows_ete": self.WINDOWS_ETE, "is_seasonal": True}
        assert select_windows(sched, 4) == self.WINDOWS_ETE
        assert select_windows(sched, 7) == self.WINDOWS_ETE
        assert select_windows(sched, 10) == self.WINDOWS_ETE

    def test_seasonal_no_ete_fallback(self):
        """Saisonnalisé mais pas de windows_ete → fallback windows"""
        sched = {"windows": self.WINDOWS_HIVER, "windows_ete": None, "is_seasonal": True}
        assert select_windows(sched, 7) == self.WINDOWS_HIVER

    def test_boundary_march_is_winter(self):
        """Mars = saison haute (hiver) → windows"""
        sched = {"windows": self.WINDOWS_HIVER, "windows_ete": self.WINDOWS_ETE, "is_seasonal": True}
        assert select_windows(sched, 3) == self.WINDOWS_HIVER

    def test_boundary_april_is_summer(self):
        """Avril = saison basse (été) → windows_ete"""
        sched = {"windows": self.WINDOWS_HIVER, "windows_ete": self.WINDOWS_ETE, "is_seasonal": True}
        assert select_windows(sched, 4) == self.WINDOWS_ETE


# ═══════════════════════════════════════════════════════════════════════════════
# 3. RESOLVE_PERIOD (sans DB)
# ═══════════════════════════════════════════════════════════════════════════════


class TestResolvePeriod:
    """Tests résolution complète avec TOUSchedule dict (sans DB)."""

    # Schedule legacy non-saisonnalisé (22h-06h)
    LEGACY_SCHED = {
        "windows": [
            {"day_types": ["weekday"], "start": "22:00", "end": "06:00", "period": "HC"},
            {"day_types": ["weekday"], "start": "06:00", "end": "22:00", "period": "HP"},
            {"day_types": ["weekend", "holiday"], "start": "00:00", "end": "24:00", "period": "HC"},
        ],
        "windows_ete": None,
        "is_seasonal": False,
    }

    # Schedule saisonnalisé Phase 2 (Nice)
    SEASONAL_SCHED = {
        "windows": [  # Hiver: HC 23h-07h
            {"day_types": ["weekday", "weekend", "holiday"], "start": "23:00", "end": "07:00", "period": "HCH"},
            {"day_types": ["weekday", "weekend", "holiday"], "start": "07:00", "end": "23:00", "period": "HPH"},
        ],
        "windows_ete": [  # Été: HC 01h-06h + 12h-15h
            {"day_types": ["weekday", "weekend", "holiday"], "start": "01:00", "end": "06:00", "period": "HCB"},
            {"day_types": ["weekday", "weekend", "holiday"], "start": "12:00", "end": "15:00", "period": "HCB"},
            {"day_types": ["weekday", "weekend", "holiday"], "start": "00:00", "end": "01:00", "period": "HPB"},
            {"day_types": ["weekday", "weekend", "holiday"], "start": "06:00", "end": "12:00", "period": "HPB"},
            {"day_types": ["weekday", "weekend", "holiday"], "start": "15:00", "end": "24:00", "period": "HPB"},
        ],
        "is_seasonal": True,
    }

    # ── Legacy schedule ──

    def test_legacy_winter_night_hc(self):
        """Janvier 3h avec legacy 22-06 → HCH (hiver + HC)"""
        result = resolve_period(datetime(2026, 1, 15, 3, 0), tou_schedule=self.LEGACY_SCHED)
        assert result == "HCH"

    def test_legacy_winter_day_hp(self):
        """Janvier 10h avec legacy 06-22 → HPH (hiver + HP)"""
        result = resolve_period(datetime(2026, 1, 15, 10, 0), tou_schedule=self.LEGACY_SCHED)
        assert result == "HPH"

    def test_legacy_summer_night_hc(self):
        """Juillet 3h avec legacy 22-06 → HCB (été + HC)"""
        result = resolve_period(datetime(2026, 7, 15, 3, 0), tou_schedule=self.LEGACY_SCHED)
        assert result == "HCB"

    def test_legacy_summer_day_hp(self):
        """Juillet 14h avec legacy 06-22 → HPB (été + HP)"""
        result = resolve_period(datetime(2026, 7, 15, 14, 0), tou_schedule=self.LEGACY_SCHED)
        assert result == "HPB"

    # ── Seasonal schedule (Phase 2) ──

    def test_seasonal_winter_night_hch(self):
        """Janvier 3h avec HC saisonnalisé 23-07 → HCH"""
        result = resolve_period(datetime(2026, 1, 15, 3, 0), tou_schedule=self.SEASONAL_SCHED)
        assert result == "HCH"

    def test_seasonal_winter_day_hph(self):
        """Janvier 10h avec saisonnalisé → HPH"""
        result = resolve_period(datetime(2026, 1, 15, 10, 0), tou_schedule=self.SEASONAL_SCHED)
        assert result == "HPH"

    def test_seasonal_summer_night_hcb(self):
        """Juillet 3h avec HC saisonnalisé été 01-06 → HCB"""
        result = resolve_period(datetime(2026, 7, 15, 3, 0), tou_schedule=self.SEASONAL_SCHED)
        assert result == "HCB"

    def test_seasonal_summer_meridien_hcb(self):
        """Juillet 13h avec HC saisonnalisé été 12-15 → HCB (méridienne)"""
        result = resolve_period(datetime(2026, 7, 15, 13, 0), tou_schedule=self.SEASONAL_SCHED)
        assert result == "HCB"

    def test_seasonal_summer_morning_hpb(self):
        """Juillet 9h → HPB (pas dans les fenêtres HC été)"""
        result = resolve_period(datetime(2026, 7, 15, 9, 0), tou_schedule=self.SEASONAL_SCHED)
        assert result == "HPB"

    def test_seasonal_summer_evening_hpb(self):
        """Juillet 20h → HPB (soirée, HP été)"""
        result = resolve_period(datetime(2026, 7, 15, 20, 0), tou_schedule=self.SEASONAL_SCHED)
        assert result == "HPB"

    # ── Fallback (sans schedule) ──

    def test_fallback_no_schedule(self):
        """Sans TOUSchedule → fallback turpe_calendar"""
        result = resolve_period(datetime(2026, 1, 15, 3, 0))
        assert result == "HCH"  # 3h en janvier = HC hiver via turpe_calendar

    def test_fallback_summer(self):
        """Sans TOUSchedule, juillet 10h → HPB via turpe_calendar"""
        # 15 juillet 2026 = mercredi, 10h = HP en postes TURPE
        result = resolve_period(datetime(2026, 7, 15, 10, 0))
        assert result == "HPB"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. RESOLVE_PERIOD_BINARY
# ═══════════════════════════════════════════════════════════════════════════════


class TestResolvePeriodBinary:
    """Tests wrapper HP/HC binaire."""

    def test_binary_hp(self):
        result = resolve_period_binary(datetime(2026, 1, 15, 10, 0))
        assert result == "HP"

    def test_binary_hc(self):
        result = resolve_period_binary(datetime(2026, 1, 15, 3, 0))
        assert result == "HC"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SCÉNARIOS REPROGRAMMATION HC
# ═══════════════════════════════════════════════════════════════════════════════


class TestReprogScenarios:
    """Scénarios avant/après reprogrammation HC."""

    BEFORE = {
        "windows": [
            {"day_types": ["weekday", "weekend", "holiday"], "start": "22:00", "end": "06:00", "period": "HC"},
            {"day_types": ["weekday", "weekend", "holiday"], "start": "06:00", "end": "22:00", "period": "HP"},
        ],
        "windows_ete": None,
        "is_seasonal": False,
    }

    AFTER = {
        "windows": [
            {"day_types": ["weekday", "weekend", "holiday"], "start": "23:00", "end": "07:00", "period": "HCH"},
            {"day_types": ["weekday", "weekend", "holiday"], "start": "07:00", "end": "23:00", "period": "HPH"},
        ],
        "windows_ete": [
            {"day_types": ["weekday", "weekend", "holiday"], "start": "01:00", "end": "06:00", "period": "HCB"},
            {"day_types": ["weekday", "weekend", "holiday"], "start": "12:00", "end": "15:00", "period": "HCB"},
            {"day_types": ["weekday", "weekend", "holiday"], "start": "00:00", "end": "01:00", "period": "HPB"},
            {"day_types": ["weekday", "weekend", "holiday"], "start": "06:00", "end": "12:00", "period": "HPB"},
            {"day_types": ["weekday", "weekend", "holiday"], "start": "15:00", "end": "24:00", "period": "HPB"},
        ],
        "is_seasonal": True,
    }

    def test_22h_shift_before(self):
        """Avant reprog : 22h = HC (ancien 22-06)"""
        result = resolve_period(datetime(2026, 1, 15, 22, 0), tou_schedule=self.BEFORE)
        assert result == "HCH"

    def test_22h_shift_after(self):
        """Après reprog : 22h = HP (nouveau 23-07) → surcoût client"""
        result = resolve_period(datetime(2026, 1, 15, 22, 0), tou_schedule=self.AFTER)
        assert result == "HPH"

    def test_06h_shift_before(self):
        """Avant reprog : 06h = HP (ancien 06-22)"""
        result = resolve_period(datetime(2026, 1, 15, 6, 0), tou_schedule=self.BEFORE)
        assert result == "HPH"

    def test_06h_shift_after(self):
        """Après reprog : 06h = HC (nouveau 23-07) → gain client"""
        result = resolve_period(datetime(2026, 1, 15, 6, 0), tou_schedule=self.AFTER)
        assert result == "HCH"

    def test_meridienne_ete_after(self):
        """Après reprog été : 13h = HC (méridienne 12-15)"""
        result = resolve_period(datetime(2026, 7, 15, 13, 0), tou_schedule=self.AFTER)
        assert result == "HCB"

    def test_meridienne_ete_before(self):
        """Avant reprog : 13h = HP (pas de méridienne)"""
        result = resolve_period(datetime(2026, 7, 15, 13, 0), tou_schedule=self.BEFORE)
        assert result == "HPB"

    def test_impact_financier_22h_shift(self):
        """22h passe de HC à HP après reprog → impact mesurable"""
        ts = datetime(2026, 1, 15, 22, 0)
        old = resolve_period(ts, tou_schedule=self.BEFORE)
        new = resolve_period(ts, tou_schedule=self.AFTER)
        assert "HC" in old  # avant: HC
        assert "HP" in new  # après: HP


# ═══════════════════════════════════════════════════════════════════════════════
# 6. INTÉGRATION classify_period (backward-compat)
# ═══════════════════════════════════════════════════════════════════════════════


class TestClassifyPeriodWrapper:
    """Vérifie que classify_period délègue correctement au resolver."""

    def test_classify_returns_tariff_period_enum(self):
        """classify_period retourne TariffPeriod enum (pas str)."""
        from services.tariff_period_classifier import classify_period, TariffPeriod

        result = classify_period(datetime(2026, 1, 15, 10, 0))
        assert isinstance(result, TariffPeriod)

    def test_classify_winter_hp(self):
        """10h lundi janvier → HPH"""
        from services.tariff_period_classifier import classify_period, TariffPeriod

        # 15 janvier 2026 = jeudi
        result = classify_period(datetime(2026, 1, 15, 10, 0))
        assert result == TariffPeriod.HPH

    def test_classify_winter_hc_night(self):
        """3h lundi janvier → HCH"""
        from services.tariff_period_classifier import classify_period, TariffPeriod

        result = classify_period(datetime(2026, 1, 15, 3, 0))
        assert result == TariffPeriod.HCH

    def test_classify_summer_hp(self):
        """10h mercredi juillet → HPB"""
        from services.tariff_period_classifier import classify_period, TariffPeriod

        result = classify_period(datetime(2026, 7, 15, 10, 0))
        assert result == TariffPeriod.HPB

    def test_classify_summer_hc(self):
        """3h mercredi juillet → HCB"""
        from services.tariff_period_classifier import classify_period, TariffPeriod

        result = classify_period(datetime(2026, 7, 15, 3, 0))
        assert result == TariffPeriod.HCB

    def test_classify_sunday_winter_hc(self):
        """10h dimanche janvier → HCH (dimanche = HC toute la journée en TURPE)"""
        from services.tariff_period_classifier import classify_period, TariffPeriod

        # 18 janvier 2026 = dimanche
        result = classify_period(datetime(2026, 1, 18, 10, 0))
        assert result == TariffPeriod.HCH

    def test_classify_holiday_hc(self):
        """10h jour de l'An → HCH (férié = HC en TURPE)"""
        from services.tariff_period_classifier import classify_period, TariffPeriod

        result = classify_period(datetime(2026, 1, 1, 10, 0))
        assert result == TariffPeriod.HCH

    def test_classify_pointe(self):
        """9h décembre avec has_pointe=True → POINTE"""
        from services.tariff_period_classifier import classify_period, TariffPeriod

        # 15 décembre 2025 = lundi
        result = classify_period(datetime(2025, 12, 15, 9, 0), has_pointe=True)
        assert result == TariffPeriod.POINTE

    def test_classify_value_attribute(self):
        """classify_period().value retourne une string (utilisé par cost_by_period)."""
        from services.tariff_period_classifier import classify_period

        result = classify_period(datetime(2026, 1, 15, 10, 0))
        assert result.value == "HPH"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. RESOLVE_PERIOD_NO_DB
# ═══════════════════════════════════════════════════════════════════════════════


class TestResolvePeriodNoDb:
    """Tests fallback pur turpe_calendar."""

    def test_winter_hp(self):
        """Lundi 10h janvier → HPH"""
        assert resolve_period_no_db(datetime(2026, 1, 19, 10, 0)) == "HPH"

    def test_winter_hc(self):
        """3h janvier → HCH"""
        assert resolve_period_no_db(datetime(2026, 1, 19, 3, 0)) == "HCH"

    def test_summer_hp(self):
        """10h juillet → HPB"""
        assert resolve_period_no_db(datetime(2026, 7, 15, 10, 0)) == "HPB"

    def test_summer_hc(self):
        """3h juillet → HCB"""
        assert resolve_period_no_db(datetime(2026, 7, 15, 3, 0)) == "HCB"
