#!/usr/bin/env python3
"""
Phys 39 Module 6, Part I, Part 7. Naidu / Cohen

The six experimental Goldilocks plots and the step-response metrics for A3
Question 2.

    python3 python/plot_goldilocks_experiment.py     (run from the repository root)

INPUT   data/module_06/pi_run_20261013_094149.csv   Runs 1, 2, 4, 5, and the
                                                     first high-gain runs
        data/module_06/pi_run_20261014_111720.csv   Runs 3 and 6, repeated at
                                                     much higher gain

        Every row carries the run label, mode, kp and ki in force, so each run
        is cut out by those columns. The instructor asked for the high-gain P
        and PI runs to be pushed into saturation, so on 14 October Run 3 was
        repeated at Kp = 200 (was 64) and Run 6 at Ki = 20 (was 1.0), with the
        same setpoints, PWM limit and anti-windup. The 13 October Kp = 64 and
        Ki = 1.0 runs are kept and reported as "earlier high-gain runs".
        Rows from 3750 s on in the 13 October file (Ki = 2, 5, 10, an
        instructor spot check) are not used. See the two bench logs.

        Two irregularities in the 14 October Run 6, both visible in the data:
        control was switched on with Ki = 0 for 15 s before Ki = 20 was
        entered, so the integral started at 38 C s; and control was off for
        25 s at the end of the 35 C stage, during which the setpoint was
        changed back to 30 C. The 35 C stage is taken to end where control
        went off, and the down step starts where it came back on.

OUTPUT  docs/figures/module_06/goldilocks/run*.png      one figure per run
        docs/figures/module_06/goldilocks/overlay_p_and_pi.png
                                         three P and three PI runs overlaid,
                                         laid out like the course reference
        docs/figures/module_06/goldilocks/high_gain_steps.png
        data/module_06/goldilocks_metrics.csv

METRICS, thresholds stated here and in the CSV

    T_i      mean of the 30 s before the step (control-on rows only)
    T_f      mean of the last 30 s of the stage; for a stage that is still
             oscillating at its end (see below), the mean over whole cycles in
             its last 90 s instead, so the value is the centre of the cycle
    rise     time from 10 % to 90 % of (T_f - T_i), linear interpolation
    overshoot  how far T goes past T_f, in C and as % of |T_f - T_i|
    settling time after the step at which T last leaves T_f +/- 2 % of
             |T_f - T_i|; reported as "does not settle" if it never stays
    ss error T_set - T_f
    period   for a decaying response, twice the mean spacing between
             crossings of T_f (0.05 C hysteresis, at least three crossings);
             for a sustained oscillation, the mean spacing of upward
             crossings of the cycle mean (0.3 C hysteresis) in the last 90 s
    sustained  peak-to-peak over the last 90 s above 0.5 C with at least
             three cycles
    at limit   share of readings in the stage with |PWM sent| >= 254
"""

import csv
import os
import sys
from collections import namedtuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OCT13 = "data/module_06/pi_run_20261013_094149.csv"
OCT14 = "data/module_06/pi_run_20261014_111720.csv"
FIG_DIR = "docs/figures/module_06/goldilocks"
METRICS_CSV = "data/module_06/goldilocks_metrics.csv"

Spec = namedtuple("Spec", "data_run mode kp ki level stem source date")

# The six retained runs, keyed by run number.
RUNS = {
    1: Spec(1, "P", 2.0, 0.0, "low", "run1_p_kp2", OCT13, "13 Oct"),
    2: Spec(2, "P", 16.0, 0.0, "medium", "run2_p_kp16", OCT13, "13 Oct"),
    3: Spec(3, "P", 200.0, 0.0, "high", "run3_p_kp200", OCT14, "14 Oct"),
    4: Spec(4, "PI", 12.0, 0.05, "low", "run4_pi_ki0p05", OCT13, "13 Oct"),
    5: Spec(5, "PI", 12.0, 0.2, "medium", "run5_pi_ki0p2", OCT13, "13 Oct"),
    6: Spec(6, "PI", 12.0, 20.0, "high", "run6_pi_ki20", OCT14, "14 Oct"),
}
# The first high-gain runs, superseded by the 14 October repeats.
EARLIER = {
    "3 (Kp 64)": Spec(3, "P", 64.0, 0.0, "high", "run3_p_kp64", OCT13, "13 Oct"),
    "6 (Ki 1)": Spec(6, "PI", 12.0, 1.0, "high", "run6_pi_ki1", OCT13, "13 Oct"),
}

T_LIM = (24.0, 43.0)
X_LIM = (-30.0, 610.0)
REF_WINDOW = (-10.0, 160.0)
PWM_LIMIT = 255
BEFORE = 30.0
FINAL = 30.0
DRIFT_WINDOW = 60.0
SETTLE_FRACTION = 0.02
HYSTERESIS = 0.05
CYCLE_WINDOW = 90.0
CYCLE_HYST = 0.3
SUSTAINED_P2P = 0.5
GAP = 2.0              # s; a longer jump between control-on rows is a gap

TEMP = "#1E6B3A"
SET = "#595959"
HEAT = "#C0392B"
COOL = "#1F77B4"
TEXT = "#404040"
LEVEL_COLORS = {"low": "#8FB8DE", "medium": "#2F6DA8", "high": "#0B2545"}


# ---------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------

_cache = {}


def load(path):
    if path in _cache:
        return _cache[path]
    if not os.path.exists(path):
        sys.exit(f"{path} not found. Run this from the repository root.")
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    cols = {}
    for name in ("time_s", "temperature_C", "setpoint_C", "kp", "ki",
                 "error_C", "dt_s", "q_Cs"):
        cols[name] = np.array([float(r[name]) for r in rows])
    for name in ("pwm_sent", "control_on", "run", "saturated", "q_held"):
        cols[name] = np.array([int(r[name]) for r in rows])
    cols["mode"] = np.array([r["mode"] for r in rows])
    _cache[path] = cols
    return cols


def stage_indices(t, sp, on):
    """Indices of the up step, the end of the up stage, the down step and the
    end of the record. A stage ends at the next setpoint change or where
    control went off, whichever is first."""
    on_idx = np.flatnonzero(on)
    i_up = int(on_idx[np.isclose(sp[on_idx], 35.0)][0])
    after = on_idx[on_idx > i_up]
    i_down = int(after[np.isclose(sp[after], 30.0)][0])
    off_after = np.flatnonzero(~on[i_up:i_down]) + i_up
    up_end = int(off_after[0] - 1) if off_after.size else i_down - 1
    return i_up, up_end, i_down, int(on_idx[-1])


def segments(t, sp, on):
    """Consecutive (setpoint, on, duration) groups, for the simulation."""
    out, start = [], 0
    for i in range(1, len(t) + 1):
        if i == len(t) or sp[i] != sp[start] or on[i] != on[start]:
            end_t = t[i] if i < len(t) else t[-1] + 0.56
            out.append((float(sp[start]), bool(on[start]), float(end_t - t[start])))
            start = i
    return out


def cut(spec):
    d = load(spec.source)
    match = ((d["run"] == spec.data_run) & (d["mode"] == spec.mode)
             & np.isclose(d["kp"], spec.kp) & np.isclose(d["ki"], spec.ki))
    on_rows = np.flatnonzero(match & (d["control_on"] == 1))
    if on_rows.size == 0:
        sys.exit(f"No rows for {spec}.")
    span = np.arange(on_rows[0], on_rows[-1] + 1)
    if not match[span].all():
        sys.exit(f"{spec}: other gains appear inside the run.")
    r = {k: v[span] for k, v in d.items()}
    r["on"] = r["control_on"] == 1
    r["spec"] = spec
    r["i_up"], r["up_end"], r["i_down"], r["end"] = stage_indices(
        r["time_s"], r["setpoint_C"], r["on"])
    r["segments"] = segments(r["time_s"], r["setpoint_C"], r["on"])
    q0 = r["q_Cs"][0]
    if spec.mode == "PI" and not r["q_held"][0]:
        q0 -= r["error_C"][0] * r["dt_s"][0]
    r["q_start"] = q0 if spec.mode == "PI" else 0.0
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


def cycle_stats(ts, Ts):
    """Mean, extremes and period of the last CYCLE_WINDOW seconds."""
    w = ts >= ts[-1] - CYCLE_WINDOW
    tw, Tw = ts[w], Ts[w]
    mean = Tw.mean()
    state, ups = None, []
    for k in range(len(Tw)):
        s = 1 if Tw[k] - mean > CYCLE_HYST else (-1 if Tw[k] - mean < -CYCLE_HYST else 0)
        if s:
            if state == -1 and s == 1:
                ups.append(k)
            state = s
    sustained = (Tw.max() - Tw.min() > SUSTAINED_P2P) and len(ups) >= 3
    period = (float(np.mean(np.diff(tw[ups]))) if len(ups) >= 3 else np.nan)
    whole = (Tw[ups[0]:ups[-1]].mean() if len(ups) >= 2 else mean)
    return {"sustained": sustained, "cycle_mean_C": whole,
            "cycle_min_C": Tw.min(), "cycle_max_C": Tw.max(),
            "cycle_p2p_C": Tw.max() - Tw.min(), "cycle_period_s": period}


def step_metrics(r, i_step, i_end, label, which):
    spec = r["spec"]
    t, T, on = r["time_s"], r["temperature_C"], r["on"]
    t0 = t[i_step]
    T_set = r["setpoint_C"][i_step]
    before = (t >= t0 - BEFORE) & (t < t0) & on
    T_i = T[before].mean()
    ts, Ts = t[i_step:i_end + 1], T[i_step:i_end + 1]
    cyc = cycle_stats(ts, Ts)
    if cyc["sustained"]:
        T_f = cyc["cycle_mean_C"]
    else:
        T_f = Ts[ts >= ts[-1] - FINAL].mean()
    noise = Ts[ts >= ts[-1] - FINAL].std(ddof=1)
    delta = T_f - T_i
    rising = delta > 0

    t10 = crossing_time(ts, Ts, 0, T_i + 0.1 * delta, rising)
    t90 = crossing_time(ts, Ts, 0, T_i + 0.9 * delta, rising)
    k = int(np.argmax(Ts)) if rising else int(np.argmin(Ts))
    over = max(0.0, (Ts[k] - T_f) if rising else (T_f - Ts[k]))
    # A step taken from the middle of a large oscillation has no defined
    # starting value, so rise time and percent overshoot are not reported.
    pre_p2p = float(np.ptp(T[before])) if before.any() else 0.0
    from_cycle = pre_p2p > abs(delta)
    if from_cycle:
        t10 = t90 = over = np.nan

    band = SETTLE_FRACTION * abs(delta)
    outside = np.flatnonzero(np.abs(Ts - T_f) > band)
    if outside.size == 0:
        settle = 0.0
    elif cyc["sustained"] or outside[-1] + 1 >= len(ts):
        settle = np.nan
    else:
        settle = ts[outside[-1] + 1] - t0

    if cyc["sustained"]:
        period, ncross = cyc["cycle_period_s"], -1
    else:
        dev = Ts - T_f
        state, crossings, last = None, [], None
        for i in range(len(dev)):
            if i > 0 and np.sign(dev[i]) != np.sign(dev[i - 1]) and dev[i] != dev[i - 1]:
                f = -dev[i - 1] / (dev[i] - dev[i - 1])
                last = ts[i - 1] + f * (ts[i] - ts[i - 1])
            s = 1 if dev[i] > HYSTERESIS else (-1 if dev[i] < -HYSTERESIS else 0)
            if s:
                if state is not None and s != state and last is not None:
                    crossings.append(last)
                state = s
        period = (2.0 * float(np.mean(np.diff(crossings)))
                  if len(crossings) >= 3 else np.nan)
        ncross = len(crossings)

    dw = ts >= ts[-1] - DRIFT_WINDOW
    drift = np.polyfit(ts[dw], Ts[dw], 1)[0] * 60.0
    sent = r["pwm_sent"][i_step:i_end + 1]

    return {
        "run": label, "date": spec.date, "mode": spec.mode, "kp": spec.kp,
        "ki": spec.ki, "step": which, "setpoint_C": T_set,
        "step_time_s": t0, "stage_length_s": ts[-1] - t0,
        "T_initial_C": T_i, "T_final_C": T_f, "change_C": delta,
        "rise_10_90_s": t90 - t10,
        "overshoot_C": over, "overshoot_pct": 100.0 * over / abs(delta),
        "peak_C": Ts[k], "peak_time_s": ts[k] - t0,
        "settling_2pct_s": settle, "settle_band_C": band,
        "ss_error_C": T_set - T_f, "period_s": period, "crossings": ncross,
        "drift_C_per_min": drift, "final_noise_sd_C": noise,
        "sustained": int(cyc["sustained"]),
        "starts_mid_cycle": int(from_cycle), "pre_step_p2p_C": pre_p2p,
        "cycle_min_C": cyc["cycle_min_C"], "cycle_max_C": cyc["cycle_max_C"],
        "cycle_p2p_C": cyc["cycle_p2p_C"],
        "at_limit_pct": 100.0 * float(np.mean(np.abs(sent) >= 254)),
        "q_held_pct": 100.0 * float(np.mean(r["q_held"][i_step:i_end + 1])),
        "saturated_rows": int(r["saturated"][i_step:i_end + 1].sum()),
    }


def run_metrics(r, label):
    up = step_metrics(r, r["i_up"], r["up_end"], label, "up")
    down = step_metrics(r, r["i_down"], r["end"], label, "down")
    return up, down


# ---------------------------------------------------------------------
# PLOTTING
# ---------------------------------------------------------------------

def house_style(fs=10):
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": fs,
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


def masked(r, key):
    """The column with control-off rows set to NaN, so lines break there."""
    v = r[key].astype(float).copy()
    v[~r["on"]] = np.nan
    return v


def signed_pwm(ax, x, u, lw=1.3):
    """Signed command as a held step, red where heating, blue where cooling."""
    xs = np.repeat(x, 2)[1:]
    us = np.repeat(u, 2)[:-1]
    ax.plot(xs, us, color="#BBBBBB", linewidth=lw * 0.6, zorder=2)
    ax.plot(xs, np.where(us > 0, us, np.nan), color=HEAT, linewidth=lw, zorder=3)
    ax.plot(xs, np.where(us < 0, us, np.nan), color=COOL, linewidth=lw, zorder=3)


def gain_text(spec):
    if spec.mode == "P":
        return f"$K_p$ = {spec.kp:g} PWM/°C"
    return f"$K_p$ = {spec.kp:g} PWM/°C,  $K_i$ = {spec.ki:g} PWM/(°C s)"


def title_for(label, spec):
    kind = "P control" if spec.mode == "P" else "PI control"
    return f"Run {label} ({spec.date}): {kind}, {spec.level} gain,  {gain_text(spec)}"


def run_figure(r, label, up, down, path):
    spec = r["spec"]
    t = r["time_s"] - r["time_s"][r["i_up"]]
    T, sp, u = masked(r, "temperature_C"), r["setpoint_C"], masked(r, "pwm_sent")
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
    a1.set_title(title_for(label, spec), fontsize=11, color=TEXT, pad=24)
    a1.tick_params(axis="x", which="both", bottom=True, labelbottom=False,
                   length=3.5, color="#868686")
    if up["sustained"] or down["sustained"]:
        sub = (f"Sustained oscillation: about {up['cycle_p2p_C']:.1f} °C peak "
               f"to peak at 35 °C, period {up['period_s']:.1f} s")
    else:
        sub = (f"End of each stage {up['T_initial_C']:.2f} → "
               f"{up['T_final_C']:.2f} → {down['T_final_C']:.2f} °C,   "
               f"overshoot up {up['overshoot_C']:.2f} °C, down "
               f"{down['overshoot_C']:.2f} °C")
    a1.text(0.5, 1.025, sub, transform=a1.transAxes, fontsize=9.3, color=TEMP,
            ha="center", va="bottom")
    off = np.flatnonzero(~r["on"])
    if off.size:
        a1.axvspan(t[off[0]], t[off[-1]], color="#EEEEEE", zorder=0)
        a1.text(t[off[0]], T_LIM[1] - 0.6, " control off", fontsize=8,
                color="#777777", va="top")
    leg = a1.legend(loc="lower right", frameon=True, fontsize=9)
    leg.get_frame().set_edgecolor("#BFBFBF")

    signed_pwm(a2, t[keep], u[keep])
    a2.axhline(0, color="#868686", linewidth=0.8, zorder=1)
    lo, hi = np.nanmin(u[keep]), np.nanmax(u[keep])
    if max(abs(lo), abs(hi)) > 0.8 * PWM_LIMIT:
        for s in (1, -1):
            a2.axhline(s * PWM_LIMIT, color=HEAT if s > 0 else COOL,
                       linewidth=0.9, linestyle=":", zorder=1)
    pad = 0.15 * max(hi - lo, 10)
    a2.set_ylim(min(lo, 0) - pad, max(hi, 0) + pad)
    a2.set_ylabel("Signed PWM\n(+ heat, − cool)", color=TEXT)
    a2.set_xlabel("Time from the 30 → 35 °C setpoint step  (s)", color=TEXT)
    fig.text(0.01, 0.01,
             f"Data: {spec.source}, run {spec.data_run}, control ON rows.\n"
             f"Setpoint steps 30 → 35 → 30 °C, PWM limit {PWM_LIMIT}, "
             "anti-windup on. Stage values are means of its last 30 s, or of "
             "whole cycles if still oscillating.\nReadings every 0.56 s, each "
             "the mean of 1000 ADC samples. Red: heating command. Blue: "
             "cooling command.",
             fontsize=7.6, color="#595959", va="bottom")
    fig.subplots_adjust(left=0.1, right=0.985, top=0.885, bottom=0.2)
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


def reference_figure(series, path, figsize=(11.0, 8.6), fs=10.0,
                     title=None, note="", temp_label="Temperature (°C)",
                     dpi=200):
    """Laid out like the course reference figure: P on the left, PI on the
    right, output above input, the three gains overlaid, darker for higher
    gain. Top block is the 30 -> 35 C step, bottom block the 35 -> 30 C step.

    series[run] is a cut-like dict with time_s, temperature_C, pwm_sent, on,
    i_up, up_end, i_down, end and spec."""
    fig = plt.figure(figsize=figsize)
    fig.patch.set_facecolor("white")
    outer = fig.add_gridspec(2, 2, left=0.085, right=0.975,
                             top=0.93 if title else 0.955,
                             bottom=0.125, hspace=0.3, wspace=0.17)
    arrows = {("up", 0): ((0.46, 0.10), (0.56, 0.72)),
              ("up", 1): ((0.46, 0.30), (0.56, 0.90)),
              ("down", 0): ((0.70, 0.04), (0.80, 0.40)),
              ("down", 1): ((0.70, 0.06), (0.80, 0.70))}
    for row, which in enumerate(("up", "down")):
        for col, group in enumerate(((1, 2, 3), (4, 5, 6))):
            inner = outer[row, col].subgridspec(2, 1, height_ratios=[1.7, 1.0],
                                                hspace=0.07)
            a1 = fig.add_subplot(inner[0])
            a2 = fig.add_subplot(inner[1], sharex=a1)
            for ax in (a1, a2):
                style(ax)
                ax.grid(True, color="#E4E4E4", linewidth=0.6)
            for run in reversed(group):
                s = series[run]
                spec = s["spec"]
                i0 = s["i_up"] if which == "up" else s["i_down"]
                i1 = s["up_end"] if which == "up" else s["end"]
                t = s["time_s"] - s["time_s"][i0]
                idx = np.arange(len(t))
                m = ((t >= REF_WINDOW[0]) & (t <= REF_WINDOW[1])
                     & (idx <= i1) & s["on"])
                c = LEVEL_COLORS[spec.level]
                lab = (f"$K_p$ = {spec.kp:g}" if spec.mode == "P"
                       else f"$K_i$ = {spec.ki:g}")
                a1.plot(np.where(m, t, np.nan), s["temperature_C"], color=c,
                        linewidth=1.0, label=f"Run {run}, {lab}")
                u = np.where(m, s["pwm_sent"], np.nan)
                a2.plot(np.repeat(np.where(m, t, np.nan), 2)[1:],
                        np.repeat(u, 2)[:-1], color=c, linewidth=0.8)
            sp = (30.0, 35.0) if which == "up" else (35.0, 30.0)
            a1.plot([REF_WINDOW[0], 0, 0, REF_WINDOW[1]],
                    [sp[0], sp[0], sp[1], sp[1]], color=SET, linewidth=0.9,
                    linestyle="--", zorder=1)
            a1.set_xlim(*REF_WINDOW)
            a1.set_ylim(*T_LIM)
            a1.set_yticks(range(26, 43, 4))
            a1.tick_params(axis="x", labelbottom=False)
            for sign in (1, -1):
                a2.axhline(sign * PWM_LIMIT, color=HEAT if sign > 0 else COOL,
                           linewidth=0.6, linestyle=":", zorder=1)
            a2.axhline(0, color="#868686", linewidth=0.6, zorder=1)
            a2.set_ylim(-300, 300)
            a2.set_yticks([-255, 0, 255])
            (x0, y0), (x1, y1) = arrows[(which, col)]
            a1.annotate("", xy=(x1, y1), xytext=(x0, y0),
                        xycoords="axes fraction",
                        arrowprops=dict(arrowstyle="-|>", color="#333333",
                                        linewidth=0.9))
            a1.text(x1 + 0.01, y1, "$K_p$" if col == 0 else "$K_i$",
                    transform=a1.transAxes, fontsize=fs + 1, color="#333333",
                    va="bottom")
            step = "30 → 35 °C" if which == "up" else "35 → 30 °C"
            head = ("(a) P control" if col == 0
                    else "(b) PI control, $K_p$ = 12 PWM/°C")
            a1.set_title(f"{head}: step {step}", fontsize=fs, color=TEXT, pad=3)
            if col == 0:
                a1.set_ylabel(f"Output: {temp_label}", color=TEXT)
                a2.set_ylabel("Input: PWM", color=TEXT)
            if which == "up":
                h, l = a1.get_legend_handles_labels()
                leg = a1.legend(h[::-1], l[::-1], loc="lower right",
                                fontsize=fs - 1.2, frameon=True)
                leg.get_frame().set_edgecolor("#BFBFBF")
            if row == 1:
                a2.set_xlabel("Time from the setpoint step (s)", color=TEXT)
    if title:
        fig.suptitle(title, fontsize=fs + 2, color=TEXT, y=0.985)
    if note:
        fig.text(0.01, 0.008, note, fontsize=fs - 1.3, color="#595959",
                 va="bottom")
    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)


def high_gain_figure(cuts, metrics, path, figsize=(11.0, 6.4), fs=10.0,
                     dpi=200, note=True, text=True):
    """Zoom on the four steps the A3 metrics are quoted for."""
    fig, axes = plt.subplots(2, 2, figsize=figsize,
                             gridspec_kw={"hspace": 0.5,
                                          "wspace": 0.72 if text else 0.18})
    fig.patch.set_facecolor("white")
    for row, run in enumerate((3, 6)):
        r = cuts[run]
        for col, which in enumerate(("up", "down")):
            ax = axes[row][col]
            style(ax)
            ax.grid(True, color="#E4E4E4", linewidth=0.6)
            m = next(x for x in metrics if x["run"] == run and x["step"] == which)
            t = r["time_s"] - m["step_time_s"]
            win = (t >= -10) & (t <= m["stage_length_s"]) & r["on"]
            if m["sustained"]:
                ax.axhspan(m["cycle_min_C"], m["cycle_max_C"], color="#F2E3D5",
                           zorder=0, linewidth=0)
            else:
                ax.axhspan(m["T_final_C"] - m["settle_band_C"],
                           m["T_final_C"] + m["settle_band_C"], color="#D5E8D4",
                           zorder=0, linewidth=0)
            ax.plot(np.where(win, t, np.nan), r["temperature_C"], color=TEMP,
                    linewidth=1.1)
            sp = (30.0, 35.0) if which == "up" else (35.0, 30.0)
            ax.plot([-10, 0, 0, m["stage_length_s"]], [sp[0], sp[0], sp[1], sp[1]],
                    color=SET, linewidth=0.9, linestyle="--")
            ax.axhline(m["T_final_C"], color=TEMP, linewidth=0.7, linestyle=":")
            if np.isfinite(m["settling_2pct_s"]):
                ax.axvline(m["settling_2pct_s"], color="#868686", linewidth=0.8,
                           linestyle="-.")
            ax.set_xlim(-10, m["stage_length_s"] + 2)
            spec = r["spec"]
            g = (f"P, $K_p$ = {spec.kp:g}" if spec.mode == "P"
                 else f"PI, $K_p$ = {spec.kp:g}, $K_i$ = {spec.ki:g}")
            step = "30 → 35 °C" if which == "up" else "35 → 30 °C"
            ax.set_title(f"Run {run} ({g}), {step}", fontsize=fs, color=TEXT, pad=3)
            stl = (f"{m['settling_2pct_s']:.0f} s"
                   if np.isfinite(m["settling_2pct_s"]) else "none (sustained)")
            per = (f"{m['period_s']:.1f} s" if np.isfinite(m["period_s"]) else "n/a")
            if m["starts_mid_cycle"]:
                lines = ["rise, overshoot: n/a", "(step starts mid-cycle)"]
            else:
                lines = [f"rise {m['rise_10_90_s']:.1f} s",
                         f"first overshoot {m['overshoot_C']:.2f} °C "
                         f"({m['overshoot_pct']:.0f} %)"]
            lines += [f"settling {stl}",
                      f"mean error {round(m['ss_error_C'], 2) + 0.0:+.2f} °C",
                      f"period {per}"]
            if m["sustained"]:
                lines.append(f"cycle {m['cycle_min_C']:.1f} to "
                             f"{m['cycle_max_C']:.1f} °C")
            if text:
                ax.text(1.03, 0.5, "\n".join(lines), transform=ax.transAxes,
                        fontsize=fs - 1.6, color=TEXT, ha="left", va="center",
                        linespacing=1.35)
            if col == 0:
                ax.set_ylabel("Temperature (°C)", color=TEXT)
            if row == 1:
                ax.set_xlabel("Time from the setpoint step (s)", color=TEXT)
    if note:
        fig.text(0.01, 0.008,
                 "Rise: 10 % to 90 % of the change. Final value: mean of the "
                 "last 30 s, or of whole cycles in the last 90 s when the "
                 "stage is still oscillating (dotted line).\nGreen band: final "
                 "value ±2 % of the step (settling threshold); dash-dot line: "
                 "settling time. Tan band: range of the sustained oscillation "
                 "in the last 90 s.\nPeriod of a sustained oscillation: mean "
                 "spacing of upward crossings of its mean (0.3 °C hysteresis).",
                 fontsize=fs - 1.6, color="#595959", va="bottom")
    fig.subplots_adjust(left=0.07, right=0.79 if text else 0.99, top=0.95,
                        bottom=0.2 if note else 0.11)
    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------------

def collect():
    cuts, metrics = {}, []
    for label, spec in list(RUNS.items()) + list(EARLIER.items()):
        r = cut(spec)
        cuts[label] = r
        metrics += list(run_metrics(r, label))
    return cuts, metrics


def write_metrics(metrics, path):
    keys = list(metrics[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(keys)
        for m in metrics:
            w.writerow([f"{v:.3f}" if isinstance(v, float) else v
                        for v in (m[k] for k in keys)])


def main():
    house_style()
    os.makedirs(FIG_DIR, exist_ok=True)
    cuts, metrics = collect()
    for label, r in cuts.items():
        up, down = [m for m in metrics if m["run"] == label]
        run_figure(r, label, up, down,
                   os.path.join(FIG_DIR, r["spec"].stem + ".png"))
    six = {k: cuts[k] for k in RUNS}
    reference_figure(six, os.path.join(FIG_DIR, "overlay_p_and_pi.png"),
                     title="Measured step responses: three P gains and three "
                           "PI gains",
                     note="Runs 1, 2, 4, 5 on 13 October, Runs 3 and 6 on 14 "
                          "October; same setpoints, PWM limit 255, anti-windup "
                          "on. Control-on rows only. Kp in PWM/°C, Ki in "
                          "PWM/(°C s).")
    high_gain_figure(cuts, metrics, os.path.join(FIG_DIR, "high_gain_steps.png"))
    write_metrics(metrics, METRICS_CSV)

    print(f"{'run':>10} {'step':>4} {'Ti':>6} {'Tf':>6} {'rise':>6} "
          f"{'over%':>6} {'settle':>7} {'sserr':>6} {'period':>6} {'sust':>4} "
          f"{'p2p':>5} {'lim%':>5} {'held%':>5}")
    for m in metrics:
        print(f"{str(m['run']):>10} {m['step']:>4} {m['T_initial_C']:6.2f} "
              f"{m['T_final_C']:6.2f} {m['rise_10_90_s']:6.1f} "
              f"{m['overshoot_pct']:6.1f} {m['settling_2pct_s']:7.1f} "
              f"{m['ss_error_C']:+6.2f} {m['period_s']:6.1f} "
              f"{m['sustained']:4d} {m['cycle_p2p_C']:5.2f} "
              f"{m['at_limit_pct']:5.1f} {m['q_held_pct']:5.1f}")
    print(f"\nFigures in {FIG_DIR}, metrics in {METRICS_CSV}")


if __name__ == "__main__":
    main()
