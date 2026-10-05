# Module 5: P-only temperature control

Naidu / Cohen, 30 September 2026. Evidence for A3 and C4. No separate paper.

**Code.** [`python/tec_p_control_gui.py`](../../python/tec_p_control_gui.py) (controller),
[`arduino/module_04/tec_open_loop_safety`](../../arduino/module_04/tec_open_loop_safety/tec_open_loop_safety.ino) (unchanged; keeps the 60 C software limit),
[`python/plot_droop.py`](../../python/plot_droop.py) (figure).
Data in `data/module_05/`, figure in `docs/figures/module_05/`.

**From Module 4:** &chi;<sub>T,h</sub> = 0.50127 &deg;C/count,
&#124;&chi;<sub>T,c</sub>&#124; = 0.18091, T<sub>amb</sub> = 21.54 &deg;C,
&tau; = 62.9 &plusmn; 5.0 s, noise floor 0.16 &deg;C p-p.

The time constant is the one fitted in Module 6 Part 3
([`python/estimate_tau.py`](../../python/estimate_tau.py)) from the eight
constant-command steps in `data/module_04/full_run.csv`. The 70 s used at the
bench to decide how long to wait was a working estimate; every &tau;<sub>cl</sub>
below uses the fitted value.

---

## Before class

| Item | Status |
|---|---|
| Module 4 susceptibility identified near room temperature | &chi;<sub>T,h</sub> = 0.50127, &#124;&chi;<sub>T,c</sub>&#124; = 0.18091 &deg;C/count |
| Arduino safety shutdown still works | **Re-tested and passed, 5 October 2026.** Software limit lowered to about 30 &deg;C, plate warmed past it, latch tripped and both PWM outputs went to zero; limit then restored to 60 &deg;C. Same method as the Module 4 Part 1 check. Team test, not witnessed by the instructor this time, so Module 4's witnessed trip remains the stronger record. |
| Setpoint chosen, e<sub>0</sub> calculated | 30.0 &deg;C, e<sub>0</sub> = 30.0 &minus; 21.54 = 8.46 &deg;C |
| Sign convention recorded | positive u heats, negative u cools, Arduino receives P = &#124;u&#124; |

---

## Pre-class questions

**1. T<sub>set</sub> = 30, T = 25: heat or cool?** Heat. e = +5 &deg;C so
u = K<sub>p</sub>e > 0, and positive u selects heating.

**2. Units of K<sub>p</sub>?** PWM counts per &deg;C. That is why a bare
K<sub>p</sub> cannot be called large or small; the dimensionless combination
is L = K<sub>p</sub>&chi;.

**3. Why does P control need a nonzero error?** Because the output *is* the
error times a constant. At the setpoint it commands nothing, but a lump above
room temperature keeps losing heat, so something must supply a steady
counter-flow. The standing error is the loop's only means of asking for it.

**4. Symptoms of K<sub>p</sub> too large?** Overshoot then undershoot;
sustained oscillation; PWM slamming between large heat and cool values or
saturating; chasing measurement noise. The one-lump model is first order and
cannot oscillate, so oscillation would indicate lag, a second mass, sampling,
or saturation.

---

## 1. Controller

Control law, one update per measurement (**1.97 Hz measured**, set by the
Arduino's 500-sample average and its 500 ms reporting interval):

```python
e = self.setpoint - temperature_c
u = self.kp * e
heating = u >= 0.0
p = max(0, min(255, int(round(abs(u)))))
```

**Deviation worth stating.** Part 1 asks for an average of *about 1000* raw
thermistor readings. `sampleCount` was reduced from 1000 to 500 on the morning
of 30 September, before any Module 5 data was taken, so **every run in this
note averages 500**. That is inside the 100 to 1000 band Module 6 Part 3 states
for Modules 2 to 5, but it is half what Modules 4 and 5 ask for. The effect is
a factor &radic;2 in the noise on a single reading, which is consistent with
the 0.16 &deg;C floor used throughout. Restore 1000 before the next run.

Reporting is at 2 Hz rather than 1, which the module permits: it warns only
about being slower than once a second.

The GUI plots all five quantities Part 1 lists: temperature, the setpoint as a
line on the same axes, error on its own axes, PWM magnitude, and direction as
the red/blue colouring of the PWM trace.

Python decides what to ask for; the Arduino decides what to do. The Module 4
software limit is unreachable from the GUI, so a runaway gain can oscillate or
saturate the loop but cannot defeat the interlock. If the sketch latches, the
GUI sees `SAFETY SHUTDOWN` and switches P control off.

---

## 2. Sign test, K<sub>p</sub> = 0.25

| Setpoint | Expected | Result, counted from `sign_test_and_sweep.csv` |
|---|---|---|
| 30 &deg;C | positive error &rarr; heating | **PASS**, 603 samples at K<sub>p</sub> = 0.25, all HEAT |
| 15 &deg;C | negative error &rarr; cooling | **PASS**, 407 samples at K<sub>p</sub> = 0.25, all COOL |

Across every gain run at 30 &deg;C before the cooling test, 3064 samples, all
HEAT. An earlier version of this table gave 3064 as the K<sub>p</sub> = 0.25
count and 394 for cooling; neither matched the file, and both are corrected
above. The full session log continues the cooling run past the end of that
snapshot, to 431 samples, all COOL.

**Order of events.** The cooling half of the sign test was run *after* the
heating sweep, not before it. At t = 1598 s the setpoint was changed from 30 to
15 &deg;C while K<sub>p</sub> was still 8, and K<sub>p</sub> was then typed
down to 0.25 over the next 18 s. One sample at that setpoint change reports a
negative error with HEAT, at K<sub>p</sub> = 8: the Arduino echoing the
previous command before its next report. One sample of pipeline delay, not a
sign error.

**The same K<sub>p</sub> gives L = 0.125 heating but 0.045 cooling**, 2.77x
weaker, because &chi;<sub>T,c</sub> is that much smaller. The Module 4
asymmetry propagates straight into the feedback.

Data: `sign_test_and_sweep.csv`, and the complete record in
`session_2026-09-30_full_log.csv`.

---

## 3. Droop versus gain

Setpoint 30.0 &deg;C, e<sub>0</sub> = 8.46 &deg;C,
P<sub>required</sub> = 8.46/0.50127 = **16.9 counts** open-loop.

Gains chosen so P<sub>0</sub> = K<sub>p</sub>e<sub>0</sub> starts far below
P<sub>required</sub> and ends well above, with L spanning both sides of 1 and
nothing starting clamped.

Steady state: drift over the final 60 s no larger than the 0.16 &deg;C noise
floor. T<sub>ss</sub> is the mean of that minute.

Setpoint 30.0 &deg;C for every row. Predicted
P<sub>0</sub> = K<sub>p</sub>e<sub>0</sub> is what the gain would ask for
starting from ambient.

| K<sub>p</sub> | pred. P<sub>0</sub> | P<sub>0</sub>/P<sub>req</sub> | L | T<sub>ss</sub> | pred. T<sub>ss</sub> | droop | pred. droop | ratio | final PWM | K<sub>p</sub>&times;droop |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.25 | 2.1 | 0.13 | 0.125 | 22.34 | 22.48 | 7.66 | 7.52 | 1.019 | 2 | 1.9 |
| 0.50 | 4.2 | 0.25 | 0.251 | 23.06 | 23.24 | 6.94 | 6.76 | 1.026 | 3 | 3.5 |
| 1.00 | 8.5 | 0.50 | 0.501 | 24.50 | 24.36 | 5.50 | 5.64 | 0.976 | 6 | 5.5 |
| **2.00** | **16.9** | **1.00** | **1.003** | **25.75** | **25.78** | **4.25** | **4.22** | **1.006** | 8 | 8.5 |
| 4.00 | 33.8 | 2.00 | 2.005 | 27.19 | 27.18 | 2.81 | 2.82 | 0.998 | 11 | 11.2 |
| 8.00 | 67.7 | 4.00 | 4.010 | **28.43** | 28.31 | **1.57** | 1.69 | **0.930** | 13 | 12.6 |
| 16.00 | 135.4 | 8.01 | 8.020 | 29.10 | 29.06 | 0.90 | 0.94 | 0.960 | 14 | 14.4 |
| 32.00 | 270.7 | 16.02 | 16.041 | 29.54 | 29.50 | 0.46 | 0.50 | 0.927 | 15 | 14.7 |

**Every T<sub>ss</sub> above is recomputed by one method**: the mean of the final
60 s of that gain's run in `session_2026-09-30_full_log.csv`, the complete
session record. Two values changed from earlier versions of this table:

- **K<sub>p</sub> = 8: 28.33 &rarr; 28.43.** The old value matches the final
  60 s of `kp_sweep_full_run.csv` (28.335), a snapshot that stops 114 s into
  this 278 s run. The plate was still rising: 28.32 at 60 s, 28.37 at 140 s,
  28.43 from 180 s onward, flat thereafter. The ratio to prediction moves from
  0.989 to 0.930, **away from** the model.
- **K<sub>p</sub> = 4: 27.18 &rarr; 27.19.** 27.18 is the most common single
  reading in the final minute; the mean of that minute is 27.19. The run is
  the shortest of the sweep, 166 s, and was still rising 0.04 &deg;C per minute
  when the gain was changed, inside the 0.16 &deg;C criterion.

Final PWM is the median command over the same final minute. Earlier versions
listed 27 and 31 for K<sub>p</sub> = 16 and 32; those were the **peak**
commands at the start of each run, not the final ones.

**The range does what Part 3 asks.** P<sub>0</sub> starts at 0.13 of
P<sub>required</sub> and ends at 16 times it, crossing 1 exactly at
K<sub>p</sub> = 2 where L = 1. Only the top row would start outside 0 to 255,
and it did not, because it was not started from ambient: at K<sub>p</sub> = 32
the run began at 29.09 &deg;C, 0.91 &deg;C from setpoint, and its first command
was 29 counts, not 271. That is why saturation was never reached.

**How each gain was entered.** K<sub>p</sub> = 0.5 through 8 and 32 were each
entered from the previous gain's steady state. The GUI's gain field steps in
0.25, so between gains the log shows a few samples at intermediate values while
the new one was set: none before 0.5, two before 1 and 2, three before 4, one
before 32, and seven before 8, about 3.5 s during which the plate rose from
27.19 to 27.36 &deg;C. K<sub>p</sub> = 0.25 started from 21.09 &deg;C at the
beginning of the session. **K<sub>p</sub> = 16 did
not** start from a steady state: it followed the 15 &deg;C cooling test and a
49 s run at K<sub>p</sub> = 9 that never settled, and began at 28.36 &deg;C. It
still settled, final-minute drift +0.002 &deg;C, so its T<sub>ss</sub> stands.
K<sub>p</sub> = 9 is excluded from every table: it ran 49 s and was still
rising 5.7 &deg;C per minute when the gain was changed.

**Agreement with the model, all eight gains: measured/predicted droop 0.980
&plusmn; 0.039** (sample standard deviation), range 0.927 to 1.026. The
prediction uses the Module 4 susceptibility and is not fitted.

**It is not uniform.** The five gains up to K<sub>p</sub> = 4 average 1.005
&plusmn; 0.020. **The three gains from K<sub>p</sub> = 8 up are all low, by
7.0%, 4.0% and 7.3%**, mean 0.939. Section 4 looks at whether that is a real
effect; the short answer is that this data cannot tell.

**At L = 1.003 the droop is 4.25 &deg;C of an 8.46 &deg;C error: 50.2%
surviving against 50% predicted.**

**The last column is a self-consistency check, not an independent one.**
Earlier drafts of this note called it independent evidence. It is not: the
controller computes `p = round(abs(kp * e))`, so PWM = K<sub>p</sub>&times;droop
is an identity that holds at every instant whether or not the loop has settled,
and it cannot fail. What it does verify is that the command, the error and the
logging agree, which is worth confirming and is all it confirms.

It is still useful for showing the mechanism. That product climbs from 1.9
at K<sub>p</sub> = 0.25 to 14.7 at K<sub>p</sub> = 32, toward
P<sub>required</sub> = 16.9: the loop converges on roughly the same command,
and gain only changes how much error it needs in order to ask for it. That
part is a statement about the apparatus.

**Data.** `session_2026-09-30_full_log.csv` is the complete record of the
session, 5417 rows, copied from the GUI's live file on 5 October before the
next launch could overwrite it. Every value is unchanged. The GUI writes CRLF
line endings and the repository's `.gitattributes` stores text with LF, so
the original on the lab laptop hashes to SHA-256 4aa67513&hellip;b949ea and the
copy in Git to c4a031c4&hellip;3cea75; the difference is the line endings only.
The `kp_*_run.csv` and `sign_test_and_sweep.csv` files are earlier snapshots
of the same log; each is an exact prefix of it and stops partway through.

---

## 4. Predicted versus measured

```
T = T_amb + chi*P,   P = Kp(T_set - T)
  =>  T_set - T = (T_set - T_amb)/(1 + chi*Kp)
  =>  fractional droop = 1/(1 + L)
```

chi*Kp is dimensionless: (&deg;C/count)(count/&deg;C) = 1.

![droop versus gain](../figures/module_05/droop_vs_gain.png)

Regenerate with `python3 python/plot_droop.py`. Measured/predicted 0.980
&plusmn; 0.039 over all eight gains, rms residual 0.10 &deg;C.

### Are the high-gain points really low?

An earlier version of this note said the residuals change sign and show no
bias. With the corrected K<sub>p</sub> = 8 value that is no longer true, so it
needs looking at properly. The miss, predicted droop minus measured:

| K<sub>p</sub> | miss | as a fraction of the droop | final-minute p-p |
|---|---|---|---|
| 0.25 | &minus;0.14 &deg;C | +1.9% | 0.04 &deg;C |
| 0.50 | &minus;0.18 &deg;C | +2.6% | 0.05 &deg;C |
| 1.00 | +0.13 &deg;C | &minus;2.4% | 0.04 &deg;C |
| 2.00 | &minus;0.03 &deg;C | +0.6% | 0.02 &deg;C |
| 4.00 | +0.01 &deg;C | &minus;0.2% | 0.05 &deg;C |
| 8.00 | +0.12 &deg;C | &minus;7.0% | 0.02 &deg;C |
| 16.00 | +0.04 &deg;C | &minus;4.0% | 0.02 &deg;C |
| 32.00 | +0.04 &deg;C | &minus;7.3% | 0.02 &deg;C |

Two readings of the same numbers, and the data does not choose between them:

- **As a fraction of the droop**, the three high-gain points are all low by 4
  to 7%, well above their 0.02 &deg;C within-minute scatter.
- **In degrees**, their misses of 0.04 to 0.12 &deg;C are no larger than the
  run-to-run scatter at low gain, which reaches 0.18 &deg;C with both signs.
  A run-to-run offset of about 0.1 &deg;C is a small fraction of a 7 &deg;C
  droop and a large fraction of a 0.5 &deg;C one, so it would produce exactly
  this pattern without anything changing at high gain.

Three points on one side is suggestive, not conclusive: if the signs were
random, all three landing on the same side would happen one time in four. What
the data does establish is that **run-to-run reproducibility is about 0.1 to
0.2 &deg;C**, ten times the within-minute scatter, and that is the real limit
on how well the droop model can be tested here.

What could set that run-to-run offset is not measured. T<sub>amb</sub> is a
single value taken in Module 4 before this sweep, and room temperature was not
logged during it. The K<sub>p</sub> = 8 run also shows a slow component, rising
from 28.32 to 28.43 &deg;C between 60 s and 180 s after it had apparently settled, which a second
thermal time scale or a drifting ambient would both produce. Neither is
established by this data.

---

## 5. High gain

| K<sub>p</sub> | L | Settles? | mean T | predicted | Amplitude | Period | Frequency | Overshoot | Saturation? |
|---|---|---|---|---|---|---|---|---|---|
| 8.00 | 4.01 | yes | 28.43 | 28.31 | none | n/a | n/a | none | no, PWM peaked at 21 |
| 16.00 | 8.02 | yes | 29.10 | 29.06 | none | n/a | n/a | none | no, PWM peaked at 27 |
| 32.00 | 16.04 | yes, within the first 210 s | 29.54 | 29.50 | none | n/a | n/a | +0.04 &deg;C at 7 s, then &minus;0.05 &deg;C at 12 s | no, PWM peaked at 31 |

Period and frequency are not applicable: there was no sustained oscillation at
any gain to measure them on.

**No sustained oscillation and no saturation at the highest gain tested.** Each
run held at least 22 closed-loop time constants, final-60 s spread 0.02
&deg;C, and **zero direction reversals**: all 547, 865 and 827 samples at
K<sub>p</sub> = 8, 16 and 32 are HEAT. Amplitude is defined as half the
peak-to-peak excursion of the settled response; there was none to measure.

**K<sub>p</sub> = 32 overshoots and then undershoots.** Settled at 29.540
&deg;C, the trace rises to 29.58 at 7 s (+0.04 &deg;C), falls through the
settled value at about 9 s, reaches 29.49 at 12 s (&minus;0.05 &deg;C), and
does not return to 29.54 until about 28 s. The return from below is slower
than the overshoot, so this is not a symmetric damped oscillation with a single
period. Both excursions are 4 to 5 steps of the 0.01 &deg;C logging resolution
and 2 to 2.5 times the settled peak-to-peak, so they are resolved, but not by a
wide margin. Nothing comparable appears at K<sub>p</sub> = 16, whose largest
excursion above its settled value is +0.01 &deg;C. See
[`docs/figures/module_05/p_control_traces.png`](../figures/module_05/p_control_traces.png).

This matters because the one-lump model **forbids** it: its single eigenvalue
is real and negative, so the deviation keeps its sign and can neither overshoot
nor cross back. Seeing both is evidence that the model is missing a state.
Thermal lag between the TEC face and the thermistor is one candidate, which
would only show once &tau;<sub>cl</sub> = &tau;/(1+L) = 3.7 s is short enough to
approach it. Discrete sampling is another: at 1.97 Hz that is about 7 samples
per closed-loop time constant. Telling them apart needs a faster log than this
one.

### The K<sub>p</sub> = 32 run stops being valid at about 216 s

From about 216 s after K<sub>p</sub> = 32 was applied, the plate falls
steadily while the commanded heating rises: 29.54 &deg;C at 216 s, 28.52 at
230 s, 25.35 at 420 s, with the command climbing from 15 to 149 counts and
never changing direction. **The plate stopped following the command.** The
controller behaved correctly throughout, asking for more heat as the error
grew; the heat did not arrive.

What the log does establish:

- **The Arduino was driving the bridge.** The `pwm` and `heat_cool` columns are
  the Arduino's own report of what it is applying
  (`python/tec_p_control_gui.py`, line 424), not Python's request. It reported
  149 counts of heating at the end.
- **It was not a safety trip.** A latch makes the sketch print `SAFETY
  SHUTDOWN`, on which the GUI switches P control off (lines 415 to 419).
  `p_enabled` stays 1 to the last row, and the plate never approached 60
  &deg;C.
- **It does not fall like the zero-command decays of Module 4.** With
  &tau; = 62.9 s toward 21.54 &deg;C, the plate would have been at 23.65
  &deg;C 84 s after onset and 21.85 &deg;C after 204 s; it was at 26.42 and
  25.35. It cooled several times more slowly than that. Whether that means
  some heat was still arriving, or that the unpowered module conducts heat
  differently from one held at zero command, the log cannot say.

So the loss is downstream of the Arduino: the supply, the bridge, or the TEC
wiring. From the file's modification time the fall began at about 11:39 on
30 September and the log ends at 11:42. **The cause is not established by the
data and should be filled in from memory if anyone remembers what happened at
the bench then.**

Every K<sub>p</sub> = 32 number in this note therefore comes from the first
210 s only. The earlier versions happened to use a snapshot that ended at
110 s, inside the valid window, so the settled value 29.54 does not change.

**Saturation was not reached.** Each gain was entered from the previous steady
state, so the steps were small. At K<sub>p</sub> = 32 the run began 0.91 &deg;C
from setpoint and asked for 29 counts. From ambient it would ask for 271,
clamping at 255 until the error fell below 7.97 &deg;C. That is a different
experiment, since the loop is nonlinear while clamped and 1/(1+L) does not
apply. Identified for a supervised opportunity, not claimed as done.

**How high gain differs from low:** mostly in speed and offset.
&tau;<sub>cl</sub> = &tau;/(1+L) falls from 55.9 s at K<sub>p</sub> = 0.25 to
7.0 s at K<sub>p</sub> = 16 and 3.7 s at K<sub>p</sub> = 32, while droop falls from
7.66 to 0.46 &deg;C. Up to K<sub>p</sub> = 16 the approach has no resolved
overshoot. At K<sub>p</sub> = 32 it does, as described above. If thermal lag is
the cause, that places the lag between the two closed-loop time constants,
roughly 4 to 7 s; if sampling is the cause, it says nothing about lag.

Figure: `docs/figures/module_05/p_control_traces.png`, built by
`python/plot_p_control_traces.py` from `session_2026-09-30_full_log.csv`.
Raw data: `session_2026-09-30_full_log.csv`, the complete record; the
`kp_*_run.csv` files are earlier snapshots of it.

### Feedback suppresses the temperature noise

Peak-to-peak temperature over the final 60 s was **0.02 to 0.05 &deg;C at every
gain**, against **0.16 &deg;C** measured open-loop at rest.

This is the same 1/(1+L) acting on a different input: the factor that leaves a
fraction of the setpoint error behind also leaves only that fraction of any
slow disturbance. **Droop and disturbance rejection are two faces of one
number**, and the offset cannot be reduced without also quieting the output.

It explains a forecast that missed usefully. Command jitter at K<sub>p</sub> =
16 was predicted as K<sub>p</sub>&times;0.16 = 2.6 counts. Over the final
minute it was 0.41 counts standard deviation, never outside 14 to 15, because
the prediction used the open-loop noise when the loop had already suppressed
the fluctuation the controller sees. At K<sub>p</sub> = 32 the same holds: 0.31
counts standard deviation, 14 to 15. In both, the logged temperature takes
only three adjacent values 0.01 &deg;C apart across the minute, a quarter of
one ADC count (0.080 &deg;C at this temperature), and the command is simply
following that one-step flicker.

### Not attempted

**K<sub>p</sub> = 400**, used on another bench. L = 200, the command clamps
until the error is within 255/400 = 0.64 &deg;C, and inside that band one ADC
count (0.079 &deg;C) swings the command 32 counts while noise swings it 64.
No proportional region remains: it is a relay controller. Since the plate slews
about 1.8 &deg;C/s at full drive (Module 3) and the loop updates every 0.51 s,
it moves about 0.9 &deg;C between updates and cannot stop inside a 0.64 &deg;C
band, so a limit cycle follows. Outside the range justified above, and it would
reverse the full drive current through the Peltier on every swing. Not
measured on this bench; this is a prediction, not a result.

---

## 6. Interpretation

### One-lump model

```
C dT/dt = Pu*Kp*(T_set - T) - H*(T - T_amb)
```

**(1) Why the lump cannot stay at a non-ambient setpoint.** At T = T<sub>set</sub>
the commanded TEC flow is zero but H(T<sub>set</sub>&minus;T<sub>amb</sub>) is
not, so the lump drifts toward ambient, the error grows, and the controller
responds. Setting dT/dt = 0:

```
Pu*Kp*(T_set - T) = H*(T - T_amb)
T_set - T = (T_set - T_amb)/(1 + Pu*Kp/H)
```

which is the Part 4 result with **&chi;<sub>T,u</sub> = P<sub>u</sub>/H**. The
two agree provided P<sub>u</sub> and H are constant over the range, the lump is
at one uniform temperature, and there is no saturation.

**(2) &chi; = P<sub>u</sub>/H, with units.** Open the loop: at steady state
0 = P<sub>u</sub>u &minus; H(T&minus;T<sub>amb</sub>), so &chi; = dT/du =
P<sub>u</sub>/H, equivalently **P<sub>u</sub> = H&chi;<sub>T,u</sub>**. Units
(W/count)/(W/K) = K/count.

*Relating this to the Module 4 slopes.* For heating the Arduino receives
u = P &gt; 0, so &chi;<sub>T,h</sub> = dT/dP = P<sub>u</sub>/H. For cooling it
still receives the positive magnitude P = &minus;u, so dT/dP =
&minus;P<sub>u</sub>/H and the cooling magnitude is
&#124;&chi;<sub>T,c</sub>&#124; = P<sub>u</sub>/H. **The one-lump model with a
single P<sub>u</sub> therefore predicts the two magnitudes to be equal.** Ours
are 0.50127 and 0.18091, a factor of 2.77 apart. That is not a failure of the
algebra, it is Module 4's result arriving here: Peltier transport reverses with
the current and Joule heating does not, so the two add when heating and oppose
when cooling. A single P<sub>u</sub> is only valid within one direction, and
every droop prediction below uses the heating value because every run sits
above ambient.

- P<sub>u</sub> doubles &rarr; &chi; doubles
- H doubles &rarr; &chi; halves
- **C doubles &rarr; &chi; unchanged.** C does not appear in the steady-state
  ratio; it multiplies dT/dt, so it sets how long the approach takes
  (&tau;<sub>cl</sub> = C/(H + P<sub>u</sub>K<sub>p</sub>)) and nothing about
  where it ends. Thermal capacity is a transient property.

**(3) L and 1/(1+L).**

| K<sub>p</sub> | L | measured fraction | 1/(1+L) | ratio |
|---|---|---|---|---|
| 0.25 | 0.125 | 0.905 | 0.889 | 1.019 |
| 0.50 | 0.251 | 0.820 | 0.800 | 1.026 |
| 1.00 | 0.501 | 0.650 | 0.666 | 0.976 |
| 2.00 | 1.003 | 0.502 | 0.499 | 1.006 |
| 4.00 | 2.005 | 0.332 | 0.333 | 0.998 |
| 8.00 | 4.010 | 0.186 | 0.200 | 0.930 |
| 16.00 | 8.020 | 0.106 | 0.111 | 0.960 |
| 32.00 | 16.041 | 0.054 | 0.059 | 0.927 |

**Only K<sub>p</sub> = 0.25 and 0.50 genuinely have small gain**, L < 0.3, with
over 80% of the error surviving. K<sub>p</sub> = 1 and 2 are comparable; from 4
upward the feedback is strong and the fraction approaches 1/L. The
classification cannot be made from K<sub>p</sub> alone: K<sub>p</sub> = 2 is
comparable heating but weak cooling, where the same gain gives L = 0.36.

*The discrepancies.* The ratios run from 0.927 to 1.026. Up to L = 2 they
scatter both ways by up to 2.6%; from L = 4 up all three are low by 4 to 7%.
Section 4 works through this. In degrees, every miss is 0.18 &deg;C or less,
which is the run-to-run reproducibility of this session, and that is too
coarse to say whether the high-gain points are genuinely low or are a ~0.1
&deg;C offset showing up large against a small droop. The directional
susceptibility is the heating one throughout, &chi;<sub>T,h</sub> = 0.50127,
because every run sits above ambient and every logged command is HEAT. An
earlier version of this paragraph attributed the scatter to room drift over a
two-hour session; the session lasted 46 minutes and room temperature was not
logged, so that was not supported and is withdrawn.

### First-order expectation

&theta; = T &minus; T<sub>ss</sub> obeys &theta;(t) = &theta;(0)e<sup>&minus;t/&tau;<sub>cl</sub></sup>
with &tau;<sub>cl</sub> = C/(H + P<sub>u</sub>K<sub>p</sub>). This decays
monotonically and **cannot oscillate at any gain**, and &tau;<sub>cl</sub>
falls as K<sub>p</sub> rises, so higher gain should settle both closer and
faster. Both were observed.

No sustained oscillation appeared at any gain. **At K<sub>p</sub> = 32 the
trace overshoots by 0.04 &deg;C and then undershoots by 0.05 &deg;C**
(section 5), which this model forbids outright: one state variable gives one
real negative eigenvalue, so &theta; keeps its sign while shrinking and the
trace cannot cross T<sub>ss</sub> at all. Something is therefore missing from
the one-lump picture, and it is the model rather than the control law that is
at fault. Candidates: thermal lag between the TEC face and the thermistor, a
second thermal mass, discrete sampling at 1.97 Hz against &tau;<sub>cl</sub> =
3.7 s, noise amplified by gain, or saturation making the loop nonlinear.
Saturation is ruled out, since the command peaked at 31 of 255 counts. The rest
is worked through in
[`module_06_pi_modeling.md`](module_06_pi_modeling.md) section 6.

---

## 7. Evidence for A3 and C4

- [x] sign test, both directions: Part 2
- [x] gain range and its justification: Part 3
- [x] dimensional droop table: Part 3
- [x] high-gain response table: Part 5
- [x] measured and predicted droop on one graph:
  `docs/figures/module_05/droop_vs_gain.png`
- [x] Part 4 to Part 6 derivation: Part 6
- [x] low- and high-gain strip-chart traces:
  `docs/figures/module_05/p_control_traces.png`, from
  `session_2026-09-30_full_log.csv`
- [x] filenames of controller, sketch and data: top of this note
- [x] explanation of droop and the oscillation result: Parts 3, 5, 6

**Open:**

- Instructor approval of the gain range was obtained retrospectively.
- Saturation was never reached, so the clamped regime is untested.
- **Why the K<sub>p</sub> = 32 run stops tracking at about 216 s** is not
  established (section 5). Only its first 210 s are used.
- `sampleCount` was 500 for this session where Part 1 asks for about 1000
  (section 1). Restore 1000 before the next run.
- Run-to-run reproducibility is about 0.1 to 0.2 &deg;C, and room temperature
  was not logged, so the 4 to 7% low droop at the three highest gains cannot be
  separated from an offset (section 4).
