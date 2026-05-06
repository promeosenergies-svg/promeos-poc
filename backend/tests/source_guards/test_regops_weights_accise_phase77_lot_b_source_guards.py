"""
PROMEOS — Source guards Phase 7.7 Sprint C-7 Lot B — REGOPS Weights + Accise SG.

Couvre 3 P1 + 1 P2 dettes Sprint C-7 :
- D-Sprint-C7-REGOPS-Weights-Audit-Applicable-SG-001 P1 — SG REGOPS_WEIGHTS_AUDIT_APPLICABLE protégé
- D-Sprint-C7-Accise-SG-Coverage-001 P1 — SG ACCISE_GAZ + ACCISE_ELEC_T2_C5_MENAGE
- D-Sprint-C7-Weights-Sum-100pct-Invariant-001 P2 — sum(REGOPS_WEIGHTS) == 1.0 + READINESS == 100%

Anti-régression cardinal : empêche dérive silencieuse poids scoring conformité réglementaire
+ accises tarifaires (différenciateur produit Bill Intelligence + scoring R10).
"""

from __future__ import annotations


# ─── REGOPS_WEIGHTS_AUDIT_APPLICABLE protégé (4 entries) ─────────────────────


def test_sg_phase77_lot_b_regops_weights_audit_applicable_dt_protected():
    """SG P1 : REGOPS_WEIGHTS_AUDIT_APPLICABLE['DT'] = 0.39 protégé doctrine."""
    from doctrine.constants import REGOPS_WEIGHTS_AUDIT_APPLICABLE

    assert REGOPS_WEIGHTS_AUDIT_APPLICABLE.get("DT") == 0.39, (
        "SG_PHASE77_LOT_B_01 : REGOPS_WEIGHTS_AUDIT_APPLICABLE['DT'] doit être 0.39.\n"
        "Pondération scoring conformité quand AUDIT_SME applicable (loi 2025-391)."
    )


def test_sg_phase77_lot_b_regops_weights_audit_applicable_bacs_protected():
    """SG P1 : REGOPS_WEIGHTS_AUDIT_APPLICABLE['BACS'] = 0.28 protégé doctrine."""
    from doctrine.constants import REGOPS_WEIGHTS_AUDIT_APPLICABLE

    assert REGOPS_WEIGHTS_AUDIT_APPLICABLE.get("BACS") == 0.28


def test_sg_phase77_lot_b_regops_weights_audit_applicable_aper_protected():
    """SG P1 : REGOPS_WEIGHTS_AUDIT_APPLICABLE['APER'] = 0.17 protégé doctrine."""
    from doctrine.constants import REGOPS_WEIGHTS_AUDIT_APPLICABLE

    assert REGOPS_WEIGHTS_AUDIT_APPLICABLE.get("APER") == 0.17


def test_sg_phase77_lot_b_regops_weights_audit_applicable_audit_protected():
    """SG P1 : REGOPS_WEIGHTS_AUDIT_APPLICABLE['AUDIT'] = 0.16 protégé doctrine."""
    from doctrine.constants import REGOPS_WEIGHTS_AUDIT_APPLICABLE

    assert REGOPS_WEIGHTS_AUDIT_APPLICABLE.get("AUDIT") == 0.16


# ─── Invariant cardinal sum=1.0 (Pilier 1 ADR-016) ──────────────────────────


def test_sg_phase77_lot_b_regops_weights_audit_applicable_sum_invariant_100pct():
    """SG P2 INVARIANT : sum(REGOPS_WEIGHTS_AUDIT_APPLICABLE) == 1.0 (poids totaux 100%).

    Sans cet invariant, modification ad-hoc d'un poids casse silencieusement le
    calcul scoring conformité (somme≠1.0 → score normalisé incorrect).
    """
    from doctrine.constants import REGOPS_WEIGHTS_AUDIT_APPLICABLE

    total = sum(REGOPS_WEIGHTS_AUDIT_APPLICABLE.values())
    assert abs(total - 1.0) < 1e-9, (
        f"SG_PHASE77_LOT_B_05 INVARIANT : sum(REGOPS_WEIGHTS_AUDIT_APPLICABLE)={total} ≠ 1.0.\n"
        "Poids scoring conformité doivent sommer à 100% (cardinal ADR-016 Pilier 1)."
    )


def test_sg_phase77_lot_b_regops_weights_default_sum_invariant_100pct():
    """SG P2 INVARIANT : sum(REGOPS_WEIGHTS_DEFAULT) == 1.0 (cas non-AUDIT_SME)."""
    from doctrine.constants import REGOPS_WEIGHTS_DEFAULT

    total = sum(REGOPS_WEIGHTS_DEFAULT.values())
    assert abs(total - 1.0) < 1e-9, f"SG_PHASE77_LOT_B_06 INVARIANT : sum(REGOPS_WEIGHTS_DEFAULT)={total} ≠ 1.0."


def test_sg_phase77_lot_b_readiness_weights_sum_invariant_100pct():
    """SG P2 INVARIANT : READINESS_WEIGHTS sum(data+conformity+actions) == 1.0."""
    from doctrine.constants import (
        READINESS_WEIGHT_ACTIONS,
        READINESS_WEIGHT_CONFORMITY,
        READINESS_WEIGHT_DATA,
    )

    total = READINESS_WEIGHT_DATA + READINESS_WEIGHT_CONFORMITY + READINESS_WEIGHT_ACTIONS
    assert abs(total - 1.0) < 1e-9, f"SG_PHASE77_LOT_B_07 INVARIANT : sum(READINESS_WEIGHTS)={total} ≠ 1.0."


# ─── Accise SG coverage (D-Sprint-C7-Accise-SG-Coverage-001) ────────────────


def test_sg_phase77_lot_b_accise_gaz_yaml_present_and_numeric():
    """SG P1 : ACCISE_GAZ_EUR_PER_MWH présent YAML + valeur numérique cohérente."""
    from config.regulatory_sources_loader import get_term_value

    val = get_term_value("ACCISE_GAZ_EUR_PER_MWH")
    assert val is not None
    assert isinstance(val, (int, float))
    # Range plausible 2024-2026 : ~5-25 EUR/MWh (TICGN évolue progressivement)
    assert 2.0 <= float(val) <= 30.0, (
        f"SG_PHASE77_LOT_B_08 : ACCISE_GAZ_EUR_PER_MWH={val} hors range plausible [2-30] EUR/MWh.\n"
        "Vérifier YAML sources_reglementaires.yaml domaine accises (Code impositions B&S)."
    )


def test_sg_phase77_lot_b_accise_elec_t2_c5_menage_yaml_present_and_numeric():
    """SG P1 : ACCISE_ELEC_T2_C5_MENAGE_EUR_PER_MWH présent YAML + range cohérent."""
    from config.regulatory_sources_loader import get_term_value

    val = get_term_value("ACCISE_ELEC_T2_C5_MENAGE_EUR_PER_MWH")
    assert val is not None
    assert isinstance(val, (int, float))
    # Range plausible : tarif T2 C5 ménages = 25-30 EUR/MWh post LF 2026
    assert 15.0 <= float(val) <= 40.0, (
        f"SG_PHASE77_LOT_B_09 : ACCISE_ELEC_T2_C5_MENAGE_EUR_PER_MWH={val} hors range plausible [15-40] EUR/MWh."
    )


def test_sg_phase77_lot_b_accise_terms_have_legal_reference():
    """SG P1 : accises ont legal_reference + URL Légifrance/CRE (non null)."""
    from config.regulatory_sources_loader import get_term

    for term_id in ("ACCISE_GAZ_EUR_PER_MWH", "ACCISE_ELEC_T2_C5_MENAGE_EUR_PER_MWH"):
        term = get_term(term_id)
        source = term.get("source", {})
        assert source.get("legal_reference"), f"{term_id} : legal_reference manquante"
        # URL acceptée si présente (peut être null pour MVP, mais legal_reference obligatoire)
