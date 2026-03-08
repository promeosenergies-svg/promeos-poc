"""
PROMEOS — Energy Copilot Rule Engine (Chantier 3)
4 detection rules MVP:
  R1: Derive mensuelle (>+15% vs moyenne 12 mois)
  R2: Talon nuit eleve (base nuit > 40% de Pmax)
  R3: Consommation week-end anormale (>30% du total)
  R4: Facture manquante (gap > 45 jours)
"""

import json
import logging
from datetime import date, timedelta, datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import (
    Site,
    Meter,
    MeterReading,
    EnergyInvoice,
    Portefeuille,
    EntiteJuridique,
    ActionItem,
    ActionSourceType,
    ActionStatus,
    AuditLog,
)
from models.copilot_models import CopilotAction, CopilotActionStatus

logger = logging.getLogger("promeos.copilot")

from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH

EUR_PER_KWH = DEFAULT_PRICE_ELEC_EUR_KWH  # Source: config.default_prices


# ── Rule definitions ──────────────────────────────────────────────────────────


def _rule_monthly_drift(db: Session, site_id: int, meter_ids: list, today: date) -> Optional[dict]:
    """R1: Derive mensuelle — mois courant vs moyenne 12 mois."""
    if not meter_ids:
        return None

    window_start = today - timedelta(days=365)
    current_month_start = today.replace(day=1)
    prev_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

    # Average monthly consumption over 12 months
    monthly_totals = (
        db.query(
            func.strftime("%Y-%m", MeterReading.timestamp).label("ym"),
            func.sum(MeterReading.value_kwh).label("total"),
        )
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= window_start.isoformat(),
            MeterReading.timestamp < current_month_start.isoformat(),
        )
        .group_by("ym")
        .all()
    )

    if len(monthly_totals) < 3:
        return None

    avg_monthly = sum(t.total for t in monthly_totals) / len(monthly_totals)
    if avg_monthly <= 0:
        return None

    # Previous month consumption
    prev_month_total = (
        db.query(func.sum(MeterReading.value_kwh))
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= prev_month_start.isoformat(),
            MeterReading.timestamp < current_month_start.isoformat(),
        )
        .scalar()
        or 0
    )

    if prev_month_total <= 0:
        return None

    drift_pct = ((prev_month_total - avg_monthly) / avg_monthly) * 100

    if drift_pct > 15:
        savings_kwh = prev_month_total - avg_monthly
        return {
            "rule_code": "R1_MONTHLY_DRIFT",
            "rule_label": "Derive mensuelle",
            "title": f"Surconsommation +{drift_pct:.0f}% vs moyenne 12 mois",
            "description": f"La consommation du mois precedent ({prev_month_total:.0f} kWh) depasse la moyenne de {drift_pct:.0f}%. Verifier les equipements et les usages exceptionnels.",
            "category": "surconsommation",
            "priority": 2 if drift_pct > 30 else 3,
            "estimated_savings_kwh": round(savings_kwh),
            "estimated_savings_eur": round(savings_kwh * EUR_PER_KWH, 2),
            "evidence": {
                "avg_monthly_kwh": round(avg_monthly),
                "prev_month_kwh": round(prev_month_total),
                "drift_pct": round(drift_pct, 1),
                "months_analyzed": len(monthly_totals),
            },
        }
    return None


def _rule_night_baseload(db: Session, site_id: int, meter_ids: list, today: date) -> Optional[dict]:
    """R2: Talon nuit eleve — base nuit > 40% de la consommation moyenne."""
    if not meter_ids:
        return None

    window_start = today - timedelta(days=30)

    # Estimate baseload as P05 (5th percentile of readings)
    readings = (
        db.query(MeterReading.value_kwh)
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= window_start.isoformat(),
        )
        .order_by(MeterReading.value_kwh)
        .all()
    )

    if len(readings) < 50:
        return None

    p05_idx = max(0, int(len(readings) * 0.05))
    p50_idx = int(len(readings) * 0.50)
    baseload = readings[p05_idx].value_kwh
    median = readings[p50_idx].value_kwh

    if median <= 0:
        return None

    baseload_ratio = baseload / median

    if baseload_ratio > 0.6:  # Baseload > 60% of median = high
        savings_kwh = (baseload * 0.3) * 30 * 24  # 30% baseload reduction over month
        return {
            "rule_code": "R2_NIGHT_BASELOAD",
            "rule_label": "Talon nuit eleve",
            "title": f"Talon nuit a {baseload_ratio * 100:.0f}% de la conso mediane",
            "description": f"La consommation de base (P05={baseload:.1f} kWh) represente {baseload_ratio * 100:.0f}% de la mediane ({median:.1f} kWh). Verifier la veille des equipements, le chauffage/clim hors heures.",
            "category": "talon",
            "priority": 3,
            "estimated_savings_kwh": round(savings_kwh),
            "estimated_savings_eur": round(savings_kwh * EUR_PER_KWH, 2),
            "evidence": {
                "baseload_kwh": round(baseload, 1),
                "median_kwh": round(median, 1),
                "baseload_ratio_pct": round(baseload_ratio * 100, 1),
                "readings_count": len(readings),
            },
        }
    return None


def _rule_weekend_excess(db: Session, site_id: int, meter_ids: list, today: date) -> Optional[dict]:
    """R3: Consommation week-end anormale — >30% du total."""
    if not meter_ids:
        return None

    window_start = today - timedelta(days=30)

    total = (
        db.query(func.sum(MeterReading.value_kwh))
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= window_start.isoformat(),
        )
        .scalar()
        or 0
    )

    if total <= 0:
        return None

    # Weekend: Saturday (6) + Sunday (0) — strftime %w: 0=Sunday, 6=Saturday
    weekend = (
        db.query(func.sum(MeterReading.value_kwh))
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= window_start.isoformat(),
            func.strftime("%w", MeterReading.timestamp).in_(["0", "6"]),
        )
        .scalar()
        or 0
    )

    weekend_pct = (weekend / total) * 100 if total > 0 else 0

    # 2 days out of 7 = 28.6% expected. > 30% is anomalous for office buildings
    if weekend_pct > 30:
        excess_kwh = weekend - (total * 2 / 7)
        return {
            "rule_code": "R3_WEEKEND_EXCESS",
            "rule_label": "Surconsommation week-end",
            "title": f"Week-end = {weekend_pct:.0f}% de la conso totale",
            "description": f"La consommation du week-end represente {weekend_pct:.0f}% du total (attendu ~28%). Verifier les equipements restant en marche le week-end.",
            "category": "usage",
            "priority": 3,
            "estimated_savings_kwh": round(max(0, excess_kwh)),
            "estimated_savings_eur": round(max(0, excess_kwh) * EUR_PER_KWH, 2),
            "evidence": {
                "weekend_kwh": round(weekend),
                "total_kwh": round(total),
                "weekend_pct": round(weekend_pct, 1),
            },
        }
    return None


def _rule_invoice_gap(db: Session, site_id: int, today: date) -> Optional[dict]:
    """R4: Facture manquante — gap > 45 jours entre factures."""
    last_invoice = (
        db.query(EnergyInvoice)
        .filter(EnergyInvoice.site_id == site_id)
        .order_by(EnergyInvoice.period_end.desc())
        .first()
    )

    if not last_invoice or not last_invoice.period_end:
        # No invoices at all — major gap
        return {
            "rule_code": "R4_INVOICE_GAP",
            "rule_label": "Facture manquante",
            "title": "Aucune facture importee pour ce site",
            "description": "Aucune facture n'a ete importee. Importer les factures du fournisseur pour activer le suivi energetique.",
            "category": "donnees",
            "priority": 2,
            "estimated_savings_kwh": None,
            "estimated_savings_eur": None,
            "evidence": {"last_invoice_date": None, "gap_days": 999},
        }

    gap_days = (today - last_invoice.period_end).days

    if gap_days > 45:
        return {
            "rule_code": "R4_INVOICE_GAP",
            "rule_label": "Facture manquante",
            "title": f"Derniere facture il y a {gap_days} jours",
            "description": f"La derniere facture date du {last_invoice.period_end}. Verifier aupres du fournisseur et relancer l'import.",
            "category": "donnees",
            "priority": 2 if gap_days > 90 else 3,
            "estimated_savings_kwh": None,
            "estimated_savings_eur": None,
            "evidence": {
                "last_invoice_date": str(last_invoice.period_end),
                "gap_days": gap_days,
            },
        }
    return None


# ── Engine ────────────────────────────────────────────────────────────────────

RULES = [
    _rule_monthly_drift,
    _rule_night_baseload,
    _rule_weekend_excess,
]

RULES_NO_METER = [
    _rule_invoice_gap,
]


def run_copilot_for_site(
    db: Session,
    site_id: int,
    today: Optional[date] = None,
) -> list:
    """Run all copilot rules for a single site. Returns list of findings."""
    if today is None:
        today = date.today()

    meters = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active == True,
        )
        .all()
    )
    meter_ids = [m.id for m in meters]

    findings = []

    for rule_fn in RULES:
        try:
            result = rule_fn(db, site_id, meter_ids, today)
            if result:
                findings.append(result)
        except Exception as exc:
            logger.warning(f"Copilot rule {rule_fn.__name__} failed for site {site_id}: {exc}")

    for rule_fn in RULES_NO_METER:
        try:
            result = rule_fn(db, site_id, today)
            if result:
                findings.append(result)
        except Exception as exc:
            logger.warning(f"Copilot rule {rule_fn.__name__} failed for site {site_id}: {exc}")

    return findings


def run_copilot_monthly(
    db: Session,
    org_id: int,
    today: Optional[date] = None,
) -> dict:
    """
    Run copilot for all sites in an org.
    Creates CopilotAction rows for new findings.
    Returns summary.
    """
    if today is None:
        today = date.today()

    site_ids = [
        row[0]
        for row in db.query(Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id, Site.actif == True)
        .all()
    ]

    total_created = 0
    total_skipped = 0
    all_actions = []

    for sid in site_ids:
        findings = run_copilot_for_site(db, sid, today)

        for f in findings:
            # Dedup: check if same rule_code + site + month already exists
            existing = (
                db.query(CopilotAction)
                .filter(
                    CopilotAction.site_id == sid,
                    CopilotAction.rule_code == f["rule_code"],
                    CopilotAction.period_month == today.month,
                    CopilotAction.period_year == today.year,
                )
                .first()
            )

            if existing:
                total_skipped += 1
                continue

            # Priority score: higher = more urgent (priority weight + savings impact)
            savings_eur = f.get("estimated_savings_eur") or 0
            prio = f.get("priority", 3)
            priority_score = round((6 - prio) * 20 + min(savings_eur / 100, 50), 1)

            action = CopilotAction(
                org_id=org_id,
                site_id=sid,
                rule_code=f["rule_code"],
                rule_label=f["rule_label"],
                title=f["title"],
                description=f.get("description"),
                category=f.get("category", "energie"),
                priority=prio,
                estimated_savings_kwh=f.get("estimated_savings_kwh"),
                estimated_savings_eur=savings_eur or None,
                evidence_json=json.dumps(f.get("evidence", {})),
                status=CopilotActionStatus.PROPOSED,
                period_month=today.month,
                period_year=today.year,
                priority_score=priority_score,
            )
            db.add(action)
            total_created += 1
            all_actions.append(f)

    db.commit()

    return {
        "org_id": org_id,
        "sites_analyzed": len(site_ids),
        "actions_created": total_created,
        "actions_skipped_dedup": total_skipped,
        "month": today.month,
        "year": today.year,
    }


def validate_copilot_action(
    db: Session,
    action_id: int,
    user_email: str = "system",
) -> dict:
    """Validate a copilot action — converts to ActionItem + audit log."""
    action = db.query(CopilotAction).filter(CopilotAction.id == action_id).first()
    if not action:
        raise ValueError(f"CopilotAction {action_id} not found")

    # Idempotence: already converted → return existing result
    if action.status == CopilotActionStatus.CONVERTED:
        return {
            "copilot_action_id": action.id,
            "action_item_id": action.action_item_id,
            "status": "converted",
            "already_converted": True,
        }

    if action.status != CopilotActionStatus.PROPOSED:
        raise ValueError(f"CopilotAction {action_id} status is '{action.status.value}', expected 'proposed'")

    # Create ActionItem
    ai = ActionItem(
        org_id=action.org_id,
        site_id=action.site_id,
        source_type=ActionSourceType.COPILOT,
        source_id=f"copilot:{action.id}",
        source_key=f"copilot:{action.rule_code}:{action.period_year}-{action.period_month}",
        title=action.title,
        rationale=action.description,
        priority=action.priority,
        severity="medium",
        status=ActionStatus.OPEN,
        category=action.category,
        estimated_gain_eur=action.estimated_savings_eur,
    )
    db.add(ai)
    db.flush()

    action.status = CopilotActionStatus.CONVERTED
    action.validated_by = user_email
    action.validated_at = datetime.utcnow()
    action.action_item_id = ai.id

    # Audit log
    db.add(
        AuditLog(
            action="copilot_validate",
            user_id=None,
            resource_type="copilot_action",
            resource_id=str(action.id),
            detail_json=json.dumps(
                {
                    "copilot_action_id": action.id,
                    "action_item_id": ai.id,
                    "rule_code": action.rule_code,
                    "site_id": action.site_id,
                    "validated_by": user_email,
                }
            ),
        )
    )

    db.commit()

    return {
        "copilot_action_id": action.id,
        "action_item_id": ai.id,
        "status": "converted",
    }


def reject_copilot_action(
    db: Session,
    action_id: int,
    reason: str = "",
) -> dict:
    """Reject a copilot action + audit log."""
    action = db.query(CopilotAction).filter(CopilotAction.id == action_id).first()
    if not action:
        raise ValueError(f"CopilotAction {action_id} not found")

    # Idempotence: already rejected → return existing result
    if action.status == CopilotActionStatus.REJECTED:
        return {"copilot_action_id": action.id, "status": "rejected", "already_rejected": True}

    if action.status != CopilotActionStatus.PROPOSED:
        raise ValueError(f"CopilotAction {action_id} status is '{action.status.value}', expected 'proposed'")

    if not reason.strip():
        raise ValueError("Motif de rejet obligatoire")

    action.status = CopilotActionStatus.REJECTED
    action.rejection_reason = reason

    # Audit log
    db.add(
        AuditLog(
            action="copilot_reject",
            user_id=None,
            resource_type="copilot_action",
            resource_id=str(action.id),
            detail_json=json.dumps(
                {
                    "copilot_action_id": action.id,
                    "rule_code": action.rule_code,
                    "site_id": action.site_id,
                    "reason": reason,
                }
            ),
        )
    )

    db.commit()

    return {"copilot_action_id": action.id, "status": "rejected"}
