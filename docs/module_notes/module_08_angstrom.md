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

Rod geometry (`data/module_08/rod_geometry.csv`): D = 12.757 ± 0.006 mm by
calipers at 3 places; T1 hole to rod top L = 281.9 mm (11.1 in) and overall
about 305 mm (12 in), ruler readings confirmed 2 November.

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
removes the droop and gives the largest T1 swing. No saturation in the
compared cycles; P hit the −255 clamp for 14 records (7 s) right after the
switch from OL, PI never did.
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
0.05 rad; the rod swings vary by up to ±3 % from cycle to cycle with no
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

## 5. Checks on the actuator and the model (S18 data)

```bash
python3 python/analysis/angstrom_actuator.py data/module_08/angstrom_live_20261102_094506.csv --tamb 22.53
```

**Open-loop feedforward.**
`docs/figures/module_08/angstrom_feedforward_angstrom_live_20261102_094506.png`.
The Module 4 points, the piecewise-linear inverse and every u_ff the run
sent. The requested T − T_room ran from 1.5 to 33.5 °C; the measured curve
only reaches +25.1 °C (PWM 50), so 36 % of the OL records used the
extrapolated end segment (2.00 PWM per °C) up to PWM 66.8. The whole OL
waveform was above room, so OL never cooled.

**Open loop against the one-lump model.** A first-order plate with
τ = 62.9 s (Module 6) driven at 100 s passes 1/√(1 + (ωτ)²) = 0.245 of the
amplitude with a lag of arctan(ωτ) = 1.32 rad. Measured at the TEC: 0.234
and 1.42 rad. The extra 0.1 rad and the slightly smaller swing are
consistent with the rod adding load and lag that the one-lump model leaves
out.

**Controller command against applied PWM** (P and PI).
`docs/figures/module_08/angstrom_actuator_angstrom_live_20261102_094506.png`.
Fitted slopes: heating 1.000, cooling 2.773 (P) and 2.771 (PI), equal to
r = 2.771, so the multiplier is applied as intended before the clamp. P
reached −255 for 14 records just after the switch from OL; PI stayed
between −217 and +156.

**Finite-length check for the retained sensors.** For an insulated tip the
periodic solution differs from the semi-infinite one by a reflected wave of
relative size about e^(−2q(L − x)), with L = 281.9 mm:

| Period | T1 | T2 | T3 | T4 | T5 |
|---|---|---|---|---|---|
| 100 s (q = 18.5) | 0.0000 | 0.0001 | 0.0002 | 0.0005 | 0.0013 |
| 480 s (q = 9.34) | 0.005 | 0.008 | 0.013 | 0.021 | 0.035 |

Negligible at 100 s; at 480 s up to 3.5 % at T5, which is the same size as
the scatter in B and can bias q and q′ there. **Transverse Biot number**
(Module 7): Bi_⊥ = 1.7 × 10⁻⁴, so one temperature per cross-section holds.

## 6. Frequency schedule (Stage 3, built 4 November)

The GUI's schedule box takes one step per line, `duration_s Ta_C Tb_C period_s`
(up to 8 steps). **Send schedule** sends `SCHED CLEAR`, one `SCHED ADD` per step
and `SCHED LIST`; **START schedule** sends `SCHED START`. The Arduino then runs
the steps on its own clock in the selected control mode, with the laptop still
recording:

- step 1 starts with phase 0; at every later step the phase keeps running, so
  a period change does not make the setpoint jump;
- every change prints `# EVENT t_ms=... SCHEDULE STEP k dur_s=... Ta=... Tb=... period_s=...`,
  and the record's `step` field shows the active step (`run_state` 2);
- after the last step the output goes to 0 (`# EVENT ... SCHEDULE DONE`); STOP
  ends a schedule early;
- periods below 100 s, setpoints outside 10 to 56 °C, durations outside 10 to
  36000 s and more than 8 steps are refused.

Presets: **Fast test** (200 s each at 100, 150 and 200 s periods: two automatic
changes in 10 min, the Stage 3 demonstration) and **Production** (7 cycles each
at 480, 240 and 100 s, about 96 min, the S20 plan).

Checked before the bench: the sketch compiled for the Uno and was run on the
host with a stub Arduino layer (3-step schedule): steps changed at 200 s
intervals, the setpoint stayed continuous across both changes (40.18 °C two
full cycles into step 1; 53.7 °C at the 100 to 150 s change, the expected
continuation of the phase), refused steps were rejected, and the output went
to 0 at the end. The analysis scripts accept `run_state` 1 or 2.

## 7. S19 bench record, 4 November

| File | What happened |
|---|---|
| `angstrom_live_20261104_091727` | Start-up with control off. T2 to T5 showed contact faults: one-reading spikes (T5 to 58 °C, T3 to 41 °C), short dropouts (nan) on T4 and T5, and T3 and T4 stuck 2.4 and 1.1 °C high. GUI closed to reseat wires. |
| `angstrom_live_20261104_092121` | After reseating: no faults except one T5 blip at 130 s (+1.3 °C for one reading, then 0.3 °C lower). Everything at about 27.3 °C and still cooling about 0.1 °C/min. Reset to push the wires further in (no pin changes). |
| `angstrom_live_20261104_092527` | Clean. Room temperature 27.10 °C (mean of T1 to T5 with offsets, sd 0.09 °C, 09:30, control off). Supply and pump on. Fast schedule test (Stage 3): 200 s each at 100, 150 and 200 s periods, PI Kp 12 Ki 0.2; steps changed at 200.0 s intervals with a continuous setpoint, output 0 at the end. Then (09:43:45): 300 s hold at 40 °C, 1680 s at 240 s, 1260 s at 180 s; `SCHEDULE DONE` at 10:37:45. |
| `angstrom_live_20261104_104451` | After the run, output off the whole time (run_state 0), 117 s. Rod still warm and cooling: T1 to T5 raw 29.3 to 29.9 °C at the start, 28.9 to 29.5 °C at the end. Ended with a serial read error at 10:46:51 when the USB was unplugged. Not used in any fit. |
| `angstrom_live_20261104_110306` | 300 s period. Sensors not moved. No new room-temperature baseline: the rod was still warm from the earlier run (T1 to T5 raw 28.2 to 28.7 °C and cooling slowly), so the room T box was set to the 09:30 value, 27.10 °C, and a note says so. Schedule started 11:07:53 (PI, Kp 12, Ki 0.2, r 2.771): 300 s hold at 40 °C, then 300 s period, Ta 40, Tb 16. Stopped by hand at 11:50:02 (t = 2816.6 s), after cycle 7 and part way into cycle 8, to finish within the session. No nan in the run. T5 glitch in cycle 5: it read up to 0.36 °C high for about 20 s and dropped back onto the normal curve at 1989.8 s (same phase in cycles 4 and 6 for comparison). |

The room was about 5 °C warmer than on 2 November (27.1 against 22.5 °C).
The first PI cycle after a cold start ran hot (TEC up to 5.5 °C above the
falling setpoint): the plate lags about 10 s and the integral built up
during the first rise. The production preset now starts with a 5 min hold
at Ta.

### Extra periods, 4 November (PI, Ta 40, Tb 16)

Fits: `angstrom_fit_angstrom_live_20261104_092527_PI_240s.*` (cycles 3 to 7 of
the 240 s step, 1877 to 3077 s) and `..._PI_180s.*` (cycles 3 to 7 of the
180 s step, 3437 to 4337 s); finite-rod comparison in
`angstrom_finite_angstrom_live_20261104_092527.txt`. 300 s:
`angstrom_fit_angstrom_live_20261104_110306_PI_300s.*` (cycles 2 to 7 of the
300 s step, 887.2 to 2687.2 s) and `angstrom_finite_angstrom_live_20261104_110306.txt`.

| Period | B5/B1 (A5 prediction) | lag T1 to T5, rad (prediction) | TEC B/Tb | κ semi-infinite | κ finite rod |
|---|---|---|---|---|---|
| 240 s | 0.281 (0.285) | 1.15 (1.14) | 0.954 | 9.40 ± 0.17 | 9.36 ± 0.17 |
| 180 s | 0.234 (0.240) | 1.37 (1.34) | 0.928 | 9.24 ± 0.20 | 9.19 ± 0.20 |
| 300 s | 0.321 (0.319) | 1.04 (1.01) | 0.970 | 9.31 ± 0.16 | 9.33 ± 0.15 |

κ in 10⁻⁵ m²/s. Settling: at 240 s every sensor's B stayed within about 2 %
and φ within 0.04 rad over the five cycles. At 180 s the fourth retained cycle
dipped (T4 and T5 about 5 to 9 % low, phases about 0.04 rad later) and then
recovered, so a disturbance (air movement near the rod is the likely cause) is
included in that window and widens its errors.

At 300 s, cycle 1 after the hold was not settled (T1 amplitude 5.73 °C against
6.51 °C in cycle 2, T2 to T5 also 6 to 14 % low). From cycle 2 on, T1 to T4
stayed within 1 % in B and every sensor within 0.03 rad in φ from one cycle to
the next; T5 within 2.2 % (cycle 5 holds the T5 glitch). Cycles 2 to 7 are
kept (6 cycles). Checks: cycles 3 to 7 alone give κ = 9.29 ± 0.16; replacing
the 30 s of T5 around the glitch with the mean of the same phase in cycles 4
and 6 (temporary copy, deleted; the raw file is unchanged) gives 9.30. The
glitch does not matter.

**Frequency consistency, all five periods (finite-rod fits):** 100 s 9.74 ±
0.23 and 480 s 9.40 ± 0.24 (2 November), 180 s 9.19 ± 0.20, 240 s 9.36 ±
0.17 and 300 s 9.33 ± 0.15 (4 November). Weighted mean 9.38 ± 0.08 × 10⁻⁵
m²/s with χ² = 3.5 for 4 degrees of freedom, so the five periods agree within
their errors, on two days with room temperatures of 22.5 and 27.1 °C. Our κ is
still 36 % above the handbook value for 6061-T6 (6.9 × 10⁻⁵ m²/s).

## 8. S20 production run, 10 November (run by Sammy)

| File | What happened |
|---|---|
| `data/module_08_sammy/sammy_angstrom_live_20261110_164057` | Sammy's copy of the sketch and GUI, same record format. Calipers before heating: T1 to T2, T3, T4, T5 = 25.4, 50.8, 76.2, 101.6 mm, so the sensor map is unchanged. Room temperature 24.28 °C (mean of T1 to T5 over the idle baseline; offsets sum to zero). PI, Kp 12, Ki 0.2, r 2.771. Production schedule ran to `SCHEDULE DONE`: 5 min hold, 7 cycles each at 480, 240 and 100 s. No restarts, PWM never at ±255. T3 to T5 spiked at 36 to 200 s while leads were handled (before the run). T5 read 1 to 4 °C high at 1860 to 2618 s and 3060 to 3141 s (masked). At 2598 s the TEC reading jumped 4.3 °C in one record (see below). |

Fits with our pipeline (`angstrom_fit.py --mask`, then `angstrom_finite_fit.py`)
reproduce Sammy's own numbers (8.79, 9.15, 9.29 semi-infinite, against his
8.80, 9.15, 9.29). Settling under our rule (cycle to cycle, 3 % and 0.05 rad):

- 240 s: settled from cycle 2; cycles 2 to 7 kept. κ = 9.10 ± 0.14 (finite rod).
- 480 s: cycles 2 and 3 settled, then at 2598 s (in cycle 4) the TEC reading
  stepped up 4.3 °C while T1 kept falling smoothly, PI answered with −176 PWM,
  and from cycle 5 on every rod amplitude was about 10 % lower and the rod mean
  about 1.3 °C lower with the TEC reading unchanged. The sensor ratios did not
  change. Cycles 5 to 7 kept (3, below the minimum): κ = 9.22 ± 0.19.
- 100 s: cycles 2 to 5 alternate (T4 amplitude ±3 to 5 %, T5 phase ±0.1 rad),
  so only cycles 5 to 7 pass: κ = 9.28 ± 0.16. Cycles 3 to 7 give 9.41 ± 0.17.

T2's mean reads 1.2 °C above the cosh curve through the other four sensors in
all three periods, but not at room temperature and not on 2 or 4 Nov; its
amplitude ratio is normal. Details, the mean-profile fit and the checks are in
`module_08_modeling_app.md`.

**Frequency consistency, all eight windows (finite rod):** 2 Nov 100 s 9.74 ±
0.23, 480 s 9.40 ± 0.24; 4 Nov 180 s 9.19 ± 0.20, 240 s 9.36 ± 0.17, 300 s
9.33 ± 0.15; 10 Nov 480 s 9.22 ± 0.19, 240 s 9.10 ± 0.14, 100 s 9.28 ± 0.16.
Weighted mean 9.29 ± 0.06 × 10⁻⁵ m²/s, χ² = 6.5 for 7 degrees of freedom (only
the six windows with at least 5 settled cycles: 9.30 ± 0.07, χ² = 6.3 for 5).
Five periods, three days, room temperatures 22.5, 27.1 and 24.3 °C, one κ. It is
35 % above the handbook 6061-T6 value; Sammy's caliper check rules out the
sensor spacing as the cause.

## 9. S21 repeat at 480 s, 11 November

| File | What happened |
|---|---|
| `angstrom_live_20261111_094326`, `_094614` | GUI opened but no records arrived (port not answering). Header only, no data. Not used. |
| `angstrom_live_20261111_094735` | Our sketch re-uploaded. Sensors not moved and not reseated (the note at 09:51:35 says "reseated T1 T2 T5"; that is wrong, nothing was touched). Room temperature 24.37 °C (mean of T1 to T5 with offsets over the idle baseline, all within 0.14 °C). START was pressed by mistake at 09:53:11, giving 19 s of the 100 s sine before the schedule started at 09:53:30; the 5 min hold absorbed it (TEC peak 47 °C, T1 under 30 °C). Then 7 cycles at 480 s, PI, Kp 12, Ki 0.2, r 2.771; `SCHEDULE DONE` at 10:54:29. No nan, no faults. |

Fit: `angstrom_fit_angstrom_live_20261111_094735_PI_480s.*` (cycles 2 to 7,
1133.8 to 4013.8 s), `angstrom_finite_angstrom_live_20261111_094735.txt`,
`angstrom_mean_profile_20261111.*`.

Settling: cycle 1 was 10 % low and is dropped. From cycle 2 on every sensor stays
within 1.5 % in B and 0.02 rad in φ from one cycle to the next, but all rod
amplitudes creep up together, about 0.7 % per cycle (T1 6.72 to 6.94 °C over
cycles 2 to 7) with the TEC amplitude flat. The ratios along the rod do not drift
(B5/B1 0.386 in cycle 2, 0.380 in cycle 7), so q and q′ are not biased by it.
Cycles 3 to 7 alone give κ 8.82 against 8.84 for 2 to 7 (semi-infinite).

| | q (1/m) | q′ (1/m) | κ (10⁻⁵ m²/s) | B5/B1 | lag T1 to T5 (rad) |
|---|---|---|---|---|---|
| semi-infinite | 9.37 ± 0.25 | 7.90 ± 0.20 | 8.84 ± 0.33 | 0.384 | 0.82 |
| finite rod | 9.05 ± 0.26 | 7.80 ± 0.19 | 9.27 ± 0.35 | | |

The spatial fits are poorer than on other days (χ² 18 and 24 for 3, errors
scaled up). T2 is the outlier: B2/B1 = 0.827 and lag 0.162 rad, against 0.809 to
0.813 and 0.18 rad at 480 s on 2 and 10 Nov. Its mean also sits +0.35 °C above
the cosh curve through the others (mean-profile fit: m = 4.36 ± 0.30 1/m,
χ² 80 for 3). T2 behaves as if its bead sat closer to T1 or had better contact
than the others; it has now been odd on two days running. Worth checking how T2
sits in its hole before the next run.

**All nine windows (finite rod):** weighted mean 9.29 ± 0.06 × 10⁻⁵ m²/s,
χ² = 6.5 for 8 degrees of freedom. The 480 s period now has two windows with at
least 5 settled cycles (2 Nov 9.40 ± 0.24, 11 Nov 9.27 ± 0.35).
