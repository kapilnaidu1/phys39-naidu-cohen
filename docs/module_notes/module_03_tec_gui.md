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
| 2, manual drive, fixed direction | `tec_manual_fixed_direction` | yes, `maxDuty = 64`, about 25% | temperature channel confirmed at its expected operating point and by the sign of its response. No logged drive run yet |
| 3, hardware direction switch | `tec_manual_hardware_direction` | yes | pending. `PIN9_IS_HEAT` is still a placeholder and must be set from the observed direction of heat flow, not from a pin number |
| 4, strip chart, display only | `tec_temperature_strip_chart.py` | yes, compiles | pending. No CSV in `data/module_03/` yet |
| 5, control GUI | `tec_control_gui.py` | yes, compiles | pending |
| 6, serial command interface | `tec_python_control` | yes | pending |
| 7, heating and cooling test | Parts 5 and 6 together | n/a | pending. This is the run another person has to be able to reproduce |
| 8, cleanup and C3 | n/a | repository layout done, this note started | pending completion of the rows above |

**Direction calibration.** The `Heat/Cool` field reports observed physics, not
which pin carries the pulse train. The mapping is fixed by one bench
experiment: command a low duty in one direction, watch the plate temperature
for long enough to clear the sensor's own lag, and set `PIN9_IS_HEAT` from
which way it moved. Until that is done the field is unverified in both the
hardware-direction sketch and the Python control sketch.

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
