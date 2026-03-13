"""
PROMEOS - Demo Seed: Master Data Generator
Creates org, entite_juridique, portefeuilles, sites, batiments, meters.
"""

import random
from datetime import datetime

from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Batiment,
    Compteur,
    Meter,
    SiteOperatingSchedule,
    TypeSite,
    TypeCompteur,
    EnergyVector,
    ParkingType,
    OperatStatus,
)
from models.energy_models import EnergyVector as EnergyVectorModel
from models.usage import Usage
from models.enums import TypeUsage, DataSourceType

from .packs import _VILLES, _RUES


# Mapping from pack type_site string to TypeSite enum
_TYPE_MAP = {
    "commerce": TypeSite.COMMERCE,
    "bureau": TypeSite.BUREAU,
    "entrepot": TypeSite.ENTREPOT,
    "hotel": TypeSite.HOTEL,
    "sante": TypeSite.SANTE,
    "enseignement": TypeSite.ENSEIGNEMENT,
    "magasin": TypeSite.MAGASIN,
    "copropriete": TypeSite.COPROPRIETE,
}

_PARKING_MAP = {
    "outdoor": ParkingType.OUTDOOR,
    "indoor": ParkingType.INDOOR,
    "underground": ParkingType.UNDERGROUND,
    "unknown": ParkingType.UNKNOWN,
}

# Profiles → schedule mapping
_PROFILE_SCHEDULES = {
    "office": {"open_days": "0,1,2,3,4", "open_time": "08:00", "close_time": "19:00", "is_24_7": False},
    "hotel": {"open_days": "0,1,2,3,4,5,6", "open_time": "00:00", "close_time": "23:59", "is_24_7": True},
    "retail": {"open_days": "0,1,2,3,4,5", "open_time": "09:00", "close_time": "20:00", "is_24_7": False},
    "warehouse": {"open_days": "0,1,2,3,4", "open_time": "06:00", "close_time": "20:00", "is_24_7": False},
    "school": {"open_days": "0,1,2,3,4", "open_time": "07:30", "close_time": "18:00", "is_24_7": False},
    "hospital": {"open_days": "0,1,2,3,4,5,6", "open_time": "00:00", "close_time": "23:59", "is_24_7": True},
}

# V1.1: Usage breakdown per profile — (TypeUsage, label, description, pct_of_total, is_significant)
_USAGE_BREAKDOWN = {
    "office": [
        (TypeUsage.CHAUFFAGE, "Chauffage", "Chauffage bureaux et communs", 35, True),
        (TypeUsage.CLIMATISATION, "Climatisation", "Climatisation bureaux", 15, True),
        (TypeUsage.ECLAIRAGE, "Éclairage", "Eclairage interieur et exterieur", 20, True),
        (TypeUsage.IT, "IT & Bureautique", "Serveurs, postes de travail, reseau", 15, False),
        (TypeUsage.VENTILATION, "Ventilation", "VMC et CTA", 8, False),
        (TypeUsage.AUTRES, "Autres", "Ascenseurs, sanitaires, divers", 7, False),
    ],
    "warehouse": [
        (TypeUsage.CHAUFFAGE, "Chauffage", "Chauffage entrepot", 25, True),
        (TypeUsage.ECLAIRAGE, "Éclairage", "Eclairage industriel", 20, True),
        (TypeUsage.PROCESS, "Process", "Equipements de manutention, chariots", 30, True),
        (TypeUsage.VENTILATION, "Ventilation", "Ventilation entrepot", 10, False),
        (TypeUsage.IT, "IT", "Systemes de gestion logistique", 8, False),
        (TypeUsage.AUTRES, "Autres", "Securite, portes automatiques", 7, False),
    ],
    "hotel": [
        (TypeUsage.CHAUFFAGE, "Chauffage", "Chauffage chambres et communs", 25, True),
        (TypeUsage.CLIMATISATION, "Climatisation", "Climatisation chambres", 15, True),
        (TypeUsage.ECS, "ECS", "Eau chaude sanitaire chambres", 15, True),
        (TypeUsage.ECLAIRAGE, "Éclairage", "Eclairage chambres, hall, exterieur", 15, False),
        (TypeUsage.PROCESS, "Cuisine & Buanderie", "Cuisine, buanderie, spa", 15, True),
        (TypeUsage.IT, "IT", "Gestion hoteliere, Wi-Fi, TV", 8, False),
        (TypeUsage.AUTRES, "Autres", "Ascenseurs, piscine, divers", 7, False),
    ],
    "school": [
        (TypeUsage.CHAUFFAGE, "Chauffage", "Chauffage salles de classe", 45, True),
        (TypeUsage.ECLAIRAGE, "Éclairage", "Eclairage salles, couloirs, gymnase", 20, True),
        (TypeUsage.VENTILATION, "Ventilation", "Ventilation salles", 10, False),
        (TypeUsage.IT, "IT", "Salles informatiques, videoprojection", 10, False),
        (TypeUsage.AUTRES, "Autres", "Cantine, sanitaires, alarmes", 15, False),
    ],
    "hospital": [
        (TypeUsage.CHAUFFAGE, "Chauffage", "Chauffage et traitement air medical", 25, True),
        (TypeUsage.CLIMATISATION, "Climatisation", "Climatisation blocs et chambres", 15, True),
        (TypeUsage.ECLAIRAGE, "Éclairage", "Eclairage blocs, chambres, couloirs", 15, False),
        (TypeUsage.PROCESS, "Équipements médicaux", "Imagerie, sterilisation, blocs", 25, True),
        (TypeUsage.IT, "IT", "Systemes d'information hospitalier", 10, False),
        (TypeUsage.AUTRES, "Autres", "Ascenseurs, buanderie, cuisine", 10, False),
    ],
    "retail": [
        (TypeUsage.CLIMATISATION, "Climatisation", "Climatisation surface de vente", 30, True),
        (TypeUsage.ECLAIRAGE, "Éclairage", "Eclairage vitrine et interieur", 30, True),
        (TypeUsage.CHAUFFAGE, "Chauffage", "Chauffage reserve et bureaux", 15, False),
        (TypeUsage.IT, "IT & Caisses", "Caisses, systeme de gestion", 10, False),
        (TypeUsage.AUTRES, "Autres", "Enseignes, securite, reserves", 15, False),
    ],
}

# Mapping sous-compteur suffix → TypeUsage (pour lier sub_meters aux usages)
_SUB_METER_USAGE_MAP = {
    "CVC": TypeUsage.CHAUFFAGE,
    "ECLAIRAGE": TypeUsage.ECLAIRAGE,
    "CHAMBRES": TypeUsage.CLIMATISATION,
    "CUISINE": TypeUsage.PROCESS,
    "SPA": TypeUsage.ECS,
    "PROCESS": TypeUsage.PROCESS,
    "IT": TypeUsage.IT,
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
        nom=org_cfg["nom"],
        type_client=org_cfg["type_client"],
        actif=True,
        siren=org_cfg["siren"],
        is_demo=True,
    )
    db.add(org)
    db.flush()

    # 2. Entites juridiques
    entites = []
    for ej_cfg in pack["entites"]:
        ej = EntiteJuridique(
            organisation_id=org.id,
            nom=ej_cfg["nom"],
            siren=ej_cfg["siren"],
            siret=ej_cfg.get("siret"),
            naf_code=ej_cfg.get("naf_code"),
            region_code=ej_cfg.get("region_code"),
        )
        db.add(ej)
        entites.append(ej)
    db.flush()

    # 3. Portefeuilles (entite_idx routing for multi-entite packs like helios)
    portefeuilles = []
    for pf_cfg in pack["portefeuilles"]:
        ej_idx = pf_cfg.get("entite_idx", 0)
        pf = Portefeuille(
            entite_juridique_id=entites[ej_idx].id,
            nom=pf_cfg["nom"],
            description=pf_cfg["description"],
        )
        db.add(pf)
        portefeuilles.append(pf)
    db.flush()

    # 4. Sites + meters
    all_sites = []
    all_meters = []
    site_profiles = {}  # site_id → profile name
    buildings_map = {}  # site_id → [batiment_id, ...] (helios only)

    if "sites_explicit" in pack:
        # ── Explicit sites mode (helios) ─────────────────────────────────
        for site_counter, spec in enumerate(pack["sites_explicit"]):
            pf = portefeuilles[spec["portefeuille_idx"]]

            site = Site(
                portefeuille_id=pf.id,
                nom=spec["nom"],
                type=_TYPE_MAP.get(spec["type_site"], TypeSite.BUREAU),
                adresse=f"{rng.randint(1, 200)} {_RUES[site_counter % len(_RUES)]}",
                code_postal=spec["cp"],
                ville=spec["ville"],
                region=spec["region"],
                surface_m2=spec["surface_m2"],
                nombre_employes=spec.get("employees", 50),
                latitude=spec["lat"],
                longitude=spec["lon"],
                actif=True,
                is_demo=True,
                tertiaire_area_m2=spec.get("tertiaire_area_m2"),
                parking_area_m2=spec.get("parking_m2"),
                parking_type=_PARKING_MAP.get(spec.get("parking_type"), ParkingType.UNKNOWN),
                roof_area_m2=spec.get("roof_m2"),
                naf_code=spec.get("naf"),
                annual_kwh_total=spec.get("annual_kwh"),
                data_source="demo",
                siret=f"{pack['entites'][0]['siren']}{10000 + site_counter:05d}",
            )
            site._cvc_kw = spec.get("cvc_kw", 100)
            site._city = spec.get("ville", "")  # V107: per-city weather
            site._surface_m2 = spec["surface_m2"]  # V107: surface-normalized conso
            site._type_site = spec.get("type_site", "bureau")  # V107: benchmarks
            db.add(site)
            db.flush()

            site_profiles[site.id] = spec.get("profile", "office")
            all_sites.append(site)

            # OPERAT status
            operat_str = spec.get("operat_status")
            if operat_str:
                site.operat_status = getattr(OperatStatus, operat_str, None)

            # Batiments (explicit list)
            bat_ids = []
            for b_spec in spec.get("buildings", []):
                bat = Batiment(
                    site_id=site.id,
                    nom=b_spec["nom"],
                    surface_m2=b_spec["surface_m2"],
                    annee_construction=b_spec.get("annee", 2000),
                    cvc_power_kw=b_spec.get("cvc_kw"),
                )
                db.add(bat)
                db.flush()
                bat_ids.append(bat.id)
            buildings_map[site.id] = bat_ids

            # V1.1: Usage records per batiment (enriched)
            profile_key = spec.get("profile", "office")
            usage_defs = _USAGE_BREAKDOWN.get(profile_key, _USAGE_BREAKDOWN["office"])
            site_usages = {}  # TypeUsage → Usage (for sub-meter linking)
            for bat_id in bat_ids:
                bat_surface = next(
                    (
                        b["surface_m2"]
                        for b in spec.get("buildings", [])
                        if bat_id
                        == bat_ids[spec.get("buildings", []).index(b) if b in spec.get("buildings", []) else 0]
                    ),
                    spec["surface_m2"] / max(1, len(bat_ids)),
                )
                for usage_type, label, desc, pct, signif in usage_defs:
                    u = Usage(
                        batiment_id=bat_id,
                        type=usage_type,
                        label=label,
                        description=desc,
                        pct_of_total=pct,
                        is_significant=signif,
                        surface_m2=round(bat_surface * pct / 100, 0) if bat_surface else None,
                        data_source=DataSourceType.MESURE_DIRECTE,
                    )
                    db.add(u)
                    db.flush()
                    site_usages[usage_type] = u

            # Meter (electricity)
            meter_id_str = f"DEMO-HELI-{site.id:04d}"
            meter = Meter(
                meter_id=meter_id_str,
                name=f"Compteur {site.nom}",
                site_id=site.id,
                energy_vector=EnergyVectorModel.ELECTRICITY,
                subscribed_power_kva=float(spec.get("psub_kva", 80)),
                tariff_type="C5",
                is_active=True,
            )
            db.add(meter)
            db.flush()
            all_meters.append(meter)

            # Compteur legacy (elec)
            db.add(
                Compteur(
                    site_id=site.id,
                    type=TypeCompteur.ELECTRICITE,
                    numero_serie=f"DEMO-E-{site.id:04d}",
                    puissance_souscrite_kw=meter.subscribed_power_kva,
                    meter_id=meter_id_str,
                    energy_vector=EnergyVector.ELECTRICITY,
                    actif=True,
                    data_source="demo",
                )
            )

            # Gas compteur + Meter if needed (V107: gas readings require a Meter)
            if spec.get("gas"):
                gas_meter_id_str = f"DEMO-GAS-{site.id:04d}"
                gas_meter = Meter(
                    meter_id=gas_meter_id_str,
                    name=f"Compteur Gaz {site.nom}",
                    site_id=site.id,
                    energy_vector=EnergyVectorModel.GAS,
                    subscribed_power_kva=0,  # N/A for gas
                    tariff_type="T3",
                    is_active=True,
                )
                db.add(gas_meter)
                db.flush()
                all_meters.append(gas_meter)

                db.add(
                    Compteur(
                        site_id=site.id,
                        type=TypeCompteur.GAZ,
                        numero_serie=f"DEMO-G-{site.id:04d}",
                        meter_id=gas_meter_id_str,
                        energy_vector=EnergyVector.GAS,
                        actif=True,
                        data_source="demo",
                    )
                )

            # Step 26 + V1.1: Sous-compteurs lies aux usages
            sub_meter_specs = spec.get("sub_meters")
            if sub_meter_specs:
                for sm_spec in sub_meter_specs:
                    # Resolve usage_id from suffix mapping
                    matched_usage_type = _SUB_METER_USAGE_MAP.get(sm_spec["suffix"])
                    matched_usage = site_usages.get(matched_usage_type) if matched_usage_type else None

                    sub = Meter(
                        meter_id=f"SUB-{meter_id_str}-{sm_spec['suffix']}",
                        name=sm_spec["name"],
                        site_id=site.id,
                        parent_meter_id=meter.id,
                        energy_vector=EnergyVectorModel.ELECTRICITY,
                        subscribed_power_kva=0,
                        is_active=True,
                        usage_id=matched_usage.id if matched_usage else None,
                    )
                    sub._pct = sm_spec["pct"]  # fraction of parent conso
                    db.add(sub)
                    db.flush()
                    all_meters.append(sub)

            # Operating schedule
            profile_name = spec.get("profile", "office")
            sched_cfg = _PROFILE_SCHEDULES.get(profile_name, _PROFILE_SCHEDULES["office"])
            db.add(
                SiteOperatingSchedule(
                    site_id=site.id,
                    open_days=sched_cfg["open_days"],
                    open_time=sched_cfg["open_time"],
                    close_time=sched_cfg["close_time"],
                    is_24_7=sched_cfg["is_24_7"],
                )
            )

        db.flush()

    else:
        # ── Randomized sites mode (tertiaire) ──────────────────
        sites_per_pf = size_cfg["sites_per_pf"]
        site_groups = pack["site_groups"]

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
                    code_postal=cp,
                    ville=ville,
                    region=region,
                    surface_m2=surface,
                    nombre_employes=rng.randint(*group["employees_range"]),
                    latitude=lat + rng.uniform(-0.02, 0.02),
                    longitude=lon + rng.uniform(-0.02, 0.02),
                    actif=True,
                    is_demo=True,
                    tertiaire_area_m2=surface if surface >= 1000 else None,
                    parking_area_m2=parking,
                    parking_type=_PARKING_MAP.get(group.get("parking_type"), ParkingType.UNKNOWN),
                    roof_area_m2=roof,
                    naf_code=group.get("naf") if site_counter < (count * 0.8) else None,
                    annual_kwh_total=annual_kwh,
                    data_source="demo",
                    siret=f"{pack['entites'][0]['siren']}{rng.randint(10000, 99999)}",
                )
                # Store transient attributes for generators
                site._cvc_kw = cvc_kw
                site._city = ville  # V107: per-city weather
                site._surface_m2 = surface  # V107: surface-normalized conso
                site._type_site = site_type_str  # V107: benchmarks
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
                db.flush()

                # V1.1: Usage records per batiment (enriched)
                usage_defs = _USAGE_BREAKDOWN.get(profile_name, _USAGE_BREAKDOWN["office"])
                for usage_type, label, desc, pct, signif in usage_defs:
                    db.add(
                        Usage(
                            batiment_id=bat.id,
                            type=usage_type,
                            label=label,
                            description=desc,
                            pct_of_total=pct,
                            is_significant=signif,
                            surface_m2=round(surface * pct / 100, 0) if surface else None,
                            data_source=DataSourceType.ESTIMATION_PRORATA,
                        )
                    )

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
                db.add(
                    Compteur(
                        site_id=site.id,
                        type=TypeCompteur.ELECTRICITE,
                        numero_serie=f"DEMO-E-{site.id:04d}",
                        puissance_souscrite_kw=meter.subscribed_power_kva,
                        meter_id=meter_id_str,
                        energy_vector=EnergyVector.ELECTRICITY,
                        actif=True,
                        data_source="demo",
                    )
                )

                # Gas meter for some sites
                if rng.random() < group.get("gas_pct", 0):
                    db.add(
                        Compteur(
                            site_id=site.id,
                            type=TypeCompteur.GAZ,
                            numero_serie=f"DEMO-G-{site.id:04d}",
                            meter_id=f"GRD{rng.randint(100000000, 999999999)}",
                            energy_vector=EnergyVector.GAS,
                            actif=True,
                            data_source="demo",
                        )
                    )

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
        "buildings_map": buildings_map,
    }
