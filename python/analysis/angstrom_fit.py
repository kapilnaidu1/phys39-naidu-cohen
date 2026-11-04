#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I. Angstrom fits for one settled stretch of a run.
Naidu / Cohen

    python3 python/analysis/angstrom_fit.py data/module_08/angstrom_live_....csv \
        --mode PI --period 100 [--cycles 5] [--t-end S] \
        [--offsets data/module_08/calibration_rod_run_20261026_112627.csv]

    python3 python/analysis/angstrom_fit.py <run> --compare --period 100 [--cycles 3]
        (open loop vs P vs PI at the same drive)

WHAT IT DOES
  1. Picks the segment of the run with run_state 1, the given control mode
     and the given period, and keeps its last N complete cycles (or the N
     cycles ending at --t-end).
  2. Per channel (setpoint, TEC, T1..T5) fits, by least squares,
         T(t) = a + B cos(w t + phi) + c (t - tmid)
     the course's convention plus a straight-line drift term, so a slowly
     warming mean does not leak into B and phi. With this convention a
     sensor that lags has a smaller (more negative) phi.
     Uncertainties of B and phi come from the scatter of the same fit done
     cycle by cycle (sd / sqrt(N)); the one-shot least-squares errors would
     be too small because neighbouring 0.5 s readings are correlated.
     The cycle-by-cycle values are printed too: they are the settling test.
  3. Spatial fits along the rod (T1..T5 at the sensor-map positions):
         ln B = ln B0 - q x            (weighted line)
         phi  = phi0 - q' x            (phase unwrapped going up the rod)
     then  kappa = w / (2 q q'),  nu = kappa (q^2 - q'^2).
  4. Base-tracking numbers: B_TEC / Tb and B_T1 / Tb, and the lag of TEC
     and T1 behind the requested setpoint.
  5. Waveform quality: rms residual and the 2nd and 3rd harmonic amplitudes
     relative to the fundamental.

Offsets (calibration file from rod_calibration.py) are applied in memory;
the raw file is never changed. Positions come from data/module_08/sensor_map.csv
(rows R1..R5 = T1..T5).

OUTPUT
  data/module_08/angstrom_fit_<run>_<mode>_<period>s.txt / .csv
  docs/figures/module_08/angstrom_fit_<run>_<mode>_<period>s.png
  with --compare: data/module_08/angstrom_compare_<run>_<period>s.txt
"""

import argparse
import csv
import io
import os
from contextlib import redirect_stdout

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(REPO, "data", "module_08")
FIG_DIR = os.path.join(REPO, "docs", "figures", "module_08")
SENSOR_MAP = os.path.join(DATA_DIR, "sensor_map.csv")
ROD = ["T1_C", "T2_C", "T3_C", "T4_C", "T5_C"]
CHANNELS = ["setpoint_C", "TEC_C"] + ROD
COLORS = {"setpoint_C": "#7f7f7f", "TEC_C": "#000000", "T1_C": "#1f77b4",
          "T2_C": "#ff7f0e", "T3_C": "#2ca02c", "T4_C": "#9467bd",
          "T5_C": "#8c564b"}


def load(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    cols = {}
    for k in rows[0]:
        if k == "control_mode":
            cols[k] = np.array([r[k] for r in rows])
        else:
            cols[k] = np.array([float(r[k]) for r in rows])
    cols["t"] = cols["time_ms"] / 1000.0
    return cols


def load_offsets(path):
    """{column: (intercept, gain)}; base -> TEC_C, R1..R5 -> T1_C..T5_C."""
    if not path:
        return {}
    out = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            ch = r["channel"].strip()
            col = "TEC_C" if ch == "base" else (f"T{ch[1:]}_C" if ch.startswith("R") else None)
            if col is None:
                continue
            if r.get("gain"):
                out[col] = (float(r["intercept_C"]), float(r["gain"]))
            else:
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


def segment(cols, mode, period):
    """Indices of the last contiguous stretch with run_state 1, this mode
    and this period."""
    ok = np.isin(cols["run_state"], (1, 2)) & (cols["control_mode"] == mode) & \
         (np.abs(cols["period_s"] - period) < 1e-6)
    idx = np.flatnonzero(ok)
    if idx.size == 0:
        raise SystemExit(f"no running {mode} segment at {period:g} s")
    breaks = np.flatnonzero(np.diff(idx) > 1)
    start = idx[breaks[-1] + 1] if breaks.size else idx[0]
    return np.arange(start, idx[-1] + 1)


def sine_fit(t, y, w, harmonics=1):
    """Least squares a + sum_k [s_k sin(k w t) + c_k cos(k w t)] + d (t - tmid).
    Returns a, B, phi (course convention a + B cos(w t + phi)), the higher
    harmonic amplitudes, and the residuals."""
    tm = t.mean()
    cols = [np.ones_like(t)]
    for k in range(1, harmonics + 1):
        cols += [np.sin(k * w * t), np.cos(k * w * t)]
    cols.append(t - tm)
    X = np.column_stack(cols)
    p, *_ = np.linalg.lstsq(X, y, rcond=None)
    s1, c1 = p[1], p[2]
    B = np.hypot(s1, c1)
    phi = np.arctan2(-s1, c1)          # B cos(wt + phi) = B cos phi cos - B sin phi sin
    higher = [np.hypot(p[2 * k - 1], p[2 * k]) for k in range(2, harmonics + 1)]
    return p[0], B, phi, higher, y - X @ p, p[-1]


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def analyse(cols, offsets, mode, period, ncyc, t_end=None):
    idx = segment(cols, mode, period)
    t = cols["t"][idx]
    end = t[-1] if t_end is None else t_end
    start = end - ncyc * period
    if start < t[0]:
        raise SystemExit(f"only {(end - t[0]) / period:.1f} cycles available")
    keep = (t >= start) & (t <= end)
    t = t[keep]
    sel = idx[keep]
    w = 2 * np.pi / period
    res = {"t": t, "start": start, "end": end, "w": w, "fits": {}}
    for ch in CHANNELS:
        y = cols[ch][sel].astype(float)
        if ch in offsets:
            a0, b = offsets[ch]
            y = (y - a0) / b
        a, B, phi, higher, resid, drift = sine_fit(t, y, w, harmonics=3)
        per = []
        for k in range(ncyc):
            m = (t >= start + k * period) & (t < start + (k + 1) * period)
            _, Bk, pk, _, _, _ = sine_fit(t[m], y[m], w)
            per.append((Bk, pk))
        per = np.array(per)
        dph = wrap(per[:, 1] - phi)
        sB = per[:, 0].std(ddof=1) / np.sqrt(ncyc) if ncyc > 1 else np.nan
        sphi = dph.std(ddof=1) / np.sqrt(ncyc) if ncyc > 1 else np.nan
        res["fits"][ch] = dict(a=a, B=B, phi=phi, sB=sB, sphi=sphi,
                               h2=higher[0] / B, h3=higher[1] / B,
                               rms=np.sqrt(np.mean(resid ** 2)),
                               drift=drift * period, per=per, y=y,
                               resid=resid)
    pw = cols["signed_pwm"][sel]
    res["pwm"] = (pw.min(), pw.max())
    return res


def spatial(res, x, dx):
    f = res["fits"]
    B = np.array([f[c]["B"] for c in ROD])
    sB = np.array([f[c]["sB"] for c in ROD])
    phi = np.array([f[c]["phi"] for c in ROD])
    sphi = np.array([f[c]["sphi"] for c in ROD])
    phi_u = phi[0] + np.unwrap(phi - phi[0])        # going up the rod
    lnB = np.log(B)
    # point errors: cycle-to-cycle scatter plus the position uncertainty dx,
    # which moves ln B by q dx and phi by q' dx (first guess from a plain line)
    q0 = -np.polyfit(x, lnB, 1)[0]
    qp0 = -np.polyfit(x, phi_u, 1)[0]
    s_lnB = np.sqrt((sB / B) ** 2 + (q0 * dx) ** 2 + 1e-8)
    s_phi = np.sqrt(sphi ** 2 + (qp0 * dx) ** 2 + 1e-8)

    def wline(x, y, s):
        W = 1.0 / s ** 2
        A = np.column_stack([np.ones_like(x), x])
        cov = np.linalg.inv(A.T @ (A * W[:, None]))
        p = cov @ (A.T @ (W * y))
        chi2 = float(np.sum(W * (y - A @ p) ** 2))
        dof = len(x) - 2
        scale = max(chi2 / dof, 1.0) if dof > 0 else 1.0
        return p, np.sqrt(np.diag(cov) * scale), chi2, dof, y - A @ p

    pA, eA, chiA, dof, rA = wline(x, lnB, s_lnB)
    pP, eP, chiP, _, rP = wline(x, phi_u, s_phi)
    q, sq = -pA[1], eA[1]
    qp, sqp = -pP[1], eP[1]
    w = res["w"]
    kappa = w / (2 * q * qp)
    skappa = kappa * np.hypot(sq / q, sqp / qp)
    nu = kappa * (q ** 2 - qp ** 2)
    snu = np.sqrt((nu / kappa * skappa) ** 2 + (kappa * 2 * q * sq) ** 2 +
                  (kappa * 2 * qp * sqp) ** 2)
    return dict(B=B, sB=np.sqrt(sB ** 2 + (q0 * dx * B) ** 2), phi_u=phi_u,
                sphi=s_phi, q=q, sq=sq, qp=qp,
                sqp=sqp, kappa=kappa, skappa=skappa, nu=nu, snu=snu,
                chiA=chiA, chiP=chiP, dof=dof, rA=rA, rP=rP, pA=pA, pP=pP)


def report(run, res, sp, x, mode, period, ncyc, offsets_path):
    f = res["fits"]
    Tb = f["setpoint_C"]["B"]
    print(f"Run {run}")
    print(f"Mode {mode}, period {period:g} s, w = {res['w']:.5f} rad/s; window "
          f"{res['start']:.1f} to {res['end']:.1f} s ({ncyc} complete cycles)")
    print(f"Offsets: {offsets_path or 'none (raw values)'}")
    print(f"Applied PWM range in the window: {res['pwm'][0]:.0f} to {res['pwm'][1]:.0f}")
    print("\nPer channel: T = a + B cos(w t + phi) + drift; errors from cycle-to-cycle scatter")
    print(f"{'channel':>10} {'a (C)':>7} {'B (C)':>7} {'+/-':>6} {'phi':>7} {'+/-':>6} "
          f"{'drift/cyc':>9} {'rms res':>7} {'B2/B1':>6} {'B3/B1':>6}")
    for ch in CHANNELS:
        d = f[ch]
        print(f"{ch:>10} {d['a']:7.2f} {d['B']:7.3f} {d['sB']:6.3f} {d['phi']:+7.3f} "
              f"{d['sphi']:6.3f} {d['drift']:+9.3f} {d['rms']:7.3f} {d['h2']:6.3f} {d['h3']:6.3f}")
    print("\nSettling test, cycle by cycle (B in C, phi in rad):")
    for ch in CHANNELS[1:]:
        per = f[ch]["per"]
        print(f"{ch:>10} " + "  ".join(f"{b:6.3f}/{p:+.2f}" for b, p in per))
    lag_tec = wrap(f["setpoint_C"]["phi"] - f["TEC_C"]["phi"])
    lag_t1 = wrap(f["setpoint_C"]["phi"] - f["T1_C"]["phi"])
    print(f"\nBase tracking: B_TEC/Tb = {f['TEC_C']['B'] / Tb:.3f}, TEC lag "
          f"{lag_tec:.3f} rad ({lag_tec / res['w']:.1f} s); B_T1/Tb = "
          f"{f['T1_C']['B'] / Tb:.3f}, T1 lag {lag_t1:.3f} rad ({lag_t1 / res['w']:.1f} s)")
    if sp is None:
        return
    print("\nAlong the rod (T1 = x 0):")
    print(f"{'sensor':>7} {'x (mm)':>7} {'B (C)':>7} {'B/B1':>6} {'phase lag vs T1 (rad)':>22}")
    for i, ch in enumerate(ROD):
        print(f"{ch[:2]:>7} {x[i] * 1000:7.1f} {sp['B'][i]:7.3f} {sp['B'][i] / sp['B'][0]:6.3f} "
              f"{sp['phi_u'][0] - sp['phi_u'][i]:22.3f}")
    print(f"\nq  = {sp['q']:.2f} +/- {sp['sq']:.2f} 1/m   (ln B against x; chi2 {sp['chiA']:.1f}/{sp['dof']})")
    print(f"q' = {sp['qp']:.2f} +/- {sp['sqp']:.2f} 1/m   (unwrapped phi against x; chi2 {sp['chiP']:.1f}/{sp['dof']})")
    print(f"kappa = w/(2 q q') = {sp['kappa']:.3e} +/- {sp['skappa']:.1e} m^2/s")
    print(f"nu = kappa (q^2 - q'^2) = {sp['nu']:.2e} +/- {sp['snu']:.1e} 1/s")
    if sp["q"] <= sp["qp"]:
        print("NOTE: q <= q' gives nu <= 0; check settling, sensors and the semi-infinite assumption.")
    print("Point errors: cycle-to-cycle scatter combined with the sensor-map position "
          "uncertainty. Slope errors are scaled by sqrt(chi2/dof) when that exceeds 1. "
          "The fits assume a semi-infinite rod; see the Module 7 finite-length check.")


def figure(path, res, sp, x, mode, period):
    f = res["fits"]
    fig = plt.figure(figsize=(13, 8))
    ax = fig.add_subplot(2, 2, (1, 2))
    t = res["t"] - res["start"]
    for ch in CHANNELS:
        d = f[ch]
        ax.plot(t, d["y"], color=COLORS[ch], lw=1.0, label=ch.replace("_C", ""))
        ax.plot(t, d["y"] - d["resid"], color=COLORS[ch], lw=0.8, ls="--")
    ax.set_xlabel("time in the fit window (s)")
    ax.set_ylabel("°C (offsets applied)")
    ax.set_title(f"{mode}, period {period:g} s: data (solid) and fits (dashed)", fontsize=10)
    ax.legend(fontsize=8, ncol=7)
    ax.grid(True, color="#E4E4E4")
    if sp is not None:
        a1 = fig.add_subplot(2, 2, 3)
        a1.errorbar(x * 1000, sp["B"], yerr=sp["sB"], fmt="o", color="#1F4E79")
        xx = np.linspace(0, x.max() * 1.05, 50)
        a1.plot(xx * 1000, np.exp(sp["pA"][0] - sp["q"] * xx), color="#1F4E79")
        a1.set_yscale("log")
        a1.set_xlabel("x from T1 (mm)")
        a1.set_ylabel("oscillation amplitude B (°C, log)")
        a1.set_title(f"q = {sp['q']:.1f} ± {sp['sq']:.1f} m⁻¹", fontsize=10)
        a1.grid(True, which="both", color="#E4E4E4")
        a2 = fig.add_subplot(2, 2, 4)
        a2.errorbar(x * 1000, sp["phi_u"], yerr=sp["sphi"], fmt="s", color="#C0392B")
        a2.plot(xx * 1000, sp["pP"][0] - sp["qp"] * xx, color="#C0392B")
        a2.set_xlabel("x from T1 (mm)")
        a2.set_ylabel("unwrapped phase φ (rad)")
        a2.set_title(f"q′ = {sp['qp']:.1f} ± {sp['sqp']:.1f} m⁻¹;  "
                     f"κ = {sp['kappa']:.2e} m²/s", fontsize=10)
        a2.grid(True, color="#E4E4E4")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def compare(run, cols, offsets, period, ncyc):
    print(f"Run {run}: open loop vs P vs PI at period {period:g} s, last {ncyc} "
          f"complete cycles of each segment; offsets applied")
    print(f"{'mode':>4} {'chan':>5} {'mean':>7} {'B':>6} {'B/Tb':>6} {'lag vs set (rad)':>16} "
          f"{'up-swing':>8} {'down':>6} {'rms res':>7} {'B2/B1':>6} {'PWM range':>12}")
    for mode in ("OL", "P", "PI"):
        try:
            res = analyse(cols, offsets, mode, period, ncyc)
        except SystemExit as e:
            print(f"{mode:>4}: {e}")
            continue
        f = res["fits"]
        Tb = f["setpoint_C"]["B"]
        for ch in ("TEC_C", "T1_C"):
            d = f[ch]
            y = d["y"]
            up, down = y.max() - d["a"], d["a"] - y.min()
            lag = wrap(f["setpoint_C"]["phi"] - d["phi"])
            print(f"{mode:>4} {ch[:-2]:>5} {d['a']:7.2f} {d['B']:6.2f} {d['B'] / Tb:6.3f} "
                  f"{lag:16.3f} {up:8.2f} {down:6.2f} {d['rms']:7.3f} {d['h2']:6.3f} "
                  f"{res['pwm'][0]:5.0f} to {res['pwm'][1]:4.0f}")
    print("up-swing / down = max - mean and mean - min over the window (heating/cooling symmetry).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--mode", default="PI", choices=["OL", "P", "PI"])
    ap.add_argument("--period", type=float, required=True)
    ap.add_argument("--cycles", type=int, default=5)
    ap.add_argument("--t-end", type=float)
    ap.add_argument("--offsets")
    ap.add_argument("--sensor-map", default=SENSOR_MAP)
    ap.add_argument("--compare", action="store_true")
    a = ap.parse_args()

    cols = load(a.run)
    offsets = load_offsets(a.offsets)
    stem = os.path.splitext(os.path.basename(a.run))[0]
    os.makedirs(FIG_DIR, exist_ok=True)
    out = io.StringIO()
    if a.compare:
        with redirect_stdout(out):
            compare(a.run, cols, offsets, a.period, a.cycles)
        text = out.getvalue()
        print(text)
        path = os.path.join(DATA_DIR, f"angstrom_compare_{stem}_{a.period:g}s.txt")
        with open(path, "w") as fh:
            fh.write(f"python3 python/analysis/angstrom_fit.py {a.run} --compare "
                     f"--period {a.period:g} --cycles {a.cycles}"
                     + (f" --offsets {a.offsets}" if a.offsets else "") + "\n\n" + text)
        print(f"Wrote {path}")
        return

    res = analyse(cols, offsets, a.mode, a.period, a.cycles, a.t_end)
    x, dx = load_positions(a.sensor_map)
    sp = spatial(res, x, dx)
    with redirect_stdout(out):
        report(a.run, res, sp, x, a.mode, a.period, a.cycles, a.offsets)
    text = out.getvalue()
    print(text)
    tag = f"{stem}_{a.mode}_{a.period:g}s"
    with open(os.path.join(DATA_DIR, f"angstrom_fit_{tag}.txt"), "w") as fh:
        fh.write(f"python3 python/analysis/angstrom_fit.py {a.run} --mode {a.mode} "
                 f"--period {a.period:g} --cycles {a.cycles}"
                 + (f" --t-end {a.t_end:g}" if a.t_end else "")
                 + (f" --offsets {a.offsets}" if a.offsets else "") + "\n\n" + text)
    with open(os.path.join(DATA_DIR, f"angstrom_fit_{tag}.csv"), "w") as fh:
        fh.write("channel,x_m,mean_C,B_C,sB_C,phi_rad,sphi_rad,rms_resid_C,B2_over_B1,B3_over_B1\n")
        for ch in CHANNELS:
            d = res["fits"][ch]
            xi = x[ROD.index(ch)] if ch in ROD else float("nan")
            fh.write(f"{ch},{xi:.4f},{d['a']:.4f},{d['B']:.4f},{d['sB']:.4f},"
                     f"{d['phi']:.4f},{d['sphi']:.4f},{d['rms']:.4f},{d['h2']:.4f},{d['h3']:.4f}\n")
    fig = os.path.join(FIG_DIR, f"angstrom_fit_{tag}.png")
    figure(fig, res, sp, x, a.mode, a.period)
    print(f"Wrote angstrom_fit_{tag}.txt/.csv in data/module_08 and {os.path.relpath(fig, REPO)}")


if __name__ == "__main__":
    main()
