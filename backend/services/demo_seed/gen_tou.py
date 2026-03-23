"""
PROMEOS — Demo Seed: TOU Schedule Generator (V110)
Creates Time-of-Use (HP/HC) schedules for each site in the pack.

V110: Ajout des grilles saisonnalisées TURPE 7 Phase 2.
  - Sites HP/HC standard : grille legacy 06-22/22-06
  - Site Nice (HP_HC, 36 kVA) : grille saisonnalisée (HPH/HCH/HPB/HCB)

Sources :
  - CRE TURPE 7 délibération n°2025-78 du 13 mars 2025
  - CRE délibération n°2026-33 du 4 février 2026 (levée gel HC 11-14h hiver)
"""

import json
from datetime import date


# ─── Grille legacy HP/HC (non saisonnalisée) ─────────────────────────────────
# Source: EDF tarif bleu, TURPE legacy (MUDT dérogatoire)

_HP_HC_WINDOWS = [
    # Weekdays: HP 06h–22h
    {
        "day_types": ["weekday"],
        "start": "06:00",
        "end": "22:00",
        "period": "HP",
        "price_eur_kwh": 0.1841,
    },
    # Weekdays: HC 22h–06h
    {
        "day_types": ["weekday"],
        "start": "22:00",
        "end": "06:00",
        "period": "HC",
        "price_eur_kwh": 0.1210,
    },
    # Weekend + holidays: HC all day
    {
        "day_types": ["weekend", "holiday"],
        "start": "00:00",
        "end": "24:00",
        "period": "HC",
        "price_eur_kwh": 0.1210,
    },
]

# ─── Grille HC consommateur saisonnalisée Phase 2 ────────────────────────────
# Ces windows représentent les HC CONSOMMATEUR (8h/jour sur Linky) pour un
# site C5 HP/HC Phase 2 saisonnalisé.
# Source: CRE délibération n°2025-78 + n°2026-33 du 4 fév 2026
#
# NB: Ceci est DISTINCT des postes horosaisonniers TURPE (pour C4/HTA)
#     qui utilisent HP lun-sam 7h30-21h30, HC 21h30-7h30 + dim + fériés.
#     Les postes TURPE sont dans turpe_calendar.py.

# Saison haute (hiver, nov-mars) — 8h HC/jour
# HC nuit: 23h-07h (8h), HP le reste
# (variante possible avec 11h-14h HC grâce à n°2026-33, non retenue ici)
_WINDOWS_HIVER = [
    {
        "day_types": ["weekday", "weekend", "holiday"],
        "start": "23:00",
        "end": "07:00",
        "period": "HCH",
        "price_eur_kwh": 0.1350,
    },
    {
        "day_types": ["weekday", "weekend", "holiday"],
        "start": "07:00",
        "end": "23:00",
        "period": "HPH",
        "price_eur_kwh": 0.1950,
    },
]

# Saison basse (été, avr-oct) — 8h HC/jour
# HC nuit: 01h-06h (5h) + HC après-midi: 12h-15h (3h) = 8h
# HP le reste
_WINDOWS_ETE = [
    {
        "day_types": ["weekday", "weekend", "holiday"],
        "start": "01:00",
        "end": "06:00",
        "period": "HCB",
        "price_eur_kwh": 0.1150,
    },
    {
        "day_types": ["weekday", "weekend", "holiday"],
        "start": "12:00",
        "end": "15:00",
        "period": "HCB",
        "price_eur_kwh": 0.1150,
    },
    {
        "day_types": ["weekday", "weekend", "holiday"],
        "start": "00:00",
        "end": "01:00",
        "period": "HPB",
        "price_eur_kwh": 0.1750,
    },
    {
        "day_types": ["weekday", "weekend", "holiday"],
        "start": "06:00",
        "end": "12:00",
        "period": "HPB",
        "price_eur_kwh": 0.1750,
    },
    {
        "day_types": ["weekday", "weekend", "holiday"],
        "start": "15:00",
        "end": "24:00",
        "period": "HPB",
        "price_eur_kwh": 0.1750,
    },
]


def generate_tou(db, sites: list, rng=None) -> dict:
    """Create one active TOUSchedule per site.

    V110: sites avec tariff_option HP_HC et puissance ≤36 kVA reçoivent
    une grille saisonnalisée TURPE 7 Phase 2. Les autres gardent la
    grille legacy HP/HC.

    Returns dict with count created.
    """
    from models.tou_schedule import TOUSchedule

    created = 0
    windows_legacy_json = json.dumps(_HP_HC_WINDOWS, ensure_ascii=False)
    windows_hiver_json = json.dumps(_WINDOWS_HIVER, ensure_ascii=False)
    windows_ete_json = json.dumps(_WINDOWS_ETE, ensure_ascii=False)

    for site in sites:
        # Skip if already has an active schedule
        existing = (
            db.query(TOUSchedule)
            .filter(
                TOUSchedule.site_id == site.id,
                TOUSchedule.is_active == True,
            )
            .first()
        )
        if existing:
            continue

        # Déterminer si le site doit avoir une grille saisonnalisée
        # Heuristique: site avec nom contenant "Nice" (site démo HP/HC 36kVA)
        site_nom = (site.nom or "").lower()
        is_seasonal_site = "nice" in site_nom

        if is_seasonal_site:
            tou = TOUSchedule(
                site_id=site.id,
                name="HC/HP Saisonnalisé TURPE 7 Phase 2",
                effective_from=date(2026, 11, 1),
                effective_to=None,
                is_active=True,
                is_seasonal=True,
                windows_json=windows_hiver_json,
                windows_ete_json=windows_ete_json,
                source="turpe",
                source_ref="CRE n°2025-78 + n°2026-33 — Phase 2 saisonnalisé (déc 2026 → oct 2027)",
                price_hp_eur_kwh=0.1841,
                price_hc_eur_kwh=0.1210,
                price_hph_eur_kwh=0.1950,
                price_hch_eur_kwh=0.1350,
                price_hpb_eur_kwh=0.1750,
                price_hcb_eur_kwh=0.1150,
            )
        else:
            tou = TOUSchedule(
                site_id=site.id,
                name="HC/HP Standard EDF",
                effective_from=date(2023, 1, 1),
                effective_to=None,
                is_active=True,
                windows_json=windows_legacy_json,
                source="turpe",
                source_ref="EDF HC/HP Option Tarif Bleu 2023",
                price_hp_eur_kwh=0.1841,
                price_hc_eur_kwh=0.1210,
            )
        db.add(tou)
        created += 1

    db.flush()
    return {"tou_created": created}
