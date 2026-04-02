"""
Analyse du facteur de puissance (tan φ / cos φ).

Seuil réglementaire TURPE 7 : tan φ > 0.4 → pénalité énergie réactive.
Pénalité = (Q_kvarh - 0.4 × P_kwh) × tarif_kvarh si positive.
Disponible uniquement sur compteurs > 36 kVA (PRI dans R63).
"""

import math
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from models.power import PowerReading
from services.power.power_profile_service import get_active_contract

TAN_PHI_SEUIL = 0.4  # immuable TURPE 7
TARIF_KVARH_EUR = 0.016

COMPTEURS_REACTIF = {
    "CJE",
    "CJEMdisjoncteur",
    "CJEMcontroleur",
    "CVE",
    "CVEMavecTC",
    "CVEMsansTC",
    "CVEM1",
    "CVEM2",
    "CVEM3",
    "ICE",
    "PME-PMI",
    "SAPHIR",
}


def analyze_power_factor(
    db: Session,
    meter_id: int,
    date_debut: date,
    date_fin: date,
) -> dict:
    """Calcule le tan φ moyen et la pénalité énergie réactive."""
    dt_debut = datetime.combine(date_debut, datetime.min.time())
    dt_fin = datetime.combine(date_fin + timedelta(days=1), datetime.min.time())

    contract = get_active_contract(db, meter_id, date_debut)
    type_compteur = contract.type_compteur if contract else None
    has_reactive = type_compteur in COMPTEURS_REACTIF if type_compteur else False

    readings = (
        db.query(PowerReading)
        .filter(
            PowerReading.meter_id == meter_id,
            PowerReading.ts_debut >= dt_debut,
            PowerReading.ts_debut < dt_fin,
            PowerReading.sens == "CONS",
            PowerReading.P_active_kw.isnot(None),
        )
        .all()
    )

    base = {
        "meter_id": meter_id,
        "period": {"debut": date_debut.isoformat(), "fin": date_fin.isoformat()},
        "type_compteur": type_compteur,
        "source": "power_factor_analyzer",
        "computed_at": datetime.now().isoformat(),
    }

    if not readings:
        return {**base, "data_available": False, "confidence": 0}

    pas_h = readings[0].pas_minutes / 60.0
    E_active = sum(r.P_active_kw for r in readings) * pas_h

    reactive_readings = [r for r in readings if r.P_reactive_ind_kvar is not None]
    if not reactive_readings or not has_reactive:
        return {
            **base,
            "data_available": False,
            "raison": "Compteur sans mesure réactive" if not has_reactive else "Données réactives absentes",
            "E_active_kwh": round(E_active, 1),
            "confidence": 0,
        }

    E_reactive = sum(r.P_reactive_ind_kvar for r in reactive_readings) * pas_h
    tan_phi = E_reactive / E_active if E_active > 0 else 0
    cos_phi = 1 / math.sqrt(1 + tan_phi**2) if tan_phi > 0 else 1.0

    E_seuil = TAN_PHI_SEUIL * E_active
    E_penalisable = max(0, E_reactive - E_seuil)
    penalite = E_penalisable * TARIF_KVARH_EUR

    # Détail par poste
    par_poste: dict[str, dict] = {}
    for r in reactive_readings:
        p = r.periode_tarif or "HPH"
        if p not in par_poste:
            par_poste[p] = {"P": 0, "Q": 0}
        par_poste[p]["P"] += r.P_active_kw * pas_h
        par_poste[p]["Q"] += r.P_reactive_ind_kvar * pas_h

    detail = []
    for poste, v in par_poste.items():
        tp = v["Q"] / v["P"] if v["P"] > 0 else 0
        detail.append(
            {
                "poste": poste,
                "tan_phi": round(tp, 3),
                "cos_phi": round(1 / math.sqrt(1 + tp**2), 3) if tp > 0 else 1.0,
                "au_dessus_seuil": tp > TAN_PHI_SEUIL,
            }
        )

    reco = None
    if tan_phi > TAN_PHI_SEUIL and penalite >= 500:
        reco = {"code": "ACTION_REQUISE", "message": f"tan φ = {tan_phi:.2f} — condensateurs recommandés"}
    elif tan_phi > TAN_PHI_SEUIL:
        reco = {"code": "ATTENTION", "message": f"tan φ = {tan_phi:.2f} > seuil 0.4 — surveiller"}
    else:
        reco = {"code": "OK", "message": "Facteur de puissance conforme (tan φ ≤ 0.4)"}

    return {
        **base,
        "data_available": True,
        "kpis": {
            "tan_phi_moyen": round(tan_phi, 3),
            "cos_phi_moyen": round(cos_phi, 3),
            "seuil_reglementaire": TAN_PHI_SEUIL,
            "au_dessus_seuil": tan_phi > TAN_PHI_SEUIL,
            "E_active_kwh": round(E_active, 1),
            "E_reactive_ind_kvarh": round(E_reactive, 1),
            "E_reactive_penalisable_kvarh": round(E_penalisable, 1),
            "penalite_estimee_eur": round(penalite, 2),
        },
        "detail_par_poste": detail,
        "recommandation": reco,
        "confidence": round(len(reactive_readings) / len(readings), 2),
    }
