"""
PROMEOS - Demo Seed: BACS Assets Generator (V87)
Creates BacsAsset, BacsCvcSystem, BacsAssessment, BacsInspection per site.
"""

import json
import random
from datetime import date, datetime, timezone

from models.bacs_models import BacsAsset, BacsCvcSystem, BacsAssessment, BacsInspection
from models.bacs_regulatory import BacsExemption
from models.enums import CvcSystemType, CvcArchitecture, BacsTriggerReason, InspectionStatus


def generate_bacs(db, sites: list, rng: random.Random) -> dict:
    """
    Create BACS asset tree (asset -> CVC systems -> assessment -> inspection) per site.
    Uses site._cvc_kw (set by gen_master) and site.tertiaire_area_m2.

    Helios obligations:
      Paris HQ (cvc=300)     : obligated HIGH  deadline 2025
      Lyon bureau (cvc=50)   : out of scope (< 70 kW)
      Toulouse usine (cvc=150): non-tertiary   -> not obligated
      Nice hotel (cvc=280)   : obligated LOW   deadline 2030
      Marseille ecole (cvc=120): obligated LOW deadline 2030
    """
    assets_count = 0
    systems_count = 0
    assessments_count = 0
    inspections_count = 0
    exemptions_count = 0

    for site in sites:
        # cvc_kw: set as dynamic attribute by gen_master (same pattern as gen_compliance)
        cvc_kw = getattr(site, "_cvc_kw", 0) or 0
        # is_tertiary: warehouse (Toulouse) has tertiaire_area_m2=None
        is_tertiary = (site.tertiaire_area_m2 or 0) > 0

        # --- BacsAsset (1 per site) ---
        asset = BacsAsset(
            site_id=site.id,
            is_tertiary_non_residential=is_tertiary,
            pc_date=date(rng.randint(1980, 2015), rng.randint(1, 12), 1),
            renewal_events_json="[]",
            responsible_party_json=json.dumps(
                {
                    "type": "owner",
                    "name": site.nom,
                }
            ),
        )
        db.add(asset)
        db.flush()
        assets_count += 1

        # --- BacsCvcSystems ---
        if cvc_kw > 70:
            heating_kw = int(cvc_kw * 0.6)
            cooling_kw = int(cvc_kw * 0.4)
            db.add(
                BacsCvcSystem(
                    asset_id=asset.id,
                    system_type=CvcSystemType.HEATING,
                    architecture=CvcArchitecture.CASCADE,
                    units_json=json.dumps([{"label": "Chaudiere gaz", "kw": heating_kw}]),
                    putile_kw_computed=float(heating_kw),
                    engine_version="demo_seed_v87",
                )
            )
            db.add(
                BacsCvcSystem(
                    asset_id=asset.id,
                    system_type=CvcSystemType.COOLING,
                    architecture=CvcArchitecture.INDEPENDENT,
                    units_json=json.dumps([{"label": "Groupe froid", "kw": cooling_kw}]),
                    putile_kw_computed=float(cooling_kw),
                    engine_version="demo_seed_v87",
                )
            )
            systems_count += 2
        elif cvc_kw > 0:
            db.add(
                BacsCvcSystem(
                    asset_id=asset.id,
                    system_type=CvcSystemType.VENTILATION,
                    architecture=CvcArchitecture.INDEPENDENT,
                    units_json=json.dumps([{"label": "CTA", "kw": int(cvc_kw)}]),
                    putile_kw_computed=float(cvc_kw),
                    engine_version="demo_seed_v87",
                )
            )
            systems_count += 1

        # --- BacsAssessment ---
        is_obligated = is_tertiary and cvc_kw > 70
        if cvc_kw > 290:
            threshold = 290
            deadline = date(2025, 1, 1)
            trigger = BacsTriggerReason.THRESHOLD_290
        elif cvc_kw > 70:
            threshold = 70
            deadline = date(2030, 1, 1)
            trigger = BacsTriggerReason.THRESHOLD_70
        else:
            threshold = None
            deadline = None
            trigger = None

        db.add(
            BacsAssessment(
                asset_id=asset.id,
                assessed_at=datetime.now(timezone.utc),
                threshold_applied=threshold,
                is_obligated=is_obligated,
                deadline_date=deadline,
                trigger_reason=trigger,
                tri_exemption_possible=not is_obligated or cvc_kw < 150,
                tri_years=round(rng.uniform(4.0, 14.0), 1),
                confidence_score=round(rng.uniform(0.72, 0.98), 2),
                compliance_score=round(rng.uniform(20.0, 90.0), 1),
                rule_id="BACS_V87_DEMO",
                engine_version="demo_seed_v87",
            )
        )
        assessments_count += 1

        # --- BacsInspection (only for obligated sites) ---
        if is_obligated:
            status = rng.choice([InspectionStatus.COMPLETED, InspectionStatus.SCHEDULED])
            insp_date = (
                date(2024, rng.randint(1, 12), rng.randint(1, 28)) if status == InspectionStatus.COMPLETED else None
            )
            db.add(
                BacsInspection(
                    asset_id=asset.id,
                    inspection_date=insp_date,
                    due_next_date=date(2029, 1, 1),
                    report_ref=f"INSP-BACS-{site.id:04d}-2024",
                    status=status,
                )
            )
            inspections_count += 1

        # --- BacsExemption (pour sites avec TRI > 10 ans) ---
        tri_val = round(rng.uniform(4.0, 14.0), 1)
        if is_obligated and tri_val > 10:
            exemption_scenarios = [
                {
                    "type": "tri_non_viable",
                    "status": "approved",
                    "motif": f"TRI de {tri_val} ans depasse le seuil de 10 ans. "
                    f"Installation BACS estimee a {int(cvc_kw * 120)} EUR "
                    f"pour des economies annuelles de {int(cvc_kw * 8)} EUR.",
                    "tri": tri_val,
                    "cout": float(int(cvc_kw * 120)),
                    "eco": float(int(cvc_kw * 8)),
                },
                {
                    "type": "tri_non_viable",
                    "status": "submitted",
                    "motif": f"Etude TRI realisee: {tri_val} ans. Dossier soumis au prefet.",
                    "tri": tri_val,
                    "cout": float(int(cvc_kw * 130)),
                    "eco": float(int(cvc_kw * 7)),
                },
            ]
            scenario = rng.choice(exemption_scenarios)
            ex = BacsExemption(
                asset_id=asset.id,
                exemption_type=scenario["type"],
                status=scenario["status"],
                motif_detaille=scenario["motif"],
                tri_annees=scenario["tri"],
                cout_installation_eur=scenario["cout"],
                economies_annuelles_eur=scenario["eco"],
                date_demande=date(2024, rng.randint(3, 9), rng.randint(1, 28)),
            )
            if scenario["status"] == "approved":
                ex.date_decision = date(2024, rng.randint(10, 12), rng.randint(1, 28))
                ex.date_expiration = date(2029, 12, 31)
                ex.decision_reference = f"AP-BACS-{site.id:04d}-2024"
            db.add(ex)
            exemptions_count += 1

        db.flush()

    return {
        "bacs_assets_count": assets_count,
        "bacs_systems_count": systems_count,
        "bacs_assessments_count": assessments_count,
        "bacs_inspections_count": inspections_count,
        "bacs_exemptions_count": exemptions_count,
    }
