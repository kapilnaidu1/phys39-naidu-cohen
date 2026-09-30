# Module 5: P-only temperature control

Naidu / Cohen. Evidence for **A3** and the **C4** demonstration. No separate
paper for this module.

Programs:

- [`python/tec_p_control_gui.py`](../../python/tec_p_control_gui.py), the P controller
- [`arduino/module_04/tec_open_loop_safety`](../../arduino/module_04/tec_open_loop_safety/tec_open_loop_safety.ino), **unchanged**; it keeps the software limit and independent shutdown authority
- [`python/plot_droop.py`](../../python/plot_droop.py), Part 3 and 4 figure

Data in `data/module_05/`, figures in `docs/figures/module_05/`.

---

## What Module 4 hands us

Everything in Part 3 is chosen from these, not guessed:

| | value | where |
|---|---|---|
| Heating susceptibility | **&chi;<sub>T,h</sub> = 0.50127 &deg;C per PWM count** | R&sup2; = 1.0000, u = 0 to +50 |
| Cooling susceptibility | **&#124;&chi;<sub>T,c</sub>&#124; = 0.18091 &deg;C per PWM count** | R&sup2; = 0.9989, u = &minus;65 to 0 |
| Ambient / zero-PWM temperature | **T<sub>amb</sub> = 21.54 &deg;C** | measured baseline |
| Driven time constant | **&tau; &asymp; 70 s** | fitted from the step responses |
| Noise floor | **0.16 &deg;C peak-to-peak** | 60 s at rest |

---

## Pre-class questions

**1. T<sub>set</sub> = 30 &deg;C and T = 25 &deg;C: heat or cool?**

Heat. e = T<sub>set</sub> &minus; T = +5 &deg;C, so u = K<sub>p</sub>e > 0,
and positive u selects heating by our convention. Verified in code: the
controller returns HEAT with P = 10 at K<sub>p</sub> = 2.

**2. Units of K<sub>p</sub>?**

u is in PWM counts and e in &deg;C, so K<sub>p</sub> is in **PWM counts per
&deg;C**. That is exactly why a bare K<sub>p</sub> value cannot be called
large or small: the answer depends on the units it carries. The
dimensionless combination is L = K<sub>p</sub>&chi;<sub>T,u</sub>, since
&chi; has the reciprocal units.

**3. Why does P control need a nonzero error to give a nonzero output?**

Because the output *is* the error times a constant. u = K<sub>p</sub>e is
zero when e is zero; there is no other term. So at the setpoint the
controller commands no TEC heat flow at all.

But a lump above room temperature keeps losing heat to the room whether or
not the controller is commanding anything, and a lump below room temperature
keeps gaining it. To sit at a non-ambient setpoint, something must supply a
steady counter-flow, and the only way P control can command one is to hold a
standing error. **The error is not a failure of the loop; it is the loop's
only means of asking for the heat that holds the temperature.**

Quantitatively, at steady state the commanded PWM is P = K<sub>p</sub>&times;droop,
and that product must equal the PWM the plate needs open-loop,
P<sub>required</sub> &asymp; 16.9 counts for our 30 &deg;C setpoint. Raising
K<sub>p</sub> lets a smaller droop supply the same product, which is why
droop falls as 1/(1+L) but never reaches zero.

**4. Symptoms of K<sub>p</sub> too large?**

- Overshoot past the setpoint, then undershoot: the command reverses because
  the error changes sign, and the plate's thermal lag means it keeps moving
  after the command has flipped
- Sustained or growing oscillation about the setpoint
- PWM slamming between large heating and large cooling values instead of
  settling, and saturating at 0 or 255
- Chasing the measurement noise: 0.16 &deg;C of noise at K<sub>p</sub> = 50
  is 8 PWM counts of command jitter with no thermal cause at all

The one-lump model of Part 6 cannot produce oscillation at any gain, since it
is first order and decays as e<sup>&minus;t/&tau;<sub>cl</sub></sup>. So if
we do see oscillation, that is evidence the one-lump picture is missing
something: thermal lag between TEC and thermistor, a second mass, the 1 s
sampling interval, or saturation.

---

## 1. Part 1: the controller

Implemented in [`tec_p_control_gui.py`](../../python/tec_p_control_gui.py),
which imports the serial thread, parser and port resolver from the Module 4
GUI rather than duplicating them.

The control law is eight lines, matching the assignment's list:

```python
e = self.setpoint - temperature_c     # 2. error
u = self.kp * e                       # 3. signed PWM
heating = u >= 0.0                    # 4. sign -> direction
p = int(round(abs(u)))                # 5. magnitude
p = max(0, min(255, p))               # 6. clamp
self.send_command()                   # 7. to the Arduino
```

Item 1, the 1000-sample average, is already done on the Arduino; the GUI
never sees a raw ADC reading. Item 8, the plots, are temperature with the
setpoint drawn as a dashed line, the error on its own axis, and PWM split
red/blue by direction.

**Division of authority.** Python decides what to ask for; the Arduino
decides what to do. The Module 4 software limit lives in the sketch and is
unreachable from the GUI, so a runaway gain can make the loop oscillate or
saturate but cannot defeat the interlock. If the sketch latches, the GUI
notices the `SAFETY SHUTDOWN` line and switches P control off rather than
carrying on requesting drive that is being refused.

**Loop rate.** One control update per measurement, about 1 Hz. There is no
point computing a command more often than the measurement it is based on.

*To record: the sign test and instructor approval.*

---

## 2. Part 2: sign test at low gain

| Step | Expected | Result |
|---|---|---|
| Setpoint 30 &deg;C (above ambient), K<sub>p</sub> = 0.25 | positive error &rarr; **heating** | **PASS.** 3064 samples with e from +1.56 to +8.92 &deg;C, all reported HEAT |
| Setpoint 15 &deg;C (below ambient), K<sub>p</sub> = 0.25 | negative error &rarr; **cooling** | **PASS.** 394 samples with e from &minus;13.44 to &minus;6.81 &deg;C, all reported COOL |

Data: `data/module_05/sign_test_and_sweep.csv`.

**One sample needs explaining, and it is not a sign error.** At t = 1598.0 s,
the instant the setpoint moved from 30 to 15, a single line reports
e = &minus;13.44 &deg;C with direction HEAT and PWM 12. That is the Arduino
echoing the *previous* command: the controller computes the new command from
that measurement and sends it, but the sketch does not report the new
direction until its next line a second later. One sample of pipeline delay
in a 1 Hz loop. Recorded here because an automated check on the logged file
flags it, and the explanation is more useful than silently filtering it out.

**The asymmetry shows up in the loop gain.** The same K<sub>p</sub> = 0.25
gives

```
L = 0.125  heating      (chi = 0.50127)
L = 0.045  cooling      (chi = 0.18091)
```

a **2.77x weaker loop in the cooling direction for an identical gain**. The
Module 4 heating/cooling asymmetry therefore propagates directly into the
feedback behaviour: a gain that is comfortable when heating is nearly
inoperative when cooling. This is the concrete answer to what "small" means
here, and it is why L rather than K<sub>p</sub> is the quantity to reason
with.

**Small compared with what?** L = K<sub>p</sub>&chi;<sub>T,u</sub>. With
&chi;<sub>T,h</sub> = 0.50127, L = 1 arrives at K<sub>p</sub> = 1.995. So on
this apparatus K<sub>p</sub> &asymp; 2 is the natural dividing line between
weak and strong feedback, and it is a property of our TEC and insulation,
not a universal number.

Note the asymmetry carried over from Module 4: the *same* K<sub>p</sub> gives
L = 2.77&times; smaller when cooling, because &chi;<sub>T,c</sub> is that
much smaller. A gain that is comfortable heating is weak cooling.

---

## 3. Part 3: droop versus gain

Setpoint **30.0 &deg;C**, heating, so e<sub>0</sub> = 30.00 &minus; 21.54 =
**8.46 &deg;C**.

Open-loop PWM needed to hold it:

```
P_required = |T_set - T_amb| / |chi_T,h| = 8.46 / 0.50127 = 16.9 counts
```

### Proposed gain sequence, for instructor approval

Chosen so that P<sub>0</sub> = K<sub>p</sub>e<sub>0</sub> starts far below
P<sub>required</sub> and ends well above it, with L spanning both sides of 1,
and nothing starting clamped.

| K<sub>p</sub> (PWM/&deg;C) | L = K<sub>p</sub>&chi; | P<sub>0</sub> = K<sub>p</sub>e<sub>0</sub> | P<sub>0</sub>/P<sub>required</sub> | predicted droop (&deg;C) | predicted T<sub>ss</sub> (&deg;C) |
|---|---|---|---|---|---|
| 0.25 | 0.125 | 2.1 | 0.13 | 7.52 | 22.48 |
| 0.50 | 0.251 | 4.2 | 0.25 | 6.76 | 23.24 |
| 1.00 | 0.501 | 8.5 | 0.50 | 5.64 | 24.36 |
| 2.00 | 1.003 | 16.9 | 1.00 | 4.22 | 25.78 |
| 4.00 | 2.005 | 33.8 | 2.01 | 2.82 | 27.18 |
| 8.00 | 4.010 | 67.7 | 4.01 | 1.69 | 28.31 |

**The reasoning, for the record.** P<sub>0</sub> is what the controller asks
for at the very first sample, before the plate has moved. Starting with
P<sub>0</sub> far below P<sub>required</sub> guarantees the loop cannot even
reach the setpoint, which makes the droop large and easy to measure. Ending
above it puts the loop in the regime where droop is small and the
1/(1+L) prediction is being tested where it is hardest.

**A prediction worth checking as you go.** At steady state P =
K<sub>p</sub>&times;droop, and that product should approach
P<sub>required</sub> = 16.9 from below as L grows: 1.9, 3.4, 5.6, 8.4, 11.3,
13.5 counts for the six gains. The loop always ends up asking for nearly the
same PWM; what changes is how much error it needs in order to ask.

### Measured, 30 September 2026

All six settled by the drift criterion: net change over the last 60 s no
larger than the 0.16 &deg;C noise floor. T<sub>ss</sub> is the mean of that
final minute.

| K<sub>p</sub> | L | T<sub>ss</sub> (&deg;C) | predicted (&deg;C) | droop (&deg;C) | predicted | ratio | final PWM | K<sub>p</sub>&times;droop |
|---|---|---|---|---|---|---|---|---|
| 0.25 | 0.125 | 22.34 | 22.48 | 7.66 | 7.52 | 1.019 | 2 | 1.9 |
| 0.50 | 0.251 | 23.06 | 23.24 | 6.94 | 6.76 | 1.026 | 3 | 3.5 |
| 1.00 | 0.501 | 24.50 | 24.36 | 5.50 | 5.64 | 0.976 | 6 | 5.5 |
| **2.00** | **1.003** | **25.75** | **25.78** | **4.25** | **4.22** | **1.006** | 8 | 8.5 |
| 4.00 | 2.005 | 27.18 | 27.18 | 2.82 | 2.82 | 1.002 | 11 | 11.3 |
| 8.00 | 4.010 | 28.33 | 28.31 | 1.67 | 1.69 | 0.989 | 13 | 13.4 |

**Mean ratio 1.003, standard deviation 0.017, worst point 2.6% off**, across
a 32-fold range of gain. The prediction was made from the Module 4
susceptibility before any of these runs and was not fitted to them.

Trace: `data/module_05/kp_sweep_full_run.csv` holds the whole sweep;
`kp_0p25_run.csv` is the low-gain example on its own.

### Three things the table shows that the graph does not

**1. L = 1 does what it says.** At K<sub>p</sub> = 2.00, L = 1.003 and the
measured droop is 4.25 &deg;C out of e<sub>0</sub> = 8.46 &deg;C. That is
**50.2% of the initial error surviving** against a predicted 50%. The
clearest single demonstration of 1/(1+L) in the set.

**2. The last column is an independent check.** At steady state the
commanded PWM must equal K<sub>p</sub>&times;droop, and it does at every
gain to within one count. This uses no droop model at all, so it confirms
the loop really had settled rather than being caught mid-approach.

It also shows the mechanism directly: that column climbs 1.9, 3.5, 5.5, 8.5,
11.3, 13.4 toward **P<sub>required</sub> = 16.9**, the open-loop PWM needed
to hold 30 &deg;C. The loop is always converging on the same command; what
changes with gain is how much error it needs in order to ask for it. Droop
does not vanish because the plate still needs those counts, and the only way
P control can request them is to sit below the setpoint.

**3. Noise amplification arrived exactly where predicted.** At K<sub>p</sub>
= 4 the command sat at 11 with **zero** variation over the last minute. At
K<sub>p</sub> = 8 it moved between 13 and 14, standard deviation 0.28 counts.
Predicted from the noise floor: K<sub>p</sub> &times; 0.16 &deg;C = 1.3
counts. This is the first gain at which the controller is visibly chasing
measurement noise rather than temperature, and it is the effect that
eventually limits useful gain.

### Closed-loop speed

&tau;<sub>cl</sub> = &tau;/(1+L) with &tau; = 70 s from Module 4, so the loop
should also get faster as the gain rises: 62 s at K<sub>p</sub> = 0.25 down
to 14 s at K<sub>p</sub> = 8. The runs bore this out, the later points
settling in about 100 s where the first took over 250 s. Higher gain buys
both a smaller droop and a quicker approach; what it costs is noise.

---

## 4. Part 4: predicted versus measured droop

![droop versus gain](../figures/module_05/droop_vs_gain.png)

Measured droop on the unfitted 1/(1+L) curve. The second axis is L, since L
is what the physics depends on; K<sub>p</sub> is only how it is dialled in.
The dotted line at e<sub>0</sub> = 8.46 &deg;C is the no-feedback limit the
curve approaches as L &rarr; 0.

---

## 4. Part 4: predicted versus measured droop

```
T = T_amb + chi_T,h * P        P = Kp (T_set - T)

  =>   T_set - T = (T_set - T_amb) / (1 + chi_T,h * Kp)

fractional droop:   (T_set - T_ss)/(T_set - T_amb) = 1/(1 + L)
```

The product &chi;<sub>T,h</sub>K<sub>p</sub> is dimensionless:
(&deg;C/count)(count/&deg;C) = 1.

Regenerate with `python3 python/plot_droop.py`.

**Where the model and the data part company: nowhere that matters.** Mean
ratio 1.003 with a spread of 1.7%, and the residuals change sign across the
range rather than trending, so there is no systematic bias to report. The
scatter is comparable to the 0.16 &deg;C noise floor divided by the droop,
which is 2% at the largest droop and 10% at the smallest.

If the residuals are instead attributed entirely to the susceptibility, the
&chi; that best fits all six is 0.4966 against the Module 4 open-loop value
of 0.50127, about 1% lower. That is within the scatter and is not claimed as
a result; it is recorded because it is the right quantity to look at if a
later data set does show a trend.

*To record: measured against predicted, and where they part company.*

---

## 5. Part 5: high-gain response

| K<sub>p</sub> | Settles? | Mean T (&deg;C) | Amplitude (&deg;C) | Period (s) | Frequency (Hz) | Saturation? |
|---|---|---|---|---|---|---|
| | | | | | | |

Amplitude defined as **half the peak-to-peak excursion** of the settled
oscillation, measured after any initial transient has passed. State this in
the note rather than leaving it implicit.

Do not assume it must oscillate. If it does not within the approved range,
report the highest gain tested and describe how that response differs from
the low-gain one.

---

## 6. Part 6: interpretation

### The one-lump model

```
C dT/dt = Pu*Kp*(T_set - T) - H*(T - T_amb)
```

with C the thermal capacity (J/K), P<sub>u</sub> the TEC thermal power per
signed PWM count (W/count), and H the passive conductance to the room (W/K).

### Student derivation, required for A3

**(1) Why the lump cannot stay at a non-ambient setpoint.** At T =
T<sub>set</sub> the error is zero, so the commanded TEC flow is zero, but
H(T<sub>set</sub> &minus; T<sub>amb</sub>) is not: the room is still pulling
the lump back. With no TEC flow to oppose it the lump drifts toward ambient,
the error grows, and the controller responds. It settles where the two
balance. Setting dT/dt = 0 and solving:

```
Pu*Kp*(T_set - T) = H*(T - T_amb)
T_set - T = (T_set - T_amb) / (1 + Pu*Kp/H)
```

which is the Part 4 result with **&chi;<sub>T,u</sub> = P<sub>u</sub>/H**.
The two models agree provided P<sub>u</sub> and H are constant over the
range, the lump is at one uniform temperature, and there is no saturation.

**(2) &chi;<sub>T,u</sub> = P<sub>u</sub>/H, with units.** Open the loop and
treat u as an independent input. At steady state 0 = P<sub>u</sub>u &minus;
H(T &minus; T<sub>amb</sub>), so T &minus; T<sub>amb</sub> =
(P<sub>u</sub>/H)u and &chi;<sub>T,u</sub> = dT/du = P<sub>u</sub>/H. Units:
(W/count)/(W/K) = K/count. Correct.

- P<sub>u</sub> doubles &rarr; &chi; doubles. Stronger actuator, more
  temperature per count.
- H doubles &rarr; &chi; halves. Better coupling to the room fights the TEC.
- **C doubles &rarr; &chi; unchanged.** C does not appear in the steady-state
  ratio at all. It multiplies dT/dt, so it sets how long the approach takes
  (&tau;<sub>cl</sub> = C/(H + P<sub>u</sub>K<sub>p</sub>)) and nothing about
  where the approach ends. Thermal capacity is a transient property.

**(3) L for our gains, and 1/(1+L) against measurement.** Table in Part 3,
comparison to be filled in after the runs.

### First-order expectation

&theta; = T &minus; T<sub>ss</sub> obeys d&theta;/dt = &minus;&theta;/&tau;<sub>cl</sub>
with &tau;<sub>cl</sub> = C/(H + P<sub>u</sub>K<sub>p</sub>), so
&theta;(t) = &theta;(0)e<sup>&minus;t/&tau;<sub>cl</sub></sup>. This decays
monotonically and **cannot oscillate at any gain.** Note also that
&tau;<sub>cl</sub> falls as K<sub>p</sub> rises: higher gain should settle
*faster* as well as closer.

So oscillation, if we see it, falsifies the one-lump picture rather than the
control law. Candidates, in the order worth checking:

- **Thermal lag between TEC and thermistor.** The sensor sits in the plate,
  not on the module face. Delay plus gain is the classic route to
  oscillation, and a pure first-order model has no delay.
- **A second thermal mass**, the plate and the coolant block, making the
  system second order.
- **Discrete sampling at 1 Hz** against a 70 s time constant. Usually
  harmless at this ratio, but it is a genuine phase lag.
- **Measurement noise amplified by gain.** 0.16 &deg;C of noise at
  K<sub>p</sub> = 50 is 8 counts of command jitter.
- **Saturation**, which makes the loop nonlinear and can sustain a limit
  cycle the linear model does not predict.

---

## 7. Evidence checklist for A3 and C4

- [ ] low-gain sign test, both directions
- [ ] gain range and the calculation justifying it *(table above, needs instructor approval)*
- [ ] droop table with dimensions
- [ ] high-gain response table
- [ ] measured and predicted droop on one graph
- [ ] the Part 4 &harr; Part 6 derivation *(drafted above, needs our numbers)*
- [ ] representative low- and high-gain traces
- [ ] exact filenames of controller, sketch and raw data
- [ ] short written explanation of droop and of the oscillation result

---

## 8. Open items

- Instructor approval of the gain range before running it
- Everything marked *to record*
- Carried over from Module 4: the blank numeric rows in the Part 1 pre-power
  checklist
