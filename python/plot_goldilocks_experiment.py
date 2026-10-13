#!/usr/bin/env python3
"""
Phys 39 Module 6, Part I, Part 7. Naidu / Cohen

The six experimental Goldilocks plots and the step-response metrics for A3
Question 2, from the 13 October runs.

    python3 python/plot_goldilocks_experiment.py     (run from the repository root)

INPUT   data/module_06/pi_run_20261013_094149.csv
        One GUI session holding all six runs. Each row carries the run label,
        mode, kp and ki in force, so every run is cut out by those columns.
        Run 6 is the Ki = 1.0 block only: the rows from 3750 s on are still
        labelled run 6 but have Ki = 2, 5 and 10 (an instructor spot check,
        see data/module_06/bench_log_2026-10-13.md) and are not used.

OUTPUT  docs/figures/module_06/goldilocks/run1_p_kp2.png ... run6_pi_ki1.png
        docs/figures/module_06/goldilocks/overlay_p_and_pi.png
        docs/figures/module_06/goldilocks/high_gain_steps.png
        data/module_06/goldilocks_metrics.csv

WHAT IS PLOTTED

    Every run is shown on the same axes: time from the 30 to 35 C setpoint
    step, -30 s to +610 s, and 25 to 37 C. Only rows with control ON are
    drawn. The upper panel is the process output, the measured temperature,
    with the setpoint. The lower panel is the process input, the signed PWM
    actually commanded (pwm_sent), drawn as a step because each command is
    held until the next reading. Red is heating, blue is cooling.

METRICS, thresholds stated here and in the CSV

    T_i      mean of the 30 s before the step
    T_f      mean of the last 30 s of the stage (the stage ends at the next
             setpoint change, or where control was switched off)
    rise     time from 10 % to 90 % of (T_f - T_i), linear interpolation
    overshoot  how far T goes past T_f, in C and as % of |T_f - T_i|
    settling time after the step at which T last leaves T_f +/- 2 % of
             |T_f - T_i| (about +/- 0.1 C for these steps)
    ss error T_set - T_f
    period   twice the mean spacing between crossings of T_f, counting a
             crossing only when T moves from more than 0.05 C on one side to
             more than 0.05 C on the other; given when there are at least
             three such crossings
    drift    slope over the last 60 s of the stage, C per minute, so a stage
             that had not finished settling is visible

    The noise floor is about 0.01 C (standard deviation over the last 30 s
    of each stage), so the 0.05 C and 0.1 C thresholds sit well above it.
"""

import csv
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INPUT_CSV = "data/module_06/pi_run_20261013_094149.csv"
FIG_DIR = "docs/figures/module_06/goldilocks"
METRICS_CSV = "data/module_06/goldilocks_metrics.csv"

# run: (mode, Kp, Ki, gain level, file stem)
RUNS = {
    1: ("P", 2.0, 0.0, "low", "run1_p_kp2"),
    2: ("P", 16.0, 0.0, "medium", "run2_p_kp16"),
    3: ("P", 64.0, 0.0, "high", "run3_p_kp64"),
    4: ("PI", 12.0, 0.05, "low", "run4_pi_ki0p05"),
    5: ("PI", 12.0, 0.2, "medium", "run5_pi_ki0p2"),
    6: ("PI", 12.0, 1.0, "high", "run6_pi_ki1"),
}

T_LIM = (25.0, 37.0)
X_LIM = (-30.0, 610.0)
PWM_LIMIT = 255
BEFORE = 30.0          # s, window for T_i
FINAL = 30.0           # s, window for T_f
DRIFT_WINDOW = 60.0    # s
SETTLE_FRACTION = 0.02
HYSTERESIS = 0.05      # C

TEMP = "#1E6B3A"
SET = "#595959"
HEAT = "#C0392B"
COOL = "#1F77B4"
TEXT = "#404040"
LEVEL_COLORS = {"low": "#8FB8DE", "medium": "#2F6DA8", "high": "#0B2545"}


# ---------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------

def load():
    if not os.path.exists(INPUT_CSV):
        sys.exit(f"{INPUT_CSV} not found. Run this from the repository root.")
    with open(INPUT_CSV, newline="") as f:
        rows = list(csv.DictReader(f))
    cols = {}
    for name in ("time_s", "temperature_C", "setpoint_C", "kp", "ki"):
        cols[name] = np.array([float(r[name]) for r in rows])
    for name in ("pwm_sent", "control_on", "run", "saturated"):
        cols[name] = np.array([int(r[name]) for r in rows])
    cols["mode"] = np.array([r["mode"] for r in rows])
    return cols


def cut_run(d, run):
    mode, kp, ki, _, _ = RUNS[run]
    sel = ((d["run"] == run) & (d["control_on"] == 1) & (d["mode"] == mode)
           & np.isclose(d["kp"], kp) & np.isclose(d["ki"], ki))
    idx = np.flatnonzero(sel)
    if idx.size == 0:
        sys.exit(f"No rows for run {run}.")
    if np.any(np.diff(idx) != 1):
        sys.exit(f"Run {run} rows are not one contiguous block.")
    r = {k: v[idx] for k, v in d.items()}
    sp = r["setpoint_C"]
    up = int(np.flatnonzero(np.isclose(sp, 35.0))[0])
    down = up + int(np.flatnonzero(np.isclose(sp[up:], 30.0))[0])
    r["i_up"], r["i_down"] = up, down
    return r


# ---------------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------------

def crossing_time(t, y, i0, level, rising):
    """First time after index i0 that y reaches level, interpolated."""
    for i in range(i0, len(y)):
        if (y[i] >= level) if rising else (y[i] <= level):
            if i == i0:
                return t[i]
            f = (level - y[i - 1]) / (y[i] - y[i - 1])
            return t[i - 1] + f * (t[i] - t[i - 1])
    return np.nan


def step_metrics(r, i_step, i_end, run, which):
    t, T = r["time_s"], r["temperature_C"]
    t0 = t[i_step]
    T_set = r["setpoint_C"][i_step]
    before = (t >= t0 - BEFORE) & (t < t0)
    T_i = T[before].mean()
    ts, Ts = t[i_step:i_end + 1], T[i_step:i_end + 1]
    tail = ts >= ts[-1] - FINAL
    T_f = Ts[tail].mean()
    noise = Ts[tail].std(ddof=1)
    delta = T_f - T_i
    rising = delta > 0

    t10 = crossing_time(ts, Ts, 0, T_i + 0.1 * delta, rising)
    t90 = crossing_time(ts, Ts, 0, T_i + 0.9 * delta, rising)

    if rising:
        k = int(np.argmax(Ts))
        over = max(0.0, Ts[k] - T_f)
    else:
        k = int(np.argmin(Ts))
        over = max(0.0, T_f - Ts[k])

    band = SETTLE_FRACTION * abs(delta)
    outside = np.flatnonzero(np.abs(Ts - T_f) > band)
    if outside.size == 0:
        settle = 0.0
    elif outside[-1] + 1 < len(ts):
        settle = ts[outside[-1] + 1] - t0
    else:
        settle = np.nan

    # crossings of T_f with hysteresis
    dev = Ts - T_f
    state, crossings, last_sign_change = None, [], None
    for i in range(len(dev)):
        if i > 0 and np.sign(dev[i]) != np.sign(dev[i - 1]) and dev[i] != dev[i - 1]:
            f = -dev[i - 1] / (dev[i] - dev[i - 1])
            last_sign_change = ts[i - 1] + f * (ts[i] - ts[i - 1])
        s = 1 if dev[i] > HYSTERESIS else (-1 if dev[i] < -HYSTERESIS else 0)
        if s != 0:
            if state is not None and s != state and last_sign_change is not None:
                crossings.append(last_sign_change)
            state = s
    period = (2.0 * float(np.mean(np.diff(crossings)))
              if len(crossings) >= 3 else np.nan)

    dw = ts >= ts[-1] - DRIFT_WINDOW
    drift = np.polyfit(ts[dw], Ts[dw], 1)[0] * 60.0

    return {
        "run": run, "mode": RUNS[run][0], "kp": RUNS[run][1],
        "ki": RUNS[run][2], "step": which, "setpoint_C": T_set,
        "step_time_s": t0, "stage_length_s": ts[-1] - t0,
        "T_initial_C": T_i, "T_final_C": T_f, "change_C": delta,
        "rise_10_90_s": t90 - t10,
        "overshoot_C": over, "overshoot_pct": 100.0 * over / abs(delta),
        "peak_C": Ts[k], "peak_time_s": ts[k] - t0,
        "settling_2pct_s": settle, "settle_band_C": band,
        "ss_error_C": T_set - T_f, "period_s": period,
        "crossings": len(crossings), "drift_C_per_min": drift,
        "final_noise_sd_C": noise,
        "saturated_rows": int(r["saturated"][i_step:i_end + 1].sum()),
    }


# ---------------------------------------------------------------------
# PLOTTING
# ---------------------------------------------------------------------

def house_style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.edgecolor": "#868686", "axes.linewidth": 0.8,
        "xtick.direction": "out", "ytick.direction": "out",
        "xtick.color": "#595959", "ytick.color": "#595959",
    })


def style(ax):
    ax.set_facecolor("white")
    ax.grid(True, which="major", color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def signed_pwm(ax, x, u, lw=1.3):
    """Signed command as a held step, red where heating, blue where cooling."""
    xs = np.repeat(x, 2)[1:]
    us = np.repeat(u, 2)[:-1]
    ax.plot(xs, us, color="#BBBBBB", linewidth=lw * 0.6, zorder=2)
    ax.plot(xs, np.where(us > 0, us, np.nan), color=HEAT, linewidth=lw, zorder=3)
    ax.plot(xs, np.where(us < 0, us, np.nan), color=COOL, linewidth=lw, zorder=3)


def title_for(run):
    mode, kp, ki, level, _ = RUNS[run]
    if mode == "P":
        return f"Run {run}: P control, {level} gain,  $K_p$ = {kp:g} PWM/°C"
    return (f"Run {run}: PI control, {level} $K_i$,  $K_p$ = {kp:g} PWM/°C,"
            f"  $K_i$ = {ki:g} PWM/(°C s)")


def run_figure(r, run, up, down, path):
    t = r["time_s"] - r["time_s"][r["i_up"]]
    T, sp, u = r["temperature_C"], r["setpoint_C"], r["pwm_sent"]
    keep = t >= X_LIM[0]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8.6, 5.4), sharex=True,
                                 gridspec_kw={"height_ratios": [2.0, 1.0],
                                              "hspace": 0.12})
    fig.patch.set_facecolor("white")
    for ax in (a1, a2):
        style(ax)

    a1.step(t[keep], sp[keep], where="post", color=SET, linewidth=1.2,
            linestyle="--", label="Setpoint", zorder=2)
    a1.plot(t[keep], T[keep], color=TEMP, linewidth=1.5,
            label="Measured temperature", zorder=3)
    a1.set_xlim(*X_LIM)
    a1.set_ylim(*T_LIM)
    a1.set_ylabel("Temperature  (°C)", color=TEXT)
    a1.set_title(title_for(run), fontsize=11.5, color=TEXT, pad=24)
    a1.tick_params(axis="x", which="both", bottom=True, labelbottom=False,
                   length=3.5, color="#868686")
    a1.text(0.5, 1.025,
            f"End of each stage {up['T_initial_C']:.2f} → {up['T_final_C']:.2f} "
            f"→ {down['T_final_C']:.2f} °C,   overshoot up "
            f"{up['overshoot_C']:.2f} °C, down {down['overshoot_C']:.2f}"
            f" °C", transform=a1.transAxes, fontsize=9.3, color=TEMP,
            ha="center", va="bottom")
    leg = a1.legend(loc="lower right", frameon=True, fontsize=9)
    leg.get_frame().set_edgecolor("#BFBFBF")
    leg.get_frame().set_linewidth(0.8)

    signed_pwm(a2, t[keep], u[keep])
    a2.axhline(0, color="#868686", linewidth=0.8, zorder=1)
    lo, hi = u[keep].min(), u[keep].max()
    if max(abs(lo), abs(hi)) > 0.8 * PWM_LIMIT:
        for s in (1, -1):
            a2.axhline(s * PWM_LIMIT, color=HEAT if s > 0 else COOL,
                       linewidth=0.9, linestyle=":", zorder=1)
    pad = 0.15 * max(hi - lo, 10)
    a2.set_ylim(min(lo, 0) - pad, max(hi, 0) + pad)
    a2.set_ylabel("Signed PWM\n(+ heat, − cool)", color=TEXT)
    a2.set_xlabel("Time from the 30 → 35 °C setpoint step  (s)",
                  color=TEXT)

    fig.text(0.01, 0.01,
             f"Data: {INPUT_CSV}, run {run}, control ON rows only.\n"
             f"Setpoint steps 30 → 35 → 30 °C, PWM limit "
             f"{PWM_LIMIT}, anti-windup on, integral zeroed before the run. "
             "Stage values are means of its last 30 s.\n"
             "Readings every 0.56 s, each the mean of 1000 ADC samples. Red: "
             "heating command. Blue: cooling command.",
             fontsize=7.6, color="#595959", va="bottom")
    fig.subplots_adjust(left=0.1, right=0.985, top=0.885, bottom=0.2)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def overlay_figure(cuts, path):
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 6.2), sharex=True,
                             gridspec_kw={"height_ratios": [2.0, 1.0],
                                          "hspace": 0.12, "wspace": 0.16})
    fig.patch.set_facecolor("white")
    for col, group in enumerate(((1, 2, 3), (4, 5, 6))):
        a1, a2 = axes[0][col], axes[1][col]
        style(a1)
        style(a2)
        for run in group:
            r = cuts[run]
            t = r["time_s"] - r["time_s"][r["i_up"]]
            keep = t >= X_LIM[0]
            mode, kp, ki, level, _ = RUNS[run]
            lab = (f"$K_p$ = {kp:g}" if mode == "P" else f"$K_i$ = {ki:g}")
            c = LEVEL_COLORS[level]
            a1.plot(t[keep], r["temperature_C"][keep], color=c, linewidth=1.4,
                    label=f"Run {run}, {lab}")
            u = r["pwm_sent"][keep]
            a2.plot(np.repeat(t[keep], 2)[1:], np.repeat(u, 2)[:-1], color=c,
                    linewidth=1.1)
        r = cuts[group[0]]
        t = r["time_s"] - r["time_s"][r["i_up"]]
        keep = t >= X_LIM[0]
        a1.step(t[keep], r["setpoint_C"][keep], where="post", color=SET,
                linewidth=1.1, linestyle="--", label="Setpoint")
        a1.set_xlim(*X_LIM)
        a1.set_ylim(*T_LIM)
        a1.tick_params(axis="x", which="both", bottom=True, labelbottom=False,
                       length=3.5, color="#868686")
        a1.set_title("(a) P control" if col == 0 else
                     "(b) PI control,  $K_p$ = 12 PWM/°C",
                     fontsize=11.5, color=TEXT, pad=8)
        a2.axhline(0, color="#868686", linewidth=0.8, zorder=1)
        a2.set_xlabel("Time from the 30 → 35 °C step  (s)", color=TEXT)
        if col == 0:
            a1.set_ylabel("Output: temperature  (°C)", color=TEXT)
            a2.set_ylabel("Input: signed PWM\n(+ heat, \u2212 cool)", color=TEXT)
        leg = a1.legend(loc="lower right", frameon=True, fontsize=8.6)
        leg.get_frame().set_edgecolor("#BFBFBF")
        leg.get_frame().set_linewidth(0.8)
    fig.suptitle("Measured step responses: three P gains and three PI gains",
                 fontsize=13, color=TEXT, y=0.985)
    fig.text(0.01, 0.01,
             f"Same data and axes as the six run figures ({INPUT_CSV}). "
             "Kp in PWM/°C, Ki in PWM/(°C s).\nInput panels share "
             "one scale per column, so the low-gain commands sit close to zero.",
             fontsize=7.6, color="#595959", va="bottom")
    fig.subplots_adjust(left=0.085, right=0.985, top=0.885, bottom=0.14)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def high_gain_figure(cuts, metrics, path):
    """Zoom on the four steps the metrics are quoted for."""
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 6.4),
                             gridspec_kw={"hspace": 0.42, "wspace": 0.18})
    fig.patch.set_facecolor("white")
    for row, run in enumerate((3, 6)):
        r = cuts[run]
        for col, which in enumerate(("up", "down")):
            ax = axes[row][col]
            style(ax)
            m = next(x for x in metrics if x["run"] == run and x["step"] == which)
            t = r["time_s"] - m["step_time_s"]
            # This stage only: stop where the next setpoint change happens.
            end = m["stage_length_s"]
            win = (t >= -15) & (t <= end)
            ax.plot(t[win], r["temperature_C"][win], color=TEMP, linewidth=1.5)
            ax.step(t[win], r["setpoint_C"][win], where="post", color=SET,
                    linewidth=1.1, linestyle="--")
            ax.axhspan(m["T_final_C"] - m["settle_band_C"],
                       m["T_final_C"] + m["settle_band_C"], color="#D5E8D4",
                       zorder=0)
            ax.axhline(m["T_final_C"], color=TEMP, linewidth=0.8, linestyle=":")
            if np.isfinite(m["settling_2pct_s"]):
                ax.axvline(m["settling_2pct_s"], color="#868686",
                           linewidth=0.9, linestyle="-.")
            ax.set_xlim(-15, end + 3)
            mode, kp, ki, _, _ = RUNS[run]
            g = (f"P, $K_p$ = {kp:g}" if mode == "P"
                 else f"PI, $K_p$ = {kp:g}, $K_i$ = {ki:g}")
            ax.set_title(f"Run {run} ({g}): {'30 → 35' if which == 'up' else '35 → 30'} °C",
                         fontsize=10.5, color=TEXT, pad=6)
            per = (f"{m['period_s']:.0f} s" if np.isfinite(m["period_s"])
                   else "n/a")
            stl = (f"{m['settling_2pct_s']:.0f} s"
                   if np.isfinite(m["settling_2pct_s"]) else "not settled")
            ax.text(0.98, 0.05 if which == "up" else 0.95,
                    f"rise 10-90 %  {m['rise_10_90_s']:.1f} s\n"
                    f"overshoot  {m['overshoot_C']:.2f} °C "
                    f"({m['overshoot_pct']:.0f} %)\n"
                    f"settling ±2 %  {stl}\n"
                    f"ss error  {round(m['ss_error_C'], 2) + 0.0:+.2f} °C\n"
                    f"period  {per}",
                    transform=ax.transAxes, fontsize=8.6, color=TEXT,
                    ha="right", va="bottom" if which == "up" else "top")
            if col == 0:
                ax.set_ylabel("Temperature  (°C)", color=TEXT)
            if row == 1:
                ax.set_xlabel("Time from the setpoint step  (s)", color=TEXT)
    fig.suptitle("Highest-gain P and PI runs: step-response metrics",
                 fontsize=13, color=TEXT, y=0.985)
    fig.text(0.01, 0.01,
             "Green band: final value ±2 % of the step, the settling "
             "threshold. Dash-dot line: settling time. Rise time is 10 % to "
             "90 % of the change. Period is twice the mean spacing of\n"
             "crossings of the final value (0.05 °C hysteresis), given "
             "when there are at least three crossings. Final value is the mean "
             "of the last 30 s of the stage.",
             fontsize=7.6, color="#595959", va="bottom")
    fig.subplots_adjust(left=0.07, right=0.985, top=0.9, bottom=0.13)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------

def main():
    d = load()
    house_style()
    os.makedirs(FIG_DIR, exist_ok=True)
    cuts, metrics = {}, []
    for run in RUNS:
        r = cut_run(d, run)
        cuts[run] = r
        end = len(r["time_s"]) - 1
        up = step_metrics(r, r["i_up"], r["i_down"] - 1, run, "up")
        down = step_metrics(r, r["i_down"], end, run, "down")
        metrics += [up, down]
        run_figure(r, run, up, down,
                   os.path.join(FIG_DIR, RUNS[run][4] + ".png"))
    overlay_figure(cuts, os.path.join(FIG_DIR, "overlay_p_and_pi.png"))
    high_gain_figure(cuts, metrics, os.path.join(FIG_DIR, "high_gain_steps.png"))

    keys = list(metrics[0].keys())
    with open(METRICS_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for m in metrics:
            w.writerow([f"{v:.3f}" if isinstance(v, float) else v
                        for v in (m[k] for k in keys)])

    print(f"{'run':>3} {'step':>4} {'Ti':>6} {'Tf':>6} {'rise':>6} "
          f"{'over C':>6} {'over%':>6} {'settle':>7} {'ss err':>7} "
          f"{'period':>6} {'cross':>5} {'drift':>7} {'sat':>3}")
    for m in metrics:
        print(f"{m['run']:>3} {m['step']:>4} {m['T_initial_C']:6.2f} "
              f"{m['T_final_C']:6.2f} {m['rise_10_90_s']:6.1f} "
              f"{m['overshoot_C']:6.2f} {m['overshoot_pct']:6.1f} "
              f"{m['settling_2pct_s']:7.1f} {m['ss_error_C']:+7.2f} "
              f"{m['period_s']:6.1f} {m['crossings']:5d} "
              f"{m['drift_C_per_min']:+7.3f} {m['saturated_rows']:3d}")
    print(f"\nFigures in {FIG_DIR}, metrics in {METRICS_CSV}")


if __name__ == "__main__":
    main()
