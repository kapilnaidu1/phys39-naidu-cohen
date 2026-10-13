#!/usr/bin/env python3
"""
Phys 39 Module 6. Naidu / Cohen

Can sampling and command delay alone explain the Run 3 ringing?

    python3 python/sampling_delay_check.py      (run from the repository root)

Run 3 (P, Kp = 64, 13 October) overshot the 30 -> 35 C step by 1.69 C (35 %)
and rang with a 9 s period. The one-lump model with continuous control cannot
overshoot at all. This simulates the same one-lump plant (measured chi and
tau) under the controller as it actually runs: the temperature is read every
0.563 s, the command is rounded to whole counts, clipped to +/-255, and held
until the next reading. The delay between a reading and the command taking
effect is varied from 0 to one full sample.

No fitting. Plant: tau = 62.9 s, chi = 0.50127 C/count heating and 0.18091
cooling, T_amb = 21.5 C (from Run 1), starting at Run 3's measured 29.74 C.
"""

import numpy as np

TAU, CHI_H, CHI_C, T_AMB = 62.9, 0.50127, 0.18091, 21.5
DT = 0.563            # s, measured spacing of readings on 13 October
KP, T0, T_SET = 64.0, 29.74, 35.0
SUB = 50              # plant integration steps per sample


def simulate(delay_samples, t_end=80.0):
    n = int(t_end / DT)
    h = DT / SUB
    T = T0
    u_applied = round(KP * (30.0 - T0))      # the command holding 29.74 C
    pending, temps = [], []
    for k in range(n):
        tk = k * DT
        u = int(round(max(-255.0, min(255.0, KP * (T_SET - T)))))
        pending.append((tk + delay_samples * DT, u))
        for j in range(SUB):
            while pending and pending[0][0] <= tk + j * h + 1e-12:
                u_applied = pending.pop(0)[1]
            chi = CHI_H if u_applied >= 0 else CHI_C
            T += h / TAU * (T_AMB + chi * u_applied - T)
        temps.append(T)
    temps = np.array(temps)
    t = (np.arange(n) + 1) * DT
    T_f = temps[t > t_end - 20].mean()
    over = max(0.0, temps.max() - T_f)
    return T_f, over, 100.0 * over / (T_f - T0)


def main():
    print("One-lump plant, P control Kp = 64, step 30 -> 35 C, sampled at 0.563 s")
    print(f"{'delay':>14} {'final C':>8} {'overshoot C':>12} {'%':>5}")
    for d in (0.0, 0.25, 0.5, 1.0):
        T_f, over, pct = simulate(d)
        print(f"{d:5.2f} samples ({d * DT:4.2f} s) {T_f:8.2f} {over:12.2f} {pct:5.1f}")
    print("Measured, Run 3:                 34.59         1.69  34.8")


if __name__ == "__main__":
    main()
