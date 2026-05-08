"""
PROMEOS - Modèle Site
Coeur du domaine : site de consommation énergétique
"""

from sqlalchemy import JSON, Boolean, Column, Date, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, validates
from .base import Base, TimestampMixin, SoftDeleteMixin
from .enums import (
    AperCategorieTailleEnum,
    AperExemptionMotifEnum,
    OperatModulationMotifEnum,
    OperatPalierAltitudeEnum,
    OperatStatus,
    OperatUsagePrincipalEnum,
    OperatZoneClimatiqueEnum,
    ParkingType,
    StatutConformite,
    TypeSite,
)


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
    # Sprint C-7 Phase 7.1 (clôture D-Phase4-2-Operat-Surfaces-3-Distinct-001 P0 historique)
    # Surface CE (Surface des Consommations Énergétiques) — Arrêté 10/04/2020 art. 2-j
    # (NOR LOGL2005904A v15/03/2024) : "surface sur laquelle l'ensemble des consommations
    # énergétiques sont prises en compte, intégrant notamment les surfaces de stationnement
    # intérieur et de locaux techniques de l'entité fonctionnelle, au contraire de la
    # surface de plancher [SDP]".
    # 3 surfaces distinctes Site cardinal :
    # - surface_m2 = SDP (Surface De Plancher) — Code construction art. R111-22
    # - tertiaire_area_m2 = surface tertiaire assujettie OPERAT (sous-périmètre SDP)
    # - s_ce_m2 = Surface CE OPERAT (typiquement > SDP, inclut parking intérieur + locaux techniques)
    s_ce_m2 = Column(
        Float, nullable=True, comment="Surface CE OPERAT (Arrêté 10/04/2020 art. 2-j) — distincte SDP/tertiaire"
    )
    roof_area_m2 = Column(Float, nullable=True, comment="Surface toiture (m2)")
    parking_area_m2 = Column(Float, nullable=True, comment="Surface parking (m2)")
    parking_type = Column(Enum(ParkingType), nullable=True, comment="Type de parking")
    is_multi_occupied = Column(Boolean, default=False, comment="Site multi-occupant")
    operat_status = Column(Enum(OperatStatus), nullable=True, comment="Statut OPERAT")
    operat_last_submission_year = Column(Integer, nullable=True, comment="Derniere annee de declaration OPERAT")
    annual_kwh_total = Column(Float, nullable=True, comment="Consommation annuelle totale (kWh)")
    last_energy_update_at = Column(DateTime, nullable=True, comment="Derniere MAJ donnees energie")

    # Sprint C-2 Phase 4.2 — intensité énergétique persistée (matrice v1 §4.4.F #56)
    # Persistées par site_intensity_service.persist_site_intensities() ;
    # recalculées via cascade_recompute_service sur changement de
    # annual_kwh_total / surface_m2 / tertiaire_area_m2.
    intensity_kwh_m2_total = Column(
        Float,
        nullable=True,
        comment="Intensité énergétique = annual_kwh_total / surface_m2 (UI legacy, compat L825/L1528 Patrimoine.jsx)",
    )
    intensity_kwh_m2_tertiaire = Column(
        Float,
        nullable=True,
        comment="Intensité énergétique = annual_kwh_total / tertiaire_area_m2 (doctrine OPERAT/DT)",
    )

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

    # ─── OPERAT/EFA — matrice v1 §4.4.C (Sprint C-1 Phase 3, 13 champs OPERAT + 1 EFA) ───
    # Source primaire : Arrêté 10/04/2020 NOR LOGL2005904A modifié par
    # arrêté 01/08/2025 NOR ATDL2430864A (consolidé 07/09/2025).
    #
    # Tous nullable=True : les sites existants n'ont pas ces données ; la cascade
    # de calcul les remplit progressivement (Sprint C-1 Phase 6 cascade_recompute).
    # native_enum=False : SQLite reçoit un CHECK constraint, PostgreSQL un type ENUM
    # natif (compatibilité roadmap).

    operat_zone_climatique = Column(
        Enum(OperatZoneClimatiqueEnum, native_enum=False),
        nullable=True,
        comment="Matrice v1 §4.4.C #25 — Zone climatique OPERAT (résolue depuis code_postal/altitude)",
    )
    operat_palier_altitude = Column(
        Enum(OperatPalierAltitudeEnum, native_enum=False),
        nullable=True,
        comment="Matrice v1 §4.4.C #26 — Palier altitude OPERAT (5 paliers stricts Annexe I)",
    )
    altitude_m = Column(
        Integer,
        nullable=True,
        comment="Matrice v1 §4.4.C #27 — Altitude en mètres (input pour résoudre operat_palier_altitude)",
    )
    operat_sous_categorie_id = Column(
        String(50),
        nullable=True,
        comment="Matrice v1 §4.4.C #28 — Identifiant sous-catégorie OPERAT (parmi 426 Annexe I)",
    )
    operat_iiu_temporels = Column(
        JSON,
        nullable=True,
        default=dict,
        comment="Matrice v1 §4.4.C #29 — Indicateurs Intensité Usage temporels (heures/jours)",
    )
    operat_iiu_surfaciques = Column(
        JSON,
        nullable=True,
        default=dict,
        comment="Matrice v1 §4.4.C #30 — Indicateurs Intensité Usage surfaciques (m²)",
    )
    cabs_kwh_m2_an = Column(
        Float,
        nullable=True,
        comment="Matrice v1 §4.4.C #31 — Cabs 2030 calculé via OperatValeursAbsoluesService (kWh/m²/an)",
    )
    crelat_kwh_m2_an = Column(
        Float,
        nullable=True,
        comment="Matrice v1 §4.4.C — Crelat (objectif relatif) calculé alternativement à Cabs (kWh/m²/an)",
    )
    usage_principal = Column(
        Enum(OperatUsagePrincipalEnum, native_enum=False),
        nullable=True,
        comment="Matrice v1 §4.4.C #32 — Usage principal du site (catégorie macro OPERAT)",
    )
    efa_id = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Matrice v1 §4.4.G — Identifiant EFA (Entité Fonctionnelle Assujettie OPERAT)",
    )
    annee_reference_operat = Column(
        Integer,
        nullable=True,
        comment="Matrice v1 §4.4.C #33 — Année de référence OPERAT (entre 2010 et 2022)",
    )

    # Phase D-0 hotfix — D-Audit-PARAM-Site-Cat-Operat-Mode-Propriete-005 P0 :
    # 2 champs Section 9.1 P0 MVP cardinaux ajoutés (matrice v1 §4.4 cible).
    # `categorie_operat_principale` = catégorie macro OPERAT (vs `operat_sous_categorie_id`
    # 426 sous-catégories Annexe I). `mode_propriete` = trace cardinale assujettissement DT.
    categorie_operat_principale = Column(
        String(50),
        nullable=True,
        comment="Matrice v1 §4.4 — Catégorie OPERAT macro (Bureaux/Commerce/Enseignement/Santé/etc.)",
    )
    mode_propriete = Column(
        String(20),
        nullable=True,
        comment="Matrice v1 §4.4 — Mode propriété (proprietaire/locataire/syndic) — trace assujettissement DT",
    )
    methode_modulation_dt = Column(
        Enum(OperatModulationMotifEnum, native_enum=False),
        nullable=True,
        comment="Matrice v1 §4.4.C #34 — Motif de modulation DT (4 motifs officiels art. 12)",
    )
    dossier_modulation_id = Column(
        String(50),
        nullable=True,
        comment="Matrice v1 §4.4.C #35 — ID dossier de modulation déposé (avant 30/09/2026)",
    )

    # ─── APER — matrice v1 §4.4.D (Sprint C-1 Phase 3, 5 champs) ───
    # Source primaire : Loi 2023-175 art. 40 + Décret 2024-1023.
    # parking_area_m2 + parking_type existent déjà (champs antérieurs).

    aper_assujetti = Column(
        Boolean,
        nullable=True,
        comment="Matrice v1 §4.4.D #37 — Site assujetti APER (calculé via parking_area_m2 ≥ 1500, cascade Phase 6)",
    )
    aper_categorie_taille = Column(
        Enum(AperCategorieTailleEnum, native_enum=False),
        nullable=True,
        comment="Matrice v1 §4.4.D #38 — SMALL (1500-10000) ou LARGE (>10000) m²",
    )
    aper_deadline = Column(
        Date,
        nullable=True,
        comment="Matrice v1 §4.4.D #39 — Échéance APER (01/07/2026 LARGE, 01/07/2028 SMALL)",
    )
    parking_solar_pct_engaged = Column(
        Float,
        nullable=True,
        comment="Matrice v1 §4.4.D #40 — Pourcentage parking engagé en solarisation (0-100)",
    )
    aper_exemption_motif = Column(
        Enum(AperExemptionMotifEnum, native_enum=False),
        nullable=True,
        comment="Matrice v1 §4.4.D #41 — Motif d'exemption APER si applicable",
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

    # Phase D-4 Tier 1 — P0-MATV1-004 + P0-MATV1-005 cardinaux RGPD + BACS cascade
    # Audit : docs/audits/AUDIT_ECARTS_MATRICE_V1_2026_05_07.md §3 P0-MATV1-004/005.

    # P0-004 — Cascade RGPD §6.1 surcharge locale Org → Site (3 valeurs)
    # ADR-007 ext : herite_entite / accepte_local / refuse_local
    consentement_site_overrides = Column(
        JSON,
        nullable=True,
        comment="JSON cascade RGPD Org→Site override (matrice v1 §4.4.H#67 — herite_entite/accepte_local/refuse_local)",
    )

    # P0-005 — BACS Site agrégé (ADR-D-04 cascade Σ Batiment.cvc_power_kw)
    # Source : Décret BACS 2020-887 + 2025-1343 (seuils 70/290 kW).
    bacs_assujetti = Column(
        Boolean,
        nullable=True,
        comment="Site assujetti BACS (puissance_cvc_totale_kw ≥ 70 kW) — matrice v1 §4.4.E#42 ADR-D-04",
    )
    bacs_puissance_cvc_totale_kw = Column(
        Float,
        nullable=True,
        comment="Puissance CVC totale Site (Σ Batiment.cvc_power_kw — cascade ADR-D-04) — matrice v1 §4.4.E#43",
    )

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

    # ─── Phase D-3 Tier 2 DOC-1 — String→Enum validators (Pilier 9 ADR-016) ───

    @validates("categorie_operat_principale")
    def _validate_categorie_operat_principale_strict(self, key: str, value: str | None):
        """P1 fix Phase D-4 Tier 4 audit code-reviewer : Site.categorie_operat_principale strict.

        Réutilise `OperatUsagePrincipalEnum` (9 catégories OPERAT macro). Pattern Pilier 9 ADR-016.
        Cohérent Batiment.categorie_operat_batiment validator (anti-divergence Site/Bâtiment).
        """
        if value is None or value == "":
            return value
        from .enums import OperatUsagePrincipalEnum

        valid = {v.value for v in OperatUsagePrincipalEnum}
        if value not in valid:
            raise ValueError(
                f"Phase D-4 Tier 4 violation : categorie_operat_principale={value!r} non canonique "
                f"(attendu {sorted(valid)} — OperatUsagePrincipalEnum 9 catégories macro)"
            )
        return value

    @validates("mode_propriete")
    def _validate_mode_propriete_strict(self, key: str, value: str | None):
        """DOC-1 Phase D-3 Tier 2 : `mode_propriete` réutilise `EfaRole` Enum existant.

        Valeurs canoniques : PROPRIETAIRE / LOCATAIRE / MANDATAIRE.
        Pattern Pilier 9 ADR-016 — String reste, validator runtime exige Enum value.
        """
        if value is None or value == "":
            return value
        from .enums import EfaRole

        valid = {v.value for v in EfaRole}
        if value not in valid:
            raise ValueError(
                f"DOC-1 Phase D-3 Tier 2 violation : mode_propriete={value!r} non canonique "
                f"(attendu {sorted(valid)} — EfaRole)"
            )
        return value

    def __repr__(self):
        return f"<Site {self.id}: {self.nom} ({self.type.value})>"
