"""
PROMEOS - EMS Energy Signature Service
Piecewise change-point model: y = base + a*max(0, Tb-T) + b*max(0, T-Tc)
Grid search on Tb/Tc + least squares via numpy.
Model selection via adjusted R² (heating-only, cooling-only, full).
"""
from typing import List, Dict, Any
import numpy as np


def _bic(ss_res: float, n: int, k: int) -> float:
    """Bayesian Information Criterion. k = total params (incl. intercept). Lower is better."""
    if ss_res <= 0 or n <= 0:
        return np.inf
    return n * np.log(ss_res / n) + k * np.log(n)


def _fit_lstsq(X: np.ndarray, y: np.ndarray):
    """Fit via least squares, return coefficients or None on failure."""
    try:
        coeffs, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
        return coeffs
    except np.linalg.LinAlgError:
        return None


MIN_ACTIVE_POINTS = 5


def run_signature(
    daily_kwh: List[float],
    daily_temp: List[float],
) -> Dict[str, Any]:
    """Fit energy signature model to daily (kwh, temp) pairs.

    Tries three model families and picks the best via BIC (parsimony):
    - Heating-only: y = base + a * max(0, Tb - T)
    - Cooling-only: y = base + b * max(0, T - Tc)
    - Full:         y = base + a * max(0, Tb - T) + b * max(0, T - Tc)
    """
    if len(daily_kwh) != len(daily_temp) or len(daily_kwh) < 10:
        return {"error": "insufficient_data", "n_points": len(daily_kwh)}

    y = np.array(daily_kwh, dtype=float)
    T = np.array(daily_temp, dtype=float)
    n = len(y)
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))

    best_bic = np.inf
    best = None  # (base, a, b, Tb, Tc, y_pred, r2)

    Tb_range = np.arange(10.0, 20.5, 0.5)
    Tc_range = np.arange(18.0, 28.5, 0.5)

    # --- Heating-only: y = base + a * max(0, Tb - T) ---
    for Tb in Tb_range:
        heating = np.maximum(0, Tb - T)
        if np.sum(heating > 0) < MIN_ACTIVE_POINTS:
            continue
        X = np.column_stack([np.ones(n), heating])
        coeffs = _fit_lstsq(X, y)
        if coeffs is None:
            continue
        base_h, a = float(coeffs[0]), max(0.0, float(coeffs[1]))
        y_pred = base_h + a * heating
        ss_res = float(np.sum((y - y_pred) ** 2))
        bic = _bic(ss_res, n, 2)  # 2 params: intercept + a
        if bic < best_bic:
            best_bic = bic
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            best = (base_h, a, 0.0, float(Tb), None, y_pred, r2)

    # --- Cooling-only: y = base + b * max(0, T - Tc) ---
    for Tc in Tc_range:
        cooling = np.maximum(0, T - Tc)
        if np.sum(cooling > 0) < MIN_ACTIVE_POINTS:
            continue
        X = np.column_stack([np.ones(n), cooling])
        coeffs = _fit_lstsq(X, y)
        if coeffs is None:
            continue
        base_c, b = float(coeffs[0]), max(0.0, float(coeffs[1]))
        y_pred = base_c + b * cooling
        ss_res = float(np.sum((y - y_pred) ** 2))
        bic = _bic(ss_res, n, 2)  # 2 params: intercept + b
        if bic < best_bic:
            best_bic = bic
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            best = (base_c, 0.0, b, None, float(Tc), y_pred, r2)

    # --- Full model: y = base + a * max(0, Tb-T) + b * max(0, T-Tc) ---
    for Tb in Tb_range:
        for Tc in Tc_range:
            if Tc < Tb + 3:
                continue
            heating = np.maximum(0, Tb - T)
            cooling = np.maximum(0, T - Tc)
            if np.sum(heating > 0) < MIN_ACTIVE_POINTS or np.sum(cooling > 0) < MIN_ACTIVE_POINTS:
                continue
            X = np.column_stack([np.ones(n), heating, cooling])
            coeffs = _fit_lstsq(X, y)
            if coeffs is None:
                continue
            base_f, a, b = float(coeffs[0]), max(0.0, float(coeffs[1])), max(0.0, float(coeffs[2]))
            y_pred = base_f + a * heating + b * cooling
            ss_res = float(np.sum((y - y_pred) ** 2))
            bic = _bic(ss_res, n, 3)  # 3 params: intercept + a + b
            if bic < best_bic:
                best_bic = bic
                r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
                best = (base_f, a, b, float(Tb), float(Tc), y_pred, r2)

    if best is None:
        return {"error": "no_fit", "n_points": n}

    base, a, b, Tb, Tc, y_pred, r2 = best

    # Classify — threshold 1.5 kWh/°C: below this, slope is not physically meaningful
    SLOPE_THRESHOLD = 1.5
    if a > SLOPE_THRESHOLD and b < SLOPE_THRESHOLD:
        label = "heating_dominant"
    elif b > SLOPE_THRESHOLD and a < SLOPE_THRESHOLD:
        label = "cooling_dominant"
    elif a > SLOPE_THRESHOLD and b > SLOPE_THRESHOLD:
        label = "mixed"
    else:
        label = "flat"

    # Default Tb/Tc for single-slope models
    if Tb is None:
        Tb = 15.0
    if Tc is None:
        Tc = 22.0

    scatter = [
        {"T": round(float(T[i]), 1), "kwh": round(float(y[i]), 1), "predicted": round(float(y_pred[i]), 1)}
        for i in range(n)
    ]

    T_line = np.linspace(float(T.min()), float(T.max()), 50)
    pred_line = base + a * np.maximum(0, Tb - T_line) + b * np.maximum(0, T_line - Tc)
    fit_line = [
        {"T": round(float(t), 1), "predicted": round(float(p), 1)}
        for t, p in zip(T_line, pred_line)
    ]

    return {
        "base_kwh": round(base, 1),
        "a_heating": round(a, 3),
        "b_cooling": round(b, 3),
        "Tb": Tb,
        "Tc": Tc,
        "r_squared": round(r2, 4),
        "label": label,
        "n_points": n,
        "scatter": scatter,
        "fit_line": fit_line,
    }
