"""
PROMEOS — OPERAT CSV Export Service (Chantier 2)
Generates CSV file compatible with OPERAT bulk import format.
Columns: N° EFA, Nom EFA, SIRET, Surface (m²), Usage, Année référence,
         Conso élec (kWh), Conso gaz (kWh), Conso réseau (kWh), Total (kWh),
         Objectif -40% (kWh), Statut déclaration
"""

import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from models import (
    TertiaireEfa,
    TertiaireEfaBuilding,
    TertiaireDeclaration,
    TertiaireResponsibility,
    Site,
    Batiment,
    EnergyInvoice,
    EnergyContract,
    BillingEnergyType,
    AuditLog,
    Portefeuille,
    EntiteJuridique,
    not_deleted,
)

logger = logging.getLogger("promeos.operat_export")

# OPERAT CSV header (format compatible avec la plateforme ADEME)
OPERAT_COLUMNS = [
    "N_EFA",
    "Nom_EFA",
    "Site",
    "Ville",
    "Surface_m2",
    "Usage_principal",
    "Annee_reference",
    "Conso_elec_kWh",
    "Conso_gaz_kWh",
    "Conso_reseau_kWh",
    "Total_kWh",
    "Objectif_2030_kWh",
    "Objectif_2040_kWh",
    "Objectif_2050_kWh",
    "Statut_declaration",
    "Role_assujetti",
    "Responsable",
]


def _get_site_conso(db: Session, site_id: int, year: int) -> dict:
    """Get annual consumption for a site by energy type from invoices."""
    invoices = (
        db.query(EnergyInvoice, EnergyContract.energy_type)
        .outerjoin(EnergyContract, EnergyInvoice.contract_id == EnergyContract.id)
        .filter(
            EnergyInvoice.site_id == site_id,
        )
        .all()
    )

    elec_kwh = 0.0
    gaz_kwh = 0.0

    for inv, energy_type in invoices:
        inv_year = None
        if inv.period_start:
            inv_year = inv.period_start.year
        elif inv.issue_date:
            inv_year = inv.issue_date.year
        if inv_year != year:
            continue
        kwh = inv.energy_kwh or 0
        if energy_type == BillingEnergyType.GAZ:
            gaz_kwh += kwh
        else:
            elec_kwh += kwh

    return {"elec": round(elec_kwh), "gaz": round(gaz_kwh), "reseau": 0}


def validate_operat_export(
    db: Session,
    org_id: int,
    year: int,
    efa_ids: Optional[List[int]] = None,
) -> dict:
    """
    Validate OPERAT export data before generating CSV.
    Returns: {valid: bool, errors: [...], warnings: [...]}
    Errors = blocking, Warnings = non-blocking but flagged.
    """
    errors = []
    warnings = []

    query = db.query(TertiaireEfa).filter(
        TertiaireEfa.org_id == org_id,
        not_deleted(TertiaireEfa),
    )
    if efa_ids:
        query = query.filter(TertiaireEfa.id.in_(efa_ids))

    efas = query.all()

    if not efas:
        errors.append({"code": "NO_EFA", "message": "Aucune EFA trouvee pour cette organisation"})
        return {"valid": False, "errors": errors, "warnings": warnings, "efa_count": 0}

    for efa in efas:
        prefix = f"EFA #{efa.id} ({efa.nom})"

        # Surface check
        buildings = db.query(TertiaireEfaBuilding).filter(TertiaireEfaBuilding.efa_id == efa.id).all()
        total_surface = sum(b.surface_m2 or 0 for b in buildings)
        if total_surface == 0:
            errors.append({"code": "NO_SURFACE", "efa_id": efa.id, "message": f"{prefix}: surface = 0 m2"})

        # Consumption check
        conso = _get_site_conso(db, efa.site_id, year) if efa.site_id else {"elec": 0, "gaz": 0, "reseau": 0}
        total_kwh = conso["elec"] + conso["gaz"] + conso["reseau"]
        if total_kwh == 0:
            warnings.append({"code": "NO_CONSO", "efa_id": efa.id, "message": f"{prefix}: aucune consommation {year}"})

        # Responsable check
        resp = db.query(TertiaireResponsibility).filter(TertiaireResponsibility.efa_id == efa.id).first()
        if not resp:
            warnings.append({"code": "NO_RESP", "efa_id": efa.id, "message": f"{prefix}: responsable non renseigne"})

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "efa_count": len(efas),
    }


def generate_operat_csv(
    db: Session,
    org_id: int,
    year: int,
    efa_ids: Optional[List[int]] = None,
) -> str:
    """
    Generate OPERAT-compatible CSV for org's EFAs.
    Returns CSV as string.
    """
    query = db.query(TertiaireEfa).filter(
        TertiaireEfa.org_id == org_id,
        not_deleted(TertiaireEfa),
    )
    if efa_ids:
        query = query.filter(TertiaireEfa.id.in_(efa_ids))

    efas = query.order_by(TertiaireEfa.id).all()

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=OPERAT_COLUMNS, delimiter=";")
    writer.writeheader()

    for efa in efas:
        buildings = db.query(TertiaireEfaBuilding).filter(TertiaireEfaBuilding.efa_id == efa.id).all()

        total_surface = sum(b.surface_m2 or 0 for b in buildings)
        usages = list(set(b.usage_label for b in buildings if b.usage_label))
        usage_label = usages[0] if usages else "Bureau"

        # Site info
        site_nom = ""
        ville = ""
        if efa.site_id:
            site = db.query(Site).filter(Site.id == efa.site_id).first()
            if site:
                site_nom = site.nom or ""
                ville = site.ville or ""

        # Consumption — source prioritaire : TertiaireEfaConsumption
        from models import TertiaireEfaConsumption

        efa_conso = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == efa.id, TertiaireEfaConsumption.year == year)
            .first()
        )
        if efa_conso:
            conso = {
                "elec": efa_conso.kwh_elec or 0,
                "gaz": efa_conso.kwh_gaz or 0,
                "reseau": efa_conso.kwh_reseau or 0,
            }
            total_kwh = efa_conso.kwh_total
        else:
            # Fallback : factures site puis Site.annual_kwh_total
            conso = {"elec": 0, "gaz": 0, "reseau": 0}
            if efa.site_id:
                conso = _get_site_conso(db, efa.site_id, year)
            total_kwh = conso["elec"] + conso["gaz"] + conso["reseau"]
            if total_kwh == 0 and efa.site_id:
                site_fb = db.query(Site).filter(Site.id == efa.site_id).first()
                if site_fb and site_fb.annual_kwh_total:
                    conso["elec"] = round(site_fb.annual_kwh_total)
                    total_kwh = conso["elec"]

        # Baseline — source prioritaire : EFA.reference_year_kwh
        baseline_kwh = (
            efa.reference_year_kwh if hasattr(efa, "reference_year_kwh") and efa.reference_year_kwh else total_kwh
        )

        # Declaration status
        decl = (
            db.query(TertiaireDeclaration)
            .filter(
                TertiaireDeclaration.efa_id == efa.id,
                TertiaireDeclaration.year == year,
            )
            .first()
        )
        statut = decl.status.value if decl else "non_declare"

        # Responsable
        resp = db.query(TertiaireResponsibility).filter(TertiaireResponsibility.efa_id == efa.id).first()
        resp_name = resp.entity_value if resp else ""

        # Objectifs decret tertiaire — bases sur la BASELINE (pas la conso courante)
        obj_2030 = round(baseline_kwh * 0.60) if baseline_kwh else 0
        obj_2040 = round(baseline_kwh * 0.50) if baseline_kwh else 0
        obj_2050 = round(baseline_kwh * 0.40) if baseline_kwh else 0

        writer.writerow(
            {
                "N_EFA": efa.id,
                "Nom_EFA": efa.nom,
                "Site": site_nom,
                "Ville": ville,
                "Surface_m2": round(total_surface),
                "Usage_principal": usage_label,
                "Annee_reference": year,
                "Conso_elec_kWh": conso["elec"],
                "Conso_gaz_kWh": conso["gaz"],
                "Conso_reseau_kWh": conso["reseau"],
                "Total_kWh": total_kwh,
                "Objectif_2030_kWh": obj_2030,
                "Objectif_2040_kWh": obj_2040,
                "Objectif_2050_kWh": obj_2050,
                "Statut_declaration": statut,
                "Role_assujetti": efa.role_assujetti.value if efa.role_assujetti else "",
                "Responsable": resp_name,
            }
        )

    csv_content = output.getvalue()
    logger.info(f"OPERAT CSV export: org_id={org_id}, year={year}, efas={len(efas)}")
    return csv_content


def log_operat_export(
    db: Session,
    org_id: int,
    year: int,
    efa_count: int,
    user_id: Optional[int] = None,
):
    """Audit log for OPERAT export (sensitive action)."""
    log = AuditLog(
        action="operat_export",
        user_id=user_id,
        resource_type="operat_csv",
        resource_id=str(org_id),
        detail_json=json.dumps(
            {
                "org_id": org_id,
                "year": year,
                "efa_count": efa_count,
                "exported_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
    )
    db.add(log)
    db.commit()
