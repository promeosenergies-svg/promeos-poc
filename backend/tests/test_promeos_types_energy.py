"""
PROMEOS — Tests types stricts énergie (Sprint C-4 Phase 4.3, ADR-011).

Vérifie le module `backend/promeos_types/energy.py` :
- Présence des 5 NewType (KwhEFPCI, KwhEP, MWhEFPCI, GWhEFPCI, KwhPCS)
- Coefficients réglementaires constants (1 SoT)
- Helpers conversion typés (sortie bonne unité)
- Formule mathématique correcte

Clôture dette `D-Sprint-C3-7d-EnergieFinale-Type-Strict-001` (P1 Sprint C-3 7d).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from promeos_types.energy import (
    COEFF_KWH_EF_TO_KWH_EP_ELEC,
    COEFF_KWH_PCS_TO_KWH_PCI_GAZ,
    FACTOR_GWH_TO_KWH,
    FACTOR_MWH_TO_KWH,
    GWhEFPCI,
    KwhEFPCI,
    KwhEP,
    KwhPCS,
    MWhEFPCI,
    gwh_to_kwh_ef_pci,
    kwh_ef_to_gwh,
    kwh_ef_to_kwh_ep_elec,
    kwh_ef_to_mwh,
    kwh_pcs_to_kwh_ef_pci_gaz,
    mwh_to_kwh_ef_pci,
)


# ─── 1. NewType présence + alias mypy ────────────────────────────────────────


def test_kwh_ef_pci_is_callable_alias_for_float():
    """KwhEFPCI accepte un float et retourne un float (alias mypy NewType)."""
    val = KwhEFPCI(100_000.0)
    assert isinstance(val, float)
    assert val == 100_000.0


def test_kwh_ep_distinct_from_kwh_ef_pci_alias():
    """KwhEP et KwhEFPCI sont 2 NewType distincts (différenciation cardinale)."""
    ef = KwhEFPCI(100_000.0)
    ep = KwhEP(190_000.0)
    assert isinstance(ef, float) and isinstance(ep, float)
    assert ef != ep
    # NewType est mypy-only, pas runtime — mais __name__ distinct
    assert KwhEFPCI.__name__ == "KwhEFPCI"
    assert KwhEP.__name__ == "KwhEP"


def test_mwh_gwh_kwh_pcs_newtypes_exist():
    """Les 5 NewType sont exportés (cardinaux pour catch confusion ingestion)."""
    assert MWhEFPCI(1.5) == 1.5
    assert GWhEFPCI(2.75) == 2.75
    assert KwhPCS(1000.0) == 1000.0


# ─── 2. Coefficients réglementaires (1 SoT) ──────────────────────────────────


def test_coeff_ef_to_ep_elec_is_1_9_arrete_10_04_2020():
    """Coefficient EF→EP élec = 1.9 (arrêté 10/04/2020 art. 2-g NOR LOGL2005904A)."""
    assert COEFF_KWH_EF_TO_KWH_EP_ELEC == 1.9


def test_coeff_pcs_to_pci_gaz_is_0_901_grdf():
    """Coefficient PCS→PCI gaz = 0.901 (GRDF Catalogue prestations 2025)."""
    assert COEFF_KWH_PCS_TO_KWH_PCI_GAZ == 0.901


def test_factor_mwh_gwh_to_kwh():
    """Facteurs multiplicatifs MWh/GWh → kWh (1000, 1_000_000)."""
    assert FACTOR_MWH_TO_KWH == 1000
    assert FACTOR_GWH_TO_KWH == 1_000_000


# ─── 3. Helpers conversion typés ─────────────────────────────────────────────


def test_gwh_to_kwh_ef_pci_audit_sme_threshold():
    """`gwh_to_kwh_ef_pci(2.75)` = 2 750 000 kWh (seuil audit 4 ans)."""
    assert gwh_to_kwh_ef_pci(2.75) == 2_750_000.0
    # Test signature : doit retourner KwhEFPCI (vérification NewType-aware via name)
    result = gwh_to_kwh_ef_pci(GWhEFPCI(23.6))
    assert result == 23_600_000.0


def test_mwh_to_kwh_ef_pci_factor_1000():
    """`mwh_to_kwh_ef_pci(1.5)` = 1500 kWh."""
    assert mwh_to_kwh_ef_pci(1.5) == 1500.0
    assert mwh_to_kwh_ef_pci(MWhEFPCI(100.0)) == 100_000.0


def test_kwh_pcs_to_kwh_ef_pci_gaz_grdf_conversion():
    """`kwh_pcs_to_kwh_ef_pci_gaz(1000.0)` = 901 kWh PCI (×0.901 GRDF)."""
    result = kwh_pcs_to_kwh_ef_pci_gaz(1000.0)
    assert result == pytest.approx(901.0, abs=0.001)
    # Précision : 1 MWh PCS = 901 kWh PCI
    assert kwh_pcs_to_kwh_ef_pci_gaz(KwhPCS(1_000_000.0)) == pytest.approx(901_000.0, abs=0.01)


def test_kwh_ef_to_kwh_ep_elec_coefficient_1_9():
    """`kwh_ef_to_kwh_ep_elec(100_000)` = 190 000 kWhEP (coeff 1.9 arrêté 10/04/2020)."""
    assert kwh_ef_to_kwh_ep_elec(100_000.0) == 190_000.0
    assert kwh_ef_to_kwh_ep_elec(KwhEFPCI(50_000.0)) == 95_000.0


def test_kwh_ef_to_mwh_inversion():
    """`kwh_ef_to_mwh(1500.0)` = 1.5 MWh (inversion mwh_to_kwh)."""
    assert kwh_ef_to_mwh(1500.0) == 1.5
    assert kwh_ef_to_mwh(KwhEFPCI(100_000.0)) == 100.0


def test_kwh_ef_to_gwh_audit_sme_threshold_iso50001():
    """`kwh_ef_to_gwh(23_600_000)` = 23.6 GWh (seuil ISO 50001)."""
    assert kwh_ef_to_gwh(23_600_000.0) == 23.6
    assert kwh_ef_to_gwh(KwhEFPCI(2_750_000.0)) == 2.75


# ─── 4. Cohérence inversibilité ──────────────────────────────────────────────


def test_round_trip_kwh_to_mwh_to_kwh():
    """Conversion bijective kWh → MWh → kWh (pas de perte précision)."""
    initial = KwhEFPCI(123_456.0)
    mwh_round = kwh_ef_to_mwh(initial)
    kwh_back = mwh_to_kwh_ef_pci(mwh_round)
    assert kwh_back == initial


def test_round_trip_kwh_to_gwh_to_kwh():
    """Conversion bijective kWh → GWh → kWh."""
    initial = KwhEFPCI(2_750_000.0)
    gwh_round = kwh_ef_to_gwh(initial)
    kwh_back = gwh_to_kwh_ef_pci(gwh_round)
    assert kwh_back == initial
