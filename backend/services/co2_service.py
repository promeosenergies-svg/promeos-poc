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
from datetime import date
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


def compute_site_co2(db: Session, site_id: int, start: date = None, end: date = None) -> Co2Result:
    """
    Calcule l'empreinte CO₂ d'un site sur une période.

    Utilise le modele Meter (source de verite) pour decouvrir les vecteurs
    energetiques et lire les MeterReading. Fallback Site.annual_kwh_total.

    Args:
        start/end: période de calcul. Si None → 365 derniers jours.
    """
    from models import Site
    from models.energy_models import Meter, MeterReading
    from models.enums import EnergyVector  # noqa: F811

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return Co2Result(site_id=site_id, total_kg_co2=0, total_t_co2=0, breakdown=[], confidence="low")

    # Consommation par vecteur via unified service (single source of truth)
    from datetime import timedelta
    from services.consumption_unified_service import get_consumption_summary

    if end is None:
        end = date.today()
    if start is None:
        start = end - timedelta(days=365)

    # Alias pour le reste du code (y_ago/today → start/end)
    y_ago = start
    today = end

    # Vecteurs a calculer : elec toujours, gaz si compteur present
    vector_map = {"elec": EnergyVector.ELECTRICITY, "gaz": EnergyVector.GAS}

    # Detecter les vecteurs presents via Meter
    meters = (
        db.query(Meter)
        .filter(Meter.site_id == site_id, Meter.is_active.is_(True), Meter.parent_meter_id.is_(None))
        .all()
    )
    present_vectors = set()
    for m in meters:
        ev = m.energy_vector.value.lower() if m.energy_vector else "electricity"
        if ev in ("electricity", "elec"):
            present_vectors.add("elec")
        elif ev in ("gas", "gaz"):
            present_vectors.add("gaz")

    # Toujours inclure elec (fallback via annual_kwh_total)
    if not present_vectors:
        present_vectors.add("elec")

    breakdown = []
    total_kg = 0

    for energy_type in present_vectors:
        factor_info = EMISSION_FACTORS.get(energy_type, EMISSION_FACTORS.get("elec"))
        factor = factor_info["factor_kg_per_kwh"]

        try:
            ev_enum = vector_map.get(energy_type, EnergyVector.ELECTRICITY)
            summary = get_consumption_summary(db, site_id, y_ago, today, energy_vector=ev_enum)
            kwh = float(summary.get("value_kwh", 0) or 0)
        except Exception as e:
            logger.warning("Unified consumption query failed for site %d: %s", site_id, e)
            kwh = 0

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


def _aggregate_co2_results(results: list) -> dict:
    """Agrège les résultats CO₂ par vecteur et scope. Retourne les totaux."""
    vectors_agg: dict[str, dict] = {}
    scope1_kg = 0.0
    scope2_kg = 0.0
    total_kg = 0.0
    total_kwh_all = 0.0

    for r in results:
        total_kg += r.get("total_kg_co2", 0) if isinstance(r, dict) else r.total_kg_co2
        breakdowns = r.get("breakdown", []) if isinstance(r, dict) else r.breakdown
        for bd in breakdowns:
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

    return {
        "total_kg": total_kg,
        "scope1_kg": scope1_kg,
        "scope2_kg": scope2_kg,
        "total_kwh": total_kwh_all,
        "vectors_agg": vectors_agg,
    }


def _delta_pct(current: float, previous: float) -> float | None:
    """Écart en %. Négatif = amélioration (baisse). None si données manquantes."""
    if previous is None or previous == 0 or current is None:
        return None
    return round((current - previous) / previous * 100, 1)


def _safe_prev_date(year: int, month: int, day: int) -> date:
    """Construit une date en gérant le 29 février (fallback au 28)."""
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, month, 28)


MONTH_NAMES_FR = {
    1: "Janv",
    2: "Fév",
    3: "Mars",
    4: "Avr",
    5: "Mai",
    6: "Juin",
    7: "Juil",
    8: "Août",
    9: "Sept",
    10: "Oct",
    11: "Nov",
    12: "Déc",
}


def compute_portfolio_co2(db: Session, org_id: int) -> dict:
    """
    Calcule l'empreinte CO₂ portfolio (tous sites actifs) + comparaison N-1.

    Comparaison sur même période calendaire : janv→aujourd'hui N vs janv→même jour N-1.
    Facteurs ADEME centralisés — zéro calcul côté frontend.
    """
    from models import Site, not_deleted

    sites = not_deleted(db.query(Site), Site).filter(Site.actif == True).all()
    if org_id:
        site_ids_in_org = _get_org_site_ids(db, org_id)
        sites = [s for s in sites if s.id in site_ids_in_org]

    # ── Périodes N et N-1 (même plage calendaire) ──
    today = date.today()
    year_n = today.year
    start_n = date(year_n, 1, 1)
    end_n = today

    start_n1 = date(year_n - 1, 1, 1)
    end_n1 = _safe_prev_date(year_n - 1, today.month, today.day)

    # ── Calcul CO₂ par site pour N et N-1 ──
    results_n = []
    results_n1 = []
    for site in sites:
        r_n = compute_site_co2(db, site.id, start=start_n, end=end_n)
        results_n.append(
            {
                "site_id": site.id,
                "site_nom": site.nom,
                "t_co2": r_n.total_t_co2,
                "total_kg_co2": r_n.total_kg_co2,
                "breakdown": r_n.breakdown,
                "confidence": r_n.confidence,
            }
        )

        r_n1 = compute_site_co2(db, site.id, start=start_n1, end=end_n1)
        results_n1.append(r_n1)

    # ── Agrégation N ──
    agg_n = _aggregate_co2_results(results_n)

    # Vecteurs display (pour les barres du frontend)
    vectors_display = []
    for key, val in sorted(agg_n["vectors_agg"].items(), key=lambda x: -x[1]["kwh"]):
        mwh = round(val["kwh"] / 1000, 1) if val["kwh"] else 0
        pct = round((val["kwh"] / agg_n["total_kwh"]) * 100) if agg_n["total_kwh"] > 0 else 0
        vectors_display.append(
            {
                "key": key,
                "mwh": mwh,
                "pct": pct,
                "t_co2": round(val["kg_co2"] / 1000, 1),
            }
        )

    # ── Agrégation N-1 ──
    agg_n1 = _aggregate_co2_results(results_n1)
    has_n1 = agg_n1["total_kg"] > 0

    # ── Deltas (négatif = amélioration = baisse des émissions) ──
    total_t_n = round(agg_n["total_kg"] / 1000, 1)
    scope1_t_n = round(agg_n["scope1_kg"] / 1000, 1)
    scope2_t_n = round(agg_n["scope2_kg"] / 1000, 1)

    total_t_n1 = round(agg_n1["total_kg"] / 1000, 1) if has_n1 else None
    scope1_t_n1 = round(agg_n1["scope1_kg"] / 1000, 1) if has_n1 else None
    scope2_t_n1 = round(agg_n1["scope2_kg"] / 1000, 1) if has_n1 else None

    # ── Labels de période ──
    month_end = MONTH_NAMES_FR.get(today.month, str(today.month))
    period_label_n = f"Janv – {month_end} {year_n}"
    period_label_n1 = f"Janv – {month_end} {year_n - 1}"

    return {
        "org_id": org_id,
        # Champs existants (rétro-compatibilité)
        "total_t_co2": total_t_n,
        "total_kg_co2": round(agg_n["total_kg"], 1),
        "scope1_t_co2": scope1_t_n,
        "scope2_t_co2": scope2_t_n,
        "vectors": vectors_display,
        "total_kwh": round(agg_n["total_kwh"], 0),
        "sites": results_n,
        "emission_factors": {k: v["factor_kg_per_kwh"] for k, v in EMISSION_FACTORS.items()},
        "source": "ADEME Base Carbone 2024",
        # Nouveaux champs N-1
        "year": year_n,
        "period_label": period_label_n,
        "prev_year": year_n - 1,
        "prev_period_label": period_label_n1,
        "prev_total_tco2": total_t_n1,
        "prev_scope1_tco2": scope1_t_n1,
        "prev_scope2_tco2": scope2_t_n1,
        # Deltas (négatif = amélioration)
        "delta_total_pct": _delta_pct(total_t_n, total_t_n1),
        "delta_scope1_pct": _delta_pct(scope1_t_n, scope1_t_n1),
        "delta_scope2_pct": _delta_pct(scope2_t_n, scope2_t_n1),
        # Traçabilité facteurs
        "co2_factors": {
            "elec_kgco2_per_kwh": EMISSION_FACTORS["elec"]["factor_kg_per_kwh"],
            "gaz_kgco2_per_kwh": EMISSION_FACTORS["gaz"]["factor_kg_per_kwh"],
            "source": "ADEME Base Empreinte V23.6",
        },
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
