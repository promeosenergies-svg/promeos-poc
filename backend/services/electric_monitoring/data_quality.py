"""
PROMEOS Electric Monitoring - Data Quality Engine
Computes data quality score (0-100) from meter readings.

Quality checks:
- Gaps (missing readings)
- Duplicates (same timestamp)
- DST collisions (spring forward ambiguity)
- Negative values
- Outliers (statistical anomalies)
- Completeness (% of expected readings present)
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import Counter


class DataQualityEngine:
    """Compute data quality score from time-series readings."""

    # Penalty weights (sum = 1.0)
    WEIGHT_COMPLETENESS = 0.35
    WEIGHT_GAPS = 0.25
    WEIGHT_DUPLICATES = 0.15
    WEIGHT_NEGATIVES = 0.15
    WEIGHT_OUTLIERS = 0.10

    def compute(self, readings: List[Dict[str, Any]],
                interval_minutes: int = 60,
                period_start: Optional[datetime] = None,
                period_end: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Compute data quality score.

        Args:
            readings: list of {timestamp: datetime, value_kwh: float}
            interval_minutes: expected interval between readings
            period_start/end: expected coverage period

        Returns:
            dict with quality_score (0-100), issues list, details
        """
        if not readings:
            return self._empty_result()

        readings = sorted(readings, key=lambda r: r["timestamp"])
        timestamps = [r["timestamp"] for r in readings]
        values = [r["value_kwh"] for r in readings]

        issues = []

        # --- 1. Completeness ---
        if period_start is None:
            period_start = timestamps[0]
        if period_end is None:
            period_end = timestamps[-1]

        total_span_minutes = (period_end - period_start).total_seconds() / 60.0
        expected_readings = int(total_span_minutes / interval_minutes) + 1 if interval_minutes > 0 else len(readings)
        completeness_pct = min(100, (len(readings) / max(expected_readings, 1)) * 100)
        score_completeness = completeness_pct  # 0-100

        if completeness_pct < 95:
            issues.append({
                "type": "incomplete_data",
                "severity": "warning" if completeness_pct > 80 else "high",
                "detail": f"Completeness {completeness_pct:.1f}%: {len(readings)}/{expected_readings} readings",
                "value": round(completeness_pct, 1)
            })

        # --- 2. Gaps ---
        gap_count = 0
        gap_total_hours = 0.0
        max_gap_hours = 0.0
        gaps_list = []

        interval_td = timedelta(minutes=interval_minutes)
        tolerance = timedelta(minutes=interval_minutes * 1.5)

        for i in range(1, len(timestamps)):
            delta = timestamps[i] - timestamps[i - 1]
            if delta > tolerance:
                gap_hours = delta.total_seconds() / 3600.0
                gap_count += 1
                gap_total_hours += gap_hours
                max_gap_hours = max(max_gap_hours, gap_hours)
                if len(gaps_list) < 20:
                    gaps_list.append({
                        "start": timestamps[i - 1].isoformat(),
                        "end": timestamps[i].isoformat(),
                        "duration_hours": round(gap_hours, 1)
                    })

        # Score: 0 gaps = 100, 1 gap per day on average = 0
        total_days = max(1, total_span_minutes / (24 * 60))
        gaps_per_day = gap_count / total_days
        score_gaps = max(0, 100 - gaps_per_day * 50)

        if gap_count > 0:
            issues.append({
                "type": "gaps",
                "severity": "high" if max_gap_hours > 24 else "warning",
                "detail": f"{gap_count} gaps detected, total {gap_total_hours:.1f}h, max {max_gap_hours:.1f}h",
                "value": gap_count
            })

        # --- 3. Duplicates ---
        ts_counter = Counter(ts.isoformat() for ts in timestamps)
        duplicate_count = sum(c - 1 for c in ts_counter.values() if c > 1)
        duplicate_timestamps = [ts for ts, c in ts_counter.items() if c > 1]

        duplicate_rate = duplicate_count / max(len(readings), 1)
        score_duplicates = max(0, 100 - duplicate_rate * 5000)  # 2% duplicates = 0

        if duplicate_count > 0:
            issues.append({
                "type": "duplicates",
                "severity": "warning",
                "detail": f"{duplicate_count} duplicate timestamps found",
                "value": duplicate_count,
                "examples": duplicate_timestamps[:10]
            })

        # --- 4. DST collisions ---
        dst_collisions = 0
        for i in range(1, len(timestamps)):
            # Detect when clock goes back (DST fall back)
            if timestamps[i] < timestamps[i - 1]:
                dst_collisions += 1

        # Also detect spring forward (missing hour typically 2:00-3:00 in March)
        spring_gaps = 0
        for g in gaps_list:
            start_dt = datetime.fromisoformat(g["start"])
            if start_dt.month == 3 and 1.0 <= g["duration_hours"] <= 1.5:
                spring_gaps += 1

        if dst_collisions > 0 or spring_gaps > 0:
            issues.append({
                "type": "dst_collision",
                "severity": "info",
                "detail": f"DST issues: {dst_collisions} backward jumps, {spring_gaps} spring-forward gaps",
                "value": dst_collisions + spring_gaps
            })

        # --- 5. Negatives ---
        negative_count = sum(1 for v in values if v < 0)
        negative_rate = negative_count / max(len(values), 1)
        score_negatives = max(0, 100 - negative_rate * 10000)  # 1% negatives = 0

        if negative_count > 0:
            issues.append({
                "type": "negative_values",
                "severity": "high",
                "detail": f"{negative_count} negative readings detected",
                "value": negative_count
            })

        # --- 6. Outliers (IQR method) ---
        sorted_vals = sorted(v for v in values if v >= 0)
        if len(sorted_vals) > 10:
            q1_idx = len(sorted_vals) // 4
            q3_idx = 3 * len(sorted_vals) // 4
            q1 = sorted_vals[q1_idx]
            q3 = sorted_vals[q3_idx]
            iqr = q3 - q1
            lower = q1 - 3.0 * iqr
            upper = q3 + 3.0 * iqr
            outlier_count = sum(1 for v in values if v < lower or v > upper)
        else:
            outlier_count = 0

        outlier_rate = outlier_count / max(len(values), 1)
        score_outliers = max(0, 100 - outlier_rate * 2000)  # 5% outliers = 0

        if outlier_count > 0:
            issues.append({
                "type": "outliers",
                "severity": "warning",
                "detail": f"{outlier_count} statistical outliers (IQR x3)",
                "value": outlier_count
            })

        # --- Weighted total ---
        quality_score = (
            score_completeness * self.WEIGHT_COMPLETENESS +
            score_gaps * self.WEIGHT_GAPS +
            score_duplicates * self.WEIGHT_DUPLICATES +
            score_negatives * self.WEIGHT_NEGATIVES +
            score_outliers * self.WEIGHT_OUTLIERS
        )
        quality_score = round(min(100, max(0, quality_score)), 1)

        # Quality level
        if quality_score >= 90:
            level = "excellent"
        elif quality_score >= 75:
            level = "good"
        elif quality_score >= 50:
            level = "fair"
        else:
            level = "poor"

        return {
            "quality_score": quality_score,
            "quality_level": level,
            "completeness_pct": round(completeness_pct, 1),
            "total_readings": len(readings),
            "expected_readings": expected_readings,
            "gap_count": gap_count,
            "gap_total_hours": round(gap_total_hours, 1),
            "max_gap_hours": round(max_gap_hours, 1),
            "duplicate_count": duplicate_count,
            "dst_collisions": dst_collisions,
            "negative_count": negative_count,
            "outlier_count": outlier_count,
            "details": {
                "score_completeness": round(score_completeness, 1),
                "score_gaps": round(score_gaps, 1),
                "score_duplicates": round(score_duplicates, 1),
                "score_negatives": round(score_negatives, 1),
                "score_outliers": round(score_outliers, 1),
            },
            "issues": issues,
            "gaps": gaps_list,
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "quality_score": 0,
            "quality_level": "poor",
            "completeness_pct": 0,
            "total_readings": 0,
            "expected_readings": 0,
            "gap_count": 0,
            "gap_total_hours": 0,
            "max_gap_hours": 0,
            "duplicate_count": 0,
            "dst_collisions": 0,
            "negative_count": 0,
            "outlier_count": 0,
            "details": {
                "score_completeness": 0,
                "score_gaps": 0,
                "score_duplicates": 0,
                "score_negatives": 0,
                "score_outliers": 0,
            },
            "issues": [],
            "gaps": [],
        }
