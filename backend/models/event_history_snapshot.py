"""Event history snapshot — Sprint Refonte Narrative dynamique Phase 9.D.

Table `event_history_snapshots` : journal append-only des `SolEventCard`
détectés dans le temps. Permet de re-jouer la narrative à une date
historique (`simulate_date` Phase 6 V2).

## Pourquoi un store temporel ?

Phase 6 (commit `5ff240e5`) a livré `simulate_date` qui override
`datetime.now()` dans le builder — mais `compute_events()` lit la DB
courante (état temps réel). Pour vraiment simuler "comme si on était à
J-30", il faut **pouvoir relire les events détectés à cette date passée**.

Phase 9.D livre la fondation :
1. Stockage append-only de chaque `SolEventCard` détecté avec timestamp
2. Service `compute_events_at_date(db, org_id, target_date)` qui retourne
   les snapshots dont `recorded_at ≤ target_date`

## Hors scope Phase 9.D MVP

- **Wiring `compute_events()`** : la fonction actuelle reste lecture
  temps réel. Le wiring `simulate_date → compute_events_at_date` viendra
  V2 après validation panel Phase 5 (besoin réel ?).
- **Snapshot writer** : la routine d'enregistrement automatique des
  events détectés est posée comme helper `record_event_snapshot()` mais
  son intégration dans `event_service.compute_events` reste manuel V2.
- **Garbage collection** : pas de TTL/cleanup sur les snapshots. Une
  org active va générer ~50-100 snapshots/semaine. À couvrir V2 quand
  le volume DB devient un sujet (>1 an de seed).

Ref : audit final ticket BL-6 + sprint narrative-sol2 Phase 9.D.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)

from .base import Base


class EventHistorySnapshot(Base):
    """Snapshot append-only d'un SolEventCard détecté à un instant t.

    Index sur (org_id, recorded_at) pour les queries `events_at_date`.
    Pas de soft-delete (append-only) ni d'edit (snapshots immuables).

    `payload_json` = sérialisation JSON-safe du SolEventCard via `to_dict()`.
    Format flexible (TypedDict canonique côté code, str JSON côté DB) — évite
    les migrations de schéma à chaque évolution de SolEventCard.
    """

    __tablename__ = "event_history_snapshots"
    __table_args__ = (
        Index(
            "ix_event_snapshot_org_recorded",
            "org_id",
            "recorded_at",
        ),
        # Composite index pour la query principale (filter org + date range)
    )

    id = Column(Integer, primary_key=True, index=True)

    # Org-scoping cardinal PROMEOS
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)

    # Métadonnées événement (extraites pour query rapide sans déserialiser le JSON)
    event_id = Column(String(255), nullable=False)  # ex: "consumption_drift:org:1:site:42"
    event_type = Column(String(50), nullable=False)  # SolEventCard.event_type Literal value
    severity = Column(String(20), nullable=False)  # info / watch / warning / critical

    # Timestamp de détection (instant t où l'event a été créé/observé)
    recorded_at = Column(DateTime, nullable=False, index=True)

    # Payload JSON-safe (déserialisable via SolEventCard si besoin)
    # JSON1 SQLite OK ; PostgreSQL JSONB pour V2.
    payload_json = Column(Text, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<EventHistorySnapshot id={self.id} org_id={self.org_id} "
            f"event_id={self.event_id!r} recorded_at={self.recorded_at}>"
        )


__all__ = ["EventHistorySnapshot"]
