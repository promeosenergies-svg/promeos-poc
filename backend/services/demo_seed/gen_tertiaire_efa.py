"""
PROMEOS — Seed 3 EFA Tertiaire pour la demo HELIOS (Step 30).

EFA 1 : Paris bureaux 3500m2 — mono-occupation, declaration en cours (ACTIVE)
EFA 2 : Nice hotel 4000m2 — multi-occupation (hotel + restaurant), ACTIVE avec issues
EFA 3 : Lyon bureaux 1200m2 — conforme, declaration soumise (ACTIVE + SUBMITTED_SIMULATED)

Idempotent : verifie par nom avant creation.
"""

import json
from datetime import date

from models import Batiment
from models.tertiaire import (
    TertiaireEfa,
    TertiaireEfaBuilding,
    TertiaireResponsibility,
    TertiairePerimeterEvent,
    TertiaireDeclaration,
)
from models.enums import (
    EfaStatut,
    EfaRole,
    DeclarationStatus,
    PerimeterEventType,
)


def _get_or_create_building(db, site, nom, surface_m2, annee):
    """Cherche un batiment existant ou en cree un."""
    existing = (
        db.query(Batiment)
        .filter(Batiment.site_id == site.id, Batiment.nom == nom)
        .first()
    )
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
    return bat.id


def _resolve_org_id(site):
    """Remonte l'org_id depuis site → portefeuille → entite → org."""
    try:
        return site.portefeuille.entite_juridique.organisation_id
    except Exception:
        return 1


def seed_tertiaire_efa(db, helios_sites: dict) -> list:
    """
    Cree 3 EFA avec batiments, responsabilites et declarations.
    helios_sites : dict {nom_court: site_object} — ex. {"paris": site, "nice": site, "lyon": site}
    Retourne la liste des EFA creees.
    """
    paris = helios_sites.get("paris")
    nice = helios_sites.get("nice")
    lyon = helios_sites.get("lyon")

    if not paris:
        return []

    efas_created = []

    # ── EFA 1 : Paris Bureaux — mono-occupation, en cours ──────────────
    nom_paris = "EFA Siege HELIOS Paris"
    if not db.query(TertiaireEfa).filter_by(nom=nom_paris).first():
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
                checklist_json=json.dumps({
                    "surface_renseignee": True,
                    "consommations_importees": True,
                    "attestation_affichage": False,
                    "referent_designe": True,
                }),
            )
        )
        efas_created.append(efa_paris)

    # ── EFA 2 : Nice Hotel — multi-occupation ─────────────────────────
    if nice:
        nom_nice = "EFA Hotel HELIOS Nice"
        if not db.query(TertiaireEfa).filter_by(nom=nom_nice).first():
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
                    checklist_json=json.dumps({
                        "surface_renseignee": True,
                        "consommations_importees": False,
                        "attestation_affichage": False,
                        "referent_designe": False,
                    }),
                )
            )
            efas_created.append(efa_nice)

    # ── EFA 3 : Lyon Bureaux — conforme, soumise ─────────────────────
    if lyon:
        nom_lyon = "EFA Bureau Regional Lyon"
        if not db.query(TertiaireEfa).filter_by(nom=nom_lyon).first():
            org_id = _resolve_org_id(lyon)

            efa_lyon = TertiaireEfa(
                org_id=org_id,
                site_id=lyon.id,
                nom=nom_lyon,
                statut=EfaStatut.ACTIVE,
                role_assujetti=EfaRole.LOCATAIRE,
                reporting_start=date(2024, 1, 1),
                reporting_end=date(2024, 12, 31),
                notes="Declaration 2024 soumise. Site conforme.",
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
                    checklist_json=json.dumps({
                        "surface_renseignee": True,
                        "consommations_importees": True,
                        "attestation_affichage": True,
                        "referent_designe": True,
                    }),
                )
            )
            efas_created.append(efa_lyon)

    db.flush()
    return efas_created
