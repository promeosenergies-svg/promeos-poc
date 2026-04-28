"""Détecteur `data_quality_issue` — chantier α Vague C ét13d / ét15.

Doctrine §10 event_type `data_quality_issue` : émet un événement quand
le diagnostic de consommation détecte des trous de données significatifs
(insights type='data_gap' produits par `consumption_diagnostic`).

Sans qualité de données, tous les autres détecteurs perdent leur
fiabilité (z-score faussé, drift sous-estimé, mitigation invalide).
C'est le détecteur "garde-fou data" qui prévient la dégradation
silencieuse du moteur d'événements.

Réutilise SoT canonique `consumption_diagnostic.get_insights_summary`
(règle d'or §10 P3). Owner Energy Manager (responsabilité collecte data).

## Vague E ét15 — Ownership PHOTO D020 obsolète (clarification audit EM)

L'EM a signalé un risque de doublon entre `data_quality_issue` et
`asset_registry_issue` pour le contrôle « PHOTO D020 SGE/Enedis obsolète
> 90 jours ». **Décision tranchée** :

  - **`data_quality_issue` est responsable de la fraîcheur des données
    SGE/Enedis (D020, R6X CDC, etc.)** car l'âge d'une PHOTO impacte la
    qualité des analyses (signature énergétique, dérive, factures shadow).
  - **`asset_registry_issue` reste responsable de la cohérence
    structurelle du registre** (PRM/PCE rattachement, GRD code, contrats
    orphelins) — la fraîcheur des données réseau n'y figure pas.

Le détecteur `data_quality_issue` consomme tout insight type matchant
`('data_gap', 'photo_d020_stale', 'sge_snapshot_stale')` produit en
amont par `consumption_diagnostic` (extension future, pas de mock ici).
Le test `test_data_quality_owns_photo_d020_freshness_not_asset_registry`
verrouille cette frontière de responsabilité.
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

# Vague E ét15 (audit P1 tier-2 étendu) : seuils externalisés YAML
# `data_quality.threshold_*_pct` (ADR-005 convention tier-2).


def _severity_for_gap(missing_pct: float, defaults=None) -> str | None:
    """Mappe pourcentage manquant → severity doctrine §10.

    Vague E ét15 : seuils injectés depuis YAML via `defaults` DTO.
    Fallback magic constants conservé pour compat tests.
    """
    if defaults is None:
        critical, warning, watch = 30.0, 15.0, 5.0
    else:
        critical = defaults.threshold_critical_pct
        warning = defaults.threshold_warning_pct
        watch = defaults.threshold_watch_pct
    if missing_pct >= critical:
        return "critical"
    if missing_pct >= warning:
        return "warning"
    if missing_pct >= watch:
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
    from config.mitigation_loader import get_data_quality_defaults
    from services.consumption_diagnostic import get_insights_summary

    dq_defaults = get_data_quality_defaults()  # ét15 tier-2 étendu
    summary = get_insights_summary(db, org_id)
    raw_insights = summary.get("insights", [])

    # ét15 (P1 #3 audit EM) : ownership PHOTO D020 obsolète clarifié
    # vs asset_registry_issue. Tout insight de type data freshness consommé
    # par ce détecteur (data_gap = trous CDC, photo_d020_stale = PHOTO SGE
    # > 90j, sge_snapshot_stale = R6X obsolète). asset_registry_issue ne
    # touche PAS la fraîcheur de la donnée réseau (responsabilité distincte).
    _DATA_FRESHNESS_TYPES = ("data_gap", "photo_d020_stale", "sge_snapshot_stale")
    gaps = [i for i in raw_insights if i.get("type") in _DATA_FRESHNESS_TYPES]
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
        severity = _severity_for_gap(missing_pct, defaults=dq_defaults)
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
