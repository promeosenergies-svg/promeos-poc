"""
PROMEOS — regops/priority_scoring.py : algorithme canonique de priorisation
des findings cockpit jour (ADR-022 F.19a).

Module SoT pour le scoring des highlights affichés dans le Top 3 priorités
du Cockpit Jour. Étend `services.patrimoine_impact.compute_priority_score`
(qui couvrait uniquement les anomalies patrimoine) avec :

  1. Couverture cross-domain : compliance + billing + EMS staleness +
     performance énergétique + opportunités CEE.
  2. Dimension "urgence" (deadline réglementaire / contractuelle).
  3. Dimension "scope" (effet de levier groupe vs portefeuille vs site).
  4. Dimension "domain doctrinal" (platform_health en premier — anti-pattern
     "conclusions sur données pourries").
  5. Tiering explicite P1/P2/P3 mappé doctrine Sol L11.3 (highlights).

Doctrine de référence : `docs/adr/ADR-022-cockpit-data-sources.md`.

Tests unitaires : `backend/tests/regops/test_priority_scoring.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional


# ── Enums ────────────────────────────────────────────────────────────────────


class Severity(str, Enum):
    """Sévérité d'une finding. Aligné sur `patrimoine_impact._SEV_BASE`."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Domain(str, Enum):
    """Domaine doctrinal d'une finding.

    Ordre de priorité doctrinale (cf ADR-022) :
      1. PLATFORM_HEALTH — données pourries bloquent toute conclusion fiable
      2. COMPLIANCE      — sanctions réglementaires datées (DT, BACS, OPERAT…)
      3. FINANCIAL       — surcoûts factures, opportunités €
      4. ENERGY          — dérives consommation, dépassements
      5. OPTIMISATION    — recommandations préventives (CEE, flex, ACC…)
    """

    PLATFORM_HEALTH = "PLATFORM_HEALTH"
    COMPLIANCE = "COMPLIANCE"
    FINANCIAL = "FINANCIAL"
    ENERGY = "ENERGY"
    OPTIMISATION = "OPTIMISATION"


class Scope(str, Enum):
    """Périmètre concerné par la finding (effet de levier décision)."""

    GROUP = "GROUP"  # Toute l'organisation
    PORTFOLIO = "PORTFOLIO"  # Un portefeuille (sous-ensemble de sites)
    SITE = "SITE"  # Un site unique


class Tier(str, Enum):
    """Tier doctrinal mappé à l'affichage Sol L11.3 (P1/P2/P3)."""

    P1 = "P1"  # Critique — action sous 30 jours
    P2 = "P2"  # Alerte — action sous 90 jours
    P3 = "P3"  # Veille / recommandation
    NONE = "NONE"  # Non affiché dans le briefing


# ── Pondérations doctrinales (ADR-022) ──────────────────────────────────────


# Sévérité (max 60 pts) — hérité `patrimoine_impact._SEV_BASE` × 2 pour
# élargir l'amplitude vs nouvelles dimensions.
_SEVERITY_WEIGHTS: dict[Severity, int] = {
    Severity.CRITICAL: 60,
    Severity.HIGH: 50,
    Severity.MEDIUM: 30,
    Severity.LOW: 10,
}

# Impact financier €/an (max 40 pts) — buckets log-scale pour amortir les
# montants extrêmes et éviter d'écraser les autres dimensions.
_IMPACT_BUCKETS: list[tuple[float, int]] = [
    (50_000, 40),  # > 50 k€/an → 40 pts
    (10_000, 30),  # 10-50 k€/an → 30 pts
    (1_000, 20),  # 1-10 k€/an → 20 pts
    (0, 0),  # sinon 0
]

# Urgence (max 50 pts) — décroissance par paliers calendaires alignés sur
# les jalons régulatoires français (mensuel / trimestriel / annuel / DT 2030).
_URGENCY_THRESHOLDS: list[tuple[int, int]] = [
    (30, 50),  # ≤ 30 jours → 50 pts (action immédiate)
    (90, 35),  # ≤ 90 jours → 35 pts (trimestre courant)
    (365, 20),  # ≤ 1 an → 20 pts
    (730, 10),  # ≤ 2 ans → 10 pts
]

# Scope (max 30 pts) — effet de levier décisionnel groupe vs site.
_SCOPE_WEIGHTS: dict[Scope, int] = {
    Scope.GROUP: 30,
    Scope.PORTFOLIO: 20,
    Scope.SITE: 10,
}

# Domain doctrinal (max 20 pts) — platform_health PASSE EN PREMIER
# (anti-pattern doctrinal "conclusions sur données pourries").
_DOMAIN_WEIGHTS: dict[Domain, int] = {
    Domain.PLATFORM_HEALTH: 20,
    Domain.COMPLIANCE: 18,
    Domain.FINANCIAL: 15,
    Domain.ENERGY: 12,
    Domain.OPTIMISATION: 8,
}

# Tiering (mapping score → P1/P2/P3) cf ADR-022 § Roadmap.
_TIER_THRESHOLDS: list[tuple[int, Tier]] = [
    (130, Tier.P1),  # action critique sous 30 jours
    (80, Tier.P2),  # alerte action sous 90 jours
    (40, Tier.P3),  # veille / recommandation
]

# Score max théorique : 60 + 40 + 50 + 30 + 20 = 200 pts.
MAX_SCORE = 200


# ── Data class Finding (contrat input) ──────────────────────────────────────


@dataclass(frozen=True)
class Finding:
    """Représente une finding candidate pour le Top 3 priorités cockpit.

    Champs obligatoires :
      severity, domain, scope_level

    Champs optionnels :
      impact_eur_year : impact financier estimé en €/an (None = non chiffré)
      deadline_date   : date limite réglementaire/contractuelle (None = sans)
      finding_id      : identifiant stable pour traçabilité
      title           : titre court (affiché P1/P2/P3)
      site_id         : site concerné (None pour finding GROUP)
      site_name       : nom du site pour évidence
      evidence        : texte d'évidence (preuve chiffrée)
      invitation_href : URL d'action ("voir la preuve", "vérifier le connecteur"…)
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
    impact_label: str = ""  # ex "3,8 k€/an", "—", "2027"


# ── Data class PriorityScore (contrat output) ───────────────────────────────


@dataclass(frozen=True)
class PriorityScore:
    """Résultat de scoring d'une finding."""

    total: int
    tier: Tier
    breakdown: dict[str, int] = field(default_factory=dict)


# ── Calcul des composantes ──────────────────────────────────────────────────


def _severity_component(severity: Severity) -> int:
    return _SEVERITY_WEIGHTS.get(severity, 0)


def _impact_component(eur_year: Optional[float]) -> int:
    if eur_year is None or eur_year <= 0:
        return 0
    for threshold, points in _IMPACT_BUCKETS:
        if eur_year > threshold:
            return points
    return 0


def _urgency_component(deadline_date: Optional[date], today: Optional[date] = None) -> int:
    if deadline_date is None:
        return 0
    today = today or datetime.now(tz=timezone.utc).date()
    days = (deadline_date - today).days
    if days < 0:
        # Deadline passée → urgence max (sanction probable en cours).
        return _URGENCY_THRESHOLDS[0][1]
    for threshold, points in _URGENCY_THRESHOLDS:
        if days <= threshold:
            return points
    return 0


def _scope_component(scope_level: Scope) -> int:
    return _SCOPE_WEIGHTS.get(scope_level, 0)


def _domain_component(domain: Domain) -> int:
    return _DOMAIN_WEIGHTS.get(domain, 0)


def _resolve_tier(total: int) -> Tier:
    for threshold, tier in _TIER_THRESHOLDS:
        if total >= threshold:
            return tier
    return Tier.NONE


# ── API publique ─────────────────────────────────────────────────────────────


def compute_finding_priority(finding: Finding, today: Optional[date] = None) -> PriorityScore:
    """Calcule le score doctrinal d'une finding cockpit.

    Args:
        finding : Finding candidate (cf data class ci-dessus).
        today   : Date de référence (défaut : aujourd'hui UTC). Injectable
                  pour tests reproductibles.

    Returns:
        PriorityScore avec :
            - total ∈ [0, MAX_SCORE=200]
            - tier ∈ {P1, P2, P3, NONE}
            - breakdown {dimension: points} pour traçabilité audit user.

    Doctrine ADR-022 §Algorithme de priorisation.
    """
    sev = _severity_component(finding.severity)
    impact = _impact_component(finding.impact_eur_year)
    urgency = _urgency_component(finding.deadline_date, today=today)
    scope = _scope_component(finding.scope_level)
    domain = _domain_component(finding.domain)

    total = sev + impact + urgency + scope + domain
    total = min(MAX_SCORE, max(0, total))

    breakdown = {
        "severity": sev,
        "impact": impact,
        "urgency": urgency,
        "scope": scope,
        "domain": domain,
    }

    return PriorityScore(total=total, tier=_resolve_tier(total), breakdown=breakdown)


def rank_findings(findings: list[Finding], today: Optional[date] = None) -> list[tuple[Finding, PriorityScore]]:
    """Trie les findings par score décroissant et retourne les paires.

    Args:
        findings : Liste de candidates.
        today    : Date de référence injectable pour tests.

    Returns:
        Liste de tuples (finding, score) triés DESC par score.total. Inclut
        les findings de tier NONE — au caller de slicer top N et de filtrer
        si nécessaire (ex `[t for t in ranked if t[1].tier != Tier.NONE]`).
    """
    scored = [(f, compute_finding_priority(f, today=today)) for f in findings]
    return sorted(scored, key=lambda fs: fs[1].total, reverse=True)


def top_n(findings: list[Finding], n: int = 3, today: Optional[date] = None) -> list[tuple[Finding, PriorityScore]]:
    """Retourne le Top N des findings (par défaut top 3 pour cockpit jour).

    Filtre les findings de tier NONE (sous le seuil P3).
    """
    ranked = [(f, s) for f, s in rank_findings(findings, today=today) if s.tier != Tier.NONE]
    return ranked[:n]
