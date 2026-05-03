"""
PROMEOS — Sprint C-1 Phase 5 : Tests compliance_score V2 adaptatif.

Vérifie la logique adaptive 0 → 6 obligations + cas NON_APPLICABLE + V1 rollback.

Source : matrice v1 §6.2 + doctrine PROMEOS §6.4.1 V2.

⚠️ Tests unitaires utilisant des mocks Site (pas DB) pour isoler la logique
adaptive du fallback RegAssessment + AuditEnergetique.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _mock_site(
    *,
    tertiaire_area_m2=0,
    parking_area_m2=0,
    roof_area_m2=0,
    aper_assujetti=False,
    parking_solar_pct_engaged=None,
    aper_exemption_motif=None,
    batiments_cvc_kw=None,  # liste des cvc_power_kw des bâtiments
    audit_obligation=None,  # "AUDIT_4ANS" / "SME_ISO50001" / "AUCUNE" / None
    sme_certifie_iso50001=False,
    score_audit_sme=None,
    audit_realise=False,
):
    """Construit un mock Site avec relations pour tester V2 adaptive."""
    site = MagicMock()
    site.id = 1
    site.tertiaire_area_m2 = tertiaire_area_m2
    site.parking_area_m2 = parking_area_m2
    site.roof_area_m2 = roof_area_m2
    site.aper_assujetti = aper_assujetti
    site.parking_solar_pct_engaged = parking_solar_pct_engaged
    site.aper_exemption_motif = aper_exemption_motif

    # Bâtiments
    if batiments_cvc_kw is not None:
        site.batiments = [MagicMock(cvc_power_kw=kw) for kw in batiments_cvc_kw]
    else:
        site.batiments = []

    # Cascade audit_energetique : portefeuille → entite_juridique → org
    if audit_obligation is not None:
        site.portefeuille = MagicMock()
        site.portefeuille.entite_juridique = MagicMock()
        site.portefeuille.entite_juridique.organisation_id = 42
    else:
        site.portefeuille = MagicMock()
        site.portefeuille.entite_juridique = MagicMock()
        site.portefeuille.entite_juridique.organisation_id = 42

    return site


def _mock_audit(obligation, sme_certifie=False, score_audit=None, audit_realise=False):
    audit = MagicMock()
    audit.obligation = obligation
    audit.sme_certifie_iso50001 = sme_certifie
    audit.score_audit_sme = score_audit
    audit.audit_realise = audit_realise
    return audit


# ─── Helpers calcul à la volée (Option A) ───────────────────────────────────


def test_dt_assujetti_below_1000m2():
    """Site < 1000 m² tertiaire → DT non assujetti."""
    from services.compliance_score_service import _is_dt_assujetti

    site = _mock_site(tertiaire_area_m2=999)
    assert _is_dt_assujetti(site) is False


def test_dt_assujetti_exact_1000m2():
    """Site exactement 1000 m² → DT assujetti (seuil inclusif)."""
    from services.compliance_score_service import _is_dt_assujetti

    site = _mock_site(tertiaire_area_m2=1000)
    assert _is_dt_assujetti(site) is True


def test_bacs_assujetti_below_70kw():
    """Σ cvc_power_kw < 70 → BACS non assujetti."""
    from services.compliance_score_service import _is_bacs_assujetti

    site = _mock_site(batiments_cvc_kw=[30, 39])  # = 69
    assert _is_bacs_assujetti(site) is False


def test_bacs_assujetti_exact_70kw():
    """Σ cvc_power_kw = 70 → BACS assujetti."""
    from services.compliance_score_service import _is_bacs_assujetti

    site = _mock_site(batiments_cvc_kw=[40, 30])
    assert _is_bacs_assujetti(site) is True


def test_solar_toiture_below_500m2():
    """Roof < 500 m² → pas obligation solaire."""
    from services.compliance_score_service import _solar_toiture_obligation_active

    site = _mock_site(roof_area_m2=499)
    assert _solar_toiture_obligation_active(site) is False


def test_solar_toiture_500m2_active():
    """Roof ≥ 500 m² → obligation solaire active."""
    from services.compliance_score_service import _solar_toiture_obligation_active

    site = _mock_site(roof_area_m2=500)
    assert _solar_toiture_obligation_active(site) is True


# ─── V2 _compute_v2_adaptive : cas 0 obligation ─────────────────────────────


def test_zero_obligation_returns_non_applicable():
    """TPE 800 m² + parking 1000 m² + 0 audit → NON_APPLICABLE."""
    from services.compliance_score_service import _compute_v2_adaptive

    db_mock = MagicMock()
    site = _mock_site(
        tertiaire_area_m2=800,  # < 1000 → pas DT
        batiments_cvc_kw=[30],  # < 70 → pas BACS
        aper_assujetti=False,  # pas APER
        roof_area_m2=400,  # < 500 → pas SOLAR
    )
    db_mock.query.return_value.filter.return_value.first.return_value = site

    with patch("services.compliance_score_service._get_audit_energetique", return_value=None):
        result = _compute_v2_adaptive(db_mock, site.id)

    assert result.score is None
    assert result.confidence == "non_applicable"
    assert result.frameworks_evaluated == 0
    assert result.frameworks_total == 0
    assert "aucune obligation" in result.formula.lower()


# ─── V2 : cas N obligations ──────────────────────────────────────────────────


def _patch_scorers(score_value: float = 80.0):
    """Patch context : tous les scorers retournent score_value pour isolation logique."""
    return [
        patch("services.compliance_score_service._v2_score_tertiaire_operat", return_value=score_value),
        patch("services.compliance_score_service._v2_score_bacs", return_value=score_value),
        patch("services.compliance_score_service._v2_score_aper", return_value=score_value),
        patch("services.compliance_score_service._v2_score_audit_sme", return_value=score_value),
        patch("services.compliance_score_service._v2_score_iso_50001", return_value=score_value),
        patch("services.compliance_score_service._v2_score_solar_toiture", return_value=score_value),
    ]


def _run_v2_with_site(site, db_mock=None, audit=None):
    """Helper : exécute _compute_v2_adaptive avec scorers mockés à 80.0."""
    from services.compliance_score_service import _compute_v2_adaptive

    if db_mock is None:
        db_mock = MagicMock()
    db_mock.query.return_value.filter.return_value.first.return_value = site

    patches = _patch_scorers(80.0) + [
        patch("services.compliance_score_service._get_audit_energetique", return_value=audit),
    ]
    for p in patches:
        p.start()
    try:
        return _compute_v2_adaptive(db_mock, site.id)
    finally:
        for p in patches:
            p.stop()


def test_one_obligation_dt_alone():
    """Site DT seul → DT 100% pondération."""
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[30], roof_area_m2=400)
    result = _run_v2_with_site(site, audit=None)
    assert result.frameworks_evaluated == 1
    assert result.score == 80.0  # 100% × 80
    assert result.breakdown[0].framework == "tertiaire_operat"
    assert result.breakdown[0].weight == 1.0


def test_two_obligations_dt_bacs_recalcul():
    """DT + BACS → poids relatifs 60/40 (45/(45+30) et 30/75), pas figé 45/30."""
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[40, 50], roof_area_m2=400)
    result = _run_v2_with_site(site, audit=None)
    assert result.frameworks_evaluated == 2
    # poids relatifs : DT 45/75 = 0.6 ; BACS 30/75 = 0.4
    weights = {f.framework: f.weight for f in result.breakdown}
    assert weights["tertiaire_operat"] == 0.6
    assert weights["bacs"] == round(30 / 75, 4)


def test_three_obligations_dt_bacs_aper_standard():
    """DT/BACS/APER → 45/30/25 (poids officiels somme = 100%)."""
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[100], aper_assujetti=True, roof_area_m2=400)
    result = _run_v2_with_site(site, audit=None)
    assert result.frameworks_evaluated == 3
    weights = {f.framework: f.weight for f in result.breakdown}
    assert weights["tertiaire_operat"] == 0.45
    assert weights["bacs"] == 0.30
    assert weights["aper"] == 0.25


def test_four_obligations_with_audit_sme():
    """DT/BACS/APER + AUDIT_SME → poids_total=116 → 39/26/22/14 (approx)."""
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[100], aper_assujetti=True, roof_area_m2=400)
    audit = _mock_audit("AUDIT_4ANS", sme_certifie=False, score_audit=0.7)
    result = _run_v2_with_site(site, audit=audit)
    assert result.frameworks_evaluated == 4
    weights = {f.framework: f.weight for f in result.breakdown}
    # 45+30+25+16 = 116
    assert weights["tertiaire_operat"] == round(45 / 116, 4)
    assert weights["audit_sme"] == round(16 / 116, 4)


def test_five_obligations_with_iso_50001():
    """DT/BACS/APER + ISO_50001 + SOLAR (pas AUDIT_SME car exclusion)."""
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[100], aper_assujetti=True, roof_area_m2=600)
    audit = _mock_audit("SME_ISO50001", sme_certifie=True)
    result = _run_v2_with_site(site, audit=audit)
    assert result.frameworks_evaluated == 5
    codes = {f.framework for f in result.breakdown}
    assert "iso_50001" in codes
    assert "audit_sme" not in codes  # exclusion mutuelle
    assert "solar_toiture" in codes


def test_six_obligations_full_perimeter_blocked_by_exclusion():
    """5 dimensions max possible : exclusion mutuelle empêche 6 simultanées.

    DT+BACS+APER+SOLAR + (AUDIT_SME OU ISO_50001) → max 5.
    """
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[100], aper_assujetti=True, roof_area_m2=600)
    # Avec AUDIT_4ANS sans ISO certif → audit_sme ajouté
    audit_audit = _mock_audit("AUDIT_4ANS", sme_certifie=False)
    result = _run_v2_with_site(site, audit=audit_audit)
    assert result.frameworks_evaluated == 5
    codes = {f.framework for f in result.breakdown}
    assert codes == {"tertiaire_operat", "bacs", "aper", "audit_sme", "solar_toiture"}


def test_audit_sme_obligation_aucune_skipped():
    """AuditEnergetique avec obligation='AUCUNE' → pas ajouté aux dimensions."""
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[100], roof_area_m2=400)
    audit = _mock_audit("AUCUNE")
    result = _run_v2_with_site(site, audit=audit)
    codes = {f.framework for f in result.breakdown}
    assert "audit_sme" not in codes
    assert "iso_50001" not in codes


def test_audit_sme_excluded_if_iso_certified():
    """AUDIT_4ANS mais sme_certifie_iso50001=True → audit_sme NON ajouté."""
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[100], roof_area_m2=400)
    audit = _mock_audit("AUDIT_4ANS", sme_certifie=True)  # certifié → exclusion
    result = _run_v2_with_site(site, audit=audit)
    codes = {f.framework for f in result.breakdown}
    assert "audit_sme" not in codes


# ─── Confidence levels ──────────────────────────────────────────────────────


def test_confidence_low_with_2_dims():
    """2 dimensions actives → confidence 'low'."""
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[100])
    result = _run_v2_with_site(site, audit=None)
    assert result.confidence == "low"


def test_confidence_medium_with_3_dims():
    """3 dimensions actives → confidence 'medium'."""
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[100], aper_assujetti=True)
    result = _run_v2_with_site(site, audit=None)
    assert result.confidence == "medium"


def test_confidence_high_with_5_dims():
    """5 dimensions actives → confidence 'high'."""
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[100], aper_assujetti=True, roof_area_m2=600)
    audit = _mock_audit("AUDIT_4ANS", sme_certifie=False)
    result = _run_v2_with_site(site, audit=audit)
    assert result.frameworks_evaluated == 5
    assert result.confidence == "high"


# ─── V1 rollback via env var ────────────────────────────────────────────────


def test_v1_rollback_via_env_var(monkeypatch):
    """COMPLIANCE_SCORE_VERSION=V1 → comportement V1 figé + DeprecationWarning."""
    import warnings

    from database import SessionLocal
    from models import Site, not_deleted
    from services.compliance_score_service import compute_site_compliance_score

    monkeypatch.setenv("COMPLIANCE_SCORE_VERSION", "V1")

    db = SessionLocal()
    try:
        site = db.query(Site).filter(not_deleted(Site)).first()
        if site is None:
            pytest.skip("Aucun site dans la DB")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = compute_site_compliance_score(db, site.id)
            depr = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(depr) >= 1, "DeprecationWarning V1 attendu"
        # V1 force frameworks_total=3 fixe (5e champ legacy)
        assert "Moyenne pondérée" in result.formula  # signature V1
    finally:
        db.close()


def test_v2_default_no_deprecation_warning(monkeypatch):
    """Pas d'env var → V2 par défaut, pas de DeprecationWarning."""
    import warnings

    from database import SessionLocal
    from models import Site, not_deleted
    from services.compliance_score_service import compute_site_compliance_score

    monkeypatch.delenv("COMPLIANCE_SCORE_VERSION", raising=False)

    db = SessionLocal()
    try:
        site = db.query(Site).filter(not_deleted(Site)).first()
        if site is None:
            pytest.skip("Aucun site dans la DB")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = compute_site_compliance_score(db, site.id)
            depr = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(depr) == 0, "Aucun DeprecationWarning attendu en V2"
        # V2 signature contient "V2 adaptatif"
        if result.frameworks_evaluated > 0:
            assert "V2 adaptatif" in result.formula
    finally:
        db.close()


# ─── Source marker V2 dans breakdown ────────────────────────────────────────


def test_breakdown_source_v2_adaptive_marker():
    """Chaque FrameworkScore en V2 doit avoir source='v2_adaptive'."""
    site = _mock_site(tertiaire_area_m2=2000, batiments_cvc_kw=[100])
    result = _run_v2_with_site(site, audit=None)
    for fw in result.breakdown:
        assert fw.source == "v2_adaptive"


# ─── Pondérations officielles préservées ────────────────────────────────────


def test_official_weights_v2_constants():
    """_OFFICIAL_WEIGHTS_V2 contient les 6 dimensions canoniques."""
    from services.compliance_score_service import _OFFICIAL_WEIGHTS_V2

    expected = {
        "tertiaire_operat": 45,
        "bacs": 30,
        "aper": 25,
        "audit_sme": 16,
        "iso_50001": 20,
        "solar_toiture": 15,
    }
    assert _OFFICIAL_WEIGHTS_V2 == expected
