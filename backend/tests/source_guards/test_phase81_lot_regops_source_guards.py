"""
PROMEOS — Source guards Phase 8.1 Sprint C-8 — Lot REGOPS anti-régression.

3 SG cardinaux :
- SG_PHASE81_01 : helper resolve_surface_for_operat_export() présent (ADR-020 Option C)
- SG_PHASE81_02 : CGU referentiel central + service helpers présents
- SG_PHASE81_03 : KPI bill_intelligence canonique sur org_scope_q (pas base_q user-filtered)
"""

from __future__ import annotations

from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_OPERAT_HELPERS_PATH = _BACKEND_ROOT / "regops" / "operat_export_helpers.py"
_CGU_YAML_PATH = _BACKEND_ROOT / "config" / "cgu_referentiel.yaml"
_CGU_SERVICE_PATH = _BACKEND_ROOT / "services" / "cgu_service.py"
_BILL_INTEL_PATH = _BACKEND_ROOT / "routes" / "bill_intelligence.py"
_DATA_QUALITY_PATH = _BACKEND_ROOT / "regops" / "data_quality_specs.py"


def test_sg_phase81_01_operat_export_helper_present():
    """SG_PHASE81_01 : regops/operat_export_helpers.py + resolve_surface_for_operat_export() présents."""
    assert _OPERAT_HELPERS_PATH.exists(), (
        "SG_PHASE81_01 BLOQUANT : backend/regops/operat_export_helpers.py absent (Phase 8.1 ADR-020)."
    )
    content = _OPERAT_HELPERS_PATH.read_text(encoding="utf-8")

    assert "def resolve_surface_for_operat_export(" in content
    assert "def is_operat_v2_ready(" in content
    assert "ADR-020" in content
    assert "art. 2-j" in content or "Surface CE" in content

    # data_quality_specs étendu
    dq_content = _DATA_QUALITY_PATH.read_text(encoding="utf-8")
    assert '"s_ce_m2"' in dq_content, (
        "SG_PHASE81_01 : s_ce_m2 manquant dans data_quality_specs (DT optional Phase 8.1)."
    )


def test_sg_phase81_02_cgu_referentiel_central_present():
    """SG_PHASE81_02 : YAML cgu_referentiel + service helpers présents."""
    assert _CGU_YAML_PATH.exists(), "SG_PHASE81_02 BLOQUANT : backend/config/cgu_referentiel.yaml absent."
    yaml_content = _CGU_YAML_PATH.read_text(encoding="utf-8")
    assert "versions:" in yaml_content
    assert "statut: actuel" in yaml_content

    assert _CGU_SERVICE_PATH.exists(), "SG_PHASE81_02 : backend/services/cgu_service.py absent."
    svc_content = _CGU_SERVICE_PATH.read_text(encoding="utf-8")
    cardinal_helpers = [
        "def get_current_cgu_version(",
        "def is_valid_cgu_version(",
        "def list_active_cgu_versions(",
    ]
    missing = [h for h in cardinal_helpers if h not in svc_content]
    assert not missing, f"SG_PHASE81_02 BLOQUANT : helpers manquants cgu_service.py : {missing}"


def test_sg_phase81_03_kpi_bill_intelligence_canonique_org_scope_q():
    """SG_PHASE81_03 : KPI bill_intelligence calculé sur org_scope_q (PAS base_q user-filtered)."""
    content = _BILL_INTEL_PATH.read_text(encoding="utf-8")

    # Variable org_scope_q présente (Phase 8.1 fix)
    assert "org_scope_q" in content, (
        "SG_PHASE81_03 BLOQUANT : variable org_scope_q manquante (Phase 8.1 KPI canonique fix)."
    )

    # KPI calcul utilise org_scope_q (pas base_q)
    # Recherche pattern : kpi_total_economie_eur = ( ... org_scope_q.filter(... R19 ...)
    kpi_section = content.split("kpi_total_economie_eur")[1] if "kpi_total_economie_eur" in content else ""
    assert "org_scope_q" in kpi_section[:500], (
        "SG_PHASE81_03 BLOQUANT : KPI doit utiliser org_scope_q (cross-vues canonique).\n"
        "Avant fix : base_q user-filtered → KPI muté par filtres → trompeur."
    )

    # Marqueur dette Phase 8.1
    assert "D-Audit-Phase7-KPI-Mutation-Coherence-003" in content, (
        "SG_PHASE81_03 : référence dette Phase 8.1 fix KPI mutation absente."
    )

    # Exclusion des résolues (cardinal CFO actionable)
    assert "BillAnomaly.resolved_at.is_(None)" in kpi_section[:500] or "resolved_at.is_(None)" in kpi_section[:500]
