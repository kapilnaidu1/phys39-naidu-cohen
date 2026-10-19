#!/usr/bin/env python3
"""
Phys 39 Module 6, oral review and the foam-removal experiment. Naidu / Cohen

    python3 python/insulation_sensitivity.py      (run from the repository root)

1. Steady operating points. Every settled hold of the 13 October runs (P and
   PI, any gain) is a point (u, T) where C dT/dt = 0, so it must sit on the
   plant line T = T_amb + chi_h u whatever the controller was. A straight-line
   fit gives chi_h and T_amb from closed-loop data, to compare with the
   open-loop Module 4 values (0.501 C/count, 21.54 C).
2. Sensitivity of each observable to the loss conductance H, the one parameter
   that removing the foam box should change. S = d ln(X) / d ln(H).
3. Illustrative foam-off cases, H x 1.25 and H x 1.5. These factors are NOT
   measured; they only show the size and direction of each change.
4. A rough estimate of the TEC module's own passive conductance from the Laird
   CP14-127-045 data sheet (constant-property TEC model), to judge how much of
   H the foam can affect at all.

INPUT   data/module_06/pi_run_20261013_094149.csv
OUTPUT  data/module_06/steady_operating_points.csv
        data/module_06/insulation_sensitivity_output.txt
        docs/figures/module_06/oral_review/operating_points.png
        docs/figures/module_06/oral_review/insulation_sensitivity.png
"""

import csv
import importlib.util
import io
import math
import os
import sys
from contextlib import redirect_stdout
from dataclasses import replace

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "goldilocks_two_lump", os.path.join(HERE, "simulate_goldilocks_two_lump.py"))
two = importlib.util.module_from_spec(_spec)
sys.modules["goldilocks_two_lump"] = two
_spec.loader.exec_module(two)
sim = two.sim

RAW = "data/module_06/pi_run_20261013_094149.csv"
POINTS_CSV = "data/module_06/steady_operating_points.csv"
TXT = "data/module_06/insulation_sensitivity_output.txt"
FIG_DIR = "docs/figures/module_06/oral_review"

CHI_H, CHI_C, TAU, T_AMB = 0.501, 0.181, 62.9, 21.54   # Module 4
FACTORS = (1.0, 1.25, 1.5)                             # illustrative H multipliers
MIN_LEN_S, WINDOW_S, MAX_DRIFT, MAX_SD = 100.0, 60.0, 0.10, 0.5

# Laird CP14-127-045, SPECIFICATIONS table, hot side 27 C (Module 4 note)
R_M, I_MAX, QC_MAX, DT_MAX, TH_K = 1.50, 8.6, 71.3, 70.5, 300.15


def steady_points():
    """Last 60 s of every settled control-on hold in the 13 October file."""
    rows = list(csv.DictReader(open(RAW, newline="")))
    key = lambda r: (r["run"], r["mode"], r["kp"], r["ki"], r["setpoint_C"],
                     r["control_on"])
    segs, cur = [], None
    for i, r in enumerate(rows):
        k = key(r)
        if k != cur:
            segs.append([k, i, i])
            cur = k
        else:
            segs[-1][2] = i
    out = []
    for k, a, b in segs:
        if k[5] != "1":
            continue
        t = np.array([float(rows[j]["time_s"]) for j in range(a, b + 1)])
        T = np.array([float(rows[j]["temperature_C"]) for j in range(a, b + 1)])
        u = np.array([float(rows[j]["u_applied"]) for j in range(a, b + 1)])
        if t[-1] - t[0] < MIN_LEN_S:
            continue
        m = t >= t[-1] - WINDOW_S
        drift = np.polyfit(t[m], T[m], 1)[0] * 60.0
        if abs(drift) > MAX_DRIFT or u[m].std(ddof=1) > MAX_SD:
            continue
        out.append(dict(run=k[0], mode=k[1], kp=float(k[2]), ki=float(k[3]),
                        setpoint_C=float(k[4]), t_end_s=t[-1], hold_s=t[-1] - t[0],
                        T_C=T[m].mean(), u=u[m].mean(), u_sd=u[m].std(ddof=1),
                        drift_C_per_min=drift))
    return out


def fit_line(points):
    u = np.array([p["u"] for p in points])
    T = np.array([p["T_C"] for p in points])
    A = np.vstack([np.ones_like(u), u]).T
    coef, *_ = np.linalg.lstsq(A, T, rcond=None)
    res = T - A @ coef
    dof = len(T) - 2
    s2 = (res ** 2).sum() / dof
    cov = s2 * np.linalg.inv(A.T @ A)
    return coef[0], coef[1], math.sqrt(cov[0, 0]), math.sqrt(cov[1, 1]), res


def one_lump(f, kp=None, ki=None, t_set=35.0):
    """One-lump quantities with H scaled by f (C, P_u unchanged)."""
    chi, tau = CHI_H / f, TAU / f
    d = {"chi_h": chi, "chi_c": CHI_C / f, "tau": tau,
         "open-loop rise at u=25": chi * 25.0,
         "PI steady command at 35 C": (t_set - T_AMB) / chi}
    if kp is not None:
        L = chi * kp
        d["L"] = L
        d["droop"] = (t_set - T_AMB) / (1.0 + L)
        d["tau_cl"] = tau / (1.0 + L)
    if ki is not None:
        d["zeta_PI_1lump"] = (1.0 + chi * kp) / (2.0 * math.sqrt(tau * chi * ki))
    return d


def simulate(cfg, controller, kp, ki, t0, t_set, duration):
    cfg = replace(cfg, kp_pwm_per_c=kp, ki_pwm_per_c_s=ki, setpoint_c=t_set,
                  initial_c=t0)
    st = sim.ModelState(0.0, t0, t0, 0.0)
    t, T, u = [], [], []
    while st.time_s < duration - 1e-9:
        r = sim.advance_model(st, cfg, "two_lump", controller)
        t.append(r.time_s)
        T.append(r.measured_temperature_c)
        u.append(r.applied_pwm)
    return np.array(t), np.array(T), np.array(u)


def main():
    out = io.StringIO()
    pts = steady_points()
    T0, chi, sT0, schi, res = fit_line(pts)
    base = two.shared_config()
    H0 = base.heat_loss_w_per_c

    with redirect_stdout(out):
        print("1. Settled holds, 13 October (last 60 s; hold >= 100 s, drift "
              "<= 0.10 C/min, sd(u) <= 0.5)")
        for p in pts:
            print(f"   run {p['run']:>2} {p['mode']:<2} Kp {p['kp']:>4g} Ki "
                  f"{p['ki']:<5g} set {p['setpoint_C']:.0f}: T {p['T_C']:.3f} C, "
                  f"u {p['u']:6.2f} (sd {p['u_sd']:.2f}), drift "
                  f"{p['drift_C_per_min']:+.3f} C/min")
        print(f"   fit T = T_amb + chi_h u over {len(pts)} holds: chi_h = "
              f"{chi:.4f} +/- {schi:.4f} C/count, T_amb = {T0:.2f} +/- "
              f"{sT0:.2f} C, rms residual {np.sqrt((res**2).mean()):.3f} C, "
              f"largest {np.abs(res).max():.3f} C")
        print(f"   Module 4, open loop: chi_h = {CHI_H}, T_amb = {T_AMB}")
        worst = max(abs(p["drift_C_per_min"]) for p in pts)
        print(f"   largest drift {worst:.3f} C/min would bias u by at most "
              f"(tau/chi) dT/dt = {TAU / CHI_H * worst / 60:.2f} counts")
        print(f"   one-sigma fractional uncertainty of 1/chi_h from this fit: "
              f"{schi / chi * 100:.1f} %")
        print("   Two-setpoint method, run by run (first 30 C hold and the 35 C "
              "hold): chi_h = dT/du, T_amb = T - chi_h u")
        slopes = []
        for run in sorted({p["run"] for p in pts}):
            sel = [p for p in pts if p["run"] == run]
            lo = next(p for p in sel if p["setpoint_C"] == 30.0)
            hi = next((p for p in sel if p["setpoint_C"] == 35.0), None)
            if hi is None:
                continue
            c = (hi["T_C"] - lo["T_C"]) / (hi["u"] - lo["u"])
            slopes.append(c)
            print(f"   run {run} ({lo['mode']}), holds ending at {lo['t_end_s']:.0f} "
                  f"and {hi['t_end_s']:.0f} s: chi_h = {c:.4f}, T_amb = "
                  f"{lo['T_C'] - c * lo['u']:.2f} C")
        slopes = np.array(slopes)
        print(f"   mean chi_h {slopes.mean():.4f}, sd {slopes.std(ddof=1):.4f} "
              f"({slopes.std(ddof=1) / slopes.mean() * 100:.1f} % per pair)")

        print("\n2. One-lump sensitivities S = dlnX/dlnH and illustrative "
              "values for H x 1, 1.25, 1.5")
        rows = [
            ("chi_h (C/count)", lambda d: d["chi_h"], "-1", None, None),
            ("chi_c (C/count)", lambda d: d["chi_c"], "-1", None, None),
            ("tau (s)", lambda d: d["tau"], "-1", None, None),
            ("open-loop rise at u = +25 (C)", lambda d: d["open-loop rise at u=25"], "-1", None, None),
            ("PI steady command at 35 C (counts)", lambda d: d["PI steady command at 35 C"], "+1", None, None),
        ]
        for name, fn, S, _, _ in rows:
            vals = [fn(one_lump(f)) for f in FACTORS]
            print(f"   {name:<38} S {S:>5}: " + ", ".join(f"{v:.3f}" for v in vals))
        for kp in (2.0, 16.0, 64.0):
            d0 = one_lump(1.0, kp)
            L = d0["L"]
            vals = [one_lump(f, kp)["droop"] for f in FACTORS]
            print(f"   P droop at 35 C, Kp {kp:g} (L = {L:.2f})       S "
                  f"{L / (1 + L):+.2f}: " + ", ".join(f"{v:.3f}" for v in vals))
            vals = [one_lump(f, kp)["tau_cl"] for f in FACTORS]
            print(f"   P tau_cl, Kp {kp:g}                       S "
                  f"{-1 / (1 + L):+.2f}: " + ", ".join(f"{v:.2f}" for v in vals))
        d0 = one_lump(1.0, 12.0, 0.2)
        vals = [one_lump(f, 12.0, 0.2)["zeta_PI_1lump"] for f in FACTORS]
        print(f"   one-lump PI zeta, Kp 12 Ki 0.2             S "
              f"{1 / (1 + d0['L']):+.2f}: " + ", ".join(f"{v:.2f}" for v in vals))
        print("   one-lump PI natural frequency sqrt(P_u Ki / C) has no H in it: S = 0")

        print("\n   P droop: the absolute change between H1 and H2 is largest "
              "when P_u Kp = sqrt(H1 H2), i.e. L = 1 at the geometric mean H.")
        for f in (1.25, 1.5):
            kp_best = math.sqrt(f) / CHI_H
            change = ((35 - T_AMB) * (f / (f + CHI_H * kp_best * 1))
                      - (35 - T_AMB) / (1 + CHI_H * kp_best))
            print(f"   H x {f}: best Kp = sqrt({f})/chi_h = {kp_best:.2f}, droop "
                  f"change {change:.2f} C at a 35 C setpoint")

        print("\n3. Two-lump (course formulas, shared set: C, P_u, G 3.5 W/K, "
              "C_T/C 0.35 fixed; only H scaled)")
        for f in FACTORS:
            cfg = replace(base, heat_loss_w_per_c=H0 * f, setpoint_c=35.0)
            z16 = sim.two_lump_p_damping_ratio(cfg, kp_pwm_per_c=16.0)
            z200 = sim.two_lump_p_damping_ratio(cfg, kp_pwm_per_c=200.0)
            kic = sim.two_lump_pi_critical_integral_gain(replace(cfg, kp_pwm_per_c=12.0))
            print(f"   H x {f:<4} H = {H0 * f:.3f} W/K: zeta_2L,P(Kp 16) {z16:.3f}, "
                  f"zeta_2L,P(Kp 200) {z200:.3f}, K_i,crit(Kp 12) {kic:.2f}")

        print("\n4. Laird CP14-127-045 passive conductance, constant-property "
              "TEC model (rough)")
        qj = 0.5 * I_MAX ** 2 * R_M
        si = (QC_MAX + qj) / TH_K
        k_tec = (si * (TH_K - DT_MAX) - qj) / DT_MAX
        print(f"   S I_max = (Qc_max + I_max^2 R/2)/T_h = {si:.4f} W/K; "
              f"K_TEC = [S I_max (T_h - dT_max) - I_max^2 R/2]/dT_max = "
              f"{k_tec:.2f} W/K")
        print(f"   model H (shared set) = {H0:.3f} W/K")

    text = out.getvalue()
    print(text)
    os.makedirs(os.path.dirname(TXT), exist_ok=True)
    open(TXT, "w").write("python3 python/insulation_sensitivity.py\n\n" + text)
    with open(POINTS_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(pts[0].keys()))
        w.writeheader()
        for p in pts:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) else v)
                        for k, v in p.items()})

    os.makedirs(FIG_DIR, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.edgecolor": "#868686"})
    grey, blue, red = "#595959", "#1F4E79", "#C0392B"

    # Figure 1: operating-point diagram
    fig, ax = plt.subplots(figsize=(8.6, 5.6))
    ax.grid(True, color="#E4E4E4")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    u = np.linspace(0, 40, 200)
    ax.plot(u, T_AMB + CHI_H * u, color=blue, lw=2.0,
            label=f"Plant line, foam on: T = {T_AMB} + {CHI_H} u (Module 4)")
    for f, ls in ((1.25, "--"), (1.5, ":")):
        ax.plot(u, T_AMB + CHI_H / f * u, color=blue, lw=1.4, ls=ls,
                label=f"Plant line if H x {f} (illustrative, not measured)")
    for kp, c in ((2.0, "#8FB8DE"), (16.0, "#2E6DA4")):
        ax.plot(u, 35.0 - u / kp, color=c, lw=1.2,
                label=f"P controller line, Kp {kp:g}: T = 35 - u/{kp:g}")
    ax.axhline(35.0, color=red, lw=1.2, label="PI controller: T = 35 at any u")
    marker = {"P": "s", "PI": "o"}
    for mode in ("P", "PI"):
        sel = [p for p in pts if p["mode"] == mode]
        ax.plot([p["u"] for p in sel], [p["T_C"] for p in sel], marker[mode],
                color="black", ms=5.5, ls="none",
                label=f"Measured settled holds, {mode} (13 Oct)")
    ax.set_xlim(0, 40)
    ax.set_ylim(20, 40)
    ax.set_xlabel("Steady command u (PWM counts)")
    ax.set_ylabel("Steady plate temperature T (°C)")
    ax.set_title("Each steady state is where the plant line meets the controller line",
                 color="#404040")
    ax.legend(fontsize=7.6, loc="lower right", frameon=True)
    fig.text(0.01, 0.01, f"Fit to the {len(pts)} holds: chi_h = {chi:.3f} ± "
             f"{schi:.3f} °C/count, T_amb = {T0:.2f} ± {sT0:.2f} °C.\nRemoving "
             "foam lowers the plant-line slope; the P point slides down (more "
             "droop), the PI point slides right (more command).",
             fontsize=7.6, color=grey)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.93, bottom=0.16)
    fig.savefig(os.path.join(FIG_DIR, "operating_points.png"), dpi=200,
                facecolor="white")
    plt.close(fig)

    # Figure 2: where the foam shows up
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.4))
    shades = {1.0: "#1F4E79", 1.25: "#4F8FC9", 1.5: "#9CC3E6"}
    ax = axes[0][0]
    kp = np.logspace(-1, 3, 300)
    for f in FACTORS:
        ax.semilogx(kp, (35 - T_AMB) / (1 + CHI_H / f * kp), color=shades[f],
                    lw=1.6, label=f"H x {f:g}")
    diff = (35 - T_AMB) / (1 + CHI_H / 1.5 * kp) - (35 - T_AMB) / (1 + CHI_H * kp)
    ax.semilogx(kp, diff, color=red, lw=1.2, ls="--",
                label="droop change, H x 1.5 minus H x 1")
    kbest = math.sqrt(1.5) / CHI_H
    ax.axvline(kbest, color=red, lw=0.8, ls=":")
    ax.text(kbest * 1.1, 11.5, f"largest change at\nKp = {kbest:.1f}", color=red,
            fontsize=8)
    ax.set_xlabel("Kp (PWM/°C)")
    ax.set_ylabel("P-control droop at 35 °C (°C)")
    ax.set_title("(a) P droop: biggest foam signal near L = 1", color="#404040",
                 fontsize=10)
    ax.legend(fontsize=8)

    for f in FACTORS:
        cfg = replace(base, heat_loss_w_per_c=H0 * f)
        tP, TP, uP = simulate(cfg, "p", 2.0, 0.0, 30.0, 35.0, 400.0)
        tI, TI, uI = simulate(cfg, "pi", 12.0, 0.2, 30.0, 35.0, 300.0)
        axes[0][1].plot(tP, TP, color=shades[f], lw=1.5, label=f"H x {f:g}")
        axes[1][0].plot(tI, TI, color=shades[f], lw=1.5, label=f"H x {f:g}")
        axes[1][1].plot(tI, uI, color=shades[f], lw=1.5, label=f"H x {f:g}")
    axes[0][1].set_title("(b) P, Kp 2: the plate settles lower", color="#404040",
                         fontsize=10)
    axes[1][0].set_title("(c) PI, Kp 12, Ki 0.2: temperature hides H",
                         color="#404040", fontsize=10)
    axes[1][1].set_title("(d) PI: the command reveals H", color="#404040",
                         fontsize=10)
    for ax in (axes[0][1], axes[1][0]):
        ax.axhline(35, color=grey, ls="--", lw=0.9)
        ax.set_ylabel("Simulated T_m (°C)")
    axes[1][1].set_ylabel("Applied command u (counts)")
    axes[1][1].set_ylim(0, 80)
    for ax in axes.flat:
        ax.grid(True, color="#E4E4E4")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    for ax in (axes[0][1], axes[1][0], axes[1][1]):
        ax.set_xlabel("Time from the 30 → 35 °C step (s)")
        ax.legend(fontsize=8, loc="lower right")
    fig.text(0.01, 0.008, "Course two-lump code with the shared parameter set "
             "(G 3.5 W/K, C_T/C 0.35); only H is multiplied. H x 1.25 and x 1.5 "
             "are illustrations, not measurements.", fontsize=7.8, color=grey)
    fig.subplots_adjust(left=0.07, right=0.985, top=0.95, bottom=0.1,
                        hspace=0.42, wspace=0.22)
    fig.savefig(os.path.join(FIG_DIR, "insulation_sensitivity.png"), dpi=200,
                facecolor="white")
    plt.close(fig)
    print(f"Figures in {FIG_DIR}, points in {POINTS_CSV}, text in {TXT}")


if __name__ == "__main__":
    main()
