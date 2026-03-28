"""
PROMEOS — A.2: Service de score conformite unifie — SOURCE UNIQUE.

Source unique pour le score conformite 0-100 (higher = better) affiche dans l'UI.
Agrege les 3 obligations reglementaires applicables :
  - Decret Tertiaire (45%)
  - BACS (30%)
  - APER (25%)

Les CEE, qui relevent du financement, ne sont pas inclus dans le score.

Formule :
  score = moyenne_ponderee(DT 45% + BACS 30% + APER 25%)
          - penalite_findings_critiques (max -20 pts)

Grade : A >= 85, B >= 70, C >= 50, D >= 30, F < 30
Seuils UI : conforme >= 70, a risque >= 40, non conforme < 40

Confidence :
  - "high"   : 3/3 frameworks evalues
  - "medium" : 2/3 frameworks evalues
  - "low"    : 0-1 framework evalue

Autres scores dans le codebase (ne pas confondre) :
  - bacs_engine.py : sub-score BACS (composante, pas le score global)
  - compliance_engine.py : legacy 100-risk_score (non affiche, backward compat)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import yaml
from sqlalchemy.orm import Session

_logger = logging.getLogger(__name__)

# ── Chargement config scoring depuis regs.yaml (A7 — source de vérité unique) ─
_REGS_PATH = Path(__file__).resolve().parent.parent / "regops" / "config" / "regs.yaml"


def _load_scoring_config() -> dict:
    """Charge la section scoring de regs.yaml. Fallback hardcodé si fichier absent."""
    try:
        with open(_REGS_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("scoring", {})
    except Exception as exc:
        _logger.warning("regs.yaml introuvable ou invalide (%s), fallback hardcodé", exc)
        return {}


_scoring_cfg = _load_scoring_config()

# ── Poids des frameworks (DT + BACS + APER = 100%) ─────────────────────────
# Source de vérité : regs.yaml > scoring > framework_weights
FRAMEWORK_WEIGHTS: dict[str, float] = _scoring_cfg.get(
    "framework_weights",
    {
        "tertiaire_operat": 0.45,
        "bacs": 0.30,
        "aper": 0.25,
    },
)

# ── Pénalité findings critiques ─────────────────────────────────────────────
_crit_cfg = _scoring_cfg.get("critical_penalty", {})
MAX_CRITICAL_PENALTY: float = float(_crit_cfg.get("max_pts", 20.0))
CRITICAL_PENALTY_PER_FINDING: float = float(_crit_cfg.get("per_finding_pts", 5.0))


@dataclass
class FrameworkScore:
    """Score d'un framework réglementaire individuel."""

    framework: str
    score: float  # 0-100 (higher = better)
    weight: float  # poids dans le composite
    available: bool  # True si RegAssessment existe
    source: str  # "regops" | "snapshot" | "default"


@dataclass
class ComplianceScoreResult:
    """Résultat du score conformité unifié."""

    score: float  # 0-100 composite (higher = better)
    breakdown: list[FrameworkScore] = field(default_factory=list)
    critical_penalty: float = 0.0  # pts soustraits pour findings critiques
    confidence: str = "low"  # "high" | "medium" | "low"
    frameworks_evaluated: int = 0
    frameworks_total: int = 3
    last_computed: Optional[str] = None
    formula: str = "Moyenne pondérée (Tertiaire 45% + BACS 30% + APER 25%) − pénalité findings critiques (max −20 pts)"

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "breakdown": [asdict(f) for f in self.breakdown],
            "critical_penalty": self.critical_penalty,
            "confidence": self.confidence,
            "frameworks_evaluated": self.frameworks_evaluated,
            "frameworks_total": self.frameworks_total,
            "last_computed": self.last_computed,
            "formula": self.formula,
        }


def _status_to_score(status_str: str) -> float:
    """Convertit un statut enum en score 0-100."""
    mapping = {
        "COMPLIANT": 100.0,
        "CONFORME": 100.0,
        "AT_RISK": 50.0,
        "A_RISQUE": 50.0,
        "NON_COMPLIANT": 0.0,
        "NON_CONFORME": 0.0,
        "UNKNOWN": 50.0,
        "EN_COURS": 50.0,
        "DEROGATION": 80.0,
    }
    return mapping.get(str(status_str).upper().replace(" ", "_"), 50.0)


def _count_critical_findings(findings_json: Optional[str]) -> int:
    """Compte les findings de sévérité critique dans le JSON."""
    if not findings_json:
        return 0
    try:
        findings = json.loads(findings_json) if isinstance(findings_json, str) else findings_json
        if isinstance(findings, list):
            return sum(1 for f in findings if isinstance(f, dict) and str(f.get("severity", "")).lower() == "critical")
    except (json.JSONDecodeError, TypeError):
        pass
    return 0


def compute_site_compliance_score(db: Session, site_id: int) -> ComplianceScoreResult:
    """
    Score conformité unifié pour un site.

    Algorithme :
    1. Récupère RegAssessment pour chaque framework (DT, BACS, APER)
    2. Pour chaque framework : score du RegAssessment (ou fallback snapshot Site)
    3. Score composite = weighted_average(DT 45%, BACS 30%, APER 25%)
    4. Pénalité findings critiques : -5 pts par finding critique (max -20)
    5. Clamp [0, 100]
    """
    from models import RegAssessment, Site

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return ComplianceScoreResult(score=50.0, confidence="low")

    # Récupère les RegAssessments les plus récents par framework
    assessments = (
        db.query(RegAssessment)
        .filter(
            RegAssessment.object_type == "site",
            RegAssessment.object_id == site_id,
            RegAssessment.is_stale == False,
        )
        .order_by(RegAssessment.computed_at.desc())
        .all()
    )

    # Index par regulation (déterminé depuis findings_json ou deterministic_version)
    # Un RegAssessment peut contenir des findings de PLUSIEURS frameworks
    assessment_by_framework: dict[str, RegAssessment] = {}
    for a in assessments:
        detected = _detect_frameworks(a)
        for fw in detected:
            if fw not in assessment_by_framework:
                assessment_by_framework[fw] = a

    # Construire le breakdown
    breakdown: list[FrameworkScore] = []
    weighted_sum = 0.0
    total_weight = 0.0
    frameworks_evaluated = 0
    total_critical_findings = 0

    for fw_key, weight in FRAMEWORK_WEIGHTS.items():
        ra = assessment_by_framework.get(fw_key)

        if ra and ra.compliance_score is not None:
            fw_score = max(0.0, min(100.0, ra.compliance_score))
            source = "regops"
            available = True
            frameworks_evaluated += 1
            total_critical_findings += _count_critical_findings(ra.findings_json)
        else:
            # Fallback : findings réels puis snapshot Site (pour DT et BACS)
            fw_score = _fallback_site_score(site, fw_key, db=db)
            if fw_score is None:
                # Framework non applicable (all findings OUT_OF_SCOPE)
                fw_score = 0.0
                source = "not_applicable"
                available = False
            else:
                source = "snapshot" if fw_score != 50.0 else "default"
                available = source == "snapshot"
                if available:
                    frameworks_evaluated += 1

        breakdown.append(
            FrameworkScore(
                framework=fw_key,
                score=round(fw_score, 1),
                weight=weight,
                available=available,
                source=source,
            )
        )

        # Only include available frameworks in the weighted average
        if available:
            weighted_sum += fw_score * weight
            total_weight += weight

    # Score composite
    raw_score = weighted_sum / total_weight if total_weight > 0 else 50.0

    # Pénalité findings critiques
    critical_penalty = min(
        MAX_CRITICAL_PENALTY,
        total_critical_findings * CRITICAL_PENALTY_PER_FINDING,
    )
    final_score = round(max(0.0, min(100.0, raw_score - critical_penalty)), 1)

    # Confidence
    if frameworks_evaluated >= 3:
        confidence = "high"
    elif frameworks_evaluated >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    last_computed = None
    if assessments:
        last_computed = assessments[0].computed_at.isoformat() if assessments[0].computed_at else None

    result = ComplianceScoreResult(
        score=final_score,
        breakdown=breakdown,
        critical_penalty=critical_penalty,
        confidence=confidence,
        frameworks_evaluated=frameworks_evaluated,
        last_computed=last_computed,
    )

    _logger.info(
        "compliance_score site=%d: %.1f (confidence=%s, eval=%d/3, penalty=%.1f)",
        site_id,
        final_score,
        confidence,
        frameworks_evaluated,
        critical_penalty,
    )

    return result


def sync_site_unified_score(db: Session, site_id: int) -> ComplianceScoreResult:
    """Persiste le score A.2 sur Site.compliance_score_composite.

    Calcule le score unifié puis l'écrit dans les 3 champs dédiés du modèle Site.
    Doit être appelé après recompute_site() pour maintenir les deux chemins en sync.
    """
    from models import Site

    result = compute_site_compliance_score(db, site_id)
    site = db.query(Site).filter(Site.id == site_id).first()
    if site:
        site.compliance_score_composite = result.score
        site.compliance_score_breakdown_json = json.dumps([asdict(f) for f in result.breakdown])
        site.compliance_score_confidence = result.confidence
        db.flush()
        _logger.info(
            "sync_site_unified_score site=%d: persisted score=%.1f confidence=%s",
            site_id,
            result.score,
            result.confidence,
        )
    return result


def compute_portfolio_compliance(db: Session, org_id: int) -> dict:
    """
    Score conformité agrégé pour un portefeuille (moyenne pondérée par surface).

    Returns: {
        avg_score, min_score, max_score,
        total_sites, high_confidence_count,
        worst_sites: [{site_id, nom, score, confidence}],
        breakdown_avg: {tertiaire_operat, bacs, aper},
    }
    """
    from models import Site, Portefeuille, EntiteJuridique
    from models import not_deleted

    sites = (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id, Site.actif == True)
        .all()
    )

    if not sites:
        return {
            "avg_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "total_sites": 0,
            "high_confidence_count": 0,
            "worst_sites": [],
            "breakdown_avg": {},
        }

    results = []
    for site in sites:
        r = compute_site_compliance_score(db, site.id)
        results.append((site, r))

    # Moyenne pondérée par surface (fallback = poids égal)
    total_weight = 0.0
    weighted_score = 0.0
    fw_sums: dict[str, float] = {}
    fw_counts: dict[str, int] = {}

    for site, r in results:
        w = site.surface_m2 if site.surface_m2 and site.surface_m2 > 0 else 1000.0
        total_weight += w
        weighted_score += r.score * w

        for fs in r.breakdown:
            fw_sums[fs.framework] = fw_sums.get(fs.framework, 0.0) + fs.score
            fw_counts[fs.framework] = fw_counts.get(fs.framework, 0) + 1

    avg_score = round(weighted_score / total_weight, 1) if total_weight > 0 else 0.0
    scores = [r.score for _, r in results]

    worst = sorted(results, key=lambda x: x[1].score)[:5]
    worst_sites = [{"site_id": s.id, "nom": s.nom, "score": r.score, "confidence": r.confidence} for s, r in worst]

    breakdown_avg = {fw: round(fw_sums[fw] / fw_counts[fw], 1) for fw in fw_sums if fw_counts.get(fw, 0) > 0}

    high_conf = sum(1 for _, r in results if r.confidence == "high")

    return {
        "avg_score": avg_score,
        "min_score": min(scores) if scores else 0.0,
        "max_score": max(scores) if scores else 0.0,
        "total_sites": len(sites),
        "high_confidence_count": high_conf,
        "worst_sites": worst_sites,
        "breakdown_avg": breakdown_avg,
    }


def _detect_frameworks(assessment) -> list[str]:
    """Détecte TOUS les frameworks présents dans un RegAssessment.

    Un RegAssessment peut contenir des findings de plusieurs frameworks
    (DT + BACS + APER dans le même assessment).
    """
    detected: set[str] = set()

    # Essaie d'identifier via deterministic_version
    version = assessment.deterministic_version or ""
    for fw in FRAMEWORK_WEIGHTS:
        if fw in version.lower():
            detected.add(fw)

    # Scanner tous les findings dans findings_json
    if assessment.findings_json:
        try:
            findings = (
                json.loads(assessment.findings_json)
                if isinstance(assessment.findings_json, str)
                else assessment.findings_json
            )
            if isinstance(findings, list):
                for f in findings:
                    reg = str(f.get("regulation", "")).lower()
                    rule = str(f.get("rule_id", "")).lower()
                    combined = f"{reg} {rule}"
                    for fw in FRAMEWORK_WEIGHTS:
                        if fw in combined:
                            detected.add(fw)
                    # Détection spécifique APER (findings avec "parking", "toiture", "roof")
                    if "aper" in combined or "parking" in combined or "roof" in combined:
                        detected.add("aper")
                    # Détection spécifique BACS
                    if "bacs" in combined or "gtb" in combined:
                        detected.add("bacs")
        except (json.JSONDecodeError, TypeError):
            pass

    return list(detected)


def _fallback_site_score(site, fw_key: str, db: Session = None) -> float:
    """
    Fallback score depuis les ComplianceFinding réels, puis snapshots Site.

    Priorité :
    1. Findings réels (ComplianceFinding) → calcul basé sur % de règles OK
    2. Snapshot Site (legacy) → uniquement si aucun finding n'existe
    """
    # 1. Essayer les findings réels
    if db is not None:
        from models import ComplianceFinding

        # Map fw_key → regulation column values
        regulation_map = {
            "tertiaire_operat": ["decret_tertiaire_operat", "tertiaire_operat", "dt"],
            "bacs": ["bacs"],
            "aper": ["aper"],
        }
        reg_values = regulation_map.get(fw_key, [fw_key])

        findings = (
            db.query(ComplianceFinding)
            .filter(
                ComplianceFinding.site_id == site.id,
                ComplianceFinding.regulation.in_(reg_values),
            )
            .all()
        )
        if findings:
            # Exclude OUT_OF_SCOPE findings — they shouldn't affect the score
            relevant = [f for f in findings if str(f.status).upper() != "OUT_OF_SCOPE"]
            if not relevant:
                return None  # all findings are out-of-scope → framework not applicable

            total = len(relevant)
            ok_count = sum(1 for f in relevant if str(f.status).upper() == "OK")
            unknown_count = sum(1 for f in relevant if str(f.status).upper() in ("UNKNOWN", "EN_COURS"))
            # OK = full credit, UNKNOWN/EN_COURS = half credit, NOK = 0
            from datetime import date as _date

            overdue = sum(
                1 for f in relevant if str(f.status).upper() == "NOK" and f.deadline and f.deadline < _date.today()
            )
            base_score = ((ok_count + unknown_count * 0.5) / total) * 100.0 if total > 0 else 50.0
            overdue_penalty = overdue * 15.0  # -15pts per overdue NOK finding
            score = max(0.0, min(100.0, base_score - overdue_penalty))
            _logger.debug(
                "_fallback_site_score site=%d fw=%s: findings path (score=%.1f, ok=%d/%d, overdue=%d)",
                site.id,
                fw_key,
                score,
                ok_count,
                total,
                overdue,
            )
            return score

    # 2. Fallback legacy snapshot (si pas de findings)
    if fw_key == "tertiaire_operat" and site.statut_decret_tertiaire:
        score = _status_to_score(
            site.statut_decret_tertiaire.value
            if hasattr(site.statut_decret_tertiaire, "value")
            else str(site.statut_decret_tertiaire)
        )
        _logger.debug("_fallback_site_score site=%d fw=%s: legacy snapshot DT (score=%.1f)", site.id, fw_key, score)
        return score
    if fw_key == "bacs" and site.statut_bacs:
        score = _status_to_score(
            site.statut_bacs.value if hasattr(site.statut_bacs, "value") else str(site.statut_bacs)
        )
        _logger.debug("_fallback_site_score site=%d fw=%s: legacy snapshot BACS (score=%.1f)", site.id, fw_key, score)
        return score
    # APER n'a pas de snapshot dédié → score par défaut
    _logger.debug("_fallback_site_score site=%d fw=%s: default 50.0 (no data)", site.id, fw_key)
    return 50.0
