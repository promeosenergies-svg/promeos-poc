"""
PROMEOS — Source-guards Phase L29.2 — invariants metadata YAML sources_reglementaires.

Garantit la cohérence et la complétude du tagging metadata pour pilot-readiness
pré-prod externe (audit trail légal opposable Marie DAF / Jean-Marc CFO).

Patterns vérifiés :
- SG_REG_YAML_06 : 9 clés stables ont confidence: high explicite (anti-régression L29.1)
- SG_REG_YAML_07 : confidence: low ⇒ status: pending_source_verification ou internal_heuristic
- SG_REG_YAML_08 : status ∈ allowlist {verified, pending_source_verification, internal_doctrine,
  internal_heuristic, market_observatory, internal_fallback}
- SG_REG_YAML_09 : status pending_source_verification ⇒ confidence ∈ {low, medium}
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# Clés stables Phase L29.1 — DOIVENT avoir confidence: high
_STABLE_KEYS_REQUIRE_CONFIDENCE_HIGH = frozenset(
    {
        "ACCISE_ELEC_T1_EUR_PER_MWH",
        "ACCISE_ELEC_T2_EUR_PER_MWH",
        "ACCISE_GAZ_EUR_PER_MWH",
        "COMPLIANCE_DT_PENALTY_EUR",
        "COMPLIANCE_OPERAT_PENALTY_EUR",
        "BACS_THRESHOLD_KW_2025",
        "COMPLIANCE_BACS_PENALTY_EUR",
        "AUDIT_SME_THRESHOLD_GWH_PERIODIC",
        "AUDIT_SME_THRESHOLD_GWH_ISO50001",
        # Ajoutés Phase L28.2 (BACS_DEADLINE refactor cardinal — Décret 2025-1343
        # art. 1 + Décret 2020-887 art. R175-3, 4 sources internes convergentes ADR-027)
        "BACS_DEADLINE_EXISTING_70_290",
        "BACS_DEADLINE_ABOVE_290",
        # Ajouté Phase L30.1 (Décret 2025-1343 publié JO 26/12/2025 — opposable)
        "BACS_THRESHOLD_KW_2030",
    }
)

_VALID_STATUS = frozenset(
    {
        "verified",
        "pending_source_verification",
        "internal_doctrine",
        "internal_heuristic",
        "market_observatory",
        "internal_fallback",
    }
)


def _load_yaml_data() -> dict:
    """Helper : charge le YAML via le loader canonical."""
    from config.regulatory_sources_loader import reload_regulatory_sources

    return reload_regulatory_sources()


# ─── SG_REG_YAML_06 : confidence: high explicit sur 11 clés stables ─────────


def test_sg_reg_yaml_06_stable_keys_have_confidence_high():
    """Phase L29.2 audit fix P1 — Anti-régression : 11 clés stables doivent avoir
    confidence: 'high' explicite. Audit trail légal opposable pour pilot-readiness
    pré-prod externe (Marie DAF / Jean-Marc CFO doivent justifier "d'où vient ce
    7500 € ?" en 1 clic).
    """
    data = _load_yaml_data()
    terms = data["terms"]
    offenders: list[str] = []
    for key in _STABLE_KEYS_REQUIRE_CONFIDENCE_HIGH:
        if key not in terms:
            offenders.append(f"{key}: clé stable manquante")
            continue
        confidence = terms[key].get("confidence")
        if confidence != "high":
            offenders.append(f"{key}: confidence={confidence!r} (attendu 'high')")
    assert not offenders, "Clés stables sans confidence: high :\n  - " + "\n  - ".join(offenders)


# ─── SG_REG_YAML_07 : status ∈ allowlist ────────────────────────────────────


def test_sg_reg_yaml_07_status_values_in_allowlist():
    """Phase L29.2 audit fix P1 — Tout terme avec champ status doit utiliser une
    valeur ∈ allowlist (verified, pending_source_verification, internal_doctrine,
    internal_heuristic, market_observatory, internal_fallback)."""
    data = _load_yaml_data()
    offenders: list[str] = []
    for key, term in data["terms"].items():
        status = term.get("status")
        if status is not None and status not in _VALID_STATUS:
            offenders.append(f"{key}: status={status!r} hors allowlist {sorted(_VALID_STATUS)}")
    assert not offenders, "Status hors allowlist :\n  - " + "\n  - ".join(offenders)


# ─── SG_REG_YAML_08 : confidence: low ⇒ status: pending_source_verification ─


def test_sg_reg_yaml_08_low_confidence_requires_pending_status():
    """Phase L29.2 audit fix P1 — Cohérence SENTINEL-REG : confidence: 'low'
    ⇒ status: 'pending_source_verification' OU 'internal_heuristic'.

    Une valeur réglementaire externe avec confidence low SANS status pending
    serait une dette silencieuse (utilisateur pilote verrait la valeur affichée
    avec confiance implicite alors qu'elle est non-vérifiée).
    """
    data = _load_yaml_data()
    offenders: list[str] = []
    for key, term in data["terms"].items():
        confidence = term.get("confidence")
        status = term.get("status", "verified")
        if confidence == "low" and status not in (
            "pending_source_verification",
            "internal_heuristic",
        ):
            offenders.append(
                f"{key}: confidence='low' avec status={status!r} (attendu pending_source_verification ou internal_heuristic)"
            )
    assert not offenders, "Cohérence confidence/status violée :\n  - " + "\n  - ".join(offenders)


# ─── SG_REG_YAML_09 : status pending ⇒ confidence ∈ {low, medium} ───────────


def test_sg_reg_yaml_09_pending_status_requires_low_or_medium_confidence():
    """Phase L29.2 audit fix P1 — Cohérence SENTINEL-REG : status
    'pending_source_verification' ⇒ confidence ∈ {'low', 'medium'} explicite.

    Un terme pending DOIT avoir confidence explicite (jamais 'high' implicite),
    pour que le frontend (TraceTooltip) affiche la bannière warning ambre."""
    data = _load_yaml_data()
    offenders: list[str] = []
    for key, term in data["terms"].items():
        status = term.get("status")
        if status == "pending_source_verification":
            confidence = term.get("confidence")
            if confidence not in ("low", "medium"):
                offenders.append(
                    f"{key}: status=pending_source_verification avec confidence={confidence!r} (attendu 'low' ou 'medium')"
                )
    assert not offenders, "Status pending sans confidence faible :\n  - " + "\n  - ".join(offenders)
