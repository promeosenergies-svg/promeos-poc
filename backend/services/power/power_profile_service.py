"""
RÈGLE ABSOLUE : Ce service est le SEUL module qui lit PowerReading.
Tous les autres services power consomment ce module.

Source Enedis :
- CDC en Watts → convertis en kW à l'ingestion (jamais à l'analyse)
- Baseload = percentile(CDC, 5%) — puissance incompressible
- P_max = max(P_active_kw) sur la période
- Facteur de forme = E_totale_kWh / (P_max_kw × T_heures)
"""

import statistics
from datetime import datetime, date, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.power import PowerReading, PowerContract


def get_active_contract(db: Session, meter_id: int, as_of: date) -> PowerContract | None:
    """Récupère le contrat de puissance actif pour un compteur à une date donnée."""
    return (
        db.query(PowerContract)
        .filter(
            PowerContract.meter_id == meter_id,
            PowerContract.date_debut <= as_of,
            (PowerContract.date_fin.is_(None)) | (PowerContract.date_fin >= as_of),
        )
        .order_by(PowerContract.date_debut.desc())
        .first()
    )


# Conversion kVA -> kW, cos phi tertiaire typique (TURPE 7 CRE)
_COS_PHI_TERTIAIRE = 0.8
# Heuristique P_max depuis conso annuelle : taux d'utilisation moyen
_TAUX_UTILISATION_HEURISTIQUE = 0.25


# Cache P_max par meter/jour — evite de relire 365j de CDC a chaque requete.
# Se vide automatiquement quand la date change.
_p_max_cache: dict[tuple[int, date], float] = {}
_p_max_cache_date: date | None = None


def resolve_p_max_kw(db: Session, meter, site=None) -> float:
    """
    Resolution P_max d'un site avec cascade de fallbacks :
    1. PowerProfile CDC reelle (P_max_kw sur 365j)
    2. PowerContract PS par poste (somme kVA x cos phi)
    3. Estimation depuis conso annuelle (conso / 8760h / taux_utilisation)
    4. 0.0 (fail-safe)
    """
    global _p_max_cache, _p_max_cache_date
    today = date.today()

    # Purge cache si jour change
    if _p_max_cache_date != today:
        _p_max_cache = {}
        _p_max_cache_date = today

    # Cache hit
    if meter:
        key = (meter.id, today)
        if key in _p_max_cache:
            return _p_max_cache[key]

    result = _resolve_p_max_kw_uncached(db, meter, site)

    # Ne cacher que les resultats > 0 — un 0.0 peut etre temporaire
    # (donnees importees en cours de journee apres premiere resolution a vide)
    if meter and result > 0:
        _p_max_cache[(meter.id, today)] = result

    return result


def _resolve_p_max_kw_uncached(db: Session, meter, site=None) -> float:
    """Impl sans cache — appele par resolve_p_max_kw."""
    if meter:
        try:
            today = date.today()
            profile = get_power_profile(db, meter.id, today - timedelta(days=365), today)
            p_max = profile.get("kpis", {}).get("P_max_kw", 0.0) or 0.0
            if p_max > 0:
                return float(p_max)
        except Exception:
            pass

        try:
            contract = get_active_contract(db, meter.id, date.today())
            if contract and contract.ps_par_poste_kva:
                total_kva = sum(v for v in contract.ps_par_poste_kva.values() if isinstance(v, (int, float)))
                if total_kva > 0:
                    return round(total_kva * _COS_PHI_TERTIAIRE, 1)
        except Exception:
            pass

    if site:
        conso = getattr(site, "annual_kwh_total", None) or 0
        if conso > 0:
            return round(conso / (8760 * _TAUX_UTILISATION_HEURISTIQUE), 1)

    return 0.0


def get_power_profile(
    db: Session,
    meter_id: int,
    date_debut: date,
    date_fin: date,
    sens: str = "CONS",
) -> dict:
    """KPIs puissance d'un compteur sur une période."""
    dt_debut = datetime.combine(date_debut, datetime.min.time())
    dt_fin = datetime.combine(date_fin + timedelta(days=1), datetime.min.time())

    readings = (
        db.query(PowerReading)
        .filter(
            PowerReading.meter_id == meter_id,
            PowerReading.ts_debut >= dt_debut,
            PowerReading.ts_debut < dt_fin,
            PowerReading.sens == sens,
            PowerReading.P_active_kw.isnot(None),
            PowerReading.indice_vraisemblance == 0,
        )
        .order_by(PowerReading.ts_debut)
        .all()
    )

    base_response = {
        "meter_id": meter_id,
        "period": {"debut": date_debut.isoformat(), "fin": date_fin.isoformat()},
        "source": "power_profile_service",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    if not readings:
        return {**base_response, "data_available": False, "confidence": 0.0}

    values = [r.P_active_kw for r in readings]
    pas_h = readings[0].pas_minutes / 60.0

    P_max = max(values)
    P_mean = statistics.mean(values)
    sorted_vals = sorted(values)
    P_base = sorted_vals[max(0, int(len(sorted_vals) * 0.05))]

    E_totale_kwh = sum(values) * pas_h
    T_heures = len(values) * pas_h
    facteur_forme = E_totale_kwh / (P_max * T_heures) if P_max > 0 else 0

    # Contrat actif
    contract = (
        db.query(PowerContract)
        .filter(
            PowerContract.meter_id == meter_id,
            PowerContract.date_debut <= date_fin,
            (PowerContract.date_fin.is_(None)) | (PowerContract.date_fin >= date_debut),
        )
        .order_by(PowerContract.date_debut.desc())
        .first()
    )

    taux_utilisation = None
    ps_max_kva = None
    if contract and contract.ps_par_poste_kva:
        ps_max_kva = max(contract.ps_par_poste_kva.values())
        taux_utilisation = round(P_max / ps_max_kva * 100, 1) if ps_max_kva > 0 else None

    # Complétude
    total_theorique = int((dt_fin - dt_debut).total_seconds() / (readings[0].pas_minutes * 60))
    completude = round(len(values) / max(total_theorique, 1) * 100, 1)

    # Réactive
    reactive_values = [r.P_reactive_ind_kvar for r in readings if r.P_reactive_ind_kvar]
    tan_phi_mean = None
    if reactive_values and P_mean > 0:
        tan_phi_mean = round(statistics.mean(reactive_values) / P_mean, 3)

    return {
        **base_response,
        "data_available": True,
        "n_points": len(values),
        "pas_minutes": readings[0].pas_minutes,
        "completude_pct": completude,
        "confidence": round(completude / 100, 2),
        "kpis": {
            "P_max_kw": round(P_max, 2),
            "P_mean_kw": round(P_mean, 2),
            "P_base_kw": round(P_base, 2),
            "E_totale_kwh": round(E_totale_kwh, 1),
            "facteur_forme": round(facteur_forme, 3),
            "taux_utilisation_ps_pct": taux_utilisation,
            "ps_max_contractuelle_kva": ps_max_kva,
            "tan_phi_mean": tan_phi_mean,
        },
        "contract": {
            "fta_code": contract.fta_code,
            "domaine_tension": contract.domaine_tension,
            "type_compteur": contract.type_compteur,
            "ps_par_poste_kva": contract.ps_par_poste_kva,
        }
        if contract
        else None,
    }
