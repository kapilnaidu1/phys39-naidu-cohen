#!/usr/bin/env python3
"""
Phys 39 Module 7, Part 1. Multi-point cross-check: each channel at several
common temperatures. Naidu / Cohen

    python3 python/analysis/rod_calibration_multipoint.py data/module_08/rod_run_....csv \
        --windows 100:400 900:1200 1700:2000  [--ref mean|base]

Use when one channel's offset is large, or to show that offsets do not change
with temperature. The thermistors are bundled together (beads touching, taped
flat onto the plate next to the base thermistor, out of sunlight and drafts)
and held at two or more plateaus: for example control off at room
temperature, then PI at 35 C and 45 C. Each --windows entry is the time span
(Arduino seconds) of one steady plateau.

For every channel the script fits
    reading = a + b * reference
over the plateaus, where the reference is the mean of the rod channels
(default; a relative calibration) or the base thermistor (--ref base). If b
is 1 within its uncertainty, a constant offset describes the channel; if not,
the channel's error changes with temperature and the gain must be used too.

OUTPUT (raw data untouched)
    data/module_08/calibration_multipoint_<run>.csv   channel, intercept_C,
        gain, offset_C (mean over plateaus), sem_C (rms fit residual)
    data/module_08/calibration_multipoint_<run>.txt
    docs/figures/module_08/calibration_multipoint_<run>.png
The CSV can be given to the other scripts with --offsets; they apply
T_corrected = (T_raw - intercept) / gain.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--windows", nargs="+", required=True,
                    help="plateaus as t0:t1 in Arduino seconds")
    ap.add_argument("--ref", default="mean", choices=["mean", "base"])
    a = ap.parse_args()

    cols, channels = rd.load_run(a.run)
    t = cols["time_s"]
    series = rd.channel_series(cols, channels)
    wins = [tuple(float(v) for v in w.split(":")) for w in a.windows]
    if len(wins) < 2:
        raise SystemExit("Give at least two plateaus.")

    means = {n: [] for n in series}
    sems = {n: [] for n in series}
    for t0, t1 in wins:
        m = rd.window(t, t0, t1)
        for n, v in series.items():
            mu, sd, sem = rd.mean_and_sem(v[m], t[m])
            means[n].append(mu)
            sems[n].append(sem)
    means = {n: np.array(v) for n, v in means.items()}
    if a.ref == "mean":
        ref = np.nanmean(np.vstack([means[c] for c in channels]), axis=0)
        ref_label = "mean of the rod channels"
    else:
        ref = means["base"]
        ref_label = "base thermistor (A0)"

    stem = os.path.splitext(os.path.basename(a.run))[0]
    rows = []
    out = io.StringIO()
    with redirect_stdout(out):
        print(f"Run {a.run}; reference: {ref_label}")
        print("Plateaus: " + ", ".join(f"{t0:.0f}-{t1:.0f} s (ref {r:.2f} C)"
                                       for (t0, t1), r in zip(wins, ref)))
        print(f"{'channel':>8} " + " ".join(f"{'off@' + format(r, '.1f'):>9}" for r in ref)
              + f" {'gain b':>8} {'+/-':>6} {'intercept a':>12} {'rms res':>8}")
        for n in series:
            y = means[n]
            if len(wins) >= 3:
                (b, a0), cov = np.polyfit(ref, y, 1, cov=True)
                db = np.sqrt(cov[0, 0])
            else:
                b, a0 = np.polyfit(ref, y, 1)
                db = np.nan
            res = y - (a0 + b * ref)
            rms = float(np.sqrt(np.mean(res ** 2)))
            offs = y - ref
            rows.append((n, a0, b, float(np.mean(offs)), max(rms, max(sems[n]))))
            print(f"{n:>8} " + " ".join(f"{o:+9.3f}" for o in offs)
                  + f" {b:8.4f} {db:6.4f} {a0:12.3f} {rms:8.3f}")
        print("\nIf every gain is 1 within its uncertainty and the offsets are the "
              "same at each plateau, a constant offset per channel is enough.")
    text = out.getvalue()
    print(text)

    with open(os.path.join(rd.DATA_DIR, f"calibration_multipoint_{stem}.csv"), "w") as fh:
        fh.write("channel,intercept_C,gain,offset_C,sem_C,reference\n")
        for n, a0, b, off, s in rows:
            fh.write(f"{n},{a0:.4f},{b:.5f},{off:.4f},{s:.4f},{ref_label}\n")
    with open(os.path.join(rd.DATA_DIR, f"calibration_multipoint_{stem}.txt"), "w") as fh:
        fh.write(f"python3 python/analysis/rod_calibration_multipoint.py {a.run} "
                 f"--windows {' '.join(a.windows)} --ref {a.ref}\n\n" + text)

    os.makedirs(rd.FIG_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for n in series:
        ax.errorbar(ref, means[n] - ref, yerr=sems[n], fmt="o-", ms=4,
                    capsize=2, label=n)
    ax.axhline(0, color="#888888", lw=0.8)
    ax.set_xlabel(f"Reference temperature, {ref_label} (°C)")
    ax.set_ylabel("channel − reference (°C)")
    ax.set_title("Offset of each channel at each plateau", fontsize=10)
    ax.grid(True, color="#E4E4E4")
    ax.legend(fontsize=8, ncol=3)
    fig.tight_layout()
    path = os.path.join(rd.FIG_DIR, f"calibration_multipoint_{stem}.png")
    fig.savefig(path, dpi=180)
    print(f"Wrote calibration_multipoint_{stem}.csv/.txt in {rd.DATA_DIR} and {path}")


if __name__ == "__main__":
    main()
