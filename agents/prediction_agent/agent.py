"""
AMRShield - AMR Prediction Agent (baseline forecaster)

What this module is:
  A transparent, deterministic BASELINE forecaster for resistance trends,
  using Holt's linear-trend exponential smoothing.

What this module is NOT:
  - It is not a trained ML model and makes no accuracy claim.
  - It does not call the live WHO GLASS API. All series are SYNTHETIC,
    WHO GLASS-style values generated for demonstration only.

Planned next step:
  Replace the synthetic series with real WHO GLASS country/pathogen data and
  benchmark Holt against ARIMA / Prophet using rolling-origin backtesting
  (MAE / MAPE), keeping Holt as the baseline the better model must beat.
"""

from __future__ import annotations

import zlib
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────
# Synthetic, WHO GLASS-style reference values (NOT real data)
# current resistance %, assumed annual change in percentage points
# ─────────────────────────────────────────────────────────────
SYNTHETIC_BASELINE = {
    "India":      {"E. coli": (68, 2.0), "MRSA": (45, 1.2), "K. pneumoniae": (61, 2.4)},
    "Bangladesh": {"E. coli": (72, 2.2), "MRSA": (48, 1.4), "K. pneumoniae": (65, 2.6)},
    "USA":        {"E. coli": (22, 0.6), "MRSA": (31, -0.8), "K. pneumoniae": (18, 0.5)},
    "Germany":    {"E. coli": (18, 0.3), "MRSA": (12, -0.5), "K. pneumoniae": (14, 0.4)},
}
DEFAULT_BASELINE = (40, 1.0)

# Fixed smoothing parameters (documented, not tuned on any real data)
ALPHA = 0.5   # level smoothing
BETA = 0.2    # trend smoothing
HISTORY_MONTHS = 24


def _stable_seed(*parts: str) -> int:
    """Deterministic seed (Python's hash() is randomised per process)."""
    return zlib.crc32("|".join(parts).encode("utf-8"))


def synthetic_history(
    country: str,
    pathogen: str,
    months: int = HISTORY_MONTHS,
    current: float | None = None,
    annual_change: float | None = None,
) -> pd.Series:
    """
    Build a reproducible synthetic monthly resistance series ending at the
    current month. Same inputs always give the same series.
    `current` / `annual_change` override the reference table (used by dashboards).
    """
    ref_current, ref_change = SYNTHETIC_BASELINE.get(country, {}).get(pathogen, DEFAULT_BASELINE)
    current = ref_current if current is None else current
    annual_change = ref_change if annual_change is None else annual_change
    rng = np.random.default_rng(_stable_seed(country, pathogen))

    t = np.arange(-months + 1, 1)                  # ..., -2, -1, 0  (0 = current month)
    trend = current + annual_change * t / 12.0
    noise = rng.normal(0.0, 0.6, months)
    noise[-1] = 0.0                                # anchor last point at the reference value
    values = np.clip(trend + noise, 0, 100)

    end = pd.Timestamp(datetime.now(timezone.utc).date()).to_period("M")
    index = pd.period_range(end=end, periods=months, freq="M").astype(str)
    return pd.Series(np.round(values, 1), index=index, name="resistance_pct")


def holt_forecast(series: pd.Series, horizon: int, alpha: float = ALPHA, beta: float = BETA) -> dict:
    """
    Holt's linear-trend exponential smoothing.
    Returns point forecasts, an approximate 80% interval and in-sample fit error.
    """
    y = np.asarray(series, dtype=float)
    if len(y) < 3:
        raise ValueError("Need at least 3 observations for Holt smoothing")

    level, trend = y[0], y[1] - y[0]
    fitted = [y[0]]
    for obs in y[1:]:
        fitted.append(level + trend)               # one-step-ahead prediction
        prev_level = level
        level = alpha * obs + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend

    residuals = y[1:] - np.asarray(fitted[1:])
    sigma = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0
    mae = float(np.mean(np.abs(residuals)))

    steps = np.arange(1, horizon + 1)
    point = np.clip(level + steps * trend, 0, 100)
    half_width = 1.28 * sigma * np.sqrt(steps)     # rough 80% band, widens with horizon
    return {
        "point": np.round(point, 1).tolist(),
        "lower_80": np.round(np.clip(point - half_width, 0, 100), 1).tolist(),
        "upper_80": np.round(np.clip(point + half_width, 0, 100), 1).tolist(),
        "monthly_trend_pp": round(float(trend), 2),
        "in_sample_mae_pp": round(mae, 2),
    }


def run_prediction_agent(country: str, pathogen: str, horizon_months: int = 6) -> dict:
    """Forecast resistance % for a country/pathogen pair (deterministic baseline)."""
    history = synthetic_history(country, pathogen)
    fc = holt_forecast(history, horizon_months)

    last = pd.Period(history.index[-1], freq="M")
    forecast_months = [str(last + i) for i in range(1, horizon_months + 1)]

    slope = fc["monthly_trend_pp"]
    trend = "increasing" if slope > 0.05 else "decreasing" if slope < -0.05 else "stable"

    return {
        "country": country,
        "pathogen": pathogen,
        "current_resistance_pct": float(history.iloc[-1]),
        "history": [{"month": m, "resistance_pct": float(v)} for m, v in history.items()],
        "forecast": [
            {"month": m, "resistance_pct": p, "lower_80": lo, "upper_80": hi}
            for m, p, lo, hi in zip(forecast_months, fc["point"], fc["lower_80"], fc["upper_80"])
        ],
        "horizon_months": horizon_months,
        "trend": trend,
        "monthly_trend_pp": slope,
        "in_sample_mae_pp": fc["in_sample_mae_pp"],
        "method": f"Holt linear-trend exponential smoothing (alpha={ALPHA}, beta={BETA}) — baseline",
        "data_source": "SYNTHETIC WHO GLASS-style series (demo only, not real surveillance data)",
        "validated": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
