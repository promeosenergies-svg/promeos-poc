"""
PROMEOS — Source guards Phase 7.8 Sprint C-7 — 6 P0 fixes audit deep cardinaux.

Anti-régression Phase D+ : empêche récidive 6 P0 invisibles aux 3 audits Phase 5.5+5.7+
Phase 7 audit deep cumulé. Pattern doctrinal "audit logging ≠ authorization enforcement"
émergent — distinction cardinale Phase D.

5 SG cardinaux :
- SG_PHASE78_01 : DataConnect 5 endpoints (consent/sync/tokens GET/tokens DELETE/authorize) wirent resolve_org_id
- SG_PHASE78_02 : GRDF 2 endpoints (consumption/sync) wirent resolve_org_id
- SG_PHASE78_03 : scope_utils.resolve_org_id valide org_id_override DB strict
- SG_PHASE78_04 : log_consent_changes_batch commit immédiat (anti-rollback CNIL)
- SG_PHASE78_05 : audit_log_service cite Article 5(2)+30 (PAS Article 6 RGPD)
- SG_PHASE78_06 : anomaly_detector documente TURPE 7 vs TURPE 6 legacy explicitement
"""

from __future__ import annotations

from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DATACONNECT_PATH = _BACKEND_ROOT / "routes" / "dataconnect_route.py"
_GRDF_PATH = _BACKEND_ROOT / "routes" / "grdf_route.py"
_SCOPE_UTILS_PATH = _BACKEND_ROOT / "services" / "scope_utils.py"
_AUDIT_SERVICE_PATH = _BACKEND_ROOT / "services" / "audit_log_service.py"
_ANOMALY_DETECTOR_PATH = _BACKEND_ROOT / "services" / "bill_intelligence" / "anomaly_detector.py"


def test_sg_phase78_01_dataconnect_endpoints_use_resolve_org_id():
    """SG_PHASE78_01 : DataConnect 5 endpoints wirent resolve_org_id (anti-IDOR)."""
    content = _DATACONNECT_PATH.read_text(encoding="utf-8")

    # Import resolve_org_id ou _assert_prm_belongs_to_org présent
    assert "from services.scope_utils import resolve_org_id" in content, (
        "SG_PHASE78_01 BLOQUANT : import resolve_org_id manquant dans dataconnect_route.py"
    )
    # Helper validation PRM ↔ org présent
    assert "def _assert_prm_belongs_to_org" in content, (
        "SG_PHASE78_01 : helper _assert_prm_belongs_to_org manquant (Phase 7.8 fix IDOR)."
    )
    # Au moins 5 callsites resolve_org_id (5 endpoints sécurisés)
    callsites = content.count("resolve_org_id(")
    assert callsites >= 5, (
        f"SG_PHASE78_01 BLOQUANT : resolve_org_id appelé {callsites} fois (attendu ≥5 endpoints DataConnect sécurisés)."
    )


def test_sg_phase78_02_grdf_endpoints_use_resolve_org_id():
    """SG_PHASE78_02 : GRDF 2 endpoints wirent resolve_org_id."""
    content = _GRDF_PATH.read_text(encoding="utf-8")

    assert "from services.scope_utils import resolve_org_id" in content, (
        "SG_PHASE78_02 BLOQUANT : import resolve_org_id manquant dans grdf_route.py"
    )
    assert "def _assert_pce_belongs_to_org" in content, "SG_PHASE78_02 : helper _assert_pce_belongs_to_org manquant."
    callsites = content.count("resolve_org_id(")
    assert callsites >= 2, (
        f"SG_PHASE78_02 BLOQUANT : resolve_org_id appelé {callsites} fois (attendu ≥2 endpoints GRDF)."
    )


def test_sg_phase78_03_org_id_override_validates_db_existence():
    """SG_PHASE78_03 : scope_utils.resolve_org_id valide org_id_override en DB."""
    content = _SCOPE_UTILS_PATH.read_text(encoding="utf-8")

    # Marqueur Phase 7.8 fix présent
    assert "D-Audit-Phase7-IDOR-Org-Id-Override-Bypass-003" in content, (
        "SG_PHASE78_03 BLOQUANT : référence dette Phase 7.8 fix IDOR override absente."
    )
    # Validation DB stricte présente
    assert "Organisation.id == org_id_override" in content, (
        "SG_PHASE78_03 : validation DB Organisation.id == org_id_override manquante."
    )
    assert "org_id_override_rejected_db_check" in content, "SG_PHASE78_03 : log security warning manquant."


def test_sg_phase78_04_log_consent_changes_batch_commit_immediate():
    """SG_PHASE78_04 cardinal CNIL : log_consent_changes_batch commit immédiat (anti-rollback)."""
    content = _AUDIT_SERVICE_PATH.read_text(encoding="utf-8")

    # Marqueur Phase 7.8 fix
    assert "D-Audit-Phase7-Audit-Rollback-Loss-004" in content, (
        "SG_PHASE78_04 BLOQUANT : référence dette Phase 7.8 fix audit rollback absente."
    )
    # Note explicite "commit immédiat" + CNIL article 5(2)
    assert "commit immédiat" in content or "commit IMMÉDIAT" in content
    assert "anti-CWE-778" in content or "CWE-778" in content


def test_sg_phase78_05_audit_log_uses_article_5_2_30_not_article_6():
    """SG_PHASE78_05 : audit_log_service cite Article 5(2)+30 (PAS Article 6 RGPD pour traçabilité)."""
    content = _AUDIT_SERVICE_PATH.read_text(encoding="utf-8")

    # Article 5(2) + 30 présents
    assert "Article 5(2)" in content, (
        "SG_PHASE78_05 BLOQUANT REG : 'Article 5(2)' absent (substitution Phase 7.8 incomplète)."
    )
    assert "Article 30" in content, "SG_PHASE78_05 : 'Article 30' absent (registre des activités)."

    # Anti-pattern : Article 6 RGPD pour traçabilité
    # (acceptable mention Article 6 si contexte = bases légales, mais pas pour traçabilité technique)
    payload_article_6 = '"Article 6 RGPD - traçabilité' in content
    assert not payload_article_6, (
        "SG_PHASE78_05 BLOQUANT REG : 'Article 6 RGPD - traçabilité' encore présent (régression).\n"
        "Article 6 = bases légales, pas traçabilité. Substitution Article 5(2)+30 cardinal."
    )


def test_sg_phase78_06_turpe_7_vs_turpe_6_legacy_documented():
    """SG_PHASE78_06 : anomaly_detector documente TURPE 7 officiel vs TURPE 6 legacy."""
    content = _ANOMALY_DETECTOR_PATH.read_text(encoding="utf-8")

    # Listes séparées explicites
    assert "_PERIOD_CODES_KNOWN_TURPE_7" in content, (
        "SG_PHASE78_06 BLOQUANT REG : liste _PERIOD_CODES_KNOWN_TURPE_7 absente (Phase 7.8 fix codes)."
    )
    assert "_PERIOD_CODES_LEGACY_TURPE_6" in content, "SG_PHASE78_06 : liste _PERIOD_CODES_LEGACY_TURPE_6 absente."

    # Référence CRE délibération TURPE 7
    assert "2025-78" in content or "TURPE 7" in content
    # Marqueur dette Phase 7.8 fix
    assert "D-Audit-Phase7-TURPE-7-Codes-Obsolete-006" in content
