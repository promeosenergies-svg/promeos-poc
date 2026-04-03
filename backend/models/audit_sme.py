"""
Modele Audit Energetique / SME.

Source reglementaire :
- Loi n 2025-391 du 30 avril 2025 (transposition directive EU 2023/1791)
- Code de l'energie art. L.233-1 et suivants
- Seuils : >= 23.6 GWh/an -> SME ISO 50001 | >= 2.75 GWh/an -> Audit 4 ans | < 2.75 GWh -> aucun
- Deadline premier audit pour entreprises existantes : 11 octobre 2026
- Consommation = energie finale moyenne 3 ans, tous vecteurs, incl. ENR autoconsommee
"""

from sqlalchemy import Column, Integer, Float, String, Boolean, Date, ForeignKey
from datetime import datetime, timezone

from .base import Base, TimestampMixin, SoftDeleteMixin


class AuditEnergetique(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "audit_energetique"

    id = Column(Integer, primary_key=True, index=True)

    # Perimetre - organisation (entite juridique ou groupe)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=True, index=True)
    organisation_libelle = Column(String(255), nullable=True)

    # Consommation annuelle finale (moyenne 3 ans, tous vecteurs)
    annee_ref_debut = Column(Integer, nullable=True)
    annee_ref_fin = Column(Integer, nullable=True)
    conso_annuelle_moy_kwh = Column(Float, nullable=True)
    conso_annuelle_moy_gwh = Column(Float, nullable=True)
    detail_vecteurs = Column(String, nullable=True)  # JSON: {elec_kwh, gaz_kwh, fioul_kwh, ...}

    # Obligation determinee
    # "SME_ISO50001" | "AUDIT_4ANS" | "AUCUNE" | "NON_DETERMINE"
    obligation = Column(String(30), nullable=False, default="NON_DETERMINE")

    # Statut de conformite
    # "CONFORME" | "A_REALISER" | "EN_COURS" | "EN_RETARD" | "NON_CONCERNE"
    statut = Column(String(20), nullable=False, default="NON_DETERMINE")

    # Dates cles
    date_premier_audit_limite = Column(Date, nullable=True)
    date_dernier_audit = Column(Date, nullable=True)
    date_prochain_audit = Column(Date, nullable=True)
    date_transmission_admin = Column(Date, nullable=True)

    # Conformite audit
    auditeur_identifie = Column(Boolean, default=False)
    audit_realise = Column(Boolean, default=False)
    plan_action_publie = Column(Boolean, default=False)
    transmission_realisee = Column(Boolean, default=False)

    # SME specifique
    sme_certifie_iso50001 = Column(Boolean, default=False)
    date_certification_sme = Column(Date, nullable=True)
    organisme_certificateur = Column(String(100), nullable=True)

    # Scoring (contribution au score RegOps)
    score_audit_sme = Column(Float, nullable=True)  # 0.0 a 1.0

    # Tracabilite
    source = Column(String(20), default="manual")  # manual | computed
