"""
PROMEOS — Brique CBAM (Mécanisme d'Ajustement Carbone aux Frontières).

CBAM = taxe européenne sur les importations de biens carbo-intensifs depuis
des pays hors UE (Carbon Border Adjustment Mechanism, Règlement 2023/956).
Activé commercialement le **7 avril 2026** avec un premier prix de 75,36 €/tCO2
(Commission européenne, source `tarifs_reglementaires.yaml::cbam_eu`).

DOCTRINE

    CBAM_eur = Σ_scope (volume_t × intensity_tco2_per_t × rate_eur_per_tco2)

où `scope` ∈ {acier, ciment, aluminium, engrais, hydrogene, electricite}.

INTÉGRATION PROMEOS

Contrairement aux composantes factures énergie standard (TURPE, accise, CTA,
TVA), la CBAM **n'est pas une ligne de la facture électricité**. C'est une
obligation fiscale séparée portant sur la chaîne d'approvisionnement du
client. PROMEOS l'expose dans le cockpit comme un **scope CBAM estimé**
pour:
  1. positionnement wedge — "premier cockpit énergie B2B France avec audit CBAM"
  2. sensibilisation CFO — alertes si le client importe un produit couvert
  3. simulation d'exposition — scénarios volume × intensité

POSITIONNEMENT DOCTRINE

Si le site/client n'a aucune importation CBAM déclarée (cas général pour un
tertiaire standard), `compute_cbam({})` retourne 0 EUR avec note explicite
« non applicable — aucune importation hors UE déclarée ». La doctrine du
cost simulator (`cbam_scope = 0` par défaut) est préservée.

Si le client déclare des volumes d'import (via `site.cbam_imports_tonnes`),
la brique calcule l'exposition annuelle avec traçabilité complète
(intensités par défaut CE, rate CBAM versionné YAML).

Sources :
- Règlement UE 2023/956 — mécanisme CBAM
- Implementing Regulation 2023/1773 — intensités par défaut (annexe)
- `tarifs_reglementaires.yaml::cbam_eu` — rate + intensités versionnées
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Optional

import yaml

from utils.parameter_store_base import load_yaml_section

logger = logging.getLogger(__name__)

# Scopes CBAM officiels (Règlement 2023/956, article 2). Source de vérité
# canonique côté YAML via `cbam_eu.scope`, listé ici pour validation type.
CBAM_SCOPES = frozenset(["acier", "ciment", "aluminium", "engrais", "hydrogene", "electricite"])

# Fallbacks hardcodés si YAML indisponible (valeurs au 2026-04-07).
DEFAULT_RATE_EUR_PER_TCO2 = 75.36
DEFAULT_INTENSITIES = {
    "acier": 2.0,
    "ciment": 0.66,
    "aluminium": 16.5,
    "engrais": 2.6,
    "hydrogene": 10.0,
    "electricite": 0.45,
}


IntensitySource = Literal["site_specific", "default_ce"]


@dataclass(frozen=True)
class CbamScopeBreakdown:
    """Détail par scope pour audit."""

    scope: str
    volume_t: float
    intensity_tco2_per_t: float
    co2_embedded_t: float  # = volume × intensity
    cost_eur: float  # = co2 × rate
    intensity_source: IntensitySource


@dataclass(frozen=True)
class CbamResult:
    """Exposition CBAM annuelle avec détail par scope."""

    total_cost_eur: float  # Somme des coûts par scope (EUR)
    total_co2_embedded_t: float  # Tonnes CO2 cumulées
    rate_eur_per_tco2: float  # Rate CBAM utilisé
    rate_at_date: date  # Date de résolution du rate
    breakdown: list[CbamScopeBreakdown] = field(default_factory=list)
    applicable: bool = False  # True si au moins 1 scope non nul
    note: str = ""


def _load_cbam_params() -> tuple[float, dict[str, float]]:
    """Charge rate + intensités par défaut depuis `tarifs_reglementaires.yaml::cbam_eu`.

    Fallback sur les constantes hardcodées (`DEFAULT_RATE_EUR_PER_TCO2` +
    `DEFAULT_INTENSITIES`) en cas d'indisponibilité YAML — warning loggé
    pour visibilité prod.
    """
    try:
        section = load_yaml_section("cbam_eu") or {}
        rate = float(section.get("rate_eur_per_t_co2", DEFAULT_RATE_EUR_PER_TCO2))
        intensities = {str(k): float(v) for k, v in (section.get("default_intensity_tco2_per_t") or {}).items()}
        # Compléter avec défauts hardcodés pour les scopes manquants.
        for scope, default_int in DEFAULT_INTENSITIES.items():
            intensities.setdefault(scope, default_int)
        return rate, intensities
    except (FileNotFoundError, KeyError, ValueError, yaml.YAMLError) as exc:
        logger.warning("cbam: params YAML indisponible (fallback hardcoded) — %s", exc)
        return DEFAULT_RATE_EUR_PER_TCO2, dict(DEFAULT_INTENSITIES)


def compute_cbam(
    cbam_imports: Optional[dict[str, float]],
    at_date: date,
    site_specific_intensities: Optional[dict[str, float]] = None,
) -> CbamResult:
    """Calcule l'exposition CBAM annuelle pour un site.

    Args
    ----
    cbam_imports : dict[scope, tonnes_par_an] — volumes annuels d'importation
        hors UE par scope CBAM. Si `None` ou vide, le site n'a aucune exposition
        déclarée → retour CbamResult(total_cost_eur=0, applicable=False).
    at_date : date de référence pour résoudre le rate CBAM versionné.
    site_specific_intensities : optionnel — intensités carbone vérifiées
        site par site (surcharge les défauts CE). Priorité site > défaut.

    Returns
    -------
    CbamResult avec breakdown détaillé par scope + rate + audit trail.
    """
    rate, defaults = _load_cbam_params()
    site_intensities = site_specific_intensities or {}

    if not cbam_imports:
        return CbamResult(
            total_cost_eur=0.0,
            total_co2_embedded_t=0.0,
            rate_eur_per_tco2=rate,
            rate_at_date=at_date,
            breakdown=[],
            applicable=False,
            note=(
                "CBAM non applicable — aucune importation hors UE déclarée "
                "pour ce site (scope PROMEOS = consommation électrique FR directe)."
            ),
        )

    breakdown: list[CbamScopeBreakdown] = []
    total_cost = 0.0
    total_co2 = 0.0

    for scope, volume_t in cbam_imports.items():
        if scope not in CBAM_SCOPES:
            continue  # Ignore silencieusement scopes inconnus (MVP défensif).
        vol = float(volume_t or 0.0)
        if vol <= 0:
            continue

        # Priorité : intensité site-specific (vérifiée auditeur) > défaut CE.
        if scope in site_intensities:
            intensity = float(site_intensities[scope])
            intensity_source = "site_specific"
        else:
            intensity = float(defaults.get(scope, 0.0))
            intensity_source = "default_ce"

        co2 = vol * intensity
        cost = co2 * rate

        breakdown.append(
            CbamScopeBreakdown(
                scope=scope,
                volume_t=round(vol, 3),
                intensity_tco2_per_t=round(intensity, 4),
                co2_embedded_t=round(co2, 3),
                cost_eur=round(cost, 2),
                intensity_source=intensity_source,
            )
        )
        total_co2 += co2
        total_cost += cost

    applicable = total_cost > 0
    note = (
        f"CBAM applicable — {len(breakdown)} scope(s) importé(s), "
        f"{round(total_co2, 2)} tCO2 × {rate} €/tCO2 = {round(total_cost, 2)} €/an."
        if applicable
        else "CBAM non applicable — volumes importés nuls."
    )

    return CbamResult(
        total_cost_eur=round(total_cost, 2),
        total_co2_embedded_t=round(total_co2, 3),
        rate_eur_per_tco2=rate,
        rate_at_date=at_date,
        breakdown=breakdown,
        applicable=applicable,
        note=note,
    )
