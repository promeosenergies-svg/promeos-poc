"""
PROMEOS — Tests types stricts énergie (Sprint C-4 Phase 4.3 + 4.3d, ADR-011).

Vérifie le module `backend/promeos_types/energy.py` :
- Présence des 3 NewType cardinaux MVP (KwhEFPCI, GWhEFPCI, KwhPCS)
- Coefficients réglementaires constants (1 SoT)
- 2 helpers conversion typés (gwh_to_kwh_ef_pci, kwh_pcs_to_kwh_ef_pci_gaz)
- Edge case guards : finite + non-negative

Phase 4.3d audit follow-up (regulatory-expert P0 critique) :
- Suppression `COEFF_KWH_EF_TO_KWH_EP_ELEC = 1.9` (valeur fantôme — pas source officielle FR)
- Suppression `kwh_ef_to_kwh_ep_elec` (aucun consumer + OPERAT raisonne en EF)
- Suppression `KwhEP, MWhEFPCI, kwh_ef_to_mwh, kwh_ef_to_gwh, mwh_to_kwh_ef_pci` (YAGNI)
- Ajout 6 tests edge cases (NaN, Inf, négatif) sur 2 helpers conservés

Clôture dette `D-Sprint-C3-7d-EnergieFinale-Type-Strict-001` (P1 Sprint C-3 7d).
"""

from __future__ import annotations

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from promeos_types.energy import (
    COEFF_KWH_PCS_TO_KWH_PCI_GAZ,
    FACTOR_GWH_TO_KWH,
    GWhEFPCI,
    KwhEFPCI,
    KwhPCS,
    gwh_to_kwh_ef_pci,
    kwh_pcs_to_kwh_ef_pci_gaz,
)


# ─── 1. NewType présence + alias mypy ────────────────────────────────────────


def test_kwh_ef_pci_is_callable_alias_for_float():
    """KwhEFPCI accepte un float et retourne un float (alias mypy NewType)."""
    val = KwhEFPCI(100_000.0)
    assert isinstance(val, float)
    assert val == 100_000.0


def test_3_cardinal_newtypes_have_distinct_names():
    """Les 3 NewType cardinaux MVP ont des noms distincts (différenciation type-safe)."""
    assert KwhEFPCI.__name__ == "KwhEFPCI"
    assert GWhEFPCI.__name__ == "GWhEFPCI"
    assert KwhPCS.__name__ == "KwhPCS"


def test_gwh_kwh_pcs_newtypes_accept_float():
    """GWhEFPCI et KwhPCS sont des NewType-callables pour catch confusion ingestion."""
    assert GWhEFPCI(2.75) == 2.75
    assert KwhPCS(1000.0) == 1000.0


# ─── 2. Coefficients réglementaires (1 SoT) ──────────────────────────────────


def test_coeff_pcs_to_pci_gaz_is_0_901_grdf():
    """Coefficient PCS→PCI gaz = 0.901 (GRDF Catalogue prestations 2025)."""
    assert COEFF_KWH_PCS_TO_KWH_PCI_GAZ == 0.901


def test_factor_gwh_to_kwh():
    """Facteur multiplicatif GWh → kWh = 1_000_000."""
    assert FACTOR_GWH_TO_KWH == 1_000_000


# ─── 3. Helpers conversion typés ─────────────────────────────────────────────


def test_gwh_to_kwh_ef_pci_audit_sme_threshold():
    """`gwh_to_kwh_ef_pci(2.75)` = 2 750 000 kWh (seuil audit 4 ans)."""
    assert gwh_to_kwh_ef_pci(2.75) == 2_750_000.0
    assert gwh_to_kwh_ef_pci(GWhEFPCI(23.6)) == 23_600_000.0


def test_kwh_pcs_to_kwh_ef_pci_gaz_grdf_conversion():
    """`kwh_pcs_to_kwh_ef_pci_gaz(1000.0)` = 901 kWh PCI (×0.901 GRDF)."""
    result = kwh_pcs_to_kwh_ef_pci_gaz(1000.0)
    assert result == pytest.approx(901.0, abs=0.001)
    # Précision : 1 MWh PCS = 901 kWh PCI
    assert kwh_pcs_to_kwh_ef_pci_gaz(KwhPCS(1_000_000.0)) == pytest.approx(901_000.0, abs=0.01)


# ─── 4. Edge case guards (Phase 4.3d) ─────────────────────────────────────────


def test_gwh_to_kwh_ef_pci_rejects_negative():
    """Phase 4.3d : helper rejette valeur négative (énergie ≥ 0 doctrinal)."""
    with pytest.raises(ValueError, match="non-négatif"):
        gwh_to_kwh_ef_pci(-1.0)


def test_gwh_to_kwh_ef_pci_rejects_nan():
    """Phase 4.3d : helper rejette NaN."""
    with pytest.raises(ValueError, match="fini"):
        gwh_to_kwh_ef_pci(float("nan"))


def test_gwh_to_kwh_ef_pci_rejects_inf():
    """Phase 4.3d : helper rejette Inf."""
    with pytest.raises(ValueError, match="fini"):
        gwh_to_kwh_ef_pci(math.inf)


def test_kwh_pcs_to_kwh_ef_pci_gaz_rejects_negative():
    """Phase 4.3d : helper rejette valeur négative (gaz ≥ 0)."""
    with pytest.raises(ValueError, match="non-négatif"):
        kwh_pcs_to_kwh_ef_pci_gaz(-500.0)


def test_kwh_pcs_to_kwh_ef_pci_gaz_rejects_nan():
    """Phase 4.3d : helper rejette NaN."""
    with pytest.raises(ValueError, match="fini"):
        kwh_pcs_to_kwh_ef_pci_gaz(float("nan"))


def test_kwh_pcs_to_kwh_ef_pci_gaz_rejects_inf():
    """Phase 4.3d : helper rejette Inf."""
    with pytest.raises(ValueError, match="fini"):
        kwh_pcs_to_kwh_ef_pci_gaz(-math.inf)


# ─── 5. Edge case zéro (cas valide doctrinalement) ───────────────────────────


def test_gwh_to_kwh_ef_pci_accepts_zero():
    """Zéro est valide (site sans consommation = 0 kWh)."""
    assert gwh_to_kwh_ef_pci(0.0) == 0.0


def test_kwh_pcs_to_kwh_ef_pci_gaz_accepts_zero():
    """Zéro est valide pour gaz aussi."""
    assert kwh_pcs_to_kwh_ef_pci_gaz(0.0) == 0.0
