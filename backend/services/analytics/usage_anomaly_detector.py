"""
Detecteur d'anomalies par usage.

Croise la decomposition CDC (etage 1) avec les seuils contextuels par archetype
pour produire des anomalies actionnables : "votre CVC tourne 24/7 mais vous etes
un bureau 8h-20h -> 8200 EUR/an recuperables".

Chaque anomalie a :
- usage concerne (CVC_HVAC, ECLAIRAGE, ECS, FROID, etc.)
- type d'anomalie (USAGE_NUIT_EXCESSIF, USAGE_WEEKEND_EXCESSIF, USAGE_SURDIMENSIONNE, etc.)
- gain estime (kWh/an, EUR/an)
- action recommandee
- confiance (high/medium/low)

Sources seuils : archetypes_energy_v1.json (anomaly_thresholds + temporal_signature)
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Prix moyen electricite (EUR/kWh) pour estimation gains
PRIX_MOY_EUR_KWH = 0.18


@dataclass
class UsageAnomaly:
    """Une anomalie detectee sur un usage specifique."""

    usage_code: str
    usage_label: str
    anomaly_type: str
    severity: str  # critical | high | medium | low
    message: str
    detail: str
    gain_kwh_an: float
    gain_eur_an: float
    action: str
    confidence: str  # high | medium | low
    metric_observed: float
    metric_threshold: float


@dataclass
class UsageAnomalyResult:
    site_id: int
    archetype_code: str
    n_anomalies: int
    total_gain_eur_an: float
    anomalies: list[UsageAnomaly]
    period_start: str
    period_end: str
    method: str = "usage_x_archetype_thresholds"


def detect_usage_anomalies(
    db: Session,
    site_id: int,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    disagg_result=None,
) -> UsageAnomalyResult:
    """
    Detecte les anomalies par usage en croisant :
    1. Le breakdown CDC du site (disaggregate_site)
    2. Les seuils contextuels de l'archetype (anomaly_thresholds)
    3. Le profil temporel mesure (baseload nuit, weekend ratio)

    Args:
        disagg_result: optionnel — si fourni, reutilise cette decomposition
            au lieu de recalculer (evite la double lecture CDC).
    """
    if date_fin is None:
        date_fin = date.today()
    if date_debut is None:
        date_debut = date_fin - timedelta(days=365)

    # 1. Decomposer la CDC en usages (reutilise si deja calcule)
    if disagg_result is not None:
        disagg = disagg_result
    else:
        from services.analytics.usage_disaggregation import disaggregate_site

        disagg = disaggregate_site(db, site_id, date_debut, date_fin)
    archetype = disagg.archetype_code
    total_kwh = disagg.total_kwh

    if total_kwh <= 0 or not disagg.usages:
        return UsageAnomalyResult(
            site_id=site_id,
            archetype_code=archetype,
            n_anomalies=0,
            total_gain_eur_an=0,
            anomalies=[],
            period_start=date_debut.isoformat(),
            period_end=date_fin.isoformat(),
        )

    # 2. Charger les seuils contextuels de l'archetype
    thresholds = _load_archetype_thresholds(archetype)
    temporal_sig = _load_archetype_temporal(archetype)

    # 3. Profil temporel observe (depuis le disagg)
    temporal = disagg.temporal_profile or {}
    thermal = disagg.thermal_signature or {}

    # 4. Lancer les detecteurs
    anomalies: list[UsageAnomaly] = []

    # Breakdown indexe par code
    usage_by_code = {u.code: u for u in disagg.usages}

    # === Detecteur 1 : CVC 24/7 sur un site non-24/7 ===
    cvc = usage_by_code.get("CVC_HVAC")
    if cvc and cvc.pct > 20:
        night_base_ratio = _compute_night_base_ratio(temporal)
        threshold_night = thresholds.get("ANOM_BASE_NUIT_ELEVEE", 0.20)
        if night_base_ratio > threshold_night:
            excess_pct = night_base_ratio - threshold_night
            excess_kwh = round(total_kwh * excess_pct, 0)
            anomalies.append(
                UsageAnomaly(
                    usage_code="CVC_HVAC",
                    usage_label=cvc.label,
                    anomaly_type="CVC_NUIT_EXCESSIF",
                    severity="high" if excess_kwh > 10000 else "medium",
                    message=f"CVC active la nuit : {night_base_ratio:.0%} du talon vs {threshold_night:.0%} attendu",
                    detail=(
                        f"Le ratio baseload nuit ({night_base_ratio:.1%}) depasse le seuil archetype "
                        f"({threshold_night:.0%}). La CVC semble tourner en dehors des heures d'occupation."
                    ),
                    gain_kwh_an=excess_kwh,
                    gain_eur_an=round(excess_kwh * PRIX_MOY_EUR_KWH, 0),
                    action="Programmer l'arret CVC 1h avant fermeture et le redemarrage 30min avant ouverture (inertie thermique).",
                    confidence="high" if disagg.confidence_global != "low" else "medium",
                    metric_observed=round(night_base_ratio, 3),
                    metric_threshold=threshold_night,
                )
            )

    # === Detecteur 2 : Consommation weekend excessive ===
    weekend_ratio = _compute_weekend_ratio(temporal)
    threshold_weekend = thresholds.get("ANOM_WEEKEND_ELEVE", 0.25)
    if weekend_ratio > threshold_weekend:
        excess_pct = weekend_ratio - threshold_weekend
        excess_kwh = round(total_kwh * excess_pct * (104 / 365), 0)  # 104 jours weekend/an
        dominant_usage = max(disagg.usages, key=lambda u: u.kwh)
        anomalies.append(
            UsageAnomaly(
                usage_code=dominant_usage.code,
                usage_label=dominant_usage.label,
                anomaly_type="WEEKEND_EXCESSIF",
                severity="medium",
                message=f"Consommation weekend {weekend_ratio:.0%} vs {threshold_weekend:.0%} attendu",
                detail=(
                    f"Le ratio weekend/semaine ({weekend_ratio:.1%}) depasse le seuil archetype "
                    f"({threshold_weekend:.0%}). Des equipements restent actifs le weekend inutilement."
                ),
                gain_kwh_an=excess_kwh,
                gain_eur_an=round(excess_kwh * PRIX_MOY_EUR_KWH, 0),
                action="Couper les usages non essentiels le weekend (eclairage, CVC, bureautique).",
                confidence="medium",
                metric_observed=round(weekend_ratio, 3),
                metric_threshold=threshold_weekend,
            )
        )

    # === Detecteur 3 : Eclairage hors horaires ===
    eclairage = usage_by_code.get("ECLAIRAGE")
    if eclairage and eclairage.pct > 10:
        baseload_kw = temporal.get("baseload_kw", 0)
        biz_mean_kw = temporal.get("biz_mean_kw", 0)
        if biz_mean_kw > 0:
            night_to_day_ratio = baseload_kw / biz_mean_kw
            # Si le baseload nuit est > 30% du jour, l'eclairage reste allume
            if night_to_day_ratio > 0.30:
                excess_kwh = round(eclairage.kwh * (night_to_day_ratio - 0.15) * 0.5, 0)
                if excess_kwh > 500:
                    anomalies.append(
                        UsageAnomaly(
                            usage_code="ECLAIRAGE",
                            usage_label=eclairage.label,
                            anomaly_type="ECLAIRAGE_NUIT",
                            severity="medium",
                            message=f"Eclairage probablement actif la nuit (ratio nuit/jour {night_to_day_ratio:.0%})",
                            detail=(
                                f"Le ratio baseload nuit / conso jour ({night_to_day_ratio:.1%}) "
                                "suggere que l'eclairage n'est pas eteint completement la nuit."
                            ),
                            gain_kwh_an=excess_kwh,
                            gain_eur_an=round(excess_kwh * PRIX_MOY_EUR_KWH, 0),
                            action="Installer des detecteurs de presence ou une horloge sur l'eclairage.",
                            confidence="medium",
                            metric_observed=round(night_to_day_ratio, 3),
                            metric_threshold=0.30,
                        )
                    )

    # === Detecteur 4 : CVC surdimensionnee (faible R2 DJU) ===
    if cvc and cvc.pct > 25:
        r2 = thermal.get("r2", 1.0)
        if r2 < 0.3 and cvc.pct > 30:
            anomalies.append(
                UsageAnomaly(
                    usage_code="CVC_HVAC",
                    usage_label=cvc.label,
                    anomaly_type="CVC_FAIBLE_CORRELATION_DJU",
                    severity="low",
                    message=f"CVC {cvc.pct:.0f}% de la conso mais faible correlation DJU (R2={r2:.2f})",
                    detail=(
                        f"La signature energetique montre un R2={r2:.2f}. La CVC represente {cvc.pct:.0f}% "
                        "mais ne suit pas la temperature exterieure — possible surdimensionnement ou "
                        "equipement tournant en permanence."
                    ),
                    gain_kwh_an=round(cvc.kwh * 0.15, 0),
                    gain_eur_an=round(cvc.kwh * 0.15 * PRIX_MOY_EUR_KWH, 0),
                    action="Verifier le dimensionnement CVC et les consignes de temperature.",
                    confidence="low",
                    metric_observed=round(r2, 3),
                    metric_threshold=0.30,
                )
            )

    # === Detecteur 5 : ECS en heures de pointe au lieu de HC ===
    ecs = usage_by_code.get("ECS")
    if ecs and ecs.kwh > 0 and ecs.pct > 3:
        # Si l'ECS a plus de kwh_hp que kwh_hc, elle tourne en HP (suboptimal)
        # On utilise la proportion du breakdown disagg si dispo
        # Sinon heuristique : ECS d'un bureau devrait etre 100% HC
        expected_hc_pct = 0.70 if archetype in ("BUREAU_STANDARD", "ENSEIGNEMENT", "COLLECTIVITE") else 0.50
        potential_shift_kwh = round(ecs.kwh * (1 - expected_hc_pct) * 0.6, 0)
        if potential_shift_kwh > 200:
            anomalies.append(
                UsageAnomaly(
                    usage_code="ECS",
                    usage_label=ecs.label,
                    anomaly_type="ECS_HP_AU_LIEU_HC",
                    severity="medium" if potential_shift_kwh > 1000 else "low",
                    message=f"ECS potentiellement en heures pleines ({ecs.pct:.0f}% de la conso)",
                    detail=(
                        f"L'ECS ({ecs.kwh:.0f} kWh/an) pourrait etre decalee en heures creuses "
                        "ou en heures solaires 11h-14h (CRE delib. 2026-33) pour reduire le cout."
                    ),
                    gain_kwh_an=0,
                    gain_eur_an=round(potential_shift_kwh * 0.05, 0),  # delta prix HP-HC ~0.05 EUR/kWh
                    action="Programmer le ballon ECS en heures creuses ou heures solaires 11h-14h.",
                    confidence="low",
                    metric_observed=ecs.pct,
                    metric_threshold=expected_hc_pct * 100,
                )
            )

    # === Detecteur 6 : Intensite energetique (kWh/m2) hors norme ===
    site_surface = _get_site_surface(db, site_id)
    if site_surface and site_surface > 0:
        intensity = total_kwh / site_surface
        threshold_low = thresholds.get("ANOM_RATIO_M2_P10", 100)
        threshold_high = thresholds.get("ANOM_RATIO_M2_P90", 300)
        if intensity > threshold_high:
            excess_kwh = round((intensity - threshold_high) * site_surface, 0)
            anomalies.append(
                UsageAnomaly(
                    usage_code="GLOBAL",
                    usage_label="Consommation globale",
                    anomaly_type="INTENSITE_ENERGETIQUE_ELEVEE",
                    severity="high" if intensity > threshold_high * 1.5 else "medium",
                    message=f"Intensite {intensity:.0f} kWh/m2/an vs plafond {threshold_high} kWh/m2 (P90 archetype)",
                    detail=(
                        f"L'intensite energetique ({intensity:.0f} kWh/m2/an) depasse le P90 "
                        f"de l'archetype ({threshold_high} kWh/m2). Surplus : {excess_kwh:,.0f} kWh/an."
                    ),
                    gain_kwh_an=excess_kwh,
                    gain_eur_an=round(excess_kwh * PRIX_MOY_EUR_KWH, 0),
                    action="Realiser un audit energetique pour identifier les postes de surconsommation.",
                    confidence="medium",
                    metric_observed=round(intensity, 1),
                    metric_threshold=threshold_high,
                )
            )

    # Trier par gain EUR decroissant
    anomalies.sort(key=lambda a: -a.gain_eur_an)

    return UsageAnomalyResult(
        site_id=site_id,
        archetype_code=archetype,
        n_anomalies=len(anomalies),
        total_gain_eur_an=round(sum(a.gain_eur_an for a in anomalies), 0),
        anomalies=anomalies,
        period_start=date_debut.isoformat(),
        period_end=date_fin.isoformat(),
    )


# === Helpers ===


def _compute_night_base_ratio(temporal: dict) -> float:
    """Ratio baseload nuit / moyenne business hours."""
    baseload = temporal.get("baseload_kw", 0)
    biz_mean = temporal.get("biz_mean_kw", 1)
    return baseload / biz_mean if biz_mean > 0 else 0


def _compute_weekend_ratio(temporal: dict) -> float:
    """Ratio consommation off-hours / business hours."""
    off_mean = temporal.get("off_mean_kw", 0)
    biz_mean = temporal.get("biz_mean_kw", 1)
    return off_mean / biz_mean if biz_mean > 0 else 0


def _get_site_surface(db: Session, site_id: int) -> Optional[float]:
    try:
        from models.site import Site

        site = db.query(Site).filter(Site.id == site_id).first()
        return site.surface_m2 if site else None
    except Exception:
        return None


def _load_archetype_thresholds(archetype_code: str) -> dict:
    """Charge anomaly_thresholds depuis archetypes_energy_v1.json."""
    data = _load_archetype_data(archetype_code)
    return data.get("anomaly_thresholds", {})


def _load_archetype_temporal(archetype_code: str) -> dict:
    """Charge temporal_signature depuis archetypes_energy_v1.json."""
    data = _load_archetype_data(archetype_code)
    return data.get("temporal_signature", {})


_ARCHETYPE_CACHE: dict[str, dict] = {}


def _load_archetype_data(archetype_code: str) -> dict:
    """Charge les donnees d'un archetype depuis le JSON (cache en memoire)."""
    if archetype_code in _ARCHETYPE_CACHE:
        return _ARCHETYPE_CACHE[archetype_code]

    try:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        path = os.path.join(base, "docs", "base_documentaire", "naf_archetype_mapping", "archetypes_energy_v1.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for arch in data.get("archetypes", []):
            _ARCHETYPE_CACHE[arch["code"]] = arch
    except Exception as exc:
        logger.debug("archetype data load failed: %s", exc)
        return {}

    return _ARCHETYPE_CACHE.get(archetype_code, {})
