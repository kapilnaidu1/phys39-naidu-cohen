#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I: the numbers of A5 (Samuel Cohen): boundary-control metrics, spatial fits and the matched-run comparison.  SAMMY.

    python3 python/sammy_module8_a5.py          (from the repository root: prints the numbers)

Reads the team's raw runs and the SAMMY analysis tables. python/sammy_module8_a5_write.py calls it and writes
    docs/assessments/a5_angstrom_cohen.md                 the text (the single source of docs/A5_Cohen.pdf)
    docs/figures/module_08_sammy/a5_fig1_control.png ... a5_fig4_comparison.png
    data/module_08_sammy/a5_control_table.csv, a5_windows.csv, a5_comparison.csv
Which window stands for which period is the WINDOWS list below.
"""

import csv
import math
import os
import sys
import warnings

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import sammy_module8_angstrom_analysis as A
import sammy_module8_finite_rod as FR
import sammy_module8_runs_summary as RS
import sammy_module8_tec_rod_sim as S

warnings.filterwarnings("ignore")

REPO, DATA, FIG = A.REPO, os.path.join(A.REPO, "data"), A.FIG_DIR
F2 = f"{DATA}/module_08/angstrom_live_20261102_094506.csv"          # Kapil, 2 Nov: feedforward, P, PI 100 s, PI 480 s
F4 = f"{DATA}/module_08/angstrom_live_20261104_110306.csv"          # Kapil, 4 Nov: PI 300 s (the matched run)
F4FIT = f"{DATA}/module_08/angstrom_fit_angstrom_live_20261104_110306_PI_300s.csv"
S183 = f"{DATA}/module_08_sammy/sammy_angstrom_live_20261111_122227.csv"
RUN16 = "20261116_090538"
PH1 = "20261116_111935_phase1_pi200s"
PH2 = "20261116_111935_phase2_raw100s"
RUN17 = "20261117_162612"
RUN18 = "20261118_104629"                                          # 18 Nov: PI 400 s, 600 s hold, 8 cycles; T3 burst masked (_mask.csv)
TR1 = "20261118_122006_phase1_pi_kp_20_ki_0_2_100s"                # 18 Nov gain trials at 100 s (slices of one plan run)
TR2 = "20261118_122006_phase2_pi_kp_12_ki_0_5_100s"
T_ROOM18 = 24.91                                                   # calibrated T1 to T5 mean of the idle lead-in, 18 Nov
T_AMB_2NOV, T_AMB_4NOV = 22.53, 27.10
TA, TB = 40.0, 16.0
# acceptance criteria for "approached 40 + 16 sin(2 pi t / tau)" (mean error, amplitude ratio, phase lag, rms error)
CRIT = dict(mean=1.0, ratio_lo=0.90, ratio_hi=1.10, lag=0.30, rms=0.20 * TB)
# (period, label, source stamp or None for Kapil's 300 s, block, room T for the mean profile)
WINDOWS = [(100, "SAMMY 16 Nov", RUN16, "strict", 22.2), (200, "SAMMY 16 Nov", PH1, "strict", 22.7),
           (300, "Kapil 4 Nov", None, "his", T_AMB_4NOV), (400, "SAMMY 18 Nov", RUN18, "strict", T_ROOM18),
           (480, "SAMMY 16 Nov", RUN16, "strict", 22.2)]
RUNS_EXTRA = [("SAMMY 18 Nov, PI 400 s", RUN18, "P", "#c0392b")]       # added to the compiled rows of sammy_module8_runs_summary
COLORS = {100: "#1F4E79", 200: "#2a9d8f", 300: "#888888", 400: "#8e44ad", 480: "#e07b00"}
wrap = A.wrap


def load_run(path, mask=None, use_mask=True):
    """Run file with the offsets; the mask is <run>_mask.csv when that file exists (use_mask=False: none, for the sensitivity check)."""
    cols = A.load(path)
    if mask is None and use_mask and os.path.exists(path.replace(".csv", "_mask.csv")):
        mask = path.replace(".csv", "_mask.csv")
    _, data, _ = A.prepare(cols, A.load_offsets(A.OFFSETS), A.load_mask(mask) if mask else {})
    return cols, data


def fit1(t, y, P, t0, t1):
    sel = (t >= t0) & (t < t1) & np.isfinite(y)
    return A.sine_fit(t[sel], y[sel], 2 * math.pi / P)


# ---------------------------------------------------------------------------
# boundary control (Q1)
# ---------------------------------------------------------------------------

def control_metrics(cols, data, t0, t1, P, raw=False):
    """Common time fit of the settled interval [t0, t1) (three whole cycles): mean error, amplitude ratio, lag behind the requested
    setpoint, rms tracking error, saturation, and the cycle-to-cycle spread of the TEC amplitude and phase."""
    t, w = cols["t"], 2 * math.pi / P
    sel = (t >= t0) & (t < t1)
    tec = data["TEC_C"]
    f = fit1(t, tec, P, t0, t1)
    pwm = cols["signed_pwm"].astype(float)
    if raw:                                  # no setpoint in RAW: the requested 40 + 16 sin is in phase with the PWM sine
        fu = fit1(t, pwm, P, t0, t1)
        sp = TA + TB * np.cos(w * t[sel] + fu["phi"])
        phi_sp = fu["phi"]
    else:
        sp = cols["setpoint_C"][sel]
        phi_sp = fit1(t, cols["setpoint_C"], P, t0, t1)["phi"]
    lag = wrap(phi_sp - f["phi"])
    cyc = [fit1(t, tec, P, t0 + k * P, t0 + (k + 1) * P) for k in range(3)]
    base = f["a"] + f["B"] * np.cos(w * t[sel] + f["phi"])
    res = tec[sel] - base
    return dict(mean=f["a"], mean_err=f["a"] - TA, ratio=f["B"] / TB, B=f["B"], lag_rad=lag, lag_s=lag / w,
                rms=float(np.sqrt(np.nanmean((tec[sel] - sp) ** 2))), pwm_min=int(pwm[sel].min()), pwm_max=int(pwm[sel].max()),
                sat=100 * float(np.mean(np.abs(pwm[sel]) >= 255)), dB=100 * max(abs(c["B"] / f["B"] - 1) for c in cyc),
                dphi=max(abs(wrap(c["phi"] - f["phi"])) for c in cyc), resid=float((res.max() - res.min()) / 2),
                a2=float(A.sine_fit(t[sel], tec[sel], w, harmonics=2)["higher"][0] / f["B"]))


def meets(m):
    return dict(mean=abs(m["mean_err"]) <= CRIT["mean"], ratio=CRIT["ratio_lo"] <= m["ratio"] <= CRIT["ratio_hi"],
                lag=abs(m["lag_rad"]) <= CRIT["lag"], rms=m["rms"] <= CRIT["rms"])


def step_window(cols, period, which=-1, ncyc=3, tb_pos=True):
    """Last ncyc whole cycles of the (which-th) schedule step of this period."""
    steps = [s for s in A.find_steps(cols) if abs(s["period"] - period) < 1 and (not tb_pos or s["tb"] > 0 or np.isnan(s["tb"]))]
    s = steps[which]
    t1 = s["t0"] + s["ncyc"] * s["period"]
    return t1 - ncyc * period, t1, s


def control_rows():
    rows = []
    c11, d11 = load_run(S183)
    rows.append(dict(key="raw0", label="RAW zero-centered, u = 50 sin", gains="U 50, U0 0", where="SAMMY 11 Nov, 461.7 to 761.7 s", P=100,
                     m=control_metrics(c11, d11, 461.7, 761.7, 100, raw=True), cols=c11, data=d11, t0=461.7, t1=761.7, raw=True))
    c16, d16 = load_run(f"{DATA}/module_08_sammy/sammy_angstrom_live_{PH2}.csv")
    t0, t1, s = step_window(c16, 100, tb_pos=False)
    rows.append(dict(key="raw1", label="RAW positive-only", gains="U 36, U0 38", where=f"SAMMY 16 Nov, {t0:.0f} to {t1:.0f} s", P=100,
                     m=control_metrics(c16, d16, t0, t1, 100, raw=True), cols=c16, data=d16, t0=t0, t1=t1, raw=True))
    c2, d2 = load_run(F2)
    t = c2["t"]
    for key, label, gains, a, b in (("ff", "Feedforward (OL), from the steady-state curve", "no feedback", 405.8, 1078.9),
                                    ("p", "P only", "Kp 12, Ki 0", 1080.1, 1590.9), ("pi100", "PI", "Kp 12, Ki 0.2", 1592.3, 2625.9)):
        rows.append(dict(key=key, label=label, gains=gains, where=f"Kapil 2 Nov, {b - 300:.0f} to {b:.0f} s", P=100,
                         m=control_metrics(c2, d2, b - 300, b, 100), cols=c2, data=d2, t0=b - 300, t1=b, raw=False, seg=(a, b), t_amb=T_AMB_2NOV))
    c16m, d16m = load_run(f"{DATA}/module_08_sammy/sammy_angstrom_live_{RUN16}.csv")
    t0, t1, s = step_window(c16m, 100)
    rows.append(dict(key="pi100b", label="PI", gains="Kp 12, Ki 0.2", where=f"SAMMY 16 Nov, {t0:.0f} to {t1:.0f} s", P=100,
                     m=control_metrics(c16m, d16m, t0, t1, 100), cols=c16m, data=d16m, t0=t0, t1=t1, raw=False))
    c200, d200 = load_run(f"{DATA}/module_08_sammy/sammy_angstrom_live_{PH1}.csv")
    t0, t1, s = step_window(c200, 200)
    rows.append(dict(key="pi200", label="PI", gains="Kp 12, Ki 0.2", where=f"SAMMY 16 Nov, {t0:.0f} to {t1:.0f} s", P=200,
                     m=control_metrics(c200, d200, t0, t1, 200), cols=c200, data=d200, t0=t0, t1=t1, raw=False))
    c4, d4 = load_run(F4)
    t0, t1, s = step_window(c4, 300)
    rows.append(dict(key="pi300", label="PI", gains="Kp 12, Ki 0.2", where=f"Kapil 4 Nov, {t0:.0f} to {t1:.0f} s", P=300,
                     m=control_metrics(c4, d4, t0, t1, 300), cols=c4, data=d4, t0=t0, t1=t1, raw=False, seg=(286.7, 2816.3), t_amb=T_AMB_4NOV))
    for key, stamp, gains, ctl in ((("kp20", TR1, "Kp 20, Ki 0.2", ("PI", 20.0, 0.2))), ("ki05", TR2, "Kp 12, Ki 0.5", ("PI", 12.0, 0.5))):
        ct, dt = load_run(f"{DATA}/module_08_sammy/sammy_angstrom_live_{stamp}.csv")
        t0, t1, s = step_window(ct, 100)
        sched = A.find_steps(ct)                   # hold step, then the 100 s step: the simulated segment is the whole schedule
        rows.append(dict(key=key, label="PI", gains=gains, where=f"SAMMY 18 Nov, {t0:.0f} to {t1:.0f} s", P=100,
                         m=control_metrics(ct, dt, t0, t1, 100), cols=ct, data=dt, t0=t0, t1=t1, raw=False,
                         seg=(sched[0]["t0"], sched[-1]["t0"] + sched[-1]["ncyc"] * 100.0), t_amb=T_ROOM18, ctl=ctl))
    return rows


# ---------------------------------------------------------------------------
# numerical TEC-rod simulation
# ---------------------------------------------------------------------------

CONTACT_1617 = ((RUN16, 100, "strict"), (PH1, 200, "strict"), (RUN17, 400, "last5"))
CONTACT_18 = ((TR1, 100, "strict"), (TR2, 100, "strict"), (RUN18, 400, "strict"))


def fit_contact(kappa, nu, windows=CONTACT_1617):
    """G_c and the thermistor lag from the T1 to TEC amplitude ratio and phase of the given SAMMY windows (default: 16 and 17 Nov, 100, 200, 400 s)."""
    wins = []
    for stamp, P, blockname in windows:
        cols, data = load_run(f"{DATA}/module_08_sammy/sammy_angstrom_live_{stamp}.csv")
        t = cols["t"]
        info = next(s for s in A.find_steps(cols) if abs(s["period"] - P) < 1 and s["tb"] > 0)
        cyc = A.cycle_fits(t, data, info)
        block = A.settled_block(cyc, info["ncyc"])[0] if blockname == "strict" else list(range(info["ncyc"] - 5, info["ncyc"]))
        f = A.analyse_block(t, data, info, cyc, block)["fits"]
        wins.append((P, 2 * math.pi / P, f["T1_C"]["B"] / f["TEC_C"]["B"] * np.exp(1j * wrap(f["T1_C"]["phi"] - f["TEC_C"]["phi"]))))

    def cost(g, ts):
        return sum(math.log(abs(m) / abs(r)) ** 2 + (np.angle(m) - np.angle(r)) ** 2
                   for P, w, r in wins for m in [S.base_ratio(g, kappa, nu, w, ts)])

    g, ts = min(((g, ts) for g in np.arange(0.15, 0.50, 0.005) for ts in np.arange(0, 8.01, 0.25)), key=lambda p: cost(*p))
    return g, ts, [(P, abs(r), float(np.angle(r)), abs(S.base_ratio(g, kappa, nu, w, ts)), float(np.angle(S.base_ratio(g, kappa, nu, w, ts))))
                   for P, w, r in wins]


def run_sim(cols, data, seg0, seg1, mode, kp, ki, t_amb, g_c, tau_s):
    t = cols["t"]
    sp_rec = cols["setpoint_C"]
    ok = np.isfinite(sp_rec)
    sp = lambda tt: float(np.interp(tt, t[ok], sp_rec[ok]))
    i0 = int(np.searchsorted(t, seg0))
    rod0 = (S.X_SENSORS, [np.nanmean(data[c][i0:i0 + 5]) for c in A.ROD])
    tp0 = float(np.nanmean(data["TEC_C"][i0:i0 + 5]))
    return S.simulate(sp, seg1, t_amb, tp0, rod0=rod0, mode=mode, kp=kp, ki=ki, kappa=KAPPA, nu=NU, g_c=g_c, tau_s=tau_s, t_start=seg0)


def sim_metrics(t, tec, sp_fn, pwm, t0, t1, P):
    sel = (t >= t0) & (t < t1)
    w = 2 * math.pi / P
    f = A.sine_fit(t[sel], tec[sel], w)
    sp = np.array([sp_fn(x) for x in t[sel]])
    fs = A.sine_fit(t[sel], sp, w)
    return dict(mean=f["a"], mean_err=f["a"] - TA, ratio=f["B"] / TB, lag_rad=wrap(fs["phi"] - f["phi"]), lag_s=wrap(fs["phi"] - f["phi"]) / w,
                rms=float(np.sqrt(np.mean((tec[sel] - sp) ** 2))), sat=100 * float(np.mean(np.abs(pwm[sel]) >= 255)),
                pwm_min=int(pwm[sel].min()), pwm_max=int(pwm[sel].max()))


def variant(kp, ki, mode, g_c, tau_s, period=100.0):
    """Simulated trial like the bench ones: room start, 300 s hold at 40 C, then the sine; metrics over the last three cycles."""
    sp = lambda x: TA if x < 300 else TA + TB * math.sin(2 * math.pi * (x - 300) / period)
    t_end = 300 + 7 * period
    t, tp, rod, u = S.simulate(sp, t_end, T_AMB_2NOV, T_AMB_2NOV, mode=mode, kp=kp, ki=ki, kappa=KAPPA, nu=NU, g_c=g_c, tau_s=tau_s)
    return sim_metrics(t, tp, sp, u, t_end - 3 * period, t_end, period), (t, tp, u)


# ---------------------------------------------------------------------------
# windows, spatial fits, mean profile (Q2, Q3)
# ---------------------------------------------------------------------------

def sammy_window(stamp, period, which, use_mask=True):
    cols, data = load_run(f"{DATA}/module_08_sammy/sammy_angstrom_live_{stamp}.csv", use_mask=use_mask)
    t = cols["t"]
    info = next(s for s in A.find_steps(cols) if abs(s["period"] - period) < 1 and s["tb"] > 0)
    cyc = A.cycle_fits(t, data, info)
    block = A.settled_block(cyc, info["ncyc"])[0] if which == "strict" else list(range(info["ncyc"] - 5, info["ncyc"]))
    blk = A.analyse_block(t, data, info, cyc, block)
    f = blk["fits"]
    g = lambda k: np.array([f[c][k] for c in A.ROD])
    return dict(B=g("B"), sB=g("sB"), phi=g("phi"), sphi=g("sphi"), a=g("a"), sa=np.full(5, 0.02), cycles=f"{block[0] + 1} to {block[-1] + 1}",
                ncyc=len(block), ncyc_recorded=info["ncyc"], tint=(blk["ta"], blk["tb"]), cols=cols, data=data)


def burst_check(stamp, period):
    """Strict settling test without the mask: the first rejected cycle (1-based), its sensor and every rod sensor's amplitude (%) and phase (rad) against the block."""
    cols, data = load_run(f"{DATA}/module_08_sammy/sammy_angstrom_live_{stamp}.csv", use_mask=False)
    info = next(s for s in A.find_steps(cols) if abs(s["period"] - period) < 1 and s["tb"] > 0)
    cyc = A.cycle_fits(cols["t"], data, info)
    block, B, PH, fail = A.settled_block(cyc, info["ncyc"])
    k = fail["cycle"]
    refB = np.nanmedian(B[block], axis=0)
    refP = np.angle(np.exp(1j * PH[block]).sum(axis=0))
    return dict(block=block, ncyc=info["ncyc"], cycle=k + 1, sensor=A.ROD[fail["sensor"]], dB=100 * (B[k] / refB - 1), dphi=wrap(PH[k] - refP))


def burst_stats(stamp, ch, t0, t1, thr=0.25, h=5):
    """Points of one raw channel more than thr C from their (2h+1)-sample running median inside [t0, t1] s, the largest departure and the largest jump between samples."""
    cols = A.load(f"{DATA}/module_08_sammy/sammy_angstrom_live_{stamp}.csv")
    t, y = cols["t"], cols[ch].astype(float)
    med = np.array([np.median(y[max(0, i - h):i + h + 1]) for i in range(len(y))])
    sel = (t >= t0) & (t <= t1)
    res = np.abs(y - med)
    return dict(n=int(np.sum(res[sel] > thr)), res_max=float(res[sel].max()), jump=float(np.max(np.abs(np.diff(y[sel])))))


def kapil_window(path):
    with open(path, newline="") as fh:
        rows = {r["channel"]: r for r in csv.DictReader(fh)}
    g = lambda k: np.array([float(rows[c][k]) for c in A.ROD])
    return dict(B=g("B_C"), sB=g("sB_C"), phi=g("phi_rad"), sphi=g("sphi_rad"), a=g("mean_C"), sa=g("s_mean_C"), cycles="2 to 7", ncyc=6,
                ncyc_recorded=8, tint=(887.2, 2687.2))


def mean_profile(x, a, sa, t_room, L, dx):
    """Finite insulated-tip profile a - T_inf = th0 cosh[mu (1 - x/L)] / cosh mu; m = mu / L. T_inf +- 0.3 C gives the systematic error."""
    out = []
    for tr in (t_room - 0.3, t_room, t_room + 0.3):
        th = a - tr
        xi = x / L

        def resid(p, sig=None):
            th0, mu = p
            mod = th0 * np.cosh(mu * (1 - xi)) / np.cosh(mu)
            return (th - mod) / (sig if sig is not None else np.maximum(sa, 0.02))
        p0 = [th[0], 1.2]
        p, r, J = FR._lm(resid, p0)
        slope = np.abs(np.gradient(th, x))
        sig = np.sqrt(np.maximum(sa, 0.02) ** 2 + (slope * dx) ** 2 + 0.02 ** 2)
        p, r, J = FR._lm(lambda q: resid(q, sig), p)
        chi2 = float(r @ r)
        cov = np.linalg.inv(J.T @ J) * max(chi2 / (len(x) - 2), 1.0)
        out.append((p[1] / L, math.sqrt(cov[1, 1]) / L, p[0], chi2))
    m = out[1][0]
    return dict(m=m, sm_stat=out[1][1], sm_sys=abs(out[2][0] - out[0][0]) / 2, theta0=out[1][2], chi2=out[1][3])


def windows():
    x, dx = A.load_positions(A.SENSOR_MAP)
    L = A.load_geometry(A.GEOMETRY)["L"]
    res = []
    for P, label, stamp, which, t_room in WINDOWS:
        wd = kapil_window(F4FIT) if stamp is None else sammy_window(stamp, P, which)
        w = 2 * math.pi / P
        phi_u = wd["phi"][0] + np.unwrap(wd["phi"] - wd["phi"][0])
        fin = FR.joint_fit(x, dx, wd["B"], wd["sB"], phi_u, wd["sphi"], w, L, True)
        semi = FR.joint_fit(x, dx, wd["B"], wd["sB"], phi_u, wd["sphi"], w, L, False)
        lam = fin["q"] + 1j * fin["qp"]
        fl = np.cosh(lam * (L - x)) / np.cosh(lam * L)
        tip = float(np.max(np.abs(fl - np.exp(-lam * x)) / np.abs(fl)))
        res.append(dict(P=P, label=label, stamp=stamp, which=which, t_room=t_room, wd=wd, fin=fin, semi=semi, phi_u=phi_u, tip=tip,
                        prof=mean_profile(x, wd["a"], wd["sa"], t_room, L, dx), x=x, L=L, dx=dx, w=w,
                        bi=((fin["q"] ** 2 - fin["qp"] ** 2) * (A.load_geometry(A.GEOMETRY)["d"] / 4) ** 2)))
    return res


def kappa_nu_pair():
    rows, fin = RS.compiled_rows(RS.RUNS + RUNS_EXTRA)
    all5 = [r for r in rows if r["meets"]]
    return RS.weighted(all5), RS.weighted(all5, "nu", "snu"), rows


def sim_for_row(row, g_c, tau_s):
    """Closed-loop simulation of the recorded segment a measured control row comes from (key p, pi100, pi300): metrics over the same
    window and the arrays for the figure."""
    cols, data = row["cols"], row["data"]
    t = cols["t"]
    ok = np.isfinite(cols["setpoint_C"])
    sp = lambda tt: float(np.interp(tt, t[ok], cols["setpoint_C"][ok]))
    seg0, seg1 = row["seg"]
    mode, kp, ki = row.get("ctl", ("P", 12.0, 0.0) if row["key"] == "p" else ("PI", 12.0, 0.2))
    arr = run_sim(cols, data, seg0, seg1, mode, kp, ki, row["t_amb"], g_c, tau_s)
    return sim_metrics(arr[0], arr[1], sp, arr[3], row["t0"], row["t1"], row["P"]), arr, sp


def comparison(g_c, tau_s, kappa, nu, win300):
    """The matched 300 s run (Kapil, 4 Nov, cycles 2 to 7): measured against the analytical finite-rod prediction driven by the measured
    T1 (kappa and nu of the shared pair, or of the window itself) and against the numerical TEC-rod simulation."""
    cols, data = load_run(F4)
    t = cols["t"]
    P, t0, t1 = 300.0, 887.2, 2687.2
    w = 2 * math.pi / P
    x, dx = A.load_positions(A.SENSOR_MAP)
    L = A.load_geometry(A.GEOMETRY)["L"]
    fm = {ch: fit1(t, data[ch], P, t0, t1) for ch in A.CHANNELS}
    t1fit = fm["T1_C"]

    def analytic(kap, nu_, tr):
        s = np.sqrt((nu_ + 1j * w) / kap)
        s = s if s.real > 0 else -s
        m = math.sqrt(nu_ / kap)
        F = np.cosh(s * (L - x)) / np.cosh(s * L)
        return (tr + (t1fit["a"] - tr) * np.cosh(m * (L - x)) / math.cosh(m * L), t1fit["B"] * np.abs(F), t1fit["phi"] + np.angle(F))

    mean_s, B_s, ph_s = analytic(kappa, nu, T_AMB_4NOV)
    f300 = win300["fin"]
    mean_w, B_w, ph_w = analytic(f300["kappa"], f300["nu"], T_AMB_4NOV)
    arr = run_sim(cols, data, 286.7, 2816.3, "PI", 12.0, 0.2, T_AMB_4NOV, g_c, tau_s)
    t_sim, tp, rod, u = arr
    fn = {ch: fit1(t_sim, rod[:, i], P, t0, t1) for i, ch in enumerate(A.ROD)}
    fn["TEC_C"] = fit1(t_sim, tp, P, t0, t1)
    sel = (t >= t0) & (t < t1)
    sensors = []
    for i, ch in enumerate(A.ROD):
        meas = data[ch][sel]
        pa = mean_s[i] + B_s[i] * np.cos(w * t[sel] + ph_s[i])
        pn = np.interp(t[sel], t_sim, rod[:, i])
        sensors.append(dict(ch=ch, x=x[i], a=fm[ch]["a"], B=fm[ch]["B"], phi=fm[ch]["phi"],
                            ana=dict(da=mean_s[i] - fm[ch]["a"], rB=B_s[i] / fm[ch]["B"], dphi=wrap(ph_s[i] - fm[ch]["phi"]),
                                     rms=float(np.sqrt(np.nanmean((meas - pa) ** 2)))),
                            ana_w=dict(da=mean_w[i] - fm[ch]["a"], rB=B_w[i] / fm[ch]["B"], dphi=wrap(ph_w[i] - fm[ch]["phi"])),
                            num=dict(da=fn[ch]["a"] - fm[ch]["a"], rB=fn[ch]["B"] / fm[ch]["B"], dphi=wrap(fn[ch]["phi"] - fm[ch]["phi"]),
                                     rms=float(np.sqrt(np.nanmean((meas - pn) ** 2))))))
    tec = dict(meas=fm["TEC_C"], sim=fn["TEC_C"], sp=fit1(t, cols["setpoint_C"], P, t0, t1))
    return dict(cols=cols, data=data, t=t, t_sim=t_sim, tp=tp, rod=rod, u=u, sensors=sensors, tec=tec, w=w, P=P, win=(t0, t1),
                series=dict(mean=mean_s, B=B_s, ph=ph_s), x=x)


# ---------------------------------------------------------------------------
# main (numbers only until the figures and text are added below)
# ---------------------------------------------------------------------------
KAPPA, NU = 9.26e-5, 1.74e-3


def main():
    global KAPPA, NU
    kw, nuw, rows = kappa_nu_pair()
    KAPPA, NU = kw[0], nuw[0]
    print(f"kappa {kw[0] * 1e5:.3f} +- {kw[1] * 1e5:.3f} chi2 {kw[2]:.1f}/{kw[3]};  nu {nuw[0] * 1e3:.3f} +- {nuw[1] * 1e3:.3f}")
    cr = control_rows()
    print("\ncontrol rows")
    for r in cr:
        m, ok = r["m"], meets(r["m"])
        print(f"  {r['key']:7s} P {r['P']:3d} {r['label'][:30]:30s} mean {m['mean']:6.2f} err {m['mean_err']:+6.2f} ratio {m['ratio']:.3f} lag {m['lag_rad']:.3f} rad {m['lag_s']:6.1f} s "
              f"rms {m['rms']:5.2f} sat {m['sat']:4.1f}% pwm {m['pwm_min']:4d}..{m['pwm_max']:4d} dB {m['dB']:.1f}% dphi {m['dphi']:.3f} resid {m['resid']:.2f} A2/A1 {m['a2']:.3f}  meets {''.join('Y' if v else 'n' for v in ok.values())}")
    g_c, tau_s, chk = fit_contact(KAPPA, NU)
    print(f"\nG_c {g_c:.3f} W/K, thermistor lag {tau_s} s")
    for P, am, pm_, bm, pmm in chk:
        print(f"   {P} s: T1/TEC measured {am:.3f}/{pm_:+.3f}, model {bm:.3f}/{pmm:+.3f}")
    print("\nsimulation variants, 100 s, last three cycles")
    for mode, kp, ki in (("P", 12, 0), ("PI", 12, 0.2), ("PI", 12, 0.5), ("PI", 20, 0.2)):
        m, _ = variant(kp, ki, mode, g_c, tau_s)
        print(f"  {mode} Kp {kp} Ki {ki}: mean err {m['mean_err']:+.2f} ratio {m['ratio']:.3f} lag {m['lag_rad']:.3f} rms {m['rms']:.2f} sat {m['sat']:.1f}% pwm {m['pwm_min']}..{m['pwm_max']}")
    print("\nwindows")
    for w in windows():
        f = w["fin"]
        print(f"  {w['P']:3d} s {w['label']:13s} cycles {w['wd']['cycles']:8s} q {f['q']:.2f}+-{f['sq']:.2f} q' {f['qp']:.2f}+-{f['sqp']:.2f} kappa {f['kappa'] * 1e5:.2f}+-{f['skappa'] * 1e5:.2f} "
              f"nu {f['nu'] * 1e3:.2f}+-{f['snu'] * 1e3:.2f} chi2 {f['chi2']:.1f}/{f['dof']} tip {100 * w['tip']:.2f}% m {w['prof']['m']:.2f}+-{w['prof']['sm_stat']:.2f}({w['prof']['sm_sys']:.2f}) "
              f"sqrt(q2-q'2) {math.sqrt(max(f['q'] ** 2 - f['qp'] ** 2, 0)):.2f}  Bi {w['bi']:.1e}")


if __name__ == "__main__":
    main()
