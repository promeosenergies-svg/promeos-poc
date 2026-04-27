"""Détecteur `consumption_drift` — chantier α Vague C ét12b.

Doctrine §10 event_type `consumption_drift` : émet un événement quand la
consommation d'un site dérive significativement vs baseline.

Audit personas Vague A → Vague C : compromis EM non levé (« amplitude
technique Δ%/σ Bill-Intel »). Ce détecteur résout en propageant
l'amplitude (Δ%, kWh, € perdu) et σ via `EventImpact` typé doctrine §10.

Réutilise SoT `consumption_diagnostic.get_insights_summary` (pas de SQL
métier inline — règle §10 P3 détecteur).

Logique :
- Consomme insights existants `ConsumptionInsight` (types : hors_horaires,
  base_load, pointe, derive, data_gap)
- Top 2 insights actifs par estimated_loss_eur descendant (priorité CFO €)
- 1 événement par insight, severity dérivée :
  - estimated_loss_eur >= 5 k€ → critical
  - >= 1 k€ → warning
  - >= 200 € → watch
  - sinon ignoré (densification SolWeekCards)

Impact typé :
- value = estimated_loss_eur (€/an estimé)
- mitigation.npv_eur = même valeur (récupérable à 1 an si action prise)
- mitigation.payback_months = 1 (action comportementale immédiate)
- linked_assets.site_ids = [site_concerné]
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..freshness import compute_freshness
from ..types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventMitigation,
    EventSource,
    SolEventCard,
)

# Seuils € EM/CFO mid-market (cohérent billing_anomaly_detector ét12a).
_THRESHOLD_CRITICAL_EUR = 5_000.0
_THRESHOLD_WARNING_EUR = 1_000.0
_THRESHOLD_WATCH_EUR = 200.0

# Mapping insight.type → titre narratif doctrine §10 (transformation acronymes).
_TYPE_TO_TITLE: dict[str, str] = {
    "hors_horaires": "Consommation hors horaires d'occupation",
    "base_load": "Talon de consommation élevé",
    "pointe": "Pointe de consommation anormale",
    "derive": "Dérive progressive de consommation",
    "data_gap": "Données de consommation incomplètes",
}


def _severity_for_loss(loss_eur: float) -> str | None:
    """Mappe perte estimée → severity doctrine §10."""
    if loss_eur >= _THRESHOLD_CRITICAL_EUR:
        return "critical"
    if loss_eur >= _THRESHOLD_WARNING_EUR:
        return "warning"
    if loss_eur >= _THRESHOLD_WATCH_EUR:
        return "watch"
    return None


def detect(db: Session, org_id: int) -> list[SolEventCard]:
    """Émet 0..2 événements `consumption_drift` (top insights actifs).

    Doctrine §10 « 6 questions » répondues par insight :
    - quel fait : type insight (hors_horaires, base_load, pointe, derive, data_gap)
    - quel périmètre : site_id concerné (linked_assets)
    - quel impact : € estimé (value) + Δ% si présent (narrative)
    - quelle action : route /diagnostic-conso?site_id=X
    - quelle source : consumption_diagnostic (ConsumptionInsight backend)
    - quelle confiance : depuis insight.severity → mapping confidence
    """
    # Imports locaux pour éviter cycle (services/consumption → narrative → event_bus)
    from services.consumption_diagnostic import get_insights_summary

    summary = get_insights_summary(db, org_id)
    raw_insights = summary.get("insights", [])

    if not raw_insights:
        return []

    # Trier par perte décroissante, garder top 2 (focus CFO €)
    insights_sorted = sorted(
        (i for i in raw_insights if (i.get("estimated_loss_eur") or 0) > 0),
        key=lambda i: i.get("estimated_loss_eur") or 0,
        reverse=True,
    )[:2]

    now = datetime.now(timezone.utc)
    events: list[SolEventCard] = []

    for insight in insights_sorted:
        loss_eur = float(insight.get("estimated_loss_eur") or 0)
        severity = _severity_for_loss(loss_eur)
        if severity is None:
            continue

        type_code = insight.get("type", "derive")
        title = _TYPE_TO_TITLE.get(type_code, "Dérive de consommation détectée")
        site_id = insight.get("site_id")
        site_label = insight.get("site_label") or insight.get("site_name") or f"site #{site_id}"

        # Amplitude technique extraite des metrics si disponible (compromis EM)
        metrics = insight.get("metrics") or {}
        delta_pct = metrics.get("delta_pct") or metrics.get("drift_pct")
        amplitude_phrase = ""
        if delta_pct is not None:
            amplitude_phrase = f" Écart {delta_pct:+.1f}% vs baseline."
        elif insight.get("estimated_loss_kwh"):
            amplitude_phrase = f" Surconsommation estimée : {int(insight['estimated_loss_kwh'])} kWh."

        # Mapping severity insight (low/medium/high/critical) → confidence
        insight_severity = (insight.get("severity") or "medium").lower()
        confidence = "high" if insight_severity in ("high", "critical") else "medium"

        # Vague C ét12d (audit Marie/EM P0-3) : freshness depuis l'horodatage
        # réel de la donnée IoT/Enedis si disponible. Source IoT = TTL 1h
        # (temps réel attendu), source Enedis = TTL 24h (CDC J+1).
        source_system = "IoT" if metrics else "Enedis"
        insight_updated_raw = insight.get("updated_at") or insight.get("computed_at")
        if isinstance(insight_updated_raw, str):
            try:
                insight_updated = datetime.fromisoformat(insight_updated_raw.replace("Z", "+00:00"))
            except ValueError:
                insight_updated = now
        elif isinstance(insight_updated_raw, datetime):
            insight_updated = insight_updated_raw
        else:
            insight_updated = now
        freshness = compute_freshness(source_system, insight_updated, now=now)

        events.append(
            SolEventCard(
                id=f"consumption_drift:org:{org_id}:site:{site_id}:{type_code}",
                event_type="consumption_drift",
                severity=severity,
                title=f"{title} — {site_label}",
                narrative=(
                    f"{insight.get('message') or 'Dérive consommation détectée'}.{amplitude_phrase} "
                    f"Action recommandée pour récupérer ~{int(loss_eur):,} €/an."
                ).replace(",", " "),  # FR : séparateur millier = espace
                impact=EventImpact(
                    value=loss_eur,
                    unit="€",
                    period="year",
                    mitigation=EventMitigation(
                        capex_eur=None,  # action comportementale (consignes, horaires)
                        payback_months=1,  # impact immédiat dès correction
                        npv_eur=loss_eur,  # récupérable à 1 an
                        npv_horizon_year=now.year,
                    ),
                ),
                source=EventSource(
                    system=source_system,  # type: ignore[arg-type]
                    last_updated_at=insight_updated,
                    confidence=confidence,  # type: ignore[arg-type]
                    freshness_status=freshness,
                ),
                action=EventAction(
                    label="Voir le diagnostic",
                    route=f"/diagnostic-conso?site_id={site_id}" if site_id else "/diagnostic-conso",
                    owner_role="Energy Manager",
                ),
                linked_assets=EventLinkedAssets(
                    org_id=org_id,
                    site_ids=[site_id] if site_id else [],
                ),
            )
        )

    return events
