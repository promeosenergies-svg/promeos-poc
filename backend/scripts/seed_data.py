"""
PROMEOS - Script de génération de données (seed)
Architecture complète : Organisation → Portefeuille → Sites → Bâtiments → Compteurs
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models import (
    Base,
    Organisation, EntiteJuridique, Portefeuille,
    Site, Batiment, Usage, TypeUsage,
    Compteur, Consommation,
    Obligation, StatutConformite, TypeObligation,
    Alerte, SeveriteAlerte,
    TypeSite, TypeCompteur
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
    org = Organisation(
        nom="Groupe Casino",
        type_client="retail",
        actif=True
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    # Entité juridique
    entite = EntiteJuridique(
        organisation_id=org.id,
        nom="Casino France SAS",
        siren="554008671",
        siret="55400867100013"
    )
    db.add(entite)
    db.commit()
    db.refresh(entite)

    # 3 Portefeuilles
    portefeuilles = []
    for nom_region, desc in [
        ("Retail IDF", "Magasins Île-de-France"),
        ("Retail Sud", "Magasins Sud de la France"),
        ("Bureaux & Logistique", "Sites administratifs et entrepôts")
    ]:
        p = Portefeuille(
            entite_juridique_id=entite.id,
            nom=nom_region,
            description=desc
        )
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

        # Statuts conformité (réaliste)
        statut_tertiaire = random.choices(
            [StatutConformite.CONFORME, StatutConformite.A_RISQUE, StatutConformite.NON_CONFORME],
            weights=[30, 50, 20]
        )[0]

        statut_bacs = random.choices(
            [StatutConformite.CONFORME, StatutConformite.A_RISQUE, StatutConformite.NON_CONFORME],
            weights=[40, 40, 20]
        )[0]

        # Actions recommandées selon statut
        if statut_bacs == StatutConformite.NON_CONFORME:
            action = "Installer GTB >290 kW (BACS obligatoire)"
        elif statut_tertiaire == StatutConformite.NON_CONFORME:
            action = "Audit décret tertiaire - trajectoire 2030 KO"
        elif random.random() < 0.3:
            action = "Vérifier dérive conso nocturne"
        else:
            action = None

        site = Site(
            portefeuille_id=portefeuille.id,
            nom=f"{entreprise['nom']} {ville['nom']} #{compteur_global}",
            type=type_site,
            adresse=f"{random.randint(1, 200)} rue de la {random.choice(['Gare', 'République', 'Liberté', 'Paix'])}",
            ville=ville["nom"],
            code_postal=f"{random.randint(10, 95):02d}{random.randint(100, 999)}",
            region=ville["region"],
            surface_m2=random.randint(800, 5000),
            latitude=random.uniform(43.0, 49.0),
            longitude=random.uniform(-1.5, 7.5),
            actif=True,
            statut_decret_tertiaire=statut_tertiaire,
            avancement_decret_pct=random.uniform(20, 85),
            statut_bacs=statut_bacs,
            anomalie_facture=(random.random() < 0.15),
            action_recommandee=action,
            risque_financier_euro=random.uniform(1000, 50000) if statut_tertiaire == StatutConformite.NON_CONFORME else 0
        )

        db.add(site)
        sites.append(site)
        compteur_global += 1

    db.commit()
    for s in sites:
        db.refresh(s)

    print(f"  {len(sites)} sites créés")
    return sites


def create_batiments_usages(db: Session, sites: list):
    """Créer bâtiments et usages pour chaque site"""
    print("  Création des bâtiments et usages...")

    batiments = []
    for site in sites:
        # 1 bâtiment par site (simplifié POC)
        bat = Batiment(
            site_id=site.id,
            nom="Bâtiment principal",
            surface_m2=site.surface_m2,
            annee_construction=random.randint(1980, 2020)
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
            usage = Usage(
                batiment_id=b.id,
                type=usage_type,
                description=f"Usage {usage_type.value}"
            )
            db.add(usage)

    db.commit()
    print(f"  {len(batiments)} bâtiments créés avec usages")
    return batiments


def create_obligations(db: Session, sites: list):
    """Créer obligations réglementaires"""
    print("  Création des obligations...")

    for site in sites:
        # Obligation Décret Tertiaire
        obl_tertiaire = Obligation(
            site_id=site.id,
            type=TypeObligation.DECRET_TERTIAIRE,
            description="Réduction -40% en 2030 vs 2010",
            echeance=datetime(2030, 12, 31).date(),
            statut=site.statut_decret_tertiaire,
            avancement_pct=site.avancement_decret_pct
        )
        db.add(obl_tertiaire)

        # Obligation BACS (si site > 290 kW estimé)
        if site.surface_m2 > 1500:  # Proxy pour > 290 kW
            obl_bacs = Obligation(
                site_id=site.id,
                type=TypeObligation.BACS,
                description="GTB/GTC obligatoire > 290 kW",
                echeance=datetime(2025, 1, 1).date(),
                statut=site.statut_bacs,
                avancement_pct=random.uniform(40, 100)
            )
            db.add(obl_bacs)

    db.commit()
    print("  Obligations créées")


def create_compteurs_consommations(db: Session, sites: list):
    """Créer compteurs et consommations (simplifié)"""
    print("  Création compteurs et consommations...")

    compteurs = []
    for site in sites[:30]:  # Seulement 30 sites avec compteurs pour accélérer
        # 1-2 compteurs par site
        nb_compteurs = random.randint(1, 2)

        for i in range(nb_compteurs):
            type_compteur = TypeCompteur.ELECTRICITE if i == 0 else random.choice(list(TypeCompteur))
            compteur = Compteur(
                site_id=site.id,
                numero_serie=f"PRM{random.randint(100000000000, 999999999999)}",
                type=type_compteur,
                puissance_souscrite_kw=random.choice([36, 60, 90, 120, 150]) if type_compteur == TypeCompteur.ELECTRICITE else None,
                actif=True
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
                    valeur = random.uniform(10, 30)   # kWh nuit
                    cout = valeur * 0.12

                conso = Consommation(
                    compteur_id=compteur.id,
                    timestamp=timestamp,
                    valeur=round(valeur, 2),
                    cout_euro=round(cout, 2)
                )
                db.add(conso)

    db.commit()
    print(f"  {len(compteurs)} compteurs avec consommations 7j")


def create_alertes(db: Session, sites: list):
    """Créer 20 alertes actives"""
    print("  Création de 20 alertes...")

    sites_avec_problemes = [s for s in sites if
                            s.statut_decret_tertiaire == StatutConformite.NON_CONFORME or
                            s.statut_bacs == StatutConformite.NON_CONFORME or
                            s.anomalie_facture]

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
            resolue=False
        )
        db.add(alerte)

    db.commit()
    print("  20 alertes créées")


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
        create_obligations(db, sites)
        create_compteurs_consommations(db, sites)
        create_alertes(db, sites)

        print("\n" + "=" * 70)
        print("SEED TERMINE AVEC SUCCES !")
        print("=" * 70)
        print(f"Résumé :")
        print(f"   - 1 Organisation (Groupe Casino)")
        print(f"   - 1 Entité juridique")
        print(f"   - 3 Portefeuilles")
        print(f"   - 120 Sites")
        print(f"   - 120 Bâtiments")
        print(f"   - ~300 Usages")
        print(f"   - ~150 Obligations")
        print(f"   - ~50 Compteurs")
        print(f"   - ~8400 Consommations (7j)")
        print(f"   - 20 Alertes actives")
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
