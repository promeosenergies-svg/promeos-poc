"""PROMEOS — Source-guards Phase 3.5 Vague C.7 (Synthèse Stratégique).

Référence : ADR-023 §6 (anti-patterns AP-stratX1 → AP-stratX8) + §7.

Verrous structurels :
  G1. routes/cockpit_strategique.py utilise resolve_org_id + compute_applicability
      + compute_strategic_mode (preuve d'utilisation effective)
  G2. AUCUN strategic_mode hardcodé dans routes/cockpit_strategique.py ni
      dans services/strategique/builders/*.py (le mode est calculé)
  G3. AUCUN nom de site spécifique en dur dans les builders
      (AP-stratX7 : interdiction "Toulouse Entrepôt", "MERIDIAN", etc. en
       littéral dans services/strategique/builders/*.py)
  G4. AUCUN import depuis routes/cockpit_v2.py ou services/cockpit_*.py
      dans le package strategique (discipline "from scratch")
  G5. La page CockpitStrategique.jsx (à venir Vague D) ne doit pas importer
      Cockpit.jsx legacy — verrou frontend différé Vague D.7
  G6. Anti-pattern AP-stratX5 : queue_p2_p3 dans [3, 5] et kpis == 3 + charts == 2
      (vérifié par tests/services/strategique/test_builders.py — référence ici)

Note : G3 utilise une whitelist de noms acceptables (HELIOS et MERIDIAN sont
des packs démo génériques, pas des noms réels — testés ailleurs).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGIQUE_DIR = REPO_ROOT / "services" / "strategique"
ROUTE = REPO_ROOT / "routes" / "cockpit_strategique.py"
BUILDERS_DIR = STRATEGIQUE_DIR / "builders"


# ── G1 : route consomme bien les helpers cardinaux ─────────────────────


def test_g1_route_uses_resolve_org_id():
    text = ROUTE.read_text(encoding="utf-8")
    assert "resolve_org_id" in text, "Route doit utiliser resolve_org_id (org-scoping P0)"


def test_g1_route_uses_compute_applicability():
    text = ROUTE.read_text(encoding="utf-8")
    assert "compute_applicability" in text, "Route doit utiliser compute_applicability (ADR-024)"


def test_g1_route_uses_compute_strategic_mode():
    text = ROUTE.read_text(encoding="utf-8")
    assert "compute_strategic_mode" in text, "Route doit utiliser compute_strategic_mode (ADR-023 §9)"


# ── G2 : pas de strategic_mode hardcodé ─────────────────────────────────


_HARDCODED_MODE_RE = re.compile(
    r'(?:return\s+|=\s+|payload\[["\']strategic_mode["\']\]\s*=\s*)\s*'
    r'["\'](?:regulatory_driven|performance_driven|procurement_driven|opportunity_driven|data_insufficient)["\']'
)


def test_g2_no_hardcoded_mode_in_route():
    text = ROUTE.read_text(encoding="utf-8")
    matches = _HARDCODED_MODE_RE.findall(text)
    assert not matches, f"Mode hardcodé dans la route: {matches}. Doit venir de compute_strategic_mode."


def test_g2_no_hardcoded_mode_outside_thresholds():
    """Les builders peuvent référencer leur StrategicMode.X (attribut classe)
    mais ne doivent JAMAIS retourner une chaîne mode hardcodée."""
    for py in STRATEGIQUE_DIR.rglob("*.py"):
        if py.name in ("mode_thresholds.py", "__init__.py"):
            continue
        text = py.read_text(encoding="utf-8")
        # interdit : return "performance_driven" (string literal)
        bad = re.findall(r'return\s+["\'](?:regulatory_driven|performance_driven|data_insufficient)["\']', text)
        assert not bad, f"Mode string hardcodé dans {py.relative_to(REPO_ROOT)}: {bad}"


# ── G3 : pas de noms de site/portefeuille en dur ───────────────────────


# Noms qu'on s'interdit (sites/clients/portefeuilles réels)
_FORBIDDEN_SITE_NAMES = (
    "Toulouse Entrepôt",
    "Lyon Bureaux",
    "Marseille Ecole",
    "Nice Hotel",
    "Bordeaux",
    "Levallois",
    "Gennevilliers",
    "HELIOS SAS",
    "MERIDIAN SAS",
    "BORÉAL",
)


def test_g3_no_site_name_hardcoded_in_builders():
    """Les builders v1.0 utilisent des labels génériques (« site phare »,
    « meilleur élève »). Aucun nom réel ne doit apparaître."""
    violations: list[tuple[Path, str]] = []
    for py in BUILDERS_DIR.rglob("*.py"):
        if py.name == "__init__.py":
            continue
        text = py.read_text(encoding="utf-8")
        for name in _FORBIDDEN_SITE_NAMES:
            if name in text:
                violations.append((py.relative_to(REPO_ROOT), name))
    assert not violations, (
        f"Noms de site/portefeuille hardcodés détectés: {violations}. "
        "Utiliser des labels génériques (« site phare »...) v1.0."
    )


# ── G4 : pas d'import legacy ────────────────────────────────────────────


_LEGACY_IMPORT_RE = re.compile(
    r"from\s+(?:routes\.cockpit_v2|services\.cockpit_)\w+\s+import|"
    r"import\s+(?:routes\.cockpit_v2|services\.cockpit_)"
)


def test_g4_strategique_pkg_no_legacy_cockpit_import():
    """Discipline « from scratch » Phase 3.5 : aucun import de cockpit_v2.py
    ou services/cockpit_*.py dans services/strategique/."""
    violations: list[Path] = []
    for py in STRATEGIQUE_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if _LEGACY_IMPORT_RE.search(text):
            violations.append(py.relative_to(REPO_ROOT))
    assert not violations, f"Import legacy cockpit_v2/cockpit_*.py détecté: {violations}"


def test_g4_route_no_legacy_cockpit_import():
    text = ROUTE.read_text(encoding="utf-8")
    assert not _LEGACY_IMPORT_RE.search(text), (
        "routes/cockpit_strategique.py ne doit pas importer cockpit_v2 ou services/cockpit_*.py"
    )


# ── G6 : LoI L11 — cardinalité 3 KPI + 2 charts + queue 3-5 ────────────


def test_g6_loi_l11_kpis_charts_cardinality():
    """Tous les builders implémentés respectent kpis=3, charts=2, queue ∈ [3,5].

    NB : la vérification approfondie est dans tests/services/strategique/test_builders.py.
    Ici on duplique pour figer le verrou structurel (les tests fonctionnels peuvent
    être refactorés sans casser ce contrat).
    """
    from unittest.mock import MagicMock
    from datetime import datetime, timezone

    from regulatory.applicability_types import (
        ApplicabilityStatus,
        RuleApplicability,
        RuleCode,
    )
    from services.strategique.builders import IMPLEMENTED_MODES, MODE_BUILDERS

    audit = {
        "doctrine_version": "ADR-024-v1.0",
        "evaluated_at": datetime(2026, 5, 13, tzinfo=timezone.utc).isoformat(),
        "evaluator": "TestEvaluator",
        "evaluator_version": "TEST-v1.0",
        "data_source": "test.fixtures",
    }

    def _stub_entry(rule, status, missing=()):
        return RuleApplicability(
            rule_code=rule,
            rule_version=f"{rule.value}-test-v2026-01-01",
            scope_level="site" if rule in (RuleCode.DT, RuleCode.BACS, RuleCode.APER) else "organisation",
            scope_id=1,
            scope_label="X",
            status=status,
            reason_code=f"{rule.value}.APPLICABLE"
            if status == ApplicabilityStatus.APPLICABLE
            else (
                f"{rule.value}.DATA_MISSING.SURFACE"
                if status == ApplicabilityStatus.DATA_MISSING
                else f"{rule.value}.NOT_APPLICABLE.SDP_LT_1000"
                if rule == RuleCode.DT
                else f"{rule.value}.NOT_APPLICABLE.PME"
            ),
            reason_human="t",
            missing_inputs=list(missing) if status == ApplicabilityStatus.DATA_MISSING else [],
            _audit=audit,
        )

    applicability_data = {rule: [_stub_entry(rule, ApplicabilityStatus.APPLICABLE)] for rule in RuleCode}

    for mode in IMPLEMENTED_MODES:
        builder = MODE_BUILDERS[mode]
        payload = builder.build(
            db=MagicMock(),
            org_id=1,
            applicability=applicability_data,
            patrimoine_maturity=0.85,
        )
        assert len(payload["kpis"]) == 3, f"{mode.value} doit avoir 3 KPIs"
        assert len(payload["charts"]) == 2, f"{mode.value} doit avoir 2 charts"
        assert 3 <= len(payload["queue_p2_p3"]) <= 5, f"{mode.value} queue_p2_p3 hors [3,5]"
