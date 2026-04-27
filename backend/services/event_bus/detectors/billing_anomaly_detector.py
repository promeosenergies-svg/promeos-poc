"""Détecteur `billing_anomaly` — chantier α Vague C ét12a.

Doctrine §10 event_type `billing_anomaly` : émet un événement par seuil
critique de pertes facturation détectées par le shadow billing v4.2.

Audit personas Vague C ét11 — convergence CFO + EM + Doctrine :
- **CFO** : cash ~144-216 k€/an récupérable (§10 P9 « preuve de valeur »)
- **EM** : amplitude technique sur anomalies (compromis Vague A non levé)
- **Doctrine §14 T8** : preuve de valeur multi-source (Bill-Intel + RegOps)

Réutilise `losses_service.compute_billing_losses_summary` (SoT canonique
ét7') — règle d'or détecteur §10 « pas de SQL métier inline ».

Pattern mitigation EventImpact (ét11bis P0-4) : si `recovery_rate_pct`
disponible, on calcule un payback indicatif basé sur l'historique
(`payback_avg_days`) pour produire un événement CODIR-ready.

Seuils (constantes locales, pas inline magic) :
- `_THRESHOLD_CRITICAL_EUR=10_000` : pertes ouvertes > 10 k€ → critical
- `_THRESHOLD_WARNING_EUR=2_000` : pertes ouvertes > 2 k€ → warning
- `_THRESHOLD_INFO_EUR=500` : pertes ouvertes > 500 € → watch
- En-dessous : pas d'événement (le SolWeekCards densifie avec fallback)
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventMitigation,
    EventSource,
    SolEventCard,
)

# Seuils CFO B2B PROMEOS (mid-market 5-200 sites). Ajustables sans
# casser le contrat doctrine §10 — signal de tri éditorial uniquement.
_THRESHOLD_CRITICAL_EUR = 10_000.0
_THRESHOLD_WARNING_EUR = 2_000.0
_THRESHOLD_WATCH_EUR = 500.0


def detect(db: Session, org_id: int) -> list[SolEventCard]:
    """Émet 0..2 événements `billing_anomaly` selon volume pertes ouvertes.

    Logique :
    - Pertes ouvertes >= 10 k€ → 1 événement critical (CFO P0)
    - Pertes ouvertes >= 2 k€  → 1 événement warning
    - Pertes ouvertes >= 500 € → 1 événement watch
    - Reclaim YTD > 0 → 1 événement info (good_news : « X k€ déjà récupérés »)

    Doctrine §10 « 6 questions » :
    - quel fait : N anomalies ouvertes pour X € pertes
    - quel périmètre : org (futurs : site_ids via groupby — Vague C ét13+)
    - quel impact : montant € (period=year) + mitigation payback si data
    - quelle action : route /bill-intel + owner DAF
    - quelle source : losses_service (Bill-Intel shadow billing v4.2)
    - quelle confiance : depuis losses.payback_provenance.confidence
    """
    # Imports locaux pour éviter cycle (services/billing → narrative → event_bus)
    from services.billing.losses_service import (
        compute_billing_losses_summary,
        fmt_payback_human,
    )

    losses = compute_billing_losses_summary(db, org_id)
    now = datetime.now(timezone.utc)
    events: list[SolEventCard] = []

    # ── Événement principal selon volume pertes ouvertes ──
    perte_open = losses.perte_open_eur
    if perte_open > 0:
        if perte_open >= _THRESHOLD_CRITICAL_EUR:
            severity = "critical"
            title_prefix = "Pertes facturation critiques"
        elif perte_open >= _THRESHOLD_WARNING_EUR:
            severity = "warning"
            title_prefix = "Pertes facturation à contester"
        elif perte_open >= _THRESHOLD_WATCH_EUR:
            severity = "watch"
            title_prefix = "Pertes facturation à surveiller"
        else:
            severity = None  # pas d'événement sous le seuil watch
            title_prefix = ""

        if severity is not None:
            # Mitigation : si on a un payback observé, calculer payback proxy
            # pour CFO arbitrage. payback_months = round(payback_avg_days / 30)
            mitigation = None
            if losses.payback_avg_days is not None and losses.payback_avg_days > 0:
                mitigation = EventMitigation(
                    capex_eur=None,  # pas de CAPEX pour contestation facture (juridique)
                    payback_months=max(1, round(losses.payback_avg_days / 30)),
                    npv_eur=perte_open,  # NPV = pertes récupérables (taux 0% à 1 an)
                    npv_horizon_year=now.year,
                )

            payback_str = fmt_payback_human(losses.payback_avg_days)
            payback_phrase = f" Payback moyen observé : {payback_str}." if losses.payback_avg_days is not None else ""

            events.append(
                SolEventCard(
                    id=f"billing_anomaly:org:{org_id}:open",
                    event_type="billing_anomaly",
                    severity=severity,
                    title=f"{title_prefix} : {losses.nb_open} anomalie{'s' if losses.nb_open > 1 else ''}",
                    narrative=(
                        f"{losses.nb_open} anomalie{'s' if losses.nb_open > 1 else ''} "
                        "détectée"
                        f"{'s' if losses.nb_open > 1 else ''} sur vos factures par le "
                        f"shadow billing v4.2 — pertes estimées à récupérer.{payback_phrase}"
                    ),
                    impact=EventImpact(
                        value=perte_open,
                        unit="€",
                        period="year",
                        mitigation=mitigation,
                    ),
                    source=EventSource(
                        system="invoice",
                        last_updated_at=losses.losses_provenance.computed_at,
                        confidence=losses.losses_provenance.confidence,  # type: ignore[arg-type]
                        freshness_status="fresh",  # losses_service consomme les insights actuels
                    ),
                    action=EventAction(
                        label="Voir les anomalies",
                        route="/bill-intel",
                        owner_role="DAF",
                    ),
                    linked_assets=EventLinkedAssets(org_id=org_id),
                )
            )

    # ── Événement positif si récupérations YTD significatives ──
    if losses.reclaim_ytd_eur >= _THRESHOLD_WATCH_EUR:
        events.append(
            SolEventCard(
                id=f"billing_anomaly:org:{org_id}:reclaim_ytd",
                event_type="billing_anomaly",
                severity="info",
                title=f"{losses.nb_resolved} anomalie{'s' if losses.nb_resolved > 1 else ''} récupérée{'s' if losses.nb_resolved > 1 else ''} cette année",
                narrative=(
                    f"Récupérations validées YTD : reclaims confirmés grâce aux "
                    "contestations auprès des fournisseurs. Continuez le processus "
                    "shadow billing pour maintenir le rythme."
                ),
                impact=EventImpact(
                    value=losses.reclaim_ytd_eur,
                    unit="€",
                    period="year",
                ),
                source=EventSource(
                    system="invoice",
                    last_updated_at=losses.recovery_provenance.computed_at,
                    confidence=losses.recovery_provenance.confidence,  # type: ignore[arg-type]
                    freshness_status="fresh",
                ),
                action=EventAction(
                    label="Voir le bilan reclaims",
                    route="/bill-intel",
                    owner_role="DAF",
                ),
                linked_assets=EventLinkedAssets(org_id=org_id),
            )
        )

    return events
