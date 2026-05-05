"""
PROMEOS — Types stricts énergie (Sprint C-4 Phase 4.3 + 4.3d, ADR-011).

Force la distinction unité kWh énergie finale (EF) PCI vs GWh vs kWh PCS gaz GRDF.
Différenciateur Bill Intelligence runtime : catch les confusions à la signature
des services consumers.

Pattern Option A enrichi pragmatique (ADR-011) :
- `NewType` Python — alias mypy-only (pas runtime check, mais cardinal cross-module)
- Helpers conversion typés — 1 SoT coefficients réglementaires
- Defense in depth complémentaire avec SG MVP Sprint C-3 Phase 3.4 (allowlist setattr)

Sources légales coefficients :
- Gaz PCS→PCI : ×0.901 (GRDF Catalogue prestations 2025 §conversion ; cohérent
  arrêté 15/09/2006 méthode DPE / DGEC barème)
- Multiples : ×1_000_000 (GWh→kWh)

Doctrine PROMEOS Sol §6.4 "1 SoT par concept" : tous coefficients de conversion
énergie centralisés ici (vs duplication dans services consumers).

Phase 4.3d audit follow-up (2026-05-05) — suppressions doctrinales :
- COEFF_KWH_EF_TO_KWH_EP_ELEC = 1.9 SUPPRIMÉ (valeur fantôme : pas de coefficient
  officiel français connu ; arrêté 10/04/2020 OPERAT NOR LOGL2005904A art. 2-g
  raisonne en EF, pas EP). Si besoin Sprint C-5+ RE2020 : réintroduire avec source
  PDF arrêté 04/08/2021 NOR LOGL2107359A (coef 2.3) committée.
- KwhEP, MWhEFPCI, kwh_ef_to_kwh_ep_elec, mwh_to_kwh_ef_pci, kwh_ef_to_mwh,
  kwh_ef_to_gwh : YAGNI cleanup (aucun consumer).
- Guards `finite + non-negative` ajoutés sur helpers conservés.
"""

from __future__ import annotations

import math
from typing import NewType, Union


# ─── Types stricts énergie (NewType — alias mypy-only) ───────────────────────


# kWh énergie finale PCI — unité cardinale PROMEOS (conso facturée / mesurée)
KwhEFPCI = NewType("KwhEFPCI", float)

# GWh énergie finale PCI — multiple AuditEnergetique (audits SMÉ obligation 2.75 GWh)
GWhEFPCI = NewType("GWhEFPCI", float)

# kWh PCS gaz — Pouvoir Calorifique Supérieur (GRDF R171 natif, ×0.901 pour PCI)
KwhPCS = NewType("KwhPCS", float)


# ─── Coefficients réglementaires (1 SoT) ─────────────────────────────────────


COEFF_KWH_PCS_TO_KWH_PCI_GAZ = 0.901
"""Coefficient PCS→PCI gaz naturel (GRDF Catalogue prestations 2025).
Cohérent arrêté 15/09/2006 méthode DPE / DGEC barème national. Source PDF
GRDF à committer Sprint C-7 (D-Phase4-2-Sources-URLs-Verifier-001)."""

FACTOR_GWH_TO_KWH = 1_000_000
"""Facteur de conversion GWh → kWh (multiplicatif)."""


# ─── Guards de validation ─────────────────────────────────────────────────────


def _validate_finite_non_negative(value: float, name: str) -> None:
    """Guard cardinal Phase 4.3d : valeur finie et non-négative.

    Raises:
        ValueError: si NaN, Inf, ou < 0 (énergie négative impossible doctrinalement).
    """
    if not math.isfinite(value):
        raise ValueError(f"{name} doit être fini (pas NaN ni Inf), reçu {value!r}")
    if value < 0:
        raise ValueError(f"{name} doit être non-négatif (énergie ≥ 0), reçu {value}")


# ─── Helpers conversion typés ────────────────────────────────────────────────


def gwh_to_kwh_ef_pci(gwh: Union[GWhEFPCI, float]) -> KwhEFPCI:
    """Convertit GWh énergie finale PCI → kWhEF PCI (×1_000_000).

    Cas d'usage cardinal : `AuditEnergetique.conso_annuelle_moy_gwh` → kWh
    comparable `Site.annual_kwh_total`. Seuils audit SMÉ : 2.75 GWh / 23.6 GWh.

    Raises:
        ValueError: si gwh non fini ou < 0.
    """
    _validate_finite_non_negative(float(gwh), "gwh")
    return KwhEFPCI(float(gwh) * FACTOR_GWH_TO_KWH)


def kwh_pcs_to_kwh_ef_pci_gaz(kwh_pcs: Union[KwhPCS, float]) -> KwhEFPCI:
    """Convertit kWh PCS gaz GRDF → kWhEF PCI (×0.901).

    Cas d'usage cardinal : ingestion GRDF R171/R141 livre en PCS, doctrine
    PROMEOS = stockage en PCI (cohérence avec Enedis natif PCI). Sans conversion,
    conso surévaluée ~10% → Cabs OPERAT décalé → faux positifs alerte DT.

    Source : GRDF Catalogue prestations 2025 §conversion PCS→PCI.

    Raises:
        ValueError: si kwh_pcs non fini ou < 0.
    """
    _validate_finite_non_negative(float(kwh_pcs), "kwh_pcs")
    return KwhEFPCI(float(kwh_pcs) * COEFF_KWH_PCS_TO_KWH_PCI_GAZ)
