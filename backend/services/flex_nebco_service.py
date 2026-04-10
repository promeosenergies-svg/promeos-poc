"""
PROMEOS — NEBCO eligibility + BACS↔Flex ROI.
Enrichit flex_assessment avec scoring NEBCO et lien BACS.

NEBCO : ≥ 100 kW pilotable agrégé → éligible.
Revenus : 80-200 €/kW/an (NEBCO) + 45 €/kW/an (capacité 2026).
BACS↔Flex : coût GTB 15-30k€/site → revenu NEBCO → ROI mois.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.energy_models import Meter, MeterReading, FrequencyType
from models.usage import Usage
from models.enums import USAGE_LABELS_FR
from services.flex_assessment_service import compute_flex_assessment

# Seuils et prix
NEBCO_MIN_KW = 100
NEBCO_REVENUE_LOW = 80  # €/kW/an conservateur
NEBCO_REVENUE_HIGH = 200  # €/kW/an optimiste
CAPACITY_REVENUE = 45  # €/kW/an mécanisme capacité 2026
BACS_COST_PER_SITE = 25_000  # coût moyen GTB classe C

# Conversion kWh → kW selon fréquence : énergie ÷ durée_heures
# Pour DAILY/MONTHLY, on applique un ratio peak/average de 2.5 (tertiaire typique)
# car max(kWh_période) ÷ heures = puissance moyenne, pas pic
PEAK_TO_AVG_RATIO = 2.5
FREQ_TO_KW_MULTIPLIER = {
    FrequencyType.MIN_15: 4,  # 0.25h — pic réel
    FrequencyType.MIN_30: 2,  # 0.5h — pic réel
    FrequencyType.HOURLY: 1,  # 1h — pic réel
    FrequencyType.DAILY: (1 / 24) * PEAK_TO_AVG_RATIO,  # 24h — estimé
    FrequencyType.MONTHLY: (1 / 730) * PEAK_TO_AVG_RATIO,  # ~730h — estimé
}

# Pilotabilité par type d'usage (shiftable_pct du kW max)
FLEX_BY_USAGE = {
    "Chauffage": {"shiftable_pct": 0.60, "pilotability": "haute", "inertia_min": 45, "requires_gtb": True},
    "CVC": {"shiftable_pct": 0.60, "pilotability": "haute", "inertia_min": 45, "requires_gtb": True},
    "Climatisation": {"shiftable_pct": 0.55, "pilotability": "haute", "inertia_min": 20, "requires_gtb": True},
    "ECS": {"shiftable_pct": 0.90, "pilotability": "haute", "inertia_min": 180, "requires_gtb": False},
    "Ventilation": {"shiftable_pct": 0.40, "pilotability": "moyenne", "inertia_min": 15, "requires_gtb": True},
    "Éclairage": {"shiftable_pct": 0.30, "pilotability": "moyenne", "inertia_min": 0, "requires_gtb": False},
    "IT & Bureautique": {"shiftable_pct": 0.05, "pilotability": "faible", "inertia_min": 0, "requires_gtb": False},
    "Process": {"shiftable_pct": 0.15, "pilotability": "variable", "inertia_min": 0, "requires_gtb": False},
    "Cuisine": {"shiftable_pct": 0.10, "pilotability": "faible", "inertia_min": 0, "requires_gtb": False},
}

DEFAULT_FLEX_PROFILE = {"shiftable_pct": 0.10, "pilotability": "faible", "inertia_min": 0, "requires_gtb": False}


def compute_flex_nebco(db: Session, site_id: int) -> dict:
    """Scoring flex NEBCO + lien BACS pour un site."""
    from models.site import Site as SiteModel
    from datetime import datetime, timedelta, timezone

    site = db.query(SiteModel).filter(SiteModel.id == site_id).first()
    if not site:
        return {"site_id": site_id, "error": "site_not_found"}

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=365)

    # Récupérer flex_assessment existant (pour le score global)
    base_assessment = compute_flex_assessment(db, site_id)

    # Calculer kW par sous-compteur/usage
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

    by_usage = []
    total_pilotable_kw = 0
    kw_needing_gtb = 0
    usages_needing_gtb = []

    for sub in subs:
        usage = db.query(Usage).filter(Usage.id == sub.usage_id).first()
        label = (usage.label or USAGE_LABELS_FR.get(usage.type, usage.type.value)) if usage else "?"

        # kW max = max(kWh_reading) × multiplier selon fréquence du relevé max
        max_row = (
            db.query(MeterReading.value_kwh, MeterReading.frequency)
            .filter(MeterReading.meter_id == sub.id, MeterReading.timestamp >= cutoff)
            .order_by(MeterReading.value_kwh.desc())
            .limit(1)
            .first()
        )
        max_kwh = max_row.value_kwh if max_row else 0
        freq = max_row.frequency if max_row else None
        max_kw = max_kwh * FREQ_TO_KW_MULTIPLIER.get(freq, 1)

        profile = FLEX_BY_USAGE.get(label, DEFAULT_FLEX_PROFILE)
        kw_pilotable = round(max_kw * profile["shiftable_pct"], 1)
        total_pilotable_kw += kw_pilotable

        # BACS status from compliance
        bacs_status = "Non concerné"
        if profile["requires_gtb"]:
            bacs_status = "Manquant"  # default
            kw_needing_gtb += kw_pilotable
            if label not in usages_needing_gtb:
                usages_needing_gtb.append(label)

        by_usage.append(
            {
                "usage": label,
                "max_kw": round(max_kw, 1),
                "shiftable_pct": round(profile["shiftable_pct"] * 100),
                "kw_pilotable": kw_pilotable,
                "inertia_minutes": profile["inertia_min"],
                "pilotability": profile["pilotability"],
                "requires_gtb": profile["requires_gtb"],
                "bacs_status": bacs_status,
            }
        )

    by_usage.sort(key=lambda u: u["kw_pilotable"], reverse=True)
    total_pilotable_kw = round(total_pilotable_kw, 1)

    # NEBCO eligibility
    nebco_eligible = total_pilotable_kw >= NEBCO_MIN_KW

    # Revenue estimation
    revenue = {
        "nebco_low": round(total_pilotable_kw * NEBCO_REVENUE_LOW),
        "nebco_high": round(total_pilotable_kw * NEBCO_REVENUE_HIGH),
        "capacity": round(total_pilotable_kw * CAPACITY_REVENUE),
    }

    flex_revenue_mid = round(kw_needing_gtb * (NEBCO_REVENUE_LOW + NEBCO_REVENUE_HIGH) / 2)
    roi_months = round(BACS_COST_PER_SITE / max(flex_revenue_mid / 12, 1)) if flex_revenue_mid > 0 else 0

    bacs_flex_link = {
        "usages_needing_gtb": usages_needing_gtb,
        "kw_unlocked_by_bacs": round(kw_needing_gtb, 1),
        "bacs_cost_estimate_eur": BACS_COST_PER_SITE,
        "flex_revenue_unlocked_eur_year": flex_revenue_mid,
        "roi_months": roi_months,
        "verdict": (
            f"Mise en conformité BACS débloque {round(kw_needing_gtb)} kW flex → ROI {roi_months} mois"
            if kw_needing_gtb > 0
            else "Aucun usage nécessitant GTB"
        ),
    }

    # Go/No-Go checklist
    has_12m = (
        db.query(func.count(MeterReading.id))
        .join(Meter)
        .filter(Meter.site_id == site_id, Meter.parent_meter_id.is_(None), MeterReading.timestamp >= cutoff)
        .scalar()
        or 0
    ) > 365 * 24  # au moins 1 reading/h sur 12 mois

    go_nogo = {
        "puissance_100kw": total_pilotable_kw >= 100,
        "telereleve_enedis": True,  # assume true si CDC en DB
        "gtb_installed": False,
        "historique_12m": has_12m,
        "disponibilite_80pct": True,  # assume 85% per spec
        "agregateur_contact": False,
    }

    return {
        "site_id": site_id,
        "site_name": site.nom,
        "flex_score": base_assessment.get("flex_score", 0),
        "flex_summary": {
            "total_pilotable_kw": total_pilotable_kw,
            "nebco_eligible": nebco_eligible,
            "estimated_revenue_eur_year": revenue,
        },
        "by_usage": by_usage,
        "bacs_flex_link": bacs_flex_link,
        "go_nogo_checklist": go_nogo,
    }


def compute_flex_portfolio(db: Session, site_ids: list[int]) -> dict:
    """Agrège le potentiel flex de plusieurs sites."""
    results = []
    for sid in site_ids:
        try:
            r = compute_flex_nebco(db, sid)
            if "error" not in r:
                results.append(r)
        except Exception:
            continue

    total_kw = sum(r["flex_summary"]["total_pilotable_kw"] for r in results)
    nebco_sites = sum(1 for r in results if r["flex_summary"]["nebco_eligible"])
    revenue_mid = sum(
        (
            r["flex_summary"]["estimated_revenue_eur_year"]["nebco_low"]
            + r["flex_summary"]["estimated_revenue_eur_year"]["nebco_high"]
        )
        / 2
        + r["flex_summary"]["estimated_revenue_eur_year"].get("capacity", 0)
        for r in results
    )
    total_bacs_kw = sum(r["bacs_flex_link"]["kw_unlocked_by_bacs"] for r in results)
    total_bacs_cost = sum(
        r["bacs_flex_link"]["bacs_cost_estimate_eur"] for r in results if r["bacs_flex_link"]["kw_unlocked_by_bacs"] > 0
    )
    total_bacs_revenue = sum(r["bacs_flex_link"]["flex_revenue_unlocked_eur_year"] for r in results)

    return {
        "total_kw": round(total_kw, 1),
        "total_sites": len(results),
        "nebco_sites": nebco_sites,
        "revenue_mid_eur": round(revenue_mid),
        "bacs_portfolio": {
            "total_kw_unlockable": round(total_bacs_kw, 1),
            "total_cost_eur": total_bacs_cost,
            "total_revenue_eur_year": total_bacs_revenue,
            "portfolio_roi_months": round(total_bacs_cost / max(total_bacs_revenue / 12, 1))
            if total_bacs_revenue > 0
            else 0,
        },
        "sites": [_enrich_site_for_portfolio(r) for r in results],
    }


# ── Complexité et disponibilité pour le bubble chart ──────────────────────

COMPLEXITY_MAP = {"haute": 1, "moyenne": 2, "variable": 3, "faible": 4}


def _enrich_site_for_portfolio(r: dict) -> dict:
    """Enrichit les données par site pour le bubble chart flex portfolio."""
    fs = r["flex_summary"]
    rev = fs["estimated_revenue_eur_year"]
    revenue_mid = round((rev["nebco_low"] + rev["nebco_high"]) / 2 + rev.get("capacity", 0))

    # Disponibilité : % des critères go/nogo remplis
    checklist = r.get("go_nogo_checklist", {})
    checks = [v for k, v in checklist.items() if isinstance(v, bool)]
    availability_pct = round(sum(checks) / max(len(checks), 1) * 100) if checks else 50

    # Complexité : moyenne pondérée des pilotabilités par kW
    by_usage = r.get("by_usage", [])
    total_kw = sum(u.get("kw_pilotable", 0) for u in by_usage)
    if total_kw > 0:
        weighted = sum(
            COMPLEXITY_MAP.get(u.get("pilotability", "faible"), 4) * u.get("kw_pilotable", 0) for u in by_usage
        )
        complexity = round(weighted / total_kw, 1)
    else:
        complexity = 4

    return {
        "site_id": r["site_id"],
        "site_name": r["site_name"],
        "kw_pilotable": round(fs["total_pilotable_kw"], 1),
        "nebco_eligible": fs["nebco_eligible"],
        "revenue_mid_eur": revenue_mid,
        "availability_pct": availability_pct,
        "complexity_score": complexity,
    }
