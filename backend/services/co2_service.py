"""
PROMEOS V110 — Service calcul CO₂.

Facteurs d'émission officiels ADEME Base Carbone (2024) :
- Électricité réseau France : 52 gCO₂eq/kWh (mix moyen annuel)
- Gaz naturel : 227 gCO₂eq/kWh (PCI, combustion + amont)

Source : https://base-empreinte.ademe.fr
Note : le facteur élec varie selon la méthode (moyenné annuel vs marginal).
On utilise le facteur moyen annuel, cohérent avec le Décret Tertiaire.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from typing import Optional, List

from sqlalchemy.orm import Session

logger = logging.getLogger("promeos.co2")

# ── Facteurs d'émission — source unique : config/emission_factors.py ──────
# ADEME Base Empreinte V23.6 (juillet 2025)
from config.emission_factors import EMISSION_FACTORS as _CANONICAL_FACTORS

# Mapping lowercase pour backward-compat avec le reste de co2_service
EMISSION_FACTORS = {
    "elec": {
        "factor_kg_per_kwh": _CANONICAL_FACTORS["ELEC"]["kgco2e_per_kwh"],
        "source": _CANONICAL_FACTORS["ELEC"]["source"],
        "method": "ACV (analyse cycle de vie)",
        "year": _CANONICAL_FACTORS["ELEC"]["year"],
    },
    "gaz": {
        "factor_kg_per_kwh": _CANONICAL_FACTORS["GAZ"]["kgco2e_per_kwh"],
        "source": _CANONICAL_FACTORS["GAZ"]["source"],
        "method": "ACV (analyse cycle de vie)",
        "year": _CANONICAL_FACTORS["GAZ"]["year"],
    },
    "reseau_chaleur": {
        "factor_kg_per_kwh": 0.110,
        "source": "ADEME Base Empreinte V23.6 — reseau de chaleur moyen France",
        "method": "ACV",
        "year": 2024,
    },
    "fioul": {
        "factor_kg_per_kwh": 0.324,
        "source": "ADEME Base Empreinte V23.6 — fioul domestique PCI",
        "method": "ACV",
        "year": 2024,
    },
}


@dataclass
class Co2Result:
    """Résultat calcul CO₂ pour un site."""

    site_id: int
    total_kg_co2: float
    total_t_co2: float
    breakdown: list  # [{energy_type, kwh, factor, kg_co2, source}]
    confidence: str  # "high" si mesuré, "medium" si estimé

    def to_dict(self) -> dict:
        return asdict(self)


def compute_site_co2(db: Session, site_id: int) -> Co2Result:
    """
    Calcule l'empreinte CO₂ annuelle d'un site.

    Utilise le modele Meter (source de verite) pour decouvrir les vecteurs
    energetiques et lire les MeterReading. Fallback Site.annual_kwh_total.
    """
    from models import Site
    from models.energy_models import Meter, MeterReading
    from models.enums import EnergyVector

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return Co2Result(site_id=site_id, total_kg_co2=0, total_t_co2=0, breakdown=[], confidence="low")

    # Source de verite : modele Meter (Yannick) — exclut sous-compteurs
    meters = (
        db.query(Meter)
        .filter(Meter.site_id == site_id, Meter.is_active.is_(True), Meter.parent_meter_id.is_(None))
        .all()
    )

    # Grouper par vecteur energetique
    vectors: dict[str, list[int]] = {}
    for m in meters:
        ev = m.energy_vector.value.lower() if m.energy_vector else "elec"
        if ev in ("electricity", "elec"):
            ev = "elec"
        elif ev in ("gas", "gaz"):
            ev = "gaz"
        vectors.setdefault(ev, []).append(m.id)

    # Si pas de Meter, utiliser le site.annual_kwh_total comme elec
    if not vectors:
        annual = getattr(site, "annual_kwh_total", None) or 0
        if annual > 0:
            vectors = {"elec": []}

    # Calculer par vecteur
    breakdown = []
    total_kg = 0

    for energy_type, meter_ids in vectors.items():
        factor_info = EMISSION_FACTORS.get(energy_type, EMISSION_FACTORS.get("elec"))
        factor = factor_info["factor_kg_per_kwh"]

        # Conso du vecteur via MeterReading (modele Yannick)
        kwh = 0
        if meter_ids:
            try:
                from sqlalchemy import func
                from datetime import date, timedelta

                today = date.today()
                y_ago = today - timedelta(days=365)

                from models.enums import FrequencyType

                result = (
                    db.query(func.sum(MeterReading.value_kwh))
                    .filter(
                        MeterReading.meter_id.in_(meter_ids),
                        MeterReading.frequency == FrequencyType.MONTHLY,
                        MeterReading.timestamp >= y_ago,
                    )
                    .scalar()
                )
                kwh = float(result or 0)
            except Exception as e:
                logger.warning("MeterReading query failed for site %d: %s", site_id, e)

        # Fallback si pas de meter readings
        if kwh <= 0 and energy_type == "elec":
            kwh = float(getattr(site, "annual_kwh_total", 0) or 0)

        if kwh > 0:
            kg_co2 = round(kwh * factor, 1)
            total_kg += kg_co2
            breakdown.append(
                {
                    "energy_type": energy_type,
                    "kwh": round(kwh, 0),
                    "factor_kg_per_kwh": factor,
                    "kg_co2": kg_co2,
                    "t_co2": round(kg_co2 / 1000, 1),
                    "source": factor_info["source"],
                }
            )

    confidence = "high" if all(b.get("kwh", 0) > 0 for b in breakdown) else "medium"

    return Co2Result(
        site_id=site_id,
        total_kg_co2=round(total_kg, 1),
        total_t_co2=round(total_kg / 1000, 1),
        breakdown=breakdown,
        confidence=confidence,
    )


def compute_portfolio_co2(db: Session, org_id: int) -> dict:
    """Calcule l'empreinte CO₂ portfolio (tous sites actifs)."""
    from models import Site, not_deleted

    sites = not_deleted(db.query(Site), Site).filter(Site.actif == True).all()
    if org_id:
        # Filter by org via portefeuille chain
        site_ids_in_org = _get_org_site_ids(db, org_id)
        sites = [s for s in sites if s.id in site_ids_in_org]

    results = []
    total_kg = 0
    for site in sites:
        r = compute_site_co2(db, site.id)
        total_kg += r.total_kg_co2
        results.append(
            {
                "site_id": site.id,
                "site_nom": site.nom,
                "t_co2": r.total_t_co2,
                "breakdown": r.breakdown,
                "confidence": r.confidence,
            }
        )

    # Agrégats par vecteur — calculés backend (le front ne doit PAS agréger)
    vectors_agg: dict[str, dict] = {}
    scope1_kg = 0.0
    scope2_kg = 0.0
    total_kwh_all = 0.0
    for r in results:
        for bd in r.get("breakdown", []):
            key = bd.get("energy_type", "autres")
            if key not in vectors_agg:
                vectors_agg[key] = {"kwh": 0.0, "kg_co2": 0.0}
            vectors_agg[key]["kwh"] += bd.get("kwh", 0)
            vectors_agg[key]["kg_co2"] += bd.get("kg_co2", 0)
            total_kwh_all += bd.get("kwh", 0)
            # Scope 1 = gaz, fioul ; Scope 2 = elec, réseau chaleur
            if key in ("gaz", "fioul"):
                scope1_kg += bd.get("kg_co2", 0)
            else:
                scope2_kg += bd.get("kg_co2", 0)

    vectors_display = []
    for key, val in sorted(vectors_agg.items(), key=lambda x: -x[1]["kwh"]):
        mwh = round(val["kwh"] / 1000, 1) if val["kwh"] else 0
        pct = round((val["kwh"] / total_kwh_all) * 100) if total_kwh_all > 0 else 0
        vectors_display.append(
            {
                "key": key,
                "mwh": mwh,
                "pct": pct,
                "t_co2": round(val["kg_co2"] / 1000, 1),
            }
        )

    return {
        "org_id": org_id,
        "total_t_co2": round(total_kg / 1000, 1),
        "total_kg_co2": round(total_kg, 1),
        "scope1_t_co2": round(scope1_kg / 1000, 1),
        "scope2_t_co2": round(scope2_kg / 1000, 1),
        "vectors": vectors_display,
        "total_kwh": round(total_kwh_all, 0),
        "sites": results,
        "emission_factors": {k: v["factor_kg_per_kwh"] for k, v in EMISSION_FACTORS.items()},
        "source": "ADEME Base Carbone 2024",
    }


def _get_org_site_ids(db: Session, org_id: int) -> set:
    """Resolve org → site IDs via portefeuille chain."""
    from models import Site, Portefeuille, EntiteJuridique

    ejs = db.query(EntiteJuridique).filter(EntiteJuridique.organisation_id == org_id).all()
    ej_ids = [e.id for e in ejs]
    pfs = db.query(Portefeuille).filter(Portefeuille.entite_juridique_id.in_(ej_ids)).all()
    pf_ids = [p.id for p in pfs]
    sites = db.query(Site).filter(Site.portefeuille_id.in_(pf_ids)).all()
    return {s.id for s in sites}
