"""Aggregates actionable issues from compliance, billing, purchase into a unified view."""

import logging
from sqlalchemy.orm import Session
from models import Site
from models.base import not_deleted
from schemas.action_center import ActionableIssue, IssueSeverity, IssueDomain

logger = logging.getLogger("promeos.action_center")


def collect_compliance_issues(db: Session, org_id: int, site_ids: list = None) -> list:
    """Collect compliance-related actionable issues."""
    issues = []
    from routes.patrimoine._helpers import _compute_compliance_review_status

    query = db.query(Site).filter(not_deleted(Site))
    # scope to org via portefeuille chain
    from models import Portefeuille, EntiteJuridique

    query = query.join(Portefeuille).join(EntiteJuridique).filter(EntiteJuridique.organisation_id == org_id)
    if site_ids:
        query = query.filter(Site.id.in_(site_ids))

    for site in query.all():
        review = _compute_compliance_review_status(site)
        if not review["needs_review"]:
            continue

        # Determine severity
        reasons = review["reasons"]
        if "non_conforme" in reasons or "score_critique" in reasons:
            severity = IssueSeverity.critical
        elif "risque_eleve" in reasons:
            severity = IssueSeverity.high
        elif "a_risque" in reasons:
            severity = IssueSeverity.medium
        else:
            severity = IssueSeverity.low

        impact = getattr(site, "risque_financier_euro", None)

        issues.append(
            ActionableIssue(
                issue_id=f"compliance_review_{site.id}",
                domain=IssueDomain.compliance,
                severity=severity,
                site_id=site.id,
                site_name=site.nom,
                issue_code="compliance_needs_review",
                issue_label=f"Site {site.nom} nécessite une revue conformité",
                reason_codes=reasons,
                estimated_impact_eur=impact,
                recommended_action="Vérifier la conformité réglementaire et compléter les données manquantes",
            )
        )

    return issues


def collect_billing_issues(db: Session, org_id: int, site_ids: list = None) -> list:
    """Collect billing-related actionable issues (incomplete data, missing contracts)."""
    issues = []
    from routes.patrimoine._helpers import _compute_site_completeness

    query = db.query(Site).filter(not_deleted(Site))
    from models import Portefeuille, EntiteJuridique

    query = query.join(Portefeuille).join(EntiteJuridique).filter(EntiteJuridique.organisation_id == org_id)
    if site_ids:
        query = query.filter(Site.id.in_(site_ids))

    sites = query.all()
    scoped_ids = [s.id for s in sites]

    for site in sites:
        completeness = _compute_site_completeness(db, site, scoped_ids)
        missing = completeness.get("missing", [])

        if "contrat_actif" in missing:
            issues.append(
                ActionableIssue(
                    issue_id=f"billing_no_contract_{site.id}",
                    domain=IssueDomain.billing,
                    severity=IssueSeverity.high,
                    site_id=site.id,
                    site_name=site.nom,
                    issue_code="no_active_contract",
                    issue_label=f"Aucun contrat actif pour {site.nom}",
                    reason_codes=["contrat_actif_manquant"],
                    recommended_action="Ajouter un contrat énergie actif pour ce site",
                )
            )

        if "delivery_point" in missing:
            issues.append(
                ActionableIssue(
                    issue_id=f"billing_no_pdl_{site.id}",
                    domain=IssueDomain.billing,
                    severity=IssueSeverity.medium,
                    site_id=site.id,
                    site_name=site.nom,
                    issue_code="no_delivery_point",
                    issue_label=f"Aucun point de livraison pour {site.nom}",
                    reason_codes=["pdl_manquant"],
                    recommended_action="Ajouter un compteur avec PRM/PCE pour créer le point de livraison",
                )
            )

    return issues


def collect_patrimoine_issues(db: Session, org_id: int, site_ids: list = None) -> list:
    """Collect patrimoine completeness issues."""
    issues = []
    from routes.patrimoine._helpers import _compute_site_completeness

    query = db.query(Site).filter(not_deleted(Site))
    from models import Portefeuille, EntiteJuridique

    query = query.join(Portefeuille).join(EntiteJuridique).filter(EntiteJuridique.organisation_id == org_id)
    if site_ids:
        query = query.filter(Site.id.in_(site_ids))

    sites = query.all()
    scoped_ids = [s.id for s in sites]

    for site in sites:
        completeness = _compute_site_completeness(db, site, scoped_ids)
        score = completeness.get("score", 100)

        if score < 50:
            issues.append(
                ActionableIssue(
                    issue_id=f"patrimoine_incomplete_{site.id}",
                    domain=IssueDomain.patrimoine,
                    severity=IssueSeverity.medium,
                    site_id=site.id,
                    site_name=site.nom,
                    issue_code="patrimoine_incomplete",
                    issue_label=f"Données patrimoniales incomplètes ({score}%) pour {site.nom}",
                    reason_codes=completeness.get("missing", []),
                    recommended_action="Compléter les données site via le drawer patrimoine",
                )
            )

    return issues


def get_action_center_issues(
    db: Session, org_id: int, domain: str = None, severity: str = None, site_id: int = None, status: str = None
) -> dict:
    """Aggregate all actionable issues across domains."""
    site_ids = [site_id] if site_id else None

    all_issues = []

    # Collect from each domain
    if not domain or domain == "compliance":
        all_issues.extend(collect_compliance_issues(db, org_id, site_ids))
    if not domain or domain == "billing":
        all_issues.extend(collect_billing_issues(db, org_id, site_ids))
    if not domain or domain == "patrimoine":
        all_issues.extend(collect_patrimoine_issues(db, org_id, site_ids))

    # Filter by severity
    if severity:
        all_issues = [i for i in all_issues if i.severity.value == severity]

    # Filter by status
    if status:
        all_issues = [i for i in all_issues if i.status == status]

    # Sort by severity (critical first)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    all_issues.sort(key=lambda i: severity_order.get(i.severity.value, 5))

    # Compute domain/severity counts
    domains = {}
    severities = {}
    for i in all_issues:
        domains[i.domain.value] = domains.get(i.domain.value, 0) + 1
        severities[i.severity.value] = severities.get(i.severity.value, 0) + 1

    return {
        "total": len(all_issues),
        "issues": [i.model_dump() for i in all_issues],
        "domains": domains,
        "severities": severities,
    }
