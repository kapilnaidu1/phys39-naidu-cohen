#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I. Actuator checks for an Angstrom live run.
Naidu / Cohen

    python3 python/analysis/angstrom_actuator.py data/module_08/angstrom_live_....csv [--tamb 22.53]

Two figures, both from the raw run file:

1. The open-loop feedforward. The Module 4 steady-state curve
   (data/module_04/steady_state.csv: signed PWM against steady T - T0) is the
   calibration T_ss = f(u). The sketch inverts it by piecewise-linear
   interpolation, u_ff = f^-1(T_set - T_room), and extends the end segments
   past the measured range. The figure shows the measured points, the
   interpolation (dashed where it is extrapolated) and every feedforward
   command the run actually sent in OL mode.

2. Raw controller command against applied signed PWM, for P and PI.
   Expected: slope 1 for u >= 0 (heating), slope r = chi_h/chi_c for u < 0
   (cooling multiplier), and flat at +-255 if the clamp is reached. The
   script fits both slopes from the data.

OUTPUT
  docs/figures/module_08/angstrom_feedforward_<run>.png
  docs/figures/module_08/angstrom_actuator_<run>.png
  data/module_08/angstrom_actuator_<run>.txt
"""

import argparse
import csv
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CURVE = os.path.join(REPO, "data", "module_04", "steady_state.csv")
FIG_DIR = os.path.join(REPO, "docs", "figures", "module_08")
DATA_DIR = os.path.join(REPO, "data", "module_08")
T0_MODULE4 = 21.54        # PWM 0 baseline in steady_state.csv


def module4_curve():
    u, dT = [], []
    with open(CURVE, newline="") as fh:
        for r in csv.DictReader(fh):
            pwm = float(r["pwm"])
            if r["direction"] == "cool":
                if pwm == 0:
                    continue          # same baseline row as heat 0
                pwm = -pwm
            u.append(pwm)
            dT.append(float(r["steady_c"]) - T0_MODULE4)
    order = np.argsort(u)
    return np.array(u)[order], np.array(dT)[order]


def load(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    out = {}
    for k in rows[0]:
        if k == "control_mode":
            out[k] = np.array([r[k] for r in rows])
        else:
            out[k] = np.array([float(r[k]) for r in rows])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--tamb", type=float, default=22.53,
                    help="room temperature sent to the Arduino for OL (C)")
    a = ap.parse_args()
    stem = os.path.splitext(os.path.basename(a.run))[0]
    cols = load(a.run)
    run = cols["run_state"] == 1
    lines = [f"Run {a.run}", f"Module 4 curve: {os.path.relpath(CURVE, REPO)} "
             f"(T0 = {T0_MODULE4} C); room temperature for OL: {a.tamb} C", ""]

    # ---- 1. feedforward -------------------------------------------------
    u, dT = module4_curve()
    ol = run & (cols["control_mode"] == "OL")
    sp = cols["setpoint_C"][ol]
    uff = cols["feedforward_pwm"][ol]
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.plot(dT, u, "o", color="#1F4E79", label="Module 4 steady states (measured)")
    inside = np.linspace(dT.min(), dT.max(), 200)
    ax.plot(inside, np.interp(inside, dT, u), color="#1F4E79", lw=1.2,
            label="inverse f⁻¹, piecewise linear")
    hi = np.linspace(dT.max(), max(dT.max(), (sp - a.tamb).max()) + 0.5, 20)
    slope = (u[-1] - u[-2]) / (dT[-1] - dT[-2])
    ax.plot(hi, u[-1] + slope * (hi - dT[-1]), color="#1F4E79", ls="--", lw=1.2,
            label="extrapolated (end segment)")
    ax.plot(sp - a.tamb, uff, ".", ms=2, color="#C0392B",
            label="u_ff sent in the OL run")
    ax.set_xlabel("requested T − T_room (°C)")
    ax.set_ylabel("PWM (+ heat, − cool)")
    ax.set_title("Open-loop feedforward: inverse of the steady-state curve", fontsize=10)
    ax.grid(True, color="#E4E4E4")
    ax.legend(fontsize=8)
    fig.tight_layout()
    f1 = os.path.join(FIG_DIR, f"angstrom_feedforward_{stem}.png")
    fig.savefig(f1, dpi=170)
    plt.close(fig)
    need = sp - a.tamb
    beyond = need > dT.max()
    lines.append(f"OL: {ol.sum()} records, requested T - T_room {need.min():.2f} to "
                 f"{need.max():.2f} C, u_ff {uff.min():.1f} to {uff.max():.1f}.")
    lines.append(f"Measured curve reaches +{dT.max():.2f} C (PWM {u[-1]:.0f}); "
                 f"{100 * beyond.mean():.0f} % of the OL records needed more and used the "
                 f"extrapolated end segment ({slope:.2f} PWM per C).")
    lines.append("")

    # ---- 2. controller command against applied PWM -------------------------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    for ax, mode in zip(axes, ("P", "PI")):
        m = run & (cols["control_mode"] == mode)
        uc = cols["controller_pwm"][m]
        ua = cols["signed_pwm"][m]
        r = cols["heating_to_cooling_ratio"][m]
        ax.plot(uc, ua, ".", ms=2, color="#202020")
        pos, neg = uc >= 0, uc < 0
        txt = []
        for sel, name in ((pos, "heating"), (neg, "cooling")):
            ok = sel & (np.abs(ua) < 255)
            if ok.sum() > 5:
                k = np.polyfit(uc[ok], ua[ok], 1)[0]
                txt.append(f"{name} slope {k:.3f}")
        sat = np.sum(np.abs(ua) >= 255)
        lines.append(f"{mode}: {m.sum()} records, controller {uc.min():.1f} to "
                     f"{uc.max():.1f}, applied {ua.min():.0f} to {ua.max():.0f}, "
                     f"r = {np.unique(r)}, {', '.join(txt)}, "
                     f"records at the +-255 clamp: {sat}")
        ax.axhline(255, color="#C0392B", lw=0.8, ls=":")
        ax.axhline(-255, color="#C0392B", lw=0.8, ls=":")
        ax.axhline(0, color="#999999", lw=0.6)
        ax.axvline(0, color="#999999", lw=0.6)
        ax.set_title(f"{mode}: " + "; ".join(txt), fontsize=9)
        ax.set_xlabel("raw controller command (PWM counts)")
        ax.grid(True, color="#E4E4E4")
    axes[0].set_ylabel("applied signed PWM")
    fig.suptitle("Cooling multiplier r applied before the clamp", fontsize=10)
    fig.tight_layout()
    f2 = os.path.join(FIG_DIR, f"angstrom_actuator_{stem}.png")
    fig.savefig(f2, dpi=170)
    plt.close(fig)

    text = "\n".join(lines)
    print(text)
    with open(os.path.join(DATA_DIR, f"angstrom_actuator_{stem}.txt"), "w") as fh:
        fh.write(f"python3 python/analysis/angstrom_actuator.py {a.run} --tamb {a.tamb:g}\n\n"
                 + text + "\n")
    print(f"Wrote {os.path.relpath(f1, REPO)}, {os.path.relpath(f2, REPO)}")


if __name__ == "__main__":
    main()
