"""
PROMEOS — Source guards Phase 8.2 Sprint C-8 — Lot SEC+CI anti-régression.

3 SG cardinaux :
- SG_PHASE82_01 : PII patterns étendus (email/phone FR/IBAN FR/adresse)
- SG_PHASE82_02 : CI quality-gate.yml job pytest bloquant
- SG_PHASE82_03 : audit_log_service `SessionLocal` top-level (vs lazy)
"""

from __future__ import annotations

from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent
_ANOMALY_DETECTOR_PATH = _BACKEND_ROOT / "services" / "bill_intelligence" / "anomaly_detector.py"
_AUDIT_SERVICE_PATH = _BACKEND_ROOT / "services" / "audit_log_service.py"
_QUALITY_GATE_PATH = _REPO_ROOT / ".github" / "workflows" / "quality-gate.yml"


def test_sg_phase82_01_pii_patterns_extended_email_phone_iban():
    """SG_PHASE82_01 : _PII_PATTERNS étendu (email/phone FR/IBAN FR)."""
    content = _ANOMALY_DETECTOR_PATH.read_text(encoding="utf-8")

    # Marqueur dette Phase 8.2
    assert "D-Audit-Phase7-PII-Sanitization-Extended-001" in content, (
        "SG_PHASE82_01 BLOQUANT : référence dette Phase 8.2 PII étendue absente."
    )

    # Patterns étendus présents (regex)
    cardinal_patterns = [
        "@",  # Email
        r"\+33",  # Téléphone FR international
        "FR",  # IBAN FR
    ]
    for p in cardinal_patterns:
        assert p in content, f"SG_PHASE82_01 : pattern '{p}' manquant dans _PII_PATTERNS"

    # Audit_log_service _SENSITIVE_KEY_PATTERNS étendu
    audit_content = _AUDIT_SERVICE_PATH.read_text(encoding="utf-8")
    cardinal_keys = ["email", "telephone", "phone", "iban", "rib", "adresse"]
    for k in cardinal_keys:
        assert f'"{k}"' in audit_content, f"SG_PHASE82_01 : key '{k}' manquant _SENSITIVE_KEY_PATTERNS"


def test_sg_phase82_02_ci_quality_gate_pytest_bloquant():
    """SG_PHASE82_02 cardinal QA : job pytest principal quality-gate.yml retire continue-on-error."""
    content = _QUALITY_GATE_PATH.read_text(encoding="utf-8")

    # Marqueur dette Phase 8.2
    assert "D-Audit-Phase7-CI-Continue-On-Error-Bloquant-002" in content, (
        "SG_PHASE82_02 BLOQUANT : référence dette CI Phase 8.2 absente."
    )

    # Section pytest principal ne contient PAS continue-on-error: true (runtime)
    pytest_idx = content.find("Unit tests (Pytest)")
    assert pytest_idx > 0
    next_section_idx = content.find("Tests Contracts V2", pytest_idx)
    pytest_block = content[pytest_idx:next_section_idx] if next_section_idx > 0 else content[pytest_idx:]

    runtime_lines = [
        line
        for line in pytest_block.split("\n")
        if "continue-on-error: true" in line and not line.strip().startswith("#")
    ]
    assert not runtime_lines, (
        "SG_PHASE82_02 BLOQUANT : continue-on-error: true runtime encore dans bloc pytest principal :\n"
        + "\n".join(runtime_lines)
    )


def test_sg_phase82_03_audit_log_service_session_local_factory_top_level():
    """SG_PHASE82_03 : audit_log_service utilise SessionLocal top-level (vs lazy)."""
    content = _AUDIT_SERVICE_PATH.read_text(encoding="utf-8")

    # Marqueur dette Phase 8.2
    assert "D-Audit-Phase7-Import-Lazy-Fix-003" in content, (
        "SG_PHASE82_03 BLOQUANT : référence dette import lazy Phase 8.2 absente."
    )

    # Import top-level présent (try guard pattern)
    assert "from database import SessionLocal" in content, (
        "SG_PHASE82_03 : import `from database import SessionLocal` manquant."
    )
    assert "except ImportError" in content, "SG_PHASE82_03 : guard ImportError manquant top-level."

    # Compte runtime — Phase 8.2 fix : 1 import unique top-level (vs 2+ avant fix).
    # Exclure commentaires (lignes commençant par `#`).
    import re

    runtime_imports = re.findall(r"^\s*from database import SessionLocal\b", content, re.MULTILINE)
    assert len(runtime_imports) == 1, (
        f"SG_PHASE82_03 BLOQUANT : {len(runtime_imports)} imports runtime "
        "`from database import SessionLocal` (attendu : 1 top-level uniquement)."
    )
