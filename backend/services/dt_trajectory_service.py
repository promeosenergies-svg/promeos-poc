"""
PROMEOS V110 — Calcul dynamique de la trajectoire Décret Tertiaire.

SoT : operat_trajectory.validate_trajectory() (seul service avec correction DJU).
Ce module DELEGUE a operat_trajectory quand une EFA existe pour le site.
Fallback sur calcul simplifie (sans DJU) si aucune EFA.

Jalons officiels (Décret n°2019-771, art. R131-39 CCH) :
  -40% en 2030 / -50% en 2040 / -60% en 2050
  Il n'existe PAS de jalon 2026 dans le texte réglementaire.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from models import TertiaireEfa

logger = logging.getLogger("promeos.dt_trajectory")

# Objectifs réglementaires — Décret n°2019-771, art. R131-39 CCH
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
    is_dju_applied: bool = False  # True si normalisation DJU appliquee
    source_service: str = "dt_trajectory_service"  # service ayant produit le calcul
    message: Optional[str] = None


def compute_site_trajectory(db: Session, site_id: int) -> TrajectoryResult:
    """
    Calcule la trajectoire DT dynamique pour un site.

    Strategie :
    1. Si le site a une EFA → DELEGUE a operat_trajectory.validate_trajectory() (SoT avec DJU)
    2. Sinon → fallback simplifie (sans DJU) via ConsumptionTarget / Site.conso_kwh_an
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

    # Priorite 1 : delegation a operat_trajectory si EFA presente
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.site_id == site_id, not_deleted(TertiaireEfa)).first()
    if efa:
        return _compute_via_operat_trajectory(db, site_id, efa)

    # Priorite 2 : fallback simplifie (pas d'EFA → pas de DJU possible)
    return _compute_fallback(db, site_id, site)


def _compute_via_operat_trajectory(db: Session, site_id: int, efa: "TertiaireEfa") -> TrajectoryResult:
    """Delegue a operat_trajectory.validate_trajectory() — SoT avec DJU."""
    import datetime
    from services.operat_trajectory import validate_trajectory

    try:
        observation_year = datetime.date.today().year
        result = validate_trajectory(db, efa.id, observation_year)

        baseline = result.get("baseline") or {}
        current = result.get("current") or {}
        baseline_kwh = baseline.get("kwh")
        current_kwh = current.get("kwh")

        # Calculer reduction_pct depuis les donnees operat_trajectory
        reduction_pct = None
        if baseline_kwh and baseline_kwh > 0 and current_kwh is not None:
            # Utiliser la conso normalisee si disponible
            effective_kwh = current.get("normalized_kwh") or current_kwh
            reduction_pct = round((1 - effective_kwh / baseline_kwh) * 100, 1)

        avancement_2030 = None
        avancement_2040 = None
        if reduction_pct is not None:
            avancement_2030 = round(min(100, max(0, reduction_pct / OBJECTIF_2030_PCT * 100)), 1)
            avancement_2040 = round(min(100, max(0, reduction_pct / OBJECTIF_2040_PCT * 100)), 1)

        is_normalized = result.get("is_normalized", False)

        return TrajectoryResult(
            site_id=site_id,
            conso_reference_kwh=round(baseline_kwh, 0) if baseline_kwh else None,
            conso_actuelle_kwh=round(current_kwh, 0) if current_kwh else None,
            reduction_pct=reduction_pct,
            avancement_2030=avancement_2030,
            avancement_2040=avancement_2040,
            source_reference="efa_declaration",
            source_actuelle=current.get("source") or "unknown",
            confidence="high" if baseline.get("reliability") in ("high", "medium") else "medium",
            is_dju_applied=is_normalized,
            source_service="operat_trajectory",
        )
    except Exception as e:
        logger.warning("operat_trajectory failed for site %d (efa %d): %s", site_id, efa.id, e)
        return TrajectoryResult(
            site_id=site_id,
            conso_reference_kwh=None,
            conso_actuelle_kwh=None,
            reduction_pct=None,
            avancement_2030=None,
            avancement_2040=None,
            source_reference="efa_declaration",
            source_actuelle="none",
            confidence="low",
            source_service="operat_trajectory",
            message=f"Erreur operat_trajectory: {e}",
        )


def _compute_fallback(db: Session, site_id: int, site) -> TrajectoryResult:
    """Fallback simplifie quand aucune EFA n'existe (pas de DJU possible)."""
    from models import ConsumptionTarget

    # Conso de reference : ConsumptionTarget la plus ancienne
    conso_ref = None
    source_ref = "none"
    oldest_target = (
        db.query(ConsumptionTarget)
        .filter(ConsumptionTarget.site_id == site_id)
        .order_by(ConsumptionTarget.year.asc())
        .first()
    )
    if oldest_target and oldest_target.target_kwh and oldest_target.target_kwh > 0:
        conso_ref = oldest_target.target_kwh
        source_ref = "consumption_target"

    # Conso actuelle
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

    if conso_actuelle is None:
        annual = getattr(site, "annual_kwh_total", None) or getattr(site, "conso_kwh_an", None)
        if annual and annual > 0:
            conso_actuelle = annual
            source_act = "site_static"

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
            message="Consommation de reference non disponible — trajectoire incalculable",
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

    return TrajectoryResult(
        site_id=site_id,
        conso_reference_kwh=round(conso_ref, 0),
        conso_actuelle_kwh=round(conso_actuelle, 0),
        reduction_pct=reduction_pct,
        avancement_2030=avancement_2030,
        avancement_2040=avancement_2040,
        source_reference=source_ref,
        source_actuelle=source_act,
        confidence="medium",
    )


def update_site_avancement(db: Session, site_id: int) -> Optional[float]:
    """
    Recalcule et persiste avancement_decret_pct sur le Site.
    Retourne la nouvelle valeur ou None si incalculable.
    Ne persiste pas si la trajectoire retourne 0 avec une confiance basse
    (evite d'écraser l'avancement issu des obligations).
    """
    from models import Site

    result = compute_site_trajectory(db, site_id)
    if result.avancement_2030 is not None and result.avancement_2030 > 0:
        site = db.query(Site).filter(Site.id == site_id).first()
        if site:
            site.avancement_decret_pct = result.avancement_2030
            db.flush()
            return result.avancement_2030
    return None
