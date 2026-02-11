"""
PROMEOS Electric Monitoring - KPI Engine
Calculates expert-level electricity KPIs from meter readings.

KPIs computed:
- Pmax, P95, P99, Pmean, Pbase (talon), Pbase_night
- Load factor, Peak-to-average ratio
- Weekend ratio, Night ratio
- Weekday/Weekend hourly profiles (jour-type)
- Monthly consumption breakdown
- Ramp rates (max delta P between consecutive readings)
"""
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


class KPIEngine:
    """Compute expert electricity KPIs from time-series readings."""

    def compute(self, readings: List[Dict[str, Any]],
                interval_minutes: int = 60) -> Dict[str, Any]:
        """
        Compute all KPIs from a list of readings.

        Args:
            readings: list of {timestamp: datetime, value_kwh: float}
            interval_minutes: step size in minutes (15, 30, 60)

        Returns:
            dict of KPI values
        """
        if not readings:
            return self._empty_kpis()

        # Sort by timestamp
        readings = sorted(readings, key=lambda r: r["timestamp"])

        values = [r["value_kwh"] for r in readings]
        timestamps = [r["timestamp"] for r in readings]

        # Convert energy (kWh) to power (kW)
        hours_per_interval = interval_minutes / 60.0
        powers_kw = [v / hours_per_interval for v in values]

        # Basic power stats
        pmax = max(powers_kw)
        pmean = sum(powers_kw) / len(powers_kw)
        p95 = self._percentile(powers_kw, 95)
        p99 = self._percentile(powers_kw, 99)
        p10 = self._percentile(powers_kw, 10)

        # Base load (talon) = P10
        pbase = p10

        # Night base (00:00-05:00)
        night_powers = [p for p, ts in zip(powers_kw, timestamps)
                        if 0 <= ts.hour < 5]
        pbase_night = self._percentile(night_powers, 10) if night_powers else pbase

        # Load factor
        total_hours = len(readings) * hours_per_interval
        total_kwh = sum(values)
        load_factor = total_kwh / (pmax * total_hours) if pmax > 0 and total_hours > 0 else 0

        # Peak-to-average
        peak_to_avg = pmax / pmean if pmean > 0 else 0

        # Weekend vs weekday energy
        we_kwh = sum(v for v, ts in zip(values, timestamps) if ts.weekday() >= 5)
        wd_kwh = sum(v for v, ts in zip(values, timestamps) if ts.weekday() < 5)
        we_count = sum(1 for ts in timestamps if ts.weekday() >= 5)
        wd_count = sum(1 for ts in timestamps if ts.weekday() < 5)

        we_avg = we_kwh / max(we_count, 1)
        wd_avg = wd_kwh / max(wd_count, 1)
        weekend_ratio = we_avg / wd_avg if wd_avg > 0 else 0

        # Night ratio (22:00-06:00 vs total)
        night_kwh = sum(v for v, ts in zip(values, timestamps)
                        if ts.hour >= 22 or ts.hour < 6)
        night_ratio = night_kwh / total_kwh if total_kwh > 0 else 0

        # Hourly profiles (jour-type)
        weekday_profile = self._hourly_profile(readings, weekend=False, interval_minutes=interval_minutes)
        weekend_profile = self._hourly_profile(readings, weekend=True, interval_minutes=interval_minutes)

        # Monthly breakdown
        monthly_kwh = defaultdict(float)
        for r in readings:
            key = f"{r['timestamp'].year}-{r['timestamp'].month:02d}"
            monthly_kwh[key] += r["value_kwh"]

        # Ramp rate (max power change between consecutive readings)
        ramp_rates = []
        for i in range(1, len(powers_kw)):
            delta_p = abs(powers_kw[i] - powers_kw[i - 1])
            ramp_rates.append(delta_p)
        ramp_rate_max = max(ramp_rates) if ramp_rates else 0

        return {
            "pmax_kw": round(pmax, 2),
            "p95_kw": round(p95, 2),
            "p99_kw": round(p99, 2),
            "pmean_kw": round(pmean, 2),
            "pbase_kw": round(pbase, 2),
            "pbase_night_kw": round(pbase_night, 2),
            "load_factor": round(load_factor, 4),
            "peak_to_average": round(peak_to_avg, 2),
            "weekend_ratio": round(weekend_ratio, 4),
            "night_ratio": round(night_ratio, 4),
            "total_kwh": round(total_kwh, 2),
            "readings_count": len(readings),
            "interval_minutes": interval_minutes,
            "ramp_rate_max_kw_h": round(ramp_rate_max / hours_per_interval, 2) if hours_per_interval > 0 else 0,
            "weekday_profile_kw": weekday_profile,
            "weekend_profile_kw": weekend_profile,
            "monthly_kwh": dict(monthly_kwh),
        }

    def _percentile(self, data: List[float], pct: float) -> float:
        """Compute percentile without numpy."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * pct / 100.0
        f = int(k)
        c = f + 1
        if c >= len(sorted_data):
            return sorted_data[-1]
        d0 = sorted_data[f] * (c - k)
        d1 = sorted_data[c] * (k - f)
        return round(d0 + d1, 4)

    def _hourly_profile(self, readings: List[Dict], weekend: bool,
                        interval_minutes: int = 60) -> List[float]:
        """Compute average power (kW) by hour of day."""
        hours_per_interval = interval_minutes / 60.0
        by_hour = defaultdict(list)

        for r in readings:
            ts = r["timestamp"]
            is_we = ts.weekday() >= 5
            if is_we == weekend:
                power_kw = r["value_kwh"] / hours_per_interval
                by_hour[ts.hour].append(power_kw)

        profile = []
        for h in range(24):
            vals = by_hour.get(h, [])
            avg = sum(vals) / len(vals) if vals else 0
            profile.append(round(avg, 2))

        return profile

    def _empty_kpis(self) -> Dict[str, Any]:
        return {
            "pmax_kw": 0, "p95_kw": 0, "p99_kw": 0, "pmean_kw": 0,
            "pbase_kw": 0, "pbase_night_kw": 0,
            "load_factor": 0, "peak_to_average": 0,
            "weekend_ratio": 0, "night_ratio": 0,
            "total_kwh": 0, "readings_count": 0, "interval_minutes": 60,
            "ramp_rate_max_kw_h": 0,
            "weekday_profile_kw": [0] * 24,
            "weekend_profile_kw": [0] * 24,
            "monthly_kwh": {},
        }
