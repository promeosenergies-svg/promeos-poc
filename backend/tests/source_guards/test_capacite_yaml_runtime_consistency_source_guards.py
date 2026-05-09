"""
PROMEOS — Source guards cohérence YAML ↔ runtime Capacité RTE (Sprint C-4 Phase 4.2).

Anti-régression : le runtime `services/billing_engine/catalog.py` (CAPACITE_ELEC* entries)
et `services/price_decomposition_service.py::_compute_capacity()` doivent rester
cohérents avec le SoT YAML `sources_reglementaires.yaml`.

Pattern reproduit identique aux 10 SG cohérence YAML↔constants.py Sprint C-3 Phase 3.3.
Décision archi Phase 4.2 : Option B (YAML SoT + SG cohérence runtime, pas refactor service).

3 source-guards cardinaux :

- SG_CAPACITE_RUNTIME_01 : tarif 2026 YAML = rate runtime catalog `CAPACITE_ELEC` (0.00043 EUR/kWh
  = 3.15 EUR/MW × 1.2 / 8760 / 1000)
- SG_CAPACITE_RUNTIME_02 : tarif 2025 YAML = rate runtime catalog `CAPACITE_ELEC_2025` (0.0)
- SG_CAPACITE_RUNTIME_03 : deadline 1/11/2026 YAML = `valid_from` runtime catalog `CAPACITE_ELEC_NOV2026`
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.regulatory_sources_loader import get_term_value, reload_regulatory_sources
from services.billing_engine.catalog import TURPE7_RATES as CATALOG_RATES


@pytest.fixture(autouse=True)
def reload_yaml():
    reload_regulatory_sources()
    yield


_TOLERANCE_NUMERIC = 0.00002  # 2e-5 tolerance (catalog rate stocké ~0.00043 vs formule 0.000432)


def _expected_value_from_yaml(price_eur_per_mw: float, coeff: float) -> float:
    """Formule canonique runtime `_compute_capacity()` : (price × coeff) / 8760 / 1000.

    Résultat = EUR/kWh (cohérent avec `CATALOG_RATES['CAPACITE_ELEC'].unit = "EUR/kWh"`).

    Phase L23.2 audit fix P1 — conversion MW→kW (facteur /1000) cardinale :
    avant L23.2 : formule retournait EUR/MWh sans /1000 → delta 0.4315 vs catalog
    0.00043 → faux échec test source-guard (réelle cohérence : 3150 EUR/MW × 1.2 /
    8760 h / 1000 conversion MW→kW = 0.000431 EUR/kWh ≈ 0.00043 catalog ✓).

    Note doctrinale : `CAPACITE_RTE_TARIF_2026_EUR_PER_MW` est EUR/MW/an
    (puissance souscrite annuelle), divisé par 8760 h/an = EUR/MWh, divisé
    par 1000 (MW → kW) = EUR/kWh. La formule complète est dans
    `services/price_decomposition_service.py::_compute_capacity()`.
    """
    return (price_eur_per_mw * coeff) / 8760 / 1000


def test_sg_capacite_runtime_01_tarif_2026_numeric_consistency_with_catalog():
    """SG_CAPACITE_RUNTIME_01 : valeur numérique YAML 2026 cohérente avec catalog runtime.

    Note doctrinale : le catalog stocke `rate=0.00043` avec unit `EUR/kWh` qui est
    probablement incorrect (devrait être `EUR/MWh` car formule = price/8760 produit
    EUR/MWh). Dette unit-mismatch tracée Sprint C-7 polish. Ce SG valide la
    valeur numérique seule (anti-drift réglementaire).
    """
    yaml_price = get_term_value("CAPACITE_RTE_TARIF_2026_EUR_PER_MW")  # 3.15
    yaml_coeff = get_term_value("CAPACITE_RTE_COEFF_2026")  # 1.2
    expected_rate = _expected_value_from_yaml(yaml_price, yaml_coeff)  # ≈ 0.000432

    catalog_entry = CATALOG_RATES.get("CAPACITE_ELEC")
    assert catalog_entry is not None, "CATALOG_RATES['CAPACITE_ELEC'] absent du catalog runtime"
    catalog_rate = catalog_entry["rate"]

    delta = abs(catalog_rate - expected_rate)
    assert delta < _TOLERANCE_NUMERIC, (
        f"Incohérence YAML↔runtime CAPACITE 2026 (valeur numérique) :\n"
        f"  YAML : ({yaml_price} × {yaml_coeff}) / 8760 = {expected_rate:.6f}\n"
        f"  Runtime catalog CAPACITE_ELEC.rate = {catalog_rate}\n"
        f"  Δ = {delta:.6f} (tolérance {_TOLERANCE_NUMERIC})\n"
        f"  → mettre à jour billing_engine/catalog.py OU sources_reglementaires.yaml"
    )


def test_sg_capacite_runtime_02_tarif_2025_zero_in_both():
    """SG_CAPACITE_RUNTIME_02 : tarif 2025 = 0 dans YAML ET catalog."""
    yaml_2025 = get_term_value("CAPACITE_RTE_TARIF_2025_EUR_PER_MW")
    catalog_2025 = CATALOG_RATES.get("CAPACITE_ELEC_2025")
    assert yaml_2025 == 0.0, f"YAML 2025 = {yaml_2025} (attendu 0.0)"
    assert catalog_2025 is not None
    assert catalog_2025["rate"] == 0.0, f"Catalog 2025 rate = {catalog_2025['rate']} (attendu 0.0)"


def test_sg_capacite_runtime_03_deadline_matches_catalog_valid_from():
    """SG_CAPACITE_RUNTIME_03 : deadline YAML = valid_from catalog NOV2026."""
    yaml_deadline = get_term_value("CAPACITE_RTE_OBLIGATION_DEADLINE")
    catalog_nov2026 = CATALOG_RATES.get("CAPACITE_ELEC_NOV2026")
    assert catalog_nov2026 is not None, "CATALOG_RATES['CAPACITE_ELEC_NOV2026'] absent"
    assert catalog_nov2026["valid_from"] == yaml_deadline, (
        f"Incohérence deadline YAML ({yaml_deadline}) ↔ catalog valid_from ({catalog_nov2026['valid_from']})"
    )
