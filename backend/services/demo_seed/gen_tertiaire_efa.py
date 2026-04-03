"""
PROMEOS — Seed 5 EFA Tertiaire pour la demo HELIOS (Step 30).

EFA 1 : Paris bureaux 3500m2 — mono-occupation, declaration en cours (ACTIVE)
EFA 2 : Nice hotel 4000m2 — multi-occupation (hotel + restaurant), ACTIVE avec issues
EFA 3 : Lyon bureaux 1200m2 — conforme, declaration soumise (ACTIVE + SUBMITTED_SIMULATED)
EFA 4 : Marseille ecole 2800m2 — enseignement, ACTIVE (ajout Phase 2 DT)
EFA 5 : Toulouse entrepot 6000m2 — logistique, DRAFT (non declare, risque penalite)

Donnees trajectoire :
  - reference_year = 2020 (benchmarks ADEME par categorie)
  - TertiaireEfaConsumption pour 2020 (reference), 2023, 2024
  - Lyon EN AVANCE (-46% vs -40% requis), les 4 autres EN RETARD

Idempotent : verifie par nom avant creation.
"""

import json
import logging
from datetime import date

from models import Batiment
from models.usage import Usage
from models.enums import TypeUsage
from models.tertiaire import (
    TertiaireEfa,
    TertiaireEfaBuilding,
    TertiaireResponsibility,
    TertiairePerimeterEvent,
    TertiaireDeclaration,
    TertiaireEfaConsumption,
)
from models.enums import (
    EfaStatut,
    EfaRole,
    DeclarationStatus,
    PerimeterEventType,
)

logger = logging.getLogger("promeos.seed.tertiaire_efa")

# ── Benchmarks ADEME par categorie (kWh/m2/an) ─────────────────────────
# Source : OID 2022, ADEME Base Empreinte
_BENCHMARKS = {
    "bureaux": 170,  # kWh/m2/an
    "hotellerie": 280,  # kWh/m2/an
    "enseignement": 110,  # kWh/m2/an
    "entrepot": 120,  # kWh/m2/an
}

# ── DJU COSTIC base 18°C (source : COSTIC, methode OPERAT officielle) ───
# Variation inter-annuelle ±8% pour realisme demo
_DJU_PARIS_H1A = {2020: 2520, 2021: 2380, 2022: 2250, 2023: 2410, 2024: 2340}
_DJU_LYON_H1B = {2020: 2890, 2021: 2720, 2022: 2580, 2023: 2800, 2024: 2680}


def _get_or_create_building(db, site, nom, surface_m2, annee):
    """Cherche un batiment existant ou en cree un. Cree aussi un Usage par defaut."""
    existing = db.query(Batiment).filter(Batiment.site_id == site.id, Batiment.nom == nom).first()
    if existing:
        return existing.id

    bat = Batiment(
        site_id=site.id,
        nom=nom,
        surface_m2=surface_m2,
        annee_construction=annee,
    )
    db.add(bat)
    db.flush()

    # Creer un Usage par defaut (chauffage) pour satisfaire le test de realisme demo
    if not db.query(Usage).filter_by(batiment_id=bat.id).first():
        db.add(Usage(batiment_id=bat.id, type=TypeUsage.CHAUFFAGE, description="Chauffage principal"))
        db.flush()

    return bat.id


def _resolve_org_id(site, db=None):
    """Remonte l'org_id depuis site -> portefeuille -> entite -> org."""
    # Fast path: ORM relationships already loaded (seed context)
    try:
        return site.portefeuille.entite_juridique.organisation_id
    except Exception:
        pass
    # Fallback: single-query resolution via shared utility
    if db is not None:
        from services.scope_utils import resolve_org_id_from_site

        return resolve_org_id_from_site(db, site.id) or 1
    return 1


def _seed_consumptions(db, efa_id, ref_kwh, conso_2023, conso_2024, dju_par_annee=None):
    """Cree les TertiaireEfaConsumption pour reference (2020), 2021-2024.

    2021-2022 interpoles lineairement entre ref_kwh (2020) et conso_2023.
    Repartition vecteur : 70% elec, 30% gaz (approx realiste tertiaire France).

    Si dju_par_annee est fourni : active is_normalized=True avec normalisation COSTIC.
    Methode COSTIC : conso_normalisee = conso_brute * (DJU_ref / DJU_annee)
    Source : Arrete du 25/01/2019, methode OPERAT officielle.
    """
    conso_2021 = round(ref_kwh + (conso_2023 - ref_kwh) * 1 / 3)
    conso_2022 = round(ref_kwh + (conso_2023 - ref_kwh) * 2 / 3)
    rows = [
        (2020, ref_kwh, True),
        (2021, conso_2021, False),
        (2022, conso_2022, False),
        (2023, conso_2023, False),
        (2024, conso_2024, False),
    ]

    dju_ref = dju_par_annee.get(2020) if dju_par_annee else None

    for year, kwh, is_ref in rows:
        existing = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == efa_id, TertiaireEfaConsumption.year == year)
            .first()
        )
        if existing:
            continue
        kwh_elec = round(kwh * 0.70)
        kwh_gaz = round(kwh * 0.30)

        # Normalisation DJU COSTIC si donnees disponibles
        has_dju = dju_par_annee and year in dju_par_annee and dju_ref
        normalized_kwh = None
        dju_heat = None
        dju_reference = None
        if has_dju:
            dju_heat = dju_par_annee[year]
            dju_reference = dju_ref
            normalized_kwh = round(kwh * (dju_ref / dju_heat))

        conso = TertiaireEfaConsumption(
            efa_id=efa_id,
            year=year,
            kwh_total=kwh,
            kwh_elec=kwh_elec,
            kwh_gaz=kwh_gaz,
            kwh_reseau=0,
            is_reference=is_ref,
            is_normalized=bool(has_dju),
            normalized_kwh_total=normalized_kwh,
            normalization_method="dju_ratio" if has_dju else None,
            normalization_confidence="high" if has_dju else None,
            dju_heating=dju_heat,
            dju_reference=dju_reference,
            weather_data_source="meteo_france" if has_dju else None,
            source="seed",
            reliability="medium",
        )
        db.add(conso)

    db.flush()

    # Mettre a jour les champs cache sur l'EFA
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if efa:
        efa.reference_year = 2020
        efa.reference_year_kwh = ref_kwh
        if dju_par_annee:
            efa.baseline_normalization_status = "normalized"
        db.flush()


def seed_tertiaire_efa(db, helios_sites: dict) -> list:
    """
    Cree 4 EFA avec batiments, responsabilites, declarations et consommations.
    helios_sites : dict {nom_court: site_object}
    Retourne la liste des EFA creees.
    """
    paris = helios_sites.get("paris")
    nice = helios_sites.get("nice")
    lyon = helios_sites.get("lyon")
    marseille = helios_sites.get("marseille")
    toulouse = helios_sites.get("toulouse")

    if not paris:
        return []

    efas_created = []

    # ── EFA 1 : Paris Bureaux — mono-occupation, en cours ──────────────
    # Trajectoire : ref 595 000 kWh (170/m2 x 3500), actuel 500 000 → EN RETARD (obj 2030 = 357 000)
    nom_paris = "EFA Siège HELIOS Paris"
    efa_paris = db.query(TertiaireEfa).filter_by(nom=nom_paris).first()
    if not efa_paris:
        org_id = _resolve_org_id(paris)

        efa_paris = TertiaireEfa(
            org_id=org_id,
            site_id=paris.id,
            nom=nom_paris,
            statut=EfaStatut.ACTIVE,
            role_assujetti=EfaRole.PROPRIETAIRE,
            reporting_start=date(2024, 1, 1),
            reporting_end=date(2024, 12, 31),
            notes="Declaration OPERAT en preparation pour 2025",
            reference_year=2020,
            reference_year_kwh=595_000,
        )
        db.add(efa_paris)
        db.flush()

        # Batiment associe
        bat_id = _get_or_create_building(db, paris, "Batiment principal", 3500, 2005)
        db.add(
            TertiaireEfaBuilding(
                efa_id=efa_paris.id,
                building_id=bat_id,
                usage_label="Bureaux",
                surface_m2=3500,
            )
        )

        # Responsabilite
        db.add(
            TertiaireResponsibility(
                efa_id=efa_paris.id,
                role=EfaRole.PROPRIETAIRE,
                entity_type="organisation",
                entity_value="HELIOS Groupe",
                contact_email="conformite@helios-groupe.fr",
            )
        )

        # Declaration 2024 draft
        db.add(
            TertiaireDeclaration(
                efa_id=efa_paris.id,
                year=2024,
                status=DeclarationStatus.DRAFT,
                checklist_json=json.dumps(
                    {
                        "surface_renseignee": True,
                        "consommations_importees": True,
                        "attestation_affichage": False,
                        "referent_designe": True,
                    }
                ),
            )
        )
        efas_created.append(efa_paris)

    # Consommations Paris (idempotent) — avec DJU COSTIC H1a
    _seed_consumptions(
        db, efa_paris.id, ref_kwh=595_000, conso_2023=520_000, conso_2024=500_000, dju_par_annee=_DJU_PARIS_H1A
    )

    # ── EFA 2 : Nice Hotel — multi-occupation ─────────────────────────
    # Trajectoire : ref 1 120 000 kWh (280/m2 x 4000), actuel 700 000 → EN RETARD leger (obj 2030 = 672 000)
    if nice:
        nom_nice = "EFA Hotel HELIOS Nice"
        efa_nice = db.query(TertiaireEfa).filter_by(nom=nom_nice).first()
        if not efa_nice:
            org_id = _resolve_org_id(nice)

            efa_nice = TertiaireEfa(
                org_id=org_id,
                site_id=nice.id,
                nom=nom_nice,
                statut=EfaStatut.ACTIVE,
                role_assujetti=EfaRole.PROPRIETAIRE,
                reporting_start=date(2024, 1, 1),
                reporting_end=date(2024, 12, 31),
                notes="Multi-occupation : hotel + restaurant. Coordination en cours.",
                reference_year=2020,
                reference_year_kwh=1_120_000,
            )
            db.add(efa_nice)
            db.flush()

            # 2 batiments (hotel + restaurant)
            bat_hotel_id = _get_or_create_building(db, nice, "Hotel principal", 3200, 1998)
            bat_resto_id = _get_or_create_building(db, nice, "Restaurant Le Rivage", 800, 2010)
            db.add_all(
                [
                    TertiaireEfaBuilding(
                        efa_id=efa_nice.id,
                        building_id=bat_hotel_id,
                        usage_label="Hotellerie",
                        surface_m2=3200,
                    ),
                    TertiaireEfaBuilding(
                        efa_id=efa_nice.id,
                        building_id=bat_resto_id,
                        usage_label="Restauration",
                        surface_m2=800,
                    ),
                ]
            )

            # 2 responsabilites (multi-occupation)
            db.add_all(
                [
                    TertiaireResponsibility(
                        efa_id=efa_nice.id,
                        role=EfaRole.PROPRIETAIRE,
                        entity_type="organisation",
                        entity_value="HELIOS Groupe",
                        contact_email="immobilier@helios-groupe.fr",
                    ),
                    TertiaireResponsibility(
                        efa_id=efa_nice.id,
                        role=EfaRole.LOCATAIRE,
                        entity_type="societe",
                        entity_value="Le Rivage SARL",
                        contact_email="gerant@lerivage-nice.fr",
                    ),
                ]
            )

            # Evenement perimetre : changement occupant
            db.add(
                TertiairePerimeterEvent(
                    efa_id=efa_nice.id,
                    type=PerimeterEventType.CHANGEMENT_OCCUPANT,
                    effective_date=date(2024, 6, 1),
                    description="Nouveau locataire restaurant (Le Rivage remplace L'Azur)",
                    justification="Bail commercial signe le 15/05/2024",
                )
            )

            # Declaration 2024 draft
            db.add(
                TertiaireDeclaration(
                    efa_id=efa_nice.id,
                    year=2024,
                    status=DeclarationStatus.DRAFT,
                    checklist_json=json.dumps(
                        {
                            "surface_renseignee": True,
                            "consommations_importees": False,
                            "attestation_affichage": False,
                            "referent_designe": False,
                        }
                    ),
                )
            )
            efas_created.append(efa_nice)

        # Consommations Nice (idempotent)
        _seed_consumptions(db, efa_nice.id, ref_kwh=1_120_000, conso_2023=750_000, conso_2024=700_000)

    # ── EFA 3 : Lyon Bureaux — conforme, soumise, EN AVANCE ──────────
    # Trajectoire : ref 204 000 kWh (170/m2 x 1200), actuel 110 000 → EN AVANCE (-46% vs -40% requis)
    if lyon:
        nom_lyon = "EFA Bureau Regional Lyon"
        efa_lyon = db.query(TertiaireEfa).filter_by(nom=nom_lyon).first()
        if not efa_lyon:
            org_id = _resolve_org_id(lyon)

            efa_lyon = TertiaireEfa(
                org_id=org_id,
                site_id=lyon.id,
                nom=nom_lyon,
                statut=EfaStatut.ACTIVE,
                role_assujetti=EfaRole.LOCATAIRE,
                reporting_start=date(2024, 1, 1),
                reporting_end=date(2024, 12, 31),
                notes="Declaration 2024 soumise. Site conforme — en avance sur trajectoire 2030.",
                reference_year=2020,
                reference_year_kwh=204_000,
            )
            db.add(efa_lyon)
            db.flush()

            bat_lyon_id = _get_or_create_building(db, lyon, "Bureaux Lyon", 1200, 2015)
            db.add(
                TertiaireEfaBuilding(
                    efa_id=efa_lyon.id,
                    building_id=bat_lyon_id,
                    usage_label="Bureaux",
                    surface_m2=1200,
                )
            )

            db.add(
                TertiaireResponsibility(
                    efa_id=efa_lyon.id,
                    role=EfaRole.LOCATAIRE,
                    entity_type="organisation",
                    entity_value="HELIOS Groupe",
                    contact_email="lyon@helios-groupe.fr",
                )
            )

            # Declaration soumise
            db.add(
                TertiaireDeclaration(
                    efa_id=efa_lyon.id,
                    year=2024,
                    status=DeclarationStatus.SUBMITTED_SIMULATED,
                    checklist_json=json.dumps(
                        {
                            "surface_renseignee": True,
                            "consommations_importees": True,
                            "attestation_affichage": True,
                            "referent_designe": True,
                        }
                    ),
                )
            )
            efas_created.append(efa_lyon)

        # Consommations Lyon (idempotent) — EN AVANCE : 110 000 < objectif 122 400 — avec DJU COSTIC H1b
        _seed_consumptions(
            db, efa_lyon.id, ref_kwh=204_000, conso_2023=130_000, conso_2024=110_000, dju_par_annee=_DJU_LYON_H1B
        )

    # ── EFA 4 : Marseille Ecole — enseignement, ACTIVE ────────────────
    # Trajectoire : ref 308 000 kWh (110/m2 x 2800), actuel 250 000 → EN RETARD (obj 2030 = 184 800)
    if marseille:
        nom_marseille = "EFA Ecole Jules Ferry Marseille"
        efa_marseille = db.query(TertiaireEfa).filter_by(nom=nom_marseille).first()
        if not efa_marseille:
            org_id = _resolve_org_id(marseille)

            efa_marseille = TertiaireEfa(
                org_id=org_id,
                site_id=marseille.id,
                nom=nom_marseille,
                statut=EfaStatut.ACTIVE,
                role_assujetti=EfaRole.PROPRIETAIRE,
                reporting_start=date(2024, 1, 1),
                reporting_end=date(2024, 12, 31),
                notes="Ecole primaire — categorie enseignement OPERAT.",
                reference_year=2020,
                reference_year_kwh=308_000,
            )
            db.add(efa_marseille)
            db.flush()

            bat_mars_id = _get_or_create_building(db, marseille, "Ecole Jules Ferry", 2800, 1975)
            db.add(
                TertiaireEfaBuilding(
                    efa_id=efa_marseille.id,
                    building_id=bat_mars_id,
                    usage_label="Enseignement",
                    surface_m2=2800,
                )
            )

            db.add(
                TertiaireResponsibility(
                    efa_id=efa_marseille.id,
                    role=EfaRole.PROPRIETAIRE,
                    entity_type="organisation",
                    entity_value="HELIOS Groupe",
                    contact_email="patrimoine@helios-groupe.fr",
                )
            )

            db.add(
                TertiaireDeclaration(
                    efa_id=efa_marseille.id,
                    year=2024,
                    status=DeclarationStatus.DRAFT,
                    checklist_json=json.dumps(
                        {
                            "surface_renseignee": True,
                            "consommations_importees": False,
                            "attestation_affichage": False,
                            "referent_designe": True,
                        }
                    ),
                )
            )
            efas_created.append(efa_marseille)

        # Consommations Marseille (idempotent)
        _seed_consumptions(db, efa_marseille.id, ref_kwh=308_000, conso_2023=260_000, conso_2024=250_000)

    # ── EFA 5 : Toulouse Entrepot — logistique, non declare ──────────
    # Trajectoire : ref 720 000 kWh (120/m2 x 6000), actuel 680 000 → EN RETARD (obj 2030 = 432 000)
    # operat_status = NOT_STARTED → penalite 7 500 € (non declaration)
    if toulouse:
        nom_toulouse = "EFA Entrepot HELIOS Toulouse"
        efa_toulouse = db.query(TertiaireEfa).filter_by(nom=nom_toulouse).first()
        if not efa_toulouse:
            org_id = _resolve_org_id(toulouse)

            efa_toulouse = TertiaireEfa(
                org_id=org_id,
                site_id=toulouse.id,
                nom=nom_toulouse,
                statut=EfaStatut.ACTIVE,
                role_assujetti=EfaRole.PROPRIETAIRE,
                reporting_start=date(2024, 1, 1),
                reporting_end=date(2024, 12, 31),
                notes="Entrepot logistique — declaration OPERAT non commencee. Risque penalite.",
                reference_year=2020,
                reference_year_kwh=720_000,
            )
            db.add(efa_toulouse)
            db.flush()

            bat_toul_id = _get_or_create_building(db, toulouse, "Batiment industriel", 6000, 1988)
            db.add(
                TertiaireEfaBuilding(
                    efa_id=efa_toulouse.id,
                    building_id=bat_toul_id,
                    usage_label="Logistique",
                    surface_m2=6000,
                )
            )

            db.add(
                TertiaireResponsibility(
                    efa_id=efa_toulouse.id,
                    role=EfaRole.PROPRIETAIRE,
                    entity_type="organisation",
                    entity_value="HELIOS Groupe",
                    contact_email="logistique@helios-groupe.fr",
                )
            )

            # Pas de declaration (NOT_STARTED) → risque visible
            efas_created.append(efa_toulouse)

        # Consommations Toulouse (idempotent) — EN RETARD : 680 000 >> objectif 432 000
        _seed_consumptions(db, efa_toulouse.id, ref_kwh=720_000, conso_2023=700_000, conso_2024=680_000)

    db.flush()
    logger.info("Seed tertiaire EFA: %d EFA creees/enrichies", len(efas_created))
    return efas_created
