#!/usr/bin/env python3
"""
Phys 39 Module 7, Part 1. Thermistor cross-check (calibration). Naidu / Cohen

    python3 python/analysis/rod_calibration.py data/module_08/rod_run_....csv [--t0 S --t1 S] [--ref mean|base|R1...]

With every sensor at nearly the same temperature (TEC off, rod left alone
long enough to reach room temperature, at least 60 s of data), each channel
should read the same. The difference between a channel and the reference
over that window is its offset.

Reference: the mean of all channels (default), or one named channel.
Window: --t0 and --t1 in Arduino seconds (time_s). Without them, the first
control-off stretch of the run is used if it is at least 60 s long.

OUTPUT (never changes the raw run file)
    data/module_08/calibration_<run>.csv     channel, mean, sd, sem, offset
    data/module_08/calibration_<run>.txt     the printed summary
    docs/figures/module_08/calibration_<run>.png

An offset is worth correcting only if it is clearly larger than its own
uncertainty AND large compared with the temperature differences being
measured. The summary prints both comparisons; the decision is recorded in
docs/module_notes/module_08_rod_instrument.md.
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


def default_window(cols):
    t, on = cols["time_s"], cols["control_on"] == 1
    if on.size == 0:
        return None
    idx = np.flatnonzero(on)
    end = idx[0] - 1 if idx.size else len(t) - 1
    if end <= 0 or t[end] - t[0] < 60.0:
        return None
    return t[0], t[end]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--t0", type=float)
    ap.add_argument("--t1", type=float)
    ap.add_argument("--ref", default="mean")
    a = ap.parse_args()

    cols, channels = rd.load_run(a.run)
    t = cols["time_s"]
    if a.t0 is None or a.t1 is None:
        w = default_window(cols)
        if w is None:
            raise SystemExit("Give --t0 and --t1: no control-off stretch of "
                             "60 s or more at the start of this run.")
        a.t0, a.t1 = w
    m = rd.window(t, a.t0, a.t1)
    if t[m].size == 0 or t[m][-1] - t[m][0] < 60.0:
        print("!!! the window is shorter than the 60 s the assignment asks for !!!")

    series = rd.channel_series(cols, channels)
    stats = {name: rd.mean_and_sem(v[m], t[m]) for name, v in series.items()}
    if a.ref == "mean":
        ref = np.nanmean(np.vstack([series[n][m] for n in series]), axis=0)
        ref_mean = np.nanmean([s[0] for s in stats.values()])
        ref_label = "mean of all channels"
    else:
        ref = series[a.ref][m]
        ref_mean = stats[a.ref][0]
        ref_label = a.ref

    stem = os.path.splitext(os.path.basename(a.run))[0]
    positions = rd.load_sensor_map()
    out = io.StringIO()
    with redirect_stdout(out):
        print(f"Run {a.run}")
        print(f"Window {a.t0:.1f} to {a.t1:.1f} s "
              f"({t[m][-1] - t[m][0]:.0f} s, {m.sum()} rows); "
              f"reference: {ref_label} = {ref_mean:.3f} C")
        print(f"{'channel':>8} {'x (mm)':>8} {'mean (C)':>9} {'sd':>6} "
              f"{'sem':>6} {'offset':>7} {'offset/sem':>10}")
        rows = []
        for name, (mu, sd, sem) in stats.items():
            off = mu - ref_mean
            x = positions.get(name, (np.nan, np.nan))[0] * 1000
            ratio = abs(off) / sem if sem > 0 else np.inf
            rows.append((name, mu, sd, sem, off))
            print(f"{name:>8} {x:8.1f} {mu:9.3f} {sd:6.3f} {sem:6.3f} "
                  f"{off:+7.3f} {ratio:10.1f}")
        spread = max(r[4] for r in rows) - min(r[4] for r in rows)
        print(f"Spread of offsets: {spread:.3f} C")
        xs = [(positions[r[0]][0], r[4]) for r in rows if r[0] in positions]
        if len(xs) >= 3:
            x, o = np.array(xs).T
            slope = np.polyfit(x, o, 1)[0]
            print(f"Offset against position: slope {slope * 0.01:+.4f} C per cm. "
                  "A clear trend with position means the rod was not at one "
                  "temperature, not that the sensors disagree.")
    text = out.getvalue()
    print(text)

    os.makedirs(rd.FIG_DIR, exist_ok=True)
    with open(os.path.join(rd.DATA_DIR, f"calibration_{stem}.csv"), "w") as fh:
        fh.write("channel,mean_C,sd_C,sem_C,offset_C,t0_s,t1_s,reference\n")
        for name, mu, sd, sem, off in rows:
            fh.write(f"{name},{mu:.4f},{sd:.4f},{sem:.4f},{off:.4f},"
                     f"{a.t0:.2f},{a.t1:.2f},{ref_label}\n")
    with open(os.path.join(rd.DATA_DIR, f"calibration_{stem}.txt"), "w") as fh:
        fh.write(f"python3 python/analysis/rod_calibration.py {a.run} "
                 f"--t0 {a.t0:.2f} --t1 {a.t1:.2f} --ref {a.ref}\n\n" + text)

    fig, ax = plt.subplots(figsize=(9, 4.6))
    for name, v in series.items():
        ax.plot(t[m], v[m] - ref, lw=1.0, label=name)
    ax.axhline(0, color="#888888", lw=0.8)
    ax.set_xlabel("Arduino time (s)")
    ax.set_ylabel(f"channel − reference (°C)")
    ax.set_title(f"Cross-check, all sensors at one temperature ({ref_label})",
                 fontsize=10)
    ax.grid(True, color="#E4E4E4")
    ax.legend(fontsize=8, ncol=3)
    fig.tight_layout()
    path = os.path.join(rd.FIG_DIR, f"calibration_{stem}.png")
    fig.savefig(path, dpi=180)
    print(f"Wrote {os.path.join(rd.DATA_DIR, 'calibration_' + stem)}.csv and .txt, and {path}")


if __name__ == "__main__":
    main()
