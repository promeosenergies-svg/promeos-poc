"""
PROMEOS - Smart Intake Engine (DIAMANT)
Question bank, generator, prefill, before/after diff, PDF extractor.
Deterministe: la conformite vient des regles YAML, jamais de l'IA.
"""
import json
import re
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    Site, Batiment, Evidence, Portefeuille, EntiteJuridique,
    TypeEvidence, StatutEvidence, ParkingType, OperatStatus,
    IntakeFieldOverride,
)
from services.compliance_rules import (
    _eval_decret_tertiaire, _eval_bacs, _eval_aper,
)
from services.onboarding_service import is_tertiaire, estimate_cvc_power


# ========================================
# Severity ordering for question sorting
# ========================================

_SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}

MAX_QUESTIONS = 8


# ========================================
# Question Bank — 13 field definitions
# ========================================

QUESTION_BANK = [
    {
        "field_path": "site.tertiaire_area_m2",
        "question": "Quelle est la surface tertiaire assujettie (m2) ?",
        "help": "Surface soumise au decret tertiaire. >= 1000 m2 = assujetti.",
        "input_type": "number",
        "unit": "m2",
        "options": None,
        "regulations": ["decret_tertiaire_operat"],
        "blocking_rules": ["DT_SCOPE"],
        "severity": "high",
        "prefill_from": "site.surface_m2",
        "model": "site",
        "column": "tertiaire_area_m2",
    },
    {
        "field_path": "site.operat_status",
        "question": "Avez-vous declare vos consommations sur OPERAT ?",
        "help": "Plateforme ADEME pour la declaration des consommations energetiques.",
        "input_type": "select",
        "unit": None,
        "options": [
            {"value": "not_started", "label": "Non demarree"},
            {"value": "in_progress", "label": "En cours"},
            {"value": "submitted", "label": "Soumis"},
            {"value": "verified", "label": "Verifie"},
        ],
        "regulations": ["decret_tertiaire_operat"],
        "blocking_rules": ["DT_OPERAT"],
        "severity": "critical",
        "prefill_from": None,
        "model": "site",
        "column": "operat_status",
    },
    {
        "field_path": "site.annual_kwh_total",
        "question": "Quelle est la consommation energetique annuelle totale (kWh) ?",
        "help": "Somme des consommations electricite + gaz + autres sur 12 mois.",
        "input_type": "number",
        "unit": "kWh/an",
        "options": None,
        "regulations": ["decret_tertiaire_operat"],
        "blocking_rules": ["DT_ENERGY_DATA"],
        "severity": "medium",
        "prefill_from": None,
        "model": "site",
        "column": "annual_kwh_total",
    },
    {
        "field_path": "batiment.cvc_power_kw",
        "question": "Quelle est la puissance CVC nominale (kW) ?",
        "help": "Puissance des systemes de chauffage, ventilation et climatisation. > 70 kW = assujetti BACS.",
        "input_type": "number",
        "unit": "kW",
        "options": None,
        "regulations": ["bacs"],
        "blocking_rules": ["BACS_POWER"],
        "severity": "high",
        "prefill_from": "estimate_cvc",
        "model": "batiment",
        "column": "cvc_power_kw",
    },
    {
        "field_path": "site.parking_area_m2",
        "question": "Quelle est la surface du parking (m2) ?",
        "help": "Surface totale du parking. >= 1500 m2 = obligation de solarisation (loi APER).",
        "input_type": "number",
        "unit": "m2",
        "options": None,
        "regulations": ["aper"],
        "blocking_rules": ["APER_PARKING"],
        "severity": "high",
        "prefill_from": None,
        "model": "site",
        "column": "parking_area_m2",
    },
    {
        "field_path": "site.roof_area_m2",
        "question": "Quelle est la surface de toiture (m2) ?",
        "help": "Surface de toiture exploitable. >= 500 m2 = obligation ENR.",
        "input_type": "number",
        "unit": "m2",
        "options": None,
        "regulations": ["aper"],
        "blocking_rules": ["APER_TOITURE"],
        "severity": "medium",
        "prefill_from": None,
        "model": "site",
        "column": "roof_area_m2",
    },
    {
        "field_path": "site.parking_type",
        "question": "Quel est le type de parking ?",
        "help": "Parking exterieur = ombieres possibles. Couvert/souterrain = derogation possible.",
        "input_type": "select",
        "unit": None,
        "options": [
            {"value": "outdoor", "label": "Exterieur"},
            {"value": "indoor", "label": "Couvert"},
            {"value": "underground", "label": "Souterrain"},
            {"value": "silo", "label": "Silo"},
        ],
        "regulations": ["aper"],
        "blocking_rules": ["APER_PARKING_TYPE"],
        "severity": "low",
        "prefill_from": None,
        "model": "site",
        "column": "parking_type",
    },
    {
        "field_path": "evidence.attestation_bacs",
        "question": "Disposez-vous d'une attestation BACS valide ?",
        "help": "Attestation de conformite du systeme GTB/GTC (classe B minimum).",
        "input_type": "boolean",
        "unit": None,
        "options": None,
        "regulations": ["bacs"],
        "blocking_rules": ["BACS_ATTESTATION"],
        "severity": "high",
        "prefill_from": None,
        "model": "evidence",
        "column": "ATTESTATION_BACS",
    },
    {
        "field_path": "evidence.derogation_bacs",
        "question": "Beneficiez-vous d'une derogation BACS ?",
        "help": "Derogation accordee (ex: demolition prevue, bail < 6 ans).",
        "input_type": "boolean",
        "unit": None,
        "options": None,
        "regulations": ["bacs"],
        "blocking_rules": ["BACS_DEROGATION"],
        "severity": "low",
        "prefill_from": None,
        "model": "evidence",
        "column": "DEROGATION_BACS",
    },
    {
        "field_path": "site.bacs_systems_present",
        "question": "Avez-vous des systemes CVC automatises (GTB/GTC) a piloter ?",
        "help": "Systemes de chauffage, climatisation ou ventilation avec automates.",
        "input_type": "select",
        "unit": None,
        "options": [
            {"value": "yes", "label": "Oui"},
            {"value": "no", "label": "Non"},
            {"value": "unknown", "label": "Je ne sais pas"},
        ],
        "regulations": ["bacs"],
        "blocking_rules": ["BACS_POWER"],
        "severity": "high",
        "prefill_from": None,
        "model": "meta",
        "column": "bacs_systems_present",
    },
    {
        "field_path": "site.bacs_scope_basis",
        "question": "Quel est le type principal des systemes CVC ?",
        "help": "Chauffage, climatisation, ventilation ou combine.",
        "input_type": "select",
        "unit": None,
        "options": [
            {"value": "heating", "label": "Chauffage"},
            {"value": "cooling", "label": "Climatisation"},
            {"value": "ventilation", "label": "Ventilation"},
            {"value": "combined", "label": "Combine"},
        ],
        "regulations": ["bacs"],
        "blocking_rules": [],
        "severity": "medium",
        "prefill_from": None,
        "model": "meta",
        "column": "bacs_scope_basis",
    },
    {
        "field_path": "site.surface_m2",
        "question": "Quelle est la surface totale du site (m2) ?",
        "help": "Surface brute totale du site.",
        "input_type": "number",
        "unit": "m2",
        "options": None,
        "regulations": [],
        "blocking_rules": [],
        "severity": "medium",
        "prefill_from": None,
        "model": "site",
        "column": "surface_m2",
    },
    {
        "field_path": "site.naf_code",
        "question": "Quel est le code NAF du site ?",
        "help": "Code NAF (nomenclature INSEE) pour la classification de l'activite.",
        "input_type": "text",
        "unit": None,
        "options": None,
        "regulations": [],
        "blocking_rules": [],
        "severity": "low",
        "prefill_from": None,
        "model": "site",
        "column": "naf_code",
    },
    {
        "field_path": "site.is_multi_occupied",
        "question": "Le site est-il multi-occupant ?",
        "help": "Plusieurs locataires ou entites occupent le meme batiment.",
        "input_type": "boolean",
        "unit": None,
        "options": None,
        "regulations": ["decret_tertiaire_operat"],
        "blocking_rules": [],
        "severity": "low",
        "prefill_from": None,
        "model": "site",
        "column": "is_multi_occupied",
    },
    {
        "field_path": "site.nombre_employes",
        "question": "Combien d'employes sur ce site ?",
        "help": "Nombre d'employes equivalents temps plein.",
        "input_type": "number",
        "unit": None,
        "options": None,
        "regulations": [],
        "blocking_rules": [],
        "severity": "info",
        "prefill_from": None,
        "model": "site",
        "column": "nombre_employes",
    },
]


# ========================================
# Question Generator
# ========================================

def _get_current_value(site: Site, batiments: list, evidences: list, q: dict):
    """Get the current value for a question's field_path."""
    fp = q["field_path"]

    # meta questions: informational — "answered" if site already has CVC data
    if q.get("model") == "meta":
        if q["column"] in ("bacs_systems_present", "bacs_scope_basis"):
            max_cvc = max((b.cvc_power_kw or 0 for b in batiments), default=0)
            return "answered" if max_cvc > 0 else None
        return None

    if fp.startswith("site."):
        col = fp.split(".", 1)[1]
        val = getattr(site, col, None)
        # Convert enums to string
        if val is not None and hasattr(val, "value"):
            val = val.value
        return val

    if fp == "batiment.cvc_power_kw":
        if batiments:
            return max((b.cvc_power_kw or 0 for b in batiments), default=None)
        return None

    if fp == "evidence.attestation_bacs":
        return any(
            e.type == TypeEvidence.ATTESTATION_BACS and e.statut == StatutEvidence.VALIDE
            for e in evidences
        )

    if fp == "evidence.derogation_bacs":
        return any(
            e.type == TypeEvidence.DEROGATION_BACS and e.statut == StatutEvidence.VALIDE
            for e in evidences
        )

    return None


def _is_field_missing(current_value, q: dict) -> bool:
    """Check if a field is considered missing/null."""
    if q["input_type"] == "boolean":
        # Booleans are never "missing" — False is a valid answer
        # But evidence booleans default to False, meaning "no evidence"
        if q["field_path"].startswith("evidence."):
            return current_value is False or current_value is None
        return current_value is None
    return current_value is None or current_value == 0


def generate_questions(db: Session, site_id: int) -> list:
    """Generate questions for a site based on missing regulatory fields.

    Returns: list of question dicts with current_value and prefill_value added.
    Sorted by severity (blocking first: critical > high > medium > low > info).
    Capped at MAX_QUESTIONS (8).
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return []

    batiments = db.query(Batiment).filter(Batiment.site_id == site_id).all()
    evidences = db.query(Evidence).filter(Evidence.site_id == site_id).all()
    prefills = prefill_from_existing(db, site_id)
    overrides = resolve_overrides(db, site_id)

    questions = []
    for q in QUESTION_BANK:
        current = _get_current_value(site, batiments, evidences, q)
        if not _is_field_missing(current, q):
            continue

        # Build output question
        out = {
            "field_path": q["field_path"],
            "question": q["question"],
            "help": q["help"],
            "input_type": q["input_type"],
            "unit": q["unit"],
            "options": q["options"],
            "regulations": q["regulations"],
            "blocking_rules": q["blocking_rules"],
            "severity": q["severity"],
            "current_value": current,
            "prefill_value": prefills.get(q["field_path"]),
            "override": overrides.get(q["field_path"]),
        }
        questions.append(out)

    # Sort by severity descending
    questions.sort(key=lambda q: _SEVERITY_ORDER.get(q["severity"], 0), reverse=True)

    return questions[:MAX_QUESTIONS]


# ========================================
# Prefill from existing data
# ========================================

def prefill_from_existing(db: Session, site_id: int) -> dict:
    """Auto-suggest values from existing data.

    Returns: {field_path: suggested_value}
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return {}

    prefills = {}

    # surface_m2 → tertiaire_area_m2 (if tertiaire site type)
    if site.surface_m2 and site.tertiaire_area_m2 is None and is_tertiaire(site.type):
        prefills["site.tertiaire_area_m2"] = site.surface_m2

    # surface_m2 + type → estimate cvc_power_kw
    if site.surface_m2 and site.type:
        batiment = db.query(Batiment).filter(Batiment.site_id == site_id).first()
        if not batiment or not batiment.cvc_power_kw:
            estimated = estimate_cvc_power(site.type, site.surface_m2)
            prefills["batiment.cvc_power_kw"] = estimated

    return prefills


# ========================================
# Multi-scope override resolution
# ========================================

def resolve_overrides(db: Session, site_id: int) -> dict:
    """Resolve inherited overrides: SITE > ENTITY > ORG.

    Returns: {field_path: {"value": ..., "scope_type": ..., "scope_id": ...}}
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return {}

    # Walk hierarchy: site → portefeuille → entite → org
    scopes = [("site", site_id)]
    if site.portefeuille_id:
        portefeuille = db.query(Portefeuille).filter(
            Portefeuille.id == site.portefeuille_id
        ).first()
        if portefeuille:
            scopes.append(("entity", portefeuille.entite_juridique_id))
            entite = db.query(EntiteJuridique).filter(
                EntiteJuridique.id == portefeuille.entite_juridique_id
            ).first()
            if entite:
                scopes.append(("org", entite.organisation_id))

    # Collect overrides at each level (most specific first)
    result = {}
    for scope_type, scope_id in scopes:
        overrides = db.query(IntakeFieldOverride).filter(
            IntakeFieldOverride.scope_type == scope_type,
            IntakeFieldOverride.scope_id == scope_id,
        ).all()
        for ov in overrides:
            if ov.field_path not in result:  # First match wins (site > entity > org)
                result[ov.field_path] = {
                    "value": json.loads(ov.value_json),
                    "scope_type": ov.scope_type,
                    "scope_id": ov.scope_id,
                }

    return result


# ========================================
# Before/After compliance simulation
# ========================================

def _build_site_context(db: Session, site_id: int) -> dict:
    """Build compliance evaluation context dict (same pattern as compliance_rules._get_site_context)."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return {}

    batiments = db.query(Batiment).filter(Batiment.site_id == site_id).all()
    evidences = db.query(Evidence).filter(Evidence.site_id == site_id).all()

    max_cvc = max((b.cvc_power_kw or 0 for b in batiments), default=0)

    has_bacs_attestation = any(
        e.type == TypeEvidence.ATTESTATION_BACS and e.statut == StatutEvidence.VALIDE
        for e in evidences
    )
    has_bacs_derogation = any(
        e.type == TypeEvidence.DEROGATION_BACS and e.statut == StatutEvidence.VALIDE
        for e in evidences
    )

    return {
        "tertiaire_area_m2": site.tertiaire_area_m2,
        "surface_m2": site.surface_m2,
        "operat_status": site.operat_status,
        "annual_kwh_total": site.annual_kwh_total,
        "avancement_pct": 0,  # computed from obligations, not directly set
        "cvc_power_kw": max_cvc,
        "has_bacs_attestation": has_bacs_attestation,
        "has_bacs_derogation": has_bacs_derogation,
        "parking_area_m2": site.parking_area_m2,
        "roof_area_m2": site.roof_area_m2,
        "parking_type": site.parking_type,
    }


def _apply_proposed_to_ctx(ctx: dict, proposed: dict) -> dict:
    """Apply proposed answers to context dict."""
    ctx = dict(ctx)  # shallow copy

    field_to_ctx = {
        "site.tertiaire_area_m2": "tertiaire_area_m2",
        "site.surface_m2": "surface_m2",
        "site.operat_status": "operat_status",
        "site.annual_kwh_total": "annual_kwh_total",
        "site.parking_area_m2": "parking_area_m2",
        "site.roof_area_m2": "roof_area_m2",
        "site.parking_type": "parking_type",
        "batiment.cvc_power_kw": "cvc_power_kw",
        "evidence.attestation_bacs": "has_bacs_attestation",
        "evidence.derogation_bacs": "has_bacs_derogation",
    }

    for field_path, value in proposed.items():
        ctx_key = field_to_ctx.get(field_path)
        if ctx_key:
            # Convert string enum values to enum objects where needed
            if ctx_key == "operat_status" and isinstance(value, str):
                try:
                    value = OperatStatus(value)
                except ValueError:
                    pass
            if ctx_key == "parking_type" and isinstance(value, str):
                try:
                    value = ParkingType(value)
                except ValueError:
                    pass
            ctx[ctx_key] = value

    return ctx


def _score_findings(findings: list) -> float:
    """Compute compliance score as percentage of OK/OUT_OF_SCOPE findings."""
    if not findings:
        return 0.0
    ok_count = sum(1 for f in findings if f.get("status") in ("OK", "OUT_OF_SCOPE"))
    return round(ok_count / len(findings) * 100, 1)


def _count_unknowns(findings: list) -> int:
    """Count UNKNOWN findings."""
    return sum(1 for f in findings if f.get("status") == "UNKNOWN")


def compute_before_after(db: Session, site_id: int, proposed: dict) -> dict:
    """Simulate compliance diff without writing to DB.

    Args:
        db: Database session
        site_id: Target site
        proposed: {field_path: value} — proposed answers

    Returns: {score_before, score_after, delta, unknowns_before, unknowns_after, unknowns_resolved}
    """
    ctx_before = _build_site_context(db, site_id)
    if not ctx_before:
        return {"score_before": 0, "score_after": 0, "delta": 0,
                "unknowns_before": 0, "unknowns_after": 0, "unknowns_resolved": 0}

    # Run evaluators on current state
    findings_before = []
    findings_before.extend(_eval_decret_tertiaire(ctx_before))
    findings_before.extend(_eval_bacs(ctx_before))
    findings_before.extend(_eval_aper(ctx_before))

    # Apply proposed answers and re-evaluate
    ctx_after = _apply_proposed_to_ctx(ctx_before, proposed)
    findings_after = []
    findings_after.extend(_eval_decret_tertiaire(ctx_after))
    findings_after.extend(_eval_bacs(ctx_after))
    findings_after.extend(_eval_aper(ctx_after))

    score_before = _score_findings(findings_before)
    score_after = _score_findings(findings_after)
    unknowns_before = _count_unknowns(findings_before)
    unknowns_after = _count_unknowns(findings_after)

    return {
        "score_before": score_before,
        "score_after": score_after,
        "delta": round(score_after - score_before, 1),
        "unknowns_before": unknowns_before,
        "unknowns_after": unknowns_after,
        "unknowns_resolved": unknowns_before - unknowns_after,
    }


# ========================================
# PDF text extraction (simple regex)
# ========================================

def extract_from_pdf_text(text: str) -> dict:
    """Extract field values from PDF text using regex patterns.

    Returns: {field_path: extracted_value}
    """
    if not text:
        return {}

    results = {}

    # Surface: "1 500 m2" or "1500m²"
    surface_match = re.search(r"(\d[\d\s]*)\s*m[2\u00b2]", text)
    if surface_match:
        surface_str = surface_match.group(1).replace(" ", "")
        try:
            results["site.surface_m2"] = float(surface_str)
        except ValueError:
            pass

    # SIRET: 14 consecutive digits
    siret_match = re.search(r"\b(\d{14})\b", text)
    if siret_match:
        results["site.siret"] = siret_match.group(1)

    # NAF code: "4711A" or "47.11A"
    naf_match = re.search(r"\b(\d{2}\.?\d{2}[A-Z])\b", text)
    if naf_match:
        results["site.naf_code"] = naf_match.group(1)

    # Puissance kW: "150 kW" or "150,5 kW"
    kw_match = re.search(r"(\d+[\.,]?\d*)\s*kW", text, re.IGNORECASE)
    if kw_match:
        kw_str = kw_match.group(1).replace(",", ".")
        try:
            results["batiment.cvc_power_kw"] = float(kw_str)
        except ValueError:
            pass

    # Consommation kWh: "125000 kWh"
    kwh_match = re.search(r"(\d[\d\s]*)\s*kWh", text, re.IGNORECASE)
    if kwh_match:
        kwh_str = kwh_match.group(1).replace(" ", "")
        try:
            results["site.annual_kwh_total"] = float(kwh_str)
        except ValueError:
            pass

    return results


# ========================================
# Demo autofill defaults
# ========================================

DEMO_DEFAULTS = {
    "site.tertiaire_area_m2": 2500.0,
    "site.operat_status": "submitted",
    "site.annual_kwh_total": 185000.0,
    "batiment.cvc_power_kw": 180.0,
    "site.parking_area_m2": 2000.0,
    "site.roof_area_m2": 800.0,
    "site.parking_type": "outdoor",
    "evidence.attestation_bacs": True,
    "evidence.derogation_bacs": False,
    "site.surface_m2": 3000.0,
    "site.is_multi_occupied": False,
    "site.nombre_employes": 120,
}
