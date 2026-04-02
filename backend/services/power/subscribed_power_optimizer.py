"""
Optimiseur de puissance souscrite par poste.

Règles Enedis : EIR BT si |ΔPS| ≥ 36 kVA, EIR HTA si augmentation ≥ 100 kW.
PS recommandée = ceil(P_max_réel × 1.15), integer kVA (XSD C12).
"""

import math
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.power import PowerReading
from services.power.power_profile_service import get_active_contract

TARIF_ABONNEMENT_KVA_AN = {
    "Pointe": 280,
    "HPH": 250,
    "HCH": 120,
    "HPE": 140,
    "HCE": 80,
    "Base": 180,
    "HP": 200,
    "HC": 100,
    "PM": 220,
}
DEFAULT_TARIF_KVA_AN = 180
MARGE_SECURITE_PCT = 15.0
SEUIL_EIR_BT_KVA = 36
SEUIL_EIR_HTA_KW = 100


def optimize_subscribed_power(
    db: Session,
    meter_id: int,
    date_debut: date,
    date_fin: date,
) -> dict:
    """Analyse PS actuelle vs puissance réelle, recommande par poste."""
    dt_debut = datetime.combine(date_debut, datetime.min.time())
    dt_fin = datetime.combine(date_fin + timedelta(days=1), datetime.min.time())

    contract = get_active_contract(db, meter_id, date_debut)
    base = {
        "meter_id": meter_id,
        "period": {"debut": date_debut.isoformat(), "fin": date_fin.isoformat()},
        "source": "subscribed_power_optimizer",
        "computed_at": datetime.now().isoformat(),
    }

    if not contract or not contract.ps_par_poste_kva:
        return {**base, "data_available": False, "raison": "Contrat introuvable", "confidence": 0}

    ps_par_poste = contract.ps_par_poste_kva
    is_hta = (contract.domaine_tension or "").startswith("HTA")

    # Max réel par poste
    max_par_poste = {}
    for poste in ps_par_poste:
        result = (
            db.query(func.max(PowerReading.P_active_kw))
            .filter(
                PowerReading.meter_id == meter_id,
                PowerReading.ts_debut >= dt_debut,
                PowerReading.ts_debut < dt_fin,
                PowerReading.sens == "CONS",
                PowerReading.periode_tarif == poste,
                PowerReading.P_active_kw.isnot(None),
            )
            .scalar()
        )
        max_par_poste[poste] = round(result or 0, 2)

    recos = []
    eco_totale = 0.0
    eir_global = False

    for poste, ps_kva in ps_par_poste.items():
        p_max = max_par_poste.get(poste, 0)
        ps_reco = max(1, math.ceil(p_max * (1 + MARGE_SECURITE_PCT / 100)))
        delta = ps_kva - ps_reco
        taux = round(p_max / ps_kva * 100, 1) if ps_kva > 0 else 0

        eir = False
        if is_hta and abs(delta) >= SEUIL_EIR_HTA_KW:
            eir = True
        elif not is_hta and abs(delta) >= SEUIL_EIR_BT_KVA:
            eir = True
        eir_global = eir_global or eir

        tarif = TARIF_ABONNEMENT_KVA_AN.get(poste, DEFAULT_TARIF_KVA_AN)
        eco = max(0, delta * tarif)
        eco_totale += eco

        action = "OPTIMAL"
        if delta > 30 and taux < 40:
            action = "REDUIRE_URGENT"
        elif delta > 0 and taux < 60:
            action = "REDUIRE"
        elif taux > 90:
            action = "RISQUE_DEPASSEMENT"

        recos.append(
            {
                "poste": poste,
                "ps_actuelle_kva": ps_kva,
                "p_max_reel_kw": p_max,
                "ps_recommandee_kva": ps_reco,
                "delta_kva": round(delta),
                "taux_utilisation_pct": taux,
                "economie_annuelle_eur": round(eco),
                "eir_requis": eir,
                "action": action,
            }
        )

    return {
        **base,
        "data_available": True,
        "domaine_tension": contract.domaine_tension,
        "fta_code": contract.fta_code,
        "eir_requis_global": eir_global,
        "economie_totale_annuelle_eur": round(eco_totale),
        "recommandations_par_poste": recos,
        "confidence": 0.9,
    }
