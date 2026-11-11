"""
AMRShield - AMR Prediction Agent (baseline forecaster)

What this module is:
  A transparent, deterministic BASELINE forecaster for resistance trends,
  using Holt's linear-trend exponential smoothing.

Data:
  - REAL: annual EARS-Net resistance percentages for 30 EU/EEA countries
    (ECDC Surveillance Atlas, data/surveillance/ecdc_ears_net_resistance.csv,
    built by scripts/build_ecdc_dataset.py). Used whenever the country /
    pathogen / antibiotic group is covered.
  - SYNTHETIC: WHO GLASS-style monthly series, used only for countries ECDC
    does not cover (e.g. India, USA) and clearly labelled as demo data.

What this module is NOT:
  - It is not a trained ML model. `backtest_holt` reports how the baseline
    compares with a naive "same as last year" forecast on real data.
"""

from __future__ import annotations

import math
import zlib
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

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


def holt_forecast(
    series: pd.Series, horizon: int, alpha: float = ALPHA, beta: float = BETA, phi: float = 1.0
) -> dict:
    """
    Holt's linear-trend exponential smoothing; phi < 1 gives the damped-trend
    variant, where the trend fades over the horizon instead of growing forever.
    Returns point forecasts, an approximate 80% interval and in-sample fit error.
    """
    y = np.asarray(series, dtype=float)
    if len(y) < 3:
        raise ValueError("Need at least 3 observations for Holt smoothing")

    level, trend = y[0], y[1] - y[0]
    fitted = [y[0]]
    for obs in y[1:]:
        fitted.append(level + phi * trend)         # one-step-ahead prediction
        prev_level = level
        level = alpha * obs + (1 - alpha) * (level + phi * trend)
        trend = beta * (level - prev_level) + (1 - beta) * phi * trend

    residuals = y[1:] - np.asarray(fitted[1:])
    sigma = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0
    mae = float(np.mean(np.abs(residuals)))

    steps = np.arange(1, horizon + 1)
    damp = np.cumsum(phi ** steps)                 # = steps when phi == 1
    point = np.clip(level + damp * trend, 0, 100)
    half_width = 1.28 * sigma * np.sqrt(steps)     # rough 80% band, widens with horizon
    return {
        "point": np.round(point, 1).tolist(),
        "lower_80": np.round(np.clip(point - half_width, 0, 100), 1).tolist(),
        "upper_80": np.round(np.clip(point + half_width, 0, 100), 1).tolist(),
        "monthly_trend_pp": round(float(trend), 2),
        "in_sample_mae_pp": round(mae, 2),
    }


# ─────────────────────────────────────────────────────────────
# Real surveillance data (ECDC EARS-Net, annual)
# ─────────────────────────────────────────────────────────────
ECDC_PATH = Path(__file__).resolve().parents[2] / "data" / "surveillance" / "ecdc_ears_net_resistance.csv"
ECDC_SOURCE = "ECDC Surveillance Atlas (EARS-Net), R - resistant isolates %, annual"
MIN_REAL_YEARS = 5
# Damped-trend settings for annual real data. Chosen on half of the ECDC
# countries and checked on the other half (one-step-ahead MAE):
#   damped Holt 2.16 pp | naive "same as last year" 2.16 pp | old Holt (0.5, 0.2) 2.76 pp
REAL_ALPHA, REAL_BETA, REAL_PHI = 0.7, 0.2, 0.5

PATHOGEN_ALIASES = {
    "e. coli": "E. coli", "escherichia coli": "E. coli", "ecoli": "E. coli",
    "k. pneumoniae": "K. pneumoniae", "klebsiella pneumoniae": "K. pneumoniae", "klebsiella": "K. pneumoniae",
    "mrsa": "MRSA", "s. aureus": "MRSA", "staphylococcus aureus": "MRSA",
}
# Default antibiotic group per pathogen when the caller does not choose one
DEFAULT_GROUP = {
    "E. coli": "Fluoroquinolones",
    "K. pneumoniae": "Third-generation cephalosporins",
    "MRSA": "Meticillin (MRSA)",
}


@lru_cache(maxsize=1)
def load_surveillance() -> pd.DataFrame:
    """Tidy ECDC table; empty frame if the data file is missing."""
    if not ECDC_PATH.exists():
        return pd.DataFrame(columns=["country_code", "country", "pathogen", "antibiotic_group", "year", "resistance_pct"])
    return pd.read_csv(ECDC_PATH)


def real_history(country: str, pathogen: str, antibiotic_group: str | None = None) -> pd.Series | None:
    """
    Annual real resistance series for a country (name or ISO code), or None.
    A single missing year is filled by linear interpolation (and counted in
    attrs["imputed_years"]); a gap of 2+ years cuts the series, keeping the
    most recent stretch so Holt never smooths across a long reporting gap.
    """
    df = load_surveillance()
    pathogen = PATHOGEN_ALIASES.get(str(pathogen).strip().lower(), pathogen)
    group = antibiotic_group or DEFAULT_GROUP.get(pathogen)
    c = str(country).strip().lower()
    c = {"gr": "el", "gb": "uk", "united kingdom": "uk"}.get(c, c)
    rows = df[
        ((df["country"].str.lower() == c) | (df["country_code"].str.lower() == c))
        & (df["pathogen"] == pathogen)
        & (df["antibiotic_group"].str.lower() == str(group).lower())
    ].sort_values("year")
    if rows.empty:
        return None

    years = rows["year"].to_numpy()
    breaks = np.where(np.diff(years) > 2)[0]       # gap of 2+ missing years
    start = breaks[-1] + 1 if len(breaks) else 0
    rows = rows.iloc[start:]

    s = pd.Series(rows["resistance_pct"].to_numpy(dtype=float), index=rows["year"].to_numpy())
    full = s.reindex(range(int(s.index.min()), int(s.index.max()) + 1))
    imputed = int(full.isna().sum())
    full = full.interpolate(method="linear").round(2)
    if len(full) < MIN_REAL_YEARS:
        return None
    out = pd.Series(full.to_numpy(), index=full.index.astype(str), name="resistance_pct")
    out.attrs["antibiotic_group"] = rows["antibiotic_group"].iloc[0]
    out.attrs["imputed_years"] = imputed
    return out


def backtest_holt(series: pd.Series, min_train: int = MIN_REAL_YEARS) -> dict | None:
    """
    Rolling-origin, one-step-ahead backtest on a real series.
    Compares Holt with the naive forecast (next value = last value).
    """
    if series is None:
        return None
    y = np.asarray(series, dtype=float)
    if len(y) <= min_train:
        return None
    holt_err, naive_err = [], []
    for t in range(min_train, len(y)):
        pred = holt_forecast(pd.Series(y[:t]), 1, REAL_ALPHA, REAL_BETA, REAL_PHI)["point"][0]
        holt_err.append(abs(pred - y[t]))
        naive_err.append(abs(y[t - 1] - y[t]))
    return {
        "n_forecasts": len(holt_err),
        "holt_mae_pp": round(float(np.mean(holt_err)), 2),
        "naive_mae_pp": round(float(np.mean(naive_err)), 2),
    }


def run_prediction_agent(
    country: str,
    pathogen: str,
    horizon_months: int = 6,
    antibiotic_group: str | None = None,
) -> dict:
    """
    Forecast resistance % for a country/pathogen pair (deterministic baseline).
    Real annual ECDC data are used when available; otherwise a labelled
    synthetic monthly series.
    """
    real = real_history(country, pathogen, antibiotic_group)
    if real is not None:
        return _forecast_real(country, pathogen, real, horizon_months)

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
            {"period": m, "month": m, "resistance_pct": p, "lower_80": lo, "upper_80": hi}
            for m, p, lo, hi in zip(forecast_months, fc["point"], fc["lower_80"], fc["upper_80"])
        ],
        "horizon_months": horizon_months,
        "trend": trend,
        "monthly_trend_pp": slope,
        "in_sample_mae_pp": fc["in_sample_mae_pp"],
        "method": f"Holt linear-trend exponential smoothing (alpha={ALPHA}, beta={BETA}) — baseline",
        "frequency": "monthly",
        "data_source": "SYNTHETIC WHO GLASS-style series (demo only, not real surveillance data)",
        "real_data": False,
        "validated": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _forecast_real(country: str, pathogen: str, history: pd.Series, horizon_months: int) -> dict:
    """Annual forecast on real ECDC data; horizon is rounded up to whole years."""
    horizon_years = max(1, math.ceil(horizon_months / 12))
    fc = holt_forecast(history, horizon_years, REAL_ALPHA, REAL_BETA, REAL_PHI)
    last_year = int(history.index[-1])
    years = [str(last_year + i) for i in range(1, horizon_years + 1)]

    slope = fc["monthly_trend_pp"]          # per step; steps are years here
    trend = "increasing" if slope > 0.1 else "decreasing" if slope < -0.1 else "stable"

    return {
        "country": country,
        "pathogen": PATHOGEN_ALIASES.get(str(pathogen).strip().lower(), pathogen),
        "antibiotic_group": history.attrs.get("antibiotic_group"),
        "current_resistance_pct": float(history.iloc[-1]),
        "latest_year": last_year,
        "imputed_years": history.attrs.get("imputed_years", 0),
        "history": [{"period": y, "resistance_pct": float(v)} for y, v in history.items()],
        "forecast": [
            {"period": y, "resistance_pct": p, "lower_80": lo, "upper_80": hi}
            for y, p, lo, hi in zip(years, fc["point"], fc["lower_80"], fc["upper_80"])
        ],
        "frequency": "annual",
        "horizon_years": horizon_years,
        "trend": trend,
        "annual_trend_pp": slope,
        "in_sample_mae_pp": fc["in_sample_mae_pp"],
        "backtest": backtest_holt(history),
        "method": (f"Damped-trend Holt smoothing (alpha={REAL_ALPHA}, beta={REAL_BETA}, phi={REAL_PHI}) — "
                   "baseline; matches but does not beat the naive forecast on held-out ECDC data"),
        "data_source": ECDC_SOURCE,
        "real_data": True,
        "validated": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
