"""
PROMEOS Electric Monitoring - Power/Capacity Risk Engine
Computes risk score (0-100) based on subscribed power usage.

Risk factors:
- P95/P_subscribed ratio (main driver)
- Depassement frequency (how often P > P_sub)
- Volatility (coefficient of variation of power)
- Peak concentration (how clustered peak events are)
"""

from typing import List, Dict, Any, Optional


class PowerEngine:
    """Compute power/capacity risk score from KPIs and subscribed power."""

    # Weight configuration
    WEIGHT_RATIO = 0.45  # P95/Psub ratio
    WEIGHT_DEPASSEMENT = 0.30  # Frequency of exceeding subscribed power
    WEIGHT_VOLATILITY = 0.15  # CV of power
    WEIGHT_PEAK_CONC = 0.10  # Peak concentration

    def compute(
        self,
        kpis: Dict[str, Any],
        readings: List[Dict[str, Any]],
        subscribed_power_kva: Optional[float] = None,
        interval_minutes: int = 60,
    ) -> Dict[str, Any]:
        """
        Compute power risk score.

        Args:
            kpis: output from KPIEngine.compute()
            readings: raw readings [{timestamp, value_kwh}]
            subscribed_power_kva: subscribed power in kVA (None = unknown)
            interval_minutes: step size

        Returns:
            dict with risk_score (0-100), details, depassements list
        """
        if not readings or not kpis or kpis.get("readings_count", 0) == 0:
            return self._empty_result()

        hours_per_interval = interval_minutes / 60.0
        powers_kw = [r["value_kwh"] / hours_per_interval for r in readings]

        p95 = kpis.get("p95_kw", 0)
        pmax = kpis.get("pmax_kw", 0)
        pmean = kpis.get("pmean_kw", 0)

        # If no subscribed power, estimate from P95 * 1.2
        p_sub = (
            subscribed_power_kva
            if subscribed_power_kva and subscribed_power_kva > 0
            else (p95 * 1.2 if p95 > 0 else 100)
        )

        # --- Factor 1: P95/Psub ratio ---
        ratio_p95 = p95 / p_sub if p_sub > 0 else 0
        # Score: 0-100 based on ratio (>1.0 = danger zone)
        if ratio_p95 <= 0.5:
            score_ratio = ratio_p95 * 20  # 0-10
        elif ratio_p95 <= 0.8:
            score_ratio = 10 + (ratio_p95 - 0.5) * 100  # 10-40
        elif ratio_p95 <= 1.0:
            score_ratio = 40 + (ratio_p95 - 0.8) * 200  # 40-80
        else:
            score_ratio = min(100, 80 + (ratio_p95 - 1.0) * 100)  # 80-100

        # --- Factor 2: Depassement frequency ---
        depassements = []
        depassement_count = 0
        for r in readings:
            p_kw = r["value_kwh"] / hours_per_interval
            if p_kw > p_sub:
                depassement_count += 1
                depassements.append(
                    {
                        "timestamp": r["timestamp"].isoformat()
                        if hasattr(r["timestamp"], "isoformat")
                        else str(r["timestamp"]),
                        "power_kw": round(p_kw, 2),
                        "subscribed_kva": round(p_sub, 2),
                        "excess_pct": round((p_kw / p_sub - 1) * 100, 1),
                    }
                )

        depassement_rate = depassement_count / len(readings) if readings else 0
        # Score: 0% = 0, >5% = 100
        score_depassement = min(100, depassement_rate * 2000)  # 5% -> 100

        # --- Factor 3: Volatility (CV) ---
        if pmean > 0 and len(powers_kw) > 1:
            variance = sum((p - pmean) ** 2 for p in powers_kw) / len(powers_kw)
            std_dev = variance**0.5
            cv = std_dev / pmean
        else:
            cv = 0
        # Score: CV < 0.3 = low risk, CV > 1.0 = high risk
        score_volatility = min(100, max(0, (cv - 0.2) * 125))

        # --- Factor 4: Peak concentration ---
        # How many of the top 1% readings cluster within short windows
        if len(powers_kw) > 10:
            threshold_top = sorted(powers_kw, reverse=True)[max(1, len(powers_kw) // 100)]
            peaks_indices = [i for i, p in enumerate(powers_kw) if p >= threshold_top]
            if len(peaks_indices) > 1:
                gaps = [peaks_indices[i + 1] - peaks_indices[i] for i in range(len(peaks_indices) - 1)]
                avg_gap = sum(gaps) / len(gaps)
                # Smaller gaps = more concentrated peaks = higher risk
                score_peak_conc = min(100, max(0, (10 - avg_gap) * 12.5))
            else:
                score_peak_conc = 0
        else:
            score_peak_conc = 0

        # --- Weighted total ---
        risk_score = (
            score_ratio * self.WEIGHT_RATIO
            + score_depassement * self.WEIGHT_DEPASSEMENT
            + score_volatility * self.WEIGHT_VOLATILITY
            + score_peak_conc * self.WEIGHT_PEAK_CONC
        )
        risk_score = round(min(100, max(0, risk_score)), 1)

        # Risk level
        if risk_score >= 80:
            level = "critical"
        elif risk_score >= 60:
            level = "high"
        elif risk_score >= 35:
            level = "medium"
        else:
            level = "low"

        return {
            "risk_score": risk_score,
            "risk_level": level,
            "subscribed_power_kva": round(p_sub, 2),
            "ratio_p95_psub": round(ratio_p95, 4),
            "depassement_count": depassement_count,
            "depassement_rate_pct": round(depassement_rate * 100, 2),
            "volatility_cv": round(cv, 4),
            "details": {
                "score_ratio": round(score_ratio, 1),
                "score_depassement": round(score_depassement, 1),
                "score_volatility": round(score_volatility, 1),
                "score_peak_concentration": round(score_peak_conc, 1),
            },
            "depassements": depassements[:50],  # Limit to 50 for API response
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "risk_score": 0,
            "risk_level": "low",
            "subscribed_power_kva": 0,
            "ratio_p95_psub": 0,
            "depassement_count": 0,
            "depassement_rate_pct": 0,
            "volatility_cv": 0,
            "details": {
                "score_ratio": 0,
                "score_depassement": 0,
                "score_volatility": 0,
                "score_peak_concentration": 0,
            },
            "depassements": [],
        }
