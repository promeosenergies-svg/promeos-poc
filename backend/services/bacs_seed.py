"""
PROMEOS - BACS Demo Seed
Seed 10 demo sites with diverse BACS configurations covering all edge cases.
"""

import json
from datetime import date

from sqlalchemy.orm import Session

from models import (
    Site,
    BacsAsset,
    BacsCvcSystem,
    BacsInspection,
    CvcSystemType,
    CvcArchitecture,
    InspectionStatus,
)
from services.bacs_engine import evaluate_bacs


# ── 10 demo BACS configurations ──

_BACS_DEMO_CONFIGS = [
    {
        "site_name": "Tour Montparnasse",
        "is_tertiary": True,
        "pc_date": "1970-06-01",
        "systems": [
            {
                "type": "heating",
                "arch": "cascade",
                "units": [{"label": "PAC 1", "kw": 250}, {"label": "PAC 2", "kw": 200}],
            },
        ],
        "inspections": [],
        "note": ">290 kW, deadline 2025, no attestation",
    },
    {
        "site_name": "Centre Commercial Velizy",
        "is_tertiary": True,
        "pc_date": "1985-03-15",
        "systems": [
            {
                "type": "cooling",
                "arch": "network",
                "units": [{"label": "Chiller A", "kw": 180}, {"label": "Chiller B", "kw": 140}],
            },
        ],
        "inspections": [
            {"date": "2023-06-01", "status": "completed", "report": "RPT-VLZ-2023"},
        ],
        "note": ">290 kW cooling, inspection done",
    },
    {
        "site_name": "Immeuble Bureaux Nanterre",
        "is_tertiary": True,
        "pc_date": "2005-09-20",
        "systems": [
            {
                "type": "heating",
                "arch": "independent",
                "units": [{"label": "Chaudiere 1", "kw": 150}, {"label": "Chaudiere 2", "kw": 80}],
            },
        ],
        "inspections": [],
        "note": "70-290 kW (max=150), deadline 2030",
    },
    {
        "site_name": "Hopital Lyon-Sud",
        "is_tertiary": True,
        "pc_date": "1975-01-10",
        "systems": [
            {"type": "heating", "arch": "cascade", "units": [{"label": "Chaufferie centrale", "kw": 500}]},
            {
                "type": "cooling",
                "arch": "cascade",
                "units": [{"label": "Groupe froid 1", "kw": 200}, {"label": "Groupe froid 2", "kw": 100}],
            },
        ],
        "inspections": [
            {"date": "2021-03-15", "status": "completed", "report": "RPT-LYS-2021"},
        ],
        "note": ">290 kW heating+cooling, inspection a jour",
    },
    {
        "site_name": "Mairie Bordeaux",
        "is_tertiary": True,
        "pc_date": "1920-07-14",
        "systems": [
            {"type": "heating", "arch": "independent", "units": [{"label": "Chauffage ancien", "kw": 95}]},
        ],
        "inspections": [],
        "tri_context": {"cout_bacs_eur": 150000, "aides_pct": 10, "conso_kwh": 60000, "gain_pct": 8, "prix_kwh": 0.15},
        "note": "70-290 kW, TRI > 10 ans = exemption",
    },
    {
        "site_name": "Lycee Toulouse",
        "is_tertiary": True,
        "pc_date": "1990-09-01",
        "renewal_events": [{"date": "2024-02-15", "system": "heating", "kw": 200}],
        "systems": [
            {"type": "heating", "arch": "network", "units": [{"label": "PAC neuve", "kw": 200}]},
        ],
        "inspections": [],
        "note": "70-290 kW, renouvellement 2024 = trigger",
    },
    {
        "site_name": "Hotel Nice Promenade",
        "is_tertiary": True,
        "pc_date": "2010-04-01",
        "systems": [
            {
                "type": "cooling",
                "arch": "independent",
                "units": [{"label": "Split 1", "kw": 30}, {"label": "Split 2", "kw": 30}],
            },
        ],
        "inspections": [],
        "note": "<70 kW = OUT_OF_SCOPE",
    },
    {
        "site_name": "Data Center Strasbourg",
        "is_tertiary": True,
        "pc_date": None,
        "systems": [
            {
                "type": "cooling",
                "arch": "cascade",
                "units": [{"label": "CRAC 1", "kw": 300}, {"label": "CRAC 2", "kw": 200}],
            },
        ],
        "inspections": [],
        "note": ">290 kW, DQ BLOCKED (no PC date)",
    },
    {
        "site_name": "Clinique Marseille",
        "is_tertiary": True,
        "pc_date": "1998-11-30",
        "systems": [
            {"type": "heating", "arch": "network", "units": [{"label": "Chaufferie", "kw": 180}]},
        ],
        "inspections": [
            {"date": "2018-01-15", "status": "completed", "report": "RPT-MRS-2018"},
        ],
        "note": "70-290 kW, inspection overdue (>5 ans)",
    },
    {
        "site_name": "Residence Etudiante Lille",
        "is_tertiary": False,
        "pc_date": "2015-06-01",
        "systems": [
            {"type": "heating", "arch": "independent", "units": [{"label": "Chaudiere", "kw": 40}]},
        ],
        "inspections": [],
        "note": "<70 kW + non-tertiary = OUT_OF_SCOPE",
    },
]


def seed_bacs_demo(db: Session) -> dict:
    """
    Seed BACS assets for existing demo sites.
    Matches by site name or creates lightweight sites if needed.
    Returns summary of seeded assets.
    """
    seeded = []
    errors = []

    for i, cfg in enumerate(_BACS_DEMO_CONFIGS):
        site_name = cfg["site_name"]

        # Find or create site
        site = db.query(Site).filter(Site.nom == site_name).first()
        if not site:
            from models import TypeSite

            site = Site(
                nom=site_name,
                type=TypeSite.BUREAU,
                ville=site_name.split()[-1] if len(site_name.split()) > 1 else "Paris",
                surface_m2=2000,
                actif=True,
                data_source="demo",
            )
            db.add(site)
            db.flush()

        # Skip if already has BACS asset
        existing = db.query(BacsAsset).filter(BacsAsset.site_id == site.id).first()
        if existing:
            seeded.append({"site": site_name, "status": "skipped", "reason": "already exists"})
            continue

        # Create BacsAsset
        asset = BacsAsset(
            site_id=site.id,
            is_tertiary_non_residential=cfg["is_tertiary"],
            pc_date=date.fromisoformat(cfg["pc_date"]) if cfg.get("pc_date") else None,
            renewal_events_json=json.dumps(cfg.get("renewal_events", [])),
            responsible_party_json=json.dumps({"type": "owner", "name": f"Gestionnaire {site_name}"}),
        )
        db.add(asset)
        db.flush()

        # Create CVC systems
        for sys_cfg in cfg.get("systems", []):
            sys = BacsCvcSystem(
                asset_id=asset.id,
                system_type=CvcSystemType(sys_cfg["type"]),
                architecture=CvcArchitecture(sys_cfg["arch"]),
                units_json=json.dumps(sys_cfg["units"]),
            )
            db.add(sys)

        # Create inspections
        for insp_cfg in cfg.get("inspections", []):
            insp = BacsInspection(
                asset_id=asset.id,
                inspection_date=date.fromisoformat(insp_cfg["date"]),
                status=InspectionStatus(insp_cfg["status"]),
                report_ref=insp_cfg.get("report"),
            )
            db.add(insp)

        db.flush()

        # Run evaluation
        tri_ctx = cfg.get("tri_context")
        assessment = evaluate_bacs(db, site.id, tri_context=tri_ctx)

        seeded.append(
            {
                "site": site_name,
                "site_id": site.id,
                "asset_id": asset.id,
                "status": "created",
                "is_obligated": assessment.is_obligated if assessment else None,
                "putile_kw": assessment.threshold_applied if assessment else None,
                "note": cfg.get("note", ""),
            }
        )

    return {"seeded": seeded, "total": len(seeded), "errors": errors}
