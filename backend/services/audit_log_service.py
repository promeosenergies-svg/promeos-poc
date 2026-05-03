"""Audit log service — SoT pour traçabilité actions patrimoine + cascade.

Sprint C-2 Phase 1 — comble GAP audit Phase B R9 (audit_log_service dédié).

Source : matrice v1 §6.10 + audit Phase B R9.

API publique :
- log_patrimoine_change : audit modification champ patrimoine (PATCH events)
- log_cascade : audit cascade recompute (Phase 6 Sprint C-1)
- query_audit_trail : récupération audit trail org-scopée

Modèle : iam.AuditLog étendu (Phase 1.2 — 6 colonnes nullable backward compat).
Toute écriture passe par ce service (source-guard active dans
backend/tests/source_guards/test_audit_log_no_direct_writes_source_guards.py).

Allowlist legacy 7 callsites (cf. D-Phase1-Audit-Log-Legacy-Callsites-001) :
- middleware/cx_logger.py (CX events)
- services/intake_service.py
- services/operat_export_service.py
- services/copilot_engine.py
- services/iam_service.py
- (NB : routes/patrimoine/sites.py:508,554 ont été MIGRÉS vers ce service Phase 1.2)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from models.iam import AuditLog


_logger = logging.getLogger(__name__)


def _serialize_value(value: Any) -> Optional[str]:
    """Sérialise une valeur en JSON pour stockage dans old_value/new_value.

    Retourne None si value est None.
    Utilise default=str pour gérer datetime/date/Decimal automatiquement.
    """
    if value is None:
        return None
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def log_patrimoine_change(
    db: Session,
    *,
    user_id: Optional[int],
    org_id: Optional[int],
    entity_type: str,
    entity_id: int,
    action: str,
    field_modified: Optional[str] = None,
    old_value: Any = None,
    new_value: Any = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    detail: Optional[dict] = None,
) -> AuditLog:
    """Audit log modification champ patrimoine (PATCH events sur Site/Batiment/etc.).

    Args:
        db: session SQLAlchemy
        user_id: utilisateur déclencheur (None si système/cron)
        org_id: organisation propriétaire (scoping multi-tenant)
        entity_type: ex "site", "batiment", "compteur"
        entity_id: identifiant de l'entité modifiée
        action: ex "patrimoine.update", "site.update", "site.archive"
        field_modified: nom du champ modifié (optionnel si modification multi-champs)
        old_value, new_value: valeurs avant/après (sérialisés JSON automatiquement)
        correlation_id: identifiant de corrélation cross-services
        ip_address, user_agent: traçabilité HTTP
        detail: dict additionnel sérialisé dans detail_json

    Returns:
        AuditLog instance (id populé via flush, pas commit — caller décide).

    Note : ne fait pas de commit. Le caller est responsable du commit.
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=entity_type,
        resource_id=str(entity_id),
        detail_json=json.dumps(detail, default=str, ensure_ascii=False) if detail else None,
        ip_address=ip_address,
        # Sprint C-2 Phase 1 — extension
        correlation_id=correlation_id,
        org_id=org_id,
        field_modified=field_modified,
        old_value=_serialize_value(old_value),
        new_value=_serialize_value(new_value),
        user_agent=user_agent,
    )
    db.add(log)
    db.flush()
    return log


def log_cascade(
    db: Session,
    *,
    user_id: Optional[int],
    org_id: Optional[int],
    cascade_result,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    """Audit log cascade recompute (Phase 6 Sprint C-1).

    Args:
        cascade_result: instance CascadeResult de cascade_recompute_service.
            Sérialisé en payload structuré dans detail_json :
            {type, trigger_field, old_value_serialized, new_value_serialized,
             actions[], errors_count, successes_count, persisted}

    Returns:
        AuditLog instance.

    Convention payload detail_json :
    - `type`: "cascade_recompute"
    - `trigger_field`: champ amont qui a déclenché la cascade
    - `actions`: liste des recalculs cascadants (output_field, new_value, error)
    - `errors_count` / `successes_count` : agrégats
    - `persisted`: True si cascade en mode persist=True, False si dry-run
    """
    payload = {
        "type": "cascade_recompute",
        "trigger_field": cascade_result.field_modified,
        "old_value_serialized": str(cascade_result.old_value) if cascade_result.old_value is not None else None,
        "new_value_serialized": str(cascade_result.new_value) if cascade_result.new_value is not None else None,
        "actions": [
            {
                "output_field": a.output_field,
                "new_value": str(a.new_value) if a.new_value is not None else None,
                "error": a.error,
            }
            for a in cascade_result.actions
        ],
        "errors_count": sum(1 for a in cascade_result.actions if a.error),
        "successes_count": sum(1 for a in cascade_result.actions if not a.error),
        "persisted": cascade_result.persisted,
    }

    log = AuditLog(
        user_id=user_id,
        action="cascade.recompute",
        resource_type=cascade_result.entity_type,
        resource_id=str(cascade_result.entity_id) if cascade_result.entity_id is not None else None,
        detail_json=json.dumps(payload, default=str, ensure_ascii=False),
        ip_address=ip_address,
        # Sprint C-2 Phase 1 — extension
        correlation_id=correlation_id,
        org_id=org_id,
        field_modified=cascade_result.field_modified,
        old_value=_serialize_value(cascade_result.old_value),
        new_value=_serialize_value(cascade_result.new_value),
        user_agent=user_agent,
    )
    db.add(log)
    db.flush()
    return log


def query_audit_trail(
    db: Session,
    *,
    org_id: int,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    action: Optional[str] = None,
    correlation_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 100,
) -> list[AuditLog]:
    """Récupère l'audit trail filtré et org-scopé.

    Args:
        org_id: OBLIGATOIRE — sécurité multi-tenant. Une org ne peut voir que ses
            propres logs.
        entity_type, entity_id, action, correlation_id: filtres optionnels.
        since, until: bornes temporelles created_at.
        limit: pagination (défaut 100, ordre desc created_at).

    Returns:
        list[AuditLog] triée par created_at desc.

    ⚠️ Sécurité : org_id est OBLIGATOIRE pour cette query. Pas de fallback "all orgs".
    """
    q = db.query(AuditLog).filter(AuditLog.org_id == org_id)

    if entity_type:
        q = q.filter(AuditLog.resource_type == entity_type)
    if entity_id is not None:
        q = q.filter(AuditLog.resource_id == str(entity_id))
    if action:
        q = q.filter(AuditLog.action == action)
    if correlation_id:
        q = q.filter(AuditLog.correlation_id == correlation_id)
    if since:
        q = q.filter(AuditLog.created_at >= since)
    if until:
        q = q.filter(AuditLog.created_at <= until)

    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()
