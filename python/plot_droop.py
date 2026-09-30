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
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.edgecolor": "#868686", "axes.linewidth": 0.8})
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.grid(True, color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    # Smooth prediction curve across the tested range, so the comparison is
    # against a model rather than against six isolated predicted points.
    lo, hi = min(kps), max(kps)
    span = [lo + (hi - lo) * i / 300.0 for i in range(301)]
    sp0 = rows[0][1]
    e0 = sp0 - T_AMB
    ax.plot(span, [e0 / (1.0 + k * CHI_H) for k in span], "-",
            color=PRED_COLOR, linewidth=1.6,
            label=f"Predicted, $e_0/(1+K_p\\chi)$, $\\chi$={CHI_H:.4f}")
    ax.plot(kps, pred, "^", color=PRED_COLOR, markersize=6,
            markerfacecolor="none", label="Predicted at tested gains")
    ax.plot(kps, meas, "o", color=MEAS_COLOR, markersize=7,
            markeredgecolor="#404040", markeredgewidth=0.6,
            label="Measured droop")

    ax.set_xlabel("Proportional gain $K_p$  (PWM counts per °C)")
    ax.set_ylabel("Steady-state droop  $T_{set}-T_{ss}$  (°C)")
    ax.set_title("P-only control: droop falls as 1/(1+L)")
    ax.legend(fontsize=8.5)

    # Second axis in L, since L is what the physics depends on.
    top = ax.secondary_xaxis("top", functions=(lambda k: k * CHI_H,
                                               lambda l: l / CHI_H))
    top.set_xlabel("Dimensionless loop gain  $L=K_p\\chi_{T,u}$")

    ax.axhline(e0, color="#999999", linewidth=0.9, linestyle=":")
    ax.text(hi, e0, f" $e_0$ = {e0:.2f} °C, no feedback",
            fontsize=7.5, color="#777777", va="bottom", ha="right")

    fig.text(0.01, 0.015,
             f"Setpoint {sp0:.1f} °C, T_amb = {T_AMB:.2f} °C, "
             f"e0 = {e0:.2f} °C. Prediction uses the Module 4 heating "
             f"susceptibility and is not fitted to these data.",
             fontsize=7.4, color="#595959", va="bottom")
    fig.tight_layout(rect=(0, 0.06, 1, 1))

    os.makedirs(os.path.dirname(OUTPUT_PNG), exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=200, facecolor="white")
    print(f"\nFigure written to {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
