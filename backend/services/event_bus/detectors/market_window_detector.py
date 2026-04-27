"""Détecteur `market_window` — chantier α Vague C ét13b (P0 VC Sarah Sequoia).

Doctrine §10 event_type `market_window` : émet un événement quand une
fenêtre marché actionnable approche (capacité Nov 2026 obligatoire,
VNU post-ARENH, fenêtres achat trimestrielles).

Différenciant Series A : aucun concurrent énergie B2B (Metron/Tilt/Sobry/
Deepki/HelloWatt) ne pousse les fenêtres réglementaires marché en
narratif CFO. Sarah Sequoia P0 #3 (avec flex_opportunity).

Source réglementaire ancrée :
- Capacité 1/11/2026 : RTE — fin ARENH 31/12/2025, mécanisme capacité
  physique obligatoire entrée en vigueur 1/11/2026 (CRE délib 2025-269,
  délib 2026-49 coef A).
- VNU post-ARENH : Versement Nucléaire Universel, taxe/réduction selon
  prix marché EPEX. Activé si Brent > seuils définis art. L.336-2.

MVP ét13b : 1 event capacity_2026 visible jusqu'au 1/11/2026, severity
décroissante selon urgence (J-90 critical, J-180 warning, J-365 watch).
Une fois la date passée, l'event s'efface (pas de bruit historique).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from ..freshness import compute_freshness
from ..types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventSource,
    SolEventCard,
)

# Jalon réglementaire RTE — entrée en vigueur mécanisme capacité physique.
# Source : CRE délib 2025-269 + 2026-49 (coef A flexibilité capacité).
_CAPACITY_DEADLINE = date(2026, 11, 1)

# Coût indicatif moyen capacité non-couverte (€/MWh sur consommation
# annuelle si pas de garantie capacité achetée). Fourchette CRE :
# 8-15 €/MWh selon profil. On retient 12 €/MWh comme proxy mid-market.
# DEBT Vague D : externaliser dans config/mitigation_defaults.yaml quand
# le pattern de défauts marché sera consolidé.
_CAPACITY_COST_PER_MWH_EUR = 12.0

# Seuils urgence (jours avant échéance) → severity doctrine §10
_URGENCY_CRITICAL_DAYS = 90  # J-90 → critical (action immédiate)
_URGENCY_WARNING_DAYS = 180  # J-180 → warning (planifier)
_URGENCY_WATCH_DAYS = 365  # J-365 → watch (à anticiper)


def _severity_for_urgency(days_remaining: int) -> str | None:
    """Mappe jours restants → severity. Au-delà de 365j : pas d'événement."""
    if days_remaining < 0:
        return None  # échéance passée, plus d'événement
    if days_remaining <= _URGENCY_CRITICAL_DAYS:
        return "critical"
    if days_remaining <= _URGENCY_WARNING_DAYS:
        return "warning"
    if days_remaining <= _URGENCY_WATCH_DAYS:
        return "watch"
    return None


def detect(db: Session, org_id: int) -> list[SolEventCard]:
    """Émet 0..1 événement `market_window` selon urgence capacité 1/11/2026.

    Doctrine §10 « 6 questions » :
    - quel fait : échéance mécanisme capacité physique obligatoire
    - quel périmètre : org (impact transversal sur tous les contrats)
    - quel impact : € estimé non-couverture × consommation portefeuille
    - quelle action : route /achat-energie + owner DAF (arbitrage achat)
    - quelle source : RegOps (ancré CRE délib 2025-269)
    - quelle confiance : high (date réglementaire publique)
    """
    # Imports locaux pour éviter cycle (services/narrative → event_bus)
    from services.narrative.narrative_generator import _load_org_context

    today = date.today()
    days_remaining = (_CAPACITY_DEADLINE - today).days
    severity = _severity_for_urgency(days_remaining)
    if severity is None:
        return []

    ctx = _load_org_context(db, org_id)
    if not ctx.sites:
        return []

    # Estimer la consommation portefeuille (proxy : 100 MWh/site mid-market)
    # DEBT Vague D : remplacer par sum(site.consommation_annuelle_mwh) quand
    # le champ sera consolidé sur tous les seeds.
    estimated_consumption_mwh = len(ctx.sites) * 100
    impact_eur = estimated_consumption_mwh * _CAPACITY_COST_PER_MWH_EUR

    now = datetime.now(timezone.utc)

    # Phrase urgence éditoriale §5 (acronymes décodés)
    if days_remaining <= 30:
        urgency_phrase = f"dans {days_remaining} jour{'s' if days_remaining > 1 else ''} (action immédiate)"
    elif days_remaining <= 60:
        urgency_phrase = f"dans {days_remaining // 7} semaines"
    elif days_remaining <= 365:
        urgency_phrase = f"dans {days_remaining // 30} mois"
    else:
        urgency_phrase = f"le {_CAPACITY_DEADLINE.strftime('%d/%m/%Y')}"

    return [
        SolEventCard(
            id=f"market_window:org:{org_id}:capacity_nov_2026",
            event_type="market_window",
            severity=severity,  # type: ignore[arg-type]
            title=f"Mécanisme capacité obligatoire — échéance {urgency_phrase}",
            narrative=(
                f"Fin du mécanisme ARENH au 31/12/2025, remplacé par le mécanisme "
                f"capacité physique obligatoire à compter du 1er novembre 2026. "
                f"Sans garantie capacité couvrant votre portefeuille "
                f"({len(ctx.sites)} site{'s' if len(ctx.sites) > 1 else ''}), "
                f"surcoût estimé à {int(impact_eur):,} €/an "
                f"({_CAPACITY_COST_PER_MWH_EUR:.0f} €/MWh × {estimated_consumption_mwh} MWh)."
            ).replace(",", " "),
            impact=EventImpact(
                value=impact_eur,
                unit="€",
                period="year",
            ),
            source=EventSource(
                system="RegOps",
                last_updated_at=now,
                confidence="high",  # date réglementaire publique CRE
                freshness_status=compute_freshness("RegOps", now, now=now),
                methodology=(
                    "Source : CRE délibération 2025-269 + 2026-49 (coef A capacité). "
                    "Surcoût estimé = consommation portefeuille × coût indicatif "
                    f"capacité non-couverte ({_CAPACITY_COST_PER_MWH_EUR:.0f} €/MWh "
                    "fourchette CRE 8-15 €/MWh). "
                    "Action : sécuriser une garantie capacité avant la date butoir "
                    "via votre fournisseur ou un agrégateur certifié RTE."
                ),
            ),
            action=EventAction(
                label="Voir les scénarios d'achat",
                route="/achat-energie",
                owner_role="DAF",
            ),
            linked_assets=EventLinkedAssets(
                org_id=org_id,
                site_ids=[s.id for s in ctx.sites],
            ),
        )
    ]
