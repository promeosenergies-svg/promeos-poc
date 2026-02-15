"""
PROMEOS Electric Monitoring - Climate Engine
Computes climate sensitivity (kWh/j vs temperature) from readings + weather.
Aggregates hourly readings to daily kWh, then runs regression against daily avg temp.
Slope unit: (kWh/j)/°C — energy per day per degree Celsius.
Delegates to signature_service.run_signature() for the actual regression.
"""
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional

import numpy as np

from services.ems.signature_service import run_signature


def _empty_result() -> Dict[str, Any]:
    """Safe defaults when climate analysis cannot run."""
    return {
        "correlation_r": None,
        "slope_kw_per_c": None,
        "balance_point_c": None,
        "r_squared": None,
        "label": "unknown",
        "base_kwh": None,
        "a_heating": None,
        "b_cooling": None,
        "scatter": [],
        "fit_line": [],
        "n_points": 0,
    }


class ClimateEngine:
    """Compute climate sensitivity from hourly readings + daily weather."""

    def compute(
        self,
        readings: List[Dict],
        weather_data: List[Dict],
        interval_minutes: int = 60,
    ) -> Dict[str, Any]:
        """
        Args:
            readings: list of {"timestamp": datetime, "value_kwh": float}
            weather_data: list of {"date": "YYYY-MM-DD", "temp_avg_c": float, ...}
            interval_minutes: reading step (for kW conversion if needed)
        Returns:
            dict with correlation, slope, balance point, scatter, fit_line, etc.
        """
        if not readings:
            return {**_empty_result(), "reason": "no_meter"}
        if not weather_data:
            return {**_empty_result(), "reason": "no_weather"}

        # 1. Aggregate readings to daily kWh
        daily_kwh_map = defaultdict(float)
        for r in readings:
            ts = r.get("timestamp")
            if ts is None:
                continue
            if isinstance(ts, datetime):
                day_key = ts.date().isoformat()
            else:
                day_key = str(ts)[:10]
            daily_kwh_map[day_key] += r.get("value_kwh", 0) or 0

        # 2. Build weather lookup
        temp_map = {}
        for w in weather_data:
            date_str = w.get("date")
            if date_str and w.get("temp_avg_c") is not None:
                temp_map[str(date_str)[:10]] = w["temp_avg_c"]

        # 3. Match on common dates
        common_dates = sorted(set(daily_kwh_map.keys()) & set(temp_map.keys()))
        if len(common_dates) < 10:
            return {**_empty_result(), "n_points": len(common_dates), "reason": "insufficient_readings"}

        daily_kwh = [daily_kwh_map[d] for d in common_dates]
        daily_temp = [temp_map[d] for d in common_dates]

        # 4. Delegate to signature service
        sig = run_signature(daily_kwh, daily_temp)

        if sig.get("error"):
            return {**_empty_result(), "n_points": sig.get("n_points", 0), "reason": "computation_error"}

        # 5. Compute Pearson correlation
        try:
            corr_matrix = np.corrcoef(daily_temp, daily_kwh)
            correlation_r = round(float(corr_matrix[0, 1]), 4)
        except Exception:
            correlation_r = None

        # 6. Derive slope and balance point
        a_h = sig.get("a_heating", 0) or 0
        b_c = sig.get("b_cooling", 0) or 0
        slope = round(max(a_h, b_c), 3)

        label = sig.get("label", "unknown")
        if label == "heating_dominant":
            balance_point = sig.get("Tb")
        elif label == "cooling_dominant":
            balance_point = sig.get("Tc")
        elif label == "mixed":
            balance_point = sig.get("Tb")  # use heating balance as primary
        else:
            balance_point = None

        return {
            "correlation_r": correlation_r,
            "slope_kw_per_c": slope,
            "balance_point_c": balance_point,
            "r_squared": sig.get("r_squared"),
            "label": label,
            "base_kwh": sig.get("base_kwh"),
            "a_heating": sig.get("a_heating"),
            "b_cooling": sig.get("b_cooling"),
            "scatter": sig.get("scatter", []),
            "fit_line": sig.get("fit_line", []),
            "n_points": sig.get("n_points", 0),
        }
