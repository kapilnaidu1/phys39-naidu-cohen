#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I: write the A5 of Samuel Cohen (text, tables, figures).  SAMMY.

    python3 python/sammy_module8_a5_write.py        (from the repository root, then python3 python/build_a5_cohen_pdf.py)

Every number of the text is computed here from the raw runs (python/sammy_module8_a5.py holds the analysis, sammy_module8_a5_figs.py the
figures). Writes docs/assessments/a5_angstrom_cohen.md, docs/figures/module_08_sammy/a5_fig*.png and data/module_08_sammy/a5_*.csv.
Which window stands for which period is the WINDOWS list of sammy_module8_a5.py; change it there when a later run replaces a window.
"""

import csv
import math
import os

import sammy_module8_angstrom_analysis as A
import sammy_module8_finite_rod as FR
import sammy_module8_a5 as M
import sammy_module8_a5_figs as F

OUT_MD = os.path.join(A.REPO, "docs", "assessments", "a5_angstrom_cohen.md")
FIGDIR = A.FIG_DIR
nl = chr(10)


def n(v, d=2, sign=False):
    if round(v, d) == 0:
        v, sign = 0.0, False
    s = f"{v:+.{d}f}" if sign else f"{v:.{d}f}"
    return s.replace("-", "\u2212")


def sci(v, d=1):
    mant, exp = f"{v:.{d}e}".split("e")
    sup = str.maketrans("0123456789-+", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207b\u207a")
    return f"{mant} \u00d7 10{str(int(exp)).translate(sup)}"


def pm(v, s, scale=1.0, d=2):
    return f"{n(v * scale, d)} \u00b1 {n(s * scale, d)}"


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    return nl.join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def met_text(m):
    ok = M.meets(m)
    names = [k for k, v in ok.items() if v]
    return "all four" if len(names) == 4 else (", ".join(names) if names else "none")


def read_csv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    kw, nuw, allrows = M.kappa_nu_pair()
    M.KAPPA, M.NU = kw[0], nuw[0]
    kap, nu = kw[0], nuw[0]
    g_c, tau_s, chk = M.fit_contact(kap, nu)
    cr = M.control_rows()
    byk = {r["key"]: r for r in cr}
    sims = {}
    for r in cr:
        if r["key"] in ("p", "pi100", "pi300"):
            r["sim"], arr, _ = M.sim_for_row(r, g_c, tau_s)
            sims[r["key"]] = arr
    variants = [(mode, kp, ki) + (M.variant(kp, ki, mode, g_c, tau_s)[0],) for mode, kp, ki in (("P", 12, 0.0), ("PI", 12, 0.2), ("PI", 12, 0.5), ("PI", 20, 0.2))]
    wins = M.windows()
    wb = {w["P"]: w for w in wins}
    for key in ("kp20", "ki05"):
        byk[key]["sim"] = M.sim_for_row(byk[key], g_c, tau_s)[0]
    s20, s05 = byk["kp20"]["sim"], byk["ki05"]["sim"]
    g18, ts18, chk18 = M.fit_contact(kap, nu, M.CONTACT_18)
    r18 = (chk18[0][1], chk18[2][1])
    bc = M.burst_check(M.RUN18, 400)
    bs = M.burst_stats(M.RUN18, "T3_C", 2445, 2467)
    wd_m = M.sammy_window(M.RUN18, 400, "strict", mask=M.T3_BURST)
    assert wb[400]["wd"]["ncyc"] == 5 and len(bc["block"]) == 4 and wd_m["ncyc"] == 7 and bc["sensor"] == "T3_C", "typed counts in the text are stale"
    xs, dxs = A.load_positions(A.SENSOR_MAP)
    phi_m = wd_m["phi"][0] + M.np.unwrap(wd_m["phi"] - wd_m["phi"][0])
    fin_m = FR.joint_fit(xs, dxs, wd_m["B"], wd_m["sB"], phi_m, wd_m["sphi"], 2 * math.pi / 400, A.load_geometry(A.GEOMETRY)["L"], True)
    cp = M.comparison(g_c, tau_s, kap, nu, wb[300])
    s183 = read_csv(os.path.join(A.DATA_DIR, "s183_analysis_20261111_122227", "s183_by_period.csv"))[0]
    fitrow = next(r for r in read_csv(os.path.join(A.DATA_DIR, "s183_analysis_20261111_122227", "s183_model_fit.csv")) if r["model"].startswith("fitted"))
    chi_h, chi_c, tau_fit = float(fitrow["chi_h_C_per_count"]), float(fitrow["chi_c_C_per_count"]), float(fitrow["tau_s"])
    t400 = read_csv(os.path.join(A.DATA_DIR, "analysis_20261118_104629", "tracking_by_period.csv"))[0]
    t480 = next(r for r in read_csv(os.path.join(A.DATA_DIR, "analysis_20261116_090538", "tracking_by_period.csv")) if abs(float(r["period_s"]) - 480) < 1)

    # ---- figures
    F.fig1(os.path.join(FIGDIR, "a5_fig1_control.png"), cr, sims)
    F.fig2(os.path.join(FIGDIR, "a5_fig2_lengths.png"), wins, kw, nuw)
    F.fig3(os.path.join(FIGDIR, "a5_fig3_spatial.png"), wins)
    F.fig4(os.path.join(FIGDIR, "a5_fig4_comparison.png"), cp)

    # ---- numbers used in the text
    m_shared = math.sqrt(nu / kap)
    l_mean = 1000 / m_shared
    k_cond = A.RHO * A.CP * kap
    h_conv = A.RHO * A.CP * (A.load_geometry(A.GEOMETRY)["d"] / 4) * nu
    kh = A.KAPPA_HANDBOOK
    z = {P: (w["fin"]["kappa"] - kap) / w["fin"]["skappa"] for P, w in wb.items()}
    worst = max(z, key=lambda P: abs(z[P]))
    lamp = {P: 1000 / w["fin"]["q"] for P, w in wb.items()}
    b51 = {P: w["wd"]["B"][4] / w["wd"]["B"][0] for P, w in wb.items()}
    dph = {P: w["phi_u"][0] - w["phi_u"][4] for P, w in wb.items()}
    semi_low = {P: 100 * (1 - w["semi"]["kappa"] / w["fin"]["kappa"]) for P, w in wb.items()}
    ratio_t1 = {P: (am, ph) for P, am, ph, bmod, pmod in chk}
    dev_amp, dev_ph = max(abs(bmod / am - 1) for P, am, ph, bmod, pmod in chk), max(abs(pmod - ph) for P, am, ph, bmod, pmod in chk)
    n_mine = sum(1 for r in allrows if r["meets"] and not r["kapil"])
    n_kapil = sum(1 for r in allrows if r["meets"] and r["kapil"])
    t2_amp = {P: 100 * w["fin"]["dlnB"][1] for P, w in wb.items()}
    t2_dk = {}
    for P, w in wb.items():
        k = [0, 2, 3, 4]
        g = FR.joint_fit(w["x"][k], w["dx"][k], w["wd"]["B"][k], w["wd"]["sB"][k], w["phi_u"][k], w["wd"]["sphi"][k], w["w"], w["L"], True)
        t2_dk[P] = 100 * (g["kappa"] / w["fin"]["kappa"] - 1)
    k_err = [100 * w["fin"]["skappa"] / w["fin"]["kappa"] for w in wins]
    nu_err = [100 * w["fin"]["snu"] / w["fin"]["nu"] for w in wins]
    chi_dof = [w["fin"]["chi2"] / w["fin"]["dof"] for w in wins]
    res_other = max(abs(100 * w["fin"]["dlnB"][i]) for w in wins for i in (2, 3, 4))
    res_phase = max(abs(v) for w in wins for v in w["fin"]["dphi"][1:])
    resid_txt = lambda w: (", ".join(n(100 * v, 1, True) for v in w["fin"]["dlnB"][1:]), ", ".join(n(v, 3, True) for v in w["fin"]["dphi"][1:]))
    sp = {s["ch"]: s for s in cp["sensors"]}
    tec = cp["tec"]
    fl = wb[300]["fin"]
    m300w = math.sqrt(fl["nu"] / fl["kappa"])
    z300 = (fl["nu"] - nu) / fl["snu"]
    ana_w_da = [s["ana_w"]["da"] for s in cp["sensors"]]
    rod_t5 = (sp["T5_C"]["num"]["rB"] / sp["T1_C"]["num"]["rB"], sp["T5_C"]["num"]["dphi"] - sp["T1_C"]["num"]["dphi"])
    var = {(mode, kp, ki): m for mode, kp, ki, m in variants}
    droop = (M.TA - M.T_AMB_2NOV) / (1 + M.S.CHI_H * 12)
    ff_lo, ff_hi = (M.TA - M.T_AMB_2NOV - M.TB) / M.S.CHI_H, (M.TA - M.T_AMB_2NOV + M.TB) / M.S.CHI_H
    mcmp = ", ".join(f"{n(wb[P]['prof']['m'], 2)} against {n(math.sqrt(max(wb[P]['fin']['q'] ** 2 - wb[P]['fin']['qp'] ** 2, 0)), 2)}" for P in (100, 300, 400, 480))
    where = {key: byk[key]["where"] for key in byk}
    bm = lambda key, f: byk[key]["m"][f]

    # ---- tables
    names = {"raw0": ("RAW zero-centered", "u = 50 sin \u03c9t"), "raw1": ("RAW positive-only", "U0 38, U 36"),
             "ff": ("Feedforward (OL)", "3 to 67 counts"), "p": ("P only", "Kp 12"), "pi100": ("PI, 2 Nov", "Kp 12, Ki 0.2"),
             "pi100b": ("PI, 16 Nov", "Kp 12, Ki 0.2"), "pi200": ("PI, 16 Nov", "Kp 12, Ki 0.2"), "pi300": ("PI, 4 Nov", "Kp 12, Ki 0.2"),
             "kp20": ("PI, 18 Nov", "Kp 20, Ki 0.2"), "ki05": ("PI, 18 Nov", "Kp 12, Ki 0.5")}
    t1rows = []
    for key in ("raw0", "raw1", "ff", "p", "pi100", "pi100b", "pi200", "pi300", "kp20", "ki05"):
        r, m = byk[key], byk[key]["m"]
        t1rows.append([names[key][0], names[key][1], r["P"], n(m["mean_err"], 2, True), n(m["ratio"], 2), f"{n(m['lag_rad'], 2)} ({n(m['lag_s'], 1)})", n(m["rms"], 1),
                       f"{n(m['pwm_min'], 0)} to {m['pwm_max']}", n(m["sat"], 1), met_text(m)])
    for (mode, kp, ki), m in var.items():
        lab = "P only" if mode == "P" else "PI"
        t1rows.append([f"{lab}, simulated", f"Kp {kp}, Ki {ki:g}", 100, n(m["mean_err"], 2, True), n(m["ratio"], 2), f"{n(m['lag_rad'], 2)} ({n(m['lag_s'], 1)})",
                       n(m["rms"], 1), f"{n(m['pwm_min'], 0)} to {m['pwm_max']}", n(m["sat"], 1), met_text(m)])
    t1 = table(["Run", "Gains or drive", "\u03c4 (s)", "Mean error (\u00b0C)", "Amplitude ratio", "Lag, rad (s)", "RMS error (\u00b0C)",
                "PWM range (counts)", "At \u00b1255 (%)", "Criteria met"], t1rows)
    t2rows, t2b = [], []
    for P in sorted(wb):
        w = wb[P]
        f, pr = w["fin"], w["prof"]
        t2rows.append([P, f"{w['label']}, cycles {w['wd']['cycles']}" + (" (last five)" if w["which"] == "last5" else ""), pm(f["q"], f["sq"]), pm(f["qp"], f["sqp"]),
                       pm(f["kappa"], f["skappa"], 1e5), pm(f["nu"], f["snu"], 1e3), f"{f['chi2']:.1f}/{f['dof']}", n(z[P], 1, True)])
        t2b.append([P, resid_txt(w)[0], resid_txt(w)[1], n(100 * w["tip"], 1), n(-semi_low[P], 1, True), f"{n(pr['m'], 2)} \u00b1 {n(math.hypot(pr['sm_stat'], pr['sm_sys']), 2)}",
                    n(math.sqrt(max(f["q"] ** 2 - f["qp"] ** 2, 0)), 2), sci(w["bi"])])
    t2 = table(["\u03c4 (s)", "Run and settled cycles", "q (1/m)", "q\u2032 (1/m)", "\u03ba (10\u207b\u2075 m\u00b2/s)", "\u03bd (10\u207b\u00b3 1/s)", "\u03c7\u00b2/dof",
                "(\u03ba \u2212 \u03ba<sub>sh</sub>)/\u03c3"], t2rows)
    t2bt = table(["\u03c4 (s)", "Amplitude residuals T2 to T5 (%)", "Phase residuals T2 to T5 (rad)", "Finite-length difference at T5 (%)", "Semi-infinite \u03ba against finite (%)",
                  "m, mean profile (1/m)", "\u221a(q\u00b2 \u2212 q\u2032\u00b2) (1/m)", "Biot number"], t2b)
    trip = lambda d: f"{n(d['da'], 2, True)}, {n(d['rB'], 3)}, {n(d['dphi'], 3, True)}"
    t3rows = [[f"T{i + 1} ({1000 * s['x']:.1f} mm)", f"{n(s['a'], 2)}, {n(s['B'], 3)}, {n(s['phi'], 3)}", trip(s["ana"]), trip(s["num"]), n(s["ana"]["rms"], 2), n(s["num"]["rms"], 2)]
              for i, s in enumerate(cp["sensors"])]
    t3rows.append(["TEC", f"{n(tec['meas']['a'], 2)}, {n(tec['meas']['B'], 3)}, {n(tec['meas']['phi'], 3)}", "", f"{n(tec['sim']['a'] - tec['meas']['a'], 2, True)}, "
                   f"{n(tec['sim']['B'] / tec['meas']['B'], 3)}, {n(M.wrap(tec['sim']['phi'] - tec['meas']['phi']), 3, True)}", "", ""])
    t3 = table(["Sensor", "Measured: mean (\u00b0C), amplitude (\u00b0C), phase (rad)", "Analytical: \u0394mean (\u00b0C), amplitude ratio, \u0394phase (rad)",
                "Numerical: \u0394mean (\u00b0C), amplitude ratio, \u0394phase (rad)", "Analytical rms residual (\u00b0C)", "Numerical rms residual (\u00b0C)"], t3rows)

    # ---- csv files
    with open(os.path.join(A.DATA_DIR, "a5_control_table.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator=nl)
        w.writerow(["key", "run", "gains", "period_s", "interval", "mean_error_C", "amplitude_ratio", "lag_rad", "lag_s", "rms_error_C", "pwm_min", "pwm_max", "samples_at_255_percent",
                    "cycle_amplitude_spread_percent", "residual_amplitude_C", "A2_over_A1", "criteria_met"])
        for key in byk:
            r, m = byk[key], byk[key]["m"]
            w.writerow([key, r["label"], r["gains"], r["P"], r["where"], f"{m['mean_err']:.3f}", f"{m['ratio']:.4f}", f"{m['lag_rad']:.4f}", f"{m['lag_s']:.2f}", f"{m['rms']:.3f}",
                        m["pwm_min"], m["pwm_max"], f"{m['sat']:.2f}", f"{m['dB']:.2f}", f"{m['resid']:.3f}", f"{m['a2']:.4f}", met_text(m)])
    with open(os.path.join(A.DATA_DIR, "a5_windows.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator=nl)
        w.writerow(["period_s", "run", "settled_cycles", "interval_s", "q_1_m", "sq", "qprime_1_m", "sqprime", "kappa_m2_s", "skappa", "nu_1_s", "snu", "chi2", "dof",
                    "finite_length_diff_percent", "m_mean_profile_1_m", "sm_stat", "sm_sys", "room_T_C", "amp_resid_T2_to_T5_percent", "phase_resid_T2_to_T5_rad",
                    "semi_infinite_kappa_vs_finite_percent", "sqrt_q2_minus_qp2_1_m", "biot_number"])
        for P in sorted(wb):
            x, f, pr = wb[P], wb[P]["fin"], wb[P]["prof"]
            w.writerow([P, x["label"], x["wd"]["cycles"], f"{x['wd']['tint'][0]:.1f} to {x['wd']['tint'][1]:.1f}", f"{f['q']:.3f}", f"{f['sq']:.3f}", f"{f['qp']:.3f}", f"{f['sqp']:.3f}",
                        f"{f['kappa']:.4e}", f"{f['skappa']:.2e}", f"{f['nu']:.3e}", f"{f['snu']:.2e}", f"{f['chi2']:.2f}", f['dof'], f"{100 * x['tip']:.2f}", f"{pr['m']:.3f}",
                        f"{pr['sm_stat']:.3f}", f"{pr['sm_sys']:.3f}", x["t_room"], ";".join(f"{100 * v:+.2f}" for v in f["dlnB"][1:]), ";".join(f"{v:+.4f}" for v in f["dphi"][1:]),
                        f"{-semi_low[P]:+.2f}", f"{math.sqrt(max(f['q'] ** 2 - f['qp'] ** 2, 0)):.3f}", f"{x['bi']:.2e}"])
    with open(os.path.join(A.DATA_DIR, "a5_comparison.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator=nl)
        w.writerow(["sensor", "x_mm", "mean_C", "amplitude_C", "phase_rad", "ana_dmean", "ana_ampl_ratio", "ana_dphase", "num_dmean", "num_ampl_ratio", "num_dphase", "num_rms_C"])
        for i, s in enumerate(cp["sensors"]):
            w.writerow([s["ch"], f"{1000 * s['x']:.1f}", f"{s['a']:.3f}", f"{s['B']:.4f}", f"{s['phi']:.4f}", f"{s['ana']['da']:.3f}", f"{s['ana']['rB']:.4f}", f"{s['ana']['dphi']:.4f}",
                        f"{s['num']['da']:.3f}", f"{s['num']['rB']:.4f}", f"{s['num']['dphi']:.4f}", f"{s['num']['rms']:.3f}"])

    v05, v20 = var[("PI", 12, 0.5)], var[("PI", 20, 0.2)]
    text = f"""# A5: S18 Evidence, Boundary-Control Analysis and Angstrom Theory

Assessment code: A5 (individual)  
Student: Samuel Cohen (lab partner Kapil Naidu; the measurements are our team's)  
Date: 18 November 2026 (runs through 18 November)  
Repository: https://github.com/kapilnaidu1/phys39-naidu-cohen, branch main

## 1. Evidence that the S18 procedure was followed

- **S18 record.** The team's S18 evidence table (one row per step S18.1 to S18.10: result, evidence, departures) is `docs/module_notes/module_08_s18_evidence_table.md`.
  Departures that matter here: the 2 Nov feedforward inverted the measured steady-state curve instead of using the S18.5 straight line, which gives nearly the same command (3 to 67 counts against {ff_lo:.1f} to {ff_hi:.1f});
  the PI pair (Kp 12, Ki 0.2) came from the Module 6 plate model and ran at every period, and the S18.7 tuning log is the two single-gain trials of 18 Nov (Kp 20, then Ki 0.5, at 100 s; Table 1),
  neither of which met all four criteria, so I did not retune further; the 400 s window (18 Nov) has five cycles by the five-cycle rule but four by the strict settling test (3 % in amplitude, 0.05 rad)
  because a burst on T3 spoils cycle 4; I did not mask it (Question 3); 480 s stands in for 500 s.
- **Data and code.** Raw runs, each with `_events.txt`, `_notes.csv` and `_meta.json`: Kapil's `angstrom_live_20261102_094506` (feedforward, P, PI 100 s) and `angstrom_live_20261104_110306` (PI 300 s, the matched run) in `data/module_08/`;
  mine in `data/module_08_sammy/`, all `sammy_angstrom_live_` + `20261111_122227` (raw zero-centered), `20261116_090538` (PI 100 and 480 s), `20261116_111935` (phases: PI 200 s, raw positive-only), `20261117_162612` and `20261118_104629`
  (PI 400 s) and `20261118_122006` (the two gain trials, as phase slices). Each figure caption names its run and interval (also in `a5_control_table.csv` and `a5_windows.csv`). Code (in `python/`):
  `sammy_module8_a5_write.py` regenerates every number, table and figure below with `sammy_module8_a5.py`, `sammy_module8_a5_figs.py`, `sammy_module8_angstrom_analysis.py`, `sammy_module8_finite_rod.py`,
  `sammy_module8_runs_summary.py` and the model `sammy_module8_tec_rod_sim.py`; `build_a5_cohen_pdf.py` makes this PDF. The commit named on this page contains all of them.

## 2. Measured boundary-control comparison

### Question 1: what made the measured TEC temperature track the setpoint, and why?

The target is T<sub>set</sub> = 40 + 16 sin(2\u03c0t/\u03c4) \u00b0C (24 to 56 \u00b0C). A trial succeeds if, over three whole settled cycles (amplitudes within {max(r['m']['dB'] for r in cr):.0f} % of each other), the mean error is at most
{M.CRIT['mean']:.0f} \u00b0C, the amplitude ratio B<sub>TEC</sub>/16 is {M.CRIT['ratio_lo']:.2f} to {M.CRIT['ratio_hi']:.2f}, the lag behind the setpoint is at most {M.CRIT['lag']:.2f} rad and the rms tracking error is at most {M.CRIT['rms']:.1f} \u00b0C
(20 % of the amplitude). The criteria are mine: they ask for the requested sinusoid, not just a sinusoid.

**Raw PWM and feedforward give a sinusoid, not the requested one** (Table 1, rows 1 to 3). With u = 50 sin \u03c9t the heating half is stronger than the cooling half (\u03c7<sub>h</sub> 0.50 and \u03c7<sub>c</sub> 0.18 \u00b0C per count from Module 4;
the one-lump fit to this run gives {chi_h:.2f} and {chi_c:.2f}, \u03c4 = {tau_fit:.0f} s), so the mean sits {float(s183['mean_minus_baseline_C']):.1f} \u00b0C above the baseline and the second harmonic is {bm('raw0', 'a2'):.2f} of the fundamental.
Staying on the heating branch (U0 38, U 36) removes the distortion (A<sub>2</sub>/A<sub>1</sub> {bm('raw1', 'a2'):.3f}) and puts the mean within {abs(bm('raw1', 'mean_err')):.1f} \u00b0C of 40 \u00b0C, but the amplitude is only {bm('raw1', 'B'):.1f} \u00b0C
(ratio {bm('raw1', 'ratio'):.2f}) and the TEC lags the PWM by {bm('raw1', 'lag_rad'):.2f} rad ({bm('raw1', 'lag_s'):.1f} s); the 2 Nov feedforward gives the same waveform (ratio {bm('ff', 'ratio'):.2f}, lag {bm('ff', 'lag_rad'):.2f} rad).
A static calibration fixes the mean only: the plate is a first-order lag with \u03c4 \u2248 {tau_fit:.0f} s, so at 100 s (\u03c9\u03c4 = {2 * math.pi / 100 * tau_fit:.1f}) the amplitude falls to 1/\u221a(1 + (\u03c9\u03c4)\u00b2) = {1 / math.sqrt(1 + (2 * math.pi / 100 * tau_fit) ** 2):.2f}
and the lag approaches 90\u00b0.

**Integral action changes the mean and the amplitude, not the delay** (rows 4 and 5). P only with Kp 12 has a standing error: the mean is {abs(bm('p', 'mean_err')):.1f} \u00b0C low, as the loop gain \u03c7<sub>h</sub>Kp = {M.S.CHI_H * 12:.0f} predicts
((40 \u2212 22.5)/(1 + {M.S.CHI_H * 12:.0f}) = {droop:.1f} \u00b0C), with ratio {bm('p', 'ratio'):.2f} and lag {bm('p', 'lag_rad'):.2f} rad. PI with the same Kp takes the mean error to {n(bm('pi100', 'mean_err'), 2, True)} \u00b0C, because the integral supplies the steady
heating command that P can supply only through an error, and raises the ratio to {bm('pi100', 'ratio'):.2f}; the lag stays at {bm('pi100', 'lag_rad'):.2f} rad. The simulation of Question 4 (my own numerical TEC and rod model, not the course simulator) reproduces both runs (Table 1: mean errors {n(byk['p']['sim']['mean_err'], 1, True)}
and {n(byk['pi100']['sim']['mean_err'], 1, True)} \u00b0C, ratios {byk['p']['sim']['ratio']:.2f} and {byk['pi100']['sim']['ratio']:.2f}, lags {byk['p']['sim']['lag_rad']:.2f} and {byk['pi100']['sim']['lag_rad']:.2f} rad), which supports this explanation: integral action removes the droop and adds some
amplitude, and at Kp 12 neither term removes the lag.

**PI meets the criteria only at the longer periods.** With Kp 12 and Ki 0.2 at every period (a pair chosen with the Module 6 one-lump plate model and kept after the trials below, so the initial and selected PI settings are the same) the ratio is {bm('pi100', 'ratio'):.2f}, {bm('pi200', 'ratio'):.2f} and {bm('pi300', 'ratio'):.2f} at 100, 200 and 300 s, the lag {bm('pi100', 'lag_rad'):.2f}, {bm('pi200', 'lag_rad'):.2f} and {bm('pi300', 'lag_rad'):.2f} rad
and the rms error {bm('pi100', 'rms'):.1f}, {bm('pi200', 'rms'):.1f} and {bm('pi300', 'rms'):.1f} \u00b0C: all four criteria are met only at 300 s (the 16 Nov repeat of 100 s agrees). The lag in seconds is nearly constant ({bm('pi100', 'lag_s'):.1f}, {bm('pi200', 'lag_s'):.1f}, {bm('pi300', 'lag_s'):.1f},
{float(t400['TEC_lag_s']):.1f} and {float(t480['TEC_lag_s']):.1f} s at 100, 200, 300, 400 and 480 s), so with this gain pair the phase error grows as \u03c9: a delay in the plate and thermistor path that the gain does not remove. At 100 s the PWM already reaches {n(bm('pi100b', 'pwm_min'), 0)} of \u2212255 counts
(cooling needs {M.S.R_COOL:.2f} times the heating count). The two single-gain trials of 18 Nov (S18.7; Table 1, rows 9 and 10; a 300 s hold and seven 100 s cycles each, Kp 20 first) changed one gain of that baseline. Kp 20 cut the lag from {bm('pi100', 'lag_rad'):.2f} and {bm('pi100b', 'lag_rad'):.2f} rad to {bm('kp20', 'lag_rad'):.2f} rad ({bm('kp20', 'lag_s'):.1f} s)
and the rms error from {bm('pi100', 'rms'):.1f} and {bm('pi100b', 'rms'):.1f} to {bm('kp20', 'rms'):.1f} \u00b0C (ratio {bm('kp20', 'ratio'):.2f}) but clips the PWM at \u2212255 for {bm('kp20', 'sat'):.1f} % of the samples; Ki 0.5 brought the ratio to {bm('ki05', 'ratio'):.2f} and left the lag at {bm('ki05', 'lag_rad'):.2f} rad
(rms {bm('ki05', 'rms'):.1f} \u00b0C, mean {n(bm('ki05', 'mean_err'), 2, True)} \u00b0C, {bm('ki05', 'sat'):.1f} % clipped). Each meets only the mean and ratio criteria, so no gain pair meets all four at 100 s; I did not try higher gains because the cooling branch already clips at Kp 20.
The simulation of Question 4, not adjusted to the trials, gives ratio and lag {s20['ratio']:.2f} and {s20['lag_rad']:.2f} rad (Kp 20) and {s05['ratio']:.2f} and {s05['lag_rad']:.2f} rad (Ki 0.5) against {bm('kp20', 'ratio'):.2f}, {bm('kp20', 'lag_rad'):.2f} and {bm('ki05', 'ratio'):.2f}, {bm('ki05', 'lag_rad'):.2f} measured:
the right direction and size, the lag {100 * (1 - s20['lag_rad'] / bm('kp20', 'lag_rad')):.0f} % (Kp 20) and {100 * (1 - s05['lag_rad'] / bm('ki05', 'lag_rad')):.0f} % (Ki 0.5) low, and the clipping at Kp 20 missed.

**The rod boundary is T1.** The TEC thermistor reads the plate; the rod base sees the plate through a contact conductance. T1 has only {ratio_t1[100][0]:.2f}, {ratio_t1[200][0]:.2f} and {ratio_t1[400][0]:.2f} of the TEC amplitude at 100, 200 and 400 s (16 and 17 Nov) and lags it by
{abs(ratio_t1[100][1]):.2f}, {abs(ratio_t1[200][1]):.2f} and {abs(ratio_t1[400][1]):.2f} rad, which a contact conductance of {g_c:.3f} W/K in series with the rod reproduces to {100 * dev_amp:.1f} % and {dev_ph:.2f} rad (Question 4); on 18 Nov T1 had {r18[0]:.2f} and {r18[1]:.2f} of the TEC amplitude at 100 and 400 s
and the same model needs {g18:.3f} W/K (cause unknown; the leads and sensors were handled before that run). The solution of Question 2 needs only the temperature at x = 0, and T1 is the sensor nearest to it; referring the rod to the TEC or the setpoint
would put the contact path, which is not a property of the rod, into q and q\u2032.

![Boundary control](../figures/module_08_sammy/a5_fig1_control.png)

**Figure 1.** TEC (black) against the requested 40 + 16 sin (grey dashed), T1 (blue) and the PWM, over three settled cycles. Intervals: (a) {where['raw0']}; (b) {where['raw1']}; (c) {where['ff']}; (d) {where['p']}; (e) {where['pi100']};
(f) {where['pi300']}. Red dashed: the numerical TEC and rod model, run on the recorded setpoint from the start of each recorded segment.

**Table 1.** Boundary control over three settled cycles (rows 1 to 3: S18.3, S18.4, S18.6; rows 9 and 10: the S18.7 gain trials of 18 Nov; \u03c4: forcing period; Kp in PWM counts per \u00b0C, Ki in counts per (\u00b0C s); "At \u00b1255": share of samples at the PWM limit). Mean error: measured mean minus 40 \u00b0C;
amplitude ratio: B<sub>TEC</sub>/16 \u00b0C; lag: behind the requested setpoint (behind the PWM sine for RAW); controller step 0.54 s. Criteria: mean \u2264 1 \u00b0C, ratio 0.90 to 1.10, lag \u2264 0.30 rad, rms \u2264 3.2 \u00b0C. Simulated rows: the numerical model of Question 4.

{t1}

## 3. Experiment, simulation and theory

### Question 2: what do the characteristic lengths mean in T(x,t)?

**The expression.** With \u03b8 = T \u2212 T<sub>\u221e</sub> the rod obeys \u2202\u03b8/\u2202t = \u03ba \u2202\u00b2\u03b8/\u2202x\u00b2 \u2212 \u03bd\u03b8 for 0 < x < L, with the measured T1 as the base temperature T(0,t) = T<sub>a</sub> + T<sub>b</sub> cos \u03c9t and an
insulated tip, \u2202T/\u2202x = 0 at x = L = 281.9 mm. The settled-periodic solution is T(x,t) = T<sub>\u221e</sub> + (T<sub>a</sub> \u2212 T<sub>\u221e</sub>) cosh[m(L \u2212 x)]/cosh(mL) + T<sub>b</sub> A(x) cos[\u03c9t \u2212 \u03c6(x)], with
A(x)e<sup>\u2212i\u03c6(x)</sup> = cosh[s(L \u2212 x)]/cosh(sL), s = q + iq\u2032 = \u221a((\u03bd + i\u03c9)/\u03ba) and m = \u221a(\u03bd/\u03ba). I used this finite form for the mean profile and for the oscillation fits; the semi-infinite form
T<sub>b</sub> e<sup>\u2212qx</sup> cos(\u03c9t \u2212 q\u2032x) is its limit when q(L \u2212 x) \u226b 1 (Question 3 gives the size of the difference). The derivation and its checks are in `docs/module_notes/module_08_part1_complete.md`.

**The lengths.** \u2113<sub>mean</sub> = 1/m is the distance over which the mean excess temperature falls by e; \u2113<sub>amp</sub> = 1/q is the e-folding length of the oscillation amplitude; \u2113<sub>phase</sub> = 1/q\u2032 is the distance that adds one radian of lag. They are tied by
m\u00b2 = \u03bd/\u03ba = q\u00b2 \u2212 q\u2032\u00b2 and 2qq\u2032 = \u03c9/\u03ba, so q/m = \u221a((1 + \u221a(1 + \u03a9\u00b2))/2) and q\u2032/m = \u221a((\u221a(1 + \u03a9\u00b2) \u2212 1)/2) with \u03a9 = \u03c9/\u03bd. \u2113<sub>mean</sub> does not depend on the period:
\u221a(\u03ba/\u03bd) = {l_mean:.0f} mm for the \u03ba and \u03bd of Question 3. For \u03c9 \u226b \u03bd both q and q\u2032 tend to \u221a(\u03c9/2\u03ba), so \u2113<sub>amp</sub> \u2248 \u2113<sub>phase</sub> \u2248 \u221a(\u03ba\u03c4/\u03c0) grow as \u221a\u03c4: {lamp[100]:.0f} mm at 100 s and {lamp[480]:.0f} mm at 480 s
(Figure 2). The fitted points follow the curves although each period was fitted on its own, apart from the mean-profile points at 200 s (Question 3) and 300 s (Question 4).

**What this means for the experiment.** The 101.6 mm T1 to T5 array spans {101.6 / lamp[100]:.1f} \u2113<sub>amp</sub> at 100 s and {101.6 / lamp[480]:.1f} at 480 s: the T5 amplitude is {b51[100]:.2f} of T1's at 100 s ({wb[100]['wd']['B'][4]:.2f} \u00b1 {wb[100]['wd']['sB'][4]:.3f} \u00b0C)
and {b51[480]:.2f} at 480 s, with a lag across the array of {dph[100]:.2f} and {dph[480]:.2f} rad. Every sensor keeps a measurable amplitude and phase at every period, and the course targets (B<sub>far</sub> \u2248 B<sub>1</sub>/e, a lag of 0.5 to 2 rad) are met at 480 s;
at 100 s the lag is in range but the amplitude is a factor {math.exp(-1) / b51[100]:.1f} below B<sub>1</sub>/e. Since \u2113<sub>mean</sub> = {l_mean:.0f} mm is comparable to L = 282 mm (mL = {m_shared * 0.2819:.1f}), the mean excess temperature stays measurable along the whole rod and the
insulated tip matters for it, whereas the oscillation is confined to the first one or two \u2113<sub>amp</sub> (Figure 4, 300 s: T5 has {sp['T5_C']['B'] / sp['T1_C']['B']:.2f} of the T1 amplitude and lags T1 by {dph[300]:.2f} rad ({dph[300] / wb[300]['w']:.0f} s), while the mean falls from {sp['T1_C']['a']:.1f} to {sp['T5_C']['a']:.1f} \u00b0C).

![Characteristic lengths](../figures/module_08_sammy/a5_fig2_lengths.png)

**Figure 2.** Characteristic lengths against period. Curves: 1/q, 1/q\u2032 and 1/m for the shared \u03ba = {pm(kap, kw[1], 1e5)} \u00d7 10\u207b\u2075 m\u00b2/s and \u03bd = {pm(nu, nuw[1], 1e3)} \u00d7 10\u207b\u00b3 s\u207b\u00b9 (bands: \u00b11 standard error). Points: finite-rod fits of the
five production windows of Table 2 (circles 1/q, squares 1/q\u2032, with errors) and 1/m from the finite mean-profile fit of each window (triangles; the 200 s window had no pre-hold, so its mean was still rising). Open markers: the 400 s window uses the last five cycles, only {len(bc['block'])} of them strictly settled.

### Question 3: how do the measurements determine diffusivity and heat loss?

**Method.** For each period I fitted every sensor over whole settled cycles with T<sub>i</sub> = a<sub>i</sub> + B<sub>i</sub> cos(\u03c9t + \u03c6<sub>i</sub>) (the cycle-to-cycle scatter is the error), then ln B<sub>i</sub> and the unwrapped \u03c6<sub>i</sub> jointly
against x with one complex s (finite insulated-tip form, 1 mm position errors on T2 to T5, errors scaled by \u221a(\u03c7\u00b2/dof) when that exceeds 1). Then \u03ba = \u03c9/(2qq\u2032) and \u03bd = \u03ba(q\u00b2 \u2212 q\u2032\u00b2): the product of the two decay rates carries the diffusion, the
difference of their squares the side loss (Table 2, Figure 3).

**Result.** The five periods give \u03ba = {min(w['fin']['kappa'] for w in wins) * 1e5:.2f} to {max(w['fin']['kappa'] for w in wins) * 1e5:.2f} \u00d7 10\u207b\u2075 m\u00b2/s with errors of {min(k_err):.1f} to {max(k_err):.1f} %, and \u03bd = {min(w['fin']['nu'] for w in wins) * 1e3:.1f} to {max(w['fin']['nu'] for w in wins) * 1e3:.1f} \u00d7 10\u207b\u00b3 s\u207b\u00b9 with errors
of {min(nu_err):.0f} to {max(nu_err):.0f} %, because q\u00b2 \u2212 q\u2032\u00b2 is a small difference of large numbers. The windows with five settled cycles ({n_mine + n_kapil} windows: {n_mine} of mine and {n_kapil} of Kapil's) give the weighted mean \u03ba = {pm(kap, kw[1], 1e5)} \u00d7 10\u207b\u2075 m\u00b2/s
(\u03c7\u00b2 {kw[2]:.1f} for {kw[3]} degrees of freedom) and \u03bd = {pm(nu, nuw[1], 1e3)} \u00d7 10\u207b\u00b3 s\u207b\u00b9; with the handbook \u03c1 and c, k = \u03c1c\u03ba = {k_cond:.0f} W/(m K) and h = \u03c1c(D/4)\u03bd = {h_conv:.0f} W/(m\u00b2 K). The period that departs most from this pair is {worst} s
(\u03ba = {pm(wb[worst]['fin']['kappa'], wb[worst]['fin']['skappa'], 1e5)} \u00d7 10\u207b\u2075 m\u00b2/s, {n(z[worst], 1, True)}\u03c3): within its uncertainty, so I draw no trend from it.

**Checks.** (i) Residuals: after the fit the amplitudes at T3 to T5 are within {res_other:.1f} % and all phases within {res_phase:.3f} rad; the exception is T2, whose amplitude sits {min(t2_amp.values()):.1f} to {max(t2_amp.values()):.1f} % above the fit at every period
and raises \u03c7\u00b2/dof to {min(chi_dof):.1f} to {max(chi_dof):.1f} (the errors in Table 2 are scaled up accordingly). (ii) Finite length: the finite and semi-infinite amplitudes differ at T5 by {100 * wb[100]['tip']:.1f} % (100 s) to {100 * wb[480]['tip']:.1f} % (480 s), so I use the finite-rod fit;
a semi-infinite fit would give \u03ba {semi_low[400]:.1f} % (400 s) and {semi_low[480]:.1f} % (480 s) too low. (iii) Mean profile: the finite cosh fit to the mean temperatures agrees with \u221a(q\u00b2 \u2212 q\u2032\u00b2) within errors at 100, 300, 400 and 480 s ({mcmp} 1/m), as does Module 7's full-length steady-state fit of the same rod,
m = 4.12 \u00b1 0.07 1/m (`docs/module_notes/module_08_stationary_fin.md`); at 200 s the run started from room temperature without a hold, the mean was still rising and m is too large.
(iv) The transverse Biot number Bi = (D/4)\u00b2(q\u00b2 \u2212 q\u2032\u00b2) = {sci(min(w['bi'] for w in wins))} to {sci(max(w['bi'] for w in wins))} \u226a 0.1: one temperature per cross-section.
(v) The 400 s window (18 Nov) is the last five cycles of its step (cycles {wb[400]['wd']['cycles']}, no mask). The strict test counts {len(bc['block'])} of them ({bc['block'][0] + 1} to {bc['block'][-1] + 1}) because it rejects cycle {bc['cycle']} on {bc['sensor'][:2]} alone (amplitude {n(bc['dB'][2], 1, True)} %, phase {n(bc['dphi'][2], 2, True)} rad; the other sensors are within {max(abs(v) for i, v in enumerate(bc['dB']) if i != 2):.1f} %),
the effect of a burst on T3 ({bs['n']} points more than 0.25 \u00b0C from their running median, jumps up to {bs['jump']:.1f} \u00b0C between 0.5 s samples; 11:27:15 to 11:27:37, no note, cause unknown). I kept the burst in the fit (\u03ba = {pm(wb[400]['fin']['kappa'], wb[400]['fin']['skappa'], 1e5)} \u00d7 10\u207b\u2075 m\u00b2/s) and left the window out of the shared mean,
since only {len(bc['block'])} of its cycles are strictly settled. Masking T3 for those 22 s instead would give {wd_m['ncyc']} settled cycles ({wd_m['cycles']}) and \u03ba = {pm(fin_m['kappa'], fin_m['skappa'], 1e5)}, so the burst does not decide the result.

**The most important limitation.** The five periods agree with each other, so the frequency-consistency test passes, but \u03ba is {100 * (kap / kh - 1):.0f} % above the handbook {kh * 1e5:.1f} \u00d7 10\u207b\u2075 m\u00b2/s of 6061-T6 at every period (k = {k_cond:.0f} against 167 W/(m K)),
and a frequency-independent systematic cannot show up in a test across frequency. It is not the sensor spacing (the calipers read 25.4 mm; {25.4 * math.sqrt(kh / kap):.0f} mm would be needed), and not T2 (dropping it changes \u03ba by {n(max(t2_dk.values()), 1, True)} to {n(min(t2_dk.values()), 1, True)} %). The alloy,
the assumed \u03c1 and c, and the effective bead positions are untested.

![Spatial fits](../figures/module_08_sammy/a5_fig3_spatial.png)

**Figure 3.** (a) ln of the amplitude ratio, (b) unwrapped phase and (c) mean excess temperature against distance from the T1 hole for the five windows (SAMMY 16 Nov 100 s and 480 s, SAMMY 16 Nov 200 s, Kapil 4 Nov 300 s, SAMMY 18 Nov 400 s; cycles in Table 2),
with the finite-rod curves of the fitted q and q\u2032 and the cosh fit of the mean.

**Table 2.** Spatial fits of the five production windows (finite insulated tip; settled cycles are numbered from the start of the step; \u03ba<sub>sh</sub> is the shared value above; the 400 s window is the last five cycles of its step, Checks (v)). Intervals, residuals, finite-length differences, mean-profile slopes and Biot numbers are in `a5_windows.csv`.

{t2}

### Question 4: how well do theory, experiment and simulation agree?

**The matched run and its inputs.** The comparison uses Kapil's 4 Nov 300 s PI run (settled cycles 2 to 7, t = 887 to 2687 s, room {M.T_AMB_4NOV:.1f} \u00b0C), the period the course suggests. *Measured:* the geometry (D = 12.757 mm, L = 281.9 mm, sensor positions), the room temperature,
the T1 and TEC histories, the plate numbers C = {M.S.C_PLATE:.0f} J/K and H = {M.S.H_PLATE:.2f} W/K (Module 6) and \u03c7<sub>h</sub> = {M.S.CHI_H:.3f}, \u03c7<sub>c</sub> = {M.S.CHI_C:.3f} \u00b0C per count (Module 4). *Fitted:* \u03ba and \u03bd (the shared pair, which includes this window),
and a contact conductance G<sub>c</sub> = {g_c:.3f} W/K with a {tau_s:.1f} s thermistor lag, fitted to the T1/TEC amplitude ratio and phase of my 16 and 17 Nov windows at 100, 200 and 400 s, not to this run. *Assumed:* the handbook \u03c1c (it turns G<sub>c</sub> into a heat flow), an insulated tip and one side-loss rate.
The **analytical prediction** is the finite-rod solution of Question 2 driven by the measured T1 (its mean, amplitude and phase over these cycles) with the shared \u03ba and \u03bd. The **numerical simulation** is a one-lump TEC plate, the contact conductance and a finite-difference rod with the sketch's
controller (PI, Kp 12, Ki 0.2, r = 2.771, conditional integration, \u00b1255 counts, 0.54 s step), run on the recorded setpoint from the recorded temperatures at the start of the schedule (`python/sammy_module8_tec_rod_sim.py`; it is not the course web simulator).

**Boundary first.** The simulated TEC has mean {tec['sim']['a']:.2f} against {tec['meas']['a']:.2f} \u00b0C, amplitude {tec['sim']['B']:.2f} against {tec['meas']['B']:.2f} \u00b0C and a phase {M.wrap(tec['sim']['phi'] - tec['meas']['phi']):.3f} rad ahead; the simulated T1 has
{sp['T1_C']['num']['rB']:.3f} of the measured amplitude and a phase {sp['T1_C']['num']['dphi']:.3f} rad ahead ({sp['T1_C']['num']['dphi'] / cp['w']:.1f} s), with the mean {abs(sp['T1_C']['num']['da']):.2f} \u00b0C low. The model reproduces the boundary waveform to {100 * (1 - sp['T1_C']['num']['rB']):.1f} % and {sp['T1_C']['num']['dphi']:.2f} rad.

**One agreement: amplitude and phase along the rod** (Table 3, Figure 4). Driven by the measured T1, the analytical amplitudes are within {100 * max(abs(1 - sp[c]['ana']['rB']) for c in ('T3_C', 'T4_C', 'T5_C')):.1f} % of the measurements at T3 to T5 and the phases within {max(abs(sp[c]['ana']['dphi']) for c in ('T2_C', 'T3_C', 'T4_C', 'T5_C')):.3f} rad.
The numerical amplitudes are {100 * (1 - sp['T5_C']['num']['rB']):.0f} to {100 * (1 - sp['T2_C']['num']['rB']):.0f} % low and its phases {min(sp[c]['num']['dphi'] for c in ('T2_C', 'T3_C', 'T4_C', 'T5_C')):.2f} to {max(sp[c]['num']['dphi'] for c in ('T2_C', 'T3_C', 'T4_C', 'T5_C')):.2f} rad ahead, but by almost the same fraction as at T1: the transfer from T1 to T5
is reproduced to {100 * abs(1 - rod_t5[0]):.1f} % in amplitude and {abs(rod_t5[1]):.3f} rad in phase. The difference therefore belongs to the boundary (contact conductance and plate model: control and sensor behaviour), not to heat transport in the rod. T2 stands out in both models,
{100 * (1 - sp['T2_C']['ana']['rB']):.1f} % low, the T2 excess of Question 3. Because \u03ba and \u03bd include this window, the analytical comparison is a consistency check, not an independent test; the numerical TEC and T1 histories are partly independent, since G<sub>c</sub> came from other runs and the plate numbers
from Modules 4 and 6, but the controller is assumed to be the sketch's.

**One meaningful discrepancy: the mean temperature.** Both models are cooler than the measured mean and the offset grows along the rod: the analytical means are {n(sp['T2_C']['ana']['da'], 2, True)} to {n(sp['T5_C']['ana']['da'], 2, True)} \u00b0C at T2 to T5, the numerical ones {n(sp['T1_C']['num']['da'], 2, True)} to {n(sp['T5_C']['num']['da'], 2, True)} \u00b0C at T1 to T5.
The model mean decays with m = {m_shared:.2f} 1/m against {wb[300]['prof']['m']:.2f} \u00b1 {wb[300]['prof']['sm_stat']:.2f} 1/m fitted to this run's mean profile. The 300 s window's own \u03bd ({pm(fl['nu'], fl['snu'], 1e3)} \u00d7 10\u207b\u00b3 s\u207b\u00b9, {abs(z300):.1f}\u03c3 below the shared value) gives
m = {m300w:.2f} 1/m and brings the analytical means to within {max(abs(v) for v in ana_w_da):.2f} \u00b0C. The room was {M.T_AMB_4NOV:.1f} \u00b0C on 4 Nov against about 22 \u00b0C in my runs, and a smaller excess temperature means a smaller natural-convection h, which is the direction of the difference.
The \u03bd spread between windows (Table 2) is as large as this effect, so I cannot tell a real h(\u0394T) from statistical scatter.

**Table 3.** Matched 300 s run, cycles 2 to 7. Differences are prediction minus measurement; the amplitude ratio is prediction over measurement; phases are in rad.

{t3}

![Matched comparison](../figures/module_08_sammy/a5_fig4_comparison.png)

**Figure 4.** Kapil's 4 Nov 300 s run, last three of cycles 2 to 7 (t = 1787 to 2687 s). (a) setpoint, TEC and T1: measurement against the numerical simulation. (b) T3 and T5: measurement, analytical prediction (driven by the measured T1) and numerical simulation.
(c) to (e) per-sensor amplitude ratio (prediction over measurement), phase difference and mean difference (prediction minus measurement) over cycles 2 to 7.

### Conclusion

The aluminium rod behaves as a one-dimensional rod that diffuses and loses heat to the air: the amplitude and phase lengths grow as \u221a\u03c4, one pair of parameters describes all periods (\u03ba = {pm(kap, kw[1], 1e5)} \u00d7 10\u207b\u2075 m\u00b2/s, \u03bd = {pm(nu, nuw[1], 1e3)} \u00d7 10\u207b\u00b3 s\u207b\u00b9,
h \u2248 {h_conv:.0f} W/(m\u00b2 K)), and a finite-rod calculation and a coupled TEC and rod simulation both reproduce the 300 s run to a few percent in amplitude and a few hundredths of a radian in phase. The TEC follows the requested sinusoid only at the longer periods (at Kp 12 a delay of 10 to 13 s
limits the phase; a higher Kp shortens it to {bm('kp20', 'lag_s'):.0f} s but then clips the PWM at 100 s), so the rod is analysed from T1, not from the setpoint. The conclusion is limited by a {100 * (kap / kh - 1):.0f} % excess of \u03ba over the handbook value that a test across frequencies cannot reveal, a \u03bd good to only {min(nu_err):.0f} to {max(nu_err):.0f} % per window and a 400 s window with {len(bc['block'])} strictly settled cycles out of its five. The one measurement that would best resolve the first is an independent determination of the rod's conductivity or alloy (its density from mass and volume, or a steady-state conduction measurement with a known heater power), which would show whether the excess is in k or in the effective sensor spacing.

**AI assistance.** The analysis code, the numerical TEC and rod model and the first draft of this account were written with an AI assistant (GitHub Copilot). Every number and figure is regenerated from the raw files by the scripts named in Part 1, and I am responsible for the content.
"""
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote", os.path.relpath(OUT_MD, A.REPO), len(text.split()), "words")


if __name__ == "__main__":
    main()
