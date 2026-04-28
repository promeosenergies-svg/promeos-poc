"""Détecteur `action_overdue` — chantier α Vague C ét13f.

Doctrine §10 event_type `action_overdue` : émet un événement quand un
ActionPlanItem dépasse sa due_date sans être résolu.

Bouclage du moteur d'événements : les autres détecteurs identifient des
opportunités/risques (compliance, billing, drift, flex, market, contract,
data_quality, asset_registry). action_overdue surveille l'EXÉCUTION
réelle de ces actions par les owners — le pilier "fermeture de boucle"
qui empêche le plan d'actions de se transformer en cimetière de tickets.

Owner : déduit de l'action elle-même (DAF, EM, Site Manager…) — fallback
DAF si absent. Severity dérivée du retard et de la priority initiale.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..freshness import compute_freshness
from ..types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventSource,
    SolEventCard,
)

# Vague E ét15 (audit P1 tier-2 étendu) : seuils externalisés YAML
# `action_overdue.overdue_*_days` (ADR-005 convention tier-2).


def _severity_for_overdue(days_overdue: int, priority: str, defaults=None) -> str | None:
    """Mappe (retard, priorité initiale) → severity doctrine §10.

    Une action critique en retard est toujours critique.
    Une action medium devient warning à J+7, critical à J+30.
    Une action low n'apparait qu'à J+30 en watch.

    Vague E ét15 : seuils injectés depuis YAML via `defaults` DTO.
    Fallback magic constants pour compat tests.
    """
    if defaults is None:
        critical_days, warning_days = 30, 7
    else:
        critical_days = defaults.overdue_critical_days
        warning_days = defaults.overdue_warning_days
    if priority in ("critical", "high"):
        if days_overdue >= 0:
            return "critical"
    if priority == "medium":
        if days_overdue >= critical_days:
            return "critical"
        if days_overdue >= warning_days:
            return "warning"
        if days_overdue >= 0:
            return "watch"
    if priority == "low":
        if days_overdue >= critical_days:
            return "watch"
    return None


def detect(db: Session, org_id: int) -> list[SolEventCard]:
    """Émet 0..3 événements `action_overdue` (top actions les plus en retard)."""
    # Imports locaux pour éviter cycle
    from config.mitigation_loader import get_action_overdue_defaults
    from models import EntiteJuridique, Portefeuille, Site
    from models.action_plan_item import ActionPlanItem

    ao_defaults = get_action_overdue_defaults()  # ét15 tier-2 étendu
    now = datetime.now(timezone.utc)
    today = now.date()

    # Charger les actions ouvertes/in_progress avec due_date passée
    # ActionPlanItem n'a pas org_id direct → join site_id
    overdue_actions = (
        db.query(ActionPlanItem)
        .join(Site, Site.id == ActionPlanItem.site_id)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .filter(ActionPlanItem.status.in_(("open", "in_progress", "reopened")))
        .filter(ActionPlanItem.due_date.isnot(None))
        .all()
    )

    # Ne garder que les actions effectivement en retard ou imminentes
    candidates = []
    for a in overdue_actions:
        # Normaliser due_date en date (compat datetime/date)
        due = a.due_date.date() if hasattr(a.due_date, "date") else a.due_date
        days_overdue = (today - due).days
        if days_overdue < 0:
            continue
        priority = (a.priority or "medium").lower()
        severity = _severity_for_overdue(days_overdue, priority, defaults=ao_defaults)
        if severity is None:
            continue
        candidates.append((a, days_overdue, severity))

    # Top 3 plus en retard (sort by days_overdue desc)
    candidates.sort(key=lambda x: x[1], reverse=True)
    candidates = candidates[:3]

    events: list[SolEventCard] = []
    for action, days_overdue, severity in candidates:
        # Owner role déduit de l'owner ActionPlanItem (string libre)
        # Fallback DAF si non renseigné. Mapping simple basé sur des tokens FR.
        owner_str = (action.owner or "").lower()
        if "energy" in owner_str or "manager" in owner_str or "ingénieur" in owner_str:
            owner_role = "Energy Manager"
        elif "site" in owner_str or "exploitation" in owner_str:
            owner_role = "Site Manager"
        else:
            owner_role = "DAF"

        retard_phrase = (
            f"depuis {days_overdue} jour{'s' if days_overdue > 1 else ''}" if days_overdue > 0 else "aujourd'hui"
        )

        # Impact = estimated_impact_eur de l'action si présent (sinon non chiffré)
        impact_value = float(action.estimated_impact_eur) if action.estimated_impact_eur else None

        events.append(
            SolEventCard(
                id=f"action_overdue:org:{org_id}:action:{action.id}",
                event_type="action_overdue",
                severity=severity,  # type: ignore[arg-type]
                title=f"Action en retard {retard_phrase} — {action.issue_label[:60]}",
                narrative=(
                    f"L'action « {action.issue_label} » (priorité {action.priority}, "
                    f"domaine {action.domain}) est en retard de {days_overdue} "
                    f"jour{'s' if days_overdue > 1 else ''}. "
                    f"{action.recommended_action or 'Reprogrammer ou réassigner cette action.'}"
                ),
                impact=EventImpact(
                    value=impact_value,
                    unit="€",
                    period="year",
                ),
                source=EventSource(
                    system="manual",  # action plan saisi/maintenu côté équipe
                    last_updated_at=now,
                    confidence="high",  # date due_date contractuelle
                    freshness_status=compute_freshness("manual", now, now=now),
                    methodology=(
                        f"ActionPlanItem id={action.id} status={action.status} "
                        f"due_date={action.due_date.date() if hasattr(action.due_date, 'date') else action.due_date} "
                        f"priority={action.priority}. Severity dérivée du couple "
                        "(retard en jours, priorité initiale) : critical/high → critique dès J+0, "
                        "medium → warning J+7 puis critical J+30, low → watch J+30."
                    ),
                ),
                action=EventAction(
                    label="Voir le plan d'actions",
                    route="/plan-actions",
                    owner_role=owner_role,  # type: ignore[arg-type]
                ),
                linked_assets=EventLinkedAssets(
                    org_id=org_id,
                    site_ids=[action.site_id] if action.site_id else [],
                ),
            )
        )

    return events
