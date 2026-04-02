"""
PROMEOS - Mini Flex V0
Heuristic flex potential scoring driven by consumption diagnostic insights.

Levers:
  HVAC: off-hours + high base load → HVAC can be shed/shifted
  IRVE: peaks detected + site has parking/EV flag → charge shifting
  FROID: continuous consumption + cold-chain archetype → cold storage inertia

No spot/NEBCO/HPHC — pure demand-side flexibility potential.
"""

import json
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models import Site, ConsumptionInsight
from models.energy_models import UsageProfile


# ── Archetype hints ──────────────────────────────────────────────
# Maps site types and archetype codes to flex-relevant flags.
COLD_ARCHETYPES = {"COMMERCE_ALIMENTAIRE", "LOGISTIQUE_FROID", "commerce", "magasin"}
HVAC_ARCHETYPES = {"BUREAU_STANDARD", "BUREAU_PERFORMANT", "bureau", "hotel", "sante", "enseignement"}
IRVE_SITE_TYPES = {"bureau", "commerce", "magasin", "hotel", "collectivite"}


def compute_flex_mini(
    db: Session,
    site_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Dict:
    """Compute mini flex potential for a site based on its diagnostic insights.

    Returns::

        {
            "site_id": int,
            "flex_potential_score": 0-100,
            "levers": [
                {
                    "id": "hvac"|"irve"|"froid",
                    "label": str,
                    "score": 0-100,
                    "justification": str,
                    "estimate_kw": float|null,
                    "estimate_kwh_year": float|null,
                }
            ],
            "inputs_used": {insights_count, archetype, site_type},
        }
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return {
            "site_id": site_id,
            "flex_potential_score": 0,
            "levers": [],
            "inputs_used": {},
            "error": "site_not_found",
        }

    # Gather insights
    q = db.query(ConsumptionInsight).filter(ConsumptionInsight.site_id == site_id)
    insights = q.all()

    # Gather archetype from latest UsageProfile
    profile = (
        db.query(UsageProfile)
        .join(UsageProfile.meter)
        .filter(UsageProfile.meter.has(site_id=site_id))
        .order_by(UsageProfile.period_start.desc())
        .first()
    )
    archetype_code = profile.archetype_code if profile else None
    site_type = site.type.value if site.type else None

    # Index insights by type
    by_type = {}
    for ci in insights:
        by_type.setdefault(ci.type, []).append(ci)

    # ── HVAC lever ───────────────────────────────────────────────
    hvac = _score_hvac(by_type, archetype_code, site_type)

    # ── IRVE lever ───────────────────────────────────────────────
    irve = _score_irve(by_type, site, site_type)

    # ── FROID lever ──────────────────────────────────────────────
    froid = _score_froid(by_type, archetype_code, site_type)

    levers = sorted([hvac, irve, froid], key=lambda l: l["score"], reverse=True)

    # Global score = weighted average of top levers (diminishing weight)
    weights = [0.50, 0.30, 0.20]
    flex_score = sum(l["score"] * w for l, w in zip(levers, weights))
    flex_score = min(100, max(0, round(flex_score)))

    return {
        "site_id": site_id,
        "flex_potential_score": flex_score,
        "levers": levers[:3],
        "inputs_used": {
            "insights_count": len(insights),
            "archetype": archetype_code,
            "site_type": site_type,
        },
    }


def _score_hvac(by_type: Dict, archetype: Optional[str], site_type: Optional[str]) -> Dict:
    """HVAC flex: off-hours consumption + high base load → can shed/shift."""
    score = 0
    reasons = []
    estimate_kw = None

    # Off-hours insight
    hh = by_type.get("hors_horaires", [])
    if hh:
        worst = max(hh, key=lambda c: c.estimated_loss_kwh or 0)
        metrics = json.loads(worst.metrics_json) if worst.metrics_json else {}
        off_pct = metrics.get("off_hours_pct", 0)
        avg_off_kw = metrics.get("avg_off_hour_kw", 0)

        if off_pct > 50:
            score += 50
            reasons.append(f"{off_pct:.0f}% conso hors horaires")
        elif off_pct > 35:
            score += 30
            reasons.append(f"{off_pct:.0f}% conso hors horaires")
        elif off_pct > 20:
            score += 15
            reasons.append(f"{off_pct:.0f}% conso hors horaires (modere)")

        if avg_off_kw > 0:
            estimate_kw = round(avg_off_kw * 0.6, 1)  # 60% sheddable

    # Base load insight
    bl = by_type.get("base_load", [])
    if bl:
        worst = max(bl, key=lambda c: c.estimated_loss_kwh or 0)
        metrics = json.loads(worst.metrics_json) if worst.metrics_json else {}
        base_ratio = metrics.get("base_ratio_pct", 0)
        base_kw = metrics.get("base_load_kw", 0)

        if base_ratio > 50:
            score += 30
            reasons.append(f"Talon {base_ratio:.0f}% de la mediane")
        elif base_ratio > 35:
            score += 15
            reasons.append(f"Talon {base_ratio:.0f}%")

        if estimate_kw is None and base_kw > 0:
            estimate_kw = round(base_kw * 0.3, 1)  # 30% of base sheddable

    # Archetype bonus
    if archetype in HVAC_ARCHETYPES or site_type in HVAC_ARCHETYPES:
        score += 10
        reasons.append("Archetype tertiaire (CVC probable)")

    score = min(100, score)
    estimate_kwh = round(estimate_kw * 2000, 0) if estimate_kw else None  # ~2000h flex/year

    return {
        "id": "hvac",
        "label": "Effacement CVC",
        "score": score,
        "justification": " · ".join(reasons) if reasons else "Pas de signal CVC identifie",
        "estimate_kw": estimate_kw,
        "estimate_kwh_year": estimate_kwh,
    }


def _score_irve(by_type: Dict, site: Site, site_type: Optional[str]) -> Dict:
    """IRVE flex: peaks + parking/EV-ready site → charge shifting."""
    score = 0
    reasons = []
    estimate_kw = None

    # Peak insight
    peaks = by_type.get("pointe", [])
    if peaks:
        worst = max(peaks, key=lambda c: c.estimated_loss_kwh or 0)
        metrics = json.loads(worst.metrics_json) if worst.metrics_json else {}
        anomaly_days = metrics.get("anomaly_days_count", 0)

        if anomaly_days > 5:
            score += 35
            reasons.append(f"{anomaly_days} jours de pointe anormale")
        elif anomaly_days > 2:
            score += 20
            reasons.append(f"{anomaly_days} jours de pointe")

        max_daily = metrics.get("max_daily_kwh", 0)
        median_daily = metrics.get("median_daily_kwh", 0)
        if median_daily > 0 and max_daily > median_daily * 1.5:
            estimate_kw = round((max_daily - median_daily) / 24 * 0.5, 1)

    # Site type bonus (parking-likely)
    has_parking = getattr(site, "parking_type", None) is not None
    if has_parking:
        score += 25
        reasons.append("Parking present (IRVE possible)")
    elif site_type in IRVE_SITE_TYPES:
        score += 10
        reasons.append(f"Type {site_type} (parking probable)")

    # Drift + peaks = sustained need
    if by_type.get("derive") and peaks:
        score += 10
        reasons.append("Tendance haussiere + pics = besoin d'etalement")

    score = min(100, score)
    estimate_kwh = round(estimate_kw * 1500, 0) if estimate_kw else None  # ~1500h shift/year

    return {
        "id": "irve",
        "label": "Pilotage IRVE",
        "score": score,
        "justification": " · ".join(reasons) if reasons else "Pas de signal IRVE identifie",
        "estimate_kw": estimate_kw,
        "estimate_kwh_year": estimate_kwh,
    }


def _score_froid(by_type: Dict, archetype: Optional[str], site_type: Optional[str]) -> Dict:
    """Cold storage flex: continuous consumption + cold-chain archetype → thermal inertia."""
    score = 0
    reasons = []
    estimate_kw = None

    # High base load = continuous consumption (cold-chain signature)
    bl = by_type.get("base_load", [])
    if bl:
        worst = max(bl, key=lambda c: c.estimated_loss_kwh or 0)
        metrics = json.loads(worst.metrics_json) if worst.metrics_json else {}
        base_ratio = metrics.get("base_ratio_pct", 0)
        base_kw = metrics.get("base_load_kw", 0)

        if base_ratio > 60:
            score += 30
            reasons.append(f"Talon continu {base_ratio:.0f}% (signature froid)")
        elif base_ratio > 40:
            score += 15
            reasons.append(f"Talon {base_ratio:.0f}%")

        if base_kw > 0:
            estimate_kw = round(base_kw * 0.2, 1)  # 20% inertia-shiftable

    # Archetype match
    if archetype in COLD_ARCHETYPES or site_type in COLD_ARCHETYPES:
        score += 40
        reasons.append("Archetype chaine du froid")
    elif site_type == "entrepot":
        score += 15
        reasons.append("Entrepot (froid possible)")

    # Low off-hours = 24/7 operation = cold storage
    hh = by_type.get("hors_horaires", [])
    if not hh and bl:
        score += 10
        reasons.append("Fonctionnement continu (pas d'anomalie hors-horaires)")

    score = min(100, score)
    estimate_kwh = round(estimate_kw * 1000, 0) if estimate_kw else None  # ~1000h shift/year

    return {
        "id": "froid",
        "label": "Inertie Froid",
        "score": score,
        "justification": " · ".join(reasons) if reasons else "Pas de signal froid identifie",
        "estimate_kw": estimate_kw,
        "estimate_kwh_year": estimate_kwh,
    }
