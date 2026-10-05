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

> **Superseded.** The 146 s quoted below is the Module 3 estimate, taken on
> 16 September, before the A0 wiring fault was found on 23 September. Fitting
> the eight constant-command steps in `data/module_04/full_run.csv` gives
> **&tau; = 62.9 &plusmn; 5.0 s** (`python/estimate_tau.py`), and the passive
> zero-command decay alone gives 65.8 s. Use the fitted value; the text below
> is left as written because it is what we reasoned from at the time.

**1. Steady state?** The plate stops changing because the heat the Peltier
moves equals what leaks back through the exchanger, mounting and air. Nothing
has stopped happening; the flows have balanced. Practically it is a
temperature whose rate of change has fallen below a threshold declared in
advance, since an exponential approach never formally arrives. Module 3 gives
the numbers: passive &tau; &asymp; 146 s, driven &asymp; 50 s, so three time
constants is minutes.

**2. Why wait?** An exponential approach is steepest at the start, so an early
reading is not a small error but a systematically low one, low by different
amounts at different PWM values. That biases the *slope*, which is what this
module measures. Module 3 recorded no response for 35 s after commanding
duty 28, but the Module 4 steps do not reproduce that: every one responds
within 0.5 to 2 s of the command. The Module 3 run had its duty set by a trim
pot that its own log describes as intermittent.

**3. Why do the slopes differ?** Measured in Module 3: +1.821 &deg;C/s heating
against &minus;0.269 cooling at full drive, a factor of 6.8, and 3.7 at duty
159. The asymmetry growing with drive is the clue: Peltier pumping scales with
current, Joule heating with current squared. Heating adds them, cooling
opposes them.

**4. Why a software limit when a hardware switch exists?** The switch opens
near 70 &deg;C, far outside the 10 to 45 band, so reaching it means the
experiment already went wrong; a run should not normally end by tripping the
final protection. Software can also stop on a sensor that has stopped making
sense, which the switch cannot detect. It leaves a record, where a bimetallic
switch opens silently. And the two fail differently: the switch works if the
sketch hangs, the software works if the switch is mis-mounted.

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

| Requirement | Where |
|---|---|
| Named constant | `const float temperatureLimitC = 60.0;` |
| Checked every loop | `checkTemperatureLimit()`, called before the reporting gate, ~20 Hz |
| Both PWM outputs to zero | `tripSafety()` zeroes the command; `applyDrive()` returns early with both pins LOW |
| Serial keeps printing | measurement line untouched; the trip only adds `# ` lines |
| Reports clearly | banner at the trip, then `SAFETY SHUTDOWN ACTIVE` on every report |

Three design decisions worth defending:

**It latches.** Auto-resuming would turn an over-temperature event into an
unnoticed oscillation at the safety threshold. Cleared by RESET or
`CLEAR SAFETY`.

**The check is not gated by the print interval**, which would have made it run
at whatever rate we happened to be printing. It runs every pass, ~20 Hz.

**A second trip condition**, not required: five consecutive unusable thermistor
readings also latch, because an instrument that cannot measure temperature
should not drive a heater. Five rather than one because the A0 contact glitches
for single samples.

**Demonstrated 23 September**, transcript in
[`data/module_04/part1_safety_shutdown_test.txt`](../../data/module_04/part1_safety_shutdown_test.txt).
`TEST LIMIT 20` tripped within one 0.5 s reporting interval, PWM went 40 to 0,
measurement lines continued without a gap, a drive command sent while latched
was refused, and `CLEAR SAFETY` restored the 60.0 C limit with PWM left at 0.

The interlock also fired **unplanned** on the sketch's first boot: the
divider's 100 kOhm upper leg had come loose, A0 read exactly 0.0, and the
unusable-reading condition caught it.

### Run configuration

| Item | Value |
|---|---|
| Arduino sketch | `arduino/module_04/tec_open_loop_safety` |
| Python | `python/tec_control_gui.py` |
| Serial port | `/dev/cu.usbmodem1101` |
| Supply | ALITOVE ALT-1210T, 12 V; fixed output, no adjustable current limit |
| Software limit | 60.0 C |
| Hardware cutoff | thermal switch near 70 C, in series |


## 2. Part 2: choosing the two endpoint PWM values

**The endpoints are defined by temperature, not by a band.** This is the part
the earlier draft of this note got wrong.

| Direction | Target steady temperature | PWM that produces it |
|---|---|---|
| Heat | **45 C +/- 2 C** | **PWM 50**, recorded as 46.6 C. **No raw data for this run exists in the repository**; see section 4 |
| Cool | **10 C +/- 1 C** | **PWM 65**, final minute 9.81 C in `full_run.csv`, settled by the criterion |

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

| | value | fit range | R squared | rms residual |
|---|---|---|---|---|
| m_h | **0.5013** C per PWM count | u = 0 to +50 | 0.999999 | 0.010 C over a 25.1 C span |
| m_c | **0.1809** C per PWM count | u = -65 to 0 | 0.998912 | 0.138 C over an 11.8 C span |
| r = m_h/m_c | **2.771** | | | |

The figure prints R squared to four decimals, which is the Excel convention and
rounds the heating branch to 1.0000. **The honest numbers are above, and the
rms residual is the more useful one** because it has units and can be compared
with the noise floor.

### The cooling branch scatters 14 times more, and that is not explained

The heating points sit within 0.010 &deg;C rms of their line, the cooling
points within 0.138 &deg;C. An earlier version of this section explained the
difference as the cooling branch bending, because Joule heating grows as
current squared. **That was wrong, and is withdrawn.** Under PWM the bridge
switches a fixed current on and off, so &lt;I&gt; = DI and
&lt;I<sup>2</sup>&gt; = DI<sup>2</sup> are both linear in duty, which is the
result of A2's own derivation: neither branch should curve.

Nor does it. Adding a quadratic term to the cooling fit lowers the rms only
from 0.138 to 0.101 &deg;C, F(1,2) = 1.7 against a 5% critical value of 18.5,
and the residuals alternate in sign along the branch (&minus;+&minus;+&minus;),
which is scatter rather than a bend. So the cooling branch is straight but
noisier, and **why it is noisier is not established by this data.** The
heating residuals alternate the same way, at a fourteenth of the size.

### What the R squared does and does not measure

**Eight of the ten points in `steady_state.csv` are asymptotes of an
exponential fit, not direct readings** (the notes column records which). Each
asymptote is estimated from several hundred samples, so it is a
noise-suppressed quantity: scatter around a line through fitted asymptotes is
much smaller than scatter through raw endpoint readings would be. The R squared
above therefore measures the linearity of the apparatus **and** the quality of
those exponential fits together, and cannot be separated into the two.

An earlier version of this paragraph said only 0.5% to 3.6% of each step
remained when it was stopped, on the basis of a single 63 s time constant.
**That is withdrawn.** The raw log shows the +12 run still rising 0.54 &deg;C
per minute when stopped, about three times faster than a single 63 s
exponential with that much left would allow; Module 6 finds a second, slower
time scale that explains it. The audit below shows what that does to the
extrapolated values.

### Raw-data audit, 5 October

`python/steady_state_from_raw.py` recomputes every point directly from
`full_run.csv` and writes `data/module_04/steady_state_from_raw.csv`.
`steady_state.csv`, which A2 was built from, is left unchanged.

| u | final 60 s, measured | drift per min | settled? | extrapolated asymptote, by fitting window | submitted |
|---|---|---|---|---|---|
| &minus;65 | 9.81 | +0.05 | yes | 9.80 to 9.85 | 9.75 |
| &minus;49 | 13.00 | &minus;0.06 | yes | 12.92 to 12.96 | 12.99 |
| &minus;32 | 15.99 | &minus;0.11 | yes | 15.83 to 15.90 | 15.83 |
| &minus;16 | 19.06 | &minus;0.25 | **no** | 18.66 to 18.96 | 18.90 |
| 0 | 21.65 | &minus;0.11 | yes | 21.52 to 21.60 | 21.54 |
| +12 | 26.95 | +0.54 | **no** | 27.13 to 28.39 | 27.57 |
| +25 | 33.87 | +0.27 | **no** | 34.02 to 34.23 | 34.07 |
| +38 | 40.36 | +0.27 | **no** | 40.55 to 40.74 | 40.61 |
| +50 | **no run in the log** | | | | 46.60 |

What this establishes:

- **Only four of the eight runs met the module's steady-state criterion.**
  The other four were still moving 0.25 to 0.54 &deg;C per minute when
  stopped, so their values are extrapolations, not readings.
- **Those extrapolations depend on an undocumented choice.** Fitting the whole
  run, or only its last 200, 150 or 120 s, moves the +12 asymptote across
  1.26 &deg;C. The submitted values are closest to a 200 s window, within 0.02
  to 0.07 &deg;C on the heating side, but which window was used was never
  recorded.
- **The +50 point has no data behind it here.** The plate never exceeds
  40.48 &deg;C anywhere in `full_run.csv`. The run may have been logged in a
  file that was not kept; that should be checked before the point is used
  again.
- **Two submitted values match truncated snapshots rather than the end of the
  run.** &minus;65 is recorded as 9.75, which is the last reading in
  `cooling_trace_01.csv`, a snapshot that stops at 384 s; the run continued
  to 481 s and its final minute averages 9.81. The same thing happened with
  K<sub>p</sub> = 8 in Module 5.

**What survives.** Using only points present in the log, the ratio comes out
r = 2.720 from the measured final minutes, 2.765 from whole-run asymptotes and
2.816 from 200 s asymptotes, against 2.771 submitted; Q<sub>J</sub>/Q<sub>P</sub>
ranges 0.462 to 0.476 against 0.470. **A2's physical conclusion holds.** What
does not hold is the precision implied by R<sup>2</sup> = 1.0000: the honest
uncertainty on r from the choice of method alone is about &plusmn;0.05, and
the heating line's rms residual is 0.02 to 0.25 &deg;C depending on method,
not 0.010.

---

## 5. Part 5: guided energy-balance analysis

Written up in full in **`docs/A2_Naidu_Cohen.pdf`**, which is the submitted
form. Summary of the results:

**PWM averaging.** Over one period the current is I for D&tau; and zero
otherwise, so `<I> = DI` and `<I^2> = DI^2`. These differ from `<I>^2 = D^2I^2`
by a factor 1/D. Both Peltier (&prop; `<I>`) and Joule (&prop; `<I^2>`) are
therefore **linear in duty**, giving a constant susceptibility. The heating
branch is linear to one part in a thousand, which is the bench confirmation:
a D&sup2; Joule term would have curved it visibly.

**Slope ratio.** From `C dT/dt = Q_TEC - G(T-T0)` at steady state, with
`Q_TEC = d*Qp + |d|*Qj`:

```
dTh/dd = (Qp + Qj)/G      dTc/dd = (Qp - Qj)/G
r = (Qp+Qj)/(Qp-Qj)   =>   Qj/Qp = (r-1)/(r+1)
```

The 1/255 from d = u/255 and the conductance G are common to both slopes and
cancel from the ratio, which is why r is worth measuring: it is independent of
G, which was never determined.

| | value |
|---|---|
| r = m_h/m_c | **2.771** |
| **Qj/Qp = (r-1)/(r+1)** | **0.470** |

Joule heat at the object face is about 47% of the Peltier pumping.

**Laird CP14-127-045**, SPECIFICATIONS table, hot side 27.0 &deg;C:

| Quantity | Value | Condition |
|---|---|---|
| R_M | 1.50 ohm | at Th = 27 C; 1.68 at 50 C |
| I_max | 8.6 A | current at dT_max, not a safety ceiling |
| Qc_max | 71.3 W | at **dT = 0** |
| dT_max | 70.5 C | at **Qc = 0** |

```
Qj_max = 0.5 * I_max^2 * R_M = 55.47 W
Qp_max = Qc_max + Qj_max     = 126.77 W
r_Laird,max                  = 2.556
```

All values re-read from the course-hosted data sheet on 5 October and
confirmed; the SPECIFICATIONS table is on page 3. A Seebeck cross-check that
used to sit here, S = (V_max - I_max R_M)/dT_max = 0.0142 V/K, has been
withdrawn: it used R_M at 27 C for a condition where the module averages about
-8 C, and the result moves by a factor of three with that unknown resistance.
See `docs/assessments/a2_open_loop_tec.md` section 4.

**Comparison: 2.771 measured against 2.556, agreement to 8%**, closer than
this comparison deserves. They are not expected to agree: D = 1 does not imply
I = I_max (12 V across 1.50 ohm gives at most about 8.0 A, before the bridge
drop, wiring and back-EMF; the bench current itself was not measured); our
current is chopped rather than steady DC; the data sheet
holds at dT = 0 while the plate ran 25 C above and 12 C below ambient; and the
coefficients move with temperature.

**Passive conduction.** Hotter than the room, heat flows out; colder, in.
Either way it drives the object back toward room temperature, opposing both
branches. It cannot explain unequal slopes: the *same* G sits in the
denominator of both derivatives, so it sets how steep they are but cancels
from their ratio. The asymmetry lives in the numerators, where Qj adds on
heating and subtracts on cooling.

## 6. Part 6: A2 submission

**Due Wednesday 7 October, 6:00 PM.** `A2_Naidu_Cohen.pdf`, uploaded separately
by each of us. One to two pages. **No repository file and no Git checkpoint
required** for this one.

Seven required items, tracked in
[`docs/assessments/a2_open_loop_tec.md`](../assessments/a2_open_loop_tec.md).

**Explicitly excluded:** C2/C3 circuit sketches, apparatus descriptions, the
safety demonstration, and code documentation. The Part 1 material in this note
stays here and does not go into A2.

---

## 7. Open items

Parts 1 to 6 are complete. `docs/A2_Naidu_Cohen.pdf` is built; it still has to
be uploaded to Moodle by each of us separately, **due Wednesday 7 October at 6:00 PM**.

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
