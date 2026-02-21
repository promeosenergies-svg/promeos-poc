"""
PROMEOS - Demo Seed: Master Data Generator
Creates org, entite_juridique, portefeuilles, sites, batiments, meters.
"""
import random
from datetime import datetime

from models import (
    Organisation, EntiteJuridique, Portefeuille, Site, Batiment,
    Compteur, Meter, SiteOperatingSchedule,
    TypeSite, TypeCompteur, EnergyVector, ParkingType, OperatStatus,
)
from models.energy_models import EnergyVector as EnergyVectorModel

from .packs import _VILLES, _RUES


# Mapping from pack type_site string to TypeSite enum
_TYPE_MAP = {
    "commerce": TypeSite.COMMERCE, "bureau": TypeSite.BUREAU,
    "entrepot": TypeSite.ENTREPOT, "hotel": TypeSite.HOTEL,
    "sante": TypeSite.SANTE, "enseignement": TypeSite.ENSEIGNEMENT,
    "magasin": TypeSite.MAGASIN, "copropriete": TypeSite.COPROPRIETE,
}

_PARKING_MAP = {
    "outdoor": ParkingType.OUTDOOR, "indoor": ParkingType.INDOOR,
    "underground": ParkingType.UNDERGROUND, "unknown": ParkingType.UNKNOWN,
}

# Profiles → schedule mapping
_PROFILE_SCHEDULES = {
    "office":    {"open_days": "0,1,2,3,4", "open_time": "08:00", "close_time": "19:00", "is_24_7": False},
    "hotel":     {"open_days": "0,1,2,3,4,5,6", "open_time": "00:00", "close_time": "23:59", "is_24_7": True},
    "retail":    {"open_days": "0,1,2,3,4,5", "open_time": "09:00", "close_time": "20:00", "is_24_7": False},
    "warehouse": {"open_days": "0,1,2,3,4", "open_time": "06:00", "close_time": "20:00", "is_24_7": False},
    "school":    {"open_days": "0,1,2,3,4", "open_time": "07:30", "close_time": "18:00", "is_24_7": False},
    "hospital":  {"open_days": "0,1,2,3,4,5,6", "open_time": "00:00", "close_time": "23:59", "is_24_7": True},
}


def generate_master(db, pack: dict, size: str, rng: random.Random) -> dict:
    """
    Generate all master data for a pack.
    Returns context dict with org, sites, meters, profiles.
    """
    size_cfg = pack["sizes"][size]

    # 1. Organisation
    org_cfg = pack["org"]
    org = Organisation(
        nom=org_cfg["nom"], type_client=org_cfg["type_client"],
        actif=True, siren=org_cfg["siren"], is_demo=True,
    )
    db.add(org)
    db.flush()

    # 2. Entites juridiques
    entites = []
    for ej_cfg in pack["entites"]:
        ej = EntiteJuridique(
            organisation_id=org.id, nom=ej_cfg["nom"],
            siren=ej_cfg["siren"], siret=ej_cfg.get("siret"),
            naf_code=ej_cfg.get("naf_code"), region_code=ej_cfg.get("region_code"),
        )
        db.add(ej)
        entites.append(ej)
    db.flush()

    # 3. Portefeuilles
    portefeuilles = []
    for pf_cfg in pack["portefeuilles"]:
        pf = Portefeuille(
            entite_juridique_id=entites[0].id,
            nom=pf_cfg["nom"], description=pf_cfg["description"],
        )
        db.add(pf)
        portefeuilles.append(pf)
    db.flush()

    # 4. Sites + meters
    sites_per_pf = size_cfg["sites_per_pf"]
    site_groups = pack["site_groups"]
    all_sites = []
    all_meters = []
    site_profiles = {}  # site_id → profile name

    site_counter = 0
    for pf_idx, (pf, count) in enumerate(zip(portefeuilles, sites_per_pf)):
        group = site_groups[pf_idx % len(site_groups)]
        for i in range(count):
            v = _VILLES[site_counter % len(_VILLES)]
            ville, cp, region, lat, lon = v
            surface = rng.randint(*group["surface_range"])
            cvc_kw = round(surface * rng.uniform(*group["cvc_w_per_m2"]) / 1000, 1)
            parking = rng.randint(*group["parking_range"])
            roof = round(surface * rng.uniform(*group["roof_pct"]))
            annual_kwh = rng.randint(*group["annual_kwh_range"])

            # Site type: use group type, but for tertiaire equipements cycle
            site_type_str = group["type_site"]
            if "profiles" in group:
                prof_idx = i % len(group["profiles"])
                profile_name = group["profiles"][prof_idx]
                # Map profile to site type
                if profile_name == "school":
                    site_type_str = "enseignement"
                elif profile_name == "hospital":
                    site_type_str = "sante"
                elif profile_name == "hotel":
                    site_type_str = "hotel"
            else:
                profile_name = group.get("profile", "office")

            site = Site(
                portefeuille_id=pf.id,
                nom=f"{group['prefix']} {ville} #{site_counter + 1:02d}",
                type=_TYPE_MAP.get(site_type_str, TypeSite.BUREAU),
                adresse=f"{rng.randint(1, 200)} {_RUES[site_counter % len(_RUES)]}",
                code_postal=cp, ville=ville, region=region,
                surface_m2=surface, nombre_employes=rng.randint(*group["employees_range"]),
                latitude=lat + rng.uniform(-0.02, 0.02),
                longitude=lon + rng.uniform(-0.02, 0.02),
                actif=True, is_demo=True,
                tertiaire_area_m2=surface if surface >= 1000 else None,
                parking_area_m2=parking,
                parking_type=_PARKING_MAP.get(group.get("parking_type"), ParkingType.UNKNOWN),
                roof_area_m2=roof,
                naf_code=group.get("naf") if site_counter < (count * 0.8) else None,
                annual_kwh_total=annual_kwh,
                data_source="demo",
                siret=f"{pack['entites'][0]['siren']}{rng.randint(10000, 99999)}",
            )
            # Store cvc_power_kw as attribute (for Batiment)
            site._cvc_kw = cvc_kw
            db.add(site)
            db.flush()

            site_profiles[site.id] = profile_name
            all_sites.append(site)

            # Batiment
            bat = Batiment(
                site_id=site.id,
                nom=f"Batiment principal - {site.nom}",
                surface_m2=surface,
                annee_construction=rng.randint(1970, 2020),
                cvc_power_kw=cvc_kw,
            )
            db.add(bat)

            # OPERAT status for assujetti sites
            if site.tertiaire_area_m2 and site.tertiaire_area_m2 >= 1000:
                bucket = site_counter % 3
                if bucket == 0:
                    site.operat_status = OperatStatus.SUBMITTED
                elif bucket == 1:
                    site.operat_status = OperatStatus.IN_PROGRESS
                else:
                    site.operat_status = OperatStatus.NOT_STARTED

            # Meter (electricity)
            meter_id_str = f"DEMO-{pack['org']['siren'][:4]}-{site.id:04d}"
            meter = Meter(
                meter_id=meter_id_str,
                name=f"Compteur {site.nom}",
                site_id=site.id,
                energy_vector=EnergyVectorModel.ELECTRICITY,
                subscribed_power_kva=float(rng.randint(*group["psub_range"])),
                tariff_type="C5",
                is_active=True,
            )
            db.add(meter)
            db.flush()
            all_meters.append(meter)

            # Compteur (legacy model)
            db.add(Compteur(
                site_id=site.id, type=TypeCompteur.ELECTRICITE,
                numero_serie=f"DEMO-E-{site.id:04d}",
                puissance_souscrite_kw=meter.subscribed_power_kva,
                meter_id=meter_id_str,
                energy_vector=EnergyVector.ELECTRICITY, actif=True,
                data_source="demo",
            ))

            # Gas meter for some sites
            if rng.random() < group.get("gas_pct", 0):
                db.add(Compteur(
                    site_id=site.id, type=TypeCompteur.GAZ,
                    numero_serie=f"DEMO-G-{site.id:04d}",
                    meter_id=f"GRD{rng.randint(100000000, 999999999)}",
                    energy_vector=EnergyVector.GAS, actif=True,
                    data_source="demo",
                ))

            # Operating schedule
            sched_cfg = _PROFILE_SCHEDULES.get(profile_name, _PROFILE_SCHEDULES["office"])
            sched = SiteOperatingSchedule(
                site_id=site.id,
                open_days=sched_cfg["open_days"],
                open_time=sched_cfg["open_time"],
                close_time=sched_cfg["close_time"],
                is_24_7=sched_cfg["is_24_7"],
            )
            db.add(sched)

            site_counter += 1

    db.flush()

    return {
        "org": org,
        "entites": entites,
        "portefeuilles": portefeuilles,
        "sites": all_sites,
        "meters": all_meters,
        "site_profiles": site_profiles,
    }
