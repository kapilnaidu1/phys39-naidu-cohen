# Module 6 Part I: P/PI control and lumped modeling

Naidu / Cohen, 5 October 2026. Guided modeling work feeding A3. No separate
paper for the module itself.

**Code.** [`python/estimate_tau.py`](../../python/estimate_tau.py) (Part 3),
[`python/simulate_one_lump.py`](../../python/simulate_one_lump.py) (Parts 4, 5, 7),
[`python/Lab_6_first_order_p_pi_simulation_realtime.py`](../../python/Lab_6_first_order_p_pi_simulation_realtime.py)
(the supplied program, used only to check our own; see section 9).
Figures in `docs/figures/module_06/`, console output in
`data/module_06/simulation_output.txt`.

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
| Module 5 trace near oscillation | `data/module_05/kp32_high_gain_run.csv`, the only run showing any overshoot |
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
with R<sup>2</sup> &gt; 0.998 and a common &tau;. Module 3 saw the same thing
the crude way: no visible response for 35 s after commanding duty 28.

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

Agreement to 0.6%. **One physical reason they differ:** the prediction uses a
single &chi; fitted across the whole heating branch, while this run sits near
17 counts where the local slope need not equal the branch average. Room drift
over the session contributes as well, and section 3 shows &tau; itself moving
22% across the command range, so the coefficients are not strictly constant.

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

**&tau; and the Module 4 steady-state points are not independent.** Both come
from fitting T = T<sub>&infin;</sub> + (T<sub>0</sub>&minus;T<sub>&infin;</sub>)e<sup>&minus;t/&tau;</sup>
to the same steps in the same file: Module 4 kept T<sub>&infin;</sub> and this
section keeps &tau;. So the R<sup>2</sup> &gt; 0.998 reported here and the
R<sup>2</sup> of the Module 4 straight line are two views of one set of fits,
not two confirmations. What **is** independent is section 4: the simulation
takes &chi; and &tau; and predicts the whole measured trace, including its
shape, which neither fit was asked to reproduce.

**Honest caveat.** &tau; drifts from 53.3 s at u = &minus;65 to 65.0 s at
u = +38, about 22%. The plate is more sluggish hot than cold, so H and C are
not quite constant across 10 to 45 &deg;C. This supersedes the 146 s quoted in
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

**The residuals are structured, not random.** Both panels of the figure show a
smooth excursion of about &plusmn;0.3 &deg;C that changes sign once, rather
than scatter at the 0.02 &deg;C noise level: the model leads the measurement
early and lags it later. A single exponential with the right &tau; cannot do
that, so the disagreement is a second time scale rather than measurement
error. This is the same conclusion section 6 reaches from the K<sub>p</sub> =
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
| 4.00 | 2.005 | 2.815 | 2.815 | 2.82 | 0.998 | 34 |
| 8.00 | 4.010 | 1.689 | 1.689 | 1.67 | 1.011 | 68 |
| 16.00 | 8.020 | 0.938 | 0.938 | | | 135 |
| 32.00 | 16.041 | 0.496 | 0.496 | | | 255, clamps 0.3 s |

The simulation reproduces the algebraic 1/(1+L) exactly, as it must: both come
from the same balance, one solved and one integrated. Agreement with
measurement is 0.98 to 1.03 across a 32-fold range of gain.
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

Module 5 found a **0.041 &deg;C overshoot at K<sub>p</sub> = 32**, peaking 7 s
in, against a 0.020 &deg;C noise floor, and absent at every lower gain. The
model says that is impossible, so something is missing.

**The extension we judge most important: thermal lag between the TEC face and
the thermistor,** that is, a second lump. The evidence is that the overshoot
is gain-dependent in the right way. &tau;<sub>cl</sub> = &tau;/(1+L) is 7.0 s
at K<sub>p</sub> = 16, where no overshoot appears, and 3.7 s at
K<sub>p</sub> = 32, where it does. A fixed lag between the Peltier junction
and the sensor only matters once the loop becomes fast enough to act on stale
information, which puts that lag somewhere **between about 4 and 7 s**.

The page lists seven candidates. Taking each against our data:

| Extension | Verdict for this apparatus |
|---|---|
| **Two thermal masses** | **Chosen.** The TEC junction and the block are not one object; the figure's structured residuals and the gain-threshold behaviour both point here. |
| Sensor lag | Same signature as a second mass and not separable from it with our data. The thermistor is epoxied to the plate, so its own mass is small, which makes it the smaller part of the same effect. |
| Time delay | A pure transport delay would show as a flat dead time before any response. Module 3 saw 35 s of apparent dead time, but that is the first part of an exponential with &tau; = 63 s, not a true delay. No evidence for one. |
| Discrete controller update | Real and the strongest competitor: sampling at 1.97 Hz against &tau;<sub>cl</sub> = 3.7 s is only 7 samples per time constant. Cannot be separated from thermal lag at this logging rate. |
| Actuator lag | The bridge switches at 490 Hz and the Peltier effect is essentially instantaneous; any lag here is milliseconds against seconds. Ruled out. |
| PWM saturation | Ruled out by measurement: the command peaked at 31 of 255 counts, so the loop stayed linear. |
| Measurement noise | 0.020 &deg;C peak to peak, the same size as the 0.041 &deg;C overshoot, and random. It cannot produce a repeatable one-sided bump at a fixed time after the step. |

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
command 17 counts of 255.

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

Run after our own simulator, as the module requires, with our parameters
entered as C = 62.9, H = 1, P<sub>u</sub> = 0.5013. **H is free:** only
&chi; = P<sub>u</sub>/H and &tau; = C/H affect the answer, so setting H = 1
makes the other two readable at a glance. The supplied interface asks for
three numbers where the physics has two.

| Case | Ours | Supplied program |
|---|---|---|
| &tau;, &chi; | 62.9 s, 0.5013 | 62.9 s, 0.5013 |
| P droop at K<sub>p</sub> = 2 | 4.225 &deg;C | 4.225 &deg;C predicted and simulated |
| PI droop, K<sub>i</sub> = 0.05 | 0.000 &deg;C | &minus;0.000 &deg;C |
| &zeta;, K<sub>i</sub> = 0.05 | 0.797 | 0.797, "underdamped" |
| K<sub>i</sub> = 0 | PI reduces to P | droop 4.225 &deg;C, "first order because Ki = 0" |
| Windup, limit 50: time clamped | 313 s | 34.7% of 900 s = 312 s |
| Windup, limit 50: anti-windup | clamped 22 s | clamped 0.0% |

Everything agrees except the last row, and that is an implementation
difference rather than an error: both use conditional integration, but the
supplied version holds the integral early enough that the command never
reaches the clamp at all, while ours allows 22 s of clamping first. The
physical conclusion, that anti-windup removes most of the overshoot, is the
same either way.

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
- [ ] link to the pushed Git checkpoint: add the hash once pushed

**Open.** The 1 Hz log cannot separate thermal lag from discrete sampling as
the cause of the K<sub>p</sub> = 32 overshoot. A faster log would settle it,
and that is a Part II question rather than something to guess at here.
