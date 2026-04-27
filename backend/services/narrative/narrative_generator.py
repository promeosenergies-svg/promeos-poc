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
from enum import Enum
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


class NarrativeTone(str, Enum):
    """Tone narrative §5 (S1.3bis P0-D + S1.4bis /simplify Quality).

    Pattern aligné sur ProvenanceConfidence (provenance_service.py) — Enum
    str pour validation runtime + sérialisation JSON automatique.

    POSITIVE  — patrimoine bien positionné (score >= 75, pas de dérive)
    NEUTRAL   — état stable sans signal fort
    TENSION   — sites à risque ou échéance proche (90-365j)
    CRITICAL  — non-conformes ou échéance critique (<90j)
    """

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    TENSION = "tension"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Narrative:
    """Récit éditorial complet d'une page Sol §5."""

    page_key: PageKey
    persona: Persona
    kicker: str
    title: str
    italic_hook: Optional[str]
    narrative: str  # 2-3 lignes sourcée
    narrative_tone: NarrativeTone  # P0-D : densification fallback typé
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
            "narrative_tone": self.narrative_tone,
            "kpis": [asdict(k) for k in self.kpis],
            "week_cards": [asdict(c) for c in self.week_cards],
            "fallback_body": self.fallback_body,
            "provenance": self.provenance.to_dict(),
        }
        return d


# ── Helpers partagés (S1.4bis /simplify Code Reuse + Quality P0) ─────


@dataclass(frozen=True)
class OrgContext:
    """Contexte org chargé une fois par requête.

    Sprint 1.4bis : factorise le bloc dupliqué 4x dans les builders
    (KpiService + scope + site_q + non_conformes + a_risque + en_derive).
    Réduit ~100 LOC dupliquées et centralise la requête jointurisée.
    """

    risque_total: float
    conformite_score: Optional[int]
    non_conformes: int
    a_risque: int
    en_derive: int
    sites: list  # liste Site complète (utile pour Patrimoine surface_m2)


def _load_org_context(db: Session, org_id: int) -> OrgContext:
    """Charge le contexte org canonique consommé par les 4 builders.

    Une seule requête jointurisée (Site + Portefeuille + EntiteJuridique)
    + 2 appels KpiService. Pattern centralisé pour cohérence cross-builders.
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
    sites = site_q.all()
    non_conformes = sum(1 for s in sites if s.statut_decret_tertiaire == StatutConformite.NON_CONFORME)
    a_risque = sum(1 for s in sites if s.statut_decret_tertiaire == StatutConformite.A_RISQUE)

    return OrgContext(
        risque_total=risque_total or 0.0,
        conformite_score=conformite_score,
        non_conformes=non_conformes,
        a_risque=a_risque,
        en_derive=non_conformes + a_risque,
        sites=sites,
    )


def _compute_tone(
    non_conformes: int,
    a_risque: int,
    conformite_score: Optional[int],
    *,
    urgency_critical: bool = False,
) -> NarrativeTone:
    """Calcule le tone narrative à partir de l'état patrimoine.

    Sprint 1.4bis /simplify Quality P0 : 4× dupliqué dans les builders.
    `urgency_critical` permet aux builders avec deadline (Conformité audit
    SMÉ <90j) de forcer le tone CRITICAL même sans non-conforme.
    """
    if non_conformes > 0 or urgency_critical:
        return NarrativeTone.CRITICAL
    if a_risque > 0:
        return NarrativeTone.TENSION
    if conformite_score is not None and conformite_score >= 75:
        return NarrativeTone.POSITIVE
    return NarrativeTone.NEUTRAL


def _build_provenance_canonical(
    source: str,
    *,
    conformite_score: Optional[int],
    sites_count: int,
    methodology_url: str = "/methodologie/conformite-regops",
) -> Provenance:
    """Pattern build_provenance canonique : confidence HIGH si données réelles.

    Sprint 1.4bis : factorisation du pattern répété 4× dans les builders
    (lignes 247-255 / 450-458 / 673-682 / 931-938 du diff initial).
    """
    confidence = (
        ProvenanceConfidence.HIGH if conformite_score is not None and sites_count > 0 else ProvenanceConfidence.MEDIUM
    )
    return build_provenance(
        source=source,
        confidence=confidence,
        updated_at=datetime.now(timezone.utc),
        methodology_url=methodology_url,
    )


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
    # Sprint 1.4bis : helper centralisé (KpiService + sites + non_conformes/a_risque)
    ctx = _load_org_context(db, org_id)
    risque_total = ctx.risque_total
    conformite_score = ctx.conformite_score
    non_conformes = ctx.non_conformes
    a_risque = ctx.a_risque
    en_derive = ctx.en_derive

    # ── Kicker + titre ──
    # Sprint 1.4bis /simplify Quality P0 : fix dead-code kicker (l.158 du
    # diff initial, calculée avec org_name puis écrasée par kicker_full
    # avec week_iso). Désormais une seule définition canonique.
    week_iso = datetime.now(timezone.utc).isocalendar().week
    kicker = f"BRIEFING DU JOUR · SEMAINE {week_iso} · {sites_count} SITE{'S' if sites_count > 1 else ''}"

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

    # Sprint 1.4bis : helpers _compute_tone + _build_provenance_canonical
    # CRITICAL si dérive significative (>30% sites en dérive) — préservé
    # depuis l'implémentation S1.1.
    urgency_critical = sites_count > 0 and en_derive / sites_count > 0.3
    narrative_tone = _compute_tone(non_conformes, a_risque, conformite_score, urgency_critical=urgency_critical)
    provenance = _build_provenance_canonical(
        "RegOps + RegAssessment",
        conformite_score=conformite_score,
        sites_count=sites_count,
    )

    return Narrative(
        page_key="cockpit_daily",
        persona="daily",
        kicker=kicker,
        title=title,
        italic_hook=italic_hook,
        narrative=narrative,
        narrative_tone=narrative_tone,
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
    # Sprint 1.4bis : helper centralisé
    ctx = _load_org_context(db, org_id)
    risque_total = ctx.risque_total
    conformite_score = ctx.conformite_score
    non_conformes = ctx.non_conformes
    a_risque = ctx.a_risque
    en_derive = ctx.en_derive

    # Estimation leviers économies — heuristique S1.2 transparente :
    # ordre de grandeur ~8 500 €/site dérive (5% facture annuelle moyenne
    # tertiaire ETI ≈ 30 €/m²/an × 600 m² médian × 5%). Bill-Intel S5
    # affinera via reclaims réels + simulateur achat post-ARENH.
    # Affiché avec source explicite "estimation modélisée" pour ne pas
    # confondre avec un chiffrage sourcé.
    LEVIER_ESTIME_PAR_SITE_EUR = 8500.0  # heuristique modélisée, à remplacer S5
    leviers_estimes_eur = max(0, en_derive * LEVIER_ESTIME_PAR_SITE_EUR)

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
            label="Leviers économies (estimés)",
            value=f"{_fmt_eur_short(leviers_estimes_eur)}/an" if leviers_estimes_eur else "—",
            tooltip=(
                "Ordre de grandeur estimé : ~8 500 €/site en dérive "
                "(5 % facture annuelle moyenne ETI tertiaire). Chiffrage sourcé "
                "Bill-Intel + simulateur achat post-ARENH livré Sprint 5."
            ),
            source="Estimation modélisée PROMEOS",
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

    # Sprint 1.4bis : helpers _compute_tone + _build_provenance_canonical
    narrative_tone = _compute_tone(non_conformes, a_risque, conformite_score)
    provenance = _build_provenance_canonical(
        "RegOps + RegAssessment + estimation leviers",
        conformite_score=conformite_score,
        sites_count=sites_count,
        methodology_url="/methodologie/cockpit-comex",
    )

    return Narrative(
        page_key="cockpit_comex",
        persona="comex",
        kicker=kicker,
        title=title,
        italic_hook=italic_hook,
        narrative=narrative,
        narrative_tone=narrative_tone,
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
    from services.tertiaire_mutualisation_service import compute_mutualisation

    # Sprint 1.4bis : helper centralisé (charge sites + KPIs en une passe)
    ctx = _load_org_context(db, org_id)
    sites_list = ctx.sites
    surface_total_m2 = sum((s.surface_m2 or 0) for s in sites_list)
    non_conformes = ctx.non_conformes
    a_risque = ctx.a_risque
    conformite_score = ctx.conformite_score
    en_derive = ctx.en_derive  # noqa: F841 (réservé future enrichment narrative Patrimoine)

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
                "entre sites du portefeuille (Art. 3 Décret n°2019-771 — "
                "feature multisite PROMEOS)."
            ),
            source="Décret 2019-771 art. 3 (L111-10-3)",
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
    elif sites_count >= 3:
        # Sprint 1.3bis (audit UX fin S1) : si la mutualisation ne se
        # déclenche pas (données EFA partielles), exposer quand même
        # le différenciateur §4.1 doctrine via une card watch invitant
        # à compléter les données pour activer le calcul.
        week_cards.append(
            NarrativeWeekCard(
                type="watch",
                title="Évaluer le potentiel de mutualisation 2030",
                body=(
                    "Compléter les déclarations OPERAT débloquera la "
                    "simulation de mutualisation Décret Tertiaire — "
                    "économies portefeuille chiffrées en €/an."
                ),
                cta_path="/conformite?tab=mutualisation",
                cta_label="Compléter les données",
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

    # Sprint 1.5bis /simplify Code Reuse P0 : utilise les helpers canoniques
    # _compute_tone et _build_provenance_canonical comme les 4 autres builders
    # (l'audit S1.5 a relevé que _build_patrimoine bypassait ces helpers).
    # Nuance §4.1 : si tone neutre mais mutualisation active OU patrimoine
    # vide, on remonte à POSITIVE (différenciateur §4.1 ne tombe jamais en
    # neutre quand l'effet portefeuille est documenté).
    narrative_tone = _compute_tone(non_conformes, a_risque, conformite_score)
    if narrative_tone == NarrativeTone.NEUTRAL and (economie_mutualisation_eur > 0 or sites_count == 0):
        narrative_tone = NarrativeTone.POSITIVE

    # Provenance HIGH conditionnée à la mutualisation (différenciateur §4.1) —
    # critère distinct des 3 autres builders (qui conditionnent sur
    # conformite_score), donc on garde l'appel direct mais explicitement
    # documenté comme déviation intentionnelle.
    confidence = (
        ProvenanceConfidence.HIGH if economie_mutualisation_eur > 0 and sites_count > 0 else ProvenanceConfidence.MEDIUM
    )
    provenance = build_provenance(
        source="Patrimoine PROMEOS + simulation mutualisation Décret 2019-771",
        confidence=confidence,
        updated_at=datetime.now(timezone.utc),
        methodology_url="/methodologie/patrimoine-mutualisation",
    )

    return Narrative(
        page_key="patrimoine",
        persona="daily",
        kicker=kicker,
        title=title,
        italic_hook=italic_hook,
        narrative=narrative,
        narrative_tone=narrative_tone,
        kpis=tuple(kpis),
        week_cards=tuple(week_cards),
        fallback_body=fallback_body,
        provenance=provenance,
    )


# ── Builder conformite (Sprint 1.4 — DAF Marie + CFO Jean-Marc) ──────


def _build_conformite(
    db: Session,
    org_id: int,
    org_name: str,
    sites_count: int,
) -> Narrative:
    """Sprint 1.4 — Vue Conformité réglementaire.

    Promesse §4.3 doctrine : « La conformité devient une trajectoire claire
    avec étapes, échéances, scénarios. Pas un tableau d'obligations à
    cocher — un récit de progression. »

    Sert Marie ("que dois-je faire et quand ?") + Jean-Marc ("échéancier
    provisionnement € par jalon"). Audit Navigation fin S1 : Conformité
    reçoit 5/8 CTAs week-cards des 3 pages migrées — destination la plus
    sollicitée, à doctriner en priorité.

    Réutilise :
      - KpiService (compliance_score, financial_risk_eur)
      - DATE_DEADLINE_P1 audit_sme_service (11/10/2026)
      - StatutConformite (non_conformes / a_risque)
      - compute_mutualisation pour économie cumulée
    """
    from datetime import date

    # Sprint 1.4bis : helper centralisé
    ctx = _load_org_context(db, org_id)
    risque_total = ctx.risque_total  # noqa: F841 (réservé S2 chantier α exposition)
    conformite_score = ctx.conformite_score
    non_conformes = ctx.non_conformes
    a_risque = ctx.a_risque
    en_derive = ctx.en_derive  # noqa: F841 (réservé future enrichment Conformité)

    # ── Échéances réglementaires §8.3 doctrine ──
    today = date.today()

    # Audit SMÉ deadline — constante doctrine inviolable §8.3
    AUDIT_SME_DEADLINE = date(2026, 10, 11)
    days_until_audit_sme = (AUDIT_SME_DEADLINE - today).days

    # OPERAT déclaration annuelle — 30 septembre N pour conso N-1.
    operat_year = today.year if today.month < 9 else today.year + 1
    operat_deadline = date(operat_year, 9, 30)
    days_until_operat = (operat_deadline - today).days

    # BACS classe C 2030 (Décret 2020-887)
    BACS_DEADLINE = date(2030, 1, 1)
    days_until_bacs = (BACS_DEADLINE - today).days

    # Pénalité provisionnable (provision comptable CFO)
    provision_penalite_eur = non_conformes * 7500.0 + a_risque * 3750.0

    # ── Kicker + titre ──
    kicker = (
        f"CONFORMITÉ · {sites_count} SITE{'S' if sites_count > 1 else ''} · AUDIT ÉNERGÉTIQUE J-{days_until_audit_sme}"
        if days_until_audit_sme >= 0
        else f"CONFORMITÉ · {sites_count} SITE{'S' if sites_count > 1 else ''}"
    )
    title = "Conformité réglementaire"
    italic_hook = "trajectoire 2030 et échéances par jalon"

    # ── Narrative 2-3 lignes orientée "que faire et quand" ──
    narr_parts = []
    if days_until_audit_sme > 0 and days_until_audit_sme <= 365:
        narr_parts.append(
            f"Audit énergétique obligatoire dans {days_until_audit_sme} jours "
            f"({AUDIT_SME_DEADLINE.strftime('%d/%m/%Y')}, Loi 2025-391)."
        )
    if non_conformes > 0:
        narr_parts.append(
            f"{non_conformes} site{'s' if non_conformes > 1 else ''} non conforme"
            f"{'s' if non_conformes > 1 else ''} — provisionner "
            f"{_fmt_eur_short(provision_penalite_eur)} de pénalités potentielles."
        )
    elif a_risque > 0:
        narr_parts.append(
            f"{a_risque} site{'s' if a_risque > 1 else ''} sous tension sur la "
            "trajectoire 2030 — audit énergétique recommandé."
        )
    elif conformite_score is not None and conformite_score >= 75:
        narr_parts.append(
            "Patrimoine bien positionné sur la trajectoire 2030 — maintenir la qualité des déclarations OPERAT."
        )
    narr_parts.append(
        f"Score consolidé {conformite_score}/100 (Décret n°2019-771)."
        if conformite_score is not None
        else "Score consolidé en cours d'évaluation."
    )
    narrative = " ".join(narr_parts)

    # ── 3 KPIs hero §5 ──
    kpis: list[NarrativeKpi] = [
        NarrativeKpi(
            label="Trajectoire 2030",
            value=f"{conformite_score}/100" if conformite_score is not None else "—",
            tooltip=(
                "Score pondéré DT 45 % · BACS 30 % · APER 25 % "
                "(Décret n°2019-771, jalons -40 %/2030, -50 %/2040, -60 %/2050)."
            ),
            source="RegOps + Décret 2019-771",
        ),
        NarrativeKpi(
            label="Provision pénalités",
            value=_fmt_eur_short(provision_penalite_eur),
            tooltip=(
                "Pénalités potentielles cumulées : 7 500 €/site non conforme + "
                "3 750 €/site à risque (Décret n°2019-771)."
            ),
            source="Décret 2019-771",
        ),
        NarrativeKpi(
            label="Prochaine échéance",
            value=(
                f"J-{days_until_audit_sme}"
                if 0 <= days_until_audit_sme < days_until_operat
                else f"J-{days_until_operat}"
                if days_until_operat >= 0
                else "—"
            ),
            tooltip=(
                f"Audit énergétique obligatoire {AUDIT_SME_DEADLINE.strftime('%d/%m/%Y')} "
                f"(Loi 2025-391) · Déclaration OPERAT {operat_deadline.strftime('%d/%m/%Y')} "
                "(Décret 2019-771)."
            ),
            source="Calendrier réglementaire",
        ),
    ]

    # ── Week-cards Conformité par jalon ──
    week_cards: list[NarrativeWeekCard] = []

    if 0 <= days_until_audit_sme <= 365:
        # Sprint 1.4bis /simplify Quality P0 : ternaire no-op corrigé.
        # Avant : `type="todo" if urgency=="todo" else "todo"` (toujours todo,
        # masque le signal critical). Désormais drift si <90j (signal ATF
        # plus visible : "À regarder" rouge), sinon todo standard.
        is_critical = days_until_audit_sme <= 90
        week_cards.append(
            NarrativeWeekCard(
                type="drift" if is_critical else "todo",
                title=(f"Audit énergétique obligatoire J-{days_until_audit_sme}"),
                body=(
                    "Diagnostic ISO 50001 ou audit Art. L233-1 du code de "
                    f"l'énergie — échéance {AUDIT_SME_DEADLINE.strftime('%d/%m/%Y')} "
                    "(Loi 2025-391). Démarrer le marché 90 jours avant."
                ),
                cta_path="/conformite?tab=execution",
                cta_label="Lancer l'audit",
                urgency_days=days_until_audit_sme,
            )
        )

    if non_conformes > 0:
        week_cards.append(
            NarrativeWeekCard(
                type="todo",
                title=(f"Provisionner {_fmt_eur_short(non_conformes * 7500.0)} de pénalités"),
                body=(
                    f"{non_conformes} site{'s' if non_conformes > 1 else ''} "
                    f"non conforme{'s' if non_conformes > 1 else ''} — "
                    "déclaration OPERAT 2024 + plan de réduction conso "
                    "à activer avant le prochain CODIR."
                ),
                cta_path="/conformite?tab=execution",
                cta_label="Plan d'actions",
                impact_eur=non_conformes * 7500.0,
                urgency_days=180,
            )
        )

    if 0 <= days_until_operat <= 90:
        week_cards.append(
            NarrativeWeekCard(
                type="watch",
                title=(f"Déclaration OPERAT {operat_year} J-{days_until_operat}"),
                body=(
                    "Déclaration annuelle conso énergétique sur la plateforme "
                    "OPERAT (ADEME) avant le 30 septembre — sites tertiaires "
                    "≥ 1 000 m²."
                ),
                cta_path="/conformite?tab=donnees",
                cta_label="Préparer la déclaration",
                urgency_days=days_until_operat,
            )
        )

    if non_conformes == 0 and a_risque == 0 and conformite_score is not None and conformite_score >= 75:
        week_cards.append(
            NarrativeWeekCard(
                type="good_news",
                title="Trajectoire 2030 tenue",
                body=(
                    f"Score {conformite_score}/100 — patrimoine bien positionné. "
                    f"BACS classe C obligatoire dans {days_until_bacs // 30} mois."
                ),
            )
        )

    fallback_body = (
        "Calendrier réglementaire 2026-2030 sous contrôle — aucune échéance critique dans les 90 prochains jours."
    )

    # Sprint 1.4bis : helpers _compute_tone (urgency_critical=audit <90j)
    # + _build_provenance_canonical.
    audit_imminent = 0 <= days_until_audit_sme <= 90
    narrative_tone = _compute_tone(non_conformes, a_risque, conformite_score, urgency_critical=audit_imminent)
    # Conformité bascule TENSION si audit dans année (90-365j) même sans
    # site à risque — préservé depuis l'implémentation S1.4.
    if narrative_tone == NarrativeTone.NEUTRAL and 0 <= days_until_audit_sme <= 365:
        narrative_tone = NarrativeTone.TENSION

    provenance = _build_provenance_canonical(
        "RegOps + Calendrier réglementaire 2026-2030",
        conformite_score=conformite_score,
        sites_count=sites_count,
    )

    return Narrative(
        page_key="conformite",
        persona="daily",
        kicker=kicker,
        title=title,
        italic_hook=italic_hook,
        narrative=narrative,
        narrative_tone=narrative_tone,
        kpis=tuple(kpis),
        week_cards=tuple(week_cards),
        fallback_body=fallback_body,
        provenance=provenance,
    )


# ── Builder bill_intel (Sprint 1.5 — CFO Jean-Marc + DAF Marie) ──────


def _build_bill_intel(
    db: Session,
    org_id: int,
    org_name: str,
    sites_count: int,
) -> Narrative:
    """Sprint 1.5 — Vue Bill Intelligence (shadow billing v4.2).

    Promesse §4.4 doctrine : « Audit factures, détection anomalies,
    contestations, récupération. Chaque ligne de facture est challengeable.
    TURPE 7, ATRD, accises, CTA, TVA — moteur shadow v4.2 compare aux
    barèmes en vigueur et explique les écarts. »

    Sert Jean-Marc (€ à récupérer immédiatement) + Marie (qu'est-ce qui
    cloche dans ma facture ?). Audit Investisseur fin S1.4 demande
    /bill-intel comme preuve de scaling au-delà du régulatoire.

    Réutilise :
      - BillingInsight (anomalies détectées par shadow v4.2)
      - InsightStatus (open / ack / resolved / false_positive)
      - estimated_loss_eur (perte chiffrée par anomalie)
      - 17 mécanismes shadow v4.2 (TURPE 7 / ATRD T1-T4-TP / accises élec
        et gaz / CTA gaz additive / TVA / CSPE / capacité / CEE / TDN…)
    """
    from models import (
        BillingInsight,
        EntiteJuridique,
        Portefeuille,
        Site,
        not_deleted,
    )
    from models.enums import InsightStatus

    # Sprint 1.4bis : helper centralisé (sites + scope)
    ctx = _load_org_context(db, org_id)
    site_ids = [s.id for s in ctx.sites]

    # ── Récupérer les insights de facturation par scope ──
    insights_q = (
        db.query(BillingInsight)
        .join(Site, Site.id == BillingInsight.site_id)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )
    insights = insights_q.all() if site_ids else []

    open_insights = [i for i in insights if i.insight_status == InsightStatus.OPEN]
    ack_insights = [i for i in insights if i.insight_status == InsightStatus.ACK]
    resolved_insights = [i for i in insights if i.insight_status == InsightStatus.RESOLVED]

    nb_anomalies_open = len(open_insights)
    nb_contestations = len(ack_insights)
    nb_reclaims = len(resolved_insights)

    # Pertes chiffrées
    perte_open_eur = sum((i.estimated_loss_eur or 0.0) for i in open_insights)
    contestation_eur = sum((i.estimated_loss_eur or 0.0) for i in ack_insights)
    reclaim_ytd_eur = sum((i.estimated_loss_eur or 0.0) for i in resolved_insights)

    # ── Kicker + titre ──
    week_iso = datetime.now(timezone.utc).isocalendar().week
    kicker = f"FACTURATION · SEMAINE {week_iso} · {sites_count} SITE{'S' if sites_count > 1 else ''}"
    title = "Vos factures — vérifiées, recalculées, expliquées"
    italic_hook = "shadow billing v4.2"

    # ── Narrative orientée € à récupérer ──
    narr_parts = []
    if nb_anomalies_open > 0:
        narr_parts.append(
            f"{nb_anomalies_open} anomalie{'s' if nb_anomalies_open > 1 else ''} "
            f"détectée{'s' if nb_anomalies_open > 1 else ''} sur vos factures — "
            f"perte estimée {_fmt_eur_short(perte_open_eur)} à récupérer."
        )
    elif sites_count > 0:
        narr_parts.append(
            f"Aucune anomalie ouverte sur vos {sites_count} site"
            f"{'s' if sites_count > 1 else ''} — facturation sous contrôle."
        )

    if nb_contestations > 0:
        narr_parts.append(
            f"{nb_contestations} contestation{'s' if nb_contestations > 1 else ''} en cours auprès des fournisseurs."
        )

    if reclaim_ytd_eur > 0:
        narr_parts.append(f"Récupérations validées YTD : {_fmt_eur_short(reclaim_ytd_eur)} (reclaims confirmés).")
    narr_parts.append(
        "Shadow billing PROMEOS recalcule chaque ligne : TURPE 7, accise, "
        "contribution acheminement (CTA), TVA, capacité (CRE)."
    )
    narrative = " ".join(narr_parts)

    # ── 3 KPIs hero §5 — angle CFO ──
    kpis: list[NarrativeKpi] = [
        NarrativeKpi(
            label="Anomalies à traiter",
            value=str(nb_anomalies_open) if nb_anomalies_open >= 0 else "—",
            tooltip=(
                "Nombre d'anomalies détectées par le moteur shadow v4.2 et "
                "non encore traitées (status open). Comparaison facture vs "
                "barèmes officiels CRE/JORF."
            ),
            source="Shadow Billing v4.2",
        ),
        NarrativeKpi(
            label="Pertes à récupérer",
            value=_fmt_eur_short(perte_open_eur),
            tooltip=(
                "Cumul des pertes estimées sur les anomalies ouvertes. "
                "Récupérables via contestation auprès du fournisseur."
            ),
            source="Bill-Intel",
        ),
        NarrativeKpi(
            label="Récupérations YTD",
            value=_fmt_eur_short(reclaim_ytd_eur),
            tooltip=(
                "Cumul des reclaims validés depuis le début de l'année — "
                "économies déjà encaissées grâce aux contestations."
            ),
            source="Bill-Intel reclaims",
        ),
    ]

    # ── Week-cards Bill-Intel ──
    week_cards: list[NarrativeWeekCard] = []

    # Anomalies critiques (perte > 500€) en priorité
    critical_open = [i for i in open_insights if (i.estimated_loss_eur or 0) >= 500]
    if critical_open:
        top = critical_open[0]
        week_cards.append(
            NarrativeWeekCard(
                type="drift",
                title=(f"Anomalie facture · {_fmt_eur_short(top.estimated_loss_eur or 0)}"),
                body=(
                    (top.message[:120] if top.message else "Écart détecté")
                    + " — moteur shadow v4.2 a recalculé la facture."
                ),
                cta_path=f"/bill-intel?insight={top.id}",
                cta_label="Voir l'anomalie",
                impact_eur=top.estimated_loss_eur or 0,
            )
        )

    if nb_anomalies_open > (1 if critical_open else 0):
        remaining = nb_anomalies_open - (1 if critical_open else 0)
        week_cards.append(
            NarrativeWeekCard(
                type="todo",
                title=(f"Formaliser {remaining} contestation{'s' if remaining > 1 else ''}"),
                body=(
                    "Chaque anomalie ouvre droit à contestation auprès du "
                    "fournisseur — récupération typique 30-90 jours."
                ),
                cta_path="/bill-intel?status=open",
                cta_label="Liste contestations",
                impact_eur=perte_open_eur,
                urgency_days=90,
            )
        )

    if reclaim_ytd_eur > 0:
        week_cards.append(
            NarrativeWeekCard(
                type="good_news",
                title=f"{_fmt_eur_short(reclaim_ytd_eur)} récupérés YTD",
                body=(
                    f"{nb_reclaims} reclaim{'s' if nb_reclaims > 1 else ''} "
                    "validé(s) — économies encaissées grâce au shadow billing."
                ),
                impact_eur=reclaim_ytd_eur,
            )
        )

    fallback_body = (
        "Aucune anomalie critique détectée cette semaine — facturation alignée sur les barèmes officiels CRE/JORF."
    )

    # Sprint 1.4bis : helpers _compute_tone + _build_provenance_canonical
    # Tone CRITICAL si pertes > 1 k€, TENSION si anomalies non traitées,
    # POSITIVE si récupérations actives.
    if perte_open_eur >= 1000:
        narrative_tone = NarrativeTone.CRITICAL
    elif nb_anomalies_open > 0:
        narrative_tone = NarrativeTone.TENSION
    elif reclaim_ytd_eur > 0:
        narrative_tone = NarrativeTone.POSITIVE
    else:
        narrative_tone = NarrativeTone.NEUTRAL

    provenance = _build_provenance_canonical(
        "Bill-Intel shadow v4.2 + 17 mécanismes (TURPE 7 / ATRD / accise / CTA / TVA)",
        conformite_score=ctx.conformite_score,
        sites_count=sites_count,
        methodology_url="/methodologie/bill-intel-shadow",
    )

    return Narrative(
        page_key="bill_intel",
        persona="daily",
        kicker=kicker,
        title=title,
        italic_hook=italic_hook,
        narrative=narrative,
        narrative_tone=narrative_tone,
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
    "conformite": _build_conformite,
    "bill_intel": _build_bill_intel,
    # Sprint 1.6+ : ajouter achat, monitoring, diagnostic, anomalies, flex.
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
