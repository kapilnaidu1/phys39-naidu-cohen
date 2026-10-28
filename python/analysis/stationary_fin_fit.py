#!/usr/bin/env python3
"""
Phys 39 Module 7, Part 3. Stationary-fin profile: finite-length and
semi-infinite fits. Naidu / Cohen

    python3 python/analysis/stationary_fin_fit.py data/module_08/rod_run_....csv \
        --length-mm L --troom T  [--t0 S --t1 S] [--radius-mm R] \
        [--offsets data/module_08/calibration_....csv] [--include-base --base-x-mm 0]

MODEL. With theta = T - T_room, the stationary rod equation is
    d2theta/dx2 = m^2 theta,    m^2 = hP/(kA)
and the two profiles fitted are
    finite, insulated tip:  theta(x) = theta0 cosh(m(L - x)) / cosh(mL)
    semi-infinite:          theta(x) = theta0 exp(-m x)
x is measured from the origin in data/module_08/sensor_map.csv, which the
course defines as rod thermistor R1 in the first rod hole (x = 0); L is the
rod length measured from that hole to the tip. R1's reading is the boundary
condition theta(0); the TEC thermistor (base) is only the controlled variable.

DATA. Each sensor is averaged over the steady window (default: the last
300 s). The script prints each channel's drift over that window so the
steady-state criterion can be stated and checked. Point uncertainty combines
  - the standard error of the mean (allowing for correlated readings),
  - the calibration uncertainty (--cal-unc, or the SEM column of --offsets),
  - the position uncertainty, propagated through the local slope m*theta.

RESULTS. m and 1/m with one-sigma uncertainties for both models, the shift
in m when the finite end is ignored compared with the fit uncertainty, both
residual sets, mL, the finite-length error eps_T(x) at every sensor, and,
if --radius-mm is given, the transverse Biot number from the fitted m:
    Bi_perp = h R / (2k) = (m R)^2 / 4      because m^2 = hP/(kA) = 2h/(kR)
A steady profile fixes only the ratio h/k (through m); it cannot give h and
k separately. That needs the periodic (Angstrom) experiment of Module 8.

OUTPUT
    data/module_08/fin_<run>.txt, data/module_08/fin_profile_<run>.csv
    docs/figures/module_08/fin_<run>.png
"""

import argparse
import io
import os
from contextlib import redirect_stdout

import numpy as np
from scipy.optimize import curve_fit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import rod_data as rd


def theta_finite(x, theta0, m, L):
    return theta0 * np.cosh(m * (L - x)) / np.cosh(m * L)


def theta_semi(x, theta0, m):
    return theta0 * np.exp(-m * x)


def fit(model, x, y, sy, p0):
    p, cov = curve_fit(model, x, y, p0=p0, sigma=sy, absolute_sigma=True,
                       maxfev=20000)
    res = y - model(x, *p)
    chi2 = float(((res / sy) ** 2).sum())
    return p, np.sqrt(np.diag(cov)), res, chi2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--length-mm", type=float, required=True,
                    help="rod length from the sensor-map origin to the tip")
    ap.add_argument("--troom", type=float, required=True,
                    help="room temperature T_room in C (state how it was measured)")
    ap.add_argument("--t0", type=float)
    ap.add_argument("--t1", type=float)
    ap.add_argument("--radius-mm", type=float)
    ap.add_argument("--offsets")
    ap.add_argument("--cal-unc", type=float, default=0.0,
                    help="calibration uncertainty per channel, C")
    ap.add_argument("--include-base", action="store_true")
    ap.add_argument("--base-x-mm", type=float, default=0.0)
    ap.add_argument("--sensor-map")
    a = ap.parse_args()

    cols, channels = rd.load_run(a.run)
    offsets = rd.load_offsets(a.offsets) if a.offsets else None
    cal_sem = {}
    if a.offsets:
        import csv
        with open(a.offsets, newline="") as fh:
            cal_sem = {r["channel"]: float(r["sem_C"]) for r in csv.DictReader(fh)}
    series = rd.channel_series(cols, channels, offsets)
    positions = rd.load_sensor_map(a.sensor_map)
    if a.include_base:
        positions["base"] = (a.base_x_mm / 1000.0, 0.0)
    t = cols["time_s"]
    t1 = a.t1 if a.t1 is not None else t[-1]
    t0 = a.t0 if a.t0 is not None else t1 - 300.0
    m_win = rd.window(t, t0, t1)
    L = a.length_mm / 1000.0
    stem = os.path.splitext(os.path.basename(a.run))[0]

    names = [n for n in series if n in positions and (n != "base" or a.include_base)]
    if len(names) < 3:
        raise SystemExit("Need positions for at least 3 channels in the sensor map.")
    x = np.array([positions[n][0] for n in names])
    dx = np.array([np.nan_to_num(positions[n][1]) for n in names])
    stats = [rd.mean_and_sem(series[n][m_win], t[m_win]) for n in names]
    y = np.array([s[0] for s in stats]) - a.troom
    sem = np.array([s[2] for s in stats])
    cal = np.array([np.hypot(a.cal_unc, cal_sem.get(n, 0.0)) for n in names])
    drift = [np.polyfit(t[m_win], series[n][m_win], 1)[0] * 60.0 for n in names]
    order = np.argsort(x)
    x, dx, y, sem, cal = x[order], dx[order], y[order], sem[order], cal[order]
    names = [names[i] for i in order]
    drift = [drift[i] for i in order]

    # first pass without the position term, then add it through the slope
    s0 = np.sqrt(sem ** 2 + cal ** 2)
    s0 = np.where(s0 > 0, s0, 1e-3)
    m_guess = max(np.log(y[0] / y[-1]) / (x[-1] - x[0]), 1.0) if y[-1] > 0 else 5.0
    pf, *_ = fit(lambda xx, th, mm: theta_finite(xx, th, mm, L), x, y, s0,
                 (y[0], m_guess))
    sy = np.sqrt(s0 ** 2 + (pf[1] * y * dx) ** 2)

    fin = lambda xx, th, mm: theta_finite(xx, th, mm, L)
    pf, ef, rf, chif = fit(fin, x, y, sy, pf)
    ps, es, rs, chis = fit(theta_semi, x, y, sy, (pf[0], pf[1]))
    dof = len(x) - 2
    mf, sf = pf[1], ef[1]
    ms, ss = ps[1], es[1]
    eps = np.abs(fin(x, 1.0, mf) - theta_semi(x, 1.0, mf)) / fin(x, 1.0, mf)

    out = io.StringIO()
    with redirect_stdout(out):
        print(f"Run {a.run}; steady window {t0:.0f} to {t1:.0f} s "
              f"({t1 - t0:.0f} s); T_room = {a.troom:.2f} C; L = {L * 1000:.1f} mm")
        if offsets:
            print(f"Offsets subtracted: {a.offsets}")
        print(f"{'channel':>8} {'x (mm)':>7} {'theta (C)':>9} {'sigma':>6} "
              f"{'drift (C/min)':>13} {'eps_T':>7}")
        for i, n in enumerate(names):
            print(f"{n:>8} {x[i] * 1000:7.1f} {y[i]:9.3f} {sy[i]:6.3f} "
                  f"{drift[i]:+13.4f} {eps[i]:7.4f}")
        print(f"\nFinite, insulated tip: m = {mf:.3f} +/- {sf:.3f} 1/m, "
              f"1/m = {1000 / mf:.1f} +/- {1000 * sf / mf ** 2:.1f} mm, "
              f"theta0 = {pf[0]:.3f} C, chi2/dof = {chif:.2f}/{dof}")
        print(f"Semi-infinite:         m = {ms:.3f} +/- {ss:.3f} 1/m, "
              f"1/m = {1000 / ms:.1f} +/- {1000 * ss / ms ** 2:.1f} mm, "
              f"theta0 = {ps[0]:.3f} C, chi2/dof = {chis:.2f}/{dof}")
        print(f"Shift in m when the finite end is ignored: {ms - mf:+.3f} 1/m "
              f"= {(ms - mf) / sf:+.2f} sigma of the finite fit")
        print(f"mL = {mf * L:.3f}")
        ratio = y[-1] / y[0]
        print(f"Placement check (course Part 2): theta at the farthest sensor / "
              f"theta at x = 0 = {ratio:.3f}; needs <= 1/e = {1 / np.e:.3f}: "
              f"{'met' if 0 < ratio <= 1 / np.e else 'NOT met'}")
        if a.radius_mm:
            R = a.radius_mm / 1000.0
            bi = (mf * R) ** 2 / 4.0
            dbi = 2 * bi * sf / mf
            print(f"Bi_perp = (mR)^2/4 = {bi:.2e} +/- {dbi:.1e} "
                  f"(R = {a.radius_mm:.2f} mm)")
        print("m^2 = hP/(kA): the steady profile fixes h/k only, not h and k "
              "separately.")
    text = out.getvalue()
    print(text)

    os.makedirs(rd.FIG_DIR, exist_ok=True)
    with open(os.path.join(rd.DATA_DIR, f"fin_{stem}.txt"), "w") as fh:
        cmd = (f"python3 python/analysis/stationary_fin_fit.py {a.run} "
               f"--length-mm {a.length_mm:g} --troom {a.troom:g} --t0 {t0:.2f} "
               f"--t1 {t1:.2f}")
        if a.radius_mm:
            cmd += f" --radius-mm {a.radius_mm:g}"
        if a.offsets:
            cmd += f" --offsets {a.offsets}"
        if a.include_base:
            cmd += f" --include-base --base-x-mm {a.base_x_mm:g}"
        fh.write(cmd + "\n\n" + text)
    with open(os.path.join(rd.DATA_DIR, f"fin_profile_{stem}.csv"), "w") as fh:
        fh.write("channel,x_m,dx_m,theta_C,sigma_C,res_finite_C,res_semi_C,eps_T\n")
        for i, n in enumerate(names):
            fh.write(f"{n},{x[i]:.4f},{dx[i]:.4f},{y[i]:.4f},{sy[i]:.4f},"
                     f"{rf[i]:.4f},{rs[i]:.4f},{eps[i]:.5f}\n")

    fig, (ax, axr) = plt.subplots(2, 1, figsize=(8, 7),
                                  gridspec_kw={"height_ratios": [2.2, 1]},
                                  sharex=True)
    xx = np.linspace(0, L, 300)
    ax.errorbar(x * 1000, y, yerr=sy, xerr=dx * 1000, fmt="o", color="black",
                ms=5, capsize=3, label="measured, steady mean")
    ax.plot(xx * 1000, fin(xx, *pf), color="#1F4E79", lw=1.6,
            label=f"finite, insulated tip: m = {mf:.2f} ± {sf:.2f} m⁻¹")
    ax.plot(xx * 1000, theta_semi(xx, *ps), color="#C0392B", lw=1.4, ls="--",
            label=f"semi-infinite: m = {ms:.2f} ± {ss:.2f} m⁻¹")
    # course Part 2: placement is judged on a ln(theta) against x plot, and
    # the farthest sensor should sit at or below theta(0)/e
    ax.axhline(y[0] / np.e, color="#7f7f7f", lw=1.0, ls=":",
               label="θ(0)/e, placement target")
    ax.set_yscale("log")
    from matplotlib.ticker import FixedLocator, FormatStrFormatter, NullLocator
    lo, hi = ax.get_ylim()
    step = max(1, int(np.ceil((hi - lo) / 8)))
    ticks = [v for v in np.arange(1, 200, step) if lo <= v <= hi]
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_major_formatter(FormatStrFormatter("%g"))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_ylabel("θ = T − T_room (°C, log scale)")
    ax.grid(True, which="both", color="#E4E4E4")
    ax.legend(fontsize=8.5)
    ax.set_title("Stationary profile along the rod (ln θ against x)", fontsize=10)
    axr.axhline(0, color="#888888", lw=0.8)
    axr.errorbar(x * 1000 - 0.6, rf, yerr=sy, fmt="o", color="#1F4E79", ms=4,
                 capsize=2, label="finite")
    axr.errorbar(x * 1000 + 0.6, rs, yerr=sy, fmt="s", color="#C0392B", ms=4,
                 capsize=2, label="semi-infinite")
    axr.set_xlabel("Position x from the origin (mm)")
    axr.set_ylabel("Residual (°C)")
    axr.grid(True, color="#E4E4E4")
    axr.legend(fontsize=8)
    fig.tight_layout()
    path = os.path.join(rd.FIG_DIR, f"fin_{stem}.png")
    fig.savefig(path, dpi=180)
    print(f"Wrote {path}, and fin_{stem}.txt and fin_profile_{stem}.csv in {rd.DATA_DIR}")


if __name__ == "__main__":
    main()
