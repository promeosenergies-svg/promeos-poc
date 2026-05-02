"""Pydantic schemas pour endpoint REST /api/v1/events/upcoming (Phase 1.A).

Mapping fidèle des dataclasses `SolEventCard` (event_bus/types.py) vers
des schemas Pydantic exposables via FastAPI / OpenAPI.

Une classmethod `from_sol_event_card` sur EventCardSchema préserve la
SoT type côté event_bus tout en sérialisant via Pydantic côté REST.

Réf : docs/adr/ADR-002-chantier-alpha-moteur-evenements.md (§endpoint).
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from services.event_bus.types import SolEventCard


# ── Sub-schemas (mirror dataclasses event_bus/types.py) ─────────────


class MitigationSchema(BaseModel):
    capex_eur: Optional[float] = None
    payback_months: Optional[int] = None
    npv_eur: Optional[float] = None
    npv_horizon_year: Optional[int] = None


class ImpactSchema(BaseModel):
    value: Optional[float]
    unit: str
    period: str
    mitigation: Optional[MitigationSchema] = None


class SourceSchema(BaseModel):
    system: str
    last_updated_at: datetime
    confidence: str
    freshness_status: str = "fresh"
    methodology: Optional[str] = None


class ActionSchema(BaseModel):
    label: str
    route: str
    owner_role: Optional[str] = None


class LinkedAssetsSchema(BaseModel):
    org_id: int
    portfolio_id: Optional[int] = None
    site_ids: List[int] = Field(default_factory=list)
    building_ids: List[int] = Field(default_factory=list)
    meter_ids: List[int] = Field(default_factory=list)
    invoice_ids: List[int] = Field(default_factory=list)
    contract_ids: List[int] = Field(default_factory=list)


# ── EventCardSchema (mirror SolEventCard) ───────────────────────────


class EventCardSchema(BaseModel):
    """Schema Pydantic mirror de la frozen dataclass `SolEventCard`."""

    id: str
    event_type: str
    severity: str
    title: str
    narrative: str
    impact: ImpactSchema
    source: SourceSchema
    action: ActionSchema
    linked_assets: LinkedAssetsSchema

    @classmethod
    def from_sol_event_card(cls, card: SolEventCard) -> "EventCardSchema":
        """Mapping fidèle dataclass → schema. Aucune transformation métier."""
        mitigation = None
        if card.impact.mitigation is not None:
            mitigation = MitigationSchema(
                capex_eur=card.impact.mitigation.capex_eur,
                payback_months=card.impact.mitigation.payback_months,
                npv_eur=card.impact.mitigation.npv_eur,
                npv_horizon_year=card.impact.mitigation.npv_horizon_year,
            )
        return cls(
            id=card.id,
            event_type=card.event_type,
            severity=card.severity,
            title=card.title,
            narrative=card.narrative,
            impact=ImpactSchema(
                value=card.impact.value,
                unit=card.impact.unit,
                period=card.impact.period,
                mitigation=mitigation,
            ),
            source=SourceSchema(
                system=card.source.system,
                last_updated_at=card.source.last_updated_at,
                confidence=card.source.confidence,
                freshness_status=card.source.freshness_status,
                methodology=card.source.methodology,
            ),
            action=ActionSchema(
                label=card.action.label,
                route=card.action.route,
                owner_role=card.action.owner_role,
            ),
            linked_assets=LinkedAssetsSchema(
                org_id=card.linked_assets.org_id,
                portfolio_id=card.linked_assets.portfolio_id,
                site_ids=list(card.linked_assets.site_ids),
                building_ids=list(card.linked_assets.building_ids),
                meter_ids=list(card.linked_assets.meter_ids),
                invoice_ids=list(card.linked_assets.invoice_ids),
                contract_ids=list(card.linked_assets.contract_ids),
            ),
        )


# ── Réponse endpoint ────────────────────────────────────────────────


class EventUpcomingResponse(BaseModel):
    """Réponse `GET /api/v1/events/upcoming`.

    Contrat ADR-002 §endpoint :
      - events : page courante (≤ limit)
      - next_cursor : cursor opaque pour page suivante (None si fin)
      - total : taille totale post-filtres
      - computed_at : horodatage UTC de la réponse
      - cache_ttl_seconds : TTL conseillé côté consommateur
    """

    events: List[EventCardSchema]
    next_cursor: Optional[str] = None
    total: int
    computed_at: datetime
    cache_ttl_seconds: int = 300
