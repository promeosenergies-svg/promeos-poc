"""
PROMEOS - Compliance Rules Evaluator
Charge les packs YAML et produit des ComplianceFinding persistants.
"""
import json
import os
from datetime import date
from typing import List, Optional

import yaml
from sqlalchemy.orm import Session

from models import (
    Site, Batiment, Obligation, Evidence, ComplianceFinding, Organisation,
    Portefeuille, EntiteJuridique,
    StatutConformite, TypeObligation, TypeEvidence, StatutEvidence,
    OperatStatus, ParkingType,
)

RULES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rules")


# ========================================
# YAML loading (cached)
# ========================================

_RULES_CACHE = {}


def _load_pack(filename: str) -> dict:
    if filename not in _RULES_CACHE:
        path = os.path.join(RULES_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            _RULES_CACHE[filename] = yaml.safe_load(f)
    return _RULES_CACHE[filename]


def load_all_packs() -> List[dict]:
    return [
        _load_pack("decret_tertiaire_operat_v1.yaml"),
        _load_pack("decret_bacs_v1.yaml"),
        _load_pack("loi_aper_v1.yaml"),
    ]


# ========================================
# Evaluation helpers
# ========================================

def _get_site_context(db: Session, site: Site) -> dict:
    """Build evaluation context dict from site + related data."""
    batiments = db.query(Batiment).filter(Batiment.site_id == site.id).all()
    evidences = db.query(Evidence).filter(Evidence.site_id == site.id).all()
    obligations = db.query(Obligation).filter(Obligation.site_id == site.id).all()

    max_cvc = max((b.cvc_power_kw or 0 for b in batiments), default=0)

    has_bacs_attestation = any(
        e.type == TypeEvidence.ATTESTATION_BACS and e.statut == StatutEvidence.VALIDE
        for e in evidences
    )
    has_bacs_derogation = any(
        e.type == TypeEvidence.DEROGATION_BACS and e.statut == StatutEvidence.VALIDE
        for e in evidences
    )

    decret_obls = [o for o in obligations if o.type == TypeObligation.DECRET_TERTIAIRE]
    avg_avancement = (
        sum(o.avancement_pct for o in decret_obls) / len(decret_obls)
        if decret_obls else 0
    )

    return {
        "tertiaire_area_m2": site.tertiaire_area_m2,
        "surface_m2": site.surface_m2,
        "operat_status": site.operat_status,
        "annual_kwh_total": site.annual_kwh_total,
        "avancement_pct": avg_avancement,
        "cvc_power_kw": max_cvc,
        "has_bacs_attestation": has_bacs_attestation,
        "has_bacs_derogation": has_bacs_derogation,
        "parking_area_m2": site.parking_area_m2,
        "roof_area_m2": site.roof_area_m2,
        "parking_type": site.parking_type,
    }


# ========================================
# Per-pack evaluators
# ========================================

def _eval_decret_tertiaire(ctx: dict) -> List[dict]:
    """Evaluate Decret Tertiaire rules."""
    pack = _load_pack("decret_tertiaire_operat_v1.yaml")
    findings = []

    for rule in pack["rules"]:
        rid = rule["id"]
        finding = {"rule_id": rid, "regulation": pack["regulation"]}

        if rid == "DT_SCOPE":
            area = ctx.get("tertiaire_area_m2")
            if area is None:
                finding.update(status="UNKNOWN", severity=rule["severity"],
                               evidence=rule.get("when_unknown", ""))
            elif area < 1000:
                finding.update(status="OUT_OF_SCOPE",
                               evidence=rule.get("when_out_of_scope", ""))
                findings.append(finding)
                return findings  # Out of scope → skip remaining rules
            else:
                finding.update(status="OK",
                               evidence=f"Surface tertiaire {area} m2 >= 1000 m2")

        elif rid == "DT_OPERAT":
            status = ctx.get("operat_status")
            if status in (OperatStatus.SUBMITTED, OperatStatus.VERIFIED):
                finding.update(status="OK", evidence=f"OPERAT: {status.value}")
            else:
                finding.update(
                    status="NOK", severity=rule["severity"],
                    deadline=rule.get("deadline"),
                    evidence=rule.get("when_nok", ""),
                    action=rule.get("action"),
                )

        elif rid == "DT_TRAJECTORY_2030":
            pct = ctx.get("avancement_pct", 0)
            if pct >= 40:
                finding.update(status="OK",
                               evidence=f"Avancement {pct}% >= 40%")
            else:
                finding.update(
                    status="NOK", severity=rule["severity"],
                    deadline=rule.get("deadline"),
                    evidence=f"Avancement {pct}% < 40% — {rule.get('when_nok', '')}",
                    action=rule.get("action"),
                )

        elif rid == "DT_TRAJECTORY_2040":
            pct = ctx.get("avancement_pct", 0)
            if pct >= 50:
                finding.update(status="OK",
                               evidence=f"Avancement {pct}% >= 50%")
            else:
                finding.update(
                    status="NOK", severity=rule["severity"],
                    deadline=rule.get("deadline"),
                    evidence=f"Avancement {pct}% < 50% — {rule.get('when_nok', '')}",
                    action=rule.get("action"),
                )

        elif rid == "DT_ENERGY_DATA":
            kwh = ctx.get("annual_kwh_total")
            if kwh is not None:
                finding.update(status="OK",
                               evidence=f"Consommation: {kwh} kWh/an")
            else:
                finding.update(
                    status="UNKNOWN", severity=rule["severity"],
                    evidence=rule.get("when_nok", ""),
                    action=rule.get("action"),
                )

        findings.append(finding)

    return findings


def _eval_bacs(ctx: dict) -> List[dict]:
    """Evaluate BACS rules."""
    pack = _load_pack("decret_bacs_v1.yaml")
    findings = []

    cvc = ctx.get("cvc_power_kw", 0)
    has_att = ctx.get("has_bacs_attestation", False)
    has_derog = ctx.get("has_bacs_derogation", False)

    for rule in pack["rules"]:
        rid = rule["id"]
        finding = {"rule_id": rid, "regulation": pack["regulation"]}

        if rid == "BACS_POWER":
            if cvc is None or cvc == 0:
                finding.update(status="UNKNOWN", severity=rule["severity"],
                               evidence=rule.get("when_unknown", ""))
            elif cvc <= 70:
                finding.update(status="OUT_OF_SCOPE",
                               evidence=rule.get("when_out_of_scope", ""))
                findings.append(finding)
                return findings  # Out of scope
            else:
                finding.update(status="OK",
                               evidence=f"CVC {cvc} kW > 70 kW — assujetti BACS")

        elif rid == "BACS_DEROGATION":
            if has_derog:
                finding.update(status="OK",
                               evidence=rule.get("when_ok", "Derogation BACS accordee"))
            else:
                finding.update(status="OK",
                               evidence="Pas de derogation — evaluation standard")

        elif rid == "BACS_HIGH_DEADLINE":
            if cvc <= 290:
                finding.update(status="OK", evidence="CVC <= 290 kW — non concerne seuil haut")
            elif has_att or has_derog:
                finding.update(status="OK", evidence="Attestation ou derogation BACS presente")
            else:
                finding.update(
                    status="NOK", severity=rule["severity"],
                    deadline=rule.get("deadline"),
                    evidence=rule.get("when_nok", ""),
                    action=rule.get("action"),
                )

        elif rid == "BACS_LOW_DEADLINE":
            if cvc > 290 or cvc <= 70:
                finding.update(status="OK", evidence="Non concerne seuil 70-290 kW")
            elif has_att or has_derog:
                finding.update(status="OK", evidence="Attestation ou derogation BACS presente")
            else:
                finding.update(
                    status="NOK", severity=rule["severity"],
                    deadline=rule.get("deadline"),
                    evidence=rule.get("when_nok", ""),
                    action=rule.get("action"),
                )

        elif rid == "BACS_ATTESTATION":
            if has_att:
                finding.update(status="OK", evidence="Attestation BACS valide")
            elif has_derog:
                finding.update(status="OK", evidence="Derogation BACS (attestation non requise)")
            else:
                finding.update(
                    status="NOK", severity=rule["severity"],
                    evidence=rule.get("when_nok", ""),
                    action=rule.get("action"),
                )

        findings.append(finding)

    return findings


def _eval_aper(ctx: dict) -> List[dict]:
    """Evaluate Loi APER rules."""
    pack = _load_pack("loi_aper_v1.yaml")
    findings = []

    for rule in pack["rules"]:
        rid = rule["id"]
        finding = {"rule_id": rid, "regulation": pack["regulation"]}

        if rid == "APER_PARKING":
            area = ctx.get("parking_area_m2")
            if area is None:
                finding.update(status="UNKNOWN", severity=rule["severity"],
                               evidence=rule.get("when_unknown", ""))
            elif area < 1500:
                finding.update(status="OUT_OF_SCOPE",
                               evidence=rule.get("when_out_of_scope", ""))
            else:
                # Parking >= 1500 without ENR = NOK
                finding.update(
                    status="NOK", severity=rule["severity"],
                    deadline=rule.get("deadline"),
                    evidence=rule.get("when_nok", ""),
                    action=rule.get("action"),
                )

        elif rid == "APER_TOITURE":
            area = ctx.get("roof_area_m2")
            if area is None:
                finding.update(status="UNKNOWN", severity=rule["severity"],
                               evidence=rule.get("when_unknown", ""))
            elif area < 500:
                finding.update(status="OUT_OF_SCOPE",
                               evidence=rule.get("when_out_of_scope", ""))
            else:
                finding.update(
                    status="NOK", severity=rule["severity"],
                    evidence=rule.get("when_nok", ""),
                    action=rule.get("action"),
                )

        elif rid == "APER_PARKING_TYPE":
            ptype = ctx.get("parking_type")
            if ptype is None:
                finding.update(status="UNKNOWN", evidence="Type de parking non renseigne")
            elif ptype == ParkingType.OUTDOOR:
                finding.update(status="OK", evidence="Parking exterieur — ombieres possibles")
            else:
                finding.update(
                    status="NOK", severity=rule["severity"],
                    evidence=rule.get("when_nok", ""),
                    action=rule.get("action"),
                )

        findings.append(finding)

    return findings


# ========================================
# Main evaluation + persistence
# ========================================

_SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def evaluate_site(db: Session, site_id: int) -> List[ComplianceFinding]:
    """Evaluate all rules for a site and persist ComplianceFinding rows.

    Returns the list of created ComplianceFinding objects.
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return []

    ctx = _get_site_context(db, site)

    # Run all 3 packs
    raw_findings = []
    raw_findings.extend(_eval_decret_tertiaire(ctx))
    raw_findings.extend(_eval_bacs(ctx))
    raw_findings.extend(_eval_aper(ctx))

    # Delete existing findings for this site (replace strategy)
    db.query(ComplianceFinding).filter(ComplianceFinding.site_id == site_id).delete()
    db.flush()  # Flush delete before re-insert to avoid identity map conflicts

    # Persist new findings
    result = []
    for f in raw_findings:
        actions = [f["action"]] if f.get("action") else []
        deadline = None
        if f.get("deadline"):
            if isinstance(f["deadline"], str):
                deadline = date.fromisoformat(f["deadline"])
            else:
                deadline = f["deadline"]

        cf = ComplianceFinding(
            site_id=site_id,
            regulation=f["regulation"],
            rule_id=f["rule_id"],
            status=f.get("status", "UNKNOWN"),
            severity=f.get("severity"),
            deadline=deadline,
            evidence=f.get("evidence", ""),
            recommended_actions_json=json.dumps(actions, ensure_ascii=False) if actions else None,
        )
        db.add(cf)
        result.append(cf)

    db.flush()
    return result


def evaluate_organisation(db: Session, org_id: int) -> dict:
    """Evaluate all sites for an organisation.

    Returns summary: {sites_evaluated, total_findings, nok_count, unknown_count}.
    """
    # Get all site IDs for the org
    site_ids = [
        row[0] for row in
        db.query(Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    ]

    total_findings = 0
    nok_count = 0
    unknown_count = 0

    for sid in site_ids:
        findings = evaluate_site(db, sid)
        total_findings += len(findings)
        nok_count += sum(1 for f in findings if f.status == "NOK")
        unknown_count += sum(1 for f in findings if f.status == "UNKNOWN")

    db.commit()

    return {
        "organisation_id": org_id,
        "sites_evaluated": len(site_ids),
        "total_findings": total_findings,
        "nok_count": nok_count,
        "unknown_count": unknown_count,
    }


def get_summary(db: Session, org_id: int) -> dict:
    """Aggregate compliance findings for an org into a summary."""
    site_ids = [
        row[0] for row in
        db.query(Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    ]

    if not site_ids:
        return {
            "total_sites": 0,
            "sites_ok": 0,
            "sites_nok": 0,
            "sites_unknown": 0,
            "pct_ok": 0,
            "findings_by_regulation": {},
            "top_actions": [],
        }

    all_findings = (
        db.query(ComplianceFinding)
        .filter(ComplianceFinding.site_id.in_(site_ids))
        .all()
    )

    # Per-site worst status
    site_worst = {}
    for f in all_findings:
        if f.status in ("OUT_OF_SCOPE", "OK"):
            continue
        current = site_worst.get(f.site_id, "OK")
        if f.status == "NOK" or (f.status == "UNKNOWN" and current == "OK"):
            site_worst[f.site_id] = f.status

    sites_nok = sum(1 for v in site_worst.values() if v == "NOK")
    sites_unknown = sum(1 for v in site_worst.values() if v == "UNKNOWN")
    sites_ok = len(site_ids) - sites_nok - sites_unknown

    # By regulation
    by_reg = {}
    for f in all_findings:
        reg = f.regulation
        if reg not in by_reg:
            by_reg[reg] = {"ok": 0, "nok": 0, "unknown": 0, "out_of_scope": 0}
        if f.status == "OK":
            by_reg[reg]["ok"] += 1
        elif f.status == "NOK":
            by_reg[reg]["nok"] += 1
        elif f.status == "UNKNOWN":
            by_reg[reg]["unknown"] += 1
        elif f.status == "OUT_OF_SCOPE":
            by_reg[reg]["out_of_scope"] += 1

    # Top actions (NOK findings sorted by severity)
    nok_findings = [f for f in all_findings if f.status == "NOK" and f.recommended_actions_json]
    nok_findings.sort(key=lambda f: _SEVERITY_ORDER.get(f.severity, 0), reverse=True)

    top_actions = []
    seen_rules = set()
    for f in nok_findings:
        if f.rule_id in seen_rules:
            continue
        seen_rules.add(f.rule_id)
        actions = json.loads(f.recommended_actions_json) if f.recommended_actions_json else []
        if actions:
            top_actions.append({
                "regulation": f.regulation,
                "rule_id": f.rule_id,
                "severity": f.severity,
                "deadline": f.deadline.isoformat() if f.deadline else None,
                "action": actions[0],
                "nb_sites": sum(1 for ff in nok_findings if ff.rule_id == f.rule_id),
            })
        if len(top_actions) >= 5:
            break

    return {
        "total_sites": len(site_ids),
        "sites_ok": sites_ok,
        "sites_nok": sites_nok,
        "sites_unknown": sites_unknown,
        "pct_ok": round(sites_ok / len(site_ids) * 100) if site_ids else 0,
        "findings_by_regulation": by_reg,
        "top_actions": top_actions,
    }


def get_sites_findings(db: Session, org_id: int, regulation: str = None,
                       status: str = None, severity: str = None) -> List[dict]:
    """Return per-site findings list with filters."""
    site_ids = [
        row[0] for row in
        db.query(Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    ]

    if not site_ids:
        return []

    q = db.query(ComplianceFinding).filter(ComplianceFinding.site_id.in_(site_ids))
    if regulation:
        q = q.filter(ComplianceFinding.regulation == regulation)
    if status:
        q = q.filter(ComplianceFinding.status == status)
    if severity:
        q = q.filter(ComplianceFinding.severity == severity)

    findings = q.all()

    # Group by site
    sites_map = {}
    for f in findings:
        if f.site_id not in sites_map:
            site = db.query(Site).filter(Site.id == f.site_id).first()
            sites_map[f.site_id] = {
                "site_id": f.site_id,
                "site_nom": site.nom if site else "?",
                "site_type": site.type.value if site else "?",
                "findings": [],
            }
        actions = json.loads(f.recommended_actions_json) if f.recommended_actions_json else []
        sites_map[f.site_id]["findings"].append({
            "id": f.id,
            "regulation": f.regulation,
            "rule_id": f.rule_id,
            "status": f.status,
            "severity": f.severity,
            "deadline": f.deadline.isoformat() if f.deadline else None,
            "evidence": f.evidence,
            "actions": actions,
        })

    return list(sites_map.values())
