#!/usr/bin/env python3
"""
Phys 39 Module 5, Parts 3 and 4. Naidu / Cohen

Measured droop against the 1/(1+L) prediction, on one graph as the
assignment requires.

    python3 python/plot_droop.py        (run from the repository root)

INPUT   data/module_05/droop.csv, every value recomputed from
        data/module_05/session_2026-09-30_full_log.csv
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
    print("  The last two columns should agree to within rounding. That is not")
    print("  evidence about the apparatus: the controller computes")
    print("  p = round(abs(kp * e)), so PWM = Kp * droop holds at every instant,")
    print("  settled or not. It only confirms the command and the log agree.")

    # ---- figure ----
    #
    # Same conventions as docs/figures/module_04: white plot area, light grey
    # gridlines, no top or right spine, dark-edged markers, a dashed fit
    # line, the equation and R-squared as plain coloured text at the top
    # left, and a plain two-entry legend. Nothing boxed, starred or
    # otherwise decorated.
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.edgecolor": "#868686", "axes.linewidth": 0.8,
        "xtick.direction": "out", "ytick.direction": "out",
        "xtick.color": "#595959", "ytick.color": "#595959",
    })
    fig, ax = plt.subplots(figsize=(8.0, 5.2))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.grid(True, which="major", color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    sp0 = rows[0][1]
    e0 = sp0 - T_AMB
    lo, hi = min(kps), max(kps)
    span = [lo + (hi - lo) * i / 400.0 for i in range(401)]

    ax.plot(span, [e0 / (1.0 + k * CHI_H) for k in span], "--",
            color=PRED_COLOR, linewidth=1.5, zorder=2, label="Model")
    ax.plot(kps, meas, "o", color=MEAS_COLOR, markersize=8,
            markeredgecolor="#404040", markeredgewidth=0.7, linestyle="none",
            zorder=3, label="Measured droop")

    ratios = [m / p for m, p in zip(meas, pred)]
    mean_r = sum(ratios) / len(ratios)
    # Sample standard deviation (n - 1): the spread is being estimated from a
    # handful of points, so the population form would understate it.
    sd_r = (sum((r - mean_r) ** 2 for r in ratios) / (len(ratios) - 1)) ** 0.5
    rms_res = (sum((m - p) ** 2 for m, p in zip(meas, pred)) / len(meas)) ** 0.5
    ss_res = sum((m - p) ** 2 for m, p in zip(meas, pred))
    mbar = sum(meas) / len(meas)
    ss_tot = sum((m - mbar) ** 2 for m in meas)
    r2 = 1.0 - ss_res / ss_tot if ss_tot else float("nan")

    ax.text(0.03, 0.96,
            f"Model:  y = {e0:.2f} / (1 + {CHI_H:.4f}x)",
            transform=ax.transAxes, fontsize=9.5, color=PRED_COLOR, va="top")
    ax.text(0.03, 0.905,
            f"R\u00b2 = {r2:.4f},  rms residual {rms_res:.3f} \u00b0C",
            transform=ax.transAxes, fontsize=9.5, color=PRED_COLOR, va="top")
    ax.text(0.03, 0.85,
            f"measured / model = {mean_r:.3f} \u00b1 {sd_r:.3f}",
            transform=ax.transAxes, fontsize=9.5, color=MEAS_COLOR, va="top")

    ax.set_xlabel("Proportional gain $K_p$  (PWM counts per \u00b0C)")
    ax.set_ylabel("Steady-state droop  $T_{set}-T_{ss}$  (\u00b0C)")
    ax.set_title("P-only control: steady-state droop vs gain",
                 fontsize=13, color="#404040", pad=24)
    ax.set_ylim(0, e0 * 1.18)

    top = ax.secondary_xaxis("top", functions=(lambda k: k * CHI_H,
                                               lambda l: l / CHI_H))
    top.set_xlabel("Loop gain  $L = K_p\\chi$", color="#404040", labelpad=6)
    top.tick_params(colors="#595959")

    leg = ax.legend(loc="upper right", frameon=True, fontsize=9)
    leg.get_frame().set_edgecolor("#BFBFBF")
    leg.get_frame().set_linewidth(0.8)

    fig.text(0.01, 0.015,
             f"Setpoint {sp0:.1f} \u00b0C, T_amb = {T_AMB:.2f} \u00b0C, "
             f"e0 = {e0:.2f} \u00b0C. Each point is the mean of the final 60 s "
             f"of its run (for Kp = 32, of its first 210 s).\nSource: "
             f"data/module_05/session_2026-09-30_full_log.csv. The model uses the "
             f"Module 4 susceptibility and is not fitted to these data.",
             fontsize=7.6, color="#595959", va="bottom")
    fig.tight_layout(rect=(0, 0.09, 1, 1))

    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=200, facecolor="white")
    print(f"\nFigure written to {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
