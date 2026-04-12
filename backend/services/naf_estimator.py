"""
Estimateur pré-consentement : génère une courbe de référence pour un NAF + puissance.

Source : agrégats Enedis Open Data (conso-sup36-region, NAF × puissance × région).
Sans données client — permet de démontrer la valeur produit avant signature.

Cas d'usage :
- Simulation pré-vente : "voici à quoi ressemble la courbe type d'un site comme le vôtre"
- Dimensionnement PV : recouvrement PV simulé vs courbe de référence
- Estimation de consommation annuelle pour un nouveau site sans historique
- Benchmark pour prospects non consentants
"""

import logging
import math
import time
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone

from sqlalchemy.orm import Session

from models.enedis_opendata import EnedisConsoSup36

logger = logging.getLogger(__name__)

_ESTIMATOR_CACHE: dict[tuple, tuple] = {}
_CACHE_TTL = 3600  # 1h — les agrégats changent trimestriellement

# Mapping NAF prefix → secteur Enedis (doit matcher enedis_benchmarks.py)
_NAF_PREFIX_TO_SECTOR = {
    # Agriculture
    "01": "S1: Agriculture",
    "02": "S1: Agriculture",
    "03": "S1: Agriculture",
    # Industrie
    "05": "S2: Industrie",
    "06": "S2: Industrie",
    "07": "S2: Industrie",
    "08": "S2: Industrie",
    "09": "S2: Industrie",
    "10": "S2: Industrie",
    "11": "S2: Industrie",
    "12": "S2: Industrie",
    "13": "S2: Industrie",
    "14": "S2: Industrie",
    "15": "S2: Industrie",
    "16": "S2: Industrie",
    "17": "S2: Industrie",
    "18": "S2: Industrie",
    "19": "S2: Industrie",
    "20": "S2: Industrie",
    "21": "S2: Industrie",
    "22": "S2: Industrie",
    "23": "S2: Industrie",
    "24": "S2: Industrie",
    "25": "S2: Industrie",
    "26": "S2: Industrie",
    "27": "S2: Industrie",
    "28": "S2: Industrie",
    "29": "S2: Industrie",
    "30": "S2: Industrie",
    "31": "S2: Industrie",
    "32": "S2: Industrie",
    "33": "S2: Industrie",
    "35": "S2: Industrie",
    "36": "S2: Industrie",
    "37": "S2: Industrie",
    "38": "S2: Industrie",
    "39": "S2: Industrie",
    # Tertiaire (commerce, transport, hébergement, services, admin, santé, enseignement)
}


def _naf_to_sector(naf_code: str) -> str:
    """Convertit un code NAF (ex: 6201Z) en secteur Enedis."""
    if not naf_code:
        return "S3: Tertiaire"
    prefix = naf_code.strip()[:2]
    return _NAF_PREFIX_TO_SECTOR.get(prefix, "S3: Tertiaire")


def _power_to_range(kva: float | None) -> str | None:
    """Convention Enedis : ]low, high] → low < kva <= high."""
    if kva is None or kva <= 36:
        return None
    for low, high, code in (
        (36, 120, "P1: ]36-120] kVA"),
        (120, 250, "P2: ]120-250] kVA"),
        (250, 1000, "P4: ]250-1000] kVA"),
        (1000, 2000, "P5: ]1000-2000] kVA"),
        (2000, float("inf"), "P6: > 2000 kVA"),
    ):
        if low < kva <= high:
            return code
    return None


def estimate_reference_curve(
    db: Session,
    naf_code: str,
    power_kva: float,
    months: int = 12,
) -> dict | None:
    """Génère une courbe de référence pour un NAF + puissance.

    Retourne :
    - profil horaire type (24 valeurs kWh)
    - consommation annuelle estimée (kWh)
    - nombre de points de référence dans l'agrégat
    - intervalle de confiance (stddev)
    - dérivés : load factor estimé, part thermosensible, saisonnalité
    """
    key = (naf_code, round(power_kva, 0), months)
    cached = _ESTIMATOR_CACHE.get(key)
    if cached and time.monotonic() < cached[1]:
        return cached[0]

    result = _estimate(db, naf_code, power_kva, months)
    if result and "error" not in result:
        _ESTIMATOR_CACHE[key] = (result, time.monotonic() + _CACHE_TTL)
    return result


def _estimate(db: Session, naf_code: str, power_kva: float, months: int) -> dict | None:
    sector = _naf_to_sector(naf_code)
    power_range = _power_to_range(power_kva)

    if power_range is None:
        return {
            "error": "Puissance hors périmètre agrégats Enedis >36 kVA",
            "power_kva": power_kva,
            "naf_code": naf_code,
        }

    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)
    start_dt = datetime(start_date.year, start_date.month, start_date.day)

    # Query agrégats (seulement colonnes nécessaires, pas les ORM)
    rows = (
        db.query(
            EnedisConsoSup36.horodate,
            EnedisConsoSup36.courbe_moyenne_wh,
            EnedisConsoSup36.nb_points_soutirage,
        )
        .filter(
            EnedisConsoSup36.horodate >= start_dt,
            EnedisConsoSup36.secteur_activite == sector,
            EnedisConsoSup36.plage_puissance == power_range,
        )
        .all()
    )

    if not rows:
        # Fallback sans filtre puissance
        rows = (
            db.query(
                EnedisConsoSup36.horodate,
                EnedisConsoSup36.courbe_moyenne_wh,
                EnedisConsoSup36.nb_points_soutirage,
            )
            .filter(
                EnedisConsoSup36.horodate >= start_dt,
                EnedisConsoSup36.secteur_activite == sector,
            )
            .all()
        )
        if not rows:
            return {
                "error": "Aucune donnée Open Data pour ce secteur/puissance",
                "sector": sector,
                "power_range": power_range,
                "hint": "Lancez POST /api/connectors/enedis_opendata/sync pour importer les agrégats.",
            }

    # Profil horaire type (moyenne par heure)
    hourly_values: dict[int, list[float]] = defaultdict(list)
    hourly_counts: dict[int, list[int]] = defaultdict(list)
    monthly_values: dict[int, list[float]] = defaultdict(list)
    max_points = 0

    for ts, wh, nb_pts in rows:
        if ts is None or wh is None:
            continue
        hourly_values[ts.hour].append(wh)
        hourly_counts[ts.hour].append(nb_pts or 0)
        monthly_values[ts.month].append(wh)
        max_points = max(max_points, nb_pts or 0)

    if not hourly_values:
        return {"error": "Agrégats vides pour ce segment"}

    hourly_profile = []
    hourly_stddev = []
    for h in range(24):
        vals = hourly_values.get(h, [])
        if vals:
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / len(vals) if len(vals) > 1 else 0
            std = math.sqrt(variance)
            # Conversion Wh → kWh pour affichage
            hourly_profile.append(round(mean / 1000, 2))
            hourly_stddev.append(round(std / 1000, 2))
        else:
            hourly_profile.append(0)
            hourly_stddev.append(0)

    # Consommation annuelle estimée (moyenne × 365 × 48 pas/jour)
    daily_energy_kwh = sum(hourly_profile) * 2  # 2 pas 30min par heure
    annual_kwh_estimate = daily_energy_kwh * 365

    # Load factor estimé
    p_max = max(hourly_profile) if hourly_profile else 0
    p_mean = sum(hourly_profile) / len(hourly_profile) if hourly_profile else 0
    load_factor = p_mean / p_max if p_max > 0 else 0

    # Ratio nuit/jour
    night_sum = sum(hourly_profile[h] for h in range(24) if h >= 22 or h < 6)
    day_sum = sum(hourly_profile[h] for h in range(24) if 6 <= h < 22)
    night_day_ratio = night_sum / day_sum if day_sum > 0 else 0

    # Saisonnalité : écart hiver vs été
    monthly_mean = {}
    for month, vals in monthly_values.items():
        if vals:
            monthly_mean[month] = sum(vals) / len(vals) / 1000  # kWh
    winter = [monthly_mean.get(m, 0) for m in (12, 1, 2)]
    summer = [monthly_mean.get(m, 0) for m in (6, 7, 8)]
    winter_mean = sum(winter) / len(winter) if any(winter) else 0
    summer_mean = sum(summer) / len(summer) if any(summer) else 0
    seasonality_ratio = winter_mean / summer_mean if summer_mean > 0 else 0

    return {
        "naf_code": naf_code,
        "power_kva": power_kva,
        "sector": sector,
        "power_range": power_range,
        "period_months": months,
        "reference": {
            "hourly_profile_kwh": hourly_profile,
            "hourly_stddev_kwh": hourly_stddev,
            "daily_kwh": round(daily_energy_kwh, 1),
            "annual_kwh_estimate": round(annual_kwh_estimate, 0),
        },
        "kpis": {
            "load_factor": round(load_factor, 3),
            "night_day_ratio": round(night_day_ratio, 3),
            "seasonality_winter_summer_ratio": round(seasonality_ratio, 2),
        },
        "sample": {
            "n_points_in_aggregate": max_points,
            "n_rows_queried": len(rows),
            "confidence": "high" if max_points > 100 else "medium" if max_points > 20 else "low",
        },
        "disclaimer": (
            f"Courbe de référence basée sur {max_points} points Enedis du segment "
            f"{sector} × {power_range}. Écart individuel typique : 20-40%. "
            f"À utiliser comme ordre de grandeur avant consentement client."
        ),
    }


# ── Tendance mensuelle par secteur ──────────────────────────────────────


def compute_sector_trend(db: Session, naf_code: str, power_kva: float | None = None) -> dict | None:
    """Tendance mensuelle de consommation pour un secteur.

    Retourne l'évolution mois par mois de l'énergie moyenne et du nb de points.
    Permet de détecter saisonnalité et dérives sectorielles.
    """
    sector = _naf_to_sector(naf_code)
    power_range = _power_to_range(power_kva) if power_kva else None

    query = db.query(
        EnedisConsoSup36.horodate,
        EnedisConsoSup36.courbe_moyenne_wh,
        EnedisConsoSup36.nb_points_soutirage,
    ).filter(EnedisConsoSup36.secteur_activite == sector)
    if power_range:
        query = query.filter(EnedisConsoSup36.plage_puissance == power_range)

    rows = query.all()
    if not rows:
        return {"error": "Aucune donnée Open Data", "sector": sector, "power_range": power_range}

    # Agréger par (année, mois)
    monthly: dict[tuple[int, int], list[float]] = defaultdict(list)
    monthly_points: dict[tuple[int, int], int] = defaultdict(int)
    for ts, wh, nb in rows:
        if ts is None or wh is None:
            continue
        key = (ts.year, ts.month)
        monthly[key].append(wh / 1000)  # Wh → kWh
        monthly_points[key] = max(monthly_points[key], nb or 0)

    if not monthly:
        return {"error": "Données vides après agrégation"}

    trend = []
    for (year, month), vals in sorted(monthly.items()):
        mean_kwh = sum(vals) / len(vals)
        variance = sum((v - mean_kwh) ** 2 for v in vals) / len(vals) if len(vals) > 1 else 0
        trend.append(
            {
                "year": year,
                "month": month,
                "label": f"{year}-{month:02d}",
                "mean_kwh": round(mean_kwh, 2),
                "stddev_kwh": round(math.sqrt(variance), 2),
                "n_samples": len(vals),
                "n_points": monthly_points[(year, month)],
            }
        )

    # Variation vs moyenne globale
    all_means = [m["mean_kwh"] for m in trend]
    overall_mean = sum(all_means) / len(all_means) if all_means else 0
    for m in trend:
        m["deviation_pct"] = round((m["mean_kwh"] - overall_mean) / overall_mean * 100, 1) if overall_mean > 0 else 0

    return {
        "naf_code": naf_code,
        "sector": sector,
        "power_range": power_range,
        "overall_mean_kwh": round(overall_mean, 2),
        "n_months": len(trend),
        "trend": trend,
    }


# ── Comparaison site vs secteur (mois par mois) ─────────────────────────


def compare_site_vs_sector(db: Session, site_id: int, months: int = 12, persist_alerts: bool = False) -> dict | None:
    """Compare la consommation d'un site à la moyenne de son secteur, mois par mois.

    Calcule l'écart pct et détecte les mois atypiques (>20% écart).
    Si persist_alerts=True, crée des Anomaly en DB pour chaque mois atypique.
    """
    from models.site import Site
    from models.energy_models import Meter
    from data_staging.bridge import get_site_meter_ids, get_daily_kwh

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return None

    # Mapping archetype → NAF prefix inverse (fallback)
    arch = site.type.value if site.type else "bureau"

    # Récupérer puissance
    meter = db.query(Meter).filter(Meter.site_id == site_id, Meter.parent_meter_id.is_(None)).first()
    power_kva = getattr(meter, "subscribed_power_kva", None) if meter else None

    # Construire le NAF du site (si NAF réel dispo, sinon archetype)
    naf_code = getattr(site, "naf_code", None) or _archetype_to_naf(arch)
    sector = _naf_to_sector(naf_code)
    power_range = _power_to_range(power_kva)

    # Charger la consommation du site
    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)
    start_dt = datetime(start_date.year, start_date.month, start_date.day)

    meter_ids = get_site_meter_ids(db, site_id)
    if not meter_ids:
        return {"error": "Aucun compteur principal", "site_id": site_id}

    daily_kwh, data_source = get_daily_kwh(db, meter_ids, start_dt)
    if not daily_kwh:
        return {"error": "Aucune donnée site"}

    # Agréger par mois
    site_monthly: dict[tuple[int, int], float] = defaultdict(float)
    for day_str, kwh in daily_kwh.items():
        try:
            y, m, d = map(int, day_str.split("-")[:3])
            site_monthly[(y, m)] += kwh
        except (ValueError, AttributeError):
            continue

    # Charger le benchmark sectoriel mensuel
    bench_query = db.query(
        EnedisConsoSup36.horodate,
        EnedisConsoSup36.courbe_moyenne_wh,
    ).filter(
        EnedisConsoSup36.horodate >= start_dt,
        EnedisConsoSup36.secteur_activite == sector,
    )
    if power_range:
        bench_query = bench_query.filter(EnedisConsoSup36.plage_puissance == power_range)
    bench_rows = bench_query.all()

    bench_monthly: dict[tuple[int, int], list[float]] = defaultdict(list)
    for ts, wh in bench_rows:
        if ts is None or wh is None:
            continue
        key = (ts.year, ts.month)
        # Convertir courbe moyenne 30min (Wh) en kWh/jour estimé
        # 1 pas 30min × 48 pas × 30 jours
        bench_monthly[key].append(wh * 48 * 30 / 1000)

    # Comparer
    comparison = []
    alerts = []
    for (y, m), site_kwh in sorted(site_monthly.items()):
        bench_vals = bench_monthly.get((y, m), [])
        if bench_vals:
            bench_mean = sum(bench_vals) / len(bench_vals)
            deviation_pct = round((site_kwh - bench_mean) / bench_mean * 100, 1) if bench_mean > 0 else 0
            atypical = abs(deviation_pct) > 20
            if atypical:
                alerts.append(
                    {
                        "month": f"{y}-{m:02d}",
                        "deviation_pct": deviation_pct,
                        "message": (
                            f"Site {'au-dessus' if deviation_pct > 0 else 'en-dessous'} "
                            f"de {abs(deviation_pct)}% vs secteur en {y}-{m:02d}"
                        ),
                    }
                )
        else:
            bench_mean = None
            deviation_pct = None
            atypical = False

        comparison.append(
            {
                "month": f"{y}-{m:02d}",
                "site_kwh": round(site_kwh, 0),
                "benchmark_kwh": round(bench_mean, 0) if bench_mean else None,
                "deviation_pct": deviation_pct,
                "atypical": atypical,
            }
        )

    # Persister les anomalies si demandé
    persisted_anomaly_ids = []
    if persist_alerts and alerts:
        from models.energy_models import Anomaly, AnomalySeverity, Meter

        main_meter = db.query(Meter).filter(Meter.site_id == site_id, Meter.parent_meter_id.is_(None)).first()
        if main_meter:
            # Désactiver les anciennes anomalies d'atypie sectorielle
            db.query(Anomaly).filter(
                Anomaly.meter_id == main_meter.id,
                Anomaly.anomaly_code == "ANOM_ATYPIE_MENSUELLE_SECTEUR",
                Anomaly.is_active.is_(True),
            ).update({"is_active": False})

            for alert in alerts:
                dev = alert["deviation_pct"]
                severity = AnomalySeverity.HIGH if abs(dev) > 40 else AnomalySeverity.MEDIUM

                anom = Anomaly(
                    meter_id=main_meter.id,
                    anomaly_code="ANOM_ATYPIE_MENSUELLE_SECTEUR",
                    title=f"Écart sectoriel atypique — {alert['month']}",
                    description=alert["message"],
                    severity=severity,
                    confidence=0.75,
                    detected_at=datetime.now(timezone.utc),
                    measured_value=dev,
                    threshold_value=20.0,
                    deviation_pct=dev,
                    explanation_json={
                        "month": alert["month"],
                        "sector": sector,
                        "deviation_pct": dev,
                    },
                    is_active=True,
                )
                db.add(anom)
                db.flush()
                persisted_anomaly_ids.append(anom.id)
            db.commit()

    return {
        "site_id": site_id,
        "site_name": site.nom,
        "archetype": arch,
        "naf_code": naf_code,
        "sector": sector,
        "power_range": power_range,
        "persisted_anomaly_ids": persisted_anomaly_ids,
        "data_source": data_source,
        "comparison": comparison,
        "alerts": alerts,
        "n_months": len(comparison),
        "n_alerts": len(alerts),
    }


def _archetype_to_naf(archetype: str) -> str:
    """Fallback : archetype PROMEOS → code NAF représentatif."""
    mapping = {
        "bureau": "6201Z",
        "hotel": "5510Z",
        "commerce": "4711D",
        "magasin": "4711D",
        "enseignement": "8542Z",
        "sante": "8610Z",
        "collectivite": "8411Z",
        "copropriete": "6832A",
        "logement_social": "6820A",
        "usine": "2561Z",
        "entrepot": "5210A",
    }
    return mapping.get(archetype, "6201Z")
