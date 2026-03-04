"""
PROMEOS Electric Monitoring - Alert Engine
Generates 12 Tier-1 alerts from KPIs, power risk, and data quality.

12 Alert Types:
 1. BASE_NUIT_ELEVEE       - Night base load above archetype threshold
 2. WEEKEND_ANORMAL        - Weekend consumption abnormally high/low
 3. DERIVE_TALON           - Base load (talon) drifting upward over time
 4. PIC_ANORMAL            - Abnormal peak power event
 5. P95_HAUSSE             - P95 increasing vs previous period
 6. DEPASSEMENT_PUISSANCE  - Power exceeds subscribed capacity
 7. RUPTURE_PROFIL         - Hourly profile shape changed significantly
 8. HORS_HORAIRES          - Significant consumption outside business hours
 9. COURBE_PLATE           - Flat load curve (no day/night variation)
10. DONNEES_MANQUANTES     - Missing data detected
11. DOUBLONS_DST           - Duplicate timestamps or DST issues
12. VALEURS_NEGATIVES      - Negative consumption values
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


# Alert definitions with defaults
ALERT_DEFS = {
    "BASE_NUIT_ELEVEE": {
        "title": "Base nuit elevee",
        "severity": "warning",
        "threshold_night_ratio": 0.35,
    },
    "WEEKEND_ANORMAL": {
        "title": "Consommation weekend anormale",
        "severity": "warning",
        "threshold_weekend_ratio": 0.60,
    },
    "DERIVE_TALON": {
        "title": "Derive du talon de consommation",
        "severity": "warning",
        "threshold_pbase_increase_pct": 15,
    },
    "PIC_ANORMAL": {
        "title": "Pic de puissance anormal",
        "severity": "high",
        "threshold_peak_to_avg": 5.0,
    },
    "P95_HAUSSE": {
        "title": "Hausse du P95",
        "severity": "warning",
        "threshold_p95_increase_pct": 10,
    },
    "DEPASSEMENT_PUISSANCE": {
        "title": "Depassement de puissance souscrite",
        "severity": "critical",
        "threshold_ratio": 1.0,
    },
    "RUPTURE_PROFIL": {
        "title": "Rupture du profil horaire",
        "severity": "warning",
        "threshold_profile_deviation": 0.30,
    },
    "HORS_HORAIRES": {
        "title": "Consommation hors horaires",
        "severity": "info",
        "threshold_off_hours_pct": 25,
    },
    "COURBE_PLATE": {
        "title": "Courbe de charge plate",
        "severity": "info",
        "threshold_load_factor": 0.85,
    },
    "DONNEES_MANQUANTES": {
        "title": "Donnees manquantes",
        "severity": "high",
        "threshold_completeness_pct": 95,
    },
    "DOUBLONS_DST": {
        "title": "Doublons ou collisions DST",
        "severity": "warning",
        "threshold_duplicates": 0,
    },
    "SENSIBILITE_CLIMATIQUE": {
        "title": "Sensibilite climatique elevee",
        "severity": "warning",
        "threshold_slope": 3.0,
    },
    "VALEURS_NEGATIVES": {
        "title": "Valeurs negatives detectees",
        "severity": "critical",
        "threshold_count": 0,
    },
}


class AlertEngine:
    """Generate Tier-1 monitoring alerts from analysis results."""

    def evaluate(
        self,
        kpis: Dict[str, Any],
        power_risk: Dict[str, Any],
        data_quality: Dict[str, Any],
        previous_kpis: Optional[Dict[str, Any]] = None,
        site_id: Optional[int] = None,
        meter_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate all 12 alert rules and return triggered alerts.

        Args:
            kpis: from KPIEngine.compute()
            power_risk: from PowerEngine.compute()
            data_quality: from DataQualityEngine.compute()
            previous_kpis: KPIs from previous period (for trend alerts)
            site_id: scope
            meter_id: scope

        Returns:
            list of alert dicts ready for persistence
        """
        alerts = []
        now = datetime.now(timezone.utc)

        # 1. BASE_NUIT_ELEVEE
        night_ratio = kpis.get("night_ratio", 0)
        thr = ALERT_DEFS["BASE_NUIT_ELEVEE"]["threshold_night_ratio"]
        if night_ratio > thr:
            alerts.append(
                self._make_alert(
                    "BASE_NUIT_ELEVEE",
                    site_id,
                    meter_id,
                    now,
                    explanation=f"Night ratio {night_ratio:.2%} exceeds threshold {thr:.0%}. "
                    f"Base nuit = {kpis.get('pbase_night_kw', 0):.1f} kW.",
                    evidence={
                        "night_ratio": night_ratio,
                        "threshold": thr,
                        "pbase_night_kw": kpis.get("pbase_night_kw", 0),
                    },
                    recommended_action="Auditer les equipements fonctionnant la nuit (CVC, eclairage, serveurs).",
                    estimated_impact_kwh=kpis.get("total_kwh", 0) * (night_ratio - thr) * 0.5,
                )
            )

        # 2. WEEKEND_ANORMAL
        we_ratio = kpis.get("weekend_ratio", 0)
        thr_we = ALERT_DEFS["WEEKEND_ANORMAL"]["threshold_weekend_ratio"]
        if we_ratio > thr_we:
            alerts.append(
                self._make_alert(
                    "WEEKEND_ANORMAL",
                    site_id,
                    meter_id,
                    now,
                    explanation=f"Weekend/weekday ratio {we_ratio:.2%} exceeds {thr_we:.0%}. "
                    f"Equipment may be running unnecessarily on weekends.",
                    evidence={"weekend_ratio": we_ratio, "threshold": thr_we},
                    recommended_action="Verifier les plannings de CVC et eclairage le weekend.",
                    estimated_impact_kwh=kpis.get("total_kwh", 0) * (we_ratio - thr_we) * 0.3,
                )
            )

        # 3. DERIVE_TALON
        if previous_kpis:
            prev_pbase = previous_kpis.get("pbase_kw", 0)
            curr_pbase = kpis.get("pbase_kw", 0)
            if prev_pbase > 0:
                pbase_change_pct = ((curr_pbase - prev_pbase) / prev_pbase) * 100
                thr_derive = ALERT_DEFS["DERIVE_TALON"]["threshold_pbase_increase_pct"]
                if pbase_change_pct > thr_derive:
                    alerts.append(
                        self._make_alert(
                            "DERIVE_TALON",
                            site_id,
                            meter_id,
                            now,
                            explanation=f"Base load increased by {pbase_change_pct:.1f}% "
                            f"({prev_pbase:.1f} -> {curr_pbase:.1f} kW).",
                            evidence={
                                "previous_pbase_kw": prev_pbase,
                                "current_pbase_kw": curr_pbase,
                                "change_pct": round(pbase_change_pct, 1),
                            },
                            recommended_action="Identifier les nouveaux equipements ou les derives de regulation.",
                            estimated_impact_kwh=(curr_pbase - prev_pbase) * 8760 * 0.5,
                        )
                    )

        # 4. PIC_ANORMAL
        peak_to_avg = kpis.get("peak_to_average", 0)
        thr_peak = ALERT_DEFS["PIC_ANORMAL"]["threshold_peak_to_avg"]
        if peak_to_avg > thr_peak:
            alerts.append(
                self._make_alert(
                    "PIC_ANORMAL",
                    site_id,
                    meter_id,
                    now,
                    severity="high",
                    explanation=f"Peak-to-average ratio {peak_to_avg:.1f}x exceeds {thr_peak:.1f}x. "
                    f"Pmax={kpis.get('pmax_kw', 0):.1f} kW, Pmean={kpis.get('pmean_kw', 0):.1f} kW.",
                    evidence={
                        "peak_to_average": peak_to_avg,
                        "threshold": thr_peak,
                        "pmax_kw": kpis.get("pmax_kw", 0),
                        "pmean_kw": kpis.get("pmean_kw", 0),
                    },
                    recommended_action="Analyser les evenements de pointe, envisager un effacement ou delestage.",
                )
            )

        # 5. P95_HAUSSE
        if previous_kpis:
            prev_p95 = previous_kpis.get("p95_kw", 0)
            curr_p95 = kpis.get("p95_kw", 0)
            if prev_p95 > 0:
                p95_change_pct = ((curr_p95 - prev_p95) / prev_p95) * 100
                thr_p95 = ALERT_DEFS["P95_HAUSSE"]["threshold_p95_increase_pct"]
                if p95_change_pct > thr_p95:
                    alerts.append(
                        self._make_alert(
                            "P95_HAUSSE",
                            site_id,
                            meter_id,
                            now,
                            explanation=f"P95 increased by {p95_change_pct:.1f}% "
                            f"({prev_p95:.1f} -> {curr_p95:.1f} kW).",
                            evidence={
                                "previous_p95_kw": prev_p95,
                                "current_p95_kw": curr_p95,
                                "change_pct": round(p95_change_pct, 1),
                            },
                            recommended_action="Revoir la puissance souscrite si la hausse persiste.",
                        )
                    )

        # 6. DEPASSEMENT_PUISSANCE
        ratio_p95 = power_risk.get("ratio_p95_psub", 0)
        dep_count = power_risk.get("depassement_count", 0)
        if dep_count > 0:
            alerts.append(
                self._make_alert(
                    "DEPASSEMENT_PUISSANCE",
                    site_id,
                    meter_id,
                    now,
                    severity="critical",
                    explanation=f"{dep_count} depassement(s) de puissance souscrite detecte(s). "
                    f"P95/Psub = {ratio_p95:.2%}.",
                    evidence={
                        "depassement_count": dep_count,
                        "ratio_p95_psub": ratio_p95,
                        "subscribed_kva": power_risk.get("subscribed_power_kva", 0),
                    },
                    recommended_action="Ajuster la puissance souscrite ou mettre en place un effacement.",
                    estimated_impact_eur=dep_count * 50,  # rough penalty estimate
                )
            )

        # 7. RUPTURE_PROFIL
        if previous_kpis:
            prev_profile = previous_kpis.get("weekday_profile_kw", [0] * 24)
            curr_profile = kpis.get("weekday_profile_kw", [0] * 24)
            if len(prev_profile) == 24 and len(curr_profile) == 24:
                deviations = []
                for h in range(24):
                    if prev_profile[h] > 0:
                        dev = abs(curr_profile[h] - prev_profile[h]) / prev_profile[h]
                        deviations.append(dev)
                avg_deviation = sum(deviations) / len(deviations) if deviations else 0
                thr_rupture = ALERT_DEFS["RUPTURE_PROFIL"]["threshold_profile_deviation"]
                if avg_deviation > thr_rupture:
                    alerts.append(
                        self._make_alert(
                            "RUPTURE_PROFIL",
                            site_id,
                            meter_id,
                            now,
                            explanation=f"Hourly profile deviation {avg_deviation:.1%} exceeds {thr_rupture:.0%}. "
                            f"Usage pattern has significantly changed.",
                            evidence={
                                "avg_deviation_pct": round(avg_deviation * 100, 1),
                                "threshold_pct": thr_rupture * 100,
                            },
                            recommended_action="Verifier les changements d'occupation ou d'equipements.",
                        )
                    )

        # 8. HORS_HORAIRES
        weekday_profile = kpis.get("weekday_profile_kw", [0] * 24)
        total_profile_kwh = sum(weekday_profile)
        if total_profile_kwh > 0:
            off_hours_kwh = sum(weekday_profile[h] for h in range(24) if h < 7 or h > 19)
            off_hours_pct = (off_hours_kwh / total_profile_kwh) * 100
            thr_off = ALERT_DEFS["HORS_HORAIRES"]["threshold_off_hours_pct"]
            if off_hours_pct > thr_off:
                alerts.append(
                    self._make_alert(
                        "HORS_HORAIRES",
                        site_id,
                        meter_id,
                        now,
                        severity="info",
                        explanation=f"{off_hours_pct:.1f}% of weekday consumption occurs outside 7h-19h.",
                        evidence={"off_hours_pct": round(off_hours_pct, 1), "threshold": thr_off},
                        recommended_action="Verifier les programmations horaires des equipements.",
                    )
                )

        # 9. COURBE_PLATE
        load_factor = kpis.get("load_factor", 0)
        thr_lf = ALERT_DEFS["COURBE_PLATE"]["threshold_load_factor"]
        if load_factor > thr_lf:
            alerts.append(
                self._make_alert(
                    "COURBE_PLATE",
                    site_id,
                    meter_id,
                    now,
                    severity="info",
                    explanation=f"Load factor {load_factor:.2%} is very high, indicating a flat curve. "
                    f"Possible 24/7 process or stuck equipment.",
                    evidence={"load_factor": load_factor, "threshold": thr_lf},
                    recommended_action="Verifier si un process 24/7 est attendu ou si un equipement est bloque.",
                )
            )

        # 10. DONNEES_MANQUANTES
        completeness = data_quality.get("completeness_pct", 100)
        thr_comp = ALERT_DEFS["DONNEES_MANQUANTES"]["threshold_completeness_pct"]
        if completeness < thr_comp:
            alerts.append(
                self._make_alert(
                    "DONNEES_MANQUANTES",
                    site_id,
                    meter_id,
                    now,
                    severity="high",
                    explanation=f"Data completeness {completeness:.1f}% below threshold {thr_comp}%. "
                    f"{data_quality.get('gap_count', 0)} gaps detected.",
                    evidence={
                        "completeness_pct": completeness,
                        "gap_count": data_quality.get("gap_count", 0),
                        "max_gap_hours": data_quality.get("max_gap_hours", 0),
                    },
                    recommended_action="Verifier la connexion au compteur et relancer la collecte.",
                )
            )

        # 11. DOUBLONS_DST
        dup_count = data_quality.get("duplicate_count", 0)
        dst_count = data_quality.get("dst_collisions", 0)
        if dup_count > 0 or dst_count > 0:
            alerts.append(
                self._make_alert(
                    "DOUBLONS_DST",
                    site_id,
                    meter_id,
                    now,
                    explanation=f"{dup_count} doublons et {dst_count} collisions DST detectes.",
                    evidence={"duplicate_count": dup_count, "dst_collisions": dst_count},
                    recommended_action="Nettoyer les doublons et verifier la gestion du changement d'heure.",
                )
            )

        # 12. VALEURS_NEGATIVES
        neg_count = data_quality.get("negative_count", 0)
        if neg_count > 0:
            alerts.append(
                self._make_alert(
                    "VALEURS_NEGATIVES",
                    site_id,
                    meter_id,
                    now,
                    severity="critical",
                    explanation=f"{neg_count} valeur(s) negative(s) detectee(s). "
                    f"Possible erreur de comptage ou injection reseau.",
                    evidence={"negative_count": neg_count},
                    recommended_action="Verifier le cablage du compteur et la presence de production locale.",
                )
            )

        return alerts

    def _make_alert(
        self,
        alert_type: str,
        site_id: Optional[int],
        meter_id: Optional[int],
        now: datetime,
        explanation: str,
        evidence: Dict[str, Any],
        recommended_action: str = "",
        severity: Optional[str] = None,
        estimated_impact_kwh: float = 0,
        estimated_impact_eur: float = 0,
    ) -> Dict[str, Any]:
        """Build a standardized alert dict."""
        defn = ALERT_DEFS.get(alert_type, {})
        return {
            "alert_type": alert_type,
            "title": defn.get("title", alert_type),
            "severity": severity or defn.get("severity", "warning"),
            "site_id": site_id,
            "meter_id": meter_id,
            "explanation": explanation,
            "evidence": evidence,
            "recommended_action": recommended_action,
            "estimated_impact_kwh": round(estimated_impact_kwh, 1) if estimated_impact_kwh else None,
            "estimated_impact_eur": round(estimated_impact_eur, 1) if estimated_impact_eur else None,
            "kb_link": {
                "alert_type": alert_type,
                "provenance": "monitoring_engine_v1",
            },
            "created_at": now.isoformat(),
        }

    def evaluate_climate(
        self,
        climate: Dict[str, Any],
        site_id: Optional[int] = None,
        meter_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluate climate-specific alerts from ClimateEngine output."""
        alerts = []
        now = datetime.now(timezone.utc)

        slope = abs(climate.get("slope_kw_per_c") or 0)
        r2 = climate.get("r_squared") or 0
        threshold = ALERT_DEFS["SENSIBILITE_CLIMATIQUE"]["threshold_slope"]

        if slope > threshold and r2 > 0.3:
            label = climate.get("label", "unknown")
            bp = climate.get("balance_point_c")
            alerts.append(
                self._make_alert(
                    "SENSIBILITE_CLIMATIQUE",
                    site_id,
                    meter_id,
                    now,
                    explanation=(
                        f"Pente climatique {slope:.1f} kWh/degC depasse le seuil de {threshold} kWh/degC. "
                        f"R²={r2:.2f}, profil: {label}." + (f" Balance point: {bp:.0f}°C." if bp else "")
                    ),
                    evidence={
                        "slope_kw_per_c": slope,
                        "r_squared": r2,
                        "balance_point_c": bp,
                        "label": label,
                    },
                    recommended_action=(
                        "Auditer l'isolation et les systemes CVC pour reduire la sensibilite climatique."
                    ),
                )
            )

        return alerts
