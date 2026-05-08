"""
PROMEOS — PII sanitizer SoT centralisé (Phase D-3 Tier 2 SEC-2 fix P1-AUDIT-D-014).

Module unique cardinal pour la sanitization PII cross-services.

Avant Phase D-3 : 2 SoT distincts (anti-pattern documenté audit Phase D) :
- `services/audit_log_service.py:_SENSITIVE_KEY_PATTERNS` (clés audit)
- `services/bill_intelligence/anomaly_detector.py:_PII_PATTERNS` (regex valeurs)

Cette duplication créait un risque cardinal : ajout d'un pattern dans un seul SoT
sans propagation à l'autre = leak PII silencieux. Cf audit `AUDIT_PHASE_D_COMPLET_2026_05_07.md`
finding P1-AUDIT-D-014.

Pattern Pilier 13 ADR-016 candidat : "SoT cross-services centralisé pour patterns
réglementaires/sécurité — pas de duplication tolérée".

Usage :
    from services.security.pii_sanitizer import (
        sanitize_pii_value,
        is_sensitive_key,
        is_hash_key,
        PII_VALUE_PATTERNS,
        SENSITIVE_KEY_PATTERNS,
        SENSITIVE_KEY_NON_PII_ALLOWLIST,
    )
"""

from __future__ import annotations

import re
from typing import Pattern

# ═══════════════════════════════════════════════════════════════════════════
# Patterns valeurs PII (regex)
# Source : services/bill_intelligence/anomaly_detector.py:_PII_PATTERNS Phase D-1
# Ordre cardinal du plus spécifique (long+structuré) au plus générique (court).
# Anti faux-positifs labels EDF/Engie codes internes numériques.
# ═══════════════════════════════════════════════════════════════════════════

# Patterns nommés exportés (Phase D-4 Tier 4 P1 fix audit code-reviewer — anti-couplage index positionnel)
EMAIL_RFC5322_PATTERN: Pattern[str] = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
"""Email RFC 5322 simplifié (matchage substring). Pour validator strict, utiliser fullmatch()."""

IBAN_FR_PATTERN: Pattern[str] = re.compile(r"\bFR\d{2}[\s]?(?:[A-Z0-9]{4}[\s]?){5}[A-Z0-9]{3}\b")
"""IBAN FR 27 chars."""

PHONE_FR_INTL_PATTERN: Pattern[str] = re.compile(r"(?<!\w)\+33[\s.-]?[1-9](?:[\s.-]?\d{2}){4}(?!\d)")
"""Téléphone FR international +33."""

SIRET_PRM_PCE_PATTERN: Pattern[str] = re.compile(r"\b\d{14}\b")
"""SIRET / PRM / PCE / PDL — 14 chiffres."""

PHONE_FR_NATIONAL_PATTERN: Pattern[str] = re.compile(r"\b0[1-9](?:[\s.-]?\d{2}){4}\b")
"""Téléphone FR fixe/mobile 0X XX XX XX XX."""

SIREN_PATTERN: Pattern[str] = re.compile(r"\b\d{9}\b")
"""SIREN 9 chiffres (le plus court/risqué montants — last)."""

PII_VALUE_PATTERNS: tuple[Pattern[str], ...] = (
    # Patterns structurés (préfixe alphabétique → plus spécifiques)
    IBAN_FR_PATTERN,  # IBAN FR (27 chars)
    EMAIL_RFC5322_PATTERN,  # Email RFC 5322
    PHONE_FR_INTL_PATTERN,  # Téléphone FR international
    # Patterns numériques (longs → courts)
    SIRET_PRM_PCE_PATTERN,  # SIRET / PRM / PCE / PDL (14 chiffres)
    PHONE_FR_NATIONAL_PATTERN,  # Téléphone FR fixe/mobile
    SIREN_PATTERN,  # SIREN (9 chiffres) — last
    # `\b\d{10}\b` PCE court legacy GRDF — RETIRÉ Phase D-1 (faux-positifs montants TURPE).
)

PII_REDACTED = "<PII_REDACTED>"


def sanitize_pii_value(value: str) -> str:
    """Masque les identifiants PII (SIREN/SIRET/PRM/PCE/email/IBAN/téléphone) dans une chaîne.

    Retourne la chaîne avec chaque match remplacé par `<PII_REDACTED>`.
    Cohérent ordre cardinal patterns (structurés → numériques décroissants).
    """
    if not value:
        return value
    sanitized = value
    for pattern in PII_VALUE_PATTERNS:
        sanitized = pattern.sub(PII_REDACTED, sanitized)
    return sanitized


# ═══════════════════════════════════════════════════════════════════════════
# Patterns clés sensibles (substring case-insensitive)
# Source : services/audit_log_service.py:_SENSITIVE_KEY_PATTERNS Phase 7.5+8.2
# ═══════════════════════════════════════════════════════════════════════════

SENSITIVE_KEY_PATTERNS: tuple[str, ...] = (
    # Phase 7.5 baseline (auth/secret)
    "authorization",
    "bearer",
    "client_secret",
    "secret",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "code_verifier",
    "code_challenge",
    "password",
    "passwd",
    # Phase 8.2 EXTENSION (PII personnels)
    "email",
    "telephone",
    "phone",
    "iban",
    "rib",
    "bic",
    "adresse",
    "address",
    "birth_date",
    "birthdate",
    "date_naissance",
)

# Allowlist Phase 8.4 — keys techniques non-PII contenant un pattern sensible.
SENSITIVE_KEY_NON_PII_ALLOWLIST: frozenset[str] = frozenset(
    {
        "ip_address",  # IP HTTP audit trail (CNIL article 5(2) accountability)
        "mac_address",  # MAC réseau hardware (non-PII direct)
        "url_address",  # URL endpoint
        "user_agent",  # HTTP User-Agent (déjà tracé via cx_logger)
    }
)

# Champs identifiants à hasher (PRM/PCE/SIREN/SIRET) plutôt que redact.
HASH_KEY_PATTERNS: tuple[str, ...] = (
    "prm",
    "pce",
    "siren",
    "siret",
    "usage_point_id",
    # `code` est traité par exact match strict (Phase 8.3 fix overmatch period_code/error_code).
)

HASH_KEY_EXACT_MATCH: frozenset[str] = frozenset({"code"})


def is_sensitive_key(key: str) -> bool:
    """True si la clé contient un pattern sensible (case-insensitive).

    Allowlist `SENSITIVE_KEY_NON_PII_ALLOWLIST` exclut `ip_address`/`mac_address`/etc.
    (keys techniques non-PII préservées audit trail CNIL article 5(2) accountability).
    """
    lk = (key or "").lower()
    if lk in SENSITIVE_KEY_NON_PII_ALLOWLIST:
        return False
    return any(p in lk for p in SENSITIVE_KEY_PATTERNS)


def is_hash_key(key: str) -> bool:
    """True si la clé contient un identifiant à hasher (PRM/PCE/SIREN/...).

    `code` traité en exact match strict (Phase 8.3 fix anti overmatch period_code/error_code).
    """
    lk = (key or "").lower()
    if lk in HASH_KEY_EXACT_MATCH:
        return True
    return any(p in lk for p in HASH_KEY_PATTERNS)
