"""
PROMEOS — Notification Service (Sprint 10.2)
Build alerts from 5 briques and sync them idempotently.
"""
import hashlib
import json
from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from models import (
    Organisation, Site, EntiteJuridique, Portefeuille,
    ComplianceFinding, ConsumptionInsight, BillingInsight,
    EnergyContract,
    ActionItem, ActionStatus,
    NotificationEvent, NotificationBatch, NotificationPreference,
    NotificationSeverity, NotificationStatus, NotificationSourceType,
    InsightStatus,
)


# ========================================
# Helpers
# ========================================

def _get_site_ids(db: Session, org_id: int) -> list:
    """Resolve site IDs for an organisation."""
    ej_ids = [
        row[0] for row in
        db.query(EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    ]
    if not ej_ids:
        return []
    pf_ids = [
        row[0] for row in
        db.query(Portefeuille.id)
        .filter(Portefeuille.entite_juridique_id.in_(ej_ids))
        .all()
    ]
    if not pf_ids:
        return []
    return [
        row[0] for row in
        db.query(Site.id)
        .filter(Site.portefeuille_id.in_(pf_ids), Site.actif == True)
        .all()
    ]


def _hash_inputs(*parts) -> str:
    """SHA-256 hash of concatenated parts for dedup."""
    raw = "|".join(str(p) for p in parts if p is not None)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _get_thresholds(db: Session, org_id: int) -> dict:
    """Get org preferences or defaults."""
    pref = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.org_id == org_id)
        .first()
    )
    defaults = {"critical_due_days": 30, "warn_due_days": 60}
    if pref and pref.thresholds_json:
        try:
            return {**defaults, **json.loads(pref.thresholds_json)}
        except (json.JSONDecodeError, TypeError):
            pass
    return defaults


def _site_nom(db: Session, site_id: Optional[int]) -> str:
    if not site_id:
        return ""
    site = db.query(Site).filter(Site.id == site_id).first()
    return site.nom if site else f"Site #{site_id}"


# ========================================
# Build notifications from each brique
# ========================================

def build_from_compliance(db: Session, org_id: int, site_ids: list, thresholds: dict) -> List[dict]:
    """NOK findings → CRITICAL/WARN alerts. Deadline proximity boosts severity."""
    findings = (
        db.query(ComplianceFinding)
        .filter(
            ComplianceFinding.site_id.in_(site_ids),
            ComplianceFinding.status.in_(["NOK", "UNKNOWN"]),
            ComplianceFinding.insight_status != InsightStatus.FALSE_POSITIVE,
        )
        .all()
    )

    today = date.today()
    alerts = []
    for f in findings:
        # Determine severity
        sev_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        sev_score = sev_map.get(f.severity, 2)

        if f.status == "UNKNOWN":
            severity = NotificationSeverity.WARN
        elif sev_score >= 3:
            severity = NotificationSeverity.CRITICAL
        else:
            severity = NotificationSeverity.WARN

        # Deadline proximity override
        if f.deadline:
            days_left = (f.deadline - today).days
            if days_left <= thresholds["critical_due_days"]:
                severity = NotificationSeverity.CRITICAL
            elif days_left <= thresholds["warn_due_days"] and severity == NotificationSeverity.INFO:
                severity = NotificationSeverity.WARN

        site_name = _site_nom(db, f.site_id)
        title = f"Non-conformite {f.regulation or ''} — {f.rule_id}"
        if f.status == "UNKNOWN":
            title = f"Donnees manquantes pour {f.rule_id}"

        alerts.append({
            "org_id": org_id,
            "site_id": f.site_id,
            "source_type": NotificationSourceType.COMPLIANCE,
            "source_id": str(f.id),
            "source_key": f"finding:{f.id}",
            "severity": severity,
            "title": title[:500],
            "message": f.evidence or f"Site: {site_name}",
            "due_date": f.deadline,
            "estimated_impact_eur": None,
            "deeplink_path": f"/conformite?site_id={f.site_id}" if f.site_id else "/conformite",
            "evidence_json": json.dumps({
                "rule_id": f.rule_id,
                "regulation": f.regulation,
                "finding_status": f.status,
                "severity": f.severity,
            }),
            "_hash_parts": (title, f.severity, str(f.deadline), str(f.id)),
        })

    return alerts


def build_from_billing(db: Session, org_id: int, site_ids: list, thresholds: dict) -> List[dict]:
    """Top billing anomalies → WARN/CRITICAL based on loss amount."""
    insights = (
        db.query(BillingInsight)
        .filter(
            BillingInsight.site_id.in_(site_ids),
            BillingInsight.insight_status != InsightStatus.FALSE_POSITIVE,
        )
        .order_by(BillingInsight.estimated_loss_eur.desc())
        .limit(20)
        .all()
    )

    alerts = []
    for ins in insights:
        loss = ins.estimated_loss_eur or 0
        if loss >= 5000:
            severity = NotificationSeverity.CRITICAL
        elif loss >= 1000:
            severity = NotificationSeverity.WARN
        else:
            severity = NotificationSeverity.INFO

        site_name = _site_nom(db, ins.site_id)
        alerts.append({
            "org_id": org_id,
            "site_id": ins.site_id,
            "source_type": NotificationSourceType.BILLING,
            "source_id": str(ins.id),
            "source_key": f"billing_insight:{ins.id}",
            "severity": severity,
            "title": f"Anomalie facturation: {ins.type} ({site_name})"[:500],
            "message": ins.message,
            "due_date": None,
            "estimated_impact_eur": loss,
            "deeplink_path": f"/bill-intel?site_id={ins.site_id}" if ins.site_id else "/bill-intel",
            "evidence_json": json.dumps({
                "type": ins.type,
                "loss_eur": loss,
                "severity": ins.severity,
            }),
            "_hash_parts": (ins.type, str(ins.id), str(loss)),
        })

    return alerts


def build_from_purchase(db: Session, org_id: int, site_ids: list, thresholds: dict) -> List[dict]:
    """Contract renewals → CRITICAL/WARN/INFO based on days remaining."""
    today = date.today()
    contracts = (
        db.query(EnergyContract)
        .filter(
            EnergyContract.site_id.in_(site_ids),
            EnergyContract.end_date.isnot(None),
            EnergyContract.end_date >= today,
        )
        .order_by(EnergyContract.end_date.asc())
        .all()
    )

    alerts = []
    for c in contracts:
        days_left = (c.end_date - today).days
        if days_left <= 30:
            severity = NotificationSeverity.CRITICAL
        elif days_left <= 60:
            severity = NotificationSeverity.WARN
        elif days_left <= 90:
            severity = NotificationSeverity.INFO
        else:
            continue  # Too far away

        site_name = _site_nom(db, c.site_id)
        title = f"Renouvellement contrat {c.supplier_name} — {site_name} (J-{days_left})"
        alerts.append({
            "org_id": org_id,
            "site_id": c.site_id,
            "source_type": NotificationSourceType.PURCHASE,
            "source_id": str(c.id),
            "source_key": f"contract_renewal:{c.id}",
            "severity": severity,
            "title": title[:500],
            "message": f"Echeance le {c.end_date.strftime('%d/%m/%Y')} — {c.supplier_name}",
            "due_date": c.end_date,
            "estimated_impact_eur": None,
            "deeplink_path": f"/achat-energie?site_id={c.site_id}" if c.site_id else "/achat-energie",
            "evidence_json": json.dumps({
                "supplier": c.supplier_name,
                "end_date": c.end_date.isoformat(),
                "days_remaining": days_left,
            }),
            "_hash_parts": (str(c.id), c.supplier_name, c.end_date.isoformat()),
        })

    return alerts


def build_from_consumption(db: Session, org_id: int, site_ids: list, thresholds: dict) -> List[dict]:
    """Strong drifts + data gaps → WARN/CRITICAL."""
    insights = (
        db.query(ConsumptionInsight)
        .filter(ConsumptionInsight.site_id.in_(site_ids))
        .all()
    )

    alerts = []
    for ins in insights:
        loss = ins.estimated_loss_eur or 0

        # Data gaps
        if ins.type == "data_gap":
            severity = NotificationSeverity.WARN
            title = f"Lacune donnees sur {_site_nom(db, ins.site_id)}"
        # Strong drifts / high loss
        elif loss >= 5000:
            severity = NotificationSeverity.CRITICAL
            title = f"Derive importante: {ins.type} ({_site_nom(db, ins.site_id)})"
        elif loss >= 1000:
            severity = NotificationSeverity.WARN
            title = f"Anomalie conso: {ins.type} ({_site_nom(db, ins.site_id)})"
        else:
            continue  # Minor

        alerts.append({
            "org_id": org_id,
            "site_id": ins.site_id,
            "source_type": NotificationSourceType.CONSUMPTION,
            "source_id": str(ins.id),
            "source_key": f"conso_insight:{ins.id}",
            "severity": severity,
            "title": title[:500],
            "message": ins.message,
            "due_date": None,
            "estimated_impact_eur": loss if loss > 0 else None,
            "deeplink_path": f"/diagnostic-conso?site_id={ins.site_id}" if ins.site_id else "/diagnostic-conso",
            "evidence_json": json.dumps({
                "type": ins.type,
                "severity": ins.severity,
                "loss_eur": loss,
            }),
            "_hash_parts": (ins.type, str(ins.id), str(loss)),
        })

    return alerts


def build_from_actions(db: Session, org_id: int, thresholds: dict) -> List[dict]:
    """Overdue or BLOCKED actions → WARN/CRITICAL."""
    today = date.today()

    # Overdue actions
    overdue = (
        db.query(ActionItem)
        .filter(
            ActionItem.org_id == org_id,
            ActionItem.status.in_([ActionStatus.OPEN, ActionStatus.IN_PROGRESS]),
            ActionItem.due_date.isnot(None),
            ActionItem.due_date < today,
        )
        .all()
    )

    # Blocked actions
    blocked = (
        db.query(ActionItem)
        .filter(
            ActionItem.org_id == org_id,
            ActionItem.status == ActionStatus.BLOCKED,
        )
        .all()
    )

    alerts = []

    for a in overdue:
        days_overdue = (today - a.due_date).days
        severity = NotificationSeverity.CRITICAL if days_overdue > 14 else NotificationSeverity.WARN
        alerts.append({
            "org_id": org_id,
            "site_id": a.site_id,
            "source_type": NotificationSourceType.ACTION_HUB,
            "source_id": str(a.id),
            "source_key": f"action_overdue:{a.id}",
            "severity": severity,
            "title": f"Action en retard (J+{days_overdue}): {a.title}"[:500],
            "message": f"Echeance depassee: {a.due_date.strftime('%d/%m/%Y')}",
            "due_date": a.due_date,
            "estimated_impact_eur": a.estimated_gain_eur,
            "deeplink_path": "/actions",
            "evidence_json": json.dumps({
                "action_id": a.id,
                "days_overdue": days_overdue,
                "status": a.status.value,
            }),
            "_hash_parts": (str(a.id), "overdue", str(days_overdue)),
        })

    for a in blocked:
        alerts.append({
            "org_id": org_id,
            "site_id": a.site_id,
            "source_type": NotificationSourceType.ACTION_HUB,
            "source_id": str(a.id),
            "source_key": f"action_blocked:{a.id}",
            "severity": NotificationSeverity.WARN,
            "title": f"Action bloquee: {a.title}"[:500],
            "message": a.notes or "Action en statut bloque",
            "due_date": a.due_date,
            "estimated_impact_eur": a.estimated_gain_eur,
            "deeplink_path": "/actions",
            "evidence_json": json.dumps({
                "action_id": a.id,
                "status": "blocked",
                "owner": a.owner,
            }),
            "_hash_parts": (str(a.id), "blocked"),
        })

    return alerts


# ========================================
# Main sync function
# ========================================

def sync_notifications(db: Session, org_id: int, triggered_by: str = "api") -> dict:
    """
    Synchronise notifications from 5 briques. Idempotent via inputs_hash.
    Preserves READ/DISMISSED status on existing events.
    """
    batch = NotificationBatch(
        org_id=org_id,
        triggered_by=triggered_by,
        started_at=datetime.utcnow(),
        created_count=0,
        updated_count=0,
        skipped_count=0,
    )
    db.add(batch)
    db.flush()

    site_ids = _get_site_ids(db, org_id)
    thresholds = _get_thresholds(db, org_id)
    warnings = []

    # Collect alerts from all 5 briques
    all_alerts = []
    builders = [
        ("compliance", lambda: build_from_compliance(db, org_id, site_ids, thresholds)),
        ("billing", lambda: build_from_billing(db, org_id, site_ids, thresholds)),
        ("purchase", lambda: build_from_purchase(db, org_id, site_ids, thresholds)),
        ("consumption", lambda: build_from_consumption(db, org_id, site_ids, thresholds)),
        ("action_hub", lambda: build_from_actions(db, org_id, thresholds)),
    ]

    for name, builder in builders:
        try:
            all_alerts.extend(builder())
        except Exception as e:
            warnings.append(f"{name}: {e}")

    # Upsert
    for alert in all_alerts:
        inputs_hash = _hash_inputs(*alert.get("_hash_parts", (alert["title"],)))

        existing = (
            db.query(NotificationEvent)
            .filter(
                NotificationEvent.org_id == org_id,
                NotificationEvent.source_type == alert["source_type"],
                NotificationEvent.source_id == alert["source_id"],
                NotificationEvent.source_key == alert["source_key"],
            )
            .first()
        )

        if existing is None:
            event = NotificationEvent(
                org_id=org_id,
                site_id=alert.get("site_id"),
                source_type=alert["source_type"],
                source_id=alert.get("source_id"),
                source_key=alert.get("source_key"),
                severity=alert["severity"],
                title=alert["title"],
                message=alert.get("message"),
                due_date=alert.get("due_date"),
                estimated_impact_eur=alert.get("estimated_impact_eur"),
                deeplink_path=alert.get("deeplink_path"),
                evidence_json=alert.get("evidence_json"),
                status=NotificationStatus.NEW,
                inputs_hash=inputs_hash,
            )
            db.add(event)
            batch.created_count += 1
        elif existing.inputs_hash != inputs_hash:
            # Update content but PRESERVE status (READ/DISMISSED)
            existing.severity = alert["severity"]
            existing.title = alert["title"]
            existing.message = alert.get("message")
            existing.due_date = alert.get("due_date")
            existing.estimated_impact_eur = alert.get("estimated_impact_eur")
            existing.deeplink_path = alert.get("deeplink_path")
            existing.evidence_json = alert.get("evidence_json")
            existing.inputs_hash = inputs_hash
            batch.updated_count += 1
        else:
            batch.skipped_count += 1

    batch.finished_at = datetime.utcnow()
    if warnings:
        batch.warnings_json = json.dumps(warnings)

    db.commit()

    # Summary counts
    counts = _count_summary(db, org_id)

    return {
        "batch_id": batch.id,
        "created": batch.created_count,
        "updated": batch.updated_count,
        "skipped": batch.skipped_count,
        "warnings": warnings,
        **counts,
    }


def _count_summary(db: Session, org_id: int) -> dict:
    """Count notifications by severity and status for summary endpoint."""
    events = (
        db.query(NotificationEvent)
        .filter(NotificationEvent.org_id == org_id)
        .all()
    )

    by_severity = {"critical": 0, "warn": 0, "info": 0}
    by_status = {"new": 0, "read": 0, "dismissed": 0}
    new_critical = 0
    new_warn = 0

    for e in events:
        sev = e.severity.value if e.severity else "info"
        st = e.status.value if e.status else "new"
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_status[st] = by_status.get(st, 0) + 1
        if st == "new" and sev == "critical":
            new_critical += 1
        if st == "new" and sev == "warn":
            new_warn += 1

    return {
        "total": len(events),
        "by_severity": by_severity,
        "by_status": by_status,
        "new_critical": new_critical,
        "new_warn": new_warn,
    }
