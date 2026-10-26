# Module 7, Part I: thermal transport foundations, preparation notes

Naidu / Cohen. Reading: Lienhard and Lienhard, *A Heat Transfer Textbook*,
Section 1.3, pp. 11 to 26, with the course page "Module 7, Part I: Thermal
Transport Foundations". These are the answers to the ten preparation
questions and the dimensional equation sheet the course asks us to keep here.

Lienhard Problem 1.3 is part of A4, which is individual, so it is not in this
team note.

---

## The ten preparation questions

**1. Why is Fourier's law a phenomenological constitutive law, and what does
its minus sign say?**
It is *constitutive* because it describes how a particular material responds:
it links the heat flux to the temperature field through a material property,
k. It is *phenomenological* because it summarises measured, macroscopic
behaviour (flux proportional to the local gradient, no flux in a uniform
temperature) without deriving it from phonons or electrons; k has to be
measured. Conservation of energy alone has two unknowns, T and q; Fourier's
law closes it. The minus sign in q = −k ∂T/∂x says heat flows *down* the
gradient, from hot to cold.

**2. Temperature, heat-transfer rate, heat flux; k, α, h.**

| Quantity | Meaning | Units |
|---|---|---|
| T | thermal state, how hot | K or °C |
| Q̇_x | heat-transfer rate (heat current) through a whole cross-section | W |
| q_x = Q̇_x / A | heat flux, rate per unit area | W/m² |
| k | thermal conductivity: flux carried per unit temperature gradient; a material property | W/(m·K) |
| α = k/(ρc) | thermal diffusivity: how fast a temperature disturbance spreads | m²/s |
| h | surface heat-transfer coefficient: flux from a surface per degree of surface-to-fluid difference; depends on the fluid, the flow and the geometry, not just the material | W/(m²·K) |

**3. Why does a larger k give a smaller gradient for the same flux?**
From q = k ΔT/L, the gradient needed is ΔT/L = q/k. A better conductor
carries the same heat with a gentler slope; a poor conductor (insulation)
needs a steep one.

**4. Lienhard Eq. (1.12): what is calculated?**
The net rate of heat conducted *out* of a thin slice of width δx: Fourier's
law at the right face minus Fourier's law at the left face. Because the two
gradients differ only by their change across δx, the difference is
−kA (∂²T/∂x²) δx.

**5. Lienhard Eq. (1.13): what is stored?**
Internal energy of the slice. Its rate of increase is ρ c A δx ∂T/∂t: mass
of the slice times specific heat times the rate of temperature rise.

**6. Why does combining (1.12) and (1.13) give an equation for T(x, t)
rather than for q?**
Energy conservation sets the net heat lost equal to minus the energy stored.
Fourier's law has already written the heat flow in terms of T (through
∂²T/∂x²), and the storage is also in T (through ∂T/∂t), so the flux q drops
out and what remains, ∂T/∂t = α ∂²T/∂x², involves T alone.

**7. What does α describe?**
How quickly a temperature disturbance spreads through the material: the
ratio of its ability to conduct heat (k) to its ability to store it (ρc). A
disturbance spreads a distance of order √(αt) in time t, so the time to reach
a distance x grows like x²/α.

**8. How does the resistance ratio give the Biot number, and why does a
small Bi justify one temperature?**
Heat leaving a body first conducts through it, R_cond ~ L_c/(kA), then
crosses the surface, R_conv ~ 1/(hA). Their ratio is hL_c/k = Bi, with
L_c = V/A_s. The same group appears when the convective boundary condition is
made dimensionless. If Bi ≪ 1, the internal resistance is small compared
with the surface resistance, so almost all of the temperature drop is across
the surface and the inside stays nearly uniform: one temperature, a lumped
model, is a good description.

**9. Why does the thermocouple example check Bi?**
The lumped result, an exponential with time constant τ = ρcV/(hA), assumes
the bead has one temperature. Checking that Bi is small confirms the
assumption before the formula is trusted; if Bi were not small, the bead's
centre and surface would differ and the simple time constant would be wrong.
It is the same reasoning we used for the TEC plate in Module 6, where the
one-lump model eventually failed.

**10. The two independent approximations for the long cylinder, and the
calculation that tests each.**
- *Length:* can the far end be ignored, so the rod is treated as
  semi-infinite? Tested by solving the finite-length problem and comparing it
  with the semi-infinite solution at each sensor position (mL and the
  sensor-by-sensor error ε_T).
- *Radius:* can temperature variation across a cross-section be ignored, so
  the rod is one-dimensional? Tested by the transverse Biot number,
  Bi_⊥ = h(A/P)/k = hR/(2k) ≪ 1.
"Long" and "thin" are separate claims; one can hold without the other.

---

## Dimensional equation sheet

| Relation | Equation | Units check |
|---|---|---|
| Fourier's law | q = −k ∂T/∂x;  Q̇ = −kA ∂T/∂x | W/m² = (W/(m·K))(K/m) |
| Conduction resistance | R_th = L/(kA), Q̇ = ΔT/R_th | K/W = m / ((W/(m·K)) m²) |
| Storage | Q̇ = mc dT/dt = C_th dT/dt | W = (J/K)(K/s) |
| 1-D heat equation | ∂T/∂t = α ∂²T/∂x², α = k/(ρc) | K/s = (m²/s)(K/m²) |
| With generation | ρc ∂T/∂t = k∇²T + q̇‴ | W/m³ each term |
| Newton's law of cooling | q = h (T_body − T_∞) | W/m² = (W/(m²·K)) K |
| Biot number | Bi = h L_c / k, L_c = V/A_s | dimensionless |
| Fourier number | Fo = αt / L_c² | dimensionless |
| Lumped cooling | (T − T_∞)/(T_i − T_∞) = e^(−t/τ), τ = ρcV/(hA) | s = (J/(m³K)) m³ / ((W/(m²K)) m²) |
| Long cylinder | L_c = A/P = R/2 | m |
| Rod with side loss (course, Part III) | ρcA ∂θ/∂t = kA ∂²θ/∂x² − hPθ | W/m each term |
| Same, divided by ρcA | ∂θ/∂t = κ ∂²θ/∂x² − νθ, κ = k/(ρc), ν = hP/(ρcA) | κ in m²/s, ν in 1/s |
| Decay coefficient | m² = hP/(kA) = ν/κ | 1/m² |
| Transverse Biot | Bi_⊥ = h(A/P)/k = hR/(2k) | dimensionless |
| Parallel Biot | Bi_∥ = hPL²/(kA) = (mL)² | dimensionless |

**Analogies (course page):** ΔT ↔ ΔV ↔ Δp; Q̇ ↔ I ↔ volume flow; R_th ↔
R ↔ R_hyd; C_th = mc ↔ capacitance ↔ tank area. The limit of the analogy:
heat is energy in transit, not a stored substance; what is stored is internal
energy.
