#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I: semi-infinite against finite-rod (insulated tip) fits of the Angstrom amplitudes and phases.  SAMMY copy.

    python3 python/sammy_module8_finite_rod.py [<analysis stamp> ...] [--out FILE]

Same model, point errors and error scaling as Kapil Naidu's python/analysis/angstrom_finite_fit.py, but with a small numpy
Levenberg-Marquardt instead of scipy. B and the unwrapped phase of T1..T5 are fitted jointly with one complex s = q + i q':

    semi-infinite:         theta ~ B0 exp(-s x)
    finite, insulated tip: theta ~ B0 cosh(s (L - x)) / cosh(s L)

L = distance from T1's hole to the rod top (rod_geometry.csv). The point errors combine the cycle-to-cycle scatter with the
position uncertainty (T1 defines x = 0); the parameter errors are scaled by sqrt(chi2/dof) when that exceeds 1.
kappa = w / (2 q q'), nu = kappa (q^2 - q'^2).

For every SAMMY run (default: the four analysed ones) and every period the per-sensor fits are rebuilt with the analysis script's
own functions, for the strict settled block and for the last five cycles (Kapil's rule). The finite-rod fit is also repeated
without T2 (model 'finite_noT2'; T2 reads high in every run). Writes
    data/module_08_sammy/finite_rod_fits.csv
"""

import argparse
import csv
import math
import os
import warnings

import numpy as np

import sammy_module8_angstrom_analysis as A

warnings.filterwarnings("ignore", category=RuntimeWarning)

STAMPS = ["20261110_164057", "20261116_090538", "20261116_111935_phase1_pi200s", "20261117_162612"]
OUT = os.path.join(A.DATA_DIR, "finite_rod_fits.csv")


def run_path(stamp):
    return os.path.join(A.DATA_DIR, f"sammy_angstrom_live_{stamp}.csv")


def _jac(resid, p, r):
    J = np.empty((r.size, p.size))
    for k in range(p.size):
        d = np.zeros(p.size)
        d[k] = 1e-7 * max(1.0, abs(p[k]))
        J[:, k] = (resid(p + d) - r) / d[k]
    return J


def _lm(resid, p0, iters=300):
    p = np.array(p0, float)
    r = resid(p)
    lam = 1e-3
    for _ in range(iters):
        J = _jac(resid, p, r)
        H, g = J.T @ J, J.T @ r
        improved = False
        for _ in range(60):
            step = np.linalg.solve(H + lam * np.diag(np.diag(H)), -g)
            rn = resid(p + step)
            if rn @ rn < r @ r:
                done = (r @ r - rn @ rn) <= 1e-13 * (r @ r) + 1e-300
                p, r, lam, improved = p + step, rn, max(lam * 0.3, 1e-12), True
                break
            lam *= 10
        if not improved or done:
            break
    return p, r, _jac(resid, p, r)


def joint_fit(x, dx, B, sB, phi, sphi, w, L, finite):
    """One model, five sensors: ln B and the unwrapped phase against position, one complex s."""
    def model(p):
        s = p[2] + 1j * p[3]
        f = np.cosh(s * (L - x)) / np.cosh(s * L) if finite else np.exp(-s * x)
        return p[0] + np.log(np.abs(f)), p[1] + np.unwrap(np.angle(f))

    def resid(p):
        a, b = model(p)
        s_l = np.sqrt((sB / B) ** 2 + (p[2] * dx) ** 2 + 1e-8)
        s_p = np.sqrt(sphi ** 2 + (p[3] * dx) ** 2 + 1e-8)
        return np.r_[(np.log(B) - a) / s_l, (phi - b) / s_p]

    p0 = [np.log(B[0]), phi[0], -np.polyfit(x, np.log(B), 1)[0], -np.polyfit(x, phi, 1)[0]]
    p, r, J = _lm(resid, p0)
    a_fit, b_fit = model(p)
    chi2 = float(r @ r)
    dof = r.size - 4
    cov = np.linalg.inv(J.T @ J) * max(chi2 / dof, 1.0)
    q, qp = p[2], p[3]
    sq, sqp = math.sqrt(cov[2, 2]), math.sqrt(cov[3, 3])
    kap = w / (2 * q * qp)
    skap = kap * math.hypot(sq / q, sqp / qp)
    nu = kap * (q * q - qp * qp)
    snu = math.sqrt((nu / kap * skap) ** 2 + (kap * 2 * q * sq) ** 2 + (kap * 2 * qp * sqp) ** 2)
    return dict(q=q, sq=sq, qp=qp, sqp=sqp, kappa=kap, skappa=skap, nu=nu, snu=snu, chi2=chi2, dof=dof,
                dlnB=np.log(B) - a_fit, dphi=phi - b_fit)


def fit_fits(fits, w, x, dx, L, drop=(), models=("semi", "finite")):
    """The models from the per-sensor fits of A.analyse_block; drop = sensor indices (0 = T1) left out."""
    B = np.array([fits[c]["B"] for c in A.ROD])
    sB = np.array([fits[c]["sB"] for c in A.ROD])
    phi = np.array([fits[c]["phi"] for c in A.ROD])
    sphi = np.array([fits[c]["sphi"] for c in A.ROD])
    phi_u = phi[0] + np.unwrap(phi - phi[0])
    k = [i for i in range(5) if i not in drop]
    return {m: joint_fit(x[k], dx[k], B[k], sB[k], phi_u[k], sphi[k], w, L, m == "finite") for m in models}


def fit_blocks(t, data, info, cyc, blocks, x, dx, L):
    """{name: {'cycles': [...], 'semi': {...}, 'finite': {...}, 'finite_noT2': {...}}} for the named blocks of cycle indices."""
    out = {}
    for name, block in blocks.items():
        blk = A.analyse_block(t, data, info, cyc, block)
        out[name] = dict(cycles=block, **fit_fits(blk["fits"], blk["w"], x, dx, L))
        out[name]["finite_noT2"] = fit_fits(blk["fits"], blk["w"], x, dx, L, drop=(1,), models=("finite",))["finite"]
    return out


def run_blocks(stamp):
    """Per period of one SAMMY run: strict settled block and last five cycles."""
    path = run_path(stamp)
    cols = A.load(path)
    t = cols["t"]
    _, data, _ = A.prepare(cols, A.load_offsets(A.OFFSETS), A.load_mask(path.replace(".csv", "_mask.csv")))
    x, dx = A.load_positions(A.SENSOR_MAP)
    L = A.load_geometry(A.GEOMETRY)["L"]
    res = {}
    for info in [s for s in A.find_steps(cols) if s["tb"] > 0]:
        cyc = A.cycle_fits(t, data, info)
        block, _, _, _ = A.settled_block(cyc, info["ncyc"])
        blocks = {"strict": block, "last5": list(range(info["ncyc"] - min(5, info["ncyc"]), info["ncyc"]))}
        res[int(round(info["period"]))] = dict(ncyc=info["ncyc"], **fit_blocks(t, data, info, cyc, blocks, x, dx, L))
    return res


def compute(stamps=STAMPS):
    return {s: run_blocks(s) for s in stamps}


def span(cycles):
    return f"{cycles[0] + 1}-{cycles[-1] + 1}"


def write_csv(path, results):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["stamp", "period_s", "block", "cycles", "model", "q_1_m", "sq_1_m", "qprime_1_m", "sqprime_1_m", "kappa_m2_s",
                    "skappa_m2_s", "nu_1_s", "snu_1_s", "chi2", "dof"])
        for stamp, per in results.items():
            for P, rec in sorted(per.items()):
                for name in ("strict", "last5"):
                    for model in ("semi", "finite", "finite_noT2"):
                        r = rec[name][model]
                        w.writerow([stamp, P, name, span(rec[name]["cycles"]), model, f"{r['q']:.3f}", f"{r['sq']:.3f}",
                                    f"{r['qp']:.3f}", f"{r['sqp']:.3f}", f"{r['kappa']:.4e}", f"{r['skappa']:.2e}", f"{r['nu']:.3e}",
                                    f"{r['snu']:.2e}", f"{r['chi2']:.2f}", r["dof"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stamps", nargs="*", help="run or slice stamps (default: the four analysed runs)")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    results = compute(a.stamps or STAMPS)
    write_csv(a.out, results)
    print(f"{'run':32s}{'P':>5s} {'block':>6s} {'cycles':>7s} {'kappa semi':>14s} {'kappa finite':>14s} {'finite/semi':>12s}")
    for stamp, per in results.items():
        for P, rec in sorted(per.items()):
            for name in ("strict", "last5"):
                s, f = rec[name]["semi"], rec[name]["finite"]
                print(f"{stamp:32s}{P:5d} {name:>6s} {span(rec[name]['cycles']):>7s} "
                      f"{s['kappa'] * 1e5:8.2f}±{s['skappa'] * 1e5:4.2f} {f['kappa'] * 1e5:8.2f}±{f['skappa'] * 1e5:4.2f} "
                      f"{f['kappa'] / s['kappa']:12.3f}")
    print("wrote", os.path.relpath(a.out, A.REPO))


if __name__ == "__main__":
    main()
