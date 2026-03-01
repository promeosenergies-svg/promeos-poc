"""
PROMEOS - Demo Seed: EMS Explorer Pre-built Views (V87)
Creates EmsSavedView and EmsCollection records for the Helios demo.
These are shown in the EMS Consumption Explorer sidebar on first open.
"""
import json

from models.ems_models import EmsSavedView, EmsCollection


def generate_ems_views(db, sites: list) -> dict:
    """
    Create pre-built EMS Explorer collections (site groupings) and saved views.
    Tertiary sites = sites with tertiaire_area_m2 set (excludes Toulouse warehouse).
    """
    all_ids = [s.id for s in sites]
    tertiary_ids = [s.id for s in sites if (s.tertiaire_area_m2 or 0) > 0]

    collections = [
        EmsCollection(
            name="Groupe HELIOS \u2014 Tous sites",
            scope_type="org",
            site_ids_json=json.dumps(all_ids),
            is_favorite=1,
        ),
        EmsCollection(
            name="Sites tertiaires",
            scope_type="custom",
            site_ids_json=json.dumps(tertiary_ids),
            is_favorite=0,
        ),
    ]

    views = [
        EmsSavedView(
            name="Panorama annuel \u2014 Groupe HELIOS",
            config_json=json.dumps({
                "site_ids": all_ids,
                "granularity": "monthly",
                "mode": "overlay",
                "metric": "kwh",
                "date_from": "2024-01-01",
                "date_to": "2025-12-31",
            }),
        ),
        EmsSavedView(
            name="Monitoring 30j \u2014 15 min",
            config_json=json.dumps({
                "site_ids": all_ids,
                "granularity": "15min",
                "mode": "aggregate",
                "metric": "kw",
                "date_from": "last_30d",
                "date_to": "now",
            }),
        ),
        EmsSavedView(
            name="Comparaison sites \u2014 quotidien",
            config_json=json.dumps({
                "site_ids": all_ids,
                "granularity": "daily",
                "mode": "stack",
                "metric": "kwh",
                "date_from": "last_90d",
                "date_to": "now",
            }),
        ),
        EmsSavedView(
            name="Signature energetique \u2014 2 ans",
            config_json=json.dumps({
                "site_ids": all_ids,
                "granularity": "daily",
                "mode": "aggregate",
                "metric": "kwh",
                "date_from": "last_730d",
                "date_to": "now",
            }),
        ),
    ]

    for obj in collections + views:
        db.add(obj)
    db.flush()

    return {
        "views_count": len(views),
        "collections_count": len(collections),
    }
