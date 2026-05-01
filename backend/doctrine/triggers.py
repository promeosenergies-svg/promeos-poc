"""Triggers narratifs — Sprint Refonte Narrative dynamique Phase 3.1.

Mappe les **9 event_types canoniques** du moteur `event_bus` (cf
`services/event_bus/types.py:EventType`) vers les **6 déclencheurs cibles
narratifs** issus des maquettes `narrative-{grand-groupe,commerce,erp}.html`.

## Pourquoi 9 → 6 ?

Le moteur d'événements détecte tout (data quality, asset registry, flex…)
mais la narrative CFO doit **hiérarchiser** : seuls les déclencheurs avec
impact business immédiat méritent une phrase. Les autres restent dans
`<SolEventStream>` pile pour drill-down, pas dans le body narratif.

## 6 déclencheurs cibles + priorité (Option 4.C)

| Priorité | Trigger | Origine | Sens éditorial |
|---|---|---|---|
| 1 | `DT_TRAJECTORY_DRIFT` | consumption_drift | « sites en dérive vs trajectoire 2030 » |
| 2 | `MAJOR_ANOMALY` | billing_anomaly + action_overdue | « anomalie facturation / action critique en retard » |
| 3 | `EXPOSURE_VARIATION` | (calculé via weekly_deltas) | « exposition financière S-1 » |
| 4 | `AUDIT_DEADLINE_IMMINENT` | compliance_deadline | « échéance OPERAT/BACS/APER » |
| 5 | `PURCHASE_WINDOW_OPEN` | contract_renewal + market_window | « fenêtre achat / VNU / capacité » |
| 6 | `COMPLIANCE_THRESHOLD_CROSSED` | (calculé via score) | « score conformité franchit 70 / 50 / 25 » |

## Triggers masqués par typologie (doctrine §11.3)

- **COMMERCE** : pas de `COMPLIANCE_THRESHOLD_CROSSED` (score abstrait pour
  un commerçant — sera remplacé par "+X €/mois" Phase 4 V2). Pas de
  `EXPOSURE_VARIATION` (remplacé par variation coût direct).
- **ERP** : tous actifs (directeur d'établissement public a besoin du
  registre réglementaire complet).
- **GRAND_GROUPE** : tous actifs (CFO = audience experte).

## V2 (Sprint Q3 2026)

Ajout des typologies PME_TERTIAIRE et INDUSTRIE — un nouveau ensemble de
triggers masqués sera défini selon les retours panel.

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 3.1.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from doctrine.naf_to_typology import OrganizationTypology


# ─── 6 déclencheurs cibles narratifs ───────────────────────────────────────


class TriggerType(str, Enum):
    """6 déclencheurs narratifs canoniques (priorité dans `TRIGGER_PRIORITY`)."""

    DT_TRAJECTORY_DRIFT = "dt_trajectory_drift"
    MAJOR_ANOMALY = "major_anomaly"
    EXPOSURE_VARIATION = "exposure_variation"
    AUDIT_DEADLINE_IMMINENT = "audit_deadline_imminent"
    PURCHASE_WINDOW_OPEN = "purchase_window_open"
    COMPLIANCE_THRESHOLD_CROSSED = "compliance_threshold_crossed"


# ─── Priorités (1 = plus urgent, 6 = moins urgent) ─────────────────────────


TRIGGER_PRIORITY: dict[TriggerType, int] = {
    TriggerType.DT_TRAJECTORY_DRIFT: 1,
    TriggerType.MAJOR_ANOMALY: 2,
    TriggerType.EXPOSURE_VARIATION: 3,
    TriggerType.AUDIT_DEADLINE_IMMINENT: 4,
    TriggerType.PURCHASE_WINDOW_OPEN: 5,
    TriggerType.COMPLIANCE_THRESHOLD_CROSSED: 6,
}


# ─── Mapping 9 event_types canoniques → 6 triggers narratifs ───────────────


# `event_type` est le champ canonique de `SolEventCard` (cf
# `services/event_bus/types.py:EventType`). Le mapping ici résume les 9
# détecteurs vers les 6 triggers narratifs cibles. `None` = détecteur
# masqué de la narrative (reste affiché dans <SolEventStream> pile).
EVENT_TYPE_TO_TRIGGER: dict[str, Optional[TriggerType]] = {
    # Conso → trajectoire 2030
    "consumption_drift": TriggerType.DT_TRAJECTORY_DRIFT,
    # Anomalies majeures
    "billing_anomaly": TriggerType.MAJOR_ANOMALY,
    "action_overdue": TriggerType.MAJOR_ANOMALY,
    # Échéances réglementaires
    "compliance_deadline": TriggerType.AUDIT_DEADLINE_IMMINENT,
    # Achat / marché
    "contract_renewal": TriggerType.PURCHASE_WINDOW_OPEN,
    "market_window": TriggerType.PURCHASE_WINDOW_OPEN,
    # Détecteurs masqués de la narrative (gardés pour <SolEventStream>)
    "data_quality_issue": None,  # technique, pas saillant CFO
    "asset_registry_issue": None,  # technique, pas saillant CFO
    "flex_opportunity": None,  # opportunité, pas un déclencheur urgent
}


# ─── Triggers masqués par typologie (doctrine §11.3) ───────────────────────


MASKED_TRIGGERS_BY_TYPOLOGY: dict[OrganizationTypology, set[TriggerType]] = {
    OrganizationTypology.COMMERCE: {
        # Score abstrait pour un commerçant — sera remplacé par variation
        # coût direct en Phase 4 V2 ("+X €/mois").
        TriggerType.COMPLIANCE_THRESHOLD_CROSSED,
        # Exposition réglementaire = jargon CFO ; commerçant pense en €
        # de surcoût direct, pas en sanction réglementaire prospective.
        TriggerType.EXPOSURE_VARIATION,
    },
    OrganizationTypology.ERP: set(),
    OrganizationTypology.GRAND_GROUPE: set(),
    # Phase 9.B — ETI_TERTIAIRE : tous triggers actifs (audience expert-praticien)
    OrganizationTypology.ETI_TERTIAIRE: set(),
    OrganizationTypology.UNKNOWN: set(),  # Conservateur — tout actif si on ne sait pas
}


__all__ = [
    "TriggerType",
    "TRIGGER_PRIORITY",
    "EVENT_TYPE_TO_TRIGGER",
    "MASKED_TRIGGERS_BY_TYPOLOGY",
]
