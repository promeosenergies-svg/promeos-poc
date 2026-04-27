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
from datetime import date, datetime, timedelta, timezone
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
    "achat_energie",
    "monitoring",
    "diagnostic",
    "anomalies",
    "flex",
]
# Sprint 1.8 — diagnostic ajouté ; cohérent SUPPORTED_PAGE_KEYS + _BUILDERS.


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


def _build_provenance_volume_based(
    source: str,
    *,
    has_data: bool,
    sites_count: int,
    methodology_url: str,
) -> "Provenance":
    """Provenance pour vues volume-based (monitoring/diagnostic).

    Sprint 1.8bis Reuse P1 (audit /simplify) : pattern monitoring + diagnostic
    dupliqué — confidence cascade HIGH/MEDIUM/LOW selon présence données réelles.
    Différent de _build_provenance_canonical (basé conformite_score statique).
    """
    if has_data and sites_count > 0:
        confidence = ProvenanceConfidence.HIGH
    elif sites_count > 0:
        confidence = ProvenanceConfidence.MEDIUM
    else:
        confidence = ProvenanceConfidence.LOW
    return build_provenance(
        source=source,
        confidence=confidence,
        updated_at=datetime.now(timezone.utc),
        methodology_url=methodology_url,
    )


def _s(n: int) -> str:
    """Helper pluriel FR (audit /simplify Quality P2 — pattern dupliqué 15+×)."""
    return "s" if n > 1 else ""


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
    # Sprint 1.7bis /simplify Quality P1 : `date` désormais top-level (l.27).
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


# Sprint 1.6bis — constantes module nommées (audit /simplify Quality P1).
# Sourçage doctrine §4.5 + observatoire CRE T4 2025.
_ACHAT_SITE_MEDIAN_ANNUAL_KWH = 250_000  # = 250 MWh/an — benchmark ETI tertiaire moyen
_ACHAT_DEFAULT_VOLUME_EUR_PER_CONTRACT = 50_000  # plancher contrat ETI tertiaire
_ACHAT_ECONOMIE_TAUX_BENCHMARK = 0.08  # CRE T4 2025 médiane B2B post-ARENH 30 fournisseurs
_ACHAT_SEUIL_GOOD_NEWS_EUR = 5_000  # seuil signal positif économie identifiée
_ACHAT_SEUIL_CRITIQUE_VOLUME_EUR = 100_000  # exposition forte → tone CRITICAL


def _build_achat_energie(
    db: Session,
    org_id: int,
    org_name: str,
    sites_count: int,
) -> Narrative:
    """Sprint 1.6 — Vue Achat énergie post-ARENH (différenciateur §4.5).

    Promesse §4.5 doctrine : « Neutralité fournisseur — PROMEOS ne vend
    pas d'énergie. Comparaison transparente des 30+ fournisseurs CRE,
    shadow billing 6 composantes (TURPE 7 / accise / CTA / capacité Nov
    2026 / ATRD7 / VNU post-ARENH) pour challenger chaque offre. »

    Sert Jean-Marc CFO (échéances + volume exposé) + Marie DAF
    (renouvellements à formaliser) + Investisseur (preuve neutralité
    non-fournisseur, moat durable vs Advizeo/Deepki/Trinergy).

    Données réelles :
      - EnergyContract : end_date, supplier_name, price_ref_eur_per_kwh
      - Volume estimé via prix réf × ~250 MWh/site (benchmark ETI)
      - Heuristique économie 8% (médiane CRE T4 2025 sur appels d'offres
        post-ARENH B2B 30 fournisseurs).

    Sprint 1.6bis : doctrine §4.6→§4.5 (Achat est §4.5, Flex est §4.6),
    triple JOIN simplifié via site_ids.in_(), magic numbers extraits en
    constantes module, neutralité hissée dans italic_hook.
    """
    from models import EnergyContract, not_deleted

    ctx = _load_org_context(db, org_id)
    site_ids = [s.id for s in ctx.sites]

    # ── Récupérer les contrats actifs du scope ──
    # Sprint 1.6bis /simplify Efficiency P1 : site_ids déjà org-scopé via
    # _load_org_context — pas besoin de re-joindre Site→Portefeuille→EJ.
    today = date.today()
    if site_ids:
        contracts = (
            not_deleted(db.query(EnergyContract), EnergyContract).filter(EnergyContract.site_id.in_(site_ids)).all()
        )
    else:
        contracts = []

    # Single-pass partitionnement (Efficiency P2) : 1 itération vs 4.
    horizon_12m = today + timedelta(days=365)
    horizon_90j = today + timedelta(days=90)
    actifs: list[EnergyContract] = []
    echeance_12m: list[EnergyContract] = []
    echeance_90j: list[EnergyContract] = []
    for c in contracts:
        if c.end_date is not None and c.end_date < today:
            continue
        actifs.append(c)
        if c.end_date and c.end_date <= horizon_12m:
            echeance_12m.append(c)
            if c.end_date <= horizon_90j:
                echeance_90j.append(c)

    nb_contrats = len(actifs)
    nb_echeance_12m = len(echeance_12m)
    nb_echeance_90j = len(echeance_90j)

    # ── Volume EUR exposé sur renouvellements <12 mois ──
    # Quality P1 : explicit branching plutôt que max() — clarifie l'intention
    # (None → plancher, sinon prix × volume). Unités : prix en €/kWh × kWh = €.
    def _contract_volume_eur(c: EnergyContract) -> float:
        if c.price_ref_eur_per_kwh:
            return c.price_ref_eur_per_kwh * _ACHAT_SITE_MEDIAN_ANNUAL_KWH
        return float(_ACHAT_DEFAULT_VOLUME_EUR_PER_CONTRACT)

    volume_expose_eur = sum(_contract_volume_eur(c) for c in echeance_12m)
    economie_potentielle_eur = volume_expose_eur * _ACHAT_ECONOMIE_TAUX_BENCHMARK

    # ── Kicker + titre + italic hook §5 ──
    # Sprint 1.6bis P0-3/P0-4 : neutralité hissée en italic_hook
    # (différenciateur §4.5 visible 10s investisseur + Marie). Acronymes
    # nus retirés de la narrative — reformulation en français.
    week_iso = datetime.now(timezone.utc).isocalendar().week
    kicker = f"ACHAT ÉNERGIE · SEMAINE {week_iso} · {nb_contrats} CONTRAT{'S' if nb_contrats != 1 else ''}"
    title = "Vos contrats énergie"
    italic_hook = "PROMEOS ne vend pas d'énergie · 30+ offres CRE comparées"

    # ── Narrative orientée Jean-Marc (€ exposé / écart marché) ──
    narr_parts = []
    if nb_echeance_90j > 0:
        narr_parts.append(
            f"{nb_echeance_90j} contrat{'s' if nb_echeance_90j > 1 else ''} "
            f"arrive{'nt' if nb_echeance_90j > 1 else ''} à échéance dans les "
            "90 jours — préavis 1 à 3 mois selon contrat, fenêtre critique pour "
            "ne pas reconduire tacitement."
        )
    if nb_echeance_12m > nb_echeance_90j:
        suite = nb_echeance_12m - nb_echeance_90j
        narr_parts.append(
            f"{suite} renouvellement{'s' if suite > 1 else ''} dans les "
            "12 mois à anticiper (mise en concurrence ~6 mois avant)."
        )
    if volume_expose_eur > 0:
        narr_parts.append(
            f"Volume exposé {_fmt_eur_short(volume_expose_eur)} — économie "
            f"potentielle {_fmt_eur_short(economie_potentielle_eur)} via mise "
            "en concurrence post-ARENH."
        )
    elif nb_contrats == 0:
        narr_parts.append(
            "Aucun contrat actif référencé — importez vos contrats pour activer la comparaison neutre 30+ fournisseurs."
        )
    # Reformulation acronymes nus (audit Marie P0-1) : explication inline
    # avant chaque sigle. SolNarrative rend en plain text donc pas
    # d'<Explain> wrapper possible — on dégage le jargon.
    narr_parts.append(
        "Le moteur shadow audit 6 composantes — réseau (TURPE 7), accises "
        "énergie, contribution acheminement (CTA), capacité (RTE Nov 2026), "
        "réseau gaz (ATRD7), fond nucléaire VNU post-ARENH — face aux barèmes "
        "officiels CRE."
    )
    narrative = " ".join(narr_parts)

    # ── 3 KPIs hero §5 — angle CFO ──
    # Tooltip P0 (Jean-Marc) : exposer les hypothèses de calcul (250 MWh +
    # plancher 50 k€). Tooltip économie expose la fourchette 5-12% du
    # benchmark CRE pour rigueur.
    kpis: list[NarrativeKpi] = [
        NarrativeKpi(
            label="Échéances < 12 mois",
            value=str(nb_echeance_12m),
            unit=f"sur {nb_contrats}" if nb_contrats > 0 else None,
            tooltip=(
                "Nombre de contrats énergie arrivant à échéance dans les "
                "12 prochains mois. Anticiper la mise en concurrence 6 mois "
                "avant pour challenger 30+ fournisseurs."
            ),
            source="Contrats EnergyContract.end_date",
        ),
        NarrativeKpi(
            label="Volume exposé",
            value=_fmt_eur_short(volume_expose_eur),
            tooltip=(
                "Estimation budget énergie annuel des renouvellements à "
                "venir. Calcul : prix de référence × 250 MWh/site (benchmark "
                "ETI tertiaire), avec plancher 50 k€/contrat si prix manquant."
            ),
            source="EnergyContract + benchmark CRE 250 MWh/site",
        ),
        NarrativeKpi(
            label="Économie potentielle",
            value=_fmt_eur_short(economie_potentielle_eur),
            tooltip=(
                "Estimation conservative ~8 % du volume exposé, médiane "
                "observatoire CRE T4 2025 (fourchette publique 5-12 %). "
                "Détail méthodologie /methodologie/achat-post-arenh."
            ),
            source="Observatoire CRE T4 2025",
        ),
    ]

    # ── Week-cards Achat ──
    week_cards: list[NarrativeWeekCard] = []

    # Échéance critique <90j sur contrat à fort volume.
    # Sprint 1.6bis P0-2 : ?tab=renewals → ?tab=echeances (TABS frontend
    # déclare 'echeances' pas 'renewals' — fallback silencieux corrigé).
    # P1 (CFO) : DRIFT week-card transporte impact_eur pour priorisation.
    if echeance_90j:
        critical = min(echeance_90j, key=lambda c: c.end_date or today)
        days_left = (critical.end_date - today).days if critical.end_date else 90
        critical_volume = _contract_volume_eur(critical)
        week_cards.append(
            NarrativeWeekCard(
                type="drift",
                title=(f"Renouvellement urgent · {critical.supplier_name or 'fournisseur'} (J-{days_left})"),
                body=(
                    "Préavis 1 à 3 mois selon contrat — agir maintenant pour "
                    "ne pas reconduire tacitement. Lancer l'appel d'offres pour "
                    "comparer 30+ fournisseurs CRE."
                ),
                cta_path="/achat-energie?tab=echeances",
                cta_label="Voir échéances",
                impact_eur=critical_volume,
                urgency_days=days_left,
            )
        )

    if nb_echeance_12m > nb_echeance_90j:
        remaining = nb_echeance_12m - nb_echeance_90j
        week_cards.append(
            NarrativeWeekCard(
                type="todo",
                title=f"Anticiper {remaining} renouvellement{'s' if remaining > 1 else ''}",
                body=(
                    "Mise en concurrence 6 mois avant échéance pour négocier "
                    "dans les meilleures conditions — économie type 8 % sur "
                    "volume exposé (médiane CRE T4 2025)."
                ),
                cta_path="/achat-energie?tab=simulation",
                cta_label="Simuler scénarios",
                impact_eur=economie_potentielle_eur,
                urgency_days=180,
            )
        )

    if economie_potentielle_eur > _ACHAT_SEUIL_GOOD_NEWS_EUR:
        week_cards.append(
            NarrativeWeekCard(
                type="good_news",
                title=f"{_fmt_eur_short(economie_potentielle_eur)} d'écart marché identifié",
                body=(
                    "Différentiel entre vos contrats actuels et les conditions "
                    "marché post-ARENH. Comparer les offres en 5 minutes via "
                    "les scénarios PROMEOS."
                ),
                cta_path="/achat-energie?tab=simulation",
                cta_label="Comparer offres",
                impact_eur=economie_potentielle_eur,
            )
        )

    fallback_body = (
        "Aucune échéance contractuelle imminente — patrimoine sous "
        "couverture. PROMEOS surveille les opportunités marché en continu."
    )

    # Tone : CRITICAL si <90j sur contrat exposé fort, TENSION si plusieurs
    # échéances 12 mois, POSITIVE si économie identifiée significative,
    # NEUTRAL sinon.
    if nb_echeance_90j > 0 and volume_expose_eur >= _ACHAT_SEUIL_CRITIQUE_VOLUME_EUR:
        narrative_tone = NarrativeTone.CRITICAL
    elif nb_echeance_12m > 0:
        narrative_tone = NarrativeTone.TENSION
    elif economie_potentielle_eur > _ACHAT_SEUIL_GOOD_NEWS_EUR:
        narrative_tone = NarrativeTone.POSITIVE
    else:
        narrative_tone = NarrativeTone.NEUTRAL

    provenance = _build_provenance_canonical(
        "Achat post-ARENH + 30 fournisseurs CRE + shadow billing 6 composantes",
        conformite_score=ctx.conformite_score,
        sites_count=sites_count,
        methodology_url="/methodologie/achat-post-arenh",
    )

    return Narrative(
        page_key="achat_energie",
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


# Sprint 1.7 — constantes module Monitoring (audit /simplify Quality).
# Sourçage doctrine §4.2 (EMS/Performance) + ISO 50001 + COSTIC.
# ISO 50001 §8.5.1 demande des « données fiables et reproductibles » sans
# valeur chiffrée — le seuil 80 est un choix produit calibré sur observations
# pilote Enedis SGE (complétude ≥ 95% requise pour audit SMÉ formel).
_MONITORING_DATA_QUALITY_GOOD = 80  # seuil score qualité données satisfaisante (pilotage fiable)
_MONITORING_DATA_QUALITY_CRITICAL = 50  # seuil score qualité critique (recommandation réinstrumentation)
# COSTIC NF EN 16247-2 §6 : impact ≥ 0,5 % budget annuel énergie d'un site = significatif.
# 1 000 € = plancher CFO ETI tertiaire (≈5 GWh/an, 250 k€ budget énergie typique).
# Cohérent avec _build_bill_intel ligne 1201 (même seuil critique).
_MONITORING_SEUIL_IMPACT_CRITIQUE_EUR = 1_000  # impact € cumulé → tone CRITICAL


def _build_monitoring(
    db: Session,
    org_id: int,
    org_name: str,
    sites_count: int,
) -> Narrative:
    """Sprint 1.7 — Vue Monitoring Performance Électrique (différenciateur §4.2).

    Promesse §4.2 doctrine : « Performance et diagnostics — pilotage temps
    réel, KPIs électriques, qualité données, alertes automatiques.
    Conforme ISO 50001 + COSTIC. »

    Sert Marie DAF (« est-ce que ça marche bien ? »), Energy Manager
    (alertes + dérives), Investisseur (preuve EMS pillar §4.2).

    Données réelles :
      - MonitoringSnapshot : data_quality_score, kpis_json (load_factor,
        pmax_kw, total_kwh)
      - MonitoringAlert : status (open/ack/resolved), severity (info/
        warning/high/critical), estimated_impact_eur

    Doctrine §10 « simplifier la complexité » — vocabulaire FR pour
    non-sachants : alertes au lieu de NEBCO/aFRR jargon.
    """
    from models.energy_models import (
        AlertSeverity,
        AlertStatus,
        MonitoringAlert,
        MonitoringSnapshot,
    )

    from sqlalchemy import func

    ctx = _load_org_context(db, org_id)
    site_ids = [s.id for s in ctx.sites]
    # Sprint 1.7bis Quality P1 : dict pré-calculé pour lookup O(1) dans
    # week-cards. Évite next((s.nom for s in ctx.sites if s.id == X)) O(n)
    # par alerte critique.
    site_name_by_id: dict[int, str] = {s.id: (s.nom or f"site #{s.id}") for s in ctx.sites}

    # ── Récupérer les alertes actives + dernier snapshot par site ──
    # Sprint 1.7bis Efficiency P1-A : snapshot query bornée. Subquery
    # MAX(created_at) GROUP BY site_id puis JOIN — résultat = len(site_ids)
    # rows max au lieu de toute l'historique (évite 900 rows pour 10 sites).
    if site_ids:
        alerts = db.query(MonitoringAlert).filter(MonitoringAlert.site_id.in_(site_ids)).all()
        latest_subq = (
            db.query(
                MonitoringSnapshot.site_id,
                func.max(MonitoringSnapshot.created_at).label("max_created"),
            )
            .filter(MonitoringSnapshot.site_id.in_(site_ids))
            .group_by(MonitoringSnapshot.site_id)
            .subquery()
        )
        snapshots = (
            db.query(MonitoringSnapshot)
            .join(
                latest_subq,
                (MonitoringSnapshot.site_id == latest_subq.c.site_id)
                & (MonitoringSnapshot.created_at == latest_subq.c.max_created),
            )
            .all()
        )
    else:
        alerts = []
        snapshots = []

    # Single-pass partitioning des alertes
    open_alerts: list[MonitoringAlert] = []
    critical_alerts: list[MonitoringAlert] = []
    impact_total_eur = 0.0
    for a in alerts:
        if a.status == AlertStatus.OPEN:
            open_alerts.append(a)
            impact_total_eur += a.estimated_impact_eur or 0.0
            if a.severity == AlertSeverity.CRITICAL:
                critical_alerts.append(a)

    nb_alerts_open = len(open_alerts)
    nb_alerts_critical = len(critical_alerts)

    # Score qualité données : moyenne des derniers snapshots par site.
    # Sprint 1.7bis : snapshots retourne déjà 1 row par site (subquery MAX),
    # plus besoin de dédupliquer en Python.
    quality_scores = [s.data_quality_score for s in snapshots if s.data_quality_score is not None]
    data_quality_avg = round(sum(quality_scores) / len(quality_scores)) if quality_scores else None
    sites_monitored = len(snapshots)

    # ── Kicker + titre + italic hook §5 ──
    week_iso = datetime.now(timezone.utc).isocalendar().week
    if nb_alerts_open > 0:
        kicker = (
            f"MONITORING · SEMAINE {week_iso} · "
            f"{nb_alerts_open} ALERTE{'S' if nb_alerts_open > 1 else ''} ACTIVE{'S' if nb_alerts_open > 1 else ''}"
        )
    else:
        kicker = f"MONITORING · SEMAINE {week_iso} · {sites_monitored} SITE{'S' if sites_monitored != 1 else ''} SUIVI{'S' if sites_monitored != 1 else ''}"
    title = "Vos sites énergie en temps réel"
    italic_hook = "performance · alertes · qualité données"

    # ── Narrative orientée Marie DAF + Energy Manager ──
    # Sprint 1.7bis P0 (audit Marie + CX) : reformulations « intervention
    # immédiate » → « à corriger sous 7 jours », « warnings » → « alertes
    # secondaires » (FR-first §10), ISO 50001 explicité « norme management
    # énergie » (acronyme nu interdit).
    narr_parts = []
    if nb_alerts_critical > 0:
        narr_parts.append(
            f"{nb_alerts_critical} alerte{'s' if nb_alerts_critical > 1 else ''} "
            f"critique{'s' if nb_alerts_critical > 1 else ''} sur votre patrimoine — "
            "à corriger cette semaine pour limiter l'impact."
        )
    elif nb_alerts_open > 0:
        narr_parts.append(
            f"{nb_alerts_open} alerte{'s' if nb_alerts_open > 1 else ''} "
            f"active{'s' if nb_alerts_open > 1 else ''} sur votre patrimoine — "
            "à programmer selon priorité."
        )
    elif sites_monitored > 0:
        narr_parts.append(
            f"{sites_monitored} site{'s' if sites_monitored > 1 else ''} sous "
            "surveillance — aucune dérive détectée cette semaine."
        )
    else:
        narr_parts.append("Aucun site sous surveillance active — lancez l'analyse pour activer le pilotage temps réel.")

    if impact_total_eur >= _MONITORING_SEUIL_IMPACT_CRITIQUE_EUR:
        narr_parts.append(f"Impact estimé : {_fmt_eur_short(impact_total_eur)} récupérables par correction.")

    if data_quality_avg is not None:
        if data_quality_avg >= _MONITORING_DATA_QUALITY_GOOD:
            narr_parts.append(f"Qualité des relevés {data_quality_avg}/100 — pilotage fiable.")
        elif data_quality_avg < _MONITORING_DATA_QUALITY_CRITICAL:
            narr_parts.append(
                f"Qualité des relevés {data_quality_avg}/100 — fiabilité dégradée, vérifier la collecte compteur."
            )

    narr_parts.append(
        "Le moteur surveille en continu la puissance contractuelle, la charge "
        "instantanée du réseau, la consommation hors heures d'ouverture et la "
        "qualité des relevés. Conforme ISO 50001 (norme management énergie) "
        "et COSTIC (méthode audit énergétique tertiaire FR)."
    )
    narrative = " ".join(narr_parts)

    # ── 3 KPIs hero §5 — angle pilotage opérationnel ──
    # Tooltips Sprint 1.7bis (audit Marie P0-3 + CX P1-3) reformulés non-sachant :
    # 1ère phrase = bénéfice CFO/DAF, 2e phrase = définition technique courte.
    kpis: list[NarrativeKpi] = [
        NarrativeKpi(
            label="Confiance données",
            value=f"{data_quality_avg}/100" if data_quality_avg is not None else "—",
            tooltip=(
                "Vos compteurs envoient-ils des données fiables ? Score 80/100 = "
                "oui, pilotage budget possible. Calculé sur 3 axes : complétude "
                "des relevés, cohérence des valeurs, régularité des intervalles."
            ),
            source="ISO 50001 §8.5.1 — données fiables et reproductibles",
        ),
        NarrativeKpi(
            label="Alertes actives",
            value=str(nb_alerts_open),
            unit=f"dont {nb_alerts_critical} critique{'s' if nb_alerts_critical > 1 else ''}"
            if nb_alerts_critical > 0
            else None,
            tooltip=(
                "Signaux de dérive détectés automatiquement et non encore traités "
                "(workflow OPEN → ACK → RESOLVED). Une alerte critique nécessite "
                "intervention sous 7 jours, les autres sont à programmer dans le mois."
            ),
            source="MonitoringAlert workflow lifecycle",
        ),
        NarrativeKpi(
            label="Impact dérives",
            value=_fmt_eur_short(impact_total_eur),
            tooltip=(
                "Estimation modélisée du surcoût annuel cumulé des alertes ouvertes "
                "(surconsommation, dépassement puissance, profil anormal). Pas une "
                "perte mesurée — montant récupérable par correction."
            ),
            source="MonitoringAlert.estimated_impact_eur · COSTIC NF EN 16247-2",
        ),
    ]

    # ── Week-cards Monitoring ──
    week_cards: list[NarrativeWeekCard] = []

    # DRIFT — alerte critique avec plus fort impact.
    # Sprint 1.7bis Quality P1 : site_name_by_id pré-calculé (lookup O(1)).
    if critical_alerts:
        top_critical = max(critical_alerts, key=lambda a: a.estimated_impact_eur or 0)
        critical_impact = top_critical.estimated_impact_eur or 0
        site_label = site_name_by_id.get(top_critical.site_id, f"site #{top_critical.site_id}")
        week_cards.append(
            NarrativeWeekCard(
                type="drift",
                title=f"Dérive critique · {site_label}",
                body=(
                    (top_critical.explanation[:140] if top_critical.explanation else "Anomalie détectée")
                    + " — agir cette semaine pour limiter l'impact."
                ),
                cta_path=f"/monitoring?site_id={top_critical.site_id}&alert={top_critical.id}",
                cta_label="Voir l'alerte",
                impact_eur=critical_impact,
                urgency_days=7,
            )
        )

    # TODO — autres alertes ouvertes à programmer.
    # Sprint 1.7bis Energy Manager P0-1 : CTA `?status=open` pour drill-down
    # liste filtrée (vs page nue qui obligeait à re-filtrer).
    # CX P1-2 : "warning" → "secondaires" + body explicite.
    other_open = nb_alerts_open - nb_alerts_critical
    if other_open > 0:
        week_cards.append(
            NarrativeWeekCard(
                type="todo",
                title=f"Programmer {other_open} action{'s' if other_open > 1 else ''} corrective{'s' if other_open > 1 else ''}",
                body=(
                    "Alertes secondaires à intégrer au plan de maintenance — "
                    "économies cumulées progressives, contribution audit ISO 50001."
                ),
                cta_path="/monitoring?status=open",
                cta_label="Voir alertes ouvertes",
                impact_eur=impact_total_eur - sum((a.estimated_impact_eur or 0) for a in critical_alerts),
                urgency_days=30,
            )
        )

    # GOOD_NEWS — qualité données fiable
    if data_quality_avg is not None and data_quality_avg >= _MONITORING_DATA_QUALITY_GOOD and nb_alerts_open == 0:
        week_cards.append(
            NarrativeWeekCard(
                type="good_news",
                title=f"Patrimoine stable · qualité {data_quality_avg}/100",
                body=(
                    "Aucune dérive détectée et collecte des relevés fiable — "
                    "pilotage en routine, base solide pour optimisation continue."
                ),
                cta_path="/diagnostic-conso",
                cta_label="Identifier leviers",
            )
        )

    fallback_body = (
        "Aucune alerte cette semaine — patrimoine sous contrôle. Le moteur "
        "surveille puissance, charge et qualité des relevés en continu."
    )

    # Sprint 1.7bis Reuse P1-1 : tone monitoring-specific. _compute_tone
    # s'appuie sur non_conformes/a_risque (statut DT), inapplicable au
    # domaine monitoring (alertes/impact). On garde la cascade inline
    # documentée — futur refactor : ajouter param domain à _compute_tone si
    # plus de 2 builders dévient (S1.8+).
    if nb_alerts_critical > 0 or impact_total_eur >= _MONITORING_SEUIL_IMPACT_CRITIQUE_EUR:
        narrative_tone = NarrativeTone.CRITICAL
    elif nb_alerts_open > 0:
        narrative_tone = NarrativeTone.TENSION
    elif data_quality_avg is not None and data_quality_avg >= _MONITORING_DATA_QUALITY_GOOD:
        narrative_tone = NarrativeTone.POSITIVE
    else:
        narrative_tone = NarrativeTone.NEUTRAL

    # Sprint 1.7bis CX P0-2 : provenance HIGH basée sur data_quality_avg
    # plutôt que conformite_score (helper canonique inadéquat pour vue
    # monitoring — un site avec data_quality 35/100 ne peut pas être HIGH).
    if data_quality_avg is not None and data_quality_avg >= _MONITORING_DATA_QUALITY_GOOD and sites_monitored > 0:
        confidence = ProvenanceConfidence.HIGH
    elif data_quality_avg is not None and data_quality_avg >= _MONITORING_DATA_QUALITY_CRITICAL:
        confidence = ProvenanceConfidence.MEDIUM
    else:
        confidence = ProvenanceConfidence.LOW

    provenance = build_provenance(
        source="Monitoring Performance Électrique + ISO 50001 + COSTIC NF EN 16247-2",
        confidence=confidence,
        updated_at=datetime.now(timezone.utc),
        methodology_url="/methodologie/performance-monitoring",
    )

    return Narrative(
        page_key="monitoring",
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


# Sprint 1.8 — constantes module Diagnostic (audit /simplify Quality).
# Sourçage doctrine §4.2 (EMS/Performance) + ISO 50001 + COSTIC.
# Seuils sévérité ConsumptionInsight alignés sur la modélisation moteur
# (cf services/consumption_diag/), pas modifiables ici.
# Sprint 1.8bis (audit /simplify Reuse P1) : _DIAGNOSTIC_SEUIL_GAIN_PRIORITE_EUR
# supprimée — dead constant jamais référencée. Sévérité critique vient du
# moteur consumption_diag/ (SoT canonique via ConsumptionInsight.severity).
_DIAGNOSTIC_SEUIL_ECONOMIE_VISIBLE_EUR = 5_000  # cumul économies → tone POSITIVE / good_news (~1% budget ETI 5 sites)

# Sprint 1.8bis (audit /simplify Quality P1) : SoT FR labels diagnostic.
# Frontend ConsumptionDiagPage.jsx:72 TYPE_LABELS dupliquait — à terme
# exposer via API serializer ConsumptionInsight.type_label.
_INSIGHT_TYPE_LABELS_FR: dict[str, str] = {
    "hors_horaires": "Consommation hors horaires",
    "base_load": "Talon excessif",
    "pointe": "Pic de puissance",
    "derive": "Dérive consommation",
    "data_gap": "Trou de données",
}


def _build_diagnostic(
    db: Session,
    org_id: int,
    org_name: str,
    sites_count: int,
) -> Narrative:
    """Sprint 1.8 — Vue Diagnostic Consommation (différenciateur §4.2).

    Promesse §4.2 doctrine : « Diagnostics consommation — détection
    automatique des anomalies (hors-horaires / talon excessif / pointes /
    dérives), chiffrage € des leviers d'économies, plan d'actions
    priorisées par effort/gain. Conforme ISO 50001 + COSTIC NF EN 16247-2. »

    Sert Marie DAF (« où sont mes économies cachées ? »), Energy Manager
    (priorisation actions), Investisseur (preuve EMS pillar §4.2 vs
    dashboards passifs Advizeo/Deepki).

    Données réelles :
      - ConsumptionInsight : type, severity, estimated_loss_eur,
        recommended_actions_json, insight_status (open/ack/resolved/
        false_positive)
      - 5 types diagnostics : hors_horaires, base_load, pointe, derive,
        data_gap

    Doctrine §10 : vocabulaire FR — « hors-horaires », « talon excessif »,
    « dérive » au lieu d'acronymes EMS jargon.
    """
    from models.consumption_insight import ConsumptionInsight
    from models.enums import InsightStatus, Severity

    ctx = _load_org_context(db, org_id)
    site_ids = [s.id for s in ctx.sites]
    site_name_by_id: dict[int, str] = {s.id: (s.nom or f"site #{s.id}") for s in ctx.sites}

    # ── Récupérer les insights de diagnostic du scope ──
    # Sprint 1.8bis Efficiency P1 : bornage YTD + 365j rolling pour éviter
    # de matérialiser tout l'historique en RAM (10k+ insights cross-org
    # possible). YTD couvre Économies sécurisées, rolling 365j couvre
    # contexte saisonnier.
    today = date.today()
    horizon_floor = min(date(today.year, 1, 1), today - timedelta(days=365))
    if site_ids:
        insights = (
            db.query(ConsumptionInsight)
            .filter(ConsumptionInsight.site_id.in_(site_ids))
            .filter(ConsumptionInsight.created_at >= datetime.combine(horizon_floor, datetime.min.time()))
            .all()
        )
    else:
        insights = []

    # Single-pass partitioning par status + severity.
    # Sprint 1.8bis Efficiency P2 : critical_total_eur dans le single-pass
    # (vs ré-itération sum() pour autres_gain).
    # Sprint 1.8bis Quality P1 : Severity enum vs stringly-typed.
    open_insights: list[ConsumptionInsight] = []
    critical_insights: list[ConsumptionInsight] = []
    resolved_insights: list[ConsumptionInsight] = []
    economies_potentielles_eur = 0.0
    economies_realisees_eur = 0.0
    critical_total_eur = 0.0
    for i in insights:
        if i.insight_status == InsightStatus.OPEN:
            open_insights.append(i)
            i_loss = i.estimated_loss_eur or 0.0
            economies_potentielles_eur += i_loss
            if i.severity == Severity.CRITICAL.value:
                critical_insights.append(i)
                critical_total_eur += i_loss
        elif i.insight_status == InsightStatus.RESOLVED:
            resolved_insights.append(i)
            economies_realisees_eur += i.estimated_loss_eur or 0.0

    nb_leviers_open = len(open_insights)
    nb_critical = len(critical_insights)
    nb_resolved = len(resolved_insights)

    # ── Kicker + titre + italic hook §5 ──
    # Sprint 1.8bis Quality : helper _s pour pluriel FR (audit /simplify P2).
    week_iso = datetime.now(timezone.utc).isocalendar().week
    if nb_leviers_open > 0:
        kicker = (
            f"DIAGNOSTIC · SEMAINE {week_iso} · "
            f"{nb_leviers_open} LEVIER{_s(nb_leviers_open).upper()} IDENTIFIÉ{_s(nb_leviers_open).upper()}"
        )
    else:
        sites_plural = _s(sites_count).upper()
        kicker = f"DIAGNOSTIC · SEMAINE {week_iso} · {sites_count} SITE{sites_plural} ANALYSÉ{sites_plural}"
    title = "Vos économies d'énergie identifiées"
    italic_hook = "leviers chiffrés · plan d'actions priorisé"

    # ── Narrative orientée Marie DAF + Energy Manager ──
    # Doctrine §10 : acronymes EMS interdits dans narrative — vocabulaire DAF
    # non-sachant. Sprint 1.8bis CX P1 : « actionnable immédiatement » →
    # « à activer cette semaine » + « priorisées par effort/gain » →
    # « classées du plus rentable au plus simple ».
    narr_parts = []
    if nb_critical > 0:
        p_crit = _s(nb_critical)
        narr_parts.append(
            f"{nb_critical} levier{p_crit} prioritaire{p_crit} détecté{p_crit} sur "
            "votre patrimoine — à activer cette semaine."
        )
    elif nb_leviers_open > 0:
        p_open = _s(nb_leviers_open)
        narr_parts.append(
            f"{nb_leviers_open} levier{p_open} d'économies détecté{p_open} — "
            "classés du plus rentable au plus simple à mettre en œuvre."
        )
    elif sites_count > 0:
        narr_parts.append(
            f"Aucun gisement d'économies détecté sur {sites_count} site{_s(sites_count)} — patrimoine déjà optimisé."
        )
    else:
        narr_parts.append("Aucun site analysé — lancez le diagnostic pour identifier les leviers d'économies.")

    if economies_potentielles_eur > 0:
        narr_parts.append(
            f"Gisement total chiffré : {_fmt_eur_short(economies_potentielles_eur)}/an "
            "récupérables par actions correctives."
        )

    if economies_realisees_eur > 0:
        narr_parts.append(
            f"Économies déjà sécurisées depuis janvier : {_fmt_eur_short(economies_realisees_eur)} "
            f"({nb_resolved} action{_s(nb_resolved)} validée{_s(nb_resolved)})."
        )

    narr_parts.append(
        "Le moteur diagnostic analyse en continu 5 catégories — consommation hors "
        "heures d'ouverture, talon excessif (consommation de base anormale), pics de "
        "puissance, dérives saisonnières, trous de données. Conforme ISO 50001 (norme "
        "management énergie) et COSTIC (méthode audit énergétique tertiaire FR)."
    )
    narrative = " ".join(narr_parts)

    # ── 3 KPIs hero §5 — angle CFO pilotage économies ──
    # Sprint 1.8bis Marie P0-1 : "YTD" → "depuis janvier" (FR-first §10).
    # Variables intermédiaires pour lisibilité (audit Quality P2 ternaire imbriqué).
    unit_critical = f"dont {nb_critical} prioritaire{_s(nb_critical)}" if nb_critical > 0 else None
    unit_resolved = f"sur {nb_resolved} action{_s(nb_resolved)}" if nb_resolved > 0 else None
    kpis: list[NarrativeKpi] = [
        NarrativeKpi(
            label="Leviers identifiés",
            value=str(nb_leviers_open),
            unit=unit_critical,
            tooltip=(
                "Anomalies de consommation détectées par le moteur diagnostic et non "
                "encore traitées (workflow OPEN → ACK → RESOLVED). Chacune est chiffrée "
                "en euros/an récupérables par action corrective. Fenêtre d'analyse : "
                "12 mois glissants."
            ),
            source="ConsumptionInsight workflow lifecycle",
        ),
        NarrativeKpi(
            label="Gisement annuel",
            value=_fmt_eur_short(economies_potentielles_eur),
            tooltip=(
                "Cumul des pertes estimées sur les leviers ouverts — surconsommation "
                "vs benchmark archétype et horaires d'ouverture. Estimation modélisée "
                "(pas une perte mesurée), récupérable par actions correctives. "
                "Détail méthode /methodologie/diagnostic-conso."
            ),
            source="ConsumptionInsight.estimated_loss_eur · COSTIC NF EN 16247-2",
        ),
        NarrativeKpi(
            label="Économies sécurisées",
            value=_fmt_eur_short(economies_realisees_eur),
            unit=unit_resolved,
            tooltip=(
                "Cumul des gains validés depuis le 1er janvier — actions correctives "
                "implémentées et insights passés au statut RESOLVED. Base solide pour "
                "audit ISO 50001 et reporting CSRD."
            ),
            source="ConsumptionInsight RESOLVED depuis le 1er janvier",
        ),
    ]

    # ── Week-cards Diagnostic ──
    week_cards: list[NarrativeWeekCard] = []

    # DRIFT — levier critique avec plus fort gain.
    # Sprint 1.8 : site_name_by_id pré-calculé (lookup O(1)).
    # Sprint 1.8bis Quality P1 : type_fr → constante module _INSIGHT_TYPE_LABELS_FR.
    if critical_insights:
        top_critical = max(critical_insights, key=lambda i: i.estimated_loss_eur or 0)
        critical_gain = top_critical.estimated_loss_eur or 0
        site_label = site_name_by_id.get(top_critical.site_id, f"site #{top_critical.site_id}")
        type_label = _INSIGHT_TYPE_LABELS_FR.get(top_critical.type, "Anomalie consommation")
        week_cards.append(
            NarrativeWeekCard(
                type="drift",
                title=f"{type_label} · {site_label}",
                body=(
                    (top_critical.message[:140] if top_critical.message else "Anomalie détectée")
                    + " — gain immédiat à activer."
                ),
                cta_path=f"/diagnostic-conso?site_id={top_critical.site_id}&insight={top_critical.id}",
                cta_label="Voir le levier",
                impact_eur=critical_gain,
                urgency_days=14,
            )
        )

    # TODO — autres leviers ouverts à programmer.
    # Sprint 1.8bis Efficiency P2 : critical_total_eur calculé dans single-pass.
    other_open = nb_leviers_open - nb_critical
    if other_open > 0:
        autres_gain = economies_potentielles_eur - critical_total_eur
        p_other = _s(other_open)
        week_cards.append(
            NarrativeWeekCard(
                type="todo",
                title=f"Programmer {other_open} action{p_other} corrective{p_other}",
                body=(
                    "Leviers secondaires à intégrer au plan d'actions trimestriel — "
                    "économies cumulées progressives, contribution audit ISO 50001."
                ),
                cta_path="/diagnostic-conso?status=open",
                cta_label="Voir leviers ouverts",
                impact_eur=autres_gain,
                urgency_days=90,
            )
        )

    # GOOD_NEWS — économies sécurisées depuis janvier significatives.
    if economies_realisees_eur >= _DIAGNOSTIC_SEUIL_ECONOMIE_VISIBLE_EUR:
        week_cards.append(
            NarrativeWeekCard(
                type="good_news",
                title=f"{_fmt_eur_short(economies_realisees_eur)} d'économies sécurisées",
                body=(
                    f"{nb_resolved} action{_s(nb_resolved)} validée{_s(nb_resolved)} "
                    "depuis janvier — base solide pour audit ISO 50001 et reporting CSRD."
                ),
                cta_path="/diagnostic-conso?status=resolved",
                cta_label="Voir actions validées",
                impact_eur=economies_realisees_eur,
            )
        )

    fallback_body = (
        "Aucun levier détecté cette semaine — patrimoine sous contrôle. Le moteur "
        "analyse en continu 5 catégories d'anomalies pour identifier les économies."
    )

    # Tone diagnostic-specific (cohérent avec _build_monitoring) :
    # CRITICAL si leviers critiques, TENSION si leviers ouverts à traiter,
    # POSITIVE si économies YTD significatives, NEUTRAL sinon.
    if nb_critical > 0:
        narrative_tone = NarrativeTone.CRITICAL
    elif nb_leviers_open > 0:
        narrative_tone = NarrativeTone.TENSION
    elif economies_realisees_eur >= _DIAGNOSTIC_SEUIL_ECONOMIE_VISIBLE_EUR:
        narrative_tone = NarrativeTone.POSITIVE
    else:
        narrative_tone = NarrativeTone.NEUTRAL

    # Provenance : confidence basée sur volume d'insights analysés.
    # Sprint 1.8bis Reuse P1 : helper _build_provenance_volume_based extrait
    # (pattern monitoring + diagnostic dédupliqué).
    provenance = _build_provenance_volume_based(
        source="Moteur diagnostic 5 catégories + ISO 50001 + COSTIC NF EN 16247-2",
        has_data=(nb_leviers_open + nb_resolved) > 0,
        sites_count=sites_count,
        methodology_url="/methodologie/diagnostic-conso",
    )

    return Narrative(
        page_key="diagnostic",
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


# Sprint 1.9 — constantes module Anomalies / Centre d'actions.
# Sourçage : doctrine §3 P11 (le bon endroit pour chaque brique).
# Sprint 1.9bis Reuse P1 : seuil aligné sur _DIAGNOSTIC_SEUIL_ECONOMIE_VISIBLE_EUR
# (~1% budget ETI 5 sites = critère « économie/impact significatif » partagé).
_ANOMALIES_SEUIL_IMPACT_CRITIQUE_EUR = _DIAGNOSTIC_SEUIL_ECONOMIE_VISIBLE_EUR  # 5 000 € SoT partagée
_ANOMALIES_HORIZON_URGENT_DAYS = 30  # échéance < 30j = urgent
_ANOMALIES_PRIORITE_CRITIQUE_THRESHOLD = 2  # priority ≤ 2 (sur 1-5) = critique
# Sprint 1.9bis Quality P2 : wording fallback centralisé (dupliqué narrative + fallback_body).
_ANOMALIES_ZERO_LABEL = "Aucune anomalie à traiter cette semaine — patrimoine sous contrôle."

# SoT FR labels source_type ActionItem (cross-pillar).
_ACTION_SOURCE_LABELS_FR: dict[str, str] = {
    "compliance": "Conformité",
    "consumption": "Consommation",
    "billing": "Facturation",
    "purchase": "Achat",
    "monitoring": "Performance",
}


def _action_source_str(source_type) -> str:
    """Sprint 1.9bis Quality P1 : helper centralise hasattr dead-code dupliqué 2×.

    ActionSourceType est un SAEnum donc `.value` est toujours présent. Le
    fallback `str(source_type)` était dead-code trompeur ; on garde un
    fallback `"autre"` si source_type est None (action org-level).
    """
    if source_type is None:
        return "autre"
    return source_type.value if hasattr(source_type, "value") else str(source_type)


def _is_critical_action(a) -> bool:
    """Sprint 1.9bis Quality P2 : helper condition critique cross-prio/severity.

    Une action est critique si priority ≤ 2 (sur échelle 1-5) ou
    severity = critical (Severity enum models.enums S1.8bis).
    """
    from models.enums import Severity

    if a.priority is not None and a.priority <= _ANOMALIES_PRIORITE_CRITIQUE_THRESHOLD:
        return True
    return a.severity == Severity.CRITICAL.value


def _build_anomalies(
    db: Session,
    org_id: int,
    org_name: str,
    sites_count: int,
) -> Narrative:
    """Sprint 1.9 — Vue Centre d'actions (anomalies cross-pillar).

    Page transverse §3 P11 doctrine : agrège toutes les anomalies du
    patrimoine (Conformité / Performance / Facturation / Achat) en un
    seul flux d'actions priorisées par impact € et échéance.

    Sert Marie DAF (« qu'est-ce que je dois traiter cette semaine ? »),
    Energy Manager (priorisation), Investisseur (orchestration cross-
    pillar = preuve produit unifié vs concurrents siloés).

    Données réelles :
      - ActionItem (SoT cross-source) : status, priority, severity,
        estimated_gain_eur, due_date, source_type
      - Workflow : OPEN → IN_PROGRESS → DONE / BLOCKED / FALSE_POSITIVE
    """
    from models.action_item import ActionItem
    from models.enums import ActionStatus

    ctx = _load_org_context(db, org_id)
    site_name_by_id: dict[int, str] = {s.id: (s.nom or f"site #{s.id}") for s in ctx.sites}

    # ── Récupérer les actions actives (org-scoped via ActionItem.org_id) ──
    # Sprint 1.9 : filtre directement sur org_id (modèle ActionItem porte
    # cette colonne, pas besoin de joindre Site). Bornage temporel : OPEN
    # + IN_PROGRESS + DONE depuis 1er janvier (Économies sécurisées YTD).
    today = date.today()
    horizon_floor = min(date(today.year, 1, 1), today - timedelta(days=365))
    actions = (
        db.query(ActionItem)
        .filter(ActionItem.org_id == org_id)
        .filter(ActionItem.created_at >= datetime.combine(horizon_floor, datetime.min.time()))
        .all()
    )

    # Single-pass partitioning par status × priorité × source.
    open_actions: list[ActionItem] = []
    critical_actions: list[ActionItem] = []
    in_progress_actions: list[ActionItem] = []
    done_actions: list[ActionItem] = []
    impact_total_eur = 0.0
    critical_total_eur = 0.0
    economies_realisees_eur = 0.0
    sources_seen: dict[str, int] = {}
    horizon_urgent = today + timedelta(days=_ANOMALIES_HORIZON_URGENT_DAYS)
    urgent_actions: list[ActionItem] = []

    # Sprint 1.9bis Quality P1 : helpers _is_critical_action + _action_source_str
    # (severity enum-aware + dead-code hasattr supprimé).
    for a in actions:
        if a.status == ActionStatus.OPEN:
            open_actions.append(a)
            gain = a.estimated_gain_eur or 0.0
            impact_total_eur += gain
            if _is_critical_action(a):
                critical_actions.append(a)
                critical_total_eur += gain
            if a.due_date and a.due_date <= horizon_urgent:
                urgent_actions.append(a)
            src = _action_source_str(a.source_type)
            sources_seen[src] = sources_seen.get(src, 0) + 1
        elif a.status == ActionStatus.IN_PROGRESS:
            in_progress_actions.append(a)
        elif a.status == ActionStatus.DONE:
            done_actions.append(a)
            economies_realisees_eur += a.estimated_gain_eur or 0.0

    nb_actions_open = len(open_actions)
    nb_actions_critical = len(critical_actions)
    nb_actions_in_progress = len(in_progress_actions)
    nb_actions_done = len(done_actions)
    nb_urgent = len(urgent_actions)

    # ── Kicker + titre + italic hook §5 ──
    # Sprint 1.9bis Investisseur P0 : italic_hook hisse wedge concurrentiel
    # (différenciation §3 P11 vs Advizeo/Deepki/Citron/Energisme/Trinergy).
    week_iso = datetime.now(timezone.utc).isocalendar().week
    if nb_actions_open > 0:
        kicker = (
            f"CENTRE D'ACTIONS · SEMAINE {week_iso} · "
            f"{nb_actions_open} ANOMALIE{_s(nb_actions_open).upper()} ACTIVE{_s(nb_actions_open).upper()}"
        )
    else:
        kicker = f"CENTRE D'ACTIONS · SEMAINE {week_iso} · PATRIMOINE SOUS CONTRÔLE"
    title = "Vos anomalies, regroupées et priorisées"
    italic_hook = "4 piliers, 1 plan d'actions priorisé"

    # ── Narrative orientée Marie DAF + Energy Manager ──
    narr_parts = []
    if nb_actions_critical > 0:
        p_crit = _s(nb_actions_critical)
        narr_parts.append(
            f"{nb_actions_critical} anomalie{p_crit} critique{p_crit} sur votre patrimoine — "
            "à traiter cette semaine pour limiter l'impact."
        )
    elif nb_actions_open > 0:
        p_open = _s(nb_actions_open)
        narr_parts.append(
            f"{nb_actions_open} anomalie{p_open} active{p_open} regroupée{p_open} "
            f"et classée{p_open} par enjeu € et urgence."
        )
    elif nb_actions_in_progress > 0:
        narr_parts.append(
            f"{nb_actions_in_progress} action{_s(nb_actions_in_progress)} en cours — exécution conforme au plan."
        )
    else:
        narr_parts.append(_ANOMALIES_ZERO_LABEL)

    if nb_urgent > 0:
        narr_parts.append(
            f"{nb_urgent} échéance{_s(nb_urgent)} dans les {_ANOMALIES_HORIZON_URGENT_DAYS} prochains jours."
        )

    if impact_total_eur > 0:
        narr_parts.append(
            f"Impact estimé : {_fmt_eur_short(impact_total_eur)} récupérables par actions correctives priorisées."
        )

    if economies_realisees_eur > 0:
        narr_parts.append(
            f"Économies déjà sécurisées depuis janvier : {_fmt_eur_short(economies_realisees_eur)} "
            f"({nb_actions_done} action{_s(nb_actions_done)} clôturée{_s(nb_actions_done)})."
        )

    # Sprint 1.9bis Investisseur P0/P1 : phrase wedge concurrentiel rendue
    # inconditionnellement (vs « PROMEOS unifie cross-pilier — un seul flux
    # vs un dashboard par module chez les acteurs du marché »).
    if sources_seen:
        sources_top = sorted(sources_seen.items(), key=lambda kv: -kv[1])[:3]
        sources_fr = ", ".join(_ACTION_SOURCE_LABELS_FR.get(src, src) for src, _ in sources_top)
        narr_parts.append(
            f"Sources principales : {sources_fr}. PROMEOS Sol unifie les anomalies "
            "des 4 piliers en un flux unique — vs un dashboard par module chez les "
            "concurrents."
        )
    else:
        narr_parts.append(
            "PROMEOS Sol unifie les anomalies des 4 piliers en un flux unique — "
            "vs un dashboard par module chez les concurrents."
        )

    narrative = " ".join(narr_parts)

    # ── 3 KPIs hero §5 — angle CFO orchestration ──
    # Sprint 1.9bis Marie P0 : tooltip workflow reformulé FR-first (« à faire →
    # en cours → terminée » vs « OPEN → IN_PROGRESS → DONE » jargon dev).
    # « ActionItem cross-pillar » → vocabulaire utilisateur.
    unit_critical = f"dont {nb_actions_critical} critique{_s(nb_actions_critical)}" if nb_actions_critical > 0 else None
    unit_urgent = f"dont {nb_urgent} sous {_ANOMALIES_HORIZON_URGENT_DAYS}j" if nb_urgent > 0 else None
    kpis: list[NarrativeKpi] = [
        NarrativeKpi(
            label="Anomalies actives",
            value=str(nb_actions_open),
            unit=unit_critical,
            tooltip=(
                "Anomalies détectées par les 4 piliers PROMEOS et non encore "
                "traitées (à faire → en cours → terminée). Priorité 1 ou 2 sur 5 "
                "ou criticité = à traiter cette semaine."
            ),
            source="Plan d'actions consolidé · 4 piliers PROMEOS",
        ),
        NarrativeKpi(
            label="Impact financier",
            value=_fmt_eur_short(impact_total_eur),
            unit=unit_urgent,
            tooltip=(
                "Cumul des gains estimés sur les anomalies ouvertes — "
                "récupérables par actions correctives. Source unifiée : chaque "
                "pilier estime son propre gain (€/an évité)."
            ),
            source="Plan d'actions · gains estimés agrégés",
        ),
        NarrativeKpi(
            label="Économies sécurisées",
            value=_fmt_eur_short(economies_realisees_eur),
            unit=f"sur {nb_actions_done} clôturée{_s(nb_actions_done)}" if nb_actions_done > 0 else None,
            tooltip=(
                "Cumul des gains validés depuis le 1er janvier — actions "
                "clôturées (statut « terminée »). Base solide pour audit ISO "
                "50001 et reporting CSRD."
            ),
            source="Plan d'actions · clôturées depuis le 1er janvier",
        ),
    ]

    # ── Week-cards Centre d'actions ──
    week_cards: list[NarrativeWeekCard] = []

    # DRIFT — action critique avec plus fort impact.
    # Sprint 1.9bis Quality P1 : helpers _action_source_str + site_label
    # « Action transverse » plus parlant que « Toutes sources ».
    if critical_actions:
        top_critical = max(critical_actions, key=lambda a: a.estimated_gain_eur or 0)
        critical_gain = top_critical.estimated_gain_eur or 0
        site_label = (
            site_name_by_id.get(top_critical.site_id, f"site #{top_critical.site_id}")
            if top_critical.site_id
            else "Action transverse"
        )
        src_value = _action_source_str(top_critical.source_type)
        source_label = _ACTION_SOURCE_LABELS_FR.get(src_value, src_value)
        week_cards.append(
            NarrativeWeekCard(
                type="drift",
                title=f"{source_label} · {site_label}",
                body=(
                    (top_critical.title[:140] if top_critical.title else "Anomalie critique") + " — agir cette semaine."
                ),
                cta_path=f"/anomalies?status=open&action={top_critical.id}",
                cta_label="Voir l'anomalie",
                impact_eur=critical_gain,
                urgency_days=7,
            )
        )

    # TODO — autres anomalies à programmer.
    other_open = nb_actions_open - nb_actions_critical
    if other_open > 0:
        autres_gain = impact_total_eur - critical_total_eur
        p_other = _s(other_open)
        week_cards.append(
            NarrativeWeekCard(
                type="todo",
                title=f"Programmer {other_open} action{p_other} corrective{p_other}",
                body=(
                    "Anomalies secondaires regroupées par impact et échéance — "
                    "visibilité unique cross-pilier vs traitement séparé par brique."
                ),
                cta_path="/anomalies?status=open",
                cta_label="Voir liste complète",
                impact_eur=autres_gain,
                urgency_days=30,
            )
        )

    # GOOD_NEWS — économies sécurisées YTD significatives.
    if economies_realisees_eur >= _ANOMALIES_SEUIL_IMPACT_CRITIQUE_EUR:
        week_cards.append(
            NarrativeWeekCard(
                type="good_news",
                title=f"{_fmt_eur_short(economies_realisees_eur)} d'économies validées",
                body=(
                    f"{nb_actions_done} action{_s(nb_actions_done)} clôturée{_s(nb_actions_done)} "
                    "depuis janvier — patrimoine en routine d'amélioration continue."
                ),
                cta_path="/anomalies?status=done",
                cta_label="Voir actions clôturées",
                impact_eur=economies_realisees_eur,
            )
        )

    fallback_body = (
        f"{_ANOMALIES_ZERO_LABEL} Le Centre d'actions surveille en continu "
        "Conformité, Performance, Facturation et Achat."
    )

    # Tone : CRITICAL si action critique ou impact ≥5k€, TENSION si actions
    # ouvertes, POSITIVE si in_progress + clôtures, NEUTRAL sinon.
    if nb_actions_critical > 0 or impact_total_eur >= _ANOMALIES_SEUIL_IMPACT_CRITIQUE_EUR:
        narrative_tone = NarrativeTone.CRITICAL
    elif nb_actions_open > 0:
        narrative_tone = NarrativeTone.TENSION
    elif nb_actions_in_progress > 0 or economies_realisees_eur > 0:
        narrative_tone = NarrativeTone.POSITIVE
    else:
        narrative_tone = NarrativeTone.NEUTRAL

    provenance = _build_provenance_volume_based(
        source="Centre d'actions cross-pillar (Conformité + Performance + Facturation + Achat)",
        has_data=(nb_actions_open + nb_actions_done) > 0,
        sites_count=sites_count,
        methodology_url="/methodologie/centre-actions",
    )

    return Narrative(
        page_key="anomalies",
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


# Sprint 1.10 — constantes module Flex Intelligence (§4.6 doctrine).
# Sourçage : NEBCO/AOFD mécanismes RTE + ISO 50001 + observatoire CRE T4 2025.
_FLEX_SCORE_GOOD = 60  # score ≥ 60/100 = potentiel actionnable
_FLEX_SCORE_CRITICAL = 30  # score < 30/100 = potentiel limité (à renforcer)
_FLEX_SEUIL_KW_SIGNIFICATIF = 100  # ≥ 100 kW pilotables = bloc d'effacement viable

# SoT FR labels asset_type (cf models.flex_models.FlexAssetType).
_FLEX_ASSET_LABELS_FR: dict[str, str] = {
    "hvac": "CVC (climatisation)",
    "irve": "Bornes recharge",
    "cold_storage": "Froid industriel",
    "thermal_storage": "Stockage thermique",
    "battery": "Batterie stationnaire",
    "pv": "Photovoltaïque",
    "lighting": "Éclairage",
    "process": "Process industriel",
    "other": "Autre actif",
}


def _build_flex(
    db: Session,
    org_id: int,
    org_name: str,
    sites_count: int,
) -> Narrative:
    """Sprint 1.10 — Vue Flex Intelligence (différenciateur §4.6).

    Promesse §4.6 doctrine : « Effacement comme revenu — éligibilité NEBCO
    (mécanisme effacement RTE), Flex Score, bridge aggregateurs. PROMEOS
    industrialise l'audit flex sans contrainte : pas d'engagement
    aggregateur, neutralité, données chez le client. »

    Sert Energy Manager (priorisation actifs flex), Marie DAF (gisement €
    via revenus NEBCO/AOFD), Investisseur (preuve §4.6 pillar = wedge
    durable face à Voltalis, GreenFlex, Smart Energie).

    Données réelles :
      - FlexAsset : asset_type, power_kw, is_controllable, gtb_class
      - FlexAssessment : flex_score, potential_kw, levers_json,
        4 dimensions (technical/data/economic/regulatory)
    """
    from models.flex_models import FlexAsset, FlexAssessment

    ctx = _load_org_context(db, org_id)
    site_ids = [s.id for s in ctx.sites]

    # ── Récupérer assets + assessments ──
    if site_ids:
        assets = db.query(FlexAsset).filter(FlexAsset.site_id.in_(site_ids)).all()
        assessments = db.query(FlexAssessment).filter(FlexAssessment.site_id.in_(site_ids)).all()
    else:
        assets = []
        assessments = []

    # Single-pass agrégats assets : controllable_kw, asset_type counts.
    controllable_kw = 0.0
    nb_controllable = 0
    nb_total_assets = len(assets)
    asset_types_seen: dict[str, int] = {}
    for a in assets:
        if a.is_controllable:
            nb_controllable += 1
            controllable_kw += a.power_kw or 0.0
        type_key = a.asset_type.value if hasattr(a.asset_type, "value") else str(a.asset_type)
        asset_types_seen[type_key] = asset_types_seen.get(type_key, 0) + 1

    # Single-pass agrégats assessments : score moyen, potential cumulé.
    nb_assessed = len(assessments)
    sum_flex_score = sum((ass.flex_score or 0) for ass in assessments)
    flex_score_avg = round(sum_flex_score / nb_assessed) if nb_assessed > 0 else None
    potential_kw_total = sum((ass.potential_kw or 0.0) for ass in assessments)
    potential_kwh_year_total = sum((ass.potential_kwh_year or 0.0) for ass in assessments)

    # ── Kicker + titre + italic hook §5 ──
    week_iso = datetime.now(timezone.utc).isocalendar().week
    if nb_total_assets > 0:
        kicker = (
            f"FLEX INTELLIGENCE · SEMAINE {week_iso} · "
            f"{nb_total_assets} ACTIF{_s(nb_total_assets).upper()} INVENTORIÉ{_s(nb_total_assets).upper()}"
        )
    else:
        kicker = f"FLEX INTELLIGENCE · SEMAINE {week_iso} · POTENTIEL EFFACEMENT À ÉVALUER"
    title = "Votre potentiel d'effacement, sans engagement"
    italic_hook = "neutralité · pas d'aggregateur · vos données chez vous"

    # ── Narrative orientée Marie DAF + Energy Manager ──
    # Doctrine §10 : NEBCO/AOFD/GTB explicités inline (vocabulaire FR-first).
    narr_parts = []
    if nb_total_assets == 0:
        narr_parts.append(
            "Aucun actif pilotable inventorié — lancez l'audit Flex pour identifier "
            "votre potentiel d'effacement (CVC, froid, batterie, photovoltaïque)."
        )
    elif nb_controllable == 0:
        narr_parts.append(
            f"{nb_total_assets} actif{_s(nb_total_assets)} inventorié{_s(nb_total_assets)} "
            "mais aucun n'est encore pilotable — installer une GTB (gestion "
            "technique du bâtiment) débloque le potentiel."
        )
    else:
        narr_parts.append(
            f"{nb_controllable} actif{_s(nb_controllable)} pilotable{_s(nb_controllable)} "
            f"sur {nb_total_assets} — potentiel {round(controllable_kw)} kW d'effacement "
            "instantané activable."
        )

    if flex_score_avg is not None:
        if flex_score_avg >= _FLEX_SCORE_GOOD:
            narr_parts.append(
                f"Score Flex moyen {flex_score_avg}/100 — potentiel actionnable, "
                "passage en revenu NEBCO (mécanisme effacement RTE) envisageable."
            )
        elif flex_score_avg < _FLEX_SCORE_CRITICAL:
            narr_parts.append(
                f"Score Flex moyen {flex_score_avg}/100 — potentiel limité, renforcement instrumentation prioritaire."
            )
        else:
            narr_parts.append(
                f"Score Flex moyen {flex_score_avg}/100 — potentiel intermédiaire, "
                "leviers à activer pour passer le cap des 60/100."
            )

    if potential_kwh_year_total > 0:
        narr_parts.append(
            f"Potentiel énergétique annuel : {round(potential_kwh_year_total / 1000)} MWh — "
            "convertible en revenus marché capacité ou appels d'offres effacement (AOFD RTE)."
        )

    narr_parts.append(
        "PROMEOS Sol industrialise l'audit Flex sans engagement aggregateur "
        "— vos données restent chez vous, neutralité totale vs Voltalis, "
        "GreenFlex, Smart Energie."
    )
    narrative = " ".join(narr_parts)

    # ── 3 KPIs hero §5 — angle Energy Manager + DAF ──
    kpis: list[NarrativeKpi] = [
        NarrativeKpi(
            label="Potentiel pilotable",
            value=f"{round(controllable_kw)} kW" if controllable_kw > 0 else "—",
            unit=f"sur {nb_total_assets} actif{_s(nb_total_assets)}" if nb_total_assets > 0 else None,
            tooltip=(
                "Puissance instantanée mobilisable pour effacement (somme des "
                "actifs pilotables avec GTB/API). Seuil bloc d'effacement viable "
                "RTE : 100 kW minimum pour rentrer en NEBCO."
            ),
            source="FlexAsset.is_controllable agrégé",
        ),
        NarrativeKpi(
            label="Score Flex moyen",
            value=f"{flex_score_avg}/100" if flex_score_avg is not None else "—",
            unit=f"sur {nb_assessed} site{_s(nb_assessed)}" if nb_assessed > 0 else None,
            tooltip=(
                "Score 0-100 sur 4 dimensions : maturité technique (assets "
                "contrôlables), confiance données, pertinence économique, "
                "alignement réglementaire. Seuil actionnable : ≥ 60/100."
            ),
            source="FlexAssessment · 4 dimensions",
        ),
        NarrativeKpi(
            label="Énergie annuelle",
            value=(f"{round(potential_kwh_year_total / 1000)} MWh" if potential_kwh_year_total > 0 else "—"),
            tooltip=(
                "Énergie annuelle modulable estimée. Convertible en revenu "
                "via NEBCO (mécanisme effacement RTE) ou AOFD (appels d'offres "
                "effacement diffus). Estimation modélisée, pas un revenu garanti."
            ),
            source="FlexAssessment.potential_kwh_year",
        ),
    ]

    # ── Week-cards Flex ──
    week_cards: list[NarrativeWeekCard] = []

    # DRIFT — site avec score < CRITICAL.
    critical_assessments = [a for a in assessments if (a.flex_score or 100) < _FLEX_SCORE_CRITICAL]
    if critical_assessments:
        worst = min(critical_assessments, key=lambda a: a.flex_score or 0)
        site_label = next(
            (s.nom or f"site #{s.id}" for s in ctx.sites if s.id == worst.site_id), f"site #{worst.site_id}"
        )
        week_cards.append(
            NarrativeWeekCard(
                type="drift",
                title=f"Score Flex faible · {site_label}",
                body=(
                    f"Score {round(worst.flex_score or 0)}/100 — instrumentation à renforcer "
                    "(GTB, métrologie temps réel) pour débloquer le potentiel d'effacement."
                ),
                cta_path=f"/flex?site_id={worst.site_id}",
                cta_label="Voir le diagnostic",
                urgency_days=60,
            )
        )

    # TODO — sites non évalués.
    sites_not_assessed = sites_count - nb_assessed
    if sites_not_assessed > 0:
        week_cards.append(
            NarrativeWeekCard(
                type="todo",
                title=f"Évaluer {sites_not_assessed} site{_s(sites_not_assessed)}",
                body=(
                    "Lancer l'audit Flex pour cartographier le potentiel d'effacement "
                    "et estimer les revenus marché capacité — sans engagement aggregateur."
                ),
                cta_path="/flex?status=not_assessed",
                cta_label="Lancer audit Flex",
                urgency_days=90,
            )
        )

    # GOOD_NEWS — potentiel ≥ seuil viable NEBCO.
    if controllable_kw >= _FLEX_SEUIL_KW_SIGNIFICATIF:
        week_cards.append(
            NarrativeWeekCard(
                type="good_news",
                title=f"{round(controllable_kw)} kW pilotables identifiés",
                body=(
                    "Au-dessus du seuil NEBCO 100 kW — éligibilité mécanisme effacement "
                    "RTE confirmée. Passage en revenus marché capacité possible "
                    "via aggregateur OU mode auto-effacement (neutralité PROMEOS)."
                ),
                cta_path="/flex?status=actionable",
                cta_label="Voir les actifs pilotables",
                impact_eur=potential_kwh_year_total * 0.030,  # ~30 €/MWh estim. revenu effacement
            )
        )

    fallback_body = (
        "Aucun audit Flex en cours — lancez l'évaluation pour cartographier "
        "votre potentiel d'effacement et estimer les revenus marché capacité."
    )

    # Tone : CRITICAL si score moyen < critique, TENSION si non évalué,
    # POSITIVE si score ≥ good + potential significatif, NEUTRAL sinon.
    if flex_score_avg is not None and flex_score_avg < _FLEX_SCORE_CRITICAL:
        narrative_tone = NarrativeTone.CRITICAL
    elif sites_not_assessed > 0 or nb_assessed == 0:
        narrative_tone = NarrativeTone.TENSION
    elif (
        flex_score_avg is not None
        and flex_score_avg >= _FLEX_SCORE_GOOD
        and controllable_kw >= _FLEX_SEUIL_KW_SIGNIFICATIF
    ):
        narrative_tone = NarrativeTone.POSITIVE
    else:
        narrative_tone = NarrativeTone.NEUTRAL

    provenance = _build_provenance_volume_based(
        source="Flex Intelligence + NEBCO RTE + AOFD + ISO 50001",
        has_data=(nb_total_assets + nb_assessed) > 0,
        sites_count=sites_count,
        methodology_url="/methodologie/flex-effacement",
    )

    return Narrative(
        page_key="flex",
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
    "achat_energie": _build_achat_energie,
    "monitoring": _build_monitoring,
    "diagnostic": _build_diagnostic,
    "anomalies": _build_anomalies,
    "flex": _build_flex,
    # Couverture nav 10/10 (100%) — Sprint 2 : event-bus densification.
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
