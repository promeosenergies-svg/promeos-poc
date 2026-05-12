"""
PROMEOS — regops/priority_scoring.py : algorithme canonique de priorisation
des findings cockpit jour (ADR-022 + doctrine v1.0 Phase F.22).

Module SoT pour le scoring des highlights affichés dans le Top 3 priorités
du Cockpit Jour, ALIGNÉ sur la doctrine de priorisation v1.0 :

  4 axes objectifs (Gravité × Impact × Délai × Catégorie) :
    G ∈ [0, 5]  — gravité (sanction légale → information)
    I ∈ [0, 5]  — impact € ou MWh (bucket monétisé)
    D ∈ [0, 5]  — délai (≤30j → continu)
    C : Category — qualitatif (PLATEFORME / ENERGIE / REGLEMENTAIRE /
                              FINANCIER / STRATEGIQUE)

  3 personas avec pondérations différentes :
    Responsable Énergie  : wG=3, wI=2, wD=2  (défaut, P1≥25)
    DAF                  : wG=2, wI=3, wD=2  (P1≥22)
    DG/COMEX             : wG=2, wI=3, wD=3  (P1≥24)

  Formule : score = G·wG + I·wI + D·wD

  3 overrides cardinaux :
    1. G=5 → score ≥ 25 (gravité légale absolue)
    2. D=5 AND G≥3 → score ≥ 22 (urgence qualifiée)
    3. I=5 AND G=0 → score ≤ 15 (impact orphelin plafonné)

  7 hubs avec ordre catégorie en cas d'égalité (HUB_CAT_ORDER).

Doctrine de référence : `docs/adr/ADR-022-cockpit-data-sources.md` +
sprint priorisation v1.0 (plan_sprint_priorisation_v1.md).

Rétro-compat F.19a : les fonctions publiques `compute_finding_priority`,
`rank_findings`, `top_n` conservent leur signature. Les mappers
severity→G, impact_eur→I, deadline→D sont automatiques.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional


# ── Enums Severity / Scope (rétro-compat F.19a) ─────────────────────────────


class Severity(str, Enum):
    """Sévérité métier d'une finding (mappée vers G via _SEVERITY_TO_G)."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Scope(str, Enum):
    """Périmètre concerné par la finding (utilisé pour départage hub)."""

    GROUP = "GROUP"
    PORTFOLIO = "PORTFOLIO"
    SITE = "SITE"


# ── Enums Doctrine v1 : Category / Persona / HubId / Tier ───────────────────


class Domain(str, Enum):
    """Synonyme `Domain` (F.19a) → `Category` (v1). Conserve les 5 valeurs.

    Mapping :
      - PLATFORM_HEALTH   ↔ PLATEFORME
      - COMPLIANCE        ↔ REGLEMENTAIRE
      - FINANCIAL         ↔ FINANCIER
      - ENERGY            ↔ ENERGIE
      - OPTIMISATION      ↔ STRATEGIQUE
    """

    PLATFORM_HEALTH = "PLATFORM_HEALTH"
    COMPLIANCE = "COMPLIANCE"
    FINANCIAL = "FINANCIAL"
    ENERGY = "ENERGY"
    OPTIMISATION = "OPTIMISATION"


class Category(str, Enum):
    """Catégorie doctrinale v1 (5 valeurs, mapping 1-1 vers Domain F.19a)."""

    PLATEFORME = "PLATEFORME"
    ENERGIE = "ENERGIE"
    REGLEMENTAIRE = "REGLEMENTAIRE"
    FINANCIER = "FINANCIER"
    STRATEGIQUE = "STRATEGIQUE"


# Mapping bidirectionnel Domain ↔ Category pour le départage hub.
_DOMAIN_TO_CATEGORY: dict[Domain, Category] = {
    Domain.PLATFORM_HEALTH: Category.PLATEFORME,
    Domain.COMPLIANCE: Category.REGLEMENTAIRE,
    Domain.FINANCIAL: Category.FINANCIER,
    Domain.ENERGY: Category.ENERGIE,
    Domain.OPTIMISATION: Category.STRATEGIQUE,
}


class Persona(str, Enum):
    """Persona consommateur du briefing (toggle topbar)."""

    RESPONSABLE_ENERGIE = "responsable_energie"
    DAF = "daf"
    DG_COMEX = "dg_comex"


class HubId(str, Enum):
    """7 hubs Phase 3.5 — utilisé pour départager les catégories en cas
    d'égalité de score (cf HUB_CAT_ORDER)."""

    COCKPIT_JOUR = "cockpit_jour"
    COCKPIT_STRATEGIQUE = "cockpit_strategique"
    ENERGIE = "energie"
    CONFORMITE = "conformite"
    FACTURES = "factures"
    ACHAT = "achat"
    PATRIMOINE = "patrimoine"


class Tier(str, Enum):
    """Tier doctrinal P1/P2/P3 affiché par HubHighlight."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    NONE = "NONE"


# ── Pondérations persona (v1 §14.3.1) ───────────────────────────────────────


@dataclass(frozen=True)
class PersonaWeights:
    wG: int
    wI: int
    wD: int


@dataclass(frozen=True)
class PersonaThresholds:
    P1: int
    P2: int
    P3: int


PERSONA_WEIGHTS: dict[Persona, PersonaWeights] = {
    Persona.RESPONSABLE_ENERGIE: PersonaWeights(wG=3, wI=2, wD=2),  # max 35
    Persona.DAF: PersonaWeights(wG=2, wI=3, wD=2),  # max 35
    Persona.DG_COMEX: PersonaWeights(wG=2, wI=3, wD=3),  # max 40
}

PERSONA_THRESHOLDS: dict[Persona, PersonaThresholds] = {
    Persona.RESPONSABLE_ENERGIE: PersonaThresholds(P1=25, P2=18, P3=12),
    Persona.DAF: PersonaThresholds(P1=22, P2=16, P3=10),
    Persona.DG_COMEX: PersonaThresholds(P1=24, P2=17, P3=11),
}


# ── Ordre de catégorie par hub (v1 §14.3.5) ─────────────────────────────────


HUB_CAT_ORDER: dict[HubId, list[Category]] = {
    HubId.COCKPIT_JOUR: [
        Category.ENERGIE,
        Category.PLATEFORME,
        Category.REGLEMENTAIRE,
        Category.FINANCIER,
        Category.STRATEGIQUE,
    ],
    HubId.COCKPIT_STRATEGIQUE: [
        Category.STRATEGIQUE,
        Category.FINANCIER,
        Category.REGLEMENTAIRE,
        Category.ENERGIE,
        Category.PLATEFORME,
    ],
    HubId.ENERGIE: [
        Category.ENERGIE,
        Category.PLATEFORME,
        Category.REGLEMENTAIRE,
        Category.FINANCIER,
        Category.STRATEGIQUE,
    ],
    HubId.CONFORMITE: [
        Category.REGLEMENTAIRE,
        Category.FINANCIER,
        Category.ENERGIE,
        Category.PLATEFORME,
        Category.STRATEGIQUE,
    ],
    HubId.FACTURES: [
        Category.FINANCIER,
        Category.REGLEMENTAIRE,
        Category.ENERGIE,
        Category.PLATEFORME,
        Category.STRATEGIQUE,
    ],
    HubId.ACHAT: [
        Category.FINANCIER,
        Category.STRATEGIQUE,
        Category.ENERGIE,
        Category.REGLEMENTAIRE,
        Category.PLATEFORME,
    ],
    HubId.PATRIMOINE: [
        Category.PLATEFORME,
        Category.REGLEMENTAIRE,
        Category.ENERGIE,
        Category.FINANCIER,
        Category.STRATEGIQUE,
    ],
}


# ── Mappers automatiques severity/impact/deadline → G/I/D (0-5) ─────────────


# Severity → Gravité 0-5 (v1 §14.2.1)
_SEVERITY_TO_G: dict[Severity, int] = {
    Severity.CRITICAL: 5,  # Bloquant légal · sanction immédiate
    Severity.HIGH: 4,  # Bloquant opérationnel · service dégradé
    Severity.MEDIUM: 3,  # Pénalité légale différée
    Severity.LOW: 2,  # Perte économique récurrente
}


# Impact €/an → I 0-5 (v1 §14.2.2 buckets monétaires)
def _impact_eur_to_i(eur_year: Optional[float]) -> int:
    if eur_year is None or eur_year <= 0:
        return 0
    if eur_year >= 100_000:
        return 5  # ≥100 k€ ou structurant
    if eur_year >= 50_000:
        return 4  # 50-100 k€ site mid-cap
    if eur_year >= 10_000:
        return 3  # 10-50 k€ action ciblée
    if eur_year >= 1_000:
        return 2  # 1-10 k€ quick-win
    return 1  # <1 k€ maintenance


# Délai (jours jusqu'à deadline) → D 0-5 (v1 §14.2.3)
def _deadline_days_to_d(days: Optional[int]) -> int:
    if days is None:
        return 0
    if days < 0:
        return 5  # Deadline passée → urgence max (sanction en cours)
    if days <= 30:
        return 5  # ≤ 30 jours
    if days <= 90:
        return 4  # 30-90 jours
    if days <= 365:
        return 3  # 90-365 jours
    if days <= 365 * 3:
        return 2  # 1-3 ans
    return 1  # > 3 ans


def severity_to_g(severity: Severity) -> int:
    """Public mapper Severity → G ∈ [0, 5] (utilisé en tests + détecteurs)."""
    return _SEVERITY_TO_G.get(severity, 0)


def impact_eur_to_i(eur_year: Optional[float]) -> int:
    return _impact_eur_to_i(eur_year)


def deadline_to_d(deadline_date: Optional[date], today: Optional[date] = None) -> int:
    """Public mapper deadline_date → D ∈ [0, 5]."""
    if deadline_date is None:
        return 0
    today = today or datetime.now(tz=timezone.utc).date()
    return _deadline_days_to_d((deadline_date - today).days)


# ── Finding (input) — rétro-compat F.19a + accepte G/I/D explicites ────────


@dataclass(frozen=True)
class Finding:
    """Représente une finding candidate pour le Top 3 priorités cockpit.

    Phase F.22 — accepte 2 modes :
      - Mode "auto" (rétro-compat F.19a) : severity + impact_eur_year +
        deadline_date sont fournis, G/I/D dérivés via les mappers.
      - Mode "explicit" : g, i, d sont fournis directement (override des
        mappers). Permet de gérer les findings où la sévérité ne reflète
        pas exactement G de la doctrine v1 (ex : un finding "high" mais
        sans sanction légale = G=4, pas 5).
    """

    severity: Severity
    domain: Domain
    scope_level: Scope
    impact_eur_year: Optional[float] = None
    deadline_date: Optional[date] = None
    finding_id: str = ""
    title: str = ""
    site_id: Optional[int] = None
    site_name: str = ""
    evidence: str = ""
    invitation_verb: str = "voir"
    invitation_object: str = "la preuve"
    invitation_href: str = ""
    category_label: str = ""
    impact_label: str = ""
    # F.22 — overrides G/I/D explicites optionnels
    g: Optional[int] = None
    i: Optional[int] = None
    d: Optional[int] = None
    # Sources doctrinales (v1 PriorityFactors §14.5.1) — recommandées
    gravity_source: str = ""
    impact_source: str = ""
    delay_source: str = ""

    def resolve_g(self) -> int:
        return self.g if self.g is not None else severity_to_g(self.severity)

    def resolve_i(self) -> int:
        return self.i if self.i is not None else impact_eur_to_i(self.impact_eur_year)

    def resolve_d(self, today: Optional[date] = None) -> int:
        return self.d if self.d is not None else deadline_to_d(self.deadline_date, today=today)

    def resolve_category(self) -> Category:
        return _DOMAIN_TO_CATEGORY.get(self.domain, Category.STRATEGIQUE)


# ── Score (output) ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PriorityScore:
    """Résultat de scoring v1."""

    total: int
    tier: Tier
    persona: Persona
    breakdown: dict[str, int] = field(default_factory=dict)
    overrides_applied: list[str] = field(default_factory=list)


# Constante doctrine version (tracée dans audit trail).
DOCTRINE_VERSION = "priorisation_v1.0"


# ── Algorithme de scoring v1 (cardinal) ─────────────────────────────────────


def compute_finding_priority(
    finding: Finding,
    persona: Persona = Persona.RESPONSABLE_ENERGIE,
    today: Optional[date] = None,
) -> PriorityScore:
    """Calcule le score doctrinal v1 d'une finding cockpit.

    Args:
        finding : Finding candidate.
        persona : Persona consommateur (défaut Responsable Énergie).
        today   : Date de référence injectable pour tests.

    Returns:
        PriorityScore avec :
            - total      = G·wG + I·wI + D·wD + overrides
            - tier       ∈ {P1, P2, P3, NONE} selon seuils persona
            - persona    : conservé pour audit trail
            - breakdown  : {g, i, d, g_weighted, i_weighted, d_weighted}
            - overrides_applied : liste des overrides déclenchés

    Doctrine sprint priorisation v1 + ADR-022.
    """
    g = finding.resolve_g()
    i = finding.resolve_i()
    d = finding.resolve_d(today=today)
    weights = PERSONA_WEIGHTS[persona]

    g_w = g * weights.wG
    i_w = i * weights.wI
    d_w = d * weights.wD
    raw_score = g_w + i_w + d_w

    overrides_applied: list[str] = []

    # Override 1 : Gravité légale absolue.
    if g == 5:
        if raw_score < 25:
            overrides_applied.append("OV1_GRAVITE_LEGALE_ABSOLUE")
        raw_score = max(raw_score, 25)

    # Override 2 : Urgence absolue qualifiée.
    if d == 5 and g >= 3:
        if raw_score < 22:
            overrides_applied.append("OV2_URGENCE_QUALIFIEE")
        raw_score = max(raw_score, 22)

    # Override 3 : Plafond impact orphelin.
    if i == 5 and g == 0:
        if raw_score > 15:
            overrides_applied.append("OV3_IMPACT_ORPHELIN")
        raw_score = min(raw_score, 15)

    total = max(0, raw_score)

    breakdown = {
        "g": g,
        "i": i,
        "d": d,
        "g_weighted": g_w,
        "i_weighted": i_w,
        "d_weighted": d_w,
    }

    return PriorityScore(
        total=total,
        tier=_resolve_tier(total, persona),
        persona=persona,
        breakdown=breakdown,
        overrides_applied=overrides_applied,
    )


def _resolve_tier(total: int, persona: Persona) -> Tier:
    thresholds = PERSONA_THRESHOLDS[persona]
    if total >= thresholds.P1:
        return Tier.P1
    if total >= thresholds.P2:
        return Tier.P2
    if total >= thresholds.P3:
        return Tier.P3
    return Tier.NONE


# ── Ranking + Top N (avec départage hub-aware) ──────────────────────────────


def rank_findings(
    findings: list[Finding],
    persona: Persona = Persona.RESPONSABLE_ENERGIE,
    hub: HubId = HubId.COCKPIT_JOUR,
    today: Optional[date] = None,
) -> list[tuple[Finding, PriorityScore]]:
    """Trie les findings par score décroissant avec départage hub-aware
    (catégorie ordre HUB_CAT_ORDER · délai croissant · impact décroissant)."""
    cat_order = HUB_CAT_ORDER.get(hub, HUB_CAT_ORDER[HubId.COCKPIT_JOUR])

    def cat_index(f: Finding) -> int:
        cat = f.resolve_category()
        try:
            return cat_order.index(cat)
        except ValueError:
            return len(cat_order)

    scored = [(f, compute_finding_priority(f, persona, today=today)) for f in findings]
    return sorted(
        scored,
        key=lambda fs: (
            -fs[1].total,
            cat_index(fs[0]),
            fs[1].breakdown.get("d", 0) * -1,  # D élevé = urgent → en premier
            -(fs[1].breakdown.get("i", 0)),  # I élevé = impact → en premier
        ),
    )


def top_n(
    findings: list[Finding],
    n: int = 3,
    persona: Persona = Persona.RESPONSABLE_ENERGIE,
    hub: HubId = HubId.COCKPIT_JOUR,
    today: Optional[date] = None,
) -> list[tuple[Finding, PriorityScore]]:
    """Top N findings (filtre les tier NONE)."""
    ranked = [(f, s) for f, s in rank_findings(findings, persona=persona, hub=hub, today=today) if s.tier != Tier.NONE]
    return ranked[:n]


# Constantes max score (pour normalisation UI éventuelle).
MAX_SCORE_RESPONSABLE_ENERGIE = 35
MAX_SCORE_DAF = 35
MAX_SCORE_DG_COMEX = 40
# Rétro-compat F.19a — exposé pour tests existants.
MAX_SCORE = 200  # déprécié, conservé pour back-compat tests
