"""
PROMEOS Analytics Engine - KB-Driven Analysis
Pipeline: Features -> Retrieve archetypes -> Apply anomaly rules -> Generate recommendations -> ICE scoring
Every result has full KB provenance (kb_rule_id, source_section, explanation)
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Meter,
    MeterReading,
    Site,
    UsageProfile,
    Anomaly as AnomalyModel,
    Recommendation as RecommendationModel,
    KBArchetype,
    KBMappingCode,
    KBAnomalyRule,
    KBRecommendation,
    KBVersion,
    KBStatus,
    AnomalySeverity,
    RecommendationStatus,
)
from services.ems.timeseries_service import resolve_best_freq


class AnalyticsEngine:
    """KB-driven analytics engine for energy consumption analysis"""

    def __init__(self, db: Session):
        self.db = db

    def analyze(self, meter_id: int) -> Dict[str, Any]:
        """
        Run full KB-driven analysis pipeline:
        1. Extract features from meter data
        2. Retrieve matching archetype from KB
        3. Apply anomaly rules from KB
        4. Generate recommendations from KB
        5. Compute ICE scores
        """
        meter = self.db.query(Meter).filter_by(id=meter_id).first()
        if not meter:
            return {"status": "error", "message": f"Meter {meter_id} not found"}

        site = self.db.query(Site).filter_by(id=meter.site_id).first()

        # Step 1: Extract features
        features = self._extract_features(meter)
        if not features:
            return {"status": "error", "message": "Insufficient data for analysis"}

        # Step 2: Retrieve archetype
        archetype, match_score = self._retrieve_archetype(site, features)

        # Step 3: Apply anomaly rules from KB
        anomalies = self._apply_anomaly_rules(meter, features, archetype)

        # Step 4: Generate recommendations from KB
        recommendations = self._generate_recommendations(meter, anomalies, archetype, features)

        # Step 5: Save results
        profile = self._save_profile(meter, features, archetype, match_score)
        saved_anomalies = self._save_anomalies(meter, anomalies)
        saved_recos = self._save_recommendations(meter, recommendations)

        return {
            "status": "ok",
            "meter_id": meter.meter_id,
            "site_name": site.nom if site else "Unknown",
            "features": features,
            "archetype": {
                "code": archetype.code if archetype else None,
                "title": archetype.title if archetype else None,
                "match_score": match_score,
                "kwh_m2_range": f"{archetype.kwh_m2_min}-{archetype.kwh_m2_max}" if archetype else None,
            },
            "anomalies": [
                {
                    "code": a["code"],
                    "title": a["title"],
                    "severity": a["severity"],
                    "confidence": a["confidence"],
                    "measured": a["measured_value"],
                    "threshold": a["threshold_value"],
                    "deviation_pct": a["deviation_pct"],
                    "kb_rule_id": a["kb_rule_id"],
                    "explanation": a["explanation"],
                }
                for a in anomalies
            ],
            "recommendations": [
                {
                    "code": r["code"],
                    "title": r["title"],
                    "ice_score": r["ice_score"],
                    "savings_pct": r["estimated_savings_pct"],
                    "kb_recommendation_id": r["kb_recommendation_id"],
                    "triggered_by": r["triggered_by"],
                }
                for r in recommendations
            ],
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _extract_features(self, meter: Meter) -> Optional[Dict[str, Any]]:
        """Step 1: Extract features from meter readings"""
        # Get all readings (single best frequency to prevent double-counting)
        best = resolve_best_freq(self.db, [meter.id], None, None)
        readings = (
            self.db.query(MeterReading)
            .filter(MeterReading.meter_id == meter.id, MeterReading.frequency.in_(best))
            .order_by(MeterReading.timestamp)
            .all()
        )

        if len(readings) < 48:  # Minimum 2 days of hourly data
            return None

        # Basic aggregates
        values = [r.value_kwh for r in readings]
        timestamps = [r.timestamp for r in readings]

        total_kwh = sum(values)
        date_range = (timestamps[-1] - timestamps[0]).days or 1
        annual_kwh = total_kwh * (365.0 / date_range) if date_range >= 30 else total_kwh

        # Get site surface
        site = self.db.query(Site).filter_by(id=meter.site_id).first()
        surface_m2 = site.surface_m2 if site and site.surface_m2 and site.surface_m2 > 0 else None
        kwh_m2_year = annual_kwh / surface_m2 if surface_m2 else None

        # Night base ratio (22h-6h vs 8h-18h)
        night_values = [r.value_kwh for r in readings if r.timestamp.hour >= 22 or r.timestamp.hour < 6]
        day_values = [r.value_kwh for r in readings if 8 <= r.timestamp.hour <= 18]

        night_avg = sum(night_values) / len(night_values) if night_values else 0
        day_avg = sum(day_values) / len(day_values) if day_values else 1
        base_nuit_ratio = night_avg / day_avg if day_avg > 0 else 0

        # Weekend ratio
        weekend_values = [r.value_kwh for r in readings if r.timestamp.weekday() >= 5]
        weekday_values = [r.value_kwh for r in readings if r.timestamp.weekday() < 5]

        weekend_avg = sum(weekend_values) / len(weekend_values) if weekend_values else 0
        weekday_avg = sum(weekday_values) / len(weekday_values) if weekday_values else 1
        weekend_ratio = weekend_avg / weekday_avg if weekday_avg > 0 else 0

        # Peak power
        peak_power_kw = max(values) if values else 0

        # Load factor
        avg_power = sum(values) / len(values) if values else 0
        load_factor = avg_power / peak_power_kw if peak_power_kw > 0 else 0

        # Monthly averages for seasonality
        monthly_sums = {}
        monthly_counts = {}
        for r in readings:
            m = r.timestamp.month
            monthly_sums[m] = monthly_sums.get(m, 0) + r.value_kwh
            monthly_counts[m] = monthly_counts.get(m, 0) + 1

        monthly_avgs = {m: monthly_sums[m] / monthly_counts[m] for m in monthly_sums}
        monthly_values = list(monthly_avgs.values()) if monthly_avgs else [0]

        # Coefficient of variation for seasonality
        mean_monthly = sum(monthly_values) / len(monthly_values) if monthly_values else 1
        variance = sum((v - mean_monthly) ** 2 for v in monthly_values) / len(monthly_values) if monthly_values else 0
        std_monthly = math.sqrt(variance)
        seasonality_cv = std_monthly / mean_monthly if mean_monthly > 0 else 0

        # Summer gas indicator (months 6-8)
        summer_readings = [r.value_kwh for r in readings if r.timestamp.month in (6, 7, 8)]
        summer_total = sum(summer_readings) if summer_readings else 0
        summer_ratio = summer_total / total_kwh if total_kwh > 0 else 0

        return {
            "kwh_total": round(total_kwh, 1),
            "kwh_annual_estimate": round(annual_kwh, 1),
            "kwh_m2_year": round(kwh_m2_year, 1) if kwh_m2_year else None,
            "surface_m2": surface_m2,
            "base_nuit_ratio": round(base_nuit_ratio, 3),
            "weekend_ratio": round(weekend_ratio, 3),
            "peak_power_kw": round(peak_power_kw, 1),
            "load_factor": round(load_factor, 3),
            "seasonality_cv": round(seasonality_cv, 3),
            "summer_ratio": round(summer_ratio, 3),
            "readings_count": len(readings),
            "date_range_days": date_range,
            "monthly_averages": {str(m): round(v, 1) for m, v in monthly_avgs.items()},
        }

    def _retrieve_archetype(self, site: Optional[Site], features: Dict) -> tuple:
        """Step 2: Retrieve best-matching archetype from KB"""
        # Method 1: NAF code match (V110: cascade Site → EJ)
        from utils.naf_resolver import resolve_naf_code

        resolved_naf = resolve_naf_code(site, self.db) if site else None
        if site and resolved_naf:
            naf_code = resolved_naf.strip()
            naf_no_dot = naf_code.replace(".", "")

            # Try exact match (with dot)
            mapping = self.db.query(KBMappingCode).filter(KBMappingCode.naf_code == naf_code).first()

            # Try exact match (without dot)
            if not mapping:
                mapping = self.db.query(KBMappingCode).filter(KBMappingCode.naf_code == naf_no_dot).first()

            # Try LIKE match (contains)
            if not mapping:
                mapping = self.db.query(KBMappingCode).filter(KBMappingCode.naf_code.like(f"%{naf_no_dot}%")).first()

            # Try prefix match (first 2 digits)
            if not mapping and len(naf_no_dot) >= 2:
                mapping = self.db.query(KBMappingCode).filter(KBMappingCode.naf_code.like(f"{naf_no_dot[:2]}%")).first()

            if mapping:
                archetype = mapping.archetype
                return archetype, self._compute_match_score(features, archetype)

        # Method 2: Feature-based matching (kWh/m2 range)
        if features.get("kwh_m2_year"):
            kwh_m2 = features["kwh_m2_year"]

            archetypes = self.db.query(KBArchetype).filter_by(status=KBStatus.VALIDATED).all()

            best_match = None
            best_score = 0.0

            for arch in archetypes:
                if arch.kwh_m2_min and arch.kwh_m2_max:
                    mid = (arch.kwh_m2_min + arch.kwh_m2_max) / 2
                    span = arch.kwh_m2_max - arch.kwh_m2_min
                    if span > 0:
                        # Gaussian-like scoring
                        distance = abs(kwh_m2 - mid) / span
                        score = max(0, 1.0 - distance)

                        if score > best_score:
                            best_score = score
                            best_match = arch

            if best_match:
                return best_match, round(best_score, 2)

        # Method 3: Default
        default = self.db.query(KBArchetype).filter_by(code="BUREAU_STANDARD").first()

        return default, 0.3  # Low confidence default

    def _compute_match_score(self, features: Dict, archetype: KBArchetype) -> float:
        """Compute archetype match score based on real meter features."""
        base = 0.70
        bonus = 0.0
        arch_code = archetype.code or ""

        # 1. kWh/m²/an vs archetype range
        kwh_m2 = features.get("kwh_m2_year")
        if kwh_m2 and archetype.kwh_m2_min and archetype.kwh_m2_max:
            if archetype.kwh_m2_min <= kwh_m2 <= archetype.kwh_m2_max:
                bonus += 0.15
            elif kwh_m2 < archetype.kwh_m2_min * 0.7 or kwh_m2 > archetype.kwh_m2_max * 1.3:
                bonus -= 0.10
            else:
                bonus += 0.05

        # 2. Weekend ratio coherence
        weekend_ratio = features.get("weekend_ratio")
        if weekend_ratio is not None:
            if "BUREAU" in arch_code and weekend_ratio < 0.40:
                bonus += 0.10
            elif "BUREAU" in arch_code and weekend_ratio > 0.70:
                bonus -= 0.05
            elif "HOTEL" in arch_code and weekend_ratio > 0.65:
                bonus += 0.10
            elif "ENSEIGNEMENT" in arch_code and weekend_ratio < 0.35:
                bonus += 0.10
            elif "ENTREPOT" in arch_code or "LOGISTIQUE" in arch_code or "INDUSTRIE" in arch_code:
                if 0.30 <= weekend_ratio <= 0.60:
                    bonus += 0.05

        # 3. Night ratio coherence
        night_ratio = features.get("night_ratio")
        if night_ratio is not None:
            if "BUREAU" in arch_code and night_ratio < 0.25:
                bonus += 0.05
            elif "HOTEL" in arch_code and night_ratio > 0.40:
                bonus += 0.05

        return round(min(max(base + bonus, 0.40), 0.98), 2)

    def _apply_anomaly_rules(self, meter: Meter, features: Dict, archetype: Optional[KBArchetype]) -> List[Dict]:
        """Step 3: Apply KB anomaly rules against computed features"""
        anomalies = []

        rules = self.db.query(KBAnomalyRule).filter_by(status=KBStatus.VALIDATED).all()

        for rule in rules:
            result = self._evaluate_rule(rule, features, archetype)
            if result["triggered"]:
                anomalies.append(
                    {
                        "code": rule.code,
                        "title": rule.title,
                        "severity": result["severity"],
                        "confidence": result["confidence"],
                        "measured_value": result["measured"],
                        "threshold_value": result["threshold"],
                        "deviation_pct": result["deviation_pct"],
                        "kb_rule_id": rule.id,
                        "kb_version_id": rule.kb_version_id,
                        "explanation": result["explanation"],
                    }
                )

        return anomalies

    def _evaluate_rule(self, rule: KBAnomalyRule, features: Dict, archetype: Optional[KBArchetype]) -> Dict:
        """Evaluate a single anomaly rule using thresholds_json when available."""
        t = rule.thresholds_json or {}
        not_triggered = {
            "triggered": False,
            "severity": "low",
            "confidence": 0,
            "measured": 0,
            "threshold": 0,
            "deviation_pct": 0,
            "explanation": "",
        }

        if rule.rule_type == "base_nuit":
            threshold = t.get("max_ratio", 0.25)
            if archetype and archetype.code in ("COMMERCE_ALIMENTAIRE", "LOGISTIQUE_FROID"):
                threshold = max(threshold, 0.70)
            elif archetype and archetype.code in ("HOTEL_STANDARD", "HOPITAL_STANDARD"):
                threshold = max(threshold, 0.50)
            measured = (
                features.get("weekend_ratio", 0)
                if features.get("base_nuit_ratio", 0) > 1
                else features.get("base_nuit_ratio", 0)
            )
            # Fallback: use night_ratio synonym
            if measured == 0:
                measured = features.get("night_ratio", 0)
            triggered = measured > threshold
            deviation = ((measured - threshold) / threshold * 100) if threshold > 0 and triggered else 0

        elif rule.rule_type == "weekend":
            threshold = t.get("max_ratio", 0.40)
            if archetype and archetype.code in ("COMMERCE_ALIMENTAIRE", "RESTAURATION_SERVICE"):
                threshold = max(threshold, 0.80)
            measured = features.get("weekend_ratio", 0)
            triggered = measured > threshold
            deviation = ((measured - threshold) / threshold * 100) if threshold > 0 and triggered else 0

        elif rule.rule_type == "puissance":
            measured = features.get("load_factor", 0)
            over = t.get("over_ratio", 0.95)
            under = t.get("under_ratio", 0.30)
            if measured > over:
                triggered, threshold = True, over
                deviation = (measured - over) / over * 100
            elif measured < under and measured > 0:
                triggered, threshold = True, under
                deviation = (under - measured) / under * 100
            else:
                return not_triggered

        elif rule.rule_type in ("saisonnier", "saisonnalite"):
            # RULE-SAISONNIER-001: CV too low (no seasonality)
            min_cv = t.get("min_cv")
            max_summer = t.get("max_summer_ratio")
            if min_cv is not None:
                measured = features.get("seasonality_cv", 0)
                threshold = min_cv
                triggered = measured < threshold
                deviation = ((threshold - measured) / threshold * 100) if threshold > 0 and triggered else 0
            elif max_summer is not None:
                measured = features.get("summer_ratio", 0)
                threshold = max_summer
                triggered = measured > threshold
                deviation = ((measured - threshold) / threshold * 100) if threshold > 0 and triggered else 0
            else:
                return not_triggered

        elif rule.rule_type == "tendance":
            max_drift = t.get("max_drift_pct", 10.0)
            # Compute drift from monthly averages
            monthly = features.get("monthly_averages", {})
            if len(monthly) >= 6:
                vals = list(monthly.values())
                first_half = sum(vals[: len(vals) // 2]) / max(len(vals) // 2, 1)
                second_half = sum(vals[len(vals) // 2 :]) / max(len(vals) - len(vals) // 2, 1)
                drift = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
                measured = round(drift, 1)
                threshold = max_drift
                triggered = abs(measured) > threshold
                deviation = abs(measured) - threshold if triggered else 0
            else:
                return not_triggered

        elif rule.rule_type in ("benchmark", "ratio_m2"):
            measured = features.get("kwh_m2_year")
            if not measured or not archetype:
                return not_triggered
            p90_margin = t.get("p90_margin", 1.5)
            p10_margin = t.get("p10_margin", 0.5)
            threshold_high = archetype.kwh_m2_max * p90_margin if archetype.kwh_m2_max else 500
            threshold_low = archetype.kwh_m2_min * p10_margin if archetype.kwh_m2_min else 50
            if measured > threshold_high:
                triggered, threshold = True, threshold_high
                deviation = (measured - threshold_high) / threshold_high * 100
            elif measured < threshold_low:
                triggered, threshold = True, threshold_low
                deviation = (threshold_low - measured) / threshold_low * 100
            else:
                return not_triggered

        elif rule.rule_type == "qualite":
            # Data quality: check readings_count vs expected
            max_gap = t.get("max_gap_hours", 48)
            min_val = t.get("min_value", 0)
            readings = features.get("readings_count", 0)
            days = features.get("date_range_days", 0)
            expected = days  # 1 reading/day minimum
            if expected > 0 and readings < expected * 0.9:
                measured = readings
                threshold = expected * 0.9
                triggered = True
                deviation = (threshold - readings) / threshold * 100
            else:
                return not_triggered

        elif rule.rule_type == "facturation":
            # Billing vs metering — not available in demo features, skip
            return not_triggered

        elif rule.rule_type == "gaz_ete":
            threshold = t.get("max_summer_ratio", 0.10)
            measured = features.get("summer_ratio", 0)
            triggered = measured > threshold
            deviation = ((measured - threshold) / threshold * 100) if threshold > 0 and triggered else 0

        else:
            return not_triggered

        if not triggered:
            return not_triggered

        # Dynamic severity
        severity = self._dynamic_severity(rule.severity, round(deviation, 1))

        return {
            "triggered": True,
            "severity": severity,
            "confidence": 0.85
            if rule.confidence.value == "HIGH"
            else 0.70
            if rule.confidence.value == "MEDIUM"
            else 0.55,
            "measured": round(measured, 3) if isinstance(measured, float) else measured,
            "threshold": round(threshold, 3) if isinstance(threshold, float) else threshold,
            "deviation_pct": round(deviation, 1),
            "explanation": f"{rule.title} (mesure={measured:.3g}, seuil={threshold:.3g}, ecart={deviation:.1f}%)",
        }

    def _dynamic_severity(self, base_severity: str, deviation_pct: float) -> str:
        """Adjust severity based on deviation amplitude."""
        abs_dev = abs(deviation_pct) if deviation_pct else 0
        if abs_dev > 100:
            return "critical"
        elif abs_dev > 50:
            return "high"
        elif abs_dev > 20:
            return base_severity  # keep KB severity
        else:
            down = {"critical": "high", "high": "medium", "medium": "low"}
            return down.get(base_severity, base_severity)

    def _generate_recommendations(
        self, meter: Meter, anomalies: List[Dict], archetype: Optional[KBArchetype], features: Dict
    ) -> List[Dict]:
        """Step 4: Generate KB-driven recommendations"""
        recommendations = []

        # Get all KB recommendations
        kb_recos = self.db.query(KBRecommendation).filter_by(status=KBStatus.VALIDATED).all()

        for anomaly in anomalies:
            # Find matching KB recommendation
            for kb_reco in kb_recos:
                trigger_codes = kb_reco.anomaly_codes or []
                if anomaly["code"] in trigger_codes:
                    # Compute contextual ICE score
                    impact = kb_reco.impact_score or 5
                    confidence = kb_reco.confidence_score or 5
                    ease = kb_reco.ease_score or 5

                    # Adjust impact based on deviation severity
                    deviation = anomaly.get("deviation_pct", 0)
                    if deviation > 50:
                        impact = min(10, impact + 2)
                    elif deviation > 20:
                        impact = min(10, impact + 1)

                    ice = (impact * confidence * ease) / 1000.0

                    # Estimate savings
                    savings_pct = None
                    if kb_reco.savings_min_pct and kb_reco.savings_max_pct:
                        savings_pct = (kb_reco.savings_min_pct + kb_reco.savings_max_pct) / 2

                    savings_kwh = None
                    if savings_pct and features.get("kwh_annual_estimate"):
                        savings_kwh = features["kwh_annual_estimate"] * savings_pct / 100

                    recommendations.append(
                        {
                            "code": kb_reco.code,
                            "title": kb_reco.title,
                            "description": kb_reco.description,
                            "action_type": kb_reco.action_type,
                            "target_asset": kb_reco.target_asset,
                            "impact_score": impact,
                            "confidence_score": confidence,
                            "ease_score": ease,
                            "ice_score": round(ice, 3),
                            "estimated_savings_pct": savings_pct,
                            "estimated_savings_kwh": round(savings_kwh, 0) if savings_kwh else None,
                            "kb_recommendation_id": kb_reco.id,
                            "kb_version_id": kb_reco.kb_version_id,
                            "triggered_by": anomaly["code"],
                        }
                    )

        # Sort by ICE score descending
        recommendations.sort(key=lambda x: x["ice_score"], reverse=True)

        return recommendations

    def _save_profile(
        self, meter: Meter, features: Dict, archetype: Optional[KBArchetype], match_score: float
    ) -> UsageProfile:
        """Save usage profile"""
        # Delete old profiles for this meter
        self.db.query(UsageProfile).filter_by(meter_id=meter.id).delete()

        now = datetime.now(timezone.utc)
        days = features.get("date_range_days", 365)

        profile = UsageProfile(
            meter_id=meter.id,
            period_start=now - timedelta(days=days),
            period_end=now,
            archetype_id=archetype.id if archetype else None,
            archetype_code=archetype.code if archetype else None,
            archetype_match_score=match_score,
            features_json=features,
            temporal_patterns_json={
                "monthly_averages": features.get("monthly_averages", {}),
            },
            kb_version_id=archetype.kb_version_id if archetype else None,
            analysis_version="1.0",
        )

        self.db.add(profile)
        self.db.commit()

        return profile

    def _save_anomalies(self, meter: Meter, anomalies: List[Dict]) -> List[AnomalyModel]:
        """Save detected anomalies"""
        # Deactivate previous anomalies
        self.db.query(AnomalyModel).filter_by(meter_id=meter.id).update({"is_active": False})

        saved = []
        for a in anomalies:
            severity_map = {
                "low": AnomalySeverity.LOW,
                "medium": AnomalySeverity.MEDIUM,
                "high": AnomalySeverity.HIGH,
                "critical": AnomalySeverity.CRITICAL,
            }

            anomaly = AnomalyModel(
                meter_id=meter.id,
                anomaly_code=a["code"],
                title=a["title"],
                description=a["explanation"],
                severity=severity_map.get(a["severity"], AnomalySeverity.MEDIUM),
                confidence=a["confidence"],
                detected_at=datetime.now(timezone.utc),
                measured_value=a["measured_value"],
                threshold_value=a["threshold_value"],
                deviation_pct=a["deviation_pct"],
                kb_rule_id=a["kb_rule_id"],
                kb_version_id=a.get("kb_version_id"),
                explanation_json={"rule_code": a["code"], "explanation": a["explanation"]},
                is_active=True,
            )
            self.db.add(anomaly)
            saved.append(anomaly)

        self.db.commit()
        return saved

    def _save_recommendations(self, meter: Meter, recommendations: List[Dict]) -> List[RecommendationModel]:
        """Save generated recommendations"""
        # Delete previous recommendations for this meter
        self.db.query(RecommendationModel).filter_by(meter_id=meter.id).delete()

        saved = []
        for i, r in enumerate(recommendations):
            reco = RecommendationModel(
                meter_id=meter.id,
                recommendation_code=r["code"],
                title=r["title"],
                description=r.get("description"),
                triggered_by_anomaly_id=None,  # Will be linked after anomalies are saved
                estimated_savings_pct=r.get("estimated_savings_pct"),
                estimated_savings_kwh_year=r.get("estimated_savings_kwh"),
                impact_score=r["impact_score"],
                confidence_score=r["confidence_score"],
                ease_score=r["ease_score"],
                ice_score=r["ice_score"],
                priority_rank=i + 1,
                kb_recommendation_id=r["kb_recommendation_id"],
                kb_version_id=r.get("kb_version_id"),
                status=RecommendationStatus.PENDING,
            )
            self.db.add(reco)
            saved.append(reco)

        self.db.commit()
        return saved
