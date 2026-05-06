"""
PROMEOS — Source guards cohérence cost_simulator_2026 ↔ YAML SoT (Sprint C-4 Phase 4.2d).

Anti-régression : `services/purchase/cost_simulator_2026.py` hardcode 2 constantes
qui DUPLIQUENT le SoT YAML `sources_reglementaires.yaml` ajouté Phase 4.2 :

- L64 `CAPACITE_UNITAIRE_EUR_MWH = 0.43` ↔ YAML `CAPACITE_RTE_TARIF_2026_EUR_PER_MW × COEFF_2026 / 8760`
- L68 `VNU_SEUIL_DEFAUT_EUR_MWH = 78.0` ↔ YAML `VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH`

Audit code-reviewer + bill-intelligence Phase 4.2 audit follow-up : 2 violations doctrine
"1 SoT par concept" (PROMEOS Sol §6.4) → ces SG anti-dérive bloquent toute future
divergence silencieuse YAML ↔ Python sans alerte CI.

Pattern reproduit identique aux 10 SG cohérence YAML↔constants.py Sprint C-3 Phase 3.3.

⚠️ Note Phase 4.2d : la cohérence numérique n'implique pas de refactor immédiat —
les constantes Python restent en place pour MVP, le SG s'assure simplement qu'elles
ne dérivent pas du SoT YAML. Dette `D-Phase4-2-Catalog-CAPACITE-Unit-Mismatch-001`
reclassée P1 (rapport CFO) couvre le refactor consumers Sprint C-5+.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config.regulatory_sources_loader import get_term_value, reload_regulatory_sources
from services.purchase.cost_simulator_2026 import (
    CAPACITE_UNITAIRE_EUR_MWH,
    VNU_SEUIL_DEFAUT_EUR_MWH,
)


@pytest.fixture(autouse=True)
def reload_yaml():
    reload_regulatory_sources()
    yield


_TOLERANCE_NUMERIC_VNU = 0.01  # 1 centime EUR/MWh (78.0 vs 78 doit être strict)
_TOLERANCE_NUMERIC_CAPACITE_EUR_MWH = 0.05  # 5 cents EUR/MWh tolerance (catalog approxime à 0.43)


def test_sg_cost_sim_01_vnu_seuil_consistent_with_yaml():
    """SG_COST_SIM_01 : VNU_SEUIL_DEFAUT_EUR_MWH == YAML VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH.

    Anti-dérive : `cost_simulator_2026.py:68` hardcode 78.0. Si futur dev modifie le YAML
    (ex : nouveau seuil CRE) sans mettre à jour la constante Python, ce SG échoue → CI bloque.
    """
    yaml_seuil = get_term_value("VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH")
    delta = abs(VNU_SEUIL_DEFAUT_EUR_MWH - yaml_seuil)
    assert delta < _TOLERANCE_NUMERIC_VNU, (
        f"Dérive YAML↔cost_simulator_2026.VNU_SEUIL_DEFAUT_EUR_MWH :\n"
        f"  YAML VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH = {yaml_seuil}\n"
        f"  cost_simulator_2026.VNU_SEUIL_DEFAUT_EUR_MWH = {VNU_SEUIL_DEFAUT_EUR_MWH}\n"
        f"  Δ = {delta} (tolérance {_TOLERANCE_NUMERIC_VNU})\n"
        f"  → Aligner les deux valeurs OU refactorer cost_simulator_2026 pour lire YAML."
    )


def test_sg_cost_sim_02_capacite_unitaire_consistent_with_yaml_formula():
    """SG_COST_SIM_02 : CAPACITE_UNITAIRE_EUR_MWH ≈ (YAML tarif × coeff) / 8760.

    Sprint C-5 Phase 5.6 fix F4 (audit deep multi-agents) :
    Tolerance resserrée 1500 → 1.5 après correction F3 (YAML 3.15 → 3150 EUR/MW.an).
    L'écart x1000 historique (Sprint C-4 P4.2 typo) est désormais éliminé.

    Calcul attendu post-F3 :
    - YAML tarif = 3150 EUR/MW.an
    - YAML coeff = 1.2
    - Formule : 3150 × 1.2 / 8760 = 0.4315... EUR/MWh
    - Runtime : 0.43 EUR/MWh
    - Ratio : 0.4315 / 0.43 ≈ 1.004 (largement sous 1.5)

    Anti-régression : si quelqu'un revient à 3.15 ou modifie une valeur unilatéralement,
    le ratio explose au-delà de 1.5 → SG fail-fast.

    Formule canonique : (price_eur_per_mw_year × coeff) / 8760 = EUR/MWh
    """
    yaml_price = get_term_value("CAPACITE_RTE_TARIF_2026_EUR_PER_MW")  # 3150 post-F3
    yaml_coeff = get_term_value("CAPACITE_RTE_COEFF_2026")  # 1.2

    expected_formula_value = (yaml_price * yaml_coeff) / 8760  # ≈ 0.4315 EUR/MWh

    yaml_via_formula_or_runtime = max(expected_formula_value, CAPACITE_UNITAIRE_EUR_MWH)
    yaml_via_formula_or_runtime_min = min(expected_formula_value, CAPACITE_UNITAIRE_EUR_MWH)
    ratio_observed = yaml_via_formula_or_runtime / max(yaml_via_formula_or_runtime_min, 1e-9)

    # Sprint C-5 Phase 5.6 fix F4 : tolerance 1.5 (vs 1500 pré-F3).
    # Anti-régression cardinal : YAML/runtime/catalog doivent rester cohérents x1.5 max.
    _RATIO_TOLERANCE_MAX = 1.5
    assert ratio_observed <= _RATIO_TOLERANCE_MAX, (
        f"Dérive importante YAML↔cost_simulator capacité (ratio {ratio_observed:.1f}x) :\n"
        f"  YAML formule : ({yaml_price} × {yaml_coeff}) / 8760 = {expected_formula_value:.6f}\n"
        f"  cost_simulator_2026.CAPACITE_UNITAIRE_EUR_MWH = {CAPACITE_UNITAIRE_EUR_MWH}\n"
        f"  → Disambiguation Sprint C-5 (D-Phase4-2d-Capacite-EUR-MW-Disambiguation-001) "
        f"requise. Ne pas modifier l'une sans aligner les autres."
    )


def test_sg_cost_sim_03_capacite_unitaire_runtime_value_documented():
    """SG_COST_SIM_03 : CAPACITE_UNITAIRE_EUR_MWH conserve la valeur documentée 0.43 EUR/MWh.

    Anti-dérive : cette valeur est la SoT runtime (cf. cost_simulator_2026.py:64).
    Si elle bouge sans MAJ coordonnée du catalog billing_engine + YAML, ce SG bloque.
    Future migration vers lecture dynamique YAML : reporter Sprint C-5 (cf.
    D-Phase4-2-Catalog-CAPACITE-Unit-Mismatch-001 reclassé P1).
    """
    expected_value = 0.43
    delta = abs(CAPACITE_UNITAIRE_EUR_MWH - expected_value)
    assert delta < _TOLERANCE_NUMERIC_CAPACITE_EUR_MWH, (
        f"cost_simulator_2026.CAPACITE_UNITAIRE_EUR_MWH = {CAPACITE_UNITAIRE_EUR_MWH} "
        f"attendu ≈ {expected_value} EUR/MWh (tolérance {_TOLERANCE_NUMERIC_CAPACITE_EUR_MWH})."
        f" Si la valeur change, vérifier coordination catalog billing_engine + YAML "
        f"sources_reglementaires + dette D-Phase4-2-Catalog-CAPACITE-Unit-Mismatch-001."
    )
