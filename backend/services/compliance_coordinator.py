"""
PROMEOS — Coordinateur Conformité  ★ POINT D'ENTRÉE UNIQUE ★

Remplace les appels directs à recompute_site() dispersés dans l'application.
Garantit que les deux chemins de calcul conformité sont toujours mis à jour ensemble :

  1. compliance_engine.recompute_site()  → snapshots Site (statut_decret_tertiaire, statut_bacs, ...)
  2. regops.engine.evaluate_site()       → RegAssessment rows (score détaillé par framework)
  3. compliance_score_service.sync()     → Site.compliance_score_composite (score A.2 unifié)

USAGE :
  from services.compliance_coordinator import recompute_site_full
  recompute_site_full(db, site_id)   # remplace : recompute_site(db, site_id)
"""

import logging
from sqlalchemy.orm import Session

_logger = logging.getLogger(__name__)


def recompute_site_full(db: Session, site_id: int) -> dict:
    """Recompute complet d'un site — trois chemins synchronisés.

    Étapes :
    1. compliance_engine.recompute_site()
       → Site.statut_decret_tertiaire, statut_bacs, risque_financier_euro, avancement_decret_pct
    2. regops.engine.evaluate_site() + persist_assessment()
       → RegAssessment up-to-date (source pour compliance_score_service)
    3. compliance_score_service.sync_site_unified_score()
       → Site.compliance_score_composite, compliance_score_breakdown_json, compliance_score_confidence

    Chaque étape est indépendante : une erreur dans 2 ou 3 ne bloque pas les autres.
    Returns : snapshot dict de l'étape 1 (backward-compatible avec recompute_site).
    """
    # ── Étape 1 : snapshots legacy (obligations + evidences → statuts Site) ──
    from services.compliance_engine import recompute_site

    snapshot = recompute_site(db, site_id)
    _logger.info("recompute_site_full site=%d: étape 1 (legacy snapshot) done", site_id)

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
