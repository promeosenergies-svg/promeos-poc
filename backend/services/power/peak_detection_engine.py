"""
Détection des pics de puissance et calcul CMDPS par poste.

Règles : dépassement = par poste horaire (HPH/HCH/HPE/HCE/Pointe séparément).
Coût CMDPS BT >36 kVA = dépassement_kw × 12,41 €/h × pas_h (HT, TURPE 7).
CMDPS = dépassement quadratique par poste (source Enedis F12 v1.14.2 §7.6.7).

Source CMDPS : CRE délibération 2025-78 (brochure tarifaire TURPE 7 HTA-BT p.15),
applicable depuis le 1er août 2025 pour 4 ans (Z = IPC + X (−0,35%) + k (±3%)).
Constante centralisée dans `services/billing_engine/catalog.py::TURPE_CMDPS_C4`.

Audit Phase 0-bis Bill Intelligence (2026-05-24) — divergence corrigée P1 :
ancienne valeur 12,65 non sourcée (probable confusion TURPE 6 avant 01/08/2025)
remplacée par 12,41 doctriné CRE 2025-78. Cf. audit_brique_bill_intelligence
_deep_readonly_2026_05_23.md §14.2.
"""

import math
from datetime import date, datetime

from sqlalchemy.orm import Session

from models.power import PowerContract, PowerReading
from services.billing_engine.catalog import TURPE7_RATES
from services.power.power_profile_service import get_active_contract
from utils.datetime_utils import to_exclusive_next_day_dt, to_start_of_day_dt

# CMDPS BT >36 kVA (segment C4) — source de vérité unique : catalog.py
# Le catalog cite explicitement la brochure CRE 2025-78 p.15 = 12,41 €·h HT.
TARIF_DEPASSEMENT_EUR_KW = TURPE7_RATES["TURPE_CMDPS_C4"]["rate"]


def detect_peaks(
    db: Session,
    meter_id: int,
    date_debut: date,
    date_fin: date,
    seuil_pct: float = 85.0,
) -> dict:
    """Détecte les pics >= seuil_pct% de la PS par poste et calcule la CMDPS."""
    # Phase L16.3 — helpers centralisés utils/datetime_utils.py (anti-drift L13.4)
    dt_debut = to_start_of_day_dt(date_debut)
    dt_fin = to_exclusive_next_day_dt(date_fin)

    readings = (
        db.query(PowerReading)
        .filter(
            PowerReading.meter_id == meter_id,
            PowerReading.ts_debut >= dt_debut,
            PowerReading.ts_debut < dt_fin,
            PowerReading.sens == "CONS",
            PowerReading.P_active_kw.isnot(None),
        )
        .order_by(PowerReading.ts_debut)
        .all()
    )

    contract = get_active_contract(db, meter_id, date_debut)
    ps_par_poste = contract.ps_par_poste_kva if contract else {}

    base = {
        "meter_id": meter_id,
        "period": {"debut": date_debut.isoformat(), "fin": date_fin.isoformat()},
        "source": "peak_detection_engine",
        "computed_at": datetime.now().isoformat(),
    }

    if not readings or not ps_par_poste:
        return {
            **base,
            "n_pics": 0,
            "peaks": [],
            "cout_total_estime_eur": 0,
            "cmdps_par_poste": [],
            "ps_par_poste_kva": ps_par_poste,
            "confidence": 0,
        }

    ps_max_global = max(ps_par_poste.values())
    peaks = []
    depassements_par_poste: dict[str, list[tuple[float, float]]] = {}

    for r in readings:
        p = r.P_active_kw
        poste = r.periode_tarif or "HPH"
        pas_h = r.pas_minutes / 60.0
        ps_poste = ps_par_poste.get(poste, ps_max_global)

        taux = p / ps_poste * 100 if ps_poste > 0 else 0
        depassement_kw = max(0.0, p - ps_poste)
        cout = depassement_kw * TARIF_DEPASSEMENT_EUR_KW * pas_h

        if taux >= seuil_pct:
            peaks.append(
                {
                    "ts": r.ts_debut.isoformat(),
                    "P_active_kw": round(p, 2),
                    "periode_tarif": poste,
                    "ps_poste_kva": ps_poste,
                    "taux_utilisation_pct": round(taux, 1),
                    "depassement_kw": round(depassement_kw, 2),
                    "cout_estime_eur": round(cout, 2),
                }
            )

        if depassement_kw > 0:
            depassements_par_poste.setdefault(poste, []).append((depassement_kw, pas_h))

    # CMDPS par poste
    cmdps_list = []
    for poste, vals in depassements_par_poste.items():
        deps = [v[0] for v in vals]
        durees = [v[1] for v in vals]
        dq = math.sqrt(sum(d**2 for d in deps) / len(deps))
        cmdps_list.append(
            {
                "poste": poste,
                "n_points_depassement": len(deps),
                "depassement_total_kw": round(sum(deps), 2),
                "dq_kw": round(dq, 2),
                "duree_depassement_h": round(sum(durees), 3),
            }
        )

    return {
        **base,
        "n_pics": len(peaks),
        "cout_total_estime_eur": round(sum(p["cout_estime_eur"] for p in peaks), 2),
        "ps_par_poste_kva": ps_par_poste,
        "cmdps_par_poste": cmdps_list,
        "peaks": peaks[:50],
        "confidence": 1.0,
    }
