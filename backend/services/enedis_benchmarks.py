"""
Benchmark sectoriel via agrégats Enedis Open Data.

Compare un site PROMEOS aux agrégats >36 kVA par secteur d'activité (NAF),
plage de puissance et profil, à la maille régionale.

Score d'atypie : distance normalisée entre le profil du site et le benchmark.
"""

import logging
import math
import time
from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from models.enedis_opendata import EnedisConsoSup36
from models.site import Site
from models.energy_models import Meter

logger = logging.getLogger(__name__)

_BENCH_CACHE: dict[tuple, tuple] = {}
_BENCH_CACHE_TTL = 3600  # 1h (les agrégats changent trimestriellement)

# ── Mapping TypeSite PROMEOS → secteur_activite Enedis Open Data ──────────
# Les agrégats Enedis utilisent les codes : S1: Agriculture, S2: Industrie,
# S3: Tertiaire, S4: Non Affecté (vérifié sur API ODS réelle 2025-06).
_TYPE_TO_ENEDIS_SECTOR = {
    "bureau": "S3: Tertiaire",
    "hotel": "S3: Tertiaire",
    "commerce": "S3: Tertiaire",
    "magasin": "S3: Tertiaire",
    "enseignement": "S3: Tertiaire",
    "sante": "S3: Tertiaire",
    "collectivite": "S3: Tertiaire",
    "copropriete": "S3: Tertiaire",
    "logement_social": "S3: Tertiaire",
    "usine": "S2: Industrie",
    "entrepot": "S3: Tertiaire",
    "agriculture": "S1: Agriculture",
}

# Mapping puissance souscrite → plage Enedis (vérifié sur API ODS réelle 2025-06)
# Convention Enedis : ]low, high] (strictement supérieur à low, inférieur ou égal à high)
# Condition : low < kva <= high
_POWER_RANGES = [
    (36, 120, "P1: ]36-120] kVA"),
    (120, 250, "P2: ]120-250] kVA"),
    (250, 1000, "P4: ]250-1000] kVA"),
    (1000, 2000, "P5: ]1000-2000] kVA"),
    (2000, float("inf"), "P6: > 2000 kVA"),
]


def compute_benchmark(db: Session, site_id: int, months: int = 12) -> dict | None:
    """Compare un site au benchmark sectoriel Enedis Open Data."""
    key = (site_id, months)
    cached = _BENCH_CACHE.get(key)
    if cached and time.monotonic() < cached[1]:
        return cached[0]

    result = _compute_benchmark(db, site_id, months)
    if result and "error" not in result:
        _BENCH_CACHE[key] = (result, time.monotonic() + _BENCH_CACHE_TTL)
    return result


def _compute_benchmark(db: Session, site_id: int, months: int) -> dict | None:
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return None

    arch_code = site.type.value if site.type else "bureau"
    sector = _TYPE_TO_ENEDIS_SECTOR.get(arch_code, "S3: Tertiaire")

    # Récupérer la puissance souscrite du site
    meter = db.query(Meter).filter(Meter.site_id == site_id, Meter.parent_meter_id.is_(None)).first()
    power_kva = getattr(meter, "subscribed_power_kva", None)
    power_range = _power_to_range(power_kva)

    end_date = date.today()
    start_date = end_date - timedelta(days=months * 30)
    start_dt = datetime(start_date.year, start_date.month, start_date.day)

    # ── Charger les agrégats Enedis correspondants ────────────────────
    bench_query = db.query(EnedisConsoSup36).filter(
        EnedisConsoSup36.horodate >= start_dt,
    )
    if sector:
        bench_query = bench_query.filter(EnedisConsoSup36.secteur_activite == sector)
    if power_range:
        bench_query = bench_query.filter(EnedisConsoSup36.plage_puissance == power_range)

    bench_rows = bench_query.all()

    if not bench_rows:
        # Fallback : ignorer le filtre puissance
        bench_rows = (
            db.query(EnedisConsoSup36)
            .filter(
                EnedisConsoSup36.horodate >= start_dt,
                EnedisConsoSup36.secteur_activite == sector,
            )
            .all()
        )

    has_opendata = len(bench_rows) > 0

    # ── Construire le profil benchmark (courbe moyenne par heure) ─────
    bench_hourly = defaultdict(list)
    bench_total_points = 0
    for row in bench_rows:
        if row.horodate and row.courbe_moyenne_wh is not None:
            bench_hourly[row.horodate.hour].append(row.courbe_moyenne_wh)
            bench_total_points = max(bench_total_points, row.nb_points_soutirage or 0)

    bench_profile = {}
    for h in range(24):
        vals = bench_hourly.get(h, [])
        bench_profile[h] = sum(vals) / len(vals) if vals else 0

    # ── Charger la consommation réelle du site ────────────────────────
    from data_staging.bridge import get_site_meter_ids, get_readings

    meter_ids = get_site_meter_ids(db, site_id)
    if not meter_ids:
        return {"error": "Aucun compteur principal", "site_id": site_id}

    raw_readings, data_source = get_readings(db, meter_ids, start_dt)
    site_readings = [(r.timestamp, r.value_kwh) for r in raw_readings]

    if len(site_readings) < 30:
        return {
            "error": "Données site insuffisantes",
            "readings": len(site_readings),
            "has_opendata": has_opendata,
            "opendata_rows": len(bench_rows),
        }

    # Profil horaire du site
    site_hourly = defaultdict(list)
    for ts, kwh in site_readings:
        site_hourly[ts.hour].append(kwh or 0)

    site_profile = {}
    for h in range(24):
        vals = site_hourly.get(h, [])
        site_profile[h] = sum(vals) / len(vals) if vals else 0

    # ── Score d'atypie ────────────────────────────────────────────────
    if has_opendata and any(bench_profile.values()):
        atypicity = _compute_atypicity(site_profile, bench_profile)
    else:
        atypicity = None

    # ── Consommation spécifique ───────────────────────────────────────
    surface = site.surface_m2 or getattr(site, "tertiaire_area_m2", None) or 1000
    total_kwh = sum(kwh or 0 for _, kwh in site_readings)
    period_days = (end_date - start_date).days
    conso_kwh_m2_year = (total_kwh / surface) * (365 / max(period_days, 1)) if surface > 0 else 0

    # ── Profil horaire comparé (24 valeurs) ───────────────────────────
    comparison = []
    for h in range(24):
        comparison.append(
            {
                "hour": h,
                "site_wh": round(site_profile.get(h, 0) * 1000, 0),  # kWh → Wh
                "benchmark_wh": round(bench_profile.get(h, 0), 0),
            }
        )

    return {
        "site_id": site_id,
        "site_name": site.nom,
        "archetype": arch_code,
        "sector_enedis": sector,
        "data_source": data_source,
        "power_range": power_range,
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "has_opendata": has_opendata,
        "opendata_stats": {
            "rows": len(bench_rows),
            "max_points_soutirage": bench_total_points,
            "sector_filter": sector,
            "power_filter": power_range,
        },
        "site_stats": {
            "readings": len(site_readings),
            "total_kwh": round(total_kwh, 0),
            "conso_kwh_m2_year": round(conso_kwh_m2_year, 1),
            "surface_m2": round(surface),
        },
        "atypicity": {
            "score": round(atypicity, 3) if atypicity is not None else None,
            "label": _atypicity_label(atypicity) if atypicity is not None else "indisponible",
            "description": _atypicity_description(atypicity),
        },
        "hourly_comparison": comparison,
        "disclaimer": (
            f"Comparaison basée sur la moyenne du segment {sector} Enedis "
            f"({bench_total_points} points). Les écarts individuels sont typiquement de 20-40%."
            if has_opendata
            else "Aucune donnée Open Data importée. Lancez POST /api/connectors/enedis_opendata/sync pour importer."
        ),
    }


def _compute_atypicity(site_profile: dict, bench_profile: dict) -> float:
    """Score d'atypie normalisé 0-1.

    A = RMSE(site_norm, bench_norm) / max_possible_rmse
    Normalise les deux profils par leur moyenne pour comparer les formes.
    """
    site_mean = sum(site_profile.values()) / max(len(site_profile), 1)
    bench_mean = sum(bench_profile.values()) / max(len(bench_profile), 1)

    if site_mean == 0 or bench_mean == 0:
        return 0.5

    # Normaliser les deux profils (forme, pas volume)
    site_norm = {h: v / site_mean for h, v in site_profile.items()}
    bench_norm = {h: v / bench_mean for h, v in bench_profile.items()}

    # RMSE entre profils normalisés
    hours = set(site_norm.keys()) & set(bench_norm.keys())
    if not hours:
        return 0.5

    sq_diff = sum((site_norm[h] - bench_norm[h]) ** 2 for h in hours)
    rmse = math.sqrt(sq_diff / len(hours))

    # Normaliser sur 0-1 (RMSE max théorique ~2 pour profils normalisés)
    score = min(1.0, rmse / 1.5)
    return score


def _atypicity_label(score: float | None) -> str:
    if score is None:
        return "indisponible"
    if score < 0.15:
        return "typique"
    if score < 0.30:
        return "modere"
    if score < 0.50:
        return "atypique"
    return "tres_atypique"


def _atypicity_description(score: float | None) -> str:
    if score is None:
        return "Pas assez de données Open Data pour calculer le score."
    label = _atypicity_label(score)
    return {
        "typique": "Profil conforme au segment sectoriel.",
        "modere": "Écart modéré — vérifier les usages spécifiques.",
        "atypique": "Profil atypique — diagnostic recommandé.",
        "tres_atypique": "Très atypique — anomalie probable ou activité mixte.",
    }.get(label, "")


def _power_to_range(kva: float | None) -> str | None:
    """Convertit une puissance souscrite en code plage Enedis. None si ≤36 kVA ou inconnue.

    Convention Enedis : ]low, high] → low < kva <= high.
    """
    if kva is None:
        return None
    for low, high, code in _POWER_RANGES:
        if low < kva <= high:
            return code
    return None
