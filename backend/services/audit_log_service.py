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


# ─── Sprint C-7 Phase 7.4 — RGPD consent_change helper (clôture pattern doctrinal 5/5) ───


def log_consent_change(
    db: Session,
    *,
    user_id: Optional[int],
    org_id: int,
    target_type: str,
    target_id: int,
    field: str,
    old_value: Any,
    new_value: Any,
    cgu_version: Optional[str],
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Sprint C-7 Phase 7.4 — Helper RGPD `rgpd.consent_change` event AuditLog.

    Clôture pattern doctrinal "Déclaration sans enforcement runtime" 5/5 cardinal Phase C+ :

    - ADR-007 RGPD a déclaré audit trail (Sprint C-3)
    - Phase 5.3 a livré champs audit trail (`_by` + `_cgu_version`)
    - Phase 5.6 F1 a fixé enforcement FK runtime (PRAGMA foreign_keys=ON)
    - Phase 5.8 G1 a wiré cascade Org consent CASCADE_MAP runtime
    - Phase 5.8 G3 a fixé BillAnomaly UNIQUE constraint
    - Phase 7.2 a fixé DEMO_MODE bypass scope_utils
    - **Phase 7.4 (cette phase)** wire l'event AuditLog runtime → CLÔTURE pattern doctrinal

    Args:
        target_type: "organisation" | "delivery_point" (cf. ADR-007 Option B archi-helios)
        target_id: ID Organisation ou DeliveryPoint
        field: ex "consentement_dataconnect_global", "consentement_grdf_local"
        old_value, new_value: valeurs avant/après (None autorisé pour première mise à jour)
        cgu_version: version CGU acceptée (CNIL article 7 — preuve d'origine forte)

    CNIL article 7 : preuve d'origine forte = qui (user_id) + quand (created_at) +
    valeur (old/new_value) + CGU (cgu_version) + scope (target_type=organisation|delivery_point).

    Note : ne fait pas de commit. Le caller est responsable du commit (cohérent
    pattern `log_patrimoine_change` Sprint C-2 P1.3).
    """
    detail = {
        "type": "rgpd.consent_change",
        "field": field,
        "cgu_version": cgu_version,
        "rgpd_article": "Article 7 RGPD - preuve d'origine du consentement",
    }
    log = AuditLog(
        user_id=user_id,
        action="rgpd.consent_change",
        resource_type=target_type,
        resource_id=str(target_id),
        detail_json=json.dumps(detail, default=str, ensure_ascii=False),
        ip_address=ip_address,
        correlation_id=correlation_id,
        org_id=org_id,
        field_modified=field,
        old_value=_serialize_value(old_value),
        new_value=_serialize_value(new_value),
    )
    db.add(log)
    db.flush()
    return log


def log_consent_changes_batch(
    db: Session,
    *,
    user_id: Optional[int],
    org_id: int,
    target_type: str,
    target_id: int,
    changes: list[dict],
    cgu_version: Optional[str],
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> list[AuditLog]:
    """Sprint C-7 Phase 7.4 — Variant batch pour PATCH multi-champs (1 event par champ muté).

    Args:
        changes: [{"field": "consentement_dataconnect_global", "old": True, "new": False}, ...]

    Returns:
        Liste des AuditLog créés (1 par change). Caller commit responsable.
    """
    events = []
    for change in changes:
        events.append(
            log_consent_change(
                db=db,
                user_id=user_id,
                org_id=org_id,
                target_type=target_type,
                target_id=target_id,
                field=change["field"],
                old_value=change.get("old"),
                new_value=change.get("new"),
                cgu_version=cgu_version,
                correlation_id=correlation_id,
                ip_address=ip_address,
            )
        )
    return events


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
