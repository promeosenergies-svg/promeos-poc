"""
PROMEOS - Quality Rules Engine (DIAMANT)
5 deterministic rules for staging data quality gate.
"""
from difflib import SequenceMatcher
from typing import List

from sqlalchemy.orm import Session

from models import (
    StagingSite, StagingCompteur, Site, Compteur, EntiteJuridique,
    QualityFinding, QualityRuleSeverity, not_deleted,
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
    staging_sites = db.query(StagingSite).filter(
        StagingSite.batch_id == batch_id,
        StagingSite.skip.is_(False),
    ).all()

    # Intra-staging duplicates
    for i, s1 in enumerate(staging_sites):
        for s2 in staging_sites[i + 1:]:
            if s1.code_postal and s2.code_postal and s1.code_postal == s2.code_postal:
                sim = _similarity(s1.adresse or "", s2.adresse or "")
                if sim > 0.8:
                    findings.append({
                        "rule_id": "dup_site_address",
                        "severity": QualityRuleSeverity.WARNING,
                        "staging_site_id": s1.id,
                        "evidence_json": (
                            f'{{"dup_with_staging_id": {s2.id}, '
                            f'"similarity": {sim:.2f}, '
                            f'"site_a": "{s1.nom}", "site_b": "{s2.nom}"}}'
                        ),
                        "suggested_action": "merge",
                    })

    # Vs existing sites (limit to 500 for perf)
    existing_sites = not_deleted(db.query(Site), Site).filter(Site.actif.is_(True)).limit(500).all()
    for ss in staging_sites:
        for ex in existing_sites:
            if ss.code_postal and ex.code_postal and ss.code_postal == ex.code_postal:
                sim = _similarity(ss.adresse or "", ex.adresse or "")
                if sim > 0.8:
                    findings.append({
                        "rule_id": "dup_site_address",
                        "severity": QualityRuleSeverity.WARNING,
                        "staging_site_id": ss.id,
                        "evidence_json": (
                            f'{{"dup_with_existing_id": {ex.id}, '
                            f'"similarity": {sim:.2f}, '
                            f'"staging_name": "{ss.nom}", "existing_name": "{ex.nom}"}}'
                        ),
                        "suggested_action": "merge",
                    })

    return findings


def check_duplicate_meters(db: Session, batch_id: int) -> List[dict]:
    """Rule: dup_meter — staging compteurs with same PRM/PDL/PCE or numero_serie."""
    findings = []
    staging_compteurs = db.query(StagingCompteur).filter(
        StagingCompteur.batch_id == batch_id,
        StagingCompteur.skip.is_(False),
    ).all()

    # Intra-staging
    seen_serie = {}
    seen_meter = {}
    for sc in staging_compteurs:
        if sc.numero_serie:
            if sc.numero_serie in seen_serie:
                findings.append({
                    "rule_id": "dup_meter",
                    "severity": QualityRuleSeverity.BLOCKING,
                    "staging_compteur_id": sc.id,
                    "evidence_json": (
                        f'{{"dup_with_staging_id": {seen_serie[sc.numero_serie]}, '
                        f'"field": "numero_serie", "value": "{sc.numero_serie}"}}'
                    ),
                    "suggested_action": "skip",
                })
            else:
                seen_serie[sc.numero_serie] = sc.id

        if sc.meter_id:
            if sc.meter_id in seen_meter:
                findings.append({
                    "rule_id": "dup_meter",
                    "severity": QualityRuleSeverity.BLOCKING,
                    "staging_compteur_id": sc.id,
                    "evidence_json": (
                        f'{{"dup_with_staging_id": {seen_meter[sc.meter_id]}, '
                        f'"field": "meter_id", "value": "{sc.meter_id}"}}'
                    ),
                    "suggested_action": "skip",
                })
            else:
                seen_meter[sc.meter_id] = sc.id

    # Vs existing compteurs
    existing_compteurs = not_deleted(db.query(Compteur), Compteur).filter(Compteur.actif.is_(True)).all()
    existing_series = {c.numero_serie for c in existing_compteurs if c.numero_serie}
    existing_meters = {c.meter_id for c in existing_compteurs if c.meter_id}

    for sc in staging_compteurs:
        if sc.numero_serie and sc.numero_serie in existing_series:
            findings.append({
                "rule_id": "dup_meter",
                "severity": QualityRuleSeverity.BLOCKING,
                "staging_compteur_id": sc.id,
                "evidence_json": (
                    f'{{"dup_with_existing": true, '
                    f'"field": "numero_serie", "value": "{sc.numero_serie}"}}'
                ),
                "suggested_action": "merge",
            })
        if sc.meter_id and sc.meter_id in existing_meters:
            findings.append({
                "rule_id": "dup_meter",
                "severity": QualityRuleSeverity.BLOCKING,
                "staging_compteur_id": sc.id,
                "evidence_json": (
                    f'{{"dup_with_existing": true, '
                    f'"field": "meter_id", "value": "{sc.meter_id}"}}'
                ),
                "suggested_action": "merge",
            })

    return findings


def check_orphan_meters(db: Session, batch_id: int) -> List[dict]:
    """Rule: orphan_meter — staging compteur without any site association."""
    findings = []
    orphans = db.query(StagingCompteur).filter(
        StagingCompteur.batch_id == batch_id,
        StagingCompteur.skip.is_(False),
        StagingCompteur.staging_site_id.is_(None),
        StagingCompteur.target_site_id.is_(None),
    ).all()

    for sc in orphans:
        findings.append({
            "rule_id": "orphan_meter",
            "severity": QualityRuleSeverity.BLOCKING,
            "staging_compteur_id": sc.id,
            "evidence_json": (
                f'{{"numero_serie": "{sc.numero_serie or ""}", '
                f'"meter_id": "{sc.meter_id or ""}"}}'
            ),
            "suggested_action": "remap",
        })

    return findings


def check_incomplete_sites(db: Session, batch_id: int) -> List[dict]:
    """Rule: incomplete_site — staging site missing address or postal code."""
    findings = []
    sites = db.query(StagingSite).filter(
        StagingSite.batch_id == batch_id,
        StagingSite.skip.is_(False),
    ).all()

    for ss in sites:
        missing = []
        if not ss.adresse:
            missing.append("adresse")
        if not ss.code_postal:
            missing.append("code_postal")
        if missing:
            findings.append({
                "rule_id": "incomplete_site",
                "severity": QualityRuleSeverity.WARNING,
                "staging_site_id": ss.id,
                "evidence_json": f'{{"missing_fields": {missing}, "site_name": "{ss.nom}"}}',
                "suggested_action": "fix_address",
            })

    return findings


def check_missing_entity(db: Session, batch_id: int) -> List[dict]:
    """Rule: missing_entite — staging site has SIRET but no matching EntiteJuridique."""
    findings = []
    sites_with_siret = db.query(StagingSite).filter(
        StagingSite.batch_id == batch_id,
        StagingSite.skip.is_(False),
        StagingSite.siret.isnot(None),
    ).all()

    if not sites_with_siret:
        return findings

    # Get all known SIRENs (first 9 digits of SIRET)
    known_sirens = {
        ej.siren for ej in db.query(EntiteJuridique).all() if ej.siren
    }

    for ss in sites_with_siret:
        siren = ss.siret[:9] if len(ss.siret) >= 9 else ss.siret
        if siren not in known_sirens:
            findings.append({
                "rule_id": "missing_entite",
                "severity": QualityRuleSeverity.INFO,
                "staging_site_id": ss.id,
                "evidence_json": (
                    f'{{"siret": "{ss.siret}", "siren_extracted": "{siren}", '
                    f'"site_name": "{ss.nom}"}}'
                ),
                "suggested_action": "create_entite",
            })

    return findings


# ========================================
# Rules registry
# ========================================

QUALITY_RULES = [
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
]


def run_all_rules(db: Session, batch_id: int) -> List[dict]:
    """Execute all quality rules and return findings (not yet persisted)."""
    all_findings = []
    for rule in QUALITY_RULES:
        rule_findings = rule["check"](db, batch_id)
        all_findings.extend(rule_findings)
    return all_findings
