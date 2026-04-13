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

from typing import Optional

from sqlalchemy.orm import Session

from models.sirene import SireneUniteLegale, SireneEtablissement


# ══════════════════════════════════════════════════════════════════════
# Grille pricing PROMEOS (calibree sur docs/ux_demo_strategy)
# 400-2000 EUR/mois documentee + extensions GE grandes flottes
# ══════════════════════════════════════════════════════════════════════

# Prix de base par segment (EUR/mois, base 1-5 sites)
_BASE_MRR = {
    "TPE": 200,  # <10 salaries, 1-2 sites
    "PME": 600,  # 10-250 salaries, 1-20 sites
    "ETI": 2000,  # 250-5000 salaries, 10-100 sites
    "GE": 6000,  # >5000 salaries, 100+ sites
}


# Multiplicateur par tranche d'etablissements
def _sites_multiplier(n_etabs: int) -> float:
    if n_etabs <= 5:
        return 1.0
    if n_etabs <= 20:
        return 1.8
    if n_etabs <= 100:
        return 3.5
    if n_etabs <= 500:
        return 6.0
    return 10.0  # >500 sites = enterprise deal


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


def _resolve_segment(ul: SireneUniteLegale, n_etabs: int) -> str:
    """Deduit le segment depuis categorie_entreprise INSEE (prioritaire)
    avec fallback sur le nombre d'etablissements."""
    cat = (ul.categorie_entreprise or "").upper().strip()
    if cat == "GE":
        return "GE"
    if cat == "ETI":
        return "ETI"
    if cat == "PME":
        return "PME" if n_etabs >= 3 else "TPE"
    # Fallback si categorie absente
    if n_etabs >= 100:
        return "GE"
    if n_etabs >= 10:
        return "ETI"
    if n_etabs >= 3:
        return "PME"
    return "TPE"


def _resolve_naf_value_tier(naf: Optional[str]) -> str:
    if not naf:
        return "unknown"
    prefix = naf[:2]
    if prefix in _NAF_HIGH_VALUE_PREFIXES:
        return "high"
    if prefix in _NAF_MEDIUM_VALUE_PREFIXES:
        return "medium"
    if prefix in _NAF_LOW_VALUE_PREFIXES:
        return "low"
    return "unknown"


def _resolve_priority(segment: str, naf_tier: str, n_etabs: int) -> str:
    """Priorite commerciale A/B/C.

    A = deal chaud (GE/ETI + high NAF OU multi-site enterprise)
    B = deal tiede (PME multi-site OU ETI standard OU GE low)
    C = deal froid (TPE OU low NAF)
    """
    if segment in ("GE", "ETI") and naf_tier == "high":
        return "A"
    if segment == "GE":
        return "A" if n_etabs >= 20 else "B"
    if segment == "ETI":
        return "A" if (naf_tier in ("high", "medium") and n_etabs >= 10) else "B"
    if segment == "PME":
        return "B" if (naf_tier == "high" or n_etabs >= 5) else "C"
    return "C"  # TPE


# NAF value boost factors (PROMEOS willingness to pay par tier)
_NAF_BOOST = {"high": 1.25, "medium": 1.0, "low": 0.75, "unknown": 1.0}


def compute_lead_score_from_loaded(ul: SireneUniteLegale, n_etabs_actifs: int) -> dict:
    """Calcule un lead score depuis une UL deja chargee + nb etablissements.

    Permet d'eviter des queries redondantes quand l'appelant a deja ces donnees
    (ex : onboarding_from_sirene qui a deja fetch l'UL et les etabs).
    """
    segment = _resolve_segment(ul, n_etabs_actifs)
    naf_tier = _resolve_naf_value_tier(ul.activite_principale)
    priority = _resolve_priority(segment, naf_tier, n_etabs_actifs)

    mrr = int(_BASE_MRR[segment] * _sites_multiplier(n_etabs_actifs) * _NAF_BOOST[naf_tier])

    drivers = []
    if ul.categorie_entreprise:
        drivers.append(f"categorie INSEE: {ul.categorie_entreprise}")
    if ul.activite_principale:
        drivers.append(f"NAF: {ul.activite_principale} ({naf_tier}-value)")
    drivers.append(f"{n_etabs_actifs} etablissement(s) actif(s)")
    if ul.etat_administratif != "A":
        drivers.append(f"ATTENTION : etat={ul.etat_administratif} (non actif)")

    return {
        "siren": ul.siren,
        "segment": segment,
        "estimated_mrr_eur": mrr,
        "estimated_arr_eur": mrr * 12,
        "priority": priority,
        "n_etablissements_actifs": n_etabs_actifs,
        "naf_value_tier": naf_tier,
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
