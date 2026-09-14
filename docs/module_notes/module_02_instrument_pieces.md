# Module 2 instrument pieces

**C2 evidence record.** Naidu / Cohen. Measurements made in Session S4, Wednesday 9 September 2026.

Sketches referenced rather than pasted, as the assignment asks:

- [`arduino/thermistor_serial/thermistor_serial.ino`](../../arduino/thermistor_serial/thermistor_serial.ino) — Parts 1 and 2
- [`arduino/trimpot_hbridge/trimpot_hbridge.ino`](../../arduino/trimpot_hbridge/trimpot_hbridge.ino) — Part 3

Raw records:

- [`data/module_02/part1_part2_thermistor.txt`](../../data/module_02/part1_part2_thermistor.txt)
- [`data/module_02/part3_hbridge_motor.txt`](../../data/module_02/part3_hbridge_motor.txt)

---

## 1. Thermistor divider circuit

```
        +5V (Arduino)
          |
          |
       [ R_fixed ]        100.0 kOhm precision resistor, upper leg
          |
          +-------------> A0   (divider midpoint, the measured node)
          |
       [ R_th ]           NTC thermistor, lower leg
          |
         GND (Arduino)
```

The thermistor is the **lower** leg, so A0 sits across the thermistor:

$$V_{A0} = V_{ref}\cdot\frac{R_{th}}{R_{th}+R_{fixed}}$$

An NTC falls in resistance as it warms, so **V_A0 falls as temperature rises**
while the reported temperature goes up. If warming the thermistor moves the
reading the wrong way, the two legs are swapped. Every line of our Part 1
capture obeys this, which is the orientation check.

## 2. Three human-readable serial lines from Part 1

Copied from the clean re-run, `data/module_02/part1_part2_thermistor.txt`:

```
time = 126.00 s    average ADC = 565.9    voltage = 2.766 V    resistance = 123.82 kOhm    temperature = 20.9 C    samples = 500
time = 156.00 s    average ADC = 450.3    voltage = 2.201 V    resistance = 78.64 kOhm    temperature = 29.8 C    samples = 500
time = 200.00 s    average ADC = 561.8    voltage = 2.746 V    resistance = 121.79 kOhm    temperature = 21.2 C    samples = 500
```

Baseline at ambient, finger contact, and the return to baseline about 45 s
after release. Every number carries a label and a unit.

## 3. Conversion chain, averaged ADC count to temperature

Four steps, in this order and no other:

| Step | Operation | Equation |
|---|---|---|
| 1 | Average the raw counts | $\bar n = \frac{1}{N}\sum_{i=1}^{N} n_i$, N = 500 |
| 2 | One average voltage | $V = V_{ref}\,\bar n / 1023$ |
| 3 | Invert the divider | $R_{th} = R_{fixed}\,\dfrac{V}{V_{ref}-V}$ |
| 4 | Beta model | $\dfrac{1}{T} = \dfrac{1}{T_0} + \dfrac{1}{B}\ln\dfrac{R_{th}}{R_0}$, T in kelvin |

**Why the order is fixed.** Step 4 is nonlinear, so the mean of the
temperatures is not the temperature of the mean. Averaging counts first and
converting once is the correct operation; converting each raw reading and then
averaging the temperatures would introduce a bias that gets worse the wider
the spread. The assignment requires the first form from this module onward.

Worked example, taking the t = 156.00 s line above:

```
n̄   = 450.3 counts
V   = 5.00 × 450.3 / 1023            = 2.201 V
Rth = 100.0 k × 2.201 / (5.00−2.201) = 78.64 kOhm
T   = [1/298.15 + (1/4540)·ln(0.7864)]⁻¹ − 273.15 = 29.8 °C
```

## 4. Thermistor constants used in the sketch

| Constant | Value | Source |
|---|---|---|
| Part | TDK/EPCOS **B57861S0104F040V24** | part marking |
| R/T characteristic | No. 2014 | datasheet |
| R25 (`Rnominal`) | 100.000 kOhm | datasheet |
| T0 (`Tnominal`) | 25.0 °C = 298.15 K | datasheet anchor |
| B25/100 (`Beta`) | 4540 K | datasheet |
| Tolerance | ±1% on R25 and on B | datasheet |
| Dissipation factor | 1.5 mW/K | datasheet |
| Cooling time constant, air | ~15 s | datasheet |
| R_fixed | 100.0 kOhm | precision resistor |
| V_ref | 5.00 V | Arduino analog reference |
| N (`sampleCount`) | 500 | our choice, inside the required 100 to 1000 |

**A caveat we are recording rather than hiding.** B25/100 is fitted over
25 °C to 100 °C. Using it near and below room temperature is extrapolation
outside that interval, and it disagrees with the manufacturer's own R/T table
by about 30 mV of divider voltage at 15 °C, which is roughly 0.5 °C. The model
is exact only at 25 °C, where it is anchored. For scale, 30 mV is about six
times the ADC resolution of 4.88 mV, so the choice of model matters more here
than the measurement does.

## 5. Serial Plotter record, temperature versus serial read order

Code change: a single flag, `PLOTTER_MODE`. With it `true`, `loop()` calls
`Serial.println(celsius, 2)` and nothing else, so each newline is one data
point and no label varies between lines. That last part matters: a label that
changes from line to line makes Serial Plotter open a new series every line
and nothing renders.

Three runs were recorded, all in `data/module_02/part1_part2_thermistor.txt`:

| Run | Values | What it shows |
|---|---|---|
| Batch 1 | 161 | warming under finger contact, 30.6 → 35.0 °C |
| Batch 2 | 57 | untouched for over 60 s, still drifted up 2.5 °C |
| Batch 3 | 353 | full excursion, warm to 35.2 °C then wet-finger cooling to 25.6 °C |

Shape of Batch 3, sketched from the data (temperature against read order):

```
 35 C |        ....--''''`-.                       .-'''-.
      |    .-''             `.                   .'       `.
 30 C |.-''                   `-.              .'           `--.....
      |                          `-.        .-'
 25 C |                             `------'
      +--------------------------------------------------------------->
      0                         read order                        353
```

**Direction of response:** warming the thermistor between finger and thumb
moved the plotted temperature **up**; a slightly moistened finger moved it
**down**. Both are the expected direction for an NTC in the lower leg.

The curvature is the sensor's own thermal lag. The 15 s cooling time constant
is visible directly as the rounding at each turn, which is the thing a column
of numbers in Serial Monitor does not show and a plot does.

## 6. Trim pot to PWM signal path

Code: [`arduino/trimpot_hbridge/trimpot_hbridge.ino`](../../arduino/trimpot_hbridge/trimpot_hbridge.ino)

```
trim-pot voltage -> analogRead(A1) × 200, averaged -> map to 0..255
                 -> analogWrite(pin 9 or pin 10) -> H-bridge input
```

The two resolutions are different and the conversion between them is where
the interesting behaviour lives. The analog input is 10-bit, 0 to 1023. The
PWM output is 8-bit, 0 to 255.

```cpp
int duty = map((long)potAdc, 0, 1023, 0, maxDuty);
```

**A double quantization.** `potAdc` is a float average of 200 reads, but
`map()` takes `(long)potAdc`, so the average is truncated to a whole ADC count
*before* the 10-bit to 8-bit scaling. We saw the consequence directly: at a
steady pot reading of 269.0 the reported duty alternated between 66 and 67
from line to line, because `floor(268.x) → 66` and `floor(269.0) → 67`. The
averaging buys resolution in the printed ADC column and the integer `map()`
throws most of it back away at the output.

## 7. H-bridge signal table

Direction selected by a digital input on pin 11. Board: BTS7960, pin 9 to
`RPWM`, pin 10 to `LPWM`, with `R_EN`, `L_EN` and logic `VCC` at 5 V and logic
`GND` to Arduino `GND`.

| Direction input (pin 11) | Mode | Pin 9 (RPWM) | Pin 10 (LPWM) | Measured at duty 197/255 |
|---|---|---|---|---|
| `5V` HIGH | heat / clockwise | **PWM** | `0V` | shaft turned clockwise |
| `0V` LOW | cool / counterclockwise | `0V` | **PWM** | shaft turned counterclockwise |
| either | PWM commanded 0 | `0V` | `0V` | no current, motor coasts |

Verified at four separate knob settings (duty 85, 197, 216 and 254 of 255) by
toggling pin 11 and confirming the duty field was identical either side of the
toggle. Exactly one input carried PWM at a time and the other read `0 V`.

**Why the idle input is held LOW and never HIGH.** On this driver, holding the
inactive input high while pulsing the other inverts the meaning of the duty
cycle, so a commanded duty of 0 would produce full drive. At `0 V` the mapping
stays direct: commanded duty D gives an average output of D × V_supply, and
D = 0 genuinely means off. Our `setDrive()` also drives the idle pin low
*before* energizing the active one, so there is never an instant with both
inputs asserted.

**PWM timebase.** Pins 9 and 10 are both on Timer1, phase-correct, prescaler
64, so f = 16 MHz / (64 × 510) = **490.196 Hz**, T = **2040 µs**, and one
`analogWrite` count is exactly **8.000 µs**. Confirmed against the Module 1
Tektronix measurements of the same pin 9: 408.1 µs at 20% and 1.632 ms at 80%
are exactly 51 × 8 µs and 204 × 8 µs.

## 8. M+ and M− oscilloscope comparison, both directions

**Probe grounding, which is the safety-critical part of this item.** Both
oscilloscope probe ground clips were connected to **Arduino GND**, and to
nothing else, for every capture in Module 2. A ground clip is
earth-referenced, and `M+` and `M−` are both driven H-bridge outputs rather
than ground points, so clipping a ground lead to either one can short the
bridge. `M+` and `M−` are measured with the probe **tip**, each relative to
Arduino GND.

Load and power state during the Part 3 captures: the TEC module and thermal
switch were **disconnected** from the load terminals for all of Module 2, and
the only load on `M+`/`M−` was the small DC motor.

**Instrument.** The captures were taken on a **BK Precision 2120B**, a
dual-trace 30 MHz analogue oscilloscope. It has no cursors and no measurement
panel, so every value must be counted off the graticule against the VOLTS/DIV
and TIME/DIV settings. We photographed the screen with the front panel in
frame for that reason.

> **OPEN ITEM — to be completed at the bench.**
>
> Our Part 3B/3C captures were of the Arduino **control** pins 9 and 10, and
> those establish what they should: the active input is a clean two-level
> rectangular wave whose high fraction tracks the commanded duty, and the
> idle input is a flat line with no switching on it.
>
> What this section still needs is the pair of **power-output** traces, `M+`
> and `M−`, in each of the two directions, with a short comparison between
> them. Two channels, both ground clips on Arduino GND, one tip on `M+` and
> one on `M−`, at a low PWM value.
>
> Expected result, to be confirmed rather than assumed: in each direction the
> output on the actively driven side swings between roughly the supply rail
> and 0 V at 490 Hz with the commanded duty, while the other output sits near
> 0 V; switching the direction input exchanges which output does which. Brief
> spikes on the quiet output at the switching instants would be the motor's
> inductance driving current through the other half-bridge's body diode.
>
> Because the TEC replaces the motor at the start of Module 3, this
> measurement has to be made either before the motor comes off the terminal
> bus or repeated with the TEC as the load.

## 9. Motor test note

| Direction input | Serial Monitor | Rotation observed |
|---|---|---|
| pin 11 = `5V` | `HEAT / clockwise`, duty 197 of 255 (77.3%) | **clockwise** |
| pin 11 = `0V` | `COOL / counter-cw`, duty 197 of 255 (77.3%) | **counterclockwise** |

The assignment's convention for Module 2 is that heat means clockwise and cool
means counterclockwise, and our wiring matches it as built. No swap of the
motor leads at the barrier strip was needed.

**PWM speed response.** Fourteen knob settings were held and recorded, from
duty 20 to 254 of 255. The shaft did not move at the bottom of the travel,
began turning slowly in the low tens of counts, and increased smoothly in
speed to the top of the travel. Direction was set only by pin 11 and was
completely unaffected by the knob. The full table with predicted pulse widths
is in `data/module_02/part3_hbridge_motor.txt`.

A tape flag on the shaft is what makes the low-speed end legible; below about
duty 30 the rotation is easier to see as a flag sweeping than as a moving
shaft.

---

## Safety record for Module 2

- Every scope probe ground clip on Arduino `GND`, never on `M+` or `M−`.
- TEC module and thermal switch disconnected from the load terminals for the
  whole of Module 2. The only load driven was the small DC motor.
- `setup()` drives both H-bridge inputs LOW before anything else, so the
  bridge is not commanded during boot or reset.
- Signal verification in Part 3B was done with actuator power off, and the
  motor in Part 3C was only powered after the instructor checked the wiring.
- The PWM cap in the sketch was 80 of 255 while the control signals were being
  verified with no load, and 255 for the motor run.
