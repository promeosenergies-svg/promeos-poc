"""
Source-guard Phase 5 Lot 6 · Compliance Pipeline Sol.

Interdit toute formule pondération / seuil trust / bucket deadline /
enum gate hardcodé en front. Ces valeurs DOIVENT venir du backend
(endpoint `GET /api/compliance/portfolio/summary`, section 3 du
pré-flight `docs/audit/api_compliance_pipeline_phase5.md`).

Le front lit :
  - `kpis.{data_blocked, data_warning, data_ready}` (agrégats ORG)
  - `deadlines.{d30, d90, d180, beyond}` (buckets PRÉ-CALCULÉS — jamais
    recalculer côté client sur `days_remaining`)
  - `untrusted_sites[]` (LISTE PRÉ-FILTRÉE — jamais redéfinir seuil
    `trust_score < N` côté client)
  - `sites[].gate_status` (ENUM affiché — jamais réassigner
    `gate_status = 'OK'` côté client)

Les enums display (gate_status, regulation, statut, site_nom) restent
autorisés en lecture pour pills / labels / filtres.

Scope : nouveaux paths Sol Phase 5 uniquement. La page legacy
`CompliancePipelinePage.jsx` sera wrapped `{false && (…)}` en P5.3 et
reste hors scope (ses thresholds existants n'atteignent jamais le
rendu post-Sol).
"""
from pathlib import Path
import re

import pytest

FRONTEND_ROOTS = [
    Path("frontend/src/pages/CompliancePipelineSol.jsx"),
    Path("frontend/src/pages/compliance-pipeline"),
]

FORBIDDEN_PATTERNS = {
    # 1. Pondération reg_risk client-side interdite — reg_risk arrive
    # déjà pondéré backend, pas de multiplication supplémentaire.
    "reg_risk_weight_mul": r"reg_risk\s*[+*]\s*0\.[0-9]",

    # 2. Assignation littérale compliance_score — le score vient
    # agrégé backend, jamais recomposé front.
    "compliance_score_literal_assign": r"compliance_score\s*=\s*[0-9]{2}",

    # 3. Seuils completeness_pct hardcodés — gate_status backend
    # encapsule déjà le seuillage (OK/WARNING/BLOCKED).
    "completeness_pct_threshold": r"completeness_pct\s*[><]=?\s*(50|75|80|90|100)",

    # 4. REINFORCEMENT user : seuil trust_score côté front interdit.
    # La liste des sites untrusted arrive pré-filtrée backend via
    # `untrusted_sites[]`. Le front lit la longueur du tableau, pas
    # une comparaison numérique.
    "trust_score_threshold": r"trust_score\s*[<>]=?\s*[0-9]+",

    # 5. Agrégat multiplicatif financial_opportunity — le backend
    # fournit le total par site, pas de calcul fantôme.
    "financial_opportunity_mul": r"financial_opportunity_eur\s*\*",

    # 6. REINFORCEMENT user : buckets days_remaining côté front
    # interdits. Les arrays `deadlines.d30 / d90 / d180 / beyond`
    # sont déjà partitionnés backend — le front itère dessus,
    # jamais ne compare `days_remaining < 30` lui-même.
    "days_remaining_bucket": r"days_remaining\s*[<>]=?\s*(30|60|90|180)",

    # 7. REINFORCEMENT user : assignation gate_status interdite
    # côté front. L'enum `OK/WARNING/BLOCKED` est sourcé backend,
    # pas recomposé depuis completeness ou autre.
    "gate_status_literal_assign": r"gate_status\s*=\s*['\"](OK|WARNING|BLOCKED)['\"]",

    # 8. Dates DT/BACS/APER hardcodées dans formules — les
    # échéances arrivent via `deadlines[].deadline` backend.
    # Pattern : comparaison ou arithmétique sur une date littérale
    # ISO d'une des années réglementaires (2025/2028/2030).
    "hardcoded_regulation_date": r"['\"](2025|2028|2030)-(01|07|09|12)-[0-9]{2}['\"]",
}


def _collect_frontend_files():
    files = []
    for root in FRONTEND_ROOTS:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(root.rglob("*.jsx"))
            files.extend(root.rglob("*.js"))
    # Exclure les tests eux-mêmes (ils contiennent les regex des
    # patterns interdits comme strings de validation).
    return [
        f for f in files
        if "__tests__" not in f.parts
        and not f.name.endswith(".test.js")
        and not f.name.endswith(".test.jsx")
    ]


def _strip_comments(content: str) -> str:
    """Supprime commentaires // ... et /* ... */ pour éviter faux
    positifs sur docstrings d'explication."""
    return re.sub(r"//.*$|/\*.*?\*/", "", content, flags=re.S | re.M)


@pytest.mark.parametrize("name,pattern", FORBIDDEN_PATTERNS.items())
def test_no_compliance_logic_in_pipeline_frontend(name, pattern):
    """Chaque pattern métier interdit ne doit apparaître dans aucun
    fichier frontend compliance pipeline Sol (hors commentaires)."""
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
        f"{violations}. Cette valeur DOIT venir du backend (endpoint "
        f"/api/compliance/portfolio/summary). Voir "
        f"docs/audit/api_compliance_pipeline_phase5.md section 5."
    )


def test_whitelist_pipeline_enums_allowed():
    """Documente la whitelist Phase 5 : le frontend PEUT lire les
    enums display (gate_status, regulation, statut, site_nom,
    applicability.{tertiaire_operat,bacs,aper}) issus de l'API
    portfolio/summary comme display pur. Ce sont des enums
    backend-sourced, pas des formules."""
    allowed_display_fields = [
        "sites[].gate_status",           # OK/WARNING/BLOCKED enum
        "sites[].site_nom",              # string display
        "sites[].completeness_pct",      # lecture pure (pas seuillage)
        "sites[].compliance_score",      # lecture pure (pas assign)
        "sites[].reg_risk",              # lecture pure (pas *0.X)
        "sites[].financial_opportunity_eur",  # lecture pure
        "sites[].applicability.tertiaire_operat",
        "sites[].applicability.bacs",
        "sites[].applicability.aper",
        "kpis.data_blocked",
        "kpis.data_warning",
        "kpis.data_ready",
        "deadlines.d30[]",   # array pré-bucketé backend
        "deadlines.d90[]",
        "deadlines.d180[]",
        "deadlines.beyond[]",
        "untrusted_sites[]",  # array pré-filtré backend
        "total_sites",
    ]
    assert len(allowed_display_fields) >= 15, (
        "Whitelist doit contenir ≥ 15 champs display autorisés"
    )
