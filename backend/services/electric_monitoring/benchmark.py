"""
PROMEOS - Benchmark Utility
Percentile computation for peer-group KPI comparison.
"""
from typing import List, Dict, Optional
import math


def compute_percentiles(values: List[float]) -> Dict[str, float]:
    """Compute p25, p50, p75 for a sorted list of values."""
    if not values:
        return {"p25": 0, "p50": 0, "p75": 0}
    s = sorted(values)
    n = len(s)

    def _pct(p):
        k = (n - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return s[int(k)]
        return s[f] * (c - k) + s[c] * (k - f)

    return {
        "p25": round(_pct(0.25), 2),
        "p50": round(_pct(0.50), 2),
        "p75": round(_pct(0.75), 2),
    }


def compute_rank(target: float, values: List[float]) -> int:
    """Compute percentile rank (0-100) of target within values."""
    if not values:
        return 50
    below = sum(1 for v in values if v < target)
    equal = sum(1 for v in values if v == target)
    rank = (below + equal * 0.5) / len(values) * 100
    return int(round(rank))


def build_benchmark(
    target_kpis: Dict[str, Optional[float]],
    peer_kpis_list: List[Dict[str, Optional[float]]],
    kpi_keys: List[str],
) -> Dict[str, Optional[Dict]]:
    """
    Build benchmark comparison for given KPI keys.
    Returns dict of kpi_key → { value, percentile, p25, p50, p75 } or None.
    """
    result = {}
    for key in kpi_keys:
        target_val = target_kpis.get(key)
        if target_val is None:
            result[key] = None
            continue

        peer_vals = [pk[key] for pk in peer_kpis_list if pk.get(key) is not None]
        if len(peer_vals) < 2:
            result[key] = None
            continue

        pcts = compute_percentiles(peer_vals)
        rank = compute_rank(target_val, peer_vals)
        result[key] = {
            "value": round(target_val, 2),
            "percentile": rank,
            **pcts,
        }
    return result
