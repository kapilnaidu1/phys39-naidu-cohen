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

**Pre-power checks completed at the bench and verified by the instructor.**
Numeric values below still to be transcribed into the table from the bench
notebook.

| Item | Value or observation |
|---|---|
| 18 AWG on supply to `B+`/`B-` | **confirmed at the bench**, checked by the instructor |
| 18 AWG on `M+`/`M-` to TEC circuit | **confirmed at the bench**, checked by the instructor |
| 18 AWG on both thermal-switch wires | **confirmed at the bench**, checked by the instructor |
| Both Module 3 spade crimps secure | **confirmed at the bench**, checked by the instructor |
| Continuity through closed thermal switch | **confirmed at the bench**, checked by the instructor. *Meter reading not written down* |
| Thermal switch in series with TEC current path | **confirmed at the bench**, traced by hand and checked by the instructor |
| H-bridge outputs checked with TEC power off in Module 3 | yes, Module 3 Part 7 test 2, checked by the instructor. Captures not retained |
| Sketch uploaded, GUI started, PWM begins at 0 | **yes**, boot banner and PWM 0 verified at every session |
| Displayed temperature plausible | **yes**, confirmed by the finger-response test: warming the thermistor raised the reading, releasing lowered it. Checked by the instructor |
| High-current path drawn in notebook | yes, drawn and shown at the inspection, 23 Sept |
| **Instructor approval before actuator power** | **APPROVED 23 September 2026.** Instructor inspected the completed high-current wiring and approved actuator power. *Name and time to fill in.* |

Carried over from Module 3 and still open:

| Item | Status |
|---|---|
| Heat exchanger: **pump circulating**, not just fans turning | **Check this.** The 23 Sept run cooled to -6.79 C then warmed at +0.33 C/s with the command unchanged at duty 251, which is what a TEC does when hot-side heat is not being carried away. [`part7_labeled_run.txt`](../../data/module_03/part7_labeled_run.txt) |
| Measured supply voltage at the barrier strip | **confirmed at the bench**, including which of the two panel supplies feeds `B+`/`B-`. *Numeric value not written down* |
| Thermal switch rating from the body marking | **read at the bench**, checked by the instructor. *Value not written down* |

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

**Done 23 September.** Transcript:
[`data/module_04/part1_safety_shutdown_test.txt`](../../data/module_04/part1_safety_shutdown_test.txt).

All five requirements demonstrated. `TEST LIMIT 20` tripped within one 0.5 s
reporting interval, PWM went 40 to 0, measurement lines continued without a
gap, a drive command sent while latched was refused out loud, and
`CLEAR SAFETY` restored the 60.0 C limit with PWM left at 0.

The interlock also fired **unplanned** earlier the same day, on the first
boot of the new sketch: the divider's 100 kOhm upper leg had come loose, A0
read exactly 0.0, and the second trip condition caught it. A safety system
catching a fault nobody staged is better evidence than one catching a staged
fault.

### Run configuration

| Item | Value |
|---|---|
| Arduino sketch | `arduino/module_04/tec_open_loop_safety` |
| Python program | `python/tec_control_gui.py` |
| Serial port | `/dev/cu.usbmodem1101` (resolved automatically if the cable moves) |
| Supply voltage | ALITOVE ALT-1210T, 12 V nominal. Confirmed at the bench with the instructor; **numeric reading not written down** |
| Supply current limit | ALT-1210T is fixed-output, 10 A / 120 W, no adjustable limit |
| Software limit | 60.0 C |
| Hardware cutoff | thermal switch, near 70 C, in series |

---
## 2. Part 2: choosing the two endpoint PWM values

**The endpoints are defined by temperature, not by a band.** This is the part
the earlier draft of this note got wrong.

| Direction | Target steady temperature | PWM that produces it |
|---|---|---|
| Heat | **45 C +/- 2 C** | **PWM 50**, settled 46.6 C |
| Cool | **10 C +/- 1 C** | **PWM 65**, settled 9.75 C |

Those two PWM values ARE the maximum useful magnitudes. The two will differ,
and heating's will be much the smaller of the two.

Starting estimates from Module 3, to be replaced by measurement:

| | Module 3 evidence | try near |
|---|---|---|
| Heat | effective duty 64 extrapolated to about 48 C | **45 to 60** |
| Cool | duty 251 floored at -6.79 C | **90 to 130** |

Then five magnitudes per direction: **0%, 25%, 50%, 75%, 100%** of that
direction's own endpoint. Record the exact integers used.

No continuous 0 to 255 sweep. Only the five chosen values per direction,
starting low and working up.

---

## 3. Part 3: steady-state measurements

### Criterion, as the assignment defines it

1. Estimate the time constant from the response to a PWM step
2. Wait about **three time constants**
3. Then watch for **one more minute**
4. Accept the temperature when its net drift over that minute is **no larger
   than the ordinary short-term noise** in the trace
5. If a clear upward or downward drift remains, wait longer

Not a perfectly flat line, which noise makes impossible. The test is drift
against noise.

Module 3 measured a driven time constant near **50 s**, so expect roughly
150 s plus the observation minute, call it **3.5 minutes per point** and
around **45 minutes for all ten**. The passive constant was about 146 s, so
the PWM 0 points take longer than the driven ones.

### Data table

| Dir | PWM | Start C | Steady C | Waited s | Notes |
|---|---|---|---|---|---|
| Heat | 0 | | | | |
| Heat | | | | | |
| Heat | | | | | |
| Heat | | | | | |
| Heat | | | | | 45 C endpoint |
| Cool | 0 | | | | |
| Cool | | | | | |
| Cool | | | | | |
| Cool | | | | | |
| Cool | | | | | 10 C endpoint |

Two savers: go **ascending within a direction** so each point starts from the
previous steady state, and treat the two PWM 0 rows as **one measurement**
written twice.

Retain one temperature-versus-time trace per direction. Snapshot them out of
the live CSV before the next launch overwrites it.

### Strip chart y-axis

Autoscaling is implemented in `tec_control_gui.py`
(`AUTOSCALE_TEMPERATURE = True`): 1 C of headroom past the visible minimum
and maximum, with a 6 C minimum span so noise is not magnified into apparent
signal, on a white background. The PWM axis stays fixed. The fixed Module 3
axis was right for a 70 C swing and useless for judging whether a 0.05 C/s
drift has stopped.

---

## 4. Part 4: temperature versus SIGNED PWM

Signed axis: **u positive for heating, negative for cooling**. Both branches
slope upward, so both susceptibilities are positive. Raising u warms the
plate either way; going further negative cools it.

```
python3 python/plot_open_loop_calibration.py
```

Reads `data/module_04/steady_state.csv` (record PWM as a positive magnitude,
the script applies the sign from the direction column), writes the figure to
`docs/figures/module_04/`, and prints both slopes with fit ranges, R squared,
the ratio r, and Qj/Qp.

| | value | fit range | R squared |
|---|---|---|---|
| m_h | **0.5013** C per PWM count | u = 0 to +50 | 1.0000 |
| m_c | **0.1809** C per PWM count | u = -65 to 0 | 0.9989 |
| r = m_h/m_c | **2.771** | | |

Note any visible curvature. The assignment expects heating to be the steeper
branch and says a factor near 2 is an observation to investigate, not a
required answer.

---

## 5. Part 5: guided energy-balance analysis

Done at home from the Part 4 graph. No further measurements.

### 5.1 The two slopes

Above. Report units and fit ranges.

### 5.2 PWM current averaging

Over one period, current is I for time D*tau and zero for (1-D)*tau, with
D = |u|/255. From the definitions of the averages,

```
<I>   = D I
<I^2> = D I^2
```

**Why <I^2> is not <I>^2.** Squaring before averaging is not the same as
averaging before squaring. Here <I>^2 = D^2 I^2, which differs by a factor
of D. The physical consequence is the whole point of the section: Peltier
transport follows <I> and Joule heating follows <I^2>, and under PWM **both
are linear in D**, so the susceptibility is approximately constant and the
graph should be roughly straight. Had <I^2> gone as D^2, Joule heating would
be quadratic in duty and the slope would change along the axis.

With a DAC supplying a steady current instead of a chopped one,
<I^2> = <I>^2 would hold. The distinction is a property of PWM.

*Compare this prediction against the straightness of the measured graph.*

### 5.3 Steady-state balance and the slope ratio

```
C dT/dt = Q_TEC - G (T - T0)        at steady state, G (T - T0) = Q_TEC
```

The individual flows are not zero; their sum is. With signed duty d = u/255,
Peltier reversing sign with current and Joule heating not:

```
Q_TEC = d Qp + |d| Qj

heating (d > 0):   Q_TEC = d (Qp + Qj)
cooling (d < 0):   Q_TEC = d (Qp - Qj)
```

Substituting and differentiating with respect to d:

```
dTh/dd = (Qp + Qj)/G          dTc/dd = (Qp - Qj)/G
```

Both positive when Qp > Qj, with heating the larger. The 1/255 from d = u/255
appears in both measured slopes and cancels from their ratio, so

```
r = (Qp + Qj)/(Qp - Qj)   =>   Qj/Qp = (r - 1)/(r + 1)
```

Algebra check: r = 2 gives Qj/Qp = 1/3. The plot script prints this.

| | value |
|---|---|
| Qj/Qp from measured r | **0.470** |

### 5.4 Laird CP14-127-045 data sheet

**Find these yourself before asking anyone, including an AI.** The assignment
says so explicitly, and afterward you may hand over the data sheet and your
interpretation to have the selection checked.

Column for the class model at **hot side 27 C**:

| Quantity | Symbol | Value | What it means, and the condition attached |
|---|---|---|---|
| Module resistance | R_M | **1.50 ohm** | at Th = 27 C; rises to 1.68 at 50 C |
| Maximum current | I_max | **8.6 A** | the current at dT_max, not a safety ceiling |
| Max cold-side pumping at dT = 0 | Qc_max | **71.3 W** | at dT = 0 |
| Maximum temperature difference | dT_max | **70.5 C** | at Qc = 0 |

Then, at dT = 0 where conduction vanishes, with the symmetric model putting
half the Joule heat on each face:

```
Qj_max = 0.5 * I_max^2 * R_M
Qc_max = Qp_max - Qj_max          =>  solve for Qp_max
r_Laird,max = (Qp_max + Qj_max) / (Qp_max - Qj_max)
```

| | value |
|---|---|
| Qj_max | **55.47** W |
| Qp_max | **126.77** W |
| r_Laird,max | **2.556**, against measured 2.771, agreement to 8% |

### 5.5 Interpretation

Compare r_Laird,max with the measured r. **They are not expected to agree.**
Points to make:

- **D = 1 does not mean I = I_max.** Full duty means the bridge is
  continuously on; the actual current is set by supply voltage and current
  limit, H-bridge voltage drop, wiring resistance and the TEC's own
  resistance. The data-sheet figure is a maximum-current condition, not a
  full-duty condition.
- PWM chopping rather than steady DC
- The apparatus runs at finite dT, where the data-sheet dT = 0 assumption fails
- Passive heat paths the model lumps into G
- Material properties change with temperature
- Fitting one slope to a slightly curved branch

**Passive conduction.** Object hotter than the room: heat flows **out**.
Object colder: heat flows **in**. Either way it pushes the plate back toward
room temperature, so it opposes heating and cooling alike. Because that
opposition is roughly symmetric, it **cannot by itself explain unequal slope
magnitudes** - it enters both branches through the same G. The asymmetry comes
from Joule heating, which adds to Peltier transport on the heating branch and
subtracts on the cooling branch.

Module 3 saw the conductance limit directly: the plate bottomed at -6.79 C
and then warmed at +0.33 C/s with the command unchanged at duty 251.

---

## 6. Part 6: A2 submission

**Due Monday 5 October, 6:00 PM.** `A2_Naidu_Cohen.pdf`, uploaded separately
by each of us. One to two pages. **No repository file and no Git checkpoint
required** for this one.

Seven required items, tracked in
[`docs/assessments/a2_open_loop_tec.md`](../assessments/a2_open_loop_tec.md).

**Explicitly excluded:** C2/C3 circuit sketches, apparatus descriptions, the
safety demonstration, and code documentation. The Part 1 material in this note
stays here and does not go into A2.

---

## 7. Open items

Parts 1 to 6 are complete. `A2_Naidu_Cohen.pdf` is built and sits in the
repository root; it still has to be uploaded to Moodle by each of us
separately, **due Monday 5 October at 6:00 PM**.

**Confirmed at the bench and signed off by the instructor, but the numeric
value was never written down:**

- the measured supply voltage at the barrier strip
- the thermal-switch continuity reading
- the thermal-switch rating from the body marking

The inspections happened and were approved; only the numbers are missing
from the record. Two minutes with a meter and a pen at the next session
closes it, and it is worth doing, because a checklist row that says
"confirmed" without a reading is weaker evidence than one that carries the
value.

**Carried over from Module 3:** the Part 7 oscilloscope captures of pins 9
and 10 were never retained. The test was performed and checked by the
instructor; the images were not saved.
