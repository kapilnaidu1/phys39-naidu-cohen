#!/usr/bin/env python3
"""
Phys 39 Module 8. Semi-infinite against finite-rod fits of the Angstrom
amplitudes and phases. Naidu / Cohen

    python3 python/analysis/angstrom_finite_fit.py \
        data/module_08/angstrom_fit_<run>_PI_100s.csv data/module_08/angstrom_fit_<run>_PI_480s.csv \
        [--length-mm 281.9] [--dx-mm 1]

Input: the per-sensor CSV files written by angstrom_fit.py (B_i, phi_i and
their cycle-to-cycle errors). For each file, B and the unwrapped phase of
T1..T5 are fitted jointly with one complex s = q + i q':

    semi-infinite:        theta ~ B0 exp(-s x)
    finite, insulated tip: theta ~ B0 cosh(s (L - x)) / cosh(s L)

(L = distance from T1's hole to the rod top.) Point errors combine the
cycle-to-cycle scatter with the position uncertainty dx (T1 defines x = 0,
so it has none). Parameter errors are scaled by sqrt(chi2/dof) when that
exceeds 1. kappa = w / (2 q q'), nu = kappa (q^2 - q'^2).

Output: data/module_08/angstrom_finite_<run>.txt
"""

import argparse
import csv
import io
import os
import re
from contextlib import redirect_stdout

import numpy as np
from scipy.optimize import least_squares

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROD = ["T1_C", "T2_C", "T3_C", "T4_C", "T5_C"]


def load(path):
    with open(path, newline="") as fh:
        rows = {r["channel"]: r for r in csv.DictReader(fh)}
    g = lambda k: np.array([float(rows[c][k]) for c in ROD])
    phi = g("phi_rad")
    return g("x_m"), g("B_C"), g("sB_C"), phi[0] + np.unwrap(phi - phi[0]), g("sphi_rad")


def fit(x, B, sB, phi, sphi, w, L, dx, finite):
    def model(p):
        s = p[2] + 1j * p[3]
        f = np.cosh(s * (L - x)) / np.cosh(s * L) if finite else np.exp(-s * x)
        return p[0] + np.log(np.abs(f)), p[1] + np.unwrap(np.angle(f))

    def resid(p):
        a, b = model(p)
        s_l = np.sqrt((sB / B) ** 2 + (p[2] * dx) ** 2 + 1e-8)
        s_p = np.sqrt(sphi ** 2 + (p[3] * dx) ** 2 + 1e-8)
        return np.r_[(np.log(B) - a) / s_l, (phi - b) / s_p]

    r = least_squares(resid, [np.log(B[0]), phi[0], 10.0, 10.0])
    chi2 = float(np.sum(r.fun ** 2))
    dof = len(r.fun) - 4
    cov = np.linalg.inv(r.jac.T @ r.jac) * max(chi2 / dof, 1.0)
    q, qp = r.x[2], r.x[3]
    sq, sqp = np.sqrt(cov[2, 2]), np.sqrt(cov[3, 3])
    kap = w / (2 * q * qp)
    skap = kap * np.hypot(sq / q, sqp / qp)
    nu = kap * (q * q - qp * qp)
    snu = np.sqrt((nu / kap * skap) ** 2 + (kap * 2 * q * sq) ** 2 + (kap * 2 * qp * sqp) ** 2)
    return q, sq, qp, sqp, kap, skap, nu, snu, chi2, dof


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fits", nargs="+")
    ap.add_argument("--length-mm", type=float, default=281.9)
    ap.add_argument("--dx-mm", type=float, default=1.0)
    a = ap.parse_args()
    L = a.length_mm / 1000.0
    dx = np.array([0.0] + [a.dx_mm / 1000.0] * 4)
    out = io.StringIO()
    with redirect_stdout(out):
        print(f"L = {a.length_mm:g} mm (T1 hole to rod top), position uncertainty "
              f"{a.dx_mm:g} mm for T2..T5")
        print(f"{'file':>48} {'model':>13} {'q (1/m)':>12} {'q_prime (1/m)':>14} "
              f"{'kappa (1e-5 m2/s)':>18} {'nu (1e-3 1/s)':>14} {'chi2/dof':>9}")
        for path in a.fits:
            period = float(re.search(r"_(\d+(?:\.\d+)?)s\.csv$", path).group(1))
            w = 2 * np.pi / period
            data = load(path)
            for finite in (False, True):
                q, sq, qp, sqp, k, sk, nu, snu, chi2, dof = fit(*data, w, L, dx, finite)
                print(f"{os.path.basename(path):>48} {('finite rod' if finite else 'semi-infinite'):>13} "
                      f"{q:6.2f}±{sq:4.2f} {qp:8.2f}±{sqp:4.2f} {k * 1e5:11.2f}±{sk * 1e5:4.2f} "
                      f"{nu * 1e3:8.2f}±{snu * 1e3:4.2f} {chi2:5.1f}/{dof}")
    text = out.getvalue()
    print(text)
    run = re.sub(r"^angstrom_fit_|_PI_.*$", "", os.path.basename(a.fits[0]))
    path = os.path.join(REPO, "data", "module_08", f"angstrom_finite_{run}.txt")
    with open(path, "w") as fh:
        fh.write("python3 python/analysis/angstrom_finite_fit.py " + " ".join(a.fits)
                 + f" --length-mm {a.length_mm:g} --dx-mm {a.dx_mm:g}\n\n" + text)
    print(f"Wrote {os.path.relpath(path, REPO)}")


if __name__ == "__main__":
    main()
