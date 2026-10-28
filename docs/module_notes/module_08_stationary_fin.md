# Module 7, Part III: stationary-fin analysis (formative, evidence for C6)

Naidu / Cohen. Analysis code: [`python/analysis/stationary_fin_fit.py`](../../python/analysis/stationary_fin_fit.py).
Acquisition and calibration: [`module_08_rod_instrument.md`](module_08_rod_instrument.md).

First measured profile: run `rod_run_20261028_092033`, 28 October (section 3).
The fitting code was checked beforehand on synthetic data generated from the
same equation (m = 8.00 and 9.00 m⁻¹ put in, recovered within 0.05 m⁻¹ by the
finite fit); no synthetic data are stored in the repository.

---

## 1. Governing equation and assumptions

With θ(x, t) = T(x, t) − T_room, a uniform rod of cross-section A, perimeter
P, density ρ, specific heat c, conductivity k and side coefficient h obeys

```
ρ c A ∂θ/∂t = k A ∂²θ/∂x² − h P θ            (every term in W/m)
```

At steady state

```
d²θ/dx² = m² θ,      m² = hP/(kA)            (m in 1/m)
```

Assumptions: one temperature per cross-section (small transverse Biot
number), uniform k and h along the rod, a constant room temperature, a
measured boundary temperature (rod thermistor R1 in the first rod hole, x = 0,
as the course defines it; not the TEC thermistor and not the setpoint), and an
insulated tip for the finite model.

Profiles fitted:

```
finite, insulated tip:  θ(x) = θ0 cosh(m(L − x)) / cosh(mL)
semi-infinite:          θ(x) = θ0 e^(−mx)
```

## 2. Procedure (Part 3)

1. Hold the base at a constant safe temperature with PI. State the steady
   criterion in advance, for example every channel drifting by less than
   0.01 °C/min over the last 5 minutes. The script prints each channel's
   drift over the averaging window so the criterion can be checked.
2. Average each sensor over the final window (default 300 s).
3. Run

   ```bash
   python3 python/analysis/stationary_fin_fit.py data/module_08/rod_run_<...>.csv \
       --length-mm <L> --troom <T_room> --radius-mm <R> \
       --offsets data/module_08/calibration_<run>.csv
   ```

   Outputs: `docs/figures/module_08/fin_<run>.png` (θ against x with error
   bars, both fits, both residual sets), `data/module_08/fin_<run>.txt`, and
   `data/module_08/fin_profile_<run>.csv`.

Point uncertainties combine the standard error of each mean (allowing for
correlated readings), the calibration uncertainty, and the position
uncertainty propagated through the local slope (δθ ≈ m θ δx).

## 3. Results, run rod_run_20261028_092033 (28 October)

```bash
python3 python/analysis/stationary_fin_fit.py data/module_08/rod_run_20261028_092033.csv \
    --length-mm 279.4 --troom 21.03 --radius-mm 6.35 --t0 4346 --t1 4646 \
    --offsets data/module_08/calibration_rod_run_20261026_112627.csv
```

Output: [`fin_rod_run_20261028_092033.txt`](../../data/module_08/fin_rod_run_20261028_092033.txt),
[`fin_profile_rod_run_20261028_092033.csv`](../../data/module_08/fin_profile_rod_run_20261028_092033.csv),
![Stationary profile](../figures/module_08/fin_rod_run_20261028_092033.png)

**Conditions.**

- Base (TEC thermistor) held at 45 °C by PI (Kp 12, Ki 0.2) after the
  20 → 45 °C step at t = 2556 s.
- Steady window: 4346 to 4646 s, the last 300 s before control was switched
  off (4646.8 s), 30 to 35 min after the step. Drift of every channel over
  the window: between −0.004 and +0.005 °C/min, which meets the criterion stated in
  section 2 (under 0.01 °C/min).
- T_room = 21.03 °C: the mean of the five rod thermistors at the start of
  the same run (13 to 87 s, 09:20, control off, before any heating), sd
  0.02 °C after offsets; the base thermistor read 20.98 °C. Measured with
  the same thermistors as θ, so a common calibration error cancels in θ.
  Not re-measured at the end; a room drift since then is the main
  uncertainty in θ. A ±0.5 °C change in T_room moves m
  between 4.03 and 4.21 m⁻¹.
- L = 279.4 mm (about 11 in, R1's hole to the rod top, rough).
- **Positions are provisional**: about 1 in apart, by eye, entered as
  25.4 mm steps with a guessed ±6 mm. This guess dominates the point error
  bars (σ about 0.3 to 0.4 °C on R2 to R5) and makes χ² small. Replace with
  ruler values (±1 mm) and rerun.

| Channel | x (mm) | θ (°C) | σ (°C) | ε_T |
|---|---|---|---|---|
| R1 | 0.0 | 16.83 | 0.03 | 0.000 |
| R2 | 25.4 | 15.66 | 0.39 | 0.021 |
| R3 | 50.8 | 14.34 | 0.36 | 0.045 |
| R4 | 76.2 | 13.13 | 0.33 | 0.074 |
| R5 | 101.6 | 12.44 | 0.31 | 0.107 |

| Quantity | Finite fit | Semi-infinite fit |
|---|---|---|
| m (1/m) | 4.12 ± 0.15 | 3.07 ± 0.18 |
| 1/m (mm) | 243 ± 9 | 325 ± 19 |
| θ0 (°C) | 16.83 | 16.83 |
| χ² / dof | 0.45 / 3 | 0.55 / 3 |
| Shift in m when the end is ignored | −1.04 m⁻¹ = −6.7 σ of the finite fit | |
| mL | 1.15 | |

Both models fit the five points equally well (largest residual 0.19 °C,
inside every error bar). The sensors only cover x ≤ 102 mm (mx ≤ 0.42), where
a cosh and an exponential look almost the same. So the 6.7 σ difference in m
comes from the assumed tip condition and L, not from the data. With
mL = 1.15 the rod is not long compared with 1/m, and the finite model is
the one to use; the far sensors (ε_T up to 0.11 at R5) are where ignoring
the end matters most.

**Placement check (course Part 2).** θ5/θ1 = 12.44/16.83 = 0.74 (0.73 to
0.75 for T_room ± 0.5 °C). The target is θ5 ≤ θ1/e = 0.37: **not met**. From
the finite fit, the farthest available hole (about 8 in from R1) would give
θ/θ1 = 0.60 ± 0.02 and even the rod top only 0.58. Reaching 1/e at 8 in would
need m ≈ 6.4 m⁻¹, that is h/k about 2.4 times larger. Moving sensors cannot
meet the target on this set-up; raised with Prof. Fraden on 28 October.

**Transverse Biot number from the measured m.** Because m² = hP/(kA) =
2h/(kR) for a circular rod, the ratio h/k = m²R/2 is measured, and

```
Bi_⊥ = h R / (2k) = (m R)² / 4
```

so the steady profile alone fixes Bi_⊥ once R is known. With m = 4.12 m⁻¹
and R = 6.35 mm (nominal): Bi_⊥ = 1.7 × 10⁻⁴ ± 0.1 × 10⁻⁴, far below 0.1, so
one temperature per cross-section is a very good assumption. The same m
gives h/k = m²R/2 = 0.054 m⁻¹.

## 4. What the steady profile cannot do

The fit gives m, which is the combination √(hP/(kA)): only the ratio h/k.
A rod with twice the conductivity and twice the side loss gives exactly the
same steady profile. Separating k from h needs a second, independent
measurement with a different dependence on them: the periodic (Angstrom)
experiment of Module 8, where amplitude decay and phase lag along the rod
involve the diffusivity and the loss rate differently.

## 5. Discussion points (first run)

- **Sensor positions** are the weakest input today: by eye, about 1 in
  apart. They set the error bars and the χ². Measure with a ruler.
- **Room temperature** was measured once, about 70 minutes before the
  steady window. ±0.5 °C moves m by about ±0.09 m⁻¹, less than the fit's
  own ±0.15.
- **Thermal contact.** A disturbance at about 10:18 (hands and a ruler near
  the rod while measuring the spacing, noted in the run) dropped R1 by
  0.4 °C and R2 by 0.2 °C within 30 s, with smaller dips farther up, while
  the base held 45.0 °C. The rod sensors respond to the air around them, so
  contact and draughts matter. The steady window starts about 15 min after
  that.
- **Tip condition.** With all sensors in the first 102 mm the data cannot
  tell the finite and semi-infinite shapes apart (χ² 0.45 vs 0.55). Sensors
  spread out to the farthest hole would test it directly.
