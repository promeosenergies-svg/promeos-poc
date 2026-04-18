"""
Tests utils Sol V1 — now_utc, hash, tokens HMAC, formatters FR.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import pytest

from sol.utils import (
    fmt_eur,
    fmt_mwh,
    fmt_pct,
    generate_cancellation_token,
    generate_confirmation_token,
    generate_correlation_id,
    hash_inputs,
    is_sha256_hex,
    now_utc,
    verify_confirmation_token,
)


# Caractères typographiques FR attendus dans les formatters
_NBSP = "\u00A0"
_NNBSP = "\u202F"


# ─────────────────────────────────────────────────────────────────────────────
# Datetime
# ─────────────────────────────────────────────────────────────────────────────


def test_now_utc_is_aware():
    t = now_utc()
    assert isinstance(t, datetime)
    assert t.tzinfo is not None
    assert t.tzinfo.utcoffset(t) == timezone.utc.utcoffset(t)


# ─────────────────────────────────────────────────────────────────────────────
# Hash
# ─────────────────────────────────────────────────────────────────────────────


def test_hash_inputs_deterministic():
    h1 = hash_inputs("a", 1, {"x": [1, 2]})
    h2 = hash_inputs("a", 1, {"x": [1, 2]})
    assert h1 == h2
    assert len(h1) == 64
    assert is_sha256_hex(h1)


def test_hash_inputs_different_args_different_hashes():
    assert hash_inputs("a") != hash_inputs("b")
    assert hash_inputs(1, 2) != hash_inputs(2, 1)  # ordre compte


def test_hash_inputs_handles_datetime():
    # default=str gère datetime
    t = datetime(2026, 4, 18, tzinfo=timezone.utc)
    h = hash_inputs("action", t)
    assert len(h) == 64


def test_is_sha256_hex():
    assert is_sha256_hex("a" * 64) is True
    assert is_sha256_hex("A" * 64) is False  # uppercase rejeté
    assert is_sha256_hex("g" * 64) is False  # hors hex
    assert is_sha256_hex("a" * 63) is False  # longueur


# ─────────────────────────────────────────────────────────────────────────────
# Correlation & cancellation tokens
# ─────────────────────────────────────────────────────────────────────────────


def test_generate_correlation_id_is_uuid4_format():
    cid = generate_correlation_id()
    assert len(cid) == 36  # uuid4 format "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    assert cid.count("-") == 4
    # 2 correlation_ids consécutifs différents
    assert generate_correlation_id() != cid


def test_generate_cancellation_token_url_safe():
    t = generate_cancellation_token()
    # secrets.token_urlsafe(32) produit ~43 chars url-safe
    assert len(t) >= 30
    assert re.match(r"^[A-Za-z0-9_-]+$", t)
    assert generate_cancellation_token() != t


# ─────────────────────────────────────────────────────────────────────────────
# Confirmation tokens HMAC
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sol_secret_set():
    """Assure SOL_SECRET_KEY set pendant le test."""
    original = os.environ.get("SOL_SECRET_KEY")
    os.environ["SOL_SECRET_KEY"] = "test_key_do_not_use_in_prod"
    yield
    if original is None:
        os.environ.pop("SOL_SECRET_KEY", None)
    else:
        os.environ["SOL_SECRET_KEY"] = original


def test_confirmation_token_roundtrip(sol_secret_set):
    cid = generate_correlation_id()
    plan_hash = "a" * 64
    user_id = 42
    tok = generate_confirmation_token(cid, plan_hash, user_id)

    valid, uid = verify_confirmation_token(tok, cid, plan_hash)
    assert valid is True
    assert uid == user_id


def test_confirmation_token_tamper_detected(sol_secret_set):
    cid = generate_correlation_id()
    plan_hash = "a" * 64
    tok = generate_confirmation_token(cid, plan_hash, 42)

    # Altérer un char du milieu
    tampered = tok[:20] + ("A" if tok[20] != "A" else "B") + tok[21:]
    valid, uid = verify_confirmation_token(tampered, cid, plan_hash)
    assert valid is False
    assert uid is None


def test_confirmation_token_wrong_correlation_rejected(sol_secret_set):
    cid = generate_correlation_id()
    tok = generate_confirmation_token(cid, "a" * 64, 42)

    valid, uid = verify_confirmation_token(tok, "other-correlation-id-not-matching", "a" * 64)
    assert valid is False
    assert uid is None


def test_confirmation_token_wrong_plan_hash_rejected(sol_secret_set):
    cid = generate_correlation_id()
    tok = generate_confirmation_token(cid, "a" * 64, 42)

    valid, uid = verify_confirmation_token(tok, cid, "b" * 64)
    assert valid is False
    assert uid is None


def test_confirmation_token_invalid_format_rejected(sol_secret_set):
    valid, uid = verify_confirmation_token("not-a-valid-token", "x", "y")
    assert valid is False
    assert uid is None


def test_confirmation_token_requires_secret_key():
    original = os.environ.pop("SOL_SECRET_KEY", None)
    try:
        with pytest.raises(RuntimeError, match="SOL_SECRET_KEY"):
            generate_confirmation_token("cid", "hash", 1)
    finally:
        if original is not None:
            os.environ["SOL_SECRET_KEY"] = original


# ─────────────────────────────────────────────────────────────────────────────
# Formatters FR — espaces fines vérifiées par char codes
# ─────────────────────────────────────────────────────────────────────────────


def test_fmt_eur_standard():
    result = fmt_eur(1847.20)
    assert result == f"1{_NNBSP}847,20{_NNBSP}€"
    assert _NNBSP in result  # U+202F fine insécable
    assert "€" in result


def test_fmt_eur_zero():
    assert fmt_eur(0) == f"0,00{_NNBSP}€"


def test_fmt_eur_negative():
    assert fmt_eur(-1500) == f"-1{_NNBSP}500,00{_NNBSP}€"


def test_fmt_eur_large_number():
    result = fmt_eur(1_234_567.89)
    assert "1" in result
    assert "234" in result
    assert "567,89" in result
    # Au moins 2 séparateurs U+202F (milliers + avant €)
    assert result.count(_NNBSP) >= 2


def test_fmt_eur_small_decimals():
    # 1.5 → 1,50
    assert fmt_eur(1.5) == f"1,50{_NNBSP}€"


def test_fmt_mwh_standard():
    result = fmt_mwh(432.6)
    assert result == f"432,6{_NBSP}MWh"
    assert _NBSP in result  # U+00A0 insécable avant unité


def test_fmt_mwh_thousands():
    result = fmt_mwh(1847)
    # "1 847,0 MWh" avec U+00A0 milliers
    assert f"1{_NBSP}847" in result
    assert "MWh" in result


def test_fmt_pct_signed_positive():
    assert fmt_pct(0.084) == f"+8,4{_NNBSP}%"


def test_fmt_pct_signed_negative():
    assert fmt_pct(-0.041) == f"-4,1{_NNBSP}%"


def test_fmt_pct_signed_zero():
    # Par convention : 0 affiche +
    assert fmt_pct(0) == f"+0,0{_NNBSP}%"


def test_fmt_pct_unsigned():
    assert fmt_pct(0.084, signed=False) == f"8,4{_NNBSP}%"


def test_fmt_pct_precision():
    # 0.1236 * 100 = 12.36 — pas de borderline 0.5 pour éviter banker's rounding
    assert fmt_pct(0.1236, precision=2) == f"+12,36{_NNBSP}%"
    assert fmt_pct(0.5, precision=0) == f"+50{_NNBSP}%"
