"""
PROMEOS — billing_kpis_cockpit_service (P0 cleanup cockpit, 2026-05-25).

Service dédié pour agréger les KPIs Bill Intelligence à afficher dans le
Cockpit Stratégique. Doctrine §8.1 : zéro logique métier frontend — le
frontend rend uniquement `payload.billing_kpis` sans recalcul.

KPIs exposés (chaque entrée contient : id, label_fr, value, unit, source,
formula, period, scope, link_to) :
  1. surfacturations_a_contester (€)
  2. anomalies_ouvertes (count)
  3. anomalies_par_energie ({elec, gaz})
  4. preuves_attendues (count) — agrégat conformité × billing
  5. actions_facturation_ouvertes (count)

Liens (link_to) pour le cockpit :
  - /bill-intel (vue Anomalies)
  - /centre-action?domain=facturation (file prioritaire Facturation)
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import BillingInsight, EnergyInvoice, EnergyContract
from models import not_deleted
from models.enums import InsightStatus
from models.v4.action_center_items import ActionCenterItem
from models.v4.enums import Domain, LifecycleState
from services.scope_utils import sites_for_org_query as _sites_for_org


def _compute_anomalies_ouvertes(db: Session, site_ids: list[int]) -> int:
    """Compte les insights billing ouverts (open + in_progress)."""
    if not site_ids:
        return 0
    return (
        not_deleted(db.query(func.count(BillingInsight.id)), BillingInsight)
        .filter(
            BillingInsight.site_id.in_(site_ids),
            BillingInsight.insight_status.in_([InsightStatus.OPEN, InsightStatus.ACK]),
        )
        .scalar()
        or 0
    )


def _compute_anomalies_par_energie(db: Session, site_ids: list[int]) -> dict[str, int]:
    """Compte les insights billing ouverts groupés par energy_type via le contrat
    rattaché à la facture. Si pas de contrat ou pas d'énergie : 'inconnu'."""
    if not site_ids:
        return {"elec": 0, "gaz": 0, "inconnu": 0}

    rows = (
        not_deleted(
            db.query(EnergyContract.energy_type, func.count(BillingInsight.id)),
            BillingInsight,
        )
        .outerjoin(EnergyInvoice, EnergyInvoice.id == BillingInsight.invoice_id)
        .outerjoin(EnergyContract, EnergyContract.id == EnergyInvoice.contract_id)
        .filter(
            BillingInsight.site_id.in_(site_ids),
            BillingInsight.insight_status.in_([InsightStatus.OPEN, InsightStatus.ACK]),
        )
        .group_by(EnergyContract.energy_type)
        .all()
    )

    breakdown = {"elec": 0, "gaz": 0, "inconnu": 0}
    for energy_type, count in rows:
        if energy_type is None:
            breakdown["inconnu"] += count
            continue
        # EnergyType enum a la valeur "electricite" / "gaz"
        val = energy_type.value if hasattr(energy_type, "value") else str(energy_type)
        if "electric" in val.lower() or val.lower() == "elec":
            breakdown["elec"] += count
        elif "gaz" in val.lower() or "gas" in val.lower():
            breakdown["gaz"] += count
        else:
            breakdown["inconnu"] += count
    return breakdown


def _compute_surfacturations_a_contester(db: Session, site_ids: list[int]) -> float:
    """Somme des estimated_loss_eur des insights ouverts non résolus.

    SoT : BillingInsight.estimated_loss_eur (issus de shadow_billing_v2 delta_ttc).
    Cohérent avec billing_service.get_billing_summary().total_estimated_loss_eur.
    """
    if not site_ids:
        return 0.0
    total = (
        not_deleted(
            db.query(func.coalesce(func.sum(BillingInsight.estimated_loss_eur), 0.0)),
            BillingInsight,
        )
        .filter(
            BillingInsight.site_id.in_(site_ids),
            BillingInsight.insight_status.in_([InsightStatus.OPEN, InsightStatus.ACK]),
        )
        .scalar()
        or 0.0
    )
    return round(float(total), 2)


def _compute_actions_facturation_ouvertes(db: Session, org_id: int) -> int:
    """Compte les ActionCenterItem domain=facturation non clôturés.

    P2-B C5 (sync anomalie→action) : chaque BillingInsight valorisable crée
    un ActionCenterItem. Ici on compte ceux encore ouverts.
    """
    return (
        db.query(func.count(ActionCenterItem.id))
        .filter(
            ActionCenterItem.organisation_id == org_id,
            ActionCenterItem.domain == Domain.FACTURATION.value,
            ActionCenterItem.lifecycle_state != LifecycleState.CLOSED.value,
        )
        .scalar()
        or 0
    )


def compute_billing_kpis_cockpit(db: Session, org_id: int) -> dict:
    """Retourne le payload billing_kpis pour le cockpit.

    Structure (chaque KPI documenté avec source/formule/unité/période/périmètre) :
    {
        "kpis": [
            {
                "id": "surfacturations_a_contester",
                "label_fr": "Surfacturations à contester",
                "value": 1234.56,
                "unit": "EUR",
                "source": "BillingInsight.estimated_loss_eur",
                "formula": "Σ insights ouverts (open + in_progress)",
                "period": "snapshot",
                "scope": "org",
                "link_to": "/bill-intel",
            },
            ...
        ],
        "links": {
            "bill_intel": "/bill-intel",
            "centre_action_facturation": "/centre-action?domain=facturation",
        },
    }
    """
    if not org_id:
        return {"kpis": [], "links": {}}

    site_ids = [s.id for s in _sites_for_org(db, org_id).with_entities(__import__('models', fromlist=['Site']).Site.id).all()]

    surfacturations = _compute_surfacturations_a_contester(db, site_ids)
    anomalies_ouvertes = _compute_anomalies_ouvertes(db, site_ids)
    anomalies_par_energie = _compute_anomalies_par_energie(db, site_ids)
    actions_ouvertes = _compute_actions_facturation_ouvertes(db, org_id)

    return {
        "kpis": [
            {
                "id": "surfacturations_a_contester",
                "label_fr": "Surfacturations à contester",
                "value": surfacturations,
                "unit": "EUR",
                "source": "BillingInsight.estimated_loss_eur",
                "formula": "Σ insights (status ∈ {open, ack}) sur sites du périmètre",
                "period": "snapshot",
                "scope": "org",
                "link_to": "/bill-intel",
            },
            {
                "id": "anomalies_ouvertes",
                "label_fr": "Anomalies factures ouvertes",
                "value": anomalies_ouvertes,
                "unit": "count",
                "source": "BillingInsight.id",
                "formula": "COUNT(insights status ∈ {open, ack})",
                "period": "snapshot",
                "scope": "org",
                "link_to": "/bill-intel",
            },
            {
                "id": "anomalies_par_energie",
                "label_fr": "Anomalies par énergie",
                "value": anomalies_par_energie,
                "unit": "count",
                "source": "BillingInsight × EnergyInvoice × EnergyContract.energy_type",
                "formula": "GROUP BY energy_type sur insights ouverts",
                "period": "snapshot",
                "scope": "org",
                "link_to": "/bill-intel",
            },
            {
                "id": "actions_facturation_ouvertes",
                "label_fr": "Actions facturation ouvertes",
                "value": actions_ouvertes,
                "unit": "count",
                "source": "ActionCenterItem (domain=facturation, lifecycle_state ≠ closed)",
                "formula": "COUNT(items domain=facturation non clôturés)",
                "period": "snapshot",
                "scope": "org",
                "link_to": "/centre-action?domain=facturation",
            },
        ],
        "links": {
            "bill_intel": "/bill-intel",
            "centre_action_facturation": "/centre-action?domain=facturation",
        },
    }
