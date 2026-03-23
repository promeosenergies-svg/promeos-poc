"""
Tests unitaires — Calendrier TURPE 7 officiel.

Couverture:
  1. Saisons TURPE (hiver/été)
  2. Jours fériés français (fixes + mobiles)
  3. Types de jours (semaine/samedi/dimanche/férié)
  4. Postes horosaisonniers TURPE (HP lun-sam 8-22h, HC 22-8h + dim + fériés)
  5. Mode legacy C5 (HP 06-22, HC 22-06)
  6. Couverture 24h (pas de trou)
  7. Comptage d'heures par période sur une période
  8. Résolution datetime → code de période

Sources vérifiées :
  - CRE délibération n°2025-78 (TURPE 7)
  - CRE délibération n°2026-33 du 4 février 2026 (levée gel HC 11-14h)
  - Enedis brochure TURPE 7 (postes horosaisonniers)
  - Code du travail art. L3133-1 (jours fériés)
"""

import pytest
from datetime import date, datetime

from services.billing_engine.turpe_calendar import (
    get_season,
    is_jour_ferie,
    get_day_type,
    is_hp_hour,
    get_period_for_datetime,
    count_hours_by_period,
    count_hours_by_period_ratios,
    _paques,
    _jours_feries_annee,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SAISONS TURPE
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetSeason:
    """Saison haute = hiver (nov-mars), saison basse = été (avr-oct)."""

    def test_season_january(self):
        assert get_season(date(2026, 1, 15)) == "HIVER"

    def test_season_february(self):
        assert get_season(date(2026, 2, 1)) == "HIVER"

    def test_season_march(self):
        """Mars = dernier mois hiver (mois frontière)."""
        assert get_season(date(2026, 3, 31)) == "HIVER"

    def test_season_april(self):
        """Avril = premier mois été (mois frontière)."""
        assert get_season(date(2026, 4, 1)) == "ETE"

    def test_season_july(self):
        assert get_season(date(2026, 7, 14)) == "ETE"

    def test_season_october(self):
        """Octobre = dernier mois été."""
        assert get_season(date(2026, 10, 31)) == "ETE"

    def test_season_november(self):
        """Novembre = premier mois hiver (mois frontière)."""
        assert get_season(date(2026, 11, 1)) == "HIVER"

    def test_season_december(self):
        assert get_season(date(2026, 12, 25)) == "HIVER"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. JOURS FERIÉS FRANÇAIS
# ═══════════════════════════════════════════════════════════════════════════════


class TestJoursFeries:
    """Jours fériés fixes et mobiles (Pâques, Ascension, Pentecôte)."""

    # Fériés fixes
    def test_jour_an(self):
        assert is_jour_ferie(date(2026, 1, 1)) is True

    def test_fete_travail(self):
        assert is_jour_ferie(date(2026, 5, 1)) is True

    def test_victoire_1945(self):
        assert is_jour_ferie(date(2026, 5, 8)) is True

    def test_fete_nationale(self):
        assert is_jour_ferie(date(2026, 7, 14)) is True

    def test_assomption(self):
        assert is_jour_ferie(date(2026, 8, 15)) is True

    def test_toussaint(self):
        assert is_jour_ferie(date(2026, 11, 1)) is True

    def test_armistice(self):
        assert is_jour_ferie(date(2026, 11, 11)) is True

    def test_noel(self):
        assert is_jour_ferie(date(2026, 12, 25)) is True

    # Fériés mobiles 2026 (Pâques = 5 avril 2026)
    def test_paques_2026(self):
        """Pâques 2026 = 5 avril (vérifié calendrier grégorien)."""
        assert _paques(2026) == date(2026, 4, 5)

    def test_lundi_paques_2026(self):
        """Lundi de Pâques 2026 = 6 avril."""
        assert is_jour_ferie(date(2026, 4, 6)) is True

    def test_ascension_2026(self):
        """Ascension 2026 = Pâques + 39 jours = 14 mai."""
        assert is_jour_ferie(date(2026, 5, 14)) is True

    def test_pentecote_2026(self):
        """Lundi Pentecôte 2026 = Pâques + 50 jours = 25 mai."""
        assert is_jour_ferie(date(2026, 5, 25)) is True

    # Non fériés
    def test_jour_normal(self):
        assert is_jour_ferie(date(2026, 3, 15)) is False

    def test_dimanche_non_ferie(self):
        """Un dimanche normal n'est pas férié."""
        assert is_jour_ferie(date(2026, 3, 22)) is False

    # Cross-check 2025
    def test_paques_2025(self):
        """Pâques 2025 = 20 avril."""
        assert _paques(2025) == date(2025, 4, 20)

    def test_11_feries_par_an(self):
        """La France a 11 jours fériés par an."""
        feries_2026 = _jours_feries_annee(2026)
        assert len(feries_2026) == 11


# ═══════════════════════════════════════════════════════════════════════════════
# 3. TYPES DE JOURS — avec distinction samedi/dimanche
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetDayType:
    """En postes TURPE: samedi = ouvré, dimanche = HC toute la journée."""

    def test_weekday_monday(self):
        """Lundi 16 mars 2026 = weekday."""
        assert get_day_type(date(2026, 3, 16)) == "weekday"

    def test_weekday_friday(self):
        """Vendredi 20 mars 2026 = weekday."""
        assert get_day_type(date(2026, 3, 20)) == "weekday"

    def test_saturday(self):
        """Samedi 21 mars 2026 = saturday (ouvré TURPE, pas dimanche)."""
        assert get_day_type(date(2026, 3, 21)) == "saturday"

    def test_sunday(self):
        """Dimanche 22 mars 2026 = sunday (HC toute la journée TURPE)."""
        assert get_day_type(date(2026, 3, 22)) == "sunday"

    def test_holiday_on_weekday(self):
        """14 juillet 2026 = mardi → holiday (prioritaire)."""
        assert get_day_type(date(2026, 7, 14)) == "holiday"

    def test_holiday_on_sunday(self):
        """1er novembre 2026 = dimanche → holiday (prioritaire sur sunday)."""
        assert get_day_type(date(2026, 11, 1)) == "holiday"

    def test_holiday_on_saturday(self):
        """15 août 2026 = samedi → holiday (prioritaire sur saturday)."""
        assert get_day_type(date(2026, 8, 15)) == "holiday"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. POSTES HOROSAISONNIERS TURPE (C4/HTA)
# ═══════════════════════════════════════════════════════════════════════════════


class TestIsHpHourTurpe:
    """Postes TURPE: HP lun-sam 8h-22h (14h), HC 22h-8h + dim + fériés."""

    # ── Jour ouvré (lundi-vendredi) ──
    def test_ouvre_03h_hc(self):
        """03h jour ouvré = HC (nuit)."""
        assert is_hp_hour(3, "weekday") is False

    def test_ouvre_07h_hc(self):
        """07h jour ouvré = HC (avant 8h)."""
        assert is_hp_hour(7, "weekday") is False

    def test_ouvre_08h_hp(self):
        """08h jour ouvré = HP (début plage HP)."""
        assert is_hp_hour(8, "weekday") is True

    def test_ouvre_12h_hp(self):
        """12h jour ouvré = HP (milieu de journée)."""
        assert is_hp_hour(12, "weekday") is True

    def test_ouvre_21h_hp(self):
        """21h jour ouvré = HP (dernière heure HP)."""
        assert is_hp_hour(21, "weekday") is True

    def test_ouvre_22h_hc(self):
        """22h jour ouvré = HC (fin de plage HP)."""
        assert is_hp_hour(22, "weekday") is False

    # ── Samedi (= jour ouvré TURPE) ──
    def test_samedi_10h_hp(self):
        """10h samedi = HP (samedi = ouvré en TURPE)."""
        assert is_hp_hour(10, "saturday") is True

    def test_samedi_23h_hc(self):
        """23h samedi = HC."""
        assert is_hp_hour(23, "saturday") is False

    # ── Dimanche (= HC toute la journée) ──
    def test_dimanche_08h_hc(self):
        """08h dimanche = HC (dimanche toujours HC)."""
        assert is_hp_hour(8, "sunday") is False

    def test_dimanche_15h_hc(self):
        """15h dimanche = HC."""
        assert is_hp_hour(15, "sunday") is False

    # ── Jour férié (= comme dimanche, HC toute la journée) ──
    def test_ferie_10h_hc(self):
        """10h jour férié = HC."""
        assert is_hp_hour(10, "holiday") is False


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MODE LEGACY C5 (HP 06-22, HC 22-06)
# ═══════════════════════════════════════════════════════════════════════════════


class TestIsHpHourLegacy:
    """Legacy C5 HP/HC: HP 06h-22h (16h), HC 22h-06h (8h), tous jours."""

    def test_legacy_05h_hc(self):
        """05h = HC (avant 06h)."""
        assert is_hp_hour(5, "weekday", mode="LEGACY") is False

    def test_legacy_06h_hp(self):
        """06h = HP (début plage HP)."""
        assert is_hp_hour(6, "weekday", mode="LEGACY") is True

    def test_legacy_12h_hp(self):
        """12h = HP."""
        assert is_hp_hour(12, "weekday", mode="LEGACY") is True

    def test_legacy_21h_hp(self):
        """21h = HP (dernière heure HP)."""
        assert is_hp_hour(21, "weekday", mode="LEGACY") is True

    def test_legacy_22h_hc(self):
        """22h = HC."""
        assert is_hp_hour(22, "weekday", mode="LEGACY") is False

    def test_legacy_same_on_sunday(self):
        """Legacy: même plages le dimanche (pas de distinction)."""
        assert is_hp_hour(12, "sunday", mode="LEGACY") is True
        assert is_hp_hour(23, "sunday", mode="LEGACY") is False


# ═══════════════════════════════════════════════════════════════════════════════
# 6. COUVERTURE 24H — PAS DE TROU
# ═══════════════════════════════════════════════════════════════════════════════


class TestCoverage24h:
    """Chaque heure (0-23) doit être classifiée sans ambiguïté."""

    def test_24h_turpe_ouvre(self):
        """Postes TURPE jour ouvré: 14h HP (8-21), 10h HC (0-7 + 22-23)."""
        hp_count = sum(1 for h in range(24) if is_hp_hour(h, "weekday"))
        hc_count = 24 - hp_count
        assert hp_count == 14
        assert hc_count == 10
        assert hp_count + hc_count == 24

    def test_24h_turpe_samedi(self):
        """Samedi = même répartition que jour ouvré (14h HP, 10h HC)."""
        hp_count = sum(1 for h in range(24) if is_hp_hour(h, "saturday"))
        assert hp_count == 14

    def test_24h_turpe_dimanche(self):
        """Dimanche = 0h HP, 24h HC."""
        hp_count = sum(1 for h in range(24) if is_hp_hour(h, "sunday"))
        assert hp_count == 0

    def test_24h_turpe_ferie(self):
        """Jour férié = 0h HP, 24h HC."""
        hp_count = sum(1 for h in range(24) if is_hp_hour(h, "holiday"))
        assert hp_count == 0

    def test_24h_legacy(self):
        """Legacy C5: 16h HP (6-21), 8h HC (0-5 + 22-23)."""
        hp_count = sum(1 for h in range(24) if is_hp_hour(h, "weekday", mode="LEGACY"))
        assert hp_count == 16


# ═══════════════════════════════════════════════════════════════════════════════
# 7. RÉSOLUTION DATETIME → CODE DE PÉRIODE
# ═══════════════════════════════════════════════════════════════════════════════


class TestGetPeriodForDatetime:
    """get_period_for_datetime retourne HPH/HCH/HPB/HCB ou HP/HC."""

    def test_hiver_hp_saisonnalise(self):
        """10h un lundi de janvier = HPH (postes TURPE, hiver, HP)."""
        dt = datetime(2026, 1, 19, 10, 0)  # Lundi
        assert get_period_for_datetime(dt, is_seasonal=True) == "HPH"

    def test_hiver_hc_nuit(self):
        """03h un lundi de janvier = HCH (postes TURPE, nuit)."""
        dt = datetime(2026, 1, 19, 3, 0)
        assert get_period_for_datetime(dt, is_seasonal=True) == "HCH"

    def test_hiver_hc_matin_avant_8h(self):
        """07h un mardi de février = HCH (avant 8h = HC en postes TURPE)."""
        dt = datetime(2026, 2, 17, 7, 0)  # Mardi
        assert get_period_for_datetime(dt, is_seasonal=True) == "HCH"

    def test_ete_hp_saisonnalise(self):
        """10h un lundi de juillet = HPB (postes TURPE, été, HP)."""
        dt = datetime(2026, 7, 6, 10, 0)  # Lundi
        assert get_period_for_datetime(dt, is_seasonal=True) == "HPB"

    def test_ete_hc_nuit(self):
        """03h un mardi de juin = HCB (postes TURPE, nuit)."""
        dt = datetime(2026, 6, 9, 3, 0)
        assert get_period_for_datetime(dt, is_seasonal=True) == "HCB"

    def test_legacy_hp(self):
        """10h un lundi de janvier = HP (mode legacy C5)."""
        dt = datetime(2026, 1, 19, 10, 0)
        assert get_period_for_datetime(dt, is_seasonal=False) == "HP"

    def test_legacy_hc(self):
        """23h un lundi de janvier = HC (mode legacy C5)."""
        dt = datetime(2026, 1, 19, 23, 0)
        assert get_period_for_datetime(dt, is_seasonal=False) == "HC"

    def test_dimanche_hiver_saisonnalise(self):
        """10h un dimanche de janvier = HCH (dimanche toujours HC)."""
        dt = datetime(2026, 1, 18, 10, 0)  # Dimanche
        assert get_period_for_datetime(dt, is_seasonal=True) == "HCH"

    def test_dimanche_ete_saisonnalise(self):
        """14h un dimanche de juillet = HCB (dimanche toujours HC)."""
        dt = datetime(2026, 7, 5, 14, 0)  # Dimanche
        assert get_period_for_datetime(dt, is_seasonal=True) == "HCB"

    def test_samedi_hiver_hp(self):
        """10h un samedi de janvier = HPH (samedi = ouvré en TURPE)."""
        dt = datetime(2026, 1, 17, 10, 0)  # Samedi
        assert get_period_for_datetime(dt, is_seasonal=True) == "HPH"

    def test_ferie_hiver(self):
        """10h le 1er janvier = HCH (férié = HC toute la journée)."""
        dt = datetime(2026, 1, 1, 10, 0)  # Jour de l'An (jeudi)
        assert get_period_for_datetime(dt, is_seasonal=True) == "HCH"


# ═══════════════════════════════════════════════════════════════════════════════
# 8. COMPTAGE D'HEURES PAR PÉRIODE
# ═══════════════════════════════════════════════════════════════════════════════


class TestCountHoursByPeriod:
    """count_hours_by_period retourne les heures par plage sur une période."""

    def test_full_january_4p(self):
        """Janvier 2026 (31 jours, 100% hiver) → HPH + HCH uniquement."""
        counts = count_hours_by_period(date(2026, 1, 1), date(2026, 2, 1), is_seasonal=True)
        assert counts["HPB"] == 0
        assert counts["HCB"] == 0
        assert counts["HPH"] + counts["HCH"] == 31 * 24

    def test_full_july_4p(self):
        """Juillet 2026 (31 jours, 100% été) → HPB + HCB uniquement."""
        counts = count_hours_by_period(date(2026, 7, 1), date(2026, 8, 1), is_seasonal=True)
        assert counts["HPH"] == 0
        assert counts["HCH"] == 0
        assert counts["HPB"] + counts["HCB"] == 31 * 24

    def test_full_january_2p(self):
        """Janvier 2026 en mode legacy → HP + HC."""
        counts = count_hours_by_period(date(2026, 1, 1), date(2026, 2, 1), is_seasonal=False)
        assert "HPH" not in counts
        assert counts["HP"] + counts["HC"] == 31 * 24

    def test_total_hours_one_weekday(self):
        """Un jour ouvré = 24 heures totales, 14h HP + 10h HC."""
        # 5 janvier 2026 = lundi
        counts = count_hours_by_period(date(2026, 1, 5), date(2026, 1, 6), is_seasonal=True)
        assert sum(counts.values()) == 24
        assert counts["HPH"] == 14
        assert counts["HCH"] == 10

    def test_total_hours_one_sunday(self):
        """Un dimanche = 24h HC."""
        # 4 janvier 2026 = dimanche
        counts = count_hours_by_period(date(2026, 1, 4), date(2026, 1, 5), is_seasonal=True)
        assert counts["HPH"] == 0
        assert counts["HCH"] == 24

    def test_total_hours_one_saturday(self):
        """Un samedi = 14h HP + 10h HC (samedi = ouvré TURPE)."""
        # 3 janvier 2026 = samedi
        counts = count_hours_by_period(date(2026, 1, 3), date(2026, 1, 4), is_seasonal=True)
        assert counts["HPH"] == 14
        assert counts["HCH"] == 10

    def test_ratios_sum_to_one(self):
        """Les ratios doivent sommer à 1.0."""
        ratios = count_hours_by_period_ratios(date(2026, 1, 1), date(2026, 2, 1), is_seasonal=True)
        assert sum(ratios.values()) == pytest.approx(1.0, abs=0.001)

    def test_ratios_january_only_hiver(self):
        """Janvier: ratios HPB et HCB = 0."""
        ratios = count_hours_by_period_ratios(date(2026, 1, 1), date(2026, 2, 1), is_seasonal=True)
        assert ratios["HPB"] == pytest.approx(0.0)
        assert ratios["HCB"] == pytest.approx(0.0)

    def test_ratios_july_only_ete(self):
        """Juillet: ratios HPH et HCH = 0."""
        ratios = count_hours_by_period_ratios(date(2026, 7, 1), date(2026, 8, 1), is_seasonal=True)
        assert ratios["HPH"] == pytest.approx(0.0)
        assert ratios["HCH"] == pytest.approx(0.0)

    def test_full_week_jan_hph_ratio(self):
        """Semaine complète en janvier: HPH ratio ~= 6×14/(6×24+24) = 84/168 = 0.5."""
        # 5-11 jan 2026: lun-dim (6 jours ouvrés + 1 dimanche)
        ratios = count_hours_by_period_ratios(date(2026, 1, 5), date(2026, 1, 12), is_seasonal=True)
        # 6 jours ouvrés × 14h HP + 1 dim × 0h = 84h HPH
        # 6 jours ouvrés × 10h HC + 1 dim × 24h = 84h HCH
        # Total = 168h → HPH=0.5, HCH=0.5
        assert ratios["HPH"] == pytest.approx(84 / 168, abs=0.01)
        assert ratios["HCH"] == pytest.approx(84 / 168, abs=0.01)
