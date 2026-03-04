"""
PROMEOS — Patrimoine Snapshot Service (V58)

Single Source of Truth (SoT) pour un site : surface, bâtiments, compteurs,
points de livraison, contrats. Zéro N+1, soft-delete strict.

Décision D1 — surface SoT :
  surface_sot_m2 = sum(batiment.surface_m2) si nb_batiments_actifs > 0
                   else site.surface_m2
                   else None
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from models import (
    Site,
    Batiment,
    Usage,
    Compteur,
    DeliveryPoint,
    EnergyContract,
)

# Tolérance SURFACE_MISMATCH (D1) — 5 % par défaut
SURFACE_MISMATCH_TOLERANCE = 0.05


def get_site_snapshot(site_id: int, org_id: int, db: Session) -> Optional[Dict[str, Any]]:
    """
    Retourne le snapshot canonique d'un site.
    Pré-condition : l'appelant a déjà vérifié l'appartenance du site à l'org
    (via _load_site_with_org_check ou équivalent).

    Zéro N+1 : toutes les collections sont chargées en une seule requête par table.
    Soft-delete strict : Batiment.deleted_at IS NULL, Compteur.deleted_at IS NULL.
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if site is None:
        return None

    # ── 1. Bâtiments (soft-delete : deleted_at IS NULL) ──────────────────────
    batiments: List[Batiment] = (
        db.query(Batiment).filter(Batiment.site_id == site_id, Batiment.deleted_at.is_(None)).all()
    )

    # ── 2. Usages (batch — pas de N+1) ───────────────────────────────────────
    bat_ids = [b.id for b in batiments]
    usages_by_bat: Dict[int, List[Usage]] = {}
    if bat_ids:
        usages = db.query(Usage).filter(Usage.batiment_id.in_(bat_ids)).all()
        for u in usages:
            usages_by_bat.setdefault(u.batiment_id, []).append(u)

    # ── 3. Compteurs (actif=True ET deleted_at IS NULL) ───────────────────────
    compteurs: List[Compteur] = (
        db.query(Compteur)
        .filter(
            Compteur.site_id == site_id,
            Compteur.actif.is_(True),
            Compteur.deleted_at.is_(None),
        )
        .all()
    )

    # ── 4. Points de livraison (deleted_at IS NULL) ───────────────────────────
    delivery_points: List[DeliveryPoint] = (
        db.query(DeliveryPoint).filter(DeliveryPoint.site_id == site_id, DeliveryPoint.deleted_at.is_(None)).all()
    )

    # ── 5. Contrats énergie ───────────────────────────────────────────────────
    contracts: List[EnergyContract] = db.query(EnergyContract).filter(EnergyContract.site_id == site_id).all()

    # ── Surface SoT (D1) ──────────────────────────────────────────────────────
    if batiments:
        surface_sot_m2 = sum(b.surface_m2 or 0.0 for b in batiments) or None
    else:
        surface_sot_m2 = site.surface_m2  # fallback (peut être None)

    # ── Sérialisation ─────────────────────────────────────────────────────────
    batiments_data = [
        {
            "id": b.id,
            "nom": b.nom,
            "surface_m2": b.surface_m2,
            "annee_construction": b.annee_construction,
            "cvc_power_kw": b.cvc_power_kw,
            "usages": [{"id": u.id, "type": u.type.value if u.type else None} for u in usages_by_bat.get(b.id, [])],
        }
        for b in batiments
    ]

    compteurs_data = [
        {
            "id": c.id,
            "type": c.type.value if c.type else None,
            "numero_serie": c.numero_serie,
            "delivery_point_id": c.delivery_point_id,
            "delivery_code": c.delivery_code,
            "energy_vector": c.energy_vector.value if c.energy_vector else None,
        }
        for c in compteurs
    ]

    dp_data = [
        {
            "id": dp.id,
            "code": dp.code,
            "energy_type": dp.energy_type.value if dp.energy_type else None,
            "status": dp.status.value if dp.status else None,
        }
        for dp in delivery_points
    ]

    contracts_data = [
        {
            "id": c.id,
            "energy_type": c.energy_type.value if c.energy_type else None,
            "supplier_name": c.supplier_name,
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "auto_renew": c.auto_renew,
        }
        for c in contracts
    ]

    return {
        "site_id": site.id,
        "nom": site.nom,
        "type": site.type.value if site.type else None,
        "actif": site.actif,
        # Surface
        "surface_site_m2": site.surface_m2,
        "surface_sot_m2": surface_sot_m2,
        "surface_tolerance_pct": SURFACE_MISMATCH_TOLERANCE,
        # Bâtiments
        "nb_batiments": len(batiments),
        "batiments": batiments_data,
        # Compteurs
        "nb_compteurs": len(compteurs),
        "compteurs": compteurs_data,
        # Points de livraison
        "nb_delivery_points": len(delivery_points),
        "delivery_points": dp_data,
        # Contrats
        "nb_contracts": len(contracts),
        "contracts": contracts_data,
        # Metadata
        "computed_at": datetime.now(timezone.utc).isoformat() + "Z",
    }
