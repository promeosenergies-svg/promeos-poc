"""
Pont Power Intelligence → Centre d'action.
Idempotency key : power:{site_id}:{type_action} — 2 clics = 1 action.

Types d'actions : POWER_PS_OPTIM, POWER_TAN_PHI, POWER_NEBEF, POWER_PEAK_ALERT.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

POWER_ACTION_TEMPLATES = {
    "POWER_PS_OPTIM": {
        "title": "Optimisation puissance souscrite — {site_name} ({economie} €/an)",
        "category": "ECONOMIE",
        "rationale": (
            "PS surdimensionnée. PS actuelle max : {ps_actuelle} kVA · "
            "PS recommandée : {ps_recommandee} kVA · "
            "Économie TURPE estimée : {economie} €/an. {eir_warning}"
        ),
    },
    "POWER_TAN_PHI": {
        "title": "Correction facteur de puissance — {site_name} (tan φ = {tan_phi})",
        "category": "ECONOMIE",
        "rationale": (
            "tan φ = {tan_phi} > seuil 0.4 (TURPE 7). "
            "Pénalité réactive estimée : {penalite} €/an. "
            "Condensateurs recommandés (ROI estimé {roi} mois)."
        ),
    },
    "POWER_NEBEF": {
        "title": "Démarche NEBEF — {site_name} (potentiel {revenu} €/an)",
        "category": "REVENU",
        "rationale": (
            "Site éligible NEBEF (P_max = {p_max} kW ≥ 100 kW). "
            "Puissance effaçable : {p_effacable} kW. "
            "Revenu estimé : {revenu_min}–{revenu_max} €/an (central : {revenu} €/an)."
        ),
    },
    "POWER_PEAK_ALERT": {
        "title": "Dépassements puissance — {site_name} ({n_pics} pics · {cout} €)",
        "category": "RISQUE",
        "rationale": (
            "{n_pics} dépassements sur 30j. Coût TURPE estimé : {cout} €. Poste le plus impacté : {poste_max}."
        ),
    },
}


def create_power_action(
    db: Session,
    site_id: int,
    site_name: str,
    action_type: str,
    context: dict,
    impact_eur: float = 0,
    severity: str = "medium",
) -> dict:
    """Crée un ActionPlanItem depuis un résultat Power Intelligence. Idempotent."""
    template = POWER_ACTION_TEMPLATES.get(action_type)
    if not template:
        return {"error": f"Type inconnu : {action_type}"}

    idempotency_key = f"power:{site_id}:{action_type}"

    # Check idempotence via ActionPlanItem
    try:
        from models.action_plan_item import ActionPlanItem

        # Idempotence via source_ref (seul champ libre disponible sur ActionPlanItem)
        existing = db.query(ActionPlanItem).filter(ActionPlanItem.source_ref == idempotency_key).first()
        if existing:
            return {"action_id": existing.id, "status": "existing", "idempotency_key": idempotency_key}

        due_days = {"critical": 14, "high": 30, "medium": 60, "low": 90}.get(severity, 60)

        action = ActionPlanItem(
            issue_id=idempotency_key,
            domain="power",
            severity=severity,
            site_id=site_id,
            issue_code=action_type,
            issue_label=template["title"].format(**context),
            recommended_action=template["rationale"].format(**context),
            source_ref=idempotency_key,
            priority=severity,
            estimated_impact_eur=round(impact_eur),
            due_date=(datetime.now() + timedelta(days=due_days)),
            status="open",
        )
        db.add(action)
        db.commit()
        db.refresh(action)

        return {"action_id": action.id, "status": "created", "idempotency_key": idempotency_key}
    except Exception as e:
        return {"error": str(e), "idempotency_key": idempotency_key}


def create_ps_optim_action(db, site_id, site_name, optimizer_result) -> dict:
    """Crée une action depuis le résultat de l'optimiseur PS."""
    recos = optimizer_result.get("recommandations_par_poste", [])
    best = next((r for r in recos if r["action"] in ("REDUIRE_URGENT", "REDUIRE")), None)
    if not best:
        return {"status": "no_action_needed"}

    eir = "⚠ EIR requise (SGE F170)" if optimizer_result.get("eir_requis_global") else ""
    return create_power_action(
        db,
        site_id,
        site_name,
        "POWER_PS_OPTIM",
        {
            "site_name": site_name,
            "economie": int(optimizer_result.get("economie_totale_annuelle_eur", 0)),
            "ps_actuelle": best["ps_actuelle_kva"],
            "ps_recommandee": best["ps_recommandee_kva"],
            "eir_warning": eir,
        },
        impact_eur=optimizer_result.get("economie_totale_annuelle_eur", 0),
        severity="high" if best["action"] == "REDUIRE_URGENT" else "medium",
    )


def create_nebef_action(db, site_id, site_name, nebef_result) -> dict:
    if not nebef_result.get("eligible_technique"):
        return {"status": "not_eligible"}
    p = nebef_result.get("potentiel", {})
    return create_power_action(
        db,
        site_id,
        site_name,
        "POWER_NEBEF",
        {
            "site_name": site_name,
            "p_max": nebef_result.get("P_max_kw", 0),
            "p_effacable": p.get("P_effacable_total_kw", 0),
            "revenu": int(p.get("revenu_central_eur_an", 0)),
            "revenu_min": int(p.get("revenu_min_eur_an", 0)),
            "revenu_max": int(p.get("revenu_max_eur_an", 0)),
        },
        impact_eur=p.get("revenu_central_eur_an", 0),
    )


def create_tan_phi_action(db, site_id, site_name, factor_result) -> dict:
    kpis = factor_result.get("kpis", {})
    if not kpis.get("au_dessus_seuil"):
        return {"status": "compliant"}
    reco = factor_result.get("recommandation", {})
    return create_power_action(
        db,
        site_id,
        site_name,
        "POWER_TAN_PHI",
        {
            "site_name": site_name,
            "tan_phi": kpis.get("tan_phi_moyen", 0),
            "penalite": int(kpis.get("penalite_estimee_eur", 0)),
            "roi": reco.get("roi_estime_mois", 18),
        },
        impact_eur=kpis.get("penalite_estimee_eur", 0),
        severity="high" if kpis.get("penalite_estimee_eur", 0) > 1000 else "medium",
    )


def create_peak_alert_action(db, site_id, site_name, peaks_result) -> dict:
    if peaks_result.get("n_pics", 0) < 3:
        return {"status": "no_action_needed"}
    cmdps = peaks_result.get("cmdps_par_poste", [])
    poste_max = max(cmdps, key=lambda c: c.get("dq_kw", 0), default={}).get("poste", "HPH") if cmdps else "HPH"
    return create_power_action(
        db,
        site_id,
        site_name,
        "POWER_PEAK_ALERT",
        {
            "site_name": site_name,
            "n_pics": peaks_result.get("n_pics", 0),
            "cout": int(peaks_result.get("cout_total_estime_eur", 0)),
            "poste_max": poste_max,
        },
        impact_eur=peaks_result.get("cout_total_estime_eur", 0),
        severity="high" if peaks_result.get("cout_total_estime_eur", 0) > 500 else "medium",
    )
