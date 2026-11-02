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

## 4. S18 live run, 2 November (`angstrom_live_20261102_094506.csv`)

Photos: `docs/figures/module_08/setup_rod_sensors_20261102.jpg` (rod, T1 in
the lowest hole at the foam surface, +x up the rod) and
`setup_bench_wiring_20261102.jpg`. Channel labels still to be marked on a copy.

Room temperature 22.53 °C: mean of T1 to T5 with offsets, control off, rod
unheated, 09:47 (note in the run). Pump switched on about 09:50; the TEC
channel jumped about 2 °C for a few seconds at switch-on, then steady.

| Arduino time (s) | Event |
|---|---|
| 405.5 | START, open loop (OL), Ta 40, Tb 16, period 100 s |
| 1079.2 | mode P, Kp 12 (no stop, phase continuous) |
| 1591.4 | mode PI, Kp 12, Ki 0.2 |
| 2626.8 | period 480 s (mode PI re-sent, integral reset) |
| 5832.4 | STOP, end of the S18 run (11:22) |

Two command bursts overflowed the Uno's 64-byte input buffer (the last
setting and the following command were lost or garbled, then refused). No
setting took a wrong value; the GUI now sends commands 0.3 s apart.

**Open loop vs P vs PI at 100 s** (last 3 cycles of each,
`angstrom_compare_angstrom_live_20261102_094506_100s.txt`):

| Mode | TEC mean | TEC B / Tb | TEC lag (rad) | T1 B (°C) | T1 lag (rad) | PWM range |
|---|---|---|---|---|---|---|
| OL | 39.02 | 0.234 | 1.42 | 0.70 | 2.33 | 3 to 67 |
| P | 37.37 | 0.764 | 0.55 | 2.46 | 1.43 | −195 to 134 |
| PI | 39.94 | 0.868 | 0.62 | 2.88 | 1.50 | −216 to 156 |

Open loop follows the Module 4 steady-state curve but the plate's ~63 s time
constant filters a 100 s drive heavily, and it never cools actively (the
whole setpoint is above room). P tracks with a 2.6 °C droop in the mean. PI
removes the droop and gives the largest T1 swing; no saturation in any mode.
Heating and cooling halves are symmetric within 0.2 °C at TEC and T1, and
the 2nd harmonic is under 2.5 % of the fundamental.

**PI, 100 s, last 5 cycles (2125.9 to 2625.9 s)**
(`angstrom_fit_angstrom_live_20261102_094506_PI_100s.*`). Settling test:
cycle by cycle, B of every sensor within about 3 % (T5 0.426 to 0.440 °C) and φ within 0.06 rad.

| | x (mm) | B (°C) | B/B1 | lag after T1 (rad) |
|---|---|---|---|---|
| T1 | 0 | 2.874 | 1.000 | 0 |
| T2 | 25.4 | 1.899 | 0.661 | 0.38 |
| T3 | 50.8 | 1.137 | 0.396 | 0.88 |
| T4 | 76.2 | 0.697 | 0.243 | 1.32 |
| T5 | 101.6 | 0.430 | 0.149 | 1.79 |

q = 18.5 ± 0.3 m⁻¹, q′ = 17.4 ± 0.3 m⁻¹ (χ²/dof 3.3 and 4.7, errors scaled),
κ = ω/(2qq′) = (9.8 ± 0.2) × 10⁻⁵ m²/s, ν = (4.0 ± 1.5) × 10⁻³ s⁻¹.

Pilot only. κ is about 40 % above the handbook value for 6061-T6
(6.9 × 10⁻⁵ m²/s), and the straight lines miss by more than the point
errors, so something is not yet in the error budget: per-sensor lag from the
taped contacts, positions, or the semi-infinite assumption. The 480 s run
gives an independent κ; agreement or not between the two periods is the
first test.

**PI, 480 s, cycles 2 to 6 (3107.2 to 5507.2 s)**
(`angstrom_fit_angstrom_live_20261102_094506_PI_480s.*`). Cycle 1 after the
switch is excluded: the TEC swing was 15.30 °C in cycle 1 and 15.83 to
15.87 °C in cycles 2 to 6. From cycle 2 on, every phase stays within
0.04 rad; the rod swings vary by up to ±3 % from cycle to cycle with no
trend (T5 2.41 to 2.51 °C). The run was stopped at 6.7 cycles, so the
five retained cycles start with the first settled one; a stricter count
(cycles 3 to 6) has four. The means still rise 0.2 to 0.34 °C per cycle
(handled by the drift term).

| | x (mm) | B (°C) | B/B1 | lag after T1 (rad) |
|---|---|---|---|---|
| T1 | 0 | 6.368 | 1.000 | 0 |
| T2 | 25.4 | 5.176 | 0.813 | 0.17 |
| T3 | 50.8 | 4.023 | 0.632 | 0.39 |
| T4 | 76.2 | 3.140 | 0.493 | 0.59 |
| T5 | 101.6 | 2.453 | 0.385 | 0.81 |

TEC follows the setpoint at 99 % amplitude, 12 s behind; PWM −43 to 88.
B5/B1 = 0.385, the course's 1/e target for the primary period, and the
T1 → T5 lag of 0.81 rad is inside the 0.5 to 2 rad target. **480 s is the
primary period.**

q = 9.34 ± 0.18 m⁻¹, q′ = 7.84 ± 0.15 m⁻¹ (χ²/dof 2.3 and 3.2),
κ = (8.94 ± 0.24) × 10⁻⁵ m²/s, ν = (2.31 ± 0.37) × 10⁻³ s⁻¹.

**The two periods compared.**

| Period | q (1/m) | q′ (1/m) | κ (10⁻⁵ m²/s) | ν (10⁻³ 1/s) |
|---|---|---|---|---|
| 100 s | 18.5 ± 0.3 | 17.4 ± 0.3 | 9.76 ± 0.23 | 4.0 ± 1.5 |
| 480 s | 9.34 ± 0.18 | 7.84 ± 0.15 | 8.94 ± 0.24 | 2.31 ± 0.37 |

κ differs by 0.82 × 10⁻⁵ m²/s, 2.5 times the combined error, and both lie
30 to 40 % above the handbook 6061-T6 value (6.9 × 10⁻⁵). Candidates to test
on Wednesday, before calling either number a result: the finite rod (at 480 s
1/q = 107 mm against 279 mm to the top, so the reflected wave is a few
percent at T5), different thermal lags of the taped sensors, and the
position uncertainty.
