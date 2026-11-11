#!/usr/bin/env python3
"""
Phys 39 Module 8, S18.3: zero-centered raw sinusoidal PWM (U0 = 0).  SAMMY copy.

    python3 python/sammy_module8_s183_analysis.py data/module_08_sammy/sammy_angstrom_live_20261111_122227.csv

Reads a run recorded in RAW mode (u = U sin(phase), no feedback) and writes
    data/module_08_sammy/s183_analysis_<stamp>/   tables (CSV) and s183_summary.json
    docs/figures/module_08_sammy/<stamp>_s183_*.png
    docs/sammy_module_08_guide/Sammy_Module_8_S18_3_Raw_PWM_Walkthrough.md   (step-by-step maths and results)

Method, in one paragraph. Every step (period P) is cut into whole cycles. After the first cycles (the start-up
transient, about 2.5 tau) the remaining whole cycles are fitted with a mean, three harmonics and a straight drift:
    T(t) = a + sum_k [ b_k cos(k w t) + c_k sin(k w t) ] + d (t - t_mid),    w = 2 pi / P.
The PWM is fitted the same way. Amplitude A_k = sqrt(b_k^2 + c_k^2); the phase lag of the temperature behind the PWM
is theta_u - theta_T for the fundamental. The one-lump model of Module 6,
    tau dT/dt = -(T - T_amb) + chi(u) u,    chi = chi_h for u > 0 and chi_c for u < 0,
is integrated exactly between records with the recorded PWM, and (chi_h, chi_c, tau) are fitted to the whole record
(linear least squares in chi_h and chi_c for each tau, one-dimensional search over tau).
Sensor offsets of data/module_08/calibration_rod_run_20261026_112627.csv are applied (they do not change amplitudes).
"""

import argparse
import csv
import json
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sammy_module8_angstrom_analysis as an  # noqa: E402  (paths, loader, offsets)

plt.rcdefaults()
plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.color": "#e4e4e4", "axes.spines.top": False,
                     "axes.spines.right": False, "figure.facecolor": "white", "savefig.facecolor": "white"})

REPO, DATA_DIR, FIG_DIR, GUIDE_DIR = an.REPO, an.DATA_DIR, an.FIG_DIR, an.GUIDE_DIR
ROD = ["T1_C", "T2_C", "T3_C", "T4_C", "T5_C"]
COLORS = an.COLORS
M6 = dict(chi_h=0.46, chi_c=0.23, tau=80.0, T_amb=22.0)      # Module 6 simulation defaults (python/Lab_6_7_modeling_tec.py)
M4 = dict(chi_h=0.50127, chi_c=0.18091)                      # Module 4 steady-state curve (GUI and sketch defaults)
STEP_FILL = {1: "#dbe9f6", 2: "#dff1df", 3: "#fbe8d3"}
TAU_SKIP = 2.5                                              # start-up cycles skipped: enough cycles to cover 2.5 tau (tau = 80 s)
HARM = 3


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


# ---------------------------------------------------------------------------
# input
# ---------------------------------------------------------------------------

def load_run(path):
    cols = an.load(path)
    offs = an.load_offsets(an.OFFSETS)
    data = {}
    for ch in ["TEC_C"] + ROD:
        y = cols[ch].astype(float).copy()
        if ch in offs:
            y = (y - offs[ch][0]) / offs[ch][1]
        data[ch] = y
    return cols, data


def find_steps(cols):
    t, st, rs = cols["t"], cols["step"].astype(int), cols["run_state"]
    out = []
    for s in sorted(set(st[rs == 2])):
        idx = np.flatnonzero((rs == 2) & (st == s))
        P = float(np.median(cols["period_s"][idx]))
        out.append(dict(step=s, period=P, idx=idx, t0=float(t[idx[0]]), t1=float(t[idx[-1]]),
                        ncyc=int(round((t[idx[-1]] - t[idx[0]] + 0.5) / P))))
    return out


def baseline(cols, data):
    """Mean and scatter of every channel over the quiet idle stretch (u = 0) before anything was switched on."""
    t, rs = cols["t"], cols["run_state"]
    first_on = float(t[np.flatnonzero(rs != 0)[0]])
    sel = (t > 40) & (t < first_on - 3) & (rs == 0)
    stats = {ch: dict(mean=float(np.mean(data[ch][sel])), sd=float(np.std(data[ch][sel], ddof=1)), n=int(sel.sum())) for ch in data}
    return {ch: s["mean"] for ch, s in stats.items()}, (40.0, first_on - 3.0), stats


# ---------------------------------------------------------------------------
# fitting
# ---------------------------------------------------------------------------

def hfit(t, y, w, nh=HARM, drift=True):
    tm = 0.5 * (t[0] + t[-1])
    s = t - tm
    cols = [np.ones_like(s)]
    for k in range(1, nh + 1):
        cols += [np.cos(k * w * s), np.sin(k * w * s)]
    if drift:
        cols.append(s)
    X = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ coef
    out = dict(mean=float(coef[0]), drift=float(coef[-1]) if drift else 0.0, rms=float(np.sqrt(np.mean(res ** 2))),
               fit=X @ coef, res=res, tm=tm)
    for k in range(1, nh + 1):
        b, c = coef[2 * k - 1], coef[2 * k]
        out[f"A{k}"] = float(math.hypot(b, c))
        out[f"th{k}"] = float(math.atan2(b, c))          # A sin(k w s + th)
    return out


def window_of(step, skip_cycles):
    """Whole cycles after the skipped start-up cycles, inside the step."""
    P = step["period"]
    n = step["ncyc"] - skip_cycles
    a = step["t0"] + skip_cycles * P
    return a, n


def select(t, a, b):
    return (t >= a - 1e-9) & (t < b - 1e-9)


# ---------------------------------------------------------------------------
# one-lump model (Module 6): tau dT/dt = -(T - T_amb) + chi(u) u
# ---------------------------------------------------------------------------

def responses(t, u, tau):
    """Unit-chi responses to the positive and the negative part of u, zero start (exact between records, u held)."""
    dt = np.diff(t)
    e = np.exp(-dt / tau)
    h = np.zeros_like(t)
    c = np.zeros_like(t)
    up, un = np.maximum(u, 0.0), np.minimum(u, 0.0)
    for n in range(len(dt)):
        h[n + 1] = h[n] * e[n] + (1 - e[n]) * up[n]
        c[n + 1] = c[n] * e[n] + (1 - e[n]) * un[n]
    return h, c


def fit_chi(t, T, u, tau, T_amb):
    h, c = responses(t, u, tau)
    z = (T[0] - T_amb) * np.exp(-(t - t[0]) / tau)
    y = T - T_amb - z
    X = np.column_stack([h, c])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ coef
    return coef, float(np.sqrt(np.mean(res ** 2))), T_amb + z + X @ coef


def fit_model(t, T, u, T_amb, lo=20.0, hi=400.0):
    f = lambda tau: fit_chi(t, T, u, tau, T_amb)[1]
    grid = np.geomspace(lo, hi, 40)
    best = grid[int(np.argmin([f(x) for x in grid]))]
    a, b = best / 1.2, best * 1.2
    g = (math.sqrt(5) - 1) / 2
    c, d = b - g * (b - a), a + g * (b - a)
    for _ in range(40):
        if f(c) < f(d):
            b = d
        else:
            a = c
        c, d = b - g * (b - a), a + g * (b - a)
    tau = 0.5 * (a + b)
    coef, rms, fit = fit_chi(t, T, u, tau, T_amb)
    return dict(tau=tau, chi_h=float(coef[0]), chi_c=float(coef[1]), rms=rms, fit=fit)


def simulate_u(t, u, chi_h, chi_c, tau, T_amb, T0):
    h, c = responses(t, u, tau)
    return T_amb + (T0 - T_amb) * np.exp(-(t - t[0]) / tau) + chi_h * h + chi_c * c


def settled_prediction(P, U, chi_h, chi_c, tau):
    """Mean shift, fundamental amplitude and lag of the settled piecewise one-lump response to u = U sin(w t)."""
    w = 2 * math.pi / P
    dt = 0.05
    t = np.arange(0, 12 * tau + 12 * P, dt)
    u = U * np.sin(w * t)
    T = simulate_u(t, u, chi_h, chi_c, tau, 0.0, 0.0)
    a = t[-1] - 4 * P
    sel = t >= a
    fu, fT = hfit(t[sel], u[sel], w, HARM, False), hfit(t[sel], T[sel], w, HARM, False)
    return dict(mean=fT["mean"], A1=fT["A1"], lag=wrap(fu["th1"] - fT["th1"]), A2=fT["A2"], A3=fT["A3"])


def fourier_prediction(P, U, chi_h, chi_c, tau, kmax=3):
    """Closed form of the settled one-lump response to u = U sin(x), x = w t, with chi_h for u > 0 and chi_c for u < 0.
    chi(u) u = chibar U sin x + dchi U |sin x|, |sin x| = 2/pi - (4/pi) sum_k cos(2k x)/(4 k^2 - 1);
    each harmonic of order n is scaled by 1/sqrt(1 + (n w tau)^2) and delayed by arctan(n w tau)."""
    w = 2 * math.pi / P
    cb, dc = 0.5 * (chi_h + chi_c), 0.5 * (chi_h - chi_c)
    N = lambda W: 1.0 / math.sqrt(1 + (W * tau) ** 2)
    out = dict(mean=2 * dc * U / math.pi, A1=cb * U * N(w), lag=math.atan(w * tau))
    for k in range(1, kmax + 1):
        out[f"A{2 * k}"] = 4 * dc * U / (math.pi * (4 * k * k - 1)) * N(2 * k * w)
    return out


def analytic_equal(chi, U, P, tau):
    w = 2 * math.pi / P
    R = chi * U / math.sqrt(1 + (w * tau) ** 2)
    phi = math.atan(w * tau)
    return dict(w=w, R=R, phi=phi, dt=phi / w, norm=1 / math.sqrt(1 + (w * tau) ** 2))


def analytic_theta(t, chi, U, P, tau, theta0=0.0):
    a = analytic_equal(chi, U, P, tau)
    return a["R"] * (np.sin(a["w"] * t - a["phi"]) + math.sin(a["phi"]) * np.exp(-t / tau)) + theta0 * np.exp(-t / tau)


def rk4_equal(chi, U, P, tau, tmax, dt=0.02):
    w = 2 * math.pi / P
    f = lambda t, th: (-th + chi * U * math.sin(w * t)) / tau
    n = int(round(tmax / dt))
    t = np.arange(n + 1) * dt
    th = np.zeros(n + 1)
    for i in range(n):
        k1 = f(t[i], th[i])
        k2 = f(t[i] + dt / 2, th[i] + dt * k1 / 2)
        k3 = f(t[i] + dt / 2, th[i] + dt * k2 / 2)
        k4 = f(t[i] + dt, th[i] + dt * k3)
        th[i + 1] = th[i] + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
    return t, th


# ---------------------------------------------------------------------------
# analysis of the run
# ---------------------------------------------------------------------------

def analyse(path):
    cols, data = load_run(path)
    t = cols["t"]
    u = cols["signed_pwm"].astype(float)
    base, bwin, idle = baseline(cols, data)
    steps = find_steps(cols)
    room_rod = float(np.mean([base[c] for c in ROD]))
    T_amb = base["TEC_C"]
    x, _ = an.load_positions(an.SENSOR_MAP)

    # a short manual START before the plan (not part of the sweep)
    man = np.flatnonzero((cols["run_state"] == 1) & (t < steps[0]["t0"]))
    pre = None
    if len(man):
        pre = dict(t0=float(t[man[0]]), t1=float(t[man[-1]]), mode=str(cols["control_mode"][man[0]]), u_lo=float(u[man].min()),
                   u_hi=float(u[man].max()), T_start=float(data["TEC_C"][man[0]]),
                   T_peak=float(data["TEC_C"][(t >= t[man[0]]) & (t < steps[0]["t0"])].max()),
                   T_plan_start=float(data["TEC_C"][steps[0]["idx"][0]]))
    # sign check from the record: the first half-cycle of the first step has u > 0, the second u < 0
    s0 = steps[0]
    e3 = lambda a: float(np.mean(data["TEC_C"][np.abs(t - a) <= 1.0]))
    sign = dict(t_a=s0["t0"], t_b=s0["t0"] + s0["period"] / 2, t_c=s0["t0"] + s0["period"])
    sign.update(T_a=e3(sign["t_a"]), T_b=e3(sign["t_b"]), T_c=e3(sign["t_c"]),
                u_first=float(np.mean(u[(t >= sign["t_a"] + 5) & (t < sign["t_b"] - 5)])),
                u_second=float(np.mean(u[(t >= sign["t_b"] + 5) & (t < sign["t_c"] - 5)])))

    sched = np.concatenate([s["idx"] for s in steps])
    ts, Ts, us = t[sched], data["TEC_C"][sched], u[sched]
    model = fit_model(ts, Ts, us, T_amb)
    model_full = simulate_u(ts, us, model["chi_h"], model["chi_c"], model["tau"], T_amb, Ts[0])
    tau_est = model["tau"]

    results = []
    for s in steps:
        P = s["period"]
        w = 2 * math.pi / P
        skip = int(math.ceil(TAU_SKIP * M6["tau"] / P))
        skip = min(skip, s["ncyc"] - 2)
        a, n = window_of(s, skip)
        b = a + n * P
        sel = select(t, a, b) & (cols["run_state"] == 2) & (cols["step"] == s["step"])
        tt = t[sel]
        fu = hfit(tt, u[sel], w)
        fT = hfit(tt, data["TEC_C"][sel], w)
        lag = wrap(fu["th1"] - fT["th1"])
        # per-cycle fundamental fits (all cycles of the step)
        cyc = []
        for k in range(s["ncyc"]):
            ca = s["t0"] + k * P
            cs = select(t, ca, ca + P) & (cols["run_state"] == 2) & (cols["step"] == s["step"])
            if cs.sum() < 0.8 * P / 0.5:
                continue
            gu, gT = hfit(t[cs], u[cs], w, 1, False), hfit(t[cs], data["TEC_C"][cs], w, 1, False)
            cyc.append(dict(cycle=k + 1, t_start=ca, mean=gT["mean"], A1=gT["A1"], lag=wrap(gu["th1"] - gT["th1"]),
                            used=int(k >= skip), U=gu["A1"]))
        used = [c for c in cyc if c["used"]]
        sem = lambda key: float(np.std([c[key] for c in used], ddof=1) / math.sqrt(len(used))) if len(used) > 1 else float("nan")
        half = lambda key: float((max(c[key] for c in used) - min(c[key] for c in used)) / 2) if len(used) > 1 else float("nan")
        T_win = data["TEC_C"][sel]
        res = dict(step=s["step"], period=P, w=w, skip=skip, ncyc=s["ncyc"], used=n, a=a, b=b,
                   U=fu["A1"], mean=fT["mean"], A1=fT["A1"], A2=fT["A2"], A3=fT["A3"], lag=lag, lag_s=lag / w,
                   rms=fT["rms"], drift=fT["drift"], above=float(np.max(T_win) - fT["mean"]), below=float(fT["mean"] - np.min(T_win)),
                   sem_mean=sem("mean"), sem_A1=sem("A1"), sem_lag=sem("lag"), half_mean=half("mean"), half_A1=half("A1"),
                   half_lag=half("lag"), cycles=cyc, tt=tt, T=T_win, u=u[sel], fit=fT["fit"], res=fT["res"], fu=fu, fT=fT)
        res["thd"] = math.hypot(res["A2"], res["A3"]) / res["A1"]
        # single sinusoid (mean + fundamental + drift) fitted to the same cycles, and slopes of the 3-harmonic fit
        f1 = hfit(tt, T_win, w, 1)
        dTdt = np.gradient(fT["fit"], tt)
        res.update(rms1=f1["rms"], res1=f1["res"], fit1=f1["fit"], slope_up=float(np.max(dTdt)), slope_dn=float(np.min(dTdt)),
                   Tmax=float(np.max(T_win)), Tmin=float(np.min(T_win)), u_mean=fu["mean"], u_h2=fu["A2"] / fu["A1"], u_h3=fu["A3"] / fu["A1"],
                   u_rms=fu["rms"])
        # rod sensors, fundamental
        rod = {}
        for ch in ROD:
            g = hfit(tt, data[ch][sel], w)
            rod[ch] = dict(mean=g["mean"], A1=g["A1"], lag=wrap(fu["th1"] - g["th1"]), rms=g["rms"], drift=g["drift"])
        lags = np.unwrap(np.array([rod[c]["lag"] for c in ROD]))
        for i, c in enumerate(ROD):
            rod[c]["lag"] = float(lags[i])
        B = np.array([rod[c]["A1"] for c in ROD])
        q = -np.polyfit(x, np.log(B), 1)[0]
        qp = np.polyfit(x, lags, 1)[0]
        res["rod"] = rod
        res.update(q=float(q), qp=float(qp), kappa=float(w / (2 * q * qp)) if q > 0 and qp > 0 else float("nan"))
        results.append(res)

    # predictions for each period: Module 6 defaults, Module 4 chi, fitted model
    U = float(np.median([r["U"] for r in results]))
    preds = []
    eqtab = []
    chk_amp, chk_lag = [], []
    chi_mid = 0.5 * (M6["chi_h"] + M6["chi_c"])
    chi_fit_bar = 0.5 * (model["chi_h"] + model["chi_c"])
    for r in results:
        P = r["period"]
        eq = analytic_equal(chi_mid, U, P, M6["tau"])
        row = dict(period=P, equal_R=eq["R"], equal_phi=eq["phi"], equal_dt=eq["dt"], equal_norm=eq["norm"])
        for name, par in (("m6", dict(chi_h=M6["chi_h"], chi_c=M6["chi_c"], tau=M6["tau"])),
                          ("m4", dict(chi_h=M4["chi_h"], chi_c=M4["chi_c"], tau=M6["tau"])),
                          ("fit", dict(chi_h=model["chi_h"], chi_c=model["chi_c"], tau=model["tau"]))):
            p = settled_prediction(P, U, par["chi_h"], par["chi_c"], par["tau"])
            F = fourier_prediction(P, U, par["chi_h"], par["chi_c"], par["tau"])
            row.update({f"{name}_mean": p["mean"], f"{name}_A1": p["A1"], f"{name}_lag": p["lag"], f"{name}_A2": p["A2"],
                        f"{name}_A3": p["A3"], f"{name}_mean_F": F["mean"], f"{name}_A1_F": F["A1"], f"{name}_lag_F": F["lag"],
                        f"{name}_A2_F": F["A2"]})
            chk_amp.append(max(abs(p["mean"] - F["mean"]), abs(p["A1"] - F["A1"]), abs(p["A2"] - F["A2"])))
            chk_lag.append(abs(p["lag"] - F["lag"]))
        F6 = fourier_prediction(P, U, model["chi_h"], model["chi_c"], model["tau"], kmax=6)
        row["fit_A4_F"] = F6["A4"]
        row["fit_hi_rms"] = math.sqrt(0.5 * sum(F6[f"A{2 * k}"] ** 2 for k in range(2, 7)))
        preds.append(row)
        ef = analytic_equal(chi_fit_bar, U, P, model["tau"])
        eqtab.append(dict(period=P, w=eq["w"], wtau=eq["w"] * M6["tau"], norm=eq["norm"], phi=eq["phi"], dt=eq["dt"],
                          R_c=M6["chi_c"] * U * eq["norm"], R_mid=eq["R"], R_h=M6["chi_h"] * U * eq["norm"],
                          wtau_fit=eq["w"] * model["tau"], norm_fit=ef["norm"], phi_fit=ef["phi"], dt_fit=ef["dt"], R_fit=ef["R"],
                          U_need5=5.0 / (chi_fit_bar * ef["norm"])))
    return dict(cols=cols, data=data, t=t, u=u, base=base, bwin=bwin, idle=idle, pre=pre, sign=sign, room_rod=room_rod, T_amb=T_amb,
                steps=steps, model=model, model_full=model_full, ts=ts, Ts=Ts, us=us, results=results, preds=preds, eq=eqtab, U=U, x=x,
                fourier_check=dict(amp=float(max(chk_amp)), lag=float(max(chk_lag))), chi_mid=chi_mid, chi_fit_bar=chi_fit_bar,
                m6=dict(M6), m4=dict(M4), stamp=an.stamp_of(path), path=path)


# ---------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------

def write_tables(A, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    R, P = A["results"], A["preds"]
    with open(os.path.join(out_dir, "s183_by_period.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["period_s", "omega_rad_s", "cycles_in_step", "cycles_skipped", "cycles_used", "window_start_s", "window_end_s",
                    "U_counts", "u_mean_counts", "mean_C", "mean_minus_baseline_C", "A1_C", "A1_cycle_sem_C", "A1_half_range_C",
                    "A1_over_U_C_per_count", "lag_rad", "lag_cycle_sem_rad", "lag_half_range_rad", "lag_s", "A2_over_A1", "A3_over_A1",
                    "thd", "resid_rms_3harm_C", "resid_rms_single_sine_C", "peak_max_C", "peak_min_C", "peak_above_mean_C",
                    "peak_below_mean_C", "above_over_below", "steepest_rise_C_per_s", "steepest_fall_C_per_s", "rise_over_fall"])
        for r in R:
            w.writerow([f"{r['period']:g}", f"{r['w']:.6f}", r["ncyc"], r["skip"], r["used"], f"{r['a']:.1f}", f"{r['b']:.1f}",
                        f"{r['U']:.2f}", f"{r['u_mean']:.3f}", f"{r['mean']:.3f}", f"{r['mean'] - A['T_amb']:.3f}", f"{r['A1']:.3f}",
                        f"{r['sem_A1']:.3f}", f"{r['half_A1']:.3f}", f"{r['A1'] / r['U']:.4f}", f"{r['lag']:.4f}", f"{r['sem_lag']:.4f}",
                        f"{r['half_lag']:.4f}", f"{r['lag_s']:.2f}", f"{r['A2'] / r['A1']:.4f}", f"{r['A3'] / r['A1']:.4f}",
                        f"{r['thd']:.4f}", f"{r['rms']:.4f}", f"{r['rms1']:.4f}", f"{r['Tmax']:.2f}", f"{r['Tmin']:.2f}",
                        f"{r['above']:.3f}", f"{r['below']:.3f}", f"{r['above'] / r['below']:.3f}", f"{r['slope_up']:.4f}",
                        f"{r['slope_dn']:.4f}", f"{r['slope_up'] / -r['slope_dn']:.3f}"])
    with open(os.path.join(out_dir, "s183_idle_baseline.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["channel", "mean_C", "sd_C", "samples", "window_start_s", "window_end_s"])
        for ch, s in A["idle"].items():
            w.writerow([ch[:-2] if ch.endswith("_C") else ch, f"{s['mean']:.3f}", f"{s['sd']:.3f}", s["n"], f"{A['bwin'][0]:.1f}", f"{A['bwin'][1]:.1f}"])
    with open(os.path.join(out_dir, "s183_equal_chi.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        keys = list(A["eq"][0])
        w.writerow(keys)
        for row in A["eq"]:
            w.writerow([f"{row[k]:.5g}" for k in keys])
    with open(os.path.join(out_dir, "s183_cycle_fits.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["period_s", "cycle", "t_start_s", "used_in_fit", "mean_C", "A1_C", "lag_rad", "U_counts"])
        for r in R:
            for c in r["cycles"]:
                w.writerow([f"{r['period']:g}", c["cycle"], f"{c['t_start']:.1f}", c["used"], f"{c['mean']:.3f}", f"{c['A1']:.3f}",
                            f"{c['lag']:.4f}", f"{c['U']:.2f}"])
    m = A["model"]
    with open(os.path.join(out_dir, "s183_model_fit.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "chi_h_C_per_count", "chi_c_C_per_count", "tau_s", "T_amb_C", "resid_rms_C", "note"])
        w.writerow(["fitted to this run", f"{m['chi_h']:.4f}", f"{m['chi_c']:.4f}", f"{m['tau']:.1f}", f"{A['T_amb']:.2f}", f"{m['rms']:.3f}",
                    "least squares on the whole schedule, recorded PWM as input"])
        w.writerow(["Module 6 simulation defaults", M6["chi_h"], M6["chi_c"], M6["tau"], M6["T_amb"], "", "python/Lab_6_7_modeling_tec.py"])
        w.writerow(["Module 4 curve", M4["chi_h"], M4["chi_c"], "", "", "", "GUI and sketch defaults; tau not part of the curve"])
    with open(os.path.join(out_dir, "s183_predictions.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        keys = [k for k in P[0]]
        w.writerow(keys)
        for row in P:
            w.writerow([f"{row[k]:.5g}" for k in keys])
    with open(os.path.join(out_dir, "s183_rod_by_period.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["period_s", "sensor", "x_mm", "mean_C", "A1_C", "lag_behind_PWM_rad", "resid_rms_C", "q_1_m", "qprime_1_m", "kappa_m2_s"])
        for r in R:
            for i, ch in enumerate(ROD):
                g = r["rod"][ch]
                w.writerow([f"{r['period']:g}", ch[:2], f"{A['x'][i] * 1000:.1f}", f"{g['mean']:.3f}", f"{g['A1']:.4f}", f"{g['lag']:.4f}",
                            f"{g['rms']:.4f}", f"{r['q']:.3f}", f"{r['qp']:.3f}", f"{r['kappa']:.4e}"])
    summ = dict(stamp=A["stamp"], U=A["U"], baseline_window_s=list(A["bwin"]), baseline_TEC_C=A["T_amb"], baseline_rod_mean_C=A["room_rod"],
                idle=A["idle"], pre_plan_start=A["pre"], sign_check=A["sign"], fourier_check=A["fourier_check"],
                model={k: (float(v) if not isinstance(v, np.ndarray) else None) for k, v in A["model"].items() if k != "fit"},
                periods=[dict(period=r["period"], mean=r["mean"], A1=r["A1"], lag=r["lag"], lag_s=r["lag_s"], A2=r["A2"], A3=r["A3"],
                              thd=r["thd"], rms=r["rms"], rms1=r["rms1"], used=r["used"], skip=r["skip"], above=r["above"], below=r["below"],
                              Tmax=r["Tmax"], Tmin=r["Tmin"], slope_up=r["slope_up"], slope_dn=r["slope_dn"],
                              kappa=r["kappa"], q=r["q"], qp=r["qp"]) for r in R],
                predictions=P, equal_chi=A["eq"])
    with open(os.path.join(out_dir, "s183_summary.json"), "w") as fh:
        json.dump(summ, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------

def fig_overview(A, path):
    t, d, u = A["t"], A["data"], A["u"]
    fig, axs = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [2.4, 1]})
    for s in A["steps"]:
        for ax in axs:
            ax.axvspan(s["t0"], s["t1"] + 0.5, color=STEP_FILL.get(s["step"], "#eee"), lw=0)
        axs[0].text(0.5 * (s["t0"] + s["t1"]), 1.01, f"{s['period']:g} s period", transform=axs[0].get_xaxis_transform(), ha="center", fontsize=10)
    axs[0].plot(t, d["TEC_C"], color="black", lw=1.5, label="TEC thermistor")
    axs[0].plot(A["ts"], A["model_full"], color="#C0392B", lw=1.0, ls="--", label="one-lump fit")
    for ch in ROD:
        axs[0].plot(t, d[ch], color=COLORS[ch], lw=1.0, label=ch[:2])
    axs[0].axhline(A["T_amb"], color="#888", ls=":", lw=1)
    for ax in axs:
        ax.axvspan(A["bwin"][0], A["bwin"][1], color="#eeeeee", lw=0)
    axs[0].text(0.5 * (A["bwin"][0] + A["bwin"][1]), 1.01, "idle, u = 0", transform=axs[0].get_xaxis_transform(), ha="center", fontsize=9)
    if A["pre"]:
        p = A["pre"]
        axs[0].annotate(f"{p['t1'] - p['t0']:.0f} s test START ({p['mode']} mode),\nnot part of the sweep", xy=(0.5 * (p["t0"] + p["t1"]), p["T_peak"]),
                        xytext=(330, A["T_amb"] + 13), fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.8, color="#555"), color="#333")
    axs[0].set_ylabel("temperature (°C)")
    axs[0].legend(ncol=4, fontsize=9, loc="upper left")
    axs[1].plot(t, u, color="#202020", lw=0.9)
    axs[1].set_ylabel("applied PWM (counts)")
    axs[1].set_xlabel("Arduino time (s)")
    axs[0].set_title(f"S18.3 zero-centered raw PWM, U = {A['U']:.0f} counts (run {A['stamp']}); shaded = the three periods", fontsize=11, pad=18)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_periods(A, path):
    R = A["results"]
    fig, axs = plt.subplots(3, len(R), figsize=(4.6 * len(R), 8.6), squeeze=False, gridspec_kw={"height_ratios": [2.2, 1.5, 1]})
    for j, r in enumerate(R):
        sel = (A["t"] >= r["a"] - r["skip"] * r["period"]) & (A["t"] < r["b"]) & (A["cols"]["step"] == r["step"]) & (A["cols"]["run_state"] == 2)
        ax = axs[0, j]
        ax.plot(A["t"][sel] - r["a"], A["data"]["TEC_C"][sel], color="black", lw=1.4, label="TEC measured")
        ax.plot(r["tt"] - r["a"], r["fit1"], color="#1F77B4", lw=0.9, label="mean + one sinusoid")
        ax.plot(r["tt"] - r["a"], r["fit"], color="#C0392B", lw=1.0, ls="--", label=f"mean + {HARM} harmonics")
        ax.axvline(0, color="#888", lw=0.8, ls=":")
        ax.axhline(A["T_amb"], color="#888", lw=0.8, ls=":")
        ax.set_title(f"{r['period']:g} s: mean {r['mean']:.2f} °C, A1 {r['A1']:.2f} °C, lag {r['lag']:.2f} rad ({r['lag_s']:.1f} s)", fontsize=10)
        ax.set_ylabel("TEC temperature (°C)")
        ax.legend(fontsize=8, loc="best")
        ax2 = axs[1, j]
        ax2.plot(A["t"][sel] - r["a"], A["u"][sel], color="#202020", lw=1.0)
        ax2.set_ylabel("applied PWM (counts)")
        ax2.axvline(0, color="#888", lw=0.8, ls=":")
        ax3 = axs[2, j]
        ax3.plot(r["tt"] - r["a"], r["res1"], color="#1F77B4", lw=0.9, label=f"one sinusoid, RMS {r['rms1']:.3f} °C")
        ax3.plot(r["tt"] - r["a"], r["res"], color="#C0392B", lw=0.9, label=f"{HARM} harmonics, RMS {r['rms']:.3f} °C")
        ax3.axhline(0, color="#888", lw=0.8)
        ax3.set_ylabel("residual (°C)")
        ax3.set_xlabel("time since the start of the fitted window (s)")
        ax3.legend(fontsize=7.5, loc="best")
        ax3.set_title(f"THD (harmonics 2 and 3 over the fundamental) {100 * r['thd']:.1f} %", fontsize=9)
    fig.suptitle("Settled cycles of each period (left of the dotted line: start-up cycles, not fitted)", y=0.995)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_loops(A, path):
    R, m = A["results"], A["model"]
    fig, axs = plt.subplots(1, len(R), figsize=(4.6 * len(R), 4.8), squeeze=False)
    uu = np.linspace(-A["U"], A["U"], 100)
    for j, r in enumerate(R):
        ax = axs[0, j]
        ax.plot(r["u"], r["T"] - A["T_amb"], color="#1F4E79", lw=1.0, label="measured, settled cycles")
        ax.plot(uu, np.where(uu > 0, M6["chi_h"], M6["chi_c"]) * uu, color="#999", ls=":", lw=1.3, label="slow limit, Module 6 defaults")
        ax.plot(uu, np.where(uu > 0, m["chi_h"], m["chi_c"]) * uu, color="#C0392B", ls="--", lw=1.2, label="slow limit, fitted chi")
        ax.axhline(0, color="#888", lw=0.8)
        ax.axvline(0, color="#888", lw=0.8)
        ax.set_xlabel("applied PWM (counts)")
        ax.set_ylabel("TEC temperature − baseline (°C)")
        ax.set_title(f"{r['period']:g} s period", fontsize=11)
        if j == 0:
            ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("Temperature against PWM: the loop opens as the period gets shorter (phase lag) and the two halves differ (unequal heating and cooling)", fontsize=10, y=0.995)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_push(A, path):
    """The mechanism in one picture: the push chi(u) u, the one-lump response to it, and the measurement."""
    R, m = A["results"], A["model"]
    fig, axs = plt.subplots(1, len(R), figsize=(4.6 * len(R), 4.6), squeeze=False, sharey=True)
    for j, r in enumerate(R):
        ax = axs[0, j]
        sel = (A["ts"] >= r["a"]) & (A["ts"] < r["b"])
        tt = A["ts"][sel] - r["a"]
        uu = A["us"][sel]
        ax.fill_between(tt, 0, np.where(uu > 0, m["chi_h"], m["chi_c"]) * uu, color="#f3c9a5", lw=0, label="push χ(u)·u (what the PWM asks for)")
        ax.plot(tt, A["model_full"][sel] - A["T_amb"], color="#C0392B", lw=1.2, ls="--", label="one-lump model response")
        ax.plot(tt, A["Ts"][sel] - A["T_amb"], color="black", lw=1.3, label="measured TEC − baseline")
        ax.axhline(0, color="#888", lw=0.8)
        ax.set_xlabel("time since the start of the fitted window (s)")
        ax.set_title(f"{r['period']:g} s period", fontsize=11)
        if j == 0:
            ax.set_ylabel("°C above the idle baseline")
    h, lab = axs[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.suptitle("The push is a tall heating hump and a short cooling hump; the plate follows it slowly, so quick pushes are smoothed more", fontsize=10, y=0.995)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_period_trends(A, path):
    R, P, m = A["results"], A["preds"], A["model"]
    per = np.array([r["period"] for r in R])
    pp = np.geomspace(60, 700, 80)
    fig, axs = plt.subplots(1, 3, figsize=(13.5, 4.6))
    # amplitude
    ax = axs[0]
    ax.errorbar(per, [r["A1"] for r in R], yerr=[r["half_A1"] if not math.isnan(r["half_A1"]) else 0 for r in R], fmt="o", color="black", capsize=3, label="measured (A1)")
    for name, par, col, ls in (("Module 6 defaults", (M6["chi_h"], M6["chi_c"], M6["tau"]), "#999", ":"),
                               ("fitted to this run", (m["chi_h"], m["chi_c"], m["tau"]), "#C0392B", "--")):
        chi = 0.5 * (par[0] + par[1])
        ax.plot(pp, [analytic_equal(chi, A["U"], p, par[2])["R"] for p in pp], color=col, ls=ls, label=name)
    ax.set_xscale("log")
    ax.set_xlabel("forcing period (s)")
    ax.set_ylabel("fundamental amplitude of the TEC temperature (°C)")
    ax.set_title("amplitude falls as the period shortens", fontsize=10)
    ax.legend(fontsize=8)
    # phase
    ax = axs[1]
    ax.errorbar(per, [r["lag"] for r in R], yerr=[r["half_lag"] if not math.isnan(r["half_lag"]) else 0 for r in R], fmt="o", color="black", capsize=3, label="measured")
    for name, par, col, ls in (("Module 6 defaults", (M6["tau"],), "#999", ":"), ("fitted to this run", (m["tau"],), "#C0392B", "--")):
        ax.plot(pp, [math.atan(2 * math.pi / p * par[0]) for p in pp], color=col, ls=ls, label=name)
    ax.axhline(math.pi / 2, color="#bbb", lw=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("forcing period (s)")
    ax.set_ylabel("phase lag behind the PWM (rad)")
    ax.set_title("lag grows toward a quarter period (π/2)", fontsize=10)
    ax.legend(fontsize=8)
    # mean shift
    ax = axs[2]
    ax.errorbar(per, [r["mean"] - A["T_amb"] for r in R], yerr=[r["half_mean"] if not math.isnan(r["half_mean"]) else 0 for r in R], fmt="o", color="black", capsize=3, label="measured")
    for name, par, col, ls in (("Module 6 defaults", (M6["chi_h"], M6["chi_c"]), "#999", ":"), ("Module 4 curve", (M4["chi_h"], M4["chi_c"]), "#2a9d8f", "-."),
                               ("fitted to this run", (m["chi_h"], m["chi_c"]), "#C0392B", "--")):
        ax.axhline((par[0] - par[1]) * A["U"] / math.pi, color=col, ls=ls, label=f"{name}: (χh − χc) U / π")
    shifts = [r["mean"] - A["T_amb"] for r in R] + [(p[0] - p[1]) * A["U"] / math.pi for p in ((M6["chi_h"], M6["chi_c"]), (M4["chi_h"], M4["chi_c"]), (m["chi_h"], m["chi_c"]))]
    ax.set_ylim(min(shifts) - 0.8, max(shifts) + 0.8)
    ax.set_xscale("log")
    ax.set_xlabel("forcing period (s)")
    ax.set_ylabel("mean TEC temperature − baseline (°C)")
    ax.set_title("the average rises: heating beats cooling", fontsize=10)
    ax.legend(fontsize=8)
    for ax in axs:
        ax.set_xticks([100, 200, 500])
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.minorticks_off()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_harmonics(A, path):
    R, P = A["results"], A["preds"]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    width = 0.12
    xs = np.arange(len(R))
    for k, (key, lab, col) in enumerate((("A1", "1st (the PWM frequency)", "#1F4E79"), ("A2", "2nd (twice the frequency)", "#C0392B"), ("A3", "3rd", "#2a9d8f"))):
        ax.bar(xs + (k - 1) * 2.1 * width, [r[key] for r in R], width, color=col, label=f"measured, {lab}")
        ax.bar(xs + (k - 1) * 2.1 * width + width, [p[f"fit_{key}"] for p in P], width, color=col, alpha=0.35, hatch="//", label=f"fitted model, {lab}" if k == 0 else None)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{r['period']:g} s" for r in R])
    ax.set_ylabel("harmonic amplitude of the TEC temperature (°C)")
    ax.set_title("Waveform content: solid = measured, hatched = fitted one-lump model", fontsize=10)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_theory(A, path):
    chi, tau, U = 0.5 * (M6["chi_h"] + M6["chi_c"]), M6["tau"], A["U"]
    fig, axs = plt.subplots(1, 3, figsize=(13.5, 4.4))
    worst = 0.0
    for ax, P in zip(axs, (100.0, 200.0, 500.0)):
        tmax = max(4 * P, 600.0)
        t, th = rk4_equal(chi, U, P, tau, tmax)
        an_ = analytic_theta(t, chi, U, P, tau)
        worst = max(worst, float(np.max(np.abs(th - an_))))
        e = analytic_equal(chi, U, P, tau)
        ax.plot(t, an_, color="#1F4E79", lw=2.0, label="analytic: R[sin(ωt − φ) + sin φ e^(−t/τ)]")
        ax.plot(t[::60], th[::60], "o", color="#C0392B", ms=3.5, label="numerical (Runge-Kutta)")
        ax.plot(t, e["R"] * np.sin(e["w"] * t - e["phi"]), color="#999", lw=1.0, ls="--", label="settled part only")
        ax.set_title(f"P = {P:g} s: R = {e['R']:.2f} °C, φ = {e['phi']:.2f} rad, lag = {e['dt']:.1f} s", fontsize=10)
        ax.set_xlabel("time since the start (s)")
        ax.set_ylabel("T − T_amb (°C)")
        if P == 100.0:
            ax.legend(fontsize=7.5, loc="upper left")
    fig.suptitle(f"Check of the algebra (equal heating and cooling, χ = {chi:.3f} °C/count, τ = {tau:g} s, U = {U:.0f}): analytic and numerical curves agree to {worst:.1e} °C", fontsize=10, y=0.995)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return worst


def fig_rods(A, path):
    R = A["results"]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.6))
    x = A["x"] * 1000
    for r, col in zip(R, ("#1F4E79", "#2a9d8f", "#C0392B")):
        axs[0].semilogy(x, [r["rod"][c]["A1"] for c in ROD], "o-", color=col, label=f"{r['period']:g} s: q = {r['q']:.1f} 1/m")
        axs[1].plot(x, [r["rod"][c]["lag"] for c in ROD], "s-", color=col, label=f"{r['period']:g} s: q′ = {r['qp']:.1f} 1/m, κ = {r['kappa'] * 1e5:.1f}e-5")
    axs[0].set_xlabel("x from T1 (mm)")
    axs[0].set_ylabel("fundamental amplitude of the rod sensor (°C)")
    axs[1].set_xlabel("x from T1 (mm)")
    axs[1].set_ylabel("phase lag behind the PWM (rad)")
    axs[0].legend(fontsize=8)
    axs[1].legend(fontsize=8)
    fig.suptitle("Bonus: the raw-PWM wave also travels down the rod (fundamental only; few cycles, so only a cross-check of the Angstrom result)", fontsize=9.5, y=0.995)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--no-doc", action="store_true", help="skip the walkthrough markdown")
    a = ap.parse_args()
    run = os.path.abspath(a.run)
    A = analyse(run)
    stamp = A["stamp"]
    out_dir = os.path.join(DATA_DIR, f"s183_analysis_{stamp}")
    os.makedirs(FIG_DIR, exist_ok=True)
    write_tables(A, out_dir)
    f = lambda name: os.path.join(FIG_DIR, f"{stamp}_s183_{name}.png")
    fig_overview(A, f("overview"))
    fig_periods(A, f("periods"))
    fig_loops(A, f("pwm_vs_temperature"))
    fig_push(A, f("push_vs_response"))
    fig_period_trends(A, f("trends"))
    fig_harmonics(A, f("harmonics"))
    A["theory_worst"] = fig_theory(A, f("theory_check"))
    fig_rods(A, f("rods"))
    m = A["model"]
    print(f"baseline TEC {A['T_amb']:.2f} C, rod mean {A['room_rod']:.2f} C (window {A['bwin'][0]:.0f}..{A['bwin'][1]:.0f} s); U = {A['U']:.1f} counts")
    print(f"fit: chi_h {m['chi_h']:.3f}, chi_c {m['chi_c']:.3f}, tau {m['tau']:.1f} s, rms {m['rms']:.3f} C (record {len(A['ts'])} samples)")
    for r in A["results"]:
        print(f"{r['period']:5g} s: cycles {r['skip'] + 1}..{r['ncyc']} (used {r['used']}) mean {r['mean']:.2f} (+{r['mean'] - A['T_amb']:.2f}) "
              f"A1 {r['A1']:.2f} lag {r['lag']:.3f} rad = {r['lag_s']:.1f} s  A2/A1 {r['A2'] / r['A1']:.3f} THD {100 * r['thd']:.1f} % rms {r['rms']:.3f} "
              f"single-sine rms {r['rms1']:.3f} | peaks {r['Tmax']:.2f}/{r['Tmin']:.2f} slopes +{r['slope_up']:.3f}/{r['slope_dn']:.3f} "
              f"| rods q {r['q']:.1f} q' {r['qp']:.1f} kappa {r['kappa'] * 1e5:.2f}e-5")
    print(f"theory check: max |analytic - numerical| = {A['theory_worst']:.2e} C; Fourier series vs numerical (unequal chi): "
          f"{A['fourier_check']['amp']:.2e} C, {A['fourier_check']['lag']:.1e} rad")
    if not a.no_doc:
        try:
            import sammy_module8_s183_doc as doc
            doc.write(A, os.path.join(GUIDE_DIR, "Sammy_Module_8_S18_3_Raw_PWM_Walkthrough.md"))
        except ImportError:
            print("(walkthrough generator not present; tables and figures written)")
    print(f"Wrote {os.path.relpath(out_dir, REPO)} and figures {os.path.relpath(FIG_DIR, REPO)}/{stamp}_s183_*.png")


if __name__ == "__main__":
    main()
