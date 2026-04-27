"""Détecteur pilote `compliance_deadline` — chantier α MVP (Vague C ét11).

Doctrine §10 event_type `compliance_deadline` : émet un événement quand
des sites sont non-conformes ou à risque vis-à-vis du Décret Tertiaire,
avec calcul d'impact financier sourcé `backend/doctrine/constants.py`
(DT_PENALTY_EUR=7500, DT_PENALTY_AT_RISK_EUR=3750).

Remplace le calcul inline `narrative_generator._build_cockpit_daily`
lignes 405-435 (week-cards statiques) par un événement typé doctrine §10.

Pattern futur (Vague C ét12+) : tous les autres détecteurs suivent ce
modèle (consumption_drift, billing_anomaly, contract_renewal, etc.).
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

# Sprint 2 Vague C ét12d (audit CFO P0 + Marie P0 #1) : indicatifs
# CAPEX/payback pour arbitrage CFO Décret Tertiaire. Sources :
#   - Audit énergétique réglementaire mid-market : ~5-15 k€/site (ADEME)
#   - Travaux d'optimisation moyens (relamping, GTB, calorifuge) :
#     ~50-300 €/m². On retient 8 k€/site comme proxy audit + premières
#     actions quick-wins (ordre de grandeur démo, pas de précision feinte).
# La formule reste simple et défendable en CODIR (pas d'étude TRI fine
# fictive). Refacto Vague D quand `audits_marketplace` exposera devis réels.
_DT_AUDIT_PROXY_CAPEX_EUR = 8_000.0  # par site (audit + premier batch quick-wins)
_DT_AUDIT_PAYBACK_MONTHS_PROXY = 9  # proxy mid-market (économies ~30% sur 24 mois)
_DT_NPV_HORIZON_YEAR = 2030  # échéance trajectoire DT


def detect(db: Session, org_id: int) -> list[SolEventCard]:
    """Émet 1-2 événements `compliance_deadline` selon état conformité org.

    Logique alignée sur narrative_generator._build_cockpit_daily lignes 405-435 :
    - 1 événement `critical` si non_conformes > 0 (impact = pénalité totale)
    - 1 événement `warning` si a_risque > 0 (impact = pénalité conditionnelle)

    Ne renvoie aucun événement si tout est conforme — `compute_events`
    retournera la liste vide (le SolWeekCards fera son fallback densifié).
    """
    # Imports locaux pour éviter cycle imports (constants doctrine + helpers narrative)
    from doctrine.constants import (
        DT_PENALTY_AT_RISK_EUR,
        DT_PENALTY_EUR,
    )
    from models.enums import StatutConformite
    from services.narrative.narrative_generator import _load_org_context

    ctx = _load_org_context(db, org_id)
    now = datetime.now(timezone.utc)
    events: list[SolEventCard] = []

    # Doctrine §10 « quel périmètre est concerné ? » : linked_assets.site_ids
    # filtré par statut réel (pas tous les sites de l'org).
    non_conforme_site_ids = [
        s.id for s in ctx.sites if getattr(s, "statut_decret_tertiaire", None) == StatutConformite.NON_CONFORME
    ]
    a_risque_site_ids = [
        s.id for s in ctx.sites if getattr(s, "statut_decret_tertiaire", None) == StatutConformite.A_RISQUE
    ]

    # Doctrine §7.2 — la donnée RegOps est mise à jour annuellement (OPERAT)
    # ou trimestriellement (audit interne). On considère `RegAssessment` comme
    # signal humain (« manual ») pour le freshness — pas de TTL machine.
    # DEBT Vague D : remplacer `now` par `site.last_regops_assessment_at`
    # quand ce champ sera exposé dans le modèle Site (cf code-review ét12d).
    freshness = compute_freshness("manual", now, now=now)

    if ctx.non_conformes > 0:
        impact_total_eur = ctx.non_conformes * DT_PENALTY_EUR
        # Vague C ét12d (audit CFO P0 #1) : mitigation CAPEX/payback/NPV
        # indicative. Permet l'arbitrage CODIR « audit 8 k€/site → éviter
        # 7 500 €/site/an » sur l'horizon DT 2030.
        capex_audit_total = ctx.non_conformes * _DT_AUDIT_PROXY_CAPEX_EUR
        years_to_horizon = max(1, _DT_NPV_HORIZON_YEAR - now.year)
        npv_eur = float(impact_total_eur * years_to_horizon - capex_audit_total)

        events.append(
            SolEventCard(
                id=f"compliance_deadline:org:{org_id}:non_conforme",
                event_type="compliance_deadline",
                severity="critical",
                title=(
                    f"{ctx.non_conformes} site"
                    f"{'s' if ctx.non_conformes > 1 else ''} non conforme"
                    f"{'s' if ctx.non_conformes > 1 else ''} Décret Tertiaire"
                ),
                narrative=(
                    "Action prioritaire : déclarer la consommation 2024 dans "
                    "OPERAT avant échéance. Pénalité réglementaire de "
                    f"{DT_PENALTY_EUR:,} € par site non-conforme (Décret n°2019-771)."
                ).replace(",", " "),  # FR : séparateur millier = espace insécable visuel
                impact=EventImpact(
                    value=float(impact_total_eur),
                    unit="€",
                    period="year",
                    mitigation=EventMitigation(
                        capex_eur=capex_audit_total,
                        payback_months=_DT_AUDIT_PAYBACK_MONTHS_PROXY,
                        npv_eur=npv_eur,
                        npv_horizon_year=_DT_NPV_HORIZON_YEAR,
                    ),
                ),
                source=EventSource(
                    system="RegOps",
                    last_updated_at=now,
                    confidence="high",
                    freshness_status=freshness,
                ),
                action=EventAction(
                    label="Ouvrir conformité",
                    route="/conformite",
                    owner_role="DAF",
                ),
                linked_assets=EventLinkedAssets(
                    org_id=org_id,
                    site_ids=non_conforme_site_ids,
                ),
            )
        )

    if ctx.a_risque > 0:
        impact_at_risk_eur = ctx.a_risque * DT_PENALTY_AT_RISK_EUR
        capex_audit_risk = ctx.a_risque * _DT_AUDIT_PROXY_CAPEX_EUR
        years_to_horizon = max(1, _DT_NPV_HORIZON_YEAR - now.year)
        npv_at_risk = float(impact_at_risk_eur * years_to_horizon - capex_audit_risk)

        events.append(
            SolEventCard(
                id=f"compliance_deadline:org:{org_id}:a_risque",
                event_type="compliance_deadline",
                severity="warning",
                title=(f"{ctx.a_risque} site{'s' if ctx.a_risque > 1 else ''} à risque sur la trajectoire 2030"),
                narrative=(
                    "Trajectoire 2030 sous tension. Audit énergétique recommandé "
                    "pour identifier les leviers de réduction. Pénalité conditionnelle "
                    f"{DT_PENALTY_AT_RISK_EUR:,} €/site si non-conforme à échéance."
                ).replace(",", " "),  # FR : séparateur millier = espace insécable visuel
                impact=EventImpact(
                    value=float(impact_at_risk_eur),
                    unit="€",
                    period="year",
                    mitigation=EventMitigation(
                        capex_eur=capex_audit_risk,
                        payback_months=_DT_AUDIT_PAYBACK_MONTHS_PROXY,
                        npv_eur=npv_at_risk,
                        npv_horizon_year=_DT_NPV_HORIZON_YEAR,
                    ),
                ),
                source=EventSource(
                    system="RegOps",
                    last_updated_at=now,
                    confidence="high",
                    freshness_status=freshness,
                ),
                action=EventAction(
                    label="Voir les sites à risque",
                    route="/conformite",
                    owner_role="DAF",
                ),
                linked_assets=EventLinkedAssets(
                    org_id=org_id,
                    site_ids=a_risque_site_ids,
                ),
            )
        )

    if not events and ctx.conformite_score is not None and ctx.conformite_score >= 80:
        # Pas de risque : émettre un événement `info` (good_news) pour densifier.
        events.append(
            SolEventCard(
                id=f"compliance_deadline:org:{org_id}:positive",
                event_type="compliance_deadline",
                severity="info",
                title="Conformité au-dessus de 80/100",
                narrative=(
                    "Patrimoine bien positionné sur la trajectoire 2030. Maintenir la qualité des déclarations OPERAT."
                ),
                impact=EventImpact(
                    value=float(ctx.conformite_score),
                    unit="%",
                    period="year",
                ),
                source=EventSource(
                    system="RegOps",
                    last_updated_at=now,
                    confidence="high",
                    freshness_status=freshness,
                ),
                action=EventAction(
                    label="Voir la conformité",
                    route="/conformite",
                    owner_role="DAF",
                ),
                linked_assets=EventLinkedAssets(org_id=org_id),
            )
        )

    return events
