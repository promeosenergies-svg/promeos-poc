"""PROMEOS — Navigation badges aggregation service.

Source de vérité unique pour les 8 compteurs exposés via
GET /api/v1/navigation/badges. Agrégation pure : aucune logique métier
nouvelle, réutilisation des services existants (notification_service,
action_center_service, compute_portfolio_compliance) et des modèles
canoniques (MonitoringAlert, EnergyInvoice, EnergyContract).

Doctrine §8.1 : ce service est 100 % backend, le FE ne fait qu'affichage.

Phase 2.A — P1.2 (audit navigation_audit_20260501.md §3.3 + §5).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import EntiteJuridique, Portefeuille, Site, not_deleted
from models.billing_models import EnergyContract, EnergyInvoice
from models.energy_models import AlertStatus, MonitoringAlert
from models.enums import BillingInvoiceStatus
from schemas.navigation import NavBadgesResponse
from services.action_center_service import get_action_center_issues
from services.compliance_score_service import compute_portfolio_compliance

# Phase 2.A — P1.2 : couplage explicite sur le symbole privé
# `_count_summary` (dette P1 reviewer). Le scope strict P1.2 interdit la
# modification de notification_service.py — exposition publique
# `get_notification_summary` à tracker en ticket dédié post-merge.
# Mitigation : `test_sg_nav_05_count_summary_signature_stable`
# (source-guard) + `test_org_isolation` (intégration) détecteront tout
# changement silencieux de signature ou de retour.
from services.notification_service import _count_summary  # noqa: PLC2701

# Convention production : alerte d'expiration contractuelle 90 jours
# (cf. backend/services/contract_expiration_alerts.py:26 horizon_days=90,
# titre alerte "Contrat expire sous 90j"). Aligner ici sur la même fenêtre
# évite la divergence sémantique entre le badge rail et l'alerte stockée.
PURCHASE_WINDOW_DAYS = 90


def _org_active_site_ids_subquery(db: Session, org_id: int):
    """Sélection canonique des site_id actifs appartenant à l'org.

    Chaîne canonique Site → Portefeuille → EntiteJuridique → Organisation,
    convention déjà appliquée par compute_portfolio_compliance et
    action_center_service. Garantit l'isolation multi-tenant.

    Retourne un Select scalaire utilisable dans un `column.in_(...)` —
    SQLAlchemy 2.x décourage la coercion implicite Subquery → Select.
    """
    return (
        not_deleted(db.query(Site.id), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(
            EntiteJuridique.organisation_id == org_id,
            Site.actif == True,  # noqa: E712 (SQLAlchemy column equality)
        )
        .scalar_subquery()
    )


def _count_open_monitoring_alerts(db: Session, org_id: int) -> int:
    """Compte les MonitoringAlert ouvertes pour l'org."""
    site_ids = _org_active_site_ids_subquery(db, org_id)
    return (
        db.query(MonitoringAlert)
        .filter(
            MonitoringAlert.status == AlertStatus.OPEN,
            MonitoringAlert.site_id.in_(site_ids),
        )
        .count()
    )


def _count_unreviewed_billing_anomalies(db: Session, org_id: int) -> int:
    """Compte les EnergyInvoice en statut ANOMALY pour l'org."""
    site_ids = _org_active_site_ids_subquery(db, org_id)
    return (
        db.query(EnergyInvoice)
        .filter(
            EnergyInvoice.status == BillingInvoiceStatus.ANOMALY,
            EnergyInvoice.site_id.in_(site_ids),
        )
        .count()
    )


def _count_market_windows_within(db: Session, org_id: int, days: int = PURCHASE_WINDOW_DAYS) -> int:
    """Compte les contrats expirant entre aujourd'hui et J+`days`.

    Pattern aligné sur contract_expiration_alerts.py:44-52 : `end_date >=
    today` exclut les contrats déjà expirés, `end_date <= deadline` cadre
    la fenêtre d'alerte.
    """
    today = date.today()
    deadline = today + timedelta(days=days)
    site_ids = _org_active_site_ids_subquery(db, org_id)
    return (
        db.query(EnergyContract)
        .filter(
            EnergyContract.site_id.in_(site_ids),
            EnergyContract.end_date >= today,
            EnergyContract.end_date <= deadline,
        )
        .count()
    )


def _count_compliance_critical_warn(db: Session, org_id: int) -> int:
    """Wrapper sur notification_service._count_summary.

    Retourne new_critical + new_warn — compteur consommé historiquement
    par Sidebar.jsx pour le badge rail Conformité.
    """
    summary = _count_summary(db, org_id)
    return int(summary.get("new_critical", 0)) + int(summary.get("new_warn", 0))


def _count_action_center_open(db: Session, org_id: int) -> int:
    """Wrapper sur action_center_service.get_action_center_issues → total."""
    issues = get_action_center_issues(db, org_id)
    return int(issues.get("total", 0))


def _compute_compliance_progress(db: Session, org_id: int) -> tuple[float, float, float]:
    """Mapping tertiaire_operat → dt (doctrine §11.3).

    Réutilise compute_portfolio_compliance (moyenne pondérée par
    Site.surface_m2 avec fallback 1000 m²). Une clé framework peut être
    absente si l'org n'a aucun assessment pour ce framework — `.get(...,
    0.0)` garantit le contrat NavBadgesResponse (pas de None).
    """
    portfolio = compute_portfolio_compliance(db, org_id)
    breakdown = portfolio.get("breakdown_avg", {}) or {}
    return (
        float(breakdown.get("tertiaire_operat", 0.0)),
        float(breakdown.get("bacs", 0.0)),
        float(breakdown.get("aper", 0.0)),
    )


def compute_navigation_badges(db: Session, org_id: int) -> NavBadgesResponse:
    """Agrège les 8 compteurs nav pour l'org.

    Helpers privés synchrones (SQLAlchemy sync) — pas de gain de
    parallélisation backend, le bénéfice perf vient de la déduplication
    côté FE (1 call au lieu de 3 dispersés Sidebar/AppShell).
    """
    energy = _count_open_monitoring_alerts(db, org_id)
    compliance = _count_compliance_critical_warn(db, org_id)
    billing = _count_unreviewed_billing_anomalies(db, org_id)
    purchase = _count_market_windows_within(db, org_id)
    action = _count_action_center_open(db, org_id)
    dt, bacs, aper = _compute_compliance_progress(db, org_id)

    return NavBadgesResponse(
        energy_alerts=energy,
        compliance_alerts=compliance,
        billing_anomalies=billing,
        purchase_deadlines=purchase,
        action_center=action,
        conformite_dt_progress=dt,
        conformite_bacs_progress=bacs,
        conformite_aper_progress=aper,
        computed_at=datetime.now(timezone.utc),
        cache_ttl_seconds=60,
    )
