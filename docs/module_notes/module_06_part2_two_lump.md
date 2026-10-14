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
