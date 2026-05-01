"""Event history service — Sprint Refonte Narrative dynamique Phase 9.D.

Service infrastructure pour le journal append-only des `SolEventCard`
détectés. Couplé à la table `event_history_snapshots` (cf models/).

## Périmètre Phase 9.D MVP

- `record_event_snapshot(db, org_id, event)` : append-only writer
- `compute_events_at_date(db, org_id, target_date)` : reader temporel
- `purge_snapshots_before(db, before_date)` : helper GC manuel V2

Le wiring automatique dans `event_service.compute_events()` reste manuel
V2 — la décision dépend du panel Phase 5 (besoin réel ?). Pour MVP, le
service est exposé pour usage opt-in (ex: tests E2E simulate_date).

## Pourquoi append-only ?

Doctrine §10 SolEventCard : un événement est un fait observé à un instant t,
pas un état mutable. Stockage append-only respecte ce contrat — un snapshot
ne se modifie jamais après création (cohérent avec `@dataclass(frozen=True)`
côté code).

Ref : audit final ticket BL-6 + sprint narrative-sol2 Phase 9.D.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import EventHistorySnapshot
from services.event_bus.types import SolEventCard


# Phase 10.C — Allowlist PII (P1-3 audit Phase 9).
# `payload_json` stocke `to_dict()` d'un SolEventCard. Les champs libres
# `title` et `narrative` peuvent contenir des données nominatives ou des
# identifiants (SIRET, PDL, prénom dans message d'erreur). Phase 10.C
# expurge ces champs vers `[REDACTED]` avant persistence pour éviter
# d'accumuler des PII dans un journal append-only sans TTL.
#
# Champs préservés (whitelist) : event_type, severity, impact, source,
# linked_assets — utiles pour analytics/replay sans PII.
# Champs expurgés : title, narrative, action.label.
_PII_REDACTED_FIELDS = ("title", "narrative")
_PII_REDACTED_NESTED = {
    "action": ("label",),  # action.label peut contenir prénom/SIRET
}
_REDACTED_PLACEHOLDER = "[REDACTED]"


def _sanitize_pii_payload(payload: dict) -> dict:
    """Applique l'allowlist PII sur le payload SolEventCard.to_dict().

    Modifie en place puis retourne le dict (pratique mais pure-function-like
    car le caller passe un nouveau dict via `to_dict()` qui n'est pas
    réutilisé après).
    """
    for field in _PII_REDACTED_FIELDS:
        if field in payload and payload[field]:
            payload[field] = _REDACTED_PLACEHOLDER
    for parent, sub_fields in _PII_REDACTED_NESTED.items():
        if parent in payload and isinstance(payload[parent], dict):
            for sub in sub_fields:
                if sub in payload[parent] and payload[parent][sub]:
                    payload[parent][sub] = _REDACTED_PLACEHOLDER
    return payload


def record_event_snapshot(
    db: Session,
    org_id: int,
    event: SolEventCard,
    *,
    recorded_at: Optional[datetime] = None,
) -> EventHistorySnapshot:
    """Enregistre un snapshot d'event dans le journal append-only.

    Phase 10.C : applique l'allowlist PII sur le `payload_json` avant
    persistence (champs `title` et `narrative` expurgés vers `[REDACTED]`).

    Args:
        db: session SQLAlchemy.
        org_id: org-scoping (cf cardinal PROMEOS).
        event: SolEventCard à enregistrer (frozen dataclass).
        recorded_at: timestamp de détection. Si None, utilise
            `event.source.last_updated_at` (instant de mesure source).

    Returns:
        EventHistorySnapshot persisté (avec id généré).

    Note : le caller est responsable du `db.commit()`.
    """
    if recorded_at is None:
        recorded_at = event.source.last_updated_at

    # Phase 10.C : sanitize payload via allowlist PII
    safe_payload = _sanitize_pii_payload(event.to_dict())

    snapshot = EventHistorySnapshot(
        org_id=org_id,
        event_id=event.id,
        event_type=event.event_type,
        severity=event.severity,
        recorded_at=recorded_at,
        payload_json=json.dumps(safe_payload, ensure_ascii=False, default=str),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def compute_events_at_date(
    db: Session,
    org_id: int,
    target_date: datetime,
    *,
    limit: int = 100,
) -> list[EventHistorySnapshot]:
    """Retourne les snapshots org dont `recorded_at ≤ target_date`.

    Phase 6 V2 (post panel Phase 5) : peut être branché à `event_service.
    compute_events()` pour répondre au paramètre `simulate_date` de la
    route `/api/pages/{key}/briefing`.

    Args:
        db: session SQLAlchemy.
        org_id: org-scoping.
        target_date: date butoir (inclusive). Tous les snapshots avec
            `recorded_at ≤ target_date` sont retournés.
        limit: max snapshots retournés (anti-explosion en cas de seed
            massif). Défaut 100 — couvre largement 1 mois d'events
            actifs sur une org HELIOS-like.

    Returns:
        list[EventHistorySnapshot] triée DESC par recorded_at (le plus
        récent en 1er — comportement attendu pour rendu narrative).
    """
    return (
        db.query(EventHistorySnapshot)
        .filter(
            EventHistorySnapshot.org_id == org_id,
            EventHistorySnapshot.recorded_at <= target_date,
        )
        .order_by(EventHistorySnapshot.recorded_at.desc())
        .limit(limit)
        .all()
    )


def purge_snapshots_before(
    db: Session,
    before_date: datetime,
    *,
    org_id: Optional[int] = None,
) -> int:
    """Supprime les snapshots antérieurs à une date (GC manuel V2).

    Helper exposé pour le V2 quand le volume DB devient un sujet
    (>1 an de seed → ~5k snapshots/org). Pas appelé automatiquement.

    Args:
        db: session SQLAlchemy.
        before_date: date butoir exclusive. Tous les snapshots avec
            `recorded_at < before_date` sont supprimés.
        org_id: si fourni, ne supprime que les snapshots de cette org
            (utile pour purge per-tenant). Sinon purge globale.

    Returns:
        Nombre de snapshots supprimés.
    """
    query = db.query(EventHistorySnapshot).filter(EventHistorySnapshot.recorded_at < before_date)
    if org_id is not None:
        query = query.filter(EventHistorySnapshot.org_id == org_id)
    count = query.count()
    query.delete(synchronize_session=False)
    return count


__all__ = [
    "record_event_snapshot",
    "compute_events_at_date",
    "purge_snapshots_before",
]
