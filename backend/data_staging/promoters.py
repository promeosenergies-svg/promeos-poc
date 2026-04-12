"""
SF5 — Promoters : conversion staging → tables fonctionnelles.

Chaque promoter traite un type de flux et produit des rows prêtes à UPSERT.
"""

import logging
from datetime import datetime, timedelta

from data_staging.quality import quality_r4x, quality_r50, quality_r171, quality_r151_pmax
from data_staging.models import MeterLoadCurve, MeterEnergyIndex, MeterPowerPeak
from utils.parsing import safe_float, parse_date, parse_iso_datetime

logger = logging.getLogger(__name__)


# ── R4x CDC → meter_load_curve ────────────────────────────────────────────


def promote_r4x_row(row, meter_id: int, run_id: int) -> MeterLoadCurve | None:
    """Convertit un EnedisFluxMesureR4x en MeterLoadCurve.

    row: instance SQLAlchemy de EnedisFluxMesureR4x
    """
    ts = parse_iso_datetime(row.horodatage)
    if ts is None:
        return None

    val = safe_float(row.valeur_point)
    if val is None:
        return None  # D7 : pas de zéro synthétique

    q_score, is_est = quality_r4x(row.statut_point)
    pas = int(row.granularite) if row.granularite else 10

    # Router selon grandeur_physique
    gp = (row.grandeur_physique or "").upper()
    mlc = MeterLoadCurve(
        meter_id=meter_id,
        timestamp=ts,
        pas_minutes=pas,
        quality_score=q_score,
        is_estimated=is_est,
        source_flux_type=row.flux_type or "R4X",
        promotion_run_id=run_id,
    )

    if gp in ("EA", "E", ""):
        mlc.active_power_kw = val
    elif gp == "ERI":
        mlc.reactive_inductive_kvar = val
    elif gp == "ERC":
        mlc.reactive_capacitive_kvar = val
    else:
        mlc.active_power_kw = val  # fallback

    return mlc


# ── R50 CDC → meter_load_curve ────────────────────────────────────────────


def promote_r50_row(row, meter_id: int, run_id: int) -> MeterLoadCurve | None:
    """Convertit un EnedisFluxMesureR50 en MeterLoadCurve.

    IMPORTANT: horodatage R50 = FIN de l'intervalle.
    On soustrait 30 min pour obtenir le DÉBUT canonique.
    Valeur brute en W → conversion kW.
    """
    ts_end = parse_iso_datetime(row.horodatage)
    if ts_end is None:
        return None

    ts_start = ts_end - timedelta(minutes=30)

    val_w = safe_float(row.valeur)
    if val_w is None:
        return None

    val_kw = val_w / 1000.0

    q_score, is_est = quality_r50(row.indice_vraisemblance)

    return MeterLoadCurve(
        meter_id=meter_id,
        timestamp=ts_start,
        pas_minutes=30,
        active_power_kw=val_kw,
        quality_score=q_score,
        is_estimated=is_est,
        source_flux_type="R50",
        promotion_run_id=run_id,
    )


# ── R171 Index → meter_energy_index ───────────────────────────────────────


def promote_r171_row(row, meter_id: int, run_id: int) -> MeterEnergyIndex | None:
    """Convertit un EnedisFluxMesureR171 en MeterEnergyIndex.

    Seuls grandeur_physique=EA + unite=Wh sont promotables.
    """
    gp = (row.grandeur_physique or "").upper()
    unite = (row.unite or "").lower()

    if gp != "EA" or unite != "wh":
        return None  # Reste dans staging brut

    val = safe_float(row.valeur)
    if val is None:
        return None

    date_r = parse_date(row.date_fin)
    if date_r is None:
        return None

    # Type calendrier : D → CT_DIST, F → CT
    type_cal = (row.type_calendrier or "").upper()
    tariff_grid = "CT_DIST" if type_cal == "D" else "CT"

    tariff_code = row.code_classe_temporelle or "TOTAL"
    tariff_label = row.libelle_classe_temporelle or ""

    q_score, is_est = quality_r171()

    return MeterEnergyIndex(
        meter_id=meter_id,
        date_releve=date_r,
        tariff_class_code=tariff_code,
        tariff_class_label=tariff_label,
        tariff_grid=tariff_grid,
        value_wh=val,
        quality_score=q_score,
        is_estimated=is_est,
        source_flux_type="R171",
        promotion_run_id=run_id,
    )


# ── R151 Index + PMAX → meter_energy_index / meter_power_peak ─────────────


def promote_r151_row(row, meter_id: int, run_id: int) -> MeterEnergyIndex | MeterPowerPeak | None:
    """Convertit un EnedisFluxMesureR151 selon type_donnee.

    CT/CT_DIST → MeterEnergyIndex
    PMAX → MeterPowerPeak
    """
    type_d = (row.type_donnee or "").upper()
    val = safe_float(row.valeur)
    if val is None:
        return None

    date_r = parse_date(row.date_releve)
    if date_r is None:
        return None

    if type_d == "PMAX":
        q_score, is_est = quality_r151_pmax()
        return MeterPowerPeak(
            meter_id=meter_id,
            date_releve=date_r,
            value_va=val,
            quality_score=q_score,
            is_estimated=is_est,
            source_flux_type="R151",
            promotion_run_id=run_id,
        )

    if type_d in ("CT", "CT_DIST"):
        tariff_code = row.id_classe_temporelle or "TOTAL"
        tariff_label = getattr(row, "libelle_classe_temporelle", "") or ""

        q_score, is_est = quality_r171()  # R151 CT/CT_DIST : même qualité par défaut que R171
        return MeterEnergyIndex(
            meter_id=meter_id,
            date_releve=date_r,
            tariff_class_code=tariff_code,
            tariff_class_label=tariff_label,
            tariff_grid=type_d,
            value_wh=val,
            quality_score=q_score,
            is_estimated=is_est,
            source_flux_type="R151",
            promotion_run_id=run_id,
        )

    return None


# Helpers safe_float, parse_date, parse_iso_datetime importés de utils.parsing
