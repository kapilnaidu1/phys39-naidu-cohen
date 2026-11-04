"""Plot an Angstrom GUI run file: setpoint, TEC, T1 to T5 and signed PWM.

Works on a finished file or on one the GUI is still writing.

    python3 python/analysis/plot_angstrom_run.py                  # newest run, once
    python3 python/analysis/plot_angstrom_run.py --live           # redraw every 5 s
    python3 python/analysis/plot_angstrom_run.py <file.csv> --save out.png

Temperatures are raw (no calibration offsets). Rows that cannot be parsed,
such as a half-written last line, are skipped.
"""
import argparse
import csv
import glob
import os

import numpy as np
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data", "module_08"))
NUM = ["time_ms", "run_state", "step", "setpoint_C", "TEC_C",
       "T1_C", "T2_C", "T3_C", "T4_C", "T5_C", "signed_pwm"]


def newest_run():
    files = [f for f in glob.glob(os.path.join(DATA, "angstrom_live_*.csv"))
             if not f.endswith("_notes.csv")]
    if not files:
        raise SystemExit(f"no angstrom_live_*.csv in {DATA}")
    return max(files, key=os.path.getmtime)


def load(path):
    cols = {k: [] for k in NUM}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                vals = {k: float(row[k]) for k in NUM}
            except (KeyError, TypeError, ValueError):
                continue
            for k in NUM:
                cols[k].append(vals[k])
    return {k: np.array(v) for k, v in cols.items()}


def draw(fig, path):
    d = load(path)
    fig.clear()
    a, b = fig.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    if d["time_ms"].size == 0:
        a.set_title(os.path.basename(path) + ": no complete records yet")
        return
    t = d["time_ms"] / 1000.0
    on = np.isin(d["run_state"], (1, 2))
    a.plot(t, np.where(on, d["setpoint_C"], np.nan), "k--", lw=1, label="setpoint")
    a.plot(t, d["TEC_C"], color="0.35", lw=1, label="TEC")
    for k in ("T1_C", "T2_C", "T3_C", "T4_C", "T5_C"):
        a.plot(t, d[k], lw=1.2, label=k[:2])
    change = np.where(on[1:] & (np.diff(d["step"]) != 0))[0] + 1
    for i in change:
        if d["step"][i] > 1:
            a.axvline(t[i], color="r", lw=0.8, ls=":")
            b.axvline(t[i], color="r", lw=0.8, ls=":")
    a.set_ylabel("Temperature (°C, raw)")
    a.legend(ncol=4, fontsize=8, loc="upper left")
    a.grid(alpha=0.3)
    a.set_title(f"{os.path.basename(path)}   t = {t[-1]:.0f} s   "
                f"T1 {d['T1_C'][-1]:.2f}  T5 {d['T5_C'][-1]:.2f} °C")
    b.plot(t, d["signed_pwm"], "k", lw=0.8)
    b.set_ylabel("signed PWM")
    b.set_xlabel("Arduino time (s)")
    b.grid(alpha=0.3)
    fig.tight_layout()


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file", nargs="?", help="run CSV (default: newest in data/module_08)")
    p.add_argument("--live", action="store_true", help="redraw every --every seconds")
    p.add_argument("--every", type=float, default=5.0)
    p.add_argument("--save", help="write a PNG instead of opening a window")
    args = p.parse_args()
    path = args.file or newest_run()
    print("plotting", path)

    fig = plt.figure(figsize=(11, 7))
    if args.save:
        draw(fig, path)
        fig.savefig(args.save, dpi=120)
        print("saved", args.save)
        return
    if not args.live:
        draw(fig, path)
        plt.show()
        return
    plt.ion()
    plt.show()
    while plt.fignum_exists(fig.number):
        draw(fig, path)
        fig.canvas.draw_idle()
        plt.pause(args.every)


if __name__ == "__main__":
    main()
