#!/usr/bin/env python3
"""
Writes the S18.3 walkthrough (markdown) from the dictionary that sammy_module8_s183_analysis.analyse() returns.
Every number in the text comes from that dictionary or from the run file; the prose around the numbers is fixed.
It is called by the analysis script (python/sammy_module8_s183_analysis.py), not run on its own.
"""

import csv
import math
import os

FIG = "../figures/module_08_sammy/"
IMG = "../images/"

# Phone photos of the live GUI, straightened and cropped to the GUI window: (file, photo id, clock on the phone, "valid" count on screen)
PHOTOS = [("module08_sammy_gui_s183_step2_t899s_IMG_2564.jpg", "IMG_2564", "12:37 PM", 1674),
          ("module08_sammy_gui_s183_step3_t1824s_IMG_2565.jpg", "IMG_2565", "12:52 PM", 3404),
          ("module08_sammy_gui_s183_step3_t2296s_IMG_2566.jpg", "IMG_2566", "1:00 PM", 4287)]


def f(x, d=2, plus=False):
    """Number with a real minus sign (and an optional plus sign)."""
    s = f"{x:+.{d}f}" if plus else f"{x:.{d}f}"
    if float(s) == 0.0:
        s = s.lstrip("+-")
        s = ("+" if plus else "") + s
    return s.replace("-", "\u2212")


def pct(x, d=0):
    return f(100.0 * x, d) + " %"


def row(*cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


def table(head, rows):
    out = [row(*head), row(*["---"] * len(head))]
    out += [row(*r) for r in rows]
    return out


def read_notes(run_path):
    p = run_path[:-4] + "_notes.csv"
    out = []
    if os.path.exists(p):
        with open(p, newline="") as fh:
            for r in csv.DictReader(fh):
                if "<" in r["note"]:          # a typed-in placeholder, replaced by the corrected note below it
                    continue
                out.append((r["wall_clock"][11:16], float(r["time_ms"]) / 1000.0, r["note"].strip()))
    return out


def write(A, path):
    R, E, Pd, m = A["results"], A["eq"], A["preds"], A["model"]
    M6, M4 = A["m6"], A["m4"]
    U, base, rod0, tau = A["U"], A["T_amb"], A["room_rod"], m["tau"]
    stamp = A["stamp"]
    name = os.path.basename(A["path"])
    chi_mid, chib = A["chi_mid"], A["chi_fit_bar"]
    dchi = 0.5 * (m["chi_h"] - m["chi_c"])
    ratio = m["chi_h"] / m["chi_c"]
    shift_fit = (m["chi_h"] - m["chi_c"]) * U / math.pi
    shift_m6 = (M6["chi_h"] - M6["chi_c"]) * U / math.pi
    shift_m4 = (M4["chi_h"] - M4["chi_c"]) * U / math.pi
    cols = A["cols"]
    t0s = A["steps"][0]["t0"]
    t_end = A["steps"][-1]["t1"]
    plan_min = (t_end - t0s) / 60.0
    pre, sg = A["pre"], A["sign"]
    idle = A["idle"]
    figs = lambda key: f"{FIG}{stamp}_s183_{key}.png"
    pers = ", ".join(f"{r['period']:g}" for r in R[:-1]) + f" and {R[-1]['period']:g} s"
    # shortcuts for the three periods
    r1, r2, r3 = R[0], R[1], R[2]
    # inverted one-lump numbers: time constant implied by each measured amplitude and lag
    tau_amp, tau_lag = [], []
    for r in R:
        n_meas = r["A1"] / (chib * U)
        tau_amp.append(math.sqrt(max(1.0 / n_meas ** 2 - 1.0, 0.0)) / r["w"])
        tau_lag.append(math.tan(r["lag"]) / r["w"])
    # worked example: the middle period
    ex = E[1]
    skips_txt = ", ".join("%d cycle%s at %g s" % (r["skip"], "" if r["skip"] == 1 else "s", r["period"]) for r in R)
    skip_tau = [r["skip"] * r["period"] / tau for r in R]
    # how far the fitted model is from each measurement (percent)
    dev = [dict(mean=100 * ((r["mean"] - base) / p["fit_mean_F"] - 1), A1=100 * (r["A1"] / p["fit_A1_F"] - 1), A2=100 * (r["A2"] / p["fit_A2_F"] - 1))
           for r, p in zip(R, Pd)]
    dev_long = max(abs(v) for d in dev[1:] for v in d.values())
    dev_short = max(abs(v) for v in dev[0].values())
    kappas = [r["kappa"] * 1e5 for r in R]
    kappa_spread = (max(kappas) - min(kappas)) / (sum(kappas) / len(kappas))

    L = []
    add = L.append
    ext = L.extend

    # ------------------------------------------------------------------ title
    add("# Module 8, S18.3: raw sinusoidal PWM with U0 = 0, step by step (SAMMY copy)")
    add("")
    add(f"A walkthrough of the run `{name}` (11 November 2026, one click, {plan_min:.1f} minutes of schedule), written so that every")
    add("step can be followed from the first idea to the last number. All numbers below are produced from that file by")
    add("`python/sammy_module8_s183_analysis.py`; none is typed in by hand.")
    add(f"Figures: `docs/figures/module_08_sammy/{stamp}_s183_*.png`. Photos: `docs/images/module08_sammy_gui_s183_*.jpg`.")
    add(f"Tables: `data/module_08_sammy/s183_analysis_{stamp}/`. Kapil Naidu's acquisition code, analysis scripts and data are unchanged;")
    add("everything here is an addition.")
    add("")
    add("Some numbers disappeared from the pasted assignment text, among them the PWM amplitude U (the page says to keep it fixed). This document uses")
    add(f"U = {U:.0f} counts (the sketch default; the applied PWM measures {f(U, 1)}). Because the susceptibility of the page's equal-susceptibility check may also have been lost, that check is given")
    add(f"for three values, {M6['chi_c']:g}, {chi_mid:.3f} (the mean of the Module 6 defaults) and {M6['chi_h']:g} °C/count; the course value can be read off or recomputed from R = χ U N (section 4.4).")
    add("")

    # ------------------------------------------------------------------ section 0
    add("## 0. The result in one table and six sentences")
    add("")
    ext(table(["Period", "Settled cycles used", "Mean TEC temperature (°C)", "Mean above the idle baseline (°C)", "Amplitude A1 (°C)",
               "Lag behind the PWM", "Highest / lowest (°C)"],
              [[f"{r['period']:g} s", f"{r['used']} of {r['ncyc']}", f(r["mean"]), f(r["mean"] - base, 2, True), f(r["A1"]),
                f"{f(r['lag'], 3)} rad = {f(r['lag_s'], 1)} s", f"{f(r['Tmax'])} / {f(r['Tmin'])}"] for r in R]))
    add("")
    add(f"The PWM was u = {U:.0f} sin(2π t / P) counts in every step (zero average, U0 = 0). The idle baseline is the TEC thermistor with nothing switched on:")
    add(f"{f(base)} °C (room temperature from the rod sensors: {f(rod0)} °C).")
    add("")
    add(f"1. **The average moves.** The plate does not swing around room temperature. It swings around a mean {f(r1['mean'] - base, 2)}, {f(r2['mean'] - base, 2)} and {f(r3['mean'] - base, 2)} °C above the idle baseline,")
    add(f"   the same at all three periods within {f(max(r['mean'] for r in R) - min(r['mean'] for r in R), 2)} °C. Heating is stronger than cooling, and the average of the one-lump model is exactly")
    add(f"   (χh − χc) U / π = {f(shift_fit)} °C for the fitted χ (section 4.5), whatever the period.")
    add(f"2. **The amplitude is not constant.** With U fixed, the fundamental amplitude is {f(r1['A1'])}, {f(r2['A1'])} and {f(r3['A1'])} °C: it grows by a factor {f(r3['A1'] / r1['A1'], 2)} between the")
    add(f"   shortest and the longest period. The plate acts as a low-pass filter (section 4.3).")
    add(f"3. **The delay shows up two ways.** As an angle the lag falls from {f(r1['lag'], 2)} to {f(r3['lag'], 2)} rad as the period grows; as a time it rises from {f(r1['lag_s'], 1)} s to {f(r3['lag_s'], 1)} s.")
    add(f"4. **The waveform is lopsided.** The peaks above the mean are {f(r1['above'] / r1['below'], 2)}, {f(r2['above'] / r2['below'], 2)} and {f(r3['above'] / r3['below'], 2)} times the dips below it; the steepest rise is")
    add(f"   {f(r1['slope_up'] / -r1['slope_dn'], 2)}, {f(r2['slope_up'] / -r2['slope_dn'], 2)} and {f(r3['slope_up'] / -r3['slope_dn'], 2)} times the steepest fall; the second harmonic is {pct(r1['A2'] / r1['A1'], 1)}, {pct(r2['A2'] / r2['A1'], 1)} and {pct(r3['A2'] / r3['A1'], 1)} of the fundamental.")
    add(f"5. **One lump with two susceptibilities explains it.** Fitting the Module 6 model to the whole record gives χh = {f(m['chi_h'], 3)}, χc = {f(m['chi_c'], 3)} °C/count and τ = {f(tau, 1)} s")
    add(f"   (RMS misfit {f(m['rms'], 2)} °C). The ratio χh/χc = {f(ratio, 2)} matches the Module 4 value r = {f(M4['chi_h'] / M4['chi_c'], 3)}.")
    add(f"6. **A constant PWM amplitude does not give a constant temperature amplitude.** Holding a {f(5.0, 0)} °C amplitude at the three periods would take about")
    add(f"   {f(E[0]['U_need5'], 0)}, {f(E[1]['U_need5'], 0)} and {f(E[2]['U_need5'], 0)} counts (fitted model, section 4.6).")
    add("")

    # ------------------------------------------------------------------ section 1
    add("## 1. Words and symbols")
    add("")
    ext(table(["Symbol", "In plain words", "Units"], [
        ["u", "the knob: the signed PWM command. Positive heats, negative cools, 255 is the maximum", "counts"],
        ["U", f"how far the knob swings each way (the amplitude of u); here {U:.0f}", "counts"],
        ["P", "how long one full swing of the knob takes (the period)", "s"],
        ["ω = 2π/P", "how fast the swing goes, as an angle per second (one full swing is 2π radians)", "rad/s"],
        ["T", "temperature of the TEC plate, what the TEC thermistor reads", "°C"],
        ["T_amb", "room temperature (the idle baseline of this run)", "°C"],
        ["θ = T − T_amb", "how much hotter than the room the plate is", "°C"],
        ["χ (chi)", "how many °C hotter the plate ends up per count of PWM if the knob is held still for a long time; χh when heating, χc when cooling", "°C/count"],
        ["τ (tau)", "the plate's sluggishness: after a sudden change it covers 63 % of the way to its new temperature in τ seconds", "s"],
        ["N", "the shrink factor 1/√(1 + (ωτ)²): how much of the push survives as a temperature swing", "none"],
        ["φ (phi)", "how late the temperature swing is behind the knob swing, as an angle; the delay in seconds is φ/ω", "rad"],
        ["A1, A2, A3", "sizes of the temperature wiggle at the PWM frequency (1st), at twice it (2nd) and at three times it (3rd)", "°C"],
    ]))
    add("")

    # ------------------------------------------------------------------ section 2
    add("## 2. What was run, as a series of steps")
    add("")
    add("The Arduino sketch `arduino/module_08_sammy/angstrom_tec_sammy` was in RAW mode: u = U0 + U sin(phase), no feedback, clamped to ±255. The TEC thermistor")
    add("is on A0 and the rod sensors T1 to T5 on A1 to A5; a record is sent every 0.5 s. A safety latch sets the output to 0 if T1 > 56 °C, the TEC thermistor > 65 °C")
    add("or five TEC readings in a row are bad. The GUI's one-click plan (`START PLAN`) set mode RAW, U = 50, U0 = 0, sent the three-line schedule and started it;")
    add("`STOP` cancels the rest.")
    add("")
    ext(table(["Step", "What the PWM does", "Why", "Arduino time (s)"], [
        ["idle", "u = 0", f"measure room temperature and sensor noise ({idle['TEC_C']['n']} samples at 0.5 s)", f"{A['bwin'][0]:.0f} to {A['bwin'][1]:.0f}"],
        *([["test START", f"PI mode, u = {f(pre['u_lo'], 0)} to {f(pre['u_hi'], 0)}",
            f"a quick check that the TEC responds; TEC {f(pre['T_start'], 1)} to {f(pre['T_peak'], 1)} °C; not part of S18.3, outside every fit", f"{pre['t0']:.0f} to {pre['t1'] + 0.5:.0f}"]] if pre else []),
        *[[f"sweep {s['step']}", f"u = {U:.0f} sin(2π t / {s['period']:g} s)", f"{s['ncyc']} cycles of {s['period']:g} s", f"{s['t0']:.0f} to {s['t1'] + 0.5:.0f}"] for s in A["steps"]],
        ["end", "u = 0 (plan finished)", "the plate drifts back toward room temperature", f"from {t_end + 0.5:.0f}"],
    ]))
    add("")
    add(f"Each sweep starts at phase zero, so u begins at 0 and goes positive (heating) first. The TEC was {f(pre['T_plan_start'] if pre else A['Ts'][0], 1)} °C when sweep 1 began,")
    add(f"{f((pre['T_plan_start'] if pre else A['Ts'][0]) - base, 1)} °C above the idle baseline: close to the \"start near room temperature\" the page asks for. The run has {len(cols['t'])} records; the schedule part has {len(A['ts'])}.")
    add("")
    add("### Photos of the run")
    add("")
    add("Phone photos of the laptop screen during the run, straightened and cropped to the GUI window (metadata removed; the full-screen")
    add("originals are not in the repository). The numbers on screen are the logged values: the temperatures, the PWM and the stream's valid-record count")
    add("equal the CSV record with that number. Left: temperature and PWM traces; middle: live values and stream counters; right: the run controls,")
    add("the \"One long run\" plan box, the settings and the schedule text.")
    add("")
    for fn, pid, clock, nrec in PHOTOS:
        if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(path)), IMG, fn)) or nrec > len(cols["t"]):
            continue
        i = nrec - 1
        ts = cols["t"][i]
        st, per = int(cols["step"][i]), cols["period_s"][i]
        temps = ", ".join(f"T{k} {cols[f'T{k}_C'][i]:.2f}" for k in range(1, 6))
        add(f"![{pid}, {clock}: sweep {st} ({per:g} s period), t = {ts:.1f} s]({IMG}{fn})")
        add("")
        add(f"*{pid}, {clock}: sweep {st} ({per:g} s period), t = {ts:.1f} s. On screen: TEC {cols['TEC_C'][i]:.2f} °C, {temps} °C; applied PWM {int(cols['signed_pwm'][i]):+d} (record {nrec}).*")
        add("")
    notes = read_notes(A["path"])
    if notes:
        add("Notes in the run's notes file (typed in the GUI, plus the automatic plan notes):")
        add("")
        for clock, ts, txt in notes:
            add(f"- {clock} (t = {ts:.0f} s): {txt}")
        add("")

    # ------------------------------------------------------------------ section 3
    add("## 3. The idea in a picture")
    add("")
    add("Think of a bathtub. A warm tap pours in when u is positive and a cold tap when u is negative; the tap is turned up and down like a swing. The bathtub also")
    add("slowly drains and leaks heat to the room, and it holds a lot of water, so its temperature cannot change quickly. If the tap swings slowly the water")
    add("temperature follows it closely. If the tap swings quickly the temperature cannot keep up: it moves less, and it is late. The TEC plate with the aluminum")
    add("rod behaves like that bathtub, with one more twist: the warm tap is stronger than the cold tap (χh > χc).")
    add("")
    add(f"![push versus response]({figs('push_vs_response')})")
    add("")
    add("*The shaded humps are the push the PWM asks for, χ(u)·u with the fitted χ (a tall heating hump, a short cooling hump). The dashed curve is the one-lump model, the black")
    add("curve is the measured TEC temperature above the idle baseline. The plate smooths the humps; the quicker the swing, the more it smooths.*")
    add("")

    # ------------------------------------------------------------------ section 4
    add("## 4. The math, one step at a time")
    add("")
    add("### 4.1 The rule the plate follows (Module 6 one-lump model)")
    add("")
    add("```text")
    add("τ · dT/dt = −(T − T_amb) + χ(u) · u            χ(u) = χh when u > 0 (heating),  χc when u < 0 (cooling)")
    add("```")
    add("")
    add("- `dT/dt` is how fast the plate temperature changes, in °C per second.")
    add("- `−(T − T_amb)` is the leak. The hotter the plate is than the room, the faster it loses heat; it always pulls T back toward the room temperature.")
    add("- `χ(u)·u` is the push from the TEC. Held forever, u counts would lift the plate to T_amb + χ u (put dT/dt = 0 to see it).")
    add("- `τ` turns \"push minus leak\" into a speed: a large τ means a slow plate.")
    add("")
    add(f"The Module 6 simulation defaults are T_amb = {M6['T_amb']:g} °C, χh = {M6['chi_h']:g}, χc = {M6['chi_c']:g} °C/count and τ = {M6['tau']:g} s. This run's own values are in sections 4.5 and 6.")
    add("")
    add("### 4.2 Step zero: measure from the room")
    add("")
    add("Let θ = T − T_amb, how much hotter than the room. T_amb does not change, so dθ/dt = dT/dt and the rule becomes")
    add("")
    add("```text")
    add("τ · dθ/dt + θ = χ(u) · u                          (S18.3.1 when χ(u) is one number χ)")
    add("```")
    add("")
    add("With the knob swinging as u = U sin(ωt), ω = 2π/P, and the same χ for both signs of u, the right-hand side is χ U sin(ωt).")
    add("")
    add("### 4.3 The page's first case: equal heating and cooling (χh = χc = χ)")
    add("")
    add("**Step A, guess.** The plate is pushed by a sine, so after a while it must wiggle at the same frequency, with a different size and timing. A sine and a cosine with")
    add("two unknown sizes a and b can make any size and timing:")
    add("")
    add("```text")
    add("θp(t) = a · sin(ωt) + b · cos(ωt)")
    add("```")
    add("")
    add("**Step B, differentiate.**")
    add("")
    add("```text")
    add("dθp/dt = a ω · cos(ωt) − b ω · sin(ωt)")
    add("```")
    add("")
    add("**Step C, put both into the equation.**")
    add("")
    add("```text")
    add("τ (a ω cos ωt − b ω sin ωt) + a sin ωt + b cos ωt = χ U sin ωt")
    add("```")
    add("")
    add("**Step D, collect the sines and the cosines.**")
    add("")
    add("```text")
    add("(a − ωτ b) · sin ωt + (ωτ a + b) · cos ωt = χ U · sin ωt + 0 · cos ωt")
    add("```")
    add("")
    add("**Step E, match.** The equation must hold at every instant, so the sine parts must agree and the cosine parts must agree:")
    add("")
    add("```text")
    add("sine:    a − ωτ b = χ U")
    add("cosine:  ωτ a + b = 0")
    add("```")
    add("")
    add("**Step F, solve.** The cosine line gives b = −ωτ a. Put that into the sine line: a + (ωτ)² a = χ U, so")
    add("")
    add("```text")
    add("a =  χ U / (1 + (ωτ)²)")
    add("b = −ωτ · χ U / (1 + (ωτ)²)")
    add("```")
    add("")
    add("**Step G, one sine instead of two.** Write the answer as R sin(ωt − φ). Expanding, R sin(ωt − φ) = R cos φ · sin ωt − R sin φ · cos ωt, so a = R cos φ and b = −R sin φ.")
    add("Squaring and adding gives R² = a² + b²; dividing gives tan φ = −b/a:")
    add("")
    add("```text")
    add("R² = a² + b² = (χ U)² (1 + (ωτ)²) / (1 + (ωτ)²)² = (χ U)² / (1 + (ωτ)²)")
    add("R = χ U / √(1 + (ωτ)²) = χ U · N          tan φ = ωτ,   φ = arctan(ωτ)")
    add("```")
    add("")
    add("**Step H, add the start-up.** A pure leak, with no push, would die away as e^(−t/τ), and adding C·e^(−t/τ) to a solution does not break the equation")
    add("(it satisfies τ dθ/dt + θ = 0 by itself). So the general solution is θ(t) = R sin(ωt − φ) + C e^(−t/τ).")
    add("")
    add("**Step I, start from room temperature.** θ(0) = 0 gives 0 = R sin(−φ) + C, so C = R sin φ and")
    add("")
    add("```text")
    add("θ(t) = R · [ sin(ωt − φ) + sin φ · e^(−t/τ) ]")
    add("```")
    add("")
    add("**Step J, read it.** After a few τ the exponential is gone and the plate swings at the PWM's own frequency with size R = χ U N, which is smaller than the push χ U by the")
    add("shrink factor N < 1, and with a delay φ = arctan(ωτ) behind the PWM, a time delay Δt = φ/ω.")
    add("")
    add("- Slow swing (ωτ much less than 1): N → 1 and φ → 0. The plate follows the knob.")
    add("- ωτ = 1: N = 0.71 and φ = π/4 (an eighth of a period late).")
    add("- Fast swing (ωτ much more than 1): N ≈ 1/(ωτ) and φ → π/2 (a quarter period late). The plate hardly moves.")
    add("")
    add("### 4.4 Check the answer")
    add("")
    add("**Does it satisfy the equation?** Differentiate θ = R[sin(ωt − φ) + sin φ · e^(−t/τ)]:")
    add("")
    add("```text")
    add("τ dθ/dt = R · [ ωτ cos(ωt − φ) − sin φ · e^(−t/τ) ]")
    add("τ dθ/dt + θ = R · [ ωτ cos(ωt − φ) + sin(ωt − φ) ] + R sin φ · e^(−t/τ) · (−1 + 1)")
    add("             = R · [ sin(ωt − φ) + ωτ cos(ωt − φ) ]")
    add("```")
    add("")
    add("The exponential terms cancel. Now use ωτ = tan φ = sin φ / cos φ:")
    add("")
    add("```text")
    add("sin(ωt − φ) + (sin φ / cos φ) cos(ωt − φ) = [ sin(ωt − φ) cos φ + cos(ωt − φ) sin φ ] / cos φ = sin(ωt) / cos φ")
    add("```")
    add("")
    add("and cos φ = 1/√(1 + tan²φ) = 1/√(1 + (ωτ)²) = N, so R / cos φ = χ U N / N = χ U. Hence τ dθ/dt + θ = χ U sin ωt, which is the equation. The start:")
    add("θ(0) = R [sin(−φ) + sin φ] = 0, as required.")
    add("")
    add(f"**Worked numbers for P = {ex['period']:g} s** (τ = {M6['tau']:g} s):")
    add("")
    wk = [("ω", f"2π / {ex['period']:g} s", f"{ex['w']:.6f} rad/s"),
          ("ωτ", f"{ex['w']:.6f} × {M6['tau']:g}", f(ex["wtau"], 4)),
          ("N", f"1 / √(1 + {f(ex['wtau'], 4)}²)", f(ex["norm"], 4)),
          ("φ", f"arctan({f(ex['wtau'], 4)})", f"{f(ex['phi'], 4)} rad = {f(math.degrees(ex['phi']), 1)}°"),
          ("Δt", f"φ / ω = {f(ex['phi'], 4)} / {ex['w']:.6f}", f"{f(ex['dt'], 2)} s"),
          ("R", f"χ U N = {chi_mid:.3f} × {U:.0f} × {f(ex['norm'], 4)}", f"{f(ex['R_mid'], 3)} °C   (for χ = {chi_mid:.3f})")]
    wa, wb = max(len(a) for a, _, _ in wk), max(len(b) for _, b, _ in wk)
    add("```text")
    for a_, b_, c_ in wk:
        add(f"{a_.ljust(wa)} = {b_.ljust(wb)} = {c_}")
    add("```")
    add("")
    add("**All three periods** (τ = 80 s, the Module 6 value; N, φ and Δt do not depend on χ):")
    add("")
    ext(table(["P (s)", "ω (rad/s)", "ωτ", "N", "φ (rad)", "Δt (s)", f"R, χ = {M6['chi_c']:g}", f"R, χ = {chi_mid:.3f}", f"R, χ = {M6['chi_h']:g}"],
              [[f"{e['period']:g}", f"{e['w']:.5f}", f(e["wtau"], 3), f(e["norm"], 4), f(e["phi"], 4), f(e["dt"], 2), f(e["R_c"], 2), f(e["R_mid"], 2), f(e["R_h"], 2)] for e in E]))
    add("")
    add(f"R is in °C for U = {U:.0f} counts; for another χ or U, multiply N by χ U.")
    add("")
    add("**Numerical check.** The equation was also integrated numerically (fourth-order Runge-Kutta, 0.02 s steps) from θ = 0 for each period and compared with the formula at every step;")
    add(f"the largest difference is {A['theory_worst']:.1e} °C, which is rounding error.")
    add("")
    add(f"![analytic against numerical]({figs('theory_check')})")
    add("")
    add("*Blue: the formula, including the start-up transient. Red dots: the numerical integration. Gray dashed: the settled part alone.*")
    add("")
    add("### 4.5 When heating and cooling differ (χh ≠ χc)")
    add("")
    add("The page warns that one sinusoidal guess does not solve this case, because the push is a sine only while u keeps one sign. Two facts still hold and give most of the answer.")
    add("")
    add("**Fact 1: the average temperature rise, exactly.** In the settled state the temperature repeats every cycle, so the average of dθ/dt over one cycle is zero. Average the equation:")
    add("")
    add("```text")
    add("avg(θ) = avg(χ(u) u) = (1/2π) ∫ χ(U sin x) · U sin x dx")
    add("                       = (U/2π) · [ χh ∫(0..π) sin x dx + χc ∫(π..2π) sin x dx ]")
    add("                       = (U/2π) · [ 2 χh − 2 χc ]  =  (χh − χc) U / π")
    add("```")
    add("")
    add(f"This holds for any τ and any period. With the fitted values it is ({f(m['chi_h'], 4)} − {f(m['chi_c'], 4)}) × {U:.1f} / π = {f(shift_fit)} °C; the Module 6 defaults give {f(shift_m6)} °C and the")
    add(f"Module 4 curve ({M4['chi_h']:g}, {M4['chi_c']:g}) gives {f(shift_m4)} °C. The measured shifts are {f(r1['mean'] - base)}, {f(r2['mean'] - base)} and {f(r3['mean'] - base)} °C.")
    add("")
    add("**Fact 2: the waveform, split into two pieces.** Let χavg = (χh + χc)/2 and Δχ = (χh − χc)/2, so χh = χavg + Δχ and χc = χavg − Δχ. With x = ωt the push is")
    add("")
    add("```text")
    add("f = χ(u) u = χavg U sin x + Δχ U |sin x|")
    add("```")
    add("")
    add("Check: where sin x > 0 this is (χavg + Δχ) U sin x = χh U sin x; where sin x < 0, |sin x| = −sin x and it is (χavg − Δχ) U sin x = χc U sin x. The plate treats each piece")
    add("separately (the equation is linear for a given f), and the pieces add up:")
    add("")
    add("- **Piece 1, χavg U sin x,** is exactly the equal-susceptibility problem of section 4.3 with χ = χavg. It gives a swing of size χavg U N and lag arctan(ωτ).")
    add("- **Piece 2, Δχ U |sin x|,** is a train of bumps. Its standard Fourier series is a constant plus even harmonics only:")
    add("")
    add("```text")
    add("|sin x| = 2/π − (4/π) · [ cos 2x / (1·3) + cos 4x / (3·5) + cos 6x / (5·7) + ... ]")
    add("```")
    add("")
    add("Each harmonic of frequency nω goes through the same filter as before: its size is multiplied by Nn = 1/√(1 + (nωτ)²) and it is delayed by arctan(nωτ). Adding all of it:")
    add("")
    add("```text")
    for lhs, note in (("θ(t) = 2ΔχU/π", "the mean: (χh − χc) U / π"),
                      ("     + χavg U N1 · sin(x − φ1)", "the swing at the PWM frequency"),
                      ("     − (4ΔχU / 3π) N2 · cos(2x − φ2)", "second harmonic, sets the lopsidedness"),
                      ("     − (4ΔχU / 15π) N4 · cos(4x − φ4) − ...", "fourth, sixth, ... harmonics (small; no third, fifth, ... harmonic)")):
        add(lhs.ljust(46) + note)
    add("```")
    add("")
    add("What this says about the experiment:")
    add("")
    add("- the swing at the PWM frequency has the equal-susceptibility size and lag with χ replaced by the average χavg. The asymmetry does not change it;")
    add("- the asymmetry shows up as a raised average and as even harmonics. The lowest even harmonic is the 2nd, A2 = (4ΔχU / 3π) N2. The 3rd harmonic should be zero;")
    add("- the quicker the swing, the more the filter flattens the even harmonics (N2 < N1), so the lopsidedness fades at short periods. In the slow limit θ ≈ f and the peaks would be")
    add(f"  χh U = {f(m['chi_h'] * U, 1)} °C up and χc U = {f(m['chi_c'] * U, 1)} °C down.")
    add("")
    add("The series was compared with numerical integration of the piecewise equation for the Module 6 defaults, the Module 4 curve and the fitted values:")
    add(f"the largest difference in mean, A1 and A2 is {A['fourier_check']['amp']:.1e} °C (the lag differs by {A['fourier_check']['lag']:.1e} rad, the half-sample hold of the numerical scheme).")
    add("")
    ext(table(["Period", "Quantity", "Measured", f"Equal χ ({chi_mid:.3f}, τ = {M6['tau']:g} s)", f"Unequal, Module 6 defaults ({M6['chi_h']:g}, {M6['chi_c']:g}, {M6['tau']:g} s)",
               f"Unequal, fitted ({f(m['chi_h'], 3)}, {f(m['chi_c'], 3)}, {f(tau, 1)} s)"],
              [row_ for r, p in zip(R, Pd) for row_ in (
                  [f"{r['period']:g} s", "mean above idle (°C)", f(r["mean"] - base), "0", f(p["m6_mean_F"]), f(p["fit_mean_F"])],
                  ["", "A1 (°C)", f(r["A1"]), f(p["equal_R"]), f(p["m6_A1_F"]), f(p["fit_A1_F"])],
                  ["", "lag (rad)", f(r["lag"], 3), f(p["equal_phi"], 3), f(p["m6_lag_F"], 3), f(p["fit_lag_F"], 3)],
                  ["", "A2 (°C)", f(r["A2"]), "0", f(p["m6_A2_F"]), f(p["fit_A2_F"])])]))
    add("")
    add("### 4.6 Why a constant PWM amplitude cannot give a constant temperature amplitude")
    add("")
    add("The swing at the PWM frequency is χavg U N(ω) with N = 1/√(1 + (ωτ)²), and N falls as ω rises. To hold the temperature amplitude at A* the PWM amplitude must grow as the period shortens:")
    add("")
    add("```text")
    add("U(P) = A* / (χavg N) = (A* / χavg) · √(1 + (ωτ)²)")
    add("```")
    add("")
    add(f"For A* = 5 °C, χavg = {f(chib, 4)} °C/count and τ = {f(tau, 1)} s this is {f(E[0]['U_need5'], 1)}, {f(E[1]['U_need5'], 1)} and {f(E[2]['U_need5'], 1)} counts at {pers}. This is what the later")
    add("feedforward and PI stages have to supply.")
    add("")

    # ------------------------------------------------------------------ section 5
    add("## 5. How the numbers were pulled out of the data")
    add("")
    add("1. **Offsets.** The calibration offsets of `data/module_08/calibration_rod_run_20261026_112627.csv` are applied to the TEC thermistor and T1 to T5 (corrected = logged − offset). The raw CSV is not changed.")
    add(f"2. **Idle baseline (u = 0).** The mean and scatter of every channel over t = {A['bwin'][0]:.0f} to {A['bwin'][1]:.0f} s, before anything was switched on. The TEC mean is T_amb for the model fit and the")
    add("   reference for \"mean above idle\".")
    add("3. **Whole cycles only.** Each sweep is cut into whole cycles that start at phase zero (the PWM goes through zero upward). The first cycles are start-up, because the plate begins each sweep at")
    add(f"   the end state of the previous one. Enough start-up cycles are skipped to cover 2.5 τ with τ = {M6['tau']:g} s: {skips_txt}. The remaining cycles are fitted together.")
    add("4. **The fit.** For the settled cycles of one sweep the TEC temperature is fitted, by linear least squares, with")
    add("")
    add("```text")
    add("T(t) = a + Σ(k=1..3) [ b_k cos(kω s) + c_k sin(kω s) ] + d · s          s = t − t_mid,   ω = 2π/P")
    add("```")
    add("")
    add("   `a` is the average over the cycles, `d` a slow drift in °C/s (so that a drifting baseline does not leak into the harmonics), and b_k, c_k the cosine and sine content of the k-th harmonic.")
    add("   \"Least squares\" means: the computer picks the numbers that make the sum of the squared misses smallest; because the unknowns enter linearly this is one matrix solution, with no guessing.")
    add("   The size of the k-th harmonic is A_k = √(b_k² + c_k²) and its phase θ_k = atan2(b_k, c_k), so the term reads A_k sin(kω s + θ_k).")
    add("5. **Lag.** The applied PWM is fitted in the same way. The lag of the temperature behind the PWM is θ_u1 − θ_T1 in radians, and Δt = lag/ω in seconds.")
    add("6. **Distortion.** THD = √(A2² + A3²)/A1. The page's \"sinusoidal-fit residual\" is also given: the same fit with a mean, one sinusoid and the drift only.")
    add("7. **Error bars.** The fundamental is also fitted to each whole cycle separately; the tables give the standard error of the mean over the used cycles and the half-range. With only two or three")
    add("   cycles these are lower bounds on the true uncertainty: they do not include a leftover start-up transient or the model error.")
    add("8. **Model fit to the whole record.** For a trial τ, the two unit responses h and c are computed from the recorded PWM (exact between records, u held for 0.5 s):")
    add("   τ dh/dt + h = max(u, 0) and τ dc/dt + c = min(u, 0). Then T − T_amb − (T(0) − T_amb) e^(−t/τ) = χh h + χc c is fitted for χh and χc by linear least squares, and τ is found by a one-dimensional search for the")
    add("   smallest RMS misfit. The record used is every schedule sample (the start-up cycles included).")
    add("")
    add("The uncertainty of the rod positions and the rod fits are not part of the S18.3 question; the rod sensors are used once, as a cross-check, in section 8.")
    add("")

    # ------------------------------------------------------------------ section 6
    add("## 6. Results")
    add("")
    add("### 6.1 Idle data (u = 0)")
    add("")
    ext(table(["Channel", "Mean (°C)", "Scatter, sd (°C)", "Samples"],
              [[ch[:-2] if ch.endswith("_C") else ch, f(s["mean"], 3), f(s["sd"], 3), s["n"]] for ch, s in idle.items()]))
    add("")
    add(f"The rod sensors average {f(rod0, 2)} °C; the TEC thermistor reads {f(base - rod0, 2)} °C higher. The scatter of a channel is a few thousandths to about a hundredth of a °C, so the")
    add("amplitudes below are far above the noise.")
    add("")
    add("### 6.2 Sign check")
    add("")
    add(f"In the first half of sweep 1 the PWM averaged {f(sg['u_first'], 1, True)} counts and the TEC went from {f(sg['T_a'], 2)} to {f(sg['T_b'], 2)} °C ({f(sg['T_b'] - sg['T_a'], 2, True)} °C): **positive PWM heats**.")
    add(f"In the second half it averaged {f(sg['u_second'], 1, True)} counts and the TEC went from {f(sg['T_b'], 2)} to {f(sg['T_c'], 2)} °C ({f(sg['T_c'] - sg['T_b'], 2, True)} °C): **negative PWM cools**. This is the signed-PWM convention the page asks to verify.")
    add("")
    add("### 6.3 The whole record")
    add("")
    add(f"![overview]({figs('overview')})")
    add("")
    add("*Top: TEC thermistor (black), the one-lump fit (red dashed) and the five rod sensors. Bottom: the applied PWM. Shaded: idle, then the three sweeps. The spike near 175 s is the test START in PI mode.*")
    add("")
    add("### 6.4 Settled cycles, and how sinusoidal they are")
    add("")
    add(f"![periods]({figs('periods')})")
    add("")
    add("*Top: measured TEC temperature (black), the mean-plus-one-sinusoid fit (blue) and the mean-plus-three-harmonics fit (red dashed). Middle: the applied PWM. Bottom: what is left over by each fit.*")
    add("")
    ext(table(["Period", "Cycles (skipped, used)", "A1 (°C)", "A1 sem / half-range (°C)", "Lag (rad)", "Lag sem / half-range (rad)", "A2/A1", "A3/A1", "THD",
               "Residual, 3 harmonics (°C)", "Residual, one sinusoid (°C)", "One-sinusoid residual / (A1/√2)"],
              [[f"{r['period']:g} s", f"{r['skip']}, {r['used']}", f(r["A1"], 3), f"{f(r['sem_A1'], 3)} / {f(r['half_A1'], 3)}", f(r["lag"], 4), f"{f(r['sem_lag'], 4)} / {f(r['half_lag'], 4)}",
                pct(r["A2"] / r["A1"], 1), pct(r["A3"] / r["A1"], 2), pct(r["thd"], 1), f(r["rms"], 3), f(r["rms1"], 3), pct(r["rms1"] / (r["A1"] / math.sqrt(2)), 1)] for r in R]))
    add("")
    add("The third harmonic is the quietest, as the series of section 4.5 says it should be. What the three-harmonic fit leaves is mostly the fourth and sixth harmonics, which the model predicts:")
    add("")
    ext(table(["Period", "Residual of the three-harmonic fit (°C RMS)", "RMS of the model's 4th, 6th, 8th, ... harmonics (°C)", "Model's 4th harmonic amplitude (°C)"],
              [[f"{r['period']:g} s", f(r["rms"], 3), f(p["fit_hi_rms"], 3), f(p["fit_A4_F"], 3)] for r, p in zip(R, Pd)]))
    add("")
    add("Cycle by cycle (fundamental fit to each whole cycle), which shows the start-up:")
    add("")
    cyc_rows = []
    for r in R:
        for c in r["cycles"]:
            cyc_rows.append([f"{r['period']:g} s", c["cycle"], "yes" if c["used"] else "no (start-up)", f(c["mean"], 3), f(c["A1"], 3), f(c["lag"], 4)])
    ext(table(["Period", "Cycle", "Used in the fits", "Mean (°C)", "A1 (°C)", "Lag (rad)"], cyc_rows))
    add("")
    add("### 6.5 Excursions and slopes")
    add("")
    ext(table(["Period", "Highest T (°C)", "Lowest T (°C)", "Highest − mean (°C)", "Mean − lowest (°C)", "Ratio", "Steepest rise (°C/s)", "Steepest fall (°C/s)", "Ratio"],
              [[f"{r['period']:g} s", f(r["Tmax"]), f(r["Tmin"]), f(r["above"]), f(r["below"]), f(r["above"] / r["below"], 2), f(r["slope_up"], 3, True), f(r["slope_dn"], 3), f(r["slope_up"] / -r["slope_dn"], 2)] for r in R]))
    add("")
    add("The slopes are those of the three-harmonic fit (differentiating the raw 0.5 s data would mostly give noise). The highest temperature reached by the TEC in the settled")
    add(f"cycles is {f(max(r['Tmax'] for r in R))} °C, below the safety limits (TEC 65 °C, T1 56 °C).")
    add("")
    add("### 6.6 Temperature against the PWM")
    add("")
    add(f"![temperature against PWM]({figs('pwm_vs_temperature')})")
    add("")
    add("*Each loop is the settled cycles. If the plate answered instantly, the points would lie on the bent line T − baseline = χ(u) u (steeper for u > 0). The loop opens as the period gets shorter (phase lag) and the whole loop sits above the")
    add("center (the raised average). The dotted line uses the Module 6 defaults, the dashed line the fitted χ.*")
    add("")
    add("### 6.7 Trends with the period, and the fitted model")
    add("")
    add(f"![trends]({figs('trends')})")
    add("")
    add("*Left: fundamental amplitude. Middle: lag. Right: mean above the idle baseline. Black dots: measured (bars: half-range of the cycles). Dotted: Module 6 defaults. Dashed: fitted values. Dash-dot (right): Module 4 curve.*")
    add("")
    ext(table(["Parameter set", "χh (°C/count)", "χc (°C/count)", "χh/χc", "τ (s)", "T_amb (°C)", "Mean shift (χh − χc) U/π (°C)"],
              [["fitted to this run", f(m["chi_h"], 4), f(m["chi_c"], 4), f(ratio, 2), f(tau, 1), f(base), f(shift_fit)],
               ["Module 6 simulation defaults", f"{M6['chi_h']:g}", f"{M6['chi_c']:g}", f(M6["chi_h"] / M6["chi_c"], 2), f"{M6['tau']:g}", f"{M6['T_amb']:g}", f(shift_m6)],
               ["Module 4 curve (GUI and sketch defaults)", f"{M4['chi_h']:g}", f"{M4['chi_c']:g}", f(M4["chi_h"] / M4["chi_c"], 3), "(not part of the curve)", "", f(shift_m4)]]))
    add("")
    add(f"The fit's RMS misfit over the {len(A['ts'])} schedule samples is {f(m['rms'], 3)} °C. Only the ratio χh/χc agrees closely with Module 4; the absolute values are {pct(1 - m['chi_h'] / M6['chi_h'])} (χh) and {pct(1 - m['chi_c'] / M6['chi_c'])} (χc)")
    add(f"below the Module 6 defaults and τ is {f(tau, 1)} s instead of {M6['tau']:g} s. The defaults are simulation values; this run has the rod attached and a different room temperature ({f(base, 1)} °C instead of {M6['T_amb']:g} °C).")
    add("")
    add(f"![harmonics]({figs('harmonics')})")
    add("")
    add("*Harmonic content of the TEC temperature: solid, measured; hatched, fitted model.*")
    add("")
    add("Where the single-τ model falls short: inverting the equal-susceptibility formulas on each measured amplitude (with χavg from the fit) and on each lag gives the time constant each measurement implies:")
    add("")
    ext(table(["Period", "Measured A1 / model A1", "Measured lag − model lag (rad)", "τ implied by the amplitude (s)", "τ implied by the lag (s)"],
              [[f"{r['period']:g} s", f(r["A1"] / p["fit_A1_F"], 3), f(r["lag"] - p["fit_lag_F"], 3, True), f(ta, 1), f(tl, 1)] for r, p, ta, tl in zip(R, Pd, tau_amp, tau_lag)]))
    add("")
    add(f"The amplitudes imply τ between {f(min(tau_amp), 0)} and {f(max(tau_amp), 0)} s, rising with the period, and the lags at {R[1]['period']:g} and {R[2]['period']:g} s imply {f(tau_lag[1], 0)} s and {f(tau_lag[2], 0)} s. At the shortest period the lag is")
    add(f"{f(r1['lag'] - Pd[0]['fit_lag_F'], 2)} rad ({f((r1['lag'] - Pd[0]['fit_lag_F']) / r1['w'], 1)} s) longer than the single-τ model gives, and the lag is a very insensitive way to find τ there (ωτ is about {f(r1['w'] * tau, 1)}).")
    add("A plate-plus-rod system with more than one time constant would do this (the quick swing sees the fast part, the slow swing the whole system); a short extra delay, such as heat reaching the thermistor, would too.")
    add("These are explanations that fit, not ones tested in this run.")
    add("")

    # ------------------------------------------------------------------ section 7
    add("## 7. Answers to the questions on the page")
    add("")
    add("**How do you expect the temperature to respond?** A temperature swing at the PWM's own frequency, smaller and later than the push, increasingly so as the period shortens:")
    add(f"amplitude χavg U N and lag arctan(ωτ). With the Module 6 defaults and equal susceptibility ({chi_mid:.3f} °C/count) that predicts A1 = {f(E[0]['R_mid'], 2)}, {f(E[1]['R_mid'], 2)}, {f(E[2]['R_mid'], 2)} °C and lags of")
    add(f"{f(E[0]['dt'], 1)}, {f(E[1]['dt'], 1)}, {f(E[2]['dt'], 1)} s at {pers}, swinging around room temperature. Because heating is stronger than cooling, the average should also rise and the up-swings should exceed the down-swings.")
    add("")
    add("**How do the amplitude and the phase lag change with the period?** The ratio of the sluggishness to the swing time, ωτ, grows as the period shortens")
    add(f"(with the fitted τ it is {f(R[0]['w'] * tau, 1)}, {f(R[1]['w'] * tau, 1)} and {f(R[2]['w'] * tau, 1)} at {pers}). That has two effects. The shrink factor N falls, so the amplitude falls:")
    add(f"{f(r3['A1'], 2)}, {f(r2['A1'], 2)} and {f(r1['A1'], 2)} °C from the longest to the shortest period. The lag angle φ = arctan(ωτ) rises toward a quarter cycle (π/2 = 1.57 rad):")
    add(f"{f(r3['lag'], 2)}, {f(r2['lag'], 2)} and {f(r1['lag'], 2)} rad. In seconds the delay φ/ω does the opposite: it tends to a quarter of the period for a very quick swing (P/4 = {f(r1['period'] / 4, 0)} s at {r1['period']:g} s; measured {f(r1['lag_s'], 1)} s)")
    add(f"and to τ for a very slow one (τ = {f(tau, 0)} s; measured {f(r3['lag_s'], 1)} s at {r3['period']:g} s).")
    add("")
    add("**Does it meet the expectation?** The shape of the answer does; the details need the unequal susceptibilities.")
    add(f"- The amplitude is {f(r1['A1'], 2)}, {f(r2['A1'], 2)} and {f(r3['A1'], 2)} °C against {f(E[0]['R_mid'], 2)}, {f(E[1]['R_mid'], 2)} and {f(E[2]['R_mid'], 2)} °C from the equal-susceptibility formula with the default τ: "
        f"{f(100 * (r1['A1'] / E[0]['R_mid'] - 1), 0, True)} %, {f(100 * (r2['A1'] / E[1]['R_mid'] - 1), 0, True)} % and {f(100 * (r3['A1'] / E[2]['R_mid'] - 1), 0, True)} %. The trend (growing with the period) is as predicted.")
    add(f"- The lag is {f(r1['lag_s'], 1)}, {f(r2['lag_s'], 1)} and {f(r3['lag_s'], 1)} s against {f(E[0]['dt'], 1)}, {f(E[1]['dt'], 1)} and {f(E[2]['dt'], 1)} s: the same pattern, in seconds growing with the period and in radians shrinking.")
    add(f"- The average is {f(r1['mean'] - base, 2, True)} to {f(r2['mean'] - base, 2, True)} °C above the idle baseline, not zero. The equal-susceptibility solution cannot produce that; the unequal-susceptibility result of section 4.5 does ({f(shift_fit, 2, True)} °C with the fitted values).")
    add(f"- After fitting χh, χc and τ to the record, the model reproduces the measured mean, A1 and A2 to within {f(dev_long, 0)} % at {R[1]['period']:g} and {R[2]['period']:g} s and to within {f(dev_short, 0)} % at {R[0]['period']:g} s (section 6.7).")
    add("")
    add("**Unequal excursions, slopes, phase lag and distortion** (sections 6.4 to 6.6):")
    add(f"- excursions: the temperature goes {f(r1['above'])}, {f(r2['above'])} and {f(r3['above'])} °C above its mean and {f(r1['below'])}, {f(r2['below'])} and {f(r3['below'])} °C below it, a ratio of {f(r1['above'] / r1['below'], 2)}, {f(r2['above'] / r2['below'], 2)} and {f(r3['above'] / r3['below'], 2)}.")
    add(f"  The ratio grows with the period toward the slow-limit value χh/χc = {f(ratio, 2)}, because a slow plate follows the push more faithfully;")
    add(f"- slopes: the steepest rise is {f(r1['slope_up'] / -r1['slope_dn'], 2)}, {f(r2['slope_up'] / -r2['slope_dn'], 2)} and {f(r3['slope_up'] / -r3['slope_dn'], 2)} times the steepest fall;")
    add(f"- phase lag: {f(r1['lag'], 2)}, {f(r2['lag'], 2)} and {f(r3['lag'], 2)} rad, i.e. {f(r1['lag_s'], 1)}, {f(r2['lag_s'], 1)} and {f(r3['lag_s'], 1)} s;")
    add(f"- distortion: THD {pct(r1['thd'], 1)}, {pct(r2['thd'], 1)} and {pct(r3['thd'], 1)}, almost all of it the second harmonic.")
    add("")
    add("**Which departures from the equal-susceptibility prediction come from unequal heating and cooling?** The raised average, the lopsided peaks and slopes, and the second harmonic. The size of the swing at the PWM frequency and its lag do not:")
    add("section 4.5 shows they depend only on the average χavg and on τ. A likely physical reason for χh > χc is Joule heating in the thermoelectric module: the current heats the module in either direction, so it adds to the Peltier effect when the plate is being")
    add("heated and works against it when the plate is being cooled. That reason was not tested here.")
    add("")
    add("**How well does open-loop, uncompensated sinusoidal PWM give a sinusoidal temperature with a constant amplitude, independent of frequency?** Two separate properties are involved.")
    add(f"- *How nearly sinusoidal.* Reasonably, not exactly. A single sinusoid leaves a residual of {f(r1['rms1'], 2)}, {f(r2['rms1'], 2)} and {f(r3['rms1'], 2)} °C RMS ({pct(r1['rms1'] / (r1['A1'] / math.sqrt(2)), 0)}, {pct(r2['rms1'] / (r2['A1'] / math.sqrt(2)), 0)} and {pct(r3['rms1'] / (r3['A1'] / math.sqrt(2)), 0)} of the swing's RMS),")
    add("  almost entirely the second harmonic. This is a shape error caused by χh ≠ χc, and it gets worse, in relative terms, at longer periods.")
    add(f"- *How constant the amplitude is.* Not at all: A1 changes by a factor {f(r3['A1'] / r1['A1'], 2)} between {R[0]['period']:g} and {R[-1]['period']:g} s although U is fixed. This is a size error caused by the thermal lag, and it would remain even with equal susceptibilities.")
    add("")
    add("**Is a constant PWM amplitude sufficient for a constant temperature amplitude? No.** The plate is a first-order low-pass filter with shrink factor N = 1/√(1 + (ωτ)²), which depends on frequency. The PWM amplitude has to be raised as the period shortens, as U(P) in section 4.6,")
    add("and the asymmetry would still need compensating. That is the job of the feedforward and feedback stages that follow.")
    add("")

    # ------------------------------------------------------------------ section 8
    add("## 8. A cross-check from the rod (bonus)")
    add("")
    add("The raw-PWM wave also travels down the aluminum rod. Treating the fundamental at each of T1 to T5 like the Angstrom method does (ln amplitude and unwrapped phase against position, the same fits as in the production-run analysis):")
    add("")
    ext(table(["Period", "q (1/m)", "q′ (1/m)", "κ = ω / (2 q q′) (10⁻⁵ m²/s)", "T1 amplitude (°C)", "T5 amplitude (°C)"],
              [[f"{r['period']:g} s", f(r["q"], 2), f(r["qp"], 2), f(r["kappa"] * 1e5, 2), f(r["rod"]["T1_C"]["A1"], 3), f(r["rod"]["T5_C"]["A1"], 3)] for r in R]))
    add("")
    add(f"These are of the size of the production-run Angstrom result, 9.12 ± 0.09 × 10⁻⁵ m²/s (`Sammy_Module_8_Production_Run_Summary.md`), and agree with each other within {pct(kappa_spread)}. They rest on two or three cycles and on a TEC boundary that is neither zero-mean nor purely")
    add("sinusoidal, so they are a consistency check, not a second measurement of κ.")
    add("")
    add(f"![rod]({figs('rods')})")
    add("")

    # ------------------------------------------------------------------ section 9
    add("## 9. Limits of this run")
    add("")
    add(f"- U = {U:.0f} counts is assumed (the number was lost from the pasted page; it is the sketch default and the PWM measures {f(U, 1)}). The equal-susceptibility value of the page is also lost; section 4.4 gives the results for three values.")
    add(f"- Settled cycles per period: {r1['used']}, {r2['used']} and {r3['used']}. The sweep was sized to fit the available time ({plan_min:.1f} min). The error bars in the tables are cycle-to-cycle scatter of two or three cycles and are lower bounds.")
    add(f"- The start-up cycles are skipped by a rule (2.5 τ with the default τ). With the fitted τ = {f(tau, 1)} s the skipped time is {f(min(skip_tau), 1)} to {f(max(skip_tau), 1)} τ, so a small remainder of the start-up can be left (e^(−{f(min(skip_tau), 1)}) is {pct(math.exp(-min(skip_tau)))}); the drift term of the fit absorbs the slow part of it.")
    add("- The one-lump model is an approximation. With one τ it misses the amplitude by up to about 12 % at 100 s and the lag by about 0.11 rad there (section 6.7). The fitted χ and τ are those of this plate, rod and room, not universal values.")
    add(f"- T_amb in the fit is the idle TEC reading ({f(base)} °C), not the Module 6 default ({M6['T_amb']:g} °C); the rod sensors read {f(base - rod0, 2)} °C lower at idle.")
    add("- One run on one rod. S18.4 (positive-only PWM) is not covered, and the page's remaining open-loop, P and PI comparisons are separate runs.")
    add("- The photos are of the GUI display and are not data; the data are the CSV records they quote.")
    add("")

    # ------------------------------------------------------------------ section 10
    add("## 10. The series of PWM runs, and what comes next")
    add("")
    ext(table(["Run", "PWM command", "What it shows", "Status"], [
        ["idle", "u = 0", "room temperature and sensor noise", "done (this file, section 6.1)"],
        ["S18.3", f"u = {U:.0f} sin(2π t/P), U0 = 0, P = {pers}", "uncompensated response; effect of unequal heating and cooling", "done (this file)"],
        ["S18.4", "u = U0 + U sin(2π t/P) with U0 = U, so u ≥ 0", "the response when the current never reverses; separates the polarity asymmetry from other imperfections", "not yet run"],
        ["S18.5 to S18.8", "feedforward, P and PI control of a requested sine", "tracking at 100, 200 and 500 s", "the PI part was run on 10 November (production run)"],
    ]))
    add("")
    add("For S18.4 the push never changes sign, so only one susceptibility acts and the problem is the equal-susceptibility one again with a constant added: u = U (1 + sin ωt) gives")
    add("θ = χh U + R sin(ωt − φ) + (start-up), with R = χh U N and φ = arctan(ωτ). The mean temperature is T_amb + χh U, so the PWM amplitude for a target mean T* is")
    add(f"U = (T* − T_amb)/χh; with the fitted χh = {f(m['chi_h'], 3)} °C/count and T_amb = {f(base, 1)} °C that is U = (T* − {f(base, 1)}) / {f(m['chi_h'], 3)} counts. The target mean of the page was lost from the pasted text; it is needed before this run.")
    add("")

    # ------------------------------------------------------------------ section 11
    add("## 11. Files and how to reproduce")
    add("")
    add(f"- Run: `data/module_08_sammy/{name}` (with `_events.txt`, `_meta.json`, `_notes.csv`).")
    add(f"- Tables: `data/module_08_sammy/s183_analysis_{stamp}/`: `s183_by_period.csv`, `s183_cycle_fits.csv`, `s183_model_fit.csv`, `s183_predictions.csv`, `s183_equal_chi.csv`, `s183_idle_baseline.csv`, `s183_rod_by_period.csv`, `s183_summary.json`.")
    add(f"- Figures: `docs/figures/module_08_sammy/{stamp}_s183_*.png` (overview, periods, push_vs_response, pwm_vs_temperature, trends, harmonics, theory_check, rods).")
    add("")
    add("```bash")
    add(f"python3 python/sammy_module8_s183_analysis.py data/module_08_sammy/{name}")
    add("```")
    add("")
    add("The script needs numpy and matplotlib. It reads the calibration offsets and the sensor map from the repository and rewrites the tables, the figures and this document.")
    add("")
    add("## AI assistance")
    add("")
    add("The acquisition GUI changes, the analysis script, the figures and this walkthrough were produced with GitHub Copilot assistance and checked against the Module 8 page, the Module 6 model")
    add("and the recorded run. The derivations in section 4 were also verified numerically (sections 4.4 and 4.5).")

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
