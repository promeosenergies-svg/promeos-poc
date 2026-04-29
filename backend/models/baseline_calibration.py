"""PROMEOS — Modèle BaselineCalibration (Décision D §0.D)

Historisation des calibrations de baseline par site et méthode.
Jamais d'UPDATE — seulement INSERT pour auditabilité complète.

Réf : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §0.D décisions B+D + §2.B Phase 1.2
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String

from .base import Base


class BaselineMethod(str, PyEnum):
    """3 méthodes canoniques de calcul baseline (décision B §0.D).

    A_HISTORICAL   : moyenne 4 mêmes jours de semaine sur 12 semaines glissantes
    B_DJU_ADJUSTED : régression linéaire E = a×DJU + b sur 12 mois glissants
    C_REGULATORY_DT: conso année référence DT fixée (ref_year=2020 pour HELIOS)
    """

    A_HISTORICAL = "a_historical"
    B_DJU_ADJUSTED = "b_dju_adjusted"
    C_REGULATORY_DT = "c_regulatory_dt"


class BaselineCalibration(Base):
    """Calibration d'une baseline pour un site donné (décision D §0.D).

    Historisation : on conserve toutes les calibrations (jamais d'UPDATE,
    seulement INSERT). Permet auditabilité + lecture rétrospective de la
    confiance historique.
    """

    __tablename__ = "baseline_calibrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    method = Column(
        Enum(BaselineMethod, values_callable=lambda e: [v.value for v in e]),
        nullable=False,
    )
    calibration_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    coefficient_a = Column(Float, nullable=True)  # méthode B uniquement
    coefficient_b = Column(Float, nullable=True)  # méthode B uniquement
    ref_year = Column(Integer, nullable=True)  # méthode C uniquement
    r_squared = Column(Float, nullable=True)  # méthode B uniquement
    data_points = Column(Integer, nullable=False)
    confidence = Column(String(20), nullable=False)  # 'haute' | 'moyenne' | 'faible'

    def __repr__(self) -> str:
        return (
            f"<BaselineCalibration id={self.id} site={self.site_id} method={self.method} confidence={self.confidence}>"
        )
