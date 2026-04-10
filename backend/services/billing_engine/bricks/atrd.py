"""
PROMEOS — Brique ATRD (Accès aux Tiers aux Réseaux de Distribution gaz).

Remplace le calcul ATRD gaz basé sur un taux flat (€/kWh) par une
décomposition conforme à la doctrine ATRD7 GRDF :

    ATRD_HT = abonnement_proratisé
            + énergie_x_terme_proportionnel
            + (capacité_x_terme_capacité_proratisé)   ← T4 / TP uniquement

où :
- `abonnement_proratisé` = abo_eur_an × (period_days / 365)
- `énergie_x_terme_proportionnel` = energy_mwh × var_eur_mwh
- `capacité_x_terme_capacité_proratisé` = cja_mwh_per_day × capa_eur_mwh_j_an × (period_days / 365)

L'option ATRD (T1/T2/T3/T4/TP) est déterminée par la CAR GRDF du
DeliveryPoint. La fonction `compute_atrd()` accepte une `AtrdOption`
explicite et résout les taux via le ParameterStore (versionnés par date).

Bénéfices vs le calcul legacy `energy_mwh × 0.025 EUR/kWh` :
- Respecte l'abonnement annuel fixe (critique pour petits consommateurs)
- Différencie les 5 options tarifaires GRDF
- Expose l'assiette fixe (abonnement annuel) pour la CTA gaz qui en dépend
- Audit trail complet : option, taux unitaires, source réglementaire
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from ..parameter_store import ParameterResolution, ParameterStore


@dataclass(frozen=True)
class AtrdResult:
    """Résultat du calcul ATRD gaz avec audit trail complet."""

    option: str  # "T1" / "T2" / "T3" / "T4" / "TP"
    amount_ht: float  # total ATRD HT en EUR
    abonnement_ht: float  # part fixe proratisée
    proportionnel_ht: float  # kwh × terme proportionnel
    capacite_ht: float  # T4 / TP uniquement, sinon 0
    # Taux unitaires résolus (€/an, €/MWh, €/MWh/j/an)
    abo_eur_an: float
    prop_eur_mwh: float
    capa_eur_mwh_j_an: float
    # Quantités utilisées
    energy_mwh: float
    cja_mwh_per_day: float
    period_days: int
    # Traçabilité
    resolution_abo: ParameterResolution
    resolution_prop: ParameterResolution
    resolution_capa: Optional[ParameterResolution]

    @property
    def fixed_component_annual_eur(self) -> float:
        """
        Assiette annuelle fixe utile pour la CTA gaz (qui s'applique sur
        la part fixe de l'acheminement, donc l'abonnement annuel).
        """
        return self.abo_eur_an

    def to_dict(self) -> dict:
        return {
            "code": "atrd",
            "label": f"ATRD gaz {self.option}",
            "ht": round(self.amount_ht, 2),
            "option": self.option,
            "abonnement_ht": round(self.abonnement_ht, 2),
            "proportionnel_ht": round(self.proportionnel_ht, 2),
            "capacite_ht": round(self.capacite_ht, 2),
            "abo_eur_an": self.abo_eur_an,
            "prop_eur_mwh": self.prop_eur_mwh,
            "capa_eur_mwh_j_an": self.capa_eur_mwh_j_an,
            "period_days": self.period_days,
            "source": self.resolution_abo.source,
            "source_ref": self.resolution_abo.source_ref,
            "valid_from": self.resolution_abo.valid_from.isoformat() if self.resolution_abo.valid_from else None,
        }


def _prorata_year(period_days: int, basis_days: int = 365) -> float:
    """Fraction annuelle pour proratiser un terme annuel."""
    if period_days <= 0:
        return 0.0
    return period_days / basis_days


def compute_atrd(
    *,
    store: ParameterStore,
    option: str,
    energy_mwh: float,
    period_days: int,
    at_date: Optional[date] = None,
    cja_mwh_per_day: float = 0.0,
) -> AtrdResult:
    """
    Calcule la brique ATRD gaz selon l'option tarifaire GRDF.

    Args:
        store: ParameterStore partagé (source unique de vérité).
        option: "T1", "T2", "T3", "T4" ou "TP".
        energy_mwh: énergie consommée sur la période en MWh.
        period_days: nombre de jours de facturation.
        at_date: date de référence pour le versioning (défaut: today).
        cja_mwh_per_day: capacité journalière souscrite (T4/TP uniquement).

    Returns:
        AtrdResult avec audit trail complet.
    """
    if at_date is None:
        at_date = date.today()

    opt_upper = option.upper() if option else "T2"
    if opt_upper not in ("T1", "T2", "T3", "T4", "TP"):
        opt_upper = "T2"  # fallback prudent sur T2 (résidentiel chauffage)

    code_abo = f"ATRD_GAZ_{opt_upper}_ABO"
    code_prop = f"ATRD_GAZ_{opt_upper}_PROP"

    resolution_abo = store.get(code_abo, at_date=at_date)
    resolution_prop = store.get(code_prop, at_date=at_date)

    abo_eur_an = resolution_abo.value if resolution_abo.source != "missing" else 0.0
    prop_eur_mwh = resolution_prop.value if resolution_prop.source != "missing" else 0.0

    # Calcul terme capacité (T4 / TP uniquement)
    capa_eur_mwh_j_an = 0.0
    resolution_capa: Optional[ParameterResolution] = None
    if opt_upper in ("T4", "TP"):
        code_capa = f"ATRD_GAZ_{opt_upper}_CAPA"
        resolution_capa = store.get(code_capa, at_date=at_date)
        if resolution_capa.source != "missing":
            capa_eur_mwh_j_an = resolution_capa.value

    prorata = _prorata_year(period_days)
    abonnement_ht = abo_eur_an * prorata
    proportionnel_ht = max(energy_mwh, 0.0) * prop_eur_mwh
    capacite_ht = max(cja_mwh_per_day, 0.0) * capa_eur_mwh_j_an * prorata

    amount_ht = abonnement_ht + proportionnel_ht + capacite_ht

    return AtrdResult(
        option=opt_upper,
        amount_ht=amount_ht,
        abonnement_ht=abonnement_ht,
        proportionnel_ht=proportionnel_ht,
        capacite_ht=capacite_ht,
        abo_eur_an=abo_eur_an,
        prop_eur_mwh=prop_eur_mwh,
        capa_eur_mwh_j_an=capa_eur_mwh_j_an,
        energy_mwh=energy_mwh,
        cja_mwh_per_day=cja_mwh_per_day,
        period_days=period_days,
        resolution_abo=resolution_abo,
        resolution_prop=resolution_prop,
        resolution_capa=resolution_capa,
    )


def derive_atrd_option_from_car(car_kwh: Optional[float]) -> str:
    """
    Déduit l'option ATRD par défaut depuis la Consommation Annuelle de
    Référence (GRDF). Règles des seuils ATRD7 :

    - ≤ 6 000 kWh/an         → T1
    - 6 000 – 300 000 kWh/an → T2
    - 300 000 – 5 000 000 kWh/an → T3
    - > 5 000 000 kWh/an     → T4

    Sans CAR, fallback sur T2 (cas résidentiel chauffage le plus courant).
    """
    if car_kwh is None or car_kwh <= 0:
        return "T2"
    if car_kwh <= 6_000:
        return "T1"
    if car_kwh <= 300_000:
        return "T2"
    if car_kwh <= 5_000_000:
        return "T3"
    return "T4"
