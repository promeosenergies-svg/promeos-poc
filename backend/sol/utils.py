"""
Utilitaires Sol V1 : datetime, hash, tokens HMAC, formatters FR.

Pures fonctions réutilisées par planner / validator / scheduler / routes.
Aucun effet de bord, testables en isolation.

Décisions appliquées :
- P1-1 : datetime.now(timezone.utc) (pas datetime.now(UTC) import)
- P1-3 : SOL_SECRET_KEY nouvelle var env (lue lazy via os.environ, pas à l'import)
- P1-7 : formatters FR utilisent espaces fines insécables (U+202F) et
  insécables normales (U+00A0) conformes guide éditorial Sol.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

# Caractères typographiques FR (voir docs/sol/SOL_V1_VOICE_GUIDE.md §3)
_NBSP = "\u00A0"   # U+00A0 — espace insécable (milliers : "1 847")
_NNBSP = "\u202F"  # U+202F — espace fine insécable (avant : ; ! ? % €)


# ─────────────────────────────────────────────────────────────────────────────
# Datetime
# ─────────────────────────────────────────────────────────────────────────────


def now_utc() -> datetime:
    """Retourne datetime UTC-aware. Jamais utcnow() (dépréciée Python 3.12+)."""
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Hash & correlation IDs
# ─────────────────────────────────────────────────────────────────────────────


def hash_inputs(*args: Any) -> str:
    """
    SHA256 déterministe des arguments passés, sérialisation JSON canonique.

    Utilisé pour :
    - `SolActionLog.inputs_hash` (détection altération entre preview et confirm)
    - `SolConfirmationToken.plan_hash` (intégrité du plan signé)

    Idempotent : `hash_inputs(x, y) == hash_inputs(x, y)` toujours.
    """
    payload = json.dumps(args, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_correlation_id() -> str:
    """UUID4 string — clé de corrélation partagée entre phases d'une action."""
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# Tokens : cancellation (URL-safe non-signé) + confirmation (HMAC signé)
# ─────────────────────────────────────────────────────────────────────────────


def generate_cancellation_token() -> str:
    """
    Token URL-safe 32 bytes pour annulation one-click depuis email.

    Pas d'HMAC — la sécurité vient du fait que le token est secret (seul
    le destinataire de l'email le connaît) + validé contre la DB
    (SolPendingAction.cancellation_token unique). Aucune info sensible
    encodée dedans.
    """
    return secrets.token_urlsafe(32)


def _sol_secret_key() -> bytes:
    """Lit SOL_SECRET_KEY de l'env au runtime (pas à l'import).

    Évite de casser les tests qui n'ont pas la var set avant le import
    de backend.sol.utils.
    """
    secret = os.environ.get("SOL_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "SOL_SECRET_KEY environment variable is required. "
            "Set it in .env or export before starting the backend."
        )
    return secret.encode("utf-8")


def generate_confirmation_token(
    correlation_id: str,
    plan_hash: str,
    user_id: int,
) -> str:
    """
    HMAC-SHA256 signé avec SOL_SECRET_KEY, encodage url-safe base64.

    Structure du payload : `{correlation_id}|{plan_hash}|{user_id}|{iso_now}`
    Signature : HMAC-SHA256(payload) tronquée implicitement à 32 bytes.
    Format final : base64url(payload + b"|" + sig), sans padding.

    Utilisé pour lier une prévisualisation à son exécution : le token est
    émis au /preview et consommé au /confirm. Si le plan change entre les
    deux (altération ou race condition), le plan_hash ne matchera plus.
    """
    secret = _sol_secret_key()
    now_iso = now_utc().isoformat()
    payload = f"{correlation_id}|{plan_hash}|{user_id}|{now_iso}".encode("utf-8")
    sig = hmac.new(secret, payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(payload + b"|" + sig).decode("ascii").rstrip("=")


_HMAC_SHA256_SIZE = 32  # HMAC-SHA256 produces 32 raw bytes


def verify_confirmation_token(
    token: str,
    expected_correlation_id: str,
    expected_plan_hash: str,
) -> tuple[bool, int | None]:
    """
    Vérifie token HMAC. Retourne (valid, user_id) ou (False, None).

    Validations :
    1. Décodage base64url réussi
    2. Taille minimale compatible (HMAC 32 bytes + 1 "|" + payload non vide)
    3. correlation_id matche expected
    4. plan_hash matche expected (détection altération)
    5. Signature HMAC matche (détection tampering)

    N'implémente PAS expiry ni single-use : ceux-ci sont vérifiés côté DB
    via `SolConfirmationToken.expires_at` / `.consumed`.

    Structure format : `{payload_utf8} | HMAC_SHA256(payload)` (32 bytes raw).
    Slicing par longueur fixe (pas rfind b"|" — la sig binaire peut contenir
    des bytes 0x7C qui casseraient le split).
    """
    secret = _sol_secret_key()
    try:
        # Re-padding base64 si nécessaire
        padding = "=" * (-len(token) % 4)
        raw = base64.urlsafe_b64decode(token + padding)
        # Structure : payload_bytes + b"|" + sig_32_bytes
        # Slice depuis la fin par longueur fixe (sig HMAC-SHA256 = 32 bytes)
        if len(raw) < _HMAC_SHA256_SIZE + 2:  # au moins 1 byte payload + 1 "|" + 32 sig
            return (False, None)
        sig_provided = raw[-_HMAC_SHA256_SIZE:]
        separator_byte = raw[-_HMAC_SHA256_SIZE - 1:-_HMAC_SHA256_SIZE]
        if separator_byte != b"|":
            return (False, None)
        payload_bytes = raw[:-_HMAC_SHA256_SIZE - 1]

        # Validation HMAC
        sig_expected = hmac.new(secret, payload_bytes, hashlib.sha256).digest()
        if not hmac.compare_digest(sig_provided, sig_expected):
            return (False, None)

        # Parse payload : correlation_id|plan_hash|user_id|iso
        parts = payload_bytes.decode("utf-8").split("|")
        if len(parts) != 4:
            return (False, None)
        correlation_id, plan_hash, user_id_str, _iso = parts

        if correlation_id != expected_correlation_id:
            return (False, None)
        if plan_hash != expected_plan_hash:
            return (False, None)

        user_id = int(user_id_str)
        return (True, user_id)
    except (ValueError, TypeError, Exception):  # noqa: BLE001
        return (False, None)


# ─────────────────────────────────────────────────────────────────────────────
# Formatters FR — espaces fines et insécables conformes guide Sol
# ─────────────────────────────────────────────────────────────────────────────


def _format_thousands_fr(integer_str: str) -> str:
    """`"1847"` → `"1\u00A0847"`. Pas d'espaces avant 1000."""
    # Traite séparément un éventuel signe
    sign = ""
    if integer_str.startswith(("-", "+")):
        sign, integer_str = integer_str[0], integer_str[1:]
    # Insère U+00A0 tous les 3 chiffres depuis la droite
    reversed_chunks = [integer_str[::-1][i:i + 3][::-1] for i in range(0, len(integer_str), 3)]
    with_nbsp = _NBSP.join(reversed(reversed_chunks))
    return sign + with_nbsp


def fmt_eur(amount: float | int | Decimal) -> str:
    """
    Formatte un montant en euros FR.

    Exemples :
    - `1847.20` → `"1\u202F847,20\u202F€"`
    - `0` → `"0,00\u202F€"`
    - `-1500` → `"-1\u202F500,00\u202F€"`

    Règles :
    - Virgule décimale (pas point)
    - Espace fine insécable milliers (U+202F)
    - Espace fine insécable avant € (U+202F)
    - 2 décimales toujours
    """
    value = Decimal(str(amount)).quantize(Decimal("0.01"))
    integer_part, decimal_part = str(value).split(".")
    formatted = _format_thousands_fr(integer_part).replace(_NBSP, _NNBSP)
    return f"{formatted},{decimal_part}{_NNBSP}€"


def fmt_mwh(amount: float | int | Decimal, precision: int = 1) -> str:
    """
    Formatte un volume en MWh FR.

    Exemples :
    - `432.6` → `"432,6\u00A0MWh"`
    - `1847` → `"1\u00A0847,0\u00A0MWh"`
    """
    value = Decimal(str(amount)).quantize(Decimal(f"0.{'0' * precision}"))
    integer_part, decimal_part = str(value).split(".")
    formatted = _format_thousands_fr(integer_part)
    return f"{formatted},{decimal_part}{_NBSP}MWh"


def fmt_pct(ratio: float | Decimal, precision: int = 1, signed: bool = True) -> str:
    """
    Formatte un ratio en pourcentage FR.

    Exemples (signed=True) :
    - `0.084` → `"+8,4\u202F%"`
    - `-0.041` → `"-4,1\u202F%"`
    - `0` → `"+0,0\u202F%"`
    - `0.5` avec precision=0 → `"+50\u202F%"` (pas de virgule)

    Règles :
    - Virgule décimale si precision > 0
    - Signe explicite si signed=True (inclus 0 → +)
    - Espace fine insécable avant % (U+202F)
    """
    value = Decimal(str(ratio)) * Decimal("100")
    if precision > 0:
        quant = Decimal(f"0.{'0' * precision}")
    else:
        quant = Decimal("1")
    value = value.quantize(quant)

    abs_str = str(abs(value))
    if "." in abs_str:
        integer_part, decimal_part = abs_str.split(".")
        integer_part = _format_thousands_fr(integer_part).replace(_NBSP, _NNBSP)
        body = f"{integer_part},{decimal_part}"
    else:
        integer_part = _format_thousands_fr(abs_str).replace(_NBSP, _NNBSP)
        body = integer_part

    if signed:
        sign = "-" if value < 0 else "+"
        return f"{sign}{body}{_NNBSP}%"
    return f"{body}{_NNBSP}%"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers divers
# ─────────────────────────────────────────────────────────────────────────────


_HEX64 = re.compile(r"^[a-f0-9]{64}$")


def is_sha256_hex(s: str) -> bool:
    """True si `s` est un hex SHA256 (64 chars lowercase)."""
    return bool(_HEX64.match(s))


__all__ = [
    "now_utc",
    "hash_inputs",
    "generate_correlation_id",
    "generate_cancellation_token",
    "generate_confirmation_token",
    "verify_confirmation_token",
    "fmt_eur",
    "fmt_mwh",
    "fmt_pct",
    "is_sha256_hex",
]
