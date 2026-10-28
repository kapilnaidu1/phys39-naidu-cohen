# Sammy Module 7 Rod Run: Preliminary Calculations and Fits
Run: `sammy_rod_run_20261028_114042.csv` (28 Oct 2026). Raw CSV, metadata, notes, sensor map, and prior runs are left unchanged.
## Scope and assumptions
- 5414 rows from 1.34 to 3018.76 s (50.29 min). The 45 C controlled segment ended at 3012.12 s.
- Last 40 minutes are summarized as requested. The final 10 minutes are used as the primary stationary window because each rod channel's linear drift is below 0.01 C/min. The last 5 minutes are included as a sensitivity check.
- `T_room` is provisionally estimated as the mean of the five rod channels over the first 30 s: 22.081 C. Initial rod-channel mean spread is 0.467 C; including the TEC-base channel the spread is 0.961 C. This is a startup room baseline, not a documented mixed common-bath calibration. No offsets are applied.
- The sensor map has blank measured-position and resistor fields. Fits use planned positions 0, 50.8, 101.6, 152.4, 203.2 mm and a rough prior length L=279.4 mm. The resulting m fits are provisional; no formal parameter uncertainty is reported.
- The rod sensors were taped, not glued. Tape/contact affects sensor lag and may cause channel-specific thermal contact bias. Plot smoothing is off and all analysis uses raw logged values.
- Control chronology: target changed from 30 to 45 C at about 31.79 s; PI mode Kp=12 began at about 39.60 s, control was enabled at 80 s, Ki=0.2 was selected at about 257.89 s, and control was switched off at 3012.12 s. The TEC-base peak was 51.86 C at 279.30 s, 6.86 C above the 45 C setpoint.

## Time windows
| Channel | Last 40 min mean (C) | Last 10 min mean (C) | Last 10 min drift (C/min) | Last 10 min range (C) | Last 5 min mean (C) |
|---|---:|---:|---:|---:|---:|
| T_T1_C | 37.520 | 37.683 | +0.0084 | 0.170 | 37.702 |
| T_T2_C | 34.298 | 34.511 | +0.0094 | 0.240 | 34.532 |
| T_T3_C | 32.356 | 32.604 | +0.0079 | 0.260 | 32.621 |
| T_T4_C | 30.901 | 31.192 | +0.0042 | 0.200 | 31.202 |
| T_T5_C | 30.166 | 30.481 | +0.0036 | 0.220 | 30.490 |

Stationarity check: all five last-10-minute linear drift estimates have absolute value <= 0.01 C/min. This supports using that interval under the example criterion. The last 40-minute means include more of the approach and are not used as the primary stationary profile.

### Worked final-window example: T1
The selected interval is 2412.62 to 3012.12 s and contains 1073 readings. For T1 the sum is 40433.9700 C-samples:

```text
mean T1 = sum(T1 readings)/N = 40433.9700/1073
         = 37.68310 C
linear drift = fitted slope * 60 = +0.00838 C/min
```

The drift estimate uses a least-squares line through the entire window, not just the difference between two noisy endpoint readings.

### Worked startup room estimate and common-bath warning
For the first 30 s, 52 rows were recorded. The five rod-channel means were:

```text
T_T1_C: 22.36500 C
T_T2_C: 21.89846 C
T_T3_C: 22.09135 C
T_T4_C: 21.92962 C
T_T5_C: 22.12173 C
T_room estimate = (22.36500 + 21.89846 + 22.09135 + 21.92962 + 22.12173)/5
                = 22.08123 C
rod channel spread = max - min = 0.46654 C
all six channel spread including base = 0.96115 C
```

This is a room-temperature startup baseline, not a controlled common-bath check. It shows a noticeable inter-channel spread, so do not claim the calibration check passed and do not invent/apply offsets. Perform the official common-bath procedure and confirm its acceptance threshold; then either retain raw values or apply documented corrections if required.

## Provisional fin fits
Use theta = T - T_room and fit the stationary models to the final-10-minute means. For each fixed m, theta0 is solved by least squares; m is selected by a dense one-dimensional grid search. Fits are unweighted because channel calibration/position uncertainties are not established. RMSE is descriptive, not a significance test.
| Window | Model | m (1/m) | 1/m (mm) | theta0 (C) | RMSE (C) | far ratio theta5/theta1 |
|---|---|---:|---:|---:|---:|---:|
| last40 | finite insulated tip | 4.843 | 206.5 | 15.292 | 0.141 | 0.518 |
| last40 | semi-infinite | 3.397 | 294.4 | 15.023 | 0.402 | 0.501 |
| last10 | finite insulated tip | 4.716 | 212.0 | 15.445 | 0.150 | 0.532 |
| last10 | semi-infinite | 3.249 | 307.7 | 15.170 | 0.413 | 0.517 |
| last5 | finite insulated tip | 4.716 | 212.0 | 15.466 | 0.148 | 0.532 |
| last5 | semi-infinite | 3.250 | 307.7 | 15.191 | 0.411 | 0.517 |

### Worked excess-temperature ratio
For the primary last-10-minute window, estimate room temperature from the initial rod baseline, then subtract it from each stationary mean. For T1 and T5:

```text
theta1 = T1_mean - T_room = 37.68310 - 22.08123 = 15.60187 C
theta5 = T5_mean - T_room = 30.48077 - 22.08123 = 8.39954 C
theta5/theta1 = 8.39954/15.60187 = 0.53837
placement target 1/e = 0.36788
```

The observed ratio does not meet the 1/e placement target. The target is a criterion to test, not a guarantee that the available rod reaches it.

### Worked fit method and per-sensor comparison
Let f_i(m) be the model shape at sensor x_i. For the finite model, f_i=cosh[m(L-x_i)]/cosh(mL); for the semi-infinite model, f_i=exp(-m x_i). For each trial m, choose the amplitude theta0 that minimizes the sum of squared residuals. Differentiate the squared error with respect to theta0, set that derivative to zero, and solve:

```text
SSE(theta0,m) = sum_i [theta_i - theta0*f_i(m)]^2
theta0(m) = sum_i[f_i(m)*theta_i] / sum_i[f_i(m)^2]
choose m that minimizes SSE; RMSE = sqrt(SSE/N)
```

For the final-10-minute window and planned positions, the fit residual is measured theta minus predicted theta:

| Sensor | x target (mm) | measured theta (C) | finite prediction (C) | finite residual (C) | semi prediction (C) | semi residual (C) | finite-tip relative difference |
|---|---:|---:|---:|---:|---:|---:|---:|
| T1 | 0.0 | 15.602 | 15.445 | +0.157 | 15.170 | +0.432 | 0.000 |
| T2 | 50.8 | 12.430 | 12.654 | -0.224 | 12.861 | -0.431 | 0.040 |
| T3 | 101.6 | 10.522 | 10.594 | -0.071 | 10.904 | -0.382 | 0.097 |
| T4 | 152.4 | 9.111 | 9.144 | -0.033 | 9.245 | -0.134 | 0.177 |
| T5 | 203.2 | 8.400 | 8.222 | +0.178 | 7.838 | +0.561 | 0.279 |

The finite-tip relative difference compares the two *shape predictions* at the finite-fit m: abs(finite_shape - semi_shape)/finite_shape. It is not an uncertainty. The course's chosen acceptable-error threshold was missing from the pasted handout, so confirm it before declaring the semi-infinite approximation acceptable.

For the primary last-10-minute means, the raw observed excess ratio theta5/theta1 = 0.538. The prior 09:20 run reported 0.739 using five sensors only through 101.6 mm and its common-bath offsets. The new provisional ratio is smaller because T5 is planned farther out; this comparison is not a controlled repeat because the new measured positions and calibration are missing.
The last-10-minute unweighted fit has RMSE 0.150 C (finite) versus 0.413 C (semi-infinite), so the finite model fits these five provisional points better. The previous run also favored the finite fit (m=4.117 1/m; semi m=3.056 1/m), but warned that its sensors covered only the near-base region. Inspect the new residuals: with only five sensors, unknown contact bias, no measured x, and no new common-bath correction, the lower RMSE is suggestive rather than decisive.
The placement target is theta5/theta1 <= 1/e = 0.368. The new raw value 0.538 does not meet it. The prior model predicted theta/theta1 about 0.60 at the farthest available hole; spreading the sensors improves leverage for the tip comparison but the available rod length may still not reach 1/e.

## Compare with the previous run
Prior run 092033 used measured positions 0, 25.4, 50.8, 76.2, 101.6 mm, T_room=21.03 C, and calibration offsets. Its final stationary profile reported m_finite=4.117 +/- 0.036 1/m (scaled +/- 0.07), m_semi=3.056 +/- 0.043 1/m, chi2/dof 10.35/3 and 12.91/3, and far ratio 0.739. The new run is raw, has planned 2-inch positions and T_room estimated from its initial baseline; do not compare the m shift as a material change until positions, common-bath correction decision, room temperature, and geometry are measured consistently.

## Radial check and what cannot be inferred
Using the provisional finite-fit m=4.716 1/m and nominal radius R=6.35 mm, Bi_perp=(mR)^2/4=2.24e-04. This is provisionally much less than 0.1, supporting a uniform radial cross-section. Replace nominal R with the caliper measurement and propagate uncertainty. A one-dimensional stationary fit determines m^2=hP/(kA), hence a ratio involving h/k; it cannot determine k and h separately.

## New plots and next corrections
- `docs/figures/module_07_sammy/sammy_rod_run_20261028_timeseries.png`: six-channel time history and final stationary interval.
- `docs/figures/module_07_sammy/sammy_rod_run_20261028_profile_fits.png`: last-40 and last-10 means, previous run, both fits, and residuals.
- Before treating the fit as final: fill measured x positions, rod diameter, T1-to-tip length, and measured resistor values in sensor_map.csv; perform/record the official common-bath check; record room temperature near the stationary window; then rerun this script.
