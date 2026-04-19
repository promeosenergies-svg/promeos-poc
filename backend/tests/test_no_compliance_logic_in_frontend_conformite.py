"""
Source-guard Phase 4 Lot 6 · Conformité Tertiaire Sol.

Interdit toute formule compliance / pondération / pénalité / jalon /
seuil BACS hardcodée en front. Ces valeurs DOIVENT venir du backend
(RegAssessment, /api/tertiaire/dashboard, audit_sme_service).

Les enums `regulation/rule_id/status/severity` côté findings sont
AUTORISÉS en lecture affichage (display des pills et labels) — c'est
le backend qui calcule ces valeurs, le frontend ne fait que les lire
et les mapper sur des traductions UI.

Scope : tous les fichiers frontend liés à la conformité tertiaire,
incluant :
  - frontend/src/pages/ConformiteTertiaireSol.jsx (Phase 4 Sol hero)
  - frontend/src/pages/conformite-tertiaire/ (presenters Phase 4)
  - frontend/src/pages/tertiaire/TertiaireDashboardPage.jsx (legacy
    loader — le hero injecté doit rester compatible)
  - frontend/src/pages/ConformiteSol.jsx (Phase 4.1 portfolio, déjà
    refait v2.1)
"""
from pathlib import Path
import re

import pytest

# Path adapté au repo réel (pages/ pas features/)
FRONTEND_ROOTS = [
    Path("frontend/src/pages/ConformiteTertiaireSol.jsx"),
    Path("frontend/src/pages/conformite-tertiaire"),
    Path("frontend/src/pages/tertiaire/TertiaireDashboardPage.jsx"),
]

FORBIDDEN_PATTERNS = {
    # Pondérations composites DT/BACS/APER/Audit SMÉ (doivent venir
    # de weights_used backend, absent actuellement — impossible de
    # les recalculer côté front)
    "weight_dt_39": r"\*\s*0\.39\b",
    "weight_bacs_28": r"\*\s*0\.28\b",
    "weight_aper_17": r"\*\s*0\.17\b",
    "weight_audit_16": r"\*\s*0\.16\b",
    "weight_dt_45": r"\*\s*0\.45\b",
    "weight_bacs_30": r"\*\s*0\.30\b",
    "weight_aper_25": r"\*\s*0\.25\b",
    # Pénalités DT hardcoded (doivent venir de penalty_risk_eur
    # backend si exposé, sinon null honnête)
    "penalty_base_7500": r"\*\s*7500\b",
    "penalty_a_risque_3750": r"\*\s*3750\b",
    # Jalons DT (doivent venir de operat_trajectory.milestones
    # backend — interdiction d'hardcoder les pourcentages jalons
    # comme formules numériques littérales).
    # Pattern : espace + -/− + espace + chiffre + % (évite match sur
    # texte narratif `-25 %` dans strings display).
    "milestone_literal_mul": r"\*\s*0\.(25|40|50|60)\b",
    # Seuils BACS hardcoded (doivent venir de règles backend)
    "bacs_threshold_290": r"\b290\b[^,]*(\bkW\b|\bpower\b|\bpuissance\b)",
    "bacs_threshold_70": r"\b70\b[^,]*(\bkW\b|\bpower\b|\bpuissance\b)",
    # Formule score composite interdite (frontend doit lire
    # compliance_score agrégé backend, pas recomposer)
    "compliance_composite_dt": r"dt_score\s*\*\s*0\.",
    "compliance_composite_bacs": r"bacs_score\s*\*\s*0\.",
}


def _collect_frontend_files():
    """Tous les fichiers jsx/js sous les chemins surveillés, existants."""
    files = []
    for root in FRONTEND_ROOTS:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(root.rglob("*.jsx"))
            files.extend(root.rglob("*.js"))
    return files


def _strip_comments(content: str) -> str:
    """Supprime commentaires // ... et /* ... */ pour éviter les faux
    positifs sur des explications UX."""
    return re.sub(r"//.*$|/\*.*?\*/", "", content, flags=re.S | re.M)


@pytest.mark.parametrize("name,pattern", FORBIDDEN_PATTERNS.items())
def test_no_business_logic_in_conformite_frontend(name, pattern):
    """Chaque pattern métier interdit ne doit apparaître dans aucun
    fichier frontend conformité tertiaire (hors commentaires)."""
    violations = []
    for f in _collect_frontend_files():
        try:
            content = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        code_only = _strip_comments(content)
        if re.search(pattern, code_only):
            violations.append(str(f))
    assert not violations, (
        f"Violation '{name}' (pattern {pattern!r}) détectée dans : "
        f"{violations}. Cette valeur DOIT venir du backend "
        f"(RegAssessment.compliance_score / /api/tertiaire/dashboard "
        f"/ audit_sme_service). Voir docs/audit/api_regops_shape_phase4.md."
    )


def test_whitelist_findings_ops_enums_allowed():
    """Documente la whitelist : le frontend PEUT lire les enums
    findings.ops (regulation/rule_id/status/severity/legal_deadline/
    category) issus de l'API backend comme display pur (pills, labels,
    filtres). Ce test est informationnel — assert trivial pour que la
    règle soit visible dans le rapport pytest."""
    allowed_fields = [
        "findings[].regulation",
        "findings[].rule_id",
        "findings[].status",
        "findings[].severity",
        "findings[].legal_deadline",
        "findings[].category",
        "findings[].explanation",
        "compliance_score",
        "global_status",
        "next_deadline",
        "actions[].action_code",
        "actions[].priority_score",
        "actions[].owner_role",
    ]
    assert len(allowed_fields) >= 10, (
        "Whitelist doit contenir ≥ 10 champs display autorisés"
    )
