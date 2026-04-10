"""
PROMEOS — Patrimoine models (DIAMANT)
N-N link tables + Staging pipeline + Quality findings + DeliveryPoint.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin, SoftDeleteMixin
from .enums import (
    ActivationLogStatus,
    AtrdOption,
    DeliveryPointEnergyType,
    DeliveryPointStatus,
    GasProfileGrdf,
    HcReprogPhase,
    HcReprogStatus,
    ImportSourceType,
    QualityRuleSeverity,
    StagingStatus,
    TariffSegmentEnum,
)


# ========================================
# N-N Link Tables
# ========================================


class OrgEntiteLink(Base, TimestampMixin):
    """N-N: une organisation peut avoir N entites juridiques, et inversement."""

    __tablename__ = "org_entite_links"
    __table_args__ = (UniqueConstraint("organisation_id", "entite_juridique_id", name="uq_org_entite"),)

    id = Column(Integer, primary_key=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    entite_juridique_id = Column(Integer, ForeignKey("entites_juridiques.id"), nullable=False, index=True)
    role = Column(String(50), nullable=True, comment="proprietaire, gestionnaire, locataire")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    confidence = Column(Float, default=1.0, comment="Confiance du lien 0-1")
    source_ref = Column(String(200), nullable=True, comment="Reference source (facture, contrat)")


class PortfolioEntiteLink(Base, TimestampMixin):
    """N-N: un portefeuille peut etre lie a N entites juridiques."""

    __tablename__ = "portfolio_entite_links"
    __table_args__ = (UniqueConstraint("portefeuille_id", "entite_juridique_id", name="uq_portfolio_entite"),)

    id = Column(Integer, primary_key=True)
    portefeuille_id = Column(Integer, ForeignKey("portefeuilles.id"), nullable=False, index=True)
    entite_juridique_id = Column(Integer, ForeignKey("entites_juridiques.id"), nullable=False, index=True)
    role = Column(String(50), nullable=True)


# ========================================
# Staging Pipeline
# ========================================


class StagingBatch(Base, TimestampMixin):
    """Un batch d'import patrimoine (CSV, Excel, factures, manuel)."""

    __tablename__ = "staging_batches"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(Enum(StagingStatus), default=StagingStatus.DRAFT, nullable=False)
    source_type = Column(Enum(ImportSourceType), nullable=False)
    filename = Column(String(500), nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    mode = Column(String(20), nullable=True, comment="express, import, assiste, demo")
    stats_json = Column(Text, nullable=True)
    error_json = Column(Text, nullable=True)

    # Relations
    sites = relationship("StagingSite", back_populates="batch", cascade="all, delete-orphan")
    compteurs = relationship("StagingCompteur", back_populates="batch", cascade="all, delete-orphan")
    findings = relationship("QualityFinding", back_populates="batch", cascade="all, delete-orphan")


class StagingSite(Base, TimestampMixin):
    """Site en staging (pas encore active en base finale)."""

    __tablename__ = "staging_sites"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("staging_batches.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=True, comment="Ligne dans le fichier source")
    nom = Column(String(200), nullable=False)
    type_site = Column(String(50), nullable=True)
    adresse = Column(String(300), nullable=True)
    code_postal = Column(String(10), nullable=True)
    ville = Column(String(100), nullable=True)
    surface_m2 = Column(Float, nullable=True)
    siret = Column(String(14), nullable=True)
    naf_code = Column(String(5), nullable=True)
    # Lineage
    source_type = Column(String(20), nullable=True)
    source_ref = Column(String(200), nullable=True)
    # Multi-entité / bâtiment (Step 20 — optionnelles)
    siren_entite = Column(String(14), nullable=True, comment="SIREN entité juridique cible")
    nom_entite = Column(String(200), nullable=True, comment="Nom entité juridique cible")
    portefeuille_nom = Column(String(200), nullable=True, comment="Nom portefeuille cible")
    batiment_nom = Column(String(200), nullable=True, comment="Nom bâtiment à créer")
    batiment_surface_m2 = Column(Float, nullable=True, comment="Surface bâtiment (m²)")
    batiment_annee_construction = Column(Integer, nullable=True, comment="Année construction bâtiment")
    batiment_cvc_power_kw = Column(Float, nullable=True, comment="Puissance CVC bâtiment (kW)")
    # Mapping (set during correction step)
    target_site_id = Column(Integer, nullable=True, comment="Merge avec un site existant")
    target_portefeuille_id = Column(Integer, nullable=True)
    skip = Column(Boolean, default=False, comment="Ignore par l'utilisateur")
    # Step 35: incremental update matching
    match_method = Column(String(20), nullable=True, comment="siret, prm, nom_cp")
    match_confidence = Column(String(10), nullable=True, comment="high, medium")

    # Relations
    batch = relationship("StagingBatch", back_populates="sites")
    compteurs = relationship("StagingCompteur", back_populates="staging_site")


class StagingCompteur(Base, TimestampMixin):
    """Compteur en staging."""

    __tablename__ = "staging_compteurs"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("staging_batches.id"), nullable=False, index=True)
    staging_site_id = Column(Integer, ForeignKey("staging_sites.id"), nullable=True)
    row_number = Column(Integer, nullable=True)
    numero_serie = Column(String(50), nullable=True)
    meter_id = Column(String(14), nullable=True, comment="PRM/PDL/PCE")
    type_compteur = Column(String(20), nullable=True, comment="electricite, gaz, eau")
    puissance_kw = Column(Float, nullable=True)
    # Mapping
    target_site_id = Column(Integer, nullable=True)
    target_compteur_id = Column(Integer, nullable=True, comment="Merge avec compteur existant")
    skip = Column(Boolean, default=False)

    # Relations
    batch = relationship("StagingBatch", back_populates="compteurs")
    staging_site = relationship("StagingSite", back_populates="compteurs")


class QualityFinding(Base, TimestampMixin):
    """Resultat d'une regle de qualite sur un batch staging."""

    __tablename__ = "quality_findings"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("staging_batches.id"), nullable=False, index=True)
    rule_id = Column(String(50), nullable=False, comment="dup_site, dup_meter, orphan_meter, etc.")
    severity = Column(Enum(QualityRuleSeverity), nullable=False)
    staging_site_id = Column(Integer, nullable=True)
    staging_compteur_id = Column(Integer, nullable=True)
    evidence_json = Column(Text, nullable=True)
    suggested_action = Column(String(200), nullable=True, comment="merge, skip, fix_address")
    resolved = Column(Boolean, default=False)
    resolution = Column(String(200), nullable=True)

    # Relations
    batch = relationship("StagingBatch", back_populates="findings")


# ========================================
# Activation audit log
# ========================================


class ActivationLog(Base, TimestampMixin):
    """Audit trail for batch activation attempts."""

    __tablename__ = "activation_logs"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("staging_batches.id"), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(Enum(ActivationLogStatus), nullable=False)
    error_message = Column(Text, nullable=True)
    sites_created = Column(Integer, default=0)
    compteurs_created = Column(Integer, default=0)
    activation_hash = Column(String(64), nullable=True, index=True)
    user_id = Column(Integer, nullable=True)


# ========================================
# V-registre: Contract ↔ DeliveryPoint (N-N)
# Hypothese V1: 1 contrat = 1 site + 1 energie.
# Cette table permet de tracer quels PDL/PCE sont couverts par quel contrat.
# ========================================


class ContractDeliveryPoint(Base, TimestampMixin):
    """N-N: un contrat couvre N delivery points, un DP peut etre couvert par N contrats (succession)."""

    __tablename__ = "contract_delivery_points"
    __table_args__ = (UniqueConstraint("contract_id", "delivery_point_id", name="uq_contract_dp"),)

    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("energy_contracts.id"), nullable=False, index=True)
    delivery_point_id = Column(Integer, ForeignKey("delivery_points.id"), nullable=False, index=True)


# ========================================
# Delivery Point (PRM/PCE)
# ========================================


class DeliveryPoint(Base, TimestampMixin, SoftDeleteMixin):
    """Point de livraison energie (PRM elec / PCE gaz).

    Entite autonome representant un contrat de raccordement reseau.
    Un DeliveryPoint est lie a un Site et peut etre associe a N Compteurs.
    """

    __tablename__ = "delivery_points"

    id = Column(Integer, primary_key=True)
    code = Column(String(14), nullable=False, index=True, comment="PRM ou PCE (14 digits)")
    energy_type = Column(
        Enum(DeliveryPointEnergyType),
        nullable=True,
        comment="elec (PRM) ou gaz (PCE)",
    )
    # Vague 1 — gestionnaire de réseau (ENEDIS, GRDF, ELD_X, RTE...)
    # Critique pour router vers la bonne grille TURPE/ATRD et pour l'audit trail.
    grd_code = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Code GRD/GRT: ENEDIS, GRDF, ELD_STRASBOURG, RTE, etc.",
    )
    # Vague 2 — données techniques gaz (GRDF)
    atrd_option = Column(
        Enum(AtrdOption),
        nullable=True,
        comment="Option ATRD gaz (T1-T4 / TP) déterminée par CAR",
    )
    car_kwh = Column(
        Float,
        nullable=True,
        comment="Consommation Annuelle de Référence en kWh (GRDF)",
    )
    gas_profile = Column(
        Enum(GasProfileGrdf),
        nullable=True,
        comment="Profil GRDF: BASE, B0, B1, B2I, MODULANT",
    )
    cjn_mwh_per_day = Column(
        Float,
        nullable=True,
        comment="Capacité Journalière Normalisée (MWh/j) — référence GRDF",
    )
    cja_mwh_per_day = Column(
        Float,
        nullable=True,
        comment="Capacité Journalière Acheminement (MWh/j) — contractuelle T4",
    )
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    status = Column(
        Enum(DeliveryPointStatus),
        default=DeliveryPointStatus.ACTIVE,
        nullable=False,
    )

    # Segment TURPE
    tariff_segment = Column(
        Enum(TariffSegmentEnum),
        nullable=True,
        comment="C5_BT (≤36kVA), C4_BT (>36kVA), C3_HTA",
    )
    puissance_souscrite_kva = Column(Float, nullable=True, comment="Puissance souscrite (kVA)")

    # ── Reprogrammation Heures Creuses (chantier Enedis TURPE 7) ──
    hc_reprog_phase = Column(
        Enum(HcReprogPhase),
        nullable=True,
        comment="Phase reprog HC: phase_1, phase_2, phase_3, hors_perimetre",
    )
    hc_reprog_status = Column(
        Enum(HcReprogStatus),
        nullable=True,
        comment="Statut reprog: a_traiter, en_cours, traite, abandon",
    )
    hc_reprog_date_prevue = Column(Date, nullable=True, comment="Date reprog prévue (fichier M-6)")
    hc_reprog_date_effective = Column(Date, nullable=True, comment="Date reprog effective (CR-M)")
    hc_code_actuel = Column(String(20), nullable=True, comment="Code HC actuel sur le compteur")
    hc_code_futur = Column(String(20), nullable=True, comment="Code HC cible après reprog")
    hc_libelle_actuel = Column(String(100), nullable=True, comment="Libellé HC actuel")
    hc_libelle_futur = Column(String(100), nullable=True, comment="Libellé HC cible")
    # Phase 2: HC saisonnalisées (été ≠ hiver)
    hc_code_futur_ete = Column(String(20), nullable=True, comment="Code HC cible été (phase 2)")
    hc_code_futur_hiver = Column(String(20), nullable=True, comment="Code HC cible hiver (phase 2)")
    hc_saisonnalise = Column(Boolean, default=False, comment="True si HC saisonnalisées activées")

    # ── Lien vers TOUSchedule actif (résultat de la reprog) ──
    tou_schedule_id = Column(
        Integer,
        ForeignKey("tou_schedules.id", ondelete="SET NULL"),
        nullable=True,
        comment="TOUSchedule actif issu de la reprogrammation HC",
    )

    # Data lineage (coherent with Site/Compteur)
    data_source = Column(String(20), nullable=True, comment="csv, manual, demo, api")
    data_source_ref = Column(String(200), nullable=True, comment="Batch ID or filename")
    imported_at = Column(DateTime, nullable=True)
    imported_by = Column(Integer, nullable=True)

    # Relations
    site = relationship("Site", back_populates="delivery_points")
    compteurs = relationship("Compteur", back_populates="delivery_point")
    tou_schedule = relationship("TOUSchedule", foreign_keys=[tou_schedule_id])
