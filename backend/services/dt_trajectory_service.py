"""
PROMEOS V110 — Calcul dynamique de la trajectoire Décret Tertiaire.

Formule :
  reduction_pct = (1 − conso_actuelle / conso_reference) × 100
  avancement_2030 = reduction_pct / 40 × 100  (objectif -40% en 2030)
  avancement_2040 = reduction_pct / 50 × 100  (objectif -50% en 2040)

Sources :
  - conso_reference : TertiaireEfaConsumption (is_reference=True) ou Site.conso_kwh_an seedée
  - conso_actuelle : consumption_unified_service (12 derniers mois mesurés)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("promeos.dt_trajectory")

# Objectifs réglementaires
OBJECTIF_2030_PCT = 40.0  # -40% vs référence
OBJECTIF_2040_PCT = 50.0  # -50% vs référence
OBJECTIF_2050_PCT = 60.0  # -60% vs référence


@dataclass
class TrajectoryResult:
    """Résultat du calcul trajectoire DT pour un site."""

    site_id: int
    conso_reference_kwh: Optional[float]
    conso_actuelle_kwh: Optional[float]
    reduction_pct: Optional[float]  # Réduction observée vs référence
    avancement_2030: Optional[float]  # Progression vers objectif -40%
    avancement_2040: Optional[float]  # Progression vers objectif -50%
    source_reference: str  # "efa_declaration" | "site_static" | "none"
    source_actuelle: str  # "metered" | "estimated" | "none"
    confidence: str  # "high" | "medium" | "low"
    message: Optional[str] = None


def compute_site_trajectory(db: Session, site_id: int) -> TrajectoryResult:
    """
    Calcule la trajectoire DT dynamique pour un site.

    Priorité conso référence :
    1. TertiaireEfaConsumption avec is_reference=True
    2. ConsumptionTarget annuelle la plus ancienne
    3. Aucune → avancement incalculable

    Priorité conso actuelle :
    1. consumption_unified_service (12 mois mesurés)
    2. Site.conso_kwh_an (statique)
    3. Aucune → avancement incalculable
    """
    from models import Site, TertiaireEfa, TertiaireEfaConsumption, not_deleted

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return TrajectoryResult(
            site_id=site_id,
            conso_reference_kwh=None,
            conso_actuelle_kwh=None,
            reduction_pct=None,
            avancement_2030=None,
            avancement_2040=None,
            source_reference="none",
            source_actuelle="none",
            confidence="low",
            message="Site introuvable",
        )

    # 1. Chercher la conso de référence
    conso_ref = None
    source_ref = "none"

    # Priorité 1 : EFA déclaration de référence
    efas = db.query(TertiaireEfa).filter(TertiaireEfa.site_id == site_id, not_deleted(TertiaireEfa)).all()
    for efa in efas:
        ref_conso = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == efa.id, TertiaireEfaConsumption.is_reference == True)
            .first()
        )
        if ref_conso and ref_conso.kwh_total and ref_conso.kwh_total > 0:
            conso_ref = ref_conso.kwh_total
            source_ref = "efa_declaration"
            break

    # Priorité 2 : consommation historique la plus ancienne (proxy de référence)
    if conso_ref is None:
        from models import ConsumptionTarget

        oldest_target = (
            db.query(ConsumptionTarget)
            .filter(ConsumptionTarget.site_id == site_id)
            .order_by(ConsumptionTarget.year.asc())
            .first()
        )
        if oldest_target and oldest_target.target_kwh and oldest_target.target_kwh > 0:
            conso_ref = oldest_target.target_kwh
            source_ref = "consumption_target"

    # 2. Conso actuelle (12 derniers mois mesurés)
    conso_actuelle = None
    source_act = "none"

    try:
        from services.consumption_unified_service import get_portfolio_consumption
        from datetime import date, timedelta

        today = date.today()
        result = get_portfolio_consumption(db, site.org_id or 1, today - timedelta(days=365), today)
        for s in result.get("sites", []):
            if s.get("site_id") == site_id and s.get("value_kwh", 0) > 0:
                conso_actuelle = s["value_kwh"]
                source_act = s.get("source_used", "metered")
                break
    except Exception as e:
        logger.warning("consumption_unified_service failed for site %d: %s", site_id, e)

    # Fallback : Site.conso_kwh_an
    if conso_actuelle is None:
        annual = getattr(site, "annual_kwh_total", None) or getattr(site, "conso_kwh_an", None)
        if annual and annual > 0:
            conso_actuelle = annual
            source_act = "site_static"

    # 3. Calcul trajectoire
    if conso_ref is None or conso_ref <= 0:
        return TrajectoryResult(
            site_id=site_id,
            conso_reference_kwh=conso_ref,
            conso_actuelle_kwh=conso_actuelle,
            reduction_pct=None,
            avancement_2030=None,
            avancement_2040=None,
            source_reference=source_ref,
            source_actuelle=source_act,
            confidence="low",
            message="Consommation de référence non disponible — trajectoire incalculable",
        )

    if conso_actuelle is None or conso_actuelle <= 0:
        return TrajectoryResult(
            site_id=site_id,
            conso_reference_kwh=conso_ref,
            conso_actuelle_kwh=conso_actuelle,
            reduction_pct=None,
            avancement_2030=None,
            avancement_2040=None,
            source_reference=source_ref,
            source_actuelle=source_act,
            confidence="low",
            message="Consommation actuelle non disponible — trajectoire incalculable",
        )

    reduction_pct = round((1 - conso_actuelle / conso_ref) * 100, 1)
    avancement_2030 = round(min(100, max(0, reduction_pct / OBJECTIF_2030_PCT * 100)), 1)
    avancement_2040 = round(min(100, max(0, reduction_pct / OBJECTIF_2040_PCT * 100)), 1)

    confidence = "high" if source_ref == "efa_declaration" and source_act == "metered" else "medium"

    return TrajectoryResult(
        site_id=site_id,
        conso_reference_kwh=round(conso_ref, 0),
        conso_actuelle_kwh=round(conso_actuelle, 0),
        reduction_pct=reduction_pct,
        avancement_2030=avancement_2030,
        avancement_2040=avancement_2040,
        source_reference=source_ref,
        source_actuelle=source_act,
        confidence=confidence,
    )


def update_site_avancement(db: Session, site_id: int) -> Optional[float]:
    """
    Recalcule et persiste avancement_decret_pct sur le Site.
    Retourne la nouvelle valeur ou None si incalculable.
    """
    from models import Site

    result = compute_site_trajectory(db, site_id)
    if result.avancement_2030 is not None:
        site = db.query(Site).filter(Site.id == site_id).first()
        if site:
            site.avancement_decret_pct = result.avancement_2030
            db.flush()
            return result.avancement_2030
    return None
