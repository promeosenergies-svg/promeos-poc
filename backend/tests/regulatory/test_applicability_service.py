"""PROMEOS — Tests Vague A.5 : applicability_service (catalogue + compute_*).

Couverture :
  - compute_applicability retourne 5 RuleCode keys avec entrées typées
  - Règles site-scoped : une entrée par site (DT, BACS, APER)
  - Règles org-scoped : exactement 1 entrée (SMÉ, BEGES)
  - compute_patrimoine_maturity ∈ [0, 1] et reflète les champs renseignés
  - RULES_VERSIONS exhaustif (5 règles)
  - RULE_EVALUATORS exhaustif (5 règles)
  - count_unknown_or_missing helper
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from regulatory.applicability_service import (
    compute_applicability,
    compute_patrimoine_maturity,
    count_unknown_or_missing,
)
from regulatory.applicability_types import ApplicabilityStatus, RuleApplicability, RuleCode
from regulatory.rules_catalog import RULE_EVALUATORS, RULES_VERSIONS


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_site(id: int, **kwargs):
    """Site mock avec relation .batiments en liste."""
    defaults = dict(
        nom=f"Site#{id}",
        tertiaire_area_m2=1500,
        usage_principal="BUREAUX",
        parking_area_m2=None,
        roof_area_m2=None,
        organisation_id=1,
        batiments=[],
    )
    defaults.update(kwargs)
    return SimpleNamespace(id=id, **defaults)


def _make_batiment(id: int, cvc_power_kw=None):
    return SimpleNamespace(id=id, cvc_power_kw=cvc_power_kw)


def _make_org(id: int = 1, **kwargs):
    defaults = dict(
        nom="Organisation test",
        effectif_total=380,
        chiffre_affaires_eur=80_000_000.0,
        pays="FR",
    )
    defaults.update(kwargs)
    return SimpleNamespace(id=id, **defaults)


@pytest.fixture
def fake_db(monkeypatch):
    """Patch les loaders du service pour ne pas toucher la DB."""
    sites = [
        _make_site(
            1,
            nom="Toulouse",
            tertiaire_area_m2=2000,
            parking_area_m2=2000,
            batiments=[_make_batiment(10, cvc_power_kw=120)],
        ),
        _make_site(
            2, nom="Lyon", tertiaire_area_m2=850, parking_area_m2=1000, batiments=[_make_batiment(20, cvc_power_kw=30)]
        ),
    ]
    org = _make_org(id=1, nom="HELIOS SAS", effectif_total=380)
    audit_sme = SimpleNamespace(conso_annuelle_moy_gwh=4.2)

    monkeypatch.setattr(
        "regulatory.applicability_service._load_sites",
        lambda db, org_id, site_ids: sites if site_ids is None else [s for s in sites if s.id in site_ids],
    )
    monkeypatch.setattr(
        "regulatory.applicability_service._load_organisation",
        lambda db, org_id: org,
    )
    monkeypatch.setattr(
        "regulatory.applicability_service._load_audit_sme",
        lambda db, org_id: audit_sme,
    )
    monkeypatch.setattr(
        "regulatory.applicability_service._load_batiments_for_site",
        lambda db, site: list(site.batiments),
    )
    return MagicMock(spec=["query"])


# ── compute_applicability ──────────────────────────────────────────────────


def test_compute_applicability_returns_all_rules(fake_db):
    result = compute_applicability(fake_db, org_id=1)
    assert set(result.keys()) == set(RuleCode)


def test_compute_applicability_site_scoped_one_entry_per_site(fake_db):
    """DT, BACS, APER ont 1 entrée par site (2 sites dans la fixture)."""
    result = compute_applicability(fake_db, org_id=1)
    assert len(result[RuleCode.DT]) == 2
    assert len(result[RuleCode.BACS]) == 2
    assert len(result[RuleCode.APER]) == 2


def test_compute_applicability_org_scoped_single_entry(fake_db):
    """SMÉ et BEGES ont exactement 1 entrée (scope organisation)."""
    result = compute_applicability(fake_db, org_id=1)
    assert len(result[RuleCode.SME]) == 1
    assert len(result[RuleCode.BEGES]) == 1


def test_compute_applicability_entries_are_typed(fake_db):
    """Toutes les entrées sont des RuleApplicability."""
    result = compute_applicability(fake_db, org_id=1)
    for rule_entries in result.values():
        for entry in rule_entries:
            assert isinstance(entry, RuleApplicability)


def test_compute_applicability_filter_by_site_ids(fake_db):
    """site_ids filtre le périmètre."""
    result = compute_applicability(fake_db, org_id=1, site_ids=[1])
    assert len(result[RuleCode.DT]) == 1
    assert result[RuleCode.DT][0].scope_id == 1


def test_compute_applicability_dt_site1_applicable_site2_not(fake_db):
    """Site 1 (2000 m² BUREAUX) APPLICABLE ; site 2 (850 m²) NOT_APPLICABLE."""
    result = compute_applicability(fake_db, org_id=1)
    by_id = {a.scope_id: a for a in result[RuleCode.DT]}
    assert by_id[1].status == ApplicabilityStatus.APPLICABLE
    assert by_id[2].status == ApplicabilityStatus.NOT_APPLICABLE


def test_compute_applicability_sme_applicable_via_effectif(fake_db):
    """Effectif 380 → SMÉ APPLICABLE.EFFECTIF."""
    result = compute_applicability(fake_db, org_id=1)
    sme = result[RuleCode.SME][0]
    assert sme.status == ApplicabilityStatus.APPLICABLE
    assert sme.reason_code == "SME.APPLICABLE.EFFECTIF"


# ── compute_patrimoine_maturity ────────────────────────────────────────────


def test_compute_patrimoine_maturity_in_range(fake_db):
    """Maturité ∈ [0, 1]."""
    m = compute_patrimoine_maturity(fake_db, org_id=1)
    assert 0.0 <= m <= 1.0


def test_compute_patrimoine_maturity_partial_data(fake_db):
    """Sites avec parking_area_m2 = None → maturité < 1.0."""
    m = compute_patrimoine_maturity(fake_db, org_id=1)
    # 2 champs org + 4 champs site × 2 sites + 1 champ batiment × 2 = 2+8+2 = 12 checks
    # Renseignés : effectif + ca + tertiaire×2 + usage×2 + parking×2 + cvc×2 = 10
    # roof_area_m2 manquant sur 2 sites
    assert m < 1.0
    assert m > 0.5


def test_compute_patrimoine_maturity_zero_when_empty(monkeypatch):
    """0 site et 0 org → 0.0 (pas de NaN)."""
    monkeypatch.setattr(
        "regulatory.applicability_service._load_sites",
        lambda db, org_id, site_ids: [],
    )
    monkeypatch.setattr(
        "regulatory.applicability_service._load_organisation",
        lambda db, org_id: None,
    )
    db = MagicMock()
    assert compute_patrimoine_maturity(db, org_id=999) == 0.0


# ── count_unknown_or_missing ──────────────────────────────────────────────


def test_count_unknown_or_missing(fake_db):
    """Helper retourne (total, bad)."""
    result = compute_applicability(fake_db, org_id=1)
    total, bad = count_unknown_or_missing(result)
    assert total == 8  # 3×2 sites + 2 org
    assert bad >= 0


# ── Catalogue ─────────────────────────────────────────────────────────────


def test_rule_evaluators_complete():
    """RULE_EVALUATORS contient les 5 règles."""
    assert set(RULE_EVALUATORS.keys()) == set(RuleCode)


def test_rules_versions_complete():
    """RULES_VERSIONS contient les 5 versions datées."""
    assert set(RULES_VERSIONS.keys()) == set(RuleCode)
    for v in RULES_VERSIONS.values():
        assert isinstance(v, str) and len(v) > 0


def test_dt_version_pattern():
    """Vérifie le format de version DT (canon ADR-024)."""
    assert "DT-2019-771" in RULES_VERSIONS[RuleCode.DT]
