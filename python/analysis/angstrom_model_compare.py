#!/usr/bin/env python3
"""
Phys 39 Module 8, Part II. Reconstruct T(x, t) along the rod from the
measured base temperature and compare with T2..T5. Naidu / Cohen

    python3 python/analysis/angstrom_model_compare.py <run.csv> --room 27.10 \
        --window 240:1877:3077 [--window 180:3437:4337] [--mask <mask.csv>] \
        [--kappa 9.17e-5 --nu 2.02e-3]

MODEL
  d(theta)/dt = kappa d2(theta)/dx2 - nu theta,  theta = T - T_room,
  on 0 <= x <= L (L = 281.9 mm, T1 hole to tip), with
    theta(0, t) = T1(t) - T_room       (measured, offsets applied)
    d(theta)/dx = 0 at x = L           (insulated tip, as in the finite-rod fit)
  Crank-Nicolson, dx = 1 mm, dt = 0.5 s, started from the first record with
  the measured T1..T5 interpolated along the rod (constant beyond T5).
  kappa and nu default to the nine-window weighted means from
  data/module_08/part2_parameters.txt; nothing is fitted here.

OUTPUT
  docs/figures/module_08/model_compare_<run>.png        whole run
  docs/figures/module_08/model_compare_<run>_<P>s.png   each window
  data/module_08/model_compare_<run>.txt                residual summary
"""

import argparse
import csv
import os
import re

import numpy as np
from scipy.linalg import solve_banded
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D8 = os.path.join(REPO, "data", "module_08")
FIG = os.path.join(REPO, "docs", "figures", "module_08")
OFFSETS = os.path.join(D8, "calibration_rod_run_20261026_112627.csv")
ROD = ["T1_C", "T2_C", "T3_C", "T4_C", "T5_C"]
XS = np.array([0.0, 25.4, 50.8, 76.2, 101.6]) / 1000
COL = {"T1_C": "#1f77b4", "T2_C": "#ff7f0e", "T3_C": "#2ca02c", "T4_C": "#9467bd", "T5_C": "#8c564b"}


def load(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    t = np.array([float(r["time_ms"]) for r in rows]) / 1000
    T = {c: np.array([float(r[c]) for r in rows]) for c in ROD}
    return t, T


def offsets():
    out = {}
    with open(OFFSETS, newline="") as fh:
        for r in csv.DictReader(fh):
            ch = r["channel"].strip()
            if ch.startswith("R"):
                out[f"T{ch[1:]}_C"] = float(r["offset_C"])
    return out


def mask(path, t, T):
    if not path:
        return []
    notes = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            col = f"{r['channel'].strip()}_C"
            if col in T:
                sel = (t >= float(r["t_start_s"])) & (t <= float(r["t_end_s"]))
                T[col][sel] = np.nan
                notes.append(f"{col} {r['t_start_s']} to {r['t_end_s']} s masked")
    return notes


def defaults():
    path = os.path.join(D8, "part2_parameters.txt")
    kap = nu = None
    if os.path.exists(path):
        for line in open(path):
            m = re.match(r"\s+(kappa|nu)\s+([\d.]+)\s+stat", line)
            if m and line.find("1e-5") > 0 and kap is None and m.group(1) == "kappa":
                kap = float(m.group(2)) * 1e-5
            if m and m.group(1) == "nu" and nu is None:
                nu = float(m.group(2)) * 1e-3
    return kap, nu


def simulate(t, base, init, kap, nu, L, dx=1e-3, dt=0.5):
    N = int(round(L / dx))
    x = np.linspace(0, L, N + 1)
    dx = x[1] - x[0]
    n = x.size - 1                       # unknowns: nodes 1..n (n is the tip)
    r = kap * dt / dx ** 2
    # implicit matrix (I - dt/2 K) in solve_banded storage; unknown i is node i+1
    ab = np.zeros((3, n))
    ab[0, 1:] = -r / 2                   # A[i-1, i]
    ab[1, :] = 1 + r + nu * dt / 2       # A[i, i]
    ab[2, :-1] = -r / 2                  # A[i+1, i]
    ab[2, n - 2] = -r                    # tip row: ghost node theta_{n+1} = theta_{n-1}
    tg = np.arange(t[0], t[-1], dt)
    b = np.interp(tg, t[np.isfinite(base)], base[np.isfinite(base)])
    th = np.interp(x, XS[np.isfinite(init)], init[np.isfinite(init)])
    out = np.zeros((tg.size, XS.size))
    out[0] = np.interp(XS, x, th)
    for k in range(1, tg.size):
        u = th[1:]
        left = np.r_[th[0], u[:-1]]
        right = np.r_[u[1:], u[n - 2]]
        rhs = u * (1 - r - nu * dt / 2) + r / 2 * (left + right)
        rhs[n - 1] = u[n - 1] * (1 - r - nu * dt / 2) + r * u[n - 2]
        rhs[0] += r / 2 * b[k]           # implicit boundary value
        th = np.r_[b[k], solve_banded((1, 1), ab, rhs)]
        out[k] = np.interp(XS, x, th)
    return tg, out


def sine(t, y, w):
    ok = np.isfinite(y)
    X = np.column_stack([np.ones(ok.sum()), np.sin(w * t[ok]), np.cos(w * t[ok]), t[ok] - t[ok].mean()])
    p, *_ = np.linalg.lstsq(X, y[ok], rcond=None)
    return np.hypot(p[1], p[2]), np.arctan2(-p[1], p[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--room", type=float, required=True)
    ap.add_argument("--window", action="append", default=[], help="period:t0:t1 (s)")
    ap.add_argument("--mask")
    ap.add_argument("--kappa", type=float)
    ap.add_argument("--nu", type=float)
    ap.add_argument("--length-mm", type=float, default=281.9)
    a = ap.parse_args()
    kd, nd = defaults()
    kap = a.kappa or kd
    nu = a.nu or nd
    if kap is None or nu is None:
        raise SystemExit("give --kappa and --nu or run part2_parameters.py first")
    t, T = load(a.run)
    off = offsets()
    for c in ROD:
        T[c] = T[c] - off.get(c, 0.0)
    notes = mask(a.mask, t, T)
    theta = {c: T[c] - a.room for c in ROD}
    init = np.array([theta[c][0] for c in ROD])
    tg, sim = simulate(t, theta["T1_C"], init, kap, nu, a.length_mm / 1000)
    model = {c: np.interp(t, tg, sim[:, i]) + a.room for i, c in enumerate(ROD)}
    run = os.path.splitext(os.path.basename(a.run))[0]
    lines = [f"python3 python/analysis/angstrom_model_compare.py {a.run} --room {a.room:g} "
             + " ".join(f"--window {w}" for w in a.window) + (f" --mask {a.mask}" if a.mask else "")
             + (f" --kappa {a.kappa:g}" if a.kappa else "") + (f" --nu {a.nu:g}" if a.nu else ""),
             "", f"kappa = {kap:.4g} m2/s, nu = {nu:.4g} 1/s, room {a.room:.2f} C, L = {a.length_mm:g} mm;"
             " offsets applied; boundary = measured T1", *notes, ""]

    fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    for c in ROD:
        ax[0].plot(t, T[c], color=COL[c], lw=1, label=c[:2] + " measured")
        if c != "T1_C":
            ax[0].plot(t, model[c], color=COL[c], lw=1, ls="--")
            ax[1].plot(t, T[c] - model[c], color=COL[c], lw=0.8, label=c[:2])
    ax[0].plot([], [], "k--", lw=1, label="model (dashed)")
    ax[0].set_ylabel("T (°C)")
    ax[0].legend(ncol=3, fontsize=8)
    ax[0].set_title(f"{run}: rod model driven by measured T1 (κ = {kap:.3g} m²/s, ν = {nu:.3g} 1/s, no fit)")
    ax[1].axhline(0, color="k", lw=0.6)
    ax[1].set_ylabel("measured − model (°C)")
    ax[1].set_xlabel("Arduino time (s)")
    ax[1].legend(ncol=4, fontsize=8)
    for a_ in ax:
        a_.grid(alpha=0.3)
    for wspec in a.window:
        P, t0, t1 = (float(v) for v in wspec.split(":"))
        for a_ in ax:
            a_.axvspan(t0, t1, color="0.85", zorder=0)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, f"model_compare_{run}.png"), dpi=110)
    plt.close(fig)

    for wspec in a.window:
        P, t0, t1 = (float(v) for v in wspec.split(":"))
        w = 2 * np.pi / P
        sel = (t >= t0) & (t <= t1)
        lines.append(f"Window {P:g} s, {t0:g} to {t1:g} s:")
        lines.append(f"  {'sensor':<6} {'rms res (C)':>11} {'mean res (C)':>12} {'B meas':>7} {'B model':>8}"
                     f" {'ratio':>6} {'phase meas-model (rad)':>22}")
        Bm1, ph1 = sine(t[sel], T["T1_C"][sel], w)
        for c in ROD[1:]:
            r = T[c][sel] - model[c][sel]
            Bm, phm = sine(t[sel], T[c][sel], w)
            Bs, phs = sine(t[sel], model[c][sel], w)
            dph = (phm - phs + np.pi) % (2 * np.pi) - np.pi
            lines.append(f"  {c[:2]:<6} {np.sqrt(np.nanmean(r**2)):11.3f} {np.nanmean(r):12.3f} {Bm:7.3f}"
                         f" {Bs:8.3f} {Bm/Bs:6.3f} {dph:22.3f}")
        fig, ax = plt.subplots(2, 1, figsize=(11, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
        for c in ROD:
            ax[0].plot(t[sel], T[c][sel], color=COL[c], lw=1.2, label=c[:2])
            if c != "T1_C":
                ax[0].plot(t[sel], model[c][sel], color=COL[c], lw=1, ls="--")
                ax[1].plot(t[sel], T[c][sel] - model[c][sel], color=COL[c], lw=0.9)
        ax[0].set_title(f"{run}, {P:g} s window: measured (solid) and model from T1 (dashed)")
        ax[0].set_ylabel("T (°C)")
        ax[0].legend(ncol=5, fontsize=8)
        ax[1].axhline(0, color="k", lw=0.6)
        ax[1].set_ylabel("measured − model (°C)")
        ax[1].set_xlabel("Arduino time (s)")
        for a_ in ax:
            a_.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, f"model_compare_{run}_{P:g}s.png"), dpi=110)
        plt.close(fig)
    text = "\n".join(lines) + "\n"
    print(text)
    with open(os.path.join(D8, f"model_compare_{run}.txt"), "w") as fh:
        fh.write(text)


if __name__ == "__main__":
    main()
