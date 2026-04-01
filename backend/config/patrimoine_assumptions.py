"""
PROMEOS — Hypothèses de calcul d'impact patrimoine (V59)

Option A : hypothèses simples configurables, sans stockage DB.
Toutes les valeurs sont des defaults prudents B2B France.

Modifiables sans réécriture : instancier PatrimoineAssumptions(prix_elec_eur_mwh=140) etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH, DEFAULT_PRICE_GAZ_EUR_KWH

# ── Defaults B2B France ───────────────────────────────────────────────────────

#: Prix moyen électricité (€/MWh) — dérivé du référentiel centralisé (default_prices.py)
PRIX_ELEC_EUR_MWH_DEFAULT: float = DEFAULT_PRICE_ELEC_EUR_KWH * 1000.0

#: Prix moyen gaz naturel (€/MWh) — dérivé du référentiel centralisé (default_prices.py)
PRIX_GAZ_EUR_MWH_DEFAULT: float = DEFAULT_PRICE_GAZ_EUR_KWH * 1000.0

#: Consommation annuelle fallback global (kWh/an) — site B2B moyen
CONSO_FALLBACK_GLOBAL_KWH_AN: float = 300_000.0

#: Consommation annuelle par usage (kWh/an)
CONSO_FALLBACK_BY_USAGE: Dict[str, float] = {
    "bureaux": 250_000.0,
    "bureau": 250_000.0,  # alias
    "commerce": 350_000.0,
    "logistique": 180_000.0,
    "entrepot": 180_000.0,  # alias
    "industrie": 500_000.0,
    "hotellerie": 400_000.0,
    "sante": 300_000.0,
    "enseignement": 200_000.0,
}

#: Consommation par m² par usage (kWh/m²/an) pour SURFACE_MISMATCH
CONSO_KWH_M2_AN_BY_USAGE: Dict[str, float] = {
    "bureaux": 250.0,
    "bureau": 250.0,
    "commerce": 350.0,
    "logistique": 80.0,
    "entrepot": 80.0,
    "industrie": 200.0,
    "hotellerie": 300.0,
    "sante": 250.0,
    "enseignement": 150.0,
}

#: Consommation par m² fallback global (kWh/m²/an)
CONSO_KWH_M2_AN_DEFAULT: float = 200.0

#: Benchmarks ADEME — source unique : config/ademe_benchmarks.py
from config.ademe_benchmarks import BENCHMARK_BY_BUILDING_TYPE as BENCHMARK_ADEME_KWH_M2_AN  # noqa: E402

#: CEE — prix moyen du MWhc cumac (EUR/MWhc) pour estimation ROI
#: Source : Registre national CEE, cotation moyenne 2024
CEE_PRIX_MWHC_CUMAC_EUR: float = 8.50

#: Facteur horizon (1 = annualisé, pas de projection multi-annuelle en V59)
HORIZON_FACTOR: float = 1.0

#: Tolérance écart surface (%) — repris de SURFACE_MISMATCH_TOLERANCE V58
SURFACE_MISMATCH_TOLERANCE_PCT: float = 5.0


# ── Dataclass ─────────────────────────────────────────────────────────────────


@dataclass
class PatrimoineAssumptions:
    """
    Hypothèses configurables pour le calcul d'impact patrimoine.

    Usage :
        # Defaults
        a = PatrimoineAssumptions()
        # Override partiel
        a = PatrimoineAssumptions(prix_elec_eur_mwh=140)
    """

    prix_elec_eur_mwh: float = PRIX_ELEC_EUR_MWH_DEFAULT
    prix_gaz_eur_mwh: float = PRIX_GAZ_EUR_MWH_DEFAULT
    conso_fallback_kwh_an: float = CONSO_FALLBACK_GLOBAL_KWH_AN
    conso_fallback_by_usage: Dict[str, float] = field(default_factory=lambda: dict(CONSO_FALLBACK_BY_USAGE))
    conso_kwh_m2_an_by_usage: Dict[str, float] = field(default_factory=lambda: dict(CONSO_KWH_M2_AN_BY_USAGE))
    conso_kwh_m2_an_default: float = CONSO_KWH_M2_AN_DEFAULT
    horizon_factor: float = HORIZON_FACTOR
    surface_mismatch_tolerance_pct: float = SURFACE_MISMATCH_TOLERANCE_PCT

    # ── Propriétés dérivées ───────────────────────────────────────────────────

    @property
    def prix_elec_eur_kwh(self) -> float:
        """Prix électricité en €/kWh (conversion depuis MWh)."""
        return self.prix_elec_eur_mwh / 1000.0

    @property
    def prix_gaz_eur_kwh(self) -> float:
        """Prix gaz en €/kWh (conversion depuis MWh)."""
        return self.prix_gaz_eur_mwh / 1000.0

    def conso_for_usage(self, usage: Optional[str]) -> float:
        """Retourne la conso annuelle fallback (kWh/an) pour un usage."""
        if usage:
            key = usage.lower()
            if key in self.conso_fallback_by_usage:
                return self.conso_fallback_by_usage[key]
        return self.conso_fallback_kwh_an

    def conso_m2_for_usage(self, usage: Optional[str]) -> float:
        """Retourne la conso kWh/m²/an pour un usage."""
        if usage:
            key = usage.lower()
            if key in self.conso_kwh_m2_an_by_usage:
                return self.conso_kwh_m2_an_by_usage[key]
        return self.conso_kwh_m2_an_default

    def to_dict(self) -> dict:
        """Sérialisation pour exposition via API (lecture seule)."""
        return {
            "prix_elec_eur_mwh": self.prix_elec_eur_mwh,
            "prix_gaz_eur_mwh": self.prix_gaz_eur_mwh,
            "conso_fallback_kwh_an": self.conso_fallback_kwh_an,
            "conso_kwh_m2_an_default": self.conso_kwh_m2_an_default,
            "horizon_factor": self.horizon_factor,
            "surface_mismatch_tolerance_pct": self.surface_mismatch_tolerance_pct,
            "conso_fallback_by_usage": self.conso_fallback_by_usage,
            "conso_kwh_m2_an_by_usage": self.conso_kwh_m2_an_by_usage,
        }


#: Instance singleton — default B2B France
DEFAULT_ASSUMPTIONS = PatrimoineAssumptions()
