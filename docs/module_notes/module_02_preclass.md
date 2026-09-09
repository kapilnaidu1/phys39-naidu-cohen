# Module 2 pre-class questions

Naidu / Cohen. Session S4, Wednesday 9 September 2026.

Sensor: **TDK/EPCOS B57861S0104F040V24**, 100 kΩ NTC, R/T characteristic **No. 2014**,
B25/100 = **4540 K**, R25 = 100.000 kΩ, tolerance ±1%.
Fixed resistor: 100 kΩ precision.

---

## Q1. Expected divider voltage at 15 °C, 25 °C and 35 °C

### The circuit

Part 1 wires it as 5 V → fixed resistor → A0 → thermistor → GND. The **thermistor is the
bottom leg**, so A0 sits across the thermistor:

$$V_{A0} = V_{ref}\cdot\frac{R_{th}}{R_{th} + R_{fixed}} = 5.00\cdot\frac{R_{th}}{R_{th} + 100\,\text{k}\Omega}$$

An NTC falls in resistance as it warms, so **V_A0 falls as temperature rises**. Getting the
orientation backwards flips the sign of the whole response, which is the first thing to check
if the plot moves the wrong way when you pinch the thermistor.

### Resistances, read straight off the data-sheet table

| T | R_nom (datasheet) | V_A0 | Expected ADC count |
|---|---|---|---|
| 15 °C | 165.440 kΩ | **3.116 V** | 638 |
| 25 °C | 100.000 kΩ | **2.500 V** | 512 |
| 35 °C | 62.031 kΩ | **1.914 V** | 392 |

Check the 25 °C row by inspection: at R25 the two legs are equal, so the divider must sit at
exactly half of 5.00 V. It does. That is the sanity check to run first in class.

### The same three points from the beta equation

Our sketch will not carry a lookup table, it will use the beta model:

$$R(T) = R_{25}\exp\left[B\left(\frac{1}{T}-\frac{1}{T_{25}}\right)\right],\qquad T \text{ in kelvin}$$

With B = 4540 K and T25 = 298.15 K:

| T | R from beta model | V_A0 | Difference from datasheet |
|---|---|---|---|
| 15 °C | 169.64 kΩ | 3.146 V | +30 mV |
| 25 °C | 100.00 kΩ | 2.500 V | 0 (anchor point) |
| 35 °C | 61.01 kΩ | 1.895 V | −19 mV |

**The two methods disagree by up to 30 mV**, and that is not a mistake in either one. B25/100
is fitted across 25 °C to 100 °C, so using it near room temperature and below is extrapolation
outside the interval it was extracted from. The model is exact only at 25 °C, where it is pinned.

Worth having this number in mind: **30 mV is about six times our ADC resolution of 4.88 mV.**
The choice of model matters more than the measurement does.

### Sensitivity, for interpreting the above

Around 15 °C the divider moves roughly **−60 mV per °C**, so:

- one ADC count, 4.88 mV, is about **0.08 °C** of resolution
- the ±1% resistance tolerance is ±12.5 mV at 25 °C, about **±0.2 °C** (the datasheet's own ΔT column agrees)
- the 30 mV model disagreement is about **0.5 °C**

---

## Q2. Why is a temperature reading more model-dependent than a voltage reading?

A voltage reading is nearly a direct measurement. It is one ADC integer times a single
scale factor, `V = Vref * n / 1023`. The only assumption is that the reference really is
5.00 V. Nothing about the physics of the sensor enters.

A temperature reading is the output of a chain of models, each with parameters we did not
measure ourselves:

1. **The divider equation** assumes the fixed resistor is exactly 100 kΩ, that it does not
   drift with its own temperature, and that A0 draws no current. Its tolerance propagates
   straight into R_th.
2. **The R–T relation** is an approximation. The beta equation is a two-point fit; the
   Steinhart-Hart form with three coefficients does better. As shown above, our B of 4540 K
   is fitted over 25–100 °C and disagrees with the manufacturer's own table by about 0.5 °C
   at 15 °C and 35 °C.
3. **The datasheet parameters have tolerances.** R25 is ±1% and B is ±1%, and neither is
   something we calibrated.
4. **Self-heating.** The divider dissipates power in the thermistor, so it reads slightly
   above ambient. The dissipation factor is 1.5 mW/K, and at 25 °C the divider puts about
   31 µW through it, so this is roughly 0.02 °C here. Small, but it is a real bias that no
   amount of averaging removes.
5. **Thermal lag.** The cooling time constant in air is about 15 s, so the thermistor reports
   its own temperature, not the air's, whenever conditions are changing.

So the uncertainty in voltage is dominated by **noise**, which averaging reduces as 1/√N. The
uncertainty in temperature is dominated by **model and calibration error**, which averaging does
nothing to. This is the Module 1 distinction between precision and accuracy, appearing again:
we can report a temperature to 0.01 °C of precision that is wrong by 0.5 °C.

It also explains a design rule the assignment imposes. Because the R–T relation is nonlinear,
averaging voltages and then converting is not the same as converting each reading and then
averaging the temperatures. The assignment requires the first, which is the correct order.

---

## Q3. H-bridge input signals

Board: BTS7960. Arduino pin **9 → RPWM**, pin **10 → LPWM**. `R_EN`, `L_EN` and logic `VCC`
to Arduino 5 V; logic `GND` to Arduino GND. Direction chosen by a digital input, e.g. pin 11.

| Case | Direction input (pin 11) | Pin 9 (RPWM) | Pin 10 (LPWM) | Result |
|---|---|---|---|---|
| PWM = 0 | either | `0 V` | `0 V` | No current. Motor coasts, TEC does nothing. |
| Low-power heat / clockwise | `5 V` (HIGH) | **PWM**, small duty | `0 V` | Current one way, average voltage across the load = D × V_supply |
| Low-power cool / counterclockwise | `0 V` (LOW) | `0 V` | **PWM**, small duty | Current reversed, same magnitude for the same duty |

**Which pin carries PWM.** Exactly one of the two, and it is the one for the direction you
want. The other is held at a steady `0 V`. Never both at once. Both enables stay high the
whole time; direction is chosen by which input receives the pulse train, not by the enables.

**Why the idle pin must be LOW and not HIGH.** On this style of driver, holding the inactive
input high while pulsing the other inverts the meaning of the duty cycle, so a commanded
duty of 0 would produce full drive. Holding it at 0 V keeps the mapping direct: commanded
duty D gives average output D × V_supply, and D = 0 genuinely means off.

**What "PWM = 0" looks like.** Both inputs sit at a flat 0 V with no switching, so both
outputs are off and M+ and M− rest at the same potential. There is no voltage across the
load and therefore no current in either direction.

**What to expect on the scope in 3B.** The active pin shows a 490 Hz square wave switching
0 to 5 V with the commanded duty cycle; the inactive pin shows a flat 0 V line. Swapping the
direction input should swap which pin is which, with the duty unchanged.

**Safety, from the assignment.** Every scope ground clip goes to Arduino `GND`. Never to `M+`
or `M-`; both are driven outputs, and grounding either through the scope can short the bridge.

---

## Q4. One advantage of Serial Plotter over Serial Monitor

**It shows the shape of the data in time, which a column of numbers does not.** The plotter
draws each value against read order as it arrives, so trend, noise amplitude, drift, and the
response to a disturbance are visible instantly. Reading the same information out of a
scrolling list of digits is essentially impossible.

For this module specifically: pinch the thermistor and the plotter shows the curve bend, rise,
and level off, and you can see the roughly 15 s time constant directly in the shape. Serial
Monitor would show a column of numbers slowly getting larger.

We saw this in Module 1 too. The drop in scatter at the transition from single readings to
1000-reading averages was obvious at a glance on the plotter and invisible in the Monitor.

The trade-off, which is why Part 1 and Part 2 use different output formats: the Monitor gives
exact labeled values with units, while the plotter autoscales, has no units, and needs one bare
number per line. Each format is built for a different question.

**The format rule, learned the hard way in Module 1.** The plotter treats each newline as a
data point and needs exactly one numeric quantity per line. `label:value` creates a named
series; a bare number is plotted too; but a label that varies from line to line creates a new
series every line and nothing renders. For Part 2, print only the number.
