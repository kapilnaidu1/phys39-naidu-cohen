# A4: Finite-Rod Model and Validity Checks

Assessment code: A4 (individual)  
Student: Kapil Naidu (lab partner Samuel Cohen)  
Date: 4 November 2026  
Repository: https://github.com/kapilnaidu1/phys39-naidu-cohen, branch main

Equation and table numbers refer to Lienhard, *A Heat Transfer Textbook*, 6th edition. Material properties come from Tables A.1 and A.2.

## Part 1. Apply Fourier's law (Lienhard Problem 1.3)

The slab is 1 cm thick, carries q = 5000 W/m², and its cold side sits at −40 °C. At steady state with no heat generated inside, the same flux has to pass through every layer, so Fourier's law

```
q = −k dT/dx
```

gives a constant gradient. Integrating across the thickness L:

```
ΔT = T_hot − T_cold = q L / k
```

Units check: (W/m²)(m) / (W/(m K)) = K. Here qL = 5000 × 0.01 = 50 W/m, so for every material ΔT = (50 W/m)/k.

Sample calculation for pure silver: k = 427 W/(m K) (Table A.1, 20 °C), so ΔT = 50/427 = 0.117 K, which matches the answer printed with the problem. The hot face is at −39.88 °C.

| Material | k (W/(m K)), source | ΔT (K) | Hot side (°C) | Reasonable? |
|---|---|---|---|---|
| Pure silver | 427, A.1 (20 °C) | 0.117 | −39.88 | yes |
| Pure aluminum | 237, A.1 (20 °C) | 0.211 | −39.79 | yes |
| Mild steel (0.5 % C) | 54, A.1 (20 °C) | 0.926 | −39.07 | yes |
| Ice | 2.215, A.2 (0 °C) | 22.6 | −17.4 | yes, still below 0 °C so it stays frozen |
| Spruce | 0.11, A.2 (20 °C) | 455 | 415 | no |
| Insulation (85 % magnesia) | 0.067, A.2 (38 °C) | 746 | 706 | no |
| Silica aerogel | 0.024, A.2 (0 °C) | 2083 | 2043 | no |

The metals hardly notice this flux. With a large k only a small gradient is needed to carry the heat, which is also why our rod and TEC plate are aluminum. The last three are not believable. Spruce would char and catch fire well before its hot face got to 415 °C, so it could never carry this flux steadily. The magnesia table only goes from 38 to 150 °C, and this kind of insulation is used on steam pipes at a few hundred degrees, so 706 °C is way outside anything the data supports. For the aerogel the hot face would be above 2000 °C, hotter than silica can survive (it melts around 1700 °C). It's the same idea as our TEC, which we protect because it is only rated to 80 °C: push a big heat flux through something that conducts poorly and the temperature rise gets large enough to damage it. I also assumed k is constant. That's fine for the metals and ice, where the temperature hardly changes, but not for the three bad cases, where k would change over hundreds of degrees.

## Part 2. Build the stationary finite-rod model

I followed Lienhard Section 4.5 (Fig. 4.8). Take a thin slice of rod from x to x + δx. It has cross-section A, perimeter P, conductivity k, and loses heat from its side to air at T∞ with coefficient h. At steady state nothing is stored in the slice, so the heat conducted in at x has to equal the heat conducted out at x + δx plus the heat lost from the side area Pδx.

Fourier's law gives the conducted heat, Q = −kA dT/dx, and Newton's law of cooling gives the side loss, hPδx (T − T∞). Putting them together (Eq. 4.28):

```
−kA dT/dx |(x+δx)  +  kA dT/dx |(x)  +  h (P δx) (T − T∞)  =  0
```

Each term is in watts: (W/(m K))(m²)(K/m) = W and (W/(m² K))(m²)(K) = W. Dividing by kAδx and letting δx go to zero (Eq. 4.29), and writing θ = T − T∞ with T∞ constant:

```
d²θ/dx² = (hP / kA) θ = m² θ,        m = √(hP/(kA))
```

For units, hP/(kA) is (W/(m² K))(m) / ((W/(m K))(m²)) = 1/m², so m is in 1/m and 1/m is a length. It's the distance over which the excess temperature of a long rod drops by a factor of e. Along the way I assumed one temperature per cross-section (checked in Part 4), constant k and h, and a constant room temperature.

The two boundary conditions (Eq. 4.31b) are:

- At the base, x = 0: θ(0) = θ₀. The temperature where the analysis starts is fixed and known. On the course rod, x = 0 is the first rod hole and θ₀ is whatever thermistor T1 reads there, not the TEC setpoint.
- At the tip, x = L: dθ/dx = 0. No heat leaves through the end face. This is reasonable because the end face is tiny next to the side area PL, and h is small, so hardly any heat goes out the end. I check how good this is in Part 3.

To solve it, write ξ = x/L and Θ = θ/θ₀. The equation becomes d²Θ/dξ² = (mL)²Θ, with general solution

```
Θ = C₁ e^(mLξ) + C₂ e^(−mLξ)                                  (4.35)
```

Θ(0) = 1 gives C₁ + C₂ = 1, and dΘ/dξ = 0 at ξ = 1 gives C₁e^(mL) − C₂e^(−mL) = 0. Solving:

```
C₁ = e^(−mL) / (2 cosh mL),        C₂ = 1 − e^(−mL) / (2 cosh mL)
Θ(x) = θ(x)/θ₀ = cosh[m(L − x)] / cosh(mL)                    (4.41)
```

Checking: at x = 0 this is 1, and its derivative, −m sinh[m(L − x)]/cosh(mL), is zero at x = L. The tip ends up at Θ = 1/cosh(mL) (Eq. 4.45), and the heat going into the base is Q₀ = √(kAhP) θ₀ tanh(mL) (Eq. 4.44).

## Part 3. Provisional finite-length prediction

### Problem 4.12: the semi-infinite limit

Start again from the general solution (4.35), now with θ(0) = θ₀ and θ(L) = 0, meaning the far end is at room temperature. Then C₁ + C₂ = 1 and C₁e^(mL) + C₂e^(−mL) = 0, which give C₂ = 1/(1 − e^(−2mL)) and C₁ = −e^(−2mL)/(1 − e^(−2mL)). So

```
Θ = [e^(−mx) − e^(−2mL) e^(mx)] / (1 − e^(−2mL)) = sinh[m(L − x)] / sinh(mL)
```

If the rod gets very long (mL → ∞), e^(−2mL) goes to zero. At any fixed x the second term and the correction in the denominator both disappear, leaving

```
lim (L→∞) Θ = e^(−mx)                                          (4.50)
```

The insulated-tip answer has the same limit, since cosh[m(L − x)]/cosh(mL) also goes to e^(−mx). Far enough from the tip, it stops mattering what happens there. Lienhard's rule of thumb is that a fin counts as infinitely long for temperature once mL is above about 5.

### Example 4.8 and Problem 4.20: is the insulated tip good enough?

Example 4.8 is an aluminum rod with k = 205 W/(m K), D = 2.0 cm, L = 8.0 cm and h = h_L = 120 W/(m² K), so mL = 0.8656 and the axial Biot number is Bi_ax = h_L L/k = 0.0468. Including convection at the tip (Eq. 4.48), Θ_tip = 1/(cosh mL + (Bi_ax/mL) sinh mL) = 0.689. Treating the tip as insulated (Eq. 4.41), Θ_tip = 1/cosh mL = 0.715, about 4 % too high. For the heat flow (Problem 4.20), Eq. 4.49 gives Q₀/(√(kAhP) θ₀) = (Bi_ax/mL + tanh mL)/(1 + (Bi_ax/mL) tanh mL) = 0.7258 with tip convection, against tanh mL = 0.6991 with the tip insulated. The error is (0.7258 − 0.6991)/0.7258 = 3.67 %, which matches the book. So even with a big h, insulating the tip only costs a few percent.

### Our rod

Inputs:

- Material: 6061-T6 aluminum.
- Diameter (calipers, 3 places): D = 12.757 ± 0.006 mm, so R = 6.378 mm, A = πR² = 1.278 × 10⁻⁴ m², P = 2πR = 4.008 × 10⁻² m and A/P = R/2 = 3.19 × 10⁻³ m.
- Analysis length from the first rod hole (x = 0) to the top: L = 281.9 ± 1.3 mm.
- Planned sensor positions: T1 to T5 at x = 0, 25.4, 50.8, 76.2 and 101.6 mm, the first five holes, 1 in apart (±1 mm).
- Provisional h = 10 W/(m² K) for natural convection in still air.
- Conductivity: Table A.1 lists 6061-T6 at 167 W/(m K) at 20 °C and 166 to 172 W/(m K) between 0 and 100 °C, which covers the temperatures in this experiment. I used 166 to 172 W/(m K), and also tried ±10 % (150 to 185 W/(m K)) in case the real alloy or temper differs from the table.

For a round rod m = √(hP/(kA)) = √(2h/(kR)):

| k (W/(m K)) | m (1/m) | 1/m (mm) | mL |
|---|---|---|---|
| 150 | 4.57 | 219 | 1.29 |
| 166 | 4.35 | 230 | 1.23 |
| 172 | 4.27 | 234 | 1.20 |
| 185 | 4.12 | 243 | 1.16 |

So mL is about 1.2, nowhere near the mL ≈ 5 needed for the rod to count as infinitely long, and 1/m is about the same as L.

Finite-length error at each sensor, ε_T(x) = |Θ_finite − e^(−mx)| / Θ_finite:

| k (W/(m K)) | T1 (0 mm) | T2 (25.4) | T3 (50.8) | T4 (76.2) | T5 (101.6) |
|---|---|---|---|---|---|
| 150 | 0 | 1.8 % | 4.0 % | 6.6 % | 9.8 % |
| 166 | 0 | 1.9 % | 4.2 % | 6.9 % | 10.1 % |
| 172 | 0 | 2.0 % | 4.3 % | 7.0 % | 10.2 % |
| 185 | 0 | 2.0 % | 4.4 % | 7.2 % | 10.5 % |

The error gets bigger the farther out the sensor is, because the e^(+mx) part of the solution, which comes from the tip, matters more closer to the tip. It barely changes over the whole k range.

Tip condition on our rod: if the top face has the same h = 10 W/(m² K), then Bi_ax = h L/k = 0.016 to 0.017 for k = 166 to 172, much smaller than the 0.0468 in Example 4.8. Using the convective-tip solution (4.48) instead of the insulated one (4.41) changes Θ by at most 0.26 % at T5 and 1.2 % right at the tip, and changes the base heat flow by 0.5 %. So assuming an insulated tip is fine for our rod; ignoring the rod's finite length is not.

Prediction: using ε_T < 5 % at every sensor used in the fit (the criterion suggested in the course notes), the semi-infinite model works for T1, T2 and T3 (x up to 50.8 mm, ε_T at most 4.4 %), but not for T4 (6.6 to 7.2 %) or T5 (9.8 to 10.5 %). That holds for any k from 150 to 185 W/(m K) at h = 10 W/(m² K). So I don't expect the course rod to be semi-infinite over the whole measured region, and I plan to fit the finite insulated-tip solution, with the semi-infinite fit as a comparison. This depends on the sensor positions above (moving T5 closer to the base would lower its error), on L = 281.9 mm, on h = 10 W/(m² K) (a bigger h raises mL and lowers ε_T), on the k range, and on choosing 5 % as the cutoff.

## Part 4. Provisional one-dimensional prediction

The transverse Biot number compares the resistance to conduction across the rod with the resistance to convection off its surface. Lienhard uses A/P = R/2 as the transverse length (Eq. 4.27):

```
Bi_⊥ = h (A/P) / k = h R / (2k)
```

It's dimensionless: (W/(m² K))(m) / (W/(m K)) = 1. With h = 10 W/(m² K) and R = 6.378 mm:

| k (W/(m K)) | 150 | 166 | 172 | 185 |
|---|---|---|---|---|
| Bi<sub>⊥</sub> | 2.1 × 10⁻⁴ | 1.9 × 10⁻⁴ | 1.85 × 10⁻⁴ | 1.7 × 10⁻⁴ |

Bi<sub>⊥</sub> is about 2 × 10⁻⁴, way below 1. Heat moves across the inside of the aluminum thousands of times more easily than it leaves the surface, so the temperature difference across a cross-section is roughly Bi<sub>⊥</sub> times the surface-to-air difference. For a rod 10 to 20 K above room that's only a few millikelvin. So each cross-section can be treated as one temperature, and a thermistor in a hole reads the temperature of that whole slice. This is a separate conclusion from Part 3: the rod is thin enough to be one-dimensional, but it is not long enough to be semi-infinite over the measured region.

Application question. The same heat sink in forced airflow has the larger h. Moving air keeps carrying the warmed air away and thins the boundary layer at the surface, so more heat leaves per unit area per degree. Lienhard's Table 1.1 gives a few to about 30 W/(m² K) for natural convection in air and tens of W/(m² K) and up for forced air. Since m = √(hP/(kA)), the decay length 1/m goes as h<sup>−1/2</sup>. A larger h means the temperature drops off over a shorter distance, because more heat leaks out the sides before conduction can carry it along the rod. For our rod with k = 167 W/(m K), going from h = 10 to 100 W/(m² K) would shrink 1/m from 231 mm to 73 mm. Bi<sub>⊥</sub> would go up to 1.9 × 10⁻³, still small.

## Prediction record before heating

| Quantity | Provisional value (h = 10 W/(m² K), k = 166 to 172 W/(m K)) |
|---|---|
| m, 1/m | 4.27 to 4.35 m⁻¹, 230 to 234 mm |
| mL | 1.20 to 1.23 |
| Bi<sub>⊥</sub> | 1.85 to 1.92 × 10⁻⁴ |
| ε_T at T1 to T5 | 0, 1.9 to 2.0 %, 4.2 to 4.3 %, 6.9 to 7.0 %, 10.1 to 10.2 % |

What I expect to see:

- After a step at the base, T1 responds first, then T2, T3, T4 and T5 in order, with the delay growing roughly like x².
- Each sensor changes less than the one before it, since heat is lost out the sides along the way.
- The steady profile falls off from T1 but less steeply than e^(−mx) toward the top, because of the insulated tip: about Θ = 0.72 at T5 and 0.54 at the top.
- The sensors only cover the first 36 % of L, so they won't show the flattening near the tip directly. But the finite length still shifts the far sensors by 7 to 10 %, so a semi-infinite fit should come out with a noticeably smaller m than the finite fit.
