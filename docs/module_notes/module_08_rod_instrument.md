# Module 7, Part III: rod instrument and data-acquisition chain (C5)

Naidu / Cohen. Started 26 October 2026. Course naming: this note, the data
(`data/module_08/`) and the figures (`docs/figures/module_08/`) use the
`module_08` paths the course page asks for.

**C5 is demonstrated in class on Wednesday 28 October; the Moodle
"C5 Team Checkoff" receipt is due 11:55 AM and must cite the pushed commit.**

Fields marked **TO MEASURE** are not known yet and must come from the bench.
Nothing in this note is a measurement until it says so.

---

## 1. The acquisition chain

| Stage | What | Where |
|---|---|---|
| Sensor | 100 kOhm NTC thermistor (TDK B57861S0104F040V24) on the rod surface, one per position | rod |
| Divider | 5V - R_fixed - pin - thermistor - GND, thermistor as the lower leg, one divider per channel | breadboard |
| ADC | Uno 10-bit ADC, 4.88 mV per count, one converter switched between pins | A0 (base), A1 to A5 (rod) |
| Averaging | base: 1000 readings per report; rod: 500 per channel; the first 4 readings after each channel switch are discarded | sketch |
| Conversion | divider voltage, then resistance, then the beta equation (B = 4540 K, R25 = 100 kOhm), on the averaged count | sketch |
| Serial | one line per report: `Temperature (C): base, Time (s): t, PWM: n, Heat/Cool: d, Rod (C): R1, R2, R3, R4, R5` | 9600 baud |
| Logging | one CSV row per line: base columns as in Module 6, then `T_R1_C` ... | `python/rod_pi_logger.py` |
| Base control | the same PI controller and anti-windup as Module 6, acting on the base thermistor | `python/tec_pi_control_gui.py` |

**Why one line per report.** Every channel in a row was read within about
0.3 s, in the same pass of `loop()`, and carries one Arduino time stamp
(`time_s`). The base temperature is the rod's boundary condition, so a delay
or an amplitude ratio between a rod channel and the base is only meaningful
if both are on the same clock. Two separate loggers, or a laptop clock, would
add an unknown offset between the streams.

**Why the discarded readings.** The Uno's ADC samples through a multiplexer
onto a small capacitor. The divider's source resistance (about 50 kOhm at
room temperature) is five times what the ATmega328P data sheet recommends
(10 kOhm or less), so the first reading after a channel switch can be pulled
toward the previous channel. The sketch throws those away.

**Raw data only.** The saved temperatures are the raw beta-equation values.
Offsets from the cross-check are applied in memory by the analysis scripts
(`--offsets`), never written back.

## 2. Hardware and wiring (TO MEASURE / TO CONFIRM on the bench)

| Item | Value | How measured |
|---|---|---|
| Rod material | aluminium alloy 6061 (as given for the course rod, 26 Oct) | label / instructor |
| Rod diameter D, radius R = D/2 | D = 0.5 in = 12.70 mm nominal, R = 6.35 mm; **confirm with calipers** at 3 places (mean ± sd) | nominal size, 26 Oct |
| Cross-section A = πR², perimeter P = 2πR | A = 126.7 mm² = 1.267e-04 m², P = 39.9 mm = 0.0399 m, A/P = R/2 = 3.175 mm (from the nominal D) | calculated |
| Rod length L | 300 mm (30 cm) as given; **measure from the chosen origin to the tip** | nominal, 26 Oct |
| Coordinate origin and direction | TO DEFINE (for example, the face where the rod meets the plate, x increasing toward the tip) | photograph |
| Insulation around the rod | TO RECORD (bare, foam, partly covered) | |
| Each upper resistor R_fixed | TO MEASURE with the multimeter, enter in `rodRfixed[]` and `sensor_map.csv` | multimeter |

**Wiring.** Each rod thermistor gets its own divider, wired exactly like the
base: 5V to R_fixed to the analog pin, pin to thermistor, thermistor to GND.
Default pins A1 to A5 (edit `rodPins[]` if different). **Disconnect the old
trim pot from A1 first.**

**Sensor map:** [`data/module_08/sensor_map.csv`](../../data/module_08/sensor_map.csv).
One row per rod channel, in the same order as `rodPins[]`: channel name, pin,
position from the origin (mm), position uncertainty (mm), measured R_fixed,
notes. The logger names the CSV columns from this file and copies it into the
metadata of every run.

Photograph: TO ADD, `docs/figures/module_08/sensor_map_photo.jpg`, showing
the origin, the x direction and each channel label.

## 3. How to run

1. Upload `arduino/module_08/rod_tec_multichannel/rod_tec_multichannel.ino`
   (after setting `NUM_ROD`, `rodPins[]` and `rodRfixed[]`). Check in Serial
   Monitor at 9600 baud that the banner lists the rod channels and that every
   channel gives a number, then quit the Arduino IDE.
2. **Check each channel by its response:** warm one thermistor between finger
   and thumb and confirm that only its column rises. This proves the channel
   name, the pin and the physical sensor match.
3. Start the logger from the repository root:

   ```bash
   cd ~/Documents/GitHub/phys39-naidu-cohen
   python3 python/rod_pi_logger.py
   ```

   It writes `data/module_08/rod_run_<date_time>.csv`, `_meta.json` and
   `_notes.csv`. Type notes into the box during the run (Enter saves them
   with the time).

## 4. Part 1: cross-check (calibration)

With the TEC off and the rod left alone until it is at room temperature,
record at least 60 s (better 3 to 5 min). Then:

```bash
python3 python/analysis/rod_calibration.py data/module_08/rod_run_<...>.csv --t0 <start> --t1 <end>
```

It prints each channel's mean, scatter and offset from the mean of all
channels, writes `data/module_08/calibration_<run>.csv`, and plots each
channel minus the reference. **Decision rule:** apply an offset only if it is
much larger than its own standard error *and* not small compared with the
temperature differences to be measured. A trend of offset with position means
the rod was not at one temperature; wait longer and repeat.

**Multi-point check.** If an offset is large, or to show the offsets do not
change with temperature, bundle the thermistors flat on the plate next to the
base thermistor (beads touching, taped, shaded) and hold two or three plateaus:
control off at room temperature, then PI at 35 °C and 45 °C, about 5 minutes
steady at each, with a note at each. Then

```bash
python3 python/analysis/rod_calibration_multipoint.py data/module_08/rod_run_<...>.csv --windows <t0:t1> <t0:t1> <t0:t1>
```

fits reading = a + b·reference for each channel. A gain b of 1 means a
constant offset is enough; otherwise the gain is applied as well
((T − a)/b). Either output file works with `--offsets`.

Result: TO FILL after the run.

## 5. Part 2: baseline and step response

1. Baseline: control OFF, at least 2 min, all channels and room temperature.
   Note the room temperature (and how it was measured) in the notes box.
2. Step: PI (Kp 12, Ki 0.2, anti-windup on), base setpoint a safe step above
   room, for example 35 to 40 °C. Type a note at the step.
3. Record long enough to see the disturbance reach the farthest sensor and
   level off: tens of minutes, not the 2 to 4 minutes of the plate-only runs.
4. Analyse:

   ```bash
   python3 python/analysis/rod_step_response.py data/module_08/rod_run_<...>.csv --offsets data/module_08/calibration_<run>.csv
   ```

   It plots all channels, the commanded setpoint and the measured base on one
   time axis, and for each channel the arrival time (0.2 °C above its
   baseline), the half-change time and the final change, against position.

**Why farther sensors respond later and less:** heat reaches a point only by
conducting along the rod from the base, and the rod stores heat (ρcA per unit
length) as it goes, so the change spreads diffusively: the arrival time grows
roughly like x²/κ. Meanwhile the side surface keeps losing heat (hP per unit
length), so less of the base change survives the farther out a sensor is. In
the steady state the excess decays roughly like e^(−mx).

Result: TO FILL after the run.

## 6. C5 checklist (Wednesday 28 October)

- [ ] Thermistors cross-checked; calibration file and figure saved
- [ ] Sensor coordinates, origin, direction, uncertainties and wiring
      documented (sensor map, photograph, section 2)
- [ ] Synchronized multichannel logging shown live with `rod_pi_logger.py`
- [ ] Baseline and initial step-response data saved and plotted
- [ ] Every run has `_meta.json` (units, channel labels, commit, sensor map)
      and `_notes.csv`
- [ ] Commit pushed; Moodle receipt filled in with the template below
- [ ] Each of us can trace one channel end to end and name one dominant
      uncertainty

Moodle receipt template:

```text
Assignment or milestone: C5 Team Checkoff
Student name(s): Kapil Naidu, Samuel Cohen
Repository URL: https://github.com/kapilnaidu1/phys39-naidu-cohen
Branch: main
Full commit hash: <git rev-parse HEAD after the final push>
README path: README.md
Principal code path(s): arduino/module_08/rod_tec_multichannel/rod_tec_multichannel.ino, python/rod_pi_logger.py, python/analysis/
Data and figure path(s): data/module_08/, docs/figures/module_08/
Command used to reproduce the result: python3 python/analysis/rod_calibration.py ...; python3 python/analysis/rod_step_response.py ...
```

## 7. Preparing the C5 oral questions

These are prompts for our own answers, not answers to read out.

1. **Trace one sensor.** Pick a channel and follow it: physical position on
   the rod (sensor map), divider and pin (`rodPins[]`), conversion (beta
   equation in the sketch), serial field (its place after `Rod (C):`), CSV
   column (`T_<name>_C`), and its calibration offset (calibration file).
2. **Why one time reference?** Section 1: delays and amplitude ratios against
   the base are the measurement.
3. **Metadata for six months later.** Units, channel names and positions,
   origin and direction, rod geometry and insulation, room temperature, the
   setpoints and gains, the sketch and program versions (commit), the
   sampling and averaging, and timed notes of anything that happened. The
   `_meta.json` and `_notes.csv` files hold most of it; the rest is in this
   note.
4. **Largest uncertainty.** Candidates to compare once there are data:
   - sensor position: a position error δx shifts θ by about m·θ·δx, so it
     matters most where the profile is steep;
   - thermal contact: a thermistor that touches the rod poorly reads between
     the rod and the air, which looks like extra decay;
   - calibration offsets, compared with the small θ at the far sensors;
   - room-temperature drift during a long hold, which shifts every θ.
   Whichever is largest feeds straight into m, and through m (with the
   Module 8 phase data) into the conductivity.
5. to 7. **"Long and thin", the fin equation, the two profiles.** These are
   the A4 derivations. A4 is individual, so each of us prepares them from
   Lienhard Section 4.5 and the Part II page; we can check each other.
