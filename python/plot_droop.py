#!/usr/bin/env python3
"""
Phys 39 Module 5, Parts 3 and 4. Naidu / Cohen

Measured droop against the 1/(1+L) prediction, on one graph as the
assignment requires.

    python3 python/plot_droop.py        (run from the repository root)

INPUT   data/module_05/droop.csv
OUTPUT  docs/figures/module_05/droop_vs_gain.png
        a table of measured vs predicted droop, printed

INPUT FORMAT

    kp,setpoint_c,final_t_c,final_pwm,notes
    0.25,30.0,22.51,2,
    0.50,30.0,23.30,3,

    kp          proportional gain, PWM counts per degree C
    setpoint_c  the setpoint for that run
    final_t_c   settled temperature
    final_pwm   settled PWM magnitude, used for the P = Kp*droop check
    notes       free text, optional

The prediction needs no fitting. chi and T_amb both come from Module 4, so
the predicted curve is drawn before any Module 5 data exists and the
measurement either lands on it or does not.
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INPUT_CSV = "data/module_05/droop.csv"
OUTPUT_PNG = "docs/figures/module_05/droop_vs_gain.png"

# From Module 4. Not fitted here.
CHI_H = 0.50127        # C per PWM count, heating branch
T_AMB = 21.54          # C, measured zero-PWM temperature

MEAS_COLOR = "#d62728"
PRED_COLOR = "#1f4e79"


def read_rows(path):
    if not os.path.exists(path):
        sys.exit(
            f"{path} not found.\n"
            "Create it with the header:\n"
            "    kp,setpoint_c,final_t_c,final_pwm,notes\n"
            "one row per gain, and run this from the repository root."
        )
    rows = []
    with open(path, newline="") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            try:
                kp = float(r["kp"])
                sp = float(r["setpoint_c"])
                tf = float(r["final_t_c"])
            except (KeyError, ValueError, TypeError):
                print(f"  line {n}: skipped, kp/setpoint_c/final_t_c not numeric")
                continue
            try:
                pwm = float(r.get("final_pwm") or "nan")
            except ValueError:
                pwm = float("nan")
            rows.append((kp, sp, tf, pwm, (r.get("notes") or "").strip()))
    return sorted(rows)


def main():
    rows = read_rows(INPUT_CSV)
    if not rows:
        sys.exit(f"No usable rows in {INPUT_CSV}.")

    print(f"{'Kp':>6} {'L':>7} {'e0':>7} {'droop meas':>11} "
          f"{'droop pred':>11} {'ratio':>7} {'PWM meas':>9} {'Kp*droop':>9}")
    print("-" * 74)

    kps, meas, pred = [], [], []
    for kp, sp, tf, pwm, note in rows:
        e0 = sp - T_AMB
        L = kp * CHI_H
        d_meas = sp - tf
        d_pred = e0 / (1.0 + L)
        ratio = d_meas / d_pred if d_pred else float("nan")
        kps.append(kp)
        meas.append(d_meas)
        pred.append(d_pred)
        print(f"{kp:6.2f} {L:7.3f} {e0:7.2f} {d_meas:11.2f} {d_pred:11.2f} "
              f"{ratio:7.3f} {pwm:9.1f} {kp * d_meas:9.1f}")

    print()
    print("  The last two columns are a consistency check independent of the")
    print("  droop model: at steady state the commanded PWM should equal")
    print("  Kp * droop. If those disagree, the loop is not actually settled,")
    print("  or the command is being clamped.")

    # ---- figure ----
    #
    # Styled to read like a spreadsheet chart: white plot area, light grey
    # gridlines on both axes, no top or right border, outward ticks,
    # dark-edged markers, and the fit equation plus R-squared printed on the
    # chart the way Excel's "Display Equation" option writes them.
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.edgecolor": "#868686", "axes.linewidth": 0.8,
        "xtick.direction": "out", "ytick.direction": "out",
        "xtick.color": "#595959", "ytick.color": "#595959",
    })
    fig, ax = plt.subplots(figsize=(8.4, 5.6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.grid(True, which="major", color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    lo, hi = min(kps), max(kps)
    span = [lo + (hi - lo) * i / 400.0 for i in range(401)]
    sp0 = rows[0][1]
    e0 = sp0 - T_AMB

    ax.plot(span, [e0 / (1.0 + k * CHI_H) for k in span], "-",
            color=PRED_COLOR, linewidth=1.8, zorder=2,
            label="Model,  $T_{set}-T_{ss}=e_0/(1+K_p\\chi)$")
    ax.plot(kps, meas, "o", color=MEAS_COLOR, markersize=9,
            markeredgecolor="#404040", markeredgewidth=0.7, linestyle="none",
            zorder=4, label="Measured droop")
    ax.plot(kps, pred, "^", color=PRED_COLOR, markersize=7,
            markerfacecolor="none", markeredgewidth=1.2, linestyle="none",
            zorder=3, label="Model at the tested gains")

    # Agreement quoted on the chart, the way a trendline R^2 would be.
    ratios = [m / p for m, p in zip(meas, pred)]
    mean_r = sum(ratios) / len(ratios)
    sd_r = (sum((r - mean_r) ** 2 for r in ratios) / len(ratios)) ** 0.5
    worst = max(abs(r - 1.0) for r in ratios) * 100.0
    ss_res = sum((m - p) ** 2 for m, p in zip(meas, pred))
    mbar = sum(meas) / len(meas)
    ss_tot = sum((m - mbar) ** 2 for m in meas)
    r2 = 1.0 - ss_res / ss_tot if ss_tot else float("nan")

    ax.text(0.975, 0.985,
            f"$\\chi_{{T,h}}$ = {CHI_H:.4f} \u00b0C/count  (Module 4, "
            f"not fitted here)\n"
            f"R\u00b2 = {r2:.4f}\n"
            f"mean measured/model = {mean_r:.3f} \u00b1 {sd_r:.3f},  "
            f"worst {worst:.1f}%",
            transform=ax.transAxes, ha="right", va="top", fontsize=9,
            color=PRED_COLOR,
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#F4F8FC",
                      edgecolor="#C9DCEC", linewidth=0.8))

    # Mark L = 1, where exactly half the initial error survives. It is the
    # single most quotable point on the curve, so name it.
    kp_L1 = 1.0 / CHI_H
    if lo <= kp_L1 <= hi:
        ax.plot([kp_L1], [e0 / 2.0], "*", color="#7030A0", markersize=15,
                zorder=5, label=f"$L=1$ at $K_p$={kp_L1:.2f}: half of $e_0$")

    ax.axhline(e0, color="#999999", linewidth=1.0, linestyle=":", zorder=1)
    ax.text(lo, e0, f"  no feedback: $e_0$ = {e0:.2f} \u00b0C",
            fontsize=8.5, color="#777777", va="bottom", ha="left")

    ax.set_xlabel("Proportional gain  $K_p$   (PWM counts per \u00b0C)",
                  color="#404040")
    ax.set_ylabel("Steady-state droop  $T_{set}-T_{ss}$   (\u00b0C)",
                  color="#404040")
    ax.set_title("P-Only Control: Steady-State Droop vs Gain",
                 fontsize=13.5, color="#404040", pad=26)
    ax.set_ylim(0, e0 * 1.30)

    top = ax.secondary_xaxis("top", functions=(lambda k: k * CHI_H,
                                               lambda l: l / CHI_H))
    top.set_xlabel("Dimensionless loop gain   $L=K_p\\chi_{T,u}$",
                   color="#404040", labelpad=7)
    top.tick_params(colors="#595959")

    leg = ax.legend(loc="center right", frameon=True, fontsize=9)
    leg.get_frame().set_edgecolor("#BFBFBF")
    leg.get_frame().set_linewidth(0.8)

    fig.text(0.012, 0.015,
             f"Setpoint {sp0:.1f} \u00b0C,  T_amb = {T_AMB:.2f} \u00b0C,  "
             f"e\u2080 = {e0:.2f} \u00b0C.  Each point is the mean of the "
             f"final 60 s of a settled run (net drift \u2264 0.16 \u00b0C, "
             f"the measured noise floor).\nThe curve is not a fit: it uses "
             f"the open-loop susceptibility measured in Module 4 and has no "
             f"free parameters.",
             fontsize=7.6, color="#595959", va="bottom")
    fig.tight_layout(rect=(0, 0.085, 1, 1))

    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=200, facecolor="white")
    print(f"\nFigure written to {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
