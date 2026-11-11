#!/usr/bin/env python3
"""
Phys 39 Module 8, Part II. From the Angstrom fits to k and h, with a
Monte Carlo uncertainty that includes the sensor positions. Naidu / Cohen

    python3 python/analysis/part2_parameters.py [--draws 2000] [--seed 1]

INPUT
  The per-sensor CSV files written by angstrom_fit.py for the retained
  windows (listed in WINDOWS below), data/module_08/rod_geometry.csv and
  data/module_08/sensor_map.csv.

METHOD
  For each window, B_i and the unwrapped phase phi_i of T1..T5 are fitted
  with the finite insulated-tip rod (as in angstrom_finite_fit.py):
      theta(x) ~ B0 cosh(s (L - x)) / cosh(s L),   s = q + i q'
  kappa = w / (2 q q'),  nu = kappa (q^2 - q'^2),
  k = kappa rho c,       h = nu rho c (A/P) = nu rho c R / 2.
  Dimensions: [w/(q q')] = s^-1 / m^-2 = m^2/s; [nu] = s^-1;
  [kappa rho c] = m^2/s * kg/m^3 * J/(kg K) = W/(m K);
  [nu rho c R] = s^-1 * kg/m^3 * J/(kg K) * m = W/(m^2 K).

  Monte Carlo: each draw perturbs T2..T5 positions (sd 1 mm each, T1 is
  x = 0 by definition), L (sd 1.3 mm), D (sd 0.006 mm), B_i and phi_i
  (their cycle-to-cycle errors, scaled up by sqrt(chi2/dof) of the nominal
  fit when that exceeds 1, so excess scatter is not hidden), and refits.
  rho and c carry the fractional uncertainties given by --rho-rel and
  --c-rel (default 0: no cited uncertainty yet; see the packet).

OUTPUT
  data/module_08/part2_parameters.csv      one row per window
  data/module_08/part2_parameter_table.md  the parameter table
  printed summary (also data/module_08/part2_parameters.txt)
"""

import argparse
import csv
import io
import os
from contextlib import redirect_stdout

import numpy as np
from scipy.optimize import least_squares

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D8 = os.path.join(REPO, "data", "module_08")
ROD = ["T1_C", "T2_C", "T3_C", "T4_C", "T5_C"]

# label, fit file (in data/module_08), settled cycles kept, room T (C)
WINDOWS = [
    ("2 Nov 100 s", "angstrom_fit_angstrom_live_20261102_094506_PI_100s.csv", 5, 22.53),
    ("2 Nov 480 s", "angstrom_fit_angstrom_live_20261102_094506_PI_480s.csv", 5, 22.53),
    ("4 Nov 180 s", "angstrom_fit_angstrom_live_20261104_092527_PI_180s.csv", 5, 27.10),
    ("4 Nov 240 s", "angstrom_fit_angstrom_live_20261104_092527_PI_240s.csv", 5, 27.10),
    ("4 Nov 300 s", "angstrom_fit_angstrom_live_20261104_110306_PI_300s.csv", 6, 27.10),
    ("10 Nov 480 s", "angstrom_fit_sammy_angstrom_live_20261110_164057_PI_480s.csv", 3, 24.28),
    ("10 Nov 240 s", "angstrom_fit_sammy_angstrom_live_20261110_164057_PI_240s.csv", 6, 24.28),
    ("10 Nov 100 s", "angstrom_fit_sammy_angstrom_live_20261110_164057_PI_100s.csv", 3, 24.28),
    ("11 Nov 480 s", "angstrom_fit_angstrom_live_20261111_094735_PI_480s.csv", 6, 24.37),
]

# Literature values used throughout this repository for 6061-T6.
RHO, C_P, K_LIT = 2700.0, 896.0, 167.0
K_LIT_RANGE = (166.0, 172.0)      # 0 to 100 C, as cited in A4 (Lienhard Table A.1)
M7_M, M7_SM = 4.117, 0.07         # Module 7 stationary fin, 1/m


def geometry():
    g = {}
    with open(os.path.join(D8, "rod_geometry.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["quantity"] not in ("diameter_mean", "analysis_length_L"):
                continue
            g[r["quantity"]] = (float(r["value"]), float(r["uncertainty"] or 0))
    return g["diameter_mean"], g["analysis_length_L"]


def load(path):
    with open(path, newline="") as fh:
        rows = {r["channel"]: r for r in csv.DictReader(fh)}
    g = lambda k: np.array([float(rows[c][k]) for c in ROD])
    phi = g("phi_rad")
    phi = phi[0] + np.unwrap(phi - phi[0])
    return g("x_m"), g("B_C"), g("sB_C"), phi, g("sphi_rad")


def period_of(name):
    return float(name.rsplit("_", 1)[1].rstrip("s.csv"))


def model(p, x, L):
    s = p[2] + 1j * p[3]
    f = np.cosh(s * (L - x)) / np.cosh(s * L)
    return p[0] + np.log(np.abs(f)), p[1] + np.unwrap(np.angle(f))


def fit(x, B, sB, phi, sphi, L, dx=0.0, p0=None):
    def resid(p):
        a, b = model(p, x, L)
        s_l = np.sqrt((sB / B) ** 2 + (p[2] * dx) ** 2 + 1e-10)
        s_p = np.sqrt(sphi ** 2 + (p[3] * dx) ** 2 + 1e-10)
        return np.r_[(np.log(B) - a) / s_l, (phi - b) / s_p]
    r = least_squares(resid, p0 if p0 is not None else [np.log(B[0]), phi[0], 10.0, 10.0])
    return r.x, float(np.sum(r.fun ** 2)), len(r.fun) - 4


def derived(q, qp, w, R, rho, c):
    kap = w / (2 * q * qp)
    nu = kap * (q * q - qp * qp)
    return kap, nu, kap * rho * c, nu * rho * c * R / 2


def wmean(v, s):
    w = 1 / s ** 2
    m = np.sum(w * v) / np.sum(w)
    return m, np.sqrt(1 / np.sum(w)), float(np.sum(w * (v - m) ** 2)), len(v) - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--rho-rel", type=float, default=0.0)
    ap.add_argument("--c-rel", type=float, default=0.0)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    (D, sD), (Lmm, sL) = geometry()
    D, sD, L, sL = D / 1000, sD / 1000, Lmm / 1000, sL / 1000
    R = D / 2
    dxp = 1e-3
    dx_nom = np.array([0.0, dxp, dxp, dxp, dxp])

    data, rows = [], []
    for label, fname, ncyc, troom in WINDOWS:
        x, B, sB, phi, sphi = load(os.path.join(D8, fname))
        P = period_of(fname)
        w = 2 * np.pi / P
        p, chi2, dof = fit(x, B, sB, phi, sphi, L)                  # measurement errors only
        pq, chi2q, _ = fit(x, B, sB, phi, sphi, L, dx=dx_nom)        # as angstrom_finite_fit.py
        scale = max(1.0, np.sqrt(chi2 / dof))
        kap, nu, k, h = derived(p[2], p[3], w, R, RHO, C_P)
        data.append((x, B, sB, phi, sphi, w, p, scale))
        rows.append(dict(window=label, file=fname, period_s=P, omega=w, cycles=ncyc,
                         room_C=troom, q=p[2], qp=p[3], kappa=kap, nu=nu, k=k, h=h,
                         nu_over_kappa=nu / kap, chi2=chi2, dof=dof, err_scale=scale,
                         kappa_dx_quadrature=derived(pq[2], pq[3], w, R, RHO, C_P)[0],
                         chi2_dx_quadrature=chi2q))

    keys = ["q", "qp", "kappa", "nu", "k", "h", "nu_over_kappa"]
    n = len(WINDOWS)
    stat = np.zeros((a.draws, n, len(keys)))     # measurement noise only
    tot = np.zeros((a.draws, n, len(keys)))      # plus one common geometry/material draw
    for i in range(a.draws):
        shift = np.r_[0.0, rng.normal(0, dxp, 4)]  # same holes, same map on every day
        Ld = L + rng.normal(0, sL)
        Rd = (D + rng.normal(0, sD)) / 2
        rho = RHO * (1 + rng.normal(0, a.rho_rel)) if a.rho_rel else RHO
        c = C_P * (1 + rng.normal(0, a.c_rel)) if a.c_rel else C_P
        for j, (x, B, sB, phi, sphi, w, p, scale) in enumerate(data):
            Bd = B * np.exp(rng.normal(0, scale * sB / B))
            phid = phi + rng.normal(0, scale * sphi)
            ps, _, _ = fit(x, Bd, sB, phid, sphi, L, p0=p)
            kk = derived(ps[2], ps[3], w, R, RHO, C_P)
            stat[i, j] = (ps[2], ps[3]) + kk + (kk[1] / kk[0],)
            pt, _, _ = fit(x + shift, Bd, sB, phid, sphi, Ld, p0=p)
            kt = derived(pt[2], pt[3], w, Rd, rho, c)
            tot[i, j] = (pt[2], pt[3]) + kt + (kt[1] / kt[0],)
    sd_stat = stat.std(axis=0)
    sd_tot = tot.std(axis=0)
    for j, r in enumerate(rows):
        for m, key in enumerate(keys):
            r["s_" + key] = sd_stat[j, m]
            r["s_" + key + "_total"] = sd_tot[j, m]

    # combined values: weights from the statistical errors; the total error of
    # the combination comes from repeating the weighted mean in every draw
    comb = {}
    for tag, sel in (("all", np.ones(n, bool)),
                     ("ge5", np.array([r["cycles"] >= 5 for r in rows]))):
        for m, key in enumerate(keys):
            wts = 1 / sd_stat[sel, m] ** 2
            v = np.array([r[key] for r in rows])[sel]
            mean = np.sum(wts * v) / np.sum(wts)
            s_stat = np.sqrt(1 / np.sum(wts))
            chi2 = float(np.sum(wts * (v - mean) ** 2))
            per_draw = (tot[:, sel, m] * wts).sum(axis=1) / wts.sum()
            comb[(tag, key)] = (mean, s_stat, per_draw.std(), chi2, int(sel.sum()) - 1)

    out = io.StringIO()
    with redirect_stdout(out):
        report(rows, comb, D, sD, L, sL, a)
    text = out.getvalue()
    print(text, end="")
    with open(os.path.join(D8, "part2_parameters.txt"), "w") as fh:
        fh.write("python3 python/analysis/part2_parameters.py " +
                 f"--draws {a.draws} --seed {a.seed}\n\n" + text)
    cols = list(rows[0].keys())
    with open(os.path.join(D8, "part2_parameters.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=cols)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: (f"{v:.6g}" if isinstance(v, float) else v) for k, v in r.items()})
    write_table(rows, comb, D, sD, L, sL, a)


def report(rows, comb, D, sD, L, sL, a):
    R = D / 2
    print("Module 8 Part II parameters: finite insulated-tip rod, Monte Carlo errors"
          f" ({a.draws} draws, seed {a.seed})")
    print(f"D = {D*1e3:.3f} +/- {sD*1e3:.3f} mm, R = {R*1e3:.4f} mm, A/P = R/2 = {R/2*1e3:.4f} mm;"
          f" L = {L*1e3:.1f} +/- {sL*1e3:.1f} mm; T2..T5 positions +/-1 mm")
    print(f"rho = {RHO:.0f} kg/m3 (rel. err {a.rho_rel:g}), c = {C_P:.0f} J/(kg K)"
          f" (rel. err {a.c_rel:g}); literature k = {K_LIT:.0f} W/(m K)")
    print("stat = measurement scatter only (scaled by sqrt(chi2/dof) when > 1);"
          " tot = stat plus one common draw of positions, L, D (and rho, c) per iteration.\n")
    print(f"{'window':<13} {'cyc':>3} {'q (1/m)':>11} {'q_p (1/m)':>11} {'kappa 1e-5 stat/tot':>21}"
          f" {'nu 1e-3/s stat':>15} {'k W/mK stat/tot':>16} {'h W/m2K stat':>13} {'chi2/dof':>8}")
    for r in rows:
        print(f"{r['window']:<13} {r['cycles']:>3} {r['q']:6.2f}+/-{r['s_q']:.2f}"
              f" {r['qp']:6.2f}+/-{r['s_qp']:.2f} {r['kappa']*1e5:6.2f} {r['s_kappa']*1e5:.2f}/{r['s_kappa_total']*1e5:.2f}"
              f"     {r['nu']*1e3:5.2f}+/-{r['s_nu']*1e3:.2f} {r['k']:6.0f} {r['s_k']:.0f}/{r['s_k_total']:.0f}"
              f"     {r['h']:5.1f}+/-{r['s_h']:.1f} {r['chi2']:5.1f}/{r['dof']}")
    print("\n(kappa with the 1 mm position error added in quadrature instead, as in"
          " angstrom_finite_fit.py: " + ", ".join(f"{r['kappa_dx_quadrature']*1e5:.2f}" for r in rows) + ")\n")
    for tag, name in (("all", "all nine windows"), ("ge5", "the six windows with >= 5 settled cycles")):
        print(f"Weighted means over {name} (weights from stat errors):")
        for key, scale, unit in (("kappa", 1e5, "1e-5 m2/s"), ("nu", 1e3, "1e-3 1/s"),
                                 ("k", 1, "W/(m K)"), ("h", 1, "W/(m2 K)"),
                                 ("nu_over_kappa", 1, "1/m2")):
            m, ss, st, chi2, dof = comb[(tag, key)]
            print(f"  {key:<14} {m*scale:8.3f}  stat {ss*scale:.3f}  total {st*scale:.3f} {unit:<10}"
                  f" chi2 {chi2:.1f}/{dof}")
        print()
    print("By period (weighted over days, stat errors):")
    for P in sorted({r["period_s"] for r in rows}):
        rs = [r for r in rows if r["period_s"] == P]
        for key, scale, fmt in (("kappa", 1e5, "kappa {:.2f} +/- {:.2f}"), ("k", 1, "k {:.0f} +/- {:.0f}"),
                                ("h", 1, "h {:.1f} +/- {:.1f}")):
            v = np.array([r[key] for r in rs]); s = np.array([r["s_" + key] for r in rs])
            m, e, _, _ = wmean(v, s)
            print(("  " if key == "kappa" else ", ") + (f"{P:5.0f} s: " if key == "kappa" else "")
                  + fmt.format(m * scale, e * scale), end="")
        print()
    print()
    k = comb[("all", "k")]
    print(f"k against literature {K_LIT:.0f} W/(m K) (range {K_LIT_RANGE[0]:.0f} to"
          f" {K_LIT_RANGE[1]:.0f} over 0 to 100 C): ratio {k[0]/K_LIT:.3f} ({100*(k[0]/K_LIT-1):+.0f} %),"
          f" {(k[0]-K_LIT_RANGE[1])/k[2]:.0f} total sigma above the top of the range")
    nk = comb[("all", "nu_over_kappa")]
    m_ang, s_m = np.sqrt(nk[0]), nk[2] / (2 * np.sqrt(nk[0]))
    print(f"m from nu/kappa: {m_ang:.2f} +/- {s_m:.2f} 1/m (m^2 = {nk[0]:.1f} +/- {nk[2]:.1f} 1/m2, total);"
          f" Module 7 stationary fin m = {M7_M} +/- {M7_SM} (m^2 = {M7_M**2:.1f} +/- {2*M7_M*M7_SM:.1f})")
    print(f"mL = {m_ang*L:.3f} +/- {s_m*L:.3f};  transverse Biot Bi = (nu/kappa) R^2 / 4 = {nk[0]*R*R/4:.2e}")
    print("Finite-length effect at T5 (x = 101.6 mm): |cosh(s(L-x))/cosh(sL) - exp(-sx)| / |cosh(s(L-x))/cosh(sL)|")
    for P in sorted({r["period_s"] for r in rows}):
        rr = [r for r in rows if r["period_s"] == P][0]
        s = rr["q"] + 1j * rr["qp"]
        x = 0.1016
        fin = np.cosh(s * (L - x)) / np.cosh(s * L)
        print(f"  {P:5.0f} s: {100*abs(fin - np.exp(-s*x))/abs(fin):.2f} %")
    fin = np.cosh(m_ang * (L - 0.1016)) / np.cosh(m_ang * L)
    print(f"  mean profile with m = {m_ang:.2f}: {100*abs(fin - np.exp(-m_ang*0.1016))/fin:.1f} %")
    print()
    convection(D, L, comb[("all", "h")])


# Air at 300 K, Incropera, DeWitt, Bergman and Lavine, Fundamentals of Heat
# and Mass Transfer, Table A.4.
AIR_NU, AIR_K, AIR_ALPHA, AIR_PR = 15.89e-6, 26.3e-3, 22.5e-6, 0.707
SIGMA = 5.670e-8


def convection(D, L, hmeas):
    """Natural-convection scale from the Churchill and Chu correlations."""
    g, Tf = 9.81, 300.0
    print("Natural-convection scale (air properties at 300 K, Incropera Table A.4):")
    print(f"  measured h = {hmeas[0]:.1f} +/- {hmeas[2]:.1f} W/(m2 K) (total)")
    for dT in (5.0, 10.0, 15.0):
        RaD = g / Tf * dT * D ** 3 / (AIR_NU * AIR_ALPHA)
        NuD = (0.60 + 0.387 * RaD ** (1 / 6) / (1 + (0.559 / AIR_PR) ** (9 / 16)) ** (8 / 27)) ** 2
        hD = NuD * AIR_K / D
        RaL = g / Tf * dT * L ** 3 / (AIR_NU * AIR_ALPHA)
        NuL = (0.825 + 0.387 * RaL ** (1 / 6) / (1 + (0.492 / AIR_PR) ** (9 / 16)) ** (8 / 27)) ** 2
        hL = NuL * AIR_K / L
        GrL = RaL / AIR_PR
        thin = D / L < 35 / GrL ** 0.25
        print(f"  dT = {dT:4.1f} K: horizontal cylinder (Churchill-Chu, Ra_D = {RaD:.0f}) h = {hD:.1f};"
              f" vertical plate of height L (Churchill-Chu, Ra_L = {RaL:.2e}) h = {hL:.1f}"
              f"{' (D/L below 35/Gr^0.25: plate formula not valid, curvature raises h)' if thin else ''}")
    print("  For h proportional to dT^(1/4), the small-signal coefficient seen by the oscillation is"
          " d(h dT)/d(dT) = 1.25 h.")
    print(f"  Linearised radiation 4 eps sigma T^3 at 300 K = {4*SIGMA*300**3:.1f} eps W/(m2 K)"
          " (emissivity of this rod not measured).")


def write_table(rows, comb, D, sD, L, sL, a):
    R = D / 2
    A, Pm = np.pi * R * R, np.pi * D
    f = lambda key, s=1: comb[("all", key)]
    lines = [
        "| Quantity | Value | Uncertainty | Unit | Source |",
        "|---|---|---|---|---|",
        "| Forcing periods | 100, 180, 240, 300, 480 | exact (Arduino clock) | s | run files, `angstrom_tec.ino` |",
        "| ω = 2π/period | 0.0628, 0.0349, 0.0262, 0.0209, 0.0131 | exact | rad/s | from the period |",
        "| Sensor positions T1 to T5 | 0, 25.4, 50.8, 76.2, 101.6 | T1 0 (defines x = 0); T2 to T5 ±1 each | mm | tape 28 Oct, calipers 10 Nov; `sensor_map.csv` |",
        f"| Diameter D | {D*1e3:.3f} | {sD*1e3:.3f} | mm | calipers, 3 readings; `rod_geometry.csv` |",
        f"| Radius R = D/2 | {R*1e3:.3f} | {sD/2*1e3:.3f} | mm | from D |",
        f"| Area A = πR² | {A*1e6:.2f} | {2*A*sD/D*1e6:.2f} | mm² | from D |",
        f"| Perimeter P = πD | {Pm*1e3:.2f} | {np.pi*sD*1e3:.2f} | mm | from D |",
        f"| A/P = R/2 | {R/2*1e3:.4f} | {sD/4*1e3:.4f} | mm | from D |",
        f"| Analysis length L (T1 hole to tip) | {L*1e3:.1f} | {sL*1e3:.1f} | mm | ruler; `rod_geometry.csv` |",
    ]
    for r in rows:
        lines.append(f"| q, q′: {r['window']} ({r['cycles']} settled cycles) | {r['q']:.2f}, {r['qp']:.2f} |"
                     f" {r['s_q']:.2f}, {r['s_qp']:.2f} (stat) | 1/m | finite-rod fit of `{r['file']}` |")
    for key, label, sc, unit, src in (
            ("kappa", "κ = ω/(2qq′)", 1e5, "10⁻⁵ m²/s", "derived, weighted over 9 windows"),
            ("nu", "ν = κ(q² − q′²)", 1e3, "10⁻³ 1/s", "derived, weighted over 9 windows")):
        m, ss, st, chi2, dof = f(key)
        lines.append(f"| {label} | {m*sc:.2f} | {ss*sc:.2f} stat, {st*sc:.2f} total (χ² {chi2:.1f}/{dof}) | {unit} | {src} |")
    rho_u = f"{a.rho_rel*100:g} %" if a.rho_rel else "none cited yet"
    c_u = f"{a.c_rel*100:g} %" if a.c_rel else "none cited yet"
    lines += [
        f"| ρ (6061-T6) | {RHO:.0f} | {rho_u} | kg/m³ | handbook value used in A4 and A5; source to confirm |",
        f"| c (6061-T6) | {C_P:.0f} | {c_u} | J/(kg K) | handbook value used in A4 and A5; source to confirm |",
    ]
    for key, label, unit in (("k", "k = κρc", "W/(m K)"), ("h", "h = νρcA/P", "W/(m² K)")):
        m, ss, st, chi2, dof = f(key)
        prec = 0 if key == "k" else 1
        lines.append(f"| {label} | {m:.{prec}f} | {ss:.{prec}f} stat, {st:.{prec}f} total (χ² {chi2:.1f}/{dof}) | {unit} | derived |")
    lines.append(f"| k, literature (6061-T6) | {K_LIT:.0f} ({K_LIT_RANGE[0]:.0f} to {K_LIT_RANGE[1]:.0f} over 0 to 100 °C) | | W/(m K) | Lienhard, *A Heat Transfer Textbook*, Table A.1, as cited in A4 |")
    with open(os.path.join(D8, "part2_parameter_table.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
