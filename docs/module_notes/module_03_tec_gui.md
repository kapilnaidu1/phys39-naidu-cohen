# Module 3: manual TEC drive and Python control

**C3 evidence record, in progress.** Naidu / Cohen.

Sketches referenced rather than pasted:

- [`arduino/module_03/tec_manual_fixed_direction`](../../arduino/module_03/tec_manual_fixed_direction/tec_manual_fixed_direction.ino), Part 2
- [`arduino/module_03/tec_manual_hardware_direction`](../../arduino/module_03/tec_manual_hardware_direction/tec_manual_hardware_direction.ino), Part 3
- [`arduino/module_03/tec_python_control`](../../arduino/module_03/tec_python_control/tec_python_control.ino), Part 6

Python:

- [`python/tec_temperature_strip_chart.py`](../../python/tec_temperature_strip_chart.py), Part 4, display only
- [`python/tec_control_gui.py`](../../python/tec_control_gui.py), Part 5, full control

---

## 1. Part 1: TEC wiring and pre-power checklist

| Item | Value or observation |
|---|---|
| Arduino board and port | **Elegoo UNO R3**, ATmega328P, 16 MHz crystal, over USB. Pin compatible with the Uno and the same timer hardware, so the Module 1 PWM timebase results carry over. Port: **`/dev/cu.usbmodem1101`**, which is the default already set in both Python programs |
| Thermistor pin | `A0`, divider midpoint. `5V` - 100.0 kOhm - `A0` - thermistor - `GND`, thermistor as the LOWER leg |
| H-bridge control pins | pin 9 to `RPWM`, pin 10 to `LPWM`, `R_EN` and `L_EN` and logic `VCC` to `5V`, logic `GND` to Arduino `GND`. Pin 11 is the SPDT direction input from Part 3 onward |
| PWM starts at zero? | **Yes.** `setup()` drives both bridge inputs LOW before anything else, so the bridge is not commanded during boot or reset. Both manual sketches then start **disarmed** and hold duty at 0 until the trim pot has been seen below ADC 10, so a knob left up from the previous run cannot deliver drive at power-on. `tec_python_control` starts at PWM 0 and returns to 0 on any command it cannot parse |
| Module 2 motor test completed with TEC disconnected? | **Yes.** Session S4, 9 September 2026. TEC module and thermal switch were unplugged from the load terminals for all of Module 2 Part 3; the only load driven was a small DC motor. Record: [`data/module_02/part3_hbridge_motor.txt`](../../data/module_02/part3_hbridge_motor.txt) |
| High-current leads are 18 AWG? | *to record* |
| Prepared TEC and thermal-switch wiring inspected? | *to record, with who inspected it* |
| Heat exchanger connected to 12 V and operating? | Liquid loop: an ID-COOLING radiator with two fans, feeding a coolant block on the underside of the plate. *To record: fans turning AND pump circulating, both confirmed before the TEC is energised.* Fan rotation alone does not prove the pump is running |
| Power supply voltage | ALITOVE ALT-1210T, label reads DC 12 V 10 A 120 W, AC input 100 to 120 V. Measured at the barrier strip: *to record*. Note the panel carries a **second** enclosed supply as well, so record which one feeds the H-bridge `B+` and `B-` |
| Power supply current limit | **None adjustable.** The ALT-1210T is a fixed-output enclosed supply rated 10 A, 120 W. Its only front adjustment is an output voltage trim. The current ceiling is therefore the supply's own 10 A limit, not a bench setting |
| Thermal cutoff identified? | Thermal switch is mounted on the aluminium plate and wired in series with the TEC. Rating and open temperature: *to record from the body marking* |
| Instructor check complete? | *to record, with name and time* |

Actuator power feeds the H-bridge `B+` and `B-` directly, not through the
barrier strip. `M+` and `M-` go to the TEC through paired positions on the
strip. `R_IS` and `L_IS` are unconnected.

**Oscilloscope grounding.** Every probe ground clip to Arduino `GND`, never to
`M+` or `M-`. Both of those are driven outputs and a ground clip is earth
referenced, so grounding either one can short the bridge.

---

## 2. Status of each part

| Part | Program | Written | Bench evidence in the repository |
|---|---|---|---|
| 1, wiring and checklist | n/a | table above, partly filled | pending the rows marked *to record* |
| 2, manual drive, fixed direction | `tec_manual_fixed_direction` | yes, `maxDuty = 64`, about 25% | temperature channel confirmed at its expected operating point and by the sign of its response. Drive itself was confirmed under the Part 3 sketch, section 5 |
| 3, hardware direction switch | `tec_manual_hardware_direction` | yes | **direction calibration measured, 16 Sept 2026.** `PIN9_IS_HEAT = false`, both directions driven at duty 40 with 12 V on. Section 5, raw excerpts in [`data/module_03/part3_direction_calibration.txt`](../../data/module_03/part3_direction_calibration.txt) |
| 4, strip chart, display only | `tec_temperature_strip_chart.py` | yes | **run 23 Sept.** 391 rows, 195 s, 0.50 s cadence, no gaps. `part4_baseline_21C_nodrive.csv`. Baseline only: the trim pot never armed, so PWM is 0 throughout |
| 5, control GUI | `tec_control_gui.py` | yes | **run 23 Sept.** Slider and HEAT/COOL drove the plate over a 23 C range. Section 6 |
| 6, serial command interface | `tec_python_control` | yes | **run 23 Sept.** Parsed and executed commands from the GUI for the whole cycle |
| 7, heating and cooling test | Parts 5 and 6 together | n/a | **done 23 Sept, checked at the bench by the instructor.** Full drive, **-16.0 to +54.1 C, a 70.1 C swing**, 37.5 C below ambient and 32.6 C above. [`part7_full_drive_70C_swing.txt`](../../data/module_03/part7_full_drive_70C_swing.txt) and its CSV. Earlier partial-drive attempt kept at [`part7_heat_cool_cycle_gui.txt`](../../data/module_03/part7_heat_cool_cycle_gui.txt). Direction labels inverted in both, section 6 |
| 8, cleanup and C3 | n/a | repository layout done, this note started | pending completion of the rows above |

**Direction calibration.** The `Heat/Cool` field reports observed physics, not
which pin carries the pulse train. That mapping has now been measured and
`PIN9_IS_HEAT = false` is set in both the hardware-direction sketch and the
Python control sketch. Section 5 records the runs and the reasoning.

## 3. Temperature channel verification

Gate 3 passed after the divider was rebuilt. Steady reading at ambient:

```
Temperature (C): 22.68, Time (s): 273.00, PWM: 0, Active PWM pin: none
    [ADC = 542.0, V = 2.649, R = 112.68 kOhm, pot ADC = 0]
```

ADC 542 is close to mid scale, which is where a 100 kOhm thermistor against a
100.0 kOhm upper leg belongs. The measured 112.68 kOhm agrees with the
datasheet beta curve for the TDK part at 22.68 C to better than 0.1 kOhm, which
independently confirms the sensor identity: it is the 100 kOhm
B57861S0104F040V24, not a higher value part, so `Rnominal = 100000` and
`Beta = 4540` are correct as written.

An earlier session reported 457 kOhm and -2.06 C from this same channel. The
conversion arithmetic was correct and the reading was stable to under one ADC
count, but the divider was miswired, so the number described the circuit rather
than the plate. A stable, low-noise, internally consistent reading is not
evidence that a sensor is connected correctly. The orientation and operating
point checks below are what establish that.

Warming the sensor moves the ADC down and the reported temperature up, the
expected direction for an NTC in the lower leg.

All three Module 3 sketches refuse to report a temperature when the averaged
divider reading falls outside ADC 20 to 1000. They print `---` and the likely
wiring cause instead of a number, because the conversion chain will return a
plausible looking temperature from a reading that carries no sensor
information at all.

Sensitivity at that operating point: with a 100 kOhm upper leg and the
thermistor near 83 kOhm, dV/dT is about 61.8 mV/K, so one ADC count is about
0.079 C. The observed spread of about 1.5 counts is therefore about 0.12 C,
which is the quantization floor rather than sensor noise.

---

## 4. Build order and test gates

The circuit is built in five stages, and **each stage is verified before the
next one is added**. A fault can then only ever be in the thing just added,
which is the difference between a five minute fix and an afternoon. Build
everything first and any one of forty connections can be the problem.

Work with the 12 V supply unplugged from the wall for stages 1 to 4.

### Stage 1: power rails

| From | To |
|---|---|
| Arduino `5V` | breadboard `+` rail |
| Arduino `GND` | breadboard `-` rail |

**The rails are split in the middle.** On a full size breadboard the `+` rail
on one half is a separate conductor from the `+` rail on the other half, and
the same for `-`. If any component sits in the far half, jumper `+` to `+` and
`-` to `-` across the break.

**Gate 1.** DMM between `+` and `-`, measured at **all four rail ends**. Every
one must read about 5.00 V. A rail that reads 0 V at one end and 5 V at the
other is the split rail.

### Stage 2: trim pot on A1

| From | To |
|---|---|
| `+` rail | one outer pot pin |
| `-` rail | other outer pot pin |
| pot wiper, the middle pin | Arduino `A1` |

Each of the three pins in its own breadboard row. No resistor: the pot is
already a divider. Which outer pin takes `5V` only decides which way the screw
increases the reading.

**Gate 2.** Upload, open Serial Monitor at 9600, turn the screw end to end.
`pot ADC` must sweep smoothly from near 0 to near 1023. Partial range or no
response means one of the three connections is wrong.

### Stage 3: thermistor divider on A0

```
+ rail ── 20a [100 kOhm] 25a
                          25b [thermistor] 30a ── 30b ── - rail
                          25c ──────────────────────────► A0
```

| From | To |
|---|---|
| `+` rail | `20a` |
| 100 kOhm resistor | `20b` to `25a` |
| thermistor | `25b` to `30a` |
| `30b` | `-` rail |
| `25c` | Arduino `A0` |

Row 25 must hold three things: the resistor's lower leg, the thermistor's upper
leg, and the wire to `A0`. Those five holes are one node, and it is the whole
circuit. Two rows five apart are not the same node, so an off by one row error
here is invisible in a photograph and fatal to the measurement.

**Gate 3.** Two conditions, both required:

1. At rest, ADC near 551 and a temperature near room temperature
2. Pinch the thermistor: ADC falls, reported temperature rises

Condition 2 is the orientation test. If warming it sends the ADC up, the
resistor and thermistor are in each other's positions. Condition 1 without
condition 2 is not a pass, because the conversion chain produces a plausible
looking temperature from a reading that carries no sensor information.

### Stage 4: H-bridge logic, no actuator power

| From | To |
|---|---|
| Arduino pin 9 | `RPWM` |
| Arduino pin 10 | `LPWM` |
| `+` rail | `R_EN`, `L_EN`, logic `VCC` |
| `-` rail | logic `GND` |
| pin 11 | SPDT direction switch common, Part 3 onward |

`R_IS` and `L_IS` stay unconnected. The 12 V supply is still unplugged.

**Gate 4.** `PWM: 0` at rest with the pot at zero. Turn the pot up and the
commanded duty must rise while `Active PWM pin` names one pin and only one.
Exactly one of `RPWM` and `LPWM` ever carries the pulse train; the other sits
at 0 V, never at 5 V, because holding it high inverts the duty and a commanded
zero would mean full drive.

### Stage 5: TEC power

Only after gates 1 to 4 pass. Fill in the Part 1 checklist in section 1 first,
including the instructor check, then plug in the 12 V supply.

**Gate 5.** At low duty, the plate temperature moves and keeps moving in one
direction for long enough to clear the sensor's thermal lag. Record which
Arduino pin was carrying the pulse train while the plate warmed, and set
`PIN9_IS_HEAT` from that observation.

**Gate 5 passed, 16 September 2026.** Both directions at duty 40. Section 5.

---

## 5. Direction calibration, measured

| Switch | Pin driven | Plate | Rate at duty 40 |
|---|---|---|---|
| pin 11 = 0 V | **10** | rises | **+0.209 C/s** |
| pin 11 = 5 V | **9** | falls | **-0.118 C/s** |

So pin 10 is heat, pin 9 is cool, and **`PIN9_IS_HEAT = false`**.

### Confirmed independently, 23 September

A second session reached the same answer from a cleaner run, recorded in
[`data/module_03/part3_cooling_below_ambient.txt`](../../data/module_03/part3_cooling_below_ambient.txt).
Duty 28 on **pin 9** drove the plate from a 21.47 C ambient down to
**18.62 C and still falling**, that is **2.85 C below ambient**, which no
passive process can do. Pin 9 is the cooling direction and
`PIN9_IS_HEAT = false` stands.

**The onset delay, which invalidated several earlier attempts.** Drive was
commanded at t = 90 s and the temperature did not move until t = 125 s: a
**35 second lag** between command and response. Any drive interval shorter
than about 45 s therefore carries no information about direction. Several
runs on 16 and 23 September were 3 to 7 s long and were read at the time as
"the TEC is doing nothing", including one that was taken as evidence the
12 V supply was not reaching the bridge. The supply was on. The intervals
were too short. Hold drive for at least 90 s before drawing any conclusion.

### Why these runs are conclusive and the earlier ones were not

Passive physics only ever moves the plate **toward** room temperature. So
motion away from ambient, or motion toward ambient far faster than passive
decay allows, is the Peltier working and nothing else. Motion toward ambient
at roughly the passive rate proves nothing, because an unpowered plate does
exactly that. Several earlier runs in this session were of that second kind
and were correctly treated as carrying no direction information.

The plate's own passive time constant, measured from an undriven decay
earlier in the session, is **tau = 146 s**: at 9.1 C above ambient it fell at
0.0625 C/s. That is the plate on its coolant loop, not the 15 s figure from
the datasheet, which describes the bare sensor in air.

**Heating run.** The plate climbed from 30.55 to 31.28 C in a 23 C room.
Passive loss there pulls down at about 0.055 C/s, so the drive supplies
0.26 C/s and beats passive loss fourfold. Nothing but active heating raises a
plate above ambient.

**Cooling run.** Two windows, and the second is the stronger one. At 24.4 C
the plate sits only 1.4 C above ambient, so passive decay has almost nothing
left to give: 1.4 / 146 = 0.009 C/s. The measured fall was 0.118 C/s, about
**12x faster than it can fall unaided**. The ratio grows as ambient is
approached, 5x at 31 C and 12x at 24 C, which is the expected shape: passive
loss dies off with the gradient while the Peltier keeps pumping at fixed
duty.

### Sensor mounting, settled as a side effect

The two runs give **opposite** signs in the two switch positions. A
thermistor mounted on the wrong face of the Peltier would have moved the same
way in both cases, because that face heats regardless of which direction the
current takes relative to the controlled face. It did not, so the sensor
reads the face being controlled. That was the other live explanation for a
label disagreeing with the reading and it is now closed.

### What is not evidence

An apparent rise from 23.4 to 32.3 C in about 7 s appears earlier in the
session logs. Those reports read `PWM: 0` and `DISARMED`, so no drive was
commanded, and the decay afterwards had a 15 s time constant, matching a bare
sensor in air. That was a finger on the thermistor, not plate drive, and it
is recorded so it is not mistaken for a heating run.

### Conversion chain cross-check

Every `R` field in both runs agrees with the beta model to better than
0.03 kOhm, using `Rnominal = 100 kOhm`, `Beta = 4540 K`, `Rfixed = 100 kOhm`.
The temperature column is therefore not the product of a mis-set constant.

---

## 6. Parts 5 to 7: the heating and cooling cycle, and an inverted label

Full record: [`data/module_03/part7_heat_cool_cycle_gui.txt`](../../data/module_03/part7_heat_cool_cycle_gui.txt).
Data: `data/module_03/tec_control_run.csv`.

| commanded | duty | plate |
|---|---|---|
| HEAT, t = 14 to 32 s | 159 | fell 15.5 to **9.5 C**, -0.33 C/s |
| COOL, t = 33 to 50 s | 159 | rose 9.5 to **30 C**, +1.21 C/s |

23 C of swing about a 21.5 C ambient: 12 C below it and 11 C above it. Both
legs move the plate away from room temperature, which passive physics cannot
do, so both are the Peltier working.

### Why HEAT cooled and COOL heated

The board was running an older copy of `tec_python_control` with
`PIN9_IS_HEAT = true`. The repository copy has `false`. The sketch picks the
driven pin with one line:

```cpp
pwmOnPin9 = (commandedHeating == PIN9_IS_HEAT);
```

With `true`, commanding HEAT selects pin 9, and pin 9 is the **cooling**
direction, measured three separate times (16 Sept at duty 40, 23 Sept at
duty 28 crossing 2.85 C below ambient, and this run at duty 159 crossing
12 C below). So HEAT drove the cooling side.

**Every component behaved correctly.** The GUI sent what the button said.
The sketch parsed it, drove exactly one bridge input, and reported the
direction it had been commanded. The plate responded strongly and
repeatably. One boolean was wrong, and that single constant inverted the
instrument's whole vocabulary: the button, the printed word, and the
`Heat/Cool` column all lied together, and agreed with each other while doing
it.

A self-consistent instrument is not a correct one. Nothing internal can
catch this, because every part is faithfully passing on the same wrong
premise. Only comparing a label against the physical world finds it, which
is why `Heat/Cool` is defined as **observed** heating rather than as a pin
number.

### Rate asymmetry

Heating ran **3.7x faster** than cooling, +1.21 against -0.33 C/s. That is
expected: on the heating leg the module delivers pumped heat plus its own
Joule heating, while on the cooling leg the Joule heating opposes the
pumping. A Peltier is always a better heater than a cooler, and this run
measures that directly.

### Two things the run exposed

**Overshoot.** Duty went to 0 at t = 51 and the plate carried on to 32.5 C
before turning over. Commanding zero stops adding heat; it does not stop the
temperature.

**No output ceiling.** Duty reached 159, so that copy also had
`maxDuty = 255`. At +1.21 C/s the plate would pass 80 C inside a minute of
continuous heating. The run was stopped by hand. The repository copy is now
capped at 64 and announces the cap at boot, and any unattended run needs it.

---

## 7. Part 7 at full drive: a 70 C swing

Full record: [`data/module_03/part7_full_drive_70C_swing.txt`](../../data/module_03/part7_full_drive_70C_swing.txt).
Data: `data/module_03/part7_full_drive_70C_swing.csv`, 917 rows over 458.5 s.
Checked at the bench by the instructor.

| | |
|---|---|
| minimum | **-16.00 C** at t = 411.5 s |
| maximum | **+54.10 C** at t = 450.0 s |
| swing | **70.10 C** |
| relative to ambient | 37.5 C below, 32.6 C above |

Both extremes are far outside anything passive heat flow can reach, since
passive physics only moves the plate toward room temperature. The entire
70 C range is the module doing work.

### Rate asymmetry, measured properly

| leg | duty | rate |
|---|---|---|
| cooling | 96 to 254 | **-0.269 C/s** |
| heating | about 250 | **+1.821 C/s** |

Heating is **6.8x faster** than cooling. The earlier partial-drive run put
that factor at 3.7, and the difference between the two figures is itself the
result. Joule heating grows as the square of the current while the pumping
grows only linearly, so the asymmetry gets worse the harder the module is
driven. That is the argument against running a Peltier cooler flat out: past
some current the extra Joule heating costs more than the extra pumping gains.

### Sensor range at the cold end

At -16 C the thermistor is about 1.13 MOhm, so the divider sits at 4.60 V
and ADC 940, inside the plausibility window of 20 to 1000 but near the top.
Sensitivity there is 25.6 mV/K, which is **0.19 C per ADC count** against
0.079 C per count at room temperature. The -16.00 figure therefore carries
about 2.4x the quantization uncertainty of the +54.10 figure.

### The partial-drive run that looked like a hardware fault

The first Part 7 attempt reached only +27 C and -10 C from ambient and was
read at the bench as a sagging supply or a dead pump. It was neither. The
sketch had `maxDuty = 64` and `applyDrive()` clamps to it:

```cpp
int duty = constrain(commandedPwm, 0, maxDuty);
```

The GUI said 255. The bridge got 64. The curve was an honest response to a
quarter of the commanded drive, and the only thing wrong was that the number
on the screen was not the number being delivered.

The ceiling was announced twice, in the boot banner and in a `CAPPED` notice
on every command above it. Both went to the terminal, and both were missed.

**A safety limit the operator has forgotten does not look like a safety
limit. It looks like a broken instrument,** and it sends you inspecting a
supply, wiring and a heat exchanger that were fine all along. An output
limit is only safe if it cannot be forgotten, which means it has to appear
where the operator is already looking.

Fixed both ways: `maxDuty` is now 255, so commanded and delivered duty are
the same number, and the GUI now shows `CAPPED` and `OUTPUT CEILING` on the
window in orange beside the PWM readout rather than only in the terminal.

Safety now rests on the series thermal switch, on the temperature channel,
and on not leaving a full-drive heating run unattended. At +1.82 C/s that
last one is not optional.
