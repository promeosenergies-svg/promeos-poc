"""
PROMEOS — services/cockpit_highlights_service.py : agrégateur findings cockpit
(ADR-022 F.19b).

Collecte les findings candidates depuis 3 sources :
  1. Compliance — anomalies Décret tertiaire / BACS / APER / Audit SMÉ
  2. Billing    — anomalies factures (R01-R31 via bill_intelligence)
  3. Platform   — données EMS rancies, connecteurs interrompus

Applique l'algorithme de scoring canonique
`regops.priority_scoring.compute_finding_priority` puis retourne le Top N
(défaut 3 pour Cockpit Jour) au format Sol L11.3 (highlight dict).

Pour la démo HELIOS (5 sites), si les détecteurs réels ne retournent rien
(pas encore branchés F.17), un fallback `_demo_findings_helios` génère
des findings réalistes basées sur le contexte des sites — qui passent
quand même par le scoring (zéro hardcode des P1/P2/P3 affichés).

Doctrine ADR-022 §Highlights Top 3.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from regops.priority_scoring import (
    DOCTRINE_VERSION,
    Domain,
    Finding,
    HubId,
    Persona,
    PriorityScore,
    Scope,
    Severity,
    Tier,
    top_n,
)


# ── Sérialisation Finding → contrat Sol L11.3 highlight dict ────────────────


_SEVERITY_DISPLAY: dict[Severity, str] = {
    Severity.CRITICAL: "crit",
    Severity.HIGH: "warn",
    Severity.MEDIUM: "info",
    Severity.LOW: "info",
}


def finding_to_highlight_dict(finding: Finding, score: PriorityScore, rang: int) -> dict:
    """Sérialise une finding scorée vers le contrat highlight Sol L11.3.

    Phase F.22 — payload audit trail enrichi avec persona + overrides_applied
    + doctrine_version pour traçabilité complète.
    """
    return {
        "id": finding.finding_id or f"hl-{rang}",
        "rang": rang,
        "tier": score.tier.value,  # P1 / P2 / P3 / NONE
        "severity": _SEVERITY_DISPLAY.get(finding.severity, "info"),
        "category": finding.category_label,
        "scope": finding.site_name,
        "title": finding.title,
        "evidence": finding.evidence,
        "impact": {
            "value": finding.impact_label or "—",
            "label": _impact_label_for(finding),
        },
        "invitation": {
            "verb": finding.invitation_verb,
            "object": finding.invitation_object,
            "href": finding.invitation_href,
        },
        # Audit trail v1 doctrine (ADR-022 + sprint priorisation v1.0).
        "_audit": {
            "score_total": score.total,
            "score_breakdown": score.breakdown,
            "persona": score.persona.value,
            "overrides_applied": score.overrides_applied,
            "doctrine_version": DOCTRINE_VERSION,
            "domain": finding.domain.value,
            "category": finding.resolve_category().value,
            "scope_level": finding.scope_level.value,
        },
    }


def _impact_label_for(finding: Finding) -> str:
    """Libellé d'impact contextuel selon le domaine."""
    if finding.impact_eur_year and finding.impact_eur_year > 0:
        return "pénalité estimée" if finding.domain == Domain.COMPLIANCE else "impact estimé"
    if finding.deadline_date:
        return "échéance"
    return "impact à confirmer"


# ── Collecteurs par source (3 détecteurs) ───────────────────────────────────
#
# Note F.19b : ces collecteurs retournent des findings simulées calibrées
# sur le contexte HELIOS pour la démo investisseur. Le câblage aux vrais
# services (compliance_score_service, bill_intelligence, EMS staleness)
# est planifié F.17. Le scoring lui passe par l'algo canonique → tout est
# audité même en mode démo.


def _collect_compliance_findings(db: Session, org_id: Optional[int]) -> list[Finding]:
    """Collecte les findings de conformité depuis compliance_score_service.

    Phase F.20a : remplace les mocks F.19b par les vrais scores compliance
    V2 adaptatif (5 frameworks tertiaire_operat / bacs / aper / audit_sme
    / solar_toiture) par site. Cf `services.highlights_detectors`.
    """
    from services.highlights_detectors import detect_compliance_findings

    return detect_compliance_findings(db, org_id)


def _collect_billing_findings(db: Session, org_id: Optional[int]) -> list[Finding]:
    """Collecte les anomalies billing (factures R01-R31).

    Phase F.20a : appelle `highlights_detectors.detect_billing_findings`
    qui retourne [] pour l'instant (intégration bill_intelligence en F.21).
    """
    from services.highlights_detectors import detect_billing_findings

    return detect_billing_findings(db, org_id)


def _collect_platform_health_findings(db: Session, org_id: Optional[int]) -> list[Finding]:
    """Collecte les findings de santé plateforme (EMS staleness, connecteurs).

    Phase F.20a : remplace le mock F.19b par le détecteur réel basé sur
    max(MeterReading.timestamp) par site. Sévérité dépend de l'âge :
    > 72h = CRITICAL, > 24h = HIGH.
    """
    from services.highlights_detectors import detect_ems_staleness_findings

    return detect_ems_staleness_findings(db, org_id)


# ── API publique ─────────────────────────────────────────────────────────────


def build_top_n_highlights(
    db: Session,
    org_id: Optional[int],
    n: int = 3,
    today: Optional[date] = None,
    persona: Persona = Persona.RESPONSABLE_ENERGIE,
    hub: HubId = HubId.COCKPIT_JOUR,
) -> list[dict]:
    """Construit le Top N highlights cockpit jour, scoré + trié + sérialisé.

    Args:
        db      : session SQLAlchemy.
        org_id  : organisation scope (None = pas de filtre).
        n       : taille du top (défaut 3 pour Cockpit Jour Sol L11.3).
        today   : date de référence injectable pour tests.

    Returns:
        Liste de dicts au format Sol L11.3 highlight, triés par priorité
        décroissante. Inclut un champ `_audit` avec score_breakdown pour
        traçabilité (ADR-022 anti-pattern "P1 sans evidence").

    Doctrine ADR-022 §Highlights Top 3.
    """
    from regops.priority_scoring import rank_findings

    findings: list[Finding] = []
    findings.extend(_collect_compliance_findings(db, org_id))
    findings.extend(_collect_billing_findings(db, org_id))
    findings.extend(_collect_platform_health_findings(db, org_id))

    # Phase F.20a + F.22 — ranking avec persona + hub (départage HUB_CAT_ORDER)
    # puis double dédup catégorie + site (anti-pattern Sol §L11.3 AP3).
    ranked = rank_findings(findings, persona=persona, hub=hub, today=today)
    seen_categories: set[str] = set()
    seen_sites: set[Optional[int]] = set()
    deduplicated: list = []
    for finding, score in ranked:
        if score.tier.value == "NONE":
            continue
        if finding.category_label in seen_categories:
            continue
        if finding.site_id is not None and finding.site_id in seen_sites:
            continue
        seen_categories.add(finding.category_label)
        if finding.site_id is not None:
            seen_sites.add(finding.site_id)
        deduplicated.append((finding, score))
        if len(deduplicated) >= n:
            break

    return [finding_to_highlight_dict(finding, score, rang=i + 1) for i, (finding, score) in enumerate(deduplicated)]


def count_total_signals(
    db: Session,
    org_id: Optional[int],
    today: Optional[date] = None,
    persona: Persona = Persona.RESPONSABLE_ENERGIE,
) -> dict:
    """Retourne le compte des findings actifs ventilés par tier.

    Utilisé par le générateur de hero narratif pour afficher
    "X signaux méritent votre attention" (X = P1 + P2 du briefing).

    Returns:
        {"p1": int, "p2": int, "p3": int, "total": int}
    """
    findings: list[Finding] = []
    findings.extend(_collect_compliance_findings(db, org_id))
    findings.extend(_collect_billing_findings(db, org_id))
    findings.extend(_collect_platform_health_findings(db, org_id))

    from regops.priority_scoring import compute_finding_priority

    counts = {"p1": 0, "p2": 0, "p3": 0, "total": 0}
    for f in findings:
        score = compute_finding_priority(f, persona=persona, today=today)
        if score.tier == Tier.P1:
            counts["p1"] += 1
        elif score.tier == Tier.P2:
            counts["p2"] += 1
        elif score.tier == Tier.P3:
            counts["p3"] += 1
        if score.tier != Tier.NONE:
            counts["total"] += 1
    return counts
