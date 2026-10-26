# Module 7, Part III: stationary-fin analysis (formative, evidence for C6)

Naidu / Cohen. Analysis code: [`python/analysis/stationary_fin_fit.py`](../../python/analysis/stationary_fin_fit.py).
Acquisition and calibration: [`module_08_rod_instrument.md`](module_08_rod_instrument.md).

Results below are **TO FILL** from a measured steady profile. The fitting code
was checked on synthetic data generated from the same equation (m = 8.00 m⁻¹
put in, 8.00 ± 0.04 m⁻¹ recovered by the finite fit); no synthetic data are
stored in the repository.

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
number), uniform k and h along the rod, a constant room temperature, the base
held at a measured temperature (the boundary condition is the measured base,
not the setpoint), and an insulated tip for the finite model.

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

## 3. Results (TO FILL)

| Quantity | Finite fit | Semi-infinite fit |
|---|---|---|
| m (1/m) | | |
| 1/m (mm) | | |
| θ0 (°C) | | |
| χ² / dof | | |
| Shift in m when the end is ignored, in σ | | |
| mL | | |

Sensor-by-sensor finite-length error ε_T(x) = |Θ_finite − Θ_∞|/Θ_finite at the
fitted m: TO FILL (the script prints and saves it).

**Transverse Biot number from the measured m.** Because m² = hP/(kA) =
2h/(kR) for a circular rod, the ratio h/k = m²R/2 is measured, and

```
Bi_⊥ = h R / (2k) = (m R)² / 4
```

so the steady profile alone fixes Bi_⊥ once R is known. TO FILL.

## 4. What the steady profile cannot do

The fit gives m, which is the combination √(hP/(kA)): only the ratio h/k.
A rod with twice the conductivity and twice the side loss gives exactly the
same steady profile. Separating k from h needs a second, independent
measurement with a different dependence on them: the periodic (Angstrom)
experiment of Module 8, where amplitude decay and phase lag along the rod
involve the diffusivity and the loss rate differently.

## 5. Discussion points (TO FILL with data)

- Sensor-position error and its effect on m.
- Room-temperature drift during the hold.
- Imperfect thermal contact between thermistors and rod.
- Evidence for the tip boundary condition: whether the finite fit's
  residuals near the tip are smaller than the semi-infinite fit's.
