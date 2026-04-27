"""Détecteur `data_quality_issue` — chantier α Vague C ét13d.

Doctrine §10 event_type `data_quality_issue` : émet un événement quand
le diagnostic de consommation détecte des trous de données significatifs
(insights type='data_gap' produits par `consumption_diagnostic`).

Sans qualité de données, tous les autres détecteurs perdent leur
fiabilité (z-score faussé, drift sous-estimé, mitigation invalide).
C'est le détecteur "garde-fou data" qui prévient la dégradation
silencieuse du moteur d'événements.

Réutilise SoT canonique `consumption_diagnostic.get_insights_summary`
(règle d'or §10 P3). Owner Energy Manager (responsabilité collecte data).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..freshness import compute_freshness
from ..types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventSource,
    SolEventCard,
)

# Seuils de criticité basés sur le pourcentage de données manquantes
# (calculé par _detect_data_gaps dans consumption_diagnostic).
_THRESHOLD_CRITICAL_PCT = 30.0  # > 30 % manquant → diagnostic invalide
_THRESHOLD_WARNING_PCT = 15.0
_THRESHOLD_WATCH_PCT = 5.0


def _severity_for_gap(missing_pct: float) -> str | None:
    """Mappe pourcentage manquant → severity doctrine §10."""
    if missing_pct >= _THRESHOLD_CRITICAL_PCT:
        return "critical"
    if missing_pct >= _THRESHOLD_WARNING_PCT:
        return "warning"
    if missing_pct >= _THRESHOLD_WATCH_PCT:
        return "watch"
    return None


def detect(db: Session, org_id: int) -> list[SolEventCard]:
    """Émet 0..2 événements `data_quality_issue` (top sites avec trous data).

    Doctrine §10 « 6 questions » :
    - quel fait : trous data détectés (% manquant, période)
    - quel périmètre : site_id concerné
    - quel impact : confiance dégradée (pas de chiffre €, c'est un méta-impact)
    - quelle action : route /diagnostic-conso?site_id=X (vue détaillée)
    - quelle source : consumption_diagnostic (insight type=data_gap)
    - quelle confiance : high (la détection des gaps est déterministe)
    """
    # Imports locaux pour éviter cycle (services/consumption → narrative → event_bus)
    from services.consumption_diagnostic import get_insights_summary

    summary = get_insights_summary(db, org_id)
    raw_insights = summary.get("insights", [])

    # Filtrer les insights de type "data_gap" uniquement
    gaps = [i for i in raw_insights if i.get("type") == "data_gap"]
    if not gaps:
        return []

    # Trier par % manquant descendant, garder top 2 (densification §5)
    gaps_sorted = sorted(
        gaps,
        key=lambda i: (i.get("metrics") or {}).get("missing_pct", 0),
        reverse=True,
    )[:2]

    now = datetime.now(timezone.utc)
    events: list[SolEventCard] = []

    for insight in gaps_sorted:
        metrics = insight.get("metrics") or {}
        missing_pct = float(metrics.get("missing_pct") or 0)
        severity = _severity_for_gap(missing_pct)
        if severity is None:
            continue

        site_id = insight.get("site_id")
        site_label = insight.get("site_label") or insight.get("site_name") or f"site #{site_id}"
        period_days = int(metrics.get("period_days") or 30)

        events.append(
            SolEventCard(
                id=f"data_quality_issue:org:{org_id}:site:{site_id}:data_gap",
                event_type="data_quality_issue",
                severity=severity,  # type: ignore[arg-type]
                title=f"Données incomplètes — {site_label}",
                narrative=(
                    f"{missing_pct:.0f} % de données manquantes sur les {period_days} derniers "
                    f"jours sur ce site. {insight.get('message') or ''} "
                    "Tant que les trous ne sont pas comblés, les analyses de dérive et "
                    "de pertes restent estimées avec une fiabilité dégradée."
                ),
                impact=EventImpact(
                    value=missing_pct,  # impact = % manquant (proxy data quality)
                    unit="%",
                    period="month",
                ),
                source=EventSource(
                    system="Enedis",  # source primaire CDC quand existe
                    last_updated_at=now,
                    confidence="high",  # détection déterministe (gaps observés)
                    freshness_status=compute_freshness("Enedis", now, now=now),
                    methodology=(
                        "Trous de données détectés sur les relevés horaires Enedis (CDC J+1) "
                        "ou le sous-comptage IoT. Un site avec > 5 % de données manquantes "
                        "ne permet plus d'établir une signature énergétique fiable "
                        "(seuils ISO 50001 §A.6). Action : demander une réémission Enedis "
                        "ou contrôler la connectivité GTB/IoT du site."
                    ),
                ),
                action=EventAction(
                    label="Voir le diagnostic data",
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
