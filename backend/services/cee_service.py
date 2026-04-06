"""
PROMEOS — Service CEE (Certificats d'Économie d'Énergie)

Extrait de compliance_engine.py (V69).
Gère le cycle de vie des dossiers CEE : création, avancement kanban,
M&V (mesure & vérification), work packages.
"""

import json
from datetime import date, timedelta
from typing import List

from sqlalchemy.orm import Session

from models import (
    Obligation,
    Site,
    Portefeuille,
    EntiteJuridique,
    Evidence,
    StatutConformite,
    TypeEvidence,
    StatutEvidence,
)
from models.cee_models import WorkPackage, CeeDossier, CeeDossierEvidence
from models.enums import (
    WorkPackageSize,
    CeeDossierStep,
    CeeStatus,
    MVAlertType,
    ActionSourceType,
    ActionStatus,
)
from models.energy_models import FrequencyType
from config.patrimoine_assumptions import CEE_PRIX_MWHC_CUMAC_EUR


def _resolve_site_org(db: Session, site_id: int) -> int:
    """Resolve org_id from site_id."""
    from services.scope_utils import resolve_org_id_from_site

    return resolve_org_id_from_site(db, site_id) or 1  # Fallback to org 1 for demo


_CEE_EVIDENCE_TEMPLATE = [
    {"type_key": "devis", "label": "Devis signé travaux", "step": CeeDossierStep.DEVIS},
    {"type_key": "engagement", "label": "Lettre d'engagement CEE", "step": CeeDossierStep.ENGAGEMENT},
    {"type_key": "facture_travaux", "label": "Facture des travaux", "step": CeeDossierStep.TRAVAUX},
    {"type_key": "pv_reception", "label": "PV de réception chantier", "step": CeeDossierStep.PV_PHOTOS},
    {"type_key": "photos_chantier", "label": "Photos avant/après chantier", "step": CeeDossierStep.PV_PHOTOS},
    {"type_key": "rapport_mv", "label": "Rapport M&V (mesure & vérification)", "step": CeeDossierStep.MV},
    {"type_key": "attestation_fin", "label": "Attestation de fin de travaux", "step": CeeDossierStep.VERSEMENT},
]


def create_cee_dossier(
    db: Session,
    site_id: int,
    work_package_id: int,
) -> dict:
    """
    V69: Create a CEE dossier from a work package.
    Auto-creates:
    - Evidence items (proof template) linked to site coffre
    - Action items in Action Center for each kanban step
    Returns the dossier dict with evidence_items and action_ids.
    """
    from models import ActionItem

    wp = db.query(WorkPackage).filter(WorkPackage.id == work_package_id).first()
    if not wp:
        raise ValueError(f"WorkPackage {work_package_id} not found")
    if wp.site_id != site_id:
        raise ValueError(f"WorkPackage {work_package_id} does not belong to site {site_id}")

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    # Check no existing dossier
    existing = db.query(CeeDossier).filter(CeeDossier.work_package_id == work_package_id).first()
    if existing:
        raise ValueError(f"Dossier CEE already exists for WorkPackage {work_package_id}")

    # 1. Create CeeDossier
    dossier = CeeDossier(
        work_package_id=work_package_id,
        site_id=site_id,
        current_step=CeeDossierStep.DEVIS,
    )
    db.add(dossier)
    db.flush()  # get dossier.id

    # 1b. Auto-compute kWhc cumac if fiche_ref is set
    if wp.fiche_ref and site.surface_m2 and site.surface_m2 > 0:
        try:
            from regops.rules.cee_p6 import compute_cee_kwh_cumac

            result = compute_cee_kwh_cumac(
                fiche_ref=wp.fiche_ref,
                surface_m2=site.surface_m2,
                code_postal=site.code_postal,
                prix_mwhc_cumac_eur=CEE_PRIX_MWHC_CUMAC_EUR,
            )
            dossier.amount_cee_kwh = result.kwh_cumac
            dossier.amount_cee_eur = result.amount_eur
        except ValueError:
            pass  # Fiche inconnue ou données insuffisantes — on laisse NULL

    # 2. Create evidence items (proof template)
    evidence_items = []
    for tmpl in _CEE_EVIDENCE_TEMPLATE:
        # Also create an Evidence in the site coffre
        site_evidence = Evidence(
            site_id=site_id,
            type=TypeEvidence.CERTIFICAT,
            statut=StatutEvidence.MANQUANT,
            note=f"[CEE] {tmpl['label']} — {wp.label}",
        )
        db.add(site_evidence)
        db.flush()

        item = CeeDossierEvidence(
            dossier_id=dossier.id,
            site_id=site_id,
            label=tmpl["label"],
            type_key=tmpl["type_key"],
            statut=StatutEvidence.MANQUANT,
            evidence_id=site_evidence.id,
        )
        db.add(item)
        evidence_items.append(item)

    # 3. Create Action Center items for kanban steps
    action_ids = []
    org_id = _resolve_site_org(db, site_id)

    step_actions = [
        (CeeDossierStep.DEVIS, "Obtenir devis signé"),
        (CeeDossierStep.ENGAGEMENT, "Envoyer lettre d'engagement CEE"),
        (CeeDossierStep.TRAVAUX, "Réaliser les travaux"),
        (CeeDossierStep.PV_PHOTOS, "Collecter PV réception + photos chantier"),
        (CeeDossierStep.MV, "Produire rapport M&V"),
        (CeeDossierStep.VERSEMENT, "Obtenir versement prime CEE"),
    ]

    for i, (step, title) in enumerate(step_actions):
        action = ActionItem(
            org_id=org_id,
            site_id=site_id,
            source_type=ActionSourceType.COMPLIANCE,
            source_id=f"cee_dossier:{dossier.id}",
            source_key=f"cee_step:{step.value}:{dossier.id}",
            title=f"[CEE] {title} — {wp.label}",
            rationale=f"Étape dossier CEE: {step.value}",
            priority=3,
            severity="medium",
            status=ActionStatus.OPEN if i == 0 else ActionStatus.BLOCKED,
            category="conformite",
            estimated_gain_eur=wp.savings_eur_year,
        )
        db.add(action)
        db.flush()
        action_ids.append(action.id)

    dossier.action_ids_json = json.dumps(action_ids)

    # Update work package CEE status
    wp.cee_status = CeeStatus.OK

    db.commit()

    return {
        "dossier_id": dossier.id,
        "work_package_id": wp.id,
        "site_id": site_id,
        "current_step": dossier.current_step.value,
        "evidence_count": len(evidence_items),
        "action_ids": action_ids,
    }


def advance_cee_step(
    db: Session,
    dossier_id: int,
    new_step: str,
) -> dict:
    """
    V69: Advance a CEE dossier to the next kanban step.
    Updates corresponding Action Center items:
    - Mark current step action as done
    - Unblock next step action
    """
    from models import ActionItem

    dossier = db.query(CeeDossier).filter(CeeDossier.id == dossier_id).first()
    if not dossier:
        raise ValueError(f"CeeDossier {dossier_id} not found")

    try:
        target_step = CeeDossierStep(new_step)
    except ValueError:
        raise ValueError(f"Invalid CEE step: {new_step}")

    old_step = dossier.current_step
    dossier.current_step = target_step

    # Update linked actions
    action_ids = json.loads(dossier.action_ids_json or "[]")
    steps_list = list(CeeDossierStep)
    old_idx = steps_list.index(old_step)
    new_idx = steps_list.index(target_step)

    for action_id in action_ids:
        action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
        if not action:
            continue
        # Parse step from source_key: "cee_step:<step>:<dossier_id>"
        parts = action.source_key.split(":")
        if len(parts) >= 2:
            action_step_val = parts[1]
            try:
                action_step = CeeDossierStep(action_step_val)
                action_step_idx = steps_list.index(action_step)
                if action_step_idx < new_idx:
                    action.status = ActionStatus.DONE
                elif action_step_idx == new_idx:
                    action.status = ActionStatus.IN_PROGRESS
                # Leave future steps as BLOCKED
            except (ValueError, IndexError):
                pass

    db.commit()

    return {
        "dossier_id": dossier.id,
        "old_step": old_step.value,
        "new_step": target_step.value,
        "action_ids_updated": len(action_ids),
    }


def compute_mv_summary(
    db: Session,
    site_id: int,
) -> dict:
    """
    V69: Compute M&V (Mesure & Vérification) summary for a site.
    Baseline from consumption data, current from recent, delta + alerts.
    MVP heuristic — uses annual_kwh_total as baseline reference.
    """
    from models.energy_models import Meter, MeterReading
    from datetime import datetime

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    baseline_kwh = site.annual_kwh_total or 0
    baseline_monthly = round(baseline_kwh / 12, 1) if baseline_kwh else 0

    # Source de verite : unified consumption service (single source of truth)
    current_kwh = 0
    months_covered = 0
    meter_ids = []
    try:
        from services.consumption_unified_service import get_consumption_summary

        y_ago = date.today() - timedelta(days=365)
        summary = get_consumption_summary(db, site_id, y_ago, date.today())
        current_kwh = float(summary.get("value_kwh", 0) or 0)
        details = summary.get("details", {})
        metered_days = details.get("metered_days", 0)
        months_covered = max(metered_days // 30, details.get("billed_months", 0))

        # Recover meter_ids for data completeness check below
        from models import Meter

        meter_ids = [
            m.id
            for m in db.query(Meter)
            .filter(Meter.site_id == site_id, Meter.is_active.is_(True), Meter.parent_meter_id.is_(None))
            .all()
        ]
    except Exception:
        current_kwh = 0
        months_covered = 0

    current_monthly = round(current_kwh / max(1, months_covered), 1) if months_covered > 0 else 0

    # Recent readings (last 3 months) for data completeness check
    recent = []
    try:
        three_months_ago = date.today() - timedelta(days=90)
        if meter_ids:
            recent = (
                db.query(MeterReading)
                .filter(
                    MeterReading.meter_id.in_(meter_ids),
                    MeterReading.frequency == FrequencyType.MONTHLY,
                    MeterReading.timestamp >= three_months_ago,
                )
                .all()
            )
    except Exception:
        recent = []

    # Compute delta
    delta_pct = 0.0
    if baseline_monthly > 0 and current_monthly > 0:
        delta_pct = round(((current_monthly - baseline_monthly) / baseline_monthly) * 100, 1)

    # Alerts
    alerts = []

    # Alert 1: drift vs baseline (>10% increase)
    if delta_pct > 10:
        alerts.append(
            {
                "type": MVAlertType.BASELINE_DRIFT.value,
                "message": f"Dérive +{delta_pct}% vs baseline ({current_monthly:.0f} vs {baseline_monthly:.0f} kWh/mois)",
                "severity": "high" if delta_pct > 20 else "medium",
            }
        )

    # Alert 2: data missing (no recent consumption)
    if not recent or len(recent) < 3:
        alerts.append(
            {
                "type": MVAlertType.DATA_MISSING.value,
                "message": f"Données manquantes: seulement {len(recent)} relevé(s) récent(s)",
                "severity": "high",
            }
        )

    # Alert 3: upcoming obligation deadlines
    obligations = (
        db.query(Obligation)
        .filter(
            Obligation.site_id == site_id,
            Obligation.echeance != None,
            Obligation.statut != StatutConformite.CONFORME,
        )
        .all()
    )
    today = date.today()
    for o in obligations:
        if o.echeance and (o.echeance - today).days <= 90:
            alerts.append(
                {
                    "type": MVAlertType.DEADLINE_APPROACHING.value,
                    "message": f"Échéance {o.type.value} dans {(o.echeance - today).days}j ({o.echeance.isoformat()})",
                    "severity": "high" if (o.echeance - today).days <= 30 else "medium",
                }
            )

    return {
        "site_id": site_id,
        "baseline_kwh_month": baseline_monthly,
        "current_kwh_month": current_monthly,
        "delta_pct": delta_pct,
        "baseline_kwh_year": baseline_kwh,
        "current_kwh_year": current_kwh,
        "data_points": len(recent),
        "alerts": alerts,
    }


def get_site_work_packages(
    db: Session,
    site_id: int,
) -> list:
    """V69: Get all work packages for a site with CEE dossier status."""
    packages = (
        db.query(WorkPackage)
        .filter(
            WorkPackage.site_id == site_id,
        )
        .order_by(WorkPackage.created_at.desc())
        .all()
    )

    result = []
    for wp in packages:
        dossier = db.query(CeeDossier).filter(CeeDossier.work_package_id == wp.id).first()

        item = {
            "id": wp.id,
            "label": wp.label,
            "size": wp.size.value,
            "capex_eur": wp.capex_eur,
            "savings_eur_year": wp.savings_eur_year,
            "payback_years": wp.payback_years,
            "complexity": wp.complexity,
            "cee_status": wp.cee_status.value,
            "description": wp.description,
            "dossier": None,
        }

        if dossier:
            evidence_items = db.query(CeeDossierEvidence).filter(CeeDossierEvidence.dossier_id == dossier.id).all()
            action_ids = json.loads(dossier.action_ids_json or "[]")

            item["dossier"] = {
                "id": dossier.id,
                "current_step": dossier.current_step.value,
                "amount_cee_kwh": dossier.amount_cee_kwh,
                "amount_cee_eur": dossier.amount_cee_eur,
                "obliged_party": dossier.obliged_party,
                "action_ids": action_ids,
                "evidence_items": [
                    {
                        "id": ei.id,
                        "label": ei.label,
                        "type_key": ei.type_key,
                        "statut": ei.statut.value,
                        "owner": ei.owner,
                        "due_date": ei.due_date.isoformat() if ei.due_date else None,
                        "file_url": ei.file_url,
                        "evidence_id": ei.evidence_id,
                    }
                    for ei in evidence_items
                ],
            }

        result.append(item)

    return result


def compute_dossier_cee_amount(
    db: Session,
    dossier_id: int,
) -> dict:
    """
    (Re)compute the kWhc cumac amount for an existing CeeDossier.
    Uses: work_package.fiche_ref × site.surface_m2 × zone_coeff × duree_vie.
    Persists the result on the dossier row.
    """
    from regops.rules.cee_p6 import compute_cee_kwh_cumac

    dossier = db.query(CeeDossier).filter(CeeDossier.id == dossier_id).first()
    if not dossier:
        raise ValueError(f"CeeDossier {dossier_id} not found")

    wp = db.query(WorkPackage).filter(WorkPackage.id == dossier.work_package_id).first()
    if not wp:
        raise ValueError(f"WorkPackage {dossier.work_package_id} not found for dossier {dossier_id}")

    if not wp.fiche_ref:
        raise ValueError(f"WorkPackage {wp.id} has no fiche_ref — cannot compute CEE amount")

    site = db.query(Site).filter(Site.id == dossier.site_id).first()
    if not site:
        raise ValueError(f"Site {dossier.site_id} not found")

    surface = site.surface_m2
    if not surface or surface <= 0:
        raise ValueError(f"Site {site.id} has no valid surface_m2")

    result = compute_cee_kwh_cumac(
        fiche_ref=wp.fiche_ref,
        surface_m2=surface,
        code_postal=site.code_postal,
        prix_mwhc_cumac_eur=CEE_PRIX_MWHC_CUMAC_EUR,
    )

    dossier.amount_cee_kwh = result.kwh_cumac
    dossier.amount_cee_eur = result.amount_eur
    db.commit()

    return {
        "dossier_id": dossier.id,
        "fiche_ref": result.fiche_ref,
        "fiche_label": result.fiche_label,
        "surface_m2": result.surface_m2,
        "zone_climatique": result.zone_climatique,
        "zone_coefficient": result.zone_coefficient,
        "typical_savings_kwh_m2": result.typical_savings_kwh_m2,
        "duree_vie_ans": result.duree_vie_ans,
        "kwh_cumac": result.kwh_cumac,
        "amount_eur": result.amount_eur,
    }
