"""
Modèles de stockage pour les datasets Enedis Open Data.

Datasets prioritaires :
- conso-sup36-region : agrégats >36 kVA par NAF × puissance × profil × région (30 min)
- conso-inf36-region : agrégats ≤36 kVA par profil × puissance × région (30 min)
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from models.base import Base


class EnedisConsoSup36(Base):
    """Agrégats consommation >36 kVA — maille région, pas 30 min."""

    __tablename__ = "enedis_opendata_conso_sup36"
    __table_args__ = (
        UniqueConstraint(
            "horodate", "code_region", "profil", "plage_puissance", "secteur_activite", name="uq_sup36_natural_key"
        ),
        Index("ix_sup36_sector_ts", "secteur_activite", "horodate"),
        Index("ix_sup36_profil_ts", "profil", "horodate"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    horodate = Column(DateTime, nullable=False, index=True)
    region = Column(String(100), nullable=True)
    code_region = Column(String(10), nullable=True)
    profil = Column(String(20), nullable=False)
    plage_puissance = Column(String(50), nullable=True)
    secteur_activite = Column(String(50), nullable=True)
    nb_points_soutirage = Column(Integer, nullable=True)
    total_energie_wh = Column(Float, nullable=True)
    courbe_moyenne_wh = Column(Float, nullable=True)
    indice_representativite = Column(Float, nullable=True)
    import_batch = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class EnedisConsoInf36(Base):
    """Agrégats consommation ≤36 kVA — maille région, pas 30 min."""

    __tablename__ = "enedis_opendata_conso_inf36"
    __table_args__ = (
        UniqueConstraint("horodate", "code_region", "profil", "plage_puissance", name="uq_inf36_natural_key"),
        Index("ix_inf36_profil_ts", "profil", "horodate"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    horodate = Column(DateTime, nullable=False, index=True)
    region = Column(String(100), nullable=True)
    code_region = Column(String(10), nullable=True)
    profil = Column(String(20), nullable=False)
    plage_puissance = Column(String(50), nullable=True)
    nb_points_soutirage = Column(Integer, nullable=True)
    total_energie_wh = Column(Float, nullable=True)
    courbe_moyenne_wh = Column(Float, nullable=True)
    indice_representativite = Column(Float, nullable=True)
    import_batch = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
