# Module 6 Part II: two-lump model and simulation

Naidu / Cohen. Class on 19 October 2026. Feeds A3 Questions 3 and 5.
Simulator: [`python/Lab_6_7_modeling_tec.py`](../../python/Lab_6_7_modeling_tec.py),
run from the repository root with `python3 python/Lab_6_7_modeling_tec.py`.

---

## Pre-class 1: Lienhard Problem 1.8 (possible board work)

**Problem.** A copper sphere, D = 2.5 cm, starts uniformly at 40 &deg;C and
hangs in a slow air stream at 0 &deg;C with h = 15 W/m&sup2;K. Radiation is
neglected. Write the energy balance, solve it, plot T from 40 to 0 &deg;C, and
confirm Bi &#8810; 1.

**Physical system.** One lump: the whole sphere at one temperature T(t). Heat
leaves only by convection from its surface to air at T<sub>&infin;</sub> = 0
&deg;C. Copper at 20 &deg;C from Lienhard Table A.1: &rho; = 8954 kg/m&sup3;,
c<sub>p</sub> = 384 J/kg K, k = 398 W/m K, all taken as constant.

**Heat balance** (Lienhard eqn 1.20). Rate of change of stored energy equals
heat lost to the air:

```
rho c_p V dT/dt = -h A (T - T_inf)
```

Units: kg/m&sup3; &middot; J/(kg K) &middot; m&sup3; &middot; K/s = W on the
left, W/(m&sup2;K) &middot; m&sup2; &middot; K = W on the right.

**Solution** (eqns 1.21 and 1.22). With T(0) = T<sub>i</sub>:

```
T - T_inf = (T_i - T_inf) exp(-t / tau),   tau = rho c_p V / (h A) = rho c_p D / (6 h)
```

since V/A = D/6 for a sphere. Numbers: V = 8.18 &times; 10<sup>&minus;6</sup>
m&sup3;, A = 1.96 &times; 10<sup>&minus;3</sup> m&sup2;, m = 73.3 g, so
C = mc<sub>p</sub> = 28.1 J/K and hA = 0.0295 W/K, giving

**&tau; = 955 s, about 16 min.** T(t) = 40 e<sup>&minus;t/955 s</sup> &deg;C.
It never reaches 0 exactly: 1 &deg;C at 59 min, 0.1 &deg;C at 95 min.

![Problem 1.8](../figures/module_06/part2/problem_1_8.png)

**Lumped approximation, checked.** Lienhard's Biot number is Bi = hL/k, with L
a characteristic length of the body. With L = V/A = D/6, Bi = 1.6 &times;
10<sup>&minus;4</sup>; with L = D/2, 4.7 &times; 10<sup>&minus;4</sup>. Either
way Bi &#8810; 1: the resistance to conduction inside the copper is thousands
of times smaller than the resistance of the air film, so the sphere stays
uniform and only C and hA matter.

**Link to our TEC.** Same equation with C = mc<sub>p</sub> and H = hA, so
&tau; = C/H. For the plate, &tau; = 62.9 s. The TEC adds a source term
P<sub>u</sub>u to the right-hand side, which shifts where T ends up but not
how fast it gets there. Part II asks what happens when Bi is not small enough
to treat the TEC side and the thermistor side as one lump.

Script: [`python/lienhard_problem_1_8.py`](../../python/lienhard_problem_1_8.py).

---

## Pre-class 3: the two-lump equations, labelled

```
C_T dT/dt   = P_u(u) u - G (T - T_m)
C_m dT_m/dt = G (T - T_m) - H (T_m - T_amb)
```

| Symbol | Meaning | Units |
|---|---|---|
| T | temperature of the TEC-side lump, the face the TEC pumps heat into | &deg;C |
| T<sub>m</sub> | temperature of the measured lump, the block where the thermistor sits | &deg;C |
| T<sub>amb</sub> | room temperature | &deg;C |
| C<sub>T</sub>, C<sub>m</sub> | heat capacities of the two lumps; C = C<sub>T</sub> + C<sub>m</sub> is the one-lump C | J/K |
| G | thermal conductance between the two lumps | W/K |
| H | conductance from the measured lump to the room | W/K |
| u | signed PWM command, + heats, &minus; cools | counts |
| P<sub>u</sub>(u) | TEC heat per count: P<sub>u,h</sub> when heating, P<sub>u,c</sub> when cooling | W/count |

The TEC-side lump has no direct path to the room; all loss to the room goes
through H from the measured lump.

---

## Pre-class 4: the five two-lump prompts

**1. Which term carries heat from the TEC side to the measured side?**
G(T &minus; T<sub>m</sub>). It leaves the first equation with a minus sign and
enters the second with a plus sign, so the heat the TEC side loses is exactly
what the measured side gains.

**2. Which term is the heat loss from the measured block to room air?**
H(T<sub>m</sub> &minus; T<sub>amb</sub>), in the second equation.

**3. Why can T<sub>m</sub> lag behind T?** The TEC puts heat into C<sub>T</sub>
only. T<sub>m</sub> can change only when heat flows through G, and that flow is
G(T &minus; T<sub>m</sub>), which is zero until T has already moved away from
T<sub>m</sub>. So T moves first, and T<sub>m</sub> follows at a rate set by
G/C<sub>m</sub>. With a finite G and a nonzero C<sub>m</sub>, the measured
block is always catching up.

**4. Why can a controller that uses T<sub>m</sub> react too late?** The
controller sees only T<sub>m</sub>. When T<sub>m</sub> finally reaches the
setpoint, T is already above it, and the heat stored in C<sub>T</sub> keeps
flowing into the block after the command has dropped. T<sub>m</sub> carries on
past the setpoint, then the controller over-corrects the other way. The larger
the gain, the more heat goes in before the measurement catches up, which is
why Run 3 at K<sub>p</sub> = 64 overshot by 1.69 &deg;C and rang while Run 2
at K<sub>p</sub> = 16 did not.

**5. Rate-constant form.** Dividing the measured-lump equation by
C<sub>m</sub>:

```
dT_m/dt = (G/C_m)(T - T_m) - (H/C_m)(T_m - T_amb)
        =   k21  (T - T_m) -   k_m  (T_m - T_amb)
```

so k<sub>21</sub> = G/C<sub>m</sub> and k<sub>m</sub> = H/C<sub>m</sub>. Both
are (W/K)/(J/K) = 1/s, rate constants whose inverses are time scales.

- Raising k<sub>21</sub> (more coupling, or a lighter measured block) makes
  T<sub>m</sub> follow T faster: the two lumps equilibrate in about
  1/k<sub>21</sub>, so the lag shrinks. As G grows without limit the two lumps
  move together and the model becomes the one-lump model.
- Raising k<sub>m</sub> (more loss, or a lighter block) makes the block relax
  toward room temperature faster, in about 1/k<sub>m</sub>. It also lowers how
  far a given command can hold the block from room temperature, since at
  steady state T<sub>m</sub> &minus; T<sub>amb</sub> = P<sub>u</sub>u/H.

With our measured-mode numbers (C = 74.0 J/K, H = 1.176 W/K) and the starting
split C<sub>T</sub>/C = 0.35, C<sub>m</sub> = 48.1 J/K, so k<sub>m</sub> =
0.024 s<sup>&minus;1</sup> (about 41 s). k<sub>21</sub> depends on G, which we
have not measured; the starting guess G = 2 W/K gives 0.042
s<sup>&minus;1</sup> (about 24 s). Matching Run 3 in class fixes G.

---

## Settings check (in-class step 1)

`one_lump`, `p`, `measured`, with T<sub>amb</sub> = 21.54 &deg;C,
&chi;<sub>c</sub> = 0.181, &chi;<sub>h</sub> = 0.501 &deg;C/PWM,
&tau; = 62.9 s, V<sub>TEC</sub> = 12.0 V, R<sub>M</sub> = 1.50 &Omega;,
K<sub>p</sub> = 2.

The simulator derived C = 74.0 J/K, H = 1.176 W/K, P<sub>u,c</sub> = 0.2129
W/PWM, r = 2.77 and showed &tau; = 62.9 s. It settled with an error of about
4.2 &deg;C, near 25.8 &deg;C. The droop formula gives 4.23 &deg;C (25.77
&deg;C), and Run 1 measured 25.76 &deg;C at the same gain. The check passes,
so no one-lump rerun is needed.

---

## In-class step 2: three one-lump PI comparisons

`one_lump`, `pi`, anti-windup on, start at 21.54 &deg;C, setpoint 30 &deg;C,
600 s per run. Each run was done in the GUI (screenshots checked against the
numbers below). The numbers come from the same simulator code run with the
same settings, so they are exact rather than read off a plot. ζ is the
simulator's ζ<sub>1L,PI</sub> = (H + P<sub>u</sub>K<sub>p</sub>)/(2&radic;(C
P<sub>u</sub>K<sub>i</sub>)).

| Comparison | K<sub>p</sub> | K<sub>i</sub> | C (J/K) | ζ | Peak (&deg;C) | Within 0.1 &deg;C of 30 from |
|---|---|---|---|---|---|---|
| 1. raise K<sub>i</sub> | 12 | 0.06 | 74.0 | 2.55 | none; still 0.07 short at 600 s | 503 s |
| | 12 | 0.2 | 74.0 | 1.40 | 30.02 | 43 s |
| | 12 | 1.0 | 74.0 | 0.63 | 31.60 | 82 s |
| 2. raise K<sub>p</sub> | 4 | 0.2 | 74.0 | 0.60 | 31.30 | 187 s |
| | 12 | 0.2 | 74.0 | 1.40 | 30.02 | 43 s |
| | 32 | 0.2 | 74.0 | 3.39 | none; PWM at 255 at first | 201 s |
| 3. raise C (direct constants) | 12 | 0.2 | 75 | 1.38 | 30.02 | 45 s |
| | 12 | 0.2 | 150 | 0.98 | 30.58 | 199 s |

Comparison 3 used H = 1.20 W/K, P<sub>u,c</sub> = 0.21 W/PWM and r = 2.75 for
both runs, the values the GUI rounded to on switching to direct constants, so
only C differs between them.

**What each shows.**

1. Raising K<sub>i</sub> lowers ζ (ζ &prop; 1/&radic;K<sub>i</sub>). At
   ζ = 0.63 the plate overshoots by 1.6 &deg;C; at 1.40 by only 0.02 &deg;C;
   at 2.55 the integral is so slow that the last part of the droop takes
   minutes to remove, like Run 4.
2. Raising K<sub>p</sub> raises ζ (the numerator H + P<sub>u</sub>K<sub>p</sub>
   grows). Too much damping is not better: at K<sub>p</sub> = 32 there is no
   overshoot but the final 0.15 &deg;C takes over three minutes.
3. Doubling C at fixed H doubles &tau; and lowers ζ by &radic;2, from 1.38
   to 0.98: more thermal mass gives a slower, less damped response. The
   final temperature is the same, because the steady state depends on H and
   P<sub>u</sub>, not on C.

The ζ = 0.98 run still overshoots by 0.58 &deg;C. ζ near 1 does not guarantee
no overshoot for PI, because the controller adds a zero: the integral keeps
pushing until the error changes sign.

---

## In-class step 3: the two-lump P transition

The page's common parameter set, not our apparatus: `two_lump`, `direct
constants`, `p`, T<sub>amb</sub> = T<sub>0</sub> = 29 &deg;C, T<sub>set</sub> =
30 &deg;C, C = 91 J/K, H = 1.14 W/K, P<sub>u,c</sub> = 0.26 W/PWM, r = 2.0,
K<sub>i</sub> = 0, mass temperature only. ζ is the simulator's
ζ<sub>2L,P</sub>; every displayed value matched the page's prediction.

| Run | K<sub>p</sub> | G (W/K) | C<sub>T</sub>/C | ζ<sub>2L,P</sub> | Rise 10-90 % | Overshoot of T<sub>m</sub> |
|---|---|---|---|---|---|---|
| P1 | 60 | 50 | 0.35 | 1.31 | 5.3 s | none |
| P2 | 105 | 50 | 0.35 | 1.00 | 2.7 s | none |
| P3 | 160 | 50 | 0.35 | 0.81 | 1.6 s | 0.015 &deg;C (1.5 %) |
| G1 | 105 | 35 | 0.35 | 0.84 | 2.5 s | 0.009 &deg;C (0.9 %) |
| G2 | 105 | 70 | 0.35 | 1.18 | 2.9 s | none |
| F1 | 105 | 50 | 0.20 | 1.19 | 2.9 s | none |
| F2 | 105 | 50 | 0.50 | 0.96 | 2.6 s | none visible |
| F3 | 105 | 50 | 0.80 | 1.21 | 3.0 s | none |

Rise times and overshoots are from the simulator code with these settings.

**What it shows.** Raising K<sub>p</sub> moves the two-lump P loop from
monotonic (ζ 1.31) through critical (1.00) to underdamped (0.81), and the
response gets faster each time. That is what the one-lump P model can never
do: its single real eigenvalue cannot overshoot at any gain. The overshoot here
is small, 1.5 % at ζ = 0.81, because ζ is still close to 1. Lowering G (weaker
coupling, more lag) lowers ζ; raising it brings the model back toward one
lump. ζ is smallest when both thermal masses are appreciable (C<sub>T</sub>/C
= 0.5) and rises when the capacitance sits mostly in either lump, because then
one of the two states barely matters.

---

## In-class step 4: two-lump PI stability

Same common set with G = 2 W/K, K<sub>p</sub> = 18 PWM/&deg;C, `pi`,
anti-windup on, 1 &deg;C step so the PWM never saturates (largest command 64
counts). ρ<sub>I</sub> = K<sub>i</sub>/K<sub>i,crit</sub> with K<sub>i,crit</sub>
from Routh-Hurwitz, as displayed. Rise is 10-90 %, settling is the last time
T<sub>m</sub> leaves 30 &plusmn; 0.02 &deg;C (2 % of the step), period is the
spacing of the first two peaks. Every run was done in the GUI and matched;
numbers are from the simulator code with the same settings.

| Run | K<sub>i</sub> | G | K<sub>i,crit</sub> | ρ<sub>I</sub> | Rise | First overshoot | Successive peaks above 30 (&deg;C) | Settling | Period |
|---|---|---|---|---|---|---|---|---|---|
| S1 | 0.26 | 2 | 2.34 | 0.11 | 16.4 s | 0.18 &deg;C | 0.18, 0.01 | 61 s | 72 s |
| S2 | 1.0 | 2 | 2.34 | 0.43 | 12.7 s | 0.55 &deg;C | 0.55, 0.09, 0.02 | 169 s | 84 s |
| S3 | 2.1 | 2 | 2.34 | 0.90 | 10.4 s | 0.92 &deg;C | 0.92, 0.73, 0.58, 0.47 | not within 900 s | 72 s |
| S4 | 2.5 | 2 | 2.34 | 1.07 | 9.8 s | 1.02 &deg;C | 1.02, 1.07, 1.12, 1.17 (growing) | never | 68 s |
| S5 | 1.0 | 0.5 | 0.88 | 1.14 | 19.5 s | 1.05 &deg;C | 1.05, 1.22, 1.40, 1.62 (growing) | never | 135 s |
| S6 | 1.0 | 1 | 1.37 | 0.73 | 15.5 s | 0.81 &deg;C | 0.81, 0.44, 0.25, 0.15 | 674 s | 104 s |
| S7 | 1.0 | 5 | 5.27 | 0.19 | 10.8 s | 0.30 &deg;C | 0.30, 0.00 | 54 s | 80 s |

The 0.25 on the page snaps to 0.26 in the GUI (the K<sub>i</sub> slider moves
in 0.02 steps); ρ<sub>I</sub> is 0.11 either way.

**What it shows.**

- ρ<sub>I</sub> predicts the outcome before the run: well below 1 decays fast,
  just below 1 decays slowly, above 1 grows. All seven agreed with the
  prediction made from the displayed K<sub>i,crit</sub>.
- Raising K<sub>i</sub> shortens the initial correction (rise 16.4 to 9.8 s)
  while making the final settling slower (61 s, 169 s, then never). Faster
  approach and quicker settling pull in opposite directions.
- Lowering G, at fixed gains, lowers K<sub>i,crit</sub>: more internal lag
  leaves less room for integral action. The same K<sub>i</sub> = 1.0 is well
  damped at G = 5, rings at G = 1 and is unstable at G = 0.5.
- The growing runs (S4, S5) stay inside the PWM limit for the 600 s shown, so
  their growth is the linear instability itself, not saturation.
- Moving C<sub>T</sub>/C to either extreme at G = 2, K<sub>i</sub> = 1.0
  raises K<sub>i,crit</sub> and suppresses the ringing: C<sub>T</sub>/C = 0.1
  gives ρ<sub>I</sub> = 0.19 and 0.9 gives 0.13, each with a single overshoot
  of about 0.3 &deg;C and settling in 53 s and 106 s, against 0.55 &deg;C and
  169 s at 0.35. With most of the capacitance in one lump, one of the two
  states barely matters and the loop behaves almost like one lump again.

---

**Simulator quirks found.** The K<sub>i</sub> slider moves in steps of 0.02
and the program re-applies it on every redraw, so a typed 0.05 becomes 0.06.
Any field whose enabled state changes (switching measured / direct constants,
one_lump / two_lump, p / pi) is rounded to its slider step at that moment.
Set the dropdowns first, then type values, then check them.
