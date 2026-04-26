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


# ── Builder cockpit_comex (Sprint 1.2 — Jean-Marc CFO) ──────────────


def _build_cockpit_comex(
    db: Session,
    org_id: int,
    org_name: str,
    sites_count: int,
) -> Narrative:
    """Sprint 1.2 — Vue COMEX Jean-Marc CFO.

    Différences vs cockpit_daily :
      - Persona = comex (vue mensuelle/hebdo synthèse direction, pas daily)
      - Narrative orientée € : exposition financière + leviers économies €/an
      - 3 KPIs : trajectoire DT 2030 + risque exposition + leviers cumulés
      - Week-cards focalisées CFO (économies vs pertes vs échéances)
      - Méthodologie URL pointe vers la page conformite-regops + brief CODIR

    Réutilise KpiService + RegAssessment existants. Sprint 2 chantier α
    enrichira les week-cards depuis le moteur d'événements (Bill-Intel
    reclaims, Achat scénarios, Capacité Nov 2026).
    """
    from models import EntiteJuridique, Portefeuille, Site, StatutConformite, not_deleted
    from services.kpi_service import KpiScope, KpiService

    kpi_svc = KpiService(db)
    scope = KpiScope(org_id=org_id)

    risque_total = kpi_svc.get_financial_risk_eur(scope).value
    conformite_kpi = kpi_svc.get_compliance_score(scope)
    conformite_score = int(round(conformite_kpi.value)) if conformite_kpi.value is not None else None

    site_q = (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )
    non_conformes = site_q.filter(Site.statut_decret_tertiaire == StatutConformite.NON_CONFORME).count()
    a_risque = site_q.filter(Site.statut_decret_tertiaire == StatutConformite.A_RISQUE).count()
    en_derive = non_conformes + a_risque

    # Estimation leviers économies — heuristique S1.2 (5% de la facture annuelle
    # moyenne tertiaire ETI ≈ 30 €/m²/an × surface estimée). Sprint 5 affinera
    # via Bill-Intel reclaims réels + simulateur achat post-ARENH.
    leviers_estimes_eur = max(0, en_derive * 8500.0)  # ordre grandeur €/an évitable

    # ── Kicker + titre ──
    week_iso = datetime.now(timezone.utc).isocalendar().week
    kicker = f"VUE COMEX · SEMAINE {week_iso} · {sites_count} SITE{'S' if sites_count > 1 else ''}"
    title = "Synthèse exécutive du portefeuille"
    italic_hook = "vue mensuelle direction"

    # ── Narrative 2-3 lignes orientée CFO (€ + trajectoire 2030) ──
    narr_parts = []
    if en_derive > 0 and risque_total:
        narr_parts.append(
            f"Exposition réglementaire cumulée : {_fmt_eur_short(risque_total)} "
            f"sur {en_derive}/{sites_count} sites en dérive de la trajectoire 2030."
        )
    elif sites_count > 0:
        narr_parts.append(
            f"Patrimoine de {sites_count} site{'s' if sites_count > 1 else ''} "
            f"sous contrôle réglementaire — aucune exposition immédiate."
        )

    if conformite_score is not None:
        statut_phrase = (
            "trajectoire tenue"
            if conformite_score >= 75
            else "vigilance requise"
            if conformite_score >= 50
            else "écart significatif vs cible 2030"
        )
        narr_parts.append(
            f"Score conformité {conformite_score}/100 — {statut_phrase} "
            f"(Décret n°2019-771, jalons -40%/2030, -50%/2040, -60%/2050)."
        )
    if leviers_estimes_eur > 0:
        narr_parts.append(
            f"Leviers économies estimés à {_fmt_eur_short(leviers_estimes_eur)}/an "
            f"sur les sites en dérive — détail dans le plan d'actions."
        )
    narrative = " ".join(narr_parts)

    # ── 3 KPIs hero §5 — angle CFO ──
    kpis: list[NarrativeKpi] = [
        NarrativeKpi(
            label="Trajectoire 2030",
            value=f"{conformite_score}/100" if conformite_score is not None else "—",
            tooltip=(
                "Score pondéré DT 45% · BACS 30% · APER 25% (ou 39/28/17/16 si "
                "audit énergétique applicable). Cible 2030 : -40% conso vs 2010."
            ),
            source="RegOps + Décret 2019-771",
        ),
        NarrativeKpi(
            label="Exposition financière",
            value=_fmt_eur_short(risque_total),
            tooltip=(
                "Cumul pénalités Décret Tertiaire (7 500 €/site non conforme, "
                "3 750 €/site à risque) sur la trajectoire 2030."
            ),
            source="Décret 2019-771",
        ),
        NarrativeKpi(
            label="Leviers économies",
            value=f"{_fmt_eur_short(leviers_estimes_eur)}/an" if leviers_estimes_eur else "—",
            tooltip=(
                "Ordre de grandeur des économies évitables sur les sites en dérive. "
                "Affinage via Bill-Intel + simulateur achat post-ARENH."
            ),
            source="Estimation PROMEOS",
        ),
    ]

    # ── Week-cards CFO (Sprint 2 chantier α enrichira depuis events bus) ──
    week_cards: list[NarrativeWeekCard] = []
    if non_conformes > 0:
        week_cards.append(
            NarrativeWeekCard(
                type="todo",
                title=(f"Provisionner {_fmt_eur_short(non_conformes * 7500.0)} de pénalité maximale"),
                body=(
                    f"{non_conformes} site{'s' if non_conformes > 1 else ''} non "
                    f"conforme{'s' if non_conformes > 1 else ''} — pénalité 7 500 €/"
                    f"site (Décret n°2019-771)."
                ),
                cta_path="/conformite",
                cta_label="Plan d'actions",
                impact_eur=non_conformes * 7500.0,
                urgency_days=180,
            )
        )
    if leviers_estimes_eur > 0:
        week_cards.append(
            NarrativeWeekCard(
                type="watch",
                title=f"Leviers économies {_fmt_eur_short(leviers_estimes_eur)}/an",
                body=("Sites en dérive — opportunités de réduction conso ou renégociation contrat avant échéance."),
                cta_path="/achat-energie",
                cta_label="Voir scénarios",
                impact_eur=leviers_estimes_eur,
            )
        )
    if conformite_score is not None and conformite_score >= 75:
        week_cards.append(
            NarrativeWeekCard(
                type="good_news",
                title="Trajectoire 2030 tenue",
                body=(
                    "Score conformité ≥75/100 — patrimoine bien positionné. "
                    "Maintenir la qualité des déclarations OPERAT."
                ),
            )
        )

    fallback_body = (
        f"Portefeuille de {sites_count} site{'s' if sites_count > 1 else ''} stable — "
        "à présenter en l'état au prochain CODIR."
    )

    confidence = (
        ProvenanceConfidence.HIGH if conformite_score is not None and sites_count > 0 else ProvenanceConfidence.MEDIUM
    )
    provenance = build_provenance(
        source="RegOps + RegAssessment + estimation leviers",
        confidence=confidence,
        updated_at=datetime.now(timezone.utc),
        methodology_url="/docs/methodologie/conformite-regops",
    )

    return Narrative(
        page_key="cockpit_comex",
        persona="comex",
        kicker=kicker,
        title=title,
        italic_hook=italic_hook,
        narrative=narrative,
        kpis=tuple(kpis),
        week_cards=tuple(week_cards),
        fallback_body=fallback_body,
        provenance=provenance,
    )


# ── Builder patrimoine (Sprint 1.3 — DAF tertiaire midmarket Marie) ──


def _build_patrimoine(
    db: Session,
    org_id: int,
    org_name: str,
    sites_count: int,
) -> Narrative:
    """Sprint 1.3 — Vue Patrimoine DAF.

    Promesse §4.1 doctrine : « Votre patrimoine est lisible comme un récit
    d'entreprise. EUI vs ADEME, surfaces, contrats, conformité — tout est
    mis en perspective dans une narrative qui parle de votre business. »

    Différenciateur §4.1 : simulation mutualisation Décret Tertiaire (-40%
    en 2030) — feature unique B2B multisite. Promu comme bonne nouvelle
    chiffrée dans les week-cards (audit Patrimoine Sprint 0 : caché onglet
    Conformité, à promouvoir Patrimoine).

    Réutilise :
      - compute_mutualisation() (services/tertiaire_mutualisation_service)
      - KpiService (sites en dérive)
      - Site model (surface_m2 cumulée)
    """
    from models import EntiteJuridique, Portefeuille, Site, StatutConformite, not_deleted
    from services.tertiaire_mutualisation_service import compute_mutualisation

    # Surface totale + sites en dérive
    site_q = (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )
    sites_list = site_q.all()
    surface_total_m2 = sum((s.surface_m2 or 0) for s in sites_list)
    non_conformes = sum(1 for s in sites_list if s.statut_decret_tertiaire == StatutConformite.NON_CONFORME)
    a_risque = sum(1 for s in sites_list if s.statut_decret_tertiaire == StatutConformite.A_RISQUE)
    en_derive = non_conformes + a_risque

    # Mutualisation DT 2030 — différenciateur §4.1
    economie_mutualisation_eur = 0.0
    mutualisation_conforme = False
    nb_sites_surplus = 0
    try:
        mutualisation = compute_mutualisation(db, org_id, jalon=2030)
        economie_mutualisation_eur = mutualisation.economie_mutualisation_eur
        mutualisation_conforme = mutualisation.conforme_mutualise
        nb_sites_surplus = mutualisation.nb_sites_surplus
    except Exception:
        # Données EFA partielles — fallback narrative sans chiffrage mutualisation
        pass

    # ── Kicker + titre ──
    kicker = f"PATRIMOINE · {sites_count} SITE{'S' if sites_count > 1 else ''} · {_fmt_m2_short(surface_total_m2)}"
    title = "Votre patrimoine"
    italic_hook = "sites, surfaces et opportunités"

    # ── Narrative 2-3 lignes orientée business DAF ──
    narr_parts = [
        f"Patrimoine de {sites_count} site{'s' if sites_count > 1 else ''} tertiaire"
        f"{'s' if sites_count > 1 else ''} totalisant {_fmt_m2_full(surface_total_m2)}."
    ]
    if economie_mutualisation_eur > 0:
        narr_parts.append(
            f"Mutualisation Décret Tertiaire 2030 : {_fmt_eur_short(economie_mutualisation_eur)} "
            f"d'économie potentielle en consolidant les efforts entre sites du portefeuille."
        )
    elif en_derive > 0:
        narr_parts.append(
            f"{en_derive} site{'s' if en_derive > 1 else ''} en dérive de la trajectoire "
            "2030 — plan de réduction conso prioritaire."
        )
    else:
        narr_parts.append(
            "Patrimoine bien positionné sur la trajectoire 2030 — maintenir la qualité des déclarations OPERAT."
        )
    narrative = " ".join(narr_parts)

    # ── 3 KPIs hero §5 — patrimoine business ──
    kpis: list[NarrativeKpi] = [
        NarrativeKpi(
            label="Surface tertiaire",
            value=_fmt_m2_full(surface_total_m2),
            tooltip=(
                "Surface cumulée des sites du périmètre Décret Tertiaire (>1000 m² obligation déclarative OPERAT)."
            ),
            source="Patrimoine PROMEOS",
        ),
        NarrativeKpi(
            label="Sites en dérive",
            value=f"{en_derive}/{sites_count}" if sites_count > 0 else "—",
            tooltip="Sites non-conformes ou à risque sur la trajectoire 2030.",
            source="RegAssessment",
        ),
        NarrativeKpi(
            label="Mutualisation 2030",
            value=(f"{_fmt_eur_short(economie_mutualisation_eur)}/an" if economie_mutualisation_eur > 0 else "—"),
            tooltip=(
                "Économie potentielle en consolidant les efforts de réduction "
                "entre sites du portefeuille (Art. 4 Décret n°2019-771 — "
                "feature multisite PROMEOS)."
            ),
            source="Décret 2019-771 art. 4",
        ),
    ]

    # ── Week-cards Patrimoine ──
    week_cards: list[NarrativeWeekCard] = []
    if economie_mutualisation_eur > 0:
        week_cards.append(
            NarrativeWeekCard(
                type="good_news",
                title=(f"Mutualisation 2030 : {_fmt_eur_short(economie_mutualisation_eur)}/an"),
                body=(
                    f"En consolidant les efforts entre vos {sites_count} sites, "
                    "vous évitez les pénalités sur les sites en dérive grâce aux "
                    "sites en avance. Feature unique multi-sites PROMEOS."
                ),
                cta_path="/conformite?tab=mutualisation",
                cta_label="Voir la simulation",
                impact_eur=economie_mutualisation_eur,
            )
        )
    if non_conformes > 0:
        week_cards.append(
            NarrativeWeekCard(
                type="todo",
                title=(
                    f"{non_conformes} site{'s' if non_conformes > 1 else ''} "
                    "non conforme"
                    f"{'s' if non_conformes > 1 else ''} à régulariser"
                ),
                body=("Plan d'actions prioritaire — déclaration OPERAT 2024 + audit énergétique recommandé."),
                cta_path="/conformite",
                cta_label="Plan d'actions",
                impact_eur=non_conformes * 7500.0,
                urgency_days=180,
            )
        )
    if a_risque > 0 and non_conformes == 0:
        week_cards.append(
            NarrativeWeekCard(
                type="watch",
                title=f"{a_risque} site{'s' if a_risque > 1 else ''} à surveiller",
                body=(
                    "Trajectoire 2030 sous tension. Audit énergétique recommandé "
                    "pour identifier les leviers de réduction conso."
                ),
                cta_path="/conformite",
                cta_label="Voir détails",
            )
        )
    if mutualisation_conforme and economie_mutualisation_eur > 0:
        week_cards.append(
            NarrativeWeekCard(
                type="good_news",
                title="Patrimoine conforme via mutualisation",
                body=(
                    f"L'effet de portefeuille rend votre patrimoine conforme "
                    f"à la trajectoire 2030 ({nb_sites_surplus} site"
                    f"{'s' if nb_sites_surplus > 1 else ''} en avance)."
                ),
            )
        )

    fallback_body = (
        f"Patrimoine de {sites_count} site{'s' if sites_count > 1 else ''} stable — "
        "consultez le détail par site pour explorer les opportunités."
    )

    confidence = (
        ProvenanceConfidence.HIGH if economie_mutualisation_eur > 0 and sites_count > 0 else ProvenanceConfidence.MEDIUM
    )
    provenance = build_provenance(
        source="Patrimoine PROMEOS + simulation mutualisation Décret 2019-771",
        confidence=confidence,
        updated_at=datetime.now(timezone.utc),
        methodology_url="/docs/methodologie/conformite-regops",
    )

    return Narrative(
        page_key="patrimoine",
        persona="daily",
        kicker=kicker,
        title=title,
        italic_hook=italic_hook,
        narrative=narrative,
        kpis=tuple(kpis),
        week_cards=tuple(week_cards),
        fallback_body=fallback_body,
        provenance=provenance,
    )


# ── Helpers format FR ───────────────────────────────────────────────


def _fmt_m2_short(m2: float) -> str:
    """Format compact m² : 12.3k m², 1.5M m², 500 m²."""
    if m2 is None or m2 == 0:
        return "0 m²"
    abs_m2 = abs(m2)
    if abs_m2 >= 1_000_000:
        return f"{round(m2 / 100_000) / 10}M m²"
    if abs_m2 >= 1_000:
        return f"{round(m2 / 100) / 10}k m²"
    return f"{int(m2)} m²"


def _fmt_m2_full(m2: float) -> str:
    """Format complet m² : 12 345 m²."""
    if m2 is None or m2 == 0:
        return "0 m²"
    return f"{int(m2):,}".replace(",", " ") + " m²"


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
    "cockpit_comex": _build_cockpit_comex,
    "patrimoine": _build_patrimoine,
    # Sprint 1.4+ : ajouter conformite, bill_intel, achat, monitoring,
    # diagnostic, anomalies, flex.
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
