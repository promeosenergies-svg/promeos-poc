"""
PROMEOS — Tarif Loader (Step 18)
Charge le référentiel tarifs_reglementaires.yaml avec @lru_cache.
Fournit des helpers typés pour shadow billing et audit.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

_YAML_PATH = Path(__file__).resolve().parent / "tarifs_reglementaires.yaml"


@lru_cache(maxsize=1)
def load_tarifs() -> dict:
    """Load and cache the YAML referentiel."""
    return yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))


def reload_tarifs() -> dict:
    """Force reload (tests, hot-patch)."""
    load_tarifs.cache_clear()
    return load_tarifs()


# ── TURPE helpers ────────────────────────────────────────────────────────────


def get_turpe_segment(segment: str = "C5_BT") -> dict:
    """Return TURPE segment dict (energie_eur_kwh, gestion_eur_mois, label)."""
    tarifs = load_tarifs()
    segments = tarifs["turpe"]["segments"]
    if segment not in segments:
        raise KeyError(f"TURPE segment inconnu : {segment}. Disponibles : {list(segments.keys())}")
    return segments[segment]


def get_turpe_moyen_kwh(segment: str = "C5_BT") -> float:
    """TURPE énergie en EUR/kWh pour un segment donné."""
    return get_turpe_segment(segment)["energie_eur_kwh"]


def get_turpe_gestion_mois(segment: str = "C5_BT") -> float:
    """TURPE gestion en EUR/mois pour un segment donné."""
    return get_turpe_segment(segment)["gestion_eur_mois"]


# ── Accise helpers ───────────────────────────────────────────────────────────


def get_accise_kwh(energy_type: str = "elec") -> float:
    """Accise en EUR/kWh (elec ou gaz)."""
    tarifs = load_tarifs()
    if energy_type == "elec":
        return tarifs["accise_elec"]["rate_eur_kwh"]
    elif energy_type == "gaz":
        return tarifs["accise_gaz"]["rate_eur_kwh"]
    raise ValueError(f"energy_type inconnu : {energy_type}")


# ── CTA helpers ──────────────────────────────────────────────────────────────


def get_cta_taux(energy_type: str = "elec", at_date=None) -> float:
    """
    CTA en pourcentage (ex : 15.0 pour élec dist fév 2026+, 20.80 pour gaz).

    V112 : désormais versionné par `at_date` via ParameterStore — avant le
    1/02/2026 la CTA élec distribution était à 21,93%. La signature reste
    rétrocompatible : `at_date=None` utilise la date du jour.
    """
    try:
        from datetime import date as _date

        from services.billing_engine.parameter_store import ParameterStore

        store = ParameterStore(db=None)
        code = "CTA_ELEC_DIST_RATE" if energy_type == "elec" else "CTA_GAZ_DIST_RATE"
        ref_date = at_date if at_date else _date.today()
        res = store.get(code, at_date=ref_date)
        if res.source in ("db", "yaml"):
            return res.value * 100.0  # ratio → pourcentage
    except Exception:
        pass

    # Dernier recours : lecture directe du YAML (compat)
    tarifs = load_tarifs()
    return tarifs["cta"][energy_type]["taux_pct"]


# ── TICGN / ATRD / ATRT ─────────────────────────────────────────────────────


def get_ticgn_kwh() -> float:
    """TICGN (accise gaz) en EUR/kWh."""
    return load_tarifs()["ticgn"]["rate_eur_kwh"]


def get_atrd_kwh() -> float:
    """ATRD gaz distribution en EUR/kWh."""
    return load_tarifs()["atrd_gaz"]["rate_eur_kwh"]


def get_atrt_kwh() -> float:
    """ATRT gaz transport en EUR/kWh."""
    return load_tarifs()["atrt_gaz"]["rate_eur_kwh"]


# ── TVA ──────────────────────────────────────────────────────────────────────


def get_tva_normale() -> float:
    """TVA taux normal (0.20)."""
    return load_tarifs()["tva"]["normale"]["taux"]


def get_tva_reduite(at_date=None) -> float:
    """TVA taux réduit (0.055 avant août 2025, 0.20 après — suppression LFI 2025)."""
    from datetime import date

    ref = at_date or date.today()
    if isinstance(ref, date):
        supprime = date(2025, 8, 1)
        if ref >= supprime:
            return load_tarifs()["tva"]["normale"]["taux"]  # 0.20 uniforme
    return load_tarifs()["tva"]["reduite"]["taux"]


# ── Prix de référence ────────────────────────────────────────────────────────


def get_prix_reference(energy_type: str = "elec") -> float:
    """Prix de référence par défaut en EUR/kWh."""
    tarifs = load_tarifs()
    if energy_type == "elec":
        return tarifs["prix_reference"]["elec_eur_kwh"]
    return tarifs["prix_reference"]["gaz_eur_kwh"]


# ── Version & meta ───────────────────────────────────────────────────────────


def get_tarif_version() -> str:
    """Version string du référentiel."""
    return load_tarifs()["version"]


def get_tarif_summary() -> dict:
    """Summary dict for the /api/referentiel/tarifs endpoint."""
    tarifs = load_tarifs()
    return {
        "version": tarifs["version"],
        "description": tarifs.get("description", ""),
        "turpe": {
            seg_key: {
                "label": seg_val["label"],
                "energie_eur_kwh": seg_val["energie_eur_kwh"],
                "gestion_eur_mois": seg_val["gestion_eur_mois"],
            }
            for seg_key, seg_val in tarifs["turpe"]["segments"].items()
        },
        "turpe_source": tarifs["turpe"]["source"],
        "turpe_valid_from": tarifs["turpe"]["valid_from"],
        "accise_elec": {
            "rate_eur_kwh": tarifs["accise_elec"]["rate_eur_kwh"],
            "source": tarifs["accise_elec"]["source"],
            "valid_from": tarifs["accise_elec"]["valid_from"],
        },
        "accise_gaz": {
            "rate_eur_kwh": tarifs["accise_gaz"]["rate_eur_kwh"],
            "source": tarifs["accise_gaz"]["source"],
            "valid_from": tarifs["accise_gaz"]["valid_from"],
        },
        "cta_elec_pct": tarifs["cta"]["elec"]["taux_pct"],
        "cta_gaz_pct": tarifs["cta"]["gaz"]["taux_pct"],
        "tva_normale": tarifs["tva"]["normale"]["taux"],
        "tva_reduite": tarifs["tva"]["reduite"]["taux"],
        "prix_reference": tarifs["prix_reference"],
    }
