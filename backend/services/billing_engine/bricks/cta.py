"""
PROMEOS — Brique CTA (Contribution Tarifaire d'Acheminement).

Remplace le stub historique "taux 15% hardcodé" de billing_shadow_v2 par un
calcul conforme à la doctrine :

    CTA = assiette_fixe × taux

où :
- `assiette_fixe` = part fixe du tarif d'acheminement (TURPE gestion pour
  l'élec, ATRD fixe pour le gaz), proratisée sur la période de facturation.
- `taux` = ratio versionné (par date d'effet et scope) via ParameterStore :
    * CTA_ELEC_DIST_RATE  (ex-27,04% → 21,93% → 15% depuis 1/02/2026)
    * CTA_ELEC_TRANS_RATE (ex-10,14% → 10,11% → 5% depuis 1/02/2026)
    * CTA_GAZ_DIST_RATE   (20,80% — stable)
    * CTA_GAZ_TRANS_RATE  (4,71% — stable, fallback sur DIST si absent)

Particularités :
- La CTA ne dépend PAS des kWh consommés (elle est assise sur l'abonnement).
- Elle est soumise à TVA 20% (TVA normale) depuis le 1/08/2025 ; avant, elle
  bénéficiait du taux réduit 5,5% — le versionnement TVA est géré en aval
  par le pipeline TVA, pas ici.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, Optional

from ..parameter_store import ParameterResolution, ParameterStore

EnergyKind = Literal["elec", "gaz"]
NetworkLevel = Literal["distribution", "transport"]


@dataclass(frozen=True)
class CtaResult:
    """Résultat du calcul CTA avec audit trail complet."""

    amount_ht: float  # CTA HT en EUR
    rate: float  # taux utilisé (ratio, p. ex. 0.208)
    assiette_fixe: float  # assiette en EUR (part fixe proratisée)
    energy: EnergyKind
    network_level: NetworkLevel
    resolution: ParameterResolution  # trace complète du paramètre résolu

    def to_dict(self) -> dict:
        return {
            "code": "cta",
            "label": f"CTA ({self.energy} {self.network_level})",
            "ht": round(self.amount_ht, 2),
            "rate": round(self.rate, 6),
            "assiette_fixe": round(self.assiette_fixe, 2),
            "energy": self.energy,
            "network_level": self.network_level,
            "source": self.resolution.source,
            "source_ref": self.resolution.source_ref,
            "valid_from": self.resolution.valid_from.isoformat() if self.resolution.valid_from else None,
        }


def _select_code(energy: EnergyKind, network_level: NetworkLevel) -> str:
    if energy == "elec":
        return "CTA_ELEC_DIST_RATE" if network_level == "distribution" else "CTA_ELEC_TRANS_RATE"
    return "CTA_GAZ_DIST_RATE" if network_level == "distribution" else "CTA_GAZ_TRANS_RATE"


def _prorata_fraction(period_days: int, basis_days: int = 365) -> float:
    """Fraction de l'année pour proratiser une assiette annuelle."""
    if period_days <= 0:
        return 0.0
    return period_days / basis_days


def compute_cta(
    *,
    store: ParameterStore,
    energy: EnergyKind,
    network_level: NetworkLevel = "distribution",
    fixed_component_annual_eur: float,
    period_days: int,
    at_date: Optional[date] = None,
) -> CtaResult:
    """
    Calcule la CTA sur une période.

    Args:
        store: ParameterStore partagé (source unique de vérité).
        energy: "elec" ou "gaz".
        network_level: "distribution" (GRD) ou "transport" (GRT / >= 50 kV).
        fixed_component_annual_eur: part fixe annuelle du tarif d'acheminement
            (TURPE gestion + comptage pour élec, ATRD abonnement T1-T4 pour gaz).
            Exprimée en EUR/an, sans prorata (le prorata est appliqué ici).
        period_days: nombre de jours de la facture.
        at_date: date de référence pour la résolution du taux. Par défaut,
            on prend la date médiane de la période (period_days/2 après today).
            Le moteur appelant doit passer explicitement la date pour éviter
            toute dépendance à today().

    Returns:
        CtaResult (voir classe) avec montant HT, taux, assiette et audit.
    """
    if at_date is None:
        at_date = date.today()

    code = _select_code(energy, network_level)
    resolution = store.get(code, at_date=at_date)

    # Si le code n'est pas résolu, on logge via la resolution.source == "missing"
    # et on retourne un montant 0 explicite. Le pipeline en amont peut décider
    # d'un statut "missing_price" sur la composante CTA.
    taux = resolution.value if resolution.source != "missing" else 0.0

    prorata = _prorata_fraction(period_days, basis_days=365)
    assiette = fixed_component_annual_eur * prorata
    amount_ht = assiette * taux

    return CtaResult(
        amount_ht=amount_ht,
        rate=taux,
        assiette_fixe=assiette,
        energy=energy,
        network_level=network_level,
        resolution=resolution,
    )


def compute_cta_from_period_bounds(
    *,
    store: ParameterStore,
    energy: EnergyKind,
    network_level: NetworkLevel,
    fixed_component_annual_eur: float,
    period_start: date,
    period_end: date,
) -> CtaResult:
    """
    Variante qui accepte directement un intervalle [period_start, period_end].

    Utilise la date médiane pour la résolution du taux. Pour une facture à
    cheval sur un changement de taux, il faut découper la période en amont
    (c'est le rôle de `split_period_by_regulatory_changes`) et appeler ce
    helper une fois par sous-période.
    """
    delta = (period_end - period_start).days
    if delta <= 0:
        delta = 1
    mid = period_start + timedelta(days=delta // 2)
    return compute_cta(
        store=store,
        energy=energy,
        network_level=network_level,
        fixed_component_annual_eur=fixed_component_annual_eur,
        period_days=delta,
        at_date=mid,
    )
