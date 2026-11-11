#!/usr/bin/env python3
"""
Phys 39 Module 8, S18.4: positive-only sinusoidal PWM (U0 = U).  SAMMY copy.

    python3 python/sammy_module8_s184_page.py [--target 40] [--u 36]

Writes the S18.4 page, prepared before the run (no S18.4 data exist yet), from
  - the S18.3 run (Module 6 one-lump model fitted by sammy_module8_s183_analysis),
  - the PI hold at 40 C of the 10 November production run (steady PWM that held the plate),
and two figures:
    docs/sammy_module_08_guide/Sammy_Module_8_S18_4_Positive_Only_PWM_Walkthrough.md
    docs/figures/module_08_sammy/s184_predicted_run.png, s184_predicted_shapes.png
"""

import argparse
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sammy_module8_s183_analysis as S  # noqa: E402  (fit of the S18.3 run, one-lump helpers)
from sammy_module8_s183_doc import f, pct, table  # noqa: E402

an = S.an
S183_RUN = os.path.join(an.DATA_DIR, "sammy_angstrom_live_20261111_122227.csv")
HOLD_RUN = os.path.join(an.DATA_DIR, "sammy_angstrom_live_20261110_164057.csv")
PAGE = os.path.join(an.GUIDE_DIR, "Sammy_Module_8_S18_4_Positive_Only_PWM_Walkthrough.md")
FIG = "../figures/module_08_sammy/"
SCHEDULE = ((600.0, 100.0), (800.0, 200.0), (1500.0, 500.0))     # (duration s, period s): 6, 4 and 3 whole cycles
TEC_LATCH, T1_LATCH = 65.0, 56.0
START_UP_TOL = 0.2                                                # C: a cycle counts as settled below this start-up error


# ---------------------------------------------------------------------------
# the numbers
# ---------------------------------------------------------------------------

def hold_calibration(path):
    """Steady PWM that held the TEC at its setpoint during the 5 minute PI hold of the 10 November run."""
    c = an.load(path)
    t, rs, st = c["t"], c["run_state"], c["step"].astype(int)
    m1 = (rs == 2) & (st == 1)
    t0, t1 = float(t[m1][0]), float(t[m1][-1])
    last = m1 & (t >= t1 - 100.0)
    late = (rs == 0) & (t >= t0 - 170.0) & (t < t0 - 5.0)
    early = (rs == 0) & (t >= 200.0) & (t < 400.0)
    h = dict(u=float(c["signed_pwm"][last].mean()), u_sd=float(c["signed_pwm"][last].std()), T=float(c["TEC_C"][last].mean()),
             setpoint=float(np.nanmean(c["setpoint_C"][last])), slope=float(np.polyfit(t[last], c["TEC_C"][last], 1)[0] * 60.0),
             T_idle=float(c["TEC_C"][late].mean()), T_idle_early=float(c["TEC_C"][early].mean()), t0=t0, t1=t1)
    h["chi"] = (h["T"] - h["T_idle"]) / h["u"]
    h["chi_early"] = (h["T"] - h["T_idle_early"]) / h["u"]
    return h


def settled(P, U, chi, tau):
    w = 2 * math.pi / P
    N = 1.0 / math.sqrt(1 + (w * tau) ** 2)
    phi = math.atan(w * tau)
    return dict(P=P, w=w, wt=w * tau, N=N, phi=phi, dt=phi / w, R=chi * U * N)


def theta_full(t, chi, U, P, tau):
    """Complete response of tau dtheta/dt + theta = chi U (1 + sin wt) from theta(0) = 0."""
    e = settled(P, U, chi, tau)
    return chi * U * (1 + e["N"] * np.sin(e["w"] * t - e["phi"]) - (1 - e["N"] * math.sin(e["phi"])) * np.exp(-t / tau))


def rk4_check(chi, U, tau, periods):
    worst = 0.0
    for P in periods:
        w = 2 * math.pi / P
        dt = 0.05
        n = int(round(max(4 * P, 600.0) / dt))
        t = np.arange(n + 1) * dt
        th = np.zeros(n + 1)
        g = lambda tt, x: (-x + chi * U * (1 + math.sin(w * tt))) / tau
        for i in range(n):
            k1 = g(t[i], th[i])
            k2 = g(t[i] + dt / 2, th[i] + dt * k1 / 2)
            k3 = g(t[i] + dt / 2, th[i] + dt * k2 / 2)
            k4 = g(t[i] + dt, th[i] + dt * k3)
            th[i + 1] = th[i] + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        worst = max(worst, float(np.max(np.abs(th - theta_full(t, chi, U, P, tau)))))
    return worst


def planned_run(m, T_amb, U, dt=0.5):
    """The planned schedule at the board's 0.5 s record rate, integer PWM, model response from the idle baseline."""
    total = sum(d for d, _ in SCHEDULE)
    t = np.arange(0.0, total, dt)
    u = np.zeros_like(t)
    bounds, a = [], 0.0
    for dur, P in SCHEDULE:
        sel = (t >= a) & (t < a + dur)
        u[sel] = np.round(U + U * np.sin(2 * math.pi * (t[sel] - a) / P))
        bounds.append((a, a + dur, P))
        a += dur
    T = S.simulate_u(t, u, m["chi_h"], m["chi_c"], m["tau"], T_amb, T_amb)
    return t, u, T, bounds


def start_up(t, T, bounds, m, T_amb, U):
    """Per step: the start-up error at the start of every cycle (model against its own settled sinusoid) and the cycles to skip."""
    out = []
    for a, b, P in bounds:
        e = settled(P, U, m["chi_h"], m["tau"])
        n = int(round((b - a) / P))
        errs = []
        for k in range(n):
            tk = a + k * P
            i = int(np.argmin(np.abs(t - tk)))
            ss = m["chi_h"] * U * (1 + e["N"] * math.sin(e["w"] * (tk - a) - e["phi"]))
            errs.append(abs(T[i] - T_amb - ss))
        skip = next((k for k, v in enumerate(errs) if v < START_UP_TOL), n)
        out.append(dict(P=P, n=n, errs=errs, skip=skip))
    return out


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------

def fig_run(path, t, u, T, bounds, ups, m, T_amb, U, target):
    fig, axs = plt.subplots(2, 1, figsize=(12, 6.6), sharex=True, gridspec_kw={"height_ratios": [2.6, 1]})
    fills = ("#dbe9f6", "#dff1df", "#fbe8d3")
    for (a, b, P), fill, up in zip(bounds, fills, ups):
        for ax in axs:
            ax.axvspan(a, b, color=fill, lw=0)
            ax.axvspan(a, a + up["skip"] * P, facecolor="none", edgecolor="#999", hatch="//", lw=0)
        axs[0].text(0.5 * (a + b), 1.01, f"{P:g} s period", transform=axs[0].get_xaxis_transform(), ha="center", fontsize=10)
    axs[0].plot(t, T, color="black", lw=1.5, label="predicted TEC temperature (one-lump model, S18.3 fit)")
    axs[0].axhline(target, color="#2a9d8f", ls="--", lw=1.2, label=f"target mean T* = {target:g} °C")
    axs[0].axhline(T_amb + m["chi_h"] * U, color="#C0392B", ls=":", lw=1.2, label=f"predicted mean {T_amb + m['chi_h'] * U:.1f} °C")
    axs[0].axhline(T_amb, color="#888", ls=":", lw=1, label=f"idle baseline {T_amb:.2f} °C")
    axs[0].axhline(TEC_LATCH, color="#C0392B", lw=1.2)
    axs[0].text(5, TEC_LATCH - 2.6, f"TEC latch {TEC_LATCH:g} °C", color="#C0392B", fontsize=9)
    axs[0].set_ylabel("TEC temperature (°C)")
    axs[0].set_ylim(T_amb - 6, TEC_LATCH + 4)
    axs[0].legend(loc="lower right", fontsize=8, ncol=2)
    axs[1].plot(t, u, color="#202020", lw=0.9)
    axs[1].set_ylabel("applied PWM (counts)")
    axs[1].set_xlabel("time since START schedule (s)")
    axs[0].set_title(f"Planned S18.4 run, U0 = U = {U:g} counts (hatched: start-up cycles to skip)", fontsize=11, pad=18)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def fig_shapes(path, A):
    R = A["results"]
    fig, axs = plt.subplots(1, len(R), figsize=(4.6 * len(R), 4.4), sharey=True)
    x = np.linspace(0, 2 * math.pi, 400)
    for ax, r in zip(axs, R):
        ph = (r["w"] * (r["tt"] - r["a"]) - r["lag"]) % (2 * math.pi)
        ax.plot(ph, (r["T"] - r["mean"]) / r["A1"], ".", color="#bbb", ms=2.5, label="S18.3 measured, settled cycles")
        o = np.argsort(ph)
        ax.plot(ph[o], (r["fit"] - r["mean"])[o] / r["A1"], color="black", lw=1.2, label="S18.3, mean + 3 harmonics")
        ax.plot(x, np.sin(x), color="#1F77B4", ls="--", lw=1.6, label="S18.4 prediction (a pure sinusoid)")
        ax.axhline(0, color="#888", lw=0.8)
        ax.set_title(f"{r['period']:g} s period", fontsize=11)
        ax.set_xlabel("phase of the temperature swing (rad)")
        ax.set_xlim(0, 2 * math.pi)
    axs[0].set_ylabel("(T − mean) / A1")
    h, lab = axs[0].get_legend_handles_labels()
    fig.legend(h, lab, loc="lower center", ncol=3, fontsize=9, frameon=False)
    fig.suptitle("Shape of one cycle, each normalised by its own amplitude and shifted by its own lag: lopsided in S18.3, symmetric in the S18.4 prediction", fontsize=10, y=0.995)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, dpi=200)
    plt.close(fig)


# ---------------------------------------------------------------------------
# the page
# ---------------------------------------------------------------------------

def build(A, hold, target, U_override):
    R, m, M4 = A["results"], A["model"], A["m4"]
    T_amb, tau, chi = A["T_amb"], m["tau"], m["chi_h"]
    rise = target - T_amb
    U_fit, U_m4 = rise / chi, rise / M4["chi_h"]
    U_hold = rise / hold["chi"]
    U_work = float(U_override) if U_override else float(round(0.5 * (U_fit + U_hold)))
    mean_rise = chi * U_work
    mean_T = T_amb + mean_rise
    mean_T_hold = T_amb + hold["chi"] * U_work
    pred = [settled(r["period"], U_work, chi, tau) for r in R]
    ratio_amp = [r["rod"]["T1_C"]["A1"] / r["A1"] for r in R]
    ratio_mean = max((r["rod"]["T1_C"]["mean"] - A["base"]["T1_C"]) / (r["mean"] - A["base"]["TEC_C"]) for r in R)
    t1_hi = [A["base"]["T1_C"] + ratio_mean * mean_rise + ra * e["R"] for ra, e in zip(ratio_amp, pred)]
    P_fit = [S.fourier_prediction(r["period"], A["U"], m["chi_h"], m["chi_c"], tau) for r in R]
    dev_amp = [r["A1"] / p["A1"] - 1 for r, p in zip(R, P_fit)]
    dev_lag = [r["lag"] - p["lag"] for r, p in zip(R, P_fit)]
    t, u, T, bounds = planned_run(m, T_amb, U_work)
    ups = start_up(t, T, bounds, m, T_amb, U_work)
    worst = rk4_check(chi, U_work, tau, [r["period"] for r in R])
    total = sum(d for d, _ in SCHEDULE)
    stamp = A["stamp"]
    pers = ", ".join(f"{r['period']:g}" for r in R[:-1]) + f" and {R[-1]['period']:g} s"
    sched_lines = [f"{d:g} 40 0 {P:g}" for d, P in SCHEDULE]
    run183 = os.path.basename(A["path"])
    r1, r2, r3 = R
    e1, e2, e3 = pred
    tmax_hi = T_amb + mean_rise + e3["R"]
    c0 = [chi * U_work * (1 - e["N"] * math.sin(e["phi"])) for e in pred]

    L = []
    add = L.append
    ext = L.extend

    add("# Module 8, S18.4: positive-only sinusoidal PWM, step by step (SAMMY copy)")
    add("")
    add("A page prepared before the S18.4 run. **No S18.4 data have been recorded yet**, so every number below is a prediction. It is made from the S18.3 run")
    add(f"`{run183}` (the Module 6 one-lump model fitted to it) and from the PI hold of 10 November (`{os.path.basename(HOLD_RUN)}`). Once the S18.4 file exists,")
    add("these predictions are what it is compared with. Companion page: [Sammy_Module_8_S18_3_Raw_PWM_Walkthrough.md](Sammy_Module_8_S18_3_Raw_PWM_Walkthrough.md).")
    add("Figures: `docs/figures/module_08_sammy/s184_*.png`. Kapil Naidu's acquisition code, analysis scripts and data are unchanged; everything here is an addition.")
    add("")
    add(f"The mean TEC temperature that the page asks for disappeared from the pasted assignment text. This page works with T* = {target:g} °C, the mean of the sketch's default")
    add("setpoint (Ta = 40 °C); section 4 gives the formula and a table for other targets.")
    add("")

    # ---------------------------------------------------------------- 0
    add("## 0. The question, and the short answer")
    add("")
    add("S18.3 swung the PWM around zero, u = U sin(ωt), so the current reversed twice per cycle. S18.4 swings it around U0 = U instead:")
    add("")
    add("```text")
    add("u(t) = U0 + U sin(ωt) = U (1 + sin ωt)         0 ≤ u ≤ 2U, never negative")
    add("```")
    add("")
    add("The TEC now only heats. The page asks to adjust U until the mean TEC temperature is about T*, to keep the swing safe, and to compare with S18.3, so as to decide")
    add("which of the S18.3 asymmetries come from reversing the TEC current and which are still there when the current keeps one direction.")
    add("")
    add(f"**Predictions for U0 = U = {U_work:.0f} counts** (u from 0 to {2 * U_work:.0f}), room temperature {f(T_amb, 2)} °C:")
    add("")
    ext(table(["Period", "Shrink factor N", "Amplitude A1 (°C)", "Lag behind the PWM", "Highest TEC (°C)", "Lowest TEC (°C)", "Highest T1 (°C, estimate)"],
              [[f"{e['P']:g} s", f(e["N"], 3), f(e["R"], 2), f"{f(e['phi'], 3)} rad = {f(e['dt'], 1)} s", f(mean_T + e["R"], 1), f(mean_T - e["R"], 1), f(x, 1)]
               for e, x in zip(pred, t1_hi)]))
    add("")
    add(f"1. **The mean is set by χh and U, not by an asymmetry.** It is T_amb + χh U = {f(mean_T, 1)} °C with the S18.3 fit (χh = {f(chi, 3)} °C/count), at every period.")
    add(f"   The 10 November PI hold gives {f(mean_T_hold, 1)} °C for the same U. Both are within {f(math.ceil(10 * max(abs(mean_T - target), abs(mean_T_hold - target))) / 10, 1)} °C of the target.")
    add(f"2. **The amplitude is χh U N,** {f(e1['R'], 1)}, {f(e2['R'], 1)} and {f(e3['R'], 1)} °C, and **the lag is the same arctan(ωτ) as in S18.3.** The amplitude grows with the period for the same")
    add("   reason as before (the plate is a low-pass filter).")
    add("3. **The waveform should be a clean sinusoid.** In the model, the second harmonic, the unequal peaks and the unequal slopes of S18.3 come from using two different")
    add("   susceptibilities (χh for u > 0, χc for u < 0). With one sign of u there is one susceptibility and they vanish. The S18.4 run tests this.")
    add(f"4. **It is safe by a wide margin.** The highest TEC temperature is about {f(tmax_hi, 0)} °C at the 500 s period (latch {TEC_LATCH:g} °C); T1 stays near {f(t1_hi[2], 0)} °C (latch {T1_LATCH:g} °C).")
    add(f"5. **Run 600, 800 and 1500 s** ({total / 60:.1f} min): the first step needs 3 start-up cycles because the plate has to climb {f(mean_rise, 0)} °C to the mean (section 5).")
    add("")

    # ---------------------------------------------------------------- 1
    add("## 1. Words and symbols")
    add("")
    add("The symbols u, U, P, ω, T, T_amb, θ = T − T_amb, χh, τ, N, φ and A1 to A3 are explained in the S18.3 page. The new ones:")
    add("")
    ext(table(["Symbol", "In plain words"], [
        ["U0", "the offset: the level the knob swings around. Here U0 = U, so the knob swings between 0 and 2U and never goes below zero"],
        ["T*", f"the mean TEC temperature we want (here {target:g} °C)"],
        ["mean rise", "χh U0: how much hotter than the room the plate sits on average"],
        ["N = cos φ", "the shrink factor 1/√(1 + (ωτ)²). It equals cos φ, because φ = arctan(ωτ), so a measured lag gives N directly"],
    ]))
    add("")
    add("The bathtub of the S18.3 page again. In S18.3 the tap swung from hot to cold, and the hot tap was stronger. Now only the hot tap is used: it swings between")
    add("\"off\" and \"full\", so the water level moves up and down around a high average level. The tub is always being warmed; only the amount changes.")
    add("")

    # ---------------------------------------------------------------- 2
    add("## 2. The series of steps for the run")
    add("")
    add("Everything needed is already in the sketch (`SET U`, `SET U0`, mode RAW) and in the GUI (the \"RAW mode\" box and the schedule box). The \"One long run\" button runs S18.3 only")
    add("(U0 = 0); it is not used here.")
    add("")
    add("1. **Baseline.** Start the GUI (`python3 python/sammy_module8_angstrom_gui.py`) and leave the rig untouched for 2 minutes with nothing started (u = 0). Read the mean of")
    add("   T1 to T5 and type it into the note box with the real number, for example `room T baseline 24.3 C (mean of T1-T5, hands off)`.")
    add(f"2. **Settings.** Set mode to RAW. In the RAW mode box set U = {U_work:.0f} and U0 = {U_work:.0f}. Click Send settings, then GET, and check that the `# SETTINGS` line shows")
    add(f"   `mode=RAW`, `U={U_work:.1f}` and `U0={U_work:.1f}`.")
    add(f"3. **Schedule.** Type these lines in the schedule box (Ta and Tb are ignored in RAW but must be typed). The label under the box should say 3 steps, {total / 60:.1f} min.")
    add("   Click Send schedule and check the listed steps.")
    add("")
    add("```text")
    for ln in sched_lines:
        add(ln)
    add("```")
    add("")
    add(f"4. **Start.** Type the note `S18.4 start, U0 = U = {U_work:.0f}` and click START schedule. The applied PWM plot should swing between 0 and {2 * U_work:.0f} counts and never go below 0.")
    add(f"5. **Watch the first step.** The TEC should climb to about {f(mean_T, 1)} °C within three or four cycles and then swing between about {f(mean_T - e1['R'], 0)} and {f(mean_T + e1['R'], 0)} °C.")
    add(f"   If the mean of the last three cycles is more than about 2 °C from {target:g} °C, the new value is U = U_old × (T* − T_amb) / (T_mean − T_amb). The run can be finished anyway, because")
    add("   the data are still good for the comparison (section 7), and repeated with the new U if the target mean is required.")
    add(f"6. **Safety.** Press STOP if the TEC passes {TEC_LATCH - 9:g} °C or T1 passes {T1_LATCH - 6:g} °C; the board latches at {TEC_LATCH:g} and {T1_LATCH:g} °C and sets the output to 0 on its own.")
    add("7. **End.** After the last step the output goes to 0 (`SCHEDULE DONE`). Type the note `S18.4 finished`, close the GUI, and check the file with Check a saved file.")
    add("")

    # ---------------------------------------------------------------- 3
    add("## 3. The math, one step at a time")
    add("")
    add("### 3.1 The push now has one sign")
    add("")
    add("```text")
    add("u(t) = U (1 + sin ωt),   0 ≤ u ≤ 2U,   so χ(u) = χh at every moment")
    add("τ · dθ/dt + θ = χh U (1 + sin ωt)                               (S18.4.1)")
    add("```")
    add("")
    add("Compare with S18.3: the push gained a constant, and the two susceptibilities χh and χc have become one, χh. The equation is linear again, with no |sin| and no case split.")
    add("")
    add("### 3.2 Split the push in two")
    add("")
    add("The push is χh U (a constant) plus χh U sin ωt (a swing). The equation is linear, so the plate's answer to a sum of pushes is the sum of its answers to each push alone.")
    add("")
    add("### 3.3 The constant push")
    add("")
    add("Try a constant θc. Then dθc/dt = 0 and the equation says θc = χh U. In words: hold the knob at U forever and the plate ends up χh U hotter than the room.")
    add("")
    add("### 3.4 The swinging push (the S18.3 steps, with χ = χh)")
    add("")
    add("```text")
    add("guess      θs = a sin ωt + b cos ωt                       dθs/dt = a ω cos ωt − b ω sin ωt")
    add("put in     (a − ωτ b) sin ωt + (ωτ a + b) cos ωt = χh U sin ωt")
    add("match      sine: a − ωτ b = χh U        cosine: ωτ a + b = 0")
    add("solve      b = −ωτ a,   a = χh U / (1 + (ωτ)²)")
    add("one sine   θs = R sin(ωt − φ),   R = √(a² + b²) = χh U / √(1 + (ωτ)²) = χh U N,   tan φ = ωτ")
    add("```")
    add("")
    add("### 3.5 The start-up piece, and the whole answer")
    add("")
    add("A pure leak dies away as e^(−t/τ), and adding C e^(−t/τ) to a solution does not break the equation. So θ(t) = χh U + R sin(ωt − φ) + C e^(−t/τ). The plate starts at the idle")
    add("baseline, θ(0) = 0:")
    add("")
    add("```text")
    add("0 = χh U + R sin(−φ) + C   →   C = −χh U (1 − N sin φ)")
    add("θ(t) = χh U · [ 1 + N sin(ωt − φ) − (1 − N sin φ) e^(−t/τ) ]")
    add("```")
    add("")
    add("### 3.6 Check the answer")
    add("")
    add("```text")
    add("constant piece:   τ · 0 + χh U = χh U                                      satisfies the equation")
    add("swinging piece:   verified in the S18.3 page (section 4.4)")
    add("start-up piece:   τ d/dt(C e^(−t/τ)) + C e^(−t/τ) = −C e^(−t/τ) + C e^(−t/τ) = 0")
    add("start:            θ(0) = χh U (1 − N sin φ) − χh U (1 − N sin φ) = 0")
    add("```")
    add("")
    add(f"The equation was also integrated numerically (fourth-order Runge-Kutta, 0.05 s steps) from θ = 0 for the three periods with U = {U_work:.0f} and compared with the formula at every step;")
    add(f"the largest difference is {worst:.1e} °C, which is rounding error.")
    add("")
    add("### 3.7 Read the settled solution")
    add("")
    add("```text")
    add("mean            T_amb + χh U                  the constant piece, the same at every period")
    add("amplitude       R = χh U N = (χh U) cos φ     a fraction N of the mean rise")
    add("lag             φ = arctan(ωτ), delay φ/ω     the same as in S18.3: it comes from τ, not from χ")
    add("highest/lowest  T_amb + χh U (1 ± N)          symmetric about the mean")
    add("shape           a pure sinusoid in this model")
    add("```")
    add("")
    add("A slow swing (N near 1) runs from almost the room temperature to almost twice the mean rise; a quick swing (N small) hardly leaves the mean. At 500 s,")
    add(f"N = {f(e3['N'], 2)}, so the plate is predicted to swing {f(mean_T - e3['R'], 0)} to {f(mean_T + e3['R'], 0)} °C around a mean of {f(mean_T, 1)} °C. This is why \"a safe amplitude\" matters here: with U0 = U the swing is tied to the mean.")
    add("")

    # ---------------------------------------------------------------- 4
    add("## 4. Choosing U")
    add("")
    add("The mean is T_amb + χh U0 whatever the period, so with U0 = U:")
    add("")
    add("```text")
    add("U = (T* − T_amb) / χh")
    add("```")
    add("")
    add(f"Three estimates of the PWM that holds a mean of {target:g} °C when the room is at {f(T_amb, 2)} °C:")
    add("")
    ext(table(["Source", "What it says", "PWM (counts)"], [
        ["Module 4 steady-state curve (the GUI default)", f"χh = {M4['chi_h']:g} °C/count", f(U_m4, 1)],
        ["S18.3 fit (this rig, rod attached)", f"χh = {f(chi, 4)} °C/count", f(U_fit, 1)],
        ["10 November PI hold", f"the controller held the TEC at {f(hold['T'], 2)} °C with {f(hold['u'], 1)} counts on average (sd {f(hold['u_sd'], 1)}; last 100 s of the 5 minute hold, "
                                f"drift {f(hold['slope'], 3)} °C/min) when the TEC idled at {f(hold['T_idle'], 2)} °C, so χh = {f(hold['chi'], 3)} °C/count", f(U_hold, 1)],
    ]))
    add("")
    add(f"The Module 4 curve asks for fewer counts because it overestimates this rig's χh. The other two agree within {pct(abs(U_fit - U_hold) / U_fit, 0)}. **Start with U0 = U = {U_work:.0f}.**")
    add(f"An error of 10 % in χh moves the mean by {f(0.1 * mean_rise, 1)} °C. The room temperature moves it one for one: on 10 November the idle TEC reading drifted by {f(hold['T_idle_early'] - hold['T_idle'], 1)} °C in three minutes.")
    add("")
    add("For another target mean the same recipe gives (U is the mean of the S18.3-fit and the PI-hold estimates, rounded):")
    add("")
    rows = []
    for tg in (30.0, 35.0, 40.0, 45.0, 50.0):
        Ut = round(0.5 * ((tg - T_amb) / chi + (tg - T_amb) / hold["chi"]))
        hi = T_amb + chi * Ut + settled(R[2]["period"], Ut, chi, tau)["R"]
        flag = "above the TEC latch" if hi > TEC_LATCH else ("above 56 °C, not advised" if hi > T1_LATCH else "ok")
        rows.append([f"{tg:g}", f"{Ut:.0f}", f(settled(R[0]["period"], Ut, chi, tau)["R"], 1), f(settled(R[1]["period"], Ut, chi, tau)["R"], 1),
                     f(settled(R[2]["period"], Ut, chi, tau)["R"], 1), f(hi, 0), flag])
    ext(table(["T* (°C)", "U = U0 (counts)", "A1 at 100 s (°C)", "A1 at 200 s (°C)", "A1 at 500 s (°C)", "Highest TEC at 500 s (°C)", "Safety"], rows))
    add("")

    # ---------------------------------------------------------------- 5
    add("## 5. What to expect")
    add("")
    add(f"![planned run]({FIG}s184_predicted_run.png)")
    add("")
    add("*The model response to the planned schedule. Hatched: the start-up cycles that are skipped. Green dashed: the target mean. Red solid: the TEC latch.*")
    add("")
    add(f"**Start-up.** The plate starts at the room temperature, so the first step has to climb {f(mean_rise, 0)} °C to the mean. The leftover of that climb at the start of a cycle is")
    add(f"C e^(−t/τ) with |C| = {f(c0[0], 1)} °C at the first step. Counting a cycle as settled once the model's start-up error is below {START_UP_TOL:g} °C gives:")
    add("")
    ext(table(["Step", "Cycles", "Start-up error at the start of cycle 1, 2, 3, 4 (°C)", "Cycles to skip", "Settled cycles"],
              [[f"{k}: {up['P']:g} s", up["n"], ", ".join(f(v, 2) for v in up["errs"][:4]), up["skip"], up["n"] - up["skip"]] for k, up in enumerate(ups, 1)]))
    add("")
    add(f"The later steps start from the state the previous step left, which is already close to the new settled cycle. This plan gives {ups[0]['n'] - ups[0]['skip']}, {ups[1]['n'] - ups[1]['skip']} and {ups[2]['n'] - ups[2]['skip']} settled cycles (S18.3 had 3, 3 and 2).")
    add("")
    add("**Safety.** The highest values in the table of section 0 are the model's; the T1 estimate scales the S18.3 rod response (T1 amplitude over TEC amplitude "
        f"{f(ratio_amp[0], 2)}, {f(ratio_amp[1], 2)}, {f(ratio_amp[2], 2)}; mean rise of T1 over mean rise of the TEC up to {f(ratio_mean, 2)}) and is good to a degree or two.")
    add("")

    # ---------------------------------------------------------------- 6
    add("## 6. S18.3 against S18.4")
    add("")
    ext(table(["", f"S18.3 (U0 = 0, U = {A['U']:.0f})", "S18.4 (U0 = U)"], [
        ["PWM range", "−50 to +50 counts", f"0 to {2 * U_work:.0f} counts"],
        ["susceptibility that acts", "χh when u > 0, χc when u < 0", "χh all the time"],
        ["mean above the room", "(χh − χc) U / π, from the asymmetry", "χh U0, the plain heating"],
        ["amplitude of the swing", "χavg U N, with χavg = (χh + χc) / 2", "χh U N"],
        ["lag", "arctan(ωτ)", "arctan(ωτ)"],
        ["second harmonic", "(4 Δχ U / 3π) N2, Δχ = (χh − χc) / 2", "0"],
        ["peaks above / dips below the mean", "more than 1", "1"],
    ]))
    add("")
    add("With the numbers (S18.3 measured; S18.4 predicted for the planned U):")
    add("")
    hdr = ["", "S18.3 100 s", "S18.3 200 s", "S18.3 500 s", "S18.4 100 s", "S18.4 200 s", "S18.4 500 s"]
    rows = [
        ["mean above the room (°C)"] + [f(r["mean"] - T_amb, 2) for r in R] + [f(mean_rise, 2)] * 3,
        ["amplitude A1 (°C)"] + [f(r["A1"], 2) for r in R] + [f(e["R"], 2) for e in pred],
        ["lag (s)"] + [f(r["lag_s"], 1) for r in R] + [f(e["dt"], 1) for e in pred],
        ["A2 / A1"] + [pct(r["A2"] / r["A1"], 1) for r in R] + ["0 %"] * 3,
        ["peaks above / dips below"] + [f(r["above"] / r["below"], 2) for r in R] + ["1.00"] * 3,
        ["steepest rise / steepest fall"] + [f(r["slope_up"] / -r["slope_dn"], 2) for r in R] + ["1.00"] * 3,
    ]
    ext(table(hdr, rows))
    add("")
    add(f"![shapes]({FIG}s184_predicted_shapes.png)")
    add("")
    add("*One cycle of the settled S18.3 data (gray dots, black fit), each normalised by its own amplitude and shifted by its own lag, against the pure sinusoid predicted for S18.4 (blue dashed). The taller, earlier peak and the shallower, flatter trough of the S18.3 curves are the second harmonic.*")
    add("")
    add("**How to read the result when it exists.** The S18.3 distortions are the reference; what S18.4 still shows is not caused by reversing the current.")
    add("")
    ext(table(["Feature", "S18.3 measured", "S18.4 if reversing the current were the only cause", "If S18.4 still shows it"], [
        ["second harmonic A2/A1", ", ".join(pct(r["A2"] / r["A1"], 0) for r in R), "about 0 %", "the heating response itself is not linear in u (for example Joule heating grows as u²)"],
        ["peaks above / dips below", ", ".join(f(r["above"] / r["below"], 2) for r in R), "1.00", "the same cause: the heating response is not linear in u"],
        ["mean rise against χh U0", "not applicable (two χ)", f"T_amb + χh U0 = {f(mean_T, 1)} °C", "χh depends on u (the PWM now reaches 2U), or the room temperature changed"],
        ["amplitude against the single-τ prediction", ", ".join(f(100 * d, 0, True) + " %" for d in dev_amp), "no change expected from polarity", "the same deviations mean the plate and rod are not one lump"],
        ["lag against arctan(ωτ)", ", ".join(f(d, 2, True) + " rad" for d in dev_lag), "no change expected from polarity", "the same, a property of the thermal system"],
    ]))
    add("")

    # ---------------------------------------------------------------- 7
    add("## 7. After the run: what to compute")
    add("")
    add("Fit the settled whole cycles of each step exactly as in S18.3 (mean, three harmonics, drift; the lag against the PWM). Then, with the measured mean, A1 and lag φ at each period:")
    add("")
    add("```text")
    add("χh from the mean        χh = (T_mean − T_amb) / U0")
    add("χh from the swing       χh = A1 / (U cos φ)             (N = cos φ, so the measured lag removes τ)")
    add("τ from the lag          τ = tan φ / ω")
    add("distortion              A2/A1, peaks above / below the mean, steepest rise / fall")
    add("```")
    add("")
    add(f"If the one-lump model with one heating susceptibility holds, the two χh agree with each other and with the S18.3 fit ({f(chi, 3)} °C/count) and τ is near {f(tau, 0)} s. The measured mean should be within a")
    add("degree or two of the target. The tables, figures and comparison with the S18.3 page are produced from the S18.4 file by an analysis script that is still to be written;")
    add("it needs only the heating-only version of the S18.3 fits, because there is no cooling branch to fit.")
    add("")

    # ---------------------------------------------------------------- 8
    add("## 8. Limits of these predictions")
    add("")
    add(f"- No S18.4 run exists. T* = {target:g} °C and the room temperature of {f(T_amb, 2)} °C (the S18.3 idle baseline) are assumptions; use the numbers of the day.")
    add(f"- χh is taken constant. S18.3 covered u from 0 to 50 counts, S18.4 goes to {2 * U_work:.0f}; the 10 November hold at {f(hold['u'], 0)} counts supports the value, but the response between {R[0]['U']:.0f} and {2 * U_work:.0f} counts has not been measured.")
    add(f"- The one-lump model missed the S18.3 amplitude by {f(100 * dev_amp[0], 0, True)} %, {f(100 * dev_amp[1], 0, True)} % and {f(100 * dev_amp[2], 0, True)} % and the lag by {f(dev_lag[0], 2, True)} rad at 100 s, so the amplitudes and lags above are good to about 10 %.")
    add("- The T1 numbers scale the S18.3 rod response and are estimates.")
    add("- The one-click plan in the GUI is S18.3 only; S18.4 is run with the boxes as in section 2.")
    add("")

    # ---------------------------------------------------------------- 9
    add("## 9. Files and how to reproduce")
    add("")
    add("```bash")
    add(f"python3 python/sammy_module8_s184_page.py --target {target:g}")
    add("```")
    add("")
    add(f"It fits the S18.3 run `{run183}`, reads the PI hold of `{os.path.basename(HOLD_RUN)}`, and rewrites this page and the two figures.")
    add("")
    add("## AI assistance")
    add("")
    add("This page, its script and its figures were produced with GitHub Copilot assistance and checked against the Module 8 page, the Module 6 model, the sketch and the GUI code,")
    add("the S18.3 run and the 10 November hold. The derivation in section 3 was also verified numerically (section 3.6).")

    return L, dict(t=t, u=u, T=T, bounds=bounds, ups=ups, U_work=U_work, m=m, T_amb=T_amb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=float, default=40.0, help="target mean TEC temperature, C (the page's number was lost from the pasted text)")
    ap.add_argument("--u", type=float, default=None, help="override the working U = U0 in counts")
    a = ap.parse_args()
    A = S.analyse(S183_RUN)
    hold = hold_calibration(HOLD_RUN)
    L, g = build(A, hold, a.target, a.u)
    os.makedirs(an.FIG_DIR, exist_ok=True)
    fig_run(os.path.join(an.FIG_DIR, "s184_predicted_run.png"), g["t"], g["u"], g["T"], g["bounds"], g["ups"], g["m"], g["T_amb"], g["U_work"], a.target)
    fig_shapes(os.path.join(an.FIG_DIR, "s184_predicted_shapes.png"), A)
    with open(PAGE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print(f"U = U0 = {g['U_work']:.0f} counts for {a.target:g} C (hold gives {a.target - A['T_amb']:.2f}/{hold['chi']:.3f}, fit {A['model']['chi_h']:.3f})")
    print(f"Wrote {os.path.relpath(PAGE, an.REPO)} and two figures in {os.path.relpath(an.FIG_DIR, an.REPO)}")


if __name__ == "__main__":
    main()
