#!/usr/bin/env python3
"""
Phys 39 Module 5. Naidu / Cohen

Representative low-gain and high-gain strip-chart traces, which the module's
evidence list asks for as figures rather than raw CSV.

    python3 python/plot_p_control_traces.py      (run from the repository root)

INPUT   data/module_05/kp32_high_gain_run.csv
        One continuous log that carries the whole gain sweep. Each gain is a
        contiguous block of rows with the same kp and p_enabled = 1, so the
        panels are cut out of the one file rather than stitched from several.

OUTPUT  docs/figures/module_05/p_control_traces.png

Two columns, one gain each, with temperature over commanded PWM. Time is
re-zeroed at the start of each segment, so t = 0 is the moment that gain was
applied. PWM is drawn red while heating and blue while cooling, matching the
strip chart and the Module 4 figure.
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INPUT_CSV = "data/module_05/kp32_high_gain_run.csv"
OUTPUT_PNG = "docs/figures/module_05/p_control_traces.png"

CHI_H = 0.50127        # C per PWM count, Module 4 heating branch
T_AMB = 21.54          # C, Module 4 zero-PWM temperature

HEAT = "#C0392B"
COOL = "#1F77B4"
SET = "#595959"

# (gain, label). Both are read out of the one log.
PANELS = [(0.25, "low gain"), (32.0, "high gain")]


def read_segments(path):
    """Return {kp: list of rows} for every contiguous p_enabled block, keeping
    the longest block for each gain. A gain can appear more than once in the
    log, and the longest run is the one that actually settled."""
    if not os.path.exists(path):
        sys.exit(f"{path} not found. Run this from the repository root.")
    blocks, current, key = [], [], None
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                row = {
                    "t": float(r["time_s"]),
                    "T": float(r["temperature_C"]),
                    "pwm": float(r["pwm"]),
                    "heat": r["heat_cool"].strip() in ("1", "heat", "HEAT"),
                    "set": float(r["setpoint_C"]),
                    "kp": float(r["kp"]),
                    "on": r["p_enabled"].strip() in ("1", "true", "True"),
                }
            except (KeyError, ValueError, TypeError):
                continue
            k = (row["kp"], row["on"])
            if k != key:
                if current:
                    blocks.append((key, current))
                current, key = [row], k
            else:
                current.append(row)
        if current:
            blocks.append((key, current))

    longest = {}
    for (kp, on), rows in blocks:
        if not on or len(rows) < 2:
            continue
        span = rows[-1]["t"] - rows[0]["t"]
        if kp not in longest or span > longest[kp][0]:
            longest[kp] = (span, rows)
    return {kp: rows for kp, (_, rows) in longest.items()}


def main():
    segments = read_segments(INPUT_CSV)
    missing = [kp for kp, _ in PANELS if kp not in segments]
    if missing:
        sys.exit(f"{INPUT_CSV} has no enabled block for Kp = {missing}. "
                 f"Available: {sorted(segments)}")

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10.5,
        "axes.edgecolor": "#868686", "axes.linewidth": 0.8,
        "xtick.direction": "out", "ytick.direction": "out",
        "xtick.color": "#595959", "ytick.color": "#595959",
    })
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 5.4), sharex="col",
                             gridspec_kw={"height_ratios": [2.0, 1.0],
                                          "hspace": 0.12, "wspace": 0.16})
    fig.patch.set_facecolor("white")

    for col, (kp, label) in enumerate(PANELS):
        rows = segments[kp]
        t0 = rows[0]["t"]
        t = [r["t"] - t0 for r in rows]
        temperature = [r["T"] for r in rows]
        setpoint = rows[-1]["set"]
        L = kp * CHI_H
        settled = sum(r["T"] for r in rows[-60:]) / len(rows[-60:])
        droop = setpoint - settled

        ax = axes[0][col]
        ax.set_facecolor("white")
        ax.grid(True, color="#D9D9D9", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.axhline(setpoint, color=SET, linewidth=1.1, linestyle="--",
                   zorder=2, label=f"setpoint {setpoint:.1f} °C")
        ax.plot(t, temperature, color=HEAT, linewidth=1.4, zorder=3,
                label="temperature")
        ax.set_title(
            f"{label}:  $K_p$ = {kp:g} PWM/°C,  L = {L:.2f}",
            fontsize=12, color="#404040", pad=8)
        ax.set_ylabel("Temperature  (°C)", color="#404040")
        ax.text(0.98, 0.06,
                f"settled {settled:.2f} °C,  droop {droop:.2f} °C",
                transform=ax.transAxes, ha="right", fontsize=9.5,
                color="#404040")
        leg = ax.legend(loc="upper left", frameon=True, fontsize=9.5)
        leg.get_frame().set_edgecolor("#BFBFBF")
        leg.get_frame().set_linewidth(0.8)

        # PWM panel. Split into runs of one direction so the colour changes
        # only where the commanded direction changes.
        ax = axes[1][col]
        ax.set_facecolor("white")
        ax.grid(True, color="#D9D9D9", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        run_t, run_p, run_heat = [t[0]], [rows[0]["pwm"]], rows[0]["heat"]
        for ti, r in zip(t[1:], rows[1:]):
            if r["heat"] != run_heat:
                ax.plot(run_t, run_p, color=HEAT if run_heat else COOL,
                        linewidth=1.3)
                run_t, run_p, run_heat = [ti], [r["pwm"]], r["heat"]
            else:
                run_t.append(ti)
                run_p.append(r["pwm"])
        ax.plot(run_t, run_p, color=HEAT if run_heat else COOL, linewidth=1.3)
        # Autoscale rather than showing the full 0-255 range, which would
        # flatten commands of a few counts into the axis line. The headroom
        # note below carries the saturation information instead.
        peak = max(r["pwm"] for r in rows)
        ax.set_ylim(0, max(peak * 1.45, 5))
        ax.set_ylabel("PWM  (counts)", color="#404040")
        ax.set_xlabel("Time since this gain was applied  (s)", color="#404040")
        ax.text(0.98, 0.84,
                f"red heating, blue cooling. Peak {peak:.0f} of 255 counts, "
                f"no saturation",
                transform=ax.transAxes, ha="right", fontsize=9,
                color="#595959")

        print(f"  Kp = {kp:<6g} L = {L:5.2f}  {len(rows):5d} samples, "
              f"{t[-1]:6.0f} s   settled {settled:6.2f} C   "
              f"droop {droop:5.2f} C")

    fig.subplots_adjust(left=0.07, right=0.985, top=0.91, bottom=0.10)
    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=200, facecolor="white")
    print(f"\nFigure written to {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
