"""Détecteur `contract_renewal` — chantier α Vague C ét13c.

Doctrine §10 event_type `contract_renewal` : émet un événement quand un
contrat fournisseur arrive à échéance ou approche de sa date de préavis.

Couvre 4 cas d'urgence (cohérent market_window severity logic) :
- Préavis dépassé J-0 → critical (résiliation impossible avant terme)
- Préavis < 30 jours → critical (action immédiate)
- Échéance contrat < 90 jours → warning (renégocier maintenant)
- Échéance contrat < 180 jours → watch (préparer dossier)

Réutilise SoT canonique `ContratCadre` (date_fin + date_preavis) — pas de
SQL métier inline (règle d'or §10 P3). Owner DAF (responsabilité achat).
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

# Seuils urgence (jours avant échéance) cohérents market_window
_URGENCY_NOTICE_OVERDUE = 0  # préavis dépassé → critical
_URGENCY_CRITICAL_DAYS = 30
_URGENCY_WARNING_DAYS = 90
_URGENCY_WATCH_DAYS = 180


def _severity_for_contract(days_to_end: int, days_to_notice: int | None) -> str | None:
    """Mappe urgences contrat → severity doctrine §10."""
    # Préavis dépassé : il est trop tard pour résilier proprement → critique
    if days_to_notice is not None and days_to_notice <= _URGENCY_NOTICE_OVERDUE:
        return "critical"
    if days_to_notice is not None and days_to_notice <= _URGENCY_CRITICAL_DAYS:
        return "critical"
    if days_to_end <= _URGENCY_WARNING_DAYS:
        return "warning"
    if days_to_end <= _URGENCY_WATCH_DAYS:
        return "watch"
    return None


def detect(db: Session, org_id: int) -> list[SolEventCard]:
    """Émet 0..N événements `contract_renewal` selon contrats arrivant à échéance.

    Limite à top 3 contrats les plus urgents (densification cards Sol §5).
    """
    # Imports locaux pour éviter cycle (services → models → event_bus)
    from config.mitigation_loader import get_contract_renewal_defaults
    from models import not_deleted
    from models.contract_v2_models import ContractAnnexe, ContratCadre
    from models.enums import BillingEnergyType

    cr_defaults = get_contract_renewal_defaults()  # ét14 P0 #1 CFO+Marie

    today = date.today()
    contrats = not_deleted(db.query(ContratCadre), ContratCadre).filter(ContratCadre.org_id == org_id).all()

    events: list[SolEventCard] = []
    candidates = []
    for c in contrats:
        if c.date_fin is None:
            continue
        days_to_end = (c.date_fin - today).days
        days_to_notice = (c.date_preavis - today).days if c.date_preavis else None
        severity = _severity_for_contract(days_to_end, days_to_notice)
        if severity is None:
            continue
        candidates.append((c, days_to_end, days_to_notice, severity))

    # Top 3 contrats les plus urgents (par jours_to_end ascendant)
    candidates.sort(key=lambda x: x[1])
    candidates = candidates[:3]

    now = datetime.now(timezone.utc)
    for c, days_to_end, days_to_notice, severity in candidates:
        # Phrase urgence éditoriale §5
        if days_to_end <= 0:
            urgency_phrase = f"échu depuis {-days_to_end} jour{'s' if -days_to_end > 1 else ''}"
        elif days_to_end <= 30:
            urgency_phrase = f"dans {days_to_end} jour{'s' if days_to_end > 1 else ''} (action immédiate)"
        elif days_to_end <= 60:
            urgency_phrase = f"dans {days_to_end // 7} semaines"
        else:
            urgency_phrase = f"dans {days_to_end // 30} mois"

        notice_phrase = ""
        if days_to_notice is not None:
            if days_to_notice <= 0:
                notice_phrase = f" Préavis dépassé depuis {-days_to_notice} jour{'s' if -days_to_notice > 1 else ''} — résiliation impossible sans accord fournisseur."
            elif days_to_notice <= 30:
                notice_phrase = f" Préavis à respecter sous {days_to_notice} jour{'s' if days_to_notice > 1 else ''}."

        # ét14 (audit CFO+Marie P0 #1) : chiffrer la fourchette € de risque
        # tacite. Volume proxy = nb_annexes × MWh/site YAML. Prix marché
        # selon énergie. Surcoût = volume × prix × spread tacite (15 %).
        nb_annexes = (
            not_deleted(db.query(ContractAnnexe), ContractAnnexe)
            .filter(ContractAnnexe.contrat_cadre_id == c.id)
            .count()
        )
        # Si pas d'annexes, on estime un site mini (sinon 0 €/an = trompeur)
        nb_annexes_proxy = max(1, nb_annexes)
        volume_mwh = nb_annexes_proxy * cr_defaults.proxy_volume_per_annex_mwh
        market_price = (
            cr_defaults.market_price_gaz_eur_per_mwh
            if c.energie == BillingEnergyType.GAZ
            else cr_defaults.market_price_elec_eur_per_mwh
        )
        impact_tacite_eur = volume_mwh * market_price * cr_defaults.tacite_spread_pct

        events.append(
            SolEventCard(
                id=f"contract_renewal:org:{org_id}:contrat:{c.id}",
                event_type="contract_renewal",
                severity=severity,  # type: ignore[arg-type]
                title=f"Contrat {c.fournisseur} ({c.energie.value}) — échéance {urgency_phrase}",
                narrative=(
                    f"Le contrat {c.reference} avec {c.fournisseur} arrive à échéance.{notice_phrase} "
                    f"Anticiper la renégociation pour éviter une reconduction tacite estimée à "
                    f"+{int(impact_tacite_eur):,} €/an (volume proxy {volume_mwh} MWh × "
                    f"{market_price:.0f} €/MWh × spread tacite {cr_defaults.tacite_spread_pct * 100:.0f} %)."
                ).replace(",", " "),
                impact=EventImpact(
                    value=impact_tacite_eur,
                    unit="€",
                    period="year",
                ),
                source=EventSource(
                    system="manual",  # contrat saisi côté DAF (pas système ERP intégré)
                    last_updated_at=now,
                    confidence="high",  # date contractuelle officielle
                    freshness_status=compute_freshness("manual", now, now=now),
                    methodology=(
                        f"Détection basée sur ContratCadre.date_fin ({c.date_fin}) "
                        f"et ContratCadre.date_preavis ({c.date_preavis or 'non renseignée'}). "
                        "Severity dynamique selon urgence : préavis dépassé ou < 30j → critique ; "
                        "échéance < 90j → à faire ; < 180j → à surveiller. "
                        f"Impact € = nb_annexes ({nb_annexes_proxy}) × volume proxy "
                        f"({cr_defaults.proxy_volume_per_annex_mwh} MWh/site) × prix marché "
                        f"({market_price:.0f} €/MWh, source : {cr_defaults.market_price_source}) "
                        f"× spread tacite ({cr_defaults.tacite_spread_pct * 100:.0f} %, "
                        f"source : {cr_defaults.tacite_spread_source})."
                    ),
                ),
                action=EventAction(
                    label="Renégocier le contrat",
                    route="/achat-energie",
                    owner_role="DAF",
                ),
                linked_assets=EventLinkedAssets(
                    org_id=org_id,
                    contract_ids=[c.id],
                ),
            )
        )

    return events
