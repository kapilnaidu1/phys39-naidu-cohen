# Module 8, Part I: Angstrom method

Naidu / Cohen. Course page: Module 8, Part I (S18 to S22), as updated on
2 November (GUI only, no serial logger; open loop, P and PI compared). Data
in `data/module_08/`, figures in `docs/figures/module_08/`.

## 1. Acquisition

| Part | File |
|---|---|
| Arduino | `arduino/module_08/angstrom_tec/angstrom_tec.ino` |
| GUI | `python/angstrom_gui.py` |
| Check a saved file without the GUI | `python3 python/angstrom_gui.py --check-file <file>` |

The Arduino computes the setpoint T_set = Ta + Tb sin(phase) and the TEC
command in the selected mode, and prints one record every 500 ms. The GUI
sends settings and START / STOP, displays everything and saves every valid
record unchanged.

```text
time_ms,run_state,control_mode,step,Ta_C,Tb_C,period_s,setpoint_C,feedforward_pwm,TEC_C,T1_C,T2_C,T3_C,T4_C,T5_C,controller_pwm,heating_to_cooling_ratio,signed_pwm
```

| Field | Meaning |
|---|---|
| run_state | 0 idle (output off), 1 running, 9 safety latched |
| control_mode | OL, P or PI |
| step | schedule step, 0 for a run started from the GUI |
| setpoint_C | requested TEC temperature; `nan` while idle |
| feedforward_pwm | OL command; `nan` in P and PI (does not apply) |
| controller_pwm | raw P or PI command before the cooling multiplier and clamp; `nan` in OL |
| signed_pwm | applied PWM, + heats, − cools |
| temperatures | raw beta-equation values, °C; `nan` if unreadable. Offsets only in analysis |

Lines starting with `#` are the boot banner, settings and events. Each boot
prints `# BOOT n` (EEPROM counter). Every setting change is an `# EVENT` line
and is also saved in `_events.txt` with the wall-clock time.

**Control modes.**

- **OL**: u_ff = f⁻¹(T_set − T_room), piecewise-linear inverse of the
  Module 4 steady-state curve (`data/module_04/steady_state.csv`, signed
  PWM against T − T0, heating and cooling branches). No feedback, no extra
  multiplier (the two branches already differ). The curve was measured
  without the rod, so the rod's extra heat loss is expected to pull the OL
  temperatures below the setpoint.
- **P**: u = Kp e, e = T_set − T_TEC.
- **PI**: u = Kp e + Ki ∫e dt, conditional integration as in Module 6.
- P and PI: a negative command is multiplied by r = χ_h/χ_c before the clamp.
  r = 0.50127/0.18091 = **2.771** (Module 4).

**Safety.** Latch at 56 °C on T1 (the course's rod-base limit), 65 °C on the
TEC thermistor (below the 70 °C switch and the TEC's 80 °C rating), or after
5 unusable TEC readings. Setpoints must stay within 10 to 56 °C. Output is 0
until START.

Check on the Module 6 one-lump plate model (no rod), PI Kp 12, Ki 0.2,
r 2.771, Ta 40, Tb 8, 100 s: amplitude 6.8 °C, lag 0.55 rad, no saturation.
Only a sanity check of the gains; the rod adds load and lag.

## 2. S18 run order

1. Sensors: T1 to T5 = R1 to R5 on A1 to A5, at 0, 25.4, 50.8, 76.2 and
   101.6 mm (±1 mm) from the first hole, T1 lowest. Calibration offsets:
   `calibration_rod_run_20261026_112627.csv`. Photo and caliper diameter.
2. Upload the sketch, close the Arduino IDE, `python3 python/angstrom_gui.py`.
3. Measure room temperature; enter it as "room T" and in a note.
4. Same drive for all three modes: Ta 40, Tb 16, period 100 s.
   OL → STOP → P → STOP → PI. Let each settle and keep at least 5 settled
   cycles. Never a period below 100 s; T1 must stay below 56 °C.
5. If no mode gives a good sinusoidal T1: 150 s, or Tb 10; retune Kp, Ki.
6. Second period chosen from the observed attenuation and phase; at least
   5 settled cycles.
7. STOP, close the GUI, keep the file unchanged.

## 3. P3: predictions and pilot plan

**Qualitative.** Every sensor oscillates at the drive period. Farther from
T1 the oscillation is smaller (amplitude e^(−qx)) and later (phase lag q′x).
The mean also falls along the rod, with the Module 7 decay length. A shorter
period gives more attenuation and more phase lag per metre.

**Numbers, planning only.** κ from handbook values for 6061-T6 (k = 167
W/(m K), ρ = 2700 kg/m³, c = 896 J/(kg K)): κ = 6.9 × 10⁻⁵ m²/s. ν = κm² with
our Module 7 m = 4.12 m⁻¹: ν = 1.2 × 10⁻³ s⁻¹. Semi-infinite rod, T5 at
4 in (101.6 mm):

| Period (s) | q (1/m) | q′ (1/m) | 1/q (in) | B5/B1 | phase lag T1 → T5 (rad) |
|---|---|---|---|---|---|
| 100 | 21.5 | 21.1 | 1.8 | 0.11 | 2.2 |
| 150 | 17.7 | 17.2 | 2.2 | 0.17 | 1.8 |
| 240 | 14.1 | 13.5 | 2.8 | 0.24 | 1.4 |
| 300 | 12.7 | 12.0 | 3.1 | 0.28 | 1.2 |
| 480 | 10.2 | 9.3 | 3.9 | 0.36 | 0.95 |

The course target is B5 ≈ B1/e = 0.37 at the primary period, with 0.5 to
2 rad of lag. With the sensors 1 in apart that is a period of roughly 450 to
520 s; at 100 s the 1/e point is only 1.8 in from T1. These come from a
handbook κ, so the pilot run decides.

**Pilot settings.** Ta 40 °C, Tb 16 °C (24 to 56 °C), 100 s, Kp 12, Ki 0.2,
r 2.771, records every 0.5 s (200 per period). Settling test: fit groups of
complete cycles; settled when each sensor's B and φ agree between
consecutive groups within their uncertainties and the residuals show no
drift.
