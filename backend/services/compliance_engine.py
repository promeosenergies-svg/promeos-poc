"""
PROMEOS - Compliance Engine (LEGACY)

⚠️  DÉPRÉCIÉ — Ce moteur est conservé pour backward-compat (snapshots Site).
    La source de vérité est désormais RegOps (regops/engine.py) qui orchestre
    les 4 évaluateurs YAML et produit le score unifié A.2.

    Ce moteur :
    - recompute_site() : écrit les snapshots statut_decret_tertiaire/statut_bacs sur Site
    - est appelé par POST /api/compliance/recompute (endpoint legacy)
    - sert de fallback pour compliance_score_service.py si RegAssessment absent

    NE PAS ajouter de nouvelles règles ici — utiliser regops/rules/*.py + YAML.

V68: Data Readiness Gate — compute_readiness, compute_applicability,
compute_scores, compute_deadlines, compute_data_trust, site/portfolio summaries.
"""

from collections import defaultdict
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from models import (
    Obligation,
    Site,
    Portefeuille,
    EntiteJuridique,
    Organisation,
    Evidence,
    Batiment,
    ComplianceFinding,
    BillingInsight,
    StatutConformite,
    TypeObligation,
    TypeEvidence,
    StatutEvidence,
)

# Status severity ranking for "worst status" logic
_STATUS_SEVERITY = {
    StatutConformite.CONFORME: 0,
    StatutConformite.DEROGATION: 1,
    StatutConformite.A_RISQUE: 2,
    StatutConformite.NON_CONFORME: 3,
}

# BACS thresholds (kW CVC nominal)
BACS_SEUIL_HAUT = 290.0  # deadline 2025-01-01
BACS_SEUIL_BAS = 70.0  # deadline 2030-01-01
BACS_DEADLINE_290 = date(2025, 1, 1)
BACS_DEADLINE_70 = date(2030, 1, 1)

# ── Constantes réglementaires ────────────────────────────────────────
# Source : Code de la construction L174-1 / ADEME Base Empreinte V23.6
BASE_PENALTY_EURO = 7_500  # Pénalité non-conformité
A_RISQUE_PENALTY_RATIO = 0.5  # 50 % pour sites à risque
A_RISQUE_PENALTY_EURO = int(BASE_PENALTY_EURO * A_RISQUE_PENALTY_RATIO)  # 3 750
# CO2 — source unique : config/emission_factors.py (ADEME Base Empreinte V23.6)
from config.emission_factors import get_emission_factor as _get_ef
CO2_FACTOR_ELEC_KG_KWH = _get_ef("ELEC")  # 0.052
CO2_FACTOR_GAZ_KG_KWH = _get_ef("GAZ")    # 0.227

# Action text templates ordered by priority (highest first)
_ACTION_TEMPLATES = [
    (TypeObligation.BACS, StatutConformite.NON_CONFORME, "Installer GTB/GTC conforme (BACS obligatoire)"),
    (TypeObligation.DECRET_TERTIAIRE, StatutConformite.NON_CONFORME, "Audit decret tertiaire - trajectoire 2030 KO"),
    (TypeObligation.BACS, StatutConformite.A_RISQUE, "Planifier mise en conformite BACS avant echeance"),
    (TypeObligation.DECRET_TERTIAIRE, StatutConformite.A_RISQUE, "Verifier trajectoire decret tertiaire"),
]


# ========================================
# Layer A: Pure calculation functions
# ========================================


def worst_status(obligations: List[Obligation]) -> Optional[StatutConformite]:
    """Return the worst (most severe) status from a list of obligations."""
    if not obligations:
        return None
    return max(obligations, key=lambda o: _STATUS_SEVERITY[o.statut]).statut


def _worst_from_statuts(statuts: List[StatutConformite]) -> Optional[StatutConformite]:
    """Return the worst status from a plain list of StatutConformite values."""
    if not statuts:
        return None
    return max(statuts, key=lambda s: _STATUS_SEVERITY[s])


def average_avancement(obligations: List[Obligation]) -> float:
    """Return the average avancement_pct across obligations."""
    if not obligations:
        return 0.0
    return round(sum(o.avancement_pct for o in obligations) / len(obligations), 1)


def compute_risque_financier(obligations: List[Obligation]) -> float:
    """Calculate financial risk: NON_CONFORME = 100% penalty, A_RISQUE = 50% penalty."""
    non_conforme_count = sum(1 for o in obligations if o.statut == StatutConformite.NON_CONFORME)
    a_risque_count = sum(1 for o in obligations if o.statut == StatutConformite.A_RISQUE)
    return round(BASE_PENALTY_EURO * non_conforme_count + A_RISQUE_PENALTY_EURO * a_risque_count, 2)


def compute_action_recommandee(obligations: List[Obligation]) -> Optional[str]:
    """Return the highest-priority recommended action."""
    for ob_type, ob_statut, action_text in _ACTION_TEMPLATES:
        for o in obligations:
            if o.type == ob_type and o.statut == ob_statut:
                return action_text
    return None


def bacs_deadline_for_power(cvc_power_kw: float) -> Optional[date]:
    """Return the BACS regulatory deadline based on CVC power.

    >290 kW -> 2025-01-01
    >70 kW  -> 2030-01-01
    <=70 kW -> None (not concerned)
    """
    if cvc_power_kw > BACS_SEUIL_HAUT:
        return BACS_DEADLINE_290
    if cvc_power_kw > BACS_SEUIL_BAS:
        return BACS_DEADLINE_70
    return None


def compute_bacs_statut(
    evidences: List[Evidence],
    echeance: date,
    today: Optional[date] = None,
) -> StatutConformite:
    """
    Compute BACS obligation statut from evidences and deadline.

    Priority:
    1. Valid DEROGATION_BACS evidence  -> DEROGATION
    2. Valid ATTESTATION_BACS evidence -> CONFORME
    3. Deadline passed (today > echeance) -> NON_CONFORME
    4. Otherwise -> A_RISQUE
    """
    if today is None:
        today = date.today()

    bacs_evidences = [e for e in evidences if e.type in (TypeEvidence.ATTESTATION_BACS, TypeEvidence.DEROGATION_BACS)]

    has_valid_derogation = any(
        e.type == TypeEvidence.DEROGATION_BACS and e.statut == StatutEvidence.VALIDE for e in bacs_evidences
    )
    if has_valid_derogation:
        return StatutConformite.DEROGATION

    has_valid_attestation = any(
        e.type == TypeEvidence.ATTESTATION_BACS and e.statut == StatutEvidence.VALIDE for e in bacs_evidences
    )
    if has_valid_attestation:
        return StatutConformite.CONFORME

    if today > echeance:
        return StatutConformite.NON_CONFORME

    return StatutConformite.A_RISQUE


def compute_site_snapshot(
    obligations: List[Obligation],
    evidences: Optional[List[Evidence]] = None,
) -> dict:
    """
    Compute all Site snapshot fields from Obligations (+ Evidences for BACS).
    Does NOT touch anomalie_facture (not derivable from obligations).

    Pure function: does NOT mutate the obligation objects.
    """
    decret = [o for o in obligations if o.type == TypeObligation.DECRET_TERTIAIRE]
    bacs = [o for o in obligations if o.type == TypeObligation.BACS]

    # Resolve BACS statuts without mutating obligations
    if evidences is not None:
        bacs_resolved = []
        for ob in bacs:
            if ob.echeance:
                bacs_resolved.append(compute_bacs_statut(evidences, ob.echeance))
            else:
                bacs_resolved.append(ob.statut)
    else:
        bacs_resolved = [ob.statut for ob in bacs]

    worst_bacs = _worst_from_statuts(bacs_resolved)

    # Count non-conforme + a_risque across both dimensions
    non_conforme_count = sum(1 for o in decret if o.statut == StatutConformite.NON_CONFORME) + sum(
        1 for s in bacs_resolved if s == StatutConformite.NON_CONFORME
    )
    a_risque_count = sum(1 for o in decret if o.statut == StatutConformite.A_RISQUE) + sum(
        1 for s in bacs_resolved if s == StatutConformite.A_RISQUE
    )

    # Build resolved obligation pairs for action recommendation
    resolved_pairs = [(o.type, o.statut) for o in decret]
    resolved_pairs += [(TypeObligation.BACS, s) for s in bacs_resolved]

    action = None
    for ob_type, ob_statut, action_text in _ACTION_TEMPLATES:
        if (ob_type, ob_statut) in resolved_pairs:
            action = action_text
            break

    return {
        "statut_decret_tertiaire": worst_status(decret) or StatutConformite.A_RISQUE,
        "avancement_decret_pct": average_avancement(decret),
        "statut_bacs": worst_bacs or StatutConformite.A_RISQUE,
        "action_recommandee": action,
        "risque_financier_euro": round(
            BASE_PENALTY_EURO * non_conforme_count + BASE_PENALTY_EURO * 0.5 * a_risque_count, 2
        ),
    }


# ========================================
# Layer A2: V68 — Readiness Gate functions
# ========================================

# Per-regulation required fields for readiness evaluation
_READINESS_FIELDS = {
    "tertiaire_operat": {
        "blocking": ["tertiaire_area_m2", "operat_status", "annual_kwh_total"],
        "recommended": ["is_multi_occupied", "surface_m2"],
        "optional": ["naf_code"],
    },
    "bacs": {
        "blocking": ["cvc_power_kw"],
        "recommended": ["has_bacs_attestation", "has_bacs_derogation"],
        "optional": [],
    },
    "aper": {
        "blocking": ["parking_area_m2", "roof_area_m2"],
        "recommended": ["parking_type"],
        "optional": [],
    },
}

# CTA link targets for missing fields
_FIELD_CTA = {
    "tertiaire_area_m2": {"target": "patrimoine", "label": "Renseigner surface tertiaire"},
    "operat_status": {"target": "patrimoine", "label": "Mettre à jour le statut OPERAT"},
    "annual_kwh_total": {"target": "consommation", "label": "Importer les consommations"},
    "cvc_power_kw": {"target": "patrimoine", "label": "Renseigner la puissance CVC"},
    "parking_area_m2": {"target": "patrimoine", "label": "Renseigner la surface parking"},
    "roof_area_m2": {"target": "patrimoine", "label": "Renseigner la surface toiture"},
    "parking_type": {"target": "patrimoine", "label": "Préciser le type de parking"},
    "has_bacs_attestation": {"target": "conformite", "label": "Joindre l'attestation BACS"},
    "has_bacs_derogation": {"target": "conformite", "label": "Joindre la dérogation BACS"},
    "is_multi_occupied": {"target": "patrimoine", "label": "Indiquer occupation multiple"},
    "surface_m2": {"target": "patrimoine", "label": "Renseigner la surface totale"},
    "naf_code": {"target": "patrimoine", "label": "Renseigner le code NAF"},
}


def _resolve_field(site: Site, batiments: List, evidences: List, field_name: str):
    """Resolve a field value from site/batiment/evidence context."""
    if hasattr(site, field_name) and getattr(site, field_name, None) is not None:
        return getattr(site, field_name)
    if field_name == "cvc_power_kw":
        for b in batiments:
            if b.cvc_power_kw is not None:
                return b.cvc_power_kw
        return None
    if field_name == "has_bacs_attestation":
        return any(e.type == TypeEvidence.ATTESTATION_BACS and e.statut == StatutEvidence.VALIDE for e in evidences)
    if field_name == "has_bacs_derogation":
        return any(e.type == TypeEvidence.DEROGATION_BACS and e.statut == StatutEvidence.VALIDE for e in evidences)
    return None


def _is_filled(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, bool):
        return True  # False is a valid answer for booleans
    return True


def compute_readiness(
    site: Site,
    batiments: List,
    evidences: List,
) -> dict:
    """
    Compute data readiness gate for a site.

    Returns:
        completeness_pct: float 0-100
        missing: list of {field, level, regulation, cta_target, cta_label}
        gate_status: BLOCKED | WARNING | OK
    """
    missing = []
    total = 0
    filled = 0

    for reg, spec in _READINESS_FIELDS.items():
        for level in ("blocking", "recommended", "optional"):
            for field_name in spec[level]:
                total += 1
                val = _resolve_field(site, batiments, evidences, field_name)
                if _is_filled(val):
                    filled += 1
                else:
                    cta = _FIELD_CTA.get(field_name, {})
                    missing.append(
                        {
                            "field": field_name,
                            "level": level,
                            "regulation": reg,
                            "cta_target": cta.get("target", "patrimoine"),
                            "cta_label": cta.get("label", f"Renseigner {field_name}"),
                        }
                    )

    completeness = round((filled / max(1, total)) * 100, 1)
    has_blocking = any(m["level"] == "blocking" for m in missing)
    has_recommended = any(m["level"] == "recommended" for m in missing)

    if has_blocking:
        gate_status = "BLOCKED"
    elif has_recommended:
        gate_status = "WARNING"
    else:
        gate_status = "OK"

    return {
        "completeness_pct": completeness,
        "missing": missing,
        "gate_status": gate_status,
    }


def compute_applicability(
    site: Site,
    batiments: List,
) -> dict:
    """
    Compute which regulations apply to a site.

    Returns dict keyed by regulation: {applicable, reason, missing_fields}
    """
    cvc_kw = 0.0
    for b in batiments:
        cvc_kw += b.cvc_power_kw or 0
    if hasattr(site, "_cvc_kw") and site._cvc_kw is not None:
        cvc_kw = site._cvc_kw
    has_cvc_data = cvc_kw > 0 or any(b.cvc_power_kw is not None for b in batiments)

    tertiaire = site.tertiaire_area_m2 or 0
    parking = site.parking_area_m2 or 0
    roof = site.roof_area_m2 or 0

    result = {}

    # Tertiaire
    if tertiaire > 0:
        if tertiaire >= 1000:
            result["tertiaire_operat"] = {
                "applicable": True,
                "reason": f"Surface tertiaire {tertiaire:.0f} m² >= 1000 m²",
                "missing_fields": [],
            }
        else:
            result["tertiaire_operat"] = {
                "applicable": False,
                "reason": f"Surface tertiaire {tertiaire:.0f} m² < 1000 m²",
                "missing_fields": [],
            }
    else:
        result["tertiaire_operat"] = {
            "applicable": None,  # Uncertain
            "reason": "Surface tertiaire non renseignée",
            "missing_fields": ["tertiaire_area_m2"],
        }

    # BACS
    if has_cvc_data:
        if cvc_kw > BACS_SEUIL_BAS:
            result["bacs"] = {
                "applicable": True,
                "reason": f"CVC {cvc_kw:.0f} kW > {BACS_SEUIL_BAS:.0f} kW",
                "missing_fields": [],
            }
        else:
            result["bacs"] = {
                "applicable": False,
                "reason": f"CVC {cvc_kw:.0f} kW <= {BACS_SEUIL_BAS:.0f} kW",
                "missing_fields": [],
            }
    else:
        result["bacs"] = {
            "applicable": None,
            "reason": "Puissance CVC non renseignée",
            "missing_fields": ["cvc_power_kw"],
        }

    # APER
    if parking > 0 or roof > 0:
        if parking >= 1500 or roof >= 500:
            result["aper"] = {
                "applicable": True,
                "reason": f"Parking {parking:.0f} m² / Toiture {roof:.0f} m²",
                "missing_fields": [],
            }
        else:
            result["aper"] = {
                "applicable": False,
                "reason": f"Parking {parking:.0f} m² < 1500 et toiture {roof:.0f} m² < 500",
                "missing_fields": [],
            }
    else:
        result["aper"] = {
            "applicable": None,
            "reason": "Surfaces parking/toiture non renseignées",
            "missing_fields": ["parking_area_m2", "roof_area_m2"],
        }

    return result


def compute_scores(
    obligations: List[Obligation],
    findings: List[ComplianceFinding],
) -> dict:
    """
    Compute risk/opportunity scores (V68 heuristic).

    Returns: reg_risk, evidence_risk, financial_opportunity
    """
    nok_count = sum(1 for o in obligations if o.statut == StatutConformite.NON_CONFORME)
    a_risque_count = sum(1 for o in obligations if o.statut == StatutConformite.A_RISQUE)
    unknown_findings = sum(1 for f in findings if f.status == "UNKNOWN")
    nok_findings = sum(1 for f in findings if f.status == "NOK")

    # compliance_risk_score: 0-100 (0=aucun risque, 100=risque max)
    compliance_risk_score = min(100, nok_count * 30 + a_risque_count * 15 + nok_findings * 10)

    # LEGACY: compliance_score conserve pour backward compat.
    # Le score OFFICIEL du site est compliance_score_service.compute_site_compliance_score() (A.2).
    # Cette valeur n'est PAS affichee dans l'UI (remplacee par A.2 au Step 2).
    compliance_score = 100 - compliance_risk_score

    # evidence_risk: based on unknown findings (data gaps)
    evidence_risk = min(100, unknown_findings * 20 + a_risque_count * 10)

    # financial_opportunity: penalty avoidance (EUR) — NON_CONFORME=100%, A_RISQUE=50%
    financial_opportunity = round(BASE_PENALTY_EURO * nok_count + BASE_PENALTY_EURO * 0.5 * a_risque_count, 2)

    return {
        "reg_risk": compliance_risk_score,  # backward compat
        "compliance_risk_score": compliance_risk_score,
        "compliance_score": compliance_score,
        "evidence_risk": evidence_risk,
        "financial_opportunity_eur": financial_opportunity,
    }


def compute_deadlines(
    obligations: List[Obligation],
    findings: List[ComplianceFinding],
    today: Optional[date] = None,
) -> dict:
    """
    Compute upcoming deadlines bucketed into 30/90/180 days.

    Returns: {d30: [...], d90: [...], d180: [...], beyond: [...]}
    """
    if today is None:
        today = date.today()

    d30, d90, d180, beyond = [], [], [], []

    items = []
    for o in obligations:
        if o.echeance and o.statut != StatutConformite.CONFORME:
            items.append(
                {
                    "type": "obligation",
                    "regulation": o.type.value if o.type else "?",
                    "description": o.description or "",
                    "deadline": o.echeance.isoformat(),
                    "statut": o.statut.value if o.statut else "?",
                    "days_remaining": (o.echeance - today).days,
                }
            )
    for f in findings:
        if f.deadline and f.status in ("NOK", "UNKNOWN"):
            items.append(
                {
                    "type": "finding",
                    "regulation": f.regulation or "?",
                    "description": f.evidence or "",
                    "deadline": f.deadline.isoformat(),
                    "statut": f.status,
                    "days_remaining": (f.deadline - today).days,
                }
            )

    # Deduplicate by regulation+deadline
    seen = set()
    unique_items = []
    for item in items:
        key = (item["regulation"], item["deadline"])
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
    unique_items.sort(key=lambda x: x["days_remaining"])

    for item in unique_items:
        days = item["days_remaining"]
        if days <= 30:
            d30.append(item)
        elif days <= 90:
            d90.append(item)
        elif days <= 180:
            d180.append(item)
        else:
            beyond.append(item)

    return {"d30": d30, "d90": d90, "d180": d180, "beyond": beyond}


def compute_data_trust(
    site: Site,
    db: Session,
) -> dict:
    """
    Compute data trust score based on shadow billing anomalies.

    Returns: trust_score (0-100), anomaly_count, reasons
    """
    try:
        anomalies = (
            db.query(BillingInsight)
            .filter(
                BillingInsight.site_id == site.id,
                BillingInsight.insight_status.in_(["open", "ack"]),
            )
            .all()
        )
    except Exception:
        # BillingInsight table may not exist yet — graceful stub
        return {"trust_score": 100, "anomaly_count": 0, "reasons": ["billing_not_available"]}

    count = len(anomalies)
    critical = sum(1 for a in anomalies if a.severity == "critical")
    high = sum(1 for a in anomalies if a.severity == "high")

    # Trust formula: 100 - 25*critical - 10*high - 3*other
    raw = 100 - 25 * critical - 10 * high - 3 * max(0, count - critical - high)
    trust_score = max(0, min(100, raw))

    reasons = []
    if critical > 0:
        reasons.append(f"{critical} anomalie(s) critique(s)")
    if high > 0:
        reasons.append(f"{high} anomalie(s) élevée(s)")
    if count == 0:
        reasons.append("aucune anomalie détectée")

    return {"trust_score": trust_score, "anomaly_count": count, "reasons": reasons}


def compute_site_compliance_summary(
    db: Session,
    site_id: int,
    today: Optional[date] = None,
) -> dict:
    """
    V68: Full compliance summary for a single site.
    Aggregates readiness, applicability, scores, deadlines, data trust.
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    batiments = db.query(Batiment).filter(Batiment.site_id == site_id).all()
    evidences = db.query(Evidence).filter(Evidence.site_id == site_id).all()
    obligations = db.query(Obligation).filter(Obligation.site_id == site_id).all()
    findings = db.query(ComplianceFinding).filter(ComplianceFinding.site_id == site_id).all()

    readiness = compute_readiness(site, batiments, evidences)
    applicability = compute_applicability(site, batiments)
    snapshot = compute_site_snapshot(obligations, evidences)
    scores = compute_scores(obligations, findings)
    deadlines = compute_deadlines(obligations, findings, today)
    trust = compute_data_trust(site, db)

    return {
        "site_id": site.id,
        "site_nom": site.nom,
        "readiness": readiness,
        "applicability": applicability,
        "snapshot": {
            "statut_decret_tertiaire": snapshot["statut_decret_tertiaire"].value,
            "avancement_decret_pct": snapshot["avancement_decret_pct"],
            "statut_bacs": snapshot["statut_bacs"].value,
            "action_recommandee": snapshot["action_recommandee"],
            "risque_financier_euro": snapshot["risque_financier_euro"],
        },
        "scores": scores,
        "deadlines": deadlines,
        "data_trust": trust,
        "obligations_count": len(obligations),
        "findings_count": len(findings),
        "evidences_count": len(evidences),
    }


def compute_portfolio_compliance_summary(
    db: Session,
    org_id: int,
    today: Optional[date] = None,
) -> dict:
    """
    V68: Portfolio-level compliance summary.
    Aggregates all sites for an organisation.
    """
    site_ids = [
        row[0]
        for row in db.query(Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    ]

    if not site_ids:
        return {
            "org_id": org_id,
            "total_sites": 0,
            "sites": [],
            "kpis": {"sites_blocked": 0, "sites_warning": 0, "sites_ok": 0},
            "top_blockers": [],
            "deadlines": {"d30": [], "d90": [], "d180": [], "beyond": []},
            "untrusted_sites": [],
        }

    # Bulk load
    all_batiments = db.query(Batiment).filter(Batiment.site_id.in_(site_ids)).all()
    all_evidences = db.query(Evidence).filter(Evidence.site_id.in_(site_ids)).all()
    all_obligations = db.query(Obligation).filter(Obligation.site_id.in_(site_ids)).all()
    all_findings = db.query(ComplianceFinding).filter(ComplianceFinding.site_id.in_(site_ids)).all()
    all_sites = db.query(Site).filter(Site.id.in_(site_ids)).all()

    # Index by site
    bats_by = defaultdict(list)
    for b in all_batiments:
        bats_by[b.site_id].append(b)
    evs_by = defaultdict(list)
    for e in all_evidences:
        evs_by[e.site_id].append(e)
    obs_by = defaultdict(list)
    for o in all_obligations:
        obs_by[o.site_id].append(o)
    fnd_by = defaultdict(list)
    for f in all_findings:
        fnd_by[f.site_id].append(f)

    sites_out = []
    kpis = {"sites_blocked": 0, "sites_warning": 0, "sites_ok": 0}
    all_missing = []
    all_deadlines_items = {"d30": [], "d90": [], "d180": [], "beyond": []}
    untrusted = []

    for site in all_sites:
        readiness = compute_readiness(site, bats_by[site.id], evs_by[site.id])
        applicability = compute_applicability(site, bats_by[site.id])
        scores = compute_scores(obs_by[site.id], fnd_by[site.id])
        deadlines = compute_deadlines(obs_by[site.id], fnd_by[site.id], today)
        trust = compute_data_trust(site, db)

        gate = readiness["gate_status"]
        if gate == "BLOCKED":
            kpis["sites_blocked"] += 1
        elif gate == "WARNING":
            kpis["sites_warning"] += 1
        else:
            kpis["sites_ok"] += 1

        # Collect missing for top_blockers
        for m in readiness["missing"]:
            if m["level"] == "blocking":
                all_missing.append({**m, "site_id": site.id, "site_nom": site.nom})

        # Merge deadlines
        for bucket in ("d30", "d90", "d180", "beyond"):
            for item in deadlines[bucket]:
                all_deadlines_items[bucket].append(
                    {
                        **item,
                        "site_id": site.id,
                        "site_nom": site.nom,
                    }
                )

        if trust["trust_score"] < 70:
            untrusted.append(
                {
                    "site_id": site.id,
                    "site_nom": site.nom,
                    "trust_score": trust["trust_score"],
                    "anomaly_count": trust["anomaly_count"],
                    "reasons": trust["reasons"],
                }
            )

        sites_out.append(
            {
                "site_id": site.id,
                "site_nom": site.nom,
                "gate_status": gate,
                "completeness_pct": readiness["completeness_pct"],
                "reg_risk": scores["compliance_risk_score"],
                "compliance_risk_score": scores["compliance_risk_score"],
                "compliance_score": scores["compliance_score"],
                "financial_opportunity_eur": scores["financial_opportunity_eur"],
                "applicability": {k: v["applicable"] for k, v in applicability.items()},
            }
        )

    # Top blockers: aggregate by field
    blocker_counts = defaultdict(lambda: {"count": 0, "sites": [], "cta_target": "", "cta_label": ""})
    for m in all_missing:
        key = m["field"]
        blocker_counts[key]["count"] += 1
        blocker_counts[key]["sites"].append(m["site_nom"])
        blocker_counts[key]["cta_target"] = m["cta_target"]
        blocker_counts[key]["cta_label"] = m["cta_label"]
        blocker_counts[key]["regulation"] = m["regulation"]
    top_blockers = sorted(
        [{"field": k, **v} for k, v in blocker_counts.items()],
        key=lambda x: -x["count"],
    )[:10]

    # Sort deadline buckets
    for bucket in ("d30", "d90", "d180", "beyond"):
        all_deadlines_items[bucket].sort(key=lambda x: x["days_remaining"])

    return {
        "org_id": org_id,
        "total_sites": len(all_sites),
        "kpis": kpis,
        "top_blockers": top_blockers,
        "deadlines": all_deadlines_items,
        "untrusted_sites": untrusted,
        "sites": sites_out,
    }


# ========================================
# V69: CEE Pipeline + M&V
# ========================================

from models.cee_models import WorkPackage, CeeDossier, CeeDossierEvidence
from models.enums import (
    WorkPackageSize,
    CeeDossierStep,
    CeeStatus,
    MVAlertType,
    ActionSourceType,
    ActionStatus,
)


# Required evidence pieces for a CEE dossier
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
    from models import ActionItem, Site

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

    import json

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
    import json
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
    from models import Site
    from models.energy_models import Meter, MeterReading
    from datetime import datetime, date, timedelta

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    baseline_kwh = site.annual_kwh_total or 0
    baseline_monthly = round(baseline_kwh / 12, 1) if baseline_kwh else 0

    # Source de verite : Meter/MeterReading (modele Yannick)
    current_kwh = 0
    months_covered = 0
    try:
        from sqlalchemy import func
        from models.enums import FrequencyType

        meter_ids = [
            m.id
            for m in db.query(Meter)
            .filter(Meter.site_id == site_id, Meter.is_active.is_(True), Meter.parent_meter_id.is_(None))
            .all()
        ]
        if meter_ids:
            y_ago = date.today() - timedelta(days=365)
            result = (
                db.query(func.sum(MeterReading.value_kwh))
                .filter(
                    MeterReading.meter_id.in_(meter_ids),
                    MeterReading.frequency == FrequencyType.MONTHLY,
                    MeterReading.timestamp >= y_ago,
                )
                .scalar()
            )
            current_kwh = float(result or 0)
            # Nombre de mois couverts
            months_covered = (
                db.query(func.count(func.distinct(func.strftime("%Y-%m", MeterReading.timestamp))))
                .filter(
                    MeterReading.meter_id.in_(meter_ids),
                    MeterReading.frequency == FrequencyType.MONTHLY,
                    MeterReading.timestamp >= y_ago,
                )
                .scalar()
            ) or 0
    except Exception:
        current_kwh = 0
        months_covered = 0

    current_monthly = round(current_kwh / max(1, months_covered), 1) if months_covered > 0 else 0

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
    import json

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


def _resolve_site_org(db: Session, site_id: int) -> int:
    """Resolve org_id from site_id."""
    from models import Portefeuille, EntiteJuridique

    row = (
        db.query(EntiteJuridique.organisation_id)
        .join(Portefeuille, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .join(Site, Site.portefeuille_id == Portefeuille.id)
        .filter(Site.id == site_id)
        .first()
    )
    return row[0] if row else 1  # Fallback to org 1 for demo



# ========================================
# Layer B: Database persistence
# ========================================


def _apply_snapshot(site: Site, snapshot: dict):
    """Apply a computed snapshot dict to a Site ORM object."""
    for key, value in snapshot.items():
        setattr(site, key, value)


def recompute_site(db: Session, site_id: int) -> dict:
    """Recompute and persist compliance snapshot for a single Site."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    obligations = db.query(Obligation).filter(Obligation.site_id == site_id).all()
    evidences = db.query(Evidence).filter(Evidence.site_id == site_id).all()
    snapshot = compute_site_snapshot(obligations, evidences)
    _apply_snapshot(site, snapshot)
    db.flush()
    return snapshot


def _bulk_recompute(db: Session, sites: List[Site]):
    """Recompute snapshots for a list of sites (3 queries total, no N+1)."""
    if not sites:
        return

    site_ids = [s.id for s in sites]

    all_obligations = db.query(Obligation).filter(Obligation.site_id.in_(site_ids)).all()
    all_evidences = db.query(Evidence).filter(Evidence.site_id.in_(site_ids)).all()

    obs_by_site = defaultdict(list)
    for ob in all_obligations:
        obs_by_site[ob.site_id].append(ob)

    evs_by_site = defaultdict(list)
    for ev in all_evidences:
        evs_by_site[ev.site_id].append(ev)

    for site in sites:
        snapshot = compute_site_snapshot(obs_by_site[site.id], evs_by_site[site.id])
        _apply_snapshot(site, snapshot)


def recompute_portfolio(db: Session, portefeuille_id: int) -> dict:
    """Recompute compliance for all sites in a portfolio."""
    portefeuille = db.query(Portefeuille).filter(Portefeuille.id == portefeuille_id).first()
    if not portefeuille:
        raise ValueError(f"Portefeuille {portefeuille_id} not found")

    sites = db.query(Site).filter(Site.portefeuille_id == portefeuille_id).all()

    _bulk_recompute(db, sites)
    db.commit()
    return {
        "portefeuille_id": portefeuille_id,
        "portefeuille_nom": portefeuille.nom,
        "sites_recomputed": len(sites),
    }


def recompute_organisation(db: Session, organisation_id: int) -> dict:
    """Recompute compliance for ALL sites in an organisation."""
    org = db.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not org:
        raise ValueError(f"Organisation {organisation_id} not found")

    portefeuille_ids = [
        row[0]
        for row in db.query(Portefeuille.id)
        .join(EntiteJuridique)
        .filter(EntiteJuridique.organisation_id == organisation_id)
        .all()
    ]

    sites = db.query(Site).filter(Site.portefeuille_id.in_(portefeuille_ids)).all()

    _bulk_recompute(db, sites)
    db.commit()
    return {
        "organisation_id": organisation_id,
        "organisation_nom": org.nom,
        "sites_recomputed": len(sites),
    }
