#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I: Angstrom analysis of a SAMMY production run.  SAMMY copy.

    python3 python/sammy_module8_angstrom_analysis.py \
        data/module_08_sammy/sammy_angstrom_live_20261110_164057.csv \
        [--mask FILE] [--t-room 24.3] [--offsets FILE]

Same method as Kapil Naidu's python/analysis/angstrom_fit.py (which stays
unchanged): for every channel

    T(t) = a + B cos(w t + phi) + c (t - tmid)           (course convention)

then weighted straight lines of ln B and of the unwrapped phase against x,
q = -slope(ln B), q' = -slope(phi),  kappa = w / (2 q q'),  nu = kappa (q^2 - q'^2).
Errors of B and phi come from the cycle-to-cycle scatter.

What this copy adds:
  - a mask file (channel, t_start_s, t_end_s, reason) removes bad stretches
    from the fits in memory; the raw CSV is never changed;
  - a stated settling test, applied cycle by cycle to every period: counting
    back from the last cycle, a cycle joins the settled block while every
    rod sensor stays within 3 % in B and 0.05 rad in phi of the block median;
  - all three periods of the production schedule in one pass;
  - the model-validity checks of the study guide: finite-length difference,
    transverse Biot number, mean-profile loss rate m against sqrt(q^2 - q'^2);
  - controller tracking numbers, tables (CSV), a text report, figures and a
    short summary.

Raw values keep the calibration offsets of data/module_08/calibration_rod_run_20261026_112627.csv
applied in memory only (they do not change B or phi, only the mean temperatures).
"""

import argparse
import csv
import json
import math
import os
import re
import warnings

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, NullLocator

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data", "module_08_sammy")
FIG_DIR = os.path.join(REPO, "docs", "figures", "module_08_sammy")
GUIDE_DIR = os.path.join(REPO, "docs", "sammy_module_08_guide")
OFFSETS = os.path.join(REPO, "data", "module_08", "calibration_rod_run_20261026_112627.csv")
SENSOR_MAP = os.path.join(DATA_DIR, "sensor_map.csv")
GEOMETRY = os.path.join(DATA_DIR, "rod_geometry.csv")

ROD = ["T1_C", "T2_C", "T3_C", "T4_C", "T5_C"]
CHANNELS = ["setpoint_C", "TEC_C"] + ROD
COLORS = {"setpoint_C": "#7f7f7f", "TEC_C": "#000000", "T1_C": "#1f77b4", "T2_C": "#ff7f0e",
          "T3_C": "#2ca02c", "T4_C": "#9467bd", "T5_C": "#8c564b"}
STEP_COLORS = {1: "#e6e6e6", 2: "#dbe9f6", 3: "#dff1df", 4: "#fbe8d3"}

RHO, CP = 2700.0, 896.0                 # 6061-T6 handbook values
K_HANDBOOK = 167.0                      # W/(m K)
KAPPA_HANDBOOK = K_HANDBOOK / (RHO * CP)
TOL_B, TOL_PHI = 0.03, 0.05             # settling tolerances (amplitude fraction, rad)
MIN_CYCLES = 5                          # settled cycles wanted per usable period

# Kapil's PI fits (data/module_08/angstrom_fit_*.txt on the shared branch): period s -> kappa, error, q, q'
KAPIL = {100: (9.758e-5, 2.3e-6, 18.53, 17.37), 180: (9.244e-5, 2.0e-6, 14.10, 13.39),
         240: (9.399e-5, 1.7e-6, 12.34, 11.29), 300: (9.311e-5, 1.6e-6, 11.06, 10.17),
         480: (8.941e-5, 2.4e-6, 9.34, 7.84)}

# Phone photos of the live GUI, straightened and cropped to the GUI window: (file in docs/images, run time on screen in s, photo id, clock on screen)
IMAGE_DIR = os.path.join(REPO, "docs", "images")
PHOTOS = [("module08_sammy_gui_step3_t4778s_IMG_2550.jpg", 4777.9, "IMG_2550", "6:00 PM"),
          ("module08_sammy_gui_step3_t4780s_IMG_2551.jpg", 4780.1, "IMG_2551", "6:00 PM"),
          ("module08_sammy_gui_step4_t6309s_IMG_2558.jpg", 6309.2, "IMG_2558", "6:26 PM")]

plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.color": "#e4e4e4",
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})


# ---------------------------------------------------------------------------
# input
# ---------------------------------------------------------------------------

def load(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    cols = {}
    for k in rows[0]:
        cols[k] = np.array([r[k] for r in rows]) if k == "control_mode" else \
            np.array([float(r[k]) for r in rows])
    cols["t"] = cols["time_ms"] / 1000.0
    return cols


def load_offsets(path):
    out = {}
    if not path or not os.path.exists(path):
        return out
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            ch = r["channel"].strip()
            col = "TEC_C" if ch == "base" else (f"T{ch[1:]}_C" if ch.startswith("R") else None)
            if col:
                out[col] = (float(r["offset_C"]), 1.0)
    return out


def load_positions(path):
    x, dx = [], []
    with open(path, newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["channel"].strip().startswith("R")]
    for r in rows[:5]:
        x.append(float(r["position_mm"]) / 1000.0)
        dx.append(float(r["position_uncertainty_mm"] or 0) / 1000.0)
    return np.array(x), np.array(dx)


def load_geometry(path):
    g = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["value"].replace(".", "", 1).isdigit():
                g[r["quantity"]] = (float(r["value"]), float(r["uncertainty"] or 0))
    return {"d": g["diameter_mean"][0] / 1000.0, "sd": g["diameter_mean"][1] / 1000.0,
            "L": g["analysis_length_L"][0] / 1000.0, "sL": g["analysis_length_L"][1] / 1000.0}


def load_mask(path):
    out = {}
    if path and os.path.exists(path):
        with open(path, newline="") as fh:
            for r in csv.DictReader(fh):
                out.setdefault(r["channel"].strip() + "_C", []).append(
                    (float(r["t_start_s"]), float(r["t_end_s"]), r["reason"]))
    return out


def prepare(cols, offsets, mask):
    """Offsets applied in memory; 'raw' keeps masked samples, 'data' has them as nan."""
    t = cols["t"]
    raw, data, masked = {}, {}, {}
    for ch in CHANNELS:
        y = cols[ch].astype(float).copy()
        if ch in offsets:
            y = (y - offsets[ch][0]) / offsets[ch][1]
        m = np.zeros(len(y), dtype=bool)
        for a, b, _ in mask.get(ch, []):
            m |= (t >= a) & (t <= b)
        raw[ch] = y
        data[ch] = np.where(m, np.nan, y)
        masked[ch] = m
    return raw, data, masked


def write_clean_csv(run, out_path, mask):
    """Same schema as the raw file; masked samples become nan. Offsets are NOT applied."""
    with open(run, newline="") as fh:
        rows = list(csv.reader(fh))
    head = rows[0]
    ti = head.index("time_ms")
    n = 0
    for r in rows[1:]:
        t = float(r[ti]) / 1000.0
        for col, wins in mask.items():
            if any(a <= t <= b for a, b, _ in wins):
                r[head.index(col)] = "nan"
                n += 1
    with open(out_path, "w", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)
    return n


# ---------------------------------------------------------------------------
# fits
# ---------------------------------------------------------------------------

def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def design(t, w, harmonics, tm):
    cols = [np.ones_like(t)]
    for k in range(1, harmonics + 1):
        cols += [np.sin(k * w * t), np.cos(k * w * t)]
    cols.append(t - tm)
    return np.column_stack(cols)


def sine_fit(t, y, w, harmonics=1):
    """a + sum_k [s_k sin(k w t) + c_k cos(k w t)] + c (t - tmid) on the finite samples."""
    ok = np.isfinite(y)
    t, y = t[ok], y[ok]
    tm = t.mean()
    X = design(t, w, harmonics, tm)
    p, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ p
    f = dict(a=p[0], B=float(np.hypot(p[1], p[2])), phi=float(np.arctan2(-p[1], p[2])), drift=p[-1],
             tm=tm, p=p, w=w, harmonics=harmonics, n=int(ok.sum()),
             rms=float(np.sqrt(np.mean(resid ** 2))), resid=resid)
    f["higher"] = [float(np.hypot(p[2 * k - 1], p[2 * k])) for k in range(2, harmonics + 1)]
    return f


def model(f, t):
    return design(t, f["w"], f["harmonics"], f["tm"]) @ f["p"]


def find_steps(cols):
    t, st = cols["t"], cols["step"].astype(int)
    out = []
    for s in sorted(set(st[cols["run_state"] == 2])):
        idx = np.flatnonzero((cols["run_state"] == 2) & (st == s))
        P = float(np.median(cols["period_s"][idx]))
        out.append(dict(step=s, t0=float(t[idx[0]]), t1=float(t[idx[-1]]), period=P,
                        tb=float(np.median(cols["Tb_C"][idx])), ta=float(np.median(cols["Ta_C"][idx])),
                        ncyc=int((t[idx[-1]] - t[idx[0]] + 1.5) // P), idx=idx))
    return out


def cycle_fits(t, data, info):
    w = 2 * math.pi / info["period"]
    out = {ch: [] for ch in CHANNELS}
    for k in range(info["ncyc"]):
        a, b = info["t0"] + k * info["period"], info["t0"] + (k + 1) * info["period"]
        sel = (t >= a) & (t < b)
        for ch in CHANNELS:
            y = data[ch][sel]
            ok = np.isfinite(y)
            if ok.sum() < max(20, 0.8 * sel.sum()):
                out[ch].append(None)
                continue
            f = sine_fit(t[sel], y, w)
            f["n_window"], f["n_masked"] = int(sel.sum()), int(sel.sum() - ok.sum())
            out[ch].append(f)
    return out


def settled_block(cyc, ncyc):
    """Counting back from the last cycle, add a cycle while all rod sensors stay within the
    tolerances of the block median. Returns the cycle indices and the per-cycle arrays."""
    B = np.full((ncyc, 5), np.nan)
    PH = np.full((ncyc, 5), np.nan)
    for i, ch in enumerate(ROD):
        for k in range(ncyc):
            if cyc[ch][k] is not None:
                B[k, i], PH[k, i] = cyc[ch][k]["B"], cyc[ch][k]["phi"]
    block = [ncyc - 1]
    fail = None
    for k in range(ncyc - 2, -1, -1):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            refB = np.nanmedian(B[block], axis=0)
        z = np.exp(1j * PH[block])
        z[~np.isfinite(PH[block])] = 0
        refP = np.angle(z.sum(axis=0))
        valid = np.isfinite(B[k]) & np.isfinite(refB)
        good = (np.abs(B[k] / refB - 1) <= TOL_B) & (np.abs(wrap(PH[k] - refP)) <= TOL_PHI)
        if not np.all(good[valid]):
            dB = 100 * (B[k] / refB - 1)
            dP = wrap(PH[k] - refP)
            with np.errstate(invalid="ignore"):
                score = np.where(valid, np.maximum(np.abs(dB) / (100 * TOL_B), np.abs(dP) / TOL_PHI), -1.0)
            i = int(np.argmax(score))
            fail = dict(cycle=k, sensor=i, dB=float(dB[i]), dphi=float(dP[i]))
            break
        block.insert(0, k)
    return block, B, PH, fail


def analyse_block(t, data, info, cyc, block):
    P = info["period"]
    w = 2 * math.pi / P
    ta, tb = info["t0"] + block[0] * P, info["t0"] + (block[-1] + 1) * P
    sel = (t >= ta) & (t < tb)
    fits = {}
    for ch in CHANNELS:
        f = sine_fit(t[sel], data[ch][sel], w, harmonics=3)
        per = np.array([[cyc[ch][k]["B"], cyc[ch][k]["phi"]] for k in block if cyc[ch][k] is not None])
        n = len(per)
        f["n_cycles"] = n
        f["per"] = per
        f["sB"] = per[:, 0].std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
        f["sphi"] = wrap(per[:, 1] - f["phi"]).std(ddof=1) / math.sqrt(n) if n > 1 else float("nan")
        f["h2"], f["h3"] = f["higher"][0] / f["B"], f["higher"][1] / f["B"]
        f["drift_cycle"] = f["drift"] * P
        fits[ch] = f
    return dict(w=w, ta=ta, tb=tb, sel=sel, fits=fits)


def spatial(fits, w, x, dx):
    """Weighted lines ln B and unwrapped phi against x (as angstrom_fit.py)."""
    B = np.array([fits[c]["B"] for c in ROD])
    sB = np.array([fits[c]["sB"] for c in ROD])
    phi = np.array([fits[c]["phi"] for c in ROD])
    sphi = np.array([fits[c]["sphi"] for c in ROD])
    phi_u = phi[0] + np.unwrap(phi - phi[0])
    lnB = np.log(B)
    q0 = -np.polyfit(x, lnB, 1)[0]
    qp0 = -np.polyfit(x, phi_u, 1)[0]
    s_lnB = np.sqrt((sB / B) ** 2 + (q0 * dx) ** 2 + 1e-8)
    s_phi = np.sqrt(sphi ** 2 + (qp0 * dx) ** 2 + 1e-8)

    def wline(y, s):
        W = 1.0 / s ** 2
        A = np.column_stack([np.ones_like(x), x])
        cov = np.linalg.inv(A.T @ (A * W[:, None]))
        p = cov @ (A.T @ (W * y))
        chi2 = float(np.sum(W * (y - A @ p) ** 2))
        dof = len(x) - 2
        scale = max(chi2 / dof, 1.0)
        return p, np.sqrt(np.diag(cov) * scale), chi2, dof

    pA, eA, chiA, dof = wline(lnB, s_lnB)
    pP, eP, chiP, _ = wline(phi_u, s_phi)
    q, sq, qp, sqp = -pA[1], eA[1], -pP[1], eP[1]
    kappa = w / (2 * q * qp)
    skappa = kappa * math.hypot(sq / q, sqp / qp)
    nu = kappa * (q ** 2 - qp ** 2)
    snu = math.sqrt((nu / kappa * skappa) ** 2 + (kappa * 2 * q * sq) ** 2 + (kappa * 2 * qp * sqp) ** 2)
    return dict(B=B, sB=np.sqrt(sB ** 2 + (q0 * dx * B) ** 2), phi_u=phi_u, sphi=s_phi, q=q, sq=sq,
                qp=qp, sqp=sqp, kappa=kappa, skappa=skappa, nu=nu, snu=snu, chiA=chiA, chiP=chiP,
                dof=dof, pA=pA, pP=pP)


def derived(sp, x, geom, fits, t_room):
    d, L = geom["d"], geom["L"]
    q, qp = sp["q"], sp["qp"]
    out = dict(k=RHO * CP * sp["kappa"], sk=RHO * CP * sp["skappa"],
               h=RHO * CP * (d / 4) * sp["nu"], sh=RHO * CP * (d / 4) * sp["snu"],
               Bi=(d / 4) ** 2 * (q ** 2 - qp ** 2),
               m_osc=math.sqrt(q ** 2 - qp ** 2) if q > qp else float("nan"))
    lam = q + 1j * qp
    fin = np.cosh(lam * (L - x)) / np.cosh(lam * L)
    out["finite_rel"] = np.abs(fin - np.exp(-lam * x)) / np.abs(fin)
    a = np.array([fits[c]["a"] for c in ROD])
    ms = []
    for tr in (t_room - 0.3, t_room, t_room + 0.3):
        ex = a - tr
        ms.append(-np.polyfit(x, np.log(ex), 1)[0] if np.all(ex > 0) else float("nan"))
    out["m_dc"], out["sm_dc"] = ms[1], abs(ms[2] - ms[0]) / 2
    out["a_profile"] = a
    return out


def hold_metrics(cols, data, info):
    idx = info["idx"]
    t = cols["t"][idx] - info["t0"]
    tec = data["TEC_C"][idx]
    pwm = cols["signed_pwm"][idx]
    hit = np.flatnonzero(tec >= info["ta"] - 0.5)
    return dict(t_reach=float(t[hit[0]]) if len(hit) else float("nan"), tec_max=float(np.nanmax(tec)),
                overshoot=float(np.nanmax(tec) - info["ta"]), pwm_max=int(pwm.max()),
                t1_end=float(data["T1_C"][idx][-1]), tec_end=float(tec[-1]))


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------

def label(ch):
    return ch.replace("_C", "")


def fig_overview(path, cols, data, masked, steps, mask):
    t = cols["t"]
    fig, axs = plt.subplots(3, 1, figsize=(12, 7.4), sharex=True,
                            gridspec_kw={"height_ratios": [3, 1.1, 1.1]})
    ax = axs[0]
    for s in steps:
        for a_ in axs:
            a_.axvspan(s["t0"], s["t1"], color=STEP_COLORS.get(s["step"], "white"), zorder=0)
        txt = "hold" if s["tb"] == 0 else f"{s['period']:.0f} s cycles"
        ax.text((s["t0"] + s["t1"]) / 2, 1.01, txt, transform=ax.get_xaxis_transform(), ha="center",
                va="bottom", fontsize=10)
    ax.plot(t, cols["setpoint_C"], color=COLORS["setpoint_C"], ls="--", lw=1.0, label="setpoint")
    for ch in ["TEC_C"] + ROD:
        ax.plot(t, data[ch], color=COLORS[ch], lw=1.0, label=label(ch))
    for col, wins in mask.items():
        for a, b, _ in wins:
            if a > steps[0]["t0"] - 1:
                ax.axvspan(a, b, ymin=0, ymax=1, color="#d62728", alpha=0.25, lw=0)
    ax.plot([], [], color="#d62728", alpha=0.4, lw=6, label="masked in fits")
    ax.set_ylabel("temperature (°C)")
    ax.set_ylim(21, 65)
    ax.legend(ncol=9, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, 1.0), frameon=False)
    ax2 = axs[1]
    ax2.plot(t, cols["signed_pwm"], color="#202020", lw=0.6)
    for y in (255, -255):
        ax2.axhline(y, color="#C0392B", ls=":", lw=1)
    ax2.set_ylabel("applied PWM")
    ax2.set_ylim(-275, 275)
    ax3 = axs[2]
    err = data["TEC_C"] - cols["setpoint_C"]
    ax3.plot(t, err, color="#444444", lw=0.6)
    ax3.axhline(0, color="#999999", lw=0.8)
    ax3.set_ylabel("TEC - setpoint (°C)")
    ax3.set_ylim(-12, 12)
    ax3.set_xlabel("Arduino time (s)")
    ax3.set_xlim(0, steps[-1]["t1"] + 130)
    fig.suptitle("SAMMY production run 10 Nov 2026: setpoint, TEC and rod temperatures, applied PWM", y=0.995)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_cycles(path, res, t, data, raw, info):
    fits = res["fits"]
    sel = res["sel"]
    tt = t[sel]
    fig, axs = plt.subplots(2, 1, figsize=(12, 7), gridspec_kw={"height_ratios": [2.4, 1]})
    for ch in ["TEC_C"] + ROD:
        axs[0].plot(tt, raw[ch][sel], color=COLORS[ch], lw=1.0, label=label(ch))
        axs[0].plot(tt, model(fits[ch], tt), color=COLORS[ch], lw=1.0, ls="--")
    gone = np.zeros(tt.shape, bool)
    for ch in ROD:
        gone |= ~np.isfinite(data[ch][sel]) & np.isfinite(raw[ch][sel])
    if gone.any():
        axs[0].fill_between(tt, 0, 1, where=gone, transform=axs[0].get_xaxis_transform(), color="#d62728",
                            alpha=0.18, lw=0, label="masked in fits")
    axs[0].plot(tt, data["setpoint_C"][sel], color=COLORS["setpoint_C"], lw=0.9, ls=":", label="setpoint")
    axs[0].set_ylabel("temperature (°C)")
    axs[0].set_title(f"{info['period']:.0f} s period, settled block: cycles "
                     f"{res['block'][0] + 1} to {res['block'][-1] + 1} of {info['ncyc']} "
                     f"(data solid, fit dashed)", fontsize=11)
    axs[0].legend(ncol=8, fontsize=9, loc="upper right")
    for ch in ROD:
        ok = np.isfinite(data[ch][sel])
        resid = np.full(tt.shape, np.nan)
        resid[ok] = fits[ch]["resid"]
        axs[1].plot(tt, resid, color=COLORS[ch], lw=0.7, label=label(ch))
    axs[1].set_ylabel("residual (°C)")
    axs[1].set_xlabel("Arduino time (s)")
    axs[1].set_ylim(-0.6, 0.6)
    axs[1].set_title("residuals of the fits (RMS in the report)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_spatial(path, results, x):
    n = len(results)
    fig, axs = plt.subplots(2, n, figsize=(4.4 * n, 7), squeeze=False)
    xx = np.linspace(0, x.max() * 1.05, 50)
    for j, r in enumerate(results):
        sp = r["sp"]
        a1, a2 = axs[0, j], axs[1, j]
        a1.errorbar(x * 1000, sp["B"], yerr=sp["sB"], fmt="o", color="#1F4E79")
        a1.plot(xx * 1000, np.exp(sp["pA"][0] - sp["q"] * xx), color="#1F4E79")
        a1.set_yscale("log")
        lo, hi = a1.get_ylim()
        ticks = [v for v in (0.3, 0.5, 0.7, 1, 1.5, 2, 3, 4, 5, 6, 8) if lo <= v <= hi]
        a1.set_yticks(ticks)
        a1.set_yticklabels([f"{v:g}" for v in ticks])
        a1.yaxis.set_minor_locator(NullLocator())
        a1.set_title(f"{r['info']['period']:.0f} s:  q = {sp['q']:.2f} ± {sp['sq']:.2f} 1/m", fontsize=11)
        a1.set_ylabel("amplitude B (°C, log)")
        a2.errorbar(x * 1000, sp["phi_u"], yerr=sp["sphi"], fmt="s", color="#C0392B")
        a2.plot(xx * 1000, sp["pP"][0] - sp["qp"] * xx, color="#C0392B")
        a2.set_title(f"q′ = {sp['qp']:.2f} ± {sp['sqp']:.2f} 1/m,  κ = {sp['kappa'] * 1e5:.2f}e-5 m²/s",
                     fontsize=11)
        a2.set_ylabel("unwrapped phase φ (rad)")
        a2.set_xlabel("x from T1 (mm)")
        a1.set_xlabel("x from T1 (mm)")
    fig.suptitle("Amplitude and phase against distance along the rod (settled blocks)", y=0.995)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_settling(path, results):
    n = len(results)
    fig, axs = plt.subplots(2, n, figsize=(4.6 * n, 7), squeeze=False, sharex="col")
    for j, r in enumerate(results):
        B, PH, block = r["B_cyc"], r["PH_cyc"], r["block"]
        refB = np.array([r["fits"][c]["B"] for c in ROD])
        refP = np.array([r["fits"][c]["phi"] for c in ROD])
        k = np.arange(1, B.shape[0] + 1)
        for i, ch in enumerate(ROD):
            axs[0, j].plot(k, 100 * (B[:, i] / refB[i] - 1), "o-", color=COLORS[ch], ms=4, lw=0.9, label=label(ch))
            axs[1, j].plot(k, wrap(PH[:, i] - refP[i]), "o-", color=COLORS[ch], ms=4, lw=0.9)
        for a_ in axs[:, j]:
            a_.axvspan(block[0] + 0.5, block[-1] + 1.5, color="#9bd39b", alpha=0.25, lw=0)
        axs[0, j].axhspan(-100 * TOL_B, 100 * TOL_B, color="#cccccc", alpha=0.4, lw=0)
        axs[1, j].axhspan(-TOL_PHI, TOL_PHI, color="#cccccc", alpha=0.4, lw=0)
        axs[0, j].set_title(f"{r['info']['period']:.0f} s: {len(block)} settled cycles", fontsize=11)
        axs[0, j].set_ylim(-15, 15)
        axs[1, j].set_ylim(-0.25, 0.25)
        axs[1, j].set_xlabel("cycle number")
        if j == 0:
            axs[0, j].set_ylabel("B vs settled block (%)")
            axs[1, j].set_ylabel("phase vs settled block (rad)")
            axs[0, j].legend(fontsize=8, ncol=3, loc="upper left")
    fig.suptitle("Settling test: green = settled block, grey band = tolerance (3 %, 0.05 rad); T5 gaps are masked cycles",
                 y=0.995, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def period_axis(ax, results):
    periods = [r["info"]["period"] for r in results]
    ax.set_xticks(periods)
    ax.set_xticklabels([f"{p:.0f}" for p in periods])
    ax.xaxis.set_minor_locator(NullLocator())


def fig_kappa(path, results):
    fig, axs = plt.subplots(1, 2, figsize=(12, 5))
    ax = axs[0]
    for P, (k, sk, _, _) in KAPIL.items():
        ax.errorbar(P, k * 1e5, yerr=sk * 1e5, fmt="s", mfc="white", color="#888888", ms=7, capsize=3,
                    label="Kapil (PI, 2 and 4 Nov)" if P == 100 else None)
    for r in results:
        sp = r["sp"]
        ok = len(r["block"]) >= MIN_CYCLES
        ax.errorbar(r["info"]["period"], sp["kappa"] * 1e5, yerr=sp["skappa"] * 1e5, fmt="o", ms=9,
                    color="#1F4E79" if ok else "#7a9cc6", capsize=4, mfc="#1F4E79" if ok else "white",
                    label=("SAMMY, settled block (open: < 5 cycles)" if r is results[0] else None))
        s5 = r["sp5"]
        ax.errorbar(r["info"]["period"] * 1.04, s5["kappa"] * 1e5, yerr=s5["skappa"] * 1e5, fmt="D", ms=6,
                    color="#2a9d8f", capsize=3, label=("SAMMY, last 5 cycles" if r is results[0] else None))
    ax.axhline(KAPPA_HANDBOOK * 1e5, color="#C0392B", ls="--", label="handbook 6061-T6 (6.9)")
    ax.set_xscale("log")
    period_axis(ax, results)
    ax.set_xlabel("forcing period (s)")
    ax.set_ylabel("κ (10⁻⁵ m²/s)")
    ax.set_ylim(5, 12)
    ax.legend(fontsize=9)
    ax.set_title("Thermal diffusivity from each period", fontsize=11)
    ax2 = axs[1]
    for P, (k, sk, q, qp) in KAPIL.items():
        ax2.plot(P, k * (q ** 2 - qp ** 2) * 1e3, "s", mfc="white", color="#888888", ms=7)
    for r in results:
        sp = r["sp"]
        ax2.errorbar(r["info"]["period"], sp["nu"] * 1e3, yerr=sp["snu"] * 1e3, fmt="o", ms=9, color="#1F4E79",
                     capsize=4)
    ax2.axhline(0, color="#999999", lw=0.8)
    ax2.set_xscale("log")
    period_axis(ax2, results)
    ax2.set_xlabel("forcing period (s)")
    ax2.set_ylabel("ν (10⁻³ 1/s)")
    ax2.set_title("Side-loss rate (the small difference q² − q′² makes it noisy)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_length(path, results):
    fig, ax = plt.subplots(figsize=(8.5, 5.4))
    P = np.logspace(math.log10(60), math.log10(700), 100)
    kk = np.array([r["sp"]["kappa"] for r in results])
    ww = 1 / np.array([r["sp"]["skappa"] for r in results]) ** 2
    kap = float(np.sum(ww * kk) / np.sum(ww))
    ax.plot(P, 1000 * np.sqrt(kap * P / math.pi), color="#1F4E79", label=f"√(κP/π), κ = {kap * 1e5:.2f}e-5 (weighted mean of this run)")
    ax.plot(P, 1000 * np.sqrt(KAPPA_HANDBOOK * P / math.pi), color="#C0392B", ls="--", label="handbook κ = 6.9e-5")
    for r in results:
        sp, Pi = r["sp"], r["info"]["period"]
        ax.errorbar(Pi, 1000 / sp["q"], yerr=1000 * sp["sq"] / sp["q"] ** 2, fmt="o", color="#1F4E79", capsize=3,
                    label="1/q (amplitude)" if r is results[0] else None)
        ax.errorbar(Pi, 1000 / sp["qp"], yerr=1000 * sp["sqp"] / sp["qp"] ** 2, fmt="s", color="#C0392B", capsize=3,
                    label="1/q′ (phase)" if r is results[0] else None)
    ax.axhline(101.6, color="#999999", ls=":", lw=1)
    ax.text(62, 104, "T1 to T5 spacing 101.6 mm", fontsize=9, color="#666666")
    ax.set_xscale("log")
    period_axis(ax, results)
    ax.set_xlabel("forcing period (s)")
    ax.set_ylabel("characteristic length (mm)")
    ax.set_title("How far the temperature wave reaches: e-folding length against period", fontsize=11)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_profile(path, results, x, t_room):
    n = len(results)
    fig, axs = plt.subplots(1, n, figsize=(4.4 * n, 4.8), squeeze=False)
    xx = np.linspace(0, x.max() * 1.05, 50)
    for j, r in enumerate(results):
        a = r["der"]["a_profile"] - t_room
        ax = axs[0, j]
        ax.plot(x * 1000, a, "o", color="#1F4E79")
        p = np.polyfit(x, np.log(a), 1)
        ax.plot(xx * 1000, np.exp(np.polyval(p, xx)), color="#1F4E79")
        ax.set_yscale("log")
        plain = FuncFormatter(lambda v, _: f"{v:g}")
        ax.yaxis.set_major_formatter(plain)
        ax.yaxis.set_minor_formatter(plain)
        ax.set_title(f"{r['info']['period']:.0f} s\nslope of the mean profile {r['der']['m_dc']:.1f} 1/m,  "
                     f"√(q²−q′²) = {r['der']['m_osc']:.1f} 1/m", fontsize=10)
        ax.set_xlabel("x from T1 (mm)")
        if j == 0:
            ax.set_ylabel(f"mean T − T_room (°C), T_room = {t_room:.1f}")
    fig.suptitle("Mean temperature profile along the rod (settled blocks)", y=0.995)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_tracking(path, results, t, data):
    n = len(results)
    fig, axs = plt.subplots(2, n, figsize=(4.6 * n, 7), squeeze=False, gridspec_kw={"height_ratios": [2.2, 1]})
    for j, r in enumerate(results):
        info, block = r["info"], r["block"]
        P = info["period"]
        k = block[-1]
        a, b = info["t0"] + k * P, info["t0"] + (k + 1) * P
        sel = (t >= a) & (t < b)
        tt = t[sel] - a
        axs[0, j].plot(tt, data["setpoint_C"][sel], color=COLORS["setpoint_C"], ls="--", label="setpoint")
        axs[0, j].plot(tt, data["TEC_C"][sel], color="black", label="TEC")
        axs[0, j].plot(tt, data["T1_C"][sel], color=COLORS["T1_C"], label="T1")
        axs[0, j].set_title(f"{P:.0f} s: last settled cycle", fontsize=11)
        axs[1, j].plot(tt, r["cols_pwm"][sel], color="#202020")
        axs[1, j].axhline(255, color="#C0392B", ls=":")
        axs[1, j].axhline(-255, color="#C0392B", ls=":")
        axs[1, j].set_ylim(-275, 275)
        axs[1, j].set_xlabel("time in the cycle (s)")
        if j == 0:
            axs[0, j].set_ylabel("temperature (°C)")
            axs[1, j].set_ylabel("applied PWM")
            axs[0, j].legend(fontsize=9)
    fig.suptitle("PI controller tracking: TEC follows the setpoint, T1 is smaller and later", y=0.995)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def t5_models(cols, raw, masked, steps):
    """T5 predicted from T3, T4 and their slopes, fitted on the last two cycles of each step."""
    t = cols["t"]
    sm = lambda a: np.convolve(a, np.ones(9) / 9, mode="same")
    T3, T4, T5 = raw["T3_C"], raw["T4_C"], raw["T5_C"]
    X = np.column_stack([np.ones_like(T3), T3, np.gradient(sm(T3), t), T4, np.gradient(sm(T4), t)])
    out = {}
    for s in steps:
        if s["tb"] == 0:
            continue
        inrun = (t >= s["t0"]) & (t < s["t1"])
        cyc = ((t - s["t0"]) // s["period"]).astype(int)
        fit = inrun & np.isin(cyc, (s["ncyc"] - 2, s["ncyc"] - 1)) & ~masked["T5_C"]
        coef, *_ = np.linalg.lstsq(X[fit], T5[fit], rcond=None)
        pred = X @ coef
        res = T5 - pred
        use = inrun & ~masked["T5_C"]
        out[s["step"]] = dict(pred=pred, res=res, inrun=inrun, fit=fit,
                              rms_fit=float(np.sqrt(np.mean(res[fit] ** 2))),
                              max_outside=float(np.max(np.abs(res[use]))),
                              max_inside=float(np.max(np.abs(res[inrun & masked["T5_C"]])))
                              if np.any(inrun & masked["T5_C"]) else 0.0)
    return out


def fig_t5_check(path, cols, steps, mask, models):
    """T5 against its prediction from T3 and T4 over the 480 s step (documents the mask)."""
    s2 = [s for s in steps if s["step"] == 2]
    if not s2 or 2 not in models:
        return
    s2, m = s2[0], models[2]
    t, sel = cols["t"], models[2]["inrun"]
    fig, axs = plt.subplots(2, 1, figsize=(12, 6.6), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    axs[0].plot(t[sel], cols["T5_C"][sel], color=COLORS["T5_C"], lw=0.9, label="T5 measured (raw)")
    axs[0].plot(t[sel], m["pred"][sel], color="black", lw=0.8, ls="--", label="predicted from T3 and T4")
    axs[1].plot(t[sel], m["res"][sel], color=COLORS["T5_C"], lw=0.7)
    for y in (0.35, -0.35):
        axs[1].axhline(y, color="#C0392B", ls=":", lw=1)
    for a, b, why in mask.get("T5_C", []):
        if a >= s2["t0"]:
            for ax in axs:
                ax.axvspan(a, b, color="#d62728", alpha=0.2, lw=0)
    axs[0].set_ylabel("T5 (°C)")
    axs[0].legend(fontsize=9, loc="upper right")
    axs[1].set_ylabel("T5 − prediction (°C)")
    axs[1].set_xlabel("Arduino time (s)")
    axs[1].set_ylim(-1.5, 4.5)
    axs[0].set_title(f"480 s step: T5 against its prediction from T3 and T4 (fit on the last two cycles, RMS "
                     f"{m['rms_fit']:.3f} °C); red = masked windows", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def run_stats(cols, data, steps):
    t = cols["t"]
    gaps = [(float(t[i]), int(round((t[i + 1] - t[i]) * 1000))) for i in np.flatnonzero(np.diff(t) > 0.75)]
    run = cols["run_state"] == 2
    return dict(n=len(t), minutes=float((t[-1] - t[0]) / 60), gaps=gaps,
                dupes=int(np.sum(np.diff(cols["time_ms"]) == 0)), restarts=int(np.sum(np.diff(cols["time_ms"]) < 0)),
                gaps_in_run=sum(1 for g, _ in gaps if steps[0]["t0"] <= g <= steps[-1]["t1"]),
                pwm_min=int(cols["signed_pwm"].min()), pwm_max=int(cols["signed_pwm"].max()),
                clip=int(np.sum(np.abs(cols["signed_pwm"]) >= 255)),
                t1_max=float(np.nanmax(cols["T1_C"][run])), tec_max=float(np.nanmax(cols["TEC_C"][run])),
                step_minutes={s["step"]: (s["t1"] - s["t0"]) / 60 for s in steps})


# ---------------------------------------------------------------------------
# tables and report
# ---------------------------------------------------------------------------

def write_tables(out_dir, results, steps, x):
    with open(os.path.join(out_dir, "cycle_fits.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["period_s", "cycle", "t_start_s", "channel", "B_C", "phi_rad", "mean_C",
                    "drift_C_per_cycle", "samples", "masked_samples", "in_settled_block"])
        for r in results:
            P = r["info"]["period"]
            for k in range(r["info"]["ncyc"]):
                for ch in CHANNELS:
                    f = r["cyc"][ch][k]
                    t0 = r["info"]["t0"] + k * P
                    if f is None:
                        w.writerow([f"{P:g}", k + 1, f"{t0:.1f}", label(ch), "", "", "", "", "", "", ""])
                    else:
                        w.writerow([f"{P:g}", k + 1, f"{t0:.1f}", label(ch), f"{f['B']:.4f}", f"{f['phi']:.4f}",
                                    f"{f['a']:.4f}", f"{f['drift'] * P:.4f}", f["n_window"] - f["n_masked"],
                                    f["n_masked"], int(k in r["block"])])
    with open(os.path.join(out_dir, "settled_blocks.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["period_s", "cycles_recorded", "first_settled_cycle", "last_settled_cycle", "settled_cycles",
                    "window_start_s", "window_end_s", "meets_5_cycle_minimum", "tolerance_B", "tolerance_phi_rad"])
        for r in results:
            b = r["block"]
            w.writerow([f"{r['info']['period']:g}", r["info"]["ncyc"], b[0] + 1, b[-1] + 1, len(b),
                        f"{r['ta']:.1f}", f"{r['tb']:.1f}", int(len(b) >= MIN_CYCLES), TOL_B, TOL_PHI])
    with open(os.path.join(out_dir, "profile_by_period.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["period_s", "channel", "x_m", "mean_C", "B_C", "sB_C", "phi_rad", "phi_unwrapped_rad", "sphi_rad",
                    "rms_resid_C", "B2_over_B1", "B3_over_B1", "cycles_used", "samples"])
        for r in results:
            f = r["fits"]
            for ch in CHANNELS:
                d = f[ch]
                i = ROD.index(ch) if ch in ROD else None
                w.writerow([f"{r['info']['period']:g}", label(ch), f"{x[i]:.4f}" if i is not None else "",
                            f"{d['a']:.4f}", f"{d['B']:.4f}", f"{d['sB']:.4f}", f"{d['phi']:.4f}",
                            f"{r['sp']['phi_u'][i]:.4f}" if i is not None else "", f"{d['sphi']:.4f}",
                            f"{d['rms']:.4f}", f"{d['h2']:.4f}", f"{d['h3']:.4f}", d["n_cycles"], d["n"]])
    with open(os.path.join(out_dir, "kappa_by_period.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["period_s", "omega_rad_s", "settled_cycles", "q_1_m", "sq_1_m", "qprime_1_m", "sqprime_1_m",
                    "kappa_m2_s", "skappa_m2_s", "nu_1_s", "snu_1_s", "k_W_mK", "sk_W_mK", "h_W_m2K", "sh_W_m2K",
                    "m_from_q_1_m", "m_mean_profile_1_m", "sm_mean_profile_1_m", "Bi_radial",
                    "finite_length_max_rel_diff", "chi2_lnB", "chi2_phi", "dof", "q_last5_1_m", "qprime_last5_1_m",
                    "kappa_last5_m2_s", "skappa_last5_m2_s"])
        for r in results:
            sp, dv, s5 = r["sp"], r["der"], r["sp5"]
            w.writerow([f"{r['info']['period']:g}", f"{r['w']:.6f}", len(r["block"]), f"{sp['q']:.3f}",
                        f"{sp['sq']:.3f}", f"{sp['qp']:.3f}", f"{sp['sqp']:.3f}", f"{sp['kappa']:.4e}",
                        f"{sp['skappa']:.2e}", f"{sp['nu']:.3e}", f"{sp['snu']:.2e}", f"{dv['k']:.1f}",
                        f"{dv['sk']:.1f}", f"{dv['h']:.1f}", f"{dv['sh']:.1f}", f"{dv['m_osc']:.3f}",
                        f"{dv['m_dc']:.3f}", f"{dv['sm_dc']:.3f}", f"{dv['Bi']:.2e}",
                        f"{float(np.max(dv['finite_rel'])):.3e}", f"{sp['chiA']:.2f}", f"{sp['chiP']:.2f}",
                        sp["dof"], f"{s5['q']:.3f}", f"{s5['qp']:.3f}", f"{s5['kappa']:.4e}", f"{s5['skappa']:.2e}"])
    with open(os.path.join(out_dir, "tracking_by_period.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["period_s", "Tb_C", "B_TEC_over_Tb", "TEC_lag_rad", "TEC_lag_s", "B_T1_over_Tb", "T1_lag_rad",
                    "T1_lag_s", "T1_B2_over_B1", "T1_rms_resid_C", "pwm_min", "pwm_max", "samples_at_pm255"])
        for r in results:
            tr = r["track"]
            w.writerow([f"{r['info']['period']:g}", f"{r['info']['tb']:g}", f"{tr['B_tec']:.4f}", f"{tr['lag_tec']:.4f}",
                        f"{tr['lag_tec_s']:.2f}", f"{tr['B_t1']:.4f}", f"{tr['lag_t1']:.4f}", f"{tr['lag_t1_s']:.2f}",
                        f"{tr['h2_t1']:.4f}", f"{tr['rms_t1']:.4f}", tr["pwm_min"], tr["pwm_max"], tr["clip"]])


def text_report(run, results, steps, hold, offsets_path, t_room, x, mask):
    L = []
    L.append(f"Run {os.path.relpath(run, REPO)}")
    L.append(f"python3 python/sammy_module8_angstrom_analysis.py {os.path.relpath(run, REPO)} --t-room {t_room:g}")
    L.append(f"Offsets (in memory only): {os.path.relpath(offsets_path, REPO) if offsets_path else 'none'}")
    L.append("Masks (removed from the fits, raw file unchanged):")
    for col, wins in mask.items():
        for a, b, why in wins:
            L.append(f"  {col[:-2]}  {a:g} to {b:g} s  {why}")
    L.append(f"Settling test: within {100 * TOL_B:g} % in B and {TOL_PHI:g} rad in phase of the block median, "
             f"counting back from the last cycle; wanted at least {MIN_CYCLES} settled cycles.")
    if hold:
        L.append(f"Hold step: TEC reached {steps[0]['ta'] - 0.5:.1f} C after {hold['t_reach']:.0f} s, "
                 f"max {hold['tec_max']:.2f} C (overshoot {hold['overshoot']:+.2f}), peak PWM {hold['pwm_max']}, "
                 f"T1 at the end {hold['t1_end']:.2f} C.")
    for r in results:
        info, sp, f = r["info"], r["sp"], r["fits"]
        L.append("")
        L.append("=" * 78)
        L.append(f"Period {info['period']:.0f} s (step {info['step']}), w = {r['w']:.5f} rad/s; "
                 f"{info['ncyc']} cycles recorded, settled block = cycles {r['block'][0] + 1} to "
                 f"{r['block'][-1] + 1} ({len(r['block'])} cycles), window {r['ta']:.1f} to {r['tb']:.1f} s")
        L.append(f"{'channel':>10} {'a (C)':>7} {'B (C)':>7} {'+/-':>6} {'phi':>7} {'+/-':>6} {'drift/cyc':>9} "
                 f"{'rms res':>7} {'B2/B1':>6} {'B3/B1':>6} {'cycles':>6}")
        for ch in CHANNELS:
            d = f[ch]
            L.append(f"{ch:>10} {d['a']:7.2f} {d['B']:7.3f} {d['sB']:6.3f} {d['phi']:+7.3f} {d['sphi']:6.3f} "
                     f"{d['drift_cycle']:+9.3f} {d['rms']:7.3f} {d['h2']:6.3f} {d['h3']:6.3f} {d['n_cycles']:6d}")
        L.append("Along the rod (T1 = x 0):")
        L.append(f"{'sensor':>7} {'x (mm)':>7} {'B (C)':>7} {'B/B1':>6} {'phase lag vs T1 (rad)':>22}")
        for i, ch in enumerate(ROD):
            L.append(f"{label(ch):>7} {x[i] * 1000:7.1f} {sp['B'][i]:7.3f} {sp['B'][i] / sp['B'][0]:6.3f} "
                     f"{sp['phi_u'][0] - sp['phi_u'][i]:22.3f}")
        dv = r["der"]
        L.append(f"q  = {sp['q']:.2f} +/- {sp['sq']:.2f} 1/m   (ln B against x; chi2 {sp['chiA']:.1f}/{sp['dof']})")
        L.append(f"q' = {sp['qp']:.2f} +/- {sp['sqp']:.2f} 1/m   (unwrapped phi against x; chi2 {sp['chiP']:.1f}/{sp['dof']})")
        L.append(f"kappa = w/(2 q q') = {sp['kappa']:.3e} +/- {sp['skappa']:.1e} m^2/s   "
                 f"({100 * (sp['kappa'] / KAPPA_HANDBOOK - 1):+.0f} % vs handbook {KAPPA_HANDBOOK:.2e})")
        L.append(f"nu = kappa (q^2 - q'^2) = {sp['nu']:.2e} +/- {sp['snu']:.1e} 1/s")
        L.append(f"k = rho cp kappa = {dv['k']:.0f} +/- {dv['sk']:.0f} W/(m K) (rho {RHO:g}, cp {CP:g}, handbook values);  "
                 f"h = rho cp (d/4) nu = {dv['h']:.1f} +/- {dv['sh']:.1f} W/(m^2 K)")
        L.append(f"Checks: finite-length max difference {100 * float(np.max(dv['finite_rel'])):.2f} % "
                 f"(per sensor: " + ", ".join(f"{100 * v:.2f}" for v in dv['finite_rel']) + " %);  "
                 f"Bi_radial = {dv['Bi']:.1e};  m from q = {dv['m_osc']:.2f} 1/m vs mean-profile m = "
                 f"{dv['m_dc']:.2f} +/- {dv['sm_dc']:.2f} 1/m")
        tr = r["track"]
        L.append(f"Tracking: B_TEC/Tb = {tr['B_tec']:.3f}, TEC lag {tr['lag_tec']:.3f} rad ({tr['lag_tec_s']:.1f} s); "
                 f"B_T1/Tb = {tr['B_t1']:.3f}, T1 lag {tr['lag_t1']:.3f} rad ({tr['lag_t1_s']:.1f} s); "
                 f"PWM {tr['pwm_min']} to {tr['pwm_max']}, samples at +/-255: {tr['clip']}")
        s5 = r["sp5"]
        L.append(f"Last five cycles ({r['block5'][0] + 1} to {r['block5'][-1] + 1}) instead of the settled block: "
                 f"q = {s5['q']:.2f}, q' = {s5['qp']:.2f}, kappa = {s5['kappa']:.3e} +/- {s5['skappa']:.1e}")
    ok = [r for r in results if len(r["block"]) >= MIN_CYCLES]
    L.append("")
    L.append("=" * 78)
    for name, sel in (("periods with >= 5 settled cycles", ok), ("all periods", results)):
        if not sel:
            continue
        k = np.array([r["sp"]["kappa"] for r in sel])
        s = np.array([r["sp"]["skappa"] for r in sel])
        wgt = 1 / s ** 2
        plist = ", ".join(f"{r['info']['period']:.0f}" for r in sel)
        L.append(f"kappa, {name} ({plist} s): weighted mean "
                 f"{np.sum(wgt * k) / np.sum(wgt):.3e} +/- {1 / math.sqrt(np.sum(wgt)):.1e}; plain mean {k.mean():.3e} "
                 f"with spread (sd) {k.std(ddof=1) if len(k) > 1 else float('nan'):.1e}")
    return "\n".join(L) + "\n"


def write_summary(path, run, results, steps, hold, models, rs, mask, nmasked):
    stamp = stamp_of(run)
    ok = [r for r in results if len(r["block"]) >= MIN_CYCLES]
    few = [r for r in results if len(r["block"]) < MIN_CYCLES]
    sm = ", ".join(f"{m:.1f}" for m in rs["step_minutes"].values())
    clip_txt = ("never reached ±255" if rs["clip"] == 0 else f"reached ±255 in {rs['clip']} samples")
    by_no = {s["step"]: s for s in steps}
    t5txt = ", ".join(f"{models[s]['max_outside']:.2f} °C in the {by_no[s]['period']:.0f} s step" for s in sorted(models))
    k = np.array([r["sp"]["kappa"] for r in results])
    s = np.array([r["sp"]["skappa"] for r in results])
    wgt = 1 / s ** 2
    kw, skw = np.sum(wgt * k) / np.sum(wgt), 1 / math.sqrt(np.sum(wgt))
    chi2k = float(np.sum(((k - kw) / s) ** 2))
    ok_txt = ", ".join(f"{r['info']['period']:.0f} s: {r['sp']['kappa'] * 1e5:.2f} ± {r['sp']['skappa'] * 1e5:.2f}" for r in ok) or "none"
    few_txt = ", ".join(f"{r['info']['period']:.0f} s ({len(r['block'])})" for r in few) or "none"
    blockrows = []
    for r in results:
        b, f = r["block"], r["fail"]
        why = ("none, all cycles settled" if f is None else
               f"cycle {f['cycle'] + 1}: {label(ROD[f['sensor']])} off by {f['dB']:+.1f} % and {f['dphi']:+.2f} rad")
        blockrows.append(f"| {r['info']['period']:.0f} | cycles {b[0] + 1} to {b[-1] + 1} ({len(b)}) | "
                         f"{'yes' if len(b) >= MIN_CYCLES else 'no'} | {why} |")
    sens = [f"| {r['info']['period']:.0f} | cycles {r['block5'][0] + 1} to {r['block5'][-1] + 1} | "
            f"{r['sp']['kappa'] * 1e5:.2f} ± {r['sp']['skappa'] * 1e5:.2f} | "
            f"{r['sp5']['kappa'] * 1e5:.2f} ± {r['sp5']['skappa'] * 1e5:.2f} | "
            f"{100 * (r['sp5']['kappa'] / r['sp']['kappa'] - 1) + 0.0:+.1f} % |" for r in results]
    sens = [s.replace("-0.0 %", "0.0 %") for s in sens]
    rows = []
    for r in results:
        sp, dv = r["sp"], r["der"]
        rows.append(f"| {r['info']['period']:.0f} | {len(r['block'])} of {r['info']['ncyc']} | {sp['q']:.2f} ± {sp['sq']:.2f} | "
                    f"{sp['qp']:.2f} ± {sp['sqp']:.2f} | {sp['kappa'] * 1e5:.2f} ± {sp['skappa'] * 1e5:.2f} | "
                    f"{sp['nu'] * 1e3:.2f} ± {sp['snu'] * 1e3:.2f} | {dv['k']:.0f} |")
    trk = []
    for r in results:
        tr = r["track"]
        trk.append(f"| {r['info']['period']:.0f} | {tr['B_tec']:.3f} | {tr['lag_tec_s']:.1f} | {tr['B_t1']:.3f} | "
                   f"{tr['lag_t1_s']:.1f} | {tr['pwm_min']} to {tr['pwm_max']} | {tr['clip']} |")
    chk = []
    for r in results:
        dv = r["der"]
        chk.append(f"| {r['info']['period']:.0f} | {100 * float(np.max(dv['finite_rel'])):.2f} % | {dv['Bi']:.1e} | "
                   f"{dv['m_osc']:.2f} | {dv['m_dc']:.2f} ± {dv['sm_dc']:.2f} |")
    kap = "\n".join(f"| {P} | {v[0] * 1e5:.2f} ± {v[1] * 1e5:.2f} | {v[2]:.2f} | {v[3]:.2f} |" for P, v in KAPIL.items())
    t21 = [float(r["der"]["a_profile"][1] - r["der"]["a_profile"][0]) for r in results]
    t21_txt = (f" In every mean profile T2 is warmer than T1 (by {min(t21):.2f} to {max(t21):.2f} °C), which conduction away from the TEC "
               "cannot produce, so the mean-profile slope is the weaker of the two estimates of m.") if min(t21) > 0 else ""
    photo_md = "\n\n".join(f"![{p['title']}](../images/{p['file']})\n\n*{p['title']}. On screen: {p['caption']}*"
                           for p in photo_info(load(run)))
    text = f"""# Module 8, Part I: Angstrom run of 10 November 2026 (SAMMY copy)

Summary of the 112-minute production run `{os.path.basename(run)}`, analysed with
`python/sammy_module8_angstrom_analysis.py`. Slides: `Phys39_Module_8_Angstrom_Slides_Sammy.pdf` in this folder.
Figures: `docs/figures/module_08_sammy/{stamp}_*.png`. Photos: `docs/images/module08_sammy_gui_*.jpg`. Tables and the text report: `data/module_08_sammy/analysis_{stamp}/`.
Kapil Naidu's acquisition code, analysis scripts and data are unchanged; everything here is an addition.

## What was run

- PI control of the TEC thermistor (Kp 12, Ki 0.2, cooling multiplier r = 2.771) with the sine setpoint
  40 ± 16 °C computed on the Arduino (`angstrom_tec_sammy`), room T = 24.3 °C (idle mean of T1 to T5).
- Schedule: 5 min hold at 40 °C, then 7 cycles at 480 s, 7 cycles at 240 s and 7 cycles at 100 s.
  All four steps ran to the end ({sm} min), the PWM {clip_txt} (range {rs['pwm_min']} to {rs['pwm_max']}), T1 peaked at
  {rs['t1_max']:.1f} °C and the TEC thermistor at {rs['tec_max']:.1f} °C during the schedule (limits 56 and 65 °C).
  The file has {rs['n']} records over {rs['minutes']:.1f} min with {rs['dupes']} duplicated times and {rs['restarts']} restarts;
  {len(rs['gaps'])} gaps longer than 0.75 s, {rs['gaps_in_run']} of them during the schedule.
- Rod: 6061-T6 aluminum, d = 12.757 mm, T1 to T5 at 0, 25.4, 50.8, 76.2 and 101.6 mm (±1 mm), tip 281.9 mm from T1.

## Photos of the run

Phone photos of the laptop screen during the run, straightened and cropped to the GUI window (metadata removed; the full-screen
originals are not in the repository). The numbers on screen are the logged values: the temperatures, the PWM and the stream's
valid-record count equal the CSV record with that number.

{photo_md}

## Data quality and what was masked

{nmasked} samples were set to `nan` in the fits (never in the raw file; mask: `{os.path.basename(run).replace('.csv', '_mask.csv')}`):

| Channel | Arduino time (s) | Why |
|---|---|---|
| T3, T4, T5 | 36 to 200 | leads being handled before the run (spikes up to 33, 117 and 102 °C) |
| T5 | 1860 to 2618 | reads 1 to 4 °C above its prediction from T3 and T4 (480 s step, cycles 3 and 4) |
| T5 | 3060 to 3141 | reads up to 3.6 °C above the prediction (480 s step, cycle 5) |

The prediction fits T5 from T3 and T4 and their slopes on the last two cycles of each step ({models[2]['rms_fit']:.3f} °C RMS
in the 480 s step). Outside the masked windows the largest departure of T5 from its prediction is {t5txt}; inside the
masked windows it reaches {models[2]['max_inside']:.1f} °C.

## Settling test

Counting back from the last cycle, a cycle joins the settled block while every rod sensor stays within 3 % in amplitude and
0.05 rad in phase of the block median (tolerances chosen for this analysis; the handout's tolerances were not available). The page asks for at least
five settled cycles at each of at least two usable periods.

| Period (s) | Settled block | Five or more | First rejected cycle |
|---|---|---|---|
{chr(10).join(blockrows)}

Under this test only the periods marked yes meet the minimum, so the others are supplementary. Why the blocks start where they do:

- 480 s: at t = 2598 s the TEC thermistor reading stepped up by 4 °C (decaying over about 10 s while the PI controller briefly
  commanded −174 PWM), and the T5 offset vanished at t = 2617 s. From then on every rod amplitude was about 10 % lower (T1 maximum
  41.6 to 41.9 °C in cycles 1 to 4, 39.6 to 39.9 °C in cycles 5 to 7) with the TEC amplitude unchanged. The ratios between sensors did
  not change (T5/T1 0.383 to 0.385 in cycles 2, 5 and 6), so the spatial slopes are not affected, but the early cycles belong to a
  different state. The cause is unknown.
- 100 s: T5's amplitude is only 0.44 °C, so 3 % is 0.013 °C, and its phase in cycle 4 is about 0.10 rad off the later cycles.

## Results

| Period (s) | Settled cycles | q (1/m) | q′ (1/m) | κ (10⁻⁵ m²/s) | ν (10⁻³ 1/s) | k (W/(m K)) |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

- κ (10⁻⁵ m²/s) from the periods that meet the five-cycle minimum: {ok_txt}.
- All three periods, weighted mean: **{kw * 1e5:.2f} ± {skw * 1e5:.2f} × 10⁻⁵ m²/s** (χ² = {chi2k:.1f} for {len(k) - 1} degrees
  of freedom, so the three periods are consistent with one value); plain mean {k.mean() * 1e5:.2f} with spread (sd) {k.std(ddof=1) * 1e5:.2f}.
- Handbook 6061-T6 (k = 167 W/(m K), ρ = 2700 kg/m³, cp = 896 J/(kg K)): κ = 6.9 × 10⁻⁵ m²/s, so the weighted mean is
  {100 * (kw / KAPPA_HANDBOOK - 1):.0f} % above it, as in Kapil's data. k uses the handbook ρ and cp and inherits this offset;
  κ is the quantity the Angstrom method measures directly.
- ν = κ(q² − q′²) is a small difference of two nearly equal numbers, so its relative uncertainty is large.

Using the last five cycles of every period (Kapil's rule) instead of the settled block changes κ as follows:

| Period (s) | Last five cycles | κ, settled block (10⁻⁵ m²/s) | κ, last five cycles | Change |
|---|---|---|---|---|
{chr(10).join(sens)}

The choice makes no difference at 240 s and 100 s within the errors. At 480 s the last five cycles straddle the disturbance at
t = 2598 s (and T5 loses cycles 3 and 4 to the mask), so that fit mixes two states and is biased low; the settled block avoids this.

Kapil's PI fits (shared branch, 2 and 4 Nov, same rod):

| Period (s) | κ (10⁻⁵ m²/s) | q (1/m) | q′ (1/m) |
|---|---|---|---|
{kap}

## Model-validity checks

| Period (s) | Finite-length difference (max) | Radial Biot number | m from √(q²−q′²) (1/m) | m from the mean profile (1/m) |
|---|---|---|---|---|
{chr(10).join(chk)}

The semi-infinite model is a good approximation for these periods (finite-length difference small, Biot number far below 0.1).
The side-loss rate from the mean temperature profile does not match the one from q and q′, so ν and h should be quoted with caution.{t21_txt}

## Controller tracking (PI)

Hold step: TEC reached 39.5 °C after {hold['t_reach']:.0f} s with {hold['overshoot']:+.2f} °C overshoot, peak PWM {hold['pwm_max']}.

| Period (s) | B_TEC/Tb | TEC lag (s) | B_T1/Tb | T1 lag (s) | PWM range | Samples at ±255 |
|---|---|---|---|---|---|---|
{chr(10).join(trk)}

## Limits of this run

- Only the PI mode was run. The page's open-loop and P comparisons, the raw sinusoidal PWM trials (S18.3 and S18.4), the gain tuning
  at 200 s and 500 s, and the P-versus-PI simulation are not covered by this file.
- Periods with fewer than five settled cycles: {few_txt}. Their κ agrees with the others (χ² above), but the settled-cycle
  count is below the page's minimum.
- T5 needed masking in the 480 s step; its amplitude ratio to T1 is the same (0.383 to 0.385) in cycle 2, before the problem, and in cycles 5 and 6, after it.
- The tolerances of the settling test were chosen for this analysis, and the semi-infinite-rod formulas carry a finite-length bias of up to
  {100 * max(float(np.max(r['der']['finite_rel'])) for r in results):.1f} % in the amplitude ratio at T5 for the longest period.

## Reproduce

```bash
python3 python/sammy_module8_angstrom_analysis.py data/module_08_sammy/{os.path.basename(run)}
python3 python/build_sammy_module8_slides.py data/module_08_sammy/{os.path.basename(run)}
```

## AI assistance

The acquisition GUI changes, the analysis script, the figures, the slides and this summary were produced with GitHub Copilot
assistance and reviewed against Kapil Naidu's `angstrom_fit.py` method and the Module 8 study guide.
"""
    with open(path, "w") as fh:
        fh.write(text)


def stamp_of(path):
    return os.path.splitext(os.path.basename(path))[0].replace("sammy_angstrom_live_", "")


def photo_info(cols):
    """Per photo: file path, photo id, short title and a caption built from the logged record at the time on screen."""
    out = []
    for fname, tt, pid, clock in PHOTOS:
        k = int(np.argmin(np.abs(cols["t"] - tt)))
        temps = ", ".join(f"T{i} {cols[f'T{i}_C'][k]:.2f}" for i in range(1, 6))
        title = f"{pid}, {clock}: step {int(cols['step'][k])} ({cols['period_s'][k]:.0f} s period), t = {cols['t'][k]:.1f} s"
        cap = (f"setpoint {cols['setpoint_C'][k]:.2f} °C, TEC {cols['TEC_C'][k]:.2f} °C, {temps} °C; applied PWM "
               f"{int(cols['signed_pwm'][k]):+d} (record {k + 1}).")
        out.append(dict(path=os.path.join(IMAGE_DIR, fname), file=fname, id=pid, title=title, caption=cap, t=float(cols["t"][k])))
    return out


def write_run_json(path, stamp, rs, models, nmasked, hold):
    keep = ("rms_fit", "max_outside", "max_inside")
    out = dict(stamp=stamp, records=rs["n"], minutes=round(rs["minutes"], 2), duplicated=rs["dupes"], restarts=rs["restarts"],
               gaps=len(rs["gaps"]), gaps_in_schedule=rs["gaps_in_run"], pwm_min=rs["pwm_min"], pwm_max=rs["pwm_max"],
               pwm_clipped_samples=rs["clip"], t1_max_C=round(rs["t1_max"], 2), tec_max_C=round(rs["tec_max"], 2),
               step_minutes={str(a): round(b, 2) for a, b in rs["step_minutes"].items()}, masked_samples=int(nmasked),
               t5_prediction={str(a): {key: round(m[key], 4) for key in keep} for a, m in models.items()},
               hold={key: round(v, 3) for key, v in hold.items()} if hold else None)
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--mask")
    ap.add_argument("--offsets", default=OFFSETS)
    ap.add_argument("--t-room", type=float, default=24.3)
    ap.add_argument("--sensor-map", default=SENSOR_MAP)
    ap.add_argument("--geometry", default=GEOMETRY)
    ap.add_argument("--out-dir")
    ap.add_argument("--fig-dir", default=FIG_DIR)
    ap.add_argument("--summary", default=None, help="markdown summary path (default in docs/sammy_module_08_guide)")
    a = ap.parse_args()

    run = os.path.abspath(a.run)
    stamp = stamp_of(run)
    mask_path = a.mask or run.replace(".csv", "_mask.csv")
    out_dir = a.out_dir or os.path.join(DATA_DIR, f"analysis_{stamp}")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(a.fig_dir, exist_ok=True)

    cols = load(run)
    t = cols["t"]
    offsets = load_offsets(a.offsets)
    mask = load_mask(mask_path)
    raw, data, masked = prepare(cols, offsets, mask)
    x, dx = load_positions(a.sensor_map)
    geom = load_geometry(a.geometry)
    steps = find_steps(cols)
    hold = hold_metrics(cols, data, steps[0]) if steps and steps[0]["tb"] == 0 else None

    results = []
    for info in [s for s in steps if s["tb"] > 0]:
        cyc = cycle_fits(t, data, info)
        block, B, PH, fail = settled_block(cyc, info["ncyc"])
        blk = analyse_block(t, data, info, cyc, block)
        sp = spatial(blk["fits"], blk["w"], x, dx)
        block5 = list(range(info["ncyc"] - min(5, info["ncyc"]), info["ncyc"]))
        sp5 = spatial(analyse_block(t, data, info, cyc, block5)["fits"], blk["w"], x, dx)
        der = derived(sp, x, geom, blk["fits"], a.t_room)
        f = blk["fits"]
        Tb = f["setpoint_C"]["B"]
        sel = blk["sel"]
        pw = cols["signed_pwm"][sel]
        lag_tec = float(wrap(f["setpoint_C"]["phi"] - f["TEC_C"]["phi"]))
        lag_t1 = float(wrap(f["setpoint_C"]["phi"] - f["T1_C"]["phi"]))
        track = dict(B_tec=f["TEC_C"]["B"] / Tb, lag_tec=lag_tec, lag_tec_s=lag_tec / blk["w"],
                     B_t1=f["T1_C"]["B"] / Tb, lag_t1=lag_t1, lag_t1_s=lag_t1 / blk["w"], h2_t1=f["T1_C"]["h2"],
                     rms_t1=f["T1_C"]["rms"], pwm_min=int(pw.min()), pwm_max=int(pw.max()),
                     clip=int(np.sum(np.abs(pw) >= 255)))
        results.append(dict(info=info, cyc=cyc, block=block, B_cyc=B, PH_cyc=PH, sp=sp, der=der, track=track,
                            sp5=sp5, block5=block5, fail=fail, cols_pwm=cols["signed_pwm"], **blk))
        print(f"{info['period']:.0f} s: block cycles {block[0] + 1}-{block[-1] + 1} ({len(block)}), "
              f"q {sp['q']:.2f}, q' {sp['qp']:.2f}, kappa {sp['kappa']:.3e} +/- {sp['skappa']:.1e}")

    nmasked = write_clean_csv(run, os.path.join(out_dir, "clean_run_data.csv"), mask)
    write_tables(out_dir, results, steps, x)
    report = text_report(run, results, steps, hold, a.offsets, a.t_room, x, mask)
    with open(os.path.join(out_dir, "report.txt"), "w") as fh:
        fh.write(report)

    fig = lambda name: os.path.join(a.fig_dir, f"{stamp}_{name}.png")
    fig_overview(fig("run_overview"), cols, data, masked, steps, mask)
    for r in results:
        fig_cycles(fig(f"cycles_{r['info']['period']:.0f}s"), r, t, data, raw, r["info"])
    fig_spatial(fig("spatial_fits"), results, x)
    fig_settling(fig("settling"), results)
    fig_kappa(fig("kappa_vs_period"), results)
    fig_length(fig("characteristic_length"), results)
    fig_profile(fig("mean_profile"), results, x, a.t_room)
    fig_tracking(fig("tracking"), results, t, data)
    models = t5_models(cols, raw, masked, steps)
    fig_t5_check(fig("t5_mask_check"), cols, steps, mask, models)

    summary = a.summary or os.path.join(GUIDE_DIR, "Sammy_Module_8_Production_Run_Summary.md")
    os.makedirs(os.path.dirname(summary), exist_ok=True)
    rs = run_stats(cols, data, steps)
    write_run_json(os.path.join(out_dir, "run_summary.json"), stamp, rs, models, nmasked, hold)
    write_summary(summary, run, results, steps, hold, models, rs, mask, nmasked)
    print(report)
    print(f"Wrote tables and report in {os.path.relpath(out_dir, REPO)}, figures in "
          f"{os.path.relpath(a.fig_dir, REPO)}, summary {os.path.relpath(summary, REPO)}")


if __name__ == "__main__":
    main()
