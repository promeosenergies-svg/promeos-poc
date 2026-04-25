"""
Tests for business error catalog (Sprint CX item #3).
Guarantees: 20 codes, FR messages, suggestions, valid HTTP status.
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from services.error_catalog import ERROR_CATALOG, business_error, _SAFE_CONTEXT_KEYS


VALID_HTTP_STATUS = {400, 404, 409, 422, 500}


def test_catalog_has_at_least_20_codes():
    assert len(ERROR_CATALOG) >= 20, f"Attendu ≥ 20 codes, trouvé {len(ERROR_CATALOG)}"


def test_all_entries_have_required_fields():
    for code, entry in ERROR_CATALOG.items():
        assert "message" in entry, f"{code}: champ 'message' manquant"
        assert "suggestion" in entry, f"{code}: champ 'suggestion' manquant"
        assert "http_status" in entry, f"{code}: champ 'http_status' manquant"


def test_messages_are_non_empty_and_reasonable_length():
    for code, entry in ERROR_CATALOG.items():
        msg = entry["message"]
        assert isinstance(msg, str) and len(msg) > 0, f"{code}: message vide"
        assert len(msg) >= 15, f"{code}: message trop court ({len(msg)})"
        assert len(msg) <= 200, f"{code}: message > 200 caractères ({len(msg)})"
        # Doit terminer par un point (phrase complète)
        assert msg.rstrip().endswith(".") or msg.rstrip().endswith(")"), (
            f"{code}: message devrait être une phrase complète terminée par un point"
        )


def test_suggestions_are_actionable():
    for code, entry in ERROR_CATALOG.items():
        sug = entry["suggestion"]
        assert isinstance(sug, str) and len(sug) > 0, f"{code}: suggestion vide"
        assert len(sug) <= 250, f"{code}: suggestion > 250 caractères ({len(sug)})"


def test_http_status_is_valid():
    for code, entry in ERROR_CATALOG.items():
        assert entry["http_status"] in VALID_HTTP_STATUS, (
            f"{code}: status {entry['http_status']} non standard (attendu {VALID_HTTP_STATUS})"
        )


def test_codes_are_screaming_snake_case():
    for code in ERROR_CATALOG.keys():
        assert code.isupper(), f"{code} doit être en SCREAMING_SNAKE_CASE"
        assert "_" in code or code.isalpha(), f"{code}: format invalide"


def test_business_error_returns_httpexception_kwargs():
    kwargs = business_error("ACTION_NOT_FOUND")
    assert kwargs["status_code"] == 404
    assert kwargs["detail"]["code"] == "ACTION_NOT_FOUND"
    assert "message" in kwargs["detail"]
    assert "suggestion" in kwargs["detail"]


def test_business_error_with_context():
    kwargs = business_error("ACTION_NOT_FOUND", action_id=42, org_id=7)
    assert kwargs["detail"]["context"] == {"action_id": 42, "org_id": 7}


def test_business_error_raises_on_unknown_code():
    with pytest.raises(KeyError):
        business_error("NOPE_NOT_A_REAL_CODE")


# ─── Sprint CX 2.5-bis S3 : anti-PII allowlist sur context ───────────────


def test_safe_context_allowlisted():
    """S3 : les clés de l'allowlist passent inchangées."""
    kwargs = business_error(
        "ACTION_NOT_FOUND",
        action_id=42,
        site_id=7,
        org_id=1,
        siren="123456789",
        siret="12345678900012",
        module="billing",
        field="puissance_souscrite",
        value_reçue=99,
        limite=36,
        period_start="2026-01-01",
        period_end="2026-12-31",
        count=5,
    )
    ctx = kwargs["detail"]["context"]
    for key in _SAFE_CONTEXT_KEYS:
        assert key in ctx, f"clé safe {key} manquante dans le context retourné"


def test_pii_keys_stripped_email():
    """S3 : `user_email` strippé même si dev insiste."""
    kwargs = business_error("USER_NOT_FOUND", user_email="leak@example.com", action_id=42)
    ctx = kwargs["detail"].get("context", {})
    assert "user_email" not in ctx
    assert "email" not in ctx
    assert ctx == {"action_id": 42}


def test_pii_keys_stripped_common_patterns():
    """S3 : patterns email/phone/token/password/*_at/*name/nom tous strippés."""
    kwargs = business_error(
        "USER_NOT_FOUND",
        user_email="x@y.z",
        phone="0102030405",
        access_token="secret",
        password="hunter2",
        created_at="2026-01-01T00:00:00",
        last_name="Dupont",
        nom="Dupont",
        action_id=42,  # seul survivant
    )
    ctx = kwargs["detail"].get("context", {})
    assert ctx == {"action_id": 42}


def test_non_allowlisted_key_stripped():
    """S3 : clé inconnue (hors allowlist ET hors pattern PII) → strippée quand même."""
    kwargs = business_error("ACTION_NOT_FOUND", action_id=42, random_debug_field="whatever")
    ctx = kwargs["detail"].get("context", {})
    assert "random_debug_field" not in ctx
    assert ctx == {"action_id": 42}


def test_warning_logged_on_strip(caplog):
    """S3 : chaque clé strippée émet un warning traçable."""
    with caplog.at_level(logging.WARNING, logger="services.error_catalog"):
        business_error("ACTION_NOT_FOUND", user_email="leak@x.io", action_id=42)

    # Un warning contenant le code d'erreur et la clé strippée
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any("user_email" in r.getMessage() and "ACTION_NOT_FOUND" in r.getMessage() for r in warnings), (
        f"warning strip attendu, records={[r.getMessage() for r in warnings]}"
    )


def test_empty_context_after_strip_omits_field():
    """S3 : si toutes les clés sont strippées, detail.context est absent (pas {})."""
    kwargs = business_error("USER_NOT_FOUND", user_email="x@y.z", password="hunter2")
    assert "context" not in kwargs["detail"]


def test_required_codes_present():
    """Les 20 codes cibles sprint CX item #3 sont tous présents."""
    REQUIRED = [
        "ACTION_NOT_FOUND",
        "ACTION_CLOSE_BLOCKED",
        "TITLE_REQUIRED",
        "PRIORITY_REQUIRED",
        "PRIORITY_OUT_OF_RANGE",
        "REASON_REQUIRED",
        "SITE_NOT_FOUND",
        "ALERT_NOT_FOUND",
        "SIREN_INVALID",
        "SIRET_INVALID",
        "ETABLISSEMENT_NOT_FOUND",
        "INVALID_DATE_FORMAT",
        "EMAIL_ALREADY_EXISTS",
        "USER_NOT_FOUND",
        "LAST_DG_OWNER_PROTECTION",
        "USER_NO_ROLE_IN_ORG",
        "VERSION_NOT_FOUND",
        "VERSION_ALREADY_EXISTS",
        "WEIGHTS_SUM_INVALID",
        "NO_PREVIOUS_VERSION",
    ]
    for code in REQUIRED:
        assert code in ERROR_CATALOG, f"{code} manquant dans le catalogue"
