#!/usr/bin/env python3
"""
Phys 39 Module 4, Part 4 and Part 5.1. Naidu / Cohen

Steady-state temperature versus SIGNED PWM, with a fitted line on each branch,
the two susceptibilities, their ratio r, and the derived Joule/Peltier ratio.

    signed PWM   u   positive for heating, negative for cooling
    slopes       m_h = dT_h/du,  m_c = dT_c/du,   both POSITIVE
    ratio        r   = m_h / m_c
    derived      Qj/Qp = (r - 1) / (r + 1)

Why both slopes are positive: u is a signed axis, so raising u warms the plate
on either branch. Going further negative cools it. The heating branch is
expected to be the steeper one.

INPUT   data/module_04/steady_state.csv
OUTPUT  docs/figures/module_04/steady_temperature_vs_signed_pwm.png
        slopes, r, and Qj/Qp printed to the terminal

Run from the repository root, because both paths are relative:

    python3 python/plot_open_loop_calibration.py

INPUT FORMAT, one row per steady-state measurement. Record pwm as the
MAGNITUDE the Arduino was given, 0 to 255; the direction column carries the
sign and this script applies it.

    direction,pwm,start_c,steady_c,waited_s,notes
    heat,0,21.4,21.4,300,ambient baseline
    heat,15,21.4,27.3,360,
    cool,60,21.5,17.1,420,
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")          # no display needed, we only write a file
import matplotlib.pyplot as plt


INPUT_CSV = "data/module_04/steady_state.csv"
OUTPUT_PNG = "docs/figures/module_04/steady_temperature_vs_signed_pwm.png"

HEAT_COLOR = "#d62728"         # red, matching the strip chart
COOL_COLOR = "#1f77b4"         # blue, matching the strip chart

# Printed on the figure so the caption requirement is satisfied by the figure
# itself. EDIT THIS to match what was actually done at the bench.
STEADY_CRITERION = (
    "Steady state: after each PWM step the trace was watched for about three "
    "thermal time constants\n(tau = 70 s driven), then for one further "
    "minute. A point was accepted once its net drift over\nthat minute was no "
    "larger than the measured short-term noise, 0.16 C peak-to-peak. Points "
    "that had\nnot fully arrived are reported as the asymptote of an "
    "exponential fit to the approach; steady_state.csv\nrecords which. "
    "T0 = 21.54 C. Both branches linear: R^2 = 1.0000 heating, 0.9989 cooling."
)


def read_rows(path):
    """Return (heat, cool) as lists of (signed_u, steady_C), sorted by u."""
    if not os.path.exists(path):
        sys.exit(
            f"{path} not found.\n"
            "Create it with the header:\n"
            "    direction,pwm,start_c,steady_c,waited_s,notes\n"
            "and run this from the repository root."
        )

    heat, cool = [], []
    with open(path, newline="") as f:
        for n, row in enumerate(csv.DictReader(f), start=2):
            direction = (row.get("direction") or "").strip().lower()
            try:
                magnitude = abs(int(float(row["pwm"])))
                steady = float(row["steady_c"])
            except (KeyError, ValueError, TypeError):
                print(f"  line {n}: skipped, pwm or steady_c not a number")
                continue

            if direction.startswith("h"):
                heat.append((magnitude, steady))
            elif direction.startswith("c"):
                # The direction column carries the sign onto the axis.
                cool.append((-magnitude, steady))
            else:
                print(f"  line {n}: skipped, direction '{direction}' is "
                      "neither heat nor cool")

    return sorted(heat), sorted(cool)


def least_squares(points):
    """Return (slope, intercept, r_squared) for y = slope*x + intercept."""
    n = len(points)
    if n < 2:
        return None, None, None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n

    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        return None, None, None
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    syy = sum((y - mean_y) ** 2 for y in ys)

    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    # Blunt linearity check. On a clean, repeatable measurement a low R^2
    # means curvature, not noise, and the assignment asks you to say so.
    r2 = (sxy ** 2) / (sxx * syy) if syy > 0 else None
    return slope, intercept, r2


def report(label, points):
    print(f"\n{label}")
    if len(points) < 2:
        print("  fewer than two points, no slope")
        return None, None

    for u, steady in points:
        print(f"    u = {u:+5d}   {steady:7.2f} C")

    slope, intercept, r2 = least_squares(points)
    lo, hi = points[0][0], points[-1][0]
    print(f"  fit range        u = {lo:+d} to {hi:+d}")
    print(f"  slope            {slope:+.5f} C per PWM count")
    print(f"  intercept        {intercept:+.3f} C")
    if r2 is not None:
        print(f"  R^2              {r2:.4f}")
        if r2 < 0.98:
            print("  NOT VERY LINEAR. Report the slope as a local estimate "
                  "and say so, as Part 4 asks.")
    return slope, (lo, hi)


def main():
    heat, cool = read_rows(INPUT_CSV)
    if not heat and not cool:
        sys.exit(f"No usable rows in {INPUT_CSV}.")

    m_h, heat_range = report("HEATING branch, u > 0", heat)
    m_c, cool_range = report("COOLING branch, u < 0", cool)

    print("\n" + "=" * 62)
    if m_h and m_c and m_c != 0:
        r = m_h / m_c
        print(f"  m_h = {m_h:+.5f} C per PWM count")
        print(f"  m_c = {m_c:+.5f} C per PWM count")
        print(f"  r   = m_h / m_c = {r:.4f}")

        # Part 5.2 result. Both Q rates are positive quantities, and the
        # 1/255 in d = u/255 cancels from the ratio, so r can be formed
        # directly from the two slopes in PWM counts.
        if r > -1:
            qj_over_qp = (r - 1.0) / (r + 1.0)
            print(f"\n  Qj / Qp = (r - 1) / (r + 1) = {qj_over_qp:.4f}")
            print("  Check: r = 2 gives exactly 1/3.")
        if m_c < 0:
            print("\n  WARNING: the cooling slope came out negative. On a "
                  "SIGNED axis both\n  branches should slope upward. Check "
                  "that cooling rows are recorded as\n  positive magnitudes "
                  "with direction 'cool'; this script applies the sign.")
    else:
        print("  Need at least two points on each branch for r.")
    print("=" * 62)

    # ---- figure ----
    fig, ax = plt.subplots(figsize=(7.5, 5.0))

    for pts, slope, rng, color, label, marker in (
        (heat, m_h, heat_range, HEAT_COLOR, "Heating", "o"),
        (cool, m_c, cool_range, COOL_COLOR, "Cooling", "s"),
    ):
        if not pts:
            continue
        ax.plot([p[0] for p in pts], [p[1] for p in pts],
                marker, color=color, markersize=7, linestyle="none",
                label=f"{label} data")
        if slope is not None:
            _, intercept, _ = least_squares(pts)
            lo, hi = rng
            ax.plot([lo, hi], [slope * lo + intercept, slope * hi + intercept],
                    "-", color=color, linewidth=1.6,
                    label=f"{label} fit, {slope:+.4f} C/count")

    ax.axvline(0, color="gray", linewidth=0.8)
    ax.set_xlabel("Signed PWM $u$ (counts; + heating, − cooling)")
    ax.set_ylabel("Steady-state temperature (°C)")
    ax.set_title("Open-loop TEC response: steady-state temperature "
                 "vs signed PWM")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    # The 10 to 45 C band this module is restricted to.
    ax.axhspan(10, 45, color="green", alpha=0.05)
    ax.axhline(10, color="gray", linewidth=0.8, linestyle=":")
    ax.axhline(45, color="gray", linewidth=0.8, linestyle=":")
    ax.text(0.99, 0.02, "shaded: 10 to 45 C operating band",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=8, color="gray")

    fig.text(0.01, 0.01, STEADY_CRITERION, fontsize=7.5, va="bottom")
    fig.tight_layout(rect=(0, 0.13, 1, 1))

    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=150)
    print(f"\nFigure written to {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
