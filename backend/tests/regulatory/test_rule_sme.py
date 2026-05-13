"""PROMEOS — Tests Vague A.4 : SMEEvaluator (Audit énergétique L233-1)."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from regulatory.applicability_types import ApplicabilityStatus, RuleCode
from regulatory.reason_codes import REASON_CODES
from regulatory.rules.sme import (
    SME_DEADLINE,
    SME_EFFECTIF_THRESHOLD,
    SMEEvaluator,
)


def _org(id: int = 1, nom: str = "Org Test", effectif_total=None, chiffre_affaires_eur=None, bilan_eur=None):
    org = SimpleNamespace(
        id=id,
        nom=nom,
        effectif_total=effectif_total,
        chiffre_affaires_eur=chiffre_affaires_eur,
    )
    if bilan_eur is not None:
        org.bilan_eur = bilan_eur
    return org


def _audit_sme(conso_annuelle_moy_gwh=None):
    return SimpleNamespace(conso_annuelle_moy_gwh=conso_annuelle_moy_gwh)


def test_sme_applicable_effectif():
    """Effectif 380 → APPLICABLE.EFFECTIF deadline 11/10/2026."""
    org = _org(nom="HELIOS", effectif_total=380)
    app = SMEEvaluator().evaluate(org)
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.reason_code == "SME.APPLICABLE.EFFECTIF"
    assert app.deadline == SME_DEADLINE


def test_sme_applicable_effectif_at_threshold():
    """Effectif = exactement seuil → APPLICABLE."""
    org = _org(effectif_total=SME_EFFECTIF_THRESHOLD)
    app = SMEEvaluator().evaluate(org)
    assert app.status == ApplicabilityStatus.APPLICABLE


def test_sme_applicable_ca_bilan():
    """CA + bilan tous deux ≥ seuils → APPLICABLE.CA_BILAN."""
    org = _org(effectif_total=100, chiffre_affaires_eur=55_000_000, bilan_eur=48_000_000)
    app = SMEEvaluator().evaluate(org)
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.reason_code == "SME.APPLICABLE.CA_BILAN"


def test_sme_not_applicable_ca_alone_no_bilan():
    """CA ≥ 50M€ mais bilan absent → NOT_APPLICABLE (le critère exige les deux)."""
    org = _org(effectif_total=100, chiffre_affaires_eur=80_000_000)
    app = SMEEvaluator().evaluate(org)
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE


def test_sme_applicable_conso():
    """Conso > 2.75 GWh via AuditSME → APPLICABLE.CONSO_GT_THRESHOLD."""
    org = _org(effectif_total=80)
    audit = _audit_sme(conso_annuelle_moy_gwh=5.2)
    app = SMEEvaluator().evaluate(org, audit)
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.reason_code == "SME.APPLICABLE.CONSO_GT_THRESHOLD"


def test_sme_effectif_priority_over_conso():
    """Effectif > seuil prime sur conso > seuil (reason_code EFFECTIF)."""
    org = _org(effectif_total=400)
    audit = _audit_sme(conso_annuelle_moy_gwh=5.0)
    app = SMEEvaluator().evaluate(org, audit)
    assert app.reason_code == "SME.APPLICABLE.EFFECTIF"


def test_sme_not_applicable_pme():
    """Effectif 80 + CA 10M + conso 0.5 GWh tous renseignés → NOT_APPLICABLE.PME.

    Phase 3.7 KK : avec bijection reason_codes, le statut PME requiert
    explicitement les 3 critères présents (sinon DATA_MISSING.XXX précis).
    """
    org = _org(effectif_total=80, chiffre_affaires_eur=10_000_000)
    audit = _audit_sme(conso_annuelle_moy_gwh=0.5)  # conso < seuil
    app = SMEEvaluator().evaluate(org, audit)
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE
    assert app.reason_code == "SME.NOT_APPLICABLE.PME"


def test_sme_data_missing_all_absent():
    """Aucun champ renseigné → DATA_MISSING."""
    org = _org(effectif_total=None, chiffre_affaires_eur=None)
    app = SMEEvaluator().evaluate(org)
    assert app.status == ApplicabilityStatus.DATA_MISSING
    assert app.reason_code == "SME.DATA_MISSING.EFFECTIF"
    assert "organisation.effectif_total" in app.missing_inputs


def test_sme_reason_codes_in_whitelist():
    cases = [
        (_org(effectif_total=400), None),  # APPLICABLE.EFFECTIF
        (_org(effectif_total=100, chiffre_affaires_eur=55e6, bilan_eur=45e6), None),  # CA_BILAN
        (_org(effectif_total=100), _audit_sme(conso_annuelle_moy_gwh=5)),  # CONSO_GT
        (_org(effectif_total=80, chiffre_affaires_eur=10e6), None),  # NOT_APPLICABLE.PME
        (_org(effectif_total=None, chiffre_affaires_eur=None), None),  # DATA_MISSING
    ]
    for org, audit in cases:
        app = SMEEvaluator().evaluate(org, audit)
        assert app.reason_code in REASON_CODES, f"reason_code {app.reason_code} hors whitelist"


def test_sme_evaluator_constants():
    e = SMEEvaluator()
    assert e.code == RuleCode.SME
    assert e.scope == "organisation"
