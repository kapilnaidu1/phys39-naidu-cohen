# Module 8: The Angstrom Experiment, Made Understandable
Plain-language preview, lab checklist, and calculation walkthrough

**The whole experiment in one sentence:** make the temperature at one end of an aluminum rod rise and fall like a sine wave, then measure how much smaller and later that wave becomes at sensors farther along the rod.

Use this as a companion to the official assignment and your instructor's directions. Some equations and numeric settings disappeared from the pasted assignment. This guide restores the core physics, but it does not guess missing safety limits, controller gains, or required tolerances. Use the values in the complete course handout and the live lab instructions.

## 1. The picture to keep in your head

The TEC is the heater/cooler. It tries to make a repeating temperature wave. Heat takes time to travel through the aluminum, and some heat leaks from the rod into the room. So farther from the TEC, the wave should be smaller and should arrive later.

```text
TEC actuator       rod boundary             farther along the rod
TEC sensor          T1, x = 0                T2       T3       T4       T5
   |                    |                     |        |        |        |
   v                    v                     v        v        v        v
 [ TEC ]  ========= [ T1 ] =============== [ T2 ] == [ T3 ] == [ T4 ] == [ T5 ]
                       x increases --------------------------------------->

T1:    large wave, early
T3:       smaller wave, later
T5:          still smaller wave, later again
```

The TEC thermistor and T1 are not the same measurement. The TEC thermistor measures the actuator plate. **T1, in the first rod hole, measures the rod boundary used in the Angstrom calculation.** T2-T5 measure the downstream rod response.

## 2. What each channel tells you

| Channel | What it measures | How you use it |
|---|---|---|
| TEC | Temperature inside/on the TEC base | Check actuator tracking and safety; it is not the rod boundary. |
| T1 | Rod temperature at the first rod hole, x = 0 | The measured boundary waveform for the rod model. |
| T2-T5 | Rod temperatures at increasing distance | Measure wave attenuation and delay along the rod. |
| Room | Air temperature around the rod | Needed for excess-temperature and heat-loss interpretation; record it. |

The current sensor map lists T1-T5 at 0, 25.4, 50.8, 76.2, and 101.6 mm from T1, each downstream position measured with about 1 mm uncertainty. Re-check the physical map before the run; if a sensor moves, measure and record its new position.

## 3. What Angstrom's method finds

The rod acts like a low-pass filter for temperature waves. A slow wave has more time to travel far. A fast wave is more strongly reduced and delayed over the same distance.

Two measured patterns carry the answer:

- **Amplitude decay:** fit the size of the sine wave at each sensor. Its amplitude falls approximately exponentially with distance.
- **Phase lag:** fit when each sensor's wave occurs. The farther sensor reaches the same part of the cycle later.

Together, the spatial amplitude slope and spatial phase slope let you estimate thermal diffusivity, the rate coefficient for side heat loss, and, using the aluminum's density and heat capacity, thermal conductivity. You do not need to measure the air-side convection coefficient directly to find diffusivity.

The experiment is not successful just because the setpoint is sinusoidal. Use the **measured T1 waveform** as the boundary and check that it is sufficiently sinusoidal, stable, and safe.

## 4. Preview and lab plan

### Before the run

1. Confirm the channel labels, units, sensor positions, rod diameter and length, room temperature, calibration offsets if approved, and all current safety limits.
2. Confirm T1 is in the first rod hole and T2-T5 are in increasing-x order. Keep the TEC sensor separate in your notes and plots.
3. Check that the Python GUI shows TEC and T1-T5 live, along with requested setpoint, control mode, and applied PWM. Confirm that it saves a local raw record.
4. Write down the team's settling test, planned periods, mean and amplitude, sampling interval, safe limits, and file names. Do not invent the values omitted from your pasted copy of the handout.

### During the pilot

1. Start with the assignment's 100-second period. Use the approved starting mean and amplitude only after checking the actual safety limits.
2. At the same mean, amplitude, and period, compare open-loop feedforward, proportional-only, and PI control. Keep the full time record, including startup and mode changes.
3. For each mode, inspect **measured T1**, not just the requested sine. Compare its mean, amplitude, phase relative to the request, distortion, residuals, and applied PWM.
4. If T1 is clipped, badly distorted, drifting, or unsafe, stop or retune according to the instructor's protocol. Do not treat an ugly boundary as a clean Angstrom input.
5. Use pilot amplitudes and phase differences to choose a second usable period. A longer period generally reaches farther; a shorter period generally makes more attenuation and phase change per meter. Follow the assignment's minimum-period rule.

### For the production data

- Acquire at least five complete cycles **after** the team's quantitative settling test passes, at each of at least two usable periods.
- Retain measurable amplitude and phase at three or more rod sensors. Five cycles is a minimum amount to keep, not a settling test by itself.
- Log all six temperatures on one synchronized record. Keep startup transients and every frequency transition in the raw file; mark the stable analysis windows later.
- Save the sensor map, room temperature, control settings, frequency/step events, units, sampling interval, and safety events with the run.
- Preserve raw data unchanged. Apply offsets, corrections, exclusions, and fits in analysis code or copies.

### What to compare in the three control modes

| Mode | Plain-language meaning | What to look for |
|---|---|---|
| Open loop | Use the measured steady heating/cooling calibration to choose PWM, without correcting live temperature error. | Does T1 follow the requested wave? Are heating and cooling halves asymmetric? |
| P-only | PWM responds to the current temperature error. | Does it reduce error? Is there a remaining offset or phase lag? |
| PI | P responds now; I responds to accumulated error. | Does it improve tracking without windup, clipping, drift, or distortion? |

Heating and cooling may need different PWM magnitudes. Use your measured heating-to-cooling response ratio or inverse calibration, not a guessed symmetric PWM sine. Apply saturation and the required PI anti-windup. Never energize both H-bridge directions at once.

For a quick susceptibility estimate, measure the temperature change per PWM magnitude separately on the heating and cooling branches:

```text
chi_heat = |temperature change| / |heating PWM|
chi_cool = |temperature change| / |cooling PWM|
cooling multiplier = chi_heat / chi_cool
```

Practice numbers only: if heating changes temperature by 0.10 C per PWM unit and cooling by 0.05 C per PWM unit, then the cooling multiplier is 0.10/0.05 = 2. A 40-unit heating command would correspond roughly to an 80-unit cooling magnitude for the same steady temperature change. Your actual controller should use your measured curves, sign convention, and PWM saturation; this simple ratio is only a starting estimate.

To compare TEC tracking, fit the requested setpoint and measured T1 over the same stable interval and period:

```text
T1 amplitude tracking ratio = fitted T1 amplitude / requested setpoint amplitude
T1 phase lag = requested-setpoint phase - measured-T1 phase
residual RMS = sqrt(mean((measured T1 - fitted T1)^2))
```

Report these values with the T1 sine fit. State your settling tolerances before analyzing the run; for example, require fitted cycle-to-cycle mean, amplitude, and phase changes to stay below the team's chosen limits over repeated cycles. The assignment's exact tolerances are missing from the pasted copy, so obtain them from the instructor rather than copying an example threshold.

## 5. The equations, translated

Use excess temperature `theta = T - T_room`. The one-dimensional rod model is:

```text
d(theta)/dt = kappa * d2(theta)/dx2 - nu * theta
```

Here `kappa` is thermal diffusivity in m^2/s. It describes how quickly a temperature pattern spreads along the rod. `nu` is the side-loss rate in 1/s. It describes how quickly the rod loses excess heat to the room. The model assumes constant properties, a fixed room temperature, approximately linear side loss, and a cross-section that is nearly one temperature.

For sinusoidal forcing at angular frequency `omega = 2*pi/P`, the ideal semi-infinite rod response can be written:

```text
theta(x,t) = B0 * exp(-q*x) * cos(omega*t - q_prime*x)
```

`q` describes amplitude decay per distance; `q_prime` describes phase lag per distance. Both have units 1/m and should be positive in this convention. At x = 0, the wave has amplitude B0. At larger x, its amplitude is multiplied by `exp(-q*x)` and its lag is `q_prime*x` radians.

The two useful relations are:

```text
q^2 - q_prime^2 = nu / kappa
2*q*q_prime = omega / kappa

kappa = omega / (2*q*q_prime)                  [m^2/s]
nu = kappa * (q^2 - q_prime^2)                 [1/s]
k = rho * cp * kappa                           [W/(m K)]
```

`k` is thermal conductivity; do not confuse it with `kappa`, the diffusivity. `rho` is aluminum density in kg/m^3 and `cp` is specific heat capacity in J/(kg K). Check the material values required by your course before calculating conductivity.

## 6. How to get the numbers from your data

### A. Fit a sine wave to each sensor

Choose a stable time window containing at least five full cycles. Use the same forcing period for all six channels. For each sensor, fit:

```text
T_i(t) = C_i + a_i*cos(omega*t) + b_i*sin(omega*t)

mean temperature: C_i
amplitude:         B_i = sqrt(a_i^2 + b_i^2)
phase:             phi_i = atan2(-b_i, a_i)
```

This phase convention writes the fit as `C_i + B_i*cos(omega*t + phi_i)`. A downstream sensor has a more negative phase. Unwrap phases in sensor order before fitting them against position. Use elapsed seconds from the Arduino timestamps, not row number.

The residual at each sample is `measured temperature - fitted temperature`. Check the residual plot, residual RMS, drift, and obvious clipping or missing samples. A sine fit can return numbers even when the waveform is not a good sine; inspect the plot.

### B. Fit the spatial slopes

Convert sensor positions to meters. Fit straight lines to the retained sensors:

```text
ln(B_i) = intercept - q*x_i
phi_i   = intercept - q_prime*x_i

q       = negative slope of ln(amplitude) versus x    [1/m]
q_prime = negative slope of unwrapped phase versus x   [1/m]
```

Use measured positions and their uncertainties. Plot the points and fitted lines. If points curve or one sensor is far off the line, investigate finite tip effects, sensor lag, poor signal-to-noise, incorrect sensor positions, settling, and boundary distortion before deciding whether to exclude anything.

### C. Calculate diffusivity and side loss

First calculate the angular frequency from the measured/requested period:

```text
omega = 2*pi/P                                      [rad/s]
```

Then insert the spatial slopes in the inverse equations:

```text
kappa = omega / (2*q*q_prime)                       [m^2/s]
nu    = kappa * (q^2 - q_prime^2)                   [1/s]
k     = rho*cp*kappa                                [W/(m K)]
```

Radians are dimensionless. For the first equation, `(1/s)/((1/m)*(1/m)) = m^2/s`. For the second, `(m^2/s)*(1/m^2) = 1/s`. A negative `nu` is not something to silently replace with zero; it is a warning to check uncertainties, signs, settling, and the model assumptions.

If the course also asks for the convection coefficient `h`, use the circular-rod geometry:

```text
A/P = d/4
nu = h*P/(rho*cp*A)
h = rho*cp*(A/P)*nu                              [W/(m^2 K)]
```

`A` is cross-sectional area, `P` is exposed perimeter, and `d` is measured diameter. The periodic data give `kappa` and `nu`; `h` follows only after supplying the material properties and geometry.

## 7. Worked practice example (not lab data)

These are made-up, rounded values to show the arithmetic. **Do not report them as your measurements.** Imagine a 480 s period and fitted amplitudes/phases like these:

| Sensor | x (m) | Amplitude B (C) | Unwrapped phase phi (rad) |
|---|---:|---:|---:|
| T1 | 0.0000 | 1.50 | 0.00 |
| T2 | 0.0254 | 1.17 | -0.24 |
| T3 | 0.0508 | 0.91 | -0.48 |
| T4 | 0.0762 | 0.71 | -0.71 |
| T5 | 0.1016 | 0.56 | -0.95 |

Use the endpoints for a quick slope estimate (a real analysis fits all retained sensors):

```text
q = ln(B_T1/B_T5) / (x_T5 - x_T1)
  = ln(1.50/0.56) / 0.1016 m
  = 9.70 1/m

q_prime = (phi_T1 - phi_T5) / (x_T5 - x_T1)
        = (0.00 - (-0.95)) / 0.1016 m
        = 9.35 1/m
```

Now calculate the forcing frequency and diffusivity:

```text
omega = 2*pi/480 s = 0.01309 rad/s

kappa = 0.01309 / (2 * 9.70 * 9.35)
      = 0.0000722 m^2/s
```

Then calculate side loss:

```text
nu = 0.0000722 * (9.70^2 - 9.35^2)
   = 0.00048 1/s
```

If, for illustration only, you use `rho = 2700 kg/m^3` and `cp = 896 J/(kg K)`:

```text
k = 2700 * 896 * 0.0000722
  = about 175 W/(m K)
```

The result is approximate because the example slopes are rounded. Your submitted result should come from fitted slopes, not the two-endpoint shortcut, and should include uncertainty.

## 8. Model-validity checks and uncertainty

### Finite length

The analytic Angstrom equations above assume a semi-infinite rod. Your rod has a tip. Let `L` be the measured distance from T1 to the tip, `x` a sensor position, and `lambda = q + i*q_prime`. For a zero-flux tip, compare the finite-rod complex amplitude with the semi-infinite one:

```text
finite ratio:       cosh(lambda*(L - x)) / cosh(lambda*L)
semi-infinite ratio: exp(-lambda*x)
relative difference:
abs(finite ratio - semi-infinite ratio) / abs(finite ratio)
```

Calculate this at each retained sensor using the measured `L`. State the tolerance your course requires. Tip effects are usually most important for sensors nearest the tip and for long-period waves that penetrate farther.

### Cross-section temperature

For a round rod, estimate the radial/transverse Biot number:

```text
Bi_r = h*(A/P)/k = (A/P)^2 * nu/kappa
A/P = d/4, so Bi_r = (d/4)^2 * (q^2 - q_prime^2)
```

Use measured diameter. A value much smaller than 0.1 supports treating each cross-section as nearly uniform; apply the exact criterion specified in your course. This check is not independent proof of the 1-D model, so also use residuals and repeat-frequency consistency.

### Settling, repeatability, and uncertainty

- Decide settled from repeated-cycle behavior: fitted mean, amplitude, and phase should stop trending within a tolerance your team states. Do not decide from elapsed cycles alone.
- Compare frequencies: each frequency gives its own `q` and `q_prime`, but inferred `kappa` and `nu` should agree within uncertainty if the model and measurements are adequate.
- Estimate uncertainty in the trace fits and spatial slopes. Include sensor-position uncertainty and period/timing uncertainty. A practical method is to resample cycles and positions, recalculate slopes and derived values many times, and report the resulting spread.
- Report residuals and any excluded channel/time interval with a reason. Do not discard inconvenient points just to make a straight line.
- Check that `q > 0`, `q_prime > 0`, and `nu` is physically plausible within uncertainty. A strongly frequency-dependent result may signal an invalid approximation, poor tracking, sensor lag, or a bad fit.

## 9. What the existing Module 8 data can and cannot do

The repository's October 2026 records document calibration and a non-oscillating 20-to-45 C step. The 28 October step run is useful for understanding that T1 differs from the TEC sensor and downstream sensors respond later, but it is **not** a sinusoidal Angstrom dataset. It cannot provide the periodic amplitude and phase slopes needed for `kappa` and `nu`.

For the periodic experiment, use the new synchronized six-channel GUI record. The assignment's serial schema includes time, run state, control mode, schedule step, forcing parameters, TEC and T1-T5 temperatures, controller/feedforward command, heating-to-cooling ratio, and signed PWM. Keep one stable record format and document placeholders for fields that do not apply.

## 10. Checklist before calling a run usable

- [ ] T1-T5 labels and measured positions agree with the sensor map; T1 is x = 0.
- [ ] TEC and all five rod temperatures display live and are saved on one time base.
- [ ] Room temperature, units, sampling interval, period, mean, amplitude, controller settings, and safety limits are recorded.
- [ ] Requested and measured T1 waveforms are compared; measured T1 is used as the model boundary.
- [ ] Settling criterion is stated and passed before the five or more retained cycles begin.
- [ ] At least two periods are usable, with measurable amplitude and phase on at least three rod sensors per period.
- [ ] Startup, frequency changes, and safety events remain in the untouched raw file and are marked for later analysis.
- [ ] Per-sensor sine fits, spatial plots, residuals, uncertainty, finite-length check, and transverse-Biot check are planned.

**A one-line summary you can say out loud:** “We drive T1 periodically, fit the amplitude and phase at each rod position, use how those two quantities change with distance to infer diffusivity and side loss, then check whether the real finite rod behaves enough like the model.”

Sources used for this companion guide: the Module 8 Part I assignment supplied in the conversation; `docs/module_notes/module_08_rod_instrument.md`; `docs/module_notes/module_08_stationary_fin.md`; `docs/module_notes/module_08_placement_calc.md`; and `data/module_08/sensor_map.csv`. The worked values above are illustrative only.