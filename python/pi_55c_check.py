#!/usr/bin/env python3
"""
Phys 39 A3 Question 4. Naidu / Cohen

PI control to a 55 C setpoint, windup, and resetting the integral, in the
course simulator's two-lump model with the shared parameter set of Part II.

    python3 python/pi_55c_check.py      (run from the repository root)

Uses advance_model() from python/Lab_6_7_modeling_tec.py unchanged, through
python/simulate_goldilocks_two_lump.py (shared_config: chi_c 0.181, chi_h
0.501 C/PWM, tau 62.9 s, 12.0 V, 1.50 ohm, T_amb 21.54 C, G 3.5 W/K,
C_T/C 0.35, PWM limit 255).

Cases
  1. 55 C from room temperature at the chosen gains (Kp 12, Ki 0.2), with
     and without anti-windup.
  2. The same at Run 6's gains (Kp 12, Ki 20), to compare with the 60 C
     software limit.
  3. At 30 C and steady state with Kp 12, Ki 0.2, the integral is set to
     zero (the GUI's Zero integral) and the response is followed.
"""

import importlib.util
import os
import sys
from dataclasses import replace

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "goldilocks_two_lump", os.path.join(HERE, "simulate_goldilocks_two_lump.py"))
two = importlib.util.module_from_spec(_spec)
sys.modules["goldilocks_two_lump"] = two
_spec.loader.exec_module(two)
sim = two.sim

LIMIT_C = 60.0          # the Arduino's software temperature limit


def run(cfg, duration, reset_at=None):
    st = sim.ModelState(0.0, cfg.initial_c, cfg.initial_c, 0.0)
    rows = []
    while st.time_s < duration:
        if reset_at is not None and abs(st.time_s - reset_at) < cfg.dt_s / 2:
            st.integral_error_c_s = 0.0
        r = sim.advance_model(st, cfg, "two_lump", "pi")
        rows.append((r.time_s, r.measured_temperature_c, r.applied_pwm,
                     r.p_pwm, r.i_pwm, bool(r.saturated)))
    return rows


def main():
    base = two.shared_config()
    need = (55.0 - base.ambient_c) / sim.heating_susceptibility(base)
    print(f"Steady command needed at 55 C: (55 - {base.ambient_c}) / "
          f"{sim.heating_susceptibility(base):.4f} = {need:.1f} PWM counts")
    print(f"P only at Kp 12: droop (55 - {base.ambient_c}) / (1 + "
          f"{12 * sim.heating_susceptibility(base):.3f}) = "
          f"{(55 - base.ambient_c) / (1 + 12 * sim.heating_susceptibility(base)):.2f} C")

    print("\n55 C from 21.54 C, 900 s")
    for kp, ki in ((12.0, 0.2), (12.0, 20.0)):
        for aw in (False, True):
            cfg = replace(base, initial_c=base.ambient_c, setpoint_c=55.0,
                          kp_pwm_per_c=kp, ki_pwm_per_c_s=ki, anti_windup=aw)
            rows = run(cfg, 900.0)
            peak = max(rows, key=lambda r: r[1])
            sat = sum(cfg.dt_s for r in rows if r[5])
            final = sum(r[1] for r in rows[-600:]) / 600
            u_end = sum(r[2] for r in rows[-600:]) / 600
            ui_end = sum(r[4] for r in rows[-600:]) / 600
            first_over = next((r[0] for r in rows if r[1] > LIMIT_C), None)
            print(f"  Kp {kp:g} Ki {ki:g} anti-windup {'on ' if aw else 'off'}: "
                  f"peak {peak[1]:.2f} C at {peak[0]:.0f} s, saturated "
                  f"{sat:.1f} s, mean of last 30 s {final:.2f} C, u {u_end:.1f}, "
                  f"u_I {ui_end:.1f}, above {LIMIT_C:g} C "
                  f"{'from ' + format(first_over, '.0f') + ' s' if first_over else 'never'}")

    print("\nZero integral at steady state, 30 C, Kp 12, Ki 0.2")
    cfg = replace(base, initial_c=29.97, setpoint_c=30.0, kp_pwm_per_c=12.0,
                  ki_pwm_per_c_s=0.2, anti_windup=True)
    rows = run(cfg, 1000.0, reset_at=400.0)
    before = [r for r in rows if r[0] < 400.0][-1]
    after = [r for r in rows if r[0] >= 400.0]
    low = min(after, key=lambda r: r[1])
    back = next((r[0] for r in after if r[0] > low[0] and abs(r[1] - 30.0) < 0.02),
                None)
    print(f"  just before: T {before[1]:.3f} C, u {before[2]:.1f} = u_P "
          f"{before[3]:.2f} + u_I {before[4]:.2f}")
    print(f"  just after:  u {after[1][2]:.2f}")
    print(f"  lowest T {low[1]:.2f} C, {low[0] - 400:.0f} s after the reset; "
          f"back within 0.02 C {back - 400:.0f} s after")


if __name__ == "__main__":
    main()
