"""
PROMEOS — Step 33 : Snapshot mensuel + trend du score conformite.
"""

import logging
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.compliance_score_history import ComplianceScoreHistory

logger = logging.getLogger("promeos.compliance_score_trend")


def _score_to_grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "F"


def snapshot_monthly_scores(db: Session, org_id: int, month_key: str = None) -> int:
    """
    Prend un snapshot du score conformite de chaque site pour le mois donne.
    Idempotent via UniqueConstraint site_id + month_key.
    Retourne le nombre d'entrees creees.
    """
    from models import Site, Portefeuille, EntiteJuridique
    from services.compliance_score_service import compute_site_compliance_score

    if not month_key:
        month_key = date.today().strftime("%Y-%m")

    sites = (
        db.query(Site)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id, Site.actif == True)
        .all()
    )

    created = 0
    for site in sites:
        existing = (
            db.query(ComplianceScoreHistory)
            .filter_by(site_id=site.id, month_key=month_key)
            .first()
        )
        if existing:
            continue

        try:
            result = compute_site_compliance_score(db, site.id)
            score = result.score if hasattr(result, "score") else result.get("score", 50.0)
            breakdown = result.breakdown if hasattr(result, "breakdown") else result.get("breakdown")
        except Exception:
            score = 50.0
            breakdown = None

        entry = ComplianceScoreHistory(
            site_id=site.id,
            org_id=org_id,
            month_key=month_key,
            score=round(score, 1),
            grade=_score_to_grade(score),
            breakdown_json=breakdown,
        )
        db.add(entry)
        created += 1

    db.flush()
    return created


def get_score_trend(db: Session, org_id: int, months: int = 6) -> list:
    """
    Retourne le score moyen portfolio par mois sur N mois.
    Pour la sparkline du Cockpit.
    """
    cutoff = (date.today().replace(day=1) - timedelta(days=months * 31)).strftime("%Y-%m")

    rows = (
        db.query(
            ComplianceScoreHistory.month_key,
            func.avg(ComplianceScoreHistory.score).label("avg_score"),
            func.count(ComplianceScoreHistory.site_id).label("sites_count"),
        )
        .filter(
            ComplianceScoreHistory.org_id == org_id,
            ComplianceScoreHistory.month_key >= cutoff,
        )
        .group_by(ComplianceScoreHistory.month_key)
        .order_by(ComplianceScoreHistory.month_key)
        .all()
    )

    return [
        {"month": r.month_key, "score": round(r.avg_score, 1), "sites": r.sites_count}
        for r in rows
    ]
