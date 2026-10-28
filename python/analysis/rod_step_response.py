#!/usr/bin/env python3
"""
Phys 39 Module 7, Part 2. Baseline and step response of the rod. Naidu / Cohen

    python3 python/analysis/rod_step_response.py data/module_08/rod_run_....csv [--t-step S] [--pre 60] [--offsets data/module_08/calibration_....csv]

The step time is, by default, the first moment control is on and the
setpoint changes (or control is switched on). The baseline is the mean of
each channel over --pre seconds before it. For every channel the script
reports, relative to the step:

    dT_end       change from the baseline to the mean of the last 60 s
    t_0.2C       first time the channel is 0.2 C above its baseline: the
                 arrival of the disturbance
    t_50         first time it has made half of its own final change

and plots all channels on one time axis, together with the COMMANDED base
setpoint and the MEASURED base temperature (the measured base is the real
boundary condition).

OUTPUT
    docs/figures/module_08/step_<run>.png
    data/module_08/step_<run>.txt
"""

import argparse
import io
import os
from contextlib import redirect_stdout

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import rod_data as rd

ARRIVAL_C = 0.2


def find_step(cols):
    t, on, sp = cols["time_s"], cols["control_on"] == 1, cols["setpoint_C"]
    for i in range(1, len(t)):
        if on[i] and (not on[i - 1] or sp[i] != sp[i - 1]):
            return t[i]
    raise SystemExit("No step found; give --t-step.")


def first_time(t, mask):
    idx = np.flatnonzero(mask)
    return t[idx[0]] if idx.size else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--t-step", type=float)
    ap.add_argument("--pre", type=float, default=60.0)
    ap.add_argument("--offsets")
    ap.add_argument("--t-start", type=float,
                    help="ignore rows before this Arduino time (s)")
    ap.add_argument("--t-end", type=float,
                    help="ignore rows after this Arduino time (s)")
    ap.add_argument("--sensor-map", help="sensor map for this run "
                    "(default data/module_08/sensor_map.csv)")
    a = ap.parse_args()

    cols, channels = rd.load_run(a.run)
    keep = np.ones(len(cols["time_s"]), bool)
    if a.t_start is not None:
        keep &= cols["time_s"] >= a.t_start
    if a.t_end is not None:
        keep &= cols["time_s"] <= a.t_end
    cols = {k: v[keep] for k, v in cols.items()}
    offsets = rd.load_offsets(a.offsets) if a.offsets else None
    series = rd.channel_series(cols, channels, offsets)
    t = cols["time_s"]
    ts = a.t_step if a.t_step is not None else find_step(cols)
    pre = rd.window(t, ts - a.pre, ts - 1e-9)
    post = t >= ts
    end = t >= t[-1] - 60.0
    positions = rd.load_sensor_map(a.sensor_map)
    stem = os.path.splitext(os.path.basename(a.run))[0]
    if a.t_start is not None or a.t_end is not None:
        # one run can hold several steps; keep one output per segment
        stem += (f"_t{a.t_start:.0f}" if a.t_start is not None else "_t0") \
            + (f"-{a.t_end:.0f}" if a.t_end is not None else "-end")

    res = {}
    out = io.StringIO()
    with redirect_stdout(out):
        print(f"Run {a.run}; step at t = {ts:.1f} s; baseline {a.pre:.0f} s "
              f"before it; final value = mean of the last 60 s "
              f"(run ends {t[-1] - ts:.0f} s after the step)")
        if offsets:
            print(f"Offsets subtracted from {a.offsets}")
        print(f"Commanded setpoint after the step: "
              f"{cols['setpoint_C'][post][0]:.2f} C")
        print(f"{'channel':>8} {'x (mm)':>7} {'base (C)':>9} {'dT_end':>7} "
              f"{'t_0.2C (s)':>10} {'t_50 (s)':>9}")
        for name, v in series.items():
            b0 = np.nanmean(v[pre])
            dT = np.nanmean(v[end]) - b0
            rel = v - b0
            t_arr = first_time(t, post & (rel * np.sign(dT) > ARRIVAL_C)) - ts
            t50 = first_time(t, post & (rel * np.sign(dT) > 0.5 * abs(dT))) - ts
            x = positions.get(name, (np.nan, np.nan))[0] * 1000
            res[name] = (x, b0, dT, t_arr, t50)
            print(f"{name:>8} {x:7.1f} {b0:9.3f} {dT:+7.3f} {t_arr:10.1f} "
                  f"{t50:9.1f}")
    text = out.getvalue()
    print(text)
    with open(os.path.join(rd.DATA_DIR, f"step_{stem}.txt"), "w") as fh:
        fh.write(f"python3 python/analysis/rod_step_response.py {a.run} "
                 f"--t-step {ts:.2f} --pre {a.pre:g}"
                 + (f" --t-start {a.t_start:g}" if a.t_start is not None else "")
                 + (f" --t-end {a.t_end:g}" if a.t_end is not None else "")
                 + (f" --sensor-map {a.sensor_map}" if a.sensor_map else "")
                 + (f" --offsets {a.offsets}" if a.offsets else "")
                 + "\n\n" + text)

    have_x = sum(np.isfinite(r[0]) for r in res.values()) >= 2
    fig, axes = plt.subplots(1, 2 if have_x else 1, figsize=(12 if have_x else 8, 4.8),
                             squeeze=False)
    ax = axes[0][0]
    # the setpoint is only a command while control is on
    sp = np.where(cols["control_on"] == 1, cols["setpoint_C"], np.nan)
    ax.plot(t - ts, sp, color="#7f7f7f", ls="--", lw=1.2,
            label="base setpoint (commanded, control on)")
    for name, v in series.items():
        lw = 2.0 if name == "base" else 1.2
        lab = "base, measured (A0)" if name == "base" else name
        ax.plot(t - ts, v, lw=lw, label=lab)
    for tn, note in rd.load_notes(a.run):
        if np.isfinite(tn) and t[0] <= tn <= t[-1]:
            ax.axvline(tn - ts, color="#BBBBBB", lw=0.8)
            ax.text(tn - ts, ax.get_ylim()[1], note, rotation=90, fontsize=7,
                    va="top", ha="right", color="#666666")
    ax.set_xlabel("Time from the base step (s)")
    ax.set_ylabel("Temperature (°C)")
    ax.set_title("Step response, all channels on one time axis", fontsize=10)
    ax.grid(True, color="#E4E4E4")
    ax.legend(fontsize=8)
    if have_x:
        ax2 = axes[0][1]
        rod = [(r[0], r[2], r[3]) for n, r in res.items()   # x already in mm
               if n != "base" and np.isfinite(r[0])]
        rod.sort()
        x, dT, tarr = (np.array(c) for c in zip(*rod))
        ax2.plot(x, dT, "o-", color="#C0392B", label="final change dT_end (°C)")
        ax2.set_xlabel("Position along the rod (mm)")
        ax2.set_ylabel("Final change (°C)", color="#C0392B")
        ax2.grid(True, color="#E4E4E4")
        ax3 = ax2.twinx()
        ax3.plot(x, tarr, "s--", color="#1F4E79", label="arrival t_0.2C (s)")
        ax3.set_ylabel(f"Arrival time, +{ARRIVAL_C} °C (s)", color="#1F4E79")
        ax2.set_title("Farther sensors: later and smaller", fontsize=10)
    fig.tight_layout()
    os.makedirs(rd.FIG_DIR, exist_ok=True)
    path = os.path.join(rd.FIG_DIR, f"step_{stem}.png")
    fig.savefig(path, dpi=180)
    print(f"Wrote {path} and {os.path.join(rd.DATA_DIR, 'step_' + stem)}.txt")


if __name__ == "__main__":
    main()
