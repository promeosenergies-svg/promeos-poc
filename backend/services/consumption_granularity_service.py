"""
PROMEOS — services/consumption_granularity_service.py (ADR-022 F.16).

Extension `consumption_unified_service` avec les granularités daily / hourly
/ peak / baseline nécessaires au wiring du Cockpit Jour (F.17).

Fonctions :
  - get_org_daily_kwh(db, org_id, day) → kWh total du groupe pour 1 jour
  - get_org_daily_range_kwh(db, org_id, start, end) → liste {date, kwh, source}
  - get_org_hourly_curve_kw(db, org_id, day) → liste {hour: 0-23, kw}
  - get_org_peak_kw(db, org_id, day) → max kW de la courbe horaire
  - get_org_baseline_daily_kwh(db, org_id, today=None) → moyenne 7 jours (DJU-naive v1)

Doctrine ADR-022 §KPI 2 / Chart bars / Chart line / KPI 3.
Source unique consommation : `consumption_unified_service`. Ce module est
un extension cohérente, pas une duplication.

Pour les états sans données (cas démo HELIOS 5 sites sans MeterReading
seedé) : retourne None / 0 / [] pour permettre au caller d'afficher
"données partielles" plutôt qu'un faux chiffre. Aucun fallback hardcoded.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import MeterReading, Site
from models.energy_models import EnergyVector, FrequencyType
from services.scope_utils import sites_for_org_query

logger = logging.getLogger(__name__)


# ── Helpers internes ────────────────────────────────────────────────────────


def _meter_ids_for_org(
    db: Session,
    org_id: Optional[int],
    energy_vector: EnergyVector = EnergyVector.ELECTRICITY,
) -> list[int]:
    """Retourne les meter_ids actifs du scope org (filtre is_demo via scope_utils).

    Délègue à `services.ems.timeseries_service.get_site_meter_ids` pour
    chaque site afin d'exclure les sous-compteurs (matrice patrimoine §4.4.F).
    """
    from services.ems.timeseries_service import get_site_meter_ids

    sites = sites_for_org_query(db, org_id).with_entities(Site.id).all()
    meter_ids: list[int] = []
    for (site_id,) in sites:
        meter_ids.extend(get_site_meter_ids(db, site_id, energy_vector))
    return meter_ids


def _aggregate_kwh_period(
    db: Session,
    meter_ids: list[int],
    start_dt: datetime,
    end_dt: datetime,
    frequency: FrequencyType = FrequencyType.HOURLY,
) -> tuple[float, int]:
    """Agrège la somme value_kwh + nombre de lectures pour les meters/période/freq.

    Returns:
        (total_kwh, readings_count)
    """
    if not meter_ids:
        return (0.0, 0)
    result = (
        db.query(
            func.coalesce(func.sum(MeterReading.value_kwh), 0.0),
            func.count(MeterReading.id),
        )
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= start_dt,
            MeterReading.timestamp < end_dt,
            MeterReading.frequency == frequency,
        )
        .first()
    )
    return (float(result[0]), int(result[1]))


# ── API publique ─────────────────────────────────────────────────────────────


def get_org_daily_kwh(
    db: Session,
    org_id: Optional[int],
    day: date,
    energy_vector: EnergyVector = EnergyVector.ELECTRICITY,
) -> Optional[float]:
    """Consommation totale du groupe pour un jour donné, en kWh.

    Args:
        day : date du jour (J-1 typiquement pour KPI 2 cockpit jour).

    Returns:
        kWh total (float) si lectures disponibles, None sinon.
    """
    meter_ids = _meter_ids_for_org(db, org_id, energy_vector)
    if not meter_ids:
        return None

    start_dt = datetime(day.year, day.month, day.day)
    end_dt = start_dt + timedelta(days=1)

    # Tente HOURLY d'abord (CDC), fallback DAILY
    for freq in (FrequencyType.HOURLY, FrequencyType.MIN_30, FrequencyType.DAILY):
        total, count = _aggregate_kwh_period(db, meter_ids, start_dt, end_dt, freq)
        if count > 0:
            return round(total, 2)
    return None


def get_org_daily_range_kwh(
    db: Session,
    org_id: Optional[int],
    start: date,
    end: date,
    energy_vector: EnergyVector = EnergyVector.ELECTRICITY,
) -> list[dict]:
    """Consommation jour-par-jour sur une plage [start, end] inclus.

    Returns:
        Liste de {date: 'YYYY-MM-DD', kwh: float|None, source: 'metered'|'none'}
        — un élément par jour, ordre chronologique. None pour les jours sans
        données (à afficher comme "—" côté frontend).
    """
    days = []
    cursor = start
    while cursor <= end:
        kwh = get_org_daily_kwh(db, org_id, cursor, energy_vector)
        days.append(
            {
                "date": cursor.isoformat(),
                "kwh": kwh,
                "source": "metered" if kwh is not None else "none",
            }
        )
        cursor += timedelta(days=1)
    return days


def get_org_hourly_curve_kw(
    db: Session,
    org_id: Optional[int],
    day: date,
    energy_vector: EnergyVector = EnergyVector.ELECTRICITY,
) -> list[dict]:
    """Courbe de charge horaire (24 points 0h-23h) en kW pour un jour donné.

    Conversion kWh → kW : pour des lectures HOURLY, value_kwh = puissance moyenne
    horaire en kW (1 kWh sur 1 heure = 1 kW moyen). Pour HALF_HOURLY, on
    additionne les 2 demi-heures et la valeur reste en kW (½h × 2 = 1h).

    Returns:
        Liste de {hour: 0-23, kw: float|None} — 24 éléments. None si pas
        de lecture pour cette heure.
    """
    meter_ids = _meter_ids_for_org(db, org_id, energy_vector)
    if not meter_ids:
        return [{"hour": h, "kw": None} for h in range(24)]

    start_dt = datetime(day.year, day.month, day.day)
    end_dt = start_dt + timedelta(days=1)

    # Aggrégation par heure SQL (group by hour). Tente HOURLY puis HALF_HOURLY.
    for freq in (FrequencyType.HOURLY, FrequencyType.MIN_30):
        rows = (
            db.query(
                func.strftime("%H", MeterReading.timestamp).label("hour"),
                func.coalesce(func.sum(MeterReading.value_kwh), 0.0).label("kwh_sum"),
                func.count(MeterReading.id).label("cnt"),
            )
            .filter(
                MeterReading.meter_id.in_(meter_ids),
                MeterReading.timestamp >= start_dt,
                MeterReading.timestamp < end_dt,
                MeterReading.frequency == freq,
            )
            .group_by("hour")
            .all()
        )
        if rows:
            # kWh sur 1h = kW moyen sur 1h ; pour HALF_HOURLY, somme 2 demi-heures = kWh sur 1h.
            curve = {int(h): round(float(s), 2) for h, s, _c in rows}
            return [{"hour": h, "kw": curve.get(h)} for h in range(24)]

    return [{"hour": h, "kw": None} for h in range(24)]


def get_org_peak_kw(
    db: Session,
    org_id: Optional[int],
    day: date,
    energy_vector: EnergyVector = EnergyVector.ELECTRICITY,
) -> Optional[dict]:
    """Pic de puissance max du groupe pour un jour donné.

    Returns:
        {hour: 0-23, kw: float} si données disponibles, None sinon.
    """
    curve = get_org_hourly_curve_kw(db, org_id, day, energy_vector)
    valid_points = [p for p in curve if p["kw"] is not None and p["kw"] > 0]
    if not valid_points:
        return None
    peak = max(valid_points, key=lambda p: p["kw"])
    return {"hour": peak["hour"], "kw": round(peak["kw"], 2)}


def get_org_baseline_daily_kwh(
    db: Session,
    org_id: Optional[int],
    today: Optional[date] = None,
    lookback_days: int = 28,
    energy_vector: EnergyVector = EnergyVector.ELECTRICITY,
) -> Optional[float]:
    """Baseline journalière du groupe (moyenne sur lookback_days jours).

    V1 implementation : moyenne arithmétique simple.

    Args:
        today          : date de référence (défaut UTC today).
        lookback_days  : profondeur historique (défaut 28 = 4 semaines).

    Returns:
        kWh/jour moyen si au moins 7 jours de données, None sinon.
    """
    today = today or datetime.utcnow().date()
    start = today - timedelta(days=lookback_days)
    end = today - timedelta(days=1)  # exclut J0 (en cours)

    daily = get_org_daily_range_kwh(db, org_id, start, end, energy_vector)
    valid = [d["kwh"] for d in daily if d["kwh"] is not None and d["kwh"] > 0]
    if len(valid) < 7:
        return None  # Pas assez d'historique pour une baseline fiable
    return round(sum(valid) / len(valid), 2)


# ── F.26 — Baseline DJU-adjusted V2 (normalisation saisonnière) ────────────


# Profil DJU mensuel typique France métropolitaine (Paris Île-de-France) —
# moyennes COSTIC sur 30 ans, base 18°C. Source : skill
# `promeos-energy-fundamentals` + ADEME Base Empreinte.
# Plus le DJU est haut, plus le mois est froid (besoin de chauffage).
_DJU_MONTHLY_FRANCE: dict[int, int] = {
    1: 380,  # janvier  — pic chauffage
    2: 330,  # février
    3: 270,  # mars
    4: 180,  # avril
    5: 100,  # mai
    6: 40,  # juin
    7: 10,  # juillet  — quasi nul
    8: 15,  # août
    9: 60,  # septembre
    10: 150,  # octobre
    11: 260,  # novembre
    12: 360,  # décembre
}

# Fraction de la conso qui dépend du chauffage (variable selon NAF).
# Bureaux/tertiaire mixte (HELIOS) ≈ 45 % chauffage électrique.
# Pour V2 simplifié, on prend 0.4 comme paramètre canonique.
_HEATING_LOAD_RATIO = 0.40


def get_org_baseline_daily_kwh_dju_adjusted(
    db: Session,
    org_id: Optional[int],
    target_day: date,
    today: Optional[date] = None,
    lookback_days: int = 28,
    energy_vector: EnergyVector = EnergyVector.ELECTRICITY,
) -> Optional[dict]:
    """Baseline ajustée DJU (V2 doctrine ADR-022 §KPI 2 / Chart bars).

    Applique une normalisation saisonnière : la baseline brute (moyenne
    sur lookback_days) est ajustée par le ratio DJU(target_day_month) /
    DJU_moyen(lookback_period). Cela corrige l'écart "hiver vs été" qui
    fausse la comparaison J-1 vs baseline 28 jours quand on est en
    transition saisonnière.

    Formule simplifiée (sans météo réelle, V2.0) :
        baseline_adj = baseline_brute × (1 + heating_load_ratio × (DJU_ratio − 1))
        DJU_ratio = DJU_target_month / DJU_baseline_avg_month

    V3 (futur) intégrera la météo réelle Météo France + signature thermique
    par site (β coefficient régression).

    Returns:
        dict {
            baseline_raw_kwh    : moyenne brute lookback_days
            baseline_adjusted_kwh : baseline ajustée DJU
            dju_target           : DJU du mois cible
            dju_baseline_avg     : DJU moyen période baseline
            heating_load_ratio   : fraction chauffage utilisée
            method               : 'dju_v2_simplified' | 'flat' (si pas de DJU data)
        }
        ou None si pas assez de données pour baseline.
    """
    today = today or datetime.utcnow().date()
    baseline_raw = get_org_baseline_daily_kwh(
        db, org_id, today=today, lookback_days=lookback_days, energy_vector=energy_vector
    )
    if baseline_raw is None:
        return None

    # DJU du mois cible (target_day).
    dju_target = _DJU_MONTHLY_FRANCE.get(target_day.month)
    if dju_target is None:
        return {
            "baseline_raw_kwh": baseline_raw,
            "baseline_adjusted_kwh": baseline_raw,
            "dju_target": None,
            "dju_baseline_avg": None,
            "heating_load_ratio": _HEATING_LOAD_RATIO,
            "method": "flat",
        }

    # DJU moyen sur les mois couverts par la baseline (pondéré par jours).
    baseline_start = today - timedelta(days=lookback_days)
    baseline_end = today - timedelta(days=1)
    months_covered: dict[int, int] = {}
    cursor = baseline_start
    while cursor <= baseline_end:
        months_covered[cursor.month] = months_covered.get(cursor.month, 0) + 1
        cursor += timedelta(days=1)
    total_days = sum(months_covered.values())
    dju_baseline_avg = (
        (sum(_DJU_MONTHLY_FRANCE.get(m, 0) * d for m, d in months_covered.items()) / total_days)
        if total_days > 0
        else dju_target
    )

    if dju_baseline_avg <= 0:
        dju_ratio = 1.0
    else:
        dju_ratio = dju_target / dju_baseline_avg

    # Ajustement multiplicatif borné [0.6, 1.4] pour éviter les explosions.
    adjustment = 1 + _HEATING_LOAD_RATIO * (dju_ratio - 1)
    adjustment = max(0.6, min(1.4, adjustment))

    baseline_adjusted = round(baseline_raw * adjustment, 2)

    return {
        "baseline_raw_kwh": baseline_raw,
        "baseline_adjusted_kwh": baseline_adjusted,
        "dju_target": dju_target,
        "dju_baseline_avg": round(dju_baseline_avg, 1),
        "heating_load_ratio": _HEATING_LOAD_RATIO,
        "method": "dju_v2_simplified",
    }


def compute_quantiles(
    values: list[float],
    qs: list[float] | None = None,
) -> dict[str, float | None]:
    """Calcule les quantiles statistiques d'une série de valeurs numériques.

    Sprint Énergie P0.S1b (2026-05-29, brief P3) — SoT canonique des
    quartiles Q1/Q3 et médiane, à substituer au calcul frontend
    `MonitoringPage.jsx:_filterOutliers` qui faisait
    `Math.floor(length * 0.25)` côté JS (violation doctrine
    « zéro calcul métier frontend »).

    Méthode : interpolation linéaire entre les rangs (équivalent
    `numpy.quantile` avec method='linear'). Plus précis que la
    sélection par index `Math.floor` utilisée frontend.

    Args:
        values: liste de valeurs numériques (None et NaN ignorés).
        qs: liste de quantiles à calculer dans [0, 1]. Défaut
            [0.25, 0.5, 0.75] (Q1, médiane, Q3).

    Returns:
        Dict {label: value} avec clés standardisées :
        - "p25" (alias Q1) si 0.25 demandé
        - "p50" (alias médiane) si 0.5 demandé
        - "p75" (alias Q3) si 0.75 demandé
        - Pour autres quantiles, clé = f"p{int(q*100)}"
        - "n" : taille de la population filtrée
        - "iqr" : Q3 - Q1 (si Q1 et Q3 demandés)

        Valeurs `None` si population vide.

    Examples:
        >>> compute_quantiles([1, 2, 3, 4, 5])
        {'p25': 2.0, 'p50': 3.0, 'p75': 4.0, 'n': 5, 'iqr': 2.0}
        >>> compute_quantiles([])
        {'p25': None, 'p50': None, 'p75': None, 'n': 0, 'iqr': None}
        >>> compute_quantiles([10])
        {'p25': 10.0, 'p50': 10.0, 'p75': 10.0, 'n': 1, 'iqr': 0.0}
    """
    import math

    if qs is None:
        qs = [0.25, 0.5, 0.75]

    # Sanitize : retirer None / NaN / non-numérique
    clean: list[float] = []
    for v in values or []:
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isnan(f) or math.isinf(f):
            continue
        clean.append(f)

    n = len(clean)
    out: dict[str, float | None] = {"n": n}

    if n == 0:
        for q in qs:
            out[_q_label(q)] = None
        if 0.25 in qs and 0.75 in qs:
            out["iqr"] = None
        return out

    sorted_vals = sorted(clean)

    for q in qs:
        if not 0.0 <= q <= 1.0:
            out[_q_label(q)] = None
            continue
        out[_q_label(q)] = _quantile_linear(sorted_vals, q)

    if 0.25 in qs and 0.75 in qs:
        out["iqr"] = round(out["p75"] - out["p25"], 6)

    return out


def _quantile_linear(sorted_vals: list[float], q: float) -> float:
    """Interpolation linéaire entre rangs (méthode numpy linear)."""
    n = len(sorted_vals)
    if n == 1:
        return round(sorted_vals[0], 6)
    pos = q * (n - 1)
    lower = int(pos)
    upper = min(lower + 1, n - 1)
    frac = pos - lower
    return round(sorted_vals[lower] + frac * (sorted_vals[upper] - sorted_vals[lower]), 6)


def _q_label(q: float) -> str:
    """Convertit un quantile (0.25 / 0.5 / 0.75 / ...) en label payload."""
    return f"p{int(round(q * 100))}"


def get_org_subscribed_kw(
    db: Session,
    org_id: Optional[int],
) -> Optional[float]:
    """Puissance souscrite agrégée du scope (Σ Compteur.puissance_souscrite_kw).

    Returns:
        kW total souscrit si au moins 1 compteur a la donnée, None sinon.
    """
    from models import Meter

    meter_ids = _meter_ids_for_org(db, org_id)
    if not meter_ids:
        return None
    # Meter.subscribed_power_kva (modèle EN) ; Compteur.puissance_souscrite_kw
    # (modèle FR) — cf ADR-D-01 meter-compteur-duality. Les MeterReading
    # référencent Meter.id donc on agrège sur Meter. Conversion kVA → kW
    # approximée à 1.0 (cos φ ≈ 1 sur le tertiaire moderne avec compensation
    # réactif). Précision suffisante pour l'affichage P. souscrite cockpit.
    total = db.query(func.coalesce(func.sum(Meter.subscribed_power_kva), 0.0)).filter(Meter.id.in_(meter_ids)).scalar()
    return round(float(total), 2) if total and total > 0 else None
