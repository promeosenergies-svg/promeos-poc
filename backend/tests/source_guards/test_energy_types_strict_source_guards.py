"""
PROMEOS — Source guards types stricts énergie (Sprint C-4 Phase 4.3, ADR-011).

Defense in depth Phase 4.3 : SG cohérence module `promeos_types/energy.py` +
typage cardinal services consumers.

3 source-guards :

- SG_ENERGY_TYPES_01 : module promeos_types/energy.py exporte les 5 NewType + 4+ helpers
- SG_ENERGY_TYPES_02 : portfolio_intensity_service importe KwhEFPCI (consumer cardinal MVP)
- SG_ENERGY_TYPES_03 : helpers conversion utilisent les coefficients réglementaires (1 SoT)

Complémentaire avec SG MVP Sprint C-3 Phase 3.4
(`test_annual_kwh_total_kwhef_pci_source_guards.py`) qui couvre l'allowlist setattr.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ENERGY_TYPES_PATH = _BACKEND_ROOT / "promeos_types" / "energy.py"
_PORTFOLIO_INTENSITY_PATH = _BACKEND_ROOT / "services" / "portfolio_intensity_service.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# Sprint C-4 Phase 4.3d audit follow-up : alignement cardinal MVP.
# - 3 NewType cardinaux (vs 5 pré-cleanup) — KwhEP/MWhEFPCI supprimés YAGNI
# - 2 helpers conversion (vs 4) — kwh_ef_to_kwh_ep_elec supprimé P0 doctrinal +
#   mwh_to_kwh_ef_pci/kwh_ef_to_mwh/kwh_ef_to_gwh supprimés YAGNI
# - 2 coefficients (vs 4) — COEFF_KWH_EF_TO_KWH_EP_ELEC supprimé fantôme +
#   FACTOR_MWH_TO_KWH supprimé YAGNI
_REQUIRED_NEWTYPES = ["KwhEFPCI", "GWhEFPCI", "KwhPCS"]
_REQUIRED_HELPERS = [
    "gwh_to_kwh_ef_pci",
    "kwh_pcs_to_kwh_ef_pci_gaz",
]
_REQUIRED_COEFFS = [
    "COEFF_KWH_PCS_TO_KWH_PCI_GAZ",
    "FACTOR_GWH_TO_KWH",
]


def test_sg_energy_types_01_module_exports_all_newtypes_and_helpers():
    """SG_ENERGY_TYPES_01 : promeos_types/energy.py exporte 5 NewType + 4 helpers + 4 coefficients."""
    content = _read(_ENERGY_TYPES_PATH)

    missing_newtypes = [nt for nt in _REQUIRED_NEWTYPES if f"{nt} = NewType(" not in content]
    assert not missing_newtypes, f"NewType manquants dans promeos_types/energy.py : {missing_newtypes}"

    missing_helpers = [h for h in _REQUIRED_HELPERS if f"def {h}(" not in content]
    assert not missing_helpers, f"Helpers manquants dans promeos_types/energy.py : {missing_helpers}"

    missing_coeffs = [c for c in _REQUIRED_COEFFS if f"{c} = " not in content]
    assert not missing_coeffs, f"Coefficients réglementaires manquants : {missing_coeffs}"


def test_sg_energy_types_02_portfolio_intensity_imports_kwh_ef_pci():
    """SG_ENERGY_TYPES_02 : portfolio_intensity_service importe KwhEFPCI (consumer cardinal MVP).

    Anti-régression : si le typage cardinal est retiré silencieusement (refacto sans
    coordination), ce SG bloque le commit. Pattern reproductible pour autres consumers
    Sprint C-5+ (compliance_rules, cee_service, etc.) à mesure du typage progressif.
    """
    content = _read(_PORTFOLIO_INTENSITY_PATH)
    assert "from promeos_types.energy import KwhEFPCI" in content, (
        "portfolio_intensity_service.py doit importer KwhEFPCI depuis promeos_types.energy "
        "(différenciateur Bill Intelligence runtime cross-module — ADR-011 Phase 4.3)."
    )
    # Doit aussi annoter au moins une variable interne avec KwhEFPCI
    assert "KwhEFPCI(" in content, (
        "portfolio_intensity_service.py doit utiliser KwhEFPCI() pour typer la valeur agrégée "
        "(sum_annual_kwh) — sinon import inutile."
    )


def test_sg_energy_types_03_helpers_use_canonical_coefficients():
    """SG_ENERGY_TYPES_03 : les helpers conversion référencent les constantes coefficients
    (pas de duplication magic number).
    """
    content = _read(_ENERGY_TYPES_PATH)

    def _extract_function_block(src: str, fn_name: str) -> str:
        """Extrait le corps d'une fonction depuis `def <fn_name>(` jusqu'à la prochaine
        définition top-level (`def `/`class ` en début de ligne) ou EOF."""
        start = src.find(f"def {fn_name}(")
        if start == -1:
            return ""
        rest = src[start:]
        next_def = rest.find("\ndef ", 1)
        next_class = rest.find("\nclass ", 1)
        candidates = [pos for pos in (next_def, next_class) if pos != -1]
        end = min(candidates) if candidates else len(rest)
        return rest[:end]

    # kwh_pcs_to_kwh_ef_pci_gaz doit utiliser COEFF_KWH_PCS_TO_KWH_PCI_GAZ (1 SoT)
    helper_block = _extract_function_block(content, "kwh_pcs_to_kwh_ef_pci_gaz")
    assert helper_block, "Helper kwh_pcs_to_kwh_ef_pci_gaz absent"
    assert "COEFF_KWH_PCS_TO_KWH_PCI_GAZ" in helper_block, (
        "Helper kwh_pcs_to_kwh_ef_pci_gaz doit référencer COEFF_KWH_PCS_TO_KWH_PCI_GAZ (1 SoT)"
    )

    # gwh_to_kwh_ef_pci doit utiliser FACTOR_GWH_TO_KWH (1 SoT, pas magic 1_000_000 inline)
    helper_block = _extract_function_block(content, "gwh_to_kwh_ef_pci")
    assert helper_block, "Helper gwh_to_kwh_ef_pci absent"
    assert "FACTOR_GWH_TO_KWH" in helper_block, "Helper gwh_to_kwh_ef_pci doit référencer FACTOR_GWH_TO_KWH (1 SoT)"
