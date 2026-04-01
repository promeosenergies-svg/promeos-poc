"""
PROMEOS — Service Usage V1.2
Readiness Score, Metering Plan, Usage Cost Breakdown, Top UES,
Baseline auto-compute, Compliance par usage, Billing links.

Entite pivot reliant Patrimoine → Usage → Derive → Action → Conformite → Facture → Achat.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func
from services.scope_utils import resolve_site_ids

from models import (
    Site,
    Usage,
    UsageBaseline,
    Meter,
    MeterReading,
    ConsumptionInsight,
    Recommendation,
    USAGE_LABELS_FR,
    USAGE_FAMILY_MAP,
    TypeUsage,
    UsageFamily,
    DataSourceType,
)
from models.energy_models import FrequencyType
from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH


# Seuil UES ISO 50001 §6.3 : usage > 10% conso totale = significatif
UES_THRESHOLD_PCT = 10.0


def _is_ues(usage_kwh: float, total_kwh: float, manual_override: bool = False) -> bool:
    """Usage Energetique Significatif si > 10% conso totale OU override manuel."""
    if manual_override:
        return True
    if total_kwh <= 0 or usage_kwh <= 0:
        return False
    return (usage_kwh / total_kwh) * 100 >= UES_THRESHOLD_PCT


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

    Groupes par TypeUsage (merge multi-batiments).
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

    # Phase 1 : collecter kWh par usage_id + tracker les usage_id mesures
    usage_kwh = {}  # usage_id -> kwh
    usage_objs = {}  # usage_id -> Usage
    measured_usage_ids = set()  # usage_id avec sous-compteur reel

    for s in subs_with_usage:
        kwh = (
            db.query(func.sum(MeterReading.value_kwh))
            .filter(MeterReading.meter_id == s.id, MeterReading.timestamp >= cutoff)
            .scalar()
            or 0
        )
        usage_kwh[s.usage_id] = usage_kwh.get(s.usage_id, 0) + kwh
        measured_usage_ids.add(s.usage_id)
        if s.usage_id not in usage_objs:
            usage_objs[s.usage_id] = db.query(Usage).filter(Usage.id == s.usage_id).first()

    # Types deja couverts par mesure directe (sous-compteur)
    measured_types = set()
    for uid in measured_usage_ids:
        u = usage_objs.get(uid)
        if u:
            measured_types.add(u.type)

    # Fallback: usages declares sans mesure directe
    # Ne pas ajouter de fallback pour un type deja mesure par sous-compteur
    declared_usages = db.query(Usage).join(Usage.batiment).filter(Usage.batiment.has(site_id=site_id)).all()
    for u in declared_usages:
        if u.id not in usage_kwh and u.type not in measured_types:
            if u.pct_of_total and total_kwh > 0:
                usage_kwh[u.id] = total_kwh * u.pct_of_total / 100
                usage_objs[u.id] = u

    # Phase 2 : grouper par TypeUsage (merge multi-batiments)
    _cached_site_surface = _resolve_site_surface(db, site_id)

    by_type = {}  # TypeUsage -> {kwh, surface, usage_ids, has_measured, ...}
    for uid, kwh in usage_kwh.items():
        u = usage_objs.get(uid)
        if not u:
            continue
        t = u.type
        is_measured = uid in measured_usage_ids
        # Surface site (pas batiment proportionnel) pour IPE correct
        _site_surface = _cached_site_surface
        if not _site_surface:
            _site_surface = u.batiment.surface_m2 if u.batiment and u.batiment.surface_m2 else 0
        if t not in by_type:
            by_type[t] = {
                "type": t,
                "label": u.label or USAGE_LABELS_FR.get(t, t.value),
                "family": USAGE_FAMILY_MAP.get(t, UsageFamily.AUXILIAIRES),
                "kwh": 0,
                "surface_m2": 0,
                "is_significant_manual": False,
                "has_measured": False,
                "usage_ids": [],
            }
        row = by_type[t]
        row["kwh"] += kwh
        row["surface_m2"] = max(row["surface_m2"], _site_surface)  # surface site, pas cumul
        row["is_significant_manual"] = row.get("is_significant_manual", False) or u.is_significant
        row["has_measured"] = row["has_measured"] or is_measured
        row["usage_ids"].append(uid)

    # Phase 3 : normaliser si somme > total_kwh (eviter pct > 100)
    raw_sum = sum(v["kwh"] for v in by_type.values())
    if raw_sum > total_kwh and total_kwh > 0:
        ratio = total_kwh / raw_sum
        for v in by_type.values():
            v["kwh"] *= ratio

    sorted_types = sorted(by_type.values(), key=lambda x: x["kwh"], reverse=True)[:limit]

    result = []
    for row in sorted_types:
        # Derives actives pour tous les usage_ids de ce type
        drift_insights = (
            db.query(ConsumptionInsight)
            .filter(
                ConsumptionInsight.site_id == site_id,
                ConsumptionInsight.usage_id.in_(row["usage_ids"]),
                ConsumptionInsight.type == "derive",
            )
            .all()
        )

        kwh = row["kwh"]
        surface = row["surface_m2"]
        data_source = "mesure_directe" if row["has_measured"] else "estimation_prorata"

        result.append(
            {
                "usage_ids": row["usage_ids"],
                "type": row["type"].value,
                "label": row["label"],
                "family": row["family"].value,
                "kwh": round(kwh, 1),
                "pct_of_total": round(kwh / total_kwh * 100, 1) if total_kwh > 0 else 0,
                "is_significant": _is_ues(kwh, total_kwh, row.get("is_significant_manual", False)),
                "data_source": data_source,
                "has_drift": len(drift_insights) > 0,
                "drift_pct": _extract_drift_pct(drift_insights[0]) if drift_insights else None,
                "surface_m2": round(surface, 1) if surface else None,
                "ipe_kwh_m2": round(kwh / surface, 1) if surface and surface > 0 else None,
            }
        )

    return result


# ── Usage Cost Breakdown ─────────────────────────────────────────────────


def get_usage_cost_breakdown(db: Session, site_id: int, days: int = 365) -> dict:
    """Ventile le cout energetique par usage, pro-rata sous-compteur.

    Utilise la meme cascade prix que billing_links :
    contrat actif → moyenne factures 12m → SiteTariffProfile → fallback 0.068.
    """
    price_ref = _resolve_site_price(db, site_id)
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

    # Par usage (sous-compteurs uniquement — exclure les compteurs principaux)
    subs = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active.is_(True),
            Meter.usage_id.isnot(None),
            Meter.parent_meter_id.isnot(None),
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

    # Fallback : usages declares sans sous-compteur, utiliser pct_of_total
    declared_usages = db.query(Usage).join(Usage.batiment).filter(Usage.batiment.has(site_id=site_id)).all()
    for u in declared_usages:
        if u.id not in usage_costs and u.pct_of_total and total_kwh > 0:
            est_kwh = total_kwh * u.pct_of_total / 100
            usage_costs[u.id] = {
                "usage_id": u.id,
                "type": u.type.value,
                "label": u.label or USAGE_LABELS_FR.get(u.type, u.type.value),
                "kwh": est_kwh,
                "eur": est_kwh * price_ref,
            }

    # Plafonner la somme des kWh par usage au total site
    covered_kwh = sum(v["kwh"] for v in usage_costs.values())
    if covered_kwh > total_kwh and total_kwh > 0:
        # Normaliser au pro-rata pour que la somme = total_kwh
        ratio = total_kwh / covered_kwh
        for v in usage_costs.values():
            v["kwh"] *= ratio
            v["eur"] = v["kwh"] * price_ref
        covered_kwh = total_kwh

    uncovered_kwh = max(0, total_kwh - covered_kwh)

    # Grouper par type d'usage (merge multi-batiments)
    by_type = {}
    for v in usage_costs.values():
        t = v["type"]
        if t not in by_type:
            by_type[t] = {"type": t, "label": v["label"], "kwh": 0, "eur": 0}
        by_type[t]["kwh"] += v["kwh"]
        by_type[t]["eur"] += v["eur"]

    items = sorted(by_type.values(), key=lambda x: x["kwh"], reverse=True)
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
    """Endpoint agrege pour la page /usages V1.2.

    Inclut : readiness + plan + UES + derives + cost + baselines + compliance + billing.
    """
    readiness = compute_usage_readiness(db, site_id)
    plan = get_metering_plan(db, site_id)
    ues = get_top_ues(db, site_id)
    cost = get_usage_cost_breakdown(db, site_id)

    # V1.2: baselines, compliance, billing
    baselines = compute_baselines(db, site_id)
    compliance = get_usage_compliance(db, site_id)
    billing = get_usage_billing_links(db, site_id)

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
        "baselines": baselines,
        "compliance": compliance,
        "billing_links": billing,
        "summary": {
            "total_kwh": cost["total_kwh"],
            "total_eur": cost["total_eur"],
            "readiness_score": readiness["score"],
            "readiness_level": readiness["level"],
            "active_drifts_count": len(drift_list),
            "ues_count": len(ues),
            "sub_meters_count": plan["total_sub_meters"],
            "principals_count": plan["total_principals"],
            "measured_ues": sum(1 for u in ues if u.get("data_source") == "mesure_directe"),
            "estimated_ues": sum(1 for u in ues if u.get("data_source") != "mesure_directe"),
            "metering_coverage_pct": round(
                sum(m.get("coverage_pct", 0) for m in plan["meters"]) / max(1, len(plan["meters"])),
                1,
            ),
            "baselines_count": len(baselines),
            "compliance_coverage_pct": compliance["usage_coverage"]["coverage_pct"],
            "contract_active": billing["contract"] is not None,
            "price_source": billing["price_ref"]["source"],
        },
    }


# ── V1.2 — Baseline auto-compute ──────────────────────────────────────────


def compute_baselines(db: Session, site_id: int) -> list[dict]:
    """Auto-calcule les baselines pour les top usages d'un site.

    Logique :
    - Pour chaque usage avec un sous-compteur lie, calcule la conso N-1 vs N actuel.
    - Cree / met a jour UsageBaseline si necessaire.
    - Retourne les baselines avec comparaison avant/apres.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Periodes : baseline = [now-24m, now-12m], actuel = [now-12m, now]
    baseline_start = now - timedelta(days=730)
    baseline_end = now - timedelta(days=365)
    current_start = now - timedelta(days=365)
    current_end = now

    usages = db.query(Usage).join(Usage.batiment).filter(Usage.batiment.has(site_id=site_id)).all()
    results = []

    _cached_site_surface = _resolve_site_surface(db, site_id)

    # Total kWh site (periode actuelle) pour seuil UES dynamique
    principals = (
        db.query(Meter)
        .filter(Meter.site_id == site_id, Meter.is_active.is_(True), Meter.parent_meter_id.is_(None))
        .all()
    )
    _total_site_kwh = sum(
        db.query(func.sum(MeterReading.value_kwh))
        .filter(MeterReading.meter_id == m.id, MeterReading.timestamp >= current_start)
        .scalar()
        or 0
        for m in principals
    )

    # Cible DT 2030 : baseline 2020 × 0.60 (-40%)
    from models.consumption_target import ConsumptionTarget

    dt_baseline_2020 = (
        db.query(ConsumptionTarget)
        .filter(
            ConsumptionTarget.site_id == site_id,
            ConsumptionTarget.year == 2020,
            ConsumptionTarget.period == "yearly",
            ConsumptionTarget.energy_type == "electricity",
        )
        .first()
    )
    dt_target_2030_kwh = (
        dt_baseline_2020.target_kwh * 0.60 if dt_baseline_2020 and dt_baseline_2020.target_kwh else None
    )
    dt_target_2030_kwh_m2 = (
        round(dt_target_2030_kwh / _cached_site_surface, 1) if dt_target_2030_kwh and _cached_site_surface > 0 else None
    )

    for u in usages:
        # Sous-compteurs lies
        meters = db.query(Meter).filter(Meter.usage_id == u.id, Meter.is_active.is_(True)).all()
        meter_ids = [m.id for m in meters]

        # kWh baseline (N-1) depuis readings
        kwh_baseline = 0
        kwh_current = 0
        from_stored = False
        is_estimated = False

        if meter_ids:
            kwh_baseline = (
                db.query(func.sum(MeterReading.value_kwh))
                .filter(
                    MeterReading.meter_id.in_(meter_ids),
                    MeterReading.timestamp >= baseline_start,
                    MeterReading.timestamp < baseline_end,
                )
                .scalar()
                or 0
            )

            # Annualiser la baseline si les readings couvrent moins d'un an
            if kwh_baseline > 0:
                bl_min = (
                    db.query(func.min(MeterReading.timestamp))
                    .filter(
                        MeterReading.meter_id.in_(meter_ids),
                        MeterReading.timestamp >= baseline_start,
                        MeterReading.timestamp < baseline_end,
                    )
                    .scalar()
                )
                bl_max = (
                    db.query(func.max(MeterReading.timestamp))
                    .filter(
                        MeterReading.meter_id.in_(meter_ids),
                        MeterReading.timestamp >= baseline_start,
                        MeterReading.timestamp < baseline_end,
                    )
                    .scalar()
                )
                if bl_min and bl_max:
                    bl_actual_days = max(1, (bl_max - bl_min).days)
                    if bl_actual_days < 350:
                        kwh_baseline = kwh_baseline * 365.0 / bl_actual_days

            kwh_current = (
                db.query(func.sum(MeterReading.value_kwh))
                .filter(
                    MeterReading.meter_id.in_(meter_ids),
                    MeterReading.timestamp >= current_start,
                    MeterReading.timestamp < current_end,
                )
                .scalar()
                or 0
            )

            # Annualiser le current si les readings couvrent moins d'un an
            if kwh_current > 0:
                cur_min = (
                    db.query(func.min(MeterReading.timestamp))
                    .filter(
                        MeterReading.meter_id.in_(meter_ids),
                        MeterReading.timestamp >= current_start,
                        MeterReading.timestamp < current_end,
                    )
                    .scalar()
                )
                cur_max = (
                    db.query(func.max(MeterReading.timestamp))
                    .filter(
                        MeterReading.meter_id.in_(meter_ids),
                        MeterReading.timestamp >= current_start,
                        MeterReading.timestamp < current_end,
                    )
                    .scalar()
                )
                if cur_min and cur_max:
                    cur_actual_days = max(1, (cur_max - cur_min).days)
                    if cur_actual_days < 350:
                        kwh_current = kwh_current * 365.0 / cur_actual_days

        # Fallback : baseline stockee en base (seed ou saisie manuelle)
        if kwh_baseline <= 0:
            stored = (
                db.query(UsageBaseline)
                .filter(UsageBaseline.usage_id == u.id, UsageBaseline.is_active.is_(True))
                .first()
            )
            if stored:
                kwh_baseline = stored.kwh_total
                from_stored = True
                # Estimer variation actuelle (deterministe) si pas de readings
                if kwh_current <= 0 and u.pct_of_total:
                    seed_str = f"{u.id}:{current_end.year}"
                    hash_val = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
                    drift = -0.05 + (hash_val % 1000) / 1000 * 0.10
                    kwh_current = round(kwh_baseline * (1 + drift), 1)
                    is_estimated = True

        if kwh_baseline <= 0 and kwh_current <= 0:
            continue

        # IPE — denominateur = surface du SITE (pas batiment proportionnel)
        site_surface = _cached_site_surface or None
        # Fallback batiment si pas de surface site
        if not site_surface or site_surface <= 0:
            site_surface = u.batiment.surface_m2 if u.batiment and u.batiment.surface_m2 else None
        ipe_baseline = round(kwh_baseline / site_surface, 1) if site_surface and site_surface > 0 else None
        ipe_current = round(kwh_current / site_surface, 1) if site_surface and site_surface > 0 else None

        # Ecart
        ecart_kwh = kwh_current - kwh_baseline if kwh_baseline > 0 else None
        ecart_pct = round((kwh_current - kwh_baseline) / kwh_baseline * 100, 1) if kwh_baseline > 0 else None

        # Tendance
        if ecart_pct is None:
            trend = "indeterminate"
        elif ecart_pct <= -5:
            trend = "amelioration"
        elif ecart_pct >= 5:
            trend = "degradation"
        else:
            trend = "stable"

        # Upsert baseline en base si donnees suffisantes
        if kwh_baseline > 0:
            existing = (
                db.query(UsageBaseline)
                .filter(UsageBaseline.usage_id == u.id, UsageBaseline.is_active.is_(True))
                .first()
            )
            if not existing:
                bl = UsageBaseline(
                    usage_id=u.id,
                    period_start=baseline_start,
                    period_end=baseline_end,
                    kwh_total=round(kwh_baseline, 1),
                    kwh_m2_year=ipe_baseline,
                    data_source=DataSourceType.MESURE_DIRECTE,
                    confidence=0.8 if kwh_baseline > 1000 else 0.5,
                    is_active=True,
                )
                db.add(bl)

        # Actions liees (avant/apres)
        actions = (
            db.query(Recommendation).filter(Recommendation.usage_id == u.id, Recommendation.status == "completed").all()
        )

        results.append(
            {
                "usage_id": u.id,
                "type": u.type.value,
                "label": u.label or USAGE_LABELS_FR.get(u.type, u.type.value),
                "family": USAGE_FAMILY_MAP.get(u.type, UsageFamily.AUXILIAIRES).value,
                "kwh_baseline": round(kwh_baseline, 1),
                "kwh_current": round(kwh_current, 1),
                "ipe_baseline": ipe_baseline,
                "ipe_current": ipe_current,
                "ecart_kwh": round(ecart_kwh, 1) if ecart_kwh is not None else None,
                "ecart_pct": ecart_pct,
                "trend": trend,
                "surface_m2": site_surface,
                "is_significant": _is_ues(kwh_current, _total_site_kwh, u.is_significant),
                "data_source": "estimation_deterministe"
                if is_estimated
                else (
                    "mesure_directe"
                    if meter_ids and not from_stored
                    else ("baseline_stockee" if from_stored else "estimation_prorata")
                ),
                "actions_completed": len(actions),
                "dt_target_kwh_m2": dt_target_2030_kwh_m2,
                "dt_gap_pct": None,  # DT compliance = site-level, pas per-usage
            }
        )

    db.flush()
    return results


# ── V1.2 — Compliance par usage ──────────────────────────────────────────


def get_usage_compliance(db: Session, site_id: int) -> dict:
    """Widget conformite par usage — relie BACS, Tertiaire, findings au niveau usage.

    Retourne les systemes CVC lies aux usages, leur statut BACS,
    et un resume de couverture conformite.
    """
    from models.bacs_models import BacsCvcSystem, BacsAssessment, BacsAsset

    usages = db.query(Usage).join(Usage.batiment).filter(Usage.batiment.has(site_id=site_id)).all()
    usage_map = {u.id: u for u in usages}

    # BACS CVC systems lies aux usages
    cvc_systems = db.query(BacsCvcSystem).join(BacsAsset).filter(BacsAsset.site_id == site_id).all()

    # Assessment BACS du site
    assessment = (
        db.query(BacsAssessment)
        .join(BacsAsset)
        .filter(BacsAsset.site_id == site_id)
        .order_by(BacsAssessment.created_at.desc())
        .first()
    )

    # Usages avec couverture BACS
    covered_usage_ids = set()
    systems_by_usage = {}
    for sys in cvc_systems:
        uid = getattr(sys, "usage_id", None)
        if uid and uid in usage_map:
            covered_usage_ids.add(uid)
            if uid not in systems_by_usage:
                systems_by_usage[uid] = []
            systems_by_usage[uid].append(
                {
                    "system_type": sys.system_type.value if sys.system_type else None,
                    "putile_kw": sys.putile_kw_computed,
                }
            )

    # Construire items par usage, dedupliques par TypeUsage
    # (un site avec N batiments peut avoir le meme type d'usage N fois)
    merged = {}  # TypeUsage -> dict
    for u in usages:
        has_bacs = u.id in covered_usage_ids
        is_thermal = u.type in (
            TypeUsage.CHAUFFAGE,
            TypeUsage.CLIMATISATION,
            TypeUsage.VENTILATION,
            TypeUsage.ECS,
        )
        if u.type not in merged:
            merged[u.type] = {
                "usage_ids": [u.id],
                "type": u.type.value,
                "label": u.label or USAGE_LABELS_FR.get(u.type, u.type.value),
                "is_significant": u.is_significant,
                "bacs_covered": has_bacs,
                "bacs_systems": list(systems_by_usage.get(u.id, [])),
                "concerned_by_bacs": is_thermal,
                "concerned_by_dt": u.is_significant,  # UES = concerne par DT
                "concerned_by_iso50001": u.is_significant,
            }
        else:
            row = merged[u.type]
            row["usage_ids"].append(u.id)
            # OR logic: if ANY usage of that type has coverage/significance, show it
            row["is_significant"] = row["is_significant"] or u.is_significant
            row["bacs_covered"] = row["bacs_covered"] or has_bacs
            row["bacs_systems"].extend(systems_by_usage.get(u.id, []))
            row["concerned_by_bacs"] = row["concerned_by_bacs"] or is_thermal
            row["concerned_by_dt"] = row["concerned_by_dt"] or u.is_significant
            row["concerned_by_iso50001"] = row["concerned_by_iso50001"] or u.is_significant
            # Prefer explicit label over default
            if u.label:
                row["label"] = u.label

    items = list(merged.values())

    # Compteurs
    total_concerned = sum(1 for it in items if it["concerned_by_bacs"])
    total_covered = sum(1 for it in items if it["bacs_covered"])

    return {
        "site_id": site_id,
        "bacs_score": assessment.compliance_score if assessment else None,
        "bacs_is_obligated": assessment.is_obligated if assessment else None,
        "bacs_deadline": assessment.deadline_date.isoformat() if assessment and assessment.deadline_date else None,
        "usage_coverage": {
            "total_usages": len(usages),
            "bacs_concerned": total_concerned,
            "bacs_covered": total_covered,
            "coverage_pct": round(total_covered / max(1, total_concerned) * 100, 1),
        },
        "items": items,
        "top_risk": _find_top_compliance_risk(items),
    }


def _find_top_compliance_risk(items: list) -> Optional[str]:
    """Identifie le principal risque conformite."""
    uncovered_thermal = [it for it in items if it["concerned_by_bacs"] and not it["bacs_covered"]]
    if uncovered_thermal:
        labels = ", ".join(it["label"] for it in uncovered_thermal[:3])
        return f"Usages thermiques sans couverture BACS : {labels}"
    uncovered_ues = [it for it in items if it["concerned_by_dt"] and not it["bacs_covered"]]
    if uncovered_ues:
        return f"{len(uncovered_ues)} UES non couverts par un systeme de management"
    return None


# ── V1.2 — Billing links ────────────────────────────────────────────────


def get_usage_billing_links(db: Session, site_id: int) -> dict:
    """Liens usage → facture → contrat → achat.

    Retourne le contrat actif, le prix de reference, les factures recentes,
    et le lien vers achat/scenario.
    """
    from models.billing_models import EnergyContract, EnergyInvoice

    # Contrat actif
    contract = (
        db.query(EnergyContract)
        .filter(EnergyContract.site_id == site_id, EnergyContract.contract_status == "active")
        .first()
    )

    # Factures recentes (12 derniers mois)
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=365)
    invoices = (
        db.query(EnergyInvoice)
        .filter(EnergyInvoice.site_id == site_id, EnergyInvoice.period_start >= cutoff)
        .order_by(EnergyInvoice.period_start.desc())
        .limit(12)
        .all()
    )

    total_invoiced_eur = sum(inv.total_eur or 0 for inv in invoices)
    total_invoiced_kwh = sum(inv.energy_kwh or 0 for inv in invoices)
    avg_price = round(total_invoiced_eur / total_invoiced_kwh, 4) if total_invoiced_kwh > 0 else None

    # Source du prix
    if contract and getattr(contract, "price_ref_eur_per_kwh", None):
        price_source = "contrat"
        price_eur_kwh = contract.price_ref_eur_per_kwh
    elif avg_price:
        price_source = "facture"
        price_eur_kwh = avg_price
    else:
        price_source = "defaut"
        price_eur_kwh = DEFAULT_PRICE_ELEC_EUR_KWH

    return {
        "site_id": site_id,
        "contract": (
            {
                "id": contract.id,
                "supplier": contract.supplier_name,
                "energy_type": contract.energy_type.value if contract.energy_type else "elec",
                "start_date": contract.start_date.isoformat() if contract.start_date else None,
                "end_date": contract.end_date.isoformat() if contract.end_date else None,
                "status": contract.contract_status.value if contract.contract_status else None,
                "price_ref_eur_kwh": contract.price_ref_eur_per_kwh,
                "tariff_option": contract.tariff_option.value if contract.tariff_option else None,
            }
            if contract
            else None
        ),
        "invoices_summary": {
            "count": len(invoices),
            "total_eur": round(total_invoiced_eur, 0),
            "total_kwh": round(total_invoiced_kwh, 0),
            "avg_price_eur_kwh": avg_price,
        },
        "price_ref": {
            "value": price_eur_kwh,
            "source": price_source,  # "contrat" | "facture" | "defaut"
        },
        "links": {
            "bill_intel": "/bill-intel",
            "billing": "/billing",
            "purchase": "/achat-energie",
            "contract_radar": "/contrats-radar",
        },
    }


# ── V2 — Timeline mensuelle par usage ───────────────────────────────────


def get_usage_timeline(db: Session, site_id: int, months: int = 12) -> dict:
    """Consommation mensuelle par usage pour AreaChart empile."""
    from sqlalchemy import extract

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff = now - timedelta(days=months * 31)
    cutoff_prev = cutoff - timedelta(days=365)

    site_surface = _resolve_site_surface(db, site_id)

    # Sous-compteurs avec usage
    subs = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active.is_(True),
            Meter.parent_meter_id.isnot(None),
            Meter.usage_id.isnot(None),
        )
        .all()
    )
    # Principal(s)
    principals = (
        db.query(Meter)
        .filter(Meter.site_id == site_id, Meter.is_active.is_(True), Meter.parent_meter_id.is_(None))
        .all()
    )
    principal_ids = [m.id for m in principals]

    # Conso mensuelle du principal
    principal_monthly = {}
    if principal_ids:
        rows = (
            db.query(
                extract("year", MeterReading.timestamp).label("yr"),
                extract("month", MeterReading.timestamp).label("mo"),
                func.sum(MeterReading.value_kwh),
            )
            .filter(MeterReading.meter_id.in_(principal_ids), MeterReading.timestamp >= cutoff)
            .group_by("yr", "mo")
            .all()
        )
        for yr, mo, kwh in rows:
            principal_monthly[(int(yr), int(mo))] = kwh or 0

    # Baseline N-1 (principal)
    baseline_monthly = {}
    if principal_ids:
        rows = (
            db.query(
                extract("year", MeterReading.timestamp).label("yr"),
                extract("month", MeterReading.timestamp).label("mo"),
                func.sum(MeterReading.value_kwh),
            )
            .filter(
                MeterReading.meter_id.in_(principal_ids),
                MeterReading.timestamp >= cutoff_prev,
                MeterReading.timestamp < cutoff,
            )
            .group_by("yr", "mo")
            .all()
        )
        for yr, mo, kwh in rows:
            baseline_monthly[(int(yr), int(mo))] = kwh or 0

    # Conso mensuelle par sous-compteur
    # Batch load usages to avoid N+1
    _usage_ids = list({s.usage_id for s in subs if s.usage_id})
    _usage_map = {u.id: u for u in db.query(Usage).filter(Usage.id.in_(_usage_ids)).all()} if _usage_ids else {}

    usage_monthly = {}  # usage_label -> {(yr, mo): kwh}
    for s in subs:
        u = _usage_map.get(s.usage_id)
        label = (u.label or USAGE_LABELS_FR.get(u.type, u.type.value)) if u else f"Compteur {s.id}"
        if label not in usage_monthly:
            usage_monthly[label] = {}
        rows = (
            db.query(
                extract("year", MeterReading.timestamp).label("yr"),
                extract("month", MeterReading.timestamp).label("mo"),
                func.sum(MeterReading.value_kwh),
            )
            .filter(MeterReading.meter_id == s.id, MeterReading.timestamp >= cutoff)
            .group_by("yr", "mo")
            .all()
        )
        for yr, mo, kwh in rows:
            key = (int(yr), int(mo))
            usage_monthly[label][key] = usage_monthly[label].get(key, 0) + (kwh or 0)

    # Construire les mois ordonnés
    all_keys = sorted(principal_monthly.keys())
    month_labels = [f"{yr}-{mo:02d}" for yr, mo in all_keys]

    # Séries
    series = []
    usage_colors = {
        "Chauffage": "#E57373",
        "Climatisation": "#64B5F6",
        "Éclairage": "#FFD54F",
        "IT & Bureautique": "#7986CB",
        "Ventilation": "#81C784",
        "CVC": "#E57373",
        "Process": "#FF8A65",
        "Cuisine": "#FFAB91",
        "Parties communes": "#A5D6A7",
    }
    for label, monthly in usage_monthly.items():
        series.append(
            {
                "usage": label,
                "color": usage_colors.get(label, "#BDBDBD"),
                "data": [round(monthly.get(k, 0), 0) for k in all_keys],
            }
        )

    # Non affecté
    non_affecte = []
    for k in all_keys:
        total_sub = sum(monthly.get(k, 0) for monthly in usage_monthly.values())
        non_affecte.append(round(max(0, principal_monthly.get(k, 0) - total_sub), 0))
    if any(v > 0 for v in non_affecte):
        series.append({"usage": "Non affecté", "color": "#E0E0E0", "data": non_affecte})

    return {
        "months": month_labels,
        "series": series,
        "total": [round(principal_monthly.get(k, 0), 0) for k in all_keys],
        "baseline_total": [round(baseline_monthly.get((k[0] - 1, k[1]), 0), 0) for k in all_keys],
    }


# Refs ADEME — source unique : config/ademe_benchmarks.py
from config.ademe_benchmarks import BENCHMARK_BY_USAGE as _ADEME_REF_BY_USAGE


# ── V2 — Comparaison inter-sites ───────────────────────────────────────


def get_portfolio_usage_comparison(db: Session, org_id: int) -> dict:
    """Compare les IPE par usage pour tous les sites d'une organisation."""
    from models.site import Site as SiteModel
    from models.portefeuille import Portefeuille
    from models.entite_juridique import EntiteJuridique

    sites = (
        db.query(SiteModel)
        .join(Portefeuille, SiteModel.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    )
    if len(sites) < 2:
        return {"usages": [], "sites": []}

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=365)
    all_usage_labels = set()
    site_results = []

    for s in sites:
        surface = getattr(s, "surface_m2", 0) or getattr(s, "tertiaire_area_m2", 0) or 0
        if surface <= 0:
            continue

        # Total site kWh
        principal_ids = [
            m.id
            for m in db.query(Meter)
            .filter(Meter.site_id == s.id, Meter.is_active.is_(True), Meter.parent_meter_id.is_(None))
            .all()
        ]
        total_kwh = (
            sum(
                db.query(func.sum(MeterReading.value_kwh))
                .filter(MeterReading.meter_id == mid, MeterReading.timestamp >= cutoff)
                .scalar()
                or 0
                for mid in principal_ids
            )
            if principal_ids
            else 0
        )

        # IPE par usage
        usages = db.query(Usage).join(Usage.batiment).filter(Usage.batiment.has(site_id=s.id)).all()
        ipe_by_usage = {}
        for u in usages:
            label = u.label or USAGE_LABELS_FR.get(u.type, u.type.value)
            meters = db.query(Meter).filter(Meter.usage_id == u.id, Meter.is_active.is_(True)).all()
            kwh = (
                sum(
                    db.query(func.sum(MeterReading.value_kwh))
                    .filter(MeterReading.meter_id == m.id, MeterReading.timestamp >= cutoff)
                    .scalar()
                    or 0
                    for m in meters
                )
                if meters
                else (total_kwh * (u.pct_of_total or 0) / 100 if u.pct_of_total else 0)
            )
            ipe_by_usage[label] = round(kwh / surface, 1) if surface > 0 else 0
            all_usage_labels.add(label)

        type_site = getattr(s, "type_site", "bureau") or "bureau"
        benchmarks = {"bureau": 170, "hotel": 280, "enseignement": 110, "entrepot": 120, "commerce": 200}

        site_results.append(
            {
                "site_id": s.id,
                "site_name": s.nom,
                "surface_m2": surface,
                "ipe_by_usage": ipe_by_usage,
                "ipe_total": round(total_kwh / surface, 1) if surface > 0 else 0,
                "benchmark_ademe": benchmarks.get(type_site, 170),
            }
        )

    site_results.sort(key=lambda x: x["ipe_total"], reverse=True)

    return {
        "usages": sorted(all_usage_labels),
        "sites": site_results,
        "ademe_ref_by_usage": _ADEME_REF_BY_USAGE,
    }


# ── V2 — Meter readings preview ────────────────────────────────────────


def get_meter_readings_preview(db: Session, meter_id: int, days: int = 7) -> dict:
    """Relevés récents d'un compteur pour mini-graphe inline."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    readings = (
        db.query(MeterReading)
        .filter(MeterReading.meter_id == meter_id, MeterReading.timestamp >= cutoff)
        .order_by(MeterReading.timestamp)
        .all()
    )
    total = sum(r.value_kwh or 0 for r in readings)
    # Agréger par heure pour réduire le volume
    hourly = {}
    for r in readings:
        key = r.timestamp.replace(minute=0, second=0, microsecond=0).isoformat()
        hourly[key] = hourly.get(key, 0) + (r.value_kwh or 0)

    return {
        "meter_id": meter_id,
        "readings": [{"ts": ts, "kwh": round(kwh, 2)} for ts, kwh in sorted(hourly.items())],
        "total_kwh": round(total, 1),
    }


# ── Helpers ───────────────────────────────────────────────────────────────


def _resolve_site_surface(db: Session, site_id: int) -> float:
    """Retourne la surface du site (surface_m2 ou tertiaire_area_m2), 0 si absent."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return 0
    return getattr(site, "surface_m2", 0) or getattr(site, "tertiaire_area_m2", 0) or 0


def _resolve_site_price(db: Session, site_id: int) -> float:
    """Cascade unique de resolution du prix pour un site.

    Meme logique que billing_links pour garantir la coherence :
    1. Contrat actif (price_ref_eur_per_kwh)
    2. Moyenne factures 12 derniers mois
    3. SiteTariffProfile
    4. Fallback DEFAULT_PRICE_ELEC_EUR_KWH (0.068)
    """
    from models.billing_models import EnergyContract, EnergyInvoice

    # 1. Contrat actif
    contract = (
        db.query(EnergyContract)
        .filter(EnergyContract.site_id == site_id, EnergyContract.contract_status == "active")
        .first()
    )
    if contract and getattr(contract, "price_ref_eur_per_kwh", None):
        return contract.price_ref_eur_per_kwh

    # 2. Moyenne factures 12m
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=365)
    invoices = (
        db.query(EnergyInvoice)
        .filter(EnergyInvoice.site_id == site_id, EnergyInvoice.period_start >= cutoff)
        .order_by(EnergyInvoice.period_start.desc())
        .limit(12)
        .all()
    )
    total_eur = sum(inv.total_eur or 0 for inv in invoices)
    total_kwh = sum(inv.energy_kwh or 0 for inv in invoices)
    if total_kwh > 0:
        return round(total_eur / total_kwh, 4)

    # 3. SiteTariffProfile (inclut son propre fallback vers DEFAULT)
    from routes.site_config import get_site_price_ref

    return get_site_price_ref(db, site_id)


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


# ── V3 — Scoped dashboard & timeline (multi-niveaux) ────────────────────


def get_scoped_usages_dashboard(
    db: Session,
    org_id: int,
    entity_id: int = None,
    portefeuille_id: int = None,
    site_id: int = None,
    archetype_code: str = None,
) -> dict:
    """Dashboard usages adaptatif au scope, filtrable par archétype."""
    from models.site import Site as SiteModel

    site_ids = resolve_site_ids(
        db,
        org_id,
        entity_id=entity_id,
        portefeuille_id=portefeuille_id,
        site_id=site_id,
        archetype_code=archetype_code,
    )
    if not site_ids:
        return {"scope_level": "empty", "sites_count": 0, "summary": {"total_kwh": 0, "total_eur": 0}}

    # Mono-site : délègue à l'existant
    if len(site_ids) == 1:
        result = get_usages_dashboard(db, site_ids[0])
        result["scope_level"] = "site"
        result["sites_count"] = 1
        return result

    # Multi-sites : agrégation
    scope_level = "entite" if entity_id else ("portfolio" if portefeuille_id else "org")

    # Batch-fetch all site objects once
    site_objs = {s.id: s for s in db.query(SiteModel).filter(SiteModel.id.in_(site_ids)).all()}

    sites_data = []
    for sid in site_ids:
        try:
            d = get_usages_dashboard(db, sid)
            sites_data.append((sid, d))
        except Exception:
            continue

    if not sites_data:
        return {"scope_level": scope_level, "sites_count": 0, "summary": {"total_kwh": 0, "total_eur": 0}}

    # Aggregate summary
    total_kwh = sum(d["summary"]["total_kwh"] for _, d in sites_data)
    total_eur = sum(d["summary"]["total_eur"] for _, d in sites_data)
    total_surface = sum(getattr(site_objs.get(sid), "surface_m2", 0) or 0 for sid, _ in sites_data)
    ipe = round(total_kwh / total_surface, 1) if total_surface > 0 else 0

    # Aggregate baselines by label
    baselines_map = {}
    for _, d in sites_data:
        for b in d.get("baselines") or []:
            label = b.get("label", "?")
            if label not in baselines_map:
                baselines_map[label] = {
                    "label": label,
                    "kwh_baseline": 0,
                    "kwh_current": 0,
                    "is_significant": False,
                    "data_source": b.get("data_source"),
                    "dt_target_kwh_m2": b.get("dt_target_kwh_m2"),
                }
            baselines_map[label]["kwh_baseline"] += b.get("kwh_baseline") or 0
            baselines_map[label]["kwh_current"] += b.get("kwh_current") or 0
            if b.get("is_significant"):
                baselines_map[label]["is_significant"] = True

    aggregated_baselines = []
    for label, bl in baselines_map.items():
        ecart = bl["kwh_current"] - bl["kwh_baseline"]
        pct = round(ecart / bl["kwh_baseline"] * 100, 1) if bl["kwh_baseline"] > 0 else 0
        trend = "degradation" if ecart > 0 else ("amelioration" if ecart < 0 else "stable")
        ipe_current = round(bl["kwh_current"] / total_surface, 1) if total_surface > 0 else 0
        aggregated_baselines.append(
            {
                **bl,
                "ecart_kwh": round(ecart),
                "ecart_pct": pct,
                "trend": trend,
                "ipe_current": ipe_current,
            }
        )
    aggregated_baselines.sort(key=lambda x: abs(x.get("ecart_kwh", 0)), reverse=True)

    # Aggregate cost breakdown
    cost_map = {}
    total_price_weighted = 0
    for _, d in sites_data:
        cb = d.get("cost_breakdown") or {}
        site_kwh = cb.get("total_kwh", 0)
        price_ref = cb.get("price_ref_eur_kwh", 0)
        total_price_weighted += price_ref * site_kwh
        for item in cb.get("by_usage") or []:
            label = item.get("label", "?")
            if label not in cost_map:
                cost_map[label] = {"label": label, "type": item.get("type", ""), "kwh": 0, "eur": 0}
            cost_map[label]["kwh"] += item.get("kwh", 0)
            cost_map[label]["eur"] += item.get("eur", 0)

    cost_items = sorted(cost_map.values(), key=lambda x: x["kwh"], reverse=True)
    for item in cost_items:
        item["kwh"] = round(item["kwh"], 1)
        item["eur"] = round(item["eur"], 0)
        item["pct_of_total"] = round(item["kwh"] / total_kwh * 100, 1) if total_kwh > 0 else 0

    avg_price = total_price_weighted / total_kwh if total_kwh > 0 else 0

    # Aggregate top UES
    ues_map = {}
    for _, d in sites_data:
        for u in d.get("top_ues") or []:
            label = u.get("label", "?")
            if label not in ues_map:
                ues_map[label] = {
                    "label": label,
                    "type": u.get("type", ""),
                    "kwh": 0,
                    "is_significant": False,
                    "data_source": u.get("data_source"),
                }
            ues_map[label]["kwh"] += u.get("kwh", 0)
            if u.get("is_significant"):
                ues_map[label]["is_significant"] = True
    ues_list = sorted(ues_map.values(), key=lambda x: x["kwh"], reverse=True)
    for u in ues_list:
        u["kwh"] = round(u["kwh"], 1)
        u["pct_of_total"] = round(u["kwh"] / total_kwh * 100, 1) if total_kwh > 0 else 0
        u["ipe_kwh_m2"] = round(u["kwh"] / total_surface, 1) if total_surface > 0 else 0

    # Per-site summary
    per_site = []
    for sid, d in sites_data:
        s = site_objs.get(sid)
        per_site.append(
            {
                "site_id": sid,
                "site_name": s.nom if s else "?",
                "total_kwh": round(d["summary"]["total_kwh"]),
                "total_eur": round(d["summary"]["total_eur"]),
                "ipe": round(d["summary"]["total_kwh"] / (s.surface_m2 or 1), 1) if s else 0,
            }
        )

    surplus_kwh = sum(b["ecart_kwh"] for b in aggregated_baselines if b.get("ecart_kwh", 0) > 0)
    degrading = sum(1 for b in aggregated_baselines if b.get("trend") == "degradation")

    return {
        "scope_level": scope_level,
        "sites_count": len(sites_data),
        "site_id": None,
        "readiness": None,
        "metering_plan": None,
        "compliance": None,
        "billing_links": {"price_ref": {"value": avg_price, "source": "moyenne_sites"}},
        "top_ues": ues_list,
        "cost_breakdown": {
            "total_kwh": round(total_kwh, 1),
            "total_eur": round(total_eur, 0),
            "price_ref_eur_kwh": round(avg_price, 4),
            "by_usage": cost_items,
        },
        "active_drifts": [],
        "baselines": aggregated_baselines,
        "summary": {
            "total_kwh": round(total_kwh, 1),
            "total_eur": round(total_eur, 0),
            "total_surface_m2": round(total_surface),
            "ipe_kwh_m2": ipe,
            "readiness_score": None,
            "readiness_level": None,
            "active_drifts_count": 0,
            "ues_count": len(ues_list),
            "sub_meters_count": 0,
            "principals_count": 0,
            "baselines_count": len(aggregated_baselines),
            "surplus_kwh": round(surplus_kwh),
            "surplus_eur": round(surplus_kwh * avg_price),
            "sites_degrading": degrading,
        },
        "per_site_summary": per_site,
    }


def get_scoped_usage_timeline(
    db: Session,
    org_id: int,
    entity_id: int = None,
    portefeuille_id: int = None,
    site_id: int = None,
    archetype_code: str = None,
    months: int = 12,
) -> dict:
    """Timeline usages agrégée par scope, filtrable par archétype."""
    site_ids = resolve_site_ids(
        db,
        org_id,
        entity_id=entity_id,
        portefeuille_id=portefeuille_id,
        site_id=site_id,
        archetype_code=archetype_code,
    )
    if not site_ids:
        return {"months": [], "series": []}

    if len(site_ids) == 1:
        return get_usage_timeline(db, site_ids[0], months)

    # Merge timelines across sites
    all_timelines = []
    for sid in site_ids:
        try:
            t = get_usage_timeline(db, sid, months)
            if t and t.get("months"):
                all_timelines.append(t)
        except Exception:
            continue

    if not all_timelines:
        return {"months": [], "series": []}

    # Build union of all month labels (preserves order from longest timeline)
    ref = max(all_timelines, key=lambda t: len(t["months"]))
    seen = set(ref["months"])
    month_labels = list(ref["months"])
    for t in all_timelines:
        for m in t["months"]:
            if m not in seen:
                month_labels.append(m)
                seen.add(m)
    n = len(month_labels)
    month_index = {m: i for i, m in enumerate(month_labels)}

    # Merge series by usage label
    series_map = {}
    for t in all_timelines:
        t_months = t["months"]
        for s in t.get("series", []):
            label = s["usage"]
            if label not in series_map:
                series_map[label] = {"usage": label, "color": s.get("color", "#BDBDBD"), "data": [0] * n}
            for i, m in enumerate(t_months):
                if m in month_index:
                    val = s["data"][i] if i < len(s["data"]) else 0
                    series_map[label]["data"][month_index[m]] += val

    series = sorted(series_map.values(), key=lambda x: sum(x["data"]), reverse=True)
    for s in series:
        s["data"] = [round(v) for v in s["data"]]

    return {"months": month_labels, "series": series}
