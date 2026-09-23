# Module 4: open-loop TEC calibration and software safety

**A2 working note.** Naidu / Cohen. Started 23 September 2026.

Programs:

- [`arduino/module_04/tec_open_loop_safety`](../../arduino/module_04/tec_open_loop_safety/tec_open_loop_safety.ino), Part 1, the safety interlock
- [`python/tec_control_gui.py`](../../python/tec_control_gui.py), unchanged from Module 3
- [`python/plot_open_loop_calibration.py`](../../python/plot_open_loop_calibration.py), Part 4 figure and slopes

Raw data in `data/module_04/`, figures in `docs/figures/module_04/`,
the submitted note in [`docs/assessments/a2_open_loop_tec.md`](../assessments/a2_open_loop_tec.md).

---

## Pre-class questions

**1. What does it mean for the TEC/block temperature to reach steady state?**

The plate stops changing because the heat the Peltier is moving equals the
heat leaking back in or out through the exchanger, the mounting and the air.
Nothing has stopped happening; the flows have balanced. Practically, steady
state is a temperature whose rate of change has fallen below some threshold
we declare in advance, since a real exponential approach never formally
arrives.

Module 3 gives us the numbers to pick that threshold. The passive time
constant of this plate is about **146 s**, and a driven leg at full duty ran
with a time constant nearer **50 s**. After three time constants a system is
within 5% of its final value, so the honest waiting time is minutes, not
seconds.

**2. Why should you wait before recording a steady-state temperature?**

Because an exponential approach is steepest at the start, so an early reading
is not a small error, it is a systematically low one, and it is low by
different amounts at different PWM values. That biases the *slope*, which is
the thing this module is actually measuring, not just the individual points.

Module 3 measured this directly: at duty 28 the plate showed **no visible
response for 35 s** after the command. A reading taken inside that window
would have recorded the previous steady state and attributed it to the new
PWM value.

**3. Why might heating and cooling have different slopes in T vs PWM?**

Measured in Module 3, so this is not speculation. At full drive the heating
rate was **+1.821 C/s** and the cooling rate **-0.269 C/s**, a factor of
**6.8**. At duty 159 the same comparison gave a factor of 3.7.

The asymmetry grows with drive, which is the clue to the mechanism. A Peltier
pumps heat in proportion to current, but dissipates Joule heat in proportion
to current *squared*. When heating, the pumped heat and the Joule heat land
on the same face and add. When cooling, the Joule heat is working against the
pumping. So the useful cooling effect is a difference between a linear term
and a quadratic one, and past some current the quadratic wins.

Full discussion belongs in Part 5.

**4. Why is a software limit useful when a hardware thermal switch exists?**

Four reasons, roughly in order of importance:

- **The hardware switch is the last line, not the working line.** It opens
  near 70 C, far outside the 10 to 45 C band this module runs in. Reaching it
  means the experiment already went badly wrong. A run should not normally
  end by tripping the final protection, any more than a car should normally
  stop by hitting the barrier.
- **It can act on information the switch cannot see.** The switch responds to
  its own body temperature at one spot on the plate. Software can also stop
  on a sensor that has stopped making sense, which is a fault the switch has
  no way to detect.
- **It leaves a record.** A bimetallic switch opens silently and closes again
  when it cools, with nothing written down. Our interlock latches, prints why,
  and keeps reporting, so the temperature trace through the event survives in
  the CSV.
- **It fails in a different way.** The switch is in series with the TEC and
  works even if the sketch hangs. The software limit works even if the switch
  is mis-mounted or has poor thermal contact. Two protections that share no
  failure mode is the point.

---

## 1. Part 1: instrument preparation and the safety interlock

### Pre-power checklist

*To be completed at the bench, with the supply off and disconnected.*

| Item | Value or observation |
|---|---|
| 18 AWG on supply to `B+`/`B-` | *to record* |
| 18 AWG on `M+`/`M-` to TEC circuit | *to record* |
| 18 AWG on both thermal-switch wires | *to record* |
| Both Module 3 spade crimps secure | *to record* |
| Continuity through closed thermal switch | *to record, with the meter reading* |
| Thermal switch in series with TEC current path | *to record* |
| H-bridge outputs checked with TEC power off in Module 3 | yes, Module 3 Part 7 test 2, checked by the instructor. Captures not retained |
| Sketch uploaded, GUI started, PWM begins at 0 | *to record* |
| Displayed temperature plausible | *to record* |
| High-current path drawn in notebook | *to record* |
| **Instructor approval before actuator power** | *to record, with name and time* |

Carried over from Module 3 and still open:

| Item | Status |
|---|---|
| Heat exchanger: **pump circulating**, not just fans turning | **Check this.** The 23 Sept run cooled to -6.79 C then warmed at +0.33 C/s with the command unchanged at duty 251, which is what a TEC does when hot-side heat is not being carried away. [`part7_labeled_run.txt`](../../data/module_03/part7_labeled_run.txt) |
| Measured supply voltage at the barrier strip | *to record.* The panel carries **two** supplies. Record which one feeds `B+`/`B-` |
| Thermal switch rating from the body marking | *to record* |

### The software limit

Implemented in
[`tec_open_loop_safety.ino`](../../arduino/module_04/tec_open_loop_safety/tec_open_loop_safety.ino).
Against the assignment's five requirements:

| Requirement | Where |
|---|---|
| Named constant | `const float temperatureLimitC = 60.0;` |
| Checked every loop | `checkTemperatureLimit()`, called from `loop()` before the reporting gate |
| Both PWM outputs to zero | `tripSafety()` zeroes the command, `applyDrive()` returns early with both pins LOW |
| Serial data keeps printing | the measurement line is untouched; the trip only adds `# ` lines |
| Reports clearly when active | a banner at the moment of the trip, then `# SAFETY SHUTDOWN ACTIVE` on **every** report while latched |

Three design decisions worth defending in the writeup:

**It latches.** Auto-resuming the moment the plate dropped back under the
limit would turn an over-temperature event into an oscillation around the
safety threshold, which the operator might never notice. A latch forces a
human to acknowledge the event. Cleared by RESET or `CLEAR SAFETY`.

**The check is not gated by the print interval.** In the Module 3 sketch the
temperature was only computed inside the 500 ms reporting block. Leaving the
safety check there would mean it ran at whatever rate we happened to be
printing. It now runs every pass, roughly 20 Hz, since 500 averaged samples
take about 50 ms.

**A second trip condition, not required by the assignment.** Five consecutive
unusable thermistor readings also latch the shutdown. An instrument that
cannot measure temperature should not be driving a heater. Five rather than
one because the A0 contact on this bench glitches for single samples: one bad
reading is noise, five in a row is a fault.

### Demonstrating the shutdown without heating anything

`TEST LIMIT <degC>` lowers the active limit immediately, so the trip can be
demonstrated at room temperature with TEC power off and nothing re-uploaded.
It can only ever lower the limit, never raise it above `temperatureLimitC`,
so the test path cannot be used to weaken the interlock.

Procedure, with **TEC power off**:

1. Note the room temperature from the display, call it `T_room`
2. Send `TEST LIMIT` with a value about 2 C below `T_room`
3. Expect the trip banner within about 50 ms, then `# SAFETY SHUTDOWN ACTIVE` on every report
4. Confirm the measurement lines keep coming, with `PWM: 0`
5. Send `SET PWM 40 DIR HEAT` and confirm it is **refused** while latched
6. Send `CLEAR SAFETY`, confirm the limit returns to 60.0 C and PWM stays 0
7. Show the instructor

*Transcript to record into `data/module_04/part1_safety_shutdown_test.txt`.*

### Run configuration

| Item | Value |
|---|---|
| Arduino sketch | `arduino/module_04/tec_open_loop_safety` |
| Python program | `python/tec_control_gui.py` |
| Serial port | `/dev/cu.usbmodem1101` (resolved automatically if the cable moves) |
| Supply voltage | *to record* |
| Supply current limit | ALT-1210T is fixed-output, 10 A / 120 W, no adjustable limit |
| Software limit | 60.0 C |
| Hardware cutoff | thermal switch, near 70 C, in series |

---

## 2. Parts 2 and 3: direction, PWM values and steady-state data

**Operating band for this module: 10 C to 45 C.** Narrower than Module 3,
which ran -16 to +54. The maximum useful PWM in each direction is whatever
keeps the steady temperature inside that band, and it will be **well below
255 for heating**, since full duty reached 54 C.

Starting estimate from Module 3, to be replaced by the exploratory sweep:
heating passed 45 C partway through a full-duty leg, so the heating maximum
is likely modest. Cooling reached its floor near -7 C at duty 251, so the
cooling maximum is limited by the 10 C bound rather than by the hardware.

### Exploratory sweep

*Start low, increase gradually, watch temperature and supply current.*

| Direction | Max useful PWM | Steady T at that PWM | Why this is the maximum |
|---|---|---|---|
| Heat | *to record* | | |
| Cool | *to record* | | |

### Steady-state criterion

*Declare it before taking data, and record it here.*

Proposed: **temperature changing by less than 0.1 C over 30 s**, with a
minimum wait of 3 minutes regardless. The 0.1 C figure is just above the
0.079 C quantization step at room temperature, so a tighter threshold would
be measuring the ADC rather than the plate. The minimum wait comes from the
~50 s driven time constant: three of those is 150 s.

### Data table

| Direction | PWM | Start T (C) | Steady T (C) | Time waited (s) | Notes |
|---|---|---|---|---|---|
| Heat | 0 | | | | |
| Heat | | | | | |
| Heat | | | | | |
| Heat | | | | | |
| Heat | | | | | |
| Cool | 0 | | | | |
| Cool | | | | | |
| Cool | | | | | |
| Cool | | | | | |
| Cool | | | | | |

Time-series traces to retain: at least one heating and one cooling.

---

## 3. Part 4: temperature versus PWM

Generate with:

```
python3 python/plot_open_loop_calibration.py
```

It reads `data/module_04/steady_state.csv`, writes the figure to
`docs/figures/module_04/`, and prints dT/dPWM for each direction.

| Direction | dT/dPWM (C per PWM count) | Linear? |
|---|---|---|
| Heat | *to record* | |
| Cool | *to record* | |

---

## 4. Part 5: heating/cooling asymmetry

*To write after the data is in.* The argument is sketched in pre-class
question 3 above and the Module 3 measurements support it. Points to cover,
referring to the apparatus rather than the code:

- pumped heat scales with current, Joule heat with current squared, and on
  the heating leg they add while on the cooling leg they oppose
- the exchanger is a finite heat sink, demonstrated by the 23 Sept cooling
  leg reversing at -6.79 C under unchanged full command
- the thermistor reads one point on the plate, not the whole thermal system
- thermal contact, heat capacity and the room as a boundary condition

---

## 5. Open items

- Every `*to record*` row above
- Whether the pump is actually circulating
- Scope captures were not retained for Module 3 Part 7 test 2
