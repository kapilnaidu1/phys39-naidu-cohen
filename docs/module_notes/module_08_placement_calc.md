# Sensor placement along the rod: the calculation

Naidu / Cohen, 28 October 2026. Data: run `rod_run_20261028_092033`, steady
window 4346 to 4646 s. Full analysis: [`module_08_stationary_fin.md`](module_08_stationary_fin.md).

## 1. Model

With θ = T − T_room, a rod with an insulated tip at steady state follows

```
θ(x) / θ(0) = cosh(m(L − x)) / cosh(mL),      m² = hP/(kA) = 2h/(kR)
```

x = 0 is the first rod sensor (R1), L is the distance from R1 to the tip.
The course placement target is θ(x5)/θ(0) ≤ 1/e = 0.368 for the farthest
sensor.

## 2. Our numbers

| | Value |
|---|---|
| T_room (all sensors, before heating) | 21.03 °C |
| θ1 at x = 0 | 16.83 °C |
| θ5 at x = 101.6 mm (4 in) | 12.44 °C |
| θ5/θ1 measured | 0.739 |
| L, R1 to rod top | 279 mm (about 11 in) |
| m from the fit | 4.12 m⁻¹ |
| mL | 1.15 |

Check: the model with m = 4.12 gives cosh(4.12 × 0.178)/cosh(1.15) = 0.737
at R5, against 0.739 measured.

## 3. Finite rods

Prof. Fraden has measured the course rods: all of them behave as finite
rods (reported to us 2 November), so the insulated-tip form above is the one
to use, not the semi-infinite exponential.

## 4. How to place your sensors

1. **Pilot.** Hold the base steady (the course says 45 °C), with R1 in the
   first hole and one sensor as far out as you can. Measure T_room before
   heating with all sensors together.
2. **Get m.** From two steady readings, solve
   θ(x)/θ(0) = cosh(m(L − x))/cosh(mL) for m (or fit all sensors). A quick
   first guess: m ≈ −ln(θ(x)/θ(0)) / x, which underestimates m on a short
   rod.
3. **Check mL.**
   - If **mL < 1.66**, no position on that rod reaches 1/e. Put the
     farthest sensor in the farthest hole and space the rest evenly from
     x = 0. Report the ratio you get.
   - If **mL ≥ 1.66**, the farthest sensor must be at or beyond
     ```
     x5 = L − arccosh( cosh(mL) / e ) / m
     ```
     and the others spaced evenly between 0 and x5, so they spread out on
     the ln θ against x plot.
4. **Spread matters more than count.** Our five sensors in the first 4 in
   all sit between 0.74 and 1 of θ(0). Over that range a cosh and an
   exponential look almost the same, so the data could not test the tip
   condition. The same five sensors spread to 8 in would cover 0.60 to 1.
