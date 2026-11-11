# Module 8 modeling app (formative checkpoint)

Naidu / Cohen. The app is three scripts in `python/analysis/` run in order on
a raw GUI file. Nothing in `data/` is ever edited: calibration offsets, masks
and fitting windows are applied in memory and every output file starts with
the exact command that made it.

## Input

A GUI file `angstrom_live_YYYYMMDD_HHMMSS.csv` (Sammy's copy:
`sammy_angstrom_live_...csv`, same columns), one record about every 0.5 s:

```text
time_ms,run_state,control_mode,step,Ta_C,Tb_C,period_s,setpoint_C,feedforward_pwm,TEC_C,T1_C,T2_C,T3_C,T4_C,T5_C,controller_pwm,heating_to_cooling_ratio,signed_pwm
```

Also used: `data/module_08/sensor_map.csv` (T1 to T5 at 0, 25.4, 50.8, 76.2,
101.6 mm, ±1 mm; T1 defines x = 0), `data/module_08/calibration_rod_run_20261026_112627.csv`
(common-bath offsets) and, for the 10 Nov run, Sammy's mask
`data/module_08_sammy/sammy_angstrom_live_20261110_164057_mask.csv`.

## Sequence of fits

1. **Per-sensor sine fits** (`angstrom_fit.py`). For one period, take N complete
   cycles ending at `--t-end` and fit every channel to
   T = a + B cos(ωt + φ) + drift. Errors of a, B and φ come from fitting each
   cycle on its own (sd/√N). The cycle-by-cycle table is the settling test.
2. **Spatial fits** (same script). ln B against x gives q, unwrapped φ against x
   gives q′; κ = ω/(2qq′), ν = κ(q² − q′²).
3. **Finite rod** (`angstrom_finite_fit.py`). Same B and φ fitted jointly with
   cosh(s(L − x))/cosh(sL), s = q + iq′, L = 281.9 mm. Compared with the
   semi-infinite result, this is the finite-length check.
4. **Mean profile** (`angstrom_mean_profile.py`). The a_i against
   (a0 − T∞) cosh(μ(1 − ξ))/cosh(μ), ξ = x/L, gives μ = mL and m = μ/L, compared
   with Module 7 (4.117 ± 0.07 m⁻¹) and with √(q² − q′²).

Settling rule (fixed in A5 before the fits): a period is settled from the first
cycle after which every rod sensor's B stays within 3 % and φ within 0.05 rad
of the previous cycle, with no steady trend. Keep at least 5 settled cycles.

## Commands

```bash
OFF=data/module_08/calibration_rod_run_20261026_112627.csv
python3 python/analysis/angstrom_fit.py data/module_08/angstrom_live_20261102_094506.csv --mode PI --period 100 --cycles 5 --offsets $OFF
python3 python/analysis/angstrom_fit.py data/module_08/angstrom_live_20261102_094506.csv --mode PI --period 480 --cycles 5 --t-end 5507.21 --offsets $OFF
python3 python/analysis/angstrom_fit.py data/module_08/angstrom_live_20261104_092527.csv --mode PI --period 240 --cycles 5 --t-end 3077 --offsets $OFF
python3 python/analysis/angstrom_fit.py data/module_08/angstrom_live_20261104_092527.csv --mode PI --period 180 --cycles 5 --t-end 4337 --offsets $OFF
python3 python/analysis/angstrom_fit.py data/module_08/angstrom_live_20261104_110306.csv --mode PI --period 300 --cycles 6 --t-end 2687.19 --offsets $OFF
S=data/module_08_sammy/sammy_angstrom_live_20261110_164057
python3 python/analysis/angstrom_fit.py $S.csv --mode PI --period 480 --cycles 3 --t-end 4228.894 --offsets $OFF --mask ${S}_mask.csv
python3 python/analysis/angstrom_fit.py $S.csv --mode PI --period 240 --cycles 6 --t-end 5909.345 --offsets $OFF --mask ${S}_mask.csv
python3 python/analysis/angstrom_fit.py $S.csv --mode PI --period 100 --cycles 3 --t-end 6609.818 --offsets $OFF --mask ${S}_mask.csv

python3 python/analysis/angstrom_finite_fit.py data/module_08/angstrom_fit_<run>_PI_<P>s.csv ... --length-mm 281.9 --dx-mm 1
python3 python/analysis/angstrom_mean_profile.py data/module_08/angstrom_fit_*_PI_*s.csv
python3 python/analysis/angstrom_mean_profile.py data/module_08/angstrom_fit_*_PI_*s.csv --exclude T2 --tag noT2
```

Outputs: `data/module_08/angstrom_fit_*.txt/.csv`, `angstrom_finite_*.txt`,
`angstrom_mean_profile*.txt`; figures in `docs/figures/module_08/`
(per-sensor fits with ln B and phase panels, and the mean-profile plot).

## Results

All PI, Ta 40 °C, Tb 16 °C. κ in 10⁻⁵ m²/s, ν in 10⁻³ s⁻¹, q and q′ in m⁻¹.

| Run | Period | Cycles kept | q | q′ | κ semi-inf. | κ finite rod | ν finite rod |
|---|---|---|---|---|---|---|---|
| 2 Nov | 100 s | 5 | 18.53 ± 0.26 | 17.37 ± 0.33 | 9.74 ± 0.23 | 9.74 ± 0.23 | 4.1 ± 1.5 |
| 2 Nov | 480 s | 5 (2 to 6) | 9.34 ± 0.18 | 7.84 ± 0.15 | 8.93 ± 0.25 | 9.40 ± 0.24 | 2.0 ± 0.4 |
| 4 Nov | 180 s | 5 (3 to 7) | 14.10 ± 0.26 | 13.39 ± 0.15 | 9.23 ± 0.20 | 9.19 ± 0.20 | 1.7 ± 0.8 |
| 4 Nov | 240 s | 5 (3 to 7) | 12.34 ± 0.19 | 11.29 ± 0.11 | 9.39 ± 0.17 | 9.36 ± 0.17 | 2.1 ± 0.5 |
| 4 Nov | 300 s | 6 (2 to 7) | 11.06 ± 0.15 | 10.17 ± 0.10 | 9.30 ± 0.16 | 9.33 ± 0.15 | 1.3 ± 0.4 |
| 10 Nov | 480 s | 3 (5 to 7) | 9.36 ± 0.14 | 7.95 ± 0.14 | 8.78 ± 0.21 | 9.22 ± 0.19 | 1.9 ± 0.3 |
| 10 Nov | 240 s | 6 (2 to 7) | 12.42 ± 0.15 | 11.52 ± 0.12 | 9.14 ± 0.14 | 9.10 ± 0.14 | 1.7 ± 0.4 |
| 10 Nov | 100 s | 3 (5 to 7) | 18.73 ± 0.23 | 18.06 ± 0.22 | 9.28 ± 0.16 | 9.28 ± 0.16 | 2.4 ± 1.1 |

q and q′ are the semi-infinite slopes from `angstrom_fit.py`.

- κ, all eight (finite rod): weighted mean **9.29 ± 0.06**, χ² = 6.5 for 7 degrees
  of freedom. Only the six windows with 5 or more settled cycles: 9.30 ± 0.07,
  χ² = 6.3 for 5. Either way the periods and days agree. This is 35 % above the
  handbook 6061-T6 value (6.9).
- ν has 30 to 60 % errors: it is a small difference of two nearly equal numbers.

**Mean profile, m = μ/L (m⁻¹)**, against Module 7 (4.117 ± 0.07) and √(q² − q′²):

| Run | Period | m, mean profile | χ²/dof | √(q² − q′²) |
|---|---|---|---|---|
| 2 Nov | 100 s | 4.34 ± 0.16 | 34.9/3 | 6.5 ± 1.2 |
| 2 Nov | 480 s | 4.08 ± 0.21 | 0.6/3 | 5.1 ± 0.4 |
| 4 Nov | 180 s | 4.30 ± 0.11 | 2.1/3 | 4.4 ± 1.0 |
| 4 Nov | 240 s | 4.16 ± 0.09 | 5.6/3 | 5.0 ± 0.5 |
| 4 Nov | 300 s | 3.79 ± 0.08 | 10.0/3 | 4.4 ± 0.5 |
| 10 Nov, T2 excluded | 480 s | 4.28 ± 0.11 | 1.1/2 | 4.9 ± 0.4 |
| 10 Nov, T2 excluded | 240 s | 4.61 ± 0.07 | 2.5/2 | 4.6 ± 0.5 |
| 10 Nov, T2 excluded | 100 s | 4.57 ± 0.07 | 5.1/2 | 5.0 ± 1.2 |

- Mean-profile m: average 4.27, run-to-run sd 0.26 (so about ±0.09 on the
  average), much more scatter than the single-fit errors (weighted χ² = 78 for 7).
  It agrees with Module 7's 4.12. Changing T∞ by ±0.1 °C moves m by only ±0.03.
  The 4 Nov 300 s value is the lowest; that run started with the rod still warm
  and used the morning's room temperature.
- Angstrom m = √(q² − q′²): weighted mean 4.85 ± 0.18 (χ² = 4.0 for 7). That is
  about 0.6 m⁻¹ (3σ) above the mean-profile value. Each single value is weak
  because q² − q′² is a small difference.

## Approximation checks

- **Finite length.** Finite-rod against semi-infinite κ: under 1 % at 100 to 300 s,
  about 5 % at 480 s (8.93 to 9.40 and 8.78 to 9.22). The finite-rod value is used.
- **Transverse Biot number.** Bi = (ν/κ)R²/4 with R = 6.378 mm: 1.4 × 10⁻⁴ to
  4.2 × 10⁻⁴ for every window. That is far below 0.1, so the cross-section is
  isothermal and the 1-D model holds.
- **Residuals.** The joint amplitude and phase fits have χ² of 9.6 to 25.3 for 6
  degrees of freedom, and errors are scaled up by √(χ²/dof) where that exceeds 1. Mean-profile
  residuals on 2 and 4 Nov are under 0.11 °C except T3 at 2 Nov 100 s (+0.23 °C).

## Exclusions and why

- First cycles after a start or a period change fail the settling rule:
  2 Nov 480 s cycle 1; 4 Nov 240 s and 180 s cycles 1 and 2; 4 Nov 300 s cycle 1;
  10 Nov 240 s cycle 1.
- **10 Nov, T5 masked** at 1860 to 2618 s and 3060 to 3141 s (reads 1 to 4 °C
  above its prediction from T3 and T4; Sammy's mask). Also T3 to T5 at 36 to
  200 s (leads handled before the run, outside every fit window). A cycle with
  more than 10 % masked is left out of the error estimate.
- **10 Nov, 480 s: only cycles 5 to 7.** At t = 2598 s the TEC reading jumped
  4.3 °C in one record while T1 kept falling smoothly. The jump is in the TEC
  sensor, not the plate; PI answered with −176 PWM. Afterwards the rod mean
  fell about 1.3 °C and every rod amplitude about 10 %, with the TEC reading's
  mean and amplitude unchanged. That fits a TEC thermistor that now reads warmer
  than the plate (not confirmed). The ratios along the rod did not change, so
  q and q′ are fine. Before the jump only cycles 2 and 3 are settled (κ semi-inf.
  8.61 ± 0.51), so 480 s on 10 Nov has 3 settled cycles, below the minimum.
- **10 Nov, 100 s: only cycles 5 to 7.** Cycles 2 to 5 alternate (T4 amplitude
  ±3 to 5 %, T5 phase ±0.07 to 0.11 rad) with no trend. Under the rule that
  leaves 3 cycles. Cycles 3 to 7 would give κ = 9.41 ± 0.17 (semi-inf.).
- **10 Nov, T2 mean excluded from the mean-profile fit (oscillation kept).**
  T2's mean sits 1.21 to 1.26 °C above the cosh curve through T1, T3, T4 and T5
  in all three periods. On 2 and 4 Nov its residual is +0.02 to +0.07 °C. The
  bias is not there at room temperature: in the 10 Nov idle baseline T2 is within
  0.05 °C of the T1 to T5 mean after offsets. It also changed during the
  480 s step (T2 − T1 from +0.71 to +0.34 °C between cycles 1 and 7). T2's
  amplitude ratio is normal (B2/B1 0.809, 0.752, 0.653 against 0.813, 0.758,
  0.661 on earlier days), so the bias is in the mean only, and a position error
  is ruled out (it would change B2/B1 and the phase too). The cause is not
  known. T2's seating and leads should be checked before the next run.

AI assistance: Claude (Anthropic) helped write the scripts and this note. The
fits, numbers and exclusions were checked against the raw files.
