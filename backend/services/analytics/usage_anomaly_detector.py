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

    # === Detecteur 7 : Simultaneite chaud/froid (conflit thermostat) ===
    if cvc and cvc.pct > 20:
        # Heuristique : si baseload nuit ET biz_mean sont tous deux eleves
        # et que la signature DJU montre a_heating ET b_cooling significatifs
        a_heating = thermal.get("a_heating", 0) or 0
        b_cooling = thermal.get("b_cooling", 0) or 0
        if a_heating > 5 and b_cooling > 5:
            waste_kwh = round(min(a_heating, b_cooling) * 30 * 0.3, 0)  # ~30 jours x 0.3 kWh/degre
            if waste_kwh > 500:
                anomalies.append(
                    UsageAnomaly(
                        usage_code="CVC_HVAC",
                        usage_label=cvc.label,
                        anomaly_type="SIMULTANEITE_CHAUD_FROID",
                        severity="medium",
                        message=f"Conflit chaud/froid detecte (chauffage {a_heating:.0f} + clim {b_cooling:.0f} kWh/DJU)",
                        detail="La signature DJU montre des composantes chauffage ET climatisation significatives. "
                        "Possible conflit de consignes entre zones ou thermostat antagoniste.",
                        gain_kwh_an=waste_kwh,
                        gain_eur_an=round(waste_kwh * PRIX_MOY_EUR_KWH, 0),
                        action="Verifier les consignes par zone, separer les circuits chaud/froid, calibrer la bande morte.",
                        confidence="medium",
                        metric_observed=round(b_cooling, 1),
                        metric_threshold=5.0,
                    )
                )

    # === Detecteur 8 : Depassement puissance souscrite ===
    ps_kva = _get_site_ps_kva(db, site_id)
    if ps_kva and ps_kva > 0 and temporal.get("biz_mean_kw", 0) > 0:
        peak_kw = temporal.get("biz_mean_kw", 0) * 1.5  # estimation pic = 1.5x moyen
        ratio_ps = peak_kw / (ps_kva * 0.8)  # cos phi 0.8
        if ratio_ps > 0.90:
            anomalies.append(
                UsageAnomaly(
                    usage_code="GLOBAL",
                    usage_label="Puissance souscrite",
                    anomaly_type="DEPASSEMENT_PS_RISQUE",
                    severity="high" if ratio_ps > 0.95 else "medium",
                    message=f"Pic estime {peak_kw:.0f} kW vs PS {ps_kva:.0f} kVA ({ratio_ps:.0%} utilisation)",
                    detail="Le pic de puissance estime approche la puissance souscrite. "
                    "Risque de depassement (penalites TURPE) ou disjonction.",
                    gain_kwh_an=0,
                    gain_eur_an=round(ps_kva * 12.65 * 0.1, 0),  # CMDPS ~12.65 EUR/kW
                    action="Decaler les demarrages d'equipements lourds. Evaluer un ecretage ou une augmentation de PS.",
                    confidence="medium",
                    metric_observed=round(ratio_ps, 3),
                    metric_threshold=0.90,
                )
            )

    # === Detecteur 9 : Air comprime fuites (baseload nuit process) ===
    air = usage_by_code.get("AIR_COMPRIME")
    if air and air.pct > 5:
        # Air comprime nuit devrait etre ~0 si process arrete
        if temporal.get("baseload_kw", 0) > 0 and temporal.get("biz_mean_kw", 0) > 0:
            air_night_ratio = temporal["baseload_kw"] / temporal["biz_mean_kw"]
            if air_night_ratio > 0.40 and archetype in ("INDUSTRIE_LEGERE", "INDUSTRIE_LOURDE", "LOGISTIQUE_SEC"):
                fuite_kwh = round(air.kwh * 0.25, 0)  # 25% fuites typique ADEME
                anomalies.append(
                    UsageAnomaly(
                        usage_code="AIR_COMPRIME",
                        usage_label=air.label,
                        anomaly_type="AIR_COMPRIME_FUITES",
                        severity="medium",
                        message=f"Fuites air comprime probables ({air.pct:.0f}% conso, baseload nuit {air_night_ratio:.0%})",
                        detail="Le baseload nuit eleve suggere que le compresseur tourne pour compenser des fuites. "
                        "Les fuites representent 20-30% de la conso air comprime (ADEME).",
                        gain_kwh_an=fuite_kwh,
                        gain_eur_an=round(fuite_kwh * PRIX_MOY_EUR_KWH, 0),
                        action="Detection ultrasonore des fuites + reparation. CEE IND-UT-114 eligible.",
                        confidence="medium",
                        metric_observed=round(air_night_ratio, 3),
                        metric_threshold=0.40,
                    )
                )

    # === Detecteur 10 : Derive long terme (+5%/an sans raison) ===
    if thermal and thermal.get("r2", 0) > 0.3:
        # Si la signature montre une base qui augmente d'annee en annee
        # On utilise la base comme proxy de derive (hors DJU)
        base_daily = thermal.get("base_kwh", 0)
        if base_daily > 0 and total_kwh > 0:
            base_annual = base_daily * 365
            base_pct = base_annual / total_kwh
            # Si la base represente > 70% du total, le site est "flat" = derive probable
            if base_pct > 0.70:
                derive_kwh = round(total_kwh * 0.05, 0)  # 5% derive estimee
                anomalies.append(
                    UsageAnomaly(
                        usage_code="GLOBAL",
                        usage_label="Tendance long terme",
                        anomaly_type="DERIVE_LONG_TERME",
                        severity="low",
                        message=f"Consommation de base {base_pct:.0%} du total — faible sensibilite DJU",
                        detail="La consommation est dominee par la base (non thermosensible). "
                        "Une derive de +5%/an est courante (vieillissement equipements, ajout de charges).",
                        gain_kwh_an=derive_kwh,
                        gain_eur_an=round(derive_kwh * PRIX_MOY_EUR_KWH, 0),
                        action="Planifier un audit preventif pour identifier les postes en derive.",
                        confidence="low",
                        metric_observed=round(base_pct, 3),
                        metric_threshold=0.70,
                    )
                )

    # === Detecteur 11 : Ventilation parking 24/7 (bailleurs, collectivites) ===
    pompes = usage_by_code.get("POMPES")
    if pompes and pompes.pct > 5 and archetype in ("COPROPRIETE", "COLLECTIVITE", "COMMERCE_ALIMENTAIRE"):
        if temporal.get("baseload_kw", 0) > 0 and temporal.get("biz_mean_kw", 0) > 0:
            vent_ratio = temporal["baseload_kw"] / temporal["biz_mean_kw"]
            if vent_ratio > 0.80:  # ventilation tourne quasi 100% nuit comme jour
                vent_kwh = round(pompes.kwh * 0.65, 0)  # 65% recuperable avec hygrostat CO
                anomalies.append(
                    UsageAnomaly(
                        usage_code="POMPES",
                        usage_label="Ventilation parking / VMC",
                        anomaly_type="VENTILATION_24_7",
                        severity="medium",
                        message=f"Ventilation probablement 24/7 sans regulation CO (ratio nuit/jour {vent_ratio:.0%})",
                        detail="La ventilation fonctionne a debit constant jour et nuit. "
                        "Installation d'un hygrostat CO = reduction 65-75% (payback 1-2 ans).",
                        gain_kwh_an=vent_kwh,
                        gain_eur_an=round(vent_kwh * PRIX_MOY_EUR_KWH, 0),
                        action="Installer detecteur CO + variateur sur extracteur parking.",
                        confidence="medium",
                        metric_observed=round(vent_ratio, 3),
                        metric_threshold=0.80,
                    )
                )

    # === Detecteur 12 : Process nuit = jour (industrie) ===
    process = usage_by_code.get("PROCESS_BATCH") or usage_by_code.get("PROCESS_CONTINU")
    if process and process.pct > 15 and archetype in ("INDUSTRIE_LEGERE", "INDUSTRIE_LOURDE"):
        if temporal.get("baseload_kw", 0) > 0 and temporal.get("biz_mean_kw", 0) > 0:
            process_night_ratio = temporal["baseload_kw"] / temporal["biz_mean_kw"]
            if process_night_ratio > 0.80 and archetype == "INDUSTRIE_LEGERE":
                waste_kwh = round(process.kwh * (process_night_ratio - 0.3) * 0.5, 0)
                if waste_kwh > 1000:
                    anomalies.append(
                        UsageAnomaly(
                            usage_code=process.code,
                            usage_label=process.label,
                            anomaly_type="PROCESS_NUIT_EGAL_JOUR",
                            severity="high",
                            message=f"Process nuit = jour ({process_night_ratio:.0%}) sur industrie legere",
                            detail="Le ratio nuit/jour suggere que des equipements de production restent en marche "
                            "la nuit alors que l'activite est reduite. Compresseurs, pompes ou convoyeurs oublies.",
                            gain_kwh_an=waste_kwh,
                            gain_eur_an=round(waste_kwh * PRIX_MOY_EUR_KWH, 0),
                            action="Audit production : programmer arret equipements non critiques quart 3 et weekend.",
                            confidence="medium",
                            metric_observed=round(process_night_ratio, 3),
                            metric_threshold=0.80,
                        )
                    )

    # === Detecteur 13 : Froid degradation progressive (maintenance) ===
    froid = usage_by_code.get("FROID_COMMERCIAL") or usage_by_code.get("FROID_INDUSTRIEL")
    if froid and froid.pct > 10:
        # Froid qui represente > seuil archetype = possible encrassement condenseurs
        froid_threshold_pct = {"COMMERCE_ALIMENTAIRE": 55, "RESTAURANT": 45, "LOGISTIQUE_FRIGO": 70}.get(archetype, 30)
        if froid.pct > froid_threshold_pct:
            excess_pct = froid.pct - froid_threshold_pct
            excess_kwh = round(total_kwh * excess_pct / 100, 0)
            anomalies.append(
                UsageAnomaly(
                    usage_code=froid.code,
                    usage_label=froid.label,
                    anomaly_type="FROID_SURCONSOMMATION",
                    severity="medium",
                    message=f"Froid {froid.pct:.0f}% de la conso vs {froid_threshold_pct}% attendu archetype",
                    detail="La part du froid depasse le seuil typique de l'archetype. "
                    "Causes possibles : condenseurs encrasses, joints de portes defaillants, thermostat mal regle.",
                    gain_kwh_an=excess_kwh,
                    gain_eur_an=round(excess_kwh * PRIX_MOY_EUR_KWH, 0),
                    action="Nettoyage condenseurs + verification joints portes + calibrage thermostat.",
                    confidence="medium",
                    metric_observed=froid.pct,
                    metric_threshold=float(froid_threshold_pct),
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


def _get_site_ps_kva(db: Session, site_id: int) -> Optional[float]:
    """Puissance souscrite max du site (kVA)."""
    try:
        from models.energy_models import Meter
        from services.power.power_profile_service import get_active_contract
        from datetime import date as _date

        meter = db.query(Meter).filter(Meter.site_id == site_id, Meter.is_active == True).first()
        if meter:
            contract = get_active_contract(db, meter.id, _date.today())
            if contract and contract.ps_par_poste_kva:
                return max(contract.ps_par_poste_kva.values())
    except Exception:
        pass
    return None


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
