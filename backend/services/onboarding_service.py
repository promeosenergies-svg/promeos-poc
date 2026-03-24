"""
PROMEOS - Service Onboarding
Logique metier pour la creation d'un patrimoine (org + sites + batiments + obligations).
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Batiment,
    Compteur,
    Obligation,
    TypeSite,
    TypeCompteur,
    StatutConformite,
    TypeObligation,
    ParkingType,
    OperatStatus,
    DeliveryPoint,
    DeliveryPointEnergyType,
    DeliveryPointStatus,
    not_deleted,
)
from services.compliance_engine import bacs_deadline_for_power, BACS_SEUIL_HAUT
from services.compliance_coordinator import recompute_site_full as recompute_site
from services.naf_classifier import classify_naf


# ========================================
# CVC Power estimation (from seed_data)
# ========================================

# Ratios W/m2 typiques France par type de site
_CVC_RATIOS = {
    TypeSite.MAGASIN: (80, 120),
    TypeSite.BUREAU: (40, 70),
    TypeSite.USINE: (30, 60),
    TypeSite.ENTREPOT: (20, 40),
    TypeSite.COMMERCE: (70, 110),
    TypeSite.COPROPRIETE: (25, 45),
    TypeSite.LOGEMENT_SOCIAL: (25, 45),
    TypeSite.COLLECTIVITE: (40, 65),
    TypeSite.HOTEL: (60, 100),
    TypeSite.SANTE: (50, 90),
    TypeSite.ENSEIGNEMENT: (35, 60),
}


def estimate_cvc_power(type_site: TypeSite, surface_m2: float) -> float:
    """Estime la puissance CVC (kW) d'un site selon son type et surface.

    Utilise la mediane du range W/m² par type de site (deterministe).
    Meme site cree 2 fois = meme puissance CVC = meme obligation BACS.
    Hypothese : mediane des ratios ADEME typiques par usage.
    """
    lo, hi = _CVC_RATIOS.get(type_site, (40, 70))
    watt_per_m2 = (lo + hi) / 2  # mediane deterministe
    return round(surface_m2 * watt_per_m2 / 1000, 1)


def is_tertiaire(type_site: TypeSite) -> bool:
    """Determine si un type de site est soumis au decret tertiaire."""
    return type_site in {
        TypeSite.MAGASIN,
        TypeSite.BUREAU,
        TypeSite.COMMERCE,
        TypeSite.HOTEL,
        TypeSite.SANTE,
        TypeSite.ENSEIGNEMENT,
        TypeSite.COLLECTIVITE,
        TypeSite.ENTREPOT,
    }


# ========================================
# Creation helpers
# ========================================


def create_batiment_for_site(db: Session, site: Site, batiment_nom: str = None) -> Batiment:
    """Cree un batiment principal pour un site.

    Par defaut le batiment porte le meme nom que le site (regle 1 site = 1 batiment).
    """
    cvc_kw = estimate_cvc_power(site.type, site.surface_m2 or 1000)
    bat = Batiment(
        site_id=site.id,
        nom=batiment_nom or site.nom,
        surface_m2=site.surface_m2 or 1000,
        cvc_power_kw=cvc_kw,
    )
    db.add(bat)
    db.flush()
    return bat


def create_obligations_for_site(db: Session, site: Site, cvc_power_kw: float) -> List[Obligation]:
    """Cree les obligations reglementaires applicables a un site."""
    obligations = []

    # Decret tertiaire: sites tertiaires > 1000 m2
    surface = site.tertiaire_area_m2 or site.surface_m2 or 0
    if is_tertiaire(site.type) and surface >= 1000:
        obl = Obligation(
            site_id=site.id,
            type=TypeObligation.DECRET_TERTIAIRE,
            description="Reduction -40% en 2030 vs 2010",
            echeance=datetime(2030, 12, 31).date(),
            statut=StatutConformite.A_RISQUE,
            avancement_pct=0.0,
        )
        db.add(obl)
        obligations.append(obl)

    # BACS: si CVC > 70 kW
    deadline = bacs_deadline_for_power(cvc_power_kw)
    if deadline:
        seuil_label = ">290 kW" if cvc_power_kw > BACS_SEUIL_HAUT else ">70 kW"
        obl = Obligation(
            site_id=site.id,
            type=TypeObligation.BACS,
            description=f"GTB/GTC obligatoire {seuil_label} (CVC {cvc_power_kw} kW)",
            echeance=deadline,
            statut=StatutConformite.A_RISQUE,
            avancement_pct=0.0,
        )
        db.add(obl)
        obligations.append(obl)

    db.flush()
    return obligations


def ensure_delivery_points_for_site(db: Session, site_id: int) -> int:
    """Auto-create DeliveryPoints for compteurs that have a meter_id but no DP.

    Rule: for each active compteur with meter_id and no delivery_point_id,
    find or create a DeliveryPoint with code=meter_id on the same site.
    Then link the compteur to the DP.

    Returns count of DPs created (not linked-to-existing).
    """
    orphan_compteurs = (
        db.query(Compteur)
        .filter(
            Compteur.site_id == site_id,
            not_deleted(Compteur),
            Compteur.delivery_point_id.is_(None),
            Compteur.meter_id.isnot(None),
            Compteur.meter_id != "",
        )
        .all()
    )

    created = 0
    for c in orphan_compteurs:
        # Skip auto-generated meter_ids (not real PRM/PCE)
        if c.meter_id.startswith("AUTO-") or c.meter_id.startswith("SEED-") or c.meter_id.startswith("DEMO-"):
            continue

        # Deduce energy type from compteur type
        energy_type = None
        if c.type == TypeCompteur.ELECTRICITE:
            energy_type = DeliveryPointEnergyType.ELEC
        elif c.type == TypeCompteur.GAZ:
            energy_type = DeliveryPointEnergyType.GAZ

        # Find existing DP with same code on same site
        existing_dp = (
            db.query(DeliveryPoint)
            .filter(
                DeliveryPoint.code == c.meter_id,
                DeliveryPoint.site_id == site_id,
                not_deleted(DeliveryPoint),
            )
            .first()
        )

        if existing_dp:
            c.delivery_point_id = existing_dp.id
        else:
            dp = DeliveryPoint(
                code=c.meter_id,
                energy_type=energy_type,
                site_id=site_id,
                status=DeliveryPointStatus.ACTIVE,
                data_source=c.data_source or "auto",
                data_source_ref="auto_provision",
            )
            db.add(dp)
            db.flush()
            c.delivery_point_id = dp.id
            created += 1

    if orphan_compteurs:
        db.flush()

    return created


def provision_site(db: Session, site: Site) -> dict:
    """Provision complet d'un site: batiment + obligations + compliance + delivery points.

    Returns dict with creation details.
    """
    bat = create_batiment_for_site(db, site)
    obligations = create_obligations_for_site(db, site, bat.cvc_power_kw)
    dp_created = ensure_delivery_points_for_site(db, site.id)
    recompute_site(db, site.id)
    return {
        "batiment_id": bat.id,
        "cvc_power_kw": bat.cvc_power_kw,
        "obligations": len(obligations),
        "delivery_points_created": dp_created,
    }


def create_organisation_full(
    db: Session,
    org_nom: str,
    org_siren: str,
    org_type_client: str,
    portefeuilles_data: List[dict],
) -> dict:
    """Cree une organisation complete: org + entite juridique + portefeuilles.

    Returns dict with created IDs.
    """
    # Organisation
    org = Organisation(nom=org_nom, type_client=org_type_client, actif=True, siren=org_siren)
    db.add(org)
    db.flush()

    # Entite juridique (auto depuis SIREN)
    entite = EntiteJuridique(
        organisation_id=org.id,
        nom=org_nom,
        siren=org_siren or "000000000",
    )
    db.add(entite)
    db.flush()

    # Portefeuilles
    portefeuilles = []
    if not portefeuilles_data:
        portefeuilles_data = [{"nom": "Principal", "description": "Portefeuille par defaut"}]

    for p_data in portefeuilles_data:
        p = Portefeuille(
            entite_juridique_id=entite.id,
            nom=p_data.get("nom", "Principal"),
            description=p_data.get("description"),
        )
        db.add(p)
        portefeuilles.append(p)

    db.flush()

    return {
        "organisation_id": org.id,
        "entite_juridique_id": entite.id,
        "portefeuille_ids": [p.id for p in portefeuilles],
        "default_portefeuille_id": portefeuilles[0].id,
    }


def create_site_from_data(
    db: Session,
    portefeuille_id: int,
    nom: str,
    type_site: Optional[str],
    naf_code: Optional[str] = None,
    adresse: Optional[str] = None,
    code_postal: Optional[str] = None,
    ville: Optional[str] = None,
    surface_m2: Optional[float] = None,
) -> Site:
    """Cree un site a partir de donnees brutes.

    Si type_site est absent/vide, classifie automatiquement via le code NAF.
    """
    # Classification automatique si type manquant
    if type_site:
        try:
            ts = TypeSite(type_site)
        except ValueError:
            ts = classify_naf(naf_code) if naf_code else TypeSite.BUREAU
    else:
        ts = classify_naf(naf_code) if naf_code else TypeSite.BUREAU

    # Surface par defaut raisonnable
    surface = surface_m2 or 1000.0

    # Tertiaire area = surface si tertiaire
    tertiaire_area = surface if is_tertiaire(ts) else None

    site = Site(
        portefeuille_id=portefeuille_id,
        nom=nom,
        type=ts,
        adresse=adresse,
        code_postal=code_postal,
        ville=ville,
        surface_m2=surface,
        actif=True,
        naf_code=naf_code,
        tertiaire_area_m2=tertiaire_area,
        operat_status=OperatStatus.NOT_STARTED,
    )
    db.add(site)
    db.flush()
    return site
