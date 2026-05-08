"""
PROMEOS — Cascade BACS service (Phase D-4 Tier 2 — ADR-D-04 active).

Service cardinal cascade `Σ Batiment.cvc_power_kw → Site.bacs_puissance_cvc_totale_kw`
avec recalcul automatique de `Site.bacs_assujetti` selon seuil BACS_THRESHOLD_KW_EXISTING.

Pattern Pilier 3 ADR-016 (cascade vivante) reproduit Phase D-4 Tier 2.

Référence : docs/adr/ADR-D-04-bacs-puissance-cvc-cascade.md.
Audit cardinal : docs/audits/AUDIT_ECARTS_MATRICE_V1_2026_05_07.md §3 P0-MATV1-005.

Usage :
    from services.cascade_bacs_service import recompute_site_bacs_aggregate

    recompute_site_bacs_aggregate(db, site_id)

À appeler post-create/update/delete d'un Batiment.cvc_power_kw.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from doctrine.constants import BACS_THRESHOLD_KW_EXISTING
from models.batiment import Batiment
from models.site import Site


def compute_site_bacs_aggregate(db: Session, site_id: int) -> dict:
    """Calcule Σ(Batiment.cvc_power_kw) actifs pour un site donné.

    Returns:
        dict avec :
        - puissance_cvc_totale_kw (float ou 0.0) : somme des cvc_power_kw non-NULL
        - bacs_assujetti (bool) : True si Σ ≥ BACS_THRESHOLD_KW_EXISTING (70 kW)
        - nb_batiments (int) : nombre de bâtiments actifs avec cvc_power_kw renseigné
        - threshold_kw (int) : seuil cardinal Décret BACS 2025-1343
    """
    result = (
        db.query(
            func.coalesce(func.sum(Batiment.cvc_power_kw), 0.0).label("total_kw"),
            func.count(Batiment.id).label("nb_batiments"),
        )
        .filter(
            Batiment.site_id == site_id,
            Batiment.deleted_at.is_(None),
            Batiment.cvc_power_kw.isnot(None),
        )
        .first()
    )

    total_kw = float(result.total_kw) if result and result.total_kw else 0.0
    nb_batiments = int(result.nb_batiments) if result else 0

    return {
        "puissance_cvc_totale_kw": total_kw,
        "bacs_assujetti": total_kw >= BACS_THRESHOLD_KW_EXISTING,
        "nb_batiments": nb_batiments,
        "threshold_kw": BACS_THRESHOLD_KW_EXISTING,
    }


def recompute_site_bacs_aggregate(db: Session, site_id: int, *, commit: bool = False) -> Optional[dict]:
    """Recalcule + persiste Site.bacs_puissance_cvc_totale_kw + bacs_assujetti.

    Cardinal Phase D-4 Tier 2 : cascade active ADR-D-04.

    Args:
        db: SQLAlchemy session.
        site_id: Site cible.
        commit: si True, commit après update. Sinon flush only (caller doit commit).

    Returns:
        dict aggregate (cf compute_site_bacs_aggregate) ou None si site introuvable.
    """
    site = db.query(Site).filter(Site.id == site_id, Site.deleted_at.is_(None)).first()
    if site is None:
        return None

    aggregate = compute_site_bacs_aggregate(db, site_id)
    site.bacs_puissance_cvc_totale_kw = aggregate["puissance_cvc_totale_kw"]
    site.bacs_assujetti = aggregate["bacs_assujetti"]
    db.flush()

    if commit:
        db.commit()

    return aggregate
