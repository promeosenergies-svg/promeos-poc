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

# Doctrine v1.1 §7.2 statuts data obligatoires (mapping vers EventSource.freshness_status).
# - "fresh"     → donnée temps réel ou < TTL système (Enedis 24h, factures 7j…)
# - "stale"     → donnée valide mais ancienne (TTL dépassé, à rafraîchir)
# - "estimated" → donnée extrapolée (badge UI obligatoire §7.2)
# - "incomplete" → période ou périmètre partiel
# - "demo"      → donnée seed démonstration (badge visible §7.2)
EventFreshnessStatus = Literal["fresh", "stale", "estimated", "incomplete", "demo"]

EventOwnerRole = Literal["DAF", "Energy Manager", "Site Manager", "Admin", "Operator"]


# ── Sub-objects (doctrine §10) ──────────────────────────────────────


@dataclass(frozen=True)
class EventMitigation:
    """Optionnel : ratio CAPEX/payback/NPV pour décision arbitrage CFO.

    Sprint 2 Vague C ét11bis (audit CFO P0) : « le CFO décide toujours sur
    le ratio, jamais sur le risque brut ». Sans ces 3 champs, un événement
    `compliance_deadline` impact=1,5 M€/an ne dit pas si on doit dégager
    300 k€ ou 4 M€ de CAPEX. Tous champs optionnels — un événement n'a pas
    forcément de levier de mitigation chiffré.
    """

    capex_eur: Optional[float] = None  # Investissement requis pour éviter l'impact
    payback_months: Optional[int] = None  # Délai de retour sur investissement
    npv_eur: Optional[float] = None  # Valeur actualisée nette (taux d'actualisation 8% par défaut)
    npv_horizon_year: Optional[int] = None  # Horizon NPV (2030/2040/2050 typique)


@dataclass(frozen=True)
class EventImpact:
    """Impact estimé : valeur + unité + période + mitigation optionnelle.

    Doctrine §6 P13 « pas de KPI magique » : `value=None` autorisé pour les
    événements sans chiffrage immédiat (ex: data_quality_issue avant calcul
    de perte). Dans ce cas le frontend affiche « impact à qualifier ».

    Sprint 2 Vague C ét11bis : ajout `mitigation` optionnel (CFO arbitrage
    CAPEX). Backward-compatible avec ét11 — détecteurs existants ne le
    renseignent pas, futurs détecteurs (billing_anomaly, compliance_deadline
    avec étude TRI) le rempliront.
    """

    value: Optional[float]
    unit: EventUnit
    period: EventPeriod
    mitigation: Optional["EventMitigation"] = None


@dataclass(frozen=True)
class EventSource:
    """Source de l'événement — système + horodatage + niveau de confiance + statut.

    Doctrine v1.1 §7.1 contrat de confiance data : tout événement doit porter
    son identité (source primaire, dernière mise à jour, confiance évaluable,
    statut fraîcheur).

    Sprint 2 Vague C ét11bis : ajout `freshness_status` (audit doctrine P0
    pour atteindre 9+) — couvre §7.2 statuts obligatoires (Réel/Estimé/
    Incomplet/Stale/Démo). Frontend doit afficher un badge correspondant.
    """

    system: EventSourceSystem
    last_updated_at: datetime
    confidence: EventConfidence
    freshness_status: EventFreshnessStatus = "fresh"  # défaut sain : donnée temps réel/à jour


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
