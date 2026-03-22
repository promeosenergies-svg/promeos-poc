"""
PROMEOS V39 - Modeles Tertiaire / OPERAT (Decret tertiaire)
EFA = Entite Fonctionnelle Assujettie
"""

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Float,
    Date,
    DateTime,
    Text,
    ForeignKey,
    Enum,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, SoftDeleteMixin
from .enums import (
    EfaStatut,
    EfaRole,
    DeclarationStatus,
    PerimeterEventType,
    DataQualityIssueSeverity,
    DataQualityIssueStatus,
    DpeClasseEnergie,
    DpeClasseGes,
    CsrdAssujettissement,
    CsrdScope,
)


class TertiaireEfa(Base, TimestampMixin, SoftDeleteMixin):
    """Entite Fonctionnelle Assujettie au Decret tertiaire."""

    __tablename__ = "tertiaire_efa"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True, index=True)
    nom = Column(String(300), nullable=False)
    statut = Column(Enum(EfaStatut), default=EfaStatut.DRAFT, nullable=False)
    role_assujetti = Column(Enum(EfaRole), default=EfaRole.PROPRIETAIRE, nullable=False)
    reporting_start = Column(Date, nullable=True)
    reporting_end = Column(Date, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    # Trajectoire OPERAT
    reference_year = Column(Integer, nullable=True, comment="Annee de reference (ex: 2010)")
    reference_year_kwh = Column(Float, nullable=True, comment="Conso reference verrouillée (kWh)")
    trajectory_status = Column(String(20), nullable=True, comment="on_track / off_track / not_evaluable")
    trajectory_last_calculated_at = Column(DateTime, nullable=True)

    # Baseline normalization policy
    baseline_normalization_status = Column(
        String(20), nullable=True, comment="normalized, raw_only, not_possible, unknown"
    )
    baseline_normalization_reason = Column(String(200), nullable=True)

    # Relations
    consumptions = relationship("TertiaireEfaConsumption", back_populates="efa", cascade="all, delete-orphan")
    buildings = relationship("TertiaireEfaBuilding", back_populates="efa", cascade="all, delete-orphan")
    responsibilities = relationship("TertiaireResponsibility", back_populates="efa", cascade="all, delete-orphan")
    events = relationship("TertiairePerimeterEvent", back_populates="efa", cascade="all, delete-orphan")
    declarations = relationship("TertiaireDeclaration", back_populates="efa", cascade="all, delete-orphan")
    proof_artifacts = relationship("TertiaireProofArtifact", back_populates="efa", cascade="all, delete-orphan")
    quality_issues = relationship("TertiaireDataQualityIssue", back_populates="efa", cascade="all, delete-orphan")


class TertiaireEfaLink(Base, TimestampMixin):
    """Lien entre EFA (turnover, scission, fusion)."""

    __tablename__ = "tertiaire_efa_link"

    id = Column(Integer, primary_key=True, index=True)
    child_efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    parent_efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    reason = Column(String(100), nullable=False)


class TertiaireEfaBuilding(Base, TimestampMixin):
    """Association EFA <-> Batiment avec usage et surface."""

    __tablename__ = "tertiaire_efa_building"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    building_id = Column(Integer, ForeignKey("batiments.id"), nullable=True, index=True)
    usage_label = Column(String(200), nullable=True)
    surface_m2 = Column(Float, nullable=True)

    efa = relationship("TertiaireEfa", back_populates="buildings")


class TertiaireResponsibility(Base, TimestampMixin):
    """Responsabilite d'un acteur sur une EFA."""

    __tablename__ = "tertiaire_responsibility"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    role = Column(Enum(EfaRole), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_value = Column(String(300), nullable=True)
    contact_email = Column(String(300), nullable=True)
    scope_json = Column(Text, nullable=True)

    efa = relationship("TertiaireEfa", back_populates="responsibilities")


class TertiairePerimeterEvent(Base, TimestampMixin):
    """Evenement de perimetre EFA (changement occupant, vacance, renovation, etc.)."""

    __tablename__ = "tertiaire_perimeter_event"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    type = Column(Enum(PerimeterEventType), nullable=False)
    effective_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    justification = Column(Text, nullable=True)
    attachments_json = Column(Text, nullable=True)

    efa = relationship("TertiaireEfa", back_populates="events")


class TertiaireDeclaration(Base, TimestampMixin):
    """Declaration annuelle OPERAT pour une EFA."""

    __tablename__ = "tertiaire_declaration"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    status = Column(Enum(DeclarationStatus), default=DeclarationStatus.DRAFT, nullable=False)
    checklist_json = Column(Text, nullable=True)
    exported_pack_path = Column(String(500), nullable=True)

    efa = relationship("TertiaireEfa", back_populates="declarations")


class TertiaireProofArtifact(Base, TimestampMixin):
    """Preuve documentaire liee a une EFA (pont vers Memobox via kb_doc_id)."""

    __tablename__ = "tertiaire_proof_artifact"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    type = Column(String(100), nullable=False)
    file_path = Column(String(500), nullable=True)
    kb_doc_id = Column(String(200), nullable=True)
    owner_role = Column(Enum(EfaRole), nullable=True)
    valid_from = Column(Date, nullable=True)
    valid_to = Column(Date, nullable=True)
    tags_json = Column(Text, nullable=True)

    efa = relationship("TertiaireEfa", back_populates="proof_artifacts")


class TertiaireDataQualityIssue(Base, TimestampMixin):
    """Issue de qualite de donnees pour une EFA / annee."""

    __tablename__ = "tertiaire_data_quality_issue"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id"), nullable=False, index=True)
    year = Column(Integer, nullable=True)
    code = Column(String(100), nullable=False)
    severity = Column(Enum(DataQualityIssueSeverity), nullable=False)
    message_fr = Column(Text, nullable=False)
    impact_fr = Column(Text, nullable=True)
    action_fr = Column(Text, nullable=True)
    status = Column(Enum(DataQualityIssueStatus), default=DataQualityIssueStatus.OPEN, nullable=False)
    proof_required_json = Column(Text, nullable=True)
    proof_owner_role = Column(String(100), nullable=True)

    efa = relationship("TertiaireEfa", back_populates="quality_issues")


class TertiaireEfaConsumption(Base, TimestampMixin):
    """Consommation energetique annuelle d'une EFA — base de la trajectoire OPERAT."""

    __tablename__ = "tertiaire_efa_consumption"
    __table_args__ = (UniqueConstraint("efa_id", "year", name="uq_efa_consumption_year"),)

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id", ondelete="CASCADE"), nullable=False, index=True)
    year = Column(Integer, nullable=False, comment="Annee de la consommation")
    kwh_total = Column(Float, nullable=False, comment="Consommation totale (kWh)")
    kwh_elec = Column(Float, nullable=True, comment="Part electricite (kWh)")
    kwh_gaz = Column(Float, nullable=True, comment="Part gaz (kWh)")
    kwh_reseau = Column(Float, nullable=True, comment="Part reseau chaleur/froid (kWh)")
    is_reference = Column(Boolean, default=False, nullable=False, comment="True si annee de reference")
    is_normalized = Column(Boolean, default=False, nullable=False, comment="True si normalise climatiquement")
    source = Column(
        String(50), nullable=True, comment="declared_manual, import_invoice, site_fallback, inferred, unknown"
    )
    reliability = Column(String(20), nullable=True, default="unverified", comment="high, medium, low, unverified")

    # Normalisation climatique
    normalized_kwh_total = Column(Float, nullable=True, comment="Conso normalisee climatiquement (kWh)")
    normalization_method = Column(String(50), nullable=True, comment="dju_ratio, none")
    normalization_confidence = Column(String(20), nullable=True, comment="high, medium, low, none")
    dju_heating = Column(Float, nullable=True, comment="Degres-jours unifies chauffage")
    dju_cooling = Column(Float, nullable=True, comment="Degres-jours unifies climatisation")
    dju_reference = Column(Float, nullable=True, comment="DJU reference (moyenne 30 ans)")
    weather_data_source = Column(String(100), nullable=True, comment="meteo_france, manual, estimated")
    normalized_at = Column(DateTime, nullable=True)

    efa = relationship("TertiaireEfa", back_populates="consumptions")


# ========================================
# DPE Tertiaire (Décret 2024-1040)
# Obligatoire bâtiments tertiaires > 1000 m²
# Affichage public obligatoire depuis 01/07/2026
# Validité: 10 ans
# ========================================


class TertiaireEfaDpe(Base, TimestampMixin):
    """DPE Tertiaire lié à une EFA — décret 2024-1040, arrêté 25/03/2024.

    Obligation:
    - Bâtiments tertiaires > 1000 m² (neufs et existants)
    - Affichage public obligatoire (art. L.126-33 CCH)
    - Validité 10 ans
    - Réalisation par diagnostiqueur certifié (art. L.271-6 CCH)
    """

    __tablename__ = "tertiaire_efa_dpe"

    id = Column(Integer, primary_key=True, index=True)
    efa_id = Column(Integer, ForeignKey("tertiaire_efa.id", ondelete="CASCADE"), nullable=False, index=True)

    # Classification
    classe_energie = Column(Enum(DpeClasseEnergie), nullable=False, default=DpeClasseEnergie.VIERGE)
    classe_ges = Column(Enum(DpeClasseGes), nullable=False, default=DpeClasseGes.VIERGE)

    # Consommation & émissions (valeurs DPE)
    conso_ep_kwh_m2_an = Column(Float, nullable=True, comment="Consommation énergie primaire (kWhEP/m²/an)")
    emission_ges_kg_m2_an = Column(Float, nullable=True, comment="Émissions GES (kgCO2eq/m²/an)")

    # Dates
    date_realisation = Column(Date, nullable=True)
    date_validite = Column(Date, nullable=True, comment="date_realisation + 10 ans")
    date_affichage = Column(Date, nullable=True, comment="Date mise en affichage public")

    # Diagnostiqueur
    diagnostiqueur_nom = Column(String(200), nullable=True)
    diagnostiqueur_certif = Column(String(100), nullable=True, comment="N° certification COFRAC")
    numero_ademe = Column(String(20), nullable=True, comment="N° DPE ADEME (13 chiffres)")

    # Recommandations
    recommandations_json = Column(Text, nullable=True, comment="Travaux recommandés (JSON)")

    # Document
    file_ref = Column(String(500), nullable=True, comment="URL ou référence fichier DPE")

    efa = relationship("TertiaireEfa", backref="dpe_diagnostics")


# ========================================
# Seuils absolus OPERAT par catégorie
# Arrêté du 10/04/2020 modifié — valeurs absolues (Cabs)
# Alternative à la trajectoire relative (-40% / -50% / -60%)
# ========================================


class TertiaireSeuilAbsolu(Base, TimestampMixin):
    """Seuil absolu OPERAT (Cabs) par catégorie fonctionnelle et zone climatique.

    Art. R.174-26 du CCH: les assujettis peuvent choisir entre
    - Trajectoire relative: -40% (2030), -50% (2040), -60% (2050) vs année référence
    - Valeurs absolues (Cabs): seuil en kWhEF/m²/an par catégorie + zone climatique

    Sources: arrêté du 10/04/2020 modifié (annexes), guide ADEME.
    """

    __tablename__ = "tertiaire_seuil_absolu"
    __table_args__ = (
        UniqueConstraint("categorie_fonctionnelle", "zone_climatique", "echeance_annee", name="uq_seuil_absolu"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Catégorie fonctionnelle OPERAT
    categorie_fonctionnelle = Column(
        String(100),
        nullable=False,
        comment="Ex: bureaux, enseignement_1er_degre, commerce_detail, sante_hopital, hotel_tourisme",
    )
    sous_categorie = Column(String(100), nullable=True, comment="Sous-catégorie si applicable")

    # Zone climatique (H1a, H1b, H1c, H2a, H2b, H2c, H2d, H3)
    zone_climatique = Column(String(10), nullable=False, comment="H1a, H1b, H1c, H2a, H2b, H2c, H2d, H3")

    # Échéance (2030, 2040, 2050)
    echeance_annee = Column(Integer, nullable=False, comment="2030, 2040 ou 2050")

    # Seuil en kWhEF/m²/an (énergie finale)
    seuil_kwh_ef_m2_an = Column(Float, nullable=False, comment="Valeur Cabs (kWhEF/m²/an)")

    # Source réglementaire
    source_arrete = Column(String(200), nullable=True, default="Arrêté 10/04/2020 modifié")
    notes = Column(Text, nullable=True)


# ========================================
# CSRD — Directive 2022/2464
# Corporate Sustainability Reporting Directive
# Obligatoire: grandes entreprises (exercice 2025+),
#              PME cotées (exercice 2026+)
# ========================================


class CsrdAssujettissementSite(Base, TimestampMixin):
    """Assujettissement CSRD d'une organisation et données de reporting par site.

    Critères grande entreprise (2 des 3):
    - > 250 salariés
    - > 50 M€ CA net
    - > 25 M€ total bilan

    Obligations:
    - DPEF (Déclaration de Performance Extra-Financière) remplacée par rapport durabilité
    - Scope 1/2/3 GHG (protocole GHG / ISO 14064)
    - Alignement taxonomie EU (% CA/CAPEX/OPEX durables)
    - Audit par OTI (Organisme Tiers Indépendant)
    """

    __tablename__ = "csrd_site_reporting"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True, index=True)
    year = Column(Integer, nullable=False, comment="Exercice de reporting")

    # Assujettissement
    assujettissement = Column(
        Enum(CsrdAssujettissement),
        default=CsrdAssujettissement.NON_ASSUJETTI,
        nullable=False,
    )

    # Scope 1 — Émissions directes (combustion sur site, véhicules propres)
    scope1_tco2eq = Column(Float, nullable=True, comment="Scope 1 en tCO2eq")
    scope1_source = Column(String(100), nullable=True, comment="manual, bilan_carbone, api")

    # Scope 2 — Émissions indirectes énergie (élec, chaleur, vapeur achetées)
    scope2_location_tco2eq = Column(Float, nullable=True, comment="Scope 2 location-based (tCO2eq)")
    scope2_market_tco2eq = Column(Float, nullable=True, comment="Scope 2 market-based (tCO2eq)")
    facteur_emission_elec = Column(Float, nullable=True, comment="gCO2eq/kWh élec utilisé")

    # Scope 3 — Chaîne de valeur (optionnel V1)
    scope3_tco2eq = Column(Float, nullable=True, comment="Scope 3 estimé (tCO2eq)")

    # Taxonomie EU
    pct_ca_aligne = Column(Float, nullable=True, comment="% CA aligné taxonomie EU")
    pct_capex_aligne = Column(Float, nullable=True, comment="% CAPEX aligné taxonomie EU")
    pct_opex_aligne = Column(Float, nullable=True, comment="% OPEX aligné taxonomie EU")

    # Audit
    oti_nom = Column(String(200), nullable=True, comment="Organisme Tiers Indépendant")
    oti_date_audit = Column(Date, nullable=True)
    rapport_durabilite_ref = Column(String(500), nullable=True, comment="Ref du rapport de durabilité")

    notes = Column(Text, nullable=True)
