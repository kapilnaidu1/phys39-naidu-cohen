#!/usr/bin/env python3
"""
Phys 39 Module 6 Part I, Part 5. Naidu / Cohen

"Return to the high-gain trace saved in Module 5. Mark the late-time value
T_ss and the first overshoot." Left: the Module 5 Kp = 32 run. Right, for
comparison: the 13 October Kp = 64 run (3a).

    python3 python/plot_part5_overshoot.py      (run from the repository root)

INPUT   data/module_05/session_2026-09-30_full_log.csv   (Kp = 32, first 210 s;
        the 12 V supply was switched off at about 216 s, see the Module 5 note)
        data/module_06/pi_run_20261013_094149.csv        (run 3, Kp = 64)
OUTPUT  docs/figures/module_06/part5_overshoot_marked.png

T_ss is the mean of the final 60 s of the window. The first overshoot is the
first maximum after the trace crosses T_ss.
"""

import csv
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

M5 = "data/module_05/session_2026-09-30_full_log.csv"
M6 = "data/module_06/pi_run_20261013_094149.csv"
OUT = "docs/figures/module_06/part5_overshoot_marked.png"


def module5_kp32():
    rows = list(csv.DictReader(open(M5, newline="")))
    blocks, cur = [], None
    for r in rows:
        key = (r["kp"], r["p_enabled"].strip(), r["setpoint_C"])
        if key != cur:
            blocks.append((key, []))
            cur = key
        blocks[-1][1].append(r)
    b = next(b for k, b in blocks if float(k[0]) == 32 and k[1] in ("1", "True", "true"))
    t = np.array([float(r["time_s"]) for r in b])
    T = np.array([float(r["temperature_C"]) for r in b])
    t -= t[0]
    keep = t <= 210.0
    return t[keep], T[keep], 30.0


def run3a():
    rows = list(csv.DictReader(open(M6, newline="")))
    sel = [r for r in rows if r["run"] == "3" and r["control_on"] == "1"
           and abs(float(r["kp"]) - 64) < 1e-6 and r["setpoint_C"] == "35.00"]
    t = np.array([float(r["time_s"]) for r in sel])
    T = np.array([float(r["temperature_C"]) for r in sel])
    return t - t[0], T, 35.0


def marks(t, T):
    T_ss = T[t >= t[-1] - 60.0].mean()
    cross = np.flatnonzero(T >= T_ss)[0]
    k = cross + int(np.argmax(T[cross:cross + 40]))
    return T_ss, t[k], T[k]


def main():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.edgecolor": "#868686"})
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
    for ax, (t, T, sp), title, xmax in (
            (axes[0], module5_kp32(), "Module 5, P, $K_p$ = 32 (30 Sept)", 40),
            (axes[1], run3a(), "Module 6 Run 3a, P, $K_p$ = 64 (13 Oct)", 60)):
        T_ss, tp, Tp = marks(t, T)
        ax.grid(True, color="#D9D9D9")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.plot(t, T, color="#1E6B3A", linewidth=1.5, marker="o", markersize=2.2,
                label="Measured")
        ax.axhline(T_ss, color="#1F4E79", linestyle="--", linewidth=1.1,
                   label=f"late-time $T_{{ss}}$ = {T_ss:.2f} °C")
        ax.axhline(sp, color="#595959", linestyle=":", linewidth=1.0,
                   label=f"setpoint {sp:g} °C")
        ax.plot([tp], [Tp], marker="v", color="#C0392B", markersize=8, zorder=5)
        ax.annotate(f"first overshoot {Tp - T_ss:+.2f} °C at {tp:.1f} s",
                    xy=(tp, Tp), xytext=(tp + 0.15 * xmax, Tp),
                    color="#C0392B", fontsize=9, va="center",
                    arrowprops=dict(arrowstyle="-", color="#C0392B"))
        ax.set_xlim(0, xmax)
        span = max(Tp - T_ss, 0.02)
        ax.set_ylim(T_ss - 4 * span if xmax == 40 else T.min() - 0.3,
                    max(Tp, sp) + 1.2 * span)
        ax.set_title(title, color="#404040")
        ax.set_xlabel("Time from the gain or setpoint change (s)")
        ax.set_ylabel("Temperature (°C)")
        ax.legend(loc="center right" if xmax == 40 else "lower right", fontsize=8.5)
    fig.text(0.01, 0.01, "The one-lump P solution θ(0)e^(−t/τcl) approaches "
             "T_ss without crossing it. Both measured traces cross T_ss and come "
             "back, which that solution forbids.", fontsize=8, color="#595959")
    fig.subplots_adjust(left=0.07, right=0.99, top=0.9, bottom=0.2, wspace=0.25)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=200, facecolor="white")
    for name, (t, T, sp) in (("Kp 32", module5_kp32()), ("Kp 64", run3a())):
        T_ss, tp, Tp = marks(t, T)
        print(f"{name}: T_ss {T_ss:.3f} C, first overshoot {Tp:.2f} C at {tp:.1f} s "
              f"({Tp - T_ss:+.3f} C)")
    print(f"Figure {OUT}")


if __name__ == "__main__":
    main()
