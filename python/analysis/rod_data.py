"""
Phys 39 Module 7. Shared loading code for the rod-instrument analysis.
Naidu / Cohen

Used by rod_calibration.py, rod_step_response.py and stationary_fin_fit.py.

A rod run is the CSV written by python/rod_pi_logger.py:
    data/module_08/rod_run_YYYYMMDD_HHMMSS.csv     (base + rod columns)
    data/module_08/rod_run_YYYYMMDD_HHMMSS_notes.csv
    data/module_08/rod_run_YYYYMMDD_HHMMSS_meta.json

Rod columns are named T_<channel>_C. Positions come from
data/module_08/sensor_map.csv (position_mm, position_uncertainty_mm).
Calibration offsets, when used, come from a file written by
rod_calibration.py and are SUBTRACTED from the raw readings in memory only;
the raw CSV is never changed.
"""

import csv
import os

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(REPO, "data", "module_08")
FIG_DIR = os.path.join(REPO, "docs", "figures", "module_08")
SENSOR_MAP = os.path.join(DATA_DIR, "sensor_map.csv")


def load_run(path):
    """Columns of a rod run as numpy arrays (floats; blank -> nan), plus the
    list of rod channel names in file order."""
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit(f"{path} has no data rows")
    cols = {}
    for key in rows[0]:
        vals = []
        for r in rows:
            v = r[key]
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                vals.append(np.nan if key not in ("mode",) else v)
        cols[key] = np.array(vals, dtype=object if key == "mode" else float)
    channels = [k[2:-2] for k in rows[0] if k.startswith("T_") and k.endswith("_C")]
    return cols, channels


def load_notes(run_path):
    path = run_path[:-4] + "_notes.csv"
    if not os.path.exists(path):
        return []
    with open(path, newline="") as fh:
        return [(float(r["time_s"]) if r["time_s"] else np.nan, r["note"])
                for r in csv.DictReader(fh)]


def load_sensor_map(path=None):
    """{channel: (x_m, dx_m)} for channels with a position filled in."""
    path = path or SENSOR_MAP
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                x = float(r["position_mm"]) / 1000.0
            except (TypeError, ValueError):
                continue
            try:
                dx = float(r["position_uncertainty_mm"]) / 1000.0
            except (TypeError, ValueError):
                dx = np.nan
            out[r["channel"].strip()] = (x, dx)
    return out


def load_offsets(path):
    """{channel: offset_C} from a rod_calibration.py output file."""
    with open(path, newline="") as fh:
        return {r["channel"]: float(r["offset_C"]) for r in csv.DictReader(fh)}


def channel_series(cols, channels, offsets=None):
    """{name: temperature array} for the base (as 'base') and every rod
    channel, with offsets subtracted if given."""
    out = {"base": cols["temperature_C"].astype(float)}
    for ch in channels:
        out[ch] = cols[f"T_{ch}_C"].astype(float)
    if offsets:
        for ch, off in offsets.items():
            if ch in out:
                out[ch] = out[ch] - off
    return out


def window(t, t0, t1):
    return (t >= t0) & (t <= t1)


def mean_and_sem(values, t):
    """Mean, sample sd, and a standard error of the mean that allows for
    correlation between neighbouring readings (lag-1 autocorrelation)."""
    v = values[np.isfinite(values)]
    if v.size < 3:
        return np.nan, np.nan, np.nan
    d = v - v.mean()
    denom = (d * d).sum()
    rho = (d[1:] * d[:-1]).sum() / denom if denom > 0 else 0.0
    rho = min(max(rho, 0.0), 0.99)
    n_eff = max(v.size * (1 - rho) / (1 + rho), 1.0)
    sd = v.std(ddof=1)
    return v.mean(), sd, sd / np.sqrt(n_eff)
