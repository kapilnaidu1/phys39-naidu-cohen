# Phys 39 — Instrumentation Laboratory

**Team:** Kapil Naidu and Samuel Cohen
**Course:** Phys 39, Fall 2026

Team repository for the temperature-control instrument built across the semester.

---

## Repository layout

```
code/module_01/          Arduino sketches for Module 1
data/module_01/          raw numerical output captured from Serial Monitor
docs/module_notes/       written evidence notes
docs/images/             photographs, Serial Plotter and oscilloscope screenshots
```

---

## Module 1: First Contact With The Instrument

Evidence note: [`docs/module_notes/module_01_evidence.md`](docs/module_notes/module_01_evidence.md)

### Sketches

| Sketch | What it does | What it was used to measure |
|---|---|---|
| [`adc_raw.ino`](code/module_01/adc_raw.ino) | Reads A0 and prints the raw 10-bit integer as `ADC:nnn` | Minimum, maximum and midrange ADC values; the discrete-level behaviour in Part 3A |
| [`adc_volts.ino`](code/module_01/adc_volts.ino) | Converts each ADC count to a voltage and prints it | Part 3B, the one-count resolution of 4.88 mV |
| [`averaging_compare.ino`](code/module_01/averaging_compare.ino) | Alternates 100 single readings with 100 thousand-reading averages; also times the 1000-read loop with `micros()` | Parts 3C and 3D: the averaging table, the smallest discrete voltage jumps, and the acquisition time |
| [`pwm_brightness.ino`](code/module_01/pwm_brightness.ino) | Maps the averaged potentiometer voltage to a PWM duty cycle on pin 9 | Part 4, the oscilloscope measurements of the LED PWM waveform |
| [`blink_ratio.ino`](code/module_01/blink_ratio.ino) | Blinks an external LED at a chosen HIGH:LOW ratio | Part 1, the three Blink timing ratios |

### Data

| File | Contents |
|---|---|
| [`ave_data.txt`](data/module_01/ave_data.txt) | Raw Serial Monitor capture of the Part 3C blocks and the Part 3D timing lines |

### Headline results

| Quantity | Measured |
|---|---|
| ADC range | 0 to 1023 |
| One-count voltage resolution | 4.88 mV |
| s (100 single readings) | 2.035 mV |
| s (100 averages of 1000 readings) | 0.0726 mV |
| Measured s₁₀₀₀/s₁ | 0.0357 against a prediction of 0.0316 |
| Effective bits gained | 4.81 against an ideal of 4.98 |
| Time for 1000 `analogRead()` | 112,042 µs, so 112.0 µs per conversion |
| PWM frequency on pin 9 | 490.42 Hz against an expected 490 Hz |

### Hardware

Arduino Uno powered from USB, 100 kΩ potentiometer wired as a voltage divider into A0, and an LED on pin 9 through a 3.25 kΩ series resistor.

Per the Module 1 safety boundary, the TEC power supply remained off for the entire session.
