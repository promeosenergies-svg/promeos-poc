"""Narrative generator — orchestrateur récit éditorial Sol §5.

MVP Sprint 1.1 : page_key `cockpit_daily` uniquement. Sprint 1.2-1.3
étendra à patrimoine / conformite / bill_intel / achat / monitoring /
diagnostic / anomalies / flex.

Doctrine §5 grammaire éditoriale invariante :
    [KICKER]
    TITRE FRAUNCES
    Narrative 2-3 lignes sourcée
    [KPI 1] [KPI 2] [KPI 3]   ← max 3 KPIs avec tooltip
    [À regarder] [À faire] [Bonne nouvelle]   ← week-cards typées
    [FOOTER : SOURCE · CONFIANCE · MIS À JOUR]

Doctrine §8.1 règle d'or : aucun calcul métier ici. Cette couche
orchestre les services pillar existants (KpiService, RegAssessment,
BillingInsight, EnergyAnomaly, etc.) et compose la narrative finale
prête à afficher.

Cf. ADR-001 grammaire Sol industrialisée.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

from sqlalchemy.orm import Session

from services.data_provenance import (
    Provenance,
    ProvenanceConfidence,
    build_provenance,
)

# ── Types canoniques ────────────────────────────────────────────────


CardType = Literal["watch", "todo", "good_news", "drift"]
Persona = Literal["daily", "comex"]
PageKey = Literal[
    "cockpit_daily",
    "cockpit_comex",
    "patrimoine",
    "conformite",
    "bill_intel",
    "achat",
    "monitoring",
    "diagnostic",
    "anomalies",
    "flex",
]


@dataclass(frozen=True)
class NarrativeKpi:
    """KPI unitaire pour bandeau hero §5 (max 3 par page)."""

    label: str
    value: str  # Pré-formaté FR : "73/100", "26 k€", "5 sites"
    unit: Optional[str] = None
    tooltip: Optional[str] = None  # Définition non-sachant
    source: Optional[str] = None  # Référentiel court (ADEME / RegOps / EPEX)


@dataclass(frozen=True)
class NarrativeWeekCard:
    """Week-card sémantique typée §5."""

    type: CardType
    title: str
    body: str
    cta_path: Optional[str] = None
    cta_label: Optional[str] = None
    impact_eur: Optional[float] = None
    urgency_days: Optional[int] = None


@dataclass(frozen=True)
class Narrative:
    """Récit éditorial complet d'une page Sol §5."""

    page_key: PageKey
    persona: Persona
    kicker: str
    title: str
    italic_hook: Optional[str]
    narrative: str  # 2-3 lignes sourcée
    kpis: tuple[NarrativeKpi, ...]  # max 3
    week_cards: tuple[NarrativeWeekCard, ...]  # exactement 3 (post-fallback)
    fallback_body: str  # densification §4 si week_cards <3
    provenance: Provenance

    def to_dict(self) -> dict:
        d = {
            "page_key": self.page_key,
            "persona": self.persona,
            "kicker": self.kicker,
            "title": self.title,
            "italic_hook": self.italic_hook,
            "narrative": self.narrative,
            "kpis": [asdict(k) for k in self.kpis],
            "week_cards": [asdict(c) for c in self.week_cards],
            "fallback_body": self.fallback_body,
            "provenance": self.provenance.to_dict(),
        }
        return d


# ── Builders MVP — cockpit_daily ────────────────────────────────────


def _build_cockpit_daily(
    db: Session,
    org_id: int,
    org_name: str,
    sites_count: int,
) -> Narrative:
    """MVP Sprint 1.1 : briefing daily Marie 8h45.

    Réutilise l'existant :
      - KpiService : compliance_score, financial_risk_eur
      - RegAssessment : non_conformes / a_risque
      - notification_service : signaux ouvrir → week_cards (Sprint 2 chantier α)

    Sprint 1.1 = MVP avec données réelles agrégées + 3 week-cards
    densifiées via fallback. Sprint 2 alimentera depuis event bus.
    """
    from services.kpi_service import KpiScope, KpiService
    from models import Site, EntiteJuridique, Portefeuille, not_deleted
    from models import StatutConformite

    kpi_svc = KpiService(db)
    scope = KpiScope(org_id=org_id)

    risque_total = kpi_svc.get_financial_risk_eur(scope).value
    conformite_kpi = kpi_svc.get_compliance_score(scope)
    conformite_score = int(round(conformite_kpi.value)) if conformite_kpi.value is not None else None

    # Sites en dérive (non-conformes + à risque)
    site_q = (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )
    non_conformes = site_q.filter(Site.statut_decret_tertiaire == StatutConformite.NON_CONFORME).count()
    a_risque = site_q.filter(Site.statut_decret_tertiaire == StatutConformite.A_RISQUE).count()
    en_derive = non_conformes + a_risque

    # ── Kicker + titre ──
    kicker = f"BRIEFING DU JOUR · {org_name.upper() if org_name else 'PATRIMOINE'} · {sites_count} SITE{'S' if sites_count > 1 else ''}"
    week_iso = datetime.now(timezone.utc).isocalendar().week
    kicker_full = f"BRIEFING DU JOUR · SEMAINE {week_iso} · {sites_count} SITE{'S' if sites_count > 1 else ''}"

    title = "Bonjour — voici votre journée"
    italic_hook = "ce qui mérite votre attention"

    # ── Narrative 2-3 lignes ──
    narr_parts = []
    if en_derive > 0:
        narr_parts.append(
            f"Vous avez {en_derive} site{'s' if en_derive > 1 else ''} en dérive "
            f"sur {sites_count}, exposant {_fmt_eur_short(risque_total)} de risque réglementaire."
        )
    else:
        narr_parts.append(
            f"Patrimoine de {sites_count} site{'s' if sites_count > 1 else ''} sous contrôle aujourd'hui."
        )
    if conformite_score is not None:
        narr_parts.append(
            f"Score conformité {conformite_score}/100 sur la trajectoire 2030 obligatoire (Décret n°2019-771)."
        )
    narrative = " ".join(narr_parts)

    # ── 3 KPIs hero §5 ──
    kpis: list[NarrativeKpi] = [
        NarrativeKpi(
            label="Conformité réglementaire",
            value=f"{conformite_score}/100" if conformite_score is not None else "—",
            tooltip="Score pondéré DT 45% · BACS 30% · APER 25% (référentiel RegOps PROMEOS).",
            source="RegOps",
        ),
        NarrativeKpi(
            label="Risque financier",
            value=_fmt_eur_short(risque_total),
            tooltip="Exposition cumulée pénalités Décret Tertiaire (7 500 €/site, 3 750 € si à risque).",
            source="Décret 2019-771",
        ),
        NarrativeKpi(
            label="Sites en dérive",
            value=f"{en_derive}/{sites_count}" if sites_count > 0 else "—",
            tooltip="Sites non-conformes ou à risque sur la trajectoire 2030.",
            source="RegAssessment",
        ),
    ]

    # ── 3 week-cards (MVP Sprint 1.1 — densification §4) ──
    # Sprint 2 chantier α remplacera ces cards par les events réels du moteur
    # d'événements proactif. Pour S1.1 on génère depuis l'état courant.
    week_cards: list[NarrativeWeekCard] = []
    if non_conformes > 0:
        week_cards.append(
            NarrativeWeekCard(
                type="todo",
                title=f"{non_conformes} site{'s' if non_conformes > 1 else ''} non conforme{'s' if non_conformes > 1 else ''}",
                body="Action prioritaire : déclarer la consommation 2024 dans OPERAT avant échéance.",
                cta_path="/conformite",
                cta_label="Ouvrir conformité",
                impact_eur=non_conformes * 7500.0,
                urgency_days=30,
            )
        )
    if a_risque > 0:
        week_cards.append(
            NarrativeWeekCard(
                type="watch",
                title=f"{a_risque} site{'s' if a_risque > 1 else ''} à risque",
                body="Trajectoire 2030 sous tension. Audit énergétique recommandé pour identifier les leviers.",
                cta_path="/conformite",
                cta_label="Voir les sites à risque",
                impact_eur=a_risque * 3750.0,
            )
        )
    if conformite_score is not None and conformite_score >= 80:
        week_cards.append(
            NarrativeWeekCard(
                type="good_news",
                title="Conformité au-dessus de 80/100",
                body="Patrimoine bien positionné sur la trajectoire 2030. Maintenir la qualité des données OPERAT.",
            )
        )

    # Fallback densifié §4 — JAMAIS d'empty state pleine largeur
    fallback_body = (
        f"Patrimoine de {sites_count} site{'s' if sites_count > 1 else ''} stable cette semaine — "
        "aucun signal critique détecté."
    )

    # ── Provenance ──
    confidence = (
        ProvenanceConfidence.HIGH if conformite_score is not None and sites_count > 0 else ProvenanceConfidence.MEDIUM
    )
    provenance = build_provenance(
        source="RegOps + RegAssessment",
        confidence=confidence,
        updated_at=datetime.now(timezone.utc),
        methodology_url="/docs/methodologie/conformite-regops",
    )

    return Narrative(
        page_key="cockpit_daily",
        persona="daily",
        kicker=kicker_full,
        title=title,
        italic_hook=italic_hook,
        narrative=narrative,
        kpis=tuple(kpis),
        week_cards=tuple(week_cards),
        fallback_body=fallback_body,
        provenance=provenance,
    )


# ── Helpers format FR ───────────────────────────────────────────────


def _fmt_eur_short(amount: Optional[float]) -> str:
    """Format compact € : 26 k€, 1.2 M€, 450 €."""
    if amount is None or amount == 0:
        return "0 €"
    abs_amount = abs(amount)
    if abs_amount >= 1_000_000:
        return f"{round(amount / 100_000) / 10} M€"
    if abs_amount >= 1_000:
        return f"{round(amount / 100) / 10} k€"
    return f"{round(amount)} €"


# ── Entry point public ────────────────────────────────────────────────


_BUILDERS = {
    "cockpit_daily": _build_cockpit_daily,
    # Sprint 1.2+ : ajouter cockpit_comex, patrimoine, conformite, bill_intel,
    # achat, monitoring, diagnostic, anomalies, flex.
}


def generate_page_narrative(
    db: Session,
    page_key: PageKey,
    org_id: int,
    *,
    org_name: str = "",
    sites_count: int = 0,
    persona: Persona = "daily",
    archetype: Optional[str] = None,  # Sprint 3 chantier β
) -> Narrative:
    """Entry point public : génère le récit complet d'une page Sol.

    MVP Sprint 1.1 : `cockpit_daily` uniquement. Les autres page_keys
    lèvent NotImplementedError jusqu'à leur implémentation S1.2-S1.3.

    Sprint 3 ADR-003 : `archetype` brancera vers builders dédiés
    (tertiaire_midmarket / industriel_agroalim / hotelier / collectivite /
    mono_site_pme).
    """
    builder = _BUILDERS.get(page_key)
    if builder is None:
        raise NotImplementedError(
            f"Narrative builder pour page_key='{page_key}' pas encore implémenté. "
            f"MVP Sprint 1.1 : cockpit_daily. Sprint 1.2-1.3 étendra aux autres pages."
        )
    return builder(db, org_id, org_name, sites_count)
