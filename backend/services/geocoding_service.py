"""
PROMEOS — Service de géocodage via API BAN (Base Adresse Nationale)
https://adresse.data.gouv.fr/api-doc/adresse

Utilisé pour convertir les adresses postales des sites en coordonnées GPS.
Persistance en base : latitude, longitude, geocoding_source, geocoding_score, geocoded_at, geocoding_status.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from models import Site

logger = logging.getLogger("promeos.geocoding")

BAN_SEARCH_URL = "https://api-adresse.data.gouv.fr/search/"
BAN_BATCH_URL = "https://api-adresse.data.gouv.fr/search/csv/"
TIMEOUT_S = 10


def _build_query(site: Site) -> str:
    """Build a geocoding query string from site address fields."""
    parts = [site.adresse or "", site.code_postal or "", site.ville or ""]
    return " ".join(p.strip() for p in parts if p.strip())


def geocode_address(query: str) -> dict:
    """
    Geocode a single address via BAN API.
    Returns: { lat, lng, score, label, source, status }
    """
    if not query or len(query.strip()) < 3:
        return {"lat": None, "lng": None, "score": 0, "label": None, "source": "ban", "status": "not_found"}

    try:
        resp = httpx.get(BAN_SEARCH_URL, params={"q": query, "limit": 1}, timeout=TIMEOUT_S)
        resp.raise_for_status()
        data = resp.json()

        features = data.get("features", [])
        if not features:
            return {"lat": None, "lng": None, "score": 0, "label": None, "source": "ban", "status": "not_found"}

        feat = features[0]
        props = feat.get("properties", {})
        coords = feat.get("geometry", {}).get("coordinates", [None, None])
        score = props.get("score", 0)

        status = "ok" if score >= 0.5 else "partial" if score >= 0.3 else "not_found"

        return {
            "lat": coords[1],  # GeoJSON: [lng, lat]
            "lng": coords[0],
            "score": round(score, 4),
            "label": props.get("label", ""),
            "source": "ban",
            "status": status,
        }
    except Exception as e:
        logger.warning("BAN geocoding error for %r: %s", query, e)
        return {"lat": None, "lng": None, "score": 0, "label": None, "source": "ban", "status": "error"}


def geocode_site(db: Session, site_id: int, force: bool = False) -> dict:
    """
    Geocode a single site and persist coordinates.
    Skip if already geocoded unless force=True.
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return {"error": "Site not found"}

    # Skip if already geocoded with good score
    if not force and site.geocoding_status == "ok" and site.latitude and site.longitude:
        return {
            "site_id": site.id,
            "status": "skipped",
            "lat": site.latitude,
            "lng": site.longitude,
            "score": site.geocoding_score,
        }

    query = _build_query(site)
    if not query:
        return {"site_id": site.id, "status": "no_address", "lat": None, "lng": None}

    result = geocode_address(query)

    # Persist
    if result["lat"] is not None:
        site.latitude = result["lat"]
        site.longitude = result["lng"]
    site.geocoding_source = result["source"]
    site.geocoding_score = result["score"]
    site.geocoded_at = datetime.now(timezone.utc)
    site.geocoding_status = result["status"]
    db.flush()

    return {
        "site_id": site.id,
        "status": result["status"],
        "lat": result["lat"],
        "lng": result["lng"],
        "score": result["score"],
        "label": result.get("label"),
    }


def geocode_org_sites(db: Session, org_id: int, force: bool = False) -> list[dict]:
    """Geocode all sites for an org. Returns list of results."""
    from models import Portefeuille, EntiteJuridique

    pf_ids = [
        r.id
        for r in db.query(Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    ]
    if not pf_ids:
        return []

    sites = db.query(Site).filter(Site.portefeuille_id.in_(pf_ids), Site.actif == True).all()
    results = []
    for site in sites:
        r = geocode_site(db, site.id, force=force)
        results.append(r)
    db.commit()
    return results
