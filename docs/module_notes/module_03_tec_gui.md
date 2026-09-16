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
| Arduino board and port | **Elegoo UNO R3**, ATmega328P, 16 MHz crystal, over USB. Pin compatible with the Uno and the same timer hardware, so the Module 1 PWM timebase results carry over. Port: *to record* |
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

At room temperature the divider sat at ADC 465.4, which is 2.275 V, giving
83.45 kOhm and 28.6 C. That is near mid scale, which is where a 100 kOhm
thermistor against a 100.0 kOhm upper leg should sit, and warming the sensor
moved the ADC down and the reported temperature up, the expected direction for
an NTC in the lower leg.

All three Module 3 sketches refuse to report a temperature when the averaged
divider reading falls outside ADC 20 to 1000. They print `---` and the likely
wiring cause instead of a number, because the conversion chain will return a
plausible looking temperature from a reading that carries no sensor
information at all.

Sensitivity at that operating point: with a 100 kOhm upper leg and the
thermistor near 83 kOhm, dV/dT is about 61.8 mV/K, so one ADC count is about
0.079 C. The observed spread of about 1.5 counts is therefore about 0.12 C,
which is the quantization floor rather than sensor noise.
