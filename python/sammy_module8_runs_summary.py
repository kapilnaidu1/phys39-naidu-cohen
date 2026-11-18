#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I: SAMMY runs of 16 and 17 Nov 2026 (PI 200 s, S18.4 raw PWM, PI 400 s) and every period compiled.  SAMMY copy.

    python3 python/sammy_module8_runs_summary.py

Reads the analysis tables of every SAMMY run (data/module_08_sammy/analysis_<stamp>/), refits every window with the finite-rod
(insulated tip) model of python/sammy_module8_finite_rod.py, reads the 16 and 17 Nov run files with their _events.txt and _notes.csv
and the S18.4 report, and writes
    docs/sammy_module_08_guide/Sammy_Module_8_Runs_16_17Nov_Summary.md
    data/module_08_sammy/compiled_periods.csv and finite_rod_fits.csv
    docs/figures/module_08_sammy/compiled_kappa_vs_period.png, compiled_characteristic_length.png
Every number in the text comes from those files. Kapil Naidu's fits are constants: KAPIL of the analysis script (his two-line
semi-infinite fits) and KAPIL_FIN, KAPIL_11 below (his finite-rod fits, data/module_08/angstrom_finite_*.txt on the shared branch).
"""

import csv
import json
import math
import os
import re
import warnings
from datetime import datetime, timedelta

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator

import sammy_module8_angstrom_analysis as A
import sammy_module8_finite_rod as FR

warnings.filterwarnings("ignore", category=RuntimeWarning)

REPO, DATA_DIR, GUIDE_DIR, FIG_DIR = A.REPO, A.DATA_DIR, A.GUIDE_DIR, A.FIG_DIR
RUN16, RUN17 = "20261116_111935", "20261117_162612"
PH1 = "20261116_111935_phase1_pi200s"
OUT = os.path.join(GUIDE_DIR, "Sammy_Module_8_Runs_16_17Nov_Summary.md")
COMPILED = os.path.join(DATA_DIR, "compiled_periods.csv")
T_ROOM = {PH1: 22.7, RUN17: 22.4}

# Kapil's finite-rod fits, period s -> (kappa, error, q, error, q', error, nu, error, settled cycles of his Part II table)
KAPIL_FIN = {100: (9.74e-5, 0.23e-5, 18.55, 0.29, 17.39, 0.31, 4.05e-3, 1.48e-3, 5),
             180: (9.19e-5, 0.20e-5, 14.13, 0.23, 13.44, 0.20, 1.73e-3, 0.77e-3, 5),
             240: (9.36e-5, 0.17e-5, 12.30, 0.15, 11.37, 0.15, 2.06e-3, 0.47e-3, 5),
             300: (9.33e-5, 0.15e-5, 10.94, 0.12, 10.27, 0.12, 1.32e-3, 0.35e-3, 6),
             480: (9.40e-5, 0.24e-5, 9.02, 0.18, 7.72, 0.13, 2.04e-3, 0.36e-3, 5)}
# His 11 Nov 480 s repeat: two-line semi-infinite fit (kappa, error, q, q') and finite-rod fit (as above)
KAPIL_11 = dict(semi=(8.843e-5, 3.3e-6, 9.37, 7.90), fin=(9.27e-5, 0.35e-5, 9.05, 0.26, 7.80, 0.19, 1.96e-3, 0.52e-3, 6))
# His finite-rod kappa for the 10 Nov SAMMY run (angstrom_finite_sammy_angstrom_live_20261110_164057.txt): the check of the fit code
KAPIL_10NOV = {100: 9.28e-5, 240: 9.10e-5, 480: 9.22e-5}

# (label, analysis stem, marker, colour)
RUNS = [("SAMMY 10 Nov", "20261110_164057", "o", "#1F4E79"),
        ("SAMMY 16 Nov, morning", "20261116_090538", "s", "#2a9d8f"),
        ("SAMMY 16 Nov, PI 200 s", PH1, "^", "#e07b00"),
        ("SAMMY 17 Nov, PI 400 s", RUN17, "D", "#8e44ad")]

# Phone photos of the live GUI, straightened and cropped to the GUI window:
# (file in docs/images, run stamp, "valid" count on screen = record number, t on screen, photo id, phone clock)
PHOTOS = [("module08_sammy_gui_plan_phase1_t798s_IMG_2645.jpg", RUN16, 1469, 798.2, "IMG_2645", "11:32 AM"),
          ("module08_sammy_gui_plan_phase2_t2144s_IMG_2646.jpg", RUN16, 3957, 2143.9, "IMG_2646", "11:55 AM"),
          ("module08_sammy_gui_pi400_step2_t2971s_IMG_2663.jpg", RUN17, 5499, 2970.8, "IMG_2663", "5:15 PM"),
          ("module08_sammy_gui_pi400_done_t4625s_IMG_2664.jpg", RUN17, 8549, 4625.4, "IMG_2664", "5:43 PM")]


def read_csv(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def run_path(stamp):
    return os.path.join(DATA_DIR, f"sammy_angstrom_live_{stamp}.csv")


def adir(stamp):
    return os.path.join(DATA_DIR, f"analysis_{stamp}")


def read_events(stamp):
    out = []
    with open(run_path(stamp).replace(".csv", "_events.txt")) as fh:
        for line in fh:
            wall, _, text = line.rstrip("\n").partition("\t")
            out.append((datetime.fromisoformat(wall), text.strip()))
    return out


def tms(text):
    return int(re.search(r"t_ms=(\d+)", text).group(1)) / 1000.0


def hhmmss(w):
    return w.strftime("%H:%M:%S")


def f(v, d=2):
    return "nan" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{d}f}"


def pm(v, s, scale=1.0, d=2):
    return f"{f(v * scale, d)} ± {f(s * scale, d)}"


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    return out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


# ---------------------------------------------------------------------------
# compiled results
# ---------------------------------------------------------------------------

def kapil_rows():
    nan = float("nan")
    base = dict(stamp=None, recorded=None, meets=1, marker="s", color="#888888", kapil=True, settled_by="Kapil's selection",
                kappa5=nan, skappa5=nan, ks5=nan, sks5=nan, chi2=nan, dof=0, k_noT2=nan, chi2_noT2=nan, dof_noT2=0, dlnB2=nan,
                dphi2=nan, m_mean=nan, sm_mean=nan, tip=nan)
    out = []
    for P, (k, sk, q, sq, qp, sqp, nu, snu, n) in KAPIL_FIN.items():
        ks, sks, qs, qps = A.KAPIL[P]
        out.append(dict(base, source="Kapil (PI, 2 and 4 Nov)", period=P, settled=n, q=q, sq=sq, qp=qp, sqp=sqp, kappa=k, skappa=sk,
                        nu=nu, snu=snu, ks=ks, sks=sks, qs=qs, qps=qps))
    (k, sk, q, sq, qp, sqp, nu, snu, n), (ks, sks, qs, qps) = KAPIL_11["fin"], KAPIL_11["semi"]
    out.append(dict(base, source="Kapil (PI, 11 Nov)", period=480, settled=n, q=q, sq=sq, qp=qp, sqp=sqp, kappa=k, skappa=sk, nu=nu,
                    snu=snu, ks=ks, sks=sks, qs=qs, qps=qps))
    return out


def compiled_rows(runs=None):
    """SAMMY rows: finite-rod fit of the strict settled block (kappa, q, q', nu) and of the last five cycles, the analysis script's
    two-line semi-infinite fit (ks, qs, qps), and the finite-rod fit without T2. Plus Kapil's rows. Also returns the raw fits.
    runs: (label, analysis stem, marker, colour) per SAMMY run; default RUNS (the page of 16 and 17 Nov); A5 adds the 18 Nov run."""
    runs = RUNS if runs is None else runs
    fin = FR.compute([s for _, s, _, _ in runs])
    rows = []
    for label, stamp, mk, col in runs:
        kap = read_csv(os.path.join(adir(stamp), "kappa_by_period.csv"))
        blk = {int(float(r["period_s"])): r for r in read_csv(os.path.join(adir(stamp), "settled_blocks.csv"))}
        for r in kap:
            P = int(float(r["period_s"]))
            fs, f5 = fin[stamp][P]["strict"], fin[stamp][P]["last5"]
            assert len(fs["cycles"]) == int(r["settled_cycles"]), (stamp, P)
            assert abs(fs["semi"]["kappa"] / float(r["kappa_m2_s"]) - 1) < 0.01, (stamp, P)   # joint semi-infinite fit against the two lines
            ff, n2 = fs["finite"], fs["finite_noT2"]
            rows.append(dict(source=label, stamp=stamp, period=P, recorded=int(blk[P]["cycles_recorded"]), settled=len(fs["cycles"]),
                             meets=int(blk[P]["meets_5_cycle_minimum"]), settled_by="strict test", kapil=False,
                             q=ff["q"], sq=ff["sq"], qp=ff["qp"], sqp=ff["sqp"], kappa=ff["kappa"], skappa=ff["skappa"], nu=ff["nu"],
                             snu=ff["snu"], chi2=ff["chi2"], dof=ff["dof"], kappa5=f5["finite"]["kappa"],
                             skappa5=f5["finite"]["skappa"], k_noT2=n2["kappa"], chi2_noT2=n2["chi2"], dof_noT2=n2["dof"],
                             dlnB2=100 * float(ff["dlnB"][1]), dphi2=float(ff["dphi"][1]),
                             qs=float(r["q_1_m"]), qps=float(r["qprime_1_m"]), ks=float(r["kappa_m2_s"]), sks=float(r["skappa_m2_s"]),
                             ks5=float(r["kappa_last5_m2_s"]), sks5=float(r["skappa_last5_m2_s"]),
                             m_mean=float(r["m_mean_profile_1_m"]), sm_mean=float(r["sm_mean_profile_1_m"]),
                             tip=float(r["finite_length_max_rel_diff"]), marker=mk, color=col))
    return sorted(rows + kapil_rows(), key=lambda r: (r["period"], r["source"])), fin


def write_compiled(rows):
    c = lambda v, fmt: "" if v is None or (isinstance(v, float) and math.isnan(v)) else format(v, fmt)
    with open(COMPILED, "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["source", "period_s", "cycles_recorded", "settled_cycles", "settled_by", "meets_5_cycle_minimum",
                    "q_finite_1_m", "sq_finite_1_m", "qprime_finite_1_m", "sqprime_finite_1_m", "kappa_finite_m2_s", "skappa_finite_m2_s",
                    "nu_finite_1_s", "snu_finite_1_s", "kappa_finite_last5_m2_s", "skappa_finite_last5_m2_s", "q_semi_1_m",
                    "qprime_semi_1_m", "kappa_semi_m2_s", "skappa_semi_m2_s", "kappa_semi_last5_m2_s", "skappa_semi_last5_m2_s"])
        for r in rows:
            w.writerow([r["source"], r["period"], c(r["recorded"], "d"), r["settled"], r["settled_by"], r["meets"],
                        c(r["q"], ".3f"), c(r["sq"], ".3f"), c(r["qp"], ".3f"), c(r["sqp"], ".3f"), c(r["kappa"], ".4e"),
                        c(r["skappa"], ".2e"), c(r["nu"], ".3e"), c(r["snu"], ".2e"), c(r["kappa5"], ".4e"), c(r["skappa5"], ".2e"),
                        c(r["qs"], ".3f"), c(r["qps"], ".3f"), c(r["ks"], ".4e"), c(r["sks"], ".2e"), c(r["ks5"], ".4e"),
                        c(r["sks5"], ".2e")])


def weighted(rows, key="kappa", skey="skappa"):
    """Weighted mean, its error, chi2 about the mean and the degrees of freedom."""
    k = np.array([r[key] for r in rows])
    s = np.array([r[skey] for r in rows])
    w = 1 / s ** 2
    m = float(np.sum(w * k) / np.sum(w))
    return m, float(1 / math.sqrt(np.sum(w))), float(np.sum(w * (k - m) ** 2)), len(rows) - 1


def period_axis(ax, periods):
    ax.set_xscale("log")
    ax.set_xticks(periods)
    ax.set_xticklabels([f"{p:g}" for p in periods])
    ax.xaxis.set_minor_locator(NullLocator())
    ax.set_xlabel("forcing period (s)")


def source_label(r):
    return "Kapil (PI, 2, 4 and 11 Nov)" if r["kapil"] else r["source"]


def fig_kappa(path, rows, kw):
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    seen = set()
    for r in rows:
        lab = source_label(r)
        first = lab not in seen
        seen.add(lab)
        ax.errorbar(r["period"], r["kappa"] * 1e5, yerr=r["skappa"] * 1e5, fmt=r["marker"], ms=9, color=r["color"], capsize=4,
                    mfc=r["color"] if r["meets"] else "white", label=lab if first else None)
        ax.plot(r["period"] * 0.95, r["ks"] * 1e5, "x", color=r["color"], ms=6, mew=1.6, alpha=0.9,
                label="same window, semi-infinite fit (crosses)" if r is rows[0] else None)
    ax.axhline(A.KAPPA_HANDBOOK * 1e5, color="#C0392B", ls="--", label="handbook 6061-T6 (6.9)")
    ax.axhspan((kw[0] - kw[1]) * 1e5, (kw[0] + kw[1]) * 1e5, color="#1F4E79", alpha=0.12,
               label=f"weighted mean of the windows with ≥ 5 settled cycles: {kw[0] * 1e5:.2f} ± {kw[1] * 1e5:.2f}")
    period_axis(ax, [100, 180, 200, 240, 300, 400, 480])
    ax.set_ylabel("κ (10⁻⁵ m²/s)")
    ax.set_ylim(5, 12)
    ax.legend(fontsize=8, ncol=2, loc="lower left")
    ax.set_title("Thermal diffusivity from every period, finite-rod fit (open markers: fewer than 5 settled cycles)", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def curves(kap, nu, P):
    """1/q, 1/q' and 1/m in mm from s^2 = (nu + i w)/kappa and m^2 = nu/kappa."""
    w = 2 * math.pi / np.asarray(P, float)
    r = np.sqrt(nu ** 2 + w ** 2)
    return 1000 * np.sqrt(2 * kap / (r + nu)), 1000 * np.sqrt(2 * kap / (r - nu)), np.full(len(w), 1000 * math.sqrt(kap / nu))


def fig_length(path, rows, kw, nu, figsize=(9.4, 7.4), mean_label="SAMMY mean-profile 1/m (room T from the idle sensors)"):
    fig, ax = plt.subplots(figsize=figsize)
    P = np.logspace(math.log10(60), math.log10(700), 120)
    base = curves(kw[0], nu[0], P)
    corners = [curves(kw[0] + a * kw[1], nu[0] + b * nu[1], P) for a in (-1, 1) for b in (-1, 1)]
    green = "#2e7d32"
    for i, (name, c) in enumerate((("1/q (amplitude)", "#1F4E79"), ("1/q′ (phase)", "#e07b00"), ("1/m (mean profile)", green))):
        ax.fill_between(P, np.min([cr[i] for cr in corners], axis=0), np.max([cr[i] for cr in corners], axis=0), color=c, alpha=0.15, lw=0)
        ax.plot(P, base[i], color=c, label=name + " curve")
    seen, mean_seen = set(), False
    for r in rows:
        lab = source_label(r)
        first = lab not in seen
        seen.add(lab)
        mfc = r["color"] if r["meets"] else "white"
        ax.errorbar(r["period"], 1000 / r["q"], yerr=1000 * r["sq"] / r["q"] ** 2, fmt="o", color=r["color"], capsize=3, mfc=mfc, ms=6,
                    label=f"{lab}: 1/q (circle), 1/q′ (square)" if first else None)
        ax.errorbar(r["period"] * 1.03, 1000 / r["qp"], yerr=1000 * r["sqp"] / r["qp"] ** 2, fmt="s", color=r["color"], capsize=3,
                    mfc=mfc, ms=6)
        if not r["kapil"]:
            ax.errorbar(r["period"] * 0.97, 1000 / r["m_mean"], yerr=1000 * r["sm_mean"] / r["m_mean"] ** 2, fmt="^", color=green,
                        mfc="none", ms=6, capsize=3, alpha=0.8,
                        label=None if mean_seen else mean_label)
            mean_seen = True
    ax.axhline(1000 * A.load_geometry(A.GEOMETRY)["L"], color="#999999", ls=":", lw=1)
    ax.text(135, 1000 * A.load_geometry(A.GEOMETRY)["L"] + 4, "analysis length L = 281.9 mm (T1 hole to rod top)", fontsize=9, color="#666666")
    ax.axhline(101.6, color="#999999", ls=":", lw=1)
    ax.text(62, 105, "T1 to T5 spacing 101.6 mm", fontsize=9, color="#666666")
    period_axis(ax, [100, 200, 300, 400, 500])
    ax.set_ylabel("characteristic length (mm)")
    ax.set_ylim(30, 360)
    ax.set_title("Characteristic lengths against period\n"
                 f"curves: κ = {kw[0] * 1e5:.2f}e-5 m²/s, ν = {nu[0] * 1e3:.2f}e-3 1/s (weighted means of the windows with ≥ 5 settled cycles), "
                 "bands ±1 standard error", fontsize=9.5)
    ax.legend(fontsize=7.5, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# the page
# ---------------------------------------------------------------------------

def main():
    rows, fin = compiled_rows()
    write_compiled(rows)
    FR.write_csv(FR.OUT, fin)
    sam5 = [r for r in rows if r["meets"] and not r["kapil"]]
    all5 = [r for r in rows if r["meets"]]
    kw_s, kw_a, nu_a = weighted(sam5), weighted(all5), weighted(all5, "nu", "snu")
    fig_kappa(os.path.join(FIG_DIR, "compiled_kappa_vs_period.png"), rows, kw_a)
    fig_length(os.path.join(FIG_DIR, "compiled_characteristic_length.png"), rows, kw_a, nu_a)
    one = lambda P, src: next(r for r in rows if r["period"] == P and r["source"] == src)
    for P, v in KAPIL_10NOV.items():
        assert abs(one(P, "SAMMY 10 Nov")["kappa"] - v) < 0.021e-5, P        # this fit code against Kapil's own finite-rod output

    # ---- the two runs: events and notes
    ev16, ev17 = read_events(RUN16), read_events(RUN17)
    notes16 = read_csv(run_path(RUN16).replace(".csv", "_notes.csv"))
    notes17 = read_csv(run_path(RUN17).replace(".csv", "_notes.csv"))
    c16, c17 = A.load(run_path(RUN16)), A.load(run_path(RUN17))
    starts16 = [e for e in ev16 if "SCHEDULE START" in e[1]]
    done16 = [e for e in ev16 if "SCHEDULE DONE" in e[1]]
    ph16 = [(n["wall_clock"], re.sub(r"\s*\((PI|RAW)\)$", "", n["note"].replace("\n", " "))) for n in notes16 if n["note"].startswith("PLAN phase")]
    start17 = next(e for e in ev17 if "SCHEDULE START" in e[1])
    step2_17 = next(e for e in ev17 if "SCHEDULE STEP 2" in e[1])
    done17 = next(e for e in ev17 if "SCHEDULE DONE" in e[1])
    stop17 = next(e for e in ev17 if e[1].startswith("SENT STOP"))
    sent17 = next(e for e in ev17 if e[1].startswith("schedule sent"))
    refused17 = [e for e in ev17 if e[1] == "SENT SCHED START"][:-1]          # the clicks before the one that started the run
    wall16 = lambda ts: starts16[-1][0] + timedelta(seconds=ts - tms(starts16[-1][1]))
    wall17 = lambda ts: start17[0] + timedelta(seconds=ts - tms(start17[1]))
    last16 = float(c16["t"][-1])
    rs17 = json.load(open(os.path.join(adir(RUN17), "run_summary.json")))
    rs16 = json.load(open(os.path.join(adir(PH1), "run_summary.json")))
    tamb = {s: [(w, float(re.search(r"SET TAMB ([\d.]+)", x).group(1))) for w, x in ev if x.startswith("SENT SET TAMB")]
            for s, ev in ((RUN16, ev16), (RUN17, ev17))}
    ref = {RUN16: (c16, wall16), RUN17: (c17, wall17)}
    sched_idx = np.flatnonzero(c17["run_state"] == 2)
    tec_done = float(c17["TEC_C"][sched_idx[-1]])

    # ---- photos
    photo_md = []
    for fname, stamp, k, t_screen, pid, clock in PHOTOS:
        c, wall = ref[stamp]
        t = c["t"]
        i = k - 1
        assert abs(t[i] - t_screen) < 0.06, (pid, t[i], t_screen)
        temps = ", ".join(f"T{j} {f(c[f'T{j}_C'][i])}" for j in range(1, 6))
        box = [v for w, v in tamb[stamp] if w <= wall(t[i])]
        remark = ""
        if pid == "IMG_2645":
            remark = "Phase 1 of the plan; the plots show the first three 200 s cycles."
        if pid == "IMG_2646":
            remark = "Phase 2 of the plan (RAW); the blue patch at the right edge is a reflection on the glass."
        if pid == "IMG_2663":
            remark = "The plots show the last 600 s of the 400 s run."
        if pid == "IMG_2664":
            remark = (f"After `SCHEDULE DONE` at t = {tms(done17[1]):.1f} s the output is 0 (the TEC thermistor read {f(tec_done)} °C at "
                      f"the last scheduled record), so it decays afterwards.")
        title = f"{pid}, {clock}: step {int(c['step'][i])} ({f(c['period_s'][i], 0)} s period), t = {t[i]:.1f} s"
        if int(c["step"][i]) == 0:
            title = f"{pid}, {clock}: idle after the schedule, t = {t[i]:.1f} s"
        cap = (f"setpoint {f(c['setpoint_C'][i])} °C, TEC {f(c['TEC_C'][i])} °C, {temps} °C; applied PWM "
               f"{int(c['signed_pwm'][i]):+d} (record {k}); room T box {box[-1]:.2f}. {remark}").strip()
        photo_md.append(f"![{title}](../images/{fname})\n\n*{title}. On screen: {cap}*")

    # ---- 16 Nov PI 200 s and S18.4
    p200 = next(r for r in rows if r["stamp"] == PH1)
    trk200 = read_csv(os.path.join(adir(PH1), "tracking_by_period.csv"))[0]
    s184 = open(os.path.join(adir(RUN16 + "_phase2_raw100s"), "report.txt")).read().rstrip("\n")

    # ---- 17 Nov PI 400 s
    p400 = next(r for r in rows if r["stamp"] == RUN17)
    trk400 = read_csv(os.path.join(adir(RUN17), "tracking_by_period.csv"))[0]
    kap400 = read_csv(os.path.join(adir(RUN17), "kappa_by_period.csv"))[0]
    per = {}
    for r in read_csv(os.path.join(adir(RUN17), "cycle_fits.csv")):
        per.setdefault(int(r["cycle"]), {})[r["channel"]] = r
    t = c17["t"]
    _, data, _ = A.prepare(c17, A.load_offsets(A.OFFSETS), {})
    info = next(s for s in A.find_steps(c17) if s["tb"] > 0)
    cf = A.cycle_fits(t, data, info)
    ncyc = info["ncyc"]
    x, dx = A.load_positions(A.SENSOR_MAP)
    block, B, PH, fail = A.settled_block(cf, ncyc)
    names = {"after": "all cycles after the start-up cycle (2 to 7)", "last5": "last five cycles (3 to 7)"}
    blocks = {"after": list(range(1, ncyc)), "last5": list(range(ncyc - 5, ncyc))}
    frb = FR.fit_blocks(t, data, info, cf, blocks, x, dx, A.load_geometry(A.GEOMETRY)["L"])
    alt = {}
    for key, name in names.items():
        blk = A.analyse_block(t, data, info, cf, blocks[key])
        alt[name] = A.spatial(blk["fits"], blk["w"], x, dx)
    rel = {ch: 100 * (B[:, i] / B[1:, i].mean() - 1) for i, ch in enumerate(A.ROD)}      # per cycle against the mean of cycles 2 to 7
    lo = min(v[1:].min() for v in rel.values())
    hi = max(v[1:].max() for v in rel.values())
    dphi = float(np.max(np.abs(A.wrap(PH[1:] - np.mean(PH[1:], axis=0)))))
    hold = rs17["hold"]
    cyc_rows = []
    for k in range(1, ncyc + 1):
        v = per[k]
        cyc_rows.append([k, f(float(v["TEC"]["mean_C"])), f(float(v["T1"]["B_C"]), 3), f(float(v["T3"]["B_C"]), 3),
                         f"{rel['T3_C'][k - 1]:+.1f}", f(float(v["T5"]["B_C"]), 3), f(float(v["T5"]["mean_C"])),
                         "yes" if v["T1"]["in_settled_block"] == "1" else "no"])
    kalts = [p400["kappa"]] + [frb[k]["finite"]["kappa"] for k in names]

    # ---- tables
    def res_row(r):
        return [r["period"], f"{r['settled']} of {r['recorded']}", pm(r["q"], r["sq"]), pm(r["qp"], r["sqp"]),
                pm(r["kappa"], r["skappa"], 1e5), pm(r["ks"], r["sks"], 1e5), pm(r["nu"], r["snu"], 1e3), pm(r["kappa5"], r["skappa5"], 1e5)]

    head_res = ["Period (s)", "Settled cycles (strict test)", "q (1/m)", "q′ (1/m)", "κ, finite rod (10⁻⁵ m²/s)", "κ, semi-infinite",
                "ν (10⁻³ 1/s)", "κ, last five cycles (finite rod)"]
    comp = [[r["period"], r["source"], f"{r['settled']} (his selection)" if r["kapil"] else f"{r['settled']} of {r['recorded']}",
             "yes" if r["meets"] else "no", f(r["q"]), f(r["qp"]), pm(r["kappa"], r["skappa"], 1e5), pm(r["ks"], r["sks"], 1e5),
             "" if r["kapil"] else pm(r["kappa5"], r["skappa5"], 1e5)] for r in rows]
    r100b, r100a = one(100, "SAMMY 16 Nov, morning"), one(100, "SAMMY 10 Nov")
    r480b, r480a = one(480, "SAMMY 16 Nov, morning"), one(480, "SAMMY 10 Nov")
    k300 = one(300, "Kapil (PI, 2 and 4 Nov)")
    cover = [
        ["100 s", f"SAMMY 16 Nov morning ({r100b['settled']} settled cycles), SAMMY 10 Nov ({r100a['settled']}), Kapil", pm(r100b["kappa"], r100b["skappa"], 1e5), "covered"],
        ["200 s", f"SAMMY 16 Nov, phase 1 of the GUI plan ({p200['settled']} settled cycles)", pm(p200["kappa"], p200["skappa"], 1e5), "covered"],
        ["300 s", "Kapil, 4 Nov (SAMMY did not repeat it)", pm(k300["kappa"], k300["skappa"], 1e5), "covered (Kapil)"],
        ["400 s", f"SAMMY 17 Nov (7 cycles recorded, {p400['settled']} settled by the strict test)",
         f"{pm(p400['kappa'], p400['skappa'], 1e5)} (last five cycles {pm(p400['kappa5'], p400['skappa5'], 1e5)})",
         "recorded; the strict count is below five (see the 17 Nov section)"],
        ["500 s", f"the 480 s runs: SAMMY 16 Nov morning ({r480b['settled']} settled cycles), SAMMY 10 Nov ({r480a['settled']}), Kapil",
         pm(r480b["kappa"], r480b["skappa"], 1e5), "covered with 480 s for 500 s, as in the gap analysis"]]

    k_all = np.array([r["kappa"] for r in rows])
    kf_short = np.mean([r["kappa"] for r in rows if r["period"] <= 300])
    kf_long = np.mean([r["kappa"] for r in rows if r["period"] >= 400])
    ks_short = np.mean([r["ks"] for r in rows if r["period"] <= 300])
    ks_long = np.mean([r["ks"] for r in rows if r["period"] >= 400])
    q_gt = all(r["q"] > r["qp"] for r in rows)
    rat = {}
    for r in rows:
        if not r["kapil"]:
            rat.setdefault(r["period"], []).append(r["kappa"] / r["ks"])
    rat_txt = ", ".join(f"{np.mean(v):.3f} at {P} s" for P, v in sorted(rat.items()))
    own = [r for r in rows if not r["kapil"]]
    t2_rows = [[r["source"], r["period"], f"{r['dlnB2']:+.1f}", f"{r['dphi2']:+.3f}", f"{100 * (r['k_noT2'] / r['kappa'] - 1):+.1f}",
                f"{r['chi2']:.1f} → {r['chi2_noT2']:.1f}"] for r in own]
    d2 = [100 * (r["k_noT2"] / r["kappa"] - 1) for r in own]
    nl = chr(10)

    run_rows = [
        [f"16 Nov, plan run (GUI started 11:19:35, {len(c16['t'])} records, t = {c16['t'][0]:.1f} to {last16:.1f} s)",
         f"{ph16[0][1].split(': ', 1)[1]} from {ph16[0][0][11:]}; {ph16[1][1].split(': ', 1)[1]} from {ph16[1][0][11:]}; "
         f"{ph16[2][1].split(': ', 1)[1]} from {ph16[2][0][11:]}. The first two schedules ended with `SCHEDULE DONE` at {hhmmss(done16[0][0])} and "
         f"{hhmmss(done16[1][0])}. The GUI process ended at {hhmmss(wall16(last16))} (last record), 1997 s into the 2800 s step of the 400 s run "
         f"(4 whole cycles), with no STOP in the events file; the cause is unknown."],
        [f"17 Nov, PI 400 s repeat (GUI started 16:26:11, {len(c17['t'])} records, t = {c17['t'][0]:.1f} to {c17['t'][-1]:.1f} s)",
         f"Idle lead-in with supply and pump off (room T 22.4 °C, note at {notes17[0]['wall_clock'][11:]}), pump on at about "
         f"{notes17[1]['wall_clock'][11:]}. Schedule `300 40 0 100` + `2800 40 16 400` sent at {hhmmss(sent17[0])}, START at "
         f"{hhmmss(start17[0])} (the earlier START clicks at {', '.join(hhmmss(e[0]) for e in refused17)} were refused by the board because no "
         f"schedule was loaded, with no effect on the data). Step 2 from {hhmmss(step2_17[0])}, `SCHEDULE DONE` at {hhmmss(done17[0])}, GUI closed "
         f"with STOP at {hhmmss(stop17[0])}. 0 malformed, 0 duplicated, 0 restarts."]]
    photos_text = (nl + nl).join(photo_md)
    alt_rows = ([[f"strict block (cycles {block[0] + 1} to {block[-1] + 1})", pm(p400["q"], p400["sq"]), pm(p400["qp"], p400["sqp"]),
                  pm(p400["kappa"], p400["skappa"], 1e5), pm(p400["ks"], p400["sks"], 1e5)]]
                + [[names[k], pm(frb[k]["finite"]["q"], frb[k]["finite"]["sq"]), pm(frb[k]["finite"]["qp"], frb[k]["finite"]["sqp"]),
                    pm(frb[k]["finite"]["kappa"], frb[k]["finite"]["skappa"], 1e5),
                    pm(alt[names[k]]["kappa"], alt[names[k]]["skappa"], 1e5)] for k in names])

    text = f"""# Module 8, Part I: SAMMY runs of 16 and 17 November 2026, and all periods compiled

Summary of the 16 Nov GUI plan run (`sammy_angstrom_live_{RUN16}.csv`: PI 200 s, S18.4 positive-only PWM, interrupted PI 400 s) and of the
17 Nov PI 400 s repeat (`sammy_angstrom_live_{RUN17}.csv`), written by `python/sammy_module8_runs_summary.py`.
Tables and reports: `data/module_08_sammy/analysis_<stamp>/` (the 16 Nov run is analysed phase by phase from verbatim slices of the file),
compiled table `data/module_08_sammy/compiled_periods.csv`, finite-rod fits `data/module_08_sammy/finite_rod_fits.csv`. Figures:
`docs/figures/module_08_sammy/`. Photos: `docs/images/module08_sammy_gui_plan_*.jpg` and `module08_sammy_gui_pi400_*.jpg`. Kapil Naidu's
acquisition code, analysis scripts and data are unchanged; everything here is an addition.

**Fits.** q, q′, κ and ν are joint finite-rod (insulated tip) fits of the five per-sensor amplitudes and phases, L = 281.9 mm
(`python/sammy_module8_finite_rod.py`, the method of Kapil's `angstrom_finite_fit.py`); the semi-infinite columns are the two-line fits of the
analysis script. On the 10 Nov SAMMY run the finite-rod code gives κ = {one(100, 'SAMMY 10 Nov')['kappa'] * 1e5:.2f}, {one(240, 'SAMMY 10 Nov')['kappa'] * 1e5:.2f} and
{one(480, 'SAMMY 10 Nov')['kappa'] * 1e5:.2f} × 10⁻⁵ m²/s at 100, 240 and 480 s, the values in Kapil's own finite-rod output for that run.

## What was run

{nl.join(table(["Run", "What happened"], run_rows))}

## Photos of the runs

Phone photos of the laptop screen during the runs, straightened and cropped to the GUI window (metadata removed; the full-screen originals are
not in the repository). The numbers on screen are the logged values: the temperatures, the PWM and the stream's valid-record count equal the
CSV record with that number. The window is cropped a few pixels inside its edges.

{photos_text}

## 16 Nov, phase 1: PI 200 s (S18.10, Stage 5 at 200 s)

Slice `sammy_angstrom_live_{RUN16}_phase1_pi200s.csv`, analysed with `python3 python/sammy_module8_angstrom_analysis.py ... --t-room {T_ROOM[PH1]:g} --summary none`
(room T from the calibrated idle sensors before the plan). PI settings Kp 12, Ki 0.2, r 2.771; no sample masked.

{nl.join(table(head_res, [res_row(p200)]))}

Tracking: B_TEC/Tb = {f(float(trk200['B_TEC_over_Tb']), 3)}, TEC lag {f(float(trk200['TEC_lag_s']), 1)} s, B_T1/Tb = {f(float(trk200['B_T1_over_Tb']), 3)}, T1 lag {f(float(trk200['T1_lag_s']), 1)} s,
PWM {trk200['pwm_min']} to {trk200['pwm_max']} in the settled block (whole slice {rs16['pwm_min']} to {rs16['pwm_max']}, never at ±255). The TEC peaked at {rs16['tec_max_C']:.1f} °C and T1 at {rs16['t1_max_C']:.1f} °C
(limits 65 and 56 °C). Figures: `{PH1}_*.png`.

## 16 Nov, phase 2: S18.4 positive-only PWM

Slice `sammy_angstrom_live_{RUN16}_phase2_raw100s.csv`, analysed with the new `python/sammy_module8_s184_analysis.py` (settled cycles chosen from the TEC
because the rod amplitudes are only 0.15 to 1 °C); the prediction is the one of `Sammy_Module_8_S18_4_Positive_Only_PWM_Walkthrough.md`. Report
`data/module_08_sammy/analysis_{RUN16}_phase2_raw100s/report.txt`:

```text
{s184}
```

Figures: `{RUN16}_phase2_raw100s_s184_overview.png` (measured against the prediction) and `{RUN16}_phase2_raw100s_s184_shape.png` (the cycle shape against S18.3).

## 17 Nov: PI 400 s (Stage 5 at 400 s)

Analysed with `python3 python/sammy_module8_angstrom_analysis.py data/module_08_sammy/sammy_angstrom_live_{RUN17}.csv --t-room {T_ROOM[RUN17]:g} --summary none`
(room T from the idle sensors before the pump was switched on). Hold step: the TEC reached 39.5 °C after {hold['t_reach']:.0f} s with {hold['overshoot']:+.2f} °C
overshoot, peak PWM {hold['pwm_max']}. The PWM then ran {trk400['pwm_min']} to {trk400['pwm_max']} (never at ±255); the TEC peaked at {rs17['tec_max_C']:.1f} °C and T1 at
{rs17['t1_max_C']:.1f} °C. No sample was masked.

{nl.join(table(head_res, [res_row(p400)]))}

Tracking: B_TEC/Tb = {f(float(trk400['B_TEC_over_Tb']), 3)}, TEC lag {f(float(trk400['TEC_lag_s']), 1)} s, B_T1/Tb = {f(float(trk400['B_T1_over_Tb']), 3)}, T1 lag {f(float(trk400['T1_lag_s']), 1)} s.

**The settling test is the limit of this run.** Counting back from the last cycle, a cycle joins the settled block while every rod sensor stays within 3 % in
amplitude and 0.05 rad in phase of the block median (tolerances chosen for this analysis). Cycle {fail['cycle'] + 1} fails it: its {A.label(A.ROD[fail['sensor']])} amplitude is {fail['dB']:+.1f} % from
the median of cycles {block[0] + 1} to {block[-1] + 1}, so the block is those {len(block)} cycles and the five-cycle minimum is not met by the strict count. The cycles are otherwise consistent:
after the start-up cycle 1, cycles 2 to 7 agree within {lo:+.1f} to {hi:+.1f} % in amplitude (each sensor against its own mean over those cycles) and {dphi:.3f} rad in phase,
and the amplitude follows the slow warming of the rod (the T5 mean rises from {f(float(per[2]['T5']['mean_C']))} to {f(float(per[5]['T5']['mean_C']))} °C between cycles 2 and 5). Fitting other sets of cycles with the same
code (`analyse_block`):

{nl.join(table(["Cycles fitted", "q (1/m)", "q′ (1/m)", "κ, finite rod (10⁻⁵ m²/s)", "κ, semi-infinite"], alt_rows))}

The three finite-rod κ agree within {100 * (max(kalts) / min(kalts) - 1):.1f} %. Per cycle (amplitude B of the fundamental, calibrated sensors):

{nl.join(table(["Cycle", "TEC mean (°C)", "T1 B (°C)", "T3 B (°C)", "T3 B against the mean of cycles 2 to 7 (%)", "T5 B (°C)", "T5 mean (°C)", "In the strict block"], cyc_rows))}

Model-validity checks: finite-length difference {100 * float(kap400['finite_length_max_rel_diff']):.2f} %, radial Biot number {float(kap400['Bi_radial']):.1e}; the mean-decay coefficient m from the
mean temperature profile ({f(float(kap400['m_mean_profile_1_m']))} ± {f(float(kap400['sm_mean_profile_1_m']))} 1/m) does not match √(q² − q′²) from the oscillation ({f(math.sqrt(p400['q'] ** 2 - p400['qp'] ** 2))} 1/m with the finite-rod q and q′,
{f(float(kap400['m_from_q_1_m']))} 1/m semi-infinite), as in the earlier runs, so ν and h should be quoted with caution. Figures: `{RUN17}_*.png` (settling test: `{RUN17}_settling.png`).

## All periods compiled

Every SAMMY analysis and Kapil's PI fits, one row per period and run (`compiled_periods.csv`, which also holds the nu, last-five and semi-infinite
columns). κ, q and q′ are the finite-rod fits. The strict test is the settling test above; the last-five column is Kapil's rule applied without a
settling test (for 10 Nov 480 s it includes the cycles disturbed by the TEC-sensor jump).

{nl.join(table(["Period (s)", "Source", "Settled cycles", "≥ 5", "q (1/m)", "q′ (1/m)", "κ, finite rod (10⁻⁵ m²/s)", "κ, semi-infinite", "κ, last five cycles (finite rod)"], comp))}

The windows with at least five settled cycles ({len(sam5)} SAMMY windows and {len(all5) - len(sam5)} of Kapil's) give a weighted mean κ = **{kw_a[0] * 1e5:.2f} ± {kw_a[1] * 1e5:.2f} × 10⁻⁵ m²/s**
(χ² {kw_a[2]:.1f} for {kw_a[3]} degrees of freedom) and ν = {nu_a[0] * 1e3:.2f} ± {nu_a[1] * 1e3:.2f} × 10⁻³ 1/s; the SAMMY windows alone give κ = {kw_s[0] * 1e5:.2f} ± {kw_s[1] * 1e5:.2f}.
With the handbook ρ and c that is k = {A.RHO * A.CP * kw_a[0]:.0f} W/(m K). All {len(rows)} fits lie between {k_all.min() * 1e5:.2f} and {k_all.max() * 1e5:.2f}; their mean is
{100 * (k_all.mean() / A.KAPPA_HANDBOOK - 1):.0f} % above the handbook value for 6061-T6 (6.9), as in each earlier run. {'In every row q is larger than q′, the signature of the side loss.' if q_gt else ''}

**Semi-infinite against finite rod.** The insulated tip reflects part of the wave. At 400 and 480 s the reflection reaches the far sensors nearly
opposite in phase and lowers their amplitude (the largest finite-length difference is {100 * p400['tip']:.1f} % at 400 s and {100 * r480b['tip']:.1f} % at 480 s), which a semi-infinite
fit reads as faster decay, so its κ is too low there. Finite-rod κ divided by semi-infinite κ for the SAMMY windows: {rat_txt}. The semi-infinite κ
falls from {ks_short * 1e5:.2f} at 100 to 300 s to {ks_long * 1e5:.2f} at 400 and 480 s; the finite-rod κ is {kf_short * 1e5:.2f} and {kf_long * 1e5:.2f}, so most of that fall is the model and the
periods agree within their errors. The lowest finite-rod window is the strict 400 s block ({pm(p400['kappa'], p400['skappa'], 1e5)}), with only {p400['settled']} settled cycles.

![kappa against period, all runs](../figures/module_08_sammy/compiled_kappa_vs_period.png)

![characteristic lengths against period, all runs](../figures/module_08_sammy/compiled_characteristic_length.png)

The 1/m points are the mean-profile fits of the SAMMY runs (room T from the idle sensors); they lie above the 1/m curve, the same mismatch between the
mean profile and the oscillation noted in the 17 Nov validity checks.

## Sensor T2

{nl.join(table(["Window", "Period (s)", "T2 amplitude against the fit (%)", "T2 phase against the fit (rad)", "κ without T2 against κ (%)", "χ², all five sensors → without T2"], t2_rows))}

In every SAMMY window the finite-rod fit through all five sensors leaves T2 above the line in amplitude ({min(r['dlnB2'] for r in own):+.1f} to {max(r['dlnB2'] for r in own):+.1f} %)
and ahead of it in phase ({min(r['dphi2'] for r in own):+.3f} to {max(r['dphi2'] for r in own):+.3f} rad), the direction Kapil found in his runs. It is the largest single misfit: the summed χ² falls from
{sum(r['chi2'] for r in own):.0f} ({sum(r['dof'] for r in own)} degrees of freedom) to {sum(r['chi2_noT2'] for r in own):.0f} ({sum(r['dof_noT2'] for r in own)}) when T2 is left out, and κ moves by {min(d2):+.1f} to {max(d2):+.1f} %. The numbers above keep T2, as
Kapil's fits do. The cause (seating, contact or calibration) is not known; the effect on κ is small and does not explain the κ excess over the handbook.

## The five production periods of the course page

Kapil's gap analysis of 16 November (commit `a1c84f5`) lists Stage 5 at 100, 200, 300, 400 and 500 s, at least five settled cycles each:

{nl.join(table(["Period", "Covered by", "κ, finite rod (10⁻⁵ m²/s)", "Status"], cover))}

Not covered by this page: the S18 evidence table, the course-simulator runs, the S18.5 and S18.6 open-loop trial (2 Nov, done the earlier way) and A5.

## Limits

- The 400 s run has one start-up cycle and then six cycles whose amplitudes differ by a few percent with the rod's slow warming; the strict test keeps two of them. The
  strict result, the last-five result and the all-cycles result are all given, and they agree within the stated errors.
- The finite-rod fit assumes an insulated tip and one side-loss rate along the rod. The tip correction grows with the period, so the 400 s and 480 s κ depend on that
  assumption more than the 100 to 240 s values do.
- The room temperature is a measured idle value ({T_ROOM[RUN17]:g} °C on 17 Nov, {T_ROOM[PH1]:g} °C on 16 Nov), used only for the mean-profile check, not for q, q′ or κ.
- The 16 Nov plan run lost its third phase when the GUI process ended; the 17 Nov file holds the complete 400 s dataset.
"""
    with open(OUT, "w") as fh:
        fh.write(text)
    print("wrote", os.path.relpath(OUT, REPO), len(text.splitlines()), "lines;", os.path.relpath(COMPILED, REPO), ";",
          os.path.relpath(FR.OUT, REPO), "; figures compiled_*.png")


if __name__ == "__main__":
    main()
