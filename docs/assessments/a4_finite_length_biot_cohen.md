# A4: Finite-Rod Model and Validity Checks
Assessment code: A4 (individual)
Student: Samuel Cohen
Date: 4 November 2026
Repository: https://github.com/kapilnaidu1/phys39-naidu-cohen, branch main

This is my individual assessment. I use the course's shared rod geometry and sensor map, but the derivation, calculations, and interpretation below are written for my submission. The Git checkpoint is inserted by the PDF builder when it is run.

## Part 1. Apply Fourier's law: Lienhard Problem 1.3

The assigned slab is 0.010 m thick, carries a steady heat flux of 5000 W/m^2, and has its cold face at -40 C. With no internal generation, the same heat flux passes through the slab. Fourier's law is `q_x = -k dT/dx`. Taking the magnitude and integrating through a constant-property slab gives:

```text
DeltaT = T_hot - T_cold = q L / k
       = (5000 W/m^2)(0.010 m) / k
       = (50 W/m) / k
```

The units are `(W/m^2)(m)/(W/(m K)) = K`. The sign in Fourier's law says that the heat flux points toward decreasing temperature; `DeltaT` above is the positive hot-to-cold temperature difference. The hot-face temperature is `T_hot = -40 C + DeltaT`.

| Material | k and table source | DeltaT (K) | Hot face (C) | Physical check |
|---|---:|---:|---:|---|
| Pure silver | 427 W/(m K), Lienhard Table A.1, 20 C | 0.117 | -39.88 | Plausible; high conductivity gives a small gradient. |
| Pure aluminum | 237 W/(m K), Table A.1, 20 C | 0.211 | -39.79 | Plausible for the listed pure metal. |
| Mild steel, 0.5% C | 54 W/(m K), Table A.1, 20 C | 0.926 | -39.07 | Plausible under the constant-k approximation. |
| Ice | 2.215 W/(m K), Table A.2, 0 C | 22.6 | -17.4 | Plausible; the hot face remains below melting. |
| Spruce | 0.11 W/(m K), Table A.2, 20 C | 455 | 415 | Not physically self-consistent: wood would char/decompose, changing the material and its conductivity. |
| 85% magnesia insulation | 0.067 W/(m K), Table A.2, 38 C | 746 | 706 | Not reliable with constant k: the result is far outside the table's temperature range, so the input property cannot be extrapolated this way. |
| Silica aerogel | 0.024 W/(m K), Table A.2, 0 C | 2083 | 2043 | Physically unreasonable for unchanged silica aerogel; the result exceeds silica's stability range and the assumed material would not remain intact. |

For example, the silver result is `50/427 = 0.117 K`; its hot face is `-40 + 0.117 = -39.883 C`. The large rises for low-conductivity materials are warnings, not predictions to trust blindly: constant `k`, unchanged material, and steady conduction cease to be credible if the material chars, decomposes, or leaves the range of its property data. Ice is a useful contrast: even its calculated hot face remains below 0 C.

## Part 2. Derive the stationary finite-rod model

Let `T(x)` be the rod temperature and `T_room` the room temperature. Define excess temperature `theta(x) = T(x) - T_room`. Consider a slice from `x` to `x + dx`, with area `A`, exposed perimeter `P`, conductivity `k`, and side-convection coefficient `h`. At steady state the slice stores no net energy. Conduction into the slice minus conduction out, minus side convection, is zero:

```text
Q_in(x) - Q_out(x+dx) - h P dx [T(x) - T_room] = 0
```

Fourier's law for axial heat rate is `Q_x = -k A dT/dx`; Newton's law gives side loss `h (P dx) (T - T_room)`. Substitution and division by `k A dx` give, as `dx` tends to zero:

```text
d2(theta)/dx2 - m^2 theta = 0
m^2 = h P/(k A)
m = sqrt[h P/(k A)]
```

The original balance is in watts: `k A dT/dx` has units `(W/(m K))(m^2)(K/m) = W`, and `h P dx theta` has units `(W/(m^2 K))(m)(m)(K) = W`. In the differential equation, `m^2` has units `1/m^2`; therefore `m` is in `1/m` and `1/m` is a length. It is the characteristic axial decay length for a semi-infinite rod.

The two boundary conditions for this course model are:

| Location | Mathematical condition | Physical meaning |
|---|---|---|
| Analysis base, x = 0 | `theta(0) = theta_0` | The measured rod temperature at T1 sets the base value. The TEC setpoint and TEC thermistor are not the rod boundary. |
| Tip, x = L | `d(theta)/dx = 0` | Zero conductive heat flux through the end face: the tip is treated as insulated. |

The differential equation has the general solution `theta = C1 cosh(mx) + C2 sinh(mx)`. At the tip, `C1 sinh(mL) + C2 cosh(mL) = 0`; at the base, `C1 = theta_0`. Applying these conditions and normalizing gives the finite insulated-tip profile:

```text
Theta_finite(x) = theta(x)/theta_0
                = cosh[m(L - x)] / cosh(mL)
```

It checks directly: `Theta_finite(0) = 1`, and its derivative is zero at `x = L`. The normalized tip temperature is `1/cosh(mL)`. This model assumes constant properties, a fixed room temperature, uniform cross-sections, and negligible end-face heat transfer; the last assumption is checked separately in Part 3.

## Part 3. Provisional finite-length prediction

### Semi-infinite limit and finite-length error

For the finite problem with the far boundary held at room temperature, the normalized solution is `sinh[m(L-x)]/sinh(mL)`. In exponential form:

```text
Theta(x) = [exp(-m x) - exp(-2mL) exp(m x)] / [1 - exp(-2mL)]
```

As `L` tends to infinity at fixed `x`, the terms involving `exp(-2mL)` vanish and `Theta` tends to `exp(-mx)`, the semi-infinite result (Lienhard Problem 4.12). The insulated-tip solution has the same limit. For this rod I compare the semi-infinite profile with the required finite insulated-tip profile using the course's relative-temperature error:

```text
epsilon_T(x) = |Theta_finite(x) - exp(-m x)| / Theta_finite(x)
```

The measured geometry record gives `D = 12.757 +/- 0.006 mm`, hence `R = 6.378 +/- 0.003 mm`, and `L = 281.9 +/- 1.3 mm` from the T1 hole to the tip. The analysis length is not the overall rod length. Planned positions are T1-T5 at `x = 0, 25.4, 50.8, 76.2, 101.6 mm`, with about 1 mm position uncertainty. The length reading was confirmed on 2 November; retain its recorded uncertainty in the final submission.

For a circular rod, `P/A = 2/R = 4/D`, so the provisional natural-convection value `h = 10 W/(m^2 K)` gives:

```text
m = sqrt[4 h/(k D)]
```

Lienhard Table A.1 gives 6061-T6 aluminum near `167 W/(m K)` at 20 C and about `166-172 W/(m K)` across 0-100 C. I use `166-172 W/(m K)` as the direct literature range and a wider `150-185 W/(m K)` sensitivity range to allow for alloy/temper and property uncertainty. The values below use the measured diameter and nominal `L = 281.9 mm`; the small recorded geometry uncertainties do not change the conclusion.

| k (W/(m K)) | m (1/m) | 1/m (mm) | mL |
|---:|---:|---:|---:|
| 150 | 4.572 | 218.7 | 1.289 |
| 166 | 4.346 | 230.1 | 1.225 |
| 172 | 4.270 | 234.2 | 1.204 |
| 185 | 4.117 | 242.9 | 1.161 |

Thus `mL` is only about 1.16-1.29, far below the rule-of-thumb `mL about 5` for a long-fin temperature approximation. The decay length is also comparable to the rod's analysis length, so the tip cannot be ignored automatically.

| k (W/(m K)) | T1, 0 mm | T2, 25.4 mm | T3, 50.8 mm | T4, 76.2 mm | T5, 101.6 mm |
|---:|---:|---:|---:|---:|---:|
| 150 | 0.00% | 1.81% | 4.01% | 6.64% | 9.76% |
| 166 | 0.00% | 1.92% | 4.22% | 6.94% | 10.12% |
| 172 | 0.00% | 1.96% | 4.30% | 7.04% | 10.24% |
| 185 | 0.00% | 2.04% | 4.44% | 7.24% | 10.47% |

Using the course's 5% criterion, the semi-infinite approximation is adequate at T1-T3 over this parameter range, but not at T4 or T5. Therefore I would retain the finite insulated-tip profile for analysis over all five sensors and use the semi-infinite curve only as a comparison. The conclusion depends on the stated `h`, conductivity range, measured positions, and 5% cutoff. A larger `h` or sensors closer to T1 would change the error.

### Is the insulated-tip boundary itself a good approximation?

This is a different question from whether the entire rod can be called semi-infinite. Example 4.8 and Problem 4.20 compare a convecting tip with an insulated tip. I assume provisionally that the tip coefficient equals the side value, `h_L = h = 10 W/(m^2 K)`. Define `Bi_tip = h_L L/k`. The convecting-tip profile is:

```text
b = Bi_tip/(mL)
Theta_conv(x) = [cosh(m(L-x)) + b sinh(m(L-x))]
               / [cosh(mL) + b sinh(mL)]
Theta_ins(x)  = cosh(m(L-x))/cosh(mL)
```

The table gives the absolute difference between the two normalized profiles, relative to the convecting-tip result. The base is fixed, so the difference there is zero. The base heat-rate comparison uses Lienhard's dimensionless forms for convecting versus insulated tips.

| k (W/(m K)) | Bi_tip | difference at T5 | difference at physical tip | base heat-rate difference |
|---:|---:|---:|---:|---:|
| 150 | 0.01879 | 0.262% | 1.252% | 0.438% |
| 166 | 0.01698 | 0.256% | 1.166% | 0.474% |
| 172 | 0.01639 | 0.254% | 1.137% | 0.487% |
| 185 | 0.01524 | 0.248% | 1.078% | 0.512% |

Under this small-tip-convection assumption, the insulated-tip approximation changes the measured-region profile at T5 by only about 0.25%; the larger difference occurs right at the rod tip, which is not a sensor. This supports an insulated tip for the planned sensor region. It does **not** make the semi-infinite approximation acceptable at T4-T5: finite length has a roughly 7-10% effect there.

## Part 4. Provisional transverse Biot number

The transverse Biot number tests whether radial temperature variation within each cross-section is small. It is separate from the axial finite-length test:

```text
Bi_perp = h (A/P)/k = h R/(2k) = h D/(4k)
```

For a cylinder, `A/P = R/2`. The units cancel: `(W/(m^2 K))(m)/(W/(m K)) = 1`. Using the same provisional `h` and the measured radius:

| k (W/(m K)) | 150 | 166 | 172 | 185 |
|---|---:|---:|---:|---:|
| Bi_perp | 2.126e-4 | 1.921e-4 | 1.854e-4 | 1.724e-4 |

The full range is about `1.7e-4 to 2.1e-4`, far below 0.1. Radial conduction is therefore much stronger than surface convection on this length scale, supporting one temperature per cross-section at every planned sensor. This is the provisional pre-experiment prediction; later measured-profile checks are separate. The rod can be adequately one-dimensional radially while still requiring a finite-length model axially.

## Application: still air versus forced airflow

The forced-air case has the larger `h`: moving air removes the warmed boundary layer and increases heat transfer per unit area per degree. Since `m = sqrt(hP/(kA))`, increasing `h` increases `m` and shortens the decay length `1/m` in proportion to `h^(-1/2)`. For illustration, at `k = 167 W/(m K)`, increasing `h` from 10 to 100 W/(m^2 K) changes `1/m` from about 231 mm to 73.0 mm. This comparison holds the rod material and geometry fixed.

## Comparison with Kapil Naidu's A4

I used Kapil's published PDF as a structure and arithmetic cross-check, not as text to copy. Our physical setup and the 2 November measurement record are shared, so the central numerical predictions should agree within rounding.

| Item | Naidu A4 | My Cohen calculation |
|---|---|---|
| Problem 1.3 | Same slab, heat flux, cold-face temperature, and Lienhard material data | Same specified inputs; I show the integration, units, and a cautious interpretation of the magnesia extrapolation. |
| Rod inputs | D = 12.757 mm, L = 281.9 mm, planned positions T1-T5 | Same confirmed geometry and mapped positions; I retain the geometry record's +/-1.3 mm uncertainty. |
| Wide conductivity sensitivity | 150-185 W/(m K) | Same range; recalculated m = 4.117-4.572 1/m and mL = 1.161-1.289. |
| Semi-infinite error at T5 | about 9.8-10.5% | 9.76-10.47%; same conclusion to rounding. |
| Main interpretation | Finite length matters at T4-T5; radial Biot number is very small | Same conclusions, with the tip-boundary error explicitly kept separate from semi-infinite error. |

My earlier preparation is in `docs/theory/theory_bridge_chapter_1_notes.md`; shared measurement inputs are recorded in `data/module_08/rod_geometry.csv` and `data/module_08/sensor_map.csv`. This A4 is a pre-experiment prediction: I do not substitute the later fitted stationary-fin `m` for the requested provisional calculation.

## References

- J. H. Lienhard IV and J. H. Lienhard V, *A Heat Transfer Textbook*, 6th edition, Section 1.3, Section 4.5, Problem 1.3, Problem 4.12, Example 4.8, Problem 4.20, Tables A.1-A.2. Course PDF: https://sethfraden.github.io/Phys39F26-course/references/lienhard-heat-transfer-textbook-v6.pdf
- Course A4 instructions and rubric: https://sethfraden.github.io/Phys39F26-course/labs/lab-08/#a4-finite-rod-model-and-validity-checks
- Kapil Naidu, *A4: Finite-Rod Model and Validity Checks*, used only to cross-check organization and shared measurement values: https://github.com/kapilnaidu1/phys39-naidu-cohen/blob/main/docs/A4_Naidu.pdf
- Shared 6061-T6 geometry and sensor map: `data/module_08/rod_geometry.csv`; `data/module_08/sensor_map.csv`.