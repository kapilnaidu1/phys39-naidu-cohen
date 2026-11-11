# Module 8, S18.4: positive-only sinusoidal PWM, step by step (SAMMY copy)

A page prepared before the S18.4 run. **No S18.4 data have been recorded yet**, so every number below is a prediction. It is made from the S18.3 run
`sammy_angstrom_live_20261111_122227.csv` (the Module 6 one-lump model fitted to it) and from the PI hold of 10 November (`sammy_angstrom_live_20261110_164057.csv`). Once the S18.4 file exists,
these predictions are what it is compared with. Companion page: [Sammy_Module_8_S18_3_Raw_PWM_Walkthrough.md](Sammy_Module_8_S18_3_Raw_PWM_Walkthrough.md).
Figures: `docs/figures/module_08_sammy/s184_*.png`. Kapil Naidu's acquisition code, analysis scripts and data are unchanged; everything here is an addition.

The mean TEC temperature that the page asks for disappeared from the pasted assignment text. This page works with T* = 40 °C, the mean of the sketch's default
setpoint (Ta = 40 °C); section 4 gives the formula and a table for other targets.

## 0. The question, and the short answer

S18.3 swung the PWM around zero, u = U sin(ωt), so the current reversed twice per cycle. S18.4 swings it around U0 = U instead:

```text
u(t) = U0 + U sin(ωt) = U (1 + sin ωt)         0 ≤ u ≤ 2U, never negative
```

The TEC now only heats. The page asks to adjust U until the mean TEC temperature is about T*, to keep the swing safe, and to compare with S18.3, so as to decide
which of the S18.3 asymmetries come from reversing the TEC current and which are still there when the current keeps one direction.

**Predictions for U0 = U = 36 counts** (u from 0 to 72), room temperature 24.45 °C:

| Period | Shrink factor N | Amplitude A1 (°C) | Lag behind the PWM | Highest TEC (°C) | Lowest TEC (°C) | Highest T1 (°C, estimate) |
| --- | --- | --- | --- | --- | --- | --- |
| 100 s | 0.240 | 3.61 | 1.328 rad = 21.1 s | 43.1 | 35.9 | 36.3 |
| 200 s | 0.444 | 6.67 | 1.111 rad = 35.4 s | 46.2 | 32.8 | 37.7 |
| 500 s | 0.778 | 11.69 | 0.680 rad = 54.1 s | 51.2 | 27.8 | 40.9 |

1. **The mean is set by χh and U, not by an asymmetry.** It is T_amb + χh U = 39.5 °C with the S18.3 fit (χh = 0.417 °C/count), at every period.
   The 10 November PI hold gives 40.5 °C for the same U. Both are within 0.6 °C of the target.
2. **The amplitude is χh U N,** 3.6, 6.7 and 11.7 °C, and **the lag is the same arctan(ωτ) as in S18.3.** The amplitude grows with the period for the same
   reason as before (the plate is a low-pass filter).
3. **The waveform should be a clean sinusoid.** In the model, the second harmonic, the unequal peaks and the unequal slopes of S18.3 come from using two different
   susceptibilities (χh for u > 0, χc for u < 0). With one sign of u there is one susceptibility and they vanish. The S18.4 run tests this.
4. **It is safe by a wide margin.** The highest TEC temperature is about 51 °C at the 500 s period (latch 65 °C); T1 stays near 41 °C (latch 56 °C).
5. **Run 600, 800 and 1500 s** (48.3 min): the first step needs 3 start-up cycles because the plate has to climb 15 °C to the mean (section 5).

## 1. Words and symbols

The symbols u, U, P, ω, T, T_amb, θ = T − T_amb, χh, τ, N, φ and A1 to A3 are explained in the S18.3 page. The new ones:

| Symbol | In plain words |
| --- | --- |
| U0 | the offset: the level the knob swings around. Here U0 = U, so the knob swings between 0 and 2U and never goes below zero |
| T* | the mean TEC temperature we want (here 40 °C) |
| mean rise | χh U0: how much hotter than the room the plate sits on average |
| N = cos φ | the shrink factor 1/√(1 + (ωτ)²). It equals cos φ, because φ = arctan(ωτ), so a measured lag gives N directly |

The bathtub of the S18.3 page again. In S18.3 the tap swung from hot to cold, and the hot tap was stronger. Now only the hot tap is used: it swings between
"off" and "full", so the water level moves up and down around a high average level. The tub is always being warmed; only the amount changes.

## 2. The series of steps for the run

Everything needed is already in the sketch (`SET U`, `SET U0`, mode RAW) and in the GUI (the "RAW mode" box and the schedule box). The "One long run" button runs S18.3 only
(U0 = 0); it is not used here.

1. **Baseline.** Start the GUI (`python3 python/sammy_module8_angstrom_gui.py`) and leave the rig untouched for 2 minutes with nothing started (u = 0). Read the mean of
   T1 to T5 and type it into the note box with the real number, for example `room T baseline 24.3 C (mean of T1-T5, hands off)`.
2. **Settings.** Set mode to RAW. In the RAW mode box set U = 36 and U0 = 36. Click Send settings, then GET, and check that the `# SETTINGS` line shows
   `mode=RAW`, `U=36.0` and `U0=36.0`.
3. **Schedule.** Type these lines in the schedule box (Ta and Tb are ignored in RAW but must be typed). The label under the box should say 3 steps, 48.3 min.
   Click Send schedule and check the listed steps.

```text
600 40 0 100
800 40 0 200
1500 40 0 500
```

4. **Start.** Type the note `S18.4 start, U0 = U = 36` and click START schedule. The applied PWM plot should swing between 0 and 72 counts and never go below 0.
5. **Watch the first step.** The TEC should climb to about 39.5 °C within three or four cycles and then swing between about 36 and 43 °C.
   If the mean of the last three cycles is more than about 2 °C from 40 °C, the new value is U = U_old × (T* − T_amb) / (T_mean − T_amb). The run can be finished anyway, because
   the data are still good for the comparison (section 7), and repeated with the new U if the target mean is required.
6. **Safety.** Press STOP if the TEC passes 56 °C or T1 passes 50 °C; the board latches at 65 and 56 °C and sets the output to 0 on its own.
7. **End.** After the last step the output goes to 0 (`SCHEDULE DONE`). Type the note `S18.4 finished`, close the GUI, and check the file with Check a saved file.

## 3. The math, one step at a time

### 3.1 The push now has one sign

```text
u(t) = U (1 + sin ωt),   0 ≤ u ≤ 2U,   so χ(u) = χh at every moment
τ · dθ/dt + θ = χh U (1 + sin ωt)                               (S18.4.1)
```

Compare with S18.3: the push gained a constant, and the two susceptibilities χh and χc have become one, χh. The equation is linear again, with no |sin| and no case split.

### 3.2 Split the push in two

The push is χh U (a constant) plus χh U sin ωt (a swing). The equation is linear, so the plate's answer to a sum of pushes is the sum of its answers to each push alone.

### 3.3 The constant push

Try a constant θc. Then dθc/dt = 0 and the equation says θc = χh U. In words: hold the knob at U forever and the plate ends up χh U hotter than the room.

### 3.4 The swinging push (the S18.3 steps, with χ = χh)

```text
guess      θs = a sin ωt + b cos ωt                       dθs/dt = a ω cos ωt − b ω sin ωt
put in     (a − ωτ b) sin ωt + (ωτ a + b) cos ωt = χh U sin ωt
match      sine: a − ωτ b = χh U        cosine: ωτ a + b = 0
solve      b = −ωτ a,   a = χh U / (1 + (ωτ)²)
one sine   θs = R sin(ωt − φ),   R = √(a² + b²) = χh U / √(1 + (ωτ)²) = χh U N,   tan φ = ωτ
```

### 3.5 The start-up piece, and the whole answer

A pure leak dies away as e^(−t/τ), and adding C e^(−t/τ) to a solution does not break the equation. So θ(t) = χh U + R sin(ωt − φ) + C e^(−t/τ). The plate starts at the idle
baseline, θ(0) = 0:

```text
0 = χh U + R sin(−φ) + C   →   C = −χh U (1 − N sin φ)
θ(t) = χh U · [ 1 + N sin(ωt − φ) − (1 − N sin φ) e^(−t/τ) ]
```

### 3.6 Check the answer

```text
constant piece:   τ · 0 + χh U = χh U                                      satisfies the equation
swinging piece:   verified in the S18.3 page (section 4.4)
start-up piece:   τ d/dt(C e^(−t/τ)) + C e^(−t/τ) = −C e^(−t/τ) + C e^(−t/τ) = 0
start:            θ(0) = χh U (1 − N sin φ) − χh U (1 − N sin φ) = 0
```

The equation was also integrated numerically (fourth-order Runge-Kutta, 0.05 s steps) from θ = 0 for the three periods with U = 36 and compared with the formula at every step;
the largest difference is 1.6e-13 °C, which is rounding error.

### 3.7 Read the settled solution

```text
mean            T_amb + χh U                  the constant piece, the same at every period
amplitude       R = χh U N = (χh U) cos φ     a fraction N of the mean rise
lag             φ = arctan(ωτ), delay φ/ω     the same as in S18.3: it comes from τ, not from χ
highest/lowest  T_amb + χh U (1 ± N)          symmetric about the mean
shape           a pure sinusoid in this model
```

A slow swing (N near 1) runs from almost the room temperature to almost twice the mean rise; a quick swing (N small) hardly leaves the mean. At 500 s,
N = 0.78, so the plate is predicted to swing 28 to 51 °C around a mean of 39.5 °C. This is why "a safe amplitude" matters here: with U0 = U the swing is tied to the mean.

## 4. Choosing U

The mean is T_amb + χh U0 whatever the period, so with U0 = U:

```text
U = (T* − T_amb) / χh
```

Three estimates of the PWM that holds a mean of 40 °C when the room is at 24.45 °C:

| Source | What it says | PWM (counts) |
| --- | --- | --- |
| Module 4 steady-state curve (the GUI default) | χh = 0.50127 °C/count | 31.0 |
| S18.3 fit (this rig, rod attached) | χh = 0.4175 °C/count | 37.2 |
| 10 November PI hold | the controller held the TEC at 40.05 °C with 36.9 counts on average (sd 0.3; last 100 s of the 5 minute hold, drift 0.004 °C/min) when the TEC idled at 23.58 °C, so χh = 0.447 °C/count | 34.8 |

The Module 4 curve asks for fewer counts because it overestimates this rig's χh. The other two agree within 7 %. **Start with U0 = U = 36.**
An error of 10 % in χh moves the mean by 1.5 °C. The room temperature moves it one for one: on 10 November the idle TEC reading drifted by 0.4 °C in three minutes.

For another target mean the same recipe gives (U is the mean of the S18.3-fit and the PI-hold estimates, rounded):

| T* (°C) | U = U0 (counts) | A1 at 100 s (°C) | A1 at 200 s (°C) | A1 at 500 s (°C) | Highest TEC at 500 s (°C) | Safety |
| --- | --- | --- | --- | --- | --- | --- |
| 30 | 13 | 1.3 | 2.4 | 4.2 | 34 | ok |
| 35 | 24 | 2.4 | 4.4 | 7.8 | 42 | ok |
| 40 | 36 | 3.6 | 6.7 | 11.7 | 51 | ok |
| 45 | 48 | 4.8 | 8.9 | 15.6 | 60 | above 56 °C, not advised |
| 50 | 59 | 5.9 | 10.9 | 19.2 | 68 | above the TEC latch |

## 5. What to expect

![planned run](../figures/module_08_sammy/s184_predicted_run.png)

*The model response to the planned schedule. Hatched: the start-up cycles that are skipped. Green dashed: the target mean. Red solid: the TEC latch.*

**Start-up.** The plate starts at the room temperature, so the first step has to climb 15 °C to the mean. The leftover of that climb at the start of a cycle is
C e^(−t/τ) with |C| = 11.5 °C at the first step. Counting a cycle as settled once the model's start-up error is below 0.2 °C gives:

| Step | Cycles | Start-up error at the start of cycle 1, 2, 3, 4 (°C) | Cycles to skip | Settled cycles |
| --- | --- | --- | --- | --- |
| 1: 100 s | 6 | 11.52, 2.44, 0.52, 0.12 | 3 | 3 |
| 2: 200 s | 4 | 2.46, 0.09, 0.02, 0.02 | 1 | 3 |
| 3: 500 s | 3 | 1.35, 0.03, 0.03 | 1 | 2 |

The later steps start from the state the previous step left, which is already close to the new settled cycle. This plan gives 3, 3 and 2 settled cycles (S18.3 had 3, 3 and 2).

**Safety.** The highest values in the table of section 0 are the model's; the T1 estimate scales the S18.3 rod response (T1 amplitude over TEC amplitude 0.26, 0.35, 0.47; mean rise of T1 over mean rise of the TEC up to 0.73) and is good to a degree or two.

## 6. S18.3 against S18.4

|  | S18.3 (U0 = 0, U = 50) | S18.4 (U0 = U) |
| --- | --- | --- |
| PWM range | −50 to +50 counts | 0 to 72 counts |
| susceptibility that acts | χh when u > 0, χc when u < 0 | χh all the time |
| mean above the room | (χh − χc) U / π, from the asymmetry | χh U0, the plain heating |
| amplitude of the swing | χavg U N, with χavg = (χh + χc) / 2 | χh U N |
| lag | arctan(ωτ) | arctan(ωτ) |
| second harmonic | (4 Δχ U / 3π) N2, Δχ = (χh − χc) / 2 | 0 |
| peaks above / dips below the mean | more than 1 | 1 |

With the numbers (S18.3 measured; S18.4 predicted for the planned U):

|  | S18.3 100 s | S18.3 200 s | S18.3 500 s | S18.4 100 s | S18.4 200 s | S18.4 500 s |
| --- | --- | --- | --- | --- | --- | --- |
| mean above the room (°C) | 4.13 | 4.31 | 4.28 | 15.03 | 15.03 | 15.03 |
| amplitude A1 (°C) | 3.81 | 6.60 | 10.88 | 3.61 | 6.67 | 11.69 |
| lag (s) | 23.0 | 35.6 | 54.9 | 21.1 | 35.4 | 54.1 |
| A2 / A1 | 10.2 % | 11.0 % | 13.8 % | 0 % | 0 % | 0 % |
| peaks above / dips below | 1.10 | 1.18 | 1.29 | 1.00 | 1.00 | 1.00 |
| steepest rise / steepest fall | 1.37 | 1.27 | 1.13 | 1.00 | 1.00 | 1.00 |

![shapes](../figures/module_08_sammy/s184_predicted_shapes.png)

*One cycle of the settled S18.3 data (gray dots, black fit), each normalised by its own amplitude and shifted by its own lag, against the pure sinusoid predicted for S18.4 (blue dashed). The taller, earlier peak and the shallower, flatter trough of the S18.3 curves are the second harmonic.*

**How to read the result when it exists.** The S18.3 distortions are the reference; what S18.4 still shows is not caused by reversing the current.

| Feature | S18.3 measured | S18.4 if reversing the current were the only cause | If S18.4 still shows it |
| --- | --- | --- | --- |
| second harmonic A2/A1 | 10 %, 11 %, 14 % | about 0 % | the heating response itself is not linear in u (for example Joule heating grows as u²) |
| peaks above / dips below | 1.10, 1.18, 1.29 | 1.00 | the same cause: the heating response is not linear in u |
| mean rise against χh U0 | not applicable (two χ) | T_amb + χh U0 = 39.5 °C | χh depends on u (the PWM now reaches 2U), or the room temperature changed |
| amplitude against the single-τ prediction | +12 %, +5 %, −1 % | no change expected from polarity | the same deviations mean the plate and rod are not one lump |
| lag against arctan(ωτ) | +0.11 rad, +0.01 rad, +0.01 rad | no change expected from polarity | the same, a property of the thermal system |

## 7. After the run: what to compute

Fit the settled whole cycles of each step exactly as in S18.3 (mean, three harmonics, drift; the lag against the PWM). Then, with the measured mean, A1 and lag φ at each period:

```text
χh from the mean        χh = (T_mean − T_amb) / U0
χh from the swing       χh = A1 / (U cos φ)             (N = cos φ, so the measured lag removes τ)
τ from the lag          τ = tan φ / ω
distortion              A2/A1, peaks above / below the mean, steepest rise / fall
```

If the one-lump model with one heating susceptibility holds, the two χh agree with each other and with the S18.3 fit (0.417 °C/count) and τ is near 64 s. The measured mean should be within a
degree or two of the target. The tables, figures and comparison with the S18.3 page are produced from the S18.4 file by an analysis script that is still to be written;
it needs only the heating-only version of the S18.3 fits, because there is no cooling branch to fit.

## 8. Limits of these predictions

- No S18.4 run exists. T* = 40 °C and the room temperature of 24.45 °C (the S18.3 idle baseline) are assumptions; use the numbers of the day.
- χh is taken constant. S18.3 covered u from 0 to 50 counts, S18.4 goes to 72; the 10 November hold at 37 counts supports the value, but the response between 50 and 72 counts has not been measured.
- The one-lump model missed the S18.3 amplitude by +12 %, +5 % and −1 % and the lag by +0.11 rad at 100 s, so the amplitudes and lags above are good to about 10 %.
- The T1 numbers scale the S18.3 rod response and are estimates.
- The one-click plan in the GUI is S18.3 only; S18.4 is run with the boxes as in section 2.

## 9. Files and how to reproduce

```bash
python3 python/sammy_module8_s184_page.py --target 40
```

It fits the S18.3 run `sammy_angstrom_live_20261111_122227.csv`, reads the PI hold of `sammy_angstrom_live_20261110_164057.csv`, and rewrites this page and the two figures.

## AI assistance

This page, its script and its figures were produced with GitHub Copilot assistance and checked against the Module 8 page, the Module 6 model, the sketch and the GUI code,
the S18.3 run and the 10 November hold. The derivation in section 3 was also verified numerically (section 3.6).
