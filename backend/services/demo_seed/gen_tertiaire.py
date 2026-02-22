"""
PROMEOS V39 - Demo Seed: Tertiaire / OPERAT Generator
Creates EFA, buildings, responsibilities, perimeter events, quality issues,
and declaration stubs from the existing seeded sites.
"""
import random
from datetime import date, timedelta

from models import Batiment
from models.tertiaire import (
    TertiaireEfa, TertiaireEfaBuilding, TertiaireResponsibility,
    TertiairePerimeterEvent, TertiaireDeclaration, TertiaireProofArtifact,
    TertiaireDataQualityIssue, TertiaireEfaLink,
)
from models.enums import (
    EfaStatut, EfaRole, DeclarationStatus, PerimeterEventType,
    DataQualityIssueSeverity, DataQualityIssueStatus,
)

# Realistic French entity names
_RESPONSABLES = [
    ("Jean Dupont", "j.dupont@sci-terrasses.fr"),
    ("Marie Leclerc", "m.leclerc@sci-terrasses.fr"),
    ("Pierre Martin", "p.martin@sci-terrasses.fr"),
    ("Sophie Moreau", "s.moreau@gestion-immobiliere.fr"),
    ("Lucas Bernard", "l.bernard@cabinet-audit.fr"),
]

_USAGE_LABELS = [
    "Bureaux", "Commerce", "Enseignement", "Sante", "Hotellerie",
    "Logistique", "Restauration", "Services publics",
]

_EFA_NAMES = [
    "EFA Bureaux Haussmann", "EFA Tour Montparnasse Est", "EFA Centre Hospitalier Nord",
    "EFA Groupe Scolaire Jules Ferry", "EFA Hotel Mercure Gare",
    "EFA Residence Services Seniors", "EFA Centre Commercial Rivoli",
    "EFA Entrepot Logistique Sud", "EFA Mairie Annexe", "EFA Clinique Pasteur",
    "EFA Campus Universitaire", "EFA Immeuble Grand Siecle",
]

_EVENT_DESCRIPTIONS = [
    "Changement de locataire — bail commercial",
    "Periode de vacance partielle (etage 3)",
    "Renovation thermique facade nord",
    "Scission d'activite — bureaux / commerce",
    "Fusion avec EFA adjacente",
    "Changement d'usage: stockage vers bureaux",
]

# Control codes that match tertiaire_service.py
_QUALITY_ISSUES = [
    {
        "code": "TERTIAIRE_NO_BUILDING",
        "severity": DataQualityIssueSeverity.CRITICAL,
        "message_fr": "Aucun batiment associe a cette EFA",
        "impact_fr": "Impossible de calculer la surface assujettie",
        "action_fr": "Associer au moins un batiment avec sa surface",
    },
    {
        "code": "MISSING_SURFACE",
        "severity": DataQualityIssueSeverity.HIGH,
        "message_fr": "Surface manquante sur un ou plusieurs batiments",
        "impact_fr": "Le calcul de trajectoire OPERAT sera incorrect",
        "action_fr": "Renseigner la surface en m2 de chaque batiment",
    },
    {
        "code": "MISSING_USAGE",
        "severity": DataQualityIssueSeverity.MEDIUM,
        "message_fr": "Usage non defini sur un ou plusieurs batiments",
        "impact_fr": "Le referentiel de consommation ne peut etre determine",
        "action_fr": "Renseigner l'usage principal (bureaux, enseignement, etc.)",
    },
    {
        "code": "NO_RESPONSIBILITY",
        "severity": DataQualityIssueSeverity.HIGH,
        "message_fr": "Aucun responsable declare pour cette EFA",
        "impact_fr": "La declaration OPERAT ne peut etre soumise sans responsable identifie",
        "action_fr": "Ajouter au moins un responsable (proprietaire ou locataire)",
    },
    {
        "code": "NO_REPORTING_PERIOD",
        "severity": DataQualityIssueSeverity.MEDIUM,
        "message_fr": "Periode de reporting non definie",
        "impact_fr": "L'annee de reference OPERAT ne peut etre calculee",
        "action_fr": "Definir la periode de reporting (date debut / date fin)",
    },
    {
        "code": "SURFACE_COHERENCE",
        "severity": DataQualityIssueSeverity.LOW,
        "message_fr": "La somme des surfaces semble incoherente (< 500 m2 ou > 50 000 m2)",
        "impact_fr": "Verification recommandee avant declaration",
        "action_fr": "Verifier la coherence des surfaces declarees",
    },
]


def generate_tertiaire(db, org, sites: list, rng: random.Random,
                       buildings_map: dict = None) -> dict:
    """
    Generate EFA + sub-entities for demo.
    Creates 1 EFA per site (for sites with tertiaire_area_m2 >= 1000),
    plus a few EFA with deliberate gaps to generate quality issues.
    """
    efas_created = 0
    buildings_created = 0
    responsibilities_created = 0
    events_created = 0
    issues_created = 0
    declarations_created = 0
    links_created = 0
    proofs_created = 0

    efa_objects = []

    for idx, site in enumerate(sites):
        tertiaire_area = getattr(site, 'tertiaire_area_m2', 0) or 0
        if tertiaire_area < 1000:
            continue

        name = _EFA_NAMES[idx % len(_EFA_NAMES)]
        # Vary statuses: most active, some draft, one closed
        if idx == 0:
            statut = EfaStatut.CLOSED
        elif idx % 5 == 0:
            statut = EfaStatut.DRAFT
        else:
            statut = EfaStatut.ACTIVE

        role = rng.choice([EfaRole.PROPRIETAIRE, EfaRole.LOCATAIRE, EfaRole.MANDATAIRE])

        # Some EFAs deliberately missing reporting period (for quality issues demo)
        has_reporting = idx % 4 != 3

        efa = TertiaireEfa(
            org_id=org.id,
            site_id=site.id,
            nom=f"{name} — {site.nom}",
            statut=statut,
            role_assujetti=role,
            reporting_start=date(2020, 1, 1) if has_reporting else None,
            reporting_end=date(2025, 12, 31) if has_reporting else None,
            notes=f"EFA generee par seed demo — site {site.nom}",
        )
        db.add(efa)
        db.flush()
        efa_objects.append(efa)
        efas_created += 1

        # Buildings — use real batiment IDs when available (helios)
        real_bat_ids = (buildings_map or {}).get(site.id, [])
        if real_bat_ids:
            # ── Helios: link to real Batiment records ────────────────
            for bat_id in real_bat_ids:
                bat = db.query(Batiment).get(bat_id)
                usage = _USAGE_LABELS[rng.randint(0, len(_USAGE_LABELS) - 1)]
                building = TertiaireEfaBuilding(
                    efa_id=efa.id,
                    building_id=bat_id,
                    usage_label=usage,
                    surface_m2=bat.surface_m2 if bat else None,
                )
                db.add(building)
                buildings_created += 1
        elif idx % 6 != 5:  # ~83% have buildings (randomized mode)
            n_buildings = rng.randint(1, 3)
            for b in range(n_buildings):
                usage = _USAGE_LABELS[rng.randint(0, len(_USAGE_LABELS) - 1)]
                # Some deliberately missing surface or usage
                has_surface = not (idx % 7 == 0 and b == 0)
                has_usage = not (idx % 8 == 0 and b == 0)

                building = TertiaireEfaBuilding(
                    efa_id=efa.id,
                    building_id=None,  # Not linking to real batiment table in seed
                    usage_label=usage if has_usage else None,
                    surface_m2=round(tertiaire_area / n_buildings + rng.uniform(-200, 200), 1) if has_surface else None,
                )
                db.add(building)
                buildings_created += 1

        # Responsibilities — most get 1-2, some deliberately have none
        if idx % 5 != 4:  # ~80% have responsibilities
            n_resp = rng.randint(1, 2)
            for r in range(n_resp):
                resp_name, resp_email = _RESPONSABLES[rng.randint(0, len(_RESPONSABLES) - 1)]
                resp_role = rng.choice([EfaRole.PROPRIETAIRE, EfaRole.LOCATAIRE])
                resp = TertiaireResponsibility(
                    efa_id=efa.id,
                    role=resp_role,
                    entity_type="personne_physique",
                    entity_value=resp_name,
                    contact_email=resp_email,
                )
                db.add(resp)
                responsibilities_created += 1

        # Perimeter events — ~40% of EFAs have events
        if rng.random() < 0.4:
            evt_type = rng.choice(list(PerimeterEventType))
            evt_desc = _EVENT_DESCRIPTIONS[rng.randint(0, len(_EVENT_DESCRIPTIONS) - 1)]
            days_ago = rng.randint(30, 365)
            event = TertiairePerimeterEvent(
                efa_id=efa.id,
                type=evt_type,
                effective_date=date.today() - timedelta(days=days_ago),
                description=evt_desc,
            )
            db.add(event)
            events_created += 1

        # Quality issues — deliberate gaps produce specific issues
        year = date.today().year
        if idx % 6 == 5:
            # No buildings → TERTIAIRE_NO_BUILDING
            issue_def = _QUALITY_ISSUES[0]
            db.add(TertiaireDataQualityIssue(
                efa_id=efa.id, year=year, code=issue_def["code"],
                severity=issue_def["severity"],
                message_fr=issue_def["message_fr"],
                impact_fr=issue_def["impact_fr"],
                action_fr=issue_def["action_fr"],
                status=DataQualityIssueStatus.OPEN,
            ))
            issues_created += 1

        if idx % 7 == 0:
            # Missing surface
            issue_def = _QUALITY_ISSUES[1]
            db.add(TertiaireDataQualityIssue(
                efa_id=efa.id, year=year, code=issue_def["code"],
                severity=issue_def["severity"],
                message_fr=issue_def["message_fr"],
                impact_fr=issue_def["impact_fr"],
                action_fr=issue_def["action_fr"],
                status=DataQualityIssueStatus.OPEN,
            ))
            issues_created += 1

        if idx % 5 == 4:
            # No responsibility
            issue_def = _QUALITY_ISSUES[3]
            db.add(TertiaireDataQualityIssue(
                efa_id=efa.id, year=year, code=issue_def["code"],
                severity=issue_def["severity"],
                message_fr=issue_def["message_fr"],
                impact_fr=issue_def["impact_fr"],
                action_fr=issue_def["action_fr"],
                status=DataQualityIssueStatus.OPEN,
            ))
            issues_created += 1

        if not has_reporting:
            issue_def = _QUALITY_ISSUES[4]
            db.add(TertiaireDataQualityIssue(
                efa_id=efa.id, year=year, code=issue_def["code"],
                severity=issue_def["severity"],
                message_fr=issue_def["message_fr"],
                impact_fr=issue_def["impact_fr"],
                action_fr=issue_def["action_fr"],
                status=DataQualityIssueStatus.OPEN,
            ))
            issues_created += 1

        # Also add some already-resolved issues for realism
        if rng.random() < 0.3:
            issue_def = rng.choice(_QUALITY_ISSUES[1:])
            db.add(TertiaireDataQualityIssue(
                efa_id=efa.id, year=year - 1, code=issue_def["code"],
                severity=issue_def["severity"],
                message_fr=issue_def["message_fr"],
                impact_fr=issue_def["impact_fr"],
                action_fr=issue_def["action_fr"],
                status=DataQualityIssueStatus.RESOLVED,
            ))
            issues_created += 1

        # Declarations — active EFAs get a draft or prechecked declaration
        if statut == EfaStatut.ACTIVE:
            decl_status = rng.choice([DeclarationStatus.DRAFT, DeclarationStatus.PRECHECKED])
            db.add(TertiaireDeclaration(
                efa_id=efa.id, year=year,
                status=decl_status,
            ))
            declarations_created += 1

        # Proof artifacts — ~30% of EFAs have a proof
        if rng.random() < 0.3:
            proof_type = rng.choice([
                "Attestation OPERAT", "Dossier de modulation",
                "Audit energetique", "Plan de sobriete",
            ])
            db.add(TertiaireProofArtifact(
                efa_id=efa.id,
                type=proof_type,
                owner_role=role,
                valid_from=date(year - 1, 1, 1),
                valid_to=date(year, 12, 31),
            ))
            proofs_created += 1

    # EFA Links — create a few links between EFAs (turnover, scission)
    if len(efa_objects) >= 4:
        link_pairs = [
            (efa_objects[0], efa_objects[1], "scission"),
            (efa_objects[2], efa_objects[3], "turnover"),
        ]
        for child, parent, reason in link_pairs:
            db.add(TertiaireEfaLink(
                child_efa_id=child.id,
                parent_efa_id=parent.id,
                reason=reason,
            ))
            links_created += 1

    db.flush()

    return {
        "efas_created": efas_created,
        "buildings_created": buildings_created,
        "responsibilities_created": responsibilities_created,
        "events_created": events_created,
        "issues_created": issues_created,
        "declarations_created": declarations_created,
        "proofs_created": proofs_created,
        "links_created": links_created,
    }
