#!/usr/bin/env python3
"""
Phys 39 Module 6 Part I, Part 4. Naidu / Cohen

The Part 4 open-loop exercises, run in the course simulator
(python/Lab_6_7_modeling_tec.py, one_lump, its own advance_model()).

    python3 python/open_loop_course_sim_check.py    (run from the repository root)

A. Guided exercise with the simulator defaults: T_amb 22 C, chi_c 0.23,
   chi_h 0.46 C/PWM (tau 80 s, 12 V, 1.50 ohm). Commands +25, -25, -50 PWM.
   Steady state predicted from T_ss = T_amb + chi*u, then simulated; chi
   recovered from the simulated T_ss.
B. Thermal mass: direct constants, C doubled with H, P_u,c and r unchanged,
   command +25. Steady temperature and 63 % time compared.
C. Our measured parameters (chi_c 0.181, chi_h 0.501 C/PWM, tau 62.9 s,
   T_amb 21.54 C, 12 V, 1.50 ohm) against one heating and one cooling
   open-loop step from Module 4 (data/module_04/full_run.csv): u = +25 and
   u = -32. Each simulation starts at the first measured sample of the step.
   Also repeated at dt = 0.01 s to show the result does not depend on dt.

OUTPUT  docs/figures/module_06/open_loop_course_sim.png
        data/module_06/open_loop_course_sim_check.txt
"""

import csv
import importlib.util
import io
import os
import sys
from contextlib import redirect_stdout
from dataclasses import replace

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("lab67", os.path.join(HERE, "Lab_6_7_modeling_tec.py"))
sim = importlib.util.module_from_spec(_spec)
sys.modules["lab67"] = sim
_spec.loader.exec_module(sim)

RAW = "data/module_04/full_run.csv"
FIG = "docs/figures/module_06/open_loop_course_sim.png"
TXT = "data/module_06/open_loop_course_sim_check.txt"


def measured_config(chi_c, chi_h, tau, t_amb):
    d = sim.constants_from_measurements(chi_c, chi_h, tau, 12.0, 1.50)
    return replace(sim.ModelConfig(), ambient_c=t_amb,
                   measured_cooling_chi_c_per_pwm=chi_c,
                   measured_heating_chi_c_per_pwm=chi_h, measured_tau_s=tau,
                   total_capacitance_j_per_c=d.total_capacitance_j_per_c,
                   heat_loss_w_per_c=d.heat_loss_w_per_c,
                   tec_power_w_per_pwm=d.cooling_power_w_per_pwm,
                   heating_to_cooling_ratio=d.heating_to_cooling_ratio)


def open_loop(cfg, u, T0, duration):
    cfg = replace(cfg, open_loop_pwm=float(u), initial_c=T0)
    st = sim.ModelState(0.0, T0, T0, 0.0)
    t, T = [0.0], [T0]
    while st.time_s < duration - 1e-9:
        r = sim.advance_model(st, cfg, "one_lump", "open_loop")
        t.append(r.time_s)
        T.append(r.tec_temperature_c)
    return np.array(t), np.array(T)


def t63(t, T, T_ss):
    target = T[0] + 0.632 * (T_ss - T[0])
    rising = T_ss > T[0]
    k = np.flatnonzero(T >= target if rising else T <= target)[0]
    return t[k]


def longest_block(u_target):
    rows = list(csv.DictReader(open(RAW, newline="")))
    t = np.array([float(r["time_s"]) for r in rows])
    T = np.array([float(r["temperature_C"]) for r in rows])
    u = np.array([int(float(r["pwm"])) * (1 if r["heat_cool"] == "1" else -1)
                  for r in rows])
    best, i = None, 0
    while i < len(u):
        j = i
        while j + 1 < len(u) and u[j + 1] == u[i]:
            j += 1
        if u[i] == u_target and (best is None or j - i > best[1] - best[0]):
            best = (i, j)
        i = j + 1
    a, b = best
    return t[a:b + 1] - t[a], T[a:b + 1]


def main():
    out = io.StringIO()
    with redirect_stdout(out):
        print("A. Guided exercise, simulator defaults")
        dflt = measured_config(0.23, 0.46, 80.0, 22.0)
        print(f"   derived: C {dflt.total_capacitance_j_per_c:.2f} J/K, H "
              f"{dflt.heat_loss_w_per_c:.4f} W/K, P_u,c "
              f"{dflt.tec_power_w_per_pwm:.4f} W/PWM, r "
              f"{dflt.heating_to_cooling_ratio:.2f}, tau "
              f"{dflt.total_capacitance_j_per_c / dflt.heat_loss_w_per_c:.1f} s")
        sims = {}
        for u, chi in ((25, 0.46), (-25, 0.23), (-50, 0.23)):
            pred = 22.0 + chi * u
            t, T = open_loop(dflt, u, 22.0, 1200.0)
            sims[u] = T[-1]
            print(f"   u {u:+4d}: predicted {pred:6.2f} C, simulated "
                  f"{T[-1]:6.2f} C, chi from it (T_ss - T_amb)/u = "
                  f"{(T[-1] - 22.0) / u:.4f}")
        print(f"   ratio chi_h/chi_c from the simulated values: "
              f"{((sims[25] - 22) / 25) / ((sims[-25] - 22) / -25):.3f}")

        print("\nB. Double C at fixed H, P_u,c, r (direct constants), u = +25")
        for scale in (1.0, 2.0):
            cfg = replace(dflt, total_capacitance_j_per_c=scale * dflt.total_capacitance_j_per_c)
            t, T = open_loop(cfg, 25, 22.0, 1600.0)
            print(f"   C x{scale:g}: steady {T[-1]:.2f} C, 63 % time "
                  f"{t63(t, T, T[-1]):.1f} s, C/H "
                  f"{cfg.total_capacitance_j_per_c / cfg.heat_loss_w_per_c:.1f} s")

        print("\nC. Measured parameters against Module 4 open-loop steps")
        ours = measured_config(0.181, 0.501, 62.9, 21.54)
        traces = {}
        for u in (25, -32):
            tm, Tm = longest_block(u)
            t, T = open_loop(ours, u, float(Tm[0]), float(tm[-1]))
            Ts = np.interp(tm, t, T)
            res = Ts - Tm
            t2, T2 = open_loop(replace(ours, dt_s=0.01), u, float(Tm[0]), float(tm[-1]))
            dt_shift = abs(T2[-1] - T[-1])
            traces[u] = (tm, Tm, t, T)
            print(f"   u {u:+4d}: {tm[-1]:.0f} s, start {Tm[0]:.2f} C, final "
                  f"measured {Tm[-1]:.2f} C, simulated {T[-1]:.2f} C, rms "
                  f"residual {np.sqrt(np.mean(res ** 2)):.3f} C, largest "
                  f"{res[np.argmax(np.abs(res))]:+.2f} C at "
                  f"{tm[np.argmax(np.abs(res))]:.0f} s; dt 0.05 -> 0.01 s "
                  f"changes the end by {dt_shift:.4f} C")
    text = out.getvalue()
    print(text)
    os.makedirs(os.path.dirname(TXT), exist_ok=True)
    open(TXT, "w").write("python3 python/open_loop_course_sim_check.py\n\n" + text)

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.edgecolor": "#868686"})
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
    for ax, u in zip(axes, (25, -32)):
        tm, Tm, t, T = traces[u]
        ax.grid(True, color="#D9D9D9")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.plot(tm, Tm, color="#9A9A9A", linewidth=2.2, label="Measured (Module 4)")
        ax.plot(t, T, color="#1F4E79", linewidth=1.2, label="Course simulator, one lump")
        ax.set_title(f"Open loop, u = {u:+d} PWM", color="#404040")
        ax.set_xlabel("Time from the command (s)")
        ax.set_ylabel("Temperature (°C)")
        ax.legend(loc="best", fontsize=9)
    fig.text(0.01, 0.01, "Measured χc 0.181, χh 0.501 °C/PWM, τ 62.9 s, T_amb "
             "21.54 °C, 12 V, 1.50 Ω; start at the first measured sample; "
             "Δt 0.05 s. Data: data/module_04/full_run.csv.",
             fontsize=8, color="#595959")
    fig.subplots_adjust(left=0.07, right=0.99, top=0.9, bottom=0.2, wspace=0.22)
    os.makedirs(os.path.dirname(FIG), exist_ok=True)
    fig.savefig(FIG, dpi=200, facecolor="white")
    print(f"Figure {FIG}, text {TXT}")


if __name__ == "__main__":
    main()
