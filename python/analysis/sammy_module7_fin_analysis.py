#!/usr/bin/env python3
"""Analyze Sammy's 28 Oct Module 7 rod run without modifying raw data.

Run from the repository root:
    python3 python/analysis/sammy_module7_fin_analysis.py

The sensor positions and rod length in this first analysis are planning/rough
values because the run's sensor map leaves measured positions blank. The fit
is therefore explicitly provisional.
"""

import csv
import math
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "data/module_07_sammy/sammy_rod_run_20261028_114042.csv"
MAP = ROOT / "data/module_07_sammy/sensor_map.csv"
OUT = ROOT / "data/module_07_sammy"
FIG = ROOT / "docs/figures/module_07_sammy"
REPORT = OUT / "sammy_stationary_fin_analysis_20261028.md"
SUMMARY = OUT / "sammy_stationary_windows_20261028.csv"
TIME_PLOT = FIG / "sammy_rod_run_20261028_timeseries.png"
PROFILE_PLOT = FIG / "sammy_rod_run_20261028_profile_fits.png"

ROD_COLS = ["T_T1_C", "T_T2_C", "T_T3_C", "T_T4_C", "T_T5_C"]
TAMB_WINDOW_S = 30.0
STEADY_WINDOW_S = 600.0
CONTEXT_WINDOW_S = 2400.0
STEADY_DRIFT_LIMIT_C_PER_MIN = 0.01

# Planning values from the new sensor map and previous bench note. Replace
# with measured x values and rod geometry before treating the fit as final.
TARGET_X_MM = np.array([0.0, 50.8, 101.6, 152.4, 203.2])
ROUGH_ROD_LENGTH_MM = 279.4
NOMINAL_ROD_RADIUS_MM = 6.35

# Prior run results are copied from the shared Module 8 stationary-fin note.
PRIOR = {
    "date": "2026-10-28 09:20 run 092033",
    "x_mm": np.array([0.0, 25.4, 50.8, 76.2, 101.6]),
    "theta_c": np.array([16.83, 15.66, 14.34, 13.13, 12.44]),
    "t_room_c": 21.03,
    "finite_m": 4.117,
    "finite_m_scaled_unc": 0.07,
    "semi_m": 3.056,
    "theta_ratio": 0.739,
}


def load_rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def slope_c_per_min(rows, column):
    times = np.array([float(row["time_s"]) for row in rows])
    values = np.array([float(row[column]) for row in rows])
    return float(np.polyfit(times, values, 1)[0] * 60.0)


def window_stats(rows, column):
    values = np.array([float(row[column]) for row in rows])
    times = np.array([float(row["time_s"]) for row in rows])
    return {
        "n": int(len(values)),
        "mean": float(np.mean(values)),
        "sd": float(np.std(values, ddof=1)),
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        "first": float(values[0]),
        "last": float(values[-1]),
        "span_s": float(times[-1] - times[0]),
        "drift_min": float((values[-1] - values[0]) /
                            (times[-1] - times[0]) * 60.0),
        "slope_min": slope_c_per_min(rows, column),
    }


def fit_profile(x_m, theta, finite, length_m):
    """Unweighted grid fit; returns amplitude, m, residuals, and RMSE."""
    m_grid = np.linspace(0.05, 15.0, 299001)
    if finite:
        basis = np.cosh(m_grid[:, None] * (length_m - x_m[None, :]))
        basis /= np.cosh(m_grid * length_m)[:, None]
    else:
        basis = np.exp(-m_grid[:, None] * x_m[None, :])
    amplitude = np.sum(basis * theta[None, :], axis=1) / np.sum(basis**2, axis=1)
    residual_matrix = theta[None, :] - amplitude[:, None] * basis
    sse = np.sum(residual_matrix**2, axis=1)
    idx = int(np.argmin(sse))
    m = float(m_grid[idx])
    theta0 = float(amplitude[idx])
    residual = theta - theta0 * (np.cosh(m * (length_m - x_m)) /
                                 np.cosh(m * length_m) if finite else
                                 np.exp(-m * x_m))
    rmse = float(np.sqrt(np.mean(residual**2)))
    return theta0, m, residual, rmse


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    rows = load_rows(RUN)
    times = np.array([float(row["time_s"]) for row in rows])
    active = [row for row in rows if row["control_on"] == "1"
              and row["setpoint_C"] == "45.00"]
    control_end = float(active[-1]["time_s"])

    baseline = [row for row in rows if float(row["time_s"]) <= TAMB_WINDOW_S]
    baseline_stats = {col: window_stats(baseline, col)
                      for col in ["temperature_C"] + ROD_COLS}
    room_channels = np.array([baseline_stats[col]["mean"] for col in ROD_COLS])
    t_room = float(np.mean(room_channels))
    spread_rods = float(np.max(room_channels) - np.min(room_channels))
    all_baseline = np.array([baseline_stats[col]["mean"]
                             for col in ["temperature_C"] + ROD_COLS])
    spread_all = float(np.max(all_baseline) - np.min(all_baseline))

    windows = {
        "last40": [row for row in active
                   if control_end - CONTEXT_WINDOW_S <= float(row["time_s"]) <= control_end],
        "last10": [row for row in active
                   if control_end - STEADY_WINDOW_S <= float(row["time_s"]) <= control_end],
        "last5": [row for row in active
                  if control_end - 300.0 <= float(row["time_s"]) <= control_end],
    }
    stats = {name: {col: window_stats(window, col) for col in ROD_COLS}
             for name, window in windows.items()}
    steady_slopes = np.array([stats["last10"][col]["slope_min"] for col in ROD_COLS])
    all_settled = bool(np.all(np.abs(steady_slopes) <= STEADY_DRIFT_LIMIT_C_PER_MIN))

    x_mm = TARGET_X_MM.copy()
    x_m = x_mm / 1000.0
    length_m = ROUGH_ROD_LENGTH_MM / 1000.0
    theta40 = np.array([stats["last40"][col]["mean"] for col in ROD_COLS]) - t_room
    theta10 = np.array([stats["last10"][col]["mean"] for col in ROD_COLS]) - t_room
    theta5 = np.array([stats["last5"][col]["mean"] for col in ROD_COLS]) - t_room

    fits = {}
    for window_name, theta in [("last40", theta40), ("last10", theta10),
                               ("last5", theta5)]:
        fits[window_name] = {
            "finite": fit_profile(x_m, theta, True, length_m),
            "semi": fit_profile(x_m, theta, False, length_m),
        }

    fit_f = fits["last10"]["finite"]
    fit_s = fits["last10"]["semi"]
    eps = np.abs(
        (np.cosh(fit_f[1] * (length_m - x_m)) / np.cosh(fit_f[1] * length_m))
        - np.exp(-fit_f[1] * x_m)
    ) / (np.cosh(fit_f[1] * (length_m - x_m)) /
         np.cosh(fit_f[1] * length_m))
    far_ratio_raw = float(theta10[-1] / theta10[0])
    target_ratio = 1.0 / math.e
    old_m = PRIOR["finite_m"]
    old_t5_ratio = PRIOR["theta_ratio"]
    bi = (fit_f[1] * NOMINAL_ROD_RADIUS_MM / 1000.0)**2 / 4.0
    finite_basis = np.cosh(fit_f[1] * (length_m - x_m)) / np.cosh(fit_f[1] * length_m)
    semi_basis = np.exp(-fit_s[1] * x_m)
    finite_prediction = fit_f[0] * finite_basis
    semi_prediction = fit_s[0] * semi_basis
    finite_tip_error = np.abs(finite_basis - np.exp(-fit_f[1] * x_m)) / finite_basis
    base_peak_idx = int(np.argmax([float(row["temperature_C"]) for row in rows]))
    base_peak = rows[base_peak_idx]

    # Summary table is additive and records both the long context and settled window.
    with SUMMARY.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["channel", "target_x_mm", "room_estimate_C",
                         "last40_mean_C", "last40_sd_C", "last10_mean_C",
                         "last10_sd_C", "last10_linear_drift_C_per_min",
                         "last10_range_C", "last5_mean_C"])
        for i, col in enumerate(ROD_COLS):
            writer.writerow([col, f"{x_mm[i]:.1f}", f"{t_room:.4f}",
                             f"{stats['last40'][col]['mean']:.4f}",
                             f"{stats['last40'][col]['sd']:.4f}",
                             f"{stats['last10'][col]['mean']:.4f}",
                             f"{stats['last10'][col]['sd']:.4f}",
                             f"{stats['last10'][col]['slope_min']:.5f}",
                             f"{stats['last10'][col]['maximum'] - stats['last10'][col]['minimum']:.4f}",
                             f"{stats['last5'][col]['mean']:.4f}"])

    # Time history of all channels. The final stationary-check interval is shaded.
    fig, ax = plt.subplots(figsize=(11, 6), layout="constrained")
    colorset = ["#176B73", "#C74343", "#2878A5", "#8A61A8", "#C47B32", "#597A3A"]
    all_cols = ["temperature_C"] + ROD_COLS
    labels = ["TEC base (A0)", "T1", "T2", "T3", "T4", "T5"]
    for col, label, color in zip(all_cols, labels, colorset):
        vals = [float(row[col]) if row[col] else np.nan for row in rows]
        ax.plot(times / 60.0, vals, label=label, color=color, lw=1.1)
    ax.axvspan((control_end - STEADY_WINDOW_S)/60.0, control_end/60.0,
               color="#a6cee3", alpha=0.22, label="final 10 min check")
    ax.axvline(31.79/60.0, color="#555555", lw=1.0, ls="--",
               label="setpoint changed to 45 C")
    ax.set_xlabel("Elapsed time (min)")
    ax.set_ylabel("Temperature (deg C)")
    ax.set_title("All six recorded channels — 28 Oct 2026 run")
    ax.grid(alpha=0.25)
    ax.legend(ncol=3, fontsize=8)
    fig.savefig(TIME_PLOT, dpi=170)
    plt.close(fig)

    # Stationary profile and residuals. Positions are target values, so label provisional.
    fig, (ax, axr) = plt.subplots(2, 1, figsize=(9, 7),
                                  gridspec_kw={"height_ratios": [2.2, 1]},
                                  sharex=True, layout="constrained")
    yerr = np.array([stats["last10"][col]["sd"] for col in ROD_COLS])
    ax.errorbar(x_mm, theta10, yerr=yerr, fmt="o", color="#1F4E79",
                capsize=3, label="new run, final 10 min (raw; +/- within-window SD)")
    ax.plot(x_mm, theta40, "s", color="#999999", ms=5,
            label="new run, final 40 min mean (includes approach)")
    ax.plot(PRIOR["x_mm"], PRIOR["theta_c"], "x", color="#C47B32", ms=7,
            label="prior 09:20 run, calibrated profile")
    xx = np.linspace(0, length_m, 300)
    ax.plot(xx*1000, fit_f[0]*np.cosh(fit_f[1]*(length_m-xx))/np.cosh(fit_f[1]*length_m),
            color="#176B73", lw=1.8,
            label=f"provisional finite fit: m={fit_f[1]:.2f} 1/m")
    ax.plot(xx*1000, fit_s[0]*np.exp(-fit_s[1]*xx), color="#C74343", ls="--",
            lw=1.5, label=f"provisional semi-infinite: m={fit_s[1]:.2f} 1/m")
    ax.axhline(theta10[0]*target_ratio, color="#777777", ls=":", lw=1,
               label="theta(T1)/e placement target")
    ax.set_ylabel("Excess temperature theta = T − T_room (deg C)")
    ax.set_title("Stationary profile; new-run x positions are planned, not measured")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7.4)
    axr.axhline(0, color="#777777", lw=0.8)
    axr.plot(x_mm, fit_f[2], "o-", color="#176B73", label="finite residual")
    axr.plot(x_mm, fit_s[2], "s--", color="#C74343", label="semi-infinite residual")
    axr.set_xlabel("Position from T1 (mm; target positions used provisionally)")
    axr.set_ylabel("Residual (deg C)")
    axr.grid(alpha=0.25)
    axr.legend(fontsize=8)
    fig.savefig(PROFILE_PLOT, dpi=170)
    plt.close(fig)

    # Report values and caveats.
    report = []
    report.append("# Sammy Module 7 Rod Run: Preliminary Calculations and Fits\n")
    report.append("Run: `sammy_rod_run_20261028_114042.csv` (28 Oct 2026). "
                  "Raw CSV, metadata, notes, sensor map, and prior runs are left unchanged.\n")
    report.append("## Scope and assumptions\n")
    report.append(f"- {len(rows)} rows from {times[0]:.2f} to {times[-1]:.2f} s "
                  f"({(times[-1]-times[0])/60:.2f} min). The 45 C controlled segment "
                  f"ended at {control_end:.2f} s.\n")
    report.append("- Last 40 minutes are summarized as requested. The final 10 minutes "
                  "are used as the primary stationary window because each rod channel's "
                  "linear drift is below 0.01 C/min. The last 5 minutes are included "
                  "as a sensitivity check.\n")
    report.append(f"- `T_room` is provisionally estimated as the mean of the five rod "
                  f"channels over the first 30 s: {t_room:.3f} C. Initial rod-channel "
                  f"mean spread is {spread_rods:.3f} C; including the TEC-base channel "
                  f"the spread is {spread_all:.3f} C. This is a startup room baseline, "
                  "not a documented mixed common-bath calibration. No offsets are applied.\n")
    report.append("- The sensor map has blank measured-position and resistor fields. Fits "
                  "use planned positions 0, 50.8, 101.6, 152.4, 203.2 mm and a rough "
                  "prior length L=279.4 mm. The resulting m fits are provisional; "
                  "no formal parameter uncertainty is reported.\n")
    report.append("- The rod sensors were taped, not glued. Tape/contact affects sensor "
                  "lag and may cause channel-specific thermal contact bias. Plot smoothing "
                  "is off and all analysis uses raw logged values.\n")
    report.append("- Control chronology: target changed from 30 to 45 C at about 31.79 s; "
                  "PI mode Kp=12 began at about 39.60 s, control was enabled at 80 s, "
                  "Ki=0.2 was selected at about 257.89 s, and control was switched off "
                  f"at {control_end:.2f} s. The TEC-base peak was "
                  f"{float(base_peak['temperature_C']):.2f} C at "
                  f"{float(base_peak['time_s']):.2f} s, {float(base_peak['temperature_C'])-45.0:.2f} C above the 45 C setpoint.\n")
    report.append("\n## Time windows\n")
    report.append("| Channel | Last 40 min mean (C) | Last 10 min mean (C) | Last 10 min drift (C/min) | Last 10 min range (C) | Last 5 min mean (C) |\n")
    report.append("|---|---:|---:|---:|---:|---:|\n")
    for col in ROD_COLS:
        s40, s10, s5 = stats["last40"][col], stats["last10"][col], stats["last5"][col]
        report.append(f"| {col} | {s40['mean']:.3f} | {s10['mean']:.3f} | "
                      f"{s10['slope_min']:+.4f} | {s10['maximum']-s10['minimum']:.3f} | "
                      f"{s5['mean']:.3f} |\n")
    report.append("\nStationarity check: all five last-10-minute linear drift estimates have "
                  f"absolute value <= {STEADY_DRIFT_LIMIT_C_PER_MIN:.2f} C/min. This "
                  "supports using that interval under the example criterion. The last "
                  "40-minute means include more of the approach and are not used as the "
                  "primary stationary profile.\n")
    report.append("\n### Worked final-window example: T1\n")
    t1_stats = stats["last10"]["T_T1_C"]
    t1_rows = [row for row in windows["last10"] if row["T_T1_C"]]
    report.append(f"The selected interval is {float(windows['last10'][0]['time_s']):.2f} "
                  f"to {float(windows['last10'][-1]['time_s']):.2f} s and contains "
                  f"{t1_stats['n']} readings. For T1 the sum is "
                  f"{sum(float(row['T_T1_C']) for row in t1_rows):.4f} C-samples:\n\n")
    report.append("```text\n")
    report.append(f"mean T1 = sum(T1 readings)/N = {sum(float(row['T_T1_C']) for row in t1_rows):.4f}/{len(t1_rows)}\n")
    report.append(f"         = {t1_stats['mean']:.5f} C\n")
    report.append(f"linear drift = fitted slope * 60 = {t1_stats['slope_min']:+.5f} C/min\n")
    report.append("```\n\n")
    report.append("The drift estimate uses a least-squares line through the entire window, "
                  "not just the difference between two noisy endpoint readings.\n")

    report.append("\n### Worked startup room estimate and common-bath warning\n")
    report.append("For the first 30 s, 52 rows were recorded. The five rod-channel means were:\n\n")
    report.append("```text\n")
    for col in ROD_COLS:
        report.append(f"{col}: {baseline_stats[col]['mean']:.5f} C\n")
    report.append("T_room estimate = (22.36500 + 21.89846 + 22.09135 + 21.92962 + 22.12173)/5\n")
    report.append(f"                = {t_room:.5f} C\n")
    report.append(f"rod channel spread = max - min = {spread_rods:.5f} C\n")
    report.append(f"all six channel spread including base = {spread_all:.5f} C\n")
    report.append("```\n\n")
    report.append("This is a room-temperature startup baseline, not a controlled common-bath "
                  "check. It shows a noticeable inter-channel spread, so do not claim the "
                  "calibration check passed and do not invent/apply offsets. Perform the "
                  "official common-bath procedure and confirm its acceptance threshold; "
                  "then either retain raw values or apply documented corrections if required.\n")

    report.append("\n## Provisional fin fits\n")
    report.append("Use theta = T - T_room and fit the stationary models to the final-10-minute means. For each fixed m, theta0 is solved by least squares; m is selected by a dense one-dimensional grid search. Fits are unweighted because channel calibration/position uncertainties are not established. RMSE is descriptive, not a significance test.\n")
    report.append("| Window | Model | m (1/m) | 1/m (mm) | theta0 (C) | RMSE (C) | far ratio theta5/theta1 |\n")
    report.append("|---|---|---:|---:|---:|---:|---:|\n")
    for name in ["last40", "last10", "last5"]:
        for label, key in [("finite insulated tip", "finite"), ("semi-infinite", "semi")]:
            a, m, residual, rmse = fits[name][key]
            if key == "finite":
                far = math.cosh(m*(length_m-x_m[-1]))/math.cosh(m*length_m)
            else:
                far = math.exp(-m*x_m[-1])
            report.append(f"| {name} | {label} | {m:.3f} | {1000/m:.1f} | {a:.3f} | {rmse:.3f} | {far:.3f} |\n")
    report.append("\n### Worked excess-temperature ratio\n")
    report.append("For the primary last-10-minute window, estimate room temperature from "
                  "the initial rod baseline, then subtract it from each stationary mean. "
                  "For T1 and T5:\n\n")
    report.append("```text\n")
    report.append(f"theta1 = T1_mean - T_room = {stats['last10']['T_T1_C']['mean']:.5f} - {t_room:.5f} = {theta10[0]:.5f} C\n")
    report.append(f"theta5 = T5_mean - T_room = {stats['last10']['T_T5_C']['mean']:.5f} - {t_room:.5f} = {theta10[-1]:.5f} C\n")
    report.append(f"theta5/theta1 = {theta10[-1]:.5f}/{theta10[0]:.5f} = {far_ratio_raw:.5f}\n")
    report.append(f"placement target 1/e = {target_ratio:.5f}\n")
    report.append("```\n\n")
    report.append("The observed ratio does not meet the 1/e placement target. The target "
                  "is a criterion to test, not a guarantee that the available rod reaches it.\n")

    report.append("\n### Worked fit method and per-sensor comparison\n")
    report.append("Let f_i(m) be the model shape at sensor x_i. For the finite model, "
                  "f_i=cosh[m(L-x_i)]/cosh(mL); for the semi-infinite model, "
                  "f_i=exp(-m x_i). For each trial m, choose the amplitude theta0 that "
                  "minimizes the sum of squared residuals. Differentiate the squared "
                  "error with respect to theta0, set that derivative to zero, and solve:\n\n")
    report.append("```text\n")
    report.append("SSE(theta0,m) = sum_i [theta_i - theta0*f_i(m)]^2\n")
    report.append("theta0(m) = sum_i[f_i(m)*theta_i] / sum_i[f_i(m)^2]\n")
    report.append("choose m that minimizes SSE; RMSE = sqrt(SSE/N)\n")
    report.append("```\n\n")
    report.append("For the final-10-minute window and planned positions, the fit residual "
                  "is measured theta minus predicted theta:\n\n")
    report.append("| Sensor | x target (mm) | measured theta (C) | finite prediction (C) | finite residual (C) | semi prediction (C) | semi residual (C) | finite-tip relative difference |\n")
    report.append("|---|---:|---:|---:|---:|---:|---:|---:|\n")
    for i, col in enumerate(ROD_COLS):
        report.append(f"| T{i+1} | {x_mm[i]:.1f} | {theta10[i]:.3f} | {finite_prediction[i]:.3f} | {fit_f[2][i]:+.3f} | {semi_prediction[i]:.3f} | {fit_s[2][i]:+.3f} | {finite_tip_error[i]:.3f} |\n")
    report.append("\nThe finite-tip relative difference compares the two *shape predictions* at "
                  "the finite-fit m: abs(finite_shape - semi_shape)/finite_shape. It is "
                  "not an uncertainty. The course's chosen acceptable-error threshold "
                  "was missing from the pasted handout, so confirm it before declaring "
                  "the semi-infinite approximation acceptable.\n")
    report.append("\nFor the primary last-10-minute means, the raw observed excess ratio "
                  f"theta5/theta1 = {far_ratio_raw:.3f}. The prior 09:20 run reported "
                  f"0.739 using five sensors only through 101.6 mm and its common-bath "
                  f"offsets. The new provisional ratio is smaller because T5 is planned "
                  "farther out; this comparison is not a controlled repeat because the "
                  "new measured positions and calibration are missing.\n")
    finite_last10 = fits["last10"]["finite"]
    semi_last10 = fits["last10"]["semi"]
    report.append(f"The last-10-minute unweighted fit has RMSE {finite_last10[3]:.3f} C "
                  f"(finite) versus {semi_last10[3]:.3f} C (semi-infinite), so the finite "
                  "model fits these five provisional points better. The previous run also "
                  "favored the finite fit (m=4.117 1/m; semi m=3.056 1/m), but warned that "
                  "its sensors covered only the near-base region. Inspect the new residuals: "
                  "with only five sensors, unknown contact bias, no measured x, and no new "
                  "common-bath correction, the lower RMSE is suggestive rather than decisive.\n")
    report.append(f"The placement target is theta5/theta1 <= 1/e = {target_ratio:.3f}. "
                  f"The new raw value {far_ratio_raw:.3f} does not meet it. The prior model "
                  "predicted theta/theta1 about 0.60 at the farthest available hole; spreading "
                  "the sensors improves leverage for the tip comparison but the available "
                  "rod length may still not reach 1/e.\n")
    report.append("\n## Compare with the previous run\n")
    report.append("Prior run 092033 used measured positions 0, 25.4, 50.8, 76.2, 101.6 mm, "
                  "T_room=21.03 C, and calibration offsets. Its final stationary profile "
                  "reported m_finite=4.117 +/- 0.036 1/m (scaled +/- 0.07), m_semi=3.056 "
                  "+/- 0.043 1/m, chi2/dof 10.35/3 and 12.91/3, and far ratio 0.739. The "
                  "new run is raw, has planned 2-inch positions and T_room estimated from "
                  "its initial baseline; do not compare the m shift as a material change "
                  "until positions, common-bath correction decision, room temperature, and "
                  "geometry are measured consistently.\n")
    report.append("\n## Radial check and what cannot be inferred\n")
    report.append(f"Using the provisional finite-fit m={finite_last10[1]:.3f} 1/m and "
                  f"nominal radius R={NOMINAL_ROD_RADIUS_MM:.2f} mm, "
                  f"Bi_perp=(mR)^2/4={bi:.2e}. This is provisionally much less than 0.1, "
                  "supporting a uniform radial cross-section. Replace nominal R with the "
                  "caliper measurement and propagate uncertainty. A one-dimensional "
                  "stationary fit determines m^2=hP/(kA), hence a ratio involving h/k; it "
                  "cannot determine k and h separately.\n")
    report.append("\n## New plots and next corrections\n")
    report.append("- `docs/figures/module_07_sammy/sammy_rod_run_20261028_timeseries.png`: six-channel time history and final stationary interval.\n")
    report.append("- `docs/figures/module_07_sammy/sammy_rod_run_20261028_profile_fits.png`: last-40 and last-10 means, previous run, both fits, and residuals.\n")
    report.append("- Before treating the fit as final: fill measured x positions, rod diameter, T1-to-tip length, and measured resistor values in sensor_map.csv; perform/record the official common-bath check; record room temperature near the stationary window; then rerun this script.\n")
    REPORT.write_text("".join(report))


if __name__ == "__main__":
    main()