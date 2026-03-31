"""
PROMEOS — Coordinateur Conformité  ★ POINT D'ENTRÉE UNIQUE ★

Remplace les appels directs à recompute_site() dispersés dans l'application.
Garantit que les deux chemins de calcul conformité sont toujours mis à jour ensemble :

  1. recompute_site()                   → snapshots Site (statut_decret_tertiaire, statut_bacs, ...)
  2. regops.engine.evaluate_site()       → RegAssessment rows (score détaillé par framework)
  3. compliance_score_service.sync()     → Site.compliance_score_composite (score A.2 unifié)

USAGE :
  from services.compliance_coordinator import recompute_site_full
  recompute_site_full(db, site_id)   # remplace : recompute_site(db, site_id)
"""

import logging
from collections import defaultdict
from typing import List

from sqlalchemy.orm import Session

from models import Obligation, Site, Portefeuille, EntiteJuridique, Organisation, Evidence
from services.compliance_readiness_service import compute_site_snapshot

_logger = logging.getLogger(__name__)


# ── Fonctions recompute (persistence layer, ex-compliance_engine.py) ──


def _apply_snapshot(site: Site, snapshot: dict):
    """Apply a computed snapshot dict to a Site ORM object."""
    for key, value in snapshot.items():
        setattr(site, key, value)


def recompute_site(db: Session, site_id: int) -> dict:
    """Recompute and persist compliance snapshot for a single Site."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    obligations = db.query(Obligation).filter(Obligation.site_id == site_id).all()
    evidences = db.query(Evidence).filter(Evidence.site_id == site_id).all()
    snapshot = compute_site_snapshot(obligations, evidences)
    _apply_snapshot(site, snapshot)
    db.flush()
    return snapshot


def _bulk_recompute(db: Session, sites: List[Site]):
    """Recompute snapshots for a list of sites (3 queries total, no N+1)."""
    if not sites:
        return

    site_ids = [s.id for s in sites]
    all_obligations = db.query(Obligation).filter(Obligation.site_id.in_(site_ids)).all()
    all_evidences = db.query(Evidence).filter(Evidence.site_id.in_(site_ids)).all()

    obs_by_site = defaultdict(list)
    for ob in all_obligations:
        obs_by_site[ob.site_id].append(ob)
    evs_by_site = defaultdict(list)
    for ev in all_evidences:
        evs_by_site[ev.site_id].append(ev)

    for site in sites:
        snapshot = compute_site_snapshot(obs_by_site[site.id], evs_by_site[site.id])
        _apply_snapshot(site, snapshot)


def recompute_portfolio(db: Session, portefeuille_id: int) -> dict:
    """Recompute compliance for all sites in a portfolio."""
    portefeuille = db.query(Portefeuille).filter(Portefeuille.id == portefeuille_id).first()
    if not portefeuille:
        raise ValueError(f"Portefeuille {portefeuille_id} not found")

    sites = db.query(Site).filter(Site.portefeuille_id == portefeuille_id).all()
    _bulk_recompute(db, sites)
    db.commit()
    return {
        "portefeuille_id": portefeuille_id,
        "portefeuille_nom": portefeuille.nom,
        "sites_recomputed": len(sites),
    }


def recompute_organisation(db: Session, organisation_id: int) -> dict:
    """Recompute compliance for ALL sites in an organisation."""
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise ValueError(f"Organisation {organisation_id} not found")

    portefeuille_ids = [
        row[0]
        for row in db.query(Portefeuille.id)
        .join(EntiteJuridique)
        .filter(EntiteJuridique.organisation_id == organisation_id)
        .all()
    ]

    sites = db.query(Site).filter(Site.portefeuille_id.in_(portefeuille_ids)).all()
    _bulk_recompute(db, sites)
    db.commit()
    return {
        "organisation_id": organisation_id,
        "organisation_nom": org.nom,
        "sites_recomputed": len(sites),
    }


# ── Orchestration complète ──


def recompute_site_full(db: Session, site_id: int) -> dict:
    """Recompute complet d'un site — trois chemins synchronisés.

    Étapes :
    1. recompute_site() → snapshots legacy
    2. regops.engine.evaluate_site() → RegAssessment
    3. compliance_score_service.sync() → score A.2 unifié
    """
    snapshot = recompute_site(db, site_id)
    _logger.info("recompute_site_full site=%d: étape 1 (legacy snapshot) done", site_id)

    # ── Étape 1b : avancement DT dynamique (conso réelle vs référence) ───
    # Ne PAS écraser l'avancement issu de l'étape 1 (obligations) si la trajectoire
    # retourne 0 à cause de données manquantes (org_id, consommation...).
    try:
        from services.dt_trajectory_service import update_site_avancement

        avancement = update_site_avancement(db, site_id)
        if avancement is not None and avancement > 0:
            snapshot["avancement_decret_pct"] = avancement
            _logger.info(
                "recompute_site_full site=%d: étape 1b (avancement DT) = %.1f%%",
                site_id,
                avancement,
            )
        else:
            _logger.debug(
                "recompute_site_full site=%d: étape 1b — trajectoire non calculable, conserve avancement obligations (%.1f%%)",
                site_id,
                snapshot.get("avancement_decret_pct", 0),
            )
    except Exception as exc:
        _logger.warning(
            "recompute_site_full site=%d: étape 1b (avancement DT) failed (%s) — skipping",
            site_id,
            exc,
        )

    # ── Étape 2 : RegAssessment via RegOps engine ─────────────────────────────
    try:
        from regops.engine import evaluate_site, persist_assessment

        summary = evaluate_site(db, site_id)
        persist_assessment(db, summary)
        _logger.info(
            "recompute_site_full site=%d: étape 2 (RegAssessment) persisted — score=%.1f",
            site_id,
            summary.compliance_score,
        )
    except Exception as exc:
        _logger.warning(
            "recompute_site_full site=%d: étape 2 (RegAssessment) failed (%s) — skipping",
            site_id,
            exc,
        )

    # ── Étape 3 : score unifié A.2 → Site.compliance_score_composite ─────────
    try:
        from services.compliance_score_service import sync_site_unified_score

        result = sync_site_unified_score(db, site_id)
        _logger.info(
            "recompute_site_full site=%d: étape 3 (score unifié) synced — %.1f (%s)",
            site_id,
            result.score,
            result.confidence,
        )
    except Exception as exc:
        _logger.warning(
            "recompute_site_full site=%d: étape 3 (score unifié) failed (%s) — skipping",
            site_id,
            exc,
        )

    return snapshot
