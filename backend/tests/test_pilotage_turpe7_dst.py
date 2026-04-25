"""
PROMEOS - Tests DST sur classify_slots + is_hc_favorable (TURPE 7).

Frontieres saisonnalisees TURPE 7 :
    - Saison basse (ete)  : avril-octobre -> plages 2h-6h + 11h-17h FAVORABLE.
    - Saison haute (hiver): novembre-mars -> plages 2h-6h + 21h-24h FAVORABLE.

DST Europe/Paris :
    - Spring-forward : dernier dimanche de mars (2026 : 29/03 a 02:00 -> 03:00).
    - Fall-back      : dernier dimanche d'octobre (2026 : 25/10 a 03:00 -> 02:00).

Les deux transitions tombent exactement sur la frontiere saisonniere TURPE 7
(passage hiver->ete en mars, ete->hiver en octobre). Ces tests verifient :

    1. Qu'un creneau post-transition (ex. 01/04/2026) est classifie avec
       la grille "ete" attendue.
    2. Qu'un creneau post-transition (ex. 01/11/2026) est classifie avec
       la grille "hiver" attendue.
    3. Que les deux occurrences du creneau 25/10/2026 02:30 (ambigu :
       existe 1 fois en CEST puis 1 fois en CET) se classifient toutes
       les deux correctement comme FAVORABLE (saison basse, plage 2h-6h).

Dette technique documentee dans docs/pilotage-usages/INNOVATION_ROADMAP.md.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from zoneinfo import ZoneInfo

from services.pilotage.window_detector import (
    SlotMarket,
    WindowType,
    classify_slots,
    is_hc_exclure,
    is_hc_favorable,
)


TZ_PARIS = ZoneInfo("Europe/Paris")


# ---------------------------------------------------------------------------
# Test 1 : transition mars -> avril = passage hiver -> ete (saison basse)
# ---------------------------------------------------------------------------
def test_classify_slots_saison_basse_vs_haute_transition_avril():
    """
    Le 01/04/2026 02:00 Europe/Paris (apres spring-forward du 29/03) tombe
    en saison BASSE (avril-octobre) : plage 2h-6h FAVORABLE ete.

    Comparaison avec 29/03/2026 01:00 (juste avant le spring-forward) :
    en saison HAUTE car mois = 3 (mars) -> plage 2h-6h favorable hiver,
    donc 01h n'est PAS favorable en hiver non plus (plage commence a 2h).
    """
    # Creneau 01/04/2026 02:00 (apres spring-forward, saison basse ete)
    dt_avril_2h = datetime(2026, 4, 1, 2, 0, tzinfo=TZ_PARIS)
    assert is_hc_favorable(dt_avril_2h) is True, "01/04 02h -> saison ete plage 2h-6h FAVORABLE"
    assert is_hc_exclure(dt_avril_2h) is False

    # Classif avec prix median (NEUTRE seul) : TURPE 7 tranche -> FAVORABLE
    slots = {dt_avril_2h: SlotMarket(prix_eur_mwh=80.0)}
    result = classify_slots(slots, threshold_low=50.0, threshold_high=120.0)
    assert result[dt_avril_2h].window_type == WindowType.FAVORABLE
    assert result[dt_avril_2h].raison == "turpe7_favorable"

    # Creneau 29/03/2026 01:00 (avant saut DST, saison haute = mars)
    # -> mois = 3 (hiver), plages favorable hiver = 2h-6h + 21h-24h
    # -> 01h n'est dans aucune -> NI favorable NI exclure, NEUTRE
    dt_mars_1h = datetime(2026, 3, 29, 1, 0, tzinfo=TZ_PARIS)
    assert is_hc_favorable(dt_mars_1h) is False
    assert is_hc_exclure(dt_mars_1h) is False
    slots_mars = {dt_mars_1h: SlotMarket(prix_eur_mwh=80.0)}
    result_mars = classify_slots(slots_mars, threshold_low=50.0, threshold_high=120.0)
    assert result_mars[dt_mars_1h].window_type == WindowType.NEUTRE


# ---------------------------------------------------------------------------
# Test 2 : transition octobre -> novembre = passage ete -> hiver (saison haute)
# ---------------------------------------------------------------------------
def test_classify_slots_transition_1er_novembre():
    """
    Le 01/11/2026 02:00 Europe/Paris (apres fall-back du 25/10) tombe en
    saison HAUTE (novembre-mars) : plage 2h-6h FAVORABLE hiver.

    Le 01/11/2026 14:00 -> saison haute, 14h n'est dans AUCUNE plage hiver
    (ni 2h-6h, ni 21h-24h, ni 7h-11h exclure, ni 17h-21h exclure) -> NEUTRE.
    """
    # Creneau 01/11/2026 02:00 (apres fall-back, saison haute hiver)
    dt_nov_2h = datetime(2026, 11, 1, 2, 0, tzinfo=TZ_PARIS)
    assert is_hc_favorable(dt_nov_2h) is True, "01/11 02h -> saison hiver 2h-6h FAVORABLE"
    assert is_hc_exclure(dt_nov_2h) is False

    # Classif : prix NEUTRE + TURPE 7 favorable -> bascule FAVORABLE
    slots = {dt_nov_2h: SlotMarket(prix_eur_mwh=80.0)}
    result = classify_slots(slots, threshold_low=50.0, threshold_high=120.0)
    assert result[dt_nov_2h].window_type == WindowType.FAVORABLE
    assert result[dt_nov_2h].raison == "turpe7_favorable"

    # Creneau 01/11/2026 14:00 : saison hiver, 14h hors plages FAV/EXC hiver
    dt_nov_14h = datetime(2026, 11, 1, 14, 0, tzinfo=TZ_PARIS)
    assert is_hc_favorable(dt_nov_14h) is False
    assert is_hc_exclure(dt_nov_14h) is False
    slots_14 = {dt_nov_14h: SlotMarket(prix_eur_mwh=80.0)}
    result_14 = classify_slots(slots_14, threshold_low=50.0, threshold_high=120.0)
    assert result_14[dt_nov_14h].window_type == WindowType.NEUTRE

    # Creneau 01/11/2026 19:00 : plage 17h-21h EXCLURE hiver
    dt_nov_19h = datetime(2026, 11, 1, 19, 0, tzinfo=TZ_PARIS)
    assert is_hc_exclure(dt_nov_19h) is True
    slots_19 = {dt_nov_19h: SlotMarket(prix_eur_mwh=80.0)}
    result_19 = classify_slots(slots_19, threshold_low=50.0, threshold_high=120.0)
    assert result_19[dt_nov_19h].window_type == WindowType.SENSIBLE
    assert result_19[dt_nov_19h].raison == "turpe7_exclure"


# ---------------------------------------------------------------------------
# Test 3 : fall-back 25/10/2026 -> creneau 02:30 ambigu (existe 2x)
# ---------------------------------------------------------------------------
def test_classify_slots_fall_back_creneau_double():
    """
    Le 25/10/2026 passe de 03:00 CEST a 02:00 CET. Le creneau local 02:30
    existe donc 2 fois :
      - 00:30 UTC = 02:30 CEST (+02:00)
      - 01:30 UTC = 02:30 CET  (+01:00)

    Les deux sont en octobre (mois = 10 -> saison basse ete), plage 2h-6h
    FAVORABLE. Les deux occurrences doivent se classifier FAVORABLE et
    etre distinguables en tant que cles (timestamps UTC differents).
    """
    # Construction par UTC pour garantir deux instants distincts
    dt_cest_utc = datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc)  # 02:30 CEST
    dt_cet_utc = datetime(2026, 10, 25, 1, 30, tzinfo=timezone.utc)  # 02:30 CET

    dt_cest_paris = dt_cest_utc.astimezone(TZ_PARIS)
    dt_cet_paris = dt_cet_utc.astimezone(TZ_PARIS)

    # Les deux timestamps UTC sont distincts (sanity)
    assert dt_cest_utc != dt_cet_utc

    # En heure locale, les deux affichent 02:30
    assert dt_cest_paris.hour == dt_cet_paris.hour == 2
    assert dt_cest_paris.minute == dt_cet_paris.minute == 30
    # Mais offsets differents
    assert dt_cest_paris.utcoffset() == timedelta(hours=2)
    assert dt_cet_paris.utcoffset() == timedelta(hours=1)

    # Les deux doivent classifier FAVORABLE (saison basse, plage 2h-6h)
    assert is_hc_favorable(dt_cest_utc) is True, "02:30 CEST = saison ete plage 2h-6h"
    assert is_hc_favorable(dt_cet_utc) is True, "02:30 CET = saison ete plage 2h-6h"
    # Ni l'un ni l'autre ne doit etre dans la plage EXCLURE
    assert is_hc_exclure(dt_cest_utc) is False
    assert is_hc_exclure(dt_cet_utc) is False

    # Classification conjointe : les deux cles coexistent dans le dict,
    # les deux basculent FAVORABLE via TURPE 7 (prix NEUTRE).
    slots = {
        dt_cest_utc: SlotMarket(prix_eur_mwh=80.0),
        dt_cet_utc: SlotMarket(prix_eur_mwh=80.0),
    }
    result = classify_slots(slots, threshold_low=50.0, threshold_high=120.0)
    assert len(result) == 2, "Les 2 instants UTC doivent rester distingues"
    assert result[dt_cest_utc].window_type == WindowType.FAVORABLE
    assert result[dt_cet_utc].window_type == WindowType.FAVORABLE
    assert result[dt_cest_utc].raison == "turpe7_favorable"
    assert result[dt_cet_utc].raison == "turpe7_favorable"
