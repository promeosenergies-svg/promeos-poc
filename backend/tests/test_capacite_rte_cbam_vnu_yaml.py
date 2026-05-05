"""
PROMEOS — Tests YAML Capacité RTE + VNU + CBAM (Sprint C-4 Phase 4.2).

Vérifie la présence + structure des 9 nouveaux termes ajoutés au SoT YAML
`backend/config/sources_reglementaires.yaml` :

- CAPACITE_RTE_OBLIGATION_DEADLINE (2026-11-01)
- CAPACITE_RTE_TARIF_2026_EUR_PER_MW (3.15)
- CAPACITE_RTE_COEFF_2026 (1.2)
- CAPACITE_RTE_TARIF_2025_EUR_PER_MW (0.0)
- VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH (0.0)
- VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH (78.0)
- VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH (110.0)
- CBAM_OBLIGATION_DEADLINE_PHASE_PLEINE (2026-01-01)
- CBAM_REGLEMENT_REFERENCE ("Règlement (UE) 2023/956")

Clôture dette `D-Sprint-C3-Reg-Manquants-Capacite-CBAM-VNU-001` (P0 réglementaire).
"""

from __future__ import annotations

import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.regulatory_sources_loader import (
    get_term,
    get_term_value,
    get_terms_by_domain,
    list_all_term_ids,
    reload_regulatory_sources,
)


@pytest.fixture(autouse=True)
def reload_yaml():
    """Force reload du YAML pour chaque test (cache lru invalide)."""
    reload_regulatory_sources()
    yield


# ─── 1. Capacité RTE ─────────────────────────────────────────────────────────


def test_capacite_rte_obligation_deadline_present_and_iso_format():
    """SG_CAPACITE_01 : deadline 1/11/2026 présent et ISO."""
    deadline = get_term_value("CAPACITE_RTE_OBLIGATION_DEADLINE")
    assert deadline == "2026-11-01", f"Deadline capacité = {deadline} (attendu 2026-11-01)"
    # Doit être parseable comme date
    parsed = date.fromisoformat(deadline)
    assert parsed.year == 2026 and parsed.month == 11 and parsed.day == 1


def test_capacite_rte_tarif_2026_matches_runtime_catalog():
    """SG_CAPACITE_02 : tarif 2026 YAML = 3.15 EUR/MW (mirroir billing_engine/catalog.py)."""
    val = get_term_value("CAPACITE_RTE_TARIF_2026_EUR_PER_MW")
    assert val == 3.15, f"Tarif capacité 2026 YAML={val}, runtime catalog=3.15"


def test_capacite_rte_coeff_2026_value():
    """SG_CAPACITE_03 : coeff 2026 YAML = 1.2 (mirroir _compute_capacity formule)."""
    val = get_term_value("CAPACITE_RTE_COEFF_2026")
    assert val == 1.2


def test_capacite_rte_tarif_2025_zero():
    """SG_CAPACITE_04 : tarif 2025 = 0 EUR/MW (mirroir CAPACITE_ELEC_2025 catalog)."""
    val = get_term_value("CAPACITE_RTE_TARIF_2025_EUR_PER_MW")
    assert val == 0.0


def test_capacite_rte_legal_reference_decret():
    """SG_CAPACITE_05 : référence légale Décret 2025-1441 mentionnée."""
    term = get_term("CAPACITE_RTE_OBLIGATION_DEADLINE")
    legal_ref = term["source"]["legal_reference"]
    assert legal_ref and "2025-1441" in legal_ref, f"legal_reference doit citer Décret 2025-1441, got {legal_ref!r}"


# ─── 2. VNU ──────────────────────────────────────────────────────────────────


def test_vnu_tarif_unitaire_2026_zero():
    """SG_VNU_01 : tarif unitaire 2026 = 0 EUR/MWh (statut dormant)."""
    val = get_term_value("VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH")
    assert val == 0.0


def test_vnu_seuils_activation_consistent():
    """SG_VNU_02 : seuil bas (78) < seuil haut (110), cohérence ordre."""
    seuil_bas = get_term_value("VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH")
    seuil_haut = get_term_value("VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH")
    assert seuil_bas == 78.0
    assert seuil_haut == 110.0
    assert seuil_bas < seuil_haut, "Seuil bas doit être < seuil haut (cohérence ordonnée)"


def test_vnu_legal_reference_decret_2026_55():
    """SG_VNU_03 : Décret 2026-55 cité (mirroir cost_simulator_2026.py docstring)."""
    term = get_term("VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH")
    legal_ref = term["source"]["legal_reference"]
    assert legal_ref and "2026-55" in legal_ref


# ─── 3. CBAM ─────────────────────────────────────────────────────────────────


def test_cbam_obligation_deadline_2026_01_01():
    """SG_CBAM_01 : application pleine CBAM = 1/01/2026."""
    deadline = get_term_value("CBAM_OBLIGATION_DEADLINE_PHASE_PLEINE")
    assert deadline == "2026-01-01"


def test_cbam_reglement_reference_ue_2023_956():
    """SG_CBAM_02 : référence Règlement UE 2023/956."""
    term = get_term("CBAM_REGLEMENT_REFERENCE")
    legal_ref = term["source"]["legal_reference"]
    assert "2023/956" in legal_ref, f"Doit référencer 2023/956, got {legal_ref!r}"
    assert term["domain"] == "co2"


# ─── 4. Cohérence cross-cutting ──────────────────────────────────────────────


def test_get_terms_by_domain_tarifs_includes_capacite_and_vnu():
    """SG_DOMAIN_01 : domain 'tarifs' contient les nouveaux termes CAPACITE_RTE_* + VNU_*."""
    tarifs_terms = set(get_terms_by_domain("tarifs").keys())
    expected_capacite = {
        "CAPACITE_RTE_OBLIGATION_DEADLINE",
        "CAPACITE_RTE_TARIF_2026_EUR_PER_MW",
        "CAPACITE_RTE_COEFF_2026",
        "CAPACITE_RTE_TARIF_2025_EUR_PER_MW",
    }
    expected_vnu = {
        "VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH",
        "VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH",
        "VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH",
    }
    assert expected_capacite.issubset(tarifs_terms), (
        f"CAPACITE_RTE_* manquants du domain 'tarifs': {expected_capacite - tarifs_terms}"
    )
    assert expected_vnu.issubset(tarifs_terms), f"VNU_* manquants: {expected_vnu - tarifs_terms}"


def test_get_terms_by_domain_co2_includes_cbam():
    """SG_DOMAIN_02 : domain 'co2' contient les termes CBAM_*."""
    co2_terms = set(get_terms_by_domain("co2").keys())
    expected_cbam = {"CBAM_OBLIGATION_DEADLINE_PHASE_PLEINE", "CBAM_REGLEMENT_REFERENCE"}
    assert expected_cbam.issubset(co2_terms), f"CBAM_* manquants: {expected_cbam - co2_terms}"


def test_yaml_total_terms_count_after_phase_4_2():
    """SG_GLOBAL_01 : YAML total terms = 77 post-Phase 4.2 (68 pré + 9 ajoutés)."""
    total = len(list_all_term_ids())
    assert total == 77, f"YAML doit avoir 77 termes après Phase 4.2 (68 + 9 ajoutés), got {total}"
