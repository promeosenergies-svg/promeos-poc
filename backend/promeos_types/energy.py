"""
PROMEOS — Types stricts énergie (Sprint C-4 Phase 4.3, ADR-011).

Force la distinction unité kWh énergie finale (EF) PCI vs kWhEP (énergie primaire)
vs MWh vs GWh vs kWh PCS gaz GRDF. Différenciateur Bill Intelligence runtime :
catch les confusions à la signature des services consumers.

Pattern Option A enrichi pragmatique (ADR-011) :
- `NewType` Python — alias mypy-only (pas runtime check, mais cardinal cross-module)
- Helpers conversion typés — 1 SoT coefficients réglementaires
- Defense in depth complémentaire avec SG MVP Sprint C-3 Phase 3.4 (allowlist setattr)

Sources légales coefficients :
- Élec EF→EP : ×1.9 (arrêté 10/04/2020 art. 2-g, NOR LOGL2005904A)
- Gaz PCS→PCI : ×0.901 (GRDF Catalogue prestations 2025 §conversion)
- Multiples : ×1000 (MWh→kWh), ×1_000_000 (GWh→kWh)

Doctrine PROMEOS Sol §6.4 "1 SoT par concept" : tous coefficients de conversion
énergie centralisés ici (vs duplication dans services consumers).
"""

from __future__ import annotations

from typing import NewType, Union


# ─── Types stricts énergie (NewType — alias mypy-only) ───────────────────────


# kWh énergie finale PCI — unité cardinale PROMEOS (conso facturée / mesurée)
KwhEFPCI = NewType("KwhEFPCI", float)

# kWh énergie primaire — coeff 1.9 élec arrêté 10/04/2020 (DT/OPERAT)
KwhEP = NewType("KwhEP", float)

# MWh énergie finale PCI — multiple courant gros consommateurs
MWhEFPCI = NewType("MWhEFPCI", float)

# GWh énergie finale PCI — multiple AuditEnergetique (audits SMÉ obligation 2.75 GWh)
GWhEFPCI = NewType("GWhEFPCI", float)

# kWh PCS gaz — Pouvoir Calorifique Supérieur (GRDF R171 natif, ×0.901 pour PCI)
KwhPCS = NewType("KwhPCS", float)


# ─── Coefficients réglementaires (1 SoT) ─────────────────────────────────────


COEFF_KWH_EF_TO_KWH_EP_ELEC = 1.9
"""Coefficient EF→EP électricité (arrêté 10/04/2020 art. 2-g NOR LOGL2005904A)."""

COEFF_KWH_PCS_TO_KWH_PCI_GAZ = 0.901
"""Coefficient PCS→PCI gaz naturel (GRDF Catalogue prestations 2025)."""

FACTOR_MWH_TO_KWH = 1000
"""Facteur de conversion MWh → kWh (multiplicatif)."""

FACTOR_GWH_TO_KWH = 1_000_000
"""Facteur de conversion GWh → kWh (multiplicatif)."""


# ─── Helpers conversion typés ────────────────────────────────────────────────


def gwh_to_kwh_ef_pci(gwh: Union[GWhEFPCI, float]) -> KwhEFPCI:
    """Convertit GWh énergie finale PCI → kWhEF PCI (×1_000_000).

    Cas d'usage : `AuditEnergetique.conso_annuelle_moy_gwh` → kWh comparable
    `Site.annual_kwh_total`.
    """
    return KwhEFPCI(float(gwh) * FACTOR_GWH_TO_KWH)


def mwh_to_kwh_ef_pci(mwh: Union[MWhEFPCI, float]) -> KwhEFPCI:
    """Convertit MWh énergie finale PCI → kWhEF PCI (×1000).

    Cas d'usage : conversion uniforme multiple → unité cardinale.
    """
    return KwhEFPCI(float(mwh) * FACTOR_MWH_TO_KWH)


def kwh_pcs_to_kwh_ef_pci_gaz(kwh_pcs: Union[KwhPCS, float]) -> KwhEFPCI:
    """Convertit kWh PCS gaz GRDF → kWhEF PCI (×0.901).

    Cas d'usage cardinal : ingestion GRDF R171/R141 livre en PCS, doctrine
    PROMEOS = stockage en PCI (cohérence avec Enedis natif PCI). Sans conversion,
    conso surévaluée ~10% → Cabs OPERAT décalé → faux positifs alerte DT.

    Source : GRDF Catalogue prestations 2025 §conversion PCS→PCI.
    """
    return KwhEFPCI(float(kwh_pcs) * COEFF_KWH_PCS_TO_KWH_PCI_GAZ)


def kwh_ef_to_kwh_ep_elec(kwh_ef: Union[KwhEFPCI, float]) -> KwhEP:
    """Convertit kWhEF élec → kWhEP via coefficient 1.9 (arrêté 10/04/2020 art. 2-g).

    Cas d'usage : reporting OPERAT obligation tertiaire — la décote DT requiert
    énergie primaire pour alignement avec objectifs -40% / -50% / -60%.
    """
    return KwhEP(float(kwh_ef) * COEFF_KWH_EF_TO_KWH_EP_ELEC)


def kwh_ef_to_mwh(kwh_ef: Union[KwhEFPCI, float]) -> MWhEFPCI:
    """Convertit kWhEF PCI → MWhEF PCI (÷1000).

    Cas d'usage : affichage UI gros consommateurs (10 GWh+ → MWh lisible).
    """
    return MWhEFPCI(float(kwh_ef) / FACTOR_MWH_TO_KWH)


def kwh_ef_to_gwh(kwh_ef: Union[KwhEFPCI, float]) -> GWhEFPCI:
    """Convertit kWhEF PCI → GWhEF PCI (÷1_000_000).

    Cas d'usage : seuils audit SMÉ (`AUDIT_SME_THRESHOLD_GWH_PERIODIC = 2.75`,
    `AUDIT_SME_THRESHOLD_GWH_ISO50001 = 23.6`).
    """
    return GWhEFPCI(float(kwh_ef) / FACTOR_GWH_TO_KWH)
