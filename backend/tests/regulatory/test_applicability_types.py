"""PROMEOS — Tests Vague A.1 : types canoniques du moteur d'assujettissement.

Référence : `docs/adr/ADR-024-moteur-assujettissement.md` §1 + §8 source-guards.

Couverture exigée Phase 3.5 A.1 :
    1. Instanciation APPLICABLE valide
    2. Instanciation NOT_APPLICABLE valide
    3. Instanciation UNKNOWN valide
    4. Instanciation DATA_MISSING valide (avec missing_inputs non vide)
    5. frozen=True : mutation lève FrozenInstanceError
    6. _audit complet : 5 clés requises (doctrine_version, evaluated_at,
       evaluator, evaluator_version, data_source)
    7. Validation scope_level (frozenset SCOPE_LEVELS)
    8. Validation confidence ∈ [0.0, 1.0]
    9. DATA_MISSING sans missing_inputs lève ValueError
   10. Sérialisation to_dict() complète et JSON-ready
   11. RuleCode + ApplicabilityStatus exhaustifs
   12. REASON_CODES whitelist non vide et fermée
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone

import pytest

from regulatory.applicability_types import (
    DOCTRINE_VERSION,
    SCOPE_LEVELS,
    ApplicabilityStatus,
    RuleApplicability,
    RuleCode,
)
from regulatory.reason_codes import REASON_CODES, is_valid_reason_code


# ── Fixtures partagées ──────────────────────────────────────────────────────


@pytest.fixture
def audit_complete() -> dict:
    """_audit minimal valide pour instancier un RuleApplicability."""
    return {
        "doctrine_version": DOCTRINE_VERSION,
        "evaluated_at": datetime(2026, 5, 13, 10, 0, tzinfo=timezone.utc).isoformat(),
        "evaluator": "DTEvaluator",
        "evaluator_version": "DT-2019-771-v2024-10-01",
        "data_source": "models.Site.tertiaire_area_m2",
    }


# ── 1-4 : 4 statuts × instanciation ─────────────────────────────────────────


def test_instantiate_applicable(audit_complete):
    """Cas 1 — APPLICABLE : règle s'applique, trajectoire visible."""
    app = RuleApplicability(
        rule_code=RuleCode.DT,
        rule_version="DT-2019-771-v2024-10-01",
        scope_level="site",
        scope_id=42,
        scope_label="Site Toulouse Entrepôt",
        status=ApplicabilityStatus.APPLICABLE,
        reason_code="DT.APPLICABLE",
        reason_human="Site Toulouse Entrepôt : SDP 1 820 m² ≥ 1 000 m², usage tertiaire.",
        inputs_used={"tertiaire_area_m2": 1820, "usage_principal": "bureau"},
        deadline=date(2030, 12, 31),
        _audit=audit_complete,
    )
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.rule_code == RuleCode.DT
    assert app.deadline == date(2030, 12, 31)
    assert app.confidence == 1.0  # défaut


def test_instantiate_not_applicable(audit_complete):
    """Cas 2 — NOT_APPLICABLE : règle ne s'applique pas."""
    app = RuleApplicability(
        rule_code=RuleCode.DT,
        rule_version="DT-2019-771-v2024-10-01",
        scope_level="site",
        scope_id=12,
        scope_label="Site Lyon Bureaux",
        status=ApplicabilityStatus.NOT_APPLICABLE,
        reason_code="DT.NOT_APPLICABLE.SDP_LT_1000",
        reason_human="Site Lyon Bureaux : SDP 850 m² < 1 000 m². Décret tertiaire non applicable.",
        inputs_used={"tertiaire_area_m2": 850},
        _audit=audit_complete,
    )
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE
    assert app.deadline is None


def test_instantiate_unknown(audit_complete):
    """Cas 3 — UNKNOWN : statut indéterminable (usage mixte par ex.)."""
    app = RuleApplicability(
        rule_code=RuleCode.DT,
        rule_version="DT-2019-771-v2024-10-01",
        scope_level="site",
        scope_id=7,
        scope_label="Site Paris Mixte",
        status=ApplicabilityStatus.UNKNOWN,
        reason_code="DT.UNKNOWN.USAGE_MIXTE",
        reason_human="Site Paris Mixte : usage mixte. Qualification fine requise pour statuer.",
        inputs_used={"usage_principal": "mixte", "tertiaire_area_m2": 2400},
        confidence=0.5,
        _audit=audit_complete,
    )
    assert app.status == ApplicabilityStatus.UNKNOWN
    assert app.confidence == 0.5


def test_instantiate_data_missing(audit_complete):
    """Cas 4 — DATA_MISSING : champs patrimoine manquants."""
    app = RuleApplicability(
        rule_code=RuleCode.DT,
        rule_version="DT-2019-771-v2024-10-01",
        scope_level="site",
        scope_id=99,
        scope_label="Site Nice Hôtel",
        status=ApplicabilityStatus.DATA_MISSING,
        reason_code="DT.DATA_MISSING.SURFACE",
        reason_human="Site Nice Hôtel : surface tertiaire non renseignée.",
        missing_inputs=["site.tertiaire_area_m2"],
        confidence=0.0,
        _audit=audit_complete,
    )
    assert app.status == ApplicabilityStatus.DATA_MISSING
    assert app.missing_inputs == ["site.tertiaire_area_m2"]


# ── 5 : Immuabilité ─────────────────────────────────────────────────────────


def test_frozen_instance_blocks_mutation(audit_complete):
    """Cas 5 — frozen=True : toute mutation lève FrozenInstanceError."""
    app = RuleApplicability(
        rule_code=RuleCode.BACS,
        rule_version="BACS-2020-887-v2025-01-01",
        scope_level="site",
        scope_id=1,
        scope_label="Site test",
        status=ApplicabilityStatus.APPLICABLE,
        reason_code="BACS.APPLICABLE",
        reason_human="Bâtiment > seuil CVC.",
        _audit=audit_complete,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        app.status = ApplicabilityStatus.NOT_APPLICABLE  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        app.reason_code = "HACK"  # type: ignore[misc]


# ── 6 : Audit complet ──────────────────────────────────────────────────────


def test_audit_complete_required(audit_complete):
    """Cas 6 — _audit doit contenir les 5 clés requises."""
    app = RuleApplicability(
        rule_code=RuleCode.SME,
        rule_version="SME-L233-1-v2023-12-31",
        scope_level="organisation",
        scope_id=1,
        scope_label="Organisation HELIOS SAS",
        status=ApplicabilityStatus.APPLICABLE,
        reason_code="SME.APPLICABLE.EFFECTIF",
        reason_human="Effectif total 380 ≥ 250. Audit énergétique obligatoire.",
        _audit=audit_complete,
    )
    for key in ("doctrine_version", "evaluated_at", "evaluator", "evaluator_version", "data_source"):
        assert key in app._audit, f"Clé _audit manquante: {key}"
    assert app._audit["doctrine_version"] == DOCTRINE_VERSION


def test_audit_incomplete_raises(audit_complete):
    """Cas 6 bis — _audit incomplet doit lever ValueError."""
    audit_broken = {k: v for k, v in audit_complete.items() if k != "evaluator_version"}
    with pytest.raises(ValueError, match="_audit incomplet"):
        RuleApplicability(
            rule_code=RuleCode.SME,
            rule_version="SME-L233-1-v2023-12-31",
            scope_level="organisation",
            scope_id=1,
            scope_label="Org test",
            status=ApplicabilityStatus.APPLICABLE,
            reason_code="SME.APPLICABLE.EFFECTIF",
            reason_human="Effectif 250.",
            _audit=audit_broken,
        )


# ── 7-8 : Validations supplémentaires ──────────────────────────────────────


def test_scope_level_invalid_raises(audit_complete):
    """scope_level hors SCOPE_LEVELS doit lever ValueError."""
    with pytest.raises(ValueError, match="scope_level invalide"):
        RuleApplicability(
            rule_code=RuleCode.DT,
            rule_version="DT-v1",
            scope_level="batiment",  # ❌ hors whitelist
            scope_id=1,
            scope_label="X",
            status=ApplicabilityStatus.APPLICABLE,
            reason_code="DT.APPLICABLE",
            reason_human="ok",
            _audit=audit_complete,
        )


def test_confidence_out_of_range_raises(audit_complete):
    """confidence ∉ [0, 1] doit lever ValueError."""
    for bad in (-0.1, 1.5, 2.0):
        with pytest.raises(ValueError, match="confidence"):
            RuleApplicability(
                rule_code=RuleCode.DT,
                rule_version="DT-v1",
                scope_level="site",
                scope_id=1,
                scope_label="X",
                status=ApplicabilityStatus.APPLICABLE,
                reason_code="DT.APPLICABLE",
                reason_human="ok",
                confidence=bad,
                _audit=audit_complete,
            )


def test_data_missing_without_inputs_raises(audit_complete):
    """DATA_MISSING sans missing_inputs doit lever ValueError (source-guard ADR-024 §8)."""
    with pytest.raises(ValueError, match="DATA_MISSING exige missing_inputs"):
        RuleApplicability(
            rule_code=RuleCode.DT,
            rule_version="DT-v1",
            scope_level="site",
            scope_id=1,
            scope_label="X",
            status=ApplicabilityStatus.DATA_MISSING,
            reason_code="DT.DATA_MISSING.SURFACE",
            reason_human="Surface manquante.",
            missing_inputs=[],  # ❌ vide
            _audit=audit_complete,
        )


# ── 9 : Sérialisation ──────────────────────────────────────────────────────


def test_to_dict_complete_json_ready(audit_complete):
    """to_dict() doit produire un payload JSON-ready exhaustif."""
    app = RuleApplicability(
        rule_code=RuleCode.APER,
        rule_version="APER-2023-175-v2024-07-01",
        scope_level="site",
        scope_id=42,
        scope_label="Site Toulouse Entrepôt",
        status=ApplicabilityStatus.APPLICABLE,
        reason_code="APER.APPLICABLE.PARKING",
        reason_human="Parking 1 850 m² ≥ 1 500 m².",
        inputs_used={"parking_area_m2": 1850},
        evidence_refs=["NOR:TREL2305175L"],
        next_review_date=date(2027, 7, 1),
        deadline=date(2026, 7, 1),
        _audit=audit_complete,
    )
    d = app.to_dict()
    assert d["rule_code"] == "APER"
    assert d["status"] == "applicable"
    assert d["reason_code"] == "APER.APPLICABLE.PARKING"
    assert d["deadline"] == "2026-07-01"
    assert d["next_review_date"] == "2027-07-01"
    assert d["evidence_refs"] == ["NOR:TREL2305175L"]
    assert d["inputs_used"] == {"parking_area_m2": 1850}
    assert d["_audit"]["evaluator"] == "DTEvaluator"  # vient de audit_complete fixture


# ── 10-12 : Énumérations + whitelist ───────────────────────────────────────


def test_rule_code_enum_complete():
    """RuleCode v1.0 = exactement 5 règles (DT, BACS, APER, SME, BEGES)."""
    assert {r.value for r in RuleCode} == {"DT", "BACS", "APER", "SME", "BEGES"}


def test_status_enum_complete():
    """ApplicabilityStatus v1.0 = exactement 4 statuts cardinaux."""
    assert {s.value for s in ApplicabilityStatus} == {
        "applicable",
        "not_applicable",
        "unknown",
        "data_missing",
    }


def test_scope_levels_frozen():
    """SCOPE_LEVELS doit être une frozenset (immuable)."""
    assert isinstance(SCOPE_LEVELS, frozenset)
    assert SCOPE_LEVELS == frozenset({"site", "organisation", "portefeuille"})


def test_reason_codes_whitelist_non_empty():
    """REASON_CODES doit contenir au minimum un code par règle × statut clef."""
    assert len(REASON_CODES) >= 20, "Whitelist v1.0 doit couvrir 5 règles × 4 statuts au minimum."
    # Chaque règle doit avoir au moins un code APPLICABLE
    for rule in ("DT", "BACS", "APER", "SME", "BEGES"):
        applicable_codes = [c for c in REASON_CODES if c.startswith(f"{rule}.APPLICABLE")]
        assert applicable_codes, f"Aucun code APPLICABLE pour {rule}"


def test_is_valid_reason_code():
    """is_valid_reason_code() — fonction utilitaire."""
    assert is_valid_reason_code("DT.APPLICABLE")
    assert is_valid_reason_code("BACS.NOT_APPLICABLE.NO_SYSTEM_GT_THRESHOLD")
    assert not is_valid_reason_code("DT.HACK")
    assert not is_valid_reason_code("")
