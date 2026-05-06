"""
PROMEOS — Tests cardinaux Phase 8.2 Sprint C-8 — Lot SEC+CI (3 P1 fixes).

Couvre :
- D-Audit-Phase7-PII-Sanitization-Extended-001 P1 SEC (PII étendue email/phone/IBAN)
- D-Audit-Phase7-CI-Continue-On-Error-Bloquant-002 P1 QA (CI strictness)
- D-Audit-Phase7-Import-Lazy-Fix-003 P1 CR (import top-level guard)
"""

from __future__ import annotations

from pathlib import Path


# ─── Fix 1 — PII sanitization étendue ────────────────────────────────────────


def test_phase82_pii_sanitization_redacts_email():
    """Phase 8.2 cardinal SEC : email RFC 5322 redacted dans labels."""
    from services.bill_intelligence.anomaly_detector import _sanitize_pii_label

    label = "VNU dormant contact: facturation@client.fr référence 2026"
    sanitized = _sanitize_pii_label(label)
    assert "facturation@client.fr" not in sanitized
    assert "<PII_REDACTED>" in sanitized


def test_phase82_pii_sanitization_redacts_phone_fr_fixe():
    """Phase 8.2 : téléphone FR (0X XX XX XX XX) redacted."""
    from services.bill_intelligence.anomaly_detector import _sanitize_pii_label

    for label in (
        "VNU contact 06 12 34 56 78",
        "VNU contact 0612345678",
        "VNU contact 01.23.45.67.89",
    ):
        sanitized = _sanitize_pii_label(label)
        assert "<PII_REDACTED>" in sanitized, f"Label '{label}' non redacted"


def test_phase82_pii_sanitization_redacts_phone_fr_international():
    """Phase 8.2 : téléphone FR +33 X XX XX XX XX redacted."""
    from services.bill_intelligence.anomaly_detector import _sanitize_pii_label

    label = "VNU contact +33 6 12 34 56 78 référence"
    sanitized = _sanitize_pii_label(label)
    assert "<PII_REDACTED>" in sanitized


def test_phase82_pii_sanitization_redacts_iban_fr():
    """Phase 8.2 cardinal financière : IBAN FR (27 chars) redacted."""
    from services.bill_intelligence.anomaly_detector import _sanitize_pii_label

    label = "VNU domiciliation FR76 1234 5678 9012 3456 7890 123"
    sanitized = _sanitize_pii_label(label)
    assert "FR76 1234" not in sanitized
    assert "<PII_REDACTED>" in sanitized


def test_phase82_pii_sanitization_preserves_clean_label():
    """Phase 8.2 : label sans PII reste inchangé (anti faux positifs)."""
    from services.bill_intelligence.anomaly_detector import _sanitize_pii_label

    label = "VNU dormant compteur principal — calcul automatique"
    sanitized = _sanitize_pii_label(label)
    assert sanitized == label


def test_phase82_audit_log_keys_extended_redact_email_phone():
    """Phase 8.2 cardinal : _SENSITIVE_KEY_PATTERNS étendu email/phone/IBAN/adresse."""
    from services.audit_log_service import _SENSITIVE_KEY_PATTERNS, _is_sensitive_key

    cardinal_phase82 = ["email", "phone", "telephone", "iban", "rib", "adresse", "address"]
    for key in cardinal_phase82:
        assert key in _SENSITIVE_KEY_PATTERNS, f"Phase 8.2 BLOQUANT : key '{key}' manquant"

    # Fonction _is_sensitive_key matche les patterns étendus
    assert _is_sensitive_key("user_email")
    assert _is_sensitive_key("contact_phone")
    assert _is_sensitive_key("billing_address")


# ─── Fix 2 — CI bloquant ────────────────────────────────────────────────────


def test_phase82_ci_quality_gate_pytest_no_continue_on_error():
    """Phase 8.2 cardinal QA : job pytest principal `quality-gate.yml` retire continue-on-error."""
    workflow_path = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "quality-gate.yml"
    content = workflow_path.read_text(encoding="utf-8")

    # Le job "Unit tests (Pytest)" ne doit PLUS être continue-on-error
    # Recherche pattern : "Unit tests (Pytest)" suivi de "continue-on-error: true" dans 25 lignes
    pytest_section_idx = content.find("Unit tests (Pytest)")
    assert pytest_section_idx > 0, "Job 'Unit tests (Pytest)' introuvable"

    # Le marqueur Phase 8.2 doit être présent (référence dette)
    assert "D-Audit-Phase7-CI-Continue-On-Error-Bloquant-002" in content, (
        "Phase 8.2 : marqueur dette CI bloquant manquant dans quality-gate.yml"
    )

    # Bloc pytest principal = de "Unit tests (Pytest)" jusqu'au prochain `- name:` (Tests Contracts V2)
    next_section_idx = content.find("- name: Tests Contracts V2", pytest_section_idx)
    assert next_section_idx > pytest_section_idx, "Section 'Tests Contracts V2' introuvable après pytest"

    pytest_block = content[pytest_section_idx:next_section_idx]
    # Filtrer commentaires (lignes commençant par `#` ou contenant `#` + texte) — vérifier uniquement
    # les directives YAML runtime (lignes commençant par espaces puis `continue-on-error:`).
    runtime_lines = [
        line
        for line in pytest_block.split("\n")
        if "continue-on-error: true" in line and not line.strip().startswith("#")
    ]
    assert not runtime_lines, (
        "Phase 8.2 BLOQUANT QA : 'continue-on-error: true' runtime encore présent dans le job pytest principal :\n"
        + "\n".join(runtime_lines)
    )


# ─── Fix 3 — Import lazy fix ────────────────────────────────────────────────


def test_phase82_audit_log_service_session_local_factory_top_level():
    """Phase 8.2 cardinal CR : `SessionLocal` importé top-level (vs lazy in-function)."""
    import services.audit_log_service as svc

    # SessionLocal défini comme attribut module (pas import lazy)
    assert hasattr(svc, "SessionLocal"), "Phase 8.2 BLOQUANT : `SessionLocal` doit être attribut module top-level."


def test_phase82_audit_log_service_no_lazy_session_local_imports():
    """Phase 8.2 : aucun `from database import SessionLocal` lazy résiduel dans fonctions."""
    import inspect

    import services.audit_log_service as svc

    src = inspect.getsource(svc)
    # Compter occurrences runtime (exclure commentaires `#`). Phase 8.2 fix : import unique
    # top-level (try: from database import SessionLocal). Si > 1 occurrence runtime → régression lazy.
    import re

    runtime_imports = re.findall(r"^\s*from database import SessionLocal\b", src, re.MULTILINE)
    assert len(runtime_imports) == 1, (
        f"Phase 8.2 BLOQUANT : {len(runtime_imports)} imports `from database import SessionLocal` runtime "
        "(attendu : 1 top-level uniquement)."
    )


def test_phase82_record_external_api_event_uses_factory_with_guard():
    """Phase 8.2 : `_record_external_api_event` utilise `SessionLocal` + guard."""
    import inspect

    from services.audit_log_service import _record_external_api_event

    src = inspect.getsource(_record_external_api_event)
    assert "SessionLocal" in src, "Phase 8.2 : factory top-level non utilisé"
    assert "SessionLocal is None" in src or "SessionLocal is not None" in src, (
        "Phase 8.2 : guard `SessionLocal is None` manquant (résilience cardinale)"
    )
