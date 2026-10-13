#!/usr/bin/env python3
"""
Phys 39 Module 6 Part II pre-class. Naidu / Cohen

Lienhard, A Heat Transfer Textbook, Problem 1.8: a copper sphere, 2.5 cm in
diameter, starts uniformly at 40 C and cools in a slow air stream at 0 C with
h = 15 W/m^2 K. Radiation neglected. Lumped capacity, eqns (1.20) to (1.22).

    python3 python/lienhard_problem_1_8.py      (run from the repository root)

Copper properties at 20 C from Lienhard Table A.1 (pure copper):
rho = 8954 kg/m^3, c_p = 384 J/kg K, k = 398 W/m K.

OUTPUT  docs/figures/module_06/part2/problem_1_8.png and the numbers on screen.
"""

import math
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

D = 0.025            # m
H_CONV = 15.0        # W/m^2 K
T_I, T_INF = 40.0, 0.0
RHO, CP, K = 8954.0, 384.0, 398.0
OUT = "docs/figures/module_06/part2/problem_1_8.png"


def main():
    r = D / 2
    V = 4.0 / 3.0 * math.pi * r ** 3
    A = math.pi * D ** 2
    m = RHO * V
    C = m * CP                    # J/K, the lump's heat capacity
    hA = H_CONV * A               # W/K, conductance to the air
    tau = C / hA                  # s
    bi_va = H_CONV * (V / A) / K  # L = V/A = D/6
    bi_r = H_CONV * r / K         # L = r, the larger common choice

    print(f"V = {V:.4e} m^3, A = {A:.4e} m^2, V/A = D/6 = {V / A * 1e3:.3f} mm")
    print(f"m = {m * 1e3:.2f} g, C = m c_p = {C:.2f} J/K, hA = {hA:.5f} W/K")
    print(f"tau = rho c_p V / (h A) = rho c_p D / (6 h) = {tau:.0f} s "
          f"= {tau / 60:.1f} min")
    print(f"Bi = h L / k: {bi_va:.2e} with L = V/A, {bi_r:.2e} with L = r")
    for T_end in (1.0, 0.1):
        t = tau * math.log((T_I - T_INF) / (T_end - T_INF))
        print(f"reaches {T_end:g} C at t = {t:.0f} s = {t / 60:.1f} min")

    t = np.linspace(0, 6 * tau, 600)
    T = T_INF + (T_I - T_INF) * np.exp(-t / tau)

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.edgecolor": "#868686", "axes.linewidth": 0.8,
                         "xtick.color": "#595959", "ytick.color": "#595959"})
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.grid(True, color="#D9D9D9", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.plot(t / 60, T, color="#1F4E79", linewidth=1.8)
    ax.axhline(T_INF + (T_I - T_INF) / math.e, color="#868686",
               linewidth=0.9, linestyle=":")
    ax.axvline(tau / 60, color="#868686", linewidth=0.9, linestyle=":")
    ax.text(tau / 60 + 1.5, 16.5, f"t = τ = {tau / 60:.1f} min,  "
            f"T = 40/e = {40 / math.e:.1f} °C", color="#404040",
            fontsize=9.5)
    ax.set_xlim(0, 6 * tau / 60)
    ax.set_ylim(0, 41)
    ax.set_xlabel("Time  (min)", color="#404040")
    ax.set_ylabel("Sphere temperature  (°C)", color="#404040")
    ax.set_title("Lienhard 1.8: copper sphere, D = 2.5 cm, h = 15 W/m²K, "
                 "air at 0 °C", fontsize=11, color="#404040")
    fig.text(0.01, 0.01,
             f"T(t) = 40 e^(−t/τ) °C,  τ = ρcₚD/(6h) "
             f"= {tau:.0f} s.  Bi = hL/k = {bi_va:.1e} (L = D/6), so the "
             "lumped model holds.\nCopper properties at 20 °C, Lienhard "
             "Table A.1.", fontsize=7.6, color="#595959")
    fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.2)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=200, facecolor="white")
    print(f"Figure written to {OUT}")


if __name__ == "__main__":
    main()
