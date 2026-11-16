#!/usr/bin/env python3
"""
Phys 39 Module 8, Part I: write-up of the SAMMY PI re-run of 16 Nov 2026.  SAMMY copy.

    python3 python/sammy_module8_angstrom_analysis.py data/module_08_sammy/sammy_angstrom_live_20261116_090538.csv \
        --t-room 22.2 --summary none
    python3 python/sammy_module8_rerun_summary.py

Reads the run file, its _events.txt and _notes.csv, the tables in analysis_<stamp>/ and the 10 Nov tables, and writes
docs/sammy_module_08_guide/Sammy_Module_8_PI_Rerun_16Nov_Summary.md. Every number in the text comes from those files.
"""

import csv
import json
import math
import os
import re
import warnings
from datetime import datetime, timedelta

import numpy as np

from sammy_module8_angstrom_analysis import (KAPIL, KAPPA_HANDBOOK, MIN_CYCLES, OFFSETS, ROD, cycle_fits, find_steps,
                                             label, load, load_mask, load_offsets, prepare, settled_block)

warnings.filterwarnings("ignore", category=RuntimeWarning)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO, "data", "module_08_sammy")
GUIDE_DIR = os.path.join(REPO, "docs", "sammy_module_08_guide")
STAMP, NOV10, T_ROOM = "20261116_090538", "20261110_164057", 22.2
RUN = os.path.join(DATA_DIR, f"sammy_angstrom_live_{STAMP}.csv")
OUT = os.path.join(GUIDE_DIR, "Sammy_Module_8_PI_Rerun_16Nov_Summary.md")

# Phone photos of the live GUI, straightened and cropped to the GUI window:
# (file in docs/images, run time on screen in s, photo id, phone clock, remark)
PHOTOS = [("module08_sammy_gui_rerun_step2_t701s_IMG_2641.jpg", 700.6, "IMG_2641", "9:17 AM",
           "The right edge of the window is at the edge of the frame."),
          ("module08_sammy_gui_rerun_step2_t1228s_IMG_2642.jpg", 1228.0, "IMG_2642", "9:26 AM",
           "The step in the applied PWM near t = 1033 s in the lower plot is the settings re-send described below."),
          ("module08_sammy_gui_rerun_step3_t2060s_IMG_2643.jpg", 2059.8, "IMG_2643", "9:40 AM",
           "The left edge of the window is outside the frame."),
          ("module08_sammy_gui_rerun_step3_t2454s_IMG_2644.jpg", 2454.1, "IMG_2644", "9:46 AM", "")]


def table(name):
    with open(os.path.join(DATA_DIR, f"analysis_{STAMP}", name), newline="") as fh:
        return list(csv.DictReader(fh))


def nov10_kappa():
    with open(os.path.join(DATA_DIR, f"analysis_{NOV10}", "kappa_by_period.csv"), newline="") as fh:
        return {int(float(r["period_s"])): (float(r["kappa_m2_s"]), float(r["skappa_m2_s"]), int(r["settled_cycles"]))
                for r in csv.DictReader(fh)}


def read_events(path):
    out = []
    with open(path) as fh:
        for line in fh:
            wall, _, text = line.rstrip("\n").partition("\t")
            out.append((datetime.fromisoformat(wall), text))
    return out


def tms(text):
    return int(re.search(r"t_ms=(\d+)", text).group(1)) / 1000.0


def hhmmss(wall):
    return wall.strftime("%H:%M:%S")


def main():
    cols = load(RUN)
    t = cols["t"]
    with open(RUN.replace(".csv", "_notes.csv"), newline="") as fh:
        notes = list(csv.DictReader(fh))
    ev = read_events(RUN.replace(".csv", "_events.txt"))
    with open(os.path.join(DATA_DIR, f"analysis_{STAMP}", "run_summary.json")) as fh:
        rs = json.load(fh)

    start = next(e for e in ev if "SCHEDULE START" in e[1])
    t_start = tms(start[1])
    step_ev = {int(re.search(r"SCHEDULE STEP (\d)", e[1]).group(1)): e for e in ev if re.search(r"SCHEDULE STEP \d", e[1])}
    done = next(e for e in ev if "SCHEDULE DONE" in e[1])
    stop = next(e for e in ev if e[1].startswith("SENT STOP"))
    resend = next(e for e in ev if re.search(r"# EVENT t_ms=\d+ SET MODE", e[1]) and tms(e[1]) > t_start)
    sent = next(e for e in ev if e[1].startswith("SENT SET MODE") and e[0] > start[0])
    t_ev = tms(resend[1])
    wall_of = lambda ts: start[0] + timedelta(seconds=ts - t_start)
    tamb = [(w, float(re.search(r"SENT SET TAMB ([\d.]+)", x).group(1))) for w, x in ev if "SENT SET TAMB" in x]
    kp = float([re.search(r"SENT SET KP ([\d.]+)", x).group(1) for _, x in ev if "SENT SET KP" in x][-1])
    ki = float([re.search(r"SENT SET KI ([\d.]+)", x).group(1) for _, x in ev if "SENT SET KI" in x][-1])
    r_ratio = float([re.search(r"SENT SET R ([\d.]+)", x).group(1) for _, x in ev if "SENT SET R " in x][-1])

    # analysis pieces that the tables do not keep: the first rejected cycle of each period
    run_mask = load_mask(RUN.replace(".csv", "_mask.csv"))
    _, data, _ = prepare(cols, load_offsets(OFFSETS), run_mask)
    steps = find_steps(cols)
    block_info = {}
    for info in [s for s in steps if s["tb"] > 0]:
        block, _, _, fail = settled_block(cycle_fits(t, data, info), info["ncyc"])
        block_info[int(round(info["period"]))] = (block, fail, info)
    fail100 = block_info[100][1]["cycle"] + 1

    kappa = table("kappa_by_period.csv")
    track = table("tracking_by_period.csv")
    cyc = table("cycle_fits.csv")
    nov10 = nov10_kappa()
    sp = cols["setpoint_C"]
    tec = cols["TEC_C"]
    ctrl = cols["controller_pwm"]

    base = (t > 20) & (t < 150)
    base_mean = float(np.mean([cols[f"T{i}_C"][base] for i in range(1, 6)]))

    # the settings re-send
    i0 = int(np.searchsorted(t, t_ev)) - 1
    i_before = ctrl[i0] - kp * (sp[i0] - tec[i0])
    i5 = int(np.argmin(np.abs(t - (t_ev + 5.0))))
    m60 = (t >= t_ev) & (t < t_ev + 60)
    tec_min = float(np.nanmin(tec[m60]))
    sp_min = steps[1]["ta"] - steps[1]["tb"]
    gaps = [(float(t[i]), float(t[i + 1] - t[i])) for i in np.flatnonzero(np.diff(t) > 0.75)]
    gap_txt = ", ".join(f"{g:.1f}" for g, _ in gaps)
    lo, hi = (f"{f(d for _, d in gaps):.1f}" for f in (min, max))
    gap_len = lo if lo == hi else f"{lo} to {hi}"
    cyc_no = int((t_ev - tms(step_ev[2][1])) // 100) + 1
    bad_txt = f"{cyc_no} and {fail100}" if fail100 == cyc_no + 1 else f"{cyc_no} to {fail100}"

    # photos
    photo_md = []
    for fname, tt, pid, clock, remark in PHOTOS:
        k = int(np.argmin(np.abs(t - tt)))
        temps = ", ".join(f"T{i} {cols[f'T{i}_C'][k]:.2f}" for i in range(1, 6))
        box = [v for w, v in tamb if w <= wall_of(t[k])]
        box_txt = f"{box[-1]:.2f}" if box else "default"
        title = f"{pid}, {clock}: step {int(cols['step'][k])} ({cols['period_s'][k]:.0f} s period), t = {t[k]:.1f} s"
        cap = (f"setpoint {sp[k]:.2f} °C, TEC {tec[k]:.2f} °C, {temps} °C; applied PWM {int(cols['signed_pwm'][k]):+d} "
               f"(record {k + 1}); room T box {box_txt}. {remark}").strip()
        photo_md.append(f"![{title}](../images/{fname})\n\n*{title}. On screen: {cap}*")

    # tables
    rows = []
    for r in kappa:
        rows.append(f"| {float(r['period_s']):.0f} | {r['settled_cycles']} of {block_info[int(float(r['period_s']))][2]['ncyc']} | "
                    f"{float(r['q_1_m']):.2f} ± {float(r['sq_1_m']):.2f} | {float(r['qprime_1_m']):.2f} ± {float(r['sqprime_1_m']):.2f} | "
                    f"{float(r['kappa_m2_s']) * 1e5:.2f} ± {float(r['skappa_m2_s']) * 1e5:.2f} | "
                    f"{float(r['nu_1_s']) * 1e3:.2f} ± {float(r['snu_1_s']) * 1e3:.2f} | {float(r['k_W_mK']):.0f} |")
    blockrows = []
    for P, (block, fail, info) in block_info.items():
        why = ("none, all cycles settled" if fail is None else
               f"cycle {fail['cycle'] + 1}: {label(ROD[fail['sensor']])} off by {fail['dB']:+.1f} % and {fail['dphi']:+.2f} rad")
        blockrows.append(f"| {P} | cycles {block[0] + 1} to {block[-1] + 1} ({len(block)}) | "
                         f"{'yes' if len(block) >= MIN_CYCLES else 'no'} | {why} |")
    cyc100 = {}
    for r in cyc:
        if float(r["period_s"]) == 100 and r["channel"] in ("TEC", "T1"):
            cyc100.setdefault(int(r["cycle"]), {})[r["channel"]] = r
    cyc_rows = [f"| {k} | {float(v['TEC']['mean_C']):.2f} | {float(v['T1']['B_C']):.3f} | {float(v['T1']['phi_rad']):.3f} | "
                f"{'yes' if v['T1']['in_settled_block'] == '1' else 'no'} |" for k, v in sorted(cyc100.items())]
    trk = [f"| {float(r['period_s']):.0f} | {float(r['B_TEC_over_Tb']):.3f} | {float(r['TEC_lag_s']):.1f} | "
           f"{float(r['B_T1_over_Tb']):.3f} | {float(r['T1_lag_s']):.1f} | {r['pwm_min']} to {r['pwm_max']} | "
           f"{r['samples_at_pm255']} |" for r in track]
    chk = [f"| {float(r['period_s']):.0f} | {100 * float(r['finite_length_max_rel_diff']):.2f} % | {float(r['Bi_radial']):.1e} | "
           f"{float(r['m_from_q_1_m']):.2f} | {float(r['m_mean_profile_1_m']):.2f} ± {float(r['sm_mean_profile_1_m']):.2f} |"
           for r in kappa]

    k = np.array([float(r["kappa_m2_s"]) for r in kappa])
    s = np.array([float(r["skappa_m2_s"]) for r in kappa])
    w = 1 / s ** 2
    kw, skw = float(np.sum(w * k) / np.sum(w)), 1 / math.sqrt(float(np.sum(w)))
    chi2 = float(np.sum(((k - kw) / s) ** 2))
    cmp_rows, diffs = [], []
    for r in kappa:
        P = int(float(r["period_s"]))
        k0, s0 = float(r["kappa_m2_s"]), float(r["skappa_m2_s"])
        kn, sn, nn = nov10[P]
        kk, sk, *_ = KAPIL[P]
        diffs.append((P, (k0 - kn) / math.hypot(s0, sn), (k0 - kk) / math.hypot(s0, sk)))
        cmp_rows.append(f"| {P} | {k0 * 1e5:.2f} ± {s0 * 1e5:.2f} | {kn * 1e5:.2f} ± {sn * 1e5:.2f} ({nn} cycles) | "
                        f"{kk * 1e5:.2f} ± {sk * 1e5:.2f} |")
    diff_txt = "; ".join(f"{P} s: {a:+.1f} σ from the 10 Nov run and {b:+.1f} σ from Kapil" for P, a, b in diffs)
    last5 = " and ".join(f"{100 * (float(r['kappa_last5_m2_s']) / float(r['kappa_m2_s']) - 1):+.1f} % at {float(r['period_s']):.0f} s"
                         for r in kappa)
    ma, mb = max(abs(a) for _, a, _ in diffs), max(abs(b) for _, _, b in diffs)
    n100, n480 = (len(block_info[P][0]) for P in (100, 480))
    steps_min = rs["step_minutes"]
    hold = rs["hold"]
    note_base = next(n for n in notes if "baseline" in n["note"])
    photos_text = "\n\n".join(photo_md)
    chi_txt = ", ".join(f"{float(r['chi2_lnB']):.1f} (ln B) and {float(r['chi2_phi']):.1f} (phase) at {float(r['period_s']):.0f} s"
                        for r in kappa) + f", each for {int(kappa[0]['dof'])} degrees of freedom"
    masked_txt = "No sample was masked" if rs["masked_samples"] == 0 else f"{rs['masked_samples']} samples were masked"
    clip_txt = ("never reached ±255" if rs["pwm_clipped_samples"] == 0
                else f"reached ±255 in {rs['pwm_clipped_samples']} samples")

    text = f"""# Module 8, Part I: PI re-run of 16 November 2026 (SAMMY copy)

Summary of the {rs['minutes']:.0f}-minute run `{os.path.basename(RUN)}`, analysed with
`python/sammy_module8_angstrom_analysis.py data/module_08_sammy/{os.path.basename(RUN)} --t-room {T_ROOM:g}`.
Figures: `docs/figures/module_08_sammy/{STAMP}_*.png`. Photos: `docs/images/module08_sammy_gui_rerun_*.jpg`.
Tables and the text report: `data/module_08_sammy/analysis_{STAMP}/`.
Kapil Naidu's acquisition code, analysis scripts and data are unchanged; everything here is an addition.

## What was run

- PI control of the TEC thermistor (Kp {kp:g}, Ki {ki:g}, cooling multiplier r = {r_ratio:g}) with the sine setpoint
  40 ± 16 °C computed on the Arduino (`angstrom_tec_sammy`). Room T = {T_ROOM:g} °C: the note at
  {hhmmss(datetime.fromisoformat(note_base['wall_clock']))} ("{note_base['note']}") and the mean of T1 to T5 at
  t = 20 to 150 s ({base_mean:.2f} °C raw).
- Schedule: 5 min hold at 40 °C, then 12 cycles at 100 s and 8 cycles at 480 s ({sum(steps_min.values()):.1f} min). Started
  {hhmmss(start[0])}, 100 s step at {hhmmss(step_ev[2][0])}, 480 s step at {hhmmss(step_ev[3][0])}, `SCHEDULE DONE` at
  {hhmmss(done[0])}; the GUI was closed at {hhmmss(stop[0])}.
- The file has {rs['records']} records over {rs['minutes']:.1f} min, {rs['duplicated']} duplicated times and {rs['restarts']} restarts;
  {rs['gaps']} gaps longer than 0.75 s (at t = {gap_txt} s, each {gap_len} s long, when Send settings was pressed). {masked_txt}. The PWM
  {clip_txt} (range {rs['pwm_min']} to {rs['pwm_max']}), T1 peaked at {rs['t1_max_C']:.1f} °C and the TEC thermistor at {rs['tec_max_C']:.1f} °C (limits 56 and 65 °C).
- Rod: 6061-T6 aluminum, d = 12.757 mm, T1 to T5 at 0, 25.4, 50.8, 76.2 and 101.6 mm (±1 mm), tip 281.9 mm from T1.

## Photos of the run

Phone photos of the laptop screen during the run, straightened and cropped to the GUI window (metadata removed; the full-screen
originals are not in the repository). The numbers on screen are the logged values: the temperatures, the PWM and the stream's
valid-record count equal the CSV record with that number. The blue patches and dark shapes are reflections on the glass.

{photos_text}

## What disturbed the run

At {hhmmss(sent[0])} (t = {t_ev:.1f} s, cycle {cyc_no} of the 100 s step) Send settings was pressed during the schedule to correct
the room T box from {tamb[0][1]:.2f} to {tamb[-1][1]:g} °C (note at {hhmmss(datetime.fromisoformat(notes[-1]['wall_clock']))}). Two things follow from the sketch:

- Room T is used only in open-loop mode, so the PI control itself did not change.
- Every `SET MODE` zeroes the PI integral term (`handleSet` in `angstrom_tec_sammy.ino`). The integral term was about
  {i_before:+.0f} counts when it was zeroed; the controller output went from {ctrl[i0]:+.0f} to {ctrl[i5]:+.0f} counts within 5 s, and the TEC thermistor
  fell to {tec_min:.1f} °C in the next minute against a lowest setpoint of {sp_min:.1f} °C. The step is visible in photo IMG_2642.

The per-cycle fits show the effect from cycle {cyc_no} on. The settled block counts back from the last cycle and stops at the first cycle
that disagrees (cycle {fail100}), so it starts at cycle {block_info[100][0][0] + 1}:

| 100 s cycle | TEC mean (°C) | T1 amplitude (°C) | T1 phase (rad) | In the settled block |
|---|---|---|---|---|
{chr(10).join(cyc_rows)}

## Settling test

Counting back from the last cycle, a cycle joins the settled block while every rod sensor stays within 3 % in amplitude and
0.05 rad in phase of the block median (tolerances chosen for this analysis). The page asks for at least five settled cycles at each
of at least two usable periods.

| Period (s) | Settled block | Five or more | First rejected cycle |
|---|---|---|---|
{chr(10).join(blockrows)}

## Results

| Period (s) | Settled cycles | q (1/m) | q′ (1/m) | κ (10⁻⁵ m²/s) | ν (10⁻³ 1/s) | k (W/(m K)) |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

- Both periods, weighted mean: **{kw * 1e5:.2f} ± {skw * 1e5:.2f} × 10⁻⁵ m²/s** (χ² = {chi2:.1f} for {len(k) - 1} degree of freedom);
  plain mean {k.mean() * 1e5:.2f}, spread (sd) {k.std(ddof=1) * 1e5:.2f}.
- Handbook 6061-T6 (k = 167 W/(m K), ρ = 2700 kg/m³, cp = 896 J/(kg K)): κ = 6.9 × 10⁻⁵ m²/s, so the weighted mean is
  {100 * (kw / KAPPA_HANDBOOK - 1):.0f} % above it, as in the earlier runs. ν is a small difference of two nearly equal numbers, so its relative uncertainty is large.
- Using the last five cycles instead of the settled block changes κ by {last5}.

Against the earlier PI runs of the same rod (κ in 10⁻⁵ m²/s):

| Period (s) | This run | 10 Nov (SAMMY, `analysis_{NOV10}`) | Kapil (2 and 4 Nov) |
|---|---|---|---|
{chr(10).join(cmp_rows)}

Differences of this run: {diff_txt}.

## Controller tracking (PI)

Hold step: the TEC reached 39.5 °C after {hold['t_reach']:.0f} s with {hold['overshoot']:+.2f} °C overshoot, peak PWM {hold['pwm_max']}.

| Period (s) | B_TEC/Tb | TEC lag (s) | B_T1/Tb | T1 lag (s) | PWM range | Samples at ±255 |
|---|---|---|---|---|---|---|
{chr(10).join(trk)}

## Model-validity checks

| Period (s) | Finite-length difference (max) | Radial Biot number | m from √(q²−q′²) (1/m) | m from the mean profile (1/m) |
|---|---|---|---|---|
{chr(10).join(chk)}

The finite-length difference is the largest at T5 for the longest period, and the radial Biot number is far below 0.1. The side-loss rate
from the mean temperature profile does not match the one from q and q′, so ν and h should be quoted with caution.

## Where this run fits

Kapil's gap analysis of 16 November (`docs/module_notes/module_08_gap_analysis.md`, commit `a1c84f5`) lists PI at 200 s, PI at 400 s
and the positive-only PWM run as what the rewritten course page still needs from the bench. This file covers none of them. It adds a
second 100 s dataset ({n100} settled cycles) and a third 480 s dataset ({n480} settled cycles), both above the five-cycle minimum, and
their κ is within {ma:.1f} σ of the 10 Nov run and within {mb:.1f} σ of Kapil's PI fits (table above).

## Limits of this run

- Only PI mode and only the periods 100 s and 480 s.
- Cycles {bad_txt} of the 100 s step were disturbed by the settings re-send; the 100 s fit uses cycles {block_info[100][0][0] + 1} to {block_info[100][0][-1] + 1}.
  The spatial lines have χ² of {chi_txt}; the quoted errors are scaled up by √(χ²/dof) where that is above 1.
- The room T box held {tamb[0][1]:.2f} °C until {hhmmss(sent[0])} and {tamb[-1][1]:g} °C afterwards. This does not matter in PI mode; the
  fits use {T_ROOM:g} °C.
- The tolerances of the settling test were chosen for this analysis, and the semi-infinite-rod formulas carry a finite-length bias
  (table above).

## Reproduce

```bash
python3 python/sammy_module8_angstrom_analysis.py data/module_08_sammy/{os.path.basename(RUN)} --t-room {T_ROOM:g} --summary none
python3 python/sammy_module8_rerun_summary.py
```

## AI assistance

The analysis script changes, the photo crops, the figures and this summary were produced with GitHub Copilot assistance and
reviewed against Kapil Naidu's `angstrom_fit.py` method and the Module 8 study guide.
"""
    with open(OUT, "w") as fh:
        fh.write(text)
    print("wrote", os.path.relpath(OUT, REPO))


if __name__ == "__main__":
    main()
