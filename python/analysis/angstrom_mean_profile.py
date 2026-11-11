#!/usr/bin/env python3
"""
Phys 39 Module 8, Stage 6. Mean-temperature profile against the finite
insulated-tip rod. Naidu / Cohen

    python3 python/analysis/angstrom_mean_profile.py data/module_08/angstrom_fit_<run>_PI_<P>s.csv ... \
        [--length-mm 281.9 --length-err-mm 1.3] [--room 20261110=24.28] [--exclude T2]

For each angstrom_fit CSV (a_i = fitted mean of T1..T5, offsets applied) fit

    a(xi) - Tinf = (a0 - Tinf) cosh(mu (1 - xi)) / cosh(mu),   xi = x / L

for a0 and mu = mL, then m = mu / L. Point errors: cycle-to-cycle scatter of
a_i (s_mean_C column) combined with the calibration-offset standard error
(sem_C in the calibration file) and the position uncertainty (slope times
dx; T1 has none). Parameter errors are scaled by sqrt(chi2/dof) when that
exceeds 1. The error of m combines mu and L. The effect of Tinf is shown
separately by refitting with Tinf +/- 0.1 C.

Tinf is the measured room temperature of the run's day:
    2 Nov 22.53 C, 4 Nov 27.10 C (09:30 baseline), 10 Nov 24.28 C
(mean of T1 to T5 with offsets over the idle baseline).

Comparison: Module 7 full-length mean profile m = 4.117 +/- 0.07 1/m, and the
Angstrom value sqrt(q^2 - q'^2) from the same fit's .txt (semi-infinite q, q').

Output: data/module_08/angstrom_mean_profile.txt and
        docs/figures/module_08/angstrom_mean_profile.png
"""

import argparse
import csv
import io
import os
import re
from contextlib import redirect_stdout

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import least_squares

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(REPO, "data", "module_08")
FIGS = os.path.join(REPO, "docs", "figures", "module_08")
CAL = os.path.join(DATA, "calibration_rod_run_20261026_112627.csv")
MAP = os.path.join(DATA, "sensor_map.csv")
ROD = ["T1_C", "T2_C", "T3_C", "T4_C", "T5_C"]
ROOM = {"20261102": 22.53, "20261104": 27.10, "20261110": 24.28}
M7 = (4.117, 0.07)


def cal_sem():
    with open(CAL, newline="") as fh:
        rows = {r["channel"]: float(r["sem_C"]) for r in csv.DictReader(fh)}
    return np.array([rows[f"R{i}"] for i in range(1, 6)])


def pos_err():
    with open(MAP, newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["channel"].startswith("R")]
    return np.array([float(r["position_uncertainty_mm"] or 0) / 1000 for r in rows[:5]])


def load(path):
    with open(path, newline="") as fh:
        rows = {r["channel"]: r for r in csv.DictReader(fh)}
    x = np.array([float(rows[c]["x_m"]) for c in ROD])
    a = np.array([float(rows[c]["mean_C"]) for c in ROD])
    sa = np.array([float(rows[c].get("s_mean_C") or "nan") for c in ROD])
    return x, a, sa


def angstrom_m(path):
    txt = path[:-4] + ".txt"
    s = open(txt).read()
    q, sq = map(float, re.search(r"^q  = ([\d.]+) \+/- ([\d.]+)", s, re.M).groups())
    qp, sqp = map(float, re.search(r"^q' = ([\d.]+) \+/- ([\d.]+)", s, re.M).groups())
    m2 = q * q - qp * qp
    if m2 <= 0:
        return np.nan, np.nan
    m = np.sqrt(m2)
    return m, np.hypot(q * sq, qp * sqp) / m


def fit(x, a, s_a, dx, L, Tinf, use):
    xi = x / L

    def model(p, xi=xi):
        return Tinf + (p[0] - Tinf) * np.cosh(p[1] * (1 - xi)) / np.cosh(p[1])

    def sig(p):
        slope = (p[0] - Tinf) * p[1] / L * np.sinh(p[1] * (1 - xi)) / np.cosh(p[1])
        return np.sqrt(s_a ** 2 + (slope * dx) ** 2)

    def resid(p):
        return ((a - model(p)) / sig(p))[use]

    r = least_squares(resid, [a[0], 1.2])
    chi2 = float(np.sum(r.fun ** 2))
    dof = int(use.sum()) - 2
    cov = np.linalg.inv(r.jac.T @ r.jac)
    if dof > 0:
        cov *= max(chi2 / dof, 1.0)
    return r.x, np.sqrt(np.diag(cov)), chi2, dof, a - model(r.x), model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fits", nargs="+")
    ap.add_argument("--length-mm", type=float, default=281.9)
    ap.add_argument("--length-err-mm", type=float, default=1.3)
    ap.add_argument("--room", action="append", default=[],
                    help="date=T, e.g. 20261110=24.28 (overrides the built-in table)")
    ap.add_argument("--exclude", action="append", default=[],
                    help="sensor to leave out of the fit, e.g. T2 (can repeat)")
    ap.add_argument("--tag", default="", help="suffix for the output file names")
    a = ap.parse_args()
    room = dict(ROOM)
    for s in a.room:
        k, v = s.split("=")
        room[k] = float(v)
    L, sL = a.length_mm / 1000, a.length_err_mm / 1000
    sem, dx = cal_sem(), pos_err()
    use = np.array([c[:2] not in a.exclude for c in ROD])

    out = io.StringIO()
    fig, ax = plt.subplots(figsize=(8, 5.5))
    with redirect_stdout(out):
        print(f"L = {L * 1000:.1f} +/- {sL * 1000:.1f} mm; excluded: {', '.join(a.exclude) or 'none'}")
        print(f"Module 7 full-length mean profile: m = {M7[0]:.3f} +/- {M7[1]:.2f} 1/m\n")
        print(f"{'fit file':<58} {'Tinf':>6} {'a0 (C)':>13} {'mu = mL':>13} {'m (1/m)':>13} "
              f"{'chi2/dof':>8} {'m(Tinf+/-0.1)':>13} {'sqrt(q2-q2p)':>13}")
        for path in a.fits:
            name = os.path.basename(path)
            date = re.search(r"(2026\d{4})_", name).group(1)
            Tinf = room[date]
            x, am, sa = load(path)
            s_a = np.sqrt(np.nan_to_num(sa) ** 2 + sem ** 2)
            p, e, chi2, dof, res, model = fit(x, am, s_a, dx, L, Tinf, use)
            mu, smu = p[1], e[1]
            m = mu / L
            sm = m * np.hypot(smu / mu, sL / L)
            mlo = fit(x, am, s_a, dx, L, Tinf - 0.1, use)[0][1] / L
            mhi = fit(x, am, s_a, dx, L, Tinf + 0.1, use)[0][1] / L
            ma, sma = angstrom_m(path)
            print(f"{name:<58} {Tinf:6.2f} {p[0]:7.2f}+/-{e[0]:.2f} {mu:7.3f}+/-{smu:.3f} "
                  f"{m:7.2f}+/-{sm:.2f} {chi2:4.1f}/{dof:<3} {mlo:6.2f}/{mhi:<6.2f} "
                  f"{ma:7.2f}+/-{sma:.2f}")
            print(f"{'':<58} residuals a_i - fit (C): "
                  + "  ".join(f"{c[:2]} {r:+.3f}{'' if u else ' (excl.)'}"
                              for c, r, u in zip(ROD, res, use)))
            xx = np.linspace(0, x.max() * 1.05, 80)
            h = ax.errorbar(x * 1000, am - Tinf, yerr=s_a, fmt="o", ms=4,
                            label=f"{name[13:-4]}: m = {m:.2f}")
            ax.plot(xx * 1000, model(p, xx / L) - Tinf, color=h[0].get_color(), lw=1)
        print("\nm(Tinf+/-0.1) = m refitted with room temperature 0.1 C lower / higher.")
        print("sqrt(q2-q2p) = Angstrom m from the semi-infinite q and q' of the same window.")
    text = out.getvalue()
    print(text)
    tag = f"_{a.tag}" if a.tag else ""
    cmd = "python3 python/analysis/angstrom_mean_profile.py " + " ".join(
        os.path.relpath(f, REPO) for f in a.fits) + "".join(f" --exclude {s}" for s in a.exclude)
    with open(os.path.join(DATA, f"angstrom_mean_profile{tag}.txt"), "w") as fh:
        fh.write(cmd + "\n\n" + text)
    ax.set_xlabel("x from T1 (mm)")
    ax.set_ylabel("mean excess temperature a_i - T_inf (°C)")
    ax.set_title("Mean profile and finite insulated-tip fit"
                 + (f" (excluded: {', '.join(a.exclude)})" if a.exclude else ""), fontsize=10)
    ax.legend(fontsize=7)
    ax.grid(True, color="#E4E4E4")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGS, f"angstrom_mean_profile{tag}.png"), dpi=150)
    print(f"Wrote data/module_08/angstrom_mean_profile{tag}.txt and "
          f"docs/figures/module_08/angstrom_mean_profile{tag}.png")


if __name__ == "__main__":
    main()
