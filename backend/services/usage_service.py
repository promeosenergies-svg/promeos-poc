"""
PROMEOS — Service Usage V1.1
Readiness Score, Metering Plan, Usage Cost Breakdown, Top UES.

Entite pivot reliant Patrimoine → Usage → Derive → Action → Conformite → Facture.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Site,
    Usage,
    UsageBaseline,
    Meter,
    MeterReading,
    ConsumptionInsight,
    USAGE_LABELS_FR,
    USAGE_FAMILY_MAP,
    TypeUsage,
    UsageFamily,
    DataSourceType,
)
from models.energy_models import FrequencyType
from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH


# ── Usage Readiness Score ─────────────────────────────────────────────────


def compute_usage_readiness(db: Session, site_id: int) -> dict:
    """Calcule le score de readiness usage d'un site.

    Score /100 composite :
    - 30 pts : usages declares vs attendus
    - 30 pts : couverture sous-comptage (kWh sous-compteurs / kWh principal)
    - 20 pts : qualite donnees (quality_score moyen des readings)
    - 20 pts : anciennete donnees (>= 365j = 100%)

    Retourne : {score, level, details, recommendations}
    """
    # 1. Usages declares
    usages = db.query(Usage).join(Usage.batiment).filter(Usage.batiment.has(site_id=site_id)).all()
    nb_usages = len(usages)
    # Attendu : min 3 usages pour un site tertiaire standard
    expected_usages = max(3, nb_usages)
    usage_score = min(30, round(nb_usages / max(1, expected_usages) * 30))

    # 2. Couverture sous-comptage
    principals = (
        db.query(Meter)
        .filter(Meter.site_id == site_id, Meter.is_active.is_(True), Meter.parent_meter_id.is_(None))
        .all()
    )
    subs = (
        db.query(Meter)
        .filter(Meter.site_id == site_id, Meter.is_active.is_(True), Meter.parent_meter_id.isnot(None))
        .all()
    )

    principal_kwh = 0
    sub_kwh = 0
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=365)

    for m in principals:
        kwh = (
            db.query(func.sum(MeterReading.value_kwh))
            .filter(MeterReading.meter_id == m.id, MeterReading.timestamp >= cutoff)
            .scalar()
            or 0
        )
        principal_kwh += kwh

    for s in subs:
        kwh = (
            db.query(func.sum(MeterReading.value_kwh))
            .filter(MeterReading.meter_id == s.id, MeterReading.timestamp >= cutoff)
            .scalar()
            or 0
        )
        sub_kwh += kwh

    coverage_pct = (sub_kwh / principal_kwh * 100) if principal_kwh > 0 else 0
    sub_score = min(30, round(coverage_pct / 100 * 30))

    # 3. Qualite donnees
    all_meter_ids = [m.id for m in principals + subs]
    if all_meter_ids:
        avg_quality = (
            db.query(func.avg(MeterReading.quality_score))
            .filter(
                MeterReading.meter_id.in_(all_meter_ids),
                MeterReading.quality_score.isnot(None),
                MeterReading.timestamp >= cutoff,
            )
            .scalar()
            or 0
        )
    else:
        avg_quality = 0
    quality_score = min(20, round(avg_quality * 20))

    # 4. Anciennete
    if all_meter_ids:
        oldest = db.query(func.min(MeterReading.timestamp)).filter(MeterReading.meter_id.in_(all_meter_ids)).scalar()
        if oldest:
            days_of_data = (datetime.utcnow() - oldest).days
            depth_pct = min(1.0, days_of_data / 365)
        else:
            depth_pct = 0
    else:
        depth_pct = 0
    depth_score = min(20, round(depth_pct * 20))

    total = usage_score + sub_score + quality_score + depth_score

    # Level
    if total >= 75:
        level = "GREEN"
    elif total >= 40:
        level = "AMBER"
    else:
        level = "RED"

    # Recommendations
    recos = []
    if nb_usages < 3:
        recos.append("Declarer les usages energetiques du site (min. 3 : chauffage, eclairage, IT)")
    if coverage_pct < 50:
        recos.append("Installer des sous-compteurs pour couvrir >50% de la consommation")
    if avg_quality < 0.7:
        recos.append("Ameliorer la qualite des donnees (compteur communicant, releve automatique)")
    if depth_pct < 0.5:
        recos.append("Accumuler au moins 6 mois d'historique pour un diagnostic fiable")
    if not subs:
        recos.append("Aucun sous-compteur installe — plan de comptage a creer")

    return {
        "score": total,
        "level": level,
        "details": {
            "usages_declared": {"score": usage_score, "max": 30, "count": nb_usages},
            "sub_metering_coverage": {"score": sub_score, "max": 30, "pct": round(coverage_pct, 1)},
            "data_quality": {"score": quality_score, "max": 20, "avg": round(avg_quality, 2)},
            "data_depth": {"score": depth_score, "max": 20, "days": round(depth_pct * 365)},
        },
        "recommendations": recos,
        "meters_count": len(principals),
        "sub_meters_count": len(subs),
        "usages_count": nb_usages,
    }


# ── Metering Plan ─────────────────────────────────────────────────────────


def get_metering_plan(db: Session, site_id: int) -> dict:
    """Construit le plan de comptage dynamique d'un site.

    Retourne l'arbre hierarchique : compteur principal → sous-compteurs
    avec pour chaque noeud : usage associe, kWh, % du total, source de donnee.
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=365)

    principals = (
        db.query(Meter)
        .filter(Meter.site_id == site_id, Meter.is_active.is_(True), Meter.parent_meter_id.is_(None))
        .all()
    )

    plan = []
    for p in principals:
        p_kwh = (
            db.query(func.sum(MeterReading.value_kwh))
            .filter(MeterReading.meter_id == p.id, MeterReading.timestamp >= cutoff)
            .scalar()
            or 0
        )

        # Sous-compteurs
        subs = db.query(Meter).filter(Meter.parent_meter_id == p.id, Meter.is_active.is_(True)).all()

        sub_list = []
        sub_total = 0
        for s in subs:
            s_kwh = (
                db.query(func.sum(MeterReading.value_kwh))
                .filter(MeterReading.meter_id == s.id, MeterReading.timestamp >= cutoff)
                .scalar()
                or 0
            )
            sub_total += s_kwh

            # Resolve usage
            usage_info = _resolve_usage(db, s)

            sub_list.append(
                {
                    "id": s.id,
                    "meter_id": s.meter_id,
                    "name": s.name,
                    "energy_vector": s.energy_vector.value if s.energy_vector else None,
                    "kwh": round(s_kwh, 1),
                    "pct_of_principal": round(s_kwh / p_kwh * 100, 1) if p_kwh > 0 else 0,
                    "usage": usage_info,
                    "data_source": _infer_data_source(db, s),
                    "has_readings": s_kwh > 0,
                }
            )

        delta = p_kwh - sub_total

        plan.append(
            {
                "id": p.id,
                "meter_id": p.meter_id,
                "name": p.name,
                "energy_vector": p.energy_vector.value if p.energy_vector else None,
                "kwh": round(p_kwh, 1),
                "sub_meters": sub_list,
                "sub_total_kwh": round(sub_total, 1),
                "delta_kwh": round(delta, 1),
                "delta_pct": round(delta / p_kwh * 100, 1) if p_kwh > 0 else 0,
                "delta_label": "Pertes & parties communes" if delta >= 0 else "Ecart negatif (anomalie)",
                "coverage_pct": round(sub_total / p_kwh * 100, 1) if p_kwh > 0 else 0,
            }
        )

    return {
        "site_id": site_id,
        "meters": plan,
        "total_principals": len(principals),
        "total_sub_meters": sum(len(m["sub_meters"]) for m in plan),
    }


# ── Top UES (Usages Energetiques Significatifs) ──────────────────────────


def get_top_ues(db: Session, site_id: int, limit: int = 5) -> list[dict]:
    """Retourne les usages significatifs d'un site, tries par kWh decroissant.

    Source : sous-compteurs lies a des usages (mesure reelle).
    Fallback : usages declares avec pct_of_total estime.
    """
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=365)

    # Sous-compteurs avec usage_id
    subs_with_usage = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active.is_(True),
            Meter.usage_id.isnot(None),
        )
        .all()
    )

    # Conso totale du site (principaux)
    total_kwh = (
        db.query(func.sum(MeterReading.value_kwh))
        .join(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active.is_(True),
            Meter.parent_meter_id.is_(None),
            MeterReading.timestamp >= cutoff,
        )
        .scalar()
        or 0
    )

    usage_kwh = {}  # usage_id → kwh
    usage_objs = {}  # usage_id → Usage

    for s in subs_with_usage:
        kwh = (
            db.query(func.sum(MeterReading.value_kwh))
            .filter(MeterReading.meter_id == s.id, MeterReading.timestamp >= cutoff)
            .scalar()
            or 0
        )
        usage_kwh[s.usage_id] = usage_kwh.get(s.usage_id, 0) + kwh
        if s.usage_id not in usage_objs:
            usage_objs[s.usage_id] = db.query(Usage).filter(Usage.id == s.usage_id).first()

    # Fallback: usages declares sans mesure directe
    declared_usages = db.query(Usage).join(Usage.batiment).filter(Usage.batiment.has(site_id=site_id)).all()
    for u in declared_usages:
        if u.id not in usage_kwh:
            # Utiliser pct_of_total estime si disponible
            if u.pct_of_total and total_kwh > 0:
                usage_kwh[u.id] = total_kwh * u.pct_of_total / 100
                usage_objs[u.id] = u

    # Trier par kWh decroissant
    sorted_usages = sorted(usage_kwh.items(), key=lambda x: x[1], reverse=True)[:limit]

    result = []
    for uid, kwh in sorted_usages:
        u = usage_objs.get(uid)
        if not u:
            continue

        # Check for active drifts on this usage
        drift_insights = (
            db.query(ConsumptionInsight)
            .filter(
                ConsumptionInsight.site_id == site_id,
                ConsumptionInsight.usage_id == uid,
                ConsumptionInsight.type == "derive",
            )
            .all()
        )

        result.append(
            {
                "usage_id": uid,
                "type": u.type.value,
                "label": u.label or USAGE_LABELS_FR.get(u.type, u.type.value),
                "family": USAGE_FAMILY_MAP.get(u.type, UsageFamily.AUXILIAIRES).value,
                "kwh": round(kwh, 1),
                "pct_of_total": round(kwh / total_kwh * 100, 1) if total_kwh > 0 else 0,
                "is_significant": u.is_significant,
                "data_source": u.data_source.value if u.data_source else "estimation_prorata",
                "has_drift": len(drift_insights) > 0,
                "drift_pct": _extract_drift_pct(drift_insights[0]) if drift_insights else None,
                "surface_m2": u.surface_m2,
                "ipe_kwh_m2": round(kwh / u.surface_m2, 1) if u.surface_m2 and u.surface_m2 > 0 else None,
            }
        )

    return result


# ── Usage Cost Breakdown ─────────────────────────────────────────────────


def get_usage_cost_breakdown(db: Session, site_id: int, days: int = 365) -> dict:
    """Ventile le cout energetique par usage, pro-rata sous-compteur.

    Utilise le prix moyen EUR/kWh du site ou le default.
    """
    from routes.site_config import get_site_price_ref

    price_ref = get_site_price_ref(db, site_id)
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

    # Conso totale
    total_kwh = (
        db.query(func.sum(MeterReading.value_kwh))
        .join(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active.is_(True),
            Meter.parent_meter_id.is_(None),
            MeterReading.timestamp >= cutoff,
        )
        .scalar()
        or 0
    )

    # Par usage (sous-compteurs)
    subs = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active.is_(True),
            Meter.usage_id.isnot(None),
        )
        .all()
    )

    usage_costs = {}
    for s in subs:
        kwh = (
            db.query(func.sum(MeterReading.value_kwh))
            .filter(MeterReading.meter_id == s.id, MeterReading.timestamp >= cutoff)
            .scalar()
            or 0
        )
        uid = s.usage_id
        if uid not in usage_costs:
            u = db.query(Usage).filter(Usage.id == uid).first()
            usage_costs[uid] = {
                "usage_id": uid,
                "type": u.type.value if u else "autres",
                "label": (u.label or USAGE_LABELS_FR.get(u.type, u.type.value)) if u else "?",
                "kwh": 0,
                "eur": 0,
            }
        usage_costs[uid]["kwh"] += kwh
        usage_costs[uid]["eur"] += kwh * price_ref

    # Non couvert
    covered_kwh = sum(v["kwh"] for v in usage_costs.values())
    uncovered_kwh = max(0, total_kwh - covered_kwh)

    items = sorted(usage_costs.values(), key=lambda x: x["kwh"], reverse=True)
    for item in items:
        item["kwh"] = round(item["kwh"], 1)
        item["eur"] = round(item["eur"], 0)
        item["pct_of_total"] = round(item["kwh"] / total_kwh * 100, 1) if total_kwh > 0 else 0

    return {
        "site_id": site_id,
        "period_days": days,
        "price_ref_eur_kwh": price_ref,
        "total_kwh": round(total_kwh, 1),
        "total_eur": round(total_kwh * price_ref, 0),
        "by_usage": items,
        "uncovered_kwh": round(uncovered_kwh, 1),
        "uncovered_eur": round(uncovered_kwh * price_ref, 0),
        "coverage_pct": round(covered_kwh / total_kwh * 100, 1) if total_kwh > 0 else 0,
    }


# ── Page /usages aggregate endpoint ─────────────────────────────────────


def get_usages_dashboard(db: Session, site_id: int) -> dict:
    """Endpoint agrege pour la page /usages : readiness + plan + UES + derives + cost."""
    readiness = compute_usage_readiness(db, site_id)
    plan = get_metering_plan(db, site_id)
    ues = get_top_ues(db, site_id)
    cost = get_usage_cost_breakdown(db, site_id)

    # Derives actives par usage
    active_drifts = (
        db.query(ConsumptionInsight)
        .filter(
            ConsumptionInsight.site_id == site_id,
            ConsumptionInsight.type.in_(["derive", "hors_horaires", "base_load"]),
        )
        .all()
    )

    drift_list = []
    for d in active_drifts:
        usage_label = None
        usage_type = None
        if getattr(d, "usage_id", None):
            u = db.query(Usage).filter(Usage.id == d.usage_id).first()
            if u:
                usage_label = u.label or USAGE_LABELS_FR.get(u.type, u.type.value)
                usage_type = u.type.value

        drift_list.append(
            {
                "insight_id": d.id,
                "type": d.type,
                "severity": d.severity,
                "message": d.message,
                "usage_id": getattr(d, "usage_id", None),
                "usage_label": usage_label,
                "usage_type": usage_type,
                "estimated_loss_kwh": d.estimated_loss_kwh,
                "estimated_loss_eur": d.estimated_loss_eur,
            }
        )

    # Trier par perte EUR decroissante
    drift_list.sort(key=lambda x: x.get("estimated_loss_eur") or 0, reverse=True)

    return {
        "site_id": site_id,
        "readiness": readiness,
        "metering_plan": plan,
        "top_ues": ues,
        "cost_breakdown": cost,
        "active_drifts": drift_list,
        "summary": {
            "total_kwh": cost["total_kwh"],
            "total_eur": cost["total_eur"],
            "readiness_score": readiness["score"],
            "readiness_level": readiness["level"],
            "active_drifts_count": len(drift_list),
            "ues_count": len(ues),
            "sub_meters_count": plan["total_sub_meters"],
        },
    }


# ── Helpers ───────────────────────────────────────────────────────────────


def _resolve_usage(db: Session, meter: Meter) -> Optional[dict]:
    """Resolve usage info from a meter."""
    if not getattr(meter, "usage_id", None):
        return None
    u = db.query(Usage).filter(Usage.id == meter.usage_id).first()
    if not u:
        return None
    return {
        "id": u.id,
        "type": u.type.value,
        "label": u.label or USAGE_LABELS_FR.get(u.type, u.type.value),
        "family": USAGE_FAMILY_MAP.get(u.type, UsageFamily.AUXILIAIRES).value,
    }


def _infer_data_source(db: Session, meter: Meter) -> str:
    """Infere la source de donnee d'un compteur."""
    if getattr(meter, "usage_id", None):
        u = db.query(Usage).filter(Usage.id == meter.usage_id).first()
        if u and u.data_source:
            return u.data_source.value
    # Check last reading
    last_reading = (
        db.query(MeterReading).filter(MeterReading.meter_id == meter.id).order_by(MeterReading.timestamp.desc()).first()
    )
    if last_reading:
        if last_reading.is_estimated:
            return "estimation_prorata"
        if last_reading.import_job_id:
            return "import_csv"
        return "mesure_directe"
    return "inconnu"


def _extract_drift_pct(insight: ConsumptionInsight) -> Optional[float]:
    """Extrait le % de derive depuis les metrics JSON."""
    if not insight.metrics_json:
        return None
    try:
        metrics = json.loads(insight.metrics_json)
        return metrics.get("drift_pct")
    except (json.JSONDecodeError, TypeError):
        return None
