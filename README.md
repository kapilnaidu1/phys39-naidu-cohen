# Phys 39, Instrumentation Laboratory

**Team:** Kapil Naidu and Samuel Cohen
**Course:** Phys 39, Fall 2026

Team repository for the temperature-control instrument built across the
semester. The instrument measures temperature with an NTC thermistor in a
voltage divider and drives a thermoelectric cooler in either direction through
a BTS7960 H-bridge, first by hand and later under Python control.

---

## Repository layout

```
arduino/module_0N/        authoritative Arduino sketches, grouped by module
code/module_01/           Module 1 sketches, kept at their original paths
data/module_0N/           raw captures, one folder per module
docs/module_notes/        written evidence notes
docs/images/              photographs, Serial Plotter and oscilloscope captures
docs/figures/module_03/   Module 3 figures
python/                   Python programs for Module 3 onward
requirements.txt          Python dependencies
```

Each sketch folder has the same name as the `.ino` inside it, which the Arduino
IDE requires. Grouping those folders under a module directory is fine; the IDE
only cares about the sketch's immediate parent.

The Module 1 sketches stay at `code/module_01/` because the submitted A1 PDF
cites those paths.

---

## Hardware and pin map

Arduino Uno, powered over USB. Actuator power is a separate 12 V supply
(ALITOVE ALT-1210T, 12 V 10 A) feeding the H-bridge `B+` and `B-` directly,
not through the terminal block.

| Arduino pin | Connected to | Notes |
|---|---|---|
| `A0` | thermistor divider midpoint | `5V` - 100 kΩ - `A0` - thermistor - `GND`. Thermistor is the LOWER leg |
| `A1` | trim pot wiper | outer terminals to `5V` and `GND` |
| `11` | SPDT direction switch, common | outer terminals to `5V` and `GND`. Module 3 Part 3 onward |
| `9` | H-bridge `RPWM` | logic-level control input, not a power output |
| `10` | H-bridge `LPWM` | logic-level control input, not a power output |
| `5V` | H-bridge `R_EN`, `L_EN`, logic `VCC` | both enables stay high; direction is chosen by which input gets PWM |
| `GND` | H-bridge logic `GND` | common ground is required for every measurement |

H-bridge `M+` and `M-` are driven power outputs. The load (a small DC motor in
Module 2, the TEC from Module 3) connects there through paired positions on the
barrier strip. `R_IS` and `L_IS` are left unconnected.

**Oscilloscope grounding.** Every probe ground clip goes to Arduino `GND`.
Never to `M+` or `M-`: a ground clip is earth-referenced and both of those are
driven outputs, so grounding either one can short the bridge. Measure `M+` and
`M-` with the probe tip, each relative to Arduino `GND`.

**Sensor part.** TDK/EPCOS **B57861S0104F040V24**, R/T characteristic No. 2014,
R25 = 100.000 kΩ, B25/100 = 4540 K, ±1%, dissipation factor 1.5 mW/K, cooling
time constant about 15 s in air.

---

## Which sketch goes with which program

| Sketch | Module and part | Input | Output | Pair with |
|---|---|---|---|---|
| [`thermistor_serial`](arduino/module_02/thermistor_serial/thermistor_serial.ino) | 2, Parts 1 and 2 | `A0` thermistor | labeled line, or one bare number per line for Serial Plotter | Serial Monitor or Serial Plotter |
| [`trimpot_hbridge`](arduino/module_02/trimpot_hbridge/trimpot_hbridge.ino) | 2, Part 3 | `A1` pot, pin 11 direction | PWM on pin 9 or 10 | Serial Monitor |
| [`tec_manual_fixed_direction`](arduino/module_03/tec_manual_fixed_direction/tec_manual_fixed_direction.ino) | 3, Part 2 | `A0`, `A1` | PWM on pin 10 only, pin 9 held LOW | Serial Monitor |
| [`tec_manual_hardware_direction`](arduino/module_03/tec_manual_hardware_direction/tec_manual_hardware_direction.ino) | 3, Part 3 | `A0`, `A1`, pin 11 switch | PWM on pin 9 or 10 | Serial Monitor |
| [`tec_python_control`](arduino/module_03/tec_python_control/tec_python_control.ino) | 3, Part 6 | `A0` and serial commands | PWM on pin 9 or 10 | [`tec_control_gui.py`](python/tec_control_gui.py) |

`thermistor_serial` has a `PLOTTER_MODE` flag: `false` prints the labeled line
for Serial Monitor, `true` prints one bare number per line for Serial Plotter.

The display-only [`tec_temperature_strip_chart.py`](python/tec_temperature_strip_chart.py)
reads the same measurement line as `tec_control_gui.py` but never writes to the
port, so it works with any of the Module 3 sketches.

---

## How to upload and run

Arduino, for any sketch:

1. Open the `.ino` from its folder under `arduino/`.
2. Select the Uno and its port, then Upload.
3. Open Serial Monitor at **9600 baud**. A blank window almost always means the
   baud dropdown does not match `Serial.begin()`.

Python, for Module 3 Parts 4 onward:

```bash
pip install -r requirements.txt
python python/tec_temperature_strip_chart.py     # display only
python python/tec_control_gui.py                 # full manual control
```

Set `SERIAL_PORT` near the top of whichever program you run. If it is wrong,
the program lists the ports it can see and exits rather than failing silently.

**One serial port, one owner.** The Uno has a single USB serial connection and
access to it is all or nothing. Close Arduino Serial Monitor and Serial Plotter
completely before starting a Python program, and close Python before reopening
either. Because Serial Monitor cannot stay open, both Python programs print
every received line to the terminal.

---

## Serial line formats

Module 2, `thermistor_serial` with `PLOTTER_MODE = false`:

```
time = 156.00 s    average ADC = 450.3    voltage = 2.201 V    resistance = 78.64 kOhm    temperature = 29.8 C    samples = 500
```

Module 3, all three TEC sketches:

```
Temperature (C): 27.73, Time (s): 645.06, PWM: 120, Heat/Cool: 1
```

| Field | Meaning |
|---|---|
| `Temperature (C)` | plate temperature from the averaged divider reading. `---` means the divider reading was not usable, not that it is cold |
| `Time (s)` | Arduino `millis()` since reset, in seconds. The instrument's own clock, not the laptop's |
| `PWM` | commanded duty out of 255. One count is 8.000 µs of high time |
| `Heat/Cool` | `1` means OBSERVED heating, `0` means OBSERVED cooling, assigned from the bench experiment rather than from a pin number |

Lines beginning with `#` are the Arduino's own comments, headings, command
acknowledgements and faults. The Python parsers show them and do not try to
read them as measurements.

Commands from Python to Arduino, one per line:

```
SET PWM 120 DIR HEAT
SET PWM 45 DIR COOL
```

Anything else sets PWM to zero.

### CSV written by the Python programs

Columns carry their units in the names: `time_s`, `temperature_C`, `pwm`,
`heat_cool`. One row per accepted measurement, flushed immediately, so an
unplugged cable costs at most the last row.

---

## Module 1: first contact with the instrument

Evidence note: [`docs/module_notes/module_01_evidence.md`](docs/module_notes/module_01_evidence.md)
Submitted as [`docs/A1_Naidu_Cohen.pdf`](docs/A1_Naidu_Cohen.pdf)

| Sketch | What it does |
|---|---|
| [`adc_raw.ino`](code/module_01/adc_raw.ino) | prints the raw 10-bit integer as `ADC:nnn` |
| [`adc_volts.ino`](code/module_01/adc_volts.ino) | converts each count to a voltage |
| [`averaging_compare.ino`](code/module_01/averaging_compare.ino) | alternates 100 single readings with 100 thousand-reading averages, and times the acquisition loop |
| [`pwm_brightness.ino`](code/module_01/pwm_brightness.ino) | maps the averaged pot voltage to PWM on pin 9 |
| [`blink_ratio.ino`](code/module_01/blink_ratio.ino) | blinks an LED at a chosen HIGH:LOW ratio |

| Quantity | Measured |
|---|---|
| ADC range | 0 to 1023, 1024 codes |
| One-count resolution | 4.88 mV |
| s, 100 single readings | 2.035 mV |
| s, 100 averages of 1000 | 0.0726 mV |
| Measured s₁₀₀₀/s₁ | 0.0357 against a prediction of 0.0316 |
| Effective bits gained | 4.81 against an ideal of 4.98 |
| Time per `analogRead()` | 112.0 µs, so 8,925 conversions per second |
| PWM frequency, pin 9 | 490.421 Hz measured, 490.196 Hz predicted |
| PWM duty at two pot settings | 20.0% and 80.0%, pulse widths 408.1 µs and 1.632 ms |
| Rise time | 3.238 µs |

Hardware: pot into A0, LED on pin 9 through a 3.25 kΩ series resistor. The TEC
supply stayed off for the whole session.

---

## Module 2: first real instrument pieces

Evidence note: [`docs/module_notes/module_02_instrument_pieces.md`](docs/module_notes/module_02_instrument_pieces.md)
This note is the `C2` evidence record and covers all nine required items.

Data: [`data/module_02/part1_part2_thermistor.txt`](data/module_02/part1_part2_thermistor.txt)
and [`data/module_02/part3_hbridge_motor.txt`](data/module_02/part3_hbridge_motor.txt)

| Quantity | Result |
|---|---|
| Baseline plate temperature | 20.9 °C, stable |
| Finger contact | 29.8 °C, decaying back to 21.1 °C about 35 s after release |
| Serial Plotter records | three runs, 571 values total |
| Direction symmetry | verified at duty 85, 197, 216 and 254 of 255 |
| Rotation | pin 11 HIGH gave clockwise, LOW gave counterclockwise |
| PWM timebase | 490.196 Hz, 2040 µs, exactly 8.000 µs per `analogWrite` count |
| Speed sweep | 14 settings from duty 20 to 254 |

The TEC and thermal switch were disconnected for all of Module 2. The only
load driven was a small DC motor.

---

## Module 3: manual TEC and first Python GUI

In progress. Note: `docs/module_notes/module_03_tec_gui.md`

Working so far: the thermistor channel reads a plausible calibrated
temperature through the divider, and both manual sketches drive the H-bridge
from the trim pot with a low-power cap.

Both manual sketches start **disarmed** and force PWM to zero until the trim
pot has been seen at zero, so the pre-power checklist line "PWM starts at zero"
is enforced in hardware terms rather than trusted. All three Module 3 sketches
refuse to report a temperature when the divider reading falls outside ADC 20 to
1000, and print the likely wiring cause instead of a number.

---

## Verification performed

- Every value in the Module 1 and Module 2 result tables was measured on the
  bench rather than calculated and assumed.
- Both Module 2 sketches compile with `--warnings all` and produce no warnings
  from our own files.
- The Module 3 thermistor channel was checked against its expected
  room-temperature operating point, near mid scale, and confirmed by the sign
  of its response to warming.
- Both Python programs compile, and the line parser tolerates the additional
  bracketed diagnostics the manual sketches print.

## Open questions

- The B value of the thermistor embedded in the TEC plate, if it is a
  different part from the 100 kΩ breadboard sensor. Near 25 °C all candidate
  beta profiles agree to within half a degree, so the reading is usable while
  this is outstanding.
- How much of the Module 2 beta-model disagreement with the manufacturer's
  R/T table, about 0.5 °C at 15 °C and 35 °C, a Steinhart-Hart fit would
  remove.
- The TEC's thermal time constant, which sets how long a direction test must
  run before its sign is reliable. Not yet measured.
