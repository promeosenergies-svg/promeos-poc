"""SolEventCard — schéma typé événement énergétique (doctrine v1.1 §10).

Mirror Python du type TypeScript exposé dans la doctrine §10. Tout
détecteur doit produire des `SolEventCard` complets (les 6 questions
doctrine §10 : quel fait / quel périmètre / quel impact / quelle action /
quelle source / quel niveau de confiance).

Frozen dataclass pour interdire la mutation post-création — un événement
est un fait observé à un instant t, pas un état mutable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Literal, Optional

# ── Types canoniques (doctrine §10) ─────────────────────────────────

EventType = Literal[
    "consumption_drift",  # dérive conso vs baseline
    "billing_anomaly",  # écart facture / surfacturation / doublon
    "compliance_deadline",  # échéance OPERAT / BACS / APER / DT trajectoire
    "contract_renewal",  # contrat arrivant à échéance
    "market_window",  # fenêtre achat / VNU / capacité Nov 2026
    "data_quality_issue",  # trous / doublons / valeurs aberrantes
    "flex_opportunity",  # éligibilité NEBCO / aFRR / Tempo
    "asset_registry_issue",  # PRM/PCE non rattaché, contrat orphelin
    "action_overdue",  # action plan en retard
]

EventSeverity = Literal["info", "watch", "warning", "critical"]

EventUnit = Literal["€", "kWh", "MWh", "kW", "kVA", "kgCO2e", "days", "%"]

EventPeriod = Literal["day", "week", "month", "year", "contract", "deadline"]

EventSourceSystem = Literal[
    "Enedis",
    "GRDF",
    "invoice",
    "GTB",
    "IoT",
    "RegOps",
    "EPEX",
    "manual",
    "benchmark",
]

EventConfidence = Literal["high", "medium", "low"]

EventOwnerRole = Literal["DAF", "Energy Manager", "Site Manager", "Admin", "Operator"]


# ── Sub-objects (doctrine §10) ──────────────────────────────────────


@dataclass(frozen=True)
class EventImpact:
    """Impact estimé : valeur + unité + période. Doctrine §6 P13 « pas de KPI magique » :
    `value=None` autorisé pour les événements sans chiffrage immédiat (ex: data_quality_issue
    avant calcul de perte). Dans ce cas le frontend affiche « impact à qualifier »."""

    value: Optional[float]
    unit: EventUnit
    period: EventPeriod


@dataclass(frozen=True)
class EventSource:
    """Source de l'événement — système + horodatage + niveau de confiance.

    Doctrine v1.1 §7.1 contrat de confiance data : tout événement doit porter
    son identité (source primaire, dernière mise à jour, confiance évaluable).
    """

    system: EventSourceSystem
    last_updated_at: datetime
    confidence: EventConfidence


@dataclass(frozen=True)
class EventAction:
    """Action recommandée associée à l'événement — label + route deep-link."""

    label: str
    route: str
    owner_role: Optional[EventOwnerRole] = None


@dataclass(frozen=True)
class EventLinkedAssets:
    """Périmètre métier : org / portefeuille / sites / bâtiments / compteurs / factures / contrats.

    Doctrine §10 « quel périmètre est concerné ? » — un événement est rattaché
    à au moins `org_id`. Les autres champs sont optionnels selon granularité.
    """

    org_id: int
    portfolio_id: Optional[int] = None
    site_ids: list[int] = field(default_factory=list)
    building_ids: list[int] = field(default_factory=list)
    meter_ids: list[int] = field(default_factory=list)
    invoice_ids: list[int] = field(default_factory=list)
    contract_ids: list[int] = field(default_factory=list)


# ── Card (doctrine §10) ─────────────────────────────────────────────


@dataclass(frozen=True)
class SolEventCard:
    """Événement énergétique typé — doctrine v1.1 §10.

    Format obligatoire pour tout événement poussé par le moteur proactif
    (chantier α). Chaque champ répond à une des 6 questions doctrinales
    §10 (quel fait / périmètre / impact / action / source / confiance).
    """

    id: str  # identifiant stable (ex: "compliance_deadline:org:1:dt_2030")
    event_type: EventType
    severity: EventSeverity
    title: str  # phrase courte, narrative §5 doctrine (pas d'acronyme brut)
    narrative: str  # 1-2 phrases « ce qui se passe + pourquoi c'est important »
    impact: EventImpact
    source: EventSource
    action: EventAction
    linked_assets: EventLinkedAssets

    def to_dict(self) -> dict:
        """Sérialisation JSON-safe (datetime ISO, dataclasses dict)."""
        d = asdict(self)
        d["source"]["last_updated_at"] = self.source.last_updated_at.isoformat()
        return d


# ── Mapping severity → tone NarrativeWeekCard (SoT cross-stack) ──────
# Source de vérité unique consommée par event_service.to_narrative_week_cards
# (backend) ET frontend/src/domain/events/eventTypes.js mirror SEVERITY_TO_CARD_TYPE.
# Toute évolution doit être faite ici en premier puis mirror JS aligné.
SEVERITY_TO_CARD_TYPE: dict[EventSeverity, str] = {
    "critical": "todo",
    "warning": "todo",
    "watch": "watch",
    "info": "good_news",
}
