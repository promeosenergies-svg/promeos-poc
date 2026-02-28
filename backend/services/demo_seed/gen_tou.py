"""
PROMEOS — Demo Seed: TOU Schedule Generator (V83)
Creates Time-of-Use (HP/HC) schedules for each site in the pack.
EDF HC/HP standard tariff windows (semaine + week-end).
"""
import json
from datetime import date


# Standard EDF HC/HP windows (ISO format, source: TURPE)
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


def generate_tou(db, sites: list, rng=None) -> dict:
    """Create one active TOUSchedule per site.

    Returns dict with count created.
    """
    from models.tou_schedule import TOUSchedule

    created = 0
    windows_json = json.dumps(_HP_HC_WINDOWS, ensure_ascii=False)

    for site in sites:
        # Skip if already has an active schedule
        existing = db.query(TOUSchedule).filter(
            TOUSchedule.site_id == site.id,
            TOUSchedule.is_active == True,
        ).first()
        if existing:
            continue

        tou = TOUSchedule(
            site_id=site.id,
            name="HC/HP Standard EDF",
            effective_from=date(2023, 1, 1),
            effective_to=None,      # currently active
            is_active=True,
            windows_json=windows_json,
            source="turpe",
            source_ref="EDF HC/HP Option Tarif Bleu 2023",
            price_hp_eur_kwh=0.1841,
            price_hc_eur_kwh=0.1210,
        )
        db.add(tou)
        created += 1

    db.flush()
    return {"tou_created": created}
