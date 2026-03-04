"""
PROMEOS - Script de génération de données (seed)
Architecture complète : Organisation → Portefeuille → Sites → Bâtiments → Compteurs
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from models import (
    Base,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Batiment,
    Usage,
    TypeUsage,
    Compteur,
    Consommation,
    Obligation,
    StatutConformite,
    TypeObligation,
    Alerte,
    SeveriteAlerte,
    TypeSite,
    TypeCompteur,
    Evidence,
    TypeEvidence,
    StatutEvidence,
    # RegOps models
    DataPoint,
    RegAssessment,
    JobOutbox,
    RegSourceEvent,
    ParkingType,
    OperatStatus,
    EnergyVector,
    SourceType,
    JobType,
    JobStatus,
    # Sprint 9: Compliance workflow
    ComplianceFinding,
    ComplianceRunBatch,
    InsightStatus,
    # IAM
    User,
    UserOrgRole,
    UserScope,
    AuditLog,
    UserRole,
    ScopeLevel,
)
from database import engine, SessionLocal

# Données de référence France
VILLES_FRANCE = [
    {"nom": "Paris", "region": "Île-de-France"},
    {"nom": "Marseille", "region": "Provence-Alpes-Côte d'Azur"},
    {"nom": "Lyon", "region": "Auvergne-Rhône-Alpes"},
    {"nom": "Toulouse", "region": "Occitanie"},
    {"nom": "Nice", "region": "Provence-Alpes-Côte d'Azur"},
    {"nom": "Nantes", "region": "Pays de la Loire"},
    {"nom": "Montpellier", "region": "Occitanie"},
    {"nom": "Strasbourg", "region": "Grand Est"},
    {"nom": "Bordeaux", "region": "Nouvelle-Aquitaine"},
    {"nom": "Lille", "region": "Hauts-de-France"},
    {"nom": "Rennes", "region": "Bretagne"},
    {"nom": "Reims", "region": "Grand Est"},
    {"nom": "Saint-Étienne", "region": "Auvergne-Rhône-Alpes"},
    {"nom": "Toulon", "region": "Provence-Alpes-Côte d'Azur"},
    {"nom": "Grenoble", "region": "Auvergne-Rhône-Alpes"},
    {"nom": "Dijon", "region": "Bourgogne-Franche-Comté"},
    {"nom": "Angers", "region": "Pays de la Loire"},
    {"nom": "Nîmes", "region": "Occitanie"},
    {"nom": "Aix-en-Provence", "region": "Provence-Alpes-Côte d'Azur"},
    {"nom": "Brest", "region": "Bretagne"},
]

ENTREPRISES = [
    {"nom": "Bouygues", "secteur": "retail"},
    {"nom": "Carrefour", "secteur": "retail"},
    {"nom": "Casino", "secteur": "retail"},
    {"nom": "Auchan", "secteur": "retail"},
    {"nom": "EDF", "secteur": "industrie"},
    {"nom": "Total", "secteur": "industrie"},
    {"nom": "Renault", "secteur": "industrie"},
    {"nom": "PSA", "secteur": "industrie"},
    {"nom": "Orange", "secteur": "tertiaire"},
    {"nom": "SFR", "secteur": "tertiaire"},
    {"nom": "BNP", "secteur": "tertiaire"},
    {"nom": "Accor", "secteur": "hotel"},
]


def create_organisation_hierarchy(db: Session):
    """Créer hiérarchie Organisation -> EntiteJuridique -> Portefeuille"""
    print("  Création de l'organisation...")

    # Organisation principale
    org = Organisation(nom="Groupe Casino", type_client="retail", actif=True)
    db.add(org)
    db.commit()
    db.refresh(org)

    # Entité juridique
    entite = EntiteJuridique(organisation_id=org.id, nom="Casino France SAS", siren="554008671", siret="55400867100013")
    db.add(entite)
    db.commit()
    db.refresh(entite)

    # 3 Portefeuilles
    portefeuilles = []
    for nom_region, desc in [
        ("Retail IDF", "Magasins Île-de-France"),
        ("Retail Sud", "Magasins Sud de la France"),
        ("Bureaux & Logistique", "Sites administratifs et entrepôts"),
    ]:
        p = Portefeuille(entite_juridique_id=entite.id, nom=nom_region, description=desc)
        db.add(p)
        portefeuilles.append(p)

    db.commit()
    for p in portefeuilles:
        db.refresh(p)

    print(f"  Organisation créée : {org.nom} avec {len(portefeuilles)} portefeuilles")
    return org, entite, portefeuilles


def create_sites(db: Session, portefeuilles: list):
    """Créer 120 sites répartis dans 3 portefeuilles"""
    print("  Création de 120 sites...")

    sites = []
    compteur_global = 1

    for i in range(120):
        # Choix portefeuille (70% retail IDF/Sud, 30% bureaux)
        if i < 50:
            portefeuille = portefeuilles[0]  # IDF
            type_site = TypeSite.MAGASIN
        elif i < 90:
            portefeuille = portefeuilles[1]  # Sud
            type_site = TypeSite.MAGASIN
        else:
            portefeuille = portefeuilles[2]  # Bureaux
            type_site = random.choice([TypeSite.BUREAU, TypeSite.USINE])

        # Ville aléatoire
        ville = random.choice(VILLES_FRANCE)
        entreprise = random.choice(ENTREPRISES)

        # Generate RegOps business fields
        surface_m2 = random.randint(800, 5000)

        # SIRET (14 digits: 9-digit SIREN + 5-digit NIC)
        siret = f"{random.randint(100000000, 999999999)}{random.randint(10000, 99999)}"

        # Tertiaire area (for OPERAT) - same as surface for MAGASIN/BUREAU, null for USINE
        if type_site in [TypeSite.MAGASIN, TypeSite.BUREAU]:
            tertiaire_area_m2 = surface_m2
        else:
            tertiaire_area_m2 = None if random.random() < 0.3 else surface_m2 * 0.5

        # Parking area (60% have outdoor parking)
        if random.random() < 0.60:
            parking_area_m2 = random.uniform(500, 15000)
            parking_type = random.choice(
                [ParkingType.OUTDOOR, ParkingType.INDOOR, ParkingType.UNDERGROUND, ParkingType.SILO]
            )
        else:
            parking_area_m2 = None
            parking_type = ParkingType.UNKNOWN

        # Roof area (50-80% of surface for single-story, less for multi-story)
        roof_area_m2 = surface_m2 * random.uniform(0.50, 0.80) if type_site == TypeSite.MAGASIN else surface_m2 * 0.3

        # Multi-occupancy (15% of sites)
        is_multi_occupied = random.random() < 0.15

        # OPERAT status distribution
        operat_status = random.choices(
            [OperatStatus.NOT_STARTED, OperatStatus.IN_PROGRESS, OperatStatus.SUBMITTED, OperatStatus.VERIFIED],
            weights=[20, 40, 30, 10],
        )[0]

        # Last submission year
        operat_last_submission_year = (
            random.choice([2023, 2024]) if operat_status in [OperatStatus.SUBMITTED, OperatStatus.VERIFIED] else None
        )

        # Annual kWh estimate (150-250 kWh/m2 for retail, 100-180 for office)
        if type_site == TypeSite.MAGASIN:
            kwh_per_m2 = random.uniform(150, 250)
        else:
            kwh_per_m2 = random.uniform(100, 180)
        annual_kwh_total = surface_m2 * kwh_per_m2

        site = Site(
            portefeuille_id=portefeuille.id,
            nom=f"{entreprise['nom']} {ville['nom']} #{compteur_global}",
            type=type_site,
            adresse=f"{random.randint(1, 200)} rue de la {random.choice(['Gare', 'République', 'Liberté', 'Paix'])}",
            ville=ville["nom"],
            code_postal=f"{random.randint(10, 95):02d}{random.randint(100, 999)}",
            region=ville["region"],
            surface_m2=surface_m2,
            latitude=random.uniform(43.0, 49.0),
            longitude=random.uniform(-1.5, 7.5),
            actif=True,
            anomalie_facture=(random.random() < 0.15),
            # RegOps business fields
            siret=siret,
            tertiaire_area_m2=tertiaire_area_m2,
            parking_area_m2=parking_area_m2,
            parking_type=parking_type,
            roof_area_m2=roof_area_m2,
            is_multi_occupied=is_multi_occupied,
            operat_status=operat_status,
            operat_last_submission_year=operat_last_submission_year,
            annual_kwh_total=annual_kwh_total,
            last_energy_update_at=datetime.now() - timedelta(days=random.randint(1, 30)),
            # Compliance snapshot fields computed by engine after obligations
        )

        db.add(site)
        sites.append(site)
        compteur_global += 1

    db.commit()
    for s in sites:
        db.refresh(s)

    print(f"  {len(sites)} sites créés")
    return sites


def _estimate_cvc_power(type_site, surface_m2):
    """Puissance CVC réaliste (kW) selon type de site et surface.

    Ratios typiques France :
    - Magasin/retail : 80-120 W/m² (froid alimentaire + CVC)
    - Bureau         : 40-70 W/m²
    - Usine          : 30-60 W/m² (process exclu, CVC seul)
    - Entrepôt       : 20-40 W/m²
    """
    ratios = {
        TypeSite.MAGASIN: (80, 120),
        TypeSite.BUREAU: (40, 70),
        TypeSite.USINE: (30, 60),
        TypeSite.ENTREPOT: (20, 40),
    }
    lo, hi = ratios.get(type_site, (40, 70))
    watt_per_m2 = random.uniform(lo, hi)
    return round(surface_m2 * watt_per_m2 / 1000, 1)  # W -> kW


def create_batiments_usages(db: Session, sites: list):
    """Créer bâtiments et usages avec puissance CVC réaliste"""
    print("  Création des bâtiments et usages...")

    batiments = []
    for idx, site in enumerate(sites):
        cvc_kw = _estimate_cvc_power(site.type, site.surface_m2)

        # Forcer quelques sites > 290 kW pour avoir des cas BACS seuil haut
        if idx < 15:
            cvc_kw = max(cvc_kw, random.uniform(300, 600))

        bat = Batiment(
            site_id=site.id,
            nom="Bâtiment principal",
            surface_m2=site.surface_m2,
            annee_construction=random.randint(1980, 2020),
            cvc_power_kw=round(cvc_kw, 1),
        )
        db.add(bat)
        batiments.append(bat)

    db.commit()
    for b in batiments:
        db.refresh(b)

        # 2-3 usages par bâtiment
        nb_usages = random.randint(2, 3)
        usages_types = random.sample(list(TypeUsage), nb_usages)

        for usage_type in usages_types:
            usage = Usage(batiment_id=b.id, type=usage_type, description=f"Usage {usage_type.value}")
            db.add(usage)

    db.commit()
    print(f"  {len(batiments)} bâtiments créés avec usages")
    return batiments


def create_obligations(db: Session, sites: list, batiments: list):
    """Créer obligations réglementaires basées sur cvc_power_kw réel"""
    print("  Création des obligations...")
    from services.compliance_engine import bacs_deadline_for_power, BACS_SEUIL_HAUT

    # Build site_id -> batiment lookup
    bat_by_site = {b.site_id: b for b in batiments}
    nb_bacs = 0

    for site in sites:
        # Obligation Décret Tertiaire (tous les sites tertiaires)
        statut_tertiaire = random.choices(
            [StatutConformite.CONFORME, StatutConformite.A_RISQUE, StatutConformite.NON_CONFORME], weights=[30, 50, 20]
        )[0]

        obl_tertiaire = Obligation(
            site_id=site.id,
            type=TypeObligation.DECRET_TERTIAIRE,
            description="Réduction -40% en 2030 vs 2010",
            echeance=datetime(2030, 12, 31).date(),
            statut=statut_tertiaire,
            avancement_pct=random.uniform(20, 85),
        )
        db.add(obl_tertiaire)

        # Obligation BACS si CVC > 70 kW
        bat = bat_by_site.get(site.id)
        if bat and bat.cvc_power_kw:
            deadline = bacs_deadline_for_power(bat.cvc_power_kw)
            if deadline:
                seuil_label = ">290 kW" if bat.cvc_power_kw > BACS_SEUIL_HAUT else ">70 kW"
                obl_bacs = Obligation(
                    site_id=site.id,
                    type=TypeObligation.BACS,
                    description=f"GTB/GTC obligatoire {seuil_label} (CVC {bat.cvc_power_kw} kW)",
                    echeance=deadline,
                    statut=StatutConformite.A_RISQUE,  # placeholder, engine recomputes
                    avancement_pct=random.uniform(30, 100),
                )
                db.add(obl_bacs)
                nb_bacs += 1

    db.commit()
    print(f"  Obligations créées ({nb_bacs} BACS sur {len(sites)} sites)")


def create_compteurs_consommations(db: Session, sites: list):
    """Créer compteurs et consommations (simplifié)"""
    print("  Création compteurs et consommations...")

    compteurs = []
    for site in sites[:30]:  # Seulement 30 sites avec compteurs pour accélérer
        # 1-2 compteurs par site
        nb_compteurs = random.randint(1, 2)

        for i in range(nb_compteurs):
            type_compteur = TypeCompteur.ELECTRICITE if i == 0 else random.choice(list(TypeCompteur))

            # Generate meter_id (14 digits) and energy_vector
            meter_id = f"{random.randint(10000000000000, 99999999999999)}"
            if type_compteur == TypeCompteur.ELECTRICITE:
                energy_vector = EnergyVector.ELECTRICITY
            elif type_compteur == TypeCompteur.GAZ:
                energy_vector = EnergyVector.GAS
            else:
                energy_vector = EnergyVector.OTHER

            compteur = Compteur(
                site_id=site.id,
                numero_serie=f"PRM{random.randint(100000000000, 999999999999)}",
                type=type_compteur,
                puissance_souscrite_kw=random.choice([36, 60, 90, 120, 150])
                if type_compteur == TypeCompteur.ELECTRICITE
                else None,
                actif=True,
                meter_id=meter_id,
                energy_vector=energy_vector,
            )
            db.add(compteur)
            compteurs.append(compteur)

    db.commit()
    for c in compteurs:
        db.refresh(c)

    # Générer consommations (7 derniers jours)
    print("  Génération consommations...")
    now = datetime.now()

    for compteur in compteurs:
        for day in range(7):
            date_conso = now - timedelta(days=day)

            # Profil journalier simplifié
            for hour in range(24):
                timestamp = date_conso.replace(hour=hour, minute=0, second=0, microsecond=0)

                # Consommation variable selon l'heure (jour/nuit)
                if 8 <= hour <= 19:
                    valeur = random.uniform(50, 150)  # kWh jour
                    cout = valeur * 0.15
                else:
                    valeur = random.uniform(10, 30)  # kWh nuit
                    cout = valeur * 0.12

                conso = Consommation(
                    compteur_id=compteur.id, timestamp=timestamp, valeur=round(valeur, 2), cout_euro=round(cout, 2)
                )
                db.add(conso)

    db.commit()
    print(f"  {len(compteurs)} compteurs avec consommations 7j")


def create_evidences(db: Session, sites: list, batiments: list):
    """Créer evidences de conformité dont BACS-spécifiques"""
    print("  Création des evidences...")
    from services.compliance_engine import bacs_deadline_for_power

    bat_by_site = {b.site_id: b for b in batiments}

    EVIDENCE_TEMPLATES = [
        (TypeEvidence.AUDIT, "Audit énergétique réglementaire"),
        (TypeEvidence.CERTIFICAT, "Certificat de performance énergétique"),
        (TypeEvidence.RAPPORT, "Rapport annuel décret tertiaire"),
        (TypeEvidence.FACTURE, "Facture fournisseur énergie"),
        (TypeEvidence.DECLARATION, "Déclaration OPERAT"),
    ]

    nb_evidences = 0
    for site in sites:
        site_manquant = random.random() < 0.20  # 20% sites avec données manquantes

        # Evidences génériques
        for ev_type, note_base in EVIDENCE_TEMPLATES:
            if random.random() < 0.15:
                continue

            if site_manquant and random.random() < 0.5:
                status = StatutEvidence.MANQUANT
                note = f"{note_base} - Document non fourni"
            else:
                status = random.choices(
                    [StatutEvidence.VALIDE, StatutEvidence.EN_ATTENTE, StatutEvidence.EXPIRE], weights=[60, 25, 15]
                )[0]
                note = note_base

            db.add(Evidence(site_id=site.id, type=ev_type, statut=status, note=note))
            nb_evidences += 1

        # Evidences BACS (si site concerné)
        bat = bat_by_site.get(site.id)
        if bat and bat.cvc_power_kw and bacs_deadline_for_power(bat.cvc_power_kw):
            # Attestation BACS : 40% valide, 30% en_attente, 20% manquant, 10% expiré
            att_status = random.choices(
                [StatutEvidence.VALIDE, StatutEvidence.EN_ATTENTE, StatutEvidence.MANQUANT, StatutEvidence.EXPIRE],
                weights=[40, 30, 20, 10],
            )[0]
            db.add(
                Evidence(
                    site_id=site.id,
                    type=TypeEvidence.ATTESTATION_BACS,
                    statut=att_status,
                    note=f"Attestation conformité GTB/GTC ({bat.cvc_power_kw} kW)",
                )
            )
            nb_evidences += 1

            # Dérogation BACS : 10% des sites concernés ont une dérogation valide
            if random.random() < 0.10:
                db.add(
                    Evidence(
                        site_id=site.id,
                        type=TypeEvidence.DEROGATION_BACS,
                        statut=StatutEvidence.VALIDE,
                        note="Dérogation BACS accordée (bâtiment classé / démolition prévue)",
                    )
                )
                nb_evidences += 1

    db.commit()
    print(f"  {nb_evidences} evidences créées")


def create_alertes(db: Session, sites: list):
    """Créer 20 alertes actives"""
    print("  Création de 20 alertes...")

    sites_avec_problemes = [
        s
        for s in sites
        if s.statut_decret_tertiaire == StatutConformite.NON_CONFORME
        or s.statut_bacs == StatutConformite.NON_CONFORME
        or s.anomalie_facture
    ]

    now = datetime.now()

    for site in sites_avec_problemes[:20]:
        if site.statut_bacs == StatutConformite.NON_CONFORME:
            titre = f"BACS non conforme - {site.nom}"
            description = "Système >290 kW sans GTB/GTC conforme"
            severite = SeveriteAlerte.CRITICAL
        elif site.anomalie_facture:
            titre = f"Anomalie facture - {site.nom}"
            description = "Écart >20% entre conso et facture"
            severite = SeveriteAlerte.WARNING
        else:
            titre = f"Décret tertiaire KO - {site.nom}"
            description = "Trajectoire 2030 compromise"
            severite = SeveriteAlerte.WARNING

        alerte = Alerte(
            site_id=site.id,
            titre=titre,
            description=description,
            severite=severite,
            timestamp=now - timedelta(days=random.randint(0, 14)),
            resolue=False,
        )
        db.add(alerte)

    db.commit()
    print("  20 alertes créées")


def create_datapoints(db: Session, sites: list):
    """Créer ~50 DataPoints (agrégats mensuels RTE, météo, PVGIS)"""
    print("  Création de DataPoints...")

    now = datetime.now()
    datapoints = []

    # Sample 10 sites for DataPoint creation
    sample_sites = random.sample(sites, min(10, len(sites)))

    for site in sample_sites:
        # Monthly grid CO2 intensity from RTE (5 months history)
        for month_ago in range(5):
            ts_start = now - timedelta(days=30 * (month_ago + 1))
            ts_end = now - timedelta(days=30 * month_ago)

            dp = DataPoint(
                object_type="site",
                object_id=site.id,
                metric="grid_co2_intensity",
                ts_start=ts_start,
                ts_end=ts_end,
                value=round(random.uniform(50, 120), 2),  # gCO2/kWh
                unit="gCO2/kWh",
                source_type=SourceType.API,
                source_name="rte_eco2mix",
                quality_score=0.95,
                coverage_ratio=1.0,
                retrieved_at=now,
                source_ref="https://odre.opendatasoft.com/api/records/1.0/search/?dataset=eco2mix-national-tr",
            )
            db.add(dp)
            datapoints.append(dp)

        # PV production estimate from PVGIS (if has roof)
        if site.roof_area_m2 and site.roof_area_m2 > 500:
            dp = DataPoint(
                object_type="site",
                object_id=site.id,
                metric="pv_prod_estimate_kwh",
                ts_start=now - timedelta(days=365),
                ts_end=now,
                value=round(site.roof_area_m2 * 0.15 * 1100, 2),  # 15% efficiency, 1100 kWh/kWp/year
                unit="kWh/year",
                source_type=SourceType.API,
                source_name="pvgis",
                quality_score=0.85,
                coverage_ratio=1.0,
                retrieved_at=now,
                source_ref=f"https://re.jrc.ec.europa.eu/api/seriescalc?lat={site.latitude}&lon={site.longitude}",
            )
            db.add(dp)
            datapoints.append(dp)

    db.commit()
    print(f"  {len(datapoints)} DataPoints créés")


def create_reg_source_events(db: Session):
    """Créer 4 RegSourceEvents (sample regulatory news)"""
    print("  Création de RegSourceEvents...")

    import hashlib

    events_data = [
        {
            "source_name": "legifrance_rss",
            "title": "Décret n° 2024-123 modifiant le décret tertiaire",
            "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000024123456",
            "snippet": "Le décret du 23 juillet 2019 relatif aux obligations d'actions de réduction de la consommation d'énergie finale dans les bâtiments à usage tertiaire est modifié comme suit : Article 1 - Les seuils d'application sont précisés pour tenir compte des surfaces de stationnement couvertes...",
            "tags": ["energie", "tertiaire", "decret"],
            "published_at": datetime(2024, 1, 15).date(),
        },
        {
            "source_name": "cre_watcher",
            "title": "Délibération CRE sur les tarifs d'utilisation des réseaux publics d'électricité",
            "url": "https://www.cre.fr/Documents/Deliberations/Decision/turpe-6-2024",
            "snippet": "La Commission de régulation de l'énergie décide d'une évolution tarifaire de 9,8% au 1er février 2024. Cette hausse reflète l'augmentation des coûts d'exploitation des gestionnaires de réseaux et les investissements nécessaires à la transition énergétique...",
            "tags": ["tarif", "electricite", "turpe"],
            "published_at": datetime(2024, 1, 20).date(),
        },
        {
            "source_name": "rte_watcher",
            "title": "Bilan électrique 2023 : consommation en baisse, énergies renouvelables en hausse",
            "url": "https://www.rte-france.com/actualites/bilan-electrique-2023",
            "snippet": "RTE publie son bilan électrique annuel. La consommation d'électricité en France a baissé de 3,2% en 2023 par rapport à 2022. Les énergies renouvelables représentent désormais 27% de la production d'électricité, en hausse de 2 points...",
            "tags": ["bilan", "production", "renouvelables"],
            "published_at": datetime(2024, 1, 25).date(),
        },
        {
            "source_name": "legifrance_rss",
            "title": "Arrêté relatif aux installations de recharge pour véhicules électriques",
            "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000024987654",
            "snippet": "Les parkings de plus de 20 places doivent être équipés d'au moins un point de recharge pour véhicules électriques pour 20 emplacements. Cette obligation s'applique aux bâtiments neufs et aux rénovations lourdes...",
            "tags": ["parking", "irve", "mobilite"],
            "published_at": datetime(2024, 2, 1).date(),
        },
    ]

    for event_data in events_data:
        content_hash = hashlib.sha256(f"{event_data['title']}|{event_data['url']}".encode()).hexdigest()

        # Convert tags list to comma-separated string
        tags_str = ",".join(event_data["tags"]) if event_data["tags"] else None

        event = RegSourceEvent(
            source_name=event_data["source_name"],
            title=event_data["title"],
            url=event_data["url"],
            content_hash=content_hash,
            snippet=event_data["snippet"],
            tags=tags_str,
            published_at=event_data["published_at"],
            retrieved_at=datetime.now(),
            reviewed=random.choice([True, False]),
            review_note="Pertinent pour OPERAT" if random.random() < 0.5 else None,
        )
        db.add(event)

    db.commit()
    print(f"  {len(events_data)} RegSourceEvents créés")


def run_regops_assessments(db: Session, sites: list):
    """Run RegOps engine to populate RegAssessments"""
    print("  Exécution RegOps engine...")

    from regops.engine import evaluate_batch, persist_assessment

    # Run batch evaluation
    site_ids = [s.id for s in sites]
    summaries = evaluate_batch(db, site_ids)

    # Persist assessments
    for summary in summaries:
        persist_assessment(db, summary)

    db.commit()
    print(f"  {len(summaries)} RegAssessments créés")


def create_sample_jobs(db: Session):
    """Créer quelques jobs terminés pour l'historique"""
    print("  Création de jobs historiques...")

    import json

    jobs_data = [
        {
            "job_type": JobType.RECOMPUTE_ASSESSMENT,
            "payload_json": json.dumps({"scope": "site", "site_id": 1}),
            "status": JobStatus.DONE,
            "priority": 10,
            "created_at": datetime.now() - timedelta(hours=2),
            "started_at": datetime.now() - timedelta(hours=2, minutes=-1),
            "finished_at": datetime.now() - timedelta(hours=2, minutes=-2),
            "error": None,
        },
        {
            "job_type": JobType.SYNC_CONNECTOR,
            "payload_json": json.dumps({"connector": "rte_eco2mix", "object_type": "site", "object_id": 5}),
            "status": JobStatus.DONE,
            "priority": 5,
            "created_at": datetime.now() - timedelta(hours=1),
            "started_at": datetime.now() - timedelta(hours=1, minutes=-1),
            "finished_at": datetime.now() - timedelta(hours=1, minutes=-3),
            "error": None,
        },
        {
            "job_type": JobType.RUN_WATCHER,
            "payload_json": json.dumps({"watcher": "legifrance_watcher"}),
            "status": JobStatus.FAILED,
            "priority": 3,
            "created_at": datetime.now() - timedelta(minutes=30),
            "started_at": datetime.now() - timedelta(minutes=29),
            "finished_at": datetime.now() - timedelta(minutes=28),
            "error": "Connection timeout",
        },
        {
            "job_type": JobType.RECOMPUTE_ASSESSMENT,
            "payload_json": json.dumps({"scope": "all"}),
            "status": JobStatus.PENDING,
            "priority": 1,
            "created_at": datetime.now() - timedelta(minutes=5),
            "started_at": None,
            "finished_at": None,
            "error": None,
        },
    ]

    for job_data in jobs_data:
        job = JobOutbox(**job_data)
        db.add(job)

    db.commit()
    print(f"  {len(jobs_data)} jobs créés")


def run_compliance_rules(db: Session, org: Organisation):
    """Run compliance rules engine + set workflow demo data on findings."""
    print("  Evaluation conformite (compliance_rules engine)...")

    from services.compliance_rules import evaluate_organisation

    result = evaluate_organisation(db, org.id)
    print(
        f"  Batch #{result['batch_id']}: {result['total_findings']} findings "
        f"({result['nok_count']} NOK, {result['unknown_count']} UNKNOWN)"
    )

    # Set workflow status on some findings for demo variety
    findings = db.query(ComplianceFinding).all()
    demo_owners = ["j.dupont@acme.fr", "m.martin@acme.fr", "s.leroy@acme.fr"]

    for i, f in enumerate(findings):
        if f.status == "OK":
            # 50% of OK findings -> resolved
            if random.random() < 0.50:
                f.insight_status = InsightStatus.RESOLVED
                f.owner = random.choice(demo_owners)
                f.notes = "Conforme - verifie lors de l'audit"
        elif f.status == "NOK":
            # 30% -> ack (in progress), 10% -> false_positive
            r = random.random()
            if r < 0.30:
                f.insight_status = InsightStatus.ACK
                f.owner = random.choice(demo_owners)
                f.notes = "Pris en charge, travaux en cours"
            elif r < 0.40:
                f.insight_status = InsightStatus.FALSE_POSITIVE
                f.owner = random.choice(demo_owners)
                f.notes = "Faux positif - derogation accordee"

    db.commit()

    # Count workflow distribution
    wf_counts = {}
    for f in findings:
        key = f.insight_status.value if f.insight_status else "open"
        wf_counts[key] = wf_counts.get(key, 0) + 1
    print(f"  Workflow demo: {wf_counts}")


def sync_action_hub(db: Session, org: Organisation):
    """Run Action Hub sync + set demo workflow variety."""
    print("  Synchronisation Action Hub...")

    from services.action_hub_service import sync_actions
    from models import ActionItem, ActionStatus

    result = sync_actions(db, org.id, triggered_by="seed")
    print(
        f"  Action Hub batch #{result['batch_id']}: "
        f"{result['created']} created, {result['updated']} updated, "
        f"{result['skipped']} skipped, {result['closed']} closed"
    )

    # Set demo variety on actions
    items = db.query(ActionItem).filter(ActionItem.org_id == org.id).all()
    demo_owners = ["j.dupont@acme.fr", "m.martin@acme.fr", "s.leroy@acme.fr"]

    for item in items:
        r = random.random()
        if r < 0.15:
            item.status = ActionStatus.IN_PROGRESS
            item.owner = random.choice(demo_owners)
            item.notes = "En cours de traitement"
        elif r < 0.25:
            item.status = ActionStatus.DONE
            item.owner = random.choice(demo_owners)
            item.notes = "Termine"
        elif r < 0.30:
            item.status = ActionStatus.BLOCKED
            item.notes = "En attente budget"
        elif r < 0.50:
            item.owner = random.choice(demo_owners)

    db.commit()

    # Count distribution
    dist = {}
    for item in items:
        key = item.status.value if item.status else "open"
        dist[key] = dist.get(key, 0) + 1
    print(f"  Action Hub demo: {len(items)} actions, distribution: {dist}")


def sync_notifications_demo(db: Session, org: Organisation):
    """Run Notification sync + set demo variety (some READ/DISMISSED)."""
    print("  Synchronisation Notifications...")

    from services.notification_service import sync_notifications
    from models import NotificationEvent, NotificationStatus

    result = sync_notifications(db, org.id, triggered_by="seed")
    print(
        f"  Notifications batch #{result['batch_id']}: "
        f"{result['created']} created, {result['updated']} updated, "
        f"{result['skipped']} skipped"
    )

    # Set demo variety
    events = db.query(NotificationEvent).filter(NotificationEvent.org_id == org.id).all()
    for event in events:
        r = random.random()
        if r < 0.20:
            event.status = NotificationStatus.READ
        elif r < 0.30:
            event.status = NotificationStatus.DISMISSED

    db.commit()

    # Count distribution
    dist = {}
    for event in events:
        key = event.status.value if event.status else "new"
        dist[key] = dist.get(key, 0) + 1
    print(f"  Notifications demo: {len(events)} events, distribution: {dist}")


def seed_iam_demo(db: Session, org: Organisation):
    """Create 10 IAM demo personas for Groupe Atlas / Casino demo."""
    print("  Creation des utilisateurs IAM demo...")

    from services.iam_service import (
        create_user,
        assign_role,
        assign_scope,
        hash_password,
        log_audit,
    )

    # Resolve entity and site IDs for scoped users
    entites = db.query(EntiteJuridique).filter(EntiteJuridique.organisation_id == org.id).all()
    entite_idf = entites[0] if entites else None

    sites = (
        db.query(Site)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org.id)
        .all()
    )
    first_site = sites[0] if sites else None
    # Pick a second site for prestataire dual-scope
    second_site = sites[2] if len(sites) > 2 else first_site

    PERSONAS = [
        # (prenom, nom, email, role, scope_type, scope_ref, expires_days)
        ("Sophie", "Durand", "sophie@atlas.demo", UserRole.DG_OWNER, "org", None, None),
        ("Marc", "Leroy", "marc@atlas.demo", UserRole.DSI_ADMIN, "org", None, None),
        ("Claire", "Martin", "claire@atlas.demo", UserRole.DAF, "org", None, None),
        ("Thomas", "Petit", "thomas@atlas.demo", UserRole.ACHETEUR, "org", None, None),
        ("Nadia", "Benali", "nadia@atlas.demo", UserRole.RESP_CONFORMITE, "org", None, None),
        ("Lucas", "Moreau", "lucas@atlas.demo", UserRole.ENERGY_MANAGER, "org", None, None),
        ("Julie", "Lambert", "julie@atlas.demo", UserRole.RESP_IMMOBILIER, "entite", entite_idf, None),
        ("Pierre", "Garcia", "pierre@atlas.demo", UserRole.RESP_SITE, "site", first_site, None),
        ("Karim", "Diallo", "karim@atlas.demo", UserRole.PRESTATAIRE, "site", first_site, 90),
        ("Emma", "Roux", "emma@atlas.demo", UserRole.AUDITEUR, "org", None, None),
    ]

    users_created = []
    for prenom, nom, email, role, scope_type, scope_ref, expires_days in PERSONAS:
        user = create_user(db, email=email, password="demo2024", nom=nom, prenom=prenom)
        uor = assign_role(db, user_id=user.id, org_id=org.id, role=role)

        # Assign scope
        if scope_type == "org":
            assign_scope(db, uor.id, ScopeLevel.ORG, org.id)
        elif scope_type == "entite" and scope_ref:
            assign_scope(db, uor.id, ScopeLevel.ENTITE, scope_ref.id)
        elif scope_type == "site" and scope_ref:
            expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_days)) if expires_days else None
            assign_scope(db, uor.id, ScopeLevel.SITE, scope_ref.id, expires_at=expires_at)
            # Karim gets a second site scope
            if email == "karim@atlas.demo" and second_site and second_site.id != scope_ref.id:
                assign_scope(db, uor.id, ScopeLevel.SITE, second_site.id, expires_at=expires_at)

        users_created.append(user)

    # Create some audit log entries
    log_audit(db, users_created[0].id, "login", detail={"method": "password"})
    log_audit(db, users_created[1].id, "login", detail={"method": "password"})
    log_audit(
        db,
        users_created[1].id,
        "edit",
        "user",
        str(users_created[7].id),
        detail={"action": "assign_scope", "site_id": first_site.id if first_site else 0},
    )

    db.commit()
    print(f"  {len(users_created)} utilisateurs IAM crees avec roles et scopes")
    print(f"  Login demo: sophie@atlas.demo / demo2024 (DG/Owner)")
    return users_created


def seed_patrimoine_demo(db: Session) -> dict:
    """Seed patrimoine demo: Collectivite Azur (10 sites, 13 compteurs, N-N links).

    Idempotent: skips if org 'Collectivite Azur' already exists.
    Can be called from route POST /api/patrimoine/demo/load or from main().
    """
    from models import (
        OrgEntiteLink,
        PortfolioEntiteLink,
        Compteur,
        TypeCompteur,
        EnergyVector,
    )
    from services.onboarding_service import create_site_from_data, provision_site

    # Idempotence check
    existing = db.query(Organisation).filter(Organisation.nom == "Collectivite Azur").first()
    if existing:
        sites_count = (
            db.query(Site)
            .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
            .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
            .filter(EntiteJuridique.organisation_id == existing.id)
            .count()
        )
        return {"status": "already_exists", "org_id": existing.id, "sites": sites_count}

    print("  Creation Collectivite Azur (patrimoine demo)...")

    # --- Organisation ---
    org = Organisation(nom="Collectivite Azur", type_client="collectivite", actif=True, siren="200054781")
    db.add(org)
    db.flush()

    # --- Entites juridiques ---
    mairie = EntiteJuridique(
        organisation_id=org.id,
        nom="Mairie de Nice",
        siren="200054781",
        siret="20005478100015",
        naf_code="84.11Z",
        region_code="93",
        insee_code="06088",
    )
    ccas = EntiteJuridique(
        organisation_id=org.id,
        nom="CCAS Nice",
        siren="200054799",
        siret="20005479900012",
        naf_code="88.99B",
        region_code="93",
        insee_code="06088",
    )
    db.add_all([mairie, ccas])
    db.flush()

    # --- N-N links (OrgEntiteLink) ---
    link_org_mairie = OrgEntiteLink(
        organisation_id=org.id,
        entite_juridique_id=mairie.id,
        role="proprietaire",
        confidence=1.0,
    )
    link_org_ccas = OrgEntiteLink(
        organisation_id=org.id,
        entite_juridique_id=ccas.id,
        role="proprietaire",
        confidence=1.0,
    )
    db.add_all([link_org_mairie, link_org_ccas])
    db.flush()

    # --- Portefeuilles ---
    pf_equip = Portefeuille(
        entite_juridique_id=mairie.id, nom="Equipements publics", description="Mairie, ecoles, gymnases, creches"
    )
    pf_voirie = Portefeuille(
        entite_juridique_id=mairie.id, nom="Voirie & Eclairage", description="Parkings et eclairage public"
    )
    pf_medico = Portefeuille(
        entite_juridique_id=ccas.id, nom="Medico-social", description="EHPAD, foyers, centres sociaux"
    )
    db.add_all([pf_equip, pf_voirie, pf_medico])
    db.flush()

    # --- N-N links (PortfolioEntiteLink) ---
    link_pf_ccas = PortfolioEntiteLink(
        portefeuille_id=pf_medico.id,
        entite_juridique_id=ccas.id,
        role="gestionnaire",
    )
    link_pf_mairie_medico = PortfolioEntiteLink(
        portefeuille_id=pf_medico.id,
        entite_juridique_id=mairie.id,
        role="tutelle",
    )
    db.add_all([link_pf_ccas, link_pf_mairie_medico])
    db.flush()

    # --- Sites data ---
    SITES_DATA = [
        # (portefeuille, nom, type_site, surface, adresse, cp, ville, compteurs)
        (
            pf_equip,
            "Mairie Centre Nice",
            "collectivite",
            2500,
            "5 rue de la Prefecture",
            "06300",
            "Nice",
            [("electricite", "MR-E01", 120), ("gaz", "MR-G01", None)],
        ),
        (
            pf_equip,
            "Ecole Victor Hugo",
            "enseignement",
            1800,
            "12 avenue Victor Hugo",
            "06000",
            "Nice",
            [("electricite", "VH-E01", 60), ("gaz", "VH-G01", None)],
        ),
        (
            pf_equip,
            "Gymnase Municipal Magnan",
            "collectivite",
            900,
            "45 boulevard de Magnan",
            "06200",
            "Nice",
            [("electricite", "GY-E01", 36)],
        ),
        (
            pf_equip,
            "Bibliotheque Raimbaldi",
            "collectivite",
            600,
            "1 place Pierre Gautier",
            "06300",
            "Nice",
            [("electricite", "BR-E01", 36)],
        ),
        (
            pf_equip,
            "Creche Les Oliviers",
            "sante",
            400,
            "8 rue des Oliviers",
            "06100",
            "Nice",
            [("electricite", "CR-E01", 24)],
        ),
        (
            pf_voirie,
            "Parking Massena",
            "entrepot",
            5000,
            "Place Massena",
            "06000",
            "Nice",
            [("electricite", "PM-E01", 150)],
        ),
        (
            pf_voirie,
            "Eclairage Promenade des Anglais",
            "collectivite",
            0,
            "Promenade des Anglais",
            "06200",
            "Nice",
            [("electricite", "PA-E01", 200)],
        ),
        (
            pf_medico,
            "EHPAD Les Mimosas",
            "sante",
            3000,
            "22 chemin des Mimosas",
            "06100",
            "Nice",
            [("electricite", "EH-E01", 90), ("gaz", "EH-G01", None)],
        ),
        (
            pf_medico,
            "Foyer Jeunes Travailleurs",
            "logement_social",
            1200,
            "15 rue Barla",
            "06300",
            "Nice",
            [("electricite", "FJ-E01", 60)],
        ),
        (
            pf_medico,
            "Centre Social Ariane",
            "collectivite",
            800,
            "3 boulevard de l'Ariane",
            "06300",
            "Nice",
            [("electricite", "CS-E01", 36)],
        ),
    ]

    sites_created = 0
    compteurs_created = 0
    batiments_count = 0
    obligations_count = 0

    _ENERGY_MAP = {
        "electricite": (TypeCompteur.ELECTRICITE, EnergyVector.ELECTRICITY),
        "gaz": (TypeCompteur.GAZ, EnergyVector.GAS),
        "eau": (TypeCompteur.EAU, None),
    }

    for pf, nom, type_site, surface, adresse, cp, ville, compteurs_data in SITES_DATA:
        site = create_site_from_data(
            db=db,
            portefeuille_id=pf.id,
            nom=nom,
            type_site=type_site,
            adresse=adresse,
            code_postal=cp,
            ville=ville,
            surface_m2=float(surface) if surface else None,
        )
        site.data_source = "demo"
        site.data_source_ref = "patrimoine_demo"
        site.latitude = 43.7102 + random.uniform(-0.02, 0.02)
        site.longitude = 7.2620 + random.uniform(-0.02, 0.02)
        site.region = "Provence-Alpes-Cote d'Azur"

        prov = provision_site(db, site)
        batiments_count += 1
        obligations_count += prov.get("obligations", 0)
        sites_created += 1

        for ctype, serie_suffix, puissance in compteurs_data:
            tc, ev = _ENERGY_MAP.get(ctype, (TypeCompteur.ELECTRICITE, EnergyVector.ELECTRICITY))
            compteur = Compteur(
                site_id=site.id,
                type=tc,
                numero_serie=f"AZR-{serie_suffix}",
                meter_id=f"{random.randint(10000000000000, 99999999999999)}",
                energy_vector=ev,
                puissance_souscrite_kw=puissance,
                actif=True,
                data_source="demo",
                data_source_ref="patrimoine_demo",
            )
            db.add(compteur)
            compteurs_created += 1

    db.flush()

    result = {
        "status": "created",
        "org_id": org.id,
        "org_name": org.nom,
        "entites": 2,
        "portefeuilles": 3,
        "sites": sites_created,
        "compteurs": compteurs_created,
        "batiments": batiments_count,
        "obligations": obligations_count,
        "nn_links": 4,
    }
    print(
        f"  Collectivite Azur: {sites_created} sites, {compteurs_created} compteurs, "
        f"{batiments_count} batiments, {obligations_count} obligations"
    )
    return result


def main():
    """Script principal de seed"""
    print("=" * 70)
    print("PROMEOS - Génération de données (seed)")
    print("=" * 70)

    # Recréer les tables
    print("\nSuppression des anciennes tables...")
    Base.metadata.drop_all(bind=engine)

    print("Création des nouvelles tables...")
    Base.metadata.create_all(bind=engine)

    # Générer données
    db = SessionLocal()

    try:
        org, entite, portefeuilles = create_organisation_hierarchy(db)
        sites = create_sites(db, portefeuilles)
        batiments = create_batiments_usages(db, sites)
        create_obligations(db, sites, batiments)
        create_evidences(db, sites, batiments)

        # Compute compliance snapshots from obligations + evidences (engine)
        from services.compliance_engine import recompute_site

        print("  Calcul des snapshots conformite...")
        for site in sites:
            recompute_site(db, site.id)
        print(f"  {len(sites)} snapshots conformite calcules")

        create_compteurs_consommations(db, sites)
        create_alertes(db, sites)

        # RegOps data
        create_datapoints(db, sites)
        create_reg_source_events(db)
        run_regops_assessments(db, sites)
        create_sample_jobs(db)

        # Sprint 9: Compliance rules evaluation + workflow demo
        run_compliance_rules(db, org)

        # Sprint 10: Action Hub sync
        sync_action_hub(db, org)

        # Sprint 10.2: Notifications sync
        sync_notifications_demo(db, org)

        # Sprint 11: IAM demo users
        seed_iam_demo(db, org)

        # DIAMANT: Patrimoine demo (Collectivite Azur)
        patrimoine_result = seed_patrimoine_demo(db)
        db.commit()

        # V68: Billing demo 36 mois
        from services.billing_seed import seed_billing_demo

        billing_result = seed_billing_demo(db)
        if "error" in billing_result:
            print(f"  ⚠ Billing seed skipped: {billing_result['error']}")
        elif billing_result.get("skipped"):
            print(f"  ⚠ Billing seed skipped: {billing_result.get('reason')}")
        else:
            print(f"  ✓ Billing demo seeded ({billing_result.get('invoices_created')} factures, 36 mois, 2 sites)")

        print("\n" + "=" * 70)
        print("SEED TERMINE AVEC SUCCES !")
        print("=" * 70)
        print(f"Resume :")
        print(f"   - 1 Organisation (Groupe Casino) + 1 Organisation (Collectivite Azur)")
        print(f"   - 3 Entites juridiques (Casino + Mairie + CCAS)")
        print(f"   - 6 Portefeuilles (3 Casino + 3 Azur)")
        print(f"   - 130 Sites (120 Casino + 10 Azur)")
        print(f"   - 130 Batiments")
        print(f"   - ~300 Usages")
        print(f"   - ~150+ Obligations")
        print(f"   - ~63 Compteurs (50 Casino + 13 Azur)")
        print(f"   - ~8400 Consommations (7j)")
        print(f"   - ~500 Evidences")
        print(f"   - 20 Alertes actives")
        print(f"   - ~50 DataPoints (RTE, PVGIS)")
        print(f"   - 4 RegSourceEvents")
        print(f"   - 120 RegAssessments (from RegOps engine)")
        print(f"   - 4 JobOutbox entries")
        print(f"   - ComplianceFindings (from rules engine, with workflow demo)")
        print(f"   - ActionItems (from Action Hub sync, with workflow demo)")
        print(f"   - NotificationEvents (from Alert Center sync, with READ/DISMISSED demo)")
        print(f"   - 10 Users IAM (roles + scopes, login: sophie@atlas.demo / demo2024)")
        print(f"   - 4 N-N links (OrgEntiteLink + PortfolioEntiteLink)")
        print("=" * 70)

    except Exception as e:
        print(f"Erreur : {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
