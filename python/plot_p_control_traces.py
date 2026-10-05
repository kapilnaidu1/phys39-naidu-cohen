#!/usr/bin/env python3
"""
Phys 39 Module 5. Naidu / Cohen

Representative low-gain and high-gain strip-chart traces, which the module's
evidence list asks for as figures rather than raw CSV.

    python3 python/plot_p_control_traces.py      (run from the repository root)

INPUT   data/module_05/session_2026-09-30_full_log.csv
        The complete live log of the 30 September session, copied from
        p_control_run.csv with every value unchanged (Git stores it with LF
        line endings where the GUI wrote CRLF). The kp_*_run.csv files are
        earlier snapshots of this same log and stop partway through. Each gain
        is a contiguous block of rows with the same kp and setpoint, so the
        panels are cut out of the one file rather than stitched from several.

VALID WINDOW FOR Kp = 32
        From about 216 s after Kp = 32 was applied, the plate falls steadily
        while the commanded heating climbs to 149 counts: the plate stops
        following the command. Only the first 210 s are plotted, and the
        settled value is taken from that window. See the Module 5 note.

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

INPUT_CSV = "data/module_05/session_2026-09-30_full_log.csv"
OUTPUT_PNG = "docs/figures/module_05/p_control_traces.png"

CHI_H = 0.50127        # C per PWM count, Module 4 heating branch
T_AMB = 21.54          # C, Module 4 zero-PWM temperature

HEAT = "#C0392B"
COOL = "#1F77B4"
SET = "#595959"
PRED = "#1F4E79"

SETPOINT = 30.0        # C, every panel uses the heating setpoint
SETTLE_WINDOW = 60.0   # s, the settled value is the mean of this final span

# (gain, label, last valid second after the gain was applied or None)
PANELS = [(0.25, "low gain", None), (32.0, "high gain", 210.0)]


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
            k = (row["kp"], row["on"], row["set"])
            if k != key:
                if current:
                    blocks.append((key, current))
                current, key = [row], k
            else:
                current.append(row)
        if current:
            blocks.append((key, current))

    longest = {}
    for (kp, on, setpoint), rows in blocks:
        if not on or len(rows) < 2 or abs(setpoint - SETPOINT) > 1e-6:
            continue
        span = rows[-1]["t"] - rows[0]["t"]
        if kp not in longest or span > longest[kp][0]:
            longest[kp] = (span, rows)
    return {kp: rows for kp, (_, rows) in longest.items()}


def main():
    segments = read_segments(INPUT_CSV)
    missing = [kp for kp, _, _ in PANELS if kp not in segments]
    if missing:
        sys.exit(f"{INPUT_CSV} has no enabled block for Kp = {missing}. "
                 f"Available: {sorted(segments)}")

    # Same conventions as docs/figures/module_04 and the droop figure: white
    # plot area, light grey gridlines, no top or right spine, the numbers as
    # plain coloured text at the top left, a plain legend, and a small grey
    # note under the whole figure. Nothing boxed or decorated.
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.edgecolor": "#868686", "axes.linewidth": 0.8,
        "xtick.direction": "out", "ytick.direction": "out",
        "xtick.color": "#595959", "ytick.color": "#595959",
    })
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 5.6), sharex="col",
                             gridspec_kw={"height_ratios": [2.1, 1.0],
                                          "hspace": 0.13, "wspace": 0.145})
    fig.patch.set_facecolor("white")

    def style(ax):
        ax.set_facecolor("white")
        ax.grid(True, which="major", color="#D9D9D9", linewidth=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    summary = []
    for col, (kp, label, limit) in enumerate(PANELS):
        rows = segments[kp]
        t0 = rows[0]["t"]
        if limit is not None:
            rows = [r for r in rows if r["t"] - t0 <= limit]
        t = [r["t"] - t0 for r in rows]
        temperature = [r["T"] for r in rows]
        setpoint = rows[-1]["set"]
        L = kp * CHI_H
        tail = [r["T"] for r in rows if r["t"] >= rows[-1]["t"] - SETTLE_WINDOW]
        settled = sum(tail) / len(tail)
        droop = setpoint - settled
        predicted = (setpoint - T_AMB) / (1.0 + L)
        peak = max(r["pwm"] for r in rows)

        ax = axes[0][col]
        style(ax)
        ax.axhline(setpoint, color=SET, linewidth=1.2, linestyle="--",
                   zorder=2, label=f"Setpoint {setpoint:.1f} \u00b0C")
        ax.plot(t, temperature, color=HEAT, linewidth=1.5, zorder=3,
                label="Measured temperature")
        ax.set_title(f"{label}:  $K_p$ = {kp:g} PWM per \u00b0C,  L = {L:.2f}",
                     fontsize=11.5, color="#404040", pad=8)
        # sharex hides the labels on this upper panel, since both panels run on
        # the same clock and the axis is labelled once underneath. Keep the
        # tick marks visible so the shared axis reads as deliberate rather
        # than missing.
        ax.tick_params(axis="x", which="both", bottom=True, labelbottom=False,
                       length=3.5, color="#868686")
        ax.set_ylabel("Temperature  (\u00b0C)", color="#404040")

        # Equation-style annotation at the top left, in the series colour,
        # matching the Module 4 and droop figures.
        ax.text(0.03, 0.95,
                f"Settled:  T = {settled:.2f} \u00b0C,  droop = {droop:.2f} "
                f"\u00b0C", transform=ax.transAxes, fontsize=9.5,
                color=HEAT, va="top")
        ax.text(0.03, 0.855,
                f"Model 1/(1+L):  droop = {predicted:.2f} \u00b0C",
                transform=ax.transAxes, fontsize=9.5, color=PRED, va="top")

        # Leave headroom so the text never collides with the trace.
        lo, hi = min(temperature), max(max(temperature), setpoint)
        span = hi - lo
        ax.set_ylim(lo - span * 0.08, hi + span * 0.30)

        leg = ax.legend(loc="best", frameon=True, fontsize=9)
        leg.get_frame().set_edgecolor("#BFBFBF")
        leg.get_frame().set_linewidth(0.8)

        # PWM panel. Split into runs of one direction so the colour changes
        # only where the commanded direction changes.
        ax = axes[1][col]
        style(ax)
        run_t, run_p, run_heat = [t[0]], [rows[0]["pwm"]], rows[0]["heat"]
        for ti, r in zip(t[1:], rows[1:]):
            if r["heat"] != run_heat:
                ax.plot(run_t, run_p, color=HEAT if run_heat else COOL,
                        linewidth=1.4)
                run_t, run_p, run_heat = [ti], [r["pwm"]], r["heat"]
            else:
                run_t.append(ti)
                run_p.append(r["pwm"])
        ax.plot(run_t, run_p, color=HEAT if run_heat else COOL, linewidth=1.4)
        # Autoscale rather than showing the full 0-255 range, which would
        # flatten commands of a few counts onto the axis line. The note under
        # the figure carries the saturation information instead.
        ax.set_ylim(0, max(peak * 1.55, 5))
        ax.set_ylabel("PWM  (counts)", color="#404040")
        ax.set_xlabel("Time since this gain was applied  (s)", color="#404040")
        ax.text(0.03, 0.90, f"Peak {peak:.0f} of 255 counts",
                transform=ax.transAxes, fontsize=9.5, color=HEAT, va="top")

        summary.append((kp, L, peak))
        print(f"  Kp = {kp:<6g} L = {L:5.2f}  {len(rows):5d} samples, "
              f"{t[-1]:6.0f} s   settled {settled:6.2f} C   "
              f"droop {droop:5.2f} C   predicted {predicted:5.2f} C")

    fig.suptitle("P-only control: temperature and command traces",
                 fontsize=13.5, color="#404040", y=0.975)
    fig.text(0.008, 0.012,
             "Setpoint 30.0 \u00b0C, T_amb = 21.54 \u00b0C. Source: "
             "data/module_05/session_2026-09-30_full_log.csv. Time is re-zeroed "
             "where each gain was applied.\nSettled value is the mean of the final "
             "60 s shown. Kp = 32 is shown for its first 210 s only: after about "
             "216 s the plate stops following the command.\nNeither panel "
             "saturates. PWM is red while heating, blue while cooling. The model "
             "droop uses the Module 4 susceptibility and is not fitted.",
             fontsize=7.8, color="#595959", va="bottom")
    fig.subplots_adjust(left=0.068, right=0.985, top=0.865, bottom=0.185)
    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=200, facecolor="white")
    print(f"\nFigure written to {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
