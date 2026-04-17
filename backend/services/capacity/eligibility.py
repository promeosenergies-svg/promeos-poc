"""
PROMEOS Capacity — Eligibility Scoring

Évalue l'éligibilité d'un actif flexible au mécanisme de capacité RTE 2026+.
Règles issues de KB CAPACITE-ELIGIBILITE-ACTIFS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FlexAssetType(str, Enum):
    """Types d'actifs flexibles éligibles au mécanisme de capacité."""

    EFFACEMENT = "effacement"
    BESS = "bess"
    COGEN = "cogen"
    GROUPE_SECOURS = "groupe_secours"
    PAC_PILOTABLE = "pac_pilotable"
    IRVE_FLOTTE = "irve_flotte"


MIN_CERTIFICATION_MW = 1.0
MIN_EFFACEMENT_KW_PAR_BLOC = 100.0
MIN_DUREE_DISPONIBILITE_H = 2.0
MIN_DISPONIBILITE_PP1_PCT = 80.0
MAX_DELAI_MOBILISATION_MIN = 60

MIN_PUISSANCE_PAR_TYPE_KW: dict[FlexAssetType, float] = {
    FlexAssetType.EFFACEMENT: 100.0,
    FlexAssetType.BESS: 100.0,
    FlexAssetType.COGEN: 1000.0,
    FlexAssetType.GROUPE_SECOURS: 100.0,
    FlexAssetType.PAC_PILOTABLE: 100.0,
    FlexAssetType.IRVE_FLOTTE: 100.0,
}


@dataclass
class FlexibleAsset:
    """Actif flexible rattaché à un site."""

    asset_id: str
    site_id: int
    asset_type: FlexAssetType
    puissance_kw: float
    duree_disponibilite_h: float = 0.0
    disponibilite_annuelle_pct: float = 0.0
    delai_mobilisation_min: int = 0
    has_teleometrie: bool = False
    has_car: bool = False
    has_flex_ready_gtb: bool = False
    sous_obligation_achat: bool = False


@dataclass
class EligibilityScore:
    """Résultat scoring éligibilité."""

    eligible: bool
    score: int
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    puissance_certifiable_kw: float = 0.0
    kb_item_ids: list[str] = field(default_factory=lambda: ["CAPACITE-ELIGIBILITE-ACTIFS"])


def _check_blockers(asset: FlexibleAsset) -> list[str]:
    blockers: list[str] = []

    if asset.sous_obligation_achat:
        blockers.append("Actif sous obligation d'achat — exclusion mécanisme capacité")

    min_kw = MIN_PUISSANCE_PAR_TYPE_KW.get(asset.asset_type, MIN_CERTIFICATION_MW * 1000)
    if asset.puissance_kw < min_kw:
        blockers.append(
            f"Puissance {asset.puissance_kw:.0f} kW < seuil minimal {min_kw:.0f} kW pour {asset.asset_type.value}"
        )

    if asset.asset_type in (FlexAssetType.EFFACEMENT, FlexAssetType.IRVE_FLOTTE):
        if not asset.has_car:
            blockers.append("Contrat Accès Réseau (CAR) non signé")
        if not asset.has_teleometrie:
            blockers.append("Pas de télémétrie (Linky ou compteur dédié requis)")

    if asset.asset_type == FlexAssetType.PAC_PILOTABLE and not asset.has_flex_ready_gtb:
        blockers.append("GTB non conforme Flex Ready® (NF EN IEC 62746-4)")

    return blockers


def _compute_score(asset: FlexibleAsset) -> tuple[int, list[str]]:
    score = 0
    warnings: list[str] = []

    if asset.puissance_kw >= 1000:
        score += 30
    elif asset.puissance_kw >= 500:
        score += 20
    elif asset.puissance_kw >= 100:
        score += 10
    else:
        warnings.append("Puissance faible — agrégation requise pour atteindre 1 MW")

    if asset.duree_disponibilite_h >= MIN_DUREE_DISPONIBILITE_H:
        score += 20
    else:
        warnings.append(f"Durée {asset.duree_disponibilite_h}h < min {MIN_DUREE_DISPONIBILITE_H}h")

    if asset.disponibilite_annuelle_pct >= MIN_DISPONIBILITE_PP1_PCT:
        score += 25
    elif asset.disponibilite_annuelle_pct >= 60:
        score += 15
        warnings.append(f"Disponibilité {asset.disponibilite_annuelle_pct}% < min {MIN_DISPONIBILITE_PP1_PCT}% PP1")
    else:
        warnings.append(f"Disponibilité {asset.disponibilite_annuelle_pct}% trop faible")

    if asset.delai_mobilisation_min <= MAX_DELAI_MOBILISATION_MIN:
        score += 15
    else:
        warnings.append(f"Délai mobilisation {asset.delai_mobilisation_min}min > max {MAX_DELAI_MOBILISATION_MIN}min")

    if asset.has_teleometrie and asset.has_car:
        score += 10
    elif asset.has_teleometrie or asset.has_car:
        score += 5

    return min(score, 100), warnings


def compute_asset_eligibility(asset: FlexibleAsset) -> EligibilityScore:
    """Évalue l'éligibilité d'un actif individuel."""
    blockers = _check_blockers(asset)

    if blockers:
        return EligibilityScore(
            eligible=False,
            score=0,
            blockers=blockers,
            warnings=[],
            puissance_certifiable_kw=0.0,
        )

    score, warnings = _compute_score(asset)
    puissance_certifiable_kw = asset.puissance_kw * (asset.disponibilite_annuelle_pct / 100.0)

    return EligibilityScore(
        eligible=True,
        score=score,
        blockers=[],
        warnings=warnings,
        puissance_certifiable_kw=round(puissance_certifiable_kw, 2),
    )


def compute_portfolio_eligibility(assets: list[FlexibleAsset]) -> EligibilityScore:
    """Évalue l'éligibilité d'un portefeuille avec agrégation 1 MW."""
    individual_scores = [compute_asset_eligibility(a) for a in assets]
    eligible_scores = [s for s in individual_scores if s.eligible]

    if not eligible_scores:
        return EligibilityScore(
            eligible=False,
            score=0,
            blockers=["Aucun actif individuellement éligible"],
            warnings=[],
            puissance_certifiable_kw=0.0,
        )

    total_certifiable_kw = sum(s.puissance_certifiable_kw for s in eligible_scores)
    avg_score = int(sum(s.score for s in eligible_scores) / len(eligible_scores))

    all_warnings: list[str] = []
    for s in eligible_scores:
        all_warnings.extend(s.warnings)

    blockers: list[str] = []
    if total_certifiable_kw < MIN_CERTIFICATION_MW * 1000:
        blockers.append(
            f"Puissance certifiable agrégée {total_certifiable_kw:.0f} kW < "
            f"seuil minimal {MIN_CERTIFICATION_MW * 1000:.0f} kW"
        )

    return EligibilityScore(
        eligible=len(blockers) == 0,
        score=avg_score,
        blockers=blockers,
        warnings=all_warnings,
        puissance_certifiable_kw=round(total_certifiable_kw, 2),
    )
