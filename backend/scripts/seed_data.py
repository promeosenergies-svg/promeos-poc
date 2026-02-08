"""
PROMEOS - Script de génération de données de test
Génère 120 sites avec compteurs, consommations et alertes
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Site, Compteur, Consommation, Alerte, TypeSite, TypeCompteur, SeveriteAlerte
from database import SessionLocal
from datetime import datetime, timedelta
import random

# Données réalistes françaises
VILLES_FRANCE = [
    ("Paris", "75001", "Île-de-France", 48.8566, 2.3522),
    ("Lyon", "69001", "Auvergne-Rhône-Alpes", 45.7640, 4.8357),
    ("Marseille", "13001", "Provence-Alpes-Côte d'Azur", 43.2965, 5.3698),
    ("Toulouse", "31000", "Occitanie", 43.6047, 1.4442),
    ("Nice", "06000", "Provence-Alpes-Côte d'Azur", 43.7102, 7.2620),
    ("Nantes", "44000", "Pays de la Loire", 47.2184, -1.5536),
    ("Strasbourg", "67000", "Grand Est", 48.5734, 7.7521),
    ("Montpellier", "34000", "Occitanie", 43.6108, 3.8767),
    ("Bordeaux", "33000", "Nouvelle-Aquitaine", 44.8378, -0.5792),
    ("Lille", "59000", "Hauts-de-France", 50.6292, 3.0573),
    ("Rennes", "35000", "Bretagne", 48.1173, -1.6778),
    ("Reims", "51100", "Grand Est", 49.2583, 4.0317),
    ("Le Havre", "76600", "Normandie", 49.4944, 0.1079),
    ("Saint-Étienne", "42000", "Auvergne-Rhône-Alpes", 45.4397, 4.3872),
    ("Toulon", "83000", "Provence-Alpes-Côte d'Azur", 43.1242, 5.9280),
]

NOMS_ENTREPRISES = [
    "Carrefour", "Auchan", "Leclerc", "Intermarché", "Casino",
    "Renault", "PSA", "Michelin", "Total", "EDF",
    "Orange", "SFR", "Bouygues", "Vinci", "Accor",
    "Danone", "L'Oréal", "LVMH", "Airbus", "Thales"
]

def generer_sites(session, nb_sites=120):
    """Génère les sites PROMEOS"""
    print(f"📍 Génération de {nb_sites} sites...")
    
    sites = []
    types_sites = [TypeSite.MAGASIN] * 50 + [TypeSite.USINE] * 30 + [TypeSite.BUREAU] * 25 + [TypeSite.ENTREPOT] * 15
    random.shuffle(types_sites)
    
    for i in range(nb_sites):
        ville, cp, region, lat, lon = random.choice(VILLES_FRANCE)
        entreprise = random.choice(NOMS_ENTREPRISES)
        type_site = types_sites[i]
        
        # Variation GPS (± 0.1 degrés)
        lat_var = lat + random.uniform(-0.1, 0.1)
        lon_var = lon + random.uniform(-0.1, 0.1)
        
        site = Site(
            nom=f"{entreprise} {ville} #{i+1}",
            type=type_site,
            adresse=f"{random.randint(1, 200)} rue {random.choice(['de la République', 'Victor Hugo', 'Jean Jaurès'])}",
            code_postal=cp,
            ville=ville,
            region=region,
            surface_m2=random.randint(200, 5000),
            nombre_employes=random.randint(5, 200),
            latitude=round(lat_var, 6),
            longitude=round(lon_var, 6),
            actif=True
        )
        sites.append(site)
    
    session.add_all(sites)
    session.commit()
    print(f"✅ {len(sites)} sites créés")
    return sites

def generer_compteurs(session, sites):
    """Génère les compteurs pour chaque site"""
    print("⚡ Génération des compteurs...")
    
    compteurs = []
    for site in sites:
        nb_compteurs = random.randint(3, 5)
        
        # Toujours un compteur électricité
        compteurs.append(Compteur(
            site_id=site.id,
            type=TypeCompteur.ELECTRICITE,
            numero_serie=f"EL-{site.id}-{random.randint(100000, 999999)}",
            puissance_souscrite_kw=random.choice([36, 60, 90, 120, 150]),
            actif=True
        ))
        
        # Compteurs gaz (80% des sites)
        if random.random() < 0.8:
            compteurs.append(Compteur(
                site_id=site.id,
                type=TypeCompteur.GAZ,
                numero_serie=f"GZ-{site.id}-{random.randint(100000, 999999)}",
                actif=True
            ))
        
        # Compteurs eau (90% des sites)
        if random.random() < 0.9:
            compteurs.append(Compteur(
                site_id=site.id,
                type=TypeCompteur.EAU,
                numero_serie=f"EA-{site.id}-{random.randint(100000, 999999)}",
                actif=True
            ))
    
    session.add_all(compteurs)
    session.commit()
    print(f"✅ {len(compteurs)} compteurs créés")
    return compteurs

def generer_consommations(session, compteurs, jours=30):
    """Génère les consommations des N derniers jours"""
    print(f"📊 Génération des consommations ({jours} jours)...")
    
    consommations = []
    now = datetime.now()
    
    for compteur in compteurs:
        for jour in range(jours):
            date = now - timedelta(days=jour)
            
            # Valeurs réalistes selon le type
            if compteur.type == TypeCompteur.ELECTRICITE:
                valeur = random.uniform(50, 500)  # kWh/jour
                cout = valeur * 0.15  # 0.15€/kWh
            elif compteur.type == TypeCompteur.GAZ:
                valeur = random.uniform(20, 200)  # m³/jour
                cout = valeur * 0.08  # 0.08€/m³
            else:  # EAU
                valeur = random.uniform(5, 50)  # m³/jour
                cout = valeur * 4.0  # 4€/m³
            
            consommations.append(Consommation(
                compteur_id=compteur.id,
                timestamp=date,
                valeur=round(valeur, 2),
                cout_euro=round(cout, 2)
            ))
    
    session.add_all(consommations)
    session.commit()
    print(f"✅ {len(consommations)} consommations créées")

def generer_alertes(session, sites):
    """Génère des alertes réalistes"""
    print("🚨 Génération des alertes...")
    
    alertes = []
    titres_alertes = [
        "Dépassement consommation électrique",
        "Pic de consommation inhabituel",
        "Anomalie compteur gaz",
        "Fuite d'eau détectée",
        "Consommation nocturne anormale",
        "Dépassement seuil critique"
    ]
    
    for _ in range(30):
        site = random.choice(sites)
        severite = random.choice([SeveriteAlerte.INFO, SeveriteAlerte.WARNING, SeveriteAlerte.CRITICAL])
        resolue = random.random() < 0.6  # 60% résolues
        
        timestamp = datetime.now() - timedelta(days=random.randint(0, 30))
        
        alerte = Alerte(
            site_id=site.id,
            severite=severite,
            titre=random.choice(titres_alertes),
            description=f"Alerte automatique détectée sur {site.nom}",
            timestamp=timestamp,
            resolue=resolue,
            date_resolution=timestamp + timedelta(hours=random.randint(1, 48)) if resolue else None
        )
        alertes.append(alerte)
    
    session.add_all(alertes)
    session.commit()
    print(f"✅ {len(alertes)} alertes créées")

def main():
    print("=" * 70)
    print("🔥 PROMEOS - Génération des données de test")
    print("=" * 70)
    
    session = SessionLocal()
    
    try:
        # Nettoyer les données existantes
        session.query(Alerte).delete()
        session.query(Consommation).delete()
        session.query(Compteur).delete()
        session.query(Site).delete()
        session.commit()
        
        # Générer les nouvelles données
        sites = generer_sites(session, 120)
        compteurs = generer_compteurs(session, sites)
        generer_consommations(session, compteurs, 30)
        generer_alertes(session, sites)
        
        print()
        print("=" * 70)
        print("🎉 Données PROMEOS générées avec succès !")
        print("=" * 70)
        print(f"📊 Statistiques :")
        print(f"   - Sites : {session.query(Site).count()}")
        print(f"   - Compteurs : {session.query(Compteur).count()}")
        print(f"   - Consommations : {session.query(Consommation).count()}")
        print(f"   - Alertes : {session.query(Alerte).count()}")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    main()
