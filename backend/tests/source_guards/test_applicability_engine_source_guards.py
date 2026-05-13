"""PROMEOS — Source-guards Phase 3.5 Vague A.7.

Référence : `docs/adr/ADR-024-moteur-assujettissement.md` §8.

Verrous anti-régression pour le moteur d'assujettissement :

  G1. Tout `reason_code` produit par un évaluateur doit appartenir
      à `regulatory.reason_codes.REASON_CODES`. Empêche un évaluateur de
      réintroduire un code arbitraire au fil des correctifs.

  G2. Le code Phase 3.5 (regulatory/, services/strategique/, builders…)
      n'importe PAS le legacy `services.compliance_readiness_service
      .compute_applicability` (décision Phase 0 Q2 Amine).

  G3. Aucun reason_code hardcodé dans un fichier hors `regulatory.rules.*`
      (les builders Vague C doivent lire `RuleApplicability.reason_code`,
      jamais comparer à des littéraux).

  G4. Tout évaluateur enregistré dans `RULES_VERSIONS` a une `version`
      non vide et datée (format minimum : "<RULE>-<source>-v<DATE>").

  G5. DATA_MISSING ne peut jamais avoir un `missing_inputs` vide
      (verrouillé au niveau type via __post_init__, mais on revérifie
      qu'aucun évaluateur ne tente de contourner via paramètres anormaux).
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REGULATORY_DIR = REPO_ROOT / "regulatory"


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def all_evaluator_outputs(monkeypatch):
    """Cas combinatoires couvrant les 4 statuts × 5 règles via SimpleNamespace.

    IMPORTANT : utilise pytest `monkeypatch` (function-scoped) pour restaurer
    les loaders du service après le test, sinon les tests suivants (ex.
    test_endpoint_applicability) héritent du mock et cassent leur fixture DB.
    """
    from types import SimpleNamespace

    from regulatory.applicability_service import compute_applicability

    sites_data = [
        dict(
            id=1,
            nom="big",
            tertiaire_area_m2=2000,
            usage_principal="BUREAUX",
            parking_area_m2=2000,
            roof_area_m2=600,
            batiments=[SimpleNamespace(id=100, cvc_power_kw=120)],
        ),
        dict(
            id=2,
            nom="small",
            tertiaire_area_m2=500,
            usage_principal="BUREAUX",
            parking_area_m2=800,
            roof_area_m2=200,
            batiments=[SimpleNamespace(id=200, cvc_power_kw=30)],
        ),
        dict(
            id=3,
            nom="mixte",
            tertiaire_area_m2=2500,
            usage_principal="MIXTE",
            parking_area_m2=None,
            roof_area_m2=None,
            batiments=[SimpleNamespace(id=300, cvc_power_kw=None)],
        ),
        dict(
            id=4, nom="incomplet", tertiaire_area_m2=None, usage_principal="BUREAUX", parking_area_m2=2000, batiments=[]
        ),
    ]
    sites = [SimpleNamespace(**d) for d in sites_data]
    org = SimpleNamespace(id=1, nom="OrgTest", effectif_total=380, chiffre_affaires_eur=80_000_000.0, pays="FR")
    audit_sme = SimpleNamespace(conso_annuelle_moy_gwh=5.0)

    monkeypatch.setattr(
        "regulatory.applicability_service._load_sites",
        lambda db, oid, sids: sites if sids is None else [s for s in sites if s.id in sids],
    )
    monkeypatch.setattr(
        "regulatory.applicability_service._load_organisation",
        lambda db, oid: org,
    )
    monkeypatch.setattr(
        "regulatory.applicability_service._load_audit_sme",
        lambda db, oid: audit_sme,
    )
    monkeypatch.setattr(
        "regulatory.applicability_service._load_batiments_for_site",
        lambda db, site: list(getattr(site, "batiments", [])),
    )
    return compute_applicability(db=None, org_id=1)


# ── G1 : reason_code whitelist ────────────────────────────────────────────


def test_g1_all_reason_codes_in_whitelist(all_evaluator_outputs):
    """Aucun évaluateur ne doit émettre un reason_code hors whitelist."""
    from regulatory.reason_codes import REASON_CODES

    leak: list[str] = []
    for rule_code, entries in all_evaluator_outputs.items():
        for entry in entries:
            if entry.reason_code not in REASON_CODES:
                leak.append(f"{rule_code.value}: {entry.reason_code}")
    assert not leak, f"reason_codes hors whitelist: {leak}"


# ── G2 : interdiction d'import legacy ─────────────────────────────────────


def test_g2_regulatory_pkg_no_legacy_compliance_import():
    """Le package regulatory/ ne doit JAMAIS importer compliance_readiness_service.

    Décision Phase 0 Q2 (Amine 2026-05-13) : cohabitation par chemin distinct.
    """
    pattern = re.compile(
        r"from\s+services\.compliance_readiness_service\s+import|"
        r"import\s+services\.compliance_readiness_service"
    )
    violations: list[Path] = []
    for py in REGULATORY_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            violations.append(py.relative_to(REPO_ROOT))
    assert not violations, (
        f"Import legacy compliance_readiness_service détecté: {violations}. "
        "Décision Phase 0 Q2 : cohabitation par chemin distinct."
    )


def test_g2_regulatory_route_no_legacy_import():
    """L'endpoint /api/regulatory/applicability ne doit pas importer le legacy."""
    route = REPO_ROOT / "routes" / "regulatory_applicability.py"
    text = route.read_text(encoding="utf-8")
    assert "compliance_readiness_service.compute_applicability" not in text


# ── G3 : pas de reason_code hardcodé hors regulatory/ ────────────────────


_REASON_CODE_LITERAL_RE = re.compile(
    r'"(?:DT|BACS|APER|SME|BEGES)\.(?:APPLICABLE|NOT_APPLICABLE|UNKNOWN|DATA_MISSING)\.[A-Z_]+"'
)


def test_g3_no_reason_code_hardcoded_outside_regulatory():
    """Le code Phase 3.5 hors regulatory/ ne doit pas comparer à des littéraux reason_code.

    Allowed paths : regulatory/, tests/, docs/ (commentaires).
    Tout autre fichier qui contient `"DT.APPLICABLE"` etc. risque de drifter
    si la whitelist évolue. Doit lire `RuleApplicability.reason_code` à la place.
    """
    allowed_substrings = ("/regulatory/", "/tests/", "/docs/", "__pycache__")
    violations: list[tuple[Path, str]] = []
    for py in REPO_ROOT.rglob("*.py"):
        rel = str(py)
        if any(a in rel for a in allowed_substrings):
            continue
        text = py.read_text(encoding="utf-8", errors="ignore")
        match = _REASON_CODE_LITERAL_RE.search(text)
        if match:
            violations.append((py.relative_to(REPO_ROOT), match.group(0)))
    assert not violations, (
        f"reason_code hardcodés détectés hors regulatory/: {violations}. Lire RuleApplicability.reason_code à la place."
    )


# ── G4 : versions évaluateurs ────────────────────────────────────────────


_VERSION_RE = re.compile(r"^[A-Z]+(?:[-+][\w.\-+]+)+\d{4}-\d{2}-\d{2}$")


def test_g4_evaluators_have_dated_version():
    """Chaque RULES_VERSIONS doit suivre un format minimal '<RULE>-...<YYYY-MM-DD>'."""
    from regulatory.rules_catalog import RULES_VERSIONS

    bad: list[tuple[str, str]] = []
    for rule, version in RULES_VERSIONS.items():
        if not version:
            bad.append((rule.value, "<empty>"))
            continue
        if not _VERSION_RE.match(version):
            bad.append((rule.value, version))
    assert not bad, f"Versions évaluateurs au format non canonique: {bad}"


# ── G5 : DATA_MISSING vs missing_inputs ──────────────────────────────────


def test_g5_data_missing_always_has_inputs(all_evaluator_outputs):
    """DATA_MISSING doit toujours avoir missing_inputs non vide.

    Renforce la garde __post_init__ (couvre régression future éventuelle si
    quelqu'un appelait via dict(...) au lieu du dataclass constructor).
    """
    from regulatory.applicability_types import ApplicabilityStatus

    for rule_code, entries in all_evaluator_outputs.items():
        for entry in entries:
            if entry.status == ApplicabilityStatus.DATA_MISSING:
                assert entry.missing_inputs, (
                    f"DATA_MISSING sans missing_inputs pour {rule_code.value}: {entry.reason_code}"
                )


# ── G7 (Phase 3.8 QQ) : bijection reason_codes ────────────────────────────


def test_g7_reason_codes_whitelist_subset_of_source():
    """Phase 3.8 — bijection : tout code de la whitelist REASON_CODES doit
    être détecté comme littéral dans au moins un fichier regulatory/rules/*.

    Garde-fou contre les codes whitelistés mais jamais émis (zombies),
    identifiés par audit regulatory-expert Phase 3.5 sur :
      - SME.DATA_MISSING.CA, SME.DATA_MISSING.CONSO
      - APER.DATA_MISSING.ROOF_AREA
    Bijection résolue Phase 3.7 KK (codes émis) + Phase 3.8 QQ (verrou).
    """
    import re as _re

    from regulatory.reason_codes import REASON_CODES

    rules_dir = REGULATORY_DIR / "rules"
    all_sources = ""
    for py in rules_dir.rglob("*.py"):
        all_sources += py.read_text(encoding="utf-8", errors="ignore")
    orphan_codes: list[str] = []
    for code in sorted(REASON_CODES):
        # Le code doit apparaître comme chaîne entre guillemets dans au moins un
        # fichier d'évaluateur.
        if not _re.search(rf'["\']({_re.escape(code)})["\']', all_sources):
            orphan_codes.append(code)
    assert not orphan_codes, (
        f"Codes whitelistés jamais émis (orphelins) : {orphan_codes}. "
        "La whitelist doit être en bijection avec les codes effectivement "
        "produits par les évaluateurs."
    )


# ── G6 : RuleEvaluator.scope cohérent ────────────────────────────────────


def test_g6_evaluator_scope_consistent_with_rule():
    """Vérifie cohérence scope (site vs organisation) par règle v1.0."""
    from regulatory.applicability_types import RuleCode
    from regulatory.rules_catalog import RULE_EVALUATORS

    expected_scope = {
        RuleCode.DT: "site",
        RuleCode.BACS: "site",
        RuleCode.APER: "site",
        RuleCode.SME: "organisation",
        RuleCode.BEGES: "organisation",
    }
    for rule, evaluator in RULE_EVALUATORS.items():
        assert evaluator.scope == expected_scope[rule], (
            f"scope mismatch pour {rule.value}: attendu {expected_scope[rule]}, reçu {evaluator.scope}"
        )
