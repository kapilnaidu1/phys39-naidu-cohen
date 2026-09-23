#!/usr/bin/env python3
"""
Phys 39 Module 4, Part 4. Steady-state temperature versus PWM magnitude.
Naidu / Cohen

Reads the steady-state table, plots heating in red and cooling in blue to
match the strip chart's colour convention, and estimates dT/dPWM for each
direction.

INPUT   data/module_04/steady_state.csv
OUTPUT  docs/figures/module_04/steady_temperature_vs_pwm.png
        dT/dPWM printed to the terminal for both directions

Run from the repository root, because both paths are relative:

    python3 python/plot_open_loop_calibration.py

INPUT FORMAT, one row per steady-state measurement:

    direction,pwm,start_c,steady_c,waited_s,notes
    heat,0,21.4,21.4,180,ambient baseline
    heat,32,21.4,26.8,240,
    cool,48,21.5,15.2,300,

    direction   "heat" or "cool", case-insensitive
    pwm         integer magnitude, 0 to 255
    steady_c    the number that gets plotted
    start_c     kept for the record, not plotted
    waited_s    kept for the record, not plotted
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")          # no display needed, we only write a file
import matplotlib.pyplot as plt


INPUT_CSV = "data/module_04/steady_state.csv"
OUTPUT_PNG = "docs/figures/module_04/steady_temperature_vs_pwm.png"

HEAT_COLOR = "#d62728"         # red, matching the strip chart
COOL_COLOR = "#1f77b4"         # blue, matching the strip chart

# Stated on the figure so the caption requirement is met by the figure
# itself, not only by the surrounding prose. Edit to match what was
# actually used at the bench.
STEADY_CRITERION = ("Steady state: temperature changing by less than 0.1 C "
                    "over 30 s,\nwith a minimum wait of 180 s at every "
                    "setting.")


def read_rows(path):
    if not os.path.exists(path):
        sys.exit(
            f"{path} not found.\n"
            "Create it from the steady-state table in the module note, with "
            "the header:\n"
            "    direction,pwm,start_c,steady_c,waited_s,notes\n"
            "Run this from the repository root, since the path is relative."
        )

    heat, cool = [], []
    with open(path, newline="") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            direction = (row.get("direction") or "").strip().lower()
            try:
                pwm = int(float(row["pwm"]))
                steady = float(row["steady_c"])
            except (KeyError, ValueError, TypeError):
                print(f"  line {n}: skipped, pwm or steady_c not a number")
                continue

            if direction.startswith("h"):
                heat.append((pwm, steady))
            elif direction.startswith("c"):
                cool.append((pwm, steady))
            else:
                print(f"  line {n}: skipped, direction '{direction}' "
                      "is neither heat nor cool")

    return sorted(heat), sorted(cool)


def susceptibility(points):
    """Estimate dT/dPWM in C per PWM count.

    Two figures are returned because they answer different questions.

    The ENDPOINT slope is what the assignment's formula asks for: the total
    change in steady temperature divided by the total change in PWM. It is
    the right summary number when the relationship is close to linear.

    The LEAST-SQUARES slope uses every point rather than just the two ends.
    When the data is curved the two disagree, and that disagreement is
    itself the evidence for saying so. A least-squares fit through curved
    data is not more correct than the endpoint slope, it just fails
    differently, so both are reported rather than one being chosen.
    """
    if len(points) < 2:
        return None, None, None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    endpoint = (ys[-1] - ys[0]) / (xs[-1] - xs[0]) if xs[-1] != xs[0] else None

    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        return endpoint, None, None
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    fit = sxy / sxx

    # Coefficient of determination, as a blunt linearity check. Low R^2 on a
    # clean, repeatable measurement means curvature, not noise.
    syy = sum((y - mean_y) ** 2 for y in ys)
    r2 = (sxy ** 2) / (sxx * syy) if syy > 0 else None

    return endpoint, fit, r2


def report(label, points):
    print(f"\n{label}")
    if len(points) < 2:
        print("  fewer than two points, no slope")
        return None

    for pwm, steady in points:
        print(f"    PWM {pwm:3d}   {steady:7.2f} C")

    endpoint, fit, r2 = susceptibility(points)
    print(f"  dT/dPWM, endpoints      {endpoint:+.4f} C per PWM count")
    if fit is not None:
        print(f"  dT/dPWM, least squares  {fit:+.4f} C per PWM count")
    if r2 is not None:
        print(f"  R^2                     {r2:.4f}")
        if r2 < 0.98:
            print("  NOT VERY LINEAR. Report the slope as a local estimate "
                  "and say so.")
    return endpoint


def main():
    heat, cool = read_rows(INPUT_CSV)

    if not heat and not cool:
        sys.exit(f"No usable rows in {INPUT_CSV}.")

    heat_slope = report("HEATING", heat)
    cool_slope = report("COOLING", cool)

    if heat_slope and cool_slope and cool_slope != 0:
        ratio = abs(heat_slope / cool_slope)
        print(f"\nAsymmetry: heating slope is {ratio:.2f}x the cooling slope "
              "in magnitude.")
        print("Part 5 explains this from the apparatus, not the code.")

    fig, ax = plt.subplots(figsize=(7.5, 5.0))

    if heat:
        ax.plot([p[0] for p in heat], [p[1] for p in heat],
                "o-", color=HEAT_COLOR, label="Heating", markersize=7)
    if cool:
        ax.plot([p[0] for p in cool], [p[1] for p in cool],
                "s-", color=COOL_COLOR, label="Cooling", markersize=7)

    ax.set_xlabel("PWM magnitude (counts, 0 to 255)")
    ax.set_ylabel("Steady-state temperature (°C)")
    ax.set_title("Open-loop TEC response: steady-state temperature vs PWM")
    ax.grid(True, alpha=0.3)
    ax.legend()

    # The 10 to 45 C operating band this module is restricted to.
    ax.axhspan(10, 45, color="green", alpha=0.05)
    ax.axhline(10, color="gray", linewidth=0.8, linestyle=":")
    ax.axhline(45, color="gray", linewidth=0.8, linestyle=":")
    ax.text(0.99, 0.02, "shaded: 10 to 45 C operating band",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color="gray")

    fig.text(0.01, 0.01, STEADY_CRITERION, fontsize=8, va="bottom")
    fig.tight_layout(rect=(0, 0.08, 1, 1))

    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=150)
    print(f"\nFigure written to {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
