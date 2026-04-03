"""
PROMEOS — Patrimoine ↔ Conformite Sync Service.

Assure la coherence entre patrimoine (sites, batiments) et conformite (OPERAT, BACS).
- Cascade soft-delete site → EFA + BACS
- Propagation surface
- Recalcul BACS auto apres modif CVC
- Detection orphelins
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict

from sqlalchemy.orm import Session

from models import TertiaireEfa, TertiaireEfaConsumption, Site, Batiment, not_deleted
from models.bacs_models import BacsAsset, BacsCvcSystem
from models.tertiaire import TertiaireEfaBuilding

logger = logging.getLogger("promeos.sync")


# ── A. Cascade soft-delete ─────────────────────────────────────────────


def cascade_site_archive(db: Session, site_id: int, actor: str = "system") -> dict:
    """Cascade l'archivage d'un site vers les EFA et BacsAssets lies."""
    archived = {"efa": 0, "bacs": 0}

    # EFA liees au site
    efas = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.site_id == site_id,
            TertiaireEfa.deleted_at.is_(None),
        )
        .all()
    )
    for efa in efas:
        efa.soft_delete(by=actor, reason=f"Cascade archive site {site_id}")
        archived["efa"] += 1

    # BacsAssets lies au site
    assets = (
        db.query(BacsAsset)
        .filter(
            BacsAsset.site_id == site_id,
            BacsAsset.deleted_at.is_(None),
        )
        .all()
    )
    for asset in assets:
        asset.soft_delete(by=actor, reason=f"Cascade archive site {site_id}")
        archived["bacs"] += 1

    db.flush()
    logger.info("sync: cascade archive site %d → %d EFA, %d BACS", site_id, archived["efa"], archived["bacs"])
    return archived


# ── B. Propagation surface ─────────────────────────────────────────────


def flag_efa_desync_on_surface_change(db: Session, site_id: int) -> int:
    """Flag les EFA liees a un site dont la surface a change."""
    efas = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.site_id == site_id,
            TertiaireEfa.deleted_at.is_(None),
        )
        .all()
    )

    flagged = 0
    for efa in efas:
        # Comparer surface EfaBuilding vs batiment reel
        buildings = (
            db.query(TertiaireEfaBuilding)
            .filter(
                TertiaireEfaBuilding.efa_id == efa.id,
            )
            .all()
        )
        for eb in buildings:
            if eb.building_id:
                bat = db.query(Batiment).filter(Batiment.id == eb.building_id).first()
                if bat and bat.surface_m2 and eb.surface_m2 != bat.surface_m2:
                    eb.surface_m2 = bat.surface_m2  # Synchro
                    flagged += 1

    if flagged:
        db.flush()
        logger.info("sync: surface synchro site %d → %d EfaBuilding(s) mise(s) a jour", site_id, flagged)
    return flagged


# ── C. Recalcul BACS auto ─────────────────────────────────────────────


def auto_recompute_bacs(db: Session, site_id: int) -> bool:
    """Recalcule l'evaluation BACS apres modification de systeme CVC."""
    asset = (
        db.query(BacsAsset)
        .filter(
            BacsAsset.site_id == site_id,
            not_deleted(BacsAsset),
        )
        .first()
    )
    if not asset:
        return False

    try:
        from services.bacs_engine import evaluate_bacs

        evaluate_bacs(db, site_id)
        db.flush()
        logger.info("sync: BACS auto-recompute site %d", site_id)
        return True
    except Exception as e:
        logger.warning("sync: BACS recompute failed site %d: %s", site_id, e)
        return False


# ── D. Detection orphelins ─────────────────────────────────────────────


def detect_orphans(db: Session) -> Dict[str, List[Dict]]:
    """Detecte les entites conformite orphelines (site archive ou supprime)."""
    orphans = {"efa_orphans": [], "bacs_orphans": []}

    # EFA avec site_id pointant vers site archive/supprime
    efas = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.site_id.isnot(None),
            TertiaireEfa.deleted_at.is_(None),
        )
        .all()
    )
    for efa in efas:
        site = db.query(Site).filter(Site.id == efa.site_id, not_deleted(Site)).first()
        if not site:
            orphans["efa_orphans"].append(
                {
                    "efa_id": efa.id,
                    "efa_nom": efa.nom,
                    "site_id": efa.site_id,
                    "reason": "Site archive ou supprime",
                }
            )

    # BacsAsset avec site_id pointant vers site archive/supprime
    assets = (
        db.query(BacsAsset)
        .filter(
            BacsAsset.deleted_at.is_(None),
        )
        .all()
    )
    for asset in assets:
        site = db.query(Site).filter(Site.id == asset.site_id, not_deleted(Site)).first()
        if not site:
            orphans["bacs_orphans"].append(
                {
                    "asset_id": asset.id,
                    "site_id": asset.site_id,
                    "reason": "Site archive ou supprime",
                }
            )

    total = len(orphans["efa_orphans"]) + len(orphans["bacs_orphans"])
    if total:
        logger.warning("sync: %d orphelin(s) detecte(s)", total)

    return orphans


# ── E. Reevaluation eligibilite si usage/type change ───────────────────


def reevaluate_on_usage_change(db: Session, site_id: int) -> Dict:
    """Marque la conformite comme desynchronisee si le type/usage du site a change."""
    result = {"efa_flagged": 0, "bacs_flagged": 0}

    # Flag EFA liees
    efas = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.site_id == site_id,
            TertiaireEfa.deleted_at.is_(None),
        )
        .all()
    )
    for efa in efas:
        if efa.trajectory_status and efa.trajectory_status not in ("not_evaluable",):
            efa.trajectory_status = "review_required"
            result["efa_flagged"] += 1

    # Flag BacsAsset
    assets = (
        db.query(BacsAsset)
        .filter(
            BacsAsset.site_id == site_id,
            not_deleted(BacsAsset),
        )
        .all()
    )
    for asset in assets:
        if asset.bacs_scope_status and asset.bacs_scope_status not in ("not_applicable", "potentially_in_scope"):
            asset.bacs_scope_status = "review_required"
            asset.bacs_scope_reason = "Usage/type site modifie — reevaluation requise"
            result["bacs_flagged"] += 1

    if result["efa_flagged"] or result["bacs_flagged"]:
        db.flush()
        logger.info(
            "sync: reevaluation usage site %d → %d EFA, %d BACS flagges",
            site_id,
            result["efa_flagged"],
            result["bacs_flagged"],
        )

    return result


# ── F. Job de coherence periodique ─────────────────────────────────────


def run_coherence_check(db: Session) -> Dict:
    """Verification periodique de la coherence patrimoine ↔ conformite.

    Detecte :
    - orphelins (EFA/BACS avec site archive)
    - desynchronisations surface
    - BACS sans recalcul recent

    Retourne un resume exploitable.
    """
    from datetime import timedelta

    summary = {
        "orphans": detect_orphans(db),
        "surface_desyncs": [],
        "bacs_stale": [],
    }

    # Detecter desync surface
    efas = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.site_id.isnot(None),
            TertiaireEfa.deleted_at.is_(None),
        )
        .all()
    )

    for efa in efas:
        from models.tertiaire import TertiaireEfaBuilding

        buildings = db.query(TertiaireEfaBuilding).filter(TertiaireEfaBuilding.efa_id == efa.id).all()
        for eb in buildings:
            if eb.building_id:
                bat = db.query(Batiment).filter(Batiment.id == eb.building_id).first()
                if bat and bat.surface_m2 and eb.surface_m2 and abs(bat.surface_m2 - eb.surface_m2) > 1:
                    summary["surface_desyncs"].append(
                        {
                            "efa_id": efa.id,
                            "building_id": eb.building_id,
                            "efa_surface": eb.surface_m2,
                            "batiment_surface": bat.surface_m2,
                        }
                    )

    # Detecter BACS avec evaluation trop ancienne (> 30 jours)
    # Strip tzinfo for SQLite naive-datetime compatibility
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    from models.bacs_models import BacsAssessment

    assets = db.query(BacsAsset).filter(not_deleted(BacsAsset)).all()
    for asset in assets:
        last_assessment = (
            db.query(BacsAssessment)
            .filter(BacsAssessment.asset_id == asset.id)
            .order_by(BacsAssessment.assessed_at.desc())
            .first()
        )
        if not last_assessment or (last_assessment.assessed_at and last_assessment.assessed_at < cutoff):
            summary["bacs_stale"].append(
                {
                    "asset_id": asset.id,
                    "site_id": asset.site_id,
                    "last_assessed": last_assessment.assessed_at.isoformat()
                    if last_assessment and last_assessment.assessed_at
                    else None,
                }
            )

    total_issues = (
        len(summary["orphans"]["efa_orphans"])
        + len(summary["orphans"]["bacs_orphans"])
        + len(summary["surface_desyncs"])
        + len(summary["bacs_stale"])
    )
    summary["total_issues"] = total_issues
    summary["status"] = "clean" if total_issues == 0 else "issues_detected"

    if total_issues:
        logger.warning("coherence: %d issue(s) detectee(s)", total_issues)
    else:
        logger.info("coherence: patrimoine ↔ conformite OK")

    return summary
