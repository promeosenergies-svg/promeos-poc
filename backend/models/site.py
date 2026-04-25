"""
PROMEOS - Modèle Site
Coeur du domaine : site de consommation énergétique
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String
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
    geocoding_source = Column(String(50), nullable=True, comment="Source: ban, manual, seed")
    geocoding_score = Column(Float, nullable=True, comment="Score confiance géocodage 0-1")
    geocoded_at = Column(DateTime, nullable=True, comment="Date du dernier géocodage")
    geocoding_status = Column(String(20), nullable=True, comment="ok, partial, not_found, error")

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

    # Score conformité unifié A.2 (snapshot, mis à jour par compliance_score_service)
    compliance_score_composite = Column(
        Float, nullable=True, comment="Score 0-100 unifié (DT 45% + BACS 30% + APER 25%)"
    )
    compliance_score_breakdown_json = Column(String, nullable=True, comment="Détail par framework JSON")
    compliance_score_confidence = Column(String(10), nullable=True, comment="high/medium/low")

    # RegOps business identifiers
    siret = Column(String(14), nullable=True, comment="SIRET du site")
    insee_code = Column(String(5), nullable=True, comment="Code INSEE commune")
    naf_code = Column(String(10), nullable=True, comment="Code NAF override (ex: 47.11F)")
    tertiaire_area_m2 = Column(Float, nullable=True, comment="Surface tertiaire assujettie (m2)")
    roof_area_m2 = Column(Float, nullable=True, comment="Surface toiture (m2)")
    parking_area_m2 = Column(Float, nullable=True, comment="Surface parking (m2)")
    parking_type = Column(Enum(ParkingType), nullable=True, comment="Type de parking")
    is_multi_occupied = Column(Boolean, default=False, comment="Site multi-occupant")
    operat_status = Column(Enum(OperatStatus), nullable=True, comment="Statut OPERAT")
    operat_last_submission_year = Column(Integer, nullable=True, comment="Derniere annee de declaration OPERAT")
    annual_kwh_total = Column(Float, nullable=True, comment="Consommation annuelle totale (kWh)")
    last_energy_update_at = Column(DateTime, nullable=True, comment="Derniere MAJ donnees energie")

    # Pilotage des usages (Flex Ready® NF EN IEC 62746-4, Baromètre Flex 2026)
    archetype_code = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Archétype Baromètre Flex 2026 (BUREAU_STANDARD, COMMERCE_ALIMENTAIRE, LOGISTIQUE_FRIGO...)",
    )
    puissance_pilotable_kw = Column(
        Float,
        nullable=True,
        comment="Puissance pilotable/décalable estimée (kW), pour scoring portefeuille",
    )

    # CBAM — exposition industrielle hors UE (Règlement UE 2023/956).
    # JSON : {scope: tonnes_annuelles} pour chaque scope CBAM (acier, ciment,
    # aluminium, engrais, hydrogène, électricité). Null/vide = non applicable.
    cbam_imports_tonnes = Column(
        JSON,
        nullable=True,
        comment="Volumes annuels d'importation hors UE par scope CBAM (tonnes/an)",
    )
    # Optionnel : intensités carbone site-specific vérifiées (override défauts CE).
    cbam_intensities_tco2_per_t = Column(
        JSON,
        nullable=True,
        comment="Intensités carbone vérifiées par scope (tCO2/t) — surcharge défauts CE",
    )

    @property
    def conso_kwh_an(self):
        """Alias for annual_kwh_total — used by frontend dashboards."""
        return self.annual_kwh_total

    @property
    def portefeuille_nom(self):
        """Nom du portefeuille parent — used by breadcrumbs and Site360."""
        return self.portefeuille.nom if self.portefeuille else None

    is_demo = Column(Boolean, default=False, comment="Donnees de demonstration")

    # Data lineage
    data_source = Column(String(20), nullable=True, comment="csv, manual, demo, api")
    data_source_ref = Column(String(200), nullable=True, comment="Batch ID or filename")
    imported_at = Column(DateTime, nullable=True, comment="Date d'import")
    imported_by = Column(Integer, nullable=True, comment="User ID de l'importateur")

    # Relations avec les autres tables
    compteurs = relationship("Compteur", back_populates="site", cascade="all, delete-orphan", lazy="dynamic")
    alertes = relationship("Alerte", back_populates="site", cascade="all, delete-orphan", lazy="dynamic")
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
    meters = relationship("Meter", back_populates="site", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Site {self.id}: {self.nom} ({self.type.value})>"
