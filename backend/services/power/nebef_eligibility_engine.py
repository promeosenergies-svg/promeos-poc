"""
Éligibilité NEBEF (effacement de consommation).
Seuil : P_max ≥ 100 kW. Checklist 9 critères. Revenu central 140 €/kW/an.
"""

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from services.power.power_profile_service import get_power_profile, get_active_contract

SEUIL_NEBEF_KW = 100.0
REVENU_CENTRAL = 140.0
REVENU_MIN = 80.0
REVENU_MAX = 200.0

CVC_PILOTABLE_PCT = {
    "BUREAU_STANDARD": 0.35,
    "HOTEL_HEBERGEMENT": 0.40,
    "ENSEIGNEMENT": 0.30,
    "LOGISTIQUE_SEC": 0.20,
    "DEFAULT": 0.25,
}


def check_nebef_eligibility(
    db: Session,
    meter_id: int,
    site_archetype: str = "DEFAULT",
) -> dict:
    """Évalue l'éligibilité NEBEF et estime le potentiel."""
    date_fin = date.today()
    date_debut = date_fin - timedelta(days=365)

    profile = get_power_profile(db, meter_id, date_debut, date_fin)
    contract = get_active_contract(db, meter_id, date_fin)

    base = {
        "meter_id": meter_id,
        "source": "nebef_eligibility_engine",
        "computed_at": datetime.now().isoformat(),
    }

    if not profile.get("data_available"):
        return {**base, "eligible": False, "raison": "Données insuffisantes", "confidence": 0}

    P_max = profile["kpis"]["P_max_kw"]
    completude = profile["completude_pct"]
    type_compteur = contract.type_compteur if contract else None

    checklist = [
        {"critere": "P_max ≥ 100 kW", "ok": P_max >= SEUIL_NEBEF_KW, "bloquant": True},
        {
            "critere": "Télé-relevé confirmé",
            "ok": type_compteur in {"PME-PMI", "ICE", "SAPHIR", "CVE", "CJE", "Linky"},
            "bloquant": True,
        },
        {"critere": "Historique 12 mois > 50%", "ok": completude >= 50.0, "bloquant": True},
        {"critere": "GTB/EMS commande à distance", "ok": None, "bloquant": True},
        {"critere": "Accord client signé", "ok": None, "bloquant": True},
        {"critere": "Agrégateur agréé RTE", "ok": None, "bloquant": True},
        {"critere": "Disponibilité ≥ 80%", "ok": None, "bloquant": False},
        {"critere": "Pas de contrainte fourniture", "ok": True, "bloquant": False},
        {"critere": "Assurance RC à jour", "ok": None, "bloquant": False},
    ]

    bloquants_ok = all(c["ok"] is not False for c in checklist if c["bloquant"])
    eligible = P_max >= SEUIL_NEBEF_KW and bloquants_ok

    taux_cvc = CVC_PILOTABLE_PCT.get(site_archetype, CVC_PILOTABLE_PCT["DEFAULT"])
    P_eff_cvc = round(P_max * taux_cvc, 1)
    P_eff_ecl = round(P_max * 0.12, 1)
    P_eff_total = round(P_eff_cvc + P_eff_ecl, 1)

    potentiel = (
        {
            "P_effacable_total_kw": P_eff_total,
            "revenu_min_eur_an": round(P_eff_total * REVENU_MIN),
            "revenu_central_eur_an": round(P_eff_total * REVENU_CENTRAL),
            "revenu_max_eur_an": round(P_eff_total * REVENU_MAX),
        }
        if P_max >= SEUIL_NEBEF_KW
        else None
    )

    return {
        **base,
        "eligible": eligible,
        "P_max_kw": round(P_max, 1),
        "seuil_nebef_kw": SEUIL_NEBEF_KW,
        "type_compteur": type_compteur,
        "checklist": checklist,
        "potentiel": potentiel,
        "confidence": round(completude / 100, 2),
    }
