"""
PROMEOS - Patrimoine Service (DIAMANT)
Staging pipeline: import → quality gate → corrections → activation.
"""

import io
import csv
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from sqlalchemy.exc import SQLAlchemyError

from models import (
    StagingBatch,
    StagingSite,
    StagingCompteur,
    QualityFinding,
    StagingStatus,
    ImportSourceType,
    QualityRuleSeverity,
    Site,
    Compteur,
    TypeCompteur,
    EnergyVector,
    ActivationLog,
    ActivationLogStatus,
    DeliveryPoint,
    DeliveryPointEnergyType,
    EntiteJuridique,
    Portefeuille,
    Batiment,
    not_deleted,
)
from services.onboarding_service import create_site_from_data, provision_site
from services.quality_rules import run_all_rules
from services.import_mapping import normalize_header, normalize_type_site, normalize_type_compteur


# ========================================
# Batch lifecycle
# ========================================


def create_staging_batch(
    db: Session,
    org_id: Optional[int],
    user_id: Optional[int],
    source_type: ImportSourceType,
    mode: str,
    filename: Optional[str] = None,
    content_hash: Optional[str] = None,
) -> StagingBatch:
    """Create a new staging batch."""
    batch = StagingBatch(
        org_id=org_id,
        user_id=user_id,
        status=StagingStatus.DRAFT,
        source_type=source_type,
        mode=mode,
        filename=filename,
        content_hash=content_hash,
    )
    db.add(batch)
    db.flush()
    return batch


# ========================================
# CSV Import
# ========================================

_CSV_COLUMNS = [
    "nom",
    "adresse",
    "code_postal",
    "ville",
    "surface_m2",
    "type",
    "naf_code",
    "siren",
    "siret",
    "energy_type",
    "delivery_code",
    "numero_serie",
    "meter_id",
    "type_compteur",
    "puissance_kw",
]


def import_csv_to_staging(db: Session, batch_id: int, file_content: bytes) -> dict:
    """Parse CSV, create StagingSite + StagingCompteur rows in staging.

    Returns: {sites_count, compteurs_count, parse_errors}
    """
    batch = db.get(StagingBatch, batch_id)
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    text = file_content.decode("utf-8-sig")

    # Auto-detect delimiter
    first_line = text.split("\n")[0]
    delimiter = ";" if ";" in first_line else ","

    # Normalize headers via import_mapping (FR/EN synonyms)
    raw_reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    raw_headers = next(raw_reader, [])
    canonical_headers = []
    for h in raw_headers:
        mapped = normalize_header(h)
        canonical_headers.append(mapped if mapped else h.strip().lower())

    reader = csv.DictReader(
        io.StringIO(text),
        delimiter=delimiter,
        fieldnames=canonical_headers,
    )
    next(reader)  # skip original header row

    sites_created = 0
    compteurs_created = 0
    parse_errors = []

    # Track staging sites by name for compteur linking
    site_map = {}

    for row_num, row in enumerate(reader, start=2):
        try:
            nom = (row.get("nom") or "").strip()
            if not nom:
                parse_errors.append({"row": row_num, "error": "Champ 'nom' manquant ou vide"})
                continue

            # Create or reuse staging site
            if nom not in site_map:
                surface_raw = (row.get("surface_m2") or "").strip()
                surface = float(surface_raw) if surface_raw else None

                # SIRET: accept both "siret" and "siren" columns
                siret_val = (row.get("siret") or "").strip() or None

                # Multi-entité / bâtiment columns (Step 20)
                siren_entite_val = (row.get("siren_entite") or "").strip() or None
                nom_entite_val = (row.get("nom_entite") or "").strip() or None
                portefeuille_val = (row.get("portefeuille") or "").strip() or None
                batiment_nom_val = (row.get("batiment_nom") or "").strip() or None
                bat_surface_raw = (row.get("batiment_surface_m2") or "").strip()
                bat_surface = float(bat_surface_raw) if bat_surface_raw else None
                bat_annee_raw = (row.get("batiment_annee_construction") or "").strip()
                bat_annee = int(bat_annee_raw) if bat_annee_raw else None
                bat_cvc_raw = (row.get("batiment_cvc_power_kw") or "").strip()
                bat_cvc = float(bat_cvc_raw) if bat_cvc_raw else None

                ss = StagingSite(
                    batch_id=batch_id,
                    row_number=row_num,
                    nom=nom,
                    type_site=normalize_type_site((row.get("type") or "").strip())
                    or (row.get("type") or "").strip()
                    or None,
                    adresse=(row.get("adresse") or "").strip() or None,
                    code_postal=(row.get("code_postal") or "").strip() or None,
                    ville=(row.get("ville") or "").strip() or None,
                    surface_m2=surface,
                    siret=siret_val,
                    naf_code=(row.get("naf_code") or "").strip() or None,
                    source_type=batch.source_type.value if batch.source_type else None,
                    source_ref=batch.filename,
                    # Step 20: multi-entité / bâtiment
                    siren_entite=siren_entite_val,
                    nom_entite=nom_entite_val,
                    portefeuille_nom=portefeuille_val,
                    batiment_nom=batiment_nom_val,
                    batiment_surface_m2=bat_surface,
                    batiment_annee_construction=bat_annee,
                    batiment_cvc_power_kw=bat_cvc,
                )
                db.add(ss)
                db.flush()
                site_map[nom] = ss
                sites_created += 1

            # Create staging compteur if meter data present
            numero_serie = (row.get("numero_serie") or "").strip()
            # Support both "meter_id" and "delivery_code" columns
            meter_id = (row.get("meter_id") or row.get("delivery_code") or "").strip()
            type_compteur = (row.get("type_compteur") or "").strip() or None
            # Infer type_compteur from energy_type if missing
            energy_type = (row.get("energy_type") or "").strip()
            if not type_compteur and energy_type:
                et = energy_type.lower()
                if any(k in et for k in ("elec", "prm", "pdl")):
                    type_compteur = "electricite"
                elif any(k in et for k in ("gaz", "gas", "pce")):
                    type_compteur = "gaz"

            if numero_serie or meter_id:
                puissance_raw = (row.get("puissance_kw") or "").strip()
                puissance = float(puissance_raw) if puissance_raw else None

                sc = StagingCompteur(
                    batch_id=batch_id,
                    staging_site_id=site_map[nom].id,
                    row_number=row_num,
                    numero_serie=numero_serie or None,
                    meter_id=meter_id or None,
                    type_compteur=normalize_type_compteur(type_compteur) if type_compteur else None,
                    puissance_kw=puissance,
                )
                db.add(sc)
                compteurs_created += 1

        except Exception as e:
            parse_errors.append({"row": row_num, "error": str(e)})

    db.flush()

    # Update batch stats
    batch.stats_json = json.dumps(
        {
            "sites_count": sites_created,
            "compteurs_count": compteurs_created,
            "parse_errors": len(parse_errors),
        }
    )

    return {
        "sites_count": sites_created,
        "compteurs_count": compteurs_created,
        "parse_errors": parse_errors,
    }


# ========================================
# Invoice-based import
# ========================================


def import_invoices_to_staging(db: Session, batch_id: int, metadata: dict) -> dict:
    """Extract site/meter info from invoice metadata into staging.

    metadata format: {"invoices": [{"site_name": ..., "meter_id": ..., "address": ..., ...}]}
    Returns: {sites_detected, compteurs_detected}
    """
    batch = db.get(StagingBatch, batch_id)
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    invoices = metadata.get("invoices", [])
    site_map = {}
    compteurs_detected = 0

    for idx, inv in enumerate(invoices, start=1):
        site_name = inv.get("site_name", "").strip()
        if not site_name:
            continue

        if site_name not in site_map:
            ss = StagingSite(
                batch_id=batch_id,
                row_number=idx,
                nom=site_name,
                adresse=inv.get("address"),
                code_postal=inv.get("postal_code"),
                ville=inv.get("city"),
                siret=inv.get("siret"),
                source_type="invoice",
                source_ref=inv.get("invoice_ref"),
            )
            db.add(ss)
            db.flush()
            site_map[site_name] = ss

        meter_id = inv.get("meter_id", "").strip()
        if meter_id:
            sc = StagingCompteur(
                batch_id=batch_id,
                staging_site_id=site_map[site_name].id,
                row_number=idx,
                meter_id=meter_id,
                type_compteur=inv.get("energy_type"),
            )
            db.add(sc)
            compteurs_detected += 1

    db.flush()

    batch.stats_json = json.dumps(
        {
            "sites_count": len(site_map),
            "compteurs_count": compteurs_detected,
        }
    )

    return {
        "sites_detected": len(site_map),
        "compteurs_detected": compteurs_detected,
    }


# ========================================
# QA Scoring Thresholds
# ========================================

# Gating thresholds for quality score (0-100)
QA_THRESHOLD_EXCELLENT = 85  # Green — auto-activable
QA_THRESHOLD_BON = 70  # Amber — activable with review
QA_THRESHOLD_MOYEN = 50  # Orange — requires corrections

QA_GRADES = {
    "excellent": {
        "min": QA_THRESHOLD_EXCELLENT,
        "label": "Excellent",
        "color": "green",
        "message": "Donnees de haute qualite, activation automatique possible.",
    },
    "bon": {
        "min": QA_THRESHOLD_BON,
        "label": "Bon",
        "color": "amber",
        "message": "Quelques avertissements mineurs. Activation possible apres revue.",
    },
    "moyen": {
        "min": QA_THRESHOLD_MOYEN,
        "label": "Moyen",
        "color": "orange",
        "message": "Corrections recommandees avant activation.",
    },
    "insuffisant": {
        "min": 0,
        "label": "Insuffisant",
        "color": "red",
        "message": "Donnees degradees. Corrections obligatoires.",
    },
}


def compute_quality_grade(score: float) -> dict:
    """Compute QA grade from quality score.

    Returns: {grade, label, color, message, threshold_next, gap}
    """
    if score >= QA_THRESHOLD_EXCELLENT:
        grade = "excellent"
    elif score >= QA_THRESHOLD_BON:
        grade = "bon"
    elif score >= QA_THRESHOLD_MOYEN:
        grade = "moyen"
    else:
        grade = "insuffisant"

    info = QA_GRADES[grade]

    # Next threshold to reach (for progress display)
    if grade == "excellent":
        threshold_next = None
        gap = 0.0
    elif grade == "bon":
        threshold_next = QA_THRESHOLD_EXCELLENT
        gap = round(QA_THRESHOLD_EXCELLENT - score, 1)
    elif grade == "moyen":
        threshold_next = QA_THRESHOLD_BON
        gap = round(QA_THRESHOLD_BON - score, 1)
    else:
        threshold_next = QA_THRESHOLD_MOYEN
        gap = round(QA_THRESHOLD_MOYEN - score, 1)

    return {
        "grade": grade,
        "label": info["label"],
        "color": info["color"],
        "message": info["message"],
        "threshold_next": threshold_next,
        "gap": gap,
    }


# ========================================
# Summary & Quality Gate
# ========================================


def get_staging_summary(db: Session, batch_id: int) -> dict:
    """Returns summary stats for a staging batch."""
    batch = db.get(StagingBatch, batch_id)
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    sites_count = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == batch_id,
            StagingSite.skip.is_(False),
        )
        .count()
    )

    compteurs_count = (
        db.query(StagingCompteur)
        .filter(
            StagingCompteur.batch_id == batch_id,
            StagingCompteur.skip.is_(False),
        )
        .count()
    )

    findings = (
        db.query(QualityFinding)
        .filter(
            QualityFinding.batch_id == batch_id,
        )
        .all()
    )

    critical = sum(1 for f in findings if f.severity == QualityRuleSeverity.CRITICAL and not f.resolved)
    blocking = sum(
        1
        for f in findings
        if f.severity in (QualityRuleSeverity.BLOCKING, QualityRuleSeverity.CRITICAL) and not f.resolved
    )
    warnings = sum(1 for f in findings if f.severity == QualityRuleSeverity.WARNING and not f.resolved)
    info_count = sum(1 for f in findings if f.severity == QualityRuleSeverity.INFO and not f.resolved)
    total_findings = len(findings)

    # Quality score: 100 if no findings, decremented by severity
    max_issues = max(sites_count + compteurs_count, 1)
    quality_score = max(0.0, 100.0 - (blocking * 20 + warnings * 5 + info_count * 1) / max_issues * 100)
    quality_score = round(min(100.0, quality_score), 1)

    # QA grade with thresholds
    grade_info = compute_quality_grade(quality_score)

    return {
        "batch_id": batch_id,
        "status": batch.status.value if batch.status else None,
        "mode": batch.mode,
        "sites": sites_count,
        "compteurs": compteurs_count,
        "findings_total": total_findings,
        "blocking": blocking,
        "warnings": warnings,
        "info": info_count,
        "quality_score": quality_score,
        "quality_grade": grade_info,
        "can_activate": blocking == 0,
        "can_auto_activate": blocking == 0 and quality_score >= QA_THRESHOLD_EXCELLENT,
    }


def run_quality_gate(db: Session, batch_id: int) -> list:
    """Run all quality rules, persist QualityFinding rows.

    Returns list of findings dicts.
    """
    batch = db.get(StagingBatch, batch_id)
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    # Clear previous findings for this batch (re-run)
    db.query(QualityFinding).filter(QualityFinding.batch_id == batch_id).delete()
    db.flush()

    # Run all rules
    raw_findings = run_all_rules(db, batch_id)

    # Persist findings
    persisted = []
    for f in raw_findings:
        qf = QualityFinding(
            batch_id=batch_id,
            rule_id=f["rule_id"],
            severity=f["severity"],
            staging_site_id=f.get("staging_site_id"),
            staging_compteur_id=f.get("staging_compteur_id"),
            evidence_json=f.get("evidence_json"),
            suggested_action=f.get("suggested_action"),
        )
        db.add(qf)
        persisted.append(qf)

    db.flush()

    # Update batch status (CRITICAL or BLOCKING findings prevent validation)
    blocking_count = sum(
        1 for f in persisted if f.severity in (QualityRuleSeverity.BLOCKING, QualityRuleSeverity.CRITICAL)
    )
    if blocking_count == 0:
        batch.status = StagingStatus.VALIDATED

    return [
        {
            "id": qf.id,
            "rule_id": qf.rule_id,
            "severity": qf.severity.value,
            "staging_site_id": qf.staging_site_id,
            "staging_compteur_id": qf.staging_compteur_id,
            "evidence": qf.evidence_json,
            "suggested_action": qf.suggested_action,
            "resolved": qf.resolved,
        }
        for qf in persisted
    ]


# ========================================
# Corrections (apply_fix)
# ========================================


def apply_fix(db: Session, batch_id: int, fix_type: str, params: dict) -> dict:
    """Apply a correction to staging data.

    fix_type: "merge_sites" | "skip" | "remap" | "update_field"
    """
    if fix_type == "merge_sites":
        return _fix_merge_sites(db, batch_id, params)
    elif fix_type == "skip":
        return _fix_skip(db, batch_id, params)
    elif fix_type == "remap":
        return _fix_remap(db, batch_id, params)
    elif fix_type == "update_field":
        return _fix_update_field(db, batch_id, params)
    else:
        return {"applied": False, "detail": f"Unknown fix_type: {fix_type}"}


def _fix_merge_sites(db: Session, batch_id: int, params: dict) -> dict:
    """Merge a staging site into an existing site (set target_site_id, skip staging)."""
    staging_site_id = params.get("staging_site_id")
    target_site_id = params.get("target_site_id")
    if not staging_site_id or not target_site_id:
        return {"applied": False, "detail": "staging_site_id and target_site_id required"}

    ss = (
        db.query(StagingSite)
        .filter(
            StagingSite.id == staging_site_id,
            StagingSite.batch_id == batch_id,
        )
        .first()
    )
    if not ss:
        return {"applied": False, "detail": f"StagingSite {staging_site_id} not found in batch"}

    ss.target_site_id = target_site_id
    ss.skip = True

    # Remap orphan compteurs from this staging site to target
    compteurs = (
        db.query(StagingCompteur)
        .filter(
            StagingCompteur.staging_site_id == staging_site_id,
        )
        .all()
    )
    for sc in compteurs:
        sc.target_site_id = target_site_id

    # Resolve related findings
    _resolve_findings(db, batch_id, staging_site_id=staging_site_id, resolution="merged")

    db.flush()
    return {"applied": True, "detail": f"Merged staging site {staging_site_id} → site {target_site_id}"}


def _fix_skip(db: Session, batch_id: int, params: dict) -> dict:
    """Skip a staging site or compteur."""
    staging_site_id = params.get("staging_site_id")
    staging_compteur_id = params.get("staging_compteur_id")

    if staging_site_id:
        ss = (
            db.query(StagingSite)
            .filter(
                StagingSite.id == staging_site_id,
                StagingSite.batch_id == batch_id,
            )
            .first()
        )
        if ss:
            ss.skip = True
            _resolve_findings(db, batch_id, staging_site_id=staging_site_id, resolution="skipped")
            db.flush()
            return {"applied": True, "detail": f"Skipped staging site {staging_site_id}"}

    if staging_compteur_id:
        sc = (
            db.query(StagingCompteur)
            .filter(
                StagingCompteur.id == staging_compteur_id,
                StagingCompteur.batch_id == batch_id,
            )
            .first()
        )
        if sc:
            sc.skip = True
            _resolve_findings(db, batch_id, staging_compteur_id=staging_compteur_id, resolution="skipped")
            db.flush()
            return {"applied": True, "detail": f"Skipped staging compteur {staging_compteur_id}"}

    return {"applied": False, "detail": "No staging_site_id or staging_compteur_id provided"}


def _fix_remap(db: Session, batch_id: int, params: dict) -> dict:
    """Remap an orphan compteur to a staging site or existing site."""
    staging_compteur_id = params.get("staging_compteur_id")
    target_staging_site_id = params.get("target_staging_site_id")
    target_site_id = params.get("target_site_id")

    if not staging_compteur_id:
        return {"applied": False, "detail": "staging_compteur_id required"}

    sc = (
        db.query(StagingCompteur)
        .filter(
            StagingCompteur.id == staging_compteur_id,
            StagingCompteur.batch_id == batch_id,
        )
        .first()
    )
    if not sc:
        return {"applied": False, "detail": f"StagingCompteur {staging_compteur_id} not found"}

    if target_staging_site_id:
        sc.staging_site_id = target_staging_site_id
    elif target_site_id:
        sc.target_site_id = target_site_id
    else:
        return {"applied": False, "detail": "target_staging_site_id or target_site_id required"}

    _resolve_findings(db, batch_id, staging_compteur_id=staging_compteur_id, resolution="remapped")
    db.flush()
    return {"applied": True, "detail": f"Remapped compteur {staging_compteur_id}"}


def _fix_update_field(db: Session, batch_id: int, params: dict) -> dict:
    """Update a field on a staging site."""
    staging_site_id = params.get("staging_site_id")
    field = params.get("field")
    value = params.get("value")

    if not staging_site_id or not field:
        return {"applied": False, "detail": "staging_site_id and field required"}

    ss = (
        db.query(StagingSite)
        .filter(
            StagingSite.id == staging_site_id,
            StagingSite.batch_id == batch_id,
        )
        .first()
    )
    if not ss:
        return {"applied": False, "detail": f"StagingSite {staging_site_id} not found"}

    allowed_fields = {"adresse", "code_postal", "ville", "surface_m2", "type_site", "siret", "naf_code"}
    if field not in allowed_fields:
        return {"applied": False, "detail": f"Field '{field}' not allowed (allowed: {allowed_fields})"}

    setattr(ss, field, value)
    db.flush()
    return {"applied": True, "detail": f"Updated {field}='{value}' on staging site {staging_site_id}"}


def _resolve_findings(
    db: Session,
    batch_id: int,
    staging_site_id: Optional[int] = None,
    staging_compteur_id: Optional[int] = None,
    resolution: str = "fixed",
):
    """Mark related quality findings as resolved."""
    q = db.query(QualityFinding).filter(
        QualityFinding.batch_id == batch_id,
        QualityFinding.resolved.is_(False),
    )
    if staging_site_id:
        q = q.filter(QualityFinding.staging_site_id == staging_site_id)
    if staging_compteur_id:
        q = q.filter(QualityFinding.staging_compteur_id == staging_compteur_id)

    for f in q.all():
        f.resolved = True
        f.resolution = resolution


# ========================================
# Activation (staging → real entities)
# ========================================

_TYPE_COMPTEUR_MAP = {
    "electricite": (TypeCompteur.ELECTRICITE, EnergyVector.ELECTRICITY),
    "gaz": (TypeCompteur.GAZ, EnergyVector.GAS),
    "eau": (TypeCompteur.EAU, None),
}

_ENERGY_TYPE_MAP = {
    "electricite": DeliveryPointEnergyType.ELEC,
    "gaz": DeliveryPointEnergyType.GAZ,
}


def _pre_activation_checks(db: Session, batch_id: int):
    """Pre-activation safety checks. Raises ValueError on any failure."""
    # 1. No unresolved blocking/critical findings
    blocking = (
        db.query(QualityFinding)
        .filter(
            QualityFinding.batch_id == batch_id,
            QualityFinding.severity.in_([QualityRuleSeverity.BLOCKING, QualityRuleSeverity.CRITICAL]),
            QualityFinding.resolved.is_(False),
        )
        .count()
    )
    if blocking > 0:
        raise ValueError(f"{blocking} unresolved blocking/critical findings — run quality gate fixes first")

    # 2. meter_id uniqueness against live DB
    staging_compteurs = (
        db.query(StagingCompteur)
        .filter(
            StagingCompteur.batch_id == batch_id,
            StagingCompteur.skip.is_(False),
            StagingCompteur.target_compteur_id.is_(None),
            StagingCompteur.meter_id.isnot(None),
        )
        .all()
    )
    staging_meter_ids = [sc.meter_id.strip() for sc in staging_compteurs if sc.meter_id and sc.meter_id.strip()]
    if staging_meter_ids:
        collisions = (
            not_deleted(db.query(Compteur), Compteur)
            .filter(
                Compteur.meter_id.in_(staging_meter_ids),
            )
            .all()
        )
        if collisions:
            collision_ids = [f"{c.meter_id} (compteur #{c.id})" for c in collisions]
            raise ValueError(f"Activation blocked: duplicate delivery point(s) in DB: {', '.join(collision_ids)}")

    # 3. numero_serie uniqueness against live DB
    staging_series = (
        db.query(StagingCompteur)
        .filter(
            StagingCompteur.batch_id == batch_id,
            StagingCompteur.skip.is_(False),
            StagingCompteur.target_compteur_id.is_(None),
            StagingCompteur.numero_serie.isnot(None),
        )
        .all()
    )
    serie_vals = [sc.numero_serie.strip() for sc in staging_series if sc.numero_serie and sc.numero_serie.strip()]
    if serie_vals:
        serie_collisions = (
            not_deleted(db.query(Compteur), Compteur)
            .filter(
                Compteur.numero_serie.in_(serie_vals),
            )
            .all()
        )
        if serie_collisions:
            collision_ids = [f"{c.numero_serie} (compteur #{c.id})" for c in serie_collisions]
            raise ValueError(f"Activation blocked: duplicate numero_serie in DB: {', '.join(collision_ids)}")


def _compute_activation_hash(db: Session, batch_id: int) -> str:
    """Compute SHA-256 fingerprint of staging content for idempotence."""
    sites = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == batch_id,
            StagingSite.skip.is_(False),
        )
        .order_by(StagingSite.id)
        .all()
    )

    compteurs = (
        db.query(StagingCompteur)
        .filter(
            StagingCompteur.batch_id == batch_id,
            StagingCompteur.skip.is_(False),
        )
        .order_by(StagingCompteur.id)
        .all()
    )

    content = json.dumps(
        {
            "batch_id": batch_id,
            "sites": [{"id": s.id, "nom": s.nom, "cp": s.code_postal} for s in sites],
            "compteurs": [{"id": c.id, "mid": c.meter_id, "ns": c.numero_serie} for c in compteurs],
        },
        sort_keys=True,
    )

    return hashlib.sha256(content.encode()).hexdigest()


def _find_or_create_delivery_point(db, site_id, meter_id, type_compteur, batch, batch_id, now):
    """Find existing active DeliveryPoint or create a new one.

    Returns (delivery_point, created: bool).
    """
    if not meter_id or not meter_id.strip():
        return None, False

    code = meter_id.strip()

    # Check for existing active DP with same code on this site
    existing = (
        not_deleted(db.query(DeliveryPoint), DeliveryPoint)
        .filter(
            DeliveryPoint.code == code,
            DeliveryPoint.site_id == site_id,
        )
        .first()
    )
    if existing:
        return existing, False

    energy_type = _ENERGY_TYPE_MAP.get(type_compteur)
    dp = DeliveryPoint(
        code=code,
        energy_type=energy_type,
        site_id=site_id,
        data_source=batch.source_type.value if batch.source_type else "import",
        data_source_ref=f"batch:{batch_id}",
        imported_at=now,
        imported_by=batch.user_id,
    )
    db.add(dp)
    db.flush()
    return dp, True


def _do_activate(db: Session, batch, batch_id: int, portefeuille_id: int, now) -> dict:
    """Core activation logic: create real entities from staging.

    Must be called within a SAVEPOINT (begin_nested) for atomicity.
    Creates Site + DeliveryPoint + Compteur for each staging row.
    """
    staging_sites = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == batch_id,
            StagingSite.skip.is_(False),
        )
        .all()
    )

    sites_created = 0
    compteurs_created = 0
    delivery_points_created = 0
    total_batiments = 0
    total_obligations = 0

    # Resolve org_id from the default portefeuille (for multi-entity creation)
    default_pf = db.get(Portefeuille, portefeuille_id)
    default_entite = db.get(EntiteJuridique, default_pf.entite_juridique_id) if default_pf else None
    org_id = default_entite.organisation_id if default_entite else (batch.org_id or None)

    # Cache: avoid duplicate entity/portefeuille creation within same batch
    _entite_cache = {}  # siren → EntiteJuridique
    _pf_cache = {}  # (entite_id, pf_nom) → Portefeuille

    for ss in staging_sites:
        if ss.target_site_id:
            site = db.get(Site, ss.target_site_id)
        else:
            # ── Step 20: resolve entité / portefeuille from staging fields ──
            resolved_pf_id = ss.target_portefeuille_id or portefeuille_id

            if ss.siren_entite and org_id:
                # Resolve entité juridique by SIREN
                if ss.siren_entite in _entite_cache:
                    entite = _entite_cache[ss.siren_entite]
                else:
                    entite = (
                        db.query(EntiteJuridique)
                        .filter(
                            EntiteJuridique.siren == ss.siren_entite,
                            EntiteJuridique.organisation_id == org_id,
                        )
                        .first()
                    )
                    if not entite:
                        entite = EntiteJuridique(
                            organisation_id=org_id,
                            nom=ss.nom_entite or f"Entité {ss.siren_entite}",
                            siren=ss.siren_entite,
                        )
                        db.add(entite)
                        db.flush()
                    _entite_cache[ss.siren_entite] = entite

                # Resolve portefeuille under this entité
                pf_nom = ss.portefeuille_nom or "Portefeuille principal"
                pf_key = (entite.id, pf_nom)
                if pf_key in _pf_cache:
                    resolved_pf_id = _pf_cache[pf_key].id
                else:
                    pf = (
                        db.query(Portefeuille)
                        .filter(
                            Portefeuille.entite_juridique_id == entite.id,
                            Portefeuille.nom == pf_nom,
                        )
                        .first()
                    )
                    if not pf:
                        pf = Portefeuille(
                            entite_juridique_id=entite.id,
                            nom=pf_nom,
                        )
                        db.add(pf)
                        db.flush()
                    _pf_cache[pf_key] = pf
                    resolved_pf_id = pf.id

            elif ss.portefeuille_nom and default_entite:
                # Portefeuille sans siren_entite → sous l'entité par défaut
                pf_key = (default_entite.id, ss.portefeuille_nom)
                if pf_key in _pf_cache:
                    resolved_pf_id = _pf_cache[pf_key].id
                else:
                    pf = (
                        db.query(Portefeuille)
                        .filter(
                            Portefeuille.entite_juridique_id == default_entite.id,
                            Portefeuille.nom == ss.portefeuille_nom,
                        )
                        .first()
                    )
                    if not pf:
                        pf = Portefeuille(
                            entite_juridique_id=default_entite.id,
                            nom=ss.portefeuille_nom,
                        )
                        db.add(pf)
                        db.flush()
                    _pf_cache[pf_key] = pf
                    resolved_pf_id = pf.id

            site = create_site_from_data(
                db=db,
                portefeuille_id=resolved_pf_id,
                nom=ss.nom,
                type_site=ss.type_site,
                naf_code=ss.naf_code,
                adresse=ss.adresse,
                code_postal=ss.code_postal,
                ville=ss.ville,
                surface_m2=ss.surface_m2,
            )
            site.data_source = batch.source_type.value if batch.source_type else "import"
            site.data_source_ref = f"batch:{batch_id}"
            site.imported_at = now
            site.imported_by = batch.user_id
            if ss.siret:
                site.siret = ss.siret

            prov = provision_site(db, site)
            total_batiments += 1
            total_obligations += prov.get("obligations", 0)
            sites_created += 1

            # ── Step 20: create bâtiment if specified ──
            if ss.batiment_nom or ss.batiment_surface_m2:
                bat = Batiment(
                    site_id=site.id,
                    nom=ss.batiment_nom or "Bâtiment principal",
                    surface_m2=ss.batiment_surface_m2 or ss.surface_m2 or 0,
                    annee_construction=ss.batiment_annee_construction,
                    cvc_power_kw=ss.batiment_cvc_power_kw,
                )
                db.add(bat)

        staging_compteurs = (
            db.query(StagingCompteur)
            .filter(
                StagingCompteur.staging_site_id == ss.id,
                StagingCompteur.skip.is_(False),
            )
            .all()
        )

        for sc in staging_compteurs:
            if sc.target_compteur_id:
                continue

            # Find or create DeliveryPoint for this meter_id
            dp, dp_created = _find_or_create_delivery_point(
                db,
                site.id,
                sc.meter_id,
                sc.type_compteur,
                batch,
                batch_id,
                now,
            )
            if dp_created:
                delivery_points_created += 1

            tc_info = _TYPE_COMPTEUR_MAP.get(sc.type_compteur, (TypeCompteur.ELECTRICITE, EnergyVector.ELECTRICITY))
            compteur = Compteur(
                site_id=site.id,
                type=tc_info[0],
                numero_serie=sc.numero_serie or f"STG-{sc.id}",
                meter_id=sc.meter_id,
                energy_vector=tc_info[1],
                puissance_souscrite_kw=sc.puissance_kw,
                actif=True,
                delivery_point_id=dp.id if dp else None,
                data_source=batch.source_type.value if batch.source_type else "import",
                data_source_ref=f"batch:{batch_id}",
            )
            db.add(compteur)
            compteurs_created += 1

    # Mark batch as applied (inside savepoint — rolled back on failure)
    batch.status = StagingStatus.APPLIED
    batch.stats_json = json.dumps(
        {
            "sites_created": sites_created,
            "compteurs_created": compteurs_created,
            "delivery_points_created": delivery_points_created,
            "batiments": total_batiments,
            "obligations": total_obligations,
            "activated_at": now.isoformat(),
        }
    )

    db.flush()

    return {
        "sites_created": sites_created,
        "compteurs_created": compteurs_created,
        "delivery_points_created": delivery_points_created,
        "batiments": total_batiments,
        "obligations": total_obligations,
    }


def activate_batch(db: Session, batch_id: int, portefeuille_id: int, user_id: int = None) -> dict:
    """Create real Site/Compteur/Batiment from validated staging.

    Atomic: wrapped in SAVEPOINT — any error rolls back ALL created entities.
    Idempotent: returns cached result if batch already activated.
    Audited: creates ActivationLog entry for every attempt.
    """
    batch = db.get(StagingBatch, batch_id)
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    # Idempotence: already applied → return cached result
    if batch.status == StagingStatus.APPLIED:
        existing_log = (
            db.query(ActivationLog)
            .filter(
                ActivationLog.batch_id == batch_id,
                ActivationLog.status == ActivationLogStatus.SUCCESS,
            )
            .first()
        )
        if existing_log:
            return {
                "sites_created": existing_log.sites_created,
                "compteurs_created": existing_log.compteurs_created,
                "batiments": 0,
                "obligations": 0,
                "detail": "Batch already applied (idempotent)",
                "activation_log_id": existing_log.id,
            }
        return {
            "sites_created": 0,
            "compteurs_created": 0,
            "batiments": 0,
            "obligations": 0,
            "detail": "Batch already applied",
        }

    # Pre-activation safety checks (outside savepoint — fail fast)
    _pre_activation_checks(db, batch_id)

    # Idempotence: check activation_hash
    activation_hash = _compute_activation_hash(db, batch_id)
    existing_success = (
        db.query(ActivationLog)
        .filter(
            ActivationLog.activation_hash == activation_hash,
            ActivationLog.status == ActivationLogStatus.SUCCESS,
        )
        .first()
    )
    if existing_success:
        return {
            "sites_created": existing_success.sites_created,
            "compteurs_created": existing_success.compteurs_created,
            "batiments": 0,
            "obligations": 0,
            "detail": "Idempotent: same content already activated",
            "activation_log_id": existing_success.id,
        }

    # Create activation log (STARTED) — persisted outside savepoint
    now = datetime.now(timezone.utc)
    log = ActivationLog(
        batch_id=batch_id,
        started_at=now,
        status=ActivationLogStatus.STARTED,
        activation_hash=activation_hash,
        user_id=user_id,
    )
    db.add(log)
    db.flush()

    # Atomic activation within SAVEPOINT
    # batch.status + log.status are updated INSIDE the savepoint so that
    # a rollback reverts everything atomically (no "APPLIED" without entities).
    try:
        with db.begin_nested():
            result = _do_activate(db, batch, batch_id, portefeuille_id, now)
            # Status updates inside savepoint — atomic with entity creation
            log.status = ActivationLogStatus.SUCCESS
            log.completed_at = datetime.now(timezone.utc)
            log.sites_created = result["sites_created"]
            log.compteurs_created = result["compteurs_created"]

        # Savepoint committed — batch.status=APPLIED + log=SUCCESS are atomic
        result["activation_log_id"] = log.id
        return result

    except (SQLAlchemyError, ValueError, Exception) as e:
        # Savepoint auto-rolled back — all created entities undone.
        # Expire BOTH batch and log to discard stale in-memory state
        # (APPLIED / SUCCESS / non-zero counters) that would otherwise
        # be re-flushed to DB by the flush() below.
        db.expire(batch)
        db.expire(log)
        log.status = ActivationLogStatus.FAILED
        log.completed_at = datetime.now(timezone.utc)
        log.error_message = str(e)[:2000]
        log.sites_created = 0
        log.compteurs_created = 0
        db.flush()

        raise ValueError(f"Activation failed (rolled back): {e}") from e


# ========================================
# Diff plan (incremental sync)
# ========================================


def get_diff_plan(db: Session, portfolio_id: int, staging_batch_id: int) -> dict:
    """Compare staging batch vs existing portfolio → diff plan.

    Returns: {to_create, to_update, to_merge}
    """
    from models import Portefeuille

    pf = db.get(Portefeuille, portfolio_id)
    if not pf:
        raise ValueError(f"Portefeuille {portfolio_id} not found")

    existing_sites = (
        db.query(Site)
        .filter(
            Site.portefeuille_id == portfolio_id,
            Site.actif.is_(True),
        )
        .all()
    )

    staging_sites = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == staging_batch_id,
            StagingSite.skip.is_(False),
        )
        .all()
    )

    # Build lookup by name + code_postal
    existing_by_key = {}
    for s in existing_sites:
        key = f"{(s.nom or '').lower().strip()}|{(s.code_postal or '').strip()}"
        existing_by_key[key] = s

    to_create = []
    to_update = []
    to_merge = []

    for ss in staging_sites:
        key = f"{(ss.nom or '').lower().strip()}|{(ss.code_postal or '').strip()}"

        if key in existing_by_key:
            existing = existing_by_key[key]
            changes = _compute_site_diff(ss, existing)
            if changes:
                to_update.append(
                    {
                        "staging_site_id": ss.id,
                        "existing_site_id": existing.id,
                        "name": ss.nom,
                        "changes": changes,
                    }
                )
            else:
                to_merge.append(
                    {
                        "staging_site_id": ss.id,
                        "existing_site_id": existing.id,
                        "name": ss.nom,
                        "detail": "identical",
                    }
                )
        else:
            to_create.append(
                {
                    "staging_site_id": ss.id,
                    "name": ss.nom,
                    "type": ss.type_site,
                    "address": ss.adresse,
                }
            )

    return {
        "to_create": to_create,
        "to_update": to_update,
        "to_merge": to_merge,
    }


def _compute_site_diff(staging: StagingSite, existing: Site) -> list:
    """Compare staging site fields vs existing site, return list of changed fields."""
    changes = []
    field_pairs = [
        ("adresse", staging.adresse, existing.adresse),
        ("ville", staging.ville, existing.ville),
        ("surface_m2", staging.surface_m2, existing.surface_m2),
        ("siret", staging.siret, existing.siret),
    ]
    for field, new_val, old_val in field_pairs:
        if new_val is not None and str(new_val).strip() != str(old_val or "").strip():
            changes.append({"field": field, "old": old_val, "new": new_val})
    return changes


# ========================================
# Utilities
# ========================================


def compute_content_hash(content: bytes) -> str:
    """SHA-256 hash of file content for idempotence check."""
    return hashlib.sha256(content).hexdigest()


def abandon_batch(db: Session, batch_id: int) -> dict:
    """Mark a batch as abandoned (user cancelled)."""
    batch = db.get(StagingBatch, batch_id)
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")

    if batch.status == StagingStatus.APPLIED:
        return {"applied": False, "detail": "Cannot abandon an already applied batch"}

    batch.status = StagingStatus.ABANDONED
    db.flush()
    return {"applied": True, "detail": f"Batch {batch_id} abandoned"}
