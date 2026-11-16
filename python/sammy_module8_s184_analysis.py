#!/usr/bin/env python3
"""
Phys 39 Module 8, S18.4: analysis of a positive-only raw PWM run, u = U0 + U sin(wt).  SAMMY copy.

    python3 python/sammy_module8_s184_analysis.py data/module_08_sammy/sammy_angstrom_live_20261116_111935_phase2_raw100s.csv \
        [--t-amb 23.05] [--t-room 22.7]

The input is one RAW schedule. The plan of 16 Nov writes three schedules into one CSV, so cut the phase out by time_ms first
(rows between the "PLAN phase" notes). Cycles are fitted and the settled block chosen as in sammy_module8_angstrom_analysis.py,
with the applied PWM in the place of the setpoint channel. The TEC response is compared with
  - the prediction of python/sammy_module8_s184_page.py (Module 6 one-lump model fitted to the S18.3 run), and
  - the S18.3 sweep at the same period (u = 50 sin wt), to see which asymmetries come from reversing the current.
Writes data/module_08_sammy/analysis_<stamp>/ (report.txt, cycle_fits.csv) and docs/figures/module_08_sammy/<stamp>_s184_*.png.
"""

import argparse
import csv
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sammy_module8_s183_analysis as S  # noqa: E402  (hfit, one-lump simulation, S18.3 analysis)
import sammy_module8_s184_page as PG  # noqa: E402  (S18.3 run path, prediction formulas, room temperature of the page)

an = S.an
ROD = an.ROD
TARGET = 40.0                                   # C: S18.4 asks for a mean TEC temperature near this


def fig_overview(path, ts, TEC, rod, u, Tm, P, skip, pred, title):
    fig, axs = plt.subplots(3, 1, figsize=(12, 8), sharex=True, gridspec_kw={"height_ratios": [2.6, 1, 1]})
    for ax in axs:
        ax.axvspan(0, skip * P, facecolor="none", edgecolor="#999", hatch="//", lw=0)
    axs[0].plot(ts, TEC, color="black", lw=1.4, label="TEC measured")
    for ch in ROD:
        axs[0].plot(ts, rod[ch], color=an.COLORS[ch], lw=0.9, label=an.label(ch))
    axs[0].plot(ts, Tm, color="#1F77B4", ls="--", lw=1.3, label="one-lump prediction (S18.3 fit)")
    axs[0].axhline(pred["mean"], color="#C0392B", ls=":", lw=1.2, label=f"predicted mean {pred['mean']:.1f} °C")
    axs[0].axhline(TARGET, color="#2a9d8f", ls="--", lw=1.1, label=f"target {TARGET:g} °C")
    axs[0].set_ylabel("temperature (°C)")
    axs[0].set_ylim(min(float(np.min(v)) for v in rod.values()) - 3.2, None)
    axs[0].legend(fontsize=8, ncol=4, loc="lower right")
    axs[0].set_title(title, fontsize=11)
    axs[1].plot(ts, TEC - Tm, color="#555555", lw=0.9)
    axs[1].axhline(0, color="#999999", lw=0.8)
    axs[1].set_ylabel("TEC − prediction (°C)")
    axs[2].plot(ts, u, color="#202020", lw=0.9)
    axs[2].axhline(0, color="#C0392B", ls=":", lw=1)
    axs[2].set_ylabel("applied PWM (counts)")
    axs[2].set_xlabel("time since START schedule (s); hatched = start-up cycles left out of the fits")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_shape(path, r3, tt, T, fT, lag, w, a, P):
    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    x = np.linspace(0, 2 * math.pi, 400)
    ph3 = (r3["w"] * (r3["tt"] - r3["a"]) - r3["lag"]) % (2 * math.pi)
    ax.plot(ph3, (r3["T"] - r3["mean"]) / r3["A1"], ".", color="#bbbbbb", ms=2.5, label=f"S18.3 measured ({P:g} s, u = 50 sin wt)")
    ph = (w * (tt - a) - lag) % (2 * math.pi)
    ax.plot(ph, (T - fT["mean"]) / fT["A1"], ".", color="#e8a39b", ms=2.5, label="S18.4 measured, settled cycles")
    o = np.argsort(ph)
    ax.plot(ph[o], ((fT["fit"] - fT["mean"]) / fT["A1"])[o], color="#C0392B", lw=1.3, label="S18.4, mean + 3 harmonics")
    ax.plot(x, np.sin(x), color="#1F77B4", ls="--", lw=1.5, label="pure sinusoid")
    ax.axhline(0, color="#888888", lw=0.8)
    ax.set_xlim(0, 2 * math.pi)
    ax.set_xlabel("phase of the temperature swing (rad)")
    ax.set_ylabel("(T − mean) / A1")
    ax.legend(fontsize=8, loc="lower left")
    ax.set_title("Shape of one cycle, each normalised by its own amplitude and lag", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def tec_block(cyc, n):
    """Counting back from the last cycle, add a cycle while the TEC mean, amplitude and lag stay near the block median.
    Rod amplitudes are only 0.15 to 1 degC here, so their cycle-to-cycle noise is above the 3 % rod test of the PI runs."""
    mean = np.array([cyc["TEC_C"][k]["a"] for k in range(n)])
    B = np.array([cyc["TEC_C"][k]["B"] for k in range(n)])
    lag = np.array([an.wrap(cyc["setpoint_C"][k]["phi"] - cyc["TEC_C"][k]["phi"]) for k in range(n)])
    block = [n - 1]
    for k in range(n - 2, -1, -1):
        if (abs(mean[k] - np.median(mean[block])) > PG.START_UP_TOL or abs(B[k] / np.median(B[block]) - 1) > an.TOL_B
                or abs(lag[k] - np.median(lag[block])) > an.TOL_PHI):
            return block, k
        block.insert(0, k)
    return block, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--t-amb", type=float, default=PG.T_AMB_RUN, help="room temperature of the prediction (default: the S18.4 page)")
    ap.add_argument("--t-room", type=float, default=22.7, help="room temperature for the mean rod profile")
    ap.add_argument("--out-dir")
    ap.add_argument("--fig-dir", default=an.FIG_DIR)
    a = ap.parse_args()
    run = os.path.abspath(a.run)
    stamp = an.stamp_of(run)
    out_dir = a.out_dir or os.path.join(an.DATA_DIR, f"analysis_{stamp}")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(a.fig_dir, exist_ok=True)

    cols = an.load(run)
    t, u = cols["t"], cols["signed_pwm"].astype(float)
    _, data, _ = an.prepare(cols, an.load_offsets(an.OFFSETS), {})
    data["setpoint_C"] = u                                  # the applied PWM is the reference signal of a RAW run
    steps = an.find_steps(cols)
    if len(steps) != 1 or set(cols["control_mode"][steps[0]["idx"]]) != {"RAW"}:
        sys.exit("expected exactly one RAW step: cut the phase out of the plan file first")
    info = steps[0]
    P, idx = info["period"], info["idx"]
    w = 2 * math.pi / P

    cyc = an.cycle_fits(t, data, info)
    block, fail = tec_block(cyc, info["ncyc"])
    blk = an.analyse_block(t, data, info, cyc, block)
    x, dx = an.load_positions(an.SENSOR_MAP)
    sp = an.spatial(blk["fits"], blk["w"], x, dx)
    der = an.derived(sp, x, an.load_geometry(an.GEOMETRY), blk["fits"], a.t_room)

    sel = blk["sel"]
    tt, T = t[sel], data["TEC_C"][sel]
    fT, fu = S.hfit(tt, T, w), S.hfit(tt, u[sel], w)
    dT = np.gradient(fT["fit"], tt)
    lag = S.wrap(fu["th1"] - fT["th1"])
    U0, U = fu["mean"], fu["A1"]
    tec = dict(mean=fT["mean"], A1=fT["A1"], A2=fT["A2"], A3=fT["A3"], lag=lag, lag_s=lag / w, h2=fT["A2"] / fT["A1"],
               above=float(T.max() - fT["mean"]), below=float(fT["mean"] - T.min()), up=float(dT.max()), dn=float(dT.min()),
               Tmax=float(T.max()), Tmin=float(T.min()))

    A183 = S.analyse(PG.S183_RUN)
    m = A183["model"]
    r3 = next(r for r in A183["results"] if r["period"] == P)
    e = PG.settled(P, U, m["chi_h"], m["tau"])
    pred = dict(mean=a.t_amb + m["chi_h"] * U0, A1=e["R"], lag=e["phi"], N=e["N"])
    Tm = S.simulate_u(t[idx], u[idx], m["chi_h"], m["chi_c"], m["tau"], a.t_amb, data["TEC_C"][idx][0])
    resid = data["TEC_C"][idx] - Tm
    rms_blk = float(np.sqrt(np.mean(resid[sel[idx]] ** 2)))
    chi_mean = (tec["mean"] - a.t_amb) / U0
    n_amp = tec["A1"] / (chi_mean * U)                       # A1 = chi U N
    tau_amp = math.sqrt(1 / n_amp ** 2 - 1) / w              # N = 1 / sqrt(1 + (w tau)^2)
    tau_lag = math.tan(lag) / w                              # lag = arctan(w tau)

    L = []
    add = L.append
    add(f"S18.4 positive-only PWM: {os.path.relpath(run, an.REPO)}")
    add(f"python3 python/sammy_module8_s184_analysis.py {os.path.relpath(run, an.REPO)} --t-amb {a.t_amb:g} --t-room {a.t_room:g}")
    add("")
    add(f"Schedule: {P:g} s period, {info['ncyc']} whole cycles ({t[idx][-1] - t[idx][0]:.1f} s), TEC at the start {data['TEC_C'][idx][0]:.2f} °C")
    add(f"Applied PWM: {u[idx].min():.0f} to {u[idx].max():.0f} counts, never negative: {'yes' if u[idx].min() >= 0 else 'NO'}; "
        f"fitted U0 = {U0:.2f}, U = {U:.2f}; highest T1 {data['T1_C'][idx].max():.2f} °C")
    add(f"Settled block (counting back from the last cycle while the TEC mean is within {PG.START_UP_TOL:g} °C, its amplitude within {100 * an.TOL_B:g} % "
        f"and its lag within {an.TOL_PHI:g} rad of the block median): cycles {block[0] + 1} to {block[-1] + 1} ({len(block)} cycles)"
        + (f"; first rejected cycle {fail + 1}" if fail is not None else ""))
    add("")
    add("TEC thermistor over the settled block (3 harmonics + drift):")
    add(f"  mean {tec['mean']:.2f} °C ({tec['mean'] - TARGET:+.2f} from the {TARGET:g} °C target); highest {tec['Tmax']:.2f}, lowest {tec['Tmin']:.2f} °C (latch {PG.TEC_LATCH:g})")
    add(f"  A1 {tec['A1']:.3f} °C, lag {tec['lag']:.3f} rad = {tec['lag_s']:.1f} s, A2/A1 {tec['h2']:.3f}, A3/A1 {tec['A3'] / tec['A1']:.3f}")
    add(f"  highest peak above the mean {tec['above']:.2f}, lowest below {tec['below']:.2f}; steepest rise {tec['up']:.3f}, steepest fall {tec['dn']:.3f} °C/s")
    add("")
    add(f"Prediction made before the run (S18.3 one-lump fit chi_h {m['chi_h']:.3f}, tau {m['tau']:.1f} s, T_amb {a.t_amb:g} °C, this run's U0 and U):")
    add(f"  mean {pred['mean']:.2f}  A1 {pred['A1']:.3f}  lag {pred['lag']:.3f} rad = {pred['lag'] / w:.1f} s  "
        f"highest {pred['mean'] + pred['A1']:.1f}  lowest {pred['mean'] - pred['A1']:.1f} °C")
    add(f"  measured minus predicted: mean {tec['mean'] - pred['mean']:+.2f} °C, A1 {tec['A1'] - pred['A1']:+.3f} °C ({100 * (tec['A1'] / pred['A1'] - 1):+.1f} %), "
        f"lag {tec['lag'] - pred['lag']:+.3f} rad ({tec['lag_s'] - pred['lag'] / w:+.1f} s)")
    add(f"  whole run, model integrated with the recorded PWM from the first record: RMS of TEC - model over the settled block {rms_blk:.2f} °C")
    add("")
    add("One-lump check with this run's own numbers (mean = T_amb + chi U0, A1 = chi U N, N = 1 / sqrt(1 + (w tau)^2), lag = arctan(w tau)):")
    add(f"  chi from the mean {chi_mean:.3f} °C/count (S18.3 fit chi_h {m['chi_h']:.3f});  tau from the amplitude {tau_amp:.1f} s, "
        f"tau from the lag {tau_lag:.1f} s (S18.3 fit {m['tau']:.1f} s); one lump would give the same tau twice")
    add("")
    add(f"Shape of the TEC cycle, S18.4 (u >= 0) against S18.3 at {P:g} s (u = {A183['U']:.0f} sin wt):")
    add(f"  {'':28s}{'S18.4':>14s}{'S18.3':>14s}")
    add(f"  {'A2/A1':28s}{tec['h2']:14.3f}{r3['A2'] / r3['A1']:14.3f}")
    add(f"  {'peak above / below mean (°C)':28s}{tec['above']:7.2f}/{tec['below']:<6.2f}{r3['above']:7.2f}/{r3['below']:<6.2f}")
    add(f"  {'steepest rise / fall (°C/s)':28s}{tec['up']:7.3f}/{tec['dn']:<6.3f}{r3['slope_up']:7.3f}/{r3['slope_dn']:<6.3f}")
    add(f"  {'lag behind the PWM (rad)':28s}{tec['lag']:14.3f}{r3['lag']:14.3f}")
    add("")
    add(f"Rod, settled block, same fits as the PI runs: q {sp['q']:.2f} +/- {sp['sq']:.2f} 1/m, q' {sp['qp']:.2f} +/- {sp['sqp']:.2f} 1/m, "
        f"kappa {sp['kappa']:.3e} +/- {sp['skappa']:.1e} m^2/s; T1 amplitude {blk['fits']['T1_C']['B']:.3f} °C, T5 {blk['fits']['T5_C']['B']:.3f} °C")
    msq = f"{der['m_osc']:.2f} 1/m" if math.isfinite(der["m_osc"]) else "undefined here (q' is above q)"
    add(f"  mean-profile loss rate m {der['m_dc']:.2f} 1/m (T_room {a.t_room:g} °C) against sqrt(q^2 - q'^2): {msq}")
    report = "\n".join(L) + "\n"
    with open(os.path.join(out_dir, "report.txt"), "w") as fh:
        fh.write(report)
    print(report)

    with open(os.path.join(out_dir, "cycle_fits.csv"), "w", newline="") as fh:
        wr = csv.writer(fh, lineterminator="\n")
        wr.writerow(["cycle", "settled", "u_mean", "u_amp", "TEC_mean_C", "TEC_A1_C", "TEC_lag_rad"]
                    + [f"{c[:2]}_{k}" for c in ROD for k in ("B_C", "phi_rad")])
        for k in range(info["ncyc"]):
            ca = info["t0"] + k * P
            cs = (t >= ca) & (t < ca + P) & (cols["run_state"] == 2)
            gT, gu = S.hfit(t[cs], data["TEC_C"][cs], w, 1, False), S.hfit(t[cs], u[cs], w, 1, False)
            wr.writerow([k + 1, int(k in block), f"{gu['mean']:.3f}", f"{gu['A1']:.3f}", f"{gT['mean']:.4f}", f"{gT['A1']:.4f}",
                         f"{S.wrap(gu['th1'] - gT['th1']):.4f}"]
                        + [f"{cyc[c][k][key]:.4f}" for c in ROD for key in ("B", "phi")])

    fig = lambda name: os.path.join(a.fig_dir, f"{stamp}_s184_{name}.png")
    fig_overview(fig("overview"), t[idx] - info["t0"], data["TEC_C"][idx], {c: data[c][idx] for c in ROD}, u[idx], Tm, P, block[0],
                 pred, f"S18.4 positive-only PWM, U0 = {U0:.0f}, U = {U:.0f} counts, {P:g} s period: measured against the prediction made before the run")
    fig_shape(fig("shape"), r3, tt, T, fT, lag, w, blk["ta"], P)
    print(f"Wrote report.txt and cycle_fits.csv in {os.path.relpath(out_dir, an.REPO)}, figures in {os.path.relpath(a.fig_dir, an.REPO)}")


if __name__ == "__main__":
    main()
