"""
PROMEOS - Tests de l'indice TURPE 7 HC saisonnalise dans `classify_slots`.

Verifie :
  1. Helpers `is_hc_favorable` / `is_hc_exclure` sur les 4 quadrants
     saison / heure (ete 14h, hiver 22h, hiver 14h, hiver 19h, ete 9h,
     ete 3h).
  2. Regle d'integration : l'indice TURPE 7 est ADDITIONNEL au signal
     prix (pas d'inversion ni de substitution).

Source : Barometre Flex 2026 (RTE / Enedis / GIMELEC / Think Smartgrids),
avril 2026, section "Evolution Heures Creuses TURPE 7".
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from services.pilotage.window_detector import (
    SlotMarket,
    WindowType,
    classify_slots,
    is_hc_exclure,
    is_hc_favorable,
)


TZ_PARIS = ZoneInfo("Europe/Paris")


# --- 1. Helpers is_hc_favorable / is_hc_exclure -----------------------------


def test_is_hc_favorable_saisons_quadrants():
    """
    Quadrants officiels TURPE 7 HC -- creneaux A FAVORISER :
      - ete 14h  -> True (plage solaire 11h-17h saison basse)
      - hiver 22h -> True (plage creux nocturne 21h-24h saison haute)
      - hiver 14h -> False (pas dans 2h-6h ni 21h-24h saison haute)
    """
    # Ete (juillet) a 14h -> plage 11h-17h = FAVORABLE
    dt_ete_14h = datetime(2026, 7, 15, 14, 0, tzinfo=TZ_PARIS)
    assert is_hc_favorable(dt_ete_14h) is True, "ete 14h doit etre dans la plage solaire TURPE 7 (11h-17h)"

    # Hiver (janvier) a 22h -> plage 21h-24h = FAVORABLE
    dt_hiver_22h = datetime(2027, 1, 20, 22, 0, tzinfo=TZ_PARIS)
    assert is_hc_favorable(dt_hiver_22h) is True, "hiver 22h doit etre dans la plage creux nocturne TURPE 7 (21h-24h)"

    # Hiver a 14h -> hors creneau FAVORABLE (saison haute = 2h-6h + 21h-24h)
    dt_hiver_14h = datetime(2027, 1, 20, 14, 0, tzinfo=TZ_PARIS)
    assert is_hc_favorable(dt_hiver_14h) is False, "hiver 14h n'est PAS dans un creneau TURPE 7 a favoriser"


def test_is_hc_exclure_saisons_quadrants():
    """
    Quadrants officiels TURPE 7 HC -- creneaux A EXCLURE :
      - hiver 19h -> True (pic soir 17h-21h saison haute)
      - ete 9h    -> True (montee matin 7h-11h saison basse)
      - ete 3h    -> False (plage nocturne 2h-6h = a FAVORISER en ete)
    """
    # Hiver (novembre) a 19h -> plage 17h-21h = EXCLURE
    dt_hiver_19h = datetime(2026, 11, 10, 19, 0, tzinfo=TZ_PARIS)
    assert is_hc_exclure(dt_hiver_19h) is True, "hiver 19h doit etre dans la plage pic soir TURPE 7 a exclure (17h-21h)"

    # Ete (aout) a 9h -> plage 7h-11h = EXCLURE
    dt_ete_9h = datetime(2026, 8, 5, 9, 0, tzinfo=TZ_PARIS)
    assert is_hc_exclure(dt_ete_9h) is True, "ete 9h doit etre dans la plage montee matin TURPE 7 a exclure (7h-11h)"

    # Ete a 3h -> plage 2h-6h = FAVORABLE (donc NON exclure)
    dt_ete_3h = datetime(2026, 7, 15, 3, 0, tzinfo=TZ_PARIS)
    assert is_hc_exclure(dt_ete_3h) is False, "ete 3h est dans un creneau TURPE 7 a favoriser, pas a exclure"


# --- 2. Non-inversion : le signal prix domine TURPE 7 ----------------------


def test_slot_prix_bas_14h_ete_reste_favorable():
    """
    Un slot a prix bas a 14h ete reste FAVORABLE (pas d'inversion).

    Le creneau TURPE 7 "a favoriser" s'aligne avec le signal prix : la
    classification reste FAVORABLE, pilotee par le prix (raison="prix").
    L'indice TURPE 7 favorable est trace dans la classification pour
    explicabilite cockpit, mais il n'altere pas la decision.
    """
    ts = datetime(2026, 7, 15, 14, 0, tzinfo=TZ_PARIS)
    slots = {ts: SlotMarket(prix_eur_mwh=10.0)}
    threshold_low, threshold_high = 50.0, 120.0

    result = classify_slots(slots, threshold_low, threshold_high)
    assert result[ts].window_type == WindowType.FAVORABLE
    assert result[ts].raison == "prix", "le signal prix doit rester la raison dominante (pas d'inversion TURPE 7)"
    assert result[ts].turpe7_favorable is True

    # Controle contre-intuitif : meme sur un creneau TURPE 7 a EXCLURE,
    # un prix bas doit rester FAVORABLE (stricte non-inversion).
    ts_exc = datetime(2026, 8, 5, 9, 0, tzinfo=TZ_PARIS)  # ete 9h = exclure
    slots_exc = {ts_exc: SlotMarket(prix_eur_mwh=10.0)}
    result_exc = classify_slots(slots_exc, threshold_low, threshold_high)
    assert result_exc[ts_exc].window_type == WindowType.FAVORABLE, (
        "prix bas sur creneau a exclure -> reste FAVORABLE (pas d'inversion)"
    )
    assert result_exc[ts_exc].turpe7_exclure is True


def test_slot_prix_eleve_19h_hiver_reste_sensible():
    """
    Un slot a prix eleve a 19h hiver reste SENSIBLE (alignement).

    Le creneau TURPE 7 "a exclure" s'aligne avec le signal prix : la
    classification reste SENSIBLE, pilotee par le prix. L'indice
    turpe7_exclure est trace dans la classification.

    Controle de non-inversion : meme sur un creneau TURPE 7 a FAVORISER
    (ex. hiver 22h), un prix eleve doit rester SENSIBLE.
    """
    ts = datetime(2026, 11, 10, 19, 0, tzinfo=TZ_PARIS)
    slots = {ts: SlotMarket(prix_eur_mwh=200.0)}
    threshold_low, threshold_high = 50.0, 120.0

    result = classify_slots(slots, threshold_low, threshold_high)
    assert result[ts].window_type == WindowType.SENSIBLE
    assert result[ts].raison == "prix"
    assert result[ts].turpe7_exclure is True, "alignement TURPE 7 trace"

    # Controle contre-intuitif : meme sur un creneau TURPE 7 a FAVORISER,
    # un prix eleve doit rester SENSIBLE (stricte non-inversion).
    ts_fav = datetime(2027, 1, 20, 22, 0, tzinfo=TZ_PARIS)  # hiver 22h = favorable
    slots_fav = {ts_fav: SlotMarket(prix_eur_mwh=200.0)}
    result_fav = classify_slots(slots_fav, threshold_low, threshold_high)
    assert result_fav[ts_fav].window_type == WindowType.SENSIBLE, (
        "prix eleve sur creneau a favoriser -> reste SENSIBLE (pas d'inversion)"
    )
    assert result_fav[ts_fav].turpe7_favorable is True


# --- 3. Indice additionnel : TURPE 7 tranche les slots NEUTRE --------------


def test_slot_neutre_bascule_favorable_via_turpe7():
    """
    Regle d'integration : un slot au prix median (entre threshold_low et
    threshold_high, NEUTRE par prix seul) bascule en FAVORABLE s'il
    tombe sur un creneau TURPE 7 "a favoriser".
    """
    # Hiver 3h = creneau 2h-6h FAVORABLE saison haute
    ts = datetime(2027, 1, 20, 3, 30, tzinfo=TZ_PARIS)
    slots = {ts: SlotMarket(prix_eur_mwh=80.0)}
    threshold_low, threshold_high = 50.0, 120.0

    result = classify_slots(slots, threshold_low, threshold_high)
    assert result[ts].window_type == WindowType.FAVORABLE
    assert result[ts].raison == "turpe7_favorable"
    assert result[ts].turpe7_favorable is True


def test_slot_neutre_bascule_sensible_via_turpe7():
    """
    Regle d'integration : un slot au prix median bascule en SENSIBLE
    s'il tombe sur un creneau TURPE 7 "a exclure", et reste NEUTRE si
    aucun creneau TURPE 7 ne s'applique.
    """
    # Ete 9h = creneau 7h-11h EXCLURE saison basse
    ts_exc = datetime(2026, 8, 5, 9, 30, tzinfo=TZ_PARIS)
    # Ete 23h30 = hors creneau TURPE 7 (ni 2h-6h, ni 11h-17h, ni 7h-11h,
    # ni 18h-23h)
    ts_neutre = datetime(2026, 8, 5, 23, 30, tzinfo=TZ_PARIS)

    slots = {
        ts_exc: SlotMarket(prix_eur_mwh=80.0),
        ts_neutre: SlotMarket(prix_eur_mwh=80.0),
    }
    threshold_low, threshold_high = 50.0, 120.0

    result = classify_slots(slots, threshold_low, threshold_high)
    assert result[ts_exc].window_type == WindowType.SENSIBLE
    assert result[ts_exc].raison == "turpe7_exclure"
    assert result[ts_neutre].window_type == WindowType.NEUTRE
    assert result[ts_neutre].raison == "neutre"
