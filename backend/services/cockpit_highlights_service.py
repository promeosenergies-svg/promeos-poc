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
    Domain,
    Finding,
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

    Format aligné sur `_build_cockpit_jour_highlights` historique pour
    rétro-compat avec `HubHighlight.jsx` (frontend).
    """
    return {
        "id": finding.finding_id or f"hl-{rang}",
        "rang": rang,
        "tier": score.tier.value,  # P1 / P2 / P3
        "severity": _SEVERITY_DISPLAY.get(finding.severity, "info"),
        "category": finding.category_label,
        "scope": finding.site_name,  # Texte affiché ex "Bureau Régional Lyon"
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
        # Audit trail (ADR-022 anti-pattern "P1 sans evidence")
        "_audit": {
            "score_total": score.total,
            "score_breakdown": score.breakdown,
            "domain": finding.domain.value,
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
    """Collecte les findings de conformité (DT / BACS / APER / Audit SMÉ).

    F.19b : retourne des findings démo HELIOS calibrées. F.17 branchera
    `compliance_score_service.detect_anomalies(site)` pour chaque site.
    """
    return [
        Finding(
            severity=Severity.HIGH,
            domain=Domain.COMPLIANCE,
            scope_level=Scope.SITE,
            impact_eur_year=3_800.0,
            deadline_date=date(2030, 12, 31),  # DT jalon -40 %
            finding_id="hl-lyon-dt-2030",
            title="Écart de conformité à qualifier — Décret tertiaire",
            site_id=2,
            site_name="Bureau Régional Lyon",
            evidence=(
                "Surface 1 240 m² déclarée · usage tertiaire mixte · jalon 2030 à −40 %. Preuve OPERAT à reconstituer."
            ),
            category_label="Conformité",
            impact_label="3,8 k€/an",
            invitation_verb="voir",
            invitation_object="la preuve",
            invitation_href="/compliance/sites/2",
        ),
        Finding(
            severity=Severity.MEDIUM,
            domain=Domain.COMPLIANCE,
            scope_level=Scope.SITE,
            impact_eur_year=None,
            deadline_date=date(2027, 1, 1),  # BACS jalon 2027
            finding_id="hl-paris-bacs-cvc",
            title="Revue BACS recommandée — puissance CVC à confirmer",
            site_id=1,
            site_name="Siège HELIOS Paris",
            evidence=(
                "Site > 1 000 m², seuil BACS 2027 applicable. Puissance CVC"
                " déclarée 290 kW à confirmer pour qualifier l'obligation."
            ),
            category_label="Conformité BACS",
            impact_label="2027",
            invitation_verb="programmer",
            invitation_object="la revue",
            invitation_href="/compliance/sites/1",
        ),
    ]


def _collect_billing_findings(db: Session, org_id: Optional[int]) -> list[Finding]:
    """Collecte les anomalies billing (factures R01-R31).

    F.19b : aucune anomalie billing demo HELIOS pour l'instant. F.17
    branchera `bill_intelligence.detect_anomalies_for_invoice(invoice)`
    sur les factures récentes scope.
    """
    return []


def _collect_platform_health_findings(db: Session, org_id: Optional[int]) -> list[Finding]:
    """Collecte les findings de santé plateforme (EMS staleness, connecteurs).

    F.19b : retourne 1 finding démo (Toulouse EMS connector). F.17 branchera
    un détecteur réel sur l'âge de la dernière mesure par site.
    """
    return [
        Finding(
            severity=Severity.HIGH,
            domain=Domain.PLATFORM_HEALTH,
            scope_level=Scope.SITE,
            impact_eur_year=None,
            deadline_date=None,
            finding_id="hl-toulouse-ems-connector",
            title="Connecteur EMS à vérifier avant recalcul de conformité",
            site_id=3,
            site_name="Entrepôt HELIOS Toulouse",
            evidence=(
                "Dernière mesure il y a 6 jours · synchronisation Enedis"
                " interrompue · recalcul conformité bloqué tant que la"
                " connexion n'est pas rétablie."
            ),
            category_label="Donnée EMS",
            impact_label="—",
            invitation_verb="vérifier",
            invitation_object="le connecteur",
            invitation_href="/connectors?site_id=3",
        ),
    ]


# ── API publique ─────────────────────────────────────────────────────────────


def build_top_n_highlights(
    db: Session,
    org_id: Optional[int],
    n: int = 3,
    today: Optional[date] = None,
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
    findings: list[Finding] = []
    findings.extend(_collect_compliance_findings(db, org_id))
    findings.extend(_collect_billing_findings(db, org_id))
    findings.extend(_collect_platform_health_findings(db, org_id))

    ranked = top_n(findings, n=n, today=today)

    return [finding_to_highlight_dict(finding, score, rang=i + 1) for i, (finding, score) in enumerate(ranked)]


def count_total_signals(db: Session, org_id: Optional[int], today: Optional[date] = None) -> dict:
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
        score = compute_finding_priority(f, today=today)
        if score.tier == Tier.P1:
            counts["p1"] += 1
        elif score.tier == Tier.P2:
            counts["p2"] += 1
        elif score.tier == Tier.P3:
            counts["p3"] += 1
        if score.tier != Tier.NONE:
            counts["total"] += 1
    return counts
