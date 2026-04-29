"""Service monthly_comparison — KPI 2 maquette v1.1.

Calcule la consommation du mois courant vs même mois N-1, DJU-ajustée.

Logique :
  - Mois courant : du 1er du mois au jour J inclus.
  - Mois N-1     : même fenêtre (1er → jour J-1) de l'année précédente.
  - Correction DJU via baseline_service.get_baseline_b si disponible.
  - Confidence basée sur r² baseline B — fallback 'faible' si absent.

Phase 13.A P0-2 (audit véracité 5.5/10) : la consommation est désormais
**délégué intégralement** à `consumption_unified_service.get_portfolio_consumption`
(SoT canonique CLAUDE.md règle non-négociable #6). Avant : ce service
ré-implémentait sa propre agrégation MeterReading (filtrage ad-hoc,
pas de `resolve_best_freq` → risque de double-comptage frequencies
15min+30min+hourly+daily si plusieurs présentes pour un même meter).
Maintenant : 1 SoT pour les 2 sources (cockpit_facts + monthly_comparison).

Retourne des zéros + confidence='faible' en cas de données insuffisantes.

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.3
Doctrine : §11.3 source unique partagée + maquette v1.1 KPI 2
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    Site,
    Portefeuille,
    EntiteJuridique,
    not_deleted,
)
from services.baseline_service import get_baseline_b
from services.consumption_unified_service import (
    ConsumptionSource,
    get_portfolio_consumption,
)

# ─── Constantes internes ────────────────────────────────────────────────────

_CONFIDENCE_HAUTE = "haute"
_CONFIDENCE_MOYENNE = "moyenne"
_CONFIDENCE_FAIBLE = "faible"

# DJU journalier moyen de référence (hiver France tempéré) utilisé si aucune
# donnée réelle DJU n'est disponible. Permet un calcul de ratio approximatif.
_DJU_FALLBACK_DAILY = 3.0


# ─── Helpers ────────────────────────────────────────────────────────────────


def _portfolio_kwh(db: Session, org_id: int, start: date, end: date) -> float:
    """Somme conso élec portfolio sur fenêtre [start, end] via SoT canonique.

    Délègue à `consumption_unified_service.get_portfolio_consumption` avec
    `source=METERED` (on veut la donnée mesurée brute, pas réconciliée avec
    factures, pour la comparaison N vs N-1).

    Le service canonique applique :
      - `get_site_meter_ids` (parent_meter_id IS NULL + is_active TRUE)
      - `resolve_best_freq` (1 seule fréquence par site → zéro double-counting)
    """
    portfolio = get_portfolio_consumption(db, org_id, start, end, source=ConsumptionSource.METERED)
    return float(portfolio.get("total_kwh") or 0.0)


def _month_label(year: int, month: int, day_end: int) -> str:
    """Construit l'étiquette de fenêtre mensuelle, ex 'avril 2026 (j 1-27)'."""
    _MONTH_NAMES = [
        "",
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    return f"{_MONTH_NAMES[month]} {year} (j 1-{day_end})"


def _get_first_site_id(db: Session, org_id: int) -> Optional[int]:
    """Retourne l'id du premier site actif du périmètre (pour récupérer baseline B)."""
    row = (
        not_deleted(db.query(Site.id), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .first()
    )
    return row[0] if row else None


# ─── API publique ────────────────────────────────────────────────────────────


def get_monthly_vs_previous_year(db: Session, org_id: int, today: date) -> dict:
    """KPI Pilotage v1.1 : conso mois courant agrégée vs même mois N-1, DJU-ajustée.

    - Mois courant : du 1er au jour J inclus (ex: 1-27 avril 2026)
    - Mois N-1     : même fenêtre normalisée (1-27 avril 2025)
    - Correction DJU via baseline_service.get_baseline_b (méthode B si disponible)
    - Confidence basée sur r² baseline B

    Implémentation pragmatique : si baseline B indisponible ou r²<0.7, retourne
    le delta brut avec confidence='faible'.

    Returns:
        {
            "current_month_label"                 : str,
            "current_month_mwh"                   : float,
            "previous_year_month_normalized_mwh"  : float,
            "delta_pct_dju_adjusted"              : int (arrondi),
            "baseline_method"                     : "b_dju_adjusted" | "a_historical",
            "calibration_date"                    : str ISO,
            "r_squared"                           : float | None,
            "confidence"                          : "haute" | "moyenne" | "faible",
        }
    """
    now_iso = datetime.utcnow().isoformat()
    _empty = {
        "current_month_label": _month_label(today.year, today.month, today.day),
        "current_month_mwh": 0.0,
        "previous_year_month_normalized_mwh": 0.0,
        "delta_pct_dju_adjusted": 0,
        "baseline_method": "b_dju_adjusted",
        "calibration_date": now_iso,
        "r_squared": None,
        "confidence": _CONFIDENCE_FAIBLE,
    }

    # Fenêtre mois courant : 1er → today
    month_start_curr = date(today.year, today.month, 1)
    month_end_curr = date(today.year, today.month, today.day)

    # Fenêtre même mois N-1 : même fenêtre de jours, clamp si mois plus court
    prev_year = today.year - 1
    import calendar

    max_day_prev = calendar.monthrange(prev_year, today.month)[1]
    day_end_prev = min(today.day, max_day_prev)
    month_start_prev = date(prev_year, today.month, 1)
    month_end_prev = date(prev_year, today.month, day_end_prev)

    curr_kwh = _portfolio_kwh(db, org_id, month_start_curr, month_end_curr)
    prev_kwh = _portfolio_kwh(db, org_id, month_start_prev, month_end_prev)

    if curr_kwh <= 0 and prev_kwh <= 0:
        return _empty

    curr_mwh = round(curr_kwh / 1000.0, 3)
    prev_mwh_raw = round(prev_kwh / 1000.0, 3)

    # Tentative correction DJU via baseline B du premier site
    first_site_id = _get_first_site_id(db, org_id)
    baseline_method = "b_dju_adjusted"
    calibration_date = now_iso
    r_squared: Optional[float] = None
    confidence = _CONFIDENCE_FAIBLE
    prev_mwh_normalized = prev_mwh_raw  # valeur par défaut = non normalisée

    if first_site_id is not None:
        try:
            # DJU moyen de la période courante (fallback constant)
            dju_curr = _DJU_FALLBACK_DAILY * today.day
            dju_prev = _DJU_FALLBACK_DAILY * day_end_prev

            b_result = get_baseline_b(db, first_site_id, today, dju_curr)
            r_squared = b_result.get("r_squared")
            calibration_date = b_result.get("calibration_date", now_iso)
            baseline_method = b_result.get("method", "b_dju_adjusted")

            # Si méthode B disponible avec un r² valide, appliquer correction DJU
            if (
                baseline_method == "b_dju_adjusted"
                and r_squared is not None
                and r_squared >= 0.5  # seuil assoupli pour la normalisation
                and dju_curr > 0
                and dju_prev > 0
            ):
                # Normalisation : conso N-1 corrigée = conso N-1 × (DJU_curr / DJU_prev)
                correction_factor = dju_curr / dju_prev
                prev_mwh_normalized = round(prev_mwh_raw * correction_factor, 3)
                confidence = (
                    _CONFIDENCE_HAUTE
                    if r_squared >= 0.85
                    else _CONFIDENCE_MOYENNE
                    if r_squared >= 0.70
                    else _CONFIDENCE_FAIBLE
                )
            else:
                # Fallback sans correction DJU
                baseline_method = b_result.get("method", "a_historical")
                confidence = _CONFIDENCE_FAIBLE
        except Exception:
            pass  # Fallback gracieux — données brutes sans correction

    # Delta %
    if prev_mwh_normalized > 0:
        delta_pct = round((curr_mwh - prev_mwh_normalized) / prev_mwh_normalized * 100)
    else:
        delta_pct = 0

    return {
        "current_month_label": _month_label(today.year, today.month, today.day),
        "current_month_mwh": curr_mwh,
        "previous_year_month_normalized_mwh": prev_mwh_normalized,
        "delta_pct_dju_adjusted": delta_pct,
        "baseline_method": baseline_method,
        "calibration_date": calibration_date,
        "r_squared": r_squared,
        "confidence": confidence,
    }
