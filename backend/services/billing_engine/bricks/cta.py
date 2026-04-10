"""
PROMEOS — Brique CTA (Contribution Tarifaire d'Acheminement).

Remplace le stub historique "taux 15% hardcodé" de billing_shadow_v2 par un
calcul conforme à la doctrine réglementaire.

DOCTRINE ÉLEC (simple) :

    CTA_elec = assiette_fixe × taux_dist_ou_transport

où `taux` vient de :
    * CTA_ELEC_DIST_RATE  (27,04% → 21,93% → 15% depuis 1/02/2026)
    * CTA_ELEC_TRANS_RATE (10,14% → 10,11% → 5% depuis 1/02/2026)

DOCTRINE GAZ (additive, Arrêté 20/07/2021 + arrêté annuel coef) :

    CTA_gaz_distribution = assiette × (taux_dist + taux_trans × coef_transport)
                         = assiette × (20,80% + 4,71% × coef)
                         ≈ assiette × 24,73% (au 1/07/2025, coef = 83,21%)

    CTA_gaz_transport    = assiette × taux_trans      (client raccordé ATRT)
                         = assiette × 4,71%

où :
- `assiette_fixe` = part fixe annuelle du tarif d'acheminement (TURPE gestion
  pour élec, abonnement ATRD T1-T4-TP pour gaz), proratisée ici sur la période.
- `coef_transport` est le coefficient de proportionnalité transport imputé
  aux clients distribution, révisé chaque 1/07 par arrêté annuel après avis
  CRE. 83,57% (2024) → 83,21% (2025).

Sources : Arrêté 20/07/2021 JORFTEXT000043847483, Délibération CRE 2024-82,
Arrêté 16/06/2025 JORFTEXT000051760148.

Particularité : la CTA ne dépend PAS des kWh consommés (assise sur l'abonnement).
La TVA applicable sur la CTA est gérée en aval par le pipeline TVA.
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


def _resolve_cta_gaz_effective_rate(
    store: ParameterStore,
    network_level: NetworkLevel,
    at_date: date,
) -> tuple[float, ParameterResolution]:
    """
    Calcule le taux effectif CTA gaz selon la doctrine additive :

    - distribution : taux_dist + taux_trans × coef_transport
    - transport    : taux_trans seul

    Retourne (taux_effectif, resolution_principale) — la `resolution` retournée
    est celle du taux distribution (ou transport si niveau transport), avec la
    source qui pointe vers l'arrêté de base ; les autres paramètres
    (trans_rate, coef) sont résolus implicitement pour composer le taux.
    """
    res_dist = store.get("CTA_GAZ_DIST_RATE", at_date=at_date)
    res_trans = store.get("CTA_GAZ_TRANS_RATE", at_date=at_date)
    res_coef = store.get("CTA_GAZ_TRANSPORT_COEF", at_date=at_date)

    dist_rate = res_dist.value if res_dist.source != "missing" else 0.0
    trans_rate = res_trans.value if res_trans.source != "missing" else 0.0
    coef = res_coef.value if res_coef.source != "missing" else 0.0

    if network_level == "transport":
        # Client raccordé direct au réseau transport : seul le taux transport
        # s'applique, sans coefficient (il paye déjà ses coûts transport réels).
        return trans_rate, res_trans

    effective = dist_rate + trans_rate * coef
    return effective, res_dist


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

    if energy == "gaz":
        # Doctrine additive (Arrêté 20/07/2021 + arrêté annuel coef)
        taux, resolution = _resolve_cta_gaz_effective_rate(store, network_level, at_date)
    else:
        # Élec : taux unique résolu directement
        code = _select_code(energy, network_level)
        resolution = store.get(code, at_date=at_date)
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
