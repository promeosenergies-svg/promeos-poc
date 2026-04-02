"""
Optimisation de la puissance souscrite par analyse de la courbe de charge.

1. Identifier la pointe réelle (kW max) et son timestamp
2. Décomposer la pointe par usage (sous-compteur)
3. Identifier les usages décalables (via FLEX_BY_USAGE)
4. Simuler la nouvelle pointe après décalage
5. Calculer l'économie TURPE (réduction PS) et le coût CMDPS résiduel

Tarifs TURPE 7 composante soutirage (part fixe) :
  Coût_fixe = PS_kVA × prix_kVA_an (fonction du segment tarifaire)
"""

import logging
from datetime import timedelta

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from models.site import Site
from models.billing_models import EnergyContract
from models.energy_models import Meter, MeterReading, FrequencyType
from models.usage import Usage
from services.flex_nebco_service import FLEX_BY_USAGE

logger = logging.getLogger(__name__)

# Prix TURPE composante soutirage part fixe par segment (€/kVA/an)
# Sources : CRE TURPE 6 grille 2021 extrapolée TURPE 7 (+5%)
TURPE_POWER_PRICE = {
    "BASE": 10.5,  # C5 BT base
    "HP_HC": 10.5,  # C5 BT HP/HC
    "CU4": 12.0,  # C5 BT 4 périodes
    "MU4": 10.5,  # C5 BT MU4
    "CU": 28.0,  # C4 BT courte utilisation
    "MU": 20.0,  # C4 BT moyenne utilisation
    "LU": 15.0,  # C4 BT longue utilisation
}
DEFAULT_TURPE_POWER_PRICE = 20.0  # €/kVA/an


def optimize_subscribed_power(db: Session, site_id: int) -> dict | None:
    """Analyse la PS et recommande une optimisation."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return None

    # PS actuelle depuis le contrat
    contract = (
        db.query(EnergyContract)
        .filter(EnergyContract.site_id == site_id, EnergyContract.subscribed_power_kva.isnot(None))
        .first()
    )
    current_ps = contract.subscribed_power_kva if contract else None
    tariff_option = contract.tariff_option.name if contract and contract.tariff_option else None
    price_kva = TURPE_POWER_PRICE.get(tariff_option, DEFAULT_TURPE_POWER_PRICE)

    # Compteur principal
    principal = db.query(Meter).filter(Meter.site_id == site_id, Meter.parent_meter_id.is_(None)).first()
    if not principal:
        return {"error": "Aucun compteur principal", "site_id": site_id}

    # Top 10 pointes (15min)
    top_peaks = (
        db.query(MeterReading)
        .filter(
            MeterReading.meter_id == principal.id,
            MeterReading.frequency == FrequencyType.MIN_15,
        )
        .order_by(MeterReading.value_kwh.desc())
        .limit(10)
        .all()
    )

    if not top_peaks:
        return {"error": "Pas de données 15min", "site_id": site_id}

    peak = top_peaks[0]
    peak_kw = round(peak.value_kwh * 4, 1)  # kWh 15min → kW
    peak_ts = peak.timestamp

    # Profil mensuel des pointes
    monthly_peaks = _monthly_peak_profile(db, principal.id)

    # Décomposition de la pointe par usage
    decomposition = _decompose_peak(db, site_id, peak_ts, principal.id, peak_kw)

    # Simulation de décalage
    shiftable_kw = sum(d["kw"] * d["shiftable_pct"] / 100 for d in decomposition if d["shiftable"])
    new_peak_kw = round(max(peak_kw - shiftable_kw, peak_kw * 0.5), 0)  # plancher 50%

    # PS recommandée (marge 5% au-dessus de la nouvelle pointe)
    recommended_ps = round(new_peak_kw * 1.05 / 10) * 10  # arrondi à la dizaine

    if current_ps:
        # Garantir que la reco ne dépasse pas l'actuelle
        recommended_ps = min(recommended_ps, current_ps)
        savings_turpe = round((current_ps - recommended_ps) * price_kva)
        annual_cost = round(current_ps * price_kva)
        utilization = round(peak_kw / current_ps * 100, 1) if current_ps > 0 else 0
        margin_kw = round(current_ps - peak_kw, 1)

        # CMDPS estimé — comparer kW des pointes avec PS convertie en kW (cos φ ≈ 0.93)
        recommended_ps_kw = recommended_ps * 0.93
        n_days_above = sum(1 for p in monthly_peaks if p["peak_kw"] > recommended_ps_kw)
        cmdps = round(n_days_above * 2 * price_kva * 0.5) if n_days_above > 0 else 0
        net_savings = max(0, savings_turpe - cmdps)
    else:
        # Pas de PS connue — estimation
        current_ps = round(peak_kw * 1.15 / 10) * 10
        savings_turpe = round((current_ps - recommended_ps) * price_kva)
        annual_cost = round(current_ps * price_kva)
        utilization = round(peak_kw / current_ps * 100, 1)
        margin_kw = round(current_ps - peak_kw, 1)
        n_days_above = 0
        cmdps = 0
        net_savings = savings_turpe

    # Stratégie textuelle
    top_shiftable = [d for d in decomposition if d["shiftable"]]
    if top_shiftable:
        main_usage = top_shiftable[0]["usage"]
        strategy = f"Pré-conditionnement {main_usage.lower()}, décalage pic de 30 min via GTB"
    else:
        strategy = "Optimisation limitée — pas d'usage pilotable identifié"

    top_peaks_formatted = [
        {
            "timestamp": p.timestamp.isoformat() if p.timestamp else None,
            "kw": round(p.value_kwh * 4, 1),
            "hour": p.timestamp.hour if p.timestamp else None,
        }
        for p in top_peaks[:5]
    ]

    return {
        "site_id": site_id,
        "site_name": site.nom,
        "current_situation": {
            "subscribed_power_kva": current_ps,
            "actual_peak_kw": peak_kw,
            "peak_timestamp": peak_ts.isoformat() if peak_ts else None,
            "peak_hour": peak_ts.hour if peak_ts else None,
            "peak_weekday": _weekday_fr(peak_ts) if peak_ts else None,
            "utilization_pct": utilization,
            "margin_kw": margin_kw,
            "annual_cost_turpe_fixe_eur": annual_cost,
            "tariff_option": tariff_option,
            "price_kva_an": price_kva,
        },
        "peak_decomposition": decomposition,
        "optimization": {
            "strategy": strategy,
            "new_peak_kw": new_peak_kw,
            "recommended_ps_kva": recommended_ps,
            "savings_turpe_fixe_eur": savings_turpe,
            "cmdps_estimated_eur": cmdps,
            "net_savings_eur": net_savings,
            "investment_required": "Programmation GTB (inclus si BACS conforme)" if top_shiftable else "N/A",
            "roi": "Immédiat" if top_shiftable and net_savings > 0 else "N/A",
        },
        "monthly_peak_profile": monthly_peaks,
        "n_days_above_recommended_ps": n_days_above,
        "top_peaks": top_peaks_formatted,
    }


def _decompose_peak(
    db: Session,
    site_id: int,
    peak_ts,
    principal_meter_id: int,
    peak_kw: float,
) -> list[dict]:
    """Au timestamp de la pointe, lire chaque sous-compteur pour décomposer la puissance."""
    subs = db.query(Meter).filter(Meter.site_id == site_id, Meter.parent_meter_id.isnot(None)).all()

    decomposition = []
    total_sub_kw = 0

    # Convertir peak_ts en string ISO pour comparaison SQLite fiable
    peak_ts_str = peak_ts.strftime("%Y-%m-%dT%H:%M:%S") if peak_ts else ""
    peak_ts_minus = (peak_ts - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S") if peak_ts else ""
    peak_ts_plus = (peak_ts + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S") if peak_ts else ""

    for sub in subs:
        # Lecture au timestamp de pointe (comparaison string pour SQLite)
        reading = (
            db.query(MeterReading)
            .filter(
                MeterReading.meter_id == sub.id,
                MeterReading.frequency == FrequencyType.MIN_15,
                func.strftime("%Y-%m-%dT%H:%M:%S", MeterReading.timestamp) == peak_ts_str,
            )
            .first()
        )

        if not reading:
            # Fallback : ±15 min
            reading = (
                db.query(MeterReading)
                .filter(
                    MeterReading.meter_id == sub.id,
                    MeterReading.frequency == FrequencyType.MIN_15,
                    func.strftime("%Y-%m-%dT%H:%M:%S", MeterReading.timestamp).between(
                        peak_ts_minus,
                        peak_ts_plus,
                    ),
                )
                .order_by(func.abs(func.julianday(MeterReading.timestamp) - func.julianday(peak_ts_str)))
                .first()
            )

        kw = round(reading.value_kwh * 4, 1) if reading else 0

        # Label usage
        usage = db.query(Usage).filter(Usage.id == sub.usage_id).first() if sub.usage_id else None
        label = usage.label if usage else "Inconnu"

        # Cross-ref pilotabilité
        profile = FLEX_BY_USAGE.get(label, {"shiftable_pct": 0.05, "pilotability": "faible", "inertia_min": 0})
        shiftable = profile["pilotability"] in ("haute", "moyenne")

        pct = round(kw / peak_kw * 100) if peak_kw > 0 else 0
        decomposition.append(
            {
                "usage": label,
                "kw": kw,
                "pct": pct,
                "shiftable": shiftable,
                "shiftable_pct": round(profile["shiftable_pct"] * 100),
                "pilotability": profile["pilotability"],
                "inertia_min": profile.get("inertia_min", 0),
            }
        )
        total_sub_kw += kw

    # Résiduel
    residual = round(peak_kw - total_sub_kw, 1)
    if residual > 0:
        decomposition.append(
            {
                "usage": "Autres (non sous-comptés)",
                "kw": residual,
                "pct": round(residual / peak_kw * 100) if peak_kw > 0 else 0,
                "shiftable": False,
                "shiftable_pct": 0,
                "pilotability": "inconnue",
                "inertia_min": 0,
            }
        )

    decomposition.sort(key=lambda d: d["kw"], reverse=True)
    return decomposition


def _monthly_peak_profile(db: Session, meter_id: int) -> list[dict]:
    """Pointe kW max par mois."""
    MONTH_NAMES = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun", "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]
    rows = (
        db.query(
            extract("month", MeterReading.timestamp).label("mo"),
            func.max(MeterReading.value_kwh).label("max_kwh"),
        )
        .filter(
            MeterReading.meter_id == meter_id,
            MeterReading.frequency == FrequencyType.MIN_15,
        )
        .group_by(extract("month", MeterReading.timestamp))
        .all()
    )

    by_month = {int(r.mo): round(float(r.max_kwh) * 4, 1) for r in rows}
    return [{"month": MONTH_NAMES[i], "peak_kw": by_month.get(i + 1, 0)} for i in range(12)]


_JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def _weekday_fr(ts) -> str:
    return _JOURS_FR[ts.weekday()] if ts else ""
