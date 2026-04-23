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

    # === Detecteur 14 : Pic midi absent (bureaux avec cantine) ===
    if archetype in ("BUREAU_STANDARD", "ENSEIGNEMENT", "ENSEIGNEMENT_SUP", "COLLECTIVITE"):
        biz_mean = temporal.get("biz_mean_kw", 0)
        baseload = temporal.get("baseload_kw", 0)
        if biz_mean > 0 and baseload > 0:
            # Si le profil est tres plat (faible increment jour vs nuit) -> pas de pic midi
            increment_ratio = (biz_mean - baseload) / biz_mean if biz_mean > 0 else 0
            if increment_ratio < 0.20:
                anomalies.append(
                    UsageAnomaly(
                        usage_code="GLOBAL",
                        usage_label="Profil occupation",
                        anomaly_type="PIC_MIDI_ABSENT",
                        severity="low",
                        message=f"Profil tres plat (increment jour/nuit {increment_ratio:.0%})",
                        detail="Le profil de consommation ne montre pas de variation significative entre nuit et jour. "
                        "Possible : occupation faible (teletravail), ou equipements tournant 24/7.",
                        gain_kwh_an=0,
                        gain_eur_an=0,
                        action="Verifier le taux d'occupation reel. Adapter les horaires CVC/eclairage.",
                        confidence="low",
                        metric_observed=round(increment_ratio, 3),
                        metric_threshold=0.20,
                    )
                )

    # === Detecteur 15 : Creux nuit trop faible (equipements oublies) ===
    if temporal.get("baseload_kw", 0) > 0 and temporal.get("biz_mean_kw", 0) > 0:
        night_ratio_abs = temporal["baseload_kw"] / temporal["biz_mean_kw"]
        expected_night_max = thresholds.get("ANOM_BASE_NUIT_ELEVEE", 0.20)
        # Inverse : si night_ratio < 2% = suspect (compteur defaillant ?)
        if night_ratio_abs < 0.02 and temporal.get("n_night_readings", 0) > 10:
            anomalies.append(
                UsageAnomaly(
                    usage_code="GLOBAL",
                    usage_label="Qualite donnees",
                    anomaly_type="CREUX_NUIT_SUSPECT",
                    severity="high",
                    message=f"Baseload nuit quasi nul ({night_ratio_abs:.1%}) — compteur defaillant ?",
                    detail="La consommation nocturne est < 2% du jour. Possible panne compteur, "
                    "coupure alimentation, ou site reellement vide (verifier).",
                    gain_kwh_an=0,
                    gain_eur_an=0,
                    action="Verifier le compteur et l'alimentation electrique du site.",
                    confidence="medium",
                    metric_observed=round(night_ratio_abs, 4),
                    metric_threshold=0.02,
                )
            )

    # === Detecteur 16 : Chauffage collectif nuit (bailleurs) ===
    if archetype in ("COPROPRIETE", "COLLECTIVITE") and cvc and cvc.pct > 30:
        night_base_ratio = _compute_night_base_ratio(temporal)
        # Pour copro, le chauffage nuit devrait etre reduit (16-17°C vs 19-20°C jour)
        if night_base_ratio > 0.70:
            excess_kwh = round(cvc.kwh * (night_base_ratio - 0.50) * 0.5, 0)
            if excess_kwh > 500:
                anomalies.append(
                    UsageAnomaly(
                        usage_code="CVC_HVAC",
                        usage_label=cvc.label,
                        anomaly_type="CHAUFFAGE_COLLECTIF_NUIT",
                        severity="medium",
                        message=f"Chauffage collectif nuit eleve ({night_base_ratio:.0%}) — pas de reduction nocturne",
                        detail="Le chauffage semble fonctionner a puissance constante jour et nuit. "
                        "Programmer un abaissement nocturne (16-17 degres C) economiserait 15-20%.",
                        gain_kwh_an=excess_kwh,
                        gain_eur_an=round(excess_kwh * PRIX_MOY_EUR_KWH, 0),
                        action="Installer un programmateur horaire sur la chaudiere/PAC. Consigne nuit 16 degres C.",
                        confidence="medium",
                        metric_observed=round(night_base_ratio, 3),
                        metric_threshold=0.70,
                    )
                )

    # === Detecteur 17 : ECS circulation 24/7 (boucle antilégionellose non programmee) ===
    if ecs and ecs.pct > 5 and archetype in ("COPROPRIETE", "SANTE", "HOTEL_HEBERGEMENT", "SPORT_LOISIR"):
        # ECS devrait avoir un arret circulateur nuit (sauf sterilisation mardi/samedi)
        if temporal.get("baseload_kw", 0) > 0:
            ecs_night_proxy = temporal["baseload_kw"] * (ecs.pct / 100)
            if ecs_night_proxy > 0.3:  # > 300W nuit pour ECS = circulateur actif
                ecs_save_kwh = round(ecs_night_proxy * 8 * 365 * 0.6, 0)  # 8h nuit, 60% economisable
                anomalies.append(
                    UsageAnomaly(
                        usage_code="ECS",
                        usage_label=ecs.label,
                        anomaly_type="ECS_CIRCULATION_24_7",
                        severity="low",
                        message="Circulateur ECS probablement actif 24/7 (boucle antilégionellose non programmee)",
                        detail="Le circulateur de la boucle ECS semble tourner jour et nuit. "
                        "Programmer un arret 0h-6h (sauf mardi/samedi sterilisation) economise 30-40%.",
                        gain_kwh_an=ecs_save_kwh,
                        gain_eur_an=round(ecs_save_kwh * PRIX_MOY_EUR_KWH, 0),
                        action="Programmer arret circulateur ECS 0h-6h. Maintenir sterilisation 60 degres C mardi+samedi.",
                        confidence="low",
                        metric_observed=round(ecs_night_proxy, 2),
                        metric_threshold=0.3,
                    )
                )

    # === Detecteur 18 : Variance horaire extreme (equipement instable) ===
    if temporal.get("biz_mean_kw", 0) > 0 and temporal.get("baseload_kw", 0) > 0:
        # Coefficient de variation simplifie = (biz_mean - baseload) / baseload
        cv = (
            (temporal["biz_mean_kw"] - temporal["baseload_kw"]) / temporal["baseload_kw"]
            if temporal["baseload_kw"] > 0
            else 0
        )
        if cv > 5.0:  # variation > 5x le baseload = tres instable
            anomalies.append(
                UsageAnomaly(
                    usage_code="GLOBAL",
                    usage_label="Stabilite profil",
                    anomaly_type="VARIANCE_HORAIRE_EXTREME",
                    severity="low",
                    message=f"Profil tres variable (ratio pic/base {cv:.1f}x)",
                    detail="Le ratio entre la puissance moyenne jour et le baseload nuit est tres eleve. "
                    "Possible : equipements a demarrage violent, charges tres intermittentes.",
                    gain_kwh_an=0,
                    gain_eur_an=0,
                    action="Lisser les demarrages d'equipements. Evaluer un ecretage de pointe.",
                    confidence="low",
                    metric_observed=round(cv, 1),
                    metric_threshold=5.0,
                )
            )

    # === Detecteur 19 : Froid hopital/sante excessif ===
    if archetype == "SANTE" and froid and froid.pct > 15:
        anomalies.append(
            UsageAnomaly(
                usage_code=froid.code,
                usage_label=froid.label,
                anomaly_type="FROID_SANTE_EXCESSIF",
                severity="medium",
                message=f"Froid {froid.pct:.0f}% sur site sante (seuil 15%)",
                detail="La part du froid depasse le seuil attendu pour un site sante. "
                "Verifier pharmacie froide, blocs operatoires, et free-cooling si disponible.",
                gain_kwh_an=round(froid.kwh * 0.15, 0),
                gain_eur_an=round(froid.kwh * 0.15 * PRIX_MOY_EUR_KWH, 0),
                action="Deployer le free-cooling quand T_ext < 18 degres C. Verifier maintenance groupes froids.",
                confidence="medium",
                metric_observed=froid.pct,
                metric_threshold=15.0,
            )
        )

    # === Detecteur 20 : Restaurant ECS post-service excessive ===
    if archetype == "RESTAURANT" and ecs and ecs.pct > 8:
        # ECS elevee pour un restaurant = lavage excessif ou fuites
        if ecs.pct > 15:
            excess_kwh = round(ecs.kwh * (ecs.pct - 10) / 100, 0)
            anomalies.append(
                UsageAnomaly(
                    usage_code="ECS",
                    usage_label=ecs.label,
                    anomaly_type="ECS_RESTAURANT_EXCESSIVE",
                    severity="low",
                    message=f"ECS {ecs.pct:.0f}% pour restaurant (attendu 8-12%)",
                    detail="La part ECS depasse le seuil restaurant. Verifier debit lavage, "
                    "fuites circulation, isolation tuyauterie.",
                    gain_kwh_an=excess_kwh,
                    gain_eur_an=round(excess_kwh * PRIX_MOY_EUR_KWH, 0),
                    action="Audit sanitaire : debit robinets, isolation tuyauterie ECS, detartrage.",
                    confidence="low",
                    metric_observed=ecs.pct,
                    metric_threshold=15.0,
                )
            )

    # === Detecteur 21 : Ascenseur consommation elevee ===
    # Heuristique via le ratio baseload sur archetype immeuble
    if archetype in ("COPROPRIETE", "SANTE", "HOTEL_HEBERGEMENT", "BUREAU_STANDARD"):
        it_bureautique = usage_by_code.get("IT_BUREAUTIQUE")
        securite = usage_by_code.get("SECURITE_VEILLE")
        # Proxy : si securite_veille + IT > 15% et archetype immeuble, possible ascenseur surdimensionne
        sec_pct = (securite.pct if securite else 0) + (it_bureautique.pct if it_bureautique else 0)
        if sec_pct > 20 and archetype == "COPROPRIETE":
            anomalies.append(
                UsageAnomaly(
                    usage_code="SECURITE_VEILLE",
                    usage_label="Ascenseurs / equipements communs",
                    anomaly_type="ASCENSEUR_CONSO_ELEVEE",
                    severity="low",
                    message=f"Equipements parties communes {sec_pct:.0f}% (ascenseurs, VMC, securite)",
                    detail="La part des equipements parties communes depasse le seuil attendu. "
                    "Verifier consommation ascenseurs (programmation arret nuit 0h-6h = -12%).",
                    gain_kwh_an=round(total_kwh * 0.02, 0),
                    gain_eur_an=round(total_kwh * 0.02 * PRIX_MOY_EUR_KWH, 0),
                    action="Programmer arret ascenseur 0h-6h. Verifier moteur et roulements.",
                    confidence="low",
                    metric_observed=sec_pct,
                    metric_threshold=20.0,
                )
            )

    # === Detecteur 22 : Froid nuit anormal (hotel/restaurant) ===
    if archetype in ("HOTEL_HEBERGEMENT", "RESTAURANT") and froid and froid.pct > 15:
        night_base_ratio = _compute_night_base_ratio(temporal)
        froid_night_threshold = 0.50 if archetype == "RESTAURANT" else 0.60
        if night_base_ratio > froid_night_threshold:
            froid_excess = round(froid.kwh * (night_base_ratio - froid_night_threshold) * 0.3, 0)
            if froid_excess > 300:
                anomalies.append(
                    UsageAnomaly(
                        usage_code=froid.code,
                        usage_label=froid.label,
                        anomaly_type="FROID_NUIT_ANORMAL",
                        severity="medium",
                        message=f"Froid nuit eleve ({night_base_ratio:.0%}) — porte mal fermee ou thermostat",
                        detail="Le baseload nuit est eleve pour le froid. Verifier joints portes "
                        "refrigerateurs/congelateurs et thermostat.",
                        gain_kwh_an=froid_excess,
                        gain_eur_an=round(froid_excess * PRIX_MOY_EUR_KWH, 0),
                        action="Inspection joints portes + nettoyage condenseur + calibrage thermostat.",
                        confidence="medium",
                        metric_observed=round(night_base_ratio, 3),
                        metric_threshold=froid_night_threshold,
                    )
                )

    # === Detecteur 23 : Restaurant absence pic service ===
    if archetype == "RESTAURANT":
        biz_mean = temporal.get("biz_mean_kw", 0)
        baseload = temporal.get("baseload_kw", 0)
        if biz_mean > 0 and baseload > 0:
            service_ratio = (biz_mean - baseload) / biz_mean
            if service_ratio < 0.30:
                anomalies.append(
                    UsageAnomaly(
                        usage_code="GLOBAL",
                        usage_label="Profil service restaurant",
                        anomaly_type="RESTAURANT_PIC_SERVICE_ABSENT",
                        severity="low",
                        message=f"Profil plat pour restaurant (increment service {service_ratio:.0%})",
                        detail="Le profil ne montre pas de pic net aux heures de service. "
                        "Possible : fermeture non detectee, activite reduite, ou equipements 24/7.",
                        gain_kwh_an=0,
                        gain_eur_an=0,
                        action="Verifier horaires d'ouverture et programmer arret equipements hors service.",
                        confidence="low",
                        metric_observed=round(service_ratio, 3),
                        metric_threshold=0.30,
                    )
                )

    # === Detecteur 24 : Hopital chute brutale (alerte securite) ===
    if archetype == "SANTE":
        biz_mean = temporal.get("biz_mean_kw", 0)
        baseload = temporal.get("baseload_kw", 0)
        if biz_mean > 0 and baseload > 0:
            stability = baseload / biz_mean
            if stability < 0.30:
                anomalies.append(
                    UsageAnomaly(
                        usage_code="GLOBAL",
                        usage_label="Continuite service sante",
                        anomaly_type="HOPITAL_INSTABILITE",
                        severity="high",
                        message=f"Profil instable pour site sante (ratio base/jour {stability:.0%})",
                        detail="Un site sante devrait avoir un profil stable (base > 50% du jour). "
                        "Un ratio bas peut indiquer des coupures ou equipements defaillants.",
                        gain_kwh_an=0,
                        gain_eur_an=0,
                        action="Verifier alimentation secours, UPS, et continuite equipements critiques.",
                        confidence="medium",
                        metric_observed=round(stability, 3),
                        metric_threshold=0.30,
                    )
                )

    # === Detecteur 25 : Chauffage ete anormal (inverse saisonnier) ===
    if cvc and cvc.pct > 20 and thermal:
        a_heating = thermal.get("a_heating", 0) or 0
        b_cooling = thermal.get("b_cooling", 0) or 0
        # Si a_heating >> b_cooling mais qu'on est en ete, le chauffage tourne en ete
        if a_heating > 10 and b_cooling < 2:
            anomalies.append(
                UsageAnomaly(
                    usage_code="CVC_HVAC",
                    usage_label=cvc.label,
                    anomaly_type="CHAUFFAGE_ETE_ANORMAL",
                    severity="low",
                    message=f"Forte sensibilite chauffage ({a_heating:.0f} kWh/DJU) sans composante clim",
                    detail="La signature montre un chauffage dominant sans climatisation significative. "
                    "Verifier que le chauffage s'arrete bien en ete (possible sonde defaillante).",
                    gain_kwh_an=round(a_heating * 30 * 0.2, 0),
                    gain_eur_an=round(a_heating * 30 * 0.2 * PRIX_MOY_EUR_KWH, 0),
                    action="Verifier sonde exterieure et consigne d'arret chauffage ete.",
                    confidence="low",
                    metric_observed=round(a_heating, 1),
                    metric_threshold=10.0,
                )
            )

    # === Detecteur 26 : Eclairage parties communes 24/7 (bailleurs) ===
    ecl = usage_by_code.get("ECLAIRAGE")
    if ecl and ecl.pct > 8 and archetype in ("COPROPRIETE", "COLLECTIVITE"):
        if temporal.get("baseload_kw", 0) > 0 and temporal.get("biz_mean_kw", 0) > 0:
            ecl_night_ratio = temporal["baseload_kw"] / temporal["biz_mean_kw"]
            if ecl_night_ratio > 0.60:
                ecl_save = round(ecl.kwh * 0.40, 0)
                anomalies.append(
                    UsageAnomaly(
                        usage_code="ECLAIRAGE",
                        usage_label="Eclairage parties communes",
                        anomaly_type="ECLAIRAGE_PC_24_7",
                        severity="medium",
                        message=f"Eclairage parties communes probablement 24/7 (ratio nuit/jour {ecl_night_ratio:.0%})",
                        detail="L'eclairage des parties communes semble actif en permanence. "
                        "Installer des detecteurs de presence + minuterie = -40% eclairage.",
                        gain_kwh_an=ecl_save,
                        gain_eur_an=round(ecl_save * PRIX_MOY_EUR_KWH, 0),
                        action="Installer detecteurs de presence halls + minuterie escaliers (150 EUR/point).",
                        confidence="medium",
                        metric_observed=round(ecl_night_ratio, 3),
                        metric_threshold=0.60,
                    )
                )

    # === Detecteur 27 : Vapeur/chaleur perdue (industrie) ===
    if archetype in ("INDUSTRIE_LOURDE", "INDUSTRIE_LEGERE") and thermal:
        a_heating = thermal.get("a_heating", 0) or 0
        if a_heating > 20:
            recup_kwh = round(a_heating * 100 * 0.3, 0)  # 30% recuperable sur 100 DJU
            anomalies.append(
                UsageAnomaly(
                    usage_code="CVC_HVAC",
                    usage_label="Chaleur process",
                    anomaly_type="CHALEUR_PERDUE_INDUSTRIE",
                    severity="medium",
                    message=f"Forte thermosensibilite industrielle ({a_heating:.0f} kWh/DJU) — recuperation chaleur",
                    detail="La forte sensibilite au chauffage sur un site industriel suggere un potentiel "
                    "de recuperation de chaleur process (echangeurs, PAC sur effluents).",
                    gain_kwh_an=recup_kwh,
                    gain_eur_an=round(recup_kwh * PRIX_MOY_EUR_KWH, 0),
                    action="Etude recuperation chaleur process (echangeurs, PAC). CEE IND-UT-117.",
                    confidence="low",
                    metric_observed=round(a_heating, 1),
                    metric_threshold=20.0,
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
        path = os.path.join(
            base, "docs", "base_documentaire", "naf", "naf_archetype_mapping", "archetypes_energy_v1.json"
        )
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for arch in data.get("archetypes", []):
            _ARCHETYPE_CACHE[arch["code"]] = arch
    except Exception as exc:
        logger.debug("archetype data load failed: %s", exc)
        return {}

    return _ARCHETYPE_CACHE.get(archetype_code, {})
