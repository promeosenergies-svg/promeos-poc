"""
PROMEOS — Action Hub Service (Sprint 10)
Synchronise les actions des 4 briques vers ActionItem (persiste, idempotent).
"""

import hashlib
import json
from datetime import date, datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from models import (
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    ComplianceFinding,
    ConsumptionInsight,
    BillingInsight,
    ActionItem,
    ActionSyncBatch,
    ActionSourceType,
    ActionStatus,
    InsightStatus,
)
from services.purchase_actions_engine import compute_purchase_actions


# ========================================
# Helpers
# ========================================


def _get_site_ids(db: Session, org_id: int) -> list:
    """Resolve site IDs for an organisation."""
    ej_ids = [row[0] for row in db.query(EntiteJuridique.id).filter(EntiteJuridique.organisation_id == org_id).all()]
    if not ej_ids:
        return []
    pf_ids = [row[0] for row in db.query(Portefeuille.id).filter(Portefeuille.entite_juridique_id.in_(ej_ids)).all()]
    if not pf_ids:
        return []
    return [row[0] for row in db.query(Site.id).filter(Site.portefeuille_id.in_(pf_ids), Site.actif == True).all()]


def _hash_inputs(*parts) -> str:
    """SHA-256 hash of concatenated parts for change detection."""
    raw = "|".join(str(p) for p in parts if p is not None)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_priority(severity: Optional[str], gain: Optional[float], deadline: Optional[date]) -> int:
    """
    Compute action priority (1=critical, 5=low) from severity, gain, deadline.
    """
    base_map = {"critical": 1, "high": 2, "medium": 3, "low": 4}
    base = base_map.get((severity or "medium").lower(), 3)

    if gain and gain > 10000:
        base -= 1
    elif gain and gain > 5000:
        base -= 0.5

    if deadline:
        days_left = (deadline - date.today()).days
        if days_left < 30:
            base -= 1
        elif days_left < 60:
            base -= 0.5

    return max(1, min(5, round(base)))


# ========================================
# Build actions from each brique
# ========================================


def build_actions_from_compliance(db: Session, org_id: int, site_ids: list) -> List[dict]:
    """Extract actions from ComplianceFinding NOK rows."""
    findings = (
        db.query(ComplianceFinding)
        .filter(
            ComplianceFinding.site_id.in_(site_ids),
            ComplianceFinding.status == "NOK",
            ComplianceFinding.insight_status != InsightStatus.FALSE_POSITIVE,
        )
        .all()
    )

    actions = []
    for f in findings:
        raw_actions = []
        if f.recommended_actions_json:
            try:
                raw_actions = json.loads(f.recommended_actions_json)
            except (json.JSONDecodeError, TypeError):
                raw_actions = []

        if not raw_actions:
            # One action per finding even without recommendations
            raw_actions = [f.evidence or f"Non-conformite {f.rule_id}"]

        for idx, rec in enumerate(raw_actions):
            title = rec if isinstance(rec, str) else str(rec)
            actions.append(
                {
                    "org_id": org_id,
                    "site_id": f.site_id,
                    "source_type": ActionSourceType.COMPLIANCE,
                    "source_id": str(f.id),
                    "source_key": f"{f.rule_id}:{idx}",
                    "title": title[:500],
                    "rationale": f.evidence,
                    "severity": f.severity,
                    "estimated_gain_eur": None,
                    "due_date": f.deadline,
                    "_hash_parts": (title, f.severity, str(f.deadline)),
                }
            )

    return actions


def build_actions_from_consumption(db: Session, org_id: int, site_ids: list) -> List[dict]:
    """Extract actions from ConsumptionInsight rows with losses."""
    insights = (
        db.query(ConsumptionInsight)
        .filter(
            ConsumptionInsight.site_id.in_(site_ids),
            ConsumptionInsight.estimated_loss_eur > 0,
        )
        .all()
    )

    actions = []
    for ins in insights:
        raw_actions = []
        if ins.recommended_actions_json:
            try:
                raw_actions = json.loads(ins.recommended_actions_json)
            except (json.JSONDecodeError, TypeError):
                raw_actions = []

        if not raw_actions:
            # Fallback: one action from the insight message
            raw_actions = [{"title": ins.message, "expected_gain_eur": ins.estimated_loss_eur}]

        for idx, rec in enumerate(raw_actions):
            if isinstance(rec, str):
                rec = {"title": rec}
            title = rec.get("title", ins.message)
            gain = rec.get("expected_gain_eur", ins.estimated_loss_eur)
            actions.append(
                {
                    "org_id": org_id,
                    "site_id": ins.site_id,
                    "source_type": ActionSourceType.CONSUMPTION,
                    "source_id": str(ins.id),
                    "source_key": f"{ins.type}:{idx}",
                    "title": title[:500],
                    "rationale": rec.get("rationale", ins.message),
                    "severity": ins.severity,
                    "estimated_gain_eur": gain,
                    "due_date": None,
                    "_hash_parts": (title, ins.severity, str(gain)),
                }
            )

    return actions


def build_actions_from_billing(db: Session, org_id: int, site_ids: list) -> List[dict]:
    """Extract actions from BillingInsight rows with recommendations."""
    insights = (
        db.query(BillingInsight)
        .filter(
            BillingInsight.site_id.in_(site_ids),
            BillingInsight.insight_status != InsightStatus.FALSE_POSITIVE,
            BillingInsight.recommended_actions_json.isnot(None),
        )
        .all()
    )

    actions = []
    for ins in insights:
        raw_actions = []
        try:
            raw_actions = json.loads(ins.recommended_actions_json)
        except (json.JSONDecodeError, TypeError):
            raw_actions = []

        if not raw_actions:
            raw_actions = [ins.message]

        for idx, rec in enumerate(raw_actions):
            if isinstance(rec, str):
                title = rec
            else:
                title = rec.get("title", ins.message)
            actions.append(
                {
                    "org_id": org_id,
                    "site_id": ins.site_id,
                    "source_type": ActionSourceType.BILLING,
                    "source_id": str(ins.id),
                    "source_key": f"{ins.type}:{idx}",
                    "title": title[:500],
                    "rationale": ins.message,
                    "severity": ins.severity,
                    "estimated_gain_eur": ins.estimated_loss_eur,
                    "due_date": None,
                    "_hash_parts": (title, ins.severity, str(ins.estimated_loss_eur)),
                }
            )

    return actions


def build_actions_from_purchase(db: Session, org_id: int) -> List[dict]:
    """Extract actions from ephemeral purchase_actions_engine."""
    severity_map = {"red": "critical", "orange": "high", "yellow": "medium", "blue": "low"}

    try:
        result = compute_purchase_actions(db, org_id=org_id)
    except Exception:
        return []

    actions = []
    for act in result.get("actions", []):
        severity = severity_map.get(act.get("severity", "blue"), "low")
        contract_id = act.get("contract_id", "auto")
        title = act.get("label", "Action achat energie")
        actions.append(
            {
                "org_id": org_id,
                "site_id": act.get("site_id"),
                "source_type": ActionSourceType.PURCHASE,
                "source_id": f"purchase_{act.get('type', 'unknown')}",
                "source_key": f"{act.get('type', 'unknown')}:{contract_id}",
                "title": title[:500],
                "rationale": title,
                "severity": severity,
                "estimated_gain_eur": None,
                "due_date": None,
                "_hash_parts": (title, severity, str(contract_id)),
            }
        )

    return actions


# ========================================
# Main sync function
# ========================================


def sync_actions(db: Session, org_id: int, triggered_by: str = "api") -> dict:
    """
    Synchronise les actions des 4 briques vers ActionItem.
    Idempotent: upsert par (org_id, source_type, source_id, source_key).
    Preserve workflow (status/owner/notes) on update.
    Auto-close actions whose source is resolved.
    """
    batch = ActionSyncBatch(
        org_id=org_id,
        triggered_by=triggered_by,
        started_at=datetime.now(timezone.utc),
        created_count=0,
        updated_count=0,
        skipped_count=0,
        closed_count=0,
    )
    db.add(batch)
    db.flush()

    site_ids = _get_site_ids(db, org_id)
    warnings = []

    # Per-source caps — keep volumes realistic for demo (5-site portfolio ≈ 30 actions)
    _SOURCE_CAP = {
        "compliance": 10,
        "consumption": 8,
        "billing": 8,
        "purchase": 6,
    }

    def _capped(builder, label, *args):
        try:
            raw = builder(*args)
            cap = _SOURCE_CAP.get(label, 999)
            if len(raw) > cap:
                # Sort by estimated_gain_eur desc so highest-value actions survive
                raw.sort(key=lambda a: -(a.get("estimated_gain_eur") or 0))
                warnings.append(f"{label}: capped {len(raw)} → {cap}")
                return raw[:cap]
            return raw
        except Exception as e:
            warnings.append(f"{label}: {e}")
            return []

    # Collect actions from all 4 briques (capped per source)
    all_actions = []
    all_actions.extend(_capped(build_actions_from_compliance, "compliance", db, org_id, site_ids))
    all_actions.extend(_capped(build_actions_from_consumption, "consumption", db, org_id, site_ids))
    all_actions.extend(_capped(build_actions_from_billing, "billing", db, org_id, site_ids))
    all_actions.extend(_capped(build_actions_from_purchase, "purchase", db, org_id))

    # Track which (source_type, source_id, source_key) are still active
    active_keys = set()

    for act in all_actions:
        key = (act["source_type"], act["source_id"], act["source_key"])
        active_keys.add(key)

        inputs_hash = _hash_inputs(*act.get("_hash_parts", (act["title"],)))

        existing = (
            db.query(ActionItem)
            .filter(
                ActionItem.org_id == org_id,
                ActionItem.source_type == act["source_type"],
                ActionItem.source_id == act["source_id"],
                ActionItem.source_key == act["source_key"],
            )
            .first()
        )

        if existing is None:
            # Create new
            priority = compute_priority(act["severity"], act["estimated_gain_eur"], act["due_date"])
            item = ActionItem(
                org_id=org_id,
                site_id=act["site_id"],
                source_type=act["source_type"],
                source_id=act["source_id"],
                source_key=act["source_key"],
                title=act["title"],
                rationale=act.get("rationale"),
                priority=priority,
                severity=act["severity"],
                estimated_gain_eur=act["estimated_gain_eur"],
                due_date=act["due_date"],
                status=ActionStatus.OPEN,
                inputs_hash=inputs_hash,
            )
            db.add(item)
            batch.created_count += 1
        elif existing.inputs_hash != inputs_hash:
            # Update content but PRESERVE workflow fields
            existing.title = act["title"]
            existing.rationale = act.get("rationale")
            existing.severity = act["severity"]
            existing.estimated_gain_eur = act["estimated_gain_eur"]
            existing.due_date = act["due_date"]
            existing.priority = compute_priority(act["severity"], act["estimated_gain_eur"], act["due_date"])
            existing.inputs_hash = inputs_hash
            # status, owner, notes are PRESERVED
            batch.updated_count += 1
        else:
            # Identical — skip
            batch.skipped_count += 1

    # Auto-close: actions still OPEN/IN_PROGRESS whose source is no longer active
    # Only consider auto-harvested sources — manual/insight actions are user-managed
    _harvested_types = [
        ActionSourceType.COMPLIANCE,
        ActionSourceType.CONSUMPTION,
        ActionSourceType.BILLING,
        ActionSourceType.PURCHASE,
    ]
    open_items = (
        db.query(ActionItem)
        .filter(
            ActionItem.org_id == org_id,
            ActionItem.status.in_([ActionStatus.OPEN, ActionStatus.IN_PROGRESS]),
            ActionItem.source_type.in_(_harvested_types),
        )
        .all()
    )
    for item in open_items:
        key = (item.source_type, item.source_id, item.source_key)
        if key not in active_keys:
            item.status = ActionStatus.DONE
            item.notes = (item.notes or "") + "\n[Auto-ferme: source resolue]"
            item.notes = item.notes.strip()
            batch.closed_count += 1

    batch.finished_at = datetime.now(timezone.utc)
    if warnings:
        batch.warnings_json = json.dumps(warnings)

    db.commit()

    return {
        "batch_id": batch.id,
        "created": batch.created_count,
        "updated": batch.updated_count,
        "skipped": batch.skipped_count,
        "closed": batch.closed_count,
        "warnings": warnings,
    }
