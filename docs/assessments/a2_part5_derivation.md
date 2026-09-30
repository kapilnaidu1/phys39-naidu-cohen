# A2 item 3: the Part 5 derivation

Naidu / Cohen. Worth **3 of the 10 points**, the heaviest single item, and it
needs no measurements. Only the final number needs `r`.

C4 oral question 3 is this derivation spoken aloud, so the goal is to be able
to reproduce it, not to paste it.

---

## 3a. PWM average-current proof

Over one PWM period `tau`, the current is `I` for a time `D*tau` and zero for
the remaining `(1-D)*tau`, where `D = |u|/255`.

**Mean current.**

```
<I> = (1/tau) * integral_0^tau I(t) dt
    = (1/tau) * [ I * (D tau)  +  0 * (1-D) tau ]
    = (1/tau) * I D tau
    = D I                                              [1]
```

**Mean square current.** The integrand is `I^2` on the same on-interval and
zero elsewhere, because `0^2 = 0`:

```
<I^2> = (1/tau) * integral_0^tau I(t)^2 dt
      = (1/tau) * [ I^2 * (D tau)  +  0 * (1-D) tau ]
      = D I^2                                          [2]
```

### Why the mean square is not the square of the mean

Squaring and averaging do not commute. From [1],

```
<I>^2 = (D I)^2 = D^2 I^2
```

while [2] gives `<I^2> = D I^2`. So

```
<I^2> / <I>^2 = (D I^2) / (D^2 I^2) = 1/D
```

They agree only at `D = 1`, and the discrepancy grows as the duty falls.
The reason is that averaging throws away information about how the current is
distributed in time. Squaring first weights the on-interval by `I^2` before
that information is lost; averaging first replaces a waveform that is
sometimes `I` and sometimes `0` with a constant `DI` that the current never
actually takes.

### Why this matters for our measurement

Peltier transport follows `<I>` and Joule heating follows `<I^2>`. From [1]
and [2], at fixed on-state current **both are linear in `D`**:

```
Peltier   proportional to   <I>   = D I      linear in D
Joule     proportional to   <I^2> = D I^2    linear in D
```

Both heat rates scale the same way with duty, so their combination does too,
so **the susceptibility should be approximately constant and the graph
approximately straight.**

Had we wrongly used `<I^2> = <I>^2 = D^2 I^2`, the Joule term would be
quadratic in duty while the Peltier term stayed linear. Their balance would
shift along the axis, the susceptibility would vary with `D`, and both
branches would be visibly curved.

**So the straightness of our graph is a test of this result.** A straight line
is evidence for `<I^2> = D I^2`; systematic curvature would be evidence
against it, or against holding `I` fixed.

> This is a property of PWM specifically. A DAC delivering a steady current of
> adjustable amplitude has no time variation within a period, so there
> `<I^2> = <I>^2` and the Joule term really would be quadratic in the control
> variable.

*Fill in from our graph: observed linearity or curvature, and whether it
matches the PWM prediction.*

---

## 3b. Steady-state energy balance

Starting from

```
C dT/dt = Q_TEC - G (T - T0)
```

At steady state `dT/dt = 0`, so

```
G (T - T0) = Q_TEC                                     [3]
```

The individual flows are **not** zero. Their sum is. That follows from energy
conservation alone and does not depend on the model.

### Enumerating the terms and their directions

With signed duty `d = u/255` and `D = |d|`. Peltier reverses with the current;
Joule heating does not, since it depends on `I^2`.

```
Q_TEC = d * Qp  +  |d| * Qj                            [4]
```

**Heating branch, `d > 0`,** so `|d| = d`:

```
Q_TEC,h = d (Qp + Qj)        > 0
```

Peltier pumps heat **into** the object and Joule heating also lands **into**
it. They add. The object sits above `T0`, so `G(T - T0) > 0` and passive
conduction carries heat **out** to the surroundings. Balance: what the TEC
delivers, conduction removes.

**Cooling branch, `d < 0`,** so `|d| = -d`:

```
Q_TEC,c = d Qp + (-d) Qj = d (Qp - Qj)       < 0  when Qp > Qj
```

Peltier now pumps heat **out** of the object, but Joule heating still goes
**in**, because reversing current does not reverse `I^2`. They oppose. The
object sits below `T0`, so `G(T - T0) < 0` and conduction carries heat **in**
from the surroundings. Balance: what the TEC removes, conduction supplies.

> Cooling works at all only while `Qp > Qj`. If Joule heating exceeded Peltier
> pumping, the "cooling" branch would heat the object. This is the same
> physics that gave a finite cold limit in Module 3, where the plate bottomed
> out at -6.79 C and then warmed under unchanged full cooling command.

### Solving and differentiating

Substituting [4] into [3]:

```
T_h(d) - T0 = d (Qp + Qj) / G
T_c(d) - T0 = d (Qp - Qj) / G
```

Both are linear in `d` with `T0` as the common intercept, so differentiating
with respect to the signed duty cycle:

```
dT_h/dd = (Qp + Qj) / G                                [5]
dT_c/dd = (Qp - Qj) / G                                [6]
```

Both are positive whenever `Qp > Qj`, and [5] exceeds [6] because `Qj` is
added in one and subtracted in the other. **That single sign difference is the
entire origin of the asymmetry.**

---

## 3c. The slope ratio, and the numerical result

We measure against signed PWM `u`, not signed duty `d`. Since `d = u/255`,

```
m = dT/du = (dT/dd)(dd/du) = (1/255) dT/dd
```

so

```
m_h = (1/255) (Qp + Qj) / G
m_c = (1/255) (Qp - Qj) / G
```

Both the `1/255` and the `G` are common factors, so they **cancel from the
ratio**:

```
r = m_h / m_c = (Qp + Qj) / (Qp - Qj)                  [7]
```

This is why `r` is worth measuring: it is independent of `G`, which we never
determined, and independent of the PWM scaling.

Solving [7] for the heat-rate ratio:

```
r (Qp - Qj) = Qp + Qj
r Qp - r Qj = Qp + Qj
r Qp - Qp   = Qj + r Qj
Qp (r - 1)  = Qj (r + 1)
```

```
  Qj / Qp = (r - 1) / (r + 1)                          [8]
```

**Algebra check.** `r = 2` gives `(2-1)/(2+1) = 1/3`. Matches the assignment.

**Sanity limits.** `r = 1` gives `Qj/Qp = 0`, no Joule heating and symmetric
branches. As `r` grows, `Qj/Qp` approaches 1, meaning Joule heating approaches
Peltier pumping and the cooling branch flattens toward zero slope: the module
stops being able to cool.

### Our number

Measured 30 September 2026, five points per branch, `T0 = 21.54 C`.

| | value | fit range | R squared |
|---|---|---|---|
| m_h | **0.5013 C per PWM count** | u = 0 to +50 | 1.0000 |
| m_c | **0.1809 C per PWM count** | u = -65 to 0 | 0.9989 |
| r = m_h/m_c | **2.771** | | |
| **Qj/Qp = (r-1)/(r+1)** | **0.470** | | |

So the Joule heat delivered to the object face is about **47% of the Peltier
pumping** at full duty.

The heating branch is straight to one part in a thousand, which is the
prediction of 3a arriving on the bench: both contributions linear in D gives a
constant susceptibility. Predicting the u = 38 point from the u = 12 and 25
points gave 40.6 C against 40.61 C measured.

---

## Item 6: passive conduction

**Object hotter than the room:** heat flows **out** of the object.
**Object colder than the room:** heat flows **in**.

Either way the flow drives the object back toward room temperature, so
conduction opposes the TEC on both branches. It is a restoring term, which is
why it appears as `-G(T - T0)` with a single positive `G`.

**Why it cannot explain the unequal slopes.** Look at where `G` sits in [5]
and [6]: it is the same `G` in the denominator of both. Conduction therefore
sets the **scale** of both susceptibilities, and a larger `G` makes both
branches flatter, but it enters them identically and **cancels exactly from
the ratio** in [7]. A symmetric term cannot produce an asymmetric result.

The asymmetry survives in the numerators, where `Qj` is added on the heating
branch and subtracted on the cooling branch. **Peltier transport reverses with
the current; Joule heating does not.** That is the whole explanation, and it
is the answer to C4 oral question 3.
