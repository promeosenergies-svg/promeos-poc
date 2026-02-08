"""
PROMEOS - Entités du modèle de données
Gestion énergétique multi-sites (120 sites)
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
from .conformite import StatutConformite
import enum

# ========================================
# ENUMS - Types énergétiques PROMEOS
# ========================================

class TypeCompteur(str, enum.Enum):
    """Types de compteurs d'énergie"""
    ELECTRICITE = "electricite"
    GAZ = "gaz"
    EAU = "eau"

class TypeSite(str, enum.Enum):
    """Types de sites gérés par PROMEOS"""
    MAGASIN = "magasin"
    USINE = "usine"
    BUREAU = "bureau"
    ENTREPOT = "entrepot"

class SeveriteAlerte(str, enum.Enum):
    """Niveaux de sévérité des alertes énergétiques"""
    INFO = "info"           # Information
    WARNING = "warning"     # Attention
    CRITICAL = "critical"   # Critique


# ========================================
# MODÈLE SITE - Cœur de PROMEOS
# ========================================

class Site(Base, TimestampMixin):
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

    # Conformité réglementaire
    portefeuille_id = Column(Integer, ForeignKey("portefeuilles.id"), nullable=True)
    statut_decret_tertiaire = Column(Enum(StatutConformite), default=StatutConformite.A_RISQUE)
    avancement_decret_pct = Column(Float, default=0.0)  # % avancement (0-100)
    statut_bacs = Column(Enum(StatutConformite), default=StatutConformite.A_RISQUE)
    anomalie_facture = Column(Boolean, default=False)
    action_recommandee = Column(String, nullable=True)
    risque_financier_euro = Column(Float, default=0.0)  # € de risque détecté

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
    portefeuille = relationship("Portefeuille", backref="sites")

    def __repr__(self):
        return f"<Site {self.id}: {self.nom} ({self.type.value})>"


# ========================================
# MODÈLE COMPTEUR - Équipements énergétiques
# ========================================

class Compteur(Base, TimestampMixin):
    """
    Compteur d'énergie (électricité, gaz, eau)
    Un site peut avoir plusieurs compteurs
    """
    __tablename__ = "compteurs"
    
    # Identifiant
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    
    # Caractéristiques du compteur
    type = Column(Enum(TypeCompteur), nullable=False, comment="Type de compteur")
    numero_serie = Column(String(50), unique=True, index=True, comment="Numéro de série unique")
    puissance_souscrite_kw = Column(Float, comment="Puissance souscrite (kW) pour électricité")
    
    # Status
    actif = Column(Boolean, default=True, comment="Compteur actif ou non")
    
    # Relations
    site = relationship("Site", back_populates="compteurs")
    consommations = relationship(
        "Consommation", 
        back_populates="compteur", 
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self):
        return f"<Compteur {self.id}: {self.type.value} - {self.numero_serie}>"


# ========================================
# MODÈLE CONSOMMATION - Relevés énergétiques
# ========================================

class Consommation(Base, TimestampMixin):
    """
    Relevé de consommation énergétique
    Données horaires ou journalières
    """
    __tablename__ = "consommations"
    
    # Identifiant
    id = Column(Integer, primary_key=True, index=True)
    compteur_id = Column(Integer, ForeignKey("compteurs.id"), nullable=False, index=True)
    
    # Données de consommation
    timestamp = Column(DateTime, nullable=False, index=True, comment="Date/heure du relevé")
    valeur = Column(Float, nullable=False, comment="Valeur consommée (kWh, m³, etc.)")
    cout_euro = Column(Float, comment="Coût en euros")
    
    # Relations
    compteur = relationship("Compteur", back_populates="consommations")
    
    def __repr__(self):
        return f"<Consommation {self.id}: {self.valeur} à {self.timestamp}>"


# ========================================
# MODÈLE ALERTE - Notifications énergétiques
# ========================================

class Alerte(Base, TimestampMixin):
    """
    Alerte de dépassement ou anomalie énergétique
    """
    __tablename__ = "alertes"
    
    # Identifiant
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    
    # Informations de l'alerte
    severite = Column(Enum(SeveriteAlerte), nullable=False, index=True, comment="Niveau de gravité")
    titre = Column(String(200), nullable=False, comment="Titre de l'alerte")
    description = Column(Text, comment="Description détaillée")
    
    # Timestamps et résolution
    timestamp = Column(DateTime, nullable=False, index=True, comment="Date/heure de l'alerte")
    resolue = Column(Boolean, default=False, comment="Alerte résolue ou non")
    date_resolution = Column(DateTime, comment="Date de résolution")
    
    # Relations
    site = relationship("Site", back_populates="alertes")
    
    def __repr__(self):
        status = "✅" if self.resolue else "⚠️"
        return f"<Alerte {self.id}: {status} {self.titre} ({self.severite.value})>"
