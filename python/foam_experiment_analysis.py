#!/usr/bin/env python3
"""
Phys 39 Module 6, foam-removal experiment of 19 October. Naidu / Cohen

    python3 python/foam_experiment_analysis.py     (run from the repository root)

Two blocks in one GUI session, foam OFF then foam ON (a third, foam-off block
was planned but not run). Each block: PI (Kp 12, Ki 0.2) hold at 30 C, hold at
45 C, control off (passive cool-down), P (Kp 2) at a 35 C setpoint.

Measurements, per block
  * steady command u_ss at 30 and 45 C (mean of the last 60 s of each hold);
    slope du_ss/dT = H/P_u,h = 1/chi_h and intercept T_eff
  * P droop at Kp 2 (L about 1), last 60 s
  * passive cool-down after the 45 C hold, single exponential fitted over the
    same window (20 to 150 s after control off) in both blocks

Uncertainty of each hold's u_ss: standard error of the mean (lag-1
autocorrelation allowed for) combined with the bias a residual drift would
cause, (tau/chi_h) |dT/dt|.

INPUT   data/module_06/pi_run_20261019_105852.csv
        data/module_06/steady_operating_points.csv   (13 October, foam on)
OUTPUT  data/module_06/foam_experiment_output.txt
        docs/figures/module_06/oral_review/foam_experiment.png
"""

import csv
import io
import math
import os
from contextlib import redirect_stdout

import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAW = "data/module_06/pi_run_20261019_105852.csv"
REF = "data/module_06/steady_operating_points.csv"
TXT = "data/module_06/foam_experiment_output.txt"
FIG = "docs/figures/module_06/oral_review/foam_experiment.png"

BLOCK_SPLIT_S = 1370.0          # control was off and the foam was fitted here
FOAM = {1: "foam off", 2: "foam on"}
TAU, CHI_H = 62.9, 0.501        # Module 4, only for the drift-bias bound
WINDOW_S = 60.0
COOL_FIT = (20.0, 150.0)        # s after control off, common to both blocks
T_INF_COMMON = 23.0             # block 1 asymptote, fit 20 s to the end (349 s)


def load():
    rows = list(csv.DictReader(open(RAW, newline="")))
    col = lambda k: np.array([float(r[k]) for r in rows])
    return dict(t=col("time_s"), T=col("temperature_C"), u=col("u_applied"),
                sp=col("setpoint_C"), kp=col("kp"), ki=col("ki"),
                on=np.array([r["control_on"] == "1" for r in rows]),
                mode=np.array([r["mode"] for r in rows]))


def runs_of(mask):
    """(start, end) index pairs of consecutive True values."""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    cuts = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[cuts + 1]]
    ends = np.r_[idx[cuts], idx[-1]]
    return list(zip(starts, ends))


def hold(d, a, b):
    t, T, u = d["t"][a:b + 1], d["T"][a:b + 1], d["u"][a:b + 1]
    m = t >= t[-1] - WINDOW_S
    x = u[m] - u[m].mean()
    rho = (x[1:] * x[:-1]).sum() / (x * x).sum() if (x * x).sum() > 0 else 0.0
    n_eff = max(m.sum() * (1 - rho) / (1 + rho), 1.0)
    sem = u[m].std(ddof=1) / math.sqrt(n_eff)
    drift = np.polyfit(t[m], T[m], 1)[0]                      # C/s
    bias = TAU / CHI_H * abs(drift)
    return dict(t0=t[0], t1=t[-1], T=T[m].mean(), u=u[m].mean(),
                u_sd=u[m].std(ddof=1), drift_min=drift * 60, sem=sem,
                bias=bias, du=math.hypot(sem, bias))


def find_holds(d):
    out = {}
    for blk, sel in ((1, d["t"] < BLOCK_SPLIT_S), (2, d["t"] >= BLOCK_SPLIT_S)):
        for name, cond in (
                ("PI30", (d["mode"] == "PI") & (d["sp"] == 30) & (d["kp"] == 12)),
                ("PI45", (d["mode"] == "PI") & (d["sp"] == 45) & (d["kp"] == 12)),
                ("P35", (d["mode"] == "P") & (d["sp"] == 35) & (d["kp"] == 2))):
            segs = runs_of(sel & cond & d["on"])
            a, b = max(segs, key=lambda s: s[1] - s[0])
            out[(blk, name)] = hold(d, a, b)
        h45 = out[(blk, "PI45")]
        p35 = out[(blk, "P35")]
        off = (d["t"] > h45["t1"]) & (d["t"] < p35["t0"]) & ~d["on"]
        a, b = max(runs_of(off), key=lambda s: s[1] - s[0])
        out[(blk, "cool")] = (a, b)
    return out


def fit_cool(d, a, b, lo, hi):
    t = d["t"][a:b + 1] - d["t"][a]
    T = d["T"][a:b + 1]
    m = (t >= lo) & (t <= hi)
    f = lambda x, Ti, A, tau: Ti + A * np.exp(-x / tau)
    p, cv = curve_fit(f, t[m], T[m], p0=(23.0, 20.0, 60.0))
    return p[0], p[2], math.sqrt(cv[2, 2]), t[-1]


def main():
    d = load()
    H = find_holds(d)
    out = io.StringIO()
    res = {}
    with redirect_stdout(out):
        print("Holds (last 60 s). du = sqrt(SEM^2 + drift bias^2), drift bias = "
              "(tau/chi_h)|dT/dt|")
        for blk in (1, 2):
            for name in ("PI30", "PI45", "P35"):
                h = H[(blk, name)]
                print(f"  block {blk} ({FOAM[blk]}) {name}: {h['t0']:6.0f} to "
                      f"{h['t1']:6.0f} s ({h['t1'] - h['t0']:3.0f} s), T "
                      f"{h['T']:.3f} C, u {h['u']:6.2f} (sd {h['u_sd']:.2f}, "
                      f"SEM {h['sem']:.3f}, drift {h['drift_min']:+.3f} C/min, "
                      f"bias {h['bias']:.3f}), du {h['du']:.3f}")
        print("\nSlope of steady command against temperature (30 to 45 C holds)")
        for blk in (1, 2):
            lo, hi = H[(blk, "PI30")], H[(blk, "PI45")]
            dT = hi["T"] - lo["T"]
            s = (hi["u"] - lo["u"]) / dT
            ds = math.hypot(lo["du"], hi["du"]) / dT
            teff = lo["T"] - lo["u"] / s
            res[blk] = (s, ds, teff)
            print(f"  block {blk} ({FOAM[blk]}): H/P_u,h = {s:.4f} +/- {ds:.4f} "
                  f"counts/C (chi_h = {1 / s:.4f}), intercept T_eff = {teff:.2f} C")
        (s1, d1, t1), (s2, d2, t2) = res[1], res[2]
        ratio = s1 / s2
        dratio = ratio * math.hypot(d1 / s1, d2 / s2)
        print(f"  H(foam off)/H(foam on) = {ratio:.4f} +/- {dratio:.4f} "
              f"(1 sigma); 2-sigma range {ratio - 2 * dratio:.3f} to "
              f"{ratio + 2 * dratio:.3f}")
        print(f"  intercept shift, foam on minus foam off: {t2 - t1:+.2f} C "
              f"(a constant offset of {H[(2, 'PI30')]['u'] - H[(1, 'PI30')]['u']:+.2f} "
              f"counts at 30 C, {H[(2, 'PI45')]['u'] - H[(1, 'PI45')]['u']:+.2f} at 45 C)")

        print("\nP control, Kp 2, setpoint 35 C (L about 1)")
        for blk in (1, 2):
            h = H[(blk, "P35")]
            print(f"  block {blk} ({FOAM[blk]}): T_ss {h['T']:.3f} C, droop "
                  f"{35 - h['T']:.3f} C, u {h['u']:.2f}")

        print(f"\nPassive cool-down after the 45 C hold, T = T_inf + A exp(-t/tau)")
        for blk in (1, 2):
            a, b = H[(blk, "cool")]
            for lo, hi in ((COOL_FIT[0], COOL_FIT[1]), (10.0, 150.0), (40.0, 150.0)):
                Ti, tau, dtau, span = fit_cool(d, a, b, lo, hi)
                tag = "  common window" if (lo, hi) == COOL_FIT else "  sensitivity  "
                print(f"  block {blk} ({FOAM[blk]}){tag} {lo:.0f} to {hi:.0f} s: "
                      f"tau {tau:.1f} +/- {dtau:.1f} s, T_inf {Ti:.2f} C "
                      f"(cool-down lasted {span:.0f} s)")

        a, b = H[(1, "cool")]
        Ti, tau, dtau, span = fit_cool(d, a, b, 20.0, 1e9)
        print(f"  block 1 (foam off), 20 s to the end ({span:.0f} s): tau {tau:.1f} s, "
              f"T_inf {Ti:.2f} C  <- the only cool-down long enough to fix T_inf")
        print("  same common window with T_inf held equal in both blocks:")
        for t_fix in (22.8, 23.0, 23.2):
            taus = []
            for blk in (1, 2):
                a, b = H[(blk, "cool")]
                tt = d["t"][a:b + 1] - d["t"][a]
                TT = d["T"][a:b + 1]
                m = (tt >= COOL_FIT[0]) & (tt <= COOL_FIT[1])
                g = lambda x, A, tau, t_fix=t_fix: t_fix + A * np.exp(-x / tau)
                p, _ = curve_fit(g, tt[m], TT[m], p0=(20.0, 60.0))
                taus.append(p[1])
            print(f"    T_inf = {t_fix:.1f} C: tau foam off {taus[0]:.1f} s, foam on "
                  f"{taus[1]:.1f} s, ratio on/off {taus[1] / taus[0]:.3f}")

        print("\n13 October reference (foam on, 30 and 35 C pairs): chi_h mean "
              "0.5046, sd 0.0080 per pair; see python/insulation_sensitivity.py")

    text = out.getvalue()
    print(text)
    open(TXT, "w").write("python3 python/foam_experiment_analysis.py\n\n" + text)

    # Figure
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5,
                         "axes.edgecolor": "#868686"})
    fig = plt.figure(figsize=(11.0, 7.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.1], hspace=0.38, wspace=0.24)
    ax0 = fig.add_subplot(gs[0, :])
    ax1 = fig.add_subplot(gs[1, 0])
    ax2 = fig.add_subplot(gs[1, 1])
    col = {1: "#C0392B", 2: "#1F4E79"}
    for ax in (ax0, ax1, ax2):
        ax.grid(True, color="#E4E4E4")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    t, T = d["t"], d["T"]
    ax0.axvspan(t[0], BLOCK_SPLIT_S, color="#F6DCD9", lw=0)
    ax0.axvspan(BLOCK_SPLIT_S, t[-1], color="#DCE7F2", lw=0)
    ax0.plot(t, T, color="#1E6B3A", lw=1.2, label="plate temperature")
    ax0.plot(t, np.where(d["on"], d["sp"], np.nan), color="#595959", lw=0.9,
             ls="--", label="setpoint (control on)")
    ax0b = ax0.twinx()
    ax0b.plot(t, d["u"], color="#7F7F7F", lw=0.8, label="applied command")
    ax0b.set_ylabel("Command (counts)", color="#7F7F7F")
    ax0b.set_ylim(-5, 400)
    ax0.set_ylim(20, 50)
    ax0.set_xlabel("GUI time (s)")
    ax0.set_ylabel("Temperature (°C)")
    ax0.text(60, 49.5, "Block 1: foam OFF", color=col[1], fontsize=9.5, va="top")
    ax0.text(BLOCK_SPLIT_S + 40, 49.5, "Block 2: foam ON", color=col[2],
             fontsize=9.5, va="top")
    ax0.set_title("(a) The run: PI 30 °C, PI 45 °C, control off, P at Kp 2",
                  color="#404040", fontsize=10)
    ax0.legend(loc="center right", fontsize=8)

    for blk in (1, 2):
        lo, hi, p = H[(blk, "PI30")], H[(blk, "PI45")], H[(blk, "P35")]
        s, ds, teff = res[blk]
        uu = np.linspace(0, 52, 50)
        ax1.plot(uu, teff + uu / s, color=col[blk], lw=1.2,
                 label=f"{FOAM[blk]}: slope 1/χ = {s:.3f} ± {ds:.3f} counts/°C")
        ax1.errorbar([lo["u"], hi["u"]], [lo["T"], hi["T"]],
                     xerr=[lo["du"], hi["du"]], fmt="o", color=col[blk], ms=5)
        ax1.plot([p["u"]], [p["T"]], "s", color=col[blk], ms=6, mfc="none")
    ax1.set_xlim(0, 52)
    ax1.set_ylim(22, 47)
    ax1.set_xlabel("Steady command u (counts)")
    ax1.set_ylabel("Steady temperature (°C)")
    ax1.set_title("(b) PI holds (dots) and P point (squares)", color="#404040",
                  fontsize=10)
    ax1.legend(fontsize=8, loc="upper left")
    ax1.text(51, 23, f"H(off)/H(on) = {ratio:.3f} ± {dratio:.3f}", ha="right",
             fontsize=9, color="#404040")

    for blk in (1, 2):
        a, b = H[(blk, "cool")]
        tt = d["t"][a:b + 1] - d["t"][a]
        TT = d["T"][a:b + 1]
        m = (tt >= COOL_FIT[0]) & (tt <= COOL_FIT[1])
        g = lambda x, A, tau: T_INF_COMMON + A * np.exp(-x / tau)
        p, _ = curve_fit(g, tt[m], TT[m], p0=(20.0, 60.0))
        theta = TT - T_INF_COMMON
        ok = theta > 0.05
        ax2.semilogy(tt[ok], theta[ok], color=col[blk], lw=1.3,
                     label=f"{FOAM[blk]}: τ = {p[1]:.1f} s")
    ax2.axvspan(*COOL_FIT, color="#F2F2F2", lw=0)
    ax2.set_xlim(0, 360)
    ax2.set_xlabel("Time after control off (s)")
    ax2.set_ylabel(f"T − {T_INF_COMMON} °C, log scale")
    ax2.set_title(f"(c) Passive cool-down from 45 °C, fit {COOL_FIT[0]:.0f} to "
                  f"{COOL_FIT[1]:.0f} s (shaded)", color="#404040", fontsize=10)
    ax2.legend(fontsize=8, loc="upper right")
    fig.text(0.01, 0.008, "19 October, one GUI session (pi_run_20261019_105852.csv). "
             "Error bars: SEM and residual-drift bias of each 60 s mean. The planned "
             "third block (foam off again) was not run.", fontsize=7.8,
             color="#595959")
    fig.subplots_adjust(left=0.07, right=0.93, top=0.95, bottom=0.09)
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=200, facecolor="white")
    print(f"Figure {FIG}, text {TXT}")


if __name__ == "__main__":
    main()
