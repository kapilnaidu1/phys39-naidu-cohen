# A4: Finite-Rod Model and Validity Checks

Assessment code: A4 (individual)  
Student: Kapil Naidu (lab partner Samuel Cohen)  
Date: 4 November 2026  
Repository: https://github.com/kapilnaidu1/phys39-naidu-cohen, branch main

All textbook references are to Lienhard, *A Heat Transfer Textbook*, 6th edition (course copy). Material properties are from its Tables A.1 and A.2.

## Part 1. Apply Fourier's law (Lienhard Problem 1.3)

A slab 1 cm thick carries a steady heat flux q = 5000 W/m², and its cold side is at −40 °C. In steady one-dimensional conduction with no heat generation the flux is the same at every depth, so Fourier's law

```
q = −k dT/dx
```

integrates across the thickness L to a straight-line profile with

```
ΔT = T_hot − T_cold = q L / k
```

Units: (W/m²)(m)/(W/(m K)) = K. With qL = 5000 × 0.01 = 50 W/m every case is ΔT = (50 W/m)/k.

**Sample calculation, pure silver:** k = 427 W/(m K) (Table A.1, 99.99+ %, 20 °C), so ΔT = 50/427 = 0.117 K, matching the answer given with the problem. The hot side is at −39.88 °C.

| Material | k (W/(m K)), source | ΔT (K) | Hot side (°C) | Reasonable? |
|---|---|---|---|---|
| Pure silver | 427, A.1 (20 °C) | 0.117 | −39.88 | yes |
| Pure aluminum | 237, A.1 (20 °C) | 0.211 | −39.79 | yes |
| Mild steel (0.5 % C) | 54, A.1 (20 °C) | 0.926 | −39.07 | yes |
| Ice | 2.215, A.2 (0 °C) | 22.6 | −17.4 | yes: still below 0 °C, so it stays solid |
| Spruce | 0.11, A.2 (20 °C) | 455 | 415 | **no** |
| Insulation (85 % magnesia) | 0.067, A.2 (38 °C) | 746 | 706 | **no** |
| Silica aerogel | 0.024, A.2 (0 °C) | 2083 | 2043 | **no** |

The metals barely notice the flux: a high k means a small gradient carries it, which is why the rod and the TEC plate in our apparatus are aluminium. The last three results are unreasonable. Spruce would char and burn long before its hot face reached 415 °C, so the slab could not carry this flux steadily. Magnesia pipe insulation is used on steam lines at a few hundred degrees; 706 °C is far outside the 38 to 150 °C range for which the table gives k, so the constant-k answer is an extrapolation with no support. A hot face above 2000 °C is beyond the melting point of silica (about 1700 °C), so the aerogel would be destroyed. The same reasoning is why we protect the TEC: forcing a large heat flux through a poor conductor produces a temperature rise large enough to damage the material, and the TEC's rated limit is 80 °C. The calculation also assumed constant k; for the metals and ice the temperature change is small enough for that to hold, but for the three failing cases k itself would change over hundreds of degrees.

## Part 2. Build the stationary finite-rod model

**Energy balance.** Take a thin slice of the rod between x and x + δx, with cross-section A, perimeter P, conductivity k, and side heat-transfer coefficient h to air at T∞ (Lienhard Section 4.5, Fig. 4.8). At steady state no energy is stored, so conduction in at x equals conduction out at x + δx plus convection from the slice's side surface Pδx.

**Fourier's law** gives the conducted heat rate Q = −kA dT/dx, and **Newton's law of cooling** gives the side loss hPδx (T − T∞). The balance (Lienhard Eq. 4.28) is

```
−kA dT/dx |(x+δx)  +  kA dT/dx |(x)  +  h (P δx) (T − T∞)  =  0
```

Every term is in watts: (W/(m K))(m²)(K/m) = W and (W/(m² K))(m²)(K) = W. Divide by kAδx and let δx → 0 (Eq. 4.29); with θ = T − T∞ and constant T∞:

```
d²θ/dx² = (hP / kA) θ = m² θ,        m = √(hP/(kA))
```

m has units √[(W/(m² K))(m) / ((W/(m K))(m²))] = √(1/m²) = 1/m, so 1/m is a length: the distance over which the excess temperature of a long rod falls by e. This assumes one temperature per cross-section (Part 4), constant k and h, and constant T∞.

**Boundary conditions** (Lienhard Eq. 4.31b):

- **Base, x = 0: θ(0) = θ₀.** The temperature at the start of the analysis region is fixed and known. For the course rod, x = 0 is the first rod hole and θ₀ is what rod thermistor T1 measures there, not the TEC setpoint.
- **Tip, x = L: dθ/dx = 0 (insulated tip).** No heat crosses the end face. Physically, the end face area A is small compared with the side area PL, and h at the end is small, so the heat leaving through the tip is negligible. Part 3 checks this.

**Solution** (Lienhard Eqs. 4.34 to 4.41). With ξ = x/L the equation becomes d²Θ/dξ² = (mL)²Θ for Θ = θ/θ₀, whose general solution is

```
Θ = C₁ e^(mLξ) + C₂ e^(−mLξ)                                  (4.35)
```

The boundary conditions Θ(0) = 1 and dΘ/dξ(1) = 0 give C₁ + C₂ = 1 and C₁e^(mL) − C₂e^(−mL) = 0, so

```
C₁ = e^(−mL) / (2 cosh mL),        C₂ = 1 − e^(−mL) / (2 cosh mL)
Θ(x) = θ(x)/θ₀ = cosh[m(L − x)] / cosh(mL)                    (4.41)
```

Check: at x = 0 this gives 1, and its derivative −m sinh[m(L − x)]/cosh(mL) is zero at x = L. The tip sits at Θ = 1/cosh(mL) (Eq. 4.45), and the heat entering the base is Q₀ = √(kAhP) θ₀ tanh(mL) (Eq. 4.44).

## Part 3. Provisional finite-length prediction

### Lienhard Problem 4.12: the semi-infinite limit

Use the general solution (4.35) with θ(0) = θ₀ and θ(L) = 0 (the far end at room temperature): C₁ + C₂ = 1 and C₁e^(mL) + C₂e^(−mL) = 0. Then C₂ = 1/(1 − e^(−2mL)) and C₁ = −e^(−2mL)/(1 − e^(−2mL)), so

```
Θ = [e^(−mx) − e^(−2mL) e^(mx)] / (1 − e^(−2mL)) = sinh[m(L − x)] / sinh(mL)
```

As L becomes very long (mL → ∞), e^(−2mL) → 0 and both the second term and the denominator correction vanish at any fixed x:

```
lim (L→∞) Θ = e^(−mx)                                          (4.50)
```

The insulated-tip solution has the same limit, because cosh[m(L − x)]/cosh(mL) → e^(−mx) as well: far from the tip, the tip condition stops mattering. Lienhard's rule of thumb is that a fin is "infinitely long" for temperature when mL is above about 5.

### Example 4.8 and Problem 4.20: how good is the insulated tip?

Example 4.8 is an aluminium rod (k = 205 W/(m K), D = 2.0 cm, L = 8.0 cm, h = h_L = 120 W/(m² K)), so mL = 0.8656 and the axial Biot number Bi_ax = h_L L/k = 0.0468. With tip convection (Eq. 4.48), Θ_tip = 1/(cosh mL + (Bi_ax/mL) sinh mL) = 0.689; with an insulated tip (Eq. 4.41), Θ_tip = 1/cosh mL = 0.715, about 4 % higher. For the heat flow (Problem 4.20), Eq. 4.49 gives Q₀/√(kAhP)θ₀ = (Bi_ax/mL + tanh mL)/(1 + (Bi_ax/mL) tanh mL) = 0.7258 with tip convection and tanh mL = 0.6991 with the insulated tip, an error of (0.7258 − 0.6991)/0.7258 = **3.67 %**. Even with a large h, the insulated tip is a few-percent approximation.

### The course rod

**Inputs.** 6061-T6 aluminium. Measured diameter D = 12.757 ± 0.006 mm, so R = 6.378 mm, A = πR² = 1.278 × 10⁻⁴ m², P = 2πR = 4.008 × 10⁻² m and A/P = R/2 = 3.19 × 10⁻³ m. Analysis length from the first rod hole (x = 0) to the top: L = 281.9 ± 1.3 mm. Planned sensor positions: T1 to T5 at x = 0, 25.4, 50.8, 76.2 and 101.6 mm (the first five holes, 1 in apart, ±1 mm). Provisional h = 10 W/(m² K) for natural convection in still air. Conductivity: Table A.1 gives k = 167 W/(m K) at 20 °C for 6061-T6 and 166 to 172 W/(m K) between 0 and 100 °C, the range of rod temperatures in this experiment; I use **166 to 172 W/(m K)**, and test a wider ±10 % (150 to 185 W/(m K)) to allow for alloy and source variation.

**m and mL.** For a circular rod m = √(hP/(kA)) = √(2h/(kR)):

| k (W/(m K)) | m (1/m) | 1/m (mm) | mL |
|---|---|---|---|
| 150 | 4.57 | 219 | 1.29 |
| 166 | 4.35 | 230 | 1.23 |
| 172 | 4.27 | 234 | 1.20 |
| 185 | 4.12 | 243 | 1.16 |

mL ≈ 1.2 is far below Lienhard's mL ≈ 5 for a temperature calculation to treat the fin as infinitely long, and 1/m is comparable to L.

**Finite-length error at each sensor,** ε_T(x) = |Θ_finite − e^(−mx)| / Θ_finite:

| k (W/(m K)) | T1 (0 mm) | T2 (25.4) | T3 (50.8) | T4 (76.2) | T5 (101.6) |
|---|---|---|---|---|---|
| 150 | 0 | 1.8 % | 4.0 % | 6.6 % | 9.8 % |
| 166 | 0 | 1.9 % | 4.2 % | 6.9 % | 10.1 % |
| 172 | 0 | 2.0 % | 4.3 % | 7.0 % | 10.2 % |
| 185 | 0 | 2.0 % | 4.4 % | 7.2 % | 10.5 % |

The error grows with x because the reflected solution e^(+mx) matters more closer to the tip. Its size hardly depends on k across this range.

**Tip approximation for the course rod.** Taking h_L = h = 10 W/(m² K) at the top face, Bi_ax = h_L L/k = 0.016 to 0.017 (k = 166 to 172), much smaller than in Example 4.8. Replacing the insulated tip (4.41) with the convective tip (4.48) changes Θ by at most 0.26 % at T5 and 1.2 % at the tip itself, and the base heat flow by 0.5 %. The insulated tip is an excellent approximation here; the finite length is not negligible.

**Prediction.** With an error criterion of ε_T < 5 % at every sensor used in the analysis (the course's suggested criterion), the semi-infinite model is adequate for T1, T2 and T3 (x ≤ 50.8 mm, ε_T ≤ 4.4 %) but **not** for T4 (6.6 to 7.2 %) or T5 (9.8 to 10.5 %), for any k from 150 to 185 W/(m K) at h = 10 W/(m² K). I therefore do not expect the course rod to be adequately semi-infinite over the whole measured region, and I will fit the finite insulated-tip solution (with the semi-infinite fit as a comparison). This conclusion depends on: the positions above (moving T5 closer to the base would lower its error), L = 281.9 mm, h = 10 W/(m² K) (a larger h raises mL and lowers ε_T), the k range, and the 5 % criterion.

## Part 4. Provisional one-dimensional prediction

The transverse Biot number compares conduction resistance across the rod with convection resistance at its surface (Lienhard Eq. 4.27, using the transverse length A/P = R/2):

```
Bi_⊥ = h (A/P) / k = h R / (2k)
```

It is dimensionless: (W/(m² K))(m)/(W/(m K)) = 1. With h = 10 W/(m² K) and R = 6.378 mm:

| k (W/(m K)) | 150 | 166 | 172 | 185 |
|---|---|---|---|---|
| Bi<sub>⊥</sub> | 2.1 × 10⁻⁴ | 1.9 × 10⁻⁴ | 1.85 × 10⁻⁴ | 1.7 × 10⁻⁴ |

Bi<sub>⊥</sub> ≈ 2 × 10⁻⁴, much less than 1: radial conduction inside the aluminium is thousands of times faster than heat removal from the surface, so the temperature difference across a cross-section is of order Bi<sub>⊥</sub> times the surface-to-air difference: a few millikelvin for a rod 10 to 20 K above room. **Each cross-section can be represented by one temperature**, and a thermistor in a hole measures the temperature of its whole cross-section. This radial conclusion is separate from Part 3: the rod is thin enough to be one-dimensional but too short to be semi-infinite over the measured region.

**Application question.** The same heat sink in forced airflow has the **larger h**: moving air sweeps heated air away and thins the boundary layer next to the surface, so heat leaves faster per unit area and per degree. Lienhard's Table 1.1 lists h of a few to about 30 W/(m² K) for natural convection in air and tens of W/(m² K) and more for forced air. Because m = √(hP/(kA)), the decay length 1/m scales as h<sup>−1/2</sup>: a larger h makes the temperature fall off over a **shorter** distance, because more heat escapes through the sides before conduction can carry it along. For the course rod with k = 167 W/(m K), raising h from 10 to 100 W/(m² K) would shorten 1/m from 231 mm to 73 mm (and raise Bi<sub>⊥</sub> to 1.9 × 10⁻³, still small).

## Prediction record before heating

| Quantity | Provisional value (h = 10 W/(m² K), k = 166 to 172 W/(m K)) |
|---|---|
| m, 1/m | 4.27 to 4.35 m⁻¹, 230 to 234 mm |
| mL | 1.20 to 1.23 |
| Bi<sub>⊥</sub> | 1.85 to 1.92 × 10⁻⁴ |
| ε_T at T1 to T5 | 0, 1.9 to 2.0 %, 4.2 to 4.3 %, 6.9 to 7.0 %, 10.1 to 10.2 % |

- **Response order to a base step:** T1 first, then T2, T3, T4 and T5 in order, with arrival times growing roughly as x².
- **Response size:** each sensor's change smaller than the one before, because heat is lost through the side on the way.
- **Stationary profile:** decaying from T1, falling less steeply than e^(−mx) as it approaches the top because of the insulated tip; Θ ≈ 0.72 at T5 and 0.54 at the top.
- **Finite tip in the measured region:** the measured points (x ≤ 0.36 L) will not show the flattening near the tip directly, but the finite length changes the far sensors by 7 to 10 %, so a semi-infinite fit should give a noticeably smaller m than the finite fit.

## AI use

I used an AI assistant (Claude) to help draft and typeset this write-up and to check the arithmetic, as the course AI policy allows. I worked through each derivation step and checked every number against Lienhard's tables, equations and given answers (Problem 1.3, silver: 0.117 K; Problem 4.20: 3.67 %).
