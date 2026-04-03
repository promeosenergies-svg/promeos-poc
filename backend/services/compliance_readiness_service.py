"""
PROMEOS — V68 Data Readiness Gate & Compliance Summaries

Extrait de compliance_engine.py.
Évalue la complétude des données site (readiness), l'applicabilité
des réglementations, les scores de risque, les échéances et la confiance données.
"""

from collections import defaultdict
from datetime import date
from typing import List, Optional

from sqlalchemy.orm import Session

from models import (
    Obligation,
    Site,
    Portefeuille,
    EntiteJuridique,
    Evidence,
    Batiment,
    ComplianceFinding,
    BillingInsight,
    StatutConformite,
    TypeEvidence,
    StatutEvidence,
    not_deleted,
)
from config.emission_factors import BASE_PENALTY_EURO, BACS_SEUIL_BAS
from services.compliance_utils import (
    worst_status,
    average_avancement,
    compute_bacs_statut,
    _worst_from_statuts,
    _ACTION_TEMPLATES,
)


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
    """Compute data readiness gate for a site."""
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
    """Compute which regulations apply to a site."""
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
            "applicable": None,
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
    """Compute risk/opportunity scores (V68 heuristic)."""
    nok_count = sum(1 for o in obligations if o.statut == StatutConformite.NON_CONFORME)
    a_risque_count = sum(1 for o in obligations if o.statut == StatutConformite.A_RISQUE)
    unknown_findings = sum(1 for f in findings if f.status == "UNKNOWN")
    nok_findings = sum(1 for f in findings if f.status == "NOK")

    compliance_risk_score = min(100, nok_count * 30 + a_risque_count * 15 + nok_findings * 10)
    compliance_score = 100 - compliance_risk_score
    evidence_risk = min(100, unknown_findings * 20 + a_risque_count * 10)
    financial_opportunity = round(BASE_PENALTY_EURO * nok_count + BASE_PENALTY_EURO * 0.5 * a_risque_count, 2)

    return {
        "reg_risk": compliance_risk_score,
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
    """Compute upcoming deadlines bucketed into 30/90/180 days."""
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
    """Compute data trust score based on shadow billing anomalies."""
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
        return {"trust_score": 100, "anomaly_count": 0, "reasons": ["billing_not_available"]}

    count = len(anomalies)
    critical = sum(1 for a in anomalies if a.severity == "critical")
    high = sum(1 for a in anomalies if a.severity == "high")

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


def compute_site_snapshot(
    obligations: List[Obligation],
    evidences: Optional[List[Evidence]] = None,
) -> dict:
    """
    Compute all Site snapshot fields from Obligations (+ Evidences for BACS).
    Pure function: does NOT mutate the obligation objects.
    """
    from models import TypeObligation

    decret = [o for o in obligations if o.type == TypeObligation.DECRET_TERTIAIRE]
    bacs = [o for o in obligations if o.type == TypeObligation.BACS]

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

    non_conforme_count = sum(1 for o in decret if o.statut == StatutConformite.NON_CONFORME) + sum(
        1 for s in bacs_resolved if s == StatutConformite.NON_CONFORME
    )
    a_risque_count = sum(1 for o in decret if o.statut == StatutConformite.A_RISQUE) + sum(
        1 for s in bacs_resolved if s == StatutConformite.A_RISQUE
    )

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


def compute_site_compliance_summary(
    db: Session,
    site_id: int,
    today: Optional[date] = None,
) -> dict:
    """V68: Full compliance summary for a single site."""
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
    """V68: Portfolio-level compliance summary."""
    site_ids = [
        row[0]
        for row in not_deleted(
            db.query(Site.id)
            .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
            .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
            .filter(EntiteJuridique.organisation_id == org_id),
            Site,
        ).all()
    ]

    if not site_ids:
        return {
            "org_id": org_id,
            "total_sites": 0,
            "sites": [],
            "kpis": {"data_blocked": 0, "data_warning": 0, "data_ready": 0},
            "top_blockers": [],
            "deadlines": {"d30": [], "d90": [], "d180": [], "beyond": []},
            "untrusted_sites": [],
        }

    all_batiments = db.query(Batiment).filter(Batiment.site_id.in_(site_ids)).all()
    all_evidences = db.query(Evidence).filter(Evidence.site_id.in_(site_ids)).all()
    all_obligations = db.query(Obligation).filter(Obligation.site_id.in_(site_ids)).all()
    all_findings = db.query(ComplianceFinding).filter(ComplianceFinding.site_id.in_(site_ids)).all()
    all_sites = db.query(Site).filter(Site.id.in_(site_ids)).all()

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
    kpis = {"data_blocked": 0, "data_warning": 0, "data_ready": 0}
    all_missing = []
    all_deadlines_items = {"d30": [], "d90": [], "d180": [], "beyond": []}
    untrusted = []

    for site in all_sites:
        readiness = compute_readiness(site, bats_by[site.id], evs_by[site.id])
        applicability = compute_applicability(site, bats_by[site.id])
        scores = compute_scores(obs_by[site.id], fnd_by[site.id])
        deadlines_data = compute_deadlines(obs_by[site.id], fnd_by[site.id], today)
        trust = compute_data_trust(site, db)

        gate = readiness["gate_status"]
        if gate == "BLOCKED":
            kpis["data_blocked"] += 1
        elif gate == "WARNING":
            kpis["data_warning"] += 1
        else:
            kpis["data_ready"] += 1

        for m in readiness["missing"]:
            if m["level"] == "blocking":
                all_missing.append({**m, "site_id": site.id, "site_nom": site.nom})

        for bucket in ("d30", "d90", "d180", "beyond"):
            for item in deadlines_data[bucket]:
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
