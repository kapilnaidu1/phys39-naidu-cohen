# Module 6 Part I: P/PI control and lumped modeling

Naidu / Cohen, 5 October 2026. Guided modeling work feeding A3. No separate
paper for the module itself.

**Code.** [`python/estimate_tau.py`](../../python/estimate_tau.py) (Part 3),
[`python/simulate_one_lump.py`](../../python/simulate_one_lump.py) (Parts 4, 5, 7),
[`python/Lab_6_first_order_p_pi_simulation_realtime.py`](../../python/Lab_6_first_order_p_pi_simulation_realtime.py)
(the supplied program, used only to check our own; see section 9).
Figures in `docs/figures/module_06/`, console output in
`data/module_06/simulation_output.txt`. Part 7 on the apparatus:
[`python/tec_pi_control_gui.py`](../../python/tec_pi_control_gui.py),
[`python/plot_goldilocks_experiment.py`](../../python/plot_goldilocks_experiment.py),
[`python/sampling_delay_check.py`](../../python/sampling_delay_check.py)
(section 11).

**Measured parameters, all three carried in from earlier modules:**

| Symbol | Value | Where from |
|---|---|---|
| &chi;<sub>T,u</sub> = P<sub>u</sub>/H | 0.50127 &deg;C per PWM count | Module 4 heating branch |
| &tau; = C/H | 62.9 &plusmn; 5.0 s | Part 3 below |
| T<sub>amb</sub> | 21.54 &deg;C | Module 4 zero-command steady state |

**C, H and P<sub>u</sub> were never measured separately, and never need to
be.** Everything in this module depends only on the two ratios above. That is
the single most useful thing the dimensional analysis gives us, and section 9
shows it concretely: the supplied program asks for three numbers where the
physics has two, so one of them is free.

---

## Before class

The page asks only that these existing files can be located and opened, and
explicitly says not to make new work for this section.

| File | Path |
|---|---|
| Module 4 steady-state temperature vs PWM | `data/module_04/steady_state.csv`, `data/module_04/full_run.csv` |
| Module 5 droop vs gain | `data/module_05/droop.csv` |
| Module 5 trace at a stable gain | `data/module_05/kp_0p25_run.csv` |
| Module 5 trace near oscillation | `data/module_05/session_2026-09-30_full_log.csv`, K<sub>p</sub> = 32, first 210 s; the only run showing any overshoot |
| Python environment | numpy and matplotlib only; no scipy is needed by anything here |

---

## Pre-class questions

**1. What physical part of the apparatus stores heat?** The aluminium block
and heat exchanger, mainly, plus the TEC's own ceramic faces, the thermistor
and the mounting hardware. The one-lump model treats all of it as a single
mass at one temperature with C = mc<sub>p</sub>, which is the approximation
being tested, not an assumption that happens to be true.

**2. What paths let heat leave the measured block?** Conduction through the
TEC to the reservoir face and out through the exchanger; conduction along the
mounting bolts and the thermal-switch leads; convection to room air from the
exposed plate; radiation, small at 10 to 45 &deg;C. All of them are lumped
into the single conductance H, which is why H cannot be decomposed from our
data.

**3. What evidence suggests a thermal time constant?** Every open-loop step is
an exponential approach rather than a ramp or a jump. Eight constant-command
steps in `data/module_04/full_run.csv` fit
T = T<sub>&infin;</sub> + (T<sub>0</sub>&minus;T<sub>&infin;</sub>)e<sup>&minus;t/&tau;</sup>
with R<sup>2</sup> &gt; 0.998 and &tau; between 53 and 68 s, and the temperature starts
moving within 0.5 to 2 s of every command, which is what a first-order lag
does: an immediate start that slows as it approaches.

**4. Why does the algebraic droop model not predict oscillation?** Because it
contains no time derivative. It is the dT/dt = 0 limit of the balance, so it
can only say where the plate ends up, never how it gets there. Even the full
dynamic one-lump model cannot oscillate, for the stronger reason given in
section 6: one state variable gives one real eigenvalue.

---

## 1. Algebraic droop model, and a numerical check

Substituting u = K<sub>p</sub>(T<sub>set</sub>&minus;T) into the measured
open-loop relation T = T<sub>amb</sub> + &chi;u and collecting terms:

```
T_set - T = (T_set - T_amb) / (1 + chi*Kp),     L = chi*Kp
```

**Numerical check on one Module 5 run.** K<sub>p</sub> = 2.00,
T<sub>set</sub> = 30.0 &deg;C, T<sub>amb</sub> = 21.54 &deg;C:

```
L = 0.50127 * 2.00 = 1.0025
predicted droop = 8.46 / 2.0025 = 4.225 C   ->   T_ss = 25.78 C
measured  droop = 4.25 C                    ->   T_ss = 25.75 C
```

Agreement to 0.6%, 0.03 &deg;C. **One physical reason they may differ:**
T<sub>amb</sub> is a single value measured in Module 4, before this sweep, and
room temperature was not logged during it. The droop changes by
1/(1+L) = 0.50 &deg;C per degree of ambient, so an effective ambient just 0.05
&deg;C lower than 21.54 would account for the whole difference. With
run-to-run reproducibility of 0.1 to 0.2 &deg;C (Module 5 section 4), this one
run cannot resolve a difference this small.

---

## 2. The model in measured parameters

Dividing C dT/dt = P<sub>u</sub>u &minus; H(T&minus;T<sub>amb</sub>) by H:

```
dT/dt = (T_amb + chi*u - T) / tau,    chi = Pu/H [C/count],  tau = C/H [s]
```

Units check: (W/count)/(W/K) = K/count for &chi;, and (J/K)/(W/K) = s for
&tau;. Not a different model, just the form we can run.

Predictions this makes, all three from Module 5 section 6:
P<sub>u</sub> doubles and &chi; doubles; H doubles and &chi; halves; **C
doubles and &chi; is unchanged**, because C never appears in a steady-state
ratio. Thermal capacity sets the transient and nothing else.

---

## 3. The time constant

The module suggests reading &tau; off one trace as the time to reach 63% of
the total change. That needs a final temperature, and several of our steps
were stopped before they arrived, so the 63% line would be drawn against a
guess. Instead `python/estimate_tau.py` fits each step to an exponential,
estimating T<sub>&infin;</sub> and &tau; together. At fixed &tau; the model is
linear in the two amplitudes, so only &tau; is searched over and no scipy is
needed.

| Method | Result |
|---|---|
| Eight steps, exponential fit | **&tau; = 62.9 &plusmn; 5.0 s** |
| Same steps, 63% rule against the fitted asymptote | 59.8 &plusmn; 4.7 s |
| Zero-command passive decay alone | 65.8 s |

Every fit has R<sup>2</sup> &gt; 0.998. The last row is the cleanest single
number: with the TEC off it is C/H and nothing else.

**Why eight measurements of one quantity.** A constant command moves where the
temperature ends up but not how fast it gets there: the homogeneous part is
C d&theta;/dt = &minus;H&theta; whatever u is. So &tau; should be identical at
every command, which is a prediction, and
`docs/figures/module_06/tau_estimate.png` is the test. All eight collapse onto
one exponential.

**A closed-loop cross-check is too noisy to add anything.** Fitting an
exponential to each 30 &deg;C P-control run and comparing with
&tau;/(1+L) gives a ratio of 1.03 &plusmn; 0.38 over eight runs, range 0.49
to 1.68 (`python/estimate_tau.py`). Most of those runs start within about 1
&deg;C of where they end, so each fit is poorly conditioned. The trend is the
right way, &tau;<sub>cl</sub> falling from 94 s at K<sub>p</sub> = 0.25 to
3.0 s at K<sub>p</sub> = 32, but it is not a second measurement of &tau;.

**&tau; and the Module 4 steady-state points are not independent.** Both come
from fitting T = T<sub>&infin;</sub> + (T<sub>0</sub>&minus;T<sub>&infin;</sub>)e<sup>&minus;t/&tau;</sup>
to the same steps in the same file: Module 4 kept T<sub>&infin;</sub> and this
section keeps &tau;. So the R<sup>2</sup> &gt; 0.998 reported here and the
R<sup>2</sup> of the Module 4 straight line are two views of one set of fits,
not two confirmations. What **is** independent is section 4: the simulation
takes &chi; and &tau; and predicts the whole measured trace, including its
shape, which neither fit was asked to reproduce.

**Honest caveat.** &tau; is not the same at every command. On the heating
side, including the zero-command decay, it is nearly constant: 65.0 to 65.8 s
across four steps. On the cooling side it ranges from 53.3 to 67.7 s across
four steps, a 27% spread, with the shortest at the strongest cooling command
(u = &minus;65) but the longest at a weak one (u = &minus;16), so it is not a
simple trend with command either. &tau; does correlate with step size,
r = +0.62 over the eight steps: the three smallest steps (2.8 to 4.9 &deg;C)
give the three shortest &tau;, the two largest (15 and 19 &deg;C) among the
longest. With eight points that is not firm, and the three smallest steps are
all cooling, so step size and branch cannot be separated here. A dependence on
step size is what a second, slower thermal mass would produce, which fits
section 4, but this data does not establish it. C and H are therefore not
quite constant over the operating range, and 62.9 &plusmn; 5.0 s is an average
over steps that behave differently. This supersedes the 146 s quoted in
Module 3, which was measured on 16 September, before the A0 wiring fault was
found.

---

## 4. Open-loop simulation

Euler, with the command clamped before it reaches the model:

```
T[n+1] = T[n] + (dt/tau) * (T_amb + chi*u[n] - T[n])
```

**Timestep first.** Euler is only first order, so the answer has to be shown
not to depend on dt. Over 300 s of a +25 count step, going from dt = 0.05 s to
0.01 s moves T(300 s) by 1.6e-4 &deg;C, far under the 0.02 &deg;C noise floor.
dt = 0.05 s is used throughout, dt/&tau; = 8e-4.

| Measured step | span | final measured | final simulated | rms residual |
|---|---|---|---|---|
| driven, u = +25 | 298 s | 33.99 &deg;C | 33.97 &deg;C | 0.147 &deg;C |
| passive, u = 0 | 308 s | 21.60 &deg;C | 21.58 &deg;C | 0.094 &deg;C |

Nothing is fitted to these traces. &chi;, &tau; and T<sub>amb</sub> all come
from Module 4 and section 3.

**Run configuration**, for reproducibility:

| | |
|---|---|
| Exact command | `python3 python/simulate_one_lump.py`, from the repository root |
| Initial condition | T(0) set to the first measured sample of each step, not to T<sub>amb</sub> |
| Saturation limit | &plusmn;255 counts, applied to u before it reaches the model |
| Console output | `data/module_06/simulation_output.txt` |

**The residuals are structured, not random.** Model minus measurement runs
from &minus;0.38 &deg;C at 15 s to +0.17 &deg;C at 119 s on the driven step,
and from +0.15 &deg;C at 13 s to &minus;0.15 &deg;C at 124 s on the passive
one: in both, a smooth excursion that changes sign once, against scatter of
0.02 &deg;C. In both, **the measurement moves faster than the model at first
and slower later**. A single exponential cannot do that against another single
exponential, whatever its &tau;: the difference of two would keep one sign.
So the disagreement is a second, faster time scale near the start of each
step, not measurement error. This is the same conclusion section 6 reaches from the K<sub>p</sub> =
32 overshoot, arriving independently from open-loop data.

---

## 5. P-only simulation against Module 5

Command computed from the current state and clamped before it is applied,
which is the order the real controller uses.

| K<sub>p</sub> | L | simulated droop | 1/(1+L) | measured | sim/meas | peak PWM |
|---|---|---|---|---|---|---|
| 0.25 | 0.125 | 7.518 | 7.518 | 7.66 | 0.981 | 2 |
| 0.50 | 0.251 | 6.765 | 6.765 | 6.94 | 0.975 | 4 |
| 1.00 | 0.501 | 5.635 | 5.635 | 5.50 | 1.025 | 8 |
| 2.00 | 1.003 | 4.225 | 4.225 | 4.25 | 0.994 | 17 |
| 4.00 | 2.005 | 2.815 | 2.815 | 2.81 | 1.002 | 34 |
| 8.00 | 4.010 | 1.689 | 1.689 | 1.57 | 1.076 | 68 |
| 16.00 | 8.020 | 0.938 | 0.938 | 0.90 | 1.042 | 135 |
| 32.00 | 16.041 | 0.496 | 0.496 | 0.46 | 1.079 | 255, clamps 0.3 s |

Measured values are the corrected Module 5 set, recomputed from the full
session log (Module 5 note section 3). Note the column is simulated over
measured, the inverse of the Module 5 ratio.

The simulation reproduces the algebraic 1/(1+L) exactly, as it must: both come
from the same balance, one solved and one integrated. Against measurement it
agrees to within 2.5% up to K<sub>p</sub> = 4, and **over-predicts the droop
by 4 to 8% at the three highest gains**. In degrees those misses are 0.04 to
0.12 &deg;C, inside the 0.1 to 0.2 &deg;C run-to-run reproducibility of the
session, so the data cannot say whether that is a real high-gain effect.
The simulated K<sub>p</sub> = 32 run starts from ambient and clamps briefly;
the measured one started at 29.09 &deg;C and never did. Steady-state droop does
not depend on the starting point, so the comparison stands.
Figure: `docs/figures/module_06/p_control_sim.png`.

---

## 6. Why the P-controlled one-lump model cannot oscillate

With P control the balance is

```
C dT/dt = Pu*Kp*T_set + H*T_amb - (H + Pu*Kp)*T
```

Setting dT/dt = 0 gives T<sub>ss</sub>, and the deviation
&theta; = T &minus; T<sub>ss</sub> obeys the homogeneous equation

```
C dtheta/dt = -(H + Pu*Kp) * theta
```

Trying &theta; = &theta;<sub>0</sub>e<sup>&lambda;t</sup> and cancelling
&theta;:

```
lambda = -(H + Pu*Kp)/C = -(1 + L)/tau
```

**One state variable, therefore one eigenvalue, and it is real and negative**
for any positive parameters and negative feedback. A real exponential never
changes sign, so &theta; keeps the sign it started with while shrinking:
the response cannot cross the steady state, overshoot, or oscillate. Raising
K<sub>p</sub> shortens &tau;<sub>cl</sub> = &tau;/(1+L) and shrinks the droop,
but it cannot manufacture the second state or the delay that oscillation
needs.

### What our apparatus does that this forbids

Module 5 found that at K<sub>p</sub> = 32 the trace **overshoots by 0.04
&deg;C at 7 s and then undershoots by 0.05 &deg;C at 12 s**, returning to its
settled value only by about 28 s, against a settled peak-to-peak of 0.02
&deg;C. Nothing comparable appears at K<sub>p</sub> = 16. The model says
crossing the settled value is impossible, so something is missing. **This was
observed in one run only**; it has not been repeated.

**The extension we judge most important: thermal lag between the TEC face and
the thermistor,** that is, a second lump. The overshoot fits that picture:
&tau;<sub>cl</sub> = &tau;/(1+L) is 7.0 s at K<sub>p</sub> = 16, where none
appears, and 3.7 s at K<sub>p</sub> = 32, where it does, and a fixed lag only
matters once the loop is fast enough to act on stale information. *If* lag is
the cause, it lies **between about 4 and 7 s**. That rests on one run at each
gain, so it is a consistent reading rather than a measurement of the lag. The
stronger evidence is the open-loop residuals below, which do not depend on the
overshoot at all.

The page lists seven candidates. Taking each against our data:

| Extension | Verdict for this apparatus |
|---|---|
| **Two thermal masses** | **Chosen.** The TEC junction and the block are not one object; the figure's structured residuals and the gain-threshold behaviour both point here. |
| Sensor lag | Same signature as a second mass and not separable from it with our data. How the thermistor is attached to the plate is not recorded in this repository, so its own contribution cannot be estimated. |
| Time delay | A pure transport delay would show as a flat dead time before any response. In every Module 4 step, commanded from Python, the temperature moves within 0.5 to 2.0 s of the command, so any delay is at most about 2 s. Module 3 recorded a 35 s onset delay once, but in a run whose duty was set by a trim pot its own log describes as intermittent, and it is not reproduced here. |
| Discrete controller update | Real and the strongest competitor: sampling at 1.97 Hz against &tau;<sub>cl</sub> = 3.7 s is only 7 samples per time constant. Cannot be separated from thermal lag at this logging rate. |
| Actuator lag | The bridge switches at 490 Hz and the Peltier effect is essentially instantaneous; any lag here is milliseconds against seconds. Ruled out. |
| PWM saturation | Ruled out by measurement: the command peaked at 31 of 255 counts, so the loop stayed linear. |
| Measurement noise | 0.02 &deg;C settled peak to peak, against excursions of 0.04 and 0.05 &deg;C lasting several seconds each. Unlikely to be noise, but with a single occurrence it cannot be ruled out; repeating the K<sub>p</sub> = 32 step would settle it. |

**Why a second mass rather than discrete sampling.** Both are consistent with
the overshoot alone, but the open-loop residuals in section 4 separate them:
those traces have no controller in them at all, so sampling cannot be
responsible for their structure, and they still show a systematic second time
scale. Discrete sampling may contribute to the closed-loop overshoot; it
cannot explain the open-loop residual. **Settling this properly needs a faster
log**, which is a Part II measurement rather than something to decide here.

---

## 7. Integral action, damping and windup

PI adds q, the accumulated error, with dq/dt = T<sub>set</sub> &minus; T and
u = K<sub>p</sub>e + K<sub>i</sub>q. The eigenvalues satisfy

```
lambda^2 + ((1+L)/tau)*lambda + chi*Ki/tau = 0
zeta = (1 + L) / (2*sqrt(tau*chi*Ki))
```

reached by dividing the usual (H + P<sub>u</sub>K<sub>p</sub>)/C and
P<sub>u</sub>K<sub>i</sub>/C through by H. **C, H and P<sub>u</sub> never
separate.** Underdamped when (1+L)<sup>2</sup> &lt; 4&tau;&chi;K<sub>i</sub>,
which at K<sub>p</sub> = 2 means K<sub>i</sub> &gt; 0.0318 counts/(&deg;C s).

| K<sub>i</sub> | &zeta; | damping | final droop | overshoot | settles to 0.1 &deg;C |
|---|---|---|---|---|---|
| 0.002 | 3.99 | overdamped | 2.673 &deg;C | none | never |
| 0.010 | 1.78 | overdamped | 0.359 &deg;C | none | never |
| 0.050 | 0.797 | underdamped | 0.000 &deg;C | 0.27 &deg;C | 277 s |
| 0.200 | 0.399 | underdamped | 0.000 &deg;C | 2.37 &deg;C | 271 s |

P-only at the same gain never settles to 0.1 &deg;C: its droop is 4.22 &deg;C.
**Integral action removes the droop entirely, and the overshoot appears
exactly where &zeta; crosses 1.** Figure:
`docs/figures/module_06/pi_vs_p_sim.png`.

### One overdamped and one underdamped set, in full

The module asks for C, H and P<sub>u</sub> recorded for each. Only
&chi; = P<sub>u</sub>/H and &tau; = C/H affect the answer, so H is free;
H = 1 W/K makes the other two readable directly as P<sub>u</sub> = &chi;H and
C = &tau;H. Any other H scales all three together and changes nothing.

| Case | C (J/K) | H (W/K) | P<sub>u</sub> (W/count) | K<sub>p</sub> | K<sub>i</sub> | &zeta; | Trace agrees with the prediction? |
|---|---|---|---|---|---|---|---|
| overdamped | 62.9 | 1.00 | 0.5013 | 2.0 | 0.010 | 1.783 | yes, no overshoot |
| underdamped | 62.9 | 1.00 | 0.5013 | 2.0 | 0.050 | 0.797 | yes, 0.273 &deg;C overshoot |

The prediction and the trace agree on both sides of &zeta; = 1, which is the
check the module is asking for. It holds only while the model is linear and
the command is unclamped, and both of these runs stay well inside that: peak
command 16.9 counts overdamped and 20.2 counts underdamped, of 255.

### Our apparatus cannot wind up

Holding 45 &deg;C needs (45&minus;21.54)/&chi; = **47 of the 255 available
counts**, so the bridge is nowhere near the binding constraint at any setpoint
inside the 10 to 45 &deg;C safety band. The command never stays clamped long
enough for the integral to run away. To show the effect at all, both our
simulation and the supplied program were run with the limit lowered to 50
counts, which is what Part 8 asks us to suppose.

| Limit 50 counts, K<sub>p</sub> = 2, K<sub>i</sub> = 0.05, setpoint 45 &deg;C | overshoot | time clamped |
|---|---|---|
| plain PI | +1.46 &deg;C | 313 s |
| with anti-windup | +0.26 &deg;C | 22 s |

---

## 8. Windup thought experiment

**What happens to the integral term while PWM is saturated?** It keeps
growing, because dq/dt = e and the error is still large. The command the
controller *computes* diverges from the command the actuator *delivers*: one
climbs without bound while the other sits pinned at the clamp. The extra
integral buys nothing, since the actuator is already doing all it can, but it
is stored and will have to be paid back. In our run the integral reached about
1200 &deg;C&middot;s while the command was stuck at 50 counts.

**What happens after the temperature finally approaches the setpoint?** The
error changes sign, but q is still large and positive, so u = K<sub>p</sub>e +
K<sub>i</sub>q stays saturated well past the moment the error reaches zero.
The controller only begins to back off once accumulated negative error has
cancelled what it banked on the way up, which takes roughly as long as the
saturated stretch did.

**Why might this cause overshoot?** Because full drive continues after the
error has already gone to zero. Nothing in the loop is asking for more heat at
that point; the integrator is simply still holding the memory of an error it
could not act on. The plate keeps climbing until the integral drains. Measured
at a 50-count limit: 1.46 &deg;C overshoot plain against 0.26 &deg;C with
anti-windup, a factor of 5.6 from the same gains and the same plant.

**How could software prevent or reduce it?**

- **Conditional integration.** Stop accumulating whenever the command is
  clamped *and* the error would push it further into the clamp. One line, no
  new tuning parameter. This is what `simulate_one_lump.py` implements.
- **Back-calculation.** Feed (clamped &minus; unclamped) back into the
  integrator through a gain, so it unwinds smoothly rather than freezing.
  Better behaved on a real plant, one more constant to choose.
- **Clamp the integral term itself** to the range it could ever usefully
  command. Crude but effective.
- **Reset q on a setpoint change**, which removes the commonest way a loop
  enters saturation in the first place.

---

## 9. Cross-check against the supplied program

Run after our own simulator, as the module requires, on 5 October. **H is
free:** only &chi; = P<sub>u</sub>/H and &tau; = C/H affect the answer, so H = 1
W/K makes the other two readable at a glance. The supplied interface asks for
three numbers where the physics has two.

Entered in every run: T<sub>amb</sub> = 21.54 &deg;C, initial temperature
21.54 &deg;C, C = 62.9 J/K, H = 1 W/K, P<sub>u</sub> = 0.5013 W/count,
K<sub>p</sub> = 2, Euler step 0.25 s, duration 900 s. What changed between
runs is in the table below.

| Case | Ours | Supplied program |
|---|---|---|
| &tau;, &chi; | 62.9 s, 0.5013 | 62.9 s, 0.5013 |
| P droop at K<sub>p</sub> = 2 | 4.225 &deg;C | 4.225 &deg;C predicted and simulated |
| PI droop, K<sub>i</sub> = 0.05 | 0.000 &deg;C | &minus;0.000 &deg;C |
| &zeta;, K<sub>i</sub> = 0.05 | 0.797 | 0.797, "underdamped" |
| K<sub>i</sub> = 0 | PI reduces to P | droop 4.225 &deg;C, "first order because Ki = 0" |
| Windup, limit 50: time clamped | 313 s | 34.7% of 900 s = 312 s |
| Windup, limit 50: anti-windup | clamped 22 s | clamped 0.0% |

**Why the last row differs, from the two programs' code.** Both use
conditional integration, which the supplied program states in its own
docstring. They test different things:

- The supplied program computes the command the *next* integral step would
  produce, and refuses that step if it would push the command past the limit
  (`python/Lab_6_first_order_p_pi_simulation_realtime.py`, lines 110 to 122).
  The integral is stopped before saturation, so the command never reaches the
  clamp.
- Ours holds the integral only once the command is *already* clamped
  (`python/simulate_one_lump.py`, `run_pi`), so the command enters saturation
  first and stays there 22 s before the hold takes effect.

Neither is wrong; the supplied version is the more conservative. The physical
conclusion, that anti-windup removes most of the overshoot, is the same either
way. Its saturation figure is the fraction of time steps on which the
unclamped command exceeds the limit (lines 75 and 152), so at a fixed 0.25 s
step 34.7% is 312 s of the 900 s run.

### Screenshots of the supplied program

Six runs, all with the parameters above. The program's opening run with its
own default parameters (&tau; = 80 s, &chi; = 0.12) is not included, since it
describes no part of this apparatus.

**1. P only, K<sub>p</sub> = 2, setpoint 30 &deg;C, limit 255.** Predicted and
simulated P droop both 4.225 &deg;C, saturation 0.0%: the same droop our
simulator and the algebra give.

![P only, Kp = 2](../figures/module_06/supplied_sim/1_p_only_kp2.png)

**2. PI, K<sub>i</sub> = 0.05, setpoint 30 &deg;C, limit 255, anti-windup
on.** &zeta; = 0.797, "underdamped", PI droop &minus;0.000 &deg;C, saturation
0.0%. Integral action removes the droop, with a small overshoot.

![PI, Ki = 0.05](../figures/module_06/supplied_sim/2_pi_ki0p05.png)

**3. PI, K<sub>i</sub> = 0, setpoint 30 &deg;C, limit 255.** &zeta; = &infin;,
"first order because Ki = 0", PI droop 4.225 &deg;C. PI with no integral term
reproduces run 1 exactly, which is the program's own check number 2.

![PI, Ki = 0](../figures/module_06/supplied_sim/3_pi_ki0_equals_p.png)

**4. PI, K<sub>i</sub> = 0, setpoint 45 &deg;C, limit 50, anti-windup off.**
Droop 11.715 &deg;C, saturation 0.0%. This is P control at the windup
setpoint: K<sub>p</sub>e<sub>0</sub> = 2 &times; 23.46 = 47 counts, just under
the 50-count limit, so without an integral the command never clamps. It is the
baseline for runs 5 and 6, and shows that the saturation in run 5 comes from
the integral term alone.

![Setpoint 45, limit 50, Ki = 0](../figures/module_06/supplied_sim/4_setpoint45_limit50_ki0.png)

**5. PI, K<sub>i</sub> = 0.05, setpoint 45 &deg;C, limit 50, anti-windup
off.** Saturation 34.7%, final droop &minus;0.000 &deg;C. The command sits on
the 50-count limit for about 312 s and the error trace dips below zero before
recovering: windup overshoot.

![Windup, plain PI](../figures/module_06/supplied_sim/5_windup_plain.png)

**6. Same as 5, anti-windup on.** Saturation 0.0%, final droop &minus;0.000
&deg;C. The integral is never allowed to drive the command into the clamp. The
error comes down to zero with no dip that can be resolved on this plot's 23
&deg;C scale, against the clear dip in run 5. The program does not report an
overshoot value, so the size of any remaining overshoot is not known from
these screenshots.

![Windup, anti-windup on](../figures/module_06/supplied_sim/6_windup_antiwindup.png)

---

## 10. Evidence for A3

- [x] derivation of the P-control droop equation: sections 1 and 6
- [x] the three Module 5 interpretation answers: Module 5 note section 6
- [x] estimate of &chi;<sub>T,u</sub>: 0.50127 &deg;C/count, Module 4
- [x] estimate of &tau;: 62.9 &plusmn; 5.0 s, section 3
- [x] open-loop simulation against a measured trace: section 4
- [x] P-only simulation against Module 5 droop: section 5
- [x] PI simulation against P-only: section 7
- [x] why the one-lump model does not oscillate, and what ours does: section 6
- [x] windup thought-experiment answers: section 8
- [x] supplied program run with our parameters, six screenshots:
  section 9, `docs/figures/module_06/supplied_sim/`
- [x] PI controller on the apparatus and the six experimental Goldilocks
  plots with step-response metrics (A3 Question 2): section 11
- [ ] link to the pushed Git checkpoint: add the hash once pushed

**Open, now answered by section 11.** The Module 5 note left open whether the
K<sub>p</sub> = 32 overshoot was real and whether discrete sampling could
cause it. At K<sub>p</sub> = 64 the overshoot is 1.69 &deg;C with clear
ringing, far above noise, and a sampled one-lump model cannot produce more
than 0.03 &deg;C of it.

**&tau; still comes from 500-sample data.** Part 3 asks for 1000-sample
averaging, and every step in section 3 used 500. On 13 October the instructor
said not to redo the Module 4 measurements, to keep the existing &tau;, and to
use 1000 samples from now on, which the Module 6 runs do.

---

## 11. Part 7: PI control on the apparatus, and the six Goldilocks runs

13 October 2026. Controller: [`python/tec_pi_control_gui.py`](../../python/tec_pi_control_gui.py),
whose `pi_step()` holds every line that computes e, q, u<sub>P</sub>,
u<sub>I</sub> and the clamped command. The instructor reviewed it on 13
October. Sketch: [`arduino/module_06/tec_pi_safety`](../../arduino/module_06/tec_pi_safety/tec_pi_safety.ino),
the Module 4 safety sketch with 1000-sample averaging.

**What the controller does each reading.** Δt is the actual time since the
previous accepted reading (0.56 to 0.61 s here), q<sub>n+1</sub> =
q<sub>n</sub> + e<sub>n</sub>Δt, u = K<sub>p</sub>e + K<sub>i</sub>q<sub>n+1</sub>,
clamped to &plusmn;255. Anti-windup is conditional integration: the new q is
refused when the command it gives is past the limit and the error pushes it
farther out. That test is the same as `controller_command()` in the course
simulator; the two agreed on 200,000 random cases. Mode, Zero integral, PWM
limit and anti-windup can only be changed with control off.

**Protocol, the same for all six.** Setpoints 30 and 35 &deg;C, PWM limit 255,
anti-windup on, integral zeroed before each run. Each run settles at 30, steps
to 35, steps back to 30. Raw data:
`data/module_06/pi_run_20261013_094149.csv`. Bench record, including the 12 V
TEC voltage and the instructor's extra K<sub>i</sub> = 2, 5, 10 tries (not
used): `data/module_06/bench_log_2026-10-13.md`.

| Run | Controller | K<sub>p</sub> | K<sub>i</sub> | End of stage at 30 / 35 / 30 (&deg;C) | Overshoot up / down (&deg;C) |
|---|---|---|---|---|---|
| 1 | P | 2 | 0 | 25.76 / 28.25 / 25.76 | 0.02 / 0.01 |
| 2 | P | 16 | 0 | 29.05 / 33.52 / 29.12 | 0.02 / 0.03 |
| 3 | P | 64 | 0 | 29.74 / 34.59 / 29.76 | **1.69 / 0.07** |
| 4 | PI | 12 | 0.05 | 29.66 / 34.71 / 30.08 | 0.02 / 0.01 |
| 5 | PI | 12 | 0.2 | 29.97 / 35.02 / 29.93 | 0.02 / 0.02 |
| 6 | PI | 12 | 1.0 | 30.00 / 35.00 / 30.00 | **0.71 / 1.30** |

Each value is the mean of the last 30 s of the stage. Overshoots of 0.03
&deg;C and below are at the noise level (0.005 to 0.02 &deg;C standard
deviation). Drift over the last 60 s of each stage is under 0.08 &deg;C/min
except Run 2's last stage, &minus;0.33 &deg;C/min, which was ended after 78 s.
Run 4 was still creeping at +0.07 &deg;C/min at both 30 and 35, as a small
K<sub>i</sub> should. (Run 3's first stage lasted only 59 s, so its 60 s
window includes the approach; over its last 30 s it is flat.)

**Figures** (`python/plot_goldilocks_experiment.py`): one per run in
`docs/figures/module_06/goldilocks/`, all on the same axes (&minus;30 to 610 s
from the 30 &rarr; 35 step, 25 to 37 &deg;C), temperature with setpoint above
and signed applied PWM below; `overlay_p_and_pi.png` puts the three P and
three PI runs on one figure each; `high_gain_steps.png` zooms on the four
steps the metrics are quoted for.

![Six runs](../figures/module_06/goldilocks/overlay_p_and_pi.png)

**Step-response metrics, highest-gain runs** (A3 Question 2, Part 2). Rise is
10 % to 90 % of the change; settling is the last time T leaves the final value
&plusmn;2 % of the change (about &plusmn;0.1 &deg;C); period is twice the mean
spacing of crossings of the final value with 0.05 &deg;C hysteresis, given
when there are at least three crossings. All six runs are in
`data/module_06/goldilocks_metrics.csv`.

| Run, step | Rise 10-90 % | Overshoot | Settling &plusmn;2 % | ss error | Period |
|---|---|---|---|---|---|
| 3 (P, K<sub>p</sub> 64), 30 &rarr; 35 | 2.1 s | 1.69 &deg;C, 35 % | 21 s | +0.41 &deg;C | 9 s |
| 3, 35 &rarr; 30 | 4.0 s | 0.07 &deg;C, 1 % | 15 s | +0.24 &deg;C | n/a (2 crossings) |
| 6 (PI, K<sub>i</sub> 1.0), 30 &rarr; 35 | 8.2 s | 0.71 &deg;C, 14 % | 56 s | 0.00 &deg;C | n/a (1 crossing) |
| 6, 35 &rarr; 30 | 12.5 s | 1.30 &deg;C, 26 % | 68 s | 0.00 &deg;C | n/a (1 crossing) |

Run 3 hit the &plusmn;255 limit for 4 readings on the way up and 3 on the way
down, so its first 2 s are clipped, not linear. No other run saturated.

**What the six show.**

- P: raising K<sub>p</sub> shrinks the droop and speeds the response, as the
  one-lump model says (Run 1 droop 4.24 &deg;C, Run 2 0.88 &deg;C, Run 3 0.24
  &deg;C on the way down). Run 3 then overshoots by 35 % and rings with a
  9 s period, which the one-lump P model forbids (section 6).
- PI removes the droop: Runs 5 and 6 end within 0.07 &deg;C of the setpoint,
  where P at K<sub>p</sub> = 16 (Run 2) stopped 0.88 to 1.48 &deg;C short.
  Run 4 shows the slow end of that: u<sub>I</sub> climbs for minutes and the
  plate is still 0.29 &deg;C short of 35 after 300 s.
- Raising K<sub>i</sub> at fixed K<sub>p</sub> trades speed for overshoot:
  rise 58 s, 24 s, 8 s on the way up across Runs 4 to 6, overshoot 0.02, 0.02,
  0.71 &deg;C.
- Heating and cooling are not symmetric. Run 6 overshoots 0.71 &deg;C going
  up and 1.30 &deg;C coming down; the cooling branch has the smaller &chi;
  (0.18 against 0.50 &deg;C per count).

**Sampling does not explain the Run 3 ringing.**
`python/sampling_delay_check.py` runs the one-lump plant (&tau; 62.9 s,
measured &chi;) under the controller as it actually runs: read every 0.563 s,
command rounded, clipped at &plusmn;255 and held, with the delay from reading
to command anywhere from 0 to one full sample. The largest overshoot it gives
is 0.03 &deg;C, against 1.69 &deg;C measured. Something with its own lag
between the TEC and the thermistor is needed, which is what Part II's
two-lump model adds.
