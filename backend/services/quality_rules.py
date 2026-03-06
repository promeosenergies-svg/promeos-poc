"""
PROMEOS - Quality Rules Engine (DIAMANT)
11 deterministic rules for staging data quality gate.
"""

from difflib import SequenceMatcher
from typing import List

from sqlalchemy.orm import Session

from models import (
    StagingSite,
    StagingCompteur,
    Site,
    Compteur,
    EntiteJuridique,
    QualityFinding,
    QualityRuleSeverity,
    not_deleted,
)
from services.validation_helpers import (
    is_valid_siren,
    is_valid_siret,
    is_valid_meter_id,
    is_valid_postal_code,
)


# ========================================
# Individual rule checks
# ========================================


def _similarity(a: str, b: str) -> float:
    """Normalized string similarity (0-1) using SequenceMatcher."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def check_duplicate_sites(db: Session, batch_id: int) -> List[dict]:
    """Rule: dup_site_address — staging sites with similar address (inter-staging + vs existing)."""
    findings = []
    staging_sites = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == batch_id,
            StagingSite.skip.is_(False),
        )
        .all()
    )

    # Intra-staging duplicates
    for i, s1 in enumerate(staging_sites):
        for s2 in staging_sites[i + 1 :]:
            if s1.code_postal and s2.code_postal and s1.code_postal == s2.code_postal:
                sim = _similarity(s1.adresse or "", s2.adresse or "")
                if sim > 0.8:
                    findings.append(
                        {
                            "rule_id": "dup_site_address",
                            "severity": QualityRuleSeverity.WARNING,
                            "staging_site_id": s1.id,
                            "evidence_json": (
                                f'{{"dup_with_staging_id": {s2.id}, '
                                f'"similarity": {sim:.2f}, '
                                f'"site_a": "{s1.nom}", "site_b": "{s2.nom}"}}'
                            ),
                            "suggested_action": "merge",
                        }
                    )

    # Vs existing sites (limit to 500 for perf)
    existing_sites = not_deleted(db.query(Site), Site).filter(Site.actif.is_(True)).limit(500).all()
    for ss in staging_sites:
        for ex in existing_sites:
            if ss.code_postal and ex.code_postal and ss.code_postal == ex.code_postal:
                sim = _similarity(ss.adresse or "", ex.adresse or "")
                if sim > 0.8:
                    findings.append(
                        {
                            "rule_id": "dup_site_address",
                            "severity": QualityRuleSeverity.WARNING,
                            "staging_site_id": ss.id,
                            "evidence_json": (
                                f'{{"dup_with_existing_id": {ex.id}, '
                                f'"similarity": {sim:.2f}, '
                                f'"staging_name": "{ss.nom}", "existing_name": "{ex.nom}"}}'
                            ),
                            "suggested_action": "merge",
                        }
                    )

    return findings


def check_duplicate_meters(db: Session, batch_id: int) -> List[dict]:
    """Rule: dup_meter — staging compteurs with same PRM/PDL/PCE or numero_serie."""
    findings = []
    staging_compteurs = (
        db.query(StagingCompteur)
        .filter(
            StagingCompteur.batch_id == batch_id,
            StagingCompteur.skip.is_(False),
        )
        .all()
    )

    # Intra-staging
    seen_serie = {}
    seen_meter = {}
    for sc in staging_compteurs:
        if sc.numero_serie:
            if sc.numero_serie in seen_serie:
                findings.append(
                    {
                        "rule_id": "dup_meter",
                        "severity": QualityRuleSeverity.BLOCKING,
                        "staging_compteur_id": sc.id,
                        "evidence_json": (
                            f'{{"dup_with_staging_id": {seen_serie[sc.numero_serie]}, '
                            f'"field": "numero_serie", "value": "{sc.numero_serie}"}}'
                        ),
                        "suggested_action": "skip",
                    }
                )
            else:
                seen_serie[sc.numero_serie] = sc.id

        if sc.meter_id:
            if sc.meter_id in seen_meter:
                findings.append(
                    {
                        "rule_id": "dup_meter",
                        "severity": QualityRuleSeverity.BLOCKING,
                        "staging_compteur_id": sc.id,
                        "evidence_json": (
                            f'{{"dup_with_staging_id": {seen_meter[sc.meter_id]}, '
                            f'"field": "meter_id", "value": "{sc.meter_id}"}}'
                        ),
                        "suggested_action": "skip",
                    }
                )
            else:
                seen_meter[sc.meter_id] = sc.id

    # Vs existing compteurs
    existing_compteurs = not_deleted(db.query(Compteur), Compteur).filter(Compteur.actif.is_(True)).all()
    existing_series = {c.numero_serie for c in existing_compteurs if c.numero_serie}
    existing_meters = {c.meter_id for c in existing_compteurs if c.meter_id}

    for sc in staging_compteurs:
        if sc.numero_serie and sc.numero_serie in existing_series:
            findings.append(
                {
                    "rule_id": "dup_meter",
                    "severity": QualityRuleSeverity.BLOCKING,
                    "staging_compteur_id": sc.id,
                    "evidence_json": (
                        f'{{"dup_with_existing": true, "field": "numero_serie", "value": "{sc.numero_serie}"}}'
                    ),
                    "suggested_action": "merge",
                }
            )
        if sc.meter_id and sc.meter_id in existing_meters:
            findings.append(
                {
                    "rule_id": "dup_meter",
                    "severity": QualityRuleSeverity.BLOCKING,
                    "staging_compteur_id": sc.id,
                    "evidence_json": (f'{{"dup_with_existing": true, "field": "meter_id", "value": "{sc.meter_id}"}}'),
                    "suggested_action": "merge",
                }
            )

    return findings


def check_orphan_meters(db: Session, batch_id: int) -> List[dict]:
    """Rule: orphan_meter — staging compteur without any site association."""
    findings = []
    orphans = (
        db.query(StagingCompteur)
        .filter(
            StagingCompteur.batch_id == batch_id,
            StagingCompteur.skip.is_(False),
            StagingCompteur.staging_site_id.is_(None),
            StagingCompteur.target_site_id.is_(None),
        )
        .all()
    )

    for sc in orphans:
        findings.append(
            {
                "rule_id": "orphan_meter",
                "severity": QualityRuleSeverity.BLOCKING,
                "staging_compteur_id": sc.id,
                "evidence_json": (f'{{"numero_serie": "{sc.numero_serie or ""}", "meter_id": "{sc.meter_id or ""}"}}'),
                "suggested_action": "remap",
            }
        )

    return findings


def check_incomplete_sites(db: Session, batch_id: int) -> List[dict]:
    """Rule: incomplete_site — staging site missing address or postal code."""
    findings = []
    sites = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == batch_id,
            StagingSite.skip.is_(False),
        )
        .all()
    )

    for ss in sites:
        missing = []
        if not ss.adresse:
            missing.append("adresse")
        if not ss.code_postal:
            missing.append("code_postal")
        if missing:
            findings.append(
                {
                    "rule_id": "incomplete_site",
                    "severity": QualityRuleSeverity.WARNING,
                    "staging_site_id": ss.id,
                    "evidence_json": f'{{"missing_fields": {missing}, "site_name": "{ss.nom}"}}',
                    "suggested_action": "fix_address",
                }
            )

    return findings


def check_duplicate_delivery_point(db: Session, batch_id: int) -> List[dict]:
    """Rule: dup_delivery_point_global — CRITICAL.

    A PRM (elec) or PCE (gaz) must be globally unique among active compteurs.
    Detects:
    1. Intra-staging: two staging rows with the same meter_id
    2. Vs existing DB: staging meter_id already exists in active compteurs
    Soft-deleted compteurs are excluded (reuse allowed).
    """
    findings = []
    staging_compteurs = (
        db.query(StagingCompteur)
        .filter(
            StagingCompteur.batch_id == batch_id,
            StagingCompteur.skip.is_(False),
        )
        .all()
    )

    # 1. Intra-staging duplicates
    seen_meter = {}
    for sc in staging_compteurs:
        if not sc.meter_id:
            continue
        mid = sc.meter_id.strip()
        if not mid:
            continue
        if mid in seen_meter:
            findings.append(
                {
                    "rule_id": "dup_delivery_point_global",
                    "severity": QualityRuleSeverity.CRITICAL,
                    "staging_compteur_id": sc.id,
                    "evidence_json": (
                        f'{{"dup_with_staging_id": {seen_meter[mid]}, '
                        f'"field": "meter_id", "value": "{mid}", '
                        f'"scope": "intra_staging"}}'
                    ),
                    "suggested_action": "skip",
                }
            )
        else:
            seen_meter[mid] = sc.id

    # 2. Vs existing active compteurs (soft-deleted excluded)
    active_compteurs = (
        not_deleted(db.query(Compteur), Compteur)
        .filter(
            Compteur.meter_id.isnot(None),
        )
        .all()
    )
    existing_map = {}
    for c in active_compteurs:
        if c.meter_id:
            existing_map[c.meter_id.strip()] = c.id

    for sc in staging_compteurs:
        if not sc.meter_id:
            continue
        mid = sc.meter_id.strip()
        if not mid:
            continue
        if mid in existing_map:
            findings.append(
                {
                    "rule_id": "dup_delivery_point_global",
                    "severity": QualityRuleSeverity.CRITICAL,
                    "staging_compteur_id": sc.id,
                    "evidence_json": (
                        f'{{"dup_with_existing_id": {existing_map[mid]}, '
                        f'"field": "meter_id", "value": "{mid}", '
                        f'"scope": "vs_existing_db"}}'
                    ),
                    "suggested_action": "skip",
                }
            )

    return findings


def check_missing_entity(db: Session, batch_id: int) -> List[dict]:
    """Rule: missing_entite — staging site has SIRET but no matching EntiteJuridique."""
    findings = []
    sites_with_siret = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == batch_id,
            StagingSite.skip.is_(False),
            StagingSite.siret.isnot(None),
        )
        .all()
    )

    if not sites_with_siret:
        return findings

    # Get all known SIRENs (first 9 digits of SIRET)
    known_sirens = {ej.siren for ej in db.query(EntiteJuridique).all() if ej.siren}

    for ss in sites_with_siret:
        siren = ss.siret[:9] if len(ss.siret) >= 9 else ss.siret
        if siren not in known_sirens:
            findings.append(
                {
                    "rule_id": "missing_entite",
                    "severity": QualityRuleSeverity.INFO,
                    "staging_site_id": ss.id,
                    "evidence_json": (
                        f'{{"siret": "{ss.siret}", "siren_extracted": "{siren}", "site_name": "{ss.nom}"}}'
                    ),
                    "suggested_action": "create_entite",
                }
            )

    return findings


# ========================================
# Format validation rules
# ========================================


def check_valid_siren(db: Session, batch_id: int) -> List[dict]:
    """Rule: valid_siren_format — SIREN portion of SIRET must be 9 valid digits + Luhn."""
    findings = []
    sites = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == batch_id,
            StagingSite.skip.is_(False),
            StagingSite.siret.isnot(None),
        )
        .all()
    )

    for ss in sites:
        siret_val = ss.siret.strip() if ss.siret else ""
        if not siret_val:
            continue
        siren_part = siret_val[:9]
        if not is_valid_siren(siren_part):
            findings.append(
                {
                    "rule_id": "valid_siren_format",
                    "severity": QualityRuleSeverity.BLOCKING,
                    "staging_site_id": ss.id,
                    "evidence_json": (
                        f'{{"field": "siret", "siren_extracted": "{siren_part}", '
                        f'"site_name": "{ss.nom}", "reason": "invalid_siren"}}'
                    ),
                    "suggested_action": "fix_siret",
                }
            )
    return findings


def check_valid_siret(db: Session, batch_id: int) -> List[dict]:
    """Rule: valid_siret_format — SIRET must be exactly 14 valid digits + Luhn."""
    findings = []
    sites = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == batch_id,
            StagingSite.skip.is_(False),
            StagingSite.siret.isnot(None),
        )
        .all()
    )

    for ss in sites:
        siret_val = ss.siret.strip() if ss.siret else ""
        if not siret_val:
            continue
        if not is_valid_siret(siret_val):
            findings.append(
                {
                    "rule_id": "valid_siret_format",
                    "severity": QualityRuleSeverity.BLOCKING,
                    "staging_site_id": ss.id,
                    "evidence_json": (
                        f'{{"field": "siret", "value": "{siret_val}", '
                        f'"site_name": "{ss.nom}", "reason": "invalid_siret"}}'
                    ),
                    "suggested_action": "fix_siret",
                }
            )
    return findings


def check_valid_meter_format(db: Session, batch_id: int) -> List[dict]:
    """Rule: valid_meter_format — meter_id (PRM/PCE) must be exactly 14 digits."""
    findings = []
    compteurs = (
        db.query(StagingCompteur)
        .filter(
            StagingCompteur.batch_id == batch_id,
            StagingCompteur.skip.is_(False),
            StagingCompteur.meter_id.isnot(None),
        )
        .all()
    )

    for sc in compteurs:
        mid = sc.meter_id.strip() if sc.meter_id else ""
        if not mid:
            continue
        if not is_valid_meter_id(mid):
            findings.append(
                {
                    "rule_id": "valid_meter_format",
                    "severity": QualityRuleSeverity.BLOCKING,
                    "staging_compteur_id": sc.id,
                    "evidence_json": (f'{{"field": "meter_id", "value": "{mid}", "reason": "expected_14_digits"}}'),
                    "suggested_action": "fix_meter_id",
                }
            )
    return findings


def check_valid_postal_code(db: Session, batch_id: int) -> List[dict]:
    """Rule: valid_postal_code — code_postal must be a valid 5-digit French postal code."""
    findings = []
    sites = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == batch_id,
            StagingSite.skip.is_(False),
            StagingSite.code_postal.isnot(None),
        )
        .all()
    )

    for ss in sites:
        cp = ss.code_postal.strip() if ss.code_postal else ""
        if not cp:
            continue
        if not is_valid_postal_code(cp):
            findings.append(
                {
                    "rule_id": "valid_postal_code",
                    "severity": QualityRuleSeverity.WARNING,
                    "staging_site_id": ss.id,
                    "evidence_json": (
                        f'{{"field": "code_postal", "value": "{cp}", '
                        f'"site_name": "{ss.nom}", "reason": "invalid_postal_code"}}'
                    ),
                    "suggested_action": "fix_address",
                }
            )
    return findings


def check_valid_dates(db: Session, batch_id: int) -> List[dict]:
    """Rule: valid_date_format — no string date fields in current staging schema.
    Reserved for future use when date-string fields are added to staging models.
    """
    return []


# ── Step 20: multi-entité / bâtiment rules ──

def check_invalid_siren_entite(db: Session, batch_id: int) -> List[dict]:
    """Rule: invalid_siren_entite — siren_entite present but not 9 digits."""
    findings = []
    sites = db.query(StagingSite).filter(
        StagingSite.batch_id == batch_id,
        StagingSite.skip.is_(False),
        StagingSite.siren_entite.isnot(None),
    ).all()
    for ss in sites:
        siren = ss.siren_entite.strip()
        if not siren.isdigit() or len(siren) != 9:
            findings.append({
                "rule_id": "invalid_siren_entite",
                "severity": QualityRuleSeverity.WARNING,
                "staging_site_id": ss.id,
                "evidence_json": f'{{"siren_entite": "{siren}", "row": {ss.row_number}}}',
                "suggested_action": "Corriger le SIREN entité (9 chiffres)",
            })
    return findings


def check_orphan_portefeuille(db: Session, batch_id: int) -> List[dict]:
    """Rule: orphan_portefeuille — portefeuille sans siren_entite → entité par défaut."""
    findings = []
    sites = db.query(StagingSite).filter(
        StagingSite.batch_id == batch_id,
        StagingSite.skip.is_(False),
        StagingSite.portefeuille_nom.isnot(None),
        StagingSite.siren_entite.is_(None),
    ).all()
    for ss in sites:
        findings.append({
            "rule_id": "orphan_portefeuille",
            "severity": QualityRuleSeverity.INFO,
            "staging_site_id": ss.id,
            "evidence_json": f'{{"portefeuille": "{ss.portefeuille_nom}", "row": {ss.row_number}}}',
            "suggested_action": "Le portefeuille sera rattaché à l'entité par défaut",
        })
    return findings


def check_batiment_sans_surface(db: Session, batch_id: int) -> List[dict]:
    """Rule: batiment_sans_surface — batiment_nom present sans surface."""
    findings = []
    sites = db.query(StagingSite).filter(
        StagingSite.batch_id == batch_id,
        StagingSite.skip.is_(False),
        StagingSite.batiment_nom.isnot(None),
        StagingSite.batiment_surface_m2.is_(None),
    ).all()
    for ss in sites:
        findings.append({
            "rule_id": "batiment_sans_surface",
            "severity": QualityRuleSeverity.INFO,
            "staging_site_id": ss.id,
            "evidence_json": f'{{"batiment_nom": "{ss.batiment_nom}", "row": {ss.row_number}}}',
            "suggested_action": "Ajouter la surface du bâtiment",
        })
    return findings


# ========================================
# Rules registry
# ========================================

QUALITY_RULES = [
    {
        "id": "dup_delivery_point_global",
        "label": "PRM/PCE duplique (point de livraison unique)",
        "severity": "critical",
        "check": check_duplicate_delivery_point,
    },
    {
        "id": "dup_site_address",
        "label": "Sites avec adresse similaire",
        "severity": "warning",
        "check": check_duplicate_sites,
    },
    {
        "id": "dup_meter",
        "label": "Compteurs avec PRM/PDL/PCE identique",
        "severity": "blocking",
        "check": check_duplicate_meters,
    },
    {
        "id": "orphan_meter",
        "label": "Compteur sans site associe",
        "severity": "blocking",
        "check": check_orphan_meters,
    },
    {
        "id": "incomplete_site",
        "label": "Site incomplet (adresse ou CP manquant)",
        "severity": "warning",
        "check": check_incomplete_sites,
    },
    {
        "id": "missing_entite",
        "label": "Entite juridique non identifiee",
        "severity": "info",
        "check": check_missing_entity,
    },
    {
        "id": "valid_siren_format",
        "label": "Format SIREN invalide (9 chiffres + Luhn)",
        "severity": "blocking",
        "check": check_valid_siren,
    },
    {
        "id": "valid_siret_format",
        "label": "Format SIRET invalide (14 chiffres + Luhn)",
        "severity": "blocking",
        "check": check_valid_siret,
    },
    {
        "id": "valid_meter_format",
        "label": "Format PRM/PCE invalide (14 chiffres)",
        "severity": "blocking",
        "check": check_valid_meter_format,
    },
    {
        "id": "valid_postal_code",
        "label": "Code postal invalide (5 chiffres, dept valide)",
        "severity": "warning",
        "check": check_valid_postal_code,
    },
    {
        "id": "valid_date_format",
        "label": "Format date invalide",
        "severity": "warning",
        "check": check_valid_dates,
    },
    # Step 20: multi-entité / bâtiment
    {
        "id": "invalid_siren_entite",
        "label": "SIREN entité invalide (9 chiffres)",
        "severity": "warning",
        "check": check_invalid_siren_entite,
    },
    {
        "id": "orphan_portefeuille",
        "label": "Portefeuille sans entité (rattaché par défaut)",
        "severity": "info",
        "check": check_orphan_portefeuille,
    },
    {
        "id": "batiment_sans_surface",
        "label": "Bâtiment sans surface",
        "severity": "info",
        "check": check_batiment_sans_surface,
    },
]


def run_all_rules(db: Session, batch_id: int) -> List[dict]:
    """Execute all quality rules and return findings (not yet persisted)."""
    all_findings = []
    for rule in QUALITY_RULES:
        rule_findings = rule["check"](db, batch_id)
        all_findings.extend(rule_findings)
    return all_findings
