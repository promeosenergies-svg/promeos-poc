"""
PROMEOS — CDC (Courbe de Charge) Service
Query + classification TURPE slot pour chaque point de mesure.

Sources : PowerReading (kW natif), MeterReading (kWh fallback).
Horodate : UTC → Europe/Paris pour classification tarifaire.
"""

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session

TZ_PARIS = ZoneInfo("Europe/Paris")

# ── Jours fériés France (métropole) — frozenset pour O(1) lookup ────────
# Fériés fixes + calcul dynamique Pâques omis (approx: pas de Pointe les JF)
JOURS_FERIES_FIXES = frozenset(
    [
        (1, 1),  # Jour de l'An
        (5, 1),  # Fête du Travail
        (5, 8),  # Victoire 1945
        (7, 14),  # Fête nationale
        (8, 15),  # Assomption
        (11, 1),  # Toussaint
        (11, 11),  # Armistice
        (12, 25),  # Noël
    ]
)


def _is_jour_ferie(d: date) -> bool:
    """Vérifie si une date est un jour férié fixe français."""
    return (d.month, d.day) in JOURS_FERIES_FIXES


def classify_turpe_slot(dt_utc: datetime, fta_code: str) -> str:
    """
    Classifie un horodate UTC dans un poste tarifaire TURPE.

    Grille TURPE 7 (CRE 2025-78) pour FTA 5 postes (HTA, BT>36kVA LU) :
      - Pointe : Dec-Fév, jours ouvrés hors JF, 9h-11h + 18h-20h (heure locale)
      - HPH    : Nov-Mar, jours ouvrés hors JF, 6h-22h (excl. Pointe)
      - HCH    : Nov-Mar, autres créneaux
      - HPE    : Avr-Oct, jours ouvrés, 8h-20h
      - HCE    : Avr-Oct, autres créneaux
      - Base   : fallback pour FTA sans différenciation
    """
    # FTA sans différenciation → Base
    if fta_code and "SansDiff" in fta_code:
        return "Base"
    # FTA BT<36kVA HP/HC simple
    if fta_code and fta_code.startswith("BTINF"):
        # Simplified HP/HC : HC = 22h-6h locale
        dt_local = dt_utc.astimezone(TZ_PARIS)
        h = dt_local.hour
        return "HC" if (h >= 22 or h < 6) else "HP"

    dt_local = dt_utc.astimezone(TZ_PARIS)
    d = dt_local.date()
    h = dt_local.hour
    m = d.month
    wd = d.weekday()  # 0=lundi .. 6=dimanche
    is_ouvre = wd < 5 and not _is_jour_ferie(d)

    # Saison hiver : novembre à mars
    is_hiver = m in (11, 12, 1, 2, 3)

    if is_hiver:
        # Pointe : décembre-février, jours ouvrés, 9-11h et 18-20h
        if m in (12, 1, 2) and is_ouvre:
            if (9 <= h < 11) or (18 <= h < 20):
                return "Pointe"
        # HPH : jours ouvrés, 6-22h (hors Pointe)
        if is_ouvre and 6 <= h < 22:
            return "HPH"
        # HCH : tout le reste en hiver
        return "HCH"
    else:
        # Saison été : avril à octobre
        if is_ouvre and 8 <= h < 20:
            return "HPE"
        return "HCE"


def query_cdc(
    db: Session,
    meter_id: int,
    date_from: date,
    date_to: date,
    granularity: str = "30min",
) -> dict:
    """
    Interroge la CDC d'un compteur sur une période.

    Retourne :
      - points: [{t, kw, slot, quality}]
      - ps: {poste: kva} (puissance souscrite)
      - meta: {granularity, count, meter_id}
    """
    from models import Meter, MeterReading
    from models.power import PowerReading, PowerContract

    meter = db.query(Meter).filter(Meter.id == meter_id).first()
    if not meter:
        return {"error": "Compteur introuvable", "points": [], "ps": {}, "meta": {}}

    dt_from = datetime(date_from.year, date_from.month, date_from.day)
    dt_to = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59)

    # Charger contrat actif pour FTA + PS
    contract = (
        db.query(PowerContract)
        .filter(
            PowerContract.meter_id == meter_id,
            PowerContract.date_debut <= date_to,
        )
        .filter(
            (PowerContract.date_fin == None) | (PowerContract.date_fin >= date_from)  # noqa: E711
        )
        .order_by(PowerContract.date_debut.desc())
        .first()
    )
    fta_code = contract.fta_code if contract else "HTALU5"
    ps_map = (contract.ps_par_poste_kva or {}) if contract else {}

    # 1) Essayer PowerReading (CDC native kW)
    readings = (
        db.query(PowerReading)
        .filter(
            PowerReading.meter_id == meter_id,
            PowerReading.ts_debut >= dt_from,
            PowerReading.ts_debut <= dt_to,
        )
        .order_by(PowerReading.ts_debut)
        .all()
    )

    points = []
    if readings:
        for r in readings:
            slot = classify_turpe_slot(r.ts_debut, fta_code)
            points.append(
                {
                    "t": r.ts_debut.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "kw": r.P_active_kw,
                    "slot": slot,
                    "quality": r.nature_point or "M",
                }
            )
    else:
        # 2) Fallback MeterReading (kWh → kW approx)
        fallback = (
            db.query(MeterReading)
            .filter(
                MeterReading.meter_id == meter_id,
                MeterReading.timestamp >= dt_from,
                MeterReading.timestamp <= dt_to,
            )
            .order_by(MeterReading.timestamp)
            .all()
        )
        for r in fallback:
            slot = classify_turpe_slot(r.timestamp, fta_code)
            points.append(
                {
                    "t": r.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "kw": r.value_kwh,  # kWh sur 1h ≈ kW moyen
                    "slot": slot,
                    "quality": "E" if r.is_estimated else "M",
                }
            )

    # Agrégation si granularity != 30min (simplifiée)
    # Pour l'instant on retourne les points bruts

    return {
        "points": points,
        "ps": ps_map,
        "meta": {
            "granularity": granularity,
            "count": len(points),
            "meter_id": meter_id,
            "fta_code": fta_code,
            "source": "power_readings" if readings else "meter_readings",
        },
    }
