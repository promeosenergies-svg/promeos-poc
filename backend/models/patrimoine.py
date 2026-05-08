"""
PROMEOS — Patrimoine models (DIAMANT)
N-N link tables + Staging pipeline + Quality findings + DeliveryPoint.
"""

import re

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
from sqlalchemy.orm import relationship, validates

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
    # Sprint D1-B contraintes cardinales matrice v1 §8.3 — C60 PRM unique global +
    # C85 PCE unique global. L'unicité runtime est gérée par un **partial unique index**
    # (`uq_delivery_point_code_active` créé par `database/migrations.py:_add_unique_delivery_point_code_index`)
    # avec `WHERE deleted_at IS NULL`, ce qui autorise la réutilisation d'un PRM/PCE
    # après soft-delete (cas légitime décommissionnement + ré-attribution Enedis/GRDF).
    code = Column(
        String(14), nullable=False, index=True, comment="PRM ou PCE (14 digits) — unique partial active C60/C85"
    )
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

    # Phase D-1 hotfix — D-Audit-PARAM-DP-TURPE7-Explicite-006 P1 :
    # Champs TURPE 7 explicites Section 4.6 matrice v1 (vs `tariff_segment` enum partiel).
    # Cohérent CRE délibération 2025-78 du 13/03/2025 (JO 14/05/2025) TURPE 7 HTA-BT
    # + cohérent Phase 7.8 fix codes period_code TURPE 7 vs TURPE 6 legacy.
    categorie_turpe = Column(
        String(20),
        nullable=True,
        comment="Catégorie TURPE explicite (C5, C4, C3, C2, C1) — matrice v1 §4.6",
    )
    domaine_tension = Column(
        String(20),
        nullable=True,
        comment="Domaine tension (BT≤36kVA, BT>36kVA, HTA, HTB) — matrice v1 §4.6",
    )
    code_fta = Column(
        String(50),
        nullable=True,
        comment="FTA canonique CRE TURPE 7 (BTINFCU4/BTINFMU4/BTSUPCU/BTSUPLU/HTACU5/HTALU5) — matrice v1 §4.6 / Délib. 2025-78",
    )
    version_turpe = Column(
        String(10),
        nullable=True,
        comment="Version TURPE active (TURPE_6, TURPE_7) — déterminant tarif applicable",
    )
    mode_traitement = Column(
        String(20),
        nullable=True,
        comment="Mode traitement compteur (smart, traditionnel, telereleve, manuel) — matrice v1 §4.6",
    )

    # Phase D-4 Tier 1 — DP gaz 5 P0 matérialisés (ADR-D-02) + 2 P0 Accise CIBS (ADR-D-05) :
    # Audit cardinal : docs/audits/AUDIT_ECARTS_MATRICE_V1_2026_05_07.md §3 P0-MATV1-002/003/006/007/008.
    pce_format = Column(
        String(20),
        nullable=True,
        comment="Format PCE/PRM gaz (DISTRIBUTION_14/DISTRIBUTION_GI/TRANSPORT_PIR) — matrice v1 §4.6.C#2 ADR-D-02",
    )
    type_reseau = Column(
        String(20),
        nullable=True,
        comment="Type réseau gaz (DISTRIBUTION/TRANSPORT) — matrice v1 §4.6.C#3 ADR-D-02",
    )
    referentiel_tarifaire = Column(
        String(10),
        nullable=True,
        comment="Référentiel tarifaire gaz (ATRD/ATRT) — matrice v1 §4.6.C#5 ADR-D-02",
    )
    est_profile = Column(
        Boolean,
        nullable=True,
        comment="True si DP gaz profilé (T1/T2/T3) — matrice v1 §4.6.C#6 ADR-D-02",
    )
    mode_releve_gaz = Column(
        String(10),
        nullable=True,
        comment="Mode relevé gaz (MM/MJ/JJ/MH) — matrice v1 §4.6.C#8 ADR-D-02",
    )
    accise_categorie_elec = Column(
        String(30),
        nullable=True,
        comment="Catégorie accise CIBS élec (MENAGES_ASSIMILES/PME/HAUTE_PUISSANCE) — matrice v1 §4.6.B#16 ADR-D-05",
    )
    accise_categorie_gaz = Column(
        String(20),
        nullable=True,
        comment="Catégorie accise CIBS gaz (NATUREL/GPL/GNL) — matrice v1 §4.6.C#18 ADR-D-05",
    )

    # Phase D-4 Tier 2 — 2 P1 doctrine champs DP élec + gaz
    # Audit : AUDIT_ECARTS_MATRICE_V1_2026_05_07.md §4 P1-MATV1-028 + 033.
    cdc_pas_temporel_minutes = Column(
        Integer,
        nullable=True,
        comment="Pas temporel CDC Enedis (minutes — typiquement 30 ou 10) — matrice v1 §4.6.B#8 / cardinal CUSUM/forecasting",
    )
    pcs_kwh_par_nm3 = Column(
        Float,
        nullable=True,
        comment="PCS gaz (Pouvoir Calorifique Supérieur kWh/Nm³) — matrice v1 §4.6.C#13 / api_grdf",
    )

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

    # ─── Sprint C-4 Phase 4.4 — Consentement RGPD local override (ADR-007) ───
    # Override possible vs Org.consentement_*_global (cascade Phase 4.5).
    # Court-circuit ELD locales : consentement_grdf_local s'applique uniquement
    # quand grd_code='GRDF' (Régaz/GreenAlp/R-GDS/etc. ont leur propre process).
    consentement_dataconnect_local = Column(
        Boolean,
        nullable=True,
        index=True,
        comment="Override local DataConnect par PRM (Phase 4.5 cascade ADR-007)",
    )
    consentement_dataconnect_local_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp override local DataConnect (RGPD audit)",
    )
    consentement_grdf_local = Column(
        Boolean,
        nullable=True,
        comment="Override local GRDF par PCE (cascade Phase 4.5 — uniquement grd_code=GRDF)",
    )
    consentement_grdf_local_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp override local GRDF (RGPD audit)",
    )

    # ─── Sprint C-5 Phase 5.3 — Audit RGPD étendu local (ADR-007 ext) ────────
    # ondelete=SET NULL : suppression user RGPD-droit oubli préserve l'historique
    # de consentement local (la trace persiste, la référence personnelle disparaît).
    consentement_dataconnect_local_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ayant donné l'override local DataConnect (RGPD audit, NULL si user supprimé)",
    )
    consentement_dataconnect_local_cgu_version = Column(
        String(20),
        nullable=True,
        comment="Version CGU au moment de l'override local DataConnect",
    )
    consentement_grdf_local_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ayant donné l'override local GRDF (RGPD audit, NULL si user supprimé)",
    )
    consentement_grdf_local_cgu_version = Column(
        String(20),
        nullable=True,
        comment="Version CGU au moment de l'override local GRDF",
    )

    # ─── Sprint D1-B validators cross-FK Top 20 contraintes matrice v1 §8.3 ───
    # Pattern Pilier 8 candidat ADR-016 (validators runtime) — cardinal pré-pilote.
    # Source: CRE délibération 2025-78 du 13/03/2025 (TURPE 7) + ATRD 7 GRDF.

    # Matrice TURPE 7 §4.6 : categorie ↔ domaine_tension
    _TURPE_CAT_TO_DOMAINE: dict[str, set[str]] = {
        "C5": {"BT≤36kVA", "BT_INF_36"},  # BT < 36 kVA
        "C4": {"BT>36kVA", "BT_SUP_36"},  # BT > 36 kVA ≤ 250 kVA
        "C3": {"HTA"},
        "C2": {"HTA"},
        "C1": {"HTB"},
    }

    # Phase D-1bis : regex permissive pour code_fta (cohérent recommandation audit
    # P0-002 Phase D — la nomenclature canonique CRE finale sera figée Phase D-2
    # via Enum exhaustif `code_fta IN (BTINFCU4, BTINFMU4, BTSUP, HTACU5, HTALU5, ...)`.
    # En attendant, on rejette les valeurs ne respectant PAS le préfixe segmentaire.
    _CODE_FTA_PREFIX_PATTERN = re.compile(r"^(C[1-5]|BTINF|BTSUP|BT|HTA|HTB)", re.IGNORECASE)

    # Mapping grd_code → energy_type attendu (C89-90 partiel — `type_reseau` absent du modèle)
    _GRD_ENERGY_TYPE_MAP: dict[str, str] = {
        "ENEDIS": "elec",
        "RTE": "elec",
        "GRDF": "gaz",
        "TERAGA": "gaz",
        "TEREGA": "gaz",
        "GRTGAZ": "gaz",
    }

    @validates("categorie_turpe", "domaine_tension")
    def _validate_categorie_domaine_coherence(self, key: str, value: str | None):
        """C61-63 matrice v1 §8.3 : `categorie_turpe` ⟺ `domaine_tension`.

        C5 → BT≤36kVA / C4 → BT>36kVA / C3-C2 → HTA / C1 → HTB.
        """
        if value is None:
            return value
        cat = value if key == "categorie_turpe" else self.categorie_turpe
        dom = value if key == "domaine_tension" else self.domaine_tension
        if cat is None or dom is None:
            return value
        allowed = self._TURPE_CAT_TO_DOMAINE.get(cat.upper())
        if allowed is None:
            raise ValueError(f"C61-63 violation: categorie_turpe={cat!r} non reconnue (attendu C1-C5)")
        if dom.replace(" ", "") not in {a.replace(" ", "") for a in allowed}:
            raise ValueError(
                f"C61-63 violation: categorie_turpe={cat!r} incompatible avec domaine_tension={dom!r} "
                f"(attendu {sorted(allowed)})"
            )
        return value

    # Phase D-3 Tier 2 VAL-1 — PCE/PRM 3 formats canoniques (audit web search regulatory-expert) :
    #   - DISTRIBUTION_14 : 14 chiffres (Enedis PRM élec + PCE GRDF résidentiel/petit pro)
    #     Source : CRE Délib. 2025-161 du 19/06/2025 (JORFTEXT000051807406) :
    #       "PCE 14 chiffres (utilisateurs résidentiels et petits professionnels)"
    #   - DISTRIBUTION_GI : `GI` + 6 chiffres (PCE GRDF **gros industriel** distribution)
    #     Source : CRE 2025-161 : "PCE GI (gros utilisateurs, notamment industriels)"
    #     ⚠️ Longueur exacte 6 chiffres : info contractuelle ADICT (non vérifiable
    #     publiquement). Confidence longueur: low — escalade humaine Phase D-4 si besoin.
    #   - TRANSPORT_PIR  : `IR` + 4 chiffres (Point Interconnexion Réseau GRTgaz/NaTran/Teréga)
    #     Source : URLs publiques smart.grtgaz.com (typePoint=PIR) — exemples IR0011, IR0015, IR0053.
    #
    # ⚠️ Matrice v1 §4.6.C label 'TRANSPORT_GI6' = imprécision corrigée Phase D-3 Tier 2 :
    # `GI\d{6}` est en réalité un PCE distribution gros industriel GRDF, PAS du transport.
    # Le format transport canonique est `IR\d{4}`.
    _PCE_PRM_PATTERN = re.compile(r"^(\d{14}|GI\d{6}|IR\d{4})$")

    @validates("code")
    def _validate_code_pce_prm_format(self, key: str, value: str | None):
        """VAL-1 Phase D-3 Tier 2 : PRM élec ou PCE gaz — 3 formats canoniques.

        Sources officielles cross-checkées audit regulatory-expert agent SDK :
        - DISTRIBUTION_14 : `\\d{14}` (Enedis PRM élec OU GRDF PCE résidentiel/petit pro) — CRE 2025-161
        - DISTRIBUTION_GI : `GI\\d{6}` (GRDF gros industriel distribution) — CRE 2025-161 (longueur 6 à valider Phase D-4)
        - TRANSPORT_PIR   : `IR\\d{4}` (Point Interconnexion Réseau transport GRTgaz/NaTran) — smart.grtgaz.com

        Validation runtime cardinale anti-saisie utilisateur incorrecte.
        """
        if value is None or value == "":
            return value
        if not self._PCE_PRM_PATTERN.match(value):
            raise ValueError(
                f"VAL-1 Phase D-3 Tier 2 violation : code={value!r} format PRM/PCE invalide "
                f"(attendu un de : 14 chiffres / 'GI' + 6 chiffres / 'IR' + 4 chiffres — "
                f"sources CRE 2025-161 + smart.grtgaz.com)"
            )
        return value

    @validates("version_turpe")
    def _validate_version_turpe_strict(self, key: str, value: str | None):
        """DOC-1 Phase D-3 Tier 2 : `version_turpe` strict Enum `VersionTurpeEnum`.

        Pattern Pilier 9 ADR-016 : String reste, validator runtime exige valeur Enum
        (pas de migration colonne — préserve baseline DB).
        """
        if value is None or value == "":
            return value
        from .enums import VersionTurpeEnum

        valid = {v.value for v in VersionTurpeEnum}
        if value not in valid:
            raise ValueError(
                f"DOC-1 Phase D-3 Tier 2 violation : version_turpe={value!r} non canonique "
                f"(attendu {sorted(valid)} — VersionTurpeEnum)"
            )
        return value

    @validates("mode_traitement")
    def _validate_mode_traitement_strict(self, key: str, value: str | None):
        """DOC-1 Phase D-3 Tier 2 : `mode_traitement` strict Enum `ModeTraitementEnum`."""
        if value is None or value == "":
            return value
        from .enums import ModeTraitementEnum

        valid = {v.value for v in ModeTraitementEnum}
        if value not in valid:
            raise ValueError(
                f"DOC-1 Phase D-3 Tier 2 violation : mode_traitement={value!r} non canonique "
                f"(attendu {sorted(valid)} — ModeTraitementEnum)"
            )
        return value

    @validates("code_fta")
    def _validate_code_fta_format(self, key: str, value: str | None):
        """C64 matrice v1 §8.3 : `code_fta` cohérent segmentation tarifaire.

        Phase D-1bis (regex permissive) → **Phase D-2.2 strict canonique** : le
        validator exige désormais que `code_fta` appartienne à `FtaCode` Enum
        canonique (CANONICAL_FTA_CODES_TURPE_7). Pattern Pilier 9 ADR-016 :
        "Validator permissif transitoire → Enum strict canonique post-audit".

        Source : CRE délibération 2025-78 du 13/03/2025 — codes BTINFCU4 /
        BTINFMU4 / BTSUPCU / BTSUPLU / HTACU5 / HTALU5 (medium-confidence —
        Enum exhaustif sera figé Phase D-3 post parsing PDF).
        """
        if value is None or value == "":
            return value

        # Phase D-2.2 cardinal : strict canonique CRE (rejette codes inventés non listés FtaCode).
        from .enums import FtaCode

        canonical_values = {fc.value for fc in FtaCode}
        if value not in canonical_values:
            raise ValueError(
                f"C64 violation Phase D-2.2 strict canonique: code_fta={value!r} non canonique CRE TURPE 7. "
                f"Attendu un de {sorted(canonical_values)} (Délib. CRE 2025-78). "
                f"Pattern Pilier 9 ADR-016 — voir docs/audits/AUDIT_CODES_FTA_TURPE7_2026_05_07.md."
            )

        # Cohérence cardinale code_fta vs categorie_turpe : si categorie_turpe
        # défini, code_fta doit en partager la racine BT/HTA/HTB.
        if self.categorie_turpe:
            cat = self.categorie_turpe.upper()
            expected_segments = {
                "C5": ("BT", "C5"),
                "C4": ("BT", "C4"),
                "C3": ("HTA", "C3"),
                "C2": ("HTA", "C2"),
                "C1": ("HTB", "C1"),
            }.get(cat)
            if expected_segments and not value.upper().startswith(expected_segments):
                raise ValueError(
                    f"C64 violation: code_fta={value!r} incohérent avec "
                    f"categorie_turpe={cat!r} (attendu préfixe {expected_segments})"
                )
        return value

    @validates("pce_format")
    def _validate_pce_format_strict(self, key: str, value: str | None):
        """Phase D-4 Tier 1 ADR-D-02 : `pce_format` strict Enum + cohérence cross-FK avec `code`.

        P0-1 fix code-reviewer audit milieu-étape : enforce que `pce_format` correspond
        au regex de `code` (DISTRIBUTION_14 ↔ \\d{14}, DISTRIBUTION_GI ↔ GI\\d{6},
        TRANSPORT_PIR ↔ IR\\d{4}). Empêche divergence silencieuse entre colonnes.
        """
        if value is None or value == "":
            return value
        from .enums import PceFormatEnum

        valid = {v.value for v in PceFormatEnum}
        if value not in valid:
            raise ValueError(
                f"Phase D-4 Tier 1 violation : pce_format={value!r} non canonique "
                f"(attendu {sorted(valid)} — PceFormatEnum)"
            )

        # P0-1 cross-FK : cohérence pce_format ↔ code regex
        if self.code:
            expected_pattern_for_format = {
                "DISTRIBUTION_14": re.compile(r"^\d{14}$"),
                "DISTRIBUTION_GI": re.compile(r"^GI\d{6}$"),
                "TRANSPORT_PIR": re.compile(r"^IR\d{4}$"),
            }
            pattern = expected_pattern_for_format.get(value)
            if pattern is not None and not pattern.match(self.code):
                raise ValueError(
                    f"Phase D-4 Tier 1 P0-1 violation : pce_format={value!r} incohérent avec "
                    f"code={self.code!r} (attendu pattern {pattern.pattern})"
                )
        return value

    # P1-1 fix code-reviewer : cross-validator type_reseau ↔ referentiel_tarifaire
    # Bijection cardinale : DISTRIBUTION → ATRD (GRDF + ELD), TRANSPORT → ATRT (GRTgaz/NaTran/Teréga)
    _TYPE_RESEAU_REFERENTIEL_BIJECTION: dict[str, str] = {
        "DISTRIBUTION": "ATRD",
        "TRANSPORT": "ATRT",
    }

    @validates("type_reseau")
    def _validate_type_reseau_strict(self, key: str, value: str | None):
        """Phase D-4 Tier 1 ADR-D-02 : `type_reseau` strict + cross-FK référentiel."""
        if value is None or value == "":
            return value
        from .enums import TypeReseauEnum

        valid = {v.value for v in TypeReseauEnum}
        if value not in valid:
            raise ValueError(
                f"Phase D-4 Tier 1 violation : type_reseau={value!r} non canonique "
                f"(attendu {sorted(valid)} — TypeReseauEnum)"
            )

        # P1-1 cross-FK : DISTRIBUTION → ATRD, TRANSPORT → ATRT
        expected_referentiel = self._TYPE_RESEAU_REFERENTIEL_BIJECTION.get(value)
        if expected_referentiel and self.referentiel_tarifaire and self.referentiel_tarifaire != expected_referentiel:
            raise ValueError(
                f"Phase D-4 Tier 1 P1-1 violation : type_reseau={value!r} incohérent avec "
                f"referentiel_tarifaire={self.referentiel_tarifaire!r} (attendu {expected_referentiel})"
            )
        return value

    @validates("referentiel_tarifaire")
    def _validate_referentiel_tarifaire_strict(self, key: str, value: str | None):
        """Phase D-4 Tier 1 ADR-D-02 : `referentiel_tarifaire` strict + cross-FK type_reseau."""
        if value is None or value == "":
            return value
        from .enums import ReferentielTarifaireEnum

        valid = {v.value for v in ReferentielTarifaireEnum}
        if value not in valid:
            raise ValueError(
                f"Phase D-4 Tier 1 violation : referentiel_tarifaire={value!r} non canonique "
                f"(attendu {sorted(valid)} — ReferentielTarifaireEnum)"
            )

        # P1-1 cross-FK bijection inverse : ATRD ← DISTRIBUTION, ATRT ← TRANSPORT
        inverse_bijection = {v: k for k, v in self._TYPE_RESEAU_REFERENTIEL_BIJECTION.items()}
        expected_type_reseau = inverse_bijection.get(value)
        if expected_type_reseau and self.type_reseau and self.type_reseau != expected_type_reseau:
            raise ValueError(
                f"Phase D-4 Tier 1 P1-1 violation : referentiel_tarifaire={value!r} incohérent avec "
                f"type_reseau={self.type_reseau!r} (attendu {expected_type_reseau})"
            )
        return value

    @validates("mode_releve_gaz")
    def _validate_mode_releve_gaz_strict(self, key: str, value: str | None):
        """Phase D-4 Tier 1 ADR-D-02 : `mode_releve_gaz` strict MM/MJ/JJ/MH."""
        if value is None or value == "":
            return value
        from .enums import ModeReleveGazEnum

        valid = {v.value for v in ModeReleveGazEnum}
        if value not in valid:
            raise ValueError(
                f"Phase D-4 Tier 1 violation : mode_releve_gaz={value!r} non canonique "
                f"(attendu {sorted(valid)} — ModeReleveGazEnum)"
            )
        return value

    @validates("accise_categorie_elec")
    def _validate_accise_categorie_elec_strict(self, key: str, value: str | None):
        """Phase D-4 Tier 1 ADR-D-05 : `accise_categorie_elec` strict CIBS L.312-36/37."""
        if value is None or value == "":
            return value
        from .enums import AcciseCategorieElec

        valid = {v.value for v in AcciseCategorieElec}
        if value not in valid:
            raise ValueError(
                f"Phase D-4 Tier 1 violation : accise_categorie_elec={value!r} non canonique "
                f"(attendu {sorted(valid)} — AcciseCategorieElec)"
            )
        return value

    @validates("cdc_pas_temporel_minutes")
    def _validate_cdc_pas_temporel(self, key: str, value: int | None):
        """P1-MATV1-028 Phase D-4 Tier 2 : pas CDC Enedis range CDC_PAS_MIN/MAX_MINUTES (doctrine).

        Valeurs courantes : 10 (CDC fine), 30 (CDC standard), 60 (relevé horaire).
        Bornes via doctrine.constants (P1-C audit code-reviewer Pilier 13 ADR-016).
        """
        if value is None:
            return value
        from doctrine.constants import CDC_PAS_MAX_MINUTES, CDC_PAS_MIN_MINUTES

        if not isinstance(value, int) or value < CDC_PAS_MIN_MINUTES or value > CDC_PAS_MAX_MINUTES:
            raise ValueError(
                f"Phase D-4 Tier 2 violation : cdc_pas_temporel_minutes={value!r} hors range "
                f"({CDC_PAS_MIN_MINUTES}-{CDC_PAS_MAX_MINUTES} min — doctrine.constants)"
            )
        return value

    @validates("pcs_kwh_par_nm3")
    def _validate_pcs_kwh_par_nm3(self, key: str, value: float | None):
        """P1-MATV1-033 Phase D-4 Tier 2 : PCS gaz plausibilité PCS_GAZ_MIN/MAX_KWH_NM3 (doctrine).

        Bornes via doctrine.constants (P1-C audit code-reviewer Pilier 13 ADR-016).
        """
        if value is None:
            return value
        from doctrine.constants import PCS_GAZ_MAX_KWH_NM3, PCS_GAZ_MIN_KWH_NM3

        if not isinstance(value, (int, float)) or value < PCS_GAZ_MIN_KWH_NM3 or value > PCS_GAZ_MAX_KWH_NM3:
            raise ValueError(
                f"Phase D-4 Tier 2 violation : pcs_kwh_par_nm3={value!r} hors range "
                f"({PCS_GAZ_MIN_KWH_NM3}-{PCS_GAZ_MAX_KWH_NM3} kWh/Nm³ — doctrine.constants)"
            )
        return value

    @validates("accise_categorie_gaz")
    def _validate_accise_categorie_gaz_strict(self, key: str, value: str | None):
        """Phase D-4 Tier 1 ADR-D-05 : `accise_categorie_gaz` strict CIBS L.312-24."""
        if value is None or value == "":
            return value
        from .enums import AcciseCategorieGaz

        valid = {v.value for v in AcciseCategorieGaz}
        if value not in valid:
            raise ValueError(
                f"Phase D-4 Tier 1 violation : accise_categorie_gaz={value!r} non canonique "
                f"(attendu {sorted(valid)} — AcciseCategorieGaz)"
            )
        return value

    @validates("gas_profile", "cja_mwh_per_day", "atrd_option", "est_profile")
    def _validate_gas_profile_consistency(self, key: str, value):
        """C95 + C97 matrice v1 §8.3 : cohérence options ATRD ↔ profil ↔ CJA.

        - C95 : si `atrd_option=T4` → CJA OBLIGATOIRE (capacité journalière contractuelle T4).
        - C97 : si `atrd_option ∈ (T1, T2, T3)` profilé → `gas_profile` REQUIS (BASE/B0/B1/B2I).
        - P1-2 fix code-reviewer Phase D-4 Tier 1 : cross-FK `est_profile` ↔ `atrd_option`
          (T1/T2/T3 → est_profile=True ou None, T4/TP → est_profile=False ou None).
        - DP gaz uniquement (energy_type=GAZ) — skipped sur DP élec.
        """
        if self.energy_type != DeliveryPointEnergyType.GAZ:
            return value

        atrd = value if key == "atrd_option" else self.atrd_option
        cja = value if key == "cja_mwh_per_day" else self.cja_mwh_per_day
        profile = value if key == "gas_profile" else self.gas_profile
        est_profile = value if key == "est_profile" else self.est_profile

        if atrd is None:
            return value

        atrd_str = atrd.value if hasattr(atrd, "value") else str(atrd)

        # P1-2 cross-FK : est_profile ↔ atrd_option (cohérence cardinale)
        if est_profile is not None:
            expected_profile = atrd_str in {"T1", "T2", "T3"}
            if est_profile != expected_profile:
                raise ValueError(
                    f"Phase D-4 Tier 1 P1-2 violation : est_profile={est_profile} incohérent avec "
                    f"atrd_option={atrd_str!r} (T1/T2/T3 → True / T4/TP → False)"
                )

        # C95 : T4 nécessite CJA contractuelle
        if atrd_str == "T4" and cja is None:
            raise ValueError(
                "C95 violation: atrd_option=T4 nécessite cja_mwh_per_day "
                "(Capacité Journalière Acheminement contractuelle obligatoire)"
            )

        # C97 : T1-T3 profilés nécessitent gas_profile
        if atrd_str in {"T1", "T2", "T3"} and profile is None:
            raise ValueError(
                f"C97 violation: atrd_option={atrd_str} (profilé) nécessite gas_profile (BASE/B0/B1/B2I/MODULANT)"
            )

        return value

    @validates("grd_code")
    def _validate_grd_energy_type_coherence(self, key: str, value: str | None):
        """C89-90 partiel matrice v1 §8.3 : `grd_code` ⟺ `energy_type`.

        Validation cross-FK heuristique : ENEDIS/RTE → elec, GRDF/Teréga/GRTgaz → gaz.
        ELD locales (Strasbourg/Régaz/etc.) tolérées (any energy_type).
        """
        if value is None or self.energy_type is None:
            return value
        expected = self._GRD_ENERGY_TYPE_MAP.get(value.upper())
        if expected is None:
            return value  # ELD locale ou code inconnu — pas de contrainte
        actual = self.energy_type.value if hasattr(self.energy_type, "value") else str(self.energy_type)
        if actual != expected:
            raise ValueError(
                f"C89-90 violation: grd_code={value!r} incompatible avec energy_type={actual!r} (attendu {expected!r})"
            )
        return value

    # Relations
    site = relationship("Site", back_populates="delivery_points")
    compteurs = relationship("Compteur", back_populates="delivery_point")
    tou_schedule = relationship("TOUSchedule", foreign_keys=[tou_schedule_id])
