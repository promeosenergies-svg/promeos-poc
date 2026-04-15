"""
PROMEOS - Lead Score Service (V116 Option B — wedge monetisation)

Calcule un score de lead depuis les donnees Sirene pour :
  1. Pre-qualifier commercialement un SIREN avant meme l'inscription
  2. Segmenter le pricing (PME/ETI/GE)
  3. Alimenter un futur CRM avec priorite A/B/C

Input : SIREN present dans sirene_unites_legales + sirene_etablissements
Output : {segment, estimated_mrr_eur, priority, drivers}

Aucune dependance sur des donnees privees (effectifs precis, CA). Utilise
uniquement les champs publics Sirene stockes localement.
"""

from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from models.sirene import SireneEtablissement, SireneUniteLegale


class LeadSegment(str, Enum):
    """Segmentation INSEE entreprise (LME 2008, stable 2025-2026)."""

    TPE = "TPE"
    PME = "PME"
    ETI = "ETI"
    GE = "GE"


class LeadPriority(str, Enum):
    """Priorite commerciale PROMEOS."""

    A = "A"  # Deal chaud
    B = "B"  # Deal tiede
    C = "C"  # Deal froid


class NafValueTier(str, Enum):
    """Tier de valeur PROMEOS par prefix NAF (complexite reglementaire)."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


# ══════════════════════════════════════════════════════════════════════
# Grille pricing PROMEOS (calibree sur docs/ux_demo_strategy)
# 400-2000 EUR/mois documentee + extensions GE grandes flottes
# ══════════════════════════════════════════════════════════════════════

# Prix de base par segment (EUR/mois, base 1-5 sites)
# Valeurs par defaut, surchargees par config/pricing_lead_score.yaml (V119.3)
_BASE_MRR_DEFAULT = {
    LeadSegment.TPE: 200,  # <10 salaries, 1-2 sites
    LeadSegment.PME: 600,  # 10-250 salaries, 1-20 sites
    LeadSegment.ETI: 2000,  # 250-5000 salaries, 10-100 sites
    LeadSegment.GE: 6000,  # >5000 salaries, 100+ sites
}

# Cache module-level pour eviter de re-parser le YAML a chaque call
_PRICING_CACHE = None


def _load_pricing_config() -> dict:
    """Charge la grille pricing depuis YAML avec fallback sur les defaults.

    Cache module-level : reset via _reset_pricing_cache() en test.
    Format normalise : {base_mrr: {LeadSegment: int}, naf_boost: {NafValueTier: float},
                       sites_multiplier: [(max, factor), ...]}
    """
    global _PRICING_CACHE
    if _PRICING_CACHE is not None:
        return _PRICING_CACHE

    import logging
    from pathlib import Path

    config_path = Path(__file__).resolve().parent.parent / "config" / "pricing_lead_score.yaml"
    base_mrr = dict(_BASE_MRR_DEFAULT)
    naf_boost = dict(_NAF_BOOST_DEFAULT)
    sites_multiplier = list(_SITES_MULTIPLIER_DEFAULT)

    if config_path.exists():
        try:
            import yaml

            with open(config_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            if isinstance(raw.get("base_mrr"), dict):
                for k, v in raw["base_mrr"].items():
                    try:
                        base_mrr[LeadSegment(k)] = int(v)
                    except (ValueError, KeyError):
                        pass
            if isinstance(raw.get("naf_boost"), dict):
                for k, v in raw["naf_boost"].items():
                    try:
                        naf_boost[NafValueTier(k)] = float(v)
                    except (ValueError, KeyError):
                        pass
            if isinstance(raw.get("sites_multiplier"), list):
                parsed = []
                for entry in raw["sites_multiplier"]:
                    if isinstance(entry, dict) and "max" in entry and "factor" in entry:
                        parsed.append((int(entry["max"]), float(entry["factor"])))
                if parsed:
                    sites_multiplier = parsed
        except Exception as e:
            logging.getLogger(__name__).warning("pricing_lead_score.yaml load failed, using defaults: %s", e)

    _PRICING_CACHE = {"base_mrr": base_mrr, "naf_boost": naf_boost, "sites_multiplier": sites_multiplier}
    return _PRICING_CACHE


def _reset_pricing_cache() -> None:
    """Reset le cache pricing (utile en test apres modif YAML)."""
    global _PRICING_CACHE
    _PRICING_CACHE = None


# Multiplicateur par tranche d'etablissements
# Charge depuis YAML si present (V119.3), sinon fallback hardcode
_SITES_MULTIPLIER_DEFAULT = [
    (5, 1.0),
    (20, 1.8),
    (100, 3.5),
    (500, 6.0),
    (999999, 10.0),  # >500 sites = enterprise deal
]


def _sites_multiplier(n_etabs: int) -> float:
    pricing = _load_pricing_config()
    for entry in pricing["sites_multiplier"]:
        if n_etabs <= entry[0]:
            return entry[1]
    return pricing["sites_multiplier"][-1][1]


# ══════════════════════════════════════════════════════════════════════
# NAF -> complexite reglementaire (drivers de valeur PROMEOS)
# ══════════════════════════════════════════════════════════════════════

# Les prefixes NAF avec le + de contraintes compliance = + de valeur PROMEOS
_NAF_HIGH_VALUE_PREFIXES = {
    "47",  # Commerce retail (decret tertiaire + BACS)
    "55",  # Hotellerie (DT + BACS + IRVE)
    "56",  # Restauration (DT + hotte + CEE)
    "68",  # Immobilier (DT + multi-lot)
    "85",  # Enseignement (DT + BACS)
    "86",  # Sante (DT + BACS + critique)
    "87",  # EHPAD (DT + BACS + vulnerable)
}
_NAF_MEDIUM_VALUE_PREFIXES = {
    "10",
    "11",
    "12",  # Industrie agro/boissons/tabac (process energivore)
    "20",
    "21",
    "22",  # Chimie/pharma/plastique
    "25",
    "26",
    "27",  # Metaux/electronique/electrique
    "28",
    "29",
    "30",  # Machines/auto/transport
    "41",
    "42",
    "43",  # BTP
    "52",
    "53",  # Entreposage/courrier (flex potential)
    "64",
    "65",
    "66",  # Banque/assurance (tertiaire pur)
    "69",
    "70",
    "71",  # Juridique/conseil
    "72",
    "73",
    "74",  # R&D/pub/design
    "82",  # Services admin
    "84",  # Administration publique
}

# NAF faible valeur energetique pour PROMEOS (agriculture non-process)
_NAF_LOW_VALUE_PREFIXES = {
    "01",
    "02",
    "03",  # Agriculture/peche
}


def _resolve_segment(ul: SireneUniteLegale, n_etabs: int) -> LeadSegment:
    """Deduit le segment depuis categorie_entreprise INSEE (prioritaire)
    avec fallback sur le nombre d'etablissements."""
    cat = (ul.categorie_entreprise or "").upper().strip()
    if cat == LeadSegment.GE.value:
        return LeadSegment.GE
    if cat == LeadSegment.ETI.value:
        return LeadSegment.ETI
    if cat == LeadSegment.PME.value:
        return LeadSegment.PME if n_etabs >= 3 else LeadSegment.TPE
    # Fallback si categorie absente
    if n_etabs >= 100:
        return LeadSegment.GE
    if n_etabs >= 10:
        return LeadSegment.ETI
    if n_etabs >= 3:
        return LeadSegment.PME
    return LeadSegment.TPE


def _resolve_naf_value_tier(naf: Optional[str]) -> NafValueTier:
    if not naf:
        return NafValueTier.UNKNOWN
    prefix = naf[:2]
    if prefix in _NAF_HIGH_VALUE_PREFIXES:
        return NafValueTier.HIGH
    if prefix in _NAF_MEDIUM_VALUE_PREFIXES:
        return NafValueTier.MEDIUM
    if prefix in _NAF_LOW_VALUE_PREFIXES:
        return NafValueTier.LOW
    return NafValueTier.UNKNOWN


def _resolve_priority(segment: LeadSegment, naf_tier: NafValueTier, n_etabs: int) -> LeadPriority:
    """Priorite commerciale A/B/C.

    A = deal chaud (GE/ETI + high NAF OU multi-site enterprise)
    B = deal tiede (PME multi-site OU ETI standard OU GE low)
    C = deal froid (TPE OU low NAF)
    """
    is_high = naf_tier == NafValueTier.HIGH
    is_high_or_medium = naf_tier in (NafValueTier.HIGH, NafValueTier.MEDIUM)

    if segment in (LeadSegment.GE, LeadSegment.ETI) and is_high:
        return LeadPriority.A
    if segment == LeadSegment.GE:
        return LeadPriority.A if n_etabs >= 20 else LeadPriority.B
    if segment == LeadSegment.ETI:
        return LeadPriority.A if (is_high_or_medium and n_etabs >= 10) else LeadPriority.B
    if segment == LeadSegment.PME:
        return LeadPriority.B if (is_high or n_etabs >= 5) else LeadPriority.C
    return LeadPriority.C  # TPE


# NAF value boost factors (PROMEOS willingness to pay par tier)
# Valeurs par defaut surchargeables via config/pricing_lead_score.yaml (V119.3)
_NAF_BOOST_DEFAULT = {
    NafValueTier.HIGH: 1.25,
    NafValueTier.MEDIUM: 1.0,
    NafValueTier.LOW: 0.75,
    NafValueTier.UNKNOWN: 1.0,
}


def compute_lead_score_from_loaded(ul: SireneUniteLegale, n_etabs_actifs: int) -> dict:
    """Calcule un lead score depuis une UL deja chargee + nb etablissements.

    Permet d'eviter des queries redondantes quand l'appelant a deja ces donnees
    (ex : onboarding_from_sirene qui a deja fetch l'UL et les etabs).
    """
    segment = _resolve_segment(ul, n_etabs_actifs)
    naf_tier = _resolve_naf_value_tier(ul.activite_principale)
    priority = _resolve_priority(segment, naf_tier, n_etabs_actifs)

    pricing = _load_pricing_config()
    base = pricing["base_mrr"][segment]
    boost = pricing["naf_boost"][naf_tier]
    mrr = int(base * _sites_multiplier(n_etabs_actifs) * boost)

    drivers = []
    if ul.categorie_entreprise:
        drivers.append(f"categorie INSEE: {ul.categorie_entreprise}")
    if ul.activite_principale:
        drivers.append(f"NAF: {ul.activite_principale} ({naf_tier.value}-value)")
    drivers.append(f"{n_etabs_actifs} etablissement(s) actif(s)")
    if ul.etat_administratif != "A":
        drivers.append(f"ATTENTION : etat={ul.etat_administratif} (non actif)")

    return {
        "siren": ul.siren,
        "segment": segment.value,
        "estimated_mrr_eur": mrr,
        "estimated_arr_eur": mrr * 12,
        "priority": priority.value,
        "n_etablissements_actifs": n_etabs_actifs,
        "naf_value_tier": naf_tier.value,
        "drivers": drivers,
    }


def compute_lead_score(db: Session, siren: str) -> dict:
    """Calcule un lead score depuis les donnees Sirene locales.

    Raise LookupError si le SIREN n'est pas present localement.
    Raise ValueError si le SIREN est mal forme.
    """
    siren = (siren or "").strip()
    if not siren.isdigit() or len(siren) != 9:
        raise ValueError(f"SIREN invalide : {siren}")

    ul = db.query(SireneUniteLegale).filter(SireneUniteLegale.siren == siren).first()
    if ul is None:
        raise LookupError(
            f"SIREN {siren} absent du referentiel local. Hydrate d'abord via sirene_hydrate.hydrate_siren_from_api()."
        )

    n_etabs_actifs = (
        db.query(SireneEtablissement)
        .filter(
            SireneEtablissement.siren == siren,
            SireneEtablissement.etat_administratif == "A",
        )
        .count()
    )

    return compute_lead_score_from_loaded(ul, n_etabs_actifs)
