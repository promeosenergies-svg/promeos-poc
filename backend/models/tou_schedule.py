"""
PROMEOS - TOU Schedule (Grille Tarifaire HP/HC)
Time-of-Use schedule with effective date versioning.
Supports HP/HC windows per day-type, with source tracking (manual, TURPE, Enedis).

Phase 2 TURPE 7 (nov 2026+): supports seasonal HC (été/hiver différents).
  - windows_json: HC for saison haute (hiver) — default / legacy
  - windows_ete_json: HC for saison basse (été) — only if is_seasonal=True
  - Saison haute: novembre à mars
  - Saison basse: avril à octobre

Règles CRE (délibération TURPE 7 + N°2026-02):
  - Été: HC favorisées 02h-06h et 11h-17h, interdites 07h-10h et 18h-23h
  - Hiver: HC interdites 07h-11h et 17h-21h
"""

from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin


class TOUSchedule(Base, TimestampMixin):
    """Versioned Time-of-Use tariff schedule for a meter or site.

    Supports seasonal HC (Phase 2 TURPE 7):
    - windows_json: saison haute (hiver, nov-mars) ou toute l'année si non saisonnalisé
    - windows_ete_json: saison basse (été, avr-oct) — uniquement si is_seasonal=True
    """

    __tablename__ = "tou_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Scope (meter-level or site-level)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True, index=True)

    # Identity
    name = Column(String(100), nullable=False, default="HC/HP Standard")

    # Versioning with effective dates
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)  # NULL = currently active
    is_active = Column(Boolean, nullable=False, default=True)

    # TOU windows — saison haute (hiver) ou année complète si non saisonnalisé
    # Format: [{"day_types": ["weekday"], "start": "06:00", "end": "22:00", "period": "HP", "price_eur_kwh": 0.18},
    #          {"day_types": ["weekday"], "start": "22:00", "end": "06:00", "period": "HC", "price_eur_kwh": 0.12},
    #          {"day_types": ["weekend", "holiday"], "start": "00:00", "end": "24:00", "period": "HC", "price_eur_kwh": 0.12}]
    windows_json = Column(Text, nullable=False)

    # ── Phase 2 TURPE 7: HC saisonnalisées ──
    is_seasonal = Column(Boolean, nullable=False, default=False, comment="True si HC été ≠ hiver")
    # TOU windows — saison basse (été, avr-oct), null si non saisonnalisé
    windows_ete_json = Column(Text, nullable=True, comment="HC été (saison basse) — JSON array")

    # Source tracking
    source = Column(String(50), nullable=True, default="manual")  # manual, turpe, enedis_sge, grdf, reprog_hc
    source_ref = Column(String(200), nullable=True)  # reference doc/API

    # Pricing summary (denormalized for quick display)
    price_hp_eur_kwh = Column(Float, nullable=True)
    price_hc_eur_kwh = Column(Float, nullable=True)
    # Phase 2: prix saisonnalisés
    price_hph_eur_kwh = Column(Float, nullable=True, comment="HP hiver")
    price_hch_eur_kwh = Column(Float, nullable=True, comment="HC hiver")
    price_hpb_eur_kwh = Column(Float, nullable=True, comment="HP été")
    price_hcb_eur_kwh = Column(Float, nullable=True, comment="HC été")

    # Relationships
    meter = relationship("Meter")
    site = relationship("Site")

    def __repr__(self):
        return f"<TOUSchedule(id={self.id}, name='{self.name}', seasonal={self.is_seasonal}, effective={self.effective_from})>"
