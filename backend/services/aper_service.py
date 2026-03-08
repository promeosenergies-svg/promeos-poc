"""
PROMEOS — Service APER (solarisation parkings & toitures)
Calcule l'eligibilite, estime la production PV via PVGIS,
et genere des recommandations.

Loi n 2023-175 du 10 mars 2023 (Acceleration Production Energies Renouvelables).
"""

import logging
from sqlalchemy.orm import Session

from models import Site, Portefeuille, EntiteJuridique

logger = logging.getLogger("promeos.aper")


# ── Dashboard APER ──────────────────────────────────────────────────────

def _get_org_sites(db: Session, org_id: int) -> list:
    """Recupere tous les sites actifs de l'organisation."""
    pf_ids = [
        row.id for row in
        db.query(Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    ]
    if not pf_ids:
        return []
    return db.query(Site).filter(Site.portefeuille_id.in_(pf_ids), Site.actif == True).all()


def _get_next_aper_deadline(parking_sites: list, roof_sites: list) -> str | None:
    """Retourne la prochaine echeance APER parmi les sites eligibles."""
    deadlines = [s["deadline"] for s in parking_sites + roof_sites if s.get("deadline")]
    return min(deadlines) if deadlines else None


def get_aper_dashboard(db: Session, org_id: int) -> dict:
    """
    Vue agregee APER pour l'organisation.
    Retourne : sites eligibles, surfaces totales, estimations PV.
    """
    sites = _get_org_sites(db, org_id)

    parking_eligible = []
    roof_eligible = []

    for site in sites:
        # Parking exterieur >= 1500 m2
        parking_area = getattr(site, "parking_area_m2", None) or 0
        parking_type = getattr(site, "parking_type", None)
        if parking_type:
            parking_type = parking_type.value if hasattr(parking_type, "value") else str(parking_type)

        if parking_area >= 1500 and parking_type == "outdoor":
            deadline = "2026-07-01" if parking_area > 10000 else "2028-07-01"
            parking_eligible.append({
                "site_id": site.id,
                "site_nom": site.nom,
                "surface_m2": parking_area,
                "deadline": deadline,
                "category": "large" if parking_area > 10000 else "medium",
                "latitude": site.latitude,
                "longitude": site.longitude,
            })

        # Toiture >= 500 m2
        roof_area = getattr(site, "roof_area_m2", None) or 0
        if roof_area >= 500:
            roof_eligible.append({
                "site_id": site.id,
                "site_nom": site.nom,
                "surface_m2": roof_area,
                "deadline": "2028-01-01",
                "latitude": site.latitude,
                "longitude": site.longitude,
            })

    total_parking_m2 = sum(s["surface_m2"] for s in parking_eligible)
    total_roof_m2 = sum(s["surface_m2"] for s in roof_eligible)

    return {
        "parking": {
            "eligible_count": len(parking_eligible),
            "total_surface_m2": total_parking_m2,
            "sites": parking_eligible,
        },
        "roof": {
            "eligible_count": len(roof_eligible),
            "total_surface_m2": total_roof_m2,
            "sites": roof_eligible,
        },
        "total_eligible_sites": len(set(
            [s["site_id"] for s in parking_eligible] +
            [s["site_id"] for s in roof_eligible]
        )),
        "next_deadline": _get_next_aper_deadline(parking_eligible, roof_eligible),
    }


# ── Estimation PV ───────────────────────────────────────────────────────

def _get_climate_zone(site) -> str:
    """Determine la zone climatique depuis la region."""
    zone_map = {
        "Ile-de-France": "H1", "Grand Est": "H1", "Bourgogne-Franche-Comte": "H1",
        "Hauts-de-France": "H1", "Normandie": "H1", "Centre-Val de Loire": "H2",
        "Pays de la Loire": "H2", "Bretagne": "H2", "Nouvelle-Aquitaine": "H2",
        "Auvergne-Rhone-Alpes": "H1", "Occitanie": "H3",
        "Provence-Alpes-Cote d'Azur": "H3", "Corse": "H3",
    }
    return zone_map.get(getattr(site, "region", "") or "", "H2")


def _estimate_monthly_profile(annual_kwh: float, zone: str) -> list:
    """Profil mensuel simplifie (12 valeurs)."""
    profiles = {
        "H1": [4, 5, 8, 10, 12, 13, 13, 12, 10, 7, 4, 2],
        "H2": [4, 5, 8, 10, 12, 13, 13, 12, 9, 7, 4, 3],
        "H3": [5, 6, 8, 10, 12, 13, 13, 12, 9, 6, 4, 2],
    }
    profile = profiles.get(zone, profiles["H2"])
    return [round(annual_kwh * p / 100, 0) for p in profile]


def _try_pvgis(lat: float, lon: float, peak_power_kwp: float) -> dict | None:
    """Appelle l'API PVGIS EU JRC pour estimer la production annuelle."""
    try:
        import urllib.request
        import json

        url = (
            f"https://re.jrc.ec.europa.eu/api/seriescalc"
            f"?lat={lat}&lon={lon}&peakpower={peak_power_kwp}"
            f"&loss=14&outputformat=json"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "PROMEOS/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())

        monthly_data = data.get("outputs", {}).get("monthly", {}).get("fixed", [])
        if not monthly_data:
            return None

        monthly_kwh = [round(m.get("E_m", 0), 0) for m in monthly_data[:12]]
        annual_kwh = sum(monthly_kwh)

        return {
            "annual_kwh": annual_kwh,
            "monthly_kwh": monthly_kwh,
        }
    except Exception as e:
        logger.warning(f"PVGIS call failed: {e}")
        return None


def estimate_pv_production(db: Session, site_id: int, surface_m2: float | None = None,
                           surface_type: str = "parking") -> dict:
    """
    Estime la production PV pour une surface donnee.
    Utilise le connecteur PVGIS si les coordonnees sont disponibles,
    sinon un fallback par zone climatique.
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return {"error": "Site non trouve"}

    # Surface : param ou depuis le site
    if surface_m2 is None:
        if surface_type == "parking":
            surface_m2 = getattr(site, "parking_area_m2", None) or 0
        else:
            surface_m2 = getattr(site, "roof_area_m2", None) or 0

    if surface_m2 <= 0:
        return {"error": "Surface non disponible", "site_id": site_id}

    # Parametres PV
    coverage_ratio = 0.60 if surface_type == "parking" else 0.80
    panel_surface = surface_m2 * coverage_ratio
    peak_power_kwc = panel_surface * 0.180  # 180 Wc/m2

    # Essayer PVGIS d'abord
    pvgis_result = None
    if site.latitude and site.longitude:
        pvgis_result = _try_pvgis(site.latitude, site.longitude, peak_power_kwc)

    # Production annuelle
    if pvgis_result and pvgis_result.get("annual_kwh"):
        annual_kwh = pvgis_result["annual_kwh"]
        source = "PVGIS (European Commission)"
        monthly = pvgis_result.get("monthly_kwh", [])
    else:
        zone = _get_climate_zone(site)
        hours_eq = {"H1": 1050, "H2": 1150, "H3": 1350}.get(zone, 1150)
        annual_kwh = peak_power_kwc * hours_eq
        source = f"Estimation PROMEOS (zone {zone}, {hours_eq}h eq.)"
        monthly = _estimate_monthly_profile(annual_kwh, zone)

    # Economies estimees (autoconsommation ~70%)
    autoconso_ratio = 0.70
    try:
        from config.tarif_loader import get_prix_reference
        price_kwh = get_prix_reference("elec")
    except Exception:
        price_kwh = 0.068  # fallback prix marche moyen
    savings_eur = annual_kwh * autoconso_ratio * price_kwh

    # CO2 evite
    from config.emission_factors import get_emission_factor
    co2_avoided_kg = annual_kwh * get_emission_factor("ELEC")

    return {
        "site_id": site_id,
        "site_nom": site.nom,
        "surface_type": surface_type,
        "surface_totale_m2": surface_m2,
        "surface_panneaux_m2": round(panel_surface, 0),
        "puissance_crete_kwc": round(peak_power_kwc, 1),
        "production_annuelle_kwh": round(annual_kwh, 0),
        "production_annuelle_mwh": round(annual_kwh / 1000, 1),
        "monthly_kwh": monthly,
        "autoconsommation_pct": autoconso_ratio * 100,
        "economies_annuelles_eur": round(savings_eur, 0),
        "co2_evite_kg": round(co2_avoided_kg, 0),
        "co2_evite_tonnes": round(co2_avoided_kg / 1000, 1),
        "source": source,
        "coverage_ratio": coverage_ratio,
        "methodology": (
            f"Surface panneaux = {surface_m2}m2 x {coverage_ratio:.0%} = {panel_surface:.0f}m2. "
            f"Puissance = {peak_power_kwc:.1f} kWc. "
            f"Autoconsommation estimee {autoconso_ratio:.0%}."
        ),
    }
