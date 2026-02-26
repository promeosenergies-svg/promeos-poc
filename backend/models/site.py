"""
PROMEOS - Modèle Site
Coeur du domaine : site de consommation énergétique
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, Boolean, DateTime
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, SoftDeleteMixin
from .enums import TypeSite, StatutConformite, ParkingType, OperatStatus


class Site(Base, TimestampMixin, SoftDeleteMixin):
    """
    Site de consommation énergétique
    Exemples : Carrefour Paris 15e, Usine Renault Lyon, Bureau EDF Marseille
    """
    __tablename__ = "sites"

    # Identifiant
    id = Column(Integer, primary_key=True, index=True)

    # Informations générales
    nom = Column(String(200), nullable=False, index=True, comment="Nom du site")
    type = Column(Enum(TypeSite), nullable=False, comment="Type de site")

    # Adresse complète
    adresse = Column(String(300), comment="Adresse postale")
    code_postal = Column(String(10), index=True, comment="Code postal")
    ville = Column(String(100), index=True, comment="Ville")
    region = Column(String(100), comment="Région")

    # Caractéristiques physiques
    surface_m2 = Column(Float, comment="Surface en m²")
    nombre_employes = Column(Integer, comment="Nombre d'employés")

    # Géolocalisation (pour cartographie)
    latitude = Column(Float, comment="Latitude GPS")
    longitude = Column(Float, comment="Longitude GPS")

    # Status
    actif = Column(Boolean, default=True, comment="Site actif ou non")

    # Conformité réglementaire (snapshots calculés par compliance_engine)
    portefeuille_id = Column(Integer, ForeignKey("portefeuilles.id"), nullable=True, index=True)
    statut_decret_tertiaire = Column(Enum(StatutConformite), default=StatutConformite.A_RISQUE)
    avancement_decret_pct = Column(Float, default=0.0)  # % avancement (0-100)
    statut_bacs = Column(Enum(StatutConformite), default=StatutConformite.A_RISQUE)
    anomalie_facture = Column(Boolean, default=False)
    action_recommandee = Column(String, nullable=True)
    risque_financier_euro = Column(Float, default=0.0)  # de risque

    # RegOps business identifiers
    siret = Column(String(14), nullable=True, comment="SIRET du site")
    insee_code = Column(String(5), nullable=True, comment="Code INSEE commune")
    naf_code = Column(String(5), nullable=True, comment="Code NAF override")
    tertiaire_area_m2 = Column(Float, nullable=True, comment="Surface tertiaire assujettie (m2)")
    roof_area_m2 = Column(Float, nullable=True, comment="Surface toiture (m2)")
    parking_area_m2 = Column(Float, nullable=True, comment="Surface parking (m2)")
    parking_type = Column(Enum(ParkingType), nullable=True, comment="Type de parking")
    is_multi_occupied = Column(Boolean, default=False, comment="Site multi-occupant")
    operat_status = Column(Enum(OperatStatus), nullable=True, comment="Statut OPERAT")
    operat_last_submission_year = Column(Integer, nullable=True, comment="Derniere annee de declaration OPERAT")
    annual_kwh_total = Column(Float, nullable=True, comment="Consommation annuelle totale (kWh)")
    last_energy_update_at = Column(DateTime, nullable=True, comment="Derniere MAJ donnees energie")

    @property
    def conso_kwh_an(self):
        """Alias for annual_kwh_total — used by frontend dashboards."""
        return self.annual_kwh_total
    is_demo = Column(Boolean, default=False, comment="Donnees de demonstration")

    # Data lineage
    data_source = Column(String(20), nullable=True, comment="csv, manual, demo, api")
    data_source_ref = Column(String(200), nullable=True, comment="Batch ID or filename")
    imported_at = Column(DateTime, nullable=True, comment="Date d'import")
    imported_by = Column(Integer, nullable=True, comment="User ID de l'importateur")

    # Relations avec les autres tables
    compteurs = relationship(
        "Compteur",
        back_populates="site",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    alertes = relationship(
        "Alerte",
        back_populates="site",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    portefeuille = relationship("Portefeuille", back_populates="sites")
    batiments = relationship(
        "Batiment",
        back_populates="site",
        cascade="all, delete-orphan",
    )
    obligations = relationship(
        "Obligation",
        back_populates="site",
        cascade="all, delete-orphan",
    )

    # Delivery Points (PRM/PCE)
    delivery_points = relationship(
        "DeliveryPoint",
        back_populates="site",
        cascade="all, delete-orphan",
    )

    # Energy analytics
    meters = relationship(
        "Meter",
        back_populates="site",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Site {self.id}: {self.nom} ({self.type.value})>"
